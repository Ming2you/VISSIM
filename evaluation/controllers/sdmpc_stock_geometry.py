"""Opt-in exact arithmetic hot paths in a private continuous-prediction worker.

No cohort aggregation, trajectory approximation, extra storage, state-dependent
bonus, or candidate pruning. Long ordered sums retain the same tape edges;
fixed receiving geometry is memoized outside the physical state.
"""
from array import array
from bisect import bisect_right
import builtins
import hashlib
import math
from pathlib import Path
import sys
from weakref import WeakKeyDictionary
import numpy as np
from numba import njit
from evaluation.controllers import sdmpc_tangent_reverse as ad
from evaluation.controllers.sdmpc_tangent_transport import _ordered_sum

_GEOMETRY = WeakKeyDictionary()
_ORIGINAL_BOUND = None
STATS = dict(stock_calls=0, compiled_sums=0, guarded_sums=0,
             geometry_calls=0, geometry_builds=0, repeated_time_hits=0)


@njit(cache=True, fastmath=False)
def _guarded_sum(values, kinds):
    hi = lo = total = 0.
    active = False
    for j in range(len(values)):
        x = values[j]
        if active:
            total += x
        elif kinds[j]:
            total = x+(hi+lo)
            active = True
        else:
            t = hi+x
            lo += (hi-t)+x if abs(hi) >= abs(x) else (x-t)+hi
            hi = t
    return total if active else hi+lo


def stock_sum(items):
    items = list(items)
    STATS['stock_calls'] += 1
    if len(items) < 128 or sys.version_info[:2] != (3,12):
        return builtins.sum(items)
    duals = [v for v in items if isinstance(v, ad.Dual)]
    if not duals or any(type(v) is not float and not isinstance(v, ad.Dual) for v in items):
        return builtins.sum(items)
    trace = duals[0].trace
    if any(v.trace is not trace for v in duals):
        raise ValueError('Stock sum mixed prediction tapes')
    values = np.array([v.value if isinstance(v, ad.Dual) else v for v in items], dtype=np.float64)
    if not np.isfinite(values).all() or np.max(np.abs(values)) > 1e12:
        return builtins.sum(items)
    kinds = np.array([isinstance(v, ad.Dual) for v in items], dtype=np.bool_)
    if ad.PRIMAL_GUARD:
        STATS['guarded_sums'] += 1
        return ad.Dual._result(float(_guarded_sum(values, kinds)), 0, 0, trace)
    refs = np.array([v.node if isinstance(v, ad.Dual) else 0 for v in items], dtype=np.int64)
    counters = np.zeros(4, dtype=np.int64)
    parents = np.empty((len(items),2), dtype=np.int64)
    weights = np.empty((len(items),2), dtype=np.float64)
    value, ref, active = _ordered_sum(values, refs, kinds, counters, parents, weights)
    n = int(counters[0]); start = len(trace.p1)
    if n:
        if trace.frozen:
            raise ValueError('Reverse tape changed after derivative sweep')
        mapped = np.where(parents[:n] < 0, start-parents[:n]-1, parents[:n])
        for field, column in ((trace.p1,mapped[:,0]), (trace.p2,mapped[:,1]),
                              (trace.w1,weights[:n,0]), (trace.w2,weights[:n,1])):
            data = array(field.typecode)
            data.frombytes(np.ascontiguousarray(column).tobytes())
            field.extend(data)
    STATS['compiled_sums'] += 1
    if not active:
        return float(value)
    support = 0
    for v in duals:
        if v.node: support |= v.support
    node = start-int(ref)-1 if ref < 0 else int(ref)
    return ad.Dual._result(float(value), node, support, trace)


def shared_stock(self, lane=None):
    return stock_sum(row[3] for key,q in self.queues.items()
                     if lane is None or key == lane for row in q)


def known_total(state):
    aggregate=state.known_legsplit_route_state.get('aggregate_transport')
    if aggregate is not None:return aggregate.stock()
    return stock_sum(c['vehicles'] for c in state.known_legsplit_route_state['cohorts'])


def initial_bound(self, elapsed):
    STATS['geometry_calls'] += 1
    key = (self.length, self.wave, self.spacing, self.critical, self.qmax,
           tuple(self.positions), tuple(self.points), type(self).initial_prefix)
    numbers = key[:5]+key[5]+key[6]+(elapsed,)
    if (any(type(v) not in (int,float) for v in numbers)
            or not all(math.isfinite(v) for v in numbers)
            or list(key[6]) != sorted(key[6])):
        return _ORIGINAL_BOUND(self,elapsed)
    cache = _GEOMETRY.get(self)
    if cache is None or cache['key'] != key:
        running = []
        for x in self.points:
            term = -self.initial_prefix(x)+self.critical*x
            running.append(term if not running else min(running[-1],term))
        cache = dict(key=key,prefix_min=running,last_elapsed=None,last_bound=None)
        _GEOMETRY[self] = cache
        STATS['geometry_builds'] += 1
    if cache['last_elapsed'] == elapsed:
        STATS['repeated_time_hits'] += 1
        return cache['last_bound']
    limit = min(self.length,self.wave*elapsed)
    count = bisect_right(self.points,limit)
    term = -self.initial_prefix(limit)+self.critical*limit
    minimum = min(cache['prefix_min'][count-1],term) if count else term
    result = self.qmax*elapsed+minimum
    cache.update(last_elapsed=elapsed,last_bound=result)
    return result


def install(finder,cfg,*,surrogate_mode):
    global _ORIGINAL_BOUND
    options = cfg.network.sdmpc_options
    stocks = options.get('stock_geometry_hotpath')
    if not (stocks or options.get('receiving_geometry_cache')): return
    if (finder.backend != 'reverse-v1' or surrogate_mode not in ('ad','scalar')
            or not options.get('prediction_hotpath') or not options.get('compact_audit')):
        raise ValueError('Stock/geometry hot path requires an isolated continuous reverse worker with primal checks')
    if _ORIGINAL_BOUND is not None:
        raise ValueError('Stock/geometry hot path already installed')
    from evaluation.controllers import physical_urban_transport,route_choice_corridor,lane_offramp_runtime
    from evaluation.controllers.sdmpc_tangent_audit import guard
    cls = lane_offramp_runtime.SharedSignalApproach
    _ORIGINAL_BOUND = physical_urban_transport.ReceivingEnvelope.initial_bound
    physical_urban_transport.ReceivingEnvelope.initial_bound = initial_bound
    # These functions only assert scalar conservation/storage. They return no
    # flow, change no state and own no stock cache. Keep every original check,
    # but avoid building a derivative graph used solely by an assertion.
    # A scalar worker has no tape to reduce. Leave its generator sums and
    # assertions intact instead of packing lists that cannot use the kernel.
    if surrogate_mode == 'ad' and stocks:
        cls.stock = shared_stock
        route_choice_corridor._known_total = known_total
        cls.assert_conserved = guard(cls.assert_conserved)
        cls.assert_network_mirror = guard(cls.assert_network_mirror)
    from evaluation.controllers import sdmpc_tangent_transport,sdmpc_tangent_spatial
    for module in (sys.modules[__name__],sdmpc_tangent_transport,sdmpc_tangent_spatial):
        path = Path(module.__file__).resolve()
        finder.source_hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
