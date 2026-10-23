"""Two conditional whole-network forecasts of one preregistered refinement."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import copy,datetime,gzip,hashlib,importlib.util,json,sys,time,unittest
from pathlib import Path
from refine_approach15 import Refinement,TransportTests

AUDIT=Path(__file__).resolve().parent;HERE=AUDIT.parent
ROOT=Path('D:/VISSIM_packages/vsl_multizone355_20261015')
CLOCK=AUDIT/'refine15_clock'
OUT=CLOCK/'forecasts'
CONFIG=ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/vsl_schedules_20261015/config.json'
F=Path('E:/VISSIM_runs/20261011_vsl349_off2250_s29/hold/decisions_sdmpc31_g_2250_hold_s29')
OBS=Path('E:/VISSIM_runs/20261008_coupling268_off_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def main():
    assert not OUT.exists() and not (CLOCK/'launch.json').exists() and not (AUDIT/'STOP').exists()
    protocol=read(CLOCK/'protocol.json')
    assert protocol['budget']['forecasts']==4
    save(CLOCK/'launch.json',dict(pid=os.getpid(),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=sys.argv,forecast_budget=4,native=0))
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    os.environ['NUMSIM_REPO_ROOT']=str(ROOT/'vendor/NumSim-mine')
    verify=ROOT/'diagnostics/repin_v3c3_review_20261001/urban260/verify.py'
    sys.argv=[str(verify),'--at','2250','--out',str(OUT),'--tuning',str(CONFIG),'--decisions',str(OBS),'--full-selection']
    spec=importlib.util.spec_from_file_location('refine15_verify',verify)
    verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_pfo,sdmpc_sequence as seq,sdmpc
    from evaluation.controllers import physical_ramp_branches as ramps,signal_actuation_contract as signals
    from evaluation.controllers.control_hold import fixed_vsl_values
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts
    from src.models.state import ControlAction
    from src.controllers import rollout_endpoint as endpoint
    import numpy as np
    sdmpc.load_prices=lambda *a,**kw:(np.zeros(2),{'source':'offline_conditional_replay_cold_prices','committed':False})
    old=read(HERE/'matched_off2250_v3/summary.json');baseline={r['name']:r for r in old['results']}
    assert sha(CONFIG)==old['model_config_sha256']
    paths=[Path(__file__),AUDIT/'refine_approach15.py',CONFIG,verify,HERE/'matched_off2250_v3/summary.json']
    paths.extend(ROOT/'evaluation/controllers'/name for name in ('freeway_fd.py','offramp_routing.py','area_freeway_accounting.py','vissim_stackelberg_adapter.py','lane_freeway_runtime.py'))
    paths.extend(F/f'action_{sec:06d}.json' for sec in (2250,2400,2550))
    pins={str(p):sha(p) for p in paths}
    captured={};oldbounds=ramps.configure_operating_bounds;olddemand=adapter.demand_from_state
    def bounds(state,cfg,reference):
        value=oldbounds(state,cfg,reference);captured.update(state=state,cfg=cfg);return value
    def demand(*a,**kw):
        value=olddemand(*a,**kw);captured['forecast']=value;return value
    ramps.configure_operating_bounds=bounds;adapter.demand_from_state=demand
    # Install before verifier initializes its current physical route inventory.
    # The artifact directory is created by verifier; source text is stored outside.
    refinement=Refinement(CLOCK)
    from evaluation.controllers import multirate_freeway
    original_limit=multirate_freeway.time_limit
    cap=1.25
    multirate_freeway.time_limit=lambda runtime,state:min(cap,original_limit(runtime,state))
    results=[]
    def audit(reference,coord,policy,options,evaluate,derivative,quantities,check_budget,emit):
        nonlocal cap
        state,cfg=captured['state'],captured['cfg']
        assert hasattr(state,'_refine15') and state.time_sec==2250
        assert (cfg.simulation.T_f_sec,cfg.simulation.T_u_sec,cfg.mpc.horizon_steps)==(5,10,3)
        initial=baseline['hold']['snapshots'][0];n=continuity_vehicle_counts(state,cfg)
        assert max(abs(a-b) for road in n for a,b in zip(n[road],initial['n'][road]))<1e-7
        assert max(abs(a-b) for road in state.freeway_speed for a,b in zip(state.freeway_speed[road],initial['speed'][road]))<1e-7
        save(OUT/'initial_refinement.json',state._refine15)
        for name,cap,zones in [('hold125',1.25,{}),('selected125',1.25,{'FW_E__seg10':90,'FW_E__seg13':90}),('hold0625',.625,{}),('selected0625',.625,{'FW_E__seg10':90,'FW_E__seg13':90})]:
            assert len(results)<4
            actions=[]
            for sec in (2250,2400,2550):
                original=seq.first_action(adapter.control_from_json(F/f'action_{sec:06d}.json',cfg,ControlAction));action=copy.deepcopy(original)
                action.vsl=fixed_vsl_values(action.vsl,dict(start_sec=2250,base_kmh=110,zone_kmh=zones),cfg.network.freeway_vsl_zone_heads,sec)
                for key in ('green_times','offsets','ramp_metering','N_P_star','N_UF_star','inflow_outflow_allocation'):assert getattr(action,key)==getattr(original,key)
                signals.validate_writer(action,cfg,adapter.load_signal_group_actuation_plan(),'experiment');actions.append(action)
            action=seq.pack(actions);refinement.trace=[];started=time.perf_counter()
            save(OUT/'progress.json',dict(current=name,completed=[r['name'] for r in results],forecasts_entered=len(results)+1))
            with seq.prediction_scope(action,cfg,2250,3) as visits:
                point=endpoint.evaluate_price_point(state,action,copy.deepcopy(captured['forecast'][:3]),(),endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
            elapsed=time.perf_counter()-started
            assert visits==[0,1,2] and not point.aborted and len(point.states)==3
            assert not refinement.context
            response=point.control_area_response
            assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
            costs={};outside={};snaps=[]
            for r in response['residence']:
                for k,n in r['inside_veh'].items():
                    costs[k]=costs.get(k,0.)+n*r['dt_h'];outside[k]=outside.get(k,0.)+(r['model_stock_veh'][k]-n)*r['dt_h']
            assert abs(sum(costs.values())-point.ttt)<1e-7
            for s in (state,*point.states):
                get_ledger(s).assert_stocks(model_inventory(s,cfg))
                snaps.append(dict(time_sec=s.time_sec,stocks=get_ledger(s).stocks,n=continuity_vehicle_counts(s,cfg),speed=s.freeway_speed,ramp_queue=s.ramp_queue))
            with gzip.open(OUT/f'{name}_response.json.gz','wt',encoding='utf8') as f:json.dump(response,f,allow_nan=False)
            save(OUT/f'{name}_subcells.json',refinement.trace)
            result=dict(name=name,internal_cap_sec=cap,ttt_veh_h=point.ttt,seconds=elapsed,costs=costs,outside_costs=outside,snapshots=snaps,physical_constraints=True,native_validated=False)
            results.append(result);save(OUT/'results.json',results)
            print('REFINE_DONE',name,point.ttt,elapsed,flush=True)
        raise verifier.Done()
    sdmpc_pfo.solve=audit
    try:verifier.main()
    finally:
        refinement.restore()
        multirate_freeway.time_limit=original_limit
    assert len(results)==4
    for p,h in pins.items():assert sha(p)==h,p
    save(OUT/'completion.json',dict(status='complete_pending_assessment',new_forecasts=4,new_native=0,new_optimizer_runs=0,
        parameter_fits=0,production_edits=0,source_pins=pins,max_tag_balance=refinement.max_balance,max_vsl_balance=refinement.max_cohort,
        tests=0,prior_transport_tests_reused=5,future_observations_used=False,initial_stock_speed_parity=True,commands_fixed=True,goal_complete=False))


if __name__=='__main__':
    try:main()
    except BaseException as error:
        import traceback
        save(CLOCK/'failure.json',dict(error=repr(error),traceback=traceback.format_exc(),native=0))
        raise
