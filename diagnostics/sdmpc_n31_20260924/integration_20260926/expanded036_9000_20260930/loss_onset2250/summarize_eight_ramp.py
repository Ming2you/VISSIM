"""Compare one existing-command forecast with eight native ramp inventories.

All future observations below are retrospective audit inputs, never predictors.
"""
import csv
import gzip
import hashlib
import json
import statistics
from pathlib import Path

L=Path(__file__).resolve().parent; I=L.parent.parent
O=L/'eight_ramp_first150'; C=L/'city_path/2250_ps_all8'
D=Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
pins={}
def raw(p):
    b=p.read_bytes();pins[str(p)]=hashlib.sha256(b).hexdigest();return b
def load(p):
    b=raw(p);return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def close(a,b):
    assert abs(a-b)<1e-7,(a,b)
def post(snapshot):
    return snapshot['downstream_travelling_veh']+snapshot['merge_ready_veh']
def pre(snapshot):
    return snapshot['upstream_travelling_veh']+snapshot['head_ready_veh']

assert not (O/'verification.json').exists()
old=load(I/'closedloop_recorded2250_lever450_RM_C10484_city2250_ps/held_actual.json')
new=load(I/'closedloop_recorded2250_lever450_RM_C10484_city2250_ps_all8/held_actual.json')
for key in ('commands','ramps','physical_cell_states','ttt_omega_veh_h','cost_by_stock','outside_cost_by_stock'):
    assert old[key]==new[key],key
trace=load(C/'trace.json.gz');initial=load(C/'ramp_initial.json')
receipt=load(C/'receipt.json');assert receipt['forecast_count']==1 and not receipt['future_observation_inputs']
for p,h in receipt['pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
native={t:load(D/f'state_{t:06d}.json') for t in (2250,2400,3600,3750)}
for t,s in native.items():
    rec=s['vehicle_records']
    assert rec['complete'] and rec['unobservable_count']==0 and len(rec['records'])==rec['record_count']
    assert rec['capture_sim_sec_before']==rec['capture_sim_sec_after']==t
det=list(csv.DictReader(raw(I/'selected/obs150/obs150_detectors_v2.csv').decode('utf-8-sig').splitlines()))
action=load(D/'action_002250.json')
command=new['commands'][0]
for key in ('green_times','offsets','vsl'):assert command[key]==action[key],key
for r in initial['queue']:assert command['meters'][r]==action['diagnostics']['rw_meter_green_'+r]
removals=load(L.parent/'loss_diagnosis/mechanism_evidence.json')['removals_by_link']['sdmpc']
flows=[x for x in trace['transfers'] if x['end_sec']<=2400]
resources=[x for x in trace['resources'] if x['end_sec']<=2400]
end=trace['ramp_snapshots'][0];assert end['time_sec']==2400
states=(native[2250],native[2400]);rows={}
for r,n0 in initial['queue'].items():
    link=int(r.removeprefix('RM_C'))
    assert str(link) not in removals,'Native ramp deletion must be explicitly accounted'
    arrivals=[x for x in det if x['link']==str(link) and x['role']=='ramp_arrival']
    heads=[x for x in det if x['link']==str(link) and x['role']=='meter_head']
    pos={int(x['lane']):float(x['pos']) for x in heads}
    vehicles=[[x for x in s['vehicle_records']['records'] if x['link_no']==link] for s in states]
    assert sorted(initial['buffers'][r]['metadata']['initial_cohorts'])==sorted(
        [[v['position_m'],v['speed_kph'],v['lane_no']] for v in vehicles[0]])
    ns=[len(v) for v in vehicles];close(ns[0],n0)
    ps=[sum(v['position_m']>pos[v['lane_no']] for v in vv) for vv in vehicles]
    # Arrival detectors are1m inside connectors. Correct the two endpoint
    # inventories before applying full-connector conservation (10482 has1veh).
    tiny=[sum(v['position_m']<1. for v in vv) for vv in vehicles]
    def count(dd):
        total=0
        for x in dd:
            k=x['dcm_no'];v=states[1]['obs150']['detectors'][k]
            assert v is not None
            close(v,states[1]['obs150']['detectors_cum'][k]-states[0]['obs150']['detectors_cum'][k])
            total+=v
        return total
    na=count(arrivals)+tiny[1]-tiny[0];nh=count(heads);nm=ns[0]+na-ns[1]
    close(nm,nh+ps[0]-ps[1])
    obs=dict(initial=ns[0],arrival=na,head=nh,merge_reconstructed=nm,final=ns[1],
        initial_post=ps[0],final_post=ps[1],initial_pre=ns[0]-ps[0],final_pre=ns[1]-ps[1],
        entry_1m_stock_correction=tiny[1]-tiny[0])
    buff=end['buffers'][r];close(buff['connector_veh'],end['queue'][r])
    ma=sum(x['vehicles'] for x in flows if x['target']=='ramp:'+r)
    mm=sum(x['vehicles'] for x in flows if x['source']=='ramp:'+r and x['target']=='merge_pending:'+r)
    hh=[x for x in resources if x['kind']=='physical_ramp_head_service' and x['resource'].startswith(r+':')]
    mh=sum(x['accepted_total_veh'] for x in hh)
    start=initial['buffers'][r]['snapshot'];close(post(start),ps[0])
    close(n0+ma-mm,end['queue'][r]);close(post(start)+mh-mm,post(buff))
    close(pre(start)+ma-mh,pre(buff))
    for key,value in [('admitted',ma),('head_service',mh),('merge',mm)]:
        close(buff['cumulative_'+key+'_veh'],value)
    model=dict(initial=n0,arrival=ma,head=mh,merge=mm,final=end['queue'][r],final_post=post(buff),final_pre=pre(buff))
    error=dict(arrival=ma-na,head=mh-nh,merge=mm-nm,final=end['queue'][r]-ns[1],
        post=post(buff)-ps[1],pre=pre(buff)-(ns[1]-ps[1]))
    close(error['final'],error['arrival']-error['merge']);close(error['merge'],error['head']-error['post'])
    limits={}
    for kind in ('canonical_receiving','physical_receiving','eligible'):
        zz=[x for x in resources if x['resource']==r and x['kind']=='physical_ramp_merge_'+kind]
        assert len(zz)==150
        limits[kind]=dict(sum_available=sum(x['available_veh'] for x in zz),
            binding_seconds=sum(abs(x['available_veh']-x['accepted_total_veh'])<1e-7 for x in zz))
    rows[r]=dict(native=obs,model=model,error=error,model_limits=limits)

# Native head-to-endpoint ages: observed retained post-head cohorts, not an
# uncensored travel-time sample or a directly estimated merge capacity.
cohorts={}
for start in (2250,3600):
    stop=start+150;s=native[stop];meta=s['obs150']['mer']
    data=raw(D/meta['chunk']);assert hashlib.sha256(data).hexdigest()==meta['chunk_sha256']
    events=[json.loads(x) for x in data.decode('utf-8').splitlines()]
    entries=[x for x in events if x[2] is not None and start<=x[2]<stop]
    per={}
    for r in ('RM_C10490','RM_C10482','RM_C10681','RM_C10484'):
        link=int(r.removeprefix('RM_C'));heads=[x for x in det if x['link']==str(link) and x['role']=='meter_head']
        head_ids={int(x['dcp_no']) for x in heads};positions={int(x['lane']):float(x['pos']) for x in heads}
        observed={}
        for ev in entries:
            if ev[1] in head_ids:
                assert ev[4] not in observed,'Repeated head passage requires separate visit identity'
                observed[ev[4]]=ev[2]
        native_count=sum(s['obs150']['detectors'][x['dcm_no']] for x in heads)
        close(len(observed),native_count)
        vv=[v for v in s['vehicle_records']['records'] if v['link_no']==link and v['position_m']>positions[v['lane_no']]]
        before={v['veh_no']:v for v in native[start]['vehicle_records']['records']}
        members=[]
        for v in vv:
            head=observed.get(v['veh_no']);oldv=before.get(v['veh_no'])
            oldpost=oldv is not None and oldv['link_no']==link and oldv['position_m']>positions[oldv['lane_no']]
            assert head is not None or oldpost,'Unobserved post-head entry'
            members.append(dict(vehicle=v['veh_no'],position=v['position_m'],speed=v['speed_kph'],
                head_sec=head,elapsed_since_head_lower_bound=stop-head if head is not None else 150.,
                was_initial_posthead=oldpost))
        free=initial['buffers'][r]['metadata']['post_head_travel_sec']
        per[r]=dict(retained_posthead=members,deterministic_model_posthead_travel_sec=free,
            above_model_travel_count=sum(x['elapsed_since_head_lower_bound']>free for x in members),
            stopped_lt5_count=sum(x['speed']<5 for x in members),
            median_elapsed_lower_bound=statistics.median(x['elapsed_since_head_lower_bound'] for x in members) if members else None)
    cohorts[start]=per

report=dict(status='verified',previous_goal_turn='progress',current_goal_turn='progress',
    rows=rows,native_posthead_retention=cohorts,exact_prior_forecast_reproduced=True,
    identical_initial_cohorts=True,first150_commands_match=True,all8_stock_and_flow_balances=True,
    native_ramp_deletions=0,one_metre_entry_correction_explicit=True,
    forecast_count=1,optimizer_iterations=0,native_runs=0,fzp_scans=0,fit_evaluations=0,live_polls=0,
    session50357='exit0',goal='ACTIVE/NOT_QUALIFIED',adopted=False,
    caveats=['2250-2400 matched prediction.3600-3750 retention is native-only context, not a second forecast validation.',
        'Native merges are two agreeing stock-balance reconstructions, not a new merge detector.',
        'Queue endpoints can cancel arrival/head/merge errors. Post-head ages are retained-cohort lower bounds, not average travel times.',
        'Capacity availability summed over time is not a measured saturation flow. No future native values entered a model.'],
    pins=pins)
(O/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
flat=[dict(ramp=r,**{'native_'+k:v for k,v in x['native'].items()},**{'model_'+k:v for k,v in x['model'].items()},
           **{'error_'+k:v for k,v in x['error'].items()}) for r,x in rows.items()]
with (O/'comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(flat[0]));writer.writeheader();writer.writerows(flat)
print(json.dumps(dict(errors={r:x['error'] for r,x in rows.items()},retained={t:{r:{k:v for k,v in x.items() if k!='retained_posthead'} for r,x in rr.items()} for t,rr in cohorts.items()}),ensure_ascii=False))
