"""Data-free checks of the K8_PREDECLARATION_AMENDMENT_33 tools (Declare A33).  Diagnostics only, never committed.
SYNTHETIC inputs only.  Read-only exceptions that carry no V-B data: the committed recorder bytes (GWT8 k92_record.py,
sha 1d1dfa36..., copied into the synthetic tree), the committed K9-2-5 comparator k92_compare.py and k92_a27.py (GWT8,
imported read-only for the path-rule check on path STRINGS), the amendment-32 hook (AD32/vbhook, loaded read-only into
synthetic children to reproduce the collision of the stopped run), vb_select.py (AD32, run as a child on synthetic
folders), and the amendment-33 driver / recalculator (KV2, imported for their VB-I7 / selection functions on synthetic
folders; the driver's import runs only its module-level constants).  No decision replay, no adapter, no VISSIM.

    python -B dry_a33.py all      -> dry/decl/dry_a33_<part>.json for part in static, hook, pidreuse, paths, mutants and
                                     dry_a33_summary.json; prints one line per part

PID reuse is forced in a synthetic child: the child starts with `python -S` (no site at start), replaces os.getpid (and,
in some cases, time.time_ns / os.urandom) by constants, and only then runs site.main(), which imports sitecustomize
(the hook) exactly as a normal start does.  Two such children with the same constant pid = "the OS handed the same
process id to two processes of one decision".  Every child process: python -B, PYTHONHASHSEED=0, BELOW_NORMAL (inherited
from this process), env without RW_ / K8_ / K8G_ / K92A_ / K92VB_ unless the case sets K92VB_*."""
import ast
import difflib
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
from pathlib import Path

sys.dont_write_bytecode = True
AD33 = Path(__file__).resolve().parent
KB = AD33.parent
AD32 = KB / 'a32decl'
KV = KB / 'k92_vb'
KV2 = KB / 'k92_vb2'
DRY = AD33 / 'dry'
OUTD = DRY / 'decl'
SYN = DRY / 'syn'
PY = r'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
BELOW_NORMAL = 0x00004000
GWT8_SA = Path(r'D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/k8_gates/sa')
RECORDER_SHA = '1d1dfa36efbfa68e6ccc19cbeeb53f241437b1c5145e06fb843a9564661d4f90'
COMPARE_SHA = '3e2da987ff9e7b54ba2f51ad1b73bfdaf55f868bd6dedbf7937cf1f22fa4caba'
A27M_SHA = 'd4ab3f3d4e91492e02f1b7c30807ad34744c3e7590cf890bcc1275c79baa00f5'
OLD_HOOK_SHA = '4d7e0375116c3f805aa223651da0dc1c0c04b7d3315062e98e21137ba60aa321'
SELECT_SHA = '33adfd5033c277a3ad640f745a69efb2a929b27c1ff2a88d794dfa69b489e9cc'
OLD_DRIVER_SHA = '4dc9297df760800ebb20948b05ba94a645d93a8c7e44abb64c511d1be21d6e99'
OLD_RECALC_SHA = 'cab7939df8fd55ff4d7df36b058f8892d045a9aff5610b17c8f81f336d5c3e7c'
NEW_HOOK = AD33 / 'vbhook'
OLD_HOOK = AD32 / 'vbhook'
ADAPTER = 'vissim_stackelberg_adapter.py'
WORKER = 'sdmpc_tangent_worker.py'
FAKE_PID = 4242
TOKEN_RE = r'([0-9]+)_([0-9]+)_([0-9a-f]{16})'
C_RE = re.compile(r'^c_' + TOKEN_RE + r'_([0-9]{4})$')
L_RE = re.compile(r'^loaded_' + TOKEN_RE + r'\.json$')
E_RE = re.compile(r'^hook_error_' + TOKEN_RE + r'\.txt$')
S_RE = re.compile(r'^hook_setup_error_(?:' + TOKEN_RE + r'|[0-9]+_notoken)\.txt$')

# ------------------------------------------------------------------- declared hook diff (amendment 33 section 2.3)
DECL_REMOVED = sorted([
    "# k92_series.npz into <K92VB_HOOK_DIR>/c_<pid>_<seq:04d>/; the hook adds cand.json there (the action signature read",
    "# hook_error_<pid>.txt (setup: hook_setup_error_<pid>.txt); nothing is raised into the original program.  The per-call",
    "# folder number comes from a counter under a threading.Lock.",
    "def _setup():",
    "        with open(os.path.join(_OUT, 'loaded_%d.json' % pid), 'w', encoding='utf-8') as h:",
    "    with open(os.path.join(_OUT, 'loaded_%d.json' % pid), 'w', encoding='utf-8') as h:",
    "                with open(os.path.join(_OUT, 'hook_error_%d.txt' % pid), 'a', encoding='utf-8') as h:",
    "        folder = os.path.join(_OUT, 'c_%d_%04d' % (pid, seq))",
    "        os.makedirs(folder)",
    "        with open(os.path.join(folder, 'cand.json'), 'w', encoding='utf-8') as h:",
    "        _setup()",
    "            with open(os.path.join(_OUT, 'hook_setup_error_%d.txt' % os.getpid()), 'w', encoding='utf-8') as _h:",
])
DECL_ADDED = sorted([
    "# Amendment 33 (user decision D-K9-65): only the names of the files / folders this hook writes changed.  Every name",
    "# carries a per-process token <pid>_<time_ns>_<16 hex> drawn once at setup (the OS process id, the wall clock in ns and",
    "# 8 bytes of os.urandom), so a process id the OS hands out again inside one decision never meets an earlier name; every",
    "# file / folder is created exclusively (os.mkdir, open mode 'x'; the error files are append-only) and never overwritten.",
    "# k92_series.npz into <K92VB_HOOK_DIR>/c_<token>_<seq:04d>/; the hook adds cand.json there (the action signature read",
    "# hook_error_<token>.txt (setup: hook_setup_error_<token>.txt); nothing is raised into the original program.  The",
    "# per-call folder number comes from a counter under a threading.Lock.",
    "def _proc_token():",
    "    \"\"\"'<pid>_<time_ns>_<16 hex>', drawn once per process (amendment 33 section 2.1).  os.urandom reads the OS random",
    "    source; the random module and numpy random states are not touched.\"\"\"",
    "    import time",
    "    return '%d_%d_%s' % (os.getpid(), time.time_ns(), os.urandom(8).hex())",
    "",
    "",
    "def _setup(tok):",
    "        with open(os.path.join(_OUT, 'loaded_%s.json' % tok), 'x', encoding='utf-8') as h:",
    "    with open(os.path.join(_OUT, 'loaded_%s.json' % tok), 'x', encoding='utf-8') as h:",
    "                with open(os.path.join(_OUT, 'hook_error_%s.txt' % tok), 'a', encoding='utf-8') as h:",
    "        folder = os.path.join(_OUT, 'c_%s_%04d' % (tok, seq))",
    "        os.mkdir(folder)",
    "        with open(os.path.join(folder, 'cand.json'), 'x', encoding='utf-8') as h:",
    "    _TOK = None",
    "        _TOK = _proc_token()",
    "        _setup(_TOK)",
    "            _name = 'hook_setup_error_%s.txt' % (_TOK if _TOK else '%d_notoken' % os.getpid())",
    "            with open(os.path.join(_OUT, _name), 'a', encoding='utf-8') as _h:",
])
# top-level definitions of the driver / recalculator that differ from the amendment-32 bytes (section 3.2)
DECL_DRIVER_DEFS = sorted(['allowed', 'archive_bytes', 'archive_listing', 'cmd_chain', 'ok2_listing', 'pin_line_ok',
                           'pins_check', 'st_ad32', 'st_guard', 'st_judge', 'v0', 'v1', 'v10', 'v9'])
DECL_RECALC_DEFS = sorted(['selftest'])


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


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
    return k32.GetPriorityClass(h) == BELOW_NORMAL


def load_module(path, name, want=None):
    if want is not None and sha_file(path) != want:
        raise SystemExit('pinned module differs: %s' % path)
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, default=repr) + '\n', encoding='utf-8')
    return sha_file(path)


def clean_env(extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith(('RW_', 'K8_', 'K8G_', 'K92A_', 'K92VB_', 'DRY33_'))}
    env.update(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
    env.pop('PYTHONPATH', None)
    env.update(extra or {})
    return env


# ================================================================================================ synthetic program
PKG_SDMPC = '''"""Synthetic sdmpc module (dry_a33): omega_costs reads point.cost_rows only, like the real one reads its rows."""
import math


def _v(x):
    return x.value if hasattr(x, 'value') and not isinstance(x, (int, float)) else x


def omega_costs(point, cfg):
    total = math.fsum(float(r['dt_h']) * math.fsum(_v(v) for v in r['inside_veh'].values()) for r in point.cost_rows)
    return {'SC109': {'cost': total}}, {'schema': 'synthetic', 'costs': {'SC109': total}, 'total_veh_h': total}


def other_fn(point, cfg):
    return 0.0
'''
PKG_OTHER = '''def omega_costs(point, cfg):
    return 'decoy'
'''
PKG_DUAL = '''class Dual:
    __slots__ = ('value', 'tangent', 'trace', 'risks')

    def __init__(self, value, tangent=None, trace=None, risks=(0, 0)):
        self.value = float(value)
        self.tangent = tangent
        self.trace = trace
        self.risks = risks

    def __float__(self):
        raise TypeError('Dual is not convertible by float() (like the real sdmpc_dual.Dual)')
'''
# The bootstrap runs before anything else.  With DRY33_SITE_LATE=1 the child was started with -S: the constants are put
# in place first and site.main() then imports sitecustomize (the hook), so the hook sees them at its setup.
BOOT = r'''import os
import sys
if os.environ.get('DRY33_FAKE_PID'):
    os.getpid = (lambda _v=int(os.environ['DRY33_FAKE_PID']): _v)
if os.environ.get('DRY33_FAKE_NS'):
    import time as _t
    _t.time_ns = (lambda _v=int(os.environ['DRY33_FAKE_NS']): _v)
if os.environ.get('DRY33_FAKE_RAND'):
    os.urandom = (lambda n, _b=bytes.fromhex(os.environ['DRY33_FAKE_RAND']): (_b * (n // len(_b) + 1))[:n])
if os.environ.get('DRY33_SITE_LATE') == '1':
    import site
    site.main()
'''
CHILD = r'''"""Synthetic decision program (dry_a33).  argv: mode out_json."""
import json
import threading
import types
sys.dont_write_bytecode = True
import numpy  # noqa: F401  (the real worker has numpy loaded before any omega_costs call)
import sdmpc
import other
from evaluation.controllers.sdmpc_dual import Dual

MODE, OUT = sys.argv[1], sys.argv[2]
BEFORE = set(sys.modules)
T0 = 3000.0
CHAIN = ('movement:SC109_W_SC108_to_E', 'movement:SC109_W_SC108_to_N_SC16', 'storage:SC108_to_SC109')


def rows(ad=False, shift=0.0):
    out = []
    for i in range(9):
        s = T0 + 50.0 * i
        mv = {CHAIN[0]: 10.0 + i + shift, CHAIN[1]: 2.0 + 0.5 * i, CHAIN[2]: 1.0 + 0.25 * i,
              'storage:SC109_E_out': 100.0 + 10.0 * i, 'movement:SC109_N_SC16_to_W_SC108': 3.0 + i,
              'storage:in_SC108_S': 5.0, 'movement:other': 7.0}
        iv = {k: (v - 1.0 if k in ('storage:in_SC108_S', 'movement:other') else v) for k, v in mv.items()}
        if ad:
            mv = {k: Dual(v) for k, v in mv.items()}
            iv = {k: Dual(v) for k, v in iv.items()}
        out.append({'start_sec': s, 'end_sec': s + 50.0, 'dt_h': 50.0 / 3600.0, 'stage': 'urban',
                    'model_stock_veh': mv, 'inside_veh': iv})
    return out


def transfers():
    out = []
    for i in range(9):
        e = T0 + 50.0 * (i + 1)
        out.append({'source': 'movement:SC109_W_SC108_to_E', 'target': 'storage:SC109_E_out', 'end_sec': e,
                    'vehicles': 4.0 + i})
        out.append({'source': 'movement:SC109_W_SC108_to_N_SC16', 'target': 'x', 'end_sec': e, 'vehicles': 1.0})
        out.append({'source': 'movement:other', 'target': 'y', 'end_sec': e, 'vehicles': 9.0})
    return out


class RaisingPoint:
    def __init__(self, r):
        self.cost_rows = r
        self.states = [1, 2, 3]

    @property
    def control_area_response(self):
        raise RuntimeError('synthetic: the response cannot be read')


def point(ad=False, shift=0.0, raising=False):
    r = rows(ad, shift)
    if raising:
        return RaisingPoint(r)
    return types.SimpleNamespace(control_area_response={'residence': r, 'transfers': transfers()}, cost_rows=r,
                                 states=[1, 2, 3], control_area={'ttt_veh_h': 0.0})


CFG = types.SimpleNamespace(
    network=types.SimpleNamespace(movement_capacity_by_movement_veh_h={'SC109_W_SC108_to_E': 5209.8,
                                                                       'SC109_W_SC108_to_N_SC16': 413.0612},
                                  head_floor_seed=None),
    simulation=types.SimpleNamespace(T_c_sec=150.0))


def act(g3, off=21.309, fut=(23.5, 24.5)):
    return types.SimpleNamespace(
        green_times={'SC109_p2': 56.45, 'SC109_p3': g3, 'SC109_p4': 60.962},
        offsets={'SC109': off, 'SC1': 4.0},
        diagnostics={'sdmpc_prediction_sequence': {'future': [{'green_times': {'SC109_p2': 56.0, 'SC109_p3': f,
                                                                               'SC109_p4': 60.0}} for f in fut]}})


def predict(action, pt, cfg):
    return sdmpc.omega_costs(pt, cfg)


results = []
if MODE == 'normal':
    results.append(predict(act(23.588), point(), CFG)[1]['total_veh_h'])      # A, non-AD
    results.append(predict(act(26.0), point(shift=1.0), CFG)[1]['total_veh_h'])  # B, non-AD
    results.append(predict(act(23.588), point(ad=True), CFG)[1]['total_veh_h'])  # A, AD values
elif MODE == 'idle':
    pass
elif MODE == 'raising':
    results.append(predict(act(23.588), point(raising=True), CFG)[1]['total_veh_h'])
elif MODE == 'threads':
    res = {}

    def work(i):
        res[i] = predict(act(20.0 + i), point(shift=float(i)), CFG)[1]['total_veh_h']
    th = [threading.Thread(target=work, args=(i,)) for i in range(4)]
    for t in th:
        t.start()
    for t in th:
        t.join()
    results = [res[i] for i in range(4)]
elif MODE == 'decoy':
    results.append(other.omega_costs(point(), CFG))
    results.append(sdmpc.other_fn(point(), CFG))
else:
    raise SystemExit('mode')
new = sorted(set(sys.modules) - BEFORE)
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump({'mode': MODE, 'results': results, 'new_modules': new, 'pid_seen': os.getpid(),
               'k92_record_in_sys_modules': any(m == 'k92_record' or m.endswith('.k92_record') for m in sys.modules),
               'evaluation_modules': sorted(m for m in sys.modules if m.startswith(('evaluation', 'src')))}, f)
'''


def build_syn():
    if SYN.exists():
        shutil.rmtree(SYN)
    pkg = SYN / 'pkg'
    (pkg / 'evaluation' / 'controllers').mkdir(parents=True)
    (pkg / 'sdmpc.py').write_text(PKG_SDMPC, encoding='utf-8')
    (pkg / 'other.py').write_text(PKG_OTHER, encoding='utf-8')
    (pkg / 'evaluation' / '__init__.py').write_text('', encoding='utf-8')
    (pkg / 'evaluation' / 'controllers' / '__init__.py').write_text('', encoding='utf-8')
    (pkg / 'evaluation' / 'controllers' / 'sdmpc_dual.py').write_text(PKG_DUAL, encoding='utf-8')
    for name in (ADAPTER, WORKER, 'other_child.py'):
        d = SYN / ('prog_' + name.split('.')[0])
        d.mkdir(parents=True)
        (d / name).write_text(BOOT + CHILD, encoding='utf-8')
    tree = SYN / 'tree' / 'diagnostics' / 'sdmpc_n31_20260924' / 'k8_gates' / 'sa'
    tree.mkdir(parents=True)
    shutil.copy2(GWT8_SA / 'k92_record.py', tree / 'k92_record.py')
    if sha_file(tree / 'k92_record.py') != RECORDER_SHA:
        raise SystemExit('recorder copy sha differs')
    bad = SYN / 'tree_bad' / 'k92_record.py'
    bad.parent.mkdir(parents=True)
    bad.write_bytes((tree / 'k92_record.py').read_bytes() + b'\n# changed\n')
    return tree / 'k92_record.py', bad


def run_child(case, mode, *, hook_dir=None, hook_path=True, recorder=None, rec_sha=RECORDER_SHA, prog='adapter',
              drop=None, hook_code=None, fake_pid=None, fake_ns=None, fake_rand=None, popen=False, T='3000'):
    """One synthetic program run.  fake_* -> started with -S and the constants set before site.main() (the hook)."""
    out = SYN / 'out' / (case + '.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    pp = [str(hook_code or NEW_HOOK)] if hook_path else []
    pp.append(str(SYN / 'pkg'))
    extra = {'PYTHONPATH': os.pathsep.join(pp)}
    late = fake_pid is not None or fake_ns is not None or fake_rand is not None
    if late:
        extra['DRY33_SITE_LATE'] = '1'
        if fake_pid is not None:
            extra['DRY33_FAKE_PID'] = str(fake_pid)
        if fake_ns is not None:
            extra['DRY33_FAKE_NS'] = str(fake_ns)
        if fake_rand is not None:
            extra['DRY33_FAKE_RAND'] = fake_rand
    if hook_dir is not None:
        extra.update(K92VB_HOOK_DIR=str(hook_dir), K92VB_RECORDER=str(recorder), K92VB_RECORDER_SHA256=rec_sha,
                     K92VB_T=T, K92VB_SEED='41', K92VB_LABEL='dry33/%s' % case)
        for k in drop or ():
            extra.pop(k, None)
    name = {'adapter': ADAPTER, 'worker': WORKER, 'other': 'other_child.py'}[prog]
    script = SYN / ('prog_' + name.split('.')[0]) / name
    argv = [PY, '-B'] + (['-S'] if late else []) + [str(script), mode, str(out)]
    if popen:
        return subprocess.Popen(argv, cwd=str(script.parent), env=clean_env(extra), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True), out
    t0 = time.perf_counter()
    p = subprocess.run(argv, cwd=str(script.parent), env=clean_env(extra), capture_output=True, text=True,
                       timeout=600)
    res = {'rc': p.returncode, 'sec': round(time.perf_counter() - t0, 2), 'stderr_tail': p.stderr[-800:],
           'late_site': late}
    res['out'] = json.loads(out.read_text(encoding='utf-8')) if out.is_file() else None
    return res


def finish(popen_pair):
    p, out = popen_pair
    so, se = p.communicate(timeout=600)
    return {'rc': p.returncode, 'stderr_tail': se[-800:],
            'out': json.loads(out.read_text(encoding='utf-8')) if out.is_file() else None}


def hook_listing(hdir):
    hdir = Path(hdir)
    if not hdir.exists():
        return {'exists': False}
    cands = sorted(p.name for p in hdir.glob('c_*'))
    return {'exists': True, 'loaded': sorted(p.name for p in hdir.glob('loaded_*.json')), 'candidates': cands,
            'errors': sorted(p.name for p in hdir.glob('hook_error_*.txt')),
            'setup_errors': sorted(p.name for p in hdir.glob('hook_setup_error_*.txt')),
            'files_per_candidate': {c: sorted(x.name for x in (hdir / c).iterdir()) for c in cands}}


def tree_shas(hdir):
    out = {}
    for p in sorted(Path(hdir).rglob('*')):
        if p.is_file():
            out[str(p.relative_to(hdir)).replace('\\', '/')] = sha_file(p)
    return out


def names_ok(lst):
    """Every name in a hook folder written by the amendment-33 hook carries a token (section 2.1)."""
    return (all(L_RE.match(n) for n in lst.get('loaded', [])) and all(C_RE.match(n) for n in lst.get('candidates', []))
            and all(E_RE.match(n) for n in lst.get('errors', []))
            and all(S_RE.match(n) for n in lst.get('setup_errors', [])))


def tokens_of(lst):
    return sorted({L_RE.match(n).group(0)[len('loaded_'):-len('.json')] for n in lst.get('loaded', [])
                   if L_RE.match(n)})


def expected_record(shift=0.0):
    """Independent arithmetic of the synthetic program's record (amendment 32 section 3.6 fields)."""
    T0, dt = 3000.0, 150.0
    rows = []
    for i in range(9):
        s = T0 + 50.0 * i
        mv = {'E': 10.0 + i + shift, 'L': 2.0 + 0.5 * i, 'S': 1.0 + 0.25 * i, 'EO': 100.0 + 10.0 * i, 'PH': 3.0 + i,
              'F4': 5.0, 'O': 7.0}
        rows.append((s + 50.0, mv))
    dt_h = 50.0 / 3600.0
    blocks = []
    for k in (1, 2, 3):
        t_end = T0 + dt * k
        end = [mv for e, mv in rows if abs(e - t_end) < 1e-6][-1]
        inb = [mv for e, mv in rows if T0 + dt * (k - 1) < e <= t_end + 1e-9]
        dep_w = math.fsum(4.0 + i for i in range(9) if T0 + dt * (k - 1) < T0 + 50.0 * (i + 1) <= t_end + 1e-9)
        blocks.append({'chain_sum': end['E'] + end['L'] + end['S'], 'e_out_end': end['EO'],
                       'e_out_max': max(m['EO'] for m in inb), 'outw': math.fsum(dt_h * 2.0 for _ in inb),
                       'feed4': math.fsum(dt_h * 1.0 for _ in inb), 'phantom_end': end['PH'], 'dep_w': dep_w})
    return {'m1_chain_T150': blocks[0]['chain_sum'], 'm1_chain_T450': blocks[2]['chain_sum'],
            'e_out_max_over_220': max(b['e_out_max'] for b in blocks) / 220.0,
            'outw_veh_h_450': math.fsum(b['outw'] for b in blocks),
            'feed4_veh_h_450': math.fsum(b['feed4'] for b in blocks), 'phantom_end_450': blocks[2]['phantom_end'],
            'm2_w_dep_T450': math.fsum(b['dep_w'] for b in blocks), 'w_steps_with_departures': 9}


def near(a, b):
    return a is not None and b is not None and abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


def out_action(path, g3, *, fut=(23.5, 24.5), off=21.309, sdmpc_active=True):
    doc = {'green_times': {'SC109_p2': 56.45, 'SC109_p3': g3, 'SC109_p4': 60.962}, 'offsets': {'SC109': off, 'SC1': 4.0},
           'diagnostics': {'sdmpc_prediction_sequence': {'future': [{'green_times': {
               'SC109_p2': 56.0, 'SC109_p3': f, 'SC109_p4': 60.0}} for f in fut]}},
           'metadata': {'sdmpc_active': sdmpc_active, 'controller_status': 'ok'}}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(doc), encoding='utf-8')
    return Path(path)


def run_select(hook_dir, action_json, dest, T=3000):
    p = subprocess.run([PY, '-B', str(AD32 / 'vb_select.py'), 'select', '--hook-dir', str(hook_dir), '--action-json',
                        str(action_json), '--T', str(T), '--dest', str(dest)], capture_output=True, text=True,
                       env=clean_env(), timeout=600)
    sel = json.loads((Path(dest) / 'k92_select.json').read_text(encoding='utf-8')) \
        if (Path(dest) / 'k92_select.json').is_file() else None
    return p.returncode, sel


# ================================================================================================ parts
def _imports(path):
    mods = set()
    for n in ast.walk(ast.parse(Path(path).read_text(encoding='utf-8'))):
        if isinstance(n, ast.Import):
            mods |= {a.name.split('.')[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            mods.add((n.module or '').split('.')[0])
    return mods


def _defs(path):
    src = Path(path).read_text(encoding='utf-8')
    tree = ast.parse(src)
    out = {}
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            out[n.name] = ast.get_source_segment(src, n)
    return out


def _diff_lines(a, b):
    la = Path(a).read_text(encoding='utf-8').splitlines()
    lb = Path(b).read_text(encoding='utf-8').splitlines()
    rem, add = [], []
    for line in difflib.unified_diff(la, lb, lineterm='', n=0):
        if line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
            continue
        if line.startswith('-'):
            rem.append(line[1:])
        elif line.startswith('+'):
            add.append(line[1:])
    return rem, add


def part_static():
    res = {}
    hook = NEW_HOOK / 'sitecustomize.py'
    mods = _imports(hook)
    res['hook_imports'] = sorted(mods)
    res['hook_stdlib_only'] = mods <= {'os', 'sys', 'hashlib', 'json', 'threading', 'time', 'traceback', 'types'}
    res['hookdir_files'] = sorted(p.name for p in NEW_HOOK.iterdir())
    text = hook.read_text(encoding='utf-8')
    tree = ast.parse(text)
    modes, makedirs_args, mkdir_args = [], [], []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name) and f.id == 'open':
                m = n.args[1] if len(n.args) > 1 else next((k.value for k in n.keywords if k.arg == 'mode'), None)
                modes.append(m.value if isinstance(m, ast.Constant) else '<default r>' if m is None else '<expr>')
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == 'os':
                if f.attr == 'makedirs':
                    makedirs_args.append(ast.unparse(n))
                if f.attr == 'mkdir':
                    mkdir_args.append(ast.unparse(n))
    res['open_modes'] = sorted(modes)
    res['no_w_mode'] = all(m in ('rb', 'x', 'a') for m in modes) and modes.count('x') == 3 and modes.count('a') == 2
    res['makedirs_only_hook_root'] = makedirs_args == ["os.makedirs(_OUT, exist_ok=True)"] * 2
    res['mkdir_candidate'] = mkdir_args == ['os.mkdir(folder)']
    consts = sorted({n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
                     and re.match(r'^(loaded_|c_|hook_error_|hook_setup_error_|%d_)', n.value)})
    res['name_formats'] = consts
    res['name_formats_ok'] = consts == ['%d_%d_%s', '%d_notoken', 'c_%s_%04d', 'hook_error_%s.txt',
                                        'hook_setup_error_%s.txt', 'loaded_%s.json']
    res['token_source'] = "return '%d_%d_%s' % (os.getpid(), time.time_ns(), os.urandom(8).hex())" in text
    res['target_gate_calls'] = ("_TARGET = ('omega_costs', 'sdmpc.py')" in text
                                and "_OUT = os.environ.get('K92VB_HOOK_DIR')" in text and '\nif _OUT:\n' in text
                                and all(s in text for s in ('mod.network_facts(cfg)', 'mod.collect(resp, T, dt)',
                                                            'mod.write(folder, job, T, dt, _H, None)')))
    rem, add = _diff_lines(OLD_HOOK / 'sitecustomize.py', hook)
    res['hook_diff'] = {'removed': len(rem), 'added': len(add), 'removed_eq_declared': sorted(rem) == DECL_REMOVED,
                        'added_eq_declared': sorted(add) == DECL_ADDED,
                        'old_hook_sha_is_pinned': sha_file(OLD_HOOK / 'sitecustomize.py') == OLD_HOOK_SHA}
    od, nd = _defs(KV / 'vb_chain.py'), _defs(KV2 / 'vb_chain.py')
    changed = sorted(k for k in set(od) | set(nd) if od.get(k) != nd.get(k))
    res['driver_changed_defs'] = changed
    res['driver_defs_eq_declared'] = changed == DECL_DRIVER_DEFS
    res['driver_imports_same'] = _imports(KV / 'vb_chain.py') == _imports(KV2 / 'vb_chain.py')
    orc, nrc = _defs(KV / 'vb_recalc.py'), _defs(KV2 / 'vb_recalc.py')
    changed_r = sorted(k for k in set(orc) | set(nrc) if orc.get(k) != nrc.get(k))
    res['recalc_changed_defs'] = changed_r
    res['recalc_defs_eq_declared'] = changed_r == DECL_RECALC_DEFS
    res['recalc_imports_same'] = _imports(KV / 'vb_recalc.py') == _imports(KV2 / 'vb_recalc.py')
    res['old_tools_pinned'] = (sha_file(KV / 'vb_chain.py') == OLD_DRIVER_SHA
                               and sha_file(KV / 'vb_recalc.py') == OLD_RECALC_SHA
                               and sha_file(AD32 / 'vb_select.py') == SELECT_SHA)
    res['ok'] = bool(res['hook_stdlib_only'] and res['hookdir_files'] == ['sitecustomize.py'] and res['no_w_mode']
                     and res['makedirs_only_hook_root'] and res['mkdir_candidate'] and res['name_formats_ok']
                     and res['token_source'] and res['target_gate_calls'] and res['hook_diff']['removed_eq_declared']
                     and res['hook_diff']['added_eq_declared'] and res['hook_diff']['old_hook_sha_is_pinned']
                     and res['driver_defs_eq_declared'] and res['driver_imports_same'] and res['recalc_defs_eq_declared']
                     and res['recalc_imports_same'] and res['old_tools_pinned'])
    return res


def part_hook(recorder, bad):
    """The amendment-32 hook cases (dry_a32 part 'hook') again with the amendment-33 hook: same expectations, names
    carry the token."""
    cases = {}
    H = SYN / 'hooks'
    base = run_child('base_nohookpath', 'normal', hook_path=False)
    off = run_child('off_envabsent', 'normal')
    on = run_child('on_normal', 'normal', hook_dir=H / 'on_normal', recorder=recorder)
    cases['base'] = {'rc': base['rc'], 'results': base['out']['results'] if base['out'] else None}
    cases['off'] = {'rc': off['rc'], 'same_results_as_base': off['out'] and off['out']['results'] == base['out']['results'],
                    'no_hook_files': not (H / 'off_envabsent').exists(),
                    'same_modules_as_base': off['out'] and off['out']['new_modules'] == base['out']['new_modules']}
    cases['off']['ok'] = bool(off['rc'] == 0 and cases['off']['same_results_as_base'] and cases['off']['no_hook_files']
                              and cases['off']['same_modules_as_base'])
    lst = hook_listing(H / 'on_normal')
    extra_mods = sorted(set(on['out']['new_modules']) - set(base['out']['new_modules'])) if on['out'] else None
    c = {'rc': on['rc'], 'same_results_as_base': on['out'] and on['out']['results'] == base['out']['results'],
         'listing': lst, 'extra_modules_vs_base': extra_mods, 'names_ok': names_ok(lst),
         'no_evaluation_or_src_added': on['out'] and on['out']['evaluation_modules'] == base['out']['evaluation_modules'],
         'k92_record_not_in_sys_modules': on['out'] and on['out']['k92_record_in_sys_modules'] is False}
    c['three_candidates'] = len(lst.get('candidates', [])) == 3 and not lst.get('errors') and not lst.get('setup_errors')
    c['one_token'] = len({C_RE.match(x).group(1, 2, 3) for x in lst.get('candidates', [])}) == 1 and \
        [C_RE.match(x).group(4) for x in lst.get('candidates', [])] == ['0001', '0002', '0003']
    c['files_ok'] = all(v == ['cand.json', 'k92_record.json', 'k92_series.npz']
                        for v in lst.get('files_per_candidate', {}).values())
    metas = [json.loads((H / 'on_normal' / x / 'cand.json').read_text(encoding='utf-8')) for x in lst.get('candidates', [])]
    recs = [json.loads((H / 'on_normal' / x / 'k92_record.json').read_text(encoding='utf-8'))
            for x in lst.get('candidates', [])]
    c['ad_flags'] = [m['is_ad'] for m in metas]
    c['signatures_p3'] = [m['signature']['green_times']['SC109_p3'] for m in metas]
    c['meta_fields'] = all(m['first_row_start_sec'] == 3000.0 and m['dt_sec'] == 150.0 and m['n_states'] == 3
                           and m['n_residence_rows'] == 9 and m['n_transfer_rows'] == 27 and m['T'] == 3000.0
                           and m['seed'] == 41 and m['recorder_sha256'] == RECORDER_SHA
                           and m['action_from'] == [1, 'predict'] and m['pid'] == on['out']['pid_seen']
                           for m in metas)
    c['cand_keys_same_as_a32'] = all(sorted(m) == sorted(['schema', 'seq', 'pid', 'ppid', 'argv0', 'thread', 'time_ns',
                                                          'label', 'T', 'seed', 'H', 'callers', 'recorder_sha256',
                                                          'action_from', 'signature', 'n_residence_rows',
                                                          'n_transfer_rows', 'first_row_start_sec', 'n_states', 'dt_sec',
                                                          'record_errors', 'is_ad', 'incomplete_types', 'hook_sec'])
                                     for m in metas)
    exp = [expected_record(0.0), expected_record(1.0), expected_record(0.0)]
    checks = []
    for r, e in zip(recs, exp):
        hz = r.get('horizon') or {}
        row = {k: near(hz.get(k), v) if not isinstance(v, int) else hz.get(k) == v for k, v in e.items()}
        row['schema'] = r.get('schema') == 'k92-record/v1'
        row['T0'] = r.get('T0') == 3000.0 and r.get('block_sec') == 150.0 and r.get('H') == 3
        row['capacity'] = (r.get('capacity') or {}).get('SC109_W_SC108_to_E') == 5209.8
        row['seed_reason'] = r.get('seed') == 41 and r.get('vissim') is None and r.get('vissim_reason') == 'k92_vissim_ref'
        row['no_errors'] = r.get('errors') == []
        row['keyed_none'] = r.get('keyed') is None
        checks.append(row)
    c['record_checks'] = checks
    c['records_ok'] = all(all(v for v in row.values()) for row in checks)
    lj = [json.loads((H / 'on_normal' / x).read_text(encoding='utf-8')) for x in lst.get('loaded', [])]
    c['loaded_keys_same_as_a32'] = all(sorted(j) == sorted(['schema', 'pid', 'ppid', 'argv0', 'executable', 'python',
                                                            'hook_out', 'recorder', 'recorder_sha256_expected', 'label',
                                                            'started_ns', 'T', 'seed', 'recorder_sha256', 'recorder_ok'])
                                       for j in lj) and len(lj) == 1
    c['ok'] = bool(on['rc'] == 0 and c['same_results_as_base'] and c['three_candidates'] and c['files_ok']
                   and c['no_evaluation_or_src_added'] and c['k92_record_not_in_sys_modules'] and c['meta_fields']
                   and c['records_ok'] and c['ad_flags'] == [False, False, True] and c['names_ok'] and c['one_token']
                   and c['signatures_p3'] == [23.588, 26.0, 23.588] and c['cand_keys_same_as_a32']
                   and c['loaded_keys_same_as_a32'])
    cases['on_normal'] = c
    sm = run_child('on_badsha', 'normal', hook_dir=H / 'on_badsha', recorder=bad)
    lst = hook_listing(H / 'on_badsha')
    lj = [json.loads((H / 'on_badsha' / x).read_text(encoding='utf-8')) for x in lst.get('loaded', [])]
    cases['badsha'] = {'rc': sm['rc'], 'same_results_as_base': sm['out']['results'] == base['out']['results'],
                       'listing': lst, 'recorder_ok': [x.get('recorder_ok') for x in lj], 'names_ok': names_ok(lst)}
    cases['badsha']['ok'] = (sm['rc'] == 0 and cases['badsha']['same_results_as_base'] and not lst['candidates']
                             and len(lst['setup_errors']) == 1 and cases['badsha']['recorder_ok'] == [False]
                             and names_ok(lst))
    mt = run_child('on_noT', 'normal', hook_dir=H / 'on_noT', recorder=recorder, drop=('K92VB_T',))
    lst = hook_listing(H / 'on_noT')
    cases['missingT'] = {'rc': mt['rc'], 'same_results_as_base': mt['out']['results'] == base['out']['results'],
                         'listing': lst, 'names_ok': names_ok(lst)}
    cases['missingT']['ok'] = (mt['rc'] == 0 and cases['missingT']['same_results_as_base'] and not lst['candidates']
                               and len(lst['setup_errors']) == 1 and len(lst['loaded']) == 1 and names_ok(lst))
    rb = run_child('base_raising', 'raising', hook_path=False)
    ra = run_child('on_raising', 'raising', hook_dir=H / 'on_raising', recorder=recorder)
    lst = hook_listing(H / 'on_raising')
    cases['raising'] = {'rc': ra['rc'], 'same_results_as_base': ra['out'] and rb['out'] and
                        ra['out']['results'] == rb['out']['results'], 'listing': lst, 'names_ok': names_ok(lst)}
    cases['raising']['ok'] = (ra['rc'] == 0 and rb['rc'] == 0 and cases['raising']['same_results_as_base']
                              and len(lst['errors']) == 1 and len(lst['candidates']) == 1
                              and lst['files_per_candidate'][lst['candidates'][0]] == [] and names_ok(lst))
    tb = run_child('base_threads', 'threads', hook_path=False)
    ta = run_child('on_threads', 'threads', hook_dir=H / 'on_threads', recorder=recorder)
    lst = hook_listing(H / 'on_threads')
    cases['threads'] = {'rc': ta['rc'], 'same_results_as_base': ta['out']['results'] == tb['out']['results'],
                        'listing_n': len(lst['candidates']), 'errors': lst['errors'], 'names_ok': names_ok(lst)}
    cases['threads']['ok'] = (ta['rc'] == 0 and cases['threads']['same_results_as_base'] and len(lst['candidates']) == 4
                              and not lst['errors'] and len(set(lst['candidates'])) == 4 and names_ok(lst))
    da = run_child('on_decoy', 'decoy', hook_dir=H / 'on_decoy', recorder=recorder)
    lst = hook_listing(H / 'on_decoy')
    cases['decoy'] = {'rc': da['rc'], 'listing': lst}
    cases['decoy']['ok'] = da['rc'] == 0 and lst['candidates'] == [] and not lst['errors'] and len(lst['loaded']) == 1
    oa = run_child('on_otherprog', 'normal', hook_dir=H / 'on_otherprog', recorder=recorder, prog='other')
    lst = hook_listing(H / 'on_otherprog')
    cases['otherprog'] = {'rc': oa['rc'], 'listing_n': len(lst['candidates'])}
    cases['otherprog']['ok'] = oa['rc'] == 0 and len(lst['candidates']) == 3
    ok = base['rc'] == 0 and all(v.get('ok', True) for k, v in cases.items() if isinstance(v, dict) and k != 'base')
    return {'cases': cases, 'ok': bool(ok), 'base_results': base['out']['results'] if base['out'] else None}


def part_pidreuse(recorder, base_results):
    """Section 4: forced PID reuse.  The amendment-32 hook collides (reproduces the stopped run); the amendment-33 hook
    does not; a forced full token collision is refused by exclusive creation (no overwrite) and is visible (STOP side)."""
    drv = load_module(KV2 / 'vb_chain.py', 'vb_chain_dry33')
    rcl = load_module(KV2 / 'vb_recalc.py', 'vb_recalc_dry33')
    H = SYN / 'pid'
    cases = {}

    def decision_folder(name, hook_code, workers, *, adapter=True):
        """One synthetic decision: optional adapter (normal start, no omega_costs call) + workers [(fake pid or None,
        fake ns, fake rand)] started one after another (each exits before the next starts)."""
        hd = H / name / 'hook'
        hd.mkdir(parents=True)
        runs = []
        if adapter:
            runs.append(run_child('%s_adapter' % name, 'idle', hook_dir=hd, recorder=recorder, hook_code=hook_code))
        for i, (fp, fns, frand) in enumerate(workers):
            runs.append(run_child('%s_w%d' % (name, i), 'normal', hook_dir=hd, recorder=recorder, hook_code=hook_code,
                                  prog='worker', fake_pid=fp, fake_ns=fns, fake_rand=frand))
        return hd, runs

    def judge(name, hd, runs):
        lst = hook_listing(hd)
        act = out_action(H / name / 'dec' / 'action_003000.json', 23.588)
        rc_s, sel = run_select(hd, act, H / name / 'rec')
        i7 = drv.vbi7(hd, H / name / 'rec')
        rs = rcl.reselect(hd, json.loads(act.read_text(encoding='utf-8')), 3000)
        ri7 = rcl.i7_of(hd, H / name / 'rec')
        return {'listing': lst, 'n_loaded': len(lst['loaded']), 'n_candidates': len(lst['candidates']),
                'errors': lst['errors'], 'setup_errors': lst['setup_errors'],
                'rcs': [r['rc'] for r in runs], 'pids_seen': [r['out']['pid_seen'] if r['out'] else None for r in runs],
                'results_same_as_base': all(r['out'] and (r['out']['results'] == base_results or r['out']['mode'] == 'idle'
                                                          and r['out']['results'] == []) for r in runs),
                'select_rc': rc_s, 'select_status': (sel or {}).get('status'), 'select_n_match': (sel or {}).get('n_match'),
                'select_chosen': (sel or {}).get('chosen'), 'vbi7_driver': i7['ok'], 'vbi7_checks': i7['checks'],
                'recalc_status': rs['status'], 'recalc_chosen': rs.get('chosen'), 'recalc_i7': ri7['ok'],
                'select_eq_recalc': (sel or {}).get('status') == rs['status'] and (
                    ((sel or {}).get('chosen') or {}).get('folder') == rs.get('chosen')) and (
                    ((sel or {}).get('chosen') or {}).get('record_sha256') == rs.get('chosen_record_sha256'))}

    # P1 amendment-32 hook, two workers with the same pid one after another -> collision (the stopped run, synthetic)
    hd, runs = decision_folder('p1_old_seq', OLD_HOOK, [(FAKE_PID, None, None), (FAKE_PID, None, None)])
    j = judge('p1_old_seq', hd, runs)
    j['ok'] = (j['rcs'] == [0, 0, 0] and j['results_same_as_base'] and j['pids_seen'][1:] == [FAKE_PID, FAKE_PID]
               and j['n_loaded'] == 2 and len(j['errors']) == 1 and j['select_status'] == 'hook_error'
               and j['vbi7_driver'] is False and j['recalc_status'] == 'hook_error' and j['recalc_i7'] is False)
    j['reproduces_stop'] = 'loaded_%d.json overwritten (2 loaded files for 3 processes), hook_error_%d.txt' % (
        FAKE_PID, FAKE_PID)
    cases['P1_old_hook_sequential_same_pid'] = j
    # P2 amendment-33 hook, same scenario -> no collision
    hd, runs = decision_folder('p2_new_seq', NEW_HOOK, [(FAKE_PID, None, None), (FAKE_PID, None, None)])
    j = judge('p2_new_seq', hd, runs)
    toks = tokens_of(j['listing'])
    j['tokens'] = toks
    j['ok'] = (j['rcs'] == [0, 0, 0] and j['results_same_as_base'] and j['pids_seen'][1:] == [FAKE_PID, FAKE_PID]
               and j['n_loaded'] == 3 and len(set(toks)) == 3
               and sum(1 for t in toks if t.startswith('%d_' % FAKE_PID)) == 2 and j['n_candidates'] == 6
               and not j['errors'] and not j['setup_errors'] and names_ok(j['listing'])
               and j['select_status'] == 'selected' and j['select_n_match'] == 4
               and (j['select_chosen'] or {}).get('pid') == FAKE_PID
               and (j['select_chosen'] or {}).get('folder', '').endswith('_0001') and j['vbi7_driver'] is True
               and j['recalc_status'] == 'selected' and j['recalc_i7'] is True and j['select_eq_recalc'])
    cases['P2_new_hook_sequential_same_pid'] = j
    # P3 amendment-33 hook, two workers with the same pid at the same time (cannot happen in the OS; robustness)
    hd = H / 'p3_new_conc' / 'hook'
    hd.mkdir(parents=True)
    ra = run_child('p3_new_conc_adapter', 'idle', hook_dir=hd, recorder=recorder)
    pa = run_child('p3_new_conc_w0', 'normal', hook_dir=hd, recorder=recorder, prog='worker', fake_pid=FAKE_PID,
                   popen=True)
    pb = run_child('p3_new_conc_w1', 'normal', hook_dir=hd, recorder=recorder, prog='worker', fake_pid=FAKE_PID,
                   popen=True)
    runs = [ra, finish(pa), finish(pb)]
    j = judge('p3_new_conc', hd, runs)
    j['ok'] = (j['rcs'] == [0, 0, 0] and j['results_same_as_base'] and j['n_loaded'] == 3 and j['n_candidates'] == 6
               and not j['errors'] and not j['setup_errors'] and names_ok(j['listing'])
               and j['select_status'] == 'selected' and j['vbi7_driver'] is True and j['select_eq_recalc'])
    cases['P3_new_hook_concurrent_same_pid'] = j
    # P4 amendment-33 hook, same pid AND same time_ns (clock tie) -> the random part still separates
    ns = 1761111111000000000
    hd, runs = decision_folder('p4_new_same_ns', NEW_HOOK, [(FAKE_PID, ns, None), (FAKE_PID, ns, None)])
    j = judge('p4_new_same_ns', hd, runs)
    toks = tokens_of(j['listing'])
    j['tokens'] = toks
    j['ok'] = (j['rcs'] == [0, 0, 0] and j['results_same_as_base'] and j['n_loaded'] == 3
               and sum(1 for t in toks if t.startswith('%d_%d_' % (FAKE_PID, ns))) == 2 and j['n_candidates'] == 6
               and not j['errors'] and not j['setup_errors'] and j['select_status'] == 'selected'
               and j['vbi7_driver'] is True and j['select_eq_recalc'])
    cases['P4_new_hook_same_pid_same_ns'] = j
    # P5 amendment-33 hook, forced FULL token collision (same pid, same ns, same random bytes): the second process
    # cannot create its loaded file ('x') -> setup error appended, hook inert in it; the first process's files unchanged
    name = 'p5_new_full_collision'
    hd = H / name / 'hook'
    hd.mkdir(parents=True)
    r0 = run_child(name + '_adapter', 'idle', hook_dir=hd, recorder=recorder)
    r1 = run_child(name + '_w0', 'normal', hook_dir=hd, recorder=recorder, prog='worker', fake_pid=FAKE_PID, fake_ns=ns,
                   fake_rand='00112233aabbccdd')
    before = tree_shas(hd)
    r2 = run_child(name + '_w1', 'normal', hook_dir=hd, recorder=recorder, prog='worker', fake_pid=FAKE_PID, fake_ns=ns,
                   fake_rand='00112233aabbccdd')
    after = tree_shas(hd)
    j = judge(name, hd, [r0, r1, r2])
    j['first_process_files_unchanged'] = all(after.get(k) == v for k, v in before.items())
    j['new_files'] = sorted(set(after) - set(before))
    j['ok'] = (j['rcs'] == [0, 0, 0] and j['results_same_as_base'] and j['first_process_files_unchanged']
               and j['new_files'] == ['hook_setup_error_%d_%d_00112233aabbccdd.txt' % (FAKE_PID, ns)]
               and j['n_loaded'] == 2 and j['n_candidates'] == 3 and j['select_status'] == 'hook_error'
               and j['vbi7_driver'] is False and j['recalc_i7'] is False)
    cases['P5_new_hook_forced_full_collision'] = j
    # P6 one decision with the shape of the stopped VB-41 T=3,150 decision: adapter + 4 workers, two of them with the
    # same pid (not adjacent) and two with their own pid
    hd, runs = decision_folder('p6_new_decision', NEW_HOOK, [(None, None, None), (FAKE_PID, None, None),
                                                            (None, None, None), (FAKE_PID, None, None)])
    j = judge('p6_new_decision', hd, runs)
    j['ok'] = (j['rcs'] == [0] * 5 and j['results_same_as_base'] and j['n_loaded'] == 5 and j['n_candidates'] == 12
               and not j['errors'] and not j['setup_errors'] and j['select_status'] == 'selected'
               and j['select_n_match'] == 8 and j['vbi7_driver'] is True and j['recalc_i7'] is True
               and j['select_eq_recalc'] and names_ok(j['listing']))
    cases['P6_new_hook_decision_shape'] = j
    # P7 across decisions: the same pid in two decisions' folders -> each folder judged alone, both selected
    hd_a, runs_a = decision_folder('p7_dec_a', NEW_HOOK, [(FAKE_PID, None, None)])
    hd_b, runs_b = decision_folder('p7_dec_b', NEW_HOOK, [(FAKE_PID, None, None)])
    ja, jb = judge('p7_dec_a', hd_a, runs_a), judge('p7_dec_b', hd_b, runs_b)
    cases['P7_across_decisions'] = {'a': {k: ja[k] for k in ('n_loaded', 'n_candidates', 'select_status', 'vbi7_driver')},
                                    'b': {k: jb[k] for k in ('n_loaded', 'n_candidates', 'select_status', 'vbi7_driver')},
                                    'ok': ja['select_status'] == jb['select_status'] == 'selected'
                                    and ja['vbi7_driver'] is True and jb['vbi7_driver'] is True
                                    and not set(os.listdir(hd_a)) & set(os.listdir(hd_b))}
    # P8 control: a -S start without constants = a normal start (same results, same record bytes of candidate 1)
    c_norm = run_child('p8_normal_start', 'normal', hook_dir=H / 'p8_norm', recorder=recorder, prog='worker')
    hd8 = H / 'p8_late' / 'hook'
    hd8.mkdir(parents=True)
    late = subprocess.run([PY, '-B', '-S', str(SYN / 'prog_sdmpc_tangent_worker' / WORKER), 'normal',
                           str(SYN / 'out' / 'p8_late.json')], cwd=str(SYN / 'prog_sdmpc_tangent_worker'),
                          env=clean_env({'PYTHONPATH': os.pathsep.join([str(NEW_HOOK), str(SYN / 'pkg')]),
                                         'DRY33_SITE_LATE': '1', 'K92VB_HOOK_DIR': str(hd8),
                                         'K92VB_RECORDER': str(recorder), 'K92VB_RECORDER_SHA256': RECORDER_SHA,
                                         'K92VB_T': '3000', 'K92VB_SEED': '41',
                                         'K92VB_LABEL': 'dry33/p8_normal_start'}),
                          capture_output=True, text=True, timeout=600)
    ln, ll = hook_listing(H / 'p8_norm'), hook_listing(hd8)
    rec_n = [sha_file(H / 'p8_norm' / c / 'k92_record.json') for c in ln['candidates']]
    rec_l = [sha_file(hd8 / c / 'k92_record.json') for c in ll['candidates']]
    out_l = json.loads((SYN / 'out' / 'p8_late.json').read_text(encoding='utf-8'))
    cases['P8_control_late_site_equals_normal'] = {
        'rc': [c_norm['rc'], late.returncode], 'results_same': c_norm['out']['results'] == out_l['results'] ==
        base_results, 'records_same_bytes': rec_n == rec_l and len(rec_n) == 3,
        'ok': c_norm['rc'] == 0 and late.returncode == 0 and c_norm['out']['results'] == out_l['results'] == base_results
        and rec_n == rec_l and len(rec_n) == 3}
    ok = all(v['ok'] for v in cases.values())
    return {'cases': cases, 'ok': bool(ok), 'fake_pid': FAKE_PID}


def part_paths():
    """The new tree / output names under the comparison rules (path STRINGS only)."""
    a27 = load_module(GWT8_SA / 'k92_a27.py', 'k92_a27_dry33', A27M_SHA)
    kc = load_module(GWT8_SA / 'k92_compare.py', 'k92_compare_dry33', COMPARE_SHA)
    new_vbt = 'D:/VISSIM-merge/k8_gate_trees/k92b1/vb2_e27ceac8'
    old_vbt = 'D:/VISSIM-merge/k8_gate_trees/k92b1/vb_e27ceac8'
    f = '/evaluation/controllers/runtime_setup.py'
    vbr_new = 'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/vb2/chain/vb41_off/dec/action_003000.csv'
    vbr_old = 'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/vb/chain/vb41_off/dec/action_003000.csv'
    r = {'tree_root_ok_new': a27.tree_root_ok(new_vbt), 'tree_root_ok_old': a27.tree_root_ok(old_vbt),
         'norm_new_tree_file': kc.norm_s(new_vbt + f), 'norm_old_tree_file': kc.norm_s(old_vbt + f),
         'norm_new_backslash': kc.norm_s(new_vbt.replace('/', '\\') + f.replace('/', '\\')),
         'norm_vbr_new': kc.norm_s(vbr_new), 'norm_vbr_old': kc.norm_s(vbr_old)}
    r['ok'] = (r['tree_root_ok_new'] is True and r['tree_root_ok_old'] is True
               and r['norm_new_tree_file'] == r['norm_old_tree_file'] == '<root>' + f
               and r['norm_new_backslash'] == '<root>' + f
               and r['norm_vbr_new'] != r['norm_vbr_old'] and '/vb2/' in r['norm_vbr_new'])
    r['note'] = ('VBT names map to <root> (same as the stopped run); OK2 output paths are not mapped by N, as before '
                 '(amendment 32 section 4.4) -- vb2 vs vb only changes path text in the report-only leaves')
    return r


def _mutant_hook(name, edits):
    src = (NEW_HOOK / 'sitecustomize.py').read_text(encoding='utf-8')
    for old, new in edits:
        if src.count(old) < 1:
            raise SystemExit('mutant %s: anchor missing: %s' % (name, old))
        src = src.replace(old, new)
    d = SYN / 'mutants' / name
    d.mkdir(parents=True)
    (d / 'sitecustomize.py').write_text(src, encoding='utf-8')
    return d


def part_mutants(recorder, base_results):
    """Each mutant undoes one part of the fix; the PID-reuse checks must catch it."""
    drv = load_module(KV2 / 'vb_chain.py', 'vb_chain_dry33m')
    M = {}
    ns = 1761111111000000000

    def seq_pair(name, code, fakes):
        hd = SYN / 'mpid' / name / 'hook'
        hd.mkdir(parents=True)
        run_child(name + '_adapter', 'idle', hook_dir=hd, recorder=recorder, hook_code=code)
        r1 = run_child(name + '_w0', 'normal', hook_dir=hd, recorder=recorder, hook_code=code, prog='worker', **fakes)
        before = tree_shas(hd)
        r2 = run_child(name + '_w1', 'normal', hook_dir=hd, recorder=recorder, hook_code=code, prog='worker', **fakes)
        after = tree_shas(hd)
        lst = hook_listing(hd)
        act = out_action(SYN / 'mpid' / name / 'dec' / 'action_003000.json', 23.588)
        rc_s, sel = run_select(hd, act, SYN / 'mpid' / name / 'rec')
        return {'n_loaded': len(lst['loaded']), 'n_candidates': len(lst['candidates']), 'errors': len(lst['errors']),
                'setup_errors': len(lst['setup_errors']),
                'first_files_unchanged': all(after.get(k) == v for k, v in before.items()),
                'select_status': (sel or {}).get('status'), 'vbi7': drv.vbi7(hd, SYN / 'mpid' / name / 'rec')['ok'],
                'rcs': [r1['rc'], r2['rc']]}

    def caught(o, *, collision_expected=True):
        """The amendment-33 PID-reuse rule: 3 loaded files, 6 candidates, no error, first files unchanged, selected."""
        clean = (o['n_loaded'] == 3 and o['n_candidates'] == 6 and o['errors'] == 0 and o['setup_errors'] == 0
                 and o['first_files_unchanged'] and o['select_status'] == 'selected' and o['vbi7'])
        return not clean
    m1 = _mutant_hook('M1_pid_only_candidate', [("'c_%s_%04d' % (tok, seq)", "'c_%d_%04d' % (os.getpid(), seq)")])
    o = seq_pair('M1', m1, {'fake_pid': FAKE_PID})
    M['M1_candidate_name_pid_only'] = dict(o, caught=caught(o))
    m2 = _mutant_hook('M2_loaded_pid_w', [("'loaded_%s.json' % tok), 'x'", "'loaded_%d.json' % os.getpid()), 'w'")])
    o = seq_pair('M2', m2, {'fake_pid': FAKE_PID})
    M['M2_loaded_pid_name_w_mode'] = dict(o, caught=caught(o))
    m3 = _mutant_hook('M3_no_random', [("os.urandom(8).hex()", "'0000000000000000'")])
    o = seq_pair('M3', m3, {'fake_pid': FAKE_PID, 'fake_ns': ns})
    M['M3_token_without_random_clock_tie'] = dict(o, caught=caught(o))
    m4 = _mutant_hook('M4_overwrite', [("'loaded_%s.json' % tok), 'x'", "'loaded_%s.json' % tok), 'w'"),
                                       ("os.mkdir(folder)", "os.makedirs(folder, exist_ok=True)"),
                                       ("'cand.json'), 'x'", "'cand.json'), 'w'")])
    o = seq_pair('M4', m4, {'fake_pid': FAKE_PID, 'fake_ns': ns, 'fake_rand': '00112233aabbccdd'})
    # M4 under a forced full collision: the declared rule is "refused and visible" (P5); an overwriting hook leaves no
    # error file and changes the first process's files
    M['M4_no_exclusive_create_full_collision'] = dict(o, caught=not (o['setup_errors'] == 1 and o['first_files_unchanged']))
    ok = all(v['caught'] for v in M.values())
    return {'mutants': M, 'ok': bool(ok)}


def main(argv):
    if argv != ['all']:
        print(__doc__)
        return 2
    bn = set_below_normal()
    OUTD.mkdir(parents=True, exist_ok=True)
    recorder, bad = build_syn()
    summary = {'below_normal': bn, 'parts': {}, 'when': time.strftime('%Y-%m-%dT%H:%M:%S'),
               'tool_sha256': sha_file(__file__), 'hook_sha256': sha_file(NEW_HOOK / 'sitecustomize.py'),
               'driver_sha256': sha_file(KV2 / 'vb_chain.py'), 'recalc_sha256': sha_file(KV2 / 'vb_recalc.py')}
    st = part_static()
    summary['parts']['static'] = {'ok': st['ok'], 'sha256': write_json(OUTD / 'dry_a33_static.json', st)}
    print('DRY33 static ok=%s' % st['ok'], flush=True)
    hk = part_hook(recorder, bad)
    summary['parts']['hook'] = {'ok': hk['ok'], 'sha256': write_json(OUTD / 'dry_a33_hook.json', hk)}
    print('DRY33 hook ok=%s' % hk['ok'], flush=True)
    pr = part_pidreuse(recorder, hk['base_results'])
    summary['parts']['pidreuse'] = {'ok': pr['ok'], 'sha256': write_json(OUTD / 'dry_a33_pidreuse.json', pr)}
    print('DRY33 pidreuse ok=%s %s' % (pr['ok'], {k: v['ok'] for k, v in pr['cases'].items()}), flush=True)
    pa = part_paths()
    summary['parts']['paths'] = {'ok': pa['ok'], 'sha256': write_json(OUTD / 'dry_a33_paths.json', pa)}
    print('DRY33 paths ok=%s' % pa['ok'], flush=True)
    mu = part_mutants(recorder, hk['base_results'])
    summary['parts']['mutants'] = {'ok': mu['ok'], 'sha256': write_json(OUTD / 'dry_a33_mutants.json', mu)}
    print('DRY33 mutants ok=%s %s' % (mu['ok'], {k: v['caught'] for k, v in mu['mutants'].items()}), flush=True)
    summary['all_ok'] = all(v['ok'] for v in summary['parts'].values()) and bn
    h = write_json(OUTD / 'dry_a33_summary.json', summary)
    print('DRY33 all_ok=%s summary=%s' % (summary['all_ok'], h), flush=True)
    return 0 if summary['all_ok'] else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
