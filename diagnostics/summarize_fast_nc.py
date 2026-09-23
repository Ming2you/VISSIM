"""Completed runs only: one FZP pass for area, selected roads and 42 cells.

No model evaluation, COM, chart or common-source inventory verification.
Canonical controller runs require an explicit --completion-receipt.
"""
from __future__ import annotations
import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from diagnostics.analyze_no_control_corridors import native_frames
from diagnostics.capture_native_runtime_errors import parse_bytes
from scripts.measure_control_area import Frame, Vehicle, measure_frames, terminal_lengths, physical_membership_from_ledger

ROADS = (2, 40, 66, 68, 69, 70, 71, 121, 123, 127, 321, 322, 325, 326, 329,
         10639, 10681, 10682, 10643, 10646)
ISOLATED_INPUTS = {74: 1098, 66: 1100, 69: 1101}  # original XML: no incoming connector, one native input each
MEMBERSHIP = ROOT / 'diagnostics/control_area_membership.json'
REFERENCE = ROOT / 'evaluation/runs/codex_nc5400_r01_baseline_s13/run_provenance_codex_nc5400_r01_baseline_s13.json'


def require(value, message):
    if not value:
        raise ValueError(message)


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def write_csv(path, rows):
    require(bool(rows), 'Empty output table')
    with Path(path).open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cell_geometry(vbs_path=None):
    # The parent has already verified common geometry. Read it; do not rehash
    # the network or its large dependency graph for every demand-sweep run.
    #
    # REFERENCE is a specific baseline run whose provenance is consulted for one
    # thing only: the path of the generated VBS config carrying the fixed chain
    # declarations. That run lives under evaluation/runs/, which is gitignored, so
    # it is absent from checkouts assembled from source control. --geometry-vbs
    # names the same VBS config directly. The declarations are then parsed and
    # validated identically, and the proof records which route supplied them.
    # Only the per-cell freeway breakdown uses this; the Omega TTT total comes
    # from the membership document and is unaffected either way.
    if vbs_path is None:
        item = load(REFERENCE)['files']['generated_vbs_config']
        path = Path(item['path'])
        origin = {'reference_manifest': str(REFERENCE), 'recorded_sha256': item['sha256']}
    else:
        path = Path(vbs_path).resolve()
        require(path.is_file(), 'Explicit geometry VBS not found: ' + str(path))
        origin = {'reference_manifest': None, 'geometry_vbs_override': str(path),
                  'recorded_sha256': sha256_of(path)}
    source = path.read_text(encoding='utf-8-sig')
    bounds, addresses = {}, {}
    for direction in ('E', 'W'):
        def values(name):
            matches = re.findall(rf'^RW_FW_{direction}_{name}\s*=\s*"([^"]+)"\s*$', source, re.M)
            require(len(matches) == 1, 'Missing fixed chain geometry ' + name)
            return matches[0].split(',')
        edges = [float(v) for v in values('SEG_BOUNDS')]
        links, offsets = values('CHAIN_LINKS'), [float(v) for v in values('CHAIN_OFFSETS_M')]
        require(len(edges) == 22 and edges[0] == 0 and all(a < b for a, b in zip(edges, edges[1:]))
                and len(links) == len(offsets), 'Invalid fixed42-cell geometry')
        bounds[direction] = edges
        for link, offset in zip(links, offsets):
            require(int(link) not in addresses and math.isfinite(offset), 'Duplicate/nonfinite chain address')
            addresses[int(link)] = (direction, offset)
    return bounds, addresses, {**origin, 'geometry_file': str(path),
        'common_identity_reverified_this_run': False}


def terminal_candidate(old, length):
    # Mirrors the unchanged canonical one-second inference solely to FLAG a
    # known-removal collision; never changes that function's state or events.
    reach = old[3] / 3.6 + 1.5 + 10.0
    return -reach <= length - old[2] <= reach


def summarize_stream(frames, membership, terminals, bounds, addresses, removals, *, end=5400):
    require(end > 0 and end % 30 == 0, 'Require a complete30-second ending')
    removal_index = defaultdict(list)
    for index, event in enumerate(removals):
        removal_index[(int(event['vehicle_id']), int(event['link']))].append((index, event))
    road_samples, cell_samples, road_windows, matches = [], [], [], []
    peaks = {r: {'peak_n': 0, 'peak_n_sec': 0, 'peak_stopped': 0, 'peak_stopped_sec': 0} for r in ROADS}
    bins = {r: Counter() for r in ROADS}
    opening = Counter()
    previous, previous_counts = {}, Counter()
    observed, closed = 0, 0
    matched_indices = set()
    seen_ids, source_counts, source_reappearances = set(), Counter(), Counter()

    def forwarding():
        nonlocal previous, previous_counts, observed, opening, bins, closed
        for sec, current in frames:
            require(sec == observed + 1 and sec <= end, 'Expected exact1s complete run')
            observed = sec
            counts, stopped, speeds = Counter(), Counter(), Counter()
            entries, departures, absences, deleted = Counter(), Counter(), Counter(), Counter()
            for no, old in previous.items():
                new = current.get(no)
                if new is None:
                    if old[0] in bins:
                        absences[old[0]] += 1
                    candidates = [(i, e) for i, e in removal_index.get((no, old[0]), [])
                                  if abs(float(e['time_sec']) - sec) <= 1]
                    if candidates:
                        exact = len(candidates) == 1
                        if exact:
                            i, event = candidates[0]
                            require(i not in matched_indices, 'Native removal matched multiple disappearances')
                            matched_indices.add(i)
                            if old[0] in bins:
                                deleted[old[0]] += 1
                        is_inside = membership.get(str(old[0]))
                        collision = bool(is_inside and str(old[0]) in terminals
                                         and terminal_candidate(old, terminals[str(old[0])]))
                        matches.append({'vehicle_id': no, 'link': old[0], 'lower_sec': sec - 1, 'upper_sec': sec,
                            'native_times_sec': [e['time_sec'] for _, e in candidates], 'native_event_indices': [i for i, _ in candidates],
                            'unique_match': exact, 'inside': is_inside, 'last_position_m': old[2],
                            'terminal_TD_inference_collision': collision})
                elif old[0] != new[0] and old[0] in bins:
                    departures[old[0]] += 1
            for no, row in current.items():
                road = row[0]
                if no not in previous and road in ISOLATED_INPUTS:
                    key = ((sec - 1) // 900 * 900, ISOLATED_INPUTS[road])
                    (source_reappearances if no in seen_ids else source_counts)[key] += 1
                if road in bins:
                    counts[road] += 1
                    speeds[road] += row[3]
                    stopped[road] += row[3] <= 1.0
                    if no not in previous or previous[no][0] != road:
                        entries[road] += 1
            for road in ROADS:
                require(previous_counts[road] + entries[road] - departures[road] - absences[road] == counts[road], 'Road closure failure')
                closed += 1
                bins[road].update(entry=entries[road], normal_other_link_exit=departures[road],
                                  absent=absences[road], matched_native_removal=deleted[road])
                peak = peaks[road]
                if counts[road] > peak['peak_n']:
                    peak.update(peak_n=counts[road], peak_n_sec=sec)
                if stopped[road] > peak['peak_stopped']:
                    peak.update(peak_stopped=stopped[road], peak_stopped_sec=sec)
                if sec % 30 == 0:
                    road_samples.append({'sec': sec, 'link': road, 'n': counts[road], 'stopped': stopped[road],
                        'mean_speed_kph': speeds[road] / counts[road] if counts[road] else None})
                if sec % 900 == 0 or sec == end:
                    row = {'start_sec': (sec - 1) // 900 * 900, 'end_sec': sec, 'link': road,
                           'initial_n': opening[road], **dict(bins[road]), 'end_n': counts[road], 'end_stopped': stopped[road]}
                    row['closure'] = row['end_n'] - row['initial_n'] - row['entry'] + row['normal_other_link_exit'] + row['absent']
                    road_windows.append(row)
            if sec % 30 == 0:
                c, s, v = Counter(), Counter(), Counter()
                for row in current.values():
                    address = addresses.get(row[0])
                    if address is None:
                        continue
                    direction, offset = address
                    position = offset + row[2]
                    if position < 0:  # canonical ChainPosCsv caller does not bin negative chain positions
                        continue
                    cell = min(20, bisect_right(bounds[direction], position) - 1)
                    key = direction, cell
                    c[key] += 1; s[key] += row[3] <= 1.0; v[key] += row[3]
                for direction in ('E', 'W'):
                    for cell in range(21):
                        key = direction, cell
                        cell_samples.append({'sec': sec, 'direction': direction, 'cell': cell,
                            'n': c[key], 'stopped': s[key], 'mean_speed_kph': v[key] / c[key] if c[key] else None,
                            'speed_eligible_n_ge5': c[key] >= 5})
            if sec % 900 == 0:
                opening = counts.copy(); bins = {r: Counter() for r in ROADS}
            previous, previous_counts = current, counts
            seen_ids.update(current)
            yield Frame(float(sec), {str(no): Vehicle(str(r[0]), r[2], r[3]) for no, r in current.items()})

    metrics, area_rows = measure_frames(forwarding(), membership, terminals, end_sec=end,
        final_frame=None, max_tail_extrap_sec=0, simulation_step_sec=1)
    require(observed == end and metrics['boundaries']['unobserved_tail_sec'] == 0, 'Incomplete FZP extent')
    conflicts = [r for r in matches if r['terminal_TD_inference_collision']]
    recovery = []
    for road in ROADS:
        last = next(r for r in reversed(road_windows) if r['link'] == road)
        recovery.append({'link': road, **peaks[road], 'last_window_start_sec': last['start_sec'],
            'last_window_start_n': last['initial_n'], 'final_n': last['end_n'], 'final_stopped': last['end_stopped'],
            'last_window_normal_exit_minus_entry': last['normal_other_link_exit'] - last['entry'],
            'last_window_absent': last['absent'], 'last_window_native_removal': last['matched_native_removal'],
            'interpretation': 'Stock decline is not recovery proof when losses contribute; final state remains censored.'})
    return {'metrics': metrics, 'area_rows': area_rows, 'road_samples': road_samples,
        'cell_samples': cell_samples, 'road_windows': road_windows, 'recovery': recovery,
        'source_inputs': [{'start_sec': start, 'end_sec': min(start + 900, end), 'input_no': inp, 'source_link': link,
            'first_observed_insertions': source_counts[start, inp], 'seen_id_reappearances_excluded': source_reappearances[start, inp]}
            for start in range(0, end, 900) for link, inp in ISOLATED_INPUTS.items()],
        'road_closure_checks': closed, 'removal_matches': matches, 'terminal_conflicts': conflicts,
        'unmatched_native_removal_indices': sorted(set(range(len(removals))) - matched_indices)}


def completion_inputs(run, receipt_path=None):
    """Validate completion evidence only; never create or infer a run receipt."""
    run = Path(run).resolve()
    if receipt_path is None:
        manifest_path = run / 'run.json'
        manifest = load(manifest_path)
        require(manifest.get('completed') is True and type(manifest.get('exit_code')) is int
                and manifest['exit_code'] == 0 and manifest.get('owned_native_alive') is False,
                'Completed exit0/closed-native receipt required')
        end = manifest.get('terminal_sec')
        require(type(end) in (int, float) and math.isfinite(end) and end in (5400, 7200, 9000),
                'Native receipt must end at5400,7200 or9000')
        log = (run / 'stdout.txt').read_text(encoding='utf-8-sig', errors='replace')
        require(re.search(r'^STAGE=SIM_DONE\s*$', log, re.M)
                and not re.search(r'^ERROR=', log, re.M), 'Native terminal log incomplete')
        seconds = re.findall(r'^SIM_SEC=([^\r\n]+)', log, re.M)
        require(bool(seconds) and math.isfinite(float(seconds[-1])) and float(seconds[-1]) == end,
                'Native terminal log and receipt horizon mismatch')
        names = [item['name'] for item in manifest.get('error_files', [])]
        require(len(names) == len(set(names)) and all(Path(n).name == n and n.lower().endswith('.err') for n in names),
                'Invalid native ERR receipt names')
        err_paths = [run / n for n in names]
        require(bool(err_paths), 'Preserved native ERR evidence required')
        return manifest_path, manifest, err_paths, None

    receipt_path = Path(receipt_path).resolve()
    require(receipt_path == run / 'completion_receipt.json', 'Canonical receipt must belong to this run')
    receipt = load(receipt_path)
    require(receipt.get('schema') == 'selected-control-completion/v1', 'Unknown canonical completion schema')
    require(receipt.get('completed') is True and type(receipt.get('exit_code')) is int
            and receipt['exit_code'] == 0 and receipt.get('owned_native_alive') is False,
            'Completed exit0/closed-native canonical receipt required')
    end = receipt.get('terminal_sec')
    require(type(end) in (int, float) and math.isfinite(end) and end in (5400, 7200, 9000),
            'Canonical receipt must end at5400,7200 or9000')
    require(receipt.get('cscript_exit_code', 'missing') is None,
            'Watchdog exit is not a cscript exit-code observation')
    name, run_id = receipt.get('name'), receipt.get('run_id')
    require(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9_-]+', name) and name == run.name
            and isinstance(run_id, str) and bool(run_id.strip()), 'Invalid canonical run identity')
    require(isinstance(receipt.get('run_directory'), str)
            and Path(receipt['run_directory']).resolve() == run, 'Canonical run directory mismatch')

    def local_file(value, basename):
        require(isinstance(value, str) and Path(value).is_absolute(), 'Absolute canonical evidence path required')
        path = Path(value).resolve()
        require(path == run / basename and path.is_file(), 'Canonical evidence path mismatch or missing: ' + basename)
        return path

    provenance_path = local_file(receipt.get('provenance_path'), 'run_provenance_' + name + '.json')
    provenance_bytes = provenance_path.read_bytes()
    require(hashlib.sha256(provenance_bytes).hexdigest() == receipt.get('provenance_sha256'), 'Canonical provenance SHA mismatch')
    provenance = json.loads(provenance_bytes.decode('utf-8-sig'))
    require(provenance.get('run_id') == run_id and provenance.get('name') == name
            and provenance.get('sim_period_sec') == end, 'Canonical provenance identity/end mismatch')
    require(isinstance(provenance.get('controller'), str) and bool(provenance['controller']), 'Missing canonical controller identity')
    log_path = local_file(receipt.get('runlog_path'), 'runlog_' + name + '.txt')
    log_bytes = log_path.read_bytes()
    log = log_bytes.decode('utf-8-sig', errors='replace')
    require(re.search(r'^STAGE=SIM_DONE\s*$', log, re.M)
            and not any(token in log for token in ('ERROR=', 'DIAGNOSTIC_DECISION_FAILED', 'STRICT_DECISION_FAILED')),
            'Canonical terminal log incomplete or failed')
    seconds = re.findall(r'^SIM_SEC=([^\r\n]+)', log, re.M)
    require(bool(seconds) and math.isfinite(float(seconds[-1])) and float(seconds[-1]) == end,
            'Canonical terminal log and receipt horizon mismatch')
    for counter in ('DECISIONS_FAILED', 'OBSERVATION_FAILURES', 'SIGNAL_FAILURES', 'ACTION_FORMAT_FAILURES', 'COM_FAILURES'):
        require(re.findall(r'^' + counter + r'=([^\r\n]+)', log, re.M) == ['0'], 'Canonical failure counter is missing/nonzero: ' + counter)
    state_path = local_file(receipt.get('state_csv_path'), 'state_' + name + '.csv')
    state_bytes = state_path.read_bytes()
    previous_sec = -1.0
    for row in csv.DictReader(state_bytes.decode('utf-8-sig').splitlines()):
        sec = float(row['sim_sec'])
        require(math.isfinite(sec) and previous_sec < sec <= end, 'Canonical state clock is invalid')
        require('fallback' not in row.get('controller_status', '').lower(), 'Canonical state contains fallback')
        previous_sec = sec
    require(previous_sec == end, 'Canonical state CSV and receipt horizon mismatch')
    err_paths, err_rows = [], receipt.get('error_files')
    require(isinstance(err_rows, list) and bool(err_rows), 'Preserved canonical ERR evidence required')
    for item in err_rows:
        require(isinstance(item, dict) and isinstance(item.get('name'), str)
                and re.fullmatch(r'vissim_(?:network|simulation_\d+)\.err', item['name']), 'Invalid canonical ERR name')
        path = local_file(item.get('path'), item['name'])
        require(path not in err_paths, 'Duplicate canonical ERR file')
        data = path.read_bytes()
        require(type(item.get('bytes')) is int and item['bytes'] == len(data)
                and item.get('sha256') == hashlib.sha256(data).hexdigest(), 'Canonical ERR bytes/SHA mismatch')
        err_paths.append(path)
    require(any(re.fullmatch(r'vissim_simulation_\d+\.err', p.name) for p in err_paths), 'Canonical runtime ERR is required')
    completion = {'schema': receipt['schema'], 'run_id': run_id, 'controller': provenance['controller'],
        'terminal_sec': end,
        'receipt_sha256': hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        'provenance_path': str(provenance_path), 'provenance_sha256': receipt['provenance_sha256'],
        'runlog_path': str(log_path), 'runlog_sha256': hashlib.sha256(log_bytes).hexdigest(),
        'state_csv_path': str(state_path), 'state_csv_sha256': hashlib.sha256(state_bytes).hexdigest(),
        'watchdog_exit_code': receipt['exit_code'], 'cscript_exit_code': None,
        'native_process_evidence_scope': 'External wrapper receipt; no process discovery or native execution by summarizer.',
        'error_files': err_rows}
    info = {'network': provenance.get('files', {}).get('network', {}).get('path'),
            'prepared': None, 'seed': provenance.get('seed')}
    return receipt_path, info, err_paths, completion


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--completion-receipt', type=Path, help='Explicit selected-control-completion/v1 receipt; omitted keeps fast NC input')
    parser.add_argument('--geometry-vbs', type=Path, help='Generated VBS config carrying the fixed chain declarations; omitted reads it from the REFERENCE run provenance')
    args = parser.parse_args()
    run, out = args.run.resolve(), args.out.resolve()
    require(out.is_relative_to(ROOT / 'diagnostics') and not out.exists(), 'Require fresh diagnostics output')
    manifest_path, manifest, err_paths, completion = completion_inputs(run, args.completion_receipt)
    end = int(manifest['terminal_sec'] if completion is None else completion['terminal_sec'])
    files = list((run / 'vissim_eval').glob('*.fzp'))
    require(len(files) == 1, 'Expected one complete FZP')
    fzp = files[0]
    stat = (fzp.stat().st_size, fzp.stat().st_mtime_ns)
    document = load(MEMBERSHIP)
    membership = physical_membership_from_ledger(document)
    require(sum(membership.values()) == 635 and len(membership) == 1236, 'Unexpected fixed area membership')
    bounds, addresses, geometry_proof = cell_geometry(args.geometry_vbs)
    warnings, err_proof = [], []
    for path in err_paths:
        data = path.read_bytes()
        if completion is not None:
            item = next(r for r in completion['error_files'] if r['name'] == path.name)
            require(len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'], 'Canonical ERR changed before parsing')
        parsed = parse_bytes(data)
        require(not parsed['partial_tail_bytes'] and not parsed['unparsed_removal_lines'], 'Incomplete native removal lines')
        warnings.extend(parsed['events'])
        err_proof.append({'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'counts': parsed['counts']})
    removals = [e for e in warnings if e['kind'] == 'lane_change_removal']
    require(len({(e['vehicle_id'], e['link'], e['time_sec']) for e in removals}) == len(removals), 'Duplicate native removal records')
    evidence = {'path': str(fzp), 'bytes': stat[0]}
    started = time.perf_counter()
    result = summarize_stream(native_frames(fzp, evidence, deadline=time.monotonic() + 1800), membership,
        terminal_lengths(document), bounds, addresses, removals, end=end)
    elapsed = time.perf_counter() - started
    require(stat == (fzp.stat().st_size, fzp.stat().st_mtime_ns), 'FZP changed while measuring')
    out.mkdir()
    for name, key in [('area_timeseries', 'area_rows'), ('roads_30s', 'road_samples'), ('fw_cells_30s', 'cell_samples'),
                      ('road_windows_900s', 'road_windows'), ('road_recovery', 'recovery'), ('source_inputs_900s', 'source_inputs')]:
        write_csv(out / (name + '.csv'), result[key])
    save(out / 'area_metrics.json', result['metrics'])
    report = {'schema': 'fast-nc-summary/v1', 'status': 'TD_REVIEW_REQUIRED' if result['terminal_conflicts'] else 'complete',
        'run': str(run), 'manifest': str(manifest_path), 'network': manifest.get('network'),
        'prepared': manifest.get('prepared'), 'seed': manifest.get('seed'), 'terminal_sec': end,
        'fzp': evidence, 'elapsed_sec_not_benchmark': elapsed,
        'producer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'common_source_inventory_rechecked': False, 'membership_network': document['network'], 'geometry': geometry_proof,
        'ttt_veh_h': result['metrics']['ttt_veh_h'], 'td_observed_plus_terminal_canonical': result['metrics']['ttd_observed_plus_terminal_events'],
        'TD_usable_for_ranking': not bool(result['terminal_conflicts']), 'terminal_removal_collisions': result['terminal_conflicts'],
        'censored_end_n': result['metrics']['censored_last_observed_inside_vehicles'],
        'unknown_inside_disappearances': result['metrics']['unresolved_inside_disappearances'],
        'max_area_closure': result['metrics']['closure']['max_abs_residual_veh'], 'road_closure_checks': result['road_closure_checks'],
        'native_ERR': err_proof, 'native_removals': len(removals),
        'native_removals_inside': sum(membership.get(e['link']) is True for e in removals),
        'native_removals_outside': sum(membership.get(e['link']) is False for e in removals),
        'native_removals_unknown_membership': sum(e['link'] not in membership for e in removals),
        'removal_matches': result['removal_matches'],
        'unmatched_native_removal_indices': result['unmatched_native_removal_indices'],
        'unfinished_inputs': [e for e in warnings if e['kind'] == 'unfinished_vehicle_input'],
        'source_input_scope': {'verified_isolated_sources': ISOLATED_INPUTS,
            'excluded': {'1099': 'source26 has incoming connector10480; first appearance cannot be uniquely attributed'},
            'observation': 'First-ever sampled ID on an isolated source; seen-ID reappearance excluded. Insertions that traverse the entire source between1s frames can be missed; not desired demand.'},
        'limits': ['No whole-ID blacklist: earlier legal outside exits remain counted.',
            'Common membership/geometry equivalence is the parent experiment preparation prerequisite; this summarizer does not independently revalidate network variants.',
            'Terminal deletion candidates match ID+link and warning time within +/-1s of disappearance upper frame; collisions hold TD ranking, not silently subtract.',
            'Road stopped is speed<=1; area slow residence is speed<5. Empty speed is null; cell speed analysis requires count>=5.',
            'All1s transitions counted; only road/cell output downsampled to30s. Short between-frame passages can be missed.',
            'No signal/route/capacity inference. Stock decline with removal is not service recovery.']}
    if completion is not None:
        report.update(schema='physical-run-summary/v1', completion_evidence=completion, controller=completion['controller'])
    save(out / 'summary.json', report)
    print(json.dumps({k: report[k] for k in ('status', 'ttt_veh_h', 'td_observed_plus_terminal_canonical', 'unknown_inside_disappearances', 'native_removals', 'elapsed_sec_not_benchmark')}))


if __name__ == '__main__':
    main()
