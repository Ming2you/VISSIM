from pathlib import Path
import copy
import pickle
import sys
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers.sdmpc_tangent import merge_columns


class ParallelTests(unittest.TestCase):
    def test_worker_and_aggregate_options_are_explicit_and_validated(self):
        from evaluation.controllers import sdmpc
        with (ROOT/'diagnostics/sdmpc_sequence_20260921/three_blocks_h3/request.pickle').open('rb') as f:
            cfg=pickle.load(f)['owned'][0].cfg
        base={'adapter':{'sdmpc':'proxlinear-v1','sdmpc_derivatives':'tangent-v1'}}
        old=sdmpc.configure(base,copy.deepcopy(cfg))
        self.assertNotIn('derivative_workers',old);self.assertNotIn('aggregate_predictor',old)
        base['adapter'].update(sdmpc_derivative_workers=8,sdmpc_aggregate_predictor='route-bins-v1')
        options=sdmpc.configure(base,copy.deepcopy(cfg))
        self.assertEqual(options['derivative_workers'],8)
        self.assertEqual(options['aggregate_predictor'],'route-bins-v1')
        for value in (True,0,9,8.):
            bad=copy.deepcopy(base);bad['adapter']['sdmpc_derivative_workers']=value
            with self.assertRaises(ValueError):sdmpc.configure(bad,copy.deepcopy(cfg))
        bad=copy.deepcopy(base);bad['adapter']['sdmpc_aggregate_predictor']='unknown'
        with self.assertRaises(ValueError):sdmpc.configure(bad,copy.deepcopy(cfg))

    def receipts(self):
        rows=[]
        for part in ([0,2],[1,3]):
            rows.append(dict(column_indices=part,complete_primal_state_match=True,
                max_primal_state_error=0.,ad_axes=part,fallback_reasons={},
                costs=[1.,2.],resources=[3.,4.],cost_jacobian=[[j+1 for j in part],[j+5 for j in part]],
                resource_jacobian=[[j+9 for j in part],[j+13 for j in part]],
                scalar_sec=1.,tangent_sec=2.,trace={},transformed_source_sha256={'model':'same'}))
        return rows

    def test_global_columns_and_all_owner_cross_effects_preserved(self):
        r=merge_columns(self.receipts(),[[0,2],[1,3]],4,1e-8)
        np.testing.assert_array_equal(r['cost_jacobian'],[[1,2,3,4],[5,6,7,8]])
        np.testing.assert_array_equal(r['resource_jacobian'],[[9,10,11,12],[13,14,15,16]])

    def test_missing_duplicate_anchor_and_source_mismatch_rejected(self):
        with self.assertRaises(ValueError):merge_columns(self.receipts(),[[0,2],[1,2]],4,1e-8)
        for field,value in [('costs',[99.,2.]),('transformed_source_sha256',{'model':'changed'}),
                             ('max_primal_state_error',float('nan')),('max_primal_state_error',-1.),
                             ('complete_primal_state_match',False),('column_indices',[1])]:
            r=self.receipts();r[1][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                merge_columns(r,[[0,2],[1,3]],4,1e-8)


if __name__=='__main__':unittest.main()
