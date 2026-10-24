"""Post-run paired station response; no future observations enter a forecast."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from collections import defaultdict
import csv
import statistics as stats

HERE=Path(__file__).resolve().parent
H=HERE.parent
STATIONS={2:[48.185556564965211,400.,1305.3887036831929,1500.,1651.806,
             1964.218,2307.379,2652.027,3998.666],119:[395.105],24:[165.698]}


def extract(path):
    previous={};events=[]
    with path.open('rb') as stream:
        for line in stream:
            if not line[:1].isdigit():continue
            p=line.rstrip(b'\r\n;').split(b';');t=float(p[0])
            if t<2249:continue
            if t>3000:break
            vid=int(p[1]);link=int(p[2]);lane=int(p[3]);pos=float(p[4]);speed=float(p[6])
            old=previous.get(vid)
            if old and old[1]==link and pos>old[3] and t==old[0]+1:
                for point in STATIONS.get(link,[]):
                    if old[3]<point<=pos:
                        frac=(point-old[3])/(pos-old[3]);cross=t-1+frac
                        if cross>2250:
                            events.append({'time_s':cross,'link':link,'pos_m':point,'lane':lane,
                                'vehicle':vid,'speed_kmh':old[4]+frac*(speed-old[4]),
                                'lane_changed_in_frame':int(old[2]!=lane)})
            previous[vid]=(t,link,lane,pos,speed)
    return events


def mean(xs):return stats.fmean(xs) if xs else None


def summarize(events):
    per_lane=defaultdict(list)
    for r in events:per_lane[r['link'],r['pos_m'],r['lane']].append(r)
    for rs in per_lane.values():
        rs.sort(key=lambda r:r['time_s'])
        prior=None
        for r in rs:
            # Never join across an omitted/ambiguous passage to fabricate a gap.
            r['headway_s']=(r['time_s']-prior['time_s'] if prior and
                not prior['lane_changed_in_frame'] and not r['lane_changed_in_frame'] else None)
            prior=r
    groups=defaultdict(list)
    for r in events:
        for start,end in [(2250,2400),(2400,2550),(2550,2700),(2700,2850),(2850,3000),(2400,2850)]:
            if start<r['time_s']<=end:
                for lane in [0,r['lane']]:groups[r['link'],r['pos_m'],lane,start,end].append(r)
    rows=[]
    for (link,point,lane,start,end),rs in sorted(groups.items()):
        speeds=[r['speed_kmh'] for r in rs if not r['lane_changed_in_frame']]
        gaps=[r['headway_s'] for r in rs if r['headway_s'] is not None and
              r['time_s']-r['headway_s']>start]
        rows.append({'link':link,'pos_m':point,'lane':lane,'start_s':start,'end_s':end,
            'passages':len(rs),'ambiguous_lane_passages':sum(r['lane_changed_in_frame'] for r in rs),
            'observed_flow_vph':len(rs)*3600/(end-start),
            'passage_speed_mean_kmh':mean(speeds),'passage_speed_sd_kmh':stats.pstdev(speeds) if speeds else None,
            'headway_samples':len(gaps),'headway_mean_s':mean(gaps),
            'headway_median_s':stats.median(gaps) if gaps else None,
            'headway_cv':stats.pstdev(gaps)/mean(gaps) if gaps and mean(gaps)>0 else None,
            'headway_lt_15s_fraction':mean([g<1.5 for g in gaps]),
            'headway_ge_3s_fraction':mean([g>=3 for g in gaps]),
            'headway_ge_5s_fraction':mean([g>=5 for g in gaps])})
    return rows


def paired_travel(a,b):
    records={}
    for arm,events in [('none',a),('vsl',b)]:
        by_vehicle=defaultdict(dict)
        for r in events:
            if r['link']==2:by_vehicle[r['vehicle']][r['pos_m']]=r['time_s']
        records[arm]=by_vehicle
    result=[]
    for start,end in [(400.,1305.3887036831929),(1305.3887036831929,1964.218),
                      (1964.218,2652.027),(400.,2652.027)]:
        pairs=[]
        for vid,left in records['none'].items():
            right=records['vsl'].get(vid,{})
            if start not in left or end not in left or start not in right or end not in right:continue
            # Use baseline entry time, not treatment outcome, to select the cohort.
            if not 2400<left[start]<=2700:continue
            pairs.append({'vehicle':vid,'none_s':left[end]-left[start],
                          'vsl_s':right[end]-right[start]})
        delta=[r['vsl_s']-r['none_s'] for r in pairs]
        result.append({'from_pos_m':start,'to_pos_m':end,'matched_complete_vehicles':len(pairs),
            'mean_delta_travel_s':mean(delta),'median_delta_travel_s':stats.median(delta) if delta else None,
            'pairs':pairs,'censoring':'Complete at both stations by3000 in both arms; not total TTT or all vehicles.'})
    return result


def main():
    out=HERE/'station_v1';out.mkdir(exist_ok=False)
    paths={'none':H/'rules_4500_s23_v1/run_none/vissim_eval/baseline_001.fzp',
           'vsl':HERE/'native_v2/run_retry1/vissim_eval/baseline_001.fzp'}
    events={};summaries={}
    for arm,path in paths.items():
        events[arm]=extract(path);summaries[arm]=summarize(events[arm])
        with (out/(arm+'_crossings.csv')).open('x',newline='',encoding='utf-8') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(events[arm][0]));writer.writeheader();writer.writerows(events[arm])
        e.save(out/(arm+'_summary.json'),summaries[arm])
    key=lambda r:(r['link'],r['pos_m'],r['lane'],r['start_s'],r['end_s'])
    base={key(r):r for r in summaries['none']};comparisons=[]
    for r in summaries['vsl']:
        b=base.get(key(r))
        if b:
            delta={k:r[k]-b[k] for k in r if k not in ['link','pos_m','lane','start_s','end_s']
                   and r[k] is not None and b[k] is not None}
            comparisons.append({'none':b,'vsl':r,'delta':delta})
    pre=[r for r in comparisons if r['none']['end_s']==2400]
    assert all(not any(r['delta'].values()) for r in pre),'Different pre-control station traffic'
    e.save(out/'comparisons.json',comparisons)
    e.save(out/'paired_travel.json',paired_travel(events['none'],events['vsl']))
    e.save(out/'protocol.json',{'paths':{k:str(v) for k,v in paths.items()},
        'precontrol_station_summaries_exact':True,'headways':'Interpolated passage times; exclude intervals adjacent to lane-change ambiguity',
        'limitations':'Observed headways include demand gaps. They are not saturation headways, merge gaps, or capacity estimates.',
        'window':'2250..3000s. Paired450s metrics use2400..2850.'})
    for r in comparisons:
        n=r['none']
        if n['lane']==0 and n['start_s']==2400 and n['end_s']==2850:
            print(n['link'],n['pos_m'],n['passages'],r['vsl']['passages'],r['delta']['passage_speed_mean_kmh'],flush=True)


if __name__=='__main__':main()
