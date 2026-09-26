"""Continuous common-anchor forward sensitivities and native execution checks.

The current NP/actual-merge NUF definitions and native execution gate are kept.
No source in vendor is edited; instrumentation is confined to a child process.
"""
from __future__ import annotations

import copy
import hashlib
import os
import pickle
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np


def prepare_request(follower, state, forecast, reference, action, coord, bootstrap):
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    if not bootstrap:
        raise ValueError('Tangent prediction requires the canonical worker bootstrap')
    runtime = {k: v for k, v in vars(adapter).items()
               if k.startswith('_') and k.isupper() and isinstance(v, (dict, list, set))}
    memo = {id(follower): follower}
    bound = getattr(adapter, '_PHASE_VECTOR_FOLLOWER', {}).get('ref')
    if bound is not None:
        memo[id(bound)] = follower
    runtime = copy.deepcopy(runtime, memo)
    runtime.setdefault('_PHASE_VECTOR_FOLLOWER', {})['ref'] = None
    return dict(owned=(follower, state, reference, forecast), runtime=runtime,
        action=action, axes=coord.axes, green_vectors=coord.green_vectors,
        horizon=follower.cfg.mpc.horizon_steps, bootstrap=bootstrap,
        costs_order=(*coord.owners, 'PASSIVE_OMEGA'))


def _worker_failure(process, limit=6000):
    """A failed worker's exit status and stderr, keeping both its head and its tail."""
    text = process.stderr or ''
    if len(text) > limit:
        head = limit//3
        text = f'{text[:head]}\n[... {len(text)-limit} characters omitted ...]\n{text[head-limit:]}'
    return f'returncode={process.returncode}, stderr:\n{text}'


def _evaluate_single(request):
    """A missing/unsupported derivative is an error, never an implicit zero."""
    root = Path(__file__).resolve().parents[2]
    worker = Path(__file__).with_name('sdmpc_tangent_worker.py')
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='sdmpc-tangent-') as tmp:
        request_path, result_path = Path(tmp)/'request.pickle', Path(tmp)/'result.pickle'
        data = pickle.dumps(request, protocol=5)
        request_path.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        env = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
        backend = (request['owned'][0].cfg.network.sdmpc_options.get('tangent_backend', 'forward')
                   if 'owned' in request else request.get('worker_backend', 'forward'))
        # A private process owns its model hooks. It has no VISSIM entry point.
        process = subprocess.run([sys.executable, '-B', str(worker), str(request_path),
            str(result_path), digest, backend], cwd=root, env=env, capture_output=True, text=True)
        if not result_path.is_file():
            raise RuntimeError('Tangent worker failed: '+_worker_failure(process))
        try:
            result = pickle.loads(result_path.read_bytes())
        except Exception as exc:  # e.g. a worker killed while writing its result
            raise RuntimeError(f'Tangent worker failed: unreadable result ({type(exc).__name__}: {exc}); '
                               +_worker_failure(process)) from exc
        if result.get('request_sha256') != digest:
            raise ValueError('Tangent worker response identity mismatch')
        if process.returncode or 'error' in result:
            raise RuntimeError('Tangent prediction failed:\n'+result.get('error', _worker_failure(process)))
    result['wall_sec_including_spawn'] = time.perf_counter()-started
    return result


def merge_columns(results, partitions, axis_count, tolerance):
    """Assemble complete Jacobian columns from the identical numeric anchor."""
    if len(results) != len(partitions) or not results:
        raise ValueError('Missing derivative worker results')
    flat = [j for part in partitions for j in part]
    if sorted(flat) != list(range(axis_count)):
        raise ValueError('Duplicate or missing derivative columns')
    first = results[0]
    gradients = np.empty((len(first['costs']),axis_count))
    resources = np.empty((len(first['resources']),axis_count))
    sources = {}
    for result, part in zip(results,partitions):
        if (result.get('column_indices') != part or 'error' in result
                or not result.get('complete_primal_state_match')
                or not np.isfinite(result['max_primal_state_error'])
                or result['max_primal_state_error'] < 0
                or result['max_primal_state_error'] > tolerance
                or result['ad_axes'] != part or result['fallback_reasons']):
            raise ValueError('Unqualified derivative column block')
        for key in ('costs','resources'):
            a,b = np.asarray(result[key]),np.asarray(first[key])
            if a.shape != b.shape or not np.isfinite(a).all() or np.max(abs(a-b)) > tolerance:
                raise ValueError('Derivative workers used different primal anchors: '+key)
        for key,output in (('cost_jacobian',gradients),('resource_jacobian',resources)):
            values = np.asarray(result[key])
            if values.shape != (len(output),len(part)) or not np.isfinite(values).all():
                raise ValueError('Invalid derivative column matrix: '+key)
            output[:,part] = values
        for path,digest in result['transformed_source_sha256'].items():
            if path in sources and sources[path] != digest:
                raise ValueError('Derivative workers used different model sources')
            sources[path] = digest
    combined = dict(first, cost_jacobian=gradients.tolist(), resource_jacobian=resources.tolist(),
        active_axes=list(range(axis_count)),ad_axes=list(range(axis_count)),
        scalar_rollouts=len(results),tangent_rollouts=len(results),
        scalar_sec=sum(r['scalar_sec'] for r in results),
        tangent_sec=sum(r['tangent_sec'] for r in results),
        max_primal_state_error=max(r['max_primal_state_error'] for r in results),
        transformed_source_sha256=sources)
    combined.pop('column_indices',None)
    combined.pop('request_sha256',None)
    combined['trace'] = {'scope':'Per-worker traces; primal work is duplicated',
                         'workers':[r['trace'] for r in results]}
    return combined


def evaluate(request):
    workers = request['owned'][0].cfg.network.sdmpc_options.get('derivative_workers',1)
    if type(workers) is not int or not 1 <= workers <= 8:
        raise ValueError('Invalid derivative worker count')
    if request['owned'][0].cfg.network.sdmpc_options.get('surrogate_reuse'):
        return _evaluate_single(dict(request, surrogate_evaluation='ad'))
    if request['owned'][0].cfg.network.sdmpc_options.get('tangent_backend') == 'reverse-v1':
        if request['owned'][0].cfg.network.sdmpc_options.get('tangent_concurrent_primal'):
            from evaluation.controllers.sdmpc_tangent_concurrent import evaluate as concurrent
            return concurrent(request)
        return _evaluate_single(request)
    if workers == 1:
        return _evaluate_single(request)
    if request['owned'][0].cfg.network.sdmpc_options.get('tangent_shared_primal', False):
        return _evaluate_shared(request, workers)
    from concurrent.futures import ThreadPoolExecutor
    n = len(request['axes'])
    if not n:raise ValueError('No derivative columns')
    workers = min(workers,n)
    partitions = [list(range(k,n,workers)) for k in range(workers)]
    common = pickle.dumps(request,protocol=5)
    requests=[]
    for k,indices in enumerate(partitions):
        # Byte-identical common state/control/forecast; only seeds differ.
        child = pickle.loads(common)
        child['column_indices'] = indices
        child.pop('diagnostic_checkpoint',None)
        requests.append(child)
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(_evaluate_single,requests))
    tolerance = request['owned'][0].cfg.network.sdmpc_options['tangent_primal_abs_tolerance']
    combined = merge_columns(results,partitions,n,tolerance)
    combined['wall_sec_including_spawn'] = time.perf_counter()-started
    combined['parallel_derivatives'] = dict(workers=workers,columns=partitions,
        common_request_sha256=hashlib.sha256(common).hexdigest(),
        wall_sec=combined['wall_sec_including_spawn'],
        timing_scope='scalar_sec/tangent_sec are worker sums, not elapsed time',
        worker_times=[{k:r[k] for k in ('scalar_sec','tangent_sec','wall_sec_including_spawn')}
                      for r in results])
    return combined


def _evaluate_shared(request, workers):
    """One scalar witness, then at most eight isolated column propagations.

    Children load the same hashed request bytes, not independently serialized
    object graphs. The scalar states stay in a parent-owned temporary file;
    every worker verifies that witness and compares its full trajectory to it.
    """
    from concurrent.futures import ThreadPoolExecutor
    started = time.perf_counter()
    n = len(request['axes'])
    if not n:
        raise ValueError('No derivative columns')
    workers = min(workers, n)
    partitions = [list(range(k, n, workers)) for k in range(workers)]
    common = pickle.dumps(request, protocol=5)
    digest = hashlib.sha256(common).hexdigest()
    with tempfile.TemporaryDirectory(prefix='sdmpc-primal-') as tmp:
        path = Path(tmp)/'common.pickle'
        path.write_bytes(common)
        descriptor = dict(path=str(path), sha256=digest)
        witness_path = Path(tmp)/'scalar.pickle'
        baseline = _evaluate_single(dict(shared_request=descriptor,
            scalar_output=str(witness_path)))
        witness = baseline['shared_primal']
        if witness['anchor_sha256'] != digest or witness['path'] != str(witness_path):
            raise ValueError('Scalar witness used another derivative anchor')
        jobs = [dict(shared_request=descriptor, shared_primal=witness,
                     column_indices=part) for part in partitions]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_evaluate_single, jobs))
        for result in results:
            if result.get('shared_primal') != witness:
                raise ValueError('Derivative worker used another scalar witness')
        tolerance = request['owned'][0].cfg.network.sdmpc_options['tangent_primal_abs_tolerance']
        combined = merge_columns(results, partitions, n, tolerance)
    combined.update(scalar_rollouts=1, scalar_sec=baseline['scalar_sec'])
    combined['wall_sec_including_spawn'] = time.perf_counter()-started
    combined['parallel_derivatives'] = dict(workers=workers, columns=partitions,
        common_request_sha256=digest, scalar_rollouts=1,
        scalar_worker={k: baseline[k] for k in
            ('scalar_sec', 'scalar_export_sec', 'wall_sec_including_spawn')},
        wall_sec=combined['wall_sec_including_spawn'],
        timing_scope='One serial scalar witness; tangent_sec is worker sum; wall_sec is elapsed',
        worker_times=[{k: r[k] for k in ('scalar_sec', 'scalar_load_sec', 'tangent_sec',
            'state_check_sec', 'wall_sec_including_spawn')} for r in results])
    combined['trace']['scope'] = 'Per-worker traces; one shared scalar witness'
    return combined


def checked_matrices(result, costs, resources, axes, tolerance, *, allow_surrogate=False):
    """Use the continuous Jacobian with an exact-anchor value correction.

    The relaxation's cost/resource values may differ from integer execution.
    Record that difference rather than claim primal equality to the native model.
    Local residuals keep the exact executed-model anchor; proposals are checked
    in that model by the existing nonlinear feasibility/line-search gate.
    """
    n = len(axes)
    grad = np.asarray(result['cost_jacobian'], dtype=float)
    matrix = np.asarray(result['resource_jacobian'], dtype=float)
    if grad.shape != (len(costs), n) or matrix.shape != (len(resources), n):
        raise ValueError('Tangent matrix shape mismatch')
    for name, expected in (('costs', costs), ('resources', resources)):
        got = np.asarray(result[name], dtype=float)
        if got.shape != np.shape(expected) or not np.isfinite(got).all():
            raise ValueError('Nonfinite or malformed continuous primal: '+name)
        result['exact_anchor_'+name] = np.asarray(expected).tolist()
        result['anchor_correction_'+name] = (expected-got).tolist()
    if not np.isfinite(grad).all() or not np.isfinite(matrix).all():
        raise ValueError('Nonfinite tangent matrix')
    fallback = {int(j): reason for j, reason in result['fallback_reasons'].items()}
    if any(j < 0 or j >= n for j in fallback):
        raise ValueError('Tangent fallback axis outside coordinates')
    if result.get('surrogate_evaluation') == 'ad':
        from evaluation.controllers.sdmpc_tangent_surrogate import MODEL
        if (not allow_surrogate or result.get('primal_audit_performed') is not False
                or result.get('complete_primal_state_match') is not False
                or result.get('max_primal_state_error') is not None
                or result.get('surrogate_prediction', {}).get('prediction_model') != MODEL
                or any(np.max(np.abs(result['anchor_correction_'+name]), initial=0.) > tolerance
                       for name in ('costs', 'resources'))):
            raise ValueError('Surrogate Jacobian needs the same continuous candidate anchor')
    elif (not result['complete_primal_state_match']
          or result['max_primal_state_error'] > tolerance):
        raise ValueError('Tangent did not reproduce the complete scalar state')
    return grad, matrix, fallback
