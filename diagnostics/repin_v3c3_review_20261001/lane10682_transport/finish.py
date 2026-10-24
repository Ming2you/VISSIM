"""Archive the failed physical candidate and restore only this turn's edits."""
import ast
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
target=HERE/'completion.json';assert not target.exists()
after=read(HERE/'executed_multilane_sources.json')
for p,h in after.items():assert sha(ROOT/p)==h,('concurrent change; do not restore',p)
result=read(HERE/'assessment_multilane.json')
proof=read(HERE/'class_blockage.json')
assert result['forecasts']==6 and result['new_native']==0
assert max(result[k] for k in ('mass_residual','route_residual','resource_exceedance'))<1e-7
assert result['cases']['47']['hold']['ports']['10682']['after']['entry']<120
assert proof['cases']['47']['predicted10643_inaccessible_stock']>29
before=read(HERE/'before.json')
driver='diagnostics/sdmpc_n31_20260924/integration_20260926/probe_selected_arrival_path.py'
before[driver]=sha(HERE/'probe_selected_arrival_path.py.before')
restored={}
for p,h in before.items():
    backup=HERE/(Path(p).name+'.before')
    assert sha(backup)==h
    ast.parse(backup.read_text(encoding='utf8'))
    (ROOT/p).write_bytes(backup.read_bytes())
    assert sha(ROOT/p)==h
    restored[p]=h
oldpins=read(HERE.parent/'lane10682_feasibility/verification.json')['production_current']
for p,h in oldpins.items():assert sha(Path(p))==h,p
stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
assert sha(stop)==result['stop_sha256']
completion=dict(status='REJECTED_NOT_ADOPTED',goal_status='ACTIVE_NOT_QUALIFIED',
    saved_forecasts=12,valid_geometry_forecasts=6,invalid_single_lane_geometry_forecasts=6,
    saved_forecast_compute_sec=result['wall_sec']+read(HERE/'assessment.json')['wall_sec'],
    unsaved_completed_forecasts_due_to_export_assertion=2,initial_guard_failures=2,
    tests_passed=17,test_import_permission_failure_preserved=True,
    route_mass_residual=result['route_residual'],port_mass_residual=result['mass_residual'],
    resource_exceedance=result['resource_exceedance'],
    rejected_reasons=['47 recovered upstream cells slowed incorrectly',
        '47 10682 near-correct entry becomes too low',
        '10643 entry far too low in both states, false inaccessible route retention',
        '43 control gain directions not repaired'],
    root_of_new_candidate_error='No10643 target in short inlet snapshot -> uniform lane fallback; pooled destination-independent exchange leaves28.6/29.1 targets in inaccessible lanes. Native endpoint0both.',
    restored_exact=restored,previous7production_pins_exact=oldpins,stop_sha256=sha(stop),
    new_vissim=0,new_fzp_scans=0,push=0,owned_sessions_all_terminal=[40363,9070,16065,96877,3010,85673,9152,95586],
    retained='Only previous REVIEW47 optional initialization remains; archived regional dynamics is NOT current or controller-qualified.',
    next='Validate causal target-conditional inlet/approach lane distribution and required lateral transport before another regional rollout; do not fit FD to false trapped exit stock.')
target.write_text(json.dumps(completion,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in completion.items() if k not in ('restored_exact','previous7production_pins_exact')},ensure_ascii=False))
