"""Separate cell22/23 flow and density-regime divergence using saved traces."""
import csv
import json
import time
from collections import Counter
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent
PINS={}


def read(p):
    PINS[str(p)]=h.sha(p)
    return h.read(p)


def native_csv(p):
    PINS[str(p)]=h.sha(p)
    with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))


def main():
    assert not (HERE/'status.json').exists(),'No automatic rerun'
    started=time.perf_counter();protected=read(h.R/'state_pressure146/protocol.json')
    assert read(h.R/'state_pressure146/status.json')['status']=='complete_rejected'
    h.save(HERE/'protocol.json',dict(previous_goal_turn='PROGRESS:146 fitted one current-state regime, completed9autonomous forecasts and rejected reversed RM/VSL responses.',
        question='Where do current self-generated22/23 density regimes first diverge: incoming mainline flow,10484 merge, downstream discharge or lateral concentration?',
        budget=dict(cached_arms=2,window_seconds=450,cells=[22,23],new_forecasts=0,fits=0,new_native=0,new_FZP=0),
        models=['frozen144','rejected146'],native='seed67 release and release_vsl90;2670.1..3120.1 cached5s frames, matched merge-event IDs and completed30s observations.',
        definitions='Whole-cell boundary counts include each crossed boundary between5s endpoints and known merge entry cells. Lane membership changes have explicit ambiguity when crossing and lane changing within5s; do not equate endpoint lane with exact boundary lane.',
        limits='Observed future transitions are labels/ledgers only. No real future inputs or resetting in any model. Differences in ledger terms are accounting, not isolated causal interventions.',
        protected_sha256=protected['protected_sha256'],STOP=protected['STOP'],source_sha256={str(Path(__file__)):h.sha(__file__)},
        prior_checked=['146 state pressure','137 current-state22-25 terms','134 population mixing','133 rejected accepted-flow convection','merge_speed_audit actual10484 boundaries','Claude upstream_worklog/07_fww_sc1001eb/fww-struct/FWW_STRUCT_CHECK.md']))
    h.save(HERE/'status.json',dict(status='running',phase='cached_flow_ledgers'))
    events=read(h.F/'merge_speed_audit/events.json')
    mapping=read(h.F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']
    bounds=mapping['segment_bounds_m'];lengths={i:(bounds[i+1]-bounds[i])/1000 for i in (22,23)}
    step_rows=[];windows=[];lane_windows=[];checks=Counter();max_error=0.;unknown=[];ambiguities=[]
    for arm in ('release','release_vsl90'):
        cache=read(h.F/'flow67'/f'{arm}_frames.json.gz');fields=cache['fields']
        frames={round(float(t),6):{str(vid):dict(zip(fields,z)) for vid,z in frame.items()} for t,frame in cache['frames'].items()}
        times=sorted(frames);assert len(times)==91 and times[0]==2670.1 and times[-1]==3120.1
        emap={(round(e['hi'],6),str(e['vehicle'])):e for e in events if e['arm']==arm and e['road']=='FW_E'}
        truth=h.I/'heldout67_freeway_20260930/observations'/arm
        flows={(round(float(x['window_end_s']),6),int(x['cell'])):x for x in native_csv(truth/'flows_30s.csv') if x['road']=='FW_E'}
        models={}
        for name,folder in [('frozen144',h.R/'spatial_speed144/audit_repair'),('rejected146',h.R/'state_pressure146/forecast')]:
            pred=read(folder/'training'/f's67_late_{arm}.json.gz')
            rows=pred['diagnostics']['roads'][0]['joint_lane_region']['rows']
            models[name]={(round(x['time_s'],6),x['cell'],x['lane']):x for x in rows}
        native=[]
        for lo,hi in zip(times,times[1:]):
            before,after=frames[lo],frames[hi];cross=Counter();merges=Counter();unexplained_in=Counter();unexplained_out=Counter()
            for vid in before.keys()&after.keys():
                a,b=before[vid],after[vid]
                assert b['cell']>=a['cell'],('reverse cell',vid,lo,a,b)
                for boundary in range(a['cell'],b['cell']):cross[boundary]+=1
                if a['lane']!=b['lane'] and a['cell']!=b['cell'] and (a['cell'] in (22,23) or b['cell'] in (22,23)):
                    ambiguities.append(dict(arm=arm,lo=lo,vehicle=vid,cell0=a['cell'],cell1=b['cell'],lane0=a['lane'],lane1=b['lane']))
            for vid in after.keys()-before.keys():
                b=after[vid];event=emap.get((hi,vid))
                if event is None:
                    if b['cell'] in (22,23):unexplained_in[b['cell']]+=1;unknown.append(dict(arm=arm,lo=lo,vehicle=vid,side='in',cell=b['cell']))
                    continue
                assert event['cell']<=b['cell'];merges[event['cell']]+=1
                for boundary in range(event['cell'],b['cell']):cross[boundary]+=1
            for vid in before.keys()-after.keys():
                a=before[vid]
                if a['cell'] in (22,23):unexplained_out[a['cell']]+=1;unknown.append(dict(arm=arm,lo=lo,vehicle=vid,side='out',cell=a['cell']))
            for cell in (22,23):
                a=[v for v in before.values() if v['cell']==cell];b=[v for v in after.values() if v['cell']==cell]
                error=len(b)-len(a)-cross[cell-1]+cross[cell]-merges[cell]-unexplained_in[cell]+unexplained_out[cell]
                assert error==0,(arm,lo,cell,error);checks['native5s_whole_cell']+=1
                q=dict(arm=arm,lo=lo,hi=hi,cell=cell,n0=len(a),n1=len(b),
                    incoming=cross[cell-1],outgoing=cross[cell],merge=merges[cell],unknown_in=unexplained_in[cell],unknown_out=unexplained_out[cell],
                    v0=sum(v['speed_kmh'] for v in a)/len(a) if a else None,v1=sum(v['speed_kmh'] for v in b)/len(b) if b else None,
                    measured_request_start=sum(v['speed_kmh'] for v in a)*5/(lengths[cell]*3600),
                    measured_request_trap=(sum(v['speed_kmh'] for v in a)+sum(v['speed_kmh'] for v in b))*2.5/(lengths[cell]*3600))
                native.append(q)
                for label,table in models.items():
                    initial=[table.get((lo,cell,lane)) for lane in (1,2,3)]
                    final=[table[(hi,cell,lane)] for lane in (1,2,3)]
                    interval=[table[(round(lo+j,6),cell,lane)] for j in range(1,6) for lane in (1,2,3)]
                    n0=sum(x['n_veh'] for x in initial) if all(initial) else len(a)
                    n1=sum(x['n_veh'] for x in final)
                    model=dict(n0=n0,n1=n1,incoming=sum(x['mainline_in_veh'] for x in interval),
                        outgoing=sum(x['mainline_out_veh'] for x in interval),merge=sum(x['merge_veh'] for x in interval),
                        v1=sum(x['n_veh']*x['v_kmh'] for x in final)/n1 if n1 else None)
                    residual=n1-n0-model['incoming']+model['outgoing']-model['merge']
                    assert abs(residual)<1e-8;max_error=max(max_error,abs(residual));checks['model5s_whole_cell']+=1
                    step_rows.append(dict(model=label,native=q,predicted=model,error_n=n1-len(b),error_speed=model['v1']-q['v1'] if model['v1'] is not None and q['v1'] is not None else None))
        for cell in (22,23):
            for k in range(15):
                lo=round(2670.1+k*30,6);hi=round(lo+30,6);rr=[r for r in native if r['cell']==cell and lo<=r['lo']<hi]
                assert len(rr)==6;truth_row=flows[hi,cell]
                for actual_key,csv_key in [('incoming','upstream_crossings'),('outgoing','downstream_crossings'),('merge','ramp_merges')]:
                    assert sum(x[actual_key] for x in rr)==float(truth_row[csv_key]),(arm,cell,lo,actual_key)
                    checks['native30s_flow_match']+=1
                assert rr[0]['n0']==float(truth_row['start_n_veh']) and rr[-1]['n1']==float(truth_row['end_n_veh'])
            for lo,hi in [(2670.1,2675.1),(2670.1,2700.1),(2670.1,2820.1),(2820.1,2970.1),(2970.1,3120.1)]:
                nn=[r for r in native if r['cell']==cell and lo-1e-6<=r['lo']<hi-1e-6]
                native_summary=dict(n0=nn[0]['n0'],n1=nn[-1]['n1'],v1=nn[-1]['v1'],**{key:sum(x[key] for x in nn) for key in ('incoming','outgoing','merge','measured_request_start','measured_request_trap')})
                for label in models:
                    rr=[x for x in step_rows if x['model']==label and x['native']['arm']==arm and x['native']['cell']==cell and lo-1e-6<=x['native']['lo']<hi-1e-6]
                    model_summary=dict(n0=rr[0]['predicted']['n0'],n1=rr[-1]['predicted']['n1'],v1=rr[-1]['predicted']['v1'],**{key:sum(x['predicted'][key] for x in rr) for key in ('incoming','outgoing','merge')})
                    error_terms=dict(start_stock=model_summary['n0']-native_summary['n0'],incoming=model_summary['incoming']-native_summary['incoming'],
                        outgoing=-(model_summary['outgoing']-native_summary['outgoing']),merge=model_summary['merge']-native_summary['merge'])
                    assert abs(sum(error_terms.values())-(model_summary['n1']-native_summary['n1']))<1e-7
                    windows.append(dict(arm=arm,model=label,cell=cell,lo=lo,hi=hi,native=native_summary,predicted=model_summary,error_terms=error_terms))
                    table=models[label]
                    for lane in (1,2,3):
                        n0=sum(x['cell']==cell and x['lane']==lane for x in frames[lo].values());n1=sum(x['cell']==cell and x['lane']==lane for x in frames[hi].values())
                        previous=table.get((lo,cell,lane));last=table[(hi,cell,lane)]
                        ml=[table[(round(lo+j,6),cell,lane)] for j in range(1,int(round(hi-lo))+1)]
                        incoming=sum(x['mainline_in_veh'] for x in ml);outgoing=sum(x['mainline_out_veh'] for x in ml);merge=sum(x['merge_veh'] for x in ml)
                        start=previous['n_veh'] if previous else n0
                        lane_windows.append(dict(arm=arm,model=label,cell=cell,lane=lane,lo=lo,hi=hi,native_n0=n0,native_n1=n1,
                            predicted_n0=start,predicted_n1=last['n_veh'],incoming=incoming,outgoing=outgoing,merge=merge,
                            model_net_lateral=last['n_veh']-start-incoming+outgoing-merge))
    assert not unknown,unknown
    for path,digest in {**PINS,**protected['protected_sha256']}.items():assert h.sha(path)==digest,path
    assert h.sha(protected['STOP']['path'])==protected['STOP']['sha256']
    h.save(HERE/'steps.json',step_rows);h.save(HERE/'windows.json',windows);h.save(HERE/'lane_windows.json',lane_windows)
    h.save(HERE/'boundary_lane_ambiguities.json',ambiguities)
    h.save(HERE/'verification.json',dict(checks=dict(checks),model_conservation_max=max_error,unexplained_entries_losses=unknown,
        boundary_lane_ambiguities=len(ambiguities),input_sha256=PINS,core=True,STOP=True))
    h.save(HERE/'status.json',dict(status='complete_cached_diagnostic',elapsed_sec=time.perf_counter()-started,new_forecasts=0,new_fits=0,new_native=0,new_FZP=0,goal='ACTIVE_NOT_QUALIFIED'))
    for x in windows:
        if x['arm']=='release' and x['lo']==2670.1 and x['hi'] in (2675.1,2700.1,2820.1):print(json.dumps(x))
    print('VERIFIED',dict(checks),'mass',max_error,'ambiguities',len(ambiguities))


if __name__=='__main__':
    try:main()
    except BaseException as exc:
        if not (HERE/'status.json').exists() or h.read(HERE/'status.json')['status']=='running':h.save(HERE/'status.json',dict(status='failed',error=repr(exc)))
        raise
