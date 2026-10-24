"""Two autonomous450s fixed-command predictions; no native/optimizer/fit."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import copy,gzip,hashlib,importlib.util,json,pickle,sys,time
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.gate296.candidate import geometry,installed
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_phase305.candidate import hook, validate_turns, west, east, MOV, verify_pending, ATTR
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.candidate import project, SOURCE as ROUTE_SOURCE
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_composite308.candidate import install as install_sc109
from candidate import install as install_side
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_composite308.inputs import inputs
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal
from diagnostics.repin_v3c3_review_20261001.urban_rm269.sc101_recombined import candidate as service

CASE=Path(__file__).resolve().parent
HERE=CASE.parent/'sc12_initial306'
ROOT=HERE.parents[4]
A=HERE.parent;H=A.parent
OUT=Path('E:/VISSIM_analysis/20261010_sc108_side310/forecast2400')
PREV=A/'matched280/authority'
CITY=A/'citysplit287/forecast2400'
SOURCE=Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
save=lambda n,v:(OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def main():
    assert not OUT.exists(),'Preserve attempted output; no automatic retry'
    assert not any((p/'STOP').exists() for p in (ROOT,H,A,HERE))
    old=read(PREV/'summary.json')
    assert all(sha(p)==h for p,h in old['source_pins'].items())
    pins=dict(old['source_pins'])
    for p in (*CASE.glob('*.py'),CASE/'plan.json',CASE/'tests.log'):
        pins[str(p)]=sha(p)
    for support_file in ('past_shared_prefix_support.json','assessment.json','tests.log'):
        pins[str(A/'sc12_phase305'/support_file)]=sha(A/'sc12_phase305'/support_file)
    pins.update(read(A/'sc12_phase305/past_shared_prefix_support.json')['source_pins'])
    for p in [*HERE.glob('*.py'),HERE/'config.json',HERE/'plan.json',CITY/'initial.pickle',
              CITY/'summary.json',A/'cityresponse290/assessment.json',A/'gatearrival291/assessment.json',
                A/'gate296/candidate.py',A/'sourcepath292/candidate.py',
                H/'sc12w_service/candidate.py',H/'sc12w_service/typed_support_v3.json',
                H/'sc16_supply/candidate.py',H/'sc16_supply/assessment.json',HERE/'preflight_v2.json',A/'combined298/candidate.py',A/'sc101_clock299/source_geometry.py',A/'sc101_clock299/source_geometry.json',A/'sc15_source301/calibration.json',A/'sc15_source301/candidate.py',A/'sc101_peeloff302/evidence.json',A/'sc101_peeloff302/candidate.py',A/'sc101_route_tags303/support.json',A/'sc101_route_tags303/candidate.py',H/'sc101_recombined/candidate.py',H/'sc101_recombined/service_evidence.json',A/'sc101_clock299/candidate.py',A/'sc101_route_tags303/tests.log']:
        pins[str(p)]=sha(p)
    for p in (HERE/'tests_v3.log',A/'sc12_phase305/candidate.py',A/'sc12_phase305/current_projection.json'):
        pins[str(p)]=sha(p)
    option=read(HERE/'config.json');tuning=ROOT/option['base_tuning']
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    sys.argv=['verify.py','--at','2400','--out',str(OUT),'--no-prediction','--cold-prices',
              '--tuning',str(tuning),'--decisions',str(SOURCE)]
    loader=importlib.util.spec_from_file_location('combined298_verifier',H.parent/'urban260/verify.py')
    verifier=importlib.util.module_from_spec(loader);loader.loader.exec_module(verifier)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_pfo,sdmpc_sequence as seq
    from evaluation.controllers import physical_ramp_branches as ramps,signal_actuation_contract as signals
    from evaluation.controllers import area_leader_objective as constraints
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.sdmpc_tangent_worker import state_error
    from src.controllers import rollout_endpoint as endpoint
    from src.models.state import ControlAction
    original=adapter.main
    def wrapped():
        captured={};bound=ramps.configure_operating_bounds;forecast=adapter.demand_from_state
        def capture_bound(state,cfg,reference):
            captured.update(state=state,cfg=cfg)
            return bound(state,cfg,reference)
        def capture_forecast(*a,**kw):
            value=forecast(*a,**kw);captured['forecast']=value;return value
        ramps.configure_operating_bounds=capture_bound;adapter.demand_from_state=capture_forecast
        def evaluate(reference,coord,policy,options,*args):
            state,cfg=captured['state'],captured['cfg']
            oldcfg,oldstate,oldforecast=pickle.loads((CITY/'initial.pickle').read_bytes())
            assert state.time_sec==2400 and cfg.simulation.T_f_sec==5 and cfg.simulation.T_u_sec==10
            error=state_error(state,oldstate);assert error<1e-10,error
            assert get_ledger(state).stocks==get_ledger(oldstate).stocks
            expected_movements=copy.deepcopy(oldcfg.network.urban_movements)
            expected_movements[MOV]['unsignalized']=True
            assert cfg.network.urban_movements==expected_movements
            assert cfg.network.movement_capacity_by_movement_veh_h[MOV]==oldcfg.network.movement_capacity_by_movement_veh_h[MOV]
            for field,key in (('local_service_pool','groups'),('head_service_resources','resources')):
                assert not any(MOV in str(group) for group in getattr(cfg.network,field,{}).get(key,{}).values())
            changed={k for k,v in cfg.network.movement_capacity_by_movement_veh_h.items()
                if v!=oldcfg.network.movement_capacity_by_movement_veh_h[k]}
            assert changed==set(west.MEMBERS)|set(east.MEMBERS),changed
            before_service=dict(vars(cfg.network))
            application=service.install(cfg,2400)
            network_change={k for k,v in vars(cfg.network).items() if v is not before_service[k]}
            assert network_change=={'movement_capacity_by_movement_veh_h'},network_change
            cap_change={k for k,v in cfg.network.movement_capacity_by_movement_veh_h.items() if v!=before_service['movement_capacity_by_movement_veh_h'][k]}
            assert cap_change=={service.MOVEMENT},cap_change
            assert application['after_veh_h']==5236.47858772522
            assert max(application['support']['end_sec'])<2400
            save('candidate_application.json',application)
            pins.update(read(H/'sc101_recombined/service_evidence.json')['source_pins'])
            validate_turns(cfg.network)
            assert cfg.network.sc12_phase305['rate']==read(A/'sc12_phase305/past_shared_prefix_support.json')['selected_support']['rate']
            assert cfg.network.local_service_pool['groups'][west.GROUP]['service_veh_h']==cfg.network.sc12_phase305['rate']
            save('sc12_candidate_application.json',cfg.network.sc12_phase305)
            for key in (west.GROUP,east.GROUP):
                assert key in cfg.network.local_service_pool['groups']
            save('service_metadata.json',dict(combined298=cfg.network.combined298_service,sc15_source301=cfg.network.sc15_source301,sc101_peeloff302=cfg.network.sc101_peeloff302))
            assert pickle.dumps(captured['forecast'],protocol=5)==pickle.dumps(oldforecast,protocol=5)
            geom=geometry(ROOT,cfg)
            pins[geom['network_path']]=geom['network_sha256']
            pins[geom['lane_factor_path']]=geom['lane_factor_sha256']
            pins[geom['gate']['sig_file']['path']]=geom['gate']['sig_file']['sha256']
            save('geometry.json',geom)
            canonical=state
            _,_,raw,frame,network,inside,lanes=inputs()
            state,projection=project(canonical,cfg,raw,frame,network,inside,lanes)
            changed_fields={k for k,v in vars(state).items() if not equal(v,vars(canonical)[k])}
            assert changed_fields=={'urban_movement_queue','local_observation_summary','gate_initial_route_tags','_control_area_ledger'},changed_fields
            assert state.urban_arrival_buffer==canonical.urban_arrival_buffer and state.urban_storage_release_buffer==canonical.urban_storage_release_buffer
            for side_key in ('inside','outside'):
                assert abs(sum(x[side_key] for x in get_ledger(state).stocks.values())-sum(x[side_key] for x in get_ledger(canonical).stocks.values()))<1e-8
            pins.update(read(A/'sc12_phase305/current_projection.json')['source_pins'])
            membership=ROOT/read(tuning)['control_area_objective']['membership_path'];pins[str(membership)]=sha(membership)
            save('initial_projection.json',projection)
            prior_rates=dict(cfg.network.movement_capacity_by_movement_veh_h)
            sc109_application=install_sc109(cfg,state.time_sec)
            assert {k for k,v in prior_rates.items() if v!=cfg.network.movement_capacity_by_movement_veh_h[k]}=={sc109_application['movement']}
            pins.update(sc109_application['source_pins'])
            save('sc109_application.json',sc109_application)
            side_application=install_side(cfg,state.time_sec)
            pins.update(side_application['source_pins'])
            save('sc108_side_application.json',side_application)
            baseline_state=pickle.dumps(state,protocol=5)
            plan=adapter.load_signal_group_actuation_plan()
            results={}
            for arm,folder in (('hold',H/'selection2400_discrete/hold'),('city',CITY/'city_only')):
                blocks=[]
                for at in (2400,2550,2700):
                    p=folder/f'action_{at:06}.json';pins[str(p)]=sha(p)
                    command=seq.first_action(adapter.control_from_json(p,cfg,ControlAction))
                    signals.validate_writer(command,cfg,plan,'experiment')
                    ramps.candidate_from_greens(command,blocks[-1] if blocks else reference,cfg,
                        {k:command.diagnostics['rw_meter_green_'+k] for k in command.ramp_metering})
                    blocks.append(command)
                action=seq.pack(blocks);coord.validate(action)
                if arm=='hold':held=copy.deepcopy(blocks)
                else:
                    for c,h in zip(blocks,held):
                        assert ramps.physical_commands(c,cfg)==ramps.physical_commands(h,cfg)
                        assert c.vsl==h.vsl and c.N_P_star==h.N_P_star and c.N_UF_star==h.N_UF_star
                receipt_start=len(side['receipts'])
                start=time.perf_counter()
                with installed(cfg,option['diagnostic_source_path_delay'],geom) as receipts:
                    with seq.prediction_scope(action,cfg,2400,3) as visits:
                        point=endpoint.evaluate_price_point(state,action,copy.deepcopy(captured['forecast'][:3]),(),
                            endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
                wall=time.perf_counter()-start
                side_rows=side['receipts'][receipt_start:]
                assert {r['decision'] for r in side_rows}=={'1099','1100'}
                save(arm+'.side_receipts.json',side_rows)
                save('side_geometry.json',side['geometry'])
                for field in ('network','lane_factor'):
                    pins[side['geometry'][field+'_path']]=side['geometry'][field+'_sha256']
                assert not point.aborted and len(point.states)==3 and visits==[0,1,2]
                gate_end=point.states[-1]._sc10_gate296
                gate_report={k:v for k,v in gate_end.items() if k!='pending'}
                gate_report['pending']=[dict(due_step=k[0],post_steps=k[1],vehicles=v) for k,v in gate_end['pending'].items()]
                save(arm+'.gate.json',gate_report)
                assert len(gate_end['history'])==45
                assert all(not (x['green_sec']==0 and x['discharged']>1e-8) for x in gate_end['history'])
                response=point.control_area_response
                assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
                exceed=max((r['exceedance_veh'] for r in response['resource_allocations']),default=0.)
                assert exceed<1e-7
                for current in (state,*point.states):
                    get_ledger(current).assert_stocks(model_inventory(current,cfg))
                    verify_pending(current)
                assert all(s.gate_initial_route_tags.get(ROUTE_SOURCE,{})=={} for s in point.states),'Initial route cohort failed to mature'
                route_tag_states=[getattr(s,ATTR,{}) for s in point.states]
                assert all(s.get('receipts',0)>0 for s in route_tag_states)
                save(arm+'.route_tags.json',route_tag_states)
                assert pickle.dumps(state,protocol=5)==baseline_state,'Prediction mutated initial state'
                seen={r['source'] for r in receipts}
                expected={t['source'] or t['route_key'] for t in response['transfers']
                    if t['target']=='storage:SC12_to_SC6' and t['source']!=t['target'] and t['vehicles']>1e-9}
                # A configured movement with zero accepted flow needs no travel
                # receipt. Check all ACTUAL incoming sources, not all declared ones.
                assert receipts and expected<=seen<=set(geom['sources']),(expected,seen)
                costs={}
                for row in response['residence']:
                    for k,n in row['inside_veh'].items():costs[k]=costs.get(k,0)+n*row['dt_h']
                assert abs(sum(costs.values())-point.ttt)<1e-7
                follower=adapter._PHASE_VECTOR_FOLLOWER['ref']
                shared=constraints.shared_urban_quantities(follower,response,start_sec=2400,horizon_steps=3)
                feasible=constraints.shared_quantity_constraints(follower,action,shared,start_sec=2400,horizon_steps=3,
                    np_mode='cap',target_np_veh=action.N_P_star,np_tolerance_veh=options['shared_tolerance'],
                    nuf_mode='cap',target_nuf_veh_h=action.N_UF_star,nuf_tolerance_veh_h=options['shared_tolerance'])
                results[arm]=dict(omega_ttt_veh_h=point.ttt,costs_by_stock=costs,shared_constraints=feasible,
                    predicted_merge=point.control_area['predicted_ramp_merge'],resource_max_exceedance=exceed,
                    writer_three_blocks=True,conservation_states=4,wall_sec=wall,
                    accepted_sources=sorted(expected),delay_sources=sorted(seen))
                (OUT/(arm+'.response.json.gz')).write_bytes(gzip.compress(json.dumps(response,allow_nan=False).encode('utf8')))
                save(arm+'.json',results[arm]);save(arm+'.delay_receipts.json',receipts)
                print('SC108_SIDE310',arm,point.ttt,wall,flush=True)
            assert all(sha(p)==h for p,h in pins.items())
            save('summary.json',dict(status='complete',canonical_state_error_before_projection=error,initial_projection=projection,sc109_application=sc109_application,sc108_side_application=side_application,changed_initial_fields=sorted(changed_fields),source_pins=pins,
                start_sec=2400,end_sec=2850,results=results,forecasts=2,optimizer_calls=0,native_runs=0,fits=1,inherited_source_rates=3,
                future_observation_inputs=False,production_changes=0,sc101_side_entry_geometry=True,gate_dynamics_added=True,sc15_source_service=True,sc101_peeloff302=True,aggregate_source_tags303=True,sc101_past_service304=True,sc12_shared_prefix305=True,sc12_initial306=True,past_supported_service_components=['SC12W960','SC16East1677.27']))
            raise verifier.Done()
        sdmpc_pfo.solve=evaluate
        return original()
    adapter.main=wrapped
    with hook(option['diagnostic_sc101_side_entry']) as side:verifier.main()


if __name__=='__main__':main()
