"""Data-free checks of the K8_PREDECLARATION_AMENDMENT_32 tools (Declare A32).  Diagnostics only, never committed.
SYNTHETIC inputs only, with three read-only exceptions that carry no V-B data: the committed recorder bytes
(GWT8 k92_record.py, sha 1d1dfa36..., copied into the synthetic tree), the committed K9-2-5 comparator k92_compare.py
(GWT8, sha 3e2da987..., imported read-only to judge synthetic folders) and five recorded runner receipts of the J1
runs RR (bytes and their CSV sizes only -- the receipt-format check).  No decision replay, no adapter, no VISSIM.

    python -B dry_a32.py all      -> dry/decl/dry_a32_<part>.json for part in static, hook, select, receipt,
                                     reportonly, zi, closed, mutants; prints one line per part
Every child process: python -B, PYTHONHASHSEED=0, BELOW_NORMAL, env without RW_ / K8_ / K8G_ / K92A_ / K92VB_ unless
the case sets K92VB_*.  Synthetic trees: dry/syn (made fresh)."""
import ast
import copy
import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
AD32 = Path(__file__).resolve().parent
DRY = AD32 / 'dry'
OUTD = DRY / 'decl'
SYN = DRY / 'syn'
PY = r'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
BELOW_NORMAL = 0x00004000
GWT8_SA = Path(r'D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/k8_gates/sa')
RECORDER_SHA = '1d1dfa36efbfa68e6ccc19cbeeb53f241437b1c5145e06fb843a9564661d4f90'
COMPARE_SHA = '3e2da987ff9e7b54ba2f51ad1b73bfdaf55f868bd6dedbf7937cf1f22fa4caba'
RR = Path(r'D:/VISSIM_runs/20261004_sdmpc31_k8')
RECEIPTS = [  # (run, previous T, expected receipt sha256 -- VB_PRECHECK_STOP r2 section 2.3-6 / vvb_a_01.json)
    ('sdmpc31_v3c3_k8j1r_s31', 3000, '602f2a857c13546ea9f512297b3ce79906e4ff0b5147f50a2588f7c7507955a8'),
    ('sdmpc31_v3c3_k8j1_s43', 3000, '61983196eb59ef0ee11de2703422ece699e4300f8b4ce2b7dd1e9ef0fc1fe917'),
    ('sdmpc31_v3c3_k8j1_s41', 3000, 'f72c349e10bf098406ab508106311fe284772bb2522abc4302440a62d26772da'),
    ('sdmpc31_v3c3_k8j1_s41', 900, '574dfdc1d5c962596c7605085223b3049b67a38fef05e253ba7e00ec7d152044'),
    ('sdmpc31_v3c3_k8j1_s41', 2850, None)]
STDLIB_OK = None


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


def load_module(path, name):
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
           if not k.upper().startswith(('RW_', 'K8_', 'K8G_', 'K92A_', 'K92VB_'))}
    env.update(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
    env.pop('PYTHONPATH', None)
    env.update(extra or {})
    return env


# ================================================================================================ synthetic program
PKG_SDMPC = '''"""Synthetic sdmpc module (dry_a32): omega_costs reads point.cost_rows only, like the real one reads its rows."""
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
CHILD = r'''"""Synthetic decision program (dry_a32).  argv: mode out_json."""
import json
import os
import sys
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
    json.dump({'mode': MODE, 'results': results, 'new_modules': new,
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
    for name in ('vissim_stackelberg_adapter.py', 'other_child.py'):
        d = SYN / ('prog_' + name.split('.')[0])
        d.mkdir(parents=True)
        (d / name).write_text(CHILD, encoding='utf-8')
    rec_src = GWT8_SA / 'k92_record.py'
    tree = SYN / 'tree' / 'diagnostics' / 'sdmpc_n31_20260924' / 'k8_gates' / 'sa'
    tree.mkdir(parents=True)
    shutil.copy2(rec_src, tree / 'k92_record.py')
    if sha_file(tree / 'k92_record.py') != RECORDER_SHA:
        raise SystemExit('recorder copy sha differs')
    bad = SYN / 'tree_bad' / 'k92_record.py'
    bad.parent.mkdir(parents=True)
    bad.write_bytes((tree / 'k92_record.py').read_bytes() + b'\n# changed\n')
    return tree / 'k92_record.py', bad


def run_child(case, mode, *, hook_dir=None, hook_path=True, recorder=None, rec_sha=RECORDER_SHA, prog='adapter',
              drop=None, hook_code=None):
    out = SYN / 'out' / (case + '.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    pp = [str(hook_code or (AD32 / 'vbhook'))] if hook_path else []
    pp.append(str(SYN / 'pkg'))
    extra = {'PYTHONPATH': os.pathsep.join(pp)}
    if hook_dir is not None:
        extra.update(K92VB_HOOK_DIR=str(hook_dir), K92VB_RECORDER=str(recorder), K92VB_RECORDER_SHA256=rec_sha,
                     K92VB_T='3000', K92VB_SEED='41', K92VB_LABEL='dry/%s' % case)
        for k in drop or ():
            extra.pop(k, None)
    script = SYN / ('prog_vissim_stackelberg_adapter' if prog == 'adapter' else 'prog_other_child') / (
        'vissim_stackelberg_adapter.py' if prog == 'adapter' else 'other_child.py')
    t0 = time.perf_counter()
    p = subprocess.run([PY, '-B', str(script), mode, str(out)], cwd=str(script.parent), env=clean_env(extra),
                       capture_output=True, text=True, creationflags=BELOW_NORMAL, timeout=600)
    res = {'rc': p.returncode, 'sec': round(time.perf_counter() - t0, 2), 'stderr_tail': p.stderr[-800:]}
    res['out'] = json.loads(out.read_text(encoding='utf-8')) if out.is_file() else None
    return res


def hook_listing(hdir):
    hdir = Path(hdir)
    if not hdir.exists():
        return {'exists': False}
    cands = sorted(p.name for p in hdir.glob('c_*'))
    return {'exists': True, 'loaded': sorted(p.name for p in hdir.glob('loaded_*.json')), 'candidates': cands,
            'errors': sorted(p.name for p in hdir.glob('hook_error_*.txt')),
            'setup_errors': sorted(p.name for p in hdir.glob('hook_setup_error_*.txt')),
            'files_per_candidate': {c: sorted(x.name for x in (hdir / c).iterdir()) for c in cands}}


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


# ================================================================================================ parts
def part_static():
    res = {}
    allowed = {'os', 'sys', 'hashlib', 'json', 'threading', 'time', 'traceback', 'types', 'argparse', 'math',
               'shutil', 'pathlib', 'collections'}
    for rel in ('vbhook/sitecustomize.py', 'vb_select.py', 'vb_lib32.py', 'make_closed32.py'):
        tree = ast.parse((AD32 / rel).read_text(encoding='utf-8'))
        mods = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                mods |= {a.name.split('.')[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                mods.add((n.module or '').split('.')[0])
        res[rel] = {'imports': sorted(mods), 'stdlib_only': mods <= allowed,
                    'no_evaluation_src': not (mods & {'evaluation', 'src', 'k92_record', 'k92_compare'})}
    res['vbhook_folder_files'] = sorted(p.name for p in (AD32 / 'vbhook').iterdir())
    res['vbhook_only_sitecustomize'] = res['vbhook_folder_files'] == ['sitecustomize.py']
    hook_text = (AD32 / 'vbhook' / 'sitecustomize.py').read_text(encoding='utf-8')
    res['hook_target'] = "_TARGET = ('omega_costs', 'sdmpc.py')" in hook_text
    res['hook_env_gate'] = "_OUT = os.environ.get('K92VB_HOOK_DIR')" in hook_text and '\nif _OUT:\n' in hook_text
    res['hook_calls'] = all(s in hook_text for s in ('mod.network_facts(cfg)', 'mod.collect(resp, T, dt)',
                                                    'mod.write(folder, job, T, dt, _H, None)'))
    res['ok'] = (all(v['stdlib_only'] and v['no_evaluation_src'] for k, v in res.items() if k.endswith('.py'))
                 and res['vbhook_only_sitecustomize'] and res['hook_target'] and res['hook_env_gate']
                 and res['hook_calls'])
    return res


def part_hook(recorder, bad):
    cases = {}
    H = SYN / 'hooks'
    base = run_child('base_nohookpath', 'normal', hook_path=False)
    off = run_child('off_envabsent', 'normal')
    on = run_child('on_normal', 'normal', hook_dir=H / 'on_normal', recorder=recorder)
    cases['base'] = {'rc': base['rc'], 'results': base['out']['results'] if base['out'] else None}
    cases['off'] = {'rc': off['rc'], 'same_results_as_base': off['out'] and off['out']['results'] == base['out']['results'],
                    'no_hook_files': not (H / 'off_envabsent').exists(),
                    'same_modules_as_base': off['out'] and off['out']['new_modules'] == base['out']['new_modules']}
    lst = hook_listing(H / 'on_normal')
    extra_mods = sorted(set(on['out']['new_modules']) - set(base['out']['new_modules'])) if on['out'] else None
    c = {'rc': on['rc'], 'same_results_as_base': on['out'] and on['out']['results'] == base['out']['results'],
         'listing': lst, 'extra_modules_vs_base': extra_mods,
         'no_evaluation_or_src_added': on['out'] and on['out']['evaluation_modules'] == base['out']['evaluation_modules'],
         'k92_record_not_in_sys_modules': on['out'] and on['out']['k92_record_in_sys_modules'] is False}
    c['three_candidates'] = len(lst.get('candidates', [])) == 3 and not lst.get('errors') and not lst.get('setup_errors')
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
                           and m['action_from'] == [1, 'predict'] for m in metas)
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
    c['ok'] = bool(on['rc'] == 0 and c['same_results_as_base'] and c['three_candidates'] and c['files_ok']
                   and c['no_evaluation_or_src_added'] and c['k92_record_not_in_sys_modules'] and c['meta_fields']
                   and c['records_ok'] and c['ad_flags'] == [False, False, True]
                   and c['signatures_p3'] == [23.588, 26.0, 23.588])
    cases['on_normal'] = c
    # sha mismatch -> setup error, inert
    sm = run_child('on_badsha', 'normal', hook_dir=H / 'on_badsha', recorder=bad)
    lst = hook_listing(H / 'on_badsha')
    lj = [json.loads((H / 'on_badsha' / x).read_text(encoding='utf-8')) for x in lst.get('loaded', [])]
    cases['badsha'] = {'rc': sm['rc'], 'same_results_as_base': sm['out']['results'] == base['out']['results'],
                       'listing': lst, 'recorder_ok': [x.get('recorder_ok') for x in lj]}
    cases['badsha']['ok'] = (sm['rc'] == 0 and cases['badsha']['same_results_as_base'] and not lst['candidates']
                             and len(lst['setup_errors']) == 1 and cases['badsha']['recorder_ok'] == [False])
    # missing K92VB_T -> setup error, inert
    mt = run_child('on_noT', 'normal', hook_dir=H / 'on_noT', recorder=recorder, drop=('K92VB_T',))
    lst = hook_listing(H / 'on_noT')
    cases['missingT'] = {'rc': mt['rc'], 'same_results_as_base': mt['out']['results'] == base['out']['results'],
                         'listing': lst}
    cases['missingT']['ok'] = (mt['rc'] == 0 and cases['missingT']['same_results_as_base'] and not lst['candidates']
                               and len(lst['setup_errors']) == 1)
    # exception inside the hook (response property raises) -> hook_error file, program unchanged
    rb = run_child('base_raising', 'raising', hook_path=False)
    ra = run_child('on_raising', 'raising', hook_dir=H / 'on_raising', recorder=recorder)
    lst = hook_listing(H / 'on_raising')
    cases['raising'] = {'rc': ra['rc'], 'same_results_as_base': ra['out'] and rb['out'] and
                        ra['out']['results'] == rb['out']['results'], 'listing': lst}
    cases['raising']['ok'] = (ra['rc'] == 0 and rb['rc'] == 0 and cases['raising']['same_results_as_base']
                              and len(lst['errors']) == 1 and len(lst['candidates']) == 1
                              and lst['files_per_candidate'][lst['candidates'][0]] == [])
    # threads -> distinct folders, no error
    tb = run_child('base_threads', 'threads', hook_path=False)
    ta = run_child('on_threads', 'threads', hook_dir=H / 'on_threads', recorder=recorder)
    lst = hook_listing(H / 'on_threads')
    cases['threads'] = {'rc': ta['rc'], 'same_results_as_base': ta['out']['results'] == tb['out']['results'],
                        'listing_n': len(lst['candidates']), 'errors': lst['errors']}
    cases['threads']['ok'] = (ta['rc'] == 0 and cases['threads']['same_results_as_base'] and len(lst['candidates']) == 4
                              and not lst['errors'] and len(set(lst['candidates'])) == 4)
    # decoys: omega_costs in another file, another function in sdmpc.py -> no candidate
    da = run_child('on_decoy', 'decoy', hook_dir=H / 'on_decoy', recorder=recorder)
    lst = hook_listing(H / 'on_decoy')
    cases['decoy'] = {'rc': da['rc'], 'listing': lst}
    cases['decoy']['ok'] = da['rc'] == 0 and lst['candidates'] == [] and not lst['errors'] and len(lst['loaded']) == 1
    # other program name (no adapter) -> loaded argv0 other_child.py (for select no_hook)
    oa = run_child('on_otherprog', 'normal', hook_dir=H / 'on_otherprog', recorder=recorder, prog='other')
    lst = hook_listing(H / 'on_otherprog')
    cases['otherprog'] = {'rc': oa['rc'], 'listing_n': len(lst['candidates'])}
    cases['otherprog']['ok'] = oa['rc'] == 0 and len(lst['candidates']) == 3
    ok = all(v.get('ok', True) for k, v in cases.items() if isinstance(v, dict) and k != 'base') and base['rc'] == 0 \
        and cases['off']['same_results_as_base'] and cases['off']['no_hook_files'] and cases['off']['same_modules_as_base']
    return {'cases': cases, 'ok': bool(ok)}


def out_action(path, g3, *, fut=(23.5, 24.5), off=21.309, sdmpc_active=True):
    doc = {'green_times': {'SC109_p2': 56.45, 'SC109_p3': g3, 'SC109_p4': 60.962},
           'offsets': {'SC109': off, 'SC1': 4.0},
           'diagnostics': {'sdmpc_prediction_sequence': {'future': [{'green_times': {'SC109_p2': 56.0, 'SC109_p3': f,
                                                                                     'SC109_p4': 60.0}} for f in fut]}},
           'metadata': {'sdmpc_active': sdmpc_active, 'k92_w': {'x': 1}}}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(doc, indent=1), encoding='utf-8')
    return path


def part_select(vs):
    H = SYN / 'hooks'
    A = SYN / 'sel'
    if A.exists():
        shutil.rmtree(A)
    a_json = out_action(A / 'actA' / 'action_003000.json', 23.588)
    c = {}
    r = vs.select(H / 'on_normal', a_json, 3000, A / 'S1')
    c['S1_selected_nonAD'] = {'status': r['status'], 'n_match': r['n_match'], 'chosen_is_ad': (r['chosen'] or {}).get('is_ad'),
                              'copied': (A / 'S1' / 'k92_record.json').is_file() and (A / 'S1' / 'k92_series.npz').is_file(),
                              'keyed': r['keyed'], 'sdmpc_active': r['sdmpc_active']}
    c['S1_selected_nonAD']['ok'] = (r['status'] == 'selected' and r['n_match'] == 2 and r['chosen']['is_ad'] is False
                                    and c['S1_selected_nonAD']['copied'] and r['keyed'] == {'k92_w': True, 'k92_hb': False})
    b_json = out_action(A / 'actB' / 'action_003000.json', 26.0)
    r = vs.select(H / 'on_normal', b_json, 3000, A / 'S1b')
    c['S1b_single_match'] = {'status': r['status'], 'n_match': r['n_match']}
    c['S1b_single_match']['ok'] = r['status'] == 'selected' and r['n_match'] == 1
    x_json = out_action(A / 'actX' / 'action_003000.json', 30.0)
    r = vs.select(H / 'on_normal', x_json, 3000, A / 'S2')
    c['S2_no_match'] = {'status': r['status'], 'ok': r['status'] == 'no_match' and not (A / 'S2' / 'k92_record.json').exists()}
    f_json = out_action(A / 'actF' / 'action_003000.json', 23.588, fut=(23.5, 99.0))
    r = vs.select(H / 'on_normal', f_json, 3000, A / 'S2f')
    c['S2f_future_differs'] = {'status': r['status'], 'ok': r['status'] == 'no_match'}
    cf = SYN / 'hooks_conflict'
    if cf.exists():
        shutil.rmtree(cf)
    shutil.copytree(H / 'on_normal', cf)
    ad = [p for p in sorted(cf.glob('c_*')) if json.loads((p / 'cand.json').read_text(encoding='utf-8'))['is_ad']][0]
    rec = json.loads((ad / 'k92_record.json').read_text(encoding='utf-8'))
    rec['horizon']['outw_veh_h_450'] += 1.0
    (ad / 'k92_record.json').write_text(json.dumps(rec, indent=1), encoding='utf-8')
    r = vs.select(cf, a_json, 3000, A / 'S3')
    c['S3_conflict'] = {'status': r['status'], 'ok': r['status'] == 'match_conflict' and not (A / 'S3' / 'k92_record.json').exists()}
    nc = SYN / 'hooks_nocand'
    if nc.exists():
        shutil.rmtree(nc)
    nc.mkdir()
    shutil.copy2(sorted((H / 'on_normal').glob('loaded_*.json'))[0], nc)
    r = vs.select(nc, a_json, 3000, A / 'S4')
    c['S4_no_candidate'] = {'status': r['status'], 'ok': r['status'] == 'no_candidate'}
    r = vs.select(H / 'on_raising', a_json, 3000, A / 'S5')
    c['S5_hook_error'] = {'status': r['status'], 'ok': r['status'] == 'hook_error'}
    r = vs.select(H / 'on_otherprog', a_json, 3000, A / 'S6')
    c['S6_no_hook'] = {'status': r['status'], 'ok': r['status'] == 'no_hook'}
    r = vs.select(H / 'on_normal', a_json, 3150, A / 'S7')
    c['S7_T_mismatch'] = {'status': r['status'], 'ok': r['status'] == 'no_match'}
    r = vs.select(H / 'on_badsha', a_json, 3000, A / 'S9')
    c['S9_badsha'] = {'status': r['status'], 'ok': r['status'] == 'hook_error'}
    try:
        vs.select(H / 'on_normal', a_json, 3000, A / 'S1')
        c['S8_never_reused'] = {'ok': False}
    except SystemExit:
        c['S8_never_reused'] = {'ok': True}
    p = subprocess.run([PY, '-B', str(AD32 / 'vb_select.py'), 'select', '--hook-dir', str(H / 'on_normal'),
                        '--action-json', str(a_json), '--T', '3000', '--dest', str(A / 'S1cli')],
                       capture_output=True, text=True, env=clean_env(), creationflags=BELOW_NORMAL, timeout=300)
    j1 = json.loads((A / 'S1' / 'k92_select.json').read_text(encoding='utf-8'))
    j2 = json.loads((A / 'S1cli' / 'k92_select.json').read_text(encoding='utf-8'))
    for j in (j1, j2):
        j.pop('hook_dir', None)
    c['CLI_same_as_function'] = {'rc': p.returncode, 'stdout': p.stdout.strip()[-200:],
                                 'ok': p.returncode == 0 and j1 == j2 and
                                 sha_file(A / 'S1' / 'k92_record.json') == sha_file(A / 'S1cli' / 'k92_record.json')}
    return {'cases': c, 'ok': all(v['ok'] for v in c.values())}


def parse_like_load_prices(ack, csv_path, state_time, interval):
    """sdmpc.py:519-528 (load_prices) read of the receipt, re-typed here (no evaluation import); a read error = False
    (load_prices would raise)."""
    try:
        lines = Path(ack).read_text(encoding='utf-16').splitlines()
    except (UnicodeError, OSError):
        return False
    return (len(lines) == 3 and float(lines[0]) == state_time - interval
            and Path(lines[1]).resolve() == Path(csv_path).resolve() and int(lines[2]) == Path(csv_path).stat().st_size)


def part_receipt(lib):
    rows = []
    for run, prev, want in RECEIPTS:
        dec = RR / run / ('decisions_' + run)
        csv = dec / ('action_%06d.csv' % prev)
        ack = dec / ('action_%06d.json.applied' % prev)
        rec = ack.read_bytes()
        win = str(csv).replace('/', '\\')
        mine = lib.receipt_bytes(prev, win, csv.stat().st_size)
        rows.append({'run': run, 'prev_T': prev, 'record_sha256': hashlib.sha256(rec).hexdigest(),
                     'expected_sha256': want, 'record_is_expected': want is None or hashlib.sha256(rec).hexdigest() == want,
                     'bytes_equal': mine == rec, 'load_prices_parse': parse_like_load_prices(ack, csv, prev + 150, 150)})
    S = SYN / 'receipt'
    if S.exists():
        shutil.rmtree(S)
    S.mkdir(parents=True)
    oj, oc = S / 'action_003150.json', S / 'action_003150.csv'
    oj.write_text('{}', encoding='utf-8')
    oc.write_bytes(b'kind,a\r\nx,1\r\n')
    none = lib.write_receipt(oj, oc)
    Path(str(oj) + '.sdmpc_pending').write_text('Native application required\n', encoding='utf-8')
    w = lib.write_receipt(oj, oc)
    ok_parse = parse_like_load_prices(Path(str(oj) + '.applied'), oc, 3300.0, 150.0)
    try:
        lib.write_receipt(oj, oc)
        again = False
    except SystemExit:
        again = True
    bad_types = []
    for args in ((3000.0, 'x', 1), (True, 'x', 1), (3000, 'x', -1)):
        try:
            lib.receipt_bytes(*args)
            bad_types.append(False)
        except ValueError:
            bad_types.append(True)
    syn = {'no_pending_none': none is None, 'written': w is not None and w['lines'][0] == '3150',
           'parse_ok': ok_parse, 'never_overwrites': again, 'type_guards': bad_types}
    ok = all(r['bytes_equal'] and r['record_is_expected'] and r['load_prices_parse'] for r in rows) and \
        syn['no_pending_none'] and syn['written'] and syn['parse_ok'] and syn['never_overwrites'] and all(bad_types)
    return {'rr_receipts': rows, 'synthetic': syn, 'ok': ok}


def mk_dec(d, T, doc, csv=b'kind,value\r\nsignal,1\r\n', progress=None):
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    s6 = '%06d' % T
    (d / ('action_%s.json' % s6)).write_text(json.dumps(doc, indent=1), encoding='utf-8')
    (d / ('action_%s.csv' % s6)).write_bytes(csv)
    if progress is not None:
        (d / ('action_%s.joint.progress.jsonl' % s6)).write_text(
            json.dumps({'stage': 'sdmpc_completed', 'objective': progress, 'held_objective': progress}) + '\n',
            encoding='utf-8')
    return d


RRP = 'D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1_s41/decisions_sdmpc31_v3c3_k8j1_s41/action_003000'
VBP = 'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/vb/chain/VB-41/OFF/dec/action_003000'


def ss_doc(prefix, rsha, jsha, csha, extra=None):
    doc = {'green_times': {'SC109_p3': 23.588}, 'offsets': {'SC109': 1.0}, 'vsl': {}, 'ramp_metering': {},
           'n_p_star': {}, 'n_uf_star': {}, 'inflow_outflow_allocation': {},
           'prediction_error': {'source_action_json': prefix + '.json', 'value': 1.5},
           'diagnostics': {'physical_ramp_recorded_csv': {'path': prefix + '.csv', 'sha256': csha}},
           'metadata': {'sdmpc_active': True, 'decision_wall_sec': 1.0,
                        'sdmpc_state': {'previous_application': {'source': prefix + '.json.applied',
                                                                 'receipt_sha256': rsha}, 'x': 2.0},
                        'n31_binding': {'vsl_cohort_initialization': {'source': prefix + '.json', 'sha256': jsha}},
                        'joint_leader_selection': {'price_state': {'previous_application': {
                            'source': prefix + '.json.applied', 'receipt_sha256': rsha}}}}}
    for k, v in (extra or {}).items():
        cur = doc
        parts = k.split('/')
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = v
    return doc


def part_reportonly(lib, kc, closed):
    R = SYN / 'ro'
    if R.exists():
        shutil.rmtree(R)
    root = SYN / 'tree'
    h = lambda s: hashlib.sha256(s.encode()).hexdigest()  # noqa: E731
    old = ss_doc(RRP, h('r_old'), h('j_old'), h('csv'))
    cases = {}

    def run(name, new_doc, dtype='SS', csv_new=None, missing=False):
        do = mk_dec(R / name / 'old', 3150, old, progress=1.25)
        dn = mk_dec(R / name / 'new', 3150, new_doc, csv=csv_new or b'kind,value\r\nsignal,1\r\n', progress=1.25)
        if missing:
            (dn / 'action_003150.csv').unlink()
        rep = kc.compare(do, dn, 3150, root, keyed=None, old_root=root)
        ro = lib.reportonly(rep, dtype, closed)
        return rep, ro
    rep, ro = run('R1', ss_doc(VBP, h('r_new'), h('j_new'), h('csv')))
    cases['R1_only_listed'] = {'verdict_ref': rep['verdict'], 'outside_n': ro['outside_n'], 'sentence': ro['sentence'],
                               'in_hard': len(ro['in_list_hard']), 'in_uncl': len(ro['in_list_unclassified'])}
    cases['R1_only_listed']['ok'] = (rep['verdict'] == 'FAIL' and ro['outside_n'] == 0 and len(ro['in_list_hard']) == 3
                                     and len(ro['in_list_unclassified']) == 5)
    rep, ro = run('R2', ss_doc(VBP, h('r_new'), h('j_new'), h('csv'), {'green_times/SC109_p3': 24.0}))
    cases['R2_hard_outside'] = {'outside_n': ro['outside_n'], 'outside_hard': ro['outside_hard'], 'sentence': ro['sentence']}
    cases['R2_hard_outside']['ok'] = ro['outside_n'] == 1 and ro['outside_hard'][0]['path'] == '/green_times/sc109_p3' \
        and ro['sentence'].startswith('**')
    rep, ro = run('R3', ss_doc(VBP, h('r_new'), h('j_new'), h('csv'), {'metadata/foo': 'y'}))
    cases['R3_unclassified_outside'] = {'outside_n': ro['outside_n'], 'outside_unclassified': ro['outside_unclassified']}
    cases['R3_unclassified_outside']['ok'] = ro['outside_n'] == 1 and ro['outside_unclassified'][0]['path'] == '/metadata/foo'
    rep, ro = run('R4', ss_doc(VBP, h('r_new'), h('j_new'), h('csv')), csv_new=b'kind,value\r\nsignal,2\r\n')
    cases['R4_csv_differs'] = {'outside_n': ro['outside_n'], 'h1': ro['h1_csv_same']}
    cases['R4_csv_differs']['ok'] = ro['outside_n'] == 1 and ro['h1_csv_same'] is False
    rep, ro = run('R5', ss_doc(VBP, h('r_new'), h('j_new'), h('csv_changed')))
    cases['R5_csv_sha_leaf'] = {'outside_n': ro['outside_n'], 'outside_unclassified': ro['outside_unclassified']}
    cases['R5_csv_sha_leaf']['ok'] = (ro['outside_n'] == 1 and ro['outside_unclassified'][0]['path']
                                      == '/diagnostics/physical_ramp_recorded_csv/sha256')
    nn_old = {'green_times': {}, 'prediction_error': {'source_action_json': RRP + '.json'},
              'metadata': {'n31_binding': {'vsl_cohort_initialization': {'source': RRP + '.json', 'sha256': h('a')}}}}
    nn_new = copy.deepcopy(nn_old)
    nn_new['prediction_error']['source_action_json'] = VBP + '.json'
    nn_new['metadata']['n31_binding']['vsl_cohort_initialization'] = {'source': VBP + '.json', 'sha256': h('b')}
    do = mk_dec(R / 'R6' / 'old', 300, nn_old)
    dn = mk_dec(R / 'R6' / 'new', 300, nn_new)
    rep = kc.compare(do, dn, 300, root, keyed=None, old_root=root)
    ro = lib.reportonly(rep, 'NN', closed)
    cases['R6_NN'] = {'verdict_ref': rep['verdict'], 'outside_n': ro['outside_n'], 'listed_not_seen': ro['listed_not_seen']}
    cases['R6_NN']['ok'] = ro['outside_n'] == 0 and ro['listed_not_seen'] == [] and rep['verdict'] == 'FAIL'
    ro2 = lib.reportonly(rep, 'SS', closed)
    cases['R6b_NN_judged_as_SS'] = {'outside_n': ro2['outside_n'], 'listed_not_seen_n': len(ro2['listed_not_seen'])}
    cases['R6b_NN_judged_as_SS']['ok'] = ro2['outside_n'] == 0 and len(ro2['listed_not_seen']) == 10
    rep, ro = run('R7', ss_doc(VBP, h('r_new'), h('j_new'), h('csv')), missing=True)
    cases['R7_incomplete'] = {'verdict_ref': rep['verdict'], 'sentence': ro['sentence']}
    cases['R7_incomplete']['ok'] = rep['verdict'] == 'INCOMPLETE' and ro['incomplete'] and ro['outside_n'] is None
    return {'cases': cases, 'ok': all(v['ok'] for v in cases.values())}


def part_zi(lib, kc):
    Z = SYN / 'zi'
    if Z.exists():
        shutil.rmtree(Z)
    root = SYN / 'tree'
    base = {'green_times': {'SC109_p3': 23.588}, 'offsets': {'SC109': 1.0}, 'vsl': {}, 'ramp_metering': {},
            'n_p_star': {}, 'n_uf_star': {}, 'inflow_outflow_allocation': {}, 'prediction': {'wall_sec': 3.0, 'v': 1.0},
            'run_provenance': {'inputs': {'state_json': {'path': 'D:/x/state_003000.json', 'sha256': 'a' * 64}}},
            'metadata': {'decision_wall_sec': 500.0, 'sdmpc_active': True, 'token': 'b' * 64,
                         'joint_leader_selection': {'started_at': '2026-10-22T09:00:00', 'selected_objective': 1.0,
                                                    'budget': {'wall_sec': 2.0, 'final_check_reserve': {'seconds': 5.0}}}}}

    def case(name, mutate, csv2=None, prog2=1.25):
        a = copy.deepcopy(base)
        b = copy.deepcopy(base)
        mutate(b)
        da = mk_dec(Z / name / 'replay_off', 3000, a, progress=1.25)
        db = mk_dec(Z / name / 'replay_on', 3000, b, csv=csv2 or b'kind,value\r\nsignal,1\r\n', progress=prog2)
        return lib.zi_judge(kc, da, db, 3000, root)

    def wall(b):
        b['metadata']['decision_wall_sec'] = 517.3
        b['prediction']['wall_sec'] = 3.4
        b['metadata']['joint_leader_selection']['started_at'] = '2026-10-22T09:11:00'
        b['metadata']['joint_leader_selection']['budget']['wall_sec'] = 2.6
    cases = {}
    r = case('Z1_wall_only', wall)
    cases['Z1_wall_only'] = {'pass': r['pass'], 'wall': r['wallclock_paths'], 'ok': r['pass'] is True and len(r['wallclock_paths']) == 4}
    r = case('Z2_control', lambda b: b['green_times'].__setitem__('SC109_p3', 24.0))
    cases['Z2_control_differs'] = {'pass': r['pass'], 'ok': r['pass'] is False and r['checks']['compare_pass'] is False}
    r = case('Z3_V_path', lambda b: b['run_provenance']['inputs']['state_json'].__setitem__('path', 'D:/y/state_003000.json'))
    cases['Z3_state_path_V'] = {'pass': r['pass'], 'compare_pass': r['checks']['compare_pass'],
                                'ok': r['pass'] is False and r['checks']['compare_pass'] is True}
    r = case('Z4_hex', lambda b: b['metadata'].__setitem__('token', 'c' * 64))
    cases['Z4_hex_F1'] = {'pass': r['pass'], 'compare_pass': r['checks']['compare_pass'],
                          'ok': r['pass'] is False and r['checks']['compare_pass'] is True}
    r = case('Z5_csv', lambda b: None, csv2=b'kind,value\r\nsignal,2\r\n')
    cases['Z5_csv_differs'] = {'pass': r['pass'], 'ok': r['pass'] is False and r['checks']['csv_bytes_same'] is False}
    r = case('Z6_presence', lambda b: b['metadata'].__setitem__('wall_sec', 1.0))
    cases['Z6_presence_wall_name'] = {'pass': r['pass'], 'ok': r['pass'] is False}
    r = case('Z7_progress', lambda b: None, prog2=1.5)
    cases['Z7_progress_differs'] = {'pass': r['pass'], 'ok': r['pass'] is False and r['checks']['progress_last_same'] is False}
    r = case('Z8_same', lambda b: None)
    cases['Z8_identical'] = {'pass': r['pass'], 'ok': r['pass'] is True and r['n_diff_leaves'] == 0}
    r = case('Z9_reserve', lambda b: b['metadata']['joint_leader_selection']['budget']['final_check_reserve'].__setitem__('seconds', 6.0))
    cases['Z9_final_check_reserve_not_wall'] = {'pass': r['pass'], 'ok': r['pass'] is False}
    shutil.rmtree(Z / 'Z8_same' / 'replay_on')
    (Z / 'Z8_same' / 'replay_on').mkdir()
    r = lib.zi_judge(kc, Z / 'Z8_same' / 'replay_off', Z / 'Z8_same' / 'replay_on', 3000, root)
    cases['Z10_missing_output'] = {'pass': r['pass'], 'ok': r['pass'] is False and r['checks']['outputs_present'] is False}
    return {'cases': cases, 'ok': all(v['ok'] for v in cases.values())}


def part_closed(lib):
    target = AD32 / 'vb_closed_leaves.json'
    before = target.read_bytes()
    p = subprocess.run([PY, '-B', str(AD32 / 'make_closed32.py')], capture_output=True, text=True, env=clean_env(),
                       creationflags=BELOW_NORMAL, timeout=300)
    after = target.read_bytes()
    closed = lib.load_closed(target)
    types = {t: (v['n_paths'], v['n_instances'], v['n_hard_paths']) for t, v in closed['types'].items()}
    mapping = {('%s %d' % (d['chain'], d['T'])): d['type'] for d in closed['decisions']}
    first = [lib.decision_type(closed, c, T) for c, T in (('VB-31', 3000), ('VB-43', 3000), ('VB-41', 3000), ('VB-41w', 1))]
    res = {'rc': p.returncode, 'stdout': p.stdout.strip(), 'bytes_same_after_regenerate': before == after,
           'sha256': hashlib.sha256(after).hexdigest(), 'types': types, 'decisions': mapping, 'chain_first_types': first}
    res['ok'] = (p.returncode == 0 and before == after and types == {'NN': (3, 3, 1), 'SN': (9, 12, 1), 'SS': (13, 16, 3)}
                 and len(mapping) == 10 and first == [None, None, None, None]
                 and [mapping['VB-41w %d' % t] for t in (150, 300, 450, 600, 750, 900, 1050)] == ['NN'] * 5 + ['SN', 'SS']
                 and all(mapping['%s 3150' % c] == 'SS' for c in ('VB-31', 'VB-43', 'VB-41')))
    return res


def mutant(src_path, old, new, name):
    text = Path(src_path).read_text(encoding='utf-8')
    if text.count(old) != 1:
        raise SystemExit('mutant anchor not unique: %s' % name)
    d = SYN / 'mutants' / name
    d.mkdir(parents=True, exist_ok=True)
    p = d / Path(src_path).name
    p.write_text(text.replace(old, new), encoding='utf-8')
    return p


def part_mutants(kc, closed, recorder, bad):
    res = {}
    # M1 receipt without BOM
    m = load_module(mutant(AD32 / 'vb_lib32.py', "return b'\\xff\\xfe' + text.encode('utf-16-le')",
                           "return text.encode('utf-16-le')", 'M1'), 'm1lib')
    res['M1_receipt_no_bom'] = not part_receipt(m)['ok']
    # M2 report-only treats every unclassified entry as listed
    m = load_module(mutant(AD32 / 'vb_lib32.py', "(in_soft if u.get('path') in soft_list else out_soft).append(row)",
                           "in_soft.append(row)", 'M2'), 'm2lib')
    res['M2_reportonly_hides_unclassified'] = not part_reportonly(m, kc, closed)['ok']
    # M3 report-only ignores H1
    m = load_module(mutant(AD32 / 'vb_lib32.py', "(0 if out['h1_csv_same'] else 1)", "0", 'M3'), 'm3lib')
    res['M3_reportonly_ignores_csv'] = not part_reportonly(m, kc, closed)['ok']
    # M4 zero-impact rule accepts any compare-PASS difference
    m = load_module(mutant(AD32 / 'vb_lib32.py', "res['checks']['only_wallclock'] = not other",
                           "res['checks']['only_wallclock'] = True", 'M4'), 'm4lib')
    res['M4_zi_accepts_V_and_F1'] = not part_zi(m, kc)['ok']
    # M5 select prefers AD
    m = load_module(mutant(AD32 / 'vb_select.py', "key=lambda c: (c['is_ad'],", "key=lambda c: (not c['is_ad'],", 'M5'),
                    'm5sel')
    res['M5_select_prefers_ad'] = not part_select(m)['ok']
    # M6 select without the time condition
    m = load_module(mutant(AD32 / 'vb_select.py', "c['match'] = c['m1_signature'] and c['m2_time']",
                           "c['match'] = c['m1_signature']", 'M6'), 'm6sel')
    res['M6_select_without_time'] = not part_select(m)['ok']
    # M7 hook without the recorder sha check, M8 hook passing T0 = 0 -- run the hook part with a mutant hook folder
    for name, old, new in (('M7', "recorder_ok=(got == rec_want and len(rec_want) == 64)", "recorder_ok=True"),
                           ('M8', "rec = mod.write(folder, job, T, dt, _H, None)", "rec = mod.write(folder, job, 0.0, dt, _H, None)")):
        mdir = SYN / 'mutants' / name / 'vbhook'
        mdir.mkdir(parents=True, exist_ok=True)
        text = (AD32 / 'vbhook' / 'sitecustomize.py').read_text(encoding='utf-8')
        if text.count(old) != 1:
            raise SystemExit('mutant anchor not unique: %s' % name)
        (mdir / 'sitecustomize.py').write_text(text.replace(old, new), encoding='utf-8')
        hd = SYN / ('hooks_%s' % name)
        if name == 'M7':
            r = run_child('mut_M7', 'normal', hook_dir=hd, recorder=bad, hook_code=mdir)
            lst = hook_listing(hd)
            res['M7_hook_without_sha_check'] = len(lst['candidates']) > 0       # caught: badsha case expects none
        else:
            r = run_child('mut_M8', 'normal', hook_dir=hd, recorder=recorder, hook_code=mdir)
            lst = hook_listing(hd)
            recs = [json.loads((hd / x / 'k92_record.json').read_text(encoding='utf-8')) for x in lst['candidates']]
            e = expected_record(0.0)
            res['M8_hook_wrong_T0'] = not (recs and near((recs[0].get('horizon') or {}).get('m1_chain_T450'),
                                                         e['m1_chain_T450']))
    return {'caught': res, 'ok': all(res.values())}


def main(argv):
    if len(argv) < 2 or argv[1] != 'all':
        print(__doc__)
        return 2
    prio = set_below_normal()
    OUTD.mkdir(parents=True, exist_ok=True)
    kc_path = GWT8_SA / 'k92_compare.py'
    if sha_file(kc_path) != COMPARE_SHA:
        raise SystemExit('k92_compare.py sha differs')
    kc = load_module(kc_path, 'k92_compare_ro')
    recorder, bad = build_syn()
    lib = load_module(AD32 / 'vb_lib32.py', 'vb_lib32_dry')
    vs = load_module(AD32 / 'vb_select.py', 'vb_select_dry')
    closed = lib.load_closed(AD32 / 'vb_closed_leaves.json')
    parts = {}
    parts['static'] = part_static()
    parts['closed'] = part_closed(lib)
    parts['hook'] = part_hook(recorder, bad)
    parts['select'] = part_select(vs)
    parts['receipt'] = part_receipt(lib)
    parts['reportonly'] = part_reportonly(lib, kc, closed)
    parts['zi'] = part_zi(lib, kc)
    parts['mutants'] = part_mutants(kc, closed, recorder, bad)
    summary = {}
    for name, res in parts.items():
        res['tool_sha256'] = sha_file(__file__)
        summary[name] = {'ok': res['ok'], 'sha256': write_json(OUTD / ('dry_a32_%s.json' % name), res)}
        print('DRY_A32 %-10s ok=%s %s' % (name, res['ok'], summary[name]['sha256']), flush=True)
    summary['below_normal'] = prio
    summary['all_ok'] = all(v['ok'] for k, v in summary.items() if isinstance(v, dict))
    print('DRY_A32 all_ok=%s summary=%s' % (summary['all_ok'], write_json(OUTD / 'dry_a32_summary.json', summary)))
    return 0 if summary['all_ok'] else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
