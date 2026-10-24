"""WP-B2 V0-8: the origin boundary B6 hands to A1 reproduces the calibration recursion.

The b110 observations (B110, read-only) are fed to boundary_factory.build_window in
history_forecast mode (BF:98-138). The same 150 s history is turned into the
obs150 source_boundary block by obs150_lane.source_boundary (admitted_window =
150 s crossings, admitted_cum = cumulative crossings, backlog = schedule integral
minus admitted), and source_boundary.forecast (WP-C) must give the block means of
BF's 10 s source requests to 1e-9. The schedule is the obs150 context schedule
(inpx vehicle inputs), checked equal to the calibration desired_source_demand (T7b).
"""
from __future__ import annotations

import importlib.util
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_lane_support as sup  # noqa: E402
from test_lane_support import c  # noqa: E402

from evaluation.controllers import obs150_lane as lane  # noqa: E402

BF = sup.ROOT / 'diagnostics' / 'demand_sweep' / 'user_native_20260914' / 'metanet_calibration_v1' / 'boundary_factory.py'
CUTOFFS = (900.1, 1800.1, 4500.1)          # native_phase_sec 0.1 (B110 manifest)


def boundary_factory():
    spec = importlib.util.spec_from_file_location('obs150_bf', BF)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(sup.B110_OBSERVATIONS.is_dir() and sup.NET.is_file(), 'b110 observations or v2 network missing')
class SourceBoundaryV08(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bf = boundary_factory()
        cls.data = cls.bf.ObservationData(sup.B110_OBSERVATIONS)
        net = sup.network()
        cls.schedule = {'FW_E': net.source_schedule(74), 'FW_W': net.source_schedule(26)}

    def test_t7b_schedule_equals_the_calibration_demand(self):
        for road, rows in self.schedule.items():
            for t in range(0, 9001, 30):
                self.assertEqual(c.schedule_rate_at(rows, t), self.data.demand_vph(road, t))
                self.assertAlmostEqual(c.schedule_integral_veh(rows, 0.0, t), self.data.desired_before(road, t),
                                       delta=1e-9)

    def test_block_means_equal_the_calibration_recursion(self):
        from evaluation.controllers import source_boundary
        sources = {b['road']: name for name, b in self.data.definitions.items() if b['kind'] == 'source'}
        for cutoff in CUTOFFS:
            window = self.bf.build_window(self.data, cutoff, 'history_forecast', model_step_sec=10, horizon_sec=450)
            ends = [round(cutoff - 150 + d, 6) for d in range(30, 151, 30)]
            terms, cumulative = {}, {}
            for road, name in sources.items():
                crossings = sum(int(float(self.data.boundaries[t, name]['crossings'])) for t in ends)
                cumulative[road] = int(float(self.data.boundaries[cutoff, name]['cumulative_crossings']))
                terms['source:' + road] = c.IdentityTerms('source:' + road, 'source', 'down', crossings, 0, 0, 0,
                                                          crossings, (), True, ())
            obs = {'sim_sec': 900, 'source_cumulative_vehs': cumulative,
                   'err': {'removals_cum_by_boundary': {'source:FW_E': 0, 'source:FW_W': 0}}}
            context = SimpleNamespace(source_refs={r: 'source:' + r for r in c.ROADS}, source_schedule=self.schedule)
            block = lane.source_boundary(obs, context, terms)
            for road in c.ROADS:
                row = block[road]
                # BF:100 recent and BF:104-105 backlog, evaluated at the phase-shifted cutoff.
                integral = c.schedule_integral_veh(self.schedule[road], 0.0, cutoff)
                backlog = max(0.0, integral - row['admitted_cum'])
                self.assertAlmostEqual(backlog, window['meta']['external_backlog_estimate_at_cutoff'][road], delta=1e-9)
                self.assertEqual(row['recent_vph'], 3600.0 * row['admitted_window'] / 150)
                blocks = source_boundary.forecast(row['recent_vph'], backlog, self.schedule[road], cutoff, 150, 3)
                steps = [s['source_demand_vph'][road] for s in window['boundary_steps']]
                expected = [math.fsum(steps[15 * b:15 * (b + 1)]) / 15 for b in range(3)]
                for got, want in zip(blocks, expected):
                    self.assertAlmostEqual(got, want, delta=1e-9, msg=f'{road} at {cutoff}')


if __name__ == '__main__':
    unittest.main()
