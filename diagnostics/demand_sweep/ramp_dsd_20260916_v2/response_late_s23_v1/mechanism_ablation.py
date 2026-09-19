"""Bounded hypothesis tests using completed records; not an adopted predictor."""
import copy
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from canonical_harness import accounting

OUT = HERE / 'mechanism_ablation_v3'
H = HERE.parent


def main():
    OUT.mkdir(exist_ok=False)
    parameters = e.load(H/'controller_response_4500_v1/model_v4/selected_parameters.json')['parameters']
    profile = e.load(H/'controller_response_4500_v1/model_v4/port_profile.json')
    audit = e.load(HERE/'model_mechanism_audit.json')
    distributions = next(v for k,v in audit.items() if isinstance(v,dict) and '120' in v)
    ratios = {int(k): v['mean_kmh']/distributions['120']['mean_kmh'] for k,v in distributions.items()}
    e.save(OUT/'protocol.json', {'hypotheses': {
        'ramp_history': 'Only 10681 transit speed uses last150s space-mean snapshot speeds instead of pre900s free traversal. OFF-only diagnostic; not a capacity estimate or an RM-ready state model.',
        'vsl_ratio': 'Uncapped equilibrium speed multiplied by native desired-speed mean ratio. Tests distribution sensitivity; no capacity gain/drop, reward or coefficient fitting. Diagnostic hook only.'},
        'vsl_ratios': ratios, 'ramp_history_sec':150, 'future_observations_in_predictor':False,
        'development_data_not_independent_holdout':True, 'adopted':False})
    results = {}
    for name,bank,data_folder in [('early13',H/'response_pairs_v1',H/'controller_response_4500_v1/none'),
                                  ('late23',HERE,H/'controller_response_s23_v1/none')]:
        protocol=e.load(bank/'protocol.json'); start=protocol['start_s']
        data=e.ObservationData(data_folder)
        model=e.load_base_model(data.geometry,H/'controller_response_4500_v1/model_v4/config.json')
        samples=[float(row[1]) for t in range(start-120,start+1,30)
                 for row in data.port_cohorts[str(t)]['10681']]
        measured=statistics.mean(samples)
        if measured<=0: raise ValueError('Zero observed transit requires a queue model, not a speed floor')
        result={'start_s':start,'transit_speed_before':profile['travel_speed_kmh']['10681'],
                'observed_transit_proxy_kmh':measured,'initial_queue10681':len(data.port_cohorts[str(start)]['10681']), 'variants':{}}
        for variant in ['baseline','ramp_history','vsl_ratio','both']:
            result['variants'][variant]={}
            for arm in ['none','rm_ramp','vsl','both']:
                sequence=protocol['candidate_bank'].get(arm,{'green':[],'vsl':[]})
                def command(t):
                    index=int((t-start)//150)
                    return ({protocol.get('meter_id','RM_C10490'):sequence['green'][index]} if sequence['green'] else {},
                            {d:sequence['vsl'][index] for d in protocol.get('dsd_ids',[59,60,61,62])} if sequence['vsl'] else {})
                p=copy.deepcopy(profile)
                if variant in ('ramp_history','both'): p['travel_speed_kmh']['10681']=measured
                w=e.window(data,model,start,'history_forecast',p,command)
                original=accounting._mn.effective_desired_speed_kmh
                def desired(*args):
                    # Preserve installed per-segment parameter context in original.
                    if args[5]:
                        uncapped=list(args);uncapped[5]=False
                        return original(*uncapped)*ratios[int(args[3])]
                    return original(*args)
                if variant in ('vsl_ratio','both'): accounting._mn.effective_desired_speed_kmh=desired
                try: pred=e.simulate(model,w,parameters)
                finally: accounting._mn.effective_desired_speed_kmh=original
                metrics=e.component(data,model,start,pred)
                metrics['diagnostics']=pred['diagnostics']
                metrics['first30_merge10681']=sum(x['accepted_merge_veh'] for x in pred['ramps'] if x['ramp']=='RM_C10681' and x['end_sec']<=start+30)
                metrics['final_stock10681']=next(x['end']['connector_veh'] for x in pred['ramps'] if x['ramp']=='RM_C10681' and x['end_sec']==start+450)
                result['variants'][variant][arm]=metrics
                e.save(OUT/f'{name}_{variant}_{arm}.json',pred)
                print(name,variant,arm,'TTT',round(metrics['component_ttt_veh_h'],4),'merge10681',round(metrics['merges']['RM_C10681'],2),flush=True)
        results[name]=result
        e.save(OUT/(name+'_summary.json'),result)
    e.save(OUT/'results.json',results)


if __name__=='__main__': main()
