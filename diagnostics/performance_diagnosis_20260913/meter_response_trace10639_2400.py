"""One additional raw endpoint forE8's RM_C10639g8; reuse saved actual-hold capture."""
from pathlib import Path
import copy
import hashlib
import json
import os
import pickle
import subprocess
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[2]
BASE=Path(__file__).with_name('lever_counterfactual2400')/'meter_trace10490_attempt01'
OUT=BASE.parent/'meter_trace10639_attempt01'
RUN=ROOT/'evaluation/runs/codex_fid_cl9000_s13_v3/decisions_codex_fid_cl9000_s13_v3'
CONFIG=ROOT/'diagnostics/selected_control_demand/codex_fid_cl9000_s13_v3/config.json'
MID='RM_C10639'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def worker():
    os.chdir(ROOT);sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')];os.environ['RW_OFFSET_WRITER']='experiment'
    started=time.perf_counter()
    paths=[Path(__file__),Path(__file__).with_name('meter_response_trace2400.py'),BASE/'result.json',BASE/'hold_captured_response.pickle',CONFIG,RUN/'state_002400.json',RUN/'action_002250.json',RUN/'action_002250.csv',RUN/'action_002400.joint.json']
    paths+=list((ROOT/'evaluation/controllers').glob('*.py'))
    pins={str(p.relative_to(ROOT)):sha(p) for p in paths}
    report={'completed':False,'endpoint_calls':0,'new_endpoint_limit':1,'native_runs':0,'solver_runs':0,'price_fits':0,'source_sha256':pins,'ramp':MID}
    try:
        from diagnostics.probe_model_area_integration import build_projected
        from diagnostics.performance_diagnosis_20260913 import meter_response_trace2400 as trace
        from evaluation.controllers import vissim_stackelberg_adapter as a,area_follower_objective as area,physical_ramp_branches as ramps
        from evaluation.controllers.area_leader_objective import install_joint_price_field,shared_urban_quantities,shared_quantity_constraints
        from src.models.state import ControlAction,segment_vsl
        from src.models.demand import DemandStep
        from src.controllers import rollout_endpoint as ep
        base_receipt=json.loads((BASE/'result.json').read_text());assert base_receipt['completed'] and not base_receipt['source_changes']
        baseline=pickle.loads((BASE/'hold_captured_response.pickle').read_bytes())
        assert sha(BASE/'hold_captured_response.pickle')==base_receipt['arms']['hold']['raw_response_file_sha256']
        cfg,state,det,tuning,raw,mapping,metadata=build_projected(CONFIG,RUN/'state_002400.json',RUN/'action_002250.json',fixture_inputs=False)
        cal=a.deep_update(dict(a.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))),tuning.get('calibration_override',{}))
        forecast=a.demand_from_state(raw,cfg,DemandStep,3,cal,det)
        assert hashlib.sha256(pickle.dumps(forecast,protocol=5)).hexdigest()==base_receipt['forecast_sha256']
        follower=a.build_priced_wu_link_controller(cfg,tuning).nash_solver
        previous=a.control_from_json(RUN/'action_002250.json',cfg,ControlAction);previous,_=area.expand_shared_vsl_action(previous,cfg,segment_vsl_func=segment_vsl)
        hold=previous.copy();hold.N_P_star=2400.;hold.N_UF_star=2996.9313872526645
        field=json.loads((RUN/'action_002400.joint.json').read_text())['selected_price_field']
        nodes={s:n for s,n in cfg.network.signal_actuation_contract['nodes'].items() if n.get('native_clock_basis') is not None}
        assert json.dumps(field['context']['native_clock_nodes'],sort_keys=True)==json.dumps(nodes,sort_keys=True)
        field['context']['native_clock_nodes']=copy.deepcopy(nodes)
        install_joint_price_field(follower,hold,field,expected_owners=tuple(cfg.network.signals)+tuple(cfg.network.freeway_links),expected_context=field['context'],nuf_mode='equality')
        greens={r:hold.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps};greens[MID]=8.
        candidate=ramps.candidate_from_greens(hold,previous,cfg,greens)
        frozen=pickle.dumps((follower,state,previous,hold,candidate,forecast),protocol=5)
        report['frozen_inputs_sha256']=hashlib.sha256(frozen).hexdigest()
        report['input_generation_routes']={k:v for k,v in cfg.network.control_area_routes.items() if k.startswith('input:')}
        report['ramp_definition']=cfg.network.physical_ramp_branches['ramps'][MID]
        with area.shared_query_runtime_scope():
            point=ep.evaluate_price_point(state,candidate,forecast,(),ep.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
        report['endpoint_calls']=1
        assert not point.aborted and len(point.states)==3
        assert pickle.dumps((follower,state,previous,hold,candidate,forecast),protocol=5)==frozen
        capture=point.control_area_response;payload=pickle.dumps(capture,protocol=5)
        (OUT/'g8_captured_response.pickle').write_bytes(payload)
        report['raw_response_sha256']=hashlib.sha256(payload).hexdigest()
        trace.MID=MID # Analysis extractor's ramp selector only; no model/runtime mutation.
        report['g8']=trace.analyze_capture(point,cfg)
        q=shared_urban_quantities(follower,capture,start_sec=2400.,horizon_steps=3)
        report['quantity_constraints']=shared_quantity_constraints(follower,candidate,q,start_sec=2400.,horizon_steps=3,
            np_mode='cap',target_np_veh=2400.,np_tolerance_veh=1e-7,nuf_mode='equality',target_nuf_veh_h=hold.N_UF_star,nuf_tolerance_veh_h=40.)
        report['baseline_query_resource_rows']=[r for r in baseline['resource_allocations'] if r['resource']==MID and r['kind'].startswith(('ramp_release_query_','urban_meter_release_'))]
        report['same_captured_traffic']={'transfers_exact':baseline['transfers']==capture['transfers'],
            'residence_exact':baseline['residence']==capture['residence'],
            'all8_accepted_merge_time_series_exact':[r['actual_ramp_release_veh_h'] for r in baseline['freeway_frames']]==[r['actual_ramp_release_veh_h'] for r in capture['freeway_frames']],
            'all_freeway_density_time_series_exact':[r['freeway_density'] for r in baseline['freeway_frames']]==[r['freeway_density'] for r in capture['freeway_frames']],
            'all_model_stock_time_series_exact':[r['model_stock_veh'] for r in baseline['freeway_frames']]==[r['model_stock_veh'] for r in capture['freeway_frames']],
            'aggregate_control_area_exact':point.control_area==base_receipt['arms']['hold']['control_area']}
        report['initial_state_evidence_exact']=all(baseline['initial_freeway_operands'][k]==capture['initial_freeway_operands'][k] for k in baseline['initial_freeway_operands'] if k!='applied_control')
        report['completed']=report['initial_state_evidence_exact'] and all(report['same_captured_traffic'].values()) and report['quantity_constraints']['feasible']
        print(json.dumps({'same_traffic':report['same_captured_traffic'],'g8_binding':report['g8']['binding_counts'],'strict_request_binding_times':report['g8']['strict_request_binding_times']}),flush=True)
    except Exception:
        report['error']=traceback.format_exc();print(report['error'],flush=True)
    finally:
        report['source_changes']=[p for p,h in pins.items() if sha(ROOT/p)!=h];report['completed']=report['completed'] and not report['source_changes']
        report['wall_sec']=time.perf_counter()-started;(OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    return 0 if report['completed'] else 1


def main():
    if sys.argv[1:]==['--worker']:return worker()
    OUT.mkdir(exist_ok=False);started=time.perf_counter();receipt={'completed':False,'timeout_sec':120,'owned_child_only':True,'native_runs':0}
    try:
        with (OUT/'stdout.txt').open('xb') as out,(OUT/'stderr.txt').open('xb') as err:
            p=subprocess.run([sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'--worker'],cwd=ROOT,stdout=out,stderr=err,timeout=120)
        receipt.update(completed=p.returncode==0,exit_code=p.returncode)
    except subprocess.TimeoutExpired:receipt['error']='Owned offline child exceeded120s and was terminated.'
    finally:
        receipt['wall_sec']=time.perf_counter()-started;(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt),flush=True)
    return 0 if receipt['completed'] else 1


if __name__=='__main__':sys.exit(main())
