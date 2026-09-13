"""Completed NC onset: 60 indexed one-second frames, no model/whole FZP scan."""
from bisect import bisect_right
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import time
import xml.etree.ElementTree as ET
from diagnostics.probe_e8_lane_receiving import IndexedFzp

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'evaluation/runs/codex_nc5400_r01_baseline_s13'
DECISIONS = RUN / ('decisions_' + RUN.name)
OUT = ROOT / 'diagnostics/nc_r01_e8_onset.json'
FOCUS = {2, 68, 69, 70, 71, 121, 123, 126, 10643, 10639, 10682, 10681, 10641, 10635, 10634, 10646, 10773}
CONNECTORS = {10643, 10639, 10682, 10681, 10641, 10635, 10634, 10646, 10773}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def stats(items):
    return {'n': len(items), 'speed_kph': sum(x[3] for x in items) / len(items) if items else None,
            'stopped_lt1': sum(x[3] < 1 for x in items), 'stopped_lt5': sum(x[3] < 5 for x in items),
            'min_stopped_position_m': min((x[2] for x in items if x[3] < 1), default=None),
            'max_stopped_position_m': max((x[2] for x in items if x[3] < 1), default=None)}


def main():
    assert not OUT.exists()
    started = time.perf_counter()
    manifest_path = ROOT / 'diagnostics/no_control_network_arms/r01/manifest.json'
    batch = load(manifest_path); receipt = batch['arms'][0]
    assert receipt['arm'] == 'baseline' and receipt['valid'] and receipt['completed'] and receipt['trajectory']['valid']
    assert receipt['name'] == RUN.name and receipt['status'] == 'passed' and not batch['source_changes']
    network_path = ROOT / 'diagnostics/fixed_beta300v3_network_arms_flat_v1/baseline.inpx'
    mapping_path = ROOT / 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'
    small = ROOT / 'diagnostics/no_control_5400_baseline_diagnosis_v1'
    source_paths = [Path(__file__), ROOT / 'diagnostics/probe_e8_lane_receiving.py', manifest_path,
                    network_path, mapping_path, small / 'cell_samples.csv', small / 'cell_episodes.csv',
                    ROOT / 'diagnostics/e8_lane_receiving_review.md', ROOT / 'diagnostics/direct_branch_feedback_and_order_design.md']
    anchors = sorted(DECISIONS.glob('anchor_*.json')); source_paths += anchors
    lsa_paths = list(RUN.rglob('*.lsa')); assert len(lsa_paths) == 1
    source_paths += lsa_paths + [DECISIONS / 'action_000900.csv']
    pins = {p.relative_to(ROOT).as_posix(): sha(p) for p in source_paths}
    chain = load(mapping_path)['freeway_model_links']['FW_E']
    offsets = dict(zip(map(int, chain['chain_links']), chain['chain_offsets_m']))
    bounds = chain['segment_bounds_m']
    tree = ET.parse(network_path).getroot(); links = {int(x.get('no')): x for x in tree.findall('./links/link')}
    geometry = {}
    for no in sorted(CONNECTORS):
        x = links[no]; ends = {}
        for key in ('fromLinkEndPt', 'toLinkEndPt'):
            a = x.find(key); link, lane = map(int, a.get('lane').split()); position = float(a.get('pos'))
            ends[key] = {'link': link, 'lane': lane, 'position_m': position}
            if link in offsets:
                ends[key].update(chain_m=offsets[link]+position, cell=bisect_right(bounds, offsets[link]+position)-1)
        points = [tuple(float(p.get(axis, 0)) for axis in ('x', 'y', 'zOffset')) for p in x.findall('./geometry/linkPolyPts/linkPolyPoint')]
        geometry[str(no)] = {'ends': ends, 'length_m': sum(math.dist(a,b) for a,b in zip(points,points[1:])),
                             'lanes': len(x.findall('./lanes/lane')), 'lane_change_distance_m': float(x.get('lnChgDist'))}
    cuts = {'signal_diverge': geometry['10643']['ends']['fromLinkEndPt']['chain_m'],
            'first_merge': geometry['10639']['ends']['toLinkEndPt']['chain_m'],
            'direct_diverge': geometry['10682']['ends']['fromLinkEndPt']['chain_m'],
            'second_merge': geometry['10681']['ends']['toLinkEndPt']['chain_m']}
    regions = {'E8': (bounds[8], bounds[9]), 'E9_prefix': (bounds[9], cuts['direct_diverge']),
               'E9_after_diverge': (cuts['direct_diverge'], cuts['second_merge']),
               'E9_after_merge': (cuts['second_merge'], bounds[10])}

    def summarize(frame):
        rows, lanes, bins = {}, {}, {}
        for link in sorted(FOCUS): rows[str(link)] = stats([x for x in frame.values() if x[0] == link])
        for region, (start,end) in regions.items():
            for lane in range(1,5):
                values = [(link, ln, offsets[link]+p, v) for link,ln,p,v in frame.values()
                          if link in offsets and ln == lane and start <= offsets[link]+p < end]
                lanes[region + ':' + str(lane)] = {**stats(values), 'density_veh_km_lane':len(values)*1000/(end-start)}
        for lo in range(4300,5100,100):
            for lane in range(1,5):
                bins[str(lo)+':'+str(lane)] = stats([(link,ln,offsets[link]+p,v) for link,ln,p,v in frame.values()
                                                    if link in offsets and ln == lane and lo <= offsets[link]+p < lo+100])
        return {'links':rows, 'regions_lanes':lanes, '100m_lanes':bins}

    observed_anchors = []
    for path in anchors:
        raw = load(path); records = raw['vehicle_records']; routes = raw['vehicle_routes']
        assert records['complete'] and routes['complete'] and records['record_count'] == routes['record_count']
        frame = {int(r['veh_no']):(int(r['link_no']),int(r['lane_no']),r['position_m'],r['speed_kph']) for r in records['records']}
        route_by_id = {int(r['veh_no']):r for r in routes['records']}
        assert set(frame) == set(route_by_id)
        cohorts, selected = Counter(), []
        for veh,(link,lane,pos,speed) in frame.items():
            if link not in FOCUS: continue
            route = route_by_id[veh]
            region = next((key for key,(a,b) in regions.items() if link in offsets and a <= offsets[link]+pos < b), 'link'+str(link))
            key = f"{route['route_decision_no']}:{route['route_no']}" if route['route_decision_type']=='STATIC' else 'unknown'
            cohorts[region+'|lane'+str(lane)+'|'+key] += 1
            selected.append({'veh_no':veh, 'link':link, 'lane':lane, 'position_m':pos, 'speed_kph':speed,
                             'route':route, 'region':region})
        observed_anchors.append({'sim_sec':raw['sim_sec'], **summarize(frame), 'route_lane_counts':cohorts,
                                 'selected_records':selected, 'ramp_counts':raw['ramp_counts']})
    fzp = list(RUN.rglob('*.fzp')); assert len(fzp) == 1
    before = fzp[0].stat(); reader = IndexedFzp(fzp[0], max_bytes=64*1024*1024)
    snapshots, transitions, saved_frames = [], [], {}
    pairs = [(t,t+1) for t in range(1200,1490,10)] + [(1499,1500)]
    try:
        for t0,t1 in pairs:
            assert time.perf_counter()-started < 45, 'Bounded wall limit exceeded'
            pair = [reader.snapshot(t) for t in (t0,t1)]
            for t,frame in zip((t0,t1),pair):
                snapshots.append({'sim_sec':t, **summarize(frame)})
                saved_frames[str(t)] = [[veh,*record] for veh,record in frame.items() if record[0] in FOCUS]
            a,b = pair; crossed, moves, connector_events = [], [], []
            for veh in a.keys() & b.keys():
                old,new = a[veh],b[veh]
                if old[0] in offsets and new[0] in offsets:
                    p0,p1 = offsets[old[0]]+old[2],offsets[new[0]]+new[2]
                    for name,cut in {'E8_E9':bounds[9],**cuts}.items():
                        if p0 < cut <= p1: crossed.append({'veh_no':veh,'gate':name,'lane_before':old[1],'lane_after':new[1],
                            'interpolated_sec':t0+(cut-p0)/(p1-p0), 'bracket_sec':[t0,t1]})
                    if old[1] != new[1] and bounds[8] <= p0 < bounds[10]:
                        moves.append({'veh_no':veh,'old':old,'new':new})
                for no in CONNECTORS:
                    ends=geometry[str(no)]['ends']
                    if old[0] == ends['fromLinkEndPt']['link'] and new[0] == no:
                        connector_events.append({'veh_no':veh,'connector':no,'event':'entry','old':old,'new':new})
                    elif old[0] == no and new[0] == ends['toLinkEndPt']['link']:
                        connector_events.append({'veh_no':veh,'connector':no,'event':'exit','old':old,'new':new})
            transitions.append({'start_sec':t0,'end_sec':t1,'mainline_crossings_lower_bound':crossed,
                                'observed_lane_changes':moves,'observed_connector_transitions':connector_events})
    finally: reader.handle.close()
    after=fzp[0].stat(); assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    assert len(reader.selected)==60 and len(snapshots)==60
    anchor1500=next(a for a in observed_anchors if a['sim_sec']==1500)
    snapshot1500=next(a for a in snapshots if a['sim_sec']==1500)
    assert all(anchor1500['links'][str(link)]['n']==snapshot1500['links'][str(link)]['n'] for link in FOCUS)
    heads=[]
    for h in tree.findall('./signalHeads/signalHead'):
        link,lane=map(int,h.get('lane').split())
        if link in FOCUS: heads.append({'head':h.get('no'),'link':link,'lane':lane,'pos':float(h.get('pos')),'sg':h.get('sg')})
    events=[]
    for raw in lsa_paths[0].read_bytes().splitlines():
        if b';' not in raw:continue
        p=[x.strip() for x in raw.decode('ascii').split(';')]
        if len(p)==9 and p[2]=='1004' and 1150<=float(p[0])<=1510:
            events.append({'sim_sec':float(p[0]),'sc':int(p[2]),'sg':int(p[3]),'state':p[4]})
    with (small/'cell_samples.csv').open(encoding='utf-8-sig',newline='') as f:
        cells=[r for r in csv.DictReader(f) if r['direction']=='E' and r['cell_index'] in ('7','8','9','10') and 900<=float(r['sim_sec'])<=1800]
    changed=[p for p,h in pins.items() if sha(ROOT/p)!=h]; assert not changed
    result={'schema':'nc-r01-e8-onset/v1','run':RUN.name,'source_sha256':pins,'source_changes':changed,'geometry':geometry,
            'cuts_chain_m':cuts,'regions_chain_m':regions,'source_heads':heads,'selected_SC1004_native_events':events,
            'cell_samples':cells,'anchors':observed_anchors,'snapshots':snapshots,'transitions':transitions,'selected_frames':saved_frames,
            'fzp':{'path':fzp[0].relative_to(ROOT).as_posix(),'bytes':after.st_size,'mtime_ns':after.st_mtime_ns,'bytes_read':reader.bytes_read,
                   'selected_blocks':reader.selected,'full_trajectory_receipt':receipt['trajectory'],'frame1500_anchor_count_exact':True},
            'method':{'pairs_sec':pairs,'snapshot_stopped':'speed<1 and speed<5 both recorded',
                      'densities':'instantaneous vehicles / physical region length / lane; no model projection',
                      'crossings':'same ID at both ends of selected 1s bracket; interpolation is an estimate within the bracket',
                      'limitations':['Only 30 selected 1s windows; transition sums are not complete 150s flows or capacities.',
                                     'Anchor route fields apply at their own time only; no route backfill into earlier FZP.',
                                     'Position gaps/tails are not bumper clearances or proof of continuous spillback.',
                                     'No new model, capacity fit, VISSIM or whole FZP scan.']},'elapsed_sec':time.perf_counter()-started}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'path':OUT.relative_to(ROOT).as_posix(),'bytes_read':reader.bytes_read,'frames':len(snapshots),'elapsed_sec':result['elapsed_sec'],'source_changes':changed}))


if __name__=='__main__':main()
