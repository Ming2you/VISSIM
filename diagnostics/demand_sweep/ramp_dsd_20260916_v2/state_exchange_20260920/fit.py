"""Fit exchange events, never TTT or a reward for using RM/VSL."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H
from evaluation.controllers.physical_lane_groups import StateDependentExchange
import numpy as np
import csv
import math

HERE=Path(__file__).resolve().parent


def records(seed,arm):
    with (HERE/f'observations_v2/s{seed}_{arm}.csv').open(encoding='utf-8',newline='') as f:
        return [{k:float(v) if v else None for k,v in r.items()} for r in csv.DictReader(f)]


def raw(r):return [r['donor_v'],r['recipient_v']-r['donor_v'],r['donor_rho'],r['recipient_rho']]
def edge(r):return f"{int(r['cell'])}:{int(r['g'])}:{int(r['k'])}"
def eligible(r):return r['donor_v'] is not None and r['recipient_v'] is not None and r['exposure_veh_sec']>0


def deviance(y,mu):
    return float(2*np.sum(mu-y+np.where(y>0,y*np.log(np.maximum(y,1)/np.maximum(mu,1e-15)),0)))


def fit(rows,ridge):
    x=np.array([raw(r) for r in rows]);exposure=np.array([r['exposure_veh_sec'] for r in rows]);y=np.array([r['moves'] for r in rows])
    keys=sorted({edge(r) for r in rows});index={k:i for i,k in enumerate(keys)}
    ids=np.array([index[edge(r)] for r in rows]);n=len(keys)
    center=x.mean(axis=0);scale=x.std(axis=0);assert np.all(scale>0)
    z=(x-center)/scale
    denom=np.bincount(ids,weights=exposure,minlength=n);counts=np.bincount(ids,weights=y,minlength=n)
    assert np.all(counts>0) and np.all(denom>0),'Unsupported exchange edge'
    # Profile out the40 address intercepts exactly. Only four pooled state
    # coefficients need Newton steps; no new fitting dependency is required.
    def objective(beta):
        linear=z@beta
        shift=np.full(n,-np.inf);np.maximum.at(shift,ids,linear)
        weighted=exposure*np.exp(linear-shift[ids])
        totals=np.bincount(ids,weights=weighted,minlength=n)
        intercept=np.log(counts/totals)-shift
        eta=intercept[ids]+linear;mu=exposure*np.exp(eta)
        loss=np.sum(mu-y*eta)+ridge/2*np.sum(beta**2)
        gradient=z.T@(mu-y)+ridge*beta
        means=np.column_stack([np.bincount(ids,weights=mu*z[:,j],minlength=n)/counts for j in range(4)])
        centered=z-means[ids]
        hessian=centered.T@(mu[:,None]*centered)+ridge*np.eye(4)
        return float(loss),gradient,hessian,intercept
    beta=np.zeros(4)
    for iteration in range(100):
        loss,gradient,hessian,intercept=objective(beta)
        if np.max(np.abs(gradient))<1e-5:break
        delta=np.linalg.solve(hessian,gradient);step=1.
        for _ in range(30):
            candidate=beta-step*delta
            if objective(candidate)[0]<=loss-1e-4*step*float(gradient@delta):break
            step*=.5
        else:raise ArithmeticError('Poisson line search failed')
        beta=candidate
    else:raise ArithmeticError('Poisson fit did not converge')
    model={'schema':'state-dependent-exchange/v1','feature_names':StateDependentExchange.feature_names,
        'center':center.tolist(),'scale':scale.tolist(),'lower':x.min(axis=0).tolist(),'upper':x.max(axis=0).tolist(),
        'coefficients':beta.tolist(),'log_intercepts':dict(zip(keys,intercept.tolist())),
        'max_rate_per_sec':float(np.max(y/exposure)),
        'provenance':{'training_seeds':[13,23],'training_arms':['none'],'row_count':len(rows),
            'ridge':ridge,'target':'next10s adjacent-group exchange counts / actual exposure','loss_uses_TTT':False,
            'optimizer_iterations':iteration,'gradient_max_abs':float(np.max(np.abs(gradient)))}}
    return model,dict(zip(keys,(counts/denom).tolist()))


def predict(model,rows):
    x=np.array([raw(r) for r in rows]);x=np.clip(x,model['lower'],model['upper'])
    z=(x-model['center'])/model['scale'];eta=np.array([model['log_intercepts'][edge(r)] for r in rows])+z@model['coefficients']
    return np.minimum(model['max_rate_per_sec'],np.exp(eta))


def score(model,base,rows):
    rates=predict(model,rows);y=np.array([r['moves'] for r in rows]);exposure=np.array([r['exposure_veh_sec'] for r in rows])
    baseline=np.array([base[edge(r)] for r in rows])*exposure
    return {'rows':len(rows),'actual':float(y.sum()),'predicted':float((rates*exposure).sum()),
        'deviance':deviance(y,rates*exposure),'constant_rate_deviance':deviance(y,baseline)}


def main():
    out=HERE/'fit_v1';out.mkdir(exist_ok=False)
    rows=[r for s in [13,23] for r in records(s,'none') if eligible(r) and r['time_s']>=900]
    early=[r for r in rows if r['time_s']<3000];late=[r for r in rows if r['time_s']>=3000]
    trials=[]
    for ridge in [.1,1.,10.]:
        model,base=fit(early,ridge);s=score(model,base,late)
        trials.append({'ridge':ridge,'validation':s})
        print('RIDGE',ridge,s,flush=True)
    selected=min(trials,key=lambda r:r['validation']['deviance'])['ridge']
    model,base=fit(rows,selected)
    config=e.load(H/'lane_group_response_20260919/qualification_v6/config.json')
    config['freeway']['physical_lane_exchange_model']=model
    e.save(out/'model.json',model);e.save(out/'config.json',config)
    e.save(out/'selection.json',{'selected_ridge':selected,'chronological_validation':trials,
        'refit_on_all_seed13_23_NC':True,'no_controlled_rows_used_to_select':True})
    held={}
    for seed,start in [(13,1650),(23,2400),(33,2400)]:
        held[str(seed)]={}
        for arm in ['none','rm_ramp','vsl','both']:
            rs=[r for r in records(seed,arm) if eligible(r) and start<=r['time_s']<start+450]
            held[str(seed)][arm]=score(model,base,rs)
        print('CONDITIONAL',seed,held[str(seed)],flush=True)
    e.save(out/'conditional_validation.json',{'scope':'Current measured state predicts next10s hazard; actual future exposure used to assess rate. Not a450s autonomous rollout.',
        'results':held})


if __name__=='__main__':main()
