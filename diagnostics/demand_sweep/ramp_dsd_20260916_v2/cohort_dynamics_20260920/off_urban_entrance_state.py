"""Bounded spatial audit of10643 ->126 ->71 using existing native files.

Front distance is an observation, not free rear clearance or a capacity law.
No new VISSIM run, fitted coefficient, or production model is created.
"""
from pathlib import Path
import argparse,csv,hashlib,sys
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.state_exchange_20260920.analyze_dispersion import records

HERE=Path(__file__).resolve().parent


def review():
    out=HERE/'off_urban_entrance_state_v1/review.json'
    if out.exists():raise FileExistsError(out)
    result={};pins={}
    archive=out.parent/'source_before_review/off_urban_entrance_state.py.txt'
    for case in ('s23_none','s23_vsl'):
        spatial=out.parent/f'{case}.json';data=e.load(spatial)
        for file,pin in data['pins'].items():
            p=e.ROOT/file
            if p==Path(__file__):p=archive
            assert hashlib.sha256(p.read_bytes()).hexdigest()==pin
        proof=HERE/'urban_drain_observations_v5'/f'{case}_evidence.json';evidence=e.load(proof)
        table=proof.with_name(f'{case}.csv')
        with table.open(encoding='utf-8-sig') as f:rows={int(r['time_s']):r for r in csv.DictReader(f) if 2400<=float(r['time_s'])<2850}
        frames={r['time_s']:r['vehicles'] for r in data['frames']}
        groups=[]
        for t,r in rows.items():
            if r['sg2_state']!='GREEN':continue
            if not groups or t!=groups[-1][-1]+1:groups.append([])
            groups[-1].append(t)
        greens=[dict(start_s=g[0],end_s=g[-1]+1,
            lane3_crossings=sum(float(rows[t]['head_lane3']) for t in g),
            off_lane2_departures=sum(float(rows[t]['off_lane2_departures']) for t in g),
            lane3_queue_seconds=sum(float(rows[t]['urban_lane3_head_queue'])>0 for t in g),
            sg2_removals=sum(float(rows[t]['urban_sg2_removals']) for t in g)) for g in groups]
        run=e.ROOT/data['source'];network=Path(e.load(run/'run.json')['network']);root=ET.parse(network).getroot()
        decision=next(x for x in root.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic') if x.get('no')=='1126')
        route=next(x for x in decision.findall('./vehRoutSta/vehicleRouteStatic') if x.get('no')=='1')
        route_info=dict(destination=route.get('destLink'),links=[x.get('key') for x in route.findall('./linkSeq/intObjectRef')])
        connector=next(x for x in root.findall('./links/link') if x.get('no')=='10635')
        route_info['connector_from']=dict(connector.find('./fromLinkEndPt').attrib)
        route_info['connector_lane_count']=len(connector.findall('./lanes/lane'))
        assert route_info['destination']=='47' and '10635' in route_info['links']
        blockers=[]
        for loss in evidence['explicit_urban_removals']:
            if not (2400<=loss['time_sec']<2850 and loss['last_lane']==3 and loss['route_decision']==1126 and loss['route_index']==1):continue
            vid=loss['vehicle_id'];head_green=[];records=[]
            for t in rows:
                lane=[v for v in frames[t] if v[1]==71 and v[2]==3]
                own=next((v for v in lane if v[0]==vid),None)
                if own:records.append([t,own[3],own[4]])
                if own and rows[t]['sg2_state']=='GREEN' and own[4]<1 and own[3]==max(v[3] for v in lane):head_green.append(t)
            blockers.append(dict(loss=loss,route=route_info,stopped_at_lane_head_during_green_seconds=len(head_green),
                stopped_head_green_span=[min(head_green),max(head_green)+1] if head_green else None,
                last_positions=records[-2:]))
        intervals=[];entry=float(data['connections']['10641']['pos'])
        for lo in range(2400,2850,150):
            near=exits=near_exits=0;fronts=[]
            for t in range(lo,lo+150):
                ahead=sorted((v for v in frames[t] if v[1]==71 and v[2]==3 and v[3]>=entry),key=lambda v:v[3])
                close=bool(ahead and ahead[0][3]-entry<6 and ahead[0][4]<5)
                near+=close
                if ahead:fronts.append(ahead[0][3]-entry)
                n=float(rows[t]['off_lane2_departures']);exits+=n;near_exits+=n*close
            intervals.append(dict(start_s=lo,off_lane2_departures=exits,near_entry_stopped_seconds=near,
                mean_nearest_front_distance_when_present=sum(fronts)/len(fronts) if fronts else None,
                exits_while_near_entry_proxy=near_exits))
        result[case]=dict(greens=greens,intervals=intervals,confirmed_route_access_blockers=blockers,
            total_lane3_crossings=sum(float(r['head_lane3']) for r in rows.values()),
            total_off_lane2_departures=sum(float(r['off_lane2_departures']) for r in rows.values()))
        for p in (spatial,proof,table,network):pins[str(p.relative_to(e.ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
        print(case,'greens',greens,'blockers',[(r['loss']['vehicle_id'],r['stopped_at_lane_head_during_green_seconds']) for r in blockers],flush=True)
    pins[str(Path(__file__).relative_to(e.ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    e.save(out,dict(status='NATIVE_SPATIAL_ROUTE_ACCESS_AUDIT',cases=result,pins=pins,new_native_runs=0,
        interpretation='Same45s green does not guarantee lane3 discharge. Native lane-change removals identify intended connector10635, reached from71 lanes4/5 while vehicle blocks lane3.',
        caveats=['Observed head-front distance is not rear clearance. Some off exits occur while entrance proxy is occupied: never impose a binary zero flow from it.',
            'This identifies actual route-access obstruction, not the complete causal effect of VSL or a calibrated blocker transition law.',
            'Lane-change deletions remain abnormal losses, never normal service or TTD.',
            'No route choice, demand, network, or production parameter was modified.']))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--case',choices=['s23_none','s23_vsl']);ap.add_argument('--review',action='store_true');args=ap.parse_args()
    if args.review:
        if args.case:raise ValueError('Review uses the two completed extractions')
        return review()
    if not args.case:ap.error('--case is required for extraction')
    out=HERE/'off_urban_entrance_state_v1';out.mkdir(exist_ok=True)
    destination=out/f'{args.case}.json'
    if destination.exists():raise FileExistsError(destination)
    base=HERE/'urban_drain_observations_v5';proof=base/f'{args.case}_evidence.json';table=base/f'{args.case}.csv'
    receipt=e.load(proof);run=e.ROOT/receipt['source'];native=e.load(run/'run.json')
    assert native['completed'];network=Path(native['network']);root=ET.parse(network).getroot()
    links={int(x.get('no')):x for x in root.findall('./links/link')}
    destinations={str(key):dict(links[key].find('./toLinkEndPt').attrib) for key in (10643,10641,10700)}
    with table.open(encoding='utf-8-sig') as f:rows={int(r['time_s']):r for r in csv.DictReader(f)}
    selected={10643,126,10641,10700,71};frames=[];frame=[];last=None;checks=0
    def flush(t,vehicles):
        nonlocal checks
        if t in rows:
            r=rows[t]
            for lane in (1,2):
                assert sum(link==10643 and l==lane for vid,link,l,p,v in vehicles)==int(r[f'off_lane{lane}_n']);checks+=1
            for lane in range(1,6):
                assert sum(link==71 and l==lane for vid,link,l,p,v in vehicles)==int(r[f'urban_lane{lane}_n']);checks+=1
            assert sum(link==126 for vid,link,l,p,v in vehicles)==int(r['link126_n']);checks+=1
        frames.append(dict(time_s=t,vehicles=sorted(vehicles)))
    file=run/'vissim_eval/baseline_001.fzp';before=file.stat()
    for p in records(file):
        t=int(float(p[0]))
        if t<2400:continue
        if t>2850:break
        if last is not None and t!=last:
            assert t==last+1;flush(last,frame);frame=[]
        last=t;link=int(p[2])
        if link in selected:frame.append([int(p[1]),link,int(p[3]),float(p[4]),float(p[6])])
    assert last==2850;flush(last,frame)
    after=file.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    assert len(frames)==451 and checks==3600
    e.save(destination,dict(case=args.case,frames=frames,columns=['vehicle','link','lane','front_position_m','speed_kmh'],
        source=str(run.relative_to(e.ROOT)),source_fzp_stat=dict(size=before.st_size,mtime_ns=before.st_mtime_ns),
        connections=destinations,native_inventory_checks=checks,
        pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),proof,table,network]},
        interpretation='Observed positions only. Future snapshots are labels, not a causal rollout input; no vehicle lengths inferred.',
        new_native_runs=0))
    print(args.case,len(frames),'frames;',checks,'native inventory checks',flush=True)


if __name__=='__main__':main()
