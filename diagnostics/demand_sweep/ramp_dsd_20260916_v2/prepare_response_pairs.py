"""Small, same-state actuator bank; immutable native traffic and existing writer."""
import hashlib
import argparse
import json
import re
import shutil
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from diagnostics.fast_fixed_profile import prepare


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--late-response',action='store_true')
    parser.add_argument('--seed',type=int)
    parser.add_argument('--destination',type=Path)
    args=parser.parse_args()
    here = Path(__file__).resolve().parent
    if args.late_response:
        prepare_late_response(here,23 if args.seed is None else args.seed,args.destination)
        return
    if args.seed is not None or args.destination is not None:
        parser.error('--seed and --destination require --late-response')
    out = here/'response_pairs_v1'
    out.mkdir(exist_ok=False)
    network = here/'rules_v1/prepared_none/network/baseline.inpx'
    digest = hashlib.sha256(network.read_bytes()).hexdigest()
    protocol = {
        'network_sha256': digest, 'seed': 13, 'start_s': 1650,
        'evaluation_end_s': 2100, 'run_end_s': 2250,
        'baseline_run': str(here/'rules_v1/run_none'),
        'baseline_reuse_gate': 'FZP data rows exact through1650; native untargeted LDP exact',
        'scope': 'Actuator-response diagnosis, not full GNE feasibility or independent holdout',
        'fixed_others': 'Native urban signals, demand, routes, seven other meters, all other DSDs',
        'rank_metric': 'Omega TTT with losses/uninserted reported; matched component separately',
        'candidate_bank': {
            'rm8': {'green': [8,8,8,8], 'vsl': []},
            'rm_ramp': {'green': [8,6,4,4], 'vsl': []},
            'vsl': {'green': [], 'vsl': [100,80,80,80]},
            'both': {'green': [8,6,4,4], 'vsl': [100,80,80,80]},
        },
        'interpretation': '2s green and20 VSL-ID units/150s limits honored; N_P/N_UF not imposed in causal diagnostic. Restriction benefit is not assumed.',
    }
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    for arm, sequence in protocol['candidate_bank'].items():
        profile = {'schema':'native-fixed-profile/v1','network_sha256':digest,
            'seed':13,'control_start_sec':1650,'terminal_sec':2250,
            'native_off_service_anchor_green_sec':10,
            'meter_commands':[{'time_s':1650+150*i,'sc_no':9107,'green_sec':g}
                for i,g in enumerate(sequence['green'])],
            'vsl_commands':[{'time_s':1650+150*i,'dsd_no':d,'speed_id':v}
                for i,v in enumerate(sequence['vsl']) for d in (59,60,61,62)]}
        path=out/(arm+'.json')
        path.write_text(json.dumps(profile,indent=2),encoding='utf-8')
        prepare(network,path,out/('prepared_'+arm))
    print(out)


def prepare_late_response(here,seed=23,destination=None):
    """Freeze commands before looking at their same-state native outcomes."""
    if seed<=0:raise ValueError('Seed must be positive')
    fresh=seed!=23
    out=destination or here/f'response_late_s{seed}_v1';out.mkdir(parents=True,exist_ok=False)
    source=here/'rules_4500_s23_v1'
    network=source/'prepared_none/network/baseline.inpx'
    source_digest=hashlib.sha256(network.read_bytes()).hexdigest()
    if fresh:
        # Copy support signal files with the frozen input; edit only randSeed.
        target=out/'source/network';shutil.copytree(network.parent,target)
        network=target/network.name
        content,n=re.subn(rb'(<simulation\b[^>]*\brandSeed=")[0-9]+',
            lambda m:m[1]+str(seed).encode('ascii'),network.read_bytes())
        if n!=1:raise ValueError('Expected exactly one simulation seed attribute')
        network.write_bytes(content)
    digest=hashlib.sha256(network.read_bytes()).hexdigest()
    policy=json.loads((source/'prepared_none/rule_policy.json').read_text())
    times=list(range(2400,3750,150))
    bank={
        'rm8':{'green':[8,8,8,8,8,8,10,10,10],'vsl':[]},
        'rm_ramp':{'green':[8,6,4,4,4,4,6,8,10],'vsl':[]},
        'vsl':{'green':[],'vsl':[100,100,100,100,100,100,120,120,120]},
        'both':{'green':[8,6,4,4,4,4,6,8,10],'vsl':[100,100,100,100,100,100,120,120,120]},
    }
    if fresh:
        bank={'none':{'green':[],'vsl':[]},**{k:v for k,v in bank.items() if k!='rm8'}}
    protocol={'network_sha256':digest,'seed':seed,'start_s':2400,'evaluation_end_s':2850,
        'run_end_s':4500,'command_times':times,'baseline_run':str(source/'run_none'),
        'baseline_observations':str(here/'controller_response_s23_v1/none'),
        'baseline_reuse_gate':'Exact FZP payload through2400 and unchanged non-target LDP',
        'candidate_bank':bank,'meter_sc':9107,'meter_id':'RM_C10490',
        'vsl_zone':'FW_E__seg5','dsd_ids':policy['zone_dsds']['FW_E__seg5'],
        'actual_windows':[[2400,2850],[2400,3300],[3300,4500],[2400,4500]],
        'selection_basis':'Existing seed23 untreated sustained10702 low speed starts2700; model selected mild upstream VSL from2400',
        'scope':'Same-state causal diagnosis, not full GNE. Seed23 previously observed; not a new unseen seed.',
        'fixed_others':'Physical network, inputs, routes, urban signals, seven other meters and other VSL zones',
        'interpretation':'First450s tests model horizon; later windows expose delayed benefits and displaced queues. No outcome-dependent command changes.'}
    if fresh:
        protocol.update(baseline_run=str(out/'run_none'),baseline_observations=str(out/'observations/none'),
            selection_basis='Commands/times frozen from seed23 protocol before viewing this seed; no event time selected from new outcomes',
            scope='Fresh-seed paired actuator response, fixed commands; not closed-loop MPC or full GNE',
            source_network_sha256=source_digest,source_edit='simulation.randSeed only')
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    for arm,sequence in bank.items():
        profile={'schema':'native-fixed-profile/v1','network_sha256':digest,'seed':seed,
            'control_start_sec':2400,'terminal_sec':4500,'native_off_service_anchor_green_sec':10,
            'meter_commands':[{'time_s':t,'sc_no':9107,'green_sec':g} for t,g in zip(times,sequence['green'])],
            'vsl_commands':[{'time_s':t,'dsd_no':d,'speed_id':v} for t,v in zip(times,sequence['vsl']) for d in protocol['dsd_ids']]}
        path=out/(arm+'.json');path.write_text(json.dumps(profile,indent=2),encoding='utf-8')
        prepare(network,path,out/f'prepared_{arm}')
    print(out)


if __name__=='__main__':main()
