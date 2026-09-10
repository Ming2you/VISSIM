"""Read-only first controlled window: collector exposure versus actual SG events."""
import argparse
from bisect import bisect_right
from collections import defaultdict
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from diagnostics.audit_observer_control_pair import native_signal_prefix
from diagnostics.compare_preflight_live_action import stable, load
from evaluation.controllers.signal_head_observation import serialized_head_position, validate_provenance
from plant.src.vissim_strict.signal_program import parse_sig


def controlled_exposure(rows, group, start, end):
    slots = defaultdict(list)
    for row in rows:
        if (row['sc_no'], row['sg_no']) != group:
            continue
        sec = float(row['sim_sec'])
        if not math.isfinite(sec):
            raise ValueError('Nonfinite trace timestamp')
        stage = row['stage']
        if ((stage == 'immediate' and start <= sec < end)
                or (stage == 'post_step' and start < sec <= end)):
            slots[stage, sec].append(row)
    green = 0
    for stage, times in [('immediate', range(start, end)), ('post_step', range(start+1, end+1))]:
        if {sec for kind, sec in slots if kind == stage} != set(times):
            raise ValueError('Missing/noninteger actual signal frame: ' + repr((group, stage)))
        for sec in times:
            values = slots[stage, sec]
            if len(values) != 1:
                raise ValueError('Duplicated urban signal frame')
            row = values[0]
            state = row['readback_state'].upper()
            if row['ok'] != '1' or state not in {'GREEN', 'RED', 'AMBER', 'REDAMBER', 'OFF'} or state != row['requested_state'].upper():
                raise ValueError('Invalid or failed actual readback')
            if stage == 'immediate':
                green += state == 'GREEN'
    return green, {'immediate_rows': end-start, 'post_step_rows': end-start,
                   'start_immediate': slots['immediate', start][0],
                   'end_post_step': slots['post_step', end][0]}


def audit(run_name, start, end):
    evidence = []
    run = ROOT / 'evaluation/runs' / run_name
    decision = run / ('decisions_' + run_name)
    manifest = load(run / ('run_provenance_' + run_name + '.json'), evidence)
    raw = load(decision / f'state_{end:06d}.json', evidence)
    window = raw['local_observation']['signal_observation_window']
    context = validate_provenance(raw, window, manifest['signal_observation']['options'])
    if ([window['start_sec'], window['end_sec']] != [start, end] or window['transition_count'] != end-start
            or window['cadence_sec'] != 1 or window['clock_complete'] is not True):
        raise ValueError('Collector window/cadence is invalid')
    blob, trace_evidence = stable(decision / 'signal_readback.csv')
    evidence.append(trace_evidence)
    rows = list(csv.DictReader(io.StringIO(blob.decode('utf-8-sig'))))
    network_blob, network_evidence = stable(manifest['files']['network']['path'])
    evidence.append(network_evidence)
    if network_evidence['sha256'] != manifest['files']['network']['sha256']:
        raise ValueError('Pinned network changed')
    network_tree = ET.fromstring(network_blob)
    geometry = {node.get('no'): node for node in network_tree.findall('./signalHeads/signalHead')}
    native_controllers = {node.get('no'): node for node in network_tree.findall('./signalControllers/signalController')}
    native = native_signal_prefix(next(run.glob('vissim_eval/*.lsa')), end)
    cache = {}
    result_rows = []
    for head in window['heads']:
        node = geometry[head['head_id']]
        if (node.get('lane') != f"{head['link']} {head['lane']}" or node.get('sg') != f"{head['sc']} {head['sg']}"
                or serialized_head_position(float(node.get('pos'))) != head['position_m']):
            raise ValueError('Physical head identity mismatch')
        group = str(head['sc']), str(head['sg'])
        owner = 'controlled' if head['controlled_sec'] == end-start else 'native'
        if (head['unverified_sec'] != 0 or head[owner+'_sec'] != end-start
                or head[('native' if owner == 'controlled' else 'controlled')+'_sec'] != 0):
            raise ValueError('This focused audit requires full-window verified single ownership')
        if group not in cache:
            if owner == 'controlled':
                expected, proof = controlled_exposure(rows, group, start, end)
                cache[group] = {'owner': owner, 'expected_green_sec': expected, 'trace': proof}
            else:
                events = native['groups'].get(':'.join(group), [])
                times = [row[0] for row in events]
                if times and bisect_right(times, start) > 0:
                    expected = sum(events[bisect_right(times, sec)-1][1] == 'GREEN' for sec in range(start, end))
                    basis = 'actual native LSA state changes, left-step hold'
                    actual_event_coverage = True
                else:
                    controller = native_controllers[group[0]]
                    sig = Path(manifest['files']['network']['path']).parent / controller.get('supplyFile2').removeprefix('#data#')
                    _, sig_evidence = stable(sig)
                    pins = [p for p in manifest['signal_programs'] if Path(p['path']).resolve() == sig.resolve()]
                    if len(pins) != 1 or pins[0]['sha256'] != sig_evidence['sha256']:
                        raise ValueError('Native fallback program not pinned to actual run')
                    evidence.append(sig_evidence)
                    program = parse_sig(sig, int(controller.get('progNo')))
                    expected = sum(program.state_at(sec, group[1], controller_offset_sec=float(controller.get('offset'))) == 'GREEN' for sec in range(start, end))
                    basis = 'pinned native program only; no actual LSA event establishes initial state'
                    actual_event_coverage = False
                cache[group] = {'owner': owner, 'expected_green_sec': expected, 'basis': basis,
                                'independent_actual_event_coverage': actual_event_coverage}
        if cache[group]['owner'] != owner:
            raise ValueError('Heads in one SG disagree on ownership')
        result_rows.append({'head_id': head['head_id'], 'sc': group[0], 'sg': group[1], 'link': head['link'],
            'lane': head['lane'], 'owner': owner, 'collector_green_sec': head['green_sec'],
            'expected_green_sec': cache[group]['expected_green_sec'],
            'difference_sec': head['green_sec']-cache[group]['expected_green_sec']})
    changes = [row['path'] for row in evidence if hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() != row['sha256']]
    if changes:
        raise ValueError('Immutable evidence changed')
    return {'schema': 'controlled-head-window-audit/v1', 'run': run_name, 'run_id': manifest['run_id'],
        'window': [start, end], 'context_sha256': context, 'heads': len(result_rows),
        'controlled_heads': sum(r['owner'] == 'controlled' for r in result_rows),
        'native_heads': sum(r['owner'] == 'native' for r in result_rows),
        'controlled_groups': sum(r['owner'] == 'controlled' for r in cache.values()),
        'native_groups': sum(r['owner'] == 'native' for r in cache.values()),
        'native_groups_without_independent_actual_event': [':'.join(k) for k, r in cache.items()
            if r['owner'] == 'native' and not r['independent_actual_event_coverage']],
        'groups': {':'.join(key): value for key, value in cache.items()},
        'per_head': result_rows, 'mismatches': [r for r in result_rows if r['difference_sec'] != 0],
        'valid': all(r['difference_sec'] == 0 for r in result_rows), 'input_changes': changes,
        'source_files': evidence, 'native_lsa': {k: v for k, v in native.items() if k != 'groups'},
        'producer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'scope': 'Controlled heads use every actual immediate [start,end) row, validated by every actual post_step (start,end] row. Unwritten native heads use actual LSA where it establishes an initial state; absent-event groups are explicitly program-only, not independently observed. Post-step at the command boundary is not incorrectly applied to the next held interval. No model or VISSIM execution.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    parser.add_argument('--start', type=int, default=900)
    parser.add_argument('--end', type=int, default=1050)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT/'diagnostics') or output.exists():
        raise ValueError('New diagnostic output path required')
    result = audit(args.run, args.start, args.end)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('valid', 'heads', 'controlled_groups', 'native_groups', 'input_changes')}))


if __name__ == '__main__':
    main()
