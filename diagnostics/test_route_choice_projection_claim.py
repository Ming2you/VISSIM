"""A corridor claim cannot bypass physical-support validation by itself."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
from diagnostics.probe_model_area_integration import adapter, build_projected
from diagnostics.route_input_fixtures import decisions
from evaluation.controllers import area_runtime, projection_support, route_choice_corridor
from evaluation.controllers.control_area_objective import physical_membership_from_ledger


class CorridorClaimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder = decisions()
        cls.cfg, _, detectors, cls.tuning, _, _, metadata = build_projected(
            ROOT/'diagnostics/fixtures/area_baseline_before_route_choice_beta0.json', folder/'state_001200.json',
            folder/'action_001050.json', fixture_inputs=False)
        cls.source_path = folder/'state_001350.json'
        cls.source_bytes = cls.source_path.read_bytes()
        cls.raw = json.loads(cls.source_bytes)
        option = {'urban': {'route_choice_corridor': {
            'evidence_path': 'diagnostics/route_choice_corridor_ver2.json',
            'unknown_policy': 'error'}}}
        cls.before_detectors = deepcopy(detectors)
        detectors, _ = route_choice_corridor.configure(cls.cfg, option, cls.raw, detectors,
            per_lane_capacity_veh_h=metadata['movement_capacity_by_lanes_per_lane_veh_h'])
        cls.detectors, cls.prepared, _ = route_choice_corridor.prepare_projection(cls.cfg, detectors, cls.raw)
        cls.support = json.loads((ROOT/'diagnostics/physical_projection_support_635_proposal.json').read_text())
        import xml.etree.ElementTree as ET
        cls.links = {x.get('no'): x for x in ET.parse(ROOT/cls.support['network']['path']).getroot().findall('./links/link')}

    def guard(self, cfg=None, detectors=None, raw=None, support=None):
        raw = self.prepared if raw is None else raw
        return projection_support._verified_corridor_claims(
            self.cfg if cfg is None else cfg, self.detectors if detectors is None else detectors,
            raw, self.support if support is None else support, self.links,
            projection_support.complete_records(raw))

    def test_actual1350_three_on10634_project_once_and_initial_area_events_zero(self):
        detectors, prepared, metadata = projection_support.configure(self.cfg, self.tuning, self.detectors, self.prepared)
        self.assertIn('10634', metadata['verified_corridor_stock_links'])
        from src.models.state import TrafficState
        calibration = adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
        calibration = adapter.deep_update(calibration, self.tuning.get('calibration_override', {}))
        state = adapter.traffic_state_from_vissim(prepared, self.cfg, TrafficState, detectors, calibration)
        assignment = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
        self.assertEqual(assignment['10634'], {'storage:SC1004_E_choice': 3.})
        self.assertEqual(assignment['336'], {'storage:SC101_to_SC5': 1.})
        physical = physical_membership_from_ledger(json.loads((ROOT/'diagnostics/control_area_membership.json').read_text()))
        ledger = area_runtime.seed_from_projection(state, self.cfg, physical)
        self.assertEqual((ledger.entered_veh, ledger.ttd_veh, ledger.event_count), (0, 0, 0))
        self.assertAlmostEqual(sum(row['inside'] for row in ledger.stocks.values()),
            sum(physical[str(row['link_no'])] for row in self.raw['vehicle_records']['records']), places=7)
        self.assertEqual(self.raw, json.loads(self.source_bytes))
        self.assertEqual(self.source_path.read_bytes(), self.source_bytes)

    def test_marker_alone_or_forged_storage_rejected(self):
        cfg = deepcopy(self.cfg)
        del cfg.network.route_choice_corridor
        with self.assertRaisesRegex(ValueError, 'lacks configured projection'):
            self.guard(cfg=cfg)
        detectors = deepcopy(self.detectors)
        detectors['route_choice_verified_physical_stock']['10634'] = 'SC101_to_SC5'
        with self.assertRaisesRegex(ValueError, 'differs from configured partition'):
            self.guard(detectors=detectors)
        cfg = deepcopy(self.cfg)
        cfg.network.route_choice_corridor['prefix_storage'] = 'SC101_to_SC5'
        with self.assertRaisesRegex(ValueError, 'differs from pinned evidence'):
            self.guard(cfg=cfg)

    def test_source_proof_partition_and_mapping_tampering_rejected(self):
        for key, value in [('paths_validated', False), ('evidence_sha256', '0'*64), ('network_sha256', '0'*64)]:
            cfg = deepcopy(self.cfg)
            cfg.network.route_choice_corridor['physical_stock_validation'][key] = value
            with self.subTest(proof=key), self.assertRaisesRegex(ValueError, 'path/source proof differs'):
                self.guard(cfg=cfg)
        for field, value in [('transit_storage_projection', 'SC101_to_SC5'), ('link_to_origins', ['SC101_to_SC5']),
                             ('link_to_movements', [{'movement': 'fake', 'weight': 1}])]:
            detectors = deepcopy(self.detectors)
            detectors[field]['10634'] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'projection disagrees'):
                self.guard(detectors=detectors)
        prepared = deepcopy(self.prepared)
        prepared['local_observation']['link_counts']['10634'] = 2
        with self.assertRaisesRegex(ValueError, 'counts disagree'):
            self.guard(raw=prepared)

    def test_other_support_and_freeway_overlap_rejected(self):
        support = deepcopy(self.support)
        support['link_to_storage']['10634'] = 'SC101_to_SC5'
        with self.assertRaisesRegex(ValueError, 'conflicts with reviewed support'):
            self.guard(support=support)
        detectors = deepcopy(self.detectors)
        detectors.setdefault('ramp_link_to_queues', {})['10634'] = ['R_D_W']
        with self.assertRaisesRegex(ValueError, 'overlaps freeway/ramp'):
            self.guard(detectors=detectors)
        cfg = deepcopy(self.cfg)
        cfg.network.urban_link_storage_veh.pop('SC1004_E_choice')
        with self.assertRaisesRegex(ValueError, 'target is absent'):
            self.guard(cfg=cfg)

    def test_multi_corridor_validates_each_partition_and_rejects_overlap(self):
        cfg = deepcopy(self.cfg)
        part = cfg.network.route_choice_corridor
        cfg.network.route_choice_corridor = {'schema':'route-choice-corridors/v1','corridors':[part]}
        self.assertEqual(self.guard(cfg=cfg), self.guard())
        cfg.network.route_choice_corridor['corridors'].append(deepcopy(part))
        with self.assertRaisesRegex(ValueError, 'partition overlaps'):
            self.guard(cfg=cfg)

    def test_unclaimed_positive_links_still_fail_and_off_is_identity(self):
        raw = deepcopy(self.prepared)
        record = dict(veh_no=max(v['veh_no'] for v in raw['vehicle_records']['records'])+1,
                      link_no=10381, lane_no=1, position_m=1., speed_kph=20., stopped=False)
        raw['vehicle_records']['records'].append(record)
        raw['vehicle_records']['full_network_link_counts']['10381'] = 1
        for key in ('record_count', 'collection_count_before', 'collection_count_after'):
            raw['vehicle_records'][key] += 1
        with self.assertRaisesRegex(ValueError, 'unresolved physical stock support.*10381'):
            projection_support.configure(self.cfg, self.tuning, self.detectors, raw)
        detectors, observed, metadata = projection_support.configure(self.cfg, {}, self.detectors, raw)
        self.assertIs(detectors, self.detectors)
        self.assertIs(observed, raw)
        self.assertEqual(metadata, {})


if __name__ == '__main__':
    unittest.main()
