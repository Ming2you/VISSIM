"""Fixed 450s evaluation: baseline/calibrated core, two boundary modes, all windows."""
import argparse
import csv
import hashlib
import json
import math
import time
from pathlib import Path
from boundary_factory import ObservationData, build_window, PROTOCOL
from canonical_harness import load_base_model
from scoring import score_rollout, persistence_score

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def table(path,rows):
    if not rows: return
    with Path(path).open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def pooled(items,field):
    rows=[r[field] for r in items if field in r and r[field]['count']]
    n=sum(r['count'] for r in rows)
    return {'count':n,'rmse':math.sqrt(sum(r['rmse']**2*r['count'] for r in rows)/n) if n else None,
        'mae':sum(r['mae']*r['count'] for r in rows)/n if n else None,
        'bias':sum(r['bias']*r['count'] for r in rows)/n if n else None}


def check_freeze(path,parameters):
    frozen=json.loads(Path(path).read_text(encoding='utf-8'))
    for relative,digest in frozen['files'].items():
        if sha(ROOT/relative)!=digest: raise ValueError('Frozen file changed: '+relative)
    if sha(parameters)!=frozen['parameters_sha256']: raise ValueError('Parameters not frozen')
    return frozen


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,required=True)
    p.add_argument('--parameters',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--freeze',type=Path)
    p.add_argument('--seed13-validation',action='store_true')
    a=p.parse_args()
    if a.out.exists(): raise ValueError('New evaluation directory required')
    manifest=json.loads((a.data/'manifest.json').read_text(encoding='utf-8'))
    seed=manifest['seed']
    expected_network=PROTOCOL['training_network_sha256'] if a.seed13_validation else PROTOCOL['test_network_sha256']
    if manifest['network']['sha256']!=expected_network or manifest['terminal_sec']!=9000:
        raise ValueError('Unexpected network or incomplete observation horizon')
    for name,digest in manifest['files'].items():
        if sha(a.data/name)!=digest: raise ValueError('Observation output changed: '+name)
    if a.seed13_validation:
        if seed!=13: raise ValueError('Expected seed13 validation')
        cutoffs=PROTOCOL['seed13_validation_cutoffs_sec']; frozen=None
    else:
        if seed!=17 or a.freeze is None: raise ValueError('Seed17 requires parameter/code freeze')
        frozen=check_freeze(a.freeze,a.parameters)
        if manifest['extractor_sha256']!=sha(HERE/'extract_observations.py'):
            raise ValueError('Test observations extracted with different code')
        cutoffs=PROTOCOL['test_cutoffs_sec']
    data=ObservationData(a.data)
    model=load_base_model(data.geometry)
    parameter_document=json.loads(a.parameters.read_text(encoding='utf-8'))
    if parameter_document.get('training_seed')!=13: raise ValueError('Expected parameters fitted on seed13')
    parameters=parameter_document['parameters']
    if 'by_direction' not in parameters: raise ValueError('Missing direction parameters')
    a.out.mkdir()
    scores=[];cells=[];flows=[];boundaries=[];persistence=[];failures=[];persistence_failures=[]
    started=time.monotonic()
    for cutoff in cutoffs:
        for road in ('FW_E','FW_W'):
            try:
                persistence.append(persistence_score(data,cutoff,road))
            except Exception as exc:
                persistence_failures.append({'cutoff_s':cutoff,'road':road,'error_type':type(exc).__name__,'error':str(exc)})
        for mode in PROTOCOL['evaluation_modes']:
            try:
                inputs=build_window(data,cutoff,mode)
            except Exception as exc:
                failures.extend({'cutoff_s':cutoff,'mode':mode,'version':version,'stage':'boundary_preparation',
                                 'error_type':type(exc).__name__,'error':str(exc)} for version in ('baseline','calibrated'))
                continue
            boundaries.append(inputs['meta'])
            for version,override in [('baseline',None),('calibrated',parameters)]:
                label={'cutoff_s':cutoff,'mode':mode,'version':version}
                try:
                    pred=model.rollout(inputs['initial_cells'],inputs['boundary_steps'],overrides=override,
                                       initial_origin_queue=inputs['initial_origin_queue'])
                    window_scores=[{**label,**score_rollout(data,cutoff,pred,road)} for road in ('FW_E','FW_W')]
                    scores.extend(window_scores)
                    cells.extend({**label,**r} for r in pred['cells'])
                    flows.extend({**label,**r} for r in pred['flows'])
                except Exception as exc:
                    failures.append({**label,'error_type':type(exc).__name__,'error':str(exc)})
            print(json.dumps({'seed':seed,'evaluated_cutoff_s':cutoff,'mode':mode}),flush=True)
    groups=[]
    for road in ('FW_E','FW_W'):
        for mode in PROTOCOL['evaluation_modes']:
            for version in ('baseline','calibrated'):
                rows=[r for r in scores if r['road']==road and r['mode']==mode and r['version']==version]
                failed=[r for r in failures if r['mode']==mode and r['version']==version]
                group={'road':road,'mode':mode,'version':version,'expected_windows':len(cutoffs),
                    'scored_windows':len(rows),'execution_failure_windows':len(failed),
                    'invalid_windows':sum(r['invalid'] for r in rows),
                    **{f:pooled(rows,f) for f in ('density','speed','cell_n','flow_vph','off_flow_vph')},
                    'horizons':{str(h):{f:pooled([r['horizons'][str(h)] for r in rows],f) for f in ('density','speed','cell_n')}
                                 for h in (150,300,450)},
                    'freeway_ttt_observed_sum_veh_h':sum(r['freeway_ttt_observed_veh_h'] for r in rows),
                    'freeway_ttt_predicted_sum_veh_h':sum(r['freeway_ttt_predicted_veh_h'] for r in rows),
                    'onset_misses':sum(e['status']=='miss' for r in rows for e in r['onset_events']),
                    'onset_false_alarms':sum(e['status']=='false_alarm' for r in rows for e in r['onset_events']),
                    'onset_timing_error_s':stats_onset(rows)}
                groups.append(group)
    persistence_groups=[{'road':road,'expected_windows':len(cutoffs),
                         'scored_windows':sum(r['road']==road for r in persistence),
                         'failed_windows':sum(r['road']==road for r in persistence_failures),
                         **{f:pooled([r for r in persistence if r['road']==road],f)
                           for f in ('density','speed')}} for road in ('FW_E','FW_W')]
    result={'seed':seed,'horizon_s':450,'cutoffs_s':cutoffs,'parameters_sha256':sha(a.parameters),
        'observation_manifest_sha256':sha(a.data/'manifest.json'),'freeze_sha256':sha(a.freeze) if frozen else None,
        'protocol_sha256':sha(HERE/'PROTOCOL.json'),'elapsed_sec':time.monotonic()-started,
        'groups':groups,'persistence':persistence_groups,'persistence_failures':persistence_failures,'failures':failures,'scores':scores,
        'boundary_metadata':boundaries,'model_provenance':model.provenance,
        'interpretation':'All predeclared windows retained. Pooled errors include finite invalid trajectories; any failed/invalid window prevents blanket physical-validity claim. Conditional diagnosis uses measured future boundary support. History forecast has no future realized boundary/state inputs. Freeway component only, not total Omega or controller benefit.'}
    (a.out/'evaluation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    table(a.out/'predicted_cells_30s.csv',cells);table(a.out/'predicted_flows_30s.csv',flows)
    if frozen: check_freeze(a.freeze,a.parameters)
    print(json.dumps({'seed':seed,'complete':str(a.out),'failures':len(failures),
        'summary':[{k:g[k] for k in ('road','mode','version','invalid_windows','speed','density','flow_vph')} for g in groups]},ensure_ascii=False))


def stats_onset(rows):
    from scoring import stats
    return stats([e['timing_error_s'] for r in rows for e in r['onset_events'] if e['timing_error_s'] is not None])


if __name__=='__main__': main()
