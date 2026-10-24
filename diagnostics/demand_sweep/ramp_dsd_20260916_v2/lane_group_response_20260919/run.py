"""Matched recorded-state qualification. Never launches or resets VISSIM."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, CASES, MODEL, H, ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
import copy
import argparse
import statistics
import json
import time
import hashlib

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    parser.add_argument('--seed',type=int,choices=[13,23,33]);parser.add_argument('--state-guards',action='store_true')
    parser.add_argument('--parameters',type=Path)
    args=parser.parse_args();out=HERE/args.output;out.mkdir(exist_ok=False)
    params=e.load(MODEL/'selected_parameters.json')['parameters'];profile=e.load(MODEL/'port_profile.json')
    candidate_params=e.load(args.parameters)['parameters'] if args.parameters else params
    config=e.load(MODEL/'config.json')
    config['freeway']['physical_mainline_lane_groups']=True
    e.save(out/'config.json',config)
    e.save(out/'parameters.json',{'parameters':candidate_params})
    native=e.load(H/'merge_drain_response_20260919/native_audit_v1/result.json')
    results={};begun=time.perf_counter();unchanged=0
    for seed,folder,bank,start in CASES:
        if args.seed and seed!=args.seed:continue
        data=e.ObservationData(folder);model=e.load_base_model(data.geometry,MODEL/'config.json')
        candidate=e.load_base_model(data.geometry,out/'config.json')
        protocol=e.load(bank/'protocol.json');lane=e.load(HERE/f'observations_v1/s{seed}.json');byarm={}
        for arm in ARMS:
            seq=protocol['candidate_bank'].get(arm,{'green':[],'vsl':[]})
            def command(t):
                i=int((t-start)//150)
                return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                        {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
            w=e.window(data,model,start,'history_forecast',profile,command)
            baseline=e.simulate(model,w,params)
            prior=e.load(H/f'gain_response_20260919/fit_v2/prediction_{seed}_baseline_{arm}.json')
            assert json.loads(json.dumps(baseline))==prior,'Disabled model must reproduce full previous prediction'
            unchanged+=1
            w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(start)]}}
            pred=e.simulate(candidate,w,candidate_params)
            reference=data if arm=='none' else e.ObservationData(bank/'observations'/arm)
            score=e.score_rollout(reference,start,pred,'FW_E')
            if score['invalid']:raise ArithmeticError(score)
            byarm[arm]={'parts':parts(pred),'state':score,'baseline_parts':parts(baseline),
                'baseline_state':e.score_rollout(reference,start,baseline,'FW_E')}
            e.save(out/f'prediction_{seed}_{arm}.json',pred)
            # Unmodified west direction must be exactly reproduced, not just close.
            for key in ['cells','flows','ports','ramps']:
                assert [r for r in pred[key] if r['road']=='FW_W']==[r for r in baseline[key] if r['road']=='FW_W'],key
            print('DONE',seed,arm,round(sum(parts(pred).values()),6),flush=True)
        deltas={arm:{k:byarm[arm]['parts'][k]-byarm['none']['parts'][k] for k in byarm[arm]['parts']} for arm in ARMS[1:]}
        for d in deltas.values():d['total']=sum(d.values())
        result={'arms':byarm,'deltas':deltas,'actual':native[str(seed)]['delta_1s']}
        result['delta_mae']=statistics.mean(abs(deltas[a]['total']-result['actual'][a]['FW_E']['total']) for a in ARMS[1:])
        result['predicted_interaction']=deltas['both']['total']-deltas['rm_ramp']['total']-deltas['vsl']['total']
        if args.state_guards:
            result['state_guards']={}
            for t in [900,1650,2400,3600]:
                w=e.window(data,model,t,'history_forecast',profile,lambda _: ({},{}))
                old=e.simulate(model,w,params)
                w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(t)]}}
                new=e.simulate(candidate,w,candidate_params)
                result['state_guards'][str(t)]={'baseline':e.score_rollout(data,t,old,'FW_E'),
                                               'candidate':e.score_rollout(data,t,new,'FW_E')}
        results[str(seed)]=result;e.save(out/f'results_{seed}.json',result)
        print('SEED',seed,'delta', {a:round(d['total'],6) for a,d in deltas.items()},flush=True)
    e.save(out/'results.json',results)
    e.save(out/'verification.json',{'default_full_prediction_exact_cases':unchanged,'west_unchanged':True,
        'future_state_resets':0,'native_runs_started':0,'elapsed_sec':time.perf_counter()-begun,
        'seeds13_23':'development cases','seed33':'previously inspected development validation, not fresh holdout',
        'state':'Current group stocks/speeds plus preceding150s exchange hazards; frozen empirical hazards are an approximation',
        'parameters_fitted':0,'objective_or_capacity_bonus':False,
        'pins':{str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
          [e.ROOT/'evaluation/controllers/physical_lane_groups.py',e.CAL/'canonical_harness.py',H/'evaluate_response.py',Path(__file__)]}})


if __name__=='__main__':main()
