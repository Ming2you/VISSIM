"""Read-only native path/head audit of actual configured urban movements."""
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_geometry(root):
    links, heads, incoming = {}, defaultdict(list), defaultdict(list)
    for node in root.findall('./links/link'):
        key = node.get('no')
        points = [(float(p.get('x')),float(p.get('y')),float(p.get('zOffset',0))) for p in node.findall('./geometry/linkPolyPts/linkPolyPoint')]
        row = {'id':key,'lanes':len(node.findall('./lanes/lane')),'length_m':sum(math.dist(a,b) for a,b in zip(points,points[1:]))}
        a,b=node.find('fromLinkEndPt'),node.find('toLinkEndPt')
        if a is not None and b is not None:
            row.update(source=a.get('lane').split()[0],source_lane=int(a.get('lane').split()[1]),source_pos=float(a.get('pos')),
                       target=b.get('lane').split()[0],target_lane=int(b.get('lane').split()[1]),target_pos=float(b.get('pos')))
            incoming[row['target']].append(row)
        links[key]=row
    for node in root.findall('./signalHeads/signalHead'):
        link,lane=node.get('lane').split();sc,sg=node.get('sg').split()
        heads[link].append({'head':node.get('no'),'link':link,'lane':int(lane),'pos_m':float(node.get('pos')),
                            'SC':'SC'+sc,'SG':sg,'all_vehicle_types':node.get('allVehTypes')=='true',
                            'compliance':float(node.get('complRate',1))})
    return links,heads,incoming


def main():
    from diagnostics.probe_model_area_integration import build_projected
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    paths={k:ROOT/v for k,v in {
        'network':'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx',
        'contract':'diagnostics/control_area_route_contract_physical_routes.json',
        'config':'diagnostics/area_candidate_configs/n7_area_beta0.json',
        'support':'diagnostics/physical_projection_support_635_proposal.json',
        'physical_topology':'diagnostics/physical_movement_routes_ver2.json',
        'selected_plan':'outputs/signal_group_actuation_plan_mainline_20260825.json',
        'adapter':'evaluation/controllers/vissim_stackelberg_adapter.py',
        'clock':'evaluation/controllers/signal_actuation_contract.py'}.items()}
    paths['audit']=Path(__file__)
    folder=ROOT/'evaluation/runs/codex_area_beta0_retry_s13_20260910/decisions_codex_area_beta0_retry_s13_20260910'
    for sec in (900,1050,1200,1350):paths['actual_snapshot_'+str(sec)]=folder/f'state_{sec:06d}.json'
    paths['actual_previous_1050']=folder/'action_001050.json'
    before={k:sha(p) for k,p in paths.items()}
    os.environ['RW_OFFSET_WRITER']='experiment'
    cfg,state,_,_,_,_,_=build_projected(paths['config'],folder/'state_001200.json',folder/'action_001050.json')
    plan=adapter.load_signal_group_actuation_plan()
    assert adapter.signal_group_actuation_plan_path().resolve()==paths['selected_plan'].resolve()
    actual_frames={sec:load(paths['actual_snapshot_'+str(sec)])['vehicle_records']['records'] for sec in (900,1050,1200,1350)}
    root=ET.parse(paths['network']).getroot()
    links,heads,incoming=native_geometry(root)
    routes=[]
    for d in root.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'):
        for r in d.findall('./vehRoutSta/vehicleRouteStatic'):
            path=[d.get('link')]+[x.get('key') for x in r.findall('./linkSeq/intObjectRef')]
            if path[-1]!=r.get('destLink'):path.append(r.get('destLink'))
            routes.append({'id':d.get('no')+':'+r.get('no'),'path':path,'start_pos':float(d.get('pos')),
                           'all_vehicle_types':d.get('allVehTypes')=='true','routeChoiceMeth':d.get('routeChoiceMeth'),
                           'relFlow_raw':r.get('relFlow')})
    conflicts=list(root.findall('./conflictAreas/conflictArea'))
    contract=load(paths['contract'])
    results={}
    for name,spec in cfg.network.urban_movements.items():
        row=contract.get('movement:'+name,{})
        signal=spec.get('signal');phase=str(spec.get('phase','')).rpartition('_')[2]
        node=plan['controllers'].get(str(signal).removeprefix('SC'),{})
        expected_sgs=set(map(str,node.get('phase_signal_groups',{}).get(phase,[])))
        actuated_sgs={str(sg) for values in node.get('phase_signal_groups',{}).values() for sg in values}
        def relevant(h):
            return h['SC']==signal and (not node or h['SG'] in actuated_sgs)
        entry={'model_spec':dict(spec),'contract_status':row.get('status','absent'),
               'writer_controls_SC':bool(node),'expected_phase_SGs':sorted(expected_sgs),
               'writer_actuated_SGs':sorted(actuated_sgs),
               'actual1200_projected_movement_queue_veh':float(state.urban_movement_queue.get(name,0)),
               'configured_movement_capacity_veh_h':cfg.network.movement_capacity_by_movement_veh_h.get(name),
               'model_green_gated':bool(spec.get('phase')) and not bool(spec.get('unsignalized')),'branches':[]}
        if row.get('status') not in ('unique','same_transition'):
            entry['classification']='ambiguous_unresolved_physical_route';results[name]=entry;continue
        for turn in row.get('physical_turns',[]):
            path=turn.get('path') or [turn.get('from_link'),turn.get('connector'),turn.get('to_link')]
            branch_indices=[i for i,k in enumerate(path) if k in links and 'source' in links[k]]
            if not branch_indices:
                entry['branches'].append({'classification':'ambiguous_no_physical_connector','path':path});continue
            ci=branch_indices[0];conn=links[path[ci]];source=conn['source']
            triple=[source,conn['id'],conn['target']]
            matching=[]
            for route in routes:
                for j in range(len(route['path'])-2):
                    if route['path'][j:j+3]==triple:
                        if j==0 and route['start_pos']>conn['source_pos']:continue
                        matching.append((route,j+1));break
            own_source_heads=[h for h in heads[source] if h['SC']==signal]
            lanes=set(range(conn['source_lane'],conn['source_lane']+conn['lanes']))
            branch_head_evidence=[]
            for k in path[ci:]:
                branch_head_evidence.extend(h for h in heads[k] if relevant(h))
            source_before=[h for h in own_source_heads if h['pos_m']<=conn['source_pos'] and h['lane'] in lanes]
            source_after=[h for h in own_source_heads if h['pos_m']>conn['source_pos'] and h['lane'] in lanes]
            witnesses=[]
            for route,idx in matching:
                prior_heads=[];covered_segments=[];native_nonactuated_heads=[]
                for i,k in enumerate(route['path'][:idx]):
                    seg=links[k]
                    previous=links[route['path'][i-1]] if i else None
                    next_link=links[route['path'][i+1]]
                    low=route['start_pos'] if i==0 else previous.get('target_pos',0)
                    high=next_link.get('source_pos',seg['length_m'])
                    # Include pre-decision heads as a conservative ambiguity:
                    # a native route starting after a head does not prove bypass.
                    candidates=[h for h in heads[k] if relevant(h) and h['pos_m']<=high]
                    native_nonactuated_heads.extend(h for h in heads[k] if h['SC']==signal and not relevant(h) and h['pos_m']<=high)
                    prior_heads.extend(candidates)
                    passed=[h for h in candidates if low<=h['pos_m'] and h['all_vehicle_types'] and h['compliance']==1]
                    if seg['lanes']>0 and passed and {h['lane'] for h in passed}>=set(range(1,seg['lanes']+1)):
                        covered_segments.append({'link':k,'entry_pos':low,'exit_pos':high,'heads':passed})
                witnesses.append({'route_id':route['id'],'path_to_branch':route['path'][:idx+1],
                                  'applicable_all_types_static':route['all_vehicle_types'] and route['routeChoiceMeth']=='STATIC',
                                  'heads_before_branch_any_lane':prior_heads,'all_lane_controlled_segments':covered_segments,
                                  'native_same_SC_heads_not_actuated_by_selected_writer':native_nonactuated_heads})
            any_prior=any(w['heads_before_branch_any_lane'] for w in witnesses)
            all_routes_controlled=bool(witnesses) and all(w['all_lane_controlled_segments'] and w['applicable_all_types_static'] for w in witnesses)
            # Path-local authority: absence of this SC on every verified native
            # prefix and movement continuation proves bypass of that actuator,
            # not absence of car-following, yielding, downstream spillback.
            certainly_bypass=bool(witnesses) and not any_prior and not branch_head_evidence and not any(relevant(h) for h in source_before)
            if all_routes_controlled:classification='certainly_head_controlled'
            elif certainly_bypass:classification='certainly_bypasses_model_signal'
            else:classification='ambiguous_partial_lane_or_path_control'
            physical_sgs={h['SG'] for h in source_before if relevant(h)}
            active_conflicts=[dict(c.attrib) for c in conflicts if c.get('status')!='PASSIVE' and (c.get('link1') in path or c.get('link2') in path)]
            branch={'path':path,'first_connector':conn,'connector_source_lanes':sorted(lanes),
                    'source_heads_before_branch':source_before,'source_heads_after_branch':source_after,
                    'source_all_heads':heads[source],'heads_on_movement_continuation':branch_head_evidence,
                    'native_route_witnesses':witnesses,'classification':classification,
                    'physical_source_SGs':sorted(physical_sgs),
                    'source_head_phase_mismatch':bool(node and expected_sgs and physical_sgs) and not physical_sgs.issubset(expected_sgs),
                    'active_conflicts_on_declared_movement_path':active_conflicts,
                    'all_conflict_records_on_path':sum(c.get('link1') in path or c.get('link2') in path for c in conflicts),
                    'actual_snapshot_counts':{str(sec):{'connector_veh':sum(str(v['link_no'])==conn['id'] for v in records),
                        'source_lane_veh':sum(str(v['link_no'])==source and int(v['lane_no']) in lanes for v in records),
                        'source_lane_stopped_lt5':sum(str(v['link_no'])==source and int(v['lane_no']) in lanes and float(v['speed_kph'])<5 for v in records)}
                        for sec,records in actual_frames.items()},
                    'incoming_to_source_after_local_heads':[r for r in incoming[source] if source_before and max(h['pos_m'] for h in source_before)<r['target_pos']<conn['source_pos']]}
            entry['branches'].append(branch)
        classifications={b['classification'] for b in entry['branches']}
        entry['classification']=next(iter(classifications)) if len(classifications)==1 else 'ambiguous_mixed_branch_authority'
        if not classifications:entry['classification']='ambiguous_no_physical_branch'
        results[name]=entry
    after={k:sha(p) for k,p in paths.items()}
    assert before==after,'Audit inputs changed while reading'
    counts=Counter(r['classification'] for r in results.values())
    false_gates={k:r for k,r in results.items() if r['classification']=='certainly_bypasses_model_signal' and r['model_green_gated']}
    phase_mismatch={k:r for k,r in results.items() if any(b.get('source_head_phase_mismatch') for b in r['branches'])}
    priorities=[]
    for name,row in phase_mismatch.items():
        wrong=[b for b in row['branches'] if b.get('source_head_phase_mismatch')]
        disjoint=any(set(b['physical_source_SGs']).isdisjoint(row['expected_phase_SGs']) for b in wrong)
        priority='P1_disjoint_phase' if disjoint else 'P2_multiple_SGs_or_mixed_lanes'
        if row['classification']=='ambiguous_mixed_branch_authority':priority='P1_mixed_physical_branches'
        priorities.append({'movement':name,'priority':priority,'model_phase':row['model_spec'].get('phase'),
                           'expected_SGs':row['expected_phase_SGs'],'queue1200_veh':row['actual1200_projected_movement_queue_veh'],
                           'max_snapshot_connector_veh':max(x['connector_veh'] for b in wrong for x in b['actual_snapshot_counts'].values()),
                           'max_snapshot_source_lane_stopped_lt5':max(x['source_lane_stopped_lt5'] for b in wrong for x in b['actual_snapshot_counts'].values()),
                           'physical_branches':[{'connector':b['first_connector']['id'],'source_SGs':b['physical_source_SGs']} for b in wrong]})
    priorities.sort(key=lambda r:(r['priority'],-r['max_snapshot_connector_veh'],-r['max_snapshot_source_lane_stopped_lt5']))
    output={'schema':'physical-movement-signal-authority/v1','source_paths':{k:str(p) for k,p in paths.items()},
            'source_sha256':before,'active_movement_count':len(results),'classification_counts':dict(counts),
            'model_green_gated_bypass_count':len(false_gates),'model_green_gated_bypass_movements':sorted(false_gates),
            'source_lane_phase_mismatch_movements':sorted(phase_mismatch),'movements':results,
            'phase_mismatch_priority_actual_traffic':priorities,
            'writer_scope_counts':dict(Counter(r['classification'] for r in results.values() if r['writer_controls_SC'])),
            'scope':['Native physical path authority, not a green optimization or capacity fit.',
                     'For writer-controlled SCs only heads in the selected phase_signal_groups count as the green actuator; midblock-native SGs are explicitly excluded and recorded.',
                     'For SCs without a writer node, classification describes native same-SC heads only; this does not establish optimizer authority.',
                     'Certain controlled requires every matching native route prefix to traverse an applicable head section covering every road lane.',
                     'Certain bypass means no applicable head on any matching native prefix or declared movement continuation; indirect downstream interactions remain.',
                     'Static path proof is not an observed per-vehicle lane history; partial lane coverage remains ambiguous.',
                     'Active conflict records are listed; absence does not remove implicit merge/car-following/reduced-speed/priority behavior.']}
    target=ROOT/'diagnostics/movement_signal_authority_audit.json'
    target.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    csv_rows=[]
    for name,row in false_gates.items():
        for b in row['branches']:
            c=b['first_connector']
            csv_rows.append({'movement':name,'phase':row['model_spec']['phase'],'path':'>'.join(b['path']),
                'source_lanes':','.join(map(str,b['connector_source_lanes'])),'branch_pos_m':c['source_pos'],
                'next_same_lane_head_pos_m':min((h['pos_m'] for h in b['source_heads_after_branch']),default=None),
                'route_ids':','.join(w['route_id'] for w in b['native_route_witnesses']),
                'max_snapshot_connector_veh':max(r['connector_veh'] for r in b['actual_snapshot_counts'].values()),
                'active_conflict_ids':','.join(c['no'] for c in b['active_conflicts_on_declared_movement_path'])})
    for filename,rows in [('movement_signal_authority_bypass.csv',csv_rows),('movement_signal_phase_priority.csv',priorities)]:
        with (ROOT/'diagnostics'/filename).open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps({k:output[k] for k in ['active_movement_count','classification_counts','model_green_gated_bypass_count','model_green_gated_bypass_movements','source_lane_phase_mismatch_movements']},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
