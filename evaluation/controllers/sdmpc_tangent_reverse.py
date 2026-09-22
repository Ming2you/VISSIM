"""Active-branch reverse AD: one traffic trajectory, compiled output sweeps.

The primal operations and branch selections match sdmpc_dual. A compact tape
stores local derivatives, not a sparse dictionary at every arithmetic scalar.
No finite differences, quantization changes, or numerical fastmath are used.
"""
from array import array
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import builtins
import math
import time
import uuid
import weakref
import numpy as np
from evaluation.controllers import sdmpc_dual as forward

_TRACES = weakref.WeakValueDictionary()


def primal(value):
    return value.value if isinstance(value, forward.Dual) else float(value)


def derivative(value):
    if not isinstance(value, Dual):
        return {}
    if value.tangent is None:
        raise TypeError('Reverse intermediates require a compiled output sweep')
    return value.tangent


def float_keep(value=0.):
    return value if isinstance(value, Dual) else float(value)


def _restore_scalar(trace_id, node, value, support, seed):
    trace = _TRACES.get(trace_id)
    if trace is None:
        raise ValueError('Reverse audit references a tape outside its owning process')
    return Dual._result(value, node, support, trace, seed)


def _reverse_row(p1, p2, w1, w2, output, seed_nodes, seed_axes, seed_weights, n_axes):
    adjoint = np.zeros(len(p1), dtype=np.float64)
    correction = np.zeros(len(p1), dtype=np.float64)
    if output:
        adjoint[output] = 1.
    for i in range(len(p1)-1, 0, -1):
        value = adjoint[i]+correction[i]
        if value != 0.:
            for edge in range(2):
                parent = p1[i] if edge == 0 else p2[i]
                weight = w1[i] if edge == 0 else w2[i]
                if parent:
                    term = value*weight
                    old = adjoint[parent]
                    total = old+term
                    correction[parent] += ((old-total)+term if abs(old) >= abs(term) else (term-total)+old)
                    adjoint[parent] = total
    result = np.zeros(n_axes, dtype=np.float64)
    result_correction = np.zeros(n_axes, dtype=np.float64)
    for i in range(len(seed_nodes)):
        axis, node = seed_axes[i], seed_nodes[i]
        term = (adjoint[node]+correction[node])*seed_weights[i]
        old = result[axis]
        total = old+term
        result_correction[axis] += ((old-total)+term if abs(old) >= abs(term) else (term-total)+old)
        result[axis] = total
    return result+result_correction


_COMPILED = None
FAST_PRIMITIVES = False
DIRECT_SUM_NODES = False
PRIMAL_GUARD = False


class Trace:
    def __init__(self, steps, *, track_stencils=False):
        if track_stencils:
            raise ValueError('Reverse backend supports active-branch derivatives only')
        self.track_stencils = False
        self.steps = dict(enumerate(steps))
        self.p1, self.p2 = array('q', [0]), array('q', [0])
        self.w1, self.w2 = array('d', [0.]), array('d', [0.])
        self.seed_nodes, self.seed_axes, self.seed_weights = array('q'), array('q'), array('d')
        self.counts = Counter()
        self.exact_support = self.discrete_support = 0
        self.frozen = False
        self.identity = uuid.uuid4().hex
        _TRACES[self.identity] = self
        self.backward_receipt = None

    def node(self, a=0, b=0, wa=0., wb=0.):
        if self.frozen:
            raise ValueError('Reverse tape changed after derivative sweep')
        node = len(self.p1)
        self.p1.append(a); self.p2.append(b)
        self.w1.append(wa); self.w2.append(wb)
        return node

    def operation(self, value, a, wa, b=None, wb=0.):
        if isinstance(a, Dual) and a.trace is not self or isinstance(b, Dual) and b.trace is not self:
            raise ValueError('Reverse arithmetic mixed prediction tapes')
        if PRIMAL_GUARD:
            # Preserve AD numeric dispatch (including Python sum's addition
            # order), but do not build edges for a read-only assertion.
            return Dual._result(value, 0, 0, self)
        na = a.node if isinstance(a, Dual) and wa != 0. else 0
        nb = b.node if isinstance(b, Dual) and wb != 0. else 0
        if not na and not nb:
            return float(value)
        if na and not nb and wa == 1.:
            return Dual._result(value, na, a.support, self)
        if nb and not na and wb == 1.:
            return Dual._result(value, nb, b.support, self)
        if na == nb and wa == -wb and math.isfinite(wa):
            return float(value)
        support = a.support if na else b.support
        if na and nb and support != b.support:
            support |= b.support
        return Dual._result(value, self.node(na, nb, wa, wb), support, self)

    def branch(self, a, b, *, discrete=False, output_connected=False):
        if PRIMAL_GUARD:
            return (0, 0)
        self.counts['primal_comparisons'] += 1
        support = (a.support if isinstance(a, Dual) else 0) | (b.support if isinstance(b, Dual) else 0)
        if primal(a) == primal(b):
            self.counts['exact_primal_ties'] += 1
            self.exact_support |= support
        if discrete:
            self.counts['discrete_comparisons'] += 1
            self.discrete_support |= support
        return (0, 0)

    def jacobian(self, outputs, workers=8):
        global _COMPILED
        if type(workers) is not int or not 1 <= workers <= 8:
            raise ValueError('Reverse sweep requires 1..8 workers')
        if any(isinstance(v, Dual) and v.trace is not self for v in outputs):
            raise ValueError('Output belongs to another reverse tape')
        self.frozen = True
        started = time.perf_counter()
        try:
            import numba
        except ImportError as exc:
            raise ImportError('reverse-v1 requires the pinned Numba dependency on PYTHONPATH') from exc
        if _COMPILED is None:
            _COMPILED = numba.njit(cache=True, nogil=True, fastmath=False)(_reverse_row)
        vectors = tuple(np.frombuffer(v, dtype=dtype) for v, dtype in
            ((self.p1, np.int64), (self.p2, np.int64), (self.w1, np.float64), (self.w2, np.float64),
             (self.seed_nodes, np.int64), (self.seed_axes, np.int64), (self.seed_weights, np.float64)))
        p1, p2, w1, w2, sn, sa, sw = vectors
        # Compile once before starting concurrent output sweeps.
        _COMPILED(p1[:1], p2[:1], w1[:1], w2[:1], 0, sn[:0], sa[:0], sw[:0], len(self.steps))
        compile_sec = time.perf_counter()-started
        started = time.perf_counter()
        def row(value):
            node = value.node if isinstance(value, Dual) else 0
            if not node:
                return np.zeros(len(self.steps))
            return _COMPILED(p1, p2, w1, w2, node, sn, sa, sw, len(self.steps))
        with ThreadPoolExecutor(max_workers=min(workers, len(outputs))) as pool:
            result = np.array(list(pool.map(row, outputs)))
        if not np.isfinite(result).all():
            raise ValueError('Nonfinite reverse Jacobian')
        self.backward_receipt = dict(workers=min(workers, len(outputs)), outputs=len(outputs),
            axes=len(self.steps), nodes=len(self.p1)-1,
            tape_bytes=sum(v.nbytes for v in vectors), compile_or_load_sec=compile_sec,
            sweep_sec=time.perf_counter()-started, numba_version=numba.__version__, fastmath=False)
        return result

    def result(self, outputs=()):
        axes = lambda mask: [j for j in self.steps if mask & (1 << j)]
        return dict(trace_mode='reverse_active_branch_tape', operations=len(self.p1)-1,
            exact_tie_axes=axes(self.exact_support), discrete_dependent_axes=axes(self.discrete_support),
            event_counts=dict(self.counts), stencil_crossings_assessed=False,
            output_risk_propagation=False, reverse_sweeps=self.backward_receipt,
            event_scope='Conservative structural dependency support; cancellation may leave extra event axes')


class Dual(forward.Dual):
    __slots__ = ('node', 'support')

    def __init__(self, value, tangent, trace, risks=(0, 0)):
        self.value, self.trace, self.risks = float(value), trace, (0, 0)
        self.tangent = {j: v for j, v in tangent.items() if v != 0.}
        if any(type(j) is not int or j not in trace.steps or not math.isfinite(v) for j, v in self.tangent.items()):
            raise ValueError('Invalid reverse seed')
        self.node = trace.node()
        self.support = 0
        for j, weight in self.tangent.items():
            self.support |= 1 << j
            trace.seed_nodes.append(self.node); trace.seed_axes.append(j); trace.seed_weights.append(weight)

    @classmethod
    def _result(cls, value, node, support, trace, seed=None):
        result = object.__new__(cls)
        result.value, result.node, result.support = float(value), node, support
        result.trace, result.risks, result.tangent = trace, (0, 0), seed
        return result

    def __reduce_ex__(self, protocol):
        # The ledger freezes records within the same isolated prediction.
        # Serializing an entire tape per record block would be quadratic.
        return (_restore_scalar, (self.trace.identity, self.node, self.value, self.support, self.tangent))

    def __add__(self, other):
        return self.trace.operation(self.value+primal(other), self, 1., other, 1.)
    __radd__ = __add__

    def __sub__(self, other):
        return self.trace.operation(self.value-primal(other), self, 1., other, -1.)

    def __rsub__(self, other):
        return self.trace.operation(primal(other)-self.value, self, -1., other, 1.)

    def __mul__(self, other):
        return self.trace.operation(self.value*primal(other), self, primal(other), other, self.value)
    __rmul__ = __mul__

    def __truediv__(self, other):
        denominator = primal(other)
        return self.trace.operation(self.value/denominator, self, 1./denominator,
                                    other, -self.value/denominator**2)

    def __rtruediv__(self, other):
        return self.trace.operation(primal(other)/self.value, self, -primal(other)/self.value**2,
                                    other, 1./self.value)

    def __pow__(self, other):
        if isinstance(other, Dual):
            value = self.value**other.value
            return self.trace.operation(value, self, other.value*self.value**(other.value-1),
                                        other, value*math.log(self.value))
        value = self.value**other
        scale = other*self.value**(other-1) if other != 0 else 0.
        return self.trace.operation(value, self, scale)

    def __neg__(self):
        return self.trace.operation(-self.value, self, -1.)

    def __abs__(self):
        self.trace.branch(self, 0., output_connected=True)
        return self if self.value >= 0. else -self

    def __mod__(self, other):
        denominator = primal(other)
        quotient = math.floor(self.value/denominator)
        self.trace.branch(self, quotient*denominator, discrete=True)
        self.trace.branch(self, (quotient+1)*denominator, discrete=True)
        return self.trace.operation(self.value % denominator, self, 1., other, -quotient)

    def __int__(self):
        self.trace.discrete_support |= self.support
        return int(self.value)

    def __round__(self, ndigits=None):
        self.trace.discrete_support |= self.support
        return round(self.value, ndigits) if ndigits is not None else round(self.value)


class MathProxy(forward.MathProxy):
    @staticmethod
    def exp(value):
        if not isinstance(value, Dual): return math.exp(value)
        y = math.exp(value.value)
        return value.trace.operation(y, value, y)

    @staticmethod
    def expm1(value):
        if not isinstance(value, Dual): return math.expm1(value)
        return value.trace.operation(math.expm1(value.value), value, math.exp(value.value))

    @staticmethod
    def log(value):
        if not isinstance(value, Dual): return math.log(value)
        return value.trace.operation(math.log(value.value), value, 1./value.value)

    @staticmethod
    def sqrt(value):
        return value**.5 if isinstance(value, Dual) else math.sqrt(value)

    @staticmethod
    def fsum(values):
        if PRIMAL_GUARD:
            values=list(values)
            total=math.fsum(primal(v) for v in values)
            active=[v for v in values if isinstance(v,Dual)]
            if not active:return total
            trace=active[0].trace
            if any(v.trace is not trace for v in active):
                raise ValueError('Reverse arithmetic mixed prediction tapes')
            return Dual._result(total,0,0,trace)
        if DIRECT_SUM_NODES:
            # fsum's primal still uses CPython's compensated summation. Its
            # derivative is the identical ordered chain of unit-weight edges;
            # intermediate Dual wrappers have no observer and need not exist.
            numbers, active = [], []
            for value in values:
                if isinstance(value, Dual):
                    numbers.append(value.value)
                    active.append(value)
                else:
                    numbers.append(primal(value))
            total = math.fsum(numbers)
            if not active:
                return total
            first = active[0]
            trace, node, support = first.trace, first.node, first.support
            for value in active[1:]:
                if value.trace is not trace:
                    raise ValueError('Reverse arithmetic mixed prediction tapes')
                node = trace.node(node, value.node, 1., 1.)
                support |= value.support
            return Dual._result(total, node, support, trace)
        values = list(values)
        total = math.fsum(primal(v) for v in values)
        active = [v for v in values if isinstance(v, Dual)]
        if not active: return total
        joined = active[0]
        for value in active[1:]:
            joined = joined.trace.operation(0., joined, 1., value, 1.)
        return Dual._result(total, joined.node, joined.support, joined.trace)


class NumpyProxy(forward.NumpyProxy):
    @staticmethod
    def clip(value, lower, upper):
        if any(isinstance(v, Dual) for v in (value, lower, upper)):
            return minimum(maximum(value, lower), upper)
        return np.clip(value, lower, upper)

    @staticmethod
    def std(values, *args, **kwargs):
        values = list(values)
        if not any(isinstance(v, Dual) for v in values): return np.std(values, *args, **kwargs)
        if args or kwargs: raise TypeError('Unsupported reverse std signature')
        mean = sum(values)/len(values)
        variance = sum((v-mean)**2 for v in values)/len(values)
        if primal(variance) == 0.:
            trace = next(v.trace for v in values if isinstance(v, Dual))
            for v in values: trace.branch(v, mean)
            return 0.
        return MathProxy.sqrt(variance)

    @staticmethod
    def max(values): return maximum(values)
    @staticmethod
    def min(values): return minimum(values)


def extremum(is_max, *args, **kwargs):
    function = builtins.max if is_max else builtins.min
    if kwargs: return function(*args, **kwargs)
    if FAST_PRIMITIVES and len(args) == 2:
        a,b=args
        da,db=isinstance(a,Dual),isinstance(b,Dual)
        if not da and not db:
            return function(a,b)
        av,bv=(a.value if da else a),(b.value if db else b)
        choose_b=(bv>av) if is_max else (bv<av)
        selected,other=(b,a) if choose_b else (a,b)
        if other is not selected:
            (a.trace if da else b.trace).branch(other,selected,output_connected=True)
        return selected
    values = list(args[0]) if len(args) == 1 else list(args)
    if not values: raise ValueError('max()/min() arg is an empty sequence')
    trace = next((v.trace for v in values if isinstance(v, Dual)), None)
    if trace is None: return function(values)
    selected = values[0]
    for value in values[1:]:
        if (primal(value) > primal(selected)) if is_max else (primal(value) < primal(selected)):
            selected = value
    for value in values:
        if value is not selected: trace.branch(value, selected, output_connected=True)
    return selected


def minimum(*args, **kwargs): return extremum(False, *args, **kwargs)
def maximum(*args, **kwargs): return extremum(True, *args, **kwargs)
