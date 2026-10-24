"""Frozen-parameter causal replay and separately labeled conditional checks."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.ramp_response_20260919.calibrate_ramps import *
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.spatial_calibration_20260919 import calibrate as spatial

def main():
    out=HERE/'evaluation_v1';out.mkdir(exist_ok=False)
    candidate=HERE/'local_v1/model'
    # The FD and all non-ramp settings must remain bit-identical to the most
    # recent spatial model, not the older v5 configuration.
    old=e.load(BASE/'config.json');new=e.load(candidate/'config.json')
    allowed={'physical_ramp_receiving_nodes','physical_ramp_travel_speeds'}
    before=copy.deepcopy(old);after=copy.deepcopy(new)
    for cfg in [before,after]:
        for key in allowed:cfg['freeway'].pop(key,None)
    assert before==after,'Changed non-ramp config'
    assert e.load(BASE/'selected_parameters.json')==e.load(candidate/'selected_parameters.json')
    pins=[candidate/'config.json',candidate/'selected_parameters.json',candidate/'port_profile.json',
        ROOT/new['freeway']['segment_params'],e.CAL/'canonical_harness.py',
        ROOT/'evaluation/controllers/physical_ramp_boundary.py',H/'evaluate_response.py']
    freeze={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}
    write(out/'freeze.json',freeze)
    spatial.BASE=BASE
    spatial.evaluate(out,candidate)
    fits=e.load(HERE/'local_v1/selected.json');conditional={}
    for seed,folder,bank,start in [(13,H/'controller_response_4500_v1/none',H/'response_pairs_v1',1650),
            (23,H/'controller_response_s23_v1/none',H/'response_late_s23_v1',2400),
            (33,H/'state_response_20260919/native_s33_v1/observations/none',H/'state_response_20260919/native_s33_v1',2400)]:
        data=prepare_data(folder);model=e.load_base_model(data.geometry,BASE/'config.json')
        pairs=prepare_data(bank/'observations/rm_ramp');seq=e.load(bank/'protocol.json')['candidate_bank']['rm_ramp']['green']
        def cmd(t):return ({'RM_C10490':seq[int((t-start)//150)]},{})
        conditional[str(seed)]={}
        for mid in TARGETS:
            cases=[local_case(data,model,t,mid,lambda t: ({},{})) for t in STARTS]
            cases+=[local_case(pairs,model,start,mid,cmd)]
            variants={}
            for name,speed,gap in [('baseline',None,None),('ramp',fits[mid]['speeds'],fits[mid]['gap'])]:
                records=[replay(c,speed,gap) for c in cases]
                variants[name]={'loss':statistics.mean(r['loss'] for r in records),
                    'mae':{k:statistics.mean(abs(r['predicted'][k]-r['actual'][k]) for r in records) for k in records[0]['predicted']},'records':records}
            conditional[str(seed)][mid]=variants
        print('conditional',seed,{m:{v:r['mae'] for v,r in vs.items()} for m,vs in conditional[str(seed)].items()},flush=True)
    write(out/'conditional_replay.json',conditional)
    for p,digest in freeze.items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest
    write(out/'frozen_check.json',{'non_ramp_config_exact':True,'mainline_parameters_exact':True,'frozen_files_unchanged':True})

if __name__=='__main__':main()
