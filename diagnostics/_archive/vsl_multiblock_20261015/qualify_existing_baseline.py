"""Read-only reuse qualification of the already completed OFF2250 hold arm."""
import hashlib, json
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=Path('E:/VISSIM_analysis/20261011_vsl_response349/causal_off2250_analysis_v2/native_analysis')
RUN=Path('E:/VISSIM_runs/20261011_vsl349_off2250_s29/hold')
COMMANDS=Path('E:/VISSIM_workspaces/vsl349_causal_20261011/diagnostics/sdmpc_n31_20260924/integration_20260926/native_vsl349_off2250/hold/commands')
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
out=HERE/'baseline_reuse_qualification.json'
assert not out.exists()
execution_path=BASE/'hold/execution.json'
prov_path=RUN/'run_provenance_sdmpc31_g_2250_hold_s29.json'
summary_path=BASE/'summary.json'
closure_path=BASE/'runtime_closure.json'
execution,prov,summary,closure=[read(p) for p in (execution_path,prov_path,summary_path,closure_path)]
checks={
    'native_execution_passed':execution['native_execution_passed'],
    'actual_commands_passed':execution['checks']['actual_commands']['passed'],
    'run_identity':execution['run_id']==prov['run_id'],
    'run_directory':Path(execution['run_directory']).resolve()==RUN.resolve(),
    'seed29':prov['seed']==29,
    'end2700':execution['terminal_sec']==2700 and prov['sim_period_sec']==2700,
    'original_prefix_exact':summary['paired_prefix_exact'] and summary['original_initial_history_exact'],
    'observed_inputs_exact':summary['source_observed_model_inputs_exact'],
    'existing_causal_pair_valid':summary['new_pair_causal_response_valid'],
}
decisions={int(row['sim_sec']):row for row in execution['checks']['actual_commands']['decisions']}
rows=[]
for sec in [1,*range(150,2701,150)]:
    path=COMMANDS/f'action_{sec:06}.csv'
    actual=sha(path)
    expected=decisions[sec]['sha256']
    rows.append(dict(sim_sec=sec,path=str(path),sha256=actual,native_recorded_sha256=expected,
                     exact=actual==expected))
checks['all_command_csv_bytes_match_native']=all(r['exact'] for r in rows)
record=dict(status='reuse_metadata_passed_pending_canonical_preflight' if all(checks.values()) else 'reuse_gate_failed_no_new_native',
    checks=checks,commands=rows,execution=str(execution_path),provenance=str(prov_path),
    runtime_closure=str(closure_path),runtime_closure_keys=list(closure),
    source_pins={str(p):sha(p) for p in (execution_path,prov_path,summary_path,closure_path)},
    native_runs=0,forecasts=0,lsa_missing_preserved=not execution.get('native_lsa_com_coverage_passed',False),
    next='Canonical runner reuse_native_baseline plus controlled_prefix must independently pass. This metadata check is not a new native completion or proof of future prefix equality.')
out.write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(status=record['status'],checks=checks),indent=2))
