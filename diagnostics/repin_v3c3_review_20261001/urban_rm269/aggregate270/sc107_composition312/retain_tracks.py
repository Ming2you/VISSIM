"""One supplemental closed-file pass; retain missing path evidence, never future fit."""
from collections import Counter, defaultdict
from pathlib import Path
import ctypes, gzip, hashlib, json, time, xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
OUT=Path('E:/VISSIM_analysis/20261010_sc107_composition312')
sha=lambda b:hashlib.sha256(b).hexdigest()


def classify(event, track, branches, cutoff=2400):
    observed=[]
    for row in track:
        if event['time']-.1 <= row['sec'] < min(event['time']+30,cutoff):
            for label,links in branches.items():
                if row['link'] in links:observed.append((row['sec'],label,row['link']))
    kinds={r[1] for r in observed}
    return (next(iter(kinds)) if len(kinds)==1 else 'ambiguous' if kinds else 'unresolved'),observed


def main():
    assert not (OUT/'retained_completion.json').exists()
    assert not (OUT/'retained_intent.json').exists(),'Preserve prior attempt'
    old=json.loads((OUT/'completion.json').read_bytes())
    prior_bytes=(OUT/'past.json.gz').read_bytes()
    assert sha(prior_bytes)==old['cache_sha256']
    prior=json.loads(gzip.decompress(prior_bytes));pins=prior['source_pins']
    closed_path=next(p for p in pins if p.endswith('runtime_closure.json'))
    closed_bytes=Path(closed_path).read_bytes();assert sha(closed_bytes)==pins[closed_path]
    closed=json.loads(closed_bytes);assert closed['all_owned_processes_closed'] and closed['normal_sim_done_sec']==2850
    network=next(p for p in pins if p.endswith('.inpx'))
    network_bytes=Path(network).read_bytes();assert sha(network_bytes)==pins[network]
    tree=ET.fromstring(network_bytes);links={l.get('no'):l for l in tree.findall('./links/link')}
    branches={'through':{'10023','1220000402'},'right':{'10616','381','10607','1'},'left':{'10622','1220043300'}}
    for conn,start,end in [('10023','1220000201','1220000402'),('10616','1220000201','381'),('10607','381','1'),('10622','1220000201','1220043300')]:
        assert links[conn].find('fromLinkEndPt').get('lane').split()[0]==start
        assert links[conn].find('toLinkEndPt').get('lane').split()[0]==end
    source=Path(next(p for p in pins if p.endswith('.fzp')));before=source.stat()
    wanted={x['vehicle'] for x in prior['witnesses']};tracks=defaultdict(list);digest=hashlib.sha256()
    kernel=ctypes.WinDLL('kernel32');kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    intent=dict(status='started_no_retry',total_source_pass_limit=2,prior_passes=1,
        reason='Completed first pass omitted tracks and right continuation10607/1;28 paths unresolved. Retain selected pre2400 tracks once for auditable classification.',
        prediction_budget=0,native_budget=0,tracking_end_exclusive=2400)
    (OUT/'retained_intent.json').write_text(json.dumps(intent,indent=2),encoding='utf8')
    start=time.perf_counter()
    with source.open('rb') as f:
        for line in f:
            digest.update(line);line=line.strip()
            if line.startswith(b'$VEHICLE:'):
                names=[s.strip().decode('ascii').upper() for s in line.split(b':',1)[1].split(b';')]
                ix={k:names.index(k) for k in ('SIMSEC','NO','LANE\\LINK\\NO','LANE\\INDEX','POS','SPEED','ROUTDECNO','ROUTENO','NEXTLINK\\NO')}
                assert ix['SIMSEC']==0;continue
            if not line or line.startswith((b'*',b'$')):continue
            sec=float(line.split(b';',1)[0])
            if not 1500<=sec<2400:continue
            parts=line.split(b';');veh=int(parts[ix['NO']])
            if veh in wanted:
                tracks[veh].append(dict(sec=sec,link=str(int(parts[ix['LANE\\LINK\\NO']])),lane=int(parts[ix['LANE\\INDEX']]),pos=float(parts[ix['POS']]),speed=float(parts[ix['SPEED']]),
                    route_decision=parts[ix['ROUTDECNO']].decode(),route=parts[ix['ROUTENO']].decode(),next_link=parts[ix['NEXTLINK\\NO']].decode()))
    after=source.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    assert digest.hexdigest()==pins[str(source)]
    witnesses=[]
    for e in prior['witnesses']:
        turn,observed=classify(e,tracks[e['vehicle']],branches)
        witnesses.append(dict(e,turn=turn,downstream_observations=observed))
    doc=dict(witnesses=witnesses,tracks=dict(tracks),branch_links={k:sorted(v) for k,v in branches.items()},
        counts_by_source={k:dict(Counter(r['turn'] for r in witnesses if r['source']==k)) for k in ('SC1004','SC1005','unresolved')},
        head_turn_counts={str(k):v for k,v in Counter((r['head_lane'],r['sg'],r['turn']) for r in witnesses).items()},
        previous_cache_sha256=sha(prior_bytes),source_pins=pins,fit_head_window=[1800,2250],tracking_end_exclusive=2400,
        limits=['Achieved past turn distribution is not exogenous demand.', 'Head lane/signal group does not prove downstream turn.', 'No future2400..2850 is used.'])
    target=OUT/'retained_past.json.gz';target.write_bytes(gzip.compress(json.dumps(doc,ensure_ascii=False,allow_nan=False).encode()))
    done=dict(status='complete_retained_past',cache=str(target),cache_sha256=sha(target.read_bytes()),total_source_passes=2,
        script_sha256=sha(Path(__file__).read_bytes()),wall_sec=time.perf_counter()-start,counts_by_source=doc['counts_by_source'],head_turn_counts=doc['head_turn_counts'])
    (OUT/'retained_completion.json').write_text(json.dumps(done,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps(done,ensure_ascii=False))


if __name__=='__main__':main()
