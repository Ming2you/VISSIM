"""Use the existing MPC selector on completed NC snapshots; no native run."""
import copy
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
H=HERE.parent
sys.path.insert(0,str(H.parents[2]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e

def main():
    out=HERE/'decisions_v1';out.mkdir(exist_ok=False)
    original_loader=e.online_data
    policy=e.load(H/'mpc_4500_s23_v1/prepared_both/rule_policy.json')
    template=e.load(H/'mpc_4500_s23_v1/prepared_both/mpc_policy.json')
    summary=[]
    for seed,folder in [(13,'controller_response_4500_v1/none'),(23,'controller_response_s23_v1/none')]:
        data=e.ObservationData(H/folder)
        for version in ['model_v4','model_v5_node']:
            modeldir=H/'controller_response_4500_v1'/version
            prepared=out/f's{seed}_{version}';prepared.mkdir()
            model=e.load_base_model(data.geometry,modeldir/'config.json')
            files=[modeldir/n for n in ['config.json','selected_parameters.json','port_profile.json']]
            files += [e.ROOT/n for n in model.provenance['model_files']]
            files += [Path(e.__file__),e.CAL/'canonical_harness.py']
            contract=copy.deepcopy(template);contract['model_directory']=str(modeldir)
            contract['model_pins']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
            contract['scope']='Recorded NC state replay through existing MPC selector; not a native closed-loop run or GNE certification'
            e.save(prepared/'mpc_policy.json',contract)
            history={'greens':{m:10 for m in model.ramps},'states':{},
                'vsl':{str(d):120 for ds in policy['zone_dsds'].values() for d in ds}}
            for sec in [900,1650,2400,3000,3600]:
                # Replace acquisition only. Actual plant/candidates/cost/ranking
                # and budget remain the installed live decision implementation.
                def recorded_loader(*args):
                    return data,{'recorded_seed':seed,'cutoff':sec,'future_traffic_used':False}
                e.online_data=recorded_loader
                try:r=e.mpc_choice(prepared,prepared,sec,history,policy)
                finally:e.online_data=original_loader
                summary.append({'seed':seed,'version':version,'sec':sec,**r})
                print(seed,version,sec,r['selected'],round(r['hold_cost_veh_h']-r['predicted_cost_veh_h'],5),flush=True)
    e.save(out/'summary.json',summary)

if __name__=='__main__':main()
