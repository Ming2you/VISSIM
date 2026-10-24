"""Regression guards for reusing a baseline with the same native endpoint."""
import json
import unittest
from pathlib import Path
from diagnostics.sdmpc_n31_20260924.integration_20260926.native_pair1200.analyze_pair import controlled_reuse_metadata, controlled_reuse_area, ROOT


class ScopeTests(unittest.TestCase):
    def test_completed_actual_prediction_at_equal_endpoint(self):
        prediction = json.loads((Path(__file__).parent/'forecast2400/summary.json').read_bytes())
        result, limits = controlled_reuse_metadata(dict(start_sec=2400,end_sec=2850), prediction, 2850)
        self.assertEqual(result['predicted_delta_omega_veh_h'], prediction['delta_omega_veh_h'])
        self.assertIsNone(result['predicted_delta_tracked_total_veh_h'])
        self.assertTrue(any('2400..2850' in x for x in limits))
        self.assertFalse(any('4650' in x or '9000' in x for x in limits))

    def test_legacy_censored_baseline_keeps_outside_cost(self):
        result, limits = controlled_reuse_metadata(dict(start_sec=4650,end_sec=5100),
            dict(delta_omega_ttt_veh_h=-3,delta_tracked_outside_veh_h=5),9000)
        self.assertEqual(result['predicted_delta_tracked_total_veh_h'],2)
        self.assertTrue(any('not5100s' in x for x in limits))

    def test_incomplete_baseline_rejected(self):
        with self.assertRaises(AssertionError):
            controlled_reuse_metadata(dict(start_sec=2400,end_sec=2850),dict(delta_omega_veh_h=0),2700)

    def test_conflicting_or_missing_prediction_rejected(self):
        for prediction in ({},dict(delta_omega_veh_h=1,delta_omega_ttt_veh_h=2),dict(delta_omega_veh_h=float('nan'))):
            with self.subTest(prediction=prediction), self.assertRaises(AssertionError):
                controlled_reuse_metadata(dict(start_sec=2400,end_sec=2850),prediction,2850)

    def test_reused_area_is_the_actual_pinned_model_area(self):
        protocol=json.loads((ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/native_urbanrm269_10681only_2400/protocol.json').read_bytes())
        area=ROOT/'diagnostics/repin_v3c3_review_20261001/urban_area263/approaches_only/membership.json'
        result=controlled_reuse_area(protocol,area)
        self.assertEqual(len(result['model_configs']),1)
        with self.assertRaisesRegex(AssertionError,'areas differ'):
            controlled_reuse_area(protocol,ROOT/'different_area.json')
        model=result['model_configs'][0]['path']
        protocol['command_pins'][model]='0'*64
        with self.assertRaises(AssertionError):
            controlled_reuse_area(protocol,area)


if __name__=='__main__':
    unittest.main()
