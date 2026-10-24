"""An observed empty stopline queue is not a missing observation."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers.observation_projection import configure_kinematic_queue_projection, ProjectionError


class ContiguousZeroQueueTest(unittest.TestCase):
    def setUp(self):
        self.raw={'local_observation':{'queue_bin_m':7.,'queue_bins':{
            'road|1|14':[1,0],'road|1|13':[1,1],'road|1|12':[1,1]},
            'link_counts':{'road':3.},'link_stopped_counts':{'road':2.}}}
        ctx=patch.object(adapter,'_link_lengths_m',return_value={'road':105.})
        ctx.start();self.addCleanup(ctx.stop)
        for key in ('_CFG_SWITCHES','_CFG_STRINGS'):
            ctx=patch.dict(getattr(adapter,key),{},clear=True);ctx.start();self.addCleanup(ctx.stop)

    def test_known_moving_front_is_zero_not_stopped_replacement(self):
        self.assertEqual(adapter._contiguous_stopline_queue(self.raw,zero_links={'road'}),{'road':0.})

    def test_unconfigured_legacy_path_stays_unchanged(self):
        self.assertEqual(adapter._contiguous_stopline_queue(self.raw),{})

    def test_observed_stopped_group_far_from_head_is_zero(self):
        self.raw['local_observation']['queue_bins']={'road|1|1':[2,2]}
        self.assertEqual(adapter._contiguous_stopline_queue(self.raw,zero_links={'road'}),{'road':0.})

    def test_absent_bins_do_not_invent_known_zero(self):
        self.raw['local_observation']['queue_bins']={}
        self.assertEqual(adapter._contiguous_stopline_queue(self.raw,zero_links={'road'}),{})

    def test_positive_queue_and_unrelated_link_are_unchanged(self):
        self.raw['local_observation']['queue_bins']={'road|1|14':[2,2],'road|1|13':[1,0],'other|1|1':[1,0]}
        self.assertEqual(adapter._contiguous_stopline_queue(self.raw,zero_links={'road'}),{'road':2.})

    def test_zero_projection_keeps_all_cars_and_stopped_residual(self):
        adapter.install_config_switches({'urban':{'queue':{'stopped_split':True,'contiguous':True}}})
        cfg=SimpleNamespace(network=SimpleNamespace(urban_link_storage_veh={'approach':100.},
            off_ramp_storage_link={},urban_movements={'turn':{'origin':'approach','beta':1.}},
            ramps=[],freeway_links=[],freeway_segments_per_link=0,freeway_segment_length_km=.5,
            freeway_lanes=3.,v_free=100.,kinematic_queue_zero_links={'road'}))
        mapping={'link_to_origins':{'road':['approach']},'link_to_movements':{'road':[{'movement':'turn','weight':1.}]}}
        d=adapter.build_local_observation_summary(self.raw,cfg,mapping)
        self.assertEqual(d['urban_movement_queue']['turn'],0.)
        self.assertEqual(d['urban_link_storage_occupancy']['approach'],3.)
        self.assertEqual(d['urban_link_storage_stopped']['approach'],2.)


class KinematicQueueCoverageTest(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        folder=Path(temp.name);network=folder/'network.inpx';network.write_bytes(b'fixture network')
        digest=hashlib.sha256(network.read_bytes()).hexdigest()
        contract=folder/'contract.json';contract.write_text(json.dumps(dict(schema='kinematic-urban-arrival/v1',
            network=dict(path=str(network),sha256=digest),sources={'origin':{'link':'road'}})),encoding='utf-8')
        self.cfg=SimpleNamespace(network=SimpleNamespace())
        self.tuning={'urban':{'queue':{'contiguous':True},'arrival':{'kinematic_contract':str(contract)}}}
        self.raw={'vehicle_records':{'complete':True,'records':[{'link_no':'road','stopped':True}]},
                  'local_observation':{'queue_bins':{'road|1|1':[1,1]}}}
        ctx=patch('evaluation.controllers.network_provenance.snapshot_network_sha256',return_value=digest)
        ctx.start();self.addCleanup(ctx.stop)

    def configure(self):
        return configure_kinematic_queue_projection(self.cfg,self.tuning,self.raw)

    def test_scope_is_exactly_the_existing_contract(self):
        self.assertEqual(self.configure(),{'kinematic_observed_zero_queue_links':['road']})
        self.assertEqual(self.cfg.network.kinematic_queue_zero_links,{'road'})

    def test_disabled_clears_scope_and_preserves_legacy_behavior(self):
        self.configure()
        self.assertEqual(configure_kinematic_queue_projection(self.cfg,{},{}),{})
        self.assertFalse(hasattr(self.cfg.network,'kinematic_queue_zero_links'))

    def test_missing_observation_is_not_zero(self):
        self.raw['local_observation']['queue_bins']={}
        with self.assertRaises(ProjectionError):self.configure()

    def test_incomplete_frame_rejected(self):
        self.raw['vehicle_records']['complete']=False
        with self.assertRaises(ProjectionError):self.configure()

    def test_stopped_count_mismatch_rejected(self):
        self.raw['local_observation']['queue_bins']['road|1|1']=[1,0]
        with self.assertRaises(ProjectionError):self.configure()

    def test_noncontiguous_definition_rejected(self):
        self.tuning['urban']['queue']['contiguous']=False
        with self.assertRaises(ProjectionError):self.configure()


if __name__=='__main__':unittest.main()
