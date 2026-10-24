"""Post-run rule-control evidence; no COM, optimizer, parameter fitting or new plant.

native: one FZP pass through the canonical Omega accountant, with physical link
         flows/residence added for eight independent ramps and off-ramp branches.
replay: one recorded initial state/forecast and one canonical450s endpoint, with
         actual commands at its existing150s interval calls; no state reset.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import pickle
import re
import struct
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def table(path, rows):
    require(bool(rows), 'No rows for ' + str(path))
    with Path(path).open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_table(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def geometry(mapping):
    bounds, addresses = {}, {}
    for fw, row in mapping['freeway_model_links'].items():
        direction = fw.removeprefix('FW_')
        bounds[direction] = list(map(float, row['segment_bounds_m']))
        require(len(bounds[direction]) == 22, 'Expected current 21 cells per direction')
        for physical, offset in zip(row['chain_links'], row['chain_offsets_m']):
            require(int(physical) not in addresses, 'Overlapping freeway physical chains')
            addresses[int(physical)] = (direction, float(offset))
    return bounds, addresses


def connector_geometry(network, selected):
    """Read all direct alternatives before testing any selected ramp connector."""
    pairs, connectors = defaultdict(list), {}
    for node in ET.parse(network).findall('./links/link'):
        source, target = node.find('fromLinkEndPt'), node.find('toLinkEndPt')
        if source is None or target is None:
            continue
        before, before_lane = map(int, source.get('lane').split())
        after, after_lane = map(int, target.get('lane').split())
        number = int(node.get('no'))
        pairs[before, after].append(number)
        if number not in selected:
            continue
        points = [tuple(float(p.get(k, 0)) for k in ('x', 'y', 'zOffset'))
                  for p in node.findall('./geometry/linkPolyPts/linkPolyPoint')]
        connectors[number] = {'connector': number, 'from_link': before, 'to_link': after,
            'from_lane': before_lane, 'to_lane': after_lane, 'lanes': len(node.findall('./lanes/lane')),
            'from_pos_m': float(source.get('pos')), 'to_pos_m': float(target.get('pos')),
            'length_m': math.fsum(math.dist(a, b) for a, b in zip(points, points[1:]))}
    require(set(connectors) == set(selected), 'Missing requested ramp connector geometry')
    relevant = {key: values for key, values in pairs.items() if set(values) & set(selected)}
    for row in connectors.values():
        row['all_direct_connector_alternatives'] = pairs[row['from_link'], row['to_link']]
    return connectors, relevant


def short_completion(run, end):
    """Check terminal execution evidence without widening the old 5400s tool.

    This is an observation certificate, not an LDP/VSL actuation certificate.
    The independent canonical native actuation audit remains required.
    """
    path = run / 'completion_receipt.json'
    receipt = load(path)
    require(receipt.get('schema') == 'selected-control-completion/v1'
            and receipt.get('completed') is True and receipt.get('exit_code') == 0
            and receipt.get('owned_native_alive') is False, 'Uncompleted native run')
    require(receipt.get('terminal_sec') == end and receipt.get('name') == run.name
            and Path(receipt['run_directory']).resolve() == run, 'Receipt identity/end differs')
    prov_path = Path(receipt['provenance_path']).resolve()
    require(prov_path == run / ('run_provenance_' + run.name + '.json')
            and sha(prov_path) == receipt['provenance_sha256'], 'Provenance identity/SHA differs')
    provenance = load(prov_path)
    require(provenance['run_id'] == receipt['run_id'] and provenance['sim_period_sec'] == end,
            'Provenance run/end differs')
    log_path = Path(receipt['runlog_path']).resolve()
    require(log_path == run / ('runlog_' + run.name + '.txt'), 'Runlog identity differs')
    # Canonical cscript logs contain cp949 path text; all certificate tokens are ASCII.
    log = log_path.read_text(encoding='utf-8-sig', errors='replace')
    require(re.search(r'^STAGE=SIM_DONE\s*$', log, re.M)
            and not any(x in log for x in ('ERROR=', 'DIAGNOSTIC_DECISION_FAILED', 'STRICT_DECISION_FAILED')),
            'Native terminal log failed/incomplete')
    seconds = re.findall(r'^SIM_SEC=([^\r\n]+)', log, re.M)
    require(seconds and float(seconds[-1]) == end, 'Native progress does not reach terminal')
    for key in ('DECISIONS_FAILED', 'OBSERVATION_FAILURES', 'SIGNAL_FAILURES',
                'ACTION_FORMAT_FAILURES', 'COM_FAILURES'):
        require(re.findall(r'^' + key + r'=([^\r\n]+)', log, re.M) == ['0'], key + ' not zero')
    state_csv = Path(receipt['state_csv_path']).resolve()
    require(state_csv == run / ('state_' + run.name + '.csv'), 'State CSV identity differs')
    state_rows = read_table(state_csv)
    require(state_rows and float(state_rows[-1]['sim_sec']) == end
            and all('fallback' not in r.get('controller_status', '').lower() for r in state_rows),
            'Incomplete/fallback state CSV')
    errors = []
    for item in receipt['error_files']:
        err = Path(item['path']).resolve()
        require(err.parent == run and err.name == item['name'] and err not in errors
                and err.stat().st_size == item['bytes'] and sha(err) == item['sha256'],
                'ERR identity/SHA mismatch')
        errors.append(err)
    require(any(re.fullmatch(r'vissim_simulation_\d+\.err', x.name) for x in errors),
            'Missing native runtime ERR')
    return receipt, errors, {'receipt_sha256': sha(path), 'provenance_sha256': sha(prov_path),
                             'runlog_sha256': sha(log_path)}


def native(args):
    from diagnostics import summarize_fast_nc as canonical
    from diagnostics.capture_native_runtime_errors import parse_bytes
    run, out = args.run.resolve(), args.out.resolve()
    require(not out.exists(), 'Preserve prior analysis; choose a fresh output')
    preserve = bool(getattr(args, 'native_preserve', False))
    if preserve:
        manifest_path, receipt, errors, _ = canonical.completion_inputs(run)
        require(receipt.get('native_preserve') is True and receipt['terminal_sec'] == args.end,
                'Expected completed native-preserve run at the requested horizon')
        prepared = load(Path(receipt['prepared'])/'prepared.json')
        network = Path(receipt['network'])
        require(prepared['mode'] == 'native_preserve'
                and prepared['network'] == str(network)
                and all(sha(Path(p)) == digest for p,digest in prepared['snapshot_sha256'].items()),
                'Native-preserve snapshot identity changed')
        pins = {'run_manifest_sha256':sha(manifest_path),
                'prepared_manifest_sha256':sha(Path(receipt['prepared'])/'prepared.json'),
                'native_network_sha256':sha(network)}
    else:
        receipt, errors, pins = short_completion(run, args.end)
    config = load(args.config)
    mapping = load(ROOT / config['mapping_json'])
    bounds, addresses = geometry(mapping)
    document = load(canonical.MEMBERSHIP)
    membership = canonical.physical_membership_from_ledger(document)
    off_paths = [value['offramp_route_inventory'] for value in config.values()
                 if isinstance(value, dict) and 'offramp_route_inventory' in value]
    require(len(off_paths) == 1, 'Exactly one canonical off-ramp route inventory required')
    off_specs = load(ROOT / off_paths[0])['groups']
    selected_connectors = {int(r['connector']) for r in mapping['ramp_meters']}
    selected_connectors.update(int(row[b + '_connector']) for row in off_specs.values() for b in ('signal', 'direct'))
    if not preserve:
        native_provenance = load(Path(receipt['provenance_path']))
        network = Path(native_provenance['files']['network']['path'])
    connectors, skipped_pairs = connector_geometry(network, selected_connectors)
    removals, error_rows = [], []
    for err in errors:
        parsed = parse_bytes(err.read_bytes())
        require(not parsed['partial_tail_bytes'] and not parsed['unparsed_removal_lines'],
                'Incomplete native error lines')
        removals.extend(x for x in parsed['events'] if x['kind'] == 'lane_change_removal')
        error_rows.append({'path': str(err), 'sha256': sha(err), **parsed})
    require(len({(x['vehicle_id'], x['link'], x['time_sec']) for x in removals}) == len(removals),
            'Duplicate native removals')
    files = list((run / 'vissim_eval').glob('*.fzp'))
    require(len(files) == 1, 'Exactly one completed native FZP required')
    fzp = files[0]
    before = (fzp.stat().st_size, fzp.stat().st_mtime_ns)
    evidence, previous, old_counts, old_stopped = {}, {}, Counter(), Counter()
    links, pairs = {}, Counter()
    ambiguous, jump_events, max_speeds = Counter(), [], Counter()
    prefix_hash, prefix_frames, prefix_rows = hashlib.sha256(), 0, 0

    def frames():
        nonlocal previous, old_counts, old_stopped, prefix_frames, prefix_rows
        for sec, current in canonical.native_frames(fzp, evidence, deadline=time.monotonic() + 1800):
            if sec <= 900:
                # Hash canonical parsed values in vehicle-ID order, not raw FZP bytes.
                prefix_hash.update(struct.pack('>qq', sec, len(current)))
                for vehicle, row in sorted(current.items()):
                    prefix_hash.update(struct.pack('>qqqqdd', sec, vehicle, row[0], row[1], row[2], row[3]))
                prefix_frames += 1
                prefix_rows += len(current)
            block = (sec - 1) // 150 * 150
            counts, stopped, entries, departures, absent, lane_changes = (Counter() for _ in range(6))
            for vehicle, row in current.items():
                road = row[0]
                counts[road] += 1
                stopped[road] += row[3] <= 1
                max_speeds[road] = max(max_speeds[road], row[3])
                old = previous.get(vehicle)
                if old is None or old[0] != road:
                    entries[road] += 1
                elif old[1] != row[1]:
                    lane_changes[road] += 1
            for vehicle, old in previous.items():
                row = current.get(vehicle)
                if row is None:
                    absent[old[0]] += 1
                elif old[0] != row[0]:
                    departures[old[0]] += 1
                    pairs[block, old[0], row[0]] += 1
                    choices = skipped_pairs.get((old[0], row[0]))
                    if choices:
                        jump_events.append({'vehicle_id': vehicle, 'lower_sec': sec - 1, 'upper_sec': sec,
                            'before': list(old), 'after': list(row), 'candidate_connectors': choices,
                            'status': 'unresolved_parent_road_jump_not_added_to_merge_or_exit_count'})
                        for connector in set(choices) & selected_connectors:
                            ambiguous[block, connector] += 1
            for road in counts.keys() | old_counts.keys():
                key = block, road
                value = links.setdefault(key, {'start_sec': block, 'end_sec': block + 150,
                    'link': road, 'inside_omega': membership[str(road)], 'start_n': old_counts[road],
                    'end_n': 0, 'ttt_veh_h': 0., 'stopped_veh_h': 0., 'entries': 0,
                    'observed_other_link_exits': 0, 'unresolved_absences': 0, 'same_link_lane_changes': 0})
                value['ttt_veh_h'] += (old_counts[road] + counts[road]) / 7200
                value['stopped_veh_h'] += (old_stopped[road] + stopped[road]) / 7200
                value['end_n'] = counts[road]
                for field, amount in (('entries', entries[road]), ('observed_other_link_exits', departures[road]),
                                      ('unresolved_absences', absent[road]), ('same_link_lane_changes', lane_changes[road])):
                    value[field] += amount
                require(old_counts[road] + entries[road] - departures[road] - absent[road] == counts[road],
                        'Native physical link conservation failure')
            previous, old_counts, old_stopped = current, counts, stopped
            if sec % 900 == 0:
                print(json.dumps({'native': run.name, 'scanned_sec': sec}), flush=True)
            yield sec, current

    started = time.perf_counter()
    result = canonical.summarize_stream(frames(), membership, canonical.terminal_lengths(document),
                                         bounds, addresses, removals, end=args.end)
    require(before == (fzp.stat().st_size, fzp.stat().st_mtime_ns), 'FZP changed during post-run scan')
    require(prefix_frames == 900, 'Common warmup must include every native1s frame through900')
    total = math.fsum(x['ttt_veh_h'] for x in links.values() if x['inside_omega'])
    require(math.isclose(total, result['metrics']['ttt_veh_h'], abs_tol=1e-7), 'Omega TTT cross-check failed')
    ramps, offramps = [], []
    for block in range(0, args.end, 150):
        for row in mapping['ramp_meters']:
            connector, approach, mainline = (int(row[k]) for k in ('connector', 'from_link', 'to_link'))
            stock = links.get((block, connector), {})
            source = links.get((block, approach), {})
            ramps.append({'start_sec': block, 'end_sec': block + 150, 'ramp': row['id'],
                'connector': connector, 'from_link': approach, 'to_link': mainline,
                'observed_connector_to_mainline': pairs[block, connector, mainline],
                'ambiguous_parent_road_jumps': ambiguous[block, connector],
                'connector_departures_to_other_links': stock.get('observed_other_link_exits', 0) - pairs[block, connector, mainline],
                'connector_unresolved_absences': stock.get('unresolved_absences', 0),
                'observed_approach_to_connector': pairs[block, approach, connector],
                'connector_end_n': stock.get('end_n', 0), 'connector_ttt_veh_h': stock.get('ttt_veh_h', 0.),
                'connector_stopped_veh_h': stock.get('stopped_veh_h', 0.),
                'approach_all_destinations_end_n': source.get('end_n', 0),
                'approach_all_destinations_ttt_veh_h': source.get('ttt_veh_h', 0.)})
        for group, spec in off_specs.items():
            for branch in ('signal', 'direct'):
                connector = int(spec[branch + '_connector'])
                stock = links.get((block, connector), {})
                offramps.append({'start_sec': block, 'end_sec': block + 150, 'group': group,
                    'branch': branch, 'connector': connector,
                    'observed_mainline_to_connector': sum(pairs[block, road, connector] for road in addresses),
                    'ambiguous_parent_road_jumps': ambiguous[block, connector],
                    'connector_end_n': stock.get('end_n', 0),
                    'connector_ttt_veh_h': stock.get('ttt_veh_h', 0.),
                    'connector_stopped_veh_h': stock.get('stopped_veh_h', 0.)})
    out.mkdir(parents=True)
    for filename, key in (('area_timeseries', 'area_rows'), ('roads_30s', 'road_samples'),
                          ('fw_cells_30s', 'cell_samples'), ('road_recovery', 'recovery')):
        table(out / (filename + '.csv'), result[key])
    table(out / 'links_150s.csv', [links[k] for k in sorted(links)])
    table(out / 'link_pairs_150s.csv', [{'start_sec': k[0], 'end_sec': k[0] + 150,
          'from_link': k[1], 'to_link': k[2], 'vehicles': v} for k, v in sorted(pairs.items())])
    table(out / 'ramps_150s.csv', ramps)
    table(out / 'offramps_150s.csv', offramps)
    save(out / 'connector_transition_evidence.json', {'network_path': str(network), 'network_sha256': sha(network),
        'geometry': connectors, 'max_observed_speed_kph_by_selected_connector': {str(k): max_speeds[k] for k in connectors},
        'total_direct_parent_road_jumps': len(jump_events), 'classified_jump_events': jump_events,
        'scope': 'Explicit observed connector endpoints only. Potential parent-road jumps across selected connectors are preserved unresolved and never added to counts. Their absence, connector lengths, and observed speeds provide coverage evidence without a new route-inference model.'})
    save(out / 'area_metrics.json', result['metrics'])
    save(out / 'summary.json', {'schema': 'rule-native-postrun/v1', 'completed': True, 'run': str(run),
        'end_sec': args.end, 'fzp': evidence, 'elapsed_sec': time.perf_counter() - started,
        'common_warmup': {'requested_window_sec': [0, 900], 'recorded_frame_window_sec': [1, 900],
            'frames': prefix_frames, 'vehicle_rows': prefix_rows,
            'canonical_parsed_vehicle_tuple_sha256': prefix_hash.hexdigest(),
            'fields': ['sim_sec', 'vehicle_id', 'link', 'lane', 'pos_m', 'speed_kph'],
            'encoding': 'Big-endian signed64 integers for frame sec/count and sec/ID/link/lane; IEEE754 binary64 position/speed; rows ordered by vehicleID within each chronological frame.',
            'scope': 'Values yielded by unchanged canonical native_frames in this same full-file pass. This is not a raw FZP data-row hash and does not cover additional FZP columns. No0s frame synthesized.'},
        'execution_audit_separate': True, 'completion_pins': pins, 'native_errors': error_rows,
        'native_preserve': preserve,
        'configuration_use': 'Physical address catalog only; no plant predictions or historic traffic parameters applied' if preserve else 'Existing rule experiment address catalog',
        'native_removals': len(removals), 'terminal_conflicts': result['terminal_conflicts'],
        'removal_matches': result['removal_matches'],
        'unmatched_native_removal_indices': result['unmatched_native_removal_indices'],
        'removal_overlap_scope': 'Native warning ID/link/time matched to an observed1s disappearance; inside matches without terminal conflicts are part of the Omega unresolved-disappearance ledger, not additional losses.',
        'TTD_usable_for_ranking': not result['terminal_conflicts'],
        'limits': ['Observed 1s link pairs can skip short connectors; they are not desired demand.',
                   'Potential parent-road jumps remain unresolved; no skipped-route inference is used.',
                   'Approach stocks include all destinations; only connector stock is the disjoint ramp reservoir.',
                   'Native LDP and VSL application readback audits remain separate and required.']})
    print(json.dumps({'native_complete': run.name, 'TTT': total, 'out': str(out)}), flush=True)


def stock_group(key):
    if key.startswith('freeway:'):
        return 'mainline'
    if key.startswith(('ramp:', 'merge_pending:')):
        return 'onramp_connector_and_pending'
    return 'urban_and_other'


def scheduled_endpoint(state, actions, forecast, cfg):
    """Inject only the recorded commands at the existing three interval calls.

    The single canonical endpoint/ledger avoids reinitializing predicted stocks.
    The original coupled function and substep are always restored by patch scopes.
    No intermediate observations, demand changes, or stock rounding are allowed.
    """
    from evaluation.controllers import area_follower_objective as area, area_meter_finalization
    from src.controllers import rollout_endpoint as ep
    from src.simulation import coupling
    spec = ep.ObjectiveSpec(cfg, depth_override=len(actions), box_walk=False, score_mode='raw')
    controls = [area_meter_finalization.for_endpoint(a, (), spec) for a in actions]
    original_interval, original_step = coupling.run_coupled_interval, coupling.freeway_substep
    intervals, calls, cells = 0, 0, []
    start = state.time_sec

    def interval(current, ignored_control, demand, config):
        nonlocal intervals
        require(intervals < len(controls) and current.time_sec == start + intervals * cfg.simulation.T_c_sec,
                'Unexpected canonical interval clock/count')
        value = original_interval(current, controls[intervals], demand, config)
        intervals += 1
        return value

    def substep(*pos, **kw):
        nonlocal calls
        value = original_step(*pos, **kw)
        calls += 1
        elapsed = calls * cfg.simulation.T_f_sec
        if elapsed % 30 == 0:
            current = pos[0]
            for fw in cfg.network.freeway_links:
                for cell in range(cfg.network.freeway_segments_per_link):
                    cells.append({'sec': start + elapsed, 'direction': fw.removeprefix('FW_'),
                        'cell': cell, 'predicted_speed_kph': current.freeway_speed[fw][cell],
                        'predicted_density_veh_km_lane': current.freeway_density[fw][cell]})
        return value

    with area.shared_query_runtime_scope(), patch.object(coupling, 'run_coupled_interval', interval), \
            patch.object(coupling, 'freeway_substep', substep):
        point = ep.evaluate_price_point(state, controls[0], forecast, (), spec, capture_response=True)
    require(intervals == len(actions) and calls == len(actions) * cfg.simulation.K_cf
            and not point.aborted and len(point.states) == len(actions), 'Incomplete scheduled endpoint')
    require(coupling.run_coupled_interval is original_interval and coupling.freeway_substep is original_step,
            'Diagnostic hooks were not restored')
    return point, cells


def replay(args):
    from diagnostics.probe_model_area_integration import build_projected, replay_provenance
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers import area_follower_objective as area
    from src.controllers import rollout_endpoint as ep
    from src.models.demand import DemandStep
    from src.models.state import ControlAction
    out = args.out.resolve()
    require(not out.exists(), 'Preserve prior replay; choose a fresh output')
    run = args.run.resolve()
    decisions = run / ('decisions_' + run.name)
    initial_run = args.initial_run.resolve() if args.initial_run else run
    initial_decisions = initial_run / ('decisions_' + initial_run.name)
    start = args.start
    state_path = initial_decisions / f'state_{start:06d}.json'
    previous = [p for p in initial_decisions.glob('action_*.json')
                if re.fullmatch(r'action_\d+\.json', p.name) and int(p.stem.split('_')[-1]) < start]
    require(previous, 'Missing actual previous action')
    previous_path = max(previous, key=lambda p: int(p.stem.split('_')[-1]))
    common_initial = None
    actual_state_path = decisions / f'state_{start:06d}.json'
    if initial_run != run:
        require(start in (900, 1650), 'Only verified common900s or first-meter1650s states are authorized as same-state paired responses')
        exclusions = ('network_path', 'run_provenance.manifest_path', 'run_provenance.run_id',
                      'local_observation.signal_observation_window.config_sha256')
        normalized = []
        for path in (state_path, actual_state_path):
            data = load(path)
            for field in exclusions:
                parent = data
                keys = field.split('.')
                for key in keys[:-1]:
                    parent = parent.get(key, {})
                parent.pop(keys[-1], None)
            normalized.append(data)
        require(normalized[0] == normalized[1], 'Common initial observation/head-history identity failed')
        common_initial = {'all_observation_and_head_values_exact': True, 'metadata_exclusions': exclusions,
                          'source_state_sha256': sha(state_path), 'actual_arm_state_sha256': sha(actual_state_path)}
        if start == 1650:
            prefix_proof = []
            for sec in [1, *range(150, start, 150)]:
                paths = [folder / f'action_{sec:06d}.json' for folder in (initial_decisions, decisions)]
                records = [load(path) for path in paths]
                fields = ('vsl', 'ramp_metering', 'green_times', 'offsets')
                require(all(records[0][field] == records[1][field] for field in fields),
                        'First-meter1650s pair has different prior physical command JSON')
                writer_rows = [read_table(path.with_suffix('.csv')) for path in paths]
                normalized_rows = [[{k: v for k, v in row.items() if k != 'metadata'} for row in rows]
                                   for rows in writer_rows]
                require(normalized_rows[0] == normalized_rows[1],
                        'First-meter1650s pair has different prior physical writer CSV')
                prefix_proof.append({'sec': sec, 'physical_json_and_writer_csv_exact': True,
                    'sha256': {str(path): sha(path) for path in
                               [*paths, *(path.with_suffix('.csv') for path in paths)]}})
            common_initial['prior_physical_commands'] = prefix_proof
    config_path = args.config.resolve()
    cfg, state, detectors, tuning, raw, mapping, metadata = build_projected(
        config_path, state_path, previous_path, fixture_inputs=False)
    require(cfg.simulation.T_c_sec == 150 and cfg.mpc.horizon_steps == 3, 'Current150/450 contract required')
    cal = adapter.deep_update(adapter.load_optional_json(str(ROOT /
        'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json')),
        tuning.get('calibration_override', {}))
    forecast = adapter.demand_from_state(raw, cfg, DemandStep, 3, cal, detectors)
    forecast_hash = hashlib.sha256(pickle.dumps(forecast, protocol=5)).hexdigest()
    action_paths = [decisions / f'action_{sec:06d}.json' for sec in range(start, start + 450, 150)]
    for path in action_paths:
        require(path.is_file() and path.with_suffix('.csv').is_file(), 'Missing recorded actual action JSON/CSV: ' + str(path))
    inputs = [config_path, state_path, actual_state_path, previous_path, *action_paths, *(p.with_suffix('.csv') for p in action_paths)]
    pins_before = {str(p): sha(p) for p in inputs}
    results, cells, ramp_rows, flow_rows, binding_rows = [], [], [], [], []
    started = time.perf_counter()
    initial_stock = math.fsum(x['inside'] for x in state._control_area_ledger.stocks.values())
    initial_density = state.freeway_density
    actions = [adapter.control_from_json(path, cfg, ControlAction) for path in action_paths]
    parity = None
    if args.verify_held:
        held, _ = scheduled_endpoint(state, [actions[0]] * 3, forecast, cfg)
        with area.shared_query_runtime_scope():
            ordinary = ep.evaluate_price_point(state, actions[0], forecast, (),
                ep.ObjectiveSpec(cfg, depth_override=3, box_walk=False, score_mode='raw'), capture_response=True)
        parity = {'control_area_exact': held.control_area == ordinary.control_area,
                  'full_response_exact': held.control_area_response == ordinary.control_area_response,
                  'terminal_freeway_speed_exact': held.states[-1].freeway_speed == ordinary.states[-1].freeway_speed,
                  'terminal_density_exact': held.states[-1].freeway_density == ordinary.states[-1].freeway_density}
        require(all(parity.values()), 'Held450 schedule hook changes ordinary canonical response')
    point, cells = scheduled_endpoint(state, actions, forecast, cfg)
    response = point.control_area_response
    require(response['model_constraint_coverage']['complete'], 'Incomplete model constraint coverage')
    response_hash = hashlib.sha256(pickle.dumps(response, protocol=5)).hexdigest()
    for index in range(3):
        window_start = start + index * 150
        window_end = window_start + 150
        selected = lambda rows: [r for r in rows if window_start <= r['start_sec'] and r['end_sec'] <= window_end]
        costs = defaultdict(float)
        for sample in selected(response['residence']):
            for key, n in sample['inside_veh'].items():
                costs[stock_group(key)] += n * sample['dt_h']
        for frame in selected(response['freeway_frames']):
            for ramp, rate in frame['actual_ramp_release_veh_h'].items():
                ramp_rows.append({'start_sec': frame['start_sec'], 'end_sec': frame['end_sec'], 'ramp': ramp,
                    'predicted_accepted_merge_veh': rate * (frame['end_sec'] - frame['start_sec']) / 3600,
                    'predicted_connector_end_n': frame['model_stock_veh']['ramp:' + ramp]})
        events = selected(response['transfers'])
        for event in events:
            flow_rows.append({k: event[k] for k in ('start_sec', 'end_sec', 'stage', 'source', 'target',
                'vehicles', 'entered_veh', 'ttd_veh')})
        for event in selected(response['resource_allocations']):
            if event['kind'].startswith('ramp_release_query_'):
                binding_rows.append({k: event[k] for k in ('start_sec', 'end_sec', 'kind', 'resource',
                    'available_veh', 'accepted_total_veh')})
        terminal = point.states[index]
        require(terminal.time_sec == window_end, 'Wrong terminal state')
        results.append({'start_sec': window_start, 'end_sec': window_start + 150,
            'TTT_veh_h': math.fsum(costs.values()), 'TTD_veh': math.fsum(e['ttd_veh'] for e in events),
            'entered_veh': math.fsum(e['entered_veh'] for e in events),
            'end_omega_n': math.fsum(x['inside'] for x in terminal._control_area_ledger.stocks.values()),
            **{k + '_ttt_veh_h': costs[k] for k in ('mainline', 'onramp_connector_and_pending', 'urban_and_other')}})
        print(json.dumps({'replayed': run.name, 'start': window_start, 'TTT': results[-1]['TTT_veh_h']}), flush=True)
    require(math.isclose(math.fsum(r['TTT_veh_h'] for r in results), point.control_area['ttt_veh_h'], abs_tol=1e-7),
            'Model Omega residence windows do not sum to450s endpoint')
    require(forecast_hash == hashlib.sha256(pickle.dumps(forecast, protocol=5)).hexdigest(), 'Forecast mutated')
    require(all(sha(p) == h for p, h in pins_before.items()), 'Input changed during replay')
    out.mkdir(parents=True)
    for name, rows in (('model_windows_150s', results), ('model_cells_30s', cells),
                       ('model_ramps_10s', ramp_rows), ('model_transfers', flow_rows), ('model_meter_limits', binding_rows)):
        table(out / (name + '.csv'), rows)
    comparison = []
    if args.native:
        area_rows = {int(float(r['sim_sec'])): r for r in read_table(args.native / 'area_timeseries.csv')}
        native_ramps = read_table(args.native / 'ramps_150s.csv')
        for model in results:
            lower, upper = (area_rows[model[k]] for k in ('start_sec', 'end_sec'))
            actual = float(upper['ttt_veh_h_cumulative']) - float(lower['ttt_veh_h_cumulative'])
            td = float(upper['ttd_observed_plus_terminal_cumulative']) - float(lower['ttd_observed_plus_terminal_cumulative'])
            comparison.append({'start_sec': model['start_sec'], 'end_sec': model['end_sec'],
                'native_TTT_veh_h': actual, 'model_TTT_veh_h': model['TTT_veh_h'],
                'TTT_bias_veh_h': model['TTT_veh_h'] - actual,
                'native_TTD_veh': td, 'model_TTD_veh': model['TTD_veh'], 'TTD_bias_veh': model['TTD_veh'] - td,
                'native_end_omega_n': int(upper['inside_vehicles']), 'model_end_omega_n': model['end_omega_n']})
        table(out / 'comparison_150s.csv', comparison)
        ramp_comparison = []
        for row in native_ramps:
            lower, upper = int(row['start_sec']), int(row['end_sec'])
            if start <= lower and upper <= start + 450:
                model = [r for r in ramp_rows if r['ramp'] == row['ramp']
                         and lower <= r['start_sec'] and r['end_sec'] <= upper]
                require(len(model) == cfg.simulation.K_cf, 'Missing model ramp intervals')
                predicted = math.fsum(r['predicted_accepted_merge_veh'] for r in model)
                actual = int(row['observed_connector_to_mainline'])
                ramp_comparison.append({'start_sec': lower, 'end_sec': upper, 'ramp': row['ramp'],
                    'native_explicit_merges_veh': int(row['observed_connector_to_mainline']),
                    'native_merge_lower_bound_veh': actual, 'model_accepted_merges_veh': predicted,
                    'model_minus_native_lower_bound_veh': predicted - actual,
                    'native_ambiguous_parent_jumps': int(row['ambiguous_parent_road_jumps']),
                    'native_connector_end_n': int(row['connector_end_n']),
                    'model_connector_end_n': model[-1]['predicted_connector_end_n'],
                    'native_connector_ttt_veh_h': float(row['connector_ttt_veh_h'])})
        table(out / 'comparison_ramps_150s.csv', ramp_comparison)
        observed = {(int(r['sec']), r['direction'], int(r['cell'])): r
                    for r in read_table(args.native / 'fw_cells_30s.csv')}
        for cell in cells:
            actual = observed[(int(cell['sec']), cell['direction'], cell['cell'])]
            cell.update(native_n=int(actual['n']), native_speed_kph=float(actual['mean_speed_kph'])
                        if actual['mean_speed_kph'] else None)
        table(out / 'comparison_cells_30s.csv', cells)
    save(out / 'summary.json', {'schema': 'rule-executed-command-plant-replay/v1', 'completed': True,
        'run': str(run), 'window_sec': [start, start + 450], 'native_run': False, 'solver_calls': 0,
        'initial_run': str(initial_run), 'common_initial_identity': common_initial,
        'endpoint_calls': 3 if args.verify_held else 1, 'held_schedule_parity': parity,
        'wall_sec': time.perf_counter() - started,
        'initial_omega_n': initial_stock, 'initial_freeway_density': initial_density,
        'forecast_sha256': forecast_hash, 'response_sha256': response_hash,
        'control_area': point.control_area,
        'model_constraint_coverage': response['model_constraint_coverage'],
        'physical_ramp_catalog': cfg.network.physical_ramp_branches['ramps'],
        'offramp_branch_catalog': cfg.network.offramp_route_inventory['branches'],
        'applied_controls_by150': [{'start_sec': frame['start_sec'], 'control': frame['applied_control']}
            for frame in response['freeway_frames'] if (frame['start_sec'] - start) % 150 == 0],
        'source_sha256': replay_provenance(tuning, *inputs, Path(__file__)),
        'TTT_veh_h': math.fsum(r['TTT_veh_h'] for r in results),
        'TTD_veh': math.fsum(r['TTD_veh'] for r in results),
        'limits': ['Post-hoc executed-command replay; future actions are supplied but future observations/demand are not.',
                   'One observed initial state and forecast; one450s canonical endpoint with recorded commands at its existing150s calls. No stock reinitialization or rounding.',
                   'Native command application must separately pass LDP and VSL readback audits.',
                   'Each arm has its own evolved initial state except explicitly verified common900s or same-history first-meter1650s pairs; other late-arm differences are policy trajectories, not same-state counterfactuals.',
                   'Native 1s connector-to-mainline pair counts can miss short connector passages.']})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='mode', required=True)
    for name in ('native', 'replay'):
        sub = subs.add_parser(name)
        sub.add_argument('--run', type=Path, required=True)
        sub.add_argument('--config', type=Path, required=True)
        sub.add_argument('--out', type=Path, required=True)
        if name == 'native':
            sub.add_argument('--end', type=int, required=True)
            sub.add_argument('--native-preserve', action='store_true',
                             help='Read a completed saved-network fast run; never infer a selected-control receipt')
        else:
            sub.add_argument('--start', type=int, required=True)
            sub.add_argument('--native', type=Path)
            sub.add_argument('--initial-run', type=Path, help='Only900s or1650s: explicit common initial state after observation/head identity check;1650s also requires identical prior physical JSON/CSV commands; use the same physical config within each pair')
            sub.add_argument('--verify-held', action='store_true', help='Once only: two extra450s queries prove ordinary held-command response equality')
    args = parser.parse_args()
    os.chdir(ROOT)
    require(not args.out.exists(), 'Preserve prior output')
    try:
        (native if args.mode == 'native' else replay)(args)
    except Exception:
        args.out.mkdir(parents=True, exist_ok=True)
        save(args.out / 'failure.json', {'completed': False, 'mode': args.mode,
            'run': str(args.run), 'error': traceback.format_exc()})
        raise


if __name__ == '__main__':
    main()
