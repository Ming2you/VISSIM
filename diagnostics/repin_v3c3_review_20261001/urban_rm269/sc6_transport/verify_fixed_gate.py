"""Qualify the previously unverified intermediate fixed signal from closed LDP."""
import hashlib,json,sys
from pathlib import Path
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT))
from diagnostics.validate_native_signal_record import read_ldp_frames
from plant.src.vissim_strict.signal_program import parse_sig
def main():
    out=HERE/'fixed_gate_native.json';assert not out.exists()
    folder=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network'
    network=folder/'native_seed29.inpx';tree=ET.fromstring(network.read_bytes())
    controller=tree.find("./signalControllers/signalController[@no='10']")
    assert controller.get('type')=='FIXEDTIME' and controller.get('active')=='true'
    heads=[n for n in tree.findall('./signalHeads/signalHead') if n.get('sg')=='10 8']
    assert {n.get('lane') for n in heads}=={f'1220018301 {k}' for k in range(1,5)}
    sig=folder/controller.get('supplyFile2').removeprefix('#data#')
    program=parse_sig(sig,int(controller.get('progNo')))
    pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),network,sig,
        ROOT/'diagnostics/validate_native_signal_record.py',ROOT/'plant/src/vissim_strict/signal_program.py',HERE/'assessment.json']}
    arms={};records={}
    for arm in ('hold','selected'):
        file=Path(f'E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/{arm}/vissim_eval/sdmpc31_g_2400_{arm}_s29_10_001.ldp')
        record=read_ldp_frames({10:file},{10:list(range(1,9))},1800,2850)
        for p,d in record['pins'].items():pins[p]=d['sha256']
        frames=record['frames'];records[arm]=frames
        mismatches=[t for t,v in frames.items() if v['10:8']!=program.state_at(t,'8')]
        wrong_shift=[t for t,v in frames.items() if v['10:8']!=program.state_at(t-1,'8')]
        assert not mismatches and wrong_shift
        arms[arm]=dict(frame_count=len(frames),program_mismatches=mismatches,
            shifted_one_second_mismatch_count=len(wrong_shift),
            green_seconds_by_150=[dict(start_sec=a,end_sec=a+150,green_samples=sum(frames[t]['10:8']=='GREEN' for t in range(a+1,a+151))) for a in range(1800,2850,150)])
    assert records['hold']==records['selected']
    result=dict(status='native_fixed_gate_program_verified',native_controller=10,sg=8,
        head_link='1220018301',lanes=[1,2,3,4],period_sec=program.cycle_length_sec,offset_sec=program.program_offset_sec,
        arms=arms,same_recorded_signal_both_arms=True,
        model_current_delay='Aggregate available storage divided by observed lane-scaled speed; no explicit intermediate SC10 gate in this path.',
        new_native=0,new_forecasts=0,fzp_scans=0,coefficients_fitted=0,
        limitations=['Qualifies actual periodic gate execution at1s samples, not subsecond events or missing LSA.',
            'An active red gate does not by itself identify delay error or a joint gain cause; upstream platoon arrivals must be separated.',
            'Future LDP used only to verify the unchanged fixed program, never as a predictive future-state input.',
            'Supersedes the prior lack of native gate-clock confirmation; other geometry/readiness conclusions unchanged.'],source_pins=pins)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('SC10 SG8: 1051 frames per arm, zero program mismatches; native signal identical')
if __name__=='__main__':main()
