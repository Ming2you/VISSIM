"""3600 first150 guard. Future native values are audit-only inputs."""
import csv
import gzip
import json
from pathlib import Path

O=Path(__file__).resolve().parent;L=O.parent;I=L.parent.parent
D=Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
def read(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
r='RM_C10490'
base=read(I/'closedloop_recorded3600_lever450_RM_C10484_city3600_ps/held_actual.json')
candidate=read(I/'closedloop_recorded3600_lever450_RM_C10484_city3600_ps_all8_origincandidate/held_actual.json')
assert base['commands']==candidate['commands']
assert base['physical_cell_states'][0]==candidate['physical_cell_states'][0]
action=read(D/'action_003600.json');cmd=candidate['commands'][0]
for k in ('green_times','offsets','vsl'):assert cmd[k]==action[k]
for name,g in cmd['meters'].items():assert g==action['diagnostics']['rw_meter_green_'+name]
a,b=[read(D/f'state_{t:06d}.json') for t in (3600,3750)]
det=list(csv.DictReader((I/'selected/obs150/obs150_detectors_v2.csv').read_text(encoding='utf-8-sig').splitlines()))
for s,t in ((a,3600),(b,3750)):
    rec=s['vehicle_records'];assert rec['complete'] and not rec['unobservable_count']
    assert rec['capture_sim_sec_before']==rec['capture_sim_sec_after']==t
vv=[[v for v in s['vehicle_records']['records'] if v['link_no']==10490] for s in (a,b)]
heads=[x for x in det if x['link']=='10490' and x['role']=='meter_head']
arr=[x for x in det if x['link']=='10490' and x['role']=='ramp_arrival']
pos={int(x['lane']):float(x['pos']) for x in heads}
def count(dd):
    result=0.
    for x in dd:
        k=x['dcm_no'];n=b['obs150']['detectors'][k]
        assert n==b['obs150']['detectors_cum'][k]-a['obs150']['detectors_cum'][k]
        result+=n
    return result
ns=list(map(len,vv));posts=[sum(v['position_m']>pos[v['lane_no']] for v in vs) for vs in vv]
tiny=[sum(v['position_m']<1 for v in vs) for vs in vv]
arrived=count(arr)+tiny[1]-tiny[0];head=count(heads);merge=ns[0]+arrived-ns[1]
assert merge==posts[0]+head-posts[1]
native=dict(initial=ns[0],arrival=arrived,head=head,merge=merge,final=ns[1],final_post=posts[1])
rows={}
for label,forecast,cp in (('before',base,L/'city_path/3600_ps'),('candidate',candidate,L/'city_path/3600_ps_all8_origincandidate')):
    trace=read(cp/'trace.json.gz')
    arrflows=[x for x in trace['transfers'] if x['target']=='ramp:'+r]
    assert abs(sum(x['vehicles'] for x in arrflows)-forecast['ramps'][r]['arrival'])<1e-8
    arrivals=sum(x['vehicles'] for x in arrflows if x['end_sec']<=3750)
    final=forecast['physical_cell_states'][1]['ramp_queue'][r]
    model=dict(arrival=arrivals,merge=ns[0]+arrivals-final,final=final)
    if label=='candidate':
        snap=trace['ramp_snapshots'][0]['buffers'][r]
        model['final_post']=snap['downstream_travelling_veh']+snap['merge_ready_veh']
        physical_merge=sum(x['vehicles'] for x in trace['transfers'] if x['source']=='ramp:'+r and x['target']=='merge_pending:'+r and x['end_sec']<=3750)
        assert abs(physical_merge-model['merge'])<1e-8
    rows[label]=dict(model=model,error={k:v-native[k] for k,v in model.items()})
passed=all(abs(rows['candidate']['error'][k])<=abs(rows['before']['error'][k])+1 for k in ('merge','final'))
passed=passed and rows['candidate']['model']['final_post']<=native['final_post']+2
result=dict(status='recovery_pass' if passed else 'recovery_failed',passed=passed,adopted=False,native=native,rows=rows,
    gate='No >1vehicle worsening in merge/final-stock absolute error; no posthead queue >native+2. No fitted coefficients.',
    first150_actual_commands_match=True,full450_native_policy_match=False,base_first150_merge_reconstructed=True,
    base_arrival_trace_total_equals_full_forecast=True,forecast_count_this_stage=1)
(O/'recovery_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
