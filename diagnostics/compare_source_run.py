"""Read-only spatial/temporal comparison of an area MPC run and observed NC.

Default mode reads completed CSV prefixes. --measure adds the existing full-FZP
Omega and connector measurement functions, only after a completed simulation.
All output stays in a new diagnostics directory; no simulator/model execution.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,re,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from diagnostics.audit_observed_nc_trajectory import episodes,sha
from diagnostics.compare_spatial_levers import onset,LINKS
from diagnostics.audit_area_live_actuation import read_csv_prefix,audit_interval,parse_commands
from diagnostics.signal_readback_cadence import strict_signal_trace,vsl_readback_matches
from evaluation.controllers.signal_timing_oracle import decisions_from_action_rows

DEFAULT_RUN='codex_area_sources_beta0_s13_20260910'
DEFAULT_REFERENCE='codex_area_observed_nc_s13_20260910'
MAPPING=ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'
MEMBERSHIP=ROOT/'diagnostics/control_area_membership.json'
NETWORK=ROOT/'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
CONTRACT={
    'schema':'source-run-comparison/v1','stock_cadence_sec':30,'decision_period_sec':150,
    'slow_episode':{'minimum_count_veh':5,'speed_below_kph':30,'minimum_elapsed_between_samples_sec':90,'minimum_consecutive_samples':4},
    'queue_onset':{'minimum_stopped_count_veh':10,'minimum_elapsed_between_samples_sec':300},
    'road_stock_integration':'Trapezoid over complete 30s observation grid; absent sparse positive rows are zero only at known observed timestamps.',
    'speed':'Vehicle-weighted mean over positive-count snapshots; empty cells masked, never counted as stopped congestion.',
    'connector_events':'Existing analyze_ramp_corridor.scan: ID departure from connector to any observed other link; unique direct source→target connector skips reported separately. Interior disappearance is not departure.',
    'connector_blocks':'Existing 150s destination-observation timestamp bins [start,end); first and final censored blocks excluded. Event intervals touching a decision boundary retain up to one recording-step alignment uncertainty.',
    'spillback':'Report physical connector stopped stock and simultaneous upstream road/cell queues. This association does not establish a continuous queue tail or causal spillback by itself.',
    'upstream_propagation':'First sustained slow onset of cell i compared with downstream i+1; positive lag is temporal ordering, not identified causal shockwave speed.',
    'actuation':'Actual action CSV against existing oracle plus complete one-second SG/ramp cadence; only the documented pair of identical immediate ramp rows at interval start is allowed. VSL requires both finite vehicle-class DSD readbacks and is not vehicle speed compliance.',
    'omega':'Existing measure_control_area, native FZP-only phase. TTT is union stock residence; observed exits and terminal inference separate; internal disappearance never rewarded.',
}

def write_json(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write_csv(path,rows):
    if not rows:return
    with path.open('w',encoding='utf-8',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def run_path(name):
    path=(ROOT/'evaluation/runs'/name).resolve()
    if path.parent!=(ROOT/'evaluation/runs').resolve():raise ValueError('Run must be a direct child of evaluation/runs')
    return path

def comparison_contract(target,reference):
    left,right=target.get('manifest',{}),reference.get('manifest',{})
    seed,network=left.get('seed'),left.get('network_sha256')
    result={'same_seed':seed is not None and seed==right.get('seed'),
        'same_network':bool(network) and network==right.get('network_sha256'),
        'same_last_observation':target.get('last_observed_sec')==reference.get('last_observed_sec')}
    result['eligible_matched_comparison']=result['same_seed'] and result['same_network']
    return result

def integrate(series,key):
    return sum((a[1][key]+b[1][key])*(b[0]-a[0])/7200 for a,b in zip(series,series[1:]))

def road_stats(link_rows,times,start,end,links):
    lookup={};bytime=defaultdict(set)
    for row in link_rows:
        t=float(row['sim_sec']);key=(t,str(row['link']))
        if key in lookup:raise ValueError('Duplicate physical link/timestamp')
        lookup[key]={k:float(row[k]) for k in ('count','stopped_count','mean_speed_kph')};bytime[t].add(str(row['link']))
    selected=[t for t in times if start<=t<=end];history=[t for t in times if 30<=t<=end]
    stats={};curves=[]
    for link in links:
        def series(ts):return [(t,lookup.get((t,str(link)),{'count':0.,'stopped_count':0.,'mean_speed_kph':0.})) for t in ts]
        seq=series(selected);past=series(history)
        countsum=sum(r['count'] for _,r in seq)
        slow=onset(past,lambda r:r['count']>=5 and r['mean_speed_kph']<30,90)
        queued=onset(past,lambda r:r['stopped_count']>=10,300)
        stats[str(link)]={'first_sustained_slow_sec':slow,'first_stopped10_300_sec':queued,
            'ttt_30s_veh_h':integrate(seq,'count'),'stopped_30s_veh_h':integrate(seq,'stopped_count'),
            'peak_stock_veh':max((r['count'] for _,r in seq),default=None),'peak_stopped_veh':max((r['stopped_count'] for _,r in seq),default=None),
            'vehicle_weighted_sample_speed_kph':sum(r['mean_speed_kph']*r['count'] for _,r in seq)/countsum if countsum else None,
            'sample_count':len(seq),'first_onset_is_before_requested_window':slow is not None and slow<start}
        curves.extend({'link':str(link),'sim_sec':t,**r} for t,r in seq)
    return stats,curves

def cell_stats(rows,start,end):
    groups=defaultdict(list);seen=set()
    for row in rows:
        if not 30<=float(row['sim_sec'])<=end:continue
        key=(row['model_link'],int(row['segment_index']),float(row['sim_sec']))
        if key in seen:raise ValueError('Duplicate cell/timestamp')
        seen.add(key);groups[(row['model_link'],int(row['segment_index']))].append(row)
    result={};curves=[]
    for (model,index),data in sorted(groups.items()):
        ordered=sorted(data,key=lambda r:float(r['sim_sec']));events=episodes(ordered);window=[r for r in ordered if start<=float(r['sim_sec'])<=end]
        seq=[(float(r['sim_sec']),{k:float(r[k]) for k in ('count','stopped_count','mean_speed_kph')}) for r in window]
        key=f'{model}:{index}'
        result[key]={'model_link':model,'index':index,'first_sustained_slow_sec':events[0]['start_sec'] if events else None,'episodes':events,
            'peak_stock_veh':max((float(r['count']) for r in window),default=None),'peak_stopped_veh':max((float(r['stopped_count']) for r in window),default=None),
            'minimum_nonempty_speed_kph':min((float(r['mean_speed_kph']) for r in window if int(r['count'])>=5),default=None),
            'ttt_30s_veh_h':integrate(seq,'count'),'stopped_30s_veh_h':integrate(seq,'stopped_count'),'samples':len(window)}
        curves.extend({'model_link':model,'index':index,'sim_sec':t,**values} for t,values in seq)
    propagation=[]
    for key,row in result.items():
        downstream=result.get(f"{row['model_link']}:{row['index']+1}")
        if downstream and row['first_sustained_slow_sec'] is not None and downstream['first_sustained_slow_sec'] is not None:
            lag=row['first_sustained_slow_sec']-downstream['first_sustained_slow_sec']
            propagation.append({'model_link':row['model_link'],'upstream_index':row['index'],'downstream_index':row['index']+1,
                'upstream_onset_sec':row['first_sustained_slow_sec'],'downstream_onset_sec':downstream['first_sustained_slow_sec'],
                'lag_sec':lag,'upstream_later_or_equal':lag>=0})
    return result,curves,propagation

def read_snapshot_series(run,end):
    out={'run':run.name,'status':'pending','sources':{},'pending':[]}
    if not run.is_dir():out['pending']=['Run directory is not available.'];return out,[],[],[]
    tables={}
    for prefix in ('state','bottleneck_links','bottleneck_segments'):
        path=run/f'{prefix}_{run.name}.csv'
        if not path.exists():out['pending'].append(path.name);continue
        table,source=read_csv_prefix(path,end);tables[prefix]=[r for r in table if float(r['sim_sec'])<=end];out['sources'][prefix]=source
    if len(tables)!=3:return out,[],[],[]
    state=tables['state'];times=sorted({float(r['sim_sec']) for r in state if float(r['sim_sec'])%30==0})
    out['last_observed_sec']=max((float(r['sim_sec']) for r in state),default=0);out['observed_30s_times']=times
    if not times:out['pending'].append('No completed 30-second observations');return out,[],[],[]
    for a,b in zip(times,times[1:]):
        if b-a!=30:raise ValueError(f'Missing observation interval in {run.name}: {a}→{b}')
    mapping=json.loads(MAPPING.read_text(encoding='utf-8-sig'))
    expected_cells=sum(len(x['segment_bounds_m'])-1 for x in mapping['freeway_model_links'].values())
    counts=Counter(float(r['sim_sec']) for r in tables['bottleneck_segments'])
    complete=[t for t in times if counts[t]==expected_cells]
    out['last_complete_spatial_sec']=max(complete,default=0.)
    out['incomplete_cell_frames_sec']=[t for t in times if counts[t]!=expected_cells]
    if any(t<out['last_complete_spatial_sec'] for t in out['incomplete_cell_frames_sec']):
        raise ValueError('Interior freeway observation frame is incomplete')
    manifests=list(run.glob('run_provenance_*.json'))
    if len(manifests)!=1:out['pending'].append('Exactly one run provenance required')
    else:
        manifest=json.loads(manifests[0].read_text(encoding='utf-8-sig'));out['manifest']={'seed':manifest.get('seed'),'controller':manifest.get('controller'),
            'sim_period_sec':manifest.get('sim_period_sec'),'network_sha256':manifest.get('files',{}).get('network',{}).get('sha256')}
        out['sources']['manifest']={'path':str(manifests[0]),'sha256':sha(manifests[0])}
    log=run/f'runlog_{run.name}.txt';logtext=log.read_text(encoding='utf-8-sig',errors='replace') if log.exists() else ''
    from scripts.analyze_control_run import execution_status
    out['execution']=execution_status(logtext,out['last_observed_sec'],end,[r.get('controller_status','') for r in state])
    if log.exists():out['sources']['log']={'path':str(log),'sha256':sha(log)}
    out['status']='complete' if out['execution']['completed_without_reported_errors'] else 'partial_or_failed'
    if out['status']=='complete' and out['incomplete_cell_frames_sec']:raise ValueError('Completed run has incomplete freeway frames')
    return out,state,tables['bottleneck_links'],tables['bottleneck_segments']

def signature_rows(rows):
    rows=list(rows)
    decisions=decisions_from_action_rows(rows)
    if len(decisions)>1:raise ValueError('One command signature requires a single decision time')
    controllers=decisions[0]['controllers'] if decisions else {}
    output={}
    for r in rows:
        kind=r['kind']
        if kind=='vsl':key=f"vsl:{r['id']}:{r['lane']}:{r['dsd_no']}";value={'speed_kph':float(r['speed_kph'])}
        elif kind=='ramp_meter':key=f"ramp:{r['id']}";value={'green_sec':float(r['green_sec'])}
        elif kind=='signal':
            sc=str(int(float(r['sc_no'])));plan=controllers[sc]
            # The physical cycle belongs to signal_sg.green_sec; offset is
            # encoded as `offset`. Neither has a *_sec CSV column.
            if plan['cycle_sec']<=0:raise ValueError('Signal axis lacks a physical SG cycle: '+sc)
            key=f"signal:{sc}";value={k:float(r[k]) for k in ('p1_green','p2_green','p3_green','p4_green')}
            value.update(cycle_sec=plan['cycle_sec'],offset_sec=plan['offset_sec'])
        else:continue
        if key in output:raise ValueError('Duplicate actuator signature key: '+key)
        output[key]=value
    return output

def lever_changes(current,previous):
    changes={key:[] for key in ('VSL','RM','green','offset','cycle')}
    if previous is None:return changes
    for key,values in current.items():
        old=previous.get(key,{})
        for field,value in values.items():
            if old.get(field)==value:continue
            kind='VSL' if key.startswith('vsl:') else 'RM' if key.startswith('ramp:') else 'offset' if field=='offset_sec' else 'cycle' if field=='cycle_sec' else 'green'
            row={'actuator':key,'field':field,'before':old.get(field),'after':value}
            if kind=='offset' and field in old and old.get('cycle_sec')==values.get('cycle_sec'):
                cycle=values['cycle_sec'];row['wrapped_delta_sec']=(value-old[field]+cycle/2)%cycle-cycle/2
            changes[kind].append(row)
    return changes

def command_timeline(run,start,end):
    dec=run/('decisions_'+run.name);timeline=[];sources={};previous=None
    for path in sorted(dec.glob('action_*.csv')):
        t=int(path.stem.rsplit('_',1)[1])
        if t>end:continue
        data=path.read_bytes()
        import io
        rows=list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))));signature=signature_rows(rows)
        if previous is None:changed={key:value for key,value in signature.items()}
        else:changed={key:value for key,value in signature.items() if previous.get(key)!=value}
        if t>=start or previous is None:
            timeline.append({'sim_sec':t,'positive_control_duration_sec':max(0,min(end,t+150)-max(start,t)) if t>=start else 0,
                'changed_from_previous_counts':dict(Counter(k.split(':',1)[0] for k in changed)),
                'changed_keys':sorted(changed),'lever_changes':lever_changes(signature,previous),
                'first_observed_command':previous is None,'signature':signature,'zero_duration_final_command':t==end})
        previous=signature;sources[str(path.relative_to(ROOT))]=sha(path)
    return timeline,sources

def area_actuation(run,start,end,reference=None,expected_area=True):
    if not expected_area:return {'status':'native_baseline','intervals':[],'reason':'Native NC has no area MPC scoring contract.'}
    dec=run/('decisions_'+run.name);paths=sorted(dec.glob('action_*.json'))
    paths=[p for p in paths if start<=int(p.stem.rsplit('_',1)[1])<end]
    if not paths:return {'status':'pending','intervals':[],'reason':'Area decisions are not yet available.'}
    tracepath=dec/'signal_readback.csv';actionpath=run/f'action_{run.name}.csv'
    if not tracepath.exists() or not actionpath.exists():return {'status':'pending','intervals':[],'reason':'Actual readback/action log is not yet present.'}
    trace=read_csv_prefix(tracepath,end);actions=read_csv_prefix(actionpath,end)
    intervals=[]
    # Missing intermediate decisions must remain visible; iterating only the
    # files present would silently skip a failed controller step.
    for t in range(start,end,150):
        result=audit_interval(run,t,t+150,reference if t==start else None,trace,actions)
        command_path=dec/f'action_{t:06d}.csv'
        if 'actuation_trace' in result and command_path.is_file():
            _,controllers,ramps=parse_commands(command_path.read_bytes(),t)
            apply_strict_readback(result,trace[0],actions[0],controllers,ramps,t,t+150)
        intervals.append(result)
    return {'status':'fail' if any(x['status']=='fail' for x in intervals) else 'pending' if any(x['status']=='pending' for x in intervals) else 'pass',
        'status_counts':dict(Counter(x['status'] for x in intervals)),'intervals':intervals}

def apply_strict_readback(result,trace_rows,applied_rows,controllers,ramps,start,end):
    """Tighten the historical oracle without changing the pinned old audit."""
    strict=strict_signal_trace(trace_rows,controllers,ramps,start=start,end=end)
    result['actuation_trace']=strict
    cadence=strict['strict_one_second_cadence']
    malformed=bool(cadence['invalid_timestamp_rows']) or any(row['duplicate_seconds'] or row['unexpected_seconds'] for row in cadence['problems'])
    if not cadence['valid']:
        if strict['interval_complete'] or malformed:
            result['status']='fail';result.setdefault('failures',[]).append('Exact one-second signal/ramp readback cadence failed.')
        elif result['status']!='fail':
            result['status']='pending';result['pending_reason']='Complete one-second SG/ramp readback grid is not yet available.'
    applied=[row for row in applied_rows if float(row['sim_sec'])==start and row['kind']=='vsl']
    bad=[row for row in applied if not vsl_readback_matches(row)]
    result['strict_vsl_readback']={'required_finite_vehicle_class_values':2,'rows_checked':len(applied),'invalid_rows':len(bad)}
    if bad:
        result['status']='fail';result.setdefault('failures',[]).append('Both finite VSL vehicle-class readbacks must match the command.')

def measurement(run,output,enabled,end):
    """Reuse canonical measurement code; always write into diagnostics."""
    output.mkdir(parents=True,exist_ok=True)
    if not enabled:return {'status':'pending','reason':'Use --measure after completion for full FZP Omega and connector accounting.'}
    from scripts.measure_control_area import main as area_main
    area_main(['--run',str(run),'--fzp-only','--end-sec',str(end),'--out',str(output)])
    from scripts.analyze_ramp_corridor import scan
    fzp=list(run.glob('vissim_eval/*.fzp'))
    if len(fzp)!=1:raise ValueError('One complete FZP required')
    stat=fzp[0].stat();frame,meta=scan(fzp[0],NETWORK)
    if (stat.st_size,stat.st_mtime_ns)!=(fzp[0].stat().st_size,fzp[0].stat().st_mtime_ns):raise ValueError('FZP changed during connector scan')
    frame.to_csv(output/'physical_connector_passages.csv',index=False);write_json(output/'physical_connector_passages_metadata.json',meta)
    metrics=json.loads((output/'area_metrics.json').read_text(encoding='utf-8'));return {'status':'complete','area_metrics':metrics,'connector_metadata':meta,
        'path':str(output),'sources':{name:sha(output/name) for name in ('area_metrics.json','physical_connector_passages.csv','physical_connector_passages_metadata.json')}}

def passage_summary(directory,start,end):
    with (directory/'physical_connector_passages.csv').open(encoding='utf-8') as stream:table=list(csv.DictReader(stream))
    result={};last_complete=end-150
    for conn in sorted({r['connector'] for r in table}):
        own=[r for r in table if r['connector']==conn and start<=float(r['start_sec']) and float(r['end_sec'])<=last_complete]
        if not own:continue
        duration=sum(float(r['end_sec'])-float(r['start_sec']) for r in own)
        result[conn]={'source':own[0]['source_link'],'target':own[0]['target_link'],'window_sec':[start,last_complete],
            'departures_observed_veh':sum(float(r['departures_observed']) for r in own),'departures_inferred_veh':sum(float(r['departures_inferred']) for r in own),
            'arrival_events_veh':sum(float(r['arrival_events']) for r in own),'discharge_vph':sum(float(r['departures_total']) for r in own)*3600/duration,
            'mean_vehicles':sum(float(r['mean_vehicles'])*(float(r['end_sec'])-float(r['start_sec'])) for r in own)/duration,
            'mean_stopped':sum(float(r['mean_stopped'])*(float(r['end_sec'])-float(r['start_sec'])) for r in own)/duration}
    return result

def area_window_summary(directory,start,end):
    """Slice canonical cumulative residence and event rows; do not infer new exits."""
    with (directory/'area_timeseries.csv').open(encoding='utf-8') as stream:rows=list(csv.DictReader(stream))
    endpoints={float(row['sim_sec']):row for row in rows if float(row['sim_sec']) in (start,end)}
    if end not in endpoints or (start!=0 and start not in endpoints):raise ValueError('Exact Omega window endpoints unavailable')
    selected=[row for row in rows if start<float(row['sim_sec'])<=end]
    previous=start
    for row in selected:
        sec=float(row['sim_sec'])
        if not math.isclose(sec-previous,float(row['interval_sec']),abs_tol=1e-9):raise ValueError('Omega window has a missing interval')
        previous=sec
    metrics={'window_sec':[start,end],
        'ttt_veh_h':float(endpoints[end]['ttt_veh_h_cumulative'])-(float(endpoints[start]['ttt_veh_h_cumulative']) if start else 0.),
        'initial_inside_vehicles':int(endpoints[start]['inside_vehicles']) if start else 0,
        'final_inside_vehicles':int(endpoints[end]['inside_vehicles']),
        'event_timing':'Canonical event rows whose destination timestamp is in (start,end]; crossing within its recording interval is not known exactly.'}
    for key in ('observed_exit_events','terminal_exit_inferred_events','unresolved_inside_disappearances','observed_entry_events','appeared_inside_events'):
        metrics[key]=sum(int(row[key]) for row in selected)
    metrics['ttd_observed_plus_terminal_events']=metrics['observed_exit_events']+metrics['terminal_exit_inferred_events']
    metrics['sampled_stock_closure_residual_veh']=metrics['final_inside_vehicles']-metrics['initial_inside_vehicles']-metrics['observed_entry_events']-metrics['appeared_inside_events']+metrics['ttd_observed_plus_terminal_events']+metrics['unresolved_inside_disappearances']
    if metrics['sampled_stock_closure_residual_veh']:raise AssertionError('Canonical area window stock closure failed')
    return metrics

def comparison_values(target,reference):
    deltas={}
    for key,row in target.items():
        if key not in reference:continue
        pairs={}
        for field,value in row.items():
            other=reference[key].get(field)
            if isinstance(value,(int,float)) and not isinstance(value,bool) and isinstance(other,(int,float)) and not isinstance(other,bool):pairs[field]=value-other
        deltas[key]=pairs
    return deltas

def focus_window(run,start,end,output):
    """Existing indexed E8 event definitions plus observed stopped positions."""
    import time
    from diagnostics.probe_e8_lane_receiving import IndexedFzp
    from diagnostics.probe_e8_window_passages import frames,Geometry,transitions,event_summary,inventory
    evidence_path=ROOT/'diagnostics/e8_lane_receiving_evidence.json';evidence=json.loads(evidence_path.read_text(encoding='utf-8'))
    geometry=Geometry(evidence);files=list(run.glob('vissim_eval/*.fzp'))
    if len(files)!=1:raise ValueError('Focus requires exactly one completed FZP')
    path=files[0];stat=path.stat();reader=IndexedFzp(path,max_bytes=192*1024*1024);provenance=[];events=[];samples=[]
    previous=None;first=None;last=None;membership=Counter();started=time.monotonic()
    try:
        for sec,current in frames(reader,start,end,started+55,provenance):
            inv=inventory(geometry,current)
            if previous is not None:
                before,before_inv,prev_sec=previous
                if sec-prev_sec!=1:raise ValueError('Focus requires consecutive 1s recorded frames')
                for region,ids in inv.items():membership[(region,'entries')]+=len(ids-before_inv[region]);membership[(region,'exits')]+=len(before_inv[region]-ids)
                for no in before.keys()&current.keys():
                    a,b=before[no],current[no]
                    if a[0] in geometry.offsets or b[0] in geometry.offsets or a[0] in geometry.connectors or b[0] in geometry.connectors:
                        events.extend(transitions(geometry,no,a,b,prev_sec,sec))
            if first is None:first=(sec,inv)
            for conn in (10639,10682):
                own=[r for r in current.values() if r[0]==conn];stopped=[r for r in own if r[3]<5]
                for lane in sorted({r[1] for r in own} or {1}):
                    lane_rows=[r for r in own if r[1]==lane];slow=[r for r in stopped if r[1]==lane]
                    samples.append({'sim_sec':sec,'connector':conn,'lane':lane,'count':len(lane_rows),'stopped_below5':len(slow),
                        'mean_speed_kph':sum(r[3] for r in lane_rows)/len(lane_rows) if lane_rows else None,
                        'minimum_stopped_front_position_m':min((r[2] for r in slow),default=None),'maximum_stopped_front_position_m':max((r[2] for r in slow),default=None)})
            previous=(current,inv,sec);last=(sec,inv)
    finally:reader.handle.close()
    if first is None or first[0]!=start or last[0]!=end:raise ValueError('Focus endpoints unavailable')
    if (stat.st_size,stat.st_mtime_ns)!=(path.stat().st_size,path.stat().st_mtime_ns):raise ValueError('FZP changed during focus read')
    closure={region:{'initial_veh':len(ids),'final_veh':len(last[1][region]),'membership_entries_veh':membership[(region,'entries')],
        'membership_exits_veh':membership[(region,'exits')],'sampled_identity_residual_veh':len(last[1][region])-len(ids)-membership[(region,'entries')]+membership[(region,'exits')]} for region,ids in first[1].items()}
    if any(r['sampled_identity_residual_veh'] for r in closure.values()):raise AssertionError('Focus sampled identity closure')
    report={'schema':'source-run-focus/v1','run':run.name,'interval_sec':[start,end],'events':event_summary(events,start,end),'sampled_membership':closure,
        'queue_definition':'SPEED<5km/h; min/max stopped vehicle front positions by physical connector lane. This occupied extent does not prove a continuous queue or its cause.',
        'event_definition':'Existing probe_e8_window_passages.transitions/event_summary: observed versus unique skipped connector events, interval brackets and estimated counts remain separate.',
        'provenance':{'path':str(path.relative_to(ROOT)),'file_bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns,'bytes_read':reader.bytes_read,'ranges':provenance,
            'evidence_sha256':sha(evidence_path),'geometry':geometry.connectors}}
    write_json(output/f'focus_{start}_{end}.json',report);write_csv(output/f'focus_{start}_{end}_stopped_positions.csv',samples)
    return report

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run',default=DEFAULT_RUN);ap.add_argument('--reference',default=DEFAULT_REFERENCE)
    ap.add_argument('--start',type=int,default=900);ap.add_argument('--end',type=int,default=5400);ap.add_argument('--measure',action='store_true')
    ap.add_argument('--focus-window',action='append',default=[],metavar='START:END',help='Optional completed-run 1s E8/10639/10682 interval, maximum300s; may repeat.')
    ap.add_argument('--preflight-reference',type=Path);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args(argv)
    if args.start<0 or args.end<=args.start or args.start%150 or args.end%150:ap.error('Use increasing 150-second grid boundaries')
    focus=[tuple(map(int,x.split(':'))) for x in args.focus_window]
    if any(len(w)!=2 or w[0]<0 or w[1]<=w[0] or w[1]-w[0]>300 or w[1]>args.end for w in focus):ap.error('Focus needs increasing endpoints within end and duration≤300s')
    out=(ROOT/args.out).resolve()
    if (ROOT/'diagnostics').resolve() not in out.parents:ap.error('Output must stay under diagnostics')
    out.mkdir(parents=True,exist_ok=True)
    source_paths=[Path(__file__),ROOT/'diagnostics/audit_observed_nc_trajectory.py',ROOT/'diagnostics/compare_spatial_levers.py',
        ROOT/'diagnostics/audit_area_live_actuation.py',ROOT/'diagnostics/live_beta0_first_interval_audit.py',ROOT/'scripts/analyze_control_run.py',
        ROOT/'diagnostics/signal_readback_cadence.py',
        ROOT/'evaluation/controllers/signal_timing_oracle.py',ROOT/'evaluation/controllers/action_csv_schema.py',
        ROOT/'scripts/analyze_ramp_corridor.py',ROOT/'scripts/measure_control_area.py',MAPPING,MEMBERSHIP,NETWORK]
    if focus:source_paths += [ROOT/'diagnostics/probe_e8_window_passages.py',ROOT/'diagnostics/probe_e8_lane_receiving.py',ROOT/'diagnostics/e8_lane_receiving_evidence.json']
    before={str(p.relative_to(ROOT)):sha(p) for p in source_paths};runs={};curves=[];cellcurves=[];rawtables={}
    for label,name in [('reference',args.reference),('target',args.run)]:
        run=run_path(name);record,state,links,cells=read_snapshot_series(run,args.end);runs[label]=record
        if not state:continue
        rawtables[label]=(links,cells)
        last=min(args.end,record['last_complete_spatial_sec']);times=record['observed_30s_times'];end=30*math.floor(last/30)
        requested=list(map(str,LINKS));record['road_stats'],roads=road_stats(links,times,args.start,end,requested)
        record['cell_stats'],cs,record['upstream_onset_pairs']=cell_stats(cells,args.start,end)
        curves.extend({'run':label,**r} for r in roads);cellcurves.extend({'run':label,**r} for r in cs)
        record['commands'],command_sources=command_timeline(run,args.start,args.end);record['command_sources']=command_sources
        expected_area=record.get('manifest',{}).get('controller') not in ('no-control','none','uncontrolled')
        record['actuation']=area_actuation(run,args.start,args.end,args.preflight_reference if label=='target' else None,expected_area)
        record['measurement']=measurement(run,out/label,args.measure and record['status']=='complete',args.end)
        if record['measurement']['status']=='complete':
            record['passages']=passage_summary(out/label,args.start,args.end)
            record['area_window']=area_window_summary(out/label,args.start,args.end)
        record['focus']=[focus_window(run,a,b,out/label) for a,b in focus] if record['status']=='complete' else []
    completed=all(x['status']=='complete' and not x.get('pending') for x in runs.values());available=all('road_stats' in x for x in runs.values())
    target,reference=runs['target'],runs['reference']
    comparability=comparison_contract(target,reference);ready=completed and comparability['eligible_matched_comparison']
    result={'schema':CONTRACT['schema'],'contract':CONTRACT,'requested_window_sec':[args.start,args.end],'runs':runs,
        'status':'complete' if ready and args.measure else 'csv_ready_measurement_pending' if ready else 'incomparable_sources' if completed else 'pending_or_partial',
        'physical_comparison_ready':ready,'full_measurement_ready':ready and args.measure,
        'comparability':comparability,
        'source_sha256':before,'source_changes':[p for p,h in before.items() if sha(ROOT/p)!=h],
        'performance_claim':'None. Multilever policy changes require the command/readback checks and physical outcomes together; associations do not isolate a cause.'}
    if available:
        common_end=min(target['last_complete_spatial_sec'],reference['last_complete_spatial_sec'],args.end)
        result['common_completed_window_sec']=[args.start,common_end]
        result['common_window_comparison_ready']=common_end>args.start and comparability['eligible_matched_comparison']
        if result['common_window_comparison_ready']:
            common={}
            for label,record in runs.items():
                road,_=road_stats(rawtables[label][0],record['observed_30s_times'],args.start,common_end,list(map(str,LINKS)))
                cell,_,_=cell_stats(rawtables[label][1],args.start,common_end);common[label]={'roads':road,'cells':cell}
            result['target_minus_reference']={'roads':comparison_values(common['target']['roads'],common['reference']['roads']),
                'cells':comparison_values(common['target']['cells'],common['reference']['cells'])}
            if all('area_window' in record for record in runs.values()):
                result['target_minus_reference']['area_window']=comparison_values({'omega':target['area_window']},{'omega':reference['area_window']})['omega']
        reference_commands=reference.get('commands',[])
        result['target_command_changes_vs_reference']=[]
        for row in target.get('commands',[]):
            priors=[x for x in reference_commands if x['sim_sec']<=row['sim_sec']]
            if priors:result['target_command_changes_vs_reference'].append({'sim_sec':row['sim_sec'],
                'reference_command_sec':priors[-1]['sim_sec'],'lever_changes':lever_changes(row['signature'],priors[-1]['signature'])})
    write_json(out/'comparison.json',result);write_json(out/'measurement_contract.json',CONTRACT)
    write_csv(out/'road_curves.csv',curves);write_csv(out/'cell_curves.csv',cellcurves)
    lines=[f"Run comparison: {args.run} versus {args.reference}",'',f"Status: {result['status']}.",
        f"Requested interval: {args.start}–{args.end}s. Source changes during analysis: {result['source_changes']}.",'']
    for label,run in runs.items():
        lines.append(f"{label}: {run['status']}; last observation {run.get('last_observed_sec','unavailable')}s.")
        lines+=run.get('pending',[])
        if run.get('actuation'):lines.append(f"Actuation: {run['actuation']['status']}.")
        if run.get('measurement'):lines.append(f"FZP measurement: {run['measurement']['status']}.")
    lines+=['','No result is invented for missing data. Full Omega/connector metrics require --measure after completion.',
        'Native NC has no area objective decisions; its missing area-scoring flags are not an error. Zero optimized offsets are legitimate.',
        'Cell speed, physical connector queues and command readback are separate observations. DSD readback does not prove vehicle speed compliance.']
    (out/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'physical_comparison_ready':ready,'full_measurement_ready':result['full_measurement_ready'],'out':str(out),'source_changes':result['source_changes']}))
    return 0

if __name__=='__main__':raise SystemExit(main())
