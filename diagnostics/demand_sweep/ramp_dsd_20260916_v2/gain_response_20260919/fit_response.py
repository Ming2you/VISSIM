"""Small response-oriented calibration with absolute-state and held-seed gates."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, CASES, MODEL, H, ARMS
import copy
import statistics
import hashlib

HERE = Path(__file__).resolve().parent


def parts(pred):
    r = next(r for r in pred['diagnostics']['roads'] if r['road'] == 'FW_E')
    return {'mainline': r['model_residence_10s_veh_h'], 'on': r['ramp_connector_residence_local_1s_veh_h'],
            'off': r['off_connector_residence_event_veh_h']}


def main():
    out = HERE/'fit_v2'; out.mkdir(exist_ok=False)
    native = e.load(H/'merge_drain_response_20260919/native_audit_v1/result.json')
    baseline = e.load(MODEL/'selected_parameters.json')['parameters']
    profile = e.load(MODEL/'port_profile.json')
    cases = {}
    for seed, folder, bank, start in CASES:
        data = e.ObservationData(folder)
        model = e.load_base_model(data.geometry, MODEL/'config.json')
        protocol = e.load(bank/'protocol.json')
        windows = {}
        for arm in ARMS:
            seq = protocol['candidate_bank'].get(arm, {'green':[], 'vsl':[]})
            def command(t):
                i = int((t-start)//150)
                return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                        {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
            windows[arm] = e.window(data, model, start, 'history_forecast', profile, command)
        cases[seed] = (data, model, windows, start)
    axes = {'delta_merge':[0., .5, 1.], 'tau_sec':[12.,24.,40.],
            'nu_km2_h':[12.,35.,70.], 'kappa_veh_km_lane':[5.,17.,40.], 'lane_drop_phi':[0.,1.5,3.]}
    e.save(out/'protocol.json', {'training_seeds':[13,23], 'development_validation_seed':33,
        'seed33_not_fresh_holdout':True, 'axes':axes,
        'selection':'Two bounded coordinate passes on response loss, no reward or cost-weight change. Reject if either seed NC state loss worsens by more than10%.',
        'response_loss':'Mean squared error of total deltaTTT/0.5 plus mean of mainline,on,off deltaTTT errors/0.5 squared. This fits plant parameters; MPC objective remains unchanged.',
        'independent_freeflow_recovery_gate':'Selected response candidate must preserve NC state errors at900,1650,2400,3600 on both training seeds.',
        'uncertainty':'One matched pair per seed; tiny signs are not statistical evidence.',
        'all_future_inputs':'Predicted from pre-cutoff history only', 'native_runs_started':0,
        'config':str(MODEL.relative_to(e.ROOT)), 'mainline_FD_and_geometry_fixed':True,
        'code_pins':{str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in [e.CAL/'canonical_harness.py', H/'evaluate_response.py', e.ROOT/'evaluation/controllers/physical_ramp_boundary.py']}})
    def evaluate(p, seeds, retain=False):
        results = {}; losses=[]
        for seed in seeds:
            data, model, windows, start = cases[seed]
            forecasts = {arm:e.simulate(model,w,p) for arm,w in windows.items()}
            comps = {arm:parts(pred) for arm,pred in forecasts.items()}
            state = e.score_rollout(data,start,forecasts['none'],'FW_E')
            assert all(not e.score_rollout(data,start,pred,'FW_E')['invalid'] for pred in forecasts.values())
            deltas={}
            for arm in ARMS[1:]:
                target = native[str(seed)]['delta_1s'][arm]['FW_E']
                delta = {k:comps[arm][k]-comps['none'][k] for k in comps[arm]}
                delta['total'] = sum(delta.values())
                loss = ((delta['total']-target['total'])/.5)**2 + statistics.mean(((delta[k]-target[k])/.5)**2 for k in comps[arm])
                losses.append(loss)
                deltas[arm]={'predicted':delta,'actual':target,'loss':loss}
            results[str(seed)]={'state':state,'deltas':deltas}
            if retain:
                for arm,pred in forecasts.items():e.save(out/f'prediction_{seed}_{retain}_{arm}.json',pred)
        return {'loss':statistics.mean(losses),'seeds':results}
    initial=evaluate(baseline,[13,23]); trace=[]; cache={}; best=copy.deepcopy(baseline)
    limits={s:initial['seeds'][str(s)]['state']['objective']*1.10 for s in [13,23]}
    def assess(p):
        key=tuple(sorted(p['by_direction']['FW_E'].items()))
        if key not in cache:
            r=evaluate(p,[13,23]);r['parameters']=copy.deepcopy(p)
            r['eligible']=all(r['seeds'][str(s)]['state']['objective']<=limits[s] for s in [13,23])
            cache[key]=r;trace.append(r)
        return cache[key]
    incumbent=assess(best)
    for pass_no in [1,2]:
        for name,values in axes.items():
            trials=[incumbent]
            for value in values:
                p=copy.deepcopy(best);p['by_direction']['FW_E'][name]=value
                r=assess(p)
                if r['eligible']:trials.append(r)
            incumbent=min(trials,key=lambda r:r['loss']);best=copy.deepcopy(incumbent['parameters'])
            print(pass_no,name,'response_loss',round(incumbent['loss'],6),'candidates',len(cache),flush=True)
    e.save(out/'trace.json',trace)
    selected=out/'model';selected.mkdir()
    for name in ['config.json','port_profile.json']:e.save(selected/name,e.load(MODEL/name))
    e.save(selected/'selected_parameters.json',{'parameters':best,'status':'Response-fit diagnostic candidate, qualification pending'})
    result={name:evaluate(p,[13,23,33],retain=name) for name,p in [('baseline',baseline),('candidate',best)]}
    for name,p in [('baseline',baseline),('candidate',best)]:
        result[name]['state_guard']={}
        for seed in [13,23,33]:
            data,model,windows,start=cases[seed]
            result[name]['state_guard'][str(seed)]={}
            for t in [900,1650,2400,3600]:
                w=e.window(data,model,t,'history_forecast',profile,lambda _: ({},{}))
                pred=e.simulate(model,w,p)
                result[name]['state_guard'][str(seed)][str(t)]=e.score_rollout(data,t,pred,'FW_E')
    e.save(out/'evaluation.json',result)
    print('BASELINE',initial['loss'],'SELECTED',incumbent['loss'],best['by_direction']['FW_E'],flush=True)
    for seed in [13,23,33]:
        print('DELTA',seed,{a:round(r['predicted']['total'],5) for a,r in result['candidate']['seeds'][str(seed)]['deltas'].items()},flush=True)


if __name__=='__main__':main()
