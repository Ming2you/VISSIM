"""VerifyGates 3 (independent verification A31, amendment 31 section 4.3; user decision D-K9-60): shared helpers.

New file.  Standard library only.  Imports nothing of the project, of the harness (sa_* / k92_* / k8b_*), of the k92t
drivers or judges (base / 30 / 31), of k92t31_unit.py, of the earlier verification tools (vg_* / vg3_* / vglib).

Paths are kept in one dict `P` so that the synthetic self-test (vg4_synth.py) can point every reader at a fake layout.
"""
import hashlib
import json
import os
import re
import time
from pathlib import Path

SP = Path(r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/'
          r'491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8')
KB = SP / 'k92' / 'bundle1'
VG4 = KB / 'vgates4'
OK2 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1')
TK = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1')

# every place the verification reads (one dict, replaced as a whole by the synthetic self-test)
P = {
    'KB': KB,
    'LOG': KB / 'LOG.md',
    'A31': SP / 'K8_PREDECLARATION_AMENDMENT_31.md',
    'A31_SHA': SP / 'K8_PREDECLARATION_AMENDMENT_31.md.sha256',
    'FIXED31': KB / 'AMENDMENT31_FIXED.md',
    'A31_PINS': KB / 'a31_pins.sha256',
    'OK2': OK2,
    'OUTK': OK2 / 'k92t',
    'OUT30': OK2 / 'a30',
    'OUT31': OK2 / 'a31',
    'SEALED': OK2 / 'sealed_s47',
    'OK2A': OK2 / 'probe_a25',
    'RJG4': OK2 / 'a27' / 'judge' / 'rjg4.json',
    'CAP': OK2 / 'k92t' / 'jb' / 'sa' / 'cap' / 'k92t',
    'CAP_MANIFEST': KB / 'a31review' / 'out' / 'cap_manifest.json',
    'JB': OK2 / 'k92t' / 'jb',
    'UNIT_LOG_NEW': OK2 / 'k92t' / 'jb' / 'sa' / 'unit_k92t.log',
    'UB': OK2 / 'a31' / 'unit_base',
    'UNIT_LOG_BASE': OK2 / 'a31' / 'unit_base' / 'unit_b9734abe.log',
    'TK': TK,
    'TKA': TK / 'a25',
    'TREE': TK / 'a27' / 'k92t',
    'WT': TK / 'a31_wt_b9734abe',
    'WT_ADMIN': Path(r'D:/VISSIM-merge/repo/.git/worktrees/a31_wt_b9734abe'),
    'GIT_DIR_K92': Path(r'D:/VISSIM-merge/repo/.git/worktrees/sim3-n31-k8'),
    'GWT8': Path(r'D:/VISSIM-merge/sim3-n31-k8'),
    'OUT': VG4 / 'out',
}

# declared values (amendment 31 sections 0, 2.4, 4.1 C9, 4.3, fixation record AMENDMENT31_FIXED.md)
A31_SHA256 = '8541ccb7fa6c951b4affcca67d57e25be09b061c3ae3dd006d050c9c6413e304'
FIXED31_SHA256 = '605ccbd2cb392ac2ed0a6da1d27c20e93aa68fcac50ec6d99c4393236f98a053'
A31_PINS_SHA256 = 'bf1ca001e8c8a4215512582871ddf439971aff04887267a0b797b3496ddc6d4e'
JF_SHA256 = {'judge/f.json': '04cfa2e0a9ac754bd13d5c5ca2d4cd5790acb34fda64fafdce7f7382027ac792',
             'judge/jb.json': 'f8a273ef9b6e2f02f539b4193a39d35516959d8799e3cd89a2b060c006faa200'}
RJG4_SHA256 = '246f28aa8cae77281d414a8cf774bd6c6c688d6929b726baf1e83c69448a82ec'
CAP_MANIFEST_SHA256 = 'd6691f48954d07dd2b3bbfe718e468fd59f3f6b7492060a2151d4d02e177e3a9'
CAP_LISTING_SHA256 = '5340ac03da81742dd864044f9922a75bed1e542147249d4a8699a6432e273038'
CAP_N_FILES = 3944
CAP_N_BYTES = 1690146202
HEAD = 'e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d'
BRANCH = 'claude/k92-b1-20261016'
K8 = 'b9734abe1c83f95c9cec5fca5e42b7b18cd45991'
K8_BRANCH = 'claude/k8-sc1001eb-defects-20261004'


def lp(p):
    """Windows long-path form of an absolute path (reading only)."""
    s = os.path.abspath(str(p))
    if os.name != 'nt' or s.startswith('\\\\?\\'):
        return s
    return '\\\\?\\' + s


def sha256_file(p):
    h = hashlib.sha256()
    with open(lp(p), 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def sha256_or_none(p):
    try:
        return sha256_file(p)
    except OSError:
        return None


def read_json(p):
    """JSON of a file (utf-8, BOM allowed, NaN / Infinity allowed as Python's json does); raises on any error."""
    with open(lp(p), 'rb') as f:
        data = f.read()
    return json.loads(data.decode('utf-8-sig'))


def read_json_or(p, default=None):
    try:
        return read_json(p)
    except (OSError, ValueError, UnicodeDecodeError):
        return default


def read_text(p):
    with open(lp(p), 'rb') as f:
        return f.read().decode('utf-8', errors='replace')


def write_json(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(p) + '.tmp')
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False, default=str) + '\n')
    os.replace(tmp, p)
    return sha256_file(p)


def now():
    return time.strftime('%Y-%m-%d %H:%M:%S')


def log_md(text):
    """Append one automatic line to the work log (KB/LOG.md; append only)."""
    line = '- [%s +0900] %s (VerifyGates 3 자동 기록)\n' % (time.strftime('%Y-%m-%d %H:%M'), text)
    with open(P['LOG'], 'a', encoding='utf-8', newline='\n') as f:
        f.write(line)


def log_has(token):
    try:
        return token in Path(P['LOG']).read_text(encoding='utf-8', errors='replace')
    except OSError:
        return False


def jf_fixed():
    """Amendment 30 section 4.5: the J / F judge files are fixed = both sha in the LOG and both files unchanged."""
    out = {}
    for rel, want in JF_SHA256.items():
        out[rel] = {'in_log': log_has(want), 'file_sha_same': sha256_or_none(Path(P['OUTK']) / rel) == want}
    out['ok'] = all(v['in_log'] and v['file_sha_same'] for v in out.values() if isinstance(v, dict))
    return out


def tools_pinned(paths):
    """Every tool file's sha256 (64 hex) is written in the LOG (the verification pins its tools before data)."""
    rows = {}
    for p in paths:
        s = sha256_or_none(p)
        rows[Path(p).name] = {'sha256': s, 'in_log': bool(s) and log_has(s)}
    return {'ok': all(r['in_log'] for r in rows.values()), 'tools': rows}


def free_gb(drive):
    import shutil
    try:
        return shutil.disk_usage(drive).free / 1e9
    except OSError:
        return None


def count_procs():
    """Process counts by image name prefix (tasklist; names only)."""
    import subprocess
    try:
        out = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True, text=True, timeout=60).stdout
    except Exception:  # noqa: BLE001
        return None
    names = [ln.split('","')[0].strip('"').lower() for ln in out.splitlines() if ln.strip()]
    return {k: sum(1 for n in names if n.startswith(k)) for k in ('python', 'vissim', 'cscript', 'wscript')}


def norm_slash(s):
    return re.sub(r'[\\/]+', '/', str(s))
