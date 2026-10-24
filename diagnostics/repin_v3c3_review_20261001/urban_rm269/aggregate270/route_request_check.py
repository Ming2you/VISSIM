"""Two scalar responses and one AD check for held10s urban route requests."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import copy,ctypes,hashlib,json,pickle,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OUT=HERE/'route_requests10';BASE=HERE/'route_interval'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def prepare():
    from evaluation.controllers.sdmpc_tangent_surrogate import token
    assert not OUT.exists(),'Preserve every prior attempt'
    assert read(HERE/'unseen3300_routes_execution.json')['status']=='complete_reviewed'
    assert read(BASE/'ad_execution.json')['status']=='complete_reviewed'
    OUT.mkdir()
    changed=[]
    for name in ('new_hold','new_release'):
        request=pickle.loads((BASE/(name+'.pickle')).read_bytes())
        for path,old in list(request['bootstrap']['runtime_sources'].items()):
            now=sha(path)
            if now!=old:
                assert Path(path).name=='aggregate_route_corridors.py',path
                changed.append(dict(name=name,path=path,before=old,after=now))
                request['bootstrap']['runtime_sources'][path]=now
        obj=request['owned'][1].route_choice_corridor_state['aggregate_routes']
        assert obj.dt==10 and obj.updates==0
        obj.request_dt=10;obj.request_plans={};obj.request_updates=0
        request['surrogate_context_sha256']=token((request['owned'],request['runtime'],request['bootstrap'],request['horizon']))
        (OUT/(name+'.pickle')).write_bytes(pickle.dumps(request,protocol=5))
    cfg=read(HERE/'config_dt10_routes.json');cfg['urban']['route_corridor_request_step_sec']=10
    save(HERE/'config_dt10_requests.json',cfg)
    pins={str(p):sha(p) for p in (ROOT/'evaluation/controllers').glob('*.py')}
    for p in (Path(__file__),ROOT/'tests/test_aggregate_route_corridors.py',HERE/'config_dt10_requests.json'):pins[str(p)]=sha(p)
    save(OUT/'plan.json',dict(status='prepared',source_pins=pins,changed_sources=changed,
        tests_passed=18,scalar_max=2,ad_max=1,full_selections=0,native_runs=0,
        approximation='Hold per-second route requests for10s. Source stock, head green/shared service, downstream space and commits still1s; unused service is lost, never banked.',
        preserve='Same initial2400 state, controls, caps,450s horizon,Omega701,terminalOFF,network,demand. No gain coefficient.',
        not_implemented='Whole urban10s or freeway5s integration.'))


def run():
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    plan=read(OUT/'plan.json')
    for p,h in plan['source_pins'].items():assert sha(p)==h,p
    path=OUT/'execution.json';assert not path.exists(),'No duplicate/retry'
    receipt=dict(status='running',pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),results=[])
    save(path,receipt)
    for name,mode in (('new_hold','scalar'),('new_release','scalar'),('new_hold','ad')):
        assert not any((p/'STOP').exists() for p in (ROOT,HERE.parent,HERE,OUT))
        request=pickle.loads((OUT/(name+'.pickle')).read_bytes());request['surrogate_evaluation']=mode
        payload=pickle.dumps(request,protocol=5);source=OUT/(name+'.'+mode+'.request.pickle');target=OUT/(name+'.'+mode+'.result.pickle')
        source.write_bytes(payload);started=time.perf_counter()
        command=[sys.executable,'-B',str(ROOT/'evaluation/controllers/sdmpc_tangent_worker.py'),str(source),str(target),hashlib.sha256(payload).hexdigest(),'reverse-v1']
        with (OUT/(name+'.'+mode+'.stdout.log')).open('w') as stdout,(OUT/(name+'.'+mode+'.stderr.log')).open('w') as stderr:
            child=subprocess.Popen(command,cwd=ROOT,stdout=stdout,stderr=stderr)
            receipt.update(stage=name+':'+mode,child_pid=child.pid,child_started_utc=datetime.now(timezone.utc).isoformat());save(path,receipt)
            code=child.wait()
        result=pickle.loads(target.read_bytes()) if target.exists() else {}
        receipt['results'].append(dict(name=name,mode=mode,exit_code=code,wall_sec=time.perf_counter()-started,error=result.get('error')))
        valid=not code and result and 'error' not in result
        if valid:
            response=result['surrogate_prediction']
            valid=(response['conditional_model_feasibility_witness'] and response['model_constraint_coverage']['complete']
                   and response['resource_summary']['max_exceedance_veh']<1e-7)
        if not valid:
            receipt['status']='failed_no_retry';save(path,receipt);return 1
        save(path,receipt)
    for p,h in plan['source_pins'].items():assert sha(p)==h,p
    receipt['status']='complete_pending_review';save(path,receipt);return 0


if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='run':raise SystemExit(run())
    else:raise ValueError('prepare/run only')
