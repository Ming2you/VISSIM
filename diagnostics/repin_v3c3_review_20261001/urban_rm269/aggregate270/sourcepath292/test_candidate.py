import math
import unittest
from candidate import delay_steps,installed,MODE


class DelayChecks(unittest.TestCase):
    def test_lane_multiplier_and_urban_ticks(self):
        self.assertEqual(delay_steps(500,100,2,50,10),4)
        self.assertEqual(delay_steps(500,50,1,50,10),4)
        self.assertEqual(delay_steps(500,100,2,50,1),36)


    def test_source_specific_distance(self):
        self.assertEqual(delay_steps(634.584,64.2558734,2.5516,50,10),10)
        self.assertEqual(delay_steps(457.0548,64.2558734,2.5516,50,10),7)


    def test_invalid_speed(self):
        for speed in (-1,math.inf,math.nan):
            with self.subTest(speed=speed),self.assertRaises(ValueError):
                delay_steps(100,speed,2,50,10)


    def test_disabled_is_noop(self):
        from evaluation.controllers import urban_flow_accounting as ufa,native_internal_input as nii
        from src.models import urban_queue_model as uqm
        before=ufa._receive_corridor,nii.advance,uqm._link_delay_steps
        with installed(None,None,None) as rows:self.assertEqual(rows,[])
        self.assertEqual(before,(ufa._receive_corridor,nii.advance,uqm._link_delay_steps))
        with self.assertRaises(ValueError):
            with installed(None,'invalid',None):pass


    def test_failure_restores_hooks(self):
        from evaluation.controllers import urban_flow_accounting as ufa,native_internal_input as nii
        from src.models import urban_queue_model as uqm
        before=ufa._receive_corridor,nii.advance,uqm._link_delay_steps
        with self.assertRaises(RuntimeError):
            with installed(None,MODE,{}):raise RuntimeError('test')
        self.assertEqual(before,(ufa._receive_corridor,nii.advance,uqm._link_delay_steps))


if __name__=='__main__':unittest.main()
