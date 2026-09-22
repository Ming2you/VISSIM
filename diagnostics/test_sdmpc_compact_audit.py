"""Lossless record representation and read-only primal guard regression tests."""
import copy
import math
from pathlib import Path
import pickle
import sys
from dataclasses import replace
from types import SimpleNamespace as NS
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import sdmpc_tangent_audit as audit,sdmpc_tangent_reverse as ad
from evaluation.controllers.control_area_objective import ModelAreaLedger
from evaluation.controllers.sdmpc_tangent_state import state_error


def records():
    ledger=ModelAreaLedger({},capture_response=True,primal_audit=True)
    ledger.begin_response_step('urban',0.,1.)
    for i in range(4):
        ledger.record_resource_allocation('receiving',str(i),2.,{'b':.1,'a':.2})
        ledger.record_state_upper_bound('stock',str(i),.5,2.)
    return {k:ledger._response[k] for k in ('transfers','resource_allocations','state_bounds')}


class CompactAuditTests(unittest.TestCase):
    def test_column_storage_requires_isolated_witness_and_opt_in(self):
        cfg=NS(network=NS(sdmpc_options={'compact_audit':True}))
        previous=audit.WITNESS_PROCESS
        try:
            audit.WITNESS_PROCESS=False
            self.assertFalse(audit.compact_enabled(cfg))
            audit.WITNESS_PROCESS=True
            self.assertTrue(audit.compact_enabled(cfg))
            cfg.network.sdmpc_options={}
            self.assertFalse(audit.compact_enabled(cfg))
        finally:
            audit.WITNESS_PROCESS=previous

    def test_lossless_order_bytes_copy_and_pickle(self):
        original=records();block=audit.pack(original)
        self.assertEqual(block.unpack(),original)
        self.assertEqual(tuple(block.unpack()['resource_allocations'][0]['accepted_by_source_veh']),('b','a'))
        self.assertEqual(pickle.dumps(original),pickle.dumps(block.unpack()))
        self.assertIs(copy.deepcopy(block),block)
        self.assertEqual(pickle.loads(pickle.dumps(block)).unpack(),original)
        a=block.unpack();a['resource_allocations'][0]['available_veh']=7.
        self.assertEqual(block.unpack(),original)

    def test_every_numeric_column_and_source_change_is_detected(self):
        original=records();a=audit.pack(original)
        for family,keys in (('resource_allocations',('start_sec','end_sec','available_veh','accepted_total_veh','exceedance_veh')),
                            ('state_bounds',('start_sec','end_sec','value_veh','upper_veh'))):
            for key in keys:
                b=copy.deepcopy(original);b[family][2][key]+=.125
                self.assertEqual(audit.error(a,audit.pack(b)),.125)
        b=copy.deepcopy(original);b['resource_allocations'][1]['accepted_by_source_veh']['a']+=.25
        self.assertEqual(audit.error(a,audit.pack(b)),.25)
        b=copy.deepcopy(original);b['resource_allocations'][1]['resource']='different'
        self.assertIsNone(audit.error(a,audit.pack(b)))

    def test_invalid_or_incomplete_records_still_fail(self):
        for value in (math.nan,math.inf,-math.inf,True,2**54+1,ad.Dual(1.,{0:1.},ad.Trace([.1]))):
            row=records();row['resource_allocations'][0]['available_veh']=value
            with self.assertRaises(ValueError):audit.pack(row)
        row=records();row['state_bounds'][0]['extra']=1.
        with self.assertRaises(ValueError):audit.pack(row)
        a=audit.pack(records())
        with self.assertRaises(ValueError):audit.error(a,replace(a,bound_values=a.bound_values[:-8]))
        corrupt=np.frombuffer(a.bound_values,dtype=np.float64).copy();corrupt[0]=math.nan
        with self.assertRaises(ValueError):audit.error(a,replace(a,bound_values=corrupt.tobytes()))

    def test_empty_allocation_keeps_integer_sum_and_signed_zero(self):
        ledger=ModelAreaLedger({},capture_response=True,primal_audit=True)
        ledger.begin_response_step('urban',0.,1.)
        ledger.record_resource_allocation('ready','empty',-0.,{})
        row={k:ledger._response[k] for k in ('transfers','resource_allocations','state_bounds')}
        restored=audit.pack(row).unpack()
        self.assertEqual(pickle.dumps(row),pickle.dumps(restored))
        self.assertIs(type(restored['resource_allocations'][0]['accepted_total_veh']),int)
        self.assertEqual(math.copysign(1.,restored['resource_allocations'][0]['available_veh']),-1.)

    def test_old_and_new_packed_full_state_compared_with_all_fields(self):
        row=records();a={'_packed_response_records':[pickle.dumps(row,protocol=5)]}
        b={'_packed_response_records':[audit.pack(row)]}
        self.assertEqual(state_error(a,b,compact_records=True),0.)
        row['state_bounds'][2]['value_veh']+=.125
        b['_packed_response_records']=[audit.pack(row)]
        self.assertEqual(state_error(a,b,compact_records=True),.125)
        row['state_bounds'][2]['resource']='changed'
        b['_packed_response_records']=[audit.pack(row)]
        with self.assertRaises(ValueError):state_error(a,b,compact_records=True)

    def test_ledger_exports_all_fields_and_conserves_transfer_aliases(self):
        ledgers=[]
        for compact in (False,True):
            ledger=ModelAreaLedger({},capture_response=True,primal_audit=True)
            ledger.begin_response_step('urban',0.,1.)
            ledger.record_resource_allocation('receiving','q',2.,{'x':1.})
            before=copy.deepcopy(ledger._response)
            ledger.pack_completed_response_records(compact=compact)
            self.assertEqual(ledger._response['resource_allocations'],[])
            from evaluation.controllers.sdmpc_tangent_records import unpack
            rebuilt=unpack(ledger._packed_response_records[0])
            self.assertEqual(rebuilt['resource_allocations'],before['resource_allocations'])
            ledgers.append(ledger)
        self.assertEqual(state_error(ledgers[0],ledgers[1],compact_records=True),0.)

    def test_readonly_guard_retains_primal_order_failure_and_outer_jacobian(self):
        def check(values):
            n=sum(values)
            return n+ad.MathProxy.fsum(values)-n
        outputs=[]
        for enabled in (False,True):
            trace=ad.Trace([.1]);x=ad.Dual(1.,{0:1.},trace)
            values=[x*1e16,x,x*-1e16]
            before=len(trace.p1)
            result=(audit.guard(check) if enabled else check)(values)
            extra=len(trace.p1)-before
            outputs.append((ad.primal(result),trace.jacobian([x*x],1),extra))
            self.assertFalse(ad.PRIMAL_GUARD)
        self.assertEqual(outputs[0][0],outputs[1][0])
        np.testing.assert_array_equal(outputs[0][1],outputs[1][1])
        self.assertGreater(outputs[0][2],0);self.assertEqual(outputs[1][2],0)
        def fail():raise ValueError('guard failure')
        with self.assertRaisesRegex(ValueError,'guard failure'):audit.guard(fail)()
        self.assertFalse(ad.PRIMAL_GUARD)
        with self.assertRaises(ValueError):audit.guard(check)([
            ad.Dual(1.,{0:1.},ad.Trace([.1])),ad.Dual(1.,{0:1.},ad.Trace([.1]))])

    def test_compact_is_opt_in_and_requires_primal_records(self):
        from evaluation.controllers import sdmpc
        cfg=pickle.loads((ROOT/'diagnostics/sdmpc_prediction_20260922/cached_h3_v2/request.pickle').read_bytes())['owned'][0].cfg
        tuning={'adapter':{'sdmpc':'proxlinear-v1'}}
        self.assertNotIn('compact_audit',sdmpc.configure(tuning,copy.deepcopy(cfg)))
        tuning['adapter']['sdmpc_compact_audit']=True
        with self.assertRaises(ValueError):sdmpc.configure(tuning,copy.deepcopy(cfg))
        tuning['adapter']['sdmpc_primal_audit']=True
        self.assertTrue(sdmpc.configure(tuning,copy.deepcopy(cfg))['compact_audit'])
        tuning['adapter']['sdmpc_compact_audit']=1
        with self.assertRaises(ValueError):sdmpc.configure(tuning,copy.deepcopy(cfg))


if __name__=='__main__':unittest.main()
