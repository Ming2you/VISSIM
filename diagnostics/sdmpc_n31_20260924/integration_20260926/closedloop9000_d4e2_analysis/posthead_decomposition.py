"""Saved-budget ramp replay and native cohort audit; no new plant/native run."""
import gzip
import json
import math
import sys
import statistics as stats
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from evaluation.controllers.lane_plant_runtime import load_sources
from evaluation.controllers.physical_ramp_boundary import LaneResolvedRampBoundary,gap_acceptance_supply_vph
from diagnostics.sdmpc_n31_20260924.integration_20260926.closedloop9000_d4e2_analysis.audit_stopped_predictions import RECORDS

HERE=Path(__file__).resolve().parent
STUDY=HERE.parent
load=lambda p:json.loads(p.read_bytes())
ctx=load_sources(STUDY/'heldout53_response_v2/candidate_manifest.json')
ramp='RM_C10681';r=ctx['component'].ramps[ramp]
tree=ET.fromstring(ctx['paths']['network'].read_bytes())
head=min(float(h.get('pos')) for h in tree.findall('./signalHeads/signalHead') if h.get('lane').split()[0]=='10681')
speed=ctx['port_profile']['travel_speed_kmh']['10681']
events=load(HERE/'stopped_native_lane_audit.json')
with gzip.open(HERE/'stopped_native_windows.json.gz','rt',encoding='utf-8') as f:cache=json.load(f)
results={}
candidate='--candidate' in sys.argv[1:]
wave_only='--wave-only' in sys.argv[1:]
wave=None
node=ctx['component'].ramp_receiving_nodes[ramp]
if candidate or wave_only:
    # Exactly one closed training window; freeze before validating 6000.
    training=load(HERE/'stopped_posthead_audit.json')['results']['4500']['lanes']['2']
    length_km=(r['length_m']-head)/1000
    capacity=(r['length_m']-head)/ctx['component'].base.network.urban_avg_vehicle_length_m
    wave=training['native_head_veh']*24*length_km/(capacity-training['native_post_stock_mean'])
for start in (4500,6000):
    current=[v for v in load(RECORDS/f'state_{start:06d}.json')['vehicle_records']['records'] if v['link_no']==10681]
    past=load(RECORDS/f'obs150/derived_{start:06d}.json')
    with gzip.open(STUDY/f'closedloop_recorded{start}_trace_stop150/trace.json.gz','rt',encoding='utf-8') as f:response=json.load(f)['response']
    arrivals=defaultdict(float)
    for z in response['transfers']:
        if z['target']=='ramp:'+ramp:arrivals[z['start_sec']]+=z['vehicles']
    budgets={z['start_sec']:z for z in response['resource_allocations']
             if z['kind']=='physical_ramp_merge_physical_receiving' and z['resource']==ramp}
    service={z['start_sec']:z for z in response['resource_allocations']
             if z['kind']=='physical_ramp_head_service' and z['resource']==ramp+':0'}
    conflicts={}
    for sec,z in budgets.items():
        target=z['available_veh']*3600/r['lanes'];lo,hi=0.,20000.
        for _ in range(60):
            mid=(lo+hi)/2
            if gap_acceptance_supply_vph(mid,node['critical_gap_sec'],node['followup_sec'])>target:lo=mid
            else:hi=mid
        conflicts[sec]=(lo+hi)/2
    raw=load(RECORDS/f'state_{start:06d}.json')
    # Four exact native stations at physical31-cell11's downstream boundary.
    counts=[raw['obs150']['detectors'][str(d)] for d in range(960256,960260)]
    factors=[n*24/conflicts[start] for n in counts[:2]]
    buffer=LaneResolvedRampBoundary(connector_id='10681',length_m=r['length_m'],head_position_m=head,
        lanes=r['lanes'],spacing_m=ctx['component'].base.network.urban_avg_vehicle_length_m,
        travel_speed_kmh=speed,time_sec=start,initial_backlog_veh=0.,
        initial_cohorts=[[v['position_m'],v['speed_kph'],v['lane_no']] for v in current],
        lane_arrival_shares=past['ramp_arrival_shares'][ramp],posthead_wave_speed_kmh=wave)
    predictions=[]
    for sec in range(start,start+150):
        budget=budgets[sec]['available_veh'];extra={}
        if candidate:
            canonical=next(z['available_veh'] for z in response['resource_allocations']
                if z['kind']=='physical_ramp_merge_canonical_receiving' and z['resource']==ramp and z['start_sec']==sec)
            lanes=[min(canonical/2,gap_acceptance_supply_vph(conflicts[sec]*f,node['critical_gap_sec'],node['followup_sec'])/3600) for f in factors]
            budget=sum(lanes);extra={'receiving_budget_by_lane_veh':lanes}
        row=buffer.advance_local_interval(start_sec=sec,duration_sec=1.,cycle_sec=10.,
            receiving_budget_veh=budget,service_veh=service[sec]['available_veh']*10*r['lanes'],
            mode='GREEN',green_sec=10.,request_arrivals_veh=0.,allow_partial_cycle=True,**extra)
        if not (candidate or wave_only):
            assert abs(row['accepted_merge_veh']-budgets[sec]['accepted_total_veh'])<1e-7,(sec,row['accepted_merge_veh'],budgets[sec]['accepted_total_veh'])
        buffer.admit_current(arrivals[sec])
        predictions.append(dict(start_sec=sec,end_sec=sec+1,lanes=row['lane_receipts'],end=buffer.snapshot()))
    ev=events['results'][str(start)]['events'];heads={v['vehicle']:v for v in ev['head_crossings']};merges={v['vehicle']:v for v in ev['merges']}
    observations=[]
    for stamp,rows in cache['frames'].items():
        t=float(stamp)
        if not start<t<start+150:continue
        for lane in (1,2):
            vs=[v for v in rows if v[1]==10681 and v[2]==lane];post=[v for v in vs if v[3]>=head]
            observations.append(dict(time_sec=t,lane=lane,pre_veh=len(vs)-len(post),post_veh=len(post),
                stopped_post_veh=sum(v[4]<1 for v in post),mean_post_speed_kph=stats.mean(v[4] for v in post) if post else None))
    summaries={}
    for lane in (1,2):
        complete=[];initial=[]
        for vid,z in merges.items():
            if z['last_ramp_lane']!=lane:continue
            if vid in heads:
                h=heads[vid];complete.append(dict(vehicle=vid,head_lane=h['to_lane'],merge_lane=lane,
                    min_sec=z['lower_sec']-h['upper_sec'],max_sec=z['upper_sec']-h['lower_sec']))
            else:
                v,=[v for v in current if v['veh_no']==vid and v['position_m']>=head]
                initial.append(dict(vehicle=vid,position_m=v['position_m'],speed_kph=v['speed_kph'],
                    native_merge_min_sec=z['lower_sec']-start,native_merge_max_sec=z['upper_sec']-start,
                    model_free_travel_sec=(r['length_m']-v['position_m'])*3.6/speed))
        pr=[v['lanes'][lane-1] for v in predictions];obs=[v for v in observations if v['lane']==lane]
        summaries[str(lane)]=dict(native_completed_cohorts=complete,native_initial_posthead=initial,
            native_head_to_merge_median_interval_sec=[stats.median(x[k] for x in complete) for k in ('min_sec','max_sec')],
            native_post_stock_mean=stats.mean(x['post_veh'] for x in obs),
            native_stopped_post_mean=stats.mean(x['stopped_post_veh'] for x in obs),
            predicted_post_stock_mean=stats.mean(x['end']['downstream_travelling_veh']+x['end']['merge_ready_veh'] for x in pr),
            predicted_moving_post_stock_mean=stats.mean(x['end']['downstream_travelling_veh'] for x in pr),
            predicted_merge_ready_mean=stats.mean(x['end']['merge_ready_veh'] for x in pr),
            predicted_head_veh=sum(x['head_service_veh'] for x in pr),predicted_merge_veh=sum(x['accepted_merge_veh'] for x in pr),
            native_head_veh=sum(x['to_lane']==lane for x in heads.values()),native_merge_veh=sum(x['last_ramp_lane']==lane for x in merges.values()),
            capacity_limited_seconds=sum(x['eligible_merge_veh']>x['receiving_budget_veh']+1e-7 for x in pr),
            predicted_unspent_receiving_veh=sum(x['unused_receiving_budget_veh'] for x in pr))
    results[str(start)]=dict(lanes=summaries,predicted=predictions,native=observations,
        replay_exact_within_1e7=not(candidate or wave_only),initial_cohorts=current,arrival_shares=buffer.lane_arrival_shares,
        prior_native_counts=counts,conflict_factors=factors,conflict_reference_vph=conflicts[start])
out=HERE/('stopped_posthead_candidate.json' if candidate else 'stopped_posthead_wave_only.json' if wave_only else 'stopped_posthead_audit.json');assert not out.exists()
out.write_text(json.dumps(dict(results=results,free_travel_time_sec=(r['length_m']-head)*3.6/speed,
    wave_speed_kmh=wave,training_window=[4500,4650] if wave else None,
    travel_speed_kph=speed,head_position_m=head,length_m=r['length_m'],
    limitations=['Saved receiving/head budget replay is decomposition, not a new coupled forecast.',
        'Native travel durations include merge waiting; not another pure delay to add.',
        '5s event brackets and completed-cohort censoring; mean native stock uses sampled frames.']),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({t:{lane:{k:v for k,v in row.items() if k not in ('native_completed_cohorts','native_initial_posthead')}
                    for lane,row in result['lanes'].items()} for t,result in results.items()}))
