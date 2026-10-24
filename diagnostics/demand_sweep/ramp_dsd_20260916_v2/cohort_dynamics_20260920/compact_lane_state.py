"""Compact current-state identification and autonomous local transport gate.

This6-cell pilot is NOT a new controller/adapter or a full gain model.
All future inflow is a frozen past30s estimate. No future observed resets.
"""
from pathlib import Path
from collections import defaultdict,Counter
import sys,bisect,math,hashlib,copy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import current_gap_response as g
d=g.d
FIELDS=('v','sd','closing','braking','acceleration')
CELLS=tuple(range(15,21))


def aggregate(frames,geometry):
    shifts={x['link']:x['offset_m'] for x in geometry['chains']['FW_E']}
    geo={x['cell']:x for x in geometry['cells'] if x['road']=='FW_E'}
    bounds=[geo[c]['end_m'] for c in sorted(geo)]
    states={};entry={};checks=0;previous={};last_c={}
    for t in sorted(frames):
        frame=frames[t];groups=defaultdict(list);lanes=defaultdict(list);address={}
        for vid,row in frame.items():
            x=shifts[row['link']]+row['pos'];c=min(20,bisect.bisect_right(bounds,x))
            address[vid]=c;groups[c].append(vid);lanes[row['lane']].append((x,vid))
        ahead={}
        for queue in lanes.values():
            queue.sort()
            for (_,vid),(_,lead) in zip(queue,queue[1:]):ahead[vid]=lead
        states[t]={}
        for c in range(14,21):
            ids=groups[c];n=len(ids);assert n>0,(t,c)
            avg=sum(frame[i]['v'] for i in ids)/n
            accelerations=[frame[i]['v']-previous[i]['v'] for i in ids if i in previous]
            # Closing is a measurable scalar proxy, not the native target
            # interaction. Missing front vehicles at the outlet contribute0.
            closing=sum(max(0.,frame[i]['v']-frame[ahead[i]]['v']) for i in ids if i in ahead)/n
            states[t][c]=dict(n=float(n),v=avg,sd=math.sqrt(sum((frame[i]['v']-avg)**2 for i in ids)/n),
                closing=closing,braking=sum(a<-1. for a in accelerations)/n,
                acceleration=sum(accelerations)/n,history_coverage=len(accelerations)/n,
                leader_coverage=sum(i in ahead for i in ids)/n)
            assert 0<=closing<=avg+1e-9
        if previous:
            incoming=sum(last_c.get(i,99)<15 and c>=15 for i,c in address.items())
            entering_unknown=[i for i,c in address.items() if c>=15 and i not in last_c]
            assert not entering_unknown,(t,entering_unknown)
            exiting=[]
            for i,c in last_c.items():
                if c<15 or i in address:continue
                # Distinguish valid terminal disappearance from internal loss.
                row=previous[i];x=shifts[row['link']]+row['pos']
                assert c==20 and x>=bounds[-1]-row['v']/3.6-11.5,(t,i,c,x)
                exiting.append(i)
            entry[t]=float(incoming)
            old_n=sum(states[t-1][c]['n'] for c in CELLS);new_n=sum(states[t][c]['n'] for c in CELLS)
            assert new_n-old_n==incoming-len(exiting),(t,old_n,new_n,incoming,len(exiting))
            checks+=1
        previous=frame;last_c=address
    return states,entry,checks


def vector(state,c,geo,rich):
    row=state[c];up=state[c-1];down=state[c+1] if c<20 else row
    rho=lambda i,r:r['n']/(geo[i]['length_km']*geo[i]['effective_lanes'])
    x=[row['v'],rho(c,row),up['v']-row['v'],rho(min(c+1,20),down)-rho(c,row)]
    if rich:x.extend(row[f] for f in FIELDS[1:])
    return x


def targets(now,later):
    return [later['v']-now['v'],later['sd']-now['sd'],later['closing']-now['closing'],
            later['braking']-now['braking'],later['acceleration']]


def fit(states,geo,rich):
    x=[];y=[]
    for t in range(900,2100):
        for c in CELLS:x.append(vector(states[t],c,geo,rich));y.append(targets(states[t][c],states[t+1][c]))
    x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=float)
    mean=x.mean(axis=0);scale=x.std(axis=0);assert np.all(scale>1e-9)
    z=np.column_stack((np.ones(len(x)),(x-mean)/scale))
    coef,residual,rank,singular=np.linalg.lstsq(z,y,rcond=None)
    assert rank==z.shape[1]
    return dict(rich=rich,mean=mean.tolist(),scale=scale.tolist(),coef=coef.tolist(),
                rank=int(rank),condition=float(singular[0]/singular[-1]),train_rows=len(x),
                start_times=[900,2099],label_end_s=2100)


def predict(state,c,geo,model):
    x=vector(state,c,geo,model['rich'])
    z=np.array([1.]+[(v-m)/s for v,m,s in zip(x,model['mean'],model['scale'])])
    return (z@np.asarray(model['coef'])).tolist()


def conditional(states,geo,model,lo,hi):
    errors=defaultdict(list)
    for t in range(lo,hi):
        for c in CELLS:
            estimate=predict(states[t],c,geo,model);actual=targets(states[t][c],states[t+1][c])
            for i,f in enumerate(FIELDS):errors[f].append(estimate[i]-actual[i])
    return {f:dict(n=len(xs),rmse=math.sqrt(sum(x*x for x in xs)/len(xs)),bias=sum(xs)/len(xs)) for f,xs in errors.items()}


def rollout(initial,source_rate,geo,model,rho_max,horizon=30):
    """Whole downstream cells, conserved mass and point queue at the inlet.

    Compact empirical increments are a tested hypothesis, not a physical
    closure assumed valid. Projection counts and autonomous failures are kept.
    Upstream v/rho and inflow rate are fixed from information at the cutoff.
    """
    state=copy.deepcopy(initial);queue=0.;exits=0.;rows=[];projections=Counter()
    n0=sum(state[c]['n'] for c in CELLS)
    for step in range(1,horizon+1):
        old=copy.deepcopy(state)
        sending={c:min(old[c]['n'],old[c]['n']*max(0.,old[c]['v'])/(geo[c]['length_km']*3600)) for c in CELLS}
        space={c:max(0.,rho_max*geo[c]['length_km']*geo[c]['effective_lanes']-old[c]['n']) for c in CELLS}
        out={c:(sending[c] if c==20 else min(sending[c],space[c+1])) for c in CELLS}
        incoming=min(queue+source_rate,space[15]);queue+=source_rate-incoming
        for c in CELLS:
            values=predict(old,c,geo,model)
            state[c]['n']=old[c]['n']+(incoming if c==15 else out[c-1])-out[c]
            v=old[c]['v']+values[0]
            if v<0:projections['negative_speed']+=1;v=0.
            if not math.isfinite(v) or v>300:raise ArithmeticError(f'Unphysical/unbounded speed at step{step} cell{c}: {v}')
            state[c]['v']=v
            for i,f in enumerate(('sd','closing','braking'),1):
                value=old[c][f]+values[i]
                upper=v if f=='closing' else (1. if f=='braking' else math.inf)
                if value<0 or value>upper:projections[f]+=1
                state[c][f]=min(upper,max(0.,value))
            state[c]['acceleration']=values[4]
            assert -1e-8<=state[c]['n']<=rho_max*geo[c]['length_km']*geo[c]['effective_lanes']+1e-8
        exits+=out[20]
        mass=sum(state[c]['n'] for c in CELLS)+queue+exits-n0-step*source_rate
        assert abs(mass)<1e-7 and queue>=-1e-8
        rows.append(dict(step=step,cells=copy.deepcopy(state),inlet_queue=queue,cumulative_terminal=exits,mass_residual=mass))
    return rows,dict(projections)


def main():
    out=d.HERE/'compact_lane_state_v1';out.mkdir(exist_ok=False)
    gp=d.H/'controller_response_s23_v1/none/geometry.json';geometry=d.e.load(gp)
    geo={x['cell']:x for x in geometry['cells'] if x['road']=='FW_E'}
    config=d.HERE/'transport_step1_exchange_off_v2/config.json';params_path=d.HERE/'port_travel_fit_v1/selected_parameters.json'
    canonical=d.e.load_base_model(geometry,config)
    cfg=canonical._config('FW_E',d.e.load(params_path)['parameters']['by_direction']['FW_E'])
    rho_max=cfg.network.rho_max
    banks={};receipts={};conservation={}
    for arm in ('none','rm_ramp','vsl','both'):
        path=(d.H/'rules_4500_s23_v1/run_none/vissim_eval/baseline_001.fzp' if arm=='none'
              else d.H/'response_late_s23_v1'/f'run_{arm}/vissim_eval/baseline_001.fzp')
        frames,receipts[arm]=g.read(path,False,899 if arm=='none' else 2249)
        states,entry,conservation[arm]=aggregate(frames,geometry);banks[arm]=(states,entry);del frames
        print('EXTRACTED',arm,len(states),flush=True)
    nc=banks['none'][0]
    models={'coarse':fit(nc,geo,False),'compact':fit(nc,geo,True)}
    scores={}
    for arm,(states,entry) in banks.items():
        scores[arm]={name:conditional(states,geo,model,2400,2850) for name,model in models.items()}
    time_validation={name:conditional(nc,geo,m,2100,2400) for name,m in models.items()}
    runs=[]
    for arm,(states,entry) in banks.items():
        for start in (2280,2400,2550,2700):
            past=[entry[t] for t in range(start-29,start+1)];assert len(past)==30
            rate=sum(past)/30
            initial=states[start]
            for name,model in models.items():
                row=dict(arm=arm,start_s=start,horizon_s=30,model=name,inlet_rate_veh_s=rate,
                         boundary_definition='past30s flow mean and current upstream state held fixed')
                try:
                    trace,projections=rollout(initial,rate,geo,model,rho_max,30)
                    ev=[];en=[]
                    for r in trace:
                        actual=states[start+r['step']]
                        for c in CELLS:ev.append(r['cells'][c]['v']-actual[c]['v']);en.append(r['cells'][c]['n']-actual[c]['n'])
                    row.update(status='completed',speed_rmse=math.sqrt(sum(v*v for v in ev)/len(ev)),
                        n_mae=sum(abs(v) for v in en)/len(en),projections=projections,
                        final_queue=trace[-1]['inlet_queue'],max_mass_residual=max(abs(r['mass_residual']) for r in trace),
                        final_cells=trace[-1]['cells'])
                except (ArithmeticError,AssertionError) as exc:row.update(status='failed',reason=str(exc))
                runs.append(row)
    d.e.save(out/'states.json',dict({a:dict(states=s,entry=e) for a,(s,e) in banks.items()}))
    files=[Path(__file__),Path(g.__file__),gp,config,params_path]
    d.e.save(out/'result.json',dict(status='COMPACT_STATE_CONDITIONAL_AND_LOCAL_AUTONOMOUS_GATE_NOT_QUALIFIED',
        models=models,time_validation=time_validation,controlled_conditional=scores,autonomous_runs=runs,
        native_stock_ledger_checks=conservation,rho_max=rho_max,source_receipts=receipts,
        pins={str(p.relative_to(d.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        limitations=['6downstream cells only, empirical increments plus conserved Nv/L transport. Not a new canonical adapter.',
            'Coarse comparator is NC-trained regression, not the complete canonical METANET.',
            'Compact moments have fitted state evolution, with projections explicitly counted; not physical qualification.',
            'Frozen historical boundary omits future upstream control response. This pilot cannot qualify lever gain or component costs.',
            'Averaged closing speed uses geometric same-lane ordering, not native interaction targets.',
            'No VSL/RM/TTT reward, no fitted capacity increase, no future observed state/boundary in the30s rollout.'],
        future_inputs=False,new_native_runs=0,production_changes=0,qualified=False))
    print('VALIDATION',time_validation,flush=True)
    print('ROLLOUTS',[(r['arm'],r['start_s'],r['model'],r['status'],round(r.get('speed_rmse',-1),3)) for r in runs],flush=True)


if __name__=='__main__':main()
