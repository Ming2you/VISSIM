"""Replay the two completed diagnostic commands with finer output only."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
suffix=({'--length-fix':'_length','--path-fix':'_path','--selected-short':'_selected'}.get(sys.argv[1], '') if len(sys.argv)==2 else '')
assert not sys.argv[1:] or suffix
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
driver=I/'probe_selected_arrival_path.py'
def read(path):return json.loads(path.read_bytes())
def save(path,value):path.write_text(json.dumps(value,indent=2),encoding='utf-8')
def functions(text):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
before=functions((HERE/'probe.before81.py.txt').read_text(encoding='utf-8'))
after=functions(driver.read_text(encoding='utf-8'))
changed={k for k in before.keys()|after.keys() if before.get(k)!=after.get(k)}
assert changed=={'executed_interval_responses','probe_levers','probe_selected_meter','main'},changed
selected=read(HERE.parent/'s67_selection77/vsl_check_plan.json')['argv']
release=read(HERE.parent/'s67_full_observation/prediction_run76_actuator_equivalent.json')['argv'][2:]
assert Path(selected[0])==driver and Path(release[0])==driver
jobs=[('release',release+['--output-suffix=trace81'+suffix]),('selected',selected+['--output-suffix=trace81'+suffix])]
targets=[I/('closedloop_recorded2700_lever450_s67_service66_20261003_actuator_equivalent_trace81'+suffix),
         I/('closedloop_recorded2700_budget_check_selected_vsl13_s67_service66_selection77_access_trace81'+suffix)]
completed_release=None
if suffix=='_selected':
    previous=read(HERE/'run_status_path.json')
    assert previous['stage']=='failed' and previous['jobs'][0]['stage']=='complete' and previous['jobs'][1]['stage']=='failed'
    assert 'derived_000150.json' in (HERE/'selected_path.log').read_text(encoding='utf-8')
    completed_release=I/'closedloop_recorded2700_lever450_s67_service66_20261003_actuator_equivalent_trace81_path'
    assert set(read(completed_release/'summary.json')['results'])=={'release_actual','release_vsl90_actual'}
    args=[('--probe-label=s67_response81' if x.startswith('--probe-label=') else x) for x in selected]
    args+=['--selection-reference='+str(I/'closedloop_recorded2700_select_s67_service66_selection77_access'),
           '--selection-execution-reference='+str(I/'closedloop_recorded2700_select_check_s67_service66_selection77_access')]
    jobs=[('selected',args)]
    targets=[I/'closedloop_recorded2700_budget_check_selected_vsl13_s67_response81']
    assert len(str(targets[0]/'derived_history/derived_000150.json'))<250
if suffix=='_length':
    assert read(HERE/'run_status.json')['stage']=='failed'
    assert 'assert len(speed_terms)==19*150' in (HERE/'release.log').read_text(encoding='utf-8')
elif suffix=='_path':
    assert read(HERE/'run_status_length.json')['stage']=='failed'
    assert 'FileNotFoundError' in (HERE/'release_length.log').read_text(encoding='utf-8')
    assert all(len(str(t/'release_vsl90.terms.gz'))<260 for t in targets)
assert not (HERE/('run_status'+suffix+'.json')).exists() and all(not p.exists() for p in targets)
files=[driver,ROOT/'evaluation/controllers/observation_projection.py',ROOT/'evaluation/controllers/runtime_setup.py',
       ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py',ROOT/'evaluation/controllers/lane_offramp_runtime.py',
       HERE.parent/'rm47_service66_response/candidate_config.json',HERE.parent/'retained10638/candidate_manifest.json',
       HERE.parent/'s67_selected_vsl78/response_assessment80.json',HERE.parent/'s67_full_observation/response_assessment76.json']
protocol=dict(purpose='Conditional joint-policy discharge/recovery diagnosis; same physical predictions, richer recorded outputs.',
    previous_goal_turn='PROGRESS: native pair complete, selected VSL loss confirmed.',
    max_exact450_forecasts=3 if completed_release else 5,max_surrogate450_forecasts=3,max_optimizer_calls=0,new_native_runs=0,
    coefficient_fit=0,production_changes=0,changed_diagnostic_functions=sorted(changed),
    source_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
    jobs=[dict(name=n,argv=a,output=str(t)) for (n,a),t in zip(jobs,targets)],
    acceptance='Prior scalar costs/ramps/commands remain exact. Report interval flow and speed-term limits; no model adoption from this observation-only trace.',
    stop_sha256=hashlib.sha256(Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP').read_bytes()).hexdigest())
assert protocol['stop_sha256']=='91b2163b02b01447242909dee8e7f773d18e76a6594bd9db8de64d2a48246fc3'
protocol['prior_attempt_forecasts']=5 if completed_release else 3 if suffix=='_path' else 1 if suffix else 0
protocol['completed_release_output']=str(completed_release) if completed_release else None
protocol['repair']='Keep old150s assertion scoped; shorten trace filenames below Windows MAX_PATH. All failed receipts/logs retained.' if suffix else None
save(HERE/('protocol'+suffix+'.json'),protocol)
status=dict(stage='running',wrapper_pid=os.getpid(),started=datetime.datetime.now().astimezone().isoformat(),jobs=[])
status_path=HERE/('run_status'+suffix+'.json');save(status_path,status)
for name,args in jobs:
    with (HERE/(name+suffix+'.log')).open('w',encoding='utf-8') as log:
        child=subprocess.Popen([sys.executable,'-B',*args],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        row=dict(name=name,pid=child.pid,stage='running');status['jobs'].append(row);save(status_path,status)
        code=child.wait();row.update(stage='complete' if code==0 else 'failed',exit_code=code)
    save(status_path,status)
    if code:
        status['stage']='failed';save(status_path,status);raise SystemExit(code)
status.update(stage='complete',ended=datetime.datetime.now().astimezone().isoformat());save(status_path,status)
print(json.dumps(status))
