"""One past-only positional extraction from the already closed hold run.

Training source crossings end2100. Follow-up stops2395.1, before the2400
validation initial state. No active run, validation future or full TTT scan.
"""
import ctypes,gzip,hashlib,json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=Path('E:/VISSIM_analysis/20261010_sc15_source301_past')
SOURCE=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/vissim_eval/sdmpc31_g_2400_hold_s29_001.fzp')
START,END=900.1,2395.1


def main():
    assert not (OUT/'extract_intent.json').exists(), 'One closed source scan only'
    prior=json.loads(Path('E:/VISSIM_analysis/20261010_sc15_source300/completion.json').read_bytes())
    assert prior['status']=='complete_sc15_sc101_source_cache'
    links=set(prior['physical_links'])|{336,1220016101,1220012402}
    kernel=ctypes.WinDLL('kernel32');kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    OUT.mkdir(parents=True,exist_ok=True)
    intent=dict(status='started_no_automatic_retry',source=str(SOURCE),source_passes_max=1,
        window_sec=[START,END],source_crossing_fit_window=[900,2100],followup_end=END,
        physical_links=sorted(links),validation_start=2400,validation_future_used=False,
        reason='Existing300 cache starts2395.1 and cannot support a past-only estimate.',
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'extract_intent.json').write_text(json.dumps(intent,indent=2)+'\n',encoding='utf8')
    before=SOURCE.stat();digest=hashlib.sha256();frames=[];index=None;current=None
    columns=('SIMSEC','NO','LANE\\LINK\\NO','LANE\\INDEX','POS','SPEED','ROUTDECNO','ROUTENO','NEXTLINK\\NO')
    with SOURCE.open('rb') as file:
        for raw in file:
            digest.update(raw);line=raw.strip()
            if line.startswith(b'$VEHICLE:'):
                assert index is None
                names=[x.strip().decode('ascii').upper() for x in line.split(b':',1)[1].split(b';')]
                index={k:names.index(k) for k in columns};assert index['SIMSEC']==0
                continue
            if not line or line.startswith((b'*',b'$')):continue
            sec=float(line.split(b';',1)[0])
            if not START-1e-7<=sec<=END+1e-7:continue
            if current is None or current['sec']!=sec:
                if current:assert abs(sec-current['sec']-5)<1e-7
                current=dict(sec=sec,rows=[]);frames.append(current)
            row=line.split(b';');assert len(row)==len(names)
            link=int(row[index['LANE\\LINK\\NO']])
            if link in links:
                current['rows'].append([int(row[index['NO']]),link,int(row[index['LANE\\INDEX']]),
                    float(row[index['POS']]),float(row[index['SPEED']]),
                    row[index['ROUTDECNO']].decode('ascii').strip(),row[index['ROUTENO']].decode('ascii').strip(),
                    row[index['NEXTLINK\\NO']].decode('ascii').strip()])
    after=SOURCE.stat()
    assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    assert digest.hexdigest()==prior['arms']['hold']['source_sha256']
    assert len(frames)==300 and frames[0]['sec']==START and frames[-1]['sec']==END
    for frame in frames:assert len({x[0] for x in frame['rows']})==len(frame['rows'])
    result=dict(source=str(SOURCE),source_sha256=digest.hexdigest(),source_size_bytes=after.st_size,
        source_mtime_ns=after.st_mtime_ns,columns=['veh','link','lane','pos_m','speed_kph','route_decision','route','next_link'],
        frames=frames,physical_links=sorted(links),sample_sec=5,fit_head_start=900,fit_head_end=2100,
        followup_end=END,validation_start=2400,validation_future_used=False)
    target=OUT/'past.json.gz';assert not target.exists()
    target.write_bytes(gzip.compress(json.dumps(result,allow_nan=False).encode('utf8')))
    completion=dict(status='complete_past_only_source_cache',cache=str(target),
        cache_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),source_sha256=digest.hexdigest(),
        source_size_bytes=after.st_size,frames=len(frames),rows_retained=sum(len(f['rows']) for f in frames),
        source_passes=1,fit_head_window=[900,2100],followup_end=END,validation_future_used=False,
        script_sha256=intent['script_sha256'])
    (OUT/'completion.json').write_text(json.dumps(completion,indent=2)+'\n',encoding='utf8')
    print(completion)


if __name__=='__main__':main()
