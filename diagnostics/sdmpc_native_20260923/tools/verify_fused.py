r"""Roll one real taped SDMPC prediction with and without the fused Dual operators.

    verify_fused.py base  <request.pickle> <out.json>
    verify_fused.py fused <request.pickle> <out.json>
    verify_fused.py compare <base.json> <fused.json>

Each arm must run in its own fresh process (the tangent runtime refuses a process that
already imported src.models) and with PYTHONHASHSEED=0, so that any hash-ordered model
code builds its tape in the same order in both arms.

'base' disables install_fused_operations before the worker installs the stream summary,
which leaves ad.Dual's own methods -> trace.operation -> checked_operation. 'fused' uses
the code as deployed. Recorded per arm: sha256 of every tape array (p1, p2, w1, w2,
seed nodes/axes/weights), the branch counters and support masks, costs, resources, the
cost/resource/central Jacobians, the surrogate response token and the rollout time.
"""
import hashlib
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(r'D:\VISSIM-merge\sim3')


def digest(obj):
    if obj is None:
        return None
    return hashlib.sha256(np.ascontiguousarray(np.asarray(obj, dtype=np.float64)).tobytes()).hexdigest()


def roll(arm, request_path, out_path):
    import os
    if os.environ.get('PYTHONHASHSEED') != '0':
        raise SystemExit('run with PYTHONHASHSEED=0')
    sys.path[:0] = [str(ROOT), str(ROOT / 'vendor' / 'NumSim-mine')]
    from evaluation.controllers import sdmpc_tangent_runtime as runtime
    finder = runtime.install(ROOT, 'reverse-v1')
    from evaluation.controllers import sdmpc_tangent_summary as summary
    from evaluation.controllers import sdmpc_tangent_constraints as constraints
    from evaluation.controllers.sdmpc_tangent_worker import run
    if arm == 'base':
        summary.install_fused_operations = lambda: None
    captured = {}
    original = constraints.jacobian

    def capture(trace, values, workers):
        captured['trace'] = trace
        return original(trace, values, workers)
    constraints.jacobian = capture

    request = pickle.loads(Path(request_path).read_bytes())
    # The captured request pins the sources its parent saw; today's edits changed some.
    # Both arms run the same current sources, so re-pin to them -- the same thing
    # diagnostics/measure_sdmpc_pfo_decision.py does before replaying a saved request.
    pins = request['bootstrap']['runtime_sources']
    request['bootstrap']['runtime_sources'] = {
        name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in pins}
    # A taped prediction as SurrogateQuery.evaluate sends it (sdmpc_tangent_surrogate.py:216).
    # The context token then defaults to a hash of the frozen request, equal in both arms.
    request['surrogate_evaluation'] = 'ad'
    t0 = time.perf_counter()
    result = run(request, finder, {})
    wall = time.perf_counter() - t0
    trace = captured.get('trace')
    tape = {}
    if trace is not None:
        for name, dtype in (('p1', np.int64), ('p2', np.int64), ('w1', np.float64), ('w2', np.float64),
                            ('seed_nodes', np.int64), ('seed_axes', np.int64), ('seed_weights', np.float64)):
            buf = np.frombuffer(getattr(trace, name), dtype=dtype)
            tape[name] = dict(n=int(len(buf)), sha256=hashlib.sha256(buf.tobytes()).hexdigest())
        tape['counts'] = dict(trace.counts)
        tape['exact_support'] = str(trace.exact_support)
        tape['discrete_support'] = str(trace.discrete_support)
    central = result.get('central_physical') or {}
    surrogate = result.get('surrogate_prediction') or {}
    rtrace = result.get('trace') or {}
    out = dict(arm=arm, wall_sec=wall, tangent_sec=result.get('tangent_sec'),
               fused_installed=summary.ad.Dual.__add__.__name__ == 'add',
               tape=tape,
               costs=digest(result.get('costs')), resources=digest(result.get('resources')),
               cost_jacobian=digest(result.get('cost_jacobian')),
               resource_jacobian=digest(result.get('resource_jacobian')),
               central_jacobian=digest(central.get('jacobian')),
               response_token=surrogate.get('response_token'),
               exact_tie_axes=rtrace.get('exact_tie_axes'),
               discrete_dependent_axes=rtrace.get('discrete_dependent_axes'),
               event_counts=rtrace.get('event_counts'), operations=rtrace.get('operations'))
    Path(out_path).write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(dict(arm=arm, wall_sec=round(wall, 1), tangent_sec=out['tangent_sec'],
                          fused_installed=out['fused_installed'], nodes=tape.get('p1', {}).get('n'))))


def compare(a_path, b_path):
    a, b = (json.loads(Path(p).read_text()) for p in (a_path, b_path))
    if a.get('fused_installed') or not b.get('fused_installed'):
        print('WARNING: arms mislabelled -- base fused=%s, fused fused=%s'
              % (a.get('fused_installed'), b.get('fused_installed')))
    ok = True
    rows = [('tape.' + k, a['tape'].get(k), b['tape'].get(k)) for k in sorted(set(a['tape']) | set(b['tape']))]
    rows += [(k, a.get(k), b.get(k)) for k in ('costs', 'resources', 'cost_jacobian', 'resource_jacobian',
                                                'central_jacobian', 'response_token', 'exact_tie_axes',
                                                'discrete_dependent_axes', 'event_counts', 'operations')]
    for name, x, y in rows:
        same = x == y
        ok &= same
        print('  %-28s %s' % (name, 'identical' if same else 'DIFFERENT  base=%s  fused=%s' % (str(x)[:60], str(y)[:60])))
    ta, tb = a.get('tangent_sec'), b.get('tangent_sec')
    if ta and tb:
        print('\n  tangent_sec  base %.2f  fused %.2f  (%+.1f%%)' % (ta, tb, 100 * (tb / ta - 1)))
    print('\nFUSED IS BIT-IDENTICAL' if ok else '\nMISMATCH')
    return 0 if ok else 1


if __name__ == '__main__':
    if sys.argv[1] == 'compare':
        raise SystemExit(compare(sys.argv[2], sys.argv[3]))
    roll(sys.argv[1], sys.argv[2], sys.argv[3])
