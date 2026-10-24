"""Replay the retained aggregate request once per scalar/AD worker; no optimizer."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import ctypes
from datetime import datetime,timezone
import hashlib,json,pickle,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OUT=HERE/'geometry_cache'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
def save(p,x):
    Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')

def prepare():
    from evaluation.controllers.sdmpc import policy_token
    from evaluation.controllers.sdmpc_tangent_surrogate import token
    assert read(HERE/'profile_process_result.json')['exit_code']==0
    assert read(HERE/'profile_scalar/completion.json')['status']=='complete'
    OUT.mkdir(exist_ok=False)
    request=pickle.loads((HERE/'profile_scalar/request.pickle').read_bytes())
    options=request['owned'][0].cfg.network.sdmpc_options
    assert not options.get('stock_geometry_hotpath')
    identity=policy_token(options)
    options['receiving_geometry_cache']=True
    assert policy_token(options)==identity
    changes=[]
    allowed={'sdmpc.py','sdmpc_stock_geometry.py','sdmpc_tangent_worker.py'}
    for p,old in list(request['bootstrap']['runtime_sources'].items()):
        new=sha(p)
        if old!=new:
            assert Path(p).name in allowed,p
            changes.append(dict(path=p,before=old,after=new))
            request['bootstrap']['runtime_sources'][p]=new
    module=ROOT/'evaluation/controllers/sdmpc_stock_geometry.py'
    request['bootstrap']['runtime_sources'][str(module)]=sha(module)
    request['surrogate_context_sha256']=token((request['owned'],request['runtime'],request['bootstrap'],request['horizon']))
    (OUT/'request.pickle').write_bytes(pickle.dumps(request,protocol=5))
    cfg=read(HERE/'config_dt10.json')
    cfg['adapter']['sdmpc_receiving_geometry_cache']=True
    save(HERE/'config_dt10_geometry.json',cfg)
    pins={str(p):sha(p) for p in (ROOT/'evaluation/controllers').glob('*.py')}
    pins[str(Path(__file__))]=sha(__file__)
    pins[str(HERE/'config_dt10_geometry.json')]=sha(HERE/'config_dt10_geometry.json')
    save(OUT/'plan.json',dict(status='prepared',source_pins=pins,changed_sources=changes,
        scalar_max=1,ad_max=1,full_selections=0,native_runs=0,
        reason='Measured repeated fixed receiving geometry; reuse existing exact cache without stock-sum overrides.',
        clocks='Wout movement10s; native/control/mainline/ramp clocks unchanged',
        baseline='ad2400_lane_offer',only_policy_change='receiving_geometry_cache=true'))

def run():
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    assert not (OUT/'execution.json').exists(),'Preserve prior attempt'
    plan=read(OUT/'plan.json')
    for p,h in plan['source_pins'].items():assert sha(p)==h,p
    request=pickle.loads((OUT/'request.pickle').read_bytes())
    receipt=dict(status='running',pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),results=[])
    save(OUT/'execution.json',receipt)
    for mode in ('scalar','ad'):
        assert not any((p/'STOP').exists() for p in (ROOT,HERE.parent,HERE,OUT))
        source=OUT/(mode+'.request.pickle');target=OUT/(mode+'.result.pickle')
        payload=pickle.dumps(dict(request,surrogate_evaluation=mode),protocol=5)
        source.write_bytes(payload)
        command=[sys.executable,'-B',str(ROOT/'evaluation/controllers/sdmpc_tangent_worker.py'),
                 str(source),str(target),hashlib.sha256(payload).hexdigest(),'reverse-v1']
        started=time.perf_counter()
        with (OUT/(mode+'.stdout.log')).open('w') as stdout,(OUT/(mode+'.stderr.log')).open('w') as stderr:
            child=subprocess.Popen(command,cwd=ROOT,stdout=stdout,stderr=stderr)
            receipt.update(stage=mode,child_pid=child.pid,child_started_utc=datetime.now(timezone.utc).isoformat())
            save(OUT/'execution.json',receipt)
            code=child.wait()
        result=pickle.loads(target.read_bytes()) if target.exists() else {}
        receipt['results'].append(dict(mode=mode,exit_code=code,wall_sec=time.perf_counter()-started,error=result.get('error')))
        if code or not result or 'error' in result:
            receipt['status']='failed_no_retry';save(OUT/'execution.json',receipt);return 1
        save(OUT/'execution.json',receipt)
    for p,h in plan['source_pins'].items():assert sha(p)==h,p
    receipt['status']='complete_pending_review';save(OUT/'execution.json',receipt)
    return 0

def review():
    import numpy as np
    from evaluation.controllers.sdmpc_tangent_surrogate import check_scalar_upgrade
    assert read(OUT/'execution.json')['status']=='complete_pending_review'
    evidence={};pair={}
    for mode in ('scalar','ad'):
        old=pickle.loads((HERE/'ad2400_lane_offer'/(mode+'.pickle')).read_bytes())
        new=pickle.loads((OUT/(mode+'.result.pickle')).read_bytes());pair[mode]=new
        a,b=dict(old['surrogate_prediction']),dict(new['surrogate_prediction'])
        for x in (a,b):x.pop('frozen_context_token')
        check_scalar_upgrade(a,b,1e-7)
        stats=new['stock_geometry_hotpath']
        assert stats['geometry_calls']>0 and stats['repeated_time_hits']>0
        assert stats['stock_calls']==0
        error={}
        matrices=('cost_jacobian','resource_jacobian') if mode=='ad' else ()
        for k in ('costs','resources')+matrices:
            a,b=np.asarray(old[k]),np.asarray(new[k])
            assert a.shape==b.shape and np.isfinite(b).all()
            error[k]=float(np.max(abs(a-b),initial=0))
            assert np.allclose(a,b,atol=1e-7,rtol=1e-10),(mode,k,error[k])
        if mode=='ad':
            a,b=old['central_physical'],new['central_physical']
            assert a['names']==b['names'] and old['ad_axes']==new['ad_axes'] and not new['fallback_reasons']
            for k in ('values','jacobian'):
                x,y=np.asarray(a[k]),np.asarray(b[k]);assert x.shape==y.shape
                error['central_'+k]=float(np.max(abs(x-y),initial=0))
                assert np.allclose(x,y,atol=1e-7,rtol=1e-10)
        evidence[mode]=dict(max_errors=error,stats=stats,
            previous_worker_sec=old.get('wall_sec_including_spawn'),
            core_scalar_sec=new['scalar_sec'],core_tangent_sec=new.get('tangent_sec'))
    check_scalar_upgrade(pair['scalar']['surrogate_prediction'],pair['ad']['surrogate_prediction'],1e-7)
    save(OUT/'comparison.json',dict(status='equivalent',evidence=evidence,
        execution=read(OUT/'execution.json'),full_selections=0,native_runs=0,
        limitations=['One saved state and command; not native gain validation.',
                     'Different-time competing workload; elapsed time is not a matched speedup or600s decision proof.']))
    print(json.dumps(dict(status='equivalent',evidence=evidence),ensure_ascii=False))

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='run':raise SystemExit(run())
    elif sys.argv[1]=='review':review()
    else:raise ValueError('prepare/run/review required')
