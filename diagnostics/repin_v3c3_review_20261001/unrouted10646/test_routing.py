import copy
import json
import unittest
from pathlib import Path
from evaluation.controllers import offramp_routing as routing

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


class RouteFreeContinuation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document=json.loads((HERE/'route_contract.json').read_bytes())
        cls.mapping=json.loads((ROOT/cls.document['mapping']['path']).read_bytes())
        cls.current=routing.compile_inventory(cls.document,cls.mapping)
        legacy=copy.deepcopy(cls.document);legacy.pop('route_free_policy')
        cls.previous=routing.compile_inventory(legacy,cls.mapping)

    def test_merge_continues_to_native_next_connector(self):
        self.assertEqual(self.current['merges']['RM_C10646']['weights'],{'10638':1.})

    def test_input_and_other_merge_choices_preserved(self):
        self.assertEqual(self.current['inputs'],self.previous['inputs'])
        self.assertEqual(self.current['merges']['RM_C10480']['weights'],{'10491':1.})
        for ramp,row in self.current['merges'].items():
            if ramp not in ('RM_C10646','RM_C10480'):self.assertEqual(row,self.previous['merges'][ramp])

    def test_current_route_end_and_route_free_position(self):
        row=self.current['routes']['1135:2']
        self.assertEqual(routing._route_distribution(self.current,row,'FW_W',6162.507350750207),{'10638':1.})
        self.assertEqual(routing._future_distribution(self.current,'FW_W',6200.),{'10638':1.})

    def test_existing_through_route_not_redrawn(self):
        row=self.current['routes']['1133:3']
        self.assertEqual(routing._route_distribution(self.current,row,'FW_W',6200.),{'terminal':1.})

    def test_upstream_decision_before_default_exit(self):
        self.assertEqual(routing._future_distribution(self.current,'FW_W',4000.),
                         self.previous['merges']['RM_C10482']['weights'])
        self.assertEqual(routing._future_distribution(self.current,'FW_W',6300.),{'terminal':1.})

    def test_invalid_policy_fails(self):
        for value in (True,'all_terminal',''):
            d=copy.deepcopy(self.document);d['route_free_policy']=value
            with self.assertRaises(ValueError):routing.compile_inventory(d,self.mapping)


if __name__=='__main__':unittest.main()
