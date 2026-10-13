"""Uninstalled cache experiment; never imported by a running predictor.

Reuse an ordered stock sum only between queue mutations. Guarded primal sums
and real AD sums use different cache entries. No vehicle totals are updated
incrementally or stored as a second physical population.
"""
import inspect
import ast
from evaluation.controllers import lane_offramp_runtime as module


def build(backend=None):
    source = inspect.getsource(module.SharedSignalApproach)
    marker = '        self.assert_conserved()'
    assert source.count(marker) == 5
    source = source.replace(marker,
        "        self._stock_epoch = getattr(self, '_stock_epoch', 0)+1\n"+marker)
    marker = '            self.admitted+=accepted'
    assert source.count(marker) == 1
    source = source.replace(marker,
        "            self._stock_epoch = getattr(self, '_stock_epoch', 0)+1\n"+marker)
    namespace = dict(vars(module))
    tree = ast.parse(source)
    if backend is not None:
        from evaluation.controllers.sdmpc_tangent_runtime import Transform, namespace as tangent_namespace
        namespace.update(tangent_namespace(), math=backend.MathProxy(),
            _tangent_float=backend.float_keep, _tangent_min=backend.minimum,
            _tangent_max=backend.maximum, _tangent_math=backend.MathProxy())
        tree = Transform().visit(tree)
    exec(compile(ast.fix_missing_locations(tree), '<uninstalled-stock-cache-candidate>', 'exec'), namespace)
    cls = namespace['SharedSignalApproach']
    original = cls.stock
    def stock(self, lane=None):
        epoch = getattr(self, '_stock_epoch', 0)
        cache = getattr(self, '_stock_cache', None)
        if cache is None or cache[0] != epoch:
            cache = (epoch, {})
            self._stock_cache = cache
        key = (lane, bool(getattr(backend, 'PRIMAL_GUARD', False)))
        if key not in cache[1]:
            cache[1][key] = original(self, lane)
        return cache[1][key]
    cls.stock = stock
    return cls
