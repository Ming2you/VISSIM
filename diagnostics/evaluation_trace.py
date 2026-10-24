"""Optional return-frame evidence, separate from timing benchmarks and cProfile.

No model callable is replaced. Exact floats use hex strings; process identity and
source locations are provenance, not comparison keys. Only selected call/return
frames are inspected. The callback still receives all main-thread profile events,
so this is a correctness trace, never an uninstrumented timing measurement.
"""
from __future__ import annotations

import atexit
import dis
import hashlib
from itertools import zip_longest
import json
import os
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
CONTROL_FIELDS = ('N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times',
                  'offsets', 'inflow_outflow_allocation', 'infeasibility')
SCORE_FIELDS = ('index', 'stage', 'objective', 'objective_value', 'ttt', 'partial_ttt',
                'freeway_ttt', 'urban_ttt', 'far', 'barrier', 'max_rho',
                'leader_objective', 'control_area', 'completed', 'aborted',
                'price_hinge', 'leader_hinge', 'protected_queue',
                'objective_terms', 'rollout_used', 'iterations', 'converged',
                'residual_objective', 'residual_control')


def _dump(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False)


def digest(value):
    try:
        return hashlib.sha256(_dump(value).encode('utf-8')).hexdigest()
    except TypeError:
        from diagnostics.evaluation_trace_storage import streaming_hash
        return streaming_hash(value)


def canonical(value, seen=None):
    """Lossless numeric snapshots, with no repr(), address or arbitrary rounding."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return {'float_hex': value.hex()}
    if isinstance(value, Path):
        return str(value)
    seen = set() if seen is None else seen
    identity = id(value)
    if identity in seen:
        raise ValueError('Cyclic trace input requires an explicit field contract')
    seen.add(identity)
    try:
        if isinstance(value, dict):
            # Typed keys avoid collisions between e.g. integer 1 and string '1'.
            pairs = [(canonical(k, seen), canonical(v, seen)) for k, v in value.items()]
            return {'mapping': sorted(pairs, key=lambda x: _dump(x[0]))}
        if isinstance(value, (tuple, list)):
            return [canonical(v, seen) for v in value]
        if isinstance(value, (set, frozenset)):
            return {'set': sorted((canonical(v, seen) for v in value), key=_dump)}
        if hasattr(value, 'green_times') and hasattr(value, 'ramp_metering'):
            return control(value)
        if hasattr(value, '__dict__'):
            return {'fields': canonical(vars(value), seen)}
        raise TypeError('Unsupported trace value type: ' + type(value).__name__)
    finally:
        seen.remove(identity)


def control(value):
    if value is None:
        return None
    fields = {k: canonical(getattr(value, k)) for k in CONTROL_FIELDS if hasattr(value, k)}
    diag = getattr(value, 'diagnostics', {}) or {}
    commands = {k: v for k, v in diag.items() if k.startswith('rw_meter_')}
    marker = diag.get('_control_area_meter_finalized')
    if marker is not None:
        commands['finalization'] = {k: marker.get(k) for k in
            ('context_sha256', 'requested_rates', 'realized_rates', 'commands')}
    fields['physical_meter'] = canonical(commands)
    return fields


def result(value):
    if isinstance(value, (tuple, list)):
        return [result(v) for v in value]
    if value is None or isinstance(value, (str, bool, int, float, dict)):
        return canonical(value)
    out = {k: canonical(getattr(value, k)) for k in SCORE_FIELDS if hasattr(value, k)}
    for key in ('action', 'control'):
        if hasattr(value, key):
            out[key] = control(getattr(value, key))
    if hasattr(value, 'nash'):
        out['nash'] = result(value.nash)
    if hasattr(value, 'states'):
        out['state_count'] = len(value.states)
    # Retain cache behavior, not timing or all diagnostic/metadata payloads.
    metadata = getattr(value, 'metadata', {}) or {}
    out['reuse'] = canonical({k: v for k, v in metadata.items()
                              if 'nuf_reuse' in k or k == 'leader_candidate_reused'})
    return out


def classify(code):
    path = code.co_filename.replace('\\', '/').rsplit('/', 1)[-1]
    name, qual = code.co_name, code.co_qualname
    if path == 'priced_wu_link_controller.py' and name == '_evaluate_full_candidate':
        return 'leader_full'
    if path == 'area_leader_objective.py' and name == '_proxy_score_candidate':
        return 'leader_proxy'
    if path == 'stackelberg_wu_metered.py' and name == '_evaluate_fallback_candidates':
        return 'leader_pfo'
    if path == 'stackelberg_wu_metered.py' and name == 'decide_with_info':
        return 'decision'
    if name == 'solve' and path in ('local_signal_service.py', 'area_follower_objective.py',
                                   'priced_wu_link_controller.py', 'wu_faithful_follower.py'):
        return 'follower'
    if name == 'evaluate_price_point' and path in ('area_runtime.py', 'rollout_endpoint.py'):
        return 'endpoint'
    if ((path == 'area_freeway_accounting.py' and name == '_run_coupled_interval_events')
            or (path == 'coupling.py' and name == 'run_coupled_interval')):
        return 'executed_interval'
    if name.startswith('_price_worker_') and name != '_price_worker_init' and path in (
            'stackelberg_wu_metered.py', 'priced_wu_link_controller.py'):
        return 'price_task'
    if path in ('stackelberg_wu_metered.py', 'priced_wu_link_controller.py'):
        if name in ('_green_price_rollouts', '_price_batch', '_phase_price_rollouts'):
            return 'price_batch'
        if name.startswith('_global_rollout_') or name == '_global_ttt_with_phases':
            return 'price_leaf'
        if name == '_maybe_refresh_signal_prices':
            return 'price_refresh'
    if path == 'vissim_stackelberg_adapter.py' and qual.endswith(
            'install_phased_price_local.<locals>.patched'):
        return 'phase_refresh'
    return None


def _locals(frame):
    values = dict(frame.f_locals)
    # The installed outer follower is deliberately a *args/**kwargs wrapper.
    if frame.f_code.co_name == 'solve':
        for key, value in zip(('state', 'leader', 'demand', 'previous'), values.get('args', ())):
            values.setdefault(key, value)
        values.update({k: v for k, v in values.get('kwargs', {}).items() if k not in values})
    return values


def _controller_context(obj):
    if obj is None:
        return None
    follower = getattr(obj, 'nash_solver', obj)
    names = ('signal_phase_price', 'signal_phase_price_ref', 'signal_phase_price_weight',
             'signal_marginal_price', 'signal_marginal_price_ref', 'signal_marginal_price_weight',
             'metering_marginal_price', 'metering_marginal_price_ref',
             'vsl_marginal_price', 'vsl_marginal_price_ref', 'offset_marginal_price',
             'offset_marginal_price_ref', 'offset_marginal_price_weight',
             'phase_price_in_gne', 'phase_price_in_gne_rounds', 'phase_price_refine_rounds',
             '_lambda_P', '_lambda_UF', '_lambda_np', 'previous_control')
    out = {k: getattr(follower, k) for k in names if hasattr(follower, k)}
    wu = getattr(follower, '_wu', None)
    if wu is not None:
        out['wu'] = {k: v for k, v in vars(wu).items()
                     if 'lambda' in k.lower() or k.startswith('_omega') or k == 'previous_control'}
    if hasattr(obj, '_nuf_solve_cache'):
        out['nuf_cache_keys'] = list(obj._nuf_solve_cache)
    return canonical(out)


def _timing():
    return {'perf_ns': time.perf_counter_ns(), 'process_cpu_ns': time.process_time_ns(),
            'thread_cpu_ns': time.thread_time_ns(), 'thread_id': threading.get_ident()}


class Recorder:
    def __init__(self, directory, selector=classify, *, disk_backed=False):
        self.directory = Path(directory).resolve()
        if not self.directory.is_relative_to((ROOT / 'diagnostics').resolve()):
            raise ValueError('Evaluation trace output must be under diagnostics')
        self.directory.mkdir(parents=True, exist_ok=True)
        self.stem = self.directory / ('evaluation_' + str(os.getpid()))
        if self.stem.with_suffix('.json').exists() or self.stem.with_suffix('.jsonl').exists():
            raise ValueError('Evaluation trace requires a fresh output directory/process')
        self.selector, self.codes, self.frames, self.rows, self.contexts = selector, {}, {}, [], {}
        self.storage = None
        if disk_backed:
            from diagnostics.evaluation_trace_storage import Store, DiskRows, DiskMap
            self.storage = Store(self.stem.with_suffix('.sqlite'))
            self.rows = DiskRows(self.storage, 'base_rows')
            self.contexts = DiskMap(self.storage, 'base_contexts')
        self.errors, self.finished = [], False
        if disk_backed:
            from diagnostics.evaluation_trace_storage import BoundedErrors
            self.errors = BoundedErrors()
        self.stream = self.stem.with_suffix('.jsonl').open('x', encoding='utf-8', newline='\n')
        self.provenance = {'schema': 'decision-evaluation-trace/v1', 'pid': os.getpid(),
                           'parent_pid': os.getppid(), 'thread_scope': 'main thread of each process',
                           'source_files': {}, 'input_files': {}}
        manifest_path = os.environ.get('RW_EVALUATION_TRACE_MANIFEST')
        if manifest_path:
            manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
            self.provenance['launcher_manifest'] = manifest_path
            self.provenance['launcher_input_sha256'] = manifest['input_sha256']
            self.provenance['launcher_pin_contract'] = 'Parent launcher verifies these before and after the decision; workers do not redundantly hash all network files.'
        for name in json.loads(os.environ.get('RW_EVALUATION_TRACE_INPUTS_JSON', '[]')):
            path = Path(name).resolve()
            self.provenance['input_files'][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.stem.with_suffix('.started.json').write_text(_dump(self.provenance)+'\n', encoding='utf-8')

    def emit(self, row):
        row['ordinal'] = len(self.rows)
        self.rows.append(row)
        self.stream.write(_dump(self.rows.last_reference if self.storage else row) + '\n')
        self.stream.flush()

    def context(self, values):
        state = values.get('state')
        forecast = values.get('forecast', values.get('demand'))
        obj = values.get('self')
        raw = {'state': canonical(vars(state)) if hasattr(state, '__dict__') else canonical(state),
               'forecast': canonical(forecast), 'controller': _controller_context(obj)}
        cfg = getattr(obj, 'cfg', None)
        if cfg is not None:
            # Hash configuration once per logical boundary, not every physical substep.
            raw['cfg'] = canonical(cfg)
        key = digest(raw)
        self.contexts.setdefault(key, raw)
        return key

    def profile(self, frame, event, arg):
        if event not in ('call', 'return'):
            return
        code = frame.f_code
        kind = self.codes.get(code, ...)
        if kind is ...:
            kind = self.codes[code] = self.selector(code)
        if kind is None:
            return
        try:
            if event == 'call':
                self.enter(frame, kind)
            elif id(frame) in self.frames:
                self.leave(frame, arg)
        except Exception as exc:
            # Never turn an evidence serialization error into a model exception or PASS.
            self.errors.append({'kind': kind, 'event': event, 'type': type(exc).__name__,
                                'message': str(exc)})

    def enter(self, frame, kind):
        values = _locals(frame)
        parent_frame = frame.f_back
        parent = None
        while parent_frame is not None:
            candidate = self.frames.get(id(parent_frame))
            if candidate is not None:
                if candidate['kind'] == kind and kind in ('follower', 'endpoint', 'price_refresh'):
                    return  # One logical outer operation, regardless of wrapper count.
                parent = candidate
                break
            parent_frame = parent_frame.f_back
        key = len(self.rows)
        entry = {'kind': kind, 'call': key, 'parent_call': parent['call'] if parent else None}
        entry['timing'] = _timing()
        path = Path(frame.f_code.co_filename)
        if path.is_file() and str(path) not in self.provenance['source_files']:
            self.provenance['source_files'][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        entry['source'] = {'path': str(path), 'qualname': frame.f_code.co_qualname,
                           'line': frame.f_code.co_firstlineno}
        if kind == 'price_task':
            ctx = frame.f_globals.get('_PRICE_WORKER_CTX', {})
            values.update({k: ctx.get(k) for k in ('state', 'previous', 'forecast')})
            values['self'] = ctx.get('ctrl')
        if kind in ('leader_full', 'leader_proxy', 'leader_pfo', 'follower', 'price_batch',
                    'price_task', 'price_refresh', 'phase_refresh', 'decision'):
            entry['context'] = self.context(values)
        else:
            entry['context'] = parent.get('context') if parent else self.context(values)
        arguments = {}
        for name in ('index', 'stage', 'start_index', 'signal', 'pid', 'ramp', 'link', 'seg_key',
                     'value', 'offset', 'p1', 'phases', 'depth_override', 'vsl_upper', 'task',
                     'tasks', 'pts', 'incumbent_obj', 'rollout_abort_obj'):
            if name in values:
                arguments[name] = canonical(values[name])
        for name in ('action', 'leader', 'previous', 'control', 'previous_control'):
            if name in values:
                arguments[name] = control(values[name])
        if 'action_schedule' in values:
            arguments['action_schedule'] = canonical(values['action_schedule'])
        spec = values.get('objective_spec')
        if spec is not None:
            arguments['objective_spec'] = canonical({k: v for k, v in vars(spec).items()
                if k not in ('cfg', 'terminal_cost_fn') and not callable(v)})
        if 'worker' in values:
            arguments['worker'] = values['worker'].__name__
        if kind == 'executed_interval':
            # Capture the executed box-walk control after interval finalization at
            # return as well. No per-5s/10s callback or stock hash is needed.
            arguments['interval_start_sec'] = canonical(getattr(values.get('state'), 'time_sec', None))
            arguments['demand'] = canonical(values.get('demand'))
        entry['input'] = arguments
        self.frames[id(frame)] = entry
        self.emit({**entry, 'event': 'enter'})

    def leave(self, frame, arg):
        entry = self.frames.pop(id(frame))
        values = _locals(frame)
        row = {k: entry[k] for k in ('kind', 'call', 'parent_call', 'context')}
        now = _timing()
        row['timing'] = {**now, 'inclusive_wall_ns': now['perf_ns']-entry['timing']['perf_ns'],
                         'inclusive_process_cpu_ns': now['process_cpu_ns']-entry['timing']['process_cpu_ns'],
                         'inclusive_thread_cpu_ns': now['thread_cpu_ns']-entry['timing']['thread_cpu_ns']}
        row.update(event='return', result=result(arg))
        opcode = frame.f_code.co_code[frame.f_lasti] if frame.f_lasti >= 0 else 0
        row['exit'] = 'return' if dis.opname[opcode].startswith('RETURN') else 'unwind'
        if row['exit'] == 'unwind':
            self.errors.append({'kind': entry['kind'], 'event': 'unwind'})
        if entry['kind'] == 'endpoint':
            row['scored_control'] = control(values.get('control', values.get('previous')))
            row['level'] = 'logical_endpoint_outer; vendor endpoint nested below is not a second evaluation'
        if entry['kind'] in ('leader_full', 'leader_proxy', 'leader_pfo', 'executed_interval'):
            row['frame_controls_after'] = {k: control(values[k]) for k in
                ('action', 'control', 'previous', 'pfo_previous') if k in values}
        if entry['kind'] in ('price_refresh', 'phase_refresh'):
            row['prices_after'] = _controller_context(values.get('self'))
        if entry['kind'] in ('price_batch', 'price_refresh', 'phase_refresh'):
            row['serial_reruns_after'] = int(getattr(values.get('self'), 'price_parallel_serial_rerun_count', 0))
        if entry['kind'] == 'leader_full':
            row['dedupe_hits_after'] = canonical(getattr(values.get('self'), '_dedupe_hits', None))
        self.emit(row)

    def finish(self):
        from diagnostics.evaluation_trace_finalize import finish
        return finish(self)


def normalized_process(rows):
    """Renumber logical calls; strip only provenance/ordinal, never numerical values."""
    call_ids = {}
    out = []
    for row in rows:
        item = {k: v for k, v in row.items() if k not in ('source', 'ordinal', 'timing')}
        call_ids.setdefault(item['call'], len(call_ids))
        item['call'] = call_ids[item['call']]
        parent = item.get('parent_call')
        item['parent_call'] = call_ids.get(parent) if parent is not None else None
        out.append(item)
    return out


def collection(directory, *, root_pid=None, expected_child_pids=()):
    """Parent order preserved; worker scheduling/order/PID excluded from comparison."""
    from diagnostics.evaluation_trace_storage import has_disk_storage, collect
    if has_disk_storage(directory):
        return collect(directory, root_pid=root_pid, expected_child_pids=expected_child_pids, local=False)
    docs = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(Path(directory).glob('evaluation_*.json'))
            if not p.name.endswith('.started.json')]
    started = list(Path(directory).glob('evaluation_*.started.json'))
    errors = []
    if len(started) != len(docs) or not docs or any(not d['valid'] for d in docs):
        errors.append('incomplete_or_invalid_process')
    pids = {d['pid'] for d in docs}
    if len(pids) != len(docs):
        errors.append('duplicate_process_identity')
    parents = [d for d in docs if d['parent_pid'] not in pids]
    if len(parents) != 1:
        errors.append('expected_one_root_process')
    if root_pid is not None and (len(parents) != 1 or parents[0]['pid'] != root_pid):
        errors.append('root_pid_mismatch')
    missing = sorted(set(expected_child_pids)-pids)
    if missing:
        errors.append('observed_child_missing_sidecar')
    started_pids = {json.loads(p.read_text(encoding='utf-8'))['pid'] for p in started}
    if started_pids != pids:
        errors.append('started_finished_pid_sets_differ')
    worker_tasks = []
    for doc in docs:
        if doc in parents:
            continue
        roots = [r for r in doc['rows'] if r['event'] == 'enter' and r['kind'] == 'price_task']
        covered = set()
        for task in roots:
            ids = {task['call']}
            selected = []
            for row in doc['rows']:
                if row['call'] in ids or row.get('parent_call') in ids:
                    ids.add(row['call']); selected.append(row); covered.add(row['ordinal'])
            worker_tasks.append({'task_key': digest({'context': task['context'], 'input': task['input']}),
                                 'trace': normalized_process(selected)})
        if any(r['ordinal'] not in covered for r in doc['rows']):
            errors.append('unassigned_worker_record')
    compare = {'parent': parents[0]['comparison'] if len(parents) == 1 else [],
               'worker_tasks': sorted(worker_tasks, key=lambda x: (x['task_key'], digest(x['trace'])))}
    return {'valid': not errors, 'errors': errors, 'process_count': len(docs),
            'process_pids': sorted(pids), 'root_pid': parents[0]['pid'] if len(parents)==1 else None,
            'missing_observed_child_pids': missing,
            'coverage': 'leader/price/logical follower/endpoint intervals; all agent-local candidates are not yet traced',
            'worker_task_count': len(worker_tasks), 'comparison': compare,
            'comparison_sha256': digest(compare)}


def compare_collections(left, right):
    a,b=left['comparison'],right['comparison']
    first=None
    missing=object()
    for i,(x,y) in enumerate(zip_longest(a['parent'],b['parent'],fillvalue=missing)):
        if x!=y:
            first={'index':i,'left':None if x is missing else x,'right':None if y is missing else y};break
    tasks_a=[(v['task_key'],digest(v['trace'])) for v in a['worker_tasks']]
    tasks_b=[(v['task_key'],digest(v['trace'])) for v in b['worker_tasks']]
    return {'equal':left['valid'] and right['valid'] and first is None and tasks_a==tasks_b,
            'first_parent_difference':first,'worker_task_traces_equal':tasks_a==tasks_b,
            'left_parent_events':len(a['parent']),'right_parent_events':len(b['parent']),
            'left_worker_tasks':len(tasks_a),'right_worker_tasks':len(tasks_b)}


def install(directory, *, selector=classify):
    monitoring = getattr(sys, 'monitoring', None)
    monitoring_in_use = monitoring is not None and any(monitoring.get_tool(i) is not None for i in range(6))
    if (sys.getprofile() is not None or sys.gettrace() is not None or threading.getprofile() is not None
            or monitoring_in_use or os.environ.get('RW_DECISION_PROFILE_DIR') or os.environ.get('RW_PHASE_TRACE_DIR')
            or os.environ.get('RW_PHASE_COMMIT_TRACE_DIR')):
        raise RuntimeError('Evaluation trace cannot coexist with cProfile, phase trace or another profiling/tracing hook')
    recorder = Recorder(directory, selector)
    sys.setprofile(recorder.profile)
    atexit.register(recorder.finish)
    return recorder


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('directory')
    parser.add_argument('--compare')
    args = parser.parse_args()
    current = collection(args.directory)
    report = {k: v for k, v in current.items() if k != 'comparison'}
    if args.compare:
        other = collection(args.compare)
        report['other_valid'] = other['valid']
        report.update(compare_collections(current,other))
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if current['valid'] and report.get('equal', True) else 1)
