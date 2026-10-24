"""Compare every continuous state with traffic memoization OFF/ON; no VISSIM."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import pickle
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def main():
    source,out=map(Path,sys.argv[1:3]);out=out.resolve();out.mkdir(parents=True,exist_ok=False)
    request_bytes=(source/'request.pickle').read_bytes()
    option=sys.argv[3] if len(sys.argv)>3 else 'prediction_cache'
    paths=[]
    for enabled in (False,True):
        request=pickle.loads(request_bytes)
        for name in option.split(','):
            request['owned'][0].cfg.network.sdmpc_options[name]=enabled
        name='on' if enabled else 'off'
        request['scalar_output']=str(out/(name+'_states.pickle'))
        request['shared_anchor_sha256']=hashlib.sha256(pickle.dumps(request['owned'],protocol=5)).hexdigest()
        for p in request['bootstrap']['runtime_sources']:
            request['bootstrap']['runtime_sources'][p]=hashlib.sha256(Path(p).read_bytes()).hexdigest()
        path=out/(name+'_request.pickle');path.write_bytes(pickle.dumps(request,protocol=5));paths.append(path)
    started=time.perf_counter()
    def execute(path):
        name=path.name.split('_')[0]
        output=out/(name+'_result.pickle')
        with (out/(name+'.log')).open('w',encoding='utf-8') as log:
            result=subprocess.run([sys.executable,'-B',str(ROOT/'evaluation/controllers/sdmpc_tangent_worker.py'),
                str(path),str(output),hashlib.sha256(path.read_bytes()).hexdigest(),'reverse-v1'],
                cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        receipt=pickle.loads(output.read_bytes())
        if 'error' in receipt:raise RuntimeError(receipt['error'])
        return receipt
    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts=list(pool.map(execute,paths))
    witnesses=[pickle.loads((out/(name+'_states.pickle')).read_bytes()) for name in ('off','on')]
    from evaluation.controllers.sdmpc_tangent_state import state_error
    errors={k:state_error(witnesses[0][k],witnesses[1][k],fast_records=True,compact_records=True)
            for k in ('states','costs','resources')}
    checks=dict(full_states_exact=errors['states']==0.,costs_exact=errors['costs']==0.,
                resources_exact=errors['resources']==0.,
                sources_unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
                    for r in receipts for p,h in r['transformed_source_sha256'].items()))
    report=dict(scope=__doc__,option=option,checks=checks,pass_all=all(checks.values()),errors=errors,
                scalar_sec=[r['scalar_sec'] for r in receipts],wall_sec=time.perf_counter()-started,
                native_applied=False)
    (out/'comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report),flush=True)
    return 0 if report['pass_all'] else 1


if __name__=='__main__':raise SystemExit(main())
