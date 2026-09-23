"""Measured head support joined to verified canonical physical resources.

No seed-max metadata is a measurement. No traffic or action is created here.
"""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
EPS = 1e-8


def _read(pin):
    data = (ROOT / pin['path']).read_bytes()
    if hashlib.sha256(data).hexdigest() != pin['sha256']:
        raise ValueError('Physical head resource evidence changed')
    return data


def view(cfg):
    return getattr(cfg.network, 'head_service_resources', None)


def configure(cfg, tuning, raw, plan):
    section = (tuning or {}).get('urban', {}).get('capacity', {})
    path = section.get('head_resource_contract')
    if path is None:
        current = view(cfg)
        if current is not None:
            if current.get('schema') != 'physical-head-resource-join/v1':
                raise ValueError('Cannot clear an unowned physical head resource view')
            delattr(cfg.network, 'head_service_resources')
        return {}
    if not isinstance(path, str) or not path or section.get('head_observation', {}).get('enabled') is not True:
        raise ValueError('Physical resource contract requires enabled head observation')
    if tuning.get('urban', {}).get('shared_local_service_pool') is not True:
        raise ValueError('Physical head resource application requires the shared local service pool')
    data = (ROOT / path).read_bytes(); document = json.loads(data)
    if document.get('schema') != 'physical-head-resource-join/v1' or set(document['resources']) != {'10619', '10629'}:
        raise ValueError('Unreviewed physical head resource set')
    network = _read(document['network'])
    if tuning.get('execution', {}).get('native_signal_record') is True:
        from evaluation.controllers.network_provenance import snapshot_physical_file_sha256
        matches = snapshot_physical_file_sha256(raw) == hashlib.sha256(network).hexdigest()
    else:
        matches = hashlib.sha256(Path(raw['network_path']).read_bytes()).digest() == hashlib.sha256(network).digest()
    if not matches:
        raise ValueError('Head resource and snapshot networks differ')
    from evaluation.controllers.signal_head_observation import physical_groups
    geometry = physical_groups(raw['network_path'], plan)
    tree = ET.fromstring(network); links = {n.get('no'): n for n in tree.findall('./links/link')}
    for connector, row in document['resources'].items():
        key = tuple(row['group'].split('|')); heads = geometry.get(key)
        if heads != row['heads'] or len({h['sg'] for h in heads}) != 1:
            raise ValueError('Physical resource head/lane/selected-SG binding changed')
        node = links[connector]; source = node.find('fromLinkEndPt'); target = node.find('toLinkEndPt')
        first = int(source.get('lane').split()[1]); lanes = len(node.findall('./lanes/lane'))
        if (source.get('lane').split()[0] != key[0] or target.get('lane').split()[0] != row['target_link']
                or set(range(first, first+lanes)) != {h['lane'] for h in heads}
                or any(h['position_m'] >= float(source.get('pos')) for h in heads)):
            raise ValueError('Head resource does not cover exactly its post-head connector lanes')
        # Every directly competing connector on these source lanes must branch
        # before the head. This rejects adding a post-head ambiguous resource.
        for other in links.values():
            edge = other.find('fromLinkEndPt')
            if edge is None or other.get('no') == connector or edge.get('lane').split()[0] != key[0]:
                continue
            lo = int(edge.get('lane').split()[1]); overlap = set(range(lo, lo+len(other.findall('./lanes/lane')))) & {h['lane'] for h in heads}
            if any(float(edge.get('pos')) >= h['position_m'] for h in heads if h['lane'] in overlap):
                raise ValueError('Another physical connector competes after the measured heads')
        proof = json.loads(_read(row['proof']))
        if row['mode'] == 'route_turn':
            incoming = [r for r in proof['incoming_turns'].values() if r['connector'] == connector]
            if len(incoming) != 1 or {incoming[0]['keep']} != set(row['members']) or incoming[0]['signal_controlled'] is not True:
                raise ValueError('Route-owned head resource lacks its exact finite-corridor turn')
        elif row['mode'] == 'regular_pool':
            for name in row['members']:
                evidence = [r for r in proof['topology_repairs'] if name in r['keep_movements']]
                if len(evidence) != 1 or evidence[0]['physical_stopline'] != key[0] or evidence[0]['keep_movements'][name] != '1123:2':
                    raise ValueError('Source alias lacks its verified common physical turn')
            decision = next(d for d in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic') if d.get('no') == '1123')
            route = next(r for r in decision.findall('./vehRoutSta/vehicleRouteStatic') if r.get('no') == '2')
            if [n.get('key') for n in route.findall('./linkSeq/intObjectRef')] != [connector] or route.get('destLink') != row['target_link']:
                raise ValueError('Verified native resource route changed')
        else:
            raise ValueError('Unsupported head resource consumer')
    cfg.network.head_service_resources = {**document, 'contract_sha256': hashlib.sha256(data).hexdigest(),
                                          'observations': {}, 'extra_pool_groups': {}}
    return {'physical_head_resource_contract_enabled': 1.}


def observe(original, cfg, raw, previous_path, caps, plan, distribute, options):
    resource = view(cfg)
    if resource is None:
        return original(cfg, raw, previous_path, caps, plan, distribute, options)
    from evaluation.controllers.signal_head_observation import physical_groups, number
    geometry = physical_groups(raw['network_path'], plan)
    groups = [{'stopline_link': k[0], 'signal': 'SC'+v[0]['sc']} for k, v in geometry.items()]
    memberships = {}
    for key in geometry:
        weights = {}; distribute(cfg, groups, {key: 1.}, weights); memberships[key] = set(weights)
    owned = {tuple(row['group'].split('|')) for row in resource['resources'].values()}
    managed = set().union(*(memberships[k] for k in owned))
    if any(managed & members for key, members in memberships.items() if key not in owned):
        raise ValueError('Managed resource members overlap another observer group')
    metadata = original(cfg, raw, previous_path, caps, plan, distribute, options)
    # Undo only the known provisional allocations. Canonical physical topology
    # still removes phantom movements, and later resource joining owns the rate.
    changed = dict(cfg.network.movement_capacity_by_movement_veh_h)
    for m in managed:
        changed[m] = caps[m]
    cfg.network.movement_capacity_by_movement_veh_h = changed
    doc = {}
    try:
        doc = json.loads(Path(previous_path).read_text(encoding='utf-8-sig'))
        prior = {**doc.get('diagnostics', {}), **doc.get('metadata', {})}
    except (OSError, TypeError, ValueError):
        prior = {}
    context = next(k for k in metadata if k.startswith('head_provenance_'))
    window = raw['local_observation'].get('signal_observation_window') or {}
    # The legacy observer does not recognize the new namespace as a prior.
    # Therefore independently verify the original action envelope even when
    # it contains only a carried observed-only value and no current candidates.
    try:
        previous_time = number(doc['metadata']['sim_sec'])
        previous_ok = (prior.get(context) == 1.0 and not metadata.get('head_observation_prior_discarded')
            and doc['run_provenance']['run_id'] == raw['run_provenance']['run_id']
            and number(prior['head_observation_snapshot_sec']) == previous_time == window.get('start_sec')
            and previous_time < number(raw['sim_sec'])
            and all(number(v) == previous_time for k,v in prior.items() if k.startswith('head_candidate_end_')))
    except (KeyError, TypeError, ValueError):
        previous_ok = False
    for connector, row in resource['resources'].items():
        suffix = hashlib.sha256((context+resource['contract_sha256']+connector).encode()).hexdigest()[:16]
        name = 'head_resource_observed_floor_'+connector+'_'+suffix
        carried = number(prior.get(name, 0.)) if previous_ok else 0.
        if not math.isfinite(carried) or carried < 0:
            raise ValueError('Invalid previous observed-only physical resource support')
        prefix = row['group'].replace('|', '_')+'_'
        candidate = [k for k in metadata if k.startswith('head_candidate_rate_'+prefix)]
        support = 0.
        if candidate and previous_ok:
            rate_key = candidate[0]; end_key = rate_key.replace('head_candidate_rate_', 'head_candidate_end_')
            if prior.get(end_key) == window.get('start_sec') and metadata.get(end_key) == raw['sim_sec']:
                support = min(float(prior[rate_key]), float(metadata[rate_key]))
        observed = max(carried, support)
        metadata[name] = observed
        for key in tuple(metadata):
            if key.startswith('head_discharge_floor_'+prefix):
                metadata[key.replace('head_discharge_floor_', 'head_legacy_unapplied_floor_')] = metadata.pop(key)
        resource['observations'][connector] = {'observed_only_floor_veh_h': observed,
            'current_pair_support_veh_h': support, 'carried_observed_support_veh_h': carried,
            'metadata_key': name, 'snapshot_sec': float(raw['sim_sec'])}
    metadata['head_resource_provisional_members_restored'] = float(len(managed))
    return metadata


def finalize(cfg):
    spec = view(cfg)
    if spec is None:
        return {}
    result = {}; caps = dict(cfg.network.movement_capacity_by_movement_veh_h)
    for connector, row in spec['resources'].items():
        if row['receiver'] not in cfg.network.urban_link_storage_veh:
            raise ValueError('Physical head resource has no finite receiving storage')
        for name, expected in row['members'].items():
            actual = cfg.network.urban_movements.get(name, {})
            if any(actual.get(k) != v for k, v in expected.items()) or actual.get('ramp'):
                raise ValueError('Final physical service member semantics changed')
        measured = spec['observations'][connector]['observed_only_floor_veh_h']
        if row['mode'] == 'route_turn':
            route = cfg.network.route_choice_corridor
            turns = route['turns']; name = next(iter(row['members'])); inherited = turns[name]['service_veh_h']
            if turns[name]['connector'] != connector or caps[name] != inherited:
                raise ValueError('Route physical service cap/turn mismatch before observation')
            selected = max(inherited, measured); caps[name] = selected
            for child in [route, *route.get('corridors', [])]:
                if name in child.get('turns', {}):
                    child['turns'][name]['service_veh_h'] = selected
        else:
            # Comparison only, not a physical seed: preserve old behavior unless
            # observation supports an increase beyond the old aggregate envelope.
            envelope = sum(caps[m] for m in row['members'])
            if measured <= envelope + EPS:
                result['head_resource_unapplied_'+connector] = measured
                continue
            selected = measured
            for name in row['members']:
                caps[name] = selected
            first = next(iter(row['members'].values()))
            spec['extra_pool_groups'][connector] = {'members': tuple(row['members']),
                'signal': first['signal'], 'phase': first['phase'], 'receiver': row['receiver'],
                'service_veh_h': selected}
        result['head_resource_final_rate_'+connector] = selected
    cfg.network.movement_capacity_by_movement_veh_h = caps
    return result


def extend_local_pool(cfg):
    spec = view(cfg)
    if spec is None or not spec['extra_pool_groups']:
        return
    pool = getattr(cfg.network, 'local_service_pool', None)
    if not pool:
        raise ValueError('Observed shared head resource lacks its local pool')
    for key, row in spec['extra_pool_groups'].items():
        if key in pool['groups'] or any(m in pool['group_of'] for m in row['members']):
            raise ValueError('Physical resource is already registered in another pool')
        pool['groups'][key] = deepcopy(row)
        pool['group_of'].update({m: key for m in row['members']})


def regular_context(cfg, control, step):
    spec = view(cfg)
    groups = spec['extra_pool_groups'] if spec else {}
    from evaluation.controllers import local_signal_service as pool
    from src.models import urban_queue_model as uqm
    limits = {}; members = {}
    for key, row in groups.items():
        for name in row['members']:
            movement = cfg.network.urban_movements[name]
            if movement['kind'] != 'boundary_out' or movement.get('ramp'):
                raise ValueError('Regular resource acquired a non-regular service path')
            fraction = uqm._phase_green_fraction(control, cfg, movement, urban_step_index=step)
            pool.register_limit(limits, key, row['service_veh_h'], cfg.simulation.T_u_h, fraction)
            members[name] = key
    return limits, {}, members


def regular_batch(cfg, intended, context):
    limits, used, members = context
    if not members:
        return intended
    from evaluation.controllers.local_signal_service import limit_batch
    return limit_batch(intended, members, limits, used, cfg.urban_follower.receiving_space_rule)


def regular_accepted(movement, vehicles, context):
    limits, used, members = context
    if movement in members:
        from evaluation.controllers.local_signal_service import accepted
        accepted(vehicles, members[movement], limits, used)
