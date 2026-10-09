"""K8b-5 structural parity probe (K8_PREDECLARATION_AMENDMENT_18 sections 2.3.3-2 and 3.3 U5); run only as a fresh
subprocess.

    python -B k8b5_parity_probe.py <forward|reverse-v1> <direct_row|land_city|land_city_full_room> [ROOT]

The tangent Finder of ROOT (default: this checkout) is installed before any model import, exactly as the AD worker
does, so LOR, UFA, SA, UQM and the DelayedPort run instrumented.  Each scenario runs the same exact-arithmetic input
twice in this process -- the scalar witness with the operand at its structural value (0.0, a float) and the tangent
run with a Dual operand displaced by +2**-51 -- and compares the two resulting states with
sdmpc_tangent_worker.state_error (not instrumented).  Prints one JSON line.  Synthetic cfg / state only (no capture,
rollout, adapter run or VISSIM).

  direct_row           A-1: the LOR direct row 10483 -> SC1001_W_out with the W_out room at its structural 0
                       (urban.wout_exit_law installed), then the UFA store updates until the direct mass matures.
                       Compared: the K8b containers (wout_direct_pending, wout_exit_counters, wout_class_store) after
                       the drain and at the end; the whole state is compared for the report only (the former
                       uqm._schedule key below the K8b-pre predicate LOR:89 is a K8b-pre latent site, section 2.3.1-4).
  land_city            A-2: SA _land_city (P-2 gate W mass, from_transit) with the in_SC1001_W room at its structural
                       0; the whole toy state is compared (no ledger attached).
  land_city_full_room  the same with a room that holds the whole mass (frac = 1 exactly; rest = 0.0 in both runs).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND, SCENARIO = sys.argv[1], sys.argv[2]
ROOT = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else HERE.parents[2]
TESTS = ROOT / 'diagnostics' / 'sdmpc_n31_20260924' / 'tests'
for extra in (str(ROOT / 'vendor/NumSim-mine'), str(ROOT), str(TESTS)):
    if extra in sys.path:
        sys.path.remove(extra)
    sys.path.insert(0, extra)

from evaluation.controllers import sdmpc_tangent_runtime as rt  # noqa: E402

rt.install(ROOT, backend=BACKEND)
if BACKEND == 'forward':
    from evaluation.controllers import sdmpc_dual as ad  # noqa: E402
else:
    from evaluation.controllers import sdmpc_tangent_reverse as ad  # noqa: E402
from evaluation.controllers.sdmpc_tangent_worker import state_error  # noqa: E402  (not instrumented)

TINY_STEP = 2.0 ** -51
K8B_CONTAINERS = ('wout_direct_pending', 'wout_exit_counters', 'wout_class_store')


def dual(value):
    trace = ad.Trace([1.0]) if BACKEND == 'forward' else ad.Trace([1.0], track_stencils=False)
    return ad.Dual(value, {0: 1.0}, trace)


def primal(value):
    return value.value if isinstance(value, ad.Dual) else float(value)


def compare(a, b, path):
    try:
        return {'error': state_error(a, b, path), 'exception': None}
    except (ValueError, TypeError) as exc:
        return {'error': None, 'exception': f'{type(exc).__name__}: {exc}'[:400]}


def ok(cmp):
    return cmp['exception'] is None and cmp['error'] is not None and cmp['error'] <= 1e-9


def events(counters):
    return {k: primal(v) for k, v in (counters or {}).items() if k.endswith('_events') or k == 'update_steps'}


# ---------------------------------------------------------------- A-1: LOR direct row
class _NoLedger:
    """LOR reads captures_response and closes its coverage; emit_transfer calls transfer (no-op)."""
    captures_response = False

    def complete_constraint_coverage(self, *_args, **_kw):
        return None

    def transfer(self, *_args, **_kw):
        return None


def direct_row_run(room):
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import DelayedPort
    from evaluation.controllers.lane_offramp_runtime import LaneOfframpRuntime
    from evaluation.controllers import urban_flow_accounting as UFA
    import test_k8b_p4 as P4
    cfg, state, _meta = P4.make(True)
    spec = cfg.network.wout_exit_law[P4.LINK]
    t0, port_cap, store = 600, 20.0, 'OR_D_E_direct_storage'
    net = cfg.network
    net.urban_link_storage_veh[store] = port_cap
    net.movement_capacity_veh_h = 1400.0
    net.urban_stopline_storage_veh = {}
    net.urban_movements = {}
    port = DelayedPort(port_cap, 120.0, 60.0, [[119.9, 30.0, 1]], float(t0), interval_service=True)
    rows = {'10483': {'id': 'OR_D_E_direct', 'group': 'OR_D_E', 'branch': 'direct', 'connector': 10483,
                      'from_link': 2, 'to_link': 31, 'lanes': 1, 'storage_capacity_veh': port_cap, 'storage': store,
                      'direct': True, 'target': P4.LINK, 'local_upstream': False}}
    lor = LaneOfframpRuntime({'10483': port}, rows, None, {'10483': True, '31': True})
    state.urban_link_storage[store] = port_cap - port.stock
    state.urban_link_storage[P4.LINK] = room                    # W_out room: structural 0 (scalar) / +2**-51
    state.urban_arrival_buffer = {}
    state._control_area_ledger = _NoLedger()
    state.lane_offramp_runtime = lor
    lor.drain(state, None, cfg, t0, {})
    after_drain = {name: getattr(state, name, None) for name in K8B_CONTAINERS}
    import copy
    after_drain = copy.deepcopy(after_drain)
    d = max(1, int(math.ceil(float(spec['direct']['l_residence_km'])
                             / float(net.leg_ramp_split_wout_speed_kmh) / float(cfg.simulation.T_u_h))))
    for idx in range(t0, t0 + d + 1):
        UFA._wout_store_update(state, spec, P4.LINK, 0.0, idx)
    n = math.fsum(primal(x) for x in state.urban_storage_release_buffer.get(P4.LINK, {}).values())
    return state, after_drain, d, n


def direct_row():
    s_state, s_drain, d, n_s = direct_row_run(0.0)
    t_state, t_drain, _d, n_t = direct_row_run(dual(TINY_STEP))
    end_s = {name: getattr(s_state, name, None) for name in K8B_CONTAINERS}
    end_t = {name: getattr(t_state, name, None) for name in K8B_CONTAINERS}
    drain_cmp = compare(s_drain, t_drain, 'k8b')
    end_cmp = compare(end_s, end_t, 'k8b')
    s_full, t_full = dict(vars(s_state)), dict(vars(t_state))
    for st in (s_full, t_full):
        st.pop('lane_offramp_runtime', None)        # the DelayedPort objects: compared through the storages
    full = compare(s_full, t_full, 'state')
    cs = ((getattr(s_state, 'wout_exit_counters', None) or {}).get('SC1001_W_out'))
    ct = ((getattr(t_state, 'wout_exit_counters', None) or {}).get('SC1001_W_out'))
    pend = lambda dr: sorted(((dr.get('wout_direct_pending') or {}).get('SC1001_W_out') or {}).keys())  # noqa: E731
    out = {'scenario': 'direct_row', 'direct_steps': d, 'n_scalar': n_s, 'n_tangent': n_t,
           'after_drain': drain_cmp, 'end': end_cmp,
           'pend_keys_after_drain': [pend(s_drain), pend(t_drain)],
           'counters_scalar': {k: primal(v) for k, v in (cs or {}).items()},
           'counters_tangent': {k: primal(v) for k, v in (ct or {}).items()},
           'events_equal': cs is not None and ct is not None and events(cs) == events(ct),
           'full_state_report_only': full}
    out['parity'] = ok(drain_cmp) and ok(end_cmp) and out['events_equal']
    return out


# ---------------------------------------------------------------- A-2: SA _land_city
def land_city_run(room):
    import test_k8b_p2 as P2
    from evaluation.controllers import stopline_approach as SA
    from src.models import urban_queue_model as uqm
    cfg, st, raw = P2.city_cfg(1650)
    SA.city_arrival_prepare(st, cfg, raw)
    st.stopline_approach_state['city_arrival'] = {'pending': {}, 'gate_w': {},
                                                  'counters': {k: 0.0 for k in SA.CITY_COUNTER_KEYS}}
    step = 1651
    SA._context(st, cfg, step)
    receiver = cfg.network.stopline_approach['receiver']
    st.urban_link_storage[receiver] = room
    routing = uqm.approach_routing(cfg)
    city = cfg.network.stopline_city_arrival
    lw = 4.0
    by_member = {m: lw * city['beta_hat'][m] / city['beta_W_hat'] for m in cfg.network.stopline_approach['members']}
    SA._land_city(st, cfg, step, by_member, routing, 'city', True)
    return st, receiver


def land_city(full_room=False):
    room = 100.0 if full_room else 0.0
    s_st, receiver = land_city_run(room)
    t_st, _ = land_city_run(dual(room) if full_room else dual(TINY_STEP))
    full = compare(s_st, t_st, 'state')
    cs = s_st.stopline_approach_state['city_arrival']['counters']
    ct = t_st.stopline_approach_state['city_arrival']['counters']
    keys = lambda st, name: sorted((getattr(st, name).get(receiver) or {}).keys())  # noqa: E731
    out = {'scenario': 'land_city_full_room' if full_room else 'land_city', 'full_state': full,
           'arrival_keys': [keys(s_st, 'urban_arrival_buffer'), keys(t_st, 'urban_arrival_buffer')],
           'release_keys': [keys(s_st, 'urban_storage_release_buffer'), keys(t_st, 'urban_storage_release_buffer')],
           'counters_scalar': {k: primal(v) for k, v in cs.items()},
           'counters_tangent': {k: primal(v) for k, v in ct.items()},
           'events_equal': events(cs) == events(ct),
           'sa_counter_events_equal': events(s_st.stopline_approach_state['counters'])
           == events(t_st.stopline_approach_state['counters'])}
    out['parity'] = ok(full) and out['events_equal'] and out['sa_counter_events_equal']
    return out


def main():
    if SCENARIO == 'direct_row':
        out = direct_row()
    elif SCENARIO == 'land_city':
        out = land_city(False)
    elif SCENARIO == 'land_city_full_room':
        out = land_city(True)
    else:
        raise SystemExit('unknown scenario ' + SCENARIO)
    out.update(backend=BACKEND, root=str(ROOT))
    print(json.dumps(out, default=repr))


if __name__ == '__main__':
    main()
