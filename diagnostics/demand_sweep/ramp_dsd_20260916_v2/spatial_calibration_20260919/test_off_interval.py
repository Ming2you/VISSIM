"""Independent service-clock cases; defaults retain archived time semantics."""
import unittest
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response
from canonical_harness import DelayedPort

class DrainClockTests(unittest.TestCase):
    def port(self, positions, new=True):
        return DelayedPort(20., 100., 36., [[p,36.,1] for p in positions], 0., interval_service=new)

    def test_arrival_mid_interval_uses_only_remaining_service(self):
        p=self.port([50.])
        self.assertAlmostEqual(p.release(0.,10.,360.),.5)
        self.assertAlmostEqual(p.stock,.5)
        self.assertAlmostEqual(p.stock-p.initial+p.departed,0.)

    def test_unused_early_service_not_banked(self):
        p=self.port([10.])
        self.assertAlmostEqual(p.release(0.,10.,360.),.1)

    def test_service_not_used_before_arrival_at_endpoint(self):
        p=self.port([0.])
        self.assertEqual(p.release(0.,10.,3600.),0.)
        self.assertEqual(p.release(10.,10.,3600.),1.)

    def test_independent_event_partition(self):
        p=self.port([80.,30.]);q=self.port([80.,30.])
        whole=p.release(0.,10.,360.)
        split=q.release(0.,4.,360.)+q.release(4.,6.,360.)
        self.assertAlmostEqual(whole,.8)
        self.assertAlmostEqual(split,whole)
        self.assertAlmostEqual(q.stock,p.stock)

    def test_no_mass_created_or_admission_advanced(self):
        p=self.port([50.]);p.release(0.,10.,360.)
        p.accept(10.,2.)
        self.assertAlmostEqual(p.release(10.,10.,360.),.5)
        self.assertAlmostEqual(p.stock,2.)
        self.assertAlmostEqual(p.release(20.,10.,360.),1.)
        self.assertAlmostEqual(p.stock-p.initial-p.admitted+p.departed,0.)

    def test_default_clock_unchanged(self):
        p=self.port([50.],False)
        self.assertEqual(p.release(0.,10.,360.),0.)
        self.assertEqual(p.release(10.,10.,360.),1.)

    def test_no_overlapping_new_intervals(self):
        p=self.port([50.]);p.release(0.,10.,360.)
        with self.assertRaises(ValueError):p.release(9.,10.,360.)

if __name__=='__main__':unittest.main()
