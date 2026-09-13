"""Completed-run 150-second NUF-band audit using existing native readers."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(Path(__file__).resolve().parent)]
import audit_fw8_rg_meter_response as meters
from diagnostics.com_execution_equivalence.verify_pair import fzp_comparison
from diagnostics.validate_native_signal_record import read_ldp_frames


def signal_window(run, *, sc=5, start=900, end=1050, max_bytes=80*1024*1024):
    network=Path(run['provenance']['files']['network']['path'])
    doc=ET.parse(network).getroot()
    heads={tuple(map(int,h.get('lane').split())):(int(h.get('sg').split()[1]),float(h.get('pos')))
        for h in doc.iter('signalHead') if h.get('sg','').split()[0]==str(sc)
        and 1<=int(h.get('sg').split()[1])<=8}
    roads={link for link,lane in heads}
    connections={}
    for link in doc.findall('./links/link'):
        src=link.find('fromLinkEndPt')
        if src is not None and int(src.get('lane').split()[0]) in roads:
            connections[int(link.get('no'))]=(int(src.get('lane').split()[0]),float(src.get('pos')))
    ldp_path=run['directory']/f'vissim_eval/baseline_{sc}_001.ldp'
    ldp=read_ldp_frames({sc:ldp_path},{sc:list(range(1,9))},start-1,end)['frames']
    groups={sg:Counter() for sg in range(1,9)}
    bins={t:{sg:Counter() for sg in groups} for t in range(start,end,30)}
    road_stats={link:Counter() for link in roads}
    events=[];previous=None
    reader=meters.IndexedFzp(run['fzp'],max_bytes=max_bytes)
    try:
        for sec,current in meters.WINDOWS.frames(reader,start,end):
            if previous is None:
                for link in roads:road_stats[link]['initial_n']=sum(r[0]==link for r in current.values())
                previous=current;continue
            bucket=bins[start+((sec-start-1)//30)*30]
            for sg in groups:
                for counter in (groups[sg],bucket[sg]):
                    counter['green_samples']+=ldp[sec][f'{sc}:{sg}']=='GREEN'
            for link in roads:
                rows=[r for r in current.values() if r[0]==link]
                stop=sum(r[3]<5 for r in rows);stats=road_stats[link]
                stats['stopped_vehicle_seconds_lt5']+=stop
                stats['max_stopped_lt5']=max(stats['max_stopped_lt5'],stop)
                stats['end_n']=len(rows)
            for no,row in current.items():
                head=heads.get(row[:2])
                old=previous.get(no)
                if head and row[2]<head[1] and row[3]<5:
                    for counter in (groups[head[0]],bucket[head[0]]):
                        counter['upstream_stopped_vehicle_seconds_lt5']+=1
                        if head[1]-row[2]<=20 and ldp[sec][f'{sc}:{head[0]}']=='GREEN':
                            counter['stopped_within20m_during_green_vehicle_seconds']+=1
                if old is not None and row[0]==old[0] and row[0] in roads and row[1]!=old[1]:
                    road_stats[row[0]]['lane_changes']+=1
            for no,old in previous.items():
                head=heads.get(old[:2]);row=current.get(no)
                if not head or old[2]>=head[1] or row is None:continue
                sg,pos=head;kind=None
                if row[0]==old[0] and row[1]==old[1] and row[2]>=pos:kind='same_lane_head_crossing'
                elif row[0] in connections and connections[row[0]][0]==old[0] and connections[row[0]][1]>=pos:
                    kind='continuous_connector_head_crossing'
                if kind:
                    for counter in (groups[sg],bucket[sg]):counter['observed_head_crossings']+=1
                    events.append({'vehicle':no,'interval_sec':[sec-1,sec],'sg':sg,'link':old[0],
                        'left_state':ldp[sec-1][f'{sc}:{sg}'],'right_state':ldp[sec][f'{sc}:{sg}'],'method':kind})
            previous=current
    finally:reader.handle.close()
    windows={sg:meters.green_windows(ldp,f'{sc}:{sg}',start=start,end=end)[0] for sg in groups}
    return {'groups':groups,'bins30s':bins,'road_stats':road_stats,'head_crossings':events,
        'native_green_windows':windows,'head_geometry':{f'{k[0]}:{k[1]}':v for k,v in heads.items()},
        'ldp_sha256':meters.sha(ldp_path),'fzp_bounded_read':reader.selected,
        'scope':f'SC{sc} native SG1..8 heads only; one-second observed same-lane/continuous-connector crossings in({start},{end}]. Missing vehicles, skipped connectors and lane-changing crossing intervals are not inferred. GREEN samples and stopped near-head samples do not establish causal blocking.'}


def corridor_window(run, *, roads, start=900, end=1350, max_bytes=80*1024*1024):
    """Observed link balances, retaining missing/first-seen vehicles separately.

    Road membership is not a destination label. Transitions are counted only
    when the same vehicle exists in both consecutive native one-second frames.
    """
    roads=set(map(int, roads))
    if not roads or end <= start:
        raise ValueError('Require nonempty roads and a positive completed window')
    stats={link:Counter() for link in roads}
    entries={link:Counter() for link in roads}
    exits={link:Counter() for link in roads}
    bins={t:{link:Counter() for link in roads} for t in range(start,end,30)}
    events=[];previous=None
    reader=meters.IndexedFzp(run['fzp'],max_bytes=max_bytes)
    try:
        for sec,current in meters.WINDOWS.frames(reader,start,end):
            counts=Counter(row[0] for row in current.values())
            if previous is None:
                for link in roads:stats[link]['initial_n']=counts[link]
                previous=current;continue
            bucket=bins[start+((sec-start-1)//30)*30]
            for no,row in current.items():
                link=row[0];old=previous.get(no)
                if link not in roads:continue
                if row[3]<5:
                    stats[link]['stopped_vehicle_seconds_lt5']+=1
                    bucket[link]['stopped_vehicle_seconds_lt5']+=1
                if old is None:
                    stats[link]['first_appearances']+=1
                    bucket[link]['first_appearances']+=1
                elif old[0]!=link:
                    stats[link]['observed_entries']+=1
                    bucket[link]['observed_entries']+=1
                    entries[link][old[0]]+=1
                elif old[1]!=row[1]:stats[link]['lane_changes']+=1
            for no,old in previous.items():
                row=current.get(no);link=old[0]
                if row is not None and row[0]!=link and (link in roads or row[0] in roads):
                    events.append({'vehicle':no,'interval_sec':[sec-1,sec],
                        'from_link':link,'to_link':row[0],
                        'from_lane':old[1],'to_lane':row[1]})
                if link not in roads:continue
                if row is None:
                    stats[link]['unexplained_absences']+=1
                    bucket[link]['unexplained_absences']+=1
                elif row[0]!=link:
                    stats[link]['observed_exits']+=1
                    bucket[link]['observed_exits']+=1
                    exits[link][row[0]]+=1
            for link in roads:
                s=stats[link]
                balance=(s['initial_n']+s['observed_entries']+s['first_appearances']
                    -s['observed_exits']-s['unexplained_absences']-counts[link])
                if balance:raise ValueError(f'Native link balance failure at {sec}: {link}')
                s['end_n']=counts[link]
                s['max_n']=max(s['max_n'],counts[link])
            previous=current
    finally:reader.handle.close()
    return {'window_sec':[start,end],'links':stats,'entries_by_previous_link':entries,
        'exits_by_next_link':exits,'bins30s':bins,'transitions':events,
        'all_link_frame_balances_zero':True,'fzp_bounded_read':reader.selected,
        'scope':'Observed link entries/exits in consecutive one-second FZP frames. '
            'First appearances and unexplained absences are separate; no desired '
            'ramp demand or terminal exit is inferred from approach membership.'}


def main():
    target=Path(sys.argv[1]).resolve()
    if target.exists():raise FileExistsError(target)
    start=time.perf_counter();report={'completed':False}
    try:
        candidate=sys.argv[2] if len(sys.argv)>2 else 'codex_physical8_fw080_u050_band5_replay_v1'
        runs=[meters.load_run(name) for name in ('codex_native_clock_fw080_u050_open_v2',candidate)]
        for key in ('network','demand_profile'):
            assert runs[0]['provenance']['files'][key]['sha256']==runs[1]['provenance']['files'][key]['sha256']
        assert all(r['provenance']['seed']==13 for r in runs)
        report['runs']=[{'meters':meters.collect(r),'sc5':signal_window(r)} for r in runs]
        report['full_fzp_comparison']=fzp_comparison(runs[0]['fzp'],runs[1]['fzp'],1,1050)
        first=report['full_fzp_comparison']['first_difference']
        report['warmup_fzp_rows_exact_through900']=not first or (float(first['left_sec'])>900 and float(first['right_sec'])>900)
        assert report['warmup_fzp_rows_exact_through900']
        report['source_pins']={str(Path(__file__)):meters.sha(__file__),**runs[0]['pins'],**runs[1]['pins']}
        report['completed']=True
    except Exception:
        import traceback
        report['error']=traceback.format_exc()
    finally:
        report['wall_sec']=time.perf_counter()-start
        with target.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
    print(json.dumps({k:report.get(k) for k in ('completed','wall_sec','error','warmup_fzp_rows_exact_through900')}))
    return 0 if report['completed'] else 1


if __name__=='__main__':raise SystemExit(main())
