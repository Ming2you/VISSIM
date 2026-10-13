"""One city-only native arm, reusing a closed, execution-verified hold arm.

No fitting/optimization/launch. The failed older microscopic replay remains
failed; only the already validated NEW paired experiment qualifies its hold.
The new trial must independently pass exact prefix and execution validation.
"""
import csv
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
H = HERE.parent.parent
ROOT = H.parents[2]
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
OUT = I / 'native_urbanrm269_cityonly287_2400_r2'
RUN = Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold')
F = RUN / 'decisions_sdmpc31_g_2400_hold_s29'
FORECAST = HERE / 'forecast2400'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return [{k: v for k, v in r.items() if k != 'metadata'} for r in csv.DictReader(stream)]


def main():
    recovery = read(HERE / 'preparation_disk_failure.json')
    assert recovery['status'] == 'failed_preparation_preserved_exact_bytes_as_hardlinks'
    assert recovery['original_prepare_sha256'] == sha(HERE / 'prepare_native_before_disk_failure.py.txt')
    assert not OUT.exists(), 'Preserve existing preparation/attempt'
    result = read(FORECAST / 'summary.json')
    assert result['status'] == 'complete' and result['forecasts'] == 2
    assert all(x['shared_constraints']['feasible'] for x in result['results'].values())
    assert result['optimizer_calls'] == 0 and result['application']['state_error']==0
    baseline_model=read(H/'aggregate270/matched280/authority/summary.json')['results']['hold']
    city_delta=result['results']['city_only']['omega_ttt_veh_h']-baseline_model['omega_ttt_veh_h']
    assert abs(city_delta)>=1, 'No additionalnative solely for a tiny modeled change'
    pins = dict(result['source_pins'])
    for name, expected in pins.items():
        assert sha(Path(name)) == expected, name

    analysis = H / 'native2400_analysis'
    proof = read(analysis / 'summary.json')
    audit = read(analysis / 'observed_input_qualification.json')
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.qualify_native2400 import validate_scope
    scope = validate_scope(proof, audit)
    closure = read(analysis / 'runtime_closure.json')
    assert closure['all_owned_processes_closed'] and closure['owner_exit_code'] == 0
    assert closure['normal_native_end_sec'] == 2850
    execution_path = analysis / 'hold/execution.json'
    execution = read(execution_path)
    provenance_path = RUN / 'run_provenance_sdmpc31_g_2400_hold_s29.json'
    provenance = read(provenance_path)
    assert execution['native_execution_passed'] and execution['checks']['actual_commands']['passed']
    assert execution['run_id'] == provenance['run_id'] and Path(execution['run_directory']) == RUN
    assert execution['terminal_sec'] == provenance['sim_period_sec'] == 2850
    assert provenance['seed'] == 29
    first_signal = next(x for x in execution['checks']['actual_commands']['decisions'] if x['kinds'].get('signal', 0))
    assert first_signal['sim_sec'] == 900
    network = I / 'selected/network/native_seed29.inpx'
    assert sha(network) == provenance['files']['network']['sha256']
    for p in (Path(__file__), FORECAST / 'summary.json', FORECAST / 'city_only.json',
              FORECAST / 'rm_only.json', FORECAST / 'action_contract.json',
              analysis / 'summary.json', analysis / 'observed_input_qualification.json',
              analysis / 'runtime_closure.json', execution_path, provenance_path,
              network, I / 'native_pair1200/run_pair.ps1', ROOT / 'tools/sdmpc31/freeze_worktree.ps1'):
        pins[str(p)] = sha(p)

    # This separate qualification is about the NEW, exact-prefix paired runs.
    # Never overwrite/relabel the older source-run replay's failed assertion.
    qualification_path = HERE / 'baseline_reuse_qualification_r2.json'
    assert not qualification_path.exists()
    save(qualification_path, dict(
        schema='scoped-native-baseline-reuse/v1',
        scope=scope, counterfactual_valid=audit['new_pair_causal_response_valid'],
        paired_prefix_exact=proof['paired_prefix_exact'],
        original_source_replay_counterfactual_valid=proof['counterfactual_valid'],
        original_source_microscopic_history_exact=proof['original_initial_history_exact'],
        original_failure_preserved=True, baseline_run=str(RUN),
        completed_native_end_sec=2850, all_owned_processes_closed=True,
        source_summary=str(analysis / 'summary.json'), source_summary_sha256=sha(analysis / 'summary.json'),
        scope_audit=str(analysis / 'observed_input_qualification.json'), scope_audit_sha256=sha(analysis / 'observed_input_qualification.json'),
        execution=str(execution_path), execution_sha256=sha(execution_path),
        new_trial_prefix_validated=False, new_trial_gain_validated=False))
    pins[str(qualification_path)] = sha(qualification_path)
    destination = OUT / 'selected/commands'
    destination.mkdir(parents=True)
    prefix = []
    witnesses = {x['sim_sec']: x for x in execution['checks']['actual_commands']['decisions']}
    for sec in [1, *range(150, 2400, 150)]:
        record = dict(sim_sec=sec)
        for suffix in ('json', 'csv'):
            src = F / f'action_{sec:06d}.{suffix}'
            target = destination / src.name
            pins[str(src)] = sha(src)
            if suffix == 'csv':
                assert witnesses[sec]['sha256'] == pins[str(src)]
            # Reuse exact immutable local prefix bytes without another GB on C.
            # Canonical freezing still produces independent files on E.
            local = I / 'native_urbanrm269_10681only_2400/selected/commands' / src.name
            assert sha(local) == pins[str(src)]
            os.link(local, target)
            assert sha(target) == pins[str(src)]
            pins[str(target)] = sha(target)
            record[suffix] = dict(source=str(src), destination=str(target), sha256=sha(target))
        prefix.append(record)
    commands = []
    for sec in (2400, 2550, 2700, 2850):
        original_sec = min(sec, 2700)
        before = rows(F / f'action_{original_sec:06d}.csv')
        forecast_hold = rows(H / 'selection2400_discrete/hold' / f'action_{original_sec:06d}.csv')
        assert before == forecast_hold, 'Held prediction must match actual baseline commands'
        for suffix in ('json', 'csv'):
            src = FORECAST / 'city_only' / f'action_{original_sec:06d}.{suffix}'
            target = destination / f'action_{sec:06d}.{suffix}'
            pins[str(src)] = sha(src)
            if sec == 2850 and suffix == 'json':
                data = read(src)
                data['metadata']['sim_sec'] = sec
                save(target, data)
            else:
                shutil.copy2(src, target)
            pins[str(target)] = sha(target)
        after = rows(destination / f'action_{sec:06d}.csv')
        assert len(before) == len(after)
        changes = [(a, b) for a, b in zip(before, after) if a != b]
        assert changes and all(a['kind'] in ('signal','signal_sg') and a['kind']==b['kind'] and a['id']==b['id'] for a,b in changes)
        assert [r for r in before if r['kind'] in ('ramp_meter','vsl')]==[r for r in after if r['kind'] in ('ramp_meter','vsl')]
        commands.append(dict(sim_sec=sec,changed_kinds=sorted({a['kind'] for a,b in changes}),
            changed_rows=[dict(before=a,after=b) for a,b in changes],rm_vsl_held=True))

    protocol = dict(start_sec=2400, end_sec=2850, seed=29, arms=['selected'],
        control_start_sec=900, controller='wu-link', network=str(network), network_sha256=sha(network),
        command_pins=pins, native_authorization_pending=False,
        native_authorization='Necessary bounded native validation for the active user calibration goal',
        max_native_runs=1, automatic_retries=0, native_started=False,
        sim_resolution=10, vehicle_record_interval_sec=5, observation_interval_sec=150,
        future_observation_inputs=False, controller_optimization=False,
        reuse_native_baseline=dict(run=str(RUN), summary=str(qualification_path), sha256=sha(qualification_path)),
        controlled_prefix=dict(control_start_sec=900, execution=str(execution_path), execution_sha256=sha(execution_path),
            provenance=str(provenance_path), provenance_sha256=sha(provenance_path), commands=prefix),
        physical_command_check=commands, prediction_summary=str(FORECAST / 'summary.json'),
        allowed_concurrent_vissim=[],
        qualification_requires_exact_native_prefix=True,
        scope='City green and offset only, copied from the earlier jointselection; all eight RM and all VSL exactly held. Not new SDMPC optimization.',
        comparison='Reused native hold versus new selected, same2400-2850 Omega701; independently validate prefix, LDP/VSL, exits/residual/removal/outside costs.',
        terminal_command='2850 repeats2700 only for runner completion; no later traffic counted.')
    save(OUT / 'protocol.json', protocol)
    save(HERE / 'native_preparation.json', dict(status='prepared_not_launched',
        time_utc=datetime.now(timezone.utc).isoformat(), protocol=str(OUT / 'protocol.json'),
        protocol_sha256=sha(OUT / 'protocol.json'), predictions_completed=2, native_runs=0,
        output='E:/VISSIM_runs/20261010_urbanrm269_cityonly287_s29',
        runtime='E:/VISSIM_runtime/20261010_urbanrm269_cityonly287',
        forecast_delta_omega_veh_h=city_delta,
        forecast_extra_merge10681_veh=result['results']['city_only']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']-baseline_model['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681'], launch_requires_existing_finite_queue_normal_complete=True,
        baseline_reuse_scope=scope, complete_sdmpc_runtime_comparison_started=True))
    print('PREPARED_ONE_NATIVE_ARM', OUT, flush=True)


if __name__ == '__main__':
    main()
