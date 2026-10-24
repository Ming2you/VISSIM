"""Two frozen lateral closures from seed29, no control-label covariates."""
import collections
import gzip
import json
import math
from pathlib import Path
import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent
DIRECTIONS=((0,1),(1,0),(1,2),(2,1))


def features(cell,g,k,n,v,length):
    region=int(cell>=22)
    # Both training and prediction use the beginning-of-step state.
    dv=float(np.clip((v[k]-v[g])/110,-1,1)) if n[g]>0 and n[k]>0 else 0.
    dr=float(np.clip((n[g]-n[k])/(length*180),-1,1))
    return region*4+DIRECTIONS.index((g,k)),dv,dr


def rates(coeff,cell,n,v,length,mode):
    theta=coeff[mode]
    out=[[0.]*3 for _ in range(3)]
    for g,k in DIRECTIONS:
        index,dv,dr=features(cell,g,k,n,v,length)
        value=theta[index]
        if mode=='state':value+=theta[8]*dv+theta[9]*dr
        out[g][k]=math.exp(min(math.log(.05),max(math.log(1e-5),value)))
    return out


def main():
    assert not (HERE/'protocol.json').exists()
    protected=h.read(h.R/'convection165/protocol.json')
    pins={str(Path(__file__)):h.sha(__file__)}
    def read(p):pins[str(p)]=h.sha(p);return h.read(p)
    h.save(HERE/'protocol.json',dict(previous_goal_turn='PROGRESS166/167',
        hypothesis='Downstream22--25 received19--21 exchange hazards without regional calibration. Learn regional baseline and one current-state closure, keeping dynamics otherwise fixed148.',
        train='Seed29 none/VSL existing5s frames2220.1..2970.1. Reused data, not fresh blind. No43/67 data or control-response loss in fit.',
        check='43none/VSL and67release/VSL transfer proxies evaluated after coefficients frozen; no fit/selection retuning on them.',
        regions=[[20,21],[22,23,24,25]],directions=DIRECTIONS,
        models=dict(regional='8 independent count/exposure rates, two regions x four directed adjacent pairs.',
                    state='Same8 log intercepts plus two common nonnegative slopes: clipped target-donor speed difference/110 and donor-target density difference/180.'),
        labels='Count visible same-cell endpoint transfers. Exposure includes every current donor vehicle, including cross-cell and disappeared labels. Other paths explicitly unobserved, not true no-lane-change labels. This predicts a partial endpoint-transfer intensity, not microscopic full hazard.',
        frozen_budget=dict(regional_closed_form_fits=1,state_box_poisson_fits=1,max_coordinate_sweeps=60,
                           autonomous450=17,native=0,FZP=0,push=0),
        bounds=dict(log_intercepts=[math.log(1e-5),math.log(.05)],state_slopes=[0,4],
                    runtime_rate_per_direction=[1e-5,.05]),
        objective='Poisson visible-count likelihood with offset5*Ndonor; fixed ridge1 around regional intercepts and zero slopes. Deterministic box coordinate Newton, no hyperparameter or feature grid.',
        decision='Freeze both regardless transfer-score ranking, run fixed148 baseline parity plus8autonomous29/67 arms each. Same meaningful deltaTTT/sign/response/absolute/choice gates as148; no adoption on local transfer fit.',
        limitations='Same-cell endpoint counts omit simultaneous boundary+lane changes and5s returns. Nonadjacent jumps reported, not mapped into false one-step changes. Constant and state intensities are observational closures, not VSL causal coefficients. Cell19 unchanged; destination classes/space/mass/velocity transport unchanged.',
        protected_sha256=protected['protected_sha256'],STOP=protected['STOP']))
    h.save(HERE/'status.json',dict(status='fitting'))
    bounds=read(h.F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']['segment_bounds_m']
    lengths={i:(bounds[i+1]-bounds[i])/1000 for i in range(20,26)}
    sources=read(h.R/'state_information92/protocol.json')['inputs']
    rows=[];excluded=collections.Counter()
    for name,entry in sources.items():
        path=h.ROOT/entry['path'];assert h.sha(path)==entry['sha256'];doc=read(path)
        frames={round(float(t),6):{str(vid):dict(zip(doc['fields'],r)) for vid,r in frame.items()} for t,frame in doc['frames'].items()}
        for t,u in zip(sorted(frames),sorted(frames)[1:]):
            a,b=frames[t],frames[u];assert abs(u-t-5)<1e-6
            for cell in range(20,26):
                groups=[[x for x in a.values() if x['cell']==cell and x['lane']==g+1] for g in range(3)]
                n=[len(x) for x in groups];v=[sum(x['speed_kmh'] for x in z)/len(z) if z else 0. for z in groups]
                moves=collections.Counter()
                for vid,x in a.items():
                    if x['cell']!=cell:continue
                    y=b.get(vid)
                    if y is None:excluded[name+'_disappear']+=1
                    elif y['cell']!=cell:
                        excluded[name+'_cross_cell']+=1
                        if y['lane']!=x['lane']:excluded[name+'_cross_cell_lane_unlocated']+=1
                    elif y['lane']!=x['lane']:
                        pair=(x['lane']-1,y['lane']-1)
                        if pair not in DIRECTIONS:excluded[name+'_nonadjacent']+=1
                        else:moves[pair]+=1
                for g,k in DIRECTIONS:
                    if not n[g]:assert moves[g,k]==0;continue
                    index,dv,dr=features(cell,g,k,n,v,lengths[cell])
                    rows.append(dict(case=name,time=t,cell=cell,source=g+1,target=k+1,index=index,
                        dv=dv,dr=dr,exposure=5*n[g],count=moves[g,k]))
    train=[r for r in rows if r['case'].startswith('29_')]
    counts=[sum(r['count'] for r in train if r['index']==j) for j in range(8)]
    exposure=[sum(r['exposure'] for r in train if r['index']==j) for j in range(8)]
    assert all(n>0 for n in counts) and all(n>0 for n in exposure)
    regional=[math.log(min(.05,max(1e-5,c/e))) for c,e in zip(counts,exposure)]
    x=np.zeros((len(train),10));y=np.array([r['count'] for r in train],dtype=float);e=np.array([r['exposure'] for r in train],dtype=float)
    for i,r in enumerate(train):x[i,r['index']]=1;x[i,8:]=[r['dv'],r['dr']]
    center=np.array(regional+[0,0]);theta=center.copy()
    lower=np.array([math.log(1e-5)]*8+[0,0]);upper=np.array([math.log(.05)]*8+[4,4])
    def objective(t):
        linear=x@t
        return float(np.sum(e*np.exp(linear)-y*linear)+.5*np.sum((t-center)**2))
    trace=[objective(theta)]
    for sweep in range(60):
        before=theta.copy()
        for j in range(10):
            mu=e*np.exp(x@theta)
            gradient=float(x[:,j]@(mu-y)+theta[j]-center[j])
            curvature=float((x[:,j]**2)@mu+1)
            target=float(np.clip(theta[j]-gradient/curvature,lower[j],upper[j]))
            current=objective(theta);step=target-theta[j]
            for bt in range(20):
                trial=theta.copy();trial[j]+=step
                value=objective(trial)
                if value<=current+1e-10:theta=trial;break
                step*=.5
        trace.append(objective(theta))
        assert trace[-1]<=trace[-2]+1e-8
        if max(abs(theta-before))<1e-8:break
    gradient=x.T@(e*np.exp(x@theta)-y)+(theta-center)
    projected=np.where(theta<=lower+1e-7,np.minimum(gradient,0),np.where(theta>=upper-1e-7,np.maximum(gradient,0),gradient))
    fit=dict(regional=regional,state=theta.tolist(),counts=counts,exposure=exposure,
             train_rows=len(train),sweeps=sweep+1,objective_trace=trace,
             max_projected_gradient=float(max(abs(projected))),ridge=1.,feature_source='current state only')
    # Numerical differentiation at the fitted point verifies the actual objective.
    diffs=[]
    for j in range(10):
        a=theta.copy();b=theta.copy();a[j]+=1e-5;b[j]-=1e-5
        diffs.append(abs((objective(a)-objective(b))/2e-5-gradient[j]))
    assert max(diffs)<1e-4
    fit['gradient_difference_max']=max(diffs)
    h.save(HERE/'coefficients.json',fit)
    # Freeze before looking at43/67 scores. Both candidates retain the same budget.
    scores=[]
    original=read(h.F/'joint_lane_25/protocol.json')['candidate']['exchange_rates_per_sec']
    for case in sorted({r['case'] for r in rows}):
        z=[r for r in rows if r['case']==case]
        for mode in ('original','regional','state'):
            expected=[]
            for r in z:
                if mode=='original':rate=original[r['source']-1][r['target']-1]
                else:
                    t=fit[mode];linear=t[r['index']]+(t[8]*r['dv']+t[9]*r['dr'] if mode=='state' else 0)
                    rate=math.exp(min(math.log(.05),max(math.log(1e-5),linear)))
                expected.append(r['exposure']*rate)
            dev=sum(2*(y0*math.log(y0/m)-y0+m if y0 else m) for r,m in zip(z,expected) for y0 in [r['count']])
            scores.append(dict(case=case,mode=mode,rows=len(z),observed=sum(r['count'] for r in z),predicted=sum(expected),
                poisson_deviance=dev,rmse=math.sqrt(sum((r['count']-m)**2 for r,m in zip(z,expected))/len(z))))
    with gzip.open(HERE/'rows.json.gz','wt',encoding='utf-8') as f:json.dump(rows,f,allow_nan=False)
    h.save(HERE/'transfer_scores.json',scores);h.save(HERE/'censored.json',dict(excluded))
    for p,d in {**pins,**protected['protected_sha256']}.items():assert h.sha(p)==d,p
    assert h.sha(protected['STOP']['path'])==protected['STOP']['sha256']
    h.save(HERE/'fit_verification.json',dict(input_sha256=pins,gradient_error=max(diffs),core=True,STOP=True))
    h.save(HERE/'status.json',dict(status='coefficients_frozen',new_fits=2,new_forecasts=0))
    print({k:v for k,v in fit.items() if k!='objective_trace'})
    for r in scores:
        if r['case'].startswith('67'):print(r)


if __name__=='__main__':main()
