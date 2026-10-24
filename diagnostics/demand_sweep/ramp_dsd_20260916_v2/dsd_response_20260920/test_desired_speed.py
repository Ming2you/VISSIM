"""Actuator tests only: these do not qualify congestion or control-gain prediction."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from evaluation.controllers.desired_speed_transport import (
    SpeedDistribution, DesiredSpeedCohort, selected_distribution)
import unittest
import math

DISTRIBUTIONS={
    100:SpeedDistribution(((0,88),(.03,95),(.1,100),(.7,110),(.91,120),(1,130))),
    120:SpeedDistribution(((0,85),(.03,105),(.1,110),(.68,125),(.91,140),(1,155)))}


class ActuatorTests(unittest.TestCase):
    def test_native_high_fractile_vehicle_and_restoration(self):
        # Native vehicle19696, first VSL sign at2412..2413. A single scalar
        # speed100 would miss the observed129.662km/h desired speed.
        u=DISTRIBUTIONS[120].fractile(154.493)
        cohort=DesiredSpeedCohort(1.,u,120)
        self.assertAlmostEqual(cohort.cross(100,DISTRIBUTIONS),129.662,delta=.001)
        self.assertAlmostEqual(cohort.cross(120,DISTRIBUTIONS),154.493,delta=.001)
        self.assertEqual(cohort.mass,1.)
        self.assertEqual(cohort.fractile,u)

    def test_native_missed_link_entry_is_already_controlled(self):
        # Vehicle22416 crosses DSD53 in the first sample after entering link2.
        # By DSD57 its speed is already from distribution100, not120.
        cohort=DesiredSpeedCohort(1.,DISTRIBUTIONS[120].fractile(151.244),120)
        self.assertAlmostEqual(cohort.cross(100,DISTRIBUTIONS),127.496,delta=.001)
        self.assertAlmostEqual(cohort.cross(100,DISTRIBUTIONS),127.496,delta=.001)

    def test_command_is_not_retroactive_or_instantaneous_cell_cap(self):
        events=[(2400,100),(2700,120)]
        cohort=DesiredSpeedCohort(2.5,.8,120)
        original=cohort.desired_speed(DISTRIBUTIONS)
        selected_distribution(120,events,2500)
        self.assertEqual(cohort.desired_speed(DISTRIBUTIONS),original)
        self.assertEqual(selected_distribution(120,events,2400),120)
        self.assertEqual(selected_distribution(120,events,2400.1),100)
        cohort.cross(selected_distribution(120,events,2400.1),DISTRIBUTIONS)
        selected_distribution(120,events,2750)
        self.assertEqual(cohort.distribution_id,100)
        self.assertEqual(cohort.mass,2.5)

    def test_quantile_inverse_and_moments(self):
        for d in DISTRIBUTIONS.values():
            for u in [0,.001,.03,.1,.2,.68,.7,.8,.91,.977464,1]:
                self.assertAlmostEqual(d.fractile(d.quantile(u)),u,places=12)
        self.assertAlmostEqual(DISTRIBUTIONS[120].moments()['mean_kmh'],122.275)
        self.assertAlmostEqual(DISTRIBUTIONS[100].moments()['mean_kmh'],107.970)
        self.assertGreater(DISTRIBUTIONS[120].moments()['sd_kmh'],DISTRIBUTIONS[100].moments()['sd_kmh'])

    def test_invalid_values_fail_explicitly(self):
        for points in [((.1,1),(1,2)),((0,1),(1,1)),((0,1),(.5,3),(.5,4),(1,5))]:
            with self.assertRaises(ValueError):SpeedDistribution(points)
        for u in [-.1,1.1,math.nan]:
            with self.assertRaises(ValueError):DISTRIBUTIONS[120].quantile(u)
        with self.assertRaises(ValueError):DISTRIBUTIONS[100].fractile(154.)
        with self.assertRaises(ValueError):selected_distribution(120,[(2700,100),(2400,120)],2800)
        with self.assertRaises(ValueError):DesiredSpeedCohort(-1,.5,120).cross(100,DISTRIBUTIONS)


if __name__=='__main__':unittest.main()
