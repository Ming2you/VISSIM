"""Correct the113 rate-fit population; keep the same two-rate hypothesis.

The former fit conditioned on remaining in the same cell, whereas its passive
application evolves every old vehicle before accepted transport. Here the next
speed label may be in any mainline cell. Missing next labels stay censored.
"""
import ctypes
import ctypes.wintypes
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OLD=HERE.parent/'stop_law113'


def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(name,x):(HERE/name).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert not (HERE/'protocol.json').exists(), 'Do not repeat population correction'
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=ctypes.wintypes.HANDLE
    kernel.SetPriorityClass.argtypes=[ctypes.wintypes.HANDLE,ctypes.wintypes.DWORD]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    import numpy as np
    from scipy.optimize import minimize
    protocol=read(OLD/'protocol.json')
    protocol.update(previous_goal_turn='PROGRESS:113 completed fits and four forecasts but rejected autonomous stopped-stock closure.',
        scope='Same cells16..23/threshold5kmh/features, but follow old vehicles to ANY next mainline cell rather than condition on staying in old cell.',
        hypothesis='Conditioning the fitted reaction rates on remaining in a cell excludes many moving vehicles, unlike reaction-before-transport deployment.',
        budget=dict(fits=2,parameters_each=2,conditional_inputs=6,autonomous_if_conditional_pass=4),
        censoring='Vehicles absent from next mainline cache are missing labels, not assumed to stop or restart. Quantify counts.',
        next_gate='Same113 conditional macro gate; then4fixed450 passive checks, plus>=20% reduction of43/67 averageB RMSE vs113state and>=20% reduction of meaningful67 VSL delta error. No coefficient/feature extension.',
        no_production_change=True,exact_parent_helper_sha256=sha(OLD/'passive.py'))
    save('protocol.json',protocol)
    for path,h in protocol['core_pins'].items():assert sha(path)==h
    geometry=read(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json')
    lane={r['cell']:r['lane_km'] for r in geometry['cells'] if r['road']=='FW_E'}
    critical={int(k):v for k,v in protocol['critical'].items()}
    free={int(k):v for k,v in protocol['v_free'].items()}
    maximum=protocol['rho_max']
    rows=[];audit=[];missing=0;examined=0
    for case,s in protocol['input_pins'].items():
        assert sha(ROOT/s['path'])==s['sha256']
        with gzip.open(ROOT/s['path'],'rt',encoding='utf-8') as f:data=json.load(f)
        frames={float(t):v for t,v in data['frames'].items()};times=sorted(frames)
        totals=dict(same_exposure=0,cross_exposure=0,missing_next=0,same_onset=0,cross_onset=0,same_restart=0,cross_restart=0)
        for t,tn in zip(times,times[1:]):
            assert abs(tn-t-5)<1e-7
            old,new=frames[t],frames[tn]
            grouped={i:{k:r for k,r in old.items() if r[0]==i} for i in range(16,25)}
            for i in range(16,24):
                a,down=grouped[i],grouped[i+1]
                known={k:r for k,r in a.items() if k in new}
                nb=sum(r[1]<5 for r in known.values());nm=len(known)-nb
                onset=sum(r[1]>=5 and new[k][1]<5 for k,r in known.items())
                release=sum(r[1]<5 and new[k][1]>=5 for k,r in known.items())
                for k,r in known.items():
                    assert new[k][0]>=i, 'Unexpected backward cell transition'
                    prefix='same' if new[k][0]==i else 'cross'
                    totals[prefix+'_exposure']+=1
                    totals[prefix+'_onset']+=int(r[1]>=5 and new[k][1]<5)
                    totals[prefix+'_restart']+=int(r[1]<5 and new[k][1]>=5)
                totals['missing_next']+=len(a)-len(known)
                n,nd=len(a),len(down)
                v=sum(r[1] for r in a.values())/n if n else free[i]
                vd=sum(r[1] for r in down.values())/nd if nd else free[i+1]
                rho=n/lane[i];rd=nd/lane[i+1]
                fd=sum(r[1]<5 for r in down.values())/nd if nd else 0.
                pressure=(rho/critical[i])*(fd+max(v-vd,0.)/free[i]+rd/maximum)
                room=max(vd,0.)/free[i+1]*max(1-rd/maximum,0.)
                rows.append(dict(case=case,cell=i,start=t,end=tn,window150=int(round(t-times[0],6)//150),
                    moving_exposure=nm,stopped_exposure=nb,onset=onset,release=release,pressure=pressure,room=room))
        total=sum(totals[k] for k in ('same_exposure','cross_exposure','missing_next'))
        audit.append(dict(case=case,**totals,excluded_by_old_stayer_condition=totals['cross_exposure']/(total-totals['missing_next']),
                          censored_fraction=totals['missing_next']/total))
        missing+=totals['missing_next'];examined+=total
    save('population.json',dict(cases=audit,total_exposures=examined,missing_next=missing,censored_fraction=missing/examined))
    # No feature changes: compare exact rows in the first113 data file.
    former=read(OLD/'rows.json');assert len(former)==len(rows)==6240
    assert all(all(a[k]==b[k] for k in ('case','cell','start','end','window150','pressure','room')) for a,b in zip(rows,former))
    assert all(a['moving_exposure']>=b['moving_exposure'] and a['stopped_exposure']>=b['stopped_exposure'] for a,b in zip(rows,former))
    save('rows.json',rows)
    exposure=np.array([[r['moving_exposure'],r['stopped_exposure']] for r in rows],dtype=float)
    y=np.array([[r['onset'],r['release']] for r in rows],dtype=float)
    features=np.array([[r['pressure'],r['room']] for r in rows])
    keys=sorted({(r['case'],r['window150']) for r in rows})
    groups=[np.array([r['case']==c and r['window150']==w for r in rows]) for c,w in keys]
    actual=np.array([y[g].sum(axis=0) for g in groups]);train=np.array([c.startswith('29_') for c,w in keys])
    initial={r['model']:r['coefficients'] for r in read(OLD/'macro_results.json')['fits']}
    def aggregate(theta,x):
        rates=np.asarray(theta)*x;total=rates.sum(axis=1)
        f=np.divide(-np.expm1(-5*total),total,out=np.full_like(total,5.),where=total>0)
        p=rates*f[:,None];assert np.all(p>=0) and np.all(p.sum(axis=1)<=1+1e-12)
        pred=p*exposure
        return np.array([pred[g].sum(axis=0) for g in groups])
    def error(pred):
        e=pred-actual
        return ((e[:,0]/40)**2+(e[:,1]/40)**2+((e[:,0]-e[:,1])/20)**2)/3
    fits=[];windows=[]
    for name,x in [('constant',np.ones_like(features)),('state',features)]:
        started=time.perf_counter()
        f=minimize(lambda z:float(error(aggregate(np.exp(z),x))[train].mean()),np.log(initial[name]),method='L-BFGS-B',
                   bounds=[(math.log(1e-5),math.log(2.))]*2,options=dict(maxiter=40,maxfun=150,ftol=1e-10,gtol=1e-7))
        theta=np.exp(f.x);pred=aggregate(theta,x)
        result=dict(model=name,coefficients=theta.tolist(),success=bool(f.success),message=str(f.message),nfev=f.nfev,nit=f.nit,
                    elapsed_seconds=time.perf_counter()-started,by_seed={})
        for seed in ('29','43','67'):
            selected=np.array([c.startswith(seed+'_') for c,w in keys]);e=pred[selected]-actual[selected]
            result['by_seed'][seed]=dict(macro_loss=float(error(pred)[selected].mean()),net_rmse=float(np.sqrt(np.mean((e[:,0]-e[:,1])**2))))
        fits.append(result)
        for key,a,p in zip(keys,actual,pred):windows.append(dict(model=name,case=key[0],window150=key[1],actual=a.tolist(),predicted=p.tolist()))
        save('fit_partial.json',fits)
    gates=[]
    for seed in ('43','67'):
        b,s=(f['by_seed'][seed] for f in fits)
        gates.append(dict(seed=seed,macro_improvement=1-s['macro_loss']/b['macro_loss'],net_improvement=1-s['net_rmse']/b['net_rmse'],
                          passed=s['macro_loss']<=.8*b['macro_loss'] and s['net_rmse']<=b['net_rmse']))
    result=dict(fits=fits,windows=windows,gates=gates,decision='CONDITIONAL_PASS_ONLY' if all(g['passed'] for g in gates) and all(f['success'] for f in fits) else 'DO_NOT_CONNECT')
    save('macro_results.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='windows'}),flush=True)
    if result['decision']=='CONDITIONAL_PASS_ONLY':
        spec=importlib.util.spec_from_file_location('passive_reuse114',OLD/'passive.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.HERE=HERE # Reuse the unchanged diagnostic; no copied runner or adapter.
        module.main()
    assert sha(OLD/'passive.py')==protocol['exact_parent_helper_sha256']
    for p,h in protocol['core_pins'].items():assert sha(p)==h
    save('fit_status.json',dict(status='complete_pending_assessment',fits=2,forecasts=4 if result['decision']=='CONDITIONAL_PASS_ONLY' else 0))


if __name__=='__main__':main()
