r"""Apply the three lossless SDMPC decision-speed changes to a tree.

Each edit is anchored on exact source text and refuses to double-apply, so the
script is safe to re-run and reports precisely what it changed.

  A  marshal cache for AST-transformed modules (sdmpc_tangent_runtime.py)
  B  Trace.branch body written out            (sdmpc_tangent_reverse.py)
  C  two-argument max/min entry               (sdmpc_tangent_reverse.py)

None of the three changes what the model computes; A is pure caching and B/C
preserve the selected operand and every recorded comparison counter.
"""
import io
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r'D:\VISSIM-merge\sim3')
C = ROOT / 'evaluation' / 'controllers'
CHANGED = []


def edit(path, old, new, label):
    raw = io.open(path, 'rb').read()
    text = raw.decode('utf-8')
    crlf = b'\r\n' in raw
    o = old.replace('\n', '\r\n') if crlf else old
    n = new.replace('\n', '\r\n') if crlf else new
    if n in text:
        print('  SKIP %s (already applied)' % label)
        return
    if text.count(o) != 1:
        raise SystemExit('  FAIL %s: anchor count=%d in %s' % (label, text.count(o), path))
    io.open(path, 'wb').write(text.replace(o, n).encode('utf-8'))
    CHANGED.append(label)
    print('  OK   %s  (crlf=%s)' % (label, crlf))


RT = C / 'sdmpc_tangent_runtime.py'
RV = C / 'sdmpc_tangent_reverse.py'

# --------------------------------------------------------------- A: marshal cache
edit(RT, "import importlib.machinery\nimport sys\n",
         "import importlib.machinery\nimport marshal\nimport os\nimport sys\n",
     'A1 runtime imports')

CACHE_HELPER = '''_CACHE_DIR = Path(__file__).resolve().parent / '__tangentcache__'
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
    key = hashlib.sha256('\\x00'.join((digest, _self_digest(),
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


class Loader(importlib.abc.Loader):'''

edit(RT, "class Loader(importlib.abc.Loader):", CACHE_HELPER, 'A2 cache helper')

edit(RT,
     "        source = Path(self.filename).read_bytes()\n"
     "        self.hashes[self.filename] = hashlib.sha256(source).hexdigest()\n"
     "        tree = Transform().visit(ast.parse(source, filename=self.filename))\n"
     "        module.__dict__.update(namespace())\n"
     "        exec(compile(ast.fix_missing_locations(tree), self.filename, 'exec'), module.__dict__)",
     "        source = Path(self.filename).read_bytes()\n"
     "        digest = hashlib.sha256(source).hexdigest()\n"
     "        self.hashes[self.filename] = digest\n"
     "        module.__dict__.update(namespace())\n"
     "        exec(_transformed_code(self.filename, source, digest), module.__dict__)",
     'A3 exec_module')

# --------------------------------------------------------------- B: branch body
OLD_BRANCH = """        if PRIMAL_GUARD:
            return (0, 0)
        self.counts['primal_comparisons'] += 1
        support = (a.support if isinstance(a, Dual) else 0) | (b.support if isinstance(b, Dual) else 0)
        if primal(a) == primal(b):
            self.counts['exact_primal_ties'] += 1
            self.exact_support |= support
        if discrete:
            self.counts['discrete_comparisons'] += 1
            self.discrete_support |= support
        return (0, 0)"""

NEW_BRANCH = """        if PRIMAL_GUARD:
            return (0, 0)
        # A taped rollout runs millions of these, so the body is written out
        # instead of calling primal() twice. The two predicates below differ on
        # purpose and must stay that way: only a reverse Dual carries .support,
        # while primal() reads .value off any forward.Dual. Collapsing them would
        # silently change the exact-tie test for a bare forward Dual.
        counts = self.counts
        counts['primal_comparisons'] += 1
        if isinstance(a, Dual):
            support, av = a.support, a.value
        elif isinstance(a, forward.Dual):
            support, av = 0, a.value
        else:
            support, av = 0, float(a)
        if isinstance(b, Dual):
            support |= b.support
            bv = b.value
        elif isinstance(b, forward.Dual):
            bv = b.value
        else:
            bv = float(b)
        if av == bv:
            counts['exact_primal_ties'] += 1
            self.exact_support |= support
        if discrete:
            counts['discrete_comparisons'] += 1
            self.discrete_support |= support
        return (0, 0)"""

edit(RV, OLD_BRANCH, NEW_BRANCH, 'B  Trace.branch body')

# --------------------------------------------------------------- C: max/min entry
OLD_MM = ("def minimum(*args, **kwargs): return extremum(False, *args, **kwargs)\n"
          "def maximum(*args, **kwargs): return extremum(True, *args, **kwargs)")

NEW_MM = '''_ABSENT = object()


def _two_argument(is_max, a, b):
    """The FAST_PRIMITIVES two-argument body, reached without an *args repack.

    max/min is the hottest primitive in an instrumented rollout: the runtime
    rewrites every `max(`/`min(` in ~90 modules to these functions, and a taped
    rollout makes millions of the calls. The two-argument case therefore skips
    the extremum() frame and its builtins lookup. The operand selected and the
    comparison evidence recorded are exactly those of the path in extremum().
    """
    da = isinstance(a, Dual)
    db = isinstance(b, Dual)
    if not da and not db:
        return (builtins.max if is_max else builtins.min)(a, b)
    av = a.value if da else a
    bv = b.value if db else b
    if (bv > av) if is_max else (bv < av):
        selected, other = b, a
    else:
        selected, other = a, b
    if other is not selected:
        (a.trace if da else b.trace).branch(other, selected, output_connected=True)
    return selected


def minimum(a=_ABSENT, b=_ABSENT, *rest, **kwargs):
    if b is not _ABSENT and not rest and not kwargs and FAST_PRIMITIVES:
        return _two_argument(False, a, b)
    if a is _ABSENT: return extremum(False, **kwargs)
    if b is _ABSENT: return extremum(False, a, **kwargs)
    return extremum(False, a, b, *rest, **kwargs)


def maximum(a=_ABSENT, b=_ABSENT, *rest, **kwargs):
    if b is not _ABSENT and not rest and not kwargs and FAST_PRIMITIVES:
        return _two_argument(True, a, b)
    if a is _ABSENT: return extremum(True, **kwargs)
    if b is _ABSENT: return extremum(True, a, **kwargs)
    return extremum(True, a, b, *rest, **kwargs)'''

edit(RV, OLD_MM, NEW_MM, 'C  maximum/minimum entry')

print('changed: %d' % len(CHANGED))
