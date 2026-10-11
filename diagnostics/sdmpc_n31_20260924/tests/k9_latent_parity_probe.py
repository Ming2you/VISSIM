"""K9-1 Z1 latent key-touch parity probe (K8_PREDECLARATION_AMENDMENT_19 r2 section 2.4 and 4.1 K9-1-0b
tests/test_k9_latent.py); run only as a fresh subprocess.

    python -B k9_latent_parity_probe.py <forward|reverse-v1> <scenario> [ROOT]

The tangent Finder of ROOT (default: this checkout) is installed before any model import, exactly as the AD worker
does, so LOR, UFA, UQM and the DelayedPort run instrumented.  Synthetic cfg / state only (no capture, rollout, adapter
run or VISSIM): the K8b-5 direct-row toy (tests/k8b5_parity_probe.py direct_row: connector 10483 -> SC1001_W_out, the
W_out room is the operand) with the LOR direct row of the code root.  Prints one JSON line.

  law_plus / law_minus      W_out exit law installed (P-4b direct class): the scalar witness with the room at its
                            structural 0.0 against the tangent run with a Dual room +2**-51 / -2**-51; the WHOLE
                            states (sdmpc_tangent_worker.state_error, not instrumented) after the drain and after the
                            direct mass matures; the release-buffer keys after the drain; the Z1 touch counts.
  nolaw_plus / nolaw_minus  the same without the exit law and with SC1001_W_out routed (the arrival buffer is booked
                            too; the due is uqm._link_delay_steps).
  due_law / due_nolaw       scalar only: the keys the touch books at room 0.0 against the keys the n > 0 branch books
                            at a small positive room (the F-2 form: the touched due = the skipped branch's due)."""
from __future__ import annotations

import copy
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

TINY = 2.0 ** -51
LINK = 'SC1001_W_out'


def dual(value):
    trace = ad.Trace([1.0]) if BACKEND == 'forward' else ad.Trace([1.0], track_stencils=False)
    return ad.Dual(value, {0: 1.0}, trace)


def primal(value):
    return value.value if isinstance(value, ad.Dual) else float(value)


class _NoLedger:
    captures_response = False

    def complete_constraint_coverage(self, *_args, **_kw):
        return None

    def transfer(self, *_args, **_kw):
        return None


def run(room, law):
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import DelayedPort
    from evaluation.controllers import lane_offramp_runtime as LORM
    from evaluation.controllers import urban_flow_accounting as UFA
    import test_k8b_p4 as P4
    cfg, state, _meta = P4.make(law)
    net = cfg.network
    t0, port_cap, store = 600, 20.0, 'OR_D_E_direct_storage'
    net.urban_link_storage_veh[store] = port_cap
    net.movement_capacity_veh_h = 1400.0
    net.urban_stopline_storage_veh = {}
    net.urban_movements = {}
    net.urban_avg_vehicle_length_m = 7.0                       # uqm._link_delay_steps (no-law due)
    net.urban_avg_speed_km_h = 30.0
    net.boundary_queue_max_veh = 50.0
    state.urban_link_speed_kph = {}
    port = DelayedPort(port_cap, 120.0, 60.0, [[119.9, 30.0, 1]], float(t0), interval_service=True)
    rows = {'10483': {'id': 'OR_D_E_direct', 'group': 'OR_D_E', 'branch': 'direct', 'connector': 10483,
                      'from_link': 2, 'to_link': 31, 'lanes': 1, 'storage_capacity_veh': port_cap, 'storage': store,
                      'direct': True, 'target': LINK, 'local_upstream': False}}
    lor = LORM.LaneOfframpRuntime({'10483': port}, rows, None, {'10483': True, '31': True})
    state.urban_link_storage[store] = port_cap - port.stock
    state.urban_link_storage[LINK] = room
    state.urban_arrival_buffer = {}
    state._control_area_ledger = _NoLedger()
    state.lane_offramp_runtime = lor
    routing = {} if law else {LINK: []}
    before = getattr(LORM, 'LATENT_TOUCH', {'events': 0})['events']
    lor.drain(state, None, cfg, t0, routing)
    touches = getattr(LORM, 'LATENT_TOUCH', {'events': 0})['events'] - before
    after = {'release': copy.deepcopy(state.urban_storage_release_buffer),
             'arrival': copy.deepcopy(state.urban_arrival_buffer)}
    if law:
        spec = net.wout_exit_law[LINK]
        d = max(1, int(math.ceil(float(spec['direct']['l_residence_km']) / float(net.leg_ramp_split_wout_speed_kmh)
                                 / float(cfg.simulation.T_u_h))))
        for idx in range(t0, t0 + d + 1):
            UFA._wout_store_update(state, spec, LINK, 0.0, idx)
    return state, after, touches


def cmp(a, b, path):
    try:
        return {'error': state_error(a, b, path), 'exception': None}
    except (ValueError, TypeError) as exc:
        return {'error': None, 'exception': f'{type(exc).__name__}: {exc}'[:400]}


def keys(after):
    return {name: {k: sorted(v.keys()) for k, v in table.items()} for name, table in after.items()}


def parity(law, sign):
    s_state, s_after, s_touch = run(0.0, law)
    t_state, t_after, t_touch = run(dual(sign * TINY), law)
    drain = cmp(s_after, t_after, 'buffers_after_drain')
    s_full, t_full = dict(vars(s_state)), dict(vars(t_state))
    for st in (s_full, t_full):
        st.pop('lane_offramp_runtime', None)
    full = cmp(s_full, t_full, 'state')
    out = {'law': law, 'sign': sign, 'touch_events': [s_touch, t_touch],
           'keys_after_drain': [keys(s_after), keys(t_after)], 'after_drain': drain, 'full_state': full}
    out['key_divergence_0'] = drain['exception'] is None and full['exception'] is None
    out['parity'] = (out['key_divergence_0'] and drain['error'] is not None and drain['error'] <= 1e-9
                     and full['error'] is not None and full['error'] <= 1e-9
                     and out['keys_after_drain'][0] == out['keys_after_drain'][1])
    return out


def due(law):
    z_state, z_after, z_touch = run(0.0, law)
    p_state, p_after, p_touch = run(1e-6, law)
    out = {'law': law, 'touch_events': [z_touch, p_touch], 'keys_touch': keys(z_after),
           'keys_branch': keys(p_after),
           'values_touch': {n: {k: {str(s): primal(x) for s, x in v.items()} for k, v in t.items()}
                            for n, t in z_after.items()}}
    out['same_keys'] = out['keys_touch'] == out['keys_branch']
    out['touch_values_zero'] = all(x == 0.0 for t in out['values_touch'].values() for v in t.values()
                                   for x in v.values())
    return out


def main():
    table = {'law_plus': lambda: parity(True, 1.0), 'law_minus': lambda: parity(True, -1.0),
             'nolaw_plus': lambda: parity(False, 1.0), 'nolaw_minus': lambda: parity(False, -1.0),
             'due_law': lambda: due(True), 'due_nolaw': lambda: due(False)}
    if SCENARIO not in table:
        raise SystemExit('unknown scenario ' + SCENARIO)
    out = table[SCENARIO]()
    out.update(scenario=SCENARIO, backend=BACKEND, root=str(ROOT))
    print(json.dumps(out, default=repr))


if __name__ == '__main__':
    main()
