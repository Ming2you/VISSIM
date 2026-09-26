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

from evaluation.controllers.beta_source import complete_beta_source
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


def configure_phase_authority(cfg, tuning, selected_plan, *, state_json=None):
    """After movement merging, before capacity estimation and follower creation.

    Correct only explicitly reviewed phase fields or a proven pre-head peel-off.
    Native routing/receiver/stock and service capacity are not inferred or changed.
    Workers inherit these configured specs; this is not a runtime method patch.
    """
    path = tuning.get('urban', {}).get('movements', {}).get('physical_phase_authority')
    if path is None:
        return {}
    if not isinstance(path, str) or not path:
        raise ValueError('physical_phase_authority must name a pinned evidence document')
    document, routes, edges = load_evidence(path)
    if document.get('schema') != 'physical-phase-authority/v1':
        raise ValueError('Unsupported phase authority evidence schema')
    if state_json is not None and snapshot_network_sha256(state_json) != document['network']['sha256']:
        raise ValueError('Snapshot and phase authority network hashes differ')
    plan_path = ROOT / document['selected_plan']['path']
    plan_bytes = plan_path.read_bytes()
    if hashlib.sha256(plan_bytes).hexdigest() != document['selected_plan']['sha256']:
        raise ValueError('Phase authority selected plan hash mismatch')
    if selected_plan != json.loads(plan_bytes.decode('utf-8-sig')):
        raise ValueError('Actual selected plan differs from phase authority evidence')
    tree = ET.parse(ROOT / document['network']['path']).getroot()
    links = {x.get('no'): x for x in tree.findall('./links/link')}
    heads = {x.get('no'): x for x in tree.findall('./signalHeads/signalHead')}
    specs = dict(cfg.network.urban_movements)
    changes = {}
    for name, row in document['by_movement'].items():
        spec = specs.get(name)
        if spec is None or any(spec.get(k) != v for k, v in row['expected_spec'].items()):
            raise ValueError(f'{name}: stale expected movement/phase semantics')
        if spec.get('unsignalized'):
            raise ValueError(f'{name}: phase correction cannot change unsignalized authority')
        source, connector, target = row['path']
        node, expected = links[connector], row['connector']
        start, end = node.find('fromLinkEndPt'), node.find('toLinkEndPt')
        actual_connector = {'id': connector, 'source_lane': int(start.get('lane').split()[1]),
            'source_pos': float(start.get('pos')), 'target_lane': int(end.get('lane').split()[1]),
            'target_pos': float(end.get('pos')), 'lanes': len(node.findall('./lanes/lane'))}
        if actual_connector != expected or start.get('lane').split()[0] != source or end.get('lane').split()[0] != target:
            raise ValueError(f'{name}: connector lane/position evidence changed')
        signal = str(spec['signal'])
        own_heads = [h for h in heads.values() if h.get('lane').split()[0] == source
                     and h.get('sg').split()[0] == signal.removeprefix('SC')]
        if {h.get('no') for h in own_heads} != {h['head'] for h in row['source_heads']}:
            raise ValueError(f'{name}: source head set changed')
        for evidence in row['source_heads']:
            head = heads[evidence['head']]
            actual = {'head': head.get('no'), 'link': head.get('lane').split()[0],
                'lane': int(head.get('lane').split()[1]), 'pos_m': float(head.get('pos')),
                'SC': 'SC' + head.get('sg').split()[0], 'SG': head.get('sg').split()[1],
                'all_vehicle_types': head.get('allVehTypes') == 'true',
                'compliance': float(head.get('complRate', 1))}
            if actual != evidence or not actual['all_vehicle_types'] or actual['compliance'] != 1:
                raise ValueError(f'{name}: source head lane/position/applicability changed')
        source_heads = row['source_heads']
        lanes = {h['lane'] for h in source_heads if h['pos_m'] < expected['source_pos']}
        if lanes != set(range(1, len(links[source].findall('./lanes/lane')) + 1)):
            raise ValueError(f'{name}: source lanes lack complete pre-branch head coverage')
        matching = []
        for route_id, route in routes.items():
            sequence = route['path']
            for index in range(len(sequence) - 2):
                if sequence[index:index + 3] != row['path']:
                    continue
                entry = (float(route['decision']['pos']) if index == 0 else
                         float(links[sequence[index - 1]].find('toLinkEndPt').get('pos')))
                if entry >= min(h['pos_m'] for h in source_heads):
                    raise ValueError(f'{name}: native route enters after the controlling head')
                matching.append(route_id)
                break
        if set(matching) != set(row['native_routes']) or not matching:
            raise ValueError(f'{name}: native route witness set changed')
        groups = selected_plan['controllers'][signal.removeprefix('SC')]['phase_signal_groups']
        source_sgs = {h['SG'] for h in source_heads}
        owners = {phase for phase, sgs in groups.items() if source_sgs & set(map(str, sgs))}
        new_phase = row['new_phase']
        if len(owners) != 1 or new_phase != signal + '_' + next(iter(owners)):
            raise ValueError(f'{name}: source SG has no unique selected target phase')
        if not source_sgs <= set(map(str, groups[new_phase.rpartition('_')[2]])):
            raise ValueError(f'{name}: selected target phase omits a source SG')
        old_sgs = set(map(str, groups[spec['phase'].rpartition('_')[2]]))
        if source_sgs & old_sgs:
            raise ValueError(f'{name}: old/new SG authority is not disjoint')
        changes[name] = {'before': spec['phase'], 'after': new_phase, 'source_SGs': sorted(source_sgs)}
        specs[name] = dict(spec, phase=new_phase)
    unsignalized_changes = {}
    if 'unsignalized_movements' in document:
        peeloffs = document['unsignalized_movements']
        supported = {'SC1004_W_to_S', 'SC1004_offW_to_S', 'SC1004_offE_to_S'}
        if not isinstance(peeloffs, dict) or set(peeloffs) != supported:
            raise ValueError('Unsignalized authority requires exactly the three reviewed SC1004 aliases')
        for name, row in peeloffs.items():
            spec = specs.get(name)
            expected_spec = row['expected_spec']
            if (not {'phase', 'kind', 'origin', 'receiving_link'} <= expected_spec.keys()
                    or spec is None or spec.get('signal') != 'SC1004'
                    or any(spec.get(k) != v for k, v in expected_spec.items())
                    or spec.get('unsignalized')):
                raise ValueError(f'{name}: stale expected unsignalized movement semantics')
            if row['path'] != ['71', '10642', '67']:
                raise ValueError(f'{name}: unsupported unsignalized physical path')
            source, connector, target = row['path']
            if any(edge not in edges for edge in zip(row['path'], row['path'][1:])):
                raise ValueError(f'{name}: disconnected unsignalized physical path')
            node, expected = links[connector], row['connector']
            start, end = node.find('fromLinkEndPt'), node.find('toLinkEndPt')
            actual_connector = {'id': connector, 'source_lane': int(start.get('lane').split()[1]),
                'source_pos': float(start.get('pos')), 'target_lane': int(end.get('lane').split()[1]),
                'target_pos': float(end.get('pos')), 'lanes': len(node.findall('./lanes/lane'))}
            if (actual_connector != expected or start.get('lane').split()[0] != source
                    or end.get('lane').split()[0] != target):
                raise ValueError(f'{name}: unsignalized connector lane/position evidence changed')
            # Every controller head on the source must be downstream, not just
            # heads of the old phase. A later connector/target head is unsupported.
            source_heads = [h for h in heads.values() if h.get('lane').split()[0] == source]
            cited = row['source_heads']
            if (not source_heads or len(cited) != len(source_heads)
                    or {h.get('no') for h in source_heads} != {h['head'] for h in cited}):
                raise ValueError(f'{name}: unsignalized source head set changed')
            groups = selected_plan['controllers']['1004']['phase_signal_groups']
            known_sgs = {str(sg) for group in groups.values() for sg in group}
            if spec['phase'] not in {'SC1004_' + phase for phase in groups}:
                raise ValueError(f'{name}: unknown preserved selected phase')
            for evidence in cited:
                head = heads[evidence['head']]
                actual = {'head': head.get('no'), 'link': head.get('lane').split()[0],
                    'lane': int(head.get('lane').split()[1]), 'pos_m': float(head.get('pos')),
                    'SC': 'SC' + head.get('sg').split()[0], 'SG': head.get('sg').split()[1],
                    'all_vehicle_types': head.get('allVehTypes') == 'true',
                    'compliance': float(head.get('complRate', 1))}
                if (actual != evidence or actual['SC'] != spec['signal'] or actual['SG'] not in known_sgs
                        or not actual['all_vehicle_types'] or actual['compliance'] != 1
                        or not math.isfinite(actual['pos_m'])
                        or not actual['pos_m'] > actual_connector['source_pos']):
                    raise ValueError(f'{name}: source head is not a proven downstream head')
            if any(h.get('lane').split()[0] in {connector, target} for h in heads.values()):
                raise ValueError(f'{name}: connector/landing link has an unsupported signal head')
            matching = []
            for route_id, route in routes.items():
                sequence = route['path']
                for index in range(len(sequence) - 2):
                    if sequence[index:index + 3] != row['path']:
                        continue
                    if (route['decision'].get('allVehTypes') != 'true'
                            or route['decision'].get('routeChoiceMeth') != 'STATIC'):
                        raise ValueError(f'{name}: unsupported unsignalized route applicability')
                    entry = (float(route['decision']['pos']) if index == 0 else
                             float(links[sequence[index - 1]].find('toLinkEndPt').get('pos')))
                    if not math.isfinite(entry) or not 0 <= entry <= actual_connector['source_pos']:
                        raise ValueError(f'{name}: native route enters after the peel-off')
                    matching.append(route_id)
                    break
            if (not matching or len(row['native_routes']) != len(matching)
                    or set(matching) != set(row['native_routes'])):
                raise ValueError(f'{name}: unsignalized native route witness set changed')
            unsignalized_changes[name] = {'before': spec.get('unsignalized', False), 'after': True,
                                         'preserved_phase': spec['phase'], 'path': list(row['path'])}
            specs[name] = dict(spec, unsignalized=True)
    if 'head_free_movements' in document:
        tunnels = document['head_free_movements']
        name = 'SC107_N_SC1_to_S'
        if not isinstance(tunnels, dict) or set(tunnels) != {name}:
            raise ValueError('Head-free authority requires the single reviewed SC107 tunnel')
        row, spec = tunnels[name], specs.get(name)
        required = {'signal', 'phase', 'kind', 'origin', 'receiving_link', 'approach', 'turn'}
        expected_spec = row['expected_spec']
        if (not required <= expected_spec.keys() or spec is None
                or spec.get('signal') != 'SC107' or spec.get('phase') != 'SC107_p2'
                or any(spec.get(k) != v for k, v in expected_spec.items())
                or spec.get('unsignalized')):
            raise ValueError(f'{name}: stale expected head-free movement semantics')
        tunnel_path = ['1220006803', '10597', '1220006801', '10594', '1220042200']
        if row['path'] != tunnel_path or any(edge not in edges for edge in zip(tunnel_path, tunnel_path[1:])):
            raise ValueError(f'{name}: disconnected or unsupported head-free path')
        if any(h.get('lane').split()[0] in tunnel_path for h in heads.values()):
            raise ValueError(f'{name}: head-free path contains a signal head')
        connectors = {}
        for index in (1, 3):
            node = links[tunnel_path[index]]
            start, end = node.find('fromLinkEndPt'), node.find('toLinkEndPt')
            if (start.get('lane').split()[0] != tunnel_path[index - 1]
                    or end.get('lane').split()[0] != tunnel_path[index + 1]):
                raise ValueError(f'{name}: head-free connector endpoints changed')
            connectors[tunnel_path[index]] = {
                'source_lane': int(start.get('lane').split()[1]), 'source_pos': float(start.get('pos')),
                'target_lane': int(end.get('lane').split()[1]), 'target_pos': float(end.get('pos')),
                'lanes': len(node.findall('./lanes/lane'))}
        if connectors != row['connectors']:
            raise ValueError(f'{name}: head-free connector lane/position evidence changed')
        matching = {key: route for key, route in routes.items() if '10597' in route['path']}
        if row['native_routes'] != ['1063:2'] or set(matching) != {'1063:2'}:
            raise ValueError(f'{name}: head-free native route witness set changed')
        route = matching['1063:2']
        decision = route['decision']
        actual_decision = {'no': decision['no'], 'link': decision['link'],
                           'pos': float(decision['pos']), 'allVehTypes': decision['allVehTypes'],
                           'routeChoiceMeth': decision['routeChoiceMeth']}
        if (route['path'] != tunnel_path or actual_decision != row['decision']
                or decision['allVehTypes'] != 'true' or decision['routeChoiceMeth'] != 'STATIC'
                or not 0 <= actual_decision['pos'] < connectors['10597']['source_pos']):
            raise ValueError(f'{name}: head-free native route identity changed')
        conflicts = {x.get('no'): {k: x.get(k) for k in ('link1', 'link2', 'status')}
                     for x in tree.findall('./conflictAreas/conflictArea')
                     if x.get('link1') in tunnel_path or x.get('link2') in tunnel_path}
        if conflicts != row['conflicts'] or any(x['status'] != 'PASSIVE' for x in conflicts.values()):
            raise ValueError(f'{name}: head-free conflict authority changed')
        unsignalized_changes[name] = {'before': spec.get('unsignalized', False), 'after': True,
                                     'preserved_phase': spec['phase'], 'path': tunnel_path}
        specs[name] = dict(spec, unsignalized=True)
    # All proofs pass before committing any movement; no projected state is used.
    cfg.network.urban_movements = specs
    invalidate_topology_cache(cfg.network)
    result = {'physical_phase_authority_corrected_count': len(changes),
            'physical_phase_authority_changes': changes, 'physical_phase_authority_evidence_path': path,
            'physical_phase_authority_evidence_sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}
    if 'unsignalized_movements' in document or 'head_free_movements' in document:
        result.update(physical_unsignalized_authority_corrected_count=len(unsignalized_changes),
                      physical_unsignalized_authority_changes=unsignalized_changes)
    return result


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


def configure_native_input_signal_authority(cfg, tuning, detectors, *, state_json):
    """Bind input1083 to its first selected head, before physical projection.

    Call after dynamic origin repairs and capacity estimation. This validates and
    narrows the existing movement only. Native-input code owns position-based
    initial cohorts, generation, travel readiness and the area route extension.
    No storage envelope, service rate, receiving stock or signal clock is fitted.
    """
    path = tuning.get('urban', {}).get('movements', {}).get('native_input_signal_authority')
    if path is None:
        return detectors, {}
    if not isinstance(path, str) or not path:
        raise ValueError('native_input_signal_authority must name pinned evidence')
    if getattr(cfg.network, 'native_input_signal_authority', None) is not None:
        raise ValueError('Native input signal authority must configure once before projection')
    source_bytes = (ROOT / path).read_bytes()
    evidence = json.loads(source_bytes.decode('utf-8-sig'))
    if evidence.get('schema') != 'native-input-signal-authority/v1' or set(evidence['inputs']) != {'1083'}:
        raise ValueError('Only the reviewed input1083 signal approach is supported')
    documents = {}
    for key in ('network', 'selected_plan', 'membership'):
        record = evidence[key]
        content = (ROOT / record['path']).read_bytes()
        if hashlib.sha256(content).hexdigest() != record['sha256']:
            raise ValueError('Native input signal authority source hash differs: ' + key)
        documents[key] = content
    if snapshot_network_sha256(state_json) != evidence['network']['sha256']:
        raise ValueError('Native input signal authority snapshot network differs')
    physical = physical_membership_from_ledger(json.loads(documents['membership'].decode('utf-8-sig')))
    tree = ET.fromstring(documents['network'])
    links = {x.get('no'): x for x in tree.findall('./links/link')}
    row = evidence['inputs']['1083']
    source, connector, receiver = row['physical_path']
    if source != row['physical_source'] or connector != row['connector']:
        raise ValueError('Native input signal approach path differs')
    inputs = [x for x in tree.findall('./vehicleInputs/vehicleInput') if x.get('link') == source]
    if len(inputs) != 1 or inputs[0].get('no') != '1083':
        raise ValueError('Native signal source has additional or missing input')
    if any(x.find('toLinkEndPt') is not None and x.find('toLinkEndPt').get('lane').split()[0] == source for x in links.values()):
        raise ValueError('Native signal source also receives an upstream cohort')
    outgoing = [x for x in links.values() if x.find('fromLinkEndPt') is not None and x.find('fromLinkEndPt').get('lane').split()[0] == source]
    if len(outgoing) != 1 or outgoing[0].get('no') != connector:
        raise ValueError('Native signal source is no longer a single physical turn')
    node = outgoing[0]
    if (dict(node.find('fromLinkEndPt').attrib) != row['connector_from']
            or dict(node.find('toLinkEndPt').attrib) != row['connector_to']
            or node.find('toLinkEndPt').get('lane').split()[0] != receiver
            or len(node.findall('./lanes/lane')) != row['connector_lanes']
            or len(links[source].findall('./lanes/lane')) != row['source_lanes']):
        raise ValueError('Native signal connector lane/position geometry differs')
    heads = [dict(x.attrib) for x in tree.findall('./signalHeads/signalHead') if x.get('lane').split()[0] == source]
    if heads != row['source_heads']:
        raise ValueError('Native signal source head evidence differs')
    head_positions = {}
    for h in heads:
        lane = int(h['lane'].split()[1])
        if (h['sg'] != '108 2' or h['allVehTypes'] != 'true' or float(h['complRate']) != 1
                or lane in head_positions or not 0 < float(h['pos']) < float(row['connector_from']['pos'])):
            raise ValueError('Native signal source head authority is incomplete')
        head_positions[lane] = float(h['pos'])
    if set(head_positions) != set(range(1, row['source_lanes'] + 1)):
        raise ValueError('Native signal source has a lane without its selected head')
    plan = json.loads(documents['selected_plan'].decode('utf-8-sig'))['controllers']['108']
    actual = (getattr(cfg.network, 'signal_actuation_contract', None) or {}).get('nodes', {}).get('SC108')
    if not actual or any(actual.get(k) != v for k, v in plan.items()):
        raise ValueError('Native signal source needs the actual selected physical signal contract')
    phases = [p for p, sgs in plan['phase_signal_groups'].items() if '2' in sgs and plan['phase_segments'][p]]
    if phases != ['p3'] or row['phase'] != 'SC108_p3':
        raise ValueError('Native signal source SG does not uniquely own p3')
    decisions = tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')
    if any(x.get('link') == source for x in decisions):
        raise ValueError('Native signal source acquired an unreviewed routing decision')
    excluded = row['excluded_upstream_decision']
    decision = next((x for x in decisions if x.get('no') == excluded['no']), None)
    if (decision is None or decision.get('link') != receiver
            or float(decision.get('pos')) != excluded['pos']
            or float(decision.get('pos')) >= float(row['connector_to']['pos'])):
        raise ValueError('Excluded receiver decision is no longer upstream of the source merge')
    origin, target, kept = row['pre_head_storage'], row['post_head_storage'], row['kept_movement']
    if (origin, target, kept) != ('in_SC108_W', 'SC108_to_SC109', 'SC108_W_to_E_SC109'):
        raise ValueError('Native input1083 names a different modeled approach or receiver')
    specs = cfg.network.urban_movements
    siblings = {name for name, spec in specs.items() if spec.get('origin') == origin}
    if siblings != set(row['expected_movements']):
        raise ValueError('Native signal origin acquired an unreviewed movement')
    # The pinned 'beta' of each expected movement is the routing table's value when this evidence was reviewed. A
    # complete beta source (urban.beta.source routing_v3b2) already gives this single-connector origin its physical
    # split, so there the check is: the kept movement carries 1 and every sibling 0 (the result committed below).
    complete = complete_beta_source(tuning)
    for name, expected in row['expected_movements'].items():
        if (any(specs[name].get(k) != v for k, v in expected.items() if not (complete and k == 'beta'))
                or specs[name].get('unsignalized')):
            raise ValueError('Native signal movement semantics changed: ' + name)
        if complete and not math.isclose(float(specs[name].get('beta', 0.0)), 1.0 if name == kept else 0.0,
                                         rel_tol=0.0, abs_tol=1e-9):
            raise ValueError('Complete beta source disagrees with the single native turn: ' + name)
    for link, origins in detectors.get('link_to_origins', {}).items():
        if origin in origins:
            raise ValueError('Native signal origin still has another physical observation: ' + str(link))
    if any(x.get('movement') in siblings and float(x.get('weight', 1)) > 0
           for rows in detectors.get('link_to_movements', {}).values() for x in rows):
        raise ValueError('Native signal movement already receives another observed source')
    if float(state_json['demand'].get('urban_volume_vph_by_gate', {}).get(origin, 0)) != 0:
        raise ValueError('Native signal origin already has an external gate forecast')
    for link in row['receiver_support']:
        if target not in detectors.get('link_to_origins', {}).get(link, []):
            raise ValueError('Native signal receiver lacks its physical downstream support')
    if any(not physical.get(link, False) for link in row['physical_path'] + row['receiver_support']):
        raise ValueError('Native signal path no longer lies entirely inside the declared area')
    caps = cfg.network.movement_capacity_by_movement_veh_h
    capacity = float(caps[kept])
    storage = float(cfg.network.urban_link_storage_veh[origin])
    if not math.isfinite(capacity + storage) or min(capacity, storage) <= 0:
        raise ValueError('Native signal origin lacks its existing finite service/storage envelope')
    removed = siblings - {kept}
    out = copy.deepcopy(detectors)
    for agent in out.get('agents', {}).values():
        if 'visible_movements' in agent:
            agent['visible_movements'] = [m for m in agent['visible_movements'] if m not in removed]
    route = path_membership(row['physical_path'], physical)
    route.update(from_link=source, connector=connector, to_link=receiver)
    proof = {**copy.deepcopy(row), 'source_contract_validated': True,
             'head_position_by_lane_m': {str(k): v for k, v in head_positions.items()},
             'preserved_movement_capacity_veh_h': capacity, 'preserved_storage_capacity_veh': storage,
             'movement_area_route': {'status': 'unique', 'source_inside': True, 'target_inside': True,
                 'physical_turns': [route], 'outward_crossings_per_vehicle': 0, 'inward_crossings_per_vehicle': 0}}
    # Commit only after every native, model, observation and area proof passes.
    cfg.network.urban_movements = {k: (dict(v, beta=1.0) if k == kept else v) for k, v in specs.items() if k not in removed}
    cfg.network.movement_capacity_by_movement_veh_h = {k: v for k, v in caps.items() if k not in removed}
    rename = getattr(cfg.network, 'movement_merge_rename', None)
    if isinstance(rename, dict):
        cfg.network.movement_merge_rename = {k: v for k, v in rename.items() if v not in removed}
    cfg.network.native_input_signal_authority = {'schema': evidence['schema'], 'inputs': {'1083': proof},
        'source_path': path, 'source_sha256': hashlib.sha256(source_bytes).hexdigest(), 'network_sha256': evidence['network']['sha256']}
    invalidate_topology_cache(cfg.network)
    return out, {'native_input_signal_authority': copy.deepcopy(cfg.network.native_input_signal_authority),
                 'native_input_signal_removed_movements': sorted(removed)}


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
