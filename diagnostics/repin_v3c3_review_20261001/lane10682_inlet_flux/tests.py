import copy
import importlib.util
import json
from pathlib import Path
import unittest
from evaluation.controllers.physical_lane_groups import RouteLaneRegion

HERE = Path(__file__).resolve().parent
path = HERE.parent/'lane10682_target_transport/tests.py'
spec = importlib.util.spec_from_file_location('access_tests', path)
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)


class InletFlux(unittest.TestCase):
    def fixture(self, observations, **overrides):
        state,cfg,joint = previous.old.fixture(True)
        cfg.network.offramp_route_inventory.update(
            bounds={'FW_E':[0.,1000.,1100.,2100.,3100.,4100.]}, physical={'1':['FW_E',0.]})
        config = dict(cells=[2,3], lanes=3, exchange_rates_per_sec=joint.rates,
            inlet_lane_to_group={'1':0,'2':1,'3':2},off_access={'exit':[0,1]},
            ramp_access={'ramp':[0]},destination_approach=True,
            inlet_observation_distance_m=500.,inlet_estimator='current_window_flux')
        config.update(overrides)
        before = copy.deepcopy(state.offramp_route_inventory_state)
        result = RouteLaneRegion(config,state,cfg,'FW_E',observations)
        self.assertEqual(before,state.offramp_route_inventory_state)
        return result

    @staticmethod
    def row(lane, position, speed, target='terminal', count=1.):
        return (dict(link_no=1,position_m=position,lane_no=lane,speed_kph=speed),
                'FW_E',1 if position>=1000 else 0,{'test|'+target:count})

    def test_all_destinations_use_current_flux_not_tiny_previous_cell(self):
        rows=[self.row(1,1050,10),self.row(2,900,80),self.row(3,800,40)]
        joint=self.fixture(rows)
        for got,want in zip(joint.inlet['terminal'],[1/13,8/13,4/13]):
            self.assertAlmostEqual(got,want)
        self.assertEqual(joint.inlet_evidence['terminal'],'current_upstream_window_flux')
        self.assertAlmostEqual(sum(joint.inlet['terminal']),1.)

    def test_stationary_queue_uses_counts_and_preserves_current_wrong_lane_stock(self):
        joint=self.fixture([self.row(2,1050,0.,'exit'),self.row(3,900,0.,'exit',2.)])
        self.assertEqual(joint.inlet['exit'],[0.,1/3,2/3])
        self.assertGreater(joint.stocks[2][2]['b|exit'],0.)
        self.assertEqual(joint.inlet_evidence['exit'],'current_upstream_window_stationary_counts')

    def test_outside_window_has_no_effect_and_empty_exit_uses_geometry(self):
        joint=self.fixture([self.row(1,1050,10),self.row(2,500,10000)])
        self.assertEqual(joint.inlet['terminal'],[1.,0.,0.])
        self.assertEqual(joint.inlet['exit'],[.5,.5,0.])

    def test_invalid_mode_and_speed_fail_closed(self):
        with self.assertRaises(ValueError):self.fixture([],inlet_estimator='magic')
        with self.assertRaises(ValueError):self.fixture([],destination_approach=False)
        with self.assertRaises(ValueError):self.fixture([self.row(1,1050,float('nan'))])
        with self.assertRaises(ValueError):self.fixture([self.row(1,1050,-1)])


if __name__=='__main__':
    target=HERE/'tests.json'; assert not target.exists()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(previous.DestinationApproach)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(InletFlux))
    path=HERE.parent/'lane10682_feasibility/check_partition.py'
    spec=importlib.util.spec_from_file_location('partition_tests',path)
    part=importlib.util.module_from_spec(spec);spec.loader.exec_module(part)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(part.Partition))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    target.write_text(json.dumps(dict(tests=result.testsRun,passed=result.wasSuccessful(),
        failures=len(result.failures),errors=len(result.errors)),indent=2)+'\n')
    raise SystemExit(not result.wasSuccessful())
