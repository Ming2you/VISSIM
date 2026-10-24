"""Independent feature/fit checks and one no-fit GKT moment diagnostic."""
from collections import Counter,defaultdict
from bisect import bisect_right
from pathlib import Path
import math
import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def positive_gaussian_second(mu,var):
    if var<1e-14:return max(mu,0.)**2
    sd=math.sqrt(var);z=mu/sd
    return (var+mu*mu)*(.5*(1+math.erf(z/math.sqrt(2))))+mu*sd*math.exp(-.5*z*z)/math.sqrt(2*math.pi)


def main():
    protocol=h.read(HERE/'protocol.json');models=h.read(HERE/'frozen_models.json')
    rows=h.read(HERE/'rows.json.gz');summary=h.read(HERE/'summary.json')
    old=h.read(h.R/'state_information92/protocol.json')
    files={k:h.ROOT/v['path'] for k,v in old['inputs'].items() if not k.startswith('67')}
    files.update({f'67_{arm}':h.R/'blocking176'/f'{arm}_frames.json.gz'
                  for arm in ('hold','release','hold_vsl90','release_vsl90')})
    lengths=np.diff(h.read(h.F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']['segment_bounds_m'])
    sample_errors=[];target_context=[];count=0
    current_groups=defaultdict(list)
    for case,path in files.items():
        d=h.read(path);ix={k:i for i,k in enumerate(d['fields'])};rich='speed' in ix
        ci,li,vi,xi=[ix[k] for k in ('cell','lane','speed' if rich else 'speed_kmh','x' if rich else 'x_m')]
        frames={round(float(t),6):v for t,v in d['frames'].items()}
        grouped=defaultdict(list)
        for r in rows:
            if r['case']==case:grouped[r['t']].append(r)
        for t,rr in grouped.items():
            frame=frames[t];past=frames[round(t-5,6)];future=frames[round(t+5,6)]
            by=defaultdict(list);stats=defaultdict(list)
            def road(x):
                if 6847.981<=x<7431.364:return 119
                if 7438.047<=x<10784.028:return 24
                return 0
            for vid,z in frame.items():
                if road(z[xi]):by[road(z[xi]),z[li]].append((z[xi],vid))
                stats[z[ci],z[li]].append(z[vi])
            for key in by:by[key].sort()
            for r in rr:
                vid=r['id'];z=frame[vid];cell,lane=z[ci],z[li]
                ordered=by[road(z[xi]),lane]
                idx=bisect_right(ordered,(z[xi],vid));leader=ordered[idx][1]
                assert leader==r['leader']
                lead=frame[leader];space=lead[xi]-z[xi]
                state=[(len(stats[c,lane])/(lengths[c]/1000),np.mean(stats[c,lane])) for c in (cell-1,cell,cell+1)]
                up,own,down=state;rho,v=own
                features=[z[vi],rho,v,*up,*down,z[vi]-past[vid][vi],rho*rho,rho*v,
                          float(cell==21),float(cell==24),float(cell==25),
                          lead[vi]-z[vi],space-lengths[cell]/len(stats[cell,lane]),
                          max(0.,(z[vi]-lead[vi])/3.6)**2/space]
                sample_errors.append(max(abs(a-b) for a,b in zip(features,r['x'])))
                assert abs(future[vid][vi]-z[vi]-r['y'])<1e-10
                assert len(features)==16 and space>0 and road(z[xi])==road(lead[xi])
                count+=1
            # Unfiltered CURRENT pairs: no survival/lane-change censoring in moments.
            for key,ordered in by.items():
                for (_,vid),(_,leadid) in zip(ordered,ordered[1:]):
                    z,lead=frame[vid],frame[leadid]
                    if z[ci] not in (20,21,24,25):continue
                    current_groups[case,t,int(z[ci]),int(z[li])].append((z[vi],lead[vi]))
                    if not rich:continue
                    target=frame.get(str(z[ix['target']]))
                    category=('unobserved' if target is None or z[ix['target_type']]!='Vehicle' else
                              'geometric_leader' if str(z[ix['target']])==leadid else
                              'other_lane' if target[li]!=z[li] else 'other_same_lane')
                    slow=z[vi]<20
                    state=('front_pulling_away' if lead[vi]-z[vi]>=10 else
                           'approaching_slower_front' if z[vi]-lead[vi]>=10 else 'near_equal_speed')
                    target_context.append(dict(case=case,t=t,cell=int(z[ci]),lane=int(z[li]),
                       v=z[vi],leader_v=lead[vi],front_spacing_m=lead[xi]-z[xi],
                       native_accel=z[ix['accel']],native_target=category,
                       slow=slow,relative_state=state,lnchg=z[ix['lnchg']]))
    assert count==len(rows)==79188 and max(sample_errors)<1e-9
    # Different numerical solver: weighted QR least squares, including ridge rows.
    fit_errors={}
    train=[r for r in rows if r['case'].startswith('29')]
    sizes=Counter((r['case'],r['t'],r['cell'],r['lane']) for r in train)
    weights=np.array([1/sizes[r['case'],r['t'],r['cell'],r['lane']] for r in train])
    for name,m in models.items():
        p=len(m['features']);x=np.array([r['x'][:p] for r in train]);y=np.array([r['y'] for r in train])
        mean=np.average(x,axis=0,weights=weights);sd=np.sqrt(np.average((x-mean)**2,axis=0,weights=weights))
        assert max(abs(mean-m['mean']))<1e-8 and max(abs(sd-m['sd']))<1e-8
        a=np.column_stack([np.ones(len(x)),(x-mean)/sd]);penalty=np.eye(p+1);penalty[0,0]=0
        beta=np.linalg.lstsq(np.vstack([a*np.sqrt(weights[:,None]),penalty]),
                            np.r_[y*np.sqrt(weights),np.zeros(p+1)],rcond=None)[0]
        fit_errors[name]=float(max(abs(beta-m['beta'])));assert fit_errors[name]<1e-8
    # Post-gate DESCRIPTIVE moment comparison, no fitting or adoption gate change.
    # Empirical E[(v-w)_+^2] vs Gaussian closure with measured pair covariance,
    # and exactly the same marginals with covariance set to zero.
    moments=[]
    for (case,t,cell,lane),pairs in current_groups.items():
        if len(pairs)<5:continue
        a=np.array(pairs)/3.6;u,w=a.T;dv=u-w
        mu=float(np.mean(dv));var=float(np.var(dv));v0=float(np.var(u)+np.var(w))
        truth=float(np.mean(np.maximum(dv,0)**2))
        cov=float(np.mean((u-u.mean())*(w-w.mean())))
        assert abs(var-(v0-2*cov))<1e-10
        moments.append(dict(case=case,t=t,cell=cell,lane=lane,n=len(pairs),
                            empirical=truth,paired_gaussian=positive_gaussian_second(mu,var),
                            independent_gaussian=positive_gaussian_second(mu,v0),covariance=cov))
    moment_summary=[]
    for case in files:
        rr=[r for r in moments if r['case']==case]
        moment_summary.append(dict(case=case,groups=len(rr),
            empirical_mean=float(np.mean([r['empirical'] for r in rr])),
            measured_pair_covariance_mean=float(np.mean([r['covariance'] for r in rr])),
            **{f'{m}_rmse':math.sqrt(float(np.mean([(r[m]-r['empirical'])**2 for r in rr])))
               for m in ('paired_gaussian','independent_gaussian')}))
    reactions=[];targets=[]
    for case in sorted({r['case'] for r in target_context}):
        for slow in (True,False):
            for state in ('front_pulling_away','approaching_slower_front','near_equal_speed'):
                rr=[r for r in target_context if r['case']==case and r['slow']==slow and r['relative_state']==state]
                if not rr:continue
                reactions.append(dict(case=case,below20=slow,state=state,n=len(rr),
                    mean_native_accel=float(np.mean([r['native_accel'] for r in rr])),
                    mean_own_speed=float(np.mean([r['v'] for r in rr])),
                    mean_front_spacing=float(np.mean([r['front_spacing_m'] for r in rr]))))
        rr=[r for r in target_context if r['case']==case]
        targets.append(dict(case=case,n=len(rr),counts=dict(Counter(r['native_target'] for r in rr)),
                            active_lanechange=sum(r['lnchg'] in ('Left','Right') for r in rr)))
    h.save(HERE/'moment_context.json',dict(added_after_information_gate=True,fits=0,
        note='Observed current pairs, >=5pairs/group. All Gaussian inputs measured, not autonomously predicted. Independent covariance0 closure is not the existing METANET. RMSE units(m/s)^2, no gap/exposure coefficient so NOT an acceleration/flow error. No causal control comparison.',
        summary=moment_summary,reactions=reactions,all_current_targets=targets))
    from diagnostics.repin_v3c3_review_20261001.neighbor_information194.check import savegz
    savegz(HERE/'moment_rows.json.gz',moments)
    for p,digest in {**protocol['input_sha256'],**protocol['protected_sha256']}.items():assert h.sha(p)==digest,p
    assert h.sha(protocol['STOP']['path'])==protocol['STOP']['sha256']
    assert h.sha(HERE/'frozen_models.json')==h.read(HERE/'completion.json')['frozen_models_sha256']
    h.save(HERE/'verification.json',dict(feature_records=count,feature_components=count*16,
         max_feature_error=max(sample_errors),fit_qr_beta_max_error=fit_errors,
         moment_groups=len(moments),current_native_pairs=len(target_context),
         input_core_STOP_unchanged=True,coefficient_freeze_verified=True))
    print(dict(verification=h.read(HERE/'verification.json'),moment_summary=moment_summary,targets=targets))


if __name__=='__main__':main()
