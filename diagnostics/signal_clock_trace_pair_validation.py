"""Validate completed clock trace certificates without loading trace rows/DBs.

This is separate from normal timing and returned-action comparison. The sole
source exception is the reviewed original -> cached clock, in that direction;
all current bytes must match the second (cached) execution. Failure raises
ValueError; success returns a compact certificate with passed=True.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CLOCK = 'evaluation/controllers/signal_actuation_contract.py'
CLOCK_SHA = (
    '8a470f7083fb3452756cd39573a690cc164989a079cd66eb10e1279f0a8f4c1f',
    '9581813d96fb27a7275ba41766763bd0bf123a200fb15b8cec8bf42e484227b5',
)
REQUIRED_TRACERS = {
    'diagnostics/'+name for name in (
        'evaluation_trace.py', 'evaluation_trace_local.py', 'evaluation_trace_monitor.py',
        'evaluation_trace_finalize.py', 'evaluation_trace_state.py', 'evaluation_trace_storage.py',
        'evaluation_trace_bootstrap/sitecustomize.py', 'decision_profile.py',
        'run_area_production_preflight.py',
    )
}
OUTPUT_ENV = ('RW_EVALUATION_TRACE_DIR', 'RW_EVALUATION_TRACE_MANIFEST')
OTHER_ENV = ('RW_DECISION_PROFILE_DIR', 'RW_PHASE_COMMIT_TRACE_DIR', 'RW_PHASE_TRACE_DIR',
             'RW_DECISION_RESOURCE_DIR', 'RW_EVALUATION_TRACE_INPUTS_JSON')
OTHER_MODES = ('read_only_phase_trace', 'read_only_process_profile', 'normal_process_counters',
               'process_profile_validation', 'normal_resource_validation')


def _require(condition, message):
    if not condition: raise ValueError(message)


def _sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _digest(value):
    _require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None,
             'Missing or invalid SHA256')
    return value


def _relative(value):
    _require(isinstance(value, str) and value, 'Missing evidence path')
    path = (ROOT/value).resolve()
    _require(path.is_relative_to(ROOT.resolve()), 'Evidence path escapes workspace')
    return path.relative_to(ROOT.resolve()).as_posix()


def _pins(value):
    _require(isinstance(value, dict) and value, 'Missing evidence pin map')
    result = {_relative(path): _digest(key) for path, key in value.items()}
    _require(len(result) == len(value), 'Duplicate normalized evidence path')
    return result


def _argument(command, flag):
    _require(command.count(flag) == 1, 'Expected one command argument: '+flag)
    index = command.index(flag)+1
    _require(index < len(command), 'Missing command argument value: '+flag)
    return command[index]


def validate_trace_pair(left_folder, right_folder):
    """Consume preflight certificates only; never recollect raw trace data."""
    folders = [Path(path).resolve() for path in (left_folder, right_folder)]
    _require(folders[0] != folders[1], 'Two distinct execution folders required')
    for folder in folders:
        _require(folder.is_relative_to(ROOT/'diagnostics/area_production_preflight'),
                 'Execution folder escapes preflight output directory')
    paths = [folder/'manifest.json' for folder in folders]
    manifest_bytes = [path.read_bytes() for path in paths]
    manifests = [json.loads(raw) for raw in manifest_bytes]
    manifest_shas = [hashlib.sha256(raw).hexdigest() for raw in manifest_bytes]
    expected_current = {}

    def current_pin(relative, key):
        previous = expected_current.setdefault(relative, key)
        _require(previous == key, 'Conflicting current evidence pins: '+relative)

    sources, inputs, traces, environments, executables, tracers = [], [], [], [], [], []
    for side, (folder, manifest) in enumerate(zip(folders, manifests)):
        _require(all(manifest.get(key) is True for key in ('valid', 'source_unchanged', 'inputs_unchanged')),
                 'Preflight was not completed with unchanged source/input')
        _require(type(manifest.get('exit_code')) is int and manifest['exit_code'] == 0
                 and manifest.get('surviving_worker_pids') == [] and not manifest.get('timed_out', False),
                 'Preflight failed, timed out, or retained workers')
        _require(not any(key in manifest for key in OTHER_MODES), 'Competing diagnostic mode recorded')
        trace = manifest.get('evaluation_trace_validation', {})
        _require(trace.get('valid') is True and trace.get('errors') == []
                 and trace.get('trace_sources_unchanged') is True, 'Invalid or changed trace certificate')
        _require(trace.get('missing_observed_child_pids') == [], 'Missing observed child trace')
        pid = manifest.get('adapter_pid')
        pids = trace.get('process_pids')
        _require(type(pid) is int and pid > 0 and trace.get('root_pid') == pid,
                 'Trace root differs from actual adapter PID')
        _require(isinstance(pids, list) and all(type(p) is int and p > 0 for p in pids)
                 and len(pids) == len(set(pids)) and pid in pids
                 and type(trace.get('process_count')) is int and trace['process_count'] == len(pids),
                 'Invalid trace process inventory')
        workers = manifest.get('observed_worker_processes')
        _require(isinstance(workers, list), 'Missing observed worker inventory')
        worker_pids = [worker.get('pid') for worker in workers]
        _require(all(type(p) is int and p > 0 for p in worker_pids)
                 and len(worker_pids) == len(set(worker_pids)) and set(worker_pids) <= set(pids),
                 'Observed worker has no completed trace')
        _require(type(trace.get('worker_task_count')) is int and trace['worker_task_count'] > 0,
                 'Expected positive completed price task count')
        for key in ('comparison_sha256', 'v1_comparison_sha256'): _digest(trace.get(key))
        contracts = trace.get('identity_contracts')
        _require(isinstance(contracts, list) and contracts and all(isinstance(x, str) and x for x in contracts)
                 and len(contracts) == len(set(contracts)) and 'legacy v2 raw phase demand address' not in contracts,
                 'Missing normalized local identity contract')
        traces.append(trace)

        env = manifest.get('environment', {})
        _require(env.get('RW_EVALUATION_TRACE_BACKEND') == 'monitor'
                 and env.get('RW_EVALUATION_TRACE_LOCALS') == '1', 'Full local monitor trace required')
        _require(not any(key in env for key in OTHER_ENV), 'Competing trace environment')
        _require(env.get('PYTHONPATH'), 'Missing recorded PYTHONPATH')
        py_paths = [Path(p).resolve() for p in env['PYTHONPATH'].split(os.pathsep) if p]
        _require(ROOT.resolve() in py_paths and (ROOT/'diagnostics/evaluation_trace_bootstrap').resolve() in py_paths,
                 'Trace bootstrap not on recorded PYTHONPATH')
        _require(not any(p.name in ('phase_trace_bootstrap', 'decision_profile_bootstrap', 'decision_resource_bootstrap')
                         for p in py_paths), 'Competing bootstrap on PYTHONPATH')
        for key, target in zip(OUTPUT_ENV, (folder/'evaluation_trace', folder/'manifest.json')):
            _require(isinstance(env.get(key), str) and Path(env[key]).resolve() == target,
                     'Trace output environment points at another execution: '+key)
        seed = manifest.get('python_hash_seed', {})
        _require(seed.get('explicit_cli') is True and isinstance(seed.get('adapter_and_workers'), str)
                 and seed['adapter_and_workers'].isdigit(), 'Explicit adapter/worker hash seed required')
        environments.append({**{key: value for key, value in env.items() if key not in OUTPUT_ENV},
                             'PYTHONHASHSEED': seed['adapter_and_workers']})
        command = manifest.get('command')
        _require(isinstance(command, list) and command and all(isinstance(x, str) for x in command),
                 'Missing actual adapter command')
        executables.append(str(Path(command[0]).resolve()))
        _require(Path(executables[-1]).is_file(), 'Recorded Python executable is missing')
        for flag, name in (('--out-action-json', 'action.json'), ('--out-action-csv', 'action.csv')):
            _require(Path(_argument(command, flag)).resolve() == folder/name, 'Command output belongs to another execution')

        source = _pins(manifest.get('source_sha256'))
        _require(source.get(CLOCK) == CLOCK_SHA[side], 'Clock source direction/pin differs from reviewed pair')
        for path, key in source.items(): current_pin(path, CLOCK_SHA[1] if path == CLOCK else key)
        sources.append(source)
        tracer = _pins(manifest.get('read_only_evaluation_trace'))
        _require(REQUIRED_TRACERS <= tracer.keys(), 'Missing required tracer source pin')
        for path, key in tracer.items(): current_pin(path, key)
        tracers.append(tracer)
        raw_inputs = _pins(manifest.get('input_sha256'))
        tuning = _relative(_argument(command, '--tuning-json'))
        _require(tuning in raw_inputs and manifest.get('config_sha256') == raw_inputs[tuning], 'Config input pin mismatch')
        logical_inputs = {}
        for path, key in raw_inputs.items():
            if path == CLOCK:
                _require(key == CLOCK_SHA[side], 'Clock input/source pin mismatch')
                key = CLOCK_SHA[1]
            current_pin(path, key)
            logical_inputs['<same-byte-tuning-json>' if path == tuning else path] = key
        for flag in ('--state-json', '--mapping-json', '--detector-mapping-json', '--calibration-json'):
            _require(_relative(_argument(command, flag)) in raw_inputs, 'Unpinned command input: '+flag)
        _require(_relative(_argument(command, '--state-json')) == _relative(manifest['recorded_snapshot']),
                 'Command state differs from recorded snapshot')
        if '--previous-action-json' in command:
            _require(_relative(_argument(command, '--previous-action-json')) in raw_inputs, 'Unpinned previous action')
        inputs.append(logical_inputs)

    _require(set(sources[0]) == set(sources[1])
             and [path for path in sources[0] if sources[0][path] != sources[1][path]] == [CLOCK],
             'Source delta is not exactly the reviewed clock')
    _require(inputs[0] == inputs[1], 'Paired input bytes differ')
    _require(tracers[0] == tracers[1], 'Tracer source pins differ')
    _require(environments[0] == environments[1] and executables[0] == executables[1], 'Trace execution environments differ')
    for key in ('recorded_run', 'recorded_sim_sec', 'recorded_snapshot'):
        _require(key in manifests[0] and manifests[0][key] == manifests[1].get(key), 'Recorded execution input differs: '+key)
    for key in ('comparison_sha256', 'v1_comparison_sha256', 'identity_contracts', 'process_count', 'worker_task_count'):
        _require(traces[0][key] == traces[1][key], 'Trace pair differs: '+key)
    for path, key in expected_current.items():
        _require(_sha(ROOT/path) == key, 'Evidence changed after execution: '+path)
    _require([_sha(path) for path in paths] == manifest_shas, 'Preflight manifest changed during validation')
    return {
        'schema': 'signal-clock-trace-pair/v1', 'passed': True,
        'manifest_paths': [str(path.relative_to(ROOT)) for path in paths], 'manifest_sha256': manifest_shas,
        **{key: traces[0][key] for key in ('comparison_sha256', 'v1_comparison_sha256',
                                         'identity_contracts', 'process_count', 'worker_task_count')},
        'tracer_source_count': len(tracers[0]), 'rechecked_source_input_files': len(expected_current),
        'python_executable': executables[0], 'environment': environments[0],
        'source_delta': {'path': CLOCK, 'before': CLOCK_SHA[0], 'after': CLOCK_SHA[1]},
        'producer_sha256': _sha(Path(__file__)),
        'scope': 'Completed preflight certificates and current pinned bytes only; raw trace DBs are not recollected. '
                 'Returned JSON/CSV preservation and normal timing remain separate checks.',
    }
