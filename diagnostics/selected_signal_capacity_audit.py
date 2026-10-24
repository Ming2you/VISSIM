"""Read-only installed capacity/measurement audit. No optimizer or simulator.

Usage: python -m diagnostics.selected_signal_capacity_audit --run <run-name>
Outputs are diagnostic JSON/CSV only; native clocks use a completed NC LSA.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from diagnostics.probe_model_area_integration import ROOT, adapter, build_projected

PREFIX = ROOT / 'diagnostics/selected_signal_capacity_audit'
NEMA = {'NBT':'p1','SBT':'p1','NBL':'p2','SBL':'p2','EBT':'p3','WBT':'p3','EBL':'p4','WBL':'p4'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def simple(value):
    if isinstance(value, dict):
        return {('|'.join(map(str,k)) if isinstance(k,tuple) else str(k)):simple(v) for k,v in value.items()}
    if isinstance(value, (tuple,list,set)):
        return [simple(v) for v in value]
    return value


def native_clocks(network, plan, start, end):
    from evaluation.controllers.fixed_signal_schedule import _union_green_overlap
    from plant.src.vissim_strict.signal_program import parse_sig
    lsa = ROOT/'evaluation/runs/codex_area_observed_nc_s13_20260910/vissim_eval/modi_eval_userfix Ver2_001.lsa'
    tree = ET.parse(network)
    programs, controllers, heads, pins = {}, {}, defaultdict(list), {str(network.relative_to(ROOT)):sha(network),str(lsa.relative_to(ROOT)):sha(lsa)}
    selected = set(plan['controllers'])
    for sc in tree.findall('./signalControllers/signalController'):
        key = sc.get('no')
        if key not in selected: continue
        path = network.parent/sc.get('supplyFile2').replace('#data#','')
        programs[key] = parse_sig(path,int(sc.get('progNo')))
        controllers[key] = {'SC':'SC'+key,'active':sc.get('active'),'type':sc.get('type'),'progNo':sc.get('progNo'),
                            'offset_sec':float(sc.get('offset')),'sig_file':str(path.relative_to(ROOT)),
                            'cycle_sec':programs[key].cycle_length_sec,'program_offset_sec':programs[key].program_offset_sec}
        pins[str(path.relative_to(ROOT))] = sha(path)
    for head in tree.findall('./signalHeads/signalHead'):
        sc,sg = head.get('sg').split(); link,lane = head.get('lane').split()
        if sc not in selected: continue
        phase = next((p for p,gs in plan['controllers'][sc]['phase_signal_groups'].items() if sg in map(str,gs)),None)
        heads[link].append({'head':head.get('no'),'SC':'SC'+sc,'sg':sg,'lane':int(lane),'pos':float(head.get('pos')),
                            'phase':phase,'writer_selected_sg':phase is not None,'all_vehicle_types':head.get('allVehTypes') == 'true'})
    events = defaultdict(list)
    with lsa.open(encoding='utf-8-sig',errors='replace') as stream:
        for line in stream:
            c = [v.strip() for v in line.split(';')]
            if len(c)<5 or c[2] not in selected: continue
            try:t=float(c[0])
            except ValueError:continue
            if t<=end:events[c[2],c[3]].append((t,c[4].upper()))
    sg_rows = {}
    for link,rows in heads.items():
        for h in rows:
            sc=h['SC'][2:];sg=h['sg'];key=(sc,sg)
            if key in sg_rows:continue
            ev=events[key]; prev=[(t,s) for t,s in ev if t<=start]
            if not prev:
                sg_rows[key]={'SC':'SC'+sc,'sg':sg,'lsa_green_seconds':None,'sig_green_seconds':None,
                              'dense_state_mismatches':[],'lsa_missing_start':True,'writer_selected_sg':h['writer_selected_sg']}
                continue
            current=prev[-1][1];i=0;green=0; mismatches=[]
            for sec in range(start,end):
                while i<len(ev) and ev[i][0]<=sec:current=ev[i][1];i+=1
                predicted=programs[sc].state_at(sec,sg,controller_offset_sec=controllers[sc]['offset_sec'])
                if predicted!=current:mismatches.append({'sec':sec,'lsa':current,'sig':predicted})
                green+=int(current=='GREEN')
            calculated=_union_green_overlap(programs[sc],(sg,),start,end,controllers[sc]['offset_sec'])
            sg_rows[key]={'SC':'SC'+sc,'sg':sg,'lsa_green_seconds':green,'sig_green_seconds':calculated,
                          'dense_state_mismatches':mismatches,'writer_selected_sg':h['writer_selected_sg']}
    links={}
    for link, rows in heads.items():
        sc=rows[0]['SC'][2:]
        if any(h['SC'][2:]!=sc for h in rows):raise ValueError('Multiple controllers on one link require a separate union')
        all_sgs=tuple(sorted({h['sg'] for h in rows})); selected_sgs=tuple(sorted({h['sg'] for h in rows if h['writer_selected_sg']}))
        union=lambda gs:_union_green_overlap(programs[sc],gs,start,end,controllers[sc]['offset_sec']) if gs else 0.
        lanes={lane:tuple(sorted({h['sg'] for h in rows if h['lane']==lane})) for lane in {h['lane'] for h in rows}}
        links[link]={'SC':'SC'+sc,'heads':rows,'native_all_head_union_green_sec':union(all_sgs),
                     'native_selected_head_union_green_sec':union(selected_sgs),
                     'native_all_head_lane_green_sec':sum(union(gs) for gs in lanes.values()),
                     'native_each_sg':{sg:sg_rows[sc,sg] for sg in all_sgs}}
    return {'interval':[start,end],'completed_nc_lsa':str(lsa.relative_to(ROOT)),'source_sha256':pins,
            'controllers':controllers,'signals':list(sg_rows.values()),'links':links,
            'missing_lsa_sg_count':sum(r.get('lsa_missing_start',False) for r in sg_rows.values()),
            'mismatch_sg_count':sum(bool(r['dense_state_mismatches']) or abs(r['lsa_green_seconds']-r['sig_green_seconds'])>1e-8 for r in sg_rows.values() if not r.get('lsa_missing_start'))}


def build(run):
    root=ROOT/'evaluation/runs'/run; decisions=root/('decisions_'+run)
    state_path=decisions/'state_000900.json'; previous=decisions/'action_000750.json';action_path=decisions/'action_000900.json'
    manifest_path=root/'area_candidate_source_manifest.json';manifest=read(manifest_path)
    config=ROOT/manifest['outputs']['0']['path']
    pinned={ROOT/k:v for k,v in manifest['source_sha256'].items()}
    pinned.update({ROOT/v['path']:v['sha256'] for v in manifest['outputs'].values()})
    if any(sha(p)!=v for p,v in pinned.items()):raise ValueError('Active source differs from run manifest')
    inputs={p:sha(p) for p in (state_path,previous,action_path,previous.with_suffix('.csv'),action_path.with_suffix('.csv'),config,manifest_path)}
    captured={}; stage_names={'install_movement_capacity_by_lanes','install_native_signal_structure','install_measured_movement_capacity'}
    def observe(frame,event,arg):
        if event!='return':return
        name=frame.f_code.co_name
        if name not in stage_names:return
        if Path(frame.f_code.co_filename).resolve()!=Path(adapter.__file__).resolve():return
        if name in stage_names:
            loc=frame.f_locals; cfg=loc['cfg']; row={'metadata':copy.deepcopy(arg),'caps':copy.deepcopy(cfg.network.movement_capacity_by_movement_veh_h)}
            if name=='install_measured_movement_capacity':
                for key in ('base_caps','seed','seed_lg','est','est_lg','green_sec','prev_est','departures','groups','_cap_geo'):
                    row[key]=copy.deepcopy(loc.get(key))
                row['specs']=copy.deepcopy(cfg.network.urban_movements)
            captured[name]=row
    before_profile=sys.getprofile();sys.setprofile(observe)
    try:cfg,state,detectors,tuning,raw,mapping,metadata=build_projected(config,state_path,previous,fixture_inputs=False)
    finally:sys.setprofile(before_profile)
    measured=captured['install_measured_movement_capacity'];base=captured['install_movement_capacity_by_lanes'];native=captured['install_native_signal_structure']
    action=read(action_path); previous_doc=read(previous)
    required_meta={k:v for k,v in metadata.items() if k.startswith(('measured_capacity','sat_est_','movement_capacity_by_lanes','movement_capacity_perimeter'))}
    mismatched={k:(v,action['metadata'].get(k)) for k,v in required_meta.items() if v!=action['metadata'].get(k)}
    if mismatched:raise AssertionError(('Runtime capacity metadata mismatch',mismatched))
    _,_,ControlAction,_,_,_=adapter.repo_imports(ROOT/'vendor/NumSim-mine')
    control=adapter.control_from_json(action_path,cfg,ControlAction)
    from src.models import urban_queue_model as uqm
    from src.controllers.local_signal_plant import build_local_model
    plan=adapter.load_signal_group_actuation_plan();selected=set(cfg.network.signals)
    phase_movements={s:{p:[] for p in ('p1','p2','p3','p4')} for s in selected}
    for m,sp in cfg.network.urban_movements.items():
        if sp['signal'] in selected:phase_movements[sp['signal']][sp['phase'].split('_')[-1]].append(m)
    local_caps={}
    for signal in selected:local_caps.update(build_local_model(cfg,signal,cfg.network.urban_movements,phase_movements).cap_flow_of)
    olinks=adapter._origin_links_by_signal();groups=measured['groups']; sigs={str(g['stopline_link']):str(g['signal']) for g in groups}
    sigs.update({k:v for k,v in adapter._SUS_SIGS.items() if k not in sigs})
    assignments=defaultdict(list); group_rows=[]
    for (link,pid),total in (measured['est_lg'] or {}).items():
        sig=sigs.get(link);origins=set(adapter._LTO.get(link,[]));members=[]
        for m,sp in measured['specs'].items():
            if (sp.get('signal')==sig and sp.get('phase','').endswith('_'+pid) and sp.get('kind') in (adapter._LG_KINDS or {'internal'})
                and (sp.get('origin') in origins or link in olinks.get(sig,{}).get(sp.get('origin'),set()))):members.append((m,max(0.,float(sp.get('beta',0)))))
        weight=sum(w for _,w in members) or len(members)
        for m,w in members:assignments[m].append({'link':link,'phase':pid,'group_service_veh_h':total,'beta_share':w/weight,'assigned_veh_h':total*w/weight})
        group_rows.append({'link':link,'signal':sig,'phase':pid,'seed_veh_h':measured['seed_lg'][link,pid],'service_veh_h':total,
                           'members':dict(members),'positive_members':sum(w>1e-9 for _,w in members)})
    authority=read(ROOT/'diagnostics/movement_signal_authority_audit.json')['movements']
    rows=[]
    corridor_turns=getattr(cfg.network,'route_choice_corridor',{}).get('turns',{})
    for m,sp in cfg.network.urban_movements.items():
        if sp.get('signal') not in selected:continue
        cap=cfg.network.movement_capacity_by_movement_veh_h.get(m);old=base['caps'].get(m)
        written=assignments.get(m,[]); measured_cap=measured['caps'].get(m)
        if m in corridor_turns:source='physical_corridor_single_turn_base_per_lane'
        elif written:source='measured_lane_group_assignment'
        elif measured_cap!=native['caps'].get(m):source='geometric_fallback'
        elif cap!=native['caps'].get(m):source='later_override'
        elif old is not None and cap==old:source='unchanged_normalized_lane_base'
        elif cap is None:source='global_scalar'
        elif sp.get('ramp') and cap==float(cfg.network.ramp_capacity_veh_h.get(sp['ramp'],0)):source='gate_onramp_capacity_override'
        else:source='normalized_base_with_native_factor'
        originlinks=sorted(set(olinks.get(sp['signal'],{}).get(sp.get('origin'),set()))|{lk for lk,orig in adapter._LTO.items() if sp.get('origin') in orig})
        audit=authority.get(m,{})
        physical_heads={h['head']:h for b in audit.get('branches',[]) for h in b.get('source_heads_before_branch',[]) if h['SC']==sp['signal']}
        row={'movement':m,'signal':sp['signal'],'phase':sp['phase'],'kind':sp.get('kind'),'beta':sp.get('beta',0),
             'origin':sp.get('origin'),'receiving_link':sp.get('receiving_link'),'projected_queue_veh':state.urban_movement_queue.get(m,0),
             'source_class':source,'initial_lane_base_veh_h':old,'before_measurement_veh_h':native['caps'].get(m),
             'after_measurement_veh_h':measured_cap,'final_capacity_veh_h':cap,'local_cached_capacity_veh_h':local_caps.get(m),
             'actual_control_capacity_veh_h':uqm._movement_capacity_flow(control,cfg,m,sp),
             'online_assignments':written,'origin_links':originlinks,'physical_local_heads_from_pinned_audit':list(physical_heads.values()),
             'authority_status':audit.get('contract_status'),'corridor_turn':corridor_turns.get(m)}
        rows.append(row)
    clock=native_clocks(ROOT/'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx',plan,750,900)
    shifted_clock=native_clocks(ROOT/'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx',plan,720,870)
    local=raw['local_observation'];fields=['link_departures_window','link_stopped_counts','link_counts','link_speeds_kph','link_stopped_counts_window_mean','link_stopped_counts_window_max']
    queries=set(measured['seed'])|set(measured['prev_est'])|set(measured['departures'])
    active_origin_queries={lk for r in rows if float(r['beta'])>1e-9 for lk in r['origin_links']}
    link_rows=[]
    for link in sorted(set(measured['est'])|{x for r in rows if float(r['beta'])>1e-9 for x in r['origin_links']}):
        green=measured['green_sec'].get(link,0.);depart=measured['departures'].get(link,0.)
        obs=depart/green*3600 if green>1 else 0.
        carried=.98*measured['prev_est'].get(link,measured['seed'].get(link,0.))
        mode='queued_ewma' if obs>0 and float(local['link_stopped_counts'].get(link,0))>=6 else 'observed_running_max' if obs>0 and obs>=carried else 'decayed_previous_or_seed'
        native_link=clock['links'].get(link)
        link_rows.append({'link':link,'estimated_service_veh_h':measured['est'].get(link),'previous_service_veh_h':measured['prev_est'].get(link),
                          'seed_service_veh_h':measured['seed'].get(link),'model_denominator_green_sec':green,'departures_count':depart,
                          'computed_observed_veh_h':obs,'update_path':mode,'stopped_snapshot':local['link_stopped_counts'].get(link),
                          'query_fields_missing':[f for f in fields if link not in local.get(f,{})],
                          'native_clock':native_link,'actual_departure_window_native_clock':shifted_clock['links'].get(link)})
    active=[r for r in rows if float(r['beta'])>1e-9]
    by_signal=[]
    for signal in sorted(selected):
        rr=[r for r in active if r['signal']==signal]
        by_signal.append({'signal':signal,'active_beta_positive':len(rr),'positive_queue':sum(r['projected_queue_veh']>1e-9 for r in rr),
                          'capacity_sources':dict(Counter(r['source_class'] for r in rr))})
    measured_head_groups=[]
    for g in group_rows:
        current_heads=clock['links'].get(g['link'],{}).get('heads',[])
        matching=[h for h in current_heads if h['phase']==g['phase'] and h['SC']==g['signal']]
        measured_head_groups.append({**g,'current_matching_heads':matching,'current_head_phase_missing':not matching})
    head_members=defaultdict(list)
    for row in active:
        for h in row['physical_local_heads_from_pinned_audit']:
            head_members[h['head']].append({'movement':row['movement'],'phase':row['phase'],'cap_veh_h':row['final_capacity_veh_h'],
                                           'queue_veh':row['projected_queue_veh'],'source_class':row['source_class'],
                                           'actual_local_head':h})
    shared_heads={h:r for h,r in head_members.items() if len(r)>1}
    physical_pools=defaultdict(list)
    for row in rows:
        if row['corridor_turn']:
            physical_pools[row['corridor_turn']['connector']].append(row)
    shared_turns=[]
    for connector,rr in physical_pools.items():
        if len(rr)<2:continue
        rates={float(r['corridor_turn']['service_veh_h']) for r in rr};assert len(rates)==1
        rate=next(iter(rates))
        shared_turns.append({'connector':connector,'movements':[r['movement'] for r in rr],
                             'each_canonical_capacity_veh_h':[r['final_capacity_veh_h'] for r in rr],
                             'global_shared_service_veh_h':rate,
                             'saturated_local_per_movement_budget_5s_sum':sum(r['local_cached_capacity_veh_h'] for r in rr)*5/3600,
                             'global_shared_service_budget_5s':rate*5/3600,
                             'scope':'Saturated all-GREEN algebra; not an observed interval flow. Local phased/ramp-aware steppers have no connector service pool.'})
    from evaluation.controllers.runtime_setup import install_worker_runtime
    worker_cfg=copy.deepcopy(cfg);worker_before=copy.deepcopy(worker_cfg.network.movement_capacity_by_movement_veh_h)
    install_worker_runtime(adapter,worker_cfg,raw,detectors)
    worker_capacity_unchanged=worker_before==worker_cfg.network.movement_capacity_by_movement_veh_h
    assert worker_capacity_unchanged
    header=['movement','signal','phase','kind','beta','projected_queue_veh','source_class','initial_lane_base_veh_h','final_capacity_veh_h','local_cached_capacity_veh_h','actual_control_capacity_veh_h']
    result={'schema':'selected-signal-capacity-audit/v1','run':run,'decision_sec':900,'previous_decision_sec':750,
            'scope':'Configuration/getter/clock audit only. No coupled endpoint, optimizer or VISSIM execution.',
            'input_sha256':{str(p.relative_to(ROOT)):v for p,v in inputs.items()},'run_source_count':len(pinned),
            'runtime_metadata_matches_actual_action':not mismatched,'capacity_tuning':tuning['urban']['capacity'],
            'installed_capacity_metadata':required_meta,'queue_window_samples':local.get('queue_window_samples'),
            'previous_controller':previous_doc['metadata'].get('controller'),
            'actual_departure_window_inferred_from_runner':[720,870],
            'actual_queue_sample_times_inferred_from_runner':[750,780,810,840,870],
            'native_interval_vs_departure_clock':'Requested 750-900 native clock is retained; STEPWISE decision resets before log, so raw900 departure comparisons actually span 720-870. Both are 150sec; no completed-NC raw900 window is reused.',
            'worker_reinstallation_capacity_unchanged':worker_capacity_unchanged,
            'summary':{'selected_signals':len(selected),'all_movements':len(rows),'active_beta_positive':len(active),
                       'all_capacity_sources':dict(Counter(r['source_class'] for r in rows)),
                       'active_capacity_sources':dict(Counter(r['source_class'] for r in active)),
                       'actual_capacity_vs_local_cache_differences':[r['movement'] for r in rows if r['local_cached_capacity_veh_h']!=r['actual_control_capacity_veh_h']],
                       'multiple_measured_assignments':[r['movement'] for r in rows if len(r['online_assignments'])>1],
                       'all_assignment_count':sum(len(r['online_assignments']) for r in rows),
                       'unique_measured_groups':len(group_rows),'groups_without_members':sum(not g['members'] for g in group_rows),
                       'link_update_paths':dict(Counter(r['update_path'] for r in link_rows if r['estimated_service_veh_h'] is not None))},
            'query_field_coverage':{f:{'query_links':len(queries),'missing_links':sorted(queries-set(local.get(f,{}))),'nonfinite_links':[k for k in queries if k in local.get(f,{}) and not math.isfinite(float(local[f][k]))],
                                       'mapping_origin_support_links_not_all_numeric_queries':len(active_origin_queries),'mapping_origin_support_outside_local_field':sorted(active_origin_queries-set(local.get(f,{}))),
                                       'physical_head_link_count':len(clock['links']),'physical_head_missing_links':sorted(set(clock['links'])-set(local.get(f,{})))} for f in fields},
            'by_signal':by_signal,'movements':rows,'measurement_groups':measured_head_groups,'measurement_links':link_rows,'native_clock':clock,
            'actual_departure_window_clock':shifted_clock,'physical_head_members_lower_bound_from_pinned_audit':shared_heads,'explicit_shared_turns':shared_turns}
    if any(sha(p)!=v for p,v in {**pinned,**inputs}.items()):raise AssertionError('Read-only audit changed source/input')
    result['all_source_and_input_bytes_unchanged']=True
    PREFIX.with_suffix('.json').write_text(json.dumps(simple(result),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with PREFIX.with_suffix('.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=header,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    print(json.dumps(result['summary'],ensure_ascii=False,indent=2));print('native clock mismatch SGs',clock['mismatch_sg_count'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',required=True)
    build(parser.parse_args().run)
