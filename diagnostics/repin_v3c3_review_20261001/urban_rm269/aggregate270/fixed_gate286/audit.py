"""Small cached-snapshot check of the known omitted intermediate fixed signal."""
import hashlib,json,sys,xml.etree.ElementTree as ET
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];H=HERE.parent.parent
sys.path.insert(0,str(ROOT))
from plant.src.vissim_strict.signal_program import parse_sig
PINS={}
def read(p):
    p=Path(p); b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)

def main():
    target=HERE/'assessment.json';assert not target.exists()
    verified=read(H/'sc6_transport/fixed_gate_native.json')
    assert verified['same_recorded_signal_both_arms']
    for p,h in verified['source_pins'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    old=read(H/'sc6_transport/assessment.json')
    info=old['intermediate_fixed_signal'];sig=Path(info['sig_file'])
    if not sig.exists():
        folder=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network'
        net=ET.fromstring((folder/'native_seed29.inpx').read_bytes())
        sc=net.find("./signalControllers/signalController[@no='10']")
        sig=folder/sc.get('supplyFile2').removeprefix('#data#')
    program=parse_sig(sig,1);PINS[str(sig)]=hashlib.sha256(sig.read_bytes()).hexdigest()
    headpos={int(h['lane'].split()[1]):float(h['pos']) for h in info['heads']}
    # Physical map only; do not equate this region to model origin stocks.
    pre={'1220015100','10212','136','10211','138','10215'}
    post={'10216','1220018302','10209','1210018302'}
    result={}
    for arm in ('hold','selected'):
        folder=Path(f'E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/{arm}/decisions_sdmpc31_g_2400_{arm}_s29')
        result[arm]=[]
        for t in (2400,2550,2700,2850):
            d=read(folder/f'state_{t:06}.json'); rows=d['vehicle_records']['records']; out={}
            groups={'pre_gate':[],'gate_link_before_head':[],'post_gate':[]}
            for r in rows:
                link=str(r['link_no'])
                if link in pre:groups['pre_gate'].append(r)
                elif link=='1220018301':
                    if r['position_m']<=headpos[r['lane_no']]:
                        groups['pre_gate'].append(r);groups['gate_link_before_head'].append(r)
                    else:groups['post_gate'].append(r)
                elif link in post and (link!='1210018302' or r['position_m']<=140.108794):groups['post_gate'].append(r)
            for k,rr in groups.items():
                lanes={str(lane):{'vehicles':sum(r['lane_no']==lane for r in rr),'stopped':sum(r['lane_no']==lane and r['stopped'] for r in rr)} for lane in sorted({r['lane_no'] for r in rr})}
                out[k]={'vehicles':len(rr),'stopped':sum(r['stopped'] for r in rr),'mean_speed_kph':sum(r['speed_kph'] for r in rr)/len(rr) if rr else None,'by_lane':lanes}
            out.update(time_sec=t,known_fixed_phase=program.state_at(t,'8'))
            result[arm].append(out)
    PINS[str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report={'status':'complete_cached_spatial_gate_diagnostic','gate':'SC10/SG8','model_gate_explicit':False,'native_fixed_program_verified_previously':True,'snapshots':result,'physical_support':{'pre_gate_links':sorted(pre|{'1220018301'}),'post_gate_links':sorted(post|{'1220018301'}),'gate_link_split_at_lane_head':headpos},'new_forecasts':0,'native_runs':0,'fzp_scans':0,'coefficient_fits':0,'source_pins':PINS,'limitations':['Snapshots do not provide gate discharge or continuous queue duration.','Observed downstream stopped stock may originate at SC6; it is not necessarily an SC10 effect.','This spatial region is not asserted equivalent to a generic model origin.','Future snapshots are diagnostic targets only; no forecast inputs changed.','An omitted active gate with stopped vehicles does not prove it causes the joint Omega gain error.']}
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for arm,rows in result.items():
        print(arm,[(r['time_sec'],r['known_fixed_phase'],r['pre_gate']['vehicles'],r['pre_gate']['stopped'],r['post_gate']['vehicles'],r['post_gate']['stopped']) for r in rows])
if __name__=='__main__':main()
