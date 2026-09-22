import unittest
from distribution_response import capped_mean


class DistributionCapTest(unittest.TestCase):
    def test_dispersion_crosses_active_cap(self):
        # Capping the mean misses slow vehicles that remain below the FD cap.
        self.assertEqual(capped_mean([80.,120.],100.),90.)
        self.assertNotEqual(capped_mean([80.,120.],100.),min(100.,(80.+120.)/2))

    def test_uniform_cap_and_free_cases(self):
        self.assertEqual(capped_mean([80.,90.],60.),60.)
        self.assertEqual(capped_mean([80.,90.],120.),85.)

    def test_empirical_weights_are_preserved(self):
        self.assertEqual(capped_mean([80.,120.,120.],110.),100.)

    def test_empty_is_not_zero_speed(self):
        with self.assertRaises(ValueError):capped_mean([],100.)


if __name__=='__main__':unittest.main()
