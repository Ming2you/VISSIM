"""Pure tests of endpoint sampling and conservative physical head brackets."""
import unittest

from diagnostics.selected_signal_sampling_audit import departures, departure_paths, head_events, summarize


def row(link=66, lane=1, pos=0):
    return (link, lane, pos, 20.0)


def spec(branch_pos=110, lanes=1):
    return {'heads': [{'head': 'h', 'SC': '1', 'sg': '2', 'lane': 1, 'pos_m': 100}],
            'branches': {'9': {'source_lane': 1, 'target_lane': 1, 'lanes': lanes,
                               'from_pos_m': branch_pos, 'target': '10', 'target_pos_m': 0,
                               'length_m': 10}}}


class SamplingTests(unittest.TestCase):
    def test_transient_source_vehicle_is_lost_with_same_data_downsample(self):
        fine = departures({1: row()}, {1: row(9)}, 9, 10)
        checkpoints = {0: {}, 30: {}}
        result = summarize(fine, [], checkpoints, 0, 30, '66')
        self.assertEqual(result['lost_departures'], 1)
        self.assertEqual(result['one_second_events_by_downsampling_reason'],
                         {'not_on_source_at_30s_bin_start': 1})

    def test_reentry_is_missed_without_inventing_endpoint_exit(self):
        start = {1: row()}; end = {1: row(pos=2)}
        fine = departures(start, {1: row(9)}, 0, 1)
        coarse = departures(start, end, 0, 30)
        result = summarize(fine, coarse, {0: start, 30: end}, 0, 30, '66')
        self.assertEqual(result['one_second_events_by_downsampling_reason'],
                         {'same_source_at_both_30s_endpoints': 1})

    def test_absence_separate_from_changed_link_and_unchanged_ids(self):
        events = departures({1: row(), 2: row(), 3: row()}, {2: row(9), 3: row()}, 1, 2)
        self.assertEqual(len(events), 2)
        self.assertEqual(sum(e['endpoint_absent'] for e in events), 1)

    def test_same_lane_head_bracket_and_lane_change_ambiguous(self):
        event = head_events(spec(), 1, row(pos=99), row(pos=101), 1, 2)[0]
        self.assertEqual(event['method'], 'same_source_position_bracket')
        self.assertEqual(event['linear_estimate_sec'], 1.5)
        event = head_events(spec(), 1, row(pos=99), row(lane=2, pos=101), 1, 2)[0]
        self.assertEqual(event['kind'], 'unresolved_lane_change_at_head')

    def test_prehead_branch_and_nohead_lane_are_not_signal_crossings(self):
        event = head_events(spec(branch_pos=90), 1, row(pos=85), row(9, pos=3), 1, 2)[0]
        self.assertEqual(event['kind'], 'pre_head_bypass')
        event = head_events(spec(lanes=2), 1, row(lane=2, pos=105), row(9, lane=2, pos=3), 1, 2)[0]
        self.assertEqual(event['kind'], 'no_head_on_branch_source_lane')

    def test_connector_crossing_requires_unique_lane_consistent_path(self):
        event = head_events(spec(), 1, row(pos=99), row(9, pos=3), 1, 2)[0]
        self.assertEqual(event['kind'], 'head_crossing')
        self.assertEqual(event['method'], 'source_to_observed_connector_bracket')
        s = spec(); s['branches']['11'] = dict(s['branches']['9'])
        event = head_events(s, 1, row(pos=99), row(10, pos=3), 1, 2)[0]
        self.assertEqual(event['kind'], 'unresolved_departure_path')

    def test_lost_bypass_is_not_lost_signal_crossing(self):
        fine = departures({1: row(pos=85), 2: row(pos=99)}, {1: row(9, pos=3), 2: row(9, pos=3)}, 9, 10)
        events = head_events(spec(branch_pos=90), 1, row(pos=85), row(9, pos=3), 9, 10)
        events += head_events(spec(), 2, row(pos=99), row(9, pos=3), 9, 10)
        coarse = departures({2: row()}, {2: row(9)}, 0, 30)
        total, missing = departure_paths(fine, coarse, events, 0, 30, '66')
        self.assertEqual(total, {'pre_head_bypass': 1, 'verified_head_path_departure': 1})
        self.assertEqual(missing, {'pre_head_bypass': 1})


if __name__ == '__main__':
    unittest.main()
