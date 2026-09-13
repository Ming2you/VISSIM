"""Accepted urban transfers and endpoint integration; no live simulation."""
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
from src.models.state import ExperimentConfig, TrafficState, ControlAction
from src.models.demand import DemandStep
from src.models import urban_queue_model as uqm
from evaluation.controllers import urban_flow_accounting as urban, area_runtime
from evaluation.controllers.control_area_objective import ModelAreaLedger, MembershipError


def seed_all_inside(state, cfg, *, capture=False):
    stocks = area_runtime.model_inventory(state, cfg)
    state._control_area_ledger = ModelAreaLedger({k: {'inside': v} for k, v in stocks.items()}, capture_response=capture)
    state._control_area_ledger.begin_response_step('urban', 0, cfg.simulation.T_u_h * 3600)
    routes = {}
    for movement, spec in uqm.movement_specs(cfg).items():
        routes['movement:' + movement] = {'target_inside': bool(spec.get('receiving_link') in state.urban_link_storage)}
        routes['arrival:' + movement] = {'target_inside': True}
    for origin in cfg.network.boundary_in_links:
        routes['input:gate:' + origin] = {'target_inside': True}
    for ramp in cfg.network.ramps:
        routes['input:ramp:' + ramp] = {'target_inside': True}
    cfg.network.control_area_routes = routes
    return state._control_area_ledger


class UrbanAccountingTests(unittest.TestCase):
    def test_vendor_equations_unchanged_and_all_accepted_flows_conserved(self):
        cfg = ExperimentConfig()
        state = TrafficState.initial(cfg)
        uqm.ensure_urban_state(state, cfg)
        state.urban_movement_queue = {k: 3.0 for k in state.urban_movement_queue}
        control = ControlAction.uncontrolled(cfg)
        demand = DemandStep({}, {}, {})
        seed_all_inside(state, cfg)
        reference = state.copy()
        actual = urban.urban_substep_accounted(state, control, demand, cfg, urban_step_index=0, ramp_release_veh_h={})
        expected = uqm.urban_substep(reference, control, demand, cfg, urban_step_index=0, ramp_release_veh_h={})
        self.assertEqual(actual, expected)
        self.assertEqual({k: v for k, v in vars(state).items() if k != '_control_area_ledger'},
                         {k: v for k, v in vars(reference).items() if k != '_control_area_ledger'})
        state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state, cfg))

    def test_internal_transfer_and_physical_excursion(self):
        ledger = ModelAreaLedger({'u': {'inside': 10}, 'fw': {}})
        ledger.transfer('u', 'fw', 4, inside_to_inside=1, outside_to_inside=0)
        self.assertEqual(ledger.ttd_veh, 0)
        ledger.transfer('fw', 'u', 2, inside_to_inside=1, outside_to_inside=1,
                        physical_source_inside=True, outward_crossings=1, inward_crossings=1)
        self.assertEqual(ledger.ttd_veh, 2)
        self.assertEqual(ledger.entered_veh, 2)
        ledger.residence(['u', 'fw'], .5)
        self.assertEqual(ledger.ttt_veh_h, 5)
        with self.assertRaises(MembershipError):
            ledger.residence(['u', 'u'], .5)

    def test_initialized_twenty_vehicles_arrive_once_not_forty(self):
        cfg = ExperimentConfig()
        state = TrafficState.initial(cfg)
        uqm.ensure_urban_state(state, cfg)
        sinks = uqm.sink_storage_links(cfg)
        source = next(k for k in uqm.approach_routing(cfg) if k in cfg.network.urban_link_storage_veh
                      and k not in sinks and k not in cfg.network.off_ramp_storage_link.values())
        state.urban_link_storage[source] = cfg.network.urban_link_storage_veh[source] - 20
        state.urban_arrival_buffer = {source: {1: 20.0}}
        cfg.network.movement_capacity_veh_h = 0
        control = ControlAction.uncontrolled(cfg)
        for key in control.green_times:
            control.green_times[key] = 0.0
        baseline = state.copy()
        paired = state.copy()
        metadata = area_runtime.pair_initial_arrival_releases(paired, cfg)
        def urban_total(s):
            return sum(s.urban_movement_queue.values()) + sum(cfg.network.urban_link_storage_veh[k] - v for k, v in s.urban_link_storage.items())
        opening = urban_total(state)
        uqm.urban_substep(baseline, control, DemandStep({}, {}, {}), cfg, urban_step_index=1, ramp_release_veh_h={})
        uqm.urban_substep(paired, control, DemandStep({}, {}, {}), cfg, urban_step_index=1, ramp_release_veh_h={})
        self.assertAlmostEqual(urban_total(baseline), opening + 20)
        self.assertAlmostEqual(urban_total(paired), opening)
        self.assertEqual(metadata['paired_initial_arrival_release_veh'], 20)

    def test_failed_event_is_atomic_and_retryable(self):
        ledger = ModelAreaLedger({'x': {'inside': 8}})
        with self.assertRaises(ValueError):
            ledger.transfer('x', None, 3, inside_to_inside=0, outside_to_inside=0,
                            physical_source_inside=True, outward_crossings=-1, inward_crossings=0, event_id='attempt')
        self.assertEqual(ledger.stocks['x']['inside'], 8)
        self.assertNotIn('attempt', ledger.explicit_events)

    def test_conservative_transit_flag_is_independent_and_initializes_once(self):
        cfg = ExperimentConfig()
        state = TrafficState.initial(cfg)
        before = dict(vars(cfg.network))
        self.assertEqual(area_runtime.configure_initial_transit(cfg, {}, state), {})
        self.assertEqual(vars(cfg.network), before)
        tuning = {'urban': {'conservative_initial_transit': True}}
        first = area_runtime.configure_initial_transit(cfg, tuning, state)
        state.urban_storage_release_buffer['future_candidate_flow'] = {999: 3}
        second = area_runtime.configure_initial_transit(cfg, tuning, state)
        self.assertEqual(first, second)
        self.assertEqual(state.urban_storage_release_buffer['future_candidate_flow'], {999: 3})
        self.assertFalse(getattr(cfg.network, 'control_area_enabled', False))

    def test_candidate_copy_isolation_and_event_idempotency(self):
        cfg = ExperimentConfig()
        state = TrafficState.initial(cfg)
        state._control_area_ledger = ModelAreaLedger({'x': {'inside': 8}})
        copied = state.copy()
        args = dict(inside_to_inside=0, outside_to_inside=0, event_id='exit1')
        copied._control_area_ledger.transfer('x', None, 3, **args)
        copied._control_area_ledger.transfer('x', None, 3, **args)
        self.assertEqual(copied._control_area_ledger.ttd_veh, 3)
        self.assertEqual(state._control_area_ledger.stocks['x']['inside'], 8)


class ResourceEvidenceTests(unittest.TestCase):
    """Tiny source/receiver competitions; no endpoint, adapter or native run."""
    def assert_same_state(self, left, right):
        self.assertEqual({k: v for k, v in vars(left).items() if k != '_control_area_ledger'},
                         {k: v for k, v in vars(right).items() if k != '_control_area_ledger'})
        a, b = left._control_area_ledger, right._control_area_ledger
        self.assertEqual({k: v for k, v in vars(a).items() if not k.startswith('_response')},
                         {k: v for k, v in vars(b).items() if not k.startswith('_response')})

    def test_regular_batch_and_head_capture_actual_not_intended_off_exact(self):
        from evaluation.controllers import head_service_resources as heads
        cfg = ExperimentConfig()
        first = next(m for m, s in cfg.network.urban_movements.items()
                     if s.get('receiving_link') in cfg.network.urban_link_storage_veh
                     and not s.get('ramp') and s.get('kind') != 'off_ramp')
        second = first + '_test_competitor'
        cfg.network.urban_movements[second] = dict(cfg.network.urban_movements[first])
        receiver = cfg.network.urban_movements[first]['receiving_link']
        state = TrafficState.initial(cfg); uqm.ensure_urban_state(state, cfg)
        state.urban_movement_queue = {m: (5. if m in (first, second) else 0.) for m in state.urban_movement_queue}
        state.ramp_queue = {r: 0. for r in state.ramp_queue}
        control = ControlAction.uncontrolled(cfg); demand = DemandStep({}, {}, {})
        left, right = state.copy(), state.copy()
        seed_all_inside(left, cfg); ledger = seed_all_inside(right, cfg, capture=True)
        def context(*args):
            return ({'test_head': 1.0}, {}, {first: 'test_head', second: 'test_head'})
        with patch.object(heads, 'regular_context', side_effect=context), \
             patch.object(uqm, '_phase_green_fraction', return_value=1.), \
             patch.object(uqm, '_movement_capacity_flow', return_value=36000.), \
             patch.object(uqm, '_effective_available_space', side_effect=lambda s, c, link: .75 if link == receiver else 0.):
            expected = urban.urban_substep_accounted(left, control, demand, cfg, 0, {})
            actual = urban.urban_substep_accounted(right, control, demand, cfg, 0, {})
        self.assertEqual(expected, actual); self.assert_same_state(left, right)
        rows = ledger.response()['resource_allocations']
        receiving = next(r for r in rows if r['kind'] == 'regular_receiving' and r['resource'] == 'storage:' + receiver)
        head = next(r for r in rows if r['kind'] == 'regular_shared_head')
        self.assertEqual(receiving['available_veh'], .75)
        self.assertEqual(head['available_veh'], 1.)
        self.assertEqual(head['accepted_total_veh'], .75)
        self.assertEqual(head['accepted_by_source_veh'], {'movement:' + first: .375, 'movement:' + second: .375})
        self.assertEqual(receiving['accepted_total_veh'], head['accepted_total_veh'])
        self.assertFalse(ledger.response()['shared_capacity_certificate'])
        ledger.assert_stocks(area_runtime.model_inventory(right, cfg))

    def test_grouped_ramp_receiving_uses_one_remaining_room(self):
        cfg = ExperimentConfig()
        first = next(m for m, s in cfg.network.urban_movements.items() if s.get('ramp'))
        second = first + '_test_competitor'
        spec = cfg.network.urban_movements[first]
        ramp = spec['ramp']
        cfg.network.ramp_queue_max_veh_by_ramp[ramp] = 20.
        cfg.network.urban_movements[second] = dict(spec)
        cfg.network.on_ramp_to_movement[ramp].append(second)
        state = TrafficState.initial(cfg); uqm.ensure_urban_state(state, cfg)
        state.urban_movement_queue = {m: (4. if m in (first, second) else 0.) for m in state.urban_movement_queue}
        state.ramp_queue[ramp] = cfg.network.ramp_queue_cap(ramp) - 1.5
        left, right = state.copy(), state.copy()
        seed_all_inside(left, cfg); ledger = seed_all_inside(right, cfg, capture=True)
        control = ControlAction.uncontrolled(cfg); demand = DemandStep({}, {}, {})
        with patch.object(uqm, '_phase_green_fraction', return_value=1.), \
             patch.object(uqm, '_movement_capacity_flow', return_value=36000.):
            expected = urban.urban_substep_accounted(left, control, demand, cfg, 0, {})
            actual = urban.urban_substep_accounted(right, control, demand, cfg, 0, {})
        self.assertEqual(expected, actual); self.assert_same_state(left, right)
        row = next(r for r in ledger.response()['resource_allocations']
                   if r['kind'] == 'urban_ramp_receiving' and r['resource'] == 'ramp:' + ramp)
        self.assertEqual(row['available_veh'], 1.5)
        self.assertEqual(row['accepted_total_veh'], 1.5)
        self.assertEqual(row['accepted_by_source_veh']['movement:' + first], .75)
        self.assertEqual(row['accepted_by_source_veh']['movement:' + second], .75)
        ledger.assert_stocks(area_runtime.model_inventory(right, cfg))

    def test_off_drain_records_sequential_receiver_room_not_reused_capacity(self):
        cfg = ExperimentConfig(); state = TrafficState.initial(cfg)
        uqm.ensure_urban_state(state, cfg)
        ramp = cfg.network.off_ramps[0]; source = cfg.network.off_ramp_storage_link[ramp]
        receiver = next(k for k in state.urban_link_storage if k != source)
        cfg.network.off_ramp_to_movement = {ramp: ['test_a', 'test_b']}
        specs = {m: {'beta': .5, 'receiving_link': receiver} for m in ('test_a', 'test_b')}
        state.urban_link_storage[source] = cfg.network.urban_link_storage_veh[source] - 10.
        state.urban_link_storage[receiver] = 3.
        ledger = seed_all_inside(state, cfg, capture=True)
        cfg.network.control_area_routes.update({'movement:' + m: {'target_inside': True} for m in specs})
        with patch.object(uqm, '_phase_green_fraction', return_value=1.), \
             patch.object(uqm, '_movement_capacity_flow', return_value=36000.), \
             patch.object(uqm, '_effective_available_space', side_effect=lambda s, c, link: s.urban_link_storage[link]):
            result = urban._drain_offramp_storage_accounted(state, ControlAction.uncontrolled(cfg), cfg, specs, 0, {})
        rows = ledger.response()['resource_allocations']
        rows = [r for r in rows if r['kind'] == 'offramp_receiving']
        self.assertEqual([r['available_veh'] for r in rows], [3., 0.])
        self.assertEqual([r['accepted_total_veh'] for r in rows], [3., 0.])
        self.assertEqual(result[ramp], 3.)

    def test_direct_and_signal_landings_keep_original_allocation_and_clock(self):
        cfg = ExperimentConfig(); state = TrafficState.initial(cfg)
        uqm.ensure_urban_state(state, cfg)
        ramp = cfg.network.off_ramps[0]; signal = cfg.network.off_ramp_storage_link[ramp]
        direct = next(k for k in state.urban_link_storage if k not in cfg.network.off_ramp_storage_link.values())
        cfg.network.offramp_direct_share_by_offramp = {ramp: .25}
        cfg.network.offramp_direct_tail_by_offramp = {ramp: direct}
        state.urban_link_storage[direct] = 2.; state.urban_link_storage[signal] = 8.
        left, right = state.copy(), state.copy()
        seed_all_inside(left, cfg); ledger = seed_all_inside(right, cfg, capture=True)
        cfg.network.control_area_routes.update({key + ramp: {'target_inside': True}
            for key in ('offramp_direct:', 'offramp_signal:')})
        # The isolated landing receives vehicles already withdrawn by freeway
        # continuity. Apply that known withdrawal to the fixture, not dynamics.
        freeway = cfg.network.off_ramp_from_freeway[ramp]
        initial = sum(ledger.stocks['freeway:' + freeway].values())
        for target_state in (left, right):
            target_state.freeway_density[freeway] = [rho * (initial - 8.) / initial
                for rho in target_state.freeway_density[freeway]]
        ledger.begin_response_step('landing', 0, cfg.simulation.T_f_h * 3600)
        with patch.object(urban, '_adapter', SimpleNamespace(_LEGSPLIT_LAST={})), \
             patch.object(uqm, '_offramp_landing_orig_schedule', uqm.schedule_offramp_arrivals, create=True):
            expected = urban.schedule_offramp_arrivals_accounted(left, cfg, ramp, 8., 2)
            actual = urban.schedule_offramp_arrivals_accounted(right, cfg, ramp, 8., 2)
        self.assertEqual(expected, actual); self.assert_same_state(left, right)
        rows = ledger.response()['resource_allocations']
        self.assertEqual([r['available_veh'] for r in rows], [2., 8.])
        self.assertEqual([r['accepted_total_veh'] for r in rows], [2., 6.])
        self.assertTrue(all(r['stage'] == 'landing' for r in rows))
        ledger.assert_stocks(area_runtime.model_inventory(right, cfg))

    def test_legsplit_final_common_ramp_room_after_regular_acceptance(self):
        cfg = ExperimentConfig(); state = TrafficState.initial(cfg)
        uqm.ensure_urban_state(state, cfg)
        ramp = cfg.network.ramps[0]
        cfg.network.ramp_queue_max_veh_by_ramp[ramp] = 20.
        sources = list(cfg.network.urban_link_storage_veh)[:2]
        cfg.network.leg_ramp_split_enabled = True
        cfg.network.boundary_out_ramp_split = {s: {'free': 0., 'ramps': {ramp: 1.}} for s in sources}
        cfg.network.ramp_capacity_veh_h[ramp] = 36000.
        state.ramp_queue[ramp] = cfg.network.ramp_queue_cap(ramp) - 5.
        for source in sources:
            state.urban_link_storage[source] = cfg.network.urban_link_storage_veh[source] - 10.
        left, right = state.copy(), state.copy()
        seed_all_inside(left, cfg); ledger = seed_all_inside(right, cfg, capture=True)
        cfg.network.control_area_routes.update({'legsplit:' + s: {'target_inside': True} for s in sources})
        def body(s, *args, **kwargs):
            s.ramp_queue[ramp] += 3.
            # The stub represents another accepted transfer before reconciliation.
            s._control_area_ledger.transfer(None, 'ramp:' + ramp, 3.,
                source_inside=False, inside_to_inside=1., outside_to_inside=1.)
            return {'unchanged_body_result': True}
        stub = SimpleNamespace(_LEGSPLIT_LAST={}, _mapping=lambda x: x or {},
            _legsplit_arrived_at_link=lambda *args: 10., _legsplit_wout_rate=lambda *args: 720.)
        with patch.object(urban, '_adapter', stub), patch.object(urban, 'urban_substep_accounted', side_effect=body):
            expected = urban.legsplit_substep_accounted(left, ControlAction.uncontrolled(cfg), DemandStep({}, {}, {}), cfg, 0, {})
            actual = urban.legsplit_substep_accounted(right, ControlAction.uncontrolled(cfg), DemandStep({}, {}, {}), cfg, 0, {})
        self.assertEqual(expected, actual); self.assert_same_state(left, right)
        row, = [r for r in ledger.response()['resource_allocations'] if r['kind'] == 'legsplit_ramp_receiving']
        self.assertEqual(row['available_veh'], 2.)
        self.assertEqual(row['accepted_by_source_veh'], {'legsplit:' + s: 1. for s in sources})
        ledger.assert_stocks(area_runtime.model_inventory(right, cfg))

    def test_capture_rejects_oversubscription_and_off_never_records(self):
        off = ModelAreaLedger({})
        off.record_resource_allocation(None, None, float('nan'), None)
        self.assertIsNone(urban._resource_ledger(SimpleNamespace(_control_area_ledger=off)))
        ledger = ModelAreaLedger({}, capture_response=True)
        ledger.begin_response_step('urban', 0., 5.)
        with self.assertRaisesRegex(ValueError, 'exceeds'):
            ledger.record_resource_allocation('test', 'receiver', 1., {'a': .6, 'b': .6})
        self.assertEqual(ledger.response()['resource_allocations'], [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
