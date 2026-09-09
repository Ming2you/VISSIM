"""Actual stopped-1050 observation and current production support regression.

This integration test reads the recorded beta0 failure and all31 pure-n7
snapshots. It never contacts VISSIM or reads future trajectories. The three
1050/guard tests also run from the separate receiver_turns_v1 fixture archive.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers import area_runtime, projection_support
from evaluation.controllers.runtime_setup import configure_runtime

SUPPORT = ROOT / 'diagnostics/physical_projection_support_635_proposal.json'
PROOF = ROOT / 'diagnostics/unresolved_projection_support_review.json'
CONFIG = ROOT / 'diagnostics/fixtures/area_baseline_before_route_choice_beta0.json'
LIVE = ROOT / 'evaluation/runs/codex_area_beta0_s13_20260910/decisions_codex_area_beta0_s13_20260910'
PURE = ROOT / 'evaluation/runs/codex_n7_pure_s13_20260910/decisions_codex_n7_pure_s13_20260910'
FIXTURE_ENV = 'VISSIM_RECEIVER_FIXTURE_ROOT'


def fixture_input(path, *, raw=False):
    # Baseline configuration is a tracked immutable diagnostic fixture.
    if path == CONFIG:
        return path
    location = os.environ.get(FIXTURE_ENV)
    if not location:
        return path
    destination = Path(location).resolve()
    if not (destination/'restoration.json').is_file():
        raise FileNotFoundError(f'{FIXTURE_ENV} requires a verified restored fixture')
    result = destination/('raw' if raw else 'relocated')/path.relative_to(ROOT)
    if not result.is_file():
        raise FileNotFoundError(f'Receiver regression input is not in the fixture: {path.relative_to(ROOT)}')
    return result


def build_actual(path):
    """Same canonical cfg/runtime entry as main, with the actual previous action."""
    tuning = adapter.load_optional_json(str(fixture_input(CONFIG)))
    writer = tuning['actuation']['real_world_signal_control']['offset_writer']
    with patch.dict(os.environ, {'RW_OFFSET_WRITER': writer}):
        return _build_actual(path, tuning)


def _build_actual(path, tuning):
    raw = json.loads(fixture_input(path).read_text(encoding='utf-8'))
    previous = path.with_name(f"action_{int(raw['sim_sec'])-150:06d}.json")
    previous = fixture_input(previous)
    if not previous.exists():
        raise FileNotFoundError(f'Actual previous control is required: {previous}')
    adapter.install_config_switches(tuning)
    calibration = adapter.load_optional_json(str(ROOT / 'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
    calibration = adapter.deep_update(calibration, tuning.get('calibration_override', {}))
    mapping = adapter.load_optional_json(str(ROOT / tuning['mapping_json']))
    detectors = adapter.load_optional_json(str(ROOT / tuning['detector_mapping_json']))
    detectors, _ = adapter.filter_midblock_links_from_detector_mapping(detectors, tuning)
    _, _, _, _, TrafficState, _ = adapter.repo_imports(ROOT / 'vendor/NumSim-mine')
    cfg = adapter.build_config(ROOT / 'vendor/NumSim-mine', 150, raw['sim_period_sec'],
        'fast-smoke', calibration, tuning, local_observation=True, flagship=True)
    state, detectors, metadata = configure_runtime(adapter, cfg, tuning, mapping, raw,
        str(previous), detectors, calibration, TrafficState)
    metadata['diagnostic_snapshot_path'] = path.relative_to(ROOT).as_posix()
    metadata['diagnostic_snapshot_sha256'] = hashlib.sha256(fixture_input(path, raw=True).read_bytes()).hexdigest()
    metadata['diagnostic_run'] = path.parent.parent.name
    return cfg, state, detectors, raw, metadata


class ReceiverTurnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before_sha = hashlib.sha256(SUPPORT.read_bytes()).hexdigest()
        cls.support = json.loads(SUPPORT.read_text(encoding='utf-8'))
        cls.proof = json.loads(PROOF.read_text(encoding='utf-8'))
        cls.inside = set(json.loads((ROOT/'diagnostics/control_area_membership.json').read_text(encoding='utf-8'))['inside_links'])
        cls.actual = build_actual(LIVE / 'state_001050.json')
        cls.results = []

    @classmethod
    def tearDownClass(cls):
        after = hashlib.sha256(SUPPORT.read_bytes()).hexdigest()
        if after != cls.before_sha:
            raise AssertionError('Support changed during this regression')
        output_name = 'projection_support_receiver_regression_portable.json' if os.environ.get(FIXTURE_ENV) else 'projection_support_receiver_regression.json'
        (ROOT/'diagnostics'/output_name).write_text(json.dumps({
            'support_sha256': after, 'proof_sha256': hashlib.sha256(PROOF.read_bytes()).hexdigest(),
            'actual_1050_sha256': hashlib.sha256(fixture_input(LIVE/'state_001050.json', raw=True).read_bytes()).hexdigest(),
            'remaining_unresolved_positive_guard_count': len(cls.support['full_area_coverage_audit']['unresolved_physical_links']),
            'snapshots': cls.results,
        }, indent=2)+'\n', encoding='utf-8')

    def assert_projection_closure(self, built):
        cfg, state, detectors, raw, metadata = built
        ledger = state._control_area_ledger
        ledger.assert_stocks(area_runtime.model_inventory(state, cfg))
        expected = sum(count for key, count in raw['vehicle_records']['full_network_link_counts'].items() if key in self.inside)
        actual = sum(row['inside'] for row in ledger.stocks.values())
        self.assertAlmostEqual(actual, expected, places=7)
        self.assertEqual((ledger.entered_veh, ledger.ttd_veh, ledger.event_count), (0, 0, 0))
        assigned = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
        physical = raw['vehicle_records']['full_network_link_counts']
        for key in self.support['link_to_storage']:
            self.assertAlmostEqual(sum(assigned.get(key, {}).values()), physical.get(key, 0), places=7, msg=key)
        self.results.append({'run': metadata['diagnostic_run'],
            'snapshot': metadata['diagnostic_snapshot_path'], 'snapshot_sha256': metadata['diagnostic_snapshot_sha256'],
            'sim_sec': raw['sim_sec'],
            'raw_inside_veh': expected, 'model_inside_veh': actual,
            'initial_entry_veh': ledger.entered_veh, 'initial_exit_veh': ledger.ttd_veh})

    def test_actual_1050_is_single_transit_stock_without_initial_entry(self):
        cfg, state, detectors, raw, _ = self.actual
        self.assertEqual(hashlib.sha256(fixture_input(LIVE/'state_001050.json', raw=True).read_bytes()).hexdigest(), self.proof['source_sha256']['snapshot'])
        self.assert_projection_closure(self.actual)
        assignment = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
        self.assertEqual(assignment['10421'], {'storage:SC5_to_SC11': 1.0})
        self.assertEqual(detectors['transit_storage_projection']['10421'], 'SC5_to_SC11')
        self.assertNotIn('10421', detectors['link_to_movements'])

    def test_removing_proved_support_reproduces_original_failure(self):
        cfg, _, detectors, raw, _ = self.actual
        missing = deepcopy(self.support)
        missing['link_to_storage'].pop('10421')
        missing['full_area_coverage_audit']['unresolved_physical_links'].append('10421')
        with tempfile.TemporaryDirectory(prefix='receiver-regression-', dir=ROOT/'diagnostics') as tmp:
            path = Path(tmp)/'missing_support.json'
            path.write_text(json.dumps(missing), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, "unresolved physical stock support.*10421.*1"):
                projection_support.configure(cfg, {'observation': {'physical_support_repair': str(path)}}, detectors, raw)

    def test_all_remaining_unknown_links_still_fail_before_mutation(self):
        cfg, _, detectors, raw, _ = self.actual
        unresolved = self.support['full_area_coverage_audit']['unresolved_physical_links']
        self.assertEqual(set(unresolved), set(self.proof['remaining_unresolved'])-set(self.support['link_to_storage']))
        for key in unresolved:
            with self.subTest(link=key):
                altered = deepcopy(raw)
                records = altered['vehicle_records']['records']
                records.append({'veh_no': max(row['veh_no'] for row in records)+1,
                    'link_no': int(key), 'lane_no': 1, 'position_m': 0.1, 'speed_kph': 0., 'stopped': True})
                altered['vehicle_records']['full_network_link_counts'][key] = altered['vehicle_records']['full_network_link_counts'].get(key, 0)+1
                for field in ('collection_count_before', 'collection_count_after', 'record_count'):
                    altered['vehicle_records'][field] = len(records)
                before = deepcopy(altered)
                with self.assertRaisesRegex(ValueError, 'unresolved physical stock support.*'+key):
                    projection_support.configure(cfg, {'observation': {'physical_support_repair': str(SUPPORT)}}, detectors, altered)
                self.assertEqual(altered, before)

    def test_old31_pure_snapshots_keep_exact_physical_area_stock(self):
        paths = sorted(PURE.glob('state_*.json'))
        paths = [p for p in paths if 900 <= int(p.stem.split('_')[1]) <= 5400]
        self.assertEqual(len(paths), 31)
        for path in paths:
            with self.subTest(snapshot=path.name):
                self.assert_projection_closure(build_actual(path))


if __name__ == '__main__':
    unittest.main(verbosity=2)
