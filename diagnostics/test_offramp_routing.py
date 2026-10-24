from pathlib import Path
import copy
import json
import sys
from types import SimpleNamespace as NS
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from evaluation.controllers import offramp_routing as routing


class PriorTests(unittest.TestCase):
    def setUp(self):
        self.document=json.loads((ROOT/'diagnostics/offramp_route_prior_ver2.json').read_text())
        self.cfg=NS(network=NS(offramp_direct_share_by_offramp={o:.4 for o in self.document['groups']}))
        self.tuning=json.loads((ROOT/'diagnostics/offramp_route_prior_overlay.json').read_text())

    def test_flag_absent_preserves_config_exactly(self):
        before=copy.deepcopy(self.cfg)
        self.assertEqual(routing.install(self.cfg,{}),{})
        self.assertEqual(self.cfg,before)

    def test_pinned_weights_empty_default_and_dest_connector(self):
        rows=routing.derive_prior(self.document)
        self.assertAlmostEqual(rows['OR_F_E']['direct_share'],4/5.6)
        self.assertEqual(rows['OR_F_W']['direct_share'],.75)
        self.assertTrue(next(r for r in rows['OR_F_W']['routes'] if r['branch']=='signal')['empty_relFlow_default_one'])
        self.assertTrue(next(r for r in rows['OR_F_E']['routes'] if r['branch']=='signal')['connector_is_destination'])

    def test_install_preserves_other_groups_and_records_source(self):
        self.cfg.network.offramp_direct_share_by_offramp['other']=.2
        raw={'run_provenance':{'files':{'network':{'sha256':self.document['network']['sha256']}}}}
        result=routing.install(self.cfg,self.tuning,raw)
        self.assertEqual(self.cfg.network.offramp_direct_share_by_offramp['other'],.2)
        self.assertEqual(self.cfg.network.offramp_direct_share_by_offramp['OR_D_W'],.5)
        self.assertIn('source_sha256',result['offramp_route_prior_provenance'])

    def test_wrong_network_or_tampered_share_fails_before_mutation(self):
        before=copy.deepcopy(self.cfg)
        with self.assertRaises(ValueError):routing.install(self.cfg,self.tuning,{'run_provenance':{}})
        self.assertEqual(before,self.cfg)
        self.document['groups']['OR_D_W']['direct_share']=.7
        with self.assertRaises(ValueError):routing.derive_prior(self.document)


if __name__=='__main__':unittest.main()
