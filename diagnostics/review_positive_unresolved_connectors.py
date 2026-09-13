"""Preserve source-lineage and future-choice evidence for four positive gaps."""
import csv
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]


def main():
    from diagnostics.probe_model_area_integration import build_projected
    run = 'codex_area_beta0_retry_s13_20260910'
    folder = ROOT/'evaluation/runs'/run/('decisions_'+run)
    paths = {
        'network': ROOT/'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx',
        'membership': ROOT/'diagnostics/control_area_membership.json',
        'config': ROOT/'diagnostics/area_candidate_configs/n7_area_beta0.json',
        'state': folder/'state_001200.json', 'previous': folder/'action_001050.json',
        'gate_map': ROOT/'evaluation/real_world_modi_inventory/urban_input_gate_map_legs4b_20260819.csv',
        'support': ROOT/'diagnostics/physical_projection_support_635_proposal.json',
        'canonical_contract': ROOT/'diagnostics/control_area_route_contract_physical_routes.json',
        'occurrence': ROOT/'diagnostics/unresolved_positive_occurrence_audit.json'}
    cfg, _, detectors, _, raw, _, _ = build_projected(paths['config'], paths['state'], paths['previous'], fixture_inputs=False)
    tree = ET.parse(paths['network']).getroot()
    links = {x.get('no'): x for x in tree.findall('./links/link')}
    inside = set(json.loads(paths['membership'].read_text())['inside_links'])
    contract = json.loads(paths['canonical_contract'].read_text())
    support = json.loads(paths['support'].read_text())
    incoming, outgoing = {}, {}
    for key, node in links.items():
        a, b = node.find('fromLinkEndPt'), node.find('toLinkEndPt')
        if a is not None:
            row = {'connector': key, 'from': dict(a.attrib), 'to': dict(b.attrib), 'lanes': len(node.findall('./lanes/lane'))}
            incoming.setdefault(b.get('lane').split()[0], []).append(row)
            outgoing.setdefault(a.get('lane').split()[0], []).append(row)
    native = []
    for decision in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'):
        for route in decision.findall('./vehRoutSta/vehicleRouteStatic'):
            path = [decision.get('link')] + [x.get('key') for x in route.findall('./linkSeq/intObjectRef')] + [route.get('destLink')]
            native.append({'id': decision.get('no')+':'+route.get('no'), 'decision': dict(decision.attrib),
                'route': dict(route.attrib), 'path': path, 'membership': {k: k in inside for k in path}})
    selected = ['10379','10381','1220008203','236','1210008203',
                '10610','385','10611','1220000102','10618','10619','382','183',
                '10500','62','10603','404','10501','52']
    geometry = {}
    for key in selected:
        geometry[key] = {'inside': key in inside, 'incoming': incoming.get(key, []), 'outgoing': outgoing.get(key, []),
            'heads': [dict(x.attrib) for x in tree.findall('./signalHeads/signalHead') if x.get('lane').split()[0] == key],
            'inputs': [{'attributes':dict(x.attrib), 'volumes':[dict(y.attrib) for y in x.findall('./timeIntVehVols/timeIntervalVehVolume')]}
                       for x in tree.findall('./vehicleInputs/vehicleInput') if x.get('link') == key],
            'origins': detectors.get('link_to_origins', {}).get(key),
            'projected_movements': detectors.get('link_to_movements', {}).get(key),
            'transit_marker': detectors.get('transit_storage_projection', {}).get(key)}
    upstream = {}
    for connector in ['10367','10374','10378']:
        upstream[connector] = {'support_target':support['link_to_storage'][connector],
            'support_evidence':support['evidence'][connector],
            'active_canonical_turns': [dict(movement=name.removeprefix('movement:'), turn=turn,
                current_spec=cfg.network.urban_movements[name.removeprefix('movement:')])
                for name, row in contract.items() if name.startswith('movement:') and name.removeprefix('movement:') in cfg.network.urban_movements
                for turn in row.get('physical_turns', []) if turn.get('connector') == connector]}
    with paths['gate_map'].open(encoding='utf-8-sig') as f:
        gates = [row for row in csv.DictReader(line for line in f if not line.startswith('#')) if row['no'] == '1091']
    relevant = {name: row for name,row in cfg.network.urban_movements.items()
        if row.get('origin') in {'SC11_to_SC1','in_SC1_E','SC107_to_SC1004','SC107_to_SC1005'}
        or row.get('receiving_link') in {'SC107_to_SC1004','SC107_to_SC1005'}}
    output = {
        'sources': {key:{'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for key,path in paths.items()},
        'geometry':geometry, 'native_routes':[row for row in native if any(k in row['path'] for k in ['10379','10381','10610','10611'])
            or row['decision']['no'] in ['12','1128','1123']],
        'upstream_10379':upstream, 'input_1091_gate_map':gates,
        'input_1091_live_gate_value':raw['demand']['urban_volume_vph_by_gate'].get('in_SC1_E'),
        'input_1091_forecast_note':'Anchored gate dictionary omits in_SC1_E; base forecast initializes absent gates to0. Internal aggregate is reported but not distributed by this path.',
        'active_movements':relevant,
        'initial_support_proposals':{
            '10379':{'status':'unique_premerge_source_lineage','target':'SC11_to_SC1',
                'path':['1220008203','10379','1210008203'],
                'proof':'Source has no input/head and all three actual incoming connectors have the same reviewed canonical receiver. Native1104:1 selects10379. Do not reassign the mixed downstream road.',
                'validator_extension':'Check exact source incoming set against pinned canonical accepted receivers/support rows, no source input, real connector endpoint and native route.'},
            '10381':{'status':'unique_physical_input_but_model_origin_needs_explicit_contract','proposed_target':'in_SC1_E',
                'path':['236','10381','1210008203'],
                'proof':'Source236 has no incoming connectors and only nativeinput1091; native1105:1 selects10381. Its downstream is the SC1 E approach.',
                'remaining_gap':'Gate map calls1091 internal and leaves gate empty. The live anchored forecast omits it. Existing boundary_in origin in_SC1_E is an available receiver, but no source-to-origin mapping contract authorizes calling it the current assigned gate.',
                'initial_area_events':{'entered':0,'ttd':0}},
            '10610':{'status':'future_choice_1128','single_target_prohibited':True},
            '10611':{'status':'future_choice_1128','single_target_prohibited':True}},
        '1128_reuse_design':{
            'shared_prefix':['10610','385','10611','10618','10619','1220000102'],
            'decision_position_m':20.576829873567828,
            '10611_entry_position_m':14.137201,
            'branches':{
                '1':{'path':['1220000102','10500','62','10603','404'], 'native_weight_default':1,
                    'needs_local_stage':'Physical transit via62 then accepted10603 before the local signal head; existing SC107_to_SC1005 has an extra through-to-SC1004 movement incompatible with this selected route.',
                    'arrival_target_candidate':'SC1005_to_SC105','initial_and_branch_area_crossings':0},
                '2':{'path':['1220000102','10501','52'],'native_weight_default':1,
                    'existing_receiver':'SC107_to_SC1004','initial_and_branch_area_crossings':0}},
            'why_no_single_existing_stock':'SC107_to_SC1005 and SC107_to_SC1004 predict different downstream queues, travel, and service. Assigning their shared predecision physical road to either commits a route early.',
            'minimal_generalization':'Parameterize one finite-prefix engine by corridor id, branch->target/stage, number of native choices, explicit queue vs unsignalled transit exit, service group and physical partition. Keep candidate-private cohorts per id; no separate adapter or duplicated urban body.',
            'routing_policy':'Use prior only for future eligible prechoice vehicles. Already past decision without actual route identity must fail or explicit diagnostic hold. Blank native weights mean declared defaults, not empirical50/50 truth.',
            'scope_caveat':'Other same-road entrants10618/10619 must be included with real path/accepted source mapping. Both branches remain inside Omega through404 or52; TTD is only later accepted crossing out of635.'},
        'production_data_changed':False}
    destination = ROOT/'diagnostics/positive_unresolved_connector_review.json'
    if destination.exists(): raise FileExistsError(destination)
    destination.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__ == '__main__': main()
