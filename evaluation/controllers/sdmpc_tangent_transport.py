"""Array kernel for the original ordered lane-to-lane longitudinal transfers.

Both physical values and the same local reverse edges are computed together.
No fastmath, horizon skipping, destination aggregation, or receiving relaxation.
The boundary owns Python state; only this contiguous arithmetic block is compiled.
"""
from array import array
import math
import sys
import time
import numpy as np
from numba import njit
from evaluation.controllers.sdmpc_tangent_spatial import (
    _constant, _value, _add, _subtract, _multiply, _divide, _minimum, _branch)

STATS = dict(calls=0, scalar_calls=0, traced_calls=0, nodes=0, wall_sec=0.,
             kernel_sec=0., first_call_sec=None, numerical_workers=1)


@njit(cache=True, inline='always', fastmath=False)
def _put(values, refs, kinds, index, item):
    values[index], refs[index], kinds[index] = item


@njit(cache=True, inline='always', fastmath=False)
def _truth(item, counters, ties, discrete):
    if item[2]:
        _branch(item, _constant(0.), counters, ties)
        k = counters[3]
        if k == len(discrete):
            raise ValueError('Transport branch buffer exhausted')
        discrete[k] = item[1]
        counters[3] += 1
    return item[0] != 0.


@njit(cache=True, fastmath=False)
def _ordered_sum(values, refs, kinds, counters, parents, weights):
    # CPython 3.12 float sum compensates the plain prefix. Encountering a Dual
    # ends that fast path and follows its original ordered __radd__/__add__.
    hi, lo = 0., 0.
    total = _constant(0.)
    active = False
    for j in range(len(values)):
        item = _value(values, refs, kinds, j)
        if active:
            total = _add(total, item, counters, parents, weights)
        elif item[2]:
            total = _add(_constant(hi+lo), item, counters, parents, weights)
            active = True
        else:
            x = item[0]
            t = hi+x
            lo += (hi-t)+x if abs(hi) >= abs(x) else (x-t)+hi
            hi = t
    return total if active else _constant(hi+lo)


@njit(cache=True, nogil=True, fastmath=False)
def _transport(values, refs, kinds, sizes, matrices, through, free, before,
               velocity, incoming, outgoing, incoming_moment, part_moment,
               intent_before, intent_current, intent_targets, intent_lengths,
               inter, counters, parents, weights, ties, discrete):
    width = matrices.shape[1]
    req_v = np.empty((width, width), dtype=np.float64)
    req_r = np.empty((width, width), dtype=np.int64)
    req_k = np.empty((width, width), dtype=np.bool_)
    for i in range(len(sizes)-1):
        for g in range(sizes[i]):
            for k in range(sizes[i+1]):
                item = _multiply(_value(values, refs, kinds, through[i,g]),
                    _constant(matrices[i,g,k]), counters, parents, weights)
                req_v[g,k], req_r[g,k], req_k[g,k] = item
        accepted = _constant(0.)
        for k in range(sizes[i+1]):
            total = _ordered_sum(req_v[:sizes[i],k], req_r[:sizes[i],k],
                req_k[:sizes[i],k], counters, parents, weights)
            if _truth(total, counters, ties, discrete):
                factor = _minimum(_constant(1.), _divide(
                    _value(values, refs, kinds, free[i+1,k]), total,
                    counters, parents, weights), counters, ties)
            else:
                factor = _constant(0.)
            for g in range(sizes[i]):
                x = _multiply((req_v[g,k],req_r[g,k],req_k[g,k]), factor,
                              counters, parents, weights)
                j = outgoing[i,g]
                _put(values, refs, kinds, j, _add(_value(values,refs,kinds,j),x,counters,parents,weights))
                j = incoming[i+1,k]
                _put(values, refs, kinds, j, _add(_value(values,refs,kinds,j),x,counters,parents,weights))
                accepted = _add(accepted,x,counters,parents,weights)
                j = part_moment[i+1,k]
                if j >= 0:
                    xv = _multiply(x,_value(values,refs,kinds,velocity[0,i,g]),counters,parents,weights)
                    _put(values,refs,kinds,j,_add(_value(values,refs,kinds,j),xv,counters,parents,weights))
                j = incoming_moment[i+1,k]
                if j >= 0:
                    xv = _multiply(x,_value(values,refs,kinds,velocity[1,i,g]),counters,parents,weights)
                    _put(values,refs,kinds,j,_add(_value(values,refs,kinds,j),xv,counters,parents,weights))
                for o in range(len(intent_lengths)):
                    if i >= intent_lengths[o]:
                        continue
                    donor = _value(values,refs,kinds,before[i,g])
                    if _truth(donor,counters,ties,discrete):
                        y = _divide(_multiply(x,_value(values,refs,kinds,intent_before[o,i,g]),
                            counters,parents,weights),donor,counters,parents,weights)
                    else:
                        y = _constant(0.)
                    j = intent_current[o,i,g]
                    _put(values,refs,kinds,j,_subtract(_value(values,refs,kinds,j),y,counters,parents,weights))
                    j = intent_targets[o,i+1,k]
                    _put(values,refs,kinds,j,_add(_value(values,refs,kinds,j),y,counters,parents,weights))
        _put(values,refs,kinds,inter[i],accepted)


def _ad():
    return sys.modules.get('evaluation.controllers.sdmpc_tangent_reverse')


class Packed:
    def __init__(self):
        self.items = []

    def row(self, row):
        first = len(self.items)
        self.items.extend(row)
        return list(range(first, len(self.items)))

    def rows(self, rows, count, width):
        out = np.full((count,width),-1,dtype=np.int64)
        for i,row in enumerate(rows):
            out[i,:len(row)] = self.row(row)
        return out

    def arrays(self):
        ad = _ad()
        duals = [v for v in self.items if ad is not None and isinstance(v,ad.Dual)]
        self.trace = duals[0].trace if duals else None
        if any(v.trace is not self.trace for v in duals):
            raise ValueError('Array transport mixed reverse tapes')
        if self.trace is not None and (self.trace.frozen or ad.PRIMAL_GUARD):
            raise ValueError('Array transport cannot change a frozen or read-only tape')
        self.supports = {0:0, **{v.node:v.support for v in duals}}
        self.values = np.asarray([v.value if ad is not None and isinstance(v,ad.Dual) else v
                                  for v in self.items],dtype=np.float64)
        if not np.isfinite(self.values).all():
            raise ValueError('Nonfinite array transport input')
        self.refs = np.asarray([v.node if ad is not None and isinstance(v,ad.Dual) else 0
                               for v in self.items],dtype=np.int64)
        self.kinds = np.asarray([ad is not None and isinstance(v,ad.Dual) for v in self.items],dtype=np.bool_)
        return self.values,self.refs,self.kinds

    def finish(self, counters, parents, weights, ties, discrete):
        n,nties,comparisons,ndiscrete = map(int,counters)
        self.start = len(self.trace.p1) if self.trace is not None else 0
        if self.trace is None:
            if n or comparisons or ndiscrete:
                raise ValueError('Plain transport unexpectedly recorded derivatives')
            return
        mapped = np.where(parents[:n]<0,self.start-parents[:n]-1,parents[:n])
        for field,column in ((self.trace.p1,mapped[:,0]),(self.trace.p2,mapped[:,1]),
                             (self.trace.w1,weights[:n,0]),(self.trace.w2,weights[:n,1])):
            data = array(field.typecode)
            data.frombytes(np.ascontiguousarray(column).tobytes())
            field.extend(data)
        for j,(a,b) in enumerate(mapped.tolist()):
            self.supports[self.start+j] = self.supports[a] | self.supports[b]
        self.trace.counts['primal_comparisons'] += comparisons
        self.trace.counts['exact_primal_ties'] += nties
        self.trace.counts['discrete_comparisons'] += ndiscrete
        for a,b in ties[:nties].tolist():
            self.trace.exact_support |= self.supports[self.resolve(a)] | self.supports[self.resolve(b)]
        for ref in discrete[:ndiscrete].tolist():
            self.trace.discrete_support |= self.supports[self.resolve(ref)]

    def resolve(self, ref):
        return self.start-int(ref)-1 if ref<0 else int(ref)

    def restore(self, indices):
        ad = _ad()
        result = []
        for index in indices:
            if index < 0:
                continue
            value = float(self.values[index])
            if self.kinds[index]:
                node = self.resolve(self.refs[index])
                value = ad.Dual._result(value,node,self.supports[node],self.trace)
            result.append(value)
        return result


def longitudinal(plant, before, oldv, part_before, free, through, incoming,
                 outgoing, incoming_moment, part_in_moment, intent_before):
    """Execute exactly the original inter-cell loop and mutate its output lists."""
    started = time.perf_counter()
    count,width = len(before),max(map(len,before))
    sizes = np.asarray(list(map(len,before)),dtype=np.int64)
    matrices = np.zeros((count-1,width,width),dtype=np.float64)
    for i,matrix in enumerate(plant.matrices):
        for g,row in enumerate(matrix):
            if len(row) != sizes[i+1]:
                raise ValueError('Lane matrix does not match downstream groups')
            matrices[i,g,:len(row)] = row
    pack = Packed()
    source = [pack.rows(rows,count,width) for rows in (through,free,before)]
    velocity = np.stack([pack.rows([part_before[i]['post_v'] if i in part_before else oldv[i]
        for i in range(count)],count,width),pack.rows(oldv,count,width)])
    inc,out = [pack.rows(rows,count,width) for rows in (incoming,outgoing)]
    mom = pack.rows(incoming_moment or [],count,width)
    pmom = np.full((count,width),-1,dtype=np.int64)
    for i,row in part_in_moment.items():
        pmom[i,:len(row)] = pack.row(row)
    names = list(intent_before)
    lengths = np.asarray([len(intent_before[o]) for o in names],dtype=np.int64)
    initial = np.full((len(names),count,width),-1,dtype=np.int64)
    current = initial.copy()
    targets = initial.copy()
    for o,name in enumerate(names):
        initial[o] = pack.rows(intent_before[name],count,width)
        current[o] = pack.rows(plant.upstream_off[name],count,width)
        targets[o] = current[o]
        end = lengths[o]
        targets[o,end,:len(plant.off[name])] = pack.row(plant.off[name])
    inter = np.asarray(pack.row([0.]*(count-1)),dtype=np.int64)
    arrays = pack.arrays()
    # Bounds follow the number of arithmetic/branch operations per edge and
    # destination, not a traffic coefficient. No truncation on overflow.
    edges = sum(int(sizes[i])*int(sizes[i+1]) for i in range(count-1))
    capacity = 32+edges*(20+6*len(names))
    counters = np.zeros(4,dtype=np.int64)
    parents = np.zeros((capacity,2),dtype=np.int64)
    weights = np.zeros((capacity,2),dtype=np.float64)
    ties = np.zeros((capacity,2),dtype=np.int64)
    discrete = np.zeros(capacity,dtype=np.int64)
    kernel_start = time.perf_counter()
    _transport(*arrays,sizes,matrices,*source,velocity,inc,out,mom,pmom,
        initial,current,targets,lengths,inter,counters,parents,weights,ties,discrete)
    STATS['kernel_sec'] += time.perf_counter()-kernel_start
    pack.finish(counters,parents,weights,ties,discrete)
    for rows,indices in ((incoming,inc),(outgoing,out),(incoming_moment,mom)):
        if rows is not None:
            for i,row in enumerate(rows):
                row[:] = pack.restore(indices[i])
    for i,row in part_in_moment.items():
        row[:] = pack.restore(pmom[i])
    for o,name in enumerate(names):
        for i,row in enumerate(plant.upstream_off[name]):
            row[:] = pack.restore(current[o,i])
        plant.off[name][:] = pack.restore(targets[o,lengths[o]])
    result = pack.restore(inter)
    elapsed = time.perf_counter()-started
    if STATS['first_call_sec'] is None:
        STATS['first_call_sec'] = elapsed
    STATS['calls'] += 1
    STATS['traced_calls' if pack.trace is not None else 'scalar_calls'] += 1
    STATS['nodes'] += int(counters[0])
    STATS['wall_sec'] += elapsed
    return result
