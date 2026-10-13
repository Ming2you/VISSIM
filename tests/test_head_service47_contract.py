"""47 through head flow must not be shared with its disjoint lane1 right turn."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from evaluation.controllers import head_service_resources as hs

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT/'diagnostics/repin_v3c3_review_20261001/goal8_265/head47'

class Service47ContractTest(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads((CASE/'head_resources.json').read_bytes())
        self.tuning = json.loads((CASE/'config.json').read_bytes())
        self.tuning['execution']['native_signal_record'] = False
        self.raw = {'network_path': str(ROOT/self.doc['network']['path'])}
        self.plan = json.loads((ROOT/'outputs/signal_group_actuation_plan_mainline_20260825.json').read_bytes())
        movements = {}
        for row in self.doc['resources'].values():
            movements.update({m: {**v, 'beta': 1.} for m, v in row['members'].items()})
            movements.update({m: {**v['expected_spec'], 'beta': 1.} for m, v in row.get('disjoint_consumers', {}).items()})
            for detail in row.get('disjoint_consumers', {}).values():
                if 'downstream_choice' in detail:
                    choice = json.loads((ROOT/detail['downstream_choice']['path']).read_bytes())
                    turn = next(t for t in choice['incoming_turns'].values() if t['keep'] in movements and t['connector']==detail['path'][1])
                    movements[turn['remove']] = {**movements[turn['keep']], 'receiving_link': choice['bypass_storage']}
        self.cfg = SimpleNamespace(network=SimpleNamespace(urban_movements=movements,
            urban_link_storage_veh={r['receiver']: 100. for r in self.doc['resources'].values()}))
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'contract.json'
        self.tuning['urban']['capacity']['head_resource_contract'] = str(self.path)

    def configure(self):
        self.path.write_text(json.dumps(self.doc))
        return hs.configure(self.cfg, self.tuning, self.raw, self.plan)

    def test_pinned_geometry_accepts_straight_and_disjoint_right(self):
        self.assertEqual(self.configure()['physical_head_resource_contract_enabled'], 1.)

    def test_old_v9_still_accepted(self):
        self.doc['schema'] = 'physical-head-resource-join/v9'
        del self.doc['resources']['10493']
        self.assertEqual(self.configure()['physical_head_resource_contract_enabled'], 1.)

    def test_cannot_assign_lane1_to_straight_head(self):
        self.doc['resources']['10493']['heads'][0]['lane'] = 1
        with self.assertRaisesRegex(ValueError, 'head/lane'):
            self.configure()

    def test_cannot_remove_disjoint_evidence(self):
        self.doc['resources']['10493'].pop('disjoint_consumers')
        with self.assertRaisesRegex(ValueError, 'another model consumer'):
            self.configure()

    def test_cannot_invent_second_straight_consumer(self):
        self.cfg.network.urban_movements['unproven'] = copy.deepcopy(
            self.cfg.network.urban_movements['SC1003_S_SC1004_to_N_SC1001'])
        with self.assertRaisesRegex(ValueError, 'another model consumer'):
            self.configure()

    def test_cannot_point_right_at_straight_native_route(self):
        self.doc['resources']['10493']['disjoint_consumers']['SC1003_S_SC1004_to_E_SC105']['native_route'] = '1122:1'
        with self.assertRaisesRegex(ValueError, 'Excluded consumer'):
            self.configure()
