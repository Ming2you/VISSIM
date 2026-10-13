"""The city-only report must use its own result and the same-window hold."""
from copy import deepcopy
import unittest

from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.citynative289.complete_cached_analysis import (
    prediction_metadata,
)


class MetadataTest(unittest.TestCase):
    def setUp(self):
        self.city = dict(
            status="complete", start_sec=2400, end_sec=2850,
            application=dict(state_error=0, same_forecast=True, same_current_source_pins=True),
            results=dict(city_only=dict(omega_ttt_veh_h=555), rm_only=dict(omega_ttt_veh_h=558)),
        )
        self.authority = dict(
            status="complete", start_sec=2400, end_sec=2850,
            results=dict(hold=dict(omega_ttt_veh_h=560), selected=dict(omega_ttt_veh_h=554)),
        )

    def test_city_is_not_rm_or_joint_and_outside_stays_unknown(self):
        result = prediction_metadata(self.city, self.authority)
        self.assertEqual(result["delta_omega_veh_h"], -5)
        self.assertIsNone(result["delta_tracked_outside_veh_h"])

    def test_reject_different_baseline_window(self):
        self.authority["end_sec"] = 3000
        with self.assertRaises(AssertionError):
            prediction_metadata(self.city, self.authority)

    def test_reject_different_initial_state_or_source(self):
        for key, value in (("state_error", 1), ("same_forecast", False), ("same_current_source_pins", False)):
            city = deepcopy(self.city)
            city["application"][key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError):
                prediction_metadata(city, self.authority)

    def test_reject_unfinished_or_nonfinite(self):
        for field, value in (("status", "running"), ("value", float("nan")), ("value", float("inf"))):
            city = deepcopy(self.city)
            if field == "status":
                city["status"] = value
            else:
                city["results"]["city_only"]["omega_ttt_veh_h"] = value
            with self.subTest(field=field, value=value), self.assertRaises(AssertionError):
                prediction_metadata(city, self.authority)


if __name__ == "__main__":
    unittest.main()
