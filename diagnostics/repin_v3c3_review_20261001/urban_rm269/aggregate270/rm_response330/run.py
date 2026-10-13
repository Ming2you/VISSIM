"""Exactly one new joint450 prediction; reuse329 city response.

Reuse the identical canonical bootstrap and installed diagnostic model. Swap
only the one packed command before prediction_scope, then intercept the sole
endpoint to record/validate its response and stop the old two-arm harness.
"""
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime,timezone
import copy,gzip,hashlib,importlib.util,json,os,pickle,time
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.rm_response330.scope import preflight,read,sha,BASE,COMMANDS
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal

HERE=Path(__file__).resolve().parent;A=HERE.parent
OUT=Path('E:/VISSIM_analysis/20261010_rm_response330/forecast2400_v2')
spec=importlib.util.spec_from_file_location('routes329_base_for330',A/'native_routes329/run.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
module=base.module;module.CASE=HERE;module.OUT=OUT
save=lambda n,v:(OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
class Completed(Exception):pass

def main():
    assert not OUT.exists() and not (HERE/'launch_v2.json').exists(),'Preserve any prior attempt'
    proof=preflight()
    tests=(HERE/'tests.log').read_text(encoding='utf8');assert 'Ran 3 tests' in tests and 'OK' in tests
    OUT.parent.mkdir(parents=True,exist_ok=True)
    (HERE/'launch_v2.json').write_text(json.dumps(dict(pid=os.getpid(),started_at=datetime.now(timezone.utc).isoformat(),
        output=str(OUT),new_forecasts=1,new_native=0),indent=2)+'\n',encoding='utf8')
    from evaluation.controllers import sdmpc_sequence as seq,vissim_stackelberg_adapter as adapter
    from evaluation.controllers import signal_actuation_contract as signals,physical_ramp_branches as ramps,area_leader_objective as constraints
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.area_runtime import model_inventory
    from src.models.state import ControlAction
    from src.controllers import rollout_endpoint as endpoint
    old_scope,initial_endpoint=seq.prediction_scope,endpoint.evaluate_price_point
    old_install=module.install_geometry;endpoint_holder={}
    ctx={};pins=dict(proof['source_pins'])
    for p in (*HERE.glob('*.py'),HERE/'plan.json',HERE/'tests.log'):pins[str(p)]=sha(p)

    @contextmanager
    def joint_scope(action,cfg,start,horizon):
        assert not ctx,'Only one prediction allowed'
        assert start==2400 and horizon==3 and cfg.simulation.T_f_sec==5 and cfg.simulation.T_u_sec==10
        held=seq.first_action(action)
        expected=seq.first_action(adapter.control_from_json(COMMANDS['hold']/'action_002400.json',cfg,ControlAction))
        assert ramps.physical_commands(held,cfg)==ramps.physical_commands(expected,cfg)
        plan=adapter.load_signal_group_actuation_plan();blocks=[];before=held
        for at in (2400,2550,2700):
            path=COMMANDS['joint']/f'action_{at:06}.json'
            joint=seq.first_action(adapter.control_from_json(path,cfg,ControlAction))
            city=seq.first_action(adapter.control_from_json(COMMANDS['city']/path.name,cfg,ControlAction))
            for field in ('green_times','offsets','vsl','inflow_outflow_allocation','N_P_star','N_UF_star'):
                assert equal(getattr(joint,field),getattr(city,field)),field
            signals.validate_writer(joint,cfg,plan,'experiment')
            ramps.candidate_from_greens(joint,before,cfg,
                {r:joint.diagnostics['rw_meter_green_'+r] for r in joint.ramp_metering})
            before=joint;blocks.append(joint)
        packed=seq.pack(blocks);ctx.update(cfg=cfg,action=packed,calls=0)
        with old_scope(packed,cfg,start,horizon) as visits:
            ctx['visits']=visits
            yield visits

    def evaluate(state,action,forecast,schedule,objective_spec,**kwargs):
        assert ctx['calls']==0 and not schedule and objective_spec.cfg is ctx['cfg']
        assert objective_spec.depth_override==3 and objective_spec.score_mode=='raw'
        assert kwargs.get('capture_response') is True and state.time_sec==2400
        cfg=ctx['cfg'];ctx['calls']+=1
        # Exact reports of deterministic initial transformations are compared
        # before forecasting, not merely asserted from an experiment name.
        reports=('bounds.json','candidate_application.json','current_routes.json','future_route_application.json',
            'geometry.json','initial_calendar.json','initial_projection.json','north_gate_application.json',
            'prehead_geometry.json','sc108_side_application.json','sc109_application.json',
            'sc12_candidate_application.json','sc16_application.json','service_metadata.json',
            'shared_head_application.json','source_geometry.json')
        for n in reports:assert read(OUT/n)==read(BASE/n),'Initial configuration/projection changed: '+n
        oldcfg,oldstate,oldforecast=pickle.loads((A/'citysplit287/forecast2400/initial.pickle').read_bytes())
        assert equal(forecast,oldforecast[:3]),'Exogenous forecast changed'
        (OUT/'initial.pickle').write_bytes(pickle.dumps((cfg,state,forecast),protocol=5))
        initial=pickle.dumps(state,protocol=5);initial_stocks=copy.deepcopy(get_ledger(state).stocks)
        start=time.perf_counter()
        point=endpoint_holder['canonical'](state,ctx['action'],copy.deepcopy(forecast),(),objective_spec,**kwargs)
        wall=time.perf_counter()-start
        assert not point.aborted and len(point.states)==3 and ctx['visits']==[0,1,2]
        assert pickle.dumps(state,protocol=5)==initial
        response=point.control_area_response
        assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
        exceed=max((x['exceedance_veh'] for x in response['resource_allocations']),default=0.)
        assert exceed<1e-7
        stocks=[]
        for s in (state,*point.states):
            get_ledger(s).assert_stocks(model_inventory(s,cfg));module.verify_pending(s)
            stocks.append(dict(time_sec=s.time_sec,stocks=get_ledger(s).stocks))
        save('joint.stocks.json',stocks)
        costs={};outside={}
        for row in response['residence']:
            for k,n in row['inside_veh'].items():costs[k]=costs.get(k,0.)+n*row['dt_h']
            for k,total in row['model_stock_veh'].items():
                n=total-row['inside_veh'].get(k,0.)
                assert n>=-1e-7,'Inside stock exceeds its model total'
                outside[k]=outside.get(k,0.)+n*row['dt_h']
        assert abs(sum(costs.values())-point.ttt)<1e-7
        follower=adapter._PHASE_VECTOR_FOLLOWER['ref']
        quantities=constraints.shared_urban_quantities(follower,response,start_sec=2400,horizon_steps=3)
        feasible=constraints.shared_quantity_constraints(follower,ctx['action'],quantities,start_sec=2400,horizon_steps=3,
            np_mode='cap',target_np_veh=ctx['action'].N_P_star,np_tolerance_veh=1e-7,
            nuf_mode='cap',target_nuf_veh_h=ctx['action'].N_UF_star,nuf_tolerance_veh_h=1e-7)
        assert feasible['feasible']
        gates={}
        for attr in ('_sc10_gate296',base.c.gate.ATTR):
            gate=getattr(point.states[-1],attr)
            remaining=sum(gate['pending'].values())+sum(gate.get('ready',{}).values())
            assert abs(gate['received']-gate['discharged']-remaining)<1e-7
            assert all(not(r['green_sec']==0 and r['discharged']>1e-8) for r in gate['history'])
            gates[attr]=dict(received=gate['received'],discharged=gate['discharged'],remaining=remaining)
        (OUT/'joint.response.json.gz').write_bytes(gzip.compress(json.dumps(response,allow_nan=False).encode('utf8')))
        result=dict(omega_ttt_veh_h=point.ttt,costs_by_stock=costs,outside_costs_by_stock=outside,
            shared_constraints=feasible,predicted_merge=point.control_area['predicted_ramp_merge'],
            resource_max_exceedance=exceed,writer_three_blocks=True,conservation_states=4,wall_sec=wall)
        save('joint.json',result);save('scope.json',proof)
        assert all(sha(p)==h for p,h in pins.items())
        save('summary.json',dict(status='complete',start_sec=2400,end_sec=2850,new_forecasts=1,reused_city=str(BASE/'city.json'),
            inherited_model='329',initial_application_reports_exact=reports,
            initial_stocks=initial_stocks,results={'joint':result},gate_conservation=gates,
            native_scope=proof['scope'],source_pins=pins,production_adopted=False,goal_complete=False,
            budget=dict(new_forecasts450=1,new_native=0,ad=0,optimizer=0,fits=0,push=0),
            future_observation_inputs=False,initial_state_mutated=False))
        print('RM_RESPONSE330_JOINT',point.ttt,'wall',wall,flush=True)
        raise Completed()

    def install_then_capture(cfg,state):
        result=old_install(cfg,state)
        # area_runtime installs the response-capturing endpoint during bootstrap.
        # Instrument it AFTER installation, never its unwrapped inner function.
        canonical=endpoint.evaluate_price_point
        assert getattr(canonical,'_control_area_objective',False)
        assert not endpoint_holder
        endpoint_holder['canonical']=canonical
        endpoint.evaluate_price_point=evaluate
        return result
    seq.prediction_scope=joint_scope;module.install_geometry=install_then_capture
    done=False
    try:
        gb=base.base
        with gb.prior.prior.base.prior.branch() as branch,gb.prior.prior.base.prior.enabled() as transport,gb.c.enabled() as gate,base.c.enabled() as routes:
            try:module.main()
            except Completed:done=True
    finally:
        seq.prediction_scope=old_scope;module.install_geometry=old_install
        endpoint.evaluate_price_point=endpoint_holder.get('canonical',initial_endpoint)
    assert done and ctx['calls']==1
    save('receipts.json',dict(branch=branch,transport=transport,gate=gate,routes=routes))
    print('DONE330:one forecast,source/command scope verified;oldcity reused.',flush=True)

if __name__=='__main__':main()
