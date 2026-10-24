"""One closed-file pass: pre2400 physical turn and upstream source witnesses."""
from collections import Counter,defaultdict
from pathlib import Path
import ctypes
import gzip
import hashlib
import json
import time
import xml.etree.ElementTree as ET
from evaluation.controllers import obs150_contract as oc

HERE=Path(__file__).resolve().parent;A=HERE.parent;ROOT=HERE.parents[4]
OUT=Path('E:/VISSIM_analysis/20261010_sc107_composition312')
FOLDER=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/decisions_sdmpc31_g_2400_hold_s29')
PINS={}

def raw(p):
    p=Path(p);b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return b


def main():
    assert not (OUT/'intent.json').exists()
    closed=json.loads(raw('E:/VISSIM_analysis/20261010_urbanrm269_cityonly289/runtime_closure.json'))
    assert closed['all_owned_processes_closed'] and closed['normal_sim_done_sec']==2850
    network=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    tree=ET.fromstring(raw(network));links={l.get('no'):l for l in tree.findall('./links/link')}
    branches={'through':('10023','1220000402'),'right':('10616','381'),'left':('10622','1220043300')}
    for label,(connector,target) in branches.items():
        assert links[connector].find('fromLinkEndPt').get('lane').split()[0]=='1220000201'
        assert links[connector].find('toLinkEndPt').get('lane').split()[0]==target
    sources={'SC1004':('56','10621'),'SC1005':('61','10499')}
    for source,connector in sources.values():
        assert links[connector].find('fromLinkEndPt').get('lane').split()[0]==source
        assert links[connector].find('toLinkEndPt').get('lane').split()[0]=='387'
    events=[];tails=[]
    for end in (1950,2100,2250):
        state=json.loads(raw(FOLDER/f'state_{end:06}.json'));b=oc.load_bundle(state)
        ds,_=oc.read_detector_csv(b.obs['detector_config']['path'],b.obs['detector_config']['sha256'])
        raw(b.obs['detector_config']['path']);raw(FOLDER/b.obs['mer']['chunk'])
        w=oc.assign_window(b.obs,b.mer_rows)
        for d in ds:
            if d.role!='head' or d.link!=1220000201:continue
            sg=oc.parse_head_ref(d.ref)[2]
            events.extend(dict(vehicle=r.veh,time=r.t_entry,head_lane=d.lane,sg=sg) for r in w.entries[d.dcp_no])
            tails.append(dict(end=end,lane=d.lane,count=w.tails[d.dcp_no]))
    wanted={r['vehicle'] for r in events}
    assert len(wanted)==len(events),'Repeated head crossings need separate episodes'
    completion=json.loads(raw('E:/VISSIM_analysis/20261010_exit_timing309/completion.json'))
    authority=completion['arms']['hold'];source=Path(authority['source'])
    before=source.stat();digest=hashlib.sha256();tracks=defaultdict(list);names=None;last=-1
    kernel=ctypes.WinDLL('kernel32');kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'intent.json').write_text(json.dumps(dict(status='started_no_automatic_retry',source_pass_limit=1,
        fit_head_window=[1800,2250],tracking_window=[1500,2400],tracking_end_exclusive=True,
        new_native=0,new_predictions=0)),encoding='utf8')
    start=time.perf_counter()
    with source.open('rb') as file:
        for line in file:
            digest.update(line);line=line.strip()
            if line.startswith(b'$VEHICLE:'):
                names=[x.strip().decode('ascii').upper() for x in line.split(b':',1)[1].split(b';')]
                ix={k:names.index(k) for k in ('SIMSEC','NO','LANE\\LINK\\NO','LANE\\INDEX','POS','SPEED')}
                assert ix['SIMSEC']==0;continue
            if not line or line.startswith((b'*',b'$')):continue
            at=float(line.split(b';',1)[0]);assert at>=last;last=at
            if not 1500<=at<2400:continue
            parts=line.split(b';');veh=int(parts[ix['NO']])
            if veh in wanted:
                tracks[veh].append(dict(sec=at,link=str(int(parts[ix['LANE\\LINK\\NO']])),lane=int(parts[ix['LANE\\INDEX']]),
                    position=float(parts[ix['POS']]),speed=float(parts[ix['SPEED']])))
    after=source.stat()
    assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    assert digest.hexdigest()==authority['source_sha256']
    witnesses=[]
    for e in events:
        track=tracks[e['vehicle']]
        downstream=[(r['sec'],k,r['link']) for r in track if e['time']-0.1<=r['sec']<min(e['time']+30,2400) for k,keys in branches.items() if r['link'] in keys]
        turn=min(downstream)[1] if downstream else 'unresolved'
        upstream=[(r['sec'],k,r['link']) for r in track if r['sec']<e['time'] for k,keys in sources.items() if r['link'] in keys]
        from_where=max(upstream)[1] if upstream else 'unresolved'
        before_head=[r for r in track if r['sec']<e['time'] and r['link']=='1220000201']
        last_lane=before_head[-1]['lane'] if before_head else None
        witnesses.append(dict(e,turn=turn,source=from_where,last_sampled_lane=last_lane,
            downstream_first=None if not downstream else min(downstream),upstream_last=None if not upstream else max(upstream)))
    counts={k:dict(Counter(r['turn'] for r in witnesses if r['source']==k)) for k in (*sources,'unresolved')}
    totals=dict(Counter(r['turn'] for r in witnesses))
    PINS[str(source)]=digest.hexdigest();raw(Path(__file__))
    doc=dict(status='complete_past_sc107_turn_witnesses',fit_head_window=[1800,2250],tracking_end_exclusive=2400,
        witnesses=witnesses,counts_by_observed_source=counts,physical_total=totals,unresolved_tails=tails,
        source_pins=PINS,source_passes=1,new_native=0,new_forecasts=0,wall_sec=time.perf_counter()-start,
        limits=['5s sampling can miss connector/path observations; unresolved paths remain explicit.',
                'Last observed upstream branch identifies source only when witnessed; unobserved source is not assigned from current lane.',
                'Pre2400 history only, no city/hold validation future contributes to these turn frequencies.',
                'This is a achieved-turn distribution, potentially affected by queues; not yet an exogenous route-choice estimate.'])
    target=OUT/'past.json.gz';target.write_bytes(gzip.compress(json.dumps(doc,ensure_ascii=False,allow_nan=False).encode('utf8')))
    (OUT/'completion.json').write_text(json.dumps(dict(status=doc['status'],cache=str(target),cache_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        source_passes=1,wall_sec=doc['wall_sec'],source_pins=PINS),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('PAST_TURNS',counts,'TOTAL',totals,'TAILS',sum(x['count'] for x in tails),'WALL',doc['wall_sec'])


if __name__=='__main__':main()
