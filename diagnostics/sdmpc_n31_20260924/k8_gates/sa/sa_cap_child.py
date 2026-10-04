"""Adapter process for K8-6 SA captures: run the adapter as `python adapter.py ...` until sdmpc.solve builds its
surrogate Query, store the request template (+ the H_long A1 forecast and the SDMPC coordinates), stop.
(k8_gates/cap_child.py base pattern + termcost tc_capture forecast/coord + the FH transplant of sa_fh.py.)

    python -B sa_cap_child.py <out_dir> <capture_spec.json> <adapter.py> <adapter args...>

capture_spec.json (written by sa_capture.py): harness, T, seed, frame_T, arm, tree, tuning{path, sha256}, h_long,
  fh{spec_path, enabled} | null.
Writes <out_dir>/template.pickle, forecast_long.pickle, coord.pickle, capture.json (k8-sa-capture/v1), or
capture_failed.json.  Nothing under the code root is edited; the FH transplant wraps
lane_plant_runtime.observe_state in memory (sa_fh.install).
A failure record carries the child's own classification of its full traceback (error_kind / error_site, sa_errors;
K8 amendment 7 §2); an exception of the harness stage after the template (forecast_long, coord, record writing) is
marked harness_stage_error (a harness failure -> INCOMPLETE, whatever frame raised it)."""
import hashlib
import json
import os
import pickle
import runpy
import sys
import time
import traceback
from pathlib import Path

import sa_errors  # stdlib only; this script's folder is sys.path[0] here

if len(sys.argv) < 4 or sys.argv[1] in ('-h', '--help'):
    print(__doc__)
    raise SystemExit(0 if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help') else 2)
HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[1])
SPEC = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
ADAPTER = sys.argv[3]
ARGS = sys.argv[4:]
OUT.mkdir(parents=True, exist_ok=True)
STARTED = time.perf_counter()
REC = {'schema': 'k8-sa-capture/v1', **{k: SPEC.get(k) for k in ('harness', 'T', 'seed', 'frame_T', 'arm', 'tree',
                                                                  'tuning', 'h_long')}}
STASH = {'bound': None}
META_KEYS = ('stopline_approach_install_check', 'stopline_approach_initial', 'lane_ramp_head_service_normalisation',
             'lane_plant_install_check')
PROBE_LINKS = ('32', '10778', '129', '10777', '127', '10695', '10118', '10368', '10491', '10481')
W_MEMBERS = ('SC1001_W_to_E_SC1002', 'SC1001_W_to_S_SC1003', 'SC1001_W_to_N_SC2002')
TRANSPLANT = None


class Captured(BaseException):
    pass


def _f(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    v = getattr(x, 'value', None)
    return float(v) if v is not None else float('nan')


def write_record(name, rec):
    """capture.json / capture_failed.json via a temporary file + os.replace (review r4 N-r4-4): a process stopped
    while writing leaves no truncated record (no record = killed, never an unreadable JSON)."""
    tmp = OUT / (name + '.tmp')
    tmp.write_text(json.dumps(rec, indent=1, default=repr), encoding='utf-8')
    os.replace(tmp, OUT / name)


def frame_of(name, need):
    frame = sys._getframe(1)
    while frame is not None:
        if frame.f_code.co_name == name and all(k in frame.f_locals for k in need):
            return frame
        frame = frame.f_back
    return None


def capture_probes(state, cfg, bound, shortfall_kept=None, rehome_kept=None):
    """Plain floats from the captured state (H-2/H-2b, G-EB-9, G-EB-14, G-EB-1 numeric fields come from the
    template itself).  `shortfall_kept` = the SA metadata posthead_receiver_shortfall_veh (amendment 7 §1 term, both
    branches since amendment 8 §1); `rehome_kept` = its posthead_rehome_shortfall_veh (the (d) share, which SA books
    on its connector as the member queue, so M_other is read net of it)."""
    net = cfg.network
    pd = state.local_observation_summary.get('projection_diagnostics') or {}
    prov = pd.get('physical_stock_assignment_by_link') or {}
    split = pd.get('storage_seed_split_by_link')
    cap = net.urban_link_storage_veh
    out = {'provenance': {k: {kk: _f(vv) for kk, vv in (prov.get(k) or {}).items()} for k in PROBE_LINKS},
           'seed_split': ({k: split.get(k) for k in PROBE_LINKS + ('unattributed',) if k in split}
                          if isinstance(split, dict) else None),
           'seed_split_present': isinstance(split, dict),
           'occupancy': {k: _f(cap[k]) - _f(state.urban_link_storage.get(k, cap[k]))
                         for k in ('in_SC1001_W', 'SC1001_to_SC2002', 'SC1001_to_SC1002', 'SC1001_to_SC1003',
                                   'OR_D_W_storage', 'OR_D_E_storage', 'SC1001_W_out') if k in cap},
           'capacity': {k: _f(cap[k]) for k in ('in_SC1001_W', 'OR_D_W_storage', 'OR_D_E_storage') if k in cap},
           'arrival': {k: {str(t): _f(v) for t, v in (state.urban_arrival_buffer.get(k) or {}).items()}
                       for k in ('in_SC1001_W', 'SC1001_to_SC2002')},
           'release': {k: {str(t): _f(v) for t, v in (state.urban_storage_release_buffer.get(k) or {}).items()}
                       for k in ('in_SC1001_W', 'SC1001_to_SC2002')},
           'w_queue': {m: _f(state.urban_movement_queue.get(m, 0.0)) for m in W_MEMBERS},
           'freeway_density': {r: [_f(v) for v in vals] for r, vals in state.freeway_density.items()},
           'freeway_speed': {r: [(_f(v) if v is not None else None) for v in vals]
                             for r, vals in state.freeway_speed.items()}}
    lor = getattr(state, 'lane_offramp_runtime', None)
    if lor is not None:
        out['ports'] = {off: {'stock': _f(lor.ports[off].stock), 'capacity': _f(lor.ports[off].capacity),
                              'approach': lor.descriptions[off].get('approach')}
                        for off in ('10491', '10481') if off in lor.ports}
    lfr = getattr(state, 'lane_freeway_runtime', None)
    if lfr is not None:
        for name in ('off_splits', 'off_split_ratio'):
            v = getattr(lfr, name, None)
            if isinstance(v, dict):
                out['lane_freeway_off_splits'] = {str(k): (_f(x) if not isinstance(x, dict) else x) for k, x in v.items()}
                break
    sa = getattr(state, 'stopline_approach_state', None)
    if isinstance(sa, dict):
        out['sa'] = {'stock': {str(l): _f(v) for l, v in sa['stock'].items()},
                     'packets': {str(l): len(v) for l, v in sa['lanes'].items()},
                     'tags_total': sum(_f(v) for row in sa['tags'].values() for v in row.values()),
                     'carry_total': sum(_f(v) for row in sa['carry'].values() for v in row.values())}
    if bound is not None:
        import sa_identity
        out['records'] = sa_identity.identity_terms(bound, prov, getattr(net, 'stopline_approach', None),
                                                    shortfall_kept=shortfall_kept, rehome_kept=rehome_kept)
    return out


def hooked(self, template, check_budget, emit, runner=None):
    try:
        _hooked(template)
    except Exception:
        REC['harness_stage_error'] = traceback.format_exc()[-1500:]    # amendment 7 §2: a harness failure
        raise
    REC['captured'] = True
    raise Captured()


def _hooked(template):
    main = frame_of('main', ('state_json', 'forecast', 'cfg'))
    solve = frame_of('solve', ('coord',))
    tbytes = pickle.dumps(template, protocol=5)
    (OUT / 'template.pickle').write_bytes(tbytes)
    follower, state, reference, forecast3 = template['owned']
    meta = dict(template_sha256=hashlib.sha256(tbytes).hexdigest(), sim_sec=float(state.time_sec),
                horizon=template['horizon'], axes=len(template['axes']), costs_order=list(template['costs_order']),
                forecast_len=len(forecast3),            # sa_jobs needs forecast_long.pickle for H > this (B-r4-1)
                python_hash_seed=os.environ.get('PYTHONHASHSEED'))
    if main is not None:
        f = main.f_locals
        adapter = sys.modules['__main__']
        H = int(SPEC.get('h_long') or len(forecast3))
        DemandStep = type(forecast3[0])
        longer = adapter.demand_from_state(f['state_json'], f['cfg'], DemandStep, H, f.get('calibration'),
                                           f.get('detector_mapping'))
        (OUT / 'forecast_long.pickle').write_bytes(pickle.dumps(list(longer), protocol=5))
        meta['forecast_long_len'] = len(longer)
        meta['forecast_long_prefix_equal'] = (pickle.dumps(list(longer[:len(forecast3)]), protocol=5)
                                              == pickle.dumps(list(forecast3), protocol=5))
        md = f.get('runtime_patch_metadata') or {}
        REC['metadata'] = {k: md.get(k) for k in META_KEYS if k in md}
    if solve is not None:
        sv = solve.f_locals
        try:
            (OUT / 'coord.pickle').write_bytes(pickle.dumps(dict(coord=sv['coord']), protocol=5))
        except Exception as exc:
            meta['coord_error'] = repr(exc)[:300]
    initial = ((REC.get('metadata') or {}).get('stopline_approach_initial') or {})
    try:
        REC['probes'] = capture_probes(state, follower.cfg, STASH['bound'],
                                       shortfall_kept=initial.get('posthead_receiver_shortfall_veh'),
                                       rehome_kept=initial.get('posthead_rehome_shortfall_veh'))
    except Exception:
        REC['probes_error'] = traceback.format_exc()[-1500:]
    if TRANSPLANT is not None:
        REC['transplant'] = TRANSPLANT.record
    meta['capture_wall_sec'] = time.perf_counter() - STARTED
    REC.update(meta)
    REC['ok'] = True
    write_record('capture.json', REC)


sys.path[0] = str(Path(ADAPTER).resolve().parent)
ROOT = Path(ADAPTER).resolve().parents[2]
sys.path.insert(1, str(ROOT))
sys.path.insert(2, str(HERE))
import importlib.abc  # noqa: E402


class Post(importlib.abc.MetaPathFinder):
    def __init__(self, callbacks):
        self.callbacks = callbacks

    def find_spec(self, fullname, path=None, target=None):
        if fullname not in self.callbacks:
            return None
        idx = sys.meta_path.index(self)
        for f in sys.meta_path[idx + 1:]:
            fs = getattr(f, 'find_spec', None)
            spec = fs(fullname, path, target) if fs else None
            if spec is not None:
                break
        else:
            return None
        orig = spec.loader.exec_module
        cb = self.callbacks[fullname]

        def exec_module(module):
            orig(module)
            cb(module)
        spec.loader.exec_module = exec_module
        return spec


def patch_surrogate(module):
    module.Query.__init__ = hooked


def patch_lpr(module):
    global TRANSPLANT
    fh = SPEC.get('fh')
    if fh:
        import sa_fh
        spec = json.loads(Path(fh['spec_path']).read_text(encoding='utf-8'))
        TRANSPLANT = sa_fh.Transplant(spec, enabled=bool(fh.get('enabled', True)))
        sa_fh.install(module, TRANSPLANT)
    original = module.bind_current_routes

    def bind_current_routes(raw, observation):
        out = original(raw, observation)
        STASH['bound'] = out
        return out
    module.bind_current_routes = bind_current_routes


sys.meta_path.insert(0, Post({'evaluation.controllers.sdmpc_tangent_surrogate': patch_surrogate,
                              'evaluation.controllers.lane_plant_runtime': patch_lpr}))
sys.argv = [ADAPTER] + ARGS
code = 3
try:
    runpy.run_path(ADAPTER, run_name='__main__')
    print('SA_CAPTURE_FAILED adapter returned', flush=True)
    code = 2
except Captured:
    print('SA_CAPTURE_OK', flush=True)
    code = 0
except SystemExit as e:
    if REC.get('captured'):
        print('SA_CAPTURE_OK', flush=True)
        code = 0
    else:
        print('SA_CAPTURE_FAILED exit', e.code, flush=True)
        code = 3
except BaseException:
    _tb = traceback.format_exc()
    REC['error'] = _tb[-3000:]
    REC['error_kind'], REC['error_site'] = sa_errors.classify(_tb)     # the full traceback (amendment 7 §2)
    print('SA_CAPTURE_FAILED exception', flush=True)
    code = 4
if 'captured' not in REC:
    REC['ok'] = False
    if TRANSPLANT is not None:
        REC['transplant'] = TRANSPLANT.record
    write_record('capture_failed.json', REC)
sys.stdout.flush()
sys.stderr.flush()
os._exit(code)
