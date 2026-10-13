"""One fresh2700 selected-arm first150 response. No optimizer or native run.

Controller horizon remains450. This truncated diagnostic separates initial-state
propagation from local dynamics during a W_out interval with no vehicle removals.
"""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
from pathlib import Path
import copy, gzip, hashlib, importlib.util, json, sys, time

HERE=Path(__file__).resolve().parent;H=HERE.parent;ROOT=HERE.parents[3]
OUT=HERE/'forecast2700_v3'
F=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/selected/decisions_sdmpc31_g_2400_selected_s29')
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False,
        default=lambda value:repr(value)[:600])+'\n',encoding='utf8')

def main():
    assert not OUT.exists(),'No duplicate prediction'
    plan=read(HERE/'plan.json')
    for path,digest in plan['source_pins'].items():assert sha(Path(path))==digest,path
    assert read(HERE/'audit.json')['arms']['selected']['blocks'][-1]['removals_W_out']==0
    tuning=H/'connector_lane/config.json'
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    os.environ.update(NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'),PYTHONDONTWRITEBYTECODE='1')
    sys.argv=['verify.py','--at','2700','--out',str(OUT),'--no-prediction','--cold-prices','--tuning',str(tuning),'--decisions',str(F)]
    loader=importlib.util.spec_from_file_location('canonical_verifier2700',H.parent/'urban260/verify.py')
    verifier=importlib.util.module_from_spec(loader);loader.loader.exec_module(verifier)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_pfo,sdmpc_sequence as seq
    from evaluation.controllers import physical_ramp_branches as ramps,signal_actuation_contract as signals
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers import head_service_resources as heads,vsl_exposure_history as exposure
    from evaluation.controllers import obs150_contract as oc,obs150_observation as observer,lane_plant_runtime as lane
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
    from src.controllers import rollout_endpoint as endpoint
    from src.models.state import ControlAction
    observe_heads,initialize_vsl=heads.observe,exposure.initialize
    old_main=adapter.main
    def wrapped_main():
        # Fixed-command native replay did not run the online observer. Rebuild
        # its causal products with the canonical observer into this diagnostic
        # directory; never add derived files or applied markers to native data.
        context=lane.load_sources(read(tuning)['freeway']['lane_plant'])
        history=OUT/'derived_history';history.mkdir()
        pins={};run_id=None
        for at in range(150,2701,150):
            path=F/f'state_{at:06}.json';raw=read(path);pins[str(path.resolve())]=sha(path)
            if run_id is None:run_id=raw['run_provenance']['run_id']
            assert raw['sim_sec']==at and raw['run_provenance']['run_id']==run_id==raw['obs150']['run_id']
            cached=HERE/'forecast2700_v2/derived_history'/f'derived_{at:06}.json'
            derived=read(cached)
            assert derived['inputs']['raw_sha256']==oc.canonical_sha256(raw['obs150'])
            assert derived['window']==dict(start_s=at-150,end_s=at)
            (history/f'derived_{at:06}.json').write_bytes(oc.derived_bytes(derived))
        execution_path=H/'native2400_analysis/selected/execution.json'
        execution=read(execution_path);pins[str(execution_path.resolve())]=sha(execution_path)
        assert execution['native_execution_passed']
        closure_path=H/'native2400_analysis/runtime_closure.json'
        closure=read(closure_path);pins[str(closure_path.resolve())]=sha(closure_path)
        assert closure['all_owned_processes_closed'] and closure['owner_exit_code']==0
        assert closure['normal_native_end_sec']==2850 and 'selected' in closure['arms']
        assert Path(closure['runs_root']).resolve()==F.parent.parent.resolve()
        assert execution['run_id']==run_id and execution['terminal_sec']==2850
        checks={x['sim_sec']:x for x in execution['checks']['actual_commands']['decisions']}
        for at in (2550,2700):
            for ext in ('.json','.csv'):
                path=F/f'action_{at:06}{ext}';pins[str(path.resolve())]=sha(path)
                if ext=='.csv':assert pins[str(path.resolve())]==checks[at]['sha256']
        receipt=dict(observation_cutoff_sec=2700,files=pins,native_summary=str(H/'native2400_analysis/summary.json'),
            future_states_used=False,price_markers_fabricated=False,online_observer_was_not_run=True)
        previous=probe.bind_fixed_replay_reference(receipt,F,OUT)
        sys.argv[sys.argv.index('--previous-action-json')+1]=str(previous)
        save('offline_history.json',receipt)
        def verify_derived(raw,derived):
            target=history/f"derived_{derived['sim_sec']:06}.json"
            assert target.read_bytes()==oc.derived_bytes(derived)
            return target
        oc.write_derived=verify_derived
        head_inputs=[]
        def warm(original,cfg,raw,previous_path,caps,signal_plan,distribute,options):
            return probe.replay_head_history(observe_heads,original,cfg,raw,caps,signal_plan,distribute,options,
                folder=F,sim_sec=2700,output=OUT,history_inputs=head_inputs,derived_directory=history)
        heads.observe=warm
        missing=[t for t in range(150,2701,150) if not (F/'obs150'/f'vsl_cohorts_{t:06}.json').exists()]
        exposure.initialize=lambda context,raw,state,cfg:probe.replay_vsl_history(initialize_vsl,context,raw,state,cfg,OUT,
            derived_directory=history,known_missing_online_cutoffs=missing)
        captured={};old_bounds=ramps.configure_operating_bounds;old_forecast=adapter.demand_from_state
        def bounds(state,cfg,reference):
            captured.update(state=state,cfg=cfg)
            return old_bounds(state,cfg,reference)
        def forecast(*args,**kwargs):
            result=old_forecast(*args,**kwargs);captured['forecast']=result;return result
        ramps.configure_operating_bounds=bounds;adapter.demand_from_state=forecast
        def audit(reference,coord,policy,options,evaluate,derivative,quantities,check_budget,emit):
            state,cfg=captured['state'],captured['cfg']
            assert cfg.network.known_legsplit_routes['connector_queue_gate']
            assert cfg.network.known_legsplit_routes['lateral_access_rate_per_sec']==read(H/'lateral_access/past_fit.json')['rate_per_sec']
            save('initial_state.json',vars(state));save('network.json',vars(cfg.network))
            action_path=F/'action_002700.json'
            action=seq.first_action(adapter.control_from_json(action_path,cfg,ControlAction))
            signals.validate_writer(action,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
            save('applied_command.json',vars(action))
            start=time.perf_counter()
            point=endpoint.evaluate_price_point(state,action,copy.deepcopy(captured['forecast'][:1]),(),
                endpoint.ObjectiveSpec(cfg,depth_override=1,box_walk=False,score_mode='raw'),capture_response=True)
            save('rollout_status.json',dict(aborted=point.aborted,states=len(point.states),expected_depth=1))
            assert not point.aborted and len(point.states)==1
            response=point.control_area_response
            with gzip.open(OUT/'applied.response.json.gz','wt',encoding='utf8') as stream:json.dump(response,stream,allow_nan=False)
            assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
            exceed=max((r['exceedance_veh'] for r in response['resource_allocations']),default=0.)
            assert exceed<=1e-7
            for current in (state,*point.states):get_ledger(current).assert_stocks(model_inventory(current,cfg))
            costs={}
            for row in response['residence']:
                for key,n in row['inside_veh'].items():costs[key]=costs.get(key,0.)+n*row['dt_h']
            assert abs(sum(costs.values())-point.ttt)<1e-7
            save('summary.json',dict(status='complete',start_sec=2700,end_sec=2850,forecast_sec=150,
                controller_horizon_sec=450,forecasts=1,native_runs=0,optimizer_calls=0,new_coefficients=0,
                future_observation_inputs=False,command_path=str(action_path),command_sha256=sha(action_path),
                omega_ttt_veh_h=point.ttt,costs_by_stock=costs,predicted_merge=point.control_area['predicted_ramp_merge'],
                wall_sec=time.perf_counter()-start,resource_max_exceedance=exceed,conservation_states=2,
                known_initial_cohorts=state.known_legsplit_route_state['cohorts'],
                known_endpoint_cohorts=point.states[-1].known_legsplit_route_state['cohorts'],
                scope='Same executed2700 command and fresh2700 native state. Autonomous150 diagnostic only; no causal two-arm gain or full450 qualification.'))
            print('FRESH2700_DONE',round(point.ttt,6),flush=True)
            raise verifier.Done()
        sdmpc_pfo.solve=audit
        return old_main()
    adapter.main=wrapped_main
    verifier.main()

if __name__=='__main__':main()
