"""Numerical lane-drop hygiene; fractional spillback must remain physical."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from evaluation.controllers.freeway_fd import positive_lane_reduction


class LaneDropRoundoff(unittest.TestCase):
    def test_same_lane_geometry_roundoff_is_not_a_drop(self):
        self.assertEqual(positive_lane_reduction(3.0000000000000004,3.),0.)
        self.assertEqual(positive_lane_reduction(3.,2.9999999999999996),0.)
        self.assertEqual(positive_lane_reduction(3.,3.),0.)
        self.assertEqual(positive_lane_reduction(3.,4.),0.)

    def test_physical_fractional_spillback_is_not_rounded(self):
        for a,b in ((4.,3.),(3.,2.7),(3.,3.-1e-12),(2.55,2.5)):
            self.assertEqual(positive_lane_reduction(a,b),a-b)

    def test_selected_refined_geometry_has_only_one_static_east_drop(self):
        import json
        path=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json'
        geometry=json.loads(path.read_text())
        for road,expected in (('FW_E',[18]),('FW_W',[])):
            cells=sorted((c for c in geometry['cells'] if c['road']==road),key=lambda c:c['cell'])
            lanes=[c['lane_km']/c['length_km'] for c in cells]
            actual=[i for i in range(len(lanes)-1) if positive_lane_reduction(lanes[i],lanes[i+1])>0]
            self.assertEqual(actual,expected)

if __name__=='__main__': unittest.main()
