import copy
import unittest
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.transfer331.inputs import validate, require_past

class CurrentInputs(unittest.TestCase):
    def setUp(self):
        self.raw = dict(sim_sec=3300, vehicle_records=dict(
            complete=True, paused_at_sim_sec=3300, capture_sim_sec_before=3300,
            capture_sim_sec_after=3300, records=[dict(veh_no=1, link_no=68,
            lane_no=1, position_m=2., speed_kph=0.)]))
        self.frame = dict(schema='lane-plant-frame/v1', complete=True, time_s=3300,
                          vehicles=[[1,68,1,2.,0.]])
    def test_stale_development_frame_rejected(self):
        validate(self.raw,self.frame,3300)
        old=copy.deepcopy(self.frame);old['time_s']=2400
        with self.assertRaises(ValueError):validate(self.raw,old,3300)
    def test_same_count_different_vehicle_rejected(self):
        bad=copy.deepcopy(self.frame);bad['vehicles'][0][0]=2
        with self.assertRaises(ValueError):validate(self.raw,bad,3300)
    def test_fixed_support_is_past_not_future(self):
        require_past(2400,3300)
        with self.assertRaises(ValueError):require_past(2400,2250)

if __name__ == '__main__':unittest.main()
