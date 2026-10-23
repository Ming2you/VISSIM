"""Two bounded regime-inclusive updates; reserve independent validation.

Canonical whole coupled rollouts; no observed future boundary injection.
The production package and earlier fits/forecasts stay read-only.
"""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import copy,datetime,gzip,hashlib,importlib.util,json,math,sys,time,traceback
from pathlib import Path
from refine_approach15 import Refinement

A=Path(__file__).resolve().parent;HERE=A.parent;O=A/'refine15_regime_fit_v3'
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
    baseline_analysis=Path('E:/VISSIM_analysis/20261011_vsl_response349/causal_off2250_analysis_v2/native_analysis')
    closure=read(baseline_analysis/'runtime_closure.json')
    assert closure['all_owned_processes_closed'] and closure['owner_exit_code']==0 and closure['normal_native_end_sec']==2700
    execution=read(baseline_analysis/'hold/execution.json')
    assert execution['native_execution_passed']
    assert execution['checks']['actual_signal_readbacks']['passed'] and execution['checks']['actual_vsl_apply_readbacks']['passed']
    assert not execution['native_lsa_com_coverage_passed'],'Preserve approved LDP substitute and missing LSA'
    cache_receipt=read(HERE/'native_analysis_repaired_20261016/baseline_cache_receipt.json')
    for p,h in cache_receipt['pins'].items():assert sha(p)==h,p
    # Fixed replay has native execution/LDP/readbacks; online OFF has applied sentinels.
    # Qualify exact physical replay without substituting coordination budgets.
    for at in (1650,2250,2850):
        folder=HOLD if at in (1650,2250) else OBS
        for sec in range(at,at+450,150):
            path=folder/f'action_{sec:06d}.json';doc=read(path)
            if folder==OBS:assert Path(str(path)+'.applied').is_file()
            assert all(v==110 for v in doc['vsl'].values())
            if at in (1650,2250):
                other=read(OBS/f'action_{sec:06d}.json')
                assert all(doc.get(k)==other.get(k) for k in ('ramp_metering','vsl','green_times','offsets','inflow_outflow_allocation'))
    initial_audit=read(A/'refine15_update_audit.json');spec=read(SPEC)
    old=initial_audit['parent_parameters'];response=initial_audit['state_response']
    names=['rho_crit','metanet_a_m','tau_sec','nu_ge','nu_lt']
    initial=read(A/'refine15_joint_fit/selection.json')['fitted']['values']
    bounds={v['parameter']:v for v in spec['variables'] if v.get('cell')==15}
    lower=[max(-.5,bounds[n]['lower']/x-1) for n,x in zip(names,initial)]
    upper=[min(.5,bounds[n]['upper']/x-1) for n,x in zip(names,initial)]
    assert all(lo<0<hi for lo,hi in zip(lower,upper))
    read(A/'refine15_calibration/fit.json');read(A/'refine15_clock/assessment.json');read(A/'refine15_regimes/off110_snapshots.json')
    previous_completion=read(A/'refine15_joint_fit/completion.json')
    for p,h in previous_completion['source_pins'].items():assert sha(p)==h,p
    prior=ROOT/'diagnostics/repin_v3c3_review_20261001/aggregate_recovery247'
    review=read(prior/'verification.json');assert review['status']=='PASS' and review['forecasts']==0
    for p in [Path(__file__),A/'refine_approach15.py',CONFIG,VERIFY,ROOT/'evaluation/controllers/freeway_fd.py',ROOT/'evaluation/controllers/area_freeway_accounting.py',ROOT/'evaluation/controllers/multirate_freeway.py']:
        PINS[str(p)]=sha(p)
    O.mkdir()
    protocol=dict(hypothesis='Transferred FD and dynamic coefficients jointly misrepresent the refined transient; identify a finite local correction from autonomous baseline trajectories, not one-step population changes.',
        train_start_sec=[1650,2250,2850],train_end_sec=[2100,2700,3300],evaluation_reserved=['seed67','seed71'],horizon_sec=450,
        train_controls='1650/2250 use exact hold replay actions including their recorded NP/NUF caps;2850 uses completed original OFF actions. Applied physical commands match across the common replay prefix, later coordination-cap metadata does not.2250 is now development/training. All90 outcomes and seeds67/71 excluded from fitting.',
        objective='Equalized native stock /10veh and speed /20kmh residuals at150/300/450 over cells14,15a/b/c,16,17,18. Parameter step regularizer0.1; controller Omega TTT objective unchanged.',
        parameters=names,initial=initial,relative_lower=lower,relative_upper=upper,historical_bounds=str(SPEC),
        fixed='v_free, kappa, remaining cells, geometry, VSL law, city/ramp physics, source/demand; FW5/U10,internalcap0.625,terminalOFF,Omega701',
        optimizer='At most two measured bounded regularized Gauss-Newton updates. Relative0.05 forward Jacobian; no grid, line-search or restart. Stop after a non-improving nonlinear step. Reuse two previous identical trajectories.',
        budgets=dict(max_new_training450=37,max_development_response450=1,max_new_forecasts=38,max_updates=2,native=0,SDMPC_optimizations=0),
        train_gate='Keep lowest measured nonlinear training loss. Improvement>=1percent and no regime stock/speed RMSE increase>10percent. If passed, one90 response forecast at2250 is development diagnostic only. Frozen independent67/71 validation and AD/NP/NUF remain required.',
        reporting='Best measured bounded update, not converged calibration.2250 is no longer held-out. Seed67/71 outcomes were previously inspected during model development, but no data from them enters this fit. Report this limit; no blind-test claim.',
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
        for p in (CONFIG,VERIFY,OBS/f'state_{at:06d}.json'):PINS[str(p)]=sha(p)
        # Qualified old prefix is checked here at the actual calibration starts.
        if at in (1650,2250):
            assert read(OBS/f'state_{at:06d}.json')['vehicle_records']==read(HOLD/f'state_{at:06d}.json')['vehicle_records']
            previous=read(A/f'refine15_joint_fit/capture_{at}/isolated_capture.json')['initial_refinement']
            assert temp['state']._refine15==previous
        actions=[]
        for sec in (at,at+150,at+300):
            path=(HOLD if at in (1650,2250) else OBS)/f'action_{sec:06d}.json';PINS[str(path)]=sha(path)
            if at==2850:assert Path(str(path)+'.applied').is_file(),str(path)
            action=seq.first_action(adapter.control_from_json(path,temp['cfg'],ControlAction))
            assert all(float(x)==110 for x in action.vsl.values())
            if at in (1650,2250):
                prior=seq.first_action(adapter.control_from_json(OBS/f'action_{sec:06d}.json',temp['cfg'],ControlAction))
                for field in ('ramp_metering','vsl','green_times','offsets','inflow_outflow_allocation'):
                    assert getattr(action,field)==getattr(prior,field),(at,sec,field)
            signals.validate_writer(action,temp['cfg'],adapter.load_signal_group_actuation_plan(),'experiment')
            actions.append(action)
        temp['actions']=actions;captured[at]['actions']=actions
        save(O/f'capture_{at}'/'isolated_capture.json',dict(at=at,optimizer_calls=0,forecasts=0,initial_refinement=captured[at]['state']._refine15))
    def truth(at):
        s=captured[at]['state'];rt=s.lane_freeway_runtime.configs['FW_E'].network.offramp_route_inventory;bs=rt['bounds']['FW_E'];result=[]
        for sec in (at+150,at+300,at+450):
            raw=read((HOLD if at in (1650,2250) else OBS)/f'state_{sec:06d}.json');assert raw['sim_sec']==sec and raw['vehicle_records']['complete']
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
        assert forecasts_count<38
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
    cache={};records=[];point_cache={}
    try:
        for at in (1650,2250,2850):capture(at)
        actual={at:truth(at) for at in (1650,2250,2850)};save(O/'training_truth.json',actual)
        prior={1650:read(A/'refine15_joint_fit/fitted_1650.json'),2250:read(A/'refine15_joint_fit/validation_hold.json')}
        for at,p in prior.items():
            assert p['values']==list(initial) and p['physical']
        def evaluate(z,label):
            key=tuple(float(x) for x in z)
            if key in cache:return cache[key]
            assert len(records)<13
            values=initial*(1+z);rows=[];reused=0
            for at in (1650,2250,2850):
                if label=='baseline' and at in prior:
                    row=prior[at];reused+=1
                else:row=predict(at,values,f'{label}_{at}')
                rows.append(row)
            ns=[];vs=[];regimes={}
            for row in rows:
                n=[];v=[]
                for p,q in zip(row['frames'],actual[row['start']]):
                    n.extend(a-b for a,b in zip(p['n'],q['n']));v.extend(a-b for a,b in zip(p['speed'],q['speed']))
                ns.extend(n);vs.extend(v)
                regimes[str(row['start'])]=dict(stock_rmse=float(np.sqrt(np.mean(np.square(n)))),speed_rmse=float(np.sqrt(np.mean(np.square(v)))))
            residual=np.r_[np.array(ns)/10/math.sqrt(len(ns)),np.array(vs)/20/math.sqrt(len(vs))]
            record=dict(label=label,relative=list(map(float,z)),values=list(map(float,values)),data_loss=float(residual@residual),stock_rmse=float(np.sqrt(np.mean(np.square(ns)))),speed_rmse=float(np.sqrt(np.mean(np.square(vs)))),regimes=regimes,reused=reused)
            records.append(record);cache[key]=residual;point_cache[key]=rows;save(O/'training_evaluations.json',records)
            return residual
        z=np.zeros(5);current=evaluate(z,'baseline');best=records[-1];base=records[0];updates=[]
        for iteration in (1,2):
            columns=[]
            for i in range(5):
                probe=z.copy();h=min(.05,upper[i]-z[i])
                if h<.01:h=-min(.05,z[i]-lower[i])
                assert abs(h)>.001
                probe[i]+=h;columns.append((evaluate(probe,f'probe{iteration}_{names[i]}')-current)/h)
            J=np.column_stack(columns);singular=np.linalg.svd(J,compute_uv=False)
            # Trust region applies to each relative update and fixed historical bounds.
            lo=np.maximum(np.array(lower)-z,-.25);hi=np.minimum(np.array(upper)-z,.25)
            step=lsq_linear(np.vstack([J,.1*np.eye(5)]),np.r_[-current,-.1*z],bounds=(lo,hi),tol=1e-10,max_iter=100)
            assert step.success
            proposed=z+step.x;rnew=evaluate(proposed,f'fitted{iteration}');candidate=records[-1]
            improved=candidate['data_loss']<best['data_loss']
            updates.append(dict(iteration=iteration,measured_improvement=improved,data_jacobian_singular_values=singular.tolist(),active_bounds=step.active_mask.tolist(),candidate=candidate))
            save(O/'updates.json',updates)
            if not improved:break
            z=proposed;current=rnew;best=candidate
        eligible=best['data_loss']<=.99*base['data_loss'] and all(best['regimes'][str(at)][key]<=1.1*base['regimes'][str(at)][key] for at in (1650,2250,2850) for key in ('stock_rmse','speed_rmse'))
        selection=dict(eligible=bool(eligible),baseline=base,fitted=best,updates=updates,converged_nonlinear=False,method='At most two measured bounded Gauss-Newton updates',frozen_before_development_response=True,independent_evaluation_reserved=[67,71])
        save(O/'selection.json',selection)
        if eligible:
            key=tuple(float(x) for x in z);hold=next(p for p in point_cache[key] if p['start']==2250)
            selected=predict(2250,initial*(1+z),'development_selected',{'FW_E__seg10':90,'FW_E__seg13':90},full=True)
            save(O/'development_response.json',dict(hold=hold,selected=selected,scope='Hold2250 entered calibration;90 outcomes did not. Development response only, not held-out validation.'))
        for p,h in PINS.items():assert sha(p)==h,p
        save(O/'completion.json',dict(status='complete_pending_assessment',forecasts=forecasts_count,training_vectors=len(records),updates=len(updates),reused_forecasts=2,SDMPC_optimizations=0,native=0,coefficient_grid=0,production_edits=0,source_pins=PINS,max_route_balance=refine.max_balance,max_vsl_balance=refine.max_cohort,goal_complete=False,candidate_adopted=False))
        print('REGIME_FIT_COMPLETE',json.dumps(selection),flush=True)
    finally:
        refine.restore();multirate_freeway.time_limit=old_limit

if __name__=='__main__':
    try:main()
    except BaseException as error:
        if O.is_dir():save(O/'failure.json',dict(error=repr(error),traceback=traceback.format_exc(),native=0))
        raise
