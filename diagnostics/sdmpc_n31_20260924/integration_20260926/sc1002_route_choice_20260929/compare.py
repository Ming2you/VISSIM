"""Compare the six completed fixed-command forecasts; no native I/O or fitting."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
I = HERE.parent
ROOT = Path(__file__).resolve().parents[4]
pins = {}


def read(path):
    data = path.read_bytes()
    pins[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(data)


previous = read(I/'sc1001_sources_20260929/comparison.json')
report = {}
paths = {
    'seed43':('closedloop_recorded2250_lever450_trace10484_head10119_s43_v2',
              'closedloop_recorded2250_lever450_native1113_s43'),
    'seed47':('closedloop_recorded2700_select_check_head10119_s47',
              'closedloop_recorded2700_select_check_native1113_s47'),
}
for seed,(before_dir,after_dir) in paths.items():
    before = read(I/before_dir/'summary.json')
    after = read(I/after_dir/'summary.json')
    assert after['future_observation_inputs'] is False
    assert after['optimizer_iterations'] == 0 and after['native_started'] is False
    assert before['start_sec'] == after['start_sec'] and before['duration_sec'] == after['duration_sec'] == 450
    old,new = before['results'],after['results']
    rows=[]; costs=[]; flows=[]
    for key,result in new.items():
        assert result['commands'] == old[key]['commands']
        validation = result['validation']
        if key == 'selected':
            assert validation['prewrite_binding_passed'] and validation['written_command_binding_passed']
            assert validation == old[key]['validation']
        else:
            assert validation['all_actuator_and_step_constraints_checked']
        native_cost = next(r['native_delta_omega_veh_h'] for r in previous[seed]['costs'] if r['case']==key)
        costs.append(dict(case=key,actual_delta_omega=native_cost,
            before_delta_omega=old[key]['ttt_omega_veh_h']-old['held_actual']['ttt_omega_veh_h'],
            after_delta_omega=result['ttt_omega_veh_h']-new['held_actual']['ttt_omega_veh_h'],
            before_omega=old[key]['ttt_omega_veh_h'],after_omega=result['ttt_omega_veh_h'],
            before_outside=old[key]['tracked_outside_residence_veh_h'],
            after_outside=result['tracked_outside_residence_veh_h']))
        native_arm=('nc' if seed=='seed43' else 'hold') if key=='held_actual' else key
        for ramp,value in result['ramps'].items():
            actual=next(r['actual'] for r in previous[seed]['ramps'] if r['arm']==native_arm and r['ramp']==ramp)
            assert abs(value['residual'])<1e-7
            rows.append(dict(arm=native_arm,ramp=ramp,actual=actual,before=old[key]['ramps'][ramp],after=value))
        def focused(d):
            return {k:v for k,v in d['control_area']['flow_counts'].items()
                    if (k.startswith(('movement:','arrival:')) and
                        (k.endswith('to_W_SC1001') or k.endswith('SC1001_E_SC1002_to_W_RAMP')))}
        flows.append(dict(case=key,before=focused(old[key]),after=focused(result)))
    runtime=read(I/after_dir/'runtime.json')
    old_runtime=read(I/before_dir/'runtime.json')
    assert runtime['initial_source_sha256']==old_runtime['initial_source_sha256']
    report[seed]=dict(costs=costs,ramps=rows,flows=flows,
        applied_choice=runtime['metadata']['native_choice_groups'],
        max_ramp_residual=max(abs(r['after']['residual']) for r in rows),
        ramp_mae={version:{metric:sum(abs(r[version][metric]-r['actual'][metric]) for r in rows)/len(rows)
                  for metric in ('arrival','merge','final_stock')} for version in ('before','after')})

old = read(I/'closedloop_recorded2250_init_sc1002_audit_v1/audit.json')
new = read(I/'closedloop_recorded2250_init_sc1002_unchanged_v2/audit.json')
old.pop('source_hashes');new.pop('source_hashes')
assert old == new
old_config = read(I/'sc1001_sources_20260929/candidate_config.json')
new_config = read(HERE/'candidate_config.json')
old_config['urban']['movements']['physical_route_topology']=new_config['urban']['movements']['physical_route_topology']
assert old_config == new_config
head = read(I/'sc1001_sources_20260929/native_join_checks.json')
assert head['head_join_future_matched']==head['head_join_future_count']==37 and not head['unmatched']
report.update(default_initialization_audit_exact=True,configs_only_route_contract_changed=True,
    commands_exact=True,forecasts=6,native_runs=0,optimizer_iterations=0,future_observation_inputs=False,
    actual_head10119_future=37,fit=False,gain_qualified=False)
for p in ('evaluation/controllers/physical_movement_routes.py','evaluation/controllers/runtime_setup.py',
          'diagnostics/test_physical_movement_routes.py'):
    path=ROOT/p;pins[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
report['source_pins']=pins
target=HERE/'comparison.json'
assert not target.exists()
target.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
print(json.dumps({s:{k:report[s][k] for k in ('costs','ramp_mae','max_ramp_residual')} for s in paths},ensure_ascii=False,indent=2))
