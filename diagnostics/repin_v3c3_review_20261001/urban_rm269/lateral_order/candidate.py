"""Diagnostic only: same total lateral demand, foremost cohorts served first.

No fitted rate, priority multiplier or new receiving space. Equal positions
share proportionally; different lanes use the common pre-transfer snapshot.
Strict ordering is a closure under test, not a claim of native microscopic FIFO.
"""
from itertools import groupby
from evaluation.controllers import route_choice_corridor as rc


def advance(state, cfg, step):
    spec = cfg.network.known_legsplit_routes
    rate = spec.get('lateral_access_rate_per_sec')
    if rate is None:
        return
    geometry = spec['entry_lane_receiving']; ramp = geometry['ramp']
    occupied = rc._known_lane_occupancy(state, spec, step)
    pending = []; ledger = rc.get_ledger(state)
    for lane, target in (('3', '2'), ('4', '3')):
        cap = geometry['road_capacity_veh'][target]
        room = max(0., cap - occupied[target])
        probability = -rc.math.expm1(-rate * cfg.simulation.T_u_sec * min(1., room/cap))
        if probability <= 0:
            continue
        rows = []; desired = 0.
        for cohort in state.known_legsplit_route_state['cohorts']:
            if cohort['target'] != ramp or cohort['due'] > step:
                continue
            share = cohort['lane68']['shares'].get(lane, 0.)
            if share <= 0 or cohort['vehicles'] <= 0:
                continue
            n = cohort['vehicles'] * share
            rows.append((cohort, n))
            desired += n * probability
        budget = min(room, desired)
        accepted = 0.
        rows.sort(key=lambda row: tuple(row[0]['lane68']['order']))
        for _, group in groupby(rows, key=lambda row: tuple(row[0]['lane68']['order'])):
            group = list(group); available = sum(n for _, n in group)
            amount = min(budget, available)
            if amount <= 0:
                break
            factor = amount/available if amount < available else 1.
            for cohort, n in group:
                moved_fraction = cohort['lane68']['shares'][lane] * factor
                pending.append((cohort, lane, target, moved_fraction))
                accepted += cohort['vehicles'] * moved_fraction
            budget -= amount
        if ledger is not None and ledger.captures_response:
            ledger.record_resource_allocation('known_wout_lateral_receiving', '68:'+target,
                                               room, {'lane:68:'+lane: accepted})
    for cohort, lane, target, fraction in pending:
        shares = dict(cohort['lane68']['shares'])
        shares[lane] -= fraction
        shares[target] = shares.get(target, 0.) + fraction
        cohort['lane68'] = {**cohort['lane68'],
                            'shares': {k:v for k,v in shares.items() if v > 0}}


def install():
    rc._known_lateral_advance = advance
