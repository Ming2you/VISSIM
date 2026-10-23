"""Qualification gates for reusing the completed same-endpoint native cache."""
import ast
import copy
import unittest
import analyze_multizone as target


class CacheQualification(unittest.TestCase):
    def setUp(self):
        self.protocol = target.read(target.PROTOCOL)
        self.baseline = target.read(target.BASE / 'summary.json')

    def test_existing_same_area_endpoint_and_history(self):
        target.validate_cache(self.protocol, self.baseline)

    def test_longer_completed_baseline_cannot_supply_terminal_metrics(self):
        self.baseline['recorded_run_end_sec'] = 9000
        with self.assertRaises(AssertionError):
            target.validate_cache(self.protocol, self.baseline)

    def test_changed_measurement_area_is_rejected(self):
        self.baseline['physical_area']['sha256'] = 'different area'
        with self.assertRaises(AssertionError):
            target.validate_cache(self.protocol, self.baseline)

    def test_unqualified_observed_input_history_is_rejected(self):
        self.baseline['source_observed_model_inputs_exact'] = False
        with self.assertRaises(AssertionError):
            target.validate_cache(self.protocol, self.baseline)

    def test_scoped_adapter_keeps_native_and_initial_state_gates(self):
        self.assertEqual(target.sha(target.SOURCE), target.SOURCE_SHA)
        patched = target.transform(target.SOURCE.read_text(encoding='utf-8-sig'))
        ast.parse(patched)
        self.assertNotIn('prefix_digest(baseline_fzp', patched)
        self.assertIn("assert execution['native_execution_passed']", patched)
        self.assertIn("'Different actual initial vehicle state'", patched)
        self.assertIn("controlled_reuse_area(protocol, args.membership_json)", patched)
        self.assertIn("'Replay does not recover the same initial microscopic history", patched)


if __name__ == '__main__':
    unittest.main()
