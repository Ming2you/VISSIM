"""One streaming pass per closed FZP, retaining only boundary-event witnesses."""
from collections import Counter
from pathlib import Path
import csv
import ctypes
import gzip
import hashlib
import json
import time

from evaluation.controllers.control_area_objective import physical_membership_from_ledger

HERE=Path(__file__).resolve().parent
A=HERE.parent
ROOT=HERE.parents[4]
OUT=Path('E:/VISSIM_analysis/20261010_exit_timing309')
NATIVE=Path('E:/VISSIM_analysis/20261010_urbanrm269_cityonly289')
read=lambda p:json.loads(Path(p).read_bytes())


def events_between(previous,current,membership,start,end):
    assert end>start
    assert all(link in membership for link in (*previous.values(),*current.values()))
    events=[]
    for vehicle in previous.keys() | current.keys():
        old,new=previous.get(vehicle),current.get(vehicle)
        before=old is not None and membership[old]
        after=new is not None and membership[new]
        if before and not after:
            kind='observed_exit' if new is not None else 'disappeared_inside'
        elif after and not before:
            kind='observed_entry' if old is not None else 'appeared_or_reappeared_inside'
        else:
            continue
        events.append(dict(vehicle=vehicle,kind=kind,from_link=old,to_link=new,
                           low_sec=start,high_sec=end,mid_sec=(start+end)/2))
    count=Counter(r['kind'] for r in events)
    assert (sum(membership[k] for k in current.values())-sum(membership[k] for k in previous.values())
            ==count['observed_entry']+count['appeared_or_reappeared_inside']-count['observed_exit']-count['disappeared_inside'])
    return events


def extract(source,membership,expected_hash,timeseries):
    before=source.stat();digest=hashlib.sha256();index=None;last=-1.
    previous=None;current=None;current_time=None;previous_time=None
    events=[];counts=[];rows=0;window_rows=0
    def consume(at,frame):
        nonlocal previous,previous_time
        if previous is not None:
            assert abs(at-previous_time-5)<1e-7
            batch=events_between(previous,frame,membership,previous_time,at)
            c=Counter(x['kind'] for x in batch)
            expected=timeseries[round(at,5)]
            assert c['observed_exit']==int(expected['observed_exit_events'])
            assert c['observed_entry']==int(expected['observed_entry_events'])
            assert c['appeared_or_reappeared_inside']==int(expected['appeared_inside_events'])+int(expected['reappeared_inside_events'])
            assert c['disappeared_inside']==int(expected['terminal_exit_inferred_events'])+int(expected['unresolved_inside_disappearances'])
            assert sum(membership[x] for x in frame.values())==int(expected['inside_vehicles'])
            events.extend(batch);counts.append(dict(end_sec=at,**c))
        previous,previous_time=frame,at
    with source.open('rb') as file:
        for raw in file:
            digest.update(raw);line=raw.strip()
            if line.startswith(b'$VEHICLE:'):
                assert index is None
                names=[x.strip().decode('ascii').upper() for x in line.split(b':',1)[1].split(b';')]
                index={k:names.index(k) for k in ('SIMSEC','NO','LANE\\LINK\\NO')}
                assert index['SIMSEC']==0
                continue
            if not line or line.startswith((b'*',b'$')):continue
            assert index is not None
            at=float(line.split(b';',1)[0]);assert at>=last;last=at;rows+=1
            if not 2395.1-1e-7<=at<=2850:continue
            if current_time!=at:
                if current is not None:consume(current_time,current)
                current_time,current=at,{}
            parts=line.split(b';');assert len(parts)==len(names)
            vehicle=int(parts[index['NO']]);link=str(int(parts[index['LANE\\LINK\\NO']]))
            assert vehicle not in current
            current[vehicle]=link;window_rows+=1
    assert current is not None
    consume(current_time,current)
    after=source.stat()
    assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    assert digest.hexdigest()==expected_hash
    assert len(counts)==90 and counts[0]['end_sec']==2400.1 and counts[-1]['end_sec']==2845.1
    observed=[r for r in events if r['kind']=='observed_exit']
    return dict(status='complete_closed_boundary_event_cache',source=str(source),source_sha256=expected_hash,
        source_size_bytes=after.st_size,source_mtime_ns=after.st_mtime_ns,
        full_file_rows_visited=rows,window_rows_visited=window_rows,events=events,counts=counts,
        observed_exit_time_cost=-sum((2850-r['mid_sec'])/3600 for r in observed),
        observed_exit_count=len(observed),scope='Transitions2395.1->2400.1 through2840.1->2845.1; matches prior area rows >2400. Common prefix cancels. No events invented in final4.9s hold tail.',
        limits=['Disappearances remain unclassified here; never treated as normal exits.',
                'Five-second sampled crossings may skip short links or multiple hidden boundary changes.',
                'No future events become prediction inputs.'])


def main():
    assert not (OUT/'intent.json').exists(), 'No duplicate extraction or automatic retry'
    closure=read(NATIVE/'runtime_closure.json')
    proof=read(NATIVE/'cached_summary.json')
    assert closure['all_owned_processes_closed'] and closure['normal_sim_done_sec']==2850
    assert proof['paired_prefix_exact'] and proof['common_start_vehicle_records_exact']
    sources=read(Path('E:/VISSIM_analysis/20261010_gatearrival291/completion.json'))['arms']
    tuning=read(A/'flow279/config_10686_free.json')
    path=ROOT/tuning['control_area_objective']['membership_path']
    membership=physical_membership_from_ledger(read(path));assert sum(membership.values())==701
    k=ctypes.WinDLL('kernel32');k.GetCurrentProcess.restype=ctypes.c_void_p
    k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'intent.json').write_text(json.dumps(dict(status='started_no_automatic_retry',source_pass_limit=2,
        closed_only=True,selected_window=[2400,2850],new_native=0,new_predictions=0)),encoding='utf8')
    arms={};started=time.perf_counter()
    for arm,directory in [('hold','hold'),('city','selected')]:
        file=NATIVE/directory/'area_timeseries.csv'
        with file.open(encoding='utf-8-sig',newline='') as f:
            times={round(float(r['sim_sec']),5):r for r in csv.DictReader(f) if float(r['sim_sec'])>2400}
        source=Path(sources[arm]['source'])
        result=extract(source,membership,sources[arm]['source_sha256'],times)
        target=OUT/(arm+'.json.gz');assert not target.exists()
        target.write_bytes(gzip.compress(json.dumps(result,allow_nan=False).encode('utf8')))
        arms[arm]=dict(cache=str(target),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            exit_count=result['observed_exit_count'],exit_time_cost=result['observed_exit_time_cost'],
            source=str(source),source_sha256=result['source_sha256'])
        print(arm,arms[arm],flush=True)
    native_delta=read(A/'timing307/assessment.json')['native_boundary']['observed_exit_events']
    assert arms['city']['exit_count']-arms['hold']['exit_count']==native_delta['vehicles']
    assert abs(arms['city']['exit_time_cost']-arms['hold']['exit_time_cost']-native_delta['cost'])<1e-8
    doc=dict(status='complete_closed_exit_timing_cache',arms=arms,wall_sec=time.perf_counter()-started,
        native_delta_reproduced=native_delta,source_passes=2,new_native=0,new_predictions=0,new_fits=0,
        source_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),path,HERE/'tests.log',NATIVE/'cached_summary.json',NATIVE/'runtime_closure.json']})
    (OUT/'completion.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('COMPLETE',doc['wall_sec'],native_delta,flush=True)


if __name__=='__main__':main()
