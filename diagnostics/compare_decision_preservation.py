"""Exact returned-result comparison for same-input performance experiments."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
NON_RESULT_PATHS = {
    '/diagnostics/wu_faithful_solve_time_sec': 'selected follower elapsed time',
    '/metadata/decision_wall_sec': 'decision elapsed time',
    '/metadata/prediction_wall_sec': 'prediction elapsed time',
    '/prediction/wall_sec': 'prediction elapsed time duplicate',
    '/metadata/run_provenance/workspace_git_commit': 'runtime source revision provenance',
    '/run_provenance/workspace_git_commit': 'runtime source revision provenance duplicate',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_tuning_provenance(action, manifest, input_hashes):
    """A copied config path is provenance only when its bytes and fingerprint verify."""
    command = manifest['command']
    expected_path = str(Path(command[command.index('--tuning-json') + 1]).resolve())
    for document in (action['run_provenance'], action['metadata']['run_provenance']):
        tuning = document['inputs']['tuning_json']
        if (tuning['path'] != expected_path or tuning['exists'] is not True
                or tuning['sha256'] != input_hashes['--tuning-json']):
            raise ValueError('Returned tuning provenance does not match the actual hashed input')
        stable = {k: document[k] for k in ('numsim_repo_root', 'numsim_git_commit',
                  'numsim_snapshot_commit', 'numsim_src_sha256', 'imported_modules',
                  'signal_program_sha256')}
        stable['inputs'] = {k: v for k, v in document['inputs'].items() if k != 'state_json'}
        fingerprint = hashlib.sha256(json.dumps(stable, ensure_ascii=True, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()
        if fingerprint != document['execution_fingerprint_sha256']:
            raise ValueError('Returned execution fingerprint fails independent recomputation')
    return True


def candidate_timing_paths(actions):
    """Only matched elapsed-time fields from the audited full-candidate wrapper.

    priced_wu_link_controller.py:850-860 assigns perf_counter()-t0 after
    super()._evaluate_full_candidate returns. No cost/choice uses this field.
    The adapter copies that float to metadata with the explicit meta_ prefix.
    Missing keys, types, invalid values and disagreement of duplicates remain
    errors; no arbitrary timing-like substring is excluded.
    """
    paths = {}
    common = actions[0]['diagnostics'].keys() & actions[1]['diagnostics'].keys()
    for key in common:
        if not re.fullmatch(r'leader_candidate_wall_sec_[a-z_]+_[0-9]+', key):
            continue
        for action in actions:
            value = action['diagnostics'][key]
            duplicate = action['metadata'].get('meta_'+key)
            if (type(value) is not float or not math.isfinite(value) or value < 0
                    or type(duplicate) is not float or struct.pack('!d', value) != struct.pack('!d', duplicate)):
                raise ValueError('Invalid or mismatched candidate elapsed-time evidence: '+key)
        for path in ('/diagnostics/'+key, '/metadata/meta_'+key):
            paths[path] = 'Audited full-candidate perf_counter elapsed time (including exact metadata duplicate)'
    return paths


def differences(left, right, path=''):
    if type(left) is not type(right):
        return [{'path': path, 'left': left, 'right': right, 'reason': 'type'}]
    if isinstance(left, dict):
        rows = []
        for key in sorted(left.keys() | right.keys()):
            location = path + '/' + key.replace('~', '~0').replace('/', '~1')
            if key not in left or key not in right:
                rows.append({'path': location, 'left_present': key in left,
                             'right_present': key in right, 'left': left.get(key),
                             'right': right.get(key), 'reason': 'key_presence'})
            else:
                rows.extend(differences(left[key], right[key], location))
        return rows
    if isinstance(left, list):
        if len(left) != len(right):
            return [{'path': path, 'left': left, 'right': right, 'reason': 'length'}]
        return [row for i, (a, b) in enumerate(zip(left, right))
                for row in differences(a, b, path + '/' + str(i))]
    equal = struct.pack('!d', left) == struct.pack('!d', right) if isinstance(left, float) else left == right
    if equal:
        return []
    return [{'path': path, 'left': left, 'right': right, 'reason': 'value',
             **({'left_float_hex': left.hex(), 'right_float_hex': right.hex()}
                if isinstance(left, float) else {})}]


def compare(left, right):
    paths = [folder / name for folder in (left, right)
             for name in ('manifest.json', 'action.json', 'action.csv')]
    evidence = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    manifests = [json.loads((folder / 'manifest.json').read_text(encoding='utf-8')) for folder in (left, right)]
    for manifest in manifests:
        if not all(manifest.get(k) is True for k in ('valid', 'source_unchanged', 'inputs_unchanged')):
            raise ValueError('Both decisions must be completed and input/source validated')
    inputs = []
    for manifest in manifests:
        command = manifest['command']
        selected = {}
        for flag in ('--state-json', '--previous-action-json', '--tuning-json',
                     '--mapping-json', '--detector-mapping-json', '--calibration-json'):
            if flag not in command:
                continue
            path = Path(command[command.index(flag) + 1])
            relative = str(path.relative_to(ROOT))
            current = sha(path)
            if manifest['input_sha256'].get(relative) != current:
                raise ValueError('Recorded decision input changed: ' + relative)
            evidence[relative] = current
            selected[flag] = current
        inputs.append(selected)
    actions = [json.loads((folder / 'action.json').read_text(encoding='utf-8')) for folder in (left, right)]
    provenance_verified = all(validate_tuning_provenance(a, m, i)
                              for a, m, i in zip(actions, manifests, inputs))
    exclusions = dict(NON_RESULT_PATHS)
    exclusions.update(candidate_timing_paths(actions))
    if provenance_verified and inputs[0]['--tuning-json'] == inputs[1]['--tuning-json']:
        for prefix in ('/run_provenance', '/metadata/run_provenance'):
            exclusions[prefix + '/inputs/tuning_json/path'] = 'Separate source-pinned family; identical verified config bytes'
            exclusions[prefix + '/execution_fingerprint_sha256'] = 'Independently recomputed provenance fingerprint including config path; all component fields remain compared'
    all_diffs = differences(*actions)
    result_diffs = [row for row in all_diffs if row['path'] not in exclusions]
    other_diffs = [{**row, 'exclusion': exclusions[row['path']]}
                   for row in all_diffs if row['path'] in exclusions]
    csv_equal = (left / 'action.csv').read_bytes() == (right / 'action.csv').read_bytes()
    source_diffs = differences(*(m['source_sha256'] for m in manifests))
    execution_environments = [
        {**{k: m['environment'].get(k) for k in
            ('RW_OFFSET_WRITER', 'NUMSIM_REPO_ROOT', 'RW_MAINLINE_SG_ONLY')},
         'PYTHONHASHSEED': m.get('python_hash_seed', {}).get('adapter_and_workers')}
        for m in manifests]
    report = {'schema': 'decision-performance-result-preservation/v1',
              'left': str(left.relative_to(ROOT)), 'right': str(right.relative_to(ROOT)),
              'inputs_equal': inputs[0] == inputs[1], 'argument_file_sha256': inputs,
              'csv_bytes_exact': csv_equal, 'result_differences': result_diffs,
              'provenance_or_timing_differences': other_diffs, 'source_differences': source_diffs,
              'decision_wall_sec': [a['metadata']['decision_wall_sec'] for a in actions],
              'execution_environments': execution_environments,
              'execution_environment_equal': execution_environments[0] == execution_environments[1],
              'returned_provenance_independently_verified': provenance_verified,
              'returned_results_exact': inputs[0] == inputs[1] and csv_equal and not result_diffs,
              'input_sha256': evidence, 'producer_sha256': sha(Path(__file__)),
              'scope': 'Complete returned JSON including next-decision metadata and exact CSV. Intermediate candidates require the separate evaluation trace; source changes require independent review.'}
    if any(sha(ROOT / relative) != expected for relative, expected in evidence.items()):
        raise ValueError('Comparison evidence changed during read')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('left', type=Path)
    parser.add_argument('right', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    target = args.output.resolve()
    if not target.is_relative_to(ROOT / 'diagnostics') or target.exists():
        parser.error('Use a new output path under diagnostics')
    report = compare(args.left.resolve(), args.right.resolve())
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('returned_results_exact', 'inputs_equal', 'csv_bytes_exact',
                                            'decision_wall_sec', 'result_differences')}, indent=2))
    raise SystemExit(0 if report['returned_results_exact'] else 1)
