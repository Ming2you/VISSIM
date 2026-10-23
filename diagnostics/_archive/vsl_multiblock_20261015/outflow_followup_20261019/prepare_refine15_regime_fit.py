"""Prepare a finite regime-inclusive fit from the reviewed coupled harness."""
from pathlib import Path
import hashlib
A=Path(__file__).resolve().parent
source=A/'run_refine15_joint_fit.py';target=A/'run_refine15_regime_fit.py'
assert not target.exists()
s=source.read_text(encoding='utf8')
assert hashlib.sha256(source.read_bytes()).hexdigest()=='374c0c7654c352d8219adc186a75a1543ff02ff056983ea6bc6cb6d64f3a2419'
def replace(old,new):
    global s
    assert s.count(old)==1,(old[:80],s.count(old))
    s=s.replace(old,new)
replace("O=A/'refine15_joint_fit'","O=A/'refine15_regime_fit'")
replace("initial=[old['rho_crit'],old['metanet_a_m'],response['relaxation']['acceleration_sec'],response['anticipation']['downstream_ge_local'],response['anticipation']['downstream_lt_local']]", "initial=read(A/'refine15_joint_fit/selection.json')['fitted']['values']")
replace("train_start_sec=[1200,1650],train_end_sec=[1650,2100],validation_start_sec=2250,horizon_sec=450,", "train_start_sec=[1650,2250,2850],train_end_sec=[2100,2700,3300],evaluation_reserved=['seed67','seed71'],horizon_sec=450,")
replace("train_controls='Existing hold110 replay city/RM commands, exact original prefix. No90 samples or response signs in the fit.',", "train_controls='Existing completed OFF110 replay city/RM.1650 free flow,2250 breakdown,2850 recovery. Previous2250 holdout is now explicitly development/training. All90 outcomes and seeds67/71 excluded from fitting.',")
replace("optimizer='One explicit0.05 relative forward Jacobian; one bounded regularized Gauss-Newton step. No coefficient grid or iterative restarts.',", "optimizer='At most two measured bounded regularized Gauss-Newton updates. Relative0.05 forward Jacobian; no grid, line-search or restart. Stop after a non-improving nonlinear step. Reuse two previous identical trajectories.',")
replace("budgets=dict(training_vectors=7,training450_forecasts=14,validation450_forecasts=2,native=0,SDMPC_optimizations=0),", "budgets=dict(max_new_training450=37,max_development_response450=1,max_new_forecasts=38,max_updates=2,native=0,SDMPC_optimizations=0),")
replace("train_gate='Actual nonlinear residual improves at least1percent; separate stock and speed RMSE no more than110percent of baseline; physical/tag invariants pass. Only then capture2250 and run hold/selected once with frozen values.',", "train_gate='Keep lowest measured nonlinear training loss. Improvement>=1percent and no regime stock/speed RMSE increase>10percent. If passed, one90 response forecast at2250 is development diagnostic only. Frozen independent67/71 validation and AD/NP/NUF remain required.',")
replace("reporting='Best measured bounded update, not a converged optimum. Bound contact and data Jacobian singular values must be reported. Validation cannot update coefficients. A positive result still requires independent seed67/71 and AD/NP/NUF qualification.',", "reporting='Best measured bounded update, not converged calibration.2250 is no longer held-out. Seed67/71 outcomes were previously inspected during model development, but no data from them enters this fit. Report this limit; no blind-test claim.',")
replace("read(A/'refine15_calibration/fit.json');read(A/'refine15_clock/assessment.json')", "read(A/'refine15_calibration/fit.json');read(A/'refine15_clock/assessment.json');read(A/'refine15_regimes/off110_snapshots.json');read(A/'refine15_joint_fit/completion.json')")
replace("if not hasattr(net,'freeway_state_response'):net.freeway_state_response={}", "if not hasattr(net,'freeway_state_response'):net.freeway_state_response={}")
# The no-op replacement above pins the inherited effective coefficient path.
replace("for p in (CONFIG,VERIFY,OBS/f'state_{at:06d}.json',HOLD/f'state_{at:06d}.json'):PINS[str(p)]=sha(p)", "for p in (CONFIG,VERIFY,OBS/f'state_{at:06d}.json'):PINS[str(p)]=sha(p)")
replace("assert read(OBS/f'state_{at:06d}.json')['vehicle_records']==read(HOLD/f'state_{at:06d}.json')['vehicle_records']", "if at in (1650,2250):\n            assert read(OBS/f'state_{at:06d}.json')['vehicle_records']==read(HOLD/f'state_{at:06d}.json')['vehicle_records']\n            previous=read(A/f'refine15_joint_fit/capture_{at}/isolated_capture.json')['initial_refinement']\n            assert temp['state']._refine15==previous")
replace("path=HOLD/f'action_{sec:06d}.json';PINS[str(path)]=sha(path)", "path=OBS/f'action_{sec:06d}.json';PINS[str(path)]=sha(path)\n            assert Path(str(path)+'.applied').is_file(),str(path)")
replace("assert all(float(x)==110 for x in action.vsl.values())", "assert all(float(x)==110 for x in action.vsl.values())\n            if at in (1650,2250):\n                prior=seq.first_action(adapter.control_from_json(HOLD/f'action_{sec:06d}.json',temp['cfg'],ControlAction))\n                for field in ('N_P_star','N_UF_star','ramp_metering','vsl','green_times','offsets','inflow_outflow_allocation'):\n                    assert getattr(action,field)==getattr(prior,field),(at,sec,field)")
replace("raw=read(HOLD/f'state_{sec:06d}.json');assert raw['sim_sec']==sec", "raw=read(OBS/f'state_{sec:06d}.json');assert raw['sim_sec']==sec")
replace("assert forecasts_count<16", "assert forecasts_count<38")
start=s.index('    cache={};records=[]')
end=s.index('    finally:\n        refine.restore()',start)
s=s[:start]+'''    cache={};records=[];point_cache={}
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
''' +s[end:]
compile(s,str(target),'exec')
target.write_text(s,encoding='utf8')
print(target)
