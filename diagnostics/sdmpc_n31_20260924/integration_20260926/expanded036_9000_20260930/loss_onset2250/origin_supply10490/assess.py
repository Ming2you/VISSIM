"""Predeclared10490 gate using the already reconstructed native balances."""
import gzip
import hashlib
import json
from pathlib import Path

O=Path(__file__).resolve().parent;L=O.parent;I=L.parent.parent
def read(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
old=read(L/'eight_ramp_first150/verification.json')
base=read(I/'closedloop_recorded2250_lever450_RM_C10484_city2250_ps_all8_originbase/held_actual.json')
candidate=read(I/'closedloop_recorded2250_lever450_RM_C10484_city2250_ps_all8_origincandidate/held_actual.json')
assert base['commands']==candidate['commands']
assert base['physical_cell_states'][0]==candidate['physical_cell_states'][0]
initial=read(L/'city_path/2250_ps_all8_originbase/ramp_initial.json')
assert initial==read(L/'city_path/2250_ps_all8_origincandidate/ramp_initial.json')
trace=read(L/'city_path/2250_ps_all8_origincandidate/trace.json.gz')
rows={};max_residual=0.
for r in initial['queue']:
    snap=trace['ramp_snapshots'][0]['buffers'][r]
    assert trace['ramp_snapshots'][0]['time_sec']==2400
    n0=initial['queue'][r]
    arrivals=sum(x['vehicles'] for x in trace['transfers'] if x['end_sec']<=2400 and x['target']=='ramp:'+r)
    merge=sum(x['vehicles'] for x in trace['transfers'] if x['end_sec']<=2400 and x['source']=='ramp:'+r and x['target']=='merge_pending:'+r)
    head=sum(x['accepted_total_veh'] for x in trace['resources'] if x['end_sec']<=2400 and x['kind']=='physical_ramp_head_service' and x['resource'].startswith(r+':'))
    post=snap['downstream_travelling_veh']+snap['merge_ready_veh']
    n1=snap['connector_veh']
    native=old['rows'][r]['native']
    residual=max(abs(n0+arrivals-merge-n1),abs(native['initial_post']+head-merge-post))
    max_residual=max(max_residual,residual);assert residual<1e-8
    for k,v in (('admitted',arrivals),('merge',merge),('head_service',head)):
        assert abs(snap['cumulative_'+k+'_veh']-v)<1e-8
    model=dict(initial=n0,arrival=arrivals,head=head,merge=merge,final=n1,final_post=post,final_pre=n1-post)
    rows[r]=dict(native=native,before=old['rows'][r]['model'],candidate=model,
        error={k:model[k]-native[nk] for k,nk in (('arrival','arrival'),('head','head'),('merge','merge_reconstructed'),('final','final'),('final_post','final_post'))})
target=rows['RM_C10490'];previous=old['rows']['RM_C10490']['error']
reduction={k:1-abs(target['error'][k])/abs(previous[oldkey]) for k,oldkey in (('merge','merge'),('final_post','post'))}
passed=all(v>=.2 for v in reduction.values())
rr=[x for x in trace['resources'] if x['resource']=='RM_C10490' and x['kind']=='physical_ramp_merge_origin_density' and x['end_sec']<=2400]
assert len(rr)==150
limits=dict(min_vph=min(x['available_veh']*3600 for x in rr),max_vph=max(x['available_veh']*3600 for x in rr),
    mean_vph=sum(x['available_veh']*3600 for x in rr)/150,
    binding_seconds=sum(abs(x['available_veh']-x['accepted_total_veh'])<1e-7 for x in rr))
result=dict(status='primary_pass' if passed else 'rejected_primary',adopted=False,
    primary_gate_passed=passed,primary_relative_error_reduction=reduction,rows=rows,
    density_supply=limits,identical_commands=True,identical_initial_state_and_cohorts=True,
    max_mass_residual=max_residual,ttt450_before=base['ttt_omega_veh_h'],ttt450_candidate=candidate['ttt_omega_veh_h'],
    native_match_scope='First1502250-2400 only;450 held beyond actual next decision is not a native policy replay.',
    physical_forecasts=2,optimizer_runs=0,fits=0,native_runs=0,fzp_scans=0,live_monitoring=0,
    next_stage='recovery3600' if passed else 'STOP: no recovery/independent forecasts, no coefficient grid',
    source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (
        O/'protocol.json',O/'candidate_config.json',L/'eight_ramp_first150/verification.json',
        L/'city_path/2250_ps_all8_origincandidate/trace.json.gz')})
(O/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=result['status'],reduction=reduction,target=target,limits=limits),ensure_ascii=False))
