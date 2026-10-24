"""One retained scalar and one retained AD response; no optimizer or retry."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import ctypes
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import pickle
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OUT=HERE/'upgrade_replay'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
def save(obj):
    (OUT/'execution.json').write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def main():
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    assert not (OUT/'execution.json').exists(),'Preserve existing attempt'
    assert not (OUT/'STOP').exists()
    request=pickle.loads((OUT/'request.pickle').read_bytes())
    receipt=dict(status='running',parent_pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),
                 full_selections=0,native_runs=0,max_predictions=2,results=[])
    save(receipt)
    for mode in ('scalar','ad'):
        assert not (OUT/'STOP').exists()
        path=OUT/(mode+'.request.pickle');target=OUT/(mode+'.result.pickle')
        assert not path.exists() and not target.exists()
        payload=pickle.dumps(dict(request,surrogate_evaluation=mode),protocol=5)
        path.write_bytes(payload)
        command=[sys.executable,'-B',str(HERE/'upgrade_worker.py'),str(path),str(target),
                 hashlib.sha256(payload).hexdigest(),'reverse-v1']
        start=time.perf_counter()
        with (OUT/(mode+'.stdout.log')).open('w') as stdout,(OUT/(mode+'.stderr.log')).open('w') as stderr:
            child=subprocess.Popen(command,cwd=ROOT,stdout=stdout,stderr=stderr)
            receipt.update(stage=mode,child_pid=child.pid,child_started_utc=datetime.now(timezone.utc).isoformat())
            save(receipt);code=child.wait()
        result=pickle.loads(target.read_bytes()) if target.exists() else {}
        receipt['results'].append(dict(mode=mode,exit_code=code,wall_sec=time.perf_counter()-start,
            completed=code==0 and bool(result) and 'error' not in result,error=result.get('error')))
        if code or not result or 'error' in result:
            receipt['status']='failed_no_retry';save(receipt);return 1
        save(receipt)
    receipt['status']='complete_pending_comparison';save(receipt)
    return 0
if __name__=='__main__':raise SystemExit(main())
