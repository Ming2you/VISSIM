"""Closed-run SDMPC connection checks and matched traffic comparisons.

Reuses native-execution and physical-area measurement utilities. No simulator,
optimizer, model fit, or process control. The finite native queue must be closed.
"""
import csv
import argparse
import json
import math
import hashlib
from collections import Counter
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from diagnostics.com_execution_equivalence.verify_pair import verify_native_execution, decision_recovery_evidence, user_stop_evidence
from diagnostics.fast_fixed_profile_verify import prefix_digest
from diagnostics.capture_native_runtime_errors import parse_bytes
from scripts.measure_control_area import read_fzp_frames, measure_frames, terminal_lengths, sha256
from evaluation.controllers.control_area_objective import physical_membership_from_ledger

RUNS = Path('D:/VISSIM_runs/20260926_selected1200_replay')
ORIGINAL = Path('D:/VISSIM_runs/20260924_sd31_gain/sdmpc31_g_gain_s29_r3')


def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def controlled_reuse_metadata(protocol, prediction, baseline_terminal_sec):
    """Report the requested window, including a baseline ending exactly there.

    Missing outside-cost predictions stay unknown. This does not qualify native
    execution, prefix identity or actual gain; those checks remain in main().
    """
    start, end = protocol['start_sec'], protocol['end_sec']
    assert end - start == 450 and baseline_terminal_sec >= end
    values = [prediction[k] for k in ('delta_omega_ttt_veh_h', 'delta_omega_veh_h') if k in prediction]
    assert values and all(math.isfinite(float(x)) for x in values)
    assert all(abs(float(x) - float(values[0])) < 1e-9 for x in values)
    omega = float(values[0])
    outside = prediction.get('delta_tracked_outside_veh_h')
    if outside is not None:
        assert math.isfinite(float(outside))
    result = dict(predicted_delta_omega_veh_h=omega,
        predicted_delta_tracked_total_veh_h=None if outside is None else omega + float(outside))
    limitations = [f'Controlled command prefix is checked against the reused baseline; comparison window is {start}..{end}s. No fresh SDMPC selection during replay.']
    if baseline_terminal_sec > end:
        limitations.append(f'Reused baseline ends at{baseline_terminal_sec}s; its terminal native latent delay and uninserted count are not{end}s measurements and are omitted.')
    if outside is None:
        limitations.append('Outside-cost prediction is unavailable here; no zero outside cost or predicted tracked-total gain is assumed.')
    return result, limitations


def controlled_reuse_area(protocol, membership_path, *, root=ROOT):
    """Keep an explicit replay area identical to its pinned model configuration."""
    assert protocol.get('reuse_native_baseline') and protocol.get('controlled_prefix')
    configs = []
    for name, digest in protocol['command_pins'].items():
        path = Path(name)
        if path.suffix != '.json' or 'config' not in path.stem:
            continue
        assert sha256(path) == digest, str(path)
        area = load(path).get('control_area_objective', {})
        if not area.get('enabled'):
            continue
        assert (root / area['membership_path']).resolve() == membership_path.resolve(), 'Model and native comparison areas differ'
        configs.append(dict(path=str(path), sha256=digest))
    assert configs, 'No pinned model area for this reused controlled pair'
    return dict(model_configs=configs, membership_path=str(membership_path.resolve()),
                membership_sha256=sha256(membership_path))


def measurement_area(path, *, root=ROOT):
    """Load one pinned area for BOTH arms, including explicit area revisions."""
    document = load(path)
    pins = {str((root/item['path']).resolve()): item
            for item in [document['network'], *document.get('sources', [])]}
    revisions = document.get('area_revision_sources', [])
    if revisions:
        # The revised ledger retains historical source metadata. Its declared
        # revision pins supersede only the same files; all other pins remain.
        previous = document['previous_membership']
        assert sha256(root/previous['path']) == previous['sha256'], previous['path']
        assert load(root/previous['path'])['network'] == document['network']
        for item in revisions:
            pins[str((root/item['path']).resolve())] = item
    for resolved, item in pins.items():
        assert sha256(Path(resolved)) == item['sha256'], item['path']
    membership = physical_membership_from_ledger(document)
    assert sum(membership.values()) == document['counts']['inside_total']
    return document, membership, dict(path=str(path.resolve()), sha256=sha256(path),
        inside_links=sum(membership.values()), outside_links=sum(not x for x in membership.values()),
        network_sha256=document['network']['sha256'],
        current_source_pins={p:x['sha256'] for p,x in pins.items()},
        previous_membership=document.get('previous_membership'), same_area_for_both_arms=True)


def table(p, rows):
    with p.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def native_network_cost(run, end):
    data = load(run/'native_network_performance.json')
    assert data['schema'] == 'vissim_native_network_performance_v1'
    assert data['from_sec'] == 0 and data['to_sec'] == end
    assert data['read_at_sim_sec'] >= end and data['all_links_included'] is True
    assert data['evaluated_links'] > 0 and data['time_unit'] == 'veh*s'
    values = data['native']
    for key in ('TravTmTot', 'DelayLatent', 'DemandLatent', 'VehAct', 'VehArr'):
        assert type(values[key]) in (int, float) and math.isfinite(values[key]) and values[key] >= 0, key
    return {
        'native_physical_network_time_veh_h': values['TravTmTot']/3600,
        'native_uninserted_delay_veh_h': values['DelayLatent']/3600,
        'native_total_time_including_uninserted_veh_h': (values['TravTmTot']+values['DelayLatent'])/3600,
        'native_uninserted_at_end': values['DemandLatent'],
        'native_network_end_vehicles': values['VehAct'],
        'native_arrived_vehicles': values['VehArr'],
    }


def closed_loop_analysis_end(run_end, requested_end):
    end = run_end if requested_end is None else requested_end
    if not 900 < end <= run_end or end % 150:
        raise ValueError('Analysis end must be a 150-second boundary after900, within the recorded run')
    return end


def completed_nc_identity(run, end):
    candidates=list(run.glob('run_provenance_sdmpc31_nc*_s29.json'))
    assert len(candidates)==1, 'Ambiguous reused NC provenance'
    prov=load(candidates[0]);period=prov['sim_period_sec']
    assert type(period) is int and period>=end and prov['seed']==29
    assert prov['name']==f'sdmpc31_nc{period}_s29'
    return prov['name'],period


def traffic_events_through(events, end):
    return [e for e in events if e.get('kind') != 'unfinished_vehicle_input'
            and e.get('time_sec') is not None and e['time_sec'] <= end]


def independent_four_protocol(protocol):
    """The prospectively pinned seed71 experiment; not an arbitrary factorial."""
    if not protocol.get('independent_four_arm'):
        return False
    assert protocol.get('native_factorial') is True
    assert protocol['controller'] == 'diagnostic-ramp-profile'
    assert protocol['seed'] == 71 and protocol['arms'] == ['nc','rm','vsl','both']
    assert (protocol['start_sec'], protocol['end_sec'], protocol['control_start_sec']) == (2250,2700,2250)
    assert protocol['sim_resolution'] == 10 and protocol['vehicle_record_interval_sec'] == 5
    assert protocol['observation_interval_sec'] == 150 and protocol['future_observation_inputs'] is False
    assert protocol['network_sha256'] == '64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    return True


def observation_profile_pair(protocol):
    """Accept only explicitly prepared observation pairs and the seed73 replication."""
    if protocol.get('controller') != 'diagnostic-ramp-profile':
        return None
    if independent_four_protocol(protocol):
        return 'four71'
    assert (protocol['start_sec'], protocol['end_sec']) == (2700, 3150)
    arms = tuple(protocol['arms'])
    if protocol['seed'] == 47:
        assert arms == ('hold', 'release')
        return 'rm47'
    if protocol.get('replication_seed') is not None:
        assert protocol['replication_seed'] == protocol['seed'] == 73
        assert arms == ('release', 'release_vsl90')
        assert protocol['network_sha256'] == '64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
        assert protocol['sim_resolution'] == 10 and protocol['vehicle_record_interval_sec'] == 5
        assert protocol['observation_interval_sec'] == 150 and protocol['future_observation_inputs'] is False
        return 'vsl73'
    assert protocol['seed'] == 67 and arms == ('release', 'release_vsl90')
    return 'vsl67'


def previous_vsl67_prefix(protocol):
    """Reuse the completed native prefix proof; do not rescan the old FZP."""
    source = Path(protocol['original_native_protocol'])
    original = load(source)
    assert original['seed'] == 67 and original['intervention_sec'] == 2700
    assert original['source_network_sha256'] == protocol['network_sha256']
    path = source.parent/'native_summary.json'
    cached = load(path)
    assert cached['common_prefix_exact']
    prefixes = {row['arm']: row['prefix'] for row in cached['rows']}
    assert set(prefixes) == set(original['arms'])
    prefix = prefixes['release']
    assert all(value == prefix for value in prefixes.values())
    assert prefix['rows'] > 0 and prefix['last_time_s'] == 2695.1
    return prefix, dict(protocol=str(source), protocol_sha256=sha256(source),
                        summary=str(path), summary_sha256=sha256(path),
                        method='prefix_digest(cutoff=2700, recording_grid=(5,.1)); normalized FZP data rows',
                        old_fzp_rescanned=False)


def verify_recording_start_alignment(summary_path, alignment_path):
    """Qualify only the new pair; preserve the failed whole-file old-prefix test."""
    summary, proof = load(summary_path), load(alignment_path)
    protocol_path = Path(summary['protocol_path'])
    assert summary['protocol_sha256'] == sha256(protocol_path)
    assert observation_profile_pair(load(protocol_path)) == 'vsl67'
    assert (summary['start_sec'], summary['end_sec']) == (2700, 3150)
    assert summary['paired_prefix_exact'] and summary['common_start_vehicle_records_exact']
    assert all(row['native_execution_passed'] for row in summary['arms'].values())
    assert set(summary['arms']) == set(summary['prefixes']) == {'release', 'release_vsl90'}
    assert summary['prefixes']['release'] == summary['prefixes']['release_vsl90']
    assert proof['schema'] == 'recording-start-alignment/v1' and proof['overlap_exact']
    assert Path(proof['analysis_summary']).resolve() == summary_path.resolve()
    assert proof['analysis_summary_sha256'] == sha256(summary_path)
    assert (proof['first_common_record_s'], proof['cutoff_s']) == (5.1, 2700)
    assert proof['overlap'] == summary['original_prefix']
    assert proof['overlap']['last_time_s'] == 2695.1
    assert len(proof['extra_new_start_rows']) == 1
    assert float(proof['extra_new_start_rows'][0].split(';')[0]) == .1
    assert summary['prefixes']['release']['rows'] == proof['overlap']['rows'] + 1
    native = Path(proof['new_fzp']).stat()
    assert (native.st_size, native.st_mtime_ns) == (proof['new_file_size'], proof['new_mtime_ns'])
    assert not summary['original_initial_history_exact'] and not summary['counterfactual_valid']
    return dict(scope='within_new_seed67_pair_from_its_observed2700_state',
                paired_native_effect_valid=True, original_raw_prefix_exact=False,
                old_new_common_recorded_interval_exact=True,
                alignment_path=str(alignment_path), alignment_sha256=sha256(alignment_path),
                original_summary_sha256=sha256(summary_path))


def selected_vsl_prefix(protocol, alignment_path):
    """Use the qualified new67 prefix for an already evaluated VSL neighbor."""
    assert protocol['controller']=='wu-link' and protocol['arms']==['selected','vsl90']
    assert (protocol['seed'],protocol['start_sec'],protocol['end_sec'],protocol['control_start_sec'])==(67,2700,3150,2700)
    assert alignment_path is not None
    baseline_path=Path(protocol['baseline_summary'])
    proof=verify_recording_start_alignment(baseline_path,alignment_path)
    baseline=load(baseline_path)
    for path,digest in protocol['command_pins'].items(): assert sha256(Path(path))==digest,path
    prediction=Path(protocol['prediction_source']); assert sha256(prediction)==protocol['prediction_sha256']
    results=load(prediction)['results']
    left,right=(results[x]['execution'] for x in ('selected','vsl90'))
    assert left['quantities']['feasible'] and right['quantities']['feasible']
    assert abs(right['ttt_omega_veh_h']-left['ttt_omega_veh_h']-protocol['predicted_delta_omega_veh_h'])<1e-9
    for a,b in zip(results['selected']['commands'],results['vsl90']['commands']):
        assert all(a[k]==b[k] for k in ('meters','green_times','offsets'))
    return baseline['prefixes']['release'],proof


def controlled_pair_context(protocol, source, model_config, membership_path, *, protocol_dir, root=ROOT):
    """Qualify a prospective held/selected replay against its observed state.

    This verifies inputs only. Native prefix equality, command application,
    runtime closure and both measured costs remain separate gates below.
    """
    assert protocol['controller'] == 'wu-link'
    assert protocol['arms'] == ['hold', 'selected'] and not protocol.get('reuse_native_baseline')
    start, end = protocol['start_sec'], protocol['end_sec']
    assert start % 150 == 0 and end - start == 450
    assert protocol['control_start_sec'] < start
    assert protocol['future_observation_inputs'] is False and protocol['controller_optimization'] is False
    assert protocol['sim_resolution'] == 10 and protocol['vehicle_record_interval_sec'] == 5
    pins = {Path(p).resolve(): h for p, h in protocol['command_pins'].items()}
    for p, digest in pins.items():
        assert sha256(p) == digest, str(p)
    state_path = source / f'state_{start:06d}.json'
    assert pins[state_path.resolve()] == sha256(state_path)
    state = load(state_path)
    assert state['sim_sec'] == start and state['vehicle_records']['complete']
    for sec in (1, *range(150, start, 150)):
        for suffix in ('.json', '.csv'):
            path = source / f'action_{sec:06d}{suffix}'
            assert pins[path.resolve()] == sha256(path)
    provenance_path, = source.parent.glob('run_provenance_*.json')
    provenance = load(provenance_path)
    assert pins[provenance_path.resolve()] == sha256(provenance_path)
    assert provenance['seed'] == protocol['seed']
    assert provenance['files']['network']['sha256'] == protocol['network_sha256']
    assert provenance['sim_period_sec'] >= end
    assert pins[model_config.resolve()] == sha256(model_config)
    model_area = root / load(model_config)['control_area_objective']['membership_path']
    assert model_area.resolve() == membership_path.resolve(), 'Model and native comparison areas differ'
    prediction_path = Path(protocol['prediction_summary'])
    assert pins[prediction_path.resolve()] == sha256(prediction_path)
    prediction = load(prediction_path)
    assert prediction['status'] == 'two_discrete_predictions_complete'
    assert prediction['selected_model_caps_feasible']
    prediction_pins = {(root / p).resolve(): h for p, h in prediction['source_pins'].items()}
    assert prediction_pins[state_path.resolve()] == sha256(state_path)
    assert prediction_pins[model_config.resolve()] == sha256(model_config)
    target_caps = None
    for arm in ('hold', 'selected'):
        result = prediction['results'][arm]
        quantities = result['shared_constraints']
        assert quantities['feasible']
        assert quantities['window']['start_sec'] == start and quantities['window']['end_sec'] == end
        caps = [quantities[key]['target'] for key in ('np', 'nuf')]
        if target_caps is None:
            target_caps = caps
        assert caps == target_caps, 'Held/selected predictions used different caps'
        assert [r['sim_sec'] for r in result['commands']] == list(range(start, end, 150))
        for row in result['commands']:
            command = protocol_dir / arm / 'commands' / ('action_%06d.csv' % row['sim_sec'])
            assert pins[command.resolve()] == sha256(command) == row['csv_sha256']
    expected_delta = prediction['results']['selected']['omega_ttt_veh_h'] - prediction['results']['hold']['omega_ttt_veh_h']
    assert abs(expected_delta - prediction['delta_omega_ttt_veh_h']) < 1e-8
    return dict(source_decisions=str(source.resolve()), state_sha256=sha256(state_path),
                provenance_sha256=sha256(provenance_path),
                model_config_sha256=sha256(model_config), membership_sha256=sha256(membership_path),
                prediction_path=str(prediction_path), prediction_sha256=sha256(prediction_path),
                predicted_delta_omega_veh_h=prediction['delta_omega_ttt_veh_h'],
                validation_scope='Pinned input/context only; does not establish native equivalence or gain')


def decision_summary(decisions, start, end, *, recovery=None):
    """Read completed decisions only, keeping proposed commands distinct from native proof."""
    rows = []
    # First control slew is relative to the last written warmup command,
    # not an assumed open meter or the optimizer's next predicted block.
    previous_path = decisions / f'action_{start-150:06d}.csv'
    with previous_path.open(encoding='utf-8-sig', newline='') as stream:
        previous_rows = [r for r in csv.DictReader(stream) if r['kind'] == 'ramp_meter']
    previous_meters = {r['id']: float(r['green_sec']) for r in previous_rows}
    assert len(previous_rows) == len(previous_meters) == 8, previous_path
    for sec in range(start, end, 150):
        stem = decisions / f'action_{sec:06d}'
        held=load(stem.with_suffix('.json')).get('metadata',{}).get('controller_status')=='hold_previous_error'
        if held:
            assert recovery is not None and recovery['passed'] and str(sec) in recovery['holds'], 'Unverified held decision'
            proof=recovery['holds'][str(sec)]
            assert proof['command_json_sha256']==sha256(stem.with_suffix('.json'))
            assert proof['command_csv_sha256']==sha256(stem.with_suffix('.csv'))
        else:
            assert recovery is None or str(sec) not in recovery['holds'], 'Recovery record/command mismatch'
            report = load(stem.with_suffix('.joint.json'))
            assert report['completed'] is True, f'Incomplete SDMPC decision: {sec}'
            selected = report['selection']
            assert selected['feasible'] is True, f'Infeasible selected SDMPC command: {sec}'
            binding = load(stem.with_suffix('.joint_written.json'))
            assert binding['prewrite_binding_passed'] and binding['written_command_binding_passed'], sec
            for key, suffix in (('action_csv', '.csv'), ('action_json', '.json')):
                path = stem.with_suffix(suffix)
                assert Path(binding[key]['path']).resolve() == path.resolve(), (sec, key, 'path')
                assert sha256(path) == binding[key]['sha256'], (sec, key, 'sha256')
            pfo = selected['pfo_warm_start']
        with stem.with_suffix('.csv').open(encoding='utf-8-sig', newline='') as stream:
            commands = list(csv.DictReader(stream))
        vsl, meters = {}, {}
        for command in commands:
            if command['kind'] == 'vsl':
                key, speed = command['id'], float(command['speed_kph'])
                assert speed in (50, 60, 70, 80, 90, 100, 110), (sec, key, speed)
                assert key not in vsl or vsl[key] == speed, (sec, key)
                vsl[key] = speed
            elif command['kind'] == 'ramp_meter':
                key, green = command['id'], float(command['green_sec'])
                assert key not in meters, (sec, key, 'duplicate meter')
                assert math.isfinite(green) and green.is_integer() and 0 <= green <= 10, (sec, key, green)
                meters[key] = green
        assert set(meters) == set(previous_meters), (sec, meters)
        changes = {key: meters[key]-previous_meters[key] for key in meters}
        assert all(abs(delta) <= 2 for delta in changes.values()), (sec, 'RM slew', changes)
        assert all(vsl.get(key) == 110 for key in ('RW_FW_E_S0', 'RW_FW_W_S0')), (sec, 'entry VSL')
        previous_meters = meters
        if held:
            rows.append(dict(sim_sec=sec,vsl_commands_kph=vsl,meter_green_commands_sec=meters,
                written_command_binding_passed=None,command_bounds_and_slew_passed=True,
                meter_green_change_sec=changes,restricted_vsl={k:v for k,v in vsl.items() if v<110},
                restricted_meters={k:v for k,v in meters.items() if v<10},
                hold_previous_error=True,optimizer_success=False,recovery_evidence=proof,
                prediction_status='not_computed',predicted_reduction_from_held_veh_h=None,
                predicted_ttt_reduction_from_held_veh_h=None,predicted_objective_reduction_from_held_veh_h=None,
                pfo=None,sdmpc_candidates=None,sdmpc_converged=False,model_constraints=None,
                native_execution_verified=False))
            continue
        rows.append({
            'sim_sec': sec, 'vsl_commands_kph': vsl, 'meter_green_commands_sec': meters,
            'written_command_binding_passed': True,
            'command_bounds_and_slew_passed': True, 'meter_green_change_sec': changes,
            'restricted_vsl': {k: v for k, v in vsl.items() if v < 110},
            'restricted_meters': {k: v for k, v in meters.items() if v < 10},
            # In cap mode the progress event's held_objective is the PFO warm start.
            # The selection record preserves the separate original held command.
            'held_surrogate_objective_veh_h': selected['held_objective'],
            'pfo_warm_start_surrogate_objective_veh_h': selected['warm_start_objective'],
            'selected_surrogate_objective_veh_h': selected['selected_objective'],
            # Retain the legacy reduction field, but label TTT and the augmented
            # score explicitly for terminal-only and distance-only experiments.
            'predicted_reduction_from_held_veh_h': selected['prediction_ttt_reduction'],
            'predicted_ttt_reduction_from_held_veh_h': selected['prediction_ttt_reduction'],
            'predicted_objective_reduction_from_held_veh_h': (
                selected['held_objective'] - selected['selected_objective']),
            'predicted_terminal_reduction_veh_h': selected.get('prediction_terminal_reduction', 0.0),
            'predicted_distance_reward_reduction_veh_h': selected.get('prediction_distance_cost_reduction', 0.0),
            'predicted_distance_increase_veh_km': selected.get('prediction_distance_increase_veh_km'),
            'pfo': {k: pfo[k] for k in ('max_iterations', 'executed_iterations',
                                      'accepted_iterations', 'converged', 'status', 'seconds')},
            'sdmpc_candidates': selected['candidates'],
            'sdmpc_converged': selected['converged'],
            'sdmpc_after_pfo_seconds': selected['sdmpc_after_pfo_seconds'],
            'model_constraints': selected['final_constraints'],
        })
    return {'scope': 'Model decision and CSV command summary; native execution is verified separately.',
            'warning': 'Rolling predicted reductions have different initial states; do not sum them as realized gain.',
            'held_error_decisions':sum(bool(r.get('hold_previous_error')) for r in rows),
            'optimized_decisions':sum(not r.get('hold_previous_error',False) for r in rows),
            'decisions': rows}


def short_connection(runs, nc_run, output, status_path):
    """Check a closed 1200s connection trial, without claiming congestion gain.

    The caller must separately confirm the owner/native processes have closed.
    Reuse the native command oracle and observation contracts, not new models.
    """
    from evaluation.controllers import obs150_contract as oc

    status = load(status_path)
    assert status['stage'] == 'requested_native_arms_complete_unanalyzed', status
    assert Path(status['details']['out_dir']).resolve() == runs.resolve()
    assert status['details']['arms'] == ['sdmpc'] and status['details']['terminal'] == 1200
    assert not (runs/'STOP').exists() and not (nc_run.parent/'STOP').exists()
    assert not (output/'summary.json').exists(), 'Preserve completed connection check'
    name = 'sdmpc31_sdmpc1200_s29'
    run = runs/'sdmpc'
    decisions = run/f'decisions_{name}'
    result = {'scope': 'SDMPC1200 connection only; not congestion or net-gain qualification',
              'passed': False, 'whole_omega_gain_qualified': False,
              'process_exit_verified_by_this_function': False,
              'status_path': str(status_path), 'status_sha256': sha256(status_path)}
    try:
        assert f'OK {name} attempt=1 ' in (run/'launch.log').read_text(encoding='utf-8-sig')
        execution = verify_native_execution(run, 1200, run_name=name)
        save(output/'execution.json', execution)
        result['native_execution_passed'] = execution['native_execution_passed']
        result['native_lsa_com_coverage_passed'] = execution['native_lsa_com_coverage_passed']
        assert execution['native_execution_passed'], 'Native LDP/readback verification failed'
        report = decision_summary(decisions, 900, 1200)
        save(output/'decisions.json', report)
        for sec in (900, 1050):
            joint = load(decisions/f'action_{sec:06d}.joint.json')
            assert joint['selection']['feasible'] is True, sec
            binding = load(decisions/f'action_{sec:06d}.joint_written.json')
            assert binding['prewrite_binding_passed'] and binding['written_command_binding_passed'], sec
            for key in ('action_csv', 'action_json'):
                assert sha256(Path(binding[key]['path'])) == binding[key]['sha256'], (sec, key)
        provenance = load(run/f'run_provenance_{name}.json')
        tuning_pin = provenance['files']['tuning']
        assert sha256(Path(tuning_pin['path'])) == tuning_pin['sha256']
        tuning = load(Path(tuning_pin['path']))
        frozen = Path(provenance['files']['main_vbs_runner']['path']).parent.parent
        manifest_sha = sha256(frozen/tuning['freeway']['lane_plant'])
        windows = []
        for sec in (1, *range(150, 1200, 150)):
            raw = load(decisions/f'state_{sec:06d}.json')
            obs = raw[oc.RAW_STATE_KEY]
            oc.validate_raw(obs, expected_simres=10)
            derived = load(decisions/f'obs150/derived_{sec:06d}.json')
            oc.validate_derived(derived)
            assert obs['run_id'] == derived['run_id'] == provenance['run_id']
            assert derived['inputs']['raw_sha256'] == oc.canonical_sha256(obs)
            for kind, item in obs['frames'].items():
                assert sha256(oc.resolve(obs, item['path'])) == item['sha256'], (sec, kind)
                assert derived['inputs'][f'frame_{kind}_sha256'] == item['sha256']
            history = load(decisions/f'obs150/vsl_cohorts_{sec:06d}.json')
            assert history['run_id'] == obs['run_id'] and history['manifest_sha256'] == manifest_sha
            assert history['cutoff'] == sec and history['frame_sha256'] == obs['frames']['current']['sha256']
            assert history['derived_sha256'] == oc.canonical_sha256(derived)
            start, _, _ = oc.bundle_interval(sec)
            previous = decisions/f'obs150/vsl_cohorts_{start:06d}.json'
            assert history['previous_sha256'] == (sha256(previous) if previous.exists() else None)
            for road, audit in history['audit'].items():
                assert audit['conservation_max'] < 1e-7, (sec, road)
                stock = sum(sum(row.values()) for row in history['cohorts'][road])
                assert abs(stock-audit['end_stock']) < 1e-7, (sec, road)
            windows.append({'sim_sec': sec, 'history_sha256': sha256(decisions/f'obs150/vsl_cohorts_{sec:06d}.json'),
                            'audit': history['audit']})
        save(output/'observation_history.json', {'manifest_sha256': manifest_sha, 'windows': windows})
        nc_name = 'sdmpc31_nc9000_s29'
        nc_prov = load(nc_run/f'run_provenance_{nc_name}.json')
        assert nc_prov['seed'] == provenance['seed'] == 29
        assert nc_prov['files']['network']['sha256'] == provenance['files']['network']['sha256']
        assert f'OK {nc_name} attempt=1 ' in (nc_run/'launch.log').read_text(encoding='utf-8-sig')
        prefixes = {}
        for arm, folder in (('sdmpc', run), ('nc', nc_run)):
            fzp, = (folder/'vissim_eval').glob('*.fzp')
            prefixes[arm] = prefix_digest(fzp, 900, recording_grid=(5, .1))
        result.update(prefixes=prefixes, matched_nc=str(nc_run),
                      precontrol_prefix_exact=prefixes['sdmpc'] == prefixes['nc'],
                      completed_decisions=2, observed_history_windows=len(windows))
        assert result['precontrol_prefix_exact'], 'First900s native data differs from matched NC'
        result['passed'] = True
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        save(output/'summary.json', result)
    print(json.dumps(result, ensure_ascii=False), flush=True)


def native_response2250_stocks(path, membership):
    """Preserve the historic byte hash; collect just the completed450s stock window."""
    before=path.stat(); digest=hashlib.sha256(); count=0; header=False
    rows=[]; last=None; seen=set(); network_n=omega_n=0
    with path.open('rb') as stream:
        for raw in stream:
            if raw.startswith(b'$VEHICLE:'):
                assert not header
                assert raw.split(b':',1)[1].split(b';')[:3]==[b'SIMSEC',b'NO',b'LANE\\LINK\\NO']
                header=True
            if not raw[:1].isdigit():continue
            assert header
            values=raw.split(b';',3);t=float(values[0])
            if t>2700.1:break
            if t<2250:digest.update(raw);count+=1
            if t<2250.1:continue
            if last is not None and t!=last:
                assert abs(t-last-5)<1e-7
                rows.append(dict(time_s=last,network_n=network_n,omega_n=omega_n))
                network_n=omega_n=0;seen=set()
            last=t;vehicle=int(values[1]);assert vehicle not in seen;seen.add(vehicle)
            network_n+=1;omega_n+=int(membership[values[2].decode('ascii')])
    if last is not None:rows.append(dict(time_s=last,network_n=network_n,omega_n=omega_n))
    assert len(rows)==91 and rows[0]['time_s']==2250.1 and rows[-1]['time_s']==2700.1
    after=path.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    return dict(sha256=digest.hexdigest(),rows=count),rows


def observation_reuse2250(runs, nc_run, output, status_path):
    """Verify the one seed43 NC observation supplement before reusing old arms."""
    target=output/'observation_reuse.json'
    assert not target.exists(), 'Preserve an existing audit, including failures'
    closure=load(output/'runtime_closure.json')
    assert closure['all_owned_processes_closed'] and closure['owner_exit_code']==0
    status=load(status_path)
    assert status['stage']=='requested_native_arms_complete_unanalyzed'
    assert status['details']['arms']==['nc'] and status['details']['terminal']==2700
    assert not (runs/'STOP').exists()
    name='sdmpc31_nc2700_s43';run=runs/'nc'
    result=dict(passed=False,seed=43,prefix_cutoff_sec=2250,
                scope='Causal observation supplement and existing native-response reuse; no gain qualification',
                recording_dir=str(run/f'decisions_{name}'),profiles={})
    try:
        provenance=load(run/f'run_provenance_{name}.json')
        assert provenance['seed']==43 and provenance['sim_period_sec']==2700
        assert provenance['controller']=='no-control'
        assert provenance['files']['network']['sha256']=='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
        assert f'OK {name} attempt=1 ' in (run/'launch.log').read_text(encoding='utf-8-sig')
        execution=verify_native_execution(run,2700,run_name=name)
        save(output/'observation_execution.json',execution)
        result['native_execution_passed']=execution['native_execution_passed']
        result['native_lsa_com_coverage_passed']=execution['native_lsa_com_coverage_passed']
        assert result['native_execution_passed']
        prefixes={}
        for arm,folder in (('new_nc',run),('old_nc',nc_run)):
            fzp,=(folder/'vissim_eval').glob('*.fzp')
            prefixes[arm]=prefix_digest(fzp,2250,recording_grid=(5,.1))
        result.update(prefixes=prefixes,precontrol_prefix_exact=prefixes['new_nc']==prefixes['old_nc'])
        assert result['precontrol_prefix_exact'], 'Old native responses have a different microscopic history'
        old_proof=ROOT.parent/'control-full-review/diagnostics/metanet_net_gain_goal_20260924/heldout43/native_summary.json'
        proof=load(old_proof)
        assert proof['passed'] and set(proof['arms'])=={'rm','vsl','both'}
        ledger_path=HERE.parent/'selected/scenario/control_area_membership_213a5d.json'
        ledger=load(ledger_path)
        for item in [ledger['network'],*ledger['sources']]:assert sha256(ROOT/item['path'])==item['sha256']
        membership=physical_membership_from_ledger(ledger)
        result['ledger']={'path':str(ledger_path),'sha256':sha256(ledger_path)}
        result['legacy_prefixes']={}
        result['stock_window_sec']=[2250.1,2700.1]
        for arm,folder in [('nc',nc_run),*[(a,Path('D:/VISSIM_runs/20260924_response2250_s43')/a/'run') for a in ('rm','vsl','both')]]:
            fzp,=(folder/'vissim_eval').glob('*.fzp')
            legacy,stocks=native_response2250_stocks(fzp,membership)
            assert legacy==proof['reference_prefix'], ('Legacy raw-line prefix differs',arm,legacy)
            result['legacy_prefixes'][arm]=legacy
            table(output/(arm+'_area_stocks_5s.csv'),stocks)
        result['prefix_hash_methods']='Current normalizes CRLF to LF; historic hashes raw CRLF bytes. Both verified independently.'
        result['reused_native_proof']={'path':str(old_proof),'sha256':sha256(old_proof)}
        native_root=Path('D:/VISSIM_runs/20260924_response2250_s43')
        preflight_path=native_root/'preflight.json';preflight=load(preflight_path)
        assert preflight['passed'] and preflight['seed']==43
        result['reused_preflight']={'path':str(preflight_path),'sha256':sha256(preflight_path)}
        for arm,row in proof['arms'].items():
            assert row['execution']['passed']
            assert row['prefix_before2250']==proof['reference_prefix']
            path=native_root/f'prepared_{arm}/fixed_profile.json'
            assert sha256(path)==preflight['pins'][str(path)], 'Executed command profile changed'
            profile=load(path)
            assert profile==load(native_root/(arm+'.json')), 'Prepared and requested profiles differ'
            assert profile['seed']==43 and profile['control_start_sec']==2250
            result['profiles'][arm]={'path':str(path),'sha256':sha256(path)}
        state_path=run/f'decisions_{name}/state_002250.json'
        state=load(state_path)
        assert state['sim_sec']==2250 and state['run_provenance']['run_id']==provenance['run_id']
        result['state']={'path':str(state_path),'sha256':sha256(state_path)}
        result['passed']=True
    except Exception as exc:
        result['error']=f'{type(exc).__name__}: {exc}'
        raise
    finally:
        save(target,result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('profiles','prefixes')}),flush=True)


def cached_diagnostics(runs, output, nc_run=None):
    """Use completed decision snapshots and the existing FZP aggregates only."""
    import bisect
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    summary = load(output/'summary.json')
    end = summary['end_sec']
    assert end >= 900 and end % 150 == 0 and summary['paired_prefix_exact']
    assert not (output/'spatial_decision_audit.json').exists(), 'Preserve completed audit'
    manifest = load(HERE.parent/'selected/plant_n31_v2.json')
    geometry_path = ROOT/manifest['sources']['geometry']['path']
    assert sha256(geometry_path) == manifest['sources']['geometry']['sha256']
    geometry = load(geometry_path)
    chains = {int(x['link']): (road, x['offset_m'])
              for road, chain in geometry['chains'].items() for x in chain}
    times = list(range(900, end+1, 150))
    costs, gradients, snapshots = {}, [], {}
    for arm in ('nc', 'sdmpc'):
        run = nc_run if arm == 'nc' and nc_run is not None else runs/arm
        name = summary.get('run_names', {}).get(arm, f'sdmpc31_{arm}{end}_s29')
        folder = run/f'decisions_{name}'
        matrices = {r: np.full((len(geometry['bounds'][r])-1, len(times)), np.nan)
                    for r in ('FW_E', 'FW_W')}
        for ti, sec in enumerate(times):
            state = load(folder/f'state_{sec:06d}.json')
            records = state['vehicle_records']
            assert records['complete'] and records['paused_at_sim_sec'] == sec
            sums = {r: np.zeros((2, len(matrices[r]))) for r in matrices}
            for vehicle in records['records']:
                address = chains.get(int(vehicle['link_no']))
                if address is None:
                    continue
                road, offset = address
                bounds = geometry['bounds'][road]
                position = offset + vehicle['position_m']
                # Native position may slightly overshoot a physical terminal.
                cell = min(len(bounds)-2, max(0, bisect.bisect_right(bounds, position)-1))
                sums[road][0, cell] += 1
                sums[road][1, cell] += vehicle['speed_kph']
            for road in matrices:
                count, speed = sums[road]
                np.divide(speed, count, out=matrices[road][:, ti], where=count > 0)
            if arm == 'sdmpc' and sec < end:
                selection = load(folder/f'action_{sec:06d}.joint.json')['selection']
                rows = [r for r in selection['gradient_rows'] if r['kind'] == 'meter']
                east = [r for r in rows if r['owner'] == 'FW_E']
                gradients.append({'sim_sec': sec, 'east_meter_gradient_rows': len(east),
                    'east_exact_zero_cost_and_resource_rows': sum(
                        r['total'] == 0 and all(v == 0 for v in r['resource_derivatives_scaled']) for r in east),
                    'rows': rows,
                    'finite_neighbor_audit_performed': selection['finite_neighbor_audit_performed']})
        snapshots[arm] = matrices
        residence = load(output/arm/'area_metrics.json')['physical_link_residence']
        groups = {}
        for link, row in residence.items():
            if int(link) in chains:
                group = chains[int(link)][0] + '_mainline'
            else:
                group = 'other_inside_Omega' if row['inside'] else 'outside_Omega'
            groups[group] = groups.get(group, 0.) + row['ttt_veh_h']
        costs[arm] = groups
    delta = {key: costs['sdmpc'][key]-costs['nc'][key] for key in costs['nc']}
    assert abs(sum(delta.values())-summary['delta_TTT_veh_h']-
               summary['delta_outside_Omega_residence_veh_h']) < 1e-7
    save(output/'spatial_decision_audit.json', {
        'cost_scope': f'0..{end}s, cached5s FZP residence including last-frame tail; excludes uninserted queue-time integral',
        'cost_veh_h': costs, 'delta_sdmpc_minus_nc_veh_h': delta,
        'meter_gradients': gradients,
        'heatmap_scope': f'Instantaneous observed native snapshots every150s,900..{end}; physical31cell geometry. Not a5s or150s averaged FZP heatmap.',
        'interpretation': 'A zero local derivative does not establish that a finite legal metering change has zero effect.'})
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharex=True)
    for row, road in enumerate(('FW_E', 'FW_W')):
        for col, arm in enumerate(('nc', 'sdmpc')):
            ax = axes[row, col]
            # Nearest-neighbour display around measured instants; no temporal averaging.
            edges = np.array([times[0]-75] + [t+75 for t in times])
            p = ax.pcolormesh(edges, np.array(geometry['bounds'][road])/1000,
                              snapshots[arm][road], cmap='RdYlBu', vmin=0, vmax=110)
            ax.set_title(f'{road} | {arm.upper()}')
            ax.set_xlim(900, end)
            ax.set_ylabel('Distance downstream [km]')
            ax.set_xlabel('Simulation time [s]')
            for boundary in geometry['boundaries']:
                if boundary['road'] == road and boundary['kind'] in ('ramp', 'offramp'):
                    ax.axhline(boundary['chain_pos_m']/1000, color='k', lw=.4, alpha=.35)
    fig.colorbar(p, ax=axes, label='Observed speed [km/h]', fraction=.025)
    fig.suptitle(f'Matched native{end} | seed29 | instantaneous150s snapshots,31physical cells')
    fig.savefig(output/'observed_snapshot_heatmap.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(json.dumps({'delta_cost_components': delta,
        'east_zero_meter_rows': [(r['sim_sec'], r['east_exact_zero_cost_and_resource_rows'],
                                  r['east_meter_gradient_rows']) for r in gradients]}), flush=True)


def captured_controlled_replay_ramps(protocol, selected_run, output):
    """Read frozen accepted-flow traces, without another model rollout or fit."""
    import gzip
    from types import SimpleNamespace as NS
    from evaluation.controllers.physical_ramp_branches import predicted_merge_quantity
    prediction_path=Path(protocol['prediction_summary'])
    preparation=prediction_path.parent
    launch=load(preparation/'native_launch.json')
    frozen=Path(launch['frozen_tree'])
    assert sha256(frozen/'FREEZE.json')==launch['freeze_sha256']
    manifest=load(frozen/'FREEZE.json')['files']
    pins={}
    def pinned(path):
        digest=sha256(path)
        assert manifest[path.relative_to(ROOT).as_posix()]==digest,path
        pins[str(path)]=digest
        return path
    predictions=load(pinned(prediction_path))
    prepared=load(pinned(preparation/'protocol.json'))
    baseline=load(Path(protocol['controlled_prefix']['provenance']))
    actual=load(selected_run/f'run_provenance_sdmpc31_g_{protocol["start_sec"]}_selected_s{protocol["seed"]}.json')
    assert Path(actual['workspace_root']).resolve()==frozen.resolve()
    initial_path=Path(protocol['reuse_native_baseline']['run'])/('decisions_'+baseline['name'])/f'state_{protocol["start_sec"]:06d}.json'
    assert sha256(initial_path)==prepared['source_sha256'][str(initial_path)]
    initial=load(initial_path)
    assert initial['vehicle_records']['complete'] and initial['sim_sec']==protocol['start_sec']
    pins[str(initial_path)]=sha256(initial_path)
    mapping=load(pinned(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'))
    ramps={r['id']:r for r in mapping['ramp_meters']}
    assert len(ramps)==8
    cfg=NS(network=NS(physical_ramp_branches={'ramps':ramps}))
    result={}
    for arm,case in (('hold','held_actual'),('selected','selected')):
        path=pinned(preparation/(arm+'_response.json.gz'))
        with gzip.open(path,'rt',encoding='utf-8') as stream:response=json.load(stream)
        assert response['conditional_model_feasibility_witness'] and response['model_constraint_coverage']['complete']
        accepted=predicted_merge_quantity(response,cfg,start_sec=protocol['start_sec'],end_sec=protocol['end_sec'])
        assert abs(accepted['total_rate_veh_h']-predictions[arm]['inherited_constraints']['nuf']['actual'])<1e-7
        rows={}
        for ramp,spec in ramps.items():
            start=sum(int(v['link_no'])==int(spec['connector']) for v in initial['vehicle_records']['records'])
            arrivals=math.fsum(x['vehicles'] for x in response['transfers'] if x['target']=='ramp:'+ramp)
            outgoing=[x for x in response['transfers'] if x['source']=='ramp:'+ramp]
            assert all(x['target']=='merge_pending:'+ramp for x in outgoing)
            merge=accepted['accepted_vehicles_by_ramp'][ramp]
            assert abs(math.fsum(x['vehicles'] for x in outgoing)-merge)<1e-7
            ending=start+arrivals-merge
            assert ending>=-1e-7
            rows[ramp]=dict(arrival=arrivals,merge=merge,final_stock=max(0.,ending),residual=0.,
                initial_stock=start,final_stock_source='initial connector stock plus captured accepted entries minus accepted merges; original endpoint ledger checks passed')
        result[case]=dict(ramps=rows,omega_ttt_veh_h=predictions[arm]['omega_ttt_veh_h'])
        del response, outgoing
    document=dict(results=result,source_sha256=pins,freeze_sha256=launch['freeze_sha256'],
        new_model_predictions=0,fit=0,future_states_used_as_prediction_inputs=False)
    save(output/'captured_prediction_ramps.json',document)
    return document


def replay_ramp_audit(runs, output, protocol_path, prediction_override=None, *, paired_history_only=False,
                      recording_alignment=None):
    """Compare frozen predictions with closed native detector bundles, without FZP scans."""
    from evaluation.controllers import obs150_contract as oc
    from evaluation.controllers.obs150_observation import check_rule_crosscheck

    protocol, comparison = load(protocol_path), load(output/'summary.json')
    independent_four = independent_four_protocol(protocol)
    aligned_scope = None
    if recording_alignment is not None:
        assert not paired_history_only
        aligned_scope = verify_recording_start_alignment(output/'summary.json', recording_alignment)
    elif paired_history_only:
        # A failed reproduction of an older run must stay failed. These checks
        # qualify only contrasts among the four newly executed common-prefix arms.
        assert protocol.get('native_factorial') is True
        assert protocol['arms'] == ['held_actual', 'rm_only', 'vsl_release', 'both']
        assert set(comparison['prefixes']) == set(protocol['arms'])
        assert comparison['paired_prefix_exact'] and comparison['common_start_vehicle_records_exact']
        assert all(p == comparison['prefixes']['held_actual'] for p in comparison['prefixes'].values())
        assert all(comparison['arms'][arm]['native_execution_passed'] for arm in protocol['arms'])
        assert comparison['start_sec'] == protocol['start_sec'] == 2250
        assert comparison['end_sec'] == protocol['end_sec'] == 2700
    else:
        assert comparison['counterfactual_valid']
    assert comparison['protocol_sha256'] == sha256(protocol_path)
    rm_pair=protocol.get('controller')=='diagnostic-ramp-profile'
    selected_vsl_pair=protocol.get('arms')==['selected','vsl90']
    reused=protocol.get('reuse_native_baseline')
    factorial=protocol.get('native_factorial',False)
    controlled_reuse=bool(reused and protocol.get('controlled_prefix'))
    if independent_four:
        assert load(protocol_path.parent/'status.json')['stage']=='requested_native_arms_complete_unanalyzed'
        assert prediction_override is not None and not paired_history_only and recording_alignment is None
    elif rm_pair:
        if observation_profile_pair(protocol) in ('vsl67','vsl73'):
            assert load(protocol_path.parent/'status.json')['stage']=='both_native_complete_unanalyzed'
        else:
            assert load(runs/'launch_status.json')['stage']=='two_runs_complete_unanalyzed'
        assert prediction_override is not None
    elif selected_vsl_pair:
        assert protocol['seed']==67 and protocol['start_sec']==2700 and protocol['end_sec']==3150
        assert load(protocol_path.parent/'status.json')['stage']=='both_native_complete_unanalyzed'
        assert prediction_override is None and recording_alignment is None and not paired_history_only
    elif reused or factorial:
        assert load(protocol_path.parent/'status.json')['stage']=='requested_native_arms_complete_unanalyzed'
    else:
        assert load(runs/'task_status.json')['phase'] == 'complete'
    assert not (runs/'STOP').exists()
    audit_output=prediction_override.parent if rm_pair else output
    target = audit_output/'ramp_response_audit.json'
    assert not target.exists(), 'Preserve completed ramp audit'
    prediction_path = (Path(protocol['prediction_summary']) if controlled_reuse else
                       prediction_override if rm_pair else Path(protocol['prediction_source']))
    document=(captured_controlled_replay_ramps(protocol,runs/'selected',output) if controlled_reuse else load(prediction_path))
    if independent_four:
        receipt_path=output/'observation_reuse.json'
        receipt=load(receipt_path)
        assert receipt['passed'] and receipt['seed']==71
        assert document['native_profile_inputs'][str(receipt_path)] == sha256(receipt_path)
        assert receipt['native_summary']['sha256'] == sha256(output/'summary.json')
        assert document['native_reference_arm']=='nc' and document['reference_arm']=='held_actual'
        assert all(sha256(Path(path))==digest for path,digest in document['native_profile_inputs'].items())
    elif rm_pair:
        proof=document['replay_pair']
        assert Path(proof['native_summary']).resolve()==(output/'summary.json').resolve()
        assert proof['observation_cutoff_sec']==2700 and proof['future_states_used'] is False
        assert all(sha256(Path(path))==digest for path,digest in proof['files'].items())
    elif not controlled_reuse:
        assert sha256(prediction_path) == protocol['prediction_sha256']
    predictions = document['results']
    if selected_vsl_pair:
        predictions={arm:predictions[arm]['execution'] for arm in protocol['arms']}
        assert all(row['quantities']['feasible'] for row in predictions.values())
        for row in predictions.values():
            assert all(set(r)=={'arrivals','merges','final_stock','residual'} for r in row['ramps'].values())
            row['ramps']={r:dict(arrival=v['arrivals'],merge=v['merges'],
                                 final_stock=v['final_stock'],residual=v['residual'])
                          for r,v in row['ramps'].items()}
    cases = ({'nc':'held_actual','rm':'rm','vsl':'vsl','both':'both'} if independent_four else
             {arm:arm for arm in protocol['arms']} if selected_vsl_pair else
             {arm:arm+'_actual' for arm in protocol['arms']} if rm_pair and protocol['seed'] in (67,73) else
             {arm:arm for arm in protocol['arms']} if factorial else
             {'hold':'held_actual','selected':'selected'} if reused else
             {'hold': 'held_actual', 'release': 'release_actual' if rm_pair else 'vsl_FW_E__seg13_release'})
    assert set(cases) == (set(protocol['arms'])|{'hold'} if reused else set(protocol['arms']))
    start, end = protocol['start_sec'], protocol['end_sec']
    assert end-start == 450
    report = dict(scope='Eight physical ramp connectors under the completed fixed '+('RM' if rm_pair else 'VSL')+' pair',
                  start_sec=start, end_sec=end, prediction_source=str(prediction_path),
                  prediction_sha256=sha256(prediction_path), arms={}, input_sha256={},
                  new_model_predictions=0, new_native_runs=0, fzp_rescans=0,
                  limitations=['Actual entries use native detector counts with the canonical boundary correction.',
                               'Merge = initial connector stock + entries - final stock - native removals; head crossings are separate.',
                               ('Retrospective autonomous forecasts used only observations through2700; later states are evaluation targets.'
                                if rm_pair else 'Future native observations are evaluation targets only; predictions were frozen before these runs.'),
                               ('RM-only one-state comparison, not VSL or independent-seed qualification.'
                                if rm_pair else 'The VSL pair does not by itself establish an RM intervention benefit.')])
    csv_rows = []
    if aligned_scope is not None:
        report['comparison_scope'] = aligned_scope
        report['limitations'][-1] = 'VSL-only effect under the same RM release schedule; seed67 already seen, not a fresh holdout.'
    if reused:
        report['scope']='Eight physical ramps: completed native hold vs saved selected city/RM commands'
        report['limitations'][-1]='Joint city/RM response; not an isolated RM or VSL efficacy test.'
    if controlled_reuse:
        report['scope']='Eight physical ramps: matched10681 g0 vs2/4/6 with all other commands fixed'
        report['limitations'][-1]='Isolated10681 actuator diagnostic at one existing seed29 state; not fresh PFO-feasible SDMPC selection.'
        report['captured_prediction_evidence']=str(output/'captured_prediction_ramps.json')
    if rm_pair and observation_profile_pair(protocol)=='vsl73':
        report['scope']='Eight physical ramps: seed73 VSL110/90 replication under identical RM release schedules'
        report['limitations'][-1]='New seed73, one fixed-policy contrast; no isolated RM effect or general VSL robustness claim.'
    if selected_vsl_pair:
        report['scope']='Eight physical ramps: VSL110/90 with identical selected SDMPC city/RM commands'
        report['limitations'][-1]='Isolated VSL contrast at already-used seed67; no isolated RM-effect or fresh holdout claim.'
    if factorial:
        report['scope']='Eight physical ramps: fixed-city onset2250 RM10484/VSL13 factorial'
        report['limitations'][-1]='One actual onset state; independent-state gain qualification remains separate.'
        if independent_four:
            report['scope']='Eight physical ramps: independent seed71 east4 RM/VSL13 factorial'
            report['limitations'][-2]='Autonomous forecasts use only observations through2250; later native states are evaluation targets.'
            report['limitations'][-1]='Fixed-command one-state independent-seed validation; not closed-loop SDMPC performance or general model qualification.'
    if paired_history_only:
        report.update(native_comparison_scope='within_four_new_replays_only',
            within_new_replays_common_history_exact=True,
            original_native_history_exact=comparison['original_initial_history_exact'],
            original_reproduction_check_preserved=True,
            prediction_history_equivalence_qualified=False,
            comparison_summary_sha256=sha256(output/'summary.json'))
        report['limitations'].append('Original9000 raw-prefix reproduction failed and remains failed. New four-arm native contrasts have identical prefixes; old-state forecast comparisons remain conditional until their consumed historical inputs are checked.')
    for arm, case in cases.items():
        assert comparison['arms'][arm]['native_execution_passed']
        run = Path(reused['run']) if reused and arm=='hold' else runs/arm
        name = f'sdmpc31_g_{start}_{arm}_s{protocol["seed"]}'
        if controlled_reuse and arm=='hold':name=load(Path(protocol['controlled_prefix']['provenance']))['name']
        decisions = run/f'decisions_{name}'
        prediction = predictions[case]['ramps']
        assert len(prediction) == 8
        initial_path = decisions/f'state_{start:06d}.json'
        initial = load(initial_path)
        assert initial['sim_sec'] == start and initial['vehicle_records']['complete']
        report['input_sha256'][str(initial_path)] = sha256(initial_path)

        def stock(raw, ramp):
            assert raw['vehicle_records']['complete']
            return sum(int(v['link_no']) == int(ramp.removeprefix('RM_C'))
                       for v in raw['vehicle_records']['records'])

        actual = {r: dict(initial_stock=stock(initial, r), arrival=0, head=0, merge=0,
                          removals=0, final_stock=stock(initial, r), windows=[])
                  for r in prediction}
        for sec in range(start+150, end+1, 150):
            path = decisions/f'state_{sec:06d}.json'
            raw = load(path)
            assert raw['sim_sec'] == sec
            report['input_sha256'][str(path)] = sha256(path)
            obs = raw[oc.RAW_STATE_KEY]
            detectors, _ = oc.read_detector_csv(obs['detector_config']['path'],
                                                 obs['detector_config']['sha256'])
            oc.validate_raw(obs, detectors, expected_simres=oc.EXPECTED_SIMRES)
            check_rule_crosscheck(obs, detectors)
            bundle = oc.load_bundle(raw)
            boundaries = oc.evaluate_boundaries(obs, detectors, bundle.frame_end,
                                                bundle.frame_start, bundle.err_rows)
            removals = oc.window_removals(bundle.err_rows, sec-150, sec)
            for ramp, row in actual.items():
                link = int(ramp.removeprefix('RM_C'))
                arrival = boundaries['ramp_arrival:'+ramp].cross
                heads = {d.boundary_ref for d in detectors if d.role == 'meter_head' and d.link == link}
                assert heads, ramp
                head = sum(boundaries[ref].cross for ref in heads)
                removed = sum(int(r['link']) == link for r in removals)
                ending = stock(raw, ramp)
                merge = row['final_stock']+arrival-ending-removed
                assert merge >= 0, (arm, ramp, sec, merge)
                row['windows'].append(dict(start_sec=sec-150, end_sec=sec, arrival=arrival,
                                           head=head, merge=merge, final_stock=ending, removals=removed))
                for key, value in dict(arrival=arrival, head=head, merge=merge, removals=removed).items():
                    row[key] += value
                row['final_stock'] = ending
        rows = {}
        for ramp, observed in actual.items():
            predicted = prediction[ramp]
            assert abs(observed['initial_stock']+predicted['arrival']-predicted['merge']-predicted['final_stock']) < 1e-7
            assert observed['initial_stock']+observed['arrival']-observed['merge']-observed['removals']-observed['final_stock'] == 0
            delta = {k: predicted[k]-observed[k] for k in ('arrival', 'merge', 'final_stock')}
            rows[ramp] = dict(actual=observed, predicted=predicted, prediction_minus_actual_veh=delta)
            csv_rows.append(dict(arm=arm, ramp=ramp, initial_stock=observed['initial_stock'],
                                 actual_arrival=observed['arrival'], predicted_arrival=predicted['arrival'],
                                 actual_merge=observed['merge'], predicted_merge=predicted['merge'],
                                 actual_final_stock=observed['final_stock'], predicted_final_stock=predicted['final_stock'],
                                 native_removals=observed['removals']))
        report['arms'][arm] = rows
    save(target, report)
    table(audit_output/'ramp_response_audit.csv', csv_rows)
    print(json.dumps(dict(report=str(target), rows=csv_rows)), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--short-connection', action='store_true')
    modes.add_argument('--observation-reuse2250', action='store_true')
    modes.add_argument('--closed-loop-3000', action='store_true')
    modes.add_argument('--closed-loop-8100', action='store_true')
    modes.add_argument('--closed-loop-9000', action='store_true')
    modes.add_argument('--replay-protocol', type=Path)
    parser.add_argument('--runs-root', type=Path)
    parser.add_argument('--paired-history-only', action='store_true',
                        help='Cached four-arm audit only; retain failed original reproduction and qualify only within-new-replay contrasts.')
    parser.add_argument('--recording-start-alignment', type=Path,
                        help='Explicit cached seed67 recording-start proof; original failed summary is preserved.')
    parser.add_argument('--nc-run-dir', type=Path, help='Reuse a completed matched NC run without copying or rerunning it')
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--status-json', type=Path)
    parser.add_argument('--cached-diagnostics', action='store_true')
    parser.add_argument('--cached-replay-ramp-audit', action='store_true')
    parser.add_argument('--prediction-summary', type=Path)
    parser.add_argument('--membership-json', type=Path,
                        help='Pinned area for a fresh closed-loop or controlled held/selected comparison')
    parser.add_argument('--controlled-pair-source', type=Path,
                        help='Original observed decisions for a two-arm held/selected450s replay')
    parser.add_argument('--controlled-pair-model-config', type=Path,
                        help='Pinned model config used for the completed discrete selection check')
    parser.add_argument('--analysis-end-sec', type=int,
                        help='Censor traffic comparison at this time; retain actual run completion checks')
    parser.add_argument('--user-stop-receipt', type=Path,
                        help='Explicit closed user-stop receipt for the SDMPC arm; NC must remain normally completed')
    args = parser.parse_args()
    controlled_pair = args.controlled_pair_source is not None
    reused_controlled_area = False
    if args.replay_protocol:
        replay = load(args.replay_protocol)
        reused_controlled_area = bool(replay.get('reuse_native_baseline') and replay.get('controlled_prefix'))
    if controlled_pair != (args.controlled_pair_model_config is not None):
        parser.error('Controlled pair requires both original decisions and model config')
    if controlled_pair and (not args.replay_protocol or args.membership_json is None
            or args.cached_diagnostics or args.cached_replay_ramp_audit or args.recording_start_alignment):
        parser.error('Controlled pair requires a fresh replay comparison and explicit model-matched area')
    if args.user_stop_receipt is not None and (not (args.closed_loop_3000 or args.closed_loop_8100 or args.closed_loop_9000)
            or args.analysis_end_sec is None or args.nc_run_dir is None
            or args.cached_diagnostics or args.cached_replay_ramp_audit):
        parser.error('--user-stop-receipt requires a fresh censored closed-loop comparison with completed NC')
    if args.analysis_end_sec is not None and (not (args.closed_loop_3000 or args.closed_loop_8100 or args.closed_loop_9000)
                                             or args.cached_diagnostics or args.cached_replay_ramp_audit):
        parser.error('--analysis-end-sec requires a fresh closed-loop comparison')
    if args.membership_json is not None and not (args.closed_loop_3000 or args.closed_loop_8100 or args.closed_loop_9000 or controlled_pair or reused_controlled_area):
        parser.error('--membership-json requires a fresh closed-loop or controlled pair comparison')
    if args.membership_json is not None and (args.cached_diagnostics or args.cached_replay_ramp_audit):
        parser.error('A changed area cannot reuse cached metrics from another area')
    selected_vsl_alignment = bool(args.replay_protocol and not args.cached_diagnostics
                                  and load(args.replay_protocol).get('arms') == ['selected','vsl90'])
    if args.recording_start_alignment is not None and not (args.replay_protocol and not args.paired_history_only
                                                          and (args.cached_replay_ramp_audit or selected_vsl_alignment)):
        parser.error('--recording-start-alignment requires the cached replay audit or the selected/VSL native pair')
    if args.paired_history_only and not (args.cached_replay_ramp_audit and args.replay_protocol):
        parser.error('--paired-history-only requires --cached-replay-ramp-audit and --replay-protocol')
    if args.observation_reuse2250:
        if any(x is None for x in (args.runs_root,args.nc_run_dir,args.output_dir,args.status_json)):
            parser.error('--observation-reuse2250 requires runs,reference,output,status paths')
        if args.cached_diagnostics or args.cached_replay_ramp_audit or args.prediction_summary:
            parser.error('Observation reuse is a separate completed-native audit')
        observation_reuse2250(args.runs_root,args.nc_run_dir,args.output_dir,args.status_json)
        return
    if args.prediction_summary is not None and not args.cached_replay_ramp_audit:
        parser.error('--prediction-summary requires the existing cached ramp audit')
    if args.short_connection:
        if any(x is None for x in (args.runs_root, args.nc_run_dir, args.output_dir, args.status_json)):
            parser.error('--short-connection requires --runs-root, --nc-run-dir, --output-dir, --status-json')
        if args.cached_diagnostics or args.cached_replay_ramp_audit:
            parser.error('--short-connection cannot be combined with cached analysis')
        short_connection(args.runs_root, args.nc_run_dir, args.output_dir, args.status_json)
        return
    if args.cached_replay_ramp_audit and (not args.replay_protocol or args.cached_diagnostics):
        parser.error('--cached-replay-ramp-audit requires --replay-protocol, without --cached-diagnostics')
    closed_loop = args.closed_loop_3000 or args.closed_loop_8100 or args.closed_loop_9000
    if args.nc_run_dir is not None and not closed_loop:
        parser.error('--nc-run-dir requires a closed-loop comparison')
    if closed_loop:
        run_end = 9000 if args.closed_loop_9000 else 8100 if args.closed_loop_8100 else 3000
        try:
            end = closed_loop_analysis_end(run_end, args.analysis_end_sec)
        except ValueError as exc:
            parser.error(str(exc))
        if run_end != 3000 and args.runs_root is None:
            parser.error('An explicit --runs-root is required outside the default3000 fixture')
        runs = args.runs_root or Path('D:/VISSIM_runs/20260926_sd31_closedloop3000')
        arms, start = ('nc', 'sdmpc'), 900
        output = HERE.parent/f'closedloop{end}_analysis'
        status_path = HERE.parent/f'closedloop{run_end}_status.json'
        names = {arm: f'sdmpc31_{arm}{run_end}_s29' for arm in arms}
        nc_run_end=run_end
        if args.nc_run_dir is not None:
            names['nc'],nc_run_end=completed_nc_identity(args.nc_run_dir,end)
        scope = f'matched traffic through{end}s from completed SDMPC{run_end}s and NC; execution alone does not establish gain'
    elif args.replay_protocol:
        if args.runs_root is None:
            parser.error('--replay-protocol requires --runs-root')
        protocol=load(args.replay_protocol)
        runs, arms = args.runs_root, (('hold','selected') if protocol.get('reuse_native_baseline') else tuple(protocol['arms']))
        start,end=protocol['start_sec'],protocol['end_sec']
        factorial = protocol.get('native_factorial',False)
        assert len(arms)==(4 if factorial else 2) and end-start==450 and type(protocol['seed']) is int
        if factorial and not independent_four_protocol(protocol):
            assert arms==('held_actual','rm_only','vsl_release','both') and start==2250 and protocol['seed']==29
        output,status_path=args.replay_protocol.parent/'analysis',args.replay_protocol.parent/'status.json'
        names={arm:f'sdmpc31_g_{start}_{arm}_s{protocol["seed"]}' for arm in arms}
        scope=protocol['scope']
    else:
        runs, arms, start, end = RUNS, ('hold', 'selected'), 1200, 1650
        output, status_path = HERE/'analysis', HERE/'status.json'
        names = {arm: f'sdmpc31_g_1200_{arm}_s29' for arm in arms}
        scope = 'one frozen SDMPC450s decision replay; not closed-loop performance'
    if not closed_loop:
        run_end = end
    traffic_censored = closed_loop and (end < run_end or end < nc_run_end)
    if args.output_dir is not None:
        output = args.output_dir
    if args.status_json is not None:
        status_path = args.status_json
    if args.cached_replay_ramp_audit:
        replay_ramp_audit(runs, output, args.replay_protocol, args.prediction_summary,
                          paired_history_only=args.paired_history_only,
                          recording_alignment=args.recording_start_alignment)
        return
    if args.cached_diagnostics:
        assert closed_loop
        cached_diagnostics(runs, output, args.nc_run_dir)
        return
    status = load(status_path)
    stopped_evidence=None
    if args.user_stop_receipt:
        assert end < run_end, 'User-stop analysis cannot claim the requested run completed'
        stopped_evidence=user_stop_evidence(runs/'sdmpc',end,args.user_stop_receipt)
        scope=f'matched traffic through{end}s: explicitly user-stopped SDMPC prefix versus completed NC'
    else:
        assert status['stage'] in ('both_native_complete_unanalyzed', 'requested_native_arms_complete_unanalyzed'), status
        assert not (runs/'STOP').exists(), 'User STOP exists'
    if closed_loop and not args.user_stop_receipt:
        assert Path(status['details']['out_dir']).resolve() == runs.resolve(), 'Completed queue belongs to another result directory'
        assert status['details']['terminal'] == run_end, 'Completion receipt must retain the actual run length'
        if 'arms' in status['details']:
            expected_arms = ['sdmpc'] if args.nc_run_dir is not None else list(arms)
            assert status['details']['arms'] == expected_arms, 'Requested native arms must have completed'
    assert not (output/'summary.json').exists(), 'Preserve existing completed comparison'
    protocol = load(args.replay_protocol or HERE/'protocol.json')
    controlled_context = None
    if controlled_pair:
        controlled_context = controlled_pair_context(protocol, args.controlled_pair_source,
            args.controlled_pair_model_config, args.membership_json, protocol_dir=args.replay_protocol.parent)
        closure = load(output/'runtime_closure.json')
        assert closure['all_owned_processes_closed'] and closure['owner_exit_code'] == 0
        assert Path(closure['runs_root']).resolve() == runs.resolve()
    factorial = protocol.get('native_factorial',False)
    independent_four = independent_four_protocol(protocol)
    if independent_four:
        closure = load(output/'runtime_closure.json')
        assert closure['all_owned_processes_closed'] and closure['owner_exit_code'] == 0
        assert Path(closure['runs_root']).resolve() == runs.resolve()
        assert load(runs/'chain_status.json')['phase'] == 'native_four_complete_unanalyzed'
    if factorial:
        for path,digest in protocol['command_pins'].items():assert sha256(Path(path))==digest,path
        if not independent_four:
            assert sha256(Path(protocol['prediction_source']))==protocol['prediction_sha256']
    reused=protocol.get('reuse_native_baseline')
    controlled_reuse=bool(reused and protocol.get('controlled_prefix'))
    reused_summary=None
    if reused:
        assert protocol['arms']==['selected'] and arms==('hold','selected')
        assert sha256(Path(reused['summary']))==reused['sha256']
        reused_summary=load(Path(reused['summary']))
        assert reused_summary['counterfactual_valid'] and reused_summary['paired_prefix_exact']
        for path,digest in protocol['command_pins'].items():assert sha256(Path(path))==digest,path
    if controlled_reuse:
        proof=protocol['controlled_prefix']
        if args.membership_json is not None:
            controlled_reuse_area(protocol, args.membership_json)
        assert sha256(Path(proof['execution']))==proof['execution_sha256']
        assert sha256(Path(proof['provenance']))==proof['provenance_sha256']
        baseline_execution=load(Path(proof['execution']))
        baseline_provenance=load(Path(proof['provenance']))
        assert baseline_execution['native_execution_passed'] and baseline_execution['terminal_sec']>=end
        assert baseline_execution['run_id']==baseline_provenance['run_id']
        assert Path(baseline_execution['run_directory']).resolve()==Path(reused['run']).resolve()
        names['hold']=baseline_provenance['name']
        closure=load(output/'runtime_closure.json')
        assert closure['all_owned_processes_closed'] and closure['owner_exit_code']==0
        assert Path(closure['runs_root']).resolve()==runs.resolve()
    profile_pair = observation_profile_pair(protocol) if args.replay_protocol else None
    rm_observation_pair = profile_pair is not None
    if profile_pair == 'vsl73':
        closure = load(output/'runtime_closure.json')
        assert closure['all_owned_processes_closed'] and closure['owner_exit_code'] == 0
        assert Path(closure['runs_root']).resolve() == runs.resolve()
        assert load(runs/'chain_status.json')['phase'] == 'complete_unanalyzed'
    selected_vsl_pair = bool(args.replay_protocol and protocol.get('arms')==['selected','vsl90'])
    if rm_observation_pair:
        for path,digest in protocol['command_pins'].items():
            assert sha256(Path(path))==digest, path
    ledger_path = args.membership_json or HERE.parent/'selected/scenario/control_area_membership_213a5d.json'
    ledger, membership, area_receipt = measurement_area(ledger_path)
    assert ledger['network']['sha256'] == protocol['network_sha256']
    terminals = terminal_lengths(ledger)
    summary = {'scope': scope,
               'start_sec': start, 'end_sec': end, 'recorded_run_end_sec': run_end, 'arms': {},
               'traffic_censored_before_run_end': traffic_censored,
               'reused_nc_run': str(args.nc_run_dir.resolve()) if args.nc_run_dir is not None else None,
               'whole_omega_gain_qualified': False, 'new_calibration': False,
               'physical_area': area_receipt}
    if closed_loop:
        summary['requested_run_period_sec_by_arm']={'nc':nc_run_end,'sdmpc':run_end}
    if stopped_evidence:
        summary.update(user_stop=stopped_evidence,requested_sim_period_sec=run_end,
                       recorded_run_end_sec=None,sdmpc_execution_verified_through_sec=end)
    if closed_loop:
        control_run=runs/'sdmpc';control_name=names['sdmpc']
        recovery=decision_recovery_evidence(control_run,control_name,
            load(control_run/f'run_provenance_{control_name}.json'),
            (control_run/f'runlog_{control_name}.txt').read_bytes().splitlines(),
            through_sec=end if args.user_stop_receipt else None)
        decisions = decision_summary(control_run/f'decisions_{control_name}', start, end,recovery=recovery)
        summary['decision_recovery']=recovery
        save(output/'sdmpc_decisions.json', decisions)
    original_prefix = None
    if selected_vsl_pair:
        original_prefix,proof=selected_vsl_prefix(protocol,args.recording_start_alignment)
        summary['original_prefix_source']=proof
    if profile_pair == 'vsl67':
        original_prefix, proof = previous_vsl67_prefix(protocol)
        summary['original_prefix_source'] = proof
    if controlled_reuse:
        baseline_fzp,=(Path(reused['run'])/'vissim_eval').glob('*.fzp')
        original_prefix=prefix_digest(baseline_fzp,start,recording_grid=(5,.1))
    elif reused:
        original_prefix=reused_summary['prefixes']['hold']
    elif not rm_observation_pair and not closed_loop and not selected_vsl_pair:
        original_run=(args.controlled_pair_source.parent if controlled_pair else
                      Path(protocol['original_run']) if args.replay_protocol else ORIGINAL)
        original_fzp, = (original_run/'vissim_eval').glob('*.fzp')
        original_prefix = prefix_digest(original_fzp, start, recording_grid=(5, .1))
    prefixes = {}
    common_start_records = None
    for arm in arms:
        if reused and arm=='hold' and not controlled_reuse:
            summary['arms'][arm]=reused_summary['arms']['hold']
            prefixes[arm]=reused_summary['prefixes']['hold']
            assert summary['arms'][arm]['native_execution_passed']
            save(output/arm/'reused_result.json',dict(source=reused,metrics=summary['arms'][arm],prefix=prefixes[arm],fzp_rescanned=False))
            continue
        baseline_window=controlled_reuse and arm=='hold'
        run = (Path(reused['run']) if baseline_window else
               args.nc_run_dir if arm == 'nc' and args.nc_run_dir is not None else runs/arm)
        name = names[arm]
        arm_run_end=nc_run_end if closed_loop and arm=='nc' else run_end
        if args.nc_run_dir is not None and arm == 'nc':
            assert not (run.parent/'STOP').exists(), 'Reused NC belongs to a stopped job'
            log = (run/f'runlog_{name}.txt').read_text(encoding='utf-8-sig').splitlines()
            assert 'STAGE=SIM_DONE' in log and f'SIM_SEC={arm_run_end}' in log, 'Reused NC is incomplete'
            assert f'OK {name} attempt=1 ' in (run/'launch.log').read_text(encoding='utf-8-sig')
        provenance = load(run/f'run_provenance_{name}.json')
        assert provenance['files']['network']['sha256'] == protocol['network_sha256']
        assert provenance['seed'] == protocol['seed']
        assert provenance['sim_period_sec']>=end if baseline_window else provenance['sim_period_sec']==arm_run_end
        if controlled_pair or (reused and not baseline_window) or factorial and not independent_four or selected_vsl_pair:
            decisions=run/f'decisions_{name}'
            for sec in (1,*range(150,end+1,150)):
                for suffix in ('.json','.csv'):
                    planned=args.replay_protocol.parent/arm/'commands'/f'action_{sec:06d}{suffix}'
                    assert sha256(decisions/planned.name)==sha256(planned),(arm,sec,suffix)
            baseline_dir=(args.controlled_pair_source if controlled_pair else
                          Path(protocol['common_prefix_source']) if selected_vsl_pair else
                          Path(reused['run'])/f'decisions_{names["hold"]}' if reused else
                          Path(protocol['original_run'])/'decisions_sdmpc31_sdmpc9000_s29')
            baseline_state=load(baseline_dir/f'state_{start:06d}.json')
            selected_state=load(decisions/f'state_{start:06d}.json')
            assert baseline_state['vehicle_records']['complete'] and selected_state['vehicle_records']['complete']
            assert baseline_state['vehicle_records']['records']==selected_state['vehicle_records']['records'],'Different actual initial vehicle state'
            summary['common_start_vehicle_records_exact']=True
            if controlled_reuse:
                for key in ('network','main_vbs_runner','control_mapping','demand_profile','vehicle_input_roles',
                            'urban_input_gate_map','signal_group_plan'):
                    assert provenance['files'][key]['sha256']==baseline_provenance['files'][key]['sha256'],key
        if rm_observation_pair:
            decisions=run/f'decisions_{name}'
            initial = load(decisions/f'state_{start:06d}.json')
            assert initial['sim_sec'] == start and initial['vehicle_records']['complete']
            records = initial['vehicle_records']['records']
            if common_start_records is None:
                common_start_records = records
            assert records == common_start_records, 'Observation pair has different initial vehicle states'
            summary['common_start_vehicle_records_exact'] = True
            for sec in (1,*range(150,end+1,150)):
                for suffix in ('.csv','.json'):
                    planned=args.replay_protocol.parent/arm/'commands'/f'action_{sec:06d}{suffix}'
                    assert sha256(decisions/planned.name)==sha256(planned), (arm,sec,suffix)
            log=(run/f'runlog_{name}.txt').read_bytes().splitlines()
            assert b'STAGE=SIM_DONE' in log and f'SIM_SEC={end}'.encode('ascii') in log
            native=[line for line in log if line.startswith(b'PROFILE_NATIVE_SIGNAL_READBACK ')]
            expected=[f'PROFILE_NATIVE_SIGNAL_READBACK sim_sec={sec} checked=160 non_native=0 missing=0'.encode('ascii')
                      for sec in (1,end)]
            assert native==expected, 'Native urban signal ownership missing at initialization or termination'
        out = output/arm
        stopped_arm=bool(args.user_stop_receipt and arm=='sdmpc')
        execution = baseline_execution if baseline_window else verify_native_execution(
            run, end if stopped_arm else arm_run_end, run_name=name,
            user_stop_receipt=args.user_stop_receipt if stopped_arm else None)
        save(out/'execution.json', execution)
        if args.replay_protocol or closed_loop:
            assert execution['native_execution_passed'], f'Native execution failed: {out}'
        errors = []
        events = []
        for p in ([] if baseline_window else sorted(run.rglob('*.err'))):
            parsed = parse_bytes(p.read_bytes())
            assert not parsed['unparsed_removal_lines'], str(p)
            if traffic_censored:
                parsed['events'] = traffic_events_through(parsed['events'], end)
                parsed['counts'] = dict(Counter(e['kind'] for e in parsed['events']))
                parsed['unparsed'] = traffic_events_through(parsed['unparsed'], end)
                parsed['traffic_end_sec'] = end
                parsed['terminal_uninserted_count_unavailable'] = True
            errors.append({'path': str(p), 'sha256': sha256(p), **parsed})
            events.extend(parsed['events'])
        # Some native .err files are copied into the run root: count each event once.
        events = [json.loads(s) for s in sorted({json.dumps(e, sort_keys=True) for e in events})]
        if baseline_window:
            cached_errors=Path(proof['execution']).parent/'native_errors.json'
            events=[e for e in load(cached_errors)['unique_events']
                    if e.get('kind')!='unfinished_vehicle_input' and e.get('time_sec',0)<=end]
            errors=[dict(reused_source=str(cached_errors),sha256=sha256(cached_errors),
                         truncated_at_sec=end,terminal_uninserted_count_unavailable=True)]
        removals = {str(e['vehicle_id']): e for e in events if e['kind'] == 'lane_change_removal'}
        save(out/'native_errors.json', {'files': errors, 'unique_events': events})
        fzp, = (run/'vissim_eval').glob('*.fzp')
        prefixes[arm] = original_prefix if baseline_window else prefix_digest(fzp, start, recording_grid=(5, .1))
        before = fzp.stat()
        previous = None

        def audited_frames():
            nonlocal previous
            for frame in read_fzp_frames(fzp):
                if frame.time_sec>end:break  # Reused longer run: never account later traffic.
                if previous:
                    dt = frame.time_sec - previous.time_sec
                    for no in previous.vehicles.keys() - frame.vehicles.keys():
                        v = previous.vehicles[no]
                        if no in removals and v.link in terminals:
                            reach = v.speed_kph/3.6*dt + 1.5*dt*dt + 10
                            overshoot = v.speed_kph/3.6*.1 + .015 + 10
                            assert not -overshoot <= terminals[v.link]-v.position_m <= reach, (
                                'Explicit removal would be counted as terminal TTD', no)
                previous = frame
                yield frame

        metrics, times = measure_frames(audited_frames(), membership, terminals,
                                       end_sec=end, simulation_step_sec=.1, include_distance=True)
        after = fzp.stat()
        assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
        assert metrics['sampling']['nominal_step_sec'] == 5 and metrics['sampling']['missing_snapshot_gaps'] == 0
        save(out/'area_metrics.json', metrics)
        table(out/'area_timeseries.csv', times)
        if baseline_window:
            cached_path=Path(proof['execution']).parent/'area_timeseries.csv'
            with cached_path.open(encoding='utf-8-sig',newline='') as stream:
                cached={float(r['sim_sec']):r for r in csv.DictReader(stream)}
            checked=0
            for row in times:
                if row['sim_sec']==end:continue  # Newly censored final tail, not the old9000 endpoint.
                old=cached[row['sim_sec']]
                assert all(abs(float(old[key])-row[key])<1e-8 for key in (
                    'inside_vehicles','outside_vehicles','ttt_veh_h_cumulative','ttd_observed_plus_terminal_cumulative'))
                checked+=1
            save(out/'reused_window.json',dict(source=reused,execution_receipt=proof['execution'],
                execution_validated_through_sec=baseline_execution['terminal_sec'],
                traffic_read_through_sec=end,cached_timeseries_sha256=sha256(cached_path),
                unchanged_cached_samples=checked,full9000_traffic_reanalysis=False))
        at_start = next(r for r in times if abs(r['sim_sec']-(start+.1)) < 1e-7)
        row = {'native_execution_passed': execution['native_execution_passed'],
               'lsa_passed': execution['native_lsa_com_coverage_passed'],
               f'TTT_0_{end}_veh_h': metrics['ttt_veh_h'],
               f'TTT_{start}p1_{end}_veh_h': metrics['ttt_veh_h']-at_start['ttt_veh_h_cumulative'],
               'Omega_TTD_events': metrics['ttd_observed_plus_terminal_events'],
               'Omega_end_vehicles': metrics['censored_last_observed_inside_vehicles'],
               'native_removals': len(removals),
               'uninserted_at_end': None if baseline_window or traffic_censored else sum(e['remaining_vehicles'] for e in events if e['kind']=='unfinished_vehicle_input'),
               'unresolved_Omega_disappearances': metrics['unresolved_inside_disappearances'],
               'outside_Omega_residence_veh_h': sum(r['ttt_veh_h'] for r in metrics['physical_link_residence'].values() if not r['inside']),
               'last_fzp_sec': metrics['boundaries']['last_fzp_sec'],
               'tail_hold_veh_h': metrics['ttt_censored_tail_extrapolation_veh_h']}
        row.update(sampled_TVD_Omega_veh_km=metrics['distance']['sampled_tvd_omega_veh_km'],
                   sampled_TVD_censored_tail_veh_km=metrics['distance']['censored_tail_hold_veh_km'],
                   distance_definition=metrics['distance']['definition'])
        if not baseline_window and not traffic_censored and (args.closed_loop_9000 or (run/'native_network_performance.json').exists()):
            row.update(native_network_cost(run, end))
        summary['arms'][arm] = row
        print(json.dumps({arm: row}), flush=True)
    a, b = (summary['arms'][arm] for arm in arms[:2])
    summary.update(prefixes=prefixes, original_prefix=original_prefix,
                   paired_prefix_exact=all(v==prefixes[arms[0]] for v in prefixes.values()),
                   original_initial_history_exact=(all(x==original_prefix for x in prefixes.values())
                                                   if original_prefix is not None else None),
                   delta_definition=f'{arms[1]} minus {arms[0]}',
                   delta_TTT_veh_h=b[f'TTT_0_{end}_veh_h']-a[f'TTT_0_{end}_veh_h'],
                   delta_outside_Omega_residence_veh_h=b['outside_Omega_residence_veh_h']-a['outside_Omega_residence_veh_h'],
                   limitations=['5s sampled residence; final4.9s holds last observed stock.',
                                'Urban signals and freeway commands are jointly controlled; not VSL-only attribution.',
                                'Native whole-network time and sampled Omega time have different scopes and must not be substituted.',
                                'Completion of a simulation does not establish controller gain or independent-seed robustness.',
                                'Native LSA coverage failure remains separate; user authorized LDP as execution evidence.'])
    key = 'native_total_time_including_uninserted_veh_h'
    if key in a and key in b:
        summary['delta_native_total_time_including_uninserted_veh_h'] = b[key]-a[key]
        summary['delta_native_uninserted_delay_veh_h'] = b['native_uninserted_delay_veh_h']-a['native_uninserted_delay_veh_h']
    else:
        summary['limitations'].append('Uninserted terminal count is not the external input-queue time integral; native delay is missing.')
    if traffic_censored:
        summary['limitations'].append(f'Traffic, exit/removal events and residual stock stop at{end}s. '
            +(f'SDMPC was explicitly user-stopped; command verification covers1..{end}s, not normal completion. '
              if stopped_evidence else f'Native completion and command verification retain{run_end}s. ')
            +f'Terminal uninserted count and whole-run cost are not{end}s measurements and are omitted.')
    if factorial:
        summary.update(protocol_path=str(args.replay_protocol),protocol_sha256=sha256(args.replay_protocol),
            prediction_source=None if independent_four else protocol['prediction_source'],
            predicted_delta_by_arm=None if independent_four else protocol['predicted_delta_by_arm'],
            comparisons={arm:dict(delta_TTT_veh_h=row[f'TTT_0_{end}_veh_h']-a[f'TTT_0_{end}_veh_h'],
                delta_outside_Omega_residence_veh_h=row['outside_Omega_residence_veh_h']-a['outside_Omega_residence_veh_h'],
                delta_native_total_time_including_uninserted_veh_h=row[key]-a[key] if key in row and key in a else None)
                for arm,row in summary['arms'].items()},
            counterfactual_valid=summary['paired_prefix_exact'] and (independent_four or summary['original_initial_history_exact'])
                and summary['common_start_vehicle_records_exact'] and all(r['native_execution_passed'] for r in summary['arms'].values()))
        summary['limitations'][1]='City signals/offset and other levers fixed. Factorial changes only10484 RM and VSL13 after the common2250 history. Primary legacy delta is rm_only minus held_actual; comparisons lists all arms.'
        if independent_four:
            summary['matched_prior_run_claimed'] = False
            summary['native_urban_ownership_readback_scope'] = 'Initialization and termination; pinned CSVs contain no urban writes, and native LDP verifies intervening states.'
            summary['limitations'][1] = 'Native city signals fixed; east four RM8/6/4 and/or DSD63..66 VSL90 after2250. Within-new-arm comparison; no older-run identity claim.'
            summary['limitations'].append('Common precontrol history does not imply identical future insertion counts or vehicle composition. Whole-run paired differences cancel the exact prefix; no separately sampled2250 native latent-delay checkpoint is claimed.')
    elif rm_observation_pair:
        summary.update(protocol_path=str(args.replay_protocol),protocol_sha256=sha256(args.replay_protocol),
            prediction_source=None,matched_prior_run_claimed=profile_pair=='vsl67',
            counterfactual_valid=summary['paired_prefix_exact'] and summary['common_start_vehicle_records_exact']
                and (profile_pair!='vsl67' or summary['original_initial_history_exact']),
            native_urban_ownership_readback_scope='Initialization and termination; no per-decision ownership readback claimed. Every actual CSV is checked against the pinned plan without urban rows; native LDP covers the intervening states.')
        summary['limitations'][1]='Only10484 RM changes after the common paired prefix; native urban signals and VSL110 held. No original fast-run trajectory identity claimed.'
        if profile_pair == 'vsl67':
            summary['limitations'][1]='OnlyDSD63..66 change110to90 after2700. Both arms use identical RM release schedules and native urban signals. Original67 prefix proof is reused; its2670.1-to3120.1 cost interval is not substituted for this2700-to3150 comparison.'
        if profile_pair == 'vsl73':
            summary['replication_seed'] = 73
            summary['limitations'][1]='Seed73 VSL110/90 at DSD63..66 after2700 with identical RM release schedules and native city signals. Common initial state is within seed73; no seed67 trajectory identity claim.'
            summary['limitations'].append('One fresh seed is not a statistical robustness result; future source admissions and composition may differ after intervention.')
    elif selected_vsl_pair:
        summary.update(protocol_path=str(args.replay_protocol),protocol_sha256=sha256(args.replay_protocol),
            prediction_source=protocol['prediction_source'],predicted_delta_omega_veh_h=protocol['predicted_delta_omega_veh_h'],
            counterfactual_valid=summary['paired_prefix_exact'] and summary['original_initial_history_exact']
                and summary['common_start_vehicle_records_exact'] and all(r['native_execution_passed'] for r in summary['arms'].values()))
        summary['limitations'][1]='Same selected SDMPC city/RM sequence; only DSD63..66 differ110vs90 after2700. Original observed2700 state and qualified new67 prefix required. No independent-seed claim.'
    elif controlled_reuse:
        prediction=load(Path(protocol['prediction_summary']))
        predicted_fields, reuse_limitations = controlled_reuse_metadata(protocol, prediction, baseline_execution['terminal_sec'])
        summary.update(protocol_path=str(args.replay_protocol),protocol_sha256=sha256(args.replay_protocol),
            prediction_source=protocol['prediction_summary'],
            **predicted_fields,
            counterfactual_valid=summary['paired_prefix_exact'] and summary['original_initial_history_exact']
                and summary['common_start_vehicle_records_exact'] and all(r['native_execution_passed'] for r in summary['arms'].values()))
        summary['limitations'][1] = reuse_limitations[0]
        summary['limitations'].extend(reuse_limitations[1:])
    elif controlled_pair:
        summary.update(protocol_path=str(args.replay_protocol),protocol_sha256=sha256(args.replay_protocol),
            controlled_pair_context=controlled_context,
            prediction_source=controlled_context['prediction_path'],
            predicted_delta_omega_veh_h=controlled_context['predicted_delta_omega_veh_h'],
            counterfactual_valid=summary['paired_prefix_exact'] and summary['original_initial_history_exact']
                and summary['common_start_vehicle_records_exact']
                and all(row['native_execution_passed'] for row in summary['arms'].values()))
        summary['limitations'][1]='Held physical commands versus a previously selected city/RM three-block sequence after the identical observed prefix. No reoptimization during replay; not RM-only attribution or closed-loop performance.'
    elif args.replay_protocol:
        summary.update(protocol_path=str(args.replay_protocol),protocol_sha256=sha256(args.replay_protocol),
            prediction_source=protocol['prediction_source'],
            predicted_delta_omega_veh_h=protocol['predicted_delta_omega_veh_h'],
            predicted_delta_tracked_total_veh_h=protocol['predicted_delta_tracked_total_veh_h'],
            counterfactual_valid=summary['paired_prefix_exact'] and summary['original_initial_history_exact'])
        summary['limitations'][1]=('Selected city/RM commands after native urban prefix; baseline metrics reused from the pinned completed hold.'
                                   if reused else 'Only the protocol VSL zone changes after the common prefix; city signals,offset and all RM commands are held.')
    if closed_loop:
        summary['counterfactual_valid'] = summary['paired_prefix_exact'] and all(
            row['native_execution_passed'] for row in summary['arms'].values())
    save(output/'summary.json', summary)
    if closed_loop:
        assert summary['counterfactual_valid'], 'Closed-loop matched NC prefix differs; preserve results but reject paired gain comparison'
    if args.replay_protocol:
        assert summary['counterfactual_valid'], 'Replay does not recover the same initial microscopic history; result is not a valid paired effect'
    if independent_four:
        receipt_path = output/'observation_reuse.json'
        assert not receipt_path.exists(), 'Preserve completed observation binding'
        state_path = runs/'nc'/f'decisions_{names["nc"]}'/'state_002250.json'
        receipt = dict(passed=True, seed=71, prefix_cutoff_sec=2250,
            scope='Independent seed71 fixed-control response; future observations are evaluation targets only.',
            independent_four_arm=True, recording_dir=str(state_path.parent),
            state=dict(path=str(state_path),sha256=sha256(state_path)),
            native_execution_passed=all(row['native_execution_passed'] for row in summary['arms'].values()),
            precontrol_prefix_exact=summary['paired_prefix_exact'],
            native_summary=dict(path=str(output/'summary.json'),sha256=sha256(output/'summary.json')),
            protocol=dict(path=str(args.replay_protocol),sha256=sha256(args.replay_protocol)),
            ledger=dict(path=str(ledger_path),sha256=sha256(ledger_path)),profiles={})
        for arm in ('rm','vsl','both'):
            path = args.replay_protocol.parent/f'{arm}_fixed_profile.json'
            digest = sha256(path)
            assert protocol['command_pins'][str(path)] == digest
            receipt['profiles'][arm] = dict(path=str(path),sha256=digest)
        save(receipt_path, receipt)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('arms','limitations')}), flush=True)


if __name__ == '__main__':
    main()
