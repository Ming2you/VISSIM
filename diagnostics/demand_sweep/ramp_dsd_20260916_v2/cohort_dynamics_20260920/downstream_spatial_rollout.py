"""Bounded autonomous spatial-resolution test using the consumed METANET law.

No fitting, future boundary, port approximation or controller reward. This is
a local gate before changing the canonical 42-cell topology, not a new adapter.
"""
from pathlib import Path
from collections import Counter, defaultdict
import bisect
import copy
import hashlib
import math
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import downstream_wave_audit as d
import canonical_harness as ch

CELLS=tuple(range(15,21))


def locate(frames,geometry):
    shifts={r['link']:r['offset_m'] for r in geometry['chains']['FW_E']}
    geo={r['cell']:r for r in geometry['cells'] if r['road']=='FW_E'}
    bounds=[geo[c]['end_m'] for c in sorted(geo)]
    result={}
    for t,frame in frames.items():
        result[t]={}
        for vid,r in frame.items():
            x=shifts[r['link']]+r['pos'];c=min(20,bisect.bisect_right(bounds,x))
            if c>=14:
                assert 1<=r['lane']<=3
                result[t][vid]=dict(x=x,cell=c,lane=r['lane'],v=r['v'])
    return result


def initial_and_boundary(frames,start,geo,mode):
    fine=mode=='lane_100m';lanes=1 if mode=='coarse' else 3;width=3./lanes
    bins=[]
    for c in CELLS:
        count=math.ceil(geo[c]['length_km']*10) if fine else 1
        length=geo[c]['length_km']/count
        for j in range(count):bins.append(dict(cell=c,length=length,start=geo[c]['start_m']+j*length*1000))
    ends=[b['start']+b['length']*1000 for b in bins]
    n=[[0.]*lanes for b in bins];mom=copy.deepcopy(n)
    cell_values=defaultdict(list)
    for r in frames[start].values():cell_values[r['cell']].append(r['v'])
    for r in frames[start].values():
        if r['cell']<15:continue
        i=min(len(bins)-1,bisect.bisect_right(ends,r['x']));g=0 if lanes==1 else r['lane']-1
        n[i][g]+=1;mom[i][g]+=r['v']
    # An empty spatial bin has no observed mean. Use its present coarse-cell
    # mean, not future observations or an invented stationary vehicle.
    v=[[mom[i][g]/x if x else sum(cell_values[b['cell']])/len(cell_values[b['cell']])
        for g,x in enumerate(n[i])] for i,b in enumerate(bins)]
    upstream=[[] for g in range(lanes)]
    for r in frames[start].values():
        if r['cell']==14:upstream[0 if lanes==1 else r['lane']-1].append(r['v'])
    assert all(upstream)
    upstream=[sum(vs)/len(vs) for vs in upstream]
    arrivals=[0.]*lanes;exposure=Counter();changes=Counter()
    for t in range(start-29,start+1):
        for vid,r in frames[t-1].items():
            if r['cell']>=15:exposure[r['cell'],r['lane']-1]+=1
        for vid,r in frames[t].items():
            before=frames[t-1].get(vid)
            if before and before['cell']==14 and r['cell']>=15:
                arrivals[0 if lanes==1 else r['lane']-1]+=1/30
            if before and before['cell']>=15 and before['lane']!=r['lane']:
                changes[before['cell'],before['lane']-1,r['lane']-1]+=1
    rates={c:[[changes[c,g,k]/exposure[c,g] if exposure[c,g] else 0.
               for k in range(3)] for g in range(3)] for c in CELLS} if lanes==3 else {}
    return dict(bins=bins,n=n,v=v,width=width,upstream=upstream,arrivals=arrivals,rates=rates)


def reconstructed_flux(n,v,bins,width):
    """Limited downstream-face reconstruction for the existing1s transport.

    First-order boundary faces; minmod interior slopes. Cap donor mass and
    speed moment before receiver allocation, retaining both when blocked.
    This numerical candidate is not a new traffic capacity or desired speed.
    """
    length=[b['length'] for b in bins];count=len(n);groups=len(n[0])
    rho=[[x/(length[i]*width) for x in row] for i,row in enumerate(n)]
    faces=copy.deepcopy(v);outgoing=copy.deepcopy(n)
    for i in range(count):
        for g in range(groups):
            courant=v[i][g]/(3600*length[i])
            if not 0<=courant<=1:raise ValueError('Reconstructed transport requires CFL<=1')
            values=[]
            for field in (rho,v):
                slope=0.
                if 0<i<count-1:
                    left=(field[i][g]-field[i-1][g])/((length[i]+length[i-1])/2)
                    right=(field[i+1][g]-field[i][g])/((length[i]+length[i+1])/2)
                    if left*right>0:slope=math.copysign(min(abs(left),abs(right)),left)
                values.append(max(0.,field[i][g]+.5*length[i]*(1-courant)*slope))
            density,velocity=values;faces[i][g]=velocity
            desired=density*velocity*width/3600
            moment_limit=n[i][g]*v[i][g]/velocity if velocity else n[i][g]
            outgoing[i][g]=min(n[i][g],moment_limit,desired)
    return outgoing,faces


def forward_acceleration(acceleration,stock):
    """Current-bin/next-occupied-bin exposure; no individual target identities."""
    count=len(stock);groups=len(stock[0]);result=[[None]*groups for _ in stock]
    for i in range(count):
        for g in range(groups):
            j=next((j for j in range(i+1,count) if stock[j][g]>1e-9),None)
            if j is not None:
                p=min(1.,1/max(stock[i][g],1e-9))
                result[i][g]=(1-p)*acceleration[i][g]+p*acceleration[j][g]
    return result


def rollout(inputs,cfg,horizon=30,collect_speed_terms=False,momentum_advection=False,boundary_steps=None,reconstruct_flux=False,acceleration_memory=None,response_resolution='transport'):
    if response_resolution not in ('transport','physical_cell'):raise ValueError('Unsupported response resolution')
    if reconstruct_flux and not momentum_advection:
        raise ValueError('Face transport requires conserved speed-moment advection')
    s=copy.deepcopy(inputs);n=s['n'];v=s['v'];bins=s['bins'];width=s['width']
    count=len(n);groups=len(n[0]);queue=[0.]*groups;exits=0.;records=[];mass0=sum(map(sum,n))
    cell_bins={c:[i for i,b in enumerate(bins) if b['cell']==c] for c in CELLS}
    cell_lengths={c:sum(bins[i]['length'] for i in ids) for c,ids in cell_bins.items()}
    acceleration=None
    if acceleration_memory is not None:
        if not momentum_advection or reconstruct_flux:raise ValueError('Acceleration pilot requires unchanged first-order momentum transport')
        ws,wf=acceleration_memory['self_weight'],acceleration_memory['forward_weight']
        if not (ws>=0 and wf>=0 and ws+wf<=1+1e-12):raise ValueError('Invalid acceleration convex weights')
        acceleration=copy.deepcopy(acceleration_memory['initial'])
        if len(acceleration)!=count or any(len(r)!=groups or any(not math.isfinite(x) for x in r) for r in acceleration):
            raise ValueError('Missing or invalid initial acceleration observations')
    mn=ch.accounting._mn;net=cfg.network;control=ch.ControlAction.uncontrolled(cfg)
    floor_hits=0;max_speed=0.;max_mass=0.;terms=[];requested=0.
    if boundary_steps is not None:
        if len(boundary_steps)!=horizon:raise ValueError('Incomplete diagnostic boundary sequence')
        for row in boundary_steps:
            if set(row)!={'arrivals','upstream','entry_speed'} or any(
                len(row[k])!=groups or any(not math.isfinite(x) or x<0 for x in row[k]) for k in row):
                raise ValueError('Invalid explicit diagnostic boundary')
    for i,b in enumerate(bins):
        if max(n[i])>net.rho_max*b['length']*width+1e-8:
            raise ValueError(f'Observed initial subcell exceeds configured jam storage: {i},{n[i]}')
    for step in range(1,horizon+1):
        boundary=boundary_steps[step-1] if boundary_steps is not None else None
        arrivals=boundary['arrivals'] if boundary else s['arrivals']
        boundary_upstream=boundary['upstream'] if boundary else s['upstream']
        entry_speed=boundary['entry_speed'] if boundary else s['upstream']
        requested=(requested+sum(arrivals)) if boundary else step*sum(s['arrivals'])
        old=copy.deepcopy(n);oldv=copy.deepcopy(v)
        if response_resolution=='physical_cell':
            response_rho={c:[sum(old[i][g] for i in ids)/(cell_lengths[c]*width) for g in range(groups)]
                          for c,ids in cell_bins.items()}
        if acceleration is not None:
            old_acceleration=copy.deepcopy(acceleration)
            forward=forward_acceleration(old_acceleration,old)
        free=[[max(0.,net.rho_max*b['length']*width-x) for x in row] for b,row in zip(bins,old)]
        outgoing=[[min(x,x*max(0.,oldv[i][g])/(3600*bins[i]['length'])) for g,x in enumerate(row)] for i,row in enumerate(old)]
        face_v=oldv
        if reconstruct_flux:outgoing,face_v=reconstructed_flux(old,oldv,bins,width)
        for i in range(count-1):
            for g in range(groups):outgoing[i][g]=min(outgoing[i][g],free[i+1][g])
        if not getattr(net,'terminal_zero_gradient',False):
            cap=net.freeway_capacity_veh_h*3/net.freeway_lanes/3600
            factor=min(1.,cap/sum(outgoing[-1])) if sum(outgoing[-1]) else 1.
            outgoing[-1]=[x*factor for x in outgoing[-1]]
        entry=[min(queue[g]+arrivals[g],free[0][g]) for g in range(groups)]
        queue=[queue[g]+arrivals[g]-entry[g] for g in range(groups)]
        carriers=copy.deepcopy(oldv)
        for i in range(count):
            incoming=entry if i==0 else outgoing[i-1]
            n[i]=[old[i][g]+incoming[g]-outgoing[i][g] for g in range(groups)]
            free[i]=[max(0.,free[i][g]-incoming[g]) for g in range(groups)]
            if momentum_advection:
                upstream=entry_speed if i==0 else oldv[i-1]
                carriers[i]=[((old[i][g]-outgoing[i][g])*oldv[i][g]+incoming[g]*upstream[g])/x
                    if x else oldv[i][g] for g,x in enumerate(n[i])]
                if reconstruct_flux:
                    upstream=entry_speed if i==0 else face_v[i-1]
                    carriers[i]=[(old[i][g]*oldv[i][g]-outgoing[i][g]*face_v[i][g]+incoming[g]*upstream[g])/x
                        if x else oldv[i][g] for g,x in enumerate(n[i])]
        # Same past30s coarse-cell exchange hazards in both lane resolutions.
        # No simultaneous swap uses space just freed by another exchange.
        if groups==3:
            for i,b in enumerate(bins):
                requests=[]
                for g in range(groups):
                    rates=s['rates'][b['cell']][g];total=sum(rates)
                    amount=min(old[i][g],n[i][g])*(1-math.exp(-total))
                    requests.append([amount*r/total if total else 0. for r in rates])
                for k in range(groups):
                    want=sum(row[k] for row in requests);factor=min(1.,free[i][k]/want) if want else 1.
                    for row in requests:row[k]*=factor
                velocity=list(carriers[i])
                moment=[x*y for x,y in zip(n[i],velocity)]
                for g,row in enumerate(requests):
                    for k,x in enumerate(row):
                        n[i][g]-=x;n[i][k]+=x;moment[g]-=x*velocity[g];moment[k]+=x*velocity[g]
                carriers[i]=[moment[g]/x if x else oldv[i][g] for g,x in enumerate(n[i])]
        for i,b in enumerate(bins):
            for g in range(groups):
                rho=old[i][g]/(b['length']*width)
                down=old[i+1][g]/(bins[i+1]['length']*width) if i+1<count else (rho if getattr(net,'terminal_zero_gradient',False) else min(rho,net.rho_crit))
                response_length=b['length']
                if response_resolution=='physical_cell':
                    c=b['cell'];response_length=cell_lengths[c];rho=response_rho[c][g]
                    down=(response_rho[c+1][g] if c<CELLS[-1] else
                          rho if getattr(net,'terminal_zero_gradient',False) else min(rho,net.rho_crit))
                up=carriers[i][g] if momentum_advection else (oldv[i-1][g] if i else boundary_upstream[g])
                limit=mn.segment_vsl(control,'FW_E',b['cell'],cfg,physical_length_km=response_length,segment_end=True)
                eq=mn.effective_desired_speed_kmh(rho,net.v_free,net.rho_crit,limit,net.alpha_vsl,False,
                    net.metanet_a_m,getattr(net,'vsl_fd_two_branch',False),net.rho_max,float(getattr(net,'rho_crit_two_branch',0.) or 0.))
                value=mn.metanet_speed_update_kmh(carriers[i][g],up,rho,down,eq,1/3600,response_length,
                    net.metanet_tau_h,mn.select_anticipation_nu(rho,net,limit),net.metanet_kappa_veh_km_lane,net.v_min)
                if collect_speed_terms:
                    assert not (getattr(net,'freeway_state_response',{}) or {}).get('FW_E')
                    p=net.freeway_segment_params['FW_E'][b['cell']]
                    tau=p.get('metanet_tau_h',net.metanet_tau_h)*3600
                    nu=p.get('metanet_nu_km2_h',net.metanet_nu_km2_h)
                    kappa=p.get('metanet_kappa_veh_km_lane',net.metanet_kappa_veh_km_lane)
                    carrier=carriers[i][g]
                    relax=(eq-carrier)/tau
                    convection=carrier*(up-carrier)/(3600*response_length)
                    pressure=-nu/tau/response_length*(down-rho)/(rho+kappa)
                    assert abs(value-max(net.v_min,carrier+relax+convection+pressure))<1e-7
                    terms.append(dict(step=step,i=i,g=g,carrier=carrier,relax=relax,
                        convection=convection,pressure=pressure,tau=tau,actual_function_value=value))
                if acceleration is not None:
                    base=value-carriers[i][g]
                    if ws or wf:
                        ahead=forward[i][g]
                        ahead_weight=wf if ahead is not None else 0.
                        reaction=(1-ws-ahead_weight)*base+ws*old_acceleration[i][g]+ahead_weight*(ahead or 0.)
                        value=max(net.v_min,carriers[i][g]+reaction)
                    acceleration[i][g]=value-carriers[i][g]
                if not math.isfinite(value) or value>300:raise ArithmeticError('Unbounded speed')
                v[i][g]=max(net.v_min,value);floor_hits+=value<=net.v_min;max_speed=max(max_speed,value)
                assert -1e-8<=n[i][g]<=net.rho_max*b['length']*width+1e-8
        exits+=sum(outgoing[-1]);residual=sum(map(sum,n))+sum(queue)+exits-mass0-requested
        assert abs(residual)<1e-7;max_mass=max(max_mass,abs(residual))
        aggregate={}
        for c in CELLS:
            ids=[i for i,b in enumerate(bins) if b['cell']==c];stock=sum(sum(n[i]) for i in ids)
            speed=sum(sum(x*y for x,y in zip(n[i],v[i])) for i in ids)/stock if stock else 0.
            aggregate[c]=dict(n=stock,v=speed)
        records.append(dict(step=step,cells=aggregate,queue=sum(queue),exits=exits,residual=residual))
    checks=dict(max_mass_residual=max_mass,speed_floor_hits=floor_hits,max_speed=max_speed)
    if acceleration is not None:
        checks['acceleration_memory']=dict(self_weight=ws,forward_weight=wf,
            equilibrium_weight=1-ws-wf,final_acceleration=acceleration)
    if collect_speed_terms:checks['speed_terms']=terms
    return records,checks


def calibrate_local(momentum=False):
    """Two physically nonnegative equation multipliers; no treatment-cost fit."""
    import numpy as np
    out=d.HERE/('downstream_spatial_moment_calibration_v1' if momentum else 'downstream_spatial_calibration_v3');out.mkdir(exist_ok=False)
    gp=d.H/'controller_response_s23_v1/none/geometry.json';geometry=d.e.load(gp)
    geo={r['cell']:r for r in geometry['cells'] if r['road']=='FW_E'}
    config=d.HERE/'transport_step1_exchange_off_v2/config.json';pp=d.HERE/'port_travel_fit_v1/selected_parameters.json'
    model=d.e.load_base_model(geometry,config);cfg=model._config('FW_E',d.e.load(pp)['parameters']['by_direction']['FW_E'])
    path=d.HERE/'route_state_native_v1/none_s23/run_retry1/vissim_eval/baseline_001.fzp'
    raw,receipt=d.extract(path,True);frames=locate(raw,geometry);del raw
    saved=d.e.load(d.HERE/'downstream_spatial_rollout_v1/inputs.json')
    results={};runs=[];repeated=0
    for mode in ('coarse','lane_100m'):
        bank=[initial_and_boundary(frames,t,geo,mode) for t in range(2280,2401)]
        samples=[]
        for index,t in enumerate(range(2280,2400)):
            _,check=rollout(bank[index],cfg,1,True,momentum_advection=momentum)
            for term in check['speed_terms']:
                i,g=term['i'],term['g'];weight=min(bank[index]['n'][i][g],bank[index+1]['n'][i][g])
                if not weight:continue
                samples.append(dict(time_s=t,weight=weight,
                    target=bank[index+1]['v'][i][g]-term['carrier']-term['convection'],**term))
        a=np.array([[r['relax'],r['pressure']] for r in samples]);y=np.array([r['target'] for r in samples])
        w=np.sqrt([r['weight'] for r in samples]);upper=min(r['tau'] for r in samples)
        aw=a*w[:,None];yw=y*w
        # Exact active-set solution of a2-variable convex least-squares box:
        # interior, alpha=0, alpha=upper, or beta=0. No parameter grid search.
        unconstrained=np.linalg.lstsq(aw,yw,rcond=None)[0]
        candidates=[]
        if 0<=unconstrained[0]<=upper and unconstrained[1]>=0:candidates.append(unconstrained)
        for alpha_bound in (0.,upper):
            beta_bound=max(0.,float(aw[:,1]@(yw-aw[:,0]*alpha_bound))/float(aw[:,1]@aw[:,1]))
            candidates.append(np.array([alpha_bound,beta_bound]))
        alpha_bound=min(upper,max(0.,float(aw[:,0]@yw)/float(aw[:,0]@aw[:,0])))
        candidates.append(np.array([alpha_bound,0.]))
        fitted=min(candidates,key=lambda x:float(np.sum((aw@x-yw)**2)))
        alpha,beta=map(float,fitted)
        def rms(values):return math.sqrt(sum(r['weight']*v*v for r,v in zip(samples,values))/sum(r['weight'] for r in samples))
        gradient=aw.T@(aw@fitted-yw)
        tolerance=1e-7*(1+float(np.linalg.norm(aw.T@yw)))
        assert (abs(gradient[0])<=tolerance if 1e-8<alpha<upper-1e-8 else
                gradient[0]>=-tolerance if alpha<=1e-8 else gradient[0]<=tolerance)
        assert abs(gradient[1])<=tolerance if beta>1e-8 else gradient[1]>=-tolerance
        d.e.save(out/(mode+'_training.json'),samples)
        if alpha<=1e-8:
            results[mode]=dict(status='REJECTED_DEGENERATE_RELAXATION',training_start=2280,label_end=2400,
                samples=len(samples),alpha=alpha,beta=beta,unconstrained=unconstrained.tolist(),
                gradient=gradient.tolist(),kkt_tolerance=tolerance,
                weighted_equation_rmse_before=rms(a@np.ones(2)-y),weighted_equation_rmse_after=rms(a@fitted-y),
                decision='No finite tau/nu mapping; no epsilon replacement or production adoption.')
            print('FIT_REJECTED',mode,alpha,beta,flush=True)
            continue
        params=copy.deepcopy(cfg)
        for c in CELLS:
            p=params.network.freeway_segment_params['FW_E'][c]
            p['metanet_tau_h']/=alpha;p['metanet_nu_km2_h']*=beta/alpha
        results[mode]=dict(training_start=2280,label_end=2400,samples=len(samples),alpha=alpha,beta=beta,
            weighted_equation_rmse_before=rms(a@np.ones(2)-y),weighted_equation_rmse_after=rms(a@fitted-y),
            gradient=gradient.tolist(),kkt_tolerance=tolerance,unconstrained=unconstrained.tolist(),
            tau_seconds=[params.network.freeway_segment_params['FW_E'][c]['metanet_tau_h']*3600 for c in CELLS],
            nu=[params.network.freeway_segment_params['FW_E'][c]['metanet_nu_km2_h'] for c in CELLS],
            fit_method='Nonnegative weighted least squares; relaxation Euler weight <=1; two scalars only.')
        for arm in ('none','rm_ramp'):
            for start in (2280,2400,2550,2700):
                key=f'{arm}_{start}_{mode}';data=saved[key];inputs=data['inputs']
                inputs['rates']={int(k):v for k,v in inputs['rates'].items()}
                reference,checks=rollout(inputs,cfg)
                # Existing saved JSON has string dictionary keys after loading.
                import json
                assert json.loads(json.dumps(reference))==d.e.load(d.HERE/'downstream_spatial_rollout_v1'/(key+'.json'))
                repeated+=1
                pred,checks=rollout(inputs,params,collect_speed_terms=True,momentum_advection=momentum)
                checks.pop('speed_terms')
                se=[];ne=[]
                for r in pred:
                    for c,p in r['cells'].items():
                        actual=data['observed'][str(start+r['step'])][str(c)]
                        se.append(p['v']-actual['v']);ne.append(p['n']-actual['n'])
                row=dict(arm=arm,start=start,mode=mode,speed_rmse=math.sqrt(sum(x*x for x in se)/len(se)),
                    speed_bias=sum(se)/len(se),stock_mae=sum(abs(x) for x in ne)/len(ne),checks=checks)
                runs.append(row);d.e.save(out/(key+'.json'),pred)
                print('FIT',arm,start,mode,row['speed_rmse'],flush=True)
    files=[Path(__file__),gp,config,pp,d.HERE/'downstream_spatial_rollout_v1/inputs.json']
    d.e.save(out/'result.json',dict(qualified=False,coefficients=results,runs=runs,reference_traces_exact=repeated,
        source_receipt=receipt,source_pins={p.relative_to(d.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        new_native_runs=0,core_changes=False,future_inputs_to_model=False,momentum_advection=momentum,
        limitations=['Only120s NC precontrol fit;2280 rollout overlaps training and is not validation.',
            '2400/2550/2700 are already inspected development states, not fresh holdout.',
            'Same local30s domain/boundary as the uncalibrated gate; no450s lever-gain qualification.']))


def main():
    out=d.HERE/'downstream_spatial_rollout_v1'
    assert out.is_dir() and not (out/'result.json').exists()
    gp=d.H/'controller_response_s23_v1/none/geometry.json';geometry=d.e.load(gp)
    geo={r['cell']:r for r in geometry['cells'] if r['road']=='FW_E'}
    config=d.HERE/'transport_step1_exchange_off_v2/config.json';pp=d.HERE/'port_travel_fit_v1/selected_parameters.json'
    model=d.e.load_base_model(geometry,config);cfg=model._config('FW_E',d.e.load(pp)['parameters']['by_direction']['FW_E'])
    outputs=[];receipts={};saved_inputs={}
    for arm in ('none','rm_ramp'):
        path=d.HERE/'route_state_native_v1'/('none_s23/run_retry1' if arm=='none' else 'rm_ramp_s23/run')/'vissim_eval/baseline_001.fzp'
        raw,receipts[arm]=d.extract(path,True);frames=locate(raw,geometry);del raw
        for start in (2280,2400,2550,2700):
            observed={}
            for t in range(start+1,start+31):
                observed[t]={}
                for c in CELLS:
                    vs=[r['v'] for r in frames[t].values() if r['cell']==c]
                    assert vs;observed[t][c]=dict(n=len(vs),v=sum(vs)/len(vs))
            for mode in ('coarse','lane','lane_100m'):
                inputs=initial_and_boundary(frames,start,geo,mode)
                key=f'{arm}_{start}_{mode}';saved_inputs[key]=dict(inputs=inputs,observed=observed)
                row=dict(arm=arm,start=start,mode=mode,bins=len(inputs['bins']),groups=len(inputs['n'][0]))
                try:
                    trace,checks=rollout(inputs,cfg);se=[];ne=[]
                    for r in trace:
                        for c,values in r['cells'].items():
                            actual=observed[start+r['step']][c];se.append(values['v']-actual['v']);ne.append(values['n']-actual['n'])
                    row.update(status='completed',speed_rmse=math.sqrt(sum(x*x for x in se)/len(se)),speed_bias=sum(se)/len(se),
                        stock_mae=sum(abs(x) for x in ne)/len(ne),checks=checks,final=trace[-1])
                    d.e.save(out/(key+'.json'),trace)
                except (ArithmeticError,ValueError,AssertionError) as exc:
                    row.update(status='failed',reason=str(exc))
                outputs.append(row);print(arm,start,mode,row['status'],row.get('speed_rmse'),flush=True)
    d.e.save(out/'inputs.json',saved_inputs)
    files=[Path(__file__),Path(d.__file__),gp,config,pp,d.e.CAL/'canonical_harness.py',d.ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py']
    d.e.save(out/'result.json',dict(qualified=False,runs=outputs,source_receipts=receipts,
        source_pins={p.relative_to(d.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        no_fitting=True,new_native_runs=0,core_changes=False,future_inputs_to_model=False,
        scope='Port-free cells15..20,30s autonomous gate; same canonical speed equation/parameters; not450s gains.',
        boundaries='Current cell14 lane speeds and preceding30s lane entries held; unmet entries retained in queue.',
        limitations=['Lateral hazards fixed from preceding30s; no autonomous gap/order prediction.',
            'Empty fine bins use current coarse-cell mean; native terminal overshoot stays in last bin.',
            'No VSL/RM actuator within this6-cell region, so observed post-treatment states are local gates, not causal lever-gain forecasts.',
            'Coarse comparator is the same local finite-volume construction, not a full canonical42-cell rollout.']))


if __name__=='__main__':
    if sys.argv[1:]==['--calibrate-local']:calibrate_local()
    elif sys.argv[1:]==['--calibrate-momentum']:calibrate_local(True)
    elif not sys.argv[1:]:main()
    else:raise SystemExit('Supported options: --calibrate-local, --calibrate-momentum')
