"""Bounded ramp-neighborhood response fit through the existing plant runner."""
import copy, json, math, subprocess, sys, time
from pathlib import Path
import numpy as np
import vsl_response as v
from prepare import save, table
c=v.c;f=v.f;B=v.B;ROOT=v.ROOT;K=v.K
PHYSICAL='--physical' in sys.argv
O=B/('ramp_physical_v1' if PHYSICAL else 'ramp_region_v1')
def label(name):return 'physical_'+name if PHYSICAL else name
PORTS=[p for p in c.G['boundaries'] if p['road']=='FW_E' and p['kind'] in ('ramp','offramp')]
NEAR=sorted({i for p in PORTS for j in [p['to_cell'] if p['kind']=='ramp' else p['from_cell']]
             for i in range(max(0,j-1),min(31,j+2))})
FAR=sorted(set(range(30))-set(NEAR))
KEYS=('rho_crit','shape','Q','wave','delta_merge') if PHYSICAL else ('tau_acc','tau_dec','nu_high','nu_low')
BASE=c.load(B/('ramp_region_v1/region_selected_actions.json' if PHYSICAL else 'outlet_service_v1/outlet_default2400.json'))
REFERENCE=B/'ramp_region_v1/region_selected_actions' if PHYSICAL else v.O/'vr_hadi_fd_cap_r2_validation'


def specification(name,values=None,arms=('none','vsl')):
    spec=copy.deepcopy(BASE);spec.update(name=label(name),output_group=O.name,arms=list(arms))
    spec['control_response_fit']=dict(training=[2400,2700],commands=['none','vsl'],independent_validation=False,
        protocol=O.name+'/protocol.json',scope='ramp cell and immediate adjacent cells only')
    if values is not None and PHYSICAL:
        spec['regional_values']={k:values[k] for k in KEYS}
        spec['delta_merge']=values['delta_merge'];spec['physical_coefficients']['metanet_delta_merge']=values['delta_merge']
        spec['regional_physical_coefficients']=[dict(cells=NEAR,coefficients=dict(rho_crit=values['rho_crit'],metanet_a_m=values['shape']))]
        for i in NEAR:
            spec['hadiuzzaman']['cells'][i].update(capacity_vphpl=values['Q'],wave_kmh=values['wave'],rho_critical=values['rho_crit'])
    elif values is not None:
        local=copy.deepcopy(spec['state_response'])
        local['relaxation']=dict(acceleration_sec=values['tau_acc'],deceleration_sec=values['tau_dec'])
        local['anticipation']=dict(downstream_ge_local=values['nu_high'],downstream_lt_local=values['nu_low'])
        spec['state_response']['cell_overrides']={str(i):copy.deepcopy(local) for i in NEAR}
        spec['regional_values']=dict(values)
    return spec


def nc_residual(pred,lo=0,hi=10,cells=range(30)):
    obs=v.observed('none');arrays=c.predicted(pred);err=[[],[],[]]
    for i in cells:
        ng=len(c.WIDTHS[i]);n=obs['n'][lo:hi,i,:ng];m=arrays['n'][lo:hi,i,:ng]
        av=np.divide(obs['mom'][lo:hi,i,:ng],n,out=np.zeros_like(n),where=n>0)
        pv=np.divide(arrays['mom'][lo:hi,i,:ng],m,out=np.zeros_like(m),where=m>0)
        err[0].extend((pv-av)[n>=1]);err[1].extend((m-n).ravel())
        err[2].extend((arrays['q'][lo:hi,i]-obs['q'][lo:hi,i])*120)
    return np.concatenate([np.asarray(x)/s/math.sqrt(len(x)) for x,s in zip(err,(20,5,500))])


def costs(p):
    return dict(mainline=sum(r['n_veh']*5/3600 for r in p['lane_groups']['FW_E'] if r['time_s']%5==0),
        on=sum(r['end']['connector_veh']*5/3600 for r in p['ramps'] if r['road']=='FW_E' and r['end_sec']%5==0),
        off=sum(r['n_veh']*5/3600 for r in p['ports'] if r['road']=='FW_E' and r['time_s']%5==0))


def execute(spec):
    name=spec['name'];path=O/(name+'.json');resultpath=O/(name+'_score.json')
    assert not resultpath.exists()
    save(path,spec);started=time.perf_counter()
    with (O/(name+'_process.log')).open('x',encoding='utf-8') as log:
        proc=subprocess.run([sys.executable,'-B','-X','utf8',str(B/'run.py'),'refined_guard1',str(path)],
                            cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    result=dict(name=name,spec=spec,exit_code=proc.returncode,seconds=time.perf_counter()-started)
    if proc.returncode:save(resultpath,result);raise RuntimeError(name+' execution failed')
    pred={a:f.load_prediction(O/name/f'refined_guard1_{a}.json') for a in spec['arms']}
    checks={a:c.screen(p) for a,p in pred.items()}
    for a,p in pred.items():
        ref=f.load_prediction(REFERENCE/f'refined_guard1_{a}.json')
        for key in ('cells','flows','ports','ramps'):
            assert [r for r in p[key] if r['road']=='FW_W']==[r for r in ref[key] if r['road']=='FW_W']
    effective=c.load(O/name/'effective_config.json')
    for row in effective:
        old=next(r for r in c.load(REFERENCE/'effective_config.json') if r['arm']==row['arm'])
        expected=copy.deepcopy(old)
        if PHYSICAL:
            expected['scalar']=spec['physical_coefficients'];expected['receiving']['FW_E']=spec['hadiuzzaman']
            for region in spec.get('regional_physical_coefficients',[]):
                for i in region['cells']:expected['rows'][i].update(region['coefficients'])
        assert {k:x for k,x in row.items() if k!='state_response'}=={k:x for k,x in expected.items() if k!='state_response'}
        assert row['state_response']['FW_E']==spec['state_response']
    if spec['state_response'].get('cell_overrides'):
        for a in spec['arms']:
            usage=c.load(O/name/f'cell_response_{a}.json');assert set(usage)=={str(i) for i in range(31)}
            for i,row in usage.items():
                expected=spec['state_response']['cell_overrides'].get(i,{k:x for k,x in spec['state_response'].items() if k!='cell_overrides'})
                assert row['calls']>0 and row['response']==expected and row['override']==(int(i) in NEAR)
    state=nc_residual(pred['none']);response,metric=v.response_metrics({a:c.predicted(pred[a]) for a in ('none','vsl')})
    r=np.concatenate((state,response));np.save(O/(name+'_residual.npy'),r)
    result.update(numerics=checks,objective=float(r@r),nc_loss=float(state@state),response=metric,
        nc_near=c.score(pred['none'],cells=NEAR),nc_far=c.score(pred['none'],cells=FAR),
        west_exact=True,effective_config_exact=True,costs5s={a:costs(p) for a,p in pred.items()})
    save(resultpath,result)
    print(json.dumps(dict(name=name,loss=result['objective'],nc=result['nc_loss'],response=metric['response_loss'],
        numerical=all(x['passed'] for x in checks.values()),seconds=result['seconds'])),flush=True)
    return result,pred


def prepare():
    assert not (O/'protocol.json').exists()
    sources=[Path(__file__),B/'run.py',B/'geometry_200_branch_guard.json',c.O/'observed_none.npz',v.O/'observed_vsl.npz',
        ROOT/'evaluation/controllers/freeway_fd.py',ROOT/'evaluation/controllers/physical_lane_groups.py',
        ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py',ROOT/'evaluation/parameters.json']
    save(O/'protocol.json',dict(near_cells=NEAR,far_cells=FAR,ports=PORTS,neighborhood='attached cell plus immediately previous/next cell; geometry fixed before fitting',
        train=[2400,2700],late_check=[2700,2850],seed=23,initial_s=2400,forecast_sec=450,
        independent_validation=False,future_inputs=False,new_native=0,production_adopted=False,
        parameters=list(KEYS),bounds={k:f.BOUNDS[k][:2] for k in KEYS},maximum_fit_pairs=16,
        objective='NC all30 nonterminal cells speed/20,N/5,q/500 squared errors + paired VSL-minus-NC speed/10,N/2,q/200 squared errors; fixed observed masks.',
        selection='Lowest training objective with numerical pass, global NC and NEAR/FAR NC losses <=110% of common baseline; freeze before late/control checks.',
        fixed=('Background FD/receiving and all response/port drain parameters, geometry/storage, signals/routes/demand, commands and costs. Local rho_crit shared by FD and receiving; merge delta applies only at actual merge cells.' if PHYSICAL else 'All other parameters, background response, mainline FD/receiving capacity, merge coefficient, port draining/storage/travel, signals/routes/demand, actuator rules and waiting costs.'),
        source_pins={str(p.relative_to(ROOT)):c.sha(p) for p in sources}))
    initial=BASE['calibration_values']
    for name,values in [('region_disabled',None),('region_identity',initial)]:
        row,pred=execute(specification(name,values))
        for arm,p in pred.items():assert p==f.load_prediction(REFERENCE/f'refined_guard1_{arm}.json')
    save(O/'compatibility.json',dict(full_json_exact=4,regional_identity_exact=True,disabled_exact=True))


def fit():
    sys.path.insert(0,str(ROOT/'tmp/calibration_dependencies'));from scipy.optimize import least_squares
    initial=BASE['calibration_values'];low=np.array([f.BOUNDS[k][0] for k in KEYS]);span=np.array([f.BOUNDS[k][1]-f.BOUNDS[k][0] for k in KEYS])
    x0=(np.array([initial[k] for k in KEYS])-low)/span
    baseline=c.load(O/(label('region_identity')+'_score.json'));history=[baseline];seen={tuple(x0):np.load(O/(label('region_identity')+'_residual.npy'))};jacobians=[]
    dim=len(seen[tuple(x0)])
    class Budget(Exception):pass
    def objective(x):
        key=tuple(x)
        if key in seen:return seen[key]
        if len(history)>=16:raise Budget()
        values={**{k:initial[k] for k in KEYS},**dict(zip(KEYS,(low+span*x).tolist()))}
        row,_=execute(specification('region_fit_%02d'%len(history),values));history.append(row)
        r=np.load(O/(row['name']+'_residual.npy'))
        if not all(c['passed'] for c in row['numerics'].values()):r=np.full(dim,100.)
        seen[key]=r;save(O/'fit_history.json',history);return r
    def jac(x):
        base=objective(x);cols=[];entries=[]
        for i,key in enumerate(KEYS):
            step=.025 if x[i]+.025<=1 else -.025;z=x.copy();z[i]+=step
            diff=objective(z)-base;cols.append(diff/step);entries.append(dict(parameter=key,absolute_step=step*span[i],response_norm=float(np.linalg.norm(diff))))
        jacobians.append(dict(x=x.tolist(),sensitivity=entries));save(O/'jacobians.json',jacobians)
        return np.stack(cols,axis=1)
    try:
        opt=least_squares(objective,x0,jac=jac,bounds=(np.zeros(len(KEYS)),np.ones(len(KEYS))),max_nfev=3,ftol=.005,xtol=.005,gtol=.005,tr_solver='lsmr')
        stop=dict(status=int(opt.status),message=opt.message,nfev=int(opt.nfev),njev=int(opt.njev))
    except Budget:stop=dict(status=0,message='16 paired candidate budget reached')
    good=[r for r in history if all(c['passed'] for c in r['numerics'].values()) and r['nc_loss']<=1.1*baseline['nc_loss']
          and all(r[k]['objective']<=1.1*baseline[k]['objective'] for k in ('nc_near','nc_far'))]
    selected=min(good,key=lambda r:r['objective'])
    save(O/'selection.json',dict(selected=selected['name'],values=selected['spec']['regional_values'],optimizer=stop,
        selected_training=selected['objective'],baseline_training=baseline['objective'],fit_pairs=len(history),independent_validation=False))
    print('FROZEN',selected['name'],selected['objective'],stop,flush=True)


def negative():
    """Complete signed local sensitivity after a no-improvement budget stop."""
    initial={k:BASE['calibration_values'][k] for k in KEYS}
    baseline=c.load(O/(label('region_identity')+'_score.json'));records=c.load(O/'fit_history.json')
    assert c.load(O/'selection_first_optimizer.json')['selected']==label('region_identity')
    assert len(records)+len(KEYS)+1<=16
    save(O/'negative_protocol.json',dict(reason='All four positive sensitivity probes worsened training; optimizer stopped at nfev3 without improvement. Check negative directions before rejecting regional differentiation.',
        parameters=list(KEYS),fraction_of_original_bound_span=.025,lower_bound_clamp=True,
        maximum_additional_pairs=len(KEYS)+1,final_candidate='Combine only independently improving negative directions; select with unchanged NC guards and training objective.',
        no_late_or_RM_or_both_used=True,source_sha256=c.sha(Path(__file__)),history_sha256=c.sha(O/'fit_history.json')))
    combined=copy.deepcopy(initial)
    def eligible(r):
        return all(x['passed'] for x in r['numerics'].values()) and r['nc_loss']<=1.1*baseline['nc_loss'] and all(r[k]['objective']<=1.1*baseline[k]['objective'] for k in ('nc_near','nc_far'))
    for key in KEYS:
        values=copy.deepcopy(initial);lo,hi,_=f.BOUNDS[key];values[key]=max(lo,values[key]-.025*(hi-lo))
        row,_=execute(specification('region_negative_'+key,values));records.append(row)
        if eligible(row) and row['objective']<baseline['objective']:combined[key]=values[key]
    if combined!=initial:
        row,_=execute(specification('region_negative_combined',combined));records.append(row)
    best=min((r for r in records if eligible(r)),key=lambda r:r['objective'])
    save(O/'signed_history.json',records)
    save(O/'selection.json',dict(selected=best['name'],values=best['spec']['regional_values'],
        optimizer=c.load(O/'selection_first_optimizer.json')['optimizer'],
        followup='Four negative directions and one combined candidate, no convergence claim',fit_pairs=len(records),
        selected_training=best['objective'],baseline_training=baseline['objective'],independent_validation=False))
    print('FROZEN signed',best['name'],best['objective'],flush=True)


def coherent_fit():
    """Recalibrate the linked FD/supply alternative; Q and wave are derived."""
    assert PHYSICAL
    sys.path.insert(0,str(ROOT/'tmp/calibration_dependencies'));from scipy.optimize import least_squares
    keys=('rho_crit','shape','delta_merge');initial=BASE['calibration_values']
    low=np.array([f.BOUNDS[k][0] for k in keys]);span=np.array([f.BOUNDS[k][1]-f.BOUNDS[k][0] for k in keys])
    x0=(np.array([initial[k] for k in keys])-low)/span
    baseline=c.load(O/(label('region_coherent')+'_score.json'));guard=c.load(O/(label('region_identity')+'_score.json'))
    history=[baseline];seen={tuple(x0):np.load(O/(baseline['name']+'_residual.npy'))};dim=len(seen[tuple(x0)]);jacobians=[]
    save(O/'coherent_fit_protocol.json',dict(parameters=list(keys),bounds={k:f.BOUNDS[k][:2] for k in keys},maximum_pairs=12,
        derived='Q=v_free*rho_crit*exp(-1/shape); wave=Q/(rho_jam-rho_crit)',
        Q_wave_not_independent_bounds=True,guard_baseline=guard['name'],train=[2400,2700],no_late_or_other_controls=True,
        source_sha256=c.sha(Path(__file__)),baseline_sha256=c.sha(O/(baseline['name']+'_score.json'))))
    class Budget(Exception):pass
    def objective(x):
        key=tuple(x)
        if key in seen:return seen[key]
        if len(history)>=12:raise Budget()
        values={**{k:initial[k] for k in KEYS},**dict(zip(keys,(low+span*x).tolist()))}
        values['Q']=initial['v_free']*values['rho_crit']*math.exp(-1/values['shape'])
        values['wave']=values['Q']/(initial['rho_jam']-values['rho_crit'])
        row,_=execute(specification('region_coherent_fit_%02d'%len(history),values));history.append(row)
        r=np.load(O/(row['name']+'_residual.npy'))
        if not all(v['passed'] for v in row['numerics'].values()):r=np.full(dim,100.)
        seen[key]=r;save(O/'coherent_fit_history.json',history);return r
    def jac(x):
        base=objective(x);cols=[];entries=[]
        for i,key in enumerate(keys):
            step=.025 if x[i]+.025<=1 else -.025;z=x.copy();z[i]+=step
            diff=objective(z)-base;cols.append(diff/step);entries.append(dict(parameter=key,absolute_step=step*span[i],response_norm=float(np.linalg.norm(diff))))
        jacobians.append(dict(x=x.tolist(),sensitivity=entries));save(O/'coherent_jacobians.json',jacobians)
        return np.stack(cols,axis=1)
    try:
        opt=least_squares(objective,x0,jac=jac,bounds=(np.zeros(3),np.ones(3)),max_nfev=3,ftol=.005,xtol=.005,gtol=.005,tr_solver='lsmr')
        stop=dict(status=int(opt.status),message=opt.message,nfev=int(opt.nfev),njev=int(opt.njev))
    except Budget:stop=dict(status=0,message='12 coherent paired candidate budget reached')
    good=[r for r in history if all(c['passed'] for c in r['numerics'].values()) and r['nc_loss']<=1.1*guard['nc_loss']
          and all(r[k]['objective']<=1.1*guard[k]['objective'] for k in ('nc_near','nc_far'))]
    if good:
        best=min(good,key=lambda r:r['objective']);selection=dict(selected=best['name'],values=best['spec']['regional_values'],selected_training=best['objective'])
    else:selection=dict(selected=None,values=None,selected_training=None)
    save(O/'coherent_selection.json',dict(**selection,optimizer=stop,baseline_training=baseline['objective'],fit_pairs=len(history),independent_validation=False))
    print('FROZEN coherent',selection,stop,flush=True)


def validate(selection_file='selection.json',name='region_selected_actions'):
    selected=c.load(O/selection_file);assert selected['selected'] is not None
    row,pred=execute(specification(name,selected['values'],f.ARMS))
    for a in ('none','vsl'):assert pred[a]==f.load_prediction(O/selected['selected']/f'refined_guard1_{a}.json')
    rows=[]
    for role,folder in [('common',REFERENCE),('regional',O/label(name))]:
        pp={a:f.load_prediction(folder/f'refined_guard1_{a}.json') for a in ('none','vsl')}
        for phase,lo,hi in [('train',0,10),('late',10,15)]:
            _,rr=v.response_metrics({a:c.predicted(p) for a,p in pp.items()},lo,hi)
            for zone,cells in [('near',NEAR),('far',FAR)]:
                rows.append(dict(role=role,phase=phase,zone=zone,**c.score(pp['none'],lo,hi,cells),**rr))
    old=c.load(K/('segment_resolution_20260921_cal_'+REFERENCE.name)/'result.json')
    new=c.load(K/('segment_resolution_20260921_cal_'+label(name))/'result.json')
    native=c.load(B.parent/'response_chain_20260921/qualification.json')['gains']
    gains={a:dict(actual_1s=native[a]['actual'],baseline_1s=old['deltas'][a],regional_1s=new['deltas'][a]) for a in f.ARMS[1:]}
    forecasts=sum(c.load(p)['forecasts'] for p in O.glob('*/refined_guard1_receipt.json'))
    prefix='coherent_' if selection_file.startswith('coherent') else ''
    save(O/(prefix+'validation.json'),dict(forecasts=forecasts,new_native=0,production_adopted=False,qualified=False,
        metrics=rows,gains=gains,common5s_costs=row['costs5s'],all_owned_calculations_terminal=True))
    table(O/(prefix+'state_metrics.csv'),rows)
    print(json.dumps(dict(forecasts=forecasts,late=[x for x in rows if x['phase']=='late'],
        gains={a:{k:v['total'] for k,v in r.items()} for a,r in gains.items()}),ensure_ascii=False),flush=True)


if __name__=='__main__':{'prepare':prepare,'fit':fit,'negative':negative,'validate':validate,'coherent-fit':coherent_fit,
    'validate-coherent':lambda:validate('coherent_selection.json','region_coherent_actions')}[sys.argv[1]]()
