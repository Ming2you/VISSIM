"""Regression for native OFF logs disagreeing with COM GREEN overrides."""
import csv
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.analyze_actuation import readback_intervals, signal_intervals


class ReadbackTests(unittest.TestCase):
    def test_native_off_is_distinct_from_checked_com_green(self):
        with tempfile.TemporaryDirectory() as directory:
            lsa, com = Path(directory) / "states.lsa", Path(directory) / "signal.csv"
            lsa.write_text("1;0;9101;1;off;1;Fixed Time;0;\n")
            com.write_text("sim_sec,sc_no,sg_no,requested_state,readback_state,ok,stage\n"
                           "1,9101,1,GREEN,GREEN,1,immediate\n"
                           "30,9101,1,GREEN,GREEN,1,post_step\n"
                           "60,9101,1,GREEN,GREEN,1,post_step\n")
            native = signal_intervals(lsa, 60)
            checked, first, counts, errors = readback_intervals(com, 60)
            self.assertEqual(native, [(9101, 1, 1, 60, "off")])
            self.assertEqual(sum(end-start for _, _, start, end, aspect in checked if aspect == "green"), 59)
            self.assertEqual(first, {(9101, 1): 1})
            self.assertEqual(counts["post_step:green"], 2)
            self.assertEqual(errors, [])

    def test_readback_mismatch_is_retained_as_observed_aspect(self):
        with tempfile.TemporaryDirectory() as directory:
            com = Path(directory) / "signal.csv"
            com.write_text("sim_sec,sc_no,sg_no,requested_state,readback_state,ok,stage\n"
                           "10,1001,2,GREEN,RED,0,post_step\n")
            checked, _, _, errors = readback_intervals(com, 30)
            self.assertEqual(checked, [(1001, 2, 10, 30, "red")])
            self.assertEqual(len(errors), 1)


if __name__ == "__main__":
    unittest.main()
