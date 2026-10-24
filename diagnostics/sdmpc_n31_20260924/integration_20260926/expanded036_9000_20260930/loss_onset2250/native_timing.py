"""Retrospective native event matching; these future events never enter a predictor."""
import collections
import hashlib
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
D = Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
pins = {}
results = {}
for start in (2250, 3600):
    states, events = {}, []
    for end in (start, start+150, start+300):
        path = D/f'state_{end:06d}.json'
        data = path.read_bytes(); pins[str(path)] = hashlib.sha256(data).hexdigest()
        states[end] = json.loads(data)
        meta = states[end]['obs150']['mer']; path = D/meta['chunk']
        data = path.read_bytes(); pins[str(path)] = hashlib.sha256(data).hexdigest()
        assert pins[str(path)] == meta['chunk_sha256']
        events.extend(row for line in data.decode('utf-8').splitlines()
                      if (row:=json.loads(line))[2] is not None)
    initial = {r['veh_no']:r for r in states[start]['vehicle_records']['records']}
    by_vehicle = collections.defaultdict(list)
    for row in events:
        by_vehicle[row[4]].append(row)
    arrivals = [r for r in events if r[1] == 960271 and start <= r[2] < start+150]
    details = []
    for row in arrivals:
        head = next((h for h in by_vehicle[row[4]] if h[1] == 960220 and h[2] > row[2]), None)
        upstream = [h for h in by_vehicle[row[4]] if h[1] in range(960158,960167) and h[2] < row[2]]
        record = initial.get(row[4], {})
        details.append(dict(vehicle=row[4],arrival_sec=row[2],initial_link=record.get('link_no'),
            initial_position_m=record.get('position_m'),head_sec=head[2] if head else None,
            arrival_to_head_sec=head[2]-row[2] if head else None,
            upstream_events=[dict(dcp=h[1],time=h[2],to_ramp_sec=row[2]-h[2]) for h in upstream]))
    delays = [r['arrival_to_head_sec'] for r in details if r['arrival_to_head_sec'] is not None]
    def count(dcp, a, b):
        return sum(r[1] in dcp and a <= r[2] < b for r in events)
    bins = [dict(start=t,end=t+30,arrival=count([960271],t,t+30),head=count([960220],t,t+30),
                 road29_straight_head=count([960158,960159],t,t+30),road40_left_head=count([960164],t,t+30))
            for t in range(start,start+150,30)]
    initial_head = []
    for vehicle,row in initial.items():
        if row['link_no'] != 10484 or row['position_m'] >= 377.1107628548054:
            continue
        head = next((h for h in by_vehicle[vehicle] if h[1] == 960220 and h[2] >= start),None)
        initial_head.append(dict(vehicle=vehicle,remaining_m=377.1107628548054-row['position_m'],
            initial_speed_kmh=row['speed_kph'],actual_delay_sec=head[2]-start if head else None))
    results[str(start)] = dict(bins=bins,arrival_cohort=details,initial_prehead=initial_head,
        travel=dict(cohort_size=len(details),matched_head=len(delays),right_censored=len(details)-len(delays),
                    followup_end=start+300,median_sec=statistics.median(delays) if delays else None,
                    min_sec=min(delays) if delays else None,max_sec=max(delays) if delays else None),
        note='Observed cohort travel includes any waiting; not free-flow speed calibration. Missing upstream matches are not zero flows;37 right-turn diverges before its head detectors.')
out = dict(purpose='Post-run diagnosis only; no future observations supplied to forecasts',states=results,pins=pins)
(HERE/'speed_binding/native_timing.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({t:dict(travel=r['travel'],road29=sum(b['road29_straight_head'] for b in r['bins']),
    road40=sum(b['road40_left_head'] for b in r['bins'])) for t,r in results.items()}))
