"""Out-of-window check of a causal transit proxy, not actuator calibration."""
import copy
import json
from pathlib import Path
import statistics
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e


def main():
    out=HERE/'transit_history_validation_v1';out.mkdir(exist_ok=False)
    modeldir=HERE.parent/'controller_response_4500_v1/model_v4'
    params=e.load(modeldir/'selected_parameters.json')['parameters']
    profile=e.load(modeldir/'port_profile.json')
    results=[]
    for seed,folder in [(13,'controller_response_4500_v1/none'),(23,'controller_response_s23_v1/none')]:
        data=e.ObservationData(HERE.parent/folder)
        model=e.load_base_model(data.geometry,modeldir/'config.json')
        for start in [900,1200,1500,1650,1950,2250,2400,2700,3000,3300,3600,3900]:
            samples=[float(row[1]) for t in range(start-120,start+1,30) for row in data.port_cohorts[str(t)]['10681']]
            measured=statistics.mean(samples)
            if measured<=0: raise ValueError('No positive observed transit proxy')
            actual=e.component(data,model,start)
            row={'seed':seed,'start_s':start,'speed_proxy_kmh':measured,
                'initial_stock':len(data.port_cohorts[str(start)]['10681']),
                'actual_merge':actual['merges']['RM_C10681'],
                'actual_final_stock':len(data.port_cohorts[str(start+450)]['10681'])}
            for mode in ['history_forecast','conditioned_diagnostic']:
                for variant in ['baseline','observed_transit']:
                    p=copy.deepcopy(profile)
                    if variant=='observed_transit':p['travel_speed_kmh']['10681']=measured
                    w=e.window(data,model,start,mode,p,lambda t: ({},{}))
                    pred=e.simulate(model,w,params)
                    r=next(x for x in pred['ramps'] if x['ramp']=='RM_C10681' and x['end_sec']==start+450)
                    row[mode+'_'+variant]={'merge':r['end']['cumulative_merge_veh'],
                        'stock':r['end']['connector_veh'],'first30merge':sum(x['accepted_merge_veh'] for x in pred['ramps'] if x['ramp']=='RM_C10681' and x['end_sec']<=start+30)}
            results.append(row)
        print('Completed seed',seed,flush=True)
    summary={}
    for seed in [13,23]:
        selected=[r for r in results if r['seed']==seed]
        summary[seed]={key:{'merge_mae':statistics.mean(abs(r[key]['merge']-r['actual_merge']) for r in selected),
            'stock_mae':statistics.mean(abs(r[key]['stock']-r['actual_final_stock']) for r in selected)}
            for key in ['history_forecast_baseline','history_forecast_observed_transit','conditioned_diagnostic_baseline','conditioned_diagnostic_observed_transit']}
    e.save(out/'results.json',results);e.save(out/'summary.json',summary)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
