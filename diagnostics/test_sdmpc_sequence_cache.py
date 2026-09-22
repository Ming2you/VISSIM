from pathlib import Path
import copy
import json
import pickle
import sys
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import sdmpc,sdmpc_sequence as seq


class SequenceCacheTests(unittest.TestCase):
    def setUp(self):
        request=pickle.loads((ROOT/'diagnostics/sdmpc_sequence_20260921/three_blocks_h3/request.pickle').read_bytes())
        self.anchor=request['action']
        self.z=np.arange(231,dtype=float)
        self.costs=np.arange(20,dtype=float)
        self.resources=np.array([552.,5144.])
        self.cache=sdmpc.GradientCache()

    def plan(self,cap):
        controls=seq.actions(self.anchor,3)
        for c in controls:c.N_P_star=cap
        return seq.pack(controls)

    def key(self,action):return self.cache.key(self.z,action,self.costs,self.resources)

    def test_horizon_cap_copy_does_not_defeat_cross_cap_reuse(self):
        a,b=self.plan(2400.),self.plan(743.75)
        before=pickle.dumps((a,b))
        self.assertEqual(self.key(a),self.key(b))
        self.assertEqual(pickle.dumps((a,b)),before)
        grad=np.ones((20,231));matrix=np.ones((2,231))
        self.cache.put(self.key(a),a.N_P_star,grad,matrix)
        got=self.cache.get(self.key(b),b.N_P_star)
        self.assertIsNotNone(got)
        got[0][0,0]=99
        self.assertEqual(self.cache.get(self.key(b),b.N_P_star)[0][0,0],1)

    def test_changed_future_control_or_anchor_value_is_not_reused(self):
        a=self.plan(2400.);b=self.plan(743.75)
        row=b.diagnostics[seq.KEY]['future'][0]
        first=next(iter(row['green_times']));row['green_times'][first]+=.001
        self.assertNotEqual(self.key(a),self.key(b))
        self.assertNotEqual(self.key(a),self.cache.key(self.z,a,self.costs+1e-12,self.resources))
        self.assertNotEqual(self.key(a),self.cache.key(self.z,a,self.costs,self.resources+1e-9))
        b=self.plan(743.75);b.N_UF_star+=1.
        self.assertNotEqual(self.key(a),self.key(b))

    def test_legacy_key_unchanged_and_invalid_plan_rejected(self):
        a=seq.first_action(self.anchor);b=copy.deepcopy(a);b.N_P_star=0.
        self.assertEqual(self.key(a),sdmpc.token((self.z,b,self.costs,self.resources)))
        b=self.plan(3.);b.diagnostics[seq.KEY]['future'].pop()
        with self.assertRaises(ValueError):self.key(b)

    def test_full_report_tuple_key_export_preserves_evidence_entries(self):
        from diagnostics.sdmpc_json_records import json_records
        report=pickle.loads((ROOT/'diagnostics/sdmpc_reverse_20260921/full_decision/result.pickle').read_bytes())
        result=json.loads(json.dumps(json_records(report)))
        self.assertTrue(result['completed'])
        self.assertEqual(result['selection']['selected_objective'],report['selection']['selected_objective'])
        source={(1,'x'):np.array([1.,2.]),(2,'y'):3.}
        self.assertEqual(json_records(source),{'__tuple_keyed_mapping__':[[[1,'x'],[1.,2.]],[[2,'y'],3.]]})


if __name__=='__main__':unittest.main()
