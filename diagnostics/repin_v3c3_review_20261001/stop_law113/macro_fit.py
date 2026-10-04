"""Same two rates/features; fit the user's150s macro criterion directly."""
import json
import math
from pathlib import Path
import time

HERE=Path(__file__).resolve().parent
def read(name):return json.loads((HERE/name).read_text(encoding='utf-8'))
def save(name,x):(HERE/name).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    assert not (HERE/'macro_protocol.json').exists(),'No repeat or broader search'
    import numpy as np
    from scipy.optimize import minimize
    rows=read('rows.json');previous=read('fit.json')
    save('macro_protocol.json',dict(
        reason='Conditional NLL weights all vehicle transitions, but user prioritizes150s aggregate queue/flow. Initial law improves gross count RMSE; check net onset-minus-release directly.',
        same_features_and_two_rates=True,new_cells=False,new_parameter_range=False,
        max_fits=2,models=['constant common rates','same fixed state features'],training='seed29 none/vsl only',
        evaluation='43/67 already inspected, explicitly non-blind. No evaluation data in objective.',
        objective='Mean per150s of ((onset error/40)^2+(restart error/40)^2+(net-generation error/20)^2)/3',
        bounds_rates_per_second=[1e-5,2.],maxiter=40,maxfun=150,
        accept='For each evaluation seed,150s macro loss improves>=20% vs macro-fitted common constant, and net-generation RMSE is no worse. No adoption from conditional success.',
        stop='Two fixed fits then assess. No threshold/feature/region/coefficient expansion.',
        physical_limit='Future observed traffic state and labelled stayer exposure: conditional diagnostic, not a450s autonomous plant or TTT response test.'))
    exposure=np.array([[r['moving_exposure'],r['stopped_exposure']] for r in rows],dtype=float)
    y=np.array([[r['onset'],r['release']] for r in rows],dtype=float)
    features=np.array([[r['pressure'],r['room']] for r in rows])
    keys=sorted({(r['case'],r['window150']) for r in rows})
    groups=[np.array([r['case']==c and r['window150']==w for r in rows]) for c,w in keys]
    actual=np.array([y[g].sum(axis=0) for g in groups]);train=np.array([c.startswith('29_') for c,w in keys])
    def aggregate(theta,x):
        rates=np.asarray(theta)*x;total=rates.sum(axis=1)
        f=np.divide(-np.expm1(-5*total),total,out=np.full_like(total,5.),where=total>0)
        p=rates*f[:,None];assert np.all(p>=0) and np.all(p.sum(axis=1)<=1+1e-12)
        expected=p*exposure
        return np.array([expected[g].sum(axis=0) for g in groups])
    def error(pred):
        e=pred-actual;net=e[:,0]-e[:,1]
        return ((e[:,0]/40)**2+(e[:,1]/40)**2+(net/20)**2)/3
    results=[];windows=[]
    for name,x,initial in [('constant',np.ones_like(features),previous['constant_rates']),
                           ('state',features,[previous['theta_stop'],previous['theta_release']])]:
        started=time.perf_counter()
        fitted=minimize(lambda z:float(error(aggregate(np.exp(z),x))[train].mean()),np.log(initial),method='L-BFGS-B',
                         bounds=[(math.log(1e-5),math.log(2.))]*2,options=dict(maxiter=40,maxfun=150,ftol=1e-10,gtol=1e-7))
        theta=np.exp(fitted.x);pred=aggregate(theta,x)
        result=dict(model=name,coefficients=theta.tolist(),success=bool(fitted.success),message=str(fitted.message),
                    nfev=fitted.nfev,nit=fitted.nit,elapsed_seconds=time.perf_counter()-started,by_seed={})
        for seed in ('29','43','67'):
            selected=np.array([c.startswith(seed+'_') for c,w in keys]);e=pred[selected]-actual[selected]
            result['by_seed'][seed]=dict(macro_loss=float(error(pred)[selected].mean()),
                onset_rmse=float(np.sqrt(np.mean(e[:,0]**2))),restart_rmse=float(np.sqrt(np.mean(e[:,1]**2))),
                net_rmse=float(np.sqrt(np.mean((e[:,0]-e[:,1])**2))),
                onset_bias=float(e[:,0].mean()),restart_bias=float(e[:,1].mean()),net_bias=float((e[:,0]-e[:,1]).mean()))
        for key,a,p in zip(keys,actual,pred):windows.append(dict(model=name,case=key[0],window150=key[1],actual=a.tolist(),predicted=p.tolist(),
                                                                actual_net=float(a[0]-a[1]),predicted_net=float(p[0]-p[1])))
        results.append(result);save('macro_partial.json',results)
    checks=[]
    for seed in ('43','67'):
        base=results[0]['by_seed'][seed];state=results[1]['by_seed'][seed]
        checks.append(dict(seed=seed,macro_improvement=1-state['macro_loss']/base['macro_loss'],
                          net_improvement=1-state['net_rmse']/base['net_rmse'],
                          passed=state['macro_loss']<=.8*base['macro_loss'] and state['net_rmse']<=base['net_rmse']))
    summary=dict(fits=results,windows=windows,gates=checks,
                 decision='CONDITIONAL_PASS_ONLY' if all(r['success'] for r in results) and all(c['passed'] for c in checks) else 'DO_NOT_CONNECT',
                 autonomous_qualified=False,production_changed=False,new_native=0)
    save('macro_results.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k!='windows'},ensure_ascii=False))


if __name__=='__main__':main()
