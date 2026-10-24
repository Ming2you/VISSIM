"""Validation-only audit quantities retain all guards without AD tapes."""
from pathlib import Path
import ast
import copy
import pickle
import sys
import types
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import sdmpc_tangent_reverse as ad
from evaluation.controllers import sdmpc_tangent_runtime as runtime


class PrimalAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        old=runtime.ad
        try:
            runtime.ad=ad
            module=types.ModuleType('audit_test')
            sys.modules['audit_test']=module
            cls.addClassCleanup(sys.modules.pop,'audit_test',None)
            ns=module.__dict__
            ns.update(runtime.namespace())
            path=ROOT/'evaluation/controllers/control_area_objective.py'
            exec(compile(ast.fix_missing_locations(runtime.Transform().visit(ast.parse(path.read_text()))),str(path),'exec'),ns)
            cls.Ledger=ns['ModelAreaLedger']
        finally: runtime.ad=old

    def ledger(self,mode):
        ledger=self.Ledger({},capture_response=True,primal_audit=mode)
        ledger.begin_response_step('urban',0.,1.)
        return ledger

    def test_same_primal_records_without_extra_tape_nodes(self):
        trace=ad.Trace([.1]); x=ad.Dual(1.,{0:1.},trace)
        other=ad.Dual(.5,{0:2.},trace)
        a,b=self.ledger(False),self.ledger(True)
        n=len(trace.p1)
        b.record_resource_allocation('merge','x',2.,{'a':x,'b':other})
        b.record_state_upper_bound('queue','q',x,2.)
        self.assertEqual(len(trace.p1),n)
        a.record_resource_allocation('merge','x',2.,{'a':x,'b':other})
        a.record_state_upper_bound('queue','q',x,2.)
        self.assertGreater(len(trace.p1),n)
        from evaluation.controllers.sdmpc_tangent_state import state_error
        self.assertEqual(state_error(a._response,b._response),0.)
        self.assertIs(type(b._response['resource_allocations'][0]['accepted_total_veh']),float)
        self.assertEqual(trace.jacobian([x*x],1)[0,0],2.)

    def test_allocation_and_storage_failures_remain_failures(self):
        for mode in (False,True):
            x=ad.Dual(3.,{0:1.},ad.Trace([.1])); ledger=self.ledger(mode)
            with self.assertRaisesRegex(ValueError,'exceeds shared'):
                ledger.record_resource_allocation('merge','x',2.,{'a':x})
            with self.assertRaisesRegex(ValueError,'upper bound exceeded'):
                ledger.record_state_upper_bound('queue','q',x,2.)
            with self.assertRaises(ValueError):
                ledger.record_resource_allocation('merge','x',2.,{'a':-x})
            with self.assertRaises(ValueError):
                ledger.record_resource_allocation('merge','x',2.,[])

    def test_configuration_is_opt_in_and_validated(self):
        from evaluation.controllers import sdmpc
        cfg=pickle.loads((ROOT/'diagnostics/sdmpc_sequence_20260921/three_blocks_h3/request.pickle').read_bytes())['owned'][0].cfg
        tuning={'adapter':{'sdmpc':'proxlinear-v1'}}
        self.assertNotIn('primal_audit',sdmpc.configure(tuning,copy.deepcopy(cfg)))
        tuning['adapter']['sdmpc_primal_audit']=True
        self.assertIs(sdmpc.configure(tuning,copy.deepcopy(cfg))['primal_audit'],True)
        tuning['adapter']['sdmpc_primal_audit']='true'
        with self.assertRaises(ValueError): sdmpc.configure(tuning,copy.deepcopy(cfg))


if __name__=='__main__':unittest.main()
