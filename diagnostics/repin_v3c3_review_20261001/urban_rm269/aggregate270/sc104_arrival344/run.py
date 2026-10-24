"""One four-prediction2400 experiment, same saved commands and inputs."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime,timezone
import gzip,hashlib,importlib.util,json,os,pickle,sys,time,traceback
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc104_arrival344 import candidate
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc6_balance343 import candidate as head_candidate
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.transfer331.inputs import load
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.rm_response330.scope import COMMANDS

HERE=Path(__file__).resolve().parent;A=HERE.parent;ROOT=HERE.parents[4]
BASE=A/'transfer331/build2400_v2';OUT=HERE/'forecast2400'
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,v):(OUT/n).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')

def main():
    assert not OUT.exists() and not (HERE/'launch.json').exists()
    assert not any((p/'STOP').exists() for p in (ROOT,A.parent,A,HERE))
    assert 'OK' in (HERE/'tests.log').read_text(encoding='utf8')
    proof=read(BASE/'summary.json');source=Path(proof['source'])
    raw,frame,pins=load(source,2400)
    for p in (*HERE.glob('*.py'),HERE/'plan.json',HERE/'tests.log',A/'sc6_balance343/head_resources.json',A/'sc6_balance343/configure_fixture/fixture.pickle',BASE/'canonical.pickle',BASE/'initial.pickle'):
        pins[str(p)]=sha(p)
    network=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    pins[str(network)]=sha(network)
    sys.argv=['verify.py','--at','2400','--out',str(OUT),'--no-prediction','--cold-prices',
              '--tuning',str(A/'flow279/config_10686_free.json'),'--decisions',str(source)]
    loader=importlib.util.spec_from_file_location('arrival344_verifier',A.parents[1]/'urban260/verify.py')
    verifier=importlib.util.module_from_spec(loader);loader.loader.exec_module(verifier)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_pfo,sdmpc_sequence as seq
    from evaluation.controllers import physical_ramp_branches as ramps,signal_actuation_contract as signals,area_leader_objective as constraints
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.area_runtime import model_inventory
    from src.models.state import ControlAction
    from src.controllers import rollout_endpoint as endpoint
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_phase305.candidate import hook,verify_pending
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.corridor339.runtime import source_hooks,enabled
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc107_shared316.candidate import refresh_local
    original=adapter.main;captured={};results={};done=False
    launch=dict(pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),status='running',forecast_budget=4,native=0)
    (HERE/'launch.json').write_text(json.dumps(launch,indent=2)+'\n',encoding='utf8')
    def wrapped():
        bound,forecast=ramps.configure_operating_bounds,adapter.demand_from_state
        def capture_bound(state,cfg,reference):
            captured.update(state=state,cfg=cfg);return bound(state,cfg,reference)
        def capture_forecast(*a,**kw):
            value=forecast(*a,**kw);captured['forecast']=value;return value
        ramps.configure_operating_bounds=capture_bound;adapter.demand_from_state=capture_forecast
        def evaluate(reference,*unused):
            nonlocal done
            cfg,state=captured['cfg'],captured['state']
            bc,bs,bf=pickle.loads((BASE/'canonical.pickle').read_bytes())
            checks=dict(cfg=equal(cfg,bc),state=equal(state,bs),forecast=equal(captured['forecast'],bf))
            save('bootstrap_parity.json',checks);assert all(checks.values()),checks
            saved,state,forecast=pickle.loads((BASE/'initial.pickle').read_bytes())
            assert equal(forecast,captured['forecast'])
            for k,v in vars(saved.network).items():setattr(cfg.network,k,deepcopy(v))
            assert equal(cfg,saved)
            follower=adapter._PHASE_VECTOR_FOLLOWER['ref'];refresh_local(follower,cfg)
            plan=adapter.load_signal_group_actuation_plan();arms={}
            for arm in ('hold','city','joint'):
                blocks=[];prev=seq.first_action(reference)
                for at in (2400,2550,2700):
                    path=COMMANDS[arm]/f'action_{at:06}.json';pins[str(path)]=sha(path)
                    b=seq.first_action(adapter.control_from_json(path,cfg,ControlAction))
                    signals.validate_writer(b,cfg,plan,'experiment')
                    ramps.candidate_from_greens(b,prev,cfg,{r:b.diagnostics['rw_meter_green_'+r] for r in b.ramp_metering})
                    blocks.append(b);prev=b
                arms[arm]=seq.pack(blocks)
            for module in tuple(sys.modules.values()):
                path=getattr(module,'__file__',None)
                if path and Path(path).suffix=='.py' and Path(path).is_relative_to(ROOT):pins[str(Path(path))]=sha(path)
            head_receipt=head_candidate.install(cfg,raw,plan,source,2400)
            save('head_installation.json',head_receipt);pins.update(head_receipt['source_pins'])
            for name in ('disabled_hold','hold','city','joint'):
                if name=='hold':
                    frozen_stock=deepcopy(get_ledger(state).stocks)
                    receipt=candidate.install(cfg,network.read_bytes(),frame)
                    assert frozen_stock==get_ledger(state).stocks
                    save('installation.json',receipt)
                action=arms['hold' if name=='disabled_hold' else name];before=pickle.dumps(state,protocol=5)
                tick=time.perf_counter()
                with enabled(cfg,hooks),seq.prediction_scope(action,cfg,2400,3) as visits:
                    point=endpoint.evaluate_price_point(state,action,deepcopy(forecast[:3]),(),
                        endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
                wall=time.perf_counter()-tick
                assert not point.aborted and len(point.states)==3 and visits==[0,1,2]
                assert before==pickle.dumps(state,protocol=5)
                r=point.control_area_response
                assert r['model_constraint_coverage']['complete'] and r['conditional_model_feasibility_witness']
                exceed=max(x['exceedance_veh'] for x in r['resource_allocations']);assert exceed<1e-7
                for s in (state,*point.states):get_ledger(s).assert_stocks(model_inventory(s,cfg));verify_pending(s)
                q=constraints.shared_urban_quantities(follower,r,start_sec=2400,horizon_steps=3)
                feasible=constraints.shared_quantity_constraints(follower,action,q,start_sec=2400,horizon_steps=3,
                    np_mode='cap',target_np_veh=action.N_P_star,np_tolerance_veh=1e-7,
                    nuf_mode='cap',target_nuf_veh_h=action.N_UF_star,nuf_tolerance_veh_h=1e-7)
                assert feasible['feasible']
                inside={};outside={}
                for row in r['residence']:
                    for k,n in row['inside_veh'].items():inside[k]=inside.get(k,0)+n*row['dt_h']
                    for k,n in row['model_stock_veh'].items():outside[k]=outside.get(k,0)+(n-row['inside_veh'].get(k,0))*row['dt_h']
                assert abs(sum(inside.values())-point.ttt)<1e-7
                result=dict(omega_ttt_veh_h=point.ttt,costs_by_stock=inside,outside_costs_by_stock=outside,
                    shared_constraints=feasible,predicted_merge=q['predicted_ramp_merge'],resource_max_exceedance=exceed,
                    conservation_states=4,writer_three_blocks=True,wall_sec=wall)
                if name=='disabled_hold':
                    old=read(A/'sc6_balance343/forecast2400/hold.json')
                    assert abs(point.ttt-old['omega_ttt_veh_h'])<1e-8
                    assert equal(inside,old['costs_by_stock'])
                    result['disabled_cost_parity']=True
                save(name+'.json',result)
                (OUT/(name+'.response.json.gz')).write_bytes(gzip.compress(json.dumps(r,allow_nan=False).encode()))
                results[name]=result
                print('ARRIVAL344',name,point.ttt,'wall',wall,flush=True)
            assert all(sha(p)==h for p,h in pins.items())
            save('summary.json',dict(status='complete',results=results,source_pins=pins,forecasts=4,
                start_sec=2400,end_sec=2850,future_observation_inputs=False,native=0,optimizer=0,fits=0,
                production_adopted=False,goal_complete=False))
            done=True;raise verifier.Done()
        sdmpc_pfo.solve=evaluate
        return original()
    adapter.main=wrapped
    try:
        with source_hooks() as hooks,hook('source_path_current_physical_speed'):
            verifier.main()
        assert done;launch['status']='complete'
    except BaseException:
        launch.update(status='failed_preserved',error=traceback.format_exc());raise
    finally:
        launch.update(forecasts=len(results),finished_utc=datetime.now(timezone.utc).isoformat())
        (HERE/'launch.json').write_text(json.dumps(launch,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
