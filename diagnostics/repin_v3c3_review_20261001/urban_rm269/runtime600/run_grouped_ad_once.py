"""One AD prediction for the qualified grouped-arrival scalar; no optimizer/run."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import hashlib
import json
from pathlib import Path
import pickle
import subprocess
import sys
import time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers.sdmpc_tangent_surrogate import token


def save(p,obj):p.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')


def main():
    base=HERE/'whole_transfer/scalar_grouped'
    assert json.loads((base/'summary.json').read_bytes())['status']=='complete_equivalent_physical_scalar'
    assert not any((p/'STOP').exists() for p in (HERE,HERE.parent,ROOT))
    out=HERE/'whole_transfer/ad_grouped_v2';out.mkdir(exist_ok=False)
    scalar=pickle.loads((base/'request.pickle').read_bytes())
    # Use the exact scalar input rather than an independently retained AD
    # template. Pickle round trips can alter memoization/digests without a
    # traffic-state change; the shared input's receipt is the pairing proof.
    request=scalar
    state_token=token((request['owned'],request['runtime'],request['bootstrap'],request['horizon']))
    assert request['surrogate_evaluation']=='scalar' and len(request['axes'])==213
    for name,expected in scalar['bootstrap']['runtime_sources'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected,name
    request['surrogate_evaluation']='ad'
    assert token((request['owned'],request['runtime'],request['bootstrap'],request['horizon']))==state_token
    data=pickle.dumps(request,protocol=5);inp=out/'request.pickle';inp.write_bytes(data)
    result_path=out/'result.pickle';worker=ROOT/'evaluation/controllers/sdmpc_tangent_worker.py'
    state=dict(status='running',maximum_predictions=1,maximum_ad_predictions=1,full_selections=0,native_runs=0,
               request_sha256=hashlib.sha256(data).hexdigest(),source_pins=dict(request['bootstrap']['runtime_sources']),
               shared_scalar_input_sha256=hashlib.sha256((base/'request.pickle').read_bytes()).hexdigest(),
               input_changes=['surrogate_evaluation: scalar -> ad'])
    save(out/'execution.json',state);start=time.perf_counter()
    with (out/'stdout.log').open('w') as stdout,(out/'stderr.log').open('w') as stderr:
        child=subprocess.Popen([sys.executable,str(worker),str(inp),str(result_path),state['request_sha256'],'reverse-v1'],
            stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        state['pid']=child.pid;state['launched_at_epoch']=time.time();save(out/'execution.json',state)
        code=child.wait()
    state.update(exit_code=code,wall_sec=time.perf_counter()-start,status='failed_no_retry' if code else 'complete_pending_comparison')
    save(out/'execution.json',state)
    if code:
        result=pickle.loads(result_path.read_bytes())
        raise RuntimeError(result.get('error',(out/'stderr.log').read_text()))
    print(json.dumps({k:state[k] for k in ('status','wall_sec','exit_code','pid')}))

if __name__=='__main__':main()
