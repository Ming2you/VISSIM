"""Read-only source-generation audit of every native internal input."""
from collections import defaultdict
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def csv_rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as file:
        return list(csv.DictReader(line for line in file if not line.startswith('#')))


def main():
    from diagnostics.probe_model_area_integration import adapter, build_projected
    from src.models.demand import DemandStep
    os.environ['RW_MAINLINE_SG_ONLY'] = '1'
    folder = ROOT/'evaluation/runs/codex_area_beta0_retry_s13_20260910/decisions_codex_area_beta0_retry_s13_20260910'
    config = ROOT/'diagnostics/route_choice_native_phase_integration_config.json'
    snapshot, previous = folder/'state_001350.json', folder/'action_001200.json'
    sources = [config, snapshot, previous, *sorted((ROOT/'evaluation/controllers').glob('*.py'))]
    cfg, state, detectors, tuning, raw, mapping, metadata = build_projected(config, snapshot, previous, fixture_inputs=False)
    manifest_path = Path(raw['run_provenance']['manifest_path'])
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    network_path = ROOT/'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
    membership_path = ROOT/'diagnostics/control_area_membership.json'
    gate_path = ROOT/'evaluation/real_world_modi_inventory/urban_input_gate_map_ver2_20260907.csv'
    roles_path = ROOT/'evaluation/real_world_modi_inventory/vehicle_input_roles.csv'
    profile_path = Path(manifest['demand_profile'])
    sources += [network_path, membership_path, gate_path, roles_path, profile_path, manifest_path]
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in sources}
    gates = csv_rows(gate_path)
    roles = {x['no']:x['role'].lower() for x in csv_rows(roles_path)}
    profile = {x['role'].lower():float(x['multiplier']) for x in csv_rows(profile_path)}
    tree = ET.parse(network_path).getroot()
    links = {x.get('no'):x for x in tree.findall('./links/link')}
    inputs = {x.get('no'):x for x in tree.findall('./vehicleInputs/vehicleInput')}
    inside = set(json.loads(membership_path.read_text(encoding='utf-8'))['inside_links'])
    native = defaultdict(list)
    for decision in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'):
        for route in decision.findall('./vehRoutSta/vehicleRouteStatic'):
            native[decision.get('link')].append({'route':decision.get('no')+':'+route.get('no'),
                'decision_pos_m':float(decision.get('pos')), 'all_vehicle_types':decision.get('allVehTypes'),
                'route_method':decision.get('routeChoiceMeth'), 'relFlow':route.get('relFlow'),
                'dest_pos_m':float(route.get('destPos')),
                'path':[decision.get('link')]+[x.get('key') for x in route.findall('./linkSeq/intObjectRef')]+[route.get('destLink')]})
    calibration = adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
    calibration = adapter.deep_update(calibration, tuning.get('calibration_override', {}))
    forecast = adapter.demand_from_state(raw, cfg, DemandStep, 1, calibration, detectors)[0]
    assigned = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    specs = cfg.network.urban_movements
    positive_gates = {key:float(value) for key,value in forecast.urban_boundary.items() if value > 0}
    scheduled_native = getattr(cfg.network, 'native_internal_inputs', {}).get('inputs', {})
    shared = getattr(cfg.network, 'shared_approach', {})
    far = raw['local_observation'].get('far_measurement', {}).get('link_volume_veh_h', {})
    rows = []
    for gate in gates:
        if gate['status'] not in ('internal', 'shared_stem_unmapped'):
            continue
        no, link = gate['no'], gate['link']
        factor = float(manifest['demand_scale'])*profile.get('no:'+no, profile.get(roles[no], profile.get('__default__', 1.)))
        schedule = [{'start_sec':float(x.get('timeInt').split()[1])/1000,
            'rate_veh_h':float(x.get('volume'))*factor, 'volume_type':x.get('volType')}
            for x in inputs[no].findall('./timeIntVehVols/timeIntervalVehVolume')]
        current = next(r['rate_veh_h'] for r in reversed(schedule) if r['start_sec'] <= raw['sim_sec'])
        integrated = sum(r['rate_veh_h']*((schedule[i+1]['start_sec'] if i+1<len(schedule) else 5400)-r['start_sec'])/3600
            for i,r in enumerate(schedule))
        destinations = []
        for route in native.get(link, []):
            path = route['path']
            destinations.append({**route,
                'membership':[x in inside for x in path],
                'crossing_edges':[{'from_link':a,'to_link':b,'source_inside':a in inside,'target_inside':b in inside}
                    for a,b in zip(path,path[1:]) if (a in inside)!=(b in inside)],
                'projection_along_path':{x:{'origins':detectors.get('link_to_origins',{}).get(x,[]),
                    'movements':detectors.get('link_to_movements',{}).get(x,[]),
                    'transit_target':detectors.get('transit_storage_projection',{}).get(x)} for x in path},
                'future_native_decisions_on_destination':native.get(path[-1],[])})
        source_origins = detectors.get('link_to_origins', {}).get(link, [])
        source_movements = detectors.get('link_to_movements', {}).get(link, [])
        names = {r['movement'] for r in source_movements}
        names |= {name for name,row in specs.items() if row.get('origin') in source_origins}
        origin_rates = {origin:float(forecast.urban_boundary.get(origin,0)) for origin in source_origins}
        if no in scheduled_native:
            implementation = {'status':'explicit_native_internal_generation',
                'storage':scheduled_native[no]['target_storage'], 'rate_at_snapshot_veh_h':current,
                'source_event':'input:internal:'+no, 'boundary_entry_veh':0}
        elif no == str(shared.get('native_input')):
            implementation = {'status':'explicit_shared_stem_generation', 'storage':shared['storage'],
                'rate_at_snapshot_veh_h':current, 'source_event':'input:shared:'+shared['storage'],
                'excluded_from_internal_bucket':True}
        else:
            implementation = {'status':'no_explicit_native_source_generation', 'rate_at_snapshot_veh_h':0,
                'missing_desired_rate_veh_h':current,
                'reason':'Blank internal gate excluded by runner; profiled_demand_rates uses mapped gate table only. Aggregate internal volume is validated by the1091 helper but is not injected for other IDs. Initial stock/ordinary transfers do not create this future source.'}
        rows.append({'native_input':no,'physical_source':link,'source_inside':link in inside,
            'bucket':gate['status'],'gate_row':gate,'schedule':schedule,'desired_0_5400_veh':integrated,
            'desired_rate_at_snapshot_veh_h':current,'initial_raw_count':raw['vehicle_records']['full_network_link_counts'].get(link,0),
            'initial_stock_assignment':assigned.get(link,{}), 'source_origins':source_origins,
            'source_transit_projection':detectors.get('transit_storage_projection',{}).get(link),
            'source_movement_specs':{name:specs[name] for name in sorted(names)},
            'forecast_by_source_origin':origin_rates,
            'positive_gate_collisions':{origin:{'forecast_veh_h':value,'mapped_native_sources':[g['no'] for g in gates if g['gate']==origin and g['status']=='mapped']}
                for origin,value in origin_rates.items() if value>0},
            'observed_source_flow_veh_h':far.get(link), 'native_routes':destinations,
            'future_implementation':implementation})
    internal = [r for r in rows if r['bucket']=='internal']
    missing = [r for r in internal if r['future_implementation']['status']=='no_explicit_native_source_generation']
    result = {'scope':'Read-only1350 current canonical configuration with1091 and two route corridors enabled. No rollout, VISSIM, future FZP or production mutation. Native schedule is desired demand, not observed admission.',
        'sim_sec':raw['sim_sec'],'sources_sha256':hashes,'source_changes':[p for p,h in hashes.items() if sha(ROOT/p)!=h],
        'raw_demand':raw['demand'],'positive_urban_forecast':positive_gates,'ramp_forecast':forecast.ramp_arrival,
        'summary':{'internal_input_count':len(internal),'all_sources_inside':all(r['source_inside'] for r in internal),
            'internal_desired_rate_veh_h':sum(r['desired_rate_at_snapshot_veh_h'] for r in internal),
            'explicit_internal_source_count':len(internal)-len(missing),
            'missing_explicit_native_input_ids':[r['native_input'] for r in missing],
            'missing_desired_rate_veh_h':sum(r['desired_rate_at_snapshot_veh_h'] for r in missing),
            'missing_desired_0_5400_veh':sum(r['desired_0_5400_veh'] for r in missing)},
        'inputs':rows}
    output = ROOT/'diagnostics/native_internal_inputs_audit.json'
    if output.exists():
        raise FileExistsError(output)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result['summary'],ensure_ascii=False,indent=2))
    for r in rows:
        print(r['native_input'],r['physical_source'],r['desired_rate_at_snapshot_veh_h'],r['source_origins'],
              r['forecast_by_source_origin'],[x['route'] for x in r['native_routes']])


if __name__ == '__main__':
    main()
