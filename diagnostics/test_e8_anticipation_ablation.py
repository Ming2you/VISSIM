"""Check the diagnostic intervention and actual endpoint pairing, not a new model."""
import copy
import json
import os
from pathlib import Path
import unittest

from diagnostics.probe_e8_anticipation_ablation import (
    ROOT, accelerating_nu, positive_anticipation, trace_freeway, build_projected,
    adapter, endpoint, metanet, ControlAction, DemandStep, digest,
)


class AnticipationTests(unittest.TestCase):
    def test_sign_selection_and_original_off_equivalence(self):
        original = metanet.metanet_speed_update_kmh
        for rho, downstream in ((100.0, 30.0), (30.0, 100.0), (30.0, 30.0), (0.0, 0.0)):
            args = (5., 5., rho, downstream, 2., 10./3600, .513441, 18./3600, 30., 40., 5.)
            expected = original(*args)
            with positive_anticipation(1.0):
                self.assertEqual(metanet.metanet_speed_update_kmh(*args), expected)
            with positive_anticipation(0.0):
                actual = metanet.metanet_speed_update_kmh(*args)
            if downstream >= rho:
                self.assertEqual(actual, expected)
            else:
                self.assertEqual(actual, 5.0)
                self.assertGreater(expected, actual)
        self.assertIs(metanet.metanet_speed_update_kmh, original)

    def test_invalid_and_exception_restore(self):
        for value in (-.01, 1.01, float('nan')):
            with self.assertRaises(ValueError):
                accelerating_nu(100, 30, 30, value)
        original = metanet.metanet_speed_update_kmh
        with self.assertRaisesRegex(RuntimeError, "test restore"):
            with positive_anticipation(0.):
                raise RuntimeError("test restore")
        self.assertIs(metanet.metanet_speed_update_kmh, original)

    def test_actual_unwrapped_endpoint_matches_factor_one_trace(self):
        directory = ROOT / 'evaluation/runs/codex_n7_pure_s13_20260910/decisions_codex_n7_pure_s13_20260910'
        cfg, state, detectors, tuning, raw, _, _ = build_projected(
            ROOT/'evaluation/configs/n21_n7_20260908.json', directory/'state_003300.json',
            directory/'action_003150.json', fixture_inputs=False)
        action = adapter.control_from_json(directory/'action_003300.json', cfg, ControlAction)
        calibration = adapter.deep_update(dict(adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))), tuning.get('calibration_override', {}))
        demand = adapter.demand_from_state(raw, cfg, DemandStep, 1, calibration, detectors)
        initial = (cfg, state, action, demand)
        fingerprint = digest(initial)
        c1, s1, a1, d1 = copy.deepcopy(initial)
        plain = endpoint.evaluate_price_point(s1, a1, d1, (), endpoint.ObjectiveSpec(c1, depth_override=1, box_walk=False))
        c2, s2, a2, d2 = copy.deepcopy(initial)
        with positive_anticipation(1.0), trace_freeway(c2) as trace:
            wrapped = endpoint.evaluate_price_point(s2, a2, d2, (), endpoint.ObjectiveSpec(c2, depth_override=1, box_walk=False))
        self.assertEqual(len(trace), 15)
        self.assertEqual(plain.objective, wrapped.objective)
        self.assertEqual(digest(plain.states), digest(wrapped.states))
        self.assertEqual(digest(initial), fingerprint)

    def test_recorded_integrated_pairs_keep_first_flow_and_all_actions(self):
        for start in (1200, 3300):
            doc = json.loads((ROOT/f'diagnostics/e8_anticipation_integrated_{start}.json').read_text(encoding='utf-8'))
            base, alt = (doc['scenarios'][name] for name in ('canonical', 'positive_anticipation_zero'))
            self.assertEqual(len(base['rows']), 45)
            self.assertEqual(len(alt['rows']), 45)
            self.assertTrue(base['stock_closure_checked'] and alt['stock_closure_checked'])
            self.assertTrue(doc['source_unchanged'])
            # Flux uses old speed, so changing speed dynamics cannot change this
            # first density/accepted-flow step. It can change later substeps.
            self.assertEqual(base['rows'][0]['freeway_density'], alt['rows'][0]['freeway_density'])
            self.assertEqual([r['applied_action'] for r in base['rows']], [r['applied_action'] for r in alt['rows']])
            self.assertEqual(len({digest(r['applied_action']) for r in base['rows']}), 1)
            for value in (base, alt):
                for row in value['rows']:
                    self.assertTrue(all(v >= 0 for lanes in row['freeway_density'].values() for v in lanes))


if __name__ == '__main__':
    unittest.main()
