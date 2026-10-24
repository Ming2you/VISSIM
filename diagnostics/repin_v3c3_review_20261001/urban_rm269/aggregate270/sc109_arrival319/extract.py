"""Retain missing closed-run position/speed evidence once per source file."""
from collections import defaultdict
from pathlib import Path
import ctypes
import gzip
import hashlib
import json
import time

HERE=Path(__file__).resolve().parent
A=HERE.parent
OUT=Path('E:/VISSIM_analysis/20261010_sc109_arrival319')
PINS={}


def read(path, compressed=False):
    path=Path(path);data=path.read_bytes()
    PINS[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if compressed else data)


def main():
    assert not OUT.exists(), 'Preserve any previous attempt; do not restart automatically'
    chain=read(A/'exit_timing309/sc109_chain.json')
    closure=read('E:/VISSIM_analysis/20261010_urbanrm269_cityonly289/runtime_closure.json')
    assert closure['all_owned_processes_closed'] and closure['normal_sim_done_sec']==2850
    common=read('E:/VISSIM_analysis/20261010_urbanrm269_cityonly289/cached_summary.json')
    assert common['paired_prefix_exact'] and common['common_start_vehicle_records_exact']
    support=set(chain['initial_provenance'])|{'10024','1220000600','10112'}
    kernel=ctypes.WinDLL('kernel32')
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    OUT.mkdir(parents=True)
    (OUT/'intent.json').write_text(json.dumps(dict(status='started_no_automatic_retry',source_pass_limit=2,
        reason='Existing309 cache has boundary events only;312 tracks stop before2400. Need in-corridor speed and position to distinguish travel from stopped delay.',
        selected_window=[2395.1,2850],new_native=0,new_forecasts=0,new_fits=0)),encoding='utf8')
    started=time.perf_counter();results={}
    for arm in ('hold','city'):
        prior=read(f'E:/VISSIM_analysis/20261010_exit_timing309/{arm}.json.gz',True)
        source=Path(prior['source']);before=source.stat()
        assert before.st_size==prior['source_size_bytes'] and before.st_mtime_ns==prior['source_mtime_ns']
        wanted={r['vehicle'] for heads in chain['head_events'][arm].values() for r in heads}
        tracks=defaultdict(list);digest=hashlib.sha256();rows=0;kept=0;times=set();last=-1.
        with source.open('rb') as file:
            for line in file:
                digest.update(line);line=line.strip()
                if line.startswith(b'$VEHICLE:'):
                    names=[s.strip().decode('ascii').upper() for s in line.split(b':',1)[1].split(b';')]
                    ix={k:names.index(k) for k in ('SIMSEC','NO','LANE\\LINK\\NO','LANE\\INDEX','POS','SPEED','ROUTDECNO','ROUTENO','NEXTLINK\\NO')}
                    assert ix['SIMSEC']==0
                    continue
                if not line or line.startswith((b'*',b'$')):continue
                sec=float(line.split(b';',1)[0]);assert sec>=last;last=sec;rows+=1
                if not 2395.1-1e-7<=sec<=2850:continue
                parts=line.split(b';');vehicle=int(parts[ix['NO']]);link=str(int(parts[ix['LANE\\LINK\\NO']]))
                if vehicle not in wanted and link not in support:continue
                tracks[vehicle].append(dict(sec=sec,link=link,lane=int(parts[ix['LANE\\INDEX']]),
                    pos=float(parts[ix['POS']]),speed=float(parts[ix['SPEED']]),
                    route_decision=parts[ix['ROUTDECNO']].decode(),route=parts[ix['ROUTENO']].decode(),
                    next_link=parts[ix['NEXTLINK\\NO']].decode()))
                times.add(sec);kept+=1
        after=source.stat()
        assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
        assert digest.hexdigest()==prior['source_sha256']
        assert min(times)==2395.1 and max(times)==2845.1 and len(times)==91
        report=dict(status='complete_closed_corridor_tracks',arm=arm,source=str(source),source_sha256=digest.hexdigest(),
                    source_size_bytes=after.st_size,source_mtime_ns=after.st_mtime_ns,
                    full_file_rows=rows,retained_rows=kept,tracks=dict(tracks),support_links=sorted(support),
                    future_diagnostic_only=True,source_passes=1)
        path=OUT/(arm+'.json.gz')
        path.write_bytes(gzip.compress(json.dumps(report,allow_nan=False).encode('utf8')))
        results[arm]=dict(cache=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                          tracks=len(tracks),retained_rows=kept,source_sha256=digest.hexdigest())
        print('RETAINED319',arm,results[arm]['tracks'],kept,flush=True)
    PINS[str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    completion=dict(status='complete',arms=results,wall_sec=time.perf_counter()-started,source_pins=PINS,
                    new_native=0,new_predictions=0,new_fits=0,source_passes=2)
    (OUT/'completion.json').write_text(json.dumps(completion,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('COMPLETE319',completion['wall_sec'],flush=True)


if __name__=='__main__':main()
