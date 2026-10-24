"""Integrate periodic service over an interval, without one-second sampling.

The ramp input is the existing calibrated cycle-mean service. Green-time
overlap only distributes that service in time; it is not another green factor
on the calibrated mean. This is potential service; receiving and ready stock
must still limit actual discharge.
"""
import math
from evaluation.controllers.sdmpc_dual import primal


def green_seconds(start_sec, duration_sec, cycle_sec, green_sec, offset_sec=0.):
    if (not all(math.isfinite(primal(v)) for v in
                (start_sec,duration_sec,cycle_sec,green_sec,offset_sec))
            or duration_sec<0 or cycle_sec<=0 or not 0<=green_sec<=cycle_sec):
        raise ValueError('Invalid periodic signal interval')

    def integral(second):
        phase=second-offset_sec
        cycles=math.floor(primal(phase)/cycle_sec)
        return cycles*green_sec+min(phase-cycles*cycle_sec,green_sec)

    return integral(start_sec+duration_sec)-integral(start_sec)


def meter_service_vehicles(mean_vph, start_sec, duration_sec, cycle_sec, green_sec, offset_sec=0.):
    if not math.isfinite(primal(mean_vph)) or mean_vph<0:
        raise ValueError('Invalid calibrated cycle-mean service')
    overlap=green_seconds(start_sec,duration_sec,cycle_sec,green_sec,offset_sec)
    if green_sec==0:
        if mean_vph!=0:
            raise ValueError('Zero-green calibrated service must be zero')
        return 0.
    return mean_vph*cycle_sec/green_sec*overlap/3600.
