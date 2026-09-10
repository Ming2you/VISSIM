"""Focused evidence checks; reads only the small artifacts and fixed geometry."""
from pathlib import Path
import csv
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from diagnostics.sc1004_head_service_identifiability import geometry, path
from diagnostics.selected_signal_sampling_audit import head_events
from diagnostics.prepare_sc15_service_calibration import blocks_from_rows, HOLDOUTS
from evaluation.controllers.fixed_signal_schedule import _union_green_overlap


class EvidenceChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geo, _, cls.program, cls.offset, _ = geometry()
        cls.result = json.loads(path('.json').read_text(encoding='utf-8'))

    def test_prehead_bypasses_are_not_head_service(self):
        for road, connector, before in [('46','10625',948.),('66','10632',2629.),('71','10642',36.)]:
            rows = head_events(self.geo[road], 1, (int(road),1,before,20.), (int(connector),1,3.,20.),100,101)
            self.assertEqual([r['kind'] for r in rows], ['pre_head_bypass'])

    def test_lane_mismatch_is_not_arbitrarily_allocated(self):
        rows = head_events(self.geo['71'],1,(71,1,78.,20.),(10634,2,3.,20.),100,101)
        self.assertEqual([r['kind'] for r in rows], ['unresolved_departure_lane'])
        rows = head_events(self.geo['71'],1,(71,1,78.,20.),(71,2,80.,20.),100,101)
        self.assertEqual([r['kind'] for r in rows], ['unresolved_lane_change_at_head'])

    def test_green_boundary_bracket_is_not_whole_green(self):
        t = next(t for t in range(1,5400)
                 if self.program.state_at(t,'2',controller_offset_sec=self.offset)=='GREEN'
                 and self.program.state_at(t-1,'2',controller_offset_sec=self.offset)!='GREEN')
        self.assertEqual(_union_green_overlap(self.program,('2',),t-.5,t+.5,self.offset),.5)

    def test_block_uses_endpoint_uncertainty_once(self):
        crossings = {('h',i):{'vehicle_id':i,'lower_sec':2*i,'upper_sec':2*i+1,'linear_estimate_sec':2*i+.5} for i in range(3)}
        gaps = [{'input_no':'h','previous_vehicle_id':i,'vehicle_id':i+1,
                 'green_start_sec':0,'queued_after_third_departure':True} for i in range(2)]
        blocks, excluded = blocks_from_rows(gaps,crossings,holdouts=[])
        self.assertEqual(excluded,[]); self.assertEqual(len(blocks),1)
        self.assertEqual(blocks[0]['gap_count'],2)
        self.assertEqual(blocks[0]['duration_upper_sec'],5)
        self.assertEqual(blocks[0]['duration_lower_sec'],3)

    def test_all_fit_blocks_exclude_holdouts_and_reproduce_rate(self):
        for h in self.result['heads'].values():
            blocks = h['broad_fit_blocks']
            for block in blocks:
                lo,hi = block['first_crossing_lower_sec'],block['last_crossing_upper_sec']
                self.assertFalse(any(lo<=b and hi>=a for a,b in HOLDOUTS))
            n = sum(b['gap_count'] for b in blocks)
            total = sum(b['duration_upper_sec'] for b in blocks)
            self.assertEqual(n,h['broad_fit_diagnostic_only']['gaps'])
            if n: self.assertAlmostEqual(3600*n/total,h['broad_fit_diagnostic_only']['rate_lower_veh_h'])

    def test_resource_flow_keeps_distinct_repeat_visits(self):
        with path('.head_crossings.csv').open(encoding='utf-8') as f: rows = list(csv.DictReader(f))
        own = [r for r in rows if r['physical_resource']=='10634' and r['resource_join_verified']=='True'
               and r['guaranteed_green']=='True' and r['repeated_head_vehicle_id']=='False']
        identities = [(r['vehicle_id'],r['lower_sec'],r['upper_sec']) for r in own]
        self.assertEqual(len(identities),len(set(identities)))
        resource = self.result['shared_10634_observed_resource']
        self.assertEqual(len(own),resource['guaranteed_green_and_subsequent_connector_verified_crossings'])
        self.assertEqual(len({r['vehicle_id'] for r in own}),resource['unique_vehicle_ids'])
        self.assertAlmostEqual(len(own)*3600/resource['full_run_native_green_seconds'],resource['observed_green_exposure_rate_lower_bound_veh_h'])

    def test_sparse_resource_lanes_do_not_receive_an_estimate(self):
        for head in ('90030882','90030883'):
            h = self.result['heads'][head]
            self.assertEqual(h['broad_fit_diagnostic_only']['gaps'],0)
            self.assertIsNone(h['broad_fit_diagnostic_only']['rate_lower_veh_h'])
        self.assertIsNone(self.result['shared_10634_observed_resource']['simultaneous_three_lane_saturation_estimate'])


if __name__=='__main__': unittest.main(verbosity=2)
