r"""V-A analysis common definitions (amendment 34 sec.8; J1 tools SP/j1/analysis/tools/an_*.py with run paths and
names changed).  Imported by the eight V-A analysis tools.  No computation here except helpers.

Profiles (every tool takes --profile):
  va        V-A arm = RVA runs sdmpc31_v3c3_k92va_s<S>; outputs AV/out, V-A scans AV/scans/va_s<S>.
            A tool refuses to run in this profile unless AV/va_analysis_pins.sha256 lists its own bytes and the
            method document (amendment 34 sec.8.0-2: pinned before the first V-A launch).
  selftest  V-A arm = the J1 runs (published J1 data), outputs AV/selftest/out, scans AV/selftest/scans.
            Used only to reproduce the J1 - NC3 tables (amendment 34 sec.8.0-2) before pinning.
J1 and NC3 scans are reused from SP/j1/analysis/scans after the sha256 prefix check of amendment 34 sec.8.1; a
mismatching one is rescanned with the same tool by va_scan.py into <profile scans>/<tag> and disclosed."""
import ctypes
import hashlib
import io
import json
import math
import os
import statistics
import sys
from ctypes import wintypes

sys.dont_write_bytecode = True
SP = r'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8'
VA = os.path.join(SP, 'k92', 'va')
AV = os.path.join(VA, 'analysis')
TOOLS = os.path.join(AV, 'tools')
PINS = os.path.join(AV, 'va_analysis_pins.sha256')
METHOD = os.path.join(AV, 'ANALYSIS_METHOD_VA.md')
STAGE1 = r'D:\VISSIM-merge\tools\stage1'
STAGE1_SHA = {
    'stage1_common.py': 'e000c69eebad2636c00299727ceb1624d408d5ac3c6ae26204301b1fa891fdae',
    'stage1_scan.py': '651c4f51fdddf49d46c77ed4c28b0626c410b3282426b9fd30f2a6ef43f7625f',
    'stage1_uninserted.py': '19eba94ed01bce47b591b47362aba13b2ac697cfbf2cb9156954b573e7727cd1',
    'stage1_report.py': 'cb4ccc3a431f32ebb6f716a0b67c148a71d82470c443b4851f80832d98d7a1b9',
}
RVA = r'D:\VISSIM_runs\20261023_sdmpc31_k92'
RR = r'D:\VISSIM_runs\20261004_sdmpc31_k8'
NCROOT = r'D:\VISSIM_runs\20261001_v3c3'
SEEDS = (31, 41, 43)
VA_NAMES = {s: 'sdmpc31_v3c3_k92va_s%d' % s for s in SEEDS}
J1_NAMES = {31: 'sdmpc31_v3c3_k8j1r_s31', 41: 'sdmpc31_v3c3_k8j1_s41', 43: 'sdmpc31_v3c3_k8j1_s43'}
J1_SCANS = os.path.join(SP, 'j1', 'analysis', 'scans')
# amendment 34 sec.8.1: (scan.json, uninserted.json) sha256 first 16 hex
J1_SCAN_SHA16 = {
    'j1_s31': ('4eb525ddbc8f3ff1', '34fb9bc6885364e5'), 'j1_s41': ('645f1861d1f3a47c', 'ac94e55d91a97238'),
    'j1_s43': ('35a3b79504740837', '9813298b609dc7bd'), 'nc3_s31': ('9419b0bc31e2ab18', '3490c88ccd16175a'),
    'nc3_s41': ('fd103d4362a809ba', '94f93c9193aa7014'), 'nc3_s43': ('3d946a0fa489a46a', 'f2baaeddae324156'),
}
LINK_SETS = (r'D:\VISSIM-merge\review-d80faf9\diagnostics\vsl_handoff_20260924\evidence\accounting'
             r'\east_link_sets_source.json')
FZP_SKIP = b'0.10;'          # runner FZP 0.10 s row (K7 sec.3.6), skipped by a read-only shim
T2 = 2.920                   # t0.95(2), K8 sec.5.5
T_ACT = 900.0
NOISE = {'M1': (104, 175), 'M2': (115, 194), 'M3': (102, 172), 'M3u': (8, 13), 'M4': (63, 106)}
G_K5_BUDGET = 1.0158         # amendment 34 sec.8.3-9, report only
P3_THRESHOLD = 24.5          # V-B sec.6-1 / J1 definition (s)
LINK174_CHAIN = (21, 10112, 174, 10280, 10281, 173)
EAST_LINKS = (1220000704, 1220000803)   # SC109 east approach (SG6) / west through exit, both outside Omega
LABEL_SAME = '같은 방향(K8 §5.5 표시 조건 충족, 판정 아님)'
LABEL_MOVED = '대기 이전(Ω 밖으로)'
LABEL_NA = '해당 없음(Ω 감소 아님)'


class Profile(object):
    def __init__(self, name):
        if name not in ('va', 'selftest'):
            raise SystemExit('profile must be va or selftest')
        self.name = name
        if name == 'va':
            self.out = os.path.join(AV, 'out')
            self.scans = os.path.join(AV, 'scans')
            self.va_root, self.va_names = RVA, dict(VA_NAMES)
        else:
            self.out = os.path.join(AV, 'selftest', 'out')
            self.scans = os.path.join(AV, 'selftest', 'scans')
            self.va_root, self.va_names = RR, dict(J1_NAMES)
        os.makedirs(self.out, exist_ok=True)
        os.makedirs(self.scans, exist_ok=True)

    def va_run(self, seed):
        return runner_run(self.va_root, self.va_names[seed])


def profile_from_argv(argv=None):
    argv = sys.argv if argv is None else argv
    name = 'va'
    if '--profile' in argv:
        name = argv[argv.index('--profile') + 1]
    return Profile(name)


def runner_run(root, name):
    rd = os.path.join(root, name)
    dec = os.path.join(rd, 'decisions_' + name)
    return {'name': name, 'run_dir': rd, 'dec': dec, 'obs150': os.path.join(dec, 'obs150'),
            'fzp': os.path.join(rd, 'vissim_eval', 'sdmpc31_%s_001.fzp' % name),
            'inpx': os.path.join(rd, 'network', 'sdmpc31_%s.inpx' % name),
            'err': os.path.join(rd, 'network', 'sdmpc31_%s_001.err' % name),
            'err_root': os.path.join(rd, 'vissim_simulation_001.err'),
            'runlog': os.path.join(rd, 'runlog_%s.txt' % name),
            'launch': os.path.join(rd, 'launch_%s.log' % name),
            'action_csv': os.path.join(rd, 'action_%s.csv' % name),
            'provenance': os.path.join(rd, 'run_provenance_%s.json' % name),
            'wmi': os.path.join(root, 'wmi_%s.log' % name)}


def j1_run(seed):
    return runner_run(RR, J1_NAMES[seed])


def nc3_run(seed):
    rd = os.path.join(NCROOT, 's%d_v3c3nc' % seed, 'run')
    return {'name': 'baseline_s%d_v3c3nc' % seed, 'run_dir': rd,
            'fzp': os.path.join(rd, 'vissim_eval', 'baseline_s%d_v3c3nc_001.fzp' % seed),
            'err': os.path.join(rd, 'baseline_s%d_v3c3nc_001.err' % seed)}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def set_below_normal():
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.GetCurrentProcess.restype = wintypes.HANDLE
    k.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k.SetPriorityClass.restype = wintypes.BOOL
    k.GetPriorityClass.argtypes = [wintypes.HANDLE]
    k.GetPriorityClass.restype = wintypes.DWORD
    h = k.GetCurrentProcess()
    k.SetPriorityClass(h, 0x00004000)
    return k.GetPriorityClass(h)


def jload(p):
    with io.open(p, encoding='utf-8-sig') as f:
        return json.load(f)


def jdump(o, p):
    tmp = p + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8') as f:
        json.dump(o, f, indent=1, ensure_ascii=False, default=_default)
    os.replace(tmp, p)


def _default(o):
    try:
        import numpy as np
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
    except ImportError:
        pass
    if isinstance(o, (set, tuple)):
        return list(o)
    return str(o)


def require_pinned(prof, script_path):
    """va profile only: the method document and this script must be listed in the pin file with their bytes."""
    if prof.name != 'va':
        return {'pinned': False, 'profile': prof.name}
    if not os.path.isfile(PINS):
        raise SystemExit('va profile refused: pin file missing (method and tools must be pinned first)')
    want = {}
    with io.open(PINS, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            h, name = line.split(None, 1)
            want[os.path.normcase(os.path.abspath(name.lstrip('*')))] = h
    for p in (METHOD, os.path.abspath(script_path), os.path.abspath(__file__)):
        k = os.path.normcase(os.path.abspath(p))
        if k not in want or sha(p) != want[k]:
            raise SystemExit('va profile refused: %s not pinned or changed' % p)
    return {'pinned': True, 'pins_sha256': sha(PINS)}


def j1_scan_dir(prof, tag):
    """SP/j1 scan folder if both sha16 prefixes match amendment 34 sec.8.1, else the profile rescan folder."""
    d = os.path.join(J1_SCANS, tag)
    want = J1_SCAN_SHA16[tag]
    try:
        ok = (sha(os.path.join(d, 'scan.json'))[:16] == want[0] and sha(os.path.join(d, 'uninserted.json'))[:16] == want[1])
    except OSError:
        ok = False
    if ok:
        return d, True
    return os.path.join(prof.scans, tag), False


def scan_dir(prof, tag):
    if tag.startswith('va_'):
        return os.path.join(prof.scans, tag)
    return j1_scan_dir(prof, tag)[0]


def stats(vals, ncs):
    """J1 an_metrics.stats: mean, sd (n-1), 90 % CI = mean +- 2.920 sd / sqrt(3), strict sign counts, pct of NC mean."""
    n = len(vals)
    m = statistics.fmean(vals)
    sd = statistics.stdev(vals) if n > 1 else float('nan')
    half = T2 * sd / math.sqrt(n) if n > 1 else float('nan')
    ncm = statistics.fmean(ncs)
    lo, hi = m - half, m + half
    return {'n': n, 'mean': m, 'sd': sd, 'half90': half, 'ci90': [lo, hi],
            'ci_excludes_0': bool(lo > 0 or hi < 0),
            'neg': sum(1 for v in vals if v < 0), 'pos': sum(1 for v in vals if v > 0),
            'nc_mean': ncm, 'pct_of_nc': 100.0 * m / ncm if ncm else None,
            'per_seed_pct': [100.0 * v / c if c else None for v, c in zip(vals, ncs)]}


def label(dd):
    """Amendment 34 sec.8.4 (= K8 sec.5.5, J1 method 2.5): only where d(3) < 0.  N: d(4) <= 0 and d(4-3) <= 0.
    W: N and d(4b) <= 0 and d(removals) <= 0, removals by reading A (W_A) and reading B (W_B) separately."""
    if dd['M3'] >= 0:
        return {'N': LABEL_NA, 'W_A': LABEL_NA, 'W_B': LABEL_NA}
    n_ok = dd['M4'] <= 0 and dd['OUT_a'] <= 0
    wa = n_ok and dd['M4b'] <= 0 and dd['REM'] <= 0
    wb = n_ok and dd['M4b'] <= 0 and dd['REM_B'] <= 0
    return {'N': LABEL_SAME if n_ok else LABEL_MOVED, 'W_A': LABEL_SAME if wa else LABEL_MOVED,
            'W_B': LABEL_SAME if wb else LABEL_MOVED}


def action_files(dec):
    import glob
    out = []
    for p in sorted(glob.glob(os.path.join(dec, 'action_[0-9][0-9][0-9][0-9][0-9][0-9].json'))):
        out.append((int(os.path.basename(p)[7:13]), p))
    return out


def load_json_bytes(p):
    with open(p, 'rb') as f:
        return json.loads(f.read())


def import_stage1():
    for n, want in STAGE1_SHA.items():
        if sha(os.path.join(STAGE1, n)) != want:
            raise SystemExit('stage1 tool %s sha mismatch' % n)
    if STAGE1 not in sys.path:
        sys.path.insert(0, STAGE1)
    import stage1_common as C
    C.find_rule_policy = lambda run_dir: None   # never glob sibling (sealed-seed) folders
    return C
