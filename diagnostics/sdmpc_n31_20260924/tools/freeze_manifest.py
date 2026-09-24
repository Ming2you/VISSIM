r"""FREEZE.json of a frozen launch tree FRZ (plan D5, NEW-14).

A git worktree cannot be the launch tree: runtime files are untracked (NEW-14), and the
worktree keeps changing. freeze_worktree.ps1 robocopies W to FRZ; this helper records and
checks what was copied.

    freeze_manifest.py git-state <W> <out.json>
        HEAD, branch and `git status --porcelain=v1 --untracked-files=all -z` of W (bytes, sha).
    freeze_manifest.py build <W> <FRZ> <git-state.json>
        Hash every file of FRZ and of W (same exclusions), require them identical and the git
        state unchanged since git-state, then write <FRZ>\FREEZE.json. Prints FREEZE_OK.
    freeze_manifest.py verify <FRZ>
        Re-hash FRZ against FREEZE.json: no changed, missing or extra file. Prints FREEZE_VERIFIED.

The file table covers the whole tree (a superset of the plan's evaluation/ scripts/ src/
plant/ diagnostics/sdmpc_n31_20260924/): an extra sibling file can change a run too, e.g. the
runner finds <config>_sgplan.vbs by name. Excluded: .git (the worktree link file, or a clone's
folder), __pycache__/.pytest_cache folders and *.pyc at any depth, and the root FREEZE.json itself.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from n31_common import FREEZE_NAME, FREEZE_SCHEMA, ToolError, file_sha256, long_path, read_json, require, write_json  # noqa: E402

# Same rules as the robocopy call in freeze_worktree.ps1 (/XD and /XF match case-insensitively at
# every depth). FREEZE.json is excluded at the root only: nested boundary_fit/freeze.json are inputs.
EXCLUDED_DIRS = ('__pycache__', '.pytest_cache', '.git')   # .git: a plain clone's folder (a worktree has a file)
EXCLUDED_NAMES = ('.git',)
EXCLUDED_SUFFIXES = ('.pyc',)
PLAN_SUBTREES = ('evaluation/', 'scripts/', 'src/', 'plant/', 'diagnostics/sdmpc_n31_20260924/')


def excluded(rel):
    parts = rel.split('/')
    if any(p.lower() in EXCLUDED_DIRS for p in parts[:-1]):
        return True
    name = parts[-1]
    if len(parts) == 1 and name == FREEZE_NAME:
        return True
    return name.lower() in EXCLUDED_NAMES or name.lower().endswith(EXCLUDED_SUFFIXES)


def walk_files(root):
    """{relative forward-slash path: absolute path} of every non-excluded file under root."""
    root_long = long_path(root)
    out = {}
    for current, dirs, files in os.walk(root_long):
        dirs[:] = sorted(d for d in dirs if d.lower() not in EXCLUDED_DIRS)
        rel_dir = os.path.relpath(current, root_long)
        for name in files:
            rel = name if rel_dir == '.' else os.path.join(rel_dir, name)
            rel = rel.replace('\\', '/')
            if not excluded(rel):
                out[rel] = os.path.join(current, name)
    return dict(sorted(out.items()))


def hash_tree(root):
    table, total = {}, 0
    for rel, path in walk_files(root).items():
        table[rel] = file_sha256(path)
        total += os.path.getsize(path)
    return table, total


def tree_sha256(table):
    return hashlib.sha256(json.dumps(table, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def _git(root, *args):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True)
    require(result.returncode == 0, f'git {" ".join(args)} failed: {result.stderr.decode("utf-8", "replace").strip()}')
    return result.stdout


def git_state(root):
    head = _git(root, 'rev-parse', '--verify', 'HEAD^{commit}').decode('ascii').strip()
    branch = _git(root, 'rev-parse', '--abbrev-ref', 'HEAD').decode('utf-8').strip()
    porcelain = _git(root, 'status', '--porcelain=v1', '--untracked-files=all', '-z')
    entries = [e.decode('utf-8', 'surrogateescape') for e in porcelain.split(b'\0') if e]
    return {'head': head, 'branch': branch,
            'status_command': 'git status --porcelain=v1 --untracked-files=all -z',
            'status_sha256': hashlib.sha256(porcelain).hexdigest(), 'status_entries': len(entries),
            'status': entries}


def diff_tables(expected, actual):
    changed = sorted(k for k in expected.keys() & actual.keys() if expected[k] != actual[k])
    return {'changed': changed, 'missing': sorted(expected.keys() - actual.keys()),
            'extra': sorted(actual.keys() - expected.keys())}


def _summary(diff, limit=20):
    return '; '.join(f'{k}={len(v)} {v[:limit]}' for k, v in diff.items() if v)


def build(source, frozen, state_file):
    source, frozen = Path(source).resolve(), Path(frozen).resolve()
    require(frozen.is_dir(), f'Frozen tree missing: {frozen}')
    require(not (frozen / FREEZE_NAME).exists(), f'{FREEZE_NAME} already exists: {frozen}')
    before = read_json(state_file)
    frozen_table, total = hash_tree(frozen)
    source_table, _ = hash_tree(source)
    diff = diff_tables(source_table, frozen_table)
    require(not any(diff.values()), 'Frozen copy differs from the worktree (edited during the copy?): ' + _summary(diff))
    after = git_state(source)
    require(after == before, 'Worktree git state changed during the freeze')
    document = {
        'schema': FREEZE_SCHEMA,
        'created_at': _dt.datetime.now().astimezone().isoformat(timespec='seconds'),
        'source': str(source), 'frozen': str(frozen),
        'git': before,
        'exclusions': {'dirs': list(EXCLUDED_DIRS), 'names': list(EXCLUDED_NAMES),
                       'suffixes': list(EXCLUDED_SUFFIXES), 'root_only': [FREEZE_NAME]},
        'plan_subtrees': list(PLAN_SUBTREES),
        'plan_subtree_files': {p: sum(1 for k in frozen_table if k.startswith(p)) for p in PLAN_SUBTREES},
        'file_count': len(frozen_table), 'total_bytes': total,
        'tree_sha256': tree_sha256(frozen_table),
        'files': frozen_table,
    }
    sha = write_json(frozen / FREEZE_NAME, document, indent=None)
    print(f'FREEZE_OK path={frozen / FREEZE_NAME} sha256={sha} files={len(frozen_table)} bytes={total} '
          f'head={before["head"]} status_entries={before["status_entries"]}')
    return document


def verify(frozen):
    frozen = Path(frozen).resolve()
    path = frozen / FREEZE_NAME
    require(path.is_file(), f'Not a frozen tree (no {FREEZE_NAME}): {frozen}')
    document = read_json(path)
    require(document.get('schema') == FREEZE_SCHEMA, f'Unsupported freeze schema in {path}')
    require(Path(document['frozen']).resolve() == frozen, f'{FREEZE_NAME} names another tree: {document["frozen"]}')
    expected = document['files']
    require(tree_sha256(expected) == document['tree_sha256'], f'{FREEZE_NAME} file table was edited')
    actual, _ = hash_tree(frozen)
    diff = diff_tables(expected, actual)
    require(not any(diff.values()), 'Frozen tree changed since the freeze: ' + _summary(diff))
    sha = file_sha256(path)
    print(f'FREEZE_VERIFIED path={path} sha256={sha} files={len(actual)} head={document["git"]["head"]}')
    return {'path': str(path), 'sha256': sha, 'document': document}


def main(argv):
    if len(argv) == 3 and argv[0] == 'git-state':
        state = git_state(Path(argv[1]).resolve())
        write_json(argv[2], state)
        print(f'GIT_STATE head={state["head"]} branch={state["branch"]} entries={state["status_entries"]}')
        return 0
    if len(argv) == 4 and argv[0] == 'build':
        build(argv[1], argv[2], argv[3])
        return 0
    if len(argv) == 2 and argv[0] == 'verify':
        verify(argv[1])
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except ToolError as error:
        print(f'FREEZE_ERROR {error}', file=sys.stderr)
        sys.exit(1)
