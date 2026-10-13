from pathlib import Path
import copy,json,pickle,unittest
from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_sequence as seq
from src.models.state import ControlAction
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.response332.commands import pair,TARGET

class Commands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a=Path(__file__).resolve().parent.parent
        cls.cfg,_,_=pickle.loads((a/'transfer331/build3300_v2/initial.pickle').read_bytes())
        source=Path(json.loads((a/'decision285/full_decision_execution.json').read_bytes())['decisions'])
        cls.reference=seq.first_action(adapter.control_from_json(source/'action_003150.json',cls.cfg,ControlAction))
        cls.cap=adapter.control_from_json(a/'decision285/full3300_current/unused.json',cls.cfg,ControlAction)
    def test_only_target_rm_changes(self):
        arms=pair(self.reference,self.cfg,self.cap)
        self.assertEqual([b.diagnostics['rw_meter_green_'+TARGET] for b in arms['hold']],[2.,2.,2.])
        self.assertEqual([b.diagnostics['rw_meter_green_'+TARGET] for b in arms['release']],[4.,6.,8.])
    def test_actual_reference_unchanged(self):
        before=pickle.dumps(self.reference)
        pair(self.reference,self.cfg,self.cap)
        self.assertEqual(before,pickle.dumps(self.reference))
    def test_wrong_initial_green_rejected(self):
        other=self.reference.copy();other.diagnostics['rw_meter_green_'+TARGET]=4.
        with self.assertRaises(ValueError):pair(other,self.cfg,self.cap)

if __name__=='__main__':unittest.main()
