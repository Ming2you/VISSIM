"""Accepted-flow velocity transport invariants."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from evaluation.controllers.physical_lane_groups import advected_speed
import unittest


class MomentumTests(unittest.TestCase):
    def test_equal_speed_is_preserved_across_unequal_counts(self):
        self.assertEqual(advected_speed(10.,80.,3.,7.*80.,14.),80.)

    def test_conservative_mixing_stays_between_donor_speeds(self):
        actual=advected_speed(10.,50.,2.,4.*100.,12.)
        self.assertAlmostEqual(actual*12.,8.*50.+4.*100.)
        self.assertGreaterEqual(actual,50.);self.assertLessEqual(actual,100.)

    def test_no_flow_preserves_speed_and_overdraw_fails(self):
        self.assertEqual(advected_speed(10.,50.,0.,0.,10.),50.)
        self.assertEqual(advected_speed(0.,50.,0.,0.,0.),50.)
        with self.assertRaises(ArithmeticError):advected_speed(1.,50.,2.,0.,0.)


if __name__=='__main__':unittest.main()
