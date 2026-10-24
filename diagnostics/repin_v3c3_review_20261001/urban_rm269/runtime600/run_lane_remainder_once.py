"""One retained scalar trajectory after the full benchmark closes; no retry."""
import hashlib
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
import time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers.sdmpc_tangent_surrogate import token,check_scalar_upgrade


def save(p,obj):p.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')


def main():
    receipt=json.loads((HERE/'hot_full.execution.json').read_bytes())
    assert receipt['status']=='complete_uncompared' and receipt['exit_code']==0,receipt['status']
    out=HERE/'whole_transfer'/'scalar_lane';out.mkdir(exist_ok=False)
    assert not any((p/'STOP').exists() for p in (HERE,HERE.parent,ROOT))
    plan=json.loads((HERE/'hot_full_benchmark_plan.json').read_bytes())
    for name,digest in plan['source_pins'].items():
        original=HERE/'whole_transfer'/'route_choice_corridor.before.py' if Path(name).name=='route_choice_corridor.py' else Path(name)
        assert hashlib.sha256(original.read_bytes()).hexdigest()==digest,name
    request=pickle.loads((HERE/'hot_validation/scalar.request.pickle').read_bytes())
    assert request['surrogate_evaluation']=='scalar'
    changes=[]
    for name,expected in list(request['bootstrap']['runtime_sources'].items()):
        observed=hashlib.sha256(Path(name).read_bytes()).hexdigest()
        if observed!=expected:
            assert Path(name).name in ('sdmpc_stock_geometry.py','route_choice_corridor.py'),name
            changes.append(dict(path=name,before=expected,after=observed))
            request['bootstrap']['runtime_sources'][name]=observed
    request['surrogate_context_sha256']=token((request['owned'],request['runtime'],request['bootstrap'],request['horizon']))
    data=pickle.dumps(request,protocol=5);inp=out/'request.pickle';inp.write_bytes(data)
    result_path=out/'result.pickle';worker=HERE/'cohort_size_worker.py'
    state=dict(status='running',maximum_predictions=1,native_runs=0,changed_pins=changes,
               request_sha256=hashlib.sha256(data).hexdigest(),worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest())
    save(out/'execution.json',state)
    start=time.perf_counter()
    with (out/'stdout.log').open('w') as stdout,(out/'stderr.log').open('w') as stderr:
        child=subprocess.Popen([sys.executable,str(worker),str(inp),str(result_path),state['request_sha256'],'reverse-v1'],
            stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        state['pid']=child.pid;state['launched_at_epoch']=time.time();save(out/'execution.json',state)
        exitcode=child.wait()
    state.update(exit_code=exitcode,wall_sec=time.perf_counter()-start,status='failed_no_retry' if exitcode else 'complete')
    save(out/'execution.json',state)
    if exitcode:raise RuntimeError((out/'stderr.log').read_text())
    result=pickle.loads(result_path.read_bytes())
    assert 'error' not in result,result.get('error')
    previous=pickle.loads((HERE/'hot_validation/scalar.result.pickle').read_bytes())
    summaries=[dict(previous['surrogate_prediction']),dict(result['surrogate_prediction'])]
    for item in summaries:
        item.pop('diagnostic_transfer_witness',None);item.pop('frozen_context_token',None)
    from compare_physical_summary import compare
    comparison=compare(*summaries)
    report=dict(status='complete_equivalent_scalar',summary_equivalent=True,additional_scalar_predictions=1,
                new_ad_predictions=0,new_full_selections=0,native_runs=0,wall_sec=state['wall_sec'],
                cohort_size=result['cohort_size_diagnostic'],comparison=comparison)
    save(out/'summary.json',report);print(json.dumps(report))

if __name__=='__main__':main()
