from pathlib import Path
from datetime import datetime,timezone
import hashlib
import json

HERE=Path(__file__).resolve().parent
A=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    out=HERE/'completion.json';assert not out.exists()
    reports=[json.loads((HERE/n).read_bytes()) for n in ('diagnosis.json','initial_trace.json')]
    for report in reports:
        for p,h in report['source_pins'].items():assert sha(p)==h,p
    extraction=Path('E:/VISSIM_analysis/20261010_sc109_arrival319/completion.json')
    cache=json.loads(extraction.read_bytes());assert cache['status']=='complete' and cache['source_passes']==2
    for arm,r in cache['arms'].items():assert sha(r['cache'])==r['sha256'],arm
    now=datetime.now(timezone.utc).isoformat()
    next_step=('SC109 initial calendar lumps41moving vehicles at+20s while hold green closes+25s, creating25.5967 waiting through vehicles; initial-cohort passive attribution shows city benefit-0.512/-0.553vehh versus native-0.039. '
               'Implement one bounded current-position/speed/physical-path initial-calendar candidate for SC108_to_SC109, initially preserving existing queues, composition, mass/ownership, rates, commands and new-arrival317 transport to isolate timing. '
               'Compare two autonomous450s fixed-command responses against317, not future-conditioned318; preserve route/lane tags and explicitly retain unresolved composition limits. No future diagnostic data as predictor input. '
               'Then qualify justified aggregate corrections with unused-state and whole-choice checks; do not claim completion from a partial timing gain. Keep FW5/U10,Omega701,horizon450,terminalOFF and immutable queue; no coefficient grid/new full native/push.')
    done=dict(status='complete_sc109_initial_timing_bias_and_platoon_diagnosis',goal_complete=False,
        production_adopted=False,previous_goal_turn='progress: canonical source correction and two conditional forecasts',
        this_goal_turn='progress: retained missing closed trajectories once, separated matched platoon moving/stopped delay, traced model initial cohort and found false early-green timing benefit',
        updated_utc=now,current_workers=[],next_step=next_step,
        budget=dict(new_forecasts=0,native=0,optimizer=0,fits=0,source_fzp_passes=2),
        extraction_completion=str(extraction),extraction_sha256=sha(extraction),
        source_pins={str(p):sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.json','.md','.log')})
    out.write_text(json.dumps(done,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for path in (A/'plan.json',A.parent/'plan.json'):
        backup=path.with_name('plan.before319.json');assert not backup.exists();backup.write_bytes(path.read_bytes())
        d=json.loads(path.read_bytes())
        d.update(current_stage='arrival319_initial_calendar_bias_confirmed_candidate_pending',latest_stage=str(HERE/'README.md'),
                 current_workers=[],goal_complete=False,updated_utc=now,next_step=next_step,
                 latest_goal_turn_audit=dict(previous=done['previous_goal_turn'],current=done['this_goal_turn']))
        d['sc109_arrival319']=dict(status=done['status'],completion=str(out),sha256=sha(out),adopted=False)
        temp=path.with_suffix('.tmp319.json');temp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');temp.replace(path)
    print('RECORDED319: concrete initial-calendar bias; goal active incomplete; no live offline worker.')


if __name__=='__main__':main()
