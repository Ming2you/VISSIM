"""Compare validated, same-input decisions; this is not a VISSIM outcome report."""
import argparse
import copy
import csv
import hashlib
import json
import math
from pathlib import Path

from diagnostics.run_area_production_preflight import validate_result

ROOT = Path(__file__).resolve().parents[1]
BETAS = (0, 60, 150, 300)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_config(cfg):
    value = copy.deepcopy(cfg)
    value.pop('name', None)
    value['control_area_objective']['beta_seconds'] = None
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, action='append', required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    out = args.output_directory.resolve()
    if not out.is_relative_to(ROOT / 'diagnostics') or out.exists():
        parser.error('Choose a new diagnostics output directory')
    records, inputs, reference = {}, {}, None
    for supplied in args.manifest:
        path = supplied.resolve()
        manifest = json.loads(path.read_text(encoding='utf-8'))
        if not (manifest.get('valid') is True and manifest['exit_code'] == 0 and
                manifest['source_unchanged'] and manifest['inputs_unchanged'] and
                manifest['surviving_worker_pids'] == []):
            raise ValueError('Unvalidated or changed preflight: ' + str(path))
        action_path = path.with_name('action.json')
        action = json.loads(action_path.read_text(encoding='utf-8'))
        beta = action['metadata']['control_area_beta_seconds']
        if beta not in BETAS or beta in records:
            raise ValueError('Duplicate or unsupported coefficient')
        validate_result(action, beta)
        command = manifest['command']
        cfg_path = Path(command[command.index('--tuning-json') + 1])
        cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
        if sha(cfg_path) != manifest['config_sha256']:
            raise ValueError('Configuration changed after the decision')
        previous = command[command.index('--previous-action-json') + 1]
        state = command[command.index('--state-json') + 1]
        identity = {
            'recorded_run': manifest['recorded_run'],
            'recorded_sim_sec': manifest['recorded_sim_sec'],
            'state_sha256': sha(Path(state)),
            'previous_action_sha256': sha(Path(previous)),
            'source_sha256': manifest['source_sha256'],
            'normalized_configuration': normalized_config(cfg),
        }
        for input_path in (Path(state), Path(previous)):
            relative = str(input_path.relative_to(ROOT))
            if sha(input_path) != manifest['input_sha256'][relative]:
                raise ValueError('Recorded decision input changed')
        if reference is None:
            reference = identity
        elif reference != identity:
            raise ValueError('Decisions differ beyond the objective coefficient')
        d = action['diagnostics']
        ttt, ttd = d['control_area_follower_ttt_veh_h'], d['control_area_follower_ttd_veh']
        if not all(math.isfinite(x) and x >= 0 for x in (ttt, ttd)):
            raise ValueError('Invalid predicted area metric')
        record = {
            'beta_seconds': int(beta), 'manifest': str(path.relative_to(ROOT)),
            'wall_sec': manifest['elapsed_sec'],
            'follower_ttt_veh_h': ttt, 'follower_ttd_veh': ttd,
            'follower_objective_veh_h': d['control_area_follower_objective_veh_h'],
            'leader_held_objective_veh_h': action['metadata']['leader_objective'],
            'vsl': action['vsl'], 'ramp_metering': action['ramp_metering'],
            'green_times': action['green_times'], 'offsets': action['offsets'],
            'selected_stage_fallback': d['leader_selected_stage_fallback'],
            'follower_formula_recomputed': ttt - beta / 3600 * ttd,
        }
        records[int(beta)] = record
        for input_path in (path, action_path, cfg_path, Path(state), Path(previous)):
            inputs[str(input_path.relative_to(ROOT))] = sha(input_path)
    if set(records) != set(BETAS):
        raise ValueError('All four candidate decisions are required')
    for beta, record in records.items():
        record['predicted_follower_dominated_by'] = [other for other, row in records.items()
            if other != beta and row['follower_ttt_veh_h'] <= record['follower_ttt_veh_h'] and
            row['follower_ttd_veh'] >= record['follower_ttd_veh'] and
            (row['follower_ttt_veh_h'] < record['follower_ttt_veh_h'] or
             row['follower_ttd_veh'] > record['follower_ttd_veh'])]
    commands = []
    for kind in ('vsl', 'ramp_metering', 'green_times', 'offsets'):
        keys = sorted(records[0][kind])
        if any(set(row[kind]) != set(keys) for row in records.values()):
            raise ValueError('Command topology differs between coefficients')
        for key in keys:
            commands.append({'kind': kind, 'id': key,
                **{f'beta{beta}': records[beta][kind][key] for beta in BETAS},
                'changed': len({records[beta][kind][key] for beta in BETAS}) > 1})
    result = {
        'schema': 'area-weight-preflight-comparison/v1', 'status': 'PASS',
        'scope': 'Same observed state and prior action, same frozen model, four independent full MPC decisions.',
        'limits': [
            'These are model predictions, not VISSIM traffic outcomes or a selected final weight.',
            'Follower metrics belong to its searched rollout. The leader score uses a held endpoint; their values need not coincide.',
            'A dominated searched rollout identifies local search sensitivity; it does not prove a globally optimal alternative or actual traffic benefit.',
            'This 900-second decision does not validate congestion onset, propagation or later actions.'
        ],
        'recorded_run': reference['recorded_run'], 'recorded_sim_sec': reference['recorded_sim_sec'],
        'state_sha256': reference['state_sha256'],
        'previous_action_sha256': reference['previous_action_sha256'],
        'source_sha256': reference['source_sha256'], 'input_sha256': inputs,
        'records': [records[beta] for beta in BETAS],
        'command_counts': {kind: {'total': sum(row['kind'] == kind for row in commands),
            'vary_with_beta': sum(row['kind'] == kind and row['changed'] for row in commands)}
            for kind in ('vsl', 'ramp_metering', 'green_times', 'offsets')},
    }
    out.mkdir()
    (out / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    with (out / 'commands.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(commands[0]))
        writer.writeheader()
        writer.writerows(commands)
    lines = [
        '# Same-state objective-weight decision comparison', '',
        'All four full MPC decisions pass the objective and actuation contract checks on the same actual 900-second input. These are internal model predictions. VISSIM outcomes and a final weight remain pending.', '',
        '| Reward seconds/vehicle | Follower TTT [veh h] | Follower TTD [veh] | Follower J [veh h] | Leader held J [veh h] | Wall [s] |',
        '|---:|---:|---:|---:|---:|---:|',
    ]
    for beta in BETAS:
        r = records[beta]
        lines.append(f"| {beta} | {r['follower_ttt_veh_h']:.6f} | {r['follower_ttd_veh']:.6f} | {r['follower_objective_veh_h']:.6f} | {r['leader_held_objective_veh_h']:.6f} | {r['wall_sec']:.2f} |")
    lines += ['', 'Follower and held leader objectives use different rollout paths and are deliberately reported separately. Scores at different reward coefficients cannot be compared as one common objective.', '',
        'The complete four-lever command table is `commands.csv`. Coefficient sensitivity is:']
    for kind, counts in result['command_counts'].items():
        lines.append(f"- {kind}: {counts['vary_with_beta']} of {counts['total']} fields change across these four decisions.")
    lines += ['', 'Predicted follower dominance, when present, is evidence of search sensitivity, not simulator performance:']
    for beta in BETAS:
        lines.append(f"- beta {beta}: dominated by {records[beta]['predicted_follower_dominated_by']} among these four searched rollouts.")
    lines += ['', 'The common state, previous action, runtime sources and configuration equivalence are checked. Configuration differences are restricted to the coefficient and its descriptive name. Source/input hashes and original full preflight manifests are retained in `comparison.json`.', '']
    (out / 'assessment.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'output': str(out), 'status': 'PASS', 'command_counts': result['command_counts']}))


if __name__ == '__main__':
    main()
