"""Observed lane-storage protection in the existing signal command domain.

This is a reactive reserve constraint, not a forecast of spillback. It changes
neither vehicle stocks nor saturation/receiving flows nor the TTT objective.
"""
from collections import defaultdict
import math
import xml.etree.ElementTree as ET

import numpy as np


def configure(cfg, tuning, raw, plan):
    policy = (tuning or {}).get('urban', {}).get('storage_release_guard', {})
    cfg.network.urban_storage_guard = None
    if not policy.get('enabled', False):
        return {}
    trigger = float(policy['trigger_fraction'])
    increment = float(policy['reserve_green_sec'])
    spacing = float(cfg.network.urban_avg_vehicle_length_m)
    if not (0 < trigger < 1 and 0 < increment <= 2 and spacing > 0
            and all(map(math.isfinite, (trigger, increment, spacing)))):
        raise ValueError('Invalid urban storage reserve policy')
    from evaluation.controllers.signal_head_observation import physical_groups
    from evaluation.controllers.route_choice_corridor import _length
    from evaluation.controllers.projection_support import complete_records
    records = complete_records(raw)
    tree = ET.parse(raw['network_path']).getroot()
    links = {x.get('no'): x for x in tree.findall('./links/link')}
    lengths = {k: _length(v) for k, v in links.items()}
    groups = physical_groups(raw['network_path'], plan)
    positions = defaultdict(list)
    for v in records:
        positions[str(v['link_no']), int(v['lane_no'])].append(float(v['position_m']))
    outgoing = defaultdict(list)
    for connector, node in links.items():
        start, end = node.find('fromLinkEndPt'), node.find('toLinkEndPt')
        if start is None or end is None:
            continue
        source, first = start.get('lane').split()
        target, landing = end.get('lane').split()
        for i in range(len(node.findall('./lanes/lane'))):
            outgoing[source, int(first)+i].append(dict(connector=connector,
                source_pos=float(start.get('pos')), link=target, lane=int(landing)+i,
                position=float(end.get('pos'))))
    stops = defaultdict(list)
    for h in tree.findall('./signalHeads/signalHead'):
        link, lane = h.get('lane').split()
        stops[link, int(lane)].append(float(h.get('pos')))

    def occupancy(link, lane, start, end):
        if not math.isfinite(end-start) or end-start <= 0:
            raise ValueError('Urban reserve has no physical lane storage')
        count = sum(start <= p <= end for p in positions[link, lane])
        capacity = (end-start)/spacing
        return dict(vehicles=count, capacity_veh=capacity, fill_fraction=count/capacity)

    scores = {owner: {} for owner in cfg.network.signals}
    evidence = []
    for (link, phase), heads in sorted(groups.items()):
        for head in heads:
            owner = 'SC'+head['sc']
            if owner not in scores or phase not in cfg.network.signal_live_phases(owner):
                continue
            lane, end = head['lane'], head['position_m']
            source = occupancy(link, lane, 0., end)
            receivers = []
            for turn in outgoing[link, lane]:
                if turn['source_pos'] < end-1e-6:
                    continue  # A branch before this head is not its controlled discharge.
                target, target_lane, start = turn['link'], turn['lane'], turn['position']
                future_heads = [p for p in stops[target, target_lane] if p > start+1e-6]
                target_end = min(future_heads, default=lengths[target])
                if target_end <= start+1e-6:
                    continue
                receivers.append(dict(**turn, **occupancy(target, target_lane, start, target_end)))
            # A signal lane may serve several turns. Never invent its turn
            # split: only call the receiver blocked if ALL reachable turns fill.
            all_blocked = bool(receivers) and all(r['fill_fraction'] >= trigger for r in receivers)
            crowded = source['fill_fraction'] >= trigger
            score = 0.
            if all_blocked:
                score = -1.  # Avoid increasing service into an observed full receiver.
            elif crowded and receivers:
                score = source['fill_fraction']
            key = owner+'_'+phase
            scores[owner][key] = scores[owner].get(key, 0.)+score
            evidence.append(dict(signal=owner, phase=key, link=link, lane=lane,
                head_id=head['head_id'], **source, crowded=crowded,
                all_receivers_full=all_blocked, receiver_known=bool(receivers),
                receivers=receivers, pressure=score))
    missing = [s for s, p in scores.items() if not p]
    if missing:
        raise ValueError('Urban storage guard lacks controlled heads: '+','.join(missing))
    cfg.network.urban_storage_guard = dict(schema='observed-urban-lane-storage/v1',
        policy=policy, signals=scores, lanes=evidence, observed_sec=float(raw['sim_sec']),
        scope='Observed pre-head lane reserve; no predictive no-spillback guarantee. '
              'Shared turns retain unknown destination; all-blocked test is conservative.')
    return dict(urban_storage_guard_signals=len(scores), urban_storage_guard_lanes=len(evidence))


def constrain(coord):
    """One feasible pressure-progress halfspace per affected signal, no rollout.

    LP uses the actual command's existing phase/min/max/cycle/trust constraints.
    Conflicting full approaches cannot independently demand extra cycle time.
    Half of attainable improvement leaves room for millisecond writer rounding.
    """
    from scipy.optimize import linprog
    data = getattr(coord.cfg.network, 'urban_storage_guard', None)
    coord.urban_storage_receipt = []
    if not data:
        return
    for owner, weights in data['signals'].items():
        scale = max(map(abs, weights.values()), default=0.)
        if not scale:
            continue
        ix = [j for j, a in enumerate(coord.axes) if a['owner'] == owner and a['kind'] == 'green']
        w = np.array([sum(weights.get(owner+'_'+p, 0.)*factor for p, factor in coord.green_vectors[j].items())
                      *coord.axes[j]['scale']/scale for j in ix])
        if not ix or np.max(np.abs(w), initial=0) < 1e-10:
            coord.urban_storage_receipt.append(dict(signal=owner, status='no_green_redistribution_direction'))
            continue
        G = coord.G[:, ix]
        mask = np.any(G != 0, axis=1)
        G, lo, hi = G[mask], coord.glo[mask], coord.ghi[mask]
        matrix = np.concatenate((G[np.isfinite(hi)], -G[np.isfinite(lo)]))
        rhs = np.concatenate((hi[np.isfinite(hi)], -lo[np.isfinite(lo)]))
        result = linprog(-w, A_ub=matrix, b_ub=rhs,
                         bounds=list(zip(coord.lower[ix], coord.upper[ix])), method='highs')
        if not result.success:
            raise ValueError('Urban reserve actuator feasibility failed: '+owner)
        maximum = float(w@result.x)
        required = min(data['policy']['reserve_green_sec'], max(0., maximum)*.5)
        receipt = dict(signal=owner, attainable_pressure_sec=maximum,
                       required_pressure_sec=required, phase_weights=weights)
        if required < .01:
            receipt['status'] = 'no_attainable_reserve_progress'
        else:
            row = np.zeros(len(coord.axes)); row[ix] = w
            coord.G = np.vstack((coord.G, row))
            coord.glo = np.append(coord.glo, required)
            coord.ghi = np.append(coord.ghi, np.inf)
            receipt['status'] = 'constrained'
        coord.urban_storage_receipt.append(receipt)


def operating_seed(coord, reference, policy):
    """Project warm start only; preserve the previous applied trust anchor."""
    if coord.valid(coord.encode(reference)):
        return reference
    from evaluation.controllers.sdmpc import solve_qp
    z = coord.encode(reference)
    step, proof = solve_qp(np.zeros(len(z)), np.zeros(len(z)), 1.,
        coord.lower-z, coord.upper-z, coord.G, coord.glo-coord.G@z, coord.ghi-coord.G@z, policy)
    if not proof['success']:
        raise ValueError('Urban/ramp reserve has no executable operating seed')
    # Leave the active reserve face before the native writer rounds greens to
    # milliseconds. Physical min/max and consecutive changes stay constrained.
    step, proof = solve_qp(1.05*step, np.zeros(len(z)), 1.,
        coord.lower-z, coord.upper-z, coord.G, coord.glo-coord.G@z, coord.ghi-coord.G@z, policy)
    if not proof['success']:
        raise ValueError('Urban/ramp reserve rounding-margin projection failed')
    seed = coord.decode(z+step, reference)
    coord.validate(seed)
    return seed
