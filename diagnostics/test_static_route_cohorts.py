"""Crossing edge cases and stored actual matched-cohort evidence checks."""
import json
from pathlib import Path
import unittest

from diagnostics.probe_static_route_cohorts import connector_event, gate_event, in_cohort

ROOT = Path(__file__).resolve().parents[1]


class CrossingTests(unittest.TestCase):
    def test_window_boundary_and_lane_ambiguity(self):
        event = gate_event((2, 1, 90, 20), (2, 2, 110, 20), 2, 100, 749, 751)
        self.assertTrue(in_cohort(event))
        self.assertTrue(event['gate_lane_ambiguous'])
        self.assertFalse(in_cohort(gate_event((2,1,90,20),(2,1,110,20),2,100,599,601)))

    def test_first_seen_downstream_or_wrong_link_never_proves_gate(self):
        self.assertIsNone(gate_event((10681,1,90,20),(2,1,2330,20),2,2320,700,701))
        self.assertIsNone(gate_event((2,1,2321,20),(2,1,2330,20),2,2320,700,701))

    def test_only_declared_physical_source_proves_entry(self):
        spec = {'source_link':2,'connector':10682,'source_pos_m':100,'target_link':121,'target_pos_m':5,'length_m':200}
        self.assertIsNone(connector_event((121,1,90,20),(10682,1,10,20),spec,700,701,True))
        event = connector_event((2,1,90,20),(10682,1,10,20),spec,700,701,True)
        self.assertEqual(event['estimated_sec'],700.5)

    def test_observed_transition_can_have_no_valid_interpolation(self):
        spec = {'source_link':2,'connector':10682,'source_pos_m':100,'target_link':121,'target_pos_m':5,'length_m':200}
        event = connector_event((2,1,101,20),(10682,1,10,20),spec,700,701,True)
        self.assertIsNone(event['estimated_sec'])
        self.assertEqual(event['method'],'observed_transition_interval_only')


class ActualEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'diagnostics/static_route_matched_cohorts.json').read_text(encoding='utf-8'))

    def test_all_decision_ids_have_one_observed_ordered_outcome(self):
        expected={'OR_F_E':193,'OR_D_E':119,'OR_D_W':205,'OR_F_W':148}
        for group,rows in self.data['decision_cohorts'].items():
            self.assertEqual(len(rows),expected[group])
            for no,r in rows.items():
                self.assertEqual(int(no),r['vehicle_id'])
                self.assertTrue(in_cohort(r['gate_crossing']))
                self.assertIsNotNone(r['outcome'])
                self.assertGreaterEqual(r['outcome']['t0'],r['gate_crossing']['t0'])
                self.assertLessEqual(r['outcome']['t1'],1200)
                self.assertNotIn('disappearance_before_outcome',r)

    def test_all_off_outcomes_use_native_connector_source(self):
        for source in ('decision_cohorts','intermediate_merge_bypass_cohorts'):
            for group,rows in self.data[source].items():
                for row in rows.values():
                    event=row['outcome'];kind=event['kind']
                    if kind in ('direct','signal'):
                        spec=self.data['gates'][group][kind]
                        self.assertEqual((event['old_link'],event['new_link']),(spec['source_link'],spec['connector']))
                    else:
                        self.assertEqual(event['old_link'],self.data['gates'][group]['through_link'])
                        self.assertEqual(event['new_link'],event['old_link'])

    def test_bypass_is_distinct_and_repeated_visit_not_double_counted(self):
        for group in self.data['decision_cohorts']:
            self.assertFalse(set(self.data['decision_cohorts'][group]) & set(self.data['intermediate_merge_bypass_cohorts'][group]))
        records=self.data['intermediate_merge_bypass_cohorts']['OR_D_E']
        self.assertEqual(len(records),10)
        self.assertEqual(len(records['161']['repeated_merge_crossings']),1)
        self.assertLess(records['161']['outcome']['t1'],records['161']['repeated_merge_crossings'][0]['t0'])

    def test_bounded_complete_observation_and_no_censoring(self):
        self.assertLess(self.data['fzp']['bytes_read'],256*1024*1024)
        self.assertLess(self.data['fzp']['elapsed_wall_seconds'],45)
        self.assertEqual(self.data['fzp']['frame_count'],602)
        self.assertEqual(self.data['fzp']['cadence_counts'],{'1.0':601})
        self.assertTrue(all(not x for x in self.data['unclassified_appearances_beyond_gate'].values()))
        self.assertTrue(all(r['cohort_n']==r['resolved_n'] for r in self.data['summary']))


if __name__=='__main__':
    unittest.main()
