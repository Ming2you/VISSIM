"""K8-6 SA gate rollout worker: one fresh process per job (TL3 / FH / DP rollouts on a captured request template).

    python -B sa_worker.py <job.pickle> <result.pickle>      (started by sa_jobs.py; never by hand on a busy PC)

Same order as sdmpc_tangent_worker.main() and k8_gates/worker.py: install the tangent finder, unpickle the request,
then sdmpc_tangent_worker.run(request, finder, result) in the deployed surrogate mode ('scalar' or 'ad').
Harness-side, in-memory changes only (nothing under the code root is edited):
  (1) horizon H: the H-block A1 forecast captured by sa_cap_child.py (demand_from_state of the same state, prefix
      equal to the captured forecast), cfg.mpc.horizon_steps = H; H beyond `segment` continues from the block-end state
      through the same endpoint (F2 / termcost continuation, k8 scratch f2_worker.py design).
  (2) entry: OBS replaces DemandStep.freeway_mainline per block by the job's observed rates (EO 150 s bundles, FD2 for
      FH); FD7 replaces urban_boundary['in_SC1001_W'] per block (FH only); FD5 sets every VSL command to 110 (FH only).
  (3) action: REFERENCE, or a three-block plan packed with sdmpc_sequence.pack (C00 / C11 / C12, H3 only), or meters.
  (4) passive recorders (wrappers that call the original first and read primal values only):
        LaneOfframpRuntime.land / .drain    per-second port stocks, inflow, release, blocked steps (N9), 10638
        urban_queue_model._phase_green_fraction / _allocate_receiving_counts   W member green / receiving-limited s
        stopline_approach.end_step          SA per-step diagnostics and per-lane realized service (key present only)
        stopline_approach.intended          (job probes T3N7) phi_l used by SA vs the general-path phi of each member
        sdmpc.omega_costs                   block-end summaries, continuation, the response transfers
                                            (+ job probes T15b: shared-urban-kind-service of the captured response)
        sdmpc_tangent_reverse.Trace.jacobian  (variant TAN, mode 'ad') forward sweep of the tape for d FW_W(T+450)
  (5) mode ad_full (G-EB-11(e)): K8 amendment 10 rule (sa_s3parity.py): the K8-2 S3 ledger gate is instrumented and
      sdmpc_tangent_state.state_error is routed through sa_s3parity.compare (comparator unchanged); the report is
      result / summary 's3_parity' (excluded records per site and origin, sa_created, mismatches outside the rule).
Per-second records for the G-EB-5 8970.1 s cut (amendment 5 section 2-4): steps.inflow_<off> (port landing veh in that
second) and w_departures_steps (W member departures per response second).
Output: result.pickle (everything) + summary.json next to it (sa_common contract k8-sa-job/v1); a failed run carries
error_kind / error_site of its full traceback (sa_errors, the one table of K8 amendment 7 §2)."""
import copy
import hashlib
import json
import math
import os
import pickle
import sys
import time
import traceback
from collections import defaultdict
from pathlib import Path

import importlib.abc

import sa_errors  # stdlib only; this script's folder is sys.path[0] while its imports run
import sa_s3parity as S3P  # stdlib only at import; must run untransformed (imported before the tangent finder)

R = Path(os.environ.get('K8G_ROOT') or Path(__file__).resolve().parents[4]).resolve()

GATE = 'in_SC1001_W'
W_MEMBERS = ('SC1001_W_to_E_SC1002', 'SC1001_W_to_S_SC1003', 'SC1001_W_to_N_SC2002')
W_E = 'SC1001_W_to_E_SC1002'
ONE = 'SC1001_W_to_onE'
RECEIVERS = ('SC1001_to_SC1002', 'SC1001_to_SC1003', 'SC1001_to_SC2002')
RECORD_OFFS = ('10491', '10481', '10638')
BLOCKED_MARGIN = 1.0
STATE = {'job': None, 'T0': None, 'dt': 150.0, 'H': 3, 'block_ends': [], 'summary': None, 'x10490': None,
         'follower': None, 'sa_counters0': None}
PROBES = {'T3N7': None, 'T15b': None}
REC = {'steps': defaultdict(list), 'cap': {}, 'inflow': defaultdict(lambda: defaultdict(float)),
       'release': defaultdict(lambda: defaultdict(float)), 'green': defaultdict(lambda: defaultdict(set)),
       'limited': defaultdict(lambda: defaultdict(set)), 'e_bound': defaultdict(set), 'onE_steps': defaultdict(int),
       'vmin_steps': defaultdict(int), 'sa_end_calls': 0, 'sa_last': None,
       'sa_lane': defaultdict(lambda: defaultdict(float)), 'samples30': {'t': [], 'fw_w_v': [], 'fw_w_n': []},
       'errors': []}
TANGENT = {'nodes': None, 'axes': None, 'values': None, 'error': None}
S3PARITY = {'log': None}         # K8 amendment 10 (mode ad_full)
SEGMENTS = {'sec': []}


def _f(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    v = getattr(x, 'value', None)
    if v is None:
        v = getattr(x, '_validation_primal', None)
    try:
        return float(v)
    except Exception:
        return float('nan')


def _block_of(t):
    """1-based block index of a step that ENDS at time t (t in (T0+150(k-1), T0+150k])."""
    return max(1, int(math.ceil((t - STATE['T0'] - 1e-9) / STATE['dt'])))


class Post(importlib.abc.MetaPathFinder):
    def __init__(self, callbacks):
        self.callbacks = dict(callbacks)

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


# ------------------------------------------------------------------------------------------------ recorders
def _note(exc):
    if len(REC['errors']) < 20:
        REC['errors'].append(traceback.format_exc()[-600:] if exc is None else repr(exc)[:400])


def patch_lor(module):
    cls = module.LaneOfframpRuntime
    orig_land, orig_drain = cls.land, cls.drain

    def land(self, state, cfg, end, flows, group_flows):
        out = orig_land(self, state, cfg, end, flows, group_flows)
        if STATE['T0'] is None:
            return out
        try:
            t = float(end)
            k = _block_of(t)
            REC['steps']['t'].append(t)
            for off in RECORD_OFFS:
                if off not in self.ports:
                    continue
                p = self.ports[off]
                REC['cap'][off] = _f(p.capacity)
                REC['steps']['stock_' + off].append(_f(p.stock))
                landed = _f(flows.get(off, 0.0)) / 3600.0
                REC['steps']['inflow_' + off].append(landed)        # G-EB-5 8970.1 s cut (amendment 5 2-4)
                REC['inflow'][off][k] += landed
                if (off == '10491' and REC.get('first_block_lanes') is None
                        and _f(p.stock) >= _f(p.capacity) - BLOCKED_MARGIN):
                    REC['first_block_lanes'] = lane_composition(state, t)
            v = state.freeway_speed.get('FW_W') if hasattr(state, 'freeway_speed') else None
            if v is not None:
                vmin = _f(cfg.network.v_min)
                cells = [_f(v[i]) for i in (6, 7, 8, 9) if i < len(v) and v[i] is not None]
                REC['steps']['cell_v_6_9_min'].append(min(cells) if cells else None)
                if cells and min(cells) <= vmin + 1e-9:
                    REC['vmin_steps'][k] += 1
                if abs((t - STATE['T0']) / 30.0 - round((t - STATE['T0']) / 30.0)) < 1e-9:
                    from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts
                    REC['samples30']['t'].append(t)
                    REC['samples30']['fw_w_v'].append([_f(x) if x is not None else None for x in v])
                    REC['samples30']['fw_w_n'].append([_f(x) for x in continuity_vehicle_counts(state, cfg)['FW_W']])
            x10490 = STATE['x10490']
            if x10490 is not None and _f(state.urban_movement_queue.get(ONE, 0.0)) >= (x10490 - 239.38422422843928) / 6.0:
                REC['onE_steps'][k] += 1
        except Exception as exc:  # passive: never break the rollout
            _note(exc)
        return out

    def drain(self, state, control, cfg, step, routing):
        before = {}
        if STATE['T0'] is not None:
            try:
                before = {off: _f(self.ports[off].stock) for off in RECORD_OFFS if off in self.ports}
            except Exception as exc:
                _note(exc)
        out = orig_drain(self, state, control, cfg, step, routing)
        if before:
            try:
                k = _block_of(float(step) + 1.0)
                for off, b in before.items():
                    REC['release'][off][k] += b - _f(self.ports[off].stock)
            except Exception as exc:
                _note(exc)
        return out
    cls.land, cls.drain = land, drain


def lane_composition(state, t):
    """N15 (G-EB-6 (b) report): SA lane stock by origin at the first 10491 blocked step (key present only)."""
    sa = getattr(state, 'stopline_approach_state', None)
    if not isinstance(sa, dict):
        return {'t': t, 'sa': False}
    out = {'t': t, 'sa': True, 'lanes': {}}
    for lane, packets in sa['lanes'].items():
        row = defaultdict(float)
        for packet in packets:
            row[str(packet[2])] += _f(packet[4])
        row['carry'] = sum(_f(v) for v in (sa['carry'].get(lane) or {}).values())
        out['lanes'][str(lane)] = dict(row)
    return out


def _caller_step():
    frame = sys._getframe(2)
    for _ in range(4):
        if frame is None:
            return None
        loc = frame.f_locals
        for name in ('step_idx', 'urban_step_index', 'step'):
            v = loc.get(name)
            if isinstance(v, int):
                return v
        frame = frame.f_back
    return None


def patch_endpoint(module):
    """Install the UQM recorders lazily, at each endpoint call: install_worker_runtime (inside
    sdmpc_tangent_worker.run) re-patches urban_queue_model._phase_green_fraction (adapter monitor-fixed-signal /
    phase-vector patches), so a wrapper set at import time would be replaced.  The wrapper goes over whatever function
    is installed when the rollout starts and is idempotent."""
    original = module.evaluate_price_point

    def evaluate_price_point(*args, **kwargs):
        uqm = sys.modules.get('src.models.urban_queue_model')
        if uqm is not None:
            try:
                wrap_uqm(uqm)
            except Exception as exc:
                _note(exc)
        return original(*args, **kwargs)
    module.evaluate_price_point = evaluate_price_point


def wrap_uqm(module):
    if getattr(module._phase_green_fraction, '__k8sa__', False) and getattr(
            module._allocate_receiving_counts, '__k8sa__', False):
        return
    orig_green, orig_alloc = module._phase_green_fraction, module._allocate_receiving_counts
    specs_ref = {}

    def member_of(cfg, spec):
        """W member whose spec this is: identity first, else equal content (movement_specs may copy)."""
        rows = specs_ref.get(id(cfg))
        if rows is None:
            rows = [(m, cfg.network.urban_movements[m]) for m in W_MEMBERS if m in cfg.network.urban_movements]
            specs_ref[id(cfg)] = rows
        for m, s in rows:
            if s is spec:
                return m
        if isinstance(spec, dict) and spec.get('signal') == 'SC1001':
            for m, s in rows:
                if s == spec:
                    return m
        return None

    def _phase_green_fraction(control, cfg, spec, *args, **kwargs):
        out = orig_green(control, cfg, spec, *args, **kwargs)
        if STATE['T0'] is not None:
            try:
                m = member_of(cfg, spec)
                step = kwargs.get('urban_step_index', args[0] if args else None)
                if m is not None and isinstance(step, int) and _f(out) > 0.0:
                    REC['green'][_block_of(step + 1.0)][m].add(step)
            except Exception as exc:
                _note(exc)
        return out

    def _allocate_receiving_counts(rule, intended, available_space):
        out = orig_alloc(rule, intended, available_space)
        if STATE['T0'] is not None:
            try:
                hit = [m for m in W_MEMBERS if m in intended]
                if hit:
                    step = _caller_step()
                    if step is not None:
                        k = _block_of(step + 1.0)
                        for m in hit:
                            want, got = _f(intended[m]), _f(out.get(m, 0.0))
                            if want > 1e-12 and got < want - 1e-9:
                                REC['limited'][k][m].add(step)
                                if m == W_E:
                                    REC['e_bound'][k].add(step)
            except Exception as exc:
                _note(exc)
        return out
    _phase_green_fraction.__k8sa__ = True
    _allocate_receiving_counts.__k8sa__ = True
    if not getattr(orig_green, '__k8sa__', False):
        module._phase_green_fraction = _phase_green_fraction
    if not getattr(orig_alloc, '__k8sa__', False):
        module._allocate_receiving_counts = _allocate_receiving_counts
    REC.setdefault('uqm_wraps', 0)
    REC['uqm_wraps'] += 1


def patch_sa(module):
    orig = module.end_step
    if 'T3N7' in ((STATE['job'] or {}).get('probes') or ()):
        patch_sa_intended(module)

    def end_step(state, cfg, step):
        try:
            plan = state.stopline_approach_state.get('plan') or {}
            lane = plan.get('lane_realized') or {}
            k = _block_of(float(step) + 1.0)
            for l, v in lane.items():
                REC['sa_lane'][k][int(l)] += _f(v)
        except Exception as exc:
            _note(exc)
        out = orig(state, cfg, step)
        REC['sa_end_calls'] += 1
        REC['sa_last'] = {k: _f(v) for k, v in out.items()}
        return out
    module.end_step = end_step


def patch_sa_intended(module):
    """T3-N7 on a captured template (amendment 1 r2 section 8, amendment 5 section 4): the phi_l that SA.intended
    applies equals the general UFA path's phi of every member of the lane under the worker runtime (adapter patches,
    wrap_clock).  Passive: the original runs first; the comparison calls the installed _phase_green_fraction again
    (side-effect free; the green recorder keeps sets of steps)."""
    orig = module.intended
    PROBES['T3N7'] = {'calls': 0, 'max_abs_diff': 0.0, 'positive': {}, 'function': None, 'errors': 0}

    def intended(state, control, cfg, step):
        st = state.stopline_approach_state
        fresh = 'intended' not in (st.get('plan') or {})
        out = orig(state, control, cfg, step)
        if fresh and STATE['T0'] is not None:
            rec = PROBES['T3N7']
            try:
                uqm = sys.modules['src.models.urban_queue_model']
                spec = cfg.network.stopline_approach
                specs = uqm.movement_specs(cfg)
                fn = uqm._phase_green_fraction
                rec['function'] = f'{getattr(fn, "__module__", "?")}.{getattr(fn, "__qualname__", "?")}'
                for lane, row in spec['lanes'].items():
                    phi_sa = _f(st['plan']['budget'][lane]) / (row['s_veh_h'] * cfg.simulation.T_u_h)
                    for member in row['members']:
                        phi = _f(fn(control, cfg, specs[member], urban_step_index=step))
                        rec['max_abs_diff'] = max(rec['max_abs_diff'], abs(phi_sa - phi))
                    if phi_sa > 0.0:
                        rec['positive'][str(lane)] = rec['positive'].get(str(lane), 0) + 1
                rec['calls'] += 1
            except Exception as exc:
                rec['errors'] += 1
                _note(exc)
        return out
    module.intended = intended


def probe_kind_service(point, cfg):
    """T15b on a captured template: shared-urban-kind-service (area_leader_objective) of the captured response vs the
    SA counters of the same rollout (deltas from the template state)."""
    from evaluation.controllers import area_leader_objective as constraints
    out = {'error': None}
    try:
        q = constraints.shared_urban_quantities(STATE['follower'], point.control_area_response,
                                                start_sec=STATE['T0'], horizon_steps=len(point.states))
        served = q['served_by_movement_veh']
        spec = cfg.network.stopline_approach
        last = point.states[-1].stopline_approach_state['counters']
        first = STATE['sa_counters0'] or {}
        internal = defaultdict(float)
        for row in (point.control_area_response or {}).get('transfers') or []:
            key = row.get('route_key')
            if isinstance(key, str) and key.startswith('stopline_internal:'):
                internal[key[len('stopline_internal:'):]] += _f(row['vehicles'])
        out.update(schema=q.get('schema'), owner_SC1001=q['owners'].get('SC1001'),
                   served_members={m: _f(served.get(m, 0.0)) for m in spec['members']},
                   served_offramp={m: _f(served.get(m, 0.0)) for m in spec['offramp_movements']},
                   internal_by_member=dict(internal),
                   counters_delta={k: _f(v) - _f(first.get(k, 0.0)) for k, v in last.items()},
                   horizon_steps=len(point.states), urban_steps=len(point.states) * int(cfg.simulation.K_cu))
    except Exception:
        out['error'] = traceback.format_exc()[-1500:]
    PROBES['T15b'] = out


# ------------------------------------------------------------------------------------------------ block summaries
def block_row(k, s, cfg):
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts
    net = cfg.network
    cap = net.urban_link_storage_veh
    occ = {key: _f(cap[key]) - _f(s.urban_link_storage.get(key, cap[key])) for key in cap}
    q = {m: _f(v) for m, v in s.urban_movement_queue.items()}
    ports = getattr(s, 'lane_offramp_runtime', None)
    port = {off: (_f(ports.ports[off].stock) if ports is not None and off in ports.ports else None)
            for off in ('10491', '10481')}
    transit_gate = math.fsum(_f(v) for v in (s.urban_inflow_transit_buffer.get('gate:' + GATE) or {}).values())
    w_all = math.fsum(v for m, v in q.items() if m.startswith('SC1001_W_to_'))
    gate_occ = occ.get(GATE, 0.0)
    counts = [_f(x) for x in continuity_vehicle_counts(s, cfg)['FW_W']]
    speeds = [(_f(x) if x is not None else None) for x in s.freeway_speed.get('FW_W', [])]
    L = get_ledger(s)
    sa = getattr(s, 'stopline_approach_state', None)
    row = dict(k=k, t_end=_f(s.time_sec),
               w_ports=dict(movement_w_all=w_all, gate_occ=gate_occ, transit_gate=transit_gate,
                            port_10491=port['10491'], port_10481=port['10481'],
                            total=w_all + gate_occ + transit_gate + (port['10491'] or 0.0) + (port['10481'] or 0.0)),
               w_ready=math.fsum(q.get(m, 0.0) for m in W_MEMBERS),
               w_out_occ=occ.get('SC1001_W_out'),
               fw_w_stock=math.fsum(counts), fw_w_cell_n=counts, fw_w_cell_v=speeds,
               cell9_v=speeds[9] if len(speeds) > 9 else None,
               origin_fw_w=_f(s.mainline_origin_queue.get('FW_W', 0.0)),
               ledger_ttt=_f(L.ttt_veh_h) if L is not None else None,
               receivers={r: occ.get(r) for r in RECEIVERS},
               ramp_queue={r: _f(s.ramp_queue.get(r, 0.0)) for r in ('RM_C10482', 'RM_C10490')},
               e_approach_queue=math.fsum(v for m, v in q.items() if m.startswith('SC1001_E_to_')),
               w_queue={m: q.get(m, 0.0) for m in W_MEMBERS + ('SC1001_W_to_onW', ONE)},
               sa_stock=({str(l): _f(v) for l, v in sa['stock'].items()} if isinstance(sa, dict) else None))
    return row


def transfer_flows(response, T0, dt, per_second=None):
    """Per-block departures of the W members from the response transfer rows (source movement:<member>); with
    `per_second` (a dict), also their sum per response end second (G-EB-5 8970.1 s cut)."""
    dep = defaultdict(lambda: defaultdict(float))
    rows = (response or {}).get('transfers') or []
    for row in rows:
        try:
            src = str(row['source'])
            if not src.startswith('movement:'):
                continue
            m = src[len('movement:'):]
            if m not in W_MEMBERS:
                continue
            end = _f(row['end_sec'])
            k = max(1, int(math.ceil((end - T0 - 1e-9) / dt)))
            dep[k][m] += _f(row['vehicles'])
            if per_second is not None:
                per_second[round(end, 6)] = per_second.get(round(end, 6), 0.0) + _f(row['vehicles'])
        except Exception as exc:
            _note(exc)
    return dep


def patch_sdmpc(module):
    original = module.omega_costs

    def omega_costs(point, cfg):
        if STATE['summary'] is None:
            try:
                STATE['summary'] = summarize_and_continue(point, cfg)
            except Exception:
                STATE['summary'] = {'error': traceback.format_exc()[-1500:]}
        return original(point, cfg)
    module.omega_costs = omega_costs


def summarize_and_continue(point, cfg):
    job = STATE['job']
    T0, dt = STATE['T0'], STATE['dt']
    blocks = [block_row(k + 1, s, cfg) for k, s in enumerate(point.states)]
    per_second = {}
    dep = transfer_flows(point.control_area_response, T0, dt, per_second)
    if 'T15b' in (job.get('probes') or ()):
        probe_kind_service(point, cfg)
    if TANGENT['nodes'] is None and job.get('variant') == 'TAN':
        record_tangent_nodes(point, cfg)
    done, last = len(point.states), point.states[-1]
    total = STATE['H']
    if done < total:
        from src.controllers import rollout_endpoint
        from evaluation.controllers.control_area_objective import get_ledger
        while done < total:
            seg = min(STATE['segment'], total - done)
            t1 = time.perf_counter()
            for row in get_ledger(last).stocks.values():   # -1e-18 cohort residues (f2 continuation note)
                for side in ('inside', 'outside'):
                    v = row[side]
                    if v < 0:
                        if v < -1e-9:
                            raise ValueError('negative cohort beyond residue: %r' % v)
                        row[side] = 0.0
            nxt = rollout_endpoint.evaluate_price_point(
                last, STATE['action'], STATE['forecast'][done:done + seg], (),
                rollout_endpoint.ObjectiveSpec(cfg, depth_override=seg, box_walk=False, score_mode='raw'),
                capture_response=True)
            if nxt.aborted or len(nxt.states) != seg:
                raise ValueError('Incomplete continued segment')
            blocks += [block_row(done + k + 1, s, cfg) for k, s in enumerate(nxt.states)]
            for kk, row in transfer_flows(nxt.control_area_response, T0, dt, per_second).items():
                for m, v in row.items():
                    dep[kk][m] += v
            done, last = done + seg, nxt.states[-1]
            SEGMENTS['sec'].append(time.perf_counter() - t1)
            del nxt
    for row in blocks:
        k = row['k']
        row['w_departures'] = {m: dep[k].get(m, 0.0) for m in W_MEMBERS}
        row['port_inflow'] = {off: REC['inflow'][off].get(k, 0.0) for off in RECORD_OFFS}
        row['port_release'] = {off: REC['release'][off].get(k, 0.0) for off in RECORD_OFFS}
        row['w_green_sec'] = {m: float(len(REC['green'][k].get(m, ()))) for m in W_MEMBERS}
        row['w_recv_limited_sec'] = {m: float(len(REC['limited'][k].get(m, ()))) for m in W_MEMBERS}
        row['e_recv_bound_sec'] = float(len(REC['e_bound'].get(k, ())))
        row['onE_threshold_steps'] = float(REC['onE_steps'].get(k, 0))
        row['vmin_steps_cells_6_9'] = float(REC['vmin_steps'].get(k, 0))
        row['sa_lane_served'] = ({str(l): v for l, v in REC['sa_lane'][k].items()} if REC['sa_end_calls'] else None)
    seconds = sorted(per_second)
    return {'blocks': blocks, 'w_departures_steps': {'t': seconds, 'veh': [per_second[t] for t in seconds]}}


# ------------------------------------------------------------------------------------------------ tangent (G-EB-8)
def record_tangent_nodes(point, cfg):
    """Block-3 FW_W continuity counts as tape nodes (attribute reads only; no Dual arithmetic)."""
    from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts
    s = point.states[min(2, len(point.states) - 1)]
    nodes, trace = [], None
    for x in continuity_vehicle_counts(s, cfg)['FW_W']:
        try:
            n = object.__getattribute__(x, 'node')
        except (AttributeError, TypeError):
            n = 0
        if n:
            nodes.append(int(n))
            trace = trace or getattr(x, 'trace', None)
    TANGENT['nodes'] = nodes
    TANGENT['trace_id'] = id(trace) if trace is not None else None


def patch_reverse(module):
    cls = module.Trace
    original = cls.jacobian

    def jacobian(self, *args, **kwargs):
        if TANGENT['nodes'] and TANGENT['values'] is None and TANGENT.get('trace_id') == id(self):
            try:
                TANGENT['values'] = forward_sweeps(self, TANGENT['nodes'], [a['index'] for a in TANGENT['axes']])
            except Exception:
                TANGENT['error'] = traceback.format_exc()[-1500:]
        return original(self, *args, **kwargs)
    cls.jacobian = jacobian


def forward_sweeps(trace, nodes, axes):
    """d(sum of nodes)/d(axis) for each axis: t = J e_axis by one forward pass of the tape per axis (s3site sweep)."""
    import numpy as np
    try:
        import numba

        @numba.njit(cache=False)
        def sweep(p1, p2, w1, w2, sn, sa, sw, axis, n):
            t = np.zeros(n)
            for k in range(len(sn)):
                if sa[k] == axis:
                    t[sn[k]] += sw[k]
            for i in range(1, n):
                a = p1[i]
                b = p2[i]
                if a != 0:
                    t[i] += w1[i] * t[a]
                if b != 0:
                    t[i] += w2[i] * t[b]
            return t
    except Exception:
        def sweep(p1, p2, w1, w2, sn, sa, sw, axis, n):
            t = np.zeros(n)
            for k in range(len(sn)):
                if sa[k] == axis:
                    t[sn[k]] += sw[k]
            for i in range(1, n):
                if p1[i]:
                    t[i] += w1[i] * t[p1[i]]
                if p2[i]:
                    t[i] += w2[i] * t[p2[i]]
            return t
    n = len(trace.p1)
    TANGENT['n_trace_axes'] = len(getattr(trace, 'steps', ()) or ())
    v = [np.frombuffer(trace.p1, dtype=np.int64), np.frombuffer(trace.p2, dtype=np.int64),
         np.frombuffer(trace.w1, dtype=np.float64), np.frombuffer(trace.w2, dtype=np.float64),
         np.frombuffer(trace.seed_nodes, dtype=np.int64), np.frombuffer(trace.seed_axes, dtype=np.int64),
         np.frombuffer(trace.seed_weights, dtype=np.float64)]
    out = {}
    for axis in axes:
        t = sweep(v[0], v[1], v[2], v[3], v[4], v[5], v[6], int(axis), n)
        out[int(axis)] = float(sum(float(t[j]) for j in nodes))
    del v
    return out


def tangent_axes(request, owner='SC1001'):
    rows = []
    gv = request.get('green_vectors') or []
    for i, a in enumerate(request.get('axes') or []):
        if not isinstance(a, dict):
            continue
        if a.get('kind', 'green') == 'green' and str(a.get('owner')) == owner:
            rows.append(dict(index=i, owner=a.get('owner'), key=a.get('key'), block=a.get('block'),
                             scale=a.get('scale'), axis={k: (v if isinstance(v, (int, float, str, type(None)))
                                                             else repr(v)) for k, v in a.items()},
                             green_vector=(dict(gv[i]) if i < len(gv) and isinstance(gv[i], dict) else None)))
    return rows


# ------------------------------------------------------------------------------------------------ job setup
def apply_entry(forecast, job):
    out, applied = [], {'freeway': {}, 'gate': {}}
    obs = {k: v for k, v in (job.get('obs_entry') or {}).items() if not k.startswith('_')}
    gate = job.get('gate_demand') or {}
    for k, d in enumerate(forecast):
        d2 = copy.deepcopy(d)
        if obs:
            fm = dict(d2.freeway_mainline)
            for road, rates in obs.items():
                if k >= len(rates):
                    raise ValueError('OBS entry shorter than the horizon')
                applied['freeway'].setdefault(road, []).append([_f(fm.get(road, float('nan'))), float(rates[k])])
                fm[road] = float(rates[k])
            d2.freeway_mainline = fm
        if gate:
            ub = dict(d2.urban_boundary)
            for origin, rates in gate.items():
                if k >= len(rates):
                    raise ValueError('gate demand shorter than the horizon')
                applied['gate'].setdefault(origin, []).append([_f(ub.get(origin, float('nan'))), float(rates[k])])
                ub[origin] = float(rates[k])
            d2.urban_boundary = ub
        out.append(d2)
    return out, applied


def build_action(job, request, reference):
    from evaluation.controllers import sdmpc_sequence as seq
    spec = job.get('action', 'REFERENCE')
    action = reference.copy()
    notes = {}
    if job.get('vsl110'):
        notes['vsl110_changed'] = sorted(k for k, v in action.vsl.items() if _f(v) != 110.0)
        for k in list(action.vsl):
            action.vsl[k] = 110.0
    if spec == 'REFERENCE':
        return action, notes
    follower = request['owned'][0]
    cfg = follower.cfg
    if 'meters' in spec:
        from evaluation.controllers.sdmpc_continuous import meter_rate
        rows = cfg.network.physical_ramp_branches['ramps']
        for ramp, g in spec['meters'].items():
            action.diagnostics['rw_meter_green_' + ramp] = float(g)
            action.ramp_metering[ramp] = meter_rate(float(g), rows[ramp])
        return action, notes
    if 'offramp_profile' in spec:
        # C00 / C11 / C12 (termcost candidates.py:180-199, Realizer.offramp_phase / green_axis_delta / realize):
        # the signal's off-ramp phase (max sum beta x movement capacity of its off_ramp movements) gets
        # sign x (6, 10, 10) s in blocks 0/1/2; the other live phases give/take it in proportion to their slack to
        # the physical bounds, clipped to what the bounds allow; decode rounding to 3 decimals and the pivot (last
        # live phase) = effective green total - the others.  Phase-level form of the axis-coordinate rule (the
        # same green_times when the axis vectors are unit-with-pivot, which the read-back below reports).
        if int(job['H']) != 3:
            raise ValueError('three-block plans are H3 only (sdmpc_sequence.prediction_scope)')
        from evaluation.controllers import signal_actuation_contract as signals
        p = spec['offramp_profile']
        signal, sign, profile = p['signal'], float(p['sign']), [float(x) for x in p['profile']]
        net = cfg.network
        best = defaultdict(float)
        for m, row in net.urban_movements.items():
            if row.get('signal') == signal and row.get('kind') == 'off_ramp' and row.get('phase'):
                best[row['phase']] += float(row['beta']) * float(net.movement_capacity_by_movement_veh_h.get(m, 0.0))
        if not best:
            raise ValueError('no off-ramp movement at ' + signal)
        phase = max(sorted(best), key=lambda q: best[q]).split('_', 1)[1]
        live = tuple(net.signal_live_phases(signal))
        basis = signals.native_clock_basis(net, signal)
        if basis is not None and basis['kind'] == 'concurrent_p1_p2':
            raise ValueError('concurrent signal: no declared rule')
        bounds = signals.phase_bounds(net, signal)
        controls, effective = [], []
        for d in profile:
            delta = sign * d
            g = {q: _f(reference.green_times[signal + '_' + q]) for q in live}
            others = [q for q in live if q != phase]
            if delta >= 0:
                slack = {q: max(0.0, g[q] - bounds[q][0]) for q in others}
                eff = min(delta, bounds[phase][1] - g[phase], sum(slack.values()))
            else:
                slack = {q: max(0.0, bounds[q][1] - g[q]) for q in others}
                eff = -min(-delta, g[phase] - bounds[phase][0], sum(slack.values()))
            total = sum(slack.values())
            change = {phase: eff}
            for q in others:
                change[q] = -eff * slack[q] / total if total > 0 else 0.0
            c = action.copy()
            greens = dict(c.green_times)
            pivot = live[-1]
            for q in live:
                if q != pivot:
                    greens[signal + '_' + q] = round(g[q] + change[q], 3)
            greens[signal + '_' + pivot] = round(_f(net.signal_effective_green_total(signal))
                                                 - sum(greens[signal + '_' + q] for q in live if q != pivot), 3)
            c.green_times = greens
            signals.validate_control(c, cfg)
            controls.append(c)
            effective.append(round(eff, 6))
        notes.update(signal=signal, phase=phase, requested=[sign * d for d in profile], effective=effective,
                     beta_capacity=dict(best),
                     blocks=[{k: _f(v) for k, v in c.green_times.items() if k.startswith(signal + '_')}
                             for c in controls])
        return seq.pack(controls), notes
    raise ValueError('unknown job action ' + repr(spec)[:200])


def main():
    job_path, result_path = sys.argv[1:3]
    started = time.perf_counter()
    result = {'job_path': job_path}
    try:
        job = pickle.loads(Path(job_path).read_bytes())
        STATE['job'] = job
        STATE['x10490'] = job.get('x10490_m')
        from evaluation.controllers.sdmpc_tangent_runtime import install
        finder = install(R, 'reverse-v1')
        callbacks = {'evaluation.controllers.lane_offramp_runtime': patch_lor,
                     'src.controllers.rollout_endpoint': patch_endpoint,
                     'evaluation.controllers.stopline_approach': patch_sa,
                     'evaluation.controllers.sdmpc': patch_sdmpc}
        if job.get('variant') == 'TAN':
            callbacks['evaluation.controllers.sdmpc_tangent_reverse'] = patch_reverse
        sys.meta_path.insert(0, Post(callbacks))
        from evaluation.controllers import sdmpc_tangent_worker as standard
        request = pickle.loads(Path(job['template']).read_bytes())
        follower, state, reference, forecast = request['owned']
        STATE['follower'] = follower
        sa0 = getattr(state, 'stopline_approach_state', None)
        STATE['sa_counters0'] = ({k: _f(v) for k, v in sa0['counters'].items()} if isinstance(sa0, dict) else None)
        H = int(job['H'])
        segment = int(job.get('segment') or H)
        first = min(segment, H)
        if H > len(forecast):
            longer = pickle.loads(Path(job['forecast_long']).read_bytes())
            if len(longer) < H:
                raise ValueError('captured long forecast shorter than the horizon')
            if pickle.dumps(list(longer[:len(forecast)]), protocol=5) != pickle.dumps(list(forecast), protocol=5):
                raise ValueError('long forecast prefix differs from the captured forecast')
            forecast = list(longer[:H])
        else:
            forecast = list(forecast[:H])
        forecast, applied = apply_entry(forecast, job)
        follower.cfg.mpc.horizon_steps = H          # aggregate time bins cover the whole H (termcost / F2)
        request['owned'] = (follower, state, reference, forecast)
        request['horizon'] = first
        action, notes = build_action(job, request, reference)
        request['action'] = copy.deepcopy(action)
        mode = job.get('mode', 'scalar')
        if mode not in ('scalar', 'ad', 'ad_full'):
            raise ValueError('sa_worker modes: scalar | ad | ad_full')
        if mode == 'ad_full':
            # Non-surrogate reverse AD (scalar witness + tangent + full state_error): the two diagnostic-only options
            # that need the surrogate worker are switched off in this process only (K8-0b worker.py ad_full,
            # amend1 S1_OWNER section 5 recipe; model arithmetic unchanged).
            opts = follower.cfg.network.sdmpc_options
            opts['central_multiplier'] = False
            opts['prediction_hotpath'] = False
            # K8 amendment 10: the T20 rule on the full state comparison (harness wrapper, comparator unchanged)
            from evaluation.controllers import control_area_objective as cao_module
            from evaluation.controllers import sdmpc_tangent_state as tangent_state_module
            S3PARITY['log'] = S3P.install_worker(cao_module, tangent_state_module, root=R)
        else:
            request['surrogate_evaluation'] = mode
            from evaluation.controllers.sdmpc_tangent_surrogate import token
            request['surrogate_context_sha256'] = token((request['owned'], request['runtime'], request['bootstrap'],
                                                         request['horizon']))
        STATE.update(T0=float(state.time_sec), dt=float(follower.cfg.simulation.T_c_sec), H=H, segment=segment,
                     forecast=forecast, action=request['action'])
        if job.get('variant') == 'TAN':
            TANGENT['axes'] = tangent_axes(request, job.get('tangent_owner', 'SC1001'))
            TANGENT['n_request_axes'] = len(request.get('axes') or ())
        result['entry_applied'] = applied
        result['action_notes'] = notes
        try:
            seg_index = follower.cfg.network.off_ramp_segment_index
            result['or_d_w_cell'] = {k: int(v) for k, v in seg_index.items() if str(k) in ('OR_D_W', '10491', '10479')}
        except Exception:
            result['or_d_w_cell'] = None
        out = standard.run(request, finder, result)
        result['out_keys'] = sorted(out.keys())
        result['costs'] = [_f(x) for x in out.get('costs', [])]
        result['resources'] = [_f(x) for x in out.get('resources', [])]
        result['costs_order'] = list(request['costs_order'])
        sp = out.get('surrogate_prediction') or {}
        result['objective_veh_h'] = sp.get('objective_veh_h')
        result['objective_repr'] = repr(sp.get('objective_veh_h'))
        for key in ('cost_jacobian', 'resource_jacobian', 'ad_axes', 'trace', 'max_primal_state_error',
                    'complete_primal_state_match', 'scalar_rollouts', 'tangent_rollouts'):
            if key in out:
                result[key] = out[key]
        if isinstance(STATE['summary'], dict) and 'error' in STATE['summary']:
            raise RuntimeError('summary failed: ' + STATE['summary']['error'])
        result['summary'] = STATE['summary']
    except Exception:
        result['error'] = traceback.format_exc()
    result['s3_parity'] = S3PARITY['log'].report() if S3PARITY['log'] is not None else None
    result['segment_sec'] = SEGMENTS['sec']
    result['recorder_errors'] = REC['errors']
    result['uqm_wraps'] = REC.get('uqm_wraps', 0)
    result['wall_sec'] = time.perf_counter() - started
    result['python_hash_seed'] = os.environ.get('PYTHONHASHSEED')
    result['steps'] = {k: list(v) for k, v in REC['steps'].items()}
    result['cap'] = dict(REC['cap'])
    result['samples30'] = REC['samples30']
    result['sa'] = ({'end_step_calls': REC['sa_end_calls'], 'step_diag_last': REC['sa_last'],
                     'first_block_lanes': REC.get('first_block_lanes')}
                    if REC['sa_end_calls'] else None)
    result['first_block_lanes'] = REC.get('first_block_lanes')
    probes = (STATE['job'] or {}).get('probes') or ()
    result['probes'] = {k: PROBES.get(k) for k in probes} if probes else None
    result['tangent'] = (dict(axes=TANGENT['axes'], values=TANGENT['values'], error=TANGENT['error'],
                              n_nodes=len(TANGENT['nodes'] or ()), n_trace_axes=TANGENT.get('n_trace_axes'),
                              n_request_axes=TANGENT.get('n_request_axes'))
                         if TANGENT['axes'] is not None else None)
    Path(result_path).write_bytes(pickle.dumps(result, protocol=5))
    summary = to_summary(result)
    Path(result_path).with_name('summary.json').write_text(json.dumps(summary, indent=1, default=repr), encoding='utf-8')
    return 1 if 'error' in result else 0


error_kind = sa_errors.error_kind          # the one table (amendment 7 §2, review N-r4-2)


def to_summary(result):
    job = STATE['job'] or {}
    steps = result.get('steps') or {}
    first = {}
    for off in RECORD_OFFS:
        xs = steps.get('stock_' + off) or []
        cap = (result.get('cap') or {}).get(off)
        hit = None
        if cap is not None:
            for t, x in zip(steps.get('t') or [], xs):
                if x is not None and x >= cap - BLOCKED_MARGIN:
                    hit = t
                    break
        first[off] = hit
    blocks = ((result.get('summary') or {}).get('blocks') or [])
    for row in blocks:
        k = row['k']
        row['blocked_steps'] = {}
        for off in RECORD_OFFS:
            cap = (result.get('cap') or {}).get(off)
            xs = steps.get('stock_' + off) or []
            row['blocked_steps'][off] = float(sum(1 for t, x in zip(steps.get('t') or [], xs)
                                                  if cap is not None and x is not None and x >= cap - BLOCKED_MARGIN
                                                  and _block_of(t) == k))
    err = result.get('error')
    return {'schema': 'k8-sa-job/v1',
            'job': {k: job.get(k) for k in ('label', 'harness', 'T', 'seed', 'frame_T', 'arm', 'entry', 'H', 'variant',
                                            'mode', 'tree', 'template', 'forecast_long')},   # inputs: B-r4-1
            'ok': err is None, 'error': (err or '')[-2000:] or None, 'error_kind': error_kind(err),
            'error_site': sa_errors.error_site(err) if err is not None else None,   # full traceback (amendment 7 §2)
            'wall_sec': result.get('wall_sec'), 'objective': result.get('objective_veh_h'),
            'objective_repr': result.get('objective_repr'), 'costs': result.get('costs'),
            'costs_order': result.get('costs_order'), 'resources': result.get('resources'),
            'T0': STATE.get('T0'), 'block_sec': STATE.get('dt'), 'blocks': blocks,
            'steps': steps, 'cap': result.get('cap'), 'samples30': result.get('samples30'),
            'first_block_t': first, 'sa': result.get('sa'), 'tangent': result.get('tangent'),
            'w_departures_steps': (result.get('summary') or {}).get('w_departures_steps'),
            'probes': result.get('probes'),
            'max_primal_state_error': result.get('max_primal_state_error'),
            'complete_primal_state_match': result.get('complete_primal_state_match'),
            's3_parity': result.get('s3_parity'),
            'action_notes': result.get('action_notes'), 'entry_applied': result.get('entry_applied'),
            'or_d_w_cell': result.get('or_d_w_cell'), 'recorder_errors': result.get('recorder_errors'),
            'uqm_wraps': result.get('uqm_wraps'),
            'segment_sec': result.get('segment_sec')}


if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[1] in ('-h', '--help'):
        print(__doc__)
        raise SystemExit(0 if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help') else 2)
    sys.path[0] = str(R / 'evaluation' / 'controllers')     # as the standard worker script
    sys.path[:0] = [str(R), str(R / 'vendor/NumSim-mine')]
    raise SystemExit(main())
