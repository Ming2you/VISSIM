"""Assess the finished, frozen125 selections; never fit or launch simulations."""
import itertools
from pathlib import Path
from .run import HERE, R, C, F, read, save, sha, losses


def main():
    status=read(HERE/'status.json');assert status['status']=='complete_pending_assessment'
    protocol=read(HERE/'protocol.json');selected=read(HERE/'selection.json');rows=read(HERE/'validation.json')
    comparisons={};ranking=[]
    for structure in ('aggregate','shared'):
        fixed=[r for r in rows if r['structure']==structure and r['mode']=='fixed']
        fitted=[r for r in rows if r['structure']==structure and r['mode']=='selected']
        assert len(fixed)==len(fitted)==9
        base=losses(fixed,selected[structure]['fixed']['z'])
        candidate=losses(fitted,selected[structure]['selected']['z'])
        for case in ('s43_early','s67_late'):
            group=[r for r in fitted if r['case']==case]
            actual=min(group,key=lambda x:x['actual']['ttt'])
            prediction=min(group,key=lambda x:x['predicted']['ttt'])
            ranking.append(dict(structure=structure,case=case,actual_best=actual['arm'],predicted_best=prediction['arm'],
                actual_regret_veh_h=prediction['actual']['ttt']-actual['actual']['ttt']))
        train=selected[structure]
        checks=dict(training_objective_improved5pct=train['training_improvement']>=.05,
            training_response_not_worse=train['selected']['loss']['response']<=train['fixed']['loss']['response'],
            meaningful_validation_signs=all(p['sign_correct'] for p in candidate['pairs'] if p['meaningful']),
            validation_response_improved10pct=candidate['response']<=.9*base['response'],
            validation_absolute_error_within110pct=candidate['absolute']<=1.1*base['absolute'],
            meaningful_best_choice=all(r['actual_regret_veh_h']<=.5 for r in ranking if r['structure']==structure))
        comparisons[structure]=dict(z=train['selected']['z'],training_improvement=train['training_improvement'],
            fixed=base,refitted=candidate,checks=checks,component_gate_pass=all(checks.values()),
            bounds='All three common multipliers remain within the predeclared local box; this is not an exhaustive calibration.')
    # Actual outcome states and model initial states must BOTH be common.
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import replay_congested_component as replay
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    records=[r for r in read(C/'data_catalog.json')['checked_records'] if r['case'] in ('s29_late','s43_early')]+common.records(False)
    initial=[]
    for case in ('s29_late','s43_early','s67_late'):
        states=[];native=[]
        for rec in [r for r in records if r['case']==case]:
            args,kw=replay.read_primitive_capture(rec['input'],rec['sha256']);states.append(args[0])
            obs=ObservationData(rec['truth']);native.append([(x['cell'],x['n_veh'],x['v_kmh']) for x in obs.cells[rec['cutoff']] if x['road']=='FW_E'])
        assert all(s==states[0] for s in states) and all(s==native[0] for s in native)
        initial.append(dict(case=case,model_current_state_equal=True,native_current_n_v_equal=True,arms=len(states)))
    for path,digest in protocol['protected_sha256'].items():assert sha(path)==digest
    assert sha(protocol['STOP']['path'])==protocol['STOP']['sha256']
    for path,digest in protocol['source_sha256'].items():assert sha(path)==digest
    # Record each meaningful VSL and RM contrast, including negative outcomes.
    report_pairs=[]
    for structure,comparison in comparisons.items():
        for mode in ('fixed','refitted'):
            for p in comparison[mode]['pairs']:
                report_pairs.append(dict(structure=structure,mode=mode,**p))
    budget={s:len([e for e in read(HERE/'evaluations.json') if e['structure']==s]) for s in comparisons}
    assert max(budget.values())<=9 and status['forecasts']<=110
    admissible={}
    for structure in comparisons:
        group=[e for e in read(HERE/'evaluations.json') if e['structure']==structure]
        base=next(e for e in group if e['tag']=='fixed')['loss']
        admissible[structure]=[dict(z=e['z'],tag=e['tag'],folder=e['folder'],objective=e['loss']['objective'],response=e['loss']['response'],
            validated_in125=e['z']==selected[structure]['selected']['z']) for e in group
            if e['loss']['objective']<=.95*base['objective'] and e['loss']['response']<=base['response']]
    result=dict(status='complete_component_assessed_not_full_gain_qualified',comparisons=comparisons,rankings=ranking,
        common_initial_checks=initial,pairs=report_pairs,evaluation_vectors=budget,forecasts=status['forecasts'],
        training_admissible_candidates=admissible,
        selection_limitation='Weighted objective minimum need not satisfy the response non-worsening gate. One aggregate training-feasible candidate was not selected for validation; do not reject it using another candidate results. No extra fit or validation beyond110calls here.',
        scope=protocol['scope'],new_native=0,new_FZP=0,production_adopted=False,goal_complete=False,
        conservation_max=max(x['conservation_max'] for x in rows),route_partition_max=max(x.get('route_error',0.) for x in rows),
        repair='Six valid forecasts retained after7.1e-15 configuration equality mismatch; tuple/list protocol preflight repaired before more forecasts. Physical equations and observations unchanged.',
        elapsed_forecast_work_sec=status['elapsed_sec']+read(HERE/'first_failure.json')['elapsed_sec'],
        interpretation='Equal predeclared local parameter/budget comparison, not arbitrary independent cells. Success on one metric is insufficient; a failed local box does not bound all dynamics-consistent calibration. No validation retuning follows.')
    save(HERE/'assessment.json',result)
    save(HERE/'completion.json',dict(status=result['status'],goal='ACTIVE_NOT_QUALIFIED',previous_goal_turn='PROGRESS',current_goal_turn='PROGRESS_bounded_two_structure_calibration_and_validation',forecasts=status['forecasts']))
    for name,c in comparisons.items():
        print(name,'z=',c['z'],'trainImprovement=',round(c['training_improvement'],4),'valid response=',c['fixed']['response'],c['refitted']['response'],'checks=',c['checks'])
        for mode in ('fixed','refitted'):
            for p in c[mode]['pairs']:
                if p['case']=='s67_late' and (p['left'],p['right']) in [('release','release_vsl90'),('hold','release'),('hold','hold_vsl90')]:
                    print(mode,p['left'],p['right'],'TTT actual/pred=',p['actual']['ttt'],p['predicted']['ttt'])
    print('ranks',ranking,'forecasts',status['forecasts'],'seconds',result['elapsed_forecast_work_sec'])


if __name__=='__main__':main()
