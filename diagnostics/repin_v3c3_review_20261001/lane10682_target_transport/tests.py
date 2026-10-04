import copy
import importlib.util
import json
from pathlib import Path
import unittest
from evaluation.controllers.physical_lane_groups import RouteLaneRegion

HERE=Path(__file__).resolve().parent
path=HERE.parent/'lane10682_transport/tests.py'
spec=importlib.util.spec_from_file_location('previous_transport_tests',path)
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)

class DestinationApproach(old.Transfers):
    def test_route_conditioned_moves_preserve_exit_access_and_through_rates(self):
        state,cfg,joint=old.fixture(True);joint.destination_approach=True
        runtime=cfg.network.offramp_route_inventory
        self.assertEqual(joint.class_exchange_rates('b|exit',2,0,runtime),[0.,0.,0.])
        self.assertEqual(joint.class_exchange_rates('b|exit',2,2,runtime),[0.,.02,0.])
        self.assertEqual(joint.class_exchange_rates('a|terminal',2,1,runtime),joint.rates[1])
        joint.off_access['exit']=(0,1)
        self.assertEqual(joint.class_exchange_rates('b|exit',2,1,runtime),[.02,0.,0.])
        self.assertEqual(joint.class_exchange_rates('b|exit',3,1,runtime),joint.rates[1])

    def test_enabled_transport_conserves_classes_and_does_not_teleport(self):
        state,cfg,joint=old.fixture(True);joint.destination_approach=True
        before=copy.deepcopy(joint.stocks)
        self.advance(state,cfg,joint,0.)
        self.assertGreater(joint.stocks[2][2]['b|exit'],.9*before[2][2]['b|exit'])
        for _ in range(119):self.advance(state,cfg,joint)
        self.assertLess(joint.max_residual,1e-9)

    def inlet_fixture(self,observations):
        state,cfg,previous=old.fixture(True)
        runtime=cfg.network.offramp_route_inventory
        runtime.update(bounds={'FW_E':[0.,1000.,1100.,2100.,3100.,4100.]},physical={'1':['FW_E',0.]})
        spec=dict(cells=[2,3],lanes=3,exchange_rates_per_sec=previous.rates,
            inlet_lane_to_group={'1':0,'2':1,'3':2},off_access={'exit':[0,1]},
            ramp_access={'ramp':[0]},destination_approach=True,inlet_observation_distance_m=500.)
        before=copy.deepcopy(state.offramp_route_inventory_state)
        joint=RouteLaneRegion(spec,state,cfg,'FW_E',observations)
        self.assertEqual(before,state.offramp_route_inventory_state)
        return joint

    def test_no_sample_geometry_prior_only_partitions_future_inlet(self):
        joint=self.inlet_fixture([])
        self.assertEqual(joint.inlet['exit'],[.5,.5,0.])
        self.assertGreater(joint.stocks[2][2]['b|exit'],0.)
        self.assertEqual(joint.inlet_evidence['exit'],'geometry_prior_no_current_sample')

    def test_current_nearby_observation_replaces_missing_previous_cell(self):
        physical=dict(link_no=1,position_m=900.,lane_no=2,speed_kph=72.)
        joint=self.inlet_fixture([(physical,'FW_E',0,{'b|exit':1.})])
        self.assertEqual(joint.inlet['exit'],[0.,1.,0.])
        self.assertEqual(joint.inlet_evidence['exit'],'current_upstream_window')

    def test_existing_previous_cell_wrong_lane_observation_is_not_relocated(self):
        physical=dict(link_no=1,position_m=1050.,lane_no=3,speed_kph=72.)
        joint=self.inlet_fixture([(physical,'FW_E',1,{'b|exit':1.})])
        self.assertEqual(joint.inlet['exit'],[0.,0.,1.])
        self.assertEqual(joint.inlet_evidence['exit'],'current_previous_cell')

if __name__=='__main__':
    target=HERE/'tests.json';assert not target.exists()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(DestinationApproach)
    path=HERE.parent/'lane10682_feasibility/check_partition.py'
    spec=importlib.util.spec_from_file_location('partition_tests',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(m.Partition))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    target.write_text(json.dumps(dict(tests=result.testsRun,errors=len(result.errors),failures=len(result.failures),passed=result.wasSuccessful()),indent=2)+'\n')
    raise SystemExit(not result.wasSuccessful())
