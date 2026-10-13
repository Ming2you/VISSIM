"""Record334/335 evidence and the remaining actual-goal requirements."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
HERE=Path(__file__).resolve().parent;A=HERE.parent;H=A.parent;W=A/'worker334'
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def main():
    assert not (HERE/'completion.json').exists()
    worker=read(W/'assessment.json');probe=read(HERE/'assessment.json');search=read(HERE/'search_review.json')
    assert worker['status']=='same_latest_model_continuous_scalar_ad_passed'
    assert probe['status']=='complete_two_bounded_responses'
    assert abs(probe['small_direction']['omega_fd']-probe['small_direction']['omega_ad'])<0.0001
    assert all(r['cap_feasible'] for r in probe['continuous'].values())
    assert search['existing_finite_meter_audit'] is True
    pins={**worker['source_pins'],**probe['source_pins']}
    for p,h in pins.items():assert sha(Path(p))==h,p
    for p in (W/'README.md',W/'rm_sensitivity.json',W/'assessment.json',HERE/'README.md',HERE/'search_review.json',HERE/'assessment.json',Path(__file__)):
        pins[str(p)]=sha(p)
    now=datetime.now(timezone.utc).isoformat()
    next_step=('Run one bounded full SDMPC3300 choice using the exact qualified331/329 model and diagnostic runtime hooks, '
        'same canonical worker bootstrap, FW5/U10,450s,terminalOFF,Omega701,2outer/2restoration/8derivative workers. '
        'Ensure the actual coordinator state, copied follower, Query template and scalar/AD worker all use latest model; '
        'do not only patch a reporting predictor. Reuse334/335 evidence, do not repeat these forecasts or fit the tiny net sign. '
        'Inspect finite RM candidate evaluation under same caps; meter_neighbors already exists, so do not add duplicate probes. '
        'AD first-block local RM direction is numerically consistent, but extrapolated large RM costs/caps are very different '
        'from nonlinear response. Record best feasible selection and timing, not unproven optimum. '
        'Whole city/joint native ranking and unused state/seed still unqualified. No native or push in this handoff.')
    stages=dict(worker334=dict(status=worker['status'],readme=str(W/'README.md'),assessment=str(W/'assessment.json'),
                              axes=213,successful_ad=1,failed_ad_attempts=2,scalar=1,ad_wall_sec=worker['timings']['ad']['wall_sec_including_imports']),
                rm_probe335=dict(status=probe['status'],readme=str(HERE/'README.md'),assessment=str(HERE/'assessment.json'),
                                 scalar=2,ad=0,fits=0,native=0,local_slope_verified=True,
                                 finite_model_omega_delta=probe['finite_step']['omega_delta'],
                                 linearized_omega_delta=probe['finite_step']['active_branch_linear_omega']))
    for parent in (A,H):
        p=parent/'plan.json';backup=parent/'plan.before334_335.json'
        assert not backup.exists();backup.write_bytes(p.read_bytes())
        doc=read(p);doc.update(stages)
        doc.update(current_stage='worker334_passed_rm335_nonlinear_response_confirmed',latest_stage=str(HERE/'README.md'),
            current_workers=[],next_step=next_step,goal_complete=False,updated_utc=now,
            last_goal_turn='progress334_335_latest_worker_link_verified_and_local_vs_finite_rm_response_separated',
            latest_goal_turn_audit=dict(previous='progress333_scope_and_service_evidence; intervening heartbeat completed queue status only',
                current='progress: authoritative frozen request, independent scalar/213-axis AD parity, bounded epsilon and executable RM response, timing and cap evidence saved'))
        save(p,doc)
    save(W/'completion.json',dict(stages['worker334'],completed_at=now,source_pins=worker['source_pins'],goal_complete=False))
    save(HERE/'completion.json',dict(stages,completed_at=now,source_pins=pins,next_step=next_step,
                                     production_changes=0,goal_complete=False,full_sdmpc_selection=False))
    print('COMPLETE334_335: exact latest scalar/AD; one local derivative probe; one nonlinear RM profile; next latest full SDMPC choice. Goal active.')
if __name__=='__main__':main()
