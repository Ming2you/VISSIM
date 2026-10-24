"""Existing centralized MPC: isolate cost integration from physical transit."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.merge_drain_response_20260919.audit import *
import copy,hashlib

def main():
    out=HERE/'decisions_v1';out.mkdir(exist_ok=False)
    prior=H/'ramp_response_20260919/arrival_v1/gap84/model'
    paths={'sample30s':prior}
    for version,source in [('internal_cost',prior),('entry_and_cost',HERE/'causal_v1/model')]:
        folder=out/version;folder.mkdir()
        for name in ['config.json','selected_parameters.json','port_profile.json']:
            doc=e.load(source/name)
            if name=='config.json':doc['freeway']['physical_component_residence']=True
            write(folder/name,doc)
        paths[version]=folder
    policy=e.load(H/'mpc_4500_s23_v1/prepared_both/rule_policy.json')
    template=e.load(H/'mpc_4500_s23_v1/prepared_both/mpc_policy.json')
    original=e.online_data;summary=[]
    for seed,folder,bank,start in CASES:
        data=e.ObservationData(folder)
        for version,modeldir in paths.items():
            prepared=out/f's{seed}_{version}';prepared.mkdir()
            model=e.load_base_model(data.geometry,modeldir/'config.json')
            files=[modeldir/n for n in ['config.json','selected_parameters.json','port_profile.json']]
            files += [ROOT/n for n in model.provenance['model_files']]
            files += [Path(e.__file__),e.CAL/'canonical_harness.py']
            contract=copy.deepcopy(template);contract['model_directory']=str(modeldir)
            contract['model_pins']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
            contract['scope']='Recorded-state centralized RM/VSL MPC; not native closed-loop or full GNE'
            write(prepared/'mpc_policy.json',contract)
            history={'greens':{m:10 for m in model.ramps},'states':{},
                'vsl':{str(d):120 for ds in policy['zone_dsds'].values() for d in ds}}
            for sec in [start,3600]:
                e.online_data=lambda *args:(data,{'recorded_seed':seed,'cutoff':sec,'future_traffic_used':False})
                try:r=e.mpc_choice(prepared,prepared,sec,history,policy)
                finally:e.online_data=original
                summary.append({'seed':seed,'version':version,'sec':sec,**r})
                print(seed,version,sec,r['selected'],round(r['hold_cost_veh_h']-r['predicted_cost_veh_h'],6),flush=True)
                write(out/'summary.json',summary)

if __name__=='__main__':main()
