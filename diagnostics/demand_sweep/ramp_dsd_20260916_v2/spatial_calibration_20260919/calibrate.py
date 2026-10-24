"""Fit spatial FD on seed13 uncontrolled records; never fit a control reward.

Uses the existing canonical plant and segment parameter configuration. Seeds23
and33 and paired interventions are evaluated only after parameters are frozen.
"""
from pathlib import Path
import copy
import hashlib
import json
import statistics
import sys
import time

HERE = Path(__file__).resolve().parent
H = HERE.parent
ROOT = H.parents[2]
sys.path[:0] = [str(ROOT), str(H/'state_response_20260919')]
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from study import direction_parts

BASE = H/'controller_response_4500_v1/model_v5_node'
# Groups follow physical topology, fixed before fitting: source, ordinary four
# lanes, first exit complex, actual lane drop/merge, ordinary three lanes.
GROUPS = {'source': [0], 'ordinary4': list(range(1,7))+[10,11,12],
          'exit_complex': [7,8,9], 'drop_merge': [13,14],
          'ordinary3': list(range(15,21))}
STARTS = [900,1650,2400,3600]
ARMS = ['none','rm_ramp','vsl','both']

def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')

def setup(folder, config=BASE/'config.json', profile=None):
    data=e.ObservationData(folder)
    model=e.load_base_model(data.geometry,config)
    profile=profile or e.load(BASE/'port_profile.json')
    windows={t:e.window(data,model,t,'history_forecast',profile,lambda t: ({},{})) for t in STARTS}
    return data,model,profile,windows

def summary(scores):
    return {'loss':statistics.mean(s['objective'] for s in scores),
        'speed_rmse':statistics.mean(s['speed']['rmse'] for s in scores),
        'density_rmse':statistics.mean(s['density']['rmse'] for s in scores),
        'flow_rmse':statistics.mean(s['flow_vph']['rmse'] for s in scores),
        'mainline_ttt_mae':statistics.mean(abs(s['freeway_ttt_predicted_veh_h']-s['freeway_ttt_observed_veh_h']) for s in scores),
        'invalid':any(s['invalid'] for s in scores),
        'confusion':{k:sum(s['congestion_confusion'][k] for s in scores) for k in scores[0]['congestion_confusion']}}

def fit(out):
    out.mkdir(exist_ok=False)
    data,model,profile,windows=setup(H/'controller_response_4500_v1/none')
    original=copy.deepcopy(model.base.network.freeway_segment_params['FW_E'])
    baseparams=e.load(BASE/'selected_parameters.json')['parameters']
    protocol={'training':'seed13 no control only','starts_s':STARTS,'horizon_s':450,
        'validation_seeds':[23,33],'groups':GROUPS,'rho_crit_scales':[.6,.8,1.,1.2,1.4,1.8,2.2],
        'v_free_multipliers':[.91,1.], 'coordinate_passes':2,
        'loss':'Unchanged mean(speed_RMSE/20)^2+(density_RMSE/10)^2+(flow_RMSE/1000)^2',
        'unchanged':'METANET equations, tau/nu/merge, demand, actions, boundaries, waiting accounting',
        'not_claimed':'Static FD fit is not lane-resolved queues or a full coupled urban plant.'}
    write(out/'protocol.json',protocol)
    cache={};trace=[];beg=time.perf_counter()
    def score(spec):
        key=json.dumps(spec,sort_keys=True)
        if key in cache:return cache[key]
        for group,indices in GROUPS.items():
            for i in indices:
                model.base.network.freeway_segment_params['FW_E'][i]['rho_crit']=original[i]['rho_crit']*spec[group]
        params=copy.deepcopy(baseparams)
        params['by_direction']['FW_E']['v_free_multiplier']=spec['vf']
        scores=[]
        for t,w in windows.items():
            pred=e.simulate(model,w,params)
            scores.append(e.score_rollout(data,t,pred,'FW_E'))
        result={'spec':copy.deepcopy(spec),'summary':summary(scores),'windows':scores}
        cache[key]=result;trace.append(result)
        write(out/'fit_trace.json',trace)
        print('fit',len(trace),round(result['summary']['loss'],4),spec,flush=True)
        return result
    best=score({**dict.fromkeys(GROUPS,1.),'vf':.91})
    baseline=copy.deepcopy(best)
    for vf in [.91,1.]:
        row=score({**dict.fromkeys(GROUPS,1.),'vf':vf})
        if row['summary']['loss']<best['summary']['loss']:best=row
    for sweep in range(2):
        changed=False
        for g in GROUPS:
            local=best
            for s in protocol['rho_crit_scales']:
                row=score({**best['spec'],g:s})
                if row['summary']['loss']<local['summary']['loss']:local=row
            changed |= local is not best
            best=local
        if not changed:break
    write(out/'fit_result.json',{'baseline':baseline,'selected':best,'evaluations':len(trace),'wall_sec':time.perf_counter()-beg})
    # Freeze a configuration consumed by the EXISTING model loader, no new adapter.
    modeldir=out/'model';modeldir.mkdir()
    config=e.load(BASE/'config.json');segment=e.load(ROOT/config['freeway']['segment_params'])
    for g,indices in GROUPS.items():
        for i in indices:
            r=segment['segments'][f'FW_E_S{i}']
            r['rho_crit']*=best['spec'][g]
            r['q_cap_veh_h_lane']=r['v_free']*r['rho_crit']*__import__('math').exp(-1/r['metanet_a_m'])
    segment['spatial_calibration']={'protocol':str((out/'protocol.json').relative_to(ROOT)),
        'seed':13,'control_training':False,'spec':best['spec'],'status':'frozen before validation; not adopted by default'}
    write(modeldir/'segment_params.json',segment)
    config['freeway']['segment_params']=(modeldir/'segment_params.json').relative_to(ROOT).as_posix()
    write(modeldir/'config.json',config)
    params=copy.deepcopy(baseparams);params['by_direction']['FW_E']['v_free_multiplier']=best['spec']['vf']
    write(modeldir/'selected_parameters.json',{'parameters':params,'adoption':'Experimental spatial calibration, awaiting response evaluation'})
    write(modeldir/'port_profile.json',profile)
    write(out/'freeze.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in modeldir.iterdir()})
    return modeldir

def evaluate(out,modeldir):
    all_results={}
    for seed,folder,bank,start in [(13,H/'controller_response_4500_v1/none',H/'response_pairs_v1',1650),
            (23,H/'controller_response_s23_v1/none',H/'response_late_s23_v1',2400),
            (33,H/'state_response_20260919/native_s33_v1/observations/none',H/'state_response_20260919/native_s33_v1',2400)]:
        all_results[str(seed)]={}
        for name,path in [('baseline',BASE),('spatial',modeldir)]:
            data,model,profile,windows=setup(folder,path/'config.json')
            params=e.load(path/'selected_parameters.json')['parameters'];scores=[]
            for t,w in windows.items():
                pred=e.simulate(model,w,params);scores.append(e.score_rollout(data,t,pred,'FW_E'))
            protocol=e.load(bank/'protocol.json');pairs={}
            for arm in ARMS:
                seq=protocol['candidate_bank'].get(arm,{'green':[],'vsl':[]})
                def command(t):
                    i=int((t-start)//150)
                    return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                        {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
                actual=data if arm=='none' else e.ObservationData(bank/'observations'/arm)
                w=e.window(data,model,start,'history_forecast',profile,command)
                pred=e.simulate(model,w,params)
                pairs[arm]={'predicted':direction_parts(data,model,start,pred),'actual':direction_parts(actual,model,start),
                    'score':e.score_rollout(actual,start,pred,'FW_E')}
                write(out/f'prediction_{seed}_{name}_{arm}.json',pred)
            deltas={}
            for arm in ARMS[1:]:
                deltas[arm]={}
                for which in ['predicted','actual']:
                    parts={k:pairs[arm][which]['FW_E'][k]-pairs['none'][which]['FW_E'][k] for k in ['mainline','on','off']}
                    deltas[arm][which]={**parts,'total':sum(parts.values())}
            all_results[str(seed)][name]={'no_control':summary(scores),'windows':scores,'deltas':deltas,
                'response_mae':statistics.mean(abs(x['predicted']['total']-x['actual']['total']) for x in deltas.values()),
                'exact_sign_matches':sum(((x['predicted']['total']>0)-(x['predicted']['total']<0))==
                                         ((x['actual']['total']>0)-(x['actual']['total']<0)) for x in deltas.values()),
                'sign_definition':'Three-way negative/zero/positive; zero is not a benefit; no statistical significance implied',
                'any_invalid':any(s['invalid'] for s in scores) or any(x['score']['invalid'] for x in pairs.values())}
            print('evaluate',seed,name,all_results[str(seed)][name]['no_control'], 'response',all_results[str(seed)][name]['response_mae'],flush=True)
            write(out/'evaluation.json',all_results)

if __name__=='__main__':
    out=HERE/'fit_v1'
    if len(sys.argv)>1 and sys.argv[1]=='evaluate':
        evaluate(out,out/'model')
    else:
        modeldir=fit(out)
        evaluate(out,modeldir)
