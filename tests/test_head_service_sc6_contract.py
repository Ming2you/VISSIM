"""SC6 short-green evidence belongs only to its proven left-turn lane."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from evaluation.controllers import head_service_resources as hs
from evaluation.controllers.signal_head_observation import green_exposure_windows

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / 'diagnostics/repin_v3c3_review_20261001/urban_rm269/sc6_queue'


class ServiceSC6ContractTest(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads((CASE / 'head_resources.json').read_bytes())
        self.tuning = json.loads((CASE / 'service_config.json').read_bytes())
        self.tuning['execution']['native_signal_record'] = False
        self.raw = {'network_path': str(ROOT / self.doc['network']['path'])}
        self.plan = json.loads((ROOT / 'outputs/signal_group_actuation_plan_mainline_20260825.json').read_bytes())
        # configure() runs before corridor alias removal. Reconstruct that
        # lifecycle stage, as in the existing47/SC101 contract tests.
        movements = {}
        for row in self.doc['resources'].values():
            movements.update({m: {**v, 'beta': 1.} for m, v in row['members'].items()})
            movements.update({m: {**v['expected_spec'], 'beta': 1.} for m, v in row.get('disjoint_consumers', {}).items()})
            for detail in row.get('disjoint_consumers', {}).values():
                if 'downstream_choice' in detail:
                    choice = json.loads((ROOT / detail['downstream_choice']['path']).read_bytes())
                    turn = next(t for t in choice['incoming_turns'].values()
                                if t['keep'] in movements and t['connector'] == detail['path'][1])
                    movements[turn['remove']] = {**movements[turn['keep']], 'receiving_link': choice['bypass_storage']}
        self.cfg = SimpleNamespace(network=SimpleNamespace(urban_movements=movements,
            urban_link_storage_veh={r['receiver']: 100. for r in self.doc['resources'].values()}))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'contract.json'
        self.tuning['urban']['capacity']['head_resource_contract'] = str(self.path)

    def configure(self):
        self.path.write_text(json.dumps(self.doc))
        return hs.configure(self.cfg, self.tuning, self.raw, self.plan)

    def test_geometry_accepts_left_only_and_keeps_through_observer(self):
        self.assertEqual(self.configure()['physical_head_resource_contract_enabled'], 1.)
        self.assertEqual(green_exposure_windows(self.cfg, ('1210018302', 'p2')), 4)
        self.assertEqual(green_exposure_windows(self.cfg, ('1210018302', 'p1')), 0)
        self.assertEqual(green_exposure_windows(self.cfg, ('1220021201', 'p4')), 0)

    def test_old_v10_still_supported(self):
        self.doc['schema'] = 'physical-head-resource-join/v10'
        del self.doc['resources']['10206']
        self.assertEqual(self.configure()['physical_head_resource_contract_enabled'], 1.)

    def test_cannot_assign_left_head_to_through_lane(self):
        self.doc['resources']['10206']['heads'][0]['lane'] = 3
        with self.assertRaisesRegex(ValueError, 'head/lane'):
            self.configure()

    def test_cannot_assign_left_measurement_to_through_movement(self):
        row = self.doc['resources']['10206']
        row['members'] = {'SC6_S_SC12_to_N_SC103': next(iter(row['members'].values()))}
        with self.assertRaisesRegex(ValueError, 'incoming route proof'):
            self.configure()

    def test_unproven_duplicate_consumer_rejected(self):
        self.cfg.network.urban_movements['unproven'] = copy.deepcopy(
            self.cfg.network.urban_movements['SC6_S_SC12_to_W_SC5'])
        with self.assertRaisesRegex(ValueError, 'another model consumer'):
            self.configure()

    def test_old_schema_cannot_silently_acquire_new_resource(self):
        self.doc['schema'] = 'physical-head-resource-join/v10'
        with self.assertRaisesRegex(ValueError, 'Unreviewed'):
            self.configure()


if __name__ == '__main__':
    unittest.main()
