import math
import unittest
from evaluation.controllers.physical_lane_groups import receiving_limited_speed as response


class ReceivingSpeedResponseTests(unittest.TestCase):
    def test_unrestricted_and_zero_request_are_exact(self):
        self.assertEqual(response(87.123,70.,2.,2.,5.,12.),87.123)
        self.assertEqual(response(87.123,70.,0.,0.,5.,12.),87.123)

    def test_only_decelerates_and_does_not_change_flux_operands(self):
        for request,accepted in ((1.,0.),(1.,.5),(1.,1.)):
            value=response(90.,60.,request,accepted,5.,12.)
            self.assertGreaterEqual(value,0.)
            self.assertLessEqual(value,90.)
        self.assertEqual(response(20.,100.,1.,.5,1.,0.),20.)

    def test_blocked_response_and_instant_limit(self):
        self.assertAlmostEqual(response(60.,60.,1.,0.,5.,10.),60.*math.exp(-.5))
        self.assertEqual(response(80.,60.,1.,.5,1.,0.),30.)

    def test_constant_blockage_time_subdivision(self):
        speed=60.
        for _ in range(5):speed=response(speed,speed,1.,0.,1.,10.)
        self.assertAlmostEqual(speed,response(60.,60.,1.,0.,5.,10.))

    def test_limited_flow_does_not_force_a_recovering_speed_above_its_prediction(self):
        self.assertEqual(response(20.,80.,1.,.5,1.,12.),20.)

    def test_invalid_operands_fail(self):
        for values in ((10.,10.,1.,2.,1.,10.),(10.,10.,1.,.5,0.,10.),
                       (10.,10.,1.,.5,1.,-1.),(float('nan'),10.,1.,.5,1.,10.),
                       (10.,10.,1.,.5,1.,True)):
            with self.assertRaises(ValueError):response(*values)


if __name__=='__main__':unittest.main()
