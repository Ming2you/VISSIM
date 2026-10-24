"""Independent convex-fit and feature checks, plus instantaneous67 audit."""
from collections import defaultdict, Counter
import math
import numpy as np
from .check import HERE, V0, T, JAM
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from diagnostics.repin_v3c3_review_20261001.neighbor_information194.check import normalize


def main():
    protocol=h.read(HERE/'protocol.json')
    groups=h.read(HERE/'groups.json.gz')
    fits=h.read(HERE/'frozen_models.json')
    allrows=h.read(h.R/'neighbor_information194/rows.json.gz')
    by=defaultdict(list)
    for r in allrows:by[r['case'],r['t'],r['cell'],r['lane']].append(r)
    inputs=h.read(h.R/'state_information92/protocol.json')['inputs']
    paths={k:h.ROOT/inputs[k]['path'] for k in ('29_none','43_none')}
    paths.update({f'67_{arm}':h.R/'blocking176'/f'{arm}_frames.json.gz' for arm in ('hold','release')})
    lengths=np.diff(h.read(h.F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']['segment_bounds_m'])
    checked=0;error=0.;native=[]
    def exact(a,b):
        nonlocal checked,error
        error=max(error,abs(a-b));checked+=1
        assert abs(a-b)<1e-9,(a,b)
    for case,path in paths.items():
        frames=normalize(h.read(path))
        for z in (r for r in groups if r['case']==case):
            key=(case,z['t'],z['cell'],z['lane']);rr=by[key]
            fr=frames[z['t']];next_fr=frames[round(z['t']+5,6)]
            counts=Counter((v['cell'],v['lane']) for v in fr.values())
            velocities=[];fronts=[];rhos=[];changes=[];accelerations=[]
            for r in rr:
                v=fr[r['id']];w=fr[r['leader']]
                velocities.append(v['v']/3.6);fronts.append(w['v']/3.6)
                rhos.append(counts[w['cell'],w['lane']]/lengths[w['cell']])
                changes.append((next_fr[r['id']]['v']-v['v'])/18.)
                if 'accel' in v:accelerations.append(float(v['accel']))
            u=np.array(velocities);w=np.array(fronts);rho=float(np.mean(rhos))
            B=float(np.mean(np.maximum(u-w,0)**2))
            exact(z['n'],len(rr));exact(z['v'],float(np.mean(u)))
            exact(z['rho_a'],rho);exact(z['B_paired'],B)
            exact(z['acceleration_5s'],float(np.mean(changes)))
            # Independent paper35 substitution: effective cross section x rho B.
            f=fits['paired'];cross=V0*rho*T*T/(f['tau_sec']*f['A_jam']*(1-rho/JAM)**2)
            a=(V0-float(np.mean(u)))/f['tau_sec']-cross*rho*B
            exact(a,z['paired_prediction'])
            if accelerations:
                observed=float(np.mean(accelerations))
                native.append(dict(case=case,t=z['t'],cell=z['cell'],lane=z['lane'],n=len(rr),
                    native_accel=observed,interval_accel=z['acceleration_5s'],
                    paired=a,independent=z['independent_prediction'],v_kmh=z['v']*3.6,
                    rho_veh_km=rho*1000,B=B))
    train=[r for r in groups if r['case']=='29_none'];fit_audits={}
    for mode,fit in fits.items():
        x=np.array([[r['relaxation_feature'],r[mode+'_braking_feature']] for r in train]);y=np.array([r['acceleration_5s'] for r in train])
        beta=np.array([fit['alpha'],fit['gamma']])
        # Independent optimality: stationarity in interior or lower A-bound ray.
        grad=x.T@(x@beta-y)/len(y)
        if .001+1e-8<fit['A_jam']<.5-1e-8 and 5+1e-8<fit['tau_sec']<120-1e-8:
            assert np.max(np.abs(grad))<1e-9
            q,r=np.linalg.qr(x,mode='reduced');ref=np.linalg.solve(r,q.T@y)
        else:
            assert abs(fit['A_jam']-.5)<1e-12
            direction=np.array([1.,2.]);v=x@direction
            ref=direction*float(v@y/(v@v))
            assert abs(grad@direction)<1e-9
            assert grad[1]>=-1e-9
        assert max(abs(ref-beta))<1e-10
        fit_audits[mode]=dict(max_beta_error=float(max(abs(ref-beta))),gradient=grad.tolist())
    summaries=[]
    for case in paths:
        rs=[r for r in native if r['case']==case]
        if not rs:continue
        for cell in (None,20,21,24,25):
            zz=[r for r in rs if cell is None or r['cell']==cell]
            if not zz:continue
            score=dict(case=case,cell=cell,groups=len(zz))
            for target in ('native_accel','interval_accel'):
                for model in ('persistence','paired','independent'):
                    score[target+'_'+model+'_rmse']=math.sqrt(float(np.mean([(r.get(model,0)-r[target])**2 for r in zz])))
            summaries.append(score)
    # Descriptive severity bins declared after scoring; do not refit on them.
    severity=[]
    for case in paths:
        for low,high in ((0.,60.),(60.,100.),(100.,180.)):
            zz=[r for r in groups if r['case']==case and low<=1000*r['rho_a']<high]
            if not zz:continue
            severity.append(dict(case=case,rho_range=[low,high],n=len(zz),
                predicted_mean=float(np.mean([r['paired_prediction'] for r in zz])),
                actual_mean=float(np.mean([r['acceleration_5s'] for r in zz])),
                paired_rmse=math.sqrt(float(np.mean([(r['paired_prediction']-r['acceleration_5s'])**2 for r in zz])))))
    for p,d in {**protocol['input_sha256'],**protocol['protected_sha256'],protocol['STOP']['path']:protocol['STOP']['sha256']}.items():assert h.sha(p)==d,p
    assert h.sha(HERE/'frozen_models.json')==h.read(HERE/'completion.json')['frozen_sha256']
    h.save(HERE/'instantaneous.json',dict(note='Post-fit diagnostic at same censored cohorts; no coefficients changed. Native instantaneous acceleration and five-second cohort-average response remain different estimands.',scores=summaries,rows=native))
    h.save(HERE/'severity.json',severity)
    result=dict(status='pass',feature_checks=checked,max_error=error,fit_independent_audits=fit_audits,
        protected_input_STOP_unchanged=True,models_frozen=True,forecasts=0)
    h.save(HERE/'verification.json',result)
    print(result)
    print('INSTANT',[s for s in summaries if s['cell'] is None])
    print('SEVERITY',severity)


if __name__=='__main__':main()
