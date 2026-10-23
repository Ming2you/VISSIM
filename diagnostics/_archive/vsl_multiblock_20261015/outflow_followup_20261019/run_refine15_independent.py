"""Two recorded VSL interventions at a verified common native initial state.

Native354 full recipe with optional existing receiving envelope on10639 and10484.
Conditional recorded-command response, not autonomous policy/cap or native validation.
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,copy,csv,gzip,hashlib,importlib.util,json,sys,time,ctypes
sys.dont_write_bytecode=True
k=ctypes.WinDLL("kernel32");k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
from pathlib import Path
ROOT=Path('D:/VISSIM_packages/vsl_multizone355_20261015');HERE=ROOT/'diagnostics/vsl_response349';BASE=Path('E:/VISSIM_analysis/20261011_vsl_response349');A=Path(__file__).resolve().parent
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
R=ROOT/'diagnostics/repin_v3c3_review_20261001'
TUNING=R/'urban_rm269/aggregate270/vsl_schedules_20261015/config.json'
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,choices=(67,71),required=True);ap.add_argument('--spatial-targets',action='store_true')
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    assert not a.out.exists() and not (HERE/'STOP').exists()
    start=2700 if a.seed==67 else 2250
    native=R/'s67_full_observation/analysis/summary.json' if a.seed==67 else I/'native_rm_observation2700_s71_four84/analysis/summary.json'
    folder=Path('D:/VISSIM_runs/20261003_s67_vsl_observation2700/release/decisions_sdmpc31_g_2700_release_s67') if a.seed==67 else Path('D:/VISSIM_runs/20261003_independent_s71_four84/nc/decisions_sdmpc31_g_2250_nc_s71')
    arms=('release','release_vsl90') if a.seed==67 else ('rm','both')
    assert not a.spatial_targets,'Adopted355 receiving is already configured; do not attach twice'
    fit=read(A/'refine15_regime_fit_v3/selection.json');done=read(A/'refine15_regime_fit_v3/completion.json')
    assert fit['eligible']
    for p,h in done['source_pins'].items():assert sha(p)==h,p
    old=read(A/'refine15_update_audit.json');p=old['parent_parameters'];r=old['state_response']
    variants={'original':[p['rho_crit'],p['metanet_a_m'],r['relaxation']['acceleration_sec'],r['anticipation']['downstream_ge_local'],r['anticipation']['downstream_lt_local']],'fitted':fit['fitted']['values']}
    alignment=R/'s67_full_observation/recording_start_alignment76.json' if a.seed==67 else None
    os.environ['NUMSIM_REPO_ROOT']=str(ROOT/'vendor/NumSim-mine')
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    sys.argv=['verify.py','--at',str(start),'--out',str(a.out),'--no-prediction','--cold-prices','--tuning',str(TUNING),'--decisions',str(folder)]
    spec=importlib.util.spec_from_file_location('matched349_bootstrap',R/'urban260/verify.py')
    verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_pfo,sdmpc_sequence as seq
    from evaluation.controllers import physical_ramp_branches as ramps,signal_actuation_contract as signals
    from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts
    from evaluation.controllers.control_area_objective import get_ledger,physical_membership_from_ledger
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.area_follower_objective import expand_shared_vsl_action,shared_query_runtime_scope
    from src.controllers import rollout_endpoint as endpoint
    from src.models.state import ControlAction
    def save(name,x):(a.out/name).write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    original_main=adapter.main
    def wrapped_main():
        from refine_approach15 import Refinement
        from evaluation.controllers import multirate_freeway
        refine=Refinement(a.out);old_limit=multirate_freeway.time_limit
        multirate_freeway.time_limit=lambda runtime,state:min(.625,old_limit(runtime,state))
        from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
        from evaluation.controllers import obs150_contract as oc
        receipt=read(BASE/f'matched_seed{a.seed}_v3/fixed_replay_receipt.json')
        for source_path,expected in receipt['files'].items():
            assert sha(source_path)==expected, 'Previously qualified replay source changed: '+source_path
        assert receipt['observation_cutoff_sec']==start and not receipt['future_states_used']
        save('fixed_replay_receipt.json',receipt)
        derived=Path(receipt['derived_directory'])
        head,vsl=probe.replay_head_history,probe.replay_vsl_history
        probe.replay_head_history=lambda *args,**kw:head(*args,**dict(kw,derived_directory=derived))
        probe.replay_vsl_history=lambda *args,**kw:vsl(*args,**dict(kw,derived_directory=derived,compare_online=False))
        def readonly(raw,document):
            path=derived/f"derived_{document['sim_sec']:06d}.json"
            assert path.read_bytes()==oc.derived_bytes(document);return path
        oc.write_derived=readonly
        previous=probe.bind_fixed_replay_reference(receipt,folder,a.out)
        sys.argv[sys.argv.index('--previous-action-json')+1]=str(previous)
        captured={};bound=ramps.configure_operating_bounds;forecast=adapter.demand_from_state
        from evaluation.controllers import runtime_setup
        configure=runtime_setup.configure_runtime
        def capture_runtime(*args,**kwargs):
            result=configure(*args,**kwargs)
            captured.update(mapping=args[3],calibration=args[7],tuning=args[2])
            if a.spatial_targets:
                from evaluation.controllers.known_wout_causal_response import attach
                state, _, _ = result
                wave = args[2]['urban']['known_wout_causal_lane_response']['wave_m_s']
                before = dict(state.ramp_queue)
                receipts = []
                for name in ('RM_C10639','RM_C10484'):
                    buffer = state.lane_ramp_runtime.buffers[name]
                    assert not getattr(buffer,'lane_exchange_rates',None)
                    children = getattr(buffer,'_lane_buffers',[buffer])
                    assert len(children)==1
                    for child in children:
                        assert not getattr(child,'_causal_receiving_enabled',False)
                        attach(child,wave); child._causal_receiving_enabled=True
                        env=child._spatial_entry['envelope']
                        assert env.lag>=args[1].simulation.T_u_sec
                        receipts.append(dict(ramp=name,wave_m_s=wave,lag_sec=env.lag,
                            projection_max_m=env.projection_max_m,initial_prehead_veh=env.initial,capacity_veh=env.capacity))
                assert before==state.ramp_queue
                save('candidate_receipt.json',dict(targets=receipts,initial_mass_unchanged=True,parameter_fits=0))
            return result
        runtime_setup.configure_runtime=capture_runtime
        def capture_bound(state,cfg,reference):
            captured.update(state=state,cfg=cfg);return bound(state,cfg,reference)
        def capture_forecast(*args,**kw):
            result=forecast(*args,**kw);captured['forecast']=result;return result
        ramps.configure_operating_bounds=capture_bound;adapter.demand_from_state=capture_forecast
        def run(*unused,**kw):
            state,cfg=captured['state'],captured['cfg'];assert state.time_sec==start
            assert cfg.simulation.T_f_sec==5 and cfg.simulation.T_u_sec==10
            initial=copy.deepcopy(get_ledger(state).stocks);initial_n=continuity_vehicle_counts(state,cfg)
            physical=physical_membership_from_ledger(read(ROOT/read(TUNING)['control_area_objective']['membership_path']))
            raw=read(folder/f'state_{start:06}.json')
            assert sum(physical.values())==701
            observed=sum(physical[str(v['link_no'])] for v in raw['vehicle_records']['records'])
            assert abs(observed-sum(v['inside'] for v in initial.values()))<1e-7
            pins={str(TUNING):sha(TUNING),str(Path(__file__)):sha(__file__)};commands={}
            segment_vsl=adapter.repo_imports(ROOT/'vendor/NumSim-mine')[-1]
            for arm in arms:
                blocks=[]
                for index,path in enumerate(receipt['candidate_actions'][arm]):
                    pins[path]=sha(path);command=seq.first_action(adapter.control_from_json(Path(path),cfg,ControlAction))
                    # Historical root aliases differ from their segment minimum.
                    # Preserve effective zone speeds and prove actual DSD equality
                    # using the canonical writer before strict alias expansion.
                    with shared_query_runtime_scope():
                        before={road:[float(segment_vsl(command,road,i,cfg))
                            for i in range(len(cfg.network.freeway_vsl_zone_head_of_cell[road]))]
                            for road in cfg.network.freeway_links}
                        for road,values in before.items():
                            command.vsl[road]=min(values)
                            for i,value in enumerate(values):command.vsl[f'{road}__seg{i}']=value
                        assert before=={road:[float(segment_vsl(command,road,i,cfg))
                            for i in range(len(values))] for road,values in before.items()}
                    rewritten=a.out/f'{arm}_block{index}_vsl_binding.csv'
                    adapter.write_action_csv(rewritten,command,cfg,captured['mapping'],segment_vsl,
                        read(path)['metadata'],adapter.adapter_actuation_settings(captured['calibration'],captured['tuning']),
                        signal_group_plan_table=adapter.load_signal_group_actuation_plan(),offset_writer='experiment')
                    def signs(source):
                        with source.open(encoding='utf-8-sig',newline='') as stream:
                            return sorted((int(row['dsd_no']),float(row['speed_kph']))
                                for row in csv.DictReader(stream) if row['kind']=='vsl')
                    assert signs(rewritten)==signs(Path(path).with_suffix('.csv'))
                    command,_=expand_shared_vsl_action(command,cfg,segment_vsl_func=segment_vsl)
                    signals.validate_writer(command,cfg,adapter.load_signal_group_actuation_plan(),'experiment');blocks.append(command)
                commands[arm]=blocks
            for left,right in zip(commands[arms[0]],commands[arms[1]]):
                assert left.green_times==right.green_times and left.offsets==right.offsets
                assert left.ramp_metering==right.ramp_metering
                assert {k:v for k,v in left.diagnostics.items() if k.startswith('rw_meter_green_')}=={k:v for k,v in right.diagnostics.items() if k.startswith('rw_meter_green_')}
            save('protocol.json',dict(seed=a.seed,start=start,end=start+450,arms=arms,scope=__doc__,pins=pins,
                same_city_commands=True,same_rm=True,only_vsl_intervention=True,
                spatial_targets=a.spatial_targets,initial_omega_vehicles=observed,initial_stocks=initial,
                future_observation_inputs=False,recorded_future_commands_are_conditions=True))
            results={};origin_state,origin_cfg=state,cfg
            pins[str(A/'refine15_regime_fit_v3/selection.json')]=sha(A/'refine15_regime_fit_v3/selection.json')
            pins[str(A/'refine_approach15.py')]=sha(A/'refine_approach15.py')
            assert hasattr(origin_state,'_refine15')
            for name in ('RM_C10639','RM_C10484'):
                buf=origin_state.lane_ramp_runtime.buffers[name]
                assert all(getattr(b,'_causal_receiving_enabled',False) for b in getattr(buf,'_lane_buffers',[buf]))
            for variant,values in variants.items():
                for arm in arms:
                    state,cfg=copy.deepcopy((origin_state,origin_cfg))
                    for net in (cfg.network,state.lane_freeway_runtime.configs['FW_E'].network):
                        net.freeway_segment_params['FW_E'][15].update(rho_crit=values[0],metanet_a_m=values[1])
                        if not hasattr(net,'freeway_state_response'):net.freeway_state_response={}
                        net.freeway_state_response.setdefault('FW_E',{}).setdefault('cell_overrides',{})['15']=dict(relaxation=dict(acceleration_sec=values[2],deceleration_sec=values[2]),anticipation=dict(downstream_ge_local=values[3],downstream_lt_local=values[4]))
                    label=variant+'_'+arm;action=seq.pack(commands[arm]);tick=time.perf_counter();refine.trace=[]
                    with seq.prediction_scope(action,cfg,start,3) as visits:
                        point=endpoint.evaluate_price_point(state,action,copy.deepcopy(captured['forecast'][:3]),(),endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
                    elapsed=time.perf_counter()-tick;assert visits==[0,1,2] and not point.aborted and len(point.states)==3
                    response=point.control_area_response
                    assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
                    snapshots=[]
                    for current in (state,*point.states):
                        ledger=get_ledger(current);ledger.assert_stocks(model_inventory(current,cfg))
                        snapshots.append(dict(time_sec=current.time_sec,stocks=ledger.stocks,n=continuity_vehicle_counts(current,cfg),speed=current.freeway_speed,ramp_queue=current.ramp_queue,refinement=current._refine15))
                    assert initial==get_ledger(state).stocks and initial_n==continuity_vehicle_counts(state,cfg)
                    costs={};outside={}
                    for row in response['residence']:
                        for key,value in row['inside_veh'].items():
                            costs[key]=costs.get(key,0.)+value*row['dt_h']
                            outside[key]=outside.get(key,0.)+(row['model_stock_veh'][key]-value)*row['dt_h']
                    assert abs(sum(costs.values())-point.ttt)<1e-7
                    through=[sum(x['accepted_total_veh'] for x in response['resource_allocations'] if x['kind']=='freeway_mainline_sending' and x['resource']=='FW_E:cell:18' and x['end_sec']<=start+t+1e-8) for t in (150,300,450)]
                    (a.out/(label+'_response.json.gz')).write_bytes(gzip.compress(json.dumps(response,allow_nan=False).encode('utf8')))
                    save(label+'_snapshots.json',snapshots);save(label+'_subcells.json',refine.trace)
                    results[label]=dict(ttt=point.ttt,costs_by_stock=costs,outside_costs_by_stock=outside,throughflow=through,seconds=elapsed,physical_constraints=True,writer=True,sdmpc_cap_or_selection_claimed=False)
                    save('prediction_progress.json',results);print('INDEPENDENT',a.seed,label,point.ttt,elapsed,flush=True)
            for p,h in pins.items():assert sha(p)==h,p
            save('summary.json',dict(status='complete_frozen_independent_pair_comparison',seed=a.seed,start=start,end=start+450,results=results,new_predictions=4,native_runs=0,fits=0,coefficient_updates=0,parameters=variants,independent_from_fit=True,previous_native_outcomes_seen_during_model_development=True,blind_test_claimed=False,source_pins=pins,max_route_balance=refine.max_balance,max_vsl_balance=refine.max_cohort,candidate_adopted=False))
            raise verifier.Done()
        sdmpc_pfo.solve=run
        try:return original_main()
        finally:
            refine.restore();multirate_freeway.time_limit=old_limit
    adapter.main=wrapped_main
    try:
        verifier.main()
        save('source_recipe.json',dict(root=str(ROOT),tuning=str(TUNING),spatial_targets=a.spatial_targets,production_adopted=False))
    except BaseException as err:
        import traceback
        if a.out.exists():
            save('failure_preserved.json',dict(error=type(err).__name__+': '+str(err),native_runs=0,fits=0,completed_forecasts=len(read(a.out/'prediction_progress.json')) if (a.out/'prediction_progress.json').exists() else 0))
            (a.out/'traceback.txt').write_text(''.join(traceback.format_exception(err)),encoding='utf8')
        raise

if __name__=='__main__':main()
