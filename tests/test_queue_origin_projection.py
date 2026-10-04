"""Observed queues must stay on their physical approach when filtering is enabled."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from evaluation.controllers import vissim_stackelberg_adapter as adapter


class QueueOriginProjectionTests(unittest.TestCase):
    def setUp(self):
        for name in ('_CFG_SWITCHES', '_CFG_STRINGS'):
            context = patch.dict(getattr(adapter, name), {}, clear=True)
            context.start()
            self.addCleanup(context.stop)

    def project(self, enabled=None):
        queue = {} if enabled is None else {'origin_filter': enabled}
        metadata = adapter.install_config_switches({'urban': {'queue': queue}})
        movements = {
            'own': {'origin': 'south_approach', 'beta': 1.},
            'opposite': {'origin': 'north_approach', 'beta': 1.},
            'phantom': {'origin': 'unconnected_boundary', 'beta': 1.},
        }
        cfg = SimpleNamespace(network=SimpleNamespace(
            urban_link_storage_veh={'south_approach': 100., 'north_approach': 100.},
            off_ramp_storage_link={}, urban_movements=movements, ramps=[],
            freeway_links=[], freeway_segments_per_link=0,
            freeway_segment_length_km=.5, freeway_lanes=3., v_free=100.))
        mapping = {'link_to_origins': {'road': ['south_approach']},
                   'link_to_movements': {'road': [
                       {'movement': m, 'weight': 1.} for m in movements]}}
        raw = {'local_observation': {'link_counts': {'road': 6.},
                                    'link_stopped_counts': {'road': 3.}}}
        return metadata, adapter.build_local_observation_summary(raw, cfg, mapping, None)

    def test_explicit_switch_reaches_existing_projection_filter(self):
        metadata, _ = self.project(True)
        self.assertTrue(adapter._queue_origin_filter_enabled())
        self.assertEqual(metadata['cfg_switch_queue_origin_filter'], 1.)

    def test_no_queue_is_assigned_to_opposite_or_unconnected_approach(self):
        _, before = self.project(False)
        _, after = self.project(True)
        a, b = before['urban_movement_queue'], after['urban_movement_queue']
        self.assertGreater(a['phantom'], 0.)
        self.assertGreater(b['own'], 0.)
        self.assertEqual(b['opposite'], 0.)
        self.assertEqual(b['phantom'], 0.)
        self.assertAlmostEqual(sum(a.values()), sum(b.values()))
        self.assertEqual(before['urban_link_storage_occupancy'], after['urban_link_storage_occupancy'])

    def test_missing_option_keeps_legacy_projection(self):
        _, absent = self.project()
        _, disabled = self.project(False)
        self.assertEqual(absent['urban_movement_queue'], disabled['urban_movement_queue'])
        self.assertEqual(absent['urban_link_storage_occupancy'], disabled['urban_link_storage_occupancy'])


if __name__ == '__main__':
    unittest.main()
