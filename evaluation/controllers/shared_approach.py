"""Explicit finite shared-input storage with candidate-private branch travel.

The reviewed link69 is inside Omega and has independent native input1101. Native
relative flows are conditional priors, not observed vehicle routes. Vehicles stay
in shared storage until their branch travel is complete and its actual receiver
accepts them; a full receiver never deletes or redirects a blocked cohort.
"""
from __future__ import annotations
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from evaluation.controllers.network_provenance import snapshot_network_sha256
from evaluation.controllers.projection_support import complete_records
from evaluation.controllers.physical_movement_routes import invalidate_topology_cache
from evaluation.controllers.control_area_objective import emit_input, emit_transfer

ROOT = Path(__file__).resolve().parents[2]


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _length(link):
    pts = [(float(p.get('x')), float(p.get('y')), float(p.get('z') or 0))
           for p in link.findall('./geometry/linkPolyPts/linkPolyPoint')]
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def configure(cfg, tuning, raw):
    section = tuning.get('urban', {})
    observed_initial = section.get('shared_approach_observed_initial_routes', False)
    if type(observed_initial) is not bool:
        raise ValueError('shared_approach_observed_initial_routes must be boolean')
    path = section.get('shared_approach')
    if path is None:
        if observed_initial:
            raise ValueError('Observed initial routes require a pinned shared_approach')
        return {}
    document = json.loads((ROOT / path).read_text(encoding='utf-8-sig'))
    network = ROOT / document['network']['path']
    if _sha(network) != document['network']['sha256'] or snapshot_network_sha256(raw) != document['network']['sha256']:
        raise ValueError('Shared approach network fingerprints disagree')
    tree = ET.parse(network).getroot()
    links = {x.get('no'): x for x in tree.findall('./links/link')}
    physical_link, storage = document['physical_link'], document['storage']
    if storage in cfg.network.urban_link_storage_veh:
        raise ValueError('Shared approach must be configured once before projection')
    gate_path = ROOT / document['gate_map']['path']
    if _sha(gate_path) != document['gate_map']['sha256']:
        raise ValueError('Shared approach gate map changed')
    with gate_path.open(encoding='utf-8-sig') as handle:
        gate_rows = list(csv.DictReader(line for line in handle if not line.startswith('#')))
    native_input = tree.find(f"./vehicleInputs/vehicleInput[@no='{document['native_input']}']")
    gate = next(x for x in gate_rows if x['no'] == document['native_input'])
    if native_input is None or native_input.get('link') != physical_link or gate['status'] != 'shared_stem_unmapped':
        raise ValueError('Shared approach native input is no longer the reviewed unmapped stem')
    if gate['gate'] in cfg.network.boundary_in_links:
        raise ValueError('Shared native input already has another model boundary gate')
    # The runner's profile applies role then input-specific overrides. These are
    # declared experiment inputs, not future measured traffic.
    provenance = raw.get('run_provenance') or {}
    manifest = json.loads(Path(provenance['manifest_path']).read_text(encoding='utf-8-sig'))
    multiplier = 1.0
    profile_path = manifest.get('demand_profile')
    profile_evidence = None
    if profile_path:
        profile_path = Path(profile_path)
        expected_profile = document.get('demand_profile')
        if not expected_profile or _sha(profile_path) != expected_profile['sha256']:
            raise ValueError('Shared native demand profile differs from its pinned scenario source')
        with profile_path.open(encoding='utf-8-sig') as handle:
            profile = {row['role'].strip().lower(): float(row['multiplier']) for row in csv.DictReader(handle)}
        multiplier = profile.get('no:' + document['native_input'], profile.get(gate['role'].lower(), profile.get('__default__', 1.0)))
        profile_evidence = {'path': str(profile_path), 'sha256': _sha(profile_path)}
    scale = float(manifest['demand_scale']) * multiplier
    if not math.isfinite(scale) or scale < 0:
        raise ValueError('Invalid shared native input scale')
    schedule = []
    for row in native_input.findall('./timeIntVehVols/timeIntervalVehVolume'):
        parts = row.get('timeInt').split()
        if parts[0] != '1' or row.get('cont') != 'false':
            raise ValueError('Unsupported shared native demand interval semantics')
        schedule.append({'start_sec': float(parts[1]) / 1000, 'rate_veh_h': float(row.get('volume')) * scale,
                         'raw_rate_veh_h': float(row.get('volume')), 'volume_type': row.get('volType')})
    schedule.sort(key=lambda x: x['start_sec'])
    if not schedule or schedule[0]['start_sec'] != 0:
        raise ValueError('Native input schedule lacks its initial interval')
    decision = tree.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{document['native_decision']}']")
    if decision is None or decision.get('link') != physical_link or decision.get('allVehTypes') != 'true' or decision.get('routeChoiceMeth') != 'STATIC':
        raise ValueError('Shared approach requires the reviewed all-type static decision')
    if observed_initial:
        decision_position = float(decision.get('pos'))
        route_ids = [route.get('no') for route in decision.findall('./vehRoutSta/vehicleRouteStatic')]
        if (physical_link != '69' or document['native_decision'] != '1134'
                or set(document['branches']) != {'1', '2', '3', '4'}
                or len(route_ids) != 4 or set(route_ids) != set(document['branches'])
                or not math.isfinite(decision_position) or decision_position < 0):
            raise ValueError('Observed initial routes require the reviewed link69/1134 four-branch decision')
    starts = [float(x.get('start')) for x in tree.findall(".//timeIntervalSet[@no='VEHICLEROUTESTATIC']/timeInts/timeInterval")]
    if starts != [0.0]:
        raise ValueError('Shared approach route weights changed intervals')
    branches = {}
    for route in decision.findall('./vehRoutSta/vehicleRouteStatic'):
        key = route.get('no')
        choice = document['branches'][key]
        path_links = [physical_link] + [x.get('key') for x in route.findall('./linkSeq/intObjectRef')] + [route.get('destLink')]
        connector = path_links[1]
        origin = links[connector].find('fromLinkEndPt')
        if connector != choice['connector'] or origin.get('lane').split()[0] != physical_link:
            raise ValueError('Shared approach branch source changed')
        if observed_initial:
            from evaluation.controllers.route_choice_corridor import _validate_path
            branch_position = float(origin.get('pos'))
            if (not math.isfinite(branch_position)
                    or not decision_position <= branch_position <= _length(links[physical_link])
                    or path_links.count(physical_link) != 1):
                raise ValueError('Observed initial route has an invalid decision-to-branch interval')
            _validate_path(path_links, links)
        raw_weight = (route.get('relFlow') or '').strip()
        match = re.fullmatch(r'2 0:([0-9]+(?:\.[0-9]+)?)', raw_weight) if raw_weight else None
        weight = 1.0 if not raw_weight else float(match.group(1)) if match else None
        if weight is None or weight <= 0:
            raise ValueError('Invalid shared branch static relative flow')
        if choice['target_kind'] == 'ramp':
            if choice['target'] not in cfg.network.ramps:
                raise ValueError('Unknown shared ramp receiver')
        elif choice['target'] not in cfg.network.urban_link_storage_veh:
            raise ValueError('Unknown shared urban receiver')
        receiving_link = choice['physical_receiver_start']
        if receiving_link not in path_links:
            raise ValueError('Shared receiving point is not on its native route')
        # Path distance after leaving69 but before entering the existing stock.
        distance = 0.0
        for index in range(1, path_links.index(receiving_link)):
            link_id = path_links[index]
            x = links[link_id]
            if x.find('fromLinkEndPt') is not None:
                distance += _length(x)
            else:
                previous = links[path_links[index - 1]].find('toLinkEndPt')
                following = links[path_links[index + 1]].find('fromLinkEndPt')
                distance += max(0.0, float(following.get('pos')) - float(previous.get('pos')))
        branches[key] = {**choice, 'weight': weight, 'relFlow_raw': raw_weight, 'path': path_links,
            'branch_position_m': float(origin.get('pos')), 'pre_receiver_distance_m': distance,
            'lanes': len(links[connector].findall('./lanes/lane'))}
    total_weight = sum(row['weight'] for row in branches.values())
    for row in branches.values():
        row['share'] = row['weight'] / total_weight
    jam_path = ROOT / document['jam_source']['path']
    if _sha(jam_path) != document['jam_source']['sha256']:
        raise ValueError('Shared approach jam-density source changed')
    jam = float(json.loads(jam_path.read_text(encoding='utf-8'))['jam_density_veh_km_lane'])
    length = _length(links[physical_link])
    lanes = len(links[physical_link].findall('./lanes/lane'))
    capacity = length / 1000 * lanes * jam
    spec = {**document, 'branches': branches, 'capacity_veh': capacity, 'length_m': length,
            'schedule': schedule, 'demand_profile': profile_evidence, 'demand_scale': scale,
            'source': {'path': str(path), 'sha256': _sha(ROOT / path)}}
    if observed_initial:
        spec.update(observed_initial_routes=True, decision_position_m=decision_position)
    cfg.network.urban_link_storage_veh = {**cfg.network.urban_link_storage_veh, storage: capacity}
    cfg.network.shared_approach = spec
    invalidate_topology_cache(cfg.network)
    return {'shared_approach_enabled': 1.0, 'shared_approach': spec}


def _speed(state, cfg):
    from src.models.urban_queue_model import OBSERVED_SPEED_DELAY_CAP_RATIO
    spec = cfg.network.shared_approach
    observed = state.urban_link_speed_kph.get(spec['storage'], cfg.network.urban_avg_speed_km_h)
    return max(float(observed), float(cfg.network.urban_avg_speed_km_h) / OBSERVED_SPEED_DELAY_CAP_RATIO)


def initialize(state, cfg, raw, detectors):
    """After physical projection and its paired-release repair, before area seed."""
    spec = getattr(cfg.network, 'shared_approach', None)
    if spec is None:
        return {}
    if hasattr(state, 'shared_approach_state'):
        raise ValueError('Shared approach state must be initialized once per physical snapshot')
    records = [row for row in complete_records(raw) if str(row['link_no']) == spec['physical_link']]
    # The conservative projection keeps spillback on its actual urban link and
    # exposes it to the ramp controller as observation only. It is not another
    # ramp stock. Never infer a stock transfer from that queue diagnostic.
    diagnostics = state.local_observation_summary.get('projection_diagnostics', {})
    if getattr(cfg.network, 'ramp_spillback_obs', False) and not diagnostics.get('ramp_spillback_observed_only'):
        raise ValueError('Shared approach requires spillback observation without duplicate ramp stock')
    assignment = diagnostics.get('physical_stock_assignment_by_link', {}).get(spec['physical_link'], {})
    if any(amount > 1e-8 for key, amount in assignment.items() if key != 'storage:' + spec['storage']):
        raise ValueError('Shared approach source has another physical stock assignment; vehicle-level cohorts are required')
    retained = records
    occupancy = spec['capacity_veh'] - state.urban_link_storage[spec['storage']]
    if not math.isclose(occupancy, len(retained), abs_tol=1e-8):
        raise ValueError(f'Shared approach physical projection does not conserve its records: {occupancy} vs {len(retained)}')
    dt = cfg.simulation.T_u_sec
    index = int(round(state.time_sec / dt))
    bins = {key: {} for key in spec['branches']}
    routes = None
    observed_counts = {key: 0 for key in spec['branches']}
    unselected = 0
    if spec.get('observed_initial_routes', False):
        from evaluation.controllers.vehicle_routes import complete_vehicle_routes
        routes = complete_vehicle_routes(raw, required=True)
    from src.models.urban_queue_model import OBSERVED_SPEED_DELAY_CAP_RATIO
    for vehicle in retained:
        selected = None
        if routes is not None:
            route = routes[vehicle['veh_no']]
            position = float(vehicle['position_m'])
            decision_position = spec['decision_position_m']
            if route['route_decision_no'] is None:
                if not 0 <= position < decision_position:
                    raise ValueError('Shared initial unselected vehicle is not before its decision')
                unselected += 1
            else:
                selected = str(route['route_no'])
                if (route['route_decision_type'] != 'STATIC'
                        or route['route_decision_no'] != int(spec['native_decision'])
                        or selected not in spec['branches']
                        or not decision_position <= position <= spec['branches'][selected]['branch_position_m']):
                    raise ValueError('Shared initial observed route is outside its reviewed decision/branch interval')
                observed_counts[selected] += 1
        speed = max(float(vehicle['speed_kph']), cfg.network.urban_avg_speed_km_h / OBSERVED_SPEED_DELAY_CAP_RATIO)
        for key, branch in spec['branches'].items():
            if selected is not None and key != selected:
                continue
            distance = max(0.0, branch['branch_position_m'] - float(vehicle['position_m'])) + branch['pre_receiver_distance_m']
            due = index + max(1, math.ceil(distance / (speed / 3.6) / dt))
            bins[key][due] = bins[key].get(due, 0.0) + (1.0 if selected is not None else branch['share'])
    if routes is not None and not math.isclose(sum(sum(row.values()) for row in bins.values()), occupancy,
                                              rel_tol=0., abs_tol=1e-8):
        raise ValueError('Shared initial observed-route bins do not conserve projected stock')
    state.shared_approach_state = {'bins': bins, 'unadmitted_demand_veh': 0.0, 'last_step': index - 1,
                                 'admitted_veh': 0.0, 'departed_veh': 0.0}
    # This storage has its own four-branch travel state, never a generic urban
    # arrival/release pair in addition to those same vehicles.
    state.urban_arrival_buffer.pop(spec['storage'], None)
    state.urban_storage_release_buffer.pop(spec['storage'], None)
    result = {'shared_initial_veh': len(retained), 'shared_spillback_observation_only_veh': sum(bool(row['stopped']) for row in records),
              'shared_route_assignment': 'conditional native static prior; actual per-vehicle destination is unobserved'}
    if routes is not None:
        result.update(shared_initial_observed_route_veh_by_branch=observed_counts,
                      shared_initial_unselected_predecision_veh=unselected,
                      shared_initial_unselected_model_expectation_by_branch={
                          key: unselected*branch['share'] for key, branch in spec['branches'].items()},
                      shared_route_assignment='Observed STATIC1134 destinations retained; only unselected predecision vehicles use the native prior as a model expectation, not observed destination demand.')
    return result


def demand_amount(schedule, start_sec, end_sec):
    """Integrate the declared native volume schedule across interval boundaries."""
    amount = 0.0
    for index, row in enumerate(schedule):
        stop = schedule[index + 1]['start_sec'] if index + 1 < len(schedule) else end_sec
        overlap = max(0.0, min(end_sec, stop) - max(start_sec, row['start_sec']))
        amount += overlap * row['rate_veh_h'] / 3600
    return amount


def advance(state, control, demand, cfg, urban_step_index):
    """Advance once before normal urban releases; independent of objective flag."""
    spec = getattr(cfg.network, 'shared_approach', None)
    if spec is None:
        return {}
    from src.models import urban_queue_model as uqm
    local = getattr(state, 'shared_approach_state', None)
    if local is None or urban_step_index != local['last_step'] + 1:
        raise ValueError('Shared approach requires initialized candidate-private state and sequential explicit steps')
    source = spec['storage']
    capacity = spec['capacity_veh']
    before = capacity - state.urban_link_storage[source]
    bins_total = sum(sum(row.values()) for row in local['bins'].values())
    if not math.isclose(before, bins_total, abs_tol=1e-7):
        raise ValueError('Shared branch travel stock and physical storage disagree')
    dt, dt_h = cfg.simulation.T_u_sec, cfg.simulation.T_u_h
    from evaluation.controllers.control_area_objective import get_ledger
    ledger = get_ledger(state)
    capture = ledger is not None and ledger.captures_response
    accepted_by_branch = {}
    routing = uqm.approach_routing(cfg)
    for key, branch in spec['branches'].items():
        bins = local['bins'][key]
        ready = sum(amount for step, amount in bins.items() if step <= urban_step_index)
        target = branch['target']
        if branch['target_kind'] == 'ramp':
            available = max(0.0, cfg.network.ramp_queue_cap(target) - state.ramp_queue.get(target, 0.0))
        else:
            available = uqm._effective_available_space(state, cfg, target)
        service = cfg.network.movement_capacity_veh_h * branch['lanes'] * dt_h
        accepted = min(ready, available, service)
        if capture:
            sources = {'shared:' + source + ':branch:' + key: accepted}
            ledger.record_resource_allocation('shared_approach_ready', source + ':' + key, ready, sources)
            ledger.record_resource_allocation('shared_approach_service', source + ':' + key, service, sources)
            ledger.record_resource_allocation('shared_approach_receiving', branch['target_kind'] + ':' + target, available, sources)
        if accepted:
            left = accepted
            for due in sorted(bins):
                if due > urban_step_index or left <= 0:
                    break
                take = min(left, bins[due]); bins[due] -= take; left -= take
            local['bins'][key] = {step: value for step, value in bins.items() if value > 1e-12}
            state.urban_link_storage[source] += accepted
            if branch['target_kind'] == 'ramp':
                state.ramp_queue[target] = state.ramp_queue.get(target, 0.0) + accepted
                emit_transfer(state, cfg, 'storage:' + source, 'ramp:' + target, accepted, preserve_area=True)
            else:
                state.urban_link_storage[target] -= accepted
                emit_transfer(state, cfg, 'storage:' + source, 'storage:' + target, accepted, preserve_area=True)
                handled = False
                if getattr(cfg.network, 'route_choice_corridor', None):
                    from evaluation.controllers.route_choice_corridor import receive_shared_accepted
                    handled = receive_shared_accepted(state, cfg, source, key, accepted, urban_step_index)
                if not handled:
                    arrival = urban_step_index + uqm._link_delay_steps(state, cfg, target)
                    if target not in routing:
                        raise ValueError('Shared urban receiver has no downstream movements')
                    uqm._schedule(state.urban_arrival_buffer, target, arrival, accepted)
                    uqm._schedule(state.urban_storage_release_buffer, target, arrival, accepted)
                    if hasattr(cfg.network,'physical_ramp_branches'):
                        from evaluation.controllers.physical_ramp_branches import tag_shared_city_arrival
                        tag_shared_city_arrival(state,cfg,key,arrival,accepted)
        accepted_by_branch[key] = accepted
    desired = demand_amount(spec['schedule'], urban_step_index * dt, (urban_step_index + 1) * dt)
    local['unadmitted_demand_veh'] += desired
    admitted = min(local['unadmitted_demand_veh'], max(0.0, state.urban_link_storage[source]))
    if capture:
        ledger.record_resource_allocation('shared_approach_generation_receiving', 'storage:' + source,
            max(0.0, state.urban_link_storage[source]), {'input:shared:' + source: admitted})
    if admitted:
        speed = _speed(state, cfg)
        state.urban_link_storage[source] -= admitted
        local['unadmitted_demand_veh'] -= admitted
        for key, branch in spec['branches'].items():
            distance = branch['branch_position_m'] + branch['pre_receiver_distance_m']
            due = urban_step_index + max(1, math.ceil(distance / (speed / 3.6) / dt))
            bins = local['bins'][key]
            bins[due] = bins.get(due, 0.0) + admitted * branch['share']
        emit_input(state, cfg, 'storage:' + source, admitted, route_key='input:shared:' + source)
    departed = sum(accepted_by_branch.values())
    after = capacity - state.urban_link_storage[source]
    residual = after - before - admitted + departed
    if abs(residual) > 1e-7:
        raise AssertionError('Shared approach accepted-flow mass balance failed')
    local['admitted_veh'] += admitted; local['departed_veh'] += departed
    local['last_step'] = urban_step_index
    if capture:
        ledger.complete_constraint_coverage('shared_approach')
    return {'shared_input_desired_veh': desired, 'shared_input_admitted_veh': admitted,
            'shared_unadmitted_demand_veh': local['unadmitted_demand_veh'],
            'shared_departed_veh': departed, 'shared_accepted_by_branch': accepted_by_branch,
            'shared_storage_veh': after, 'shared_mass_residual_veh': residual}


def install(adapter, cfg):
    """Install physical dynamics for legacy scoring; area extraction calls directly."""
    if getattr(cfg.network, 'shared_approach', None) is None:
        return {}
    from src.models import urban_queue_model as uqm
    original = uqm.urban_substep
    if getattr(original, '_control_area_events', False):
        return {'shared_approach_runtime': 'canonical_area_body'}
    if getattr(original, '_shared_approach', False):
        return {'shared_approach_runtime': 'existing_wrapper'}

    def urban_substep(state, control, demand, cfg_arg, urban_step_index=None, ramp_release_veh_h=None):
        if getattr(cfg_arg.network, 'shared_approach', None) is None:
            return original(state, control, demand, cfg_arg, urban_step_index=urban_step_index,
                            ramp_release_veh_h=ramp_release_veh_h)
        uqm.ensure_urban_state(state, cfg_arg)
        index = uqm._urban_step_index(state, cfg_arg) if urban_step_index is None else urban_step_index
        added = advance(state, control, demand, cfg_arg, index)
        ttt, diagnostics = original(state, control, demand, cfg_arg, urban_step_index=urban_step_index,
                                    ramp_release_veh_h=ramp_release_veh_h)
        diagnostics.update(added)
        return ttt, diagnostics

    urban_substep._shared_approach = True
    urban_substep._legsplit_wrapped = getattr(original, '_legsplit_wrapped', False)
    adapter._fw_rebind('urban_substep', original, urban_substep)
    uqm.urban_substep = urban_substep
    return {'shared_approach_runtime': 'installed_wrapper'}
