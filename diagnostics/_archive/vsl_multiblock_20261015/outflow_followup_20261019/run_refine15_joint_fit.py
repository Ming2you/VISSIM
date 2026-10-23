"""One bounded trajectory-calibration step, followed by frozen validation.

Canonical whole coupled rollouts; no observed future boundary injection.
The production package and earlier fits/forecasts stay read-only.
"""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import copy,datetime,gzip,hashlib,importlib.util,json,math,sys,time,traceback
from pathlib import Path
from refine_approach15 import Refinement

A=Path(__file__).resolve().parent;HERE=A.parent;O=A/'refine15_joint_fit'
ROOT=Path('D:/VISSIM_packages/vsl_multizone355_20261015')
CONFIG=ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/vsl_schedules_20261015/config.json'
VERIFY=ROOT/'diagnostics/repin_v3c3_review_20261001/urban260/verify.py'
HOLD=Path('E:/VISSIM_runs/20261011_vsl349_off2250_s29/hold/decisions_sdmpc31_g_2250_hold_s29')
OBS=Path('E:/VISSIM_runs/20261008_coupling268_off_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
SPEC=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/cellwise_calibration/parameter_spec.json'
PINS={}
def read(p):
    p=Path(p);b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    assert not O.exists() and not (A/'STOP').exists()
    initial_audit=read(A/'refine15_update_audit.json');spec=read(SPEC)
    old=initial_audit['parent_parameters'];response=initial_audit['state_response']
    names=['rho_crit','metanet_a_m','tau_sec','nu_ge','nu_lt']
    initial=[old['rho_crit'],old['metanet_a_m'],response['relaxation']['acceleration_sec'],response['anticipation']['downstream_ge_local'],response['anticipation']['downstream_lt_local']]
    bounds={v['parameter']:v for v in spec['variables'] if v.get('cell')==15}
    lower=[max(-.5,bounds[n]['lower']/x-1) for n,x in zip(names,initial)]
    upper=[min(.5,bounds[n]['upper']/x-1) for n,x in zip(names,initial)]
    assert all(lo<0<hi for lo,hi in zip(lower,upper))
    read(A/'refine15_calibration/fit.json');read(A/'refine15_clock/assessment.json')
    prior=ROOT/'diagnostics/repin_v3c3_review_20261001/aggregate_recovery247'
    review=read(prior/'verification.json');assert review['status']=='PASS' and review['forecasts']==0
    for p in [Path(__file__),A/'refine_approach15.py',CONFIG,VERIFY,ROOT/'evaluation/controllers/freeway_fd.py',ROOT/'evaluation/controllers/area_freeway_accounting.py',ROOT/'evaluation/controllers/multirate_freeway.py']:
        PINS[str(p)]=sha(p)
    O.mkdir()
    protocol=dict(hypothesis='Transferred FD and dynamic coefficients jointly misrepresent the refined transient; identify a finite local correction from autonomous baseline trajectories, not one-step population changes.',
        train_start_sec=[1200,1650],train_end_sec=[1650,2100],validation_start_sec=2250,horizon_sec=450,
        train_controls='Existing hold110 replay city/RM commands, exact original prefix. No90 samples or response signs in the fit.',
        objective='Equalized native stock /10veh and speed /20kmh residuals at150/300/450 over cells14,15a/b/c,16,17,18. Parameter step regularizer0.1; controller Omega TTT objective unchanged.',
        parameters=names,initial=initial,relative_lower=lower,relative_upper=upper,historical_bounds=str(SPEC),
        fixed='v_free, kappa, remaining cells, geometry, VSL law, city/ramp physics, source/demand; FW5/U10,internalcap0.625,terminalOFF,Omega701',
        optimizer='One explicit0.05 relative forward Jacobian; one bounded regularized Gauss-Newton step. No coefficient grid or iterative restarts.',
        budgets=dict(training_vectors=7,training450_forecasts=14,validation450_forecasts=2,native=0,SDMPC_optimizations=0),
        train_gate='Actual nonlinear residual improves at least1percent; separate stock and speed RMSE no more than110percent of baseline; physical/tag invariants pass. Only then capture2250 and run hold/selected once with frozen values.',
        reporting='Best measured bounded update, not a converged optimum. Bound contact and data Jacobian singular values must be reported. Validation cannot update coefficients. A positive result still requires independent seed67/71 and AD/NP/NUF qualification.',
        prior_review='Aggregate247 distinguished instantaneous acceleration from population mean changes and nonlinear averaging atcells21-25; it did not calibrate the current refinedcell15. Existing proof reused, not repeated.',
        source_pins=dict(PINS))
    save(O/'protocol.json',protocol)
    save(O/'launch.json',dict(pid=os.getpid(),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=sys.argv))
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    os.environ['NUMSIM_REPO_ROOT']=str(ROOT/'vendor/NumSim-mine')
    import numpy as np
    from scipy.optimize import lsq_linear
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,head_service_resources,vsl_exposure_history,physical_ramp_branches as ramps,signal_actuation_contract as signals,sdmpc_pfo,sdmpc,sdmpc_sequence as seq,multirate_freeway,offramp_routing as route
    from evaluation.controllers.control_hold import fixed_vsl_values
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts
    from src.controllers import rollout_endpoint as endpoint
    from src.models.state import ControlAction
    initial=np.array(initial)
    sdmpc.load_prices=lambda *a,**k:(np.zeros(2),dict(source='offline_baseline_calibration_cold_prices',committed=False))
    refine=Refinement(O);old_limit=multirate_freeway.time_limit
    multirate_freeway.time_limit=lambda runtime,state:min(.625,old_limit(runtime,state))
    captured={};forecasts_count=0
    def capture(at):
        assert at not in captured
        original={name:getattr(module,name) for module,name in [(adapter,'demand_from_state'),(ramps,'configure_operating_bounds'),(head_service_resources,'observe'),(vsl_exposure_history,'initialize'),(signals,'_validate_native_vector'),(sdmpc_pfo,'solve')]}
        temp={}
        def bound(state,cfg,reference):
            value=original['configure_operating_bounds'](state,cfg,reference);temp.update(state=state,cfg=cfg);return value
        def forecast(*a,**k):
            value=original['demand_from_state'](*a,**k);temp['forecast']=value;return value
        ramps.configure_operating_bounds=bound;adapter.demand_from_state=forecast
        sys.argv=[str(VERIFY),'--at',str(at),'--out',str(O/f'capture_{at}'),'--tuning',str(CONFIG),'--decisions',str(OBS),'--full-selection']
        loader=importlib.util.spec_from_file_location(f'joint_fit_capture_{at}',VERIFY)
        v=importlib.util.module_from_spec(loader);loader.loader.exec_module(v)
        def stop(*a,**k):
            state,cfg=temp['state'],temp['cfg'];assert state.time_sec==at and hasattr(state,'_refine15')
            assert (cfg.simulation.T_f_sec,cfg.simulation.T_u_sec,cfg.mpc.horizon_steps)==(5,10,3)
            captured[at]=temp.copy();raise v.Done()
        sdmpc_pfo.solve=stop
        try:v.main()
        finally:
            for module,name in [(adapter,'demand_from_state'),(ramps,'configure_operating_bounds'),(head_service_resources,'observe'),(vsl_exposure_history,'initialize'),(signals,'_validate_native_vector'),(sdmpc_pfo,'solve')]:setattr(module,name,original[name])
        assert at in captured
        for p in (CONFIG,VERIFY,OBS/f'state_{at:06d}.json',HOLD/f'state_{at:06d}.json'):PINS[str(p)]=sha(p)
        # Qualified old prefix is checked here at the actual calibration starts.
        assert read(OBS/f'state_{at:06d}.json')['vehicle_records']==read(HOLD/f'state_{at:06d}.json')['vehicle_records']
        actions=[]
        for sec in (at,at+150,at+300):
            path=HOLD/f'action_{sec:06d}.json';PINS[str(path)]=sha(path)
            action=seq.first_action(adapter.control_from_json(path,temp['cfg'],ControlAction))
            assert all(float(x)==110 for x in action.vsl.values())
            signals.validate_writer(action,temp['cfg'],adapter.load_signal_group_actuation_plan(),'experiment')
            actions.append(action)
        temp['actions']=actions;captured[at]['actions']=actions
        save(O/f'capture_{at}'/'isolated_capture.json',dict(at=at,optimizer_calls=0,forecasts=0,initial_refinement=captured[at]['state']._refine15))
    def truth(at):
        s=captured[at]['state'];rt=s.lane_freeway_runtime.configs['FW_E'].network.offramp_route_inventory;bs=rt['bounds']['FW_E'];result=[]
        for sec in (at+150,at+300,at+450):
            raw=read(HOLD/f'state_{sec:06d}.json');assert raw['sim_sec']==sec and raw['vehicle_records']['complete']
            groups=[[] for _ in range(7)]
            for v in raw['vehicle_records']['records']:
                if str(v['link_no']) not in rt['physical']:continue
                road,pos,i=route._position(rt,v['link_no'],v['position_m'])
                if road!='FW_E' or not 14<=i<=18:continue
                j=0 if i==14 else (min(2,int(3*(pos-bs[15])/(bs[16]-bs[15])))+1 if i==15 else i-12)
                groups[j].append(v['speed_kph'])
            assert all(groups)
            result.append(dict(n=[len(g) for g in groups],speed=[sum(g)/len(g) for g in groups]))
        return result
    def predict(at,values,label,zones=None,full=False):
        nonlocal forecasts_count
        assert forecasts_count<16
        forecasts_count+=1;save(O/'progress.json',dict(stage='predicting',label=label,start=at,forecast_entered=forecasts_count))
        state,cfg=copy.deepcopy((captured[at]['state'],captured[at]['cfg']))
        for net in (cfg.network,state.lane_freeway_runtime.configs['FW_E'].network):
            p=net.freeway_segment_params['FW_E'][15]
            p.update(rho_crit=float(values[0]),metanet_a_m=float(values[1]))
            if not hasattr(net,'freeway_state_response'):net.freeway_state_response={}
            spec=net.freeway_state_response.setdefault('FW_E',{})
            spec.setdefault('cell_overrides',{})['15']=dict(relaxation=dict(acceleration_sec=float(values[2]),deceleration_sec=float(values[2])),anticipation=dict(downstream_ge_local=float(values[3]),downstream_lt_local=float(values[4])))
        actions=copy.deepcopy(captured[at]['actions'])
        for i,a in enumerate(actions):
            a.vsl=fixed_vsl_values(a.vsl,dict(start_sec=at,base_kmh=110,zone_kmh=zones or {}),cfg.network.freeway_vsl_zone_heads,at+i*150)
            signals.validate_writer(a,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
        action=seq.pack(actions);refine.trace=[];start=time.perf_counter()
        with seq.prediction_scope(action,cfg,at,3) as visits:
            point=endpoint.evaluate_price_point(state,action,copy.deepcopy(captured[at]['forecast'][:3]),(),endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
        assert visits==[0,1,2] and not point.aborted and len(point.states)==3 and not refine.context
        response=point.control_area_response
        assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
        frames=[];snapshots=[]
        for st in (state,*point.states):
            get_ledger(st).assert_stocks(model_inventory(st,cfg))
            counts=continuity_vehicle_counts(st,cfg);d=st._refine15
            n=[counts['FW_E'][14],*[sum(r.values()) for r in d['routes']],*counts['FW_E'][16:19]]
            speed=[st.freeway_speed['FW_E'][14],*d['speed'],*st.freeway_speed['FW_E'][16:19]]
            frames.append(dict(n=n,speed=speed));snapshots.append(dict(time_sec=st.time_sec,n=counts,speed=st.freeway_speed))
        through=[sum(x['accepted_total_veh'] for x in response['resource_allocations'] if x['kind']=='freeway_mainline_sending' and x['resource']=='FW_E:cell:18' and x['end_sec']<=at+t+1e-8) for t in (150,300,450)]
        result=dict(label=label,start=at,values=list(map(float,values)),frames=frames[1:],snapshots=snapshots,throughflow=through,ttt=point.ttt,seconds=time.perf_counter()-start,physical=True)
        save(O/(label+'.json'),result)
        if full:
            with gzip.open(O/(label+'_response.json.gz'),'wt',encoding='utf8') as f:json.dump(response,f,allow_nan=False)
            save(O/(label+'_subcells.json'),refine.trace)
        print('TRAJECTORY',label,'forecast',forecasts_count,'ttt',point.ttt,'sec',result['seconds'],flush=True)
        return result
    cache={};records=[]
    try:
        capture(1200);capture(1650)
        actual={at:truth(at) for at in (1200,1650)};save(O/'training_truth.json',actual)
        def evaluate(z,label):
            key=tuple(float(x) for x in z)
            if key in cache:return cache[key]
            assert len(records)<7
            values=initial*(1+z);rows=[predict(at,values,f'{label}_{at}') for at in (1200,1650)]
            ns=[];vs=[]
            for row in rows:
                for p,q in zip(row['frames'],actual[row['start']]):
                    ns.extend(a-b for a,b in zip(p['n'],q['n']));vs.extend(a-b for a,b in zip(p['speed'],q['speed']))
            residual=np.r_[np.array(ns)/10/math.sqrt(len(ns)),np.array(vs)/20/math.sqrt(len(vs))]
            record=dict(label=label,relative=list(map(float,z)),values=list(map(float,values)),data_loss=float(residual@residual),stock_rmse=float(np.sqrt(np.mean(np.square(ns)))),speed_rmse=float(np.sqrt(np.mean(np.square(vs)))))
            records.append(record);cache[key]=residual;save(O/'training_evaluations.json',records)
            return residual
        z0=np.zeros(5);r0=evaluate(z0,'baseline');columns=[]
        for i in range(5):
            z=z0.copy();z[i]=.05;columns.append((evaluate(z,f'probe_{names[i]}')-r0)/.05)
        J=np.column_stack(columns);singular=np.linalg.svd(J,compute_uv=False)
        step=lsq_linear(np.vstack([J,.1*np.eye(5)]),np.r_[-r0,np.zeros(5)],bounds=(lower,upper),tol=1e-10,max_iter=100)
        assert step.success
        z=step.x;evaluate(z,'fitted');base,chosen=records[0],records[-1]
        eligible=chosen['data_loss']<=.99*base['data_loss'] and chosen['stock_rmse']<=1.1*base['stock_rmse'] and chosen['speed_rmse']<=1.1*base['speed_rmse']
        selection=dict(eligible=bool(eligible),baseline=base,fitted=chosen,data_jacobian_singular_values=singular.tolist(),active_bounds=step.active_mask.tolist(),converged_nonlinear=False,method='One measured bounded Gauss-Newton update; no nonlinear convergence claim',frozen_before_validation=True)
        save(O/'selection.json',selection)
        validation=[]
        if eligible:
            capture(2250);values=initial*(1+z)
            validation=[predict(2250,values,'validation_hold',full=True),predict(2250,values,'validation_selected',{'FW_E__seg10':90,'FW_E__seg13':90},full=True)]
            save(O/'validation_truth.json',truth(2250))
            save(O/'validation.json',validation)
        for p,h in PINS.items():assert sha(p)==h,p
        save(O/'completion.json',dict(status='complete_pending_assessment',forecasts=forecasts_count,training_vectors=len(records),fits=1,SDMPC_optimizations=0,native=0,coefficient_grid=0,production_edits=0,source_pins=PINS,
            max_route_balance=refine.max_balance,max_vsl_balance=refine.max_cohort,goal_complete=False,candidate_adopted=False))
        print('JOINT_FIT_COMPLETE',json.dumps(selection),flush=True)
    finally:
        refine.restore();multirate_freeway.time_limit=old_limit

if __name__=='__main__':
    try:main()
    except BaseException as error:
        if O.is_dir():save(O/'failure.json',dict(error=repr(error),traceback=traceback.format_exc(),native=0))
        raise
