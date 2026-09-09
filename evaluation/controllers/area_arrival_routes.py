"""Resolve aliases by their actual first modeled physical stopline.

A PN entry connector can be upstream of the modeled signal, so assigning that
connector directly to a movement confuses gate crossing with signal service.
Native graph reachability to the first signal head proves the shared stopline;
an already validated turn from that stopline proves the movement destination.
No branch weights are inferred. Differing crossing patterns remain unresolved.
"""
from __future__ import annotations
from collections import defaultdict
from copy import deepcopy
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
from evaluation.controllers.control_area_objective import physical_membership_from_ledger


def extend_gate_routes(cfg, routes, membership_document, *, root, detector_mapping=None):
    path = Path(root) / membership_document['network']['path']
    if hashlib.sha256(path.read_bytes()).hexdigest() != membership_document['network']['sha256']:
        raise ValueError('Gate path network hash differs from physical membership')
    physical = physical_membership_from_ledger(membership_document)
    tree = ET.parse(path).getroot()
    successors = defaultdict(list)
    for link in tree.findall('./links/link'):
        a, b = link.find('fromLinkEndPt'), link.find('toLinkEndPt')
        if a is not None:
            source, target = a.get('lane').split()[0], b.get('lane').split()[0]
            successors[source].append((link.get('no'), target))
            successors[link.get('no')].append((None, target))
    heads = defaultdict(set)
    for head in tree.findall('.//signalHead'):
        if head.get('lane') and head.get('sg'):
            heads[head.get('lane').split()[0]].add(head.get('sg').split()[0])
    modeled_controllers = {str(spec.get('signal', '')).removeprefix('SC') for spec in cfg.network.urban_movements.values()}
    known_stoplines = set()
    for route in routes.values():
        if type(route.get('target_inside')) is bool:
            known_stoplines.update(str(turn.get('from_link', (turn.get('path') or [''])[0]))
                                  for turn in route.get('physical_turns', []))

    def paths_to_first_stopline(source, target_stoplines):
        target_controllers = set().union(*(heads[stopline] for stopline in target_stoplines))
        frontier = [[source]]
        found = []
        for _ in range(12):
            following = []
            for trace in frontier:
                current = trace[-1]
                if current in target_stoplines:
                    found.append(trace)
                    continue
                if current in known_stoplines:
                    continue
                if heads[current] & modeled_controllers - target_controllers:
                    continue
                for connector, target in successors[current]:
                    if target not in trace:
                        following.append(trace + ([connector] if connector else []) + [target])
            frontier = following
            if not frontier:
                break
        return found

    def pattern(trace):
        mask = [physical[x] for x in trace]
        return (mask[0], mask[-1], sum(a and not b for a, b in zip(mask, mask[1:])),
                sum(not a and b for a, b in zip(mask, mask[1:])))

    output = deepcopy(routes)
    added = []
    for movement, spec in cfg.network.urban_movements.items():
        if spec.get('kind') == 'on_ramp':
            continue
        origin = str(spec.get('origin', ''))
        if spec.get('kind') == 'off_ramp':
            origin = str(cfg.network.off_ramp_storage_link.get(origin, origin))
        gate = routes.get('input:gate:' + origin, {})
        sources = [str(row['link']) for row in gate.get('physical_sources', [])]
        if not sources:
            sources = [str(link) for link, origins in (detector_mapping or {}).get('link_to_origins', {}).items()
                       if origin in origins]
        candidates = []
        target_stoplines = set()
        for other, other_spec in cfg.network.urban_movements.items():
            if other_spec.get('signal') != spec.get('signal') or other_spec.get('receiving_link') != spec.get('receiving_link'):
                continue
            route = routes.get('movement:' + other, {})
            turns = route.get('physical_turns', [])
            if type(route.get('target_inside')) is not bool or not turns:
                continue
            candidates.append((other, route))
            target_stoplines.update(str(turn.get('from_link', (turn.get('path') or [''])[0])) for turn in turns)
        paths = [trace for source in sources for trace in paths_to_first_stopline(source, target_stoplines)]
        if not paths:
            continue
        reached = {trace[-1] for trace in paths}
        valid = []
        for other, route in candidates:
            turns = route.get('physical_turns', [])
            if type(route.get('target_inside')) is not bool or not turns:
                continue
            if all(str(turn.get('from_link', (turn.get('path') or [''])[0])) in reached for turn in turns):
                valid.append((other, route))
        route_patterns = {(row['source_inside'], row['target_inside'], row['outward_crossings_per_vehicle'], row['inward_crossings_per_vehicle']) for _, row in valid}
        arrival_patterns = {pattern(trace) for trace in paths}
        target_sides = {p[1] for p in arrival_patterns}
        monotone = all(p[2] == int(p[0] and not p[1]) and p[3] == int(not p[0] and p[1]) for p in arrival_patterns)
        if len(route_patterns) != 1 or len(target_sides) != 1 or (len(arrival_patterns) != 1 and not monotone):
            continue
        arrival_source, arrival_target, out_count, in_count = next(iter(arrival_patterns))
        turn_source = next(iter(route_patterns))[0]
        if arrival_target != turn_source:
            raise ValueError('Gate arrival and validated turn disagree on physical stopline membership')
        key = 'movement:' + movement
        # A validated current route already covers its stopline. Gate alias
        # extension only fills an unresolved movement and its matching arrival.
        if type(output.get(key, {}).get('target_inside')) is bool:
            continue
        output[key] = dict(valid[0][1], status='shared_physical_stopline', shared_turn_movements=[name for name, _ in valid])
        output['arrival:' + movement] = {
            'status': 'native_gate_to_first_signal_head', 'source_inside': arrival_source,
            'target_inside': arrival_target, 'inside_to_inside': float(arrival_target),
            'outside_to_inside': float(arrival_target),
            'outward_crossings_per_vehicle': out_count, 'inward_crossings_per_vehicle': in_count,
            'physical_paths': paths,
            'timing_assumption': 'Native path crossings are placed at modeled arrival at the first signalized stopline.'}
        if len(arrival_patterns) > 1:
            # Different positions along one monotone approach are carried by
            # the actual inside/outside source cohorts, not equal path weights.
            for name in ('source_inside', 'outward_crossings_per_vehicle', 'inward_crossings_per_vehicle'):
                output['arrival:' + movement].pop(name)
        added.append({'movement': movement, 'gate': origin, 'stoplines': sorted(reached), 'paths': paths,
                      'shared_turn_movements': [name for name, _ in valid]})
    arrivals_only = []
    for movement, spec in cfg.network.urban_movements.items():
        key = 'arrival:' + movement
        if type(output.get(key, {}).get('target_inside')) is bool:
            continue
        siblings = []
        for other, other_spec in cfg.network.urban_movements.items():
            if any(other_spec.get(k) != spec.get(k) for k in ('signal', 'origin', 'approach')):
                continue
            route = output.get('movement:' + other, {})
            if type(route.get('source_inside')) is bool and route.get('physical_turns'):
                siblings.append((other, route))
        sides = {route['source_inside'] for _, route in siblings}
        if len(sides) != 1:
            continue
        side = sides.pop()
        output[key] = {'status': 'proven_common_approach_stopline', 'target_inside': side,
                       'inside_to_inside': float(side), 'outside_to_inside': float(side),
                       'shared_approach_movements': [name for name, _ in siblings],
                       'departure_status': output.get('movement:' + movement, {}).get('status'),
                       'timing_assumption': 'Arrival reaches the shared approach; unresolved departure remains forbidden.'}
        arrivals_only.append(movement)
    return output, {'gate_alias_routes_resolved': len(added), 'resolved_gate_aliases': added,
                    'arrival_only_common_approach': arrivals_only}
