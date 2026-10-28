"""vsl_plant shared helpers (PRE_VP.md, 2026-10-27 KST).  Scratch tool, never committed.

Writes only under VP (scratchpad k8/vsl_plant), GT (D:/VISSIM-merge/k8_gate_trees/vsl_plant) and the report copy
folder RVP.  Reads (never writes) run folders, FRZ_K92, the o1o2 / vsl_v3c3 outputs.  Seeds always come from the
run provenance field `seed`, never from a folder or file name.  BLIND: v3c3-s47 and the sealed seeds 37/59/61/67
are refused by name (blind_guard)."""
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
SP = Path(r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/'
          r'491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8')
VP = SP / 'vsl_plant'
TOOLS = VP / 'tools'
DECL = VP / 'decl'
GT = Path(r'D:/VISSIM-merge/k8_gate_trees/vsl_plant')
CODE = GT / 'code_va'                      # scratch copy of FRZ_K92 (vp_tree.py)
OUT = GT / 'out'
RVP = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/vsl_plant')
LOCK = Path(r'D:/VISSIM-merge/k8_gate_trees/heavy.lock')
LAST_RELEASE = GT / 'lock_last_release.json'
FRZ_VA = Path(r'D:/VISSIM-merge/frozen/sdmpc31_c20aff1d_202610230833')
FRZ_VA_FREEZE_SHA = '011f5be253fd31a5fb8342859b2b571375e49b4bbbbb42ea8f3ca93657b68476'
REV = 'c20aff1d7bf0c432cb4f20e2922bd406d857aa5d'
TUNING_REL = 'diagnostics/sdmpc_n31_20260924/config_n31_v2.json'
TUNING_SHA = 'c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866'
POLICY_TOKEN = '428e650ded2f1cb8bb4365abac76ea9765da4783d19e8c2dab1bcd7b688399f9'
GPREP = SP / 'j1' / 'fix' / 'gates' / 'gprep.py'
GPREP_SHA = '0482a53868fd3ee644724dab2dcb6af2c56d749708ccec5242f6b3549ae26f22'
O2_CELLS = SP / 'vsl_v3c3' / 'o1o2' / 'tools' / 'o2_fzp_cells.py'
O2_CELLS_SHA = 'cff42e34d518bb5d1864fcd5d9c503b329037007f73947564088362c3a412013'
CELL_SCAN = SP / 'vsl_v3c3' / 'tools' / 'vsl_cell_scan.py'
CELL_SCAN_SHA = 'fa5aeafd01c99297652f8f5fce6d5f760cdbb223640b3258d2020cd03229a078'
PY = r'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
DEPROOT = r'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps'
BELOW_NORMAL = 0x00004000
RELEASE_PAUSE_SEC = 20.0
RUN_ROOTS = {'va': Path(r'D:/VISSIM_runs/20261023_sdmpc31_k92'),
             'nc3': Path(r'D:/VISSIM_runs/20261001_v3c3'),
             'vsl': Path(r'D:/VISSIM_runs/20261027_vsl_v3c3'),
             'b': Path(r'D:/VISSIM_runs/20261026_codex_b_v3c3')}
BLIND_TOKENS = ('s47', 's37', 's59', 's61', 's67', 'sealed')

# FW_E mainline chain and the 31 plant cells.  Our plant (V-A, FRZ_K92) runs FW_E on 31 refined cells (worker-seen
# segment rows = 31, segment_lanes 4 x 19 + 3 x 12); the VSL command space is the 21 parent segments.  CELL_B equals
# vsl_cell_scan.py / o2_fzp_cells.py CELL_B; every rollout checks it against the plant's own cell lengths (S-MAP).
CHAIN = [(74, 0.0, 4), (10699, 2701.577, 4), (2, 2734.527, 4), (10613, 6841.743, 3),
         (119, 6847.981, 3), (10702, 7431.364, 3), (24, 7438.047, 3)]
CELL_B = [0.0, 526.2879, 1052.5758, 1578.8638, 2105.1517, 2631.4396, 3157.7275, 3684.0155, 4210.3034, 4286.333,
          4542.5389, 4736.5913, 4894.3955, 5078.6373, 5262.8792, 5789.1672, 6315.4551, 6490.8844, 6666.3137, 6841.743,
          7041.7112, 7241.6793, 7334.5286, 7498.7905, 7663.0524, 7827.3143, 8320.0999, 8812.8855, 9305.6711, 9798.4567,
          10291.2424, 10784.028]
N_CELL = 31
CELL_LANES = [4] * 19 + [3] * 12
# Zones on the 31 cells (PRE_O1O2 names and ranges) plus three cell-aligned approximations of the VSL_REPORT chain
# zones (Mu 6,300-6,700 / VS0 6,700-6,800 / B2 6,800-8,100 m): Mu' = 16-17, VS0' = 18, B2' = 19-24.
ZONES = {'U': list(range(0, 8)), 'B1': list(range(8, 14)), 'M1': [14, 15], 'VSa': [16, 17, 18], "Mu'": [16, 17],
         "VS0'": [18], 'VSb': list(range(19, 26)), "B2'": list(range(19, 25)), 'D': list(range(26, 31))}
ZONE_ORDER = ['U', 'B1', 'M1', 'VSa', "Mu'", "VS0'", 'VSb', "B2'", 'D']
FOCUS_CELLS = list(range(8, 26))


def kst():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S KST')


def lp(path):
    p = os.path.abspath(str(path))
    return '\\\\?\\' + p if os.name == 'nt' and not p.startswith('\\\\?\\') and len(p) > 240 else p


def sha256_file(path):
    h = hashlib.sha256()
    with open(lp(path), 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def read_json(path, default=None):
    try:
        with open(lp(path), 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp%d' % os.getpid())
    with open(lp(tmp), 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(lp(tmp), lp(path))


def make_logger(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    def log(msg):
        line = '%s [pid=%d] %s' % (kst(), os.getpid(), msg)
        with open(lp(path), 'a', encoding='utf-8') as f:
            f.write(line + '\n')
        print(line, flush=True)
    return log


def blind_guard(*names):
    for n in names:
        s = str(n).lower().replace('\\', '/')
        for t in BLIND_TOKENS:
            if t in s:
                raise SystemExit('BLIND_GUARD: refused name %r (token %r)' % (n, t))


def provenance_seed(run_dir):
    """Seed of a run from its run_provenance JSON field `seed` (never from the folder name)."""
    run_dir = Path(run_dir)
    provs = sorted(run_dir.glob('run_provenance_*.json'))
    if len(provs) != 1:
        raise SystemExit('expected one run_provenance file in %s, found %d' % (run_dir, len(provs)))
    doc = read_json(provs[0])
    seed = doc.get('seed') if isinstance(doc, dict) else None
    if not isinstance(seed, int):
        raise SystemExit('run_provenance has no integer seed: %s' % provs[0])
    return seed, provs[0], sha256_file(provs[0])


# ------------------------------------------------------------------------------------------------ shared LOCK
def lock_acquire(job, log=print, poll_sec=2.0):
    """Exclusive create of the shared heavy-job LOCK.  Our own previous release must be >= 20 s ago, so that other
    workflows waiting on the LOCK get a turn.  Waits while another owner holds it."""
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    t0, said = time.time(), -1e9
    while True:
        # Every attempt (also after waiting on someone else's lock) respects our own last release + pause.
        last = read_json(LAST_RELEASE, {}) or {}
        gap = time.time() - float(last.get('epoch', 0.0))
        if gap < RELEASE_PAUSE_SEC:
            time.sleep(RELEASE_PAUSE_SEC - gap)
            continue
        try:
            with open(LOCK, 'xb') as f:
                f.write(json.dumps({'owner': 'vsl_plant', 'pid': os.getpid(), 'started_kst': kst(),
                                    'job': job}).encode('utf-8'))
            log('LOCK_ACQUIRED job=%s waited_sec=%.0f' % (job, time.time() - t0))
            return time.time() - t0
        except FileExistsError:
            waited = time.time() - t0
            if waited - said >= 540:
                try:
                    holder = LOCK.read_text(encoding='utf-8', errors='replace')[:200]
                except OSError:
                    holder = '?'
                log('LOCK_BUSY job=%s waited_sec=%.0f holder=%r' % (job, waited, holder))
                said = waited
            time.sleep(poll_sec)


def lock_release(log=print):
    try:
        doc = json.loads(LOCK.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        log('LOCK_RELEASE: no readable lock (nothing removed)')
        return False
    if doc.get('owner') == 'vsl_plant' and doc.get('pid') == os.getpid():
        LOCK.unlink()
        write_json(LAST_RELEASE, {'epoch': time.time(), 'kst': kst(), 'pid': os.getpid()})
        log('LOCK_RELEASED')
        return True
    log('LOCK_RELEASE: lock is not ours (%r); not removed' % doc)
    return False


# ------------------------------------------------------------------------------------------------ children
def child_env(numba_dir, hook_dir=None):
    """K9-2 replay environment (k92/bundle1/a25decl/tools/k92lib.py child_env, D-K9-99): NUMBA_NUM_THREADS removed,
    BLAS threads 1, PYTHONHASHSEED 0, python -B.  hook_dir: the passive worker hook (vp_hooks/sitecustomize.py)."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('RW_', 'K8_', 'K8G_', 'S31F_', 'GH1_', 'K92A_', 'C1P0_', 'VP_'))}
    env.update({'NUMBA_CACHE_DIR': str(numba_dir), 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1',
                'OPENBLAS_NUM_THREADS': '1', 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONHASHSEED': '0'})
    env.pop('NUMBA_NUM_THREADS', None)
    if hook_dir:
        env['VP_HOOK_DIR'] = str(hook_dir)
    return env


def run_capture(argv, log_path, env, cwd=None, timeout=None):
    t0 = time.time()
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(lp(log_path), 'w', encoding='utf-8', errors='replace') as out:
        rc = subprocess.run([str(a) for a in argv], stdout=out, stderr=subprocess.STDOUT, env=env,
                            cwd=str(cwd) if cwd else None, creationflags=BELOW_NORMAL, timeout=timeout).returncode
    return rc, time.time() - t0


def free_space_gb():
    import shutil
    return {d[0]: round(shutil.disk_usage(d).free / 1e9, 2) for d in ('C:\\', 'D:\\')}


def require_space(log):
    fs = free_space_gb()
    if any(v < 8.0 for v in fs.values()):
        log('LOW_SPACE %s (< 8 GB): STOP' % fs)
        raise SystemExit('LOW_SPACE %s' % fs)
    return fs


def set_below_normal():
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL('kernel32', use_last_error=True)
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    k32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k32.SetPriorityClass(k32.GetCurrentProcess(), BELOW_NORMAL)
