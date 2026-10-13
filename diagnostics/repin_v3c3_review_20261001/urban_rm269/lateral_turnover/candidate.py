"""Diagnostic: propagate used adjacent-lane departure opportunities by one step.

Demand is the greater of the old aggregate attempt and last-step receiving-lane
departures (one opportunity/vehicle), capped by current donor stock and current
space. This is a hypothesis, not a microscopic accepted-gap model. Longitudinal
connector arrivals retain their existing priority; no future departure is used.
"""
from evaluation.controllers import route_choice_corridor as rc


FIELD = '_diagnostic_lane68_turnover'


def advance(state, cfg, step):
    spec=cfg.network.known_legsplit_routes
    rate=spec.get('lateral_access_rate_per_sec')
    if rate is None:return
    geometry=spec['entry_lane_receiving']; ramp=geometry['ramp']
    prior=getattr(state,FIELD,None)
    if prior is not None:
        assert prior['step']==step-1, 'Never reuse an old departure opportunity'
    slots=prior['departed'] if prior is not None else {}
    occupied=rc._known_lane_occupancy(state,spec,step)
    pending=[];departed={};ledger=rc.get_ledger(state)
    for lane,target in (('3','2'),('4','3')):
        cap=geometry['road_capacity_veh'][target]
        room=max(0.,cap-occupied[target])
        probability=-rc.math.expm1(-rate*cfg.simulation.T_u_sec*min(1.,room/cap))
        rows=[];donors=0.
        for c in state.known_legsplit_route_state['cohorts']:
            if c['target']!=ramp or c['due']>step:continue
            share=c['lane68']['shares'].get(lane,0.)
            if share<=0 or c['vehicles']<=0:continue
            rows.append((c,share));donors+=c['vehicles']*share
        if donors<=0:continue
        attempt=max(donors*probability,min(donors,slots.get(target,0.)))
        accepted=min(room,attempt)
        # Retain the old proportional source allocation; only demand changes.
        fraction=accepted/donors if accepted<donors else 1.
        for c,share in rows:pending.append((c,lane,target,share*fraction))
        departed[lane]=accepted
        if ledger is not None and ledger.captures_response:
            ledger.record_resource_allocation('known_wout_lateral_receiving','68:'+target,room,
                                               {'lane:68:'+lane:accepted})
    for c,lane,target,fraction in pending:
        shares=dict(c['lane68']['shares'])
        shares[lane]-=fraction;shares[target]=shares.get(target,0.)+fraction
        c['lane68']={**c['lane68'],'shares':{k:v for k,v in shares.items() if v>0}}
    setattr(state,FIELD,dict(step=step,departed=departed))


def _lane_stocks(state, spec):
    """Only exit-eligible owners modified by the current commit, per lane."""
    result={}
    for c in state.known_legsplit_route_state['cohorts']:
        if c['target']!=spec['entry_lane_receiving']['ramp'] and not c.get('local68_queue'):
            continue
        for lane,share in c.get('lane68',{}).get('shares',{}).items():
            result[lane]=result.get(lane,0.)+c['vehicles']*share
    return result


def install():
    original=rc.known_legsplit_commit
    def commit(state,cfg,receipts,step):
        spec=cfg.network.known_legsplit_routes
        before=_lane_stocks(state,spec)
        result=original(state,cfg,receipts,step)
        after=_lane_stocks(state,spec)
        current=getattr(state,FIELD,None)
        # No prepared request means no eligible source transfer this step.
        if current is None or current['step']!=step:
            assert all(abs(before.get(k,0)-after.get(k,0))<1e-7 for k in set(before)|set(after))
            setattr(state,FIELD,dict(step=step,departed={}))
        else:
            for lane in set(before)|set(after):
                departure=before.get(lane,0.)-after.get(lane,0.)
                assert departure>=-1e-7
                current['departed'][lane]=current['departed'].get(lane,0.)+max(0.,departure)
        return result
    rc._known_lateral_advance=advance
    rc.known_legsplit_commit=commit
