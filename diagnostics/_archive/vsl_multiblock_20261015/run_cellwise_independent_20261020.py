"""Frozen cell16..18 correction: independent recorded seed67/71 comparisons.

Four scalar450s forecasts per seed; no refit, native run or source modification.
Replay bootstrap and canonical command binding reuse the qualified earlier recipe.
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import argparse,copy,csv,datetime,gzip,hashlib,importlib.util,json,math,sys,time,traceback
from pathlib import Path
sys.dont_write_bytecode=True
V=Path(__file__).resolve().parent
FIT=V/'cellwise_smallstep_20261020'
ROOT=Path('D:/VISSIM_packages/vsl_multizone355_20261015')
R=ROOT/'diagnostics/repin_v3c3_review_20261001'
TUNING=R/'urban_rm269/aggregate270/vsl_schedules_20261015/config.json'
BASE=Path('E:/VISSIM_analysis/20261011_vsl_response349')
PINS={}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
    p=Path(p);raw=p.read_bytes();PINS[str(p)]=hashlib.sha256(raw).hexdigest()
    return json.loads(raw.decode('utf-8-sig'))
def save(p,x):
    tmp=p.with_name(p.name+'.tmp');tmp.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8');os.replace(tmp,p)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,choices=(67,71),required=True);args=ap.parse_args()
    seed=args.seed;out=V/'cellwise_independent_20261020'/f'seed{seed}'
    assert not out.exists(),'Reuse existing case; no duplicate'
    assert not any((p/'STOP').exists() for p in (V,FIT,out.parent))
    selection=read(FIT/'selection.json');protocol=read(FIT/'protocol.json');closed=read(FIT/'owner_closure.json')
    assert selection['eligible_for_development'] and closed['recorded_pid_absent'] and closed['actual_exit_code']==0
    variants={'original':protocol['initial'],'fitted':selection['values']}
    assert len(variants['original'])==15 and max(abs(x) for x in selection['relative_step'])<=.05000001
    start=2700 if seed==67 else 2250
    folder=Path('D:/VISSIM_runs/20261003_s67_vsl_observation2700/release/decisions_sdmpc31_g_2700_release_s67') if seed==67 else Path('D:/VISSIM_runs/20261003_independent_s71_four84/nc/decisions_sdmpc31_g_2250_nc_s71')
    arms=('release','release_vsl90') if seed==67 else ('rm','both')
    receipt=read(BASE/f'matched_seed{seed}_v3/fixed_replay_receipt.json')
    for p,h in receipt['files'].items():assert sha(p)==h,p
    assert receipt['observation_cutoff_sec']==start and not receipt['future_states_used']
    preparation=read(out.parent/'preparation.json')
    assert sha(Path(__file__))==preparation['runner_sha256']
    launch=out.parent/f'seed{seed}_launch.json'
    assert not launch.exists(),'Reuse the already claimed case'
    save(launch,dict(pid=os.getpid(),entry_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),seed=seed,command=sys.argv,attempts=1,native=0))
    os.environ['NUMSIM_REPO_ROOT']=str(ROOT/'vendor/NumSim-mine')
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    import numpy as np
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_pfo,sdmpc_sequence as seq
    from evaluation.controllers import physical_ramp_branches as ramps,signal_actuation_contract as signals,runtime_setup
    from evaluation.controllers import offramp_routing as route
    from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts
    from evaluation.controllers.control_area_objective import get_ledger,physical_membership_from_ledger
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.area_follower_objective import expand_shared_vsl_action,shared_query_runtime_scope
    from src.controllers import rollout_endpoint as endpoint
    from src.models.state import ControlAction
    sys.argv=['verify.py','--at',str(start),'--out',str(out),'--no-prediction','--cold-prices','--tuning',str(TUNING),'--decisions',str(folder)]
    loader=importlib.util.spec_from_file_location('cellwise_independent_bootstrap',R/'urban260/verify.py')
    verifier=importlib.util.module_from_spec(loader);loader.loader.exec_module(verifier)
    original_main=adapter.main
    def wrapped_main():
        from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
        from evaluation.controllers import obs150_contract as oc
        derived=Path(receipt['derived_directory'])
        head,vsl=probe.replay_head_history,probe.replay_vsl_history
        probe.replay_head_history=lambda *a,**k:head(*a,**dict(k,derived_directory=derived))
        probe.replay_vsl_history=lambda *a,**k:vsl(*a,**dict(k,derived_directory=derived,compare_online=False))
        def readonly(raw,document):
            path=derived/f"derived_{document['sim_sec']:06d}.json"
            assert path.read_bytes()==oc.derived_bytes(document);return path
        oc.write_derived=readonly
        previous=probe.bind_fixed_replay_reference(receipt,folder,out)
        sys.argv[sys.argv.index('--previous-action-json')+1]=str(previous)
        captured={};bound=ramps.configure_operating_bounds;forecast=adapter.demand_from_state;configure=runtime_setup.configure_runtime
        def capture_runtime(*a,**k):
            result=configure(*a,**k);captured.update(mapping=a[3],calibration=a[7],tuning=a[2]);return result
        def capture_bound(state,cfg,ref):
            captured.update(state=state,cfg=cfg);return bound(state,cfg,ref)
        def capture_forecast(*a,**k):
            result=forecast(*a,**k);captured['forecast']=result;return result
        runtime_setup.configure_runtime=capture_runtime;ramps.configure_operating_bounds=capture_bound;adapter.demand_from_state=capture_forecast
        def run(*unused,**kw):
            state,cfg=captured['state'],captured['cfg']
            assert state.time_sec==start and not hasattr(state,'_refine15')
            assert (cfg.simulation.T_f_sec,cfg.simulation.T_u_sec,cfg.mpc.horizon_steps)==(5,10,3)
            assert not state.lane_freeway_runtime.lanes
            assert len(state.freeway_density['FW_E'])==31
            for name in ('RM_C10639','RM_C10484'):
                buffer=state.lane_ramp_runtime.buffers[name]
                assert all(getattr(b,'_causal_receiving_enabled',False) for b in getattr(buffer,'_lane_buffers',[buffer]))
            initial=copy.deepcopy(get_ledger(state).stocks);initial_n=continuity_vehicle_counts(state,cfg)
            physical=physical_membership_from_ledger(read(ROOT/read(TUNING)['control_area_objective']['membership_path']))
            raw=read(folder/f'state_{start:06d}.json')
            assert sum(physical.values())==701
            observed=sum(physical[str(v['link_no'])] for v in raw['vehicle_records']['records'])
            assert abs(observed-sum(v['inside'] for v in initial.values()))<1e-7
            segment_vsl=adapter.repo_imports(ROOT/'vendor/NumSim-mine')[-1]
            commands={};actual={}
            inventory=state.lane_freeway_runtime.configs['FW_E'].network.offramp_route_inventory
            for arm in arms:
                native_folder=Path(receipt['candidate_actions'][arm][0]).parent
                assert read(native_folder/f'state_{start:06d}.json')['vehicle_records']==raw['vehicle_records']
                blocks=[]
                for j,path in enumerate(receipt['candidate_actions'][arm]):
                    payload=read(path);command=seq.first_action(adapter.control_from_json(Path(path),cfg,ControlAction))
                    with shared_query_runtime_scope():
                        before={road:[float(segment_vsl(command,road,i,cfg)) for i in range(len(cfg.network.freeway_vsl_zone_head_of_cell[road]))] for road in cfg.network.freeway_links}
                        for road,values in before.items():
                            command.vsl[road]=min(values)
                            for i,value in enumerate(values):command.vsl[f'{road}__seg{i}']=value
                        assert before=={road:[float(segment_vsl(command,road,i,cfg)) for i in range(len(values))] for road,values in before.items()}
                    rewritten=out/f'{arm}_block{j}_vsl_binding.csv'
                    adapter.write_action_csv(rewritten,command,cfg,captured['mapping'],segment_vsl,payload['metadata'],adapter.adapter_actuation_settings(captured['calibration'],captured['tuning']),signal_group_plan_table=adapter.load_signal_group_actuation_plan(),offset_writer='experiment')
                    def signs(p):
                        with p.open(encoding='utf-8-sig',newline='') as f:return sorted((int(r['dsd_no']),float(r['speed_kph'])) for r in csv.DictReader(f) if r['kind']=='vsl')
                    assert signs(rewritten)==signs(Path(path).with_suffix('.csv'))
                    command,_=expand_shared_vsl_action(command,cfg,segment_vsl_func=segment_vsl)
                    signals.validate_writer(command,cfg,adapter.load_signal_group_actuation_plan(),'experiment');blocks.append(command)
                commands[arm]=blocks
                targets=[]
                for sec in (start+150,start+300,start+450):
                    obs=read(native_folder/f'state_{sec:06d}.json')
                    assert obs['sim_sec']==sec and obs['vehicle_records']['complete']
                    groups=[[] for _ in range(31)]
                    for car in obs['vehicle_records']['records']:
                        if str(car['link_no']) not in inventory['physical']:continue
                        road,pos,index=route._position(inventory,car['link_no'],car['position_m'])
                        if road=='FW_E':groups[index].append(car['speed_kph'])
                    targets.append(dict(time_sec=sec,n=[len(g) for g in groups],speed=[sum(g)/len(g) if g else None for g in groups]))
                actual[arm]=targets
            for left,right in zip(commands[arms[0]],commands[arms[1]]):
                assert all(getattr(left,k)==getattr(right,k) for k in ('green_times','offsets','ramp_metering'))
                assert {k:v for k,v in left.diagnostics.items() if k.startswith('rw_meter_green_')}=={k:v for k,v in right.diagnostics.items() if k.startswith('rw_meter_green_')}
            save(out/'protocol.json',dict(seed=seed,start=start,end=start+450,arms=arms,parameters=variants,fixed_coefficient_source=str(FIT/'selection.json'),same_city_rm=True,only_vsl_contrast=True,new_forecasts_budget=4,initial_omega=observed,future_state_input=False,spatial_refinement=False,clock_cap_override=False,previous_outcomes_seen=True,blind_test=False,native=0,production_adoption=False))
            save(out/'targets.json',actual)
            results={};origin_state,origin_cfg=state,cfg
            for variant,values in variants.items():
                for arm in arms:
                    assert len(results)<4 and not (out.parent/'STOP').exists()
                    state,cfg=copy.deepcopy((origin_state,origin_cfg))
                    net=state.lane_freeway_runtime.configs['FW_E'].network
                    existing=[]
                    for c in (16,17,18):
                        p=net.freeway_segment_params['FW_E'][c];r=net.freeway_state_response['FW_E']['cell_overrides'][str(c)]
                        existing.extend([p['rho_crit'],p['metanet_a_m'],r['relaxation']['acceleration_sec'],r['anticipation']['downstream_ge_local'],r['anticipation']['downstream_lt_local']])
                    assert np.max(np.abs(np.array(existing)-variants['original']))<1e-9
                    before=copy.deepcopy(net.freeway_segment_params['FW_E'])
                    for j,c in enumerate((16,17,18)):
                        rho,shape,tau,nge,nlt=values[j*5:j*5+5]
                        for network in (net,cfg.network):
                            network.freeway_segment_params['FW_E'][c].update(rho_crit=rho,metanet_a_m=shape)
                            if not hasattr(network,'freeway_state_response'):network.freeway_state_response={}
                            network.freeway_state_response.setdefault('FW_E',{}).setdefault('cell_overrides',{})[str(c)]=dict(relaxation=dict(acceleration_sec=tau,deceleration_sec=tau),anticipation=dict(downstream_ge_local=nge,downstream_lt_local=nlt))
                    assert net.freeway_segment_params['FW_E']==cfg.network.freeway_segment_params['FW_E']
                    assert all(net.freeway_segment_params['FW_E'][i]==before[i] for i in range(31) if i not in (16,17,18))
                    label=variant+'_'+arm;action=seq.pack(copy.deepcopy(commands[arm]));tick=time.perf_counter()
                    with seq.prediction_scope(action,cfg,start,3) as visits:
                        point=endpoint.evaluate_price_point(state,action,copy.deepcopy(captured['forecast'][:3]),(),endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
                    assert visits==[0,1,2] and not point.aborted and len(point.states)==3
                    response=point.control_area_response
                    assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
                    frames=[]
                    for st in point.states:
                        get_ledger(st).assert_stocks(model_inventory(st,cfg))
                        frames.append(dict(time_sec=st.time_sec,n=continuity_vehicle_counts(st,cfg)['FW_E'],speed=st.freeway_speed['FW_E']))
                    assert initial==get_ledger(state).stocks and initial_n==continuity_vehicle_counts(state,cfg)
                    through=[sum(r['accepted_total_veh'] for r in response['resource_allocations'] if r['kind']=='freeway_mainline_sending' and r['resource']=='FW_E:cell:18' and r['end_sec']<=start+h+1e-8) for h in (150,300,450)]
                    dn=np.array([p['n'] for p in frames])-np.array([q['n'] for q in actual[arm]])
                    dv=np.array([p['speed'] for p in frames])-np.array([q['speed'] for q in actual[arm]],dtype=float)
                    assert np.isfinite(dn).all()
                    scores=dict(n_rmse=float(np.sqrt(np.mean(dn[:,14:21]**2))),speed_rmse=float(np.sqrt(np.nanmean(dv[:,14:21]**2))),all31_n_rmse=float(np.sqrt(np.mean(dn**2))),all31_speed_rmse=float(np.sqrt(np.nanmean(dv**2))))
                    result=dict(ttt=point.ttt,throughflow=through,seconds=time.perf_counter()-tick,physical=True,scores=scores,frames=frames)
                    results[label]=result
                    with gzip.open(out/f'{label}_response.json.gz','wt',encoding='utf8') as f:json.dump(response,f,allow_nan=False)
                    save(out/f'{label}.json',result);save(out/'prediction_progress.json',dict(completed=list(results),new_native=0))
                    print('INDEPENDENT',seed,label,'seconds',round(result['seconds'],3),flush=True)
            for p in (Path(__file__),TUNING,R/'urban260/verify.py',ROOT/'evaluation/controllers/lane_freeway_runtime.py',ROOT/'evaluation/controllers/freeway_fd.py',ROOT/'evaluation/controllers/area_freeway_accounting.py'):PINS[str(p)]=sha(p)
            for p,h in PINS.items():assert sha(p)==h,p
            save(out/'summary.json',dict(status='complete_frozen_cellwise_independent',seed=seed,start=start,end=start+450,arms=arms,results=results,new_predictions=4,native_runs=0,fits=0,coefficient_updates=0,parameters=variants,independent_from_fit=True,blind_test=False,source_pins=PINS,candidate_adopted=False))
            raise verifier.Done()
        sdmpc_pfo.solve=run
        return original_main()
    adapter.main=wrapped_main
    try:
        verifier.main()
        assert (out/'summary.json').exists()
        save(out/'completion.json',dict(status='entrypoint_complete',new_forecasts=4,native=0))
    except BaseException as error:
        save(out/'failure.json',dict(error=repr(error),traceback=traceback.format_exc(),native=0));raise

if __name__=='__main__':main()
