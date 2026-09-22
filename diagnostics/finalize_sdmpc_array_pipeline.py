"""Array pipeline qualification, iteration context and unchanged-default proof."""
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
    folder=ROOT/'diagnostics/sdmpc_array_pipeline_20260922'
    qualification=json.loads((folder/'qualification_summary.json').read_text())
    current=json.loads((folder/'full_decision_v1/result.json').read_text())
    baseline=json.loads((ROOT/'diagnostics/sdmpc_trial_20260922/full_decision_v1/result.json').read_text())
    old=pickle.loads((ROOT/'diagnostics/sdmpc_array_transport_20260922/states_v1/off_states.pickle').read_bytes())
    off=pickle.loads((folder/'states_v2/off_states.pickle').read_bytes())
    errors={k:state_error(old[k],off[k],fast_records=True,compact_records=True) for k in ('states','costs','resources')}
    coupling=json.loads((folder/'coupling_v4.json').read_text())
    jac=json.loads((folder/'pipeline_h3_v3/result.json').read_text())
    old_jac=json.loads((ROOT/'diagnostics/sdmpc_trial_20260922/trial_h3_v1/result.json').read_text())
    config=ROOT/'diagnostics/sdmpc_trial_20260922/config_candidate.json'
    expected='5c708fcff3cdda8abc33ee35a65d35613153f49fe233b745b9ba0ddeeb289fe4'
    checks=dict(whole_decision_qualified=qualification['pass_all'],default_historical_states_exact=max(errors.values())==0.,
        previous_selected_config_unchanged=hashlib.sha256(config.read_bytes()).hexdigest()==expected,
        regression_passed='Ran 136 tests' in (folder/'regression_v3.log').read_text() and '\nOK' in (folder/'regression_v3.log').read_text(),
        coupling_passed=len(coupling)==2 and all(r['tests']==9 and r['passed'] for r in coupling),
        parameters_passed='PASS' in (folder/'parameters_v1.log').read_text(encoding='utf-8'),
        array_derivative_pipeline_used=jac['array_urban_pipeline']['calls']==450,
        branch_events_and_axes_exact=all(jac['trace'][name]==old_jac['trace'][name]
            for name in ('event_counts','exact_tie_axes','discrete_dependent_axes')),
        original_reverse_node_count=jac['reverse_sweeps']['nodes']==14137087)
    result=dict(checks=checks,pass_all=all(checks.values()),default_errors=errors,
        before_sec=baseline['wall_sec'],after_sec=current['wall_sec'],
        reduction_percent=100*(1-current['wall_sec']/baseline['wall_sec']),
        selected_for_speed=False,
        iteration_context=current['iteration_context'],
        measurement='One full decision per implementation; historical baseline, not a statistical speed guarantee.',
        native_applied=False,comparison9000_completed=False,arrays=jac['array_urban_pipeline'],fifo_boundary=jac['persistent_urban_fifo'])
    paths=['AGENTS.md','docs/SDMPC_ARRAY_PIPELINE_20260922.md',
        'evaluation/controllers/physical_urban_transport.py','evaluation/controllers/sdmpc_prediction_cache.py',
        'evaluation/controllers/sdmpc.py','evaluation/controllers/sdmpc_tangent_worker.py',
        'evaluation/controllers/sdmpc_tangent_urban.py','evaluation/controllers/sdmpc_tangent_fifo.py',
        'evaluation/controllers/sdmpc_tangent_transport.py','evaluation/controllers/sdmpc_tangent_spatial.py',
        'diagnostics/test_sdmpc_array_pipeline.py','diagnostics/check_array_pipeline_coupling.py',
        'diagnostics/check_sdmpc_full_decision.py','diagnostics/check_sdmpc_reverse.py',
        'diagnostics/finalize_sdmpc_array_pipeline.py']
    manifest={}
    for name in paths:
        source=ROOT/name;target=folder/'final_sources'/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target);manifest[name]=hashlib.sha256(source.read_bytes()).hexdigest()
    result['sources']=manifest
    with (folder/'connection_summary.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(result,indent=2))
    return 0 if result['pass_all'] else 1


if __name__=='__main__':raise SystemExit(main())
