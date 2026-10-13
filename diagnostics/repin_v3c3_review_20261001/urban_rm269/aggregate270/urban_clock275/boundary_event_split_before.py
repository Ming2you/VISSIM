"""Interval service for finite urban boundary components.

This is a component API, not activation of a coarse whole-network urban clock.
The one-second production coupling is unchanged until its other physical
owners and arrival timelines support the same exchange contract.
"""
from __future__ import annotations
import math
import copy


def signal_intervals(control,cfg,lane_specs):
    """Bind the existing native/continuous signal law to absolute intervals.

    The private clock view changes only the averaging interval, never the
    observation state, caller's configuration or installed prediction mode.
    Worker-installed continuous signal hooks are used through the same API.
    """
    from evaluation.controllers import signal_actuation_contract as signals
    view=copy.copy(cfg)
    view.simulation=copy.copy(cfg.simulation)
    def fractions(start,duration):
        if (not math.isfinite(start) or isinstance(duration,bool)
                or not math.isfinite(duration) or not 0<duration<=10):
            raise ValueError('Invalid physical signal averaging interval')
        view.simulation.T_u=duration
        values={lane:signals.phase_fraction(control,view,spec,start/duration)
                for lane,spec in lane_specs.items()}
        if any(value is None for value in values.values()):
            raise ValueError('Coarse urban service requires a verified physical signal clock')
        return values
    return fractions


def advance_shared_interval(approach,start_sec,duration_sec,green_interval,receiving):
    """Advance5/10s with FIFO readiness events and one downstream reservation.

    green_interval(start, duration) must integrate the applied signal over
    that exact interval. A fraction sampled once for the whole macro interval
    cannot be reused after a packet becomes ready. No arrivals are admitted
    during this call; a future scheduler must retain them in their upstream
    owner until the agreed exchange endpoint. Residence uses uniform accepted
    flow within each event interval, as in the existing physical components.
    """
    if (isinstance(duration_sec,bool) or duration_sec not in (1,5,10)
            or not math.isfinite(start_sec) or int(start_sec)!=start_sec
            or start_sec!=approach.time or not callable(green_interval)):
        raise ValueError('Shared approach requires contiguous1/5/10s and an interval signal integral')
    movements={m for row in approach.lanes.values() for m in row['movements']}
    if set(receiving)!=movements or any(not math.isfinite(v) or v<0 for v in receiving.values()):
        raise ValueError('Shared approach needs one complete finite downstream reservation')
    end=start_sec+duration_sec
    cuts=sorted({start_sec,end}|{p[0] for q in approach.queues.values() for p in q if start_sec<p[0]<end})
    intervals=[]
    for a,b in zip(cuts,cuts[1:]):
        green=green_interval(a,b-a)
        if set(green)!=set(approach.lanes) or any(not math.isfinite(v) or not 0<=v<=1 for v in green.values()):
            raise ValueError('Incomplete or invalid interval signal integral')
        intervals.append((a,b-a,green))
    left=dict(receiving)
    result=[];lateral=[]
    for start,duration,green in intervals:
        rows=approach.advance(start,green,left,duration_sec=duration)
        for row in rows:
            target=row['movement']
            left[target]-=row['vehicles']
            if left[target]<-1e-7:
                raise ArithmeticError('Shared approach reused its downstream reservation')
        result.extend(rows);lateral.extend(approach.last_lateral)
    approach.last_lateral=lateral
    approach.last_interval_segments=len(intervals)
    return result


def release_delayed_interval(port,start_sec,duration_sec,service_veh_h,receiving_veh):
    """Drain an ungated delayed port with one finite receiving reservation.

    Keep the physical service rate while room remains. Dividing room by the
    whole interval would wrongly slow a late-arriving vehicle even when it can
    use the outlet's full rate near the end. Split only at existing arrival
    events and at exhaustion of the shared receiving budget; no1s replay.
    """
    if (duration_sec not in (5,10) or isinstance(duration_sec,bool)
            or not port.interval_service or port.last_time_s!=start_sec
            or any(not math.isfinite(v) or v<0 for v in (start_sec,service_veh_h,receiving_veh))):
        raise ValueError('Coarse drainage needs a current interval-service port and finite offers')
    end=start_sec+duration_sec
    cuts=sorted({start_sec,end}|{t for t,n in port.pending if start_sec<t<end})
    before=port.stock;left=receiving_veh;departed=0.;segments=0
    rate=service_veh_h/3600.
    for a,b in zip(cuts,cuts[1:]):
        ready=port.ready+sum(n for t,n in port.pending if t<=a)
        if rate>0 and 0<left<=ready and left<rate*(b-a):
            split=a+left/rate
            amount=port.release(a,split-a,service_veh_h)
            amount+=port.release(split,b-split,0.)
            segments+=2
        else:
            amount=port.release(a,b-a,service_veh_h if left>0 else 0.)
            segments+=1
        if amount>left+1e-7:raise ArithmeticError('Off-ramp reused its finite receiving reservation')
        departed+=amount;left=max(0.,left-amount)
    if abs(before-port.stock-departed)>1e-7:
        raise ArithmeticError('Coarse off-ramp drainage lost vehicles')
    port.last_coarse_drain_segments=segments
    return departed
