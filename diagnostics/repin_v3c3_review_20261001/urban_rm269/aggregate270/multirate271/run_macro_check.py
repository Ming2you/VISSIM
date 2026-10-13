"""One named, source-pinned offline response. Never starts/retries VISSIM."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import ctypes,hashlib,json,pickle,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];BASE=HERE.parent/'route_interval'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')


def main():
    from evaluation.controllers.sdmpc_tangent_surrogate import token
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    label,case,mode=sys.argv[1:]
    assert case in ('hold5','release5','default1') and mode in ('scalar','ad')
    assert label.isidentifier()
    receipt_path=HERE/(label+'_execution.json');assert not receipt_path.exists(),'No duplicate or automatic retry'
    assert not any((p/'STOP').exists() for p in (ROOT,HERE,HERE.parent,HERE.parent.parent))
    source=BASE/('new_release.pickle' if case=='release5' else 'new_hold.pickle')
    request=pickle.loads(source.read_bytes())
    allowed={'physical_urban_transport.py','physical_ramp_boundary.py','known_wout_causal_response.py',
        'lane_ramp_runtime.py','lane_offramp_runtime.py','lane_coupling.py',
        'lane_freeway_runtime.py','area_freeway_accounting.py','runtime_setup.py'}
    changed=[]
    for path,old in list(request['bootstrap']['runtime_sources'].items()):
        current=sha(Path(path))
        if current!=old:
            assert Path(path).name in allowed,path
            changed.append(dict(path=path,old=old,new=current));request['bootstrap']['runtime_sources'][path]=current
    for name in ('multirate_ramp_boundary.py','multirate_freeway.py'):
        path=ROOT/'evaluation/controllers'/name;request['bootstrap']['runtime_sources'][str(path)]=sha(path)
    follower,state,reference,forecast=request['owned']
    if case!='default1':
        assert not state.lane_freeway_runtime.lanes
        assert follower.cfg.simulation.T_u_sec==1
        from evaluation.controllers.multirate_freeway import configure
        configure(follower.cfg,{'freeway':{'multirate_exchange_sec':5}},state)
    request['surrogate_context_sha256']=token((request['owned'],request['runtime'],request['bootstrap'],request['horizon']))
    request['surrogate_evaluation']=mode
    payload=pickle.dumps(request,protocol=5);src=HERE/(label+'_request.pickle');dst=HERE/(label+'_result.pickle')
    src.write_bytes(payload)
    receipt=dict(status='running',case=case,mode=mode,pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),
        scope='Current saved2400 state,450s causal prediction; freeway5s with shared numerical substeps, urban1s. No native, full urban10s or controller selection.',
        input_sha256=sha(source),request_sha256=sha(src),changed_sources=changed,
        source_pins={str(p):sha(p) for p in (ROOT/'evaluation/controllers').glob('*.py')})
    save(receipt_path,receipt);started=time.perf_counter()
    cmd=[sys.executable,'-B',str(ROOT/'evaluation/controllers/sdmpc_tangent_worker.py'),str(src),str(dst),sha(src),'reverse-v1']
    with (HERE/(label+'_stdout.log')).open('w') as out,(HERE/(label+'_stderr.log')).open('w') as err:
        child=subprocess.Popen(cmd,cwd=ROOT,stdout=out,stderr=err)
        receipt.update(child_pid=child.pid,child_started_utc=datetime.now(timezone.utc).isoformat());save(receipt_path,receipt)
        code=child.wait()
    receipt.update(exit_code=code,wall_sec=time.perf_counter()-started,status='failed_no_retry' if code else 'complete_unreviewed')
    receipt['source_pins_unchanged']=all(sha(Path(p))==h for p,h in receipt['source_pins'].items())
    save(receipt_path,receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('source_pins','changed_sources')}))
    return code


if __name__=='__main__':raise SystemExit(main())
