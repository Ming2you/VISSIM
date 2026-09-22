"""Stream a completed full native NC run; retain road/lane flows, not all tracks."""
import argparse
from bisect import bisect_right
from collections import Counter
import csv
import hashlib
import math
from pathlib import Path
import time

from diagnostics import run_fixed_beta300v3_route_experiment as d
from diagnostics.audit_observer_control_pair import native_signal_prefix
from diagnostics.capture_native_runtime_errors import parse_bytes
from diagnostics.selected_signal_sampling_audit import geometry, head_events

ROADS = (30, 46, 47, 52, 56, 66, 67, 68, 69, 70, 71, 72, 121, 123, 126, 127, 329, 420,
         10625, 10629, 10633, 10634, 10635, 10639, 10641, 10643, 10646, 10681, 10682, 10772, 10773, 1220007200)


def native_clock(groups):
    """Validate observed change events; never backfill an unknown initial state."""
    times = {}
    for key, events in groups.items():
        last = None
        for row in events:
            d.require(len(row) == 2 and math.isfinite(row[0]) and row[0] >= 0
                      and isinstance(row[1], str) and bool(row[1]), 'Invalid native signal event')
            if last is not None:
                d.require(row[0] >= last[0] and (row[0] != last[0] or row[1] == last[1]),
                          'Reordered/conflicting native signal events: ' + key)
            last = row
        times[key] = [row[0] for row in events]
    return times


def signal_state(groups, times, key, sec):
    index = bisect_right(times.get(key, []), sec) - 1
    return None if index < 0 else groups[key][index][1]


def crossing_green(groups, times, key, start, end):
    """A conservative whole-bracket GREEN, including the upper endpoint.

    Checking only endpoint colors misses intervening subsecond transitions.
    Unknown-before-first-event is separate from a known non-GREEN bracket.
    """
    d.require(math.isfinite(start) and math.isfinite(end) and start < end, 'Invalid crossing bracket')
    states = [signal_state(groups, times, key, start)]
    a, b = bisect_right(times.get(key, []), start), bisect_right(times.get(key, []), end)
    states.extend(row[1] for row in groups.get(key, [])[a:b])
    if any(state is None for state in states):
        return None
    return all(state == 'GREEN' for state in states)


def native_run_mode(log):
    rows = [line.strip() for line in log.splitlines() if line.strip().startswith(b'RUN_MODE=')]
    modes = {b'RUN_MODE=CONTINUOUS_STATIC controller=no-control': 'CONTINUOUS_STATIC',
             b'RUN_MODE=STEPWISE controller=no-control': 'STEPWISE',
             b'RUN_MODE=STEPWISE_PHYSICAL_HEAD_OBSERVATION': 'STEPWISE'}
    d.require(len(rows) == 1 and rows[0] in modes, 'Unknown/conflicting actual NC run mode')
    return modes[rows[0]], rows[0].decode('ascii')


def no_control_commands(actions, end, interval, *, mode):
    """Recorded NC must also have the unchanged open VSL/meter commands."""
    d.require(type(interval) is int and interval > 0, 'Invalid control interval')
    by_time = {}
    for row in actions:
        sec = float(row['sim_sec'])
        d.require(math.isfinite(sec) and sec.is_integer(), 'Invalid applied command timestamp')
        by_time.setdefault(int(sec), []).append(row)
    d.require(mode in ('CONTINUOUS_STATIC', 'STEPWISE'), 'Unknown NC command cadence mode')
    if mode == 'CONTINUOUS_STATIC':
        d.require(end >= 900, 'This continuous-static profile requires the recorded 900s reapplication')
        expected = {1, 900}
    else:
        expected = {1, *range(interval, end + 1, interval)}
    d.require(set(by_time) == expected, 'NC command decisions incomplete for ' + mode)
    baseline = None
    for rows in by_time.values():
        physical = d.physical_rows(rows)
        d.require(Counter(row['kind'] for row in rows) == {'vsl': 66, 'ramp_meter': 8}, 'Unexpected NC command coverage')
        d.require(all(float(row['speed_kph']) == 120.0 if row['kind'] == 'vsl'
                      else float(row['rate_vph']) == 900.0 and float(row['green_sec']) == 10.0
                      for row in rows), 'NC has active VSL or meter restriction')
        d.require(baseline is None or physical == baseline, 'NC physical command changed')
        baseline = physical
    return {'mode': mode, 'decision_times_sec': sorted(by_time), 'rows_per_decision': 74,
            'full_vsl_kph': 120, 'per_meter_rate_vph': 900, 'per_meter_green_sec': 10,
            'all_recorded_physical_commands_identical': True}


def native_frames(path, evidence, *, deadline, interval_sec=1, phase_sec=0):
    """Explicit full-file scan, one global vehicle frame in memory at a time."""
    d.require(type(interval_sec) is int and interval_sec in (1,5), 'Native interval must be1 or5 seconds')
    d.require(0 <= phase_sec < interval_sec, 'Invalid native recording phase')
    if phase_sec: evidence['native_phase_sec'] = phase_sec
    if interval_sec!=1:evidence['observation_interval_sec']=interval_sec
    file_hash, payload_hash = hashlib.sha256(), hashlib.sha256()
    frame, now, count = {}, None, 0
    with path.open('rb') as stream:
        for raw in stream:
            file_hash.update(raw)
            if raw.startswith(b'$VEHICLE:'):
                names = raw.decode('ascii').strip().split(':', 1)[1].split(';')
                d.require(len(names) == len(set(names)), 'Duplicate native header column')
                break
        else:
            raise ValueError('Native vehicle header absent')
        fields = {k: names.index(k) for k in ('SIMSEC', 'NO', 'LANE\\LINK\\NO', 'LANE\\INDEX', 'POS', 'SPEED')}
        evidence['header'] = raw.decode('ascii').strip()
        for raw in stream:
            file_hash.update(raw)
            payload_hash.update(raw)
            d.require(raw.endswith(b'\n'), 'Truncated native final row')
            parts = raw.rstrip(b'\r\n').split(b';')
            d.require(len(parts) == len(names), 'Unexpected native row shape')
            sec = float(parts[fields['SIMSEC']])
            grid = (sec-phase_sec)/interval_sec
            d.require(abs(grid-round(grid)) < 1e-8,'Native frame is off the declared sampling grid')
            if not phase_sec: sec = int(sec)
            if now is not None and sec != now:
                d.require(abs(sec-now-interval_sec) < 1e-8, 'Missing or reordered native frame')
                d.require(time.monotonic() < deadline, 'Declared full-scan deadline exceeded')
                yield now, frame
                frame = {}
            now = sec
            no = int(parts[fields['NO']])
            d.require(no > 0 and no not in frame, 'Invalid/duplicate native vehicle in frame')
            row = (int(parts[fields['LANE\\LINK\\NO']]), int(parts[fields['LANE\\INDEX']]),
                   float(parts[fields['POS']]), float(parts[fields['SPEED']]))
            # VISSIM can record a just-entered vehicle slightly before Pos=0
            # (actual NC t53: link26 Pos=-0.09). Preserve finite coordinates.
            d.require(row[0] > 0 and row[1] > 0 and all(math.isfinite(v) for v in row[2:]) and row[3] >= 0,
                      'Invalid native position/speed/link/lane')
            frame[no] = row
            count += 1
        if now is not None:
            yield now, frame
    evidence.update(file_sha256=file_hash.hexdigest(), payload_sha256=payload_hash.hexdigest(), rows=count)


def analyze(run, network, output, end):
    output = output.resolve()
    d.require(output.is_relative_to(d.ROOT / 'diagnostics') and not output.exists(), 'New diagnostic output directory required')
    d.require(type(end) is int and end > 0, 'Positive integer native extent required')
    provenance_path = run / ('run_provenance_' + run.name + '.json')
    provenance = d.load(provenance_path)
    d.require(provenance['controller'] == 'no-control' and provenance['seed'] == 13
              and provenance['sim_period_sec'] == end and provenance['files']['network']['sha256'] == d.sha(network),
              'Wrong NC run extent/network')
    log_path = run / ('runlog_' + run.name + '.txt')
    log = log_path.read_bytes()
    d.require(b'STAGE=SIM_DONE' in log, 'Completed run required')
    mode, mode_row = native_run_mode(log)
    action_path = run / ('action_' + run.name + '.csv')
    actions = d.csv_rows(action_path)
    d.require(bool(actions), 'Missing NC physical actions')
    d.require(not any(r['kind'] in ('signal', 'signal_sg') for r in actions), 'NC emitted urban signal overrides')
    command_proof = no_control_commands(actions, end, provenance['control_interval_sec'], mode=mode)
    command_proof['actual_run_mode_line'] = mode_row
    fzp = d.single_fzp(run)
    lsa_files = list(run.glob('vissim_eval/*.lsa'))
    d.require(len(lsa_files) == 1, 'One completed native LSA required')
    lsa = lsa_files[0]
    err = run / 'vissim_simulation_001.err'
    parsed = parse_bytes(err.read_bytes())
    d.require(not parsed['partial_tail_bytes'] and not parsed['unparsed_removal_lines'], 'Incomplete native deletion evidence')
    helpers = ('run_fixed_beta300v3_route_experiment.py', 'audit_observer_control_pair.py',
               'capture_native_runtime_errors.py', 'selected_signal_sampling_audit.py', 'audit_sc15_source_discharge.py')
    pins = {d.relative(p): d.sha(p) for p in (Path(__file__), network, provenance_path, log_path, action_path, lsa, err,
                                            *(Path(__file__).parent / name for name in helpers))}
    native = native_signal_prefix(lsa, end)
    groups = native['groups']
    times = native_clock(groups)
    def green(sc, sg, sec):
        state = signal_state(groups, times, f'{sc}:{sg}', sec)
        return None if state is None else state == 'GREEN'
    geo = geometry(network)
    heads = {h['lane']: h for h in geo['71']['heads']}
    d.require(len(heads) == len(geo['71']['heads']) and bool(heads)
              and all(h['SC'] == '1004' for h in heads.values()), 'Ambiguous road71 head/lane geometry')
    d.require(all(f"1004:{h['sg']}" in groups for h in heads.values()), 'Missing road71 native signal events')
    output.mkdir()
    evidence = {'path': d.relative(fzp), 'bytes': fzp.stat().st_size}
    stat_before = (fzp.stat().st_size, fzp.stat().st_mtime_ns)
    bins = {i: {'start': i * 900, 'end': min((i + 1) * 900, end), 'road_ttt': Counter(),
                'entries': Counter(), 'departures': Counter(), 'absences': Counter(), 'lane_changes': Counter(),
                'head_crossings': Counter(), 'green_head_crossings': Counter(), 'near_head_green_stopped_vehicle_seconds': Counter(),
                'head_event_classes': Counter(), 'unknown_signal_head_crossings': Counter(),
                'unknown_signal_samples': Counter(), 'near_head_unknown_signal_stopped_samples': Counter(),
                'opening_road_stock': {}, 'closing_road_stock': {},
                'arrivals420_by_source': Counter()} for i in range((end + 899) // 900)}
    previous, previous_counts = {}, Counter()
    sources, observed_frames, closed = {}, 0, 0
    road_set = set(ROADS)
    event_columns = ('upper_sec', 'kind', 'vehicle', 'link', 'lane', 'other_link', 'other_lane', 'source_family')
    head_columns = ('vehicle_id', 'link', 'lower_sec', 'upper_sec', 'kind', 'head', 'SC', 'sg',
                    'lane_before', 'pos_before_m', 'lane_after', 'pos_after_m', 'to_link', 'connector',
                    'method', 'linear_estimate_sec', 'bracket_green')
    time_columns = ['sec'] + [f'{road}_{key}' for road in ROADS for key in ('n', 'stopped')] + ['SG2_GREEN', 'SG5_GREEN']
    with (output / 'events.csv').open('x', newline='', encoding='utf-8') as es, (output / 'timeseries.csv').open('x', newline='', encoding='utf-8') as ts, (output / 'head_events.csv').open('x', newline='', encoding='utf-8') as hs:
        ew, tw, hw = csv.DictWriter(es, fieldnames=event_columns), csv.DictWriter(ts, fieldnames=time_columns), csv.DictWriter(hs, fieldnames=head_columns)
        ew.writeheader(); tw.writeheader(); hw.writeheader()
        for sec, current in native_frames(fzp, evidence, deadline=time.monotonic() + 900):
            d.require(sec == observed_frames + 1 and sec <= end, 'Native extent differs')
            observed_frames += 1
            counts = Counter(r[0] for r in current.values() if r[0] in road_set)
            stopped = Counter(r[0] for r in current.values() if r[0] in road_set and r[3] <= 1)
            block = bins[(sec - 1) // 900]
            if sec == block['start'] + 1:
                block['opening_road_stock'] = {str(road): previous_counts[road] for road in ROADS}
            # Do not carry an old source label across global disappearance or
            # ID reuse. Continuous trajectories can legitimately revisit roads.
            sources = {no: family for no, family in sources.items() if no in current}
            entries, departures = Counter(), Counter()
            for no, row in previous.items():
                if row[0] not in road_set:
                    continue
                nxt = current.get(no)
                if nxt is None or nxt[0] != row[0]:
                    departures[row[0]] += 1
                    key = str(row[0]) if nxt is None else f'{row[0]}>{nxt[0]}'
                    block['absences' if nxt is None else 'departures'][key] += 1
                    ew.writerow(dict(upper_sec=sec, kind='global_absence' if nxt is None else 'departure', vehicle=no,
                                     link=row[0], lane=row[1], other_link='' if nxt is None else nxt[0], other_lane='' if nxt is None else nxt[1]))
                elif nxt[1] != row[1]:
                    block['lane_changes'][f'{row[0]}:{row[1]}>{nxt[1]}'] += 1
                if row[0] == 71:
                    for event in head_events(geo['71'], no, row, nxt, sec - 1, sec):
                        block['head_event_classes'][event['kind']] += 1
                        bracket = ''
                        if event['kind'] == 'head_crossing':
                            key = f"{event['sg']}:{row[1]}"
                            block['head_crossings'][key] += 1
                            value = crossing_green(groups, times, f"1004:{event['sg']}", sec - 1, sec)
                            bracket = 'unknown' if value is None else ('GREEN' if value else 'not_whole_GREEN')
                            if value is None:
                                block['unknown_signal_head_crossings'][key] += 1
                            elif value:
                                block['green_head_crossings'][key] += 1
                        hw.writerow({**{k: event.get(k, '') for k in head_columns}, 'bracket_green': bracket})
            for no, row in current.items():
                if row[0] in (127, 329, 72):
                    sources[no] = str(row[0])
                if row[0] not in road_set:
                    continue
                old = previous.get(no)
                if old is None or old[0] != row[0]:
                    entries[row[0]] += 1
                    block['entries'][str(row[0])] += 1
                    family = sources.get(no, 'unobserved') if row[0] == 420 else ''
                    if row[0] == 420:
                        block['arrivals420_by_source'][family] += 1
                    ew.writerow(dict(upper_sec=sec, kind='entry', vehicle=no, link=row[0], lane=row[1],
                                     other_link='' if old is None else old[0], other_lane='' if old is None else old[1], source_family=family))
                if row[0] == 71 and row[1] in heads:
                    head = heads[row[1]]
                    if row[3] <= 1 and 0 <= head['pos_m'] - row[2] <= 20:
                        value = green('1004', head['sg'], sec)
                        if value is None:
                            block['near_head_unknown_signal_stopped_samples'][str(row[1])] += 1
                        elif value:
                            block['near_head_green_stopped_vehicle_seconds'][str(row[1])] += 1
            for road in ROADS:
                d.require(previous_counts[road] + entries[road] - departures[road] == counts[road], 'Road stock does not close')
                block['road_ttt'][str(road)] += (previous_counts[road] + counts[road]) / 7200
                closed += 1
            lights = {sg: green('1004', sg, sec) for sg in ('2', '5')}
            for sg, value in lights.items():
                if value is None:
                    block['unknown_signal_samples'][sg] += 1
            tw.writerow({'sec': sec, **{f'{road}_{key}': value[road] for road in ROADS for key, value in (('n', counts), ('stopped', stopped))},
                         **{f'SG{sg}_GREEN': '' if value is None else int(value) for sg, value in lights.items()}})
            if sec == block['end']:
                block['closing_road_stock'] = {str(road): counts[road] for road in ROADS}
            previous, previous_counts = current, counts
    d.require(observed_frames == end and stat_before == (fzp.stat().st_size, fzp.stat().st_mtime_ns), 'Incomplete/changed native file')
    d.assert_pins(pins)
    report = {'schema': 'full-nc-corridor-stream/v2', 'run': d.relative(run), 'end_sec': end, 'valid': True,
              'source_sha256': pins, 'source_changes': [], 'fzp': evidence, 'frames': observed_frames,
              'road_closure_checks': closed, 'road_closure_nonzero': 0, 'windows': bins,
              'no_control_command_proof': command_proof,
              'native_warnings': parsed, 'native_signal_proof': {k: v for k, v in native.items() if k != 'groups'},
              'head_geometry_71': geo['71'],
              'definitions': {'window': 'Transitions have start < upper_sec <= end; each bracket (t-1,t] is counted once.',
                              'road_ttt': 'Trapezoidal sum (N(t-1)+N(t))/7200 veh*h, with native empty initialization N(0)=0 assumed, not observed.',
                              'closure': 'Frame bookkeeping identity Nprev + observed entries - observed departures/absences = Nnow, not independent vehicle conservation.',
                              'green_head_crossing': 'Resolved same-lane/unique-connector bracket; observed LSA GREEN throughout and at both endpoints. Initial unknown is separate.',
                              'near_head_green_stopped_vehicle_seconds': '1Hz right-endpoint sampled proxy: speed<=1 km/h, position 0..20m before head, observed GREEN. Not continuous stopped duration.',
                              'head_scope': 'Head classifications are road71/SC1004 only; other listed roads have stock and transition counts.'},
              'limits': ['One-second observations; crossings are time brackets. Absences are not throughput.',
                         'Native initial signal state before its first LSA event is unknown, not inferred RED; blank GREEN cells preserve that gap.',
                         'Short traversals/lane changes wholly between frames are unobserved. Resolved head crossings are a conservative subset; unresolved event classes are retained.',
                         'Road entries include first observations/native generation, not just connector crossings; short-link passage counts can be missed between frames.',
                         'Near-head stopped vehicle-seconds during GREEN do not prove blockage or saturation capacity.',
                         'Road TTT describes physical roads, not the separate Omega objective.',
                         '420 source is the most recently observed127/329/72 road in a continuously observed global trajectory, not an inferred route choice.']}
    d.save(output / 'summary.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True); parser.add_argument('--network', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True); parser.add_argument('--end-sec', type=int, default=5400)
    args = parser.parse_args()
    result = analyze(d.workspace_path(args.run), d.workspace_path(args.network), d.workspace_path(args.output), args.end_sec)
    print({'valid': result['valid'], 'frames': result['frames'], 'road_closure_checks': result['road_closure_checks']})
