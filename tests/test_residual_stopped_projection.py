"""Queue stock and stopped residual stock must partition observed stopped cars."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from evaluation.controllers import vissim_stackelberg_adapter as adapter


class ResidualStoppedProjectionTest(unittest.TestCase):
    def setUp(self):
        for key in ('_CFG_SWITCHES','_CFG_STRINGS'):
            ctx=patch.dict(getattr(adapter,key),{},clear=True);ctx.start();self.addCleanup(ctx.stop)
        self.cfg=SimpleNamespace(network=SimpleNamespace(
            urban_link_storage_veh={'approach':100.},off_ramp_storage_link={},
            urban_movements={'turn':{'origin':'approach','beta':1.}},ramps=[],freeway_links=[],
            freeway_segments_per_link=0,freeway_segment_length_km=.5,freeway_lanes=3.,v_free=100.))
        self.mapping={'link_to_origins':{'road':['approach']},
                      'link_to_movements':{'road':[{'movement':'turn','weight':1.}]}}
        self.raw={'local_observation':{'link_counts':{'road':10.},'link_stopped_counts':{'road':6.}}}

    def project(self,contiguous=None,upstream=False,stopped=True):
        adapter.install_config_switches({'urban':{'queue':{'stopped_split':stopped,
                                                         'contiguous':contiguous is not None}}})
        if upstream:self.cfg.network.head_queue_upstream_storage={'road':'approach'}
        with patch.object(adapter,'_contiguous_stopline_queue',return_value={} if contiguous is None else {'road':contiguous}):
            return adapter.build_local_observation_summary(self.raw,self.cfg,self.mapping)

    def test_all_stopped_in_ready_queue_leaves_no_stopped_residual(self):
        d=self.project()
        self.assertEqual(d['urban_movement_queue']['turn'],6.)
        self.assertEqual(d['urban_link_storage_occupancy']['approach'],4.)
        self.assertEqual(d['urban_link_storage_stopped']['approach'],0.)

    def test_disconnected_stopped_cars_remain_in_residual(self):
        d=self.project(contiguous=4.)
        self.assertEqual(d['urban_movement_queue']['turn'],4.)
        self.assertEqual(d['urban_link_storage_occupancy']['approach'],6.)
        self.assertEqual(d['urban_link_storage_stopped']['approach'],2.)
        self.assertEqual(d['urban_link_storage_stopped']['approach']+d['urban_movement_queue']['turn'],6.)

    def test_upstream_native_queue_is_still_stopped_storage(self):
        d=self.project(contiguous=4.,upstream=True)
        self.assertEqual(d['urban_movement_queue']['turn'],0.)
        self.assertEqual(d['urban_link_storage_stopped']['approach'],6.)

    def test_constant_partition_retains_legacy_proportional_estimate(self):
        d=self.project(stopped=False)
        self.assertAlmostEqual(d['urban_link_storage_stopped']['approach'],d['urban_link_storage_occupancy']['approach']*.6)

    def test_queue_cannot_exceed_independent_observed_stopped_count(self):
        with self.assertRaises(ValueError):self.project(contiguous=7.)


if __name__=='__main__':unittest.main()
