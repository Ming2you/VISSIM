"""Record completed diagnostics; no production, native, or shared-cap change."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import json

HERE=Path(__file__).resolve().parent
A=HERE.parent
H=A.parent
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(path,doc):
    assert not path.exists(),path
    path.write_text(json.dumps(doc,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def main():
    now=datetime.now(timezone.utc).isoformat()
    stage309=A/'exit_timing309';stage310=A/'sc108_side310'
    for doc in (read(stage309/'assessment.json'),read(stage309/'sc109_chain.json'),read(stage310/'comparison.json'),read(HERE/'comparison.json')):
        for p,h in doc['source_pins'].items():assert sha(p)==h,p
    for p in (stage310/'tests.log',HERE/'tests.log'):
        text=p.read_text(encoding='utf8');assert 'Ran 3 tests' in text and 'OK' in text
    new=read(HERE/'comparison.json');older=read(stage310/'comparison.json')
    assert new['results']['new']['hold']['shared_constraints']['np']['violation']>0
    assert new['results']['new']['city']['shared_constraints']['feasible']
    assert not new['adopted'] and not new['goal_complete']
    next_step='Reuse Claude U7 and309 native head/cohort records to diagnose SC107 physical W discharge control response and upstream66/69 source timing/finite receiving. Do not retune21 or SC109 to force the remaining sign. Preserve same demand/area, FW5/urban10, horizon450, terminalOFF, and immutable native queue. Qualify justified composite with fullAD, unused-state response and actual NP/NUF-feasible SDMPC choice within600s; saved hold command currently exceeds NP, so never call the pair jointly feasible or widen cap to pass.'
    common=dict(goal_complete=False,updated_utc=now,production_adopted=False,native_changed=False,pushes=0,
        previous_goal_turn='no_progress: clock clarification reused existing completed evidence',
        this_goal_turn='progress: native upstream cohort/head audit, two bounded service/geometry corrections, six meaningful tests, four450 predictions, and unused3300 stock-preserving geometry check',
        next_step=next_step)
    d309=dict(common,status='complete_exit_timing_and_upstream_chain_diagnostic',budget=dict(new_forecasts=0,closed_fzp_passes=2,new_native=0,fits=0),
        extraction_note='The two source passes and3extraction tests were already completed before this continuation; this continuation reused their cache without rescanning.',
        next_stage=str(stage310),source_pins={str(p):sha(p) for p in stage309.iterdir() if p.suffix in ('.py','.json','.md','.log')})
    write(stage309/'completion.json',d309)
    for path,report,session in ((stage310,older,85351),(HERE,new,7936)):
        done=dict(common,status=report['status'],budget=report['budget'],tests_passed=3,
            delta_omega_veh_h=report['delta_omega_veh_h'],native_delta_omega_veh_h=report['native_delta_omega_veh_h'],
            absolute_gain_error_reduction_veh_h=report['absolute_gain_error_reduction_veh_h'],
            shared_cap_pass={arm:r['shared_constraints']['feasible'] for arm,r in report['results']['new'].items()},
            hold_np_violation_veh=report['results']['new']['hold']['shared_constraints']['np']['violation'],
            owned_tool_session=session,owned_process_exited=True,exit_code=0,
            full_ad=0,full_selection=0,unseen_state_forecasts=0,
            unseen_initialization_only=(path==HERE),
            source_pins={str(p):sha(p) for p in path.iterdir() if p.suffix in ('.py','.json','.md','.log')})
        write(path/'completion.json',done)
    for p in (A/'plan.json',H/'plan.json'):
        backup=p.with_name('plan.before311.json');assert not backup.exists();backup.write_bytes(p.read_bytes())
        doc=read(p)
        doc.update(current_stage='sc108_geometry311_complete_whole_gain_unqualified',goal_complete=False,current_workers=[],updated_utc=now,
            next_step=next_step,latest_stage=str(HERE/'README.md'),
            latest_goal_turn_audit=dict(previous=common['previous_goal_turn'],current=common['this_goal_turn']),
            current_prediction_clock=dict(freeway_exchange_sec=5,urban_exchange_sec=10,control_sec=150,horizon_sec=450,terminal_cost=False,necessary_internal_stability_substeps_retained=True))
        for stage in (stage309,stage310,HERE):
            done=read(stage/'completion.json')
            doc[stage.name]=dict(status=done['status'],completion=str(stage/'completion.json'),sha256=sha(stage/'completion.json'),adopted=False)
        tmp=p.with_suffix('.json.tmp311');tmp.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8');tmp.replace(p)
    print('RECORDED',json.dumps(dict(goal_complete=False,full450_this_turn=4,tests_this_turn=6,delta_omega=new['delta_omega_veh_h'],hold_np_violation=new['results']['new']['hold']['shared_constraints']['np']['violation'])))


if __name__=='__main__':main()
