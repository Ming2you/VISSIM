"""Bounded cell-specific coupled trajectory calibration from completed OFF data.

Current 31-cell geometry and FW5/U10 remain unchanged. No native launch, no
production edit, no controller optimization, and no future state injection.
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import copy, datetime, gzip, hashlib, importlib.util, json, math, sys, time, traceback
from pathlib import Path

V=Path(__file__).resolve().parent
A=V/'outflow_followup_20261019'
O=V/'cellwise_smallstep_20261020'
PREVIOUS=V/'cellwise_coupled_20261020'
ROOT=Path('D:/VISSIM_packages/vsl_multizone355_20261015')
CONFIG=ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/vsl_schedules_20261015/config.json'
VERIFY=ROOT/'diagnostics/repin_v3c3_review_20261001/urban260/verify.py'
OLD=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/cellwise_calibration'
HOLD=Path('E:/VISSIM_runs/20261011_vsl349_off2250_s29/hold/decisions_sdmpc31_g_2250_hold_s29')
OBS=Path('E:/VISSIM_runs/20261008_coupling268_off_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
PINS={}
CELLS=(16,17,18)
TIMES=(1650,2250,2850)
NAMES=('rho_crit','metanet_a_m','tau_sec','nu_ge','nu_lt')

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
    p=Path(p);raw=p.read_bytes();PINS[str(p)]=hashlib.sha256(raw).hexdigest()
    return json.loads(raw)
def save(p,x):
    temp=p.with_name(p.name+'.tmp')
    temp.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    os.replace(temp,p)


def main():
    assert not (O/'launch.json').exists(), 'Reuse existing invocation.'
    assert not any((p/'STOP').exists() for p in (V,A,O,PREVIOUS))
    preparation=read(O/'protocol.json')
    for path,digest in preparation['source_pins'].items():
        assert sha(path)==digest,path
    assert sha(Path(__file__))==read(O/'preparation_receipt.json')['runner_sha256']
    save(O/'launch.json',dict(pid=os.getpid(),entry_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=sys.argv,attempts=1))
    active=read(V/'cached_vsl_exposure_audit_v2/active_component_config.json')
    reference=read(OLD/'expanded_joint/eval_036/reference_config.json')
    params=active['parameters'];responses=reference['freeway']['state_response']['FW_E']['cell_overrides']
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    os.environ['NUMSIM_REPO_ROOT']=str(ROOT/'vendor/NumSim-mine')
    import numpy as np
    from scipy.optimize import lsq_linear
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,head_service_resources,vsl_exposure_history
    from evaluation.controllers import physical_ramp_branches as ramps,signal_actuation_contract as signals,sdmpc_pfo,sdmpc,sdmpc_sequence as seq,offramp_routing as route
    from evaluation.controllers.control_hold import fixed_vsl_values
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts
    from src.controllers import rollout_endpoint as endpoint
    from src.models.state import ControlAction
    initial=np.array(preparation['initial'])
    z=np.array(preparation['relative_step'])
    sdmpc.load_prices=lambda *a,**k:(np.zeros(2),dict(source='offline_cellwise_coupled_cold_prices',committed=False))
    captured={};forecast_count=0
    def capture(at):
        patched=[(adapter,'demand_from_state'),(ramps,'configure_operating_bounds'),(head_service_resources,'observe'),(vsl_exposure_history,'initialize'),(signals,'_validate_native_vector'),(sdmpc_pfo,'solve')]
        originals={(module,name):getattr(module,name) for module,name in patched}
        temp={}
        def bounds(state,cfg,ref):
            value=originals[ramps,'configure_operating_bounds'](state,cfg,ref);temp.update(state=state,cfg=cfg);return value
        def demand(*a,**k):
            value=originals[adapter,'demand_from_state'](*a,**k);temp['forecast']=value;return value
        ramps.configure_operating_bounds=bounds;adapter.demand_from_state=demand
        sys.argv=[str(VERIFY),'--at',str(at),'--out',str(O/f'capture_{at}'),'--tuning',str(CONFIG),'--decisions',str(OBS),'--full-selection']
        loader=importlib.util.spec_from_file_location(f'cellwise_capture_{at}',VERIFY)
        verifier=importlib.util.module_from_spec(loader);loader.loader.exec_module(verifier)
        def stop(*a,**k):
            s,cfg=temp['state'],temp['cfg']
            assert s.time_sec==at and not hasattr(s,'_refine15')
            assert (cfg.simulation.T_f_sec,cfg.simulation.T_u_sec,cfg.mpc.horizon_steps)==(5,10,3)
            assert not s.lane_freeway_runtime.lanes
            net=s.lane_freeway_runtime.configs['FW_E'].network
            assert net.freeway_segment_params['FW_E']==params
            assert all(net.freeway_state_response['FW_E']['cell_overrides'][str(c)]==responses[str(c)] for c in CELLS)
            get_ledger(s).assert_stocks(model_inventory(s,cfg))
            captured[at]=temp.copy();raise verifier.Done()
        sdmpc_pfo.solve=stop
        try:verifier.main()
        finally:
            for (module,name),value in originals.items():setattr(module,name,value)
        assert at in captured
        raw=read(OBS/f'state_{at:06d}.json')
        if at in (1650,2250):assert raw['vehicle_records']==read(HOLD/f'state_{at:06d}.json')['vehicle_records']
        actions=[]
        for sec in (at,at+150,at+300):
            path=(HOLD if at in (1650,2250) else OBS)/f'action_{sec:06d}.json'
            read(path)
            if at==2850:assert Path(str(path)+'.applied').is_file()
            block=seq.first_action(adapter.control_from_json(path,temp['cfg'],ControlAction))
            assert all(float(x)==110 for x in block.vsl.values())
            if at in (1650,2250):
                old=seq.first_action(adapter.control_from_json(OBS/f'action_{sec:06d}.json',temp['cfg'],ControlAction))
                assert all(getattr(block,k)==getattr(old,k) for k in ('ramp_metering','vsl','green_times','offsets','inflow_outflow_allocation'))
            signals.validate_writer(block,temp['cfg'],adapter.load_signal_group_actuation_plan(),'experiment')
            actions.append(block)
        captured[at]['actions']=actions
        save(O/f'capture_{at}/isolated_capture.json',dict(time_sec=at,optimizer_calls=0,forecasts=0,
            component_cell_count=len(temp['state'].freeway_density['FW_E']),parent_cell_count=len(temp['cfg'].network.freeway_segment_params['FW_E']),
            initial_stock=continuity_vehicle_counts(temp['state'],temp['cfg']),initial_speed=temp['state'].freeway_speed))

    def truth(at):
        inventory=captured[at]['state'].lane_freeway_runtime.configs['FW_E'].network.offramp_route_inventory
        output=[]
        for sec in (at+150,at+300,at+450):
            raw=read((HOLD if at in (1650,2250) else OBS)/f'state_{sec:06d}.json')
            assert raw['sim_sec']==sec and raw['vehicle_records']['complete']
            groups=[[] for _ in range(31)]
            for car in raw['vehicle_records']['records']:
                if str(car['link_no']) not in inventory['physical']:continue
                road,pos,index=route._position(inventory,car['link_no'],car['position_m'])
                if road=='FW_E':groups[index].append(car['speed_kph'])
            assert all(groups)
            output.append(dict(time_sec=sec,n=[len(g) for g in groups],speed=[sum(g)/len(g) for g in groups]))
        return output

    def predict(at,values,label,zones=None):
        nonlocal forecast_count
        assert forecast_count<4 and not (O/'STOP').exists()
        forecast_count+=1
        save(O/'progress.json',dict(stage='predicting',label=label,at=at,forecasts_entered=forecast_count))
        state,cfg=copy.deepcopy((captured[at]['state'],captured[at]['cfg']))
        net=state.lane_freeway_runtime.configs['FW_E'].network
        before=copy.deepcopy(net.freeway_segment_params['FW_E'])
        assert cfg.network.freeway_segment_params['FW_E']==before and len(before)==31
        for i,c in enumerate(CELLS):
            rho,a,tau,nge,nlt=map(float,values[i*5:i*5+5])
            net.freeway_segment_params['FW_E'][c].update(rho_crit=rho,metanet_a_m=a)
            net.freeway_state_response['FW_E']['cell_overrides'][str(c)]=dict(relaxation=dict(acceleration_sec=tau,deceleration_sec=tau),anticipation=dict(downstream_ge_local=nge,downstream_lt_local=nlt))
            # initialize() copies the physical31 table into resource/objective
            # consumers as well. Maintain that contract; VSL keys remain parent21.
            cfg.network.freeway_segment_params['FW_E'][c]=copy.deepcopy(net.freeway_segment_params['FW_E'][c])
            if not hasattr(cfg.network,'freeway_state_response'):cfg.network.freeway_state_response={}
            cfg.network.freeway_state_response.setdefault('FW_E',{}).setdefault('cell_overrides',{})[str(c)]=copy.deepcopy(net.freeway_state_response['FW_E']['cell_overrides'][str(c)])
        assert cfg.network.freeway_segment_params['FW_E']==net.freeway_segment_params['FW_E']
        assert all(net.freeway_segment_params['FW_E'][i]==before[i] for i in range(31) if i not in CELLS)
        actions=copy.deepcopy(captured[at]['actions'])
        for j,b in enumerate(actions):
            b.vsl=fixed_vsl_values(b.vsl,dict(start_sec=at,base_kmh=110,zone_kmh=zones or {}),cfg.network.freeway_vsl_zone_heads,at+150*j)
            signals.validate_writer(b,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
        action=seq.pack(actions);began=time.perf_counter()
        with seq.prediction_scope(action,cfg,at,3) as visits:
            point=endpoint.evaluate_price_point(state,action,copy.deepcopy(captured[at]['forecast'][:3]),(),endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
        assert visits==[0,1,2] and not point.aborted and len(point.states)==3
        response=point.control_area_response
        assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
        frames=[]
        for st in point.states:
            get_ledger(st).assert_stocks(model_inventory(st,cfg))
            n=continuity_vehicle_counts(st,cfg)
            frames.append(dict(time_sec=st.time_sec,n=n['FW_E'],speed=st.freeway_speed['FW_E']))
        through=[sum(r['accepted_total_veh'] for r in response['resource_allocations'] if r['kind']=='freeway_mainline_sending' and r['resource']=='FW_E:cell:18' and r['end_sec']<=at+h+1e-8) for h in (150,300,450)]
        result=dict(label=label,start=at,values=list(map(float,values)),frames=frames,through=through,ttt=point.ttt,seconds=time.perf_counter()-began,physical=True)
        if label.startswith(('baseline','fitted','development')):
            response_path=O/f'{label}_response.json.gz'
            with gzip.open(response_path,'wt',encoding='utf8') as f:json.dump(response,f,allow_nan=False)
            result['response_cache']=str(response_path)
            result['response_sha256']=sha(response_path)
        save(O/f'{label}.json',result)
        print('TRAJECTORY',label,forecast_count,'seconds',round(result['seconds'],3),flush=True)
        return result
    for p in (Path(__file__),CONFIG,VERIFY,ROOT/'evaluation/controllers/lane_freeway_runtime.py',ROOT/'evaluation/controllers/area_freeway_accounting.py',ROOT/'evaluation/controllers/freeway_fd.py'):
        PINS[str(p)]=sha(p)
    for at in TIMES:
        capture(at)
        previous=read(PREVIOUS/f'capture_{at}/isolated_capture.json')
        current=read(O/f'capture_{at}/isolated_capture.json')
        assert previous==current,'Initial capture changed'
    actual={str(at):truth(at) for at in TIMES}
    assert actual==read(PREVIOUS/'training_truth.json'),'Training targets changed'
    rows=[predict(at,initial*(1+z),f'fitted_small_{at}') for at in TIMES]
    parts=[];scores={}
    for row in rows:
        q=actual[str(row['start'])]
        dn=np.array([p['n'] for p in row['frames']])-np.array([p['n'] for p in q])
        dv=np.array([p['speed'] for p in row['frames']])-np.array([p['speed'] for p in q])
        nd,vd=dn[:,14:21],dv[:,14:21]
        parts.extend((nd.ravel()/10,vd.ravel()/20))
        scores[str(row['start'])]=dict(n_rmse=float(np.sqrt(np.mean(nd**2))),speed_rmse=float(np.sqrt(np.mean(vd**2))),all31_n_rmse=float(np.sqrt(np.mean(dn**2))),all31_speed_rmse=float(np.sqrt(np.mean(dv**2))))
    residual=np.concatenate(parts)/math.sqrt(63)
    loss=float(residual@residual)
    baseline=preparation['baseline']
    guard=all(scores[str(at)][key]<=1.1*baseline['scores'][str(at)][key] for at in TIMES for key in ('n_rmse','speed_rmse','all31_n_rmse','all31_speed_rmse'))
    eligible=bool(loss<=.99*baseline['data_loss'] and guard)
    selection=dict(candidate_loss=loss,baseline_loss=baseline['data_loss'],training_reduction=1-loss/baseline['data_loss'],scores=scores,retention_guard=guard,eligible_for_development=eligible,relative_step=z.tolist(),values=(initial*(1+z)).tolist(),candidate_adopted=False,nonlinear_convergence_proven=False)
    save(O/'selection.json',selection)
    print('MEASURED_STEP',json.dumps(selection),flush=True)
    if eligible:
        selected=predict(2250,initial*(1+z),'development_twozone90',zones={'FW_E__seg10':90,'FW_E__seg13':90})
        hold=next(r for r in rows if r['start']==2250)
        save(O/'development_response.json',dict(hold=hold,selected=selected,flow_delta=[b-a for a,b in zip(hold['through'],selected['through'])],ttt_delta=selected['ttt']-hold['ttt']))
    for path,digest in PINS.items():assert sha(path)==digest,path
    save(O/'completion.json',dict(status='complete_pending_assessment',forecasts=forecast_count,new_jacobian_probes=0,new_native=0,controller_optimizations=0,production_edits=0,new_fzp_scans=0,future_state_input=False,all_physical_checks_passed=True,source_pins=PINS,candidate_adopted=False,goal_complete=False))
    print('SMALLSTEP_COMPLETE',forecast_count,'eligible',eligible,flush=True)

if __name__=='__main__':
    try:main()
    except BaseException as error:
        if O.is_dir():save(O/'failure.json',dict(error=repr(error),traceback=traceback.format_exc(),native=0))
        raise
