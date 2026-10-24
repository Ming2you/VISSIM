"""Correct endpoint observation likelihood before reusing the existing phase runner."""
import ast
import copy
import gzip
import json
import math
from pathlib import Path
import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from diagnostics.repin_v3c3_review_20261001.queue_dynamics178.prepare import pressure

HERE=Path(__file__).resolve().parent
OLD=h.R/'phase_equilibrium181'


def transition_probability(log_rates, p, dt):
    alpha,beta=np.exp(log_rates)[0]*p,np.exp(log_rates)[1]*(1-p)
    rate=alpha+beta
    mass=-np.expm1(-rate*dt)/rate
    return alpha*mass,beta*mass


def fit(p, nm, ns, onset, release, start, maxiter=30):
    """One bounded two-variable Newton fit; no restart or parameter grid."""
    total=float(np.sum(nm+ns));bounds=np.log([1e-6,1.])
    def loss(x):
        pm,ps=transition_probability(x,p,5.)
        pm=np.clip(pm,1e-12,1-1e-12);ps=np.clip(ps,1e-12,1-1e-12)
        return float(-np.sum(onset*np.log(pm)+(nm-onset)*np.log1p(-pm)
                              +release*np.log(ps)+(ns-release)*np.log1p(-ps))/total)
    def derivatives(x):
        eps=1e-4;f=loss(x);g=np.zeros(2);H=np.zeros((2,2))
        for i in range(2):
            e=np.eye(2)[i]*eps
            g[i]=(loss(x+e)-loss(x-e))/(2*eps)
            H[i,i]=(loss(x+e)-2*f+loss(x-e))/eps**2
        e=np.array([eps,0]);v=np.array([0,eps])
        H[0,1]=H[1,0]=(loss(x+e+v)-loss(x+e-v)-loss(x-e+v)+loss(x-e-v))/(4*eps**2)
        return g,H
    x=np.clip(np.log(start),*bounds);history=[]
    for iteration in range(maxiter):
        f=loss(x);g,H=derivatives(x)
        projected=x-np.clip(x-g,*bounds)
        history.append(dict(iteration=iteration,loss=f,rates=np.exp(x).tolist(),
                            projected_gradient=float(max(abs(projected)))))
        if max(abs(projected))<1e-8:break
        H+=np.eye(2)*max(0.,1e-7-float(np.linalg.eigvalsh(H)[0]))
        step=-np.linalg.solve(H,g)
        if max(abs(step))>1:step/=max(abs(step))
        accepted=False
        for j in range(16):
            nxt=np.clip(x+step/2**j,*bounds)
            if loss(nxt)<f+1e-4*float(g@(nxt-x)):
                x=nxt;accepted=True;break
        if not accepted:break
    g,H=derivatives(x)
    return dict(rates=np.exp(x).tolist(),loss=loss(x),history=history,
                projected_gradient=float(max(abs(x-np.clip(x-g,*bounds)))),
                hessian_eigenvalues=np.linalg.eigvalsh(H).tolist(),
                bound_hit=bool(np.any(abs(x-bounds[0])<1e-6)|np.any(abs(x-bounds[1])<1e-6)),
                iterations=len(history))


OLD_TRANSITION='''        onset=(n-p[0])*(-math.expm1(-a*pressure*sec))
        release=p[0]*(-math.expm1(-b*(1-pressure)*sec))
        # Convert disjoint OLD populations simultaneously. New slow vehicles
        # brake to zero; released slow vehicles keep their speed moment before
        # METANET accelerates the moving population. No instantaneous v_free.
        moving=n-p[0];u=p[2]/moving if moving>1e-10 else 0.
        w=p[1]/p[0] if p[0]>1e-10 else 0.
        p[2]+=-onset*u+release*w;p[1]-=release*w;p[0]+=onset-release
'''

EXACT_TRANSITION='''        alpha,beta=a*pressure,b*(1-pressure)
        total=alpha+beta
        # Exact two-state population and speed-moment kinetics at fixed current
        # pressure. Formation brakes to zero; release preserves existing moment.
        if total>0:
            equilibrium=n*alpha/total
            integrated_s=equilibrium*sec+(p[0]-equilibrium)*(-math.expm1(-total*sec))/total
            onset=alpha*(n*sec-integrated_s);release=beta*integrated_s
            if min(onset,release)<-1e-9:raise ArithmeticError('209 negative transition count')
            onset=max(0.,onset);release=max(0.,release)
            old_ms=p[1]
            kernel=(sec*math.exp(-alpha*sec) if abs(alpha-beta)<1e-10 else
                    math.exp(-min(alpha,beta)*sec)*(-math.expm1(-abs(alpha-beta)*sec))/abs(alpha-beta))
            p[1]=old_ms*math.exp(-beta*sec)
            p[2]=p[2]*math.exp(-alpha*sec)+beta*old_ms*kernel
            p[0]+=onset-release
        else:onset=release=0.
'''


def main():
    assert not (HERE/'frozen_fit.json').exists()
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers.freeway_geometry import cell_lengths_km
    common.setup()
    manifest=h.R/'lane_state132/eval_01/manifest.json'
    context=lpr.load_sources(manifest)
    cfg=context['component']._config('FW_E',context['parameters']['by_direction']['FW_E'])
    fd=cfg.network.freeway_segment_params['FW_E'];jam=cfg.network.rho_max
    lengths=cell_lengths_km(cfg.network,'FW_E',31)
    proto=copy.deepcopy(h.read(OLD/'protocol.json'))
    proto.update(previous_goal_turn='PROGRESS208 observed recurrence/duration accounting',
        hypothesis='178 endpoint event numerator uses stayers but exposure uses all vehicles; count/exposure also approximates finite5s transitions. Correct matching trials and exact two-state likelihood, not a new feature or capacity bonus.',
        fit='One bounded two-hazard likelihood fit on29 only,1e-6..1/s,30Newton iterations,16backtracks, no restarts/grids.',
        train='29none/VSL existing5s early caches, same cell/lane endpoint eligibility in numerator AND denominator.',
        validation='Freeze before43/61/67; historically inspected states,67 part of olderFD calibration, not blind.',
        equation='Exact two-state endpoint probabilities over5s; exact population and speed-moment reaction over1s. Other181 physics unchanged.',
        budget=dict(parity450=1,fixed_operator_train=4,refit_train=4,validation_max=16,total450_max=25,fits=1,native=0,FZP=0),
        gates='Same original baseline meaningful |deltaTTT|>=.5 signs, response error improvement>=10%, absolute<=110%; no gate expansion or outcome-driven retry.',
        limitations=['Pressure frozen during each likelihood5s interval; within-interval state is unobserved.',
                    'Same-cell/lane survivor conditioning remains; corrected trial denominator does not remove selection bias.',
                    'Zero-pressure onset events remain unsupported and explicitly counted; numerical log clipping is not a new formation channel.',
                    'Exact moments assume zero-speed formation and moment-preserving release, still an unqualified two-population closure.'])
    h.save(HERE/'protocol.json',proto)
    src=h.read(h.R/'state_information92/protocol.json')['inputs'];samples=[];pins={str(manifest):h.sha(manifest)}
    for name in ('29_none','29_vsl'):
        path=h.ROOT/src[name]['path'];assert h.sha(path)==src[name]['sha256'];pins[str(path)]=h.sha(path)
        d=h.read(path);assert d['fields']==['cell','speed_kmh','x_m','lane']
        frames={float(t):v for t,v in d['frames'].items()};times=sorted(frames)
        for t,tn in zip(times,times[1:]):
            assert abs(tn-t-5)<1e-8
            now,future=frames[t],frames[tn]
            for i in range(20,26):
                for lane in (1,2,3):
                    own={k:z for k,z in now.items() if z[0]==i and z[3]==lane}
                    down=[z for z in now.values() if z[0]==i+1 and z[3]==lane]
                    n=len(own);s=sum(z[1]<5 for z in own.values());dn=len(down);ds=sum(z[1]<5 for z in down)
                    p=pressure(n,s,dn,ds,lengths[i],lengths[i+1],fd[i]['rho_crit'],fd[i+1]['rho_crit'],jam)
                    eligible=[(z,future[k]) for k,z in own.items() if k in future and future[k][0]==i and future[k][3]==lane]
                    ns=sum(z[1]<5 for z,_ in eligible);nm=len(eligible)-ns
                    on=sum(z[1]>=5 and v[1]<5 for z,v in eligible)
                    off=sum(z[1]<5 and v[1]>=5 for z,v in eligible)
                    samples.append(dict(case=name,time=t,cell=i,lane=lane,n=n,s=s,p=p,nm=nm,ns=ns,on=on,off=off))
    h.save(HERE/'fit_samples.json',samples)
    p,nm,ns,on,off=[np.array([z[k] for z in samples],float) for k in ('p','nm','ns','on','off')]
    old=h.read(OLD/'coefficients.json');start=[old['formation_per_sec'],old['release_per_sec']]
    naive=[sum(on)/sum(5*(z['n']-z['s'])*z['p'] for z in samples),
           sum(off)/sum(5*z['s']*(1-z['p']) for z in samples)]
    assert np.allclose(naive,start,rtol=0,atol=1e-12)
    fitted=fit(p,nm,ns,on,off,start)
    assert fitted['projected_gradient']<1e-5,fitted
    # A deterministic expected-count fixture must recover known rates despite5s coarsening.
    pp=np.array([.1,.25,.5,.7,.9]);truth=np.array([.08,.4]);pm,ps=transition_probability(np.log(truth),pp,5.)
    fixture=fit(pp,np.full(5,200.),np.full(5,80.),200*pm,80*ps,start)
    assert max(abs(np.array(fixture['rates'])-truth))<1e-5,fixture
    fitted.update(training_seed=29,frozen=True,old_rates=start,old_same_numerator_all_exposure=naive,
        trials=int(sum(nm+ns)),all_current_population=int(sum(z['n'] for z in samples)),
        unsupported_onset_events=int(sum(on[p==0])),unsupported_release_events=int(sum(off[p==1])),
        fixture=fixture,input_sha256=pins)
    h.save(HERE/'frozen_fit.json',fitted)
    original=h.read(OLD/'executed_function_sources.json');exact=copy.deepcopy(original)
    assert original['RouteLaneRegion'].count(OLD_TRANSITION)==1
    exact['RouteLaneRegion']=original['RouteLaneRegion'].replace(OLD_TRANSITION,EXACT_TRANSITION)
    assert all(exact[k]==v for k,v in original.items() if k!='RouteLaneRegion')
    h.save(HERE/'exact_function_sources.json',exact)
    spec=h.read(OLD/'spec.json')
    for label,records,code,rates in [('parity','parity',original,start),('operator_train','train',exact,start),
        ('refit_train','train',exact,fitted['rates']),('operator_validation','validation',exact,start),
        ('refit_validation','validation',exact,fitted['rates'])]:
        folder=HERE/label;folder.mkdir()
        ss=copy.deepcopy(spec);ss['queue178'].update(formation_per_sec=rates[0],release_per_sec=rates[1])
        h.save(folder/'spec.json',ss);h.save(folder/'coefficients.json',ss['queue178'])
        h.save(folder/'executed_function_sources.json',code)
        h.save(folder/'protocol.json',proto);h.save(folder/'pins.json',pins)
        h.save(folder/'setting.json',dict(manifest=str(manifest),structure='queue',records=records))
    print(json.dumps({k:v for k,v in fitted.items() if k not in ('history','input_sha256','fixture')}))


if __name__=='__main__':main()
