"""Read-only projection of an existing W_out state into bounded aggregate arrays.

The projection is not a forecast. Prechoice readiness means readiness for route
choice, not readiness for a ramp/exit or an observed stopped queue. Already
chosen routes remain chosen. Tail stock is not assigned to road68 storage.
"""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.reservoir import IntervalBins, LaneTurnReservoir


def project(state, network, horizon=450, step_sec=1):
    start = int(state['time_sec'])
    if start != state['time_sec']:
        raise ValueError('Projection requires an integer one-second clock')
    spec = network['known_legsplit_routes']
    geometry = spec['entry_lane_receiving']
    targets = tuple(sorted({'prechoice', 'unknown', 'free', *spec['future_choice_weights']}))
    road_caps = geometry['road_capacity_veh']
    road = LaneTurnReservoir(road_caps, [(l,t) for l in road_caps for t in targets], start, horizon, step_sec)
    connectors = {}
    for link, entry in geometry['connector_entries'].items():
        caps = {str(l):entry['capacity_per_lane_veh'] for l in entry['lanes']}
        connectors[link] = LaneTurnReservoir(caps, [(l,t) for l in caps for t in targets], start, horizon, step_sec)
    tail = IntervalBins(targets, start, horizon, step_sec)
    source_targets = defaultdict(float)
    source_mass = 0.
    for c in state['known_legsplit_route_state']['cohorts']:
        target = c['target']; amount = c['vehicles']; source_mass += amount
        source_targets[target] += amount
        if 'connector68' in c:
            tag = c['connector68']; obj = connectors[tag['link']]; due = tag['ready_step']
        elif 'lane68' in c and (target in (geometry['ramp'], 'unknown', 'prechoice')
                               or c.get('local68_queue') or start < c['lane68']['exit_step']):
            tag = c['lane68']; obj = road; due = c['due']
        else:
            tail.add(target, c['due'], amount)
            continue
        if abs(sum(tag['shares'].values())-1.) > 1e-9:
            raise ValueError('Projection cannot repair or discard lane shares')
        for lane, share in tag['shares'].items():
            obj.seed(lane, target, amount*share, due)
    # Mature only the known initial stage-eligible stock; no physical flow.
    for obj in (road, *connectors.values()):
        obj.bins.advance(start)
        obj.check(); obj.bins.verify()
    tail.advance(start); tail.verify()

    projected_targets = defaultdict(float)
    for obj in (road, *connectors.values()):
        for j,(lane,t) in enumerate(obj.bins.labels):
            projected_targets[t] += obj.bins.total(j)
    for j,t in enumerate(tail.labels):
        projected_targets[t] += tail.total(j)
    errors = {t:projected_targets[t]-source_targets[t] for t in targets}
    projected_mass = sum(projected_targets.values())
    storage = spec['storage']
    owner_mass = network['urban_link_storage_veh'][storage]-state['urban_link_storage'][storage]
    if max([abs(e) for e in errors.values()] + [abs(projected_mass-owner_mass)]) > 1e-7:
        raise ValueError('Projection did not preserve routes and the sole W_out owner')

    def describe(obj):
        return dict(stock_veh=obj.stock(), capacity_veh=sum(obj.capacity.values()),
                    by_lane_veh={l:obj.stock(l) for l in obj.capacity},
                    stage_eligible_veh=float(sum(obj.bins.waiting)),
                    pending_stage_veh=float(sum(obj.bins.pending)),
                    labels=len(obj.bins.labels), future_shape=list(obj.bins.future.shape))
    return dict(time_sec=start, update_sec=step_sec, prediction_updates=horizon//step_sec,
                source_cohorts=len(state['known_legsplit_route_state']['cohorts']),
                source_mass_veh=source_mass, sole_owner_mass_veh=owner_mass,
                projected_mass_veh=projected_mass, target_error_veh=dict(errors),
                road68=describe(road), connectors={k:describe(v) for k,v in connectors.items()},
                tail=dict(stock_veh=sum(tail.total(j) for j in range(len(targets))),
                          stage_eligible_veh=float(sum(tail.waiting)), pending_stage_veh=float(sum(tail.pending)),
                          labels=len(targets), future_shape=list(tail.future.shape)),
                warning='Projection only. Pending/eligible refer to model stage ETA, not observed moving/stopped classes. No SDMPC/native validation.')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--saved', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--step-sec', type=int, default=1)
    args = p.parse_args()
    documents = {n:args.saved/(n+'.json') for n in ('state','network')}
    inputs = {n:json.loads(path.read_text(encoding='utf-8-sig')) for n,path in documents.items()}
    result = project(**inputs, step_sec=args.step_sec)
    result['sources'] = {n:dict(path=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                         for n,path in documents.items()}
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__ == '__main__':
    main()
