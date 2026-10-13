"""Repin a diagnosed freeze-tool repair; no native retry or command change."""
import json,hashlib,shutil
from datetime import datetime,timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent;H=HERE.parent;U=H.parents[2]
P=U/'diagnostics/sdmpc_n31_20260924/integration_20260926/native_urbanrm269_10681only_2400'
OLD=Path('E:/VISSIM_runtime/20261009_urbanrm269_10681only')
NEW=Path('E:/VISSIM_runtime/20261009_urbanrm269_10681only_freezefix')
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')

def main():
    assert not NEW.exists(), 'Preserve an existing repair dispatch'
    state=read(OLD/'chain_state.json')
    assert state['stage']=='failed_or_stopped_no_retry' and state['native_dispatches']==0
    proof=read(OLD/'freeze_repair_validation.json')
    assert proof['status']=='passed_actual_source_enumeration' and proof['source_errors']==0
    assert not proof['excluded_command_or_model_pins']
    assert not list(Path('E:/VISSIM_runs/20261009_urbanrm269_10681only_s29/selected').glob('runlog_*.txt'))
    assert read(P/'status.json')['stage']=='preflight_complete'
    backup=HERE/'before_freeze_repair';backup.mkdir(exist_ok=False)
    paths=(P/'protocol.json',HERE/'launch_plan.json',HERE/'native_preparation.json',HERE/'plan.json')
    for p in paths:shutil.copy2(p,backup/p.name)
    freezer=U/'tools/sdmpc31/freeze_worktree.ps1'
    manifest=U/'diagnostics/sdmpc_n31_20260924/tools/freeze_manifest.py'
    protocol=read(P/'protocol.json');changed={}
    for p,digest in protocol['command_pins'].items():
        observed=sha(Path(p))
        if observed!=digest:
            assert Path(p)==freezer, p
            changed[p]=dict(before=digest,after=observed)
            protocol['command_pins'][p]=observed
    assert len(changed)==1
    before=read(backup/'protocol.json')
    assert {k:v for k,v in before.items() if k!='command_pins'}=={k:v for k,v in protocol.items() if k!='command_pins'}
    save(P/'protocol.json',protocol)
    launch=read(HERE/'launch_plan.json')
    repinned={}
    for p,digest in launch['source_pins'].items():
        observed=sha(Path(p))
        if observed!=digest:
            assert Path(p) in (P/'protocol.json',freezer,manifest),p
            repinned[p]=dict(before=digest,after=observed)
            launch['source_pins'][p]=observed
    for p in (Path(__file__),HERE/'test_freeze_scope.py'):
        launch['source_pins'][str(p)]=sha(p)
    receipt=dict(time_utc=datetime.now(timezone.utc).isoformat(),
        cause='Sandbox ACL on exactly one synthetic pytest basetemp; robocopy directory failure, no traffic-input copy failures.',
        old_runtime=str(OLD),failed_tree_preserved=True,source_permissions_changed=False,deleted_files=0,
        source_enumeration=proof,protocol_nonpin_fields_unchanged=True,
        commands_and_preflight_inputs_unchanged=True,prior_native_dispatches=0,
        freeze_tool_pins_changed=changed,launch_pins_changed=repinned,
        previous_unconditional_retry=False,root_cause_repair_validated=True,
        next_runtime=str(NEW),maximum_new_native_arms=1,automatic_retries=0)
    save(HERE/'freeze_repair.json',receipt)
    launch['source_pins'][str(HERE/'freeze_repair.json')]=sha(HERE/'freeze_repair.json')
    launch.update(status='diagnosed_freeze_repair_ready',runtime=str(NEW),
        previous_failed_runtime=str(OLD),freeze_scope_tests_passed=3,prior_native_dispatches=0)
    save(HERE/'launch_plan.json',launch)
    preparation=read(HERE/'native_preparation.json')
    preparation.update(status='preflight_complete_freeze_repair_ready',runtime=str(NEW),
        protocol_sha256=sha(P/'protocol.json'),native_runs=0,freeze_repair=str(HERE/'freeze_repair.json'))
    save(HERE/'native_preparation.json',preparation)
    stage=read(HERE/'plan.json')
    stage.update(status='freeze_failed_root_cause_fixed_native_unstarted',
        freeze_repair=str(HERE/'freeze_repair.json'),native_runtime=str(NEW),new_native_runs=0)
    save(HERE/'plan.json',stage)
    parent=read(H/'plan.json')
    parent['isolated10681'].update(status='freeze_tool_repaired_native_unstarted',runtime=str(NEW),freeze_repair=str(HERE/'freeze_repair.json'))
    parent['previous_goal_turn']=dict(time_utc=receipt['time_utc'],classification='progress',
        completed=['Owned freeze terminal failure diagnosed: exactly one unreadable synthetic pytest scratch directory; no native dispatched.',
                   'Canonical copy and manifest exclusions now agree for that exact scratch only; other unreadable input directories fail closed;3tests and actualsource enumeration pass.',
                   'Failed tree/receipts preserved, no permissions/deletion/traffic/model/command changes; prepared native remains one arm.',
                   'Static review confirms diagnostic candidate still requires scalar/AD worker integration after native validation.'],
        next='One corrected canonical freeze in new runtime, then the same single prepared10681-only native comparison. No blind or native retry.')
    save(H/'plan.json',parent)
    print('FREEZE_REPAIR_REPINNED',len(repinned),'launch pins; native launches0',flush=True)

if __name__=='__main__':main()
