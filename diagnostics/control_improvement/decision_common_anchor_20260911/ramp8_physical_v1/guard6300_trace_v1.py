"""One recorded6300 command proof, preserving guards and stopping before prices/game.
Only process-local observation wrappers; the existing adapter main owns model/worker cleanup.
"""
import argparse
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import json
import os
from pathlib import Path
import pickle
import pickletools
import runpy
import struct
import sys
import time
import traceback
import types

D = Path(__file__).resolve().parent
ROOT = D.parents[3]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def tree_observation(root):
    """Diagnostic typed hashes plus actual order/alias witnesses; no deep copies."""
    memo, active, occurrences = {}, set(), {}
    sets, orders, opaque, cycles = {}, {}, {}, []

    def walk(value, path):
        kind = type(value)
        typename = kind.__module__ + '.' + kind.__qualname__
        if value is None or kind in (bool, int, str):
            return digest(encoded((typename, value)))
        if kind is float:
            return digest(encoded((typename, struct.pack('>d', value).hex())))
        if kind is bytes:
            return digest(encoded((typename, value.hex())))
        if kind in (types.FunctionType, types.BuiltinFunctionType, type):
            return digest(encoded((typename, value.__module__, value.__qualname__)))
        identity = id(value)
        occurrences.setdefault(identity, []).append(path)
        if identity in active:
            cycles.append(path)
            return digest(encoded(('cycle-unresolved', typename)))
        if identity in memo:
            return memo[identity]
        active.add(identity)
        if isinstance(value, dict):
            keys = list(value)
            orders[path] = [repr(key) for key in keys]
            parts = sorted((walk(key, path + '.<key>'), walk(value[key], path + '[' + repr(key) + ']')) for key in keys)
        elif kind in (list, tuple):
            parts = [walk(item, path + '[' + str(i) + ']') for i, item in enumerate(value)]
        elif kind in (set, frozenset):
            # Preserve raw iteration separately; semantic digest sorts values.
            sets[path] = {'type': typename, 'iteration': [repr(item) for item in value]}
            parts = sorted(walk(item, path + '.<set-item>') for item in value)
        elif hasattr(value, '__dict__'):
            parts = walk(vars(value), path + '.__dict__')
        else:
            # Unknown custom values stay explicit, never declared value-equal.
            opaque[path] = typename
            parts = ('opaque-pickle', digest(pickle.dumps(value, protocol=5)))
        active.remove(identity)
        result = digest(encoded((typename, parts)))
        memo[identity] = result
        return result

    semantic = walk(root, '$')
    aliases = sorted([paths for paths in occurrences.values() if len(paths) > 1])
    return {'semantic_sha256': semantic, 'sets': sets, 'dict_orders': orders,
            'aliases': aliases, 'opaque_paths': opaque, 'cycle_paths': cycles}


def changed_mapping(before, after):
    return {key: {'before': before.get(key), 'after': after.get(key)}
            for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)}


def exception_chain(exc):
    out, seen = [], set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        out.append({'type': type(exc).__name__, 'message': str(exc),
                    'traceback': ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__, chain=False))})
        exc = exc.__cause__ if exc.__cause__ is not None else exc.__context__
    return out


class DiagnosticStop(RuntimeError):
    pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('label')
    cli = parser.parse_args()
    if not cli.label.replace('_', '').isalnum():
        raise ValueError('Fresh result label required')
    out = D / cli.label
    out.mkdir(exist_ok=False)
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    os.environ['RW_OFFSET_WRITER'] = 'experiment'
    os.environ['PYTHONUTF8'] = '1'
    record = ROOT / 'evaluation/runs/codex_fid_cl9000_s13_v2/decisions_codex_fid_cl9000_s13_v2'
    config = ROOT / 'diagnostics/selected_control_demand/codex_fid_cl9000_s13_v2/config.json'
    args = ['evaluation/controllers/vissim_stackelberg_adapter.py',
        '--state-json', str(record / 'state_006300.json'),
        '--previous-action-json', str(record / 'action_006150.json'),
        '--out-action-json', str(out / 'action_006300.json'),
        '--out-action-csv', str(out / 'action_006300.csv'),
        '--mapping-json', 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json',
        '--detector-mapping-json', 'evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json',
        '--calibration-json', 'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json',
        '--tuning-json', str(config), '--controller', 'wu-link', '--mode', 'fast-smoke']
    paths = [Path(__file__), config, record / 'state_006300.json', record / 'action_006150.json', record / 'action_006150.csv',
             *sorted((ROOT / 'evaluation/controllers').glob('*.py'))]
    pins = {str(path): digest(path.read_bytes()) for path in paths}
    report = {'schema': 'guard6300-command-trace/v1', 'diagnostic_complete': False,
        'decision_completed': False, 'native_run': False, 'python_hash_seed': os.environ.get('PYTHONHASHSEED'),
        'process_probe_hash': hash('guard6300_probe'), 'hash_randomization_flag': sys.flags.hash_randomization,
        'entry_mode': 'canonical_script_runpy___main__',
        'arguments': args, 'source_sha256': pins, 'fingerprints': [], 'command_calls': 0,
        'scope': 'Canonical adapter.main on actual6300/6150/config. Original guard/fingerprint return values unchanged. Stop immediately after first command_evidence; no common-price/game search.'}
    start = time.perf_counter()
    snapshots = []
    from evaluation.controllers import joint_owner_neighbors as neighbors
    if 'evaluation.controllers.vissim_stackelberg_adapter' in sys.modules:
        raise RuntimeError('Script probe requires an uninitialized canonical adapter')
    original_make = neighbors.make_joint_neighbor_callbacks

    def make(*pos, **kw):
        original_fingerprint = kw['context_fingerprint']
        adapter = sys.modules['evaluation.controllers.vissim_stackelberg_adapter']
        report['adapter_module'] = {'name': adapter.__name__, 'file': adapter.__file__,
            'canonical_is_main': adapter is sys.modules['__main__'],
            'package_alias_same': adapter is sys.modules['evaluation.controllers'].vissim_stackelberg_adapter}
        area = sys.modules['evaluation.controllers.area_follower_objective']
        report['worker_entrypoints'] = {name: getattr(area, name).__module__ + '.' + getattr(area, name).__qualname__
            for name in ('_initialize_shared_response_worker', '_evaluate_shared_response_worker')}
        report['legacy_price_worker_bootstrap_module_name'] = adapter.__name__

        def fingerprint(value):
            token = original_fingerprint(value)
            runtime = {k: v for k, v in vars(adapter).items()
                       if k.startswith('_') and k.isupper() and isinstance(v, (dict, list, set))}
            full = pickle.dumps((value, runtime), protocol=5)
            index = len(snapshots)
            path = out / ('snapshot_' + str(index).zfill(2) + '.pickle')
            with path.open('xb') as stream:
                stream.write(full)
            observation = tree_observation({'context': value, 'runtime': runtime})
            top = {scope + '.' + str(key): digest(pickle.dumps(item, protocol=5))
                   for scope, container in (('context', value), ('runtime', runtime))
                   for key, item in container.items()}
            semantic_top = {scope + '.' + str(key): tree_observation(item)['semantic_sha256']
                           for scope, container in (('context', value), ('runtime', runtime))
                           for key, item in container.items()}
            row = {'index': index, 'token': token, 'captured_pickle_sha256': digest(full),
                   'captured_matches_returned_token': digest(full) == token,
                   'bytes': len(full), 'snapshot': str(path), 'top_pickle_sha256': top,
                   'semantic_top_sha256': semantic_top, 'semantic_sha256': observation['semantic_sha256'],
                   'opaque_paths': observation['opaque_paths'], 'cycle_paths': observation['cycle_paths'],
                   'frames': [{'offset': offset, 'bytes': arg} for opcode, arg, offset in pickletools.genops(full) if opcode.name == 'FRAME']}
            if snapshots:
                base, old = snapshots[0]
                row['diff_from_initial'] = {
                    'full_pickle_changed': token != base['token'],
                    'typed_value_hash_changed': row['semantic_sha256'] != base['semantic_sha256'],
                    'top_pickle_changes': changed_mapping(base['top_pickle_sha256'], top),
                    'semantic_top_changes': changed_mapping(base['semantic_top_sha256'], semantic_top),
                    'set_iteration_changes': changed_mapping(old['sets'], observation['sets']),
                    'dict_order_changes': changed_mapping(old['dict_orders'], observation['dict_orders']),
                    'alias_groups_removed': [group for group in old['aliases'] if group not in observation['aliases']],
                    'alias_groups_added': [group for group in observation['aliases'] if group not in old['aliases']]}
            snapshots.append((row, observation))
            report['fingerprints'].append(row)
            return token

        kw['context_fingerprint'] = fingerprint
        callbacks = original_make(*pos, **kw)
        command = callbacks['command_evidence']

        def first_command(*command_args, **command_kw):
            report['command_calls'] += 1
            try:
                result = command(*command_args, **command_kw)
            except BaseException as exc:
                report['command_exception_chain'] = exception_chain(exc)
                report['first_command_completed'] = False
                raise
            report['first_command_completed'] = True
            report['first_command_physical_rows_sha256'] = digest(pickle.dumps(result['physical_rows'], protocol=5))
            report['first_command_ordered_row_count'] = len(result['ordered_rows'])
            raise DiagnosticStop('DIAGNOSTIC_STOP_AFTER_FIRST_COMMAND_EVIDENCE')

        callbacks['command_evidence'] = first_command
        return callbacks

    neighbors.make_joint_neighbor_callbacks = make
    previous_argv = sys.argv
    sys.argv = args
    print(json.dumps({'stage': 'probe_start', 'hash_seed': report['python_hash_seed'], 'output': str(out)}), flush=True)
    try:
        with (out / 'stdout.txt').open('x', encoding='utf-8') as stdout, (out / 'stderr.txt').open('x', encoding='utf-8') as stderr:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                runpy.run_path(str(ROOT / args[0]), run_name='__main__')
        report['unexpected_adapter_return'] = True
    except DiagnosticStop as exc:
        report.update(diagnostic_complete=True, outcome='first_command_passed_then_diagnostic_stop', exception_chain=exception_chain(exc))
    except BaseException as exc:
        chain = exception_chain(exc)
        report.update(exception_chain=chain, outcome='canonical_failure')
        report['guard_reproduced'] = any(item['message'] == 'Frozen joint query context changed' for item in chain)
        report['diagnostic_complete'] = report['guard_reproduced']
    finally:
        neighbors.make_joint_neighbor_callbacks = original_make
        sys.argv = previous_argv
        report['wall_sec'] = time.perf_counter() - start
        report['source_changes'] = [path for path, before in pins.items() if digest(Path(path).read_bytes()) != before]
        report['diagnostic_complete'] = report['diagnostic_complete'] and not report['source_changes']
        joint_path = out / 'action_006300.joint.json'
        if joint_path.exists():
            joint = json.loads(joint_path.read_text(encoding='utf-8-sig'))
            report['canonical_joint'] = {'completed': joint['completed'], 'error': joint.get('error'),
                'source_changes': joint['source_changes'], 'physical_response_cache': joint.get('physical_response_cache')}
        with (out / 'trace.json').open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps({key: report.get(key) for key in ('diagnostic_complete', 'outcome', 'guard_reproduced',
        'command_calls', 'first_command_completed', 'wall_sec', 'source_changes')}), flush=True)
    return 0 if report['diagnostic_complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
