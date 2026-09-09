"""Explicitly configured physical topology repair for the shared runtime.

Frozen offline NC13 source-specific observations provide prediction priors.
Ownership files remain unchanged. Apply before projecting the original snapshot.
"""
from copy import deepcopy
import math
import hashlib
import json
import xml.etree.ElementTree as ET
from evaluation.controllers.physical_movement_routes import (
    ROOT, load_evidence, path_membership, invalidate_topology_cache)
from evaluation.controllers.control_area_objective import physical_membership_from_ledger
from evaluation.controllers.network_provenance import snapshot_network_sha256


def checked_evidence(path):
    document, native, edges = load_evidence(path)
    tree = ET.parse(ROOT / document['network']['path']).getroot()
    links = {row.get('no'): row for row in tree.findall('./links/link')}
    for name, row in document['by_movement'].items():
        trace = row['path']
        for previous, current, following in zip(trace, trace[1:], trace[2:]):
            entering = links[previous].find('toLinkEndPt')
            leaving = links[following].find('fromLinkEndPt')
            if entering is not None and leaving is not None:
                if float(entering.get('pos')) > float(leaving.get('pos')) + 1e-7:
                    raise ValueError(f'{name}: path turns back behind its physical entry position on {current}')
    return document, native, edges, links


def configure(cfg, detectors, tuning, *, state_json):
    path = tuning.get('urban', {}).get('movements', {}).get('dynamic_physical_route_topology')
    if path is None:
        return detectors, {}
    if not isinstance(path, str) or not path:
        raise ValueError('dynamic_physical_route_topology must name pinned evidence')
    document, native, edges, links = checked_evidence(path)
    if snapshot_network_sha256(state_json) != document['network']['sha256']:
        raise ValueError('Snapshot and dynamic topology network hashes differ')
    calibration_path = ROOT / document['calibration']['path']
    if hashlib.sha256(calibration_path.read_bytes()).hexdigest() != document['calibration']['sha256']:
        raise ValueError('Frozen offline route calibration hash differs')
    calibration = json.loads(calibration_path.read_text(encoding='utf-8'))
    if calibration['network'] != document['network']:
        raise ValueError('Calibration and topology network differ')
    specs = deepcopy(cfg.network.urban_movements)
    output = deepcopy(detectors)
    removed_names, metadata = [], []
    for repair in document['topology_repairs']:
        removed = repair['remove_movement']
        old = specs.get(removed, {})
        if any(old.get(key) != value for key, value in repair['expected_removed_spec'].items()):
            raise ValueError(f'{removed}: canonical movement semantics changed')
        outgoing = {b for a, b in edges if a == repair['physical_stopline']}
        if outgoing != set(repair['expected_outgoing_connectors']):
            raise ValueError(f'{removed}: physical turn choices changed')
        weights = {}
        for name, key in repair['keep_movements'].items():
            route = native[key]
            if specs[name]['origin'] != old['origin'] or specs[name]['signal'] != old['signal']:
                raise ValueError('A repaired branch must retain its original physical approach')
            if repair['physical_stopline'] not in route['path']:
                raise ValueError('Native route does not cross the reviewed stopline')
            prior = calibration['priors'][old['origin']]
            count = prior['counts'][specs[name]['turn']]
            weight = count / prior['completed_denominator']
            if not math.isfinite(weight) or weight < 0 or weight != prior['shares'][specs[name]['turn']]:
                raise ValueError('Offline prior shares do not match observed completed-cohort counts')
            weights[name] = weight
        total = sum(weights.values())
        if not math.isclose(total, 1.0, abs_tol=1e-12):
            raise ValueError('Completed observed choices do not cover the retained movements')
        betas = {name: weight / total for name, weight in weights.items()}
        affected = []
        for link, rows in output.get('link_to_movements', {}).items():
            if not any(row['movement'] == removed for row in rows):
                continue
            if link not in repair['physical_projection_links']:
                raise ValueError(f'{removed}: observation on unreviewed physical link {link}')
            if any(row['movement'] not in {removed, *betas} for row in rows):
                raise ValueError('Physical source has unrelated model assignments')
            total_weight = sum(float(row['weight']) for row in rows)
            output['link_to_movements'][link] = [
                {'movement': name, 'weight': total_weight * beta, 'approach': old['approach'],
                 'source': 'offline_nc13_route_prior_without_phantom'} for name, beta in betas.items()]
            affected.append({'link': link, 'before_weight': total_weight,
                             'after_weight': sum(row['weight'] for row in output['link_to_movements'][link])})
        if set(row['link'] for row in affected) != set(repair['physical_projection_links']):
            raise ValueError('Canonical detector support differs from reviewed physical projection')
        specs.pop(removed)
        for name, beta in betas.items():
            specs[name]['beta'] = beta
        removed_names.append(removed)
        metadata.append({'removed_movement': removed, 'offline_calibrated_betas': betas,
                         'projection': affected, 'limitations': repair['prior_limitations']})
    origin_changes = []
    for repair in document.get('origin_repairs', []):
        link, target = repair['physical_link'], repair['target_origin']
        before = output['link_to_origins'].get(link)
        if before != repair['expected_origins']:
            raise ValueError('Reviewed source origin aliases changed')
        if not any(spec['origin'] == target for spec in specs.values()):
            raise ValueError('Physical origin has no modeled receiving movements')
        if any(native[key]['path'][0] != link for key in repair['native_routes']):
            raise ValueError('Source proof does not start at the actual observation link')
        output['link_to_origins'][link] = [target]
        origin_changes.append({'physical_link': link, 'before': before, 'after': [target]})
    for agent in output.get('agents', {}).values():
        if 'visible_movements' in agent:
            agent['visible_movements'] = [name for name in agent['visible_movements'] if name not in removed_names]
    cfg.network.urban_movements = specs
    cfg.network.dynamic_physical_route_topology_path = path
    for field in ('movement_capacity_by_movement_veh_h', 'movement_merge_rename'):
        mapping = getattr(cfg.network, field, None)
        if isinstance(mapping, dict):
            setattr(cfg.network, field, {key: value for key, value in mapping.items()
                if (value if field == 'movement_merge_rename' else key) not in removed_names})
    invalidate_topology_cache(cfg.network)
    return output, {'dynamic_physical_route_topology': path, 'repairs': metadata,
                    'origin_repairs': origin_changes, 'network': document['network'],
                    'offline_route_calibration': document['calibration'],
                    'native_decision_positions': calibration['native_decision_positions']}


def extend_routes(cfg, routes, detectors, membership, path):
    document, _, _, _ = checked_evidence(path)
    physical = physical_membership_from_ledger(membership)
    output, resolved = deepcopy(routes), []
    for name, row in document['by_movement'].items():
        choice = getattr(cfg.network, 'route_choice_corridor', None)
        if choice and name in choice['renames']:
            replacement = choice['renames'][name]
            if name in cfg.network.urban_movements or replacement not in choice['turns']:
                raise ValueError(f'{name}: invalid route-choice movement coalescing')
            continue
        spec = cfg.network.urban_movements[name]
        if any(spec.get(key) != value for key, value in row['expected_spec'].items()):
            raise ValueError(f'{name}: model path identity changed')
        if spec['receiving_link'] not in detectors['link_to_origins'].get(row['path'][-1], []):
            raise ValueError(f'{name}: final physical link does not support the model receiver')
        turn = path_membership(row['path'], physical)
        output['movement:' + name] = dict(turn, status='position_checked_native_path',
            inside_to_inside=float(turn['target_inside']), outside_to_inside=float(turn['target_inside']),
            physical_turns=[dict(turn, native_routes=row['native_routes'])],
            timing_assumption=row['timing_assumption'])
        key = 'arrival:' + name
        if type(output.get(key, {}).get('target_inside')) is not bool:
            output[key] = {'target_inside': turn['source_inside'],
                           'inside_to_inside': float(turn['source_inside']),
                           'outside_to_inside': float(turn['source_inside']),
                           'status': 'position_checked_native_approach'}
        resolved.append(name)
    return output, {'dynamic_native_paths_resolved': resolved}
