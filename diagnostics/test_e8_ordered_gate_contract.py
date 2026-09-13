"""Algebraic gate requirements only; no calibrated traffic predictor is implied."""
import copy
import unittest
from diagnostics.probe_e8_ordered_gate_observability import transfer_partition


class GateContractTests(unittest.TestCase):
    def test_same_macro_stock_and_speed_do_not_identify_lane_eligibility(self):
        # Same total and declared mean speed; only the discarded lane labels
        # differ. Unlimited service/receiver is a diagnostic algebraic bound.
        observed={'E9_direct_lane1':8.,'E9_direct_other_lanes':38.,'direct10682':0.}
        alias={'E9_direct_lane1':46.,'E9_direct_other_lanes':0.,'direct10682':0.}
        self.assertEqual(sum(observed.values()),sum(alias.values()))
        _,n0=transfer_partition(observed,'E9_direct_lane1','direct10682',46.,46.,eligible=True)
        _,n1=transfer_partition(alias,'E9_direct_lane1','direct10682',46.,46.,eligible=True)
        self.assertEqual((n0,n1),(8.,46.))

    def test_ineligible_lane_stock_remains_and_counts_as_residence(self):
        initial={'E9_direct_lane1':8.,'E9_direct_other_lanes':38.,'direct10682':0.}
        result,n=transfer_partition(initial,'E9_direct_other_lanes','direct10682',38.,46.,eligible=False)
        self.assertEqual(n,0.);self.assertEqual(result,initial)
        self.assertEqual(sum(result.values())*10/3600,46*10/3600)

    def test_explicit_exchange_changes_eligibility_without_creating_stock(self):
        initial={'E9_direct_lane1':8.,'E9_direct_other_lanes':38.,'direct10682':0.}
        before=copy.deepcopy(initial)
        candidate,n=transfer_partition(initial,'E9_direct_other_lanes','E9_direct_lane1',1.,1.,eligible=True)
        candidate,served=transfer_partition(candidate,'E9_direct_lane1','direct10682',9.,9.,eligible=True)
        self.assertEqual((n,served),(1.,9.));self.assertEqual(sum(candidate.values()),46.)
        self.assertEqual(initial,before)

    def test_physical_order_does_not_allow_exit_before_its_node(self):
        state={'E8_after_10639_route1134_3':2.,'E9_through':0.,'direct10682':0.}
        state,n=transfer_partition(state,'E8_after_10639_route1134_3','direct10682',2.,2.,eligible=False)
        self.assertEqual(n,0.)
        state,n=transfer_partition(state,'E8_after_10639_route1134_3','E9_through',2.,2.,eligible=True)
        self.assertEqual(n,2.);self.assertEqual(state['direct10682'],0.);self.assertEqual(sum(state.values()),2.)

    def test_receiving_rejection_remains_at_source_and_repeat_cannot_double_serve(self):
        initial={'source':3.,'receiver':0.}
        state,n=transfer_partition(initial,'source','receiver',8.,1.,eligible=True)
        self.assertEqual((n,state['source']),(1.,2.))
        state,n=transfer_partition(state,'source','receiver',8.,0.,eligible=True)
        self.assertEqual((n,state['source']),(0.,2.));self.assertEqual(sum(state.values()),3.)


if __name__=='__main__':
    unittest.main()
