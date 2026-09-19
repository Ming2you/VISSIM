"""Reject unsafe combinations before an audit optimization can be installed."""
import copy
import pickle
from types import SimpleNamespace
import unittest
from evaluation.controllers.area_runtime import configure_final_audit_optimizations as configure
from evaluation.controllers.area_runtime import configure_compact_signal_clock


class FinalAuditOptimizationConfig(unittest.TestCase):
    def config(self):
        return {'control_area_objective': {'reuse_final_audit_physical_proofs': True,
            'audit_response_pipeline': True,
            'response_scheduling': {'lookahead': 8, 'final_check_reserve_sec': 30.}},
            'adapter': {'joint_owner_game': {'defer_candidate_final_audit': True,
                'ignore_wall_time_limits': True, 'response_cache_enabled': True,
                'response_parallel_workers': 8}}}

    def test_absent_options_preserve_default_object_bytes(self):
        network = SimpleNamespace(existing={'unchanged': 4})
        before = pickle.dumps(network, protocol=5)
        configure(network, {})
        self.assertEqual(pickle.dumps(network, protocol=5), before)

    def test_both_install_and_explicit_off_clears_previous_flags(self):
        network = SimpleNamespace()
        configure(network, self.config())
        self.assertTrue(network.control_area_reuse_final_audit_physical_proofs)
        self.assertTrue(network.control_area_audit_response_pipeline)
        configure(network, {'control_area_objective': {'reuse_final_audit_physical_proofs': False,
                                                      'audit_response_pipeline': False}})
        self.assertEqual(vars(network), {})

    def test_pipeline_rejects_each_missing_required_contract_atomically(self):
        paths = (('adapter', 'joint_owner_game', 'defer_candidate_final_audit'),
                 ('adapter', 'joint_owner_game', 'ignore_wall_time_limits'),
                 ('adapter', 'joint_owner_game', 'response_cache_enabled'),
                 ('control_area_objective', 'reuse_final_audit_physical_proofs'))
        for path in paths:
            with self.subTest(path=path):
                cfg = self.config(); target = cfg
                for key in path[:-1]: target = target[key]
                target[path[-1]] = False
                network = SimpleNamespace(marker=17)
                with self.assertRaises(ValueError): configure(network, cfg)
                self.assertEqual(vars(network), {'marker': 17})
        for workers in (0, 1, True, 8., 16):
            with self.subTest(workers=workers):
                cfg = self.config()
                cfg['adapter']['joint_owner_game']['response_parallel_workers'] = workers
                with self.assertRaises(ValueError): configure(SimpleNamespace(), cfg)

    def test_flags_are_strict_booleans(self):
        for name in ('reuse_final_audit_physical_proofs', 'audit_response_pipeline'):
            for value in (None, 0, 1, 'true', []):
                with self.subTest(name=name, value=value):
                    cfg = self.config(); cfg['control_area_objective'][name] = value
                    with self.assertRaises(ValueError): configure(SimpleNamespace(), cfg)

    def test_pipeline_rejects_unbounded_or_invalid_scheduling(self):
        for value in (None, {}, {'lookahead': 0, 'final_check_reserve_sec': 30.}):
            cfg = self.config(); cfg['control_area_objective']['response_scheduling'] = value
            with self.assertRaises(ValueError): configure(SimpleNamespace(), cfg)
        cfg = self.config(); cfg['control_area_objective']['prefetch_complete_sweep_responses'] = True
        with self.assertRaises(ValueError): configure(SimpleNamespace(), cfg)

    def test_proof_reuse_alone_does_not_require_pipeline_or_unlimited(self):
        cfg = self.config(); cfg['control_area_objective']['audit_response_pipeline'] = False
        cfg['adapter']['joint_owner_game']['ignore_wall_time_limits'] = False
        network = SimpleNamespace(); configure(network, cfg)
        self.assertEqual(vars(network), {'control_area_reuse_final_audit_physical_proofs': True})

    def test_compact_clock_default_and_disable_preserve_configuration(self):
        network = SimpleNamespace(existing=4)
        before = pickle.dumps(network, protocol=5)
        configure_compact_signal_clock(network, {})
        self.assertEqual(pickle.dumps(network, protocol=5), before)
        configure_compact_signal_clock(network, {'control_area_objective': {'compact_signal_clock_cache': True}})
        self.assertTrue(network.control_area_compact_signal_clock_cache)
        configure_compact_signal_clock(network, {'control_area_objective': {'compact_signal_clock_cache': False}})
        self.assertEqual(pickle.dumps(network, protocol=5), before)

    def test_compact_clock_rejects_nonboolean(self):
        for value in (None, 0, 1, 'true', []):
            with self.subTest(value=value), self.assertRaises(ValueError):
                configure_compact_signal_clock(SimpleNamespace(), {'control_area_objective': {'compact_signal_clock_cache': value}})


if __name__ == '__main__':
    unittest.main()
