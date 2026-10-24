from pathlib import Path
import copy
import pickle
import sys
import unittest
from dataclasses import FrozenInstanceError
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers.sdmpc_tangent_records import freeze, unpack
from evaluation.controllers.sdmpc_dual import Dual, Trace, derivative


class FrozenRecordsTests(unittest.TestCase):
    def test_no_alias_to_owned_mutable_source_or_exports(self):
        source={'rows':[{'x':1.,'accepted':{'lane':.2}},('tag',.3)]}
        block=freeze(source)
        self.assertIs(copy.deepcopy(block),block)
        source['rows'][0]['accepted']['lane']=9.
        a,b=unpack(block),unpack(block)
        self.assertEqual(a['rows'][0]['accepted']['lane'],.2)
        a['rows'][0]['accepted']['lane']=8.
        self.assertEqual(b['rows'][0]['accepted']['lane'],.2)
        self.assertIs(type(b['rows']),list); self.assertIs(type(b['rows'][1]),tuple)
        with self.assertRaises(FrozenInstanceError): block.kind='changed'
        with self.assertRaises(TypeError): block.entries[0]=('changed',0)

    def test_pickle_and_existing_bytes_have_same_values(self):
        source={'rows':[{'x':1.,'target':None,'amounts':{'a':.2,'b':.1}}]}
        self.assertEqual(unpack(pickle.loads(pickle.dumps(freeze(source)))),source)
        self.assertEqual(unpack(pickle.dumps(source)),source)
        with self.assertRaises(TypeError): freeze({'bad':set()})
        with self.assertRaises(TypeError): unpack([])

    def test_derivatives_survive_freeze_and_independent_exports(self):
        x=Dual(2.,{0:3.},Trace([.1],track_stencils=False))
        row=unpack(freeze({'transfers':[{'vehicles':x}]}))['transfers'][0]
        self.assertIs(row['vehicles'],x)
        self.assertEqual(derivative(row['vehicles']*4.),{0:12.})

    def test_ledger_snapshots_and_full_audit_equal_legacy(self):
        from evaluation.controllers.control_area_objective import ModelAreaLedger
        from evaluation.controllers.sdmpc_tangent_state import state_error
        before,after=[ModelAreaLedger({},capture_response=True,immutable_audit=mode) for mode in (False,True)]
        for ledger in (before,after):
            for t in range(3):
                ledger.begin_response_step('urban',float(t),float(t+1))
                ledger.record_resource_allocation('merge','lane',3.,{'a':.7,'b':1.2})
                ledger.record_state_upper_bound('queue','q',1.9,3.)
                ledger.pack_completed_response_records()
        self.assertEqual(before.response(),after.response())
        snapshot=copy.deepcopy(after)
        self.assertIs(snapshot._packed_response_records[0],after._packed_response_records[0])
        self.assertEqual(state_error(snapshot,after),0.)
        changed=snapshot.response()
        changed['resource_allocations'][0]['accepted_by_source_veh']['a']=99.
        self.assertEqual(before.response(),after.response())
        self.assertEqual(pickle.loads(pickle.dumps(snapshot)).response(),before.response())

    def test_immutable_audit_option_is_validated(self):
        from evaluation.controllers import sdmpc
        cfg=pickle.loads((ROOT/'diagnostics/sdmpc_sequence_20260921/three_blocks_h3/request.pickle').read_bytes())['owned'][0].cfg
        base={'adapter':{'sdmpc':'proxlinear-v1'}}
        self.assertNotIn('immutable_audit',sdmpc.configure(base,copy.deepcopy(cfg)))
        base['adapter']['sdmpc_immutable_audit']=True
        self.assertIs(sdmpc.configure(base,copy.deepcopy(cfg))['immutable_audit'],True)
        base['adapter']['sdmpc_immutable_audit']=1
        with self.assertRaises(ValueError):sdmpc.configure(base,copy.deepcopy(cfg))


if __name__=='__main__':unittest.main()
