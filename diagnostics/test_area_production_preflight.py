"""Check strict output validation and child identity without launching a solver."""
import unittest
from diagnostics.run_area_production_preflight import owned_descendants, validate_result


class PreflightTests(unittest.TestCase):
    def test_only_exact_root_or_still_owned_parent_extends_tree(self):
        root = {'pid': 10, 'parent': 1, 'created': 'a'}
        rows = {10: root, 20: {'pid': 20, 'parent': 10, 'created': 'b'},
                30: {'pid': 30, 'parent': 20, 'created': 'c'},
                40: {'pid': 40, 'parent': 99, 'created': 'd'}}
        owned = {}
        owned_descendants(rows, root, owned)
        self.assertEqual(set(owned), {20, 30})
        rows[10] = {**root, 'created': 'reused'}
        rows[50] = {'pid': 50, 'parent': 10, 'created': 'new-unrelated'}
        owned_descendants(rows, root, owned)
        self.assertNotIn(50, owned)

    def test_stale_reused_worker_pid_does_not_capture_unrelated_descendants(self):
        owned = {20: {'pid': 20, 'parent': 10, 'created': 'old'}}
        rows = {20: {'pid': 20, 'parent': 99, 'created': 'new'},
                30: {'pid': 30, 'parent': 20, 'created': 'unrelated'}}
        owned_descendants(rows, None, owned)
        self.assertNotIn(30, owned)

    def test_successful_json_with_wrong_or_missing_contract_is_rejected(self):
        metadata = {'controller_status': 'ok', 'physical_signal_contract_enabled': 1.,
                    'offset_writer': 'experiment', 'offset_experiment': 1.,
                    'offset_production_writes': 0., 'control_area_endpoint_enabled': 1.,
                    'control_area_near_only': 1., 'freeway_physical_vehicle_counts': 1.,
                    'control_area_beta_seconds': 300., 'meta_wu_price_parallel_serial_rerun_count': 0.,
                    'control_area_follower_objective_installed': 1., 'control_area_fallback_uses_objective': 1.,
                    'control_area_meter_finalization_enabled': 1., 'control_area_meter_writer_matches_scored': 1.,
                    'control_area_meter_context_sha256': 'context',
                    'meta_leader_fallback_guard_metric_ttt': 0., 'nash_objective': -10.,
                    'offset_written_sec': {'SC1': 0.}, 'decision_wall_sec': 1.}
        diagnostics = {'control_area_follower_objective_active': 1.,
                       'control_area_phase_outer_matches_scored': 1., 'control_area_meter_finalized_before_score': 1.,
                       '_control_area_meter_finalized': {'context_sha256': 'context', 'realized_rates': {'R': 600.}, 'commands': {}},
                       'control_area_follower_objective_veh_h': -10., 'control_area_follower_ttt_veh_h': 10.,
                       'control_area_follower_ttd_veh': 240., 'control_area_follower_additional_cost_veh_h': 0.}
        payload = {'metadata': metadata, 'diagnostics': diagnostics, 'ramp_metering': {'R': 600.}}
        validate_result(payload, 300)
        for key, bad in [('controller_status', 'fallback_fixed'), ('offset_writer', 'intent_only'),
                         ('physical_signal_contract_enabled', 0.), ('control_area_beta_seconds', 0.),
                         ('meta_wu_price_parallel_serial_rerun_count', 1.)]:
            with self.assertRaises(AssertionError):
                validate_result({**payload, 'metadata': {**metadata, key: bad}}, 300)
        with self.assertRaises(AssertionError):
            validate_result({**payload, 'diagnostics': {**diagnostics,
                            'control_area_follower_objective_veh_h': -30.}}, 300)
        for key in ('control_area_phase_outer_matches_scored', 'control_area_meter_finalized_before_score'):
            with self.assertRaises(AssertionError):
                validate_result({**payload, 'diagnostics': {**diagnostics,key:0.}}, 300)
        with self.assertRaises(AssertionError):
            validate_result({**payload,'ramp_metering':{'R':601.}},300)


if __name__ == '__main__':
    unittest.main()
