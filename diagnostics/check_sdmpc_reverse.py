"""Pinned saved-state reverse-vs-forward Jacobian comparison; no VISSIM."""
from pathlib import Path
import hashlib
import json
import pickle
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def main():
    from evaluation.controllers import sdmpc_tangent
    source,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=False)
    request=pickle.loads((source/'request.pickle').read_bytes())
    request.pop('diagnostic_checkpoint',None)
    options=request['owned'][0].cfg.network.sdmpc_options
    options.update(tangent_backend='reverse-v1', derivative_workers=8, tangent_shared_primal=True)
    if '--immutable-audit' in sys.argv:
        options['immutable_audit']=True
    if '--primal-audit' in sys.argv:
        options['primal_audit']=True
    if '--concurrent-primal' in sys.argv:
        options['tangent_concurrent_primal']=True
    if '--fast-primitives' in sys.argv:
        options['fast_primitives']=True
    if '--response-np-cache' in sys.argv:
        options['response_np_cache']=True
    if '--prediction-cache' in sys.argv:
        options['prediction_cache']=True
    if '--compact-audit' in sys.argv:
        options['compact_audit']=True
    if '--ramp-stock-cache' in sys.argv:
        options['ramp_stock_cache']=True
    if '--initial-derivative-overlap' in sys.argv:
        options['initial_derivative_overlap']=True
    if '--trial-derivative-overlap' in sys.argv:
        options['trial_derivative_overlap']=True
    if '--spatial-receiving' in sys.argv:
        options['spatial_receiving']=True
    if '--flow-update-cache' in sys.argv:
        options['flow_update_cache']=True
    if '--array-transport' in sys.argv:
        options['array_transport']=True
    if '--persistent-urban-fifo' in sys.argv:
        options['persistent_urban_fifo']=True
    if '--array-urban-pipeline' in sys.argv:
        options['array_urban_pipeline']=True
    if '--surrogate-reuse' in sys.argv:
        options['surrogate_reuse']=True
    if '--initial-shared-prediction' in sys.argv:
        options['initial_shared_prediction']=True
    if '--prediction-hotpath' in sys.argv:
        options['prediction_hotpath']=True
    for name in request['bootstrap']['runtime_sources']:
        request['bootstrap']['runtime_sources'][name]=hashlib.sha256(Path(name).read_bytes()).hexdigest()
    (out/'request.pickle').write_bytes(pickle.dumps(request,protocol=5))
    try: result=sdmpc_tangent.evaluate(request)
    except Exception:
        import traceback
        (out/'error.txt').write_text(traceback.format_exc()); raise
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    baseline=json.loads((source/'result.json').read_text())
    checks={key:float(np.max(abs(np.asarray(result[key])-np.asarray(baseline[key]))))
            for key in ('costs','resources','cost_jacobian','resource_jacobian')}
    report=dict(baseline=str(source), checks=checks, pass_all=max(checks.values())<=1e-7,
        wall_sec=result['wall_sec_including_spawn'],
        times={k:result[k] for k in ('scalar_sec','tangent_sec','state_check_sec','reverse_sec')},
        reverse_sweeps=result['reverse_sweeps'], native_applied=False,
        scope='One complete Jacobian, not an entire SDMPC solve')
    (out/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    return 0 if report['pass_all'] else 1


if __name__=='__main__': raise SystemExit(main())
