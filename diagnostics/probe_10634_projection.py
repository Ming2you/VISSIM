"""Read-only bounded evidence for the three 10634 vehicles at beta0 retry 1350."""
from pathlib import Path
import sys, json, hashlib, xml.etree.ElementTree as ET, time, math, os
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RUN = ROOT / 'evaluation/runs/codex_area_beta0_retry_s13_20260910'
DEC = RUN / ('decisions_' + RUN.name)

def main():
    raw_path = DEC / 'state_001350.json'
    raw = json.loads(raw_path.read_text(encoding='utf-8-sig'))
    from evaluation.controllers.projection_support import complete_records
    records = complete_records(raw)
    vehicles = [row for row in records if str(row['link_no']) == '10634']
    ids = {int(row['veh_no']) for row in vehicles}
    assert len(ids) == 3
    net_path = ROOT / 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
    tree = ET.parse(net_path).getroot()
    links = {n.get('no'): n for n in tree.findall('./links/link')}
    selected = ['71','10634','56','10621','10627','57','61','10632','10617','10623','10624','387']
    report = {'run': RUN.name, 'sim_sec': raw['sim_sec'], 'vehicles': vehicles,
              'physical_links': {}, 'native_routing': {}, 'previous_snapshots': {},
              'small_source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                  [raw_path, net_path, Path(__file__), ROOT/'evaluation/controllers/area_dynamic_routes.py',
                   ROOT/'diagnostics/dynamic_area_routes_ver2.json', ROOT/'evaluation/controllers/projection_support.py']}}
    report['all_shared_initial_records'] = [row for row in records if str(row['link_no']) in {'10627','10634','10632','56'}]
    report['downstream_initial_records'] = [row for row in records if str(row['link_no']) in {'57','10617','10621','61','387','10623','10624','404'}]
    for key in selected:
        node = links[key]
        ends = {tag: dict(node.find(tag).attrib) for tag in ('fromLinkEndPt','toLinkEndPt') if node.find(tag) is not None}
        points = [tuple(float(p.get(c, 0)) for c in ('x','y','zOffset')) for p in node.findall('./geometry/linkPolyPts/linkPolyPoint')]
        report['physical_links'][key] = {'endpoints': ends, 'lanes': len(node.findall('./lanes/lane')),
                                        'length_m': sum(math.dist(a,b) for a,b in zip(points,points[1:]))}
    for node in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'):
        routes = node.findall('./vehRoutSta/vehicleRouteStatic')
        if node.get('no') in {'1125','1126','1129','1138','1140'} or any(any(x.get('key') in {'10634','56','10621'} for x in r.findall('./linkSeq/intObjectRef')) for r in routes):
            data = {'attributes': dict(node.attrib), 'routes': {}}
            for route in routes:
                data['routes'][route.get('no')] = {'attributes': dict(route.attrib), 'path': [x.get('key') for x in route.findall('./linkSeq/intObjectRef')]}
            report['native_routing'][node.get('no')] = data
    report['native_inputs_on_selected'] = [n.attrib for n in tree.findall('./vehicleInputs/vehicleInput') if n.get('link') in selected]
    report['signal_heads_on_selected'] = [n.attrib for n in tree.findall('./signalHeads/signalHead') if n.get('lane','').split(' ')[0] in selected]
    for path in sorted(DEC.glob('state_*.json')):
        earlier = json.loads(path.read_text(encoding='utf-8-sig'))
        found = [row for row in earlier['vehicle_records']['records'] if int(row['veh_no']) in ids]
        report['previous_snapshots'][str(earlier['sim_sec'])] = found
    decision_pos = float(report['native_routing']['1129']['attributes']['pos'])
    report['prefix_position_coverage'] = {}
    for label,directory in [('retry',DEC),('pure_n7',ROOT/'evaluation/runs/codex_n7_pure_s13_20260910/decisions_codex_n7_pure_s13_20260910')]:
        rows=[]
        for path in sorted(directory.glob('state_*.json')):
            snap=json.loads(path.read_text(encoding='utf-8-sig'))
            current=[x for x in snap['vehicle_records']['records'] if str(x['link_no']) in {'56','57','10617','10627','10634','10632','10621'}]
            before=[x for x in current if str(x['link_no'])=='56' and float(x['position_m'])<decision_pos]
            after=[x for x in current if str(x['link_no'])=='56' and float(x['position_m'])>=decision_pos]
            rows.append({'sim_sec':snap['sim_sec'],'56_before_decision_veh':len(before),'56_at_or_after_decision_veh':len(after),
                '56_after_decision_records':after,'physical_counts':{key:sum(str(x['link_no'])==key for x in current) for key in ['56','57','10617','10627','10634','10632','10621']}})
        report['prefix_position_coverage'][label]=rows
    from diagnostics.probe_e8_lane_receiving import IndexedFzp
    from diagnostics.probe_e8_window_passages import frames
    fzp, = (RUN/'vissim_eval').glob('*.fzp')
    reader = IndexedFzp(fzp, max_bytes=90*1024*1024)
    provenance, histories = [], {str(key): [] for key in sorted(ids)}
    try:
        for sec, rows in frames(reader, 1050, 1350, time.monotonic()+60, provenance):
            for key in ids:
                row = rows.get(key)
                if row is None: continue
                prior = histories[str(key)]
                if prior and prior[-1]['link'] == row[0] and prior[-1]['lane'] == row[1]:
                    prior[-1].update(last_sec=sec,last_position_m=row[2],last_speed_kph=row[3])
                else:
                    prior.append({'first_sec':sec,'last_sec':sec,'link':row[0],'lane':row[1],
                                  'first_position_m':row[2],'last_position_m':row[2],
                                  'first_speed_kph':row[3],'last_speed_kph':row[3]})
        report['trajectory'] = {'file': str(fzp.relative_to(ROOT)), 'file_size': fzp.stat().st_size,
                                'bytes_read':reader.bytes_read, 'range_hashes':provenance,'histories':histories,
                                'future_route_not_observed': True}
    finally: reader.handle.close()
    os.environ['RW_MAINLINE_SG_ONLY']='1'
    from diagnostics.probe_model_area_integration import build_projected
    cfg,state,detectors,tuning,_,mapping,_ = build_projected(ROOT/'diagnostics/area_candidate_configs/n7_area_beta0.json',
                DEC/'state_001200.json', DEC/'action_001050.json', fixture_inputs=False)
    report['valid_1200_model'] = {'detectors': {key:{field:detectors.get(field,{}).get(key) for field in
                   ('link_to_origins','link_to_movements','transit_storage_projection')} for key in selected},
         'movements': {key:spec for key,spec in cfg.network.urban_movements.items() if spec.get('signal') in {'SC1004','SC1005'}
                       and (spec.get('receiving_link') in {'SC1004_to_SC1005','SC1004_to_SC107'} or spec.get('origin')=='SC1004_to_SC1005')},
         'storage_capacity_veh':{key:value for key,value in cfg.network.urban_link_storage_veh.items() if 'SC1004' in key},
         'storage_veh':{key:cfg.network.urban_link_storage_veh[key]-value for key,value in state.urban_link_storage.items() if 'SC1004' in key},
         'movement_capacity_veh_h':{key:value for key,value in getattr(cfg.network,'movement_capacity_by_movement_veh_h',{}).items() if key.startswith('SC1004_') and '_to_E_' in key}}
    report['source_changes_during_probe'] = [key for key,sha in report['small_source_sha256'].items()
                  if hashlib.sha256((ROOT/key).read_bytes()).hexdigest()!=sha]
    output=ROOT/'diagnostics/projection_10634_evidence.json'
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    paths = {key: [row['link'] for i,row in enumerate(rows) if i == 0 or rows[i-1]['link'] != row['link']] for key,rows in histories.items()}
    print(json.dumps({'vehicles':vehicles,'link_paths':paths,'shared_initial_records':report['all_shared_initial_records'],'bytes_read':reader.bytes_read,'output':str(output),'source_changes':report['source_changes_during_probe']},ensure_ascii=False,indent=2))

if __name__ == '__main__': main()
