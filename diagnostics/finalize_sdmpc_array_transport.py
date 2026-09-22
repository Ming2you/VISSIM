"""Report array-transport evidence; never claim a complete controller benchmark."""
from pathlib import Path
import hashlib
import json
ROOT=Path(__file__).resolve().parents[1]


def main():
    folder=ROOT/'diagnostics/sdmpc_array_transport_20260922'
    load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    old=load(ROOT/'diagnostics/sdmpc_trial_20260922/trial_h3_v1/result.json')
    new=load(folder/'array_h3_v1/result.json')
    matrices=load(folder/'array_h3_v1/comparison.json')
    states=load(folder/'states_v1/comparison.json')
    physical=load(folder/'physical_fixture_check_v3.json')
    before=load(ROOT/'diagnostics/sdmpc_trial_20260922/config_candidate.json')
    after=load(folder/'config_candidate.json')
    enabled=after['adapter'].pop('sdmpc_array_transport')
    checks=dict(cost_resource_jacobians_exact=all(v==0. for v in matrices['checks'].values()),
        all_saved_states_exact=states['pass_all'],
        only_array_transport_option_added=enabled is True and before==after,
        runtime_sources_unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
            for p,h in new['transformed_source_sha256'].items()),
        same_graph_node_count=old['reverse_sweeps']['nodes']==new['reverse_sweeps']['nodes'],
        same_branch_event_counts=old['trace']['event_counts']==new['trace']['event_counts'],
        same_tie_axes=old['trace']['exact_tie_axes']==new['trace']['exact_tie_axes'],
        same_discrete_dependency_axes=old['trace']['discrete_dependent_axes']==new['trace']['discrete_dependent_axes'],
        physical_off_on=physical['pass_all'],
        regression_suite='Ran 129 tests' in (folder/'tests_sdmpc_v1.log').read_text(encoding='utf-8')
            and (folder/'tests_sdmpc_v1.log').read_text(encoding='utf-8').strip().endswith('OK'),
        coupling_suite='Ran 9 tests' in (folder/'tests_coupling_v1.log').read_text(encoding='utf-8')
            and (folder/'tests_coupling_v1.log').read_text(encoding='utf-8').strip().endswith('OK'),
        parameters='파라미터 검사 PASS' in (folder/'parameters_v1.log').read_text(encoding='utf-8'))
    stats=new['array_transport']
    report=dict(scope='One 450s prediction with complete Jacobian, plus paired continuous full states; no whole SDMPC solve.',
        checks=checks,numerical_equivalence_pass=all(checks.values()),
        performance_selection='NOT_SELECTED_FOR_SPEED',default_enabled=False,
        native_applied=False,whole_decision_measured=False,
        prior_jacobian_sec=old['wall_sec_including_spawn'],current_jacobian_sec=new['wall_sec_including_spawn'],
        repetitions=1,scalar_off_on_sec=states['scalar_sec'],kernel=stats,
        wrapper_sec=stats['wall_sec']-stats['kernel_sec'],
        compiled_node_fraction=stats['nodes']/new['reverse_sweeps']['nodes'],
        limits='The prior Jacobian is a historical single timing. The paired scalar runs use current identical source. '
               'No speed gain or 150s decision target is certified; this kernel covers only longitudinal lane transport.')
    (folder/'qualification_summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    return 0 if all(checks.values()) else 1


if __name__=='__main__':raise SystemExit(main())
