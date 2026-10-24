"""Current ordered-neighbor information gate, not an autonomous traffic model.

Two fixed regressions fit seed29 only. Current geometry defines the leader;
future snapshots supply the same-vehicle response label and censoring only.
No FZP/COM/controller execution or production edits.
"""
from collections import Counter, defaultdict
from pathlib import Path
import gzip
import json
import math
import time
import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent
CELLS = (20, 21, 24, 25)
BASE = ['vehicle_v', 'lane_rho', 'lane_v', 'up_rho', 'up_v',
        'down_rho', 'down_v', 'past5_vehicle_dv', 'rho_squared',
        'rho_times_v', 'cell21', 'cell24', 'cell25']
EXTRA = ['leader_minus_vehicle_v', 'front_spacing_minus_uniform_spacing',
         'positive_closing_speed_squared_per_spacing']


def savegz(path, value):
    path.write_bytes(gzip.compress(json.dumps(value, ensure_ascii=False,
                                allow_nan=False).encode(), mtime=0))


def normalize(d):
    ix = {s:i for i,s in enumerate(d['fields'])}
    rich = 'speed' in ix
    out = {}
    for t, frame in d['frames'].items():
        out[round(float(t), 6)] = {k:dict(
            cell=int(z[ix['cell']]), lane=int(z[ix['lane']]),
            v=float(z[ix['speed' if rich else 'speed_kmh']]),
            x=float(z[ix['x' if rich else 'x_m']]),
            **({s:z[ix[s]] for s in ('link','length','target','target_type',
                                    'accel','lnchg','interaction')} if rich else {}))
            for k,z in frame.items()}
    return out


def physical_link(x):
    # No cross-connector lane-number inference. Both links are three-lane.
    if 6847.981 <= x < 7431.364: return 119
    if 7438.047 <= x < 10784.028: return 24
    return None


def extract(case, frames, lengths):
    rows = []; counts = Counter(); context = []
    for t, fr in sorted(frames.items()):
        prev = frames.get(round(t-5, 6)); future = frames.get(round(t+5, 6))
        if prev is None or future is None: continue
        by_lane = defaultdict(list); stats = defaultdict(list)
        for vid,z in fr.items():
            stats[z['cell'],z['lane']].append(z['v'])
            road = physical_link(z['x'])
            if road is not None: by_lane[road,z['lane']].append((z['x'],vid))
        means = {key:(len(vs)/(lengths[key[0]]/1000),float(np.mean(vs)),len(vs))
                 for key,vs in stats.items()}
        leaders = {}
        for items in by_lane.values():
            items.sort()
            for (_,vid),(_,lid) in zip(items,items[1:]): leaders[vid] = lid
        for vid,z in fr.items():
            cell,lane = z['cell'],z['lane']
            if cell not in CELLS: continue
            counts['current_target_cell_samples'] += 1
            road = physical_link(z['x'])
            if vid not in leaders: counts['no_observed_same_link_leader'] += 1; continue
            lid = leaders[vid]; lead = fr[lid]; gap = lead['x']-z['x']
            if gap <= 0: counts['zero_or_negative_front_spacing'] += 1; continue
            if vid not in prev or vid not in future: counts['missing_past_or_future_vehicle'] += 1; continue
            old,new = prev[vid],future[vid]
            if any(a['lane'] != lane or physical_link(a['x']) != road for a in (old,new)):
                counts['endpoint_lane_or_link_change'] += 1; continue
            keys = [(j,lane) for j in (cell-1,cell,cell+1)]
            if any(key not in means or means[key][2]<2 for key in keys):
                counts['sparse_current_lane_or_neighbor'] += 1; continue
            up,own,down = [means[k] for k in keys]
            v=z['v']; rho,mean,n=own
            features = [v,rho,mean,up[0],up[1],down[0],down[1],v-old['v'],
                        rho*rho,rho*mean,float(cell==21),float(cell==24),float(cell==25)]
            # Front-to-front spacing (all six older caches lack length), not net gap.
            closing = max(0.,(v-lead['v'])/3.6)
            features += [lead['v']-v, gap-lengths[cell]/n, closing*closing/gap]
            rows.append(dict(case=case,t=t,cell=cell,lane=lane,id=vid,leader=lid,
                             x=features,y=new['v']-v,gap_m=gap,
                             future_leader_same_lane=(lid in future and future[lid]['lane']==lane),
                             current_lnchg=z.get('lnchg'),future_lnchg=new.get('lnchg')))
            counts['used'] += 1
            if 'target' in z:
                target=fr.get(str(z['target'])); a=float(z['accel'])
                category=('not_vehicle' if z['target_type']!='Vehicle' else
                          'not_in_mainline_cache' if target is None else
                          'geometric_leader' if str(z['target'])==lid else
                          'different_lane' if target['lane']!=lane else 'other_same_lane')
                context.append(dict(case=case,t=t,cell=cell,lane=lane,v=v,accel=a,
                                    gap_m=gap,leader_v=lead['v'],category=category,
                                    target_ahead=(target is not None and target['x']>z['x']),
                                    lnchg=z['lnchg'],future_dv=new['v']-v))
    return rows,dict(counts),context


def fit(rows, p):
    x=np.array([r['x'][:p] for r in rows]); y=np.array([r['y'] for r in rows])
    # Each beginning cell/lane/time contributes equally despite different N.
    sizes=Counter((r['case'],r['t'],r['cell'],r['lane']) for r in rows)
    w=np.array([1/sizes[r['case'],r['t'],r['cell'],r['lane']] for r in rows])
    mean=np.average(x,axis=0,weights=w)
    sd=np.sqrt(np.average((x-mean)**2,axis=0,weights=w)); sd=np.maximum(sd,1e-8)
    a=np.column_stack([np.ones(len(x)),(x-mean)/sd])
    penalty=np.eye(p+1);penalty[0,0]=0
    lhs=a.T@(w[:,None]*a)+penalty;rhs=a.T@(w*y)
    beta=np.linalg.solve(lhs,rhs)
    return dict(features=(BASE+EXTRA)[:p],mean=mean.tolist(),sd=sd.tolist(),
                beta=beta.tolist(),normal_equation_residual=float(max(abs(lhs@beta-rhs))))


def predict(row, model):
    p=len(model['mean']);x=np.array(row['x'][:p])
    return float(np.r_[1.,(x-model['mean'])/model['sd']]@model['beta'])


def score(rows):
    grouped=defaultdict(list)
    for r in rows:grouped[r['case'],r['t'],r['cell'],r['lane']].append(r)
    summaries=[]
    for case in sorted({r['case'] for r in rows}):
        rr=[r for r in rows if r['case']==case]
        groups=[v for k,v in grouped.items() if k[0]==case]
        for cell in (None,*CELLS):
            gs=[g for g in groups if cell is None or g[0]['cell']==cell]
            if not gs:continue
            ans=dict(case=case,cell=cell,vehicle_pairs=sum(map(len,gs)),lane_frames=len(gs))
            for model in ('persistence','mean','ordered'):
                errors=[[(r.get(model,0)-r['y']) for r in g] for g in gs]
                ans[model+'_vehicle_rmse']=math.sqrt(float(np.mean([np.mean(np.square(e)) for e in errors])))
                ans[model+'_group_rmse']=math.sqrt(float(np.mean([np.mean(e)**2 for e in errors])))
            ans['ordered_nonphysical_future_speed']=sum(not 0 <= r['x'][0]+r['ordered'] <= 160 for g in gs for r in g)
            summaries.append(ans)
    return summaries


def main():
    assert not (HERE/'protocol.json').exists(),'Preserve previous run, no automatic retry'
    started=time.perf_counter()
    protected=h.read(h.R/'lateral_state193/protocol.json')
    pins={str(Path(__file__)):h.sha(__file__)}
    old=h.read(h.R/'state_information92/protocol.json')
    mapping=h.F/'route_inventory/mapping31.json';pins[str(mapping)]=h.sha(mapping)
    lengths=np.diff(h.read(mapping)['freeway_model_links']['FW_E']['segment_bounds_m'])
    files={k:h.ROOT/v['path'] for k,v in old['inputs'].items() if not k.startswith('67')}
    files.update({f'67_{arm}':h.R/'blocking176'/f'{arm}_frames.json.gz'
                  for arm in ('hold','release','hold_vsl90','release_vsl90')})
    pins.update({str(p):h.sha(p) for p in files.values()})
    protocol=dict(
        scope='Current-state information diagnostic, NOT METANET accuracy comparison or an operational model.',
        question='Does current ordered same-link leader spacing/relative speed add transferable5s material response information beyond mean lane states?',
        train='seed29 none/vsl only; fit then freeze before43/67 evaluation',cells=CELLS,
        base_features=BASE,ordered_extra=EXTRA,
        population='Same vehicle at t-5,t,t+5 with endpoint lane/link unchanged; current/future lane changes between snapshots remain censored. Not all vehicles/flow or cumulative TTT.',
        geometry='Immediate current front-to-front leader in same link119/24 and lane. Missing leader is unknown, never free space. No invented vehicle lengths.',
        regression='Two weighted standardized ridge1 fits, unpenalized intercept; each current cell/lane/time equal weight; no seed/time/command feature, no grids.',
        gate='Each heldout seed pooled groupRMSE improves10%; no arm groupRMSE worsens10%; report vehicleRMSE/nonphysical values separately. Only information justification, never gain qualification.',
        budget=dict(fits=2,autonomous=0,native=0,FZP=0),
        prior_reviewed=['Claude upstream worklog','92 aggregate variance screen','165 convection','176/177 queue onset','193 LCcount','20260921 ORDERED_RELATIVE_RESPONSE_GATE fixed-geometry failures'],
        literature=['https://mtreiber.de/publications/MASTER.pdf','https://journals.aps.org/pre/abstract/10.1103/PhysRevE.59.239','https://its.berkeley.edu/publications/lane-changing-traffic-streams'],
        limitations='Known historically inspected states, not freshblind; conditional on observed neighborhood and endpoint survival; different policy populations. No causal efficacy/capacity claim or autonomous closure.',
        input_sha256=pins,protected_sha256=protected['protected_sha256'],STOP=protected['STOP'])
    h.save(HERE/'protocol.json',protocol)
    for p,d in protected['protected_sha256'].items():assert h.sha(p)==d,p
    assert h.sha(protected['STOP']['path'])==protected['STOP']['sha256']
    rows=[];counts={};context=[]
    for case in ('29_none','29_vsl'):
        rr,counts[case],cc=extract(case,normalize(h.read(files[case])),lengths);rows+=rr;context+=cc
    models={name:fit(rows,p) for name,p in [('mean',len(BASE)),('ordered',len(BASE+EXTRA))]}
    h.save(HERE/'frozen_models.json',models);frozen=h.sha(HERE/'frozen_models.json')
    for case in files:
        if case.startswith('29'):continue
        rr,counts[case],cc=extract(case,normalize(h.read(files[case])),lengths);rows+=rr;context+=cc
    for r in rows:
        for name,model in models.items():r[name]=predict(r,model)
    summaries=score(rows)
    pooled=[r for r in summaries if r['cell'] is None and not r['case'].startswith('29')]
    gates={}
    for seed in ('43','67'):
        rr=[r for r in pooled if r['case'].startswith(seed)]
        rmse={m:math.sqrt(sum(r[m+'_group_rmse']**2*r['lane_frames'] for r in rr)/sum(r['lane_frames'] for r in rr))
              for m in ('mean','ordered')}
        gates[seed]=dict(rmse=rmse,improvement=1-rmse['ordered']/rmse['mean'],
                        improves10=rmse['ordered']<=.9*rmse['mean'],
                        no_arm_worse10=all(r['ordered_group_rmse']<=1.1*r['mean_group_rmse'] for r in rr))
    # Native interaction target is a validation label, never a regression input.
    contexts=[]
    for case in sorted({r['case'] for r in context}):
        for braking in (False,True):
            rr=[r for r in context if r['case']==case and (r['accel']<-.5 if braking else True)]
            contexts.append(dict(case=case,subset='accel_below_minus0.5' if braking else 'all_used',
                                 count=len(rr),target_category=dict(Counter(r['category'] for r in rr))))
    savegz(HERE/'rows.json.gz',rows);savegz(HERE/'native_context_rows.json.gz',context)
    h.save(HERE/'summary.json',dict(scores=summaries,gates=gates,population_counts=counts,native_target=contexts,
        fits=2,elapsed_seconds=time.perf_counter()-started,production_adopted=False,
        information_gate_pass=all(g['improves10'] and g['no_arm_worse10'] for g in gates.values())))
    for p,d in {**pins,**protected['protected_sha256']}.items():assert h.sha(p)==d,p
    assert h.sha(protected['STOP']['path'])==protected['STOP']['sha256']
    assert h.sha(HERE/'frozen_models.json')==frozen
    h.save(HERE/'completion.json',dict(status='complete_information_diagnostic',rows=len(rows),
        frozen_models_sha256=frozen,source_sha256=h.sha(__file__),protected_unchanged=True,
        goal='ACTIVE_NOT_QUALIFIED',autonomous=0,native=0,FZP=0,push=0))
    print(json.dumps(dict(gates=gates,rows=len(rows),summary=[r for r in summaries if r['cell'] is None]),ensure_ascii=False))


def recovery206():
    """Four bounded information fits; native leader acceleration is NOT an operational input."""
    def expit(z):return np.exp(-np.logaddexp(0.,-z))
    work=HERE.parent/'recovery_memory206';started=time.perf_counter()
    assert not (work/'protocol.json').exists(),'No overwrite or automatic fit retry'
    base=['v','lane_rho','lane_v','down_rho','down_v','leader_v','log_front_spacing','own_past5_dv']
    extra=['same_leader_past5_dv']
    old=h.read(h.R/'state_information92/protocol.json')
    files={k:h.ROOT/v['path'] for k,v in old['inputs'].items() if not k.startswith('67')}
    files.update({f'67_{arm}':h.R/'blocking176'/f'{arm}_frames.json.gz'
                  for arm in ('hold','release','hold_vsl90','release_vsl90')})
    geometry=h.F/'route_inventory/mapping31.json'
    lengths=np.diff(h.read(geometry)['freeway_model_links']['FW_E']['segment_bounds_m'])
    pins={str(p):h.sha(p) for p in (*files.values(),geometry)}
    core=h.read(h.R/'regional_audit202/protocol.json')['source_sha256']
    protocol=dict(previous_goal_turn='PROGRESS205 observed target chain',
        question='Does the current geometric leader recent speed increase identify restart phase beyond current spacing/speed/density?',
        scope='Conditional same-vehicle next5s stop/restart; not a METANET rollout, TTT or autonomous gain validation.',
        cells=list(range(19,26)),train='29_none and29_vsl only; all cached750s; freeze before43 and67',
        evaluation='Previously inspected43 two arms and67 four arms. Not blind whole-model validation.',
        population='Current lane/link119/24 with observed geometric leader, same leader ID and lane/link also observed t-5; own t-5 same lane/link; nonempty own/down lane; future same vehicle must remain observed, possibly elsewhere. No future leader condition.',
        threshold_kmh=5,base_features=base,extra_features=extra,
        fit='Four standardized logistic ridge1 fits, unpenalized intercept, beta box[-10,10], projected damped Newton max200,20 line-search steps. Each current cell/lane/time/state has total weight1. No search/retry/bound expansion.',
        budget=dict(fits=4,autonomous=0,native=0,FZP=0),
        gate='Each heldout seed and both stop/restart pooled Brier must improve at least5%; no arm Brier worsens10%; both transition-count contrastRMSE must not worsen. Failure means no physical integration from this feature alone.',
        caution='Past5 finite speed change is not instantaneous acceleration or an identified sub5s reaction time. Conditional selected population and actual neighbor history; no causality or flow conservation supplied by this classifier.',
        input_sha256=pins,source_sha256=core,previous_reviewed=['92','114','118','178','183','194','197neighbor renewal','205','Claude03_codex_review'])
    h.save(work/'protocol.json',protocol)
    counts={};all_rows=[]
    def extract_phase(case):
        frames=normalize(h.read(files[case]));ts=sorted(frames);counter=Counter();rows=[]
        for t in ts:
            if round(t-5,6) not in frames or round(t+5,6) not in frames:continue
            fr=frames[t];past=frames[round(t-5,6)];future=frames[round(t+5,6)]
            ordered=defaultdict(list);groups=defaultdict(list)
            for vid,z in fr.items():
                road=physical_link(z['x'])
                if road is not None:ordered[road,z['lane']].append((z['x'],vid))
                groups[z['cell'],z['lane']].append(z['v'])
            leads={}
            for g in ordered.values():
                g.sort();leads.update({a[1]:b[1] for a,b in zip(g,g[1:])})
            for vid,z in fr.items():
                if not 19<=z['cell']<=25:continue
                counter['current_cells19_25']+=1
                lid=leads.get(vid)
                if lid is None:counter['no_same_link_leader']+=1;continue
                if vid not in past or lid not in past:counter['no_past_own_or_leader']+=1;continue
                leader=fr[lid];p=past[vid];pl=past[lid];road=physical_link(z['x'])
                if any(physical_link(a['x'])!=road or a['lane']!=z['lane'] for a in (p,pl)):
                    counter['past_lane_link_differ']+=1;continue
                own=groups[z['cell'],z['lane']];down=groups[z['cell']+1,z['lane']]
                if not down:counter['empty_down_lane']+=1;continue
                gap=leader['x']-z['x']
                if gap<=0:counter['nonpositive_spacing']+=1;continue
                if vid not in future:counter['missing_future_not_labeled']+=1;continue
                n=future[vid];state='restart' if z['v']<5 else 'stop'
                x=[z['v'],len(own)/(lengths[z['cell']]/1000),float(np.mean(own)),
                   len(down)/(lengths[z['cell']+1]/1000),float(np.mean(down)),leader['v'],math.log1p(gap),
                   z['v']-p['v'],leader['v']-pl['v']]
                y=int(n['v']>=5) if state=='restart' else int(n['v']<5)
                rows.append(dict(case=case,t=t,t0=ts[0],block=int(round((t-ts[0])/5))//30,
                    cell=z['cell'],lane=z['lane'],id=vid,leader=lid,state=state,x=x,y=y,
                    future_v=n['v'],future_cell=n['cell'],future_lane=n['lane']))
                counter['used_'+state]+=1
        counts[case]=dict(counter)
        return rows
    def fit_phase(rows,p):
        x=np.asarray([z['x'][:p] for z in rows]);y=np.asarray([z['y'] for z in rows],float)
        groups=Counter((z['case'],z['t'],z['cell'],z['lane']) for z in rows)
        w=np.asarray([1/groups[z['case'],z['t'],z['cell'],z['lane']] for z in rows])
        mu=np.average(x,weights=w,axis=0);sd=np.sqrt(np.average((x-mu)**2,weights=w,axis=0));sd=np.maximum(sd,1e-8)
        a=np.c_[np.ones(len(x)),(x-mu)/sd];penalty=np.r_[0.,np.ones(p)]
        def loss(beta):
            eta=a@beta
            return (float(w@(np.logaddexp(0.,eta)-y*eta)+.5*np.dot(penalty*beta,beta)),
                    a.T@(w*(expit(eta)-y))+penalty*beta)
        beta=np.zeros(p+1)
        for iteration in range(200):
            value,gradient=loss(beta);projected=beta-np.clip(beta-gradient,-10,10)
            if max(abs(projected))<1e-6:break
            probability=expit(a@beta)
            hessian=a.T@((w*probability*(1-probability))[:,None]*a)+np.diag(penalty)
            direction=-np.linalg.solve(hessian,gradient)
            proposal=np.clip(beta+direction,-10,10)
            if np.dot(gradient,proposal-beta)>=0:proposal=np.clip(beta-gradient,-10,10)
            delta=proposal-beta
            for line in range(20):
                trial=beta+(2.**-line)*delta
                if loss(trial)[0]<=value+1e-4*np.dot(gradient,trial-beta):
                    beta=trial;break
            else:raise AssertionError('Bounded Newton line search failed')
        value,gradient=loss(beta);projected=beta-np.clip(beta-gradient,-10,10)
        assert max(abs(projected))<.002,(iteration,max(abs(projected)))
        return dict(features=(base+extra)[:p],mean=mu.tolist(),sd=sd.tolist(),beta=beta.tolist(),
            rows=len(rows),groups=len(groups),loss=value,iterations=iteration+1,
            projected_gradient_max=float(max(abs(projected))),bound_hits=int(sum(abs(beta)>9.999)))
    train=extract_phase('29_none')+extract_phase('29_vsl');all_rows.extend(train)
    models={}
    for state in ('stop','restart'):
        selected=[z for z in train if z['state']==state]
        for name,p in (('current',len(base)),('memory',len(base+extra))):models[state+'_'+name]=fit_phase(selected,p)
    h.save(work/'frozen_models.json',models);frozen=h.sha(work/'frozen_models.json')
    for case in files:
        if not case.startswith('29'):all_rows.extend(extract_phase(case))
    for z in all_rows:
        for name in ('current','memory'):
            m=models[z['state']+'_'+name];p=len(m['mean'])
            z[name]=float(expit(np.r_[1.,(np.asarray(z['x'][:p])-m['mean'])/m['sd']]@m['beta']))
    score=[];blocks=[]
    for case in files:
        for state in ('stop','restart'):
            rr=[z for z in all_rows if z['case']==case and z['state']==state]
            sizes=Counter((z['t'],z['cell'],z['lane']) for z in rr)
            weights=np.asarray([1/sizes[z['t'],z['cell'],z['lane']] for z in rr])
            s=dict(case=case,state=state,rows=len(rr),groups=len(sizes),actual=sum(z['y'] for z in rr))
            for name in ('current','memory'):
                pp=np.array([z[name] for z in rr]);yy=np.array([z['y'] for z in rr])
                s[name+'_expected']=float(pp.sum())
                s[name+'_brier']=float(np.average((pp-yy)**2,weights=weights))
            score.append(s)
            for block in sorted({z['block'] for z in rr}):
                q=[z for z in rr if z['block']==block]
                blocks.append(dict(case=case,state=state,block=block,rows=len(q),actual=sum(z['y'] for z in q),
                    current=sum(z['current'] for z in q),memory=sum(z['memory'] for z in q)))
    pairs=[('43_none','43_vsl'),('67_hold','67_release'),('67_hold','67_hold_vsl90'),('67_release','67_release_vsl90')]
    contrasts=[];index={(z['case'],z['state'],z['block']):z for z in blocks}
    for first,second in pairs:
        for state in ('stop','restart'):
            for block in sorted({z['block'] for z in blocks if z['case']==first and z['state']==state}):
                a=index[first,state,block];b=index[second,state,block]
                contrasts.append(dict(seed=first[:2],first=first,second=second,state=state,block=block,
                    **{m:b[m]-a[m] for m in ('actual','current','memory')}))
    gates=[]
    for seed in ('43','67'):
        for state in ('stop','restart'):
            ss=[z for z in score if z['case'].startswith(seed) and z['state']==state]
            cc=[z for z in contrasts if z['seed']==seed and z['state']==state]
            metrics={}
            for name in ('current','memory'):
                metrics[name+'_brier']=sum(z[name+'_brier']*z['groups'] for z in ss)/sum(z['groups'] for z in ss)
                metrics[name+'_contrast_rmse']=math.sqrt(float(np.mean([(z[name]-z['actual'])**2 for z in cc])))
            gates.append(dict(seed=seed,state=state,**metrics,
                brier_improves5=metrics['memory_brier']<=.95*metrics['current_brier'],
                no_arm_worsens10=all(z['memory_brier']<=1.1*z['current_brier'] for z in ss),
                contrast_not_worse=metrics['memory_contrast_rmse']<=metrics['current_contrast_rmse']))
    for p,digest in pins.items():assert h.sha(p)==digest
    for p,digest in core.items():assert h.sha(h.ROOT/p)==digest
    assert h.sha(work/'frozen_models.json')==frozen
    stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert h.sha(stop)=='91b2163b02b01447242909dee8e7f773d18e76a6594bd9db8de64d2a48246fc3'
    savegz(work/'rows.json.gz',all_rows);h.save(work/'blocks.json',blocks);h.save(work/'contrasts.json',contrasts)
    h.save(work/'summary.json',dict(status='COMPLETE_CONDITIONAL_INFORMATION_TEST',rows=len(all_rows),
        fits=4,scores=score,gates=gates,population_counts=counts,
        information_gate_pass=all(z['brier_improves5'] and z['no_arm_worsens10'] and z['contrast_not_worse'] for z in gates),
        frozen_sha256=frozen,seconds=time.perf_counter()-started,source_sha256=h.sha(__file__),
        autonomous=0,native=0,FZP=0,goal='ACTIVE_NOT_QUALIFIED'))
    print(json.dumps(dict(rows=len(all_rows),gates=gates,seconds=time.perf_counter()-started)))


def variance213():
    """One measured pressure-gradient information fit; no plant mutation."""
    import ctypes
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    work=HERE.parent/'variance_pressure213';started=time.perf_counter()
    assert not (work/'protocol.json').exists(),'Preserve all attempts; no automatic fit retry'
    old=h.read(h.R/'state_information92/protocol.json')
    files={k:h.ROOT/v['path'] for k,v in old['inputs'].items() if not k.startswith('67')}
    files.update({f'67_{arm}':h.R/'blocking176'/f'{arm}_frames.json.gz'
                  for arm in ('hold','release','hold_vsl90','release_vsl90')})
    mapping=h.F/'route_inventory/mapping31.json'
    cache=HERE/'rows.json.gz';baseline=HERE/'frozen_models.json'
    pins={str(p):h.sha(p) for p in (*files.values(),mapping,cache,baseline,Path(__file__))}
    protected=h.read(h.R/'restart_supply210/protocol.json')
    core=protected['source_sha256'];stop=protected['STOP']
    h.save(work/'protocol.json',dict(previous_turn='PROGRESS212: observed origin partition verified; no adoption.',
        hypothesis='Does the spatial gradient of current within-lane velocity variance add transferable material speed response information beyond194 current means/ordered neighbor features?',
        distinction='92 used own aggregate standard deviation;194/196 evaluated approaching-pair braking moments. This single feature is a current adjacent-lane pressure difference, not their rerun or an added VSL bonus.',
        literature='https://mtreiber.de/publications/MASTER.pdf Eq2 pressure P=rho*theta; this is only an information screen, not full GKT or a replacement METANET model.',
        feature='-5*(rho_down*theta_down-rho*theta)/(rho*0.5*(L+L_down)*3600); rho veh/km/lane,theta (km/h)^2,L km; feature km/h over5s. Forward cell-center difference, no future state.',
        target='Same endpoint-surviving cohort5s material speed change from194; not total cell mean, flow or TTT. All current vehicles define moments, not only future survivors.',
        train='29 none/vsl only; freeze before43/67 inference. Same79188 rows and equal cell/lane/time weights as194.',
        fitting='One augmented standardized ridge1 least squares, unpenalized intercept, pressure coefficient>=0. Other16 covariates refit. Original194 ordered baseline reused; no threshold/grid search.',
        gate='Both43/67 pooled groupRMSE improve10pct over frozen194 ordered; no arm worsens10pct. Conditional policy-block response MSE also must not worsen. Otherwise no autonomous candidate or new variance state.',
        budget=dict(fits=1,forecasts=0,native=0,FZP=0),
        input_sha256=pins,source_sha256=core,STOP=stop,
        limits='Known inspected seeds, endpoint-survival selection, correlated repeated samples, finite spatial support. Even a pass is not autonomous prediction, VSL causality or wholeOmega qualification. No pressure term is added to METANET.'))
    assert all(h.sha(h.ROOT/p)==sha for p,sha in core.items()) and h.sha(stop['path'])==stop['sha256']
    lengths=np.diff(h.read(mapping)['freeway_model_links']['FW_E']['segment_bounds_m'])/1000
    raw=h.read(cache);original_model=h.read(baseline)['ordered']
    records=[];moments=[]
    def extract(case):
        frames=normalize(h.read(files[case]));cached={};out=[]
        for r in raw:
            if r['case']!=case:continue
            key=(r['t'],r['cell'],r['lane'])
            if key not in cached:
                t,c,g=key;fr=frames[t]
                own=[z['v'] for z in fr.values() if (z['cell'],z['lane'])==(c,g)]
                down=[z['v'] for z in fr.values() if (z['cell'],z['lane'])==(c+1,g)]
                assert len(own)>=2 and len(down)>=2
                rho=len(own)/lengths[c];rho_d=len(down)/lengths[c+1]
                theta=float(np.var(own));theta_d=float(np.var(down))
                distance=.5*(lengths[c]+lengths[c+1])
                pressure=-5*(rho_d*theta_d-rho*theta)/(rho*distance*3600)
                assert math.isfinite(pressure)
                cached[key]=pressure
                moments.append(dict(case=case,t=t,cell=c,lane=g,n=len(own),n_down=len(down),
                    rho=rho,rho_down=rho_d,theta=theta,theta_down=theta_d,distance_km=distance,pressure5=pressure))
            q=dict(r);q['x']=list(r['x'])+[cached[key]]
            assert abs(predict(r,original_model)-r['ordered'])<1e-10
            out.append(q)
        return out
    for case in ('29_none','29_vsl'):records+=extract(case)
    x=np.array([r['x'] for r in records]);y=np.array([r['y'] for r in records])
    sizes=Counter((r['case'],r['t'],r['cell'],r['lane']) for r in records)
    w=np.array([1/sizes[r['case'],r['t'],r['cell'],r['lane']] for r in records])
    mean=np.average(x,axis=0,weights=w);sd=np.maximum(1e-8,np.sqrt(np.average((x-mean)**2,axis=0,weights=w)))
    design=np.column_stack([np.ones(len(x)),(x-mean)/sd])
    penalty=np.eye(18);penalty[0,0]=0
    lhs=design.T@(w[:,None]*design)+penalty;rhs=design.T@(w*y)
    beta=np.linalg.solve(lhs,rhs);unconstrained=beta.copy()
    if beta[-1]<0:
        beta=np.r_[np.linalg.solve(lhs[:-1,:-1],rhs[:-1]),0.]
    gradient=lhs@beta-rhs
    assert max(abs(gradient[:-1]))<1e-7
    assert (beta[-1]>0 and abs(gradient[-1])<1e-7) or (beta[-1]==0 and gradient[-1]>=-1e-7)
    model=dict(features=BASE+EXTRA+['current_variance_pressure5'],mean=mean.tolist(),sd=sd.tolist(),
        beta=beta.tolist(),pressure_coefficient=beta[-1]/sd[-1],unconstrained_pressure_coefficient=unconstrained[-1]/sd[-1],
        kkt_gradient=gradient.tolist(),training_rows=len(records))
    h.save(work/'frozen_model.json',model);frozen=h.sha(work/'frozen_model.json')
    for case in files:
        if not case.startswith('29'):records+=extract(case)
    assert len(records)==len(raw)==79188
    grouped=defaultdict(list)
    for r in records:
        r['pressure']=predict(r,model)
        grouped[r['case'],r['t'],r['cell'],r['lane']].append(r)
    blocks=[]
    for (case,t,cell,lane),rr in grouped.items():
        blocks.append(dict(case=case,t=t,cell=cell,lane=lane,n=len(rr),
            actual=float(np.mean([r['y'] for r in rr])),
            ordered=float(np.mean([r['ordered'] for r in rr])),
            pressure=float(np.mean([r['pressure'] for r in rr]))))
    scores=[];gates=[];contrasts=[]
    for case in files:
        for cell in (None,*CELLS):
            rr=[r for r in blocks if r['case']==case and (cell is None or r['cell']==cell)]
            scores.append(dict(case=case,cell=cell,groups=len(rr),**{m+'_rmse':math.sqrt(float(np.mean([(r[m]-r['actual'])**2 for r in rr]))) for m in ('ordered','pressure')}))
    for a,b in [('43_none','43_vsl'),('67_hold','67_release'),('67_hold','67_hold_vsl90'),('67_release','67_release_vsl90')]:
        by={case:{(r['t'],r['cell'],r['lane']):r for r in blocks if r['case']==case} for case in (a,b)}
        for cell in CELLS:
            keys=set(by[a])&set(by[b]);keys=[k for k in keys if k[1]==cell]
            for start in (2220.1,2370.1,2520.1,2670.1,2820.1,2970.1):
                kk=[k for k in keys if start<=k[0]<start+150]
                if not kk:continue
                contrasts.append(dict(pair=a+'->'+b,cell=cell,start=start,groups=len(kk),
                    **{m:float(np.mean([by[b][k][m]-by[a][k][m] for k in kk])) for m in ('actual','ordered','pressure')}))
    for seed in ('43','67'):
        rr=[r for r in blocks if r['case'].startswith(seed)]
        pooled={m:math.sqrt(float(np.mean([(r[m]-r['actual'])**2 for r in rr]))) for m in ('ordered','pressure')}
        cc=[r for r in contrasts if r['pair'].startswith(seed)]
        response={m:float(np.mean([(r[m]-r['actual'])**2 for r in cc])) for m in ('ordered','pressure')}
        gates.append(dict(seed=seed,pooled_rmse=pooled,response_mse=response,
            improves10=pooled['pressure']<=.9*pooled['ordered'],response_not_worse=response['pressure']<=response['ordered'],
            no_arm_worse10=all(r['pressure_rmse']<=1.1*r['ordered_rmse'] for r in scores if r['cell'] is None and r['case'].startswith(seed))))
    savegz(work/'rows.json.gz',records);savegz(work/'moments.json.gz',moments)
    h.save(work/'blocks.json',blocks);h.save(work/'contrasts.json',contrasts)
    assert all(h.sha(Path(p))==sha for p,sha in pins.items()) and h.sha(work/'frozen_model.json')==frozen
    assert all(h.sha(h.ROOT/p)==sha for p,sha in core.items()) and h.sha(stop['path'])==stop['sha256']
    result=dict(status='COMPLETE_CONDITIONAL_PRESSURE_INFORMATION',rows=len(records),moment_groups=len(moments),
        fits=1,pressure_coefficient=float(model['pressure_coefficient']),scores=scores,gates=gates,
        gate_pass=all(g['improves10'] and g['response_not_worse'] and g['no_arm_worse10'] for g in gates),
        seconds=time.perf_counter()-started,frozen_sha256=frozen,core_preserved=len(core),
        forecasts=0,native=0,FZP=0,adopted=False,goal='ACTIVE_NOT_QUALIFIED')
    h.save(work/'summary.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='scores'}))


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['--recovery206']:recovery206()
    elif sys.argv[1:]==['--variance213']:variance213()
    else:main()
