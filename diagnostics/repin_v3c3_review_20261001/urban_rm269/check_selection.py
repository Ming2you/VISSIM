"""Verify the completed single offline selection; never launches a prediction."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
read=lambda p:json.loads(p.read_bytes())
out=HERE/'selection2400'
launch=read(HERE/'selection2400_launch.json')
done=read(out/'completion.json')
assert done['status']=='complete' and done['full_selection'] and not done['native_execution']
for name,pin in launch['source_pins'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==pin,name
j=read(out/'unused.joint.json');s=j['selection']
a=read(out/'unused.json');reference=read(out/'reference.json')
assert j['completed'] and s['feasible'] and s['final_constraints']['feasible']
assert s['control_sequence']['blocks']==3
assert s['control_sequence']['all_actuator_and_step_constraints_checked']
assert (out/'unused.csv').is_file()
assert abs(sum(s['omega_partition']['costs'].values())-s['selected_objective'])<1e-6
assert s['policy']['response_cap_cache'] and s['policy']['max_iterations']==2
assert s['policy']['pfo_cap_options']['max_iterations']==2
assert s['finite_neighbor_audit_performed']
query=s['surrogate_query']
assert query['nuf_cap_response_reuse_enabled']
assert not query['failed_batches']
result=dict(status='verified_offline',completion=done,converged=s['converged'],
    selection_status=s['selection_status'],source_pins_verified=True,
    held_objective=s['held_objective'],selected_objective=s['selected_objective'],
    omega_partition=s['omega_partition']['costs'],constraints=s['final_constraints'],
    reference_rm={k:v for k,v in reference.get('diagnostics',{}).items() if k.startswith('rw_meter_green_')},
    selected_rm={k:v for k,v in a['diagnostics'].items() if k.startswith('rw_meter_green_')},
    sequence=s['control_sequence'],cap_candidates=s['candidates'],
    meter_audit=s['meter_neighbor_audit'],gradient_reuse=s['gradient_reuse'],
    query_stats={k:v for k,v in query.items() if k!='rows'},
    decision_budget=j['decision_budget'],
    scope='One offline complete SDMPC selection on saved2400 state; native gain, microscopic lane access and overall runtime speedup not established.')
(HERE/'selection2400_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:result[k] for k in ('status','converged','selection_status','held_objective','selected_objective','selected_rm')},ensure_ascii=False,indent=2))
