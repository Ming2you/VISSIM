"""Post-prediction ID audit of the existing1200-1350 MER; no FZP or fitting."""
from collections import Counter
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from evaluation.controllers.obs150_contract import MerRow,assign_window


def main():
    future_mode='--future' in sys.argv[1:]
    run=Path('D:/VISSIM_runs/20260924_sd31_gain/sdmpc31_g_gain_s29_r3/decisions_sdmpc31_g_gain_s29_r3')
    initial=HERE/'selected_init1200_final/state_001200.json'
    future=run/'state_001350.json'
    mer=run/'obs150/mer_001350.jsonl'
    derived_path=run/'obs150/derived_001350.json'
    table=HERE/'selected/obs150/obs150_detectors_v2.csv'
    start=json.loads(initial.read_bytes());end=json.loads(future.read_bytes())
    derived=json.loads(derived_path.read_bytes())
    assignment=assign_window(end['obs150'],[MerRow(*json.loads(line)) for line in mer.read_text().splitlines()])
    assert assignment.start_s==1200 and assignment.end_s==1350
    records={r['veh_no']:r for r in start['vehicle_records']['records']}
    ending={r['veh_no']:r for r in end['vehicle_records']['records']}
    with table.open(encoding='utf-8-sig',newline='') as f:detectors=list(csv.DictReader(f))
    results={}
    for link in (10482,10490):
        key='ramp_arrival:RM_C'+str(link)
        rows=[r for r in detectors if r['boundary_ref']==key]
        assert rows and all(r['orientation']=='down' and float(r['pos'])==1. for r in rows)
        dcps=[int(r['dcp_no']) for r in rows]
        assert all(assignment.tails[dcp]==0 for dcp in dcps)
        crossings=[r for dcp in dcps for r in assignment.entries[dcp]]
        assert len({r.veh for r in crossings})==len(crossings)
        ids={r.veh for r in crossings}
        # The1m detector is downstream of actual ramp entry. Correct its tiny
        # stock with the same native ID identity used by obs150.
        near=lambda data:{i for i,r in data.items() if r['link_no']==link and 0.<=r['position_m']<1.}
        before,after=near(records),near(ending)
        assert not (after & ids)
        arrivals=(ids|after)-before
        actual=derived['boundaries'][key]['cross']
        assert len(arrivals)==len(crossings)+len(after)-len(before)==actual
        groups=Counter(str(records[i]['link_no']) if i in records else 'absent_initial_network' for i in arrivals)
        results[str(link)]=dict(actual_entry_veh=actual,detector_veh=len(crossings),
            station_initial_ids=sorted(before),station_final_ids=sorted(after),
            by_initial_link=dict(groups),entry_vehicle_ids=sorted(arrivals),
            detector_times={str(r.veh):r.t_entry for r in crossings if r.veh in arrivals})
    comparisons={}
    traces={}
    folders=[
        ('before','recorded_ramp_canonical_prior1200_travel_north_authority_pool4_head10633_history_trace'),
        ('initial_routes','gate_initial1200_trace')]
    if future_mode:folders.extend([('future_geometry','gate_future1200_trace'),('future_geometry_lanes','gate_future_lanes1200_trace')])
    for label,directory in folders:
        folder=HERE/directory
        summary=json.loads((folder/'summary.json').read_bytes())
        with gzip.open(folder/'trace.json.gz','rt',encoding='utf-8') as f:trace=json.load(f)
        traces[label]=trace
        transfers=trace['response']['transfers'];queues={}
        for suffix in ('onW','onE'):
            target='movement:SC1001_W_to_'+suffix
            by_source=Counter()
            for t in transfers:
                if t['target']==target:by_source[t['source']]+=t['vehicles']
            queues[suffix]=dict(by_source)
        comparisons[label]=dict(ramps={k:summary['ramps'][k] for k in ('RM_C10482','RM_C10490')},
                               arrivals_to_pre_ramp_queue=queues,
                               gate_future_accounting=trace.get('gate_future_final_accounting'))
    default_path=HERE/'gate_default1200_trace/trace.json.gz'
    with gzip.open(default_path,'rt',encoding='utf-8') as f:default=json.load(f)
    assert default==traces['before'], 'Disabled gate change altered a historical response'
    response=traces['initial_routes']['response']
    # First1s residence is after the first accepted generation. No gate
    # departures occur then. Its stock must equal that input, proving zero
    # pre-existing gate buffer without treating it as an initial approach.
    gate='transit:gate:in_SC1001_W'
    incoming=[t for t in response['transfers'] if t['target']==gate]
    first_stock=response['residence'][0]['model_stock_veh'][gate]
    assert incoming[0]['source'] is None and abs(first_stock-incoming[0]['vehicles'])<1e-9
    result=dict(window=[1200,1350],actual=results,predictions=comparisons,
        disabled_full_trace_exact=True,initial_gate_transit_stock_veh=0.,
        future_observation_use='Validation targets only, after both predictions were completed',
        queue_vs_entry_warning='Model queue arrivals are upstream of entry service; not the same boundary as actual ramp entries',
        source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (initial,future,mer,derived_path,table)},
        gain_qualified=False)
    if future_mode:
        proof=json.loads((HERE/'gate_future_lanes1200_trace/runtime.json').read_bytes())
        cohorts=proof['gate_initial_route_evidence'];initial_errors={}
        for link,family in (('10482','1'),('10490','3')):
            actual=set(results[link]['entry_vehicle_ids'])
            selected=[r for r in cohorts if r['vehicle'] is not None and r['route_family']==family and r['vehicles']==1.]
            ids={r['vehicle'] for r in selected}
            late=[{**r,'observed_detector_sec':results[link]['detector_times'][str(r['vehicle'])]}
                  for r in selected if r['vehicle'] in actual and r['due_sec']>1350]
            early=[r for r in selected if r['due_sec']<=1350 and r['vehicle'] not in actual]
            initial_errors[link]=dict(actual_committed_current_ids=len(ids&actual),
                predicted_late_but_observed_arrived=late,predicted_arrival_but_not_observed=early,
                outside_current_gate_owner_actual_ids=sorted(actual-ids),
                timing_caveat='Predicted queue-ready vs native1m detector entry; service can delay entry, not make it precede readiness')
        result['initial_cohort_timing']=initial_errors
        result['future_geometry']=proof['gate_future_travel']
        result['entry_capacities_veh_h']=proof['gate_entry_capacity_veh_h']
    filename='gate_future_audit1200.json' if future_mode else 'gate_arrival_cohorts1200.json'
    (HERE/filename).write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({k:{n:v for n,v in r.items() if n!='entry_vehicle_ids'} for k,r in results.items()}))


if __name__=='__main__':main()
