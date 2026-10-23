"""Read completed OFF snapshots to plan calibration; no rollout or FZP scan."""
import datetime,hashlib,json,math,os,sys
from pathlib import Path
os.environ['PYTHONDONTWRITEBYTECODE']='1'
A=Path(__file__).resolve().parent;O=A/'refine15_regimes'
ROOT=Path('D:/VISSIM_packages/vsl_multizone355_20261015')
RUN=Path('E:/VISSIM_runs/20261008_coupling268_off_s29_8100')
F=RUN/'sdmpc/decisions_sdmpc31_sdmpc8100_s29'
PINS={}
def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
assert not (O/'off110_snapshots.json').exists()
assert not O.exists() or (O/'initial_failure.json').exists()
queue=read(Path('E:/VISSIM_runtime/20261008_coupling268_vsl_three/queue_state.json'))
close=queue['conditions']['off']
assert close['native_exit_code']==0 and close['normal_sim_done']==8100 and close['owners_closed']
assert read(RUN/'native_status.json')['details']['terminal']==8100
provenance=read(RUN/'sdmpc/run_provenance_sdmpc31_sdmpc8100_s29.json')
assert provenance['seed']==29 and provenance['sim_period_sec']==8100 and provenance['control_interval_sec']==150
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import offramp_routing as route
contract=read(ROOT/'diagnostics/repin_v3c3_review_20261001/unrouted10646/route_contract.json')
rt=route.compile_inventory(contract,read(ROOT/contract['mapping']['path']))
bs=rt['bounds']['FW_E'];sub=(bs[16]-bs[15])/3
rows=[]
for t in range(900,8101,150):
    raw=read(F/f'state_{t:06d}.json');assert raw['sim_sec']==t and raw['vehicle_records']['complete']
    groups=[[] for _ in range(7)]
    for v in raw['vehicle_records']['records']:
        physical=rt['physical'].get(str(v['link_no']))
        if physical is None:continue
        road,offset=physical
        if road!='FW_E' or not bs[14]<=offset+v['position_m']<bs[19]:continue
        road,pos,i=route._position(rt,v['link_no'],v['position_m'])
        j=0 if i==14 else (1+min(2,int((pos-bs[15])/sub)) if i==15 else i-12)
        groups[j].append(v['speed_kph'])
    assert all(groups),(t,'empty component')
    row=dict(time=t,n=[len(g) for g in groups],speed=[sum(g)/len(g) for g in groups])
    if t<8100:
        action=read(F/f'action_{t:06d}.json')
        assert all(float(v)==110 for v in action['vsl'].values()),t
        row['command_applied']=(F/f'action_{t:06d}.json.applied').is_file()
    rows.append(row)
O.mkdir(exist_ok=True)
save(O/'off110_snapshots.json',dict(status='complete',rows=rows,bin_names=['14','15a','15b','15c','16','17','18'],
    length_m=[bs[15]-bs[14],sub,sub,sub,*[bs[i+1]-bs[i] for i in range(16,19)]],
    decision_folder=str(F),source_pins=PINS,new_fzp_scans=0,new_forecasts=0,new_native=0,
    independent_evaluation_reserved=['seed67 release versus release_vsl90','seed71 rm versus both'],
    scope='110 at all commands. Completed native OFF under recorded city/RM. Later state/controls differ from hold2250; never treat later policies as a common causal prefix.'))
for r in rows:
    if r['time']%450==0:
        print(json.dumps(dict(t=r['time'],n15=r['n'][1:4],v15=[round(v,1) for v in r['speed'][1:4]],v18=round(r['speed'][-1],1))))
