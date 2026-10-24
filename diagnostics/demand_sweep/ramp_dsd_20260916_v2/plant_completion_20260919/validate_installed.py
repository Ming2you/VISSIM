"""Validate installed model against frozen native records and archived forecasts."""
import json
from pathlib import Path
import statistics
import sys

HERE=Path(__file__).resolve().parent
H=HERE.parent
sys.path.insert(0,str(H.parents[2]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e

def main():
    out=HERE/'installed_v2';out.mkdir(exist_ok=False)
    base=H/'controller_response_4500_v1/model_v4'
    modified=H/'controller_response_4500_v1/model_v5_node'
    params=e.load(base/'selected_parameters.json')['parameters']
    profile=e.load(base/'port_profile.json')
    archived=e.load(H/'response_late_s23_v1/transit_history_validation_v1/results.json')
    hypothesis=e.load(HERE/'node_v2/results.json')
    results=[]
    for seed,folder in [(13,'controller_response_4500_v1/none'),(23,'controller_response_s23_v1/none')]:
        data=e.ObservationData(H/folder)
        models={k:e.load_base_model(data.geometry,p/'config.json') for k,p in [('previous',base),('node',modified)]}
        for ref in [r for r in archived if r['seed']==seed]:
            start=ref['start_s'];actual=e.component(data,models['previous'],start)
            row={'seed':seed,'start_s':start,'actual':actual,'actual_final_stock':ref['actual_final_stock']}
            hyp=next(r for r in hypothesis if r['seed']==seed and r['start_s']==start)
            for mode in ['history_forecast','conditioned_diagnostic']:
                row[mode]={}
                for name,model in models.items():
                    w=e.window(data,model,start,mode,profile,lambda t: ({},{}))
                    p=e.simulate(model,w,params)
                    metrics=e.component(data,model,start,p)
                    end=next(r['end'] for r in p['ramps'] if r['ramp']=='RM_C10681' and r['end_sec']==start+450)
                    metrics['final_stock10681']=end['connector_veh']
                    metrics['first30merge']=sum(r['accepted_merge_veh'] for r in p['ramps'] if r['ramp']=='RM_C10681' and r['end_sec']<=start+30)
                    metrics['mass_checks']=p['local_ramp_audit']['checks']
                    row[mode][name]=metrics
                    ref_values=ref[mode+'_baseline'] if name=='previous' else hyp[mode]
                    for k,v in [('merge',metrics['merges']['RM_C10681']),('stock',metrics['final_stock10681']),('first30merge',metrics['first30merge'])]:
                        if v != ref_values[k]:raise AssertionError((seed,start,mode,name,k,v,ref_values[k]))
                    if name=='node':
                        # The installed class must expose residence to both public
                        # diagnostics and interval receipts (old probe did not).
                        total=sum(r['connector_ttt_veh_h'] for r in p['ramps'])
                        actual_integral=sum(r['ramp_connector_residence_local_1s_veh_h'] for r in p['diagnostics']['roads'])
                        if abs(total-actual_integral)>1e-8:raise AssertionError(('residence',total,actual_integral))
            results.append(row)
        print('Validated seed',seed,flush=True)
    e.save(out/'results.json',results)
    summary={str(seed):{mode:{name:{
        'merge10681_mae':statistics.mean(abs(r[mode][name]['merges']['RM_C10681']-r['actual']['merges']['RM_C10681']) for r in results if r['seed']==seed),
        'stock10681_mae':statistics.mean(abs(r[mode][name]['final_stock10681']-r['actual_final_stock']) for r in results if r['seed']==seed),
        'component_ttt_mae':statistics.mean(abs(r[mode][name]['component_ttt_veh_h']-r['actual']['component_ttt_veh_h']) for r in results if r['seed']==seed)
        } for name in models} for mode in ['history_forecast','conditioned_diagnostic']} for seed in [13,23]}
    e.save(out/'summary.json',{'scores':summary,'default_scalar_replay_exact':True,'node_scalar_probe_replay_exact':True,
        'forecasts':96,'development_data_not_fresh_holdout':True})
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
