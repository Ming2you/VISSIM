"""Record completed evidence without changing active runs or adopting a candidate."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
A=HERE.parent
H=A.parent
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(path,data):
    tmp=path.with_suffix(path.suffix+'.tmp308')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    tmp.replace(path)


def main():
    now=datetime.now(timezone.utc).isoformat()
    assert not (HERE/'completion.json').exists()
    result=read(HERE/'comparison.json')
    for p,h in result['source_pins'].items(): assert sha(p)==h,p
    native_next='Reconcile largest remaining observed-Omega-exit timing differences against model routes, keeping native admission/disappearance accounting separate. Do not increase SC109 again or tune future admissions. Use existing closed metrics and event caches before any further model change. Qualify a supported composite with full AD and unused-state feasible SDMPC choice within600s only after the material response issue is bounded.'
    timing=dict(status='complete_timing_admission_and_upstream_supply_diagnosis',goal_complete=False,
        updated_utc=now,budget=dict(new_forecasts=0,new_native=0,fzp_scans=0,fits=0),
        findings=['SC101 early-discharge benefit is observed despite fewer total departures.',
                  'SC6 initial target cohort first150 count63 is identical; later supply accounts for most head-time loss.',
                  'SC10 accepts too little upstream supply; raising its mostly nonbinding service is unsupported.',
                  'SC109 pre-existing low service persists in306 and starves SC16/SC12; old candidate requires composite validation.',
                  'Native admission accounting contributes2.6346 of5.2867vehh, not a counterfactual-adjusted control effect.'],
        next_stage=str(HERE),source_pins={str(p):sha(p) for p in (A/'timing307').iterdir() if p.suffix in ('.py','.json','.md')})
    save(A/'timing307/completion.json',timing)
    done=dict(status=result['status'],goal_complete=False,updated_utc=now,
        previous_goal_turn='no_progress: user clock clarification reused existing evidence; no new verification or change',
        this_goal_turn='progress: completed upstream limit and native head diagnosis, three tests and two new composite450 responses; established supply improvement with only0.1248vehh gain correction',
        model_delta_veh_h=result['delta_omega_veh_h']['composite'],
        previous_model_delta_veh_h=result['delta_omega_veh_h']['previous'],
        native_delta_veh_h=result['native_delta_omega_veh_h'],budget=result['budget'],
        tests_passed=3,adopted=False,full_ad=0,full_selection=0,unseen_state_forecasts=0,
        owned_tool_session=93226,owned_process_exited=True,exit_code=0,
        output='E:/VISSIM_analysis/20261010_sc109_composite308/forecast2400_v2',
        setup_failures=[dict(log='run.log',stage='import',forecasts=0),dict(log='run_v2.log',stage='output_parent_missing',forecasts=0)],
        next_step=native_next,
        source_pins={str(p):sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.json','.md','.log')})
    save(HERE/'completion.json',done)
    for path in (A/'plan.json',H/'plan.json'):
        doc=read(path)
        backup=path.with_name('plan.before308.json')
        assert not backup.exists()
        backup.write_bytes(path.read_bytes())
        doc.update(current_stage='sc109_composite308_complete_unqualified',goal_complete=False,
            current_workers=[],updated_utc=now,next_step=native_next,
            latest_goal_turn_audit=dict(previous=done['previous_goal_turn'],current=done['this_goal_turn']),
            timing307=dict(status=timing['status'],completion=str(A/'timing307/completion.json')),
            sc109_composite308=dict(status=done['status'],completion=str(HERE/'completion.json'),adopted=False,
                                  model_delta_veh_h=done['model_delta_veh_h'],native_delta_veh_h=done['native_delta_veh_h']))
        doc['current_prediction_clock']={'freeway_exchange_sec':5,'urban_exchange_sec':10,'control_sec':150,'horizon_sec':450,'terminal_cost':False,'necessary_internal_stability_substeps_retained':True}
        save(path,doc)
    print(json.dumps({k:done[k] for k in ('status','goal_complete','model_delta_veh_h','tests_passed','budget','adopted')}))


if __name__=='__main__': main()
