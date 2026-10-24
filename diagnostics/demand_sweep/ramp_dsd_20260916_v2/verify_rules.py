"""After all runs: replay recorded rule inputs and verify actual native records."""
import csv
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from diagnostics.fast_fixed_profile import rule_step
from diagnostics.fast_fixed_profile_verify import verify, prefix_digest


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--terminal-sec',type=int,choices=(3000,4500),default=3000)
    parser.add_argument('--runs',type=Path)
    parser.add_argument('--reference-none',type=Path)
    args=parser.parse_args();terminal=args.terminal_sec
    here=args.runs or Path(__file__).resolve().parent/('rules_v1' if terminal==3000 else 'rules_4500_v1')
    for arm in ('none','rm','vsl','both'):
        receipt=json.loads((here/f'run_{arm}/run.json').read_text(encoding='utf-8-sig'))
        assert receipt['completed'] and receipt['terminal_sec']==terminal and not receipt['owned_native_alive']
        meta=json.loads((here/f'prepared_{arm}/prepared.json').read_text())
        assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest for path,digest in meta['snapshot_sha256'].items())
    pins=json.loads((here/'code_pins.json').read_text())
    if (here/'validator_correction.json').exists():
        correction=json.loads((here/'validator_correction.json').read_text())
        assert pins[correction['path']]==correction['before']
        pins[correction['path']]=correction['after']
    assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest for path,digest in pins.items())
    result={}
    for arm in ('none','rm','vsl','both'):
        prepared,run=here/f'prepared_{arm}',here/f'run_{arm}'
        mpc=(prepared/'mpc_policy.json').exists()
        if mpc:
            from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response
            def recorded_choice(_prepared,_out,sec,_history,_cfg):
                decision=json.loads((run/f'decision_{sec}.json').read_text())['mpc']
                audit=json.loads((run/f'mpc_candidates_{sec}.json').read_text())
                selected=next(c for c in audit['candidates'] if c['name']==audit['selected'])
                assert selected['cost_veh_h']==min(c['cost_veh_h'] for c in audit['candidates'])
                assert selected['greens']==decision['greens'] and selected['zones']==decision['zones']
                assert audit['observation']['features_latest_realized_sec']==sec
                assert not audit['observation']['future_traffic_used']
                return decision
            evaluate_response.mpc_choice=recorded_choice
        with tempfile.TemporaryDirectory(dir=here) as tmp:
            out=Path(tmp)
            for sec in range(900,terminal,150):
                name=f'observation_{sec}.csv'
                (out/name).write_bytes((run/name).read_bytes())
                rule_step(prepared,out,sec)
                name=f'decision_{sec}.json'
                assert (out/name).read_bytes()==(run/name).read_bytes(), (arm,sec)
            assert (out/'fixed_events.csv').read_bytes()==(run/'fixed_events.csv').read_bytes()
        actual=verify(prepared,run,here/'run_none' if arm!='none' else None)
        result[arm]={'recorded_policy_replay_exact':True, 'ldp_and_readback_passed':actual['passed'],
            'event_readbacks':actual['event_readbacks'], 'native_meter_samples_checked':actual['native_meter_samples_checked'],
            'warmup':actual.get('paired_warmup_prefix')}
        if mpc:result[arm]['mpc_selected_minimum_recorded_cost_and_causal_cutoff']=True
        if terminal==4500 and not args.runs:
            old=here.parent/'rules_v1'/f'run_{arm}/vissim_eval/baseline_001.fzp'
            before=prefix_digest(old,3000)
            after=prefix_digest(run/'vissim_eval/baseline_001.fzp',3000)
            assert before==after, (arm,'Extending SimBreak changed an existing3000s prefix')
            result[arm]['same_policy_previous3000_prefix_exact']={'passed':True,'digest':before}
    if not args.runs or args.reference_none:
        prior=(args.reference_none/'vissim_eval/baseline_001.fzp') if args.reference_none else here.parent/'run_dsd/vissim_eval/baseline_001.fzp'
        current=here/'run_none/vissim_eval/baseline_001.fzp'
        extent=terminal if args.reference_none else 2250
        a,b=prefix_digest(prior,extent),prefix_digest(current,extent)
        result['instrumentation_continuous_execution_equivalence']={'passed':a==b,'prior':a,'current':b}
        assert a==b,'Observation or pause scheme changed native baseline traffic'
    (here/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
