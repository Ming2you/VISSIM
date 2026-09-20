"""Inspect local entry queues versus whole-lane free storage; no model fitting."""
from pathlib import Path
import sys
import hashlib
import argparse,csv,time,statistics
import xml.etree.ElementTree as ET
from collections import defaultdict,Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,CASES

HERE=Path(__file__).resolve().parent


def quantiles(values):
    x=sorted(values)
    return {str(q):x[int((len(x)-1)*q)] for q in (.1,.5,.9)} if x else {}


def main():
    out=HERE/'off_entry_space_audit_v1';out.mkdir(exist_ok=False)
    results={};pins={}
    for seed,folder,bank,start in CASES:
        data=e.ObservationData(folder)
        model=e.load_base_model(data.geometry,HERE/'port_origin_split_v1/config.json')
        port=model.offramps['10643'];capacity=port['storage_capacity_veh']/port['lanes']
        per_lane={l:{'snapshots':[],'stopped_pair_spacings_m':[]} for l in (1,2)}
        for t,cohorts in data.port_cohorts.items():
            if not 900<=float(t)<=4500:continue
            for lane,values in per_lane.items():
                rows=sorted((p,v) for p,v,l in cohorts['10643'] if l==lane)
                values['stopped_pair_spacings_m'].extend(b[0]-a[0] for a,b in zip(rows,rows[1:]) if a[1]<1 and b[1]<1)
                if rows:
                    p,v=rows[0]
                    values['snapshots'].append({'time_s':int(t),'stock':len(rows),'first_front_position_m':p,
                        'first_speed_kmh':v,'nominal_free_veh':capacity-len(rows),
                        'stopped_in_first6m':p<6 and v<5,'stopped_in_first10m':p<10 and v<5})
        summary={}
        for lane,values in per_lane.items():
            snapshots=values['snapshots'];gaps=values['stopped_pair_spacings_m']
            summary[str(lane)]={'nonempty_snapshots':len(snapshots),'stopped_pair_samples':len(gaps),
                'spacing_quantiles_m':quantiles(gaps),'max_observed_stock':max(r['stock'] for r in snapshots)}
            for limit in (6,10):
                selected=[r for r in snapshots if r[f'stopped_in_first{limit}m']]
                summary[str(lane)][f'entry_queue_first{limit}m']={'samples':len(selected),
                    'nominal_free_space_quantiles_veh':quantiles([r['nominal_free_veh'] for r in selected]),
                    'nominal_room_for_at_least_one':sum(r['nominal_free_veh']>=1 for r in selected)}
        results[str(seed)]={'summary':summary,'lane_capacity_veh':capacity,'observations':per_lane}
        for p in (folder/'port_cohorts_30s.json',folder/'geometry.json'):
            pins[str(p.relative_to(e.ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
        print(seed,summary,flush=True)
    e.save(out/'result.json',{'results':results,'pins':pins,'native_runs_started':0,'fitted_parameters':[],
        'interpretation':'Near-entry stopped vehicles coexist with nominal free storage. This identifies a candidate spatial receiving limitation, not a proved capacity law or proof that no vehicle can enter.',
        'sampling':'Existing NC snapshots every30s,900..4500; adjacent stopped front-to-front spacing is not a calibrated jam density.',
        'model_observation':'Canonical lane store admits from capacity-stock after release; newly freed downstream space has no backward propagation delay.'})


def blocking_audit():
    """Lane-local blockage observations; never infer zero capacity from zero flow."""
    from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import H
    from diagnostics.analyze_no_control_corridors import native_frames
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.extract_observations import Observer
    out=HERE/'lane_blocking_audit_v1';out.mkdir(exist_ok=False)
    root=ET.parse(H/'source_dsd/baseline.inpx').getroot()
    links={int(x.get('no')):x for x in root.findall('./links/link')}
    results={};source_pins={};start,end=2400,2850
    for seed,folder,bank,_ in CASES:
        if seed not in (23,33):continue
        for arm in ('none','vsl'):
            data=e.ObservationData(folder if arm=='none' else bank/'observations'/arm)
            observer=Observer(data.geometry);manifest=e.load(data.folder/'manifest.json')
            run=Path(manifest['source_run']);run=run if run.is_absolute() else e.ROOT/run
            assert e.load(run/'run.json')['completed']
            path=run/'vissim_eval/baseline_001.fzp';stat=path.stat();evidence={}
            ports={int(p['connector']):p for p in data.geometry['boundaries'] if p['road']=='FW_E' and p['kind']=='offramp'}
            access={}
            for o,p in ports.items():
                first=int(links[o].find('fromLinkEndPt').get('lane').split()[1])
                access[o]={first+i:i+1 for i in range(int(p['lanes']))}
            events=e.rows(data.folder/'port_events.csv')
            expected={kind:{(int(float(r['time_s'])),int(r['vehicle']),int(r['connector'])) for r in events
                       if int(r['connector']) in ports and r['kind']==kind and start<float(r['time_s'])<=end}
                      for kind in ('arrival','departure')}
            seen={kind:set() for kind in expected};rows=[];urban=[];group_rows=[];flows=Counter();previous=None;checks=0
            for t,frame in native_frames(path,evidence,deadline=time.monotonic()+600):
                if t<start:continue
                if t>end:break
                if previous is not None:assert t==last+1
                bylink=defaultdict(dict);positions={}
                for vid,r in frame.items():
                    bylink[r[0]][vid]=r
                    loc=observer.locate(r)
                    if loc and loc[0]=='FW_E':positions[vid]=loc
                if previous is not None:
                    for o,p in ports.items():
                        now=bylink[o];old={v:r for v,r in previous.items() if r[0]==o}
                        added=set(now)-set(old);left=set(old)-set(now)
                        for v in added:seen['arrival'].add((t,v,o));flows[t,o,now[v][1],'off_entry']+=1
                        for v in left:seen['departure'].add((t,v,o))
                        for lane in range(1,int(p['lanes'])+1):
                            delta=sum(r[1]==lane for r in now.values())-sum(r[1]==lane for r in old.values())
                            boundary=sum(now[v][1]==lane for v in added)-sum(old[v][1]==lane for v in left)
                            lateral=sum(int(now[v][1]==lane)-int(old[v][1]==lane) for v in set(now)&set(old))
                            assert delta==boundary+lateral
                            checks+=1
                        for vid,r in previous.items():
                            if r[0]!=p['from_link'] or not p['from_pos_m']-100<=r[2]<=p['from_pos_m']:continue
                            if vid in positions and positions[vid][2]>p['chain_pos_m']:
                                flows[t,o,r[1],'through']+=1
                for o,p in ports.items():
                    for lane in range(1,len(links[p['from_link']].findall('./lanes/lane'))+1):
                        approach=sorted((p['from_pos_m']-r[2],r[3]) for r in bylink[p['from_link']].values()
                                        if r[1]==lane and p['from_pos_m']-100<=r[2]<=p['from_pos_m'])
                        offlane=access[o].get(lane)
                        off=sorted((r[2],r[3]) for r in bylink[o].values() if r[1]==offlane)
                        chain=[];gap=0.
                        for distance,speed in approach:
                            if speed>=5 or distance-gap>20:break
                            chain.append(distance);gap=distance
                        row=dict(time_s=t,connector=o,mainline_lane=lane,off_lane=offlane or 0,
                            main_n=len(approach),main_stopped=sum(v<5 for _,v in approach),
                            main_v=sum(v for _,v in approach)/len(approach) if approach else None,
                            stopped_chain_n=len(chain),stopped_chain_extent_m=max(chain,default=0.),
                            off_n=len(off),off_stopped=sum(v<5 for _,v in off),
                            off_entry_stopped6=bool(off and off[0][0]<6 and off[0][1]<5),
                            off_entry_stopped10=bool(off and off[0][0]<10 and off[0][1]<5),
                            off_first_position_m=off[0][0] if off else None)
                        row['connected_queue_candidate']=row['off_entry_stopped10'] and len(chain)>=3
                        rows.append(row)
                    if t%10==0:
                        for group in range(3):
                            vehicles=[frame[v] for v,loc in positions.items() if loc[1]==p['from_cell']
                                      and (min(frame[v][1],3)-1)==group]
                            group_rows.append(dict(time_s=t,connector=o,cell=p['from_cell'],group=group,n=len(vehicles),
                                v=sum(r[3] for r in vehicles)/len(vehicles) if vehicles else None))
                for lane in range(1,6):
                    current=[r for r in bylink[71].values() if r[1]==lane]
                    urban.append(dict(time_s=t,lane=lane,n=len(current),stopped=sum(r[3]<5 for r in current)))
                previous=frame;last=t
            assert last==end and seen==expected,(seed,arm,'off-ramp transitions differ', {k:len(seen[k]^expected[k]) for k in expected})
            after=path.stat();assert (stat.st_size,stat.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
            for r in rows:
                t=r['time_s'];o=r['connector'];lane=r['mainline_lane'];offlane=r['off_lane']
                r['next1s_through']=flows[t+1,o,lane,'through'] if t<end else None
                r['next1s_off_entry']=flows[t+1,o,offlane,'off_entry'] if offlane and t<end else None
                r['next10s_through']=sum(flows[u,o,lane,'through'] for u in range(t+1,t+11)) if t+10<=end else None
                r['next10s_off_entry']=sum(flows[u,o,offlane,'off_entry'] for u in range(t+1,t+11)) if offlane and t+10<=end else None
            for label,values in [('lanes',rows),('urban71',urban),('groups',group_rows)]:
                with (out/f's{seed}_{arm}_{label}.csv').open('x',encoding='utf-8',newline='') as f:
                    writer=csv.DictWriter(f,fieldnames=list(values[0]));writer.writeheader();writer.writerows(values)
            summary={}
            for o,p in ports.items():
                summary[str(o)]={}
                for lane in range(1,len(links[p['from_link']].findall('./lanes/lane'))+1):
                    selected=[r for r in rows if r['connector']==o and r['mainline_lane']==lane and r['time_s']<end]
                    states={}
                    for label,condition in [('all',lambda r:True),('off_entry_stopped10',lambda r:r['off_entry_stopped10']),
                         ('connected_queue_candidate',lambda r:r['connected_queue_candidate'])]:
                        sample=[r for r in selected if condition(r)]
                        states[label]=dict(seconds=len(sample),mean_main_n=statistics.mean(r['main_n'] for r in sample) if sample else None,
                            mean_main_stopped=statistics.mean(r['main_stopped'] for r in sample) if sample else None,
                            mean_main_speed=statistics.mean(r['main_v'] for r in sample if r['main_v'] is not None) if any(r['main_v'] is not None for r in sample) else None,
                            through_next1s=sum(r['next1s_through'] for r in sample),off_entry_next1s=sum(r['next1s_off_entry'] or 0 for r in sample),
                            next1s_with_any_crossing=sum(r['next1s_through']>0 or (r['next1s_off_entry'] or 0)>0 for r in sample),
                            next10s_with_any_crossing=sum((r['next10s_through'] or 0)>0 or (r['next10s_off_entry'] or 0)>0 for r in sample if r['next10s_through'] is not None),
                            next10s_evaluable=sum(r['next10s_through'] is not None for r in sample),
                            max_stopped_chain_extent_m=max((r['stopped_chain_extent_m'] for r in sample),default=0.))
                    summary[str(o)][str(lane)]=states
            results[f'{seed}_{arm}']=dict(ports=summary,normal_lane_conservation_checks=checks,
                urban71={str(l):dict(mean_n=statistics.mean(r['n'] for r in urban if r['lane']==l and r['time_s']>start),
                    mean_stopped=statistics.mean(r['stopped'] for r in urban if r['lane']==l and r['time_s']>start)) for l in range(1,6)},
                source=str(path.relative_to(e.ROOT)),source_bytes=stat.st_size,source_mtime_ns=stat.st_mtime_ns,
                historical_source_sha256=manifest['fzp']['file_sha256'],file_unchanged_during_partial_read=True,
                off_events_exact=True,partial_read_evidence=evidence)
            for f in [data.folder/'manifest.json',data.folder/'geometry.json',data.folder/'port_events.csv']:
                source_pins[str(f.relative_to(e.ROOT))]=hashlib.sha256(f.read_bytes()).hexdigest()
            e.save(out/f's{seed}_{arm}.json',results[f'{seed}_{arm}'])
            print('LANE_BLOCKING_COMPLETE',seed,arm,checks,{o:{l:s['connected_queue_candidate']['seconds'] for l,s in v.items()} for o,v in summary.items()},flush=True)
    e.save(out/'result.json',dict(results=results,source_pins=source_pins,code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        interval_s=[start,end],new_native_runs=0,model_parameters_changed=False,
        definition='Off-ramp first vehicle front within10m at<5km/h, and at least3 consecutive stopped vehicles on the geometrically connected mainline lane within100m upstream, with front-to-front gaps<=20m from the branch. This is a connected-queue candidate, not a proved closed lane.',
        limit='Positive actual passage can refute a frozen zero-throughput mask; zero passage does not prove zero capacity or observed demand. Rolling windows overlap. Numeric thresholds are measurement definitions, not fitted plant parameters. No vehicle cost or storage is removed.',
        literature='https://escholarship.org/uc/item/59x2m66n'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--blocking',action='store_true');args=parser.parse_args()
    blocking_audit() if args.blocking else main()
