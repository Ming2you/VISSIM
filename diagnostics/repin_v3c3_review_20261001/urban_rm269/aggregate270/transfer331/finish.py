"""Close the integration audit with exact receipts; leave whole goal active."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

HERE=Path(__file__).resolve().parent;A=HERE.parent;H=A.parent
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
save=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')

def main():
    assert not (HERE/'completion.json').exists()
    previous=read(HERE/'build2400_v2/summary.json')
    current=read(HERE/'build3300_v2/summary.json')
    parity=read(HERE/'build2400_v2/parity2400.json')
    assert previous['status']==current['status']=='complete'
    assert parity==dict(state_differences=[],network_differences=[],forecast_equal=True)
    aliases={str(HERE/'build.py'):HERE/'build_before_coverage.txt'}
    for p,h in previous['source_pins'].items():
        candidate=Path(p)
        if sha(candidate)!=h:
            assert p in aliases and sha(aliases[p])==h,p
    for p,h in current['source_pins'].items():assert sha(p)==h,p
    assert current['initial_mass']==current['final_mass']==dict(inside=4007.,outside=1022.)
    assert 'Ran 6 tests' in (HERE/'tests_coverage.log').read_text(encoding='utf8')
    assert 'OK' in (HERE/'tests_coverage.log').read_text(encoding='utf8')
    gate=read(HERE/'build3300_v2/gate325.json')
    assert gate['initial_gate_veh']==8 and sum(gate['direct_post_calendar'].values())==4
    assert sum(gate['ready_after'].values())==1
    queue_path=Path('E:/VISSIM_runtime/20261008_coupling268_vsl_three/queue_state.json')
    queue=read(queue_path)
    queue_receipt={k:queue.get(k) for k in ('stage','freeze_count','native_launches','automatic_retries')}
    assert queue_receipt==dict(stage='complete_unanalyzed',freeze_count=1,native_launches=3,automatic_retries=0)
    assessment=dict(status='complete_current_state_transfer',at_sec=3300,
        development_initial_exact=True,current_inside_veh=4007,current_outside_veh=1022,
        gate_cohorts=dict(pre_signal=8,post_signal_transit=4,ready=1),
        corrected_missing_connectors=['10218','10224'],supported_post_gate_connectors=['10218','10223','10224'],
        forecasts=0,ad=0,optimizer=0,native=0,new_fits=0,production_adopted=False,
        goal_complete=False,queue_untouched=queue_receipt,
        preserved_failures=['build2400: sandbox dependency access','build3300: uncovered connector ownership'],
        source_pins=current['source_pins'],
        limitations=['Initial assimilation only, not450 response qualification.',
                     'Same seed saved3300, not independent or blind seed.',
                     'Unknown current destination retains baseline beta.',
                     '2400 whole city/joint gain ranking remains wrong.'])
    save(HERE/'assessment.json',assessment)
    finished=datetime.now(timezone.utc).isoformat()
    completion=dict(status='complete_current_state_transfer',completed_at=finished,
        progress_classification='progress',previous_goal_turn='no progress: clock-status restatement',
        test_count=6,initializations_completed=2,partial_failed_attempts_preserved=2,
        forecasts=0,native_runs=0,goal_status='active',goal_complete=False,
        evidence={str(p):sha(p) for p in (HERE/'assessment.json',HERE/'README.md',
                                        HERE/'build3300_v2/completion.json',HERE/'build2400_v2/completion.json')})
    save(HERE/'completion.json',completion)
    next_step=('Using the331 current3300 initial state and unchanged fixed coefficients, run a bounded450s RM response pair '
        'with the identical city/VSL and shared caps, plus recorded-command response if needed. Preserve331 current-route '
        'connector coverage and all329 forecast contexts; do not deserialize and omit scoped transport/gate/service hooks. '
        'Compare actual observed response separately from hypothetical RM alternatives; no native causal claim from one observed '
        'trajectory. Then qualify full AD and one SDMPC choice only if large response evidence warrants it. City/joint wholeOmega '
        'ranking remains open; do not tune small RM signs or declare goal achieved. KeepFW5/U10,450,terminalOFF,same demand/area; '
        'no unchanged native/full optimizer repeats,push or coefficient grids.')
    for parent in (A,H):
        path=parent/'plan.json';backup=parent/'plan.before331.json'
        assert not backup.exists()
        backup.write_bytes(path.read_bytes())
        plan=read(path)
        plan.update(current_stage='transfer331_current3300_initialized_bounded_response_next',
            current_workers=[],latest_stage=str(HERE/'README.md'),next_step=next_step,
            goal_complete=False,updated_at=finished)
        plan['transfer331']=dict(status=completion['status'],completion=str(HERE/'completion.json'),
            sha256=sha(HERE/'completion.json'),adopted=False)
        save(path,plan)
    print('COMPLETE331:3300 mass/routes preserved; forecasting and joint gain remain unqualified.')

if __name__=='__main__':main()
