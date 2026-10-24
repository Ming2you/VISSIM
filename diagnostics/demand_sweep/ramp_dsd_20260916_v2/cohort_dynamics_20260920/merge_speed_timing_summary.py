"""Saved native merge-event speed/headway exposure, not a causal fit."""
from pathlib import Path
from collections import defaultdict
import csv
import hashlib
import json
import statistics

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
H=HERE.parent


def rows(p):
    with p.open(encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def stats(values):
    return dict(n=len(values),mean=statistics.mean(values),sd=statistics.pstdev(values),
                minimum=min(values),maximum=max(values)) if values else dict(n=0)


def summarize(folder,start,end):
    ports=folder/'port_events.csv';heads=folder/'head_crossings.csv'
    events=rows(ports);head_events=rows(heads)
    head_by_vehicle=defaultdict(list)
    for r in head_events:
        head_by_vehicle[int(r['vehicle']),int(r['ramp'])].append(int(float(r['time_s'])))
    summaries=[]
    for lo in range(start,end,150):
        for conn in (10490,10484):
            use=[r for r in events if r['kind']=='departure' and int(r['connector'])==conn and lo<float(r['time_s'])<=lo+150]
            times=sorted(float(r['time_s']) for r in use)
            speed=[float(r['speed_kmh']) for r in use]
            travel=[]
            for r in use:
                candidates=[t for t in head_by_vehicle[int(r['vehicle']),conn] if t<=float(r['time_s'])]
                assert candidates
                travel.append(float(r['time_s'])-max(candidates))
            summaries.append(dict(start_s=lo,end_s=lo+150,connector=conn,merges=len(use),
                premerge_speed_kmh=stats(speed),between_merge_spacing_s=stats([b-a for a,b in zip(times,times[1:])]),
                head_to_merge_time_s=stats(travel)))
    return summaries,[ports,heads]


def main():
    out=HERE/'merge_speed_timing_v1';out.mkdir(exist_ok=False)
    cases={'start2400':(2400,2850,{
        'none':H/'controller_response_s23_v1/none',
        **{a:H/'response_late_s23_v1/observations'/a for a in ('rm_ramp','vsl','both')}}),
        'start2550':(2550,3000,{a:H/'response_late_s23_v1/observations'/a for a in ('rm8','rm_ramp')})}
    result={};files=[Path(__file__),ROOT/'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/extract_observations.py']
    for label,(start,end,folders) in cases.items():
        result[label]={}
        for arm,path in folders.items():
            result[label][arm],inputs=summarize(path,start,end)
            files.extend(inputs)
    pins={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    doc=dict(status='OBSERVED_MERGE_EXPOSURE_NOT_CALIBRATION',qualified=False,results=result,source_pins=pins,
        speed_definition='Last recorded connector speed at departure_time-1s, not downstream speed or desired-speed setting.',
        matching='Within-run head event matched by vehicle and connector. Between-run newly generated vehicle IDs are not paired.',
        causal_limit='Arm speed distributions contain different vehicle/time selections. Means alone do not identify insertion-speed causal effects.',
        new_native_runs=0,production_changes=0)
    (out/'result.json').write_text(json.dumps(doc,indent=2),encoding='utf-8')
    for case,arms in result.items():
        for arm,values in arms.items():
            print(case,arm,[(r['start_s'],r['connector'],r['merges'],round(r['premerge_speed_kmh']['mean'],2),round(r['head_to_merge_time_s']['mean'],2)) for r in values])


if __name__=='__main__':
    main()
