"""P0 configure-only child (amendment C1 section 4, RV-8): run the decision program `python adapter.py ...` until
sdmpc.configure and install_cost_ownership (ADP main) have returned, record the configured structure, stop.
No decision is solved (no load_prices, no harness guard, no prediction).

    python -B c1_p0_child.py <out_dir> <adapter.py> <adapter args...>
Writes <out_dir>/configured.json (+ cfgnet_leaves.json.gz = every cfg.network leaf path -> sha256(repr)[:16]) or
<out_dir>/configure_failed.json (traceback).  Prints nothing of a traffic value.
Recorded: policy token (sdmpc.token of dict(cfg.network.sdmpc_options)), joint options max_leader_candidates,
/metadata c1_port, lane_ramp_head_service_normalisation, physical ramp spec keys and service tables, route contract
input: event kinds, ledger stock keys and their model membership (control_area_objective.resolve_model_membership
per key over detector_stock_supports, the install_cost_ownership supports; an unresolvable key is listed apart),
the observed pre-head storage of every meter buffer (P0-5: getattr(buffer, '_lane_buffers', [buffer]) parts,
snapshot keys, head_position_m, lanes, spacing_m) and the previous executed meter greens."""
import gzip
import hashlib
import json
import math
import os
import runpy
import sys
import time
import traceback
from pathlib import Path

OUT = Path(sys.argv[1])
ADAPTER = sys.argv[2]
ARGS = sys.argv[3:]
OUT.mkdir(parents=True, exist_ok=True)
STARTED = time.perf_counter()
REC = {'schema': 'c1-p0-configured/v1', 'python_hash_seed': os.environ.get('PYTHONHASHSEED')}


class Captured(BaseException):
    pass


def frame_of(name, need):
    frame = sys._getframe(1)
    while frame is not None:
        if frame.f_code.co_name == name and all(k in frame.f_locals for k in need):
            return frame
        frame = frame.f_back
    return None


def leaf_hashes(obj):
    """cfg.network walk: dict keys '/k' ('/' and '~' escaped), list/tuple indices '/[i]', sets sorted by repr,
    ndarray tolist, objects by __dict__ (+ '/@type')."""
    out = {}
    seen = set()

    def h(v):
        return hashlib.sha256(repr(v).encode('utf-8', 'replace')).hexdigest()[:16]

    def esc(k):
        return str(k).replace('~', '~0').replace('/', '~1')

    def walk(v, p, depth):
        if depth > 60:
            out[p] = 'DEPTH'
            return
        t = type(v)
        if v is None or t in (bool, int, str, bytes):
            out[p] = h(v)
            return
        if t is float:
            out[p] = 'nan' if v != v else h(v)
            return
        if getattr(t, '__module__', '') == 'numpy':
            if t.__name__ == 'ndarray':
                walk(v.tolist(), p, depth + 1)
            else:
                try:
                    walk(v.item(), p, depth + 1)
                except Exception:  # noqa: BLE001
                    out[p] = h(v)
            return
        if id(v) in seen and not isinstance(v, (str, bytes)):
            out[p] = 'CYCLE'
            return
        if isinstance(v, dict):
            seen.add(id(v))
            if not v:
                out[p] = '{}'
            for k in v:
                walk(v[k], p + '/' + esc(k), depth + 1)
            seen.discard(id(v))
            return
        if isinstance(v, (list, tuple)):
            seen.add(id(v))
            if not v:
                out[p] = '[]'
            for i, x in enumerate(v):
                walk(x, p + '/[%d]' % i, depth + 1)
            seen.discard(id(v))
            return
        if isinstance(v, (set, frozenset)):
            out[p] = h(sorted(repr(x) for x in v))
            return
        if callable(v) and not hasattr(v, '__dict__'):
            out[p] = 'callable:' + t.__name__
            return
        d = getattr(v, '__dict__', None)
        if isinstance(d, dict) and not isinstance(v, type):
            seen.add(id(v))
            out[p + '/@type'] = t.__name__
            for k in d:
                walk(d[k], p + '/' + esc(k), depth + 1)
            seen.discard(id(v))
            return
        out[p] = 'opaque:' + t.__name__

    walk(obj, '', 0)
    return out


def num(x):
    try:
        x = float(x)
    except Exception:  # noqa: BLE001
        return None
    return x if math.isfinite(x) else repr(x)


def collect(cfg, detector_mapping):
    from evaluation.controllers import sdmpc
    main = frame_of('main', ('cfg', 'tuning', 'state'))
    f = main.f_locals if main is not None else {}
    net = cfg.network
    REC['main_frame_found'] = main is not None
    REC['token'] = sdmpc.token(dict(net.sdmpc_options)) if getattr(net, 'sdmpc_options', None) is not None else None
    REC['sdmpc_options_keys'] = list(net.sdmpc_options) if getattr(net, 'sdmpc_options', None) is not None else None
    jo = f.get('joint_options') or {}
    REC['joint_max_leader_candidates'] = jo.get('max_leader_candidates')
    REC['joint_options_keys'] = sorted(jo)
    tuning = f.get('tuning') or {}
    REC['tuning_has_c1_port'] = 'c1_port' in tuning
    REC['tuning_c1_port'] = tuning.get('c1_port')
    md = f.get('runtime_patch_metadata') or {}
    REC['metadata_c1_port'] = md.get('c1_port')
    REC['metadata_head_normalisation'] = md.get('lane_ramp_head_service_normalisation')
    REC['cfg_c1_port'] = getattr(net, 'c1_port', None)
    spec = getattr(net, 'physical_ramp_branches', None) or {}
    REC['spec_keys'] = sorted(spec)
    REC['spec_allow_zero_green'] = spec.get('allow_zero_green', 'ABSENT')
    REC['spec_storage_release_guard'] = spec.get('storage_release_guard', 'ABSENT')
    REC['service_tables'] = {m: {g: num(s) for g, s in r['service_by_green_veh_h'].items()}
                             for m, r in (spec.get('ramps') or {}).items()}
    REC['ramp_capacity_veh_h'] = {m: num(v) for m, v in (getattr(net, 'ramp_capacity_veh_h', {}) or {}).items()}
    REC['has_ramp_operating_green_floors'] = hasattr(net, 'ramp_operating_green_floors')
    routes = getattr(net, 'control_area_routes', {}) or {}
    REC['route_inputs'] = {k: [v.get('event_kind'), v.get('target_inside'), v.get('status')]
                           for k, v in routes.items() if k.startswith('input:') and isinstance(v, dict)}
    # ledger keys and model membership (per key; the install_cost_ownership supports)
    state = f.get('state')
    ledger = getattr(state, '_control_area_ledger', None)
    keys = sorted(ledger.stocks) if ledger is not None else []
    REC['ledger_keys_n'] = len(keys)
    REC['ledger_inside_veh_total'] = None   # not recorded (a traffic value)
    try:
        from evaluation.controllers.control_area_objective import (detector_stock_supports, resolve_model_membership,
                                                                    physical_membership_from_ledger, MembershipError)
        root = Path(ADAPTER).resolve().parents[2]
        mpath = Path((tuning.get('control_area_objective') or {}).get('membership_path', ''))
        mdoc = json.loads(((root / mpath) if not mpath.is_absolute() else mpath).read_text(encoding='utf-8'))
        physical = physical_membership_from_ledger(mdoc)
        REC['membership_inside_n'] = sum(1 for v in physical.values() if v)
        REC['membership_sha256'] = hashlib.sha256(((root / mpath) if not mpath.is_absolute() else mpath)
                                                  .read_bytes()).hexdigest()
        supports = detector_stock_supports(detector_mapping, off_ramp_storage_links=net.off_ramp_storage_link,
                                           freeway_chains={})
        inside, outside, unresolved = [], [], []
        for k in keys:
            try:
                side = resolve_model_membership(physical, supports, [k])[k]
                (inside if side else outside).append(k)
            except MembershipError:
                unresolved.append(k)
        REC['model_membership'] = {'inside': inside, 'outside': outside, 'unresolved_n': len(unresolved),
                                   'unresolved_sample': unresolved[:20]}
    except Exception:  # noqa: BLE001
        REC['model_membership_error'] = traceback.format_exc()[-1500:]
    # P0-5 storage buffers
    lrr = getattr(state, 'lane_ramp_runtime', None)
    rows = {}
    if lrr is None:
        REC['lane_ramp_runtime'] = None
    else:
        for ramp, buf in sorted(getattr(lrr, 'buffers', {}).items()):
            parts = getattr(buf, '_lane_buffers', [buf])
            lanes = []
            for i, part in enumerate(parts, 1):
                row = {'lane': i, 'has_lane_buffers_attr': hasattr(buf, '_lane_buffers'),
                       'type': type(part).__name__}
                try:
                    s = part.snapshot()
                    row['snapshot_keys_present'] = [k for k in ('upstream_travelling_veh', 'head_ready_veh') if k in s]
                    occ = float(s['upstream_travelling_veh']) + float(s['head_ready_veh'])
                    cap = float(part.head_position_m) * float(part.lanes) / float(part.spacing_m)
                    row.update(head_position_m=num(part.head_position_m), lanes=num(part.lanes),
                               spacing_m=num(part.spacing_m), prehead_veh=num(occ), capacity_veh=num(cap),
                               fill_fraction=num(occ / cap) if cap else None,
                               finite_positive_capacity=math.isfinite(cap) and cap > 0,
                               finite_nonnegative_occupancy=math.isfinite(occ) and occ >= 0)
                except Exception:  # noqa: BLE001
                    row['error'] = traceback.format_exc()[-600:]
                lanes.append(row)
            rows[ramp] = lanes
        REC['lane_ramp_runtime'] = rows
    hist = f.get('historical') or f.get('previous_action')
    prev = {}
    try:
        diag = getattr(hist, 'diagnostics', None) or {}
        prev = {k[len('rw_meter_green_'):]: num(v) for k, v in diag.items() if str(k).startswith('rw_meter_green_')}
    except Exception:  # noqa: BLE001
        pass
    REC['previous_meter_greens_from_main'] = prev
    leaves = leaf_hashes(net)
    REC['cfgnet_leaves_n'] = len(leaves)
    with gzip.open(OUT / 'cfgnet_leaves.json.gz', 'wt', encoding='utf-8') as g:
        json.dump(leaves, g, sort_keys=True)
    REC['wall_sec'] = round(time.perf_counter() - STARTED, 1)


def write(name):
    tmp = OUT / (name + '.tmp')
    tmp.write_text(json.dumps(REC, indent=1, default=repr), encoding='utf-8')
    os.replace(tmp, OUT / name)


sys.path[0] = str(Path(ADAPTER).resolve().parent)
ROOT = Path(ADAPTER).resolve().parents[2]
sys.path.insert(1, str(ROOT))
import importlib.abc  # noqa: E402


class Post(importlib.abc.MetaPathFinder):
    def __init__(self, callbacks):
        self.callbacks = callbacks

    def find_spec(self, fullname, path=None, target=None):
        if fullname not in self.callbacks:
            return None
        idx = sys.meta_path.index(self)
        for finder in sys.meta_path[idx + 1:]:
            fs = getattr(finder, 'find_spec', None)
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


def patch_sdmpc(module):
    original = module.install_cost_ownership

    def install_cost_ownership(cfg, detector_mapping):
        out = original(cfg, detector_mapping)
        try:
            collect(cfg, detector_mapping)
            REC['ok'] = True
            write('configured.json')
        except Exception:  # noqa: BLE001
            REC['collect_error'] = traceback.format_exc()[-3000:]
        REC['captured'] = True
        raise Captured()
    module.install_cost_ownership = install_cost_ownership


sys.meta_path.insert(0, Post({'evaluation.controllers.sdmpc': patch_sdmpc}))
sys.argv = [ADAPTER] + ARGS
code = 3
try:
    runpy.run_path(ADAPTER, run_name='__main__')
    REC['error'] = 'adapter returned without reaching install_cost_ownership'
    code = 2
except Captured:
    code = 0 if REC.get('ok') else 5
except SystemExit as e:
    REC['error'] = 'SystemExit %r' % (e.code,)
    code = 0 if REC.get('captured') and REC.get('ok') else 3
except BaseException:  # noqa: BLE001
    REC['error'] = traceback.format_exc()[-4000:]
    code = 4
if not REC.get('ok'):
    REC['ok'] = False
    write('configure_failed.json')
print('C1_P0_CHILD code=%d' % code, flush=True)
sys.stdout.flush()
sys.stderr.flush()
os._exit(code)
