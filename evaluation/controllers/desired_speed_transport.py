"""Desired-speed distribution IDs and point-actuated vehicle cohorts.

Pure actuator semantics, separate from congestion dynamics. The numeric ID is
never a speed cap. Fractiles persist when a vehicle crosses another decision.
"""
from bisect import bisect_left
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class SpeedDistribution:
    points: tuple[tuple[float, float], ...]  # (fractile, speed km/h)

    def __post_init__(self):
        if len(self.points)<2 or self.points[0][0]!=0 or self.points[-1][0]!=1:
            raise ValueError('A distribution must cover fractiles0..1')
        if any(not math.isfinite(x) for p in self.points for x in p):raise ValueError('Nonfinite distribution')
        if any(a[0]>=b[0] or a[1]>=b[1] for a,b in zip(self.points,self.points[1:])):
            raise ValueError('This cohort implementation requires strictly increasing CDF knots')

    def quantile(self, fractile):
        if not math.isfinite(fractile) or not 0<=fractile<=1:raise ValueError('Invalid persistent fractile')
        i=max(1,bisect_left([p[0] for p in self.points],fractile))
        a,b=self.points[i-1],self.points[i]
        return a[1]+(fractile-a[0])*(b[1]-a[1])/(b[0]-a[0])

    def fractile(self, speed, rounding_tolerance=.00051):
        if not math.isfinite(speed) or speed<self.points[0][1]-rounding_tolerance or speed>self.points[-1][1]+rounding_tolerance:
            raise ValueError('Desired speed outside the declared distribution')
        speed=min(self.points[-1][1],max(self.points[0][1],speed))
        i=max(1,bisect_left([p[1] for p in self.points],speed))
        a,b=self.points[i-1],self.points[i]
        return a[0]+(speed-a[1])*(b[0]-a[0])/(b[1]-a[1])

    def moments(self):
        mean=sum((b[0]-a[0])*(a[1]+b[1])/2 for a,b in zip(self.points,self.points[1:]))
        second=sum((b[0]-a[0])*(a[1]**2+a[1]*b[1]+b[1]**2)/3 for a,b in zip(self.points,self.points[1:]))
        return {'mean_kmh':mean,'sd_kmh':math.sqrt(max(0.,second-mean*mean))}


@dataclass
class DesiredSpeedCohort:
    mass: float
    fractile: float
    distribution_id: int

    def cross(self, distribution_id, distributions):
        if not math.isfinite(self.mass) or self.mass<0:raise ValueError('Invalid cohort mass')
        value=distributions[distribution_id].quantile(self.fractile)
        self.distribution_id=distribution_id
        return value

    def desired_speed(self, distributions):
        return distributions[self.distribution_id].quantile(self.fractile)


def selected_distribution(native_id, events, crossing_sec):
    """Commands are written after the native frame at t. No retroactive update."""
    selected=native_id
    last=-math.inf
    for sec,distribution in events:
        if sec<=last:raise ValueError('Decision commands must be strictly ordered')
        last=sec
        if crossing_sec>sec:selected=distribution
    return selected
