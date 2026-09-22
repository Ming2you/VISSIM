"""One prox-linear step plus original-model sequence/first-command validation.

This diagnostic freezes NP at the measured held NP and NUF at the measured
held actual merge. It is not a full outer-cap search or convergence claim.
"""
from pathlib import Path
import json
import hashlib
import pickle
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def main():
    from diagnostics.check_sdmpc_three_blocks import context
    from evaluation.controllers import sdmpc,sdmpc_sequence as seq,area_follower_objective as joint
    from evaluation.controllers import area_leader_objective as constraints
    source,out=Path(sys.argv[1]),Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=False)
    with (source/'request.pickle').open('rb') as f: request=pickle.load(f)
    result=json.loads((source/'result.json').read_text())
    if 'error' in result:raise ValueError('Unqualified derivative input')
    equivalence=[]
    for name,expected in result['transformed_source_sha256'].items():
        actual=hashlib.sha256(Path(name).read_bytes()).hexdigest()
        if actual!=expected:
            if Path(name).resolve()!=Path(seq.__file__).resolve():
                raise ValueError('Derivative source changed before native-model qualification: '+name)
            from diagnostics.check_sdmpc_sequence_transport import qualify
            equivalence.append(qualify(source,request,expected))
        request['bootstrap']['runtime_sources'][name]=actual
    (out/'source_equivalence.json').write_text(json.dumps(equivalence,indent=2)+'\n')
    coord,callbacks,ctx,options=context(request)
    follower,state,reference,forecast=request['owned'];cfg=follower.cfg
    query=joint.make_decision_shared_query(follower,state,reference,forecast,
        horizon_steps=3,source_fingerprint=sdmpc.token(request['bootstrap']['runtime_sources']),
        parallel_workers=8,worker_bootstrap=request['bootstrap'],unlimited_time=True)
    started=time.perf_counter()
    try:
        held=query((reference,))['results'][0]
        def quantities(action,value):
            return constraints.shared_quantity_constraints(follower,action,value['quantities'],
                start_sec=state.time_sec,horizon_steps=3,np_mode='cap',target_np_veh=action.N_P_star,
                np_tolerance_veh=options['np_tolerance_veh'],nuf_mode='equality',
                target_nuf_veh_h=action.N_UF_star,nuf_tolerance_veh_h=options['nuf_tolerance_veh_h'])
        measured=quantities(reference,held)
        anchor=seq.first_action(reference)
        anchor.N_P_star=measured['np']['actual'];anchor.N_UF_star=measured['nuf']['actual']
        z=coord.encode(anchor)
        gradient=np.asarray(result['cost_jacobian']).sum(axis=0)
        scale=np.array([cfg.network.sdmpc_options['budget_scale_np_veh'],cfg.network.sdmpc_options['budget_scale_nuf_veh_h']])
        A=np.asarray(result['resource_jacobian'])/scale[:,None]
        tick=time.perf_counter()
        raw=np.zeros(len(z));local_qps=[]
        # Same owner-local own+externality step and resource projection as
        # sdmpc.solve, at the initial zero-price reference.
        for owner in coord.owners:
            ix=np.array([j for j,a in enumerate(coord.axes) if a['owner']==owner])
            d,receipt=sdmpc.solve_qp(np.zeros(len(ix)),gradient[ix],cfg.network.sdmpc_options['proximal'],
                coord.lower[ix]-z[ix],coord.upper[ix]-z[ix],coord.G[:,ix],
                coord.glo-coord.G@z,coord.ghi-coord.G@z,cfg.network.sdmpc_options)
            local_qps.append(dict(owner=owner,**receipt))
            if not receipt['success']:raise ValueError(local_qps[-1])
            raw[ix]=d
        G=np.vstack([coord.G,A]);lo=np.r_[coord.glo-coord.G@z,-np.inf,0.];hi=np.r_[coord.ghi-coord.G@z,0.,0.]
        step,qp=sdmpc.solve_qp(raw,np.zeros(len(z)),1.,coord.lower-z,coord.upper-z,
            G,lo,hi,cfg.network.sdmpc_options)
        qp_sec=time.perf_counter()-tick
        if not qp['success']:raise ValueError(qp)
        candidates=[];projection=[]
        for exponent in range(cfg.network.sdmpc_options['line_search_steps']):
            try:
                action=coord.decode(z+step*(.5**exponent),anchor)
                proof=coord.validate(action)
            except ValueError as exc:
                projection.append(dict(fraction=.5**exponent,error=str(exc)));continue
            if sdmpc.token(action) in {sdmpc.token(c) for c in candidates}:continue
            candidates.append(action);projection.append(dict(fraction=.5**exponent,proof=proof))
        if not candidates:raise ValueError('No executable three-block proposal')
        print(json.dumps(dict(stage='native_sequence_candidates',count=len(candidates),qp_sec=qp_sec)),flush=True)
        values=query(tuple(candidates))['results']
        rows=[]
        for action,value in zip(candidates,values):
            q=quantities(action,value)
            evidence=callbacks['command_evidence'](action,ctx)
            first_evidence=callbacks['command_evidence'](seq.first_action(action),ctx)
            first_only=evidence['owner_physical_sha256']==first_evidence['owner_physical_sha256']
            if not first_only:raise ValueError('Future controls changed block-zero writer output')
            encoded=coord.encode(action).reshape(3,coord.width)
            row=dict(action_token=sdmpc.token(action),objective_veh_h=value['objective_veh_h'],
                held_objective_veh_h=held['objective_veh_h'],
                reduction_veh_h=held['objective_veh_h']-value['objective_veh_h'],
                constraints=q,model_coverage=value['model_constraint_coverage'],
                model_feasible=value['conditional_model_feasibility_witness'],
                max_resource_exceedance_veh=value['resource_summary']['max_exceedance_veh'],
                changed_axes_by_block=[int(np.count_nonzero(abs(x)>1e-9)) for x in encoded],
                adjacent_blocks_differ=[bool(np.any(abs(encoded[k]-encoded[k-1])>1e-9)) for k in (1,2)],
                block_zero_writer_proof=first_only,command_rows=len(evidence['ordered_rows']),
                controls=[{key:getattr(a,key) for key in seq.FIELDS} for a in seq.actions(action,3)])
            row['all_constraints_passed']=(q['feasible'] and value['conditional_model_feasibility_witness']
                and value['model_constraint_coverage']['complete'] and value['resource_summary']['max_exceedance_veh']<=options['shared_tolerance'])
            rows.append(row)
        report=dict(schema='sdmpc-three-block-single-step/v1',native_applied=False,
            full_sdmpc_decision=False,target_source='measured_hold_np_and_actual_merge_nuf',
            derivative_to_native_source_equivalence=equivalence,
            local_qps=local_qps,qp=qp,qp_sec=qp_sec,projection=projection,candidates=rows,
            feasible_candidates=sum(r['all_constraints_passed'] for r in rows),
            improving_feasible_candidates=sum(r['all_constraints_passed'] and r['reduction_veh_h']>0 for r in rows),
            query=query.stats(),wall_sec=time.perf_counter()-started)
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k not in ('candidates','query','projection')}),flush=True)
        return 0 if report['feasible_candidates'] else 1
    finally:query.close()


if __name__=='__main__':raise SystemExit(main())
