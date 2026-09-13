"""Small in-memory ledger checks; no FZP, model, COM or actual-run analysis."""
import copy
import unittest
from unittest.mock import patch
from diagnostics import measure_no_control_5400_three_arm_area as producer
from diagnostics.measure_no_control_5400_three_arm_area import EVENTS, interval_windows, spatial_checks


def samples():
    rows = []
    ttt = 0.0
    # One vehicle appears in the first frame, exits alive at901, re-enters at
    #1801, then disappears unresolved at4501. No other traffic is invented.
    previous = 0
    td = 0
    for t in range(1, 5401):
        n = int(t <= 900 or 1801 <= t <= 4500)
        step = dict.fromkeys(EVENTS, 0)
        if t == 1:
            step["appeared_inside_events"] = 1
        elif t == 901:
            step["observed_exit_events"] = 1
            td += 1
        elif t == 1801:
            step["observed_entry_events"] = 1
        elif t == 4501:
            step["unresolved_inside_disappearances"] = 1
        ttt += (n + previous) / 7200
        rows.append({"sim_sec": t, "source": "fzp", "interval_sec": 1, "inside_vehicles": n,
                     "ttt_veh_h_cumulative": ttt, "ttd_observed_plus_terminal_cumulative": td,
                     "stock_closure_residual_veh": 0, **step})
        previous = n
    return rows, {"ttt_veh_h": ttt, "ttd_observed_plus_terminal_events": td}


class Area5400Tests(unittest.TestCase):
    def test_running_batch_stops_before_measurement(self):
        argv = ["producer", "--out", str(producer.ROOT / "diagnostics/unused_synthetic_gate_output")]
        with patch("sys.argv", argv), patch.object(producer, "load", return_value={"schema": "no-control-network-arms5400/v1", "status": "running"}), patch.object(producer.subprocess, "run") as child:
            with self.assertRaisesRegex(ValueError, "All three completed"):
                producer.main()
            child.assert_not_called()

    def test_six_windows_close_without_blacklisting_earlier_exit(self):
        rows, metrics = samples()
        windows = interval_windows(rows, metrics)
        self.assertEqual(windows[0]["ttd_events"], 1)
        self.assertEqual(windows[0]["unresolved_inside_disappearances"], 1)
        self.assertEqual(windows[2]["ttd_events"], 1)
        self.assertEqual(windows[6]["unresolved_inside_disappearances"], 1)
        self.assertAlmostEqual(windows[0]["ttt_veh_h"], 1)
        self.assertEqual(windows[7]["ttd_events"], 0)
        self.assertEqual(windows[8]["ttd_events"], 1)

    def test_missing_or_duplicate_timestamp_rejected(self):
        rows, metrics = samples()
        with self.assertRaisesRegex(ValueError, "grid"):
            interval_windows(rows[:-1], metrics)
        rows[-1]["sim_sec"] = 5399
        with self.assertRaisesRegex(ValueError, "grid"):
            interval_windows(rows, metrics)

    def test_censored_tail_not_promoted_to_actual_full_run(self):
        rows, metrics = samples()
        rows[-1]["source"] = "censored_hold_extrapolation"
        with self.assertRaisesRegex(ValueError, "substitution"):
            interval_windows(rows, metrics)

    def test_wrong_event_accounting_rejected_even_if_declared_closure_zero(self):
        rows, metrics = samples()
        rows[900]["observed_exit_events"] = 0
        with self.assertRaisesRegex(ValueError, "TD differs"):
            interval_windows(rows, metrics)

    def test_spatial_boundary_rejects_internal_transfer_as_TD(self):
        metrics = {"exit_events_by_observed_link_pair": {"in->out": 1}, "ttd_observed_exit_events": 1,
                   "terminal_inferred_by_link": {}, "ttd_terminal_exit_inferred_events": 0,
                   "unresolved_inside_disappearances_by_link": {"in": 1}, "unresolved_inside_disappearances": 1,
                   "physical_link_residence": {"in": {"inside": True, "ttt_veh_h": 1., "slow_veh_h": .5}}, "ttt_veh_h": 1.}
        self.assertEqual(spatial_checks(metrics, {"in", "terminal"}, {"out"}, {"terminal"})[0]["events"], 1)
        bad = copy.deepcopy(metrics)
        bad["exit_events_by_observed_link_pair"] = {"in->terminal": 1}
        with self.assertRaisesRegex(ValueError, "outside-boundary"):
            spatial_checks(bad, {"in", "terminal"}, {"out"}, {"terminal"})


if __name__ == "__main__":
    unittest.main()
