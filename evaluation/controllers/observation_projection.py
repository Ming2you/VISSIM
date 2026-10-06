"""Opt-in physical branch observations for existing model reservoirs.

This changes a copied detector projection, never the ownership ledger. Topology
and geometry are explicit scenario data. Each selected physical link contributes
its complete snapshot once, to one existing storage; it cannot also seed a signal
queue. Run before traffic_state_from_vissim and follower model construction.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping
import sys
import xml.etree.ElementTree as ET


class ProjectionError(ValueError):
    pass


def configure_kinematic_queue_projection(cfg, tuning, raw, detectors=None):
    """Preserve observed zeros for origins using the same kinematic queue walk."""
    setting=(tuning or {}).get('urban',{}).get('arrival',{}).get('kinematic_contract')
    if setting is None:
        if hasattr(cfg.network,'kinematic_queue_zero_links'):
            delattr(cfg.network,'kinematic_queue_zero_links')
        return {}
    from evaluation.controllers.network_provenance import snapshot_network_sha256
    root=Path(__file__).resolve().parents[2]
    doc=json.loads((root/setting).read_bytes())
    if (doc.get('schema')!='kinematic-urban-arrival/v1'
            or (tuning or {}).get('urban',{}).get('queue',{}).get('contiguous') is not True):
        raise ProjectionError('Kinematic projection requires its contiguous queue contract')
    if (hashlib.sha256((root/doc['network']['path']).read_bytes()).hexdigest()!=doc['network']['sha256']
            or snapshot_network_sha256(raw)!=doc['network']['sha256']):
        raise ProjectionError('Kinematic arrival network changed')
    records=raw.get('vehicle_records',{})
    bins=raw.get('local_observation',{}).get('queue_bins')
    if not records.get('complete') or not isinstance(bins,dict):
        raise ProjectionError('Kinematic projection requires complete current queue observations')
    links={str(spec['link']) for spec in doc['sources'].values()}
    for link in links:
        vehicles=[v for v in records['records'] if str(v['link_no'])==link]
        counts=[row for key,row in bins.items() if str(key).split('|')[0]==link]
        if (any(not isinstance(row,(tuple,list)) or len(row)!=2
                or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in row)
                or not 0<=row[1]<=row[0] for row in counts)
                or math.fsum(row[0] for row in counts)!=len(vehicles)
                or math.fsum(row[1] for row in counts)!=sum(bool(v['stopped']) for v in vehicles)):
            raise ProjectionError('Kinematic queue bins do not cover current vehicle records')
    metadata = {}
    native_path = doc.get('native_choice_evidence_path')
    if native_path is not None:
        if detectors is None:
            raise ProjectionError('Kinematic native choices require physical detector mapping')
        from evaluation.controllers.physical_movement_routes import configure_native_choice_groups
        metadata.update({'kinematic_' + key: value for key, value in configure_native_choice_groups(cfg, detectors,
            {'urban': {'movements': {'physical_route_topology': native_path}}}, state_json=raw).items()})
    cfg.network.kinematic_queue_zero_links=frozenset(links)
    return {'kinematic_observed_zero_queue_links':sorted(links), **metadata}


def initialize_kinematic_arrivals(adapter, state, cfg, tuning, raw, detectors):
    """Retain stock ownership; replace reviewed point-queue arrival schedules.

    Uses current lane/position/speed only. Lane attribution is an approximation
    for uncommitted vehicles, not a reconstruction of their future routes.
    Physical lane/branch owners must never receive a second arrival schedule.
    """
    setting = (tuning or {}).get('urban', {}).get('arrival', {}).get('kinematic_contract')
    if setting is None:
        return {}
    from src.models.urban_queue_model import approach_routing
    from evaluation.controllers.network_provenance import snapshot_network_sha256
    root = Path(__file__).resolve().parents[2]
    doc = json.loads((root / setting).read_bytes())
    if doc.get('schema') != 'kinematic-urban-arrival/v1':
        raise ProjectionError('Unknown kinematic arrival contract')
    network = (root / doc['network']['path']).read_bytes()
    if (hashlib.sha256(network).hexdigest() != doc['network']['sha256']
            or snapshot_network_sha256(raw) != doc['network']['sha256']):
        raise ProjectionError('Kinematic arrival network changed')
    links = {x.get('no'): x for x in ET.fromstring(network).findall('./links/link')}
    records = raw['vehicle_records']
    if not records.get('complete') or not hasattr(cfg.network, 'physical_ramp_branches'):
        raise ProjectionError('Kinematic arrival needs complete records and installed tag consumer')
    floor = float(doc['speed_floor_kph'])
    if not math.isfinite(floor) or floor <= 0:
        raise ProjectionError('Invalid declared kinematic speed floor')
    summary = state.local_observation_summary
    provenance = summary['projection_diagnostics']['physical_stock_assignment_by_link']
    lane_queues = adapter._contiguous_stopline_queue(raw, per_lane=True)
    dt = cfg.simulation.T_u_sec
    now = int(round(state.time_sec / dt))
    routing = approach_routing(cfg)
    receipt = {}
    native_groups, current_routes = {}, None
    if doc.get('native_choice_evidence_path') is not None:
        from evaluation.controllers.physical_movement_routes import load_evidence
        from evaluation.controllers.vehicle_routes import complete_vehicle_routes
        native_doc, native_routes, _ = load_evidence(doc['native_choice_evidence_path'])
        if native_doc['network'] != doc['network']:
            raise ProjectionError('Kinematic routing and geometry evidence differ')
        native_groups = native_doc.get('native_choice_groups', {})
        current_routes = complete_vehicle_routes(raw, required=True)
    for source, spec in doc['sources'].items():
        link = str(spec['link'])
        support = dict(provenance.get(link, {}))
        movements = spec['movements']
        if (detectors['link_to_origins'].get(link) != [source]
                or set(movements) != set(dict(routing.get(source, [])))
                or set(support) - {'storage:' + source, *('movement:' + m for m in movements)}
                or source in getattr(state, 'gate_initial_route_tags', {})
                or source in getattr(cfg.network, 'physical_gate_travel', {})):
            raise ProjectionError('Kinematic source has another physical owner or routing')
        geometry = {}
        for m, row in movements.items():
            if cfg.network.urban_movements[m] != row['expected_spec']:
                raise ProjectionError('Kinematic movement catalog changed')
            connector = links[str(row['connector'])]
            start = connector.find('fromLinkEndPt')
            if start is None or start.get('lane').split()[0] != link:
                raise ProjectionError('Kinematic movement does not leave its physical link')
            first = int(start.get('lane').split()[1])
            geometry[m] = (float(start.get('pos')), set(range(first, first + len(connector.findall('./lanes/lane')))))
        group_key = spec.get('native_choice_group')
        native_group = native_groups.get(group_key) if group_key is not None else None
        if group_key is not None:
            if (native_group is None or native_group['origin'] != source
                    or native_group['stopline'] != link
                    or set(native_group['route_to_movement'].values()) != set(movements)):
                raise ProjectionError('Kinematic current-route group differs from this source')
            for rid, m in native_group['route_to_movement'].items():
                if native_routes[rid]['path'][:2] != [link, str(movements[m]['connector'])]:
                    raise ProjectionError('Kinematic current-route connector changed')
            decision_position = float(native_routes[next(iter(native_group['route_to_movement']))]['decision']['pos'])
        vehicles = [v for v in records['records'] if str(v['link_no']) == link]
        if abs(math.fsum(support.values()) - len(vehicles)) > 1e-7:
            raise ProjectionError('Kinematic source stock differs from current records')
        ready = set()
        for lane in {v['lane_no'] for v in vehicles}:
            n = float(lane_queues.get((link, str(lane)), 0.))
            front = sorted((v for v in vehicles if v['lane_no'] == lane), key=lambda v: -v['position_m'])[:int(n)]
            if n != int(n) or len(front) != n or any(not v['stopped'] for v in front):
                raise ProjectionError('Contiguous queue cannot be matched to current vehicle records')
            ready.update(v['veh_no'] for v in front)
        old_q = math.fsum(support.get('movement:' + m, 0.) for m in movements)
        if abs(len(ready) - old_q) > 1e-7:
            raise ProjectionError('Kinematic queue definition differs from original physical queue')
        residual = [v for v in vehicles if v['veh_no'] not in ready]
        if abs(len(residual) - support.get('storage:' + source, 0.)) > 1e-7:
            raise ProjectionError('Kinematic residual stock differs')
        arrival = dict(state.urban_arrival_buffer.get(source, {}))
        if arrival != state.urban_storage_release_buffer.get(source, {}):
            raise ProjectionError('Kinematic source requires paired arrival/release reservations')
        for stopped, tau in ((False, adapter._ARRIVAL_TAU_MOVING_SEC), (True, adapter._ARRIVAL_TAU_STOPPED_SEC)):
            n = sum(bool(v['stopped']) == stopped for v in residual)
            step = now + max(1, int(round(tau / dt)))
            remaining = arrival.get(step, 0.) - n
            if remaining < -1e-7:
                raise ProjectionError('Original residual cohort is missing from its reservation')
            if remaining > 0:
                arrival[step] = remaining
            else:
                arrival.pop(step, None)
        mean_speed = math.fsum(v['speed_kph'] for v in vehicles) / len(vehicles) if vehicles else floor
        queues = dict.fromkeys(movements, 0.)
        tags = {}
        known_count, prechoice_count = 0, 0
        for v in vehicles:
            choices = {m: beta for m, beta in routing[source] if v['lane_no'] in geometry[m][1]
                       and v['position_m'] <= geometry[m][0] + 1e-6}
            if native_group is not None:
                observed = current_routes[v['veh_no']]
                rid = f"{observed['route_decision_no']}:{observed['route_no']}"
                selected = native_group['route_to_movement'].get(rid)
                if observed['route_decision_type'] == 'STATIC' and selected is not None:
                    # Current lane need not be the destination lane yet. Retain
                    # intent; do not resample a known destination from beta.
                    if v['position_m'] > geometry[selected][0] + 1e-6:
                        raise ProjectionError('Known destination is behind current vehicle position')
                    choices = {selected: 1.}
                    known_count += 1
                elif v['position_m'] < decision_position:
                    choices = dict(routing[source])
                    prechoice_count += 1
                else:
                    raise ProjectionError('Missing current destination after native decision; cannot redraw')
            total = math.fsum(choices.values())
            if total <= 0:
                raise ProjectionError('Current lane/position has no supported movement')
            for m, beta in choices.items():
                amount = beta / total
                if v['veh_no'] in ready:
                    queues[m] += amount
                else:
                    eta = (geometry[m][0] - v['position_m']) / (max(v['speed_kph'], mean_speed, floor) / 3.6)
                    step = now + max(1, math.ceil(eta / dt))
                    row = tags.setdefault(step, {})
                    row[m] = row.get(m, 0.) + amount
                    arrival[step] = arrival.get(step, 0.) + amount
        for m, n in queues.items():
            state.urban_movement_queue[m] += n - support.get('movement:' + m, 0.)
            support['movement:' + m] = n
        if abs(math.fsum(queues.values()) + math.fsum(sum(x.values()) for x in tags.values()) - len(vehicles)) > 1e-7:
            raise ProjectionError('Kinematic projection does not conserve vehicles')
        provenance[link] = support
        state.urban_arrival_buffer[source] = dict(arrival)
        state.urban_storage_release_buffer[source] = dict(arrival)
        if not hasattr(state, 'gate_initial_route_tags'):
            state.gate_initial_route_tags = {}
        state.gate_initial_route_tags[source] = tags
        moving = [v['speed_kph'] for v in vehicles if not v['stopped']]
        gate_speed = max(math.fsum(moving) / len(moving), floor) if moving else floor
        gate_delay = min(pos for pos, lanes in geometry.values()) / (gate_speed / 3.6)
        if not hasattr(cfg.network, 'urban_boundary_travel_time_sec'):
            cfg.network.urban_boundary_travel_time_sec = {}
        cfg.network.urban_boundary_travel_time_sec[source] = gate_delay
        receipt[source] = dict(link=link, queue_veh=queues, residual_veh=len(residual),
                               last_arrival_delay_sec=(max(tags)-now)*dt if tags else 0.,
                               gate_travel_sec=gate_delay, future_traffic_inputs=False)
        if native_group is not None:
            receipt[source].update(known_destination_veh=known_count,
                                   before_choice_veh=prechoice_count, native_choice_group=group_key)
    return {'kinematic_arrivals': receipt}


def record_projection_assignment(provenance, physical_link, stock_key, vehicles):
    """Record the actual assignment at its mutation site, after any clipping."""
    count = _count(vehicles, stock_key)
    if count:
        row = provenance.setdefault(str(physical_link), {})
        row[str(stock_key)] = row.get(str(stock_key), 0.0) + count


def audit_projection_provenance(provenance, storage, movement, ramp):
    """Verify assignment provenance covers every urban/ramp summary stock."""
    expected = {**{"storage:" + k: v for k, v in storage.items()},
                **{"movement:" + k: v for k, v in movement.items()},
                **{"ramp:" + k: v for k, v in ramp.items()}}
    assigned = defaultdict(float)
    for row in provenance.values():
        for key, value in row.items():
            assigned[key] += float(value)
    residual = {key: assigned.get(key, 0.0) - float(expected.get(key, 0.0))
                for key in assigned.keys() | expected.keys()
                if abs(assigned.get(key, 0.0) - float(expected.get(key, 0.0))) > 1e-8}
    if residual:
        raise ProjectionError(f"physical assignment provenance does not cover projected stocks: {residual}")
    return {"physical_stock_assignment_veh": sum(assigned.values()),
            "physical_stock_assignment_by_link": provenance}


def _count(value: Any, label: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ProjectionError(f"{label}: expected finite nonnegative count, got {value!r}")
    return number


def configure_head_queue_lanes(cfg, tuning, state_json):
    """Validate optional connector-lane evidence before projecting any queue."""
    section = (tuning or {}).get('urban', {}).get('queue', {})
    source = section.get('head_lane_contract')
    if source is None:
        if hasattr(cfg.network, 'head_queue_movement_lanes'):
            delattr(cfg.network, 'head_queue_movement_lanes')
        if hasattr(cfg.network, 'head_queue_upstream_storage'):
            delattr(cfg.network, 'head_queue_upstream_storage')
        return {}
    if section.get('attribution') != 'head_phase':
        raise ProjectionError('Connector-lane queue support requires head_phase attribution')
    from evaluation.controllers.network_provenance import snapshot_network_sha256
    root = Path(__file__).resolve().parents[2]
    data = (root/source).read_bytes()
    document = json.loads(data)
    if document.get('schema') != 'head-queue-lane-support/v1':
        raise ProjectionError('Unsupported head queue lane contract')
    def pinned(pin):
        raw = (root/pin['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != pin['sha256']:
            raise ProjectionError('Head queue lane evidence changed')
        return raw
    network = pinned(document['network'])
    if snapshot_network_sha256(state_json) != document['network']['sha256']:
        raise ProjectionError('Head queue lane network differs from observation')
    authority = json.loads(pinned(document['authority']))['network']
    tree = ET.fromstring(network)
    links = {x.get('no'):x for x in tree.findall('./links/link')}
    support = {}
    for name, row in document['movements'].items():
        actual = cfg.network.urban_movements.get(name, {})
        expected = row['expected_spec']
        if any(actual.get(k) != v or authority['urban_movements'][name].get(k) != v
               for k,v in expected.items()):
            raise ProjectionError('Head queue movement source changed: '+name)
        turns = authority['control_area_routes']['movement:'+name]['physical_turns']
        proven = [t for t in turns if t.get('from_link') == row['from_link']
                  and t.get('source_evidence', {}).get('canonical_approach_leg')]
        if (len(proven) != 1 or proven[0].get('connector') != row['connector']
                or proven[0].get('to_link') != row['to_link']):
            raise ProjectionError('Head queue movement lacks its physical route')
        connector = links[row['connector']]
        start, end = connector.find('fromLinkEndPt'), connector.find('toLinkEndPt')
        first = int(start.get('lane').split()[1])
        lanes = list(range(first, first+len(connector.findall('./lanes/lane'))))
        if (start.get('lane').split()[0] != row['from_link']
                or end.get('lane').split()[0] != row['to_link'] or lanes != row['lanes']):
            raise ProjectionError('Head queue connector lanes changed: '+name)
        support.setdefault(row['from_link'], {})[name] = lanes
    if not support:
        raise ProjectionError('Empty head queue lane support')
    upstream = {}
    for link, row in document.get('upstream_stoplines', {}).items():
        approach, storage = row['downstream_approach'], row['storage']
        if (link not in links or links[link].find('fromLinkEndPt') is not None
                or link in support or approach not in support
                or storage not in cfg.network.urban_link_storage_veh):
            raise ProjectionError('Invalid upstream queue support: '+link)
        groups = sorted({h.get('sg') for h in tree.findall('./signalHeads/signalHead')
                         if h.get('lane').split()[0] == link})
        owners = {'SC'+g.split()[0] for g in groups}
        targets = [cfg.network.urban_movements[n] for n in support[approach]]
        if (not groups or groups != row['signal_groups']
                or any(s['origin'] != storage or s['signal'] in owners for s in targets)):
            raise ProjectionError('Upstream head is not separate from the canonical queue: '+link)
        native = {c.get('no'):c for c in tree.findall('./signalControllers/signalController')}
        if any(c not in native or native[c].get('type') != 'FIXEDTIME'
               or native[c].get('active') != 'true' for c in {g.split()[0] for g in groups}):
            raise ProjectionError('Upstream queue lacks its active native fixed signal: '+link)
        # This is readiness only. Do not grant a deterministic path, route
        # destination, signal service or a new inventory to the upstream road.
        upstream[link] = storage
    cfg.network.head_queue_movement_lanes = support
    cfg.network.head_queue_upstream_storage = upstream
    return {'head_queue_lane_contract_sha256': hashlib.sha256(data).hexdigest(),
            'head_queue_lane_links': len(support), 'head_queue_lane_movements': len(document['movements']),
            'head_queue_upstream_links': len(upstream)}


def head_phase_queue_weights(link, count, entries, specs, lane_counts, head_groups, *, movement_lanes=None):
    """Keep observed queue mass on movements served by its unique lane head.

    Unknown heads retain the existing weights. Within a shared phase this does
    not invent destination information: the existing relative weights remain.
    Returns one weight per input entry, including duplicate movement aliases.
    """
    count = _count(count, 'queue count')
    lanes = {str(lane): _count(n, 'lane queue') for (road, lane), n in lane_counts.items()
             if str(road) == str(link) and n > 0}
    if not math.isclose(sum(lanes.values()), count, rel_tol=0, abs_tol=1e-8):
        raise ProjectionError(f'{link}: lane queues differ from projected queue mass')
    weights = [_count(weight, 'movement weight') for _, weight in entries]
    if count and (not entries or sum(weights) <= 0):
        raise ProjectionError(f'{link}: queue lacks positive existing movement weights')
    phases = defaultdict(set)
    for (road, phase), heads in head_groups.items():
        if str(road) == str(link):
            for head in heads:
                phases[str(head['lane'])].add(f"SC{head['sc']}_{phase}")
    assigned = [0.] * len(entries)
    supported = fallback = lane_supported = 0.
    for lane, n in lanes.items():
        known = phases.get(lane, set())
        eligible = [i for i, (movement, _) in enumerate(entries)
                    if len(known) == 1 and specs[movement].get('phase') in known and weights[i] > 0]
        if eligible and movement_lanes is not None:
            if any(movement not in movement_lanes for movement, _ in entries):
                raise ProjectionError(f'{link}: incomplete connector-lane movement support')
            eligible = [i for i in eligible if int(lane) in movement_lanes[entries[i][0]]]
            if not eligible:
                raise ProjectionError(f'{link}/{lane}: head phase and connector lanes disagree')
            lane_supported += n
        if eligible:
            supported += n
        else:
            eligible = list(range(len(entries)))
            fallback += n
        total = sum(weights[i] for i in eligible)
        for i in eligible:
            assigned[i] += n * (weights[i] / total)
    if not math.isclose(sum(assigned), count, rel_tol=0, abs_tol=1e-8):
        raise ProjectionError(f'{link}: head-phase attribution changed queue mass')
    return assigned, {'queue_veh': count, 'head_phase_supported_veh': supported,
                      'legacy_fallback_veh': fallback, 'lane_queue_veh': lanes,
                      'connector_lane_supported_veh': lane_supported}


def validate_record_storage_partition(link, row, count, stopped, speed, origins, capacities):
    """Consume a previously proven full-link partition without making new IDs."""
    if not isinstance(row, Mapping) or not row or set(row) != set(origins):
        raise ProjectionError(f'{link}: physical record partition origins differ')
    total = total_stopped = moment = 0.0
    checked = {}
    for storage, values in row.items():
        if storage not in capacities or not isinstance(values, Mapping):
            raise ProjectionError(f'{link}: invalid partition storage {storage}')
        n = _count(values['count'], 'record count')
        stopped_n = _count(values['stopped_count'], 'stopped record count')
        speed_sum = _count(values['speed_sum_kph'], 'record speed sum')
        if stopped_n > n or (n == 0 and speed_sum != 0):
            raise ProjectionError(f'{link}: inconsistent physical record moments')
        total += n; total_stopped += stopped_n; moment += speed_sum
        checked[storage] = (n, stopped_n, speed_sum)
    if not math.isclose(total, count, rel_tol=0, abs_tol=1e-8):
        raise ProjectionError(f'{link}: physical record partition count differs')
    if not math.isclose(total_stopped, stopped, rel_tol=0, abs_tol=1e-8):
        raise ProjectionError(f'{link}: physical record partition stopped count differs')
    # The independent VBS aggregate is rounded, individual records are doubles.
    if count and not math.isclose(moment, float(speed)*count, rel_tol=0, abs_tol=max(1e-5, count*1e-5)):
        raise ProjectionError(f'{link}: physical record partition speed moment differs')
    return checked


def install_physical_branch_projection(
    cfg, tuning: Mapping[str, Any], detector_mapping: Mapping[str, Any],
    *, link_counts: Mapping[str, float],
) -> tuple[Mapping[str, Any], dict[str, Any]]:
    """Install a one-link/one-storage table under one explicit configuration key.

    Absent/disabled leaves both cfg and detector mapping untouched. The optional
    capacity table is derived offline from pinned physical geometry. A scenario
    may explicitly request ``observed_lower_bound``: a measured stock is a lower
    bound on real capacity, so preserve it and report a geometry underestimate
    instead of discarding vehicles at projection time.
    """
    section = tuning.get("observation", {}).get("physical_branch_projection", {})
    if not section or section is False:
        return detector_mapping, {"physical_branch_projection_enabled": 0.0}
    if not isinstance(section, Mapping) or type(section.get("enabled", False)) is not bool:
        raise ProjectionError("physical_branch_projection must be an object with boolean enabled")
    if not section.get("enabled", False):
        return detector_mapping, {"physical_branch_projection_enabled": 0.0}
    table = {str(k): str(v) for k, v in section.get("link_to_storage", {}).items()}
    if not table:
        raise ProjectionError("enabled physical_branch_projection requires link_to_storage")
    net = cfg.network
    if not getattr(net, "offramp_direct_share_by_offramp", None):
        raise ProjectionError("physical branch projection requires the installed direct-landing split")
    if getattr(net, "landing_storage_spec", None):
        raise ProjectionError("physical branch projection and aggregate landing storage cannot both seed stock")
    counts = {str(k): _count(v, str(k)) for k, v in link_counts.items()}
    capacities = dict(net.urban_link_storage_veh)
    unknown = sorted(set(table.values()) - capacities.keys())
    if unknown:
        raise ProjectionError(f"unknown target storage: {unknown}")
    reserved = set(map(str, detector_mapping.get("freeway_link_to_model_link", {})))
    reserved.update(map(str, detector_mapping.get("ramp_link_to_queues", {})))
    reserved.update(map(str, detector_mapping.get("link_partition", {}).get("monitor_only_exit_links", [])))
    if reserved.intersection(table):
        raise ProjectionError(f"branch observation overlaps freeway/ramp/excluded channel: {sorted(reserved.intersection(table))}")
    original_origins = detector_mapping.get("link_to_origins", {})
    if set(table) - set(original_origins):
        raise ProjectionError(f"branch physical links absent from detector mapping: {sorted(set(table) - set(original_origins))}")

    target_counts: dict[str, float] = defaultdict(float)
    for link, storage in table.items():
        target_counts[storage] += counts.get(link, 0.0)
    # An exclusive branch reservoir cannot also accept an unaccounted old source.
    for link, origins in original_origins.items():
        if str(link) in table or counts.get(str(link), 0.0) == 0:
            continue
        resolved = {str(net.off_ramp_storage_link.get(str(o), str(o))) for o in origins}
        if resolved.intersection(target_counts):
            raise ProjectionError(f"positive unlisted physical source {link} shares a dedicated branch target")
    declared_caps = section.get("storage_capacity_veh", {})
    if set(declared_caps) - set(target_counts):
        raise ProjectionError("capacity overrides must belong to the dedicated branch targets")
    policy = section.get("capacity_policy", "strict")
    if policy not in {"strict", "observed_lower_bound"}:
        raise ProjectionError(f"unknown capacity_policy: {policy}")
    capacity_rows = {}
    for storage, observed in target_counts.items():
        prior = float(capacities[storage])
        geometric = _count(declared_caps.get(storage, prior), storage)
        if geometric <= 0:
            raise ProjectionError(f"positive capacity required for {storage}")
        if policy == "strict" and observed > geometric + 1e-8:
            raise ProjectionError(f"{storage}: observed {observed} exceeds capacity {geometric}")
        effective = max(geometric, observed) if policy == "observed_lower_bound" else geometric
        capacities[storage] = effective
        capacity_rows[storage] = {
            "prior_veh": prior, "declared_veh": geometric, "effective_veh": effective,
            "observed_floor_added_veh": max(0.0, observed - geometric),
        }
    copied = deepcopy(detector_mapping)
    previous = {}
    for link, storage in table.items():
        previous[link] = list(copied["link_to_origins"][link])
        copied["link_to_origins"][link] = [storage]
        copied.get("link_to_movements", {}).pop(link, None)
    metadata = {
        "physical_branch_projection_enabled": 1.0,
        "physical_branch_projection_link_count": float(len(table)),
        "physical_branch_projection_observed_veh": sum(target_counts.values()),
        "physical_branch_projection_target_veh": dict(target_counts),
        "physical_branch_projection_capacity": capacity_rows,
        "physical_branch_projection_previous_origins": previous,
        "physical_branch_projection_source": section.get("source", "explicit scenario mapping"),
    }
    copied["physical_storage_projection"] = {"link_to_storage": table, "metadata": metadata}
    # Mutate cfg only after validating the complete proposal.
    net.urban_link_storage_veh = capacities
    return copied, metadata


def audit_physical_branch_projection(
    detector_mapping: Mapping[str, Any], link_counts: Mapping[str, float],
    storage_occupancy: Mapping[str, float],
) -> dict[str, Any]:
    """Assert the measured branch stock reached its target once, without clipping."""
    section = detector_mapping.get("physical_storage_projection", {})
    if not section:
        return {}
    targets: dict[str, float] = defaultdict(float)
    provenance = {}
    for link, storage in section["link_to_storage"].items():
        count = _count(link_counts.get(link, 0.0), link)
        targets[storage] += count
        provenance[link] = {"storage": storage, "observed_veh": count, "assigned_veh": count}
    residual = {storage: float(storage_occupancy.get(storage, 0.0)) - count for storage, count in targets.items()}
    if any(abs(value) > 1e-8 for value in residual.values()):
        raise ProjectionError(f"physical branch projection failed count conservation: {residual}")
    return {
        "physical_branch_projection_assigned_veh": sum(targets.values()),
        "physical_branch_projection_residual_veh": sum(residual.values()),
        "physical_branch_projection_provenance": provenance,
    }


def install_direct_branch_capacity_runtime(cfg) -> dict[str, float]:
    """Limit freeway departure by both destinations before removing vehicles.

    The global scheduler splits accepted group flow after the freeway step. Its
    rejection counter cannot restore a vehicle already removed from freeway
    stock. Use the same fixed-share capacity helper as the local candidate model.
    ``cfg.network.local_landing_state`` is installed by link_predictor.configure;
    call this after configure in main and again in spawned price workers.
    """
    if not bool(getattr(cfg.network, "local_landing_state", False)):
        return {"direct_branch_receiving_enabled": 0.0}
    from src.models import urban_queue_model as queue_model
    from evaluation.controllers.link_predictor import branch_capacity

    original = getattr(queue_model, "_direct_branch_capacity_original", None)
    if original is None:
        original = queue_model.off_ramp_capacity_by_freeway_link
        queue_model._direct_branch_capacity_original = original

    def direct_branch_capacity(state, cfg_arg, interval_h=None):
        result = original(state, cfg_arg, interval_h=interval_h)
        net = cfg_arg.network
        if not bool(getattr(net, "local_landing_state", False)):
            return result
        duration = cfg_arg.simulation.T_c_h if interval_h is None else interval_h
        shares = getattr(net, "offramp_direct_share_by_offramp", {}) or {}
        tails = getattr(net, "offramp_direct_tail_by_offramp", {}) or {}
        by_freeway: dict[str, float] = defaultdict(float)
        for off_ramp in net.off_ramps:
            share = float(shares.get(off_ramp, 0.0))
            if not math.isfinite(share) or not 0.0 <= share <= 1.0:
                raise ProjectionError(f"{off_ramp}: direct share must be finite in [0, 1]")
            if share > 0.0:
                tail = tails.get(off_ramp)
                if tail not in net.urban_link_storage_veh:
                    raise ProjectionError(f"{off_ramp}: direct branch requires existing target storage")
                signal = net.off_ramp_storage_link[off_ramp]
                signal_available = queue_model._effective_available_space(state, cfg_arg, signal)
                direct_available = queue_model._effective_available_space(state, cfg_arg, tail)
                result[off_ramp] = branch_capacity(signal_available, direct_available, share, duration)
        # The scheduler lands groups sequentially, but their simultaneous caps
        # must not each reserve the complete space of a shared direct receiver.
        for target in {tails[o] for o in net.off_ramps if float(shares.get(o, 0.0)) > 0.0}:
            groups = [o for o in net.off_ramps if float(shares.get(o, 0.0)) > 0.0 and tails[o] == target]
            needed = sum(result[o] * float(shares[o]) * duration for o in groups)
            available = queue_model._effective_available_space(state, cfg_arg, target)
            scale = min(1.0, available / needed) if needed > 0.0 else 1.0
            for off_ramp in groups:
                result[off_ramp] *= scale
        for off_ramp in net.off_ramps:
            by_freeway[net.off_ramp_from_freeway[off_ramp]] += result[off_ramp]
        result.update(by_freeway)
        return result

    queue_model.off_ramp_capacity_by_freeway_link = direct_branch_capacity
    rebound = 0
    for module in list(sys.modules.values()):
        if module is None or module is queue_model:
            continue
        current = getattr(module, "off_ramp_capacity_by_freeway_link", None)
        if current is original or getattr(current, "__name__", "") == "direct_branch_capacity":
            setattr(module, "off_ramp_capacity_by_freeway_link", direct_branch_capacity)
            rebound += 1
    return {"direct_branch_receiving_enabled": 1.0, "direct_branch_receiving_aliases": float(rebound)}
