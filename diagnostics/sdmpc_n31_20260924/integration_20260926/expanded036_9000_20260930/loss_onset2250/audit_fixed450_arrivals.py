"""Attribute completed fixed-command2250 traffic to urban heads; no rollout."""
import collections
import csv
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
I=HERE.parent.parent
OUT=HERE/'fixed450_arrivals'
OUT.mkdir(exist_ok=False)
D=Path('D:/VISSIM_runs/20261001_onset2250_s29/held_actual/decisions_sdmpc31_g_2250_held_actual_s29')
pins={str(Path(__file__)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
def read(path):
    raw=path.read_bytes();pins[str(path)]=hashlib.sha256(raw).hexdigest()
    return raw
def load(path):
    raw=read(path);return json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)
states={t:load(D/f'state_{t:06d}.json') for t in (2250,2400,2550,2700)}
events=[]
for t,state in states.items():
    meta=state['obs150']['mer'];raw=read(D/meta['chunk'])
    assert pins[str(D/meta['chunk'])]==meta['chunk_sha256']
    events.extend(row for line in raw.decode('utf-8').splitlines() if (row:=json.loads(line))[2] is not None)
config=states[2250]['obs150']['detector_config']
detectors={int(z['dcp_no']):z for z in csv.DictReader(read(Path(config['path'])).decode('utf-8-sig').splitlines())}
assert pins[config['path']]==config['sha256']
groups={'road329_straight':(960172,960173),'road29_straight':(960158,960159),
        'road40_left':(960164,),'ramp_arrival':(960271,),'ramp_head':(960220,)}
for name,ids in groups.items():
    rows=[z for z in events if z[1] in ids and 2250<=z[2]<2700]
    assert len(rows)==len({z[4] for z in rows}),(name,'repeated vehicle')
assert sum(z[1]==960271 and 2250<=z[2]<2700 for z in events)==95
trace=load(HERE/'city_path/2250_ps/trace.json.gz')
init=load(HERE/'city_path/2250_ps/initial.json')
assert not init['future_observation_inputs']
movements={'road329_straight':'movement:SC1002_E_SC101_to_W_SC1001',
           'road29_straight':'movement:SC1001_E_SC1002_to_W_RAMP',
           'road40_left':'movement:SC1001_S_SC1003_to_W_RAMP'}
transfers=trace['transfers']
def model_count(name,a,b):
    if name=='ramp_arrival':return sum(z['vehicles'] for z in transfers if z['target']=='ramp:RM_C10484' and a<=z['start_sec']<b)
    return sum(z['vehicles'] for z in transfers if z['source']==movements[name] and z['target'].startswith('storage:') and a<=z['start_sec']<b)
bins=[]
for a in range(2250,2700,30):
    b=a+30
    bins.append(dict(start=a,end=b,actual={k:sum(z[1] in ids and a<=z[2]<b for z in events) for k,ids in groups.items()},
                     predicted={k:model_count(k,a,b) for k in (*movements,'ramp_arrival')}))
by_vehicle=collections.defaultdict(list)
for row in sorted(events,key=lambda z:z[2]):by_vehicle[row[4]].append(row)
arrivals=[z for z in events if z[1]==960271 and 2250<=z[2]<2700]
initial={z['veh_no']:z for z in states[2250]['vehicle_records']['records']}
native_cohorts=[]
for z in arrivals:
    earlier=[q for q in by_vehicle[z[4]] if q[1] in (960158,960159,960164) and q[2]<z[2]]
    last=earlier[-1] if earlier else None
    source=('road29_straight' if last and last[1] in (960158,960159) else 'road40_left' if last else 'unmatched')
    native_cohorts.append(dict(vehicle=z[4],arrival=z[2],source=source,upstream_time=last[2] if last else None,
                               initial_link=initial.get(z[4],{}).get('link_no')))
native_sources={key:dict(count=sum(z['source']==key for z in native_cohorts),
                         by150=[sum(z['source']==key and t<=z['arrival']<t+150 for z in native_cohorts) for t in range(2250,2700,150)])
                for key in ['road29_straight','road40_left','unmatched']}
native_initial=collections.Counter(z['initial_link'] for z in native_cohorts)
model_sources=collections.defaultdict(lambda:[0.,0.,0.])
for z in transfers:
    if z['target']=='ramp:RM_C10484':model_sources[z['source']][int((z['start_sec']-2250)//150)]+=z['vehicles']
totals={kind:{key:sum(b[kind][key] for b in bins) for key in bins[0][kind]} for kind in ['actual','predicted']}
assert abs(totals['predicted']['ramp_arrival']-sum(sum(v) for v in model_sources.values()))<1e-8
for p,h in pins.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
result=dict(status='complete',bins=bins,totals=totals,native_sources=native_sources,
            native_initial_links={str(k):v for k,v in native_initial.items()},model_sources=dict(model_sources),
            detector_groups={k:[detectors[n] for n in ids] for k,ids in groups.items()},pins=pins,
            future_prediction_inputs=False,new_forecasts=0,new_native=0,
            scope='Fixed2250-2700 native held arm, matched to completed physical-speed candidate trace. Native future matching is retrospective only. Unmatched vehicles are not all one origin.')
(OUT/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'source_executed.py.txt').write_bytes(Path(__file__).read_bytes())
print(json.dumps({k:result[k] for k in ['totals','native_sources','native_initial_links','model_sources']},ensure_ascii=False),flush=True)
