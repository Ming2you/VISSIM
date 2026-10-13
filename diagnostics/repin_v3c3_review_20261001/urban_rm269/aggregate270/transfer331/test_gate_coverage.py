from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.transfer331 import gate_coverage as c

class GeometryCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network=(c.gate.ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx').read_bytes()
        cls.root=ET.fromstring(cls.network);cls.paths=c.connector_paths(cls.network)
    def test_all_native_post_gate_connectors(self):
        self.assertEqual(set(self.paths),{'10218','10223','10224'})
        self.assertEqual(self.paths['10224'],[['10224',c.gate.TERMINAL]])
    def test_unknown_current_route_keeps_connector_not_guessed_turn(self):
        row=[27430,10224,1,2.10848209710191,44.5697270169784,4.211,None,None,None,None]
        with c.enabled(self.network):
            movement,path=c.gate.current_route(row,self.root)
            self.assertIsNone(movement)
            self.assertEqual(path,['10224',c.gate.TERMINAL])
            self.assertNotIn(c.gate.GATE,path)
        self.assertNotIn('10224',c.gate.POST)
    def test_known_route_and_other_links_unchanged(self):
        row=[27769,10218,2,10.0875180848342,42.375333445447,4.644,33.,2.,'STATIC',1220018201.]
        before=c.gate.current_route(row,self.root)
        with c.enabled(self.network):self.assertEqual(c.gate.current_route(row,self.root),before)
        self.assertEqual(before[0],'SC12_N_SC6_to_S_SC16')

if __name__=='__main__':unittest.main()
