"""Native entry/head timing versus existing forecasts; no forecast or FZP scan."""
import csv
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path

E=Path(__file__).resolve().parent;I=E.parent;L=E/'loss_onset2250'
O=L/'head10490_timing';O.mkdir(exist_ok=False)
D=Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
pins={}
def raw(p):
    b=p.read_bytes();pins[str(p)]=hashlib.sha256(b).hexdigest();return b
def read(p):
    b=raw(p);return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def close(a,b):assert abs(a-b)<1e-7,(a,b)
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
det=list(csv.DictReader(raw(I/'selected/obs150/obs150_detectors_v2.csv').decode('utf-8-sig').splitlines()))
det={role:[x for x in det if x['link']=='10490' and x['role']==role] for role in ('ramp_arrival','meter_head')}
assert all(len(v)==1 for v in det.values())
head_pos=float(det['meter_head'][0]['pos'])
rows={};bins=[]
for start in (2250,3600):
    stop=start+150
    states={t:read(D/f'state_{t:06d}.json') for t in (start,stop)}
    for t,s in states.items():
        v=s['vehicle_records'];assert v['complete'] and not v['unobservable_count']
        assert v['capture_sim_sec_before']==v['capture_sim_sec_after']==t
    chunk=states[stop]['obs150']['mer'];data=raw(D/chunk['chunk'])
    assert hashlib.sha256(data).hexdigest()==chunk['chunk_sha256']
    events=[json.loads(x) for x in data.decode('utf-8').splitlines()]
    observations={}
    for role,ds in det.items():
        no=int(ds[0]['dcp_no']);selected=[x for x in events if x[1]==no and x[2] is not None and start<=x[2]<stop]
        assert len({x[4] for x in selected})==len(selected)
        k=ds[0]['dcm_no']
        close(len(selected),states[stop]['obs150']['detectors'][k])
        close(len(selected),states[stop]['obs150']['detectors_cum'][k]-states[start]['obs150']['detectors_cum'][k])
        observations[role]={x[4]:x[2] for x in selected}
    vv={t:{v['veh_no']:v for v in s['vehicle_records']['records'] if v['link_no']==10490} for t,s in states.items()}
    assert all(v['position_m']>=1. for vs in vv.values() for v in vs.values())
    pre0={k:v for k,v in vv[start].items() if v['position_m']<=head_pos}
    pre1={k:v for k,v in vv[stop].items() if v['position_m']<=head_pos}
    # This preserves identities, not just counts: no unexplained entry/loss.
    native_set=(set(pre0)|set(observations['ramp_arrival']))-set(observations['meter_head'])
    assert native_set==set(pre1)
    assert set(observations['meter_head'])<=set(pre0)|set(observations['ramp_arrival'])
    cp=L/f'city_path/{start}_ps_all8_origincandidate'
    initial=read(cp/'ramp_initial.json');trace=read(cp/'trace.json.gz')
    metadata=initial['buffers']['RM_C10490']['metadata']
    travel=(head_pos-1.)/metadata['travel_speed_kmh']*3.6
    ma=[x for x in trace['transfers'] if x['target']=='ramp:RM_C10490' and x['end_sec']<=stop]
    mh=[x for x in trace['resources'] if x['kind']=='physical_ramp_head_service' and x['resource']=='RM_C10490:0' and x['end_sec']<=stop]
    assert len(mh)==150 and {x['source'] for x in ma}=={'movement:SC1001_W_to_onE'}
    start_model=initial['buffers']['RM_C10490']['snapshot']
    close(start_model['upstream_travelling_veh']+start_model['head_ready_veh'],len(pre0))
    b=trace['ramp_snapshots'][0]['buffers']['RM_C10490']
    model_pre=b['upstream_travelling_veh']+b['head_ready_veh']
    close(len(pre0)+sum(x['vehicles'] for x in ma)-sum(x['accepted_total_veh'] for x in mh),model_pre)
    retained=[]
    for vid,v in pre1.items():
        entry=observations['ramp_arrival'].get(vid)
        retained.append(dict(vehicle=vid,entry_sec=entry,age_sec=stop-entry if entry is not None else None,
            position_m=v['position_m'],speed_kph=v['speed_kph'],initial_prehead=vid in pre0,
            above_constant_travel=(stop-entry)>travel if entry is not None else None))
    completed=[dict(vehicle=vid,entry_sec=observations['ramp_arrival'][vid],head_sec=t,
        elapsed_sec=t-observations['ramp_arrival'][vid])
        for vid,t in observations['meter_head'].items() if vid in observations['ramp_arrival']]
    elapsed=[x['elapsed_sec'] for x in completed]
    initial_crossings=[dict(vehicle=vid,position_m=pre0[vid]['position_m'],initial_speed_kph=pre0[vid]['speed_kph'],
        head_sec=t,elapsed_sec=t-start,constant_speed_eta_sec=(head_pos-pre0[vid]['position_m'])/metadata['travel_speed_kmh']*3.6)
        for vid,t in observations['meter_head'].items() if vid in pre0]
    for end in range(start+10,stop+1,10):
        begin=end-10
        na=sum(begin<=t<end for t in observations['ramp_arrival'].values())
        nh=sum(begin<=t<end for t in observations['meter_head'].values())
        a=sum(x['vehicles'] for x in ma if begin<x['end_sec']<=end)
        h=sum(x['accepted_total_veh'] for x in mh if begin<x['end_sec']<=end)
        cap=sum(x['available_veh'] for x in mh if begin<x['end_sec']<=end)
        bins.append(dict(window_start=start,start_sec=begin,end_sec=end,native_arrival=na,model_arrival=a,
            native_head=nh,model_head=h,model_service_available=cap,
            native_pre=len(pre0)+sum(t<end for t in observations['ramp_arrival'].values())-sum(t<end for t in observations['meter_head'].values()),
            model_pre=len(pre0)+sum(x['vehicles'] for x in ma if x['end_sec']<=end)-sum(x['accepted_total_veh'] for x in mh if x['end_sec']<=end)))
    na=len(observations['ramp_arrival']);nh=len(observations['meter_head'])
    arrival_error=sum(x['vehicles'] for x in ma)-na;head_error=sum(x['accepted_total_veh'] for x in mh)-nh
    close(head_error,arrival_error+len(pre1)-model_pre)
    rows[start]=dict(native=dict(initial_pre=len(pre0),arrival=na,head=nh,final_pre=len(pre1)),
        model=dict(initial_pre=len(pre0),arrival=sum(x['vehicles'] for x in ma),head=sum(x['accepted_total_veh'] for x in mh),
        final_pre=model_pre,available_head_service=sum(x['available_veh'] for x in mh)),
        error_decomposition=dict(head=head_error,arrival=arrival_error,prehead_inventory=len(pre1)-model_pre),
        model_entry_detector_to_head_travel_sec=travel,native_retained_prehead=retained,
        completed_entry_head_pairs=completed,completed_travel_summary=dict(count=len(elapsed),
            min=min(elapsed),median=statistics.median(elapsed),max=max(elapsed)),
        initial_prehead_crossings=initial_crossings,
        native_late_arrivals_within_model_travel=sum(t>=stop-travel for t in observations['ramp_arrival'].values()),
        model_late_arrivals_within_model_travel=sum(x['vehicles'] for x in ma if x['end_sec']>stop-travel),
        source_movement='SC1001_W_to_onE',future_native_used_for_forecasting=False)
save(O/'verification.json',dict(status='complete_timing_audit',rows=rows,pins=pins,forecasts=0,new_native=0,
    fzp_scans=0,live_monitoring=0,fit=0,goal='ACTIVE/NOT_QUALIFIED',
    caveats=['Future MER events used only for retrospective diagnosis.',
        'Completed travel pairs are censored by the150s window; retained vehicle ages reported separately.',
        'Native events counted in[start,end); model transfers occur at interval ends, counted in(start,end].',
        'A head count smaller than available service is not evidence of lower saturation flow.']))
with (O/'timing_10s.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(bins[0]));w.writeheader();w.writerows(bins)
print(json.dumps({k:{q:v[q] for q in ('native','model','error_decomposition','model_entry_detector_to_head_travel_sec',
    'native_retained_prehead','completed_travel_summary','native_late_arrivals_within_model_travel',
    'model_late_arrivals_within_model_travel')} for k,v in rows.items()},ensure_ascii=False))
