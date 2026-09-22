"""One spatial VSL falsification, reusing the native fixed-profile runner.

Compare all arms on common5s frames. No live vehicle queries or controller.
"""
import csv,hashlib,json,sys
from pathlib import Path
from collections import Counter,defaultdict
import xml.etree.ElementTree as ET
B=Path(__file__).resolve().parent;H=B.parent;K=H/'cohort_dynamics_20260920';ROOT=B.parents[3]
sys.path.insert(0,str(ROOT))
from diagnostics.fast_fixed_profile import prepare
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.lever_mechanisms_20260921 import analyze as old
from diagnostics.capture_native_runtime_errors import parse_bytes
O=B/'vsl_response_v1'/'upstream_native'


def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def table(p,rows):
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def prep():
    O.mkdir(exist_ok=False)
    source=K/'route_state_native_v1/none_s23/source/baseline.inpx'
    profile=load(K/'route_state_native_v1/vsl_s23/profile.json')
    profile.update(network_sha256=sha(source),vehicle_record_interval_sec=5)
    for row in profile['vsl_commands']:
        assert 51<=row['dsd_no']<=58
        row['speed_id']=100 if row['dsd_no']<=54 else 120
    assert not profile['meter_commands'] and profile['seed']==23 and profile['terminal_sec']==3000
    save(O/'profile.json',profile);prepare(source,O/'profile.json',O/'prepared')
    before=ET.parse(source).getroot();after=ET.parse(O/'prepared/network/baseline.inpx').getroot()
    assert old.physical_hash(before)==old.physical_hash(after)
    save(O/'protocol.json',dict(source=str(source.relative_to(ROOT)),source_sha256=sha(source),
        intervention='At2400 onward: DSD51-54 distribution100, DSD55-58 nominal120. RM OFF/native urban signals.',
        rationale='Separate upstream restriction from the downstream speed penalty; boundary55 remains346m upstream of exit10643, not proof of a sufficient acceleration zone.',
        fixed=['geometry','demand','route','seed23','SimRes1','initial_state','urban_signals','ramps'],
        references=['route_state_native_v1/none_s23/run_retry1','route_state_native_v1/vsl_s23/run_retry1'],
        common_record_interval_s=5,run_end=3000,analysis_windows=[[2400,2850],[2850,3000],[2400,3000]],
        prefix_gate='All original9 FZP fields at common5s samples through2400 exact to NC.',
        execution_gate='Native LDP, VSL apply-time readback and untargeted snapshots; existing fixed runner.',
        model_calibration_uses_this_new_arm=False,independent_seed=False,production_adopted=False,
        physical_hash=old.physical_hash(before),source_pins={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'diagnostics/fast_fixed_profile.py',ROOT/'diagnostics/fast_nc_run.ps1',ROOT/'diagnostics/fast_nc_runner.vbs']}))
    print(O,flush=True)


WINDOWS=[(2400,2850),(2850,3000),(2400,3000)]
ZONES=[('before_exit_400_1305',400.,1305.38870368),('approach_1305_1652',1305.38870368,1651.806),
       ('after_exit_1652_1964',1651.806,1964.218),('merge_1964_2307',1964.218,2307.379),
       ('recovery_2307_2652',2307.379,2652.027)]


def extract(arm,run):
    receipt=load(run/'run.json');assert receipt['completed'] and receipt['terminal_sec']==3000 and not receipt['owned_native_alive']
    assert load(run/'fixed_validation.json')['passed']
    path=next((run/'vissim_eval').glob('*.fzp'));before=path.stat();digest=hashlib.sha256();prefix=hashlib.sha256()
    counts=defaultdict(Counter);flow=defaultdict(Counter);initial={};final={};previous={};now=None;frame={};sample_times=[]
    cols=None
    def consume(t,frame):
        nonlocal previous
        if t<2400:return
        sample_times.append(t)
        if t==2400:
            for zone,lo,hi in ZONES:initial[zone]=sum(r['link']==2 and lo<=r['pos']<hi for r in frame.values())
        for start,end in WINDOWS:
            if not start<t<=end:continue
            for r in frame.values():
                key='mainline' if r['link'] in old.CHAIN else 'on' if r['link'] in old.ON else 'off' if r['link'] in old.OFF else None
                if key:counts[start,end,key]['vehicle_seconds']+=5
                if r['link']==2:
                    for zone,lo,hi in ZONES:
                        if lo<=r['pos']<hi:
                            row=counts[start,end,zone];row['vehicle_seconds']+=5;row['slow_vehicle_seconds']+=5*(r['speed']<30)
                            row['speed_sum']+=r['speed'];row['desired_sum']+=r['desired'];row['samples']+=1
            # Only observed same-link forward crossings; no exits inferred from missing IDs.
            for vid,r in frame.items():
                a=previous.get(vid)
                if a is None or a['link']!=2 or r['link']!=2 or r['pos']<a['pos']:continue
                for point in (400.,1305.38870368,1651.806,1964.218,2307.379,2652.027):
                    if a['pos']<point<=r['pos']:flow[start,end,point]['crossings']+=1
                if a['lane']!=r['lane']:
                    for zone,lo,hi in ZONES:
                        if lo<=r['pos']<hi:counts[start,end,zone]['observed_lane_boundary_changes']+=1
        if t in (2850,3000):
            final[str(t)]={zone:sum(r['link']==2 and lo<=r['pos']<hi for r in frame.values()) for zone,lo,hi in ZONES}
        previous=frame
    with path.open('rb') as stream:
        for raw in stream:
            digest.update(raw)
            if raw.startswith(b'$VEHICLE:'):
                cols=raw.strip().split(b':',1)[1].decode().split(';');continue
            if not raw[:1].isdigit():continue
            assert cols is not None
            a=raw.rstrip(b'\r\n').split(b';');assert len(a)==len(cols)==20
            time=float(a[0]);assert time.is_integer();t=int(time)
            if t%5:continue
            if t<=2400:prefix.update(b';'.join(a[:9])+b'\n')
            if t<2395:continue
            if now is not None and t!=now:consume(now,frame);frame={}
            now=t;frame[int(a[1])]=dict(link=int(a[2]),lane=int(a[3]),pos=float(a[4]),speed=float(a[6]),desired=float(a[9]))
        consume(now,frame)
    assert now==3000 and sample_times==list(range(2400,3001,5))
    after=path.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    errors=[]
    for item in receipt['error_files']:
        error=parse_bytes((run/item['name']).read_bytes());assert not error['unparsed_removal_lines'];errors.append(error)
    rows=[]
    for (start,end,zone),row in sorted(counts.items()):
        rows.append(dict(arm=arm,start=start,end=end,zone=zone,ttt_veh_h=row['vehicle_seconds']/3600,
            slow_vehicle_seconds=row['slow_vehicle_seconds'],lane_boundary_changes=row['observed_lane_boundary_changes'],
            mean_speed=row['speed_sum']/row['samples'] if row['samples'] else None,mean_desired=row['desired_sum']/row['samples'] if row['samples'] else None))
    flowrows=[dict(arm=arm,start=s,end=e,point=p,crossings=x['crossings']) for (s,e,p),x in sorted(flow.items())]
    save(O/(arm+'_errors.json'),errors)
    return dict(arm=arm,path=str(path.relative_to(ROOT)),bytes=before.st_size,sha256=digest.hexdigest(),prefix_sha256=prefix.hexdigest(),
        initial=initial,final=final,rows=rows,flows=flowrows)


def analyze(run_name='run'):
    assert Path(run_name).name==run_name
    cases={'none':K/'route_state_native_v1/none_s23/run_retry1','both_zones':K/'route_state_native_v1/vsl_s23/run_retry1','upstream_only':O/run_name}
    results=[]
    for name,path in cases.items():
        result=extract(name,path);save(O/(name+'_summary.json'),result);results.append(result);print('extracted',name,flush=True)
    assert len({r['prefix_sha256'] for r in results})==1,'Warmup traffic differs'
    assert all(r['initial']==results[0]['initial'] for r in results)
    rows=[x for r in results for x in r['rows']];table(O/'regions_5s.csv',rows)
    table(O/'crossings_5s.csv',[x for r in results for x in r['flows']])
    costs=[]
    for start,end in WINDOWS:
        values={a:sum(r['ttt_veh_h'] for r in rows if r['arm']==a and r['start']==start and r['end']==end and r['zone'] in ('mainline','on','off')) for a in cases}
        costs.extend(dict(arm=a,start=start,end=end,component_ttt=v,delta_vs_nc=v-values['none']) for a,v in values.items())
    table(O/'costs_5s.csv',costs)
    save(O/'validation.json',dict(completed=True,prefix_common5s_exact=True,component_costs=costs,
        source_pins={r['path']:r['sha256'] for r in results},independent_seed=False,production_adopted=False,
        scope='East mainline+4on+4off links, not full Omega. Right-endpoint5s TTT; lane changes miss events between samples; crossings endpoint counts, not saturation capacity.',
        uncertainty='New policy vs reused native references on same seed; separate per-arm abnormal-removal ledgers must qualify interpretation.'))
    print(json.dumps(costs,indent=2),flush=True)


if __name__=='__main__':
    if sys.argv[1]=='prepare':prep()
    elif sys.argv[1]=='analyze':analyze(sys.argv[2] if len(sys.argv)>2 else 'run')
