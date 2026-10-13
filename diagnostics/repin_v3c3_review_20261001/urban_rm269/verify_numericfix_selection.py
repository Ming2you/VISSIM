"""Two discrete forecasts of the completed canonical numericfix2400 selection, canonical writer.

No new optimizer, coefficient fit, future observation input or native launch.
Use the selected NP/NUF caps for both commands and retain the450s horizon.
"""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import copy,csv,gzip,hashlib,importlib.util,json,sys,time
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PAIR=HERE/'runtime_pair2400_numericfix'
OUT=HERE/'numericfix_selection_discrete'
F=Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')

def main():
    assert not OUT.exists(), 'Preserve an existing execution check'
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    os.environ.update(NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'),PYTHONDONTWRITEBYTECODE='1')
    pair=read(PAIR/'plan.json')
    assert pair['status'] in ('both_complete_equivalence_pending','complete_equivalent')
    assert read(PAIR/'comparison.json')['status']=='equivalent'
    for arm in ('cache_off','cache_on'):
        receipt=read(PAIR/(arm+'.execution.json'))
        assert receipt['status']=='complete_uncompared' and receipt['exit_code']==0
    assert not (HERE/'STOP').exists() and not (PAIR/'STOP').exists()
    pins=pair['source_pins']
    for p,h in pins.items():assert sha(ROOT/p)==h,p
    for p in (Path(__file__),HERE/'runtime_pair2400_numericfix/cache_off_config.json',HERE/'runtime_pair2400_numericfix/cache_off/unused.json',
              HERE/'runtime_pair2400_numericfix/cache_off_review.json',F/'state_002400.json'):
        pins[str(p)]=sha(p)
    proof=read(HERE/'runtime_pair2400_numericfix/cache_off_review.json')
    assert proof['status']=='completed_feasible_offline_choice_reviewed' and proof['final_constraints']['feasible']
    sys.argv=['verify.py','--at','2400','--out',str(OUT),'--no-prediction',
        '--tuning',str(HERE/'runtime_pair2400_numericfix/cache_off_config.json'),'--decisions',str(F)]
    spec=importlib.util.spec_from_file_location('canonical_execution_verifier',HERE.parent/'urban260/verify.py')
    v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_pfo
    from evaluation.controllers import physical_ramp_branches as ramps,signal_actuation_contract as signals
    from evaluation.controllers import sdmpc_sequence as seq,area_leader_objective as constraints
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.area_runtime import model_inventory
    from src.controllers import rollout_endpoint as endpoint
    from src.models.state import ControlAction
    original_main=adapter.main
    def wrapped_main():
        capture={};bound=ramps.configure_operating_bounds;forecast=adapter.demand_from_state
        def capture_bound(state,cfg,reference):
            capture.update(state=state,cfg=cfg)
            return bound(state,cfg,reference)
        def capture_forecast(*a,**kw):
            f=forecast(*a,**kw);capture['forecast']=f;return f
        ramps.configure_operating_bounds=capture_bound;adapter.demand_from_state=capture_forecast
        def audit(reference,coord,policy,options,evaluate,derivative,quantities,check_budget,emit):
            state,cfg=capture['state'],capture['cfg']
            assert state.time_sec==2400 and len(capture['forecast'])==3
            assert cfg.network.known_legsplit_routes['local_queue_gate']
            oldref=read(HERE/'runtime_pair2400_numericfix/cache_off/reference.json')
            fields=('ramp_metering','vsl','green_times','offsets','inflow_outflow_allocation')
            assert all(getattr(reference,k)==oldref[k] for k in fields)
            selected=adapter.control_from_json(HERE/'runtime_pair2400_numericfix/cache_off/unused.json',cfg,ControlAction)
            coord.validate(selected)
            held=reference.copy();held.N_P_star=selected.N_P_star;held.N_UF_star=selected.N_UF_star
            coord.validate(held)
            calibration=read(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json')
            tuning=read(HERE/'runtime_pair2400_numericfix/cache_off_config.json')
            actuation=adapter.adapter_actuation_settings(calibration,tuning)
            mapping=read(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json')
            segment=adapter.repo_imports(ROOT/'vendor/NumSim-mine')[-1]
            signal_plan=adapter.load_signal_group_actuation_plan()
            source_meta=read(HERE/'runtime_pair2400_numericfix/cache_off/unused.json')['metadata']
            results={}
            for name,action in [('hold',held),('selected',selected)]:
                blocks=seq.actions(action,3);folder=OUT/name;folder.mkdir()
                written=[]
                for j,b in enumerate(blocks):
                    signals.validate_writer(b,cfg,signal_plan,'experiment')
                    meta=copy.deepcopy(source_meta)
                    for stale in ('sdmpc_state','run_provenance','hold_previous'):meta.pop(stale,None)
                    meta.update(sim_sec=2400+j*150,controller_status='fixed_command_replay',
                        diagnostic_scope='Previously selected three-block command; fixed-control execution validation, not a new optimization')
                    stem=folder/f'action_{2400+j*150:06}'
                    adapter.write_action_csv(stem.with_suffix('.csv'),b,cfg,mapping,segment,meta,actuation,
                        signal_group_plan_table=signal_plan,offset_writer='experiment')
                    save(stem.with_suffix('.json'),adapter.control_to_json_dict(b,meta))
                    restored=adapter.control_from_json(stem.with_suffix('.json'),cfg,ControlAction)
                    assert all(getattr(restored,k)==getattr(b,k) for k in fields)
                    assert all(2<=b.diagnostics['rw_meter_green_'+r]<=10 for r in cfg.network.ramps)
                    written.append(dict(sim_sec=2400+j*150,json_sha256=sha(stem.with_suffix('.json')),
                        csv_sha256=sha(stem.with_suffix('.csv')),
                        greens={r:b.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps}))
                started=time.perf_counter()
                with seq.prediction_scope(action,cfg,2400,3) as visits:
                    point=endpoint.evaluate_price_point(state,action,copy.deepcopy(capture['forecast']),(),
                        endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
                assert not point.aborted and len(point.states)==3 and visits==[0,1,2]
                response=point.control_area_response
                assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
                exceed=max((r['exceedance_veh'] for r in response['resource_allocations']),default=0.)
                assert exceed<=1e-7
                for s in (state,*point.states):get_ledger(s).assert_stocks(model_inventory(s,cfg))
                follower=adapter._PHASE_VECTOR_FOLLOWER['ref']
                qs=constraints.shared_urban_quantities(follower,response,start_sec=2400,horizon_steps=3)
                constraint=constraints.shared_quantity_constraints(follower,action,qs,start_sec=2400,horizon_steps=3,
                    np_mode='cap',target_np_veh=selected.N_P_star,np_tolerance_veh=options['shared_tolerance'],
                    nuf_mode='cap',target_nuf_veh_h=selected.N_UF_star,nuf_tolerance_veh_h=options['shared_tolerance'])
                costs={}
                for row in response['residence']:
                    for k,n in row['inside_veh'].items():costs[k]=costs.get(k,0.)+n*row['dt_h']
                assert abs(sum(costs.values())-point.ttt)<1e-7
                result=dict(omega_ttt_veh_h=point.ttt,costs_by_stock=costs,shared_constraints=constraint,
                    predicted_merge=point.control_area['predicted_ramp_merge'],resource_max_exceedance=exceed,
                    conservation_states=4,commands=written,wall_sec=time.perf_counter()-started)
                save(OUT/(name+'.json'),result);results[name]=result
                with gzip.open(OUT/(name+'_response.json.gz'),'wt',encoding='utf8') as f:json.dump(response,f,allow_nan=False)
                print(name,point.ttt,'feasible',constraint['feasible'],flush=True)
            result=dict(status='two_discrete_predictions_complete',source_pins=pins,results=results,
                delta_omega_ttt_veh_h=results['selected']['omega_ttt_veh_h']-results['hold']['omega_ttt_veh_h'],
                selected_model_caps_feasible=results['selected']['shared_constraints']['feasible'],
                native_runs=0,new_optimizer_calls=0,coefficient_fits=0,
                continuous_prediction_delta=proof['selected_objective']-proof['held_objective'],
                scope='Same physical2400 state, current2s minimum, actual discrete signal phases; native gain not yet established')
            save(OUT/'summary.json',result)
            raise v.Done()
        sdmpc_pfo.solve=audit
        return original_main()
    adapter.main=wrapped_main
    v.main()

if __name__=='__main__':main()
