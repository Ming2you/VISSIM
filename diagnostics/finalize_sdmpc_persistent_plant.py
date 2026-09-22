"""Qualify the actual plant connection separately from any speed selection."""
from pathlib import Path
import hashlib
import json
import pickle
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def main():
    from evaluation.controllers.sdmpc_tangent_state import state_error
    folder=ROOT/'diagnostics/sdmpc_persistent_plant_20260922'
    def read(path):return json.loads(path.read_text(encoding='utf-8'))
    full=read(folder/'qualification_summary.json')
    new=read(folder/'persistent_h3_v2/result.json')
    old=read(ROOT/'diagnostics/sdmpc_trial_20260922/trial_h3_v1/result.json')
    old_states=pickle.loads((ROOT/'diagnostics/sdmpc_array_transport_20260922/states_v1/off_states.pickle').read_bytes())
    new_states=pickle.loads((folder/'states_v1/off_states.pickle').read_bytes())
    errors={k:state_error(old_states[k],new_states[k],fast_records=True,compact_records=True)
            for k in ('states','costs','resources')}
    coupled=read(folder/'coupling_v1.json')
    config_before=read(ROOT/'diagnostics/sdmpc_trial_20260922/config_candidate.json')
    config_after=read(folder/'config_candidate.json')
    flag=config_after['adapter'].pop('sdmpc_persistent_urban_fifo')
    checks=dict(full_decision_equivalent=full['pass_all'],default_matches_historical_states=all(v==0. for v in errors.values()),
        same_node_count=old['reverse_sweeps']['nodes']==new['reverse_sweeps']['nodes'],
        same_branch_counts=old['trace']['event_counts']==new['trace']['event_counts'],
        same_tie_axes=old['trace']['exact_tie_axes']==new['trace']['exact_tie_axes'],
        same_discrete_axes=old['trace']['discrete_dependent_axes']==new['trace']['discrete_dependent_axes'],
        only_new_option=flag is True and config_before==config_after,
        coupling_off_on=all(row['passed'] and row['tests']==9 for row in coupled),
        regression_134='Ran 134 tests' in (folder/'regression_v2.log').read_text(encoding='utf-8') and
                       (folder/'regression_v2.log').read_text(encoding='utf-8').strip().endswith('OK'),
        parameters='파라미터 검사 PASS' in (folder/'parameters_v1.log').read_text(encoding='utf-8'))
    sources=['evaluation/controllers/physical_urban_transport.py','evaluation/controllers/sdmpc_prediction_cache.py',
        'evaluation/controllers/sdmpc.py','evaluation/controllers/sdmpc_tangent_worker.py',
        'evaluation/controllers/sdmpc_tangent_fifo.py','diagnostics/check_sdmpc_reverse.py',
        'diagnostics/test_sdmpc_tangent.py','diagnostics/test_sdmpc_persistent_fifo.py',
        'diagnostics/check_persistent_fifo_coupling.py','diagnostics/finalize_sdmpc_persistent_plant.py',
        'docs/SDMPC_PERSISTENT_PLANT_20260922.md']
    manifest=[]
    for relative in sources:
        path=ROOT/relative;target=folder/'final_sources'/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():raise ValueError('Refusing to overwrite final source: '+str(target))
        shutil.copy2(path,target)
        manifest.append(dict(path=relative,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    report=dict(scope='Actual plant FIFO connection, preserved whole SDMPC behavior; no native run',
        checks=checks,pass_all=all(checks.values()),default_off_historical_errors=errors,
        implementation='PARTIAL_PERSISTENT_PLANT_BACKEND',default_enabled=False,
        performance_selection='NOT_SELECTED_FOR_SPEED',
        whole_decision_before_sec=full['before_sec'],whole_decision_after_sec=full['after_sec'],
        single_run_reduction_percent=full['reduction_percent'],decision_150s_target_met=full['decision_150s_target_met'],
        scalar_off_on_sec=read(folder/'states_v1/comparison.json')['scalar_sec'],
        fifo_stats=new['persistent_urban_fifo'],native_applied=False,sources=manifest,
        limits='Historical saved900s anchor; one whole decision timing per configuration. '
               'Python routing/allocation/accounting still crosses scalar/Dual boundaries. '
               'No full array-native plant or RM/VSL gain qualification is claimed.')
    with (folder/'connection_summary.json').open('x',encoding='utf-8') as f:
        json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in report.items() if k!='sources'},indent=2))
    if not report['pass_all']:raise SystemExit('Plant connection qualification failed')


if __name__=='__main__':main()
