"""Separate observed green-start lag, head-to-link-exit lag and terminal censoring."""
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

D = Path(__file__).resolve().parent
ROOT = D.parents[3]
sys.path[:0] = [str(ROOT), str(ROOT/'reports/20260911_decision_runtime')]
import audit_fw8_rg_meter_response as meters


def main():
    output = D/(sys.argv[1]+'.json')
    if output.exists():
        raise FileExistsError(output)
    started = time.perf_counter()
    meters.END = 1350
    paths = [Path(__file__), D/'fast_np_native_qualification_v1.json', D/'fast_np_sc1004_arrivals450_v1.json']
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    pins = {str(p):sha(p) for p in paths}
    signals = json.loads(paths[1].read_text(encoding='utf-8'))['sc1004']
    roads = json.loads(paths[2].read_text(encoding='utf-8'))
    report = {'completed':False, 'arms':{}, 'source_sha256':pins,
        'scope':'One-second native SG6 head events, same-vehicle road52 exits, and pre-green queues. Observed first crossing lag is not fitted saturation startup lost time. No capacity equivalence or eventual recovery claim.'}
    for label,name in (('baseline','codex_physical8_fw080_u050_open1350_v1'),
                       ('selected','codex_physical8_fw080_u050_fastnp_1350_v2')):
        run = meters.load_run(name)
        pins.update(run['pins'])
        signal = signals[label]
        crossings = [r for r in signal['head_crossings'] if r['sg']==6]
        exits = [r for r in roads[label]['transitions'] if r['from_link']==52]
        events=[]
        for head in crossings:
            matches = [r for r in exits if r['vehicle']==head['vehicle'] and r['interval_sec'][1]>=head['interval_sec'][1]]
            assert len(matches)<=1
            events.append({'vehicle':head['vehicle'], 'head_interval_sec':head['interval_sec'],
                'exit_interval_sec':matches[0]['interval_sec'] if matches else None,
                'exit_minus_head_sample_sec':matches[0]['interval_sec'][1]-head['interval_sec'][1] if matches else None})
        windows=[]
        for green in signal['native_green_windows']['6']:
            start,end=green['first_native_green_frame_sec'],green['last_native_green_frame_sec']
            departures=[r for r in crossings if start<=r['interval_sec'][1]<=end+1]
            amber=[r for r in crossings if end+1<r['interval_sec'][1]<=end+4]
            relative=[r['interval_sec'][1]-start for r in departures]
            windows.append({**green, 'observed_head_departure_lags_sec':relative,
                'head_count_green_and_transition':len(departures), 'amber_tail_head_count':len(amber),
                'first_head_sample_lag_sec':min(relative) if relative else None,
                'cumulative_by_green_age_sec':{str(t):sum(x<=t for x in relative) for t in (1,5,10,20,30,44,45)},
                'first_vehicles':departures[:3]})
        targets={w['first_native_green_frame_sec']-1 for w in windows}
        snapshots={}
        reader=meters.IndexedFzp(run['fzp'],max_bytes=80*1024*1024)
        try:
            for sec,frame in meters.WINDOWS.frames(reader,900,1350):
                if sec not in targets:
                    continue
                lanes={}
                for lane in (1,2,3):
                    pos=signal['head_geometry'][f'52:{lane}'][1]
                    vehicles=[(vid,row) for vid,row in frame.items() if row[0]==52 and row[1]==lane and row[2]<pos]
                    lead=max(vehicles,key=lambda item:item[1][2]) if vehicles else None
                    lanes[str(lane)]={'upstream_n':len(vehicles),
                        'stopped_lt5':sum(row[3]<5 for _,row in vehicles),
                        'stopped_within20m':sum(row[3]<5 and pos-row[2]<=20 for _,row in vehicles),
                        'front_vehicle':{'vehicle':lead[0],'distance_to_head_m':pos-lead[1][2],'speed_kmh':lead[1][3]} if lead else None}
                snapshots[str(sec)]=lanes
        finally:
            reader.handle.close()
        assert set(map(int,snapshots))==targets
        delays=[e['exit_minus_head_sample_sec'] for e in events if e['exit_minus_head_sample_sec'] is not None]
        report['arms'][label]={'green_windows':windows, 'pre_green_lane_snapshots':snapshots,
            'matched_head_and_exit_events':events,
            'head_to_exit_lag_sec':{'n':len(delays),'min':min(delays),'median':statistics.median(delays),'max':max(delays)},
            'head_events_without_exit_in_window':len(events)-len(delays),
            'fzp_bounded_read':reader.selected}
    report['terminal_comparison_limit']='Selected SG6 opens again at1350, exactly at run end; subsequent queue discharge is unobserved. Last90s zero exits occurs during RED, not failed GREEN service.'
    report['source_changes']=[p for p,h in pins.items() if sha(Path(p))!=h]
    report['completed']=not report['source_changes']
    report['wall_sec']=time.perf_counter()-started
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('completed','wall_sec','source_changes')}))
    for arm,v in report['arms'].items():
        print(arm, 'head_to_exit',v['head_to_exit_lag_sec'])
        for w in v['green_windows']:
            p=v['pre_green_lane_snapshots'][str(w['first_native_green_frame_sec']-1)]
            print(w['first_native_green_frame_sec'],w['first_head_sample_lag_sec'],w['cumulative_by_green_age_sec'],
                  'initial_upstream',sum(x['upstream_n'] for x in p.values()),'stopped',sum(x['stopped_lt5'] for x in p.values()))


if __name__=='__main__':
    try:
        main()
    except Exception:
        import traceback
        failure=D/(sys.argv[1]+'.failed.json')
        failure.write_text(json.dumps({'completed':False,'error':traceback.format_exc()},indent=2)+'\n',encoding='utf-8')
        raise
