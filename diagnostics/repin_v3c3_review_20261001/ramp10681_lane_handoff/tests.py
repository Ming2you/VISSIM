import importlib.util
import json
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('inlet_tests',HERE.parent/'lane10682_inlet_flux/tests.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)


class RampHandoff(unittest.TestCase):
    def fixture(self):
        state,cfg,joint=prior.previous.old.fixture(True)
        joint.ramp_access['ramp']=(0,1)
        joint.preserve_ramp_lanes=True
        return state,cfg,joint

    def plan(self,joint,state,cfg,values):
        joint.plan(state,cfg,[100.]*5,{'exit':10.},[100.]*4,[1000000.]*5,
            {'ramp':360.},{'exit':180.},ramp_group_release_veh_h=values)

    def test_exact_accepted_lane_receipts_are_not_redistributed_to_spare_lane(self):
        state,cfg,joint=self.fixture()
        self.plan(joint,state,cfg,{'ramp':[0.,360.,0.]})
        self.assertEqual(joint.merge[3],[0.,.1,0.])
        self.assertAlmostEqual(sum(joint.merge[3]),.1)

    def test_missing_wrong_sum_and_unconnected_receipts_fail_closed(self):
        for value in (None,{}, {'ramp':[0.,180.,0.]},{'ramp':[0.,0.,360.]},{'ramp':[0.,float('nan'),0.]}):
            state,cfg,joint=self.fixture()
            with self.assertRaises(ValueError):self.plan(joint,state,cfg,value)

    def test_physical_space_is_lane_specific(self):
        state,cfg,joint=self.fixture()
        i=3;capacity=cfg.network.rho_max*joint.lengths[i]
        joint.stocks[i][1]={'a|terminal':capacity}
        space=joint.ramp_lane_supply('ramp',cfg)
        self.assertGreater(space[0],0.)
        self.assertEqual(space[1],0.)
        with self.assertRaises(ArithmeticError):self.plan(joint,state,cfg,{'ramp':[0.,360.,0.]})

    def test_disabled_mode_keeps_legacy_space_weighted_allocation(self):
        state,cfg,joint=self.fixture();joint.preserve_ramp_lanes=False
        self.plan(joint,state,cfg,None)
        self.assertGreater(joint.merge[3][0],0.)
        self.assertGreater(joint.merge[3][1],0.)
        self.assertAlmostEqual(sum(joint.merge[3]),.1)


if __name__=='__main__':
    target=HERE/'tests.json';assert not target.exists()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(prior.previous.DestinationApproach)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(prior.InletFlux))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(RampHandoff))
    spec=importlib.util.spec_from_file_location('partition_tests',HERE.parent/'lane10682_feasibility/check_partition.py')
    part=importlib.util.module_from_spec(spec);spec.loader.exec_module(part)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(part.Partition))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    target.write_text(json.dumps(dict(tests=result.testsRun,passed=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors)),indent=2)+'\n')
    raise SystemExit(not result.wasSuccessful())
