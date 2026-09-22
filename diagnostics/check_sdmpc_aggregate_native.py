"""Original actuator model check for held and validated three-block commands."""
from pathlib import Path
import hashlib
import json
import pickle
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def main():
    from diagnostics.check_sdmpc_three_blocks import context
    from evaluation.controllers import area_follower_objective as joint,sdmpc,sdmpc_sequence as seq
    from evaluation.controllers import area_leader_objective as constraints
    source,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=False)
    request=pickle.loads((source/'request.pickle').read_bytes())
    receipt=json.loads((source/'result.json').read_text())
    for name,expected in receipt['transformed_source_sha256'].items():
        actual=hashlib.sha256(Path(name).read_bytes()).hexdigest()
        if actual!=expected:raise ValueError('Qualified aggregate source changed: '+name)
        request['bootstrap']['runtime_sources'][name]=expected
    coord,callbacks,ctx,options=context(request)
    follower,state,reference,forecast=request['owned'];cfg=follower.cfg
    prior=ROOT/'diagnostics/sdmpc_sequence_20260921/sequence_restoration'
    witness=pickle.loads((prior/'iteration_1.pickle').read_bytes())
    selected=witness['action'];coord.validate(selected)
    query=joint.make_decision_shared_query(follower,state,reference,forecast,horizon_steps=3,
        source_fingerprint=sdmpc.token(request['bootstrap']['runtime_sources']),parallel_workers=8,
        worker_bootstrap=request['bootstrap'],unlimited_time=True)
    started=time.perf_counter()
    try:
        values=query((reference,selected))['results']
        rows=[]
        for name,action,value in zip(('held','selected'),(reference,selected),values):
            q=constraints.shared_quantity_constraints(follower,action,value['quantities'],
                start_sec=state.time_sec,horizon_steps=3,np_mode='cap',target_np_veh=selected.N_P_star,
                np_tolerance_veh=options['np_tolerance_veh'],nuf_mode='equality',target_nuf_veh_h=selected.N_UF_star,
                nuf_tolerance_veh_h=options['nuf_tolerance_veh_h'])
            rows.append(dict(name=name,ttt_veh_h=value['objective_veh_h'],constraints=q,
                coverage=value['model_constraint_coverage'],model_feasible=value['conditional_model_feasibility_witness'],
                resource_exceedance_veh=value['resource_summary']['max_exceedance_veh']))
        validation=joint.validate_actual_decision_hold(follower,state,selected,values[1],
            callbacks=callbacks,context=ctx,source_fingerprint=sdmpc.token(request['bootstrap']['runtime_sources']),options=options)
        first=callbacks['command_evidence'](seq.first_action(selected),ctx)
        first_only=first['owner_physical_sha256']==validation['command_evidence']['owner_physical_sha256']
        old_selected=witness['value']
        old_proposal=json.loads((ROOT/'diagnostics/sdmpc_sequence_20260921/sequence_proposal_v3/report.json').read_text())
        checks=dict(held_ttt_error=abs(rows[0]['ttt_veh_h']-old_proposal['candidates'][0]['held_objective_veh_h']),
            selected_ttt_error=abs(rows[1]['ttt_veh_h']-old_selected['objective_veh_h']))
        old_q=witness['validation']['final_score']['quantity_constraints']
        checks.update({key+'_error':abs(rows[1]['constraints'][key]['actual']-old_q[key]['actual']) for key in ('np','nuf')})
        report=dict(schema='sdmpc-aggregate-original-actuator-check/v1',native_applied=False,
            rows=rows,checks=checks,selected_feasible=validation['feasible'],first_block_only=first_only,
            pass_all=max(checks.values())<=1e-7 and validation['feasible'] and first_only,
            wall_sec=time.perf_counter()-started,query=query.stats())
        (out/'witness.pickle').write_bytes(pickle.dumps(dict(values=values,validation=validation),protocol=5))
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k not in ('rows','query')}),flush=True)
        return 0 if report['pass_all'] else 1
    finally:query.close()


if __name__=='__main__':raise SystemExit(main())
