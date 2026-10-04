"""Compare native routing correction and locate the remaining arrival response."""
from pathlib import Path
import gzip
import hashlib
import json
import statistics

HERE=Path(__file__).resolve().parent
I=HERE.parents[1]
ROOT=I.parents[2]
pins={}


def read(p,compressed=False):
    raw=p.read_bytes();pins[str(p)]=hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if compressed else raw)


protocol=read(HERE/'protocol.json')
base=read(Path(protocol['base_config']));candidate=read(HERE/'candidate_config.json')
changed=candidate['urban']['movements']['physical_route_topology']
candidate['urban']['movements']['physical_route_topology']=base['urban']['movements']['physical_route_topology']
assert candidate==base
old_doc=read(Path(protocol['previous_evidence']));new_doc=read(ROOT/changed)
new_groups={k:new_doc['native_choice_groups'].pop(k) for k in list(new_doc['native_choice_groups']) if k.startswith('SC1001_')}
assert new_doc==old_doc and len(new_groups)==3
truth=read(I/'baseline_reproduction_20260929/sc1001_transport/comparison.json')
result={};mass=0.
for seed,at in ((47,2700),(43,2250)):
    old_dir=I/f'closedloop_recorded{at}_lever450_trace10484_peeloff10121_s{seed}_v1'
    new_dir=I/f'closedloop_recorded{at}_lever450_trace10484_sc1001_native_s{seed}_v1'
    old=read(old_dir/'summary.json');new=read(new_dir/'summary.json')
    old_runtime=read(old_dir/'runtime.json');runtime=read(new_dir/'runtime.json')
    assert old_runtime['initial_source_sha256']==runtime['initial_source_sha256']
    assert old['start_sec']==new['start_sec']==at and old['duration_sec']==new['duration_sec']==450
    assert not new['future_observation_inputs'] and not new['native_started'] and new['optimizer_iterations']==0
    rows=[];ramp_rows=[]
    for key,r in new['results'].items():
        b=old['results'][key]
        assert b['commands']==r['commands']
        assert r['validation']['all_actuator_and_step_constraints_checked'] and r['executed_control_blocks']==[0,1,2]
        arm=('hold' if key=='held_actual' else 'release') if seed==47 else ('nc' if key=='held_actual' else key)
        for ramp in r['ramps']:
            mass=max(mass,abs(r['ramps'][ramp]['residual']))
            native=next(v['actual'] for v in truth[f'seed{seed}']['ramps'] if v['arm']==arm and v['ramp']==ramp)
            ramp_rows.append(dict(case=key,ramp=ramp,actual=native,before=b['ramps'][ramp],after=r['ramps'][ramp]))
        cost=next(v for v in truth[f'seed{seed}']['costs'] if v['case']==key)
        traces=[read(f/(key+'_RM_C10484_trace.json.gz'),True) for f in (old_dir,new_dir)]
        assert traces[0]['initial_stock']==traces[1]['initial_stock']
        flows=[]
        for trace in traces:
            flows.append({app:sum(x['vehicles'] for x in trace['transfers'] if x['source']==f'movement:SC1001_{app}_to_W_RAMP')
                          for app in ('N_SC2002','E_SC1002','S_SC1003')})
        rows.append(dict(case=key,actual_delta_omega=cost['actual_delta_omega'],
            before_delta_omega=b['ttt_omega_veh_h']-old['results']['held_actual']['ttt_omega_veh_h'],
            after_delta_omega=r['ttt_omega_veh_h']-new['results']['held_actual']['ttt_omega_veh_h'],
            before_omega=b['ttt_omega_veh_h'],after_omega=r['ttt_omega_veh_h'],
            before_outside=b['tracked_outside_residence_veh_h'],after_outside=r['tracked_outside_residence_veh_h'],
            before_SC1001_flows=flows[0],after_SC1001_flows=flows[1]))
    result[f'seed{seed}']=dict(costs=rows,ramps=ramp_rows,
        mae={version:{metric:statistics.mean(abs(x[version][metric]-x['actual'][metric]) for x in ramp_rows)
                      for metric in ('arrival','merge','final_stock')} for version in ('before','after')})
assert mass<1e-7

# Post-run causal location check; these future trajectories are never model input.
cache=read(I/'baseline_reproduction_20260929/ramp_entry_space/native_paths.json.gz',True)
ids=[12355,15679,16177,20739,21647,21834,22390,22986,23230,24139]
paired=[]
for vid in ids:
    samples={arm:{r[0]:r for r in cache[arm]['rows'] if r[1]==vid and r[0]>=2700} for arm in ('hold','release')}
    first={arm:next(r for r in samples[arm].values() if r[2]==31) for arm in samples}
    assert first['hold']==first['release']
    common=sorted(set(samples['hold']) & set(samples['release']))
    difference=next(t for t in common if samples['hold'][t]!=samples['release'][t])
    hold=samples['hold'][max(samples['hold'])]
    entered=next(r for r in samples['release'].values() if r[2]==10484)
    assert hold[2]==31 and hold[6:8]==['1137','1'] and entered[6:8]==['1137','1']
    paired.append(dict(vehicle=vid,identical_first31=first['hold'],first_difference_sec=difference,
                       hold_first_difference=samples['hold'][difference],release_first_difference=samples['release'][difference],
                       hold_last=hold,release_first10484=entered))
result.update(core_changed=False,coefficient_fit=False,new_forecasts=6,new_native=0,production_adopted=False,
              gain_qualified=False,max_ramp_mass_residual=mass,paired_native_delay_cases=paired,
              native_pair_scope='Ten common initial vehicle IDs with equal first31 snapshot and same1137:1 selection; native hold delay is after SC1001 entry, not a change of destination. This is post-run diagnosis only.',
              route_uncertainty='Future1137 realized route1 count58/99 is not its configured expectation49.5; do not fit58/99 or force predicted arrivals to the realized release count.',
              source_pins=pins)
for name,pin in protocol['core_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==pin,name
for p,pin in pins.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==pin,p
out=HERE/'comparison.json';assert not out.exists()
out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
print(json.dumps({s:{'costs':[{k:r[k] for k in ('case','actual_delta_omega','before_delta_omega','after_delta_omega')} for r in result[s]['costs']],
                        'ramp10484':[r for r in result[s]['ramps'] if r['ramp']=='RM_C10484'],'mae':result[s]['mae']} for s in ('seed47','seed43')},indent=2))
