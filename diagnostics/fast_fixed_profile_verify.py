"""Closed-file native fixed-profile verification, including paired warmup FZP."""
import argparse
import csv
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


def prefix_digest(path, cutoff):
    """All raw FZP data columns/rows through cutoff; ignore volatile headers only."""
    digest = hashlib.sha256()
    count, last = 0, None
    with Path(path).open('rb') as stream:
        for line in stream:
            if not re.match(rb'^\d+(?:\.\d+)?;', line):
                continue
            sec = float(line.split(b';', 1)[0])
            if sec > cutoff:
                break
            require(last is None or sec >= last, 'Reordered FZP prefix')
            digest.update(line.rstrip(b'\r\n') + b'\n')
            count += 1
            last = sec
    require(count > 0 and last == cutoff, 'Missing exact FZP prefix endpoint')
    return {'sha256': digest.hexdigest(), 'rows': count, 'last_time_s': last}


def native_record(folder, proof, end):
    stem = Path(proof['network']).stem
    groups = {int(k): v for k, v in proof['fixed_profile_proof']['ldp_signal_groups'].items()}
    files = {sc: Path(folder)/'vissim_eval'/f'{stem}_{sc}_001.ldp' for sc in groups}
    return read_ldp_frames(files, groups, 1, end)


def verify(prepared, run, reference=None):
    prepared, run = Path(prepared), Path(run)
    meta = json.loads((prepared/'prepared.json').read_text(encoding='utf-8-sig'))
    require(meta['mode'] == 'fixed_profile', 'Wrong prepared mode')
    proof = meta['fixed_profile_proof']
    end = int(meta['terminal_sec'])
    setup = rows(run/'readback.csv')
    for kind, expected in [('native_simulation', proof['saved_simulation_period_sec']),
                           ('fixed_simulation', proof['effective_simulation_period_sec'])]:
        selected = [r for r in setup if r['kind'] == kind and r['no'] == 'SimPeriod']
        require(len(selected) == 1 and float(selected[0]['expected']) == expected and float(selected[0]['actual']) == expected,
                'Missing/different saved or effective SimPeriod readback')
    events = rows(prepared/'fixed_events.csv')
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
    if reference:
        reference = Path(reference)
        # A zero-command NC hypothesis run must match its entire observed run.
        cutoff = end if not events else int(meta['control_start_sec'])
        stem = Path(meta['network']).stem
        own = prefix_digest(run/'vissim_eval'/f'{stem}_001.fzp', cutoff)
        ref = prefix_digest(reference/'vissim_eval'/f'{stem}_001.fzp', cutoff)
        require(own == ref, 'Paired complete FZP warmup prefix differs')
        ref_ldp = native_record(reference, meta, end)
        targets = {r['no'] + ':1' for r in events if r['kind'] == 'meter'}
        for sec in range(1, end + 1):
            for address, value in ldp['frames'][sec].items():
                if sec <= cutoff or address not in targets:
                    require(value == ref_ldp['frames'][sec][address], 'Untargeted/native warmup signal differs')
        result.update(paired_warmup_prefix=own, paired_comparison_end_sec=cutoff,
                      paired_native_signals_passed=True, reference=str(reference))
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
