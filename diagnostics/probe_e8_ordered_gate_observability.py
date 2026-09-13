"""Current-snapshot route/lane identifiability; no forecast or traffic-model change."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.controllers.projection_support import complete_records
from evaluation.controllers.vehicle_routes import complete_vehicle_routes

MAPPING = 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'
NETWORK = 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
RUN = 'evaluation/runs/codex_area_sources_beta0_s13_20260910'


def transfer_partition(stock, source, target, requested_veh, receiver_room_veh, *, eligible):
    """Algebraic receipt fixture, not an estimated service/lane-change law.

    Every key is a disjoint subset of an existing physical stock. A successful
    lane change is an explicit input event; elapsed time alone does not invent it.
    """
    if source == target or any(not math.isfinite(v) or v < 0 for v in (*stock.values(), requested_veh, receiver_room_veh)):
        raise ValueError('Invalid disjoint stock transfer')
    result = dict(stock)
    receipt = min(stock[source], requested_veh, receiver_room_veh) if eligible else 0.
    result[source] -= receipt
    result[target] = result.get(target, 0.)+receipt
    if not math.isclose(sum(stock.values()), sum(result.values()), abs_tol=1e-12):
        raise AssertionError('Partition transfer lost stock')
    return result, receipt


def main():
    files = [MAPPING, NETWORK, 'evaluation/controllers/area_freeway_accounting.py',
             'evaluation/controllers/link_predictor.py', 'evaluation/controllers/vehicle_routes.py',
             'evaluation/controllers/projection_support.py',
             'diagnostics/direct_branch_order_audit.json', 'diagnostics/e8_lane_receiving_evidence.json']
    files += [f'{RUN}/decisions_codex_area_sources_beta0_s13_20260910/state_{t:06d}.json' for t in (1200,3300)]
    sha = lambda p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    pins = {p: sha(p) for p in files}
    manifest_path = ROOT/'diagnostics/contract_candidate_configs/manifest.json'
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    frozen = {p: sha(p) for p in manifest['source_sha256']}
    mapping = json.loads((ROOT/MAPPING).read_text(encoding='utf-8'))['freeway_model_links']['FW_E']
    offset = mapping['chain_offsets_m'][mapping['chain_links'].index(2)]
    low, boundary, high = mapping['segment_bounds_m'][8:11]
    network = ET.parse(ROOT/NETWORK).getroot()
    links = {n.get('no'): n for n in network.findall('./links/link')}
    nodes = {}
    for key, role in [('10643','diverge'),('10639','merge'),('10682','diverge'),('10681','merge')]:
        link = links[key];endpoint = link.find('fromLinkEndPt' if role=='diverge' else 'toLinkEndPt')
        first = int(endpoint.get('lane').split()[1]);lanes = len(link.findall('./lanes/lane'))
        nodes[key] = {'role': role, 'chain_m': offset+float(endpoint.get('pos')),
                      'mainline_lanes': list(range(first, first+lanes)), 'native_endpoint': endpoint.attrib}
    gate = nodes['10682']['chain_m']
    routes = {}
    for decision in network.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'):
        if decision.get('no') not in ('1130','1134','1135'):
            continue
        for route in decision.findall('./vehRoutSta/vehicleRouteStatic'):
            key = decision.get('no')+':'+route.get('no')
            routes[key] = {'decision': decision.attrib, 'route': route.attrib,
                'ordered_links': [decision.get('link')]+[n.get('key') for n in route.findall('./linkSeq/intObjectRef')]+[route.get('destLink')]}
    assert '10682' in routes['1130:3']['ordered_links']
    assert routes['1134:3']['ordered_links'] == ['69','10637','70','10639','2']
    assert float(routes['1134:3']['route']['destPos'])+offset > gate
    snapshots = []
    for time_sec in (1200,3300):
        path = f'{RUN}/decisions_codex_area_sources_beta0_s13_20260910/state_{time_sec:06d}.json'
        raw = json.loads((ROOT/path).read_text(encoding='utf-8'))
        physical = complete_records(raw); observed = complete_vehicle_routes(raw, required=True)
        assert raw['sim_sec'] == time_sec
        rows = []
        for row in physical:
            pos = row['position_m']+offset
            if row['link_no'] != 2 or not low <= pos < high:
                continue
            route = observed[row['veh_no']]
            identity = f"{route['route_decision_no']}:{route['route_no']}" if route['route_decision_type']=='STATIC' else 'unresolved'
            rows.append({'veh_no': row['veh_no'], 'chain_m': pos, 'lane': row['lane_no'],
                         'speed_kph': row['speed_kph'], 'current_route': identity,
                         'zone': 'E8' if pos<boundary else 'E9_before_10682' if pos<gate else 'E9_after_10682'})
        zone_rows = {}
        for zone in ('E8','E9_before_10682','E9_after_10682'):
            selected = [r for r in rows if r['zone']==zone]
            by_lane = []
            for lane in (1,2,3,4):
                group = [r for r in selected if r['lane']==lane]
                direct = [r for r in group if r['current_route']=='1130:3']
                by_lane.append({'lane':lane,'count':len(group),'mean_speed_kph':sum(r['speed_kph'] for r in group)/len(group) if group else None,
                    'stopped_lt1':sum(r['speed_kph']<1 for r in group),'stopped_lt5':sum(r['speed_kph']<5 for r in group),
                    'route1130_3_count':len(direct),'route1130_3_stopped_lt1':sum(r['speed_kph']<1 for r in direct),
                    'route_counts':dict(Counter(r['current_route'] for r in group)),
                    'front_vehicle':max(group,key=lambda r:r['chain_m']) if group else None})
            zone_rows[zone] = {'count':len(selected),'by_lane':by_lane}
        e8 = zone_rows['E8']['count'];e9 = zone_rows['E9_before_10682']['count']+zone_rows['E9_after_10682']['count']
        assert (e8,e9)==tuple(raw['freeway_segments']['FW_E'][i]['count'] for i in (8,9))
        direct = [r for r in rows if r['zone']=='E9_before_10682' and r['current_route']=='1130:3']
        physical_lane = nodes['10682']['mainline_lanes']
        compatible = sum(r['lane'] in physical_lane for r in direct)
        demands = sum(min(abs(r['lane']-lane) for lane in physical_lane) for r in direct)
        # Receiver and service limits intentionally nonbinding: expose only
        # which current stock requires a lateral exchange, not actual discharge.
        proof_stock = {'direct_lane1':float(compatible),'direct_needs_exchange':float(len(direct)-compatible),'connector10682':0.}
        same_lane, accepted = transfer_partition(proof_stock,'direct_lane1','connector10682',float(len(direct)),float(len(direct)),eligible=True)
        measured = {}
        for connector in ('10643','10639','10682','10681'):
            group = [r for r in physical if r['link_no']==int(connector)]
            stopped = [r for r in group if r['speed_kph']<1]
            measured[connector] = {'count':len(group),'stopped_lt1':len(stopped),
                'mean_speed_kph':sum(r['speed_kph'] for r in group)/len(group) if group else None,
                'upstreammost_stopped_position_m':min(r['position_m'] for r in stopped) if stopped else None}
        prefix_count = zone_rows['E9_before_10682']['count']
        rear_count = zone_rows['E9_after_10682']['count']
        density = {'macro_E9_veh_km_lane':e9/((high-boundary)/1000*4),
                   'prefix_veh_km_lane':prefix_count/((gate-boundary)/1000*4),
                   'rear_veh_km_lane':rear_count/((high-gate)/1000*4),
                   'prefix_fraction_of_macro_stock':prefix_count/e9}
        snapshots.append({'sim_sec':time_sec,'source':path,'zones':zone_rows,'vehicle_rows':rows,
            'geometric_densities_from_current_partition':density,
            'same_lane_direct_stock_upper_bound_only':accepted,'all_direct_stock':len(direct),
            'direct_requires_exchange_stock':len(direct)-compatible,'minimum_adjacent_lane_exchanges_needed':demands,
            'partition_conservation_residual':sum(same_lane.values())-sum(proof_stock.values()),
            'direct_ordered_merge_cohort_bypass_count':sum(r['current_route']=='1134:3' for r in rows if r['zone']=='E9_before_10682'),
            'connector_observations':measured})
    pieces = sorted({low,boundary,high,*[n['chain_m'] for n in nodes.values()]})
    shortest = min(b-a for a,b in zip(pieces,pieces[1:]))
    length = gate-boundary
    # Exact rho*v continuity arithmetic at a declared120km/h illustration.
    numerical = {'prefix_length_m':length,'dt_sec':10.,'illustrative_speed_kph':120.,
        'courant_speed_dt_over_length':120/3.6*10/length,'prefix_advection_dt_limit_sec':length/(120/3.6),
        'shortest_piece_if_both_macro_boundaries_and_all_nodes_split_m':shortest,
        'shortest_piece_dt_limit_sec':shortest/(120/3.6),
        'one_vehicle_empty_inflow_uncapped_next_stock':1.-120/3.6*10/length,
        'scope':'Positivity counterexample for unmodified explicit rho*v sending; not a fitted speed/capacity or a proof of stability of a new solver.'}
    changes = [p for p,h in pins.items() if sha(p)!=h]+[p for p,h in frozen.items() if sha(p)!=h]
    assert not changes and manifest_path.read_bytes()==manifest_bytes
    out = {'schema':'e8-ordered-gate-observability/v1','scope':'Paused current state only; no future states, endpoint, MPC, FZP scan or VISSIM. Algebraic eligibility/stock bounds are not forecasts.',
        'source_sha256':pins,'source_changes':changes,'frozen_source_count':len(frozen),
        'nodes':nodes,'macro_bounds_m':[low,boundary,high],'native_routes':routes,
        'snapshots':snapshots,'short_cell_counterexample':numerical,
        'minimum_contract':'Disjoint subset of existing macrocell N; ordered route/lane eligibility; explicit accepted lateral/longitudinal receipts; common sending/receiving/speed-lookahead state. No automatic lane-change success after an invented wait.'}
    (ROOT/'diagnostics/e8_ordered_gate_observability.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'snapshot_summary':[{k:r[k] for k in ('sim_sec','same_lane_direct_stock_upper_bound_only','all_direct_stock','direct_requires_exchange_stock','minimum_adjacent_lane_exchanges_needed','direct_ordered_merge_cohort_bypass_count')} for r in snapshots],
                     'numerical':numerical,'source_changes':changes},indent=2))


if __name__=='__main__':
    main()
