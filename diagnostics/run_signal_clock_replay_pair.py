"""Sequential same-input original/cached-clock replay, restoring the cached source.

The actual adapter path is used in both cases. Only the reviewed clock module is
temporarily switched to its byte-pinned original; no alternate adapter is made.
Do not run another model/benchmark while this source-switching pair is active.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

from diagnostics.compare_decision_preservation import compare
from diagnostics.run_area_production_preflight import process_snapshot, owned_descendants, stop_exact_process

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'evaluation/controllers/signal_actuation_contract.py'
BEFORE = '8a470f7083fb3452756cd39573a690cc164989a079cd66eb10e1279f0a8f4c1f'
AFTER = '9581813d96fb27a7275ba41766763bd0bf123a200fb15b8cec8bf42e484227b5'
BASE = ROOT/'diagnostics/performance_head_off_baseline_v1'
CACHED = ROOT/'diagnostics/performance_head_off_clock_v1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def prepare_family(*, initial=False):
    original = json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
    updated = json.loads(json.dumps(original))
    key = next(k for k in original['source_sha256'] if k.replace('\\', '/') == SOURCE.relative_to(ROOT).as_posix())
    require(original['source_sha256'][key] == BEFORE, 'Baseline clock pin differs')
    for path, expected in original['source_sha256'].items():
        if path != key and sha((ROOT/path).read_bytes()) != expected:
            raise ValueError('Non-clock baseline source changed: '+path)
    updated['source_sha256'][key] = AFTER
    updated['purpose'] = ('Same initial head-ON config bytes, reviewed signal-clock optimization only.' if initial
                          else 'Same head-OFF config bytes, reviewed signal-clock optimization only.')
    for value in updated['outputs'].values():
        value['path'] = str((CACHED/Path(value['path']).name).relative_to(ROOT))
    if CACHED.exists():
        require(json.loads((CACHED/'manifest.json').read_text(encoding='utf-8')) == updated,
                'Existing cached family manifest differs')
    else:
        CACHED.mkdir()
        for beta, old in original['outputs'].items():
            raw = (ROOT/old['path']).read_bytes()
            require(sha(raw) == old['sha256'], 'Baseline config differs: '+beta)
            (ROOT/updated['outputs'][beta]['path']).write_bytes(raw)
        (CACHED/'manifest.json').write_text(json.dumps(updated, indent=2)+'\n', encoding='utf-8')
    for beta, old in original['outputs'].items():
        left = (ROOT/old['path']).read_bytes()
        right = (ROOT/updated['outputs'][beta]['path']).read_bytes()
        require(sha(left) == old['sha256'] and sha(right) == updated['outputs'][beta]['sha256'],
                'Family config SHA differs: '+beta)
        require(left == right, 'Family config bytes differ: '+beta)
    proof = {'baseline_manifest_sha256': sha((BASE/'manifest.json').read_bytes()),
             'cached_manifest_sha256': sha((CACHED/'manifest.json').read_bytes()),
             'provenance_scope': 'Manifest provenance is inherited baseline provenance. The current source delta is recorded here.',
             'source_delta': {key: {'before': BEFORE, 'after': AFTER}},
             'all_nonclock_source_pins_verified': True, 'all_four_config_bytes_and_pins_verified': True}
    proof_path = CACHED/'clock_source_provenance.json'
    if proof_path.exists():
        require(json.loads(proof_path.read_text(encoding='utf-8')) == proof, 'Clock provenance proof differs')
    else:
        proof_path.write_text(json.dumps(proof, indent=2)+'\n', encoding='utf-8')
    return updated


def main():
    global BASE, CACHED
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--time', type=int, required=True, choices=(900, 1500, 3300, 4950))
    parser.add_argument('--evaluation-trace', action='store_true',
                        help='Compare all observed local candidates with v3; never a normal timing benchmark')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--baseline-family', help='Reviewed direct diagnostics child with the original clock pin')
    parser.add_argument('--baseline-family-sha256')
    parser.add_argument('--cached-family', help='New direct diagnostics child for the same config bytes and cached clock')
    args = parser.parse_args()
    if args.time == 900:
        BASE = ROOT/'diagnostics/contract_candidate_configs_v4'
        CACHED = ROOT/'diagnostics/performance_initial_clock_replay_v1'
    custom = (args.baseline_family, args.baseline_family_sha256, args.cached_family)
    require(not any(custom) or all(custom), 'Custom families require both names and the exact baseline manifest SHA')
    if all(custom):
        require(all(re.fullmatch(r'[A-Za-z0-9_-]+', name) for name in (args.baseline_family, args.cached_family)),
                'Family names must be direct diagnostics children')
        require(args.baseline_family != args.cached_family, 'Distinct before/after families required')
        BASE = ROOT/'diagnostics'/args.baseline_family
        CACHED = ROOT/'diagnostics'/args.cached_family
        require(sha((BASE/'manifest.json').read_bytes()) == args.baseline_family_sha256, 'Custom baseline manifest SHA differs')
    after = SOURCE.read_bytes()
    if sha(after) != AFTER:
        raise ValueError('Start only from the exact reviewed cached-clock source')
    with zipfile.ZipFile(ROOT/'diagnostics/fixtures/signal_clock_original_module.zip') as archive:
        before = archive.read(SOURCE.relative_to(ROOT).as_posix())
    if sha(before) != BEFORE:
        raise ValueError('Original module archive differs from the frozen baseline')
    prepare_family(initial=args.time == 900)
    if not args.execute:
        print('Prepared exact same-byte after-family; no source change or model execution.')
        return
    tag = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    prefix = 'trace_pair' if args.evaluation_trace else 'pair'
    directory = ROOT/f'diagnostics/signal_clock_performance_v1/{prefix}_t{args.time}_{tag}'
    directory.mkdir(parents=True, exist_ok=False)
    auxiliary = [Path(__file__).resolve(), ROOT/'diagnostics/compare_decision_preservation.py',
                 ROOT/'diagnostics/run_area_production_preflight.py']
    if args.evaluation_trace:
        auxiliary.append(ROOT/'diagnostics/signal_clock_trace_pair_validation.py')
    journal = {'time': args.time, 'scope': 'Sequential original/clock, same recorded state and prior action',
               'mode': 'evaluation_trace' if args.evaluation_trace else 'normal_resource_counters',
               'normal_timing_evidence': not args.evaluation_trace,
               'python': {'executable': sys.executable, 'version': sys.version,
                          'implementation': sys.implementation.name,
                          'executable_sha256': sha(Path(sys.executable).read_bytes())},
               'auxiliary_source_sha256': {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in auxiliary},
               'before_source_sha256': BEFORE, 'after_source_sha256': AFTER,
               'family_manifest_sha256': {str((p/'manifest.json').relative_to(ROOT)): sha((p/'manifest.json').read_bytes())
                                          for p in (BASE, CACHED)},
               'producer_sha256': sha(Path(__file__).read_bytes()), 'members': [], 'complete': False}
    def save():
        (directory/'pair.json').write_text(json.dumps(journal, indent=2)+'\n', encoding='utf-8')
    save()
    folders = []
    safe_to_restore = True
    try:
        for name, content, family in (('before', before, BASE), ('clock', after, CACHED)):
            if sha(SOURCE.read_bytes()) not in (BEFORE, AFTER):
                raise ValueError('Another writer changed the clock; refusing to overwrite it')
            SOURCE.write_bytes(content)
            require(sha(SOURCE.read_bytes()) == sha(content), 'Written source SHA differs')
            command = [sys.executable, '-X', 'utf8', '-m', 'diagnostics.run_area_production_preflight',
                       '--time', str(args.time), '--run',
                       ('codex_contract_observed_nc_s13_1050_v2_20260910' if args.time == 900
                        else 'codex_area_sources_beta0_s13_20260910'),
                       '--beta', '300', '--config-directory', family.name,
                       '--evaluation-trace' if args.evaluation_trace else '--resource-counters',
                       '--python-hash-seed', '20260910', '--timeout-sec',
                       '3600' if args.evaluation_trace else '1800', '--execute']
            journal['active'] = name
            journal['members'].append({'variant': name, 'command': command})
            save()
            process_snapshot()  # Permission check before launching any child.
            process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True, encoding='utf-8')
            safe_to_restore = False
            parent_record = process_snapshot().get(process.pid)
            try:
                stdout, stderr = process.communicate()
                # Success certifies the preflight's own exact-tree cleanup.
                # A failed/crashed launcher may leave descendants: fail closed
                # and require an inventory before restoring that source.
                safe_to_restore = process.returncode == 0
            except BaseException:
                # communicate does not terminate the parent on interruption;
                # discover and stop its exact descendants before source restore.
                snapshot = process_snapshot()
                if parent_record and snapshot.get(process.pid, {}).get('created') == parent_record['created']:
                    owned = {}
                    owned_descendants(snapshot, parent_record, owned)
                    for child in reversed(list(owned.values())):
                        stop_exact_process(child)
                    stop_exact_process(parent_record)
                    process.wait()
                # A child can spawn during a cleanup snapshot. Even after this
                # bounded best-effort stop, require a separate inventory before
                # any interrupted-run source restoration.
                safe_to_restore = False
                journal['interrupted_owned_tree_cleanup_attempted'] = True
                raise
            (directory/(name+'.stdout.txt')).write_text(stdout, encoding='utf-8')
            (directory/(name+'.stderr.txt')).write_text(stderr, encoding='utf-8')
            journal['members'][-1]['exit_code'] = process.returncode
            save()
            if process.returncode:
                raise RuntimeError(f'{name} preflight failed; original failure retained in {directory}')
            paths = [line.split('=', 1)[1] for line in stdout.splitlines() if line.startswith('PRODUCTION_PREFLIGHT=')]
            require(len(paths) == 1, 'Expected exactly one completed preflight manifest')
            manifest_path = Path(paths[0]).resolve()
            require(manifest_path.is_relative_to(ROOT/'diagnostics/area_production_preflight'),
                    'Preflight manifest escapes its diagnostics directory')
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            require(manifest['valid'] and manifest['inputs_unchanged'] and manifest['source_unchanged'],
                    'Preflight preservation checks failed')
            journal['members'][-1].update(manifest=str(manifest_path.relative_to(ROOT)),
                                          decision_wall_sec=manifest['validated_metadata']['decision_wall_sec'])
            save()
            folders.append(manifest_path.parent)
            print('PAIR_MEMBER_COMPLETE='+name+' '+str(manifest_path), flush=True)
        result = compare(*folders)
        (directory/'strict_result_comparison.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
        exact_delta = [(r['path'].replace('\\', '/'), r.get('left'), r.get('right'), r['reason'])
                       for r in result['source_differences']] == [
                           ('/evaluation/controllers/signal_actuation_contract.py', BEFORE, AFTER, 'value')]
        manifests_unchanged = all(sha((ROOT/p).read_bytes()) == h
                                 for p, h in journal['family_manifest_sha256'].items())
        journal['source_delta_exactly_reviewed_clock'] = exact_delta
        journal['family_manifests_unchanged'] = manifests_unchanged
        auxiliary_unchanged = all(sha((ROOT/p).read_bytes()) == h
                                  for p,h in journal['auxiliary_source_sha256'].items())
        python_unchanged = sha(Path(sys.executable).read_bytes()) == journal['python']['executable_sha256']
        journal['auxiliary_sources_unchanged'] = auxiliary_unchanged
        journal['python_executable_unchanged'] = python_unchanged
        trace_pass = True
        if args.evaluation_trace:
            from diagnostics.signal_clock_trace_pair_validation import validate_trace_pair
            trace_result = validate_trace_pair(*folders)
            (directory/'strict_trace_comparison.json').write_text(json.dumps(trace_result, indent=2)+'\n', encoding='utf-8')
            trace_pass = trace_result['passed']
        journal['decision_preservation_pass'] = (result['returned_results_exact'] and result['execution_environment_equal']
                                                and exact_delta and manifests_unchanged and auxiliary_unchanged
                                                and python_unchanged and trace_pass)
        if not journal['decision_preservation_pass']:
            raise AssertionError('Pair result differs; keep the full difference evidence')
    except BaseException as exc:
        journal['error'] = {'type': type(exc).__name__, 'message': str(exc)}
        save()
        raise
    finally:
        if not safe_to_restore:
            journal['restored'] = False
            journal['requires_process_cleanup_before_source_restore'] = True
            save()
            raise RuntimeError('Could not certify child cleanup; retain current source and inspect the owned run before restoring')
        # Preflight owns/waits its process tree before returning. Never overwrite
        # an unexpected user/source change during restoration.
        if sha(SOURCE.read_bytes()) not in (BEFORE, AFTER):
            journal['restored'] = False
            save()
            raise ValueError('Unexpected clock edit; preserved for review rather than overwritten')
        SOURCE.write_bytes(after)
        journal['restored'] = sha(SOURCE.read_bytes()) == AFTER
        journal['complete'] = journal.get('decision_preservation_pass', False) and journal['restored']
        journal.pop('active', None)
        save()
        require(journal['restored'], 'Final cached source restoration failed')
    print('CLOCK_PAIR='+str(directory/'pair.json'), flush=True)


if __name__ == '__main__':
    main()
