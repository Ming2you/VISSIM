from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

HERE=Path(__file__).resolve().parent;A=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    out=HERE/'completion.json';assert not out.exists()
    r=json.loads((HERE/'assessment.json').read_bytes());c=json.loads((HERE/'cohorts.json').read_bytes())
    for doc in (r,c):
        for p,h in doc['source_pins'].items():assert sha(p)==h,p
    assert abs(c['total_delta_TTT_veh_h']-r['delta_omega']['native'])<1e-7
    now=datetime.now(timezone.utc).isoformat()
    next_step='Prioritize post-initial aggregate arrivals: review Claude F2/U7 and current source/urban arrival generation, route composition and signal-window readiness. Use existing three-block/native event records to separate different actual admissions from new-cohort discharge timing. No SC10/SC12 nominal rate/beta/ETA grid. Source318 belongs to317 and cannot be added to326. Keep wholeOmega objective and FW5/urban10; no unchanged optimization/native repeat.'
    done=dict(status='complete_whole_inventory_time_and_initial_roster_partition327',
        previous_goal_turn='progress326_shared_cap_candidate_tested_and_rejected',
        this_goal_turn='progress327_exact_mass_time_error_and_initial_roster_partition_changes_next_priority',
        goal_complete=False,production_adopted=False,current_workers=[],execution_exit_code=0,
        delta_omega=r['delta_omega'],error_parts=r['error_native_minus_model'],
        native_initial_cohort_delta=c['delta_TTT_veh_h_by_initial_cohort'],budget=r['budget'],
        next_step=next_step,updated_utc=now,source_pins={str(p):sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.json','.log','.md')})
    out.write_text(json.dumps(done,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for path in (A/'plan.json',A.parent/'plan.json'):
        backup=path.with_name('plan.before327.json');assert not backup.exists();backup.write_bytes(path.read_bytes())
        d=json.loads(path.read_bytes());d.update(current_stage='balance327_post_initial_arrivals_and_departure_timing_priority',
            latest_stage=str(HERE/'README.md'),current_workers=[],goal_complete=False,updated_utc=now,next_step=next_step,
            latest_goal_turn_audit=dict(previous=done['previous_goal_turn'],current=done['this_goal_turn']))
        d['balance327']=dict(status=done['status'],completion=str(out),sha256=sha(out),adopted=False)
        tmp=path.with_suffix('.tmp327.json');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');tmp.replace(path)
    print('RECORDED327: exact existing-result decomposition; no new runs or forecasts; goal active/incomplete.')

if __name__=='__main__':main()
