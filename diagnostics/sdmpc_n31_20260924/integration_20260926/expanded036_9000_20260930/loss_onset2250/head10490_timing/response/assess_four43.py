"""Four fixed responses of the timing candidate; existing native evidence only."""
import csv
import hashlib
import json
import sys
from pathlib import Path

O=Path(__file__).resolve().parent;L=O.parent.parent;I=L.parent.parent
def option(name,default):
    return next((a.split('=',1)[1] for a in sys.argv[1:] if a.startswith('--'+name+'=')),default)
candidate_label=option('candidate-label','geotime_s43_20261001')
baseline_label=option('baseline-label','physical_speed_after_s43_20261001')
for label in (candidate_label,baseline_label):
    assert all(c.isalnum() or c in '_-' for c in label)
O=Path(option('output-dir',str(O))).resolve()
assert O.is_relative_to(L) and O.is_dir() and not (O/'four43_verification.json').exists()
pins={}
def read(p):
    b=p.read_bytes();pins[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)
def close(a,b):assert abs(a-b)<1e-7,(a,b)
old=read(Path(option('baseline-verification',str(L/'physical_speed/four43/verification.json'))))
before_model=old['candidate'] if 'candidate' in old else old['models']['after']
proof=read(I/'seed43_fullplant_20260929/analysis_v2/observation_reuse.json')
assert proof['passed'] and proof['precontrol_prefix_exact'] and proof['native_execution_passed']
assert hashlib.sha256(Path(proof['reused_native_proof']['path']).read_bytes()).hexdigest()==proof['reused_native_proof']['sha256']
f=I/('closedloop_recorded2250_lever450_trace10484_'+candidate_label)
summary=read(f/'summary.json')
assert not summary['native_started'] and not summary['future_observation_inputs'] and summary['optimizer_iterations']==0
assert summary['prediction_conditioned_on_executed_commands'] and summary['city_signals_held']
assert set(summary['results'])=={'held_actual','rm','vsl','both'}
for p,h in summary['native_profile_inputs'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
arms=('nc','rm','vsl','both');result={};states={};volume_errors={}
for arm in arms:
    key='held_actual' if arm=='nc' else arm
    row=read(f/f'{key}.json');assert row==summary['results'][key]
    baseline=read(I/f'closedloop_recorded2250_lever450_trace10484_{baseline_label}/{key}.json')
    assert row['commands']==baseline['commands']
    assert row['physical_cell_states'][0]==baseline['physical_cell_states'][0]
    assert row['validation']['all_actuator_and_step_constraints_checked']
    assert max(abs(r['residual']) for r in row['ramps'].values())<1e-8
    close(sum(row['cost_by_stock'].values()),row['ttt_omega_veh_h'])
    for ramp in ('RM_C10639','RM_C10681','RM_C10490','RM_C10484'):
        assert [c['meters'][ramp] for c in row['commands']]==([8.,6.,4.] if arm in ('rm','both') else [10.]*3)
    parts={road:row['cost_by_stock']['freeway:'+road] for road in ('FW_E','FW_W')}
    parts['eight_on_ramps']=sum(v for k,v in row['cost_by_stock'].items() if k.startswith('ramp:'))
    parts['other_Omega']=row['ttt_omega_veh_h']-sum(parts.values())
    result[arm]=dict(omega=row['ttt_omega_veh_h'],outside=row['tracked_outside_residence_veh_h'],
        combined=row['ttt_with_tracked_outside_veh_h'],components=parts,ramps=row['ramps'])
    states[arm]=row['physical_cell_states'][0];assert states[arm]==states['nc']
    # Recheck the small native stock tables without touching trajectories.
    p=I/f'seed43_fullplant_20260929/analysis_v2/{arm}_area_stocks_5s.csv'
    data=p.read_bytes();pins[str(p)]=hashlib.sha256(data).hexdigest()
    rows=list(csv.DictReader(data.decode('utf-8-sig').splitlines()))
    assert len(rows)==91 and float(rows[0]['time_s'])==2250.1 and float(rows[-1]['time_s'])==2700.1
    native=sum((float(a['omega_n'])+float(b['omega_n']))*.5*5/3600 for a,b in zip(rows,rows[1:]))
    close(native,old['native'][arm]['cost']['omega'])
    volume_errors[arm]={r:{k:row['ramps'][r][k]-v[k] for k in ('arrival','merge','final_stock')}
        for r,v in old['native'][arm]['ramps'].items()}
for arm in arms:
    result[arm]['delta']={k:result[arm][k]-result['nc'][k] for k in ('omega','outside','combined')}
    result[arm]['delta_components']={k:v-result['nc']['components'][k] for k,v in result[arm]['components'].items()}
rank=dict(native=old['rank']['native'],before=old['rank'].get('candidate',old['rank'].get('after')),
          candidate=sorted(arms,key=lambda a:result[a]['omega']))
out=dict(status='four_fixed_responses_complete',adopted=False,forecast_count=4,goal='ACTIVE/NOT_QUALIFIED',
    native=old['native'],before=before_model,candidate=result,rank=rank,volume_errors=volume_errors,
    model_labels=dict(before=baseline_label,candidate=candidate_label),
    same_commands_and_initial_physical_states=True,all8_ramp_conservation=True,writer_constraints=True,
    native_omega_reintegrated=True,coefficients_fitted=0,optimizer=0,new_native=0,fzp_scans=0,live_monitoring=0,pins=pins,
    limitations=['Model differences relative to the named baseline are declared in the experiment protocol.',
        'RM means all four east meters8/6/4, not10484alone.',
        'Actual native inlet realization differs: prior source/flux audit must not be discarded.',
        'No future measured demand was used in forecasts. Fixed executed commands are conditioning inputs.',
        'Physical/writer bounds tested; NP/NUF optimization feasibility and fullAD not tested.',
        'Native5s stock clock2250.1-2700.1; prediction starts2250, matching prior comparison convention.'])
(O/'four43_verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(rank=rank,delta={a:dict(native=old['native'][a]['delta']['omega'],before=before_model[a]['delta']['omega'],
    candidate=result[a]['delta']['omega'],components=result[a]['delta_components']) for a in arms},
    ramp10490={a:dict(actual=old['native'][a]['ramps']['RM_C10490'],predicted=result[a]['ramps']['RM_C10490']) for a in arms}),ensure_ascii=False))
