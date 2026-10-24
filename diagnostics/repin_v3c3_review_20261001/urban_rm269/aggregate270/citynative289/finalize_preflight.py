"""Record canonical preflight and reserve one freeze, without starting VISSIM."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(Path(p).read_bytes())
def sha(p):
    with Path(p).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()
def save(p,v):
    Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def main():
    p=read(HERE/'plan.json')
    task=Path(p['protocol']).parent
    s=read(task/'status.json')
    assert p['status']=='prepared_pending_canonical_preflight' and s['stage']=='preflight_complete'
    assert p['freeze_dispatches']==p['native_dispatches']==0
    for path,digest in p['source_pins'].items(): assert sha(path)==digest,path
    for path in (task/'launch_inputs.json',task/'selected/config_replay.json',
                 task/'selected/plant_replay.json',task/'selected/replay.vbs',
                 task/'selected/replay_sgplan.vbs',HERE/'freeze_once.ps1',Path(__file__)):
        p['source_pins'][str(path)]=sha(path)
    p.update(status='preflight_complete_freeze_reserved',preflight_passed=True,freeze_dispatches=1,
        runtime_status_authority=str(Path(p['runtime'])/'freeze_status.json'),
        updated_utc=datetime.now(timezone.utc).isoformat())
    save(HERE/'plan.json',p)
    old=HERE.parent/'citysplit287/launch_plan.json'
    old_data=read(old)
    assert old_data['native_dispatches']==0
    old_data.update(status='superseded_before_native_by_qualified_concurrency',superseded_by=str(HERE/'plan.json'))
    save(old,old_data)
    for mainplan in (HERE.parent/'plan.json',HERE.parent.parent/'plan.json'):
        doc=read(mainplan)
        doc.update(current_stage='citynative289 canonical preflight passed; one concurrent freeze reserved',
            current_receipt=str(HERE/'plan.json'),
            next_step='Check citynative289 runtime freeze receipt. After verified canonical freeze and unchanged pins/ownership/STOP checks, launch exactly one city-only replay with existing runner. Preserve the coupling268 queue and exact reserved VISSIM; no retry.',
            latest_goal_turn_audit=dict(outcome='progress',previous_turn='verified_wait',
                evidence=str(HERE/'plan.json'),reason='Removed an unnecessary serial preparation gate using the already-qualified canonical pinned-concurrency path; same command treatment.',goal_complete=False),
            updated_utc=p['updated_utc'])
        save(mainplan,doc)
    print(json.dumps(dict(status=p['status'],native_dispatches=0,freeze_dispatches=1)))


if __name__=='__main__': main()
