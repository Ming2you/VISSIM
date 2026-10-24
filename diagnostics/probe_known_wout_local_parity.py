"""One urban step and direct local cost calls; no endpoint/MPC/VISSIM."""
import copy
import inspect
import json
import pickle
import sys
from pathlib import Path
from diagnostics.probe_model_area_integration import ROOT,adapter
from diagnostics.test_known_wout_routes import actual_case,option
from diagnostics.prepare_known_wout_routes import installed
from diagnostics.known_wout_fixtures import input_path
from src.models.state import ControlAction
from src.models.demand import DemandStep
from evaluation.controllers import link_predictor,urban_flow_accounting as urban


def prepared(sec):
    cfg,state,detectors,tuning,raw,mapping,metadata=actual_case(sec)
    control=adapter.control_from_json(input_path(f'action_{sec:06d}.json'),cfg,ControlAction)
    calibration=adapter.deep_update(dict(adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))),tuning.get('calibration_override',{}))
    demand=adapter.demand_from_state(raw,cfg,DemandStep,1,calibration,detectors)[0]
    # Recorded source-run settings predate the current shared pool. Enable only
    # that existing opt-in in this private cfg to audit the active local caller;
    # keep observed capacities, demand and all controls unchanged.
    from evaluation.controllers import local_signal_service
    local_signal_service.configure(cfg,{'urban':{'shared_local_service_pool':True}})
    controller=adapter.build_priced_wu_link_controller(cfg,tuning)
    follower=controller.nash_solver
    # Same handshake the real phase-price refresh performs before local calls.
    follower.phase_price_local_cost_model=controller.phase_price_local_cost_model
    return cfg,state,control,demand,follower,tuning


def local_transfers(landing,control,ramp_q):
    function=type(landing).advance
    code,first=inspect.getsourcelines(function)
    ramp_line=first+next(i for i,l in enumerate(code) if 'departed += transfer' in l)
    debit_line=first+next(i for i,l in enumerate(code) if 'self.stock[target] -= departed' in l)
    rows=[];totals=[]
    def capture(frame,event,arg):
        if event=='line' and frame.f_locals.get('target')=='SC1004_W_out':
            v=frame.f_locals
            if frame.f_lineno==ramp_line:
                rows.append({'target':v['ramp'],'vehicles':v['transfer'],'room':v['room'],'connector_budget':v['cap']})
            if frame.f_lineno==debit_line:
                totals.append({'arrived':v['arrived'],'reach':v['reach'],'departed':v['departed'],'step':landing.step})
        return capture
    def dispatch(frame,event,arg):
        return capture if frame.f_code is function.__code__ else None
    old=sys.gettrace()
    try:
        sys.settrace(dispatch)
        landing.advance(control,ramp_q,landing.cfg.simulation.T_u_h)
    finally:sys.settrace(old)
    assert len(totals)==1
    return {'ramps':rows,'free':totals[0]['departed']-sum(r['vehicles'] for r in rows),**totals[0]}


def main():
    output=ROOT/'diagnostics/known_wout_local_parity_before.json'
    if output.exists():raise FileExistsError(output)
    results=[]
    for sec in (1200,3300):
        cfg,state,control,demand,follower,tuning=prepared(sec)
        with installed() as route:
            route.configure_known_legsplit(cfg,option(tuning),state,
                adapter.load_optional_json(str(input_path(f'state_{sec:06d}.json'))))
            before=pickle.dumps((state,control,demand))
            step=round(sec/cfg.simulation.T_u_sec)
            coupling=follower._wu._coupling(state,control,demand)
            model=follower._local_freeway_models['FW_E']
            landing=link_predictor.LocalLandingState(follower,model,state)
            replacement=dict(landing.replaced_coupling)
            ramps={r:state.ramp_queue[r] for r in model.owned_ramps}
            local=local_transfers(landing,control,ramps)
            # Capture the real canonical legsplit's final accepted receipts.
            global_state=state.copy(); receipts=[]
            original=route.known_legsplit_commit
            def record(s,cfg_arg,actual,idx):
                receipts.extend({'target':r or 'free','vehicles':n} for k,r,n in actual if k=='SC1004_W_out')
                return original(s,cfg_arg,actual,idx)
            from unittest.mock import patch
            with patch.object(route,'known_legsplit_commit',side_effect=record):
                urban.legsplit_substep_accounted(global_state,control,demand,cfg,
                    urban_step_index=step,ramp_release_veh_h=control.ramp_metering)
            local_model=follower._local_models['SC1004']
            contexts=[];costs=[]
            for candidate in (state.copy(),state.copy()):
                if costs:
                    for row in candidate.known_legsplit_route_state['cohorts']:
                        row['target']='R_F_E'
                ctx=follower._phase_refine_context(candidate,control,demand)
                setup=follower._phase_refine_signal_setup('SC1004',candidate,ctx)
                phases={p:control.green_times['SC1004_'+p] for p in ('p1','p2','p3','p4')}
                costs.append(follower._phase_local_cost_phased('SC1004',phases,setup,ctx))
                contexts.append({'has_known_wout_seed':any('wout' in k.lower() for k in setup),
                    'receiving_space_W_out':setup['s_eff0']['SC1004_W_out'],
                    'ramp_keys':list(setup['ramp_q'])})
            assert before==pickle.dumps((state,control,demand))
            results.append({'start_sec':sec,'step':step,'local_landing_enabled':cfg.network.local_landing_state,
                'private_existing_shared_pool_enabled':True,'recorded_source_shared_pool_flag':tuning.get('urban',{}).get('shared_local_service_pool'),
                'local_landing_transfers':local,'global_legsplit_actual_transfers':receipts,
                'frozen_u_on_vph':{r:coupling['u_on_'+r] for r in ('R_F_E','R_F_W')},
                'local_replaced_coupling_vph':replacement,
                'SC1004_model_movements_receiving_W_out':[m for m in local_model.movements if local_model.receiving_of[m]=='SC1004_W_out'],
                'SC1004_model_movements_origin_W_out':[m for m in local_model.movements if local_model.origin_of[m]=='SC1004_W_out'],
                'SC1004_contexts':contexts,'SC1004_actual_cost_and_all_R_FE_tag_cost':costs,
                'source_objects_unchanged':True,'scope':'Global includes actual urban body; local freezes other boundaries. Compare W_out accepted sub-transfer where initial receiver caps are nonbinding, not whole-plant trajectories.'})
    output.write_text(json.dumps({'schema':'known-wout-local-parity-before/v1','cases':results},indent=2)+'\n',encoding='utf-8')
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
