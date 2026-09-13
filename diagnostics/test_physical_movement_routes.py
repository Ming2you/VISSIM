"""Physical routing and stock-preserving re-projection regression tests."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
from diagnostics.probe_physical_movement_routes import case, EVIDENCE
from evaluation.controllers.physical_movement_routes import configure_topology_repair, load_evidence, path_membership
from evaluation.controllers.network_provenance import snapshot_network_sha256


class PhysicalRoutesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report, cls.join, cls.inputs, cls.data = case('codex_n7_s13_6056c94_20260909', 3300)

    def test_real_3300_positive_unknown_flow_is_resolved_without_weight_guess(self):
        self.assertAlmostEqual(sum(self.report['unresolved_before'].values()), 2.008212, places=6)
        self.assertEqual(set(self.report['unresolved_after_path_join_only']), {'SC107_S_to_N_SC1'})
        self.assertEqual(self.report['unresolved_after_topology_repair'], {})
        self.assertGreater(self.join['counts']['no_match'], 0)  # do not invent inactive unknown routes

    def test_real_900_path_join_resolves_unknown_without_changing_routing(self):
        report, _, _, _ = case('codex_nc_s13_6056c94_20260909_retry', 900)
        self.assertAlmostEqual(sum(report['unresolved_before'].values()), 0.536848, places=6)
        self.assertEqual(report['unresolved_after_path_join_only'], {})
        self.assertEqual(report['unresolved_after_topology_repair'], {})
        self.assertEqual(report['model_stock_delta'], 0)

    def test_queue_reprojection_closes_mass_and_respects_passed_right_branch(self):
        _, old, _, _, _, _, new, _ = self.data
        self.assertEqual(self.report['model_stock_delta'], 0)
        self.assertEqual(old.urban_movement_queue['SC107_S_to_N_SC1'], 1)
        self.assertNotIn('SC107_S_to_N_SC1', new.urban_movement_queue)
        self.assertEqual(new.urban_movement_queue['SC107_S_to_E_SC108'], 0)
        self.assertEqual(new.urban_movement_queue['SC107_S_to_W_SC1004'], 2)
        self.assertEqual(new.urban_movement_queue['SC107_S_to_W_SC1005'], 2)

    def test_native_prior_approach_sum_and_distinct_real_bypass_receivers(self):
        betas = self.report['repair_metadata']['native_route_betas']
        self.assertAlmostEqual(sum(betas.values()), 1)
        self.assertAlmostEqual(betas['SC107_S_to_E_SC108'], 202 / 481)
        self.assertAlmostEqual(betas['SC107_S_to_W_SC1004'], 279 / 481 / 2)
        self.assertEqual(self.join['by_movement']['SC107_S_to_W_SC1004']['physical_turns'][0]['path'][-1], '10501')
        self.assertEqual(self.join['by_movement']['SC1004_S_to_E_SC107']['physical_turns'][0]['path'][-1], '10621')

    def test_through_and_external_right_with_same_compass_are_separate(self):
        straight = self.join['by_movement']['SC107_W_SC1005_to_E_SC108']
        right = self.join['by_movement']['SC107_W_SC1005_to_S']
        self.assertEqual(straight['outward_crossings_per_accepted_vehicle'], 0)
        self.assertEqual(right['outward_crossings_per_accepted_vehicle'], 1)
        self.assertEqual(straight['physical_turns'][0]['path'][1], '10023')
        self.assertEqual(right['physical_turns'][0]['path'][1], '10616')

    def test_flag_absent_preserves_objects_and_state(self):
        cfg, _, detectors, tuning, *_ = self.data
        before = copy.deepcopy(vars(cfg.network))
        result, metadata = configure_topology_repair(cfg, detectors, tuning)
        self.assertIs(result, detectors)
        self.assertEqual(metadata, {})
        self.assertEqual(vars(cfg.network), before)

    def test_unreviewed_observation_support_fails_before_mutation(self):
        cfg, _, detectors, tuning, raw, *_ = self.data
        cfg, detectors, tuning = copy.deepcopy(cfg), copy.deepcopy(detectors), copy.deepcopy(tuning)
        detectors['link_to_movements']['379'] = [{'movement': 'SC107_S_to_N_SC1', 'weight': 1}]
        tuning.setdefault('urban', {}).setdefault('movements', {})['physical_route_topology'] = EVIDENCE
        with self.assertRaisesRegex(ValueError, 'unreviewed physical link'):
            configure_topology_repair(cfg, detectors, tuning, state_json=raw)
        self.assertIn('SC107_S_to_N_SC1', cfg.network.urban_movements)

    def test_warm_vendor_identity_caches_are_evicted_for_the_changed_network(self):
        from src.models import urban_queue_model as uqm
        cfg, _, detectors, tuning, raw, *_ = self.data
        cfg, tuning = copy.deepcopy(cfg), copy.deepcopy(tuning)
        tuning.setdefault('urban', {}).setdefault('movements', {})['physical_route_topology'] = EVIDENCE
        self.assertIn('SC107_S_to_N_SC1', uqm.movement_specs(cfg))
        uqm._legacy_sync_index(cfg)
        self.assertIs(uqm._SYNC_INDEX_NET, cfg.network)
        configure_topology_repair(cfg, detectors, tuning, state_json=raw)
        self.assertIsNone(uqm._SYNC_INDEX_NET)
        self.assertNotIn('SC107_S_to_N_SC1', uqm.movement_specs(cfg))
        uqm._legacy_sync_index(cfg)
        self.assertEqual(uqm._SYNC_COUNTS[0], 370)

    def test_path_requires_native_edges_and_known_membership(self):
        document, _, _ = load_evidence(EVIDENCE)
        document['by_movement']['SC107_S_to_E_SC108']['path'] = ['379', '1220042300']
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'bad.json'
            path.write_text(json.dumps(document), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'disconnected'):
                load_evidence(path)
        with self.assertRaisesRegex(ValueError, 'membership missing'):
            path_membership(['a', 'unknown'], {'a': True})
        result = path_membership(['a', 'b', 'c'], {'a': True, 'b': False, 'c': True})
        self.assertEqual((result['outward_crossings_per_vehicle'], result['inward_crossings_per_vehicle']), (1, 1))

    def test_physical_generation_membership_uses_input_not_gate_name(self):
        routes = self.inputs['routes']
        self.assertFalse(routes['input:gate:in_SC107_S']['target_inside'])
        self.assertTrue(routes['input:gate:in_SC1001_W']['target_inside'])
        self.assertEqual(routes['input:gate:in_SC1_S']['physical_sources'][0]['link'], '1220042300')
        for ramp in ['R_D_W', 'R_D_E', 'R_F_W', 'R_F_E']:
            self.assertTrue(routes['input:ramp:' + ramp]['target_inside'])
            self.assertEqual(routes['input:ramp:' + ramp]['native_inputs_on_receiving_links'], [])

    def test_real_manifest_read_and_mismatched_run_id_fail(self):
        raw = self.data[4]
        expected = self.inputs['network']['sha256']
        self.assertEqual(snapshot_network_sha256(raw), expected)
        bad = copy.deepcopy(raw)
        bad['run_provenance']['run_id'] = 'different'
        with self.assertRaisesRegex(ValueError, 'run IDs differ'):
            snapshot_network_sha256(bad)


if __name__ == '__main__':
    unittest.main()
