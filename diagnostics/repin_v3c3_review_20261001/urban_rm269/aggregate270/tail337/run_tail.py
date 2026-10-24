"""Replay saved optimization, executing only new canonical finite RM neighbors."""
from pathlib import Path
from datetime import datetime,timezone
import copy, hashlib, json, os, pickle, time, traceback
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.tail337.prepare import HERE,A,S,ROOT,read,sha,save,inputs,compatible_sources

def main():
    assert not (HERE/'tail_execution.json').exists(), 'Preserve an attempted tail'
    assert not any((p/'STOP').exists() for p in (ROOT,A.parent,A,HERE))
    pins=compatible_sources(); request,coord,writer_plan=inputs()
    from evaluation.controllers import sdmpc,sdmpc_sequence as seq,signal_actuation_contract as signals,physical_ramp_branches as ramps
    from evaluation.controllers.area_leader_objective import shared_quantity_constraints
    from evaluation.controllers.sdmpc_tangent_surrogate import Query,validate_prediction,check_scalar_upgrade,token
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.tail337.worker_runner import evaluate as worker
    joint=read(S/'full3300/unused.joint.json'); selection=joint['selection']; options=joint['options']
    follower,state,reference,forecast=request['owned']; cfg=follower.cfg
    old=pickle.loads((S/'workers/0001/request.pickle').read_bytes())
    assert all(equal(request[k],old[k]) for k in ('owned','runtime','horizon'))
    calls=0
    def bounded_worker(r):
        nonlocal calls
        calls+=1
        assert calls<=24,'New finite-neighbor forecast budget exhausted; no expansion'
        assert r['surrogate_evaluation']=='scalar'
        return worker(r)
    query=Query(request,lambda *a:None,lambda stage,**kw:print(stage,kw,flush=True),runner=bounded_worker)
    imported=[]; saved_actions=[]
    for folder in sorted((S/'workers').glob('[0-9]*')):
        if folder.name=='0000':continue
        data=(folder/'request.pickle').read_bytes(); r=pickle.loads(data)
        result=pickle.loads((folder/'result.pickle').read_bytes())
        assert hashlib.sha256(data).hexdigest()==result['request_sha256'] and 'error' not in result
        assert all(equal(r[k],old[k]) for k in ('owned','runtime','bootstrap','horizon'))
        assert r['surrogate_context_sha256']==old['surrogate_context_sha256']
        item=copy.deepcopy(result['surrogate_prediction'])
        validate_prediction(item,r['action'],r['surrogate_context_sha256'])
        assert not any(k in item for k in ('warm_budget_binding','initial_target_binding'))
        # A derived summary gets a NEW context digest after explicit source-only
        # compatibility and exact physical inputs, not a forged old identity.
        original_token=item.pop('response_token'); item['frozen_context_token']=query.context_token
        item['response_token']=token(item); validate_prediction(item,r['action'],query.context_token)
        key=query.physical_key(r['action'])
        if key in query.entries:check_scalar_upgrade(query.entries[key][1],item,query.primal_tolerance)
        else:query.entries[key]=(copy.deepcopy(r['action']),item,None)
        saved_actions.append((r['action'],item))
        imported.append(dict(folder=str(folder),request_sha256=result['request_sha256'],source_response=original_token,
            derived_response=item['response_token'],new_context=query.context_token,old_context=r['surrogate_context_sha256']))
    save('cache_import.json',dict(exact_context_values_checked=True,selection_only_compatibility='source_compatibility.json',
        saved_predictions=len(imported),unique_physical=len(query.entries),records=imported))
    def quantity(action,item):
        return shared_quantity_constraints(follower,action,item['quantities'],start_sec=state.time_sec,horizon_steps=3,
            np_mode='cap',target_np_veh=action.N_P_star,np_tolerance_veh=options['np_tolerance_veh'],
            nuf_mode='cap',target_nuf_veh_h=action.N_UF_star,nuf_tolerance_veh_h=options['nuf_tolerance_veh_h'])
    def feasible(action,item):
        coverage=item['model_constraint_coverage']
        return bool(coord.valid(coord.encode(action)) and quantity(action,item)['feasible']
            and item['conditional_model_feasibility_witness'] and coverage['complete']
            and coverage['conditional_model_feasibility_witness']
            and item['resource_summary']['max_exceedance_veh']<=options['shared_tolerance'])
    incumbents=[]
    for row in selection['meter_neighbor_audit']['budget_audits']:
        found=[]
        for action,item in saved_actions:
            if abs(item['objective_veh_h']-row['baseline_objective'])>1e-8:continue
            candidate=action.copy(); candidate.N_P_star=row['np_cap'];candidate.N_UF_star=row['nuf_target']
            for representation in (candidate,seq.pack(seq.actions(candidate,3))):
                if token(representation)==row['incumbent_action_token']:found.append(representation)
        assert found, 'Missing exact saved incumbent '+str(row)
        a=found[0]; item=query.evaluate([a])[0];assert feasible(a,item)
        incumbents.append((a,item,None))
    best=min(incumbents,key=lambda x:x[1]['objective_veh_h'])
    seed=request['action'];seed_item=query.evaluate([seed])[0]
    best,retention=sdmpc.retain_feasible_held(seed,seed_item['objective_veh_h'],best,best[0],
        cfg.network.sdmpc_options['objective_tolerance'],query.evaluate,feasible)
    assert retention['selected'] and calls==0
    held=copy.deepcopy(best)
    record=dict(status='running',pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),
        new_forecast_limit=24,optimizer_calls=0,native_calls=0,imported_responses=len(imported),source_pins=pins)
    save('tail_execution.json',record);began=time.perf_counter()
    observed=[]
    def evaluate(actions,**kw):
        items=query.evaluate(actions,**kw)
        for a,i in zip(actions,items):
            observed.append(dict(action_token=sdmpc.token(a),objective=i['objective_veh_h'],feasible=feasible(a,i),
                quantities=quantity(a,i),commands=[ramps.physical_commands(b,cfg) for b in seq.actions(a,3)],
                owners=i['sdmpc_omega_partition']['costs']))
        return items
    try:
        best,audit=sdmpc.audit_meter_budget_candidates(coord,best,incumbents,
            cfg.network.sdmpc_options['objective_tolerance'],evaluate,feasible)
        selected,item,_=best; assert feasible(selected,item)
        sequence=coord.validate(selected)
        writer=[]
        for b in seq.actions(selected,3):
            proof=signals.validate_writer(b,cfg,writer_plan,'experiment')
            writer.append(dict(proof=proof,rm=ramps.physical_commands(b,cfg),vsl=b.vsl,greens=b.green_times,offsets=b.offsets))
        partition=item['sdmpc_omega_partition']['costs']
        assert abs(sum(partition.values())-item['objective_veh_h'])<1e-7
        assert all(sha(p)==h for p,h in pins.items())
        (HERE/'selected.pickle').write_bytes(pickle.dumps(dict(request=request,held=held,selected=best),protocol=5))
        save('tail_summary.json',dict(status='complete',selection_status='best_observed_feasible_tail_replay',
            initial=held[1]['objective_veh_h'],selected=item['objective_veh_h'],old_selected=selection['selected_objective'],
            retention=retention,finite_rm=audit,observations=observed,sequence=sequence,writer=writer,
            quantity_check=quantity(selected,item),owner_costs=partition,merge=item['quantities']['predicted_ramp_merge'],
            new_predictions=calls,cache=query.stats(),optimizer_calls=0,native_calls=0,
            physical_clock_verified=False,scope='Canonical post-optimization tail from archived optimization; not a repeated full solve'))
        record['status']='complete'
    except BaseException:
        record.update(status='failed_preserved',error=traceback.format_exc());raise
    finally:
        query.close();record.update(wall_sec=time.perf_counter()-began,new_predictions=calls)
        save('tail_execution.json',record)
    print('TAIL337_DONE',item['objective_veh_h'],'new_predictions',calls,flush=True)

if __name__=='__main__':main()
