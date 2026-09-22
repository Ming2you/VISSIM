"""Opt-in coefficient transfer to the unchanged aggregate freeway grid.

This module does not install lane, port, ramp travel or urban CTM dynamics.
Current complete observations are binned onto the declared legacy grid, so
offline snapshots collected with another grid do not silently change geometry.
"""
from bisect import bisect_right
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CELL_KEYS = {'v_free', 'rho_crit', 'metanet_a_m', 'metanet_tau_h',
             'metanet_nu_km2_h', 'metanet_kappa_veh_km_lane'}
DIRECTION_KEYS = {'metanet_delta_merge', 'freeway_lane_drop_phi'}


def configure(cfg, tuning, mapping):
    path = tuning.get('freeway', {}).get('parameter_transfer')
    if path is None:
        return {}
    if tuning['freeway'].get('lane_plant') or tuning['freeway'].get('geometry_profile'):
        raise ValueError('Parameter-only transfer requires the legacy aggregate grid')
    data = (ROOT / path).read_bytes()
    document = json.loads(data)
    if document.get('schema') != 'legacy-metanet-parameter-transfer/v1':
        raise ValueError('Unsupported coefficient transfer schema')
    for pin in document['sources'].values():
        if hashlib.sha256((ROOT / pin['path']).read_bytes()).hexdigest() != pin['sha256']:
            raise ValueError('Coefficient transfer source changed: ' + pin['path'])
    if document['legacy_mapping'] != mapping['freeway_model_links']:
        raise ValueError('Coefficient transfer cannot alter the declared legacy grid')
    net = cfg.network
    if set(document['by_direction']) != set(net.freeway_links):
        raise ValueError('Direction coefficient coverage differs')
    expected = {f'{road}_S{i}' for road in net.freeway_links
                for i in range(net.freeway_segments_per_link)}
    if set(document['segments']) != expected:
        raise ValueError('Cell coefficient coverage differs')
    for key, row in document['segments'].items():
        if set(row) != CELL_KEYS or any(not math.isfinite(v) or v <= 0 for v in row.values()):
            raise ValueError('Invalid coefficient row: ' + key)
    for road, row in document['by_direction'].items():
        if set(row) != DIRECTION_KEYS or any(not math.isfinite(v) or v < 0 for v in row.values()):
            raise ValueError('Invalid directional coefficients: ' + road)
    net.freeway_segment_params = {road: [dict(document['segments'][f'{road}_S{i}'])
        for i in range(net.freeway_segments_per_link)] for road in net.freeway_links}
    net.metanet_parameters_by_direction = deepcopy(document['by_direction'])
    net.metanet_parameter_transfer = {'path': str((ROOT / path).resolve()),
                                    'sha256': hashlib.sha256(data).hexdigest()}
    return {'metanet_parameter_transfer_enabled': 1.0}


def project_current(raw, mapping):
    from evaluation.controllers.projection_support import complete_records
    from evaluation.controllers.vehicle_routes import complete_vehicle_routes
    if raw.get('vehicle_routes') is None and raw.get('lane_plant_observation'):
        # Offline reuse of a same-second capture; no lane dynamics or history
        # reconstruction, and never touch the running observer checkpoint.
        from evaluation.controllers.lane_plant_runtime import bind_current_routes
        meta = raw['lane_plant_observation']
        sec = raw['sim_sec']
        if meta['time_s'] != sec or meta['run_id'] != raw['run_provenance']['run_id']:
            raise ValueError('Offline current-route observation identity differs')
        data = (Path(meta['directory']) / f'frame_{int(sec):06d}.json').read_bytes()
        frame = json.loads(data.decode('utf-16') if data.startswith((b'\xff\xfe', b'\xfe\xff'))
                           else data.decode('utf-8-sig'))
        if frame['run_id'] != meta['run_id'] or frame['time_s'] != sec or frame['complete'] is not True:
            raise ValueError('Offline route frame is not the current complete observation')
        raw = bind_current_routes(raw, {'frames': [frame]})
    result = dict(raw)
    tables, addresses = {}, {}
    for road, geometry in mapping['freeway_model_links'].items():
        bounds = geometry['segment_bounds_m']
        tables[road] = [dict(count=0, speed_sum=0., length_km=(b-a)/1000.,
                             lanes=geometry['segment_lanes'][i])
                         for i, (a,b) in enumerate(zip(bounds, bounds[1:]))]
        for link, offset in zip(geometry['chain_links'], geometry['chain_offsets_m']):
            addresses[str(link)] = road, float(offset)
    for vehicle in complete_records(raw):
        address = addresses.get(str(vehicle['link_no']))
        if address is None:
            continue
        road, offset = address
        bounds = mapping['freeway_model_links'][road]['segment_bounds_m']
        position = offset + vehicle['position_m']
        # The original aggregate observation convention censors at chain ends.
        index = min(len(bounds)-2, max(0, bisect_right(bounds, position)-1))
        row = tables[road][index]
        row['count'] += 1
        row['speed_sum'] += vehicle['speed_kph']
    result['freeway_segments'] = tables
    if raw.get('vehicle_routes'):
        result['vehicle_routes'] = deepcopy(raw['vehicle_routes'])
        for row in result['vehicle_routes']['records']:
            for key in ('route_decision_no', 'route_no'):
                value = row[key]
                if isinstance(value, float) and math.isfinite(value) and value.is_integer():
                    row[key] = int(value)
        complete_vehicle_routes(result, required=True)
    return result


def configure_demand(cfg, mapping):
    if not getattr(cfg.network, 'metanet_parameter_transfer', None):
        return {}
    schedule = cfg.network.native_input_schedule
    starts = {str(row['chain_links'][0]): road
              for road, row in mapping['freeway_model_links'].items()
              if row['chain_offsets_m'][0] == 0}
    directed = {}
    for number, row in schedule['inputs'].items():
        if row['role'].startswith('freeway'):
            directed[number] = starts[str(row['physical_source'])]
    if sorted(directed.values()) != sorted(cfg.network.freeway_links):
        raise ValueError('Each aggregate road needs one actual native mainline input')
    schedule['freeway_link_by_input'] = directed
    return {'metanet_directional_native_demand_enabled': 1.0}
