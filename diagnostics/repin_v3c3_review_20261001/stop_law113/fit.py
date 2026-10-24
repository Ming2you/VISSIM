"""One two-coefficient, state-dependent stopped/moving transition diagnostic.

No controller/plant edits, FZP reads, or forward traffic forecasts. Both fitted
rates are shared across cells, seeds and policies. This is a local statistical
closure motivated by separate onset/release processes, not Zhou's full model.
"""
import ctypes
import ctypes.wintypes
import gzip
import hashlib
import json
import math
from pathlib import Path
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
R=HERE.parent
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'


def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,x):
    (HERE/name).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    assert not (HERE/'protocol.json').exists(), 'No repeat or adaptive feature sweep'
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=ctypes.wintypes.HANDLE
    kernel.SetPriorityClass.argtypes=[ctypes.wintypes.HANDLE,ctypes.wintypes.DWORD]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    import numpy as np
    from scipy.optimize import minimize
    from evaluation.controllers import lane_plant_runtime as lpr
    context=lpr.load_sources(R/'retained10638/candidate_manifest.json')
    net=context['component']._config('FW_E',context['parameters']['by_direction']['FW_E']).network
    geometry=read(I/'selected/port_gain/geometry.json')
    cells={r['cell']:r for r in geometry['cells'] if r['road']=='FW_E'}
    sources=read(R/'stopped_lane106/protocol.json')['inputs']
    critical={i:net.freeway_segment_params['FW_E'][i]['rho_crit'] for i in range(16,24)}
    free={i:net.freeway_segment_params['FW_E'][i]['v_free'] for i in range(16,25)}
    protocol=dict(previous_goal_turn='PROGRESS:112 established both onset and release change; sub5s merge timing has small sensitivity.',
        question='Can one small shared state-dependent law explain observed stop/restart counts outside training, without VSL-specific coefficients?',
        train=['29_none','29_vsl'],evaluation=['43_none','43_vsl','67_release','67_release_vsl90'],
        scope='FW_E physical zero-based16..23, speeds below5kmh. Only common vehicles remaining in the same cell at both five-second frames.',
        equations=dict(stop_pressure='(rho_i/rho_crit_i)*(B_down/N_down + max(v_i-v_down,0)/v_free_i + rho_down/rho_max)',
            release_room='max(v_down,0)/v_free_down * max(1-rho_down/rho_max,0)',
            rates='a=theta_stop*stop_pressure; b=theta_release*release_room',
            transition='p01=a/(a+b)*(1-exp(-(a+b)*5)); p10=b/(a+b)*(1-exp(-(a+b)*5))'),
        baseline='One common constant two-rate Markov law, fitted by pooled training transition proportions; no per-cell/arm coefficients.',
        fits=1,fitted_coefficients=2,bounds_rates_per_second=[1e-5,2.],max_iterations=40,max_function_evaluations=150,
        fixed_features=True,thresholds_not_tuned=True,critical=critical,v_free=free,rho_max=net.rho_max,
        gates='For each evaluation seed: conditional NLL improves>=10%,150s transition-count RMSE improves>=20%,and aggregate onset/restart delta signs correct when |observed delta|>=10events.',
        limitations=['Previously inspected seeds, not blind.','Five-second endpoint transitions can hide repeated stops/restarts.',
            'Current observed traffic states feed this diagnostic, not autonomous future states.',
            'Stayer membership defines labelled exposure and uses the next frame; not deployable unmodified.',
            'Not Zhou2022 equations or a proof that this state improves discharge, TTT or control selection.',
            'No production change, no future observation injected into a plant, no new native/FZP.'],
        input_pins={k:dict(path=v['path'],sha256=v['sha256']) for k,v in sources.items()},
        core_pins=read(R/'merge_phase109/protocol.json')['protected_sha256'])
    save('protocol.json',protocol)
    for p,h in protocol['core_pins'].items():assert sha(p)==h
    rows=[];stock_balances=0
    for case,spec in sources.items():
        path=ROOT/spec['path'];assert sha(path)==spec['sha256']
        with gzip.open(path,'rt',encoding='utf-8') as f:data=json.load(f)
        assert data['fields'][:4]==['cell','speed_kmh','x_m','lane'], data['fields']
        times=sorted(map(float,data['frames']));frames={float(t):v for t,v in data['frames'].items()}
        for t,tn in zip(times,times[1:]):
            assert abs(tn-t-5)<1e-7
            old,new=frames[t],frames[tn]
            grouped={i:{v:r for v,r in old.items() if r[0]==i} for i in range(16,25)}
            for i in range(16,24):
                a=grouped[i];down=grouped[i+1];b={v:r for v,r in new.items() if r[0]==i}
                la={v for v,r in a.items() if r[1]<5};lb={v for v,r in b.items() if r[1]<5}
                common=a.keys()&b.keys();nb=len(la&common);nm=len(common-la)
                onset=len((lb-la)&common);release=len((la-lb)&common)
                low_in=len(lb-a.keys());low_out=len(la-b.keys())
                assert len(lb)==len(la)+onset-release+low_in-low_out;stock_balances+=1
                n=len(a);nd=len(down)
                v=sum(r[1] for r in a.values())/n if n else free[i]
                vd=sum(r[1] for r in down.values())/nd if nd else free[i+1]
                rho=n/cells[i]['lane_km'];rd=nd/cells[i+1]['lane_km']
                fd=sum(r[1]<5 for r in down.values())/nd if nd else 0.
                pressure=(rho/critical[i])*(fd+max(v-vd,0.)/free[i]+rd/net.rho_max)
                room=max(vd,0.)/free[i+1]*max(1-rd/net.rho_max,0.)
                rows.append(dict(case=case,cell=i,start=t,end=tn,window150=int(round(t-times[0],6)//150),
                    moving_exposure=nm,stopped_exposure=nb,onset=onset,release=release,pressure=pressure,room=room))
    train=np.array([r['case'].startswith('29_') for r in rows])
    x=np.array([[r['pressure'],r['room']] for r in rows])
    exposure=np.array([[r['moving_exposure'],r['stopped_exposure']] for r in rows],dtype=float)
    y=np.array([[r['onset'],r['release']] for r in rows],dtype=float)
    def probability(theta,features):
        rates=np.array(theta)*features;total=rates.sum(axis=1)
        factor=np.divide(-np.expm1(-5*total),total,out=np.full_like(total,5.),where=total>0)
        result=rates*factor[:,None]
        assert np.all(result>=0) and np.all(result<=1+1e-12) and np.all(result.sum(axis=1)<=1+1e-12)
        return result
    def terms(p):
        p=np.clip(p,1e-12,1-1e-12)
        return -y*np.log(p)-(exposure-y)*np.log1p(-p)
    counts=y[train].sum(axis=0);exposures=exposure[train].sum(axis=0);proportions=counts/exposures
    assert 0<proportions.sum()<1
    total_rate=-math.log1p(-proportions.sum())/5
    constant=proportions/proportions.sum()*total_rate
    constant_p=probability(constant,np.ones_like(x))
    initial=np.clip(constant/np.average(x[train],axis=0,weights=exposure[train].sum(axis=1)),1e-5,2.)
    def objective(logtheta):return float(terms(probability(np.exp(logtheta),x))[train].sum()/exposure[train].sum())
    before=time.perf_counter()
    fitted=minimize(objective,np.log(initial),method='L-BFGS-B',bounds=[(math.log(1e-5),math.log(2.))]*2,
                    options=dict(maxiter=40,maxfun=150,ftol=1e-10,gtol=1e-7))
    theta=np.exp(fitted.x);fitted_p=probability(theta,x)
    save('fit.json',dict(theta_stop=theta[0],theta_release=theta[1],constant_rates=constant.tolist(),
                        converged=bool(fitted.success),message=str(fitted.message),nfev=fitted.nfev,nit=fitted.nit,
                        elapsed_seconds=time.perf_counter()-before,train_nll=objective(fitted.x)))
    for row,pa,pb in zip(rows,constant_p,fitted_p):
        row['baseline_probability']=pa.tolist();row['state_probability']=pb.tolist()
    save('rows.json',rows)
    evaluation=[];windows=[]
    for seed in ('29','43','67'):
        mask=np.array([r['case'].startswith(seed+'_') for r in rows])
        scores={}
        for name,p in [('constant',constant_p),('state',fitted_p)]:
            pred=p*exposure;groups={}
            for index,r in enumerate(rows):
                if not mask[index]:continue
                key=(r['case'],r['window150']);g=groups.setdefault(key,dict(observed=np.zeros(2),predicted=np.zeros(2)))
                g['observed']+=y[index];g['predicted']+=pred[index]
            error=np.array([g['predicted']-g['observed'] for g in groups.values()])
            scores[name]=dict(nll=float(terms(p)[mask].sum()/exposure[mask].sum()),
                              transition_rmse150=float(np.sqrt(np.mean(error**2))))
            for (case,window),g in groups.items():windows.append(dict(model=name,case=case,window150=window,observed=g['observed'].tolist(),predicted=g['predicted'].tolist()))
        nll_improvement=1-scores['state']['nll']/scores['constant']['nll']
        rmse_improvement=1-scores['state']['transition_rmse150']/scores['constant']['transition_rmse150']
        cases=sorted({r['case'] for r in rows if r['case'].startswith(seed+'_')})
        deltas={}
        for name,p in [('constant',constant_p),('state',fitted_p)]:
            sums=[]
            for case in cases:
                sel=np.array([r['case']==case for r in rows]);sums.append((y[sel].sum(axis=0),(p*exposure)[sel].sum(axis=0)))
            ad=sums[1][0]-sums[0][0];pd=sums[1][1]-sums[0][1]
            deltas[name]=dict(cases=cases,actual=ad.tolist(),predicted=pd.tolist(),
                              meaningful_signs=bool(np.all((np.abs(ad)<10)|(ad*pd>0))))
        evaluation.append(dict(seed=seed,scores=scores,deltas=deltas,nll_improvement=nll_improvement,rmse_improvement=rmse_improvement,
                               passed=nll_improvement>=.1 and rmse_improvement>=.2 and deltas['state']['meaningful_signs']))
    save('results.json',dict(evaluation=evaluation,windows=windows,observed_balances=stock_balances,observed_rows=len(rows),
                            further_integration_justified=bool(fitted.success and all(r['passed'] for r in evaluation if r['seed']!='29')),
                            autonomous_gain_qualified=False))
    for p,h in protocol['core_pins'].items():assert sha(p)==h
    print(json.dumps(dict(fit=read(HERE/'fit.json'),evaluation=evaluation),ensure_ascii=False))


if __name__=='__main__':main()
