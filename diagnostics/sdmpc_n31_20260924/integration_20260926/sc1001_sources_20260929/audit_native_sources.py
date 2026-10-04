"""One closed FZP scan: observed source of actual10480/10484 arrivals, not forecast inputs."""
from pathlib import Path
import collections
import csv
import gzip
import hashlib
import json
import time

HERE=Path(__file__).resolve().parent; I=HERE.parent; ROOT=I.parents[2]
OLD=ROOT.parent/'control-full-review/diagnostics'
FZP=Path('D:/VISSIM_runs/20260929_seed43_observation2700/nc/vissim_eval/sdmpc31_nc2700_s43_001.fzp')
PORT=OLD/'dsd110_20260923/response_recalibration_20260924/gain_response/seed43/none/port_events.csv'
assert not (HERE/'native_source_audit.json').exists()
events=list(csv.DictReader(PORT.read_text(encoding='utf-8-sig').splitlines()))
targets=[r for r in events if r['connector'] in ('10480','10484') and r['kind']=='arrival'
         and 2250.1<float(r['time_s'])<=2700.1]
ids={r['vehicle'] for r in targets}
watched={'29','37','40','10119','10121','10698','31','78','10703','76','80','84',
         '10721','10723','10726','124','10774','10775','125','10483','10484','10480'}
history=collections.defaultdict(list); samples=[]; names=None
digest=hashlib.sha256(); count=0; started=time.perf_counter(); size=FZP.stat().st_size
with FZP.open('rb') as stream:
    for raw in stream:
        digest.update(raw)
        if raw.startswith(b'$VEHICLE:'):
            names=raw.decode('ascii').strip().split(':',1)[1].split(';')
            ix={k:names.index(k) for k in ('SIMSEC','NO','LANE\\LINK\\NO','LANE\\INDEX','POS','SPEED','ROUTDECNO','ROUTENO','NEXTLINK\\NO')}
            continue
        if names is None:continue
        fields=raw.rstrip(b'\r\n').split(b';');assert len(fields)==len(names)
        count+=1
        vehicle=fields[ix['NO']].strip().decode();link=fields[ix['LANE\\LINK\\NO']].strip().decode()
        if link not in watched and vehicle not in ids:continue
        sec=float(fields[ix['SIMSEC']]);assert sec<=2700.1+1e-6
        row=dict(time=sec,vehicle=vehicle,link=link,lane=int(fields[ix['LANE\\INDEX']]),
            pos=float(fields[ix['POS']]),speed=float(fields[ix['SPEED']]),
            decision=fields[ix['ROUTDECNO']].strip().decode(),route=fields[ix['ROUTENO']].strip().decode(),
            next_link=fields[ix['NEXTLINK\\NO']].strip().decode())
        if link in watched:samples.append(row)
        if vehicle in ids:
            old=history[vehicle]
            # Preserve every five-second sample for target IDs, including native route IDs.
            old.append(row)
assert FZP.stat().st_size==size
classified=[]
for event in targets:
    at=float(event['time_s']); vehicle=event['vehicle']; rows=history[vehicle]
    prior=[r for r in rows if r['time']<=at+1e-7]
    source=[r for r in prior if r['link'] in ('10119','10121','10698','78','10703')]
    label=None
    if source:
        source=source[-1]
        label='SC2001' if source['link'] in ('78','10703') else 'SC1001:'+source['link']
    else:
        source=None
    near=[r for r in rows if abs(r['time']-at)<=5.01]
    assert near, ('Old native port event has no matching current trajectory',event)
    classified.append(dict(event=event,source=label,source_observation=source,near_arrival=near))
counts={r:dict(collections.Counter(x['source'] or 'unresolved' for x in classified if x['event']['connector']==r))
        for r in ('10480','10484')}
with gzip.open(HERE/'local_samples.json.gz','wt',encoding='utf-8') as stream:
    json.dump(dict(local_samples=samples,target_histories=history),stream,separators=(',',':'))
report=dict(seed=43,window_sec=[2250.1,2700.1],sources_by_ramp=counts,arrivals=classified,
    fzp=dict(path=str(FZP),sha256=digest.hexdigest(),size=size,rows=count),
    port_events=dict(path=str(PORT),sha256=hashlib.sha256(PORT.read_bytes()).hexdigest()),
    wall_sec=time.perf_counter()-started,scope='Post-run source diagnosis only; no future forecast inputs',
    limitations=['Five-second frames can skip short connectors; unresolved source labels are not filled by guessed priors.',
                 'Native port events from the matched earlier NC run are checked against current observed trajectories.'])
(HERE/'native_source_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(counts=counts,wall_sec=report['wall_sec'],rows=count,local_samples=len(samples))))
