"""Finite SC2001 outlet with frozen offline origin priors and accepted transfers.

Enabled by the explicit urban.sc2001_corridor evidence path. The same accepted
transfers update physical stock and the control-area ledger.
"""
from __future__ import annotations
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from evaluation.controllers.network_provenance import snapshot_network_sha256
from evaluation.controllers.projection_support import complete_records
from evaluation.controllers.physical_movement_routes import invalidate_topology_cache
from evaluation.controllers.control_area_objective import emit_transfer, physical_membership_from_ledger

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'vendor/NumSim-mine').is_dir())


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _length(link):
    points = [tuple(float(p.get(axis) or 0) for axis in ('x', 'y', 'z'))
              for p in link.findall('./geometry/linkPolyPts/linkPolyPoint')]
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


def _travel_segments(links, path):
    """Distances up to entry into the last connector, with position monotonicity."""
    segments = []
    for index, key in enumerate(path[:-1]):
        link = links[key]
        if link.find('fromLinkEndPt') is not None:
            if index == 0 or link.find('fromLinkEndPt').get('lane').split()[0] != path[index-1]:
                raise ValueError('Corridor connector source does not match its path')
            if link.find('toLinkEndPt').get('lane').split()[0] != path[index+1]:
                raise ValueError('Corridor connector target does not match its path')
            start, stop = 0., _length(link)
        else:
            start = 0. if index == 0 else float(links[path[index-1]].find('toLinkEndPt').get('pos'))
            following = links[path[index+1]].find('fromLinkEndPt')
            if following is None or following.get('lane').split()[0] != key:
                raise ValueError('Corridor road does not lead to its declared connector')
            stop = float(following.get('pos'))
            if stop < start:
                raise ValueError('Corridor branch is upstream of the vehicle entry position')
        segments.append({'link': key, 'start_m': start, 'stop_m': stop})
    return segments


def _remaining(branch, link='78', position=0.):
    segments = branch['travel_segments']
    first = next((index for index, row in enumerate(segments) if row['link'] == str(link)), None)
    if first is None:
        raise ValueError('Initial physical record is outside its corridor route')
    return max(0., segments[first]['stop_m'] - max(position, segments[first]['start_m'])) + sum(
        row['stop_m'] - row['start_m'] for row in segments[first+1:])


def configure(cfg, tuning, raw):
    """Configure before projection. Only frozen constants and network are read."""
    path = tuning.get('urban', {}).get('sc2001_corridor')
    if path is None:
        return {}
    if getattr(cfg.network, 'sc2001_corridor', None) is not None:
        raise ValueError('SC2001 corridor must be configured once before projection')
    document = json.loads((ROOT / path).read_text(encoding='utf-8-sig'))
    network = ROOT / document['network']['path']
    if _sha(network) != document['network']['sha256'] or snapshot_network_sha256(raw) != document['network']['sha256']:
        raise ValueError('SC2001 corridor network fingerprints disagree')
    calibration = document['calibration']
    if calibration['kind'] != 'offline_empirical_completed_cohort_prior' or calibration['runtime_reads_training_fzp'] is not False:
        raise ValueError('SC2001 corridor requires explicit offline frozen calibration')
    # Deliberately do not open calibration.fzp_path or audit_path at runtime.
    # Their hashes are training provenance; the current observation is only raw.
    outcomes = set(document['branches'])
    for origin, row in calibration['priors'].items():
        counts, shares = row['counts'], row['shares']
        denominator = row['completed_denominator']
        if set(counts) != outcomes or set(shares) != outcomes or denominator <= 0 or sum(counts.values()) != denominator:
            raise ValueError('SC2001 calibration denominator or branch support disagrees')
        if any(type(value) is not int or value < 0 for value in counts.values()):
            raise ValueError('SC2001 calibration counts must be nonnegative integers')
        if any(not math.isfinite(shares[key]) or not math.isclose(shares[key], counts[key]/denominator, abs_tol=1e-14) for key in outcomes):
            raise ValueError('SC2001 calibration shares do not match completed counts')
    tree = ET.parse(network).getroot()
    links = {node.get('no'): node for node in tree.findall('./links/link')}
    area_path = ROOT / 'diagnostics/control_area_membership.json'
    area_document = json.loads(area_path.read_text(encoding='utf-8'))
    if area_document['network']['sha256'] != document['network']['sha256']:
        raise ValueError('SC2001 area and physical network fingerprints disagree')
    inside = physical_membership_from_ledger(area_document)
    entry = float(links['10703'].find('toLinkEndPt').get('pos'))
    decision = tree.find("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='1137']")
    if float(decision.get('pos')) >= entry or float(links['10704'].find('fromLinkEndPt').get('pos')) >= entry:
        raise ValueError('SC2001 excluded route/return topology changed')
    incoming = {}
    for movement, row in document['incoming_movements'].items():
        spec = cfg.network.urban_movements.get(movement, {})
        if spec.get('receiving_link') != document['storage'] or row['origin'] not in calibration['priors']:
            raise ValueError('SC2001 accepted movement source is not in the calibrated receiver contract')
        connector = links[row['entry_connector']]
        from_link, to_link = connector.find('fromLinkEndPt'), connector.find('toLinkEndPt')
        if from_link.get('lane').split()[0] != row['physical_source'] or to_link.get('lane').split()[0] != '78':
            raise ValueError('SC2001 incoming physical turn changed')
        if [inside.get(key) for key in [row['physical_source'], row['entry_connector'], '78']] != [False, False, True]:
            raise ValueError('SC2001 incoming physical area crossing changed')
        incoming[movement] = {**row, 'pre_78_distance_m': _length(connector), 'entry_78_position_m': float(to_link.get('pos'))}
    actual_incoming = {key for key, row in cfg.network.urban_movements.items() if row.get('receiving_link') == document['storage']}
    if actual_incoming != set(incoming):
        raise ValueError('SC2001 has an uncalibrated incoming model movement')
    branches = {}
    for key, row in document['branches'].items():
        path_links = row['path']
        segments = _travel_segments(links, path_links)
        membership = [inside.get(link) for link in path_links]
        expected = [True]*len(path_links) if row['target_kind'] == 'ramp' else [True]*(len(path_links)-1) + [False]
        if membership != expected:
            raise ValueError('SC2001 route no longer has only its declared outward crossing')
        if row['target_kind'] == 'ramp' and row['target'] not in cfg.network.ramps:
            raise ValueError('SC2001 ramp receiver is absent')
        connector = links[path_links[-1]]
        branches[key] = {**row, 'travel_segments': segments, 'lanes': len(connector.findall('./lanes/lane')),
                         'source_inside': True, 'target_inside': row['target_kind'] == 'ramp'}
    jam_path = ROOT / document['jam_source']['path']
    if _sha(jam_path) != document['jam_source']['sha256']:
        raise ValueError('SC2001 jam-density source changed')
    jam = float(json.loads(jam_path.read_text(encoding='utf-8'))['jam_density_veh_km_lane'])
    length, lanes = _length(links['78']), len(links['78'].findall('./lanes/lane'))
    capacity = length/1000*lanes*jam
    if not math.isfinite(capacity) or capacity <= 0 or cfg.simulation.T_u_sec <= 0:
        raise ValueError('Invalid SC2001 capacity or time step units')
    spec = {**document, 'branches': branches, 'incoming_movements': incoming,
        'length_m': length, 'lanes': lanes, 'capacity_veh': capacity,
        'source': {'path': str(path), 'sha256': _sha(ROOT / path)},
        'area_source': {'path': str(area_path.relative_to(ROOT)), 'sha256': _sha(area_path)}}
    cfg.network.urban_link_storage_veh = {**cfg.network.urban_link_storage_veh, spec['storage']: capacity}
    cfg.network.sc2001_corridor = spec
    invalidate_topology_cache(cfg.network)
    return {'sc2001_corridor_enabled': 1., 'sc2001_corridor': spec}


def extend_area_routes(cfg):
    """After canonical area configuration: resolve only the three real entries."""
    spec = getattr(cfg.network, 'sc2001_corridor', None)
    if spec is None:
        return {}
    routes = dict(cfg.network.control_area_routes)
    for movement, row in spec['incoming_movements'].items():
        routes['movement:' + movement] = {'status': 'physical_sc2001_route', 'source_inside': False,
            'target_inside': True, 'inside_to_inside': 1., 'outside_to_inside': 1.,
            'outward_crossings_per_vehicle': 0, 'inward_crossings_per_vehicle': 1,
            'physical_path': [row['physical_source'], row['entry_connector'], '78']}
    cfg.network.control_area_routes = routes
    return {'sc2001_area_entry_routes': len(spec['incoming_movements'])}


def prepare_projection(cfg, detectors, raw):
    """Move the actual78/10703 records once; other shared-road stocks stay put."""
    spec = getattr(cfg.network, 'sc2001_corridor', None)
    if spec is None:
        return detectors, raw, {}
    by_link = defaultdict(list)
    for row in complete_records(raw):
        by_link[str(row['link_no'])].append(row)
    copied, prepared = deepcopy(detectors), deepcopy(raw)
    marker = dict(copied.get('transit_storage_projection', {}))
    metadata = {}
    for key in spec['initial_physical_links']:
        if key in copied.get('freeway_link_to_model_link', {}) or key in copied.get('ramp_link_to_queues', {}):
            raise ValueError('SC2001 initial support duplicates a ramp/freeway observation')
        rows = by_link[key]
        local = prepared['local_observation']
        if key in local.get('link_counts', {}) and local['link_counts'][key] != len(rows):
            raise ValueError('SC2001 local and full physical counts disagree')
        local.setdefault('link_counts', {})[key] = len(rows)
        local.setdefault('link_stopped_counts', {})[key] = sum(bool(row['stopped']) for row in rows)
        if rows:
            local.setdefault('link_speeds_kph', {})[key] = sum(row['speed_kph'] for row in rows)/len(rows)
        metadata[key] = {'previous_origins': detectors.get('link_to_origins', {}).get(key, []), 'vehicles': len(rows)}
        copied.setdefault('link_to_origins', {})[key] = [spec['storage']]
        copied.setdefault('link_to_movements', {}).pop(key, None)
        marker[key] = spec['storage']
    copied['transit_storage_projection'] = marker
    copied['observable_links'] = sorted(set(map(str, copied.get('observable_links', []))) | set(spec['initial_physical_links']), key=int)
    return copied, prepared, {'sc2001_initial_physical_projection': metadata}


def _occupancy(state, spec):
    return spec['capacity_veh'] - state.urban_link_storage[spec['storage']]


def _tracked(local):
    return sum(sum(bins.values()) for branches in local['bins'].values() for bins in branches.values())


def _speed(state, cfg, observed=None):
    from src.models.urban_queue_model import OBSERVED_SPEED_DELAY_CAP_RATIO
    if observed is None:
        observed = state.urban_link_speed_kph.get(cfg.network.sc2001_corridor['storage'], cfg.network.urban_avg_speed_km_h)
    value = max(float(observed), cfg.network.urban_avg_speed_km_h/OBSERVED_SPEED_DELAY_CAP_RATIO)
    if not math.isfinite(value) or value <= 0:
        raise ValueError('SC2001 travel speed must be finite and positive')
    return value


def _reserve(local, cfg, origin, amount, index, *, physical_link='78', position=0., before_78_m=0., speed):
    spec = cfg.network.sc2001_corridor
    for branch, share in spec['calibration']['priors'][origin]['shares'].items():
        if share == 0:
            continue
        distance = before_78_m + _remaining(spec['branches'][branch], physical_link, position)
        delay = max(1, math.ceil(distance/(speed/3.6)/cfg.simulation.T_u_sec))
        bins = local['bins'].setdefault(origin, {}).setdefault(branch, {})
        due = index + delay
        bins[due] = bins.get(due, 0.) + amount*share


def initialize(state, cfg, raw, detectors=None):
    spec = getattr(cfg.network, 'sc2001_corridor', None)
    if spec is None:
        return {}
    if hasattr(state, 'sc2001_corridor_state'):
        raise ValueError('SC2001 must initialize once from the physical snapshot')
    records = [row for row in complete_records(raw) if str(row['link_no']) in spec['initial_physical_links']]
    assignment = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    for key in spec['initial_physical_links']:
        if any(value > 1e-8 for stock, value in assignment.get(key, {}).items() if stock != 'storage:' + spec['storage']):
            raise ValueError('SC2001 physical records are assigned to another model stock')
    if not math.isclose(_occupancy(state, spec), len(records), abs_tol=1e-7):
        raise ValueError('SC2001 physical storage does not conserve its initial records')
    if len(records) > spec['capacity_veh'] + 1e-7:
        raise ValueError('Observed SC2001 exceeds the conservative78 storage; capacity model must be reviewed')
    index = int(round(state.time_sec/cfg.simulation.T_u_sec))
    local = {'bins': {}, 'last_step': index-1, 'received_veh': 0., 'departed_veh': 0.}
    for row in records:
        _reserve(local, cfg, 'initial_unknown_origin', 1., index, physical_link=str(row['link_no']),
                 position=float(row['position_m']), speed=_speed(state, cfg, row['speed_kph']))
    state.sc2001_corridor_state = local
    state.urban_arrival_buffer.pop(spec['storage'], None)
    state.urban_storage_release_buffer.pop(spec['storage'], None)
    return {'sc2001_initial_veh': len(records), 'sc2001_initial_origin': 'unobserved; frozen pooled NC13 prior'}


def receive_accepted(state, cfg, movement, vehicles, urban_step_index):
    """Reserve only: caller already moved actual accepted vehicles into storage."""
    spec = getattr(cfg.network, 'sc2001_corridor', None)
    if spec is None:
        return False
    row = spec['incoming_movements'].get(movement)
    if row is None:
        receiver = cfg.network.urban_movements.get(movement, {}).get('receiving_link')
        if receiver == spec['storage'] and vehicles > 0:
            raise ValueError('Positive SC2001 inflow lacks a calibrated origin')
        return False
    if not math.isfinite(vehicles) or vehicles < 0:
        raise ValueError('SC2001 accepted inflow must be finite and nonnegative')
    local = getattr(state, 'sc2001_corridor_state', None)
    if local is None or local['last_step'] != urban_step_index:
        raise ValueError('SC2001 accepted inflow requires the current explicit advanced step')
    if not math.isclose(_occupancy(state, spec), _tracked(local) + vehicles, abs_tol=1e-7):
        raise ValueError('SC2001 accepted inflow was not applied exactly once to physical storage')
    _reserve(local, cfg, row['origin'], vehicles, urban_step_index, position=row['entry_78_position_m'],
             before_78_m=row['pre_78_distance_m'], speed=_speed(state, cfg))
    local['received_veh'] += vehicles
    return True


def advance(state, control, demand, cfg, urban_step_index):
    spec = getattr(cfg.network, 'sc2001_corridor', None)
    if spec is None:
        return {}
    local = getattr(state, 'sc2001_corridor_state', None)
    if local is None or urban_step_index != local['last_step'] + 1:
        raise ValueError('SC2001 requires candidate-private state and sequential explicit steps')
    before = _occupancy(state, spec)
    if not math.isclose(before, _tracked(local), abs_tol=1e-7):
        raise ValueError('SC2001 branch cohorts and physical storage disagree')
    dt_h = cfg.simulation.T_u_h
    sat = float(cfg.network.movement_capacity_veh_h)
    if not math.isfinite(sat) or sat <= 0 or not math.isclose(dt_h*3600, cfg.simulation.T_u_sec, abs_tol=1e-10):
        raise ValueError('Invalid SC2001 lane service or time-step units')
    ready = {key: sum(amount for branches in local['bins'].values() for due, amount in branches.get(key, {}).items()
                     if due <= urban_step_index) for key in spec['branches']}
    accepted = {}
    for key, branch in spec['branches'].items():
        service = sat*branch['lanes']*dt_h
        if branch['target_kind'] == 'ramp':
            target = branch['target']
            receiving = max(0., cfg.network.ramp_queue_cap(target) - state.ramp_queue.get(target, 0.))
        else:
            cap_h = float(cfg.network.boundary_out_capacity_veh_h)
            if not math.isfinite(cap_h) or cap_h <= 0:
                raise ValueError('SC2001 external exit requires finite positive boundary service')
            receiving = cap_h*dt_h
        accepted[key] = min(ready[key], receiving, service)
    # Aggregate78 has two lanes. Preserve each destination's blockage rather
    # than reallocating its prior; proportionally share the common service.
    shared_service = sat*spec['lanes']*dt_h
    factor = min(1., shared_service/sum(accepted.values())) if sum(accepted.values()) else 1.
    accepted = {key: value*factor for key, value in accepted.items()}
    by_origin = {}
    for key, amount in accepted.items():
        if amount <= 0:
            continue
        pending = amount
        # Actual due order is FIFO; simultaneous origin cohorts share equally
        # in proportion to their existing ready stocks, never by branch count.
        dues = sorted({due for branches in local['bins'].values() for due in branches.get(key, {}) if due <= urban_step_index})
        for due in dues:
            total = sum(branches.get(key, {}).get(due, 0.) for branches in local['bins'].values())
            take = min(total, pending)
            for origin, branches in local['bins'].items():
                bins = branches.get(key, {})
                allocated = take*bins.get(due, 0.)/total if total else 0.
                if allocated:
                    bins[due] -= allocated
                    by_origin.setdefault(origin, {})[key] = by_origin.get(origin, {}).get(key, 0.) + allocated
            pending -= take
            if pending <= 1e-12:
                break
        branch = spec['branches'][key]
        state.urban_link_storage[spec['storage']] += amount
        target_stock = None
        if branch['target_kind'] == 'ramp':
            target = branch['target']; state.ramp_queue[target] = state.ramp_queue.get(target, 0.) + amount
            target_stock = 'ramp:' + target
        emit_transfer(state, cfg, 'storage:' + spec['storage'], target_stock, amount,
                      target_inside=branch['target_inside'], route_key='sc2001:' + key)
    for branches in local['bins'].values():
        for key in branches:
            branches[key] = {due: amount for due, amount in branches[key].items() if amount > 1e-12}
    departed = sum(accepted.values())
    residual = _occupancy(state, spec) - before + departed
    if abs(residual) > 1e-7 or not math.isclose(_occupancy(state, spec), _tracked(local), abs_tol=1e-7):
        raise AssertionError('SC2001 accepted-flow mass balance failed')
    local['last_step'] = urban_step_index; local['departed_veh'] += departed
    return {'sc2001_departed_veh': departed, 'sc2001_external_exit_veh': accepted['outside_125'],
            'sc2001_accepted_by_branch': accepted, 'sc2001_accepted_by_origin': by_origin,
            'sc2001_storage_veh': _occupancy(state, spec), 'sc2001_mass_residual_veh': residual}
