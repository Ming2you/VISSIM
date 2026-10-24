"""Audit the frozen observed-response193 screen, without forecast or refitting."""
import math
from pathlib import Path
import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from .fit import probabilities, LOW, HIGH, EDGES

HERE=Path(__file__).resolve().parent


def main():
    rows=h.read(HERE/'records.json.gz');frozen=h.read(HERE/'coefficients_frozen.json')
    digest=h.sha(HERE/'coefficients_frozen.json')
    original=h.read(h.R/'lateral_sampling192/endpoint_counts.json')
    mapping=h.read(h.F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']
    bounds=mapping['segment_bounds_m'];feature_checks=0;maximum=0.
    for case,entry in h.read(h.R/'state_information92/protocol.json')['inputs'].items():
        doc=h.read(h.ROOT/entry['path']);ix={k:i for i,k in enumerate(doc['fields'])}
        counts=np.zeros((2,3,3),dtype=int)
        for r in [z for z in rows if z['case']==case]:
            reg=int(r['cell']>=22);counts[reg]+=np.array(r['counts'])
            fr=doc['frames'][str(r['time'])]
            groups=[[v for v in fr.values() if v[ix['cell']]==r['cell'] and v[ix['lane']]==g+1] for g in range(3)]
            n=[len(g) for g in groups]
            v=[sum(z[ix['speed_kmh']] for z in g)/len(g) if g else 0. for g in groups]
            assert n==r['n'] and max(abs(a-b) for a,b in zip(v,r['v']))<1e-12
            length=(bounds[r['cell']+1]-bounds[r['cell']])/1000
            x=np.zeros((4,10))
            for e,(g,k) in enumerate(EDGES):
                x[e,4*reg+e]=1
                x[e,8]=max(-1.,min(1.,(v[k]-v[g])/110)) if n[g]>0 and n[k]>0 else 0.
                x[e,9]=max(-1.,min(1.,(n[g]-n[k])/(180*length)))
            error=float(abs(x-np.array(r['features'])).max());assert error<1e-12
            maximum=max(maximum,error);feature_checks+=x.size
        assert counts.tolist()==original[case]['counts']
    ids=[i for i,r in enumerate(rows) if r['case'].startswith('29_')]
    xa=np.array([r['features'] for r in rows]);ya=np.array([r['counts'] for r in rows])
    theta=np.array(frozen['state']);center=np.array(frozen['center']);x=xa[ids];y=ya[ids];N=float(y.sum())
    assert N==frozen['train_pairs']
    def loss(z):return float((-np.sum(y*np.log(probabilities(x,z)))+.5*np.sum((z-center)**2))/N)
    assert abs(loss(theta)-frozen['objective_history'][-1])<1e-12
    grad=[];eps=1e-5;lower=[LOW]*8+[0.,0.];upper=[HIGH]*8+[4.,4.]
    for j in range(10):
        a,b=theta.copy(),theta.copy();a[j]+=eps;b[j]-=eps;g=(loss(a)-loss(b))/(2*eps)
        grad.append(min(g,0.) if theta[j]<=lower[j]+1e-7 else max(g,0.) if theta[j]>=upper[j]-1e-7 else g)
    assert max(abs(g) for g in grad)<1e-6
    # Regional aggregation checks avoid treating source-cell cohorts as located lane-change events.
    predictions={label:probabilities(xa,z) for label,z in [('192',center),('193',theta)]}
    bins={}
    for i,r in enumerate(rows):
        k=(r['case'],r['window'],int(r['cell']>=22));b=bins.setdefault(k,{v:np.zeros(3) for v in ('actual','192','193')})
        c=ya[i];mass=c.sum(axis=1);b['actual']+=c.sum(axis=0)-mass
        for label,p in predictions.items():b[label]+=(mass[:,None]*p[i]).sum(axis=0)-mass
    regional=[]
    for a,b in [('43_none','43_vsl'),('67_release','67_release_vsl90')]:
        for (case,window,reg),left in bins.items():
            if case!=a or (b,window,reg) not in bins:continue
            right=bins[b,window,reg]
            for g in range(3):regional.append(dict(case=a[:2],window=window,region=reg,lane=g+1,
                actual=float(right['actual'][g]-left['actual'][g]),p192=float(right['192'][g]-left['192'][g]),p193=float(right['193'][g]-left['193'][g])))
    metrics={case:{label:float(np.mean([((r['p'+label]-r['actual'])/max(3.,abs(r['actual'])))**2 for r in regional if case=='all' or r['case']==case]))
                   for label in ('192','193')} for case in ('43','67','all')}
    gate=h.read(HERE/'observed_gate.json');assert not gate['passed']
    response=gate['response_rows']
    for case in ('43','67','all'):
        for label in ('192','193'):
            error=np.mean([((r['p'+label]-r['actual'])/max(3.,abs(r['actual'])))**2 for r in response if case=='all' or r['case']==case])
            assert abs(error-gate['metrics'][case][label])<1e-12
    assert not (HERE/'forecast').exists()
    proto=h.read(HERE/'protocol.json');pins=h.read(HERE/'fit_verification.json')['input_sha256']
    for p,d in {**pins,**proto['protected_sha256'],proto['STOP']['path']:proto['STOP']['sha256']}.items():assert h.sha(p)==d,p
    assert h.sha(HERE/'coefficients_frozen.json')==digest
    h.save(HERE/'regional_response.json',dict(metrics=metrics,rows=regional,
        note='Endpoint lane change of region-surviving cohorts. This is not the full regional lateral flow budget.'))
    result=dict(status='pass',record_rows=len(rows),endpoint_pairs=int(ya.sum()),feature_checks=feature_checks,
        maximum_feature_error=maximum,projected_gradient=max(abs(g) for g in grad),same_pairs_as192=True,
        frozen_coefficients_unchanged=True,production_and_STOP_preserved=True,new_forecasts=0)
    h.save(HERE/'verification.json',result)
    h.save(HERE/'completion.json',dict(status='complete_observed_screen',result='REJECTED_BEFORE_ROLLOUT',
        fit_count=1,fit_seconds=h.read(HERE/'status.json')['seconds'],autonomous_forecasts=0,native=0,FZP=0,push=False,
        production_adopted=False,full_goal='ACTIVE_NOT_QUALIFIED'))
    print(result);print('REGIONAL_RESPONSE',metrics)


if __name__=='__main__':main()
