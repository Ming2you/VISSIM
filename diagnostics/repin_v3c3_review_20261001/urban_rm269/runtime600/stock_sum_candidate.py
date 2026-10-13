"""Prototype: the existing ordered sum kernel for long stock-only reads.

No cohort is merged or dropped. Every input retains its value and reverse node.
The original node order and weights are appended in contiguous arrays, avoiding
one Python Dual object and four Python append calls per intermediate addition.
Not installed in production or the active benchmark.
"""
from array import array
import builtins
import sys
import numpy as np
from numba import njit
from evaluation.controllers import sdmpc_tangent_reverse as ad
from evaluation.controllers.sdmpc_tangent_transport import _ordered_sum


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
        return ad.Dual._result(float(_guarded_sum(values, kinds)), 0, 0, trace)
    refs = np.array([v.node if isinstance(v, ad.Dual) else 0 for v in items], dtype=np.int64)
    counters = np.zeros(4, dtype=np.int64)
    parents = np.empty((len(items),2), dtype=np.int64)
    weights = np.empty((len(items),2), dtype=np.float64)
    value, ref, active = _ordered_sum(values, refs, kinds, counters, parents, weights)
    n = int(counters[0])
    start = len(trace.p1)
    if n:
        if trace.frozen:
            raise ValueError('Reverse tape changed after derivative sweep')
        mapped = np.where(parents[:n] < 0, start-parents[:n]-1, parents[:n])
        for field, column in ((trace.p1,mapped[:,0]), (trace.p2,mapped[:,1]),
                              (trace.w1,weights[:n,0]), (trace.w2,weights[:n,1])):
            data = array(field.typecode)
            data.frombytes(np.ascontiguousarray(column).tobytes())
            field.extend(data)
    if not active:
        return float(value)
    support = 0
    for v in duals:
        if v.node:
            support |= v.support
    node = start-int(ref)-1 if ref < 0 else int(ref)
    return ad.Dual._result(float(value), node, support, trace)


def shared_stock(self, lane=None):
    return stock_sum(row[3] for key,q in self.queues.items()
                     if lane is None or key == lane for row in q)


def known_total(state):
    return stock_sum(c['vehicles'] for c in state.known_legsplit_route_state['cohorts'])
