"""Immutable pre-integration references used only by diagnostic regression tests."""
import ast
from functools import lru_cache
from pathlib import Path
import subprocess
from types import FunctionType

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_COMMIT = '3299040'


@lru_cache(maxsize=None)
def source_at(commit, path):
    from diagnostics.review_fixtures import reference_source
    archived = reference_source(commit, path)
    if archived is not None:
        return archived
    return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT).decode('utf-8')


def source(path):
    return source_at(REFERENCE_COMMIT, path)


def function(path, name, namespace):
    node = next(n for n in ast.parse(source(path)).body if isinstance(n, ast.FunctionDef) and n.name == name)
    temporary = dict(namespace)
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<fixed ' + REFERENCE_COMMIT + ' ' + name + '>', 'exec'), temporary)
    reference = temporary[name]
    return FunctionType(reference.__code__, namespace, name, reference.__defaults__, reference.__closure__)
