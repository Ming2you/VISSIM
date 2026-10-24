"""Autonomous450s gain qualification; no future state / exchange substitutions."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, CASES, MODEL, H, ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
import json
import copy
import time
import argparse

HERE=Path(__file__).resolve().parent;LANE=H/'lane_group_response_20260919'


def normalized(x):return json.loads(json.dumps(x))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--candidate-config',type=Path,default=HERE/'fit_v1/config.json')
    parser.add_argument('--output',type=Path,default=HERE/'qualification_v1')
    parser.add_argument('--parameters',type=Path)
    parser.add_argument('--ramp-origin',type=Path)
    args=parser.parse_args()
    args.candidate_config=args.candidate_config.resolve()
    out=args.output;out.mkdir(exist_ok=False)
    params=e.load(LANE/'qualification_v6/parameters.json')['parameters']
    candidate_params=e.load(args.parameters)['parameters'] if args.parameters else params
    canonical_params=e.load(MODEL/'selected_parameters.json')['parameters']
    profile=e.load(MODEL/'port_profile.json')
    native=e.load(H/'merge_drain_response_20260919/native_audit_v1/result.json')
    results={};exact_default=exact_previous=0;guards=[];begin=time.perf_counter()
    for seed,folder,bank,start in CASES:
        data=e.ObservationData(folder);lane=e.load(LANE/f'observations_v1/s{seed}.json')
        origin_doc=e.load(args.ramp_origin/f's{seed}.json') if args.ramp_origin else {}
        origins=origin_doc.get('counts')
        baseline=e.load_base_model(data.geometry,MODEL/'config.json')
        old=e.load_base_model(data.geometry,LANE/'qualification_v6/config.json')
        model=e.load_base_model(data.geometry,args.candidate_config)
        protocol=e.load(bank/'protocol.json');arms={}
        for arm in ARMS:
            seq=protocol['candidate_bank'].get(arm,{'green':[],'vsl':[]})
            def command(t):
                i=int((t-start)//150)
                return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                        {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
            w=e.window(data,baseline,start,'history_forecast',profile,command)
            canonical=normalized(e.simulate(baseline,w,canonical_params))
            assert canonical==e.load(H/f'gain_response_20260919/fit_v2/prediction_{seed}_baseline_{arm}.json'),'Default regression'
            exact_default+=1
            w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(start)]}}
            previous=normalized(e.simulate(old,w,params))
            assert previous==e.load(LANE/f'qualification_v6/prediction_{seed}_{arm}.json'),'Disabled feature regression'
            exact_previous+=1
            w=e.window(data,model,start,'history_forecast',profile,command,port_origin_counts=origins)
            w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(start)]}}
            if origins is not None:w['lane_group_dynamics']['FW_E']['initial_ramp_origin']=origins[str(start)]
            if model.port_initial_positions:
                w['lane_group_dynamics']['FW_E']['initial_off_eligible']=origin_doc['eligible_before_off'][str(start)]
            pred=normalized(e.simulate(model,w,candidate_params))
            reference=data if arm=='none' else e.ObservationData(bank/'observations'/arm)
            score=e.score_rollout(reference,start,pred,'FW_E')
            if score['invalid']:raise ArithmeticError(score)
            for key in ['cells','flows','ports','ramps']:
                assert [r for r in pred[key] if r['road']=='FW_W']==[r for r in canonical[key] if r['road']=='FW_W']
            details=next(r for r in pred['diagnostics']['roads'] if r['road']=='FW_E')
            arms[arm]={'parts':parts(pred),'score':score,
                'continuity_residual':details['lane_group_continuity_residual_max_veh']}
            if 'state_exchange_feature_values' in details:
                arms[arm]['feature_clip_fraction']=details['state_exchange_clipped_feature_values']/details['state_exchange_feature_values']
            e.save(out/f'prediction_{seed}_{arm}.json',pred)
        deltas={a:{k:arms[a]['parts'][k]-arms['none']['parts'][k] for k in arms[a]['parts']} for a in ARMS[1:]}
        for d in deltas.values():d['total']=sum(d.values())
        actual=native[str(seed)]['delta_1s']
        result={'arms':arms,'deltas':deltas,'actual':actual,'state_guards':{}}
        for t in [900,1650,2400,3600]:
            w=e.window(data,baseline,t,'history_forecast',profile,lambda _: ({},{}))
            original=e.score_rollout(data,t,e.simulate(baseline,w,canonical_params),'FW_E')
            w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(t)]}}
            previous=e.score_rollout(data,t,e.simulate(old,w,params),'FW_E')
            w=e.window(data,model,t,'history_forecast',profile,lambda _: ({},{}),port_origin_counts=origins)
            w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(t)]}}
            if origins is not None:w['lane_group_dynamics']['FW_E']['initial_ramp_origin']=origins[str(t)]
            if model.port_initial_positions:
                w['lane_group_dynamics']['FW_E']['initial_off_eligible']=origin_doc['eligible_before_off'][str(t)]
            candidate=e.score_rollout(data,t,e.simulate(model,w,candidate_params),'FW_E')
            valid=not candidate['invalid'] and candidate['objective']<=1.1*original['objective']
            result['state_guards'][str(t)]={'canonical':original,'previous_lane':previous,'candidate':candidate,'passed':valid}
            guards.append(valid)
        results[str(seed)]=result;e.save(out/f'result_{seed}.json',result)
        print('GAIN',seed,{a:round(d['total'],6) for a,d in deltas.items()},flush=True)
    records=[]
    for s,r in results.items():
        for a,d in r['deltas'].items():
            truth=r['actual'][a]['FW_E']
            records.append({'seed':int(s),'arm':a,'prediction':d,'actual':truth,
                'total_sign_correct':d['total']*truth['total']>0,
                'component_signs_correct':{k:d[k]*truth[k]>0 for k in ['mainline','on','off']}})
    e.save(out/'results.json',results)
    e.save(out/'verification.json',{'default_predictions_exact':exact_default,'previous_candidate_exact':exact_previous,
        'west_unchanged':True,'future_state_resets':0,'future_exchange_inputs':0,
        'state_guards_passed':sum(guards),'state_guards_total':len(guards),'gain_cases':records,
        'native_runs_started':0,'elapsed_s':time.perf_counter()-begin})


if __name__=='__main__':main()
