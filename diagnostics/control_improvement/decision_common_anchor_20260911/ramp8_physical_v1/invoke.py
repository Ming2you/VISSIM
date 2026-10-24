"""Same recorded80/50 state and native commands; bounded physical branch audit."""
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import pickle
import sys
import time
import traceback

D = Path(__file__).resolve().parent
ROOT = D.parents[3]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
os.chdir(ROOT)
os.environ['RW_OFFSET_WRITER'] = 'experiment'


def ttd_by_windows(transfers):
    """Summarize recorded accepted exits; never infer exits from total service."""
    windows = [{'start_sec': start, 'end_sec': start+150., 'by_route': {}}
               for start in (900., 1050., 1200.)]
    total = {}
    for row in transfers:
        count = row['ttd_veh']
        if type(count) not in (int, float) or not math.isfinite(count) or count < 0:
            raise ValueError('Recorded TTD must be finite and nonnegative')
        if count == 0:
            continue
        start, end = row['start_sec'], row['end_sec']
        window = next((w for w in windows if end <= w['end_sec']), None)
        if (window is None or not math.isfinite(start) or not math.isfinite(end)
                or not window['start_sec'] <= start <= end):
            raise ValueError('Recorded TTD transfer is outside or straddles a 150s window')
        key = str(row['route_key'])
        window['by_route'][key] = window['by_route'].get(key, 0.) + count
        total[key] = total.get(key, 0.) + count
    return total, windows


def main():
    label = sys.argv[1]
    arguments=sys.argv[2:]
    candidate_json=None
    config_override=None
    if '--config' in arguments:
        i=arguments.index('--config');config_override=Path(arguments[i+1]).name
        if not (D/config_override).is_file():raise FileNotFoundError(config_override)
        arguments=arguments[:i]+arguments[i+2:]
    if '--candidate-json' in arguments:
        i=arguments.index('--candidate-json')
        candidate_json=Path(arguments[i+1]).resolve(strict=True)
        arguments=arguments[:i]+arguments[i+2:]
    packed_parallel='--packed-parallel' in arguments
    if packed_parallel:arguments.remove('--packed-parallel')
    packed_parity='--packed-parity' in arguments
    if packed_parity:arguments.remove('--packed-parity')
    response_diff='--response-diff' in arguments
    if response_diff:arguments.remove('--response-diff')
    config_name='config.json';topology_name='topology.json'
    if arguments and arguments[0]=='--routes-v2':
        config_name='config_routes_v2.json';topology_name='topology_routes_v2.json';arguments=arguments[1:]
    if arguments and arguments[0]=='--routes-v3':
        config_name='config_routes_v3.json';topology_name='topology_routes_v2.json';arguments=arguments[1:]
    if config_override is not None:config_name=config_override
    if not label.replace('_','').isalnum():
        raise ValueError('Explicit fresh local result label required')
    target = D/(label+'.json')
    if target.exists():
        raise FileExistsError(target)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    b = ROOT/'evaluation/runs/codex_native_clock_fw080_u050_open_v2/decisions_codex_native_clock_fw080_u050_open_v2'
    paths = [Path(__file__), D/config_name,D/topology_name, b/'state_000900.json',b/'action_000750.json',b/'action_000900.json',b/'action_000900.csv']
    paths += list((ROOT/'evaluation/controllers').glob('*.py'))
    if candidate_json is not None:paths.append(candidate_json)
    pins = {str(p.relative_to(ROOT)):sha(p) for p in paths}
    report = {'complete':False,'native_run':False,'source_sha256':pins,'arms':{},
        'scope':'Explicit8reservoir model migration; same recorded900state/450s forecast. Native evidence reused only for exactly matched commands. Not a controller optimization.'}
    started = time.perf_counter()
    try:
        from diagnostics.probe_model_area_integration import build_projected
        from evaluation.controllers import vissim_stackelberg_adapter as a, physical_ramp_branches as ramps, area_runtime
        from src.models.state import ControlAction
        from src.models.demand import DemandStep
        from src.controllers import rollout_endpoint as ep
        from src.controllers.priced_wu_link_controller import LinkAgentWuFollower
        from evaluation.controllers import area_follower_objective, area_leader_objective
        cfg,state,det,tuning,raw,mapping,meta=build_projected(D/config_name,b/'state_000900.json',b/'action_000750.json',fixture_inputs=False)
        cal=a.deep_update(dict(a.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))),tuning.get('calibration_override',{}))
        forecast=a.demand_from_state(raw,cfg,DemandStep,3,cal,det)
        anchor=a.control_from_json(b/'action_000900.json',cfg,ControlAction)
        if packed_parallel:
            from diagnostics.check_fixed_candidate_response import compare_decision_cache
            from src.models.state import segment_vsl
            anchor,report['vsl_expansion']=area_follower_objective.expand_shared_vsl_action(anchor,cfg,segment_vsl_func=segment_vsl)
            cfg.network.control_area_pack_completed_response_records=True
            bootstrap={'state_json':{'network_path':str(a._network_path_from_state(raw).resolve(strict=True))},
                'detector_mapping':det,'runtime_sources':{str((ROOT/name).resolve(strict=True)):value for name,value in pins.items()}}
            compare_decision_cache(state,anchor,forecast,cfg,tuning,report,parallel_workers=1,worker_bootstrap=bootstrap,deadline_sec=120.,compact_results_dir=target.with_suffix('.compact'))
            report['complete']=True
            return
        follower=LinkAgentWuFollower(cfg)
        report['initial_ramp_stocks']=dict(state.ramp_queue)
        report['initial_inventory']=area_runtime.model_inventory(state,cfg)
        report['branches']=cfg.network.physical_ramp_branches
        report['forecast_sha256']=hashlib.sha256(pickle.dumps(forecast,protocol=5)).hexdigest()
        written={row['id']:row for row in csv.DictReader((b/'action_000900.csv').open(encoding='utf-8-sig',newline='')) if row['kind']=='ramp_meter'}
        reference_commands=ramps.physical_commands(anchor,cfg)
        for mid,row in reference_commands.items():
            assert row['green_sec']==float(written[mid]['green_sec']) and row['rate_vph']==float(written[mid]['rate_vph']) and row['sc_no']==float(written[mid]['sc_no'])
        report['native_reference_meter_commands_exact']=True
        initial=pickle.dumps((cfg,state,anchor,forecast),protocol=5)
        greens={mid:anchor.diagnostics['rw_meter_green_'+mid] for mid in cfg.network.ramps}
        controls={'open':anchor}
        for mid in cfg.network.ramps:
            controls[mid+'_g8']=ramps.candidate_from_greens(anchor,anchor,cfg,{**greens,mid:8.})
        controls['fw_w_pair_g8']=ramps.candidate_from_greens(anchor,anchor,cfg,{**greens,'RM_C10646':8.,'RM_C10644':8.})
        if candidate_json is not None:controls['selected']=a.control_from_json(candidate_json,cfg,ControlAction)
        if arguments:
            selected = arguments
            if len(selected) != len(set(selected)) or not set(selected) <= set(controls):
                raise ValueError('Unknown/duplicate requested audit arm')
            controls = {name:controls[name] for name in selected}
        fixed_test_target=None
        captured_responses=[]
        if response_diff and tuple(controls)!=('open','selected'):
            raise ValueError('Response comparison requires exactly open and selected arms')
        for name,control in controls.items():
            t=time.perf_counter()
            with area_follower_objective.shared_query_runtime_scope():
                point=ep.evaluate_price_point(state,control,forecast,(),ep.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
            response=point.control_area_response
            if response_diff:captured_responses.append(response)
            assert not point.aborted and len(point.states)==3
            assert response['model_constraint_coverage']['complete']
            assert pickle.dumps((cfg,state,anchor,forecast),protocol=5)==initial
            quantity=point.control_area['predicted_ramp_merge']
            with area_follower_objective.shared_query_runtime_scope():
                local=area_follower_objective.score_shared_owner_point(follower,point,state,control,anchor,horizon_steps=3)
            if packed_parity:
                from diagnostics.check_fixed_candidate_response import _full_response_value_diff
                from evaluation.controllers.control_area_objective import get_ledger
                cfg.network.control_area_pack_completed_response_records=True
                guarded=pickle.dumps((cfg,state,anchor,forecast),protocol=5)
                packed_start=time.perf_counter()
                with area_follower_objective.shared_query_runtime_scope():
                    packed=ep.evaluate_price_point(state,control,forecast,(),ep.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
                packed_elapsed=time.perf_counter()-packed_start
                packed_local=area_follower_objective.score_shared_owner_point(follower,packed,state,control,anchor,horizon_steps=3)
                assert pickle.dumps((cfg,state,anchor,forecast),protocol=5)==guarded
                del cfg.network.control_area_pack_completed_response_records
                comparison=_full_response_value_diff(response,packed.control_area_response)
                physical_states_exact=all(pickle.dumps({k:v for k,v in vars(x).items() if k!='_control_area_ledger'},protocol=5)==pickle.dumps({k:v for k,v in vars(y).items() if k!='_control_area_ledger'},protocol=5) for x,y in zip(point.states,packed.states)) and len(point.states)==len(packed.states)
                ledger_states_exact=all(pickle.dumps({k:v for k,v in vars(get_ledger(x)).items() if k not in ('_response','_packed_response_records')},protocol=5)==pickle.dumps({k:v for k,v in vars(get_ledger(y)).items() if k not in ('_response','_packed_response_records')},protocol=5) for x,y in zip(point.states,packed.states))
                score_exact=pickle.dumps((point.objective,local,point.control_area),protocol=5)==pickle.dumps((packed.objective,packed_local,packed.control_area),protocol=5)
                parity={'full_response_comparison':comparison,'physical_state_bytes_exact':physical_states_exact,'ledger_dynamic_state_bytes_exact':ledger_states_exact,'objective_all_owner_scores_and_area_bytes_exact':score_exact,'packed_endpoint_sec':packed_elapsed,'reference_elapsed_before_comparison_sec':packed_start-t}
                report.setdefault('packed_parity',{})[name]=parity
                assert physical_states_exact and ledger_states_exact and score_exact and comparison['all_typed_values_exact'] and not comparison['first_dict_order_differences'] and len(set(comparison['mutable_alias_graph_sha256']))==1
            local_quantities=area_leader_objective.shared_urban_quantities(follower,response,start_sec=900.,horizon_steps=3)
            if fixed_test_target is None:
                if name != 'open':
                    raise ValueError('Quantity check benchmark requires unchanged open reference first')
                fixed_test_target=quantity['total_rate_veh_h']
            constraints=area_leader_objective.shared_quantity_constraints(follower,control,local_quantities,
                start_sec=900.,horizon_steps=3,np_mode='cap',target_np_veh=2400.,np_tolerance_veh=1e-7,
                nuf_mode='equality',target_nuf_veh_h=fixed_test_target,nuf_tolerance_veh_h=1e-7)
            first_response={'freeway_frames':[r for r in response['freeway_frames'] if r['end_sec']<=1050.]}
            from evaluation.controllers.control_area_objective import get_ledger
            all_td,td_windows=ttd_by_windows(response['transfers'])
            first_td=td_windows[0]['by_route']
            assert math.isclose(math.fsum(all_td.values()),point.control_area['ttd_veh'],rel_tol=0.,abs_tol=1e-8)
            item={'elapsed_sec':time.perf_counter()-t,'objective_veh_h':point.objective,
                'area_150':vars(get_ledger(point.states[0]).metrics),'ttd_150_by_route':first_td,
                'ttd_450_by_route':all_td,'ttd_150_windows':td_windows,
                'local_base_costs':{owner:row['cost'] for owner,row in local.items()},
                'fixed_benchmark_quantity_constraints':constraints,
                'quantity_target_scope':'Open held response is this benchmark fixed target, not an optimized leader target; candidate target is not moved.',
                'predicted_merge_450':quantity,'predicted_merge_150':ramps.predicted_merge_quantity(first_response,cfg,start_sec=900.,end_sec=1050.),
                'physical_commands':ramps.physical_commands(control,cfg),'closing_ramp_stock':dict(point.states[-1].ramp_queue),
                'response_sha256':hashlib.sha256(pickle.dumps(response,protocol=5)).hexdigest(),
                'model_coverage':response['model_constraint_coverage'], 'area':point.control_area,
                'ramp_frames':[{'start_sec':r['start_sec'],'end_sec':r['end_sec'],'flows_veh_h':r['actual_ramp_release_veh_h'],
                    'stock_veh':{mid:r['model_stock_veh']['ramp:'+mid] for mid in cfg.network.ramps}} for r in response['freeway_frames']]}
            report['arms'][name]=item
            print(name,round(item['elapsed_sec'],3),'NUF',round(quantity['total_rate_veh_h'],3),flush=True)
        if response_diff:
            from diagnostics.check_fixed_candidate_response import _full_response_value_diff
            assert all(hashlib.sha256(pickle.dumps(value,protocol=5)).hexdigest()==report['arms'][name]['response_sha256']
                       for name,value in zip(controls,captured_responses))
            report['response_comparison']=_full_response_value_diff(*captured_responses)
            def non_target_view(response):
                def frame(value):
                    return {**value,'applied_control':{k:v for k,v in value['applied_control'].items()
                                                       if k not in ('N_P_star','N_UF_star')}}
                return {**response,'initial_freeway_operands':frame(response['initial_freeway_operands']),
                        'freeway_frames':[frame(value) for value in response['freeway_frames']]}
            report['response_non_target_comparison']={
                'excluded_only':'N_P_star and N_UF_star in each initial/frame applied_control; diagnostic view only, raw responses retained unchanged',
                'excluded_values_per_response':2*(1+len(captured_responses[0]['freeway_frames'])),
                'comparison':_full_response_value_diff(*(non_target_view(r) for r in captured_responses))}
            assert all(hashlib.sha256(pickle.dumps(value,protocol=5)).hexdigest()==report['arms'][name]['response_sha256']
                       for name,value in zip(controls,captured_responses))
        report['complete']=True
    except Exception:
        report['error']=traceback.format_exc()
        print(report['error'],flush=True)
    finally:
        report['source_changes']=[key for key,value in pins.items() if sha(ROOT/key)!=value]
        report['complete']=report['complete'] and not report['source_changes']
        report['elapsed_sec']=time.perf_counter()-started
        with target.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    sys.exit(0 if report['complete'] else 1)

if __name__ == '__main__':
    main()
