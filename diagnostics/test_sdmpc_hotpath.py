"""Compact prediction work must retain every check and identical AD tape."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import sdmpc_tangent_reverse as ad
from evaluation.controllers.sdmpc_tangent_summary import install,checked_operation,CheckedRecords
from evaluation.controllers.control_area_objective import ModelAreaLedger


class HotpathTests(unittest.TestCase):
    def test_arithmetic_preserves_exact_tape_and_values(self):
        def calculate(function):
            with patch.object(ad.Trace,'operation',function):
                t=ad.Trace([.1,.1]);a=ad.Dual(1.7,{0:2.},t);b=ad.Dual(2.5,{1:-3.},t)
                values=[a+b,a-b,b-a,a*0.,a+a,a/a,4/a,a**b,ad.MathProxy.exp(a),-a,
                    a+0.,0.+a,(a+1.)-a,a%2.,ad.minimum(a,b),ad.MathProxy.fsum([a,1.,b])]
                for i in range(30):values.append(values[-1]*.999+a/(i+1)-.01*b)
                raw=[v.tobytes() for v in (t.p1,t.p2,t.w1,t.w2)]
                support=[getattr(v,'support',None) for v in values]
                numbers=[ad.primal(v).hex() for v in values]
                jac=t.jacobian(values,1)
                return raw,support,numbers,jac
        a=calculate(ad.Trace.operation);b=calculate(checked_operation)
        self.assertEqual(a[:3],b[:3]);np.testing.assert_array_equal(a[3],b[3])

    def test_guard_mixed_tapes_and_frozen_tape_still_enforced(self):
        with patch.object(ad.Trace,'operation',checked_operation):
            t=ad.Trace([.1]);a=ad.Dual(2.,{0:1.},t)
            b=ad.Dual(3.,{0:1.},ad.Trace([.1]))
            with self.assertRaises(ValueError):a+b
            before=len(t.p1)
            with patch.object(ad,'PRIMAL_GUARD',True):
                value=a*a
                self.assertEqual(value.node,0);self.assertEqual(value.value,4.)
            self.assertEqual(len(t.p1),before)
            t.frozen=True
            with self.assertRaises(ValueError):a*a

    def with_installed(self):
        cfg=NS(network=NS(sdmpc_options=dict(prediction_hotpath=True,surrogate_reuse=True,
            fast_primitives=True,primal_audit=True)))
        originals={k:getattr(ModelAreaLedger,k) for k in ('__init__','pack_completed_response_records','response')}
        original_op=ad.Trace.operation
        def restore():
            for key,value in originals.items():setattr(ModelAreaLedger,key,value)
            if hasattr(ModelAreaLedger,'_sdmpc_stream_summary_installed'):
                del ModelAreaLedger._sdmpc_stream_summary_installed
            ad.Trace.operation=original_op
        self.addCleanup(restore)
        install(NS(backend='reverse-v1',source_hashes={}),cfg,surrogate_mode='ad')

    def test_checked_records_survive_intervals_and_independent_clones(self):
        self.with_installed()
        x=ModelAreaLedger({},capture_response=True,primal_audit=True,indexed_coverage=True)
        x.begin_response_step('urban',0,1)
        x.record_resource_allocation('capacity','r',10.,{'a':3.,'b':4.})
        x.record_state_upper_bound('stock','s',4.,9.)
        x.pack_completed_response_records(compact=True)
        y=copy.deepcopy(x)
        y.begin_response_step('urban',1,2)
        y.record_resource_allocation('supply','r',5.,{'a':2.})
        y.pack_completed_response_records(compact=True)
        out=y.response();old=x.response()
        self.assertEqual(out['resource_allocations'],[]);self.assertEqual(out['state_bounds'],[])
        self.assertEqual(out['model_constraint_coverage']['checked_allocation_count'],2)
        self.assertEqual(out['model_constraint_coverage']['checked_state_bound_count'],1)
        self.assertEqual(old['model_constraint_coverage']['checked_allocation_count'],1)
        self.assertEqual(out['streamed_model_checks']['allocation_summary'],
            dict(count=2,kinds={'capacity':1,'supply':1},max_exceedance_veh=0.))
        self.assertFalse(out['model_constraint_coverage']['complete'])
        with self.assertRaises(TypeError):list(y._response['resource_allocations'])

    def test_failed_checks_keep_original_exception_and_do_not_count(self):
        self.with_installed()
        x=ModelAreaLedger({},capture_response=True,primal_audit=True)
        x.begin_response_step('urban',0,1)
        with self.assertRaises(ValueError) as err:x.record_resource_allocation('capacity','r',1.,{'a':2.})
        self.assertEqual(err.exception.resource_allocation['exceedance_veh'],1.)
        with self.assertRaises(ValueError):x.record_state_upper_bound('stock','s',2.,1.)
        with self.assertRaises(ValueError):x.record_resource_allocation('capacity','r',1.,{'a':float('nan')})
        self.assertEqual(len(x._response['resource_allocations']),0)
        self.assertEqual(len(x._response['state_bounds']),0)

    def test_transfer_records_remain_complete_and_missing_coverage_false(self):
        self.with_installed()
        x=ModelAreaLedger({'s':{'inside':5.,'outside':0.}},capture_response=True,primal_audit=True)
        x.begin_response_step('urban',0,1)
        x.transfer('s','t',2.,inside_to_inside=1.,outside_to_inside=0.,route_key='movement:m')
        x.pack_completed_response_records(compact=True)
        out=x.response()
        self.assertEqual(len(out['transfers']),1);self.assertEqual(out['transfers'][0]['vehicles'],2.)
        self.assertFalse(out['conditional_model_feasibility_witness'])

    def test_requires_explicit_surrogate_worker(self):
        cfg=NS(network=NS(sdmpc_options={}))
        original=ModelAreaLedger.response
        install(NS(backend='reverse-v1'),cfg,surrogate_mode=None)
        self.assertIs(ModelAreaLedger.response,original)
        cfg.network.sdmpc_options.update(prediction_hotpath=True,surrogate_reuse=True,
            fast_primitives=True,primal_audit=True)
        with self.assertRaises(ValueError):install(NS(backend='reverse-v1'),cfg,surrogate_mode=None)


if __name__=='__main__':unittest.main()
