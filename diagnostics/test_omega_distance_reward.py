"""Whole-area difference reward: negative cost, partition and final gate."""
import copy
from types import SimpleNamespace as NS
import unittest
from evaluation.controllers import omega_distance as distance,sdmpc_terminal as terminal
from evaluation.controllers.sdmpc import omega_costs


def fixture():
    spec=dict(schema=distance.REWARD_SCHEMA,weight_h_per_km=.1,initial_transport=distance.COMMON_INITIAL)
    cfg=NS(network=NS(signals=('SC1',),freeway_links=('FW_E',),sdmpc_distance_reward=spec,
        sdmpc_cost_ownership={'freeway:FW_E':'FW_E','movement:m':'SC1'}))
    observer=distance.TravelReservations(0.,1.,{})
    observer.dynamic_by_stock={'freeway:FW_E':5.,'movement:m':3.}
    observer.steps=observer.local_steps=1
    observer.coverage={'freeway:FW_E':'dynamic_mainline','movement:m':'point_queue'}
    observer.initial_fixed_reservations={}
    final=NS(time_sec=1.,_omega_travel_reservations=observer,
        lane_urban_runtime=NS(off_storage='off',port=NS(lanes=[]),side_port=None))
    point=NS(states=[final],objective=2.,ttt=2.,control_area=dict(near_score_veh_h=2.,
        ttt_veh_h=2.,additional_cost_veh_h=0.),control_area_response=dict(residence=[
        dict(dt_h=.1,inside_veh={'freeway:FW_E':10.,'movement:m':10.})]))
    return cfg,point


class DistanceRewardTests(unittest.TestCase):
    def test_signed_reward_partition_and_final_score(self):
        cfg,point=fixture();distance.finish_reward(point,cfg)
        self.assertAlmostEqual(point.objective,1.2)
        self.assertEqual(point.ttt,2.)
        terminal.validate_score(point.control_area,point.objective,cfg)
        local,part=omega_costs(point,cfg)
        self.assertAlmostEqual(local['FW_E']['cost'],.5)
        self.assertAlmostEqual(local['SC1']['cost'],.7)
        self.assertAlmostEqual(part['total_veh_h'],point.objective)
        self.assertFalse(point.control_area['distance_reward']['absolute_tvd_available'])

    def test_forged_area_term_and_owner_receipts_fail(self):
        cfg,point=fixture();distance.finish_reward(point,cfg)
        for field,value in [('shifted_tvd_veh_km',80.),('omitted_term','all_city'),
                            ('absolute_tvd_available',True),('observed_steps',0)]:
            forged=copy.deepcopy(point.control_area);forged['distance_reward'][field]=value
            with self.assertRaises(ValueError):terminal.validate_score(forged,point.objective,cfg)
        del cfg.network.sdmpc_distance_reward
        with self.assertRaises(ValueError):terminal.validate_score(point.control_area,point.objective,cfg)

    def test_incomplete_physical_steps_fail(self):
        cfg,point=fixture();point.states[-1]._omega_travel_reservations.local_steps=0
        with self.assertRaises(distance.DistanceCoverageError):distance.finish_reward(point,cfg)

    def test_actual_unmapped_generation_fails_not_an_unused_demand_field(self):
        cfg,point=fixture();state=point.states[-1]
        distance.accepted_external_ramp(state,'r',0.)
        with self.assertRaises(distance.DistanceCoverageError):distance.accepted_external_ramp(state,'r',1.)

    def test_final_writer_boundary_accepts_negative_distance_score_and_rejects_other_weight(self):
        from diagnostics.test_joint_leader_result import fixture as joint_fixture
        from evaluation.controllers.area_leader_objective import validate_joint_leader_result
        response=joint_fixture();score=response['final_score']
        cfg,point=fixture()
        cfg.network.signals=tuple('SC'+str(i) for i in range(1,18))
        cfg.network.freeway_links=('FW_E','FW_W')
        cfg.network.ramps=tuple(response['game']['control'].ramp_metering)
        cfg.network.ramp_to_freeway={r:'FW_E' if r.endswith('E') else 'FW_W' for r in cfg.network.ramps}
        cfg.network.control_area_enabled=True;cfg.network.control_area_beta_seconds=0
        point.control_area=dict(score['control_area'],near_score_veh_h=2.,ttt_veh_h=2.,beta_seconds=0.)
        point.states[-1]._omega_travel_reservations.dynamic_by_stock['freeway:FW_E']=50.
        distance.finish_reward(point,cfg)
        score.update(objective_veh_h=point.objective,control_area=point.control_area)
        result=validate_joint_leader_result(response,target_np_veh=340.,target_nuf_veh_h=7200.,cfg=cfg)
        self.assertAlmostEqual(result['objective_value'],-3.3)
        cfg.network.sdmpc_distance_reward['weight_h_per_km']=.2
        with self.assertRaises(ValueError):
            validate_joint_leader_result(response,target_np_veh=340.,target_nuf_veh_h=7200.,cfg=cfg)


if __name__=='__main__':unittest.main()
