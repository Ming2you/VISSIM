import unittest
import hashlib
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from evaluation.controllers.observation_projection import (
    ProjectionError, configure_head_queue_lanes, head_phase_queue_weights)
from evaluation.controllers import vissim_stackelberg_adapter as adapter


class HeadPhaseQueueProjectionTest(unittest.TestCase):
    def setUp(self):
        self.entries = [('through', 1.), ('right', 1.), ('left', 1.)]
        self.specs = {'through': {'phase': 'SC1001_p1'}, 'right': {'phase': 'SC1001_p1'},
                      'left': {'phase': 'SC1001_p2'}}
        self.heads = {('40', 'p1'): [{'lane': 3, 'sc': '1001'}],
                      ('40', 'p2'): [{'lane': 4, 'sc': '1001'}]}
        self.lanes = {('40', '3'): 8., ('40', '4'): 66.}

    def project(self, count=74., entries=None, lanes=None, heads=None):
        return head_phase_queue_weights('40', count, entries or self.entries, self.specs,
                                        self.lanes if lanes is None else lanes,
                                        self.heads if heads is None else heads)

    def test_observed_left_queue_is_not_split_into_other_phase(self):
        values, audit = self.project()
        self.assertEqual(values, [4., 4., 66.])
        self.assertEqual(sum(values), 74.)
        self.assertEqual(audit['head_phase_supported_veh'], 74.)
        self.assertEqual(audit['legacy_fallback_veh'], 0.)

    def test_shared_phase_keeps_existing_relative_weights(self):
        values, _ = self.project(entries=[('through', 3.), ('right', 1.), ('left', 1.)])
        self.assertEqual(values, [6., 2., 66.])

    def test_unknown_head_retains_mass_and_reports_fallback(self):
        values, audit = self.project(count=77., lanes={**self.lanes, ('40', '1'): 3.})
        self.assertEqual(values, [5., 5., 67.])
        self.assertEqual(audit['legacy_fallback_veh'], 3.)

    def test_duplicate_alias_entries_do_not_duplicate_queue(self):
        values, _ = self.project(entries=[('through', 1.), ('left', 1.), ('left', 1.)])
        self.assertEqual(values, [8., 33., 33.])

    def test_ambiguous_head_does_not_invent_phase(self):
        heads = {('40', 'p1'): [{'lane': 3, 'sc': '1001'}, {'lane': 4, 'sc': '1001'}],
                 ('40', 'p2'): [{'lane': 4, 'sc': '1001'}]}
        values, audit = self.project(heads=heads)
        self.assertEqual(values, [26., 26., 22.])
        self.assertEqual(audit['legacy_fallback_veh'], 66.)

    def test_mass_mismatch_rejected(self):
        with self.assertRaises(ProjectionError):
            self.project(count=73.)

    def test_same_phase_on_disjoint_connector_lanes_keeps_through_queue(self):
        values, audit = head_phase_queue_weights('40',74.,self.entries,self.specs,
            self.lanes,self.heads,movement_lanes={'through':[3],'right':[1],'left':[4]})
        self.assertEqual(values,[8.,0.,66.])
        self.assertEqual(audit['connector_lane_supported_veh'],74.)

    def test_shared_connector_lane_does_not_invent_destination(self):
        values, _ = head_phase_queue_weights('40',74.,[('through',3.),('right',1.),('left',1.)],
            self.specs,self.lanes,self.heads,movement_lanes={'through':[3],'right':[3],'left':[4]})
        self.assertEqual(values,[6.,2.,66.])

    def test_partial_connector_support_is_rejected(self):
        with self.assertRaises(ProjectionError):
            head_phase_queue_weights('40',74.,self.entries,self.specs,self.lanes,self.heads,
                                     movement_lanes={'through':[3],'left':[4]})

    def test_head_and_connector_disagreement_is_rejected(self):
        with self.assertRaises(ProjectionError):
            head_phase_queue_weights('40',74.,self.entries,self.specs,self.lanes,self.heads,
                                     movement_lanes={'through':[1],'right':[1],'left':[4]})

    def test_default_contiguous_queue_still_sums_lane_walks(self):
        bins = {f'40|4|{i}': [1, 1] for i in range(113, 179)}
        bins.update({f'40|3|{i}': [1, 1] for i in range(171, 179)})
        bins['40|4|112'] = [1, 0]
        bins['40|3|170'] = [1, 0]
        state = {'local_observation': {'queue_bin_m': 7., 'queue_bins': bins}}
        with patch.object(adapter, '_link_lengths_m', return_value={'40': 1258.}):
            self.assertEqual(adapter._contiguous_stopline_queue(state), {'40': 74.})
            self.assertEqual(adapter._contiguous_stopline_queue(state, per_lane=True), self.lanes)


class HeadLaneContractTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.network = self.root/'network.inpx'
        self.network.write_text('<network><links><link no="101"><fromLinkEndPt lane="29 2"/>'
            '<toLinkEndPt lane="31 1"/><lanes><lane/><lane/></lanes></link></links></network>')
        self.spec = dict(signal='SC1',phase='SC1_p3',origin='from29',receiving_link='to31',kind='urban')
        self.cfg = SimpleNamespace(network=SimpleNamespace(urban_movements={'through':dict(self.spec)}))
        authority = self.root/'authority.json'
        authority.write_text(json.dumps({'network':{'urban_movements':{'through':self.spec},
            'control_area_routes':{'movement:through':{'physical_turns':[dict(from_link='29',
                connector='101',to_link='31',source_evidence={'canonical_approach_leg':True})]}}}}))
        def pin(path):
            return dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        self.document = dict(schema='head-queue-lane-support/v1',network=pin(self.network),
            authority=pin(authority),movements={'through':dict(from_link='29',connector='101',
                to_link='31',lanes=[2,3],expected_spec=self.spec)})
        self.contract = self.root/'contract.json'
        self.tuning = {'urban':{'queue':{'attribution':'head_phase','head_lane_contract':str(self.contract)}}}

    def load(self, observed_hash=None):
        self.contract.write_text(json.dumps(self.document))
        with patch('evaluation.controllers.network_provenance.snapshot_network_sha256',
                   return_value=observed_hash or self.document['network']['sha256']):
            return configure_head_queue_lanes(self.cfg,self.tuning,{})

    def test_pinned_geometry_installs_only_documented_road(self):
        result = self.load()
        self.assertEqual(self.cfg.network.head_queue_movement_lanes,{'29':{'through':[2,3]}})
        self.assertEqual(result['head_queue_lane_links'],1)

    def test_unconfigured_path_clears_stale_optional_support(self):
        self.load()
        self.assertEqual(configure_head_queue_lanes(self.cfg,{},{}),{})
        self.assertFalse(hasattr(self.cfg.network,'head_queue_movement_lanes'))

    def test_changed_network_bytes_are_rejected(self):
        self.network.write_text('<different/>')
        with self.assertRaises(ProjectionError):
            self.load()

    def test_other_observation_network_is_rejected(self):
        with self.assertRaises(ProjectionError):
            self.load(observed_hash='0'*64)

    def test_rebound_movement_is_rejected(self):
        self.cfg.network.urban_movements['through']['receiving_link']='different'
        with self.assertRaises(ProjectionError):
            self.load()

    def test_wrong_connector_lane_claim_is_rejected(self):
        self.document['movements']['through']['lanes']=[1,2]
        with self.assertRaises(ProjectionError):
            self.load()


if __name__ == '__main__':
    unittest.main()
