"""K9-2 V-B chain driver (K8_PREDECLARATION_AMENDMENT_32 section 4; amendment 24 section 14.1 as changed by
amendments 27 section 6.2, 29 section 6.2, 31 section 4.4 and 32).  Scratch tool, never committed.

    python -B vb_chain.py selftest     synthetic self-tests, no child process -> KV/selftest/vb_selftest.json
    python -B vb_chain.py chain        V0 .. V10 (one detached run: KI/launch.ps1 -Tag vb_chain)

Writes only (guard()): VBR = OK2/vb, TK/vb_e27ceac8 and TK/vb_e27ceac8.build.json (V1 only), KV, KB/LOG.md (append),
OK2/snap/s38-s41_vb_*.json (snapshot child), OK2/logs/vb_* (launcher).  Read only: RR, FRZ_K8 / FRZ_K8b, GWT8 (git
read only), AD32, KI.  No VISSIM, no COM, no runner, no commit / push.  The adapter children write their own tangent
cache under VBT/evaluation/controllers/__tangentcache__ (as every earlier TK-tree replay) and obs150/derived_<T>.json
in their prepared folder (VBR).
Launch rule (section 4.3): the argument list / order, the environment and the working folder of k92_replay.py
(blob 822dd78f, VBT copy) -- differences only: the output paths and, for chained decisions, the previous action.
Stdout of this driver: stage names, verdict words, counts and sha only (metric values go to VBR/judge files)."""
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import types
from pathlib import Path

sys.dont_write_bytecode = True
SP = Path(r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/'
          r'491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8')
KB = SP / 'k92' / 'bundle1'
KV = KB / 'k92_vb'
KI = KB / 'impl'
AD32 = KB / 'a32decl'
HOOKDIR = AD32 / 'vbhook'
sys.path.insert(0, str(KI))
import k92lib as L  # noqa: E402
import cglib as G  # noqa: E402

TK = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1')
VBT_NAME = 'vb_e27ceac8'
VBT = TK / VBT_NAME
VBT_BUILD = TK / (VBT_NAME + '.build.json')
OK2 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1')
VBR = OK2 / 'vb'
RR = Path(r'D:/VISSIM_runs/20261004_sdmpc31_k8')
FRZ7 = Path(r'D:/VISSIM-merge/frozen')
FRZ8 = Path(r'D:/VISSIM-merge/frozen/sdmpc31_74cd495f_202610131824')
FRZ8B = Path(r'D:/VISSIM-merge/frozen/sdmpc31_b9734abe_202610141821')
GWT8 = Path(r'D:/VISSIM-merge/sim3-n31-k8')
REPO = Path(r'D:/VISSIM-merge/repo')
K92ATTRIB = Path(r'D:/VISSIM-merge/k8_gate_trees/k92attrib')
DA = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_attrib')
V4 = Path(r'D:/VISSIM-merge/k8_gates_out_v4')
OUTH = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/offline_gates_k8h')
OUTK = OK2 / 'k92t'
SEALED = OK2 / 'sealed_s47'
DEP = r'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps'
N31 = 'diagnostics/sdmpc_n31_20260924'
SA_REL = N31 + '/k8_gates/sa'
PY = L.PY
BELOW_NORMAL = 0x00004000
STALL_SEC = 30 * 60
NC_CAP_SEC = 30 * 60

HEAD = 'e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d'
K8_HEAD = 'b9734abe1c83f95c9cec5fca5e42b7b18cd45991'
BRANCH = 'claude/k92-b1-20261016'
K8_BRANCH = 'claude/k8-sc1001eb-defects-20261004'

# ---------------------------------------------------------------------------------------------- pins (amendment 32)
A_SHA = {24: 'd46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc',
         25: '4fd7b599fe0f6131143e911dd3ab2be264a175e3f90b185bade9482d60b9ff8e',
         26: '8f8356168a299c07960d86ef12aa9f7af6f2f040af08ba75e5233a5819edba37',
         27: '4ce8b27a2ebf08aa0e8ac3f647b4e4336a98f7be7ec8d6f006a0fd1d12005a13',
         28: '9881eb40c1129af0cdff48026dc8656b4235d43f0eb80566e4be9b66d9ac345e',
         29: '4bd6dc8de8b0a4a4ab0b8703c07d7a73d244c4a622b81585f06dc69d6d83599d',
         30: 'ba556227a6356b1733bfa8125b334cfef180c1eed97e8d69ae4ba53a3106a56a',
         31: '8541ccb7fa6c951b4affcca67d57e25be09b061c3ae3dd006d050c9c6413e304'}
F_SHA = {24: 'fbc3d59fe2e47fec00d87262d624aa9a163ed02e113609b06173841397df101a',
         25: 'd1338fbc40a2efaf6997667f59e7bd709951e1fd3f2b1a8a0a0881794c3d24ed',
         26: '6edc55acd5aa0976701456d956e33f33c52ae0853535f6a4d8cb8bf26a354581',
         27: '394ab15fdea0d945a3b766c208e692ee7e1086fca3c178f6b423079d71fedcdb',
         28: '14451cf4d46c5c0095bc896134112148ba5700ee70b2ed78b8ee38d0e62e20e5',
         29: '3ba1d0bdaab8a0189f903d10fc1024baed770080542cbd841f79d3a56df58e43',
         30: 'ad3fafadd59985b3b71f33d5523ceb2324aa8267395d7280039228669cb83e9c',
         31: '605ccbd2cb392ac2ed0a6da1d27c20e93aa68fcac50ec6d99c4393236f98a053'}
A32 = SP / 'K8_PREDECLARATION_AMENDMENT_32.md'
A32_SHA = '7f25c21e72fc2599022c72adb1976257413a8486f4898ffcec61f3c6b01423e7'
A32_DECLARE_SHA = '176ded8997b53206b320b15efb3c92b79de2b256ee8293acbd41c1dabbd36e52'
FIXED32 = KB / 'AMENDMENT32_FIXED.md'
FIXED32_SHA = 'b59088ab44683f5990f2a44038c688aec59a21fcb5207e72b0bc7ee5782ddef4'
NOTES = SP / 'K9_1_J1_NOTES_20261013.md'
NOTES_204_SHA = '402eaf59aa738bef1dcb27f41d51eba873a8cb6abdbfde7707dfc6b146cfbd3b'
EXPECTED_PINS = AD32 / 'a32_pins.expected.sha256'
EXPECTED_PINS_SHA = '9e4dc5925e36fcc092f1b4ace4c3e86600d8f96422f3720653fe7d72d4514fcb'
A32_PINS = KB / 'a32_pins.sha256'
VB_PINS = KV / 'vb_pins.sha256'
A31_PINS = KB / 'a31_pins.sha256'
GATES_REC = {KB / 'GATES_K92B1_A31.md': 'e2b301837feb35d652d0db088d634e07449676abd01cb0e8b2dfef6eff232885',
             KB / 'VERIFY_GATES_K92B1_r3.md': '6fb66ac5b8de8bbd00df420bc3b1bf5364e5f95148574dd2834204e3df3ac189',
             KB / 'vgates4' / 'out' / 'vg4_result.json':
                 '0b7654eca9e1165fad42ebe59b28bde91598d0b183f0cf694a21ba09a398b603'}
GATES_MD_NOW = '449b361e96d047156e63f73bcdae905ec61408b9a5f9be047629092d3ab0a792'
HOOK_SHA = '4d7e0375116c3f805aa223651da0dc1c0c04b7d3315062e98e21137ba60aa321'
SELECT_SHA = '33adfd5033c277a3ad640f745a69efb2a929b27c1ff2a88d794dfa69b489e9cc'
LIB_SHA = '504999a196a9e08582f303d4ad38d4cc661fcfc765df62d11bc4cc7c05ddc75f'
CLOSED_SHA = 'b800be45ae3e4e5030ed31ecd221e6288d52c2a287bdeaa5efee243e3cc2f426'
REC_SHA = '1d1dfa36efbfa68e6ccc19cbeeb53f241437b1c5145e06fb843a9564661d4f90'
KC_SHA = '3e2da987ff9e7b54ba2f51ad1b73bfdaf55f868bd6dedbf7937cf1f22fa4caba'
KR_SHA = '822dd78ffde70e07baebf83e948d72ed3f82ab71107920b02a05ee8783a1b965'
ARMS_SHA = '578a8707dff89b2020124eca2928121bae075c81d41d3a1bfbe30ea8a25299b1'
A27M_SHA = 'd4ab3f3d4e91492e02f1b7c30807ad34744c3e7590cf890bcc1275c79baa00f5'
RS_SHA = '70cca680ef9f5dd84ee506ff8857712466f3779039289ca79adadc3d8f1eceba'
SHO_SHA = 'a6b5931ee3c4b04eacb023a0f7c29ac0f50cb1e955e9577f09ff7b5162680443'
CFG_SHA = 'd0f9ef395d4f9c51e6c68412f7c33abd546217e0d8cdc59d3c620183fa7aaec6'
SAFK91_SHA = '5f0d0e40a39e44b3c7601f23177afbad8c2eee23d4421626482f2244a86c3341'
CFGB1_SHA = 'c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866'
SAFB1_SHA = '65cac7ea0b33d8f0b5c8efc458307578bcae7a2e34d1d097ce448a18a65ada28'
K92_VALUES = KB / 'k92_probe_a25' / 'K92_VALUES.json'
K92_VALUES_SHA = '296c659562e45528606599aa4df99535faa694a86533ffca6bb2fbcde7db975a'
GPREP = SP / 'j1' / 'fix' / 'gates' / 'gprep.py'
GPREP_SHA = '0482a53868fd3ee644724dab2dcb6af2c56d749708ccec5242f6b3549ae26f22'
SNAP = KI / 'k92snap.py'
SNAP_SHA = '0dbd7d2c75f982d867eff46f27b1c2d8fbf34301d39952bdc87ebd7a0c8beeff'
SNAP_BASE = OK2 / 'snap' / 's02_after_probe_stop.json'
SEED = 1045.1612903225805
SEED_REPR = '1045.1612903225805'
FLOOR_PREFIX = 'head_discharge_floor_173_p4_'
CFG_REL = N31 + '/config_n31_v2.json'
SAFK91_REL = N31 + '/config_n31_v2_stopline_observed_full_k91.json'
CFGB1_REL = N31 + '/config_n31_v2_k92b1.json'
SAFB1_FILE = 'config_n31_v2_stopline_observed_full_k91_k92b1.json'
ARM_KEYS = ['/urban/capacity/head_floor_seed', '/urban/sc109w_through_saturation']

T3000 = list(range(3000, 4501, 150))
TW = [1, 150, 300, 450, 600, 750, 900, 1050]
CHAINS = {
    'VB-31': {'key': 'vb31', 'run': 'sdmpc31_v3c3_k8j1r_s31', 'seed': 31, 'old_root': FRZ8B, 'times': T3000,
              'off_times': [3000, 3150], 'off': ('VBT', CFG_REL, CFG_SHA), 'b1': ('VBT', CFGB1_REL, CFGB1_SHA)},
    'VB-43': {'key': 'vb43', 'run': 'sdmpc31_v3c3_k8j1_s43', 'seed': 43, 'old_root': FRZ8, 'times': T3000,
              'off_times': [3000, 3150], 'off': ('VBT', SAFK91_REL, SAFK91_SHA),
              'b1': ('VBR', 'arms/sa/tuning/' + SAFB1_FILE, SAFB1_SHA)},
    'VB-41': {'key': 'vb41', 'run': 'sdmpc31_v3c3_k8j1_s41', 'seed': 41, 'old_root': FRZ8, 'times': T3000,
              'off_times': [3000, 3150], 'off': ('VBT', SAFK91_REL, SAFK91_SHA),
              'b1': ('VBR', 'arms/sa/tuning/' + SAFB1_FILE, SAFB1_SHA)},
    'VB-41w': {'key': 'vb41w', 'run': 'sdmpc31_v3c3_k8j1_s41', 'seed': 41, 'old_root': FRZ8, 'times': TW,
               'off_times': TW, 'off': ('VBT', SAFK91_REL, SAFK91_SHA),
               'b1': ('VBR', 'arms/sa/tuning/' + SAFB1_FILE, SAFB1_SHA)},
}
ORDER = ['VB-41w', 'VB-31', 'VB-43', 'VB-41']
ZI_CELLS = [('z1_off', 'sdmpc31_v3c3_k8j1_s43', 1050, 'off'), ('z1_b1', 'sdmpc31_v3c3_k8j1_s43', 1050, 'b1'),
            ('z2_b1', 'sdmpc31_v3c3_k8j1_s43', 750, 'b1')]
SELECT_OK = ('selected', 'no_candidate', 'no_match', 'match_conflict')
ADAPTER = 'vissim_stackelberg_adapter.py'


# ---------------------------------------------------------------------------------------------- small helpers
def sha(p):
    return L.sha256_file(p)


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%S')


def read_json(p, default=None):
    return L.read_json(p, default)


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def num(v):
    return float(v) if is_num(v) else None


def s6(T):
    return '%06d' % int(T)


def load_pinned(path, want, name):
    if sha(path) != want:
        raise SystemExit('pinned module differs: %s' % path)
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.__pinned_sha256__ = want
    return mod


# ---------------------------------------------------------------------------------------------- write guard (4.5-3)
class GuardError(Exception):
    pass


def _n(p):
    return os.path.normcase(os.path.abspath(str(p))).rstrip('\\')


def _inside(p, root):
    a, b = _n(p), _n(root)
    return a == b or a.startswith(b + '\\')


DENY = (RR, FRZ7, GWT8, REPO, K92ATTRIB, DA, V4, OUTH, OUTK, SEALED, AD32, KI)


def allowed(p, v1=False):
    if any(_inside(p, d) for d in DENY):
        return False
    if _inside(p, VBR) or _inside(p, KV):
        return True
    if _inside(p, VBT) or _n(p) == _n(VBT_BUILD):
        return bool(v1)
    if _n(p) == _n(KB / 'LOG.md'):
        return True
    q = Path(os.path.abspath(str(p)))
    if _n(q.parent) == _n(OK2 / 'snap'):
        return re.fullmatch(r's(38|39|40|41)_vb_[a-z0-9_]+\.json', q.name) is not None
    if _n(q.parent) == _n(OK2 / 'logs'):
        return q.name.startswith('vb_')
    return False


def guard(p, v1=False):
    if not allowed(p, v1):
        raise GuardError('write outside the declared V-B scope: %s' % p)
    return Path(p)


def wjson(p, obj):
    guard(p)
    guard(str(p) + '.tmp')
    L.write_json(p, obj)
    return sha(p)


def mkdir(p, exist_ok=True):
    guard(p)
    Path(p).mkdir(parents=True, exist_ok=exist_ok)
    return Path(p)


def rename(a, b):
    guard(a)
    guard(b)
    os.rename(L.lp(a), L.lp(b))


# ---------------------------------------------------------------------------------------------- environment
def base_env():
    env = L.child_env(VBR / 'numba_cache')
    for k in list(env):
        if k.upper().startswith('K92VB_'):
            env.pop(k)
    return env


def clean_env():
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith(('RW_', 'K8_', 'K8G_', 'K92A_', 'K92VB_'))}
    env.pop('PYTHONPATH', None)
    env.update(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
    return env


def hook_env(T, seed, label, hook_dir):
    return {'K92VB_HOOK_DIR': str(hook_dir), 'K92VB_RECORDER': str(VBT / SA_REL / 'k92_record.py'),
            'K92VB_RECORDER_SHA256': REC_SHA, 'K92VB_T': str(int(T)), 'K92VB_SEED': str(int(seed)),
            'K92VB_LABEL': label}


# ---------------------------------------------------------------------------------------------- launch rule (4.3)
class Refused(Exception):
    pass


def _rebase(p, run_root, root):
    if not p:
        return p
    full = os.path.abspath(p)
    base = os.path.abspath(run_root).rstrip('\\') + '\\'
    if full.lower().startswith(base.lower()):
        return os.path.join(str(root), full[len(base):])
    return p


def adapter_launch(prep_dir, root, tuning, out_json, out_csv, *, base, controller='', extra_pythonpath='',
                   prev_override=None, dep_root=DEP):
    """k92_replay.py:51-121 (blob 822dd78f) without running anything: (python, argv, cwd, env, ...).  Only the two
    output paths and (prev_override) the previous action differ from that launcher."""
    rd = Path(os.path.abspath(prep_dir))
    root = Path(os.path.abspath(root))
    m = json.loads((rd / 'replay_manifest.json').read_text(encoding='utf-8-sig'))
    if m.get('schema') != 'sdmpc31-replay-state/v1':
        raise Refused('unsupported replay manifest schema %s' % m.get('schema'))
    sec = int(m['sim_sec'])
    dec = Path(m['source_decisions'])
    run_dir = dec.parent
    run_name = re.sub(r'^decisions_', '', dec.name)
    prov = json.loads((run_dir / ('run_provenance_%s.json' % run_name)).read_text(encoding='utf-8-sig'))
    run_root = prov['workspace_root']
    prev = None
    if m.get('previous_sec') is not None:
        prev = str(dec / ('action_%06d.json' % int(m['previous_sec'])))
        for _k, v in (m.get('evidence', {}).get('previous') or {}).items():
            src = v['source']
            if not Path(src).is_file():
                raise Refused('previous action file vanished: ' + src)
            if hashlib.sha256(Path(src).read_bytes()).hexdigest() != v['sha256']:
                raise Refused('previous action file changed since prepare: ' + src)
        if not Path(prev).is_file():
            raise Refused('previous action missing: ' + prev)
    record_prev = prev
    if prev_override is not None:
        if prev is None:
            raise Refused('previous override for a decision without a previous action')
        prev = str(prev_override)
        if not Path(prev).is_file():
            raise Refused('chained previous action missing: ' + prev)
    if not controller:
        plan = json.loads((run_dir / 'launch_plan.json').read_text(encoding='utf-8-sig'))
        controller = plan['warmup_controller'] if sec < int(plan['control_start_sec']) else plan['controller']
    files = prov['files']
    mapping = _rebase(files['control_mapping']['path'], run_root, root)
    calibration = _rebase(files['calibration']['path'], run_root, root)
    runner_config = _rebase(files['generated_vbs_config']['path'], run_root, root)
    det = ''
    for line in Path(runner_config).read_text(encoding='utf-8', errors='replace').splitlines():
        mm = re.match(r'^\s*RW_DETECTOR_MAPPING_PATH\s*=\s*"(.*)"\s*$', line)
        if mm:
            det = mm.group(1)
    adapter = str(root / 'evaluation' / 'controllers' / 'vissim_stackelberg_adapter.py')
    tuning = os.path.abspath(str(tuning))
    for f in (tuning, mapping, calibration, adapter):
        if not Path(f).is_file():
            raise Refused('missing input: ' + f)
    a = [adapter, '--state-json', m['state']['replay'], '--out-action-json', str(out_json), '--out-action-csv',
         str(out_csv), '--mapping-json', mapping, '--controller', controller]
    if det:
        a += ['--detector-mapping-json', det]
    a += ['--calibration-json', calibration, '--tuning-json', tuning]
    if prev:
        a += ['--previous-action-json', prev]
    mode = str(prov['env'].get('RW_ADAPTER_MODE') or '')
    if mode:
        a += ['--mode', mode]
    env = {k: v for k, v in base.items() if not k.upper().startswith('RW_')}
    env.update({k: str(v) for k, v in prov['env'].items()})
    env['PYTHONPATH'] = dep_root + r'\sdmpc;' + dep_root + r'\sdmpc-numba'
    if extra_pythonpath:
        env['PYTHONPATH'] = extra_pythonpath + ';' + env['PYTHONPATH']
    env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONUTF8='1')
    python = str(prov['env'].get('RW_PYTHON') or '')
    if not python:
        raise Refused('provenance env lacks RW_PYTHON')
    return {'python': python, 'argv': [python, '-B'] + a, 'cwd': str(root), 'env': env, 'sec': sec,
            'controller': controller, 'prev': prev, 'record_prev': record_prev, 'manifest_previous_sec':
            m.get('previous_sec'), 'source_decisions': str(dec), 'run_name': run_name}


def run_watched(argv, cwd, env, stdout_p, stderr_p, progress_p, sdmpc, log, tag):
    guard(stdout_p)
    guard(stderr_p)
    t0 = time.perf_counter()
    killed = None
    with open(stdout_p, 'w', encoding='utf-8', errors='replace') as so, \
            open(stderr_p, 'w', encoding='utf-8', errors='replace') as se:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=so, stderr=se, creationflags=BELOW_NORMAL)
        last_size, last_change = -1, time.perf_counter()
        while True:
            try:
                rc = proc.wait(timeout=30)
                break
            except subprocess.TimeoutExpired:
                pass
            size = progress_p.stat().st_size if progress_p.is_file() else -1
            if size != last_size:
                last_size, last_change = size, time.perf_counter()
            stalled = (time.perf_counter() - last_change > STALL_SEC) if sdmpc else \
                (time.perf_counter() - t0 > NC_CAP_SEC)
            if stalled:
                log('STALL %s: killing own PID tree %d' % (tag, proc.pid))
                subprocess.run(['taskkill', '/T', '/F', '/PID', str(proc.pid)], capture_output=True)
                killed = {'pid': proc.pid, 'sec': round(time.perf_counter() - t0, 1), 'sdmpc': sdmpc}
                rc = proc.wait()
                break
    return rc, round(time.perf_counter() - t0, 1), proc.pid, killed


def text_count(p, needle):
    p = Path(p)
    if not p.is_file():
        return None
    return sum(needle in line for line in p.read_text(encoding='utf-8', errors='replace').splitlines())


def env_brief(env):
    return {'names': sorted(env), 'set': {k: env.get(k) for k in sorted(env) if k.startswith('K92VB_') or k in (
        'PYTHONPATH', 'PYTHONHASHSEED', 'NUMBA_CACHE_DIR', 'PYTHONUTF8', 'OMP_NUM_THREADS')}}


# ---------------------------------------------------------------------------------------------- plan (4.5-4)
def tuning_path(chain, arm):
    where, rel, want = CHAINS[chain][arm]
    return (VBT / rel if where == 'VBT' else VBR / rel), want


def plan():
    rows = []
    for arm in ('off', 'b1'):
        for chain in ORDER:
            c = CHAINS[chain]
            times = c['off_times'] if arm == 'off' else c['times']
            for i, T in enumerate(times):
                first = i == 0
                prevT = None if T == 1 else (T - 150 if first else times[i - 1])
                if first:
                    dtype = 'FIRST'
                elif T < 900:
                    dtype = 'NN'
                elif T == 900:
                    dtype = 'SN'
                else:
                    dtype = 'SS'
                tp, tw = tuning_path(chain, arm)
                rows.append({'chain': chain, 'key': c['key'], 'arm': arm, 'T': T, 'prev_T': prevT, 'first': first,
                             'dtype': dtype, 'run': c['run'], 'seed': c['seed'], 'old_root': str(c['old_root']),
                             'tuning': str(tp), 'tuning_sha256': tw,
                             'controller': 'no-control' if T < 900 else 'wu-link'})
    return rows


def chain_dir(row):
    return VBR / 'chain' / ('%s_%s' % (row['key'], row['arm']))


def rr_dec(run):
    return RR / run / ('decisions_' + run)


# ---------------------------------------------------------------------------------------------- judges (2.4, 2.5)
def files_of_T(dec_dir, T):
    tag = s6(T)
    return sorted(p.name for p in Path(dec_dir).iterdir() if p.is_file() and tag in p.name) \
        if Path(dec_dir).is_dir() else []


def floor_keys(md):
    return sorted(k for k in md if k.startswith(FLOOR_PREFIX))


def vbi2(doc, names, T, rc, df_count, *, exception=None):
    """Section 2.4 VB-I2 for one decision.  exception (VB-41w B1 T=150 only) = {'floor_key', 't1_doc'}."""
    md = doc.get('metadata') if isinstance(doc, dict) and isinstance(doc.get('metadata'), dict) else {}
    c = {'exit0': rc == 0,
         'no_hold_file': not [n for n in names if 'hold' in n.lower()],
         'no_error_file': not [n for n in names if n.endswith('.error.txt')],
         'no_decision_failed': df_count == 0,
         'controller_status_ok': md.get('controller_status') == 'ok',
         'no_exception_key': not [k for k in md if 'exception' in k.lower()],
         'snapshot_is_T': is_num(md.get('head_observation_snapshot_sec'))
         and float(md['head_observation_snapshot_sec']) == float(T)}
    pd = md.get('head_observation_prior_discarded')
    if exception is None:
        c['prior_discarded_0'] = is_num(pd) and float(pd) == 0.0
    else:
        key = exception['floor_key']
        t1md = (exception.get('t1_doc') or {}).get('metadata') or {}
        c['prior_discarded_exception'] = (is_num(pd) and float(pd) == 1.0 and is_num(md.get(key))
                                          and float(md[key]) == SEED and is_num(t1md.get(key))
                                          and float(t1md[key]) == SEED)
    return {'ok': all(c.values()), 'checks': c}


def vbi6(docs, floor_key, warm):
    """Section 2.4 VB-I6 for one B1 chain: docs = [(T, doc)] in T order."""
    vals, rows, ok = [], [], True
    for T, doc in docs:
        md = (doc or {}).get('metadata') or {}
        ks = floor_keys(md)
        v = num(md.get(ks[0])) if len(ks) == 1 else None
        good = len(ks) == 1 and ks[0] == floor_key and v is not None
        rows.append({'T': T, 'n_keys': len(ks), 'name_ok': len(ks) == 1 and ks[0] == floor_key, 'value': v})
        ok = ok and good
        vals.append(v)
    nondec = all(a is not None and b is not None and b >= a for a, b in zip(vals, vals[1:]))
    out = {'rows': rows, 'non_decreasing': nondec}
    if warm:
        t = {T: v for (T, _d), v in zip(docs, vals)}
        out['t150_eq_t1_eq_seed'] = t.get(150) is not None and t.get(1) == SEED and t.get(150) == SEED
        ok = ok and out['t150_eq_t1_eq_seed']
    out['ok'] = ok and nondec
    return out


def vbi7(hook_dir, rec_dir):
    hook_dir, rec_dir = Path(hook_dir), Path(rec_dir)
    loaded = []
    for p in sorted(hook_dir.glob('loaded_*.json')) if hook_dir.is_dir() else []:
        j = read_json(p, {}) or {}
        loaded.append({'argv0': j.get('argv0'), 'recorder_ok': j.get('recorder_ok')})
    errs = sorted(p.name for p in hook_dir.glob('hook_error_*.txt')) + \
        sorted(p.name for p in hook_dir.glob('hook_setup_error_*.txt')) if hook_dir.is_dir() else []
    cands = [d for d in sorted(hook_dir.glob('c_*')) if d.is_dir()] if hook_dir.is_dir() else []
    incomplete = [d.name for d in cands if not (d / 'cand.json').is_file() or not (d / 'k92_record.json').is_file()]
    sel = read_json(rec_dir / 'k92_select.json')
    status = (sel or {}).get('status')
    c = {'c1_loaded': bool(loaded) and sum(1 for x in loaded if x['argv0'] == ADAPTER) == 1
         and all(x['recorder_ok'] is True for x in loaded),
         'c2_no_hook_error': not errs,
         'c3_candidates_complete': not incomplete,
         'c4_select_status': status in SELECT_OK}
    return {'ok': all(c.values()), 'checks': c, 'n_loaded': len(loaded),
            'n_adapter_loaded': sum(1 for x in loaded if x['argv0'] == ADAPTER), 'n_candidates': len(cands),
            'errors': errs, 'incomplete': incomplete, 'status': status}


# ---------------------------------------------------------------------------------------------- resume (4.7)
def decision_paths(cd, T):
    t = s6(T)
    return {'prep': cd / 'prep' / ('t' + t), 'prep_rec': cd / 'prep' / ('t%s.prep.json' % t),
            'prep_log': cd / 'prep' / ('t%s.prepare.txt' % t), 'sel_log': cd / 'logs' / ('select_t%s.txt' % t),
            'hook': cd / 'hook' / ('t' + t), 'rec': cd / 'rec' / ('t' + t), 'dec': cd / 'dec',
            'done': cd / 'done' / ('t%s.json' % t), 'json': cd / 'dec' / ('action_%s.json' % t),
            'csv': cd / 'dec' / ('action_%s.csv' % t), 'logs': cd / 'logs'}


def classify_decision(cd, T):
    P = decision_paths(cd, T)
    if P['done'].is_file():
        d = read_json(P['done'], {}) or {}
        sh = d.get('out_sha256') or {}
        if P['json'].is_file() and P['csv'].is_file() and sha(P['json']) == sh.get('json') \
                and sha(P['csv']) == sh.get('csv'):
            return 'done'
        return 'done_mismatch'
    parts = [P['prep'], P['prep_rec'], P['prep_log'], P['sel_log'], P['hook'], P['rec']]
    dec_files = [p for p in P['dec'].glob('action_%s.*' % s6(T))] if P['dec'].is_dir() else []
    dec_files += [p for p in P['dec'].glob('run_t%s.json' % s6(T))] if P['dec'].is_dir() else []
    if any(p.exists() for p in parts) or dec_files:
        return 'half'
    return 'fresh'


def move_interrupted(cd, T, stamp):
    P = decision_paths(cd, T)
    moved = []
    for k in ('prep', 'hook', 'rec'):
        if P[k].exists():
            dst = P[k].parent / ('%s_interrupted_%s' % (P[k].name, stamp))
            rename(P[k], dst)
            moved.append([str(P[k]), str(dst)])
    for k in ('prep_rec', 'prep_log', 'sel_log'):
        if P[k].exists():
            dst = P[k].parent / ('%s_interrupted_%s' % (P[k].name, stamp))
            rename(P[k], dst)
            moved.append([str(P[k]), str(dst)])
    if P['dec'].is_dir():
        files = sorted(P['dec'].glob('action_%s.*' % s6(T))) + sorted(P['dec'].glob('run_t%s.json' % s6(T)))
        if files:
            box = mkdir(P['dec'] / ('_interrupted_%s_t%s' % (stamp, s6(T))), exist_ok=False)
            for f in files:
                rename(f, box / f.name)
                moved.append([str(f), str(box / f.name)])
    return moved


# ---------------------------------------------------------------------------------------------- driver context
class Ctx:
    def __init__(self):
        self.log = None
        self.lib = None
        self.sel = None
        self.kc = None
        self.a27 = None
        self.closed = None
        self.base = None
        self.floor_keys = None


CTX = Ctx()


def logmd(text):
    guard(KB / 'LOG.md')
    with open(KB / 'LOG.md', 'a', encoding='utf-8') as f:
        f.write('- [%s] V-B driver: %s\n' % (time.strftime('%Y-%m-%d %H:%M +0900'), text))


def step_line(name, rc, sec, pre, post, extra=None):
    rec = {'name': name, 'rc': rc, 'sec': sec, 'vissim_pre': pre, 'vissim_post': post, 'when': now()}
    rec.update(extra or {})
    guard(VBR / 'steps.jsonl')
    with open(VBR / 'steps.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec) + '\n')


def stop(stage, rule, why, detail=None):
    doc = {'stage': stage, 'rule': rule, 'why': why, 'detail': detail, 'when': now()}
    try:
        wjson(VBR / ('STOP_vb_%s.json' % stage), doc)
    except Exception:  # noqa: BLE001
        pass
    try:
        logmd('STOP %s (%s): %s' % (stage, rule, why))
    except Exception:  # noqa: BLE001
        pass
    if CTX.log:
        CTX.log('STOP %s %s %s' % (stage, rule, why))
    raise SystemExit(3)


def stage_rec(name):
    return read_json(VBR / 'stages' / ('%s.json' % name))


def stage_pass(name, doc):
    doc = dict(doc)
    doc.update(stage=name, passed=True, when=now())
    h = wjson(VBR / 'stages' / ('%s.json' % name), doc)
    CTX.log('STAGE %s PASS sha=%s' % (name, h[:16]))
    return h


def child(argv, log_path, cwd, env):
    guard(log_path)
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with open(log_path, 'w', encoding='utf-8', errors='replace') as f:
        rc = subprocess.run([str(a) for a in argv], cwd=str(cwd), env=env, stdout=f, stderr=subprocess.STDOUT,
                            creationflags=BELOW_NORMAL).returncode
    return rc, round(time.time() - t0, 1)


# ---------------------------------------------------------------------------------------------- V0
def pins_check(path):
    rows = []
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        h, p = line.split(' *', 1)
        try:
            got = sha(p)
        except OSError:
            got = None
        rows.append({'path': p, 'ok': got == h})
    return rows


def first_lines_sha(path, n):
    data = Path(path).read_bytes()
    pos, k = 0, 0
    while k < n:
        i = data.find(b'\n', pos)
        if i < 0:
            return None
        pos, k = i + 1, k + 1
    return hashlib.sha256(data[:pos]).hexdigest()


def git(*args):
    return subprocess.run(['git', '--no-optional-locks', '-C', str(GWT8)] + list(args), capture_output=True, text=True,
                          encoding='utf-8', errors='replace').stdout


def git_state():
    head = git('rev-parse', 'HEAD').strip()
    br = git('rev-parse', '--abbrev-ref', 'HEAD').strip()
    k8 = git('rev-parse', K8_BRANCH).strip()
    status = [x for x in git('status', '--porcelain').splitlines() if x.strip()]
    n = git('rev-list', '--count', '%s..HEAD' % K8_HEAD).strip()
    remote = [x for x in git('for-each-ref', 'refs/remotes', '--format=%(refname)').splitlines() if 'k92' in x]
    wt = [x for x in git('worktree', 'list', '--porcelain').splitlines() if x.startswith('worktree ')]
    wt_vb = [x for x in wt if 'vb' in Path(x[9:].strip()).name.lower()]
    ok = head == HEAD and br == BRANCH and k8 == K8_HEAD and not status and n == '6' and not remote and not wt_vb
    return {'ok': ok, 'head': head, 'branch': br, 'k8': k8, 'status_lines': len(status), 'ahead': n,
            'remote_k92': len(remote), 'worktree_vb': len(wt_vb)}


def rr_listing():
    out = {}
    for run in sorted({c['run'] for c in CHAINS.values()}):
        d = rr_dec(run)
        rows = []
        for base, dirs, names in os.walk(L.lp(d)):
            dirs.sort()
            for n in sorted(names):
                p = os.path.join(base, n)
                st = os.stat(p)
                rows.append([os.path.relpath(p, L.lp(d)).replace('\\', '/'), st.st_size, round(st.st_mtime, 6)])
        out[run] = {'files': len(rows), 'sha256': hashlib.sha256(json.dumps(rows).encode()).hexdigest()}
    return out


def ok2_listing():
    """OK2 outside VBR (sealed root never entered); the snapshot / log files this stage may add are left out."""
    rows = []
    root = L.lp(OK2)
    for base, dirs, names in os.walk(root):
        if _n(base) == _n(root):
            dirs[:] = [x for x in dirs if x not in ('sealed_s47', 'vb')]
        dirs.sort()
        rel_base = os.path.relpath(base, root).replace('\\', '/')
        for n in sorted(names):
            if rel_base == 'snap' and re.fullmatch(r's(38|39|40|41)_vb_[a-z0-9_]+\.json', n):
                continue
            if rel_base == 'logs' and n.startswith('vb_'):
                continue
            p = os.path.join(base, n)
            st = os.stat(p)
            rows.append([rel_base + '/' + n, st.st_size, round(st.st_mtime, 6)])
    return {'files': len(rows), 'sha256': hashlib.sha256(json.dumps(rows).encode()).hexdigest()}


def phase_mode(path):
    doc = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    sec = doc.get('phase_price') if isinstance(doc.get('phase_price'), dict) else {}
    return {'mode_present': 'mode' in sec, 'mode': sec.get('mode'),
            'ok': sec.get('mode') != 'observed_backpressure'}


def v0(resume):
    c = {}
    c['C1'] = {n: {'amend': sha(SP / ('K8_PREDECLARATION_AMENDMENT_%d.md' % n)) == A_SHA[n]
                   and (SP / ('K8_PREDECLARATION_AMENDMENT_%d.md.sha256' % n)).read_text(encoding='utf-8')[:64]
                   == A_SHA[n],
                   'fixed': sha(KB / ('AMENDMENT%d_FIXED.md' % n)) == F_SHA[n]} for n in range(24, 32)}
    c1 = all(v['amend'] and v['fixed'] for v in c['C1'].values())
    fixed_text = FIXED32.read_text(encoding='utf-8')
    toks = set(re.findall(r'(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])', fixed_text))
    c['C2'] = {'a32': sha(A32) == A32_SHA,
               'a32_sha256_file': (SP / 'K8_PREDECLARATION_AMENDMENT_32.md.sha256').read_text(encoding='utf-8')[:64]
               == A32_SHA,
               'in_fixed': A32_SHA in toks, 'declare_not_64': A32_DECLARE_SHA not in toks,
               'fixed_file': sha(FIXED32) == FIXED32_SHA}
    c['C3'] = {'notes_204': first_lines_sha(NOTES, 204) == NOTES_204_SHA}
    c['C4'] = git_state()
    exp = EXPECTED_PINS.read_bytes()
    a32rows = pins_check(A32_PINS) if A32_PINS.is_file() else []
    vbrows = pins_check(VB_PINS) if VB_PINS.is_file() else []
    logtext = (KB / 'LOG.md').read_text(encoding='utf-8')
    c['C5'] = {'a32_pins_bytes': A32_PINS.is_file() and A32_PINS.read_bytes() == exp and sha(EXPECTED_PINS) ==
               EXPECTED_PINS_SHA, 'a32_pins_ok': len(a32rows) == 51 and all(r['ok'] for r in a32rows),
               'vb_pins_ok': bool(vbrows) and all(r['ok'] for r in vbrows), 'vb_pins_n': len(vbrows),
               'vb_pins_sha_in_log': VB_PINS.is_file() and sha(VB_PINS) in logtext,
               'driver_sha_in_log': sha(__file__) in logtext,
               'recalc_sha_in_log': (KV / 'vb_recalc.py').is_file() and sha(KV / 'vb_recalc.py') in logtext}
    a31 = pins_check(A31_PINS)
    bad = [i + 1 for i, r in enumerate(a31) if not r['ok']]
    c['C6'] = {'lines': len(a31), 'bad_lines': bad,
               'ok': len(a31) == 133 and bad == [127] and a31[126]['path'].endswith('/GATES_K92B1.md')
               and sha(KB / 'GATES_K92B1.md') == GATES_MD_NOW}
    c['C7'] = {str(p.relative_to(KB)).replace('\\', '/'): sha(p) == h for p, h in GATES_REC.items()}
    if resume:
        c['C8'] = {'resume': True, 'vbr': VBR.is_dir(), 'vbt_build': VBT_BUILD.is_file()}
        c8 = VBR.is_dir() and (VBT_BUILD.is_file() or not VBT.exists())
    else:
        c['C8'] = {'vbr_absent': not VBR.exists(), 'vbt_absent': not VBT.exists(),
                   'build_absent': not VBT_BUILD.exists()}
        c8 = all(c['C8'].values())
    c['C9'] = rr_listing()
    cen = L.census()
    c['C10'] = {'vissim_any': cen['vissim_any'], 'foreign': len(cen['foreign_runner_or_replay'])}
    fs = L.free_space_gb()
    c['C11'] = {'free_gb': fs, 'ok': all(v >= 8.0 for v in fs.values())}
    c12 = {}
    for rel, want in ((CFG_REL, CFG_SHA), (SAFK91_REL, SAFK91_SHA), (CFGB1_REL, CFGB1_SHA)):
        c12[rel] = dict(phase_mode(GWT8 / rel), sha_ok=sha(GWT8 / rel) == want)
    c['C12'] = c12
    c['ok_by'] = {'C1': c1, 'C2': all(c['C2'].values()), 'C3': c['C3']['notes_204'], 'C4': c['C4']['ok'],
                  'C5': all(v for k, v in c['C5'].items() if k != 'vb_pins_n'), 'C6': c['C6']['ok'],
                  'C7': all(c['C7'].values()), 'C8': c8, 'C10': c['C10']['vissim_any'] == 0 and c['C10']['foreign'] == 0,
                  'C11': c['C11']['ok'], 'C12': all(v['ok'] and v['sha_ok'] for v in c12.values())}
    c['ok'] = all(c['ok_by'].values())
    c['ok2_outside_vb'] = ok2_listing()
    return c


# ---------------------------------------------------------------------------------------------- snapshot
def snapshot(name):
    out = OK2 / 'snap' / ('%s.json' % name)
    rec = stage_rec('snap_' + name)
    if rec:
        return rec
    guard(out)
    if sha(SNAP) != SNAP_SHA:
        stop('snap', 'S-K53', 'snapshot tool differs')
    pre = L.vissim_count()
    rc1, sec1 = child([PY, '-B', SNAP, 'take', out], VBR / 'logs' / ('snap_%s_take.txt' % name), KI, clean_env())
    rc2, sec2 = child([PY, '-B', SNAP, 'diff', SNAP_BASE, out], VBR / 'logs' / ('snap_%s_diff.txt' % name), KI,
                      clean_env())
    step_line('snap_' + name, rc2, round(sec1 + sec2, 1), pre, L.vissim_count())
    txt = (VBR / 'logs' / ('snap_%s_diff.txt' % name)).read_text(encoding='utf-8', errors='replace')
    same = rc1 == 0 and rc2 == 0 and 'K92SNAP_DIFF SAME' in txt
    if not same:
        stop('snap_' + name, 'S-K11', 'read-only snapshot differs from s02 or failed', {'rc': [rc1, rc2]})
    doc = {'file': str(out), 'sha256': sha(out), 'vs': str(SNAP_BASE), 'result': 'SAME'}
    stage_pass('snap_' + name, doc)
    logmd('스냅숏 %s SAME (s02 대비), sha256 `%s`' % (out.name, doc['sha256']))
    return doc


# ---------------------------------------------------------------------------------------------- V1, V2
def v1():
    rec = stage_rec('V1')
    if rec:
        return rec
    if VBT.exists() and not VBT_BUILD.is_file():
        stop('V1', 'S-K54', 'VBT exists without a build record (would be renamed outside the scope)')
    guard(VBT, v1=True)
    guard(VBT_BUILD, v1=True)
    b = G.build_archive(VBT_NAME, HEAD, CTX.log, cr_fix=True)
    a27 = load_pinned(VBT / SA_REL / 'k92_a27.py', A27M_SHA, 'k92_a27_vb')
    CTX.a27 = a27
    forms = a27.form_string(a27.l_form(VBT))
    shas = {'RS': sha(VBT / L.RS_REL) == RS_SHA, 'SHO': sha(VBT / L.SHO_REL) == SHO_SHA,
            'CFG': sha(VBT / CFG_REL) == CFG_SHA, 'SAFK91': sha(VBT / SAFK91_REL) == SAFK91_SHA,
            'CFGB1': sha(VBT / CFGB1_REL) == CFGB1_SHA, 'REC': sha(VBT / SA_REL / 'k92_record.py') == REC_SHA,
            'KC': sha(VBT / SA_REL / 'k92_compare.py') == KC_SHA,
            'KR_k92_replay': sha(VBT / SA_REL / 'k92_replay.py') == KR_SHA,
            'sa_arms': sha(VBT / SA_REL / 'sa_arms.py') == ARMS_SHA, 'k92_a27': True}
    p8b, p8 = a27.cr_pair(FRZ8B, VBT), a27.cr_pair(FRZ8, VBT)
    d = L.tree_diff(VBT, GWT8)
    doc = {'build': b, 'build_sha256': sha(VBT_BUILD), 'tree_root_ok': a27.tree_root_ok(VBT), 'cr_form': forms,
           'cr_pair_frz8b': p8b, 'cr_pair_frz8': p8, 'sha_ok': shas,
           'report_vs_gwt8': {'changed': len(d['changed']), 'only_vbt': len(d['only_a']), 'only_gwt8': len(d['only_b']),
                              'changed_files': d['changed'][:40]}}
    ok = doc['tree_root_ok'] and forms == 'CCCCCCCCCC' and p8b['ok'] and p8['ok'] and all(shas.values()) \
        and b.get('rs_sha256') == RS_SHA and b.get('sho_sha256') == SHO_SHA
    if not ok:
        wjson(VBR / 'stages' / 'V1_failed.json', doc)
        stop('V1', 'S-K15', 'V-B tree checks false', {'sha_ok': shas, 'cr_form': forms})
    stage_pass('V1', doc)
    logmd('V1 트리 `TK/vb_e27ceac8` (git archive e27ceac8 + CR 고침, 형태 %s, cr_pair 둘 참, RS·SHO·튜닝·REC·KC·'
          'k92_replay sha 기대값), 빌드 기록 sha256 `%s`; GWT8 작업 트리 대비 바이트 다름 %d·VBT만 %d·GWT8만 %d(보고만)'
          % (forms, doc['build_sha256'], len(d['changed']), len(d['only_a']), len(d['only_b'])))
    return doc


def arm_check(base_path, arm_path, want_arm):
    base = json.loads(Path(base_path).read_text(encoding='utf-8-sig'))
    arm = json.loads(Path(arm_path).read_text(encoding='utf-8-sig'))
    diff = sorted(L.leaf_paths_diff(base, arm))
    ev = {}
    for name, node in (('w', (arm.get('urban') or {}).get('sc109w_through_saturation')),
                       ('hb', ((arm.get('urban') or {}).get('capacity') or {}).get('head_floor_seed'))):
        rel = (node or {}).get('evidence')
        want = (node or {}).get('evidence_sha256')
        f = VBT / rel if isinstance(rel, str) else None
        ev[name] = {'evidence': rel, 'pinned': want, 'file_sha_ok': f is not None and f.is_file() and sha(f) == want}
    out = {'arm': str(arm_path), 'arm_sha256': sha(arm_path), 'diff_paths': diff,
           'two_paths': diff == ARM_KEYS, 'evidence': ev, 'file_sha_ok': sha(arm_path) == want_arm}
    out['ok'] = out['two_paths'] and out['file_sha_ok'] and all(v['file_sha_ok'] for v in ev.values())
    return out


def v2():
    rec = stage_rec('V2')
    if rec:
        return rec
    out = VBR / 'arms'
    mkdir(out)
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(('RW_', 'K8_', 'K8G_', 'K92A_', 'K92VB_'))}
    env.update(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', K8G_ROOT=str(VBT), K8G_OUT=str(out))
    pre = L.vissim_count()
    rc, sec = child([PY, '-B', VBT / SA_REL / 'sa_arms.py', '--root', VBT, '--out', out, '--k92b1'],
                    VBR / 'logs' / 'v2_sa_arms.txt', VBT / SA_REL, env)
    step_line('V2_sa_arms', rc, sec, pre, L.vissim_count())
    saf = out / 'sa' / 'tuning' / SAFB1_FILE
    i3 = {'CFG-B1': arm_check(VBT / CFG_REL, VBT / CFGB1_REL, CFGB1_SHA),
          'SAF-B1': arm_check(VBT / SAFK91_REL, saf, SAFB1_SHA) if saf.is_file() else {'ok': False}}
    c12 = {'VBT_' + rel: phase_mode(VBT / rel) for rel in (CFG_REL, SAFK91_REL, CFGB1_REL)}
    if saf.is_file():
        c12['SAF-B1'] = phase_mode(saf)
    doc = {'rc': rc, 'saf_b1': str(saf), 'saf_b1_sha256': sha(saf) if saf.is_file() else None, 'VB_I3': i3,
           'C12': c12}
    ok = rc == 0 and doc['saf_b1_sha256'] == SAFB1_SHA and all(v['ok'] for v in i3.values()) and \
        all(v['ok'] for v in c12.values()) and 'SAF-B1' in c12
    if not ok:
        wjson(VBR / 'stages' / 'V2_failed.json', doc)
        stop('V2', 'S-K15', 'arm files / VB-I3 / C12 false')
    stage_pass('V2', doc)
    logmd('V2 팔: SAF-B1 `%s` = 기대값, VB-I3 두 팔 참(차이 두 경로, 증거 sha = VBT 커밋 증거, 파일 sha), C12 참' % SAFB1_SHA)
    return doc


# ---------------------------------------------------------------------------------------------- prepare + run one
def prepare(run, T, prep_dir, prep_rec, log, tag):
    if prep_dir.exists():
        stop('prep', 'S-K54', 'prepared folder exists (never rewritten): %s' % prep_dir)
    guard(prep_dir)
    guard(prep_rec)
    if sha(GPREP) != GPREP_SHA:
        stop('prep', 'S-K53', 'gprep.py differs')
    mkdir(prep_dir.parent)
    rc, sec = child([PY, '-B', GPREP, str(rr_dec(run)), str(T), str(prep_dir), str(prep_rec)],
                    Path(str(prep_rec)[:-len('.prep.json')] + '.prepare.txt'), KI, CTX.base)
    pr = read_json(prep_rec) or {}
    ok = rc == 0 and pr.get('all_copies') and pr.get('state_obs150_directory_is_bundle') \
        and pr.get('history_count') == pr.get('history_expected')
    log('PREP %s rc=%s ok=%s sec=%s' % (tag, rc, ok, sec))
    return ok, {'rc': rc, 'sec': sec, 'record_sha256': sha(prep_rec) if Path(prep_rec).is_file() else None,
                'history': [pr.get('history_count'), pr.get('history_expected')],
                'previous_sec': pr.get('previous_sec'), 'evidence_previous': pr.get('evidence_previous')}


def adapter_run(prep_dir, tuning, out_dir, T, *, prev_override, hooked, seed, label, hook_dir, log, tag):
    out_dir = Path(out_dir)
    mkdir(out_dir)
    oj, oc = out_dir / ('action_%s.json' % s6(T)), out_dir / ('action_%s.csv' % s6(T))
    for p in (oj, oc):
        guard(p)
        if p.exists():
            stop('run', 'S-K54', 'output exists (never rewritten): %s' % p)
    fs = L.free_space_gb()
    if any(v < 8.0 for v in fs.values()):
        stop('run', 'S-K14', 'free space below 8 GB before %s: %s' % (tag, fs))
    waited, cen = L.wait_idle(log, tag)
    try:
        la = adapter_launch(prep_dir, VBT, tuning, oj, oc, base=CTX.base, controller='',
                            extra_pythonpath=str(HOOKDIR) if hooked else '', prev_override=prev_override)
    except Refused as e:
        stop('run', 'S-K15', 'launch refused %s: %s' % (tag, e))
    env = dict(la['env'])
    if hooked:
        env.update(hook_env(T, seed, label, hook_dir))
    stem = 'action_%s' % s6(T)
    pre = L.vissim_count()
    log('START %s ctl=%s hooked=%s prev=%s' % (tag, la['controller'], hooked, 'chain' if prev_override else
                                                ('record' if la['prev'] else '-')))
    rc, wall, pid, killed = run_watched(la['argv'], la['cwd'], env, out_dir / (stem + '.stdout.txt'),
                                        out_dir / (stem + '.stderr.txt'), out_dir / (stem + '.joint.progress.jsonl'),
                                        la['controller'] != 'no-control', log, tag)
    post = L.vissim_count()
    shas = {k: (sha(p) if p.is_file() else None) for k, p in
            (('json', oj), ('csv', oc), ('progress', out_dir / (stem + '.joint.progress.jsonl')))}
    rr = {'tag': tag, 'argv': la['argv'], 'cwd': la['cwd'], 'env': env_brief(env), 'exit': rc, 'wall_sec': wall,
          'pid': pid, 'killed': killed, 'controller': la['controller'], 'previous': la['prev'],
          'record_previous': la['record_prev'], 'out_sha256': shas, 'waited_sec': waited,
          'census_foreign': len(cen['foreign_runner_or_replay']), 'vissim_pre': pre, 'vissim_post': post,
          'hooked': hooked, 'tuning': str(tuning), 'tuning_sha256': sha(tuning), 'finished': now()}
    wjson(out_dir / ('run_t%s.json' % s6(T)), rr)
    step_line(tag, rc, wall, pre, post)
    log('END %s exit=%s wall=%s killed=%s' % (tag, rc, wall, bool(killed)))
    if killed:
        stop('run', 'S-K15', 'stalled decision killed: %s' % tag)
    return rr, la


def select(hook_dir, action_json, T, dest, log_path):
    if Path(dest).exists():
        stop('select', 'S-K54', 'record folder exists (never rewritten): %s' % dest)
    guard(dest)
    if sha(AD32 / 'vb_select.py') != SELECT_SHA:
        stop('select', 'S-K53', 'vb_select.py differs')
    rc, sec = child([PY, '-B', AD32 / 'vb_select.py', 'select', '--hook-dir', hook_dir, '--action-json', action_json,
                     '--T', str(T), '--dest', dest], log_path, KV, clean_env())
    sel = read_json(Path(dest) / 'k92_select.json')
    return rc, (sel or {}).get('status')


def write_receipt_guarded(out_json, out_csv):
    guard(str(out_json) + '.applied')
    return CTX.lib.write_receipt(out_json, out_csv)


def tree_files_ok():
    return {'RS': sha(VBT / L.RS_REL) == RS_SHA, 'SHO': sha(VBT / L.SHO_REL) == SHO_SHA,
            'REC': sha(VBT / SA_REL / 'k92_record.py') == REC_SHA, 'KC': sha(VBT / SA_REL / 'k92_compare.py') == KC_SHA,
            'HOOK': sha(HOOKDIR / 'sitecustomize.py') == HOOK_SHA, 'LIB': sha(AD32 / 'vb_lib32.py') == LIB_SHA,
            'SELECT': sha(AD32 / 'vb_select.py') == SELECT_SHA,
            'hookdir_one_file': sorted(p.name for p in HOOKDIR.iterdir()) == ['sitecustomize.py']}


def decision(row):
    log = CTX.log
    cd = chain_dir(row)
    T = row['T']
    P = decision_paths(cd, T)
    tag = '%s_%s_T%s' % (row['key'], row['arm'], s6(T))
    state = classify_decision(cd, T)
    if state == 'done':
        log('SKIP %s (done)' % tag)
        return read_json(P['done'])
    if state == 'done_mismatch':
        stop('chain', 'S-K54', 'done record and outputs differ: %s' % tag)
    resume = None
    if state == 'half':
        stamp = time.strftime('%Y%m%d_%H%M%S')
        resume = move_interrupted(cd, T, stamp)
        wjson(cd / 'resume' / ('t%s_%s.json' % (s6(T), stamp)), {'moved': resume})
        log('RESUME %s moved=%d' % (tag, len(resume)))
    tf = tree_files_ok()
    tuning, tw = Path(row['tuning']), row['tuning_sha256']
    if not all(tf.values()) or sha(tuning) != tw:
        stop('chain', 'S-K53', 'tree / tool / tuning bytes changed before %s' % tag, tf)
    # previous action (4.4)
    prev_override = None
    if not row['first']:
        Pp = decision_paths(cd, row['prev_T'])
        dprev = read_json(Pp['done'])
        if not dprev or dprev.get('exit') != 0 or sha(Pp['json']) != dprev['out_sha256']['json'] or \
                sha(Pp['csv']) != dprev['out_sha256']['csv']:
            stop('chain', 'S-K54', 'chained previous is not the completed previous decision of this chain: %s' % tag)
        prev_override = Pp['json']
    ok, prep = prepare(row['run'], T, P['prep'], P['prep_rec'], log, tag)
    if not ok:
        stop('chain', 'S-K15', 'prepare failed: %s' % tag, prep)
    mkdir(P['hook'].parent)
    if P['hook'].exists():
        stop('chain', 'S-K54', 'hook folder exists: %s' % P['hook'])
    mkdir(P['hook'], exist_ok=False)
    label = '%s/%s/T%s' % (row['chain'], row['arm'], s6(T))
    rr, la = adapter_run(P['prep'], tuning, P['dec'], T, prev_override=prev_override, hooked=True, seed=row['seed'],
                         label=label, hook_dir=P['hook'], log=log, tag=tag)
    # previous-action rule checks (S-K54)
    if row['first']:
        want = None if row['prev_T'] is None else rr_dec(row['run']) / ('action_%s.json' % s6(row['prev_T']))
        good = (la['prev'] is None) if want is None else (la['prev'] is not None and _n(la['prev']) == _n(want))
    else:
        good = la['prev'] is not None and _n(la['prev']) == _n(prev_override)
    if not good:
        stop('chain', 'S-K54', 'previous action rule broken: %s' % tag)
    if rr['exit'] != 0:
        stop('chain', 'S-K15', 'adapter exit %s: %s' % (rr['exit'], tag))
    receipt = write_receipt_guarded(P['json'], P['csv'])
    rc_s, status = select(P['hook'], P['json'], T, P['rec'], P['logs'] / ('select_t%s.txt' % s6(T)))
    if rc_s != 0:
        stop('chain', 'S-K52', 'select failed rc=%s: %s' % (rc_s, tag))
    done = {'row': row, 'exit': rr['exit'], 'wall_sec': rr['wall_sec'], 'out_sha256': rr['out_sha256'],
            'previous': la['prev'], 'receipt': receipt, 'select_status': status, 'prepare': prep,
            'resume_moved': resume, 'tree_files_ok_before': tf, 'tree_files_ok_after': tree_files_ok(),
            'finished': now()}
    mkdir(P['done'].parent)
    h = wjson(P['done'], done)
    log('DONE %s status=%s receipt=%s sha=%s' % (tag, status, bool(receipt), h[:16]))
    if not all(done['tree_files_ok_after'].values()):
        stop('chain', 'S-K53', 'tree / tool bytes changed during %s' % tag)
    return done


# ---------------------------------------------------------------------------------------------- per-decision judge
def load_doc(p):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return None


def judge_rows(rows):
    """VB-I2 and VB-I7 for the given plan rows (outputs read again from the files)."""
    out = []
    t1_docs = {}
    for row in rows:
        cd = chain_dir(row)
        P = decision_paths(cd, row['T'])
        rr = read_json(P['dec'] / ('run_t%s.json' % s6(row['T']))) or {}
        doc = load_doc(P['json'])
        names = files_of_T(P['dec'], row['T'])
        stem = 'action_%s' % s6(row['T'])
        df = (text_count(P['dec'] / (stem + '.stdout.txt'), 'DECISION_FAILED') or 0) + \
            (text_count(P['dec'] / (stem + '.stderr.txt'), 'DECISION_FAILED') or 0)
        exc = None
        if row['chain'] == 'VB-41w' and row['arm'] == 'b1' and row['T'] == 150:
            P1 = decision_paths(cd, 1)
            if row['key'] not in t1_docs:
                t1_docs[row['key']] = load_doc(P1['json'])
            exc = {'floor_key': CTX.floor_keys[row['run']], 't1_doc': t1_docs[row['key']]}
        i2 = vbi2(doc or {}, names, row['T'], rr.get('exit'), df, exception=exc)
        i2['output_present'] = doc is not None
        i2['ok'] = i2['ok'] and doc is not None
        i7 = vbi7(P['hook'], P['rec'])
        sel = read_json(P['rec'] / 'k92_select.json') or {}
        out.append({'chain': row['chain'], 'arm': row['arm'], 'T': row['T'], 'VB_I2': i2, 'VB_I7': i7,
                    'sdmpc_active': (doc or {}).get('metadata', {}).get('sdmpc_active') if doc else None,
                    'select_status': sel.get('status'), 'n_candidates': sel.get('n_candidates'),
                    'n_match': sel.get('n_match'), 'hook_sec_total': sel.get('hook_sec_total')})
        del doc
    return out


# ---------------------------------------------------------------------------------------------- V3 ZI
def zi_cell(cell, run, T, arm):
    log = CTX.log
    cdir = VBR / 'zi' / cell
    judge_p = cdir / 'zi_judge.json'
    if judge_p.is_file():
        return read_json(judge_p)
    if cdir.exists():
        stamp = time.strftime('%Y%m%d_%H%M%S')
        rename(cdir, VBR / 'zi' / ('%s_interrupted_%s' % (cell, stamp)))
        for extra in (VBR / 'zi' / ('%s.prep.json' % cell), VBR / 'zi' / ('%s.prepare.txt' % cell)):
            if extra.exists():
                rename(extra, extra.parent / ('%s_interrupted_%s' % (extra.name, stamp)))
        log('ZI_RESUME %s moved' % cell)
    if arm == 'off':
        tuning, tw = VBT / SAFK91_REL, SAFK91_SHA
    else:
        tuning, tw = VBR / 'arms' / 'sa' / 'tuning' / SAFB1_FILE, SAFB1_SHA
    if sha(tuning) != tw or not all(tree_files_ok().values()):
        stop('V3', 'S-K53', 'tree / tuning bytes changed before ZI %s' % cell)
    ok, prep = prepare(run, T, cdir, VBR / 'zi' / ('%s.prep.json' % cell), log, 'ZI_' + cell)
    if not ok:
        stop('V3', 'S-K51', 'ZI prepare failed: %s' % cell, prep)
    stem = 'action_%s' % s6(T)
    # hook off
    rr_off, la_off = adapter_run(cdir, tuning, cdir / 'replay', T, prev_override=None, hooked=False, seed=43,
                                 label='', hook_dir=None, log=log, tag='ZI_%s_off' % cell)
    rename(cdir / 'replay', cdir / 'replay_off')
    z6_files = [str(p) for p in cdir.rglob('loaded_*')] + [str(p) for p in cdir.rglob('c_*')]
    z6 = {'hook_dir_absent': not (cdir / 'hook_on').exists(), 'no_hook_files': not z6_files, 'files': z6_files[:20]}
    # hook on
    hdir = mkdir(cdir / 'hook_on', exist_ok=False)
    rr_on, la_on = adapter_run(cdir, tuning, cdir / 'replay', T, prev_override=None, hooked=True, seed=43,
                               label='ZI/%s/T%s' % (cell, s6(T)), hook_dir=hdir, log=log, tag='ZI_%s_on' % cell)
    rename(cdir / 'replay', cdir / 'replay_on')
    rc_s, status = select(hdir, cdir / 'replay_on' / (stem + '.json'), T, cdir / 'rec_on',
                          cdir / 'select_on.txt')

    def z1(rr, d):
        names = sorted(p.name for p in d.iterdir()) if d.is_dir() else []
        df = (text_count(d / (stem + '.stdout.txt'), 'DECISION_FAILED') or 0) + \
            (text_count(d / (stem + '.stderr.txt'), 'DECISION_FAILED') or 0)
        return {'exit0': rr['exit'] == 0, 'json': (d / (stem + '.json')).is_file(), 'csv': (d / (stem + '.csv')).is_file(),
                'no_error_txt': not [n for n in names if n.endswith('.error.txt')], 'no_decision_failed': df == 0}
    z1_off, z1_on = z1(rr_off, cdir / 'replay_off'), z1(rr_on, cdir / 'replay_on')
    zj = CTX.lib.zi_judge(CTX.kc, cdir / 'replay_off', cdir / 'replay_on', T, VBT)
    i7 = vbi7(hdir, cdir / 'rec_on')
    z7 = {'c1': i7['checks']['c1_loaded'], 'c2': i7['checks']['c2_no_hook_error'],
          'c3': i7['checks']['c3_candidates_complete'], 'select_rc0': rc_s == 0, 'status': status}
    z7['ok'] = z7['c1'] and z7['c2'] and z7['c3'] and z7['select_rc0'] and \
        (status == 'selected' if cell.startswith('z1') else status in SELECT_OK)
    checks = {'z1': all(z1_off.values()) and all(z1_on.values()), 'z2': zj['checks'].get('csv_bytes_same') is True,
              'z3': zj['checks'].get('compare_pass') is True, 'z4': zj['checks'].get('progress_last_same') is True,
              'z5': zj['checks'].get('only_wallclock') is True, 'z6': z6['hook_dir_absent'] and z6['no_hook_files'],
              'z7': z7['ok']}
    sel = read_json(cdir / 'rec_on' / 'k92_select.json') or {}
    cand_bytes = 0
    for d in hdir.glob('c_*'):
        for f in d.iterdir():
            cand_bytes += f.stat().st_size
    report = {'wall_on_over_off': (rr_on['wall_sec'] / rr_off['wall_sec']) if rr_off['wall_sec'] else None,
              'wall_off_sec': rr_off['wall_sec'], 'wall_on_sec': rr_on['wall_sec'],
              'n_candidates': sel.get('n_candidates'), 'n_match': sel.get('n_match'),
              'hook_sec_total': sel.get('hook_sec_total'), 'candidate_bytes': cand_bytes,
              'n_loaded': i7['n_loaded']}
    if sel.get('status') == 'selected':
        r = read_json(cdir / 'rec_on' / 'k92_record.json') or {}
        report['record_fields'] = {'top': sorted(r), 'horizon': sorted((r.get('horizon') or {}))}
    if cell == 'z1_off':
        rep = CTX.kc.compare(rr_dec(run), cdir / 'replay_off', T, VBT, keyed=None, old_root=FRZ8, label='zi_rec')
        report['off_vs_record'] = {'verdict': rep.get('verdict'), 'hard_verdict': rep.get('hard_verdict'),
                                   'unclassified_n': rep.get('unclassified_n'), 'allowed_counts': rep.get('allowed_counts')}
    doc = {'cell': cell, 'run': run, 'T': T, 'arm': arm, 'tuning': str(tuning), 'checks': checks, 'pass': all(checks.values()),
           'z1_detail': {'off': z1_off, 'on': z1_on}, 'zi_judge': zj, 'z6': z6, 'z7': z7, 'report_only': report,
           'prepare': prep}
    wjson(judge_p, doc)
    log('ZI %s pass=%s checks=%s' % (cell, doc['pass'], checks))
    return doc


def v3():
    rec = stage_rec('V3')
    if rec:
        return rec
    cells = {}
    for cell, run, T, arm in ZI_CELLS:
        cells[cell] = zi_cell(cell, run, T, arm)
        if not cells[cell]['pass']:
            wjson(VBR / 'zi' / 'zi.json', {'cells': cells, 'pass': False})
            stop('V3', 'S-K51', 'ZI cell %s not PASS' % cell, cells[cell]['checks'])
    doc = {'cells': {k: {'pass': v['pass'], 'checks': v['checks'], 'report_only': v['report_only']}
                     for k, v in cells.items()}, 'pass': True}
    h = wjson(VBR / 'zi' / 'zi.json', doc)
    stage_pass('V3', {'zi_sha256': h, 'pass': True})
    logmd('V3 ZI 세 칸 PASS, `VBR/zi/zi.json` sha256 `%s`' % h)
    return doc


# ---------------------------------------------------------------------------------------------- V4 .. V7
def run_chain(arm):
    rows = [r for r in plan() if r['arm'] == arm]
    for row in rows:
        decision(row)
    return rows


def v5():
    rec = stage_rec('V5')
    if rec:
        return rec
    rows = [r for r in plan() if r['arm'] == 'off']
    i1 = {}
    for row in rows:
        if not row['first']:
            continue
        cd = chain_dir(row)
        rep = CTX.kc.compare(rr_dec(row['run']), cd / 'dec', row['T'], VBT, keyed=None,
                             old_root=Path(row['old_root']), label='VB-I1 %s T=%d' % (row['chain'], row['T']))
        sdmpc = row['T'] >= 900
        a = [x for x in rep.get('k92_checks') or [] if x.get('rule') == 'A_K92']
        d5 = (len(a) >= 1 and all(x.get('ok') and x.get('new_is_root_rs') and x.get('old_is_root_rs') for x in a)) \
            if sdmpc else None
        i1['%s/T%s' % (row['chain'], s6(row['T']))] = {
            'verdict': rep.get('verdict'), 'hard_verdict': rep.get('hard_verdict'), 'sdmpc': sdmpc,
            'a_k92_rows': len(a), 'd5_root_check': d5, 'pass': rep.get('verdict') == 'PASS' and (d5 is not False),
            'report': rep}
    ro = {}
    for row in rows:
        if row['first']:
            continue
        cd = chain_dir(row)
        dtype = CTX.lib.decision_type(CTX.closed, row['chain'], row['T'])
        rep = CTX.kc.compare(rr_dec(row['run']), cd / 'dec', row['T'], VBT, keyed=None,
                             old_root=Path(row['old_root']), label='VB-I1 report-only %s T=%d' % (row['chain'], row['T']))
        view = CTX.lib.reportonly(rep, dtype, CTX.closed)
        ro['%s/T%s' % (row['chain'], s6(row['T']))] = {'chain': row['chain'], 'T': row['T'], 'prev_T': row['prev_T'],
                                                       'dtype': dtype, 'view': view, 'report': rep}
    ji = judge_rows(rows)
    i1_ok = len(i1) == 4 and all(v['pass'] for v in i1.values())
    i2_ok = all(r['VB_I2']['ok'] for r in ji)
    i7_ok = all(r['VB_I7']['ok'] for r in ji)
    outside = {k: v['view'].get('outside_n') for k, v in ro.items()}
    h1 = wjson(VBR / 'judge' / 'vb_i1.json', {'VB_I1': i1, 'VB_I1_pass': i1_ok, 'off_rows': ji, 'VB_I2_off_ok': i2_ok,
                                               'VB_I7_off_ok': i7_ok, 'closed_sha256': sha(AD32 / 'vb_closed_leaves.json')})
    h2 = wjson(VBR / 'judge' / 'vb_reportonly.json', {'decisions': ro, 'outside_n': outside})
    CTX.log('V5 VB-I1 4=%s VB-I2 14=%s VB-I7 14=%s reportonly_outside=%s' % (
        [v['verdict'] for v in i1.values()], i2_ok, i7_ok, outside))
    if not (i1_ok and i2_ok and i7_ok):
        stop('V5', 'S-K55', 'OFF gate false (VB-I1 %s, VB-I2 %s, VB-I7 %s)' % (i1_ok, i2_ok, i7_ok))
    stage_pass('V5', {'vb_i1_sha256': h1, 'vb_reportonly_sha256': h2, 'outside_n': outside})
    n_dec = sum(1 for v in outside.values() if v)
    logmd('V5 OFF 관문: VB-I1 판정 4결정 결과 넷 %s, OFF 14결정 VB-I2·VB-I7 참; 보고 전용 10결정 닫힌 목록 밖 차이 '
          '결정 %d개에서 모두 %s개(판정 아님); `judge/vb_i1.json` `%s`, `judge/vb_reportonly.json` `%s`'
          % ([v['verdict'] for v in i1.values()], n_dec,
             sum(v for v in outside.values() if isinstance(v, int)), h1, h2))
    return True


def v7():
    rec = stage_rec('V7')
    if rec:
        return rec
    rows = plan()
    ji = judge_rows(rows)
    i4 = []
    for row in rows:
        P = decision_paths(chain_dir(row), row['T'])
        i4.append({'chain': row['chain'], 'arm': row['arm'], 'T': row['T'], 'json': P['json'].is_file(),
                   'csv': P['csv'].is_file()})
    i4_ok = len(i4) == 55 and all(x['json'] and x['csv'] for x in i4) and \
        sum(1 for r in rows if r['arm'] == 'b1') == 41 and sum(1 for r in rows if r['arm'] == 'off') == 14
    i6 = {}
    for chain in ORDER:
        crow = [r for r in rows if r['chain'] == chain and r['arm'] == 'b1']
        docs = []
        for r in crow:
            d = load_doc(decision_paths(chain_dir(r), r['T'])['json'])
            md = (d or {}).get('metadata') or {}
            docs.append((r['T'], {'metadata': {k: md[k] for k in md if k.startswith(FLOOR_PREFIX)}}))
            del d
        i6[chain] = vbi6(docs, CTX.floor_keys[CHAINS[chain]['run']], chain == 'VB-41w')
    i3 = (stage_rec('V2') or {}).get('VB_I3') or {}
    i3_now = {'CFG-B1': arm_check(VBT / CFG_REL, VBT / CFGB1_REL, CFGB1_SHA),
              'SAF-B1': arm_check(VBT / SAFK91_REL, VBR / 'arms' / 'sa' / 'tuning' / SAFB1_FILE, SAFB1_SHA)}
    doc = {'rows': ji, 'VB_I2_ok': all(r['VB_I2']['ok'] for r in ji), 'VB_I7_ok': all(r['VB_I7']['ok'] for r in ji),
           'VB_I4': i4, 'VB_I4_ok': i4_ok, 'VB_I6': i6, 'VB_I6_ok': all(v['ok'] for v in i6.values()),
           'VB_I3': i3_now, 'VB_I3_ok': all(v['ok'] for v in i3_now.values()) and all(
               v.get('ok') for v in i3.values()) and bool(i3)}
    sel_counts = {}
    for r in ji:
        if r['sdmpc_active']:
            sel_counts[r['select_status']] = sel_counts.get(r['select_status'], 0) + 1
    doc['select_counts_sdmpc'] = sel_counts
    doc['not_selected_sdmpc'] = [[r['chain'], r['arm'], r['T'], r['select_status']] for r in ji
                                 if r['sdmpc_active'] and r['select_status'] != 'selected']
    doc['ok'] = doc['VB_I2_ok'] and doc['VB_I7_ok'] and doc['VB_I4_ok'] and doc['VB_I6_ok'] and doc['VB_I3_ok']
    h = wjson(VBR / 'judge' / 'vb_i.json', doc)
    CTX.log('V7 VB-I2=%s VB-I3=%s VB-I4=%s VB-I6=%s VB-I7=%s sel=%s' % (
        doc['VB_I2_ok'], doc['VB_I3_ok'], doc['VB_I4_ok'], doc['VB_I6_ok'], doc['VB_I7_ok'], sel_counts))
    if not doc['ok']:
        stop('V7', 'S-K15' if doc['VB_I7_ok'] else 'S-K52', 'integrity false', {
            k: doc[k] for k in ('VB_I2_ok', 'VB_I3_ok', 'VB_I4_ok', 'VB_I6_ok', 'VB_I7_ok')})
    stage_pass('V7', {'vb_i_sha256': h})
    logmd('V7 무결성 55결정: VB-I2·VB-I3·VB-I4·VB-I6·VB-I7 참; SDMPC 결정 고르기 상태 %s; `judge/vb_i.json` `%s`'
          % (sel_counts, h))
    return doc


# ---------------------------------------------------------------------------------------------- V8 metrics
def dsum(doc, run):
    md = doc.get('metadata') if isinstance(doc.get('metadata'), dict) else {}
    jls = md.get('joint_leader_selection') if isinstance(md.get('joint_leader_selection'), dict) else {}
    g = doc.get('green_times') if isinstance(doc.get('green_times'), dict) else {}
    fk = CTX.floor_keys[run]
    w, h, s = num(jls.get('warm_start_objective')), num(jls.get('held_objective')), num(jls.get('selected_objective'))
    return {'p2': num(g.get('SC109_p2')), 'p3': num(g.get('SC109_p3')), 'p4': num(g.get('SC109_p4')),
            'floor': num(md.get(fk)), 'floor_keys_n': len(floor_keys(md)),
            'seed_binding': num(md.get('k92_hb_seed_binding')),
            'groups_carried': num(md.get('head_observation_groups_carried')),
            'groups_updated': num(md.get('head_observation_groups_updated')),
            'k92_w': 'k92_w' in md, 'k92_hb': 'k92_hb' in md,
            'selection_status': jls.get('selection_status') if jls else None, 'omega': s,
            'warm_gt_held': (w > h) if (w is not None and h is not None) else None,
            'selected_gt_held': (s > h) if (s is not None and h is not None) else None,
            'decision_wall_sec': num(md.get('decision_wall_sec'))}


REC_FIELDS = ('chain_T450', 'chain_blocks', 'chain_max_450', 'w_bound_ratio', 'e_out_over_220', 'outw', 'feed4',
              'feed4_ratio', 'phantom_end')


def record_metrics(rec_dir, T):
    import numpy as np
    sel = read_json(Path(rec_dir) / 'k92_select.json') or {}
    st = sel.get('status')
    if st != 'selected':
        return dict({k: None for k in REC_FIELDS}, none_reason='record:%s' % st, n_states=None)
    r = read_json(Path(rec_dir) / 'k92_record.json') or {}
    hz = r.get('horizon') or {}
    blocks = r.get('blocks') or []
    chain_blocks = [num(b.get('chain_sum')) for b in blocks[:3]]
    cmax = None
    npz = Path(rec_dir) / 'k92_series.npz'
    if npz.is_file():
        z = np.load(npz, allow_pickle=True)
        keys = [str(k) for k in z['keys']]
        idx = [keys.index(k) for k in ('movement:SC109_W_SC108_to_E', 'movement:SC109_W_SC108_to_N_SC16',
                                       'storage:SC108_to_SC109') if k in keys]
        if len(idx) == 3:
            t_end, model = z['t_end'], z['model']
            best = None
            for i in range(len(t_end)):
                te = float(t_end[i])
                if not (te > T and te <= T + 450.0):
                    continue
                vals = [float(model[i, j]) for j in idx]
                if all(math.isfinite(v) for v in vals):
                    sm = math.fsum(vals)
                    best = sm if best is None or sm > best else best
            cmax = best
    wb, wd = hz.get('w_capacity_bound_steps'), hz.get('w_steps_with_departures')
    outw, feed = num(hz.get('outw_veh_h_450')), num(hz.get('feed4_veh_h_450'))
    chosen = sel.get('chosen') or {}
    cand = read_json(Path(sel.get('hook_dir', '')) / str(chosen.get('folder')) / 'cand.json') if chosen else None
    return {'chain_T450': num(hz.get('m1_chain_T450')), 'chain_blocks': chain_blocks, 'chain_max_450': cmax,
            'w_bound_ratio': (float(wb) / float(wd)) if is_num(wb) and is_num(wd) and wd else None,
            'e_out_over_220': num(hz.get('e_out_max_over_220')), 'outw': outw, 'feed4': feed,
            'feed4_ratio': (feed / outw) if (outw is not None and feed is not None and outw > 0) else None,
            'phantom_end': num(hz.get('phantom_end_450')), 'none_reason': None,
            'n_states': (cand or {}).get('n_states')}


def metric_rows():
    rows = []
    rec_csv = {}
    for chain in ORDER:
        c = CHAINS[chain]
        for side in ('REC', 'OFF', 'B1'):
            times = c['times'] if side != 'OFF' else c['off_times']
            for T in times:
                if side == 'REC':
                    jp = rr_dec(c['run']) / ('action_%s.json' % s6(T))
                    cp = rr_dec(c['run']) / ('action_%s.csv' % s6(T))
                    run_wall = None
                else:
                    P = decision_paths(VBR / 'chain' / ('%s_%s' % (c['key'], side.lower())), T)
                    jp, cp = P['json'], P['csv']
                    run_wall = num((read_json(P['dec'] / ('run_t%s.json' % s6(T))) or {}).get('wall_sec'))
                doc = load_doc(jp) or {}
                row = {'chain': chain, 'side': side, 'T': T}
                row.update(dsum(doc, c['run']))
                del doc
                row['csv_sha256'] = sha(cp)
                row['wall_run_sec'] = run_wall
                if side == 'REC':
                    rec_csv[(chain, T)] = row['csv_sha256']
                    row.update({k: None for k in REC_FIELDS}, none_reason='REC: recorder not run (J1 record)',
                               n_states=None)
                else:
                    P = decision_paths(VBR / 'chain' / ('%s_%s' % (c['key'], side.lower())), T)
                    row.update(record_metrics(P['rec'], T))
                    row['select_status'] = (read_json(P['rec'] / 'k92_select.json') or {}).get('status')
                rows.append(row)
    for row in rows:
        if row['side'] != 'REC':
            row['csv_same_as_rec'] = row['csv_sha256'] == rec_csv[(row['chain'], row['T'])]
        if row['side'] == 'B1' and row['chain'] == 'VB-41w':
            rec = [r for r in rows if r['side'] == 'REC' and r['chain'] == 'VB-41w' and r['T'] == row['T']][0]
            want = max(rec['floor'], SEED) if rec['floor'] is not None else SEED
            row['floor_eq_max_rec_seed'] = row['floor'] is not None and row['floor'] == want
    return rows


def chain_metrics(rows):
    out = []
    for chain in ORDER:
        for side in ('REC', 'OFF', 'B1'):
            rs = sorted((r for r in rows if r['chain'] == chain and r['side'] == side), key=lambda r: r['T'])
            p3 = [(r['T'], r['p3']) for r in rs]
            low = [T for T, v in p3 if v is not None and v <= 24.5]
            deltas = []
            for (Ta, a), (Tb, b) in zip(p3, p3[1:]):
                if Tb - Ta == (150 if Ta > 1 else 149) and a is not None and b is not None:
                    deltas.append(b - a)
            big = [d for d in deltas if abs(d) >= 0.5]
            flips = sum(1 for x, y in zip(big, big[1:]) if (x > 0) != (y > 0))
            st = {}
            for r in rs:
                st[str(r['selection_status'])] = st.get(str(r['selection_status']), 0) + 1
            first_diff = None
            if side != 'REC':
                d = [r['T'] for r in rs if not r['csv_same_as_rec']]
                first_diff = min(d) if d else None
            out.append({'chain': chain, 'side': side, 'n': len(rs), 'n_p3_le_24_5': len(low),
                        'first_T_p3_le_24_5': min(low) if low else None, 'n_deltas': len(deltas),
                        'sign_changes': flips,
                        'mean_abs_dp3': (math.fsum(abs(d) for d in deltas) / len(deltas)) if deltas else None,
                        'n_k92_w': sum(1 for r in rs if r['k92_w']), 'n_k92_hb': sum(1 for r in rs if r['k92_hb']),
                        'selection_status_counts': st,
                        'n_warm_gt_held': sum(1 for r in rs if r['warm_gt_held'] is True),
                        'n_selected_gt_held': sum(1 for r in rs if r['selected_gt_held'] is True),
                        'first_T_csv_differs': first_diff,
                        'n_select_selected': sum(1 for r in rs if r.get('select_status') == 'selected')})
    return out


def v8():
    rec = stage_rec('V8')
    if rec:
        return rec
    rows = metric_rows()
    chains = chain_metrics(rows)
    h = wjson(VBR / 'judge' / 'vb_m.json', {'schema': 'k92vb-metrics/v1', 'rows': rows, 'chains': chains,
                                           'definitions': METRIC_DOC})
    stage_pass('V8', {'vb_m_sha256': h, 'n_rows': len(rows), 'n_chain_rows': len(chains)})
    logmd('V8 지표 표 `judge/vb_m.json` sha256 `%s` (결정 줄 %d, 사슬 줄 %d)' % (h, len(rows), len(chains)))
    return True


METRIC_DOC = (
    'Rows per (chain, side, T): side REC = RR record decision, OFF = hooked OFF chain (14 T), B1 = B1 chain (41 T). '
    'M1 p2/p3/p4 = green_times.SC109_p{2,3,4}. M4 floor = metadata[expected (173,p4) floor key of the run] '
    '(K92_VALUES /p0_2/f_expected_floor_keys), floor_keys_n, seed_binding = k92_hb_seed_binding, '
    'groups_carried/updated = head_observation_groups_*; VB-41w B1 floor_eq_max_rec_seed = floor == max(REC floor, s) '
    '(s when the REC floor is absent). M5 from the selected k92_record.json (amendment 32 section 3.6): chain_T450 = '
    'horizon.m1_chain_T450, chain_blocks = blocks[0..2].chain_sum, chain_max_450 = max over k92_series.npz rows with '
    't_end in (T, T+450] and the three chain keys finite of their sum, w_bound_ratio = w_capacity_bound_steps / '
    'w_steps_with_departures (None when the denominator is 0), e_out_over_220 = horizon.e_out_max_over_220; M5(e) = '
    'chain-level n_k92_w / n_k92_hb (metadata keys of the decision JSON). M6 outw = horizon.outw_veh_h_450, feed4 = '
    'horizon.feed4_veh_h_450, feed4_ratio = feed4 / outw (None when outw <= 0), omega = '
    'joint_leader_selection.selected_objective. M7 selection_status; warm_gt_held = warm_start_objective > '
    'held_objective (PFO result = warm_start_objective [interpretation, sdmpc.py:990-994]); selected_gt_held = '
    'selected_objective > held_objective; chain counts. M8 phantom_end = horizon.phantom_end_450. M9 csv_sha256, '
    'csv_same_as_rec, chain-level first_T_csv_differs; wall_run_sec (driver-measured adapter wall) and '
    'decision_wall_sec (metadata). M2 chain-level n_p3_le_24_5 (p3 <= 24.5) and first T. M3 deltas between '
    'consecutive chain decisions (T and the previous chain T, both present), sign changes counted over the deltas '
    'with |d| >= 0.5 in order, mean |d| over all deltas. Record-based fields are None with none_reason '
    'record:<select status> when the select status is not selected, and REC: recorder not run on the REC side.')


# ---------------------------------------------------------------------------------------------- V9, V10
def v9():
    rec = stage_rec('V9')
    if rec:
        return rec
    dest = VBR / 'recalc' / 'recalc.json'
    if dest.exists():
        stop('V9', 'S-K54', 'recalc output exists')
    mkdir(dest.parent)
    pre = L.vissim_count()
    rc, sec = child([PY, '-B', KV / 'vb_recalc.py', 'run', '--vbr', VBR, '--dest', dest], VBR / 'logs' / 'v9_recalc.txt',
                    KV, clean_env())
    step_line('V9_recalc', rc, sec, pre, L.vissim_count())
    r = read_json(dest) or {}
    if rc != 0 or r.get('equal') is not True:
        stop('V9', 'S-K15', 'VB-I5 false (recalc rc=%s equal=%s)' % (rc, r.get('equal')),
             {'n_diff': r.get('n_diff')})
    stage_pass('V9', {'recalc_sha256': sha(dest), 'equal': True, 'n_compared': r.get('n_compared')})
    logmd('V9 재계산 VB-I5 같음(비교 %s칸), `recalc/recalc.json` sha256 `%s`' % (r.get('n_compared'), sha(dest)))
    return True


def v10(v0doc):
    rec = stage_rec('V10')
    if rec:
        return rec
    a32 = pins_check(A32_PINS)
    vbp = pins_check(VB_PINS)
    gs = git_state()
    rr = rr_listing()
    ok2 = ok2_listing()
    doc = {'a32_pins_ok': len(a32) == 51 and all(x['ok'] for x in a32) and A32_PINS.read_bytes() ==
           EXPECTED_PINS.read_bytes(), 'vb_pins_ok': bool(vbp) and all(x['ok'] for x in vbp), 'git': gs,
           'rr_same': rr == v0doc['C9'], 'ok2_outside_vb_same': ok2 == v0doc['ok2_outside_vb'],
           'rr': rr, 'ok2_outside_vb': ok2, 'vissim': L.vissim_count(), 'free_gb': L.free_space_gb()}
    doc['ok'] = doc['a32_pins_ok'] and doc['vb_pins_ok'] and gs['ok'] and doc['rr_same'] and doc['ok2_outside_vb_same']
    if not doc['ok']:
        wjson(VBR / 'stages' / 'V10_failed.json', doc)
        stop('V10', 'S-K53', 'end comparison false', {k: doc[k] for k in ('a32_pins_ok', 'vb_pins_ok', 'rr_same',
                                                                       'ok2_outside_vb_same')})
    stage_pass('V10', doc)
    logmd('V10 끝 대조 OK: a32 고정 51/51·V-B 고정 목록 OK, GWT8 head `e27ceac8`·status 0·K8 `b9734abe`·원격 k92 0, '
          'RR 목록 sha = V0, OK2 의 vb 밖 = 스냅숏·로그뿐')
    return doc


# ---------------------------------------------------------------------------------------------- chain command
def cmd_chain():
    L.set_below_normal()
    resume = VBR.exists()
    v0doc = v0(resume)
    if not v0doc['ok']:
        print('V0 FALSE', json.dumps(v0doc['ok_by']), flush=True)
        if not resume:
            try:
                mkdir(VBR)
                wjson(VBR / 'check_v0.json', v0doc)
            except Exception:  # noqa: BLE001
                pass
        stop('V0', 'S-K53', 'precheck false', v0doc['ok_by'])
    mkdir(VBR)
    name = 'check_v0.json' if not resume else 'check_v0_resume_%s.json' % time.strftime('%Y%m%d_%H%M%S')
    h0 = wjson(VBR / name, v0doc)
    CTX.log = L.make_logger(VBR / 'driver_log.txt')
    if (VBR / 'stages' / 'V0.json').is_file():
        v0first = read_json(VBR / 'stages' / 'V0.json')
    else:
        stage_pass('V0', dict(v0doc, check_file=name, check_sha256=h0))
        v0first = read_json(VBR / 'stages' / 'V0.json')
    logmd('V0 사전 점검 %s 참(C1–C12), `%s` sha256 `%s`, 구동기 `%s`, 재계산기 `%s`' % (
        'resume' if resume else 'first', name, h0, sha(__file__), sha(KV / 'vb_recalc.py')))
    CTX.lib = load_pinned(AD32 / 'vb_lib32.py', LIB_SHA, 'vb_lib32')
    CTX.sel = load_pinned(AD32 / 'vb_select.py', SELECT_SHA, 'vb_select')
    if sha(AD32 / 'vb_closed_leaves.json') != CLOSED_SHA or sha(HOOKDIR / 'sitecustomize.py') != HOOK_SHA:
        stop('V0', 'S-K53', 'closed list / hook bytes differ')
    CTX.closed = CTX.lib.load_closed(AD32 / 'vb_closed_leaves.json')
    if sha(K92_VALUES) != K92_VALUES_SHA:
        stop('V0', 'S-K53', 'K92_VALUES.json differs')
    CTX.floor_keys = json.loads(K92_VALUES.read_text(encoding='utf-8'))['p0_2']['f_expected_floor_keys']
    CTX.base = base_env()
    snapshot('s38_vb_v0')
    v1()
    CTX.kc = load_pinned(VBT / SA_REL / 'k92_compare.py', KC_SHA, 'k92_compare_vb')
    CTX.a27 = load_pinned(VBT / SA_REL / 'k92_a27.py', A27M_SHA, 'k92_a27_vb')
    v2()
    v3()
    snapshot('s39_vb_zi')
    if not stage_rec('V4'):
        run_chain('off')
        stage_pass('V4', {'n': 14})
        logmd('V4 OFF 사슬 14결정 끝(종료 0)')
    v5()
    snapshot('s40_vb_off')
    if not stage_rec('V6'):
        run_chain('b1')
        stage_pass('V6', {'n': 41})
        logmd('V6 B1 사슬 41결정 끝(종료 0)')
    v7()
    v8()
    v9()
    snapshot('s41_vb_end')
    v10(v0first)
    CTX.log('CHAIN END all stages PASS')
    print('VB_CHAIN_DONE', flush=True)
    return 0


# ================================================================================================ self-tests (4.5)
ST = KV / 'selftest'
SYN = ST / 'syn'


def _w(p, data):
    p = Path(p)
    guard(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, (bytes, bytearray)):
        p.write_bytes(data)
    elif isinstance(data, str):
        p.write_text(data, encoding='utf-8')
    else:
        p.write_text(json.dumps(data), encoding='utf-8')
    return p


def st_launch(S):
    """4.5-1: the k92_replay.py bytes VBT will hold (GWT8 822dd78f) run in this process with subprocess.run caught."""
    kr_path = GWT8 / SA_REL / 'k92_replay.py'
    kr = load_pinned(kr_path, KR_SHA, 'k92_replay_st')
    wsroot = S / 'frozen_ws'           # the run's workspace root
    root = S / 'tree'                  # the replay root (VBT stand-in)
    runs = S / 'runs'
    run = 'sdmpc31_v3c3_syn_s41'
    dec = runs / run / ('decisions_' + run)
    for rel in ('evaluation/m/map.json', 'evaluation/c/cal.json'):
        _w(wsroot / rel, '{}')
        _w(root / rel, '{}')
    vbs = 'Const X = 1\r\nRW_DETECTOR_MAPPING_PATH = "D:\\fake\\det.json"\r\n'
    _w(wsroot / 'diag/scen/x.vbs', vbs)
    _w(root / 'diag/scen/x.vbs', vbs)
    _w(root / 'evaluation/controllers/vissim_stackelberg_adapter.py', '')
    _w(root / 'tuning.json', '{}')
    env_run = {'RW_PYTHON': PY, 'RW_STATE_LOG': '1', 'RW_OBSERVATION_CADENCE': '150'}
    prov = {'workspace_root': str(wsroot).replace('/', '\\'),
            'files': {'control_mapping': {'path': str(wsroot / 'evaluation/m/map.json')},
                      'calibration': {'path': str(wsroot / 'evaluation/c/cal.json')},
                      'generated_vbs_config': {'path': str(wsroot / 'diag/scen/x.vbs')}},
            'env': env_run}
    _w(runs / run / ('run_provenance_%s.json' % run), prov)
    _w(runs / run / 'launch_plan.json', {'control_start_sec': 900, 'controller': 'wu-link',
                                         'warmup_controller': 'no-control'})
    _w(dec / 'action_002850.json', '{"x": 1}')
    _w(dec / 'action_002850.csv', 'a\r\n')
    prev_sha = hashlib.sha256((dec / 'action_002850.json').read_bytes()).hexdigest()

    def manifest(d, sec, prev):
        m = {'schema': 'sdmpc31-replay-state/v1', 'sim_sec': sec, 'previous_sec': prev, 'source_decisions': str(dec),
             'state': {'replay': str(d / ('state_%06d.json' % sec))}, 'evidence': {'previous': {}}}
        if prev is not None:
            m['evidence']['previous']['.json'] = {'source': str(dec / ('action_%06d.json' % prev)), 'sha256': prev_sha}
        _w(d / 'replay_manifest.json', m)
        _w(d / ('state_%06d.json' % sec), '{}')

    base = {'PATH': r'C:\Windows', 'SYSTEMROOT': r'C:\Windows', 'RW_LEAK': 'x', 'K8_X': '1', 'PYTHONHASHSEED': '0',
            'NUMBA_CACHE_DIR': 'nc', 'PYTHONPATH': r'C:\elsewhere'}

    def via_replay(d, extra=''):
        captured = {}

        def fake_run(cmd, **kw):
            captured['argv'] = list(cmd)
            captured['cwd'] = kw.get('cwd')
            captured['env'] = dict(kw.get('env'))
            return types.SimpleNamespace(returncode=0)
        kr.subprocess = types.SimpleNamespace(run=fake_run)
        kr.os = types.SimpleNamespace(path=os.path, environ=dict(base))
        argv = ['k92_replay.py', '--replay-dir', str(d), '--root', str(root), '--tuning', str(root / 'tuning.json'),
                '--no-compare']
        if extra:
            argv += ['--extra-pythonpath', extra]
        old = sys.argv
        sys.argv = argv
        try:
            kr.main()
        except SystemExit as e:
            captured['exit'] = e.code
        finally:
            sys.argv = old
        return captured

    def via_driver(d, extra='', prev_override=None, out_dir=None):
        sec = int(json.loads((d / 'replay_manifest.json').read_text(encoding='utf-8'))['sim_sec'])
        od = Path(os.path.abspath(d)) / 'replay' if out_dir is None else Path(out_dir)
        la = adapter_launch(d, root, root / 'tuning.json', od / ('action_%06d.json' % sec),
                            od / ('action_%06d.csv' % sec), base=dict(base), extra_pythonpath=extra,
                            prev_override=prev_override)
        return la

    cases = {}
    da = S / 'prep_a'
    manifest(da, 1, None)
    ra, la = via_replay(da), via_driver(da)
    cases['a_T1'] = {'argv': ra['argv'] == la['argv'], 'cwd': ra['cwd'] == la['cwd'], 'env': ra['env'] == la['env'],
                     'exit0': ra.get('exit') == 0, 'controller_no_control': 'no-control' in la['argv']}
    db = S / 'prep_b'
    manifest(db, 3000, 2850)
    rb, lb = via_replay(db), via_driver(db)
    cases['b_record_prev'] = {'argv': rb['argv'] == lb['argv'], 'cwd': rb['cwd'] == lb['cwd'],
                              'env': rb['env'] == lb['env'], 'prev_is_record': lb['prev'] == str(dec / 'action_002850.json')}
    dc = S / 'prep_c'
    manifest(dc, 3000, 2850)
    rc_, lc = via_replay(dc, str(HOOKDIR)), via_driver(dc, str(HOOKDIR))
    cases['c_hookdir'] = {'argv': rc_['argv'] == lc['argv'], 'cwd': rc_['cwd'] == lc['cwd'],
                          'env': rc_['env'] == lc['env'],
                          'pythonpath_first_is_hookdir': lc['env']['PYTHONPATH'].split(';')[0] == str(HOOKDIR)}
    dd = S / 'prep_d'
    manifest(dd, 3000, 2850)
    chain_prev = _w(S / 'chain' / 'dec' / 'action_002850.json', '{"x": 2}')
    rd_ = via_replay(dd, str(HOOKDIR))
    ld = via_driver(dd, str(HOOKDIR), prev_override=chain_prev, out_dir=S / 'chain' / 'dec')
    diff_pos = [i for i, (x, y) in enumerate(zip(rd_['argv'], ld['argv'])) if x != y]
    names = sorted(rd_['argv'][i - 1] for i in diff_pos)
    env_on = dict(ld['env'])
    env_on.update(hook_env(3000, 41, 'ST/T003000', S / 'hook'))
    env_cmp = {k: v for k, v in env_on.items() if not k.startswith('K92VB_')}
    cases['d_chained'] = {'same_length': len(rd_['argv']) == len(ld['argv']),
                          'differs_only_at': names == ['--out-action-csv', '--out-action-json',
                                                       '--previous-action-json'],
                          'cwd': rd_['cwd'] == ld['cwd'], 'env_without_k92vb': rd_['env'] == env_cmp,
                          'k92vb_names': sorted(k for k in env_on if k.startswith('K92VB_')) == sorted(
                              hook_env(1, 1, '', '').keys())}
    # RW_ADAPTER_MODE -> --mode, and RW_* of the base env dropped
    prov2 = dict(prov, env=dict(env_run, RW_ADAPTER_MODE='lane'))
    _w(runs / run / ('run_provenance_%s.json' % run), prov2)
    de = S / 'prep_e'
    manifest(de, 3000, 2850)
    re_, le = via_replay(de), via_driver(de)
    cases['e_mode'] = {'argv': re_['argv'] == le['argv'], 'env': re_['env'] == le['env'],
                       'mode_arg': le['argv'][-2:] == ['--mode', 'lane'], 'rw_leak_dropped': 'RW_LEAK' not in le['env']}
    ok = all(all(v.values()) for v in cases.values())
    return {'ok': ok, 'cases': cases, 'k92_replay_sha256': KR_SHA, 'k92_replay_path': str(kr_path)}


def st_receipt(S):
    rows = []
    want = {('sdmpc31_v3c3_k8j1r_s31', 3000): '602f2a857c13546ea9f512297b3ce79906e4ff0b5147f50a2588f7c7507955a8',
            ('sdmpc31_v3c3_k8j1_s43', 3000): '61983196eb59ef0ee11de2703422ece699e4300f8b4ce2b7dd1e9ef0fc1fe917',
            ('sdmpc31_v3c3_k8j1_s41', 3000): 'f72c349e10bf098406ab508106311fe284772bb2522abc4302440a62d26772da',
            ('sdmpc31_v3c3_k8j1_s41', 900): '574dfdc1d5c962596c7605085223b3049b67a38fef05e253ba7e00ec7d152044',
            ('sdmpc31_v3c3_k8j1_s41', 2850): '561652c695f41c1201a87d50e2467fa07f187f1fd40a3d771329b8c27f91666b'}
    lib = CTX.lib
    for (run, prev), h in want.items():
        d = rr_dec(run)
        csv = d / ('action_%06d.csv' % prev)
        ack = d / ('action_%06d.json.applied' % prev)
        mine = lib.receipt_bytes(prev, str(csv), csv.stat().st_size)
        rec = ack.read_bytes()
        rows.append({'run': run, 'prev': prev, 'record_sha_is_pin': hashlib.sha256(rec).hexdigest() == h,
                     'bytes_equal': mine == rec})
    oj = _w(S / 'dec' / 'action_003150.json', '{}')
    oc = _w(S / 'dec' / 'action_003150.csv', 'a,b\r\n1,2\r\n')
    none = write_receipt_guarded(oj, oc)
    _w(Path(str(oj) + '.sdmpc_pending'), 'pending\n')
    w = write_receipt_guarded(oj, oc)
    data = Path(str(oj) + '.applied').read_bytes()
    lines = data.decode('utf-16').splitlines()
    parse = len(lines) == 3 and lines[0] == '3150' and Path(lines[1]).resolve() == oc.resolve() and \
        int(lines[2]) == oc.stat().st_size and data.startswith(b'\xff\xfe') and b'\r\x00\n\x00' in data
    try:
        write_receipt_guarded(oj, oc)
        again = False
    except SystemExit:
        again = True
    syn = {'no_pending_none': none is None, 'written': w is not None, 'parse': parse, 'never_overwrites': again}
    return {'ok': all(r['bytes_equal'] and r['record_sha_is_pin'] for r in rows) and all(syn.values()),
            'rr': rows, 'synthetic': syn}


def st_guard():
    ok_paths = [(VBR / 'chain' / 'x.json', False), (VBT / 'evaluation' / 'x.py', True), (VBT_BUILD, True),
                (KV / 'selftest' / 'x.json', False), (KB / 'LOG.md', False), (OK2 / 'snap' / 's38_vb_v0.json', False),
                (OK2 / 'snap' / 's41_vb_end.json', False), (OK2 / 'logs' / 'vb_chain.txt', False)]
    bad_paths = [(VBT / 'evaluation' / 'x.py', False), (VBT_BUILD, False),
                 (RR / 'sdmpc31_v3c3_k8j1_s41' / 'x.json', True), (FRZ8 / 'x.py', True), (FRZ8B / 'x.py', True),
                 (Path(r'D:/VISSIM-merge/frozen/sdmpc31_6c4c7400_202610011831/x'), True), (GWT8 / 'x.py', True),
                 (GWT8 / '.git', True), (REPO / '.git' / 'worktrees' / 'x', True), (K92ATTRIB / 'x', True),
                 (DA / 'x', True), (V4 / 'x', True), (OUTH / 'x', True), (OUTK / 'x', True), (SEALED / 'x', True),
                 (OK2 / 'commit' / 'x', True), (OK2 / 'snap' / 's02_after_probe_stop.json', True),
                 (OK2 / 'snap' / 's42_vb_x.json', True), (OK2 / 'logs' / 'other.txt', True), (OK2 / 'x.json', True),
                 (KB / 'other.md', True), (AD32 / 'vb_lib32.py', True), (HOOKDIR / 'x.py', True), (KI / 'x.py', True),
                 (TK / 'other' / 'x', True), (TK / 'vb_e27ceac8_interrupted_1' / 'x', True), (SP / 'x.md', True)]
    a = [allowed(p, v) for p, v in ok_paths]
    b = [not allowed(p, v) for p, v in bad_paths]
    raised = False
    try:
        guard(RR / 'x')
    except GuardError:
        raised = True
    return {'ok': all(a) and all(b) and raised, 'allowed_ok': a, 'denied_ok': b, 'guard_raises': raised}


def st_plan():
    rows = plan()
    want_off = {'VB-41w': TW, 'VB-31': [3000, 3150], 'VB-43': [3000, 3150], 'VB-41': [3000, 3150]}
    want_b1 = {'VB-41w': TW, 'VB-31': T3000, 'VB-43': T3000, 'VB-41': T3000}
    c = {}
    off = [r for r in rows if r['arm'] == 'off']
    b1 = [r for r in rows if r['arm'] == 'b1']
    c['n55'] = len(rows) == 55 and len(off) == 14 and len(b1) == 41
    c['order_off'] = [(r['chain'], r['T']) for r in off] == [(ch, T) for ch in ORDER for T in want_off[ch]]
    c['order_b1'] = [(r['chain'], r['T']) for r in b1] == [(ch, T) for ch in ORDER for T in want_b1[ch]]
    firsts = sorted((r['chain'], r['T']) for r in off if r['first'])
    c['first4'] = firsts == sorted([('VB-31', 3000), ('VB-43', 3000), ('VB-41', 3000), ('VB-41w', 1)])
    chained = sorted((r['chain'], r['T'], r['prev_T'], r['dtype']) for r in off if not r['first'])
    closed = sorted((d['chain'], d['T'], d['prev_T'], d['type']) for d in CTX.closed['decisions'])
    c['chained10_eq_closed'] = len(chained) == 10 and chained == closed
    c['first_prev'] = all((r['prev_T'] is None) if r['T'] == 1 else (r['prev_T'] == r['T'] - 150)
                          for r in rows if r['first'])
    c['old_roots'] = all(r['old_root'] == str({'VB-31': FRZ8B}.get(r['chain'], FRZ8)) for r in rows)
    want_tun = {('VB-31', 'off'): (str(VBT / CFG_REL), CFG_SHA), ('VB-31', 'b1'): (str(VBT / CFGB1_REL), CFGB1_SHA)}
    for ch in ('VB-43', 'VB-41', 'VB-41w'):
        want_tun[(ch, 'off')] = (str(VBT / SAFK91_REL), SAFK91_SHA)
        want_tun[(ch, 'b1')] = (str(VBR / 'arms' / 'sa' / 'tuning' / SAFB1_FILE), SAFB1_SHA)
    c['tunings'] = all((r['tuning'], r['tuning_sha256']) == want_tun[(r['chain'], r['arm'])] for r in rows)
    c['seeds_runs'] = all({'VB-31': (31, 'sdmpc31_v3c3_k8j1r_s31'), 'VB-43': (43, 'sdmpc31_v3c3_k8j1_s43'),
                           'VB-41': (41, 'sdmpc31_v3c3_k8j1_s41'), 'VB-41w': (41, 'sdmpc31_v3c3_k8j1_s41')}[r['chain']]
                          == (r['seed'], r['run']) for r in rows)
    c['controllers'] = all(r['controller'] == ('no-control' if r['T'] < 900 else 'wu-link') for r in rows)
    zi = {(run, T) for _c, run, T, _a in ZI_CELLS}
    vb = {(r['run'], r['T']) for r in rows}
    c['zi_outside_55'] = not (zi & vb)
    return {'ok': all(c.values()), 'checks': c, 'table': rows}


def st_judge(S):
    def doc(T, prior=0.0, snap=None, status='ok', extra=None, floor=None, key='head_discharge_floor_173_p4_aaaa'):
        md = {'controller_status': status, 'head_observation_prior_discarded': prior,
              'head_observation_snapshot_sec': float(T) if snap is None else snap}
        if floor is not None:
            md[key] = floor
        md.update(extra or {})
        return {'metadata': md}
    fk = 'head_discharge_floor_173_p4_aaaa'
    r = {}
    r['i2_true'] = vbi2(doc(3000), ['action_003000.json', 'action_003000.csv'], 3000, 0, 0)['ok'] is True
    r['i2_exception_key'] = vbi2(doc(3000, extra={'adapter_exception_text': 'x'}), [], 3000, 0, 0)['ok'] is False
    r['i2_hold_file'] = vbi2(doc(3000), ['action_003000.decision_hold.json'], 3000, 0, 0)['ok'] is False
    r['i2_error_file'] = vbi2(doc(3000), ['action_003000.error.txt'], 3000, 0, 0)['ok'] is False
    r['i2_prior_1_elsewhere'] = vbi2(doc(3000, prior=1.0), [], 3000, 0, 0)['ok'] is False
    r['i2_snapshot'] = vbi2(doc(3000, snap=2850.0), [], 3000, 0, 0)['ok'] is False
    r['i2_status'] = vbi2(doc(3000, status='hold'), [], 3000, 0, 0)['ok'] is False
    r['i2_exit'] = vbi2(doc(3000), [], 3000, 1, 0)['ok'] is False
    r['i2_df'] = vbi2(doc(3000), [], 3000, 0, 2)['ok'] is False
    t1 = doc(1, floor=SEED)
    r['i2_exc_true'] = vbi2(doc(150, prior=1.0, floor=SEED), [], 150, 0, 0,
                            exception={'floor_key': fk, 't1_doc': t1})['ok'] is True
    r['i2_exc_t1_lacks'] = vbi2(doc(150, prior=1.0, floor=SEED), [], 150, 0, 0,
                                exception={'floor_key': fk, 't1_doc': doc(1)})['ok'] is False
    r['i2_exc_floor_not_s'] = vbi2(doc(150, prior=1.0, floor=SEED + 1.0), [], 150, 0, 0,
                                   exception={'floor_key': fk, 't1_doc': t1})['ok'] is False
    r['i2_exc_prior_0'] = vbi2(doc(150, prior=0.0, floor=SEED), [], 150, 0, 0,
                               exception={'floor_key': fk, 't1_doc': t1})['ok'] is False
    good = [(T, doc(T, floor=v)) for T, v in ((3000, 1100.0), (3150, 1100.0), (3300, 1200.0))]
    r['i6_true'] = vbi6(good, fk, False)['ok'] is True
    two = [(3000, {'metadata': {fk: 1.0, 'head_discharge_floor_173_p4_bbbb': 2.0}})]
    r['i6_two_keys'] = vbi6(two, fk, False)['ok'] is False
    r['i6_name'] = vbi6([(3000, doc(3000, floor=1.0, key='head_discharge_floor_173_p4_cccc'))], fk, False)['ok'] is False
    r['i6_decreasing'] = vbi6([(3000, doc(3000, floor=2.0)), (3150, doc(3150, floor=1.0))], fk, False)['ok'] is False
    warm = [(1, doc(1, floor=SEED)), (150, doc(150, floor=SEED)), (300, doc(300, floor=SEED + 5))]
    r['i6_warm_true'] = vbi6(warm, fk, True)['ok'] is True
    r['i6_warm_150'] = vbi6([(1, doc(1, floor=SEED)), (150, doc(150, floor=SEED + 1))], fk, True)['ok'] is False

    def hook(d, loaded=(('vissim_stackelberg_adapter.py', True), ('sdmpc_tangent_worker.py', True)), cands=1,
             err=False, missing=False, status='selected'):
        h, rc = d / 'hook', d / 'rec'
        for i, (a, ok) in enumerate(loaded):
            _w(h / ('loaded_%d.json' % (100 + i)), {'argv0': a, 'recorder_ok': ok})
        for i in range(cands):
            _w(h / ('c_101_%04d' % (i + 1)) / 'cand.json', {})
            if not (missing and i == 0):
                _w(h / ('c_101_%04d' % (i + 1)) / 'k92_record.json', {})
        if err:
            _w(h / 'hook_error_101.txt', 'x')
        if status is not None:
            _w(rc / 'k92_select.json', {'status': status})
        return vbi7(h, rc)['ok']
    r['i7_true'] = hook(S / 'h1') is True
    r['i7_error'] = hook(S / 'h2', err=True) is False
    r['i7_recorder_false'] = hook(S / 'h3', loaded=(('vissim_stackelberg_adapter.py', False),)) is False
    r['i7_missing_record'] = hook(S / 'h4', missing=True) is False
    r['i7_two_adapters'] = hook(S / 'h5', loaded=(('vissim_stackelberg_adapter.py', True),
                                                 ('vissim_stackelberg_adapter.py', True))) is False
    r['i7_status_hook_error'] = hook(S / 'h6', status='hook_error') is False
    r['i7_no_select'] = hook(S / 'h7', status=None) is False
    r['i7_no_candidate_ok'] = hook(S / 'h8', cands=0, status='no_candidate') is True
    return {'ok': all(r.values()), 'cases': r}


def st_resume(S):
    cd = S / 'vb41w_b1'
    Pa = decision_paths(cd, 150)
    _w(Pa['json'], '{"a": 1}')
    _w(Pa['csv'], 'a\r\n')
    _w(Pa['done'], {'exit': 0, 'out_sha256': {'json': sha(Pa['json']), 'csv': sha(Pa['csv'])}})
    for k in ('prep', 'hook', 'rec'):
        _w(Pa[k] / 'x.txt', 'x')
    Pb = decision_paths(cd, 300)
    _w(Pb['prep'] / 'state_000300.json', '{}')
    _w(Pb['hook'] / 'loaded_1.json', '{}')
    _w(Pb['dec'] / 'action_000300.json', '{}')
    _w(Pb['dec'] / 'action_000300.stdout.txt', '')
    _w(Pb['dec'] / 'run_t000300.json', '{}')
    Pm = decision_paths(cd, 450)
    _w(Pm['json'], '{"m": 1}')
    _w(Pm['csv'], 'm\r\n')
    _w(Pm['done'], {'exit': 0, 'out_sha256': {'json': 'x', 'csv': 'y'}})
    r = {'done': classify_decision(cd, 150) == 'done', 'half': classify_decision(cd, 300) == 'half',
         'fresh': classify_decision(cd, 600) == 'fresh', 'done_mismatch': classify_decision(cd, 450) == 'done_mismatch'}
    moved = move_interrupted(cd, 300, '20990101_000000')
    r['moved_prep'] = (cd / 'prep' / 't000300_interrupted_20990101_000000').is_dir() and not Pb['prep'].exists()
    r['moved_hook'] = (cd / 'hook' / 't000300_interrupted_20990101_000000').is_dir()
    box = cd / 'dec' / '_interrupted_20990101_000000_t000300'
    r['moved_dec_files'] = sorted(p.name for p in box.iterdir()) == ['action_000300.json', 'action_000300.stdout.txt',
                                                                   'run_t000300.json']
    r['after_move_fresh'] = classify_decision(cd, 300) == 'fresh'
    r['done_untouched'] = Pa['json'].is_file() and classify_decision(cd, 150) == 'done'
    r['n_moved'] = len(moved) == 5
    # a stage with a passed record is not run again
    global VBR
    real = VBR
    try:
        VBR = S / 'vbr'
        _w(VBR / 'stages' / 'V5.json', {'stage': 'V5', 'passed': True})
        _w(VBR / 'judge' / 'vb_i1.json', {'x': 1})
        r['stage_skip'] = v5() == {'stage': 'V5', 'passed': True}
    finally:
        VBR = real
    return {'ok': all(r.values()), 'cases': r}


def st_ad32():
    pins = {}
    for line in A32_PINS.read_text(encoding='utf-8').splitlines()[:3]:
        h, p = line.split(' *', 1)
        pins[Path(p).name] = h
    lib = load_pinned(AD32 / 'vb_lib32.py', LIB_SHA, 'vb_lib32_st')
    sel = load_pinned(AD32 / 'vb_select.py', SELECT_SHA, 'vb_select_st')
    r = {'pins_lines_1_3': pins == {'sitecustomize.py': HOOK_SHA, 'vb_select.py': SELECT_SHA,
                                    'vb_lib32.py': LIB_SHA},
         'lib_loaded_from_ad32': Path(lib.__file__).resolve() == (AD32 / 'vb_lib32.py').resolve(),
         'select_loaded_from_ad32': Path(sel.__file__).resolve() == (AD32 / 'vb_select.py').resolve(),
         'lib_sha': lib.__pinned_sha256__ == LIB_SHA, 'select_sha': sel.__pinned_sha256__ == SELECT_SHA,
         'hook_sha': sha(HOOKDIR / 'sitecustomize.py') == HOOK_SHA,
         'closed_sha': sha(AD32 / 'vb_closed_leaves.json') == CLOSED_SHA,
         'select_cli_is_ad32': True}
    try:
        load_pinned(AD32 / 'vb_lib32.py', '0' * 64, 'x')
        r['wrong_sha_refused'] = False
    except SystemExit:
        r['wrong_sha_refused'] = True
    return {'ok': all(r.values()), 'cases': r}


def cmd_selftest():
    L.set_below_normal()
    real_popen, real_run = subprocess.Popen, subprocess.run

    def no_child(*a, **k):
        raise RuntimeError('self-test started a child process')
    subprocess.Popen = no_child
    subprocess.run = no_child
    try:
        if SYN.exists():
            guard(SYN)
            shutil.rmtree(L.lp(SYN))
        mkdir(SYN)
        CTX.lib = load_pinned(AD32 / 'vb_lib32.py', LIB_SHA, 'vb_lib32')
        CTX.closed = CTX.lib.load_closed(AD32 / 'vb_closed_leaves.json')
        CTX.log = lambda m: None
        res = {'schema': 'k92vb-selftest/v1', 'driver_sha256': sha(__file__), 'when': now()}
        for name, fn in (('t1_launch', lambda: st_launch(SYN / 'launch')),
                         ('t2_receipt', lambda: st_receipt(SYN / 'receipt')),
                         ('t3_guard', st_guard), ('t4_plan', st_plan), ('t5_judge', lambda: st_judge(SYN / 'judge')),
                         ('t6_resume', lambda: st_resume(SYN / 'resume')), ('t7_ad32', st_ad32)):
            try:
                res[name] = fn()
            except Exception as e:  # noqa: BLE001
                import traceback
                res[name] = {'ok': False, 'error': repr(e), 'tb': traceback.format_exc()}
        res['ok'] = all(res[k]['ok'] for k in res if k.startswith('t'))
    finally:
        subprocess.Popen, subprocess.run = real_popen, real_run
    out = ST / 'vb_selftest.json'
    guard(out)
    out.write_text(json.dumps(res, indent=1, sort_keys=True, default=str) + '\n', encoding='utf-8')
    print('VB_SELFTEST ok=%s %s sha=%s' % (res['ok'], {k: res[k]['ok'] for k in res if k.startswith('t')}, sha(out)))
    return 0 if res['ok'] else 1


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'selftest':
        sys.exit(cmd_selftest())
    if len(sys.argv) == 2 and sys.argv[1] == 'chain':
        try:
            sys.exit(cmd_chain())
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception as exc:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            if VBR.is_dir():
                stop('crash', 'S-K15', 'driver exception: %r' % exc)
            raise
    print(__doc__)
    sys.exit(2)
