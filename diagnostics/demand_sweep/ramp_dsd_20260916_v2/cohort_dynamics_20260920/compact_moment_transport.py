"""Test transporting compact vehicle moments with conserved local fluxes.

One diagnostic change: carry mean/second moment/closing/braking/acceleration
with accepted vehicles before learning local residual changes. No capacity fit.
"""
from pathlib import Path
from collections import Counter
import sys,copy,math,hashlib
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import compact_lane_state as m
d=m.d


def transport(old,rate,queue,geo,rho_max):
    new=copy.deepcopy(old)
    send={c:min(old[c]['n'],old[c]['n']*max(0.,old[c]['v'])/(geo[c]['length_km']*3600)) for c in m.CELLS}
    space={c:max(0.,rho_max*geo[c]['length_km']*geo[c]['effective_lanes']-old[c]['n']) for c in m.CELLS}
    out={c:send[c] if c==20 else min(send[c],space[c+1]) for c in m.CELLS}
    accepted=min(queue+rate,space[15]);newqueue=queue+rate-accepted
    for c in m.CELLS:
        entering=accepted if c==15 else out[c-1];remaining=old[c]['n']-out[c]
        n=remaining+entering;new[c]['n']=n
        if not n:
            for f in m.FIELDS:new[c][f]=0.
            continue
        up=old[c-1];self=old[c]
        v=(remaining*self['v']+entering*up['v'])/n
        second=(remaining*(self['v']**2+self['sd']**2)+entering*(up['v']**2+up['sd']**2))/n
        new[c]['v']=v;new[c]['sd']=math.sqrt(max(0.,second-v*v))
        for f in ('closing','braking','acceleration'):new[c][f]=(remaining*self[f]+entering*up[f])/n
        assert -1e-9<=new[c]['closing']<=v+1e-8 and 0<=new[c]['braking']<=1
    residual=sum(new[c]['n'] for c in m.CELLS)+newqueue+out[20]-sum(old[c]['n'] for c in m.CELLS)-queue-rate
    assert abs(residual)<1e-8
    return new,newqueue,out[20],accepted


def fit(states,entry,geo,rho_max,kind):
    x=[];y=[]
    # All three comparators use the same7020training transitions, with a full
    # past30s boundary estimate. No future inflow is used for residual fitting.
    for t in range(930,2100):
        rate=sum(entry[s] for s in range(t-29,t+1))/30
        now=states[t]
        adv=transport(now,rate,0.,geo,rho_max)[0] if kind=='transported' else now
        for c in m.CELLS:
            x.append(m.vector(adv,c,geo,kind!='coarse'))
            if kind=='transported':y.append([states[t+1][c][f]-adv[c][f] for f in m.FIELDS])
            else:y.append(m.targets(now[c],states[t+1][c]))
    x=np.asarray(x);y=np.asarray(y);mean=x.mean(axis=0);scale=x.std(axis=0);assert np.all(scale>1e-9)
    z=np.column_stack((np.ones(len(x)),(x-mean)/scale));coef,res,rank,s=np.linalg.lstsq(z,y,rcond=None)
    assert rank==z.shape[1]
    return dict(kind=kind,rich=kind!='coarse',mean=mean.tolist(),scale=scale.tolist(),coef=coef.tolist(),
                rank=int(rank),condition=float(s[0]/s[-1]),train_rows=len(x),start_times=[930,2099],label_end_s=2100)


def step(old,rate,queue,geo,rho_max,model):
    adv,q,exits,accepted=transport(old,rate,queue,geo,rho_max);new=copy.deepcopy(adv);project=Counter()
    for c in m.CELLS:
        delta=m.predict(adv,c,geo,model)
        for i,f in enumerate(m.FIELDS):new[c][f]=adv[c][f]+delta[i]
        if new[c]['v']<0:project['negative_speed']+=1;new[c]['v']=0.
        if not math.isfinite(new[c]['v']) or new[c]['v']>300:raise ArithmeticError('Unbounded transported speed')
        for f in ('sd','closing','braking'):
            upper=new[c]['v'] if f=='closing' else (1. if f=='braking' else math.inf)
            if new[c][f]<0 or new[c][f]>upper:project[f]+=1
            new[c][f]=max(0.,min(upper,new[c][f]))
    return new,q,exits,accepted,dict(project)


def conditional(states,entry,geo,rho_max,model,lo,hi):
    errors={f:[] for f in m.FIELDS}
    for t in range(lo,hi):
        rate=sum(entry[s] for s in range(t-29,t+1))/30
        if model['kind']=='transported':
            adv=transport(states[t],rate,0.,geo,rho_max)[0]
            for c in m.CELLS:
                delta=m.predict(adv,c,geo,model)
                for i,f in enumerate(m.FIELDS):errors[f].append(adv[c][f]+delta[i]-states[t+1][c][f])
        else:
            for c in m.CELLS:
                delta=m.predict(states[t],c,geo,model);actual=m.targets(states[t][c],states[t+1][c])
                for i,f in enumerate(m.FIELDS):errors[f].append(delta[i]-actual[i])
    return {f:dict(n=len(v),rmse=math.sqrt(sum(x*x for x in v)/len(v))) for f,v in errors.items()}


def main():
    out=d.HERE/'compact_moment_transport_v1';out.mkdir(exist_ok=False)
    bp=d.HERE/'compact_lane_state_v1/states.json';raw=d.e.load(bp)
    banks={a:({int(t):{int(c):r for c,r in row.items()} for t,row in x['states'].items()},
              {int(t):v for t,v in x['entry'].items()}) for a,x in raw.items()}
    source=d.HERE/'compact_lane_state_v1/result.json';old=d.e.load(source);rho_max=old['rho_max']
    gp=d.H/'controller_response_s23_v1/none/geometry.json';geo={r['cell']:r for r in d.e.load(gp)['cells'] if r['road']=='FW_E'}
    nc,entry=banks['none'];models={name:fit(nc,entry,geo,rho_max,name) for name in ('coarse','compact','transported')}
    time_validation={name:conditional(nc,entry,geo,rho_max,model,2100,2400) for name,model in models.items()}
    runs=[]
    for arm,(states,entries) in banks.items():
        for start in (2280,2400,2550,2700):
            initial=states[start];rate=sum(entries[t] for t in range(start-29,start+1))/30
            for name,model in models.items():
                record=dict(arm=arm,start_s=start,model=name)
                try:
                    if name!='transported':trace,projections=m.rollout(initial,rate,geo,model,rho_max,30)
                    else:
                        state=copy.deepcopy(initial);queue=0.;exits=0.;trace=[];projections=Counter()
                        n0=sum(state[c]['n'] for c in m.CELLS)
                        for dt in range(1,31):
                            state,queue,q,accepted,p=step(state,rate,queue,geo,rho_max,model);exits+=q;projections.update(p)
                            residual=sum(state[c]['n'] for c in m.CELLS)+queue+exits-n0-dt*rate
                            assert abs(residual)<1e-7
                            trace.append(dict(step=dt,cells=copy.deepcopy(state),inlet_queue=queue,mass_residual=residual))
                    ev=[];en=[]
                    for row in trace:
                        actual=states[start+row['step']]
                        for c in m.CELLS:ev.append(row['cells'][c]['v']-actual[c]['v']);en.append(row['cells'][c]['n']-actual[c]['n'])
                    record.update(status='completed',speed_rmse=math.sqrt(sum(x*x for x in ev)/len(ev)),n_mae=sum(abs(x) for x in en)/len(en),
                        projections=dict(projections),max_mass_residual=max(abs(r['mass_residual']) for r in trace),
                        final_queue=trace[-1]['inlet_queue'],final_cells=trace[-1]['cells'])
                except (ArithmeticError,AssertionError) as exc:record.update(status='failed',reason=str(exc))
                runs.append(record)
    files=[Path(__file__),Path(m.__file__),bp,source,gp]
    d.e.save(out/'result.json',dict(status='COMPACT_MOMENT_TRANSPORT_LOCAL_GATE_NOT_QUALIFIED',models=models,
        time_validation=time_validation,autonomous_runs=runs,
        pins={str(p.relative_to(d.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        limitations=['Local6-cell30s pilot with frozen past/current boundary, no full lever/cost qualification.',
            'Empirical local residual is refit after transport; no duplicate mean-velocity convection is added.',
            'All comparators share930..2100training; speed bounds and auxiliary projections are reported.',
            'Closing/braking/acceleration are averaged descriptive vehicle attributes; nonlinear ordering creation is not proved by moment conservation.'],
        future_inputs=False,production_changes=0,new_native_runs=0,qualified=False))
    print('VALIDATION',{name:metrics['v'] for name,metrics in time_validation.items()},flush=True)
    print('RUNS',[(r['arm'],r['start_s'],r['model'],r['status'],round(r.get('speed_rmse',-1),3)) for r in runs],flush=True)


if __name__=='__main__':main()
