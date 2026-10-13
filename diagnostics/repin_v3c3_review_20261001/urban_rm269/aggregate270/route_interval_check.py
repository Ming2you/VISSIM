"""Bounded coarse route-state experiment, with the same saved control state."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import copy,ctypes,hashlib,json,pickle,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=HERE/'route_interval'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,x):Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')


def prepare():
    from evaluation.controllers import aggregate_route_corridors as ar,physical_ramp_branches as ramps,sdmpc_sequence as seq
    from evaluation.controllers.sdmpc_tangent_surrogate import token
    base=pickle.loads((HERE/'profile_scalar/request.pickle').read_bytes())
    assert read(HERE/'service_saturation/execution.json')['status']=='complete_reviewed_not_adopted'
    OUT.mkdir(exist_ok=False)
    allowed={'sdmpc.py','sdmpc_stock_geometry.py','sdmpc_tangent_worker.py','sdmpc_tangent_summary.py',
             'sdmpc_tangent_surrogate.py','route_choice_corridor.py','runtime_setup.py'}
    changed=[]
    for p,old in list(base['bootstrap']['runtime_sources'].items()):
        new=sha(p)
        if new!=old:
            assert Path(p).name in allowed,p
            changed.append(dict(path=p,old=old,new=new));base['bootstrap']['runtime_sources'][p]=new
    p=ROOT/'evaluation/controllers/aggregate_route_corridors.py'
    base['bootstrap']['runtime_sources'][str(p)]=sha(p)
    original=base['action'];cfg=base['owned'][0].cfg
    blocks=seq.actions(original,3);previous=seq.first_action(original);released=[]
    assert [c.diagnostics['rw_meter_green_RM_C10681'] for c in blocks]==[2.,2.,2.]
    for block,green in zip(blocks,(4,6,8)):
        greens={r:block.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps};greens['RM_C10681']=green
        result=ramps.candidate_from_greens(block,previous,cfg,greens);released.append(result);previous=result
    release=seq.pack(released)
    # Only physical meter fields for10681 and corresponding packed future controls change.
    for old,new in zip(blocks,released):
        assert old.green_times==new.green_times and old.vsl==new.vsl and old.offsets==new.offsets
        assert old.N_P_star==new.N_P_star and old.N_UF_star==new.N_UF_star
    metadata={}
    for name,coarse,action in [('old_release',False,release),('new_hold',True,original),('new_release',True,release)]:
        request=copy.deepcopy(base);request['action']=copy.deepcopy(action)
        if coarse:
            metadata[name]=ar.configure(request['owned'][0].cfg,{'urban':{'route_corridor_aggregate_step_sec':10}},request['owned'][1])
        request['surrogate_context_sha256']=token((request['owned'],request['runtime'],request['bootstrap'],request['horizon']))
        (OUT/(name+'.pickle')).write_bytes(pickle.dumps(request,protocol=5))
    cfgfile=read(HERE/'config_dt10.json');cfgfile.setdefault('urban',{})['route_corridor_aggregate_step_sec']=10
    save(HERE/'config_dt10_routes.json',cfgfile)
    pins={str(p):sha(p) for p in (ROOT/'evaluation/controllers').glob('*.py')}
    for p in (Path(__file__),ROOT/'tests/test_aggregate_route_corridors.py',HERE/'config_dt10_routes.json'):pins[str(p)]=sha(p)
    save(OUT/'plan.json',dict(status='prepared',source_pins=pins,changed_sources=changed,projection=metadata,
        scalar_max=3,ad_max=1,full_selections=0,native_runs=0,
        baseline_hold='ad2400_lane_offer/scalar.pickle',
        preservation='Same state/network/demand/450s/Omega701/terminalOFF; only RM10681 differs between paired actions.',
        change='Four ordinary urban route corridors use fixed route/stage/source/head-tag stocks and10s arrival/choice bins; receiving/service1s. Other urban mechanisms/mainline remain1s.',
        approximation='Ready classes share service proportionally instead of cohort-order FIFO; later stage speed uses initial storage-weighted mean. No fitted gain/bonus.',
        tests='15passed',status_note='Not full urban10s or mainline5s, no native adoption.'))


def run(mode):
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    plan=read(OUT/'plan.json')
    for p,h in plan['source_pins'].items():assert sha(p)==h,p
    receipt_path=OUT/(mode+'_execution.json');assert not receipt_path.exists(),'No duplicate/retry'
    receipt=dict(status='running',pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),results=[])
    save(receipt_path,receipt)
    names=['old_release','new_hold','new_release'] if mode=='scalar' else ['new_hold']
    if mode=='ad':assert read(OUT/'scalar_review.json')['physical_gates_pass']
    for name in names:
        assert not any((p/'STOP').exists() for p in (ROOT,HERE.parent,HERE,OUT))
        request=pickle.loads((OUT/(name+'.pickle')).read_bytes());request['surrogate_evaluation']=mode
        payload=pickle.dumps(request,protocol=5);source=OUT/(name+'.'+mode+'.request.pickle');target=OUT/(name+'.'+mode+'.result.pickle')
        source.write_bytes(payload)
        command=[sys.executable,'-B',str(ROOT/'evaluation/controllers/sdmpc_tangent_worker.py'),str(source),str(target),hashlib.sha256(payload).hexdigest(),'reverse-v1']
        started=time.perf_counter()
        with (OUT/(name+'.'+mode+'.stdout.log')).open('w') as stdout,(OUT/(name+'.'+mode+'.stderr.log')).open('w') as stderr:
            child=subprocess.Popen(command,cwd=ROOT,stdout=stdout,stderr=stderr)
            receipt.update(stage=name,child_pid=child.pid,child_started_utc=datetime.now(timezone.utc).isoformat());save(receipt_path,receipt)
            code=child.wait()
        result=pickle.loads(target.read_bytes()) if target.exists() else {}
        receipt['results'].append(dict(name=name,exit_code=code,wall_sec=time.perf_counter()-started,error=result.get('error')))
        if code or not result or 'error' in result:
            receipt['status']='failed_no_retry';save(receipt_path,receipt);return 1
        save(receipt_path,receipt)
    for p,h in plan['source_pins'].items():assert sha(p)==h,p
    receipt['status']='complete_pending_review';save(receipt_path,receipt);return 0


def review_scalar():
    assert read(OUT/'scalar_execution.json')['status']=='complete_pending_review'
    rows={};responses={}
    for name in ('old_hold','old_release','new_hold','new_release'):
        path=HERE/'ad2400_lane_offer/scalar.pickle' if name=='old_hold' else OUT/(name+'.scalar.result.pickle')
        data=pickle.loads(path.read_bytes());r=data['surrogate_prediction'];responses[name]=r
        cov=r['model_constraint_coverage'];assert cov['complete'] and cov['schedule_complete'] and not cov['missing_constraints']
        assert r['resource_summary']['max_exceedance_veh']<1e-7
        cost=r['sdmpc_omega_partition']['costs'];assert abs(sum(cost.values())-r['objective_veh_h'])<1e-7
        rows[name]=dict(omega_veh_h=r['objective_veh_h'],owner_costs=cost,merge_rate_veh_h=r['quantities']['predicted_ramp_merge']['rate_veh_h_by_ramp'],
            constraint_visits=cov['completed_visits'],allocation_checks=r['resource_summary']['count'])
    delta={}
    for mode in ('old','new'):
        h,r=rows[mode+'_hold'],rows[mode+'_release']
        delta[mode]=dict(omega_veh_h=r['omega_veh_h']-h['omega_veh_h'],
            owner_costs={k:r['owner_costs'][k]-h['owner_costs'][k] for k in h['owner_costs']},
            extra10681_merge_veh=(r['merge_rate_veh_h']['RM_C10681']-h['merge_rate_veh_h']['RM_C10681'])*450/3600)
    report=dict(status='complete_physical_gates_only',physical_gates_pass=True,rows=rows,deltas=delta,
        execution=read(OUT/'scalar_execution.json'),native_gain_qualified=False,whole_wall_qualified=False)
    save(OUT/'scalar_review.json',report)
    print(json.dumps(dict(deltas=delta,timing=report['execution']['results']),ensure_ascii=False))


if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1] in ('scalar','ad'):raise SystemExit(run(sys.argv[1]))
    elif sys.argv[1]=='review':review_scalar()
    else:raise ValueError('prepare/scalar/review/ad required')
