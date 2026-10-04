import importlib.util
import json
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('handoff_tests',HERE.parent/'ramp10681_lane_handoff/tests.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)


class LaneConflict(unittest.TestCase):
    def fixture(self):
        state,cfg,joint=prior.RampHandoff().fixture()
        joint.stocks[2]=[{'b|exit':8.},{'a|terminal':2.},{'a|terminal':20.}]
        joint.v[2]=[72.,30.,100.]
        return state,cfg,joint

    def test_departing_exit_classes_do_not_conflict_with_merge_downstream(self):
        state,cfg,joint=self.fixture()
        values=joint.ramp_conflicting_flows('ramp',cfg)
        self.assertEqual(values[0],0.)
        self.assertGreater(values[1],0.)
        joint.stocks[2][0]['b|exit']+=4.
        self.assertEqual(values,joint.ramp_conflicting_flows('ramp',cfg))

    def test_unconnected_fast_lane_does_not_limit_receiving_lane_gap(self):
        state,cfg,joint=self.fixture()
        values=joint.ramp_conflicting_flows('ramp',cfg)
        joint.stocks[2][2]['a|terminal']*=2
        joint.v[2][2]=150.
        self.assertEqual(values,joint.ramp_conflicting_flows('ramp',cfg))
        joint.v[2][1]*=.5
        self.assertAlmostEqual(joint.ramp_conflicting_flows('ramp',cfg)[1],values[1]/2)

    def test_conflict_cannot_send_more_than_current_through_stock(self):
        state,cfg,joint=self.fixture();joint.v[2][1]=1e8
        self.assertAlmostEqual(joint.ramp_conflicting_flows('ramp',cfg)[1]*cfg.simulation.T_f_h,2.)
        # The fixture contains cells 1..3; cell 1 has no upstream lane state.
        cfg.network.offramp_route_inventory['merges']['ramp']['cell']=1
        with self.assertRaises(ValueError):joint.ramp_conflicting_flows('ramp',cfg)


if __name__=='__main__':
    target=HERE/'tests_corrected.json';assert not target.exists()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(prior.prior.previous.DestinationApproach)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(prior.prior.InletFlux))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(prior.RampHandoff))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(LaneConflict))
    spec=importlib.util.spec_from_file_location('partition_tests',HERE.parent/'lane10682_feasibility/check_partition.py')
    part=importlib.util.module_from_spec(spec);spec.loader.exec_module(part)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(part.Partition))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    target.write_text(json.dumps(dict(tests=result.testsRun,passed=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors)),indent=2)+'\n')
    raise SystemExit(not result.wasSuccessful())
