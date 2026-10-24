"""Synthetic geometry distinguishes physical crossings, route evidence and censoring."""
from types import SimpleNamespace
import unittest
from diagnostics.probe_e8_window_passages import transitions, event_summary, removal_matches


class PassageTests(unittest.TestCase):
    def setUp(self):
        self.g = SimpleNamespace(offsets={2: 0}, gates={'before': 99., 'after': 101.},
            connectors={10682: {'source': 2, 'target': 121, 'source_pos': 100., 'target_pos': 10.,
                                'source_lane': 1, 'target_lane': 1, 'length': 20.}},
            unique_pairs={(2, 121): 10682})
        self.g.pos = lambda r: r[2] if r[0] == 2 else None

    def test_mainline_crossing_preserves_lane_ambiguity_and_time_bounds(self):
        rows = transitions(self.g, 7, (2, 2, 90., 36.), (2, 3, 110., 36.), 10., 15.)
        self.assertEqual([r['kind'] for r in rows], ['before', 'after'])
        self.assertEqual([r['estimated_sec'] for r in rows], [12.25, 12.75])
        self.assertTrue(all(not r['lane_endpoints_agree'] for r in rows))
        counts = event_summary(rows, 12.5, 20.)
        self.assertEqual(counts['before']['estimated_count_observed'], 0)
        self.assertEqual(counts['before']['possibly_within_observed'], 1)
        self.assertEqual(counts['after']['definitely_within_observed'], 0)

    def test_observed_direct_entry_crosses_before_but_not_through_after(self):
        rows = transitions(self.g, 8, (2, 2, 90., 36.), (10682, 1, 10., 36.), 10., 15.)
        d = {r['kind']: r for r in rows}
        self.assertEqual(set(d), {'before', 'connector_10682_entry'})
        self.assertEqual(d['connector_10682_entry']['estimated_sec'], 12.5)
        self.assertFalse(d['before']['lane_endpoints_agree'])
        self.assertEqual((d['before']['lane_before'], d['before']['lane_after']), (2, 1))

    def test_unique_skipped_connector_is_inferred_not_observed(self):
        rows = transitions(self.g, 9, (2, 1, 90., 36.), (121, 1, 20., 36.), 10., 15.)
        self.assertTrue(all(r['inferred_short_connector'] for r in rows))
        self.assertEqual({r['kind'] for r in rows}, {'before', 'connector_10682_entry', 'connector_10682_exit'})
        d = event_summary(rows, 10., 15.)
        self.assertEqual(d['connector_10682_entry']['estimated_count_observed'], 0)
        self.assertEqual(d['connector_10682_entry']['estimated_count_inferred'], 1)

    def test_unknown_multi_link_jump_does_not_invent_connector(self):
        rows = transitions(self.g, 10, (2, 1, 90., 36.), (123, 1, 20., 36.), 10., 15.)
        self.assertEqual(rows, [])
        rows = transitions(self.g, 11, (10682, 1, 15., 36.), (123, 1, 20., 36.), 10., 15.)
        self.assertEqual(rows[0]['kind'], 'connector_10682_exit')
        self.assertIsNone(rows[0]['estimated_sec'])
        self.assertEqual(rows[0]['method'], 'interval_only')

    def test_warning_at_last_record_time_matches_first_absence_bracket(self):
        warning = {'sim_sec': '3237.0', 'vehicle': '14249'}
        self.assertEqual(removal_matches([warning], 3237., 3238.), [warning])
        self.assertEqual(removal_matches([warning], 3238., 3239.), [])


if __name__ == '__main__':
    unittest.main()
