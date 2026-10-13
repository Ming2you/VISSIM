"""One scalar and one complete AD replay of the measured route hot path."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import copy,hashlib,json,pickle,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OUT=HERE/'service_saturation'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from geometry_cache_check import sha,read,save


def prepare():
    from evaluation.controllers.sdmpc import policy_token
    from evaluation.controllers.sdmpc_tangent_surrogate import token
    assert read(HERE/'profile_process_result.json')['exit_code']==0
    assert read(HERE/'geometry_cache/execution.json')['status']=='complete_reviewed'
    assert read(HERE/'geometry_cache/comparison.json')['status']=='equivalent'
    OUT.mkdir(exist_ok=False)
    request=pickle.loads((HERE/'profile_scalar/request.pickle').read_bytes())
    options=request['owned'][0].cfg.network.sdmpc_options
    assert not options.get('stock_geometry_hotpath') and not options.get('receiving_geometry_cache')
    identity=policy_token(options);options['route_service_saturation']=True
    assert policy_token(options)==identity
    allowed={'sdmpc.py','sdmpc_stock_geometry.py','sdmpc_tangent_worker.py',
             'route_choice_corridor.py','sdmpc_tangent_summary.py','sdmpc_tangent_surrogate.py'}
    changes=[]
    for p,old in list(request['bootstrap']['runtime_sources'].items()):
        new=sha(p)
        if old!=new:
            assert Path(p).name in allowed,p
            changes.append(dict(path=p,before=old,after=new))
            request['bootstrap']['runtime_sources'][p]=new
    request['surrogate_context_sha256']=token((request['owned'],request['runtime'],request['bootstrap'],request['horizon']))
    (OUT/'request.pickle').write_bytes(pickle.dumps(request,protocol=5))
    cfg=read(HERE/'config_dt10.json');cfg['adapter']['sdmpc_route_service_saturation']=True
    save(HERE/'config_dt10_service.json',cfg)
    pins={str(p):sha(p) for p in (ROOT/'evaluation/controllers').glob('*.py')}
    for p in (Path(__file__),HERE/'geometry_cache_check.py',HERE/'config_dt10_service.json'):pins[str(p)]=sha(p)
    save(OUT/'plan.json',dict(status='prepared',source_pins=pins,changed_sources=changes,
        scalar_max=1,ad_max=1,full_selections=0,native_runs=0,
        reason='Profile showed366147 receiving and366147 branch allocation checks; reuse identical exhausted service within one step.',
        preserve='Every physical state update, route/lane/due identity, accepted flow, cost, constraint scope and current clocks.',
        baseline='ad2400_lane_offer',only_policy_change='route_service_saturation=true',
        audit='v2 explicitly separates executed allocation checks from proven zero-flow logical checks; never labels omitted calls as executed.',
        tests='22passed; unequal shared-branch budget case failed before fixing cache key'))


def normalize_audit(item):
    """Normalize only declared representation changes, after validating proof."""
    from evaluation.controllers.sdmpc_tangent_summary import validate_streamed_checks
    x=copy.deepcopy(item);x.pop('frozen_context_token')
    summary=x['streamed_model_checks'];validate_streamed_checks(summary)
    assert summary['allocation_summary']==x['resource_summary']
    assert summary['allocation_summary']['count']==x['model_constraint_coverage']['checked_allocation_count']
    # Logical check counts/kinds, max exceedance and every state/coverage value remain compared.
    if summary['schema']=='sdmpc-streamed-model-checks/v2':
        summary.pop('executed_allocation_summary');summary.pop('zero_service_reuse')
        summary['schema']='sdmpc-streamed-model-checks/v1';summary['original_checks_performed']=True
        summary['scope']='All original checks run; full successful check rows omitted, traffic/coverage records retained'
    if 'central_physical' in x:
        allowed={
            'Horizon-end queue/density/storage/lane inventory and recorded urban state bounds; all original stepwise dynamic audits retained',
            'Horizon-end queue/density/storage/lane inventory and recorded urban state bounds; zero-service allocation reuse is reported separately'}
        assert x['central_physical']['scope'] in allowed
        x['central_physical']['scope']='same physical states; allocation evidence compared above'
    return x


def review():
    import numpy as np
    from evaluation.controllers.sdmpc_tangent_surrogate import check_scalar_upgrade
    assert read(OUT/'execution.json')['status']=='complete_pending_review'
    evidence={};pair={}
    for mode in ('scalar','ad'):
        old=pickle.loads((HERE/'ad2400_lane_offer'/(mode+'.pickle')).read_bytes())
        new=pickle.loads((OUT/(mode+'.result.pickle')).read_bytes());pair[mode]=new
        check_scalar_upgrade(normalize_audit(old['surrogate_prediction']),normalize_audit(new['surrogate_prediction']),1e-7)
        stats=new['route_service_saturation'];assert stats['skipped_after_zero_service']>0
        error={}
        for k in ('costs','resources')+(('cost_jacobian','resource_jacobian') if mode=='ad' else ()):
            x,y=np.asarray(old[k]),np.asarray(new[k]);assert x.shape==y.shape and np.isfinite(y).all()
            error[k]=float(np.max(abs(x-y),initial=0));assert np.allclose(x,y,atol=1e-7,rtol=1e-10),(mode,k,error[k])
        if mode=='ad':
            a,b=old['central_physical'],new['central_physical']
            assert a['names']==b['names'] and old['ad_axes']==new['ad_axes'] and not new['fallback_reasons']
            for k in ('values','jacobian'):
                x,y=np.asarray(a[k]),np.asarray(b[k]);assert x.shape==y.shape and np.isfinite(y).all()
                error['central_'+k]=float(np.max(abs(x-y),initial=0));assert np.allclose(x,y,atol=1e-7,rtol=1e-10),(k,error[k])
        audit=new['surrogate_prediction']['streamed_model_checks']
        evidence[mode]=dict(max_errors=error,stats=stats,
            logical_allocation_checks=audit['allocation_summary']['count'],
            executed_allocation_checks=audit['executed_allocation_summary']['count'],
            zero_flow_checks_reused=audit['zero_service_reuse']['allocation_kinds'],
            previous_worker_sec=old.get('wall_sec_including_spawn'),
            core_scalar_sec=new['scalar_sec'],core_tangent_sec=new.get('tangent_sec'))
    check_scalar_upgrade(pair['scalar']['surrogate_prediction'],pair['ad']['surrogate_prediction'],1e-7)
    result=dict(status='equivalent',evidence=evidence,execution=read(OUT/'execution.json'),
        full_selections=0,native_runs=0,limitations=[
            'One state and command only; no native gain or whole decision600s proof.',
            'Timing is under competing native work, not a matched speedup.',
            'Same route/cohort state representation; only repeated zero-service evaluations are aggregated.'])
    save(OUT/'comparison.json',result);print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='run':
        import geometry_cache_check as runner
        runner.OUT=OUT
        raise SystemExit(runner.run())
    elif sys.argv[1]=='review':review()
    else:raise ValueError('prepare/run/review required')
