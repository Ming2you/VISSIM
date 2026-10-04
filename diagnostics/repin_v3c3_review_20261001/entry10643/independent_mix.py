"""Independent seed43 native destination-population check; no fitting."""
import hashlib
import json
from pathlib import Path
from evaluation.controllers import obs150_contract as oc, offramp_routing as routing

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
pins={}
def read(path):
    raw=path.read_bytes();pins[str(path)]=hashlib.sha256(raw).hexdigest();return json.loads(raw)

def main():
    assert not (HERE/'independent_mix.json').exists()
    runtime=read(HERE/'native_cohorts.json')['route_runtime']
    folder=Path('D:/VISSIM_runs/20260929_seed43_observation2700/nc/decisions_sdmpc31_nc2700_s43')
    raws={t:read(folder/f'state_{t:06d}.json') for t in (2250,2400,2550,2700)}
    frames={t:read(Path(r['lane_plant_observation']['directory'])/f'frame_{t:06d}.json') for t,r in raws.items()}
    dets,h=oc.read_detector_csv(I/'selected/obs150/obs150_detectors_v2.csv');groups=oc.group_boundaries(dets)
    initial={v[0] for v in frames[2250]['vehicles'] if str(v[1]) in runtime['physical']}
    initial_known={v[0] for v in frames[2250]['vehicles'] if str(v[1]) in runtime['physical'] and v[6:8]==[1130.,1.]}
    source=[];off=[];tails=[]
    for t in (2400,2550,2700):
        bundle=oc.load_bundle(raws[t]);window=oc.assign_window(bundle.obs,bundle.mer_rows)
        for ref,dest in [('source:FW_E',source),('off_entry:10643',off)]:
            for det in groups[ref]:
                if window.tails[det.dcp_no]:tails.append(dict(end_sec=t,ref=ref,detector=det.dcp_no,count=window.tails[det.dcp_no]))
                dest.extend(dict(vehicle=e.veh,time_sec=e.t_entry) for e in window.entries[det.dcp_no])
    assert not any(x['ref']=='off_entry:10643' for x in tails)
    assert len({e['vehicle'] for e in off})==len(off)==76
    new_off={e['vehicle'] for e in off}-initial
    assert new_off<={e['vehicle'] for e in source}
    end_known=[];end_unknown=[]
    for v in frames[2700]['vehicles']:
        if v[0] in initial or str(v[1]) not in runtime['physical']:continue
        road,pos,cell=routing._position(runtime,v[1],v[3])
        if road!='FW_E' or pos>runtime['branches']['10643']['source_chain_m']:continue
        if v[6] is None:end_unknown.append(v[0])
        elif v[6:8]==[1130.,1.]:end_known.append(v[0])
    new_source={e['vehicle'] for e in source}-initial
    end_before={v[0] for v in frames[2700]['vehicles'] if v[0] not in initial and v[1]==74 and v[3]<40}
    prediction=read(I/'closedloop_recorded2250_lever450_trace10681_retained43/summary.json')['results']['held_actual']
    generated=prediction['control_area']['flow_counts']['origin:FW_E->freeway:FW_E']
    out=dict(status='COMPLETED_INDEPENDENT_NATIVE_MIX_CHECK',seed=43,start_sec=2250,end_sec=2700,
        native_off_entry=len(off),initial_known_count=len(initial_known),
        initial_known_exited=len(initial_known&{e['vehicle'] for e in off}),new_target_exited=len(new_off),
        new_target_retained=len(end_known),new_target_observed=len(new_off)+len(end_known),
        new_source_generation_lower_bound=len(new_source|end_before),source_tails=tails,
        unknown_new_mainline_before_exit=len(end_unknown),model_source_generated=generated,
        configured_target_probability=runtime['inputs']['FW_E']['weights']['10643'],
        expected_model_target_generated=generated*runtime['inputs']['FW_E']['weights']['10643'],
        source_pins=pins,new_native=0,new_fzp_scan=0,fit=0,
        limitation='This identifies realized destination population, not a replacement routing probability or proof of statistical independence.')
    (HERE/'independent_mix.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print({k:v for k,v in out.items() if k!='source_pins'})

if __name__=='__main__':main()
