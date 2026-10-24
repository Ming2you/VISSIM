"""Bounded actual recorded-state qualification of pending canonical functions."""
import hashlib
import json
import os
from pathlib import Path
import pickle
import sys
import time
import traceback

from qualify_fast_np import D, ROOT, install_pending


def main():
    label = sys.argv[1]
    if not label.replace('_','').isalnum(): raise ValueError('Fresh label required')
    target = D/(label+'.json')
    if target.exists(): raise FileExistsError(target)
    os.chdir(ROOT); os.environ['RW_OFFSET_WRITER'] = 'experiment'
    pins = install_pending()
    report = {'completed':False, 'native_run':False, 'source_sha256':pins,
        'scope':'Original 900s observed destination queues and 450s forecast; pending canonical functions in memory. Network, demand, model, targets, and actual-command box unchanged. Co-running with valid older decision; not a matched whole-decision speed benchmark.'}
    started = time.perf_counter()
    budget = None
    try:
        from diagnostics.probe_model_area_integration import build_projected
        from evaluation.controllers import vissim_stackelberg_adapter as a, area_follower_objective as area
        from src.models.state import ControlAction, segment_vsl
        from src.models.demand import DemandStep
        record = ROOT/'evaluation/runs/codex_native_clock_fw080_u050_open_v2/decisions_codex_native_clock_fw080_u050_open_v2'
        config = D/'joint_config_fast_np_v2.json'
        for path in [Path(__file__), D/'qualify_fast_np.py', config, record/'state_000900.json', record/'action_000750.json', record/'action_000900.json', record/'action_000900.csv']:
            pins[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        cfg,state,det,tuning,raw,mapping,_ = build_projected(config,record/'state_000900.json',record/'action_000750.json',fixture_inputs=False)
        cal = a.deep_update(dict(a.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))),tuning.get('calibration_override',{}))
        forecast = a.demand_from_state(raw,cfg,DemandStep,3,cal,det)
        historical = a.control_from_json(record/'action_000900.json',cfg,ControlAction)
        historical,_ = area.expand_shared_vsl_action(historical,cfg,segment_vsl_func=segment_vsl)
        controller = a.build_priced_wu_link_controller(cfg,tuning)
        options = a.joint_owner_game_settings(tuning,cfg,'wu-link')
        budget = area.DecisionBudget(options['decision_time_budget_sec'], reserve_sec=options['finalization_reserve_sec'], unlimited_time=True)
        bootstrap = {'state_json':{'network_path':str(a._network_path_from_state(raw).resolve(strict=True))},
            'detector_mapping':det,'runtime_sources':pins}
        report['setup_wall_sec'] = time.perf_counter()-started
        def progress(event):
            event = {'elapsed_sec':time.perf_counter()-started, **event}
            with (D/(label+'.progress.jsonl')).open('a',encoding='utf-8') as stream:
                stream.write(json.dumps(event,default=str)+'\n')
            if event['stage'] in ('joint_leader_candidate_start','joint_price_endpoints','actual_hold_validated'):
                print(json.dumps(event,default=str),flush=True)
        solved = area.solve_runtime_joint_leader(controller,state,forecast,historical,mapping,
            runtime_sources=pins,options=options,progress=progress,budget=budget,worker_bootstrap=bootstrap)
        payload = pickle.dumps(solved,protocol=5)
        (D/(label+'.pickle')).write_bytes(payload)
        report['result_pickle_sha256'] = hashlib.sha256(payload).hexdigest()
        report['result_keys'] = list(solved)
        # Keep the full native Python result for exact action/response validation;
        # only the compact leader receipt is duplicated as human-readable JSON.
        for key in ('metadata','selection','leader_selection'):
            if key in solved: report[key] = solved[key]
        report['completed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        if budget is not None and hasattr(budget,'response_query'):
            budget.response_query.close()
            report['query_stats'] = budget.response_query.stats()
        report['source_changes'] = [p for p,h in pins.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
        report['wall_sec'] = time.perf_counter()-started
        target.write_text(json.dumps(report,indent=2,default=str)+'\n',encoding='utf-8')
    print(json.dumps({k:report.get(k) for k in ('completed','wall_sec','source_changes','error','result_keys')}))
    return 0 if report['completed'] and not report['source_changes'] else 1


if __name__ == '__main__': sys.exit(main())
