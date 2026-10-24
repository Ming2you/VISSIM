"""Bounded paired-response calibration using the existing conserved runner.

Training uses NC and VSL 2400-2700 only. Late time and RM/both are checks.
All of these trajectories are development data, not independent validation.
"""
import copy,json,math,subprocess,sys,time
from pathlib import Path
import numpy as np
import full_calibration as f
from prepare import save,table
c=f.c;B=f.B;ROOT=f.ROOT;K=f.K;O=B/'vsl_response_v1'
KEYS=('tau_acc','tau_dec','nu_high','nu_low','delta_merge')
LABELS=('hadi_fd_cap_r2','wang_command_r2')
CELLS=list(range(30)) # unobserved terminal crossing excluded


def observed(arm):
    path=c.O/'observed_none.npz' if arm=='none' else B/'vsl_response_v1/observed_vsl.npz'
    with np.load(path) as z:return {k:z[k] for k in z.files}


def response_metrics(pred,lo=0,hi=10):
    obs={a:observed(a) for a in ('none','vsl')};errors=[[],[],[]]
    for i in CELLS:
        ng=len(c.WIDTHS[i]);speeds={}
        for a in ('none','vsl'):
            speeds[a]=[]
            for source in (obs,pred):
                n=source[a]['n'][lo:hi,i,:ng];m=source[a]['mom'][lo:hi,i,:ng]
                speeds[a].append(np.divide(m,n,out=np.zeros_like(n),where=n>0))
        mask=(obs['none']['n'][lo:hi,i,:ng]>=1)&(obs['vsl']['n'][lo:hi,i,:ng]>=1)
        errors[0].extend(((speeds['vsl'][1]-speeds['none'][1])-(speeds['vsl'][0]-speeds['none'][0]))[mask])
        for dest,key,scale in ((errors[1],'n',1),(errors[2],'q',120)):
            sl=(slice(lo,hi),i,slice(ng)) if key=='n' else (slice(lo,hi),i)
            dest.extend(((pred['vsl'][key][sl]-pred['none'][key][sl]-(obs['vsl'][key][sl]-obs['none'][key][sl]))*scale).ravel())
    rmse=[float(np.sqrt(np.mean(np.square(x)))) for x in errors]
    # Observation-based fixed masks prevent an optimizer from hiding errors
    # by emptying a modeled cell. Scales are error tolerances, not MPC rewards.
    residual=np.concatenate([np.asarray(x)/s/math.sqrt(len(x)) for x,s in zip(errors,(10,2,200))])
    return residual,dict(response_loss=float(residual@residual),delta_speed_rmse=rmse[0],delta_group_n_rmse=rmse[1],delta_boundary_q_rmse=rmse[2])


def execute(spec):
    path=O/(spec['name']+'.json');score=O/(spec['name']+'_score.json')
    if score.exists():
        result=c.load(score);assert result['spec']==spec;return result
    receipt_path=O/spec['name']/'refined_guard1_receipt.json'
    if receipt_path.exists():
        receipt=c.load(receipt_path)
        assert receipt['completed'] and receipt['fit']==spec and c.load(path)==spec
        assert receipt['runner_sha256']==c.sha(B/'run.py') and receipt['forecasts']==len(spec['arms'])
        result=dict(name=spec['name'],spec=spec,exit_code=0,seconds=None,reused_completed_predictions=True)
    else:
        save(path,spec);started=time.perf_counter()
        with (O/(spec['name']+'_process.log')).open('x',encoding='utf-8') as log:
            proc=subprocess.run([sys.executable,'-B','-X','utf8',str(B/'run.py'),'refined_guard1',str(path)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        result=dict(name=spec['name'],spec=spec,exit_code=proc.returncode,seconds=time.perf_counter()-started)
    if result['exit_code']:
        save(score,result);raise RuntimeError('Forecast failed; see '+str(score))
    pred={a:f.load_prediction(O/spec['name']/f'refined_guard1_{a}.json') for a in spec['arms']}
    checks={a:c.screen(p) for a,p in pred.items()};assert all(x['passed'] for x in checks.values()),checks
    for a,p in pred.items():
        reference=f.load_prediction(f.O/('fc_'+spec['base_label']+'_actions')/f'refined_guard1_{a}.json')
        for key in ('cells','flows'):
            assert [r for r in p[key] if r['road']=='FW_W']==[r for r in reference[key] if r['road']=='FW_W']
        audit=next(x for x in p['diagnostics']['roads'] if x['road']=='FW_E')['hadiuzzaman_audit']
        assert audit['max_budget_violation_veh']<1e-7
    entries=c.load(O/spec['name']/'effective_config.json');assert [x['arm'] for x in entries]==spec['arms']
    for e in entries:
        assert e['scalar']==spec['physical_coefficients'] and e['state_response']['FW_E']==spec['state_response']
        assert e['receiving']['FW_E']==spec['hadiuzzaman'] and e['port_response']['FW_E']==spec['port_response']
        for row in e['rows']:
            for key in ('v_free','rho_crit','rho_max','metanet_a_m','metanet_kappa_veh_km_lane'):
                assert row[key]==spec['physical_coefficients'][key]
        if 'vsl_fd_response' in spec:assert e['vsl_fd_response']['FW_E']==spec['vsl_fd_response']
    if 'vsl_fd_response' in spec:
        for arm in spec['arms']:
            usage=c.load(O/spec['name']/f'vsl_fd_usage_{arm}.json')
            assert all(x['spec']==spec['vsl_fd_response'] for x in usage)
            if arm in ('vsl','both'):assert any(x['calls']>100 and x['command']<x['maximum'] for x in usage)
    if 'diagnostic_vsl_policy' in spec:
        result.update(numerics=checks,west_exact=True,effective_config_exact=True,
            fit_metric_omitted='Different policy is evaluated against its own native result after parameter freezing.')
        save(score,result);print(spec['name'],'policy validation complete',flush=True);return result
    arrays={a:c.predicted(p) for a,p in pred.items() if a in ('none','vsl')}
    rr,metric=response_metrics(arrays);state=f.residual(pred['none'])
    residual=np.concatenate((state,rr));np.save(O/(spec['name']+'_residual.npy'),residual)
    result.update(numerics=checks,train=c.score(pred['none']),response=metric,objective=float(residual@residual),west_exact=True,effective_config_exact=True)
    save(score,result);print(spec['name'],result['objective'],metric,flush=True);return result


def specification(label,name,values,arms=('none','vsl')):
    family,law=('hadi','fd_cap') if label.startswith('hadi') else ('wang','command')
    spec=f.specification(name,values,family,law,nc=False)
    spec.update(output_group=O.name,arms=list(arms),base_label=label,
        control_response_fit=dict(training=[2400,2700],commands=['none','vsl'],independent_validation=False,protocol='vsl_response_v1/protocol.json'))
    return spec


def prepare():
    assert not (O/'protocol.json').exists()
    sources=[B/'run.py',B/'calibrate.py',__file__,B/'geometry_200_branch_guard.json',B/'guard_initial_groups.json',c.O/'observed_none.npz']
    from pathlib import Path
    save(O/'protocol.json',dict(initial_s=2400,train=[2400,2700],late_check=[2700,2850],seed=23,
        controls_used_for_training=['none','vsl'],control_checks=['rm_ramp','both'],independent_validation=False,
        families=list(LABELS),parameters=list(KEYS),bounds={k:f.BOUNDS[k][:2] for k in KEYS},
        objective='NC original state loss + paired VSL-minus-NC speed/10, N/2, q/200 squared RMSE. All east nonterminal cells; same fixed observations mask.',
        selection='Lowest training objective with numerical pass and NC loss <=1.10 times its prefit value; at most 20 paired candidates per family.',
        fixed='Geometry, demand, route, all other coefficients incl capacity/drop/jam, actuator coverage, initial state, waiting cost and future input forecast.',
        qualified_only_if='Held-back late/control response and component gain direction improve; no production adoption or independent validation in this fit.',
        maximum_pairs_per_family=20,no_new_native_in_this_fit=True,production_adopted=False,
        source_pins={str(Path(p).resolve().relative_to(ROOT)):c.sha(Path(p)) for p in sources}))
    c.observe('vsl_s23',O)
    print('observations complete',flush=True)


def fit(label):
    sys.path.insert(0,str(ROOT/'tmp/calibration_dependencies'));from scipy.optimize import least_squares
    initial=c.load(f.O/(label+'_selected.json'))['selected']['spec']['calibration_values']
    low=np.array([f.BOUNDS[k][0] for k in KEYS]);span=np.array([f.BOUNDS[k][1]-f.BOUNDS[k][0] for k in KEYS])
    x0=(np.array([initial[k] for k in KEYS])-low)/span
    history=[];seen={};sens=[];dimension=None
    class Budget(Exception):pass
    def objective(x):
        nonlocal dimension
        key=tuple(x)
        if key in seen:return seen[key]
        if len(history)>=20:raise Budget()
        values={**initial,**dict(zip(KEYS,(low+span*x).tolist()))}
        spec=specification(label,f'vr_{label}_{len(history):02}',values)
        row=execute(spec);history.append(row)
        r=np.load(O/(spec['name']+'_residual.npy'));dimension=len(r)
        seen[key]=r;save(O/(label+'_history.json'),history);return r
    def jac(x):
        r=objective(x);cols=[];rows=[]
        for j,key in enumerate(KEYS):
            dx=.025 if x[j]+.025<=1 else -.025;z=x.copy();z[j]+=dx
            difference=objective(z)-r;cols.append(difference/dx)
            rows.append(dict(parameter=key,normalized_step=dx,response_norm=float(np.linalg.norm(difference))))
        sens.append(dict(x=x.tolist(),sensitivity=rows));save(O/(label+'_sensitivities.json'),sens)
        return np.stack(cols,axis=1)
    try:
        result=least_squares(objective,x0,jac=jac,bounds=(np.zeros(len(KEYS)),np.ones(len(KEYS))),max_nfev=4,ftol=.01,xtol=.005,gtol=.005,tr_solver='lsmr')
        stop=dict(status=int(result.status),message=result.message,nfev=int(result.nfev),njev=int(result.njev))
    except Budget:stop=dict(status=0,message='20 paired candidate budget exhausted')
    before=history[0]
    for a in ('none','vsl'):
        assert f.load_prediction(O/before['name']/f'refined_guard1_{a}.json')==f.load_prediction(f.O/('fc_'+label+'_actions')/f'refined_guard1_{a}.json'),'Pair subset changed forecast'
    good=[r for r in history if r['train']['objective']<=1.10*before['train']['objective']]
    selected=min(good,key=lambda r:r['objective'])
    save(O/(label+'_selected.json'),dict(selected=selected,baseline=before,optimizer=stop,default_pair_exact=True))
    print('FROZEN',label,selected['name'],stop,flush=True)


def validate():
    actual=c.load(B.parent/'response_chain_20260921/qualification.json')['gains'];rows=[];scores=[]
    for label in LABELS:
        selected=c.load(O/(label+'_selected.json'))
        values=selected['selected']['spec']['calibration_values']
        spec=specification(label,'vr_'+label+'_validation',values,f.ARMS);execute(spec)
        result=c.load(K/('segment_resolution_20260921_cal_'+spec['name'])/'result.json')
        for role,folder in [('before',f.O/('fc_'+label+'_actions')),('after',O/spec['name'])]:
            pp={a:f.load_prediction(folder/f'refined_guard1_{a}.json') for a in ('none','vsl')}
            arrays={a:c.predicted(p) for a,p in pp.items()}
            for phase,lo,hi in [('train',0,10),('late',10,15)]:
                _,metric=response_metrics(arrays,lo,hi)
                scores.append(dict(family=label,role=role,phase=phase,**metric,**c.score(pp['none'],lo,hi)))
        for a in ('none','vsl'):
            assert f.load_prediction(O/spec['name']/f'refined_guard1_{a}.json')==f.load_prediction(O/selected['selected']['name']/f'refined_guard1_{a}.json')
        for arm in f.ARMS[1:]:
            delta=result['deltas'][arm];truth=actual[arm]['actual']
            rows.append(dict(family=label,arm=arm,predicted=delta['total'],actual=truth['total'],
                **{k:delta[k] for k in ('mainline','on','off')},sign_correct=delta['total']*truth['total']>0))
    table(O/'response_metrics.csv',scores);table(O/'gain_check.csv',rows)
    forecasts=sum(c.load(p)['forecasts'] for p in O.glob('*/refined_guard1_receipt.json'))
    save(O/'validation.json',dict(forecasts=forecasts,new_native_runs=0,production_adopted=False,independent_validation=False,
        response_metrics=scores,gains=rows,all_owned_calculations_terminal=True))
    print(json.dumps(dict(forecasts=forecasts,metrics=scores,gains=rows),indent=2),flush=True)


def literature():
    """Recalibrate two additional published VSL laws, without changing the MPC cost."""
    global O
    from pathlib import Path
    import ramp_region
    from evaluation.controllers.freeway_fd import literature_vsl_parameters
    from vsl_strength import sampled_costs, POLICIES
    sys.path.insert(0,str(ROOT/'tmp/calibration_dependencies'));from scipy.optimize import least_squares
    O=B/'literature_vsl_v1';assert not (O/'protocol.json').exists()
    initial=c.load(B/'ramp_region_v1/region_selected_actions.json')
    def spec(name,values=None,arms=('none','vsl')):
        s=copy.deepcopy(initial);s.update(name=name,output_group=O.name,arms=list(arms),base_label='hadi_fd_cap_r2')
        if values is not None:s['vsl_fd_response']=values
        return s
    sources=[Path(__file__),B/'run.py',B/'geometry_200_branch_guard.json',B/'guard_initial_groups.json',
        B/'ramp_region_v1/region_selected_actions.json',c.O/'observed_none.npz',B/'vsl_response_v1/observed_vsl.npz',
        ROOT/'evaluation/controllers/freeway_fd.py',ROOT/'evaluation/controllers/physical_lane_groups.py',
        ROOT/'tests/test_literature_vsl_fd.py']
    save(O/'protocol.json',dict(laws=['carlson Eq11','frejo Eq13'],equation_source='https://www.dcsc.tudelft.nl/~bdeschutter/pub/rep/19_022.pdf',
        source_pages_pdf=[7,8],calibrated=['A','E','alpha (Frejo only)'],bounds=dict(A=[0.,1.],E=[.5,4.],alpha=[0.,.25]),
        initial=dict(A=.2,E=1.5,alpha=.05),optimizer_max_nfev=3,max_pairs=dict(carlson=12,frejo=16),
        training=[2400,2700],late_check=[2700,2850],seed=23,diagnostic_step_s=1,production_step_unchanged_s=5,
        geometry='31 cells per direction, each ramp separate; existing short branch partitions retained',
        fit_loss='NC state loss + paired VSL-minus-NC speed/10, N/2, q/200 residuals, same masks and units as vsl_response_v1.',
        selection='Minimum training loss among evaluated stable candidates whose induced FD capacity at80/100 is no greater than baseline. Raw best also retained; no capacity boost adopted from fitting alone.',
        scope='Replace active-VSL desired-speed law only. Existing CTM receiving, actual accepted merge, finite port storage/drainage, anticipation branches, costs and inputs fixed. Not a reproduction of a paper network or closed-loop MPC.',
        inactive_semantics='Original no-control law preserved exactly. At active Frejo VSL, vf*=min(Vmax*b_r,vf), including nominal-cap clipping if vf>Vmax. No additional command min-cap is applied after the new law.',
        independent_validation=False,new_native=0,production_adopted=False,
        source_pins={str(p.relative_to(ROOT)):c.sha(p) for p in sources}))
    baseline=execute(spec('lp20260921_disabled',arms=f.ARMS))
    for arm in f.ARMS:
        assert f.load_prediction(O/'lp20260921_disabled'/f'refined_guard1_{arm}.json')==f.load_prediction(B/'ramp_region_v1/region_selected_actions'/f'refined_guard1_{arm}.json')
    save(O/'disabled_identity.json',dict(all_four_forecasts_exact=True))
    summaries=[]
    for family in ('carlson','frejo'):
        keys=['A','E']+(['alpha'] if family=='frejo' else [])
        low=np.array([0.,.5]+([0.] if family=='frejo' else []));span=np.array([1.,3.5]+([.25] if family=='frejo' else []))
        x0=(np.array([.2,1.5]+([.05] if family=='frejo' else []))-low)/span
        history=[];cache={};maximum=12 if family=='carlson' else 16
        class Budget(Exception):pass
        def objective(x):
            key=tuple(x)
            if key in cache:return cache[key]
            if len(history)>=maximum:raise Budget()
            values=dict(law=family,A=.2,E=1.5,alpha=0.);values.update(zip(keys,(low+span*x).tolist()))
            s=spec(f'lp20260921_{family}_{len(history):02}',values);row=execute(s)
            # The new VSL law must not alter NC/RM or use future observations.
            assert f.load_prediction(O/s['name']/'refined_guard1_none.json')==f.load_prediction(O/'lp20260921_disabled/refined_guard1_none.json')
            p=initial['physical_coefficients'];vf,rc,am=p['v_free'],p['rho_crit'],p['metanet_a_m'];q0=vf*rc*math.exp(-1/am)
            capacities={}
            for command in (80.,100.):
                vp,rp,ap=literature_vsl_parameters(values,vf,rc,am,command,120.)
                capacities[str(int(command))]=vp*rp*math.exp(-1/ap)/q0
            row.update(fd_capacity_ratios=capacities,capacity_bonus_free=max(capacities.values())<=1.+1e-10)
            history.append(row);save(O/(family+'_history.json'),history)
            cache[key]=np.load(O/(s['name']+'_residual.npy'));return cache[key]
        def jac(x):
            r=objective(x);columns=[]
            for j in range(len(keys)):
                dx=.025 if x[j]+.025<=1 else -.025;z=x.copy();z[j]+=dx
                columns.append((objective(z)-r)/dx)
            return np.stack(columns,axis=1)
        try:
            fit=least_squares(objective,x0,jac=jac,bounds=(np.zeros(len(keys)),np.ones(len(keys))),
                max_nfev=3,ftol=.002,xtol=.002,gtol=.002,tr_solver='lsmr')
            stop=dict(status=int(fit.status),message=fit.message,nfev=int(fit.nfev),njev=int(fit.njev))
        except Budget:stop=dict(status=0,message='Explicit short calibration budget exhausted')
        eligible=[r for r in history if r['capacity_bonus_free']]
        assert eligible,'No capacity-neutral-or-lower candidate; preserve failure and do not promote'
        selected=min(eligible,key=lambda r:r['objective']);raw=min(history,key=lambda r:r['objective'])
        frozen=dict(selected=selected,raw_best=raw,optimizer=stop,fit_pairs=len(history),independent_validation=False)
        save(O/(family+'_selection.json'),frozen);print('FROZEN',family,selected['name'],selected['spec']['vsl_fd_response'],flush=True)
        s=spec('lp20260921_'+family+'_actions',selected['spec']['vsl_fd_response'],f.ARMS);execute(s)
        for arm in ('none','vsl'):
            assert f.load_prediction(O/s['name']/f'refined_guard1_{arm}.json')==f.load_prediction(O/selected['name']/f'refined_guard1_{arm}.json')
        assert f.load_prediction(O/s['name']/'refined_guard1_rm_ramp.json')==f.load_prediction(O/'lp20260921_disabled/refined_guard1_rm_ramp.json')
        predictions={a:f.load_prediction(O/s['name']/f'refined_guard1_{a}.json') for a in ('none','vsl')}
        arrays={a:c.predicted(p) for a,p in predictions.items()};_,late=response_metrics(arrays,10,15)
        result=c.load(K/('segment_resolution_20260921_cal_'+s['name'])/'result.json')
        policy_results=[];native=c.load(B/'vsl_strength_v1/qualified_scope_comparison.json')['results']
        for label in ('up100','both80','up80'):
            up,down=POLICIES[label];p=spec('lp20260921_'+family+'_'+label,selected['spec']['vsl_fd_response'])
            p['diagnostic_vsl_policy']={str(i):[max(100,up if i<=54 else down),up if i<=54 else down,up if i<=54 else down] for i in range(51,59)}
            execute(p)
            costs={a:sampled_costs(f.load_prediction(O/p['name']/f'refined_guard1_{a}.json')) for a in ('none','vsl')}
            delta={k:costs['vsl'][k]-costs['none'][k] for k in costs['none']};delta['total']=sum(delta.values())
            truth=next(x['actual_geometric_delta'] for x in native if x['policy']==label)
            policy_results.append(dict(policy=label,predicted_common5s=delta,actual_common5s=truth))
        summary=dict(family=family,selected_values=selected['spec']['vsl_fd_response'],fit_pairs=len(history),
            before=history[0]['objective'],after=selected['objective'],late=late,deltas_1s=result['deltas'],
            capacity_ratios=selected['fd_capacity_ratios'],policy_checks=policy_results,qualified=False)
        summaries.append(summary);save(O/'results.json',dict(results=summaries,new_native=0,qualified=False,independent_validation=False))
    forecasts=sum(c.load(p)['forecasts'] for p in O.glob('*/refined_guard1_receipt.json'))
    save(O/'terminal.json',dict(forecasts=forecasts,all_owned_calculations_terminal=True,new_native=0,qualified=False))
    print('LITERATURE COMPLETED',forecasts,flush=True)


def literature_report():
    """Verify completed forecasts and compare identical geometric cost scopes."""
    global O
    from pathlib import Path
    from vsl_strength import sampled_costs
    from evaluation.controllers.freeway_fd import literature_vsl_parameters
    O=B/'literature_vsl_v1';terminal=c.load(O/'terminal.json');assert terminal['all_owned_calculations_terminal']
    pins=c.load(O/'protocol.json')['source_pins'];resolved={}
    for rel,digest in pins.items():
        path=ROOT/rel
        if c.sha(path)!=digest:
            assert path==Path(__file__)
            path=O/'source_before_scope_report.py.txt'
        assert c.sha(path)==digest;resolved[rel]=str(path.relative_to(ROOT))
    before=c.load(O/'before_sources.json')
    for rel,row in before.items():assert c.sha(ROOT/row['archive'])==row['sha256']
    baseline=f.load_prediction(O/'lp20260921_disabled/refined_guard1_none.json')
    reference=B/'ramp_region_v1/region_selected_actions'
    for arm in f.ARMS:
        assert f.load_prediction(O/'lp20260921_disabled'/f'refined_guard1_{arm}.json')==f.load_prediction(reference/f'refined_guard1_{arm}.json')
    forecasts=0;cases=0;checks=[];usage_count=0;nc_exact=0
    for path in O.glob('*/refined_guard1_receipt.json'):
        r=c.load(path);spec=r['fit'];assert r['completed'] and r['runner_sha256']==c.sha(B/'run.py')
        assert c.load(O/(spec['name']+'.json'))==spec
        log=(O/(spec['name']+'_process.log')).read_text(encoding='utf-8');assert 'Ran 27 tests' in log and '\nOK\n' in log
        score=c.load(O/(spec['name']+'_score.json'));assert score['exit_code']==0 and score['spec']==spec
        checks.extend(score['numerics'].values());forecasts+=r['forecasts'];cases+=1
        assert f.load_prediction(path.parent/'refined_guard1_none.json')==baseline;nc_exact+=1
        if 'vsl_fd_response' in spec:
            for arm in spec['arms']:
                usage=c.load(path.parent/f'vsl_fd_usage_{arm}.json');actual_calls=0
                for row in usage:
                    assert row['spec']==spec['vsl_fd_response']
                    expected=literature_vsl_parameters(row['spec'],*row['base'],row['command'],row['maximum'])
                    assert list(expected)==row['effective']
                    if row['calls']>1:
                        assert row['base']==[spec['physical_coefficients'][k] for k in ('v_free','rho_crit','metanet_a_m')]
                        assert row['maximum']==120. and row['command'] in (80.,100.)
                        actual_calls+=row['calls']
                assert (actual_calls>0)==(arm in ('vsl','both'));usage_count+=1
    assert len(checks)==forecasts==terminal['forecasts']==66 and cases==30 and all(x['passed'] for x in checks)
    source_native=B/'vsl_strength_v1/qualified_scope_comparison.json';native=c.load(source_native)
    assert native['passed_execution_and_bookkeeping']
    truths={x['policy']:x['actual_geometric_delta'] for x in native['results']}
    actual=c.load(B.parent/'response_chain_20260921/qualification.json')['gains']
    results=c.load(O/'results.json')['results'];gains=[];policies=[];candidates=[]
    for family,folder in [('existing','lp20260921_disabled')]+[(s['family'],'lp20260921_'+s['family']+'_actions') for s in results]:
        raw=c.load(K/('segment_resolution_20260921_cal_'+folder)/'result.json')
        for arm in f.ARMS[1:]:gains.append(dict(family=family,arm=arm,predicted=raw['deltas'][arm],actual=actual[arm]['actual']))
        if family=='existing':continue
        for label in ('both100','up100','both80','up80'):
            name=folder if label=='both100' else 'lp20260921_'+family+'_'+label
            costs={a:sampled_costs(f.load_prediction(O/name/f'refined_guard1_{a}.json')) for a in ('none','vsl')}
            delta={k:costs['vsl'][k]-costs['none'][k] for k in costs['none']};delta['total']=sum(delta.values())
            truth=truths[label]
            policies.append(dict(family=family,policy=label,predicted=delta,actual=truth,
                error={k:delta[k]-truth[k] for k in delta},sign_match=delta['total']*truth['total']>0))
        for row in c.load(O/(family+'_history.json')):
            delta=c.load(K/('segment_resolution_20260921_cal_'+row['name'])/'result.json')['deltas']['vsl']
            candidates.append(dict(family=family,name=row['name'],objective=row['objective'],values=row['spec']['vsl_fd_response'],
                fd_capacity_ratios=row['fd_capacity_ratios'],capacity_bonus_free=row['capacity_bonus_free'],vsl_delta_ttt=delta['total']))
    assert len(candidates)==21
    save(O/'checked_results.json',dict(gains_1s=gains,policies_common5s=policies,all_fit_candidates=candidates,
        source_native=str(source_native.relative_to(ROOT)),source_native_sha256=c.sha(source_native),
        raw_results_note='results.json retains initial full-link policy costs. This report uses prior geometry-audited costs, excluding negative-source/past-terminal positions; no new forecasts or refit.',
        independent_validation=False,new_native=0,qualified=False,production_adopted=False))
    baseline_score=c.load(O/'lp20260921_disabled_score.json')
    table1=[]
    for arm in f.ARMS[1:]:
        values=[next(x['predicted']['total'] for x in gains if x['family']==name and x['arm']==arm) for name in ('existing','carlson','frejo')]
        table1.append('| '+arm+' | '+f"{actual[arm]['actual']['total']:+.6f}"+' | '+' | '.join(f'{x:+.6f}' for x in values)+' |')
    table2=[]
    for label in ('both100','up100','both80','up80'):
        values=[next(x['predicted']['total'] for x in policies if x['family']==name and x['policy']==label) for name in ('carlson','frejo')]
        table2.append('| '+label+' | '+f"{truths[label]['total']:+.6f}"+' | '+' | '.join(f'{x:+.6f}' for x in values)+' |')
    details=[]
    for s in results:
        selection=c.load(O/(s['family']+'_selection.json'))
        details.append(f"- {s['family']}: {s['fit_pairs']}개 NC/VSL 쌍. A/E/alpha={s['selected_values']}. 학습 목적값 {s['before']:.6f} → {s['after']:.6f}, 뒤 150초 반응 손실 {s['late']['response_loss']:.6f}. optimizer: {selection['optimizer']}. 용량 제약 없는 최저 학습 손실 {selection['raw_best']['objective']:.6f}도 따로 보존했다.")
    text='''# 추가 METANET VSL 식: 적용·재보정·이득 검증

**이번에 시험한 두 식 모두 VSL 순이득 예측을 해결하지 못했다.** 6편의 관련 원문을 검토해, 기존과 중복되는 MPC 식과 새로운 물리 반응식을 구분했다. Carlson FD 변형과 Frejo의 순응도 포함 FD 변형을 기존 플랜트에 직접 연결하고 **66회 450초 오프라인 예측**을 완료했다. 새 VISSIM 런은 0회이며, 기존 native 기록을 평가에 사용했다. 수식·출처·MPC와 모델 논문의 구분은 [SOURCE_REVIEW.md](SOURCE_REVIEW.md)에 정리했다.

## 동일 초기 상태의 4조건

2400–2850초, seed23. ΔTTT=제어−무제어, 차량·시간; 음수가 이득이다. 동측 본선+4개 on-ramp+4개 off-ramp 성분이며 전체 Ω 성능은 아니다. 이 표는 공통 1초 비용이다.

| 제어 | VISSIM 기록 | 기존 플랜트 | Carlson 재보정 | Frejo 재보정 |
|---|---:|---:|---:|---:|
'''+ '\n'.join(table1)+'''

RM만 사용한 경우는 정확히 같아야 한다. 새 식은 활성 VSL에만 적용되므로 이 결과를 RM 재보정 개선으로 해석하지 않는다. Frejo의 VSL 예측은 본선 +0.13270, on-ramp -0.02429, off-ramp -0.04599로 합계 +0.06242다. 실제는 본선 -0.85222, on-ramp -0.16667, off-ramp +0.03694다. 합계뿐 아니라 본선·진출부 방향도 아직 틀린다.

## 실제 재보정 범위

앞서 보정된 NC 동역학, 램프 분리 31셀 기하, merge/anticipation/수용·저장·배수·대기 비용을 고정했다. 새 A/E 및 Frejo alpha를 2400–2700초의 속도·재고·유량 반응으로 재보정했다. 기존 모델의 학습 목적값은 '''+f'{baseline_score["objective"]:.6f}'+'''이다.

'''+ '\n'.join(details)+'''

두 최적화 모두 짧은 예산에서 종료됐으며 전역 최적 보정은 아니다. 비교값은 평가한 후보 중 선택했고, 유한차분 후보도 포함한다. FD에서 유도되는 용량이 무제어보다 커지는 후보는 기록하되 채택 후보에서는 제외했다. 이 제한 없이 평가한 값까지 포함해 21개 새 계수 후보의 기본 VSL ΔTTT가 전부 양수였다. 따라서 이번 결과를 ‘유효한 용량 증가를 금지해서만 이득을 못 본 것’으로 설명할 수는 없지만, 전체 매개변수 영역을 배제한 결론도 아니다.

Frejo의 alpha≈0.151은 이 플랜트에서 맞춘 유효계수다. 실측 운전자 위반율이나 확정된 순응도로 해석할 수 없다. 원래 수용 제약은 유지했으므로 독립적인 순수 METANET 복제 결과도 아니다.

## 동결 후 VSL 강도·위치 비교

공통 5초 기록·동일 기하 범위로 다시 계산했다. both는 양쪽 VSL 구역이라는 뜻이며 RM+VSL 조합을 뜻하지 않는다. 80 조건은 2400초 100 → 2550초 80으로 기존 변경 한도를 지킨다.

| VSL 조건 | VISSIM ΔTTT | Carlson | Frejo |
|---|---:|---:|---:|
'''+ '\n'.join(table2)+'''

모든 VSL 조건의 이득 부호가 맞지 않았다. 뒤 150초와 RM/both, 다른 강도·위치 결과는 계수 선택 뒤 대조했지만 이미 본 개발 자료다. 미사용 seed나 실제 폐루프 MPC 검증을 통과한 것은 아니다.

## 검증과 남는 판단

- 비활성 새 기능 4조건 전체 JSON은 이전 예측과 정확히 같다. 30개 케이스의 NC도 정확히 같다.
- 66개 예측 수치·보존 검사, 실제 계수 소비·명령 적용 범위, 서측 불변 검사와 케이스별 기존 27개 수송 검사를 통과했다. 수식·비활성 경로·셀 계수·저장 한계 단위검사 8개도 통과했다.
- 두 준비/채점 실패는 보존했다: 기존 결과명 충돌은 예측 전 실패, 관측 파일 경로 오류는 완료된 4개 예측을 재사용해 복구했다. 또 최초 정책 요약의 전체 링크 비용과 기하 제외 비용을 구분해 `checked_results.json`으로 재대조했다. 원래 결과는 덮어쓰지 않았다.
- 정본 parameters.json·네트워크·수요·생산 5초 간격은 바꾸지 않았다. 짧은 셀 진단은 기존 1초 적분이다. 새 식은 기본 비활성이며 운영 제어기로 채택하지 않았다.

현재 증거는 ‘VSL에 따라 FD만 변형하면 해결된다’는 가설을 지지하지 않는다. 다음에는 지금의 합류·진출 영향부에서 속도/재고/수용 제약이 방출·회복으로 연결되는 과정을 검증하는 편이 타당하다. 이 결과만으로 특정 누락 항을 확정하거나 METANET 전체가 불가능하다고 결론내릴 수 없다. 물리 이득 부호가 맞기 전에 MPC 탐색법을 교체하는 것은 해결 근거가 부족하다. 자유류의 불필요한 제한 회피와 미사용 seed 검증도 남아 있다.
'''
    (O/'README.md').write_text(text,encoding='utf-8')
    verification=dict(forecasts=forecasts,cases=cases,all_owned_calculations_terminal=True,numeric_pass=len(checks),
        max_speed=max(x['max_speed_kmh'] for x in checks),max_courant=max(x['max_courant'] for x in checks),max_mass_residual=max(x['max_mass_residual_veh'] for x in checks),
        all_nc_whole_json_exact=nc_exact,disabled_four_whole_json_exact=True,literature_usage_files_checked=usage_count,
        unit_tests_passed=8,transport_contracts_per_case=27,protocol_pins_resolved=resolved,
        current_source_pins={str(p.relative_to(ROOT)):c.sha(p) for p in [Path(__file__),B/'run.py',ROOT/'evaluation/controllers/freeway_fd.py',ROOT/'evaluation/controllers/physical_lane_groups.py',ROOT/'tests/test_literature_vsl_fd.py',ROOT/'evaluation/parameters.json',source_native,B.parent/'response_chain_20260921/qualification.json',B/'vsl_strength_v1/edge_audit.json',B/'vsl_strength.py']},
        new_native=0,qualified=False,production_adopted=False)
    save(O/'verification.json',verification)
    files=[p for p in O.rglob('*') if p.is_file() and p.name!='completion.json']
    save(O/'completion.json',dict(outputs={str(p.relative_to(ROOT)):c.sha(p) for p in files},verification_sha256=c.sha(O/'verification.json'),qualified=False))
    print(json.dumps(dict(forecasts=forecasts,cases=cases,gains=gains,policies=policies),ensure_ascii=False),flush=True)


def receiving_speed_experiment():
    global O
    O=B/'receiving_speed_v1';protocol=c.load(O/'protocol.json')
    assert not (O/'results.json').exists()
    baseline=c.load(B/'literature_vsl_v1/lp20260921_disabled.json');results=[]
    reference=B/'literature_vsl_v1/lp20260921_disabled'
    actual=c.load(B.parent/'response_chain_20260921/qualification.json')['gains']
    pins={str(p.relative_to(ROOT)):c.sha(p) for p in [Path(__file__),B/'run.py',
        ROOT/'evaluation/controllers/physical_lane_groups.py',ROOT/'evaluation/parameters.json',
        ROOT/'tests/test_receiving_speed_response.py']}
    save(O/'execution_sources.json',pins)
    for case in protocol['candidates']:
        spec=copy.deepcopy(baseline);spec.update(name=case['name'],output_group=O.name,arms=list(f.ARMS))
        if case['response'] is not None:spec['receiving_speed_response']=case['response']
        score=execute(spec);pred={a:f.load_prediction(O/spec['name']/f'refined_guard1_{a}.json') for a in f.ARMS}
        effective=c.load(O/spec['name']/'effective_config.json')
        assert all(e['receiving_speed_response']==({'FW_E':case['response']} if case['response'] is not None else {}) for e in effective)
        usages={}
        for arm,p in pred.items():
            old=f.load_prediction(reference/f'refined_guard1_{arm}.json')
            if case['response'] is None:assert p==old,'Default-disabled response changed the forecast'
            road=next(r for r in p['diagnostics']['roads'] if r['road']=='FW_E')
            rows=[r for r in road.get('port_response_trace',[]) if r['kind']=='receiving_speed']
            assert bool(rows)==(case['response'] is not None)
            if rows:
                assert all(r['reaction_seconds']==case['response']['reaction_seconds'] and r['accepted_veh']<=r['requested_veh']+1e-7 for r in rows)
            usages[arm]=dict(events=len(rows),max_reduction_kmh=max([r['before_kmh']-r['after_kmh'] for r in rows]+[0.]),
                groups=sorted({(r['cell'],r['group'],r['side']) for r in rows}))
        costs=c.load(K/('segment_resolution_20260921_cal_'+spec['name'])/'result.json')
        results.append(dict(name=spec['name'],response=case['response'],score=score,
            gains=costs['deltas'],actual={a:actual[a]['actual'] for a in f.ARMS[1:]},
            late=response_metrics({a:c.predicted(pred[a]) for a in ('none','vsl')},10,15)[1],usage=usages))
        save(O/'progress.json',results)
    reference_loss=results[0]['score']['train']['objective']
    for r in results:
        r['nc_guard_passed']=r['score']['train']['objective']<=1.1*reference_loss
        r['gain_signs']={a:r['gains'][a]['total']*r['actual'][a]['total']>0 for a in f.ARMS[1:]}
        r['qualified']=False
    save(O/'results.json',dict(results=results,forecasts=12,new_native=0,fit_performed=False,qualified=False))
    save(O/'terminal.json',dict(all_owned_calculations_terminal=True,forecasts=12))
    print(json.dumps([dict(name=r['name'],nc=r['score']['train']['objective'],response=r['score']['response']['response_loss'],
        gains=r['gains'],guard=r['nc_guard_passed']) for r in results]),flush=True)


def distance_objective_report():
    """Rescore saved responses; no refit, controller, or native execution.

    TVD here is mainline production, while TTT retains connector waiting.
    This intentionally narrower experiment does not claim full-Omega TVD.
    """
    from prepare import native
    from evaluation.controllers.control_area_objective import AreaMetrics, ControlAreaObjective
    out=B/'objective_distance_v1';protocol=c.load(out/'protocol.json')
    assert not (out/'results.json').exists()
    lo,hi=protocol['start_s'],protocol['end_s'];arms=protocol['arms']
    sources=c.load(B/'sources.json');pins={};actual={};proofs={};crossing_checks={}
    for arm in arms:
        key=arm+'_s23';source=sources[key];proof={};counts=dict(mainline=0,on=0,off=0)
        speed_distance=0.;position_distance=0.;prior={};priorloc={};misses=[];negative=[];frames=0
        with np.load(B/(key+'_0.npz')) as cache:
            cached_n=cache['n'][lo+1-2249:hi+1-2249].sum()
            cached_mom=cache['mom'][lo+1-2249:hi+1-2249].sum()/3600
        for t,frame in native.native(ROOT/source['path'],proof):
            loc={vid:native.locate(car) for vid,car in frame.items()}
            loc={vid:p for vid,p in loc.items() if p is not None}
            if lo<t<=hi:
                frames+=1;counts['mainline']+=len(loc)
                counts['on']+=sum(car.link in native.ON for car in frame.values())
                counts['off']+=sum(car.link in native.OFF for car in frame.values())
                speed_distance+=sum(frame[vid].speed for vid in loc)/3600
                # Independent longitudinal-distance check. Actual same-vehicle
                # progress plus clipped entry/exit pieces, not desired speed.
                for vid in priorloc.keys()|loc.keys():
                    a,b=priorloc.get(vid),loc.get(vid);old,new=prior.get(vid),frame.get(vid)
                    if a and b:progress=b[1]-a[1]
                    elif b and old and old.link in native.ON:progress=b[1]-native.ON[old.link]['chain_pos_m']
                    elif b and new.link==74 and (old is None or old.link==74 and old.pos<0):progress=b[1]
                    elif a and new and new.link in native.OFF:progress=native.OFF[new.link]['chain_pos_m']-a[1]
                    elif a and old.link==24 and native.BOUNDS[-1]-a[1]<=old.speed/3.6+11.5 and (new is None or new.link==24):progress=native.BOUNDS[-1]-a[1]
                    else:misses.append([t,vid]);continue
                    if progress < -0.002:negative.append([t,vid,progress])
                    position_distance+=progress/1000
            prior,priorloc=frame,loc
        assert frames==hi-lo and not misses and not negative,(arm,misses[:5],negative[:5])
        assert proof['file_sha256']==source['file_sha256']
        assert counts['mainline']==cached_n and math.isclose(speed_distance,cached_mom,abs_tol=1e-7)
        parts={k:v/3600 for k,v in counts.items()}
        actual[arm]=dict(ttt_parts_veh_h=parts,ttt_veh_h=sum(parts.values()),tvd_mainline_veh_km=speed_distance,
            position_progress_veh_km=position_distance,frames=frames)
        proofs[arm]=proof;crossing_checks[arm]=dict(unclassified=misses,negative_progress=negative)
        pins[source['path']]=source['file_sha256']
        print('Distance postprocess complete:',arm,flush=True)
    assert len({p['prefix2249_2400_original9_sha256'] for p in proofs.values()})==1
    save(out/'native.json',dict(values=actual,proofs=proofs,crossing_checks=crossing_checks))
    families={'existing':'lp20260921_disabled','carlson':'lp20260921_carlson_actions','frejo':'lp20260921_frejo_actions'}
    values={'native':actual};flow_audits={}
    lengths={r['cell']:r['length_km'] for r in c.load(B/'geometry_200_branch_guard.json')['cells'] if r['road']=='FW_E'}
    for family,folder in families.items():
        values[family]={};flow_audits[family]={}
        for arm in arms:
            path=B/'literature_vsl_v1'/folder/f'refined_guard1_{arm}.json'
            p=f.load_prediction(path);compressed=path.with_suffix('.json.gz');pins[str(compressed.relative_to(ROOT))]=c.sha(compressed)
            rows=p['lane_groups']['FW_E'];on=[r for r in p['ramps'] if r['road']=='FW_E'];off=[r for r in p['ports'] if r['road']=='FW_E']
            assert {r['time_s'] for r in rows}==set(range(lo+1,hi+1))
            assert len(rows)==(hi-lo)*sum(map(len,c.WIDTHS)) and len(on)==len(off)==(hi-lo)*4
            assert all(r['duration_sec']==1 for r in on)
            parts=dict(mainline=sum(r['n_veh'] for r in rows)/3600,
                on=sum(r['end']['connector_veh'] for r in on)/3600,off=sum(r['n_veh'] for r in off)/3600)
            values[family][arm]=dict(ttt_parts_veh_h=parts,ttt_veh_h=sum(parts.values()),
                tvd_mainline_veh_km=sum(r['n_veh']*r['v_kmh'] for r in rows)/3600)
            # q*L based on accepted cell departures is NOT substituted for
            # distance: partial port cells and end stocks need separate terms.
            flow_audits[family][arm]=sum(r['mainline_out_veh']*lengths[r['cell']] for r in rows)
    deltas={};scores=[];thresholds={}
    for family,data in values.items():
        deltas[family]={};thresholds[family]={}
        for arm in arms[1:]:
            dt=data[arm]['ttt_veh_h']-data['none']['ttt_veh_h'];dd=data[arm]['tvd_mainline_veh_km']-data['none']['tvd_mainline_veh_km']
            deltas[family][arm]=dict(ttt_veh_h=dt,tvd_mainline_veh_km=dd,
                ttt_parts_veh_h={k:data[arm]['ttt_parts_veh_h'][k]-data['none']['ttt_parts_veh_h'][k] for k in data[arm]['ttt_parts_veh_h']})
            thresholds[family][arm]=dict(signed_break_even_seconds_per_km=3600*dt/dd if dd else None,
                favorable_for_all_nonnegative_weights=dt<0 and dd>=0,
                unfavorable_for_all_nonnegative_weights=dt>=0 and dd<=0)
        for weight in protocol['distance_seconds_per_km']:
            objective=ControlAreaObjective(protocol['exit_beta_seconds']/3600,weight/3600)
            costs={arm:objective.score(AreaMetrics(data[arm]['ttt_veh_h']),tvd_veh_km=data[arm]['tvd_mainline_veh_km']) for arm in arms}
            delta={arm:costs[arm]-costs['none'] for arm in arms[1:]}
            for arm in arms[1:]:
                assert math.isclose(delta[arm],deltas[family][arm]['ttt_veh_h']-weight/3600*deltas[family][arm]['tvd_mainline_veh_km'],abs_tol=1e-10)
            scores.append(dict(family=family,weight_sec_per_km=weight,delta_score_veh_h=delta,rank=sorted(costs,key=costs.get)))
    result=dict(protocol=protocol,values=values,deltas=deltas,scores=scores,thresholds=thresholds,
        accepted_boundary_flow_times_length_audit=flow_audits,
        audit_note='Boundary q*L is an independent transport diagnostic, not a matched TVD substitute for port-split cells. n*v is the literature-style state-production approximation; no claim that its speed obeys every accepted-flow limit.',
        new_forecasts=0,new_native=0,calibration_performed=False,full_omega_objective_connected=False,qualified=False)
    save(out/'results.json',result)
    table(out/'sensitivity.csv',[dict(family=x['family'],weight_sec_per_km=x['weight_sec_per_km'],
        rm_delta_j=x['delta_score_veh_h']['rm_ramp'],vsl_delta_j=x['delta_score_veh_h']['vsl'],rank=' > '.join(x['rank'])) for x in scores])
    pins.update({str(p.relative_to(ROOT)):c.sha(p) for p in [Path(__file__),ROOT/'evaluation/controllers/control_area_objective.py',
        ROOT/'diagnostics/test_control_area_objective.py',ROOT/'evaluation/parameters.json',B/'sources.json',B/'geometry_200_branch_guard.json',B/'prepare.py']})
    save(out/'verification.json',dict(source_pins=pins,matched_native_prefix=True,native_cache_match=True,
        native_position_progress_classified=True,observed_and_predicted_common_end_samples=True,
        forecast_count=9,weight_rows=len(scores),unchanged_saved_forecasts=True,live_controller_enabled=False))
    print(json.dumps(dict(deltas=deltas,thresholds=thresholds),ensure_ascii=False),flush=True)


def recovery_acceleration_experiment():
    """NC-only bounded local relaxation fit; pressure/demand/costs unchanged."""
    out=B/'recovery_acceleration_v1'
    assert out.is_dir() and not (out/'protocol.json').exists()
    initial=c.load(B/'receiving_speed_v1/rs20260921_disabled.json')
    targets=list(range(25,31));fit_cells=list(range(25,30))
    old_f_out=f.O;f.O=out
    common={k:copy.deepcopy(v) for k,v in initial['state_response'].items() if k!='cell_overrides'}
    old_tau=common['relaxation']['acceleration_sec']
    sources=[Path(__file__),B/'run.py',ROOT/'evaluation/controllers/freeway_fd.py',
        ROOT/'evaluation/controllers/physical_lane_groups.py',ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py',
        ROOT/'evaluation/parameters.json',B/'geometry_200_branch_guard.json',
        B/'receiving_speed_v1/rs20260921_disabled.json',c.O/'observed_none.npz']
    save(out/'protocol.json',dict(train=[2400,2700],late=[2700,2850],seed=23,cells=targets,fit_cells=fit_cells,
        fitted_parameter='recovery acceleration time only',candidate_seconds=[6,12,24,48],identity_seconds=old_tau,
        gate='desired>speed AND downstream<=local density AND downstream<critical density; no time or control flag.',
        caveat='Opening/positive relaxation is not proof of previous congestion; free-flow equilibrium must be unchanged.',
        formula='tau becomes tau_recovery; nu becomes nu*tau_recovery/tau so nu/tau is unchanged.',
        selection='Lowest NC target-cell train state loss among numeric passes with full/other-cell NC loss <=110% baseline. No control gain used for fitting.',
        control_validation_after_freeze=True,independent_seed=False,new_native=0,production_adopted=False,
        source_pins={str(p.relative_to(ROOT)):c.sha(p) for p in sources}))
    def spec(name,tau,all_arms=False):
        s=copy.deepcopy(initial);s.pop('control_response_fit',None)
        s.update(name=name,output_group=out.name,nc_only=not all_arms,arms=list(f.ARMS) if all_arms else ['none'])
        if tau is not None:
            for i in targets:
                s['state_response']['cell_overrides'][str(i)]={**copy.deepcopy(common),'recovery_relaxation':{'acceleration_sec':tau}}
        return s
    def run(s):
        rec=f.execute(s);assert rec['exit_code']==0 and rec['numerics']['passed']
        p=f.load_prediction(out/s['name']/'refined_guard1_none.json')
        rec['regional']={name:c.score(p,cells=cells) for name,cells in
            [('target',fit_cells),('other',list(range(25))),('all',list(range(30)))]}
        rec['late']={name:c.score(p,10,15,cells=cells) for name,cells in
            [('target',fit_cells),('all',list(range(30)))]}
        save(out/(s['name']+'_regional_score.json'),rec)
        return rec,p
    try:
        baseline,p0=run(spec('ra_disabled',None,True))
        for arm in f.ARMS:
            p=f.load_prediction(out/'ra_disabled'/f'refined_guard1_{arm}.json')
            assert p==f.load_prediction(B/'receiving_speed_v1/rs20260921_disabled'/f'refined_guard1_{arm}.json')
        identity,ip=run(spec('ra_identity',old_tau));assert ip==p0
        trials=[]
        for tau in (6,12,24,48):
            row,p=run(spec('ra_t'+str(tau),tau))
            row['guard_pass']=all(row['regional'][key]['objective']<=1.10*baseline['regional'][key]['objective'] for key in ('all','other'))
            trials.append(row)
            save(out/'trials.json',trials)
        valid=[row for row in trials if row['guard_pass']]
        selected=min(valid,key=lambda r:r['regional']['target']['objective']) if valid else None
        save(out/'selected.json',dict(selected=selected,baseline=baseline,selection_frozen=True,control_data_used=False))
        if selected is None:
            save(out/'results.json',dict(qualified=False,reason='All NC guards failed',trials=trials));return
        tau=selected['spec']['state_response']['cell_overrides']['25']['recovery_relaxation']['acceleration_sec']
        chosen,sp=run(spec('ra_selected_actions',tau,True))
        assert sp==f.load_prediction(out/selected['name']/'refined_guard1_none.json')
        actual=c.load(B.parent/'response_chain_20260921/qualification.json')['gains']
        gains=[];usage={};checks={}
        for label in ('ra_disabled','ra_selected_actions'):
            ledger=c.load(K/('segment_resolution_20260921_cal_'+label)/'result.json')
            for arm in f.ARMS:
                p=f.load_prediction(out/label/f'refined_guard1_{arm}.json');checks[label+':'+arm]=c.screen(p)
                ref=f.load_prediction(out/'ra_disabled'/f'refined_guard1_{arm}.json')
                for key in ('cells','flows'):
                    assert [r for r in p[key] if r['road']=='FW_W']==[r for r in ref[key] if r['road']=='FW_W']
                if arm!='none':gains.append(dict(model=label,arm=arm,predicted=ledger['deltas'][arm],actual=actual[arm]['actual']))
                up=out/label/f'recovery_usage_{arm}.json'
                if up.exists():
                    rows=c.load(up);assert set(rows)==set(map(str,targets))
                    assert all(x['max_pressure_coefficient_error']<1e-8 for x in rows.values())
                    usage[label+':'+arm]=rows
            if label=='ra_selected_actions':
                pp={a:c.predicted(f.load_prediction(out/label/f'refined_guard1_{a}.json')) for a in ('none','vsl')}
                _,response=response_metrics(pp,10,15)
        save(out/'results.json',dict(qualified=False,selected_tau_seconds=tau,baseline=baseline['regional'],
            selected=chosen['regional'],baseline_late=baseline['late'],selected_late=chosen['late'],
            late_vsl_response=response,gains=gains,usage=usage,numerics=checks,
            forecasts=sum(c.load(p)['forecasts'] for p in out.glob('*/refined_guard1_receipt.json')),
            default_whole_json_exact=4,identity_whole_json_exact=True,nc_subset_exact=True,
            west_exact=True,production_adopted=False,new_native=0,independent_seed=False))
        print(json.dumps(dict(tau=tau,baseline=baseline['regional'],selected=chosen['regional'],gains=gains),ensure_ascii=False),flush=True)
    finally:f.O=old_f_out


def strict_recovery_acceleration_experiment():
    """Diagnostic stricter state gate; no second fit to controlled gains."""
    out=B/'recovery_acceleration_v1'
    assert (out/'results.json').exists() and not (out/'strict_results.json').exists()
    s=c.load(out/'ra_selected_actions.json');old_tau=s['state_response']['relaxation']['acceleration_sec']
    coef=s['physical_coefficients'];ceiling=coef['v_free']*math.exp(-1/coef['metanet_a_m'])
    s['name']='ra_strict_actions'
    for i in range(25,31):s['state_response']['cell_overrides'][str(i)]['recovery_relaxation']['speed_ceiling_kmh']=ceiling
    save(out/'strict_protocol.json',dict(ceiling_kmh=ceiling,definition='Existing calibrated exponential FD speed at critical density; not an empirically identified universal congestion threshold.',
        coefficient_frozen_from_nc=True,new_fit=False,source_pins={str(p.relative_to(ROOT)):c.sha(p) for p in [Path(__file__),B/'run.py',ROOT/'evaluation/controllers/freeway_fd.py']}))
    old=f.O;f.O=out
    try:row=f.execute(s)
    finally:f.O=old
    assert row['exit_code']==0 and row['numerics']['passed']
    usage={};checks={}
    for arm in f.ARMS:
        p=f.load_prediction(out/s['name']/f'refined_guard1_{arm}.json')
        assert p==f.load_prediction(out/'ra_disabled'/f'refined_guard1_{arm}.json')
        checks[arm]=c.screen(p);usage[arm]=c.load(out/s['name']/f'recovery_usage_{arm}.json')
        assert all(r['eligible']==r['changed']==0 for r in usage[arm].values())
    save(out/'strict_results.json',dict(qualified=False,ceiling_kmh=ceiling,whole_json_exact_to_baseline=4,usage=usage,numerics=checks,
        conclusion='This threshold never activates in these predicted downstream states; no effect, not a universal impossibility of recovery models.',new_native=0,new_forecasts=4))
    print('Strict FD-critical-speed gate: four complete forecasts are exactly baseline; zero eligible calls.',flush=True)


if __name__=='__main__':
    if sys.argv[1]=='recovery-acceleration':recovery_acceleration_experiment()
    elif sys.argv[1]=='strict-recovery':strict_recovery_acceleration_experiment()
    elif sys.argv[1]=='receiving-speed':receiving_speed_experiment()
    elif sys.argv[1]=='distance-objective':distance_objective_report()
    elif sys.argv[1]=='literature':literature()
    elif sys.argv[1]=='literature-report':literature_report()
    elif sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='fit':fit(sys.argv[2])
    elif sys.argv[1]=='validate':validate()
