"""A queue for another destination can block a one-lane off-ramp receiver."""
import copy
from types import SimpleNamespace as NS
import unittest
from evaluation.controllers.route_choice_corridor import direct_exit_receiving_space


class Buffer:
    def __init__(self, pre=24., post=0.): self.pre, self.post=pre, post
    def snapshot(self):
        return dict(head_ready_veh=self.pre, upstream_travelling_veh=0.,
                    connector_veh=self.pre+self.post)


class SharedLaneReceivingTest(unittest.TestCase):
    def setup_case(self, ready=21., due=10, post=0.):
        self.cfg=NS(network=NS(direct_exit_legsplit=dict(connector='10483',
            shared_lane_receiving=dict(ramp='RM_C10480', storage_veh_to_entry=44.))))
        self.state=NS(lane_ramp_runtime=NS(buffers={'RM_C10480':Buffer(post=post)}),
            ramp_queue={'RM_C10480':24.+post},
            direct_exit_route_state=dict(cohorts=[dict(target='RM_C10480',vehicles=ready,due=due)]))

    def room(self, connector='10483', step=10, aggregate=900.):
        return direct_exit_receiving_space(self.state,self.cfg,connector,step,aggregate)

    def test_full_shared_lane_blocks_even_with_large_aggregate_room(self):
        self.setup_case()
        self.assertEqual(self.room(),0.)

    def test_releasing_ramp_queue_restores_space_without_capacity_bonus(self):
        self.setup_case(ready=15.)
        self.assertEqual(self.room(),5.)
        self.state.lane_ramp_runtime.buffers['RM_C10480'].pre=20.
        self.state.ramp_queue['RM_C10480']=20.
        self.assertEqual(self.room(),9.)
        self.assertEqual(self.room(aggregate=2.),2.)

    def test_inflight_city_arrivals_and_other_destinations_are_not_stopped_queue(self):
        self.setup_case(due=11)
        self.state.direct_exit_route_state['cohorts'].append(dict(target='free',vehicles=100.,due=0))
        self.assertEqual(self.room(),20.)
        self.assertEqual(self.room(step=11),0.)

    def test_posthead_cars_do_not_extend_red_queue_and_pending_entries_do(self):
        self.setup_case(ready=15.,post=10.)
        self.assertEqual(self.room(),5.)
        self.state.ramp_queue['RM_C10480']+=2.
        self.assertEqual(self.room(),3.)

    def test_no_stock_mutation_or_double_count_and_other_offramps_unchanged(self):
        self.setup_case()
        before=copy.deepcopy(vars(self.state))
        self.assertEqual(self.room(connector='10481'),900.)
        self.room()
        self.assertEqual(self.state.ramp_queue,before['ramp_queue'])
        self.assertEqual(self.state.direct_exit_route_state,before['direct_exit_route_state'])

    def test_disabled_is_exact_old_aggregate_room(self):
        self.setup_case()
        self.cfg.network.direct_exit_legsplit.pop('shared_lane_receiving')
        self.assertEqual(self.room(),900.)


if __name__=='__main__':unittest.main()
