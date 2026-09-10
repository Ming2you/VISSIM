"""Compare recorded preflight/live inputs and outputs without importing a model."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LEVERS = ('vsl', 'ramp_metering', 'green_times', 'offsets')
HEAD_VALUE = re.compile(r'^(head_(?:discharge_floor|candidate_rate|candidate_end)_\d+_p\d+)_([0-9a-f]{16})$')


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def stable(path):
    path = Path(path).resolve()
    before = path.stat()
    blob = path.read_bytes()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError('Input changed during read: ' + str(path))
    return blob, {'path': str(path), 'sha256': sha(blob), 'bytes': len(blob)}


def load(path, evidence):
    blob, row = stable(path)
    evidence.append(row)
    return json.loads(blob.decode('utf-8-sig'))


def head_values(metadata):
    values, original = {}, {}
    for key, value in metadata.items():
        match = HEAD_VALUE.fullmatch(key)
        if match:
            physical = match[1]
            if physical in values:
                raise ValueError('Multiple contexts for one physical head group: ' + physical)
            values[physical] = value
            original[physical] = key
    return values, original


def different(a, b):
    return {k: {'offline': a.get(k), 'live': b.get(k)}
            for k in sorted(a.keys() | b.keys()) if a.get(k) != b.get(k)}


def context(raw, manifest, action):
    window = raw['local_observation']['signal_observation_window']
    obs = manifest['signal_observation']
    if raw['run_provenance']['run_id'] != manifest['run_id']:
        raise ValueError('Raw/manifest run identity mismatch')
    if window['config_sha256'] != manifest['files']['tuning']['sha256']:
        raise ValueError('Raw/recorded tuning identity mismatch')
    identity = {'run_id': manifest['run_id'],
                'config_chain_sha256': [s['sha256'] for s in obs['config_chain']],
                'network_sha256': manifest['files']['network']['sha256'],
                'quality': obs['options']}
    digest = sha(json.dumps(identity, sort_keys=True).encode())
    if action['metadata'].get('head_provenance_' + digest) != 1.0:
        raise ValueError('Action does not retain its own observation provenance')
    return {'identity': identity, 'context_sha256': digest,
            'raw_run_provenance': raw['run_provenance'],
            'action_run_provenance': action['run_provenance']}


def audit(preflight, run_name, second):
    evidence = []
    preflight = Path(preflight).resolve()
    run = ROOT / 'evaluation/runs' / run_name
    decision = run / ('decisions_' + run_name)
    pre = load(preflight / 'manifest.json', evidence)
    if not all(pre.get(k) is True for k in ('valid', 'source_unchanged', 'inputs_unchanged')) or pre['exit_code'] != 0:
        raise ValueError('Preflight was not validated successfully')
    if pre['recorded_sim_sec'] != second:
        raise ValueError('Preflight timestamp differs')
    command = pre['command']
    arg = lambda key: Path(command[command.index(key) + 1])
    raws = [load(arg('--state-json'), evidence), load(decision / f'state_{second:06d}.json', evidence)]
    acts = [load(preflight / 'action.json', evidence), load(decision / f'action_{second:06d}.json', evidence)]
    manifests = [load(r['run_provenance']['manifest_path'], evidence) for r in raws]
    if any(a['metadata']['controller_status'] != 'ok' or a['metadata']['sim_sec'] != second for a in acts):
        raise ValueError('Completed successful decisions are required')
    if pre['config_sha256'] != manifests[1]['files']['tuning']['sha256']:
        raise ValueError('Offline optimization/live config differ')
    config_blob, config_evidence = stable(arg('--tuning-json'))
    evidence.append(config_evidence)
    if sha(config_blob) != pre['config_sha256']:
        raise ValueError('Optimization config changed')
    previous = [load(arg('--previous-action-json'), evidence)]
    previous_sec = previous[0]['metadata']['sim_sec']
    previous.append(load(decision / f'action_{int(previous_sec):06d}.json', evidence))
    contexts = [context(r, m, a) for r, m, a in zip(raws, manifests, acts)]
    head_comparisons = {}
    for label, pair in [('previous', previous), ('decision', acts)]:
        values = [head_values(a['metadata']) for a in pair]
        head_comparisons[label] = {'counts': [len(v[0]) for v in values],
            'physical_value_differences': different(values[0][0], values[1][0]),
            'original_identity_keys': [v[1] for v in values],
            'values_by_physical_group': values[0][0],
            'provenance_markers': [{k: v for k, v in a['metadata'].items() if k.startswith('head_provenance_')} for a in pair],
            'observation_status': [{k: v for k, v in a['metadata'].items() if k.startswith('head_observation_')} for a in pair]}
    top = [{k: v for k, v in r.items() if k not in ('run_provenance', 'local_observation')} for r in raws]
    local = [{k: v for k, v in r['local_observation'].items() if k != 'signal_observation_window'} for r in raws]
    heads = [r['local_observation']['signal_observation_window'] for r in raws]
    head_content = [{k: v for k, v in h.items() if k != 'config_sha256'} for h in heads]
    csv_blobs = [stable(p) for p in (preflight / 'action.csv', decision / f'action_{second:06d}.csv')]
    evidence.extend(x[1] for x in csv_blobs)
    csv_rows = [list(csv.DictReader(io.StringIO(x[0].decode('utf-8-sig')))) for x in csv_blobs]
    source_pins = {str((ROOT / p).resolve()): value for p, value in pre['input_sha256'].items()}
    live_sources = [*manifests[1]['files'].values(), *manifests[1]['controller_sources'], *manifests[1]['signal_programs']]
    common = {str(Path(row['path']).resolve()): row['sha256'] for row in live_sources if row.get('exists', True) and str(Path(row['path']).resolve()) in source_pins}
    mismatched_sources = {p: {'preflight': source_pins[p], 'live': value} for p, value in common.items() if source_pins[p] != value}
    levers = {k: {'equal': acts[0][k] == acts[1][k], 'entries': [len(a[k]) for a in acts],
                  'offline': acts[0][k], 'live': acts[1][k]} for k in LEVERS}
    result = {'schema': 'preflight-live-action-comparison/v1', 'status': 'complete',
        'live_run': run_name, 'sim_sec': second, 'preflight_directory': str(preflight),
        'raw_contexts': contexts, 'optimization_config_sha256': pre['config_sha256'],
        'recorded_common_source_count': len(common), 'recorded_source_mismatches': mismatched_sources,
        'snapshot_top_level_differences': list(different(*top)),
        'snapshot_legacy_local_differences': list(different(*local)),
        'head_window_differences_except_config_identity': list(different(*head_content)),
        'head_counts': [len(h['heads']) for h in heads],
        'head_window_bounds': [[h['start_sec'], h['end_sec']] for h in heads],
        'head_metadata': head_comparisons, 'four_lever_vectors': levers,
        'leader_targets_equal': all(acts[0][k] == acts[1][k] for k in ('N_P_star', 'N_UF_star')),
        'decision_csv_raw_exact': csv_blobs[0][0] == csv_blobs[1][0],
        'decision_csv_parsed_exact': csv_rows[0] == csv_rows[1],
        'decision_csv_rows': [len(rows) for rows in csv_rows],
        'source_files': evidence, 'producer_sha256': sha(Path(__file__).read_bytes()),
        'limits': ['No model, optimizer, simulator, FZP or COM is executed/read by this comparison.',
            'Raw run/config identities are deliberately retained; head hash suffixes are only normalized for physical-group value comparison, never for reuse by a controller.',
            'Offline raw observation belongs to the recorded NC config, while its optimization uses the current beta300 config. This is distinct from rewriting the raw observation provenance.',
            'Decision CSV identity proves identical emitted commands. Actual COM service over the following interval requires the separate signal/readback audit.']}
    result['matching_inputs_and_outputs'] = (not mismatched_sources and not result['snapshot_top_level_differences']
        and not result['snapshot_legacy_local_differences'] and not result['head_window_differences_except_config_identity']
        and all(not row['physical_value_differences'] for row in head_comparisons.values())
        and all(v['equal'] for v in levers.values()) and result['leader_targets_equal'] and result['decision_csv_raw_exact'])
    # Recheck the bounded, immutable input set; no live-growing files are consumed.
    changed = [r['path'] for r in evidence if sha(Path(r['path']).read_bytes()) != r['sha256']]
    if changed:
        raise ValueError('Inputs changed during comparison: ' + repr(changed))
    result['input_changes'] = changed
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preflight', type=Path, required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--second', type=int, default=900)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / 'diagnostics') or output.exists():
        raise ValueError('Use a new diagnostic output path')
    result = audit(args.preflight, args.run, args.second)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(output), 'matching': result['matching_inputs_and_outputs'],
                      'input_changes': result['input_changes']}))


if __name__ == '__main__':
    main()
