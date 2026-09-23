"""Horizon-end state inequalities on the existing continuous prediction tape.

No traffic law is replaced. Every original stepwise allocator/state gate still
runs. Allocation/conservation audits are checks of condensed dynamics, not extra
optimization multipliers. The central state registry follows the release's H3
endpoint contract, including this plant's recorded urban cell/queue bounds.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import time
import numpy as np
from evaluation.controllers import sdmpc_tangent_reverse as ad


class Registry:
    def __init__(self, endpoints):
        self.endpoints = set(endpoints)
        self.rows = {}
        self.visited = set()

    def add(self, name, value):
        if name in self.rows:
            raise ValueError('Duplicate central state constraint: ' + name)
        if not np.isfinite(ad.primal(value)):
            raise ValueError('Nonfinite central state constraint: ' + name)
        self.rows[name] = value

    def bound(self, ledger, kind, resource, value, upper):
        stamp = ledger._response_stamp()
        end = stamp['end_sec']
        if end not in self.endpoints:
            return
        self.visited.add(end)
        name = f"state/{end:g}/{kind}/{resource}"
        self.add(name + '/lower', -value)
        self.add(name + '/upper', value - upper)

    def finish(self, states, cfg):
        if {float(s.time_sec) for s in states} != self.endpoints or self.visited != self.endpoints:
            raise ValueError('Missing horizon-end state bound coverage')
        fields = ('ramp_queue', 'urban_movement_queue', 'mainline_origin_queue',
                  'freeway_density', 'freeway_buffer_up_density', 'freeway_buffer_down_density')
        for state in states:
            prefix = f'physical/{float(state.time_sec):g}'
            for field in fields:
                for key, values in sorted(getattr(state, field).items()):
                    seq = values if isinstance(values, (list, tuple)) else [values]
                    for j, value in enumerate(seq):
                        self.add(f'{prefix}/{field}/{key}/{j}/lower', -value)
            for key, cap in sorted(cfg.network.urban_link_storage_veh.items()):
                value = state.urban_link_storage.get(key, cap)
                self.add(f'{prefix}/storage/{key}/lower', -value)
                self.add(f'{prefix}/storage/{key}/upper', value-cap)
            lane = getattr(state, 'lane_freeway_runtime', None)
            if lane is not None:
                for road, plant in sorted(lane.lanes.items()):
                    for i, groups in enumerate(plant.n):
                        for j, value in enumerate(groups):
                            self.add(f'{prefix}/lane_inventory/{road}/{i}/{j}/lower', -value)
        names = sorted(self.rows)
        values = [self.rows[name] for name in names]
        return names, values


def install(finder, endpoints):
    from evaluation.controllers.control_area_objective import ModelAreaLedger
    registry = Registry(endpoints)
    original = ModelAreaLedger.record_state_upper_bound

    def record(ledger, kind, resource, value_veh, upper_veh):
        original(ledger, kind, resource, value_veh, upper_veh)
        if ledger.captures_response:
            registry.bound(ledger, kind, resource, value_veh, upper_veh)

    ModelAreaLedger.record_state_upper_bound = record
    path = Path(__file__).resolve()
    finder.source_hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return registry


def _forward_column(p1, p2, w1, w2, sn, sa, sw, outputs, axis):
    tangent = np.zeros(len(p1), dtype=np.float64)
    for k in range(len(sn)):
        if sa[k] == axis:
            tangent[sn[k]] += sw[k]
    for i in range(1, len(p1)):
        tangent[i] += w1[i]*tangent[p1[i]] + w2[i]*tangent[p2[i]]
    return tangent[outputs]


_COMPILED_FORWARD = None


def _forward_column_from(p1, p2, w1, w2, sn, sa, sw, outputs, axis, start):
    """_forward_column, but the tape sweep begins at `start` instead of node 1."""
    tangent = np.zeros(len(p1), dtype=np.float64)
    for k in range(len(sn)):
        if sa[k] == axis:
            tangent[sn[k]] += sw[k]
    for i in range(start, len(p1)):
        tangent[i] += w1[i]*tangent[p1[i]] + w2[i]*tangent[p2[i]]
    return tangent[outputs]


def _mark_ancestors(p1, p2, live):
    for i in range(len(p1)-1, 0, -1):
        if live[i]:
            live[p1[i]] = 1
            live[p2[i]] = 1


_COMPILED_FROM = None
_COMPILED_MARK = None


def _forward_columns(arrays, unique, n, workers):
    """All n forward columns, evaluated only where they can reach an output.

    The full sweep runs every axis over the whole tape (~14M nodes x 231 axes), yet
    only ~31% of nodes are ancestors of a central output and ~33 axes reach none.
    Three reductions, each exact:

      1. Ancestor compaction. Parents precede children on the tape, so the ancestor
         set of the outputs is closed under taking parents. Sweeping only those
         nodes, in the original order, performs the same floating-point operations on
         every node that can influence an output -- a non-finite weight on an
         ancestor therefore still surfaces exactly as before.
      2. Dead axes. An axis with no seed among the ancestors yields +0.0 at every
         output in the full sweep (tangent starts at +0.0, and x += -0.0 stays +0.0),
         which is what np.zeros returns.
      3. First use. Before an axis's earliest seed node every tangent is exactly 0.0
         when the weights are finite, so that axis's sweep starts there.

    Steps 2 and 3 both rest on 0*w == 0, which fails for a non-finite w: 0*inf is NaN,
    and it reaches the outputs even on an axis whose seeds reach none of them. So if
    any compact weight is non-finite, every axis -- dead ones included -- is swept from
    node 1 over the compact tape, which reproduces the full sweep's NaN/inf pattern
    exactly (tools/verify_central_prune.py poisons a weight to check this).
    """
    global _COMPILED_FROM, _COMPILED_MARK
    import numba
    if _COMPILED_FROM is None:
        _COMPILED_FROM = numba.njit(cache=True, nogil=True, fastmath=False)(_forward_column_from)
        _COMPILED_MARK = numba.njit(cache=True, nogil=True)(_mark_ancestors)
    p1, p2, w1, w2, sn, sa, sw = arrays
    live = np.zeros(len(p1), dtype=np.uint8)
    live[unique] = 1
    _COMPILED_MARK(p1, p2, live)
    live[0] = 1                                   # dummy slot 0 stays at compact index 0
    keep = np.flatnonzero(live)
    remap = np.zeros(len(p1), dtype=np.int64)
    remap[keep] = np.arange(len(keep), dtype=np.int64)
    seeds = live[sn].astype(bool)
    compact = (np.ascontiguousarray(remap[p1[keep]]), np.ascontiguousarray(remap[p2[keep]]),
               np.ascontiguousarray(w1[keep]), np.ascontiguousarray(w2[keep]),
               np.ascontiguousarray(remap[sn[seeds]]), np.ascontiguousarray(sa[seeds]),
               np.ascontiguousarray(sw[seeds]))
    outputs = np.ascontiguousarray(remap[unique])
    finite = bool(np.isfinite(compact[2]).all() and np.isfinite(compact[3]).all())
    start = {}
    for node, axis in zip(compact[4].tolist(), compact[5].tolist()):
        start[axis] = min(start.get(axis, node), node)
    if not finite:
        start = {axis: 1 for axis in range(n)}
    _COMPILED_FROM(*(a[:1] if i < 4 else a[:0] for i, a in enumerate(compact)),
                   np.zeros(1, dtype=np.int64), 0, 1)
    zero = np.zeros(len(outputs), dtype=np.float64)

    def column(axis):
        if axis not in start:
            return zero
        return _COMPILED_FROM(*compact, outputs, axis, max(1, start[axis]))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        columns = list(pool.map(column, range(n)))
    swept = sum(len(keep) - max(1, s) for s in start.values())
    live_axes = len(set(compact[5].tolist()))
    stats = dict(tape_nodes=int(len(p1)-1), ancestor_nodes=int(len(keep)-1), live_axes=live_axes,
                 dead_axes=int(n-live_axes), finite_weights=finite,
                 node_updates_ratio=swept/float(max(1, (len(p1)-1)*n)))
    return np.asarray(columns).T, stats


def jacobian(trace, values, workers):
    """Reuse the same tape, choosing its smaller input/output sweep dimension."""
    global _COMPILED_FORWARD
    started = time.perf_counter()
    if any(isinstance(v, ad.Dual) and v.trace is not trace for v in values):
        raise ValueError('Physical state uses another prediction tape')
    nodes = np.array([v.node if isinstance(v, ad.Dual) else 0 for v in values], dtype=np.int64)
    unique, inverse = np.unique(nodes, return_inverse=True)
    nonzero = unique[unique != 0]
    n = len(trace.steps)
    if len(nonzero) <= n:
        # Group identical tape outputs; constants need no reverse traversal.
        by_node = {v.node: v for v in values if isinstance(v, ad.Dual) and v.node}
        chosen = [by_node[int(node)] for node in nonzero]
        rows = trace.jacobian(chosen, workers) if chosen else np.zeros((0, n))
        table = {0: np.zeros(n), **{int(node): row for node, row in zip(nonzero, rows)}}
        matrix = np.array([table[int(node)] for node in nodes])
        method, sweeps = 'reverse_unique_state_nodes', len(nonzero)
    else:
        arrays = tuple(np.frombuffer(v, dtype=dtype) for v, dtype in (
            (trace.p1, np.int64), (trace.p2, np.int64), (trace.w1, np.float64), (trace.w2, np.float64),
            (trace.seed_nodes, np.int64), (trace.seed_axes, np.int64), (trace.seed_weights, np.float64)))
        columns, pruning = _forward_columns(arrays, unique, n, workers)
        matrix = columns[inverse]
        method, sweeps = 'forward_columns_on_existing_reverse_tape', n
    if not np.isfinite(matrix).all():
        raise ValueError('Nonfinite physical state Jacobian')
    return matrix, dict(seconds=time.perf_counter()-started, method=method, sweeps=sweeps,
                        rows=len(values), unique_nonzero_nodes=len(nonzero), workers=workers,
                        additional_traffic_rollouts=0, additional_optimization_iterations=0,
                        **({'forward_pruning': pruning} if method.startswith('forward') else {}))
