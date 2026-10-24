"""Bounded current-plant replay under recorded controls, not a causal arm test."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse
import copy
import gzip
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
TUNING=ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native348/optimized_config.json'
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--arm',choices=('window','optimized','off'),required=True)
    ap.add_argument('--at',type=int,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--vsl-pair',action='store_true')
    ap.add_argument('--legacy-urban',action='store_true',help='Explicit diagnostic without native348 urban recipe; not a current full-plant validation')
    ap.add_argument('--initialization-only',action='store_true');args=ap.parse_args()
    assert args.at in (2250,3300,4500,5700)
    assert not args.out.exists(),'Preserve existing attempt'
    assert not (HERE/'STOP').exists()
    if args.vsl_pair:assert args.arm=='off' and args.at in (2250,4500)
    folder=Path(f'E:/VISSIM_runs/20261008_coupling268_{args.arm}_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
    tuning=HERE/'legacy_urban_diagnostic_config.json' if args.legacy_urban else TUNING
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    sys.argv=['verify.py','--at',str(args.at),'--out',str(args.out),'--no-prediction','--cold-prices',
        '--tuning',str(tuning),'--decisions',str(folder)]
    spec=importlib.util.spec_from_file_location('response349_bootstrap',ROOT/'diagnostics/repin_v3c3_review_20261001/urban260/verify.py')
    v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_pfo,sdmpc_sequence as seq
    from evaluation.controllers import physical_ramp_branches as ramps,signal_actuation_contract as signals
    from evaluation.controllers import offramp_routing as routing
    from evaluation.controllers import calibrated_urban_runtime as calibration
    from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_hold import fixed_vsl_values
    from src.controllers import rollout_endpoint as endpoint
    from src.models.state import ControlAction
    original_main=adapter.main
    original_projection=calibration.project_current_link
    projection_receipts={}
    def save_projection_receipts():
        (args.out/'projection_receipts.json').write_text(json.dumps(projection_receipts,indent=2)+'\n',encoding='utf8')
    def projection_diagnostic(component,state,cfg,raw,frame,network,inside,lanes):
        try:
            result,receipt=original_projection(component,state,cfg,raw,frame,network,inside,lanes)
            projection_receipts[component.SOURCE]=receipt
            save_projection_receipts()
            return result,receipt
        except Exception as exc:
            detail=dict(error=str(exc),at=state.time_sec,link=component.LINK,source=component.SOURCE,
                physical=[x for x in raw['vehicle_records']['records'] if str(x['link_no'])==component.LINK],
                lane_queues={str(k):v for k,v in lanes.items() if k[0]==component.LINK},
                provenance=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link'].get(component.LINK),
                movements=component.MOVEMENTS)
            (args.out/'initialization_failure.json').write_text(json.dumps(detail,indent=2)+'\n',encoding='utf8')
            raise
    calibration.project_current_link=projection_diagnostic
    corridor=calibration.module('corridor339.project');original_corridor=corridor.install
    def corridor_diagnostic(*a,**kw):
        try:result,receipt=original_corridor(*a,**kw)
        except Exception:
            save_failed_component('corridor',*a)
            raise
        projection_receipts['SC108_to_SC109']=receipt
        save_projection_receipts()
        return result,receipt
    corridor.install=corridor_diagnostic
    terminal=calibration.module('sc105_initial340.candidate');original_terminal=terminal.install
    def save_failed_component(name,cfg,state,raw,frame,network,lanes):
        import pickle
        (args.out/(name+'_initialization_inputs.pickle')).write_bytes(pickle.dumps(
            (cfg,state,raw,frame,network,lanes),protocol=5))
    def terminal_diagnostic(cfg,state,raw,frame,network,lanes):
        try:return original_terminal(cfg,state,raw,frame,network,lanes)
        except Exception as exc:
            save_failed_component('terminal',cfg,state,raw,frame,network,lanes)
            provenance=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
            owners={link:row for link,row in provenance.items() if any(
                n and (k=='storage:'+terminal.TARGET or k in {'movement:'+m for m in terminal.MOVES}) for k,n in row.items())}
            detail=dict(error=str(exc),at=state.time_sec,owners=owners,
                physical=[v for v in raw['vehicle_records']['records'] if str(v['link_no']) in owners],
                frames=[v for v in frame['vehicles'] if str(v[1]) in owners])
            (args.out/'terminal_initialization_failure.json').write_text(json.dumps(detail,indent=2)+'\n',encoding='utf8')
            raise
    terminal.install=terminal_diagnostic
    gate=calibration.module('sc10_north325.candidate');original_gate=gate.install
    def gate_diagnostic(cfg,state,raw,frame,network,lanes):
        try:return original_gate(cfg,state,raw,frame,network,lanes)
        except Exception:
            save_failed_component('gate',cfg,state,raw,frame,network,lanes)
            raise
    gate.install=gate_diagnostic
    timing=calibration.module('sc109_initial320.candidate')
    original_distance=timing.remaining_distance
    def distance_diagnostic(vehicle,next_link,links,stop):
        try:return original_distance(vehicle,next_link,links,stop)
        except Exception as exc:
            import xml.etree.ElementTree as ET
            detail=dict(error=str(exc),vehicle=vehicle,next_link=next_link,receiving_stop_m=stop,
                links={k:ET.tostring(links[k],encoding='unicode') for k in (str(vehicle['link_no']),'173','10280','10281')})
            (args.out/'initialization_failure.json').write_text(json.dumps(detail,indent=2)+'\n',encoding='utf8')
            raise
    timing.remaining_distance=distance_diagnostic
    def wrapped_main():
        captured={};bound=ramps.configure_operating_bounds;forecast=adapter.demand_from_state
        def capture_bound(state,cfg,reference):
            captured.update(state=state,cfg=cfg);return bound(state,cfg,reference)
        def capture_forecast(*a,**kw):
            result=forecast(*a,**kw);captured['forecast']=result;return result
        ramps.configure_operating_bounds=capture_bound;adapter.demand_from_state=capture_forecast
        def audit(*unused,**kw):
            state,cfg=captured['state'],captured['cfg']
            assert state.time_sec==args.at and cfg.simulation.T_f_sec==5 and cfg.simulation.T_u_sec==10
            def save(name,x):(args.out/name).write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
            if args.initialization_only:
                ledger=get_ledger(state);ledger.assert_stocks(model_inventory(state,cfg))
                save('projection_receipts.json',projection_receipts)
                save('summary.json',dict(status='initialized_only',arm=args.arm,at_sec=args.at,new_predictions=0,
                    area_stock={side:sum(row[side] for row in ledger.stocks.values()) for side in ('inside','outside')},
                    model_inventory_checked=True))
                raise v.Done()
            pins={str(tuning):sha(tuning),str(Path(__file__)):sha(__file__)}
            blocks=[]
            for at in range(args.at,args.at+450,150):
                path=folder/f'action_{at:06}.json';assert Path(str(path)+'.applied').exists()
                pins[str(path)]=sha(path)
                command=seq.first_action(adapter.control_from_json(path,cfg,ControlAction))
                signals.validate_writer(command,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
                blocks.append(command)
            save('input_pins.json',pins)
            cases=[('recorded',blocks)]
            if args.vsl_pair:
                for speed in (110,90):
                    alternate=copy.deepcopy(blocks)
                    policy=dict(start_sec=0,base_kmh=110,zone_kmh={'FW_E__seg13':speed})
                    for c in alternate:
                        c.vsl=fixed_vsl_values(c.vsl,policy,cfg.network.freeway_vsl_zone_heads,args.at)
                    for original,changed in zip(blocks,alternate):
                        assert original.green_times==changed.green_times and original.offsets==changed.offsets
                        assert original.ramp_metering==changed.ramp_metering
                    cases.append((f'vsl{speed}',alternate))
            summary=[]
            for name,controls in cases:
                action=seq.pack(controls)
                for c in controls:signals.validate_writer(c,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
                started=time.perf_counter()
                with seq.prediction_scope(action,cfg,args.at,3) as visits:
                    point=endpoint.evaluate_price_point(state,action,copy.deepcopy(captured['forecast']),(),
                        endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
                assert not point.aborted and len(point.states)==3 and visits==[0,1,2]
                response=point.control_area_response
                assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
                snapshots=[]
                for current in (state,*point.states):
                    ledger=get_ledger(current);ledger.assert_stocks(model_inventory(current,cfg))
                    snapshots.append(dict(time_sec=current.time_sec,stocks=ledger.stocks,
                        n=continuity_vehicle_counts(current,cfg),speed=current.freeway_speed,
                        density=current.freeway_density))
                save(name+'_snapshots.json',snapshots)
                (args.out/(name+'_response.json.gz')).write_bytes(gzip.compress(json.dumps(response,allow_nan=False).encode('utf8')))
                save(name+'_control_area.json',point.control_area)
                summary.append(dict(name=name,omega_ttt_veh_h=point.ttt,seconds=time.perf_counter()-started,
                    physical_model_constraints_passed=True,native_executed=False))
                save('prediction_progress.json',summary)
                print('PREDICTION',name,point.ttt,flush=True)
            # Observe targets only after every rollout. Native future states never enter prediction.
            from assess import targets as observed_targets
            targets,target_pins=observed_targets(folder,args.at,tuning)
            pins.update(target_pins)
            initial=read(args.out/'recorded_snapshots.json')[0]
            error=max(abs(x-y) for fw in targets[0]['n'] for x,y in zip(initial['n'][fw],targets[0]['n'][fw]))
            assert error<1e-7,('Initial physical31 counts mismatch',error)
            save('native_targets.json',targets)
            save('summary.json',dict(status='complete_conditional_response',arm=args.arm,start_sec=args.at,end_sec=args.at+450,
                rows=summary,initial_cell_stock_max_error=error,source_pins=pins,
                native348_urban_calibration_enabled=not args.legacy_urban,
                latest_full_plant_validation=not args.legacy_urban,
                future_observations_used_as_input=False,actual_future_commands_used_as_conditions=True,
                autonomous_controller_validation=False,new_native_runs=0,new_fits=0,
                counterfactual_scope='Model-only VSL contrast on same initial state, city/RM controls and demand. Not native causal validation.'))
            raise v.Done()
        sdmpc_pfo.solve=audit
        return original_main()
    adapter.main=wrapped_main
    v.main()

if __name__=='__main__':main()
