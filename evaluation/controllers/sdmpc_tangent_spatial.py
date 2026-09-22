"""Independent urban receivers, with compiled local reverse tapes.

The canonical shared-head caps run in their original order. Each receiver then
owns a reserved tape span; compiled workers write private numeric arrays only.
Importing those spans preserves the order of all nonzero reverse edges, even
when head-cap operations occur between receivers. No boundary derivative is
detached and no time step is skipped. Scalar sums retain CPython's float prefix.
"""
from array import array
import math
import sys
import time

import numpy as np
from numba import njit, prange, get_num_threads, set_num_threads

STATS = dict(batches=0, receivers=0, scalar_batches=0, traced_batches=0,
             max_kernel_workers=0, reserved_nodes=0, used_nodes=0, wall_sec=0.)


@njit(cache=True, inline='always', fastmath=False)
def _constant(value):
    return value, 0, False


@njit(cache=True, inline='always', fastmath=False)
def _branch(a, b, counters, ties):
    if a[2] or b[2]:
        counters[2] += 1
        if a[0] == b[0]:
            j = counters[1]
            if j >= len(ties):
                raise ValueError('Local branch buffer exhausted')
            ties[j, 0], ties[j, 1] = a[1], b[1]
            counters[1] += 1


@njit(cache=True, inline='always', fastmath=False)
def _maximum(a, b, counters, ties):
    _branch(a, b, counters, ties)
    return b if b[0] > a[0] else a


@njit(cache=True, inline='always', fastmath=False)
def _minimum(a, b, counters, ties):
    _branch(a, b, counters, ties)
    return b if b[0] < a[0] else a


@njit(cache=True, inline='always', fastmath=False)
def _operation(value, a, wa, b, wb, counters, parents, weights):
    na = a[1] if a[2] and wa != 0. else 0
    nb = b[1] if b[2] and wb != 0. else 0
    if not na and not nb:
        return _constant(value)
    if na and not nb and wa == 1.:
        return value, na, True
    if nb and not na and wb == 1.:
        return value, nb, True
    if na == nb and wa == -wb and math.isfinite(wa):
        return _constant(value)
    j = counters[0]
    if j >= len(parents):
        raise ValueError('Local tape buffer exhausted')
    parents[j, 0], parents[j, 1] = na, nb
    weights[j, 0], weights[j, 1] = wa, wb
    counters[0] += 1
    return value, -j-1, True


@njit(cache=True, inline='always', fastmath=False)
def _add(a, b, counters, parents, weights):
    if not a[2] and b[2]:  # Dual.__radd__ calls Dual.__add__(self, other).
        return _operation(b[0]+a[0], b, 1., a, 1., counters, parents, weights)
    return _operation(a[0]+b[0], a, 1., b, 1., counters, parents, weights)


@njit(cache=True, inline='always', fastmath=False)
def _subtract(a, b, counters, parents, weights):
    if not a[2] and b[2]:
        return _operation(a[0]-b[0], b, -1., a, 1., counters, parents, weights)
    return _operation(a[0]-b[0], a, 1., b, -1., counters, parents, weights)


@njit(cache=True, inline='always', fastmath=False)
def _multiply(a, b, counters, parents, weights):
    if not a[2] and b[2]:
        return _operation(b[0]*a[0], b, a[0], a, b[0], counters, parents, weights)
    return _operation(a[0]*b[0], a, b[0], b, a[0], counters, parents, weights)


@njit(cache=True, inline='always', fastmath=False)
def _divide(a, b, counters, parents, weights):
    if not a[2] and not b[2]:
        return _constant(a[0]/b[0])
    if not a[2]:
        return _operation(a[0]/b[0], b, -a[0]/b[0]**2, a, 1./b[0], counters, parents, weights)
    return _operation(a[0]/b[0], a, 1./b[0], b, -a[0]/b[0]**2, counters, parents, weights)


@njit(cache=True, inline='always', fastmath=False)
def _value(values, refs, kinds, index):
    return values[index], refs[index], kinds[index]


@njit(cache=True, fastmath=False)
def _receiver(values, refs, kinds, nq, nf, stopline, prefix, first_dual,
              priority, rule, counters, parents, weights, ties, output, outrefs, outkinds):
    zero = _constant(0.)
    available = _maximum(zero, _value(values, refs, kinds, 0), counters, ties)
    if stopline:
        bound = _maximum(zero, _value(values, refs, kinds, 1), counters, ties)
        available = _minimum(available, bound, counters, ties)
    queued = zero
    for j in range(nq):
        item = _maximum(zero, _value(values, refs, kinds, 2+j), counters, ties)
        queued = _add(queued, item, counters, parents, weights)
    space = _maximum(zero, _subtract(available, queued, counters, parents, weights), counters, ties)
    output[0], outrefs[0], outkinds[0] = space
    # builtin sum uses compensated floating addition before the first Dual.
    # That prefix is calculated by the real builtin in the owning Python process.
    total = _constant(prefix)
    for j in range(nf):
        item = _maximum(_value(values, refs, kinds, 2+nq+j), zero, counters, ties)
        if j >= first_dual:
            total = _add(total, item, counters, parents, weights)
    _branch(total, space, counters, ties)
    free = total[0] <= space[0]
    if not free:
        _branch(total, _constant(1.e-9), counters, ties)
        free = total[0] <= 1.e-9
    share = zero
    if not free and rule == 1:
        share = _divide(space, _constant(float(max(nf, 1))), counters, parents, weights)
    remaining = space
    for k in range(nf):
        j = priority[k] if rule == 2 and not free else k
        item = _maximum(_value(values, refs, kinds, 2+nq+j), zero, counters, ties)
        if free:
            result = item
        elif rule == 1:
            result = _minimum(item, share, counters, ties)
        elif rule == 2:
            result = _minimum(item, remaining, counters, ties)
            remaining = _subtract(remaining, result, counters, parents, weights)
        else:
            result = _divide(_multiply(item, space, counters, parents, weights), total, counters, parents, weights)
        output[j+1], outrefs[j+1], outkinds[j+1] = result
    return free


@njit(cache=True, nogil=True, parallel=True, fastmath=False)
def _batch(values, refs, kinds, shapes, prefixes, first_duals, priority, rule,
           counters, parents, weights, ties, outputs, outrefs, outkinds):
    free = np.empty(len(values), dtype=np.bool_)
    for i in prange(len(values)):
        free[i] = _receiver(values[i], refs[i], kinds[i], shapes[i, 0], shapes[i, 1],
            shapes[i, 2] != 0, prefixes[i], first_duals[i], priority[i], rule,
            counters[i], parents[i], weights[i], ties[i], outputs[i], outrefs[i], outkinds[i])
    return free


def _reverse():
    return sys.modules.get('evaluation.controllers.sdmpc_tangent_reverse')


def _reserve(trace, length):
    if trace.frozen:
        raise ValueError('Spatial receiver cannot append to a frozen tape')
    start = len(trace.p1)
    for field in (trace.p1, trace.p2):
        field.extend(array('q', [0])*length)
    for field in (trace.w1, trace.w2):
        field.extend(array('d', [0.])*length)
    return start


def prepare(storage, stopline, queues, intended):
    """Freeze a receiver and reserve its original position among shared caps."""
    ad = _reverse()
    inputs = [storage, 0. if stopline is None else stopline, *queues, *intended.values()]
    duals = [item for item in inputs if ad is not None and isinstance(item, ad.Dual)]
    trace = duals[0].trace if duals else None
    if any(item.trace is not trace for item in duals):
        raise ValueError('Spatial receiver mixed reverse tapes')
    if trace is not None and ad.PRIMAL_GUARD:
        raise ValueError('A physical spatial receiver ran inside a read-only guard')
    if not all(math.isfinite(item.value if ad is not None and isinstance(item, ad.Dual) else item) for item in inputs):
        raise ValueError('Nonfinite spatial receiver input')
    # Topology-only upper bounds, not traffic parameters.
    capacity = len(queues)+4*len(intended)+16
    start = _reserve(trace, capacity) if trace is not None else 0
    keys = tuple(intended)
    first_dual, prefix = len(keys), []
    for j, item in enumerate(intended.values()):
        if ad is not None and isinstance(item, ad.Dual):
            if item.value >= 0.:
                first_dual = j
                break
            prefix.append(0.)
        else:
            prefix.append(max(item, 0.))
    return dict(inputs=inputs, nq=len(queues), nf=len(keys), stopline=stopline is not None,
        keys=keys, prefix=sum(prefix), first_dual=first_dual, trace=trace,
        start=start, capacity=capacity)


def execute(rows, rule, *, kernel_workers=None):
    """Run independent receiver blocks; commit all graph edges in source order."""
    if not rows:
        return []
    started = time.perf_counter()
    ad = _reverse()
    count, width = len(rows), max(len(row['inputs']) for row in rows)
    tape_width = max(row['capacity'] for row in rows)
    result_width = 1+max(row['nf'] for row in rows)
    values = np.zeros((count, width), dtype=np.float64)
    refs = np.zeros((count, width), dtype=np.int64)
    kinds = np.zeros((count, width), dtype=np.bool_)
    shapes = np.zeros((count, 3), dtype=np.int64)
    priority = np.zeros((count, result_width), dtype=np.int64)
    prefixes = np.empty(count, dtype=np.float64)
    first_duals = np.empty(count, dtype=np.int64)
    for i, row in enumerate(rows):
        for j, item in enumerate(row['inputs']):
            active = ad is not None and isinstance(item, ad.Dual)
            values[i, j] = item.value if active else item
            if active:
                refs[i, j], kinds[i, j] = item.node, True
        shapes[i] = row['nq'], row['nf'], row['stopline']
        prefixes[i], first_duals[i] = row['prefix'], row['first_dual']
        priority[i, :row['nf']] = sorted(range(row['nf']), key=lambda j: 0 if row['keys'][j].startswith('in_') else 1)
    counters = np.zeros((count, 3), dtype=np.int64)
    parents = np.zeros((count, tape_width, 2), dtype=np.int64)
    weights = np.zeros((count, tape_width, 2), dtype=np.float64)
    ties = np.zeros((count, tape_width*2, 2), dtype=np.int64)
    outputs = np.zeros((count, result_width), dtype=np.float64)
    outrefs = np.zeros((count, result_width), dtype=np.int64)
    outkinds = np.zeros((count, result_width), dtype=np.bool_)
    traced = any(row['trace'] is not None for row in rows)
    # Two trial derivatives can overlap two scalar witnesses and two ordinary
    # queries: 2*2 traced workers + 2 scalar + 2 ordinary = eight numerical slots.
    workers = (2 if traced else 1) if kernel_workers is None else kernel_workers
    if type(workers) is not int or workers not in (1, 2):
        raise ValueError('Spatial receiver supports one or two numerical workers')
    rule_id = 1 if rule == 'equal_split' else 2 if rule == 'main_priority' else 0
    prior = get_num_threads()
    try:
        set_num_threads(workers)
        free = _batch(values, refs, kinds, shapes, prefixes, first_duals, priority, rule_id,
            counters, parents, weights, ties, outputs, outrefs, outkinds)
    finally:
        set_num_threads(prior)
    answer = []
    for i, row in enumerate(rows):
        trace = row['trace']
        n, nties, comparisons = map(int, counters[i])
        if n > row['capacity']:
            raise ValueError('Spatial receiver exceeded its reserved tape span')
        supports = {0: 0}
        for item in row['inputs']:
            if ad is not None and isinstance(item, ad.Dual):
                supports[item.node] = item.support
        def resolve(ref):
            return row['start']-int(ref)-1 if ref < 0 else int(ref)
        if trace is not None:
            mapped = np.where(parents[i, :n] < 0, row['start']-parents[i, :n]-1, parents[i, :n])
            for field, column in ((trace.p1, mapped[:, 0]), (trace.p2, mapped[:, 1]),
                                  (trace.w1, weights[i, :n, 0]), (trace.w2, weights[i, :n, 1])):
                data = array(field.typecode)
                data.frombytes(np.ascontiguousarray(column).tobytes())
                field[row['start']:row['start']+n] = data
            for j, (a, b) in enumerate(mapped):
                supports[row['start']+j] = supports[int(a)] | supports[int(b)]
            trace.counts['primal_comparisons'] += comparisons
            trace.counts['exact_primal_ties'] += nties
            for a, b in ties[i, :nties]:
                trace.exact_support |= supports[resolve(a)] | supports[resolve(b)]
        def restore(j):
            value = float(outputs[i, j])
            if not outkinds[i, j]:
                return value
            node = resolve(outrefs[i, j])
            return ad.Dual._result(value, node, supports[node], trace)
        order = (priority[i, :row['nf']] if rule_id == 2 and not free[i]
                 else range(row['nf']))
        answer.append((restore(0), {row['keys'][j]: restore(j+1) for j in order}))
        STATS['reserved_nodes'] += row['capacity'] if trace is not None else 0
        STATS['used_nodes'] += n
    STATS['batches'] += 1
    STATS['receivers'] += count
    STATS['traced_batches' if traced else 'scalar_batches'] += 1
    STATS['max_kernel_workers'] = max(STATS['max_kernel_workers'], workers)
    STATS['wall_sec'] += time.perf_counter()-started
    return answer


def regular_receivers(state, cfg, groups, step, head_context, uqm):
    from evaluation.controllers import head_service_resources
    from evaluation.controllers.route_choice_corridor import limit_intended_batch
    origins = uqm._origin_storage_movements(cfg)
    rows, identities = [], []
    for link, intended in groups.items():
        if getattr(cfg.network, 'route_choice_corridor', None):
            intended = limit_intended_batch(state, cfg, intended, step)
        intended = head_service_resources.regular_batch(cfg, intended, head_context)
        rows.append(prepare(state.urban_link_storage.get(link, 0.),
            cfg.network.urban_stopline_storage_veh.get(link),
            [state.urban_movement_queue.get(m, 0.) for m in origins.get(link, ())], intended))
        identities.append((link, intended))
    results = execute(rows, cfg.urban_follower.receiving_space_rule)
    return [(link, intended, space, accepted)
            for (link, intended), (space, accepted) in zip(identities, results)]
