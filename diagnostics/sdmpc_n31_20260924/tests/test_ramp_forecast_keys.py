"""strict_ramp_keys guard of the ramp-arrival forecast (2026-09-25).

vissim_stackelberg_adapter.profiled_demand_rates looks both forecast tables up by the runtime ramp keys
(RM_C<connector> with physical ramp branches). A table keyed by the legacy groups R_D_W/R_F_W/R_D_E/R_F_E
silently fell back to 120 s / 900 veh/h; with strict_ramp_keys the key sets must match exactly.
"""
from __future__ import annotations

import unittest

from evaluation.controllers.vissim_stackelberg_adapter import _require_ramp_forecast_keys

RAMPS = ['RM_C10480', 'RM_C10482', 'RM_C10646', 'RM_C10644', 'RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484']


class RampForecastKeyTests(unittest.TestCase):
    def test_runtime_keys_pass(self):
        table = dict.fromkeys(RAMPS, 1.0)
        _require_ramp_forecast_keys({'queue_drain_horizon_sec_by_ramp': table, 'max_vph_by_ramp': table}, RAMPS)

    def test_legacy_group_keys_rejected(self):
        legacy = dict.fromkeys(['R_D_W', 'R_F_W', 'R_D_E', 'R_F_E'], 1.0)
        with self.assertRaisesRegex(ValueError, 'queue_drain_horizon_sec_by_ramp'):
            _require_ramp_forecast_keys({'queue_drain_horizon_sec_by_ramp': legacy}, RAMPS)

    def test_missing_meter_rejected(self):
        with self.assertRaisesRegex(ValueError, 'max_vph_by_ramp'):
            _require_ramp_forecast_keys({'max_vph_by_ramp': dict.fromkeys(RAMPS[:-1], 1.0)}, RAMPS)

    def test_extra_key_rejected(self):
        table = dict.fromkeys(RAMPS + ['R_D_E'], 1.0)
        with self.assertRaises(ValueError):
            _require_ramp_forecast_keys({'max_vph_by_ramp': table}, RAMPS)


if __name__ == '__main__':
    unittest.main()
