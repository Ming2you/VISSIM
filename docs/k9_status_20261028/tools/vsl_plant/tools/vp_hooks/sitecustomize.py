# vsl_plant passive FW_E capture hook (PRE_VP.md; diagnostics only, scratch, never committed).
# Loaded only through PYTHONPATH=<VP>/tools/vp_hooks, which vp_job.py sets for the adapter process; the SDMPC
# prediction workers (sdmpc_tangent_worker.py) inherit it.  Active only when env VP_HOOK_DIR is set.
#
# PASSIVE: sys.monitoring (Python 3.12) PY_START / PY_RETURN events on ONE code object,
#   evaluation.controllers.lane_freeway_runtime.LaneFreewayRuntime.advance
# (the one-second freeway step of the V-A plant; FW_E has no lane-group plant in V-A, so the step is the aggregate
# 31-cell METANET of area_freeway_accounting._freeway_substep_events, called from that method).  The handlers only
# READ attributes (frame locals `self`, `state`, the component config) and convert numbers with
# float(getattr(x, 'value', x)); they never call a model method or write to a model object.  The import-order device
# is the one of the K8 SA hook (FRZ_K92 k8_gates/sa/sa_hooks, read only): this finder is moved back in front of the
# worker's source-transform finder when sdmpc_tangent_runtime.install returns.
#
# Per process (role = basename of argv[0]; tag = argv[3][:16] for a worker = its request sha256 prefix):
#   first:  FW_E component parameters the step sees (reach check) and the initial per-cell state at the first step
#           start: stock = rho * L * lanes (veh), speed, density, lanes, origin queue;
#   blocks: per 150 s block b = floor((t - t_first) / 150) and FW_E cell i (after each step):
#           n_dt = sum stock*dt (veh*s), nv_dt = sum stock*v*dt, q_dt = sum q*dt (q = state.freeway_flow, veh/h),
#           dt (s), steps, oq_dt = sum origin_queue*dt (veh*s);
#           (PRE_VP_FIXED X1/X2, added in review r2) per FW_E off-ramp o of the first snapshot's offramp_segment_index:
#           exit_dt[o] = sum offramp_flow_o*dt, exit_blocked_dt[o] = sum offramp_blocked_flow_o*dt (veh/h*s), and
#           speed_proj = sum speed_projection_count, read ONLY from the step's own return value
#           (ttt, off_flows, diagnostics)[2]['FW_E'] (area_freeway_accounting.py:508-519); a missing key is listed
#           in exit_missing (never an error, never a default value in the sums);
#   steps, t_first, t_last, errors.
# Output <VP_HOOK_DIR>/vphook_<tag>_<pid>.json at exit (atexit) and every 30 s.
import os
import sys

_OUT = os.environ.get('VP_HOOK_DIR')
ROAD = 'FW_E'
BLOCK = 150.0


def _setup():
    import atexit
    import importlib.abc
    import json
    import threading
    import time

    mon = sys.monitoring
    ev = mon.events
    tool = None
    for candidate in (3, 4, 5, 2, 1):
        try:
            mon.use_tool_id(candidate, 'vp_passive')
            tool = candidate
            break
        except ValueError:
            continue
    if tool is None:
        raise RuntimeError('no free sys.monitoring tool id')
    lock = threading.RLock()
    role = os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else 'python'
    S = {'first': None, 'blocks': {}, 'steps': 0, 't_first': None, 't_last': None, 'errors': [], 'patched': [],
         'last_dump': time.time(), 'order_fixes': 0, 'lengths': None, 'exits': None, 'exit_missing': []}

    def num(x):
        return float(getattr(x, 'value', x))

    def is_worker():
        return role.endswith('sdmpc_tangent_worker.py') and len(sys.argv) > 3

    def tag():
        return str(sys.argv[3])[:16] if is_worker() else 'parent'

    def dump(final=False):
        try:
            rec = {'schema': 'vp-hook/2', 'pid': os.getpid(), 'role': role, 'tag': tag(),
                   'request_sha256': str(sys.argv[3]) if is_worker() else None, 'final': final, 'tool': tool,
                   'patched': S['patched'], 'order_fixes': S['order_fixes'], 'first': S['first'], 'steps': S['steps'],
                   't_first': S['t_first'], 't_last': S['t_last'], 'blocks': S['blocks'], 'errors': S['errors'][:20],
                   'exits': S['exits'], 'exit_missing': S['exit_missing'][:20]}
            os.makedirs(_OUT, exist_ok=True)
            name = 'vphook_%s_%d.json' % (tag(), os.getpid())
            tmp = os.path.join(_OUT, name + '.tmp')
            with open(tmp, 'w', encoding='utf-8') as h:
                json.dump(rec, h)
            os.replace(tmp, os.path.join(_OUT, name))
        except Exception:
            pass

    def note(exc):
        if len(S['errors']) < 50:
            S['errors'].append(repr(exc)[:300])

    def plain(obj, depth=0):
        if depth > 5:
            return None
        if obj is None or isinstance(obj, (bool, str)):
            return obj
        if isinstance(obj, (int, float)) or hasattr(obj, 'value'):
            try:
                return num(obj)
            except Exception:
                return str(obj)[:80]
        if isinstance(obj, dict):
            return {str(k): plain(v, depth + 1) for k, v in list(obj.items())[:300]}
        if isinstance(obj, (list, tuple, set, frozenset)):
            return [plain(v, depth + 1) for v in list(obj)[:300]]
        return type(obj).__name__

    def lengths_of(net, count):
        if getattr(net, 'freeway_variable_cell_lengths', False):
            prof = (getattr(net, 'freeway_segment_length_profile_km', None) or {}).get(str(ROAD))
            return [num(x) for x in prof]
        return [num(net.freeway_segment_length_km)] * count

    def stock_of(state, lengths):
        rho = state.freeway_density[ROAD]
        lanes = state.freeway_effective_lanes[ROAD]
        return [max(0.0, num(r)) * L * max(num(l), 1e-9) for r, L, l in zip(rho, lengths, lanes)]

    def snapshot(rt, state):
        cfg = rt.configs[ROAD]
        net = cfg.network
        count = len(state.freeway_density[ROAD])
        lengths = lengths_of(net, count)
        S['lengths'] = lengths
        params = {k: plain(getattr(net, k, None)) for k in (
            'freeway_lane_drop_phi', 'metanet_delta_merge', 'capacity_drop_anticipation', 'capacity_drop_discharge_phi',
            'metanet_nu_km2_h', 'metanet_nu_cong_km2_h', 'metanet_tau_h', 'metanet_kappa_veh_km_lane', 'rho_crit',
            'rho_max', 'v_free', 'v_min', 'alpha_vsl', 'metanet_a_m', 'vsl_fd_two_branch', 'terminal_zero_gradient',
            'freeway_capacity_veh_h', 'freeway_lanes', 'freeway_variable_cell_lengths')}
        params['by_direction'] = plain((getattr(net, 'metanet_parameters_by_direction', {}) or {}).get(ROAD))
        params['segment_rows'] = [plain(r) for r in ((getattr(net, 'freeway_segment_params', {}) or {}).get(ROAD) or [])]
        params['segment_lanes'] = plain((getattr(net, 'freeway_segment_lanes', {}) or {}).get(ROAD))
        params['lengths_km'] = lengths
        params['dt_sec'] = num(cfg.simulation.T_f_sec)
        resp = getattr(net, 'freeway_vsl_fd_response', {}) or {}
        params['vsl_fd_response_present'] = ROAD in resp
        params['vsl_fd_response'] = plain(resp.get(ROAD))
        params['vsl_transport'] = plain((getattr(net, 'component_vsl_transport', {}) or {}).get(ROAD))
        params['vsl_initial_commands'] = plain((getattr(net, 'component_vsl_initial_commands', {}) or {}).get(ROAD))
        params['zone_head_of_cell'] = plain((getattr(net, 'freeway_vsl_zone_head_of_cell', {}) or {}).get(ROAD))
        params['hadi_present'] = (getattr(net, 'freeway_hadiuzzaman', {}) or {}).get(ROAD) is not None
        params['source_capacity'] = plain((getattr(net, 'freeway_source_capacity_veh_h', {}) or {}).get(ROAD))
        params['terminal_capacity'] = plain((getattr(net, 'freeway_terminal_capacity_veh_h', {}) or {}).get(ROAD))
        offs = getattr(net, 'off_ramp_from_freeway', {}) or {}
        params['offramp_segment_index'] = {o: plain((getattr(net, 'off_ramp_segment_index', {}) or {}).get(o))
                                           for o, link in offs.items() if link == ROAD}
        params['ramps_to_road'] = sorted(r for r, link in (getattr(net, 'ramp_to_freeway', {}) or {}).items()
                                         if link == ROAD)
        params['lane_plant'] = rt.lanes.get(ROAD) is not None
        init = {'t': num(state.time_sec), 'stock_veh': stock_of(state, lengths),
                'speed_kmh': [num(x) for x in state.freeway_speed[ROAD]],
                'density': [num(x) for x in state.freeway_density[ROAD]],
                'lanes': [num(x) for x in state.freeway_effective_lanes[ROAD]],
                'origin_queue_veh': num((getattr(state, 'mainline_origin_queue', {}) or {}).get(ROAD, 0.0))}
        return {'params': params, 'initial': init}

    def frame_of(code):
        frame = sys._getframe(1)
        while frame is not None and frame.f_code is not code:
            frame = frame.f_back
        return frame

    def exit_record(blk, retval, dt):
        """X1/X2 (PRE_VP_FIXED): numbers of the step's own return value only; no model call, no model write.
        Never raises: a problem is listed in exit_missing and the analysis then treats the exits as not available."""
        try:
            if S['exits'] is None:
                idx = ((S['first'] or {}).get('params') or {}).get('offramp_segment_index') or {}
                S['exits'] = sorted(str(o) for o in idx)
            diag = None
            if isinstance(retval, tuple) and len(retval) >= 3 and isinstance(retval[2], dict):
                diag = retval[2].get(ROAD)
            if not isinstance(diag, dict):
                if 'no_diagnostics' not in S['exit_missing']:
                    S['exit_missing'].append('no_diagnostics')
                return
            ex = blk.setdefault('exit_dt', {})
            exb = blk.setdefault('exit_blocked_dt', {})
            for o in S['exits']:
                for key, acc in (('offramp_flow_' + o, ex), ('offramp_blocked_flow_' + o, exb)):
                    if key in diag:
                        acc[o] = acc.get(o, 0.0) + num(diag[key]) * dt
                    elif key not in S['exit_missing']:
                        S['exit_missing'].append(key)
            if 'speed_projection_count' in diag:
                blk['speed_proj'] = blk.get('speed_proj', 0.0) + num(diag['speed_projection_count'])
            elif 'speed_projection_count' not in S['exit_missing']:
                S['exit_missing'].append('speed_projection_count')
        except Exception as exc:
            if len(S['exit_missing']) < 20:
                S['exit_missing'].append('exit_error ' + repr(exc)[:200])

    targets = {}

    def on_start(code, offset):
        if code not in targets:
            return None
        try:
            frame = frame_of(code)
            if frame is not None and S['first'] is None:
                with lock:
                    loc = frame.f_locals
                    S['first'] = snapshot(loc['self'], loc['state'])
                    S['t_first'] = num(loc['state'].time_sec)
        except Exception as exc:
            note(exc)
        return None

    def on_return(code, offset, retval):
        if code not in targets:
            if code is order.get('install_code'):
                f = order.get('finder')
                if f is not None and f in sys.meta_path and sys.meta_path[0] is not f:
                    sys.meta_path.remove(f)
                    sys.meta_path.insert(0, f)
                    S['order_fixes'] += 1
            return None
        try:
            frame = frame_of(code)
            if frame is None:
                return None
            loc = frame.f_locals
            rt, state = loc['self'], loc['state']
            net = rt.configs[ROAD].network
            dt = num(rt.configs[ROAD].simulation.T_f_sec)
            t = num(state.time_sec)
            with lock:
                if S['lengths'] is None:
                    S['lengths'] = lengths_of(net, len(state.freeway_density[ROAD]))
                if S['t_first'] is None:
                    S['t_first'] = t
                b = str(int((t - S['t_first']) // BLOCK))
                stock = stock_of(state, S['lengths'])
                speed = [num(x) for x in state.freeway_speed[ROAD]]
                flow = [num(x) for x in state.freeway_flow[ROAD]]
                blk = S['blocks'].setdefault(b, {'dt': 0.0, 'n_dt': [0.0] * len(stock), 'nv_dt': [0.0] * len(stock),
                                                 'q_dt': [0.0] * len(stock), 'oq_dt': 0.0, 'steps': 0})
                for i, n in enumerate(stock):
                    blk['n_dt'][i] += n * dt
                    blk['nv_dt'][i] += n * speed[i] * dt
                    blk['q_dt'][i] += flow[i] * dt
                blk['dt'] += dt
                blk['steps'] += 1
                blk['oq_dt'] += num((getattr(state, 'mainline_origin_queue', {}) or {}).get(ROAD, 0.0)) * dt
                exit_record(blk, retval, dt)
                S['steps'] += 1
                S['t_last'] = t
                if time.time() - S['last_dump'] > 30.0:
                    S['last_dump'] = time.time()
                    dump()
        except Exception as exc:
            note(exc)
        return None

    mon.register_callback(tool, ev.PY_START, on_start)
    mon.register_callback(tool, ev.PY_RETURN, on_return)
    order = {}

    def patch_module(module):
        name = module.__name__
        if name == 'evaluation.controllers.lane_freeway_runtime':
            code = module.LaneFreewayRuntime.advance.__code__
            targets[code] = True
            mon.set_local_events(tool, code, mon.get_local_events(tool, code) | ev.PY_START | ev.PY_RETURN)
            S['patched'].append(name + '.LaneFreewayRuntime.advance')
        if name == 'evaluation.controllers.sdmpc_tangent_runtime':
            code = module.install.__code__
            order['install_code'] = code
            mon.set_local_events(tool, code, mon.get_local_events(tool, code) | ev.PY_RETURN)

    class PassiveFinder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname not in ('evaluation.controllers.lane_freeway_runtime',
                                'evaluation.controllers.sdmpc_tangent_runtime'):
                return None
            mp = list(sys.meta_path)
            after = mp[mp.index(self) + 1:] if self in mp else mp
            spec = None
            for finder in after:
                if finder is self or not hasattr(finder, 'find_spec'):
                    continue
                spec = finder.find_spec(fullname, path, target)
                if spec is not None:
                    break
            if spec is None or spec.loader is None or not hasattr(spec.loader, 'exec_module'):
                return spec
            original = spec.loader.exec_module

            def exec_module(module, _original=original):
                _original(module)
                try:
                    patch_module(module)
                except Exception as exc:
                    note(exc)
            spec.loader.exec_module = exec_module
            return spec

    finder = PassiveFinder()
    order['finder'] = finder
    sys.meta_path.insert(0, finder)
    atexit.register(lambda: dump(True))


if _OUT:
    try:
        _setup()
    except Exception as _exc:
        try:
            os.makedirs(_OUT, exist_ok=True)
            with open(os.path.join(_OUT, 'vphook_setup_error_%d.txt' % os.getpid()), 'w', encoding='utf-8') as _h:
                _h.write(repr(_exc))
        except Exception:
            pass
