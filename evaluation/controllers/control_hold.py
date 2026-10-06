"""Explicit scheduled VSL and a failed-decision receipt; no traffic prediction.

The runner invokes the hold path only before any candidate has reached COM.
It never substitutes observations, prices, objective values, or future controls.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import json
import math
import re
from pathlib import Path

from evaluation.controllers.action_csv_schema import ACTION_CSV_FIELDS


def validate_fixed_vsl(policy, heads):
    required = {'start_sec', 'base_kmh', 'zone_kmh'}
    if not isinstance(policy, dict) or not required <= set(policy) or set(policy) - required - {'end_sec'}:
        raise ValueError('Fixed VSL requires start_sec, base_kmh, zone_kmh and optional end_sec')
    if (type(policy['start_sec']) not in (int, float) or not math.isfinite(policy['start_sec'])
            or policy['start_sec'] < 0 or policy['start_sec'] % 150):
        raise ValueError('Fixed VSL starts on a 150-second decision boundary')
    if 'end_sec' in policy:
        end = policy['end_sec']
        if (type(end) not in (int, float) or not math.isfinite(end)
                or end <= policy['start_sec'] or end % 150):
            raise ValueError('Fixed VSL ends after its start on a 150-second decision boundary')
    allowed = set(range(50, 111, 10))
    if policy['base_kmh'] not in allowed or not isinstance(policy['zone_kmh'], dict):
        raise ValueError('Invalid fixed VSL speed')
    keys = {f'{owner}__seg{head}' for owner, values in heads.items() for head in values[1:-1]}
    if not set(policy['zone_kmh']) <= keys or any(v not in allowed for v in policy['zone_kmh'].values()):
        raise ValueError('Fixed VSL must address installed interior zones')


def fixed_vsl_values(previous, policy, heads, sim_sec):
    validate_fixed_vsl(policy, heads)
    result = dict(previous)
    for owner, zones in heads.items():
        keys = [k for k in result if k.startswith(owner + '__seg')]
        if not keys:
            raise ValueError('Missing expanded VSL addresses: ' + owner)
        for key in keys:
            cell = int(key.split('__seg')[1])
            head = max(h for h in zones if h <= cell)
            speed = policy['base_kmh']
            if policy['start_sec'] <= sim_sec < policy.get('end_sec', math.inf):
                speed = policy['zone_kmh'].get(f'{owner}__seg{head}', speed)
            result[key] = float(speed)
        result[owner] = min(result[k] for k in keys)
    return result


def fixed_vsl_reference(reference, policy, heads, start_sec, interval_sec, blocks):
    """Apply the same schedule to execution block zero and prediction-only blocks."""
    from evaluation.controllers import sdmpc_sequence as sequence
    controls = sequence.actions(reference, blocks)
    for k, control in enumerate(controls):
        control.vsl = fixed_vsl_values(control.vsl, policy, heads, start_sec+k*interval_sec)
    if all(c.vsl == controls[0].vsl for c in controls[1:]):
        # Keep the historic constant-policy representation when no boundary is crossed.
        return controls[0]
    return sequence.pack(controls)


def write_hold(args, tuning):
    """Copy only the preceding applied physical command, with a new hold receipt.

    Runner ownership of previous-action-json is essential: it advances this
    pointer only after successful native application. Never read failed output.
    """
    if tuning.get('runtime', {}).get('decision_error_policy') != 'hold_previous':
        raise ValueError('Holding a failed decision is not enabled in tuning')
    state = json.loads(Path(args.state_json).read_text(encoding='utf-8-sig'))
    previous_path = Path(args.previous_action_json)
    previous_csv = previous_path.with_suffix('.csv')
    raw = json.loads(previous_path.read_text(encoding='utf-8-sig'))
    t = float(state['sim_sec'])
    prior = 1. if t == 150 else t - float(state['control_interval_sec'])
    run_id = state['run_provenance']['run_id']
    if (not run_id or raw['run_provenance']['run_id'] != run_id
            or raw['metadata']['run_provenance']['run_id'] != run_id
            or raw['metadata']['sim_sec'] != prior):
        raise ValueError('Hold requires this run\'s immediately preceding applied command')
    with previous_csv.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(ACTION_CSV_FIELDS):
            raise ValueError('Previous CSV schema differs')
        rows = list(reader)
    if not rows or any(None in row or None in row.values() for row in rows):
        raise ValueError('Previous CSV is incomplete')
    result = copy.deepcopy(raw)
    result.pop('prediction', None)
    result.pop('prediction_error', None)
    result.pop('projection_diagnostics', None)
    result['diagnostics']['hold_previous_source_sim_sec'] = prior
    result['diagnostics'].pop('sdmpc_prediction_sequence', None)
    result['metadata'] = dict(sim_sec=t, controller_status='hold_previous_error',
        run_provenance=copy.deepcopy(raw['metadata']['run_provenance']),
        prediction_status='not_computed', controller_error='See original decision failure log',
        hold_previous=dict(source=str(previous_path.resolve()),
            json_sha256=hashlib.sha256(previous_path.read_bytes()).hexdigest(),
            csv_sha256=hashlib.sha256(previous_csv.read_bytes()).hexdigest(),
            source_sim_sec=prior, native_application_pending=True))
    policy = tuning.get('adapter', {}).get('sdmpc_fixed_vsl')
    if policy is not None:
        expanded = dict(raw['vsl'])
        count = tuning['config_overrides']['network']['freeway_segments_per_link']
        for owner in tuning['freeway']['vsl_zone_heads']:
            for cell in range(count):
                expanded.setdefault(f'{owner}__seg{cell}', raw['vsl'][owner])
        result['vsl'] = fixed_vsl_values(expanded, policy, tuning['freeway']['vsl_zone_heads'], t)
    for row in rows:
        if row['kind'] == 'vsl':
            match = re.fullmatch(r'RW_(FW_[EW])_S(\d+)', row['id'])
            if match is None:
                raise ValueError('Unknown VSL row in applied command')
            key = f'{match[1]}__seg{match[2]}'
            if float(row['speed_kph']) != float(raw['vsl'].get(key, raw['vsl'][match[1]])):
                raise ValueError('Previous VSL JSON/CSV mismatch')
            row['speed_kph'] = str(result['vsl'].get(key, result['vsl'][match[1]]))
        row['metadata'] += ';hold_previous_error=1'
    # Preserve partially produced optimizer artifacts, including pending prices.
    for path in (Path(args.out_action_json), Path(args.out_action_csv),
                 Path(args.out_action_json + '.sdmpc_pending')):
        if path.exists():
            path.rename(path.with_name(path.name + '.failed_decision'))
    Path(args.out_action_json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    with Path(args.out_action_csv).open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=ACTION_CSV_FIELDS)
        writer.writeheader(); writer.writerows(rows)
    print('HOLD_NATIVE_SIGNALS=' + str(int(not any(r['kind'] == 'signal' for r in rows))))
