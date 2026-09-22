"""Joint, bounded calibration of all continuous coefficients in both hybrids.

The conserved plant/runner is reused. NC alone selects coefficients; commands
and late traffic are validation. Full candidate predictions are gzip archives.
"""
import copy,gzip,hashlib,json,math,subprocess,sys,time
from pathlib import Path
import numpy as np
import calibrate as c
from prepare import save,table
B=c.B;O=B/'full_calibration_v1';K=B.parent/'cohort_dynamics_20260920';ROOT=c.ROOT
ARMS=('none','rm_ramp','vsl','both')
# Explicit diagnostic bounds; not claims of parameter identification.
BOUNDS={
 'v_free':(95.,135.,120.),'rho_crit':(18.,50.,27.),'shape':(.8,3.,1.6),'rho_jam':(130.,240.,180.),
 'tau_acc':(12.,150.,30.),'tau_dec':(12.,150.,30.),'nu_high':(3.,90.,17.5),'nu_low':(3.,90.,17.5),
 'nu_congested':(.25,2.,1.),'kappa':(5.,100.,35.),'delta_merge':(0.,1.,1.),'lane_phi':(0.,6.,3.),
 'Q':(1800.,2800.,2420.),'wave':(5.,30.,15.),'theta':(0.,.25,0.),'spill_gamma':(.25,2.,1.),'spill_b':(1.,8.,4.)}
PORT_CELLS=sorted({p['to_cell'] if p['kind']=='ramp' else p['from_cell'] for p in c.G['boundaries']
    if p['road']=='FW_E' and p['kind'] in ('ramp','offramp')})
SCOPE=c.load(B/'hadiuzzaman_v1/scope_protocol.json')['cells']
with np.load(c.O/'observed_none.npz') as f:OBS={k:f[k] for k in f.files}


def load_prediction(path):
    if path.exists():return c.load(path)
    with gzip.open(str(path)+'.gz','rt',encoding='utf-8') as f:return json.load(f)


def residual(p):
    pred=c.predicted(p);errors=[[],[],[]]
    for i in c.CELLS:
        n=len(c.WIDTHS[i]);a=OBS['n'][:10,i,:n];b=pred['n'][:10,i,:n];mask=a>=1
        av=np.divide(OBS['mom'][:10,i,:n],a,out=np.zeros_like(a),where=a>0)
        bv=np.divide(pred['mom'][:10,i,:n],b,out=np.zeros_like(b),where=b>0)
        errors[0].extend(((bv-av)/20)[mask]);errors[1].extend(((b-a)/5).ravel())
        errors[2].extend((pred['q'][:10,i]-OBS['q'][:10,i])*120/500)
    return np.concatenate([np.asarray(x)/math.sqrt(len(x)) for x in errors])


def specification(name,values,family,law='fd_cap',nc=True):
    v=values;critical=v['Q']/v['v_free'] if family=='wang' else v['rho_crit']
    wave=v['Q']/(v['rho_jam']-critical) if family=='wang' else v['wave']
    spec=dict(name=name,output_group=O.name,parent_cells=list(range(21)),tau_sec=30.,nu_km2_h=v['nu_high'],
        rho_multiplier=1.,delta_merge=v['delta_merge'],nc_only=nc,compress_predictions=True,audit_effective=True,calibration_values=copy.deepcopy(v),
        physical_coefficients=dict(v_free=v['v_free'],rho_crit=v['rho_crit'],rho_max=v['rho_jam'],
            metanet_a_m=v['shape'],metanet_kappa_veh_km_lane=v['kappa'],metanet_delta_merge=v['delta_merge'],
            freeway_lane_drop_phi=v['lane_phi']),
        state_response=dict(relaxation=dict(acceleration_sec=v['tau_acc'],deceleration_sec=v['tau_dec']),
            anticipation=dict(downstream_ge_local=v['nu_high'],downstream_lt_local=v['nu_low']),
            congested_nu_multiplier=v['nu_congested']),
        port_response=dict(merge_speed=True,diverge_density=True,spillback=dict(mode='envelope',gamma=v['spill_gamma'],b=v['spill_b'])),
        hadiuzzaman=dict(ctm=True,relaxation=law,relaxation_cells=SCOPE,congested_branch='capacity_critical' if family=='wang' else 'fixed_wave',
            cells=[dict(capacity_vphpl=v['Q'],wave_kmh=wave,rho_critical=critical,theta=v['theta'] if i in PORT_CELLS else 0.) for i in range(31)]))
    return spec


def execute(spec):
    path=O/(spec['name']+'.json');score=O/(spec['name']+'_score.json')
    if score.exists():
        r=c.load(score);assert r['spec']==spec;return r
    save(path,spec);t=time.perf_counter()
    with (O/(spec['name']+'_process.log')).open('x',encoding='utf-8') as f:
        proc=subprocess.run([sys.executable,'-B','-X','utf8',str(B/'run.py'),'refined_guard1',str(path)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    row=dict(name=spec['name'],spec=spec,exit_code=proc.returncode,seconds=time.perf_counter()-t)
    if proc.returncode==0:
        p=load_prediction(O/spec['name']/'refined_guard1_none.json');row.update(train=c.score(p),numerics=c.screen(p))
        r=residual(p);assert abs(float(r@r)-row['train']['objective'])<1e-8
        np.save(O/(spec['name']+'_residual.npy'),r)
        if spec.get('audit_effective'):
            entries=c.load(O/spec['name']/'effective_config.json');assert len(entries)==(1 if spec['nc_only'] else 4)
            for e in entries:
                assert e['scalar']==spec['physical_coefficients']
                for x in e['rows']:
                    for key in ('v_free','rho_crit','rho_max','metanet_a_m','metanet_kappa_veh_km_lane'):
                        assert x[key]==spec['physical_coefficients'][key]
                assert e['state_response']['FW_E']==spec['state_response']
                assert e['receiving']['FW_E']==spec['hadiuzzaman'] and e['port_response']['FW_E']==spec['port_response']
    save(score,row);print(spec['name'],row.get('train',{}).get('objective'),row.get('numerics',{}).get('passed'),proc.returncode,flush=True)
    return row


def fit(family,law,resume=False):
    sys.path.insert(0,str(ROOT/'tmp/calibration_dependencies'))
    from scipy.optimize import least_squares
    base_label=family+'_'+law;label=base_label+('_r2' if resume else '')
    keys=[k for k in BOUNDS if family!='wang' or k!='wave']
    lower=np.array([BOUNDS[k][0] for k in keys]);span=np.array([BOUNDS[k][1]-BOUNDS[k][0] for k in keys])
    x0=np.array([(BOUNDS[k][2]-BOUNDS[k][0])/(BOUNDS[k][1]-BOUNDS[k][0]) for k in keys])
    if resume:
        initial=c.load(O/(base_label+'_selected.json'))['selected']['spec']['calibration_values']
        x0=np.array([(initial[k]-BOUNDS[k][0])/(BOUNDS[k][1]-BOUNDS[k][0]) for k in keys])
    seen={};history=[];jacobians=[]
    def decode(x):return {**{k:a[2] for k,a in BOUNDS.items()},**dict(zip(keys,(lower+span*x).tolist()))}
    def objective(x):
        key=tuple(float(t) for t in x)
        if key in seen:return seen[key]
        spec=specification(f'fc_{label}_{len(history):03}',decode(x),family,law)
        row=execute(spec);history.append(row)
        good=row['exit_code']==0 and row['numerics']['passed']
        r=np.load(O/(spec['name']+'_residual.npy')) if good else np.full(1003,100.)
        # Observation mask fixes residual dimensions independently of predictions.
        assert len(r)==1003
        seen[key]=r
        save(O/(label+'_history.json'),history)
        return r
    def jac(x):
        base=objective(x);cols=[];audit=[]
        for j,key in enumerate(keys):
            probe=x.copy();step=.025 if x[j]+.025<=1 else -.025;probe[j]+=step
            delta=objective(probe)-base;cols.append(delta/step)
            audit.append(dict(parameter=key,normalized_step=step,response_norm=float(np.linalg.norm(delta)),
                absolute_step=step*span[j]))
        jacobians.append(dict(x=x.tolist(),sensitivity=audit))
        save(O/(label+'_sensitivities.json'),jacobians)
        return np.stack(cols,axis=1)
    # Bounded joint least squares. All independent coefficients participate;
    # no claim of global optimum or identification from a single trajectory.
    result=least_squares(objective,x0,jac=jac,bounds=(np.zeros(len(keys)),np.ones(len(keys))),
        max_nfev=6,ftol=.005,xtol=.005,gtol=.005,tr_solver='lsmr')
    good=[r for r in history if r['exit_code']==0 and r['numerics']['passed']]
    selected=min(good,key=lambda r:r['train']['objective'])
    save(O/(label+'_selected.json'),dict(selected=selected,optimizer=dict(status=int(result.status),message=result.message,
        nfev=int(result.nfev),njev=int(result.njev),cost=float(result.cost)),scope=keys))
    print('FROZEN',label,selected['name'],selected['train']['objective'],flush=True)


def baseline():
    spec=dict(name='fc_disabled',output_group=O.name,parent_cells=c.TARGET,tau_sec=12,nu_km2_h=35,
        rho_multiplier=1.,delta_merge=1.,nc_only=False,compress_predictions=True)
    row=execute(spec);assert row['exit_code']==0
    for arm in ARMS:assert load_prediction(O/spec['name']/f'refined_guard1_{arm}.json')==c.load(B/f'refined_guard1_{arm}.json')
    save(O/'baseline_exact.json',dict(arms=list(ARMS),compressed_prediction_exact=True))


def main():
    if sys.argv[1]=='baseline':baseline();return
    if sys.argv[1] in ('fit','resume'):fit(sys.argv[2],sys.argv[3],resume=sys.argv[1]=='resume');return
    if sys.argv[1]=='actions':
        label=sys.argv[2];r=c.load(O/(label+'_selected.json'))['selected'];spec=copy.deepcopy(r['spec'])
        spec.update(name='fc_'+label+'_actions',nc_only=False)
        execute(spec)
        assert load_prediction(O/spec['name']/'refined_guard1_none.json')==load_prediction(O/r['name']/'refined_guard1_none.json')
        return


if __name__=='__main__':main()
