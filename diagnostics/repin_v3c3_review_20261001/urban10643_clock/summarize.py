"""Finalize the bounded clock/arrival audit from already saved outputs."""
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent


def read(p):
    b=p.read_bytes()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)


def main():
    assert not (HERE/'decision.json').exists()
    clocks=read(HERE/'assessment_clock_only.json')
    factor=read(HERE/'assessment_arrival_factorial.json')
    native=read(HERE/'native_clock_events.json')
    cache=read(HERE/'selected_native/rows.json.gz')
    table=[]
    cohorts={}
    for arrival in ('held','selected'):
        source=factor['native_sources'][arrival]
        # JSON str(10635) and str(10635.0) must not create two destinations.
        by_destination=Counter()
        for e in source['events']:
            d='unknown' if e['destination'] is None else str(int(e['destination']))
            by_destination[d]+=1
        data=read(HERE.parent/'lane10643_native/rows.json.gz') if arrival=='held' else cache
        initial_ids={r[1] for r in data['rows'] if r[0]==2700.1 and r[2] in (126,10641,71)}
        arrivals={e['vehicle'] for e in source['events']}
        assert initial_ids.isdisjoint(arrivals)
        n=native['47hold' if arrival=='held' else '47selected']
        missing_head_cohorts=sorted({e['vehicle'] for e in n['events']
            if e['role']=='head' and 2700.1<e['time']<=3145.1}-initial_ids-arrivals)
        cohorts[arrival]=dict(initial_n=len(initial_ids),arrivals=source['arrivals'],
            arrival_by_source=source['by_source'],arrival_by_destination=dict(by_destination),
            final_local_n=source['final_local_stock'],
            native_tracked_cohort_normal_out=source['native_normal_departures_mass_balance'],
            abnormal_removals=len(source['abnormal_removals']),
            head_ids_missing_from_tracked_cohort=missing_head_cohorts)
        for clock in ('held','selected'):
            for timing in ('early','late'):
                if arrival=='held':
                    r=clocks['results'][timing][clock+'_clock']
                else:
                    r=factor['results']['selected_arrivals_'+clock+'_clock_'+timing]
                table.append(dict(arrivals=arrival,clock=clock,timing=timing,
                    normal_out=r['departures'],local_n=r['final_n'],
                    external_wait=sum(r['backlog_by_source'].values()),
                    admitted_off10643=sum(v for k,v in r['admitted_by_source'].items()
                                         if k.startswith('off10643:')),
                    max_balance_residual=r['max_step_balance_residual']))
    own_delta={}
    for timing in ('early','late'):
        h=next(t for t in table if t['arrivals']==t['clock']=='held' and t['timing']==timing)
        s=next(t for t in table if t['arrivals']==t['clock']=='selected' and t['timing']==timing)
        own_delta[timing]=s['normal_out']-h['normal_out']
    decision=dict(status='completed_evidence_not_gain_qualified',
        scope='Tracked local126/10641/71 cohort2700.1–3145.1; not freeway or fullOmega result.',
        native_own_policy_normal_out_delta=cohorts['selected']['native_tracked_cohort_normal_out']-
                                           cohorts['held']['native_tracked_cohort_normal_out'],
        conditional_model_own_policy_normal_out_delta=own_delta,
        cohorts=cohorts,factorial=table,
        findings=[
            'Initial35vehicles and future arrival IDs are disjoint; no double-count proof in this component replay.',
            'Stopped queue, moving/local approaching stock and later boundary arrivals are distinct in the native audit.',
            'Selected lane5 last green begins with2stopped vehicles,2crossings then28.75s empty tail.',
            'Selected lane3 last green has11stopped at3030.1,7compatible+4wrong-lane destinations;42s green yields2crossings.',
            'Vehicle21111 stands lane3 at73.39m toward10635 during3035.1–3050.1 while lane4 is red and queued.',
            'No-physical-arrival shortage explanation for all green losses: eligible lane access and FIFO order also matter.',
            'Even actual policy-specific arrivals and clocks do not reproduce local discharge difference; do not fit freeway coefficients to this.',
            'Off10643 arrivals in this local replay are an endogenous observed drainage outcome, not independent desired demand.',
            'Model local initialization uses position/route and finite-volume mass; speed is not an independent ready-queue state.'
        ],
        limits=['5s sampling cannot establish exact ready times, complete lane-change chronology or every short whole-area traversal.',
                'Native normal discharge excludes2abnormal removals per policy; model keeps all vehicles, a retained comparison limitation.',
                'The two policies change several city signals; observed differences are not isolated RM effects.',
                'Future observations are diagnostic inputs only. No autonomous gain or9000 qualification.',
                'First two clock tests used stale signal-gated receiving and are invalid; preserved separately.'],
        next='Validate eligible head-queue composition and within-green arrivals at the same actual state, including lane access and exchange; reuse prior rejected exchange/FIFO candidates rather than repeat their grids.')
    (HERE/'decision.json').write_text(json.dumps(decision,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for p,h in factor['production_exact'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert hashlib.sha256(stop.read_bytes()).hexdigest()==factor['stop_sha256']
    current_results=[HERE/'early.json',HERE/'late.json',HERE/'early_clock_only.json',HERE/'late_clock_only.json']
    current_results += [HERE/(k+'.json') for k in factor['results']]
    completion=dict(status='completed_bounded_conditional_audit',goal_status='ACTIVE / NOT_QUALIFIED',
        previous_goal_turn='no_progress_explanatory_answer_only',current_goal_turn='progress',
        new_component_replays=8,invalid_initial_clock_replays=2,valid_new_replays=6,
        conditional_compute_sec=sum(read(p)['wall_sec'] for p in current_results),
        full450_autonomous_forecasts=0,coefficient_fit_calls=0,new_native=0,new_fzp_passes=1,
        extraction_sec=cache['extraction_wall_sec'],extracted_source_bytes=cache['source_bytes'],
        old_held_cohort_extraction_exact=True,shared_native_initial_exact=True,
        production_changes=0,production_exact=factor['production_exact'],stop_sha256=factor['stop_sha256'],
        owned_sessions='All synchronous tools returned terminal exit codes; no background job launched.',
        preserved_failures=['assessment.json early/late clock/held-budget incompatibility',
            'run_arrival_factorial.log preflight rejected5s skipped70/10776; zero forecasts before guard repair'],
        source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                       [HERE/'audit.py',Path(__file__)]},push=0,next=decision['next'])
    (HERE/'completion.json').write_text(json.dumps(completion,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(cohorts=cohorts,own_policy_delta=own_delta,
                         native_delta=decision['native_own_policy_normal_out_delta'],
                         compute_sec=completion['conditional_compute_sec']),ensure_ascii=False))


if __name__=='__main__':
    main()
