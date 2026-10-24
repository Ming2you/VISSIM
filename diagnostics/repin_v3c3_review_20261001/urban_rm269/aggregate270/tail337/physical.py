"""Two physical signal-clock predictions for the saved337 command pair."""
from pathlib import Path
from contextlib import ExitStack
from datetime import datetime,timezone
import copy,gzip,json,os,pickle,time,traceback
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.tail337.prepare import HERE,A,S,ROOT,read,sha,save,inputs

def main():
    out=HERE/'physical_v2'; assert not out.exists(),'Preserve physical attempt'
    assert read(HERE/'tail_execution.json')['status']=='complete'
    assert not any((p/'STOP').exists() for p in (ROOT,A.parent,A,HERE))
    pins=read(HERE/'source_compatibility.json')['source_pins']
    assert all(sha(p)==h for p,h in pins.items())
    request,coord,plan=inputs(); saved=pickle.loads((HERE/'selected.pickle').read_bytes())
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal
    assert all(equal(request[k],saved['request'][k]) for k in ('owned','runtime','bootstrap','horizon'))
    from src.controllers import rollout_endpoint as endpoint
    from evaluation.controllers import area_follower_objective as joint,area_leader_objective as constraints
    from evaluation.controllers import sdmpc_sequence as seq,signal_actuation_contract as signals,physical_ramp_branches as ramps
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.area_runtime import model_inventory
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.branch_service315.candidate import enabled as branch
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_transport317.candidate import enabled as transport
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc10_north325.candidate import enabled as north
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.native_routes329.candidate import enabled as routes
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_phase305.candidate import hook,verify_pending
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.gate296.candidate import installed,geometry
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc108_geometry311.candidate import clock
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.flow_scope333.groups import family_keys
    follower,state,reference,forecast=request['owned'];cfg=follower.cfg
    options=read(S/'full3300/unused.joint.json')['options']
    assert cfg.simulation.T_f_sec==5 and cfg.simulation.T_u_sec==10 and cfg.mpc.horizon_steps==3
    out.mkdir();write=lambda n,v:(out/n).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    record=dict(status='running',pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),forecasts=2,new_native=0)
    write('execution.json',record);started=time.perf_counter();results={}
    frozen=pickle.dumps(state,protocol=5)
    groups={'approach52':sorted(family_keys(cfg.network.urban_movements,('SC1005_to_SC1004','SC107_to_SC1004')))}
    try:
        for label in ('held','selected'):
            action=saved[label][0];coord.validate(action)
            for b in seq.actions(action,3):signals.validate_writer(b,cfg,plan,'experiment')
            tick=time.perf_counter()
            with ExitStack() as stack:
                br=stack.enter_context(branch());tr=stack.enter_context(transport());ng=stack.enter_context(north());rt=stack.enter_context(routes())
                side=stack.enter_context(hook('source_path_current_physical_speed'))
                gate=stack.enter_context(installed(cfg,'aggregate_sc10_native_calendar',geometry(ROOT,cfg)))
                prehead=stack.enter_context(clock(cfg));stack.enter_context(joint.shared_query_runtime_scope())
                visits=stack.enter_context(seq.prediction_scope(action,cfg,3300,3))
                point=endpoint.evaluate_price_point(state,action,copy.deepcopy(forecast[:3]),(),
                    endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
                assert not point.aborted and len(point.states)==3 and visits==[0,1,2]
                stocks=[]
                for s in (state,*point.states):
                    get_ledger(s).assert_stocks(model_inventory(s,cfg));verify_pending(s)
                    stocks.append(dict(time_sec=s.time_sec,stocks=copy.deepcopy(get_ledger(s).stocks)))
            assert pickle.dumps(state,protocol=5)==frozen
            response=point.control_area_response
            assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
            exceed=max((r['exceedance_veh'] for r in response['resource_allocations']),default=0.)
            assert exceed<=options['shared_tolerance']
            inside={};outside={}
            for row in response['residence']:
                for k,n in row['inside_veh'].items():inside[k]=inside.get(k,0.)+n*row['dt_h']
                for k,n in row['model_stock_veh'].items():outside[k]=outside.get(k,0.)+(n-row['inside_veh'].get(k,0.))*row['dt_h']
            assert abs(sum(inside.values())-point.ttt)<1e-7
            q=constraints.shared_urban_quantities(follower,response,start_sec=3300,horizon_steps=3)
            check=constraints.shared_quantity_constraints(follower,action,q,start_sec=3300,horizon_steps=3,
                np_mode='cap',target_np_veh=action.N_P_star,np_tolerance_veh=options['np_tolerance_veh'],
                nuf_mode='cap',target_nuf_veh_h=action.N_UF_star,nuf_tolerance_veh_h=options['nuf_tolerance_veh_h'])
            result=dict(omega_ttt=point.ttt,inside_costs=inside,outside_costs=outside,shared_constraints=check,
                group_costs={g:sum(inside.get(k,0.) for k in keys) for g,keys in groups.items()},
                groups=groups,predicted_merge=q['predicted_ramp_merge'],wall_sec=time.perf_counter()-tick,
                conservation_states=4,resource_max_exceedance=exceed,writer_three_blocks=True,
                hooks=dict(branch=br,transport=len(tr),north=len(ng),routes=len(rt),side=len(side['receipts']),gate=len(gate),prehead=len(prehead)))
            (out/(label+'.checkpoint.pickle')).write_bytes(pickle.dumps((result,stocks,response),protocol=5))
            write(label+'.json',result);write(label+'.stocks.json',stocks)
            (out/(label+'.response.json.gz')).write_bytes(gzip.compress(json.dumps(response,allow_nan=False).encode()))
            results[label]=result
            print('PHYSICAL337',label,point.ttt,'shared_feasible',check['feasible'],flush=True)
        assert all(sha(p)==h for p,h in pins.items())
        delta=results['selected']['omega_ttt']-results['held']['omega_ttt']
        write('summary.json',dict(status='complete',start_sec=3300,end_sec=3750,forecasts=2,new_native=0,
            continuous_installed=False,delta_ttt=delta,results=results,
            both_shared_feasible=all(r['shared_constraints']['feasible'] for r in results.values()),
            direction_retained=delta<0,limit='Physical-clock model, not VISSIM. One saved state; small net sign does not qualify whole-network native gain.'))
        record['status']='complete'
    except BaseException:
        record.update(status='failed_preserved',error=traceback.format_exc());raise
    finally:
        record.update(wall_sec=time.perf_counter()-started,completed_forecasts=len(results));write('execution.json',record)

if __name__=='__main__':main()
