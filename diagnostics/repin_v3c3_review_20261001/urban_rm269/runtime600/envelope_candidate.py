"""Prototype cache of fixed receiving geometry; active workers are untouched."""
from bisect import bisect_right
from evaluation.controllers.physical_urban_transport import ReceivingEnvelope

ORIGINAL = ReceivingEnvelope.initial_bound


def initial_bound(self, elapsed):
    key = (self.length, self.wave, self.spacing, self.critical, self.qmax,
           tuple(self.positions), tuple(self.points), type(self).initial_prefix)
    # No state/control derivatives are cached as constants. An altered position,
    # wave, geometry, or prefix implementation invalidates the complete cache.
    numbers = key[:5] + key[5] + key[6] + (elapsed,)
    if (any(type(v) not in (int, float) for v in numbers)
            or any(v != v or abs(v) == float('inf') for v in numbers)
            or list(key[6]) != sorted(key[6])):
        return ORIGINAL(self, elapsed)
    cache = getattr(self, '_runtime600_envelope_cache', None)
    if cache is None or cache['key'] != key:
        running = []
        for x in self.points:
            term = -self.initial_prefix(x) + self.critical*x
            running.append(term if not running else min(running[-1], term))
        cache = dict(key=key, prefix_min=running, last_elapsed=None, last_bound=None)
        self._runtime600_envelope_cache = cache
    if cache['last_elapsed'] == elapsed:
        return cache['last_bound']
    limit = min(self.length, self.wave*elapsed)
    count = bisect_right(self.points, limit)
    term = -self.initial_prefix(limit) + self.critical*limit
    minimum = min(cache['prefix_min'][count-1], term) if count else term
    result = self.qmax*elapsed + minimum
    cache.update(last_elapsed=elapsed, last_bound=result)
    return result
