"""Add no-control desired-speed observations with unchanged native physics."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from diagnostics.fast_fixed_profile import prepare
import xml.etree.ElementTree as ET
import hashlib
import argparse

HERE=Path(__file__).resolve().parent;H=HERE.parent


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--fresh-seed',type=int)
    args=parser.parse_args()
    fresh=args.fresh_seed is not None
    out=HERE/(f'fresh_s{args.fresh_seed}_v1' if fresh else 'native_v1');out.mkdir(exist_ok=False)
    source=H/'dsd_response_20260920/native_v2/prepared/network/baseline.inpx'
    cases=[(args.fresh_seed,arm) for arm in ['none','rm_ramp','vsl','both']] if fresh else [(seed,'none') for seed in [23,33]]
    for seed,arm in cases:
        folder=out/(arm if fresh else f'none_s{seed}');folder.mkdir();target=folder/'source';target.mkdir()
        root=ET.parse(source).getroot();root.find('simulation').set('randSeed',str(seed))
        network=target/'baseline.inpx'
        network.write_bytes(b'<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(root,encoding='utf-8'))
        for name in set(v[6:] for node in root.iter() for v in node.attrib.values() if v.startswith('#data#')):
            assert Path(name).name==name
            (target/name).write_bytes((source.parent/name).read_bytes())
        template=H/f'state_response_20260919/native_s33_v1/{arm}.json' if fresh else H/'dsd_response_20260920/native_v2/profile.json'
        profile=e.load(template)
        profile.update(seed=seed,terminal_sec=3000,network_sha256=hashlib.sha256(network.read_bytes()).hexdigest())
        for key in ['meter_commands','vsl_commands']:
            profile[key]=[row for row in profile[key] if row['time_s']<3000] if fresh else []
        e.save(folder/'profile.json',profile);prepare(network,folder/'profile.json',folder/'prepared')
    if fresh:
        protocol=e.load(H/'state_response_20260919/native_s33_v1/protocol.json')
        for key in ['baseline_run','baseline_observations','network_sha256','source_network_sha256']:
            protocol.pop(key,None)
        protocol.update(seed=args.fresh_seed,run_end_s=3000,actual_windows=[[2400,2850]],
            source_network=str(source.relative_to(e.ROOT)),
            selection_basis='Protocol and two unqualified models frozen before inspecting this seed. Prospective falsification, not adoption.',
            scope='FW_E mainline plus four east on/off connectors; fixed commands, not Omega or full GNE')
        protocol['command_times']=[t for t in protocol['command_times'] if t<3000]
        for seq in protocol['candidate_bank'].values():
            for key in ['green','vsl']:seq[key]=seq[key][:4]
        e.save(out/'protocol.json',protocol)
        models={'reference':H/'merge_drain_response_20260919/decisions_v1/internal_cost',
                'port_travel':HERE/'port_travel_fit_v1'}
        files=[Path(__file__).resolve(),e.ROOT/'evaluation/controllers/physical_lane_groups.py',
               e.ROOT/'diagnostics/fast_nc_runner.vbs',e.ROOT/'diagnostics/fast_nc_run.ps1',
               e.ROOT/'diagnostics/fast_fixed_profile.py',Path(e.__file__).resolve(),
               e.ROOT/'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py']
        for folder in models.values():files.extend([folder/'config.json',folder/'selected_parameters.json'])
        files.extend([models['reference']/'port_profile.json',out/'protocol.json',source])
        e.save(out/'model_freeze.json',{'models':{k:str(v.relative_to(e.ROOT)) for k,v in models.items()},
            'port_profile':str((models['reference']/'port_profile.json').relative_to(e.ROOT)),
            'pins':{str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
            'qualified':False,'prospective_seed':args.fresh_seed,'use_outcomes_for_this_test_fit':False})
        return
    e.save(out/'protocol.json',{'purpose':'Observe native desired-speed moments for baseline/control contrasts',
        'terminal_s':3000,'seeds':[23,33],'commands':[],
        'required_gate':'All nine original FZP fields identical through3000s to the completed same-seed no-control recordings',
        'claim':'Observation repeats, not independent benefit samples; unchanged physical settings/demand/routes/signals',
        'watchdog':'Existing owned-process300s startup watchdog; no vehicle COM queries'})


if __name__=='__main__':main()
