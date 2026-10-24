"""Boundary tests for the narrowly scoped offline source-service candidate."""
from copy import deepcopy
from pathlib import Path
import pickle,unittest
import candidate

HERE=Path(__file__).resolve().parent


class SourceCandidateTests(unittest.TestCase):
    def setUp(self):
        self.cfg,self.state,_=pickle.loads((HERE.parent/'citysplit287/forecast2400/initial.pickle').read_bytes())
        self.cal=candidate.document()

    def test_changes_only_two_head_service_rates(self):
        before=deepcopy(self.cfg.network.route_choice_corridor)
        state=pickle.dumps(self.state,protocol=5)
        result=candidate.install(self.cfg,2400,self.cal)
        self.assertEqual(set(result),{'1086','1087'})
        after=deepcopy(self.cfg.network.route_choice_corridor)
        for spec in after['corridors']:
            inp=next((k for k in result if k in spec.get('generated_inputs',{})),None)
            if inp is not None:
                self.assertEqual(spec['native_fixed_service']['calibrated_service_veh_h'],result[inp]['new'])
                spec['native_fixed_service']['calibrated_service_veh_h']=result[inp]['old']
        self.assertEqual(before,after)
        self.assertEqual(state,pickle.dumps(self.state,protocol=5))

    def test_future_support_is_rejected_without_partial_change(self):
        before=pickle.dumps(self.cfg,protocol=5)
        with self.assertRaisesRegex(ValueError,'precede'):
            candidate.install(self.cfg,2390,self.cal)
        self.assertEqual(before,pickle.dumps(self.cfg,protocol=5))

    def test_wrong_source_fails_atomically(self):
        for spec in self.cfg.network.route_choice_corridor['corridors']:
            if spec['decision']=='1100':spec['native_fixed_service']['controller']='16'
        before=pickle.dumps(self.cfg,protocol=5)
        with self.assertRaisesRegex(ValueError,'identity'):
            candidate.install(self.cfg,2400,self.cal)
        self.assertEqual(before,pickle.dumps(self.cfg,protocol=5))


if __name__=='__main__':unittest.main()
