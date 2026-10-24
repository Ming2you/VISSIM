"""Integrated per-cell counts versus immutable pre-integration OFF references."""
import copy
from contextlib import contextmanager
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'diagnostics'), str(ROOT / 'vendor/NumSim-mine')]
from fixed_source_reference import function
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts
from src.models.state import ExperimentConfig, TrafficState

REFERENCE = {name: function('evaluation/controllers/vissim_stackelberg_adapter.py', name, vars(adapter))
             for name in ('traffic_state_from_vissim', '_freeway_vehicle_count_by_link',
                          'install_vissim_calibration_runtime_patches')}


@contextmanager
def preserve_getters():
    # Calibration legitimately replaces these two class methods; isolate tests.
    with patch.object(TrafficState, 'freeway_vehicle_count_by_link', TrafficState.freeway_vehicle_count_by_link), \
         patch.object(TrafficState, 'total_freeway_vehicles', TrafficState.total_freeway_vehicles):
        yield


def synthetic():
    cfg = ExperimentConfig()
    cfg.network.freeway_segment_length_profile_km = {
        key: [0.2, 0.41, 0.7, 1.1] for key in cfg.network.freeway_links}
    cfg.network.freeway_segment_lanes = {key: [1, 2, 3, 4] for key in cfg.network.freeway_links}
    raw = {'sim_sec': 900, 'freeway_segments': {key: [
        {'count': count, 'speed_sum': count * speed, 'length_km': length, 'lanes': 4}
        for count, speed, length in zip((1, 9, 20, 3), (0, 25, 60, 40), (0.2, 0.41, 0.7, 1.1))]
        for key in cfg.network.freeway_links}}
    return cfg, raw


class FreewayInitialCountTests(unittest.TestCase):
    def test_each_cell_preserves_raw_n_and_uses_actual_continuity_coordinates(self):
        cfg, raw = synthetic()
        cfg.network.physical_vehicle_counts = True
        with preserve_getters():
            state = adapter.traffic_state_from_vissim(raw, cfg, TrafficState)
            for key, counts in continuity_vehicle_counts(state, cfg).items():
                for index, (count, row) in enumerate(zip(counts, raw['freeway_segments'][key])):
                    self.assertAlmostEqual(count, row['count'], places=12)
                    self.assertEqual(state.freeway_speed[key][index], row['speed_sum'] / row['count'])
                    rho = row['count'] / (cfg.network.freeway_segment_length_km * (index + 1))
                    self.assertEqual(state.freeway_density[key][index], rho)
                    self.assertEqual(state.freeway_flow[key][index], rho * state.freeway_speed[key][index] * (index + 1))
            self.assertEqual(adapter._freeway_vehicle_count_by_link(state, cfg), continuity_vehicle_counts(state, cfg))
            # Observed physical length profiles remain available to travel/speed
            # calculations; no global or link-total constant was subtracted.
            self.assertEqual(cfg.network.freeway_segment_length_profile_km['FW_E'], [.2, .41, .7, 1.1])

    def test_absent_and_false_leave_every_projected_state_field_identical(self):
        for flag in (None, False):
            cfg, raw = synthetic()
            if flag is not None:
                cfg.network.physical_vehicle_counts = flag
            expected = REFERENCE['traffic_state_from_vissim'](copy.deepcopy(raw), copy.deepcopy(cfg), TrafficState)
            expected_counts = REFERENCE['_freeway_vehicle_count_by_link'](expected, cfg)
            with preserve_getters():
                actual = adapter.traffic_state_from_vissim(copy.deepcopy(raw), copy.deepcopy(cfg), TrafficState)
                self.assertEqual(vars(actual), vars(expected))
                self.assertEqual(adapter._freeway_vehicle_count_by_link(actual, cfg), expected_counts)

    def test_calibrated_getter_and_adapter_have_same_counts_for_nonuniform_lengths(self):
        cfg, raw = synthetic()
        cfg.network.physical_vehicle_counts = True
        calibration = {'physical_inventory': {'freeway_segment_length_profile_km': cfg.network.freeway_segment_length_profile_km}}
        with preserve_getters():
            metadata = adapter.install_vissim_calibration_runtime_patches(cfg, calibration)
            self.assertEqual(metadata['calibration_state_vehicle_count_patch_installed'], 1)
            state = adapter.traffic_state_from_vissim(raw, cfg, TrafficState)
            expected = continuity_vehicle_counts(state, cfg)
            self.assertEqual(state.freeway_vehicle_count_by_link(cfg.network), expected)
            self.assertEqual(adapter._freeway_vehicle_count_by_link(state, cfg), expected)
            # Candidate spillback can make effective lanes fractional; N must
            # still use those same lanes, not a one-lane floor or nominal lanes.
            state.freeway_effective_lanes['FW_E'][1] = .25
            self.assertEqual(state.freeway_vehicle_count_by_link(cfg.network), continuity_vehicle_counts(state, cfg))

    def test_calibrated_getter_false_is_exactly_legacy(self):
        cfg, raw = synthetic()
        calibration = {'physical_inventory': {'freeway_segment_length_profile_km': cfg.network.freeway_segment_length_profile_km}}
        for flag in (None, False):
            if flag is not None:
                cfg.network.physical_vehicle_counts = flag
            with patch.object(TrafficState, 'freeway_vehicle_count_by_link', TrafficState.freeway_vehicle_count_by_link), \
                 patch.object(TrafficState, 'total_freeway_vehicles', TrafficState.total_freeway_vehicles):
                expected_meta = REFERENCE['install_vissim_calibration_runtime_patches'](cfg, calibration)
                state = REFERENCE['traffic_state_from_vissim'](raw, cfg, TrafficState)
                expected = state.freeway_vehicle_count_by_link(cfg.network)
            with preserve_getters():
                self.assertEqual(adapter.install_vissim_calibration_runtime_patches(cfg, calibration), expected_meta)
                state = adapter.traffic_state_from_vissim(raw, cfg, TrafficState)
                self.assertEqual(state.freeway_vehicle_count_by_link(cfg.network), expected)

    def test_invalid_continuity_length_fails_instead_of_inventing_inventory(self):
        for length in (0, -1, math.nan, math.inf):
            cfg, raw = synthetic()
            cfg.network.physical_vehicle_counts = True
            cfg.network.freeway_segment_length_km = length
            with preserve_getters(), self.assertRaises(ValueError):
                adapter.traffic_state_from_vissim(raw, cfg, TrafficState)

    def test_real_n7_flag_off_entire_state_is_identical(self):
        from probe_model_area_integration import build_projected
        run = ROOT / 'evaluation/runs/codex_nc_s13_6056c94_20260909_retry/decisions_codex_nc_s13_6056c94_20260909_retry'
        cfg, _, detectors, _, raw, _, _ = build_projected(
            ROOT / 'evaluation/configs/n21_n7_20260908.json', run / 'state_000900.json', run / 'action_000001.json')
        for flag in (None, False):
            if flag is not None:
                cfg.network.physical_vehicle_counts = flag
            expected = REFERENCE['traffic_state_from_vissim'](copy.deepcopy(raw), copy.deepcopy(cfg), TrafficState, detectors)
            expected_count = REFERENCE['_freeway_vehicle_count_by_link'](expected, cfg)
            with preserve_getters():
                actual = adapter.traffic_state_from_vissim(copy.deepcopy(raw), copy.deepcopy(cfg), TrafficState, detectors)
                self.assertEqual(vars(actual), vars(expected))
                self.assertEqual(adapter._freeway_vehicle_count_by_link(actual, cfg), expected_count)


if __name__ == '__main__':
    unittest.main()
