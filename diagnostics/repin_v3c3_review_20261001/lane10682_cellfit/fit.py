"""One bounded local fit on the conserved lane dynamics; never a gain reward."""
import copy
import gzip
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import CanonicalFreewayModel

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS={}
def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def write(p,x):
    assert not p.exists(),p
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def pin(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest())

def main():
    assert not (HERE/'fit.json').exists()
    manifest=read(HERE.parent/'retained10638/candidate_manifest.json')
    for key in ('geometry','reference_config','parameters'):
        p=ROOT/manifest['sources'][key]['path'];read(p)
        assert PINS[str(p)]==manifest['sources'][key]['sha256']
    geometry=read(ROOT/manifest['sources']['geometry']['path'])
    reference=read(ROOT/manifest['sources']['reference_config']['path'])
    parameters=read(ROOT/manifest['sources']['parameters']['path'])['parameters']
    component=CanonicalFreewayModel(geometry,ROOT/manifest['sources']['reference_config']['path'])
    cfg=component._config('FW_E',parameters['by_direction']['FW_E']);net=cfg.network
    cell=11;p=net.freeway_segment_params['FW_E'][cell]
    response=net.freeway_state_response['FW_E']['cell_overrides']['11']
    tau=response['relaxation']['acceleration_sec']
    assert tau==response['relaxation']['deceleration_sec']
    assert all(r['to_cell']!=cell for r in component.ramps.values() if r['road']=='FW_E')
    initial=np.array([p['rho_crit'],response['anticipation']['downstream_ge_local'],response['anticipation']['downstream_lt_local']])
    spec=read(I/'baseline_reproduction_20260929/cellwise_calibration/parameter_spec.json')
    bounds=next(x for x in spec['variables'] if x['cell']==cell and x['parameter']=='rho_crit')
    lower=[bounds['lower'],initial[1]*.5,initial[2]*.5]
    upper=[bounds['upper'],initial[1]*2.,initial[2]*2.]
    write(HERE/'protocol.json',dict(fit_seed=29,fit_policy='none',fit_window=[2220.1,2970.1],
        physical_cell=11,parameters=['rho_crit','nu_downstream_ge_local','nu_downstream_lt_local'],
        initial=initial.tolist(),lower=list(map(float,lower)),upper=list(map(float,upper)),
        max_solver_nfev=20,max_residual_calls=100,autonomous_candidates=1,max_autonomous_forecasts=6,
        structure='REVIEW50 destination-conditioned conserved lanes9-12',
        fixed=['all other cells','FD shape/free speed','relaxation time','merge and receiving','urban/off drainage','objective','commands'],
        limitations=['Conditional Eulerian lane mean derivatives include cohort replacement and lane changes.',
            'Physical lane density in the fitting observations; native effective-width/spillback history not inferred.',
            'No future observations in autonomous validation; no gain fitting.']))

    def dataset(seed):
        cache=read(I/f'baseline_reproduction_20260929/cellwise_calibration/freeway_first/cohort_early/s{seed}_none_frames.json.gz')
        assert cache['fields']==['cell','speed_kmh','x_m','lane']
        snapshots=[]
        for stamp,vs in sorted(cache['frames'].items(),key=lambda kv:float(kv[0])):
            cells=defaultdict(list)
            for c,v,x,lane in vs.values():
                if c in (10,11,12):cells[c,lane].append(v)
            sample={}
            for lane in range(1,5):
                if any(len(cells[c,lane])<2 for c in (10,11,12)):continue
                mean=lambda c:sum(cells[c,lane])/len(cells[c,lane])
                rho=lambda c:len(cells[c,lane])/net.freeway_segment_length_profile_km['FW_E'][c]
                sample[lane]=dict(time_sec=float(stamp),lane=lane,v=mean(11),up=mean(10),rho=rho(11),
                    down=rho(12),weight=min(5,len(cells[11,lane]))/5)
            snapshots.append(sample)
        rows=[]
        for a,b,c in zip(snapshots,snapshots[1:],snapshots[2:]):
            for lane in a.keys()&b.keys()&c.keys():
                assert abs(c[lane]['time_sec']-a[lane]['time_sec']-10)<1e-6
                rows.append(dict(b[lane],observed=(c[lane]['v']-a[lane]['v'])/10))
        return rows

    def terms(row,x):
        critical,nu_ge,nu_lt=x
        desired=p['v_free']*math.exp(-(row['rho']/critical)**p['metanet_a_m']/p['metanet_a_m'])
        relax=(desired-row['v'])/tau
        conv=row['v']*(row['up']-row['v'])/(3600*p['segment_length_km'])
        nu=nu_ge if row['down']>=row['rho'] else nu_lt
        ant=-nu/(tau*p['segment_length_km'])*(row['down']-row['rho'])/(row['rho']+p['metanet_kappa_veh_km_lane'])
        return dict(desired=desired,relaxation=relax,convection=conv,anticipation=ant,
            total=max(net.v_min,row['v']+relax+conv+ant)-row['v'])

    # Verify against the actually executed lane equations, not the superseded
    # aggregate equation logged in the same trace. Port clipping is separate.
    trace=read(I/'closedloop_recorded2250_lever450_trace10681_lane10682_target43/held_actual_RM_C10681_trace.json.gz')
    parity=0.;count=0
    for row in trace['mainline_diagnostics']['speed_terms']:
        if row['cell']!=cell or row.get('lane_equation')!='physical_lane':continue
        assert abs(row['lane_drop_raw'])<1e-10
        up=row['speed_before']+row['convection']*3600*row['length_km']/row['speed_before']
        rebuilt=terms(dict(v=row['speed_before'],up=up,rho=row['rho'],down=row['downstream_rho']),initial)
        parity=max(parity,abs(rebuilt['total']-(row['after_speed_equation']-row['speed_before'])),
            abs(rebuilt['desired']-row['desired']))
        count+=1
    assert count==1800 and parity<1e-8,(count,parity)
    training=dataset(29)
    assert len(training)>=100
    calls=0
    def residual(x):
        nonlocal calls
        calls+=1;assert calls<=100
        return np.array([(terms(r,x)['total']-r['observed'])*math.sqrt(r['weight']) for r in training])
    fit=least_squares(residual,initial,bounds=(lower,upper),loss='huber',f_scale=1.,max_nfev=20,x_scale='jac')
    selected=fit.x.copy()
    # Freeze the single fit before reading the separate validation seed.
    write(HERE/'selected.json',dict(values=selected.tolist(),success=bool(fit.success),status=int(fit.status),
        message=str(fit.message),nfev=int(fit.nfev),residual_calls=calls,optimality=float(fit.optimality)))
    validation=dataset(43)
    def metrics(rows,x):
        e=[terms(r,x)['total']-r['observed'] for r in rows]
        return dict(n=len(e),mae=sum(abs(v) for v in e)/len(e),bias=sum(e)/len(e),
            rmse=math.sqrt(sum(v*v for v in e)/len(e)))
    fitted=copy.deepcopy(reference)
    multiplier=parameters['by_direction']['FW_E']['rho_crit_multiplier']
    fitted['freeway']['physical_cell_fd']['FW_E']['11']['rho_crit']=float(selected[0]/multiplier)
    ant=fitted['freeway']['state_response']['FW_E']['cell_overrides']['11']['anticipation']
    ant['downstream_ge_local']=float(selected[1]);ant['downstream_lt_local']=float(selected[2])
    refpath=HERE/'reference_config.json';write(refpath,fitted)
    manifest['sources']['reference_config']=pin(refpath)
    manifest['qualification']='Three-parameter cell11 fit on REVIEW50 lane dynamics; NOT operational/gain qualified'
    mp=HERE/'candidate_manifest.json';write(mp,manifest)
    tuning=read(HERE.parent/'lane10682_target_transport/candidate_config.json')
    tuning['freeway']['lane_plant']=mp.relative_to(ROOT).as_posix()
    write(HERE/'candidate_config.json',tuning)
    rebuilt=CanonicalFreewayModel(geometry,refpath)._config('FW_E',parameters['by_direction']['FW_E']).network
    assert abs(rebuilt.freeway_segment_params['FW_E'][11]['rho_crit']-selected[0])<1e-9
    assert rebuilt.freeway_state_response['FW_E']['cell_overrides']['11']['anticipation']==ant
    result=dict(status='fit_completed_pending_autonomous_validation',selected=selected.tolist(),initial=initial.tolist(),
        solver_success=bool(fit.success),residual_calls=calls,exact_executed_lane_equation_max_error=parity,
        executed_lane_equations=count,training=dict(before=metrics(training,initial),after=metrics(training,selected)),
        validation43=dict(before=metrics(validation,initial),after=metrics(validation,selected)),
        training_by_lane={str(g):dict(before=metrics([r for r in training if r['lane']==g],initial),
            after=metrics([r for r in training if r['lane']==g],selected)) for g in sorted(set(r['lane'] for r in training))},
        gradient_samples={key:sum((r['down']>=r['rho'])==value for r in training) for key,value in [('ge',True),('lt',False)]},
        source_pins=PINS,only_current_state_in_autonomous_prediction=True,new_vissim=0,new_fzp=0)
    write(HERE/'fit.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_pins','training_by_lane')},ensure_ascii=False))

if __name__=='__main__':main()
