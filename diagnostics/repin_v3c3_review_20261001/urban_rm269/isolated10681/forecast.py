"""One held/10681-only fixed450 comparison from the completed native state.

Reuse canonical dynamics, physical actuator writer and previously bounded
receiving candidate. No new coefficients, optimizer or future observations.
"""
import os
for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[k] = '1'
import argparse
import copy
import csv
import ctypes
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
H = HERE.parent
ROOT = HERE.parents[3]
OUT = HERE / 'forecast2400'
F = Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/decisions_sdmpc31_g_2400_hold_s29')
TUNING = H / 'connector_lane/config.json'
read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False,
        default=lambda v: repr(v)[:600])+'\n', encoding='utf8')


def physical_csv(p):
    with p.open(encoding='utf-8-sig', newline='') as f:
        return [{k:v for k,v in row.items() if k!='metadata'} for row in csv.DictReader(f)]


def main():
    global OUT, TUNING
    parser = argparse.ArgumentParser()
    parser.add_argument('--aggregate10', action='store_true',
                        help='Use the opt-in canonical ten-second bridge, without diagnostic model patches')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    aggregate_dir = H/'aggregate270'
    if args.aggregate10:
        OUT = aggregate_dir/'isolated2400_lane_offer'
        TUNING = aggregate_dir/'config_dt10.json'
    if args.out:
        assert args.aggregate10 and args.out.resolve().parent==aggregate_dir.resolve()
        OUT=args.out.resolve()
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    assert not OUT.exists(), 'Preserve existing forecasts/attempts'
    assert not any((p/'STOP').exists() for p in (ROOT,H,HERE,aggregate_dir))
    plan = read(aggregate_dir/'isolated_pair_plan.json' if args.aggregate10 else HERE/'plan_at_execution.json')
    for p,digest in plan['source_pins'].items():
        assert sha(Path(p)) == digest, p
    sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
    os.environ.update(NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'), PYTHONDONTWRITEBYTECODE='1')
    sys.argv = ['verify.py','--at','2400','--out',str(OUT),'--no-prediction','--tuning',str(TUNING),'--decisions',str(F)]
    loader = importlib.util.spec_from_file_location('canonical_isolated_verify', H.parent/'urban260/verify.py')
    v = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(v)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter, sdmpc_pfo, sdmpc_sequence as seq
    from evaluation.controllers import physical_ramp_branches as ramps, signal_actuation_contract as signals
    from evaluation.controllers import area_leader_objective as constraints
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.area_runtime import model_inventory
    from src.controllers import rollout_endpoint as endpoint
    from src.models.state import ControlAction
    original_main = adapter.main

    def wrapped_main():
        # The closed fixed-command native run never invoked the predictor, so
        # its canonical derived observation audit may not exist. Materialize
        # that audit in this diagnostic output only; leave native files intact.
        from evaluation.controllers import obs150_contract as oc
        derived_receipts=[]
        def local_derived(raw,derived):
            at=derived['sim_sec']
            assert at<=2400 and raw['sim_sec']==at
            blob=oc.derived_bytes(derived)
            old=oc.resolve(raw[oc.RAW_STATE_KEY],oc.derived_path(at))
            if old.exists():
                assert old.read_bytes()==blob
                return old
            dest=OUT/'derived_observations'
            dest.mkdir(exist_ok=True)
            p=dest/f'derived_{int(at):06}.json'
            if p.exists():assert p.read_bytes()==blob
            else:p.write_bytes(blob)
            derived_receipts.append(dict(at_sec=at,original=str(old),local=str(p),sha256=hashlib.sha256(blob).hexdigest()))
            save(OUT/'derived_observation_receipts.json',derived_receipts)
            return p
        oc.write_derived=local_derived
        from evaluation.controllers import lane_plant_runtime, obs150_observation
        from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as history
        original_observe=lane_plant_runtime.observe_state
        def observe_with_past_audit(context,raw):
            assert raw['sim_sec']==2400
            for end in range(150,2400,150):
                historical=read(F/f'state_{end:06}.json')
                local_derived(historical,obs150_observation.derive(historical,context['obs150']))
            return original_observe(context,raw)
        lane_plant_runtime.observe_state=observe_with_past_audit
        old_head,old_vsl=history.replay_head_history,history.replay_vsl_history
        def replay_head(*a,**kw):
            kw['derived_directory']=OUT/'derived_observations'
            return old_head(*a,**kw)
        def replay_vsl(*a,**kw):
            kw['derived_directory']=OUT/'derived_observations'
            kw['known_missing_online_cutoffs']=tuple(t for t in range(150,2401,150)
                if not (F/'obs150'/f'vsl_cohorts_{t:06}.json').exists())
            return old_vsl(*a,**kw)
        history.replay_head_history,history.replay_vsl_history=replay_head,replay_vsl
        capture = {}
        old_bounds, old_forecast = ramps.configure_operating_bounds, adapter.demand_from_state
        def bounds(state, cfg, reference):
            capture.update(state=state,cfg=cfg)
            return old_bounds(state,cfg,reference)
        def forecast(*a, **kw):
            result=old_forecast(*a,**kw);capture['forecast']=result;return result
        ramps.configure_operating_bounds, adapter.demand_from_state = bounds, forecast

        def audit(reference,coord,policy,options,evaluate,derivative,quantities,check_budget,emit):
            state,cfg=capture['state'],capture['cfg']
            assert state.time_sec==2400 and len(capture['forecast'])==3
            if args.aggregate10:
                obj=state.known_legsplit_route_state['aggregate_transport']
                assert obj.dt==10
                storage=cfg.network.known_legsplit_routes['storage']
                owned=cfg.network.urban_link_storage_veh[storage]-state.urban_link_storage[storage]
                assert abs(obj.stock()-owned)<1e-8
            save(OUT/'state.json',vars(state));save(OUT/'network.json',vars(cfg.network))
            save(OUT/'forecast_input.json',[vars(x) if hasattr(x,'__dict__') else x for x in capture['forecast']])
            signal_plan=adapter.load_signal_group_actuation_plan()
            calibration=read(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json')
            actuation=adapter.adapter_actuation_settings(calibration,read(TUNING))
            mapping=read(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json')
            segment=adapter.repo_imports(ROOT/'vendor/NumSim-mine')[-1]
            held_blocks=[seq.first_action(adapter.control_from_json(H/'selection2400_discrete/hold'/f'action_{t:06}.json',cfg,ControlAction)) for t in (2400,2550,2700)]
            blocks=[]
            for j,held in enumerate(held_blocks):
                greens={m:held.diagnostics['rw_meter_green_'+m] for m in held.ramp_metering}
                greens['RM_C10681']=float((4,6,8)[j])
                block=ramps.candidate_from_greens(held,blocks[-1] if blocks else held_blocks[0],cfg,greens)
                for field in ('green_times','offsets','vsl','N_P_star','N_UF_star','inflow_outflow_allocation'):
                    assert getattr(block,field)==getattr(held,field),field
                assert {m for m in held.ramp_metering if block.ramp_metering[m]!=held.ramp_metering[m]}=={'RM_C10681'}
                blocks.append(block)
            sequences={'hold':seq.pack(held_blocks),'selected':seq.pack(blocks)}
            results={}
            for name,action in sequences.items():
                coord.validate(action)
                dest=OUT/name;dest.mkdir()
                written=[]
                for j,b in enumerate(seq.actions(action,3)):
                    signals.validate_writer(b,cfg,signal_plan,'experiment')
                    at=2400+150*j
                    meta=copy.deepcopy(read(H/'selection2400_discrete/hold'/f'action_{at:06}.json')['metadata'])
                    for key in ('sdmpc_state','run_provenance','hold_previous'):
                        meta.pop(key,None)
                    meta.update(sim_sec=at,controller_status='fixed_command_replay',diagnostic_scope='Only RM10681 green changes; all city/VSL/otherRM held. No optimization.')
                    stem=dest/f'action_{at:06}'
                    adapter.write_action_csv(stem.with_suffix('.csv'),b,cfg,mapping,segment,meta,actuation,signal_group_plan_table=signal_plan,offset_writer='experiment')
                    save(stem.with_suffix('.json'),adapter.control_to_json_dict(b,meta))
                    restored=adapter.control_from_json(stem.with_suffix('.json'),cfg,ControlAction)
                    assert ramps.physical_commands(restored,cfg)==ramps.physical_commands(b,cfg)
                    actual=physical_csv(stem.with_suffix('.csv'))
                    old=physical_csv(H/'selection2400_discrete/hold'/f'action_{at:06}.csv')
                    assert len(actual)==len(old)
                    changes=[dict(before=x,after=y) for x,y in zip(old,actual) if x!=y]
                    if name=='hold':
                        assert not changes,changes
                    else:
                        assert len(changes)==1 and changes[0]['after']['id']=='RM_C10681',changes
                        assert {k for k in changes[0]['before'] if changes[0]['before'][k]!=changes[0]['after'][k]} <= {'rate_vph','green_sec'}
                    written.append(dict(at=at,changed_physical_rows=changes,csv_sha256=sha(stem.with_suffix('.csv')),json_sha256=sha(stem.with_suffix('.json'))))
                started=time.perf_counter()
                with seq.prediction_scope(action,cfg,2400,3) as visits:
                    point=endpoint.evaluate_price_point(state,action,copy.deepcopy(capture['forecast']),(),endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
                assert not point.aborted and len(point.states)==3 and visits==[0,1,2]
                response=point.control_area_response
                assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
                excess=max((r['exceedance_veh'] for r in response['resource_allocations']),default=0.)
                assert excess<=1e-7
                for s in (state,*point.states):get_ledger(s).assert_stocks(model_inventory(s,cfg))
                if args.aggregate10:
                    obj=point.states[-1].known_legsplit_route_state['aggregate_transport']
                    assert obj.updates==45
                follower=adapter._PHASE_VECTOR_FOLLOWER['ref']
                qs=constraints.shared_urban_quantities(follower,response,start_sec=2400,horizon_steps=3)
                caps=constraints.shared_quantity_constraints(follower,action,qs,start_sec=2400,horizon_steps=3,np_mode='cap',target_np_veh=action.N_P_star,np_tolerance_veh=options['shared_tolerance'],nuf_mode='cap',target_nuf_veh_h=action.N_UF_star,nuf_tolerance_veh_h=options['shared_tolerance'])
                costs={}
                for row in response['residence']:
                    for k,n in row['inside_veh'].items():costs[k]=costs.get(k,0.)+n*row['dt_h']
                assert abs(sum(costs.values())-point.ttt)<1e-7
                result=dict(omega_ttt_veh_h=point.ttt,costs_by_stock=costs,shared_constraints=caps,predicted_merge=point.control_area['predicted_ramp_merge'],resource_max_exceedance=excess,conservation_states=4,commands=written,wall_sec=time.perf_counter()-started)
                save(OUT/(name+'.json'),result);results[name]=result
                with gzip.open(OUT/(name+'.response.json.gz'),'wt',encoding='utf8') as stream:json.dump(response,stream,allow_nan=False)
                print(name,point.ttt,'feasible',caps['feasible'],flush=True)
            delta=lambda k:results['selected']['costs_by_stock'].get(k,0)-results['hold']['costs_by_stock'].get(k,0)
            extra=results['selected']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']-results['hold']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']
            summary=dict(status='complete',initial_state=str(F/'state_002400.json'),model=('canonical10s aggregate and independent lane receiving' if args.aggregate10 else 'connector_lane plus existing causal spatial ramp receiving; no SC101/SC6 trial'),source_pins=plan['source_pins'],fixed_predictions=2,optimizer_calls=0,new_fits=0,new_native=0,
                delta_omega_veh_h=results['selected']['omega_ttt_veh_h']-results['hold']['omega_ttt_veh_h'],
                delta_mainline_veh_h=sum(delta(k) for k in set(results['hold']['costs_by_stock'])|set(results['selected']['costs_by_stock']) if k.startswith('freeway:')),
                delta_W_out_veh_h=delta('storage:SC1004_W_out'),delta_ramp10681_veh_h=delta('ramp:RM_C10681'),extra_merge10681_veh=extra,
                both_same_caps_feasible=all(r['shared_constraints']['feasible'] for r in results.values()),
                native_preparation_allowed=not args.aggregate10 and extra>=30 and all(r['shared_constraints']['feasible'] for r in results.values()),
                interpretation=('Compare with the retained isolated native pair; no new native run authorized by this diagnostic. Small net signs are not a fitting target.' if args.aggregate10 else 'Native isolated effect is unknown. This is a single previously selected ramp trajectory, not a search for a desired sign.'))
            for path,digest in plan['source_pins'].items():assert sha(Path(path))==digest,path
            save(OUT/'summary.json',summary)
            raise v.Done()
        def fixed_entry(controller,state,forecast,previous,cfg,mapping,tuning,provenance,previous_path,options,report_path,**kw):
            # Fixed-command native replay has executed commands but no SDMPC
            # optimizer/price-state history. Enter the canonical endpoint and
            # actuator coordinates directly; never invent that missing history
            # or relax the production optimizer's same-run provenance guard.
            from evaluation.controllers import area_follower_objective as joint
            from evaluation.controllers import area_meter_finalization as meters
            execution=read(H/'native2400_analysis/hold/execution.json')
            assert execution['native_execution_passed']
            assert execution['run_id']==provenance['run_id']==read(F/'state_002400.json')['run_provenance']['run_id']
            witness=next(x for x in execution['checks']['actual_commands']['decisions'] if x['sim_sec']==2250)
            assert witness['sha256']==sha(Path(previous_path).with_suffix('.csv'))
            historical=ramps.held_actual_reference(previous,cfg)
            reference=seq.first_action(meters.prepare_held_actual_reference(historical,cfg))
            ramps.configure_operating_bounds(state,cfg,reference)
            capture.update(state=state,cfg=cfg,forecast=forecast)
            follower=controller.nash_solver
            assert follower.cfg is cfg
            adapter._PHASE_VECTOR_FOLLOWER['ref']=follower
            policy=dict(cfg.network.sdmpc_options)
            with joint.shared_query_runtime_scope():
                callbacks,_,_=joint._joint_runtime_callbacks(follower,state,forecast,historical,reference,mapping,
                    plan['source_pins'],reference=reference,total_budget=None,directional={},
                    tolerance=options['nuf_tolerance_veh_h'],budget=None,price_probe=False)
                coord=seq.SequenceCoordinates(cfg,reference,callbacks['move_box'],policy)
                save(OUT/'fixed_entry_receipt.json',dict(native_execution_sha256=sha(H/'native2400_analysis/hold/execution.json'),
                    previous_csv_sha256=witness['sha256'],run_id=execution['run_id'],
                    optimizer_invoked=False,price_history_invented=False,production_provenance_guard_modified=False))
                audit(reference,coord,policy,options,None,None,None,None,None)
        adapter.run_joint_owner_decision=fixed_entry
        return original_main()
    adapter.main=wrapped_main
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.lateral_turnover.candidate import install as turnover
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.lane_transfer_binding.probe import install as binding
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.spatial_receiving.candidate import install as receiving
    if args.aggregate10:
        receipt=[];initial='Canonical runtime setup; no diagnostic dynamics patches installed'
    else:
        turnover();receipt=binding();initial=receiving(read(H/'spatial_receiving/plan.json')['wave_m_s'])
    v.main()
    save(OUT/'physical_receiving_receipt.json',dict(rows=receipt,initial=initial))


if __name__=='__main__':main()
