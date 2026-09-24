"""Closed-file native fixed-profile verification, including paired warmup FZP."""
import argparse
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
try:
    from .validate_native_signal_record import read_ldp_frames
except ImportError:
    from validate_native_signal_record import read_ldp_frames


def require(condition, message):
    if not condition:
        raise ValueError(message)


def rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def prefix_digest(path, cutoff, *, recording_grid=None):
    """All raw FZP data columns/rows through cutoff; ignore volatile headers only."""
    digest = hashlib.sha256()
    count, last = 0, None
    endpoint = Decimal(str(cutoff))
    previous_token = None
    if recording_grid is not None:
        interval, phase = map(lambda value: Decimal(str(value)), recording_grid)
        require(interval.is_finite() and phase.is_finite() and interval > 0 and 0 <= phase < interval,
                'Invalid native FZP recording grid')
        endpoint = ((endpoint - phase) // interval) * interval + phase
    with Path(path).open('rb') as stream:
        for line in stream:
            if not re.match(rb'^\d+(?:\.\d+)?;', line):
                continue
            token = line.split(b';', 1)[0]
            if token != previous_token:
                sec = Decimal(token.decode('ascii'))
                if sec > cutoff:
                    break
                require(last is None or sec >= last, 'Reordered FZP prefix')
                if recording_grid is not None:
                    require((sec - phase) % interval == 0, 'FZP sample is off the recorded native grid')
                    require(last is None or sec == last or sec - last == interval, 'Missing native FZP recording frame')
                previous_token = token
            digest.update(line.rstrip(b'\r\n') + b'\n')
            count += 1
            last = sec
    require(count > 0 and last == endpoint, 'Missing exact FZP prefix endpoint')
    return {'sha256': digest.hexdigest(), 'rows': count, 'last_time_s': float(last)}


def native_recording_grid(setup, resolution):
    """Derive actual output times from COM readback, without rounding timestamps."""
    def value(kind, name):
        selected = [r for r in setup if r['kind'] == kind and r['no'] == name]
        require(len(selected) == 1, 'Missing/duplicate native recording setup: ' + name)
        expected, actual = [Decimal(selected[0][k]) for k in ('expected', 'actual')]
        require(expected.is_finite() and actual.is_finite() and actual == expected,
                'Native recording setup readback differs: ' + name)
        return actual
    actual_resolution = value('native_simulation', 'SimRes')
    require(actual_resolution == resolution, 'Native resolution differs from explicit profile')
    steps = value('native_recording', 'VehRecResolution')
    start = value('native_recording', 'VehRecFromTime')
    interval = steps / actual_resolution
    require(interval in (1, 5) and start >= 0, 'Unsupported native recording interval/start')
    return interval, (start + 1 / actual_resolution) % interval


def native_record(folder, proof, end):
    stem = Path(proof['network']).stem
    groups = {int(k): v for k, v in proof['fixed_profile_proof']['ldp_signal_groups'].items()}
    files = {sc: Path(folder)/'vissim_eval'/f'{stem}_{sc}_001.ldp' for sc in groups}
    return read_ldp_frames(files, groups, 1, end)


def network_performance(path, end):
    return network_performance_records(rows(path), end)


def network_performance_records(records, end):
    names = {'DelayLatent', 'DemandLatent', 'TravTmTot', 'VehAct', 'VehArr'}
    require(len(records) == len(names) and {r['attribute'] for r in records} == names,
            'Missing/duplicate network performance metrics')
    result = {}
    for row in records:
        stamp, value = Decimal(row['sim_sec']), Decimal(row['value'])
        require(stamp.is_finite() and stamp == end and value.is_finite() and value >= 0,
                'Invalid network performance value/time')
        if row['attribute'] in ('DemandLatent', 'VehAct', 'VehArr'):
            require(value == value.to_integral_value(), 'Vehicle total is not integral')
        result[row['attribute']] = float(value)
    return result


def network_performance_checkpoints(path, times, final):
    records = rows(path)
    require(len(records) == 5*len(times), 'Missing/extra performance checkpoint rows')
    result = {}
    previous = None
    for t in times:
        group = [r for r in records if Decimal(r['sim_sec']) == t]
        value = network_performance_records(group, t)
        if previous is not None:
            require(all(value[k] >= previous[k] for k in ('DelayLatent', 'TravTmTot', 'VehArr')),
                    'Cumulative performance decreased between checkpoints')
        result[str(t)] = value
        previous = value
    if previous is not None:
        require(all(final[k] >= previous[k] for k in ('DelayLatent', 'TravTmTot', 'VehArr')),
                'Final cumulative performance precedes checkpoint')
    return result


def verify(prepared, run, reference=None):
    prepared, run = Path(prepared), Path(run)
    meta = json.loads((prepared/'prepared.json').read_text(encoding='utf-8-sig'))
    require(meta['mode'] == 'fixed_profile', 'Wrong prepared mode')
    proof = meta['fixed_profile_proof']
    end = int(meta['terminal_sec'])
    setup = rows(run/'readback.csv')
    grid = (native_recording_grid(setup, proof['native_resolution_probe'])
            if 'native_resolution_probe' in proof else None)
    for kind, expected in [('native_simulation', proof['saved_simulation_period_sec']),
                           ('fixed_simulation', proof['effective_simulation_period_sec'])]:
        selected = [r for r in setup if r['kind'] == kind and r['no'] == 'SimPeriod']
        require(len(selected) == 1 and float(selected[0]['expected']) == expected and float(selected[0]['actual']) == expected,
                'Missing/different saved or effective SimPeriod readback')
    rule_policy = prepared/'rule_policy.json'
    events = rows((run if rule_policy.exists() else prepared)/'fixed_events.csv')
    for event in events:
        if event['kind'] == 'vsl':
            value = float(event['value'])
            require(value.is_integer() and value > 0, 'VSL distribution ID must be a positive integer')
            event['value'] = str(int(value))
    if rule_policy.exists():
        policy = json.loads(rule_policy.read_text(encoding='utf-8'))
        proof['meter_schedules'] = {}
        first_meter_write = {}
        for event in events:
            if event['kind'] == 'meter':
                sc=event['no']
                first_meter_write[sc]=min(first_meter_write.get(sc,end),int(event['time_s']))
        for sec in range(meta['control_start_sec'], end, 150):
            decision = json.loads((run/f'decision_{sec}.json').read_text())
            require(decision['sec'] == sec and decision['arm'] == policy['rule']['arm'], 'Rule decision identity differs')
            if decision['arm'] in ('rm', 'both'):
                for mid, row in decision['meters'].items():
                    sc = str(policy['meters'][mid]['sc'])
                    required_active=row['green_sec']<10 or mid in decision['history'].get('states',{})
                    require(not required_active or (sc in first_meter_write and first_meter_write[sc]<=sec),
                            f'Missing meter activation at{sec}:{sc}')
                    # A planned g10 anchor can remain native OFF until its first
                    # actual COM activation. OFF is not an observed GREEN phase.
                    if sc not in first_meter_write or sec<first_meter_write[sc]:
                        continue
                    proof['meter_schedules'].setdefault(sc, []).append((sec, row['green_sec']))
    initial = rows(prepared/'fixed_initial.csv')
    readback = rows(run/'fixed_readback.csv')
    writes = [r for r in readback if r['phase'] == 'write']
    require(len(writes) == len(events), 'Missing/extra command readback')
    for event, actual in zip(events, writes):
        require(all(event[k] == actual[k] for k in ('time_s', 'kind', 'no', 'veh_class')), 'Command address/time differs')
        require(event['value'] == actual['expected'] == actual['actual'] and actual['ok'] == '1', 'Command readback differs')
        if event['kind'] == 'meter':
            require(actual['contr_by_com'] == 'True', 'Meter ownership not acquired')
    expected_addresses = {(r['kind'], r['no'], r['veh_class']) for r in initial}
    snapshots = {}
    for phase, time in [('initial', '0'), ('final', str(end))]:
        records = [r for r in readback if r['phase'] == phase]
        require(len(records) == len(initial), 'Missing/extra snapshot readback')
        snapshots[phase] = {(r['kind'], r['no'], r['veh_class']): r for r in records}
        require(set(snapshots[phase]) == expected_addresses and all(r['time_s'] == time and r['ok'] == '1' for r in records), 'Snapshot address/time differs')
    affected = {(('signal' if r['kind'] == 'meter' else r['kind']), r['no'], r['veh_class']) for r in events}
    for key in affected:
        if key[0] == 'signal':
            require(snapshots['final'][key]['contr_by_com'] == 'True', 'Targeted meter ownership lost at terminal')
    expected_final = {(r['kind'], r['no'], r['veh_class']): r['value'] for r in initial if r['kind'] == 'vsl'}
    for r in initial:
        if r['kind'] == 'vsl':
            a = snapshots['initial'][(r['kind'], r['no'], r['veh_class'])]
            require(a['actual'] == a['expected'] == r['value'], 'Initial native distribution differs')
    for event in events:
        if event['kind'] == 'vsl':
            expected_final[(event['kind'], event['no'], event['veh_class'])] = event['value']
    for key, expected in expected_final.items():
        a = snapshots['final'][key]
        require(a['actual'] == a['expected'] == expected, 'Final distribution differs from last command')
    unchanged = []
    for key in sorted(expected_addresses - affected):
        a, b = snapshots['initial'][key], snapshots['final'][key]
        field = 'actual' if key[0] == 'vsl' else 'contr_by_com'
        require(a[field] == b[field], 'Untargeted DSD/SG ownership changed')
        unchanged.append([*key, a[field]])
    invariant_sha = hashlib.sha256(json.dumps(unchanged, separators=(',', ':')).encode()).hexdigest()
    ldp = native_record(run, meta, end)
    require(all(n == end for n in ldp['file_row_count_by_sc'].values()), 'Native LDP extends beyond requested terminal')
    event_by_sec = {}
    for event in events:
        if event['kind'] == 'meter':
            event_by_sec.setdefault(int(event['time_s']), {})[event['no'] + ':1'] = event['value']
    active = {}
    samples = 0
    for sec in range(1, end + 1):
        # COM write at t occurs after native t frame; subsequent t+1 reflects it.
        active.update(event_by_sec.get(sec - 1, {}))
        for address, expected in active.items():
            require(ldp['frames'][sec][address] == expected, f'Native meter differs at{sec}:{address}')
            samples += 1
    green_counts = []
    for sc, schedule in proof['meter_schedules'].items():
        for index, (start, green) in enumerate(schedule):
            stop = schedule[index + 1][0] if index + 1 < len(schedule) else end
            observed = sum(ldp['frames'][t][f'{sc}:1'] == 'GREEN' for t in range(start + 1, stop + 1))
            expected = (stop - start) * green // 10
            require(observed == expected, 'Native actual-green duration differs')
            green_counts.append({'sc': sc, 'start': start, 'end': stop, 'green_sec_per10': green, 'observed_green_seconds': observed})
    result = {'passed': True, 'event_readbacks': len(writes), 'snapshot_addresses': len(initial),
              'saved_simulation_period_sec': proof['saved_simulation_period_sec'],
              'effective_simulation_period_sec': proof['effective_simulation_period_sec'],
              'untargeted_snapshot_sha256_before': invariant_sha, 'untargeted_snapshot_sha256_after': invariant_sha,
              'native_ldp_row_count': ldp['row_count'], 'native_ldp_sample_count': ldp['sample_count'],
              'unrecorded_signal_groups': proof['unrecorded_signal_groups'],
              'native_meter_samples_checked': samples, 'actual_green_windows': green_counts,
              'ldp_pins': ldp['pins'], 'native_lsa_scope': 'Recorded independently; LSA is not used to substitute for COM state readback or LDP'}
    if meta.get('native_network_performance') == 'whole_network_final_only':
        result['native_network_performance'] = network_performance(run/'native_netperf.csv', end)
    if meta.get('native_network_performance_checkpoints_sec'):
        result['native_network_performance_checkpoints'] = network_performance_checkpoints(
            run/'native_netperf_checkpoints.csv', meta['native_network_performance_checkpoints_sec'],
            result['native_network_performance'])
    if reference:
        reference = Path(reference)
        # A zero-command NC hypothesis run must match its entire observed run.
        cutoff = end if not events else int(meta['control_start_sec'])
        stem = Path(meta['network']).stem
        if grid is not None:
            reference_grid = native_recording_grid(rows(reference/'readback.csv'), proof['native_resolution_probe'])
            require(reference_grid == grid, 'Paired native recording grids differ')
        own = prefix_digest(run/'vissim_eval'/f'{stem}_001.fzp', cutoff, recording_grid=grid)
        ref = prefix_digest(reference/'vissim_eval'/f'{stem}_001.fzp', cutoff, recording_grid=grid)
        require(own == ref, 'Paired complete FZP warmup prefix differs')
        ref_ldp = native_record(reference, meta, end)
        targets = {r['no'] + ':1' for r in events if r['kind'] == 'meter'}
        for sec in range(1, end + 1):
            for address, value in ldp['frames'][sec].items():
                if sec <= cutoff or address not in targets:
                    require(value == ref_ldp['frames'][sec][address], 'Untargeted/native warmup signal differs')
        result.update(paired_warmup_prefix=own, paired_comparison_end_sec=cutoff,
                      paired_native_signals_passed=True, reference=str(reference))
        if grid is not None:
            result['paired_recording_grid_sec'] = [str(v) for v in grid]
    (run/'fixed_validation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', required=True, type=Path)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--reference', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.prepared, args.run, args.reference)))
    except Exception as exc:
        failure = {'passed': False, 'error': type(exc).__name__ + ': ' + str(exc)}
        (args.run/'fixed_validation.json').write_text(json.dumps(failure, indent=2), encoding='utf-8')
        print(json.dumps(failure))
        raise SystemExit(1)
