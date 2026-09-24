"""Shared helpers of the WP-D tools (SDMPC-31 x obs150, plan section 6).

The tools live in <root>/diagnostics/sdmpc_n31_20260924/tools/ where <root> is the
worktree W or a frozen copy FRZ. ROOT below is that tree, so a tool started from a
frozen copy imports the frozen contract and never the live worktree.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.controllers import obs150_contract as oc  # noqa: E402

N31D_REL = 'diagnostics/sdmpc_n31_20260924'
FREEZE_NAME = 'FREEZE.json'
FREEZE_SCHEMA = 'sdmpc31-freeze/v1'
RUNS_ROOT = Path(r'D:\VISSIM_runs\20260924_sdmpc31')
PYTHON = Path(r'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe')
DEV_TITLE_PATTERN = 'obs150|sdmpc|probe'   # D:\VISSIM_runs\20260923_stage1\launch_reserved.ps1
NETWORK_PREFIX = 'sdmpc31_'                # window title must match DEV_TITLE_PATTERN


class ToolError(RuntimeError):
    """A WP-D tool refuses to continue (never a silent default)."""


def require(condition, message):
    if not condition:
        raise ToolError(message)


def file_sha256(path):
    digest = hashlib.sha256()
    with open(long_path(path), 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def long_path(path):
    """Extended-length form so frozen copies deeper than MAX_PATH stay readable (LongPathsEnabled=0)."""
    text = os.path.abspath(str(path))
    if os.name == 'nt' and not text.startswith('\\\\?\\'):
        if text.startswith('\\\\'):
            return '\\\\?\\UNC\\' + text[2:]
        return '\\\\?\\' + text
    return text


def read_json(path):
    with io.open(long_path(path), encoding='utf-8-sig') as handle:
        return json.load(handle)


def write_json(path, document, *, indent=1):
    """UTF-8, LF, trailing newline; written through a temporary file then renamed."""
    path = Path(path)
    data = (json.dumps(document, ensure_ascii=False, indent=indent, sort_keys=False) + '\n').encode('utf-8')
    temporary = path.with_name(path.name + '.tmp')
    with open(long_path(temporary), 'wb') as handle:
        handle.write(data)
    os.replace(long_path(temporary), long_path(path))
    return hashlib.sha256(data).hexdigest()


def deep_update(base, override):
    """Same merge as vissim_stackelberg_adapter.deep_update (AD:689-696)."""
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_update(dict(out[key]), value)
        else:
            out[key] = value
    return out


def load_effective_tuning(path):
    """The extends-merged tuning, as AD load_optional_json (AD:699-717) but loud on a missing file.

    Returns (tuning, chain) where chain lists {path, sha256} child first."""
    path = Path(path).resolve()
    chain, seen = [], set()
    documents = []
    while True:
        require(path.is_file(), f'Tuning file missing: {path}')
        require(str(path).lower() not in seen, f'Cyclic tuning extends: {path}')
        seen.add(str(path).lower())
        document = json.loads(path.read_text(encoding='utf-8'))
        require(isinstance(document, dict), f'Tuning is not an object: {path}')
        chain.append({'path': str(path), 'sha256': file_sha256(path)})
        documents.append(document)
        parent = document.get('extends', '')
        if not parent:
            break
        parent_path = Path(str(parent))
        path = (parent_path if parent_path.is_absolute() else path.parent / parent_path).resolve()
    tuning = {}
    for document in reversed(documents):
        child = dict(document)
        child.pop('extends', None)
        tuning = deep_update(tuning, child)
    return tuning, chain


def repo_path(root, relative):
    """A manifest/tuning repo-relative forward-slash path under root."""
    require(isinstance(relative, str) and relative and '\\' not in relative and ':' not in relative
            and not relative.startswith('/') and '..' not in relative.split('/'),
            f'Not a repo-relative forward-slash path: {relative!r}')
    return Path(root, *relative.split('/'))


def find_freeze_root(start):
    """The nearest ancestor directory (or start itself) that holds FREEZE.json."""
    path = Path(start).resolve()
    if path.is_file():
        path = path.parent
    for candidate in (path, *path.parents):
        if (candidate / FREEZE_NAME).is_file():
            return candidate
    return None


def vbs_constants(path):
    """NAME = "value" / NAME = 123 lines of a generated VBS config (with & _ continuations)."""
    text = Path(path).read_text(encoding='utf-8-sig', errors='strict')
    joined = re.sub(r'"\s*&\s*_\s*\r?\n\s*"', '', text)
    values = {}
    for line in joined.splitlines():
        match = re.match(r'^\s*(RW_[A-Z0-9_]+)\s*=\s*(.+?)\s*$', line)
        if not match:
            continue
        raw = match.group(2)
        if raw.startswith('"') and raw.endswith('"'):
            values[match.group(1)] = raw[1:-1]
        else:
            values[match.group(1)] = raw
    return values


def decision_files(decisions_dir):
    """{sim_sec: Path} of action_<T>.json files in a decisions folder."""
    out = {}
    for path in Path(decisions_dir).glob('action_*.json'):
        match = re.fullmatch(r'action_(\d{6})\.json', path.name)
        if match:
            out[int(match.group(1))] = path
    return dict(sorted(out.items()))


def state_path(decisions_dir, sim_sec):
    return Path(decisions_dir) / f'state_{sim_sec:06d}.json'


def action_path(decisions_dir, sim_sec):
    return Path(decisions_dir) / f'action_{sim_sec:06d}.json'


def previous_decision_sec(sim_sec):
    """The decision before T on the obs150 clock: 150 -> 1, 300 -> 150, ..."""
    require(oc.is_decision_stop(sim_sec) and sim_sec >= oc.DECISION_INTERVAL_SEC,
            f'No previous decision for t={sim_sec}')
    return oc.FIRST_DECISION_SEC if sim_sec == oc.DECISION_INTERVAL_SEC else sim_sec - oc.DECISION_INTERVAL_SEC


def run_dir_of(decisions_dir):
    """<OutDir> of a watchdog run: the parent of decisions_<Name> (PS1:511)."""
    decisions_dir = Path(decisions_dir).resolve()
    require(decisions_dir.name.startswith('decisions_'), f'Not a watchdog decisions folder: {decisions_dir}')
    return decisions_dir.parent, decisions_dir.name[len('decisions_'):]


def provenance_path(run_dir, name):
    return Path(run_dir) / f'run_provenance_{name}.json'


def find_decisions_dir(path):
    """A decisions_<Name> folder itself, or the single one inside a run folder."""
    path = Path(path).resolve()
    if path.name.startswith('decisions_') and path.is_dir():
        return path
    found = sorted(p for p in path.glob('decisions_*') if p.is_dir())
    require(len(found) == 1, f'Expected one decisions_* folder in {path}, found {len(found)}')
    return found[0]


def link_or_copy(source, target):
    """Hard link (write-once run files); a copy only across volumes. Returns the method."""
    import shutil
    source, target = Path(source), Path(target)
    require(source.is_file(), f'Missing file to link: {source}')
    require(not target.exists(), f'Link target already exists: {target}')
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(long_path(source), long_path(target))
        return 'hardlink'
    except OSError as error:
        if getattr(error, 'winerror', None) != 17 and error.errno != 18:   # ERROR_NOT_SAME_DEVICE / EXDEV
            raise
    shutil.copy2(long_path(source), long_path(target))
    return 'copy'


def effective_vsl_max(tuning):
    """max(config_overrides.freeway_follower.vsl_set) of an effective tuning (OBS1:7466)."""
    values = (tuning.get('config_overrides', {}).get('freeway_follower', {}) or {}).get('vsl_set')
    require(isinstance(values, list) and values and all(isinstance(v, (int, float)) for v in values),
            'Tuning lacks config_overrides.freeway_follower.vsl_set')
    return float(max(values))
