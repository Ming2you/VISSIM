from pathlib import Path
import copy
import math
import pickle
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import sdmpc_tangent_reverse as ad, sdmpc_tangent_fast as fast
from evaluation.controllers import control_area_objective as area


class FastPrimitiveTests(unittest.TestCase):
    def test_extrema_value_derivative_and_event_counts_unchanged(self):
        for values in ((2.,3.),(3.,3.),(-0.,0.),(5.,1.)):
            results=[]
            for enabled in (False,True):
                with patch.object(ad,'FAST_PRIMITIVES',enabled):
                    trace=ad.Trace([.1,.1]);a,b=[ad.Dual(v,{j:1.},trace) for j,v in enumerate(values)]
                    out=[ad.minimum(a,b),ad.maximum(a,b),ad.minimum(a,a),ad.minimum(0.,a),
                         ad.maximum(b,4.),ad.maximum((a,b)),ad.minimum([],default=7.)]
                    results.append(([ad.primal(v) for v in out],trace.jacobian(out,1),dict(trace.counts)))
            self.assertEqual(results[0][0],results[1][0])
            np.testing.assert_array_equal(results[0][1],results[1][1])
            self.assertEqual(results[0][2],results[1][2])

    def test_plain_audits_retain_checks_records_and_copy_isolation(self):
        cfg=SimpleNamespace(network=SimpleNamespace(sdmpc_options={'fast_primitives':True,'primal_audit':True}))
        finder=SimpleNamespace(backend='reverse-v1',source_hashes={})
        original_copy=area._copy_response_tree
        original_methods={n:getattr(area.ModelAreaLedger,n) for n in
                          ('record_resource_allocation','record_state_upper_bound')}
        self.addCleanup(setattr,area,'_copy_response_tree',original_copy)
        for name,value in original_methods.items():self.addCleanup(setattr,area.ModelAreaLedger,name,value)
        self.addCleanup(setattr,ad,'FAST_PRIMITIVES',ad.FAST_PRIMITIVES)
        baseline=area.ModelAreaLedger({},capture_response=True,primal_audit=True)
        baseline.begin_response_step('urban',0.,1.)
        x=ad.Dual(1.,{0:1.},ad.Trace([.1]))
        baseline.record_resource_allocation('flow','r',2.,{'a':x})
        baseline.record_state_upper_bound('queue','q',x,2.)
        fast.install(finder,cfg)
        actual=area.ModelAreaLedger({},capture_response=True,primal_audit=True)
        actual.begin_response_step('urban',0.,1.)
        actual.record_resource_allocation('flow','r',2.,{'a':x})
        actual.record_state_upper_bound('queue','q',x,2.)
        self.assertEqual(actual.response(),baseline.response())
        for call in (lambda:actual.record_resource_allocation('flow','r',.5,{'a':x}),
                     lambda:actual.record_resource_allocation('flow','r',2.,{'a':-1.}),
                     lambda:actual.record_state_upper_bound('queue','q',x,.5)):
            with self.assertRaises(ValueError):call()
        values={'a':[x]};values['b']=values['a'];values['cycle']=values
        result=area._copy_response_tree(values)
        self.assertIs(result['a'],result['b']);self.assertIs(result['cycle'],result)
        self.assertIs(result['a'][0],x);self.assertIsNot(result['a'],values['a'])
        self.assertTrue(finder.source_hashes)

    def test_options_absent_and_invalid(self):
        from evaluation.controllers import sdmpc
        cfg=pickle.loads((ROOT/'diagnostics/sdmpc_sequence_20260921/three_blocks_h3/request.pickle').read_bytes())['owned'][0].cfg
        for key in ('fast_primitives','response_np_cache'):
            tuning={'adapter':{'sdmpc':'proxlinear-v1'}}
            self.assertNotIn(key,sdmpc.configure(tuning,copy.deepcopy(cfg)))
            tuning['adapter']['sdmpc_'+key]='true'
            with self.assertRaises(ValueError):sdmpc.configure(tuning,copy.deepcopy(cfg))

    def test_fast_record_comparison_keeps_schema_values_and_fallback(self):
        from evaluation.controllers.sdmpc_tangent_state import state_error
        row=dict(stage='urban',start_sec=0.,end_sec=1.,kind='receiving',resource='r',
                 available_veh=2.,accepted_by_source_veh={'x':1.},accepted_total_veh=1.,exceedance_veh=0.)
        a={'resource_allocations':[row]}
        for key in ('available_veh','accepted_total_veh','exceedance_veh','start_sec','end_sec'):
            b=copy.deepcopy(a);b['resource_allocations'][0][key]+=.001
            self.assertEqual(state_error(a,b),state_error(a,b,fast_records=True))
        b=copy.deepcopy(a);b['resource_allocations'][0]['accepted_by_source_veh']['x']+=.003
        self.assertEqual(state_error(a,b),state_error(a,b,fast_records=True))
        self.assertEqual(state_error(a,copy.deepcopy(a),fast_records=True),0.)
        b=copy.deepcopy(a);b['resource_allocations'][0]['resource']='other'
        with self.assertRaises(ValueError):state_error(a,b,fast_records=True)
        b=copy.deepcopy(a);b['resource_allocations'][0]['unexpected']=0.
        with self.assertRaises(ValueError):state_error(a,b,fast_records=True)
        trace=ad.Trace([.1]);b=copy.deepcopy(a)
        b['resource_allocations'][0]['available_veh']=ad.Dual(2.,{0:1.},trace)
        self.assertEqual(state_error(a,b,fast_records=True),0.)
        self.assertFalse(trace.counts)
        for field in ('available_veh','accepted_by_source_veh'):
            bad=copy.deepcopy(a)
            if field=='available_veh':bad['resource_allocations'][0][field]=float('nan')
            else:bad['resource_allocations'][0][field]['x']=float('nan')
            # Identical NaN objects compare equal inside Python containers;
            # the original numeric comparator must still reject this case.
            with self.assertRaises(ValueError):state_error(bad,copy.deepcopy(bad),fast_records=True)


if __name__=='__main__':unittest.main()
