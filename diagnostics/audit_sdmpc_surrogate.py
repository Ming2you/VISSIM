"""One offline exact-model audit AFTER approximate optimization; no native run.

This does not add exact prediction to the controller's approximate runtime.
It reports a failed exact-model constraint honestly, without changing selection.
"""
from pathlib import Path
import hashlib
import json
import pickle
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from diagnostics.sdmpc_json_records import json_records


def main():
    from diagnostics.check_sdmpc_three_blocks import context
    from evaluation.controllers import area_follower_objective as joint
    from evaluation.controllers.sdmpc import token
    folder,source,out=map(Path,sys.argv[1:4]);out.mkdir(parents=True,exist_ok=False)
    request=pickle.loads((source/'request.pickle').read_bytes())
    decision_folder=sys.argv[4] if len(sys.argv)>4 else 'full_decision_v1'
    solve=pickle.loads((folder/decision_folder/'result.pickle').read_bytes())
    if not solve['completed']:raise ValueError('No completed approximate solve')
    for path,digest in solve['source_sha256'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest:raise ValueError('Source changed: '+path)
    request['bootstrap']['runtime_sources']=solve['source_sha256']
    coord,callbacks,ctx,options=context(request)
    follower,state,reference,forecast=request['owned']
    if getattr(follower.cfg.network,'_sdmpc_continuous_prediction',False):
        raise ValueError('Exact audit has continuous hooks installed')
    selected=solve['response']['control']
    started=time.perf_counter()
    query=joint.make_decision_shared_query(follower,state,reference,forecast,
        horizon_steps=follower.cfg.mpc.horizon_steps,source_fingerprint=token(solve['source_sha256']),
        cache_enabled=True,parallel_workers=8,worker_bootstrap=request['bootstrap'],unlimited_time=True)
    try:
        held,item=query((reference,selected))['results']
        validation=joint.validate_actual_decision_hold(follower,state,selected,item,callbacks=callbacks,
            context=ctx,source_fingerprint=token(solve['source_sha256']),options=options)
    finally:query.close()
    control_proof=coord.validate(selected)
    changed={name:sum(a!=solve['response']['command_evidence'][name][key]
        for key,a in validation['command_evidence'][name].items())
        for name in ('owner_physical_sha256','owner_model_sha256')}
    result=dict(scope=__doc__,native_applied=False,optimization_iterations=0,
        optimization_scope='Post-solve audit only, not another optimization iteration',
        wall_sec=time.perf_counter()-started,query=query.stats(),
        held_exact_cost=held['objective_veh_h'],selected_exact_cost=item['objective_veh_h'],
        held_surrogate_cost=solve['selection']['held_objective'],
        selected_surrogate_cost=solve['selection']['selected_objective'],
        exact_cost_reduction_percent=100*(1-item['objective_veh_h']/held['objective_veh_h']),
        surrogate_cost_reduction_percent=100*(1-solve['selection']['selected_objective']/solve['selection']['held_objective']),
        exact_model_feasible=validation['feasible'],command_differences=changed,
        control_sequence=control_proof,exact_constraints=validation['final_score']['quantity_constraints'],
        surrogate_constraints=solve['selection']['final_constraints'],
        exact_max_resource_exceedance=item['resource_summary']['max_exceedance_veh'],
        constraint_coverage=item['model_constraint_coverage'],
        audit_completed=True,source_changes=[p for p,h in solve['source_sha256'].items()
            if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h])
    (out/'result.pickle').write_bytes(pickle.dumps(dict(summary=result,held=held,selected=item,validation=validation),protocol=5))
    (out/'result.json').write_text(json.dumps(json_records(result),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(json_records(result),indent=2))
    return 0 if not result['source_changes'] and not any(changed.values()) else 1


if __name__=='__main__':raise SystemExit(main())
