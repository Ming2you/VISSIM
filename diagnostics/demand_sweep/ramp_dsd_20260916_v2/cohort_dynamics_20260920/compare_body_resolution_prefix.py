"""Compare a verified NC repeat with a closed prefix of the disk-full run."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import analyze_body_resolution as a

B,e=a.BASE,a.e


def observed_arrivals(path,cutoff):
    seen=set();road=set();origins=Counter();road_windows=Counter();last=None;closed=False
    stamp=(path.stat().st_size,path.stat().st_mtime_ns)
    for f in a.rows(path):
        t=float(f[0])
        if t>cutoff+1e-8:closed=True;break
        vid,link=int(f[1]),int(f[2]);last=t
        if vid not in seen:seen.add(vid);origins[link]+=1
        if link==24 and vid not in road:
            road.add(vid);road_windows['before900' if t<900 else '900_to_cutoff']+=1
    assert closed and abs(last-cutoff)<1e-8 and stamp==(path.stat().st_size,path.stat().st_mtime_ns)
    return dict(observed_unique_network_vehicles=len(seen),first_observation_links=dict(origins),
        observed_unique_link24_arrivals=len(road),link24_arrival_windows=dict(road_windows),
        not_desired_demand_or_exact_input_assignment=True,complete_prefix_end=cutoff,
        source_receipt=dict(path=path.relative_to(a.a.d.ROOT).as_posix(),bytes=stamp[0],mtime_ns=stamp[1]))


def main():
    output=B/'prefix_resolution_comparison';output.mkdir(exist_ok=False)
    configs={1:('analysis_res1','run',1500.),10:('analysis_res10_prefix1500p1','run_retry1',1500.1)}
    arms={};pins={}
    for resolution,(name,run_name,cutoff) in configs.items():
        folder=B/name
        result=e.load(folder/'result.json');series=e.load(folder/'series.json');pairs=e.load(folder/'overlaps.json')
        assert not result['qualified']
        if resolution==10:assert result['failed_run_prefix_only'] and result['closed_prefix'] and not result['native_validation_passed']
        rows=[]
        for label,lo,hi in (('before900',0.,900.),('900_to_cutoff',900.,cutoff+1e-7)):
            samples=[r for r in series if lo<=r['t']<hi]
            events=[r for r in pairs if lo<=r['t']<hi]
            totals=Counter()
            for r in samples:totals.update({k:v for k,v in r.items() if k!='t'})
            intersection=[r for r in events if r['rectangle_margin_m']>0]
            slow_intersection=sum(r['back']['v']<40 and r['front']['v']<40 for r in intersection)
            rows.append(dict(window=label,samples=len(samples),first_s=samples[0]['t'],last_s=samples[-1]['t'],
                average_vehicle_count=totals['vehicles']/len(samples),
                vehicle_weighted_mean_speed_kmh=totals['speed_sum']/totals['vehicles'],
                vehicle_seconds=totals['vehicles'],slow_vehicle_seconds=totals['slow_vehicles'],
                adjacent_pairs=totals['adjacent_pairs'],slow_adjacent_pairs=totals['slow_adjacent_pairs'],
                projected_overlaps=len(events),rectangle_intersections=len(intersection),
                slow_pair_rectangle_intersections=slow_intersection,
                all_pair_intersections_per10000=10000*len(intersection)/totals['adjacent_pairs'],
                slow_pair_intersections_per10000=(10000*slow_intersection/totals['slow_adjacent_pairs'] if totals['slow_adjacent_pairs'] else None),
                stable_prior3_overlap_count=sum(r['centered_stable_prior3'] for r in events)))
        native=B/f'none_s23_res{resolution}'/run_name/'vissim_eval/baseline_001.fzp'
        arms[resolution]=dict(windows=rows,observations=observed_arrivals(native,cutoff))
        for p in (folder/'result.json',folder/'series.json',folder/'overlaps.json'):
            pins[p.relative_to(a.a.d.ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    for x,y in zip(arms[1]['windows'],arms[10]['windows']):assert x['samples']==y['samples']
    pins[Path(__file__).relative_to(a.a.d.ROOT).as_posix()]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report=dict(qualified=False,production_adopted=False,full_resolution10_run_completed=False,
        same_seed_different_dynamics=True,phase_offset_sec=.1,arms=arms,source_pins=pins,
        limits=['Failed10-step run prefix only, no late congestion or final native validation.',
            'Matching sample counts does not make initial vehicles, demand realizations or traffic exposures equal.',
            'Lower overlap counts alone do not identify a direct numerical effect; report slow-pair exposures too.',
            'First recorded links are observations, not authoritative demand origins or desired input counts.'])
    e.save(output/'result.json',report)
    print(json.dumps({r:dict(windows=v['windows'],network_vehicles=v['observations']['observed_unique_network_vehicles'],link24_arrivals=v['observations']['observed_unique_link24_arrivals']) for r,v in arms.items()}))


if __name__=='__main__':main()
