"""One bounded receiving-node hypothesis on completed records."""
import argparse
import copy
import json
import math
from pathlib import Path
import statistics
import sys

HERE=Path(__file__).resolve().parent
H=HERE.parent
ROOT=H.parents[2]
sys.path.insert(0,str(ROOT))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.response_late_s23_v1.lane_boundary_candidate import LaneResolvedRampBoundary
import canonical_harness as ch


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--history-speed',action='store_true');args=parser.parse_args()
    out=HERE/('node_history_v2' if args.history_speed else 'node_v2');out.mkdir(exist_ok=False)
    modeldir=H/'controller_response_4500_v1/model_v4'
    params=e.load(modeldir/'selected_parameters.json')['parameters']
    profile=e.load(modeldir/'port_profile.json')
    fit=e.load(HERE/'gap_fit.json')['fit'];tc,tf=fit['critical_sec'],fit['followup_sec']
    results=[]
    for seed,sub in [(13,'controller_response_4500_v1/none'),(23,'controller_response_s23_v1/none')]:
        data=e.ObservationData(H/sub);model=e.load_base_model(data.geometry,modeldir/'config.json')
        events=e.rows(data.folder/'port_events.csv')
        for start in [900,1200,1500,1650,1950,2250,2400,2700,3000,3300,3600,3900]:
            actual=e.component(data,model,start)
            result={'seed':seed,'start_s':start,'actual_merge':actual['merges']['RM_C10681'],
                    'actual_final_stock':len(data.port_cohorts[str(start+450)]['10681'])}
            arrivals=[x for x in events if x['connector']=='10681' and x['kind']=='arrival' and start-150<float(x['time_s'])<=start]
            shares=[sum(int(x['lane'])==i for x in arrivals)/len(arrivals) for i in [1,2]]
            for mode in ['history_forecast','conditioned_diagnostic']:
                p=copy.deepcopy(profile)
                if args.history_speed:
                    samples=[float(row[1]) for t in range(start-120,start+1,30) for row in data.port_cohorts[str(t)]['10681']]
                    p['travel_speed_kmh']['10681']=statistics.mean(samples)
                w=e.window(data,model,start,mode,p,lambda t: ({},{}))
                w['ramp_dynamics']['ramps']['RM_C10681']['lane_arrival_shares']=shares
                original_buffer=ch.PhysicalRampBoundary;original_release=ch.accounting._mn.compute_ramp_release_flows
                audit=[]
                def buffer(**kwargs):
                    return LaneResolvedRampBoundary(**kwargs) if 'lane_arrival_shares' in kwargs else original_buffer(**kwargs)
                def release(state,control,demand,cfg,include_current_arrivals=True):
                    selected,diag=original_release(state,control,demand,cfg,include_current_arrivals)
                    mid='RM_C10681'
                    if mid in selected:
                        road=cfg.network.ramp_to_freeway[mid];i=cfg.network.ramp_merge_segment_index[mid]
                        q=state.freeway_density[road][i-1]*state.freeway_speed[road][i-1]
                        split=sum(cfg.network.off_ramp_split_ratio[o] for o in cfg.network.off_ramps
                                  if cfg.network.off_ramp_segment_index[o]==i-1)
                        q*=max(0.,1.-split)
                        gap=q*math.exp(-q*tc/3600)/(-math.expm1(-q*tf/3600)) if q>0 else 3600/tf
                        selected[mid]=min(selected[mid],2*gap)
                        audit.append({'sec':state.time_sec,'conflict_vph_per_lane':q,'ramp_budget_vph':selected[mid]})
                    return selected,diag
                ch.PhysicalRampBoundary=buffer;ch.accounting._mn.compute_ramp_release_flows=release
                try: pred=e.simulate(model,w,params)
                finally:ch.PhysicalRampBoundary=original_buffer;ch.accounting._mn.compute_ramp_release_flows=original_release
                rs=[x for x in pred['ramps'] if x['ramp']=='RM_C10681'];r=rs[-1]
                result[mode]={'merge':r['end']['cumulative_merge_veh'],'stock':r['end']['connector_veh'],
                    'first30merge':sum(x['accepted_merge_veh'] for x in rs if x['end_sec']<=start+30),
                    'ttt':e.component(data,model,start,pred),'gap_audit':audit}
                if start in [1650,2400,2700]:e.save(out/f's{seed}_{start}_{mode}.json',pred)
            results.append(result)
        print('Completed seed',seed,flush=True)
    summary={seed:{mode:{'merge_mae':statistics.mean(abs(r[mode]['merge']-r['actual_merge']) for r in results if r['seed']==seed),
        'stock_mae':statistics.mean(abs(r[mode]['stock']-r['actual_final_stock']) for r in results if r['seed']==seed)}
        for mode in ['history_forecast','conditioned_diagnostic']} for seed in [13,23]}
    e.save(out/'results.json',results);e.save(out/'summary.json',summary);print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
