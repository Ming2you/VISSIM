"""Read-only service/maturity probe; no proposal loading, endpoint, or optimizer.

An eligibility schedule is a reservation on existing stock, never extra stock.
The tiny ready() function specifies an interface; it is not a plant replacement.
"""
from __future__ import annotations
import copy
import hashlib
import inspect
import json
import math
import os
import pickle
import sys
import unittest
from unittest.mock import patch

from diagnostics.test_shared_service_pool import ROOT, inputs, local_args, TARGETS, local, uqm
from evaluation.controllers import urban_flow_accounting as urban
from evaluation.controllers import native_input_routes, native_input_prehead
from evaluation.controllers.control_area_objective import model_stock_values, integrate_residence


def digest(value):
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def ready(occupancy, pending, step):
    """Pure query matching global due<=step maturity, with explicit data QA."""
    if type(step) is not int or not math.isfinite(occupancy) or occupancy < 0:
        raise ValueError('invalid time/stock')
    if any(type(k) is not int or not math.isfinite(v) or v < 0 for k, v in pending.items()):
        raise ValueError('invalid pending schedule')
    moving = sum(v for k, v in pending.items() if k > step)
    if moving > occupancy + 1e-9:
        raise ValueError('pending must be a subset of physical stock')
    return max(0., occupancy - moving)


def inventory(state, cfg):
    from diagnostics.probe_model_area_integration import adapter
    return model_stock_values(state, cfg.network,
                              freeway_vehicle_counts=adapter._freeway_vehicle_count_by_link(state, cfg))


def drain_service(state, cfg, action, model, step):
    """Only actual canonical drain, with explicit current service bookkeeping.

    No arrivals, route travel, ordinary movement, FW, or other urban steps run.
    This isolates maturity from unrelated route advances/generation.
    """
    state.route_choice_corridor_state['last_step'] = step
    state.route_choice_corridor_state['service_limit_veh'] = {}
    state.route_choice_corridor_state['service_used_veh'] = {}
    native_input_routes.advance(state, cfg, step)
    native_input_prehead.advance(state, cfg, step)
    receipts = []
    def profile(frame, event, arg):
        if event == 'return' and frame.f_code is urban._receive_corridor.__code__:
            f = frame.f_locals
            receipts.append({'movement': f['movement'], 'vehicles': f['vehicles']})
    old = sys.getprofile(); sys.setprofile(profile)
    try:
        departures = urban._drain_offramp_storage_accounted(
            state, action, cfg, {m: model.specs[m] for m in TARGETS[:2]}, step, {})
    finally:
        sys.setprofile(old)
    # Close the native subset's tag-only step contract; no route/stock generation.
    native_input_prehead.finish_step(state, action, cfg, step)
    state._control_area_ledger.assert_stocks(inventory(state, cfg))
    return departures, receipts


def original_local_trace(cfg, state, action, model):
    args, kwargs = local_args(cfg, state, action, model)
    lines, first = inspect.getsourcelines(local.rollout_local_tts_ramp_aware)
    capture = {first + i for i, s in enumerate(lines) if s.strip() == 'released_total += actual'}
    code = local.rollout_local_tts_ramp_aware.__code__
    rows, final = [], {}
    def trace(frame, event, arg):
        if frame.f_code is not code:
            return None
        if event == 'line' and frame.f_lineno in capture and frame.f_locals.get('m') in TARGETS:
            rows.append({'movement': frame.f_locals['m'], 'vehicles': frame.f_locals['actual']})
        if event == 'return':
            final.update({k: copy.deepcopy(frame.f_locals[k]) for k in ('occ', 'q', 'res')})
        return trace
    old = sys.gettrace(); sys.settrace(trace)
    try:
        cost = local.rollout_local_tts_ramp_aware(*args, **kwargs)
    finally:
        sys.settrace(old)
    return {'receipts': rows, 'cost_veh_h': cost, 'end_stocks': final}


def produce():
    watched = list((ROOT / 'evaluation/controllers').glob('*.py')) + [
        ROOT / 'vendor/NumSim-mine/src/models/urban_queue_model.py',
        ROOT / 'vendor/NumSim-mine/src/controllers/local_signal_plant.py',
        ROOT / 'vendor/NumSim-mine/src/controllers/wu_faithful_follower.py',
        ROOT / 'diagnostics/area_candidate_configs/n7_area_beta0.json',
    ]
    run = ROOT / 'evaluation/runs/codex_area_sources_beta0_s13_20260910'
    for name in ('state_000900.json', 'action_000750.json', 'action_000900.json'):
        watched.append(run / ('decisions_' + run.name) / name)
    pins = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
    with patch.dict(os.environ, {'RW_OFFSET_WRITER': 'experiment'}):
        cfg, state, action, demand, model, raw, detectors = inputs()
    initial = digest((cfg, state, action, demand, raw, detectors))
    k = uqm._urban_step_index(state, cfg)
    delay = uqm._inflow_delay_steps(cfg)
    off = 'OR_F_W'; storage = cfg.network.off_ramp_storage_link[off]
    occupied = cfg.network.urban_link_storage_veh[storage] - state.urban_link_storage[storage]
    specs = {m: model.specs[m] for m in TARGETS[:2]}
    actual = {'time_sec': state.time_sec, 'step': k, 'Tu_sec': cfg.simulation.T_u_sec,
              'Tf_sec': cfg.simulation.T_f_sec, 'K_fu': cfg.simulation.K_fu,
              'inflow_delay_steps': delay, 'offramps': {}, 'service_inputs': {}}
    for m in TARGETS[:2]:
        sp = model.specs[m]
        rate = uqm._movement_capacity_flow(action, cfg, m, sp)
        assert rate == model.cap_flow_of[m]
        receiver = str(sp['receiving_link'])
        actual['service_inputs'][m] = {
            'turn_beta': model.beta_of[m], 'actual_and_local_capacity_veh_h': rate,
            'actual_and_local_green_fraction': uqm._phase_green_fraction(action, cfg, sp, urban_step_index=k),
            'receiver': receiver, 'actual_and_local_initial_receiver_space_veh': uqm._effective_available_space(state, cfg, receiver),
            'actual_and_local_dt_h': cfg.simulation.T_u_h}
    for name in cfg.network.off_ramps:
        s = cfg.network.off_ramp_storage_link[name]
        n = cfg.network.urban_link_storage_veh[s] - state.urban_link_storage[s]
        actual['offramps'][name] = {'storage': s, 'stock_veh': n,
            'pending': copy.deepcopy(state.offramp_transit_buffer.get(s, {})),
            'eligible_veh': ready(n, state.offramp_transit_buffer.get(s, {}), k)}
    rows = []
    for label, at in [('actual', None), ('past', k - 1), ('due_now', k), ('due_next', k + 1), ('due_delay', k + delay)]:
        st = state.copy()
        if at is not None:
            st.offramp_transit_buffer[storage] = {at: occupied}
        before = inventory(st, cfg)
        pending0 = copy.deepcopy(st.offramp_transit_buffer.get(storage, {}))
        eligible = ready(occupied, pending0, k)
        local_trace = original_local_trace(cfg, st, action, model)
        ttt0 = st._control_area_ledger.ttt_veh_h
        integrate_residence(st, cfg, ['storage:' + storage], cfg.simulation.T_u_h)
        residence = st._control_area_ledger.ttt_veh_h - ttt0
        dep, receipts = drain_service(st, cfg, action, model, k)
        after = inventory(st, cfg)
        released = sum(r['vehicles'] for r in receipts if r['movement'] == TARGETS[0])
        assert released <= model.beta_of[TARGETS[0]] * eligible + 1e-9
        assert abs(sum(before.values()) - sum(after.values())) < 1e-7
        assert abs(before['storage:' + storage] - after['storage:' + storage] - released) < 1e-9
        assert abs(residence - occupied * cfg.simulation.T_u_h) < 1e-9
        rows.append({'case': label, 'pending_before': pending0,
                     'stock_before_veh': occupied, 'eligible_before_veh': eligible,
                     'global_receipts': receipts, 'source_departures': dep,
                     'pending_after': st.offramp_transit_buffer.get(storage, {}),
                     'storage_after_veh': after['storage:' + storage],
                     'total_stock_residual_veh': sum(after.values()) - sum(before.values()),
                     'residence_before_service_veh_h': residence,
                     'canonical_local_without_ready': local_trace})
    # Sequential two service steps: due-next switches source priority at exact boundary.
    sequential = state.copy(); sequential.offramp_transit_buffer[storage] = {k + 1: occupied}
    boundary = []
    for step in (k, k + 1):
        cap = cfg.network.urban_link_storage_veh[storage]
        n = cap - sequential.urban_link_storage[storage]
        eligible = ready(n, sequential.offramp_transit_buffer.get(storage, {}), step)
        _, receipts = drain_service(sequential, cfg, action, model, step)
        boundary.append({'step': step, 'start_sec': step * cfg.simulation.T_u_sec,
                         'eligible_veh': eligible, 'receipts': receipts})
    # Exact existing signal-only scheduling helper: stock grows once, alias once.
    # This is an isolated externally supplied 1 vehicle admission, not FW withdrawal.
    scheduled = state.copy(); scheduled._control_area_ledger = None
    schedule = getattr(uqm, '_offramp_landing_orig_schedule')
    n0 = cfg.network.urban_link_storage_veh[storage] - scheduled.urban_link_storage[storage]
    accepted, rejected = schedule(scheduled, cfg, off, 1., k + cfg.simulation.K_fu)
    n1 = cfg.network.urban_link_storage_veh[storage] - scheduled.urban_link_storage[storage]
    due = k + cfg.simulation.K_fu + delay
    assert accepted == 1. and rejected == 0. and abs(n1 - n0 - accepted) < 1e-9
    assert scheduled.offramp_transit_buffer[storage][due] == accepted
    schedule_evidence = {'schedule_callable': schedule.__module__ + '.' + schedule.__name__,
        'external_test_admission_veh': accepted, 'stock_delta_veh': n1 - n0,
        'admission_step': k + cfg.simulation.K_fu, 'due_step': due,
        'admission_sec': (k + cfg.simulation.K_fu) * cfg.simulation.T_u_sec,
        'eligible_sec': due * cfg.simulation.T_u_sec,
        'existing_local_first_positive_inflow_eligible_sec': (k + 1) * cfg.simulation.T_u_sec}
    # Existing freeway local-landing path has a distinct step convention.
    # Trace one canonical advance, not a freeway rollout or candidate search.
    from evaluation.controllers.link_predictor import LocalLandingState
    from src.controllers.priced_wu_link_controller import LinkAgentWuFollower
    agent = LinkAgentWuFollower(cfg)
    land_state = state.copy(); land_state.offramp_transit_buffer[storage] = {k + 1: occupied}
    fw_link = cfg.network.off_ramp_from_freeway[off]
    landing = LocalLandingState(agent, agent._local_freeway_models[fw_link], land_state)
    landing_rows = []; arrived_original = LocalLandingState.arrived
    def trace_arrived(self, link):
        value = arrived_original(self, link)
        if link == storage:
            landing_rows.append({'step': self.step, 'stock_veh': self.stock[link], 'eligible_veh': value})
        return value
    eligible_initial = landing.arrived(storage)
    with patch.object(LocalLandingState, 'arrived', trace_arrived):
        landing.advance(action, dict(state.ramp_queue), cfg.simulation.T_u_h)
    assert eligible_initial == 0. and landing_rows[0]['step'] == k + 1
    assert landing_rows[0]['eligible_veh'] == occupied
    landing_evidence = {'scope': 'one canonical LocalLandingState.advance(Tu), not local/global full horizon equivalence',
        'start_step': k, 'pending_due_step': k + 1, 'eligible_before_advance_veh': eligible_initial,
        'queries_during_first_advance': landing_rows, 'end_step': landing.step,
        'stock_ledger_max_abs_residual_veh': landing.ledger['max_abs_residual_veh']}
    assert digest((cfg, state, action, demand, raw, detectors)) == initial
    changes = [str(p.relative_to(ROOT)) for p in watched if hashlib.sha256(p.read_bytes()).hexdigest() != pins[str(p.relative_to(ROOT))]]
    assert not changes
    return {'schema': 'offramp-ready-contract-review/v1', 'scope': 'canonical service-only and alias schedule; no full urban interval/endpoint/optimizer/VISSIM',
            'source_sha256': pins, 'source_changes': changes, 'input_pickle_unchanged': True,
            'actual900': actual, 'cases': rows, 'sequential_boundary': boundary,
            'new_admission_timing': schedule_evidence,
            'existing_freeway_local_clock': landing_evidence,
            'limitations': ['Original local has no shared-pool repair; compare eligibility separately from total service.',
                'Only two OR movement drain services run; no ordinary W source or surrounding travel/generation.',
                'Residence-before-service is an accounting probe, not the production end-step quadrature.',
                'Initial observed OR stocks have no age seed; all-ready at 900 is current model semantics, not observed readiness.',
                'Frozen total-group off flow is not an accepted signal-only arrival profile.']}


class ReadyTests(unittest.TestCase):
    def test_boundary_and_nonmutation(self):
        p = {179: 2., 180: 3., 181: 5.}; before = dict(p)
        self.assertEqual(ready(10., p, 180), 5.)
        self.assertEqual(ready(10., p, 181), 10.)
        self.assertEqual(p, before)

    def test_invalid_subset_and_timestamp(self):
        for pending in ({181: 11.}, {181.5: 1.}, {181: float('nan')}, {181: -1.}):
            with self.assertRaises(ValueError): ready(10., pending, 180)

    def test_reservation_is_not_stock(self):
        physical = 10.; pending = {181: 10.}
        self.assertEqual(ready(physical, pending, 180), 0.)
        self.assertEqual(physical * 5 / 3600, 10 * 5 / 3600)
        eligible = ready(physical, pending, 181)
        accepted = min(eligible, .86); after = physical - accepted
        self.assertAlmostEqual(after + accepted, physical)
        self.assertEqual(ready(after, pending, 181), after)

    def test_actual900_and_canonical_service(self):
        self.result = produce()
        rows = {r['case']: r for r in self.result['cases']}
        self.assertEqual(rows['due_next']['eligible_before_veh'], 0.)
        self.assertEqual(rows['due_now']['eligible_before_veh'], 10.)
        self.assertTrue(any(r['movement'] == TARGETS[0] and r['vehicles'] > 0
                            for r in rows['due_next']['canonical_local_without_ready']['receipts']))


if __name__ == '__main__':
    result = produce()
    path = ROOT / 'diagnostics/offramp_ready_contract_review.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('actual900', 'sequential_boundary', 'new_admission_timing', 'existing_freeway_local_clock', 'source_changes')}, indent=2))
