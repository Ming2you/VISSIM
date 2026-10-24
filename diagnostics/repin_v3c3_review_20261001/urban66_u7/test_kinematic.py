import ast
import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

from evaluation.controllers.observation_projection import initialize_kinematic_arrivals, ProjectionError
from evaluation.controllers.physical_ramp_branches import split_tagged_arrival
from src.models.urban_queue_model import _inflow_delay_steps

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
B=json.loads((HERE/'before.json').read_bytes())
C=json.loads((HERE/'contract.json').read_bytes())
SOURCE=B['source']

class KinematicTests(unittest.TestCase):
    def setUp(self):
        self.queues={ast.literal_eval(k):v for k,v in B['lane_queues'].items()}
        self.adapter=NS(_ARRIVAL_TAU_MOVING_SEC=15.,_ARRIVAL_TAU_STOPPED_SEC=105.,
                        _contiguous_stopline_queue=lambda raw,per_lane: self.queues)
        self.state=NS(time_sec=2700.,urban_movement_queue=copy.deepcopy(B['queue']),
            local_observation_summary={'projection_diagnostics':{'physical_stock_assignment_by_link':{'66':copy.deepcopy(B['projection'])}}},
            urban_arrival_buffer={SOURCE:{int(k):v for k,v in B['arrival'].items()}},
            urban_storage_release_buffer={SOURCE:{int(k):v for k,v in B['release'].items()}},
            gate_initial_route_tags={'unrelated':{1:{'m':2}}})
        self.cfg=NS(network=NS(urban_movements=copy.deepcopy(B['movement_specs']),physical_ramp_branches={},
                   urban_boundary_link_length_m=468.,urban_avg_speed_km_h=50.),simulation=NS(T_u_sec=1.,T_u_h=1/3600.))
        self.raw={'vehicle_records':{'complete':True,'records':copy.deepcopy(B['current_records'])}}
        self.tuning={'urban':{'arrival':{'kinematic_contract':str((HERE/'contract.json').relative_to(ROOT))}}}
        self.detectors={'link_to_origins':B['detector_origins']}

    def run_projection(self):
        with patch('src.models.urban_queue_model.approach_routing',return_value={SOURCE:list(B['routing'].items())}), \
             patch('evaluation.controllers.network_provenance.snapshot_network_sha256',return_value=C['network']['sha256']):
            return initialize_kinematic_arrivals(self.adapter,self.state,self.cfg,self.tuning,self.raw,self.detectors)

    def test_disabled_no_mutation(self):
        old=copy.deepcopy(vars(self.state));self.tuning={}
        self.assertEqual(self.run_projection(),{})
        self.assertEqual(old,vars(self.state))

    def test_native37_left_queue_and_passed_right_branch(self):
        self.run_projection()
        self.assertEqual(self.state.urban_movement_queue,
            {'SC1004_S_to_N_SC1003':12.,'SC1004_S_to_E_SC1005':0.,'SC1004_S_to_W':37.})
        self.assertAlmostEqual(sum(self.state.urban_arrival_buffer[SOURCE].values()),126.)
        self.assertEqual(self.state.urban_arrival_buffer,self.state.urban_storage_release_buffer)
        self.assertEqual(self.state.gate_initial_route_tags['unrelated'],{1:{'m':2}})

    def test_consumption_and_copy_preserve_parent_mass(self):
        self.run_projection();other=copy.deepcopy(self.state)
        for step,n in self.state.urban_arrival_buffer[SOURCE].items():
            pairs=split_tagged_arrival(other,self.cfg,SOURCE,step,n,list(B['routing'].items()))
            self.assertAlmostEqual(sum(v for m,v in pairs),n)
        self.assertEqual(other.gate_initial_route_tags[SOURCE],{})
        self.assertTrue(self.state.gate_initial_route_tags[SOURCE])

    def test_gate_delay_only_its_own_source(self):
        self.run_projection()
        self.assertGreater(_inflow_delay_steps(self.cfg,SOURCE),200)
        self.assertEqual(_inflow_delay_steps(self.cfg),34)
        self.assertEqual(_inflow_delay_steps(self.cfg,'elsewhere'),34)

    def test_queued_vehicle_is_not_scheduled_twice(self):
        self.run_projection()
        self.assertAlmostEqual(sum(self.state.urban_movement_queue.values())+
            sum(sum(v.values()) for v in self.state.gate_initial_route_tags[SOURCE].values()),175.)

    def test_forecast_horizon_does_not_delete_distant_vehicle(self):
        self.raw['vehicle_records']['records']=[dict(veh_no=1,link_no=66,lane_no=4,position_m=0.,speed_kph=0.,stopped=True)]
        self.queues={};self.state.urban_movement_queue=dict.fromkeys(B['routing'],0.)
        self.state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']['66']={'storage:'+SOURCE:1.}
        self.state.urban_arrival_buffer={SOURCE:{2805:1.}};self.state.urban_storage_release_buffer=copy.deepcopy(self.state.urban_arrival_buffer)
        self.run_projection();self.assertGreater(min(self.state.urban_arrival_buffer[SOURCE]),3150)
        self.assertEqual(sum(self.state.urban_arrival_buffer[SOURCE].values()),1.)

    def test_physical_owner_overlap_rejected(self):
        self.state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']['66']={'storage:physical_owner':175.}
        with self.assertRaises(ProjectionError):self.run_projection()

    def test_already_tagged_source_rejected(self):
        self.state.gate_initial_route_tags[SOURCE]={}
        with self.assertRaises(ProjectionError):self.run_projection()

    def test_ready_queue_mismatch_rejected(self):
        self.queues[('66','4')]=38.
        with self.assertRaises(ProjectionError):self.run_projection()

    def test_missing_paired_release_rejected(self):
        self.state.urban_storage_release_buffer[SOURCE].pop(2805)
        with self.assertRaises(ProjectionError):self.run_projection()

    def test_incomplete_records_rejected(self):
        self.raw['vehicle_records']['complete']=False
        with self.assertRaises(ProjectionError):self.run_projection()

if __name__=='__main__':unittest.main()
