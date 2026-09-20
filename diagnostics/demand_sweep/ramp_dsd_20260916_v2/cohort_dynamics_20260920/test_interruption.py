"""Physical recipient-follower limits for the optional lateral loss term."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from evaluation.controllers.physical_lane_groups import lane_entry_speed_loss,PhysicalLaneGroups
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.lane_group_response_20260919.test_lane_groups import LaneGroupTests,ch
import copy
import unittest


class InterruptionTests(unittest.TestCase):
    def test_only_slower_entrants_disrupt_existing_recipient_followers(self):
        request=[[0.,2.],[0.,0.]]
        self.assertEqual(lane_entry_speed_loss(request,[50.,80.],[10.,20.],[8.,22.],.5),[0.,30/22])
        self.assertEqual(lane_entry_speed_loss(request,[80.,50.],[10.,20.],[8.,22.],.5),[0.,0.])

    def test_no_loss_for_empty_recipient_or_zero_entries(self):
        self.assertEqual(lane_entry_speed_loss([[0.,2.],[0.,0.]],[50.,80.],[10.,0.],[8.,2.],.5),[0.,0.])
        self.assertEqual(lane_entry_speed_loss([[0.,0.],[0.,0.]],[50.,80.],[10.,20.],[10.,20.],.5),[0.,0.])

    def test_term_preserves_stocks_and_has_no_action_reward(self):
        before=[10.,20.];after=[8.,22.];request=[[0.,2.],[0.,0.]]
        saved=copy.deepcopy((before,after,request))
        a=lane_entry_speed_loss(request,[50.,80.],before,after,0.)
        self.assertEqual(a,[0.,0.]);self.assertEqual((before,after,request),saved)

    def test_invalid_gamma_rejected(self):
        fixture=LaneGroupTests();fixture.setUpClass();spec,state,cfg=fixture.fixture()
        for value in [-1.,1.01,True,float('nan')]:
            with self.assertRaises(ValueError):PhysicalLaneGroups(spec,state,cfg,ch.accounting,interruption_gamma=value)


if __name__=='__main__':unittest.main()
