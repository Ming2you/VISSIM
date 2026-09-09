"""Read-only first150sec command/readback audit; never connects to VISSIM."""
from collections import Counter, defaultdict
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.controllers import signal_group_plan, plant_cycle
from evaluation.controllers import vissim_stackelberg_adapter as adapter

START, END = 900, 1050


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state_at(controller, sg, second, amber):
    cycle = controller['axis_cycle_sec']
    shifted = second + controller['offset_sec']
    pos = shifted - math.floor(shifted/cycle)*cycle
    windows = controller['windows']
    green = any(low <= pos < high for low, high in windows.get(sg, []))
    if green:
        return 'GREEN'
    any_green = any(low <= pos < high for group in windows.values() for low, high in group)
    if not any_green:
        for _, high in windows.get(sg, []):
            if high <= pos < high+amber or (high+amber > cycle and pos < high+amber-cycle):
                return 'AMBER'
    return 'RED'


def audit(run_name='codex_signal_zero_s13_20260910', config='diagnostics/signal_profile_config_zero.json'):
    RUN = ROOT/'evaluation/runs'/run_name
    DECISIONS = RUN/f'decisions_{run_name}'
    config_path = ROOT/config
    tuning = json.loads(config_path.read_text(encoding='utf-8'))
    profile = tuning['diagnostic']['signal_profile']
    frozen_path = ROOT/profile['green_action_json']
    frozen = json.loads(frozen_path.read_text(encoding='utf-8'))
    source_path = ROOT/frozen['source_action_json']
    source = json.loads(source_path.read_text(encoding='utf-8'))
    pure_path = ROOT/'evaluation/runs/codex_n7_pure_s13_20260910/decisions_codex_n7_pure_s13_20260910/action_002100.json'
    pure = json.loads(pure_path.read_text(encoding='utf-8'))
    action_path = DECISIONS/'action_000900.json'
    action = json.loads(action_path.read_text(encoding='utf-8'))
    provenance_path = RUN/f'run_provenance_{run_name}.json'
    provenance = json.loads(provenance_path.read_text(encoding='utf-8'))
    env_blocks = [value for value in provenance.values() if isinstance(value, dict) and 'RW_MAINLINE_SG_ONLY' in value]
    if len(env_blocks) != 1 or env_blocks[0]['RW_MAINLINE_SG_ONLY'] != '1':
        raise ValueError('This audit requires recorded RW_MAINLINE_SG_ONLY=1')
    csv_path = DECISIONS/'action_000900.csv'
    rows = list(csv.DictReader(csv_path.open(encoding='utf-8-sig', newline='')))
    adapter.install_config_switches(tuning)
    plan = adapter.load_signal_group_actuation_plan()
    plan_hash = hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    if plan_hash != profile['plan_content_sha256']:
        raise ValueError('Effective phase plan differs from the pinned diagnostic plan')
    recorded_hash_matches = {key: sha(Path(provenance['files'][key]['path'])) == provenance['files'][key]['sha256']
                             for key in ('main_vbs_runner', 'adapter', 'tuning', 'control_mapping', 'generated_vbs_config')}
    if not all(recorded_hash_matches[key] for key in ('tuning','control_mapping','generated_vbs_config')):
        raise ValueError(f'Pinned command input changed since recorded provenance: {recorded_hash_matches}')
    source_resolution = {}
    for key in ('main_vbs_runner','adapter'):
        if recorded_hash_matches[key]:
            source_resolution[key]={'status':'current_file_exact_hash'}
            continue
        relative=Path(provenance['files'][key]['path']).relative_to(ROOT).as_posix()
        commit=provenance['workspace_git_commit']
        archive=subprocess.run(['git','show',commit+':'+relative],cwd=ROOT,capture_output=True)
        candidates={}
        if archive.returncode==0:
            normalized=archive.stdout.replace(b'\r\n',b'\n')
            candidates={'git_blob':hashlib.sha256(archive.stdout).hexdigest(),
                        'git_blob_as_crlf':hashlib.sha256(normalized.replace(b'\n',b'\r\n')).hexdigest()}
        recorded=provenance['files'][key]['sha256']
        matched=[name for name,value in candidates.items() if value==recorded]
        source_resolution[key]={'status':'historical_hash_verified' if matched else 'historical_raw_hash_unresolved',
                                'commit':commit,'recorded_sha256':recorded,'candidate_sha256':candidates,'matched':matched}
    amber, all_red = plant_cycle.runner_clearance_sec()
    signals = {row['sc_no']: row for row in rows if row['kind'] == 'signal'}
    sg_rows = [row for row in rows if row['kind'] == 'signal_sg']
    expected_controllers = {key.removeprefix('SC') for key in tuning['config_overrides']['network']['signals']}
    if set(signals) != expected_controllers or len(signals) != 17:
        raise ValueError('Command controller coverage differs from configured17SC')
    command_errors, controllers = [], {}
    for sc, signal in signals.items():
        node = plan['controllers'][sc]
        greens = {key: float(signal[key+'_green']) for key in signal_group_plan.MODEL_PHASES}
        raw_targets = {key: ((plant_cycle.written_axis_green_sec(frozen['green_times'][f'SC{sc}_{key}'])
                             if frozen['green_times'][f'SC{sc}_{key}'] > 0 else 0.)
                            + float(profile.get('green_delta_sec', {}).get(f'SC{sc}_{key}', 0))) for key in greens}
        intended_green = {key: round(value, 3) for key, value in raw_targets.items()}
        intended_cycle = sum(raw_targets.values()) + sum(value > 0 for value in raw_targets.values())*(amber+all_red)
        intended_offset = (float(profile.get('base_writer_offsets_sec', {}).get('SC'+sc, 0))
                           + float(profile.get('relative_offset_sec', {}).get('SC'+sc, 0))) % intended_cycle
        if greens != intended_green:
            command_errors.append({'sc': sc, 'kind': 'frozen_green_mismatch', 'actual': greens, 'expected': intended_green})
        expected_order = signal_group_plan.phase_layout_order(node['major_maps_to'])
        expected_windows = signal_group_plan.plan_windows(signal_group_plan.node_plan_from_json(node), greens, expected_order, amber, all_red)
        expected = {(str(window.sg_no), int(window.window_index)): (round(window.start_sec, 3), round(window.end_sec, 3)) for window in expected_windows}
        actual, windows, cycles = {}, defaultdict(list), set()
        for row in sg_rows:
            if row['sc_no'] != sc:
                continue
            group = row['dsd_no']
            window_index = int(row['id'].rsplit('_W', 1)[1])
            bounds = (float(row['p1_green']), float(row['p2_green']))
            actual[(group, window_index)] = bounds
            windows[group].append(bounds)
            cycles.add(float(row['green_sec']))
            if not math.isclose(float(row['offset']), round(intended_offset, 3), abs_tol=1e-9):
                command_errors.append({'sc': sc, 'kind': 'incorrect_sg_offset', 'row': row['id']})
        if actual != expected:
            command_errors.append({'sc': sc, 'kind': 'SG_phase_window_mismatch'})
        cycle = sum(greens.values()) + sum(value > 0 for value in greens.values())*(amber+all_red)
        if len(cycles) != 1 or not math.isclose(next(iter(cycles)), cycle, abs_tol=1e-9):
            command_errors.append({'sc': sc, 'kind': 'cycle_mismatch'})
        if (not math.isclose(float(signal['offset']), round(intended_offset, 3), abs_tol=1e-9)
                or not math.isclose(action['offsets']['SC'+sc], intended_offset, abs_tol=1e-9)):
            command_errors.append({'sc': sc, 'kind': 'incorrect_signal_offset'})
        # Runner IsControlledSignalGroup filters all SG>8 with this recorded flag,
        # including native red-only groups, not only named pedestrian groups.
        groups = {str(group) for group in node['window_counts'] if int(group) <= 8}
        controllers[sc] = {'axis_cycle_sec': cycle, 'sg_csv_cycle_sec': next(iter(cycles)), 'offset_sec': float(signal['offset']),
            'greens_sec': greens, 'major_maps_to': node['major_maps_to'], 'phase_order': list(expected_order),
            'windows': dict(windows), 'groups': sorted(groups, key=int), 'window_count': len(actual)}
    readback_path = DECISIONS/'signal_readback.csv'
    selected, hash_rows = [], []
    with readback_path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        for row in reader:
            second = float(row['sim_sec'])
            if second > END:
                break
            if second >= START:
                hash_rows.append(row)
                if row['sc_no'] in controllers:
                    selected.append(row)
    if not selected or max(float(row['sim_sec']) for row in selected) < END:
        raise ValueError('The first150sec readback interval is not fully available')
    record_errors, persistence_errors, intended_errors, immediate = [], [], [], defaultdict(dict)
    last, sample_counts = {}, Counter()
    coverage = defaultdict(set)
    for row in selected:
        second, sc, sg = int(float(row['sim_sec'])), row['sc_no'], row['sg_no']
        key = sc, sg
        stage = row['stage']; requested = row['requested_state'].upper(); actual = row['readback_state'].upper()
        sample_counts[sc, stage] += 1
        coverage[second, stage].add(key)
        if row['ok'] != '1' or requested != actual:
            record_errors.append(row)
        if stage == 'immediate':
            expected = state_at(controllers[sc], sg, second, amber)
            if actual != expected:
                intended_errors.append({**row, 'expected': expected})
            last[key] = actual
            immediate[key][second] = actual
        elif stage == 'post_step':
            if key in last and actual != last[key]:
                persistence_errors.append({**row, 'previous_immediate': last[key]})
    expected_pairs = {(sc, sg) for sc, node in controllers.items() for sg in node['groups']}
    coverage_errors = [{'second': second, 'stage': stage, 'missing': sorted(expected_pairs-present), 'extra': sorted(present-expected_pairs)}
                       for (second, stage), present in coverage.items() if present != expected_pairs]
    grid_errors, transitions, controller_results = [], [], []
    for sc, node in controllers.items():
        sg_stats = {}
        expected_event_times, observed_event_times = set(), set()
        for sg in node['groups']:
            timeline = immediate[(sc, sg)]
            if START not in timeline:
                raise ValueError(f'No initial signal readback at900 for{sc}/{sg}')
            held, green_count, previous = timeline[START], 0, None
            for second in range(START, END+1):
                if second in timeline:
                    held = timeline[second]
                expected = state_at(node, sg, second, amber)
                if held != expected:
                    grid_errors.append({'sc': sc, 'sg': sg, 'sec': second, 'held': held, 'expected': expected})
                if second < END and held == 'GREEN':
                    green_count += 1
                if previous is not None and expected != previous:
                    expected_event_times.add(second)
                    if second in timeline:
                        observed_event_times.add(second)
                    transitions.append({'sc': sc, 'sg': sg, 'sec': second, 'from': previous, 'to': expected,
                        'immediate_at_transition': second in timeline})
                previous = expected
            sg_stats[sg] = {'green_sec_in_900_1050': green_count, 'initial_state_at_900': timeline[START],
                'final_state_at_1050': held, 'immediate_samples': len(timeline)}
        controller_results.append({'sc': int(sc), **node, 'immediate_checks': sample_counts[sc, 'immediate'],
            'post_step_checks': sample_counts[sc, 'post_step'], 'integer_expected_event_times': sorted(expected_event_times),
            'missing_integer_event_times': sorted(expected_event_times-observed_event_times), 'by_sg': sg_stats})
    content = io.StringIO(newline='')
    writer = csv.DictWriter(content, fieldnames=fields, lineterminator='\n'); writer.writeheader(); writer.writerows(hash_rows)
    frozen_clamps = {key: {'raw_frozen_sec': value, 'action_json_sec': action['green_times'][key]}
        for key, value in frozen['green_times'].items() if not math.isclose(value, action['green_times'][key], abs_tol=1e-10)}
    source_csv_path = source_path.with_suffix('.csv')
    source_rows = list(csv.DictReader(source_csv_path.open(encoding='utf-8-sig', newline='')))
    relevant = lambda data: [{k: row[k] for k in row if k != 'metadata'} for row in data if row['kind'] in {'signal', 'signal_sg'}]
    result = {'scope': 'First integer-event150sec [900,1050], with immediate endpoint1050 checked. Read-only recorded files; no VISSIM connection.',
        'baseline': 'Additional audit observations affected the first n7 run; its t2100 green vector is frozen for this diagnostic. It is neither nativeNC nor pure-n7 baseline.',
        'source': {'config': str(config_path.relative_to(ROOT)), 'config_sha256': sha(config_path),
            'run_provenance': str(provenance_path.relative_to(ROOT)), 'run_provenance_sha256': sha(provenance_path),
            'RW_MAINLINE_SG_ONLY': env_blocks[0]['RW_MAINLINE_SG_ONLY'],
            'local_files_match_recorded_run_hashes': recorded_hash_matches,
            'historical_runtime_source_resolution': source_resolution,
            'frozen': str(frozen_path.relative_to(ROOT)), 'frozen_sha256': sha(frozen_path),
            'frozen_hash_matches_config': sha(frozen_path) == profile['green_action_sha256'],
            'original_action': str(source_path.relative_to(ROOT)), 'original_action_hash_matches_frozen': sha(source_path) == frozen['source_action_sha256'],
            'frozen_greens_match_source_action': frozen['green_times'] == source['green_times'],
            'frozen_greens_match_pure_n7': frozen['green_times'] == pure['green_times'],
            'pure_n7_different_phase_count': sum(not math.isclose(value, pure['green_times'][key], abs_tol=1e-10) for key, value in frozen['green_times'].items()),
            'action_csv': str(csv_path.relative_to(ROOT)), 'action_csv_sha256': sha(csv_path),
            'written_signal_rows_match_original_t2100_csv': relevant(rows) == relevant(source_rows),
            'effective_plan': str(adapter.signal_group_actuation_plan_path().relative_to(ROOT)),
            'effective_plan_content_sha256': plan_hash, 'effective_plan_matches_pinned_profile': plan_hash == profile['plan_content_sha256'],
            'readback': str(readback_path.relative_to(ROOT)), 'selected_readback_rows': len(hash_rows),
            'selected_rows_canonical_csv_sha256': hashlib.sha256(content.getvalue().encode()).hexdigest()},
        'summary': {'controllers': len(controllers), 'controlled_signal_groups': len(expected_pairs), 'SG_windows': len(sg_rows),
            'controlled_readback_rows': len(selected), 'immediate_checks': sum(value for (sc, stage), value in sample_counts.items() if stage == 'immediate'),
            'post_step_checks': sum(value for (sc, stage), value in sample_counts.items() if stage == 'post_step'),
            'command_errors': len(command_errors), 'readback_errors': len(record_errors), 'persistence_errors': len(persistence_errors),
            'intended_state_errors': len(intended_errors), 'group_coverage_errors': len(coverage_errors),
            'integer_grid_errors': len(grid_errors), 'integer_SG_transitions': len(transitions),
            'missing_transition_events': sum(not row['immediate_at_transition'] for row in transitions),
            'all_offsets_zero': all(node['offset_sec'] == 0 for node in controllers.values())},
        'runner_clearance_sec': {'amber': amber, 'all_red': all_red}, 'frozen_write_clamps': frozen_clamps,
        'configured_green_deltas_sec': profile.get('green_delta_sec', {}),
        'configured_relative_offsets_sec': profile.get('relative_offset_sec', {}),
        'controllers': sorted(controller_results, key=lambda row: row['sc']), 'integer_transitions': transitions,
        'errors': {'command': command_errors, 'readback': record_errors, 'persistence': persistence_errors, 'intended': intended_errors,
            'coverage': coverage_errors, 'integer_grid': grid_errors},
        'limits': ['Immediate and post_step checks prove recorded event endpoints and persistence to the next event. The event interior is not independently sampled.',
            'Integer held-state reconstruction verifies the intended event schedule; fractional transition timing is quantized upward to the next integer second.',
            '150.001-second written cycles retain absolute simulation time, so their nominal900-second wrap occurs at900.006 and is applied at901.',
            'This verifies actuator delivery for a fixed diagnostic vector, not performance benefit or equivalence to native/pure n7 signals.']}
    if any(row['status']=='historical_raw_hash_unresolved' for row in source_resolution.values()):
        result['limits'].append('Production source was integrated after this run. Recorded raw adapter/VBS hashes could not be recovered from the recorded git blob or uniform CRLF conversion; no historical byte-identity claim is made. Config, mapping, generated config and selected plan pins were verified, and the numeric command/readback event comparison was still performed.')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', default='codex_signal_zero_s13_20260910')
    parser.add_argument('--config', default='diagnostics/signal_profile_config_zero.json')
    parser.add_argument('--output', default='diagnostics/signal_zero_first_interval_audit.json')
    args = parser.parse_args()
    result = audit(args.run, args.config)
    (ROOT/args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'summary': result['summary'], 'source': result['source'], 'clamps': result['frozen_write_clamps']}, indent=2))
    if any(result['errors'].values()):
        raise SystemExit('Recorded signal profile audit FAILED')
