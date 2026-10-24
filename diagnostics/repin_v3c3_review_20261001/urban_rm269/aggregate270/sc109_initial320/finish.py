from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

HERE=Path(__file__).resolve().parent;A=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    out=HERE/'completion.json';assert not out.exists()
    reports=[json.loads((HERE/n).read_bytes()) for n in ('review.json','current_composition.json')]
    for r in reports:
        for p,h in r['source_pins'].items():assert sha(p)==h,p
    assert 'Ran 6 tests' in (HERE/'tests.log').read_text(encoding='utf8')
    assert 'SC108_GEOMETRY311 city' in (HERE/'run.log').read_text(encoding='utf8')
    now=datetime.now(timezone.utc).isoformat()
    next_step='Fix the directly observed SC109 initial movement-information loss using existing U7b/initial route-tag semantics: all10 ready vehicles have known current left routes but model splits5through/5left; residual43 has9knownthrough/7knownleft/27unknown. Preserve current320 ETA and single physical ownership; retain an explicit prior for unknown routes rather than future destinations. Validate one bounded hold/city450 pair, then justified unused-state/AD/whole-choice checks. No more service/speed coefficient search to absorb initial routing error. Preserve FW5/U10,Omega701,horizon450,terminalOFF and immutable native queue; no automatic full native or push.'
    complete=dict(status=reports[0]['status'],goal_complete=False,production_adopted=False,
        updated_utc=now,previous_goal_turn='no progress: restated existing FW5/U10 verification; no blocker',
        this_goal_turn='progress: current-path initial calendar implemented;6tests and two autonomous450 responses; current-route audit proves ready10left was projected5through/5left',
        current_workers=[],closed_tool_session=53618,execution_exit_code=0,
        budget=reports[0]['budget'],delta_omega_veh_h=reports[0]['delta_omega_veh_h'],
        next_step=next_step,source_pins={str(p):sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.json','.md','.log')})
    out.write_text(json.dumps(complete,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for path in (A/'plan.json',A.parent/'plan.json'):
        backup=path.with_name('plan.before320.json');assert not backup.exists();backup.write_bytes(path.read_bytes())
        d=json.loads(path.read_bytes());d.update(current_stage='initial320_timing_reduced_bias_current_turn_loss_confirmed',
            latest_stage=str(HERE/'README.md'),current_workers=[],goal_complete=False,updated_utc=now,next_step=next_step,
            latest_goal_turn_audit=dict(previous=complete['previous_goal_turn'],current=complete['this_goal_turn']))
        d['sc109_initial320']=dict(status=complete['status'],completion=str(out),sha256=sha(out),adopted=False)
        temp=path.with_suffix('.tmp320.json');temp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');temp.replace(path)
    print('RECORDED320: goal active incomplete; two450 forecasts complete; current turn-projection error confirmed.')

if __name__=='__main__':main()
