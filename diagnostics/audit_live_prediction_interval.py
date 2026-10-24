"""Replay one recorded action, then audit its observed interval. No VISSIM access.

Uses the installed canonical endpoint and the historical interval measurer's
physical accounting. Outputs are new files; historical evidence is never replaced.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import pickle
import sys
import time
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
from diagnostics.live_beta0_interval_prediction import read_physical_window
from diagnostics.live_beta0_first_interval_audit import stable_rows
from diagnostics.signal_readback_cadence import strict_signal_trace, vsl_readback_matches
from diagnostics.probe_model_area_integration import build_projected, replay_provenance
from evaluation.controllers import area_runtime, vissim_stackelberg_adapter as adapter
from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts
from evaluation.controllers.control_area_objective import physical_membership_from_ledger
from evaluation.controllers.signal_timing_oracle import decisions_from_action_rows
from scripts.measure_control_area import terminal_lengths
from src.controllers import rollout_endpoint
from src.models.demand import DemandStep
from src.models.state import ControlAction, segment_vsl
from src.simulation import coupling


class PendingObservation(ValueError):
    """A live output has not yet closed the requested observation interval."""


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative(path):
    path = Path(path).resolve()
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)


def complete_frames(reader, start, end, deadline, provenance):
    """Require a later complete row to prove the final timestamp block is closed.

    The bounded binary seek never reads future data into the model. Exact sampled
    byte ranges are rehashed after measurement; a growing suffix is harmless.
    """
    reader.seek_time(start)
    current, current_t = {}, None
    digest, count, first, last, lookahead = hashlib.sha256(), 0, None, None, None
    while row := reader.line():
        if not row.endswith(b'\n'):
            raise PendingObservation('FZP has an incomplete row; wait for the writer.')
        fields = row.rstrip(b'\r\n').split(b';')
        if len(fields) != len(reader.names):
            raise ValueError('Malformed FZP row or repeated schema.')
        sec = float(fields[reader.index['SIMSEC']])
        if not math.isfinite(sec):
            raise ValueError('Nonfinite FZP timestamp.')
        if sec < start:
            continue
        if sec > end:
            lookahead = sec
            break
        if current_t is not None and sec < current_t:
            raise ValueError('FZP timestamps decreased.')
        if current_t is not None and sec != current_t:
            if time.monotonic() > deadline:
                raise RuntimeError('Bounded interval read time exhausted.')
            yield current_t, current
            current = {}
        current_t = sec
        if first is None:
            first = reader.handle.tell()-len(row)
        last = reader.handle.tell()
        digest.update(row)
        count += 1
        i = reader.index
        no = int(fields[i['NO']])
        values = (int(fields[i['LANE\\LINK\\NO']]), int(fields[i['LANE\\INDEX']]),
                  float(fields[i['POS']]), float(fields[i['SPEED']]))
        if no in current or any(not math.isfinite(x) for x in values) or values[3] < 0:
            raise ValueError('Duplicate ID or invalid physical values in FZP frame.')
        current[no] = values
    if current_t != end or lookahead is None:
        raise PendingObservation(f'FZP interval not closed: expected {end} and a later row; wait for the writer.')
    yield current_t, current
    provenance.append({'start_sec': start, 'end_sec': end, 'rows': count,
                       'first_byte': first, 'end_byte_exclusive': last,
                       'raw_range_sha256': digest.hexdigest(), 'lookahead_sec': lookahead})


def verify_ranges(path, ranges):
    with Path(path).open('rb') as stream:
        for row in ranges:
            stream.seek(row['first_byte'])
            data = stream.read(row['end_byte_exclusive']-row['first_byte'])
            if hashlib.sha256(data).hexdigest() != row['raw_range_sha256']:
                raise ValueError('Measured FZP byte range changed during the audit.')


def stock_snapshot(state, cfg):
    cells = continuity_vehicle_counts(state, cfg)
    freeway = sum(sum(x) for x in cells.values())
    omega = sum(row['inside'] for row in state._control_area_ledger.stocks.values())
    return {'omega_veh': omega, 'freeway_veh': freeway,
            'urban_and_ramps_veh': omega-freeway, 'freeway_cells_veh': cells,
            'freeway_speed_kph': copy.deepcopy(state.freeway_speed),
            'freeway_density_veh_km_lane': copy.deepcopy(state.freeway_density),
            'freeway_effective_lanes': copy.deepcopy(state.freeway_effective_lanes),
            'freeway_continuity_cell_length_km': cfg.network.freeway_segment_length_km,
            'ramp_queues_veh': dict(state.ramp_queue),
            'storage_occupancy_veh': {key: cfg.network.urban_link_storage_veh[key]-space
                                    for key, space in state.urban_link_storage.items()},
            'native_inputs': copy.deepcopy(getattr(state, 'native_internal_input_state', {})),
            'sc15_route_sources': copy.deepcopy(getattr(state, 'route_choice_corridor_state', {}))}


def raw_stock(raw, membership, freeway_sets):
    rows = raw['vehicle_records']['records']
    if not raw['vehicle_records'].get('complete') or len(rows) != raw['vehicle_records']['record_count']:
        raise ValueError('Paused COM snapshot is incomplete.')
    if len({r['veh_no'] for r in rows}) != len(rows):
        raise ValueError('Paused COM snapshot repeats vehicle IDs.')
    counts = Counter(str(r['link_no']) for r in rows)
    if counts.keys()-membership.keys():
        raise ValueError('Paused COM snapshot has unknown physical membership.')
    fw = set().union(*freeway_sets.values())
    omega = sum(value for key, value in counts.items() if membership[key])
    freeway = sum(value for key, value in counts.items() if key in fw)
    return {'omega_veh': omega, 'freeway_veh': freeway,
            'urban_and_ramps_veh': omega-freeway}


def component_errors(model, observed):
    errors = {key: model[key]-observed[key] for key in
              ('omega_veh', 'freeway_veh', 'urban_and_ramps_veh')}
    absolute = abs(errors['freeway_veh'])+abs(errors['urban_and_ramps_veh'])
    return {'model_minus_observed': errors, 'sum_absolute_component_errors_veh': absolute,
            'cancellation_veh': max(0., absolute-abs(errors['omega_veh'])),
            'definition': 'Cancellation = |FW error| + |urban/ramp error| - |Omega error|.'}


def compare_freeway_cells(initial, final, raw_start, raw_end, mapping, trace, *, threshold_kph=60.):
    """Compare identical COM cells; empty-cell speed is unavailable, never zero.

    Native density uses its recorded physical length/lanes. A second density
    comparison converts observed N into the model's scalar continuity geometry.
    This avoids hiding a length/lanes convention difference in a stock error.
    """
    if raw_end is None:
        return {'available': False, 'reason': 'No paused final COM cell snapshot.', 'rows': []}
    rows = []
    def observed(row):
        n, length, lanes, speed_sum = (float(row[key]) for key in ('count', 'length_km', 'lanes', 'speed_sum'))
        if not all(math.isfinite(x) for x in (n, length, lanes, speed_sum)) or min(n, speed_sum) < 0 or min(length, lanes) <= 0:
            raise ValueError('Invalid COM cell count, geometry or speed moment.')
        if n == 0 and speed_sum != 0:
            raise ValueError('Empty COM cell has a nonzero speed moment.')
        return n, speed_sum/n if n else None, n/(length*lanes), length, lanes
    def regime(n, speed):
        return 'empty' if n == 0 else 'below_threshold' if speed < threshold_kph else 'at_or_above_threshold'
    def evolution(before, after):
        if 'empty' in (before, after): return 'empty_endpoint_unknown'
        if before == after: return 'persistent_congestion' if before == 'below_threshold' else 'persistent_uncongested'
        return 'recovery' if before == 'below_threshold' else 'congestion_onset'
    for link, counts in final['freeway_cells_veh'].items():
        before_obs, after_obs = raw_start['freeway_segments'][link], raw_end['freeway_segments'][link]
        bounds = mapping['freeway_model_links'][link]['segment_bounds_m']
        vectors = [initial['freeway_cells_veh'][link], initial['freeway_speed_kph'][link],
                   final['freeway_speed_kph'][link], final['freeway_density_veh_km_lane'][link],
                   final['freeway_effective_lanes'][link], before_obs, after_obs]
        if any(len(vector) != len(counts) for vector in vectors) or len(bounds) != len(counts)+1:
            raise ValueError('Model, mapping and COM cell axes differ.')
        for cell, predicted_count in enumerate(counts):
            n0, v0, rho0, _, _ = observed(before_obs[cell])
            n1, v1, rho1, length, lanes = observed(after_obs[cell])
            pred_v0, pred_v1 = initial['freeway_speed_kph'][link][cell], final['freeway_speed_kph'][link][cell]
            pred_n0 = initial['freeway_cells_veh'][link][cell]
            pred_rho = final['freeway_density_veh_km_lane'][link][cell]
            model_length = final['freeway_continuity_cell_length_km']
            model_lanes = final['freeway_effective_lanes'][link][cell]
            if model_length <= 0 or model_lanes <= 0:
                raise ValueError('Invalid model cell geometry in diagnostic snapshot.')
            predicted_evolution = evolution(regime(pred_n0, pred_v0), regime(predicted_count, pred_v1))
            observed_evolution = evolution(regime(n0, v0), regime(n1, v1))
            previous = regime(pred_n0, pred_v0)
            crossings = []
            for step in trace:
                current = regime(step['cell_counts_veh'][link][cell], step['cell_speed_kph'][link][cell])
                if current != previous:
                    crossings.append({'elapsed_sec': step['elapsed_sec'], 'from': previous, 'to': current})
                previous = current
            rows.append({'link': link, 'cell_index_zero_based': cell, 'chain_start_m': bounds[cell], 'chain_end_m': bounds[cell+1],
                'initial_model_count_veh': pred_n0, 'initial_observed_count_veh': n0,
                'predicted_count_veh': predicted_count, 'observed_count_veh': n1, 'count_error_veh': predicted_count-n1,
                'initial_model_speed_kph': pred_v0, 'initial_observed_speed_kph': v0,
                'predicted_speed_kph': pred_v1, 'observed_speed_kph': v1, 'speed_error_kph': pred_v1-v1 if v1 is not None else None,
                'predicted_speed_change_kph': pred_v1-pred_v0, 'observed_speed_change_kph': v1-v0 if v0 is not None and v1 is not None else None,
                'predicted_density_veh_km_lane': pred_rho, 'observed_density_veh_km_lane': rho1,
                'density_error_physical_geometry_veh_km_lane': pred_rho-rho1,
                'observed_density_in_model_continuity_units': n1/(model_length*model_lanes),
                'density_error_same_continuity_geometry': pred_rho-n1/(model_length*model_lanes),
                'observed_length_km': length, 'observed_lanes': lanes, 'model_continuity_length_km': model_length,
                'model_effective_lanes': model_lanes, 'predicted_endpoint_evolution': predicted_evolution,
                'observed_endpoint_evolution': observed_evolution,
                'false_recovery_at_endpoint': predicted_evolution == 'recovery' and observed_evolution == 'persistent_congestion',
                'missed_onset_at_endpoint': predicted_evolution == 'persistent_uncongested' and observed_evolution == 'congestion_onset',
                'predicted_threshold_crossings': crossings})
    speeds = [row['speed_error_kph'] for row in rows if row['speed_error_kph'] is not None]
    summary = {'cells': len(rows), 'nonempty_observed_cells': len(speeds),
               'speed_bias_kph': sum(speeds)/len(speeds) if speeds else None,
               'speed_mae_kph': sum(map(abs, speeds))/len(speeds) if speeds else None,
               'speed_rmse_kph': math.sqrt(sum(x*x for x in speeds)/len(speeds)) if speeds else None,
               'count_bias_sum_veh': sum(row['count_error_veh'] for row in rows),
               'count_absolute_error_sum_veh': sum(abs(row['count_error_veh']) for row in rows),
               'false_recovery_cells': [[row['link'], row['cell_index_zero_based']] for row in rows if row['false_recovery_at_endpoint']],
               'missed_onset_cells': [[row['link'], row['cell_index_zero_based']] for row in rows if row['missed_onset_at_endpoint']]}
    return {'available': True, 'threshold_kph': threshold_kph, 'summary': summary, 'rows': rows,
            'method': 'Unweighted cell speed errors on nonempty observed cells; exact same cell indices/bounds as paused COM. Density geometry conventions are both reported.',
            'timing_limit': '60 km/h is a diagnostic threshold, not a calibrated FD or control parameter. Observed evolution uses two COM endpoints; within-interval onset/recovery time is not inferred. Model threshold crossings are sampled at 10 s.'}



def audit_actuation(run, csv_path, start, end):
    commands = list(csv.DictReader(io.StringIO(csv_path.read_text(encoding='utf-8-sig'))))
    plans = decisions_from_action_rows([{**r, 'sim_sec': start} for r in commands])
    if not plans:
        return {'valid': False, 'reason': 'Recorded CSV contains no controlled signal plan (for example native no-control). A held JSON replay is diagnostic only.',
                'command_kinds': dict(Counter(row['kind'] for row in commands))}
    controllers = plans[0]['controllers']
    ramps = {str(int(r['sc_no'])): float(r['green_sec']) for r in commands if r['kind'] == 'ramp_meter'}
    rows, source = stable_rows(run/('decisions_'+run.name)/'signal_readback.csv')
    signal = strict_signal_trace(rows, controllers, ramps, start=start, end=end)
    applied, applied_source = stable_rows(run/('action_'+run.name+'.csv'))
    applied = [r for r in applied if float(r['sim_sec']) == start and r['kind'] == 'vsl']
    expected = [r for r in commands if r['kind'] == 'vsl']
    columns = ('id', 'dsd_no', 'link', 'lane', 'speed_kph')
    match = Counter(tuple(r[k] for k in columns) for r in applied) == Counter(tuple(r[k] for k in columns) for r in expected)
    bad = [r for r in applied if not vsl_readback_matches(r)]
    return {'signal_and_meter': signal, 'vsl_command_rows_match': match,
            'vsl_readback_mismatch_count': len(bad), 'vsl_written_rows': len(applied),
            'sources': {'signal': source, 'applied': applied_source},
            'valid': signal['valid'] and match and not bad,
            'limitation': 'SG/DSD readbacks verify actuation samples, not hard vehicle speed compliance.'}


def command_roundtrip(action, cfg, mapping, calibration, tuning, action_json, csv_path):
    """Compare physical CSV columns produced by the actual canonical writer.

    An in-memory destination supplies the writer's ordinary text stream interface;
    no actual command file is created, replaced, or applied to VISSIM.
    """
    class Sink:
        def __init__(self):
            self.parent, self.data = self, None
        def mkdir(self, **kwargs):
            pass
        def open(self, *args, **kwargs):
            owner = self
            class Stream(io.StringIO):
                def __exit__(self, *exc):
                    owner.data = self.getvalue()
                    self.close()
            return Stream(newline='')
    sink = Sink()
    held = copy.deepcopy(action)
    adapter.write_action_csv(sink, held, cfg, mapping, segment_vsl, action_json['metadata'],
        adapter.adapter_actuation_settings(calibration, tuning),
        signal_group_plan_table=adapter.load_signal_group_actuation_plan(),
        offset_writer=tuning.get('actuation', {}).get('real_world_signal_control', {}).get('offset_writer', 'intent_only'))
    expected = list(csv.DictReader(io.StringIO(sink.data)))
    actual = list(csv.DictReader(io.StringIO(csv_path.read_text(encoding='utf-8-sig'))))
    columns = [key for key in actual[0] if key != 'metadata']
    first = Counter(tuple(row[key] for key in columns) for row in expected)
    second = Counter(tuple(row[key] for key in columns) for row in actual)
    return {'physical_columns_exact': first == second, 'expected_rows': len(expected),
            'actual_rows': len(actual), 'missing_rows': list((first-second).elements())[:10],
            'extra_rows': list((second-first).elements())[:10],
            'canonical_serialized_csv_sha256': hashlib.sha256(sink.data.encode('utf-8')).hexdigest(),
            'metadata_column_excluded': 'Controller metadata tokens are provenance, not physical commands; original CSV bytes remain separately pinned.'}


def source_comparison(cfg, initial, final, physical, physical_links, detectors):
    native = getattr(cfg.network, 'native_internal_inputs', {})
    if not native:
        return []
    # A first-seen ID on an isolated input road can be attributed to that input.
    # Short-source vehicles skipped at 1 s are still missing; no inferred demand truth.
    network = ET.parse(ROOT/load(ROOT/native['source_path'])['network']['path']).getroot()
    incoming, input_sources = defaultdict(list), defaultdict(list)
    for node in network.findall('./links/link'):
        target = node.find('toLinkEndPt')
        if target is not None:
            incoming[target.get('lane').split()[0]].append(node.get('no'))
    for node in network.findall('./vehicleInputs/vehicleInput'):
        input_sources[node.get('link')].append(node.get('no'))
    rows = []
    for no, spec in native['inputs'].items():
        source, target = spec['physical_source'], spec['target_storage']
        shared = sorted(link for link, targets in detectors['link_to_origins'].items() if target in targets)
        support = sorted(set(shared) | {source}, key=int)
        exclusive = not incoming[source] and input_sources[source] == [no]
        values = final['native_inputs']['inputs'][no]
        births = physical['first_seen_in_window_by_physical_link'].get(source, 0)
        row = {'input_no': no, 'physical_source': source, 'target_storage': target,
               'target_kind': spec.get('target_kind', spec.get('kind', 'common_approach')),
               'desired_veh': values['desired_veh'], 'model_admitted_generation_veh': values['admitted_veh'],
               'model_unadmitted_demand_veh': values['unadmitted_demand_veh'],
               'source_first_seen_ids_veh': births, 'source_attribution_topology_verified': exclusive,
               'observed_admitted_lower_bound_veh': births if exclusive else None,
               'source_reappearance_events_veh': physical['reappeared_in_window_by_physical_link'].get(source, 0),
               'source_initial_fzp': physical['initial_link_counts'].get(source, {'count_veh': 0}),
               'source_final_fzp': physical['final_link_counts'].get(source, {'count_veh': 0}),
               'source_interval': physical_links.get(source, {}),
               'model_target_initial_veh': initial['storage_occupancy_veh'][target],
               'model_target_final_veh': final['storage_occupancy_veh'][target],
               'target_physical_support_links': support,
               'target_stock_comparison': 'Physical source and model target have different scopes; target may include shared roads, transit, or pre-head partition.',
               'physical_source_incoming_connectors': incoming[source],
               'generation_scope': 'Admitted internal generation is a source term, not an Omega boundary entry.'}
        rows.append(row)
    return rows


def run_audit(args):
    began = time.monotonic()
    run = (ROOT/'evaluation/runs'/args.run).resolve()
    dec = run/('decisions_'+run.name)
    start, end = args.start, args.end
    state_path = Path(args.state).resolve() if args.state else dec/f'state_{start:06d}.json'
    end_path = Path(args.end_state).resolve() if args.end_state else dec/f'state_{end:06d}.json'
    action_path = Path(args.action).resolve() if args.action else dec/f'action_{start:06d}.json'
    csv_path = action_path.with_suffix('.csv')
    previous = Path(args.previous).resolve() if args.previous else max(
        (p for p in dec.glob('action_*.json') if int(p.stem.split('_')[-1]) < start),
        key=lambda p: int(p.stem.split('_')[-1]), default=dec/'action_000001.json')
    config = Path(args.config).resolve()
    manifest_path = run/'area_candidate_source_manifest.json'
    run_provenance_path = run/('run_provenance_'+run.name+'.json')
    required = [state_path, action_path, csv_path, previous, config, manifest_path, run_provenance_path]
    if not args.validation_only:
        required.append(end_path)
    missing = [relative(p) for p in required if not p.is_file()]
    if missing:
        return {'status': 'pending', 'run': args.run, 'missing': missing}
    manifest, tuning = load(manifest_path), load(config)
    paths = set(required) | {Path(__file__), ROOT/'diagnostics/live_beta0_interval_prediction.py',
                              ROOT/'scripts/measure_control_area.py'}
    paths |= {ROOT/p for p in manifest['source_sha256']}
    paths |= set((ROOT/'evaluation/controllers').glob('*.py')) | set((ROOT/'vendor/NumSim-mine/src').rglob('*.py'))
    before = replay_provenance(tuning, *paths)
    live_differences = {p: {'live': value, 'replay': sha(ROOT/p)} for p, value in manifest['source_sha256'].items()
                        if sha(ROOT/p) != value}
    config_matches = any(row['sha256'] == sha(config) for row in manifest.get('outputs', {}).values())
    if (live_differences or not config_matches) and not args.validation_only:
        raise ValueError('Replay source/config differs from executed run manifest; use validation-only for an explicitly historical smoke test.')
    cfg, state, detectors, tuning, raw, mapping, metadata = build_projected(config, state_path, previous, fixture_inputs=False)
    if float(raw['sim_sec']) != start:
        raise ValueError('Initial snapshot timestamp differs from requested interval.')
    if end-start != cfg.simulation.T_c_sec:
        raise ValueError('This CLI requires exactly one configured control interval.')
    action = adapter.control_from_json(action_path, cfg, ControlAction)
    action_json = load(action_path)
    if float(action_json['metadata']['sim_sec']) != start:
        raise ValueError('Recorded action timestamp differs from requested interval.')
    if action_json.get('run_provenance', {}).get('run_id') != raw['run_provenance']['run_id']:
        raise ValueError('Recorded action and initial snapshot belong to different runs.')
    parse_changes = {key: {'json': action_json[key], 'parsed': getattr(action, key)}
                     for key in ('green_times', 'offsets', 'ramp_metering', 'vsl')
                     if action_json[key] != getattr(action, key)}
    if parse_changes and not args.validation_only:
        raise ValueError('Actual action was changed while parsing into the current physical contract.')
    calibration = adapter.deep_update(dict(adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))), tuning.get('calibration_override', {}))
    serialized_command = command_roundtrip(action, cfg, mapping, calibration, tuning, action_json, csv_path)
    if not serialized_command['physical_columns_exact'] and not args.validation_only:
        raise ValueError('The recorded command CSV differs from canonical serialization of its action JSON.')
    forecast = adapter.demand_from_state(raw, cfg, DemandStep, 1, calibration, detectors)
    initial = stock_snapshot(state, cfg)
    untouched = pickle.dumps((state, action, forecast), protocol=5)
    expected = {key: copy.deepcopy(getattr(action, key)) for key in ('green_times', 'offsets', 'ramp_metering', 'vsl')}
    trace, original = [], coupling.freeway_substep
    def observe(*pos, **kw):
        if any(getattr(pos[1], key) != value for key, value in expected.items()):
            raise AssertionError('Held actual command changed before freeway substep.')
        result = original(*pos, **kw)
        trace.append({'elapsed_sec': (len(trace)+1)*cfg.simulation.T_f_sec,
                      'cell_counts_veh': continuity_vehicle_counts(pos[0], cfg),
                      'cell_speed_kph': copy.deepcopy(pos[0].freeway_speed),
                      'cell_density_veh_km_lane': copy.deepcopy(pos[0].freeway_density),
                      'effective_lanes': copy.deepcopy(pos[0].freeway_effective_lanes),
                      'diagnostics': dict(result[1])})
        return result
    with patch.object(coupling, 'freeway_substep', observe):
        endpoint = rollout_endpoint.evaluate_price_point(state, action, forecast, [],
            rollout_endpoint.ObjectiveSpec(cfg, depth_override=1, box_walk=False, score_mode='raw'))
    if pickle.dumps((state, action, forecast), protocol=5) != untouched:
        raise AssertionError('Endpoint mutated the input snapshot, action, or demand.')
    if endpoint.aborted or len(endpoint.states) != 1 or len(trace)*cfg.simulation.T_f_sec != end-start:
        raise AssertionError('Canonical held-action endpoint is incomplete.')
    last = endpoint.states[-1]
    last._control_area_ledger.assert_stocks(area_runtime.model_inventory(last, cfg))
    final, metrics = stock_snapshot(last, cfg), endpoint.control_area
    # Future observations are first loaded only after prediction has finished.
    end_raw = load(end_path) if end_path.is_file() else None
    if end_raw is not None and (float(end_raw['sim_sec']) != end or end_raw['run_provenance'] != raw['run_provenance']):
        raise ValueError('Paused end snapshot has a different timestamp or run provenance.')
    document = load(ROOT/tuning['control_area_objective']['membership_path'])
    membership = physical_membership_from_ledger(document)
    freeway_sets = {k: set(map(str, row['chain_links'])) for k, row in mapping['freeway_model_links'].items()}
    fzps = [Path(args.fzp).resolve()] if args.fzp else list((run/'vissim_eval').glob('*.fzp'))
    if len(fzps) != 1:
        raise ValueError('Expected one FZP; supply --fzp explicitly.')
    try:
        physical, links, series = read_physical_window(fzps[0], membership, terminal_lengths(document), raw, end_raw,
            freeway_sets, start=start, end=end, frame_reader=complete_frames)
    except PendingObservation as error:
        return {'status': 'pending', 'run': args.run, 'reason': str(error)}
    verify_ranges(fzps[0], physical['fzp_source']['selected_ranges'])
    physical['native_vs_com_start'] = physical.pop('native_vs_com_900')
    physical['native_vs_com_end'] = physical.pop('native_vs_com_1050')
    fwkeys = set().union(*freeway_sets.values())
    nfw = sum(physical['final_link_counts'].get(k, {}).get('count_veh', 0) for k in fwkeys)
    measured_final = {'omega_veh': physical['final_inside_veh'], 'freeway_veh': nfw,
                      'urban_and_ramps_veh': physical['final_inside_veh']-nfw}
    fw_ttt = sum(sum(sum(x) for x in row['cell_counts_veh'].values())*cfg.simulation.T_f_h for row in trace)
    observed_fw_ttt = sum(links[k]['residence_veh_h'] for k in fwkeys if k in links)
    residence = {'omega': {'model_veh_h': metrics['ttt_veh_h'], 'physical_veh_h': physical['totals']['ttt_trapezoid_veh_h']},
                 'freeway': {'model_veh_h': fw_ttt, 'physical_veh_h': observed_fw_ttt},
                 'urban_and_ramps': {'model_veh_h': metrics['ttt_veh_h']-fw_ttt,
                                     'physical_veh_h': physical['totals']['ttt_trapezoid_veh_h']-observed_fw_ttt}}
    for values in residence.values():
        values['error_veh_h'] = values['model_veh_h']-values['physical_veh_h']
    generation = {key: value for key, value in metrics['flow_counts'].items()
                  if key.startswith('input:') and cfg.network.control_area_routes[key]['target_inside'] is True}
    closure = final['omega_veh']-initial['omega_veh']-metrics['entered_veh']+metrics['ttd_veh']-sum(generation.values())
    if abs(closure) > 1e-7:
        raise AssertionError('Model boundary entries + inside generation - exits do not close stock.')
    sources = source_comparison(cfg, initial, final, physical, links, detectors)
    actuation = audit_actuation(run, csv_path, start, end)
    after = {key: sha(ROOT/key) for key in before}
    changes = {key: {'before': value, 'after': after[key]} for key, value in before.items() if after[key] != value}
    if changes:
        raise ValueError('Source/input bytes changed during the audit: '+str(changes))
    com_final = raw_stock(end_raw, membership, freeway_sets) if end_raw else None
    cells = compare_freeway_cells(initial, final, raw, end_raw, mapping, trace)
    if cells['available'] and abs(cells['summary']['count_bias_sum_veh']-(final['freeway_veh']-com_final['freeway_veh'])) > 1e-7:
        raise AssertionError('Cell count errors do not close the aggregate freeway error.')
    return {'schema': 'live-prediction-interval/v1', 'status': 'validation_only' if args.validation_only else 'complete',
            'run': args.run, 'interval_sec': [start, end],
            'method': 'Installed canonical runtime, actual recorded action held for one interval, no optimizer search; future observations loaded after prediction.',
            'replay_matches_executed_model': not live_differences and config_matches,
            'executed_command_audit_valid': actuation['valid'], 'actuation': actuation,
            'action_parse_changes': parse_changes, 'command_roundtrip': serialized_command,
            'source_sha256_start': before, 'source_changes_during_audit': changes,
            'source_differences_from_run_manifest': live_differences, 'config_hash_matches_manifest': config_matches,
            'inputs': {'state': relative(state_path), 'action': relative(action_path), 'command_csv': relative(csv_path),
                       'previous': relative(previous), 'config': relative(config), 'end_state': relative(end_path) if end_raw else None},
            'model': {'initial': initial, 'final': final, 'metrics': metrics, 'forecast': [vars(x) for x in forecast],
                      'generated_inside_by_input_veh': generation, 'omega_flux_residual_veh': closure,
                      'input_snapshot_action_forecast_unchanged': True, 'freeway_substep_trace': trace,
                      'native_prehead_state': copy.deepcopy(getattr(last, 'native_input_prehead_state', {})),
                      'runtime_metadata': metadata},
            'physical': physical, 'physical_link_measurement': links, 'physical_timeseries': series,
            'comparison': {'initial_com': raw_stock(raw, membership, freeway_sets),
                           'ramp_initial_com_veh': raw['ramp_counts'],
                           'ramp_final_com_veh': end_raw['ramp_counts'] if end_raw else None,
                           'final_fzp': measured_final, 'final_com': com_final,
                           'final_stock_error_vs_fzp': component_errors(final, measured_final),
                           'final_stock_error_vs_com': component_errors(final, com_final) if com_final else None,
                           'residence': residence,
                           'residence_error_cancellation_veh_h': max(0., abs(residence['freeway']['error_veh_h'])+abs(residence['urban_and_ramps']['error_veh_h'])-abs(residence['omega']['error_veh_h'])),
                           'td_model_minus_observed_and_terminal_veh': metrics['ttd_veh']-physical['ttd_observed_plus_terminal_veh']},
            'internal_sources': sources,
            'freeway_cell_comparison': cells,
            'limitations': physical['limitations']+[
                'Physical first-seen IDs on isolated input roads give an admitted-input lower bound under complete recording/unique IDs; 1 s skipped source roads remain unattributed.',
                'Appeared-inside is a sampled stock-balance term, not verified internal generation. Unresolved disappearances receive no exit credit.',
                'Unadmitted desired model demand is outside model stock and TTT. Shared approach occupancy is not the count of its input source road.',
                'Source-generation and SC15 changes are jointly active; this single replay measures final-model error, not a causal ablation of either change.',
                'Validation-only permits historical source mismatch and native uncontrolled signal clocks. It does not verify executed-model prediction accuracy.'],
            'wall_sec': time.monotonic()-began}


def write_report(report, prefix):
    prefix = Path(prefix)
    paths = [prefix.with_suffix('.json'), prefix.with_suffix('.md'), prefix.with_name(prefix.name+'_sources.csv'),
             prefix.with_name(prefix.name+'_cells.csv'), prefix.with_name(prefix.name+'_cell_trace.csv')]
    if any(p.exists() for p in paths):
        raise FileExistsError('Refusing to overwrite an existing audit artifact.')
    prefix.parent.mkdir(parents=True, exist_ok=True)
    paths[0].write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    comp = report['comparison']
    lines = [f"{report['run']}: {report['interval_sec'][0]}–{report['interval_sec'][1]} s ({report['status']}).", '',
             f"Source/config match executed manifest: {report['replay_matches_executed_model']}. Actual signal/meter/VSL audit valid: {report['executed_command_audit_valid']}.",
             '', '| Residence | Model veh·h | Physical veh·h | Error veh·h |', '|---|---:|---:|---:|']
    for key, row in comp['residence'].items():
        lines.append(f"| {key} | {row['model_veh_h']:.6f} | {row['physical_veh_h']:.6f} | {row['error_veh_h']:+.6f} |")
    lines += ['', f"Residence error cancellation: {comp['residence_error_cancellation_veh_h']:.6f} veh·h.", '',
              '| End stock | Model veh | FZP veh | COM veh |', '|---|---:|---:|---:|']
    for key in ('omega_veh', 'freeway_veh', 'urban_and_ramps_veh'):
        com = comp['final_com'][key] if comp['final_com'] else 'unavailable'
        lines.append(f"| {key} | {report['model']['final'][key]:.6f} | {comp['final_fzp'][key]} | {com} |")
    p, m = report['physical']['totals'], report['model']['metrics']
    lines += ['', f"TD: model {m['ttd_veh']:.6f}; physical {p.get('observed_exit_veh', 0)} observed + {p.get('terminal_inferred_exit_veh', 0)} terminal inferred. Interior disappearance unresolved: {p.get('unresolved_inside_disappearance_veh', 0)} vehicles.",
              f"Model inside generation: {sum(report['model']['generated_inside_by_input_veh'].values()):.6f} vehicles. Source closure residual: {report['model']['omega_flux_residual_veh']:.3g} vehicles.",
              '', '| Native input | Source | Model desired | Model admitted | Model unadmitted | Observed source births lower bound | Source final / stopped <5 |', '|---|---|---:|---:|---:|---:|---:|']
    for row in report['internal_sources']:
        q = row['source_final_fzp']
        lines.append(f"| {row['input_no']} | {row['physical_source']} | {row['desired_veh']:.3f} | {row['model_admitted_generation_veh']:.3f} | {row['model_unadmitted_demand_veh']:.3f} | {row['observed_admitted_lower_bound_veh']} | {q['count_veh']} / {q.get('stopped_lt5_veh', 0)} |")
    cells = report['freeway_cell_comparison']
    if cells['available']:
        summary = cells['summary']
        lines += ['', f"All {summary['cells']} freeway cells: nonempty-cell speed MAE {summary['speed_mae_kph']:.3f} km/h; speed bias {summary['speed_bias_kph']:+.3f} km/h; summed stock error {summary['count_bias_sum_veh']:+.3f} vehicles.", '',
                  '| Cell (zero based) | Initial observed speed | Predicted final speed | Observed final speed | Speed error | Predicted / observed final N | Predicted / observed evolution |',
                  '|---|---:|---:|---:|---:|---:|---|']
        for row in cells['rows']:
            if row['link'] == 'FW_E' and row['cell_index_zero_based'] in (8, 9):
                fmt = lambda value: 'unavailable' if value is None else f'{value:.3f}'
                lines.append(f"| E{row['cell_index_zero_based']} | {fmt(row['initial_observed_speed_kph'])} | {fmt(row['predicted_speed_kph'])} | {fmt(row['observed_speed_kph'])} | {fmt(row['speed_error_kph'])} | {row['predicted_count_veh']:.3f} / {row['observed_count_veh']:.0f} | {row['predicted_endpoint_evolution']} / {row['observed_endpoint_evolution']} |")
        lines += ['', cells['method'], cells['timing_limit']]
    lines += ['', 'The JSON retains source/config/action SHA256, bounded FZP range SHA256, each input’s finite target occupancy and physical support, component errors, actuation evidence, and per-step actual model flows.', '']
    lines.extend(report['limitations'])
    paths[1].write_text('\n'.join(lines)+'\n', encoding='utf-8')
    with paths[2].open('w', encoding='utf-8', newline='') as stream:
        rows = [{key: json.dumps(value) if isinstance(value, (dict, list)) else value for key, value in row.items()} for row in report['internal_sources']]
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else ['input_no'])
        writer.writeheader(); writer.writerows(rows)
    cell_rows = [{key: json.dumps(value) if isinstance(value, (dict, list)) else value for key, value in row.items()}
                 for row in cells['rows']]
    initial = report['model']['initial']
    initial_trace = {'elapsed_sec': 0, 'cell_counts_veh': initial['freeway_cells_veh'],
                     'cell_speed_kph': initial['freeway_speed_kph'], 'cell_density_veh_km_lane': initial['freeway_density_veh_km_lane'],
                     'effective_lanes': initial['freeway_effective_lanes']}
    trace_rows = []
    for step in [initial_trace]+report['model']['freeway_substep_trace']:
        for link, counts in step['cell_counts_veh'].items():
            for cell, count in enumerate(counts):
                trace_rows.append({'sim_sec': report['interval_sec'][0]+step['elapsed_sec'], 'elapsed_sec': step['elapsed_sec'],
                                   'link': link, 'cell_index_zero_based': cell, 'count_veh': count,
                                   'speed_kph': step['cell_speed_kph'][link][cell],
                                   'density_veh_km_lane': step['cell_density_veh_km_lane'][link][cell],
                                   'effective_lanes': step['effective_lanes'][link][cell]})
    for path, rows in ((paths[3], cell_rows), (paths[4], trace_rows)):
        with path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else ['link', 'cell_index_zero_based'])
            writer.writeheader(); writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, help='Run directory name under evaluation/runs.')
    parser.add_argument('--config', required=True)
    parser.add_argument('--output-prefix', required=True)
    parser.add_argument('--start', type=int, default=900)
    parser.add_argument('--end', type=int, default=1050)
    for name in ('state', 'end-state', 'action', 'previous', 'fzp'):
        parser.add_argument('--'+name)
    parser.add_argument('--validation-only', action='store_true', help='Explicit historical/NC smoke test; allows source mismatch and absent paused end snapshot.')
    args = parser.parse_args()
    if args.end <= args.start:
        parser.error('end must be later than start')
    report = run_audit(args)
    if report['status'] == 'pending':
        print(json.dumps(report, ensure_ascii=False)); return 2
    write_report(report, args.output_prefix)
    print(json.dumps({key: report[key] for key in ('status', 'replay_matches_executed_model', 'executed_command_audit_valid', 'wall_sec')}))
    return 0 if args.validation_only or report['executed_command_audit_valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
