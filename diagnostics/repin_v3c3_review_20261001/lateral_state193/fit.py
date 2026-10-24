"""One bounded current-state interval-likelihood fit; observed gate precedes rollout."""
import gzip
import json
import math
import time
from pathlib import Path
import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from diagnostics.repin_v3c3_review_20261001.lateral_sampling192.fit import region, transition, EDGES
from diagnostics.repin_v3c3_review_20261001.state_lateral168.fit import features

HERE = Path(__file__).resolve().parent
LOW = math.log(1e-5)
HIGH = math.log(.05)


def probabilities(x, theta, dt=5.):
    rates = np.exp(np.clip(x @ theta, LOW, HIGH))
    q = np.zeros((len(x), 3, 3))
    for index, (g, k) in enumerate(EDGES):
        q[:, g, k] = rates[:, index]
    for g in range(3):
        q[:, g, g] = -q[:, g].sum(axis=1)
    nu = -np.diagonal(q, axis1=1, axis2=2).min(axis=1)
    a = np.eye(3)[None] + q / nu[:, None, None]
    term = np.broadcast_to(np.eye(3), a.shape).copy()
    weight = np.exp(-nu * dt)
    p = weight[:, None, None] * term
    for k in range(1, 60):
        term = term @ a
        weight *= nu * dt / k
        p += weight[:, None, None] * term
        if k > 8 and weight.max() < 1e-16:
            break
    assert np.min(p) >= -1e-14 and np.max(abs(p.sum(axis=2)-1)) < 1e-12
    return p


def main():
    assert not (HERE/'protocol.json').exists()
    started = time.perf_counter()
    prior = h.read(h.R/'lateral_sampling192/protocol.json')
    protocol = dict(previous_goal_turn='PROGRESS192: endpoint sampling correction improves absolute/RM61, still misses VSL67 gain.',
        hypothesis='Do the SAME two current speed/density features of168 improve signed lane-response under192 interval endpoint sampling?',
        train='29 NC/VSL frames only; current start-cell state plus region-surviving5s endpoint lanes. No43/67 outcomes in optimization.',
        model='Eight regional log intercepts plus2 nonnegative common speed/density coefficients; same168 features/bounds,192 exp(5Q) likelihood. Frozen-start-state approximation across5s, not future-state input.',
        fit='One start from192 rates and zero slopes; raw multinomial NLL plus.5 squared departure prior; max60 coordinate sweeps, no restarts/grids.',
        observed_gate='Freeze coefficients first. Across43/67 matched150s blocks andcells20-25, signed net lane-response normalized MSE improves>=10%; neither case worsens>10%; endpoint NLL no worse in each case. If fail, NO autonomous candidate rollout.',
        limitations='Region-survivor selection remains; source-cell features frozen even when vehicle crosses cells. Endpoint counts are not microscopic event counts or a causal decomposition. Known historical states, not fresh blind.',
        budget=dict(fits=1,coordinate_sweeps_max=60,autonomous450_max_if_gate_passes=13,native=0,FZP=0),
        prior_reviewed='192 sampling audit,168 state closure and conditional-versus-autonomous failure,local Claude REVIEW. No new feature/seed/command bonus.',
        protected_sha256=prior['protected_sha256'],STOP=prior['STOP'])
    h.save(HERE/'protocol.json', protocol)
    pins={str(Path(__file__)):h.sha(__file__),str(h.R/'lateral_sampling192/fit.py'):h.sha(h.R/'lateral_sampling192/fit.py'),
          str(h.R/'state_lateral168/fit.py'):h.sha(h.R/'state_lateral168/fit.py')}
    bounds=h.read(h.F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']['segment_bounds_m']
    records=[]
    for case,info in h.read(h.R/'state_information92/protocol.json')['inputs'].items():
        path=h.ROOT/info['path'];assert h.sha(path)==info['sha256'];pins[str(path)]=info['sha256']
        doc=h.read(path)
        frames={float(t):{vid:dict(zip(doc['fields'],v)) for vid,v in fr.items()} for t,fr in doc['frames'].items()}
        start=min(frames)
        for t,u in zip(sorted(frames),sorted(frames)[1:]):
            assert abs(u-t-5)<1e-6
            for cell in range(20,26):
                groups=[[v for v in frames[t].values() if v['cell']==cell and v['lane']==g+1] for g in range(3)]
                n=[len(a) for a in groups]
                v=[sum(a['speed_kmh'] for a in group)/len(group) if group else 0. for group in groups]
                counts=np.zeros((3,3),dtype=int)
                for vid,a in frames[t].items():
                    if a['cell']!=cell:continue
                    b=frames[u].get(vid)
                    if b is not None and region(b['cell'])==region(cell):counts[int(a['lane'])-1,int(b['lane'])-1]+=1
                if counts.sum()==0:continue
                x=np.zeros((4,10));length=(bounds[cell+1]-bounds[cell])/1000
                for edge,(g,k) in enumerate(EDGES):
                    index,dv,dr=features(cell,g,k,n,v,length)
                    x[edge,index]=1.;x[edge,8:]=[dv,dr]
                records.append(dict(case=case,time=t,window=int(round(t-start,6)//150),cell=cell,n=n,v=v,
                                    counts=counts.tolist(),features=x.tolist()))
    with gzip.open(HERE/'records.json.gz','wt',encoding='utf8') as f:json.dump(records,f,allow_nan=False)
    train=[r for r in records if r['case'].startswith('29_')]
    x=np.array([r['features'] for r in train]);y=np.array([r['counts'] for r in train]);N=float(y.sum())
    center=np.array(h.read(h.R/'lateral_sampling192/coefficients.json')['regional']+[0.,0.])
    theta=center.copy();lower=np.array([LOW]*8+[0.,0.]);upper=np.array([HIGH]*8+[4.,4.]);eps=2e-4
    def loss(z):return float((-np.sum(y*np.log(np.maximum(probabilities(x,z),1e-30)))+.5*np.sum((z-center)**2))/N)
    history=[loss(theta)]
    h.save(HERE/'status.json',dict(status='fitting',sweep=0))
    for sweep in range(60):
        before=theta.copy()
        for j in range(10):
            a,b=theta.copy(),theta.copy();a[j]+=eps;b[j]-=eps
            f,fa,fb=loss(theta),loss(a),loss(b);g=(fa-fb)/(2*eps);curv=max(1e-8,(fa-2*f+fb)/eps**2)
            step=float(np.clip(theta[j]-g/curv,lower[j],upper[j])-theta[j])
            for _ in range(24):
                trial=theta.copy();trial[j]+=step
                if loss(trial)<=f+1e-14:theta=trial;break
                step*=.5
        history.append(loss(theta));assert history[-1]<=history[-2]+1e-12
        h.save(HERE/'status.json',dict(status='fitting',sweep=sweep+1,objective=history[-1]))
        if max(abs(theta-before))<1e-7:break
    gradients=[]
    for j in range(10):
        a,b=theta.copy(),theta.copy();a[j]+=eps;b[j]-=eps;g=(loss(a)-loss(b))/(2*eps)
        gradients.append(min(g,0.) if theta[j]<=lower[j]+1e-7 else max(g,0.) if theta[j]>=upper[j]-1e-7 else g)
    converged=max(abs(g) for g in gradients)<1e-6
    coefficients=dict(state=theta.tolist(),center=center.tolist(),sweeps=sweep+1,objective_history=history,
                      projected_gradient=max(abs(g) for g in gradients),converged=converged,train_pairs=int(N))
    # Do not change this selection after validation.
    h.save(HERE/'coefficients_frozen.json',coefficients)
    xa=np.array([r['features'] for r in records]);ya=np.array([r['counts'] for r in records])
    pred={name:probabilities(xa,z) for name,z in [('192',center),('193',theta)]}
    scores=[];blocks={};response_rows=[]
    for j,r in enumerate(records):
        c=ya[j];mass=c.sum(axis=1);block=(r['case'],r['window'],r['cell'])
        b=blocks.setdefault(block,dict(actual=np.zeros(3),p192=np.zeros(3),p193=np.zeros(3)))
        b['actual']+=c.sum(axis=0)-mass
        for name in pred:
            expected=mass[:,None]*pred[name][j]
            b['p'+name]+=expected.sum(axis=0)-mass
    for case in sorted({r['case'] for r in records}):
        ids=[i for i,r in enumerate(records) if r['case']==case];c=ya[ids]
        for name,p in pred.items():scores.append(dict(case=case,model=name,pairs=int(c.sum()),nll=float(-np.sum(c*np.log(p[ids]))/c.sum())))
    for a,b in [('43_none','43_vsl'),('67_release','67_release_vsl90')]:
        for (case,window,cell),left in blocks.items():
            if case!=a or (b,window,cell) not in blocks:continue
            right=blocks[b,window,cell]
            for lane in range(3):
                actual=float(right['actual'][lane]-left['actual'][lane])
                response_rows.append(dict(case=a[:2],window=window,cell=cell,lane=lane+1,actual=actual,
                    p192=float(right['p192'][lane]-left['p192'][lane]),p193=float(right['p193'][lane]-left['p193'][lane])))
    metrics={}
    for case in ('43','67','all'):
        rs=[r for r in response_rows if case=='all' or r['case']==case]
        metrics[case]={name:float(np.mean([((r['p'+name]-r['actual'])/max(3.,abs(r['actual'])))**2 for r in rs])) for name in pred}
    nll_gate=all(sum(s['nll']*s['pairs'] for s in scores if s['case'].startswith(case) and s['model']=='193') <=
                 sum(s['nll']*s['pairs'] for s in scores if s['case'].startswith(case) and s['model']=='192')+1e-10 for case in ('43','67'))
    gates=dict(converged=converged,response=metrics['all']['193']<=.9*metrics['all']['192'],
               per_case=all(metrics[c]['193']<=1.1*metrics[c]['192'] for c in ('43','67')),nll=nll_gate)
    h.save(HERE/'observed_gate.json',dict(gates=gates,passed=all(gates.values()),metrics=metrics,scores=scores,response_rows=response_rows,
                                       autonomous=False,scope='Conditional current-state endpoint response, not traffic gain'))
    # Batched exponentials independently match the previously audited scalar law.
    errors=[]
    for i in np.random.default_rng(193).choice(len(xa),24,replace=False):
        z=np.clip(xa[i]@theta,LOW,HIGH);errors.append(float(abs(transition(z)-pred['193'][i]).max()))
    assert max(errors)<1e-12
    for p,d in {**pins,**protocol['protected_sha256'],protocol['STOP']['path']:protocol['STOP']['sha256']}.items():assert h.sha(p)==d,p
    h.save(HERE/'fit_verification.json',dict(status='pass',input_sha256=pins,batch_scalar_cases=24,batch_scalar_error=max(errors),
        state_features_same168=True,coefficients_frozen_before_validation=True,protected_STOP_preserved=True))
    h.save(HERE/'status.json',dict(status='observed_gate_passed' if all(gates.values()) else 'observed_gate_failed',sweeps=sweep+1,seconds=time.perf_counter()-started,forecasts=0))
    print(dict(gates=gates,metrics=metrics,slopes=theta[-2:].tolist(),sweeps=sweep+1,projected_gradient=max(abs(g) for g in gradients),seconds=time.perf_counter()-started),flush=True)


if __name__=='__main__':main()
