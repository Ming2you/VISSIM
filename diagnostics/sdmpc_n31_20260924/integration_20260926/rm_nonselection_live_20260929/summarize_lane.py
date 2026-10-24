"""Postprocess small saved lane predictions and completed obs150 windows only."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
P=BASE/'closedloop_recorded3600_lever450_RM_C10681_live29_lane_mean_v2'
R=Path('E:/VISSIM_runs/20260929_sd31_head10119_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
read=lambda p:json.loads(p.read_bytes())
pins={}
def pin(p):
    pins[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    return p
receipt=read(pin(P/'mode_comparison_receipt.json'))
assert receipt['unchanged_execution_reproduced'] and receipt['stored_sdmpc_surrogate_reproduced']
initial=read(pin(P/'lane_initial.json'))
comparison=[]
for call in receipt['calls']:
    mode,name=call['mode'],call['case']
    item=read(pin(P/mode/(name+'.json')))
    baseline=read(P/mode/'held_actual.json')
    path=P/(mode+'_'+name+'_lanes.json.gz')
    rows=json.loads(gzip.decompress(pin(path).read_bytes()))
    assert len(rows)==450
    lanes=[]
    for i in range(2):
        lane=[r['lane_receipts'][i] for r in rows]
        lanes.append(dict(lane=i+1, initial_stock=initial['lane_snapshots'][i]['connector_veh'],
            merged=sum(r['accepted_merge_veh'] for r in lane),
            head_passed=sum(r['head_service_veh'] for r in lane),
            supply_binding_seconds=sum(abs(r['accepted_merge_veh']-r['receiving_budget_veh'])<1e-8 for r in lane),
            eligibility_binding_seconds=sum(abs(r['accepted_merge_veh']-r['eligible_merge_veh'])<1e-8 for r in lane),
            end_merge_ready=lane[-1]['end']['merge_ready_veh'],
            first150_merged=sum(r['accepted_merge_veh'] for r in lane[:150]),
            first150_head_passed=sum(r['head_service_veh'] for r in lane[:150]),
            end_stock_before_final_urban_admission=lane[-1]['end']['connector_veh']))
    comparison.append(dict(mode=mode,case=name,lanes=lanes,
        delta_omega_veh_h=item['ttt_omega_veh_h']-baseline['ttt_omega_veh_h'],
        ramps=item['ramps'],omega_ttt_veh_h=item['ttt_omega_veh_h']))

def csv_physical(t):
    path=pin(R/f'action_{t:06d}.csv')
    return [{k:v for k,v in r.items() if k!='metadata'}
        for r in csv.DictReader(path.open(encoding='utf-8-sig'))]
assert csv_physical(3450)==csv_physical(3600)
topology=ET.parse(pin(BASE/'selected/network/native_seed29.inpx')).getroot()
target=topology.find("./links/link[@no='10681']")
assert target.find('toLinkEndPt').get('lane').split()[0]=='2'
assert not [r for r in topology.findall('./links/link') if
    any(r.find(x) is not None and r.find(x).get('lane').split()[0]=='10681'
        for x in ('fromLinkEndPt','toLinkEndPt'))]
frames={}
for t in (3600,3750):
    d=read(pin(R/f'state_{t:06d}.json'))
    assert d['vehicle_records']['complete'] and d['sim_sec']==t
    frames[t]=d
before=sum(r['link_no']==10681 for r in frames[3600]['vehicle_records']['records'])
after=sum(r['link_no']==10681 for r in frames[3750]['vehicle_records']['records'])
derived=read(pin(R/'obs150/derived_003750.json'))
# Normal closed-loop bundles use strict=False; strict additionally rejects
# unrelated unidentified10643 destination labels. Check this boundary directly.
assert derived['boundary_ambiguous']==0 and derived['lag']['ok']
arrival=derived['boundaries']['ramp_arrival:RM_C10681']
assert arrival['lane_exact'] and arrival['removed']==0
assert frames[3750]['obs150']['detectors_last_equal']
assert arrival['n_start']==arrival['n_end']==0
assert arrival['cross']==sum(frames[3750]['obs150']['detectors'][key]
                            for key in ('960276','960277'))
removed=[r for r in derived['removals']['rows'] if r['link']==10681]
assert not removed
detectors=frames[3750]['obs150']['detectors']
head=sum(detectors[key] for key in ('960217','960218'))
native=dict(start_sec=3600,end_sec=3750,initial_stock=before,arrivals=arrival['cross'],
    final_stock=after,removed=0,head_passed=head,
    merge_from_conservation=before+arrival['cross']-after,
    previous_and_applied_physical_csv_equal=True,
    merge_method='Full connector initial + normalized entry - final - abnormal removals; connector has one mainline exit and no intermediate branch',
    native_full_LDP_audit_pending=True,rm_counterfactual=False,
    observation_bundle_strict=derived['strict'],this_boundary_ambiguity=0,
    future_data_used_only_for_evaluation=True)
output=dict(schema='rm-lane-mean-diagnosis/v1',native_first150=native,
    comparisons=comparison,active_service_table=initial['ramp_config']['service_by_green_veh_h'],
    lane_exchange=initial['buffer_metadata']['lane_exchange'],lane_coupling=initial['lane_coupling'],
    source_sha256=pins,production_changed=False)
(HERE/'lane_mean_comparison.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(native=native,comparisons=[{k:v for k,v in r.items() if k not in ('ramps','lanes')} for r in comparison]),indent=2))
