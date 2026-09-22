"""Run the existing bounded nonlinear restoration after the recorded proposal.

No cap/tolerance/model changes and no derivative recalculation. The measured
candidate is reconstructed through the normal decoder and must match every
recorded field after JSON normalization before its residual is reused.
"""
from pathlib import Path
import hashlib
import json
import pickle
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def main():
    from diagnostics.check_sdmpc_three_blocks import context
    from diagnostics.check_sdmpc_sequence_transport import qualify
    from evaluation.controllers import sdmpc,sdmpc_sequence as seq,area_follower_objective as joint
    from evaluation.controllers import area_leader_objective as constraints
    from src.models.state import ControlAction
    source,previous,out=map(Path,sys.argv[1:4]);out.mkdir(parents=True,exist_ok=False)
    request=pickle.loads((source/'request.pickle').read_bytes())
    result=json.loads((source/'result.json').read_text())
    report=json.loads((previous/'report.json').read_text())
    for name,expected in result['transformed_source_sha256'].items():
        actual=hashlib.sha256(Path(name).read_bytes()).hexdigest()
        if actual!=expected:
            if Path(name).resolve()!=Path(seq.__file__).resolve():raise ValueError('Source changed: '+name)
            qualify(source,request,expected)
        request['bootstrap']['runtime_sources'][name]=actual
    coord,callbacks,ctx,options=context(request)
    follower,state,reference,forecast=request['owned'];cfg=follower.cfg
    scale=np.array([cfg.network.sdmpc_options['budget_scale_np_veh'],cfg.network.sdmpc_options['budget_scale_nuf_veh_h']])
    row=min(report['candidates'],key=lambda r:np.linalg.norm(np.array([
        r['constraints'][key]['residual'] for key in ('np','nuf')])/scale))
    anchor=seq.first_action(reference)
    anchor.N_P_star=row['constraints']['np']['target'];anchor.N_UF_star=row['constraints']['nuf']['target']
    loaded=seq.pack([ControlAction(**c) for c in row['controls']])
    action=coord.decode(coord.encode(loaded),anchor)
    controls=[{key:getattr(a,key) for key in seq.FIELDS} for a in seq.actions(action,3)]
    if json.loads(json.dumps(controls))!=row['controls']:
        raise ValueError('Reconstructed native candidate differs from recorded values')
    A=np.asarray(result['resource_jacobian'])/scale[:,None]
    target=np.array([anchor.N_P_star,anchor.N_UF_star])
    actual=np.array([row['constraints'][key]['actual'] for key in ('np','nuf')])
    query=joint.make_decision_shared_query(follower,state,reference,forecast,horizon_steps=3,
        source_fingerprint=sdmpc.token(request['bootstrap']['runtime_sources']),parallel_workers=8,
        worker_bootstrap=request['bootstrap'],unlimited_time=True)
    rows=[];started=time.perf_counter();feasible=False
    try:
        for iteration in range(cfg.network.sdmpc_options['restoration_iterations']):
            z=coord.encode(action);c=(actual-target)/scale
            G=np.vstack([coord.G,A]);lo=np.r_[coord.glo-coord.G@z,-np.inf,-c[1]];hi=np.r_[coord.ghi-coord.G@z,-c[0],-c[1]]
            step,qp=sdmpc.solve_qp(np.zeros(len(z)),np.zeros(len(z)),1.,coord.lower-z,coord.upper-z,
                G,lo,hi,cfg.network.sdmpc_options)
            if not qp['success']:
                rows.append(dict(iteration=iteration,qp=qp));break
            try:repaired=coord.decode(z+step,action)
            except ValueError as exc:
                rows.append(dict(iteration=iteration,qp=qp,error=str(exc)));break
            if sdmpc.token(repaired)==sdmpc.token(action):
                rows.append(dict(iteration=iteration,status='no_change'));break
            proof=coord.validate(repaired)
            value=query((repaired,))['results'][0]
            q=constraints.shared_quantity_constraints(follower,repaired,value['quantities'],
                start_sec=state.time_sec,horizon_steps=3,np_mode='cap',target_np_veh=repaired.N_P_star,
                np_tolerance_veh=options['np_tolerance_veh'],nuf_mode='equality',
                target_nuf_veh_h=repaired.N_UF_star,nuf_tolerance_veh_h=options['nuf_tolerance_veh_h'])
            validation=joint.validate_actual_decision_hold(follower,state,repaired,value,
                callbacks=callbacks,context=ctx,source_fingerprint=sdmpc.token(request['bootstrap']['runtime_sources']),options=options)
            feasible=validation['feasible']
            first=callbacks['command_evidence'](seq.first_action(repaired),ctx)
            if first['owner_physical_sha256']!=validation['command_evidence']['owner_physical_sha256']:
                raise ValueError('Future plan affects first command')
            rows.append(dict(iteration=iteration,qp=qp,proof=proof,constraints=q,feasible=feasible,
                objective_veh_h=value['objective_veh_h'],
                reduction_veh_h=row['held_objective_veh_h']-value['objective_veh_h'],
                block_zero_writer_proof=True,model_coverage=value['model_constraint_coverage'],
                max_resource_exceedance_veh=value['resource_summary']['max_exceedance_veh']))
            (out/f'iteration_{iteration}.pickle').write_bytes(pickle.dumps(dict(action=repaired,value=value,validation=validation),protocol=5))
            print(json.dumps(dict(iteration=iteration,feasible=feasible,np_residual=q['np']['residual'],nuf_residual=q['nuf']['residual'])),flush=True)
            action=repaired;actual=np.array([q[key]['actual'] for key in ('np','nuf')])
            if feasible:break
        answer=dict(schema='sdmpc-three-block-restoration/v1',native_applied=False,full_sdmpc_decision=False,
            source_proposal=str(previous),reconstructed_candidate_all_fields_equal=True,
            configured_iterations=cfg.network.sdmpc_options['restoration_iterations'],iterations=rows,
            feasible=feasible,wall_sec=time.perf_counter()-started,query=query.stats())
        (out/'report.json').write_text(json.dumps(answer,indent=2)+'\n')
        return 0 if feasible else 1
    finally:query.close()


if __name__=='__main__':raise SystemExit(main())
