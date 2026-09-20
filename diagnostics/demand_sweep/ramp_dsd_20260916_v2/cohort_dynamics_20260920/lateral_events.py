"""Native lane-entry/follower response audit and10s lateral-flow observations.

Matched stable-leader samples are descriptive controls, not randomized causal
effects. Same-link lane-ID changes exclude connector lane-number remapping.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.state_exchange_20260920.analyze_dispersion import records
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.extract_observations import Observer
from collections import defaultdict,Counter
from bisect import bisect_right
import csv
import statistics

HERE=Path(__file__).resolve().parent;H=HERE.parent


def frames(path,observer):
    frame={};last=None
    for p in records(path):
        t=int(float(p[0]))
        if t<899:continue
        if t>3000:break
        if last is not None and t!=last:
            assert t==last+1
            yield last,frame;frame={}
        last=t;link=int(p[2])
        if link not in observer.addresses or observer.addresses[link][0]!='FW_E':continue
        row=(link,int(p[3]),float(p[4]),float(p[6]))
        loc=observer.locate(row)
        if loc:frame[int(p[1])]=(*row,loc[1])
    if last is not None:yield last,frame


def leadership(frame):
    lanes=defaultdict(list)
    for vid,r in frame.items():lanes[r[0],r[1]].append((r[2],vid))
    leaders={}
    for row in lanes.values():
        row.sort()
        for a,b in zip(row,row[1:]):leaders[a[1]]=(b[1],b[0]-a[0])
    return leaders


def extract(path,geometry):
    observer=Observer(geometry);previous={};oldlead={};before={};flows=Counter();impulses=Counter()
    events=[];unmatched=0;all_events=0
    for t,frame in frames(path,observer):
        lead=leadership(frame);changed={vid for vid,r in frame.items() if vid in previous and
            r[0]==previous[vid][0] and r[1]!=previous[vid][1]}
        for vid in changed:
            r=frame[vid];old=previous[vid];step=10*((t-1)//10)
            flows[step,r[4],old[1],r[1]]+=1
        controls=defaultdict(list);exposed=[]
        for vid,(leader,gap) in lead.items():
            if vid not in previous or vid not in oldlead or leader not in previous:continue
            r=frame[vid];old=previous[vid]
            if r[:2]!=old[:2]:continue
            group=(old[4],old[1],int(old[3]//10),bisect_right([15,30,60,120],oldlead[vid][1]))
            dv=r[3]-old[3]
            if leader==oldlead[vid][0] and leader not in changed:controls[group].append(dv)
            if leader not in changed:continue
            changer=frame[leader]
            # The follower already occupied the destination lane. A lane change
            # across the cell boundary remains a real event and is labelled here.
            if previous[leader][1]==old[1] or changer[:2]!=r[:2]:continue
            all_events+=1
            prior_dv=old[3]-before[vid][3] if vid in before and before[vid][:2]==old[:2] else None
            exposed.append((group,{'time_s':t,'cell':r[4],'lane':r[1],
                'follower':vid,'changer':leader,'follower_old_speed':old[3],
                'changer_old_speed':previous[leader][3],'front_gap_m':gap,'old_front_gap_m':oldlead[vid][1],
                'dv_kmh':dv,'prior_dv_kmh':prior_dv}))
            impulses[10*((t-1)//10),r[4],r[1]]+=max(0.,old[3]-previous[leader][3])
        for key,row in exposed:
            peers=controls[key]
            row['matched_samples']=len(peers)
            row['matched_dv_kmh']=statistics.fmean(peers) if len(peers)>=3 else None
            if len(peers)<3:unmatched+=1
            events.append(row)
        before,previous,oldlead=previous,frame,lead
    counts=[{'time_s':t,'cell':c,'from_lane':a,'to_lane':b,'moves':n}
            for (t,c,a,b),n in sorted(flows.items())]
    shock=[{'time_s':t,'cell':c,'lane':lane,'closing_speed_sum_kmh':n}
           for (t,c,lane),n in sorted(impulses.items())]
    def stats(rows):
        matched=[r for r in rows if r['matched_dv_kmh'] is not None]
        return {'events':len(rows),'mean_dv_kmh':statistics.fmean(r['dv_kmh'] for r in rows) if rows else None,
            'braking_fraction':sum(r['dv_kmh']<0 for r in rows)/len(rows) if rows else None,
            'mean_prior_dv_kmh':statistics.fmean(r['prior_dv_kmh'] for r in rows if r['prior_dv_kmh'] is not None) if rows else None,
            'matched_events':len(matched),
            'matched_excess_dv_kmh':statistics.fmean(r['dv_kmh']-r['matched_dv_kmh'] for r in matched) if matched else None}
    return counts,shock,events,{'all':stats(events),'evaluation':stats([r for r in events if 2400<r['time_s']<=2850]),
        'slower_inserter':stats([r for r in events if r['changer_old_speed']<r['follower_old_speed']]),
        'not_slower_inserter':stats([r for r in events if r['changer_old_speed']>=r['follower_old_speed']]),
        'matched_scope':'Same1s frame, cell, physical lane, prior speed10km/h bin, prior front-to-front gap bin; at least3 stable-leader peers. Association only.'}


def write_csv(path,rows):
    assert rows
    with path.open('x',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    out=HERE/'lateral_v1';out.mkdir(exist_ok=False)
    cases={23:{'none':HERE/'native_v1/none_s23/run','vsl':H/'dsd_response_20260920/native_v2/run_retry1'},
           33:{'none':HERE/'native_v1/none_s33/run',
               'spread_only':H/'state_exchange_20260920/dispersion_seed33_v1/spread_only/run'}}
    results={}
    for seed,arms in cases.items():
        folder=(H/'controller_response_s23_v1/none' if seed==23 else H/'state_response_20260919/native_s33_v1/observations/none')
        geometry=e.ObservationData(folder).geometry
        for arm,run in arms.items():
            flows,shock,events,summary=extract(run/'vissim_eval/baseline_001.fzp',geometry)
            write_csv(out/f's{seed}_{arm}_flows.csv',flows)
            write_csv(out/f's{seed}_{arm}_shock.csv',shock)
            write_csv(out/f's{seed}_{arm}_events.csv',events)
            results[f'{seed}_{arm}']=summary;print(seed,arm,summary['evaluation'],flush=True)
    e.save(out/'summary.json',results)


if __name__=='__main__':main()
