"""Bounded local lane/route aggregation check, reusing the existing worker runner."""
import hashlib,json,pickle,sys
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OUT=HERE/'local_lane_routes';BASE=HERE/'route_interval'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:pickle.loads(p.read_bytes())
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')


def prepare():
    from evaluation.controllers import aggregate_local_urban as model
    from evaluation.controllers.sdmpc_tangent_surrogate import token
    assert not OUT.exists(),'No duplicate candidate'
    assert read(HERE/'route_requests10/decision.json')['status']=='not_adopted_no_material_work_reduction'
    OUT.mkdir();metadata={};changed=[]
    for name in ('new_hold','new_release'):
        request=load(BASE/(name+'.pickle'))
        for path,old in list(request['bootstrap']['runtime_sources'].items()):
            now=sha(path)
            if now!=old:
                assert Path(path).name in ('runtime_setup.py','physical_urban_transport.py'),path
                changed.append(dict(path=path,before=old,after=now));request['bootstrap']['runtime_sources'][path]=now
        path=ROOT/'evaluation/controllers/aggregate_local_urban.py'
        request['bootstrap']['runtime_sources'][str(path)]=sha(path)
        metadata[name]=model.configure(request['owned'][0].cfg,{'urban':{'local_lane_route_aggregate':True}},request['owned'][1])
        request['surrogate_context_sha256']=token((request['owned'],request['runtime'],request['bootstrap'],request['horizon']))
        (OUT/(name+'.pickle')).write_bytes(pickle.dumps(request,protocol=5))
    cfg=read(HERE/'config_dt10_routes.json');cfg['urban']['local_lane_route_aggregate']=True
    save(HERE/'config_dt10_local_lanes.json',cfg)
    pins={str(p):sha(p) for p in (ROOT/'evaluation/controllers').glob('*.py')}
    for p in (Path(__file__),HERE/'route_request_check.py',ROOT/'tests/test_aggregate_local_urban.py',HERE/'config_dt10_local_lanes.json'):pins[str(p)]=sha(p)
    save(OUT/'plan.json',dict(status='prepared',source_pins=pins,changed_sources=changed,projection=metadata,
        scalar_max=2,ad_max=1,full_selections=0,native_runs=0,
        scope='Local40cells of126/10641/71 use destination/continuation classes. Same external prefix admission; shared old receiving; per-cell aggregate forwardFIFO; no additional gain coefficients.',
        preserve='Same2400 state,RM10681hold2/2/2 vsrelease4/6/8,othercontrols,caps,450s,Omega701,terminalOFF,network,demand.',
        limitations='Not full urban10s/freeway5s. Changes within-cell FIFO and lateral competition. Native gain and whole decision wall unqualified.'))


def review():
    from evaluation.controllers.sdmpc_tangent_surrogate import check_scalar_upgrade
    plan=read(OUT/'plan.json');receipt=read(OUT/'execution.json')
    assert receipt['status']=='complete_pending_review'
    for p,h in plan['source_pins'].items():assert sha(p)==h,p
    scalar=load(OUT/'new_hold.scalar.result.pickle');ad=load(OUT/'new_hold.ad.result.pickle')
    check_scalar_upgrade(scalar['surrogate_prediction'],ad['surrogate_prediction'],1e-7)
    errors={}
    for name in ('costs','resources'):
        errors[name]=float(np.max(abs(np.asarray(scalar[name])-np.asarray(ad[name]))));assert errors[name]<1e-7
    a,b=[x['surrogate_prediction']['central_physical'] for x in (scalar,ad)]
    assert a['names']==b['names'] and len(a['values'])==5112
    errors['central']=float(np.max(abs(np.asarray(a['values'])-np.asarray(b['values']))));assert errors['central']<1e-7
    assert len(ad['ad_axes'])==213 and not ad['fallback_reasons']
    for array,shape in ((ad['cost_jacobian'],(20,213)),(ad['resource_jacobian'],(2,213)),(b['jacobian'],(5112,213))):
        assert np.asarray(array).shape==shape and np.isfinite(array).all()
    rows={}
    for name,folder in (('previous',BASE),('aggregate',OUT)):
        h,r=[load(folder/(n+'.scalar.result.pickle'))['surrogate_prediction'] for n in ('new_hold','new_release')]
        for x in (h,r):
            assert x['model_constraint_coverage']['complete'] and x['conditional_model_feasibility_witness']
            assert x['resource_summary']['max_exceedance_veh']<1e-7
            assert abs(sum(x['sdmpc_omega_partition']['costs'].values())-x['objective_veh_h'])<1e-7
        rows[name]=dict(hold_omega=h['objective_veh_h'],release_omega=r['objective_veh_h'],delta_omega=r['objective_veh_h']-h['objective_veh_h'],
            delta_owner={k:r['sdmpc_omega_partition']['costs'][k]-v for k,v in h['sdmpc_omega_partition']['costs'].items()},
            extra_merge10681_veh=(r['quantities']['predicted_ramp_merge']['rate_veh_h_by_ramp']['RM_C10681']-h['quantities']['predicted_ramp_merge']['rate_veh_h_by_ramp']['RM_C10681'])*450/3600)
    old=load(BASE/'new_hold.ad.result.pickle')
    evidence=dict(status='one_state_response_ad_reviewed',errors=errors,rows=rows,execution=receipt,
        operations_before=old['trace']['operations'],operations_after=ad['trace']['operations'],
        operation_reduction_fraction=1-ad['trace']['operations']/old['trace']['operations'],
        native_gain_qualified=False,whole_decision_wall_qualified=False)
    save(OUT/'review.json',evidence);receipt['status']='complete_reviewed';save(OUT/'execution.json',receipt)
    plan['status']='one_state_response_ad_reviewed';save(OUT/'plan.json',plan)
    print(json.dumps(evidence,ensure_ascii=False))


if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='run':
        import route_request_check as runner
        runner.OUT=OUT
        raise SystemExit(runner.run())
    elif sys.argv[1]=='review':review()
    else:raise ValueError('prepare/run/review only')
