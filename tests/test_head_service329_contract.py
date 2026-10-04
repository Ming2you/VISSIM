"""Actual selected-network contract guards for the329 straight head join."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from evaluation.controllers import head_service_resources as hs

ROOT=Path(__file__).resolve().parents[1]
CASE=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/expanded036_9000_20260930/loss_onset2250/service329'


class Service329ContractTest(unittest.TestCase):
    def setUp(self):
        self.doc=json.loads((CASE/'head_resources.json').read_bytes())
        self.tuning=json.loads((CASE/'candidate_config.json').read_bytes())
        self.raw={'network_path':str(ROOT/self.doc['network']['path'])}
        self.plan=json.loads((ROOT/'outputs/signal_group_actuation_plan_mainline_20260825.json').read_bytes())
        movements={}
        for row in self.doc['resources'].values():
            for name,spec in row['members'].items():
                movements[name]={**spec,'beta':1.}
            for name,spec in row.get('disjoint_consumers',{}).items():
                movements[name]={**spec['expected_spec'],'beta':1.}
        self.cfg=SimpleNamespace(network=SimpleNamespace(urban_movements=movements,
            urban_link_storage_veh={r['receiver']:100. for r in self.doc['resources'].values()}))
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'contract.json'
        self.tuning['urban']['capacity']['head_resource_contract']=str(self.path)

    def configure(self):
        self.path.write_text(json.dumps(self.doc))
        return hs.configure(self.cfg,self.tuning,self.raw,self.plan)

    def test_selected_native_geometry_and_long_route_are_accepted(self):
        self.assertEqual(self.configure()['physical_head_resource_contract_enabled'],1.)
        self.assertEqual(set(hs.view(self.cfg)['resources']['10691']['members']),
                         {'SC1002_E_SC101_to_W_SC1001'})

    def test_old_v6_contract_still_valid(self):
        self.doc['schema']='physical-head-resource-join/v6'
        del self.doc['resources']['10691']
        self.assertEqual(self.configure()['physical_head_resource_contract_enabled'],1.)

    def test_unreviewed_resource_set_rejected(self):
        del self.doc['resources']['10691']
        with self.assertRaisesRegex(ValueError,'Unreviewed'):
            self.configure()

    def test_wrong_head_lane_rejected(self):
        self.doc['resources']['10691']['heads'][0]['lane']=1
        with self.assertRaisesRegex(ValueError,'head/lane'):
            self.configure()

    def test_long_route_cannot_be_replaced_by_only_local_triplet(self):
        row=self.doc['resources']['10691']['disjoint_consumers']['SC1002_E_SC101_to_N_SC2004']
        del row['native_route_path']
        with self.assertRaisesRegex(ValueError,'Excluded consumer'):
            self.configure()

    def test_unknown_competing_movement_rejected(self):
        spec=copy.deepcopy(self.cfg.network.urban_movements['SC1002_E_SC101_to_W_SC1001'])
        self.cfg.network.urban_movements['unreviewed_turn']=spec
        with self.assertRaisesRegex(ValueError,'another model consumer'):
            self.configure()


if __name__=='__main__':
    unittest.main()
