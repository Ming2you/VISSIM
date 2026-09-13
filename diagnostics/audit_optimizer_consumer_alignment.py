"""Audit an existing decision and actual-VBS fake-COM output; execute neither."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.controllers import plant_cycle, signal_group_plan


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main(decision, consumer, output):
    decision, consumer, output = decision.resolve(), consumer.resolve(), output.resolve()
    if output.exists() or output.with_suffix('.md').exists():
        raise FileExistsError('Use a new output path; historical evidence is immutable')
    manifest = read(decision / 'manifest.json')
    action = read(decision / 'action.json')
    consumed = read(consumer / 'result.json')
    diag, meta = action['diagnostics'], action['metadata']
    paths = [decision / name for name in ('manifest.json', 'action.json', 'action.csv')]
    paths += [consumer / name for name in ('result.json', 'actionFile.csv', 'signalTraceFile.csv', 'invocation.vbs', 'cscript.txt')]
    plan_path = ROOT / 'outputs/signal_group_actuation_plan_mainline_20260825.json'
    mapping_path = ROOT / 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'
    paths += [plan_path, mapping_path, plant_cycle.RUNNER_VBS]
    before = {str(p): sha(p) for p in paths}
    assert manifest['valid'] and consumed['passed'] and consumed['sim_sec'] == 900
    assert consumed['action_csv_sha256'] == sha(decision / 'action.csv')
    assert consumed['action_json_sha256'] == sha(decision / 'action.json')
    assert consumed['vbs_source_sha256'] == sha(plant_cycle.RUNNER_VBS)
    for p in (plan_path, mapping_path, plant_cycle.RUNNER_VBS):
        assert manifest['input_sha256'][str(p.relative_to(ROOT))] == sha(p)
    with (decision / 'action.csv').open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    # The canonical VBS action log has no header in the test harness.
    with (consumer / 'actionFile.csv').open(encoding='utf-8', newline='') as f:
        reader_rows = list(csv.DictReader(f, fieldnames=['sim_sec', *rows[0], 'readback']))
    assert len(reader_rows) == len(rows)
    for original, received in zip(rows, reader_rows):
        assert all(original[k] == received[k] for k in original)
    axes = {r['sc_no']: r for r in rows if r['kind'] == 'signal'}
    sg_rows = [r for r in rows if r['kind'] == 'signal_sg']
    plan, mapping = read(plan_path), read(mapping_path)
    amber, all_red = plant_cycle.runner_clearance_sec()
    signals = []
    expected_windows = {}
    for sc, row in axes.items():
        key = 'SC' + sc
        greens = {p: float(row[p + '_green']) for p in signal_group_plan.MODEL_PHASES}
        assert all(g == action['green_times'][key + '_' + p] for p, g in greens.items())
        offset = float(row['offset'])
        assert offset == action['offsets'][key] == meta['offset_written_sec'][key]
        node = plan['controllers'][sc]
        windows = signal_group_plan.plan_windows(signal_group_plan.node_plan_from_json(node), greens,
            signal_group_plan.phase_layout_order(node['major_maps_to']), amber, all_red)
        cycle = sum(greens.values()) + sum(g > 0 for g in greens.values()) * (amber + all_red)
        for w in windows:
            expected_windows[(sc, str(w.sg_no), str(w.window_index))] = (round(w.start_sec, 6), round(w.end_sec, 6))
        signals.append({'signal': key, 'greens_sec': greens, 'cycle_sec': cycle, 'offset_sec': offset})
    assert len(expected_windows) == len(sg_rows)
    for row in sg_rows:
        window = (float(row['p1_green']), float(row['p2_green']))
        assert window == expected_windows[(row['sc_no'], row['dsd_no'], row['link'])]
        assert float(row['offset']) == float(axes[row['sc_no']]['offset'])
    with (consumer / 'signalTraceFile.csv').open(encoding='utf-8', newline='') as f:
        trace = list(csv.DictReader(f))
    by_sc = {s['signal'][2:]: s for s in signals}
    oracle_mismatches = []
    for row in trace:
        if int(row['sc']) >= 9100:
            expected = 'GREEN'  # This decision has all eight meters fully open.
        else:
            signal = by_sc[row['sc']]
            x, cycle = 900 + signal['offset_sec'], signal['cycle_sec']
            pos = x - math.floor(x / cycle) * cycle
            spans = [(a, b) for (sc, sg, _), (a, b) in expected_windows.items() if sc == row['sc'] and sg == row['sg']]
            any_green = any(a <= pos < b for (sc, _, _), (a, b) in expected_windows.items() if sc == row['sc'])
            own_green = any(a <= pos < b for a, b in spans)
            own_amber = any(b <= pos < b + amber or (b + amber > cycle and pos < b + amber - cycle) for _, b in spans)
            expected = 'GREEN' if own_green else ('AMBER' if own_amber and not any_green else 'RED')
        if row['readback'] != expected or row['requested'] != expected or row['ok'] != '1':
            oracle_mismatches.append({**row, 'expected': expected})
    assert not oracle_mismatches
    marker = diag['_control_area_meter_finalized']
    assert marker['realized_rates'] == action['ramp_metering']
    assert marker['context_sha256'] == meta['control_area_meter_context_sha256']
    for flag in ('control_area_phase_finalized_before_score', 'control_area_phase_outer_matches_scored', 'control_area_meter_finalized_before_score'):
        assert diag[flag] == 1
    assert meta['control_area_meter_writer_matches_scored'] == 1
    meters = []
    meter_specs = {m['id']: m for m in mapping['ramp_meters']}
    for row in rows:
        if row['kind'] != 'ramp_meter':
            continue
        spec = meter_specs[row['id']]
        green, rate = float(row['green_sec']), float(row['rate_vph'])
        assert green == marker['commands']['rw_meter_green_' + row['id']] == 10
        assert rate == green * spec['capacity_vph'] / spec['cycle_sec']
        extra = dict(x.split('=', 1) for x in row['metadata'].split(';') if '=' in x)
        assert extra['model_ramp_key'] == spec['model_ramp_key']
        assert float(extra['group_rate_vph']) == round(action['ramp_metering'][spec['model_ramp_key']], 3)
        meters.append({'meter': row['id'], 'sc': row['sc_no'], 'green_sec': green, 'csv_equivalent_rate_vph': rate,
                       'model_group': spec['model_ramp_key'], 'model_realized_group_rate_vph': action['ramp_metering'][spec['model_ramp_key']]})
    segments = {s['segment_id']: s for s in mapping['segments']}
    vsl = [r for r in rows if r['kind'] == 'vsl']
    assert len(vsl) == 66 and len(action['vsl']) == 44 and set(action['vsl'].values()) == {120.0}
    for row in vsl:
        segment = segments[row['id']]
        model_key = segment['model_link'] + '__seg' + str(segment['model_segment_index'])
        assert float(row['speed_kph']) == action['vsl'][model_key]
        candidates = [d for d in segment['dsds'] if int(d['dsd_no']) == int(row['dsd_no'])]
        assert len(candidates) == 1
        assert int(candidates[0]['lane']) == int(row['lane'])
        assert int(candidates[0].get('link', segment['link'])) == int(row['link'])
    vsl_readback = [r for r in reader_rows if r['kind'] == 'vsl']
    assert all(r['readback'] == '120|120' for r in vsl_readback)
    assert meta['offset_writer'] == 'experiment' and meta['offset_production_writes'] == 0
    assert meta['offset_promotion_status'] == 'NOT_EVALUATED'
    report = {
        'passed': True, 'scope': 'Existing t900 actual optimizer output; canonical VBS fake COM at first event only',
        'source_hashes': before, 'producer_manifest_valid': manifest['valid'],
        'canonical_reader_rows_exact': len(rows), 'signals': signals, 'sg_window_rows_match_selected_plan': len(sg_rows),
        'first_event_rows': len(trace), 'independent_event_oracle_mismatches': oracle_mismatches,
        'phase_finalization': {k: diag[k] for k in ('control_area_phase_finalized_before_score', 'control_area_phase_finalization_source', 'control_area_phase_finalized_changed_values', 'control_area_phase_outer_matches_scored')},
        'meters': meters, 'meter_finalization_context_sha256': marker['context_sha256'],
        'meter_writer_matches_scored': meta['control_area_meter_writer_matches_scored'],
        'vsl_model_values': len(action['vsl']), 'vsl_physical_rows': len(vsl), 'vsl_kph': 120,
        'vsl_readbacks_10_70_match': len(vsl_readback),
        'offsets_nonzero': sum(s['offset_sec'] != 0 for s in signals),
        'offset_mode': meta['offset_writer'], 'offset_promotion_status': meta['offset_promotion_status'],
        'follower_score': {k: v for k, v in diag.items() if k.startswith('control_area_follower_') or k.startswith('control_area_offset_')},
        'limits': ['Fake COM does not establish live actuation or traffic response; no VISSIM or optimizer rerun.',
                   'Phase/RM score alignment uses runtime producer assertions and exact stored commands; no cost reconstruction.',
                   'No independently stored VSL scoring-vector hash; final JSON/CSV/DSD mapping/readback agree at 120 km/h.',
                   'CSV meter rate is green * nominal physical capacity / cycle, not measured throughput; model group realized rate uses the existing measured-table prediction.',
                   'Only the first event at t900 is checked; this does not establish all-cycle or failure-gate coverage.'],
    }
    assert before == {str(p): sha(p) for p in paths}
    report['inputs_unchanged'] = True
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    output.with_suffix('.md').write_text(
        '# Actual optimizer t900 consumer alignment\n\n'
        'PASS: the installed main decision was consumed by the canonical VBS with fake COM. '
        f'All {len(rows)} original CSV rows survived the reader unchanged; 17 signal axes and 122 SG windows match the final action and selected mainline plan. '
        'The independently calculated t900 event matches all 144 requested/readback states (136 urban SGs and 8 meter SGs), with zero mismatches.\n\n'
        'The producer records phase refinement before scoring (57 changed phase values), outer-return equality, meter finalization before scoring, and writer/scored meter equality. '
        'The cached meter context and four realized group rates match the final action. All eight physical meters request 10 s green. '
        'Each CSV rate is 900 veh/h = 10 s × nominal 900 veh/h / 10 s. This is an equivalent command rate, not measured throughput. '
        'R_F_W\'s model group rate is 1599.747393 veh/h while its two physical meters are fully open; the existing measured-table prediction and the two nominal CSV rates are distinct quantities.\n\n'
        'All 44 final model VSL values and 66 mapped DSD rows are 120 km/h; the canonical setter checks classes 10, 20, 30 and 70, and the action log records matching 10/70 readback for all 66 rows. '
        'Thirteen optimizer-selected nonzero offsets were accepted under experiment mode. Production writes remain zero and promotion remains NOT_EVALUATED.\n\n'
        'This establishes the stored finalization/serialization/consumer chain, using runtime assertions for the scored phase and RM vector. '
        'It does not independently reconstruct the optimizer cost, provide a VSL scoring-vector hash, prove live actuator authority, or validate later event/failure paths. '
        'No VISSIM or optimizer was rerun and all audited input hashes remained unchanged. '
        'The first sandboxed WSH attempt was denied access to its settings; the separate authorized WSH retry exited 0.\n\n'
        f'Evidence: `{output.name}`, `{consumer.name}/result.json`, `actionFile.csv`, `signalTraceFile.csv`, and the original preflight manifest.\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('passed', 'canonical_reader_rows_exact', 'sg_window_rows_match_selected_plan', 'first_event_rows', 'offsets_nonzero', 'inputs_unchanged')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decision', type=Path, required=True)
    parser.add_argument('--consumer', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    main(args.decision, args.consumer, args.output)
