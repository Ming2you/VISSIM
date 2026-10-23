"""Prepare independent-seed evaluation, without starting predictions."""
from pathlib import Path
import hashlib,json
A=Path(__file__).resolve().parent;ROOT=A.parents[1]
original=ROOT/'ramp360_seed67.py'
source=original.read_text(encoding='utf8')
target=A/'run_refine15_independent.py';assert not target.exists()
s=source
def replace(old,new):
    global s
    assert s.count(old)==1,(old[:80],s.count(old))
    s=s.replace(old,new)
replace("ROOT=Path('E:/VISSIM_runtime/20261011_native354_numeric_fixed_vsl_three/frozen/sdmpc31_ca181e84_202610111941');HERE=ROOT/'diagnostics/vsl_response349';BASE=Path('E:/VISSIM_analysis/20261011_vsl_response349')", "ROOT=Path('D:/VISSIM_packages/vsl_multizone355_20261015');HERE=ROOT/'diagnostics/vsl_response349';BASE=Path('E:/VISSIM_analysis/20261011_vsl_response349');A=Path(__file__).resolve().parent")
replace("TUNING=R/'urban_rm269/aggregate270/native348/optimized_config.json'", "TUNING=R/'urban_rm269/aggregate270/vsl_schedules_20261015/config.json'")
replace("choices=(67,),default=67", "choices=(67,71),required=True")
replace("    arms=('release','release_vsl90')", "    arms=('release','release_vsl90') if a.seed==67 else ('rm','both')\n    assert not a.spatial_targets,'Adopted355 receiving is already configured; do not attach twice'\n    fit=read(A/'refine15_regime_fit_v3/selection.json');done=read(A/'refine15_regime_fit_v3/completion.json')\n    assert fit['eligible']\n    for p,h in done['source_pins'].items():assert sha(p)==h,p\n    old=read(A/'refine15_update_audit.json');p=old['parent_parameters'];r=old['state_response']\n    variants={'original':[p['rho_crit'],p['metanet_a_m'],r['relaxation']['acceleration_sec'],r['anticipation']['downstream_ge_local'],r['anticipation']['downstream_lt_local']],'fitted':fit['fitted']['values']}")
replace("    def wrapped_main():\n", "    def wrapped_main():\n        from refine_approach15 import Refinement\n        from evaluation.controllers import multirate_freeway\n        refine=Refinement(a.out);old_limit=multirate_freeway.time_limit\n        multirate_freeway.time_limit=lambda runtime,state:min(.625,old_limit(runtime,state))\n")
replace("zip(commands['release'],commands['release_vsl90'])", "zip(commands[arms[0]],commands[arms[1]])")
replace("        return original_main()", "        try:return original_main()\n        finally:\n            refine.restore();multirate_freeway.time_limit=old_limit")
start=s.index('            results={}\n')
end=s.index('            raise verifier.Done()',start)
s=s[:start]+'''            results={};origin_state,origin_cfg=state,cfg
            pins[str(A/'refine15_regime_fit_v3/selection.json')]=sha(A/'refine15_regime_fit_v3/selection.json')
            pins[str(A/'refine_approach15.py')]=sha(A/'refine_approach15.py')
            assert hasattr(origin_state,'_refine15')
            for name in ('RM_C10639','RM_C10484'):
                buf=origin_state.lane_ramp_runtime.buffers[name]
                assert all(getattr(b,'_causal_receiving_enabled',False) for b in getattr(buf,'_lane_buffers',[buf]))
            for variant,values in variants.items():
                for arm in arms:
                    state,cfg=copy.deepcopy((origin_state,origin_cfg))
                    for net in (cfg.network,state.lane_freeway_runtime.configs['FW_E'].network):
                        net.freeway_segment_params['FW_E'][15].update(rho_crit=values[0],metanet_a_m=values[1])
                        if not hasattr(net,'freeway_state_response'):net.freeway_state_response={}
                        net.freeway_state_response.setdefault('FW_E',{}).setdefault('cell_overrides',{})['15']=dict(relaxation=dict(acceleration_sec=values[2],deceleration_sec=values[2]),anticipation=dict(downstream_ge_local=values[3],downstream_lt_local=values[4]))
                    label=variant+'_'+arm;action=seq.pack(commands[arm]);tick=time.perf_counter();refine.trace=[]
                    with seq.prediction_scope(action,cfg,start,3) as visits:
                        point=endpoint.evaluate_price_point(state,action,copy.deepcopy(captured['forecast'][:3]),(),endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
                    elapsed=time.perf_counter()-tick;assert visits==[0,1,2] and not point.aborted and len(point.states)==3
                    response=point.control_area_response
                    assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
                    snapshots=[]
                    for current in (state,*point.states):
                        ledger=get_ledger(current);ledger.assert_stocks(model_inventory(current,cfg))
                        snapshots.append(dict(time_sec=current.time_sec,stocks=ledger.stocks,n=continuity_vehicle_counts(current,cfg),speed=current.freeway_speed,ramp_queue=current.ramp_queue,refinement=current._refine15))
                    assert initial==get_ledger(state).stocks and initial_n==continuity_vehicle_counts(state,cfg)
                    costs={};outside={}
                    for row in response['residence']:
                        for key,value in row['inside_veh'].items():
                            costs[key]=costs.get(key,0.)+value*row['dt_h']
                            outside[key]=outside.get(key,0.)+(row['model_stock_veh'][key]-value)*row['dt_h']
                    assert abs(sum(costs.values())-point.ttt)<1e-7
                    through=[sum(x['accepted_total_veh'] for x in response['resource_allocations'] if x['kind']=='freeway_mainline_sending' and x['resource']=='FW_E:cell:18' and x['end_sec']<=start+t+1e-8) for t in (150,300,450)]
                    (a.out/(label+'_response.json.gz')).write_bytes(gzip.compress(json.dumps(response,allow_nan=False).encode('utf8')))
                    save(label+'_snapshots.json',snapshots);save(label+'_subcells.json',refine.trace)
                    results[label]=dict(ttt=point.ttt,costs_by_stock=costs,outside_costs_by_stock=outside,throughflow=through,seconds=elapsed,physical_constraints=True,writer=True,sdmpc_cap_or_selection_claimed=False)
                    save('prediction_progress.json',results);print('INDEPENDENT',a.seed,label,point.ttt,elapsed,flush=True)
            for p,h in pins.items():assert sha(p)==h,p
            save('summary.json',dict(status='complete_frozen_independent_pair_comparison',seed=a.seed,start=start,end=start+450,results=results,new_predictions=4,native_runs=0,fits=0,coefficient_updates=0,parameters=variants,independent_from_fit=True,previous_native_outcomes_seen_during_model_development=True,blind_test_claimed=False,source_pins=pins,max_route_balance=refine.max_balance,max_vsl_balance=refine.max_cohort,candidate_adopted=False))
''' +s[end:]
compile(s,str(target),'exec');target.write_text(s,encoding='utf8')
print(json.dumps(dict(prepared=str(target),native_runs=0,launched=False,maximum_forecasts_per_seed=4,script_sha256=hashlib.sha256(target.read_bytes()).hexdigest())))
