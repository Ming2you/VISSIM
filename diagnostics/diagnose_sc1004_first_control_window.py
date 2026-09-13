"""Bounded observational SC1004/SC1001 path diagnosis; no model or COM access."""
from bisect import bisect_right
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from diagnostics.probe_e8_lane_receiving import IndexedFzp
from diagnostics.probe_e8_window_passages import frames
from diagnostics.selected_signal_sampling_audit import geometry, head_events
from diagnostics.audit_observer_control_pair import native_signal_prefix

RUNS = {'NC': 'codex_contract_observed_nc_s13_1050_v2_20260910',
        'beta300': 'codex_contract_beta300_s13_1050_v3_20260910'}
START, END = 900, 1050
ROADS = {2, 120, 121, 123, 126, 69, 70, 71, 56, 57, 75, 46, 66, 47, 67, 68, 387,
         127, 30, 420, 72, 329, 1220007200, 1220006403, 1220007101, 417}
OUT = ROOT / 'diagnostics/sc1004_first_control_window'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def windows(values):
    result = []
    for sec, value in sorted(values.items()):
        if value:
            if result and result[-1][1] == sec:
                result[-1][1] = sec+1
            else:
                result.append([sec, sec+1])
    return result


def clock(run):
    path = run / ('decisions_'+run.name) / 'signal_readback.csv'
    rows = list(csv.DictReader(path.open(encoding='utf-8-sig')))
    actual = defaultdict(dict)
    for row in rows:
        sec = float(row['sim_sec'])
        if START <= sec <= END and row['stage'] in ('immediate', 'post_step'):
            key = row['sc_no'], row['sg_no'], row['stage']
            if row['ok'] != '1':
                raise ValueError('Failed actual signal readback')
            if sec in actual[key] and row['readback_state'] != actual[key][sec]:
                raise ValueError('Conflicting same-time signal rows')
            actual[key][sec] = row['readback_state'].upper()
    native = native_signal_prefix(next(run.glob('vissim_eval/*.lsa')), END)
    def state(sc, sg, sec, stage='immediate'):
        key = str(sc), str(sg), stage
        if key in actual:
            if sec not in actual[key]:
                raise ValueError('Missing requested actual SG second')
            return actual[key][sec]
        events = native['groups'].get(f'{sc}:{sg}', [])
        i = bisect_right([r[0] for r in events], sec)-1
        if i < 0:
            raise ValueError('Native SG initial state unknown')
        return events[i][1]
    return state, {'readback_path': str(path), 'readback_sha256': sha(path),
                   'native_lsa': {k:v for k,v in native.items() if k != 'groups'}}


def analyze(label, name, geo, links, watched):
    run = ROOT / 'evaluation/runs' / name
    if b'STAGE=SIM_DONE' not in (run / ('runlog_'+name+'.txt')).read_bytes():
        raise ValueError('Completed run required')
    state_at, signal_proof = clock(run)
    path = next(run.glob('vissim_eval/*.fzp'))
    before = path.stat()
    reader = IndexedFzp(path, max_bytes=64*1024*1024)
    provenance = []
    selected, head_rows, entries, exits = {}, [], [], []
    last = None
    try:
        for sec, current in frames(reader, START, END, time.monotonic()+45, provenance):
            selected[int(sec)] = {no: row for no,row in current.items() if row[0] in watched}
            if last is not None:
                t0, old = last
                for no, row in old.items():
                    if row[0] in (71,127,30):
                        for event in head_events(geo[str(row[0])], no, row, current.get(no), t0, sec):
                            if event['kind'] == 'head_crossing':
                                event['qualified_green'] = (state_at(event['SC'],event['sg'],int(t0)) == 'GREEN'
                                    and state_at(event['SC'],event['sg'],int(sec),'post_step') == 'GREEN')
                            head_rows.append(event)
                    if row[0] in ROADS and (no not in current or row[0] != current[no][0]):
                        exits.append({'vehicle':no,'link':row[0],'from_pos':row[2], 'lower_sec':t0,'upper_sec':sec,
                            'to':None if no not in current else current[no][0]})
                for no,row in current.items():
                    if row[0] in ROADS and (no not in old or old[no][0] != row[0]):
                        entries.append({'vehicle':no,'link':row[0],'lane':row[1],'pos':row[2],
                            'lower_sec':t0,'upper_sec':sec,'from':None if no not in old else old[no][0]})
            last = sec, current
        bytes_read = reader.bytes_read
    finally:
        reader.handle.close()
    if sorted(selected) != list(range(START,END+1)):
        raise ValueError('Incomplete one-second FZP interval')
    if (before.st_size,before.st_mtime_ns) != (path.stat().st_size,path.stat().st_mtime_ns):
        raise ValueError('Completed FZP changed')
    cache = OUT / (label+'_selected_frames.json.gz')
    with gzip.open(cache,'wt',encoding='utf-8') as stream:
        json.dump(selected,stream,separators=(',',':'))
    tracks = defaultdict(list)
    for sec, rows in selected.items():
        for no,row in rows.items():
            tracks[no].append([sec,*row])
    lane_heads = {h['lane']:h['pos_m'] for h in geo['71']['heads']}
    timeseries = []
    for sec, records in selected.items():
        road71 = [r for r in records.values() if r[0] == 71]
        row = {'sec':sec,'71_count':len(road71),'71_stopped':sum(r[3]<=1 for r in road71)}
        for lane in range(1,6):
            group = '2' if lane<=3 else '5'
            before_head = [r for r in road71 if r[1]==lane and r[2] <= lane_heads[lane]]
            near = [r for r in before_head if r[2]>=lane_heads[lane]-20]
            row.update({f'lane{lane}_prehead_n':len(before_head),f'lane{lane}_near20_n':len(near),
                f'lane{lane}_near20_stopped':sum(r[3]<=1 for r in near),
                f'lane{lane}_front_dist_m':min((lane_heads[lane]-r[2] for r in before_head),default=None)})
        for sg in ('2','5'):
            row[f'SG{sg}_green'] = int(state_at('1004',sg,sec,'post_step' if sec==END else 'immediate')=='GREEN')
        for link in (10634,56,57,126,70,123,127,30,420,1220007200):
            group = [r for r in records.values() if r[0]==link]
            row[f'{link}_n'] = len(group);row[f'{link}_stopped'] = sum(r[3]<=1 for r in group)
            if link == 56:
                for lane in range(1,5):
                    near = [r for r in group if r[1]==lane and r[2]<50]
                    row[f'56_lane{lane}_first50_n']=len(near)
                    row[f'56_lane{lane}_first50_stopped']=sum(r[3]<=1 for r in near)
        timeseries.append(row)
    with (OUT/(label+'_timeseries.csv')).open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(timeseries[0]));writer.writeheader();writer.writerows(timeseries)
    clock_groups = [('1004','2'),('1004','5'),('1001','2'),('1002','2'),('1002','5'),('105','4'),('105','7')]
    clocks = {f'{sc}:{sg}': windows({t:state_at(sc,sg,t)=='GREEN' for t in range(START,END)}) for sc,sg in clock_groups}
    summary = {}
    for sg,lanes in [('2',(1,2,3)),('5',(4,5))]:
        green = [row for row in timeseries[:-1] if row[f'SG{sg}_green']]
        events = [e for e in head_rows if e['kind']=='head_crossing' and e.get('SC')=='1004' and e.get('sg')==sg]
        summary[sg] = {'green_sec':len(green),'head_crossings':len(events),
            'qualified_head_crossings':sum(e['qualified_green'] for e in events),
            'crossings_by_lane':dict(Counter(e['lane_before'] for e in events)),
            'green_seconds_no_prehead_vehicle':sum(not any(row[f'lane{lane}_prehead_n'] for lane in lanes) for row in green),
            'green_seconds_no_vehicle_last20m':sum(not any(row[f'lane{lane}_near20_n'] for lane in lanes) for row in green),
            'green_seconds_any_stopped_last20m':sum(any(row[f'lane{lane}_near20_stopped'] for lane in lanes) for row in green),
            'green_first50_downstream56_max_stopped':max((sum(row[f'56_lane{lane}_first50_stopped'] for lane in lanes if lane<=4) for row in green),default=0)}
    # Full physical histories are retained for the small selected-road cohort;
    # never infer an unobserved earlier native route from current lane or ID.
    arrivals71 = []
    for event in entries:
        if event['link'] != 71:continue
        seen = [r for r in tracks[event['vehicle']] if r[0] <= event['upper_sec']]
        path_seen = [r[1] for i,r in enumerate(seen) if i==0 or r[1] != seen[i-1][1]]
        family = ('FW_E_signal_10643' if 10643 in path_seen else
                  'FW_W_off_10638' if 10638 in path_seen else
                  'urban69_10640' if 10640 in path_seen else
                  'urban69_via70' if 10637 in path_seen else 'earlier_origin_not_observed')
        future = [e for e in exits if e['vehicle']==event['vehicle'] and e['link']==71 and e['lower_sec']>=event['lower_sec']]
        arrivals71.append({**event,'observed_path':path_seen,'origin_evidence':family,'next71_exits':future})
    terminal420 = [no for no,row in selected[END].items() if row[0]==420 and row[3]<=1]
    end71 = [no for no,row in selected[END].items() if row[0]==71 and row[3]<=1]
    histories = {}
    for group, ids in [('end420_stopped',terminal420),('end71_stopped',end71)]:
        histories[group] = [{'vehicle':no,'samples':tracks[no],
            'visited127_in_window':any(r[1]==127 for r in tracks[no]),
            'first_stopped_sec_by_link':{str(link):min(r[0] for r in tracks[no] if r[1]==link and r[4]<=1)
                for link in {r[1] for r in tracks[no] if r[4]<=1}}} for no in ids]
    payload = {'run':name,'signal_proof':signal_proof,'fzp':{'path':str(path),'size':before.st_size,
        'mtime_ns':before.st_mtime_ns,'read_bytes':bytes_read,'selected_ranges':provenance,
        'selected_cache':str(cache),'selected_cache_sha256':sha(cache)},'green_windows':clocks,
        'sg71_summary':summary,'road_entries':entries,'road_exits':exits,'head_events':head_rows,
        'arrivals71':arrivals71,'selected_endpoint_histories':histories,
        'endpoint71':{str(t):[{'vehicle':no,'record':row} for no,row in selected[t].items() if row[0]==71] for t in (START,END)}}
    return payload


def main():
    if OUT.exists():raise ValueError('Preserve existing diagnostic directory; do not overwrite')
    OUT.mkdir()
    network=ROOT/'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
    tree=ET.parse(network).getroot();links={n.get('no'):n for n in tree.findall('./links/link')}
    watched=set(ROADS)
    for key,node in links.items():
        a,b=node.find('fromLinkEndPt'),node.find('toLinkEndPt')
        if a is not None and (int(a.get('lane').split()[0]) in ROADS or int(b.get('lane').split()[0]) in ROADS):
            watched.add(int(key))
    result={'schema':'sc1004-first-control-window/v1','window':[START,END],
        'network_sha256':sha(network),'producer_sha256':sha(__file__),
        'head_geometry':geometry(network),'selected_links':sorted(watched),'runs':{},
        'scope':['Observed association across a joint green/offset intervention; VSL and meters are unchanged.',
            'FZP crossings are conservative one-second brackets, separate from COM head-qualified counters.',
            'Green with no pre-head vehicle or an empty downstream 50m is sampled evidence, not a certified saturation/receiving capacity.',
            'No hidden pre-900 origin is inferred. End420 stopped cohorts are traced only in this 150-second observed window.']}
    for label,name in RUNS.items():result['runs'][label]=analyze(label,name,result['head_geometry'],links,watched)
    (OUT/'diagnosis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:{'sg71':v['sg71_summary'],'green':v['green_windows'],
                        'read_bytes':v['fzp']['read_bytes'],'end420_stopped':len(v['selected_endpoint_histories']['end420_stopped'])}
                      for k,v in result['runs'].items()},ensure_ascii=False))


if __name__=='__main__':main()
