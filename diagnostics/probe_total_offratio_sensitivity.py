"""One paired150s private-config sensitivity; no optimizer or plant execution."""
from __future__ import annotations
import copy
import argparse
import hashlib
import json
import os
from pathlib import Path
import pickle
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
os.environ['RW_OFFSET_WRITER']='experiment'
os.environ['RW_MAINLINE_SG_ONLY']='1'
from diagnostics.probe_model_area_integration import build_projected
from evaluation.controllers import vissim_stackelberg_adapter as adapter,area_runtime
from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts
from src.models.state import ControlAction
from src.models.demand import DemandStep
from src.controllers.rollout_endpoint import evaluate_price_point,ObjectiveSpec
from src.simulation import coupling

RUN=ROOT/'evaluation/runs/codex_area_beta0_s13_20260910'
DEC=RUN/('decisions_'+RUN.name)
CONFIG=ROOT/'diagnostics/area_candidate_configs/n7_area_beta0.json'
NATIVE={'OR_F_E':5.6/13.6,'OR_D_E':7/15,'OR_D_W':6/16,'OR_F_W':4/12}


def load(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def frozen(value): return hashlib.sha256(pickle.dumps(value,protocol=5)).hexdigest()
def fingerprints(paths): return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}


def main():
    start=time.monotonic()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',default=RUN.name)
    parser.add_argument('--start',type=int,default=900)
    parser.add_argument('--config',type=Path,default=CONFIG)
    parser.add_argument('--reference',type=Path,default=ROOT/'diagnostics/live_beta0_interval_prediction.json')
    parser.add_argument('--include-native-direct',action='store_true')
    parser.add_argument('--out',type=Path,default=ROOT/'diagnostics/total_offratio_interval_sensitivity.json')
    args=parser.parse_args()
    run=(ROOT/'evaluation/runs'/args.run).resolve()
    if run.parent!=(ROOT/'evaluation/runs').resolve(): raise ValueError('Run must be a direct child of evaluation/runs')
    dec=run/('decisions_'+run.name)
    config,reference,path=args.config.resolve(),args.reference.resolve(),args.out.resolve()
    if not path.is_relative_to((ROOT/'diagnostics').resolve()) or path.exists():
        raise ValueError('A new output under diagnostics is required')
    state_path=dec/f'state_{args.start:06d}.json'
    action_path=dec/f'action_{args.start:06d}.json'
    previous=max((p for p in dec.glob('action_*.json') if int(p.stem.split('_')[-1])<args.start),
                 key=lambda p:int(p.stem.split('_')[-1]))
    manifest=load(run/'area_candidate_source_manifest.json')
    native_path=ROOT/'diagnostics/total_offramp_ratio_audit.json'
    native_audit=load(native_path)
    primary=next(row for row in native_audit['sources'] if row['path'].endswith('.inpx'))
    if hashlib.sha256(Path(primary['path']).read_bytes()).hexdigest()!=primary['sha256']:
        raise ValueError('Native route evidence network changed')
    direct_prior={row['group']:row['direct_weight']/(row['direct_weight']+row['signal_weight']) for row in native_audit['table']}
    if {row['group']:row['total_off_prior'] for row in native_audit['table']}!=NATIVE:
        raise ValueError('Native route prior differs from the verified evidence')
    sources=[ROOT/p for p in manifest['source_sha256']]
    sources+=list((ROOT/'evaluation/controllers').glob('*.py'))+list((ROOT/'vendor/NumSim-mine/src').rglob('*.py'))
    sources+=[config,state_path,previous,action_path,reference,native_path,Path(__file__)]
    before=fingerprints(sources)
    cfg,state,detectors,tuning,raw,mapping,metadata=build_projected(config,state_path,previous,fixture_inputs=False)
    if float(raw['sim_sec'])!=args.start: raise ValueError('Snapshot time mismatch')
    calibration=adapter.deep_update(dict(adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))),tuning.get('calibration_override',{}))
    forecast=adapter.demand_from_state(raw,cfg,DemandStep,1,calibration,detectors)
    action=adapter.control_from_json(action_path,cfg,ControlAction)
    initial=frozen((cfg,state,forecast,action))
    results=[]
    alternatives=[('baseline',dict(cfg.network.off_ramp_split_ratio),None),('native_conditional_total_sensitivity',NATIVE,None)]
    if args.include_native_direct:
        alternatives.append(('native_conditional_total_and_direct_sensitivity',NATIVE,direct_prior))
    for name,ratios,direct_alternative in alternatives:
        private_cfg=copy.deepcopy(cfg)
        private_cfg.network.off_ramp_split_ratio=dict(ratios)
        if direct_alternative is not None:
            private_cfg.network.offramp_direct_share_by_offramp=dict(direct_alternative)
        private_state,private_forecast,private_action=copy.deepcopy((state,forecast,action))
        calls=[]
        original=coupling.freeway_substep
        def observe(*args,**kwargs):
            if args[3] is not private_cfg: raise AssertionError('Endpoint did not use the private configuration')
            for field in ('green_times','offsets','vsl','ramp_metering'):
                if getattr(args[1],field)!=getattr(action,field): raise AssertionError('Held control changed: '+field)
            value=original(*args,**kwargs)
            calls.append({off:{'accepted_vph':value[1]['offramp_flow_'+off],
                              'blocked_vph':value[1]['offramp_blocked_flow_'+off]} for off in private_cfg.network.off_ramps})
            return value
        with patch.object(coupling,'freeway_substep',observe):
            point=evaluate_price_point(private_state,private_action,private_forecast,[],
                ObjectiveSpec(private_cfg,depth_override=1,box_walk=False,score_mode='raw'))
        if point.aborted or len(calls)!=15: raise AssertionError('Incomplete150s held-action endpoint')
        last=point.states[-1]
        last._control_area_ledger.assert_stocks(area_runtime.model_inventory(last,private_cfg))
        counts=continuity_vehicle_counts(last,private_cfg)
        direct=dict(private_cfg.network.offramp_direct_share_by_offramp)
        if direct!=(direct_alternative or cfg.network.offramp_direct_share_by_offramp): raise AssertionError('Conditional direct branch share changed unexpectedly')
        metrics=dict(point.control_area)
        # Keep the flow ledger separate from scalar metrics for clear inspection.
        flows=metrics.pop('flow_counts')
        results.append({'name':name,'off_ramp_split_ratio':ratios,'conditional_direct_share':direct,
            'metrics':metrics,'final_omega_veh':sum(v['inside'] for v in last._control_area_ledger.stocks.values()),
            'final_freeway_count_by_direction_veh':{k:sum(v) for k,v in counts.items()},
            'FW_E8':{'count_veh':counts['FW_E'][8],'speed_kph':last.freeway_speed['FW_E'][8]},
            'FW_E9':{'count_veh':counts['FW_E'][9],'speed_kph':last.freeway_speed['FW_E'][9]},
            'ramp_final_queue_veh':dict(last.ramp_queue),
            'offramp_flows':{off:{'requested_veh':sum((r[off]['accepted_vph']+r[off]['blocked_vph'])*cfg.simulation.T_f_h for r in calls),
                                 'accepted_veh':sum(r[off]['accepted_vph']*cfg.simulation.T_f_h for r in calls),
                                 'blocked_veh':sum(r[off]['blocked_vph']*cfg.simulation.T_f_h for r in calls)} for off in ratios},
            'accepted_flow_10s_trace':calls,'area_flow_ledger_veh':flows,'model_stock_closure_valid':True})
    if frozen((cfg,state,forecast,action))!=initial: raise AssertionError('Baseline cfg/state/demand/action mutated')
    baseline=results[0]
    expected=load(reference)['model']['metrics']
    for key in ('ttt_veh_h','ttd_veh','entered_veh'):
        if abs(baseline['metrics'][key]-expected[key])>1e-8: raise AssertionError('Actual-action baseline is not reproducible: '+key)
    after=fingerprints(sources)
    changed={key:{'before':value,'after':after[key]} for key,value in before.items() if value!=after[key]}
    if changed: raise AssertionError('Production/input source changed during paired probe: '+str(changed))
    algebra={off:baseline['offramp_flows'][off]['requested_veh']/baseline['off_ramp_split_ratio'][off]*NATIVE[off] for off in NATIVE}
    report={'schema':'offratio-private-sensitivity/v2','run':run.name,'interval_sec':[args.start,args.start+150],
        'method':'Actual recorded action and its previous-action context, canonical runtime; private cfg/state/demand/action copies for each150s endpoint.',
        'inputs':{'state':str(state_path.relative_to(ROOT)),'action':str(action_path.relative_to(ROOT)),
                  'previous':str(previous.relative_to(ROOT)),'reference':str(reference.relative_to(ROOT))},
        'changed_parameters':['network.off_ramp_split_ratio']+(['network.offramp_direct_share_by_offramp'] if args.include_native_direct else []),'original_inputs_unchanged':True,
        'baseline_matches_actual_interval_replay':True,'source_sha256':before,'source_changes_during_probe':changed,
        'results':results,'fixed_baseline_gross_flow_algebra_only_veh':algebra,
        'fixed_baseline_gross_flow_algebra_total_veh':sum(algebra.values()),
        'limitations':['Native route fractions are conditional on reaching/applying decisions1130–1133; this is not a calibrated unconditional flow parameter.',
            'All alternatives retain aggregate model cell positions. The total-only arm retains existing direct shares; the optional joint arm uses native conditional direct shares. Neither repairs branch geometry, intermediate-merge cohort differences or bypass eligibility.',
            'The fixed-baseline-q arithmetic is not the dynamically recomputed alternative endpoint prediction.',
            'No candidate was applied to VISSIM; this is sensitivity evidence, not a performance gain or approved production setting.'],
        'elapsed_wall_sec':time.monotonic()-start}
    path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'results':[{k:r[k] for k in ('name','metrics','final_omega_veh','final_freeway_count_by_direction_veh','FW_E8','FW_E9','offramp_flows')} for r in results],
        'algebra_only_total_veh':sum(algebra.values()),'elapsed_wall_sec':report['elapsed_wall_sec']},indent=2))


if __name__=='__main__': main()
