"""Check initial branch labels against current physical location, not future routes."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from collections import Counter

HERE=Path(__file__).resolve().parent


def main():
    bank=HERE/'fresh_s43_v1';data=e.ObservationData(bank/'observations/none')
    freeze=e.load(bank/'model_freeze.json')
    model=e.load_base_model(data.geometry,e.ROOT/freeze['models']['port_travel']/'config.json')
    profile=e.load(e.ROOT/freeze['port_profile']);positions=e.load(bank/'predictions/initial_vehicle_locations.json')
    lane=e.load(bank/'predictions/initial_lane_states.json');rows=[]
    for cutoff,vehicles in positions.items():
        t=int(cutoff);window=e.window(data,model,t,'history_forecast',profile,lambda _: ({},{}))
        beta=window['boundary_steps'][0]['off_split_ratio']
        for off,spec in model.offramps.items():
            if spec['road']!='FW_E':continue
            cell=spec['from_cell'];point=data.geometry['bounds']['FW_E'][cell]+1000*model.lane_port_travel['FW_E']['off_distance_km'][off]
            counts=Counter();before=Counter()
            for v in vehicles.values():
                if v['cell']!=cell:continue
                counts[v['group']]+=1
                offset=data.geometry['addresses'][str(v['link'])][1]
                if offset+v['position_m']<=point:before[v['group']]+=1
            origins=sum(sum(ns) for ramp,ns in lane[cutoff]['initial_ramp_origin'].items() if model.ramps[ramp]['to_cell']==cell)
            row={'cutoff_s':t,'off':off,'cell':cell,'branch_ratio':beta[off],
                 'cell_veh':sum(counts.values()),'same_cell_ramp_origin_veh':origins,
                 'before_exit_veh':sum(before.values()),
                 'initial_off_labels_in_current_candidate':(sum(counts.values())-origins)*beta[off],
                 'before_exit_by_group':dict(before),'cell_by_group':dict(counts)}
            rows.append(row);print(row,flush=True)
    known=set(positions['2400']);exits={}
    for arm in ['none','rm_ramp','vsl','both']:
        exit_by_id={}
        for r in e.rows(bank/'observations'/arm/'port_events.csv'):
            if (r['kind']=='arrival' and r['connector'] in model.offramps and
                    model.offramps[r['connector']]['road']=='FW_E' and r['vehicle'] in known and float(r['time_s'])>2400):
                exit_by_id.setdefault(r['vehicle'],[]).append((float(r['time_s']),r['connector']))
        exits[arm]={vid:min(xs)[1] for vid,xs in exit_by_id.items()}
    contrasts={}
    for arm in ['rm_ramp','vsl','both']:
        a,b=exits['none'],exits[arm];common=a.keys()&b.keys()
        contrasts[arm]={'matched_initial_vehicles_with_observed_exit_in_both':len(common),
            'different_first_exit':[{'vehicle':v,'none':a[v],'control':b[v]} for v in common if a[v]!=b[v]],
            'only_none_observed':len(a.keys()-b.keys()),'only_control_observed':len(b.keys()-a.keys()),
            'right_censoring':'Missing exit by3000 is unknown destination, not a reroute'}
    e.save(HERE/'position_audit_v1.json',{'initial_position_checks':rows,'matched_route_observations':contrasts,
        'causality':'Initial eligibility uses only cutoff position. Later actual exit comparison is diagnostic, never model input.'})
    print(contrasts,flush=True)


if __name__=='__main__':main()
