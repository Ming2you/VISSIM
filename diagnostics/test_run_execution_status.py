import unittest

from scripts.analyze_control_run import execution_status


class ExecutionStatusTests(unittest.TestCase):
    def test_completed_simulation_with_unapplied_control_is_invalid(self):
        status = execution_status("ERROR=DECISION_EXIT_NONZERO sim_sec=900 exit=1\nSTAGE=SIM_DONE\n", 5400, 5400)
        self.assertFalse(status["completed_without_reported_errors"])
        self.assertEqual(status["runner_error_count"], 1)

    def test_clean_and_failed_readback_are_distinct(self):
        clean = "STAGE=SIM_DONE\nSIGNAL_READBACK_FAIL=0\n"
        self.assertTrue(execution_status(clean, 5400, 5400)["completed_without_reported_errors"])
        self.assertFalse(execution_status(clean.replace("FAIL=0", "FAIL=1"), 5400, 5400)["completed_without_reported_errors"])
        self.assertFalse(execution_status(clean, 5370, 5400)["completed_without_reported_errors"])


if __name__ == "__main__":
    unittest.main()
