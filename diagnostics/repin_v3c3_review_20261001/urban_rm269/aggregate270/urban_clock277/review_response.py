"""Review completed actual coupled predictions; no new rollouts."""
import json,pickle,sys,hashlib,math
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];M=HERE.parent/'multirate271'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
read=lambda p:json.loads(p.read_bytes())
obj=lambda p:pickle.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def row(r):
    p=r['surrogate_prediction'];coverage=p['model_constraint_coverage']
    assert coverage['complete'] and p['conditional_model_feasibility_witness']
    assert p['resource_summary']['max_exceedance_veh']<1e-7
    assert abs(sum(r['costs'])-p['objective_veh_h'])<1e-7
    merge=p['quantities']['predicted_ramp_merge']['accepted_vehicles_by_ramp']
    flows=p['control_area']['flow_counts']
    for ramp,n in merge.items():
        assert abs(n-flows.get('ramp:'+ramp+'->merge_pending:'+ramp,0.))<1e-7
    costs=dict(p['local_base_costs']);costs['PASSIVE_OMEGA']=p['objective_veh_h']-sum(costs.values())
    return dict(omega_veh_h=p['objective_veh_h'],owner_costs=costs,merges_veh=merge,
        resource_exceedance_veh=p['resource_summary']['max_exceedance_veh'],coverage=coverage)
def compare(a,b):
    errors={k:float(np.max(abs(np.array(a[k])-np.array(b[k])))) for k in ('costs','resources')}
    ca=a.get('central_physical',a['surrogate_prediction']['central_physical'])
    cb=b.get('central_physical',b['surrogate_prediction']['central_physical'])
    assert ca['names']==cb['names']
    errors['central_states']=float(np.max(abs(np.array(ca['values'])-np.array(cb['values']))))
    assert max(errors.values())<1e-7,errors
    return errors
def main():
    records={name:obj(HERE/(name+'_result.pickle')) for name in ('hold_v5','release_v3','hold_ad_v1','default_v1')}
    old_hold=obj(M/'macro_hold_v2_result.pickle');old_release=obj(M/'macro_release_v2_result.pickle')
    rows={name:row(r) for name,r in records.items()};rows.update(old_hold=row(old_hold),old_release=row(old_release))
    ad=records['hold_ad_v1'];errors=compare(ad,records['hold_v5'])
    assert ad['fallback_reasons']=={}
    matrices={k:np.asarray(ad[k]) for k in ('cost_jacobian','resource_jacobian')}
    matrices['central_state_jacobian']=np.asarray(ad['central_physical']['jacobian'])
    assert all(v.shape[1]==213 and np.isfinite(v).all() for v in matrices.values())
    deltas={}
    for mode,a,b in (('urban1',rows['old_hold'],rows['old_release']),('urban10',rows['hold_v5'],rows['release_v3'])):
        deltas[mode]=dict(omega_veh_h=b['omega_veh_h']-a['omega_veh_h'],
            merge10681_veh=b['merges_veh']['RM_C10681']-a['merges_veh']['RM_C10681'],
            owners={k:b['owner_costs'][k]-a['owner_costs'][k] for k in a['owner_costs']})
    for k in ('FW_E','FW_W','SC1004','PASSIVE_OMEGA'):
        assert deltas['urban1']['owners'][k]*deltas['urban10']['owners'][k]>0
    assert deltas['urban1']['omega_veh_h']*deltas['urban10']['omega_veh_h']>0
    old_ad=obj(M/'macro_hold_ad_v3_result.pickle')
    pins=None;wall={}
    for name in records:
        receipt=read(HERE/(name+'_execution.json'))
        assert receipt['exit_code']==0 and receipt['source_pins_unchanged']
        assert all(sha(Path(p))==h for p,h in receipt['source_pins'].items())
        pins=receipt['source_pins'];wall[name]=receipt['wall_sec']
    report=dict(status='single_state_fw5_urban10_scalar_ad_checked',rows=rows,deltas=deltas,
        scalar_ad_errors=errors,default_urban1_errors=compare(records['default_v1'],old_hold),
        jacobian_shapes={k:list(v.shape) for k,v in matrices.items()},
        operations=dict(urban1=old_ad['trace']['operations'],urban10=ad['trace']['operations']),
        wall_sec=wall,source_pins=pins,
        limitations=['One saved seed29 state at2400s,450s RM hold/release; not native benefit or independent seed qualification.',
            'Urban residence uses10s endpoint quadrature; physical transfer histories/short cell numerics stay explicit.',
            'Different signal and VSL actions, full decision timing and other initial states still require checks.',
            'Wall time depends on concurrent machine load; operation counts are the direct work comparison.'])
    (HERE/'response_review.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_pins','rows','limitations')},ensure_ascii=False))
if __name__=='__main__':main()
