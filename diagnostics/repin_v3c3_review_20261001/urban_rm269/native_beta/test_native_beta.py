"""Complete pinned SC12/SC16 choices; reject ambiguous ownership atomically."""
import copy
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from evaluation.controllers import physical_movement_routes as routes


class NativeBeta(unittest.TestCase):
    def setUp(self):
        self.path = (HERE/'physical_routes.json').relative_to(ROOT).as_posix()
        self.doc, self.native, self.edges = routes.load_evidence(self.path)
        names = {'SC12_S_SC16', 'SC16_S_SC109'}
        self.doc['native_choice_groups'] = {k:v for k,v in self.doc['native_choice_groups'].items() if k in names}
        net = json.loads((HERE.parent/'selection2400/network.json').read_bytes())
        self.specs, self.origins = {}, {}
        for g in self.doc['native_choice_groups'].values():
            for rid, m in g['route_to_movement'].items():
                self.specs[m] = copy.deepcopy(net['urban_movements'][m])
                path = self.native[rid]['path']; cut = path.index(g['stopline'])
                for link in path[:cut+1]: self.origins[link] = [g['origin']]
                self.origins[path[-1]] = [self.specs[m]['receiving_link']]
        self.cfg = SimpleNamespace(network=SimpleNamespace(urban_movements=copy.deepcopy(self.specs)))
        self.tree = ET.parse(ROOT/self.doc['network']['path'])

    def configure(self):
        with patch.object(routes, 'load_evidence', return_value=(self.doc,self.native,self.edges)), \
             patch.object(routes, 'snapshot_network_sha256', return_value=self.doc['network']['sha256']), \
             patch.object(routes.ET, 'parse', return_value=self.tree), patch.object(routes, 'invalidate_topology_cache'):
            return routes.configure_native_choice_groups(self.cfg, {'link_to_origins':self.origins},
                {'urban':{'movements':{'physical_route_topology':self.path}}}, state_json={})

    def test_exact_complete_native_weights_only(self):
        result = self.configure()
        self.assertEqual(set(result['native_choice_groups']), {'SC12_S_SC16','SC16_S_SC109'})
        self.assertAlmostEqual(self.cfg.network.urban_movements['SC12_S_SC16_to_N_SC6']['beta'],810/890)
        self.assertAlmostEqual(self.cfg.network.urban_movements['SC16_S_SC109_to_N_SC12']['beta'],926/972)
        for g in self.doc['native_choice_groups'].values():
            self.assertAlmostEqual(sum(self.cfg.network.urban_movements[m]['beta'] for m in g['route_to_movement'].values()),1)
        for m, spec in self.cfg.network.urban_movements.items():
            self.assertEqual({k:v for k,v in spec.items() if k!='beta'}, {k:v for k,v in self.specs[m].items() if k!='beta'})

    def test_incomplete_or_wrong_receiver_does_not_partially_commit(self):
        for mode in ('incomplete','receiver'):
            with self.subTest(mode=mode):
                self.setUp()
                if mode=='incomplete': self.doc['native_choice_groups']['SC16_S_SC109']['route_to_movement'].pop('284:3')
                else: self.origins['1220011300']=['wrong_receiver']
                with self.assertRaises(ValueError): self.configure()
                self.assertEqual(self.cfg.network.urban_movements,self.specs)

    def test_additional_input_after_decision_rejected(self):
        ET.SubElement(self.tree.getroot().find('./vehicleInputs'),'vehicleInput',{'no':'999999','link':'1210009503'})
        with self.assertRaisesRegex(ValueError,'another input'): self.configure()
        self.assertEqual(self.cfg.network.urban_movements,self.specs)


if __name__ == '__main__': unittest.main()
