"""A queue at a different native signal is not ready for a downstream green."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from evaluation.controllers import observation_projection as projection
from evaluation.controllers import vissim_stackelberg_adapter as adapter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/expanded036_9000_20260930/loss_onset2250/source_sc101'


class UpstreamQueueReadinessTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'contract.json'
        self.doc = json.loads((SOURCE/'head_lane_support.json').read_bytes())
        authority = json.loads((ROOT/self.doc['authority']['path']).read_bytes())['network']
        self.cfg = SimpleNamespace(network=SimpleNamespace(
            urban_movements=copy.deepcopy(authority['urban_movements']),
            urban_link_storage_veh=copy.deepcopy(authority['urban_link_storage_veh']),
            off_ramp_storage_link={},ramps=[],freeway_links=[],freeway_segments_per_link=0,
            freeway_segment_length_km=.5,freeway_lanes=3.,v_free=100.))
        self.doc['upstream_stoplines'] = {'1210008501':dict(storage='SC1_to_SC101',
            downstream_approach='1220011503',signal_groups=['15 3','15 8'])}
        self.tuning = {'urban':{'queue':{'attribution':'head_phase','head_lane_contract':str(self.path)}}}
        for name in ('_CFG_SWITCHES','_CFG_STRINGS'):
            ctx=patch.dict(getattr(adapter,name),{},clear=True);ctx.start();self.addCleanup(ctx.stop)

    def configure(self):
        self.path.write_text(json.dumps(self.doc),encoding='utf-8')
        with patch('evaluation.controllers.network_provenance.snapshot_network_sha256',
                   return_value=self.doc['network']['sha256']):
            return projection.configure_head_queue_lanes(self.cfg,self.tuning,{})

    def project(self,origin='SC1_to_SC101'):
        adapter.install_config_switches({'urban':{'queue':{'stopped_split':True,'origin_filter':True}}})
        names=[n for n,s in self.cfg.network.urban_movements.items() if s['origin']=='SC1_to_SC101']
        mapping={'link_to_origins':{'1210008501':[origin],'1220011503':['SC1_to_SC101']},
                 'link_to_movements':{road:[{'movement':n,'weight':1.} for n in names]
                                      for road in ('1210008501','1220011503')}}
        raw={'local_observation':{'link_counts':{'1210008501':15.,'1220011503':43.},
                                 'link_stopped_counts':{'1210008501':15.,'1220011503':5.}}}
        return adapter.build_local_observation_summary(raw,self.cfg,mapping,None)

    def test_other_signal_queue_is_kept_in_existing_storage_without_vehicle_loss(self):
        before=self.project()
        self.configure()
        after=self.project()
        self.assertAlmostEqual(sum(before['urban_movement_queue'].values()),20.)
        self.assertAlmostEqual(sum(after['urban_movement_queue'].values()),5.)
        self.assertAlmostEqual(after['urban_link_storage_occupancy']['SC1_to_SC101'],53.)
        self.assertAlmostEqual(sum(after['urban_link_storage_occupancy'].values())+
                               sum(after['urban_movement_queue'].values()),58.)
        self.assertEqual(after['projection_diagnostics']['upstream_signal_queue_links'],['1210008501'])

    def test_without_declared_upstream_source_projection_remains_identical(self):
        before=self.project()
        self.doc.pop('upstream_stoplines')
        self.configure()
        after=self.project()
        self.assertEqual(before['urban_movement_queue'],after['urban_movement_queue'])
        self.assertEqual(before['urban_link_storage_occupancy'],after['urban_link_storage_occupancy'])

    def test_rebound_storage_mapping_is_rejected(self):
        self.configure()
        with self.assertRaises(projection.ProjectionError):self.project(origin='SC5_to_SC101')

    def test_insufficient_storage_rejects_instead_of_losing_upstream_vehicles(self):
        self.configure()
        self.cfg.network.urban_link_storage_veh['SC1_to_SC101']=10.
        with self.assertRaises(projection.ProjectionError):self.project()

    def test_claimed_signal_groups_must_match_all_native_heads(self):
        self.doc['upstream_stoplines']['1210008501']['signal_groups']=['15 8']
        with self.assertRaises(projection.ProjectionError):self.configure()

    def test_canonical_approach_cannot_be_called_an_upstream_stopline(self):
        self.doc['upstream_stoplines']['1220011503']=self.doc['upstream_stoplines'].pop('1210008501')
        with self.assertRaises(projection.ProjectionError):self.configure()

    def test_storage_must_be_the_canonical_downstream_origin(self):
        self.doc['upstream_stoplines']['1210008501']['storage']='SC5_to_SC101'
        with self.assertRaises(projection.ProjectionError):self.configure()

    def test_unconfigured_contract_clears_previous_upstream_support(self):
        self.configure()
        self.assertEqual(self.cfg.network.head_queue_upstream_storage,{'1210008501':'SC1_to_SC101'})
        projection.configure_head_queue_lanes(self.cfg,{}, {})
        self.assertFalse(hasattr(self.cfg.network,'head_queue_upstream_storage'))


if __name__=='__main__': unittest.main()
