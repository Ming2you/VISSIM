"""Matched-state response gate for the receiving-node hypothesis."""
import copy
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
H=HERE.parent
sys.path.insert(0,str(H.parents[2]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.response_late_s23_v1.lane_boundary_candidate import LaneResolvedRampBoundary
import canonical_harness as ch

def main():
    out=HERE/'response_v1';out.mkdir(exist_ok=False)
    modeldir=H/'controller_response_4500_v1/model_v4'
    params=e.load(modeldir/'selected_parameters.json')['parameters']
    profile=e.load(modeldir/'port_profile.json')
    fit=e.load(HERE/'gap_fit.json')['fit'];tc,tf=fit['critical_sec'],fit['followup_sec']
    audit=e.load(H/'response_late_s23_v1/model_mechanism_audit.json')
    distributions=next(v for v in audit.values() if isinstance(v,dict) and '120' in v)
    ratios={int(k):v['mean_kmh']/distributions['120']['mean_kmh'] for k,v in distributions.items()}
    results={}
    for name,bank,folder in [('early13',H/'response_pairs_v1',H/'controller_response_4500_v1/none'),
                             ('late23',H/'response_late_s23_v1',H/'controller_response_s23_v1/none')]:
        protocol=e.load(bank/'protocol.json');start=protocol['start_s']
        data=e.ObservationData(folder);model=e.load_base_model(data.geometry,modeldir/'config.json')
        arrivals=[x for x in e.rows(folder/'port_events.csv') if x['connector']=='10681' and x['kind']=='arrival' and start-150<float(x['time_s'])<=start]
        shares=[sum(int(x['lane'])==i for x in arrivals)/len(arrivals) for i in [1,2]]
        results[name]={}
        for variant in ['node','node_dsd']:
            results[name][variant]={}
            for arm in ['none','rm_ramp','vsl','both']:
                sequence=protocol['candidate_bank'].get(arm,{'green':[],'vsl':[]})
                def command(t):
                    i=int((t-start)//150)
                    return ({protocol.get('meter_id','RM_C10490'):sequence['green'][i]} if sequence['green'] else {},
                            {d:sequence['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if sequence['vsl'] else {})
                w=e.window(data,model,start,'history_forecast',copy.deepcopy(profile),command)
                w['ramp_dynamics']['ramps']['RM_C10681']['lane_arrival_shares']=shares
                original_buffer=ch.PhysicalRampBoundary
                original_release=ch.accounting._mn.compute_ramp_release_flows
                original_desired=ch.accounting._mn.effective_desired_speed_kmh
                def buffer(**kwargs):
                    return LaneResolvedRampBoundary(**kwargs) if 'lane_arrival_shares' in kwargs else original_buffer(**kwargs)
                def release(state,control,demand,cfg,include_current_arrivals=True):
                    selected,diag=original_release(state,control,demand,cfg,include_current_arrivals)
                    mid='RM_C10681'
                    if mid in selected:
                        road=cfg.network.ramp_to_freeway[mid];i=cfg.network.ramp_merge_segment_index[mid]
                        q=state.freeway_density[road][i-1]*state.freeway_speed[road][i-1]
                        split=sum(cfg.network.off_ramp_split_ratio[o] for o in cfg.network.off_ramps if cfg.network.off_ramp_segment_index[o]==i-1)
                        q*=max(0.,1.-split)
                        gap=q*math.exp(-q*tc/3600)/(-math.expm1(-q*tf/3600)) if q>0 else 3600/tf
                        selected[mid]=min(selected[mid],2*gap)
                    return selected,diag
                def desired(*args):
                    if args[5]:
                        uncapped=list(args);uncapped[5]=False
                        return original_desired(*uncapped)*ratios[int(args[3])]
                    return original_desired(*args)
                ch.PhysicalRampBoundary=buffer;ch.accounting._mn.compute_ramp_release_flows=release
                if variant=='node_dsd':ch.accounting._mn.effective_desired_speed_kmh=desired
                try:pred=e.simulate(model,w,params)
                finally:
                    ch.PhysicalRampBoundary=original_buffer
                    ch.accounting._mn.compute_ramp_release_flows=original_release
                    ch.accounting._mn.effective_desired_speed_kmh=original_desired
                metrics=e.component(data,model,start,pred)
                results[name][variant][arm]=metrics
                e.save(out/f'{name}_{variant}_{arm}.json',pred)
            base=results[name][variant]['none']['component_ttt_veh_h']
            print(name,variant,{a:round(m['component_ttt_veh_h']-base,4) for a,m in results[name][variant].items()},flush=True)
    e.save(out/'results.json',results)

if __name__=='__main__':main()
