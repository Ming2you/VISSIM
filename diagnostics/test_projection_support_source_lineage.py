"""Pre-merge source identity uses all actual incoming canonical receivers."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
from diagnostics import test_route_choice_projection_claim as claim_fixture
from diagnostics.probe_model_area_integration import adapter
from evaluation.controllers import projection_support, area_runtime
from evaluation.controllers.control_area_objective import physical_membership_from_ledger


class SourceLineageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        claim_fixture.CorridorClaimTests.setUpClass()
        cls.fixture = claim_fixture.CorridorClaimTests
        cls.evidence = deepcopy(cls.fixture.support['evidence']['10379'])

    def validate(self, evidence=None, data=None, cfg=None, network=None):
        f = self.fixture
        import xml.etree.ElementTree as ET
        root = ET.parse(ROOT/f.support['network']['path']).getroot() if network is None else network
        links = {x.get('no'): x for x in root.findall('./links/link')}
        projection_support._reviewed_source_lineage('10379', 'SC11_to_SC1',
            self.evidence if evidence is None else evidence, f.support if data is None else data,
            links, root, f.cfg if cfg is None else cfg)

    def test_actual1350_and_observed_positive_record_project_once(self):
        self.validate()
        f = self.fixture
        initial = deepcopy(f.prepared)
        self.assertEqual(initial['vehicle_records']['full_network_link_counts'].get('10379', 0), 0)
        # Actual FZP record values, inserted with a fresh ID into a clearly
        # synthetic complete1350 test scene; this is not a claimed real1350 N.
        observed = json.loads((ROOT/'diagnostics/fixtures/link10379_observed_record.json').read_text())
        row = observed['record']
        synthetic = deepcopy(initial)
        record = {'veh_no': max(v['veh_no'] for v in synthetic['vehicle_records']['records'])+1,
            'link_no':10379, 'lane_no':row['lane'], 'position_m':row['position_m'],
            'speed_kph':row['speed_kph'], 'stopped':row['speed_kph']<5}
        synthetic['vehicle_records']['records'].append(record)
        synthetic['vehicle_records']['full_network_link_counts']['10379']=1
        synthetic['total_vehicles'] += 1
        for key in ('record_count','collection_count_before','collection_count_after'):
            synthetic['vehicle_records'][key] += 1
        synthetic['local_observation']['link_counts'].pop('10379', None)
        detectors, prepared, _ = projection_support.configure(f.cfg, f.tuning, f.detectors, synthetic)
        self.assertEqual(detectors['link_to_origins']['1210008203'], f.detectors['link_to_origins']['1210008203'])
        from src.models.state import TrafficState
        calibration = adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
        calibration = adapter.deep_update(calibration, f.tuning.get('calibration_override', {}))
        state = adapter.traffic_state_from_vissim(prepared, f.cfg, TrafficState, detectors, calibration)
        assigned = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
        self.assertEqual(assigned['10379'], {'storage:SC11_to_SC1':1.})
        physical = physical_membership_from_ledger(json.loads((ROOT/'diagnostics/control_area_membership.json').read_text()))
        ledger = area_runtime.seed_from_projection(state, f.cfg, physical)
        self.assertEqual((ledger.entered_veh,ledger.ttd_veh,ledger.event_count),(0,0,0))
        ledger.assert_stocks(area_runtime.model_inventory(state,f.cfg))
        self.assertEqual(initial, f.prepared)
        self.assertEqual(f.source_path.read_bytes(), f.source_bytes)

    def test_exact_incoming_set_and_target_required(self):
        row = deepcopy(self.evidence); row['source_lineage']['upstream_receivers'].pop('10378')
        with self.assertRaisesRegex(ValueError,'upstream connector set differs'): self.validate(row)
        data = deepcopy(self.fixture.support); data['link_to_storage']['10374']='in_SC1_E'
        with self.assertRaisesRegex(ValueError,'upstream support target differs'): self.validate(data=data)
        cfg = deepcopy(self.fixture.cfg)
        cfg.network.urban_movements['SC11_N_SC5_to_W_SC1']['receiving_link']='in_SC1_E'
        with self.assertRaisesRegex(ValueError,'another active accepted receiver'): self.validate(cfg=cfg)

    def test_native_source_path_and_pinned_contract_required(self):
        row = deepcopy(self.evidence); row['source_lineage']['native_route_ids']=['1105:1']
        with self.assertRaisesRegex(ValueError,'native route differs'): self.validate(row)
        row = deepcopy(self.evidence); row['source_lineage']['canonical_contract']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'fingerprint differs'): self.validate(row)
        row = deepcopy(self.evidence); row['source_lineage']['source_link']='236'
        with self.assertRaisesRegex(ValueError,'connector path differs'): self.validate(row)

    def test_new_source_input_cannot_be_silently_merged(self):
        import xml.etree.ElementTree as ET
        network=ET.parse(ROOT/self.fixture.support['network']['path']).getroot()
        ET.SubElement(network.find('./vehicleInputs'),'vehicleInput',{'no':'synthetic','link':'1220008203'})
        with self.assertRaisesRegex(ValueError,'independent input or signal'): self.validate(network=network)


if __name__ == '__main__': unittest.main()
