"""Physical authority, finite capacity, atomic rejection and active signal clock."""
from copy import deepcopy
import json,pickle,unittest
from pathlib import Path
import candidate

HERE=Path(__file__).resolve().parent
A=HERE.parent
ROOT=HERE.parents[4]


class PeeloffTests(unittest.TestCase):
    def setUp(self):
        self.cfg,self.state,_=pickle.loads((A/"citysplit287/forecast2400/initial.pickle").read_bytes())
        self.proof=candidate.document()
        self.plan=json.loads((ROOT/self.proof["selected_plan"]["path"]).read_bytes())

    def test_changes_signal_flag_only_preserves_stock_capacity_routes(self):
        before=deepcopy(self.cfg.network.__dict__)
        state=pickle.dumps(self.state,protocol=5)
        candidate.install(self.cfg,self.plan,self.proof)
        after=deepcopy(self.cfg.network.__dict__)
        after.pop("sc101_peeloff302")
        after["urban_movements"][candidate.MOV].pop("unsignalized")
        self.assertEqual(before,after)
        self.assertEqual(state,pickle.dumps(self.state,protocol=5))

    def test_rejects_head_before_branch_atomically(self):
        self.proof["source_heads"][0]["pos_m"]=190
        before=pickle.dumps(self.cfg,protocol=5)
        with self.assertRaisesRegex(ValueError,"before every"):
            candidate.install(self.cfg,self.plan,self.proof)
        self.assertEqual(before,pickle.dumps(self.cfg,protocol=5))

    def test_rejects_changed_receiver_atomically(self):
        self.cfg.network.urban_movements[candidate.MOV]["receiving_link"]="SC101_to_SC1002"
        before=pickle.dumps(self.cfg,protocol=5)
        with self.assertRaisesRegex(ValueError,"semantics"):
            candidate.install(self.cfg,self.plan,self.proof)
        self.assertEqual(before,pickle.dumps(self.cfg,protocol=5))

    def test_native_clock_removes_only_false_red_gate(self):
        from evaluation.controllers import signal_actuation_contract as signals
        from evaluation.controllers import vissim_stackelberg_adapter as adapter
        from src.models.state import ControlAction
        c=adapter.control_from_json(A.parent/"selection2400_discrete/hold/action_002400.json",self.cfg,ControlAction)
        spec=self.cfg.network.urban_movements[candidate.MOV]
        fractions=[signals.phase_fraction(c,self.cfg,spec,s) for s in range(240,255)]
        self.assertIn(0.0,fractions)
        rate=self.cfg.network.movement_capacity_by_movement_veh_h[candidate.MOV]
        storage=deepcopy(self.cfg.network.urban_link_storage_veh)
        candidate.install(self.cfg,self.plan,self.proof)
        spec=self.cfg.network.urban_movements[candidate.MOV]
        self.assertEqual([signals.phase_fraction(c,self.cfg,spec,s) for s in range(240,255)],[1.0]*15)
        self.assertEqual(self.cfg.network.movement_capacity_by_movement_veh_h[candidate.MOV],rate)
        self.assertEqual(self.cfg.network.urban_link_storage_veh,storage)


if __name__=="__main__":unittest.main()

