"""C1 P0 / mini-probe scratch helpers (K8 amendment C1 a98580dd...; sections 3-5).  Never committed.
Writes only under TC1 (D:/VISSIM-merge/k8_gate_trees/c1), C1D (scratchpad k8/c_port/c1) and RC1 (report copies).
Read only: GWT8 (git show / git archive), CX, FRZ_B1, run folders, frozen trees.  BLIND: nothing here prints an
objective / prediction value; v3c3-s47 is never opened."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
SP = Path(r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/'
          r'491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8')
CP = SP / 'c_port'
C1D = CP / 'c1'
TOOLS = C1D / 'tools'
DECL = C1D / 'declared'
TC1 = Path(r'D:/VISSIM-merge/k8_gate_trees/c1')
RC1 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/c_port/c1')
LOCK = Path(r'D:/VISSIM-merge/k8_gate_trees/heavy.lock')
GWT8 = Path(r'D:/VISSIM-merge/sim3-n31-k8')
REV = 'c20aff1d7bf0c432cb4f20e2922bd406d857aa5d'
CX = Path(r'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff')
FRZ_B1 = Path(r'D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1/frozen/sdmpc31_a49981ff_202610261410')
B0F = FRZ_B1 / 'diagnostics' / 'b0_v3c3'
FRZ_VA = Path(r'D:/VISSIM-merge/frozen/sdmpc31_c20aff1d_202610230833')
REPLAY_TOOLS = FRZ_VA / 'diagnostics/sdmpc_n31_20260924/tools'
GPREP = SP / 'j1' / 'fix' / 'gates' / 'gprep.py'
GPREP_SHA = '0482a53868fd3ee644724dab2dcb6af2c56d749708ccec5242f6b3549ae26f22'
MRS_SHA = '4adf41cfa7569047d87774bb648b353780fbb7ffc9b916a9c8f726e1d1de0714'
RUNS = {'va': Path(r'D:/VISSIM_runs/20261023_sdmpc31_k92'), 'robs': Path(r'D:/VISSIM_runs/20261001_sdmpc31_v3c3'),
        'b': Path(r'D:/VISSIM_runs/20261026_codex_b_v3c3')}
N31 = 'diagnostics/sdmpc_n31_20260924'
OUC_REL = N31 + '/config_n31_v2.json'
OUC_SHA = 'c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866'
AMEND_SHA = 'a98580dd2d787007ab961d692668c4a4042c79d7993f87af972cbc19d1f53acf'
TOKEN_OFF = '428e650ded2f1cb8bb4365abac76ea9765da4783d19e8c2dab1bcd7b688399f9'
PY = r'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
DEPROOT = r'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps'
BELOW_NORMAL = 0x00004000
METERS = ('RM_C10480', 'RM_C10482', 'RM_C10484', 'RM_C10490', 'RM_C10639', 'RM_C10644', 'RM_C10646', 'RM_C10681')
FWE = ('RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484')
FWW = ('RM_C10480', 'RM_C10482', 'RM_C10646', 'RM_C10644')
BLIND_TOKENS = ('nc_s47', 'v3c3-s47', '_s47', 's47_')
PATTERN = ('vissim_stackelberg_adapter', 'make_replay_state', 'replay_decision', 'sdmpc_tangent_worker',
           'run_sdmpc_n31', 'run_real_world_stackelberg', 'cap_child', 'sa_capture', 'sa_worker', 'k92_replay',
           'c1_p0_child', 'c1_probe', 'c1_p0')


def sha256_file(path):
    h = hashlib.sha256()
    with open(lp(path), 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def lp(p):
    s = os.path.abspath(str(p))
    return s if s.startswith('\\\\?\\') else '\\\\?\\' + s


def data(x):
    """codex prepare_next.py:11 serialisation."""
    return (json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf8')


def canon_sha(x):
    return sha256_bytes(json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                                   allow_nan=False).encode('utf8'))


def git_show(rel):
    r = subprocess.run(['git', '-C', str(GWT8), 'show', REV + ':' + rel], capture_output=True)
    if r.returncode:
        raise SystemExit('git show failed: ' + rel)
    return r.stdout


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return default


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp%d' % os.getpid())
    tmp.write_text(json.dumps(obj, indent=1, default=str, ensure_ascii=False), encoding='utf-8')
    os.replace(tmp, path)


def write_new(path, payload):
    """Exclusive create (never overwrite)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'xb') as f:
        f.write(payload if isinstance(payload, bytes) else payload.encode('utf-8'))
    return sha256_file(path)


def deep_diff(x, y, p=''):
    """K7 gb_common.deep_diff convention (amendment C1 section 2.2 RV-7)."""
    out = []
    if isinstance(x, dict) and isinstance(y, dict):
        for k in sorted(set(x) | set(y)):
            if k not in x or k not in y:
                out.append(p + '/' + k)
            else:
                out += deep_diff(x[k], y[k], p + '/' + k)
    elif isinstance(x, list) and isinstance(y, list):
        if len(x) != len(y):
            out.append(p)
        else:
            for i, (u, v) in enumerate(zip(x, y)):
                out += deep_diff(u, v, p + '/%d' % i)
    elif x != y or type(x) is not type(y):
        out.append(p)
    return out


def kst():
    return time.strftime('%Y-%m-%d %H:%M:%S')


def make_logger(path, prefix=''):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    def log(msg):
        line = time.strftime('%Y-%m-%dT%H:%M:%S ') + prefix + msg
        with open(path, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
        print(line, flush=True)
    return log


def log_md(text):
    with open(C1D / 'LOG.md', 'a', encoding='utf-8') as f:
        f.write('\n- [%s KST, 자동] %s\n' % (kst(), text))


def free_space_gb():
    return {d[0]: round(shutil.disk_usage(d).free / 1e9, 2) for d in ('C:\\', 'D:\\')}


def require_space(log=print):
    fs = free_space_gb()
    if any(v < 8.0 for v in fs.values()):
        log('LOW_SPACE %s (< 8 GB): STOP (S-C1-14)' % fs)
        raise SystemExit('LOW_SPACE %s' % fs)
    return fs


def set_below_normal():
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL('kernel32', use_last_error=True)
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    k32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k32.GetPriorityClass.argtypes = [wintypes.HANDLE]
    k32.GetPriorityClass.restype = wintypes.DWORD
    h = k32.GetCurrentProcess()
    k32.SetPriorityClass(h, BELOW_NORMAL)
    if k32.GetPriorityClass(h) != BELOW_NORMAL:
        raise SystemExit('priority read-back is not BELOW_NORMAL')


def vissim_count():
    try:
        out = subprocess.run([PS, '-NoProfile', '-Command',
                              '@(Get-Process -Name VISSIM* -ErrorAction SilentlyContinue).Count'],
                             capture_output=True, text=True, timeout=120)
        return int(out.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        return None


# ------------------------------------------------------------------------------------------------ shared LOCK
def lock_acquire(job, log=print, poll_sec=2):
    """Exclusive create of the shared heavy-job LOCK (amendment C1 section 3); waits while another owner holds it."""
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    waited, last = 0.0, -1e9
    t0 = time.time()
    while True:
        try:
            with open(LOCK, 'xb') as f:
                f.write(json.dumps({'owner': 'c1', 'pid': os.getpid(), 'started_kst': kst(), 'job': job}).encode('utf-8'))
            log('LOCK_ACQUIRED job=%s waited_sec=%.0f' % (job, time.time() - t0))
            return time.time() - t0
        except FileExistsError:
            waited = time.time() - t0
            if waited - last >= 540:
                try:
                    holder = LOCK.read_text(encoding='utf-8', errors='replace')[:200]
                except OSError:
                    holder = '?'
                log('LOCK_BUSY job=%s waited_sec=%.0f holder=%r' % (job, waited, holder))
                last = waited
            time.sleep(poll_sec)


def lock_release(log=print):
    try:
        doc = json.loads(LOCK.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        log('LOCK_RELEASE: no readable lock (nothing removed)')
        return False
    if doc.get('owner') == 'c1' and doc.get('pid') == os.getpid():
        LOCK.unlink()
        log('LOCK_RELEASED')
        return True
    log('LOCK_RELEASE: lock is not ours (%r); not removed' % doc)
    return False


# ------------------------------------------------------------------------------------------------ children
def child_env(numba_dir, extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('RW_', 'K8_', 'K8G_', 'S31F_', 'GH1_', 'K92A_', 'C1P0_'))}
    env.update({'NUMBA_CACHE_DIR': str(numba_dir), 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1',
                'OPENBLAS_NUM_THREADS': '1', 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONHASHSEED': '0'})
    env.pop('NUMBA_NUM_THREADS', None)
    env.update(extra or {})
    return env


def env_hsw(env):
    """A0_PROFILE / PRE_A1 U1 (b): exactly three variables."""
    env = dict(env)
    env.update({'OPENBLAS_CORETYPE': 'Haswell', 'NPY_DISABLE_CPU_FEATURES': 'AVX512F AVX512CD AVX512_SKX AVX512_CLX',
                'NUMBA_CPU_NAME': 'haswell'})
    return env


def run_capture(argv, log_path, env, cwd=None, timeout=None):
    t0 = time.time()
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8', errors='replace') as out:
        rc = subprocess.run([str(a) for a in argv], stdout=out, stderr=subprocess.STDOUT, env=env,
                            cwd=str(cwd) if cwd else None, creationflags=BELOW_NORMAL, timeout=timeout).returncode
    return rc, time.time() - t0, Path(log_path).read_text(encoding='utf-8', errors='replace')


def text_count(path, needle):
    try:
        return Path(path).read_text(encoding='utf-8', errors='replace').count(needle)
    except OSError:
        return None


def blind_guard(*names):
    for n in names:
        s = str(n).lower()
        if any(t in s for t in BLIND_TOKENS):
            raise SystemExit('BLIND_GUARD: v3c3-s47 is closed before c1t (amendment C1 section 9): %r' % (n,))
