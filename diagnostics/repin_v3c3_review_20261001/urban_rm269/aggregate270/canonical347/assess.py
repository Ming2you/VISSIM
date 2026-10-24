"""Read-only result comparison; no model predictions or optimization."""
from pathlib import Path
import hashlib,json,math,pickle,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.worker334.assess import numeric_error
from evaluation.controllers.sdmpc_tangent_surrogate import check_scalar_upgrade
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    base=Path(sys.argv[1]);assert not (base/'assessment.json').exists(),'Preserve completed comparison'
    cases={k:pickle.loads((base/k/'result.pickle').read_bytes()) for k in
           ('legacy_scalar','static_scalar','legacy_ad','static_ad')}
    pins=read(base/'source_pins.json')
    for p,h in pins.items():assert sha(Path(p))==h,p
    for name,r in cases.items():
        assert 'error' not in r,(name,r.get('error'))
        assert r['request_sha256']=='13d2b1399ee41645530790fc75eb4f40b252be36773a890f38b744a63b971f4c'
        assert r['current_source_pins']==pins
        assert r['optional_per_stock_cost_report_omitted']
        assert r['branch315_dynamic_ast_instrumented']==name.startswith('legacy')
        hooks=r['latest_model_hooks'];assert len(hooks)==1
        assert hooks[0]['conservation_states']==4
        assert hooks[0]['branch']['rates']=={'1129:branch:bypass':904.}
        assert all(hooks[0][k]>0 for k in ('transport_count','north_count','routes_count',
                                         'side_count','gate_count','prehead_count'))
        sp=r['surrogate_prediction']
        assert sp['model_constraint_coverage']['complete']
        assert sp['conditional_model_feasibility_witness']
        assert sp['resource_summary']['max_exceedance_veh']<1e-7
        assert abs(sum(sp['sdmpc_omega_partition']['costs'].values())-sp['objective_veh_h'])<1e-7
        if name.endswith('_scalar'):
            assert r['scalar_rollouts']==1 and r['tangent_rollouts']==0
        else:
            assert r['scalar_rollouts']==0 and r['tangent_rollouts']==1
            assert r['ad_axes']==list(range(213)) and not r['fallback_reasons']
        for p,h in r['transformed_source_sha256'].items():assert sha(Path(p))==h,p
    errors={}
    for left,right in (('legacy_scalar','static_scalar'),('legacy_ad','static_ad'),
                       ('static_scalar','static_ad'),('legacy_scalar','legacy_ad')):
        x,y=cases[left],cases[right]
        label=left+'__'+right
        errors[label]={k:numeric_error(x[k],y[k],k) for k in ('costs','resources')}
        check_scalar_upgrade(x['surrogate_prediction'],y['surrogate_prediction'],1e-7)
        errors[label]['central_primal']=numeric_error(x['surrogate_prediction']['central_physical'],
                                    y['surrogate_prediction']['central_physical'])
        errors[label]['ledger_stocks']=numeric_error(read(base/left/'stocks.json'),read(base/right/'stocks.json'))
        if left.endswith('_ad') and right.endswith('_ad'):
            for k in ('cost_jacobian','resource_jacobian'):
                errors[label][k]=numeric_error(x[k],y[k],k)
            errors[label]['central_jacobian']=numeric_error(x['central_physical']['jacobian'],
                                                           y['central_physical']['jacobian'])
        assert max(errors[label].values())<1e-7,(label,errors[label])
    r=cases['static_ad'];shapes={}
    for label,matrix,rows in (('owner_cost',r['cost_jacobian'],len(r['costs'])),
                             ('NP_NUF',r['resource_jacobian'],len(r['resources'])),
                             ('central',r['central_physical']['jacobian'],len(r['central_physical']['names']))):
        assert len(matrix)==rows and all(len(row)==213 for row in matrix)
        assert all(math.isfinite(v) for row in matrix for v in row)
        shapes[label]=[rows,213]
    r=cases['static_scalar'];sp=r['surrogate_prediction']
    report=dict(status='explicit_branch_service_matches_legacy_primal_and_full_gradient',
        errors=errors,matrix_shapes=shapes,omega_ttt_veh_h=sp['objective_veh_h'],
        owner_costs_veh_h=sp['sdmpc_omega_partition']['costs'],resources=r['resources'],
        predicted_merge=sp['control_area']['predicted_ramp_merge'],resource_summary=sp['resource_summary'],
        times={k:{n:v for n,v in r.items() if n in ('scalar_sec','tangent_sec','reverse_sec','wall_sec_including_imports')}
               for k,r in cases.items()},
        matched_current_tree=True,pickle_boundary=True,states_checked_per_worker=4,
        predictions=4,full_sdmpc_selection=0,new_native=0,new_fits=0,goal_complete=False,
        adopted='Explicit opt-in production branch service; current native/frozen configs untouched.',
        limitations=['One saved3300 state; equivalence to prior approximate model, not a native-gain certificate.',
            '904veh/h is a past observed discharge lower bound, not identified saturation.',
            'Other diagnostic rollout and initialization hooks remain to be connected canonically.',
            'This runtime change does not correct the remaining10681 discharge magnitude or2400 city-control gain error.',
            'Single paired timing; no end-to-end9000 runtime or speedup claim.',
            'Physical ledger equality is checked at150s boundaries and existing rollout guards, not every hidden field.'],
        request_sha256=r['request_sha256'],preparation=read(base/'preparation.json'))
    result_pins=dict(pins)
    for name in cases:
        for suffix in ('result.pickle','stocks.json','completion.json'):
            p=base/name/suffix;result_pins[str(p)]=sha(p)
    result_pins[str(Path(__file__))]=sha(Path(__file__))
    report['source_pins']=result_pins
    (base/'assessment.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:report[k] for k in ('status','errors','matrix_shapes','omega_ttt_veh_h','times')},ensure_ascii=False))
if __name__=='__main__':main()

