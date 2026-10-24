"""Same 17 physical commands in singleton/8-worker batches; no game or native run."""
import hashlib
import json
import os
from pathlib import Path
import pickle
import sys
import time
import traceback

D=Path(__file__).resolve().parent
ROOT=D.parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def main():
    label=sys.argv[1]
    if not label.replace('_','').isalnum():raise ValueError('Fresh result label required')
    target=D/(label+'.json')
    if target.exists():raise FileExistsError(target)
    os.chdir(ROOT);os.environ['RW_OFFSET_WRITER']='experiment'
    record=ROOT/'evaluation/runs/codex_native_clock_fw080_u050_open_v2/decisions_codex_native_clock_fw080_u050_open_v2'
    config=D/'joint_config_unlimited_v1.json'
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    digest=lambda v:hashlib.sha256(pickle.dumps(v,protocol=5)).hexdigest()
    paths=[Path(__file__),config,*sorted((ROOT/'evaluation/controllers').glob('*.py')),
        record/'state_000900.json',record/'action_000750.json',record/'action_000900.json',record/'action_000900.csv']
    pins={str(p):sha(p) for p in paths}
    report={'completed':False,'native_run':False,'source_sha256':pins,'arms':{},
        'scope':'Existing canonical response cache, 8 owned workers in both modes, identical 17 physical commands. ABBA scheduling diagnostic co-running with the independent unlimited game; not whole-controller or VISSIM speed qualification.'}
    started=time.perf_counter()
    try:
        from diagnostics.probe_model_area_integration import build_projected
        from evaluation.controllers import vissim_stackelberg_adapter as a, physical_ramp_branches as ramps
        from evaluation.controllers.area_follower_objective import make_decision_shared_query,expand_shared_vsl_action
        from src.models.state import ControlAction,segment_vsl
        from src.models.demand import DemandStep
        cfg,state,det,tuning,raw,mapping,meta=build_projected(config,record/'state_000900.json',record/'action_000750.json',fixture_inputs=False)
        cal=a.deep_update(dict(a.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))),tuning.get('calibration_override',{}))
        forecast=a.demand_from_state(raw,cfg,DemandStep,3,cal,det)
        anchor=a.control_from_json(record/'action_000900.json',cfg,ControlAction)
        anchor,report['vsl_expansion']=expand_shared_vsl_action(anchor,cfg,segment_vsl_func=segment_vsl)
        follower=a.build_priced_wu_link_controller(cfg,tuning).nash_solver
        greens={mid:anchor.diagnostics['rw_meter_green_'+mid] for mid in cfg.network.ramps}
        labels=['actual_open'];bank=[anchor]
        for green in (8.,9.):
            for mid in cfg.network.ramps:
                labels.append(mid+'_g'+str(int(green)))
                bank.append(ramps.candidate_from_greens(anchor,anchor,cfg,{**greens,mid:green}))
        fixed=digest((follower,state,anchor,forecast,bank))
        report['bank']={'labels':labels,'physical_commands':[ramps.physical_commands(c,cfg) for c in bank],
            'action_tokens':[digest(c) for c in bank],'forecast_sha256':digest(forecast)}
        bootstrap={'state_json':{'network_path':str(a._network_path_from_state(raw).resolve(strict=True))},
            'detector_mapping':det,'runtime_sources':pins}
        outputs={}
        report['setup_wall_sec']=time.perf_counter()-started
        for name,batch_mode in (('singleton_a',False),('batch_a',True),('batch_b',True),('singleton_b',False)):
            tick=time.perf_counter();row={'completed':False,'batch_mode':batch_mode}
            report['arms'][name]=row
            query=make_decision_shared_query(follower,state,anchor,forecast,horizon_steps=3,
                source_fingerprint=digest(pins),cache_enabled=True,parallel_workers=8,
                worker_bootstrap=bootstrap,deadline_monotonic=None,unlimited_time=True)
            try:
                baseline=query((bank[0],))['results']
                row['pool_and_baseline_wall_sec']=time.perf_counter()-tick
                query_start=time.perf_counter();before=query.stats()
                if batch_mode:
                    result=query(tuple(bank[1:]))['results']
                else:
                    result=[]
                    for control in bank[1:]:result.extend(query((control,))['results'])
                row['candidate_query_wall_sec']=time.perf_counter()-query_start
                after=query.stats()
                row['candidate_endpoint_calls']=after['endpoint_calls']-before['endpoint_calls']
                row['candidate_endpoint_cpu_sec']=after['endpoint_cpu_sec']-before['endpoint_cpu_sec']
                outputs[name]=baseline+result
                repeat=query(tuple(reversed(bank)))['results']
                assert repeat==list(reversed(outputs[name]))
                payload=pickle.dumps(outputs[name],protocol=5)
                output=D/(label+'_'+name+'.pickle')
                with output.open('xb') as stream:stream.write(payload)
                row.update(completed=True,results_sha256=hashlib.sha256(payload).hexdigest(),
                    result_file=str(output),repeat_values_exact=True)
            finally:
                query.close();row.update(stats=query.stats(),total_wall_sec=time.perf_counter()-tick)
            assert not row['stats']['owned_workers_alive']
            assert row['candidate_endpoint_calls']==16 and row['stats']['endpoint_calls']==17
            assert digest((follower,state,anchor,forecast,bank))==fixed
            assert outputs[name]==outputs['singleton_a']
            row['exact_all_result_values']=True
            print(json.dumps({'arm':name,'candidate_query_wall_sec':row['candidate_query_wall_sec'],
                'endpoint_calls':row['candidate_endpoint_calls'],'exact_values':True}),flush=True)
        report['exact_all_result_values']=True
        report['exact_result_pickle_sha256']=len({v['results_sha256'] for v in report['arms'].values()})==1
        report['completed']=True
    except Exception:
        report['error']=traceback.format_exc()
    finally:
        report.update(total_wall_sec=time.perf_counter()-started,
            source_changes=[p for p,h in pins.items() if sha(p)!=h])
        with target.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2,allow_nan=False)
    print(json.dumps({k:report.get(k) for k in ('completed','total_wall_sec','source_changes','error')}))
    return 0 if report['completed'] and not report['source_changes'] else 1


def _exact_tree(value):
    """Typed values, retaining float bits without depending on pickle aliases."""
    if value is None:
        return ('none',)
    if type(value) in (bool, int, str):
        return (type(value).__name__, value)
    if type(value) is float:
        return ('float', value.hex())
    if type(value) is bytes:
        return ('bytes', value.hex())
    if type(value) in (tuple, list):
        return (type(value).__name__, tuple(_exact_tree(v) for v in value))
    if type(value) is dict:
        pairs = [(_exact_tree(k), _exact_tree(v)) for k, v in value.items()]
        return ('dict', tuple(sorted(pairs, key=lambda row: repr(row[0]))))
    raise TypeError('Unqualified comparison type: '+type(value).__name__)


def game_main(label, max_evaluations=32):
    """Recorded fixed-game ABBA; common prices once, no native/end-to-end run."""
    import copy
    from contextlib import nullcontext
    from dataclasses import asdict
    from unittest.mock import patch
    if not label.replace('_', '').isalnum() or not 2 <= max_evaluations <= 64:
        raise ValueError('Fresh label and 2..64 fixed logical evaluations required')
    target = D/(label+'.json')
    if target.exists() or any(D.glob(label+'_*.pickle')):
        raise FileExistsError(label)
    os.chdir(ROOT)
    os.environ['RW_OFFSET_WRITER'] = 'experiment'
    record = ROOT/'evaluation/runs/codex_native_clock_fw080_u050_open_v2/decisions_codex_native_clock_fw080_u050_open_v2'
    config = D/'joint_config_fast_np_v2.json'
    sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    digest = lambda value: hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()
    paths = [Path(__file__), config, *sorted((ROOT/'evaluation/controllers').glob('*.py')),
        *sorted((ROOT/'vendor/NumSim-mine/src').rglob('*.py')),
        ROOT/'diagnostics/probe_model_area_integration.py',
        record/'state_000900.json', record/'action_000750.json',
        record/'action_000900.json', record/'action_000900.csv']
    pins = {str(path): sha(path) for path in paths}
    report = {'completed': False, 'native_run': False, 'source_sha256': pins,
        'arms': {}, 'max_logical_evaluations': max_evaluations, 'time_budget_sec': None,
        'final_check_reserve_sec': 0.,
        'scope': 'One recorded900 state, unchanged450s physics, one measured common price field. Fixed-evaluation singleton/bounded8 ABBA; no whole-decision, full-domain gap or native speed claim.',
        'scheduling_isolation': 'Legacy first/full prefetch off in both arms. One identical frozen cfg carries bounded8; only the local scheduling-options getter is forced off in singleton arms. No physical input or source code is patched.'}
    started = time.perf_counter()
    budget = None
    query = None
    try:
        from diagnostics.probe_model_area_integration import build_projected
        from evaluation.controllers import vissim_stackelberg_adapter as a
        from evaluation.controllers import area_follower_objective as area, area_runtime
        from evaluation.controllers import physical_ramp_branches as ramps, joint_owner_game as game
        from evaluation.controllers.area_leader_objective import validate_joint_leader_result
        from src.models.state import ControlAction, segment_vsl
        from src.models.demand import DemandStep
        cfg, state, det, tuning, raw, mapping, _ = build_projected(
            config, record/'state_000900.json', record/'action_000750.json', fixture_inputs=False)
        if getattr(cfg.network, 'offramp_route_inventory', None) is not None:
            raise ValueError('Speed isolation requires base physics with passive route inventory OFF')
        cal = a.deep_update(dict(a.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))), tuning.get('calibration_override', {}))
        forecast = a.demand_from_state(raw, cfg, DemandStep, 3, cal, det)
        historical = a.control_from_json(record/'action_000900.json', cfg, ControlAction)
        historical, report['vsl_expansion'] = area.expand_shared_vsl_action(historical, cfg, segment_vsl_func=segment_vsl)
        controller = a.build_priced_wu_link_controller(cfg, tuning)
        options = a.joint_owner_game_settings(tuning, cfg, 'wu-link')
        budget = area.DecisionBudget(options['decision_time_budget_sec'],
            reserve_sec=options['finalization_reserve_sec'], unlimited_time=True)
        bootstrap = {'state_json': {'network_path': str(a._network_path_from_state(raw).resolve(strict=True))},
            'detector_mapping': det, 'runtime_sources': pins}
        domain = area.prepare_joint_leader_candidates(controller, state, forecast, historical,
            budget_tolerance_veh_h=options['nuf_tolerance_veh_h'])
        proposals = domain['candidates']
        max_np = max(row['target_np_veh'] for row in proposals)
        proposal = next(row for row in proposals if row['target_np_veh'] == max_np and row['meter_bank_index'] == 0)
        price_started = time.perf_counter()
        common = area.prepare_common_joint_prices(controller, state, forecast, historical, mapping,
            runtime_sources=pins, options=options, budget=budget, worker_bootstrap=bootstrap)
        common['response_query'].close()
        report['common_prices'] = {'wall_sec': time.perf_counter()-price_started,
            'measurements': 1, 'field_sha256': digest(common['measured']['field']),
            'query_stats': common['response_query'].stats()}
        if report['common_prices']['query_stats']['owned_workers_alive']:
            raise ValueError('Common-price workers must close before ABBA')
        follower, reference = common['follower'], common['reference']
        follower.cfg.network.control_area_prefetch_first_owner_responses = False
        follower.cfg.network.control_area_prefetch_complete_sweep_responses = False
        follower.cfg.network.control_area_response_scheduling = {'lookahead': 8, 'final_check_reserve_sec': 0.}
        initial = copy.deepcopy(proposal['control'])
        initial.N_UF_star = common['nuf_initialization']['target_veh_h']
        initial = ramps.prepare_control(initial, follower.cfg)
        target_np, target_nuf = initial.N_P_star, initial.N_UF_star
        policy = {'leader_present': True, 'np_mode': 'cap', 'nuf_mode': 'equality',
            'inactive_price_addresses': dict.fromkeys(('phase', 'offset', 'vsl', 'meter'), ())}
        fields = ('N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times', 'offsets', 'inflow_outflow_allocation')
        fixed = digest((follower, state, reference, forecast, historical, initial, mapping, policy))
        report['fixed_inputs'] = {'sha256': fixed, 'state_sha256': digest(state),
            'forecast_sha256': digest(forecast), 'initial_action_sha256': digest(initial),
            'np_cap': target_np, 'nuf_target': target_nuf,
            'declared_leader_domain_sha256': digest(domain), 'declared_leader_domain_count': len(proposals)}
        baseline = None
        with area.shared_query_runtime_scope():
            a._PHASE_VECTOR_FOLLOWER['ref'] = follower
            callbacks, context, fingerprint = area._joint_runtime_callbacks(follower, state, forecast,
                historical, initial, mapping, pins, reference=reference, total_budget=None,
                directional={}, tolerance=options['nuf_tolerance_veh_h'])
            context_token = fingerprint(context)
            report['fixed_inputs']['callback_context_token'] = context_token
            report['setup_wall_sec'] = time.perf_counter()-started
            original_solve = game.solve
            for name, batch_mode in (('singleton_a', False), ('batch_a', True), ('batch_b', True), ('singleton_b', False)):
                row = {'completed': False, 'batch_mode': batch_mode}
                report['arms'][name] = row
                tick = time.perf_counter()
                query = area.make_decision_shared_query(follower, state, reference, forecast,
                    horizon_steps=3, source_fingerprint=digest(pins), cache_enabled=True,
                    parallel_workers=8, worker_bootstrap=bootstrap,
                    deadline_monotonic=None, unlimited_time=True)
                responses, trace = {}, []
                def observed_query(actions):
                    result = query(actions)
                    for item in result['results']:
                        key = item['action_token']
                        encoded = _exact_tree(item)
                        if key in responses and _exact_tree(responses[key]) != encoded:
                            raise ValueError('Repeated exact action produced different physical response values')
                        responses[key] = copy.deepcopy(item)
                    return result
                observed_query.stats = query.stats
                def traced_solve(*args, **kwargs):
                    evaluate = kwargs['evaluate']
                    def observed_evaluate(owner, action, supplied):
                        token = digest(action)
                        result = evaluate(owner, action, supplied)
                        trace.append({'owner': owner, 'action_token': token, 'evaluation': asdict(result)})
                        return result
                    kwargs['evaluate'] = observed_evaluate
                    return original_solve(*args, **kwargs)
                try:
                    observed_query((initial,))
                    row['pool_and_initial_response_wall_sec'] = time.perf_counter()-tick
                    before = query.stats()
                    game_started = time.perf_counter()
                    gate = nullcontext() if batch_mode else patch.object(area_runtime, 'response_scheduling_options', return_value=None)
                    with gate, patch.object(game, 'solve', traced_solve):
                        solved = area.solve_fixed_shared_game(follower, state, reference, forecast, initial,
                            callbacks=callbacks, context=context, context_fingerprint=fingerprint,
                            horizon_steps=3, lambda_p=follower._lambda_P, lambda_uf=follower._lambda_UF,
                            target_np_veh=target_np, target_nuf_veh_h=target_nuf, price_context=policy,
                            max_sweeps=1, max_evaluations=max_evaluations, time_budget_sec=None,
                            improvement_tolerance=options['improvement_tolerance'], shared_tolerance=options['shared_tolerance'],
                            scope_label='Recorded900 scheduling ABBA, fixed evaluation count',
                            np_tolerance_veh=options['np_tolerance_veh'], nuf_tolerance_veh_h=options['nuf_tolerance_veh_h'],
                            traversal=options['traversal'], response_query=observed_query,
                            restore_initializer=False)
                    row['game_wall_sec'] = time.perf_counter()-game_started
                    after = query.stats()
                    validate_joint_leader_result(solved, target_np_veh=target_np, target_nuf_veh_h=target_nuf, cfg=follower.cfg)
                    if solved['game']['evaluations'] != max_evaluations or len(trace) != max_evaluations:
                        raise ValueError('Qualification did not consume the same fixed logical work')
                    semantic_game = {key: value for key, value in solved['game'].items()
                        if key not in ('control', 'elapsed_sec')}
                    comparison = {'logical_evaluation_trace': trace, 'game': semantic_game,
                        'final_score': solved['final_score'], 'command_evidence': solved['command_evidence'],
                        'seven_final_fields': {key: getattr(solved['game']['control'], key) for key in fields},
                        'full_final_action_token': solved['final_action_token'],
                        'physical_responses': responses, 'price_field': common['measured']['field']}
                    exact = _exact_tree(comparison)
                    output = D/(label+'_'+name+'.pickle')
                    with output.open('xb') as stream:
                        pickle.dump({'result': solved, 'comparison': comparison}, stream, protocol=5)
                    row.update(result_file=str(output), result_file_sha256=sha(output),
                        exact_values_sha256=digest(exact), logical_reads=len(trace),
                        actual_endpoint_calls=after['endpoint_calls'],
                        game_endpoint_calls=after['endpoint_calls']-before['endpoint_calls'],
                        game_query_wall_sec=after['query_wall_sec']-before['query_wall_sec'],
                        physical_response_tokens={key: value['response_token'] for key, value in responses.items()},
                        scheduling=solved['queries'].get('bounded_response_schedule'),
                        seven_final_fields_sha256=digest(_exact_tree(comparison['seven_final_fields'])),
                        error=solved['game']['error'], final_check_complete=solved['game']['final_check_complete'])
                    if baseline is None:
                        baseline = exact
                    if exact != baseline:
                        raise ValueError('ABBA logical/physical/price/action/gap exact equivalence failed')
                    if digest((follower, state, reference, forecast, historical, initial, mapping, policy)) != fixed or fingerprint(context) != context_token:
                        raise ValueError('Fixed ABBA input or callback context changed')
                    row.update(completed=True, exact_values=True)
                finally:
                    query.close()
                    row.update(query_stats=query.stats(), total_wall_sec=time.perf_counter()-tick)
                    query = None
                if row['query_stats']['owned_workers_alive']:
                    raise ValueError('Owned workers survived an ABBA arm')
                print(json.dumps({'arm': name, 'game_wall_sec': row['game_wall_sec'],
                    'actual_endpoint_calls': row['actual_endpoint_calls'], 'logical_reads': row['logical_reads'], 'exact_values': True}), flush=True)
        report['completed'] = True
        report['exact_all_response_action_price_gap_values'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        if query is not None:
            query.close()
        if budget is not None and hasattr(budget, 'response_query'):
            budget.response_query.close()
        report.update(wall_sec=time.perf_counter()-started,
            source_changes=[path for path, token in pins.items() if sha(path) != token])
        with target.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps({key: report.get(key) for key in ('completed', 'wall_sec', 'source_changes', 'error')}))
    return 0 if report['completed'] and not report['source_changes'] else 1


if __name__ == '__main__':
    if '--game' in sys.argv[1:]:
        import argparse
        parser = argparse.ArgumentParser(description='Bounded recorded900 fixed-game ABBA; runs model endpoints only when invoked.')
        parser.add_argument('label')
        parser.add_argument('--game', action='store_true')
        parser.add_argument('--max-evaluations', type=int, default=32)
        args = parser.parse_args()
        raise SystemExit(game_main(args.label, args.max_evaluations))
    raise SystemExit(main())

