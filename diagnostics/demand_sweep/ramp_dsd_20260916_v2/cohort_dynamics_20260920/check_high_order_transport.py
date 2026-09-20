"""Check numerical diffusion, compatibility and saved local wave predictions."""
from pathlib import Path
import copy
import hashlib
import json
import math
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import downstream_spatial_rollout as s

K=Path(__file__).resolve().parent
OUT=K/'high_order_transport_v1'


def manufactured():
    bins=[dict(length=.1) for _ in range(30)];initial=[[10. if 4<=i<8 else 0.] for i in range(30)]
    results={}
    for high in (False,True):
        n=copy.deepcopy(initial);v=[[72.] for _ in n];initial_mass=sum(map(sum,n));initial_moment=initial_mass*72
        for step in range(50):
            if high:q,face=s.reconstructed_flux(n,v,bins,1.)
            else:q=[[row[0]*.2] for row in n];face=v
            nextn=[];nextv=[]
            for i,row in enumerate(n):
                entered=q[i-1][0] if i else 0.;speed=face[i-1][0] if i else 72.
                stock=row[0]+entered-q[i][0]
                moment=row[0]*v[i][0]+entered*speed-q[i][0]*face[i][0]
                assert stock>=-1e-9 and moment>=-1e-8
                nextn.append([stock]);nextv.append([moment/stock if stock else 72.])
            # Finite-domain tail is tracked instead of silently removed.
            if step==0:escaped=escaped_moment=0.
            escaped+=q[-1][0];escaped_moment+=q[-1][0]*face[-1][0]
            n,v=nextn,nextv
            assert abs(sum(map(sum,n))+escaped-initial_mass)<1e-8
            assert abs(sum(row[0]*speed[0] for row,speed in zip(n,v))+escaped_moment-initial_moment)<1e-7
        mass=sum(map(sum,n));mean=sum(i*r[0] for i,r in enumerate(n))/mass
        variance=sum(r[0]*(i-mean)**2 for i,r in enumerate(n))/mass
        results[str(high)]=dict(mass=mass,mean_cell=mean,variance_cells=variance,escaped=escaped)
    assert results['True']['variance_cells']<results['False']['variance_cells']
    assert abs(results['True']['mean_cell']-15.5)<.03
    q,face=s.reconstructed_flux([[5.]]*5,[[72.]]*5,bins[:5],1.)
    assert all(abs(r[0]-1)<1e-12 for r in q) and face==[[72.]]*5
    return results


def score(trace,observations,arm,start):
    speed=[];stock=[];ttt=actual=queue=0.
    for row in trace:
        obs=observations[arm]['states'][str(start+row['step'])]
        for c,value in row['cells'].items():
            target=obs[str(c)];speed.append(value['v']-target['v']);stock.append(value['n']-target['n'])
            ttt+=value['n']/3600;actual+=target['n']/3600
        queue+=row['queue']/3600
    return dict(speed_rmse=math.sqrt(sum(x*x for x in speed)/len(speed)),stock_mae=sum(abs(x) for x in stock)/len(stock),
        predicted_ttt=ttt,actual_ttt=actual,boundary_queue_ttt=queue,final_exits=trace[-1]['exits'])


def main():
    tests=manufactured();s.d.e.save(OUT/'manufactured.json',tests)
    gp=s.d.H/'controller_response_s23_v1/none/geometry.json';cp=K/'transport_step1_exchange_off_v2/config.json'
    pp=K/'port_travel_fit_v1/selected_parameters.json';ip=K/'downstream_spatial_rollout_v1/inputs.json'
    op=K/'compact_lane_state_v1/states.json';oraclep=K/'downstream_boundary_probe_v1/boundaries.json'
    e=s.d.e;model=e.load_base_model(e.load(gp),cp);cfg=model._config('FW_E',e.load(pp)['parameters']['by_direction']['FW_E'])
    bank=e.load(ip);observations=e.load(op);oracles=e.load(oraclep)
    runs=[];exact=0
    for arm in ('none','rm_ramp'):
        for start in (2400,2550,2700):
            key=f'{arm}_{start}_lane_100m';initial=copy.deepcopy(bank[key]['inputs'])
            initial['rates']={int(k):v for k,v in initial['rates'].items()}
            for kind in ('history','observed_boundary'):
                boundary=oracles[key+'_observed_boundary']['sequence'] if kind=='observed_boundary' else None
                for high in (False,True):
                    trace,check=s.rollout(initial,cfg,150,momentum_advection=True,boundary_steps=boundary,reconstruct_flux=high)
                    trace=json.loads(json.dumps(trace))
                    if not high:
                        old=(K/'downstream_spatial_horizon_v1'/(key+'.json') if kind=='history' else
                             K/'downstream_boundary_probe_v1'/(key+'_observed_boundary.json'))
                        assert trace==e.load(old),old;exact+=1
                    else:e.save(OUT/(key+'_'+kind+'.json'),trace)
                    row=dict(arm=arm,start=start,boundary=kind,reconstruction=high,checks=check,**score(trace,observations,arm,start))
                    runs.append(row)
                    print(json.dumps({k:v for k,v in row.items() if k!='checks'}),flush=True)
    responses=[]
    for start in (2400,2550,2700):
        for kind in ('history','observed_boundary'):
            for high in (False,True):
                base=next(v for v in runs if (v['arm'],v['start'],v['boundary'],v['reconstruction'])==('none',start,kind,high))
                alt=next(v for v in runs if (v['arm'],v['start'],v['boundary'],v['reconstruction'])==('rm_ramp',start,kind,high))
                responses.append(dict(start=start,boundary=kind,reconstruction=high,
                    predicted_delta_ttt=alt['predicted_ttt']-base['predicted_ttt'],actual_delta_ttt=alt['actual_ttt']-base['actual_ttt']))
    files=[Path(__file__),Path(s.__file__),gp,cp,pp,ip,op,oraclep,OUT/'source_before.py']
    e.save(OUT/'result.json',dict(qualified=False,production_adopted=False,new_native_runs=0,
        default_traces_exact=exact,manufactured=tests,runs=runs,response=responses,
        fitted_parameters=0,source_pins={p.relative_to(e.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        limitations=['Local cells15-20,150seconds; not full450s or gain qualification.',
          'Post-treatment2550/2700 states differ; comparison diagnoses propagation,not matched-state control selection.',
          'History arms use only current/past observations; observed_boundary arms intentionally use future boundary for diagnosis only.',
          'Existing port-free local diagnostic driver only; no canonical core or default change.']))


if __name__=='__main__':main()
