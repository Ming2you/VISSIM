"""Seed13-only bounded fitting of existing parameters using450s open rollouts.

No optimizer supplies traffic physics. Every candidate uses canonical_harness.
The parent boundary factory owns information cutoffs and replay labeling.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT/'diagnostics/rule_baseline_20260914/.plot-deps'))
from canonical_harness import load_base_model, PARAMETER_BOUNDS, OPTIONAL_PARAMETER_BOUNDS, BASELINE_PARAMETERS, sha256

NORMALIZATION = {'density_veh_km_lane':10.0, 'speed_kmh':20.0, 'flow_veh_h':1000.0}
FAILURE_SCORE = 1e12  # Hard transition exceptions must not outrank audited invalid rollouts.


def score_windows(model, windows, data, road, parameters):
    from scoring import score_rollout
    scores = []
    for window in windows:
        try:
            rollout = model.rollout(window['initial_cells'], window['boundary_steps'],
                parameters, window['initial_origin_queue'], roads=(road,),
                port_dynamics=window.get('port_dynamics'))
            scores.append(score_rollout(data, window['meta']['cutoff_s'], rollout, road))
        except (ArithmeticError,ValueError,OverflowError) as exc:
            scores.append({'objective':FAILURE_SCORE,'invalid':True,'road':road,
                'cutoff_s':window['meta']['cutoff_s'],'failure':type(exc).__name__+': '+str(exc)})
    return {'objective': math.fsum(row['objective'] for row in scores)/len(scores),
            'window_scores': scores}


def optimize_direction(model, windows, data, road, output, max_evaluations=100, initial_parameters=None, fit_keys=None):
    initial_parameters = dict(BASELINE_PARAMETERS if initial_parameters is None else initial_parameters)
    keys = tuple(PARAMETER_BOUNDS if fit_keys is None else fit_keys)
    all_bounds = {**PARAMETER_BOUNDS, **OPTIONAL_PARAMETER_BOUNDS}
    if not keys or set(keys)-all_bounds.keys() or set(keys)-initial_parameters.keys():
        raise ValueError('Fit keys must have explicit initial values and supported bounds')
    bounds = [all_bounds[k] for k in keys]
    def encode(params):
        return tuple((params[k]-lo)/(hi-lo) for k,(lo,hi) in zip(keys,bounds))
    def decode(x):
        return {**initial_parameters, **{k:lo+u*(hi-lo) for k,u,(lo,hi) in zip(keys,x,bounds)}}
    cache,records = {},[]
    started = time.monotonic()
    def evaluate(x, phase):
        x = tuple(min(1,max(0,v)) for v in x)
        if x in cache:
            return cache[x]
        params = dict(initial_parameters) if phase == 'baseline' else decode(x)
        try:
            result = score_windows(model,windows,data,road,{'by_direction':{road:params}})
        except (ArithmeticError,ValueError,OverflowError) as exc:
            result = {'objective':FAILURE_SCORE,'failure':type(exc).__name__+': '+str(exc)}
        record = {'evaluation':len(records)+1,'road':road,'phase':phase,'parameters':params,
                  'elapsed_seconds':time.monotonic()-started,**result}
        records.append(record)
        with output.open('a',encoding='utf-8') as stream:
            compact = {k:v for k,v in record.items() if k != 'window_scores'}
            compact['window_scores'] = [{k:r[k] for k in ('cutoff_s','objective','invalid','failure',
                'density','speed','flow_vph','diagnostics') if k in r} for r in result.get('window_scores',[])]
            stream.write(json.dumps(compact,allow_nan=False)+'\n')
        if len(records) == 1 or len(records)%10 == 0:
            print(json.dumps({'road':road,'evaluations':len(records),'objective':result['objective'],
                              'elapsed_seconds':round(record['elapsed_seconds'],1)}),flush=True)
        cache[x] = (result['objective'],x,result)
        return cache[x]
    baseline = evaluate(encode(initial_parameters),'baseline')
    best = baseline
    # Bounded deterministic pattern search starts from the actual baseline.
    # Allocate work to every scale; the evaluation cap is not a convergence or
    # global-optimality claim, and the complete search trace is retained.
    for delta in (.2,.1,.05):
        stage_limit = min(max_evaluations,len(records)+max(12,(max_evaluations-1)//3))
        improved = True
        while improved and len(records) < stage_limit:
            improved = False
            for index in range(len(keys)):
                anchor = best[1]
                candidates = []
                for sign in (-1,1):
                    if len(records) >= stage_limit:
                        break
                    point = list(anchor)
                    point[index] += sign*delta
                    candidates.append(evaluate(point,'pattern_'+str(delta)))
                candidate = min(candidates,key=lambda v:v[0]) if candidates else best
                if candidate[0] < best[0]-1e-10:
                    best = candidate
                    improved = True
    return {'parameters':decode(best[1]),'baseline_training':baseline[2],
            'calibrated_training':best[2],'evaluations':len(records),
            'elapsed_seconds':time.monotonic()-started,'optimizer':'baseline-start bounded coordinate pattern search (.2,.1,.05 normalized steps)'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--observations',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--max-evaluations',type=int,default=100)
    parser.add_argument('--initial-parameters',type=Path)
    parser.add_argument('--fit-keys',nargs='+')
    parser.add_argument('--port-profile',type=Path)
    args = parser.parse_args()
    if 'seed13' not in str(args.observations).lower():
        raise ValueError('Fitter accepts seed13 observations only')
    if args.out.exists():
        raise FileExistsError('Preserve previous fit artifacts; choose a new output directory')
    from boundary_factory import ObservationData,build_window
    protocol = json.loads((HERE/'PROTOCOL.json').read_text(encoding='utf-8-sig'))
    manifest = json.loads((args.observations/'manifest.json').read_text(encoding='utf-8-sig'))
    if manifest['seed'] != 13 or manifest['network']['sha256'] != protocol['training_network_sha256']:
        raise ValueError('Training data must be the predeclared seed13 network')
    data = ObservationData(args.observations)
    geometry = json.loads((args.observations/'geometry.json').read_text(encoding='utf-8-sig'))
    model = load_base_model(geometry)
    initial = json.loads(args.initial_parameters.read_text(encoding='utf-8'))['parameters']['by_direction'] if args.initial_parameters else {}
    port_profile = json.loads(args.port_profile.read_text(encoding='utf-8')) if args.port_profile else None
    source_names = ('canonical_harness.py','calibrate.py','boundary_factory.py','extract_observations.py','scoring.py','PROTOCOL.json')
    input_names = ('geometry.json','cells_30s.csv','flows_30s.csv','boundaries_30s.csv')
    if port_profile:
        input_names += ('ports_30s.csv','port_cohorts_30s.json')
    source_hashes = {name:sha256(HERE/name) for name in source_names}
    input_hashes = {name:sha256(args.observations/name) for name in input_names}
    training = [build_window(data,t,'conditioned_diagnostic',port_profile) for t in protocol['training_cutoffs_sec']]
    validation = [build_window(data,t,'conditioned_diagnostic',port_profile) for t in protocol['seed13_validation_cutoffs_sec']]
    args.out.mkdir(parents=True)
    results = {}
    for road in ('FW_E','FW_W'):
        results[road] = optimize_direction(model,training,data,road,args.out/'search.jsonl',args.max_evaluations,
                                          initial_parameters=initial.get(road),fit_keys=args.fit_keys)
    parameters = {'by_direction':{road:row['parameters'] for road,row in results.items()}}
    for road in results:
        results[road]['baseline_temporal_validation'] = score_windows(model,validation,data,road,{'by_direction':initial} if initial else None)
        results[road]['calibrated_temporal_validation'] = score_windows(model,validation,data,road,parameters)
    # Imports are cached. A changed on-disk module cannot be labeled as the
    # version used by this fit; fail rather than freezing an ambiguous result.
    if source_hashes != {name:sha256(HERE/name) for name in source_names}:
        raise RuntimeError('Fitting/protocol sources changed during optimization')
    if input_hashes != {name:sha256(args.observations/name) for name in input_names}:
        raise RuntimeError('Training observations changed during optimization')
    if any(sha256(ROOT/path) != digest for path,digest in model.provenance['model_files'].items()):
        raise RuntimeError('Canonical model dependency changed during optimization')
    document = {'schema':'canonical-metanet-seed13-calibration/v1','training_seed':13,
        'fit_mode':'conditioned_diagnostic','parameters':parameters,'results':results,
        'normalization':NORMALIZATION,'objective':'mean across windows of shared scoring.py density/speed/physical total-outflow normalized MSE sum; full450s all30s endpoints',
        'bounds':PARAMETER_BOUNDS,'training_cutoffs_sec':protocol['training_cutoffs_sec'],
        'temporal_validation_cutoffs_sec':protocol['seed13_validation_cutoffs_sec'],
        'validation_role':'reported only; no parameter/model/optimizer selection from validation errors',
        'model_provenance':model.provenance,
        'port_profile':str(args.port_profile) if args.port_profile else None,
        'port_profile_sha256':sha256(args.port_profile) if args.port_profile else None,
        'initial_parameters_source':str(args.initial_parameters) if args.initial_parameters else None,
        'fit_keys':args.fit_keys,
        'input_sha256':input_hashes,'code_sha256':source_hashes}
    (args.out/'parameters.json').write_text(json.dumps(document,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    compact = {road:{'parameters':row['parameters'],'evaluations':row['evaluations'],
        **{key:row[key]['objective'] for key in ('baseline_training','calibrated_training',
            'baseline_temporal_validation','calibrated_temporal_validation')}} for road,row in results.items()}
    print(json.dumps({'parameters':str(args.out/'parameters.json'),'sha256':sha256(args.out/'parameters.json'),
                      'results':compact},ensure_ascii=False),flush=True)


if __name__ == '__main__':
    main()
