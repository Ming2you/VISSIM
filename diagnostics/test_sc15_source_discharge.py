import unittest
from diagnostics.audit_sc15_source_discharge import head_crossing,desired

SPEC={'head_position_m':60.,'branches':{'101':{'from_pos_m':65.,'length_m':10.,'target':'201','target_pos_m':2.}},
      'native_rates':[{'start_sec':0,'rate_veh_h':100.},{'start_sec':900,'rate_veh_h':200.}]}
def row(t,pos,link='1'):return {'sec':t,'pos_m':pos,'link':link}
def vehicle(rows,nextrow=None):return {'samples':rows,'first_non_source':nextrow}

class HeadCrossings(unittest.TestCase):
    def test_observed_position_bracket_retains_uncertainty(self):
        result=head_crossing(vehicle([row(10,58),row(11,62)]),SPEC)
        self.assertEqual((result['lower_sec'],result['upper_sec'],result['linear_estimate_sec']),(10,11,10.5))
    def test_connector_gap_uses_verified_source_branch_distance(self):
        result=head_crossing(vehicle([row(10,58)],row(11,3,'101')),SPEC)
        self.assertAlmostEqual(result['linear_estimate_sec'],10.2)
        self.assertEqual(result['method'],'source_to_observed_connector_bracket')
    def test_unique_target_is_explicitly_inferred_not_observed_connector(self):
        result=head_crossing(vehicle([row(10,58)],row(11,5,'201')),SPEC)
        self.assertAlmostEqual(result['linear_estimate_sec'],10.1)
        self.assertEqual(result['method'],'source_to_unique_target_bracket')
    def test_unknown_and_nonconsecutive_departures_remain_unresolved(self):
        for target,t,expected in [('999',11,'unresolved_first_non_source'),('101',12,'unresolved_departure_observation_gap')]:
            self.assertEqual(head_crossing(vehicle([row(10,58)],row(t,3,target)),SPEC)['method'],expected)
    def test_left_and_right_censor_do_not_create_crossings(self):
        self.assertEqual(head_crossing(vehicle([row(10,61)]),SPEC)['method'],'left_censored_before_first_source_sample')
        self.assertEqual(head_crossing(vehicle([row(10,58)]),SPEC)['method'],'right_censored_on_source')
    def test_piecewise_nominal_expectation_does_not_use_current_rate_for_whole_window(self):
        self.assertAlmostEqual(desired(SPEC,450,1350),37.5)

if __name__=='__main__':unittest.main()
