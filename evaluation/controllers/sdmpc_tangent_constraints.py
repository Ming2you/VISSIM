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
        import numba
        if _COMPILED_FORWARD is None:
            _COMPILED_FORWARD = numba.njit(cache=True, nogil=True, fastmath=False)(_forward_column)
        arrays = tuple(np.frombuffer(v, dtype=dtype) for v, dtype in (
            (trace.p1, np.int64), (trace.p2, np.int64), (trace.w1, np.float64), (trace.w2, np.float64),
            (trace.seed_nodes, np.int64), (trace.seed_axes, np.int64), (trace.seed_weights, np.float64)))
        _COMPILED_FORWARD(*(a[:1] if i < 4 else a[:0] for i,a in enumerate(arrays)), np.zeros(1,dtype=np.int64), 0)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            columns = list(pool.map(lambda j: _COMPILED_FORWARD(*arrays, unique, j), range(n)))
        matrix = np.asarray(columns).T[inverse]
        method, sweeps = 'forward_columns_on_existing_reverse_tape', n
    if not np.isfinite(matrix).all():
        raise ValueError('Nonfinite physical state Jacobian')
    return matrix, dict(seconds=time.perf_counter()-started, method=method, sweeps=sweeps,
                        rows=len(values), unique_nonzero_nodes=len(nonzero), workers=workers,
                        additional_traffic_rollouts=0, additional_optimization_iterations=0)
