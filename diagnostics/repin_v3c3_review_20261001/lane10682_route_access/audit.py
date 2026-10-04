"""Destination-conditioned lane observations; no physical or traffic changes."""
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from evaluation.controllers import offramp_routing as routing
from evaluation.controllers.projection_support import complete_records
from evaluation.controllers.vehicle_routes import complete_vehicle_routes

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
F=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/cellwise_calibration/freeway_first'
PINS={}
def read(p):
    data=p.read_bytes();PINS[str(p)]=hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if p.suffix=='.gz' else data)
def category(runtime,key):
    if key is None:return 'unknown'
    target=runtime['routes'][key]['target']
    return target if target in ('10643','10682') else 'other_known'
def describe(raw,runtime):
    routes=complete_vehicle_routes(raw,required=True);labels={};rows=[]
    for v in complete_records(raw):
        if str(v['link_no']) not in runtime['physical']:continue
        road,x,cell=routing._position(runtime,v['link_no'],v['position_m'])
        if road!='FW_E':continue
        route=routes[v['veh_no']]
        key=None if route['route_decision_no'] is None else str(route['route_decision_no'])+':'+str(route['route_no'])
        group=category(runtime,key)
        labels[str(v['veh_no'])]=group
        # These archived raw captures use the one-based lane_index field.
        lane=int(v['lane_index'])
        assert 1<=lane<=4
        rows.append(dict(vehicle=str(v['veh_no']),cell=cell,x_m=x,lane=lane,speed=v['speed_kph'],group=group))
    return labels,rows
def grouped(rows):
    result={}
    for zone,indices in [('cells0_7',range(8)),('cell8',[8]),('cell9',[9]),('cell10',[10]),('cell11',[11]),('cell12',[12])]:
        values=defaultdict(lambda:[0]*4)
        for row in rows:
            if row['cell'] in indices:values[row['group']][row['lane']-1]+=1
        result[zone]=dict(values)
    return result

def trajectories(runtime,seed,arm):
    raw=read(F/f'route_inventory/s{seed}_early/initial_raw.json')
    labels,initial=describe(raw,runtime)
    cache=read(F/f'cohort_early/s{seed}_{arm}_frames.json.gz')
    assert cache['fields']==['cell','speed_kmh','x_m','lane']
    frames=sorted((float(t),vs) for t,vs in cache['frames'].items())
    assert frames[0][0]==raw['sim_sec']
    start=frames[0][1]
    assert set(labels)==set(start)
    for v in initial:
        row=start[v['vehicle']]
        assert row[0]==v['cell'] and row[3]==v['lane'] and abs(row[1]-v['speed'])<1e-7 and abs(row[2]-v['x_m'])<1e-7
    alive=set(labels);crossings=[];endpoints=[]
    exposures=defaultdict(lambda:[0.]*4)
    changes=defaultdict(lambda:[[0]*4 for _ in range(4)])
    unique=defaultdict(set)
    gate=runtime['bounds']['FW_E'][9]
    for (ta,a),(tb,b) in zip(frames,frames[1:]):
        assert abs(tb-ta-5)<1e-6
        # Stop the initial mainline episode on its first absence. A later
        # re-entry is a different route episode and is not silently relabelled.
        alive.intersection_update(a.keys(),b.keys())
        for vid in alive:
            before,after=a[vid],b[vid];group=labels[vid]
            target=runtime['branches'].get(group)
            if target and before[2]>target['source_chain_m']:
                continue
            if before[2]<gate<=after[2]:
                crossings.append(dict(vehicle=vid,target=group,start_sec=ta,end_sec=tb,
                    from_lane=before[3],to_lane=after[3],stable_lane=before[3]==after[3],
                    from_cell=before[0],to_cell=after[0]))
            if not (9<=before[0]<=12 and 9<=after[0]<=12):continue
            g,k=before[3]-1,after[3]-1
            exposures[group][g]+=tb-ta
            unique[group].add(vid)
            if g!=k:
                changes[group][g][k]+=1
                endpoints.append(dict(vehicle=vid,target=group,start_sec=ta,end_sec=tb,
                    from_cell=before[0],to_cell=after[0],from_lane=g+1,to_lane=k+1,
                    from_speed=before[1],to_speed=after[1],
                    distance_to_target_m=None if target is None else target['source_chain_m']-before[2]))
    crossing_summary={}
    for group in sorted(set(labels.values())):
        rows=[x for x in crossings if x['target']==group]
        a=[0]*4;b=[0]*4;stable=[0]*4
        for row in rows:
            a[row['from_lane']-1]+=1;b[row['to_lane']-1]+=1
            if row['stable_lane']:stable[row['from_lane']-1]+=1
        crossing_summary[group]=dict(vehicles=len(rows),before_lane_counts=a,after_lane_counts=b,
            stable_lane_counts=stable,ambiguous=sum(not x['stable_lane'] for x in rows))
    return dict(initial_sec=raw['sim_sec'],end_sec=frames[-1][0],initial=grouped(initial),
        crossing_summary=crossing_summary,exposure_veh_sec=dict(exposures),changes=dict(changes),
        unique_observed={k:len(v) for k,v in unique.items()},crossings=crossings,change_records=endpoints,
        raw_cache_initial_exact=True)

def current_profiles(runtime):
    result={}
    for seed,cutoff,directory in [(43,2250,'D:/VISSIM_runs/20260929_seed43_observation2700/nc/decisions_sdmpc31_nc2700_s43'),
        (47,2700,'D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47')]:
        samples=[]
        for t in (cutoff-300,cutoff-150,cutoff):
            raw=read(Path(directory)/f'state_{t:06d}.json')
            frame=read(Path(raw['lane_plant_observation']['directory'])/f'frame_{t:06d}.json')
            assert frame['time_s']==t
            rows=[]
            for v in frame['vehicles']:
                if str(v[1]) not in runtime['physical']:continue
                road,x,cell=routing._position(runtime,v[1],v[3])
                if road!='FW_E':continue
                key=None if v[6] is None else f'{int(v[6])}:{int(v[7])}'
                rows.append(dict(vehicle=str(v[0]),cell=cell,lane=int(v[2]),group=category(runtime,key),x_m=x))
            samples.append(dict(time_sec=t,groups=grouped(rows)))
        result[str(seed)]=dict(cutoff=cutoff,samples=samples,only_past_current=True)
    return result

def main():
    output=HERE/'audit.json';assert not output.exists()
    old=read(HERE.parent/'lane10682_transport/completion.json')
    for p,h in old['restored_exact'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
    runtime=read(HERE.parent/'entry10643/native_cohorts.json')['route_runtime']
    result=dict(status='completed_destination_lane_observation',current=current_profiles(runtime),
        trajectories={f'{seed}_{arm}':trajectories(runtime,seed,arm) for seed in (29,43) for arm in ('none','vsl')},
        source_pins=PINS,production_unchanged=old['restored_exact'],new_forecasts=0,new_fzp_scans=0,new_native=0,
        limitations=['Crossings/lane changes are 5-second endpoint brackets, not exact event locations or rates.',
            'Trajectory labels cover only initial known/current-route cohorts; new arrivals remain unlabelled.',
            'Future trajectory data are for independent-training/comparison only, never autonomous prediction inputs.'])
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for seed,row in result['current'].items():print('CURRENT',seed,row)
    for key,row in result['trajectories'].items():print('TRAJECTORY',key,row['crossing_summary'],'EVENTS',row['changes'],'EXPOSURE',row['exposure_veh_sec'])
if __name__=='__main__':main()
