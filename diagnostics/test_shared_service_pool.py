"""Canonical shared-service tests. Actual imports only; no production writes.

Only bounded local/service windows and tiny local candidate sets are permitted;
no coupled endpoint, full optimizer or VISSIM execution.
"""
from __future__ import annotations
import copy
from contextlib import contextmanager
import hashlib
import json
import os
import pickle
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

from diagnostics.probe_model_area_integration import ROOT, adapter, build_projected
from src.controllers import local_signal_plant as local, wu_faithful_follower as follower
from src.controllers.priced_wu_link_controller import LinkAgentWuFollower
from src.models import urban_queue_model as uqm

SOURCE_PATHS = tuple(ROOT / 'evaluation/controllers' / name for name in (
    'local_signal_service.py', 'route_choice_corridor.py', 'runtime_setup.py'))
TARGETS = ('SC1004_offW_to_E_SC1005', 'SC1004_offE_to_E_SC1005', 'SC1004_W_to_E_SC1005')


@contextmanager
def installed():
    from evaluation.controllers import local_signal_service, route_choice_corridor, runtime_setup
    from contextlib import ExitStack
    with ExitStack() as stack:
        for module in (local, follower):
            stack.enter_context(patch.object(module, 'rollout_local_tts_ramp_aware', module.rollout_local_tts_ramp_aware))
        for name in ('_phase_refine_context', '_phase_refine_signal_setup', '_phase_local_cost_phased'):
            stack.enter_context(patch.object(LinkAgentWuFollower, name, getattr(LinkAgentWuFollower, name)))
        stack.enter_context(patch.object(LinkAgentWuFollower, 'solve', LinkAgentWuFollower.solve))
        for name in ('_solve_urban_agent_local', '_solve_offset_local_ramp'):
            stack.enter_context(patch.object(follower.WuFaithfulFollower, name, getattr(follower.WuFaithfulFollower, name)))
        yield local_signal_service, route_choice_corridor, runtime_setup


def inputs():
    from diagnostics.shared_service_fixtures import input_path
    config = ROOT / 'diagnostics/area_candidate_configs/n7_area_beta0.json'
    cfg, state, detectors, tuning, raw, mapping, metadata = build_projected(
        config, input_path('state_000900.json'), input_path('action_000750.json'), fixture_inputs=False)
    _, Demand, Control, _, _, _ = adapter.repo_imports(ROOT / 'vendor/NumSim-mine')
    action = adapter.control_from_json(input_path('action_000900.json'), cfg, Control)
    calibration = adapter.load_optional_json(str(ROOT / 'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
    calibration = adapter.deep_update(dict(calibration), tuning.get('calibration_override', {}))
    demand = adapter.demand_from_state(raw, cfg, Demand, 1, calibration, detectors)[0]
    specs = uqm.movement_specs(cfg)
    phases = {s: {p: [] for p in ('p1', 'p2', 'p3', 'p4')} for s in cfg.network.signals}
    for m, spec in specs.items():
        if spec['signal'] in phases:
            phases[spec['signal']][spec['phase'].rsplit('_', 1)[-1]].append(m)
    model = local.build_local_model(cfg, 'SC1004', specs, phases)
    return cfg, state, action, demand, model, raw, detectors


def local_args(cfg, state, action, model, *, substeps=1, fraction=None, space=None):
    q0 = {m: state.urban_movement_queue.get(m, 0.) for m in model.movements}
    occ = {off: cfg.network.urban_link_storage_veh[cfg.network.off_ramp_storage_link[off]] - state.urban_link_storage[cfg.network.off_ramp_storage_link[off]] for off in model.offramp_movements}
    s_eff = {model.receiving_of[m]: uqm._effective_available_space(state, cfg, model.receiving_of[m]) for m in model.movements if model.receiving_of[m]}
    if space is not None:
        s_eff[model.receiving_of[TARGETS[0]]] = space
    start = uqm._urban_step_index(state, cfg)
    gf = {m: [uqm._phase_green_fraction(action, cfg, model.specs[m], urban_step_index=start + k) for k in range(substeps)] for m in model.movements}
    if fraction is not None:
        gf = {m: [fraction] * substeps for m in model.movements}
    args = (model, q0, {}, s_eff, {}, occ,
            {r: state.ramp_queue.get(r, 0.) for r in model.onramp_movements}, {}, {}, 0.,
            {p: action.green_times['SC1004_' + p] for p in ('p1', 'p2', 'p3', 'p4')}, substeps, cfg.simulation.T_u_h)
    kwargs = {'arr_by_substep': {}, 'gf_by_substep': gf}
    pool = sys.modules.get('evaluation.controllers.local_signal_service')
    if pool is not None and pool.view(cfg):
        kwargs.update(ready_seed=pool.make_ready_seed(state, model), green_profile_start_step=start)
    return args, kwargs


def accepted_trace(pool, call):
    records = []
    def profile(frame, event, arg):
        if frame.f_code is pool.accepted.__code__ and event == 'return':
            parent = frame.f_back.f_locals
            records.append((parent.get('m', parent.get('movement')), frame.f_locals['vehicles']))
    previous = sys.getprofile(); sys.setprofile(profile)
    try:
        result = call()
    finally:
        sys.setprofile(previous)
    return result, records


def one_actual_green(cfg, state, action, demand, pool):
    """One original local green candidate; also used by a fresh installed worker."""
    from dataclasses import asdict
    agent = LinkAgentWuFollower(cfg)
    coupling = agent._wu._coupling(state, action, demand)
    arrivals = agent._per_movement_arrivals('SC1004', state, action, demand)
    space = agent._frozen_s_eff(state)
    seen = []
    def profile(frame, event, arg):
        if event == 'return' and frame.f_code is pool._ready_copy.__code__:
            seen.append(asdict(frame.f_locals['seed']))
    old = sys.getprofile(); sys.setprofile(profile)
    try:
        result = agent._solve_urban_agent_local('SC1004', state, coupling, arrivals, space, {}, {},
            action, demand=demand, candidates_override=[action.green_times['SC1004_p1']])
    finally:
        sys.setprofile(old)
    return {'result': result, 'seeds': seen, 'context_reset': pool._READY_CONTEXT.get() is None}


class PoolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = {}
        source_paths = list(SOURCE_PATHS)
        source_paths += [ROOT / 'vendor/NumSim-mine/src/controllers' / p for p in (
            'local_signal_plant.py', 'wu_faithful_follower.py', 'priced_wu_link_controller.py')]
        cls.source_pins = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
        with patch.dict(os.environ, {'RW_OFFSET_WRITER': 'experiment'}):
            cls.fixture = inputs()

    @classmethod
    def tearDownClass(cls):
        assert all(hashlib.sha256(p.read_bytes()).hexdigest() == h for p, h in cls.source_pins.items())

    def setUp(self):
        self.cfg, self.state, self.action, self.demand, self.model, self.raw, self.detectors = copy.deepcopy(self.fixture)
        self.context = installed()
        self.pool, self.route, self.runtime = self.context.__enter__()
        self.addCleanup(self.context.__exit__, None, None, None)

    def enable(self):
        self.pool.configure(self.cfg, {'urban': {'shared_local_service_pool': True}})

    def test_off_dispatch_is_exact_and_does_not_install(self):
        original = local.rollout_local_tts_ramp_aware
        args, kw = local_args(self.cfg, self.state, self.action, self.model, substeps=2)
        before = pickle.dumps((args, kw))
        expected = original(*args, **kw)
        self.assertEqual(self.pool.configure(self.cfg, {}), {})
        self.assertIs(local.rollout_local_tts_ramp_aware, original)
        self.enable()
        self.pool.configure(self.cfg, {'urban': {'shared_local_service_pool': False}})
        self.assertEqual(local.rollout_local_tts_ramp_aware(*args, **kw), expected)
        self.assertEqual(before, pickle.dumps((args, kw)))

    def test_actual_900_global_and_local_have_same_shared_receipt(self):
        original = self.state.copy()
        uqm.urban_substep(original, self.action, self.demand, self.cfg,
                         urban_step_index=uqm._urban_step_index(original, self.cfg), ramp_release_veh_h=self.action.ramp_metering)
        self.enable()
        initial = pickle.dumps((self.cfg, self.state, self.action, self.demand))
        replica = self.state.copy()
        _, global_receipts = accepted_trace(self.pool, lambda: uqm.urban_substep(
            replica, self.action, self.demand, self.cfg,
            urban_step_index=uqm._urban_step_index(replica, self.cfg), ramp_release_veh_h=self.action.ramp_metering))
        args, kw = local_args(self.cfg, self.state, self.action, self.model)
        _, local_receipts = accepted_trace(self.pool, lambda: local.rollout_local_tts_ramp_aware(*args, **kw))
        self.assertEqual(global_receipts, local_receipts)
        self.assertEqual([m for m, n in local_receipts if n], [TARGETS[0]])
        self.assertAlmostEqual(sum(n for m, n in local_receipts), .8605442176870748)
        self.assertEqual(initial, pickle.dumps((self.cfg, self.state, self.action, self.demand)))
        self.assertEqual(pickle.dumps(original), pickle.dumps(replica))

    def test_partial_green_receiver_and_each_substep_budget(self):
        self.enable()
        for gf in (0., .2, .6, 1.):
            for space in (.1, .7, 100.):
                args, kw = local_args(self.cfg, self.state, self.action, self.model, substeps=2, fraction=gf, space=space)
                _, receipts = accepted_trace(self.pool, lambda: local.rollout_local_tts_ramp_aware(*args, **kw))
                budget = self.model.cap_flow_of[TARGETS[0]] * self.cfg.simulation.T_u_h * gf
                self.assertAlmostEqual(sum(n for m, n in receipts), 2 * min(budget, space))
                # The frozen external space is renewed each substep; within a
                # substep all sources share the same decrementing receiver.
                self.assertTrue(all(m == TARGETS[0] for m, n in receipts if n))

    def test_global_off_service_partial_clock_and_receiver_match_local(self):
        from evaluation.controllers import urban_flow_accounting as urban
        self.enable()
        step = uqm._urban_step_index(self.state, self.cfg)
        receiver = self.model.receiving_of[TARGETS[0]]
        offsets = {}
        for offset in range(151):
            candidate = self.action.copy(); candidate.offsets['SC1004'] = float(offset)
            gf = uqm._phase_green_fraction(candidate, self.cfg, self.model.specs[TARGETS[0]], urban_step_index=step)
            offsets.setdefault(gf, offset)
        for fraction in (0., .2, .6, 1.):
            self.assertIn(fraction, offsets)
            candidate = self.action.copy(); candidate.offsets['SC1004'] = float(offsets[fraction])
            for available in (.1, .7, 100.):
                state = self.state.copy(); state._control_area_ledger = None
                # Synthetic receiving operand only. Keep its independent route
                # cohort stock exact; no fake capacity or external generation.
                previous = state.urban_link_storage[receiver]
                state.urban_link_storage[receiver] = available
                state.route_choice_corridor_state['cohorts'].append(self.route._cohort(
                    receiver, 'prechoice', None, previous - available, step + 10000, source='test_existing_stock'))
                state.route_choice_corridor_state['last_step'] = step
                state.route_choice_corridor_state['service_limit_veh'] = {}
                state.route_choice_corridor_state['service_used_veh'] = {}
                from evaluation.controllers import native_input_routes, native_input_prehead
                native_input_routes.advance(state, self.cfg, step)
                native_input_prehead.advance(state, self.cfg, step)
                self.route._check(state, self.route._movement_spec(self.cfg, TARGETS[0]))
                # Canonical global off-service phase, after begin, with the
                # same physical source availability, green and receiver.
                _, global_rows = accepted_trace(self.pool, lambda: urban._drain_offramp_storage_accounted(
                    state, candidate, self.cfg, {m: self.model.specs[m] for m in TARGETS}, step, {}))
                args, kw = local_args(self.cfg, self.state, candidate, self.model, space=available)
                _, local_rows = accepted_trace(self.pool, lambda: local.rollout_local_tts_ramp_aware(*args, **kw))
                self.assertEqual(global_rows, local_rows)

    def test_requests_do_not_consume_and_receiving_rejection_preserves_budget(self):
        limits, used = {}, {}
        self.pool.register_limit(limits, 'g', 3600., 1 / 3600., .5)
        self.assertEqual(self.pool.limit_one(9., 'g', limits, used), .5)
        self.assertEqual(self.pool.limit_one(9., 'g', limits, used), .5)
        self.pool.accepted(.1, 'g', limits, used)
        self.assertEqual(self.pool.limit_one(9., 'g', limits, used), .4)
        out = self.pool.limit_batch({'a': 1., 'b': 1.}, {'a': 'g', 'b': 'g'}, limits, used, self.model.receiving_space_rule)
        self.assertAlmostEqual(sum(out.values()), .4)
        self.assertEqual(used, {'g': .1})
        with self.assertRaises(ValueError):
            self.pool.accepted(.5, 'g', limits, used)
        with self.assertRaises(ValueError):
            self.pool.register_limit(limits, 'g', 3600., 1 / 3600., .6)

    def test_low_off_stocks_release_remaining_budget_to_ordinary_queue(self):
        self.enable()
        state = self.state.copy()
        for m in TARGETS[:2]:
            off = self.model.specs[m]['off_ramp']
            storage = self.cfg.network.off_ramp_storage_link[off]
            state.urban_link_storage[storage] = self.cfg.network.urban_link_storage_veh[storage] - .1
        args, kw = local_args(self.cfg, state, self.action, self.model)
        _, rows = accepted_trace(self.pool, lambda: local.rollout_local_tts_ramp_aware(*args, **kw))
        self.assertEqual([m for m, n in rows], list(TARGETS))
        self.assertAlmostEqual(rows[0][1], .06)
        self.assertAlmostEqual(rows[1][1], .06)
        self.assertAlmostEqual(rows[2][1], .8605442176870748 - .12)

    def test_candidate_copy_repeat_and_aliases(self):
        self.enable()
        args, kw = local_args(self.cfg, self.state, self.action, self.model, substeps=3)
        before = pickle.dumps((args, kw))
        a = local.rollout_local_tts_ramp_aware(*args, **kw)
        dark = copy.deepcopy(kw)
        dark['gf_by_substep'] = {m: [0.] * 3 for m in self.model.movements}
        local.rollout_local_tts_ramp_aware(*args, **dark)
        self.assertEqual(a, follower.rollout_local_tts_ramp_aware(*copy.deepcopy(args), **copy.deepcopy(kw)))
        self.assertEqual(before, pickle.dumps((args, kw)))
        self.pool.install(self.cfg)
        self.assertEqual(a, local.rollout_local_tts_ramp_aware(*args, **kw))

    def test_stale_or_partial_group_is_rejected(self):
        self.enable()
        args, kw = local_args(self.cfg, self.state, self.action, self.model)
        self.model.cap_flow_of[TARGETS[0]] += 1.
        with self.assertRaises(ValueError):
            local.rollout_local_tts_ramp_aware(*args, **kw)
        self.model.cap_flow_of[TARGETS[0]] -= 1.
        self.model.movements.remove(TARGETS[0])
        with self.assertRaises(ValueError):
            local.rollout_local_tts_ramp_aware(*args, **kw)

    def test_physical_profile_is_mandatory_when_enabled(self):
        self.enable()
        args, kw = local_args(self.cfg, self.state, self.action, self.model)
        profiles = kw['gf_by_substep']
        cases = [None, {}, {m: v for m, v in profiles.items() if m != TARGETS[0]}]
        cases += [{**profiles, TARGETS[0]: invalid} for invalid in
                  ([], [1., 1.], [float('nan')], [-.1], [1.1])]
        for case in cases:
            with self.subTest(profile=case), self.assertRaises(ValueError):
                local.rollout_local_tts_ramp_aware(*args, **{**kw, 'gf_by_substep': case})

    def test_off_configuration_removes_only_owned_view(self):
        self.enable()
        self.pool.configure(self.cfg, {})
        self.assertIsNone(self.pool.view(self.cfg))
        self.enable()
        self.pool.configure(self.cfg, {'urban': {'shared_local_service_pool': False}})
        self.assertIsNone(self.pool.view(self.cfg))
        self.cfg.network.local_service_pool = {'schema': 'foreign'}
        with self.assertRaises(ValueError):
            self.pool.configure(self.cfg, {'urban': {'shared_local_service_pool': False}})

    def test_calibrated_resource_requires_pool_in_main_and_worker(self):
        spec = self.cfg.network.route_choice_corridor
        first = spec.get('corridors', [spec])[0]
        first['calibrated_service_resources'] = {'10634': {}}
        for call in (lambda: self.pool.configure(self.cfg, {}), lambda: self.pool.install(self.cfg)):
            with self.assertRaisesRegex(ValueError, 'Calibrated shared resource'):
                call()
        self.enable()
        self.assertIsNotNone(self.pool.view(self.cfg))
        with self.assertRaises(ValueError): self.pool.configure(self.cfg, {'urban': {'shared_local_service_pool': False}})

    def test_refinement_rebuilds_for_changed_stock_and_frozen_flow_cache(self):
        self.enable()
        agent = LinkAgentWuFollower(self.cfg); agent.phase_price_local_cost_model = 'phased'
        ctx = agent._phase_refine_context(self.state, self.action, self.demand); ctx['substeps'] = 1
        first = agent._phase_refine_signal_setup('SC1004', self.state, ctx)
        other = self.state.copy(); off = self.model.specs[TARGETS[0]]['off_ramp']
        storage = self.cfg.network.off_ramp_storage_link[off]
        other.urban_link_storage[storage] += 1.
        newer = agent._phase_refine_context(other, self.action, self.demand); newer['substeps'] = 1
        second = agent._phase_refine_signal_setup('SC1004', other, newer)
        self.assertIsNot(ctx, newer)
        self.assertEqual(second['off_occ'][off], first['off_occ'][off] - 1.)
        agent._wu._has_last_offramp_flow = True
        agent._wu._last_offramp_flow = {**agent._wu._last_offramp_flow, off: 123.}
        final_ctx = agent._phase_refine_context(other, self.action, self.demand); final_ctx['substeps'] = 1
        final = agent._phase_refine_signal_setup('SC1004', other, final_ctx)
        self.assertIsNot(final_ctx, newer)
        self.assertEqual(final['off_inflow'][off], 123.)

    def test_refinement_uses_identical_ramp_rollout_and_current_clock(self):
        self.enable()
        agent = LinkAgentWuFollower(self.cfg)
        agent.phase_price_local_cost_model = 'phased'
        before = pickle.dumps((self.cfg, self.state, self.action, self.demand))
        ctx = agent._phase_refine_context(self.state, self.action, self.demand)
        ctx['substeps'] = 1  # Focused single urban step, never a price endpoint.
        setup = agent._phase_refine_signal_setup('SC1004', self.state, ctx)
        self.assertTrue(setup['shared_ramp_service'])
        self.assertIs(setup, agent._phase_refine_signal_setup('SC1004', self.state, ctx))
        phases = {p: self.action.green_times['SC1004_' + p] for p in ('p1', 'p2', 'p3', 'p4')}
        actual, receipts = accepted_trace(self.pool, lambda: agent._phase_local_cost_phased('SC1004', phases, setup, ctx))
        gf = agent._offset_green_fractions_vec('SC1004', phases, self.action.offsets['SC1004'], 1, ctx['start_idx'])
        for m in TARGETS:
            self.assertEqual(gf[m], [uqm._phase_green_fraction(self.action, self.cfg, self.cfg.network.urban_movements[m], urban_step_index=ctx['start_idx'])])
        expected = local.rollout_local_tts_ramp_aware(
            setup['model'], setup['q0'], setup['arr_mv'], setup['s_eff0'], setup['off_inflow'],
            setup['off_occ'], setup['ramp_q'], setup['drain'], setup['congestion'],
            agent.ramp_metering_weight, phases, 1, ctx['dt_h'], arr_by_substep=setup['arr'], gf_by_substep=gf,
            ready_seed=setup['ready_seed'], green_profile_start_step=ctx['start_idx'])
        self.assertEqual(actual, expected)
        self.assertAlmostEqual(sum(n for _, n in receipts), .8605442176870748)
        agent.signal_phase_price = {'SC1004': {'p1': 0., 'p2': 0., 'p3': 1., 'p4': 0.}}
        agent.signal_phase_price_ref = {'SC1004': phases}
        action = self.action.copy()
        with patch.object(agent, 'phase_shape_local_cost', side_effect=AssertionError('legacy ramp proxy reached')):
            agent.apply_phase_price_refinement(action, self.state, self.demand)
        self.assertEqual(action.diagnostics['wu_phase_price_local_cost_phased_signals'], 1.)
        self.assertEqual(before, pickle.dumps((self.cfg, self.state, self.action, self.demand)))

    def test_refinement_off_exact_and_enabled_missing_context_fails(self):
        agent = LinkAgentWuFollower(self.cfg)
        self.assertIsNone(agent._phase_refine_context(self.state, self.action, self.demand))
        self.enable()
        with self.assertRaises(ValueError):
            agent._phase_refine_context(self.state, self.action, self.demand)
        delattr(self.cfg.network, 'local_service_pool')
        self.assertIsNone(agent._phase_refine_context(self.state, self.action, self.demand))

    def test_ready_due_boundary_matches_canonical_global_service(self):
        from diagnostics.offramp_ready_contract_review import drain_service
        self.enable()
        state = self.state.copy(); step = uqm._urban_step_index(state, self.cfg)
        off = self.model.specs[TARGETS[0]]['off_ramp']
        storage = self.cfg.network.off_ramp_storage_link[off]
        state.offramp_transit_buffer[storage] = {step + 1: 10.}
        args, kw = local_args(self.cfg, state, self.action, self.model, substeps=2)
        args = list(args); args[1] = {m: 0. for m in args[1]}  # Only OR service, matched global scope.
        trace = []; kw['ready_trace'] = trace
        before = pickle.dumps((state, args, kw['ready_seed']))
        _, local_rows = accepted_trace(self.pool, lambda: local.rollout_local_tts_ramp_aware(*args, **kw))
        global_rows = []
        candidate = state.copy()
        for at in (step, step + 1):
            _, rows = drain_service(candidate, self.cfg, self.action, self.model, at)
            global_rows.extend((r['movement'], r['vehicles']) for r in rows)
        self.assertEqual(local_rows, global_rows)
        self.assertEqual([m for m, n in local_rows], [TARGETS[1], TARGETS[0]])
        self.assertEqual(trace[0]['eligible_veh'][off], 0.)
        self.assertEqual(trace[1]['eligible_veh'][off], 10.)
        self.assertEqual(before, pickle.dumps((state, args, kw['ready_seed'])))

    def test_pending_retains_all_physical_residence_stock(self):
        self.enable(); state = self.state.copy(); step = uqm._urban_step_index(state, self.cfg)
        for off in self.model.offramp_movements:
            storage = self.cfg.network.off_ramp_storage_link[off]
            stock = self.cfg.network.urban_link_storage_veh[storage] - state.urban_link_storage[storage]
            state.offramp_transit_buffer[storage] = {step + 3: stock}
        args, kw = local_args(self.cfg, state, self.action, self.model, substeps=2, fraction=0.)
        args = list(args); args[1] = {m: 0. for m in args[1]}; args[6] = {r: 0. for r in args[6]}
        trace = []; kw['ready_trace'] = trace
        cost = local.rollout_local_tts_ramp_aware(*args, **kw)
        expected = sum(args[5].values()) * 2 * self.cfg.simulation.T_u_h
        self.assertAlmostEqual(cost, expected)
        self.assertTrue(all(sum(row['eligible_veh'].values()) == 0. for row in trace))
        self.assertTrue(all(sum(row['stock_after_landing_veh'].values()) == sum(args[5].values()) for row in trace))

    def test_future_signal_offers_land_after_fw_block_and_mature_at_due(self):
        self.enable(); state = self.state.copy(); step = uqm._urban_step_index(state, self.cfg)
        for off in self.model.offramp_movements:
            storage = self.cfg.network.off_ramp_storage_link[off]
            state.urban_link_storage[storage] = self.cfg.network.urban_link_storage_veh[storage]
        args, kw = local_args(self.cfg, state, self.action, self.model, substeps=10, fraction=1.)
        args = list(args); args[1] = {m: 0. for m in args[1]}; args[6] = {r: 0. for r in args[6]}
        off = self.model.specs[TARGETS[0]]['off_ramp']; args[4] = {off: 720.}
        trace = []; diagnostics = {}; kw.update(ready_trace=trace, ready_diagnostics=diagnostics)
        cost = local.rollout_local_tts_ramp_aware(*args, **kw)
        share = self.cfg.network.offramp_direct_share_by_offramp[off]
        first = next(row for row in trace if row['eligible_veh'][off] > 0.)
        self.assertEqual(first['service_step'], step + self.cfg.simulation.K_fu + uqm._inflow_delay_steps(self.cfg))
        self.assertEqual(trace[0]['landings'], [])
        first_admission = next(row for row in trace[1]['landings'] if row['offramp'] == off)
        self.assertEqual(first_admission['admission_step'], step + 2)
        self.assertEqual(first_admission['due_step'], step + 9)
        self.assertAlmostEqual(first_admission['signal_accepted_veh'], 2. * (1. - share))
        self.assertEqual(trace[1]['residence_off_stock_veh'], 0.)  # Landing follows this step's cost.
        self.assertAlmostEqual(cost, sum(row['residence_off_stock_veh'] for row in trace) * self.cfg.simulation.T_u_h)
        self.assertEqual(diagnostics['signal_rejected_veh'], 0.)
        self.assertAlmostEqual(diagnostics['signal_accepted_veh'], 10. * (1. - share))
        # Reuse the actual signal-only global scheduler as a timestamp/amount oracle.
        oracle = state.copy(); scheduler = uqm._offramp_landing_orig_schedule
        accepted, rejected = scheduler(oracle, self.cfg, off, 2. * (1. - share), step + 2)
        storage = self.cfg.network.off_ramp_storage_link[off]
        self.assertEqual(oracle.offramp_transit_buffer[storage], {step + 9: accepted})
        self.assertEqual(rejected, 0.)
        self.assertTrue(all(abs(row['stock_residual_veh']) < 1e-8 for row in trace))
        self.__class__.evidence['future_block'] = {'trace': trace, 'metrics': diagnostics, 'cost_veh_h': cost}

    def test_receiver_rejection_is_counted_and_never_reserved_or_erases_stock(self):
        self.enable(); state = self.state.copy(); off = self.model.specs[TARGETS[0]]['off_ramp']
        storage = self.cfg.network.off_ramp_storage_link[off]; state.urban_link_storage[storage] = 0.
        args, kw = local_args(self.cfg, state, self.action, self.model, substeps=2, fraction=0.)
        args = list(args); args[4] = {off: 720.}
        trace = []; metrics = {}; kw.update(ready_trace=trace, ready_diagnostics=metrics)
        candidate_summary = {}; token = self.pool._READY_METRICS.set(candidate_summary)
        try:
            local.rollout_local_tts_ramp_aware(*args, **kw)
        finally:
            self.pool._READY_METRICS.reset(token)
        self.assertGreater(metrics['signal_rejected_veh'], 0.)
        self.assertEqual(metrics['signal_accepted_veh'], 0.)
        self.assertEqual(metrics['overflow_blocks'], 1.)
        self.assertEqual(trace[-1]['pending'][off], {})
        self.assertEqual(trace[-1]['stock_after_landing_veh'][off], args[5][off])
        self.assertEqual(candidate_summary['shared_service_ready_overflow_candidate_count'], 1.)
        self.__class__.evidence['rejection'] = {'metrics': metrics, 'candidate_summary': candidate_summary}

    def test_ready_seed_required_validated_and_copied_per_candidate(self):
        from dataclasses import replace
        self.enable(); args, kw = local_args(self.cfg, self.state, self.action, self.model, substeps=2)
        for change in ({'ready_seed': None}, {'green_profile_start_step': 181},
                       {'ready_seed': replace(kw['ready_seed'], delay_steps=1)}):
            with self.assertRaises(ValueError): local.rollout_local_tts_ramp_aware(*args, **{**kw, **change})
        changed = self.state.copy(); storage = self.cfg.network.off_ramp_storage_link['OR_F_W']
        changed.offramp_transit_buffer[storage] = {181: 11.}
        with self.assertRaises(ValueError): self.pool.make_ready_seed(changed, self.model)
        changed.offramp_transit_buffer[storage] = {181: 10.}
        args, kw = local_args(self.cfg, changed, self.action, self.model, substeps=2)
        before = pickle.dumps((changed, args, kw))
        first = local.rollout_local_tts_ramp_aware(*args, **kw)
        self.assertEqual(first, local.rollout_local_tts_ramp_aware(*args, **kw))
        self.assertEqual(before, pickle.dumps((changed, args, kw)))

    def test_ready_context_nested_exception_and_wrong_model_reset(self):
        self.enable(); state = self.state.copy(); state.time_sec += self.cfg.simulation.T_u_sec
        self.assertIsNone(self.pool._READY_CONTEXT.get())
        with self.pool.bind_ready(self.state, self.model):
            outer = self.pool._READY_CONTEXT.get()
            with self.assertRaisesRegex(RuntimeError, 'test abort'):
                with self.pool.bind_ready(state, self.model):
                    self.assertEqual(self.pool._READY_CONTEXT.get()[1].start_step, 181)
                    raise RuntimeError('test abort')
            self.assertIs(self.pool._READY_CONTEXT.get(), outer)
            args, kw = local_args(self.cfg, self.state, self.action, self.model)
            kw.pop('ready_seed'); kw.pop('green_profile_start_step')
            args = list(args); args[0] = copy.copy(self.model)
            with self.assertRaises(ValueError): local.rollout_local_tts_ramp_aware(*args, **kw)
        self.assertIsNone(self.pool._READY_CONTEXT.get())

    def _actual_local_call_inputs(self, agent, state):
        coupling = agent._wu._coupling(state, self.action, self.demand)
        arrivals = agent._per_movement_arrivals('SC1004', state, self.action, self.demand)
        space = agent._frozen_s_eff(state)
        return coupling, arrivals, space

    def test_actual_green_offset_refinement_callers_use_identical_seed(self):
        self.enable(); agent = LinkAgentWuFollower(self.cfg)
        agent.phase_price_local_cost_model = 'phased'
        self.assertFalse(agent.ramp_aware_phase_resolved)
        prior_active = agent._phase_resolved_active_signals
        agent.offset_fractions = (self.action.offsets['SC1004'] / self.cfg.network.cycle_length,)
        self.cfg.mpc.horizon_steps = 1  # One fixed local candidate per axis; no endpoint/search network.
        state = self.state.copy(); storage = self.cfg.network.off_ramp_storage_link['OR_F_W']
        state.offramp_transit_buffer[storage] = {181: 10.}
        coupling, arrivals, space = self._actual_local_call_inputs(agent, state)
        captured = []; original = self.pool.rollout_shared_ramp
        def trace(*args, **kwargs):
            captured.append(kwargs['ready_seed'])
            return original(*args, **kwargs)
        p1 = self.action.green_times['SC1004_p1']
        with patch.object(self.pool, 'rollout_shared_ramp', side_effect=trace):
            green = agent._solve_urban_agent_local('SC1004', state, coupling, arrivals, space, {}, {},
                self.action, demand=self.demand, candidates_override=[p1])
            self.assertEqual(green[2], 1)
            self.assertIsNone(self.pool._READY_CONTEXT.get())
            self.assertIs(agent._phase_resolved_active_signals, prior_active)
            offset = agent._solve_offset_local_ramp('SC1004', p1, state, coupling, arrivals, space, self.action, self.demand)
            self.assertEqual(offset[1], 1)
            ctx = agent._phase_refine_context(state, self.action, self.demand)
            setup = agent._phase_refine_signal_setup('SC1004', state, ctx)
            phases = {p: self.action.green_times['SC1004_' + p] for p in ('p1', 'p2', 'p3', 'p4')}
            agent._phase_local_cost_phased('SC1004', phases, setup, ctx)
        self.assertEqual(len(captured), 3)
        self.assertEqual(captured[0], captured[1]); self.assertEqual(captured[1], captured[2])
        from dataclasses import asdict
        self.__class__.evidence['actual_caller_seeds'] = [asdict(seed) for seed in captured]
        self.assertEqual(dict(dict((row[0], row[-1]) for row in captured[0].rows)['OR_F_W']), {181: 10.})
        with patch.object(agent, '_offset_green_fractions', return_value={}):
            with self.assertRaises(ValueError):
                agent._solve_offset_local_ramp('SC1004', p1, state, coupling, arrivals, space, self.action, self.demand)
            with self.assertRaises(ValueError):
                agent._solve_urban_agent_local('SC1004', state, coupling, arrivals, space, {}, {},
                    self.action, demand=self.demand, candidates_override=[p1])
        self.assertIsNone(self.pool._READY_CONTEXT.get())
        self.assertIs(agent._phase_resolved_active_signals, prior_active)

    def test_actual_green_callers_off_after_install_are_exact(self):
        self.cfg.mpc.horizon_steps = 1
        before = one_actual_green(self.cfg, self.state, self.action, self.demand, self.pool)
        self.enable()
        self.pool.configure(self.cfg, {'urban': {'shared_local_service_pool': False}})
        after = one_actual_green(self.cfg, self.state, self.action, self.demand, self.pool)
        self.assertEqual(before, after)
        self.assertEqual(after['seeds'], [])

    def test_fresh_worker_actual_caller_builds_seed_from_state_and_off_matches(self):
        self.cfg.mpc.horizon_steps = 1
        state = self.state.copy(); storage = self.cfg.network.off_ramp_storage_link['OR_F_W']
        state.offramp_transit_buffer[storage] = {181: 10.}
        outcomes = []
        for enabled in (True, False):
            self.pool.configure(self.cfg, {'urban': {'shared_local_service_pool': enabled}})
            expected = one_actual_green(self.cfg, state, self.action, self.demand, self.pool)
            code = '''import pickle,sys,json
from diagnostics.test_shared_service_pool import installed,one_actual_green
from diagnostics.probe_model_area_integration import adapter
with installed() as (pool,route,runtime):
    cfg,state,action,demand,raw,detectors=pickle.loads(sys.stdin.buffer.read())
    runtime.install_worker_runtime(adapter,cfg,raw,detectors)
    print(json.dumps(one_actual_green(cfg,state,action,demand,pool),sort_keys=True))
'''
            result = subprocess.run([sys.executable, '-X', 'utf8', '-c', code],
                input=pickle.dumps((self.cfg, state, self.action, self.demand, self.raw, self.detectors)),
                capture_output=True, cwd=ROOT, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
            actual = json.loads(result.stdout)
            self.assertEqual(actual, json.loads(json.dumps(expected)))
            self.assertEqual(len(actual['seeds']), int(enabled))
            outcomes.append({'enabled': enabled, **actual})
        self.__class__.evidence['actual_worker_on_off'] = outcomes

    def test_result_diagnostics_scope_is_restored_after_success_and_exception(self):
        # The full solve is intentionally not run. This checks only the small
        # output-transport wrapper around its documented response interface.
        self.enable(); cfg = self.cfg
        def response(self):
            collector = self_pool._READY_METRICS.get()
            collector['shared_service_ready_candidate_max_signal_rejected_veh'] = 2.
            return types.SimpleNamespace(diagnostics={}, control=self_action.copy())
        self_pool, self_action = self.pool, self.action
        with patch.object(LinkAgentWuFollower, 'solve', response):
            self.pool.install_ready_callers()
            agent = LinkAgentWuFollower(cfg); output = agent.solve()
            self.assertEqual(output.diagnostics['shared_service_ready_candidate_max_signal_rejected_veh'], 2.)
            self.assertEqual(output.control.diagnostics['shared_service_ready_candidate_max_signal_rejected_veh'], 2.)
            self.assertIsNone(self.pool._READY_METRICS.get())
        def failure(self):
            raise RuntimeError('test aborted original solve')
        with patch.object(LinkAgentWuFollower, 'solve', failure):
            self.pool.install_ready_callers()
            with self.assertRaises(RuntimeError): LinkAgentWuFollower(cfg).solve()
            self.assertIsNone(self.pool._READY_METRICS.get())

    def test_fresh_process_reinstalls_from_serialized_cfg(self):
        self.enable()
        state = self.state.copy(); storage = self.cfg.network.off_ramp_storage_link['OR_F_W']
        state.offramp_transit_buffer[storage] = {181: 10.}
        args, kw = local_args(self.cfg, state, self.action, self.model, substeps=10)
        args = list(args); args[4] = {'OR_F_W': 720.}
        expected = local.rollout_local_tts_ramp_aware(*args, **kw)
        command = [sys.executable, '-X', 'utf8', '-c',
            'import pickle,sys; from diagnostics.test_shared_service_pool import installed; '
            'from diagnostics.probe_model_area_integration import adapter; '
            'from src.controllers import local_signal_plant as local; '
            'ctx=installed(); pool,route,runtime=ctx.__enter__(); '
            'args,kw,raw,detectors=pickle.loads(sys.stdin.buffer.read()); '
            'runtime.install_worker_runtime(adapter,args[0].cfg,raw,detectors); '
            'print(repr(local.rollout_local_tts_ramp_aware(*args,**kw))); ctx.__exit__(None,None,None)']
        result = subprocess.run(command, input=pickle.dumps((args, kw, self.raw, self.detectors)), capture_output=True, cwd=ROOT, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
        self.assertEqual(float(result.stdout.decode().strip()), expected)


if __name__ == '__main__':
    if sys.argv[1:] == ['--evidence']:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PoolTests))
        if not result.wasSuccessful():
            raise SystemExit(1)
        report = {'schema': 'shared-service-ready-production-validation/v1', 'tests_passed': result.testsRun,
                  'scope': 'canonical production imports; bounded local candidates/services; no endpoint/full MPC/VISSIM',
                  'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in SOURCE_PATHS},
                  'source_changes': [], 'evidence': PoolTests.evidence}
        (ROOT / 'diagnostics/shared_service_ready_production_validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    else:
        unittest.main()
