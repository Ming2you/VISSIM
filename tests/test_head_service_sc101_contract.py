"""Protect the physical ownership of the two SC101 south-left heads."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from evaluation.controllers import head_service_resources as hs
from evaluation.controllers.signal_head_observation import green_exposure_windows

ROOT=Path(__file__).resolve().parents[1]
CASE=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/expanded036_9000_20260930/loss_onset2250/source_sc101'


class ServiceSC101ContractTest(unittest.TestCase):
    def setUp(self):
        self.doc=json.loads((CASE/'head_resources.json').read_bytes())
        self.tuning=json.loads((CASE/'candidate_service_config.json').read_bytes())
        self.raw={'network_path':str(ROOT/self.doc['network']['path'])}
        self.plan=json.loads((ROOT/'outputs/signal_group_actuation_plan_mainline_20260825.json').read_bytes())
        movements={}
        for row in self.doc['resources'].values():
            movements.update({k:{**v,'beta':1.} for k,v in row['members'].items()})
            movements.update({k:{**v['expected_spec'],'beta':1.} for k,v in row.get('disjoint_consumers',{}).items()})
        self.cfg=SimpleNamespace(network=SimpleNamespace(urban_movements=movements,
            urban_link_storage_veh={r['receiver']:100. for r in self.doc['resources'].values()}))
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'contract.json'
        self.tuning['urban']['capacity']['head_resource_contract']=str(self.path)

    def configure(self):
        self.path.write_text(json.dumps(self.doc))
        return hs.configure(self.cfg,self.tuning,self.raw,self.plan)

    def test_pinned_native_geometry_accepts_unique_left_and_only_local_pool(self):
        self.assertEqual(self.configure()['physical_head_resource_contract_enabled'],1.)
        self.assertEqual(green_exposure_windows(self.cfg,('1220011503','p2')),4)
        self.assertEqual(green_exposure_windows(self.cfg,('1220011503','p1')),0)

    def test_left_measurement_cannot_be_assigned_to_through(self):
        self.doc['resources']['10539']['members']={
            'SC101_S_SC1_to_N_SC2005':self.doc['resources']['10539']['members']['SC101_S_SC1_to_W_SC1002']}
        with self.assertRaisesRegex(ValueError,'incoming route proof'):
            self.configure()

    def test_new_consumer_requires_new_physical_proof(self):
        self.cfg.network.urban_movements['unproven']=copy.deepcopy(
            self.cfg.network.urban_movements['SC101_S_SC1_to_W_SC1002'])
        with self.assertRaisesRegex(ValueError,'another model consumer'):
            self.configure()

    def test_cannot_call_v7_a_proof_for_new_resource(self):
        self.doc['schema']='physical-head-resource-join/v7'
        with self.assertRaisesRegex(ValueError,'Unreviewed'):
            self.configure()


if __name__=='__main__':
    unittest.main()
