"""Extend the unchanged-coefficient local transport comparison to150s.

Uses saved cutoff inputs, canonical speed equations and independently saved1s
observations. No native run, future boundary input or parameter fitting.
"""
from pathlib import Path
import copy
import hashlib
import json
import math
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import downstream_spatial_rollout as s
K=Path(__file__).resolve().parent
ROOT=K.parents[3]


def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out=K/'downstream_spatial_horizon_v1';out.mkdir(exist_ok=False)
    geometry_path=s.d.H/'controller_response_s23_v1/none/geometry.json'
    config=K/'transport_step1_exchange_off_v2/config.json';parameters=K/'port_travel_fit_v1/selected_parameters.json'
    model=s.d.e.load_base_model(load(geometry_path),config)
    cfg=model._config('FW_E',load(parameters)['parameters']['by_direction']['FW_E'])
    inputs_path=K/'downstream_spatial_rollout_v1/inputs.json';inputs=load(inputs_path)
    obs_path=K/'compact_lane_state_v1/states.json';observations=load(obs_path)
    runs=[];traces={};observed_checks=0;prefix_checks=0
    for arm in ('none','rm_ramp'):
        for start in (2400,2550,2700):
            for mode in ('coarse','lane_100m'):
                key=f'{arm}_{start}_{mode}';payload=inputs[key]
                initial=copy.deepcopy(payload['inputs']);initial['rates']={int(k):v for k,v in initial['rates'].items()}
                for t,rows in payload['observed'].items():
                    for c,previous in rows.items():
                        actual=observations[arm]['states'][t][c]
                        assert previous['n']==actual['n'] and abs(previous['v']-actual['v'])<1e-10
                        observed_checks+=1
                trace,checks=s.rollout(initial,cfg,150,momentum_advection=mode=='lane_100m')
                trace=json.loads(json.dumps(trace))
                prefix_path=(K/'downstream_spatial_rollout_v1'/(key+'.json') if mode=='coarse' else
                    K/'local_interaction_spatial_validation_v1'/(key+'_moment_only.json'))
                assert trace[:30]==load(prefix_path);prefix_checks+=1
                intervals=[]
                for lo,hi in ((1,30),(31,75),(76,150),(1,150)):
                    ev=[];en=[];actual_ttt=predicted_ttt=queue_cost=0.
                    for row in trace[lo-1:hi]:
                        t=str(start+row['step']);actual=observations[arm]['states'][t]
                        for c,estimated in row['cells'].items():
                            ev.append(estimated['v']-actual[c]['v']);en.append(estimated['n']-actual[c]['n'])
                            predicted_ttt+=estimated['n']/3600;actual_ttt+=actual[c]['n']/3600
                        queue_cost+=row['queue']/3600
                    intervals.append(dict(start_step=lo,end_step=hi,speed_rmse=math.sqrt(sum(x*x for x in ev)/len(ev)),
                        speed_bias=sum(ev)/len(ev),stock_mae=sum(abs(x) for x in en)/len(en),
                        predicted_local_ttt=predicted_ttt,actual_local_ttt=actual_ttt,
                        predicted_boundary_queue_ttt=queue_cost))
                row=dict(arm=arm,start=start,mode=mode,intervals=intervals,checks=checks,
                    final_queue=trace[-1]['queue'],final_terminal=trace[-1]['exits'])
                runs.append(row);traces[key]=trace;s.d.e.save(out/(key+'.json'),trace)
                print(arm,start,mode,intervals[-1],flush=True)
    response=[]
    for start in (2400,2550,2700):
        for mode in ('coarse','lane_100m'):
            a=next(r for r in runs if r['arm']=='none' and r['start']==start and r['mode']==mode)
            b=next(r for r in runs if r['arm']=='rm_ramp' and r['start']==start and r['mode']==mode)
            dif=[]
            for i,(ra,rb) in enumerate(zip(traces[f'none_{start}_{mode}'],traces[f'rm_ramp_{start}_{mode}'])):
                t=str(start+i+1)
                for c in ra['cells']:
                    actual=observations['rm_ramp']['states'][t][c]['v']-observations['none']['states'][t][c]['v']
                    estimate=rb['cells'][c]['v']-ra['cells'][c]['v'];dif.append(estimate-actual)
            response.append(dict(start=start,mode=mode,response_speed_rmse=math.sqrt(sum(x*x for x in dif)/len(dif)),
                predicted_local_delta_ttt=b['intervals'][-1]['predicted_local_ttt']-a['intervals'][-1]['predicted_local_ttt'],
                actual_local_delta_ttt=b['intervals'][-1]['actual_local_ttt']-a['intervals'][-1]['actual_local_ttt']))
    source=[Path(__file__),Path(s.__file__),geometry_path,config,parameters,inputs_path,obs_path]
    s.d.e.save(out/'result.json',dict(qualified=False,new_native_runs=0,future_inputs_to_model=False,
        core_changes=False,no_fitting=True,runs=runs,response=response,observed_value_pairs_checked=observed_checks,
        original30s_traces_exact=prefix_checks,
        source_pins={p.relative_to(ROOT).as_posix():sha(p) for p in source},
        scope='Same6port-free cells and frozen past30s boundary,150s local prediction. Not450s RM/VSL gain qualification.',
        cost_definition='Sum of1s end-frame inventories/3600, same window for predicted/actual; boundary queue cost reported separately.',
        limitations=['Post-treatment2550/2700 initial states differ between arms; response table is a local state-propagation check.',
            'Future upstream treatment responses are not connected. At2400 initial state and causal inputs are equal.',
            'No new seed, whole-component cost, freeflow selection, fullOmega or GNE validation.']))


if __name__=='__main__':main()
