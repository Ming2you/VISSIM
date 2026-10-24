"""Conditional GKT relaxation/braking balance, not an autonomous plant.

Fit nominal110 seed29 only; independently score nominal43 and67 RM arms.
Do not guess missing per-vehicle VSL exposure. The VSL question stays open.
"""
from collections import Counter, defaultdict
import math
from pathlib import Path
import time
import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from diagnostics.repin_v3c3_review_20261001.neighbor_information194.check import normalize, savegz

HERE=Path(__file__).resolve().parent
V0=112.275/3.6  # Stored DSD110 distribution mean, NOT individual desired speed.
T=1.8
JAM=.180  # veh/m/lane; frozen existing physical storage density.


def gaussian_positive_second(mu, variance):
    if variance<=1e-14:return max(0.,mu)**2
    sd=math.sqrt(variance);z=mu/sd
    return (variance+mu*mu)*(.5*math.erfc(-z/math.sqrt(2)))+mu*sd*math.exp(-z*z/2)/math.sqrt(2*math.pi)


def fit(groups, branch):
    x=np.array([[r['relaxation_feature'],r[branch+'_braking_feature']] for r in groups])
    y=np.array([r['acceleration_5s'] for r in groups])
    # alpha=1/tau, gamma=1/(tau*A_jam). A_jam and tau bounds are declared
    # once; optimize exactly over their four-sided convex polygon.
    vertices=np.array([(a,a/A) for a,A in ((1/120,.5),(1/5,.5),(1/5,.001),(1/120,.001))])
    candidates=[]
    unconstrained=np.linalg.lstsq(x,y,rcond=None)[0]
    def feasible(b):
        a,g=b
        return 1/120-1e-12<=a<=1/5+1e-12 and a/.5-1e-12<=g<=a/.001+1e-12
    if feasible(unconstrained):candidates.append(unconstrained)
    for a,b in zip(vertices,np.roll(vertices,-1,axis=0)):
        d=b-a;v=x@d
        step=np.clip(float(v@(y-x@a)/(v@v)),0.,1.)
        candidates.append(a+step*d)
    beta=min(candidates,key=lambda b:float(np.mean((x@b-y)**2)))
    gradient=2*x.T@(x@beta-y)/len(y)
    # Supporting hyperplane condition is sufficient for this convex problem.
    kkt=min(float(gradient@(v-beta)) for v in vertices)
    assert feasible(beta) and kkt>=-1e-8
    return dict(alpha=float(beta[0]),gamma=float(beta[1]),tau_sec=1/float(beta[0]),
                A_jam=float(beta[0]/beta[1]),train_mse=float(np.mean((x@beta-y)**2)),
                polygon_kkt_min=kkt,unconstrained=unconstrained.tolist())


def extract(case, selected, raw, lengths):
    by=defaultdict(list)
    for r in selected:by[r['t'],r['cell'],r['lane']].append(r)
    frames=normalize(h.read(raw));groups=[];counts=Counter()
    for (t,cell,lane),rr in sorted(by.items()):
        if len(rr)<5:counts['fewer_than5_pairs']+=1;continue
        fr=frames[round(t,6)]
        densities=Counter((z['cell'],z['lane']) for z in fr.values())
        u=np.array([r['x'][0]/3.6 for r in rr])
        w=np.array([(r['x'][0]+r['x'][13])/3.6 for r in rr])
        leadrho=[densities[fr[r['leader']]['cell'],fr[r['leader']]['lane']]/lengths[fr[r['leader']]['cell']] for r in rr]
        rho_a=float(np.mean(leadrho))
        if not 0<rho_a<JAM:counts['interaction_density_outside_domain']+=1;continue
        dv=u-w;mu=float(np.mean(dv));vu=float(np.var(u));vw=float(np.var(w))
        paired=float(np.mean(np.maximum(dv,0)**2))
        independent=gaussian_positive_second(mu,vu+vw)
        correlated=gaussian_positive_second(mu,float(np.var(dv)))
        factor=V0*(rho_a*T/(1-rho_a/JAM))**2
        groups.append(dict(case=case,t=t,cell=cell,lane=lane,n=len(rr),
            v=float(np.mean(u)),leader_v=float(np.mean(w)),rho_a=rho_a,
            relaxation_feature=V0-float(np.mean(u)),
            paired_braking_feature=-factor*paired,
            independent_braking_feature=-factor*independent,
            correlated_braking_feature=-factor*correlated,
            B_paired=paired,B_independent=independent,B_correlated=correlated,
            acceleration_5s=float(np.mean([r['y']/18 for r in rr]))))
        counts['groups']+=1;counts['vehicle_pairs']+=len(rr)
    return groups,dict(counts)


def main():
    assert not (HERE/'protocol.json').exists(),'Preserve every previous attempt'
    started=time.perf_counter()
    previous=h.read(h.R/'characteristic195/protocol.json')
    old=h.read(h.R/'neighbor_information194/protocol.json')
    inputs=h.read(h.R/'state_information92/protocol.json')['inputs']
    files={k:h.ROOT/inputs[k]['path'] for k in ('29_none','43_none')}
    files.update({f'67_{arm}':h.R/'blocking176'/f'{arm}_frames.json.gz' for arm in ('hold','release')})
    cache=h.R/'neighbor_information194/rows.json.gz'
    mapping=h.F/'route_inventory/mapping31.json'
    pins={str(p):h.sha(p) for p in (*files.values(),cache,mapping,Path(__file__))}
    for p in files.values():assert pins[str(p)]==old['input_sha256'][str(p)]
    h.save(HERE/'protocol.json',dict(previous_turn='PROGRESS195: autonomous local operator rejected; no live owned forecast.',
        purpose='Does the observed paired braking moment explain material acceleration before adding a GKT term to METANET?',
        literature='https://mtreiber.de/publications/MASTER.pdf Eqs20,27,35',
        equation='a=(V0-V)/tau - V0/(tau*A_jam)*(rho_a*T/(1-rho_a/rho_max))^2*B',
        observed_B='E[(v-v_leader)_+^2] for current geometric same-link leader pairs; compare zero-covariance Gaussian closure at identical measured marginal moments.',
        population='Same cohort at t and t+5; endpoint same lane/link and observed at t-5 from194. This excludes membership transport/pressure, but interval average is not instantaneous acceleration. Current lane changes between samples may remain.',
        train='Only29_none; freeze two2parameter fits before43_none and67hold/release scoring.',
        constants=dict(V0_m_s=V0,T_sec=T,rho_max_veh_m=JAM),
        bounds=dict(tau_sec=[5,120],A_jam=[.001,.5]),
        budget=dict(fits=2,forecasts=0,native=0,FZP=0),
        gate='Each nominal heldout seed pooled groupRMSE improves10pct over zero acceleration and no arm deteriorates; physical current-pair model also must improve10pct on independence in each seed. Bound hits/nonphysical five-second speeds reported. No bound expansion.',
        limitations='Conditional mean DSD110 approximation, not individual desired speed or exact original GKT interaction point. No VSL scoring because actual per-vehicle command exposure is not available uniformly across caches; this necessary nominal screen does not qualify RM/VSL gains.',
        prior_reviewed='Claude REVIEW_CHECK, local_fd24_25, first_recovery_divergence, recovery_subcells,137,169,194/195. No repeated recovery coefficient grid.',
        input_sha256=pins,protected_sha256=previous['protected_sha256'],STOP=previous['STOP']))
    for p,d in {**pins,**previous['protected_sha256'],previous['STOP']['path']:previous['STOP']['sha256']}.items():assert h.sha(p)==d,p
    lengths=np.diff(h.read(mapping)['freeway_model_links']['FW_E']['segment_bounds_m'])
    rows=h.read(cache)
    train,counts=extract('29_none',[r for r in rows if r['case']=='29_none'],files['29_none'],lengths)
    models={m:fit(train,m) for m in ('paired','independent')}
    h.save(HERE/'frozen_models.json',models);frozen=h.sha(HERE/'frozen_models.json')
    groups=list(train);count_by_case={'29_none':counts}
    for case,path in files.items():
        if case=='29_none':continue
        gg,count_by_case[case]=extract(case,[r for r in rows if r['case']==case],path,lengths)
        groups+=gg
    for r in groups:
        for branch,m in models.items():
            r[branch+'_prediction']=m['alpha']*r['relaxation_feature']+m['gamma']*r[branch+'_braking_feature']
        # Same paired-model coefficients: moment approximation diagnostic only.
        m=models['paired']
        r['correlated_prediction']=m['alpha']*r['relaxation_feature']+m['gamma']*r['correlated_braking_feature']
    scores=[]
    for case in files:
        for cell in (None,20,21,24,25):
            gg=[r for r in groups if r['case']==case and (cell is None or r['cell']==cell)]
            if not gg:continue
            score=dict(case=case,cell=cell,groups=len(gg),vehicle_pairs=sum(r['n'] for r in gg))
            for model in ('persistence','paired','independent','correlated'):
                errors=[r.get(model+'_prediction',0)-r['acceleration_5s'] for r in gg]
                score[model+'_rmse_m_s2']=math.sqrt(float(np.mean(np.square(errors))))
                score[model+'_bias_m_s2']=float(np.mean(errors))
            score['paired_nonphysical_5s_speed']=sum(not 0<=r['v']+5*r['paired_prediction']<=160/3.6 for r in gg)
            scores.append(score)
    gates={}
    for seed in ('43','67'):
        gg=[r for r in scores if r['cell'] is None and r['case'].startswith(seed)]
        pooled={m:math.sqrt(sum(r['groups']*r[m+'_rmse_m_s2']**2 for r in gg)/sum(r['groups'] for r in gg)) for m in ('persistence','paired','independent')}
        gates[seed]=dict(pooled_rmse_m_s2=pooled,versus_persistence=pooled['paired']<=.9*pooled['persistence'],
            versus_independence=pooled['paired']<=.9*pooled['independent'],
            no_arm_worse=all(r['paired_rmse_m_s2']<=r['persistence_rmse_m_s2'] for r in gg))
    savegz(HERE/'groups.json.gz',groups)
    h.save(HERE/'summary.json',dict(models=models,populations=count_by_case,scores=scores,gates=gates,
        seconds=time.perf_counter()-started,adopted=False))
    for p,d in {**pins,**previous['protected_sha256'],previous['STOP']['path']:previous['STOP']['sha256']}.items():assert h.sha(p)==d,p
    assert h.sha(HERE/'frozen_models.json')==frozen
    h.save(HERE/'completion.json',dict(status='complete_conditional_screen',groups=len(groups),fits=2,
        forecasts=0,native=0,FZP=0,push=False,production_adopted=False,
        gate_pass=all(g['versus_persistence'] and g['versus_independence'] and g['no_arm_worse'] for g in gates.values()),
        full_goal='ACTIVE_NOT_QUALIFIED',frozen_sha256=frozen))
    print(dict(models=models,gates=gates,populations=count_by_case))


if __name__=='__main__':main()
