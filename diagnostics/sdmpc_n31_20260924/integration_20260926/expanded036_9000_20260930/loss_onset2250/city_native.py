"""Retrospective native head-to-head cohorts, never forecast inputs."""
import collections
import csv
import hashlib
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
D = Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
pins = {}


def read(path):
    data = path.read_bytes()
    pins[str(path)] = hashlib.sha256(data).hexdigest()
    return data


results = {}
for start in (2250, 3600):
    states = {t:json.loads(read(D/f'state_{t:06d}.json'))
              for t in (start-150,start,start+150,start+300)}
    initial = {r['veh_no']:r for r in states[start]['vehicle_records']['records']}
    config = states[start]['obs150']['detector_config']
    rows = list(csv.DictReader(read(Path(config['path'])).decode('utf-8-sig').splitlines()))
    assert pins[config['path']] == config['sha256']
    detectors = {int(r['dcp_no']):r for r in rows}
    assert {detectors[k]['link'] for k in (960158,960159)} == {'29'}
    assert {detectors[k]['link'] for k in (960172,960173)} == {'329'}
    events = []
    for state in states.values():
        meta = state['obs150']['mer']
        data = read(D/meta['chunk'])
        assert pins[str(D/meta['chunk'])] == meta['chunk_sha256']
        events.extend(row for line in data.decode('utf-8').splitlines()
                      if (row:=json.loads(line))[2] is not None)
    by_vehicle = collections.defaultdict(list)
    for row in sorted(events,key=lambda r:r[2]):
        by_vehicle[row[4]].append(row)
    downstream = [r for r in events if r[1] in (960158,960159) and start <= r[2] < start+150]
    upstream = [r for r in events if r[1] in (960172,960173) and start <= r[2] < start+150]
    cohorts = []
    for r in downstream:
        earlier = [p for p in by_vehicle[r[4]] if p[1] in (960172,960173) and p[2] < r[2]]
        prev = earlier[-1] if earlier else None
        cohorts.append(dict(vehicle=r[4],downstream_sec=r[2],upstream_sec=prev[2] if prev else None,
            elapsed_sec=r[2]-prev[2] if prev else None,initial=initial.get(r[4])))
    lag = [r['elapsed_sec'] for r in cohorts if r['elapsed_sec'] is not None]
    initial329 = [r for r in initial.values() if r['link_no']==329]
    initial29 = [r for r in initial.values() if r['link_no']==29]
    initial329_lanes = {}
    for lane in sorted({r['lane_no'] for r in initial329}):
        vehs = [r for r in initial329 if r['lane_no']==lane]
        departed = [r for r in vehs if any(p[1] in (960172,960173) and start<=p[2]<start+150
                                            for p in by_vehicle[r['veh_no']])]
        initial329_lanes[lane] = dict(count=len(vehs),stopped=sum(r['stopped'] for r in vehs),
            through_departed150=len(departed))
    bins = []
    for a in range(start,start+150,30):
        bins.append(dict(start=a,end=a+30,upstream329=sum(a<=r[2]<a+30 for r in upstream),
            downstream29=sum(a<=r[2]<a+30 for r in downstream)))
    signals = states[start+150]['obs150']['signal_log']
    transitions = [r for r in signals['events'] if (r[1],r[2]) in (('1001','6'),('1002','6'))]
    results[start] = dict(native_upstream329=len(upstream),native_downstream29=len(downstream),
        head_to_head=dict(matched=len(lag),unmatched=len(cohorts)-len(lag),
            median=statistics.median(lag),min=min(lag),max=max(lag),
            note='Includes travel, any queueing and red delay; retrospective conditional cohort, not a free-flow calibration'),
        cohorts=cohorts,initial329_lanes=initial329_lanes,initial29=initial29,bins=bins,
        signal_start={k:v for k,v in signals['start'].items() if k in ('1001-6','1002-6')},
        signal_transitions=transitions,
        local_initial_speed={k:v for k,v in states[start]['local_observation']['link_speeds_kph'].items()
                             if k in ('29','329','10690','10691')})
out = dict(purpose='Retrospective completed-run diagnosis; no future records fed to model',results=results,pins=pins)
(HERE/'city_path/native.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({t:{k:v for k,v in r.items() if k in ('native_upstream329','native_downstream29',
    'head_to_head','initial329_lanes','signal_transitions','local_initial_speed')} for t,r in results.items()},ensure_ascii=False))
