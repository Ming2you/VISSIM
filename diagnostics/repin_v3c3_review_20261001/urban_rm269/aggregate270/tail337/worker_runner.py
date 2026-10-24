"""Canonical one-process request transport, with qualified diagnostic hooks."""
from pathlib import Path
import hashlib, itertools, json, os, pickle, subprocess, sys, threading, time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
counter=itertools.count(max((int(p.name) for p in (HERE/'workers').glob('[0-9]*') if p.is_dir()),default=-1)+1)
lock=threading.Lock()


def evaluate(request):
    with lock:
        directory=HERE/'workers'/f'{next(counter):04d}'
        directory.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter()
    data=pickle.dumps(request,protocol=5)
    digest=hashlib.sha256(data).hexdigest()
    source=directory/'request.pickle';result_path=directory/'result.pickle'
    source.write_bytes(data)
    command=[sys.executable,'-B',str(HERE/'worker.py'),str(source),str(result_path),digest]
    env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    with (directory/'worker.log').open('w',encoding='utf8') as log:
        process=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    if not result_path.is_file(): raise RuntimeError('Missing worker result: '+str(directory))
    result=pickle.loads(result_path.read_bytes())
    assert result['request_sha256']==digest
    if process.returncode or 'error' in result:
        raise RuntimeError('Worker failed: '+str(directory)+'\n'+result.get('error','nonzero exit'))
    result['wall_sec_including_spawn']=time.perf_counter()-started
    receipt=dict(mode=request['surrogate_evaluation'],digest=digest,
                 wall_sec=result['wall_sec_including_spawn'],costs=result['costs'],
                 resources=result['resources'],hooks=result['latest_model_hooks'],
                 command=command,exit_code=process.returncode)
    (directory/'receipt.json').write_text(json.dumps(receipt,indent=2,allow_nan=False),encoding='utf8')
    return result
