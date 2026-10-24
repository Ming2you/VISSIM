"""One urban substep and one local service-only substep; no MPC or VISSIM."""
from __future__ import annotations
from collections import defaultdict
import copy
import hashlib
import inspect
import json
from pathlib import Path
import pickle
import sys

from diagnostics.probe_model_area_integration import ROOT, adapter, build_projected
from src.models import urban_queue_model as uqm
from src.controllers import local_signal_plant as local
from src.controllers.wu_faithful_follower import WuFaithfulFollower
from evaluation.controllers import urban_flow_accounting as urban
from evaluation.controllers.control_area_objective import model_stock_values

TARGETS=('SC1004_offW_to_E_SC1005','SC1004_offE_to_E_SC1005','SC1004_W_to_E_SC1005')
OUT=ROOT/'diagnostics/local_shared_service_contract_review.json'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def hashed(value):return hashlib.sha256(pickle.dumps(value,protocol=5)).hexdigest()


def main():
    run=ROOT/'evaluation/runs/codex_area_sources_beta0_s13_20260910'
    d=run/('decisions_'+run.name)
    paths=[ROOT/'diagnostics/area_candidate_configs/n7_area_beta0.json',d/'state_000900.json',d/'action_000750.json',d/'action_000900.json']
    manifest=json.loads((run/'area_candidate_source_manifest.json').read_text())
    pin={ROOT/k:v for k,v in manifest['source_sha256'].items()}
    pin.update({p:sha(p) for p in paths})
    assert all(sha(p)==v for p,v in pin.items())
    cfg,state,detectors,tuning,raw,mapping,meta=build_projected(*paths[:3],fixture_inputs=False)
    _,Demand,Control,_,_,_=adapter.repo_imports(ROOT/'vendor/NumSim-mine')
    action=adapter.control_from_json(paths[3],cfg,Control)
    calibration=adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
    calibration=adapter.deep_update(dict(calibration),tuning.get('calibration_override',{}))
    demand=adapter.demand_from_state(raw,cfg,Demand,1,calibration,detectors)[0]
    before=hashed((cfg,state,action,demand,raw,detectors))
    specs=uqm.movement_specs(cfg)
    phase_movements={s:{p:[] for p in ('p1','p2','p3','p4')} for s in cfg.network.signals}
    for m,sp in specs.items():
        if sp['signal'] in phase_movements:phase_movements[sp['signal']][sp['phase'].rsplit('_',1)[-1]].append(m)
    models={s:local.build_local_model(cfg,s,specs,phase_movements) for s in cfg.network.signals}
    model=models['SC1004'];step=uqm._urban_step_index(state,cfg);dt=cfg.simulation.T_u_h
    q0={m:max(0.,state.urban_movement_queue.get(m,0.)) for m in model.movements}
    occ={off:max(0.,cfg.network.urban_link_storage_veh[cfg.network.off_ramp_storage_link[off]]-state.urban_link_storage[cfg.network.off_ramp_storage_link[off]]) for off in model.offramp_movements}
    receiver=specs[TARGETS[0]]['receiving_link']
    s_eff={model.receiving_of[m]:uqm._effective_available_space(state,cfg,model.receiving_of[m]) for m in model.movements if model.receiving_of[m]}
    gf={m:[uqm._phase_green_fraction(action,cfg,specs[m],urban_step_index=step)] for m in model.movements}
    actual_global=state.copy();global_queries=[];global_receipts=[];local_receipts=[];local_final={}
    functions={urban._corridor_intended.__code__:'query',urban._receive_corridor.__code__:'receipt'}
    query_input={}
    def profile(frame,event,arg):
        if frame.f_code not in functions:return
        loc=frame.f_locals;m=loc['movement']
        if m not in TARGETS:return
        if event=='call' and functions[frame.f_code]=='query':
            query_input[id(frame)]=float(loc['ordinary']);return
        if event!='return':return
        if functions[frame.f_code]=='receipt':
            global_receipts.append({'movement':m,'accepted_veh':loc['vehicles']});return
        st=loc['state'];sp=cfg.network.urban_movements[m]
        global_queries.append({'movement':m,'available_veh':loc['available'],'ordinary_intended_veh':query_input.pop(id(frame)),
                               'pooled_intended_veh':arg,'green_fraction':uqm._phase_green_fraction(action,cfg,sp,urban_step_index=step),
                               'receiver_space_before_veh':uqm._effective_available_space(st,cfg,receiver),
                               'pool_used_before_veh':st.route_choice_corridor_state['service_used_veh'].get('10634',0.),
                               'pool_budget_veh':st.route_choice_corridor_state['service_limit_veh'].get('10634'),
                               'dt_h':dt,'step':step})
    previous_profile=sys.getprofile();sys.setprofile(profile)
    try:
        returned=uqm.urban_substep(actual_global,action,demand,cfg,urban_step_index=step,ramp_release_veh_h=action.ramp_metering)
    finally:sys.setprofile(previous_profile)
    stock_values=model_stock_values(actual_global,cfg.network,freeway_vehicle_counts=adapter._freeway_vehicle_count_by_link(actual_global,cfg))
    pending_merge={f'merge_pending:{r}':returned[1][f'ramp_metering_release_actual_{r}_veh'] for r in cfg.network.ramps}
    stock_values.update(pending_merge)  # Explicit urban->FW handoff, before the unexecuted FW substep.
    actual_global._control_area_ledger.assert_stocks(stock_values)
    source,first=inspect.getsourcelines(local.rollout_local_tts_ramp_aware)
    capture_lines={first+i for i,line in enumerate(source) if line.strip()=='released_total += actual'}
    code=local.rollout_local_tts_ramp_aware.__code__
    def trace(frame,event,arg):
        if frame.f_code is not code:return None
        if event=='line' and frame.f_lineno in capture_lines:
            loc=frame.f_locals
            if loc.get('m') in TARGETS:local_receipts.append({'movement':loc['m'],'accepted_veh':loc['actual']})
        if event=='return':
            for key in ('q','occ','s_eff','cost'):
                local_final[key]=copy.deepcopy(frame.f_locals.get(key))
        return trace
    previous_trace=sys.gettrace();sys.settrace(trace)
    try:
        local_cost=local.rollout_local_tts_ramp_aware(model,q0,{},s_eff,{},occ,
            {r:state.ramp_queue.get(r,0.) for r in model.onramp_movements},{},{},0.,
            {p:action.green_times['SC1004_'+p] for p in ('p1','p2','p3','p4')},1,dt,
            arr_by_substep={},gf_by_substep=gf)
    finally:sys.settrace(previous_trace)
    local_receipts.append({'movement':TARGETS[-1],'accepted_veh':q0[TARGETS[-1]]-local_final['q'][TARGETS[-1]]})
    operands=[]
    for m in TARGETS:
        sp=specs[m];off=sp.get('off_ramp');avail=float(sp['beta'])*occ[off] if off else q0[m]
        query=next(r for r in global_queries if r['movement']==m)
        assert abs(query['available_veh']-avail)<1e-9
        assert query['green_fraction']==gf[m][0] and query['dt_h']==dt and query['step']==step
        operands.append({'movement':m,'SC':sp['signal'],'phase':sp['phase'],'kind':sp['kind'],'movement_beta':sp['beta'],
                         'ordinary_queue_veh':q0[m],'offramp_storage_occupied_veh':occ.get(off),
                         'service_available_veh':avail,'capacity_veh_h':model.cap_flow_of[m],
                         'receiver':receiver,'initial_receiver_available_veh':s_eff[receiver],
                         'green_fraction':gf[m][0],'dt_h':dt,'global_query_available_matches':True,
                         'global_query_green_dt_matches':True})
    # Different preceding receipts decrement global receiving space; all remain
    # nonbinding for this pool, so they cannot explain this particular difference.
    saturated_total=sum(model.cap_flow_of[m]*dt*gf[m][0] for m in TARGETS)
    assert s_eff[receiver]>=saturated_total and all(r['receiver_space_before_veh']>=saturated_total for r in global_queries)
    repeat_state=state.copy()
    uqm.urban_substep(repeat_state,action,demand,cfg,urban_step_index=step,ramp_release_veh_h=action.ramp_metering)
    assert hashed(repeat_state)==hashed(actual_global)
    assert before==hashed((cfg,state,action,demand,raw,detectors))
    assert all(sha(p)==v for p,v in pin.items())
    result={'schema':'local-shared-service-contract-review/v1','run':run.name,'decision_sec':900,'step':step,'interval':[900,905],
            'scope':'One installed global urban_substep and one canonical local ramp-aware service-only substep. Local arrivals/offramp future inflow/reservoir drain are zero, not a reconstruction of the entire follower horizon. Target three source available amounts, GF and dt equal actual global query values; receiver never binds in either.',
            'source_sha256':{str(p.relative_to(ROOT)):v for p,v in pin.items()},
            'model_attachment':{'signal':'SC1004','movement_count':len(model.movements),'has_ramps':model.has_ramps,
                                'all_target_movements_in_same_local_model':all(m in model.movements for m in TARGETS),
                                'other_local_model_target_counts':{s:len(set(TARGETS)&set(v.movements)) for s,v in models.items() if s!='SC1004'},
                                'offramp_movements':model.offramp_movements,'receiver_is_own_origin':receiver in set(model.origin_of.values())},
            'actual_initial_operands':operands,'global_queries':global_queries,'global_accepted':global_receipts,'local_accepted':local_receipts,
            'global_accepted_total_veh':sum(r['accepted_veh'] for r in global_receipts),
            'local_accepted_total_veh':sum(r['accepted_veh'] for r in local_receipts),
            'global_pool_after_veh':actual_global.route_choice_corridor_state['service_used_veh'].get('10634'),
            'global_urban_ledger_stock_closure_including_pending_merge_receipts':True,'pending_merge_receipts_veh':pending_merge,
            'global_repeat_exact':True,'candidate_input_unchanged':True,'source_bytes_unchanged':True,
            'local_TTT_service_only_veh_h':local_cost,'global_return':returned,
            'scope_limit':'Current per-source order is OR_F_W, OR_F_E, ordinary W. No claim that a new capacity value or simultaneous proportional allocation is justified; preserve current priority when sharing a primitive.'}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('global_accepted','local_accepted','global_accepted_total_veh','local_accepted_total_veh','actual_initial_operands')},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
