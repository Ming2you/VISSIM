from copy import deepcopy
from pathlib import Path
import json,pickle,unittest
from . import candidate as c
from ..transfer331.inputs import load
class NativeRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg,_,_=pickle.loads((c.A/'transfer331/build2400_v2/initial.pickle').read_bytes())
        cls.network=(c.ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx').read_bytes()
        source=json.loads((c.A/'transfer331/build2400_v2/summary.json').read_bytes())['source']
        _,cls.frame,_=load(source,2400)
    def test_real_native_path_and_current_routes(self):
        cfg=deepcopy(self.cfg);before=deepcopy(cfg.network)
        receipt=c.install(cfg,self.network,self.frame)
        self.assertEqual(receipt['current'],dict(current_source_vehicles=31,committed=29,before_decision_uncommitted=2))
        self.assertEqual(sum(cfg.network.urban_movements[m]['beta'] for m in c.MEMBERS),1.)
        for m in c.MEMBERS:cfg.network.urban_movements[m]['beta']=before.urban_movements[m]['beta']
        self.assertEqual(vars(cfg.network),vars(before))
    def test_future_before_decision_is_not_pretended_to_have_committed_route(self):
        frame={'vehicles':[[1,55,1,1.,20.,4.,None,None,None,None]]}
        self.assertEqual(c.validate_current(frame,206.)['before_decision_uncommitted'],1)
    def test_unknown_downstream_current_route_rejected(self):
        frame={'vehicles':[[1,1220061200,1,1.,20.,4.,None,None,None,None]]}
        with self.assertRaisesRegex(ValueError,'already downstream'):c.validate_current(frame,206.)
    def test_foreign_committed_route_rejected(self):
        frame=deepcopy(self.frame)
        row=next(r for r in frame['vehicles'] if r[1]==1220061200)
        row[6]=1032.
        with self.assertRaisesRegex(ValueError,'Different current'):c.compile_spec(deepcopy(self.cfg),self.network,frame)
    def test_shared_model_gate_rejected(self):
        cfg=deepcopy(self.cfg);cfg.network.native_input_schedule['inputs']['new']=dict(gate=c.ORIGIN,physical_source='other')
        with self.assertRaisesRegex(ValueError,'Another input'):c.compile_spec(cfg,self.network,self.frame)
    def test_network_edit_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unreviewed physical'):c.compile_spec(deepcopy(self.cfg),self.network+b' ',self.frame)
if __name__=='__main__':unittest.main()
