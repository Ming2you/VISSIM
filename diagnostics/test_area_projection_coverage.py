"""Exhaustive area classification and synthetic support for all new empty links."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'diagnostics'), str(ROOT/'vendor/NumSim-mine')]
from probe_sc2001_corridor_replay import fixture
from evaluation.controllers import projection_support, area_runtime


class CoverageTests(unittest.TestCase):
    def test_all_members_classified_and_no_freeway_or_ramp_duplication(self):
        coverage = json.loads((ROOT/'diagnostics/area_projection_coverage_635.json').read_text())
        area = json.loads((ROOT/'diagnostics/control_area_membership.json').read_text())
        self.assertEqual(set(coverage['by_physical_link']), set(area['inside_links']))
        self.assertEqual(sum(coverage['counts'].values()), 635)
        self.assertEqual(len(coverage['proposed_additions']), 170)
        self.assertEqual(len(coverage['unresolved']), 45)
        for link in ['10613', '10771']:
            self.assertEqual(coverage['by_physical_link'][link]['status'], 'supported_separate_freeway_chain')
            self.assertNotIn(link, coverage['proposed_additions'])
        self.assertNotIn('10627', coverage['proposed_additions'])
        self.assertIn('known_native_transfer_identity_conflicts', coverage['unresolved']['10627'])

    def test_all170_new_supports_project_one_synthetic_vehicle_once(self):
        from test_observation_projection import ActualInstalledProjection as Harness
        from src.models.state import TrafficState
        cfg, before, _, raw, detectors = fixture(return_detectors=True)
        proposal_path = 'diagnostics/physical_projection_support_635_proposal.json'
        coverage = json.loads((ROOT/'diagnostics/area_projection_coverage_635.json').read_text())
        synthetic = copy.deepcopy(raw)
        records = synthetic['vehicle_records']['records']
        largest = max(row['veh_no'] for row in records)
        for index, key in enumerate(coverage['proposed_additions'], 1):
            self.assertEqual(synthetic['vehicle_records']['full_network_link_counts'].get(key, 0), 0)
            records.append({'veh_no': largest+index, 'link_no': int(key), 'lane_no': 1,
                'position_m': 0.1, 'speed_kph': 30., 'stopped': False})
            synthetic['vehicle_records']['full_network_link_counts'][key] = 1
        for key in ('collection_count_before', 'collection_count_after', 'record_count'):
            synthetic['vehicle_records'][key] = len(records)
        tuning = {'observation': {'physical_support_repair': proposal_path}}
        detectors, synthetic, _ = projection_support.configure(cfg, tuning, detectors, synthetic)
        with patch.object(Harness.adapter, 'build_local_observation_summary', Harness.patched_summary):
            state = Harness.adapter.traffic_state_from_vissim(synthetic, cfg, TrafficState, detectors, Harness.calibration)
        assigned = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
        for link, row in coverage['proposed_additions'].items():
            self.assertEqual(assigned[link], {'storage:'+row['target_storage']: 1.})
        self.assertAlmostEqual(sum(area_runtime.model_inventory(state, cfg).values())-
            sum(area_runtime.model_inventory(before, cfg).values()), 170, places=7)

    def test_pure_six_positive_gaps_have_unique_endpoint_support(self):
        coverage = json.loads((ROOT/'diagnostics/area_projection_coverage_635.json').read_text())
        expected = {'10224': 'SC6_to_SC12', '10554': 'SC101_to_SC1', '10774': 'SC1001_W_out',
            '10273': 'SC109_to_SC16', '10579': 'SC105_to_SC1', '10294': 'SC108_to_SC7'}
        for key, target in expected.items():
            row = coverage['proposed_additions'][key]
            self.assertEqual(row['target_storage'], target)
            self.assertEqual(row['actual_downstream_origins'], [target])

    def test_positive_unresolved_support_fails_explicitly_in_production_guard(self):
        cfg, _, _, raw, detectors = fixture(return_detectors=True)
        records = raw['vehicle_records']['records']
        records.append({'veh_no': max(row['veh_no'] for row in records)+1, 'link_no': 336,
            'lane_no': 1, 'position_m': 0.1, 'speed_kph': 30., 'stopped': False})
        raw['vehicle_records']['full_network_link_counts']['336'] = 1
        for key in ('collection_count_before', 'collection_count_after', 'record_count'):
            raw['vehicle_records'][key] = len(records)
        tuning = {'observation': {'physical_support_repair': 'diagnostics/physical_projection_support_635_proposal.json'}}
        with self.assertRaisesRegex(ValueError, "unresolved physical stock support.*336"):
            projection_support.configure(cfg, tuning, detectors, raw)

    def test_existing_data_and_disabled_configuration_remain_exact(self):
        from fixed_source_reference import function
        cfg, _, _, raw, detectors = fixture(return_detectors=True)
        reference = function('evaluation/controllers/projection_support.py', 'configure', vars(projection_support))
        tuning = {'observation': {'physical_support_repair': 'diagnostics/physical_projection_support_ver2.json'}}
        self.assertEqual(reference(copy.deepcopy(cfg), tuning, detectors, raw), projection_support.configure(copy.deepcopy(cfg), tuning, detectors, raw))
        same_detectors, same_raw, metadata = projection_support.configure(cfg, {}, detectors, raw)
        self.assertIs(same_detectors, detectors); self.assertIs(same_raw, raw); self.assertEqual(metadata, {})


if __name__ == '__main__':
    unittest.main()
