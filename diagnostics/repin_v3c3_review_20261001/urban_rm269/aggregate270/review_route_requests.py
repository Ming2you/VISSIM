"""Review the bounded completed10s request experiment without more rollouts."""
import hashlib,json,pickle
from pathlib import Path
import numpy as np
from evaluation.controllers.sdmpc_tangent_surrogate import check_scalar_upgrade

HERE=Path(__file__).resolve().parent;OUT=HERE/'route_requests10';BASE=HERE/'route_interval'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
load=lambda p:pickle.loads(p.read_bytes())
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def main():
    plan=read(OUT/'plan.json');receipt=read(OUT/'execution.json')
    assert receipt['status']=='complete_pending_review' and all(r['exit_code']==0 for r in receipt['results'])
    for p,h in plan['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    pair={n:load(OUT/(n+'.scalar.result.pickle')) for n in ('new_hold','new_release')}
    scalar=pair['new_hold'];ad=load(OUT/'new_hold.ad.result.pickle')
    check_scalar_upgrade(scalar['surrogate_prediction'],ad['surrogate_prediction'],1e-7)
    errors={}
    for name in ('costs','resources'):
        x,y=np.asarray(scalar[name]),np.asarray(ad[name]);assert x.shape==y.shape and np.isfinite(y).all()
        errors[name]=float(np.max(abs(x-y)));assert errors[name]<1e-7
    a,b=scalar['surrogate_prediction']['central_physical'],ad['central_physical']
    assert a['names']==b['names'] and len(a['values'])==5112
    errors['central_values']=float(np.max(abs(np.asarray(a['values'])-np.asarray(b['values']))));assert errors['central_values']<1e-7
    assert len(ad['ad_axes'])==213 and not ad['fallback_reasons']
    for array,shape in ((ad['cost_jacobian'],(20,213)),(ad['resource_jacobian'],(2,213)),(b['jacobian'],(5112,213))):
        assert np.asarray(array).shape==shape and np.isfinite(array).all()
    rows={};margins={}
    for label,folder in (('previous',BASE),('requests10',OUT)):
        hold,release=[load(folder/(n+'.scalar.result.pickle'))['surrogate_prediction'] for n in ('new_hold','new_release')]
        rows[label]=dict(delta_omega_veh_h=release['objective_veh_h']-hold['objective_veh_h'],
            delta_owner_veh_h={k:release['sdmpc_omega_partition']['costs'][k]-v for k,v in hold['sdmpc_omega_partition']['costs'].items()},
            extra_merge10681_veh=(release['quantities']['predicted_ramp_merge']['rate_veh_h_by_ramp']['RM_C10681']-hold['quantities']['predicted_ramp_merge']['rate_veh_h_by_ramp']['RM_C10681'])*450/3600)
    for name,data in pair.items():
        r=data['surrogate_prediction'];action=load(OUT/(name+'.pickle'))['action']
        assert r['model_constraint_coverage']['complete'] and r['conditional_model_feasibility_witness'] and r['resource_summary']['max_exceedance_veh']<1e-7
        assert abs(sum(r['sdmpc_omega_partition']['costs'].values())-r['objective_veh_h'])<1e-7
        margins[name]=dict(np_veh=action.N_P_star-data['resources'][0],nuf_veh_h=action.N_UF_star-data['resources'][1])
    evidence=dict(status='one_state_response_and_ad_reviewed',max_abs_scalar_ad_errors=errors,deltas=rows,cap_margins=margins,
        execution=receipt,trace_operations=ad['trace'].get('operations'),full_selections=0,native_runs=0,
        adoption='candidate_only; no whole-decision speed or native gain qualification',
        limits=['Requests10s, accepted service/receiving1s; not full urban10s or freeway5s.',
                'Held route shares change model dynamics; not an exact optimization.',
                'No independent-state test of this additional request holding yet.',
                'Timing under competing workload; no matched speedup claim.'])
    save(OUT/'review.json',evidence);receipt['status']='complete_reviewed';save(OUT/'execution.json',receipt)
    plan.update(status='one_state_response_ad_complete_candidate_only',review='review.json');save(OUT/'plan.json',plan)
    print(json.dumps(dict(deltas=rows,errors=errors,cap_margins=margins,timing=receipt['results'],trace_operations=evidence['trace_operations']),ensure_ascii=False))


if __name__=='__main__':main()
