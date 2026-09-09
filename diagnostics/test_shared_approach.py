"""Shared input/routing and physical observation coverage regressions."""
from pathlib import Path
import copy
import json
import math
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


if __name__ == '__main__':
    unittest.main()
