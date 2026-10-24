"""Saved-state parallel Jacobian qualification, no VISSIM."""
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
    request['owned'][0].cfg.network.sdmpc_options['derivative_workers']=int(sys.argv[3]) if len(sys.argv)>3 else 8
    if '--aggregate' in sys.argv:
        request['owned'][0].cfg.network.sdmpc_options['aggregate_predictor']='route-bins-v1'
    if '--shared-primal' in sys.argv:
        request['owned'][0].cfg.network.sdmpc_options['tangent_shared_primal']=True
    if '--indexed-coverage' in sys.argv:
        request['owned'][0].cfg.network.sdmpc_options['indexed_coverage']=True
    for name in request['bootstrap']['runtime_sources']:
        request['bootstrap']['runtime_sources'][name]=hashlib.sha256(Path(name).read_bytes()).hexdigest()
    (out/'request.pickle').write_bytes(pickle.dumps(request,protocol=5))
    try:result=sdmpc_tangent.evaluate(request)
    except Exception:
        import traceback
        (out/'error.txt').write_text(traceback.format_exc());raise
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    baseline=json.loads((source/'result.json').read_text())
    checks={key:float(np.max(abs(np.asarray(result[key])-np.asarray(baseline[key]))))
            for key in ('costs','resources','cost_jacobian','resource_jacobian')}
    report=dict(baseline=str(source),checks=checks,pass_all=max(checks.values())<=1e-7,
        parallel_derivatives=result.get('parallel_derivatives'),wall_sec=result['wall_sec_including_spawn'],
        aggregate_predictor=request['owned'][0].cfg.network.sdmpc_options.get('aggregate_predictor'),native_applied=False)
    (out/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    return 0 if report['pass_all'] else 1


if __name__=='__main__':raise SystemExit(main())
