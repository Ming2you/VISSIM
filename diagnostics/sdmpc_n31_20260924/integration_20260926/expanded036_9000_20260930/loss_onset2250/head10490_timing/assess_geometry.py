"""Score initial-geometry timing against existing native first150s records."""
import csv
import gzip
import hashlib
import json
import sys
from pathlib import Path

O=Path(__file__).resolve().parent;L=O.parent;I=L.parent.parent
AT=int(sys.argv[1]);assert AT in (2250,3600);END=AT+150
D=Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
pins={}
def read(p):
    b=p.read_bytes();pins[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def close(a,b):assert abs(a-b)<1e-7,(a,b)
native={t:read(D/f'state_{t:06d}.json') for t in (AT,END)}
det=list(csv.DictReader((I/'selected/obs150/obs150_detectors_v2.csv').read_text(encoding='utf-8-sig').splitlines()))
base_folder=I/f'closedloop_recorded{AT}_lever450_RM_C10484_city{AT}_ps_all8_origincandidate'
new_folder=I/f'closedloop_recorded{AT}_lever450_RM_C10484_city{AT}_ps_all8_geotimecandidate'
base,new=[read(p/'held_actual.json') for p in (base_folder,new_folder)]
assert base['commands']==new['commands']
assert base['physical_cell_states'][0]==new['physical_cell_states'][0]
start,end=native[AT],native[END]
for t,s in native.items():
    e=s['vehicle_records'];assert e['complete'] and not e['unobservable_count']
    assert e['capture_sim_sec_before']==e['capture_sim_sec_after']==t
case={};maxres=0.
for label,name in (('before','origincandidate'),('candidate','geotimecandidate')):
    folder=L/f'city_path/{AT}_ps_all8_{name}'
    trace=read(folder/'trace.json.gz');initial=read(folder/'ramp_initial.json')
    rows={}
    for ramp,n0 in initial['queue'].items():
        link=int(ramp.removeprefix('RM_C'));snap=trace['ramp_snapshots'][0]['buffers'][ramp]
        nativevehicles=[[v for v in s['vehicle_records']['records'] if v['link_no']==link] for s in (start,end)]
        ns=list(map(len,nativevehicles));close(ns[0],n0)
        dd={role:[x for x in det if x['link']==str(link) and x['role']==role] for role in ('ramp_arrival','meter_head')}
        def count(ds):
            total=0.
            for x in ds:
                k=x['dcm_no'];val=end['obs150']['detectors'][k]
                close(val,end['obs150']['detectors_cum'][k]-start['obs150']['detectors_cum'][k]);total+=val
            return total
        positions={int(x['lane']):float(x['pos']) for x in dd['meter_head']}
        post=[sum(v['position_m']>positions[v['lane_no']] for v in vv) for vv in nativevehicles]
        tiny=[sum(v['position_m']<1. for v in vv) for vv in nativevehicles]
        na=count(dd['ramp_arrival'])+tiny[1]-tiny[0];nh=count(dd['meter_head']);nm=ns[0]+na-ns[1]
        close(nm,post[0]+nh-post[1])
        a=sum(x['vehicles'] for x in trace['transfers'] if x['end_sec']<=END and x['target']=='ramp:'+ramp)
        m=sum(x['vehicles'] for x in trace['transfers'] if x['end_sec']<=END and x['source']=='ramp:'+ramp and x['target']=='merge_pending:'+ramp)
        h=sum(x['accepted_total_veh'] for x in trace['resources'] if x['end_sec']<=END and x['kind']=='physical_ramp_head_service' and x['resource'].startswith(ramp+':'))
        mp=snap['downstream_travelling_veh']+snap['merge_ready_veh']
        residual=max(abs(ns[0]+a-m-snap['connector_veh']),abs(post[0]+h-m-mp))
        maxres=max(maxres,residual);assert residual<1e-8
        obs=dict(arrival=na,head=nh,merge=nm,final=ns[1],final_pre=ns[1]-post[1],final_post=post[1])
        model=dict(arrival=a,head=h,merge=m,final=snap['connector_veh'],final_pre=snap['connector_veh']-mp,final_post=mp)
        rows[ramp]=dict(native=obs,model=model,error={k:model[k]-v for k,v in obs.items()})
    case[label]=rows
old,new=case['before']['RM_C10490'],case['candidate']['RM_C10490']
reduction={k:1-abs(new['error'][k])/abs(old['error'][k]) for k in ('arrival','head')}
pre_improved=abs(new['error']['final_pre'])<abs(old['error']['final_pre'])
all8_errors={label:sum(abs(x['error']['arrival']) for x in rows.values()) for label,rows in case.items()}
passed=min(reduction.values())>=.2 and pre_improved and all8_errors['candidate']<=1.1*all8_errors['before']
runtime=read(new_folder/'runtime.json')
assert runtime['gate_initial_route_metadata']['gate_initial_timing_changed'] is True
assert runtime['gate_initial_route_metadata']['gate_initial_new_stock_veh']==0
assert runtime['gate_initial_route_metadata']['gate_initial_future_generation_changed'] is False
oldruntime=read(base_folder/'runtime.json')
assert oldruntime['gate_future_travel']==runtime['gate_future_travel']
assert oldruntime['movement_capacity_veh_h']==runtime['movement_capacity_veh_h']
assert oldruntime['gate_entry_capacity_veh_h']==runtime['gate_entry_capacity_veh_h']
result=dict(status='passed_declared_gate' if passed else 'failed_declared_gate',passed=passed,adopted=False,
    window=[AT,END],reduction=reduction,prehead_stock_improved=pre_improved,all8_absolute_arrival_error=all8_errors,
    cases=case,identical_commands_initial_physical_state_and_future_demand=True,capacities_unchanged=True,
    max_mass_residual=maxres,pins=pins,forecasts_this_stage=1,fit=0,native=0,
    future_native_is_only_audit_input=True)
(O/f'geometry_verification_{AT}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=result['status'],window=result['window'],reduction=reduction,
    native=new['native'],before=old['model'],candidate=new['model'],all8_arrival_error=all8_errors),ensure_ascii=False))
