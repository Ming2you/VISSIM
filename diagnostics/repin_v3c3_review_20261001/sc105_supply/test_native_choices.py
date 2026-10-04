"""Native SC105 routes: parallel channelization must retain one approach."""
import copy
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
from evaluation.controllers import physical_movement_routes as routes


class NativeChoices(unittest.TestCase):
    def setUp(self):
        self.path=str((HERE/'physical_routes.json').relative_to(ROOT))
        self.document,self.native,self.edges=routes.load_evidence(self.path)
        self.document['native_choice_groups']={k:v for k,v in self.document['native_choice_groups'].items() if k.startswith('SC105_')}
        self.specs={};self.origins={}
        for group in self.document['native_choice_groups'].values():
            for key,name in group['route_to_movement'].items():
                self.specs[name]={**group['expected_specs'][name],'beta':1/3,'capacity_sentinel':321.}
                path=self.native[key]['path'];cut=path.index(group['stopline'])
                for link in path[:cut+1]:self.origins[link]=[group['origin']]
                self.origins[path[-1]]=[self.specs[name]['receiving_link']]
        self.cfg=SimpleNamespace(network=SimpleNamespace(urban_movements=copy.deepcopy(self.specs)))
        self.tree=ET.parse(ROOT/self.document['network']['path'])

    def configure(self,tree=None):
        with patch.object(routes,'load_evidence',return_value=(self.document,self.native,self.edges)),patch.object(routes,'snapshot_network_sha256',return_value=self.document['network']['sha256']),patch.object(routes.ET,'parse',return_value=tree or self.tree),patch.object(routes,'invalidate_topology_cache'):
            return routes.configure_native_choice_groups(self.cfg,{'link_to_origins':self.origins},{'urban':{'movements':{'physical_route_topology':self.path}}},state_json={})

    def test_exact_native_weights_and_unchanged_other_fields(self):
        result=self.configure()
        self.assertEqual(len(result['native_choice_groups']),2)
        self.assertAlmostEqual(self.cfg.network.urban_movements['SC105_N_SC1002_to_S_SC1005']['beta'],602/797)
        self.assertAlmostEqual(self.cfg.network.urban_movements['SC105_W_SC1003_to_S_SC1005']['beta'],78/249)
        for g in self.document['native_choice_groups'].values():
            self.assertAlmostEqual(sum(self.cfg.network.urban_movements[m]['beta'] for m in g['route_to_movement'].values()),1)
        for m,s in self.cfg.network.urban_movements.items():
            self.assertEqual({k:v for k,v in s.items() if k!='beta'},{k:v for k,v in self.specs[m].items() if k!='beta'})

    def test_added_mid_corridor_input_rejected_without_partial_commit(self):
        ET.SubElement(self.tree.getroot().find('./vehicleInputs'),'vehicleInput',{'no':'999999','link':'1220007200'})
        with self.assertRaisesRegex(ValueError,'another input'):self.configure()
        self.assertEqual(self.cfg.network.urban_movements,self.specs)

    def test_incomplete_group_and_wrong_receiver_fail(self):
        for kind in ('missing','receiver'):
            with self.subTest(kind=kind):
                self.setUp()
                if kind=='missing':self.document['native_choice_groups']['SC105_W_SC1003']['route_to_movement'].pop('1041:3')
                else:self.origins['1220006403']=['wrong_storage']
                with self.assertRaises(ValueError):self.configure()
                self.assertEqual(self.cfg.network.urban_movements,self.specs)

    def test_extra_choice_rejected(self):
        d=ET.SubElement(self.tree.getroot().find('./vehicleRoutingDecisionsStatic'),'vehicleRoutingDecisionStatic',{'no':'999999','link':'1220007200'})
        ET.SubElement(ET.SubElement(d,'vehRoutSta'),'vehicleRouteStatic',{'no':'1'})
        with self.assertRaisesRegex(ValueError,'another input or route decision'):self.configure()

    def test_entry_after_choice_rejected(self):
        node=ET.SubElement(self.tree.getroot().find('./links'),'link',{'no':'999999'})
        ET.SubElement(node,'fromLinkEndPt',{'lane':'30 1','pos':'1'})
        ET.SubElement(node,'toLinkEndPt',{'lane':'420 1','pos':'700'})
        with self.assertRaisesRegex(ValueError,'input after the decision'):self.configure()
        self.assertEqual(self.cfg.network.urban_movements,self.specs)


if __name__=='__main__':unittest.main()
