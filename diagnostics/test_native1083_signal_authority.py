"""Focused physical-source/topology tests; generation/projection integration is separate."""
import copy
import json
import os
from pathlib import Path
import pickle
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers import area_dynamic_routes, signal_actuation_contract
from evaluation.controllers.physical_movement_routes import configure_native_input_signal_authority as configure
from evaluation.controllers.projection_support import complete_records
from diagnostics.route_input_fixtures import fixture_path

EVIDENCE = 'diagnostics/native_input_1083_signal_authority_ver2.json'


def setup():
    tuning = adapter.load_optional_json(str(ROOT / 'diagnostics/area_candidate_configs/n7_area_beta0.json'))
    adapter.install_config_switches(tuning)
    calibration = adapter.load_optional_json(str(ROOT / 'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
    calibration = adapter.deep_update(calibration, tuning.get('calibration_override', {}))
    cfg = adapter.build_config(ROOT / 'vendor/NumSim-mine', 150, 5400, 'fast-smoke', calibration, tuning,
                               local_observation=True, flagship=True)
    detectors = adapter.load_optional_json(str(ROOT / tuning['detector_mapping_json']))
    raw = adapter.load_optional_json(str(fixture_path(ROOT / 'evaluation/runs/codex_area_observed_nc_s13_20260910/decisions_codex_area_observed_nc_s13_20260910/state_000900.json')))
    # Only real initializers needed to reach the explicitly named hook boundary;
    # there is no model rollout or replacement production method in this fixture.
    adapter.apply_movement_phase_correction(cfg, tuning)
    adapter.apply_nonexistent_movement_beta_zero(cfg, tuning)
    adapter.apply_dead_phase_beta_zero(cfg)
    adapter.install_urban_stopline_storage(cfg, tuning)
    adapter.install_measured_turn_beta(cfg, tuning)
    adapter.apply_dead_phase_beta_zero(cfg)
    adapter.install_leg_ramp_split_fold(cfg, tuning)
    detectors, _ = adapter.install_merged_movements(cfg, tuning, detectors)
    adapter.install_movement_capacity_by_lanes(cfg, tuning)
    adapter.install_native_signal_structure(cfg, tuning)
    with patch.dict(os.environ, {'RW_OFFSET_WRITER': 'experiment'}):
        signal_actuation_contract.configure(cfg, tuning, adapter.load_signal_group_actuation_plan())
    detectors, _ = area_dynamic_routes.configure(cfg, detectors, tuning, state_json=raw)
    tuning['urban']['movements']['native_input_signal_authority'] = EVIDENCE
    return cfg, tuning, detectors, raw


class Native1083SignalAuthorityTests(unittest.TestCase):
    def test_single_existing_p3_movement_preserves_capacity_receiver_and_other_origins(self):
        cfg, tuning, detectors, raw = setup()
        old = copy.deepcopy(cfg.network.urban_movements)
        capacities = dict(cfg.network.movement_capacity_by_movement_veh_h)
        storage = dict(cfg.network.urban_link_storage_veh)
        original_observation = pickle.dumps((detectors, raw))
        result, _ = configure(cfg, tuning, detectors, state_json=raw)
        kept = cfg.network.urban_movements['SC108_W_to_E_SC109']
        self.assertEqual(kept, dict(old['SC108_W_to_E_SC109'], beta=1.0))
        self.assertEqual(cfg.network.urban_link_storage_veh, storage)
        for name, spec in cfg.network.urban_movements.items():
            self.assertEqual(cfg.network.movement_capacity_by_movement_veh_h[name], capacities[name])
            if spec['origin'] != 'in_SC108_W': self.assertEqual(spec, old[name])
        self.assertEqual([name for name, spec in cfg.network.urban_movements.items() if spec['origin'] == 'in_SC108_W'], ['SC108_W_to_E_SC109'])
        self.assertFalse({'SC108_W_to_N_SC7', 'SC108_W_to_S'} & set(cfg.network.movement_merge_rename.values()))
        proof = cfg.network.native_input_signal_authority['inputs']['1083']
        self.assertEqual(proof['head_position_by_lane_m'], {'1': 94.77788130622324, '2': 95.05020601926469})
        self.assertEqual(proof['movement_area_route']['physical_turns'][0]['crossing_edges'], [])
        self.assertEqual(pickle.dumps((detectors, raw)), original_observation)
        self.assertEqual(result['link_to_origins']['21'], detectors['link_to_origins']['21'])
        # This initializer intentionally leaves complete-record partition to the
        # native-input implementation instead of pretending a whole-link join suffices.

    def test_off_is_exact_noop(self):
        cfg, tuning, detectors, raw = setup()
        del tuning['urban']['movements']['native_input_signal_authority']
        before = pickle.dumps((cfg, detectors, raw))
        result, meta = configure(cfg, tuning, detectors, state_json=raw)
        self.assertIs(result, detectors)
        self.assertEqual(meta, {})
        self.assertEqual(before, pickle.dumps((cfg, detectors, raw)))

    def test_other_origin_observation_and_external_demand_fail_before_commit(self):
        for source in ('origin', 'movement', 'demand'):
            cfg, tuning, detectors, raw = setup()
            if source == 'origin': detectors['link_to_origins']['379'] = ['in_SC108_W']
            elif source == 'movement': detectors['link_to_movements']['379'] = [{'movement': 'SC108_W_to_E_SC109', 'weight': 1.}]
            else: raw['demand']['urban_volume_vph_by_gate']['in_SC108_W'] = 1.
            before = pickle.dumps(cfg)
            with self.subTest(source=source), self.assertRaises(ValueError): configure(cfg, tuning, detectors, state_json=raw)
            self.assertEqual(pickle.dumps(cfg), before)

    def test_stale_phase_selected_clock_or_missing_sibling_fail_before_commit(self):
        for change in ('phase', 'clock', 'sibling'):
            cfg, tuning, detectors, raw = setup()
            if change == 'phase': cfg.network.urban_movements['SC108_W_to_E_SC109']['phase'] = 'SC108_p4'
            elif change == 'clock': cfg.network.signal_actuation_contract['nodes']['SC108']['phase_signal_groups']['p3'] = ['6']
            else: cfg.network.urban_movements.pop('SC108_W_to_S')
            before = pickle.dumps(cfg)
            with self.subTest(change=change), self.assertRaises(ValueError): configure(cfg, tuning, detectors, state_json=raw)
            self.assertEqual(pickle.dumps(cfg), before)

    def test_changed_native_head_evidence_rejected(self):
        cfg, tuning, detectors, raw = setup()
        doc = json.loads((ROOT / EVIDENCE).read_text(encoding='utf-8'))
        doc['inputs']['1083']['source_heads'][0]['pos'] = '200'
        with tempfile.TemporaryDirectory(dir=ROOT / 'diagnostics') as folder:
            path = Path(folder) / 'changed.json'
            path.write_text(json.dumps(doc), encoding='utf-8')
            tuning['urban']['movements']['native_input_signal_authority'] = str(path)
            with self.assertRaises(ValueError): configure(cfg, tuning, detectors, state_json=raw)

    def test_actual900_requires_both_pre_and_post_head_cohorts(self):
        cfg, tuning, detectors, raw = setup()
        configure(cfg, tuning, detectors, state_json=raw)
        positions = cfg.network.native_input_signal_authority['inputs']['1083']['head_position_by_lane_m']
        records = [r for r in complete_records(raw) if str(r['link_no']) in {'21', '10112'}]
        pre = [r['veh_no'] for r in records if str(r['link_no']) == '21' and r['position_m'] <= positions[str(r['lane_no'])]]
        post = [r['veh_no'] for r in records if r['veh_no'] not in pre]
        self.assertEqual(pre, [5517])
        self.assertEqual(set(post), {5422, 5429})
        self.assertEqual(len(pre) + len(post), len(records))
        self.assertFalse(set(pre) & set(post))


if __name__ == '__main__':
    unittest.main(verbosity=2)
