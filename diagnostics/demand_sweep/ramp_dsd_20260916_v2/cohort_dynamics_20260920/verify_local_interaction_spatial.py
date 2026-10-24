"""Recheck bounded interaction evidence and local spatial experiments."""
from pathlib import Path
from collections import Counter
from unittest.mock import patch
import copy
import hashlib
import json
import math
import sys
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import downstream_spatial_rollout as s
K=Path(__file__).resolve().parent
ROOT=K.parents[3]


def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out=K/'local_interaction_spatial_validation_v1';out.mkdir(exist_ok=False)
    pins=0
    for folder,archived in (
        ('paired_native_interaction_v1',None),
        ('downstream_spatial_rollout_v1','source_before_calibration.txt'),
        ('downstream_spatial_calibration_v3','source_before_moment_transport.txt'),
        ('downstream_spatial_moment_calibration_v1',None)):
        r=load(K/folder/'result.json')
        for name,digest in r['source_pins'].items():
            p=ROOT/name
            if archived and p.name=='downstream_spatial_rollout.py':p=K/folder/archived
            assert sha(p)==digest,name;pins+=1
    pair=load(K/'paired_native_interaction_v1/result.json')
    exposures=load(K/'paired_native_interaction_v1/exposure.json')
    for target in pair['by_target']:
        for arm,record in target['arms'].items():
            rows=[r for r in exposures if r['target']==target['target'] and r['arm']==arm]
            assert sorted({r['vehicle'] for r in rows})==record['subjects']
            assert len(rows)==record['samples']
            assert sum(r['interaction'].startswith('Brake') for r in rows)==record['brake_samples']
            assert abs(sum(max(0.,-r['delta_speed_kmh']) for r in rows)-record['actual_decel_kmh'])<1e-8
    assert pair['initial_mainline']==657 and pair['first_differences']==43
    for r in pair['first_difference_by_vehicle'].values():
        assert 2418<=r['time_s']<=2460
    initial_native=load(K/'route_state_native_v1/rm_ramp_s23/analysis_v2/interaction_frames.json')
    initial_ids={int(r[1]) for r in initial_native['global_initial_rows']}
    assert {r['vehicle'] for r in exposures}<=initial_ids and {r['target'] for r in exposures}<=initial_ids
    steps=load(K/'paired_native_interaction_v1/steps.json')
    for prefix in pair['prefixes']:
        totals={a:Counter() for a in ('none','rm')}
        for row in steps:
            if row['time_s']<=prefix['end_s']:
                for a in totals:totals[a].update(row['arms'][a])
        for key,value in prefix['rm_minus_nc'].items():assert abs(totals['rm'][key]-totals['none'][key]-value)<1e-7
    geometry=s.d.e.load(s.d.H/'controller_response_s23_v1/none/geometry.json')
    model=s.d.e.load_base_model(geometry,K/'transport_step1_exchange_off_v2/config.json')
    cfg=model._config('FW_E',load(K/'port_travel_fit_v1/selected_parameters.json')['parameters']['by_direction']['FW_E'])
    inputs=load(K/'downstream_spatial_rollout_v1/inputs.json')
    replayed=0;moment_only=[];response=[]
    for key,payload in inputs.items():
        start=int(key.split('_')[-2]) if key.endswith('_coarse') or key.endswith('_lane') else int(key.split('_')[-3])
        inp=copy.deepcopy(payload['inputs']);inp['rates']={int(k):v for k,v in inp['rates'].items()}
        trace,checks=s.rollout(inp,cfg)
        assert json.loads(json.dumps(trace))==load(K/'downstream_spatial_rollout_v1'/(key+'.json'))
        replayed+=1
        if not key.endswith('lane_100m'):continue
        trace,checks=s.rollout(inp,cfg,momentum_advection=True)
        errors=[r['cells'][c]['v']-payload['observed'][str(start+r['step'])][str(c)]['v'] for r in trace for c in s.CELLS]
        moment_only.append(dict(case=key,speed_rmse=math.sqrt(sum(x*x for x in errors)/len(errors)),checks=checks))
        s.d.e.save(out/(key+'_moment_only.json'),trace)
    trained=load(K/'downstream_spatial_moment_calibration_v1/result.json')
    fitted_replay=0;kkt_checks=0
    for directory in ('downstream_spatial_calibration_v3','downstream_spatial_moment_calibration_v1'):
        result=load(K/directory/'result.json')
        for mode,coef in result['coefficients'].items():
            rows=load(K/directory/(mode+'_training.json'))
            assert all(2280<=r['time_s']<=2399 and r['step']==1 for r in rows)
            a=np.array([[r['relax'],r['pressure']] for r in rows]);y=np.array([r['target'] for r in rows]);w=np.array([r['weight'] for r in rows])
            theta=np.array([coef['alpha'],coef['beta']]);gradient=a.T@(w*(a@theta-y))
            assert np.allclose(gradient,coef['gradient'],rtol=1e-10,atol=1e-7)
            tol=coef['kkt_tolerance']
            assert abs(gradient[0])<tol if theta[0]>1e-8 else gradient[0]>=-tol
            assert abs(gradient[1])<tol if theta[1]>1e-8 else gradient[1]>=-tol
            rms=math.sqrt(float(np.sum(w*(a@theta-y)**2)/sum(w)))
            assert abs(rms-coef['weighted_equation_rmse_after'])<1e-8;kkt_checks+=1
    coef=trained['coefficients']['lane_100m'];adjusted=copy.deepcopy(cfg)
    for c in s.CELLS:
        p=adjusted.network.freeway_segment_params['FW_E'][c]
        p['metanet_tau_h']/=coef['alpha'];p['metanet_nu_km2_h']*=coef['beta']/coef['alpha']
    for row in trained['runs']:
        key=f"{row['arm']}_{row['start']}_{row['mode']}";inp=copy.deepcopy(inputs[key]['inputs']);inp['rates']={int(k):v for k,v in inp['rates'].items()}
        trace,_=s.rollout(inp,adjusted,collect_speed_terms=True,momentum_advection=True)
        assert json.loads(json.dumps(trace))==load(K/'downstream_spatial_moment_calibration_v1'/(key+'.json'))
        fitted_replay+=1
    # Verify conservative velocity transport independently of its local ODE.
    synthetic=copy.deepcopy(inputs['none_2400_lane_100m']['inputs'])
    synthetic['rates']={c:[[0.]*3 for _ in range(3)] for c in s.CELLS}
    synthetic['n']=[[10*b['length']]*3 for b in synthetic['bins']]
    synthetic['v']=[[60.]*3 for _ in synthetic['bins']]
    synthetic['upstream']=[60.]*3;synthetic['arrivals']=[10*60/3600]*3
    with patch.object(s.ch.accounting._mn,'metanet_speed_update_kmh',lambda speed,*args: speed):
        rows,_=s.rollout(synthetic,cfg,momentum_advection=True)
        for row in rows:
            for c in s.CELLS:
                expected=sum(sum(synthetic['n'][i]) for i,b in enumerate(synthetic['bins']) if b['cell']==c)
                assert abs(row['cells'][c]['n']-expected)<1e-8 and abs(row['cells'][c]['v']-60)<1e-8
        synthetic['upstream']=[90.]*3
        trace,_=s.rollout(synthetic,cfg,1,momentum_advection=True)
        moment0=sum(sum(n*v for n,v in zip(ns,vs)) for ns,vs in zip(synthetic['n'],synthetic['v']))
        moment1=sum(r['n']*r['v'] for r in trace[-1]['cells'].values())
        expected=sum(synthetic['arrivals'])*90-trace[-1]['exits']*60
        assert abs(moment1-moment0-expected)<1e-8
    for start in (2550,2700):
        for mode in ('coarse','lane','lane_100m'):
            banks={a:load(K/'downstream_spatial_rollout_v1'/f'{a}_{start}_{mode}.json') for a in ('none','rm_ramp')}
            obs={a:inputs[f'{a}_{start}_{mode}']['observed'] for a in banks};errors=[];costs={}
            for a,rs in banks.items():costs[a]=dict(pred=sum(sum(c['n'] for c in r['cells'].values()) for r in rs)/3600,
                actual=sum(sum(c['n'] for c in r.values()) for r in obs[a].values())/3600)
            for i,row in enumerate(banks['none']):
                for c,pn in row['cells'].items():
                    pr=banks['rm_ramp'][i]['cells'][c];on=obs['none'][str(start+i+1)][c];orr=obs['rm_ramp'][str(start+i+1)][c]
                    errors.append(pr['v']-pn['v']-orr['v']+on['v'])
            response.append(dict(start=start,mode=mode,response_speed_rmse=math.sqrt(sum(x*x for x in errors)/len(errors)),
                predicted_local_delta_ttt=costs['rm_ramp']['pred']-costs['none']['pred'],
                actual_local_delta_ttt=costs['rm_ramp']['actual']-costs['none']['actual']))
    s.d.e.save(out/'result.json',dict(passed=True,qualified=False,source_pins_checked=pins,
        original_traces_exact=replayed,fitted_traces_exact=fitted_replay,kkt_fits_checked=kkt_checks,
        uniform_transport_cell_checks=180,velocity_moment_boundary_check=True,moment_only=moment_only,
        post_treatment_state_response=response,new_native_runs=0,
        caveat='Implementation/local identification checks only; this does not qualify450s RM/VSL gains.',
        source_pins={p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),Path(s.__file__)]}))
    print(json.dumps(dict(passed=True,original_traces_exact=replayed,fitted_traces_exact=fitted_replay,
        source_pins_checked=pins,kkt_fits_checked=kkt_checks,moment_only=moment_only,qualified=False)))


if __name__=='__main__':main()
