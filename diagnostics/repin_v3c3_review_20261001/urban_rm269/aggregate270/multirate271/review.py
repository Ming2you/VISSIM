"""Review completed artifacts only; no simulations, forecasts or optimizers."""
import hashlib,json,pickle,sys
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];BASE=HERE.parent/'route_interval'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
unpickle=lambda p:pickle.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
def error(a,b):return float(np.max(abs(np.asarray(a)-np.asarray(b))))


def row(r):
    p=r['surrogate_prediction'];coverage=p['model_constraint_coverage']
    assert coverage['complete'] and coverage['schedule_complete'] and p['conditional_model_feasibility_witness']
    assert p['resource_summary']['max_exceedance_veh']<1e-7
    assert abs(sum(r['costs'])-p['objective_veh_h'])<1e-7
    by_owner=dict(p['local_base_costs']);by_owner['PASSIVE_OMEGA']=p['objective_veh_h']-sum(by_owner.values())
    merge=p['quantities']['predicted_ramp_merge']['accepted_vehicles_by_ramp']
    flows=p['control_area']['flow_counts'];packet_error=0.
    for ramp,n in merge.items():
        source=flows.get('ramp:'+ramp+'->merge_pending:'+ramp,0.)
        consumed=sum(v for k,v in flows.items() if k.startswith('merge_pending:'+ramp+'->freeway:'))
        packet_error=max(packet_error,abs(n-source),abs(n-consumed))
    assert packet_error<1e-7
    return dict(omega_veh_h=p['objective_veh_h'],owner_costs=by_owner,merges_veh=merge,
        packet_conservation_error_veh=packet_error,
        resource_exceedance_veh=p['resource_summary']['max_exceedance_veh'],
        expected_and_completed_visits=coverage['expected_visits'],
        allocation_checks=p['resource_summary']['count'],
        freeway_internal_steps=p['resource_summary']['kinds']['freeway_entry_request']//2)


def main():
    from evaluation.controllers.sdmpc_tangent_surrogate import token
    records={name:unpickle(path) for name,path in {
        'hold1':BASE/'new_hold.scalar.result.pickle','release1':BASE/'new_release.scalar.result.pickle',
        'hold5':HERE/'macro_hold_v2_result.pickle','release5':HERE/'macro_release_v2_result.pickle',
        'default1':HERE/'default_after_macro_result.pickle',
        'hold5_ad':HERE/'macro_hold_ad_v3_result.pickle','release5_ad':HERE/'macro_release_ad_v2_result.pickle'}.items()}
    rows={name:row(r) for name,r in records.items()}
    default_errors={k:error(records['default1'][k],records['hold1'][k]) for k in ('costs','resources')}
    a,b=[records[k]['surrogate_prediction'] for k in ('default1','hold1')]
    assert a['central_physical']['names']==b['central_physical']['names']
    default_errors['central']=error(a['central_physical']['values'],b['central_physical']['values'])
    assert max(default_errors.values())<1e-7
    for k in ('quantities','model_constraint_coverage','resource_summary'):assert a[k]==b[k],k
    ad_checks={}
    for name in ('hold5','release5'):
        a,b=records[name+'_ad'],records[name]
        errors={k:error(a[k],b[k]) for k in ('costs','resources')}
        ca,cb=a['central_physical'],b['surrogate_prediction']['central_physical']
        assert ca['names']==cb['names']
        errors['central']=error(ca['values'],cb['values'])
        assert max(errors.values())<1e-7 and a['fallback_reasons']=={}
        matrices={k:np.asarray(a[k]) for k in ('cost_jacobian','resource_jacobian')}
        matrices['central_jacobian']=np.asarray(ca['jacobian'])
        assert all(np.all(np.isfinite(v)) and v.shape[1]==213 for v in matrices.values())
        ad_checks[name]=dict(max_abs_errors=errors,shapes={k:list(v.shape) for k,v in matrices.items()},
            finite=True,operations=a['trace']['operations'],tangent_sec=a['tangent_sec'],fallbacks=a['fallback_reasons'])
    delta={}
    for clock in (1,5):
        a,b=rows['hold'+str(clock)],rows['release'+str(clock)]
        delta[str(clock)]=dict(omega_veh_h=b['omega_veh_h']-a['omega_veh_h'],
            merge10681_veh=b['merges_veh']['RM_C10681']-a['merges_veh']['RM_C10681'],
            owner_costs={k:b['owner_costs'][k]-a['owner_costs'][k] for k in a['owner_costs']})
    for owner in ('FW_E','FW_W','SC1004','PASSIVE_OMEGA'):
        assert delta['1']['owner_costs'][owner]*delta['5']['owner_costs'][owner]>0
    original_ad=unpickle(BASE/'new_hold.ad.result.pickle')
    old_request=unpickle(BASE/'new_hold.pickle');new_request=unpickle(HERE/'macro_hold_ad_v3_request.pickle')
    assert token(old_request['action'])==token(new_request['action'])
    assert token(old_request['owned'][3])==token(new_request['owned'][3])
    work=dict(old_operations=original_ad['trace']['operations'],new_operations=ad_checks['hold5']['operations'],
        reduction_pct=100*(1-ad_checks['hold5']['operations']/original_ad['trace']['operations']),
        old_ad_wall_sec=read(BASE/'ad_execution.json')['results'][0]['wall_sec'],
        new_ad_wall_sec=read(HERE/'macro_hold_ad_v3_execution.json')['wall_sec'],
        scope='Same saved2400 state inputs,held three-block commands,demand,213axes. Actual wall affected by concurrent native load; not fullSDMPC600s qualification.')
    receipt=dict(status='single_state_fw5_coupled_scalar_ad_pass',reviewed_utc=datetime.now(timezone.utc).isoformat(),
        rows=rows,deltas=delta,default1_max_abs_error=default_errors,ad=ad_checks,matched_work=work,
        tests=dict(passed=48,wall_sec=.58,scope='multirate freeway/ramp/port plus retained aggregate and causal regression tests'),
        limitations=['Urban physical update remains1s;10s bins are only selected arrival/route aggregation.',
          'Freeway exchanges90times per450s; shared internal substeps retain31physicalcells and finite conserved transfers.',
          'Only saved2400 state/seed29,RM hold/release tested. No new native benefit,heldout/VSLdirection or fulldecision wall claim.',
          'AD is conditional on active branches/numerical step count; finite213axis Jacobian and scalar agreement are not all-axis FD validation.',
          'Macro-end residence/arrival landing is a coarse approximation; no model parameter or gain bonus fitted. TTD reward rejected.',
          'First macro failure preserved: only last substep route receipt reached10638. Fixed by summing each accepted route class over5s.',
          'Chronology: scalar v2 preceded additional unsupported-mode guards; ADreleasev2 preceded configure-only hook. Numerical advance functions unchanged thereafter; final ADhold/default regression use final sources.'],
        source_pins={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'evaluation/controllers').glob('*.py')})
    save(HERE/'review.json',receipt)
    for label in ('macro_hold_v2','macro_release_v2','macro_release_ad_v2','macro_hold_ad_v3','default_after_macro'):
        p=HERE/(label+'_execution.json');x=read(p)
        assert x['exit_code']==0 and x['source_pins_unchanged']
        x.update(status='complete_reviewed',review='review.json')
        if label=='default_after_macro':x['scope_correction']='This receipt is the unchanged freeway1s/urban1s default regression; original generic scope text mentioned5s.'
        save(p,x)
    print(json.dumps(dict(status=receipt['status'],deltas=delta,matched_work=work,default1_errors=default_errors),ensure_ascii=False))


if __name__=='__main__':main()
