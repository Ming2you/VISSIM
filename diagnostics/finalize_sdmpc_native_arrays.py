"""Evidence for persistent urban arrays, with explicit optimization iterations."""
from pathlib import Path
import hashlib
import json
import pickle
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers.sdmpc_tangent_state import state_error


def main():
    folder=ROOT/'diagnostics/sdmpc_native_arrays_20260922'
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    qualification=read(folder/'qualification_summary.json')
    current=read(folder/'full_decision_v1/result.json')
    baseline=read(ROOT/'diagnostics/sdmpc_trial_20260922/full_decision_v1/result.json')
    intermediate=read(ROOT/'diagnostics/sdmpc_array_pipeline_20260922/full_decision_v1/result.json')
    jac=read(folder/'native_h3_v2/result.json')
    old_jac=read(ROOT/'diagnostics/sdmpc_trial_20260922/trial_h3_v1/result.json')
    old=pickle.loads((ROOT/'diagnostics/sdmpc_array_transport_20260922/states_v1/off_states.pickle').read_bytes())
    off=pickle.loads((folder/'states_v1/off_states.pickle').read_bytes())
    errors={k:state_error(old[k],off[k],fast_records=True,compact_records=True) for k in ('states','costs','resources')}
    coupling=read(folder/'coupling_v2.json')
    config=ROOT/'diagnostics/sdmpc_trial_20260922/config_candidate.json'
    expected='5c708fcff3cdda8abc33ee35a65d35613153f49fe233b745b9ba0ddeeb289fe4'
    regression=(folder/'regression_v2.log').read_text()
    checks=dict(whole_decision_qualified=qualification['pass_all'],default_historical_states_exact=max(errors.values())==0.,
        previous_selected_config_unchanged=hashlib.sha256(config.read_bytes()).hexdigest()==expected,
        regression_passed='Ran 136 tests' in regression and '\nOK' in regression,
        coupling_passed=len(coupling)==2 and all(r['tests']==9 and r['passed'] for r in coupling),
        parameters_passed='PASS' in (folder/'parameters_v1.log').read_text(encoding='utf-8'),
        all_450_steps_use_compiled_body=jac['array_urban_pipeline']['calls']==450,
        native_state_retained=jac['native_urban_store']['native_reuses']==449,
        cells_imported_once=jac['native_urban_store']['cell_imports']==40,
        counters_not_reimported_each_step=jac['native_urban_store']['counter_imports']==4,
        branch_events_and_axes_exact=all(jac['trace'][name]==old_jac['trace'][name]
            for name in ('operations','event_counts','exact_tie_axes','discrete_dependent_axes')))
    result=dict(checks=checks,pass_all=all(checks.values()),default_errors=errors,
        fastest_previous_sec=baseline['wall_sec'],initial_pipeline_sec=intermediate['wall_sec'],current_sec=current['wall_sec'],
        change_from_fastest_percent=100*(current['wall_sec']/baseline['wall_sec']-1),
        change_from_initial_pipeline_percent=100*(current['wall_sec']/intermediate['wall_sec']-1),
        iteration_context=current['iteration_context'],selected_for_speed=False,
        timing_scope='Single whole-decision measurements; selected candidate accepts two outer iterations, convergence unverified.',
        native_applied=False,comparison9000_completed=False,arrays=jac['array_urban_pipeline'],store=jac['native_urban_store'])
    paths=['AGENTS.md','docs/SDMPC_NATIVE_ARRAYS_20260922.md',
        'evaluation/controllers/physical_urban_transport.py','evaluation/controllers/sdmpc_prediction_cache.py',
        'evaluation/controllers/sdmpc.py','evaluation/controllers/sdmpc_tangent_worker.py',
        'evaluation/controllers/sdmpc_tangent_urban.py','evaluation/controllers/sdmpc_tangent_urban_store.py',
        'evaluation/controllers/sdmpc_tangent_fifo.py','evaluation/controllers/sdmpc_tangent_transport.py',
        'evaluation/controllers/sdmpc_tangent_spatial.py','diagnostics/test_sdmpc_array_pipeline.py',
        'diagnostics/check_array_pipeline_coupling.py','diagnostics/check_sdmpc_full_decision.py',
        'diagnostics/check_sdmpc_reverse.py','diagnostics/finalize_sdmpc_native_arrays.py']
    manifest={}
    for name in paths:
        source=ROOT/name;target=folder/'final_sources'/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target);manifest[name]=hashlib.sha256(source.read_bytes()).hexdigest()
    result['sources']=manifest
    with (folder/'connection_summary.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k!='sources'},indent=2))
    return 0 if result['pass_all'] else 1


if __name__=='__main__':raise SystemExit(main())
