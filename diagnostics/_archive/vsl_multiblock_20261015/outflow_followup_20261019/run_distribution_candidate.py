"""One isolated 450s forecast; immutable package and completed baseline reused."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import copy
import datetime
import gzip
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path
from distribution_contract import ROOT, OUT as AUDIT, NETWORK, load_distributions, free_speed_multiplier

HERE=AUDIT.parent
OUT=AUDIT/'distribution_candidate'
CONFIG=ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/vsl_schedules_20261015/config.json'
F=Path('E:/VISSIM_runs/20261011_vsl349_off2250_s29/hold/decisions_sdmpc31_g_2250_hold_s29')
OBS=Path('E:/VISSIM_runs/20261008_coupling268_off_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(path,value): Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def main():
    protocol=read(AUDIT/'distribution_candidate_protocol.json')
    assert protocol['budget']['initial_selected450']==1 and protocol['budget']['native']==0
    assert not OUT.exists() and not (AUDIT/'STOP').exists()
    with (AUDIT/'distribution_candidate_launch.json').open('x',encoding='utf8') as f:
        json.dump(dict(pid=os.getpid(),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       command=sys.argv,forecasts_authorized=1,retry=0,native=0),f,indent=2)
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    os.environ['NUMSIM_REPO_ROOT']=str(ROOT/'vendor/NumSim-mine')
    verify=ROOT/'diagnostics/repin_v3c3_review_20261001/urban260/verify.py'
    sys.argv=[str(verify),'--at','2250','--out',str(OUT),'--tuning',str(CONFIG),'--decisions',str(OBS),'--full-selection']
    spec=importlib.util.spec_from_file_location('distribution_verify',verify)
    verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter, sdmpc_pfo, sdmpc_sequence as seq, runtime_setup, sdmpc, freeway_fd as fd
    from evaluation.controllers import physical_ramp_branches as ramps, signal_actuation_contract as signals
    from evaluation.controllers.control_hold import fixed_vsl_values
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts
    from src.models.state import ControlAction
    from src.controllers import rollout_endpoint as endpoint
    import numpy as np
    sdmpc.load_prices=lambda *a,**kw:(np.zeros(2),{'source':'offline_conditional_replay_cold_prices','committed':False})
    baseline=read(HERE/'matched_off2250_v3/summary.json')
    base={r['name']:r for r in baseline['results']}
    assert base['hold']['snapshots'][0]==base['selected']['snapshots'][0]
    contract=read(AUDIT/'distribution_contract.json')
    for p,h in contract['source_pins'].items(): assert sha(p)==h,p
    paths=[Path(__file__),AUDIT/'distribution_candidate_protocol.json',CONFIG,verify,NETWORK,
           HERE/'matched_off2250_v3/summary.json',Path(fd.__file__),Path(adapter.__file__),
           ROOT/'evaluation/controllers/area_freeway_accounting.py',ROOT/'evaluation/controllers/lane_freeway_runtime.py']
    paths.extend(F/f'action_{sec:06d}.json' for sec in (2250,2400,2550))
    pins={str(p):sha(p) for p in paths}
    captured={};configure=runtime_setup.configure_runtime;bounds=ramps.configure_operating_bounds;demand=adapter.demand_from_state
    def capture_runtime(*a,**kw):
        value=configure(*a,**kw);captured.update(mapping=a[3],calibration=a[7],tuning=a[2]);return value
    def capture_bounds(state,cfg,reference):
        value=bounds(state,cfg,reference);captured.update(state=state,cfg=cfg);return value
    def capture_demand(*a,**kw):
        value=demand(*a,**kw);captured['forecast']=value;return value
    runtime_setup.configure_runtime=capture_runtime;ramps.configure_operating_bounds=capture_bounds;adapter.demand_from_state=capture_demand
    completed=[];distributions=load_distributions()

    def audit(reference,coord,policy,options,evaluate,derivative,quantities,check_budget,emit):
        state,cfg=captured['state'],captured['cfg']
        assert state.time_sec==2250 and (cfg.simulation.T_f_sec,cfg.simulation.T_u_sec,cfg.mpc.horizon_steps)==(5,10,3)
        initial=base['hold']['snapshots'][0]
        n=continuity_vehicle_counts(state,cfg)
        assert max(abs(a-b) for road in n for a,b in zip(n[road],initial['n'][road]))<1e-7
        assert max(abs(a-b) for road in state.freeway_speed for a,b in zip(state.freeway_speed[road],initial['speed'][road]))<1e-7
        actions=[]
        for sec in (2250,2400,2550):
            original=seq.first_action(adapter.control_from_json(F/f'action_{sec:06d}.json',cfg,ControlAction))
            action=copy.deepcopy(original)
            action.vsl=fixed_vsl_values(action.vsl,dict(start_sec=2250,base_kmh=110,zone_kmh={'FW_E__seg10':90,'FW_E__seg13':90}),cfg.network.freeway_vsl_zone_heads,sec)
            for field in ('green_times','offsets','ramp_metering','N_P_star','N_UF_star','inflow_outflow_allocation'):
                assert getattr(action,field)==getattr(original,field)
            signals.validate_writer(action,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
            actions.append(action)
        action=seq.pack(actions)
        original_parameters=fd.literature_vsl_parameters
        calls={90:0,110:0}
        def candidate(spec,v_free,critical,shape,command,maximum):
            result=original_parameters(spec,v_free,critical,shape,command,maximum)
            assert spec['law']=='carlson'
            multiplier=free_speed_multiplier(distributions,command,maximum)
            calls[int(command)]+=1
            return result[0]*multiplier,result[1],result[2]
        # Check the no-intervention branch and unchanged density/shape directly.
        for command in (90.,110.):
            before=original_parameters({'law':'carlson','A':.5,'E':2,'alpha':0},120.,30.,2.,command,110.)
            after=candidate({'law':'carlson','A':.5,'E':2,'alpha':0},120.,30.,2.,command,110.)
            assert before[1:]==after[1:]
            if command==110: assert before==after
        calls={90:0,110:0}
        started=time.perf_counter();fd.literature_vsl_parameters=candidate
        try:
            with seq.prediction_scope(action,cfg,2250,3) as visits:
                point=endpoint.evaluate_price_point(state,action,copy.deepcopy(captured['forecast'][:3]),(),endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
        finally:
            fd.literature_vsl_parameters=original_parameters
        seconds=time.perf_counter()-started
        assert visits==[0,1,2] and not point.aborted and len(point.states)==3 and calls[90]>0
        response=point.control_area_response
        assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
        costs={};outside={};snapshots=[]
        for r in response['residence']:
            for k,n in r['inside_veh'].items():
                costs[k]=costs.get(k,0.)+n*r['dt_h']
                outside[k]=outside.get(k,0.)+(r['model_stock_veh'][k]-n)*r['dt_h']
        assert abs(sum(costs.values())-point.ttt)<1e-7
        for s in (state,*point.states):
            get_ledger(s).assert_stocks(model_inventory(s,cfg))
            snapshots.append(dict(time_sec=s.time_sec,stocks=get_ledger(s).stocks,n=continuity_vehicle_counts(s,cfg),speed=s.freeway_speed,ramp_queue=s.ramp_queue))
        with gzip.open(OUT/'selected_response.json.gz','wt',encoding='utf8') as f: json.dump(response,f,allow_nan=False)
        result=dict(name='selected',ttt_veh_h=point.ttt,delta_veh_h=point.ttt-base['hold']['ttt_veh_h'],seconds=seconds,
                    costs=costs,outside_costs=outside,snapshots=snapshots,physical_constraints=True,native_validated=False,
                    helper_calls=calls,free_speed_multiplier=contract['candidate_free_speed_multiplier'])
        save(OUT/'candidate_result.json',result);completed.append(result)
        print('FORECAST_DONE',point.ttt,result['delta_veh_h'],seconds,flush=True)
        raise verifier.Done()

    sdmpc_pfo.solve=audit
    verifier.main()
    assert len(completed)==1
    for p,h in pins.items(): assert sha(p)==h,p
    save(OUT/'completion.json',dict(status='complete_pending_assessment',new_forecasts=1,new_native=0,
        new_optimizer_runs=0,parameter_fits=0,production_edits=0,source_pins=pins,
        future_observations_used=False,initial_stock_speed_parity=True,commands_fixed=True,
        baseline_reused=True,goal_complete=False))


if __name__=='__main__':
    try: main()
    except BaseException as error:
        import traceback
        save(AUDIT/'distribution_candidate_failure.json',dict(error=repr(error),traceback=traceback.format_exc()))
        raise
