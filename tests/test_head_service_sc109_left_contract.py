"""Two native left lanes may share past exposure, never through-lane service."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from evaluation.controllers import head_service_resources as hs
from evaluation.controllers.signal_head_observation import green_exposure_windows,pooled_green_support

ROOT=Path(__file__).resolve().parents[1]
CASE=ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269/sc109_service'

class ServiceSC109LeftContractTest(unittest.TestCase):
    def setUp(self):
        self.doc=json.loads((CASE/'head_resources.json').read_bytes())
        self.tuning=json.loads((CASE/'config.json').read_bytes())
        self.tuning['execution']['native_signal_record']=False
        self.raw={'network_path':str(ROOT/self.doc['network']['path'])}
        self.plan=json.loads((ROOT/'outputs/signal_group_actuation_plan_mainline_20260825.json').read_bytes())
        movements={}
        for row in self.doc['resources'].values():
            movements.update({m:{**v,'beta':1.} for m,v in row['members'].items()})
            movements.update({m:{**v['expected_spec'],'beta':1.} for m,v in row.get('disjoint_consumers',{}).items()})
            for detail in row.get('disjoint_consumers',{}).values():
                if 'downstream_choice' in detail:
                    choice=json.loads((ROOT/detail['downstream_choice']['path']).read_bytes())
                    turn=next(t for t in choice['incoming_turns'].values() if t['keep'] in movements and t['connector']==detail['path'][1])
                    movements[turn['remove']]={**movements[turn['keep']],'receiving_link':choice['bypass_storage']}
        self.cfg=SimpleNamespace(network=SimpleNamespace(urban_movements=movements,
            urban_link_storage_veh={r['receiver']:100. for r in self.doc['resources'].values()}))
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'contract.json'
        self.tuning['urban']['capacity']['head_resource_contract']=str(self.path)

    def configure(self):
        self.path.write_text(json.dumps(self.doc))
        return hs.configure(self.cfg,self.tuning,self.raw,self.plan)

    def test_both_left_heads_and_only_the_proven_group(self):
        self.assertEqual(self.configure()['physical_head_resource_contract_enabled'],1.)
        self.assertEqual(green_exposure_windows(self.cfg,('173','p4')),4)
        self.assertEqual(green_exposure_windows(self.cfg,('173','p3')),0)
        self.assertEqual(green_exposure_windows(self.cfg,('1210009503','p1')),0)

    def test_old_v11_remains_supported(self):
        self.doc['schema']='physical-head-resource-join/v11';del self.doc['resources']['10286']
        self.assertEqual(self.configure()['physical_head_resource_contract_enabled'],1.)
        self.assertEqual(green_exposure_windows(self.cfg,('173','p4')),0)

    def test_missing_lane_or_changed_head_rejected(self):
        for mode in ('missing','through_lane'):
            with self.subTest(mode=mode):
                original=copy.deepcopy(self.doc)
                if mode=='missing':self.doc['resources']['10286']['heads'].pop()
                else:self.doc['resources']['10286']['heads'][0]['lane']=3
                with self.assertRaisesRegex(ValueError,'head/lane'):self.configure()
                self.doc=original

    def test_measurement_cannot_move_to_through(self):
        row=self.doc['resources']['10286'];row['members']={'SC109_W_SC108_to_E':next(iter(row['members'].values()))}
        with self.assertRaisesRegex(ValueError,'incoming route proof'):self.configure()

    def test_duplicate_consumer_rejected(self):
        self.cfg.network.urban_movements['unknown']=copy.deepcopy(self.cfg.network.urban_movements['SC109_W_SC108_to_N_SC16'])
        with self.assertRaisesRegex(ValueError,'another model consumer'):self.configure()

    def test_old_schema_cannot_acquire_new_resource(self):
        self.doc['schema']='physical-head-resource-join/v11'
        with self.assertRaisesRegex(ValueError,'Unreviewed'):self.configure()

if __name__=='__main__':unittest.main()
