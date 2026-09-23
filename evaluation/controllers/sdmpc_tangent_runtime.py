"""Process-isolated source instrumentation for the current coupled predictor.

Only numeric primitives are replaced. Imports, installed model hooks, physical
equations and branch selections remain those of this checkout. Never install
this finder in the controller or in a reusable scalar prediction worker.
"""
from __future__ import annotations

import ast
import builtins
import hashlib
import importlib.abc
import importlib.machinery
import marshal
import os
import sys
from pathlib import Path

from evaluation.controllers import sdmpc_dual as ad


def numeric_isinstance(value, classes):
    if isinstance(value, ad.Dual):
        choices = classes if isinstance(classes, tuple) else (classes,)
        if float in choices:
            return True
    return builtins.isinstance(value, classes)


def numeric_type(*args):
    if len(args) == 1 and isinstance(args[0], ad.Dual):
        return float
    return builtins.type(*args)


class Transform(ast.NodeTransformer):
    calls = {'float': '_tangent_float', 'min': '_tangent_min',
             'max': '_tangent_max', 'isinstance': '_tangent_isinstance',
             'type': '_tangent_type'}

    def visit_Call(self, node):
        node = self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id in self.calls:
            node.func.id = self.calls[node.func.id]
        return node

    def visit_Import(self, node):
        result = []
        for name in node.names:
            if name.name in ('math', 'numpy'):
                result.append(ast.copy_location(ast.Assign(
                    targets=[ast.Name(id=name.asname or name.name, ctx=ast.Store())],
                    value=ast.Name(id='_tangent_'+name.name, ctx=ast.Load())), node))
            else:
                result.append(ast.copy_location(ast.Import(names=[name]), node))
        return result

    def visit_ImportFrom(self, node):
        if node.level == 0 and node.module == 'math':
            if any(n.name == '*' for n in node.names):
                raise ValueError('Wildcard math import is not supported by tangent instrumentation')
            return [ast.copy_location(ast.Assign(
                targets=[ast.Name(id=n.asname or n.name, ctx=ast.Store())],
                value=ast.Attribute(value=ast.Name(id='_tangent_math', ctx=ast.Load()),
                                    attr=n.name, ctx=ast.Load())), node) for n in node.names]
        return node


def namespace():
    return dict(_tangent_float=ad.float_keep, _tangent_min=ad.minimum,
        _tangent_max=ad.maximum, _tangent_math=ad.MathProxy(),
        _tangent_numpy=ad.NumpyProxy(), _tangent_isinstance=numeric_isinstance,
        _tangent_type=numeric_type)


_CACHE_DIR = Path(__file__).resolve().parent / '__tangentcache__'
_SELF_DIGEST = None


def _self_digest():
    global _SELF_DIGEST
    if _SELF_DIGEST is None:
        _SELF_DIGEST = hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest()
    return _SELF_DIGEST


def _transformed_code(filename, source, digest):
    """Marshal cache for the AST-transformed code object.

    Parsing, transforming and compiling the ~97 instrumented modules costs about
    four seconds, and every spawned prediction worker pays it again. The compiled
    object is a pure function of the source, of this file's Transform, of the
    interpreter and of the filename, so all four go into the key: compile() bakes
    co_filename into the object, and without it two byte-identical sources (an
    empty __init__.py, say) would share an entry and corrupt tracebacks. A miss,
    a corrupt entry or an unwritable cache directory all fall back to compiling
    in process, so the cache can only make this faster, never change what runs.
    """
    key = hashlib.sha256('\x00'.join((digest, _self_digest(),
        sys.implementation.cache_tag or '', str(filename))).encode('utf-8')).hexdigest()
    path = _CACHE_DIR / (key + '.mcode')
    try:
        return marshal.loads(path.read_bytes())
    except (OSError, ValueError, EOFError, TypeError):
        pass
    tree = Transform().visit(ast.parse(source, filename=filename))
    code = compile(ast.fix_missing_locations(tree), filename, 'exec')
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        staging = path.with_name(path.name + '.' + str(os.getpid()))
        staging.write_bytes(marshal.dumps(code))
        os.replace(staging, path)
    except OSError:
        pass
    return code


class Loader(importlib.abc.Loader):
    def __init__(self, original, filename, hashes):
        self.original, self.filename, self.hashes = original, filename, hashes

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        source = Path(self.filename).read_bytes()
        digest = hashlib.sha256(source).hexdigest()
        self.hashes[self.filename] = digest
        module.__dict__.update(namespace())
        exec(_transformed_code(self.filename, source, digest), module.__dict__)


class Finder(importlib.abc.MetaPathFinder):
    def __init__(self, root):
        self.root, self.source_hashes = Path(root).resolve(), {}

    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('evaluation.controllers.sdmpc_tangent',
                                'evaluation.controllers.sdmpc_dual',
                                'evaluation.controllers.sdmpc_prediction_cache')):
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec is None or not spec.origin or not spec.origin.endswith('.py'):
            return None
        if not Path(spec.origin).resolve().is_relative_to(self.root):
            return None
        spec.loader = Loader(spec.loader, spec.origin, self.source_hashes)
        return spec


def install(root, backend='forward'):
    global ad
    if backend == 'reverse-v1':
        from evaluation.controllers import sdmpc_tangent_reverse as ad
    elif backend != 'forward':
        raise ValueError('Unknown tangent backend')
    already = [m for m in sys.modules if m.startswith('src.models.')]
    if already:
        raise RuntimeError('Tangent instrumentation requires a fresh isolated process')
    finder = Finder(root)
    finder.ad, finder.backend = ad, backend
    sys.meta_path.insert(0, finder)
    return finder
