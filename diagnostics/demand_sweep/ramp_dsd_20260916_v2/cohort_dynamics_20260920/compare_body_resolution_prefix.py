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


def full():
    """Compare completed resolutions; no same-initial-state/control claim."""
    import math
    import numpy as np
    import xml.etree.ElementTree as ET
    root=a.a.d.ROOT;mesh=B.parent.parent/'segment_resolution_20260921'
    out=B/'full_resolution_comparison'
    if out.exists():assert not any(out.iterdir()),'Existing comparison result must not be overwritten'
    else:out.mkdir()
    sources=[Path(__file__),Path(a.__file__)]
    arms={};phase={}
    for res,name,run_name in ((1,'analysis_res1','run'),(10,'analysis_res10','run_retry2')):
        folder=B/name;run_dir=B/f'none_s23_res{res}'/run_name
        result=e.load(folder/'result.json');run=e.load(run_dir/'run.json')
        assert result['native_validation_passed'] and result['terminal_s']==3000
        assert not result.get('failed_run_prefix_only',False)
        recovery=a.require_closed_native(run_dir)
        assert e.load(run_dir/'fixed_validation.json')['passed']
        series=e.load(folder/'series.json');pairs=e.load(folder/'overlaps.json');windows=[]
        assert all(abs(q['t']-p['t']-1)<1e-8 for p,q in zip(series,series[1:]))
        phase[res]=round(series[0]['t']%1,8)
        if 'sampling' in result:assert phase[res]==result['sampling']['phase_s']
        for lo,hi in ((0,900),(900,1800),(1800,2400),(2400,2700),(2700,3000)):
            rs=[r for r in series if lo<=r['t']<hi]
            events=[r for r in pairs if lo<=r['t']<hi]
            hits=[r for r in events if r['rectangle_margin_m']>0]
            total=Counter()
            for row in rs:total.update({key:value for key,value in row.items() if key!='t'})
            slowhits=sum(r['back']['v']<40 and r['front']['v']<40 for r in hits)
            windows.append(dict(start=lo,end=hi,samples=len(rs),mean_vehicles=total['vehicles']/len(rs),
                mean_speed_kmh=total['speed_sum']/total['vehicles'],vehicle_samples=total['vehicles'],
                slow40_vehicle_samples=total['slow_vehicles'],slow40_share=total['slow_vehicles']/total['vehicles'],
                adjacent_pairs=total['adjacent_pairs'],slow_pairs=total['slow_adjacent_pairs'],
                projected_overlaps=len(events),rectangle_intersections=len(hits),slow_pair_intersections=slowhits,
                all_pair_rate_per10000=10000*len(hits)/total['adjacent_pairs'],
                slow_pair_rate_per10000=10000*slowhits/total['slow_adjacent_pairs'] if total['slow_adjacent_pairs'] else None))
        arms[res]=windows
        sources.extend([folder/'result.json',folder/'series.json',folder/'overlaps.json',run_dir/'run.json',run_dir/'fixed_validation.json'])
        if recovery is not None:sources.append(run_dir/'terminal_recovery.json')
    assert phase=={1:0.,10:.1}
    assert [x['samples'] for x in arms[1]]==[x['samples'] for x in arms[10]]
    # Confirm this was only a native integration-resolution condition change.
    networks=[];signal_hashes=[]
    for res in (1,10):
        folder=B/f'none_s23_res{res}';network=folder/'source/baseline.inpx'
        x=ET.parse(network).getroot();assert int(x.find('simulation').get('simRes'))==res
        x.find('simulation').set('simRes','1');networks.append(ET.tostring(x))
        setting=e.load(folder/'prepared/prepared.json')
        signal_hashes.append({Path(name).name:digest for name,digest in setting['snapshot_sha256'].items() if Path(name).suffix.lower()=='.sig'})
        sources.extend([network,folder/'profile.json',folder/'prepared/prepared.json'])
    assert networks[0]==networks[1] and signal_hashes[0]==signal_hashes[1]

    zpath=mesh/'none_s23_0.npz';gpath=mesh/'geometry_200_branch_guard.json'
    cells10path=B/'analysis_res10/cell_series.json'
    cells=e.load(cells10path);geo={r['cell']:r for r in e.load(gpath)['cells'] if r['road']=='FW_E'}
    with np.load(zpath) as z:
        totals={key:z[key].sum(axis=2) for key in ('n','mom','slow','stop')}
        baseline=[dict(t=t,cell=i,n=float(totals['n'][t-2249,i-10]),moment=float(totals['mom'][t-2249,i-10]),
                       slow30=float(totals['slow'][t-2249,i-10]),stop5=float(totals['stop'][t-2249,i-10]))
                  for t in range(2249,3000) for i in range(25,31)]
    assert len(cells)==len(baseline)==751*6
    coefficients=e.load(mesh/'recovery_acceleration_v1/ra_disabled.json')['physical_coefficients']
    critical_speed=coefficients['v_free']*math.exp(-1/coefficients['metanet_a_m'])
    region=[];events=[]
    for res,rows in ((1,baseline),(10,cells)):
        for i in range(25,31):
            rs=[r for r in rows if r['cell']==i]
            assert len(rs)==751 and all(abs(q['t']-p['t']-1)<1e-8 for p,q in zip(rs,rs[1:]))
            for lo,hi in ((2250,2400),(2400,2700),(2700,3000)):
                selected=[r for r in rs if lo<=r['t']<hi];n=sum(r['n'] for r in selected)
                occupied=[r for r in selected if r['n']>0]
                region.append(dict(resolution=res,cell=i,start=lo,end=hi,samples=len(selected),vehicle_samples=n,
                    mean_vehicles=n/len(selected),weighted_speed_kmh=sum(r['moment'] for r in selected)/n if n else None,
                    slow30_vehicle_samples=sum(r['slow30'] for r in selected),stop5_vehicle_samples=sum(r['stop5'] for r in selected),
                    low_mean_speed_samples=sum(r['moment']/r['n']<critical_speed for r in occupied),
                    min_mean_speed_kmh=min((r['moment']/r['n'] for r in occupied),default=None)))
            for j,r in enumerate(rs[:-4]):
                if r['t']<2400:continue
                segment=rs[j:j+5]
                if all(x['n'] and x['moment']/x['n']<critical_speed for x in segment):
                    events.append(dict(resolution=res,cell=i,t=r['t'],speed=r['moment']/r['n'],
                        mean_density=r['n']/geo[i]['lane_km'],already_below_at_start=abs(r['t']-(2400+phase[res]))<1e-8))
                    break
    sources.extend([zpath,gpath,cells10path,mesh/'recovery_acceleration_v1/ra_disabled.json'])
    result=dict(qualified=False,production_adopted=False,full_resolution10_run_completed=True,
        new_native_runs_this_turn=1,new_control_commands=0,coefficient_fit=False,phase_offset_sec=.1,
        physical_network_and_demand_equal_except_sim_resolution=True,native_signals_equal=True,
        same_initial_state=False,arms=arms,regional=region,low_mean_speed_events=events,critical_speed_kmh=critical_speed,
        source_pins={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        limitations=['Resolution changes dynamics and realized input; not a matched-state causal control effect.',
            'Actual time stamps retained, no interpolation or rounding; equal samples do not mean equal traffic exposure.',
            'Rectangular body intersection is not a native collision flag.',
            'FD-critical-speed/five-sample persistence is a diagnostic definition, not an operational gate.',
            'Existing low-resolution calibration and RM/VSL gains cannot be transferred without new validation.'])
    e.save(out/'result.json',result)
    print(json.dumps(dict(arms=arms,events=events)))


def control_comparison():
    """Assess only completed native arms; do not mix resolutions or model fits."""
    base=B.parent/'resolution_control_v1/paired'
    arms=[arm for arm in ('none','rm_ramp','vsl','both') if (base/f'analysis_{arm}/result.json').is_file()]
    assert arms[0]=='none' and len(arms)>1
    datasets={arm:e.load(base/f'analysis_{arm}/result.json') for arm in arms}
    summaries=[];regional=[]
    for arm in arms[1:]:
        for nc,action in zip(datasets['none']['windows'],datasets[arm]['windows']):
            assert (nc['start'],nc['end'],nc['samples'])==(action['start'],action['end'],action['samples'])
            delta={k:action['component_ttt_veh_h'][k]-nc['component_ttt_veh_h'][k] for k in ('mainline','on','off','total')}
            summaries.append(dict(arm=arm,start=nc['start'],end=nc['end'],delta_ttt_veh_h=delta,
                component_improvement_pct=-100*delta['total']/nc['component_ttt_veh_h']['total'],
                rm10490_merges_none=nc['signed_mainline_boundaries'].get('merge:10490',0),
                rm10490_merges_action=action['signed_mainline_boundaries'].get('merge:10490',0),
                normal_off_departure_change={str(c):action['normal_port_departures'].get(str(c),0)-nc['normal_port_departures'].get(str(c),0) for c in (10643,10682,10481,10483)},
                terminal_inferred_outflow_change=nc['signed_mainline_boundaries']['terminal_inferred']-action['signed_mainline_boundaries']['terminal_inferred'],
                source_entry_change=action['signed_mainline_boundaries']['source']-nc['signed_mainline_boundaries']['source']))
    for arm in arms:
        cells=e.load(base/f'analysis_{arm}/cells.json')
        for lo,hi in ((2400,2700),(2700,3000),(2400,2850)):
            for i in range(31):
                selected=[r for r in cells if r['cell']==i and lo<=r['time_s']<hi]
                n=sum(r.get('n',0) for r in selected)
                regional.append(dict(arm=arm,cell=i,start=lo,end=hi,mean_n=n/len(selected),
                    speed_kmh=sum(r.get('speed_sum',0) for r in selected)/n if n else None,
                    ttt_veh_h=n/3600,slow30_vehicle_s=sum(r.get('slow30',0) for r in selected)))
    tag='_'.join(arms[1:]);dest=base/f'comparison_{tag}.json'
    result=dict(qualified=False,production_adopted=False,arms=arms,all_four_conditions_completed=len(arms)==4,
        same_resolution=10,seed=23,summaries=summaries,regional=regional,
        scope=datasets['none']['scope'],sampling=datasets['none']['sampling'],
        error_counts={arm:d['error_counts'] for arm,d in datasets.items()},
        east_removals={arm:len(d['east_removals']) for arm,d in datasets.items()},
        limits=['The comparison is component residence, NOT full Omega improvement.',
            'A fixed command response does not prove the MPC would choose it.',
            'One development seed/window is not independent benefit validation.',
            'Network-wide deletion changes and source realization changes are reported, not scored as TTD.'],
        source_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),*[base/f'analysis_{arm}/result.json' for arm in arms],*[base/f'analysis_{arm}/cells.json' for arm in arms]]})
    e.save(dest,result)
    print(json.dumps(dict(path=str(dest),windows=[r for r in summaries if r['start']==2400 and r['end'] in (2850,3000)],errors=result['error_counts'])))


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--full':full()
    elif len(sys.argv)>1 and sys.argv[1]=='--control-response':control_comparison()
    else:main()
