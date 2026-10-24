"""Assess two completed scalar predictions without rerunning them."""
import ast
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path

D=Path(__file__).resolve().parent
ROOT=D.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
def load(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

assert not (D/'autonomous_assessment.json').exists()
status=load(D/'attempt2/autonomous_status.json')
assert status['phase']=='complete_pending_assessment'
assert status['stats']['calls']==2 and status['stats']['fifo_steps']==900
old=I/'closedloop_recorded2700_lever450_s67_service66_20261003_actuator_equivalent_trace81_path'
new=I/'closedloop_recorded2700_lever450_fifo85r2'
arms=('release_actual','release_vsl90_actual')
a,b=({arm:load(folder/(arm+'.json')) for arm in arms} for folder in (old,new))
parity=['ttt_omega_veh_h','cost_by_stock','tracked_outside_residence_veh_h','control_area',
        'ramps','commands','physical_cell_states','executed_intervals']
for key in parity:assert a[arms[0]][key]==b[arms[0]][key],key
for arm in arms:
    assert a[arm]['commands']==b[arm]['commands']
    assert a[arm]['physical_cell_states'][0]==b[arm]['physical_cell_states'][0]
    assert b[arm]['validation']['all_actuator_and_step_constraints_checked']
    assert all(not v['future_observation_inputs'] for v in b[arm]['executed_intervals'])

def transfers(row):return [v for block in row['executed_intervals'] for v in block['transfers']]
def flow(row):
    result=dict(source=0.,merge=0.,off=0.,terminal=0.)
    for v in transfers(row):
        source,target=v['source'] or '',v['target'] or ''
        if target=='freeway:FW_E':
            if source=='origin:FW_E':result['source']+=v['vehicles']
            elif source.startswith('merge_pending:'):result['merge']+=v['vehicles']
        elif source=='freeway:FW_E':
            if target.startswith('storage:'):result['off']+=v['vehicles']
            elif target=='external:terminal:FW_E':result['terminal']+=v['vehicles']
    return result
def result(rows):
    held,vsl=(rows[k] for k in arms);x,y=flow(held),flow(vsl)
    def costs(v):return dict(omega=v['ttt_omega_veh_h'],outside=v['tracked_outside_residence_veh_h'],
        east=v['cost_by_stock']['freeway:FW_E'],west=v['cost_by_stock']['freeway:FW_W'],
        ramps=sum(val for key,val in v['cost_by_stock'].items() if key.startswith('ramp:')))
    c1,c2=costs(held),costs(vsl)
    return dict(delta_cost={k:c2[k]-c1[k] for k in c1},east_flow_delta={k:y[k]-x[k] for k in x},
                flows={'release':x,'vsl':y})
base,candidate=result(a),result(b)
actual=load(D.parent/'s67_full_observation/response_assessment76.json')
actual_cost=actual['actual_delta_omega_veh_h']
actual_terminal=(actual['arms']['release_vsl90']['mainline']['FW_E']['actual']['terminal']-
                 actual['arms']['release']['mainline']['FW_E']['actual']['terminal'])
checks={}
for key,truth,x,y in [('omega',actual_cost,base['delta_cost']['omega'],candidate['delta_cost']['omega']),
                      ('terminal',actual_terminal,base['east_flow_delta']['terminal'],candidate['east_flow_delta']['terminal'])]:
    e0,e1=abs(x-truth),abs(y-truth)
    checks[key]=dict(actual=truth,baseline=x,candidate=y,baseline_absolute_error=e0,
        candidate_absolute_error=e1,error_reduction_fraction=1-e1/e0,pass_twenty_percent=e1<=.8*e0)
ws=load(D/'attempt2/autonomous_witness.json');residual=0.
for j,arm in enumerate(arms):
    first,last=ws[j]['stocks'][0]['stock'],ws[j]['stocks'][-1]['stock']
    rows=transfers(b[arm])
    for key in first.keys()|last.keys():
        err=(last.get(key,0)-first.get(key,0)-math.fsum(v['vehicles'] for v in rows if v['target']==key)+
             math.fsum(v['vehicles'] for v in rows if v['source']==key))
        residual=max(residual,abs(err))
    assert ws[j]['resource_max']<1e-7
assert residual<1e-7,residual
for path,digest in status['source_pins'].items():assert sha(Path(path))==digest
protocol=load(D/'protocol.json');assert sha(Path(protocol['stop']))==protocol['stop_sha256']
helper=D.parent/'vsl_current_cells16_20/assess.py'
def functions(path):return {n.name:ast.dump(n) for n in ast.parse(path.read_text(encoding='utf-8')).body
                           if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
previous,current=functions(D/'assess.before.py.txt'),functions(helper)
assert all(current[k]==v for k,v in previous.items())
passed=all(v['pass_twenty_percent'] for v in checks.values())
report=dict(status='AUTONOMOUS_CANDIDATE_REQUIRES_REGRESSION' if passed else 'AUTONOMOUS_CANDIDATE_REJECTED',
    baseline=base,candidate=candidate,acceptance=checks,baseline_exact_fields=parity,
    forecast_compute_seconds=sum(v['wall_sec'] for v in b.values()),
    inactive_attempt_compute_seconds=sum(v['wall_sec'] for v in load(I/'closedloop_recorded2700_lever450_fifo85/summary.json')['results'].values()),
    actual_forecasts=4,active_candidate_forecasts=2,parameters_fitted=0,new_native=0,fzp_scans=0,
    cohort_balance_max=status['stats']['max_residual'],physical_inventory_balance_max=residual,
    resource_max=max(v['resource_max'] for v in ws),production_adopted=False,AD_verified=False,goal_qualified=False,
    inputs_sha256={str(folder/(arm+'.json')):sha(folder/(arm+'.json')) for folder in (old,new) for arm in arms},
    helper_sha256=sha(helper),existing_functions_unchanged=len(previous),old_STOP_unchanged=True,
    completion_time=datetime.now().astimezone().isoformat())
(D/'autonomous_assessment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ('status','acceptance','physical_inventory_balance_max',
                                      'cohort_balance_max','forecast_compute_seconds')},ensure_ascii=False))
