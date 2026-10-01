"""K1 (repin plan 2026-10-01, H-1): the off-ramp storage sum does not depend on PYTHONHASHSEED.

T5 found 1-2 ulp differences in four prediction diagnostics of R-obs 4050/4500 between replays, traced to
TrafficState.off_ramp_storage_occupancy_veh iterating a set of link names (hash-seed order) while summing
floats. The sum now runs in sorted name order. Child pythons with different seeds must return the same bits,
equal to the explicit sorted-order sum. No VISSIM, no adapter.
"""
from __future__ import annotations

import os
import subprocess
import sys
import unittest

import n31_fixtures as fx

PROBE = r'''
import sys
from types import SimpleNamespace
sys.path.insert(0, sys.argv[1])
from src.models.state import TrafficState
# Eight storages whose occupancies do not sum associatively: one huge stock (an ulp of 2 veh) and seven of one
# vehicle each, so the bits depend on the order. Plus a link listed twice (two off-ramps share a storage) and
# an unknown link (skipped). Storage 0 left -> occupancy = capacity exactly.
links = {'OR_%d' % i: 'OR_%d_storage' % i for i in range(8)}
links['OR_shared'] = 'OR_3_storage'
links['OR_missing'] = 'OR_missing_storage'
capacity = {'OR_%d_storage' % i: (1e16 if i == 3 else 1.0) for i in range(8)}
storage = {link: 0.0 for link in capacity}
net = SimpleNamespace(off_ramp_storage_link=links, urban_link_storage_veh=capacity)
state = SimpleNamespace(urban_link_storage=storage)
total = TrafficState.off_ramp_storage_occupancy_veh(state, net)
expected = 0.0
for link in sorted(set(links.values())):
    if link in capacity:
        expected += max(0.0, capacity[link] - storage.get(link, capacity[link]))
print(total.hex(), float(expected).hex(), [l for l in set(links.values())][:3])
'''


class OffRampStorageHashOrderTests(unittest.TestCase):
    def run_probe(self, seed):
        env = {k: v for k, v in os.environ.items() if not k.startswith('RW_')}
        env['PYTHONHASHSEED'] = str(seed)
        done = subprocess.run([sys.executable, '-B', '-c', PROBE, str(fx.ROOT / 'vendor/NumSim-mine')],
                              capture_output=True, text=True, env=env, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)
        total, expected, order = done.stdout.split(' ', 2)
        return total, expected, order

    def test_sum_bits_are_the_sorted_order_for_every_hash_seed(self):
        results = [self.run_probe(seed) for seed in (0, 1, 2, 3, 7, 11)]
        self.assertEqual({r[0] for r in results}, {results[0][1]})      # one value, = the sorted-order sum
        self.assertTrue(all(r[0] == r[1] for r in results))
        # the probe is sensitive: the set's own iteration order does change with the seed
        self.assertGreater(len({r[2] for r in results}), 1)


if __name__ == '__main__':
    unittest.main()
