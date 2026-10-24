"""Local lane/route stocks; finite receiving with within-cell aggregate FIFO.

Vehicle identities inside the local CTM are replaced by destination and
continuation classes. External offers still admit their original FIFO prefix.
All routes in one cell share a forward service fraction, so a blocked turn
cannot be bypassed by declaring the other class free. Lateral/forward flows
consume the same old-state receiving budget; arrivals move next step only.
This is a model approximation, not exact cohort FIFO or a coarse time clock.
"""
import math
from collections import Counter, defaultdict
from evaluation.controllers.physical_urban_transport import FIFO, EPS


def label(urban, original):
    fallback = urban.continuation and (original in getattr(urban, 'aggregate_original_unrouted', urban.unrouted_labels)
                                      or original[1] == 'aggregate_unrouted'
                                      or original == (None, 'unrouted'))
    return (original[0], 'aggregate_unrouted' if fallback else 'aggregate_routed')


def configure(cfg, tuning, state):
    enabled = tuning.get('urban', {}).get('local_lane_route_aggregate')
    if enabled is None or enabled is False:return {}
    if enabled is not True:raise ValueError('Local lane aggregation requires a boolean')
    if cfg.simulation.T_u_sec != 1 or cfg.simulation.T_f_sec != 1:
        raise ValueError('Local lane aggregation keeps the1s receiving clock')
    if getattr(cfg.network, 'sdmpc_distance_reward', None):
        raise ValueError('Local aggregate distance accounting is not connected')
    runtime = getattr(state, 'lane_urban_runtime', None)
    if runtime is None:raise ValueError('Local aggregate requires physical lane geometry')
    urban = runtime.port.urban
    if getattr(urban, 'route_aggregate', False):raise ValueError('Local aggregate initialized twice')
    if getattr(urban, 'lateral_start_footprints', None):
        raise ValueError('Vehicle footprint diagnostic cannot use aggregate labels')
    # No history is thrown away: project every conservation counter too.
    def project(items):
        result = Counter()
        for original, amount in items:result[label(urban, original)] += amount
        return result
    old_unrouted = urban.unrouted_labels
    urban.aggregate_original_unrouted = set(old_unrouted)
    for key, queue in list(urban.cells.items()):
        urban.cells[key] = FIFO(sorted(project(queue.q).items(), key=repr))
    for name in ('initial', 'admitted', 'departed'):
        setattr(urban, name, project(getattr(urban, name).items()))
    urban.unrouted_labels = {label(urban, original) for original in old_unrouted}
    if urban.continuation:urban.unrouted_labels.add((None, 'aggregate_unrouted'))
    urban.route_aggregate = True
    urban.check()
    cfg.network.local_lane_route_aggregate = True
    return dict(local_lane_route_aggregate=True,
                local_lane_aggregate_cells=len(urban.cells),
                local_lane_aggregate_clock_sec=1)


def step(urban, external, exit_receiving):
    if exit_receiving is not None and (set(exit_receiving) != set(urban.exits)
            or any(not math.isfinite(n) or n < 0 for n in exit_receiving.values())):
        raise ValueError('Every local exit needs a finite nonnegative receiving budget')
    stock = {k: dict(q.counts()) for k, q in urban.cells.items()}
    old_n = {k: sum(v.values()) for k, v in stock.items()}
    receiving = {k: max(0., min(urban.capacity_rate,
                 urban.wave/urban.dx[k]*(urban.cap[k]-n))) for k, n in old_n.items()}
    sending = {k: min(urban.capacity_rate, urban.speed/urban.dx[k]*n) for k,n in old_n.items()}
    for name, (_, queue) in external.items():sending[('external', name)] = queue.stock
    urban.last_transfers = []
    urban.last_sending_limits = dict(sending)
    urban.last_receiving_limits = dict(receiving)
    additions = defaultdict(Counter)
    accepted = {}

    def routed(key, item):
        target, reason = urban.route(key, item, receiving)
        if target == ('exit', None) and exit_receiving is not None:
            road,lane,_ = key
            possible = [d for d,e in urban.exits.items() if lane in e['lanes']
                        and e['position_m'] > urban.edges[road][-2]]
            if len(possible) != 1:raise ValueError('Unknown class has no unique physical exit')
            target = ('exit', possible[0])
        return target, reason

    def transfer(source, target, item, amount, reason):
        if amount <= EPS:return
        stock[source][item] -= amount
        sending[source] = max(0., sending[source]-amount)
        urban.last_transfers.append((source, target, ((item, amount),)))
        urban.movements[(source, target, reason)] += amount
        if target[0] == 'exit':urban.departed[item] += amount
        else:additions[target][item] += amount

    if urban.lateral_access:
        requests = []
        source_totals = defaultdict(float)
        for key, classes in stock.items():
            road,lane,cell = key
            for item,n in classes.items():
                destination = item[0]
                required = urban.exits[destination]['lanes'] if destination is not None and road == 71 else None
                mandatory = required and lane not in required and not (destination == 10642 and cell > 1)
                if mandatory:
                    other = lane + (1 if lane < min(required) else -1)
                    selected = getattr(urban, 'defer_destinations', None)
                    defer = getattr(urban, 'defer_mandatory_while_forward_open', False) and (selected is None or destination in selected)
                    prefer = getattr(urban, 'prefer_more_receiving_space', False)
                    forward,reason = routed(key,item)
                    threshold = receiving.get((road,other,cell),0.) if prefer else 0.
                    if (defer or prefer) and reason == 'forward' and receiving.get(forward,0.) > threshold+EPS:continue
                    offers = [(other,n)]
                else:
                    rates = [(other,urban.exchange_rates.get((road,lane,other,destination),0.))
                             for other in (lane-1,lane+1) if (road,other,cell) in stock and (not required or other in required)]
                    total = sum(rate for _,rate in rates)
                    offers = [(other,n*-math.expm1(-total)*rate/total) for other,rate in rates if rate > 0] if total else []
                for other,amount in offers:
                    target = (road,other,cell)
                    if amount > EPS and receiving.get(target,0.) > EPS:
                        requests.append((key,target,item,amount));source_totals[key] += amount
        normalized = [(k,t,item,n*min(1.,sending[k]/source_totals[k])) for k,t,item,n in requests]
        targets = defaultdict(float)
        for _,t,_,n in normalized:targets[t] += n
        for k,t,item,n in normalized:
            amount = n*min(1.,urban.last_receiving_limits[t]/targets[t])
            transfer(k,t,item,amount,'lateral');receiving[t] = max(0.,receiving[t]-amount)

    requests = []
    blocked = set()
    fraction_at = getattr(urban.program, 'service_fraction_at', None)
    for key,classes in stock.items():
        total = sum(classes.values())
        if total <= EPS or sending[key] <= EPS:continue
        budget = min(total,sending[key])
        if fraction_at is not None and key[0] == 71 and key[2] == len(urban.edges[71])-2:
            budget = min(budget,urban.capacity_rate*fraction_at(urban.time+1,
                         2 if key[1] <= 3 else 5,controller_offset_sec=urban.offset))
        for item,n in classes.items():
            if n <= EPS:continue
            target,reason = routed(key,item)
            if target is None:
                blocked.add(key);urban.blocked_seconds[(key,reason)] += 1
            else:requests.append((key,target,item,budget*n/total,reason))
    requests = [r for r in requests if r[0] not in blocked and r[3] > EPS]
    for name,(target,queue) in external.items():
        if queue.stock > EPS:requests.append((('external',name),target,None,queue.stock,'entry'))
    targets = defaultdict(float)
    for _,target,_,amount,_ in requests:targets[target] += amount
    ratios = {t:(1. if exit_receiving is None else min(1.,exit_receiving[t[1]]/n))
              if t[0] == 'exit' else min(1.,receiving[t]/n) for t,n in targets.items()}
    source_ratio = {}
    for key,target,_,_,_ in requests:
        source_ratio[key] = min(source_ratio.get(key,1.),ratios[target])
    for key,target,item,amount,reason in requests:
        amount *= source_ratio[key]
        if amount <= EPS:continue
        if key[0] == 'external':
            packets = external[key[1]][1].take(amount)
            accepted[key[1]] = packets
            urban.last_transfers.append((key,target,tuple(packets)))
            for original,n in packets:
                mapped = label(urban,original)
                urban.admitted[mapped] += n;additions[target][mapped] += n
        else:transfer(key,target,item,amount,reason)
    for key,classes in stock.items():
        for item,n in additions[key].items():classes[item] = classes.get(item,0.)+n
        urban.cells[key] = FIFO(sorted(((item,n) for item,n in classes.items() if n > EPS),key=repr))
    urban.vehicle_seconds += (sum(old_n.values())+sum(q.stock for q in urban.cells.values()))/2
    urban.time += 1
    urban.check()
    return accepted
