"""Pinned physical paths missed by the signal-stopline turn inventory.

Path joins do not change plant/model routing. The separately enabled topology
repair removes one impossible movement before projection, preserving observation
weight on its physical source link. It must never migrate an already projected
queue without the original physical observations.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from evaluation.controllers.control_area_objective import physical_membership_from_ledger
from evaluation.controllers.network_provenance import snapshot_network_sha256

ROOT = Path(__file__).resolve().parents[2]


def invalidate_topology_cache(network):
    """Evict only this changed network from vendor's identity-based caches."""
    from src.models import urban_queue_model
    urban_queue_model._SPECS_CACHE[:] = [
        entry for entry in urban_queue_model._SPECS_CACHE if entry[0] is not network]
    if urban_queue_model._SYNC_INDEX_NET is network:
        urban_queue_model._SYNC_INDEX_NET = None
        urban_queue_model._SYNC_INDEX = ()
        urban_queue_model._SYNC_COUNTS = (0, 0, 0)


def load_evidence(path):
    document = json.loads((ROOT / path).read_text(encoding='utf-8-sig'))
    network_path = ROOT / document['network']['path']
    if hashlib.sha256(network_path.read_bytes()).hexdigest() != document['network']['sha256']:
        raise ValueError('Physical movement path network hash mismatch')
    tree = ET.parse(network_path).getroot()
    starts = [float(x.get('start')) for x in tree.findall(".//timeIntervalSet[@no='VEHICLEROUTESTATIC']/timeInts/timeInterval")]
    if starts != [0.0]:
        raise ValueError('Expected verified single static route interval')
    links = {x.get('no'): x for x in tree.findall('./links/link')}
    edges = set()
    for key, link in links.items():
        a, b = link.find('fromLinkEndPt'), link.find('toLinkEndPt')
        if a is not None and b is not None:
            edges.add((a.get('lane').split()[0], key))
            edges.add((key, b.get('lane').split()[0]))
    decisions = {x.get('no'): x for x in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')}
    routes = {}
    for did, decision in decisions.items():
        for route in decision.findall('./vehRoutSta/vehicleRouteStatic'):
            raw = (route.get('relFlow') or '').strip()
            match = re.fullmatch(r'2 0:([0-9]+(?:\.[0-9]+)?)', raw) if raw else None
            weight = 1.0 if not raw else float(match.group(1)) if match else None
            path = [decision.get('link')] + [x.get('key') for x in route.findall('./linkSeq/intObjectRef')] + [route.get('destLink')]
            routes[did + ':' + route.get('no')] = {
                'path': path, 'weight': weight, 'relFlow_raw': raw,
                'empty_relFlow_default_one': not raw, 'name': route.get('name'),
                'decision': dict(decision.attrib), 'route': dict(route.attrib)}
    for name, row in document['by_movement'].items():
        path = row['path']
        if len(path) < 2 or any((a, b) not in edges for a, b in zip(path, path[1:])):
            raise ValueError(f'{name}: disconnected physical path')
        proven_edges = set()
        for key in row['native_routes']:
            route = routes[key]
            if route['decision'].get('allVehTypes') != 'true' or route['decision'].get('routeChoiceMeth') != 'STATIC':
                raise ValueError(f'{name}: unsupported route applicability')
            proven_edges.update(zip(route['path'], route['path'][1:]))
        if any(edge not in proven_edges for edge in zip(path, path[1:])):
            raise ValueError(f'{name}: path edge lacks cited native routing evidence')
    return document, routes, edges


def path_membership(path, physical):
    missing = set(path) - physical.keys()
    if missing:
        raise ValueError(f'Physical path membership missing: {sorted(missing)}')
    mask = [physical[x] for x in path]
    edges = [{'source': a, 'target': b, 'from_inside': ia, 'to_inside': ib}
             for a, b, ia, ib in zip(path, path[1:], mask, mask[1:]) if ia != ib]
    return {'path': list(path), 'source_inside': mask[0], 'target_inside': mask[-1],
            'crossing_edges': edges,
            'outward_crossings_per_vehicle': sum(x['from_inside'] for x in edges),
            'inward_crossings_per_vehicle': sum(x['to_inside'] for x in edges)}


def extend_join(join, cfg, detectors, membership, evidence_path):
    """Replace only source-pinned paths; preserve unresolved unsupported movements."""
    document, routes, _ = load_evidence(evidence_path)
    physical = physical_membership_from_ledger(membership)
    output = copy.deepcopy(join)
    for name, evidence in document['by_movement'].items():
        if name not in cfg.network.urban_movements:
            continue
        spec = cfg.network.urban_movements[name]
        for key, expected in evidence['expected_spec'].items():
            if spec.get(key) != expected:
                raise ValueError(f'{name}: model {key} changed; path contract must be reviewed')
        path = evidence['path']
        receiver = spec.get('receiving_link')
        if receiver not in detectors.get('link_to_origins', {}).get(path[-1], []):
            # Native external terminal legs may intentionally have no detector.
            if not evidence.get('external_unobserved_destination'):
                raise ValueError(f'{name}: final path link does not support actual model receiver')
            if physical[path[-1]]:
                raise ValueError(f'{name}: purported external destination lies inside')
        physical_path = path_membership(path, physical)
        physical_path.update({'native_routes': {k: routes[k] for k in evidence['native_routes']},
                              'weight_source': 'exact movement route identity; no branch weighting',
                              'weight': None, 'rationale': evidence['rationale']})
        row = output['by_movement'][name]
        row.update(status='unique', physical_turns=[physical_path], unresolved_reason=None,
                   source_inside=physical_path['source_inside'], target_inside=physical_path['target_inside'],
                   arrival_stopline_inside=physical_path['source_inside'],
                   outward_crossings_per_accepted_vehicle=physical_path['outward_crossings_per_vehicle'],
                   inward_crossings_per_accepted_vehicle=physical_path['inward_crossings_per_vehicle'],
                   timing_assumption=evidence['timing_assumption'])
    from collections import Counter
    output['counts'] = dict(Counter(x['status'] for x in output['by_movement'].values()))
    output['physical_route_evidence'] = {'path': str(evidence_path),
        'sha256': hashlib.sha256((ROOT / evidence_path).read_bytes()).hexdigest(), 'network': document['network']}
    return output


def configure_topology_repair(cfg, detectors, tuning, *, state_json=None):
    """Run after movement merging and before traffic_state_from_vissim.

    Reproject the original physical snapshot afterward. No existing state argument
    is accepted: post-hoc proportional reallocation would erase location evidence.
    """
    path = tuning.get('urban', {}).get('movements', {}).get('physical_route_topology')
    if path is None:
        return detectors, {}
    if not isinstance(path, str) or not path:
        raise ValueError('physical_route_topology must name a pinned evidence document')
    document, routes, edges = load_evidence(path)
    if state_json is not None:
        actual = snapshot_network_sha256(state_json)
        if actual != document['network']['sha256']:
            raise ValueError('Snapshot and movement topology network hashes differ')
    repair = document['topology_repair']
    removed = repair['remove_movement']
    specs = dict(cfg.network.urban_movements)
    if removed not in specs:
        raise ValueError('Topology repair expects the canonical merged movement before projection')
    old = specs[removed]
    if any(old.get(k) != v for k, v in repair['expected_removed_spec'].items()):
        raise ValueError('Removed movement semantics changed')
    # Native input 379 cannot reach the independent northbound input at all.
    reachable = {repair['physical_source']}
    while True:
        next_set = reachable | {b for a, b in edges if a in reachable}
        if next_set == reachable:
            break
        reachable = next_set
    if repair['unreachable_northbound_input'] in reachable:
        raise ValueError('Northbound path now exists; phantom diagnosis is stale')
    primary = {key: routes[key]['weight'] for key in repair['primary_routes']}
    secondary = {key: routes[key]['weight'] for key in repair['west_continuation_routes']}
    if any(value is None or value <= 0 or not math.isfinite(value) for value in [*primary.values(), *secondary.values()]):
        raise ValueError('Topology repair needs explicit finite positive native route weights')
    total_primary, total_secondary = sum(primary.values()), sum(secondary.values())
    betas = {}
    for name, selection in repair['keep_movements'].items():
        if name not in specs or specs[name].get('origin') != old.get('origin'):
            raise ValueError('Repair target is not the same canonical origin')
        beta = primary[selection['primary']] / total_primary
        if selection.get('continuation'):
            beta *= secondary[selection['continuation']] / total_secondary
        betas[name] = beta
    if not math.isclose(sum(betas.values()), 1.0, abs_tol=1e-12):
        raise ValueError('Native routing does not close the approach demand split')
    result = copy.deepcopy(detectors)
    affected = []
    for link, rows in result.get('link_to_movements', {}).items():
        if not any(x.get('movement') == removed for x in rows):
            continue
        if link not in repair['physical_projection']:
            raise ValueError(f'Removed queue also observed on unreviewed physical link {link}')
        recipients = repair['physical_projection'][link]
        if any(x.get('movement') not in {removed, *betas} for x in rows):
            raise ValueError('Reviewed physical source now has unrelated movement assignments')
        total_weight = sum(float(x['weight']) for x in rows)
        branch_total = sum(betas[name] for name in recipients)
        result['link_to_movements'][link] = [
            {'movement': name, 'weight': total_weight * betas[name] / branch_total,
             'source': 'pinned_physical_route_after_branch', 'approach': old['approach']}
            for name in recipients]
        affected.append({'link': link, 'before_weight': total_weight,
                         'after_weight': sum(x['weight'] for x in result['link_to_movements'][link]),
                         'allowed_movements': recipients})
    for agent in result.get('agents', {}).values():
        if 'visible_movements' in agent:
            agent['visible_movements'] = [x for x in agent['visible_movements'] if x != removed]
    specs.pop(removed)
    for name, beta in betas.items():
        specs[name] = dict(specs[name], beta=beta)
    cfg.network.urban_movements = specs
    caps = getattr(cfg.network, 'movement_capacity_by_movement_veh_h', None)
    if isinstance(caps, dict):
        cfg.network.movement_capacity_by_movement_veh_h = {k: v for k, v in caps.items() if k != removed}
    rename = getattr(cfg.network, 'movement_merge_rename', None)
    if isinstance(rename, dict):
        cfg.network.movement_merge_rename = {k: v for k, v in rename.items() if v != removed}
    invalidate_topology_cache(cfg.network)
    return result, {'physical_route_topology_enabled': 1.0, 'removed_movement': removed,
        'native_route_betas': betas, 'physical_projection_changes': affected,
        'network': document['network'], 'evidence_path': path,
        'projection_requirement': 'Reproject original physical records; never discard an existing movement queue.',
        'prior_limitations': repair['prior_limitations']}


def build_input_contract(cfg, detectors, membership, gate_map_path):
    """Locate generated stock, without calling network-interior generation entry.

    Ramp demand has a known receiving queue but no independent VISSIM input on
    its connector. This contract labels that model injection explicitly.
    """
    physical = physical_membership_from_ledger(membership)
    network = ROOT / membership['network']['path']
    if hashlib.sha256(network.read_bytes()).hexdigest() != membership['network']['sha256']:
        raise ValueError('Input contract network hash mismatch')
    tree = ET.parse(network).getroot()
    inputs = {x.get('no'): x.get('link') for x in tree.findall('./vehicleInputs/vehicleInput')}
    gate_map = ROOT / gate_map_path
    with gate_map.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(line for line in handle if not line.startswith('#')))
    grouped, unmodeled = {}, []
    for row in rows:
        if inputs.get(row['no']) != row['link'] or row['link'] not in physical:
            raise ValueError('Gate input location differs from the pinned network')
        item = {'input': row['no'], 'link': row['link'], 'inside': physical[row['link']],
                'gate_map_status': row['status'], 'name': row['name']}
        if row['status'] == 'mapped':
            grouped.setdefault(row['gate'], []).append(item)
        elif row['status'] != 'freeway_excluded':
            unmodeled.append(item)
    origins = {str(spec.get('origin')) for spec in cfg.network.urban_movements.values()
               if str(spec.get('origin', '')).startswith('in_')}
    output = {}
    for origin in sorted(origins | grouped.keys()):
        sources = grouped.get(origin, [])
        sides = {row['inside'] for row in sources}
        known = len(sides) == 1
        target = next(iter(sides)) if known else None
        output['input:gate:' + origin] = {
            'status': 'unique' if len(sources) == 1 else 'same_transition' if known else 'no_match' if not sources else 'mixed_transition',
            'target_inside': target, 'physical_sources': sources,
            'event_kind': 'generation' if target else 'outside_generation' if known else 'unresolved_generation',
            'unresolved_reason': None if known else 'No unique physical input membership for this model origin.',
            'crossing_semantics': 'Generation at a physical input; creation itself is not an observed Omega boundary crossing.'}
    by_ramp = {str(ramp): [] for ramp in cfg.network.ramps}
    for link, ramps in detectors.get('ramp_link_to_queues', {}).items():
        for ramp in ramps:
            by_ramp.setdefault(str(ramp), []).append(str(link))
    for ramp, links in by_ramp.items():
        if set(links) - physical.keys():
            raise ValueError('Ramp input contract has unknown physical connector')
        sides = {physical[link] for link in links}
        known = len(sides) == 1
        output['input:ramp:' + ramp] = {
            'status': 'same_transition' if known else 'no_match' if not links else 'mixed_transition',
            'target_inside': next(iter(sides)) if known else None,
            'physical_receiving_links': links,
            'native_inputs_on_receiving_links': [key for key, link in inputs.items() if link in links],
            'event_kind': 'modeled_ramp_injection',
            'crossing_semantics': 'Explicit modeled arrival into the ramp stock; no independent native vehicle input is implied.',
            'unresolved_reason': None if known else 'Ramp receiving membership is unidentified.'}
    return {'routes': output, 'unmodeled_native_urban_inputs': unmodeled,
            'source': {'path': str(gate_map_path), 'sha256': hashlib.sha256(gate_map.read_bytes()).hexdigest()},
            'network': membership['network']}
