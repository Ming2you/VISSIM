"""Cached motion and finite through-headway evidence; no capacity fit or FZP read."""
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.physical_ramp_boundary import gap_acceptance_supply_vph

HERE=Path(__file__).resolve().parent
R=HERE.parents[1]
PINS={}


def read(path):
    data=path.read_bytes();PINS[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(data)


def main():
    motion=R/'ramp_motion187'
    verification=read(motion/'completion.json')
    assert hashlib.sha256((motion/'verification.json').read_bytes()).hexdigest()==verification['verification_sha256']
    original=read(motion/'summary.json')
    trips=read(motion/'trips.json')
    groups=defaultdict(list)
    for trip in trips['complete_interval_censored']:
        if trip['connector']=='10681':
            groups[(trip['case'],trip['arm'],trip['head']['after'][2])].append(trip)
    travel=[]
    for (case,arm,lane),rows in sorted(groups.items()):
        travel.append(dict(case=case,arm=arm,head_lane=lane,complete_trips=len(rows),
            mean_travel_lower_sec=statistics.mean(r['travel_lower'] for r in rows),
            mean_travel_upper_sec=statistics.mean(r['travel_upper'] for r in rows),
            definitely_at_least60sec=sum(r['travel_lower']>=60 for r in rows),
            lane_changes_between_head_bracket=sum(r['head']['before'][2]!=r['head']['after'][2] for r in rows)))
    for row in original['rows']:
        if row['connector']=='10681':
            assert sum(v['complete_trips'] for v in travel if v['case']==row['case'] and v['arm']==row['arm'])==row['paired_trips']
    headways=[]
    for arm,folder in [('hold',Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47')),
                       ('selected',Path('D:/VISSIM_runs/20261002_sc1001_corrected2700_s47/selected/decisions_sdmpc31_g_2700_selected_s47'))]:
        for end in (2700,2850,3000,3150):
            raw=read(folder/f'state_{end:06d}.json'); b=oc.load_bundle(raw)
            detectors,_=oc.read_detector_csv(b.obs['detector_config']['path'],b.obs['detector_config']['sha256'])
            assigned=oc.assign_window(b.obs,b.mer_rows)
            for d in detectors:
                if d.boundary_ref!='through:10682' or d.lane>2:continue
                assert assigned.tails[d.dcp_no]==0
                times=sorted(r.t_entry for r in assigned.entries[d.dcp_no])
                assert len(times)==b.obs['detectors'][str(d.dcm_no)]
                intervals=[n-p for p,n in zip(times,times[1:])]
                assert all(h>0 for h in intervals)
                span=sum(intervals); q=len(intervals)*3600/span
                slots=sum(max(0,math.floor((h-3.5)/1.5+1e-9)+1) for h in intervals)
                headways.append(dict(arm=arm,end_sec=end,lane=d.lane,detector_pos_m=d.pos,
                    interval_count=len(intervals),finite_sample_span_sec=span,
                    window_native_count=len(times),interior_gap_flow_vph=q,
                    headway_cv=statistics.pstdev(intervals)/statistics.mean(intervals),
                    illustrative_slots=slots,empirical_slots_vph=slots*3600/span,
                    poisson_expected_slots_vph=gap_acceptance_supply_vph(q,3.5,1.5),
                    intervals_sec=intervals,source_is_future_diagnostic=end>2700))
    out=dict(status='COMPLETE_NATIVE_DIAGNOSTIC_NOT_CAPACITY_IDENTIFICATION',input_sha256=PINS,
        travel_by_head_lane=travel,through_headways=headways,new_native=0,FZP=0,full_forecasts=0,fit=0,
        limitations=[
            'Travel times include moving, following, stopped and merge waiting. Completed trips only;5s recording yields interval bounds, not exact times.',
            'Lane is identified at the observed post-head side of the bracket; later lane changes remain possible. Censored trips remain in original187 artifacts.',
            'Slots use exactly the existing3.5s/1.5s assumptions for discrete isolated opportunities. They are not measured ramp capacity or actual accepted merges.',
            'Headways are from147.51m upstream of the merge; lane changes and travel between locations remain unresolved.',
            'Sample span excludes left/right censored gaps. Comparing same-span rate to Poisson is a distribution diagnosis, not statistical proof of the complete gap law.',
            'Neither future native headways nor travel times were inserted into operational predictions; no common travel-time or gap coefficient fitted.'
        ])
    (HERE/'native_evidence.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(travel_groups=len(travel),headway_windows=len(headways),causal2700=[{k:v for k,v in row.items() if k!='intervals_sec'} for row in headways if row['end_sec']==2700 and row['arm']=='hold'])))


if __name__=='__main__':main()
