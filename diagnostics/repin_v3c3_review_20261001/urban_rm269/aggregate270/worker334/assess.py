"""Compare saved independent continuous scalar/AD responses without rollout."""
from pathlib import Path
import hashlib,json,math,pickle

HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def numeric_error(a,b,path='value'):
    if isinstance(a,dict) and isinstance(b,dict):
        assert set(a)==set(b),(path,'keys')
        return max((numeric_error(a[k],b[k],path+'/'+str(k)) for k in a),default=0.)
    if isinstance(a,(list,tuple)) and isinstance(b,type(a)):
        assert len(a)==len(b),(path,'size')
        return max((numeric_error(x,y,path+'/'+str(i)) for i,(x,y) in enumerate(zip(a,b))),default=0.)
    if type(a) in (int,float) and type(b) in (int,float):
        assert math.isfinite(a) and math.isfinite(b),path
        return abs(a-b)
    assert type(a)==type(b) and a==b,(path,a,b)
    return 0.

def main():
    assert not (HERE/'assessment.json').exists(),'Keep prior audit'
    from evaluation.controllers.sdmpc_tangent_surrogate import check_scalar_upgrade
    scalar=pickle.loads((HERE/'scalar/result.pickle').read_bytes())
    ad=pickle.loads((HERE/'ad_v3/result.pickle').read_bytes())
    assert 'error' not in scalar and 'error' not in ad
    assert scalar['request_sha256']==ad['request_sha256']==read(HERE/'capture_v2/summary.json')['request_sha256']
    assert scalar['scalar_rollouts']==1 and scalar['tangent_rollouts']==0
    assert ad['scalar_rollouts']==0 and ad['tangent_rollouts']==1
    assert ad['ad_axes']==list(range(213)) and not ad['fallback_reasons']
    errors={k:numeric_error(scalar[k],ad[k],k) for k in ('costs','resources')}
    sp,ap=scalar['surrogate_prediction'],ad['surrogate_prediction']
    common_sp=dict(sp)
    #Only the optional read-only per-stock residence decomposition is absent
    #from AD. No costs, quantities, constraints or ledger stocks are excluded.
    assert ad['optional_per_stock_cost_report_omitted']
    diagnostic_costs=common_sp.pop('diagnostic_stock_costs_veh_h')
    assert abs(sum(diagnostic_costs.values())-sp['objective_veh_h'])<1e-7
    check_scalar_upgrade(common_sp,ap,1e-7)
    errors['central_values']=numeric_error(sp['central_physical'],ap['central_physical'],'central')
    errors['ledger_stocks']=numeric_error(read(HERE/'scalar/stocks.json'),read(HERE/'ad_v3/stocks.json'),'stocks')
    assert max(errors.values())<1e-7,errors
    matrix_shapes={}
    for name,matrix,rows in (
        ('cost',ad['cost_jacobian'],len(ad['costs'])),
        ('resource',ad['resource_jacobian'],len(ad['resources'])),
        ('central',ad['central_physical']['jacobian'],len(ad['central_physical']['names']))):
        assert len(matrix)==rows and all(len(row)==213 for row in matrix),name
        assert all(math.isfinite(n) for row in matrix for n in row),name
        matrix_shapes[name]=[rows,213]
    for item in (sp,ap):
        assert item['model_constraint_coverage']['complete']
        assert item['conditional_model_feasibility_witness']
        assert item['resource_summary']['max_exceedance_veh']<1e-7
        assert abs(sum(item['sdmpc_omega_partition']['costs'].values())-item['objective_veh_h'])<1e-7
    hooks={}
    for name,result in (('scalar',scalar),('ad',ad)):
        rows=result['latest_model_hooks'];assert len(rows)==1
        row=rows[0];assert row['conservation_states']==4 and result['branch315_dynamic_ast_instrumented']
        assert row['branch']['rates']=={'1129:branch:bypass':904.}
        assert all(row[k]>0 for k in ('transport_count','north_count','routes_count','side_count','gate_count','prehead_count'))
        hooks[name]=row
    pins={}
    for result in (scalar,ad):
        for p,h in result['transformed_source_sha256'].items():
            assert sha(Path(p))==h,p
            if p in pins:assert pins[p]==h
            pins[p]=h
    for p in (HERE/'capture_v2/request.pickle',HERE/'capture_v2/summary.json',HERE/'worker.py',Path(__file__),HERE/'plan.json',
              HERE/'scalar/result.pickle',HERE/'ad_v3/result.pickle',HERE/'scalar/stocks.json',HERE/'ad_v3/stocks.json'):
        pins[str(p)]=sha(p)
    result=dict(status='same_latest_model_continuous_scalar_ad_passed',axes=213,max_difference=errors,
        matrix_shapes=matrix_shapes,omega_ttt_veh_h=sp['objective_veh_h'],owner_costs_veh_h=sp['sdmpc_omega_partition']['costs'],
        resources=scalar['resources'],predicted_merge=sp['control_area']['predicted_ramp_merge'],
        resource_summary=sp['resource_summary'],hook_receipts=hooks,
        timings={k:{n:v for n,v in row.items() if n in ('scalar_sec','tangent_sec','reverse_sec','wall_sec_including_imports')}
                 for k,row in (('scalar',scalar),('ad',ad))},source_pins=pins,
        conserved_states_per_worker=4,latest_cfg_state_forecast_frozen=True,writer_blocks=3,
        scalar_rollouts=1,ad_rollouts=1,full_sdmpc_selection=False,new_native=0,new_fits=0,
        production_adopted=False,goal_complete=False,
        limitations=['Continuous signal/cycle-mean-meter model; do not compare its value as exact332 physical-clock value.',
                     'Primal agreement is not a finite-difference derivative certificate or native ranking.',
                     'Full central values and ledger stocks compared at450s trajectory boundaries; not every intermediate state field.',
                     '3300 single-state worker qualification; whole city/joint direction and unused seed still need validation.'])
    (HERE/'assessment.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('status','axes','max_difference','matrix_shapes','omega_ttt_veh_h','timings')},ensure_ascii=False))

if __name__=='__main__':main()
