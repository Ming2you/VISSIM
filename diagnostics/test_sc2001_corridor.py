"""Physical projection, calibrated routing, finite receiving and cohort closure."""
from pathlib import Path
import copy
import json
import math
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'diagnostics'), str(ROOT / 'vendor/NumSim-mine')]
from evaluation.controllers import sc2001_corridor as corridor
from evaluation.controllers import area_runtime, shared_approach
from evaluation.controllers.control_area_objective import ModelAreaLedger, emit_transfer


def fixture(time=900):
    from test_shared_approach import fixture as shared_fixture
    from test_observation_projection import ActualInstalledProjection as Harness
    from src.models.state import TrafficState
    cfg, old, raw, detectors, *_, control = shared_fixture(time)
    before_inventory = area_runtime.model_inventory(old, cfg)
    tuning = {'urban': {'sc2001_corridor': 'diagnostics/sc2001_corridor_nc13.json'}}
    metadata = corridor.configure(cfg, tuning, raw)
    detectors, raw, projection = corridor.prepare_projection(cfg, detectors, raw)
    calibration = Harness.adapter.deep_update(dict(Harness.calibration), {})
    with patch.object(Harness.adapter, 'build_local_observation_summary', Harness.patched_summary):
        state = Harness.adapter.traffic_state_from_vissim(raw, cfg, TrafficState, detectors, calibration)
    area_runtime.pair_initial_arrival_releases(state, cfg)
    shared_approach.initialize(state, cfg, raw, detectors)
    metadata.update(corridor.initialize(state, cfg, raw, detectors))
    return cfg, state, raw, detectors, control, metadata, before_inventory


def ready_now(state, index):
    for branches in state.sc2001_corridor_state['bins'].values():
        for branch, bins in branches.items():
            branches[branch] = {index: sum(bins.values())}


class CorridorTests(unittest.TestCase):
    def test_actual_snapshot_reprojection_preserves_stock_and_corrects_loop(self):
        for time in (900, 3300):
            cfg, state, raw, detectors, _, metadata, before = fixture(time)
            spec = cfg.network.sc2001_corridor
            actual = sum(raw['vehicle_records']['full_network_link_counts'].get(key, 0) for key in spec['initial_physical_links'])
            self.assertEqual(metadata['sc2001_initial_veh'], actual)
            self.assertAlmostEqual(corridor._tracked(state.sc2001_corridor_state), actual)
            self.assertAlmostEqual(sum(area_runtime.model_inventory(state, cfg).values()), sum(before.values()))
            assignment = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
            for link in spec['initial_physical_links']:
                self.assertAlmostEqual(sum(assignment.get(link, {}).values()), raw['vehicle_records']['full_network_link_counts'].get(link, 0))
                self.assertTrue(all(stock == 'storage:SC2001_S_out' for stock in assignment.get(link, {})))
            self.assertNotIn(spec['storage'], state.urban_storage_release_buffer)
            self.assertEqual(detectors['link_to_origins']['78'], [spec['storage']])

    def test_frozen_empirical_denominators_censoring_and_rare_branch(self):
        cfg, *_ = fixture()
        calibration = cfg.network.sc2001_corridor['calibration']
        prior = calibration['priors']
        self.assertEqual((prior['W']['completed_denominator'], prior['N']['completed_denominator'], prior['E_SC2002']['completed_denominator']), (323, 337, 179))
        self.assertEqual(prior['initial_unknown_origin']['completed_denominator'], 839)
        self.assertEqual(prior['initial_unknown_origin']['unresolved_or_censored'], 8)
        self.assertEqual(prior['E_SC2002']['counts']['R_D_W'], 3)
        self.assertEqual(prior['W']['shares']['R_D_W'], 0)
        self.assertGreater(prior['W']['wilson_95_intervals_conditional_on_completed']['R_D_W'][1], 0)
        self.assertFalse(calibration['runtime_reads_training_fzp'])

    def test_geometric_travel_capacity_units_and_single_outward_boundary(self):
        cfg, *_ = fixture()
        spec = cfg.network.sc2001_corridor
        self.assertAlmostEqual(spec['capacity_veh'], spec['length_m']/1000*2*168.18, places=5)
        self.assertGreater(corridor._remaining(spec['branches']['R_D_E']), 568)
        self.assertLess(corridor._remaining(spec['branches']['R_D_E']), 569)
        self.assertGreater(corridor._remaining(spec['branches']['outside_125']), 891)
        self.assertLess(corridor._remaining(spec['branches']['outside_125']), 892)
        self.assertTrue(spec['branches']['R_D_E']['target_inside'])
        self.assertTrue(spec['branches']['R_D_W']['target_inside'])
        self.assertFalse(spec['branches']['outside_125']['target_inside'])
        self.assertEqual({key: value['lanes'] for key, value in spec['branches'].items()}, {'R_D_E': 1, 'R_D_W': 1, 'outside_125': 3})

    def test_full_receiving_ramp_retains_its_origin_cohorts(self):
        cfg, state, _, _, control, *_ = fixture()
        index = round(state.time_sec/cfg.simulation.T_u_sec)
        ready_now(state, index)
        state.ramp_queue['R_D_E'] = cfg.network.ramp_queue_cap('R_D_E')
        before = corridor._tracked(state.sc2001_corridor_state)
        result = corridor.advance(state, control, None, cfg, index)
        self.assertEqual(result['sc2001_accepted_by_branch']['R_D_E'], 0)
        self.assertGreater(result['sc2001_accepted_by_branch']['outside_125'], 0)
        self.assertAlmostEqual(corridor._tracked(state.sc2001_corridor_state), before-result['sc2001_departed_veh'])

    def test_accepted_source_prior_preserves_origin_without_reapplying_stock(self):
        cfg, state, _, _, control, *_ = fixture()
        index = round(state.time_sec/cfg.simulation.T_u_sec)
        corridor.advance(state, control, None, cfg, index)
        stock = cfg.network.sc2001_corridor['storage']
        amount = 12.3
        state.urban_link_storage[stock] -= amount  # exact caller accepted mutation
        self.assertTrue(corridor.receive_accepted(state, cfg, 'SC2001_E_SC2002_to_S', amount, index))
        bins = state.sc2001_corridor_state['bins']['E_SC2002']
        self.assertAlmostEqual(sum(bins['R_D_W'].values()), amount*3/179)
        self.assertAlmostEqual(sum(bins['R_D_E'].values()), amount*19/179)
        self.assertAlmostEqual(sum(bins['outside_125'].values()), amount*157/179)
        with self.assertRaisesRegex(ValueError, 'exactly once'):
            corridor.receive_accepted(state, cfg, 'SC2001_E_SC2002_to_S', amount, index)

    def test_450_seconds_explicit_accepted_inflows_close_every_step(self):
        cfg, state, _, _, control, *_ = fixture()
        # Keep real snapshot occupancy; feed explicit test accepted movement
        # pulses. This tests local physics, not whole-network demand coverage.
        inventory = area_runtime.model_inventory(state, cfg)
        state._control_area_ledger = ModelAreaLedger({key: {'inside': value, 'outside': 0.} for key, value in inventory.items()})
        start = round(state.time_sec/cfg.simulation.T_u_sec)
        movements = list(cfg.network.sc2001_corridor['incoming_movements'])
        initial, generated, exits = sum(inventory.values()), 0., 0.
        for index in range(start, start+90):
            result = corridor.advance(state, control, None, cfg, index)
            exits += result['sc2001_external_exit_veh']
            self.assertLess(abs(result['sc2001_mass_residual_veh']), 1e-7)
            storage = cfg.network.sc2001_corridor['storage']
            admitted = min(1.4, max(0., state.urban_link_storage[storage]))
            state.urban_link_storage[storage] -= admitted
            emit_transfer(state, cfg, None, 'storage:'+storage, admitted, source_inside=True, target_inside=True)
            corridor.receive_accepted(state, cfg, movements[(index-start)%3], admitted, index)
            generated += admitted
            state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state, cfg))
        self.assertGreater(state.sc2001_corridor_state['departed_veh'], 0)
        self.assertAlmostEqual(sum(area_runtime.model_inventory(state, cfg).values()) - initial, generated-exits, places=7)
        self.assertAlmostEqual(state._control_area_ledger.ttd_veh, exits)
        self.assertLessEqual(state.ramp_queue['R_D_E'], cfg.network.ramp_queue_cap('R_D_E'))

    def test_common_lane_service_is_bounded_and_candidates_are_independent(self):
        cfg, state, _, _, control, *_ = fixture()
        index = round(state.time_sec/cfg.simulation.T_u_sec)
        ready_now(state, index)
        one, two = state.copy(), state.copy()
        result = corridor.advance(one, control, None, cfg, index)
        self.assertEqual(result, corridor.advance(two, control, None, cfg, index))
        self.assertLessEqual(result['sc2001_departed_veh'], cfg.network.movement_capacity_veh_h*2*cfg.simulation.T_u_h)
        self.assertEqual(state.sc2001_corridor_state['last_step'], index-1)
        with self.assertRaisesRegex(ValueError, 'sequential'):
            corridor.advance(one, control, None, cfg, index)

    def test_flag_absent_is_identity_and_unknown_positive_origin_fails(self):
        from types import SimpleNamespace
        empty = SimpleNamespace(network=SimpleNamespace())
        self.assertEqual(corridor.configure(empty, {}, {}), {})
        detector, raw = {}, {}
        a, b, metadata = corridor.prepare_projection(empty, detector, raw)
        self.assertIs(a, detector); self.assertIs(b, raw); self.assertEqual(metadata, {})
        self.assertFalse(corridor.receive_accepted(None, empty, 'x', 1, 0))
        cfg, state, _, _, control, *_ = fixture()
        cfg.network.urban_movements['unresolved'] = {'receiving_link': 'SC2001_S_out'}
        with self.assertRaisesRegex(ValueError, 'calibrated origin'):
            corridor.receive_accepted(state, cfg, 'unresolved', 1, 180)

    def test_runtime_configuration_never_opens_training_fzp_or_audit(self):
        from test_shared_approach import fixture as shared_fixture
        cfg, _, raw, *_ = shared_fixture()
        original = Path.open
        def checked(path, *args, **kwargs):
            self.assertNotEqual(path.suffix.lower(), '.fzp')
            self.assertNotEqual(path.name, 'sc2001_corridor_audit.json')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', checked):
            corridor.configure(cfg, {'urban': {'sc2001_corridor': 'diagnostics/sc2001_corridor_nc13.json'}}, raw)

    def test_production_urban_body_matches_fixed_reference_when_corridor_flag_is_absent(self):
        from probe_area_endpoint import fixture as full_fixture
        from fixed_source_reference import function
        from evaluation.controllers import urban_flow_accounting
        from src.models.demand import DemandStep
        cfg, state, control, _ = full_fixture(dynamic_routes=True)
        del state._control_area_ledger
        cfg.network.control_area_enabled = False
        reference = function('evaluation/controllers/urban_flow_accounting.py', 'urban_substep_accounted', vars(urban_flow_accounting))
        first, second = state.copy(), state.copy()
        demand = DemandStep({}, {}, {})
        a = urban_flow_accounting.urban_substep_accounted(first, control, demand, cfg, 180)
        b = reference(second, control, demand, cfg, 180)
        self.assertEqual(a, b)
        self.assertEqual(first.__dict__, second.__dict__)

    def test_production_dispatcher_runs_physics_without_area_objective(self):
        from evaluation.controllers import urban_flow_accounting
        from test_observation_projection import ActualInstalledProjection as Harness
        from src.models import urban_queue_model as uqm
        from src.models.demand import DemandStep
        cfg, state, _, _, control, *_ = fixture()
        cfg.network.control_area_enabled = False
        def should_not_delegate(*args, **kwargs):
            raise AssertionError('Enabled corridor was delegated to a body without its physics')
        with patch.object(uqm, 'urban_substep', should_not_delegate), patch.object(Harness.adapter, '_fw_rebind', lambda *args: None):
            urban_flow_accounting.install(Harness.adapter, cfg)
            _, diagnostics = uqm.urban_substep(state, control, DemandStep({}, {}, {}), cfg, urban_step_index=180)
        self.assertIn('sc2001_storage_veh', diagnostics)
        self.assertEqual(state.sc2001_corridor_state['last_step'], 180)
        self.assertFalse(hasattr(state, '_control_area_ledger'))


if __name__ == '__main__':
    unittest.main()
