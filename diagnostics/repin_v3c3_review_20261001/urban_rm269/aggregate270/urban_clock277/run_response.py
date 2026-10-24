"""One named source-pinned scalar/AD450s check. No native or optimizer."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import hashlib,json,pickle,subprocess,sys,time
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];M=HERE.parent/'multirate271'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value):p.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
def main():
    label,case,mode=sys.argv[1:]
    assert label.isidentifier() and case in ('hold','release','default') and mode in ('scalar','ad')
    receipt=HERE/(label+'_execution.json');assert not receipt.exists()
    assert not any((p/'STOP').exists() for p in (ROOT,HERE,HERE.parent,HERE.parent.parent))
    source=M/('macro_release_ad_v2_request.pickle' if case=='release' else 'macro_hold_ad_v3_request.pickle')
    request=pickle.loads(source.read_bytes());cfg=request['owned'][0].cfg;state=request['owned'][1]
    if case!='default':
        from evaluation.controllers.multirate_coupling import configure
        configure(cfg,{'urban':{'multirate_exchange_sec':10}},state)
    pins={str(p):sha(p) for p in (ROOT/'evaluation/controllers').glob('*.py')}
    for path,old in request['bootstrap']['runtime_sources'].items():
        if path not in pins:assert sha(Path(path))==old,path
    request['bootstrap']['runtime_sources'].update(pins)
    from evaluation.controllers.sdmpc_tangent_surrogate import token
    request['surrogate_evaluation']=mode
    request['surrogate_context_sha256']=token((request['owned'],request['runtime'],request['bootstrap'],request['horizon']))
    src=HERE/(label+'_request.pickle');dst=HERE/(label+'_result.pickle');src.write_bytes(pickle.dumps(request,protocol=5))
    record=dict(status='running',case=case,mode=mode,pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),
        source_pins=pins,input_sha256=sha(source),full_rollouts=1,full_sdmpc_selections=0,native_runs=0)
    save(receipt,record);t0=time.perf_counter()
    with (HERE/(label+'_stdout.log')).open('w') as out,(HERE/(label+'_stderr.log')).open('w') as err:
        child=subprocess.Popen([sys.executable,'-B',str(ROOT/'evaluation/controllers/sdmpc_tangent_worker.py'),str(src),str(dst),sha(src),'reverse-v1'],
            cwd=ROOT,stdout=out,stderr=err,creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS|subprocess.CREATE_NO_WINDOW)
        record['child_pid']=child.pid;save(receipt,record);code=child.wait()
    record.update(exit_code=code,wall_sec=time.perf_counter()-t0,status='failed_preserved' if code else 'complete_unreviewed',
        source_pins_unchanged=all(sha(Path(p))==h for p,h in pins.items()))
    save(receipt,record)
    print(json.dumps({k:v for k,v in record.items() if k!='source_pins'}))
    if code:
        failure=pickle.loads(dst.read_bytes()) if dst.exists() else {}
        print(failure.get('error',(HERE/(label+'_stderr.log')).read_text())[-6500:])
    return code
if __name__=='__main__':raise SystemExit(main())
