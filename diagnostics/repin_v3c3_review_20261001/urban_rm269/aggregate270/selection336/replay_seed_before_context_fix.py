"""Replay retention with saved real response and canonical cap-cache proof."""
from pathlib import Path
import copy,hashlib,json,pickle
from evaluation.controllers.sdmpc import retain_feasible_held,token
from evaluation.controllers.sdmpc_tangent_surrogate import Query
from evaluation.controllers.area_leader_objective import shared_quantity_constraints

HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_bytes())
request=pickle.loads((HERE/'workers/0001/request.pickle').read_bytes())
stored=pickle.loads((HERE/'workers/0001/result.pickle').read_bytes())
joint=read(HERE/'full3300/unused.joint.json')['selection']
seed=request['action'];follower,state,_,_=request['owned']
assert token(seed)==joint['pfo_warm_start']['iterations'][0]['action_token']
assert stored['surrogate_prediction']['objective_veh_h']==joint['pfo_warm_start']['initial_omega_objective']
loaded=[]
def saved_runner(incoming):
    assert not loaded,'No new candidate evaluation allowed in saved replay'
    assert token(incoming['action'])==token(seed)
    assert incoming['surrogate_context_sha256']==stored['surrogate_prediction']['frozen_context_token']
    loaded.append(True)
    result=copy.deepcopy(stored);result['wall_sec_including_spawn']=0.
    return result

query=Query(request,lambda *args:None,lambda *args,**kw:None,runner=saved_runner)
initial=query.evaluate([seed],derivatives=True)[0]
assert initial['objective_veh_h']==joint['held_objective']
cap_action=seed.copy()
cap_action.N_P_star=joint['final_constraints']['np']['target']
cap_action.N_UF_star=joint['final_constraints']['nuf']['target']
winner=(cap_action,dict(objective_veh_h=joint['selected_objective']),None)
proofs=[]
def feasible(action,item):
    proof=shared_quantity_constraints(follower,action,item['quantities'],start_sec=3300,horizon_steps=3,
        np_mode='cap',target_np_veh=action.N_P_star,np_tolerance_veh=1e-7,
        nuf_mode='cap',target_nuf_veh_h=action.N_UF_star,nuf_tolerance_veh_h=1e-7)
    proofs.append(proof)
    return (proof['feasible'] and item['conditional_model_feasibility_witness']
        and item['model_constraint_coverage']['complete']
        and item['resource_summary']['max_exceedance_veh']<=1e-7)
best,receipt=retain_feasible_held(seed,initial['objective_veh_h'],winner,cap_action,1e-7,query.evaluate,feasible)
assert receipt['selected'] and len(loaded)==1 and proofs[0]['feasible']
assert query.stats()['cache_hits']>=1
record=dict(status='saved_operating_seed_retained_under_same_caps',receipt=receipt,
    old_selected=joint['selected_objective'],retained=best[1]['objective_veh_h'],
    final_np_cap=cap_action.N_P_star,final_nuf_cap=cap_action.N_UF_star,
    quantity_check=proofs[0],saved_responses_loaded=1,new_predictions=0,new_optimization=0,
    canonical_cap_cache_reused=True,writer_evidence='full3300/writer.json validates this exact PFO initial action',
    reference_token=token(seed),new_native=0,
    limit='Retention-stage replay only. Subsequent finite-RM neighbors must be regenerated for this changed incumbent before claiming a final patched choice.')
(HERE/'retention_replay.json').write_text(json.dumps(record,indent=2,allow_nan=False),encoding='utf8')
query.close()
print(json.dumps({k:record[k] for k in ('status','old_selected','retained','new_predictions','new_optimization','canonical_cap_cache_reused')}),flush=True)
