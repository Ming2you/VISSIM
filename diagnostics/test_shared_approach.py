"""Shared input/routing and physical observation coverage regressions."""
from pathlib import Path
import copy
import json
import math
from types import SimpleNamespace as NS
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'diagnostics'), str(ROOT / 'vendor/NumSim-mine')]
from evaluation.controllers import shared_approach, projection_support, observation_projection, area_runtime
from evaluation.controllers.control_area_objective import physical_membership_from_ledger, projection_stock_cohorts, model_stock_values, ModelAreaLedger


def fixture(time=900, raw_transform=None):
    from test_observation_projection import ActualInstalledProjection as Harness
    Harness.setUpClass()
    adapter = Harness.adapter
    from src.models.state import TrafficState, ControlAction
    nc = ROOT / 'evaluation/runs/codex_nc_s13_6056c94_20260909_retry/decisions_codex_nc_s13_6056c94_20260909_retry'
    if time == 900:
        path, previous = nc / 'state_000900.json', nc / 'action_000001.json'
    else:
        base = ROOT / 'evaluation/runs/codex_n7_s13_6056c94_20260909/decisions_codex_n7_s13_6056c94_20260909'
        path, previous = base / 'state_003300.json', base / 'action_003150.json'
    cfg, _, detectors, tuning, raw, mapping, _ = Harness.build_projected(Harness.config_path, path, previous)
    cfg, tuning = copy.deepcopy(cfg), copy.deepcopy(tuning)
    if raw_transform:
        raw_transform(raw)
    tuning.setdefault('urban', {})['shared_approach'] = 'diagnostics/shared_approach_ver2.json'
    tuning.setdefault('observation', {})['physical_support_repair'] = 'diagnostics/physical_projection_support_ver2.json'
    shared_metadata = shared_approach.configure(cfg, tuning, raw)
    detectors, prepared, support_metadata = projection_support.configure(cfg, tuning, detectors, raw)
    detectors, _ = observation_projection.install_physical_branch_projection(
        cfg, Harness.overlay, detectors, link_counts=adapter._link_counts_from_local_observation(prepared))
    calibration = adapter.deep_update(dict(Harness.calibration), tuning.get('calibration_override', {}))
    with patch.object(adapter, 'build_local_observation_summary', Harness.patched_summary):
        state = adapter.traffic_state_from_vissim(prepared, cfg, TrafficState, detectors, calibration)
    area_runtime.pair_initial_arrival_releases(state, cfg)
    init = shared_approach.initialize(state, cfg, prepared, detectors)
    return cfg, state, prepared, detectors, shared_metadata, support_metadata, init, ControlAction.uncontrolled(cfg)


class SharedApproachTests(unittest.TestCase):
    def test_actual_900_missing_fifty_vehicles_reach_physical_stocks_once(self):
        cfg, state, raw, detectors, _, support, init, _ = fixture()
        ledger = json.loads((ROOT / 'diagnostics/control_area_membership.json').read_text(encoding='utf-8'))
        physical = physical_membership_from_ledger(ledger)
        provenance = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
        counts = raw['vehicle_records']['full_network_link_counts']
        for link in support['links']:
            self.assertAlmostEqual(sum(provenance.get(link, {}).values()), counts.get(link, 0))
        self.assertEqual(sum(row['snapshot_vehicles'] for row in support['links'].values()), 50)
        self.assertEqual(init['shared_initial_veh'], 32)
        self.assertAlmostEqual(sum(sum(x.values()) for x in state.shared_approach_state['bins'].values()), 32)
        observed_urban_inside = sum(count for link, count in counts.items()
                                    if physical.get(link) and link not in detectors['freeway_link_to_model_link'])
        cohorts = projection_stock_cohorts(provenance, physical)
        urban_inside = sum(row['inside'] for row in cohorts.values())
        self.assertEqual(urban_inside, observed_urban_inside)

    def test_actual_3300_additional_connectors_are_not_lost(self):
        _, state, raw, _, _, support, init, _ = fixture(3300)
        assignment = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
        for link in support['links']:
            self.assertAlmostEqual(sum(assignment.get(link, {}).values()), raw['vehicle_records']['full_network_link_counts'].get(link, 0))
        self.assertEqual(sum(assignment['10625'].values()), 2)
        self.assertEqual(sum(assignment['10629'].values()), 6)
        self.assertEqual(init['shared_initial_veh'], 52)

    def test_observed_stopped_spillback_does_not_seed_shared_stock_twice(self):
        def stop_some(raw):
            rows = [row for row in raw['vehicle_records']['records'] if str(row['link_no']) == '69']
            for row in rows[:10]:
                row['stopped'] = True; row['speed_kph'] = 0; row['lane_no'] = 1
            raw['local_observation']['link_stopped_counts']['69'] = 10
        _, state, raw, _, _, _, init, _ = fixture(raw_transform=stop_some)
        self.assertEqual(init['shared_initial_veh'], 32)
        self.assertEqual(init['shared_spillback_observation_only_veh'], 10)
        assignment = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']['69']
        self.assertAlmostEqual(sum(assignment.values()), 32)
        self.assertAlmostEqual(assignment['storage:shared_69'], 32)

    def test_native_input_schedule_and_route_weights_are_explicit(self):
        cfg, *_ = fixture()
        spec = cfg.network.shared_approach
        self.assertEqual([x['rate_veh_h'] for x in spec['schedule']], [934, 1333, 1400, 1200, 934, 667])
        self.assertAlmostEqual(sum(x['share'] for x in spec['branches'].values()), 1)
        self.assertAlmostEqual(spec['branches']['1']['share'], 12 / 16.25)
        self.assertAlmostEqual(spec['branches']['2']['share'], 1 / 16.25)
        self.assertGreater(spec['branches']['3']['pre_receiver_distance_m'], 149)
        self.assertAlmostEqual(shared_approach.demand_amount(spec['schedule'], 899, 901), (934 + 1333) / 3600)

    def test_advancing_admits_demand_and_conserves_all_model_stocks(self):
        cfg, state, _, _, _, _, _, control = fixture()
        from src.models.demand import DemandStep
        initial = sum(area_runtime.model_inventory(state, cfg).values())
        admitted, departed = 0.0, 0.0
        for index in range(180, 240):
            row = shared_approach.advance(state, control, DemandStep({}, {}, {}), cfg, index)
            admitted += row['shared_input_admitted_veh']; departed += row['shared_departed_veh']
            self.assertLess(abs(row['shared_mass_residual_veh']), 1e-7)
        final = sum(area_runtime.model_inventory(state, cfg).values())
        self.assertGreater(admitted, 0)
        self.assertGreater(departed, 0)
        self.assertAlmostEqual(final - initial, admitted, places=7)
        self.assertGreater(state.ramp_queue['R_F_W'], 0)

    def test_full_ramp_retains_its_cohorts_while_other_branches_flow(self):
        cfg, state, _, _, _, _, _, control = fixture()
        from src.models.demand import DemandStep
        spec = cfg.network.shared_approach
        state.ramp_queue['R_F_W'] = cfg.network.ramp_queue_cap('R_F_W')
        # Make existing physical cohorts ready; demand is separately disabled.
        for key, bins in state.shared_approach_state['bins'].items():
            state.shared_approach_state['bins'][key] = {180: sum(bins.values())}
        for row in spec['schedule']:
            row['rate_veh_h'] = 0
        before = sum(state.shared_approach_state['bins']['1'].values())
        row = shared_approach.advance(state, control, DemandStep({}, {}, {}), cfg, 180)
        self.assertEqual(row['shared_accepted_by_branch']['1'], 0)
        self.assertAlmostEqual(sum(state.shared_approach_state['bins']['1'].values()), before)
        self.assertGreater(sum(row['shared_accepted_by_branch'].values()), 0)

    def test_candidate_copies_reset_explicit_private_travel_state(self):
        cfg, state, _, _, _, _, _, control = fixture()
        from src.models.demand import DemandStep
        first, second = state.copy(), state.copy()
        a = shared_approach.advance(first, control, DemandStep({}, {}, {}), cfg, 180)
        b = shared_approach.advance(second, control, DemandStep({}, {}, {}), cfg, 180)
        self.assertEqual(a, b)
        self.assertEqual(state.shared_approach_state['last_step'], 179)
        with self.assertRaisesRegex(ValueError, 'sequential'):
            shared_approach.advance(first, control, DemandStep({}, {}, {}), cfg, 180)

    def test_area_ledger_keeps_internal_ramp_transfers_and_inside_generation_distinct(self):
        cfg, state, _, _, _, _, _, control = fixture()
        from src.models.demand import DemandStep
        inventory = area_runtime.model_inventory(state, cfg)
        state._control_area_ledger = ModelAreaLedger({key: {'inside': value, 'outside': 0.0} for key, value in inventory.items()})
        cfg.network.control_area_routes = {'input:shared:shared_69': {'target_inside': True}}
        row = shared_approach.advance(state, control, DemandStep({}, {}, {}), cfg, 180)
        state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state, cfg))
        self.assertGreater(row['shared_input_admitted_veh'], 0)
        self.assertEqual(state._control_area_ledger.ttd_veh, 0)

    def test_flag_absent_is_noop_and_partial_records_fail(self):
        from types import SimpleNamespace
        cfg = SimpleNamespace(network=SimpleNamespace())
        self.assertEqual(shared_approach.configure(cfg, {}, {}), {})
        detectors, raw = {}, {}
        a, b, metadata = projection_support.configure(cfg, {}, detectors, raw)
        self.assertIs(a, detectors); self.assertIs(b, raw); self.assertEqual(metadata, {})
        with self.assertRaisesRegex(ValueError, 'complete vehicle'):
            projection_support.complete_records({'vehicle_records': {'complete': False}})


class SharedResourceEvidenceTests(unittest.TestCase):
    def test_branch_ready_receiving_service_and_generation_off_exact(self):
        from types import SimpleNamespace as NS
        from src.models import urban_queue_model as uqm
        spec = {'storage': 'shared', 'capacity_veh': 10.,
                'schedule': [{'start_sec': 0., 'rate_veh_h': 7200.}],
                'branches': {
                    'r': {'target': 'R', 'target_kind': 'ramp', 'lanes': 1., 'share': .5,
                          'branch_position_m': 10., 'pre_receiver_distance_m': 10.},
                    'u': {'target': 'U', 'target_kind': 'urban', 'lanes': 1., 'share': .5,
                          'branch_position_m': 10., 'pre_receiver_distance_m': 10.}}}
        cfg = NS(network=NS(shared_approach=spec, movement_capacity_veh_h=3600.,
                    ramp_queue_cap=lambda r: 5., urban_avg_speed_km_h=36.,
                    control_area_routes={'input:shared:shared': {'target_inside': True}}),
                 simulation=NS(T_u_sec=5., T_u_h=5/3600))
        initial = NS(urban_link_storage={'shared': 2., 'U': 2.}, ramp_queue={'R': 4.},
            urban_link_speed_kph={}, urban_arrival_buffer={}, urban_storage_release_buffer={},
            shared_approach_state={'bins': {'r': {0: 4.}, 'u': {0: 3., 2: 1.}},
                'last_step': -1, 'unadmitted_demand_veh': 0., 'admitted_veh': 0., 'departed_veh': 0.})
        states, results = [], []
        for capture in (False, True):
            state = copy.deepcopy(initial)
            state._control_area_ledger = ModelAreaLedger({'storage:shared': {'inside': 8.},
                'storage:U': {'inside': 8.}, 'ramp:R': {'inside': 4.}}, capture_response=capture)
            state._control_area_ledger.begin_response_step('urban', 0, 5)
            with patch.object(uqm, 'approach_routing', return_value={'U': [('m', 1.)]}), \
                 patch.object(uqm, '_effective_available_space', side_effect=lambda s,c,k:s.urban_link_storage[k]), \
                 patch.object(uqm, '_link_delay_steps', return_value=1):
                results.append(shared_approach.advance(state, None, None, cfg, 0))
            states.append(state)
        self.assertEqual(results[0], results[1])
        self.assertEqual({k:v for k,v in vars(states[0]).items() if k != '_control_area_ledger'},
                         {k:v for k,v in vars(states[1]).items() if k != '_control_area_ledger'})
        ledger = states[1]._control_area_ledger
        ledger.assert_stocks({'storage:shared': 10., 'storage:U': 10., 'ramp:R': 5.})
        rows = ledger.response()['resource_allocations']
        self.assertEqual([r['accepted_total_veh'] for r in rows if r['kind'] == 'shared_approach_receiving'], [1., 2.])
        self.assertEqual([r['available_veh'] for r in rows if r['kind'] == 'shared_approach_ready'], [4., 3.])
        self.assertEqual(rows[-1]['accepted_total_veh'], 5.)
        self.assertEqual(states[0]._control_area_ledger.metrics, ledger.metrics)


class ObservedInitialRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = ROOT / 'evaluation/runs/codex_native_clock_fw080_u050_open_v2/decisions_codex_native_clock_fw080_u050_open_v2'
        cls.raws = {time: json.loads((base / f'state_{time:06d}.json').read_text(encoding='utf-8-sig'))
                    for time in (900, 1050)}
        cls.evidence = 'diagnostics/selected_control_demand/codex_native_clock_fw080_u050_open_v2/shared_approach.json'

    def initial(self, enabled=True, time=900, transform=None):
        raw = copy.deepcopy(self.raws[time])
        if transform:
            transform(raw)
        cfg = NS(network=NS(urban_link_storage_veh={'in_SC1005_W': 100., 'in_SC1004_W': 100.},
                 boundary_in_links=[], ramps=['R_D_E', 'R_D_W', 'R_F_E', 'R_F_W'],
                 urban_avg_speed_km_h=40.), simulation=NS(T_u_sec=5.))
        tuning = {'urban': {'shared_approach': self.evidence}}
        if enabled is not None:
            tuning['urban']['shared_approach_observed_initial_routes'] = enabled
        metadata = shared_approach.configure(cfg, tuning, raw)
        spec = cfg.network.shared_approach
        count = sum(row['link_no'] == 69 for row in raw['vehicle_records']['records'])
        state = NS(time_sec=time, urban_link_storage={'shared_69': spec['capacity_veh']-count},
                   local_observation_summary={'projection_diagnostics': {
                       'physical_stock_assignment_by_link': {'69': {'storage:shared_69': count}}}},
                   urban_arrival_buffer={'shared_69': {180: count}},
                   urban_storage_release_buffer={'shared_69': {180: count}})
        original = copy.deepcopy(state.urban_link_storage)
        init = shared_approach.initialize(state, cfg, raw, {})
        self.assertEqual(state.urban_link_storage, original)
        self.assertNotIn('shared_69', state.urban_arrival_buffer)
        self.assertNotIn('shared_69', state.urban_storage_release_buffer)
        return cfg, state, init, metadata

    def test_saved_900_1050_routes_are_retained_and_unselected_is_explicit(self):
        for time, known in ((900, {'1': 20, '2': 1, '3': 1, '4': 0}),
                            (1050, {'1': 21, '2': 1, '3': 7, '4': 2})):
            cfg, state, init, _ = self.initial(time=time)
            self.assertEqual(init['shared_initial_observed_route_veh_by_branch'], known)
            self.assertEqual(init['shared_initial_unselected_predecision_veh'], 1)
            self.assertIn('model expectation', init['shared_route_assignment'])
            total = 0.
            for key, bins in state.shared_approach_state['bins'].items():
                expected = known[key] + cfg.network.shared_approach['branches'][key]['share']
                self.assertAlmostEqual(sum(bins.values()), expected)
                total += sum(bins.values())
            self.assertAlmostEqual(total, sum(known.values())+1)

    def test_disabled_and_absent_are_identical_including_config_and_state(self):
        absent = self.initial(enabled=None)
        disabled = self.initial(enabled=False)
        self.assertEqual(absent, disabled)
        self.assertNotIn('observed_initial_routes', absent[0].network.shared_approach)
        without_routes = self.initial(enabled=False, transform=lambda raw: raw.pop('vehicle_routes'))
        self.assertEqual(disabled, without_routes)

    def test_flag_requires_explicit_boolean(self):
        for value in (1, 'true', {}, []):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'boolean'):
                self.initial(enabled=value)
        with self.assertRaisesRegex(ValueError, 'pinned shared_approach'):
            shared_approach.configure(NS(), {'urban': {'shared_approach_observed_initial_routes': True}}, {})

    def test_enabled_configuration_rejects_disconnected_or_backward_branch(self):
        parse = shared_approach.ET.parse
        for mutation in ('decision_after_branch', 'disconnected_path'):
            def changed(path):
                tree = parse(path)
                if mutation == 'decision_after_branch':
                    tree.find("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='1134']").set('pos', '2000')
                else:
                    tree.find("./links/link[@no='10637']/toLinkEndPt").set('lane', '71 1')
                return tree
            with self.subTest(mutation=mutation), patch.object(shared_approach.ET, 'parse', side_effect=changed):
                with self.assertRaises(ValueError):
                    self.initial()

    def test_route_capture_must_be_complete_and_join_the_paused_snapshot(self):
        for mutate in (lambda r: r.pop('vehicle_routes'),
                       lambda r: r['vehicle_routes'].update(complete=False),
                       lambda r: r['vehicle_routes'].update(sim_sec_after=901),
                       lambda r: r['vehicle_routes']['records'][0].update(veh_no=999999)):
            with self.assertRaises(ValueError):
                self.initial(transform=mutate)

    def test_inconsistent_observed_routes_fail_before_any_state_is_seeded(self):
        def alter(raw, changes=None, position=None):
            vehicle = next(v for v in raw['vehicle_records']['records'] if v['link_no'] == 69)
            route = next(r for r in raw['vehicle_routes']['records'] if r['veh_no'] == vehicle['veh_no'])
            if changes:
                route.update(changes)
            if position is not None:
                vehicle['position_m'] = position
        for changes, position in (({'route_decision_no': 1135}, None),
                                  ({'route_no': 9}, None),
                                  ({'route_decision_type': 'DYNAMIC'}, None),
                                  ({'route_decision_no': None, 'route_no': None, 'route_decision_type': None}, 100.),
                                  (None, 2000.), (None, 10.)):
            with self.subTest(changes=changes, position=position), self.assertRaises(ValueError):
                self.initial(transform=lambda raw: alter(raw, changes, position))


if __name__ == '__main__':
    unittest.main()
