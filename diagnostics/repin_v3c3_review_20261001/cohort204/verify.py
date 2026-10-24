"""Rejoin retained point measurements and audit endpoint-route conclusions."""
import ast
import csv
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    summary=read(HERE/'summary.json');checks=0
    for p,d in summary['input_sha256'].items():assert sha(Path(p))==d,p
    # The completed202 method remains available unchanged.
    before=ast.parse((HERE/'assess_before204.py.txt').read_text(encoding='utf8'))
    after=ast.parse((HERE.parent/'regional_audit202/assess.py').read_text(encoding='utf8'))
    funcs=lambda a:{n.name:ast.dump(n) for n in a.body if isinstance(n,ast.FunctionDef)}
    old,new=funcs(before),funcs(after);assert all(v==new[k] for k,v in old.items())
    cohort=read(HERE/'stopped_cohort73.json');assert len(cohort)==12
    for z in cohort:
        a,b=z['end110'],z['end90']
        assert z['id']==a['id']==b['id']==z['initial']['id']
        assert a['cell']==19 and a['v']<5
        assert (a['rd'],a['route'],a['lane'])==(b['rd'],b['route'],b['lane'])
        assert abs((b['x']-a['x'])-z['progress_delta_m'])<1e-9
        checks+=1
    snapshots=read(HERE/'snapshot_routes73.json')
    assert len(snapshots)==168
    for z in snapshots:
        assert z['stopped']==z['stop_exit']+z['stop_through']+z['stop_other_unknown'] and z['stopped']<=z['n'];checks+=1
    data=read(HERE/'paired_detector_journeys73.json');assert not data['duplicate_station_entries']
    mapping={int(z['dcp_no']):z for z in csv.DictReader((I/'selected/obs150/obs150_detectors_v2.csv').open(encoding='utf-8-sig',newline=''))}
    found={};arrival=[]
    for arm in ('release','release_vsl90'):
        folder=Path('D:/VISSIM_runs/20261003_s73_vsl_replication95')/arm/f'decisions_sdmpc31_g_2700_{arm}_s73/obs150'
        all_entries=[]
        for t in (2850,3000,3150):
            for line in (folder/f'mer_{t:06d}.jsonl').read_bytes().splitlines():
                z=json.loads(line)
                if z[2] is not None and 2700<=z[2]<=3150 and mapping[z[1]]['boundary_ref'] in ('through:10481','through:10483','off_entry:10483'):
                    key=(arm,z[4],mapping[z[1]]['boundary_ref']);assert key not in found
                    found[key]=(z[2],int(mapping[z[1]]['lane']),z[6],z[1])
                    if mapping[z[1]]['boundary_ref']=='through:10481':all_entries.append((z[2],int(mapping[z[1]]['lane']),z[6]))
        for lo,hi in ((2700,2850),(2850,3000),(3000,3150)):
            for lane in (1,2,3):
                z=sorted(v for v in all_entries if lo<=v[0]<hi and v[1]==lane)
                times=[v[0] for v in z];gaps=[b-a for a,b in zip(times,times[1:])]
                speeds=[v[2] for v in z if v[2] is not None]
                arrival.append(dict(arm=arm,start=lo,end=hi,lane=lane,entries=len(z),
                    mean_speed_kmh=statistics.fmean(speeds) if speeds else None,
                    speed_sd_kmh=statistics.pstdev(speeds) if speeds else None,
                    mean_headway_s=statistics.fmean(gaps) if gaps else None,
                    headway_cv=statistics.pstdev(gaps)/statistics.fmean(gaps) if gaps and statistics.fmean(gaps)>0 else None,
                    definition='Raw point entries within this150s window; first/last interwindow gaps excluded. Descriptive, no causal attribution.'))
    for z in data['rows']:
        for arm,suffix in (('release','110'),('release_vsl90','90')):
            for key,ref in (('entry','through:10481'),('exit',z['branch'])):
                s=z[key+suffix];value=(s['t'],s['lane'],s['v'],s['dcp'])
                assert found[arm,z['id'],ref]==value;checks+=1
        assert abs(z['delta_sec']-((z['exit90']['t']-z['entry90']['t'])-(z['exit110']['t']-z['entry110']['t'])))<1e-9
    assert len(data['rows'])==612 and len({z['id'] for z in data['rows']})==612
    for group in data['groups']:
        rows=[z for z in data['rows'] if z['branch']==group['branch'] and group['start']<=z['entry110']['t']<group['end']]
        assert len(rows)==group['count']
        if rows:assert abs(statistics.fmean(z['delta_sec'] for z in rows)-group['mean_delta_sec'])<1e-9
    source=HERE.parent/'regional_audit202/assess.py'
    (HERE/'assess_executed.py.txt').write_bytes(source.read_bytes())
    (HERE/'verify_executed.py.txt').write_bytes(Path(__file__).read_bytes())
    (HERE/'arrival_context73.json').write_text(json.dumps(arrival,indent=2),encoding='utf8')
    result=dict(status='PASS',checks=checks,pairs=612,matched_detector_events=2448,cohort=12,
        existing_functions_AST_unchanged=True,input_pins_unchanged=len(summary['input_sha256']),
        source_sha256={str(source):sha(source),str(Path(__file__)):sha(Path(__file__))},
        no_forecast_or_calibration=True,goal='ACTIVE_NOT_QUALIFIED')
    (HERE/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result))


if __name__=='__main__':main()
