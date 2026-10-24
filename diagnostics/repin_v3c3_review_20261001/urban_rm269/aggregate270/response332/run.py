"""Three fixed331 model forecasts; no new calibration, optimizer or VISSIM."""
from pathlib import Path
from contextlib import ExitStack
from datetime import datetime,timezone
import copy,gzip,hashlib,importlib.util,json,os,pickle,sys,time
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.response332.commands import pair
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal

HERE=Path(__file__).resolve().parent;A=HERE.parent;H=A.parent;ROOT=HERE.parents[4]
BASE=A/'transfer331/build3300_v2'
OUT=Path('E:/VISSIM_analysis/20261010_response332/forecast3300')
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
save=lambda n,v:(OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')

def main():
    assert not OUT.exists() and not (HERE/'launch.json').exists(),'Preserve attempted output'
    assert not any((p/'STOP').exists() for p in (ROOT,H,A,HERE))
    proof=read(BASE/'summary.json');assert proof['status']=='complete'
    pins=dict(proof['source_pins'])
    assert all(sha(p)==h for p,h in pins.items())
    for p in (*HERE.glob('*.py'),HERE/'plan.json',HERE/'tests.log',BASE/'canonical.pickle',BASE/'initial.pickle',BASE/'summary.json'):
        pins[str(p)]=sha(p)
    assert 'Ran 3 tests' in (HERE/'tests.log').read_text(encoding='utf8')
    source=Path(proof['source']);tuning=A/'flow279/config_10686_free.json'
    sys.argv=['verify.py','--at','3300','--out',str(OUT),'--no-prediction','--cold-prices',
              '--tuning',str(tuning),'--decisions',str(source)]
    spec=importlib.util.spec_from_file_location('response332_verifier',H.parent/'urban260/verify.py')
    verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_pfo,sdmpc_sequence as seq
    from evaluation.controllers import physical_ramp_branches as ramps,signal_actuation_contract as signals,area_leader_objective as constraints
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.area_runtime import model_inventory
    from src.controllers import rollout_endpoint as endpoint
    from src.models.state import ControlAction
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_phase305.candidate import hook,verify_pending
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.branch_service315.candidate import enabled as branch
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_transport317.candidate import enabled as transport
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc10_north325 import candidate as north
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.native_routes329 import candidate as routes
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc108_geometry311 import candidate as prehead
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.gate296.candidate import installed,geometry
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc107_shared316.candidate import refresh_local
    original=adapter.main;captured={};done=False
    OUT.parent.mkdir(parents=True,exist_ok=True)
    (HERE/'launch.json').write_text(json.dumps(dict(pid=os.getpid(),started_at=datetime.now(timezone.utc).isoformat(),
        output=str(OUT),forecast_budget=3,native=0),indent=2)+'\n',encoding='utf8')
    def wrapped():
        bound,forecast=ramps.configure_operating_bounds,adapter.demand_from_state
        def capture_bound(state,cfg,reference):
            captured.update(state=state,cfg=cfg)
            return bound(state,cfg,reference)
        def capture_forecast(*a,**kw):
            value=forecast(*a,**kw);captured['forecast']=value;return value
        ramps.configure_operating_bounds=capture_bound;adapter.demand_from_state=capture_forecast
        def evaluate(reference,coord,policy,options,*unused):
            nonlocal done
            cfg,state=captured['cfg'],captured['state']
            baseline_cfg,baseline_state,baseline_forecast=pickle.loads((BASE/'canonical.pickle').read_bytes())
            exact=dict(state=equal(state,baseline_state),cfg=equal(cfg,baseline_cfg),forecast=equal(captured['forecast'],baseline_forecast))
            save('bootstrap_parity.json',exact);assert all(exact.values()),exact
            frozen_cfg,frozen_state,frozen_forecast=pickle.loads((BASE/'initial.pickle').read_bytes())
            assert equal(frozen_forecast,captured['forecast'])
            assert all(equal(v,getattr(frozen_cfg,k)) for k,v in vars(cfg).items() if k!='network')
            keys=set(vars(cfg.network))|set(vars(frozen_cfg.network))
            changed=[k for k in keys if not equal(getattr(cfg.network,k,None),getattr(frozen_cfg.network,k,None))]
            assert set(vars(cfg.network))<=set(vars(frozen_cfg.network))
            for k in changed:setattr(cfg.network,k,copy.deepcopy(getattr(frozen_cfg.network,k)))
            assert equal(cfg,frozen_cfg)
            state=frozen_state
            binding=refresh_local(adapter._PHASE_VECTOR_FOLLOWER['ref'],cfg)
            save('model_restore.json',dict(network_fields=sorted(changed),state_source=str(BASE/'initial.pickle'),
                local_binding=binding,exact_cfg_state_forecast=True,new_fit=False))
            plan=adapter.load_signal_group_actuation_plan()
            cap_path=A/'decision285/full3300_current/unused.json';pins[str(cap_path)]=sha(cap_path)
            cap=adapter.control_from_json(cap_path,cfg,ControlAction)
            arms=pair(reference,cfg,cap);arms['recorded']=[]
            for at in (3300,3450,3600):
                path=source/f'action_{at:06}.json';pins[str(path)]=sha(path)
                assert path.with_suffix('.json.applied').exists()
                arms['recorded'].append(seq.first_action(adapter.control_from_json(path,cfg,ControlAction)))
            audit={}
            for arm,blocks in arms.items():
                previous=seq.first_action(reference);audit[arm]=[]
                for j,b in enumerate(blocks):
                    signals.validate_writer(b,cfg,plan,'experiment')
                    realized=ramps.candidate_from_greens(b,previous,cfg,{r:b.diagnostics['rw_meter_green_'+r] for r in b.ramp_metering})
                    assert ramps.physical_commands(realized,cfg)==ramps.physical_commands(b,cfg)
                    previous=b
                    audit[arm].append(dict(sec=3300+150*j,commands=ramps.physical_commands(b,cfg),
                        NP=b.N_P_star,NUF=b.N_UF_star,green_times=b.green_times,offsets=b.offsets,vsl=b.vsl))
            save('commands.json',audit)
            initial=pickle.dumps(state,protocol=5);stocks0=copy.deepcopy(get_ledger(state).stocks)
            geom=geometry(ROOT,cfg);results={};response_receipts={}
            for arm,blocks in arms.items():
                action=seq.pack(blocks);started=time.perf_counter()
                with installed(cfg,'aggregate_sc10_native_calendar',geom) as gate_receipts,prehead.clock(cfg) as clock_receipts:
                    with seq.prediction_scope(action,cfg,3300,3) as visits:
                        point=endpoint.evaluate_price_point(state,action,copy.deepcopy(frozen_forecast[:3]),(),
                            endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
                wall=time.perf_counter()-started
                assert not point.aborted and len(point.states)==3 and visits==[0,1,2]
                assert pickle.dumps(state,protocol=5)==initial
                response=point.control_area_response
                assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
                exceed=max((x['exceedance_veh'] for x in response['resource_allocations']),default=0.)
                assert exceed<1e-7
                stocks=[]
                for s in (state,*point.states):
                    get_ledger(s).assert_stocks(model_inventory(s,cfg));verify_pending(s)
                    stocks.append(dict(time_sec=s.time_sec,stocks=copy.deepcopy(get_ledger(s).stocks)))
                costs={};outside={}
                for row in response['residence']:
                    for k,n in row['inside_veh'].items():costs[k]=costs.get(k,0.)+n*row['dt_h']
                    for k,n in row['model_stock_veh'].items():outside[k]=outside.get(k,0.)+(n-row['inside_veh'].get(k,0.))*row['dt_h']
                assert abs(sum(costs.values())-point.ttt)<1e-7
                follower=adapter._PHASE_VECTOR_FOLLOWER['ref']
                quantities=constraints.shared_urban_quantities(follower,response,start_sec=3300,horizon_steps=3)
                feasible=constraints.shared_quantity_constraints(follower,action,quantities,start_sec=3300,horizon_steps=3,
                    np_mode='cap',target_np_veh=action.N_P_star,np_tolerance_veh=1e-7,
                    nuf_mode='cap',target_nuf_veh_h=action.N_UF_star,nuf_tolerance_veh_h=1e-7)
                gates={}
                for attr in ('_sc10_gate296',north.ATTR):
                    local=getattr(point.states[-1],attr)
                    remaining=sum(local['pending'].values())+sum(local['ready'].values())
                    assert abs(local['received']-local['discharged']-remaining)<1e-7
                    assert all(not(x['green_sec']==0 and x['discharged']>1e-8) for x in local['history'])
                    gates[attr]=dict(received=local['received'],discharged=local['discharged'],remaining=remaining)
                result=dict(omega_ttt_veh_h=point.ttt,costs_by_stock=costs,outside_costs_by_stock=outside,
                    predicted_merge=point.control_area['predicted_ramp_merge'],shared_constraints=feasible,
                    resource_max_exceedance=exceed,gates=gates,conservation_states=4,writer_three_blocks=True,wall_sec=wall)
                save(arm+'.json',result);save(arm+'.stocks.json',stocks)
                (OUT/(arm+'.response.json.gz')).write_bytes(gzip.compress(json.dumps(response,allow_nan=False).encode()))
                response_receipts[arm]=dict(gate=gate_receipts,prehead_clock=clock_receipts)
                results[arm]=result
                print('RESPONSE332',arm,point.ttt,'wall',wall,'shared_feasible',feasible['feasible'],flush=True)
            assert all(sha(p)==h for p,h in pins.items())
            save('summary.json',dict(status='complete',start_sec=3300,end_sec=3750,forecasts=3,results=results,
                initial_stocks=stocks0,source_pins=pins,shared_caps_from_preexisting_choice=True,new_fits=0,native=0,
                ad=0,optimizer=0,production_adopted=False,goal_complete=False,future_observation_inputs=False,
                scope='Two hypothetical isolated10681 controls; recorded future commands condition the third response, not traffic inputs'))
            save('forecast_receipts.json',response_receipts)
            done=True;raise verifier.Done()
        sdmpc_pfo.solve=evaluate
        return original()
    adapter.main=wrapped
    try:
        with branch() as br,transport() as tr,north.enabled() as ng,routes.enabled() as rt:
            with hook('source_path_current_physical_speed') as side:verifier.main()
        assert done
    except BaseException as exc:
        if OUT.exists():save('failure.json',dict(type=type(exc).__name__,error=str(exc)))
        raise
    save('context_receipts.json',dict(branch=br,transport=tr,north=ng,routes=rt,side=side))
    print('DONE332:3forecasts; no optimization/native/fitting.',flush=True)

if __name__=='__main__':main()
