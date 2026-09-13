"""Post-run only: qualify recorded closed-loop decisions and native execution.

Usage: python qualify_fast_np_closedloop.py RUN_NAME FRESH_RESULT_LABEL
       [--baseline RUN_NAME --start 900 --end 9000 --detail-start 4500]
No COM, model response, controller imports, or modification of run artifacts.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import traceback

D = Path(__file__).resolve().parent
ROOT = D.parents[3]
sys.path[:0] = [str(ROOT), str(ROOT/'reports/20260911_decision_runtime')]
import audit_fw8_rg_meter_response as meters
import audit_nuf_band_native as local

FIELDS = ('N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times',
          'offsets', 'inflow_outflow_allocation')
EXCLUSIONS = ('local_observation.signal_observation_window.config_sha256', 'network_path',
              'run_provenance.manifest_path', 'run_provenance.run_id', 'sim_period_sec')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pin(path, pins, expected=None):
    path = Path(path).resolve()
    actual = meters.sha(path)
    require(expected is None or actual == expected, 'Changed recorded file: '+str(path))
    require(str(path) not in pins or pins[str(path)] == actual, 'Conflicting source pin: '+str(path))
    pins[str(path)] = actual
    return path


def read(path, pins):
    return meters.read_json(pin(path, pins))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def command_rows(path, pins):
    with pin(path, pins).open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    require(rows and all(None not in r and None not in r.values() for r in rows), 'Incomplete command CSV')
    return rows


def command_changes(before, after):
    # Compare actual written physical rows; segment-address additions in JSON
    # do not by themselves establish a changed actuator command.
    def signature(row):
        return tuple((key, value if key in ('kind', 'id') or value == '' else float(value))
                     for key, value in row.items() if key != 'metadata')
    kinds = sorted({r['kind'] for r in before+after})
    changes = {}
    for kind in kinds:
        left = Counter(signature(r) for r in before if r['kind'] == kind)
        right = Counter(signature(r) for r in after if r['kind'] == kind)
        changes[kind] = {'previous_rows': sum(left.values()), 'current_rows': sum(right.values()),
            'added_or_changed_rows': sum((right-left).values()),
            'removed_or_changed_rows': sum((left-right).values())}
    old = {r['id']: r for r in before if r['kind'] == 'ramp_meter'}
    ramps = []
    for row in after:
        if row['kind'] == 'ramp_meter':
            keys = ('green_sec', 'rate_vph', 'offset')
            ramps.append({'id': row['id'], 'sc_no': int(row['sc_no']),
                'previous': {k: old.get(row['id'], {}).get(k) for k in keys},
                'written': {k: row[k] for k in keys},
                'physical_row_changed': row['id'] not in old or signature(old[row['id']]) != signature(row)})
    return {'physical_rows_by_kind': changes, 'eight_written_meters': ramps,
            'any_physical_row_change': any(v['added_or_changed_rows'] or v['removed_or_changed_rows'] for v in changes.values())}


def decision(directory, sec, previous_rows, pins):
    stem = directory/f'action_{sec:06d}'
    action = read(stem.with_suffix('.json'), pins)
    joint = read(stem.with_suffix('.joint.json'), pins)
    budget = read(stem.with_suffix('.decision_budget.json'), pins)
    written = read(stem.with_suffix('.joint_written.json'), pins)
    rows = command_rows(stem.with_suffix('.csv'), pins)
    require(joint['completed'] is True and joint['sim_sec'] == sec and joint['source_changes'] == [], 'Failed/stale joint receipt')
    for path, digest in joint['source_sha256'].items():
        pin(path, pins, digest)
    require(budget['output_completed'] is True and budget['output_error'] is None, 'Failed final output receipt')
    require(written['phase'] == 'postwrite' and written['prewrite_binding_passed'] is True
            and written['written_command_binding_passed'] is True, 'Missing written-command binding')
    for key, suffix in (('action_json', '.json'), ('action_csv', '.csv')):
        require(Path(written[key]['path']).resolve() == stem.with_suffix(suffix).resolve(), 'Binding points to another action file')
        pin(written[key]['path'], pins, written[key]['sha256'])
    require(meters.sha(stem.with_suffix('.csv')) == written['expected_csv_sha256']
            and len(rows) == written['ordered_row_count'], 'CSV hash/row count differs from its own binding')
    physical = [tuple(v for k, v in r.items() if k != 'metadata') for r in rows]
    require(hashlib.sha256(canonical(physical)).hexdigest() == written['ordered_physical_rows_sha256'], 'Physical row binding mismatch')
    fields = {k: float(action[k]) if k in FIELDS[:2] else {a: float(v) for a, v in action[k].items()} for k in FIELDS}
    require(hashlib.sha256(canonical(fields)).hexdigest() == written['seven_action_fields_sha256'], 'Seven-field action binding mismatch')
    ramps = [r for r in rows if r['kind'] == 'ramp_meter']
    require(len(ramps) == 8 and {int(r['sc_no']) for r in ramps} == set(range(9101, 9109))
            and {r['id'] for r in ramps} == set(action['ramp_metering']), 'Incomplete eight-meter write')
    owners = {'SC'+r['sc_no'] for r in rows if r['kind'] == 'signal'}
    require(len(owners) == 17, 'Incomplete canonical urban owner commands')
    selection = joint['selection']
    require(selection['failure'] is None and selection['leader_domain_infeasible'] is False
            and selection['leader_optimum_certified'] is False, 'Failed selection or unsupported leader certificate')
    held = selection['selection_status'] == 'validated_actual_hold'
    shared = None if held else joint['selected_diagnostics']['joint_shared_response']
    quantity = selection['actual_hold_validation']['quantity_constraints'] if held else shared['quantity_constraints']
    require(quantity['schema'] == 'shared-quantity-constraints/v1' and quantity['feasible'] is True
            and quantity['nuf_definition'] == 'predicted_accepted_mainline_merge'
            and set(quantity['net_inflow_veh_by_owner']) == owners, 'Wrong/incomplete NP17/NUF quantity basis')
    require(quantity['window']['start_sec'] == sec and quantity['window']['end_sec'] == sec+450, 'Wrong held forecast window')
    actual_np = math.fsum(quantity['net_inflow_veh_by_owner'][o] for o in sorted(owners))
    merge = quantity['physical_ramp_merge']
    require(set(merge['rate_veh_h_by_ramp']) == set(action['ramp_metering'])
            and set(quantity['meter_rate_veh_h_by_owner']) == {'FW_E', 'FW_W'}
            and merge['rate_veh_h_by_owner'] == quantity['meter_rate_veh_h_by_owner'], 'Incomplete predicted physical merges')
    actual_nuf = math.fsum(merge['rate_veh_h_by_ramp'].values())
    for key, actual, mode, target_key in (('np', actual_np, 'cap', 'N_P_star'), ('nuf', actual_nuf, 'equality', 'N_UF_star')):
        q = quantity[key]
        require(all(type(v) in (int, float) and math.isfinite(v) for v in (actual, q['target'], q['tolerance']))
                and q['tolerance'] >= 0, 'Nonfinite quantity constraint')
        residual = actual-q['target']
        violation = max(0., residual) if key == 'np' else abs(residual)
        require(q['mode'] == mode and q['target'] == action[target_key] and q['actual'] == actual
                and q['residual'] == residual and q['violation'] == violation
                and q['constraint_checked'] is True and q['satisfied'] is True
                and violation <= q['tolerance'], 'Invalid frozen '+key+' constraint')
    require(quantity['nuf']['tolerance'] == 40., 'Unexpected NUF band')
    init = selection['actual_hold_validation']['nuf_initialization']
    require(init['start_sec'] == sec and init['end_sec'] == sec+450
            and init['physical_commands_unchanged'] is True and init['target_veh_h'] == action['N_UF_star'], 'NUF target differs from decision entry')
    attempted = [selection['candidates'][i] for i in selection['attempted_indices']]
    require(all(r['target_nuf_veh_h'] == action['N_UF_star'] for r in attempted), 'NUF target changed within the decision')
    gap = {'response_kind': 'validated_actual_hold', 'nash_result': False,
           'final_check_complete': False, 'maximum_finite_candidate_gap': None} if held else {
        k: shared[k] for k in ('finite_neighborhood_certified', 'final_check_complete',
            'maximum_finite_candidate_gap', 'search_status', 'error', 'evaluations')}
    if shared is not None:
        require(shared['final_action_token'] == written['scored_action_token'], 'Scored action token differs from writer')
        per_owner = shared['per_owner']
        require(set(per_owner) == owners | {'FW_E', 'FW_W'}, 'Incomplete finite-gap owner catalog')
        require(all(r['gap'] is None for r in per_owner.values() if not r['complete']), 'Incomplete gap presented as known')
        require(not shared['finite_neighborhood_certified'] or shared['final_check_complete'], 'False finite-neighborhood certificate')
        require(shared['native_plant_feasibility_certified'] is False and shared['legacy_residuals_computed'] is False
                and shared['leader_target_changed'] is False, 'Unsupported final response claim')
        if shared['final_check_complete']:
            require(all(r['complete'] for r in per_owner.values())
                    and shared['maximum_finite_candidate_gap'] == max(r['gap'] for r in per_owner.values()), 'Inconsistent complete gap audit')
        else:
            require(shared['maximum_finite_candidate_gap'] is None, 'Unfinished audit has a claimed maximum gap')
        gap['complete_owner_count'] = sum(r['complete'] for r in per_owner.values())
        gap['owner_count'] = len(per_owner)
    return {'sec': sec, 'selection_status': selection['selection_status'], 'stop_reason': selection['stop_reason'],
        'selected_index': selection['selected_index'], 'attempted_count': len(attempted),
        'unknown_candidate_count': len(selection['unknown_candidate_indices']), 'model_quantity_constraints': quantity,
        'decision_entry_nuf_target_veh_h': init['target_veh_h'], 'fixed_nuf_this_decision': True,
        'written_command_binding': written, 'decision_budget': budget, 'gap_coverage': gap,
        'changes_from_previous_written_action': command_changes(previous_rows, rows),
        'forecast_quality_or_actual_nuf_attainment_certified': False, 'GNE_certified': False}, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name')
    parser.add_argument('label')
    parser.add_argument('--baseline', default='codex_physical8_fw080_u050_open1350_v1')
    parser.add_argument('--start', type=int, default=900)
    parser.add_argument('--end', type=int, default=1350)
    parser.add_argument('--detail-start', type=int)
    args = parser.parse_args()
    name, label = args.name, args.label
    start, end = args.start, args.end
    detail_start = start if args.detail_start is None else args.detail_start
    detail_end = min(detail_start+450, end)
    require(start >= 150 and start < end and start % 150 == end % 150 == 0,
            'Use positive control-aligned start/end boundaries')
    require(start <= detail_start < end and detail_start % 150 == 0,
            'Detail window must begin on a control boundary inside the run')
    require(Path(name).name == name and Path(label).name == label, 'Use a run name and fresh result label')
    target = D/(label+'.json')
    if target.exists():
        raise FileExistsError(target)
    started = time.perf_counter()
    report = {'completed': False, 'decisions': {}, 'source_pins': {},
        'scope': 'Completed native closed loop; all recorded decisions are checked. Each 450s model constraint stays separate from realized traffic. Detailed trajectory analysis is limited to the named window. No GNE, global bound, or native capacity certificate.',
        'control_window_sec': [start, end], 'detail_window_sec': [detail_start, detail_end]}
    pins = report['source_pins']
    try:
        for path in (__file__, meters.__file__, local.__file__, meters.WINDOWS.__file__):
            pin(path, pins)
        meters.START, meters.END = start, end
        base = meters.load_run(args.baseline)
        run = meters.load_run(name)  # Both completion/closed-process guards precede trajectory reads.
        for item in (base, run):
            pins.update(item['pins'])
        require(base['meters'] == run['meters'] and base['provenance']['seed'] == run['provenance']['seed'], 'Paired geometry/seed differ')
        for key in ('network', 'demand_profile'):
            require(base['provenance']['files'][key]['sha256'] == run['provenance']['files'][key]['sha256'], 'Paired '+key+' differs')
        receipt = read(run['directory']/'completion_receipt.json', pins)
        checks = receipt['native_execution_verification']['checks']
        report['native'] = {'completed': receipt['completed'], 'terminal_sec': receipt['terminal_sec'],
            'execution_passed': receipt['native_execution_passed'],
            'independent_lsa_com_coverage_passed': receipt['native_lsa_com_coverage_passed'],
            'checks': {k: v['passed'] for k, v in checks.items()}, 'errors': receipt['errors'],
            'error_files': receipt['error_files'], 'lsa_scope': checks['native_lsa'].get('limitation')}
        require(receipt['native_execution_passed'] is True and receipt['errors'] == [], 'Native execution failure')
        for row in receipt['error_files']:
            pin(row['path'], pins, row['sha256'])
        for key in ('actual_signal_readbacks', 'actual_vsl_apply_readbacks', 'native_lsa'):
            row = checks[key]
            pin(row['path'], pins, row['sha256'])
        for path, row in checks['native_ldp']['pins'].items():
            pin(path, pins, row['sha256'])
        for row in checks['sources_and_terminal_log']['native_source_pins'].values():
            pin(row['path'], pins, row['sha256'])
        # Streaming readers still stop at the explicitly named windows. Their
        # byte guard must allow a longer warmup/high-density window than the
        # original 900-second fixture; this does not load the FZP into memory.
        read_budget = max(item['fzp'].stat().st_size for item in (base, run))+1024*1024
        meters.START, meters.END = 1, start
        report['warmup_prefix'] = meters.first_raw_difference(base, run, max_bytes=read_budget)
        require(report['warmup_prefix']['all_raw_data_rows_equal']
                and report['warmup_prefix']['equal_rows_before_difference'] > 0, 'Warmup FZP prefix differs or is empty')
        states = []
        for item in (base, run):
            state = read(item['directory']/('decisions_'+item['name'])/f'state_{start:06d}.json', pins)
            for key in EXCLUSIONS:
                parent = state
                parts = key.split('.')
                for part in parts[:-1]:
                    parent = parent[part]
                parent.pop(parts[-1], None)
            states.append(state)
        report['state_identity_exclusions'] = EXCLUSIONS
        report['initial_observations_and_head_history_exact'] = states[0] == states[1]
        if start == 900:
            report['initial900_observations_and_head_history_exact'] = states[0] == states[1]
        require(states[0] == states[1], 'Initial observations/head history differ')
        directory = run['directory']/('decisions_'+name)
        previous = command_rows(directory/f'action_{start-150:06d}.csv', pins)
        for sec in range(start, end+1, 150):
            report['decisions'][str(sec)], previous = decision(directory, sec, previous, pins)
        report['native_ramps_by150s'] = {}
        for sec in range(detail_start, detail_end, 150):
            meters.START, meters.END = sec, sec+150
            report['native_ramps_by150s'][str(sec)] = {key: meters.collect(item, max_bytes=read_budget) for key, item in (('baseline', base), ('closedloop', run))}
        # Cache the exact events needed for a later head-to-exit/startup-lag audit.
        for item in (base, run):
            pin(item['directory']/'vissim_eval/baseline_1004_001.ldp', pins)
        report['sc1004'] = {key: local.signal_window(item, sc=1004, start=detail_start, end=detail_end, max_bytes=read_budget)
                           for key, item in (('baseline', base), ('closedloop', run))}
        report['corridor_52_66_71'] = {key: local.corridor_window(item, roads=[52, 66, 71], start=detail_start, end=detail_end, max_bytes=read_budget)
                                     for key, item in (('baseline', base), ('closedloop', run))}
        for item in (base, run):
            for path, digest in item['pins'].items():
                pin(path, pins, digest)
        report['completed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        report['source_changes'] = [p for p, digest in pins.items() if not Path(p).exists() or meters.sha(p) != digest]
        report['completed'] = report['completed'] and not report['source_changes']
        report['wall_sec'] = time.perf_counter()-started
        with target.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
        print(json.dumps({'completed': report['completed'], 'result': str(target),
            'qualified_decisions': len(report['decisions']), 'wall_sec': report['wall_sec'],
            'source_changes': report['source_changes'], 'error': report.get('error')}))
    return 0 if report['completed'] else 1


if __name__ == '__main__':
    sys.exit(main())
