from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

HERE=Path(__file__).resolve().parent;A=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    out=HERE/'completion.json';assert not out.exists()
    report=json.loads((HERE/'assessment.json').read_bytes())
    for p,h in report['source_pins'].items():assert sha(p)==h,p
    hold=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/decisions_sdmpc31_g_2400_hold_s29/state_002400.json')
    city=Path('E:/VISSIM_runs/20261010_urbanrm269_cityonly289_s29/selected/decisions_sdmpc31_g_2400_selected_s29/state_002400.json')
    inputs=[json.loads(p.read_bytes()) for p in (hold,city)]
    assert inputs[0]['vehicle_records']['records']==inputs[1]['vehicle_records']['records']
    frames=[p.parent/d['obs150']['frames']['current']['path'] for p,d in zip((hold,city),inputs)]
    rows=[json.loads(p.read_bytes())['vehicles'] for p in frames]
    assert rows[0]==rows[1]
    now=datetime.now(timezone.utc).isoformat()
    done=dict(status=report['status'],goal_complete=False,production_adopted=False,current_workers=[],
        previous_goal_turn='progress_sc16_323_bounded_candidate_local_level_improved_without_material_gain',
        this_goal_turn='progress_SC12_initial_platoon_bypasses_SC10_fixed_signal_same9vehicles_miss_earlier_green',
        closed_tool_session=38718,execution_exit_code=0,budget=report['budget'],common_initial_vehicles_and_routes_identical=True,
        local_cohort_head_delay_veh_h=report['cohort_head_delay_veh_h'],updated_utc=now,next_step=report['next_step'],
        source_pins={str(p):sha(p) for p in [*frames,hold,city,*[p for p in HERE.iterdir() if p.suffix in ('.py','.json','.log','.md')]]})
    out.write_text(json.dumps(done,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for path in (A/'plan.json',A.parent/'plan.json'):
        backup=path.with_name('plan.before324.json');assert not backup.exists();backup.write_bytes(path.read_bytes())
        d=json.loads(path.read_bytes());d.update(current_stage='sc12_platoon324_intermediate_signal_bypass_reproduced',
            latest_stage=str(HERE/'README.md'),current_workers=[],goal_complete=False,updated_utc=now,next_step=done['next_step'],
            latest_goal_turn_audit=dict(previous=done['previous_goal_turn'],current=done['this_goal_turn']))
        d['sc12_platoon324']=dict(status=done['status'],completion=str(out),sha256=sha(out),adopted=False)
        tmp=path.with_suffix('.tmp324.json');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');tmp.replace(path)
    print('RECORDED324: same initial state verified; middle-signal/platoon omission reproduced; goal remains active.')

if __name__=='__main__':main()
