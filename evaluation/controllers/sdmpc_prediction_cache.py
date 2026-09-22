"""Exact memoization inside one frozen-configuration traffic prediction.

No incremental floating sums, state fields, cross-candidate entries or time
skips. FIFO mutators invalidate the original ordered fsum. Signal keys retain
every dynamic operand by identity (including its AD tape), never just primal.
Configuration is query-owned and checked immutable by the endpoint caller.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import sys
import copy

_ACTIVE = ContextVar('sdmpc_prediction_cache', default=None)
_REVERSE_ARRAYS = ContextVar('sdmpc_reverse_arrays', default=False)


@contextmanager
def reverse_arrays():
    """Use numeric AD transport only while the worker propagates a Jacobian.

    Plain candidate predictions retain their measured faster scalar path.
    This execution context is internal; activation still requires the config.
    """
    token=_REVERSE_ARRAYS.set(True)
    try:yield
    finally:_REVERSE_ARRAYS.reset(token)


class Cache:
    def __init__(self, cfg):
        self.cfg = cfg
        self.stocks = {}
        self.signals = {}
        self.catalogs = {}
        self.ramp_stocks = {}
        self.ramp_enabled = cfg.network.sdmpc_options.get('ramp_stock_cache',False)
        self.flow_enabled = cfg.network.sdmpc_options.get('flow_update_cache',False)
        self.urban_pipeline_enabled = cfg.network.sdmpc_options.get('array_urban_pipeline',False) and _REVERSE_ARRAYS.get()
        self.fifo_all_enabled = cfg.network.sdmpc_options.get('persistent_urban_fifo',False)
        self.fifo_enabled = self.fifo_all_enabled or self.urban_pipeline_enabled
        self.array_fifos = {}
        self.urban_pipelines = {}


@contextmanager
def scope(cfg):
    parent = _ACTIVE.get()
    enabled = (getattr(cfg.network, 'sdmpc_options', None) or {}).get('prediction_cache', False)
    if parent is not None and parent.fifo_enabled and parent.array_fifos:
        raise ValueError('Cannot nest a prediction scope around unpublished numeric FIFO state')
    token = _ACTIVE.set(Cache(cfg) if enabled else None)
    completed = False
    try:
        yield _ACTIVE.get()
        completed = True
    finally:
        try:
            current = _ACTIVE.get()
            if completed and current is not None and current.fifo_enabled:
                for owner in current.urban_pipelines.values():owner.publish_all()
                # Publish live queues before their owner ends; copied snapshots
                # are independent. No arena is added to the public state.
                for queue, buffer in current.array_fifos.items():
                    object.__getattribute__(queue, '__dict__')['q'] = buffer.materialize()
            if parent is not None:
                parent.stocks.clear()
                parent.ramp_stocks.clear()
        finally:
            if current is not None:
                for owner in current.urban_pipelines.values():owner.restore_type()
            _ACTIVE.reset(token)


def active():
    return _ACTIVE.get()


def ramp_query_control(control):
    """Private ramp commands for the read-only METANET release query.

    Its caller changes only ramp_metering. The sole consumer reads VSL and ramp
    rates, and never mutates other control fields or retains this view. Keep
    the original whole-control deepcopy outside an explicitly enabled query.
    """
    cache = _ACTIVE.get()
    if cache is None or not cache.flow_enabled:
        return copy.deepcopy(control)
    result = copy.copy(control)
    result.ramp_metering = dict(control.ramp_metering)
    return result


def invalidate(queue):
    cache = _ACTIVE.get()
    if cache is not None:
        cache.stocks.pop(queue, None)


def ramp_stock_entry(ramp):
    cache=_ACTIVE.get()
    if cache is None or not cache.ramp_enabled:
        return None,None,None
    # Read-only checks may suppress graph recording. Their node-zero values
    # must never become an input to a subsequent physical flow calculation.
    ad=sys.modules.get('evaluation.controllers.sdmpc_tangent_reverse')
    guarded=bool(getattr(ad,'PRIMAL_GUARD',False))
    key=(ramp,guarded)
    return cache,key,cache.ramp_stocks.get(key)


def invalidate_ramp(ramp):
    cache=_ACTIVE.get()
    if cache is not None and cache.ramp_enabled:
        cache.ramp_stocks.pop((ramp,False),None)
        cache.ramp_stocks.pop((ramp,True),None)


def input_catalog(cfg, kind):
    cache = _ACTIVE.get()
    if cache is None or cache.cfg is not cfg:
        return None
    if kind not in cache.catalogs:
        cache.catalogs[kind] = {n: r for n, r in
            getattr(cfg.network, 'native_internal_inputs', {}).get('inputs', {}).items()
            if r.get('kind') == kind}
    return cache.catalogs[kind]


def signal_entry(cfg, signal, phase, step, operands, basis):
    cache = _ACTIVE.get()
    if cache is None or cache.cfg is not cfg:
        return None, None, None
    # Retaining the operand objects prevents id reuse. Equal primal values on
    # distinct derivative tapes or axes must not share an intermediate.
    geometry = (basis['kind'], basis['cycle_sec'], basis['amber_sec'], basis['all_red_sec'],
                tuple(basis['phase_order']), tuple(basis['idle_after_phase_sec'].items()))
    key = (signal, phase, step, geometry, tuple(id(v) for v in operands))
    entry = cache.signals.get(key)
    return cache, key, entry
