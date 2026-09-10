"""Completed-run physical trajectory equivalence and explicitly sampled congestion."""
from __future__ import annotations
from collections import defaultdict
import csv, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NEW='codex_area_observed_nc_s13_20260910'
OLD='codex_meter10639_g5_s13_20260910'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(4*1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def payload(path):
    before=path.stat();digest=hashlib.sha256();count=0;size=0;first=None;tail=b''
    with path.open('rb') as stream:
        for line in stream:
            if line.startswith(b'$VEHICLE:'):
                header=line.rstrip(b'\r\n').decode('ascii');break
        else:raise ValueError('Missing FZP header')
        offset=stream.tell()
        for chunk in iter(lambda:stream.read(4*1024*1024),b''):
            if first is None:first=chunk.split(b'\n',1)[0].strip()
            digest.update(chunk);count+=chunk.count(b'\n');size+=len(chunk);tail=(tail+chunk)[-1024:]
    if tail and not tail.endswith(b'\n'):count+=1
    after=path.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('File changed while reading')
    last=tail.strip().splitlines()[-1]
    return dict(path=str(path.relative_to(ROOT)),file_bytes=after.st_size,file_sha256=sha(path),
                header=header,payload_sha256=digest.hexdigest(),payload_bytes=size,rows=count,
                first_sec=float(first.split(b';',1)[0]),last_sec=float(last.split(b';',1)[0]),payload_offset=offset)

def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))

def csv_comparison(new,old,keys,drop=()):
    a={tuple(r[k] for k in keys):{k:v for k,v in r.items() if k not in drop} for r in rows(new)}
    b={tuple(r[k] for k in keys):{k:v for k,v in r.items() if k not in drop} for r in rows(old)}
    changed=[k for k in a.keys()&b.keys() if a[k]!=b[k]]
    return dict(new_rows=len(a),reference_rows=len(b),new_only_keys=sorted(a.keys()-b.keys()),
                old_only_keys=sorted(b.keys()-a.keys()),changed_rows=len(changed),first_differences=[dict(key=k,new=a[k],reference=b[k]) for k in changed[:5]],
                exact=not changed and a.keys()==b.keys(),excluded_nonphysical_columns=list(drop))

def episodes(series):
    result=[];start=previous=None
    for row in series:
        t=float(row['sim_sec']);slow=int(row['count'])>=5 and float(row['mean_speed_kph'])<30
        if start is not None and (not slow or previous!=t-30):
            if previous-start>=90:result.append({'start_sec':start,'last_slow_sec':previous,'duration_between_samples_sec':previous-start})
            start=None
        if slow and start is None:start=t
        previous=t
    if start is not None and previous-start>=90:result.append({'start_sec':start,'last_slow_sec':previous,'duration_between_samples_sec':previous-start})
    return result

def main():
    new=ROOT/'evaluation/runs'/NEW;old=ROOT/'evaluation/runs'/OLD
    fzps=[payload(next(run.glob('vissim_eval/*.fzp'))) for run in (new,old)]
    fields=('header','payload_sha256','payload_bytes','rows','first_sec','last_sec')
    comparisons={};files=[Path(__file__),ROOT/'diagnostics/native_trajectory_repeat_check.json']
    for prefix,keys,drop in [('state',('sim_sec',),('controller_mode','controller_status','decision_wall_sec')),
                             ('bottleneck_segments',('sim_sec','model_link','segment_index'),()),
                             ('bottleneck_links',('sim_sec','link'),())]:
        paths=[run/f'{prefix}_{run.name}.csv' for run in (new,old)];files+=paths
        comparisons[prefix]=csv_comparison(*paths,keys,drop)
    bycell=defaultdict(list)
    for row in rows(new/f'bottleneck_segments_{NEW}.csv'):
        if float(row['sim_sec'])>=30:bycell[(row['direction'],int(row['segment_index']))].append(row)
    cells=[]
    for (direction,index),series in sorted(bycell.items()):
        times=episodes(series);minimum=min((float(r['mean_speed_kph']) for r in series if int(r['count'])>=5),default=None)
        cells.append(dict(direction=direction,index=index,cell=f'{direction}{index}',first_sustained_slow_sec=times[0]['start_sec'] if times else None,
                          episodes=times,minimum_sampled_speed_kph=minimum,maximum_sampled_density_veh_km_lane=max(float(r['density_veh_km_lane']) for r in series),
                          maximum_sampled_stock_veh=max(int(r['count']) for r in series)))
    report=dict(schema='observed-nc-trajectory-audit/v1',new_run=NEW,reference_run=OLD,
                fzp_all_vehicle_payload_exact=all(fzps[0][k]==fzps[1][k] for k in fields),fzp=fzps,csv=comparisons,
                meaning='Every ordered native one-second FZP row matches, including vehicle ID/link/lane/position/lateral position/speed/time-in-network/delay; only pre-data metadata excluded.',
                reference_qualification='The failed metering attempt had no applied treatment and previously matched original NC at all 5-second records; it is reused only as finer NC measurement.',
                congestion_definition=dict(minimum_count_veh=5,speed_below_kph=30,minimum_elapsed_sec=90,cadence_sec=30,
                    interpretation='At least four consecutive 30-second slow samples; sampled persistence, not proof of uninterrupted congestion between samples; cell indexes zero-based.'),
                cell_congestion=cells,source_sha256={str(p.relative_to(ROOT)):sha(p) for p in files})
    out=ROOT/'diagnostics/observed_nc_trajectory_equivalence.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with out.with_name('observed_nc_congestion_onsets.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=['cell','first_sustained_slow_sec','minimum_sampled_speed_kph','maximum_sampled_density_veh_km_lane','maximum_sampled_stock_veh']);writer.writeheader()
        writer.writerows({k:r[k] for k in writer.fieldnames} for r in cells)
    print(json.dumps({k:v for k,v in report.items() if k in ('fzp_all_vehicle_payload_exact','fzp','csv')},ensure_ascii=False))
    if not report['fzp_all_vehicle_payload_exact'] or not all(v['exact'] for v in comparisons.values()):raise SystemExit('Physical trajectories differ')

if __name__=='__main__':main()
