"""Conserved coarse ramp step for a future multirate coupled rollout.

Old cohorts advance to the interval end; accepted merges debit that stock.
Integrated head service and accepted upstream arrivals occur at the end, so
newly head-served vehicles cannot also merge in this step. Time binning changes
the old1s prediction; it is not an exact performance optimization. No extra
capacity, control reward, or observed future boundary is supplied here.
"""
from math import floor, fsum
from evaluation.controllers.physical_ramp_boundary import _number, _MASS_TOLERANCE


def service_integral(start, duration, cycle, service, mode, green):
    if mode=='OFF':
        if green is not None:raise ValueError('OFF service cannot carry a green duration')
        return service*duration/cycle
    if mode=='RED':
        if service!=0 or green not in (None,0.):raise ValueError('RED cannot offer head service')
        return 0.
    if mode!='GREEN' or green is None or not 0<green<=cycle:
        raise ValueError('GREEN requires its supplied duration within the cycle')
    end=start+duration
    overlap=fsum(max(0.,min(end,k*cycle+green)-max(start,k*cycle))
                 for k in range(floor(start/cycle),floor(end/cycle)+1))
    return service*overlap/green


def advance(buffer, *, start_sec, duration_sec, cycle_sec, receiving_budget_veh,
            service_veh, mode, green_sec=None, request_arrivals_veh=0.,
            posthead_speed_kmh=None, receiving_budget_by_lane_veh=None):
    start=_number(start_sec,'coarse start')
    dt=_number(duration_sec,'coarse duration',positive=True)
    cycle=_number(cycle_sec,'meter cycle',positive=True)
    budget=_number(receiving_budget_veh,'coarse receiving budget')
    service=_number(service_veh,'cycle head service')
    requests=_number(request_arrivals_veh,'coarse arrival request')
    green=None if green_sec is None else _number(green_sec,'meter green')
    if dt not in (1.,5.,10.) or start!=buffer.time_sec:
        raise ValueError('Coarse ramp requires a contiguous1/5/10s interval')
    head=service_integral(start,dt,cycle,service,mode,green)
    lanes=getattr(buffer,'_lane_buffers',None)
    children=lanes if lanes is not None else [buffer]
    for child in children:
        child._require_phase('idle')
        if child.time_sec!=start:raise ValueError('Coarse ramp lane clocks differ')
        if getattr(child,'_causal_receiving_enabled',False) and dt>child._spatial_entry['envelope'].lag:
            raise ValueError('Coarse ramp interval exceeds receiving wave lag; substep required')
    if lanes is not None and buffer.lane_exchange_rates is not None:
        raise ValueError('Coarse ramp lateral exchange has not been connected')
    if receiving_budget_by_lane_veh is not None:
        if lanes is None or len(receiving_budget_by_lane_veh)!=len(lanes):
            raise ValueError('Coarse receiving budgets must cover the physical lanes')
        budgets=[_number(v,'coarse lane receiving') for v in receiving_budget_by_lane_veh]
        if abs(fsum(budgets)-budget)>_MASS_TOLERANCE:
            raise ValueError('Coarse lane budgets must conserve the aggregate budget')
    else:budgets=[budget/len(children)]*len(children)
    shares=buffer.lane_arrival_shares if lanes is not None else [1.]
    rows=[]
    for child,lane_budget,share in zip(children,budgets,shares):
        before=child.snapshot()
        ready=child.begin_interval(start,dt,posthead_speed_kmh=posthead_speed_kmh)
        accepted=min(ready['eligible_merge_veh'],lane_budget)
        child.commit_merge(accepted)
        local_mode='OFF' if mode=='OFF' else 'GREEN' if head>0 else 'RED'
        child.apply_head_service(head/len(children),mode=local_mode,
            green_sec=None if local_mode=='OFF' else green if local_mode=='GREEN' else 0.,
            posthead_capacity_veh=(child.length_m-child.head_position_m)*child.lanes/child.spacing_m)
        row=child.finish_interval(requests*share)
        row.update(start=before,receiving_budget_veh=lane_budget,
                   unused_receiving_budget_veh=max(0.,lane_budget-accepted),
                   receiving_rate_envelope_veh_s=lane_budget/dt,
                   local_step_sec=dt,local_receipts=[],
                   eligible_merge_scope='Old cohorts eligible by coarse interval end; no new head departures')
        rows.append(row)
    if lanes is None:return rows[0]
    first=rows[0]
    fixed={'start_sec','end_sec','duration_sec','meter_mode','green_sec','local_step_sec',
           'eligible_merge_scope','local_receipts'}
    result={k:first[k] for k in fixed}
    for key in ('start','end'):
        result[key]=buffer._aggregate_snapshots([r[key] for r in rows],buffer.connector_id)
    for key in first.keys()-fixed-{'start','end'}:
        result[key]=fsum(r[key] for r in rows)
    result['lane_receipts']=rows
    result['lane_arrival_shares']=buffer.lane_arrival_shares
    buffer.time_sec=start+dt
    for key in ('backlog_veh','cumulative_requested_veh','cumulative_admitted_veh',
                'cumulative_head_service_veh','cumulative_merge_veh','connector_ttt_veh_h'):
        setattr(buffer,key,fsum(getattr(b,key) for b in lanes))
    buffer.snapshot()
    return result
