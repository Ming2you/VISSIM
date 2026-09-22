"""Pin the architecture-review evidence without changing a production option."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'diagnostics/sdmpc_persistent_review_20260922'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sample=json.loads((OUT/'node_sites_v1/result.json').read_text(encoding='utf-8'))
    lifetime=json.loads((OUT/'lifetime_v3/result.json').read_text(encoding='utf-8'))
    prior=json.loads((ROOT/'diagnostics/sdmpc_array_transport_20260922/change_sources.json').read_text(encoding='utf-8'))
    unchanged={path:sha(Path(path))==expected for path,expected in sample['source_sha256'].items()}
    unchanged.update({path:sha(Path(path))==expected for path,expected in lifetime['source_sha256'].items()})
    for row in prior:
        path=ROOT/row['path']
        unchanged[str(path)]=sha(path)==row['sha256']
    config=ROOT/'diagnostics/sdmpc_trial_20260922/config_candidate.json'
    config_sha=sha(config)
    checks=dict(sample_primal_state_match=sample['complete_primal_state_match'],
        lifecycle_proof=lifetime['pass_all'],candidate_isolation=lifetime['candidate_isolation'],
        all_three_controls_reach_final_state_and_cost=lifetime['all_three_controls_reach_final_state_and_cost'],
        source_pins_unchanged=all(unchanged.values()),
        selected_config_unchanged=config_sha=='5c708fcff3cdda8abc33ee35a65d35613153f49fe233b745b9ba0ddeeb289fe4')
    paths=[Path(__file__),ROOT/'diagnostics/profile_sdmpc_array_lifetime.py',
        ROOT/'diagnostics/sdmpc_persistent_arena_probe.py',ROOT/'diagnostics/check_sdmpc_persistent_arena.py',
        ROOT/'docs/SDMPC_PERSISTENT_ARRAY_REVIEW_20260922.md']
    snapshot=OUT/'final_sources'
    snapshot.mkdir(exist_ok=False)
    for path in paths:shutil.copy2(path,snapshot/path.name)
    report=dict(scope='Architecture review and isolated persistent-array lifecycle proof',
        checks=checks,pass_all=all(checks.values()),source_checks=unchanged,
        selected_config_sha256=config_sha,
        recommended_first_scope='Urban demand/allocation/accepted transfer/stock and area accounting kernel chain',
        implementation_status='DIAGNOSTIC_PROOF_ONLY',performance_status='NOT_MEASURED_ON_FULL_PLANT',
        production_predictor_integrated=False,native_applied=False,
        sample=dict(horizon_sec=150,axes=77,total_nodes=sample['total_nodes'],
            samples=sample['sample_count'],max_primal_state_error=sample['max_primal_state_error'],
            attribution_is_cpu_time=False),
        lifecycle=dict(scenarios=len(lifetime['scenarios']),steps_per_scenario=450,
            stage_calls_per_scenario=1350,exact_tape_and_jacobian=True,
            max_mass_residual=max(row['max_mass_residual'] for row in lifetime['scenarios'])),
        prior_failure_preserved='lifetime_v1/failure.json',
        added_sources={str(p.relative_to(ROOT)):sha(p) for p in paths})
    target=OUT/'review_summary.json'
    with target.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_checks','added_sources')},indent=2))
    if not report['pass_all']:raise SystemExit('Architecture evidence qualification failed')


if __name__=='__main__':main()
