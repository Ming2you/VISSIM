"""Three independent block sensitivities, checked outside the solver by FD."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import copy
import hashlib
import json
import pickle
import subprocess
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def main():
    from evaluation.controllers import sdmpc_sequence as seq
    source,out=Path(sys.argv[1]),Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=False)
    with (source/'request.pickle').open('rb') as f: request=pickle.load(f)
    result=json.loads((source/'result.json').read_text())
    if 'error' in result:raise ValueError('Unqualified derivative input')
    matrix=np.vstack([result['cost_jacobian'],result['resource_jacobian']])
    baseline=np.r_[result['costs'],result['resources']]
    h=1e-6;tasks=[]
    for block in range(3):
        indices=[j for j,a in enumerate(request['axes']) if a['block']==block and a['kind']=='green' and a['owner']=='SC1']
        j=max(indices,key=lambda j:np.linalg.norm(matrix[:,j]))
        r=copy.deepcopy(request);a=r['axes'][j];controls=seq.actions(r['action'],3)
        for phase,factor in r['green_vectors'][j].items():
            controls[block].green_times[a['owner']+'_'+phase]+=h*a['scale']*factor
        r['action']=seq.pack(controls);r['scalar_only']=True;r.pop('diagnostic_checkpoint',None)
        inp=out/f'request_{block}.pickle';res=out/f'result_{block}.pickle'
        data=pickle.dumps(r,protocol=5);inp.write_bytes(data)
        tasks.append((block,j,inp,res,hashlib.sha256(data).hexdigest()))
    def run(task):
        block,j,inp,res,digest=task
        process=subprocess.run([sys.executable,'-B',str(ROOT/'evaluation/controllers/sdmpc_tangent_worker.py'),
            str(inp.resolve()),str(res.resolve()),digest],capture_output=True,text=True)
        receipt=pickle.loads(res.read_bytes())
        if process.returncode:raise RuntimeError(receipt.get('error',process.stderr))
        got=(np.r_[receipt['costs'],receipt['resources']]-baseline)/h
        want=matrix[:,j]
        relative=float(np.linalg.norm(got-want)/max(1.,np.linalg.norm(got)))
        return dict(block=block,axis=j,axis_definition=request['axes'][j],normalized_delta=h,
            analytic=want.tolist(),finite_difference=got.tolist(),relative_l2_error=relative,
            max_abs_error=float(np.max(abs(got-want))),scalar_sec=receipt['scalar_sec'],passed=relative<=.01)
    started=time.perf_counter()
    with ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(run,tasks))
    report=dict(purpose='Independent diagnostic only; no FD in the SDMPC solve',workers=3,
        scalar_rollouts=3,wall_sec=time.perf_counter()-started,cases=rows,pass_all=all(r['passed'] for r in rows))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({**report,'cases':[{k:v for k,v in r.items() if k not in ('analytic','finite_difference')} for r in rows]}),flush=True)
    return 0 if report['pass_all'] else 1


if __name__=='__main__':raise SystemExit(main())
