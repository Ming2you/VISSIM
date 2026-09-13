"""One-process no-op scope regressions: no endpoint, controller main, native or hash scan."""
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pickle
import sys
from types import SimpleNamespace

D = Path(__file__).resolve().parent
ROOT = D.parents[3]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine'), str(ROOT/'plant/src')]
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers.area_follower_objective import shared_query_runtime_scope
spec = importlib.util.spec_from_file_location('guard6300_trace_helpers', D/'guard6300_trace_v1.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
SNAPSHOT = D/'guard6300_hash7_script_trace_v1/snapshot_00.pickle'


def sha(data): return hashlib.sha256(data).hexdigest()


class Reader(pickle.Unpickler):
    def find_class(self, module, name):
        if module == '__main__': return getattr(adapter, name)
        return super().find_class(module, name)


def load_bytes(payload):
    import io
    return Reader(io.BytesIO(payload)).load()


def selected(key, value):
    return key.startswith('_') and key.isupper() and isinstance(value, (dict, list, set))


def runtime_now():
    return {key: value for key, value in vars(adapter).items() if selected(key, value)}


@contextmanager
def installed(runtime):
    previous = runtime_now()
    for key in previous: delattr(adapter, key)
    for key, value in runtime.items(): setattr(adapter, key, value)
    try:
        yield
    finally:
        for key in tuple(runtime_now()): delattr(adapter, key)
        for key, value in previous.items(): setattr(adapter, key, value)


def run_case(out, name, context, runtime, *, alias=None):
    with installed(runtime):
        old_set = adapter._MIDBLOCK_CACHE['d'] if hasattr(adapter, '_MIDBLOCK_CACHE') else None
        old_order = list(old_set) if old_set is not None else None
        alias_before = alias(context, runtime_now()) if alias else None
        before = pickle.dumps((context, runtime_now()), protocol=5)
        with shared_query_runtime_scope():
            pass
        after = pickle.dumps((context, runtime_now()), protocol=5)
        alias_after = alias(context, runtime_now()) if alias else None
        current_set = adapter._MIDBLOCK_CACHE['d'] if old_set is not None else None
        result = {'case': name, 'query_body': 'pass', 'before_sha256': sha(before), 'after_sha256': sha(after),
            'full_pickle_changed': before != after, 'same_alias_before': alias_before, 'same_alias_after': alias_after,
            'nested_set_count': len(old_set) if old_set is not None else None,
            'nested_set_values_equal': old_set == current_set if old_set is not None else None,
            'nested_set_object_same': old_set is current_set if old_set is not None else None,
            'nested_set_iteration_changed': old_order != list(current_set) if old_set is not None else None}
        for suffix, payload in (('before', before), ('after', after)):
            path = out/(name+'_'+suffix+'.pickle')
            with path.open('xb') as stream: stream.write(payload)
        # Only after the observed scope: avoid typed traversal before reproduction.
        before_value, before_runtime = load_bytes(before)
        after_value, after_runtime = load_bytes(after)
        b = helper.tree_observation({'context': before_value, 'runtime': before_runtime})
        a = helper.tree_observation({'context': after_value, 'runtime': after_runtime})
        result['typed_value_hash_equal'] = b['semantic_sha256'] == a['semantic_sha256']
        result['typed_comparison_opaque_paths'] = sorted(set(b['opaque_paths']) | set(a['opaque_paths']))
        result['typed_comparison_cycle_paths'] = sorted(set(b['cycle_paths']) | set(a['cycle_paths']))
        result['global_pickle_changes'] = {key: {'before': sha(pickle.dumps(before_runtime.get(key), protocol=5)),
            'after': sha(pickle.dumps(after_runtime.get(key), protocol=5))}
            for key in sorted(set(before_runtime) | set(after_runtime))
            if pickle.dumps(before_runtime.get(key), protocol=5) != pickle.dumps(after_runtime.get(key), protocol=5)}
        return result


def main():
    out = D/'guard6300_scope_regression_v1'
    out.mkdir(exist_ok=False)
    snapshot_bytes = SNAPSHOT.read_bytes()
    source = ROOT/'evaluation/controllers/area_follower_objective.py'
    source_sha = sha(source.read_bytes())
    cases = []
    context, runtime = load_bytes(snapshot_bytes)
    cases.append(run_case(out, 'actual_snapshot_noop', context, runtime))
    # Same31 actual strings, different permitted set allocation/deletion history.
    # This is explicitly synthetic, not a claim about the native failure history.
    context, runtime = load_bytes(snapshot_bytes)
    values = set(runtime['_MIDBLOCK_CACHE']['d'])
    temporary = {'scope_fixture_temporary_'+str(i) for i in range(4096)}
    assert not values & temporary
    values.update(temporary)
    for value in temporary: values.remove(value)
    assert values == runtime['_MIDBLOCK_CACHE']['d'] and len(values) == 31
    runtime['_MIDBLOCK_CACHE']['d'] = values
    cases.append(run_case(out, 'actual_strings_synthetic_set_history_noop', context, runtime))
    # The exact alias shape _patched_segment_vsl can establish from a real cfg row.
    context, runtime = load_bytes(snapshot_bytes)
    row = context['follower'].cfg.network.freeway_segment_params['FW_E'][0]
    runtime['_FW_SEG_CTX']['p'] = row
    alias = lambda c,r: r['_FW_SEG_CTX']['p'] is c['follower'].cfg.network.freeway_segment_params['FW_E'][0]
    cases.append(run_case(out, 'actual_cfg_row_synthetic_alias_noop', context, runtime, alias=alias))
    # Minimal pure-builtin counterexample, independent of model object behavior.
    row = {'v_free': 120., 'rho_crit': 27.}
    cases.append(run_case(out, 'minimal_builtin_alias_noop', {'cfg': {'row': row}}, {'_FW_SEG_CTX': {'p': row}},
        alias=lambda c,r: r['_FW_SEG_CTX']['p'] is c['cfg']['row']))
    assert cases[-1]['full_pickle_changed'] and cases[-1]['same_alias_before'] and not cases[-1]['same_alias_after']
    assert cases[-1]['typed_value_hash_equal']
    assert sha(SNAPSHOT.read_bytes()) == sha(snapshot_bytes) and sha(source.read_bytes()) == source_sha
    report = {'schema': 'guard6300-noop-scope-regression/v1', 'scope': 'Single Python process; canonical scope only, body pass. No endpoint/native/controller main/hash-seed scan.',
        'python_hash_seed': os.environ.get('PYTHONHASHSEED'), 'process_probe_hash': hash('guard6300_probe'),
        'canonical_scope_source': str(source), 'canonical_scope_sha256': source_sha,
        'snapshot': str(SNAPSHOT), 'snapshot_sha256': sha(snapshot_bytes), 'cases': cases,
        'minimum_alias_counterexample_confirmed': True, 'native6300_root_cause_confirmed': False,
        'source_and_original_snapshot_unchanged': True}
    with (out/'result.json').open('x', encoding='utf-8') as stream: json.dump(report, stream, indent=2)
    print(json.dumps({'minimum_alias_counterexample_confirmed':True,'native6300_root_cause_confirmed':False,
        'cases':[{key:row[key] for key in ('case','full_pickle_changed','typed_value_hash_equal','nested_set_iteration_changed','same_alias_before','same_alias_after')} for row in cases]}))


if __name__ == '__main__': main()
