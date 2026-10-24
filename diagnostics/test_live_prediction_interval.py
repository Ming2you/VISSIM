"""Physical interval completeness, identity accounting and cancellation regressions."""
from __future__ import annotations
import tempfile
import copy
import pickle
from pathlib import Path
import unittest
from diagnostics.audit_live_prediction_interval import (
    ROOT, complete_frames, component_errors, read_physical_window, verify_ranges,
    strict_signal_trace,
    compare_freeway_cells,
)
from diagnostics.signal_readback_cadence import vsl_readback_matches


class IntervalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT/'diagnostics')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'sample.fzp'

    def write(self, snapshots, *, reverse=False):
        lines = ['$VEHICLE:SIMSEC;NO;LANE\\LINK\\NO;LANE\\INDEX;POS;SPEED\n']
        for sec, rows in snapshots:
            for no, link, pos, speed in reversed(rows) if reverse else rows:
                lines.append(f'{sec};{no};{link};1;{pos};{speed}\n')
        self.path.write_text(''.join(lines), encoding='utf-8')

    def measure(self):
        return read_physical_window(self.path, {'1': True, '2': False, '3': True}, {'3': 100.},
            None, None, {'FW': {'3'}}, start=10, end=12, frame_reader=complete_frames)

    def fixture(self):
        return [(10, [(1, 1, 10, 0), (2, 1, 20, 0), (3, 3, 99, 36)]),
                (11, [(1, 2, 10, 0), (4, 1, 20, 0)]),
                (12, [(1, 1, 10, 0), (2, 1, 20, 0), (4, 1, 30, 0)]),
                (13, [(1, 1, 10, 0)])]

    def test_reentry_terminal_interior_and_source_appearance_are_separate(self):
        self.write(self.fixture())
        physical, _, _ = self.measure()
        totals = physical['totals']
        self.assertEqual(totals['observed_exit_veh'], 1)
        self.assertEqual(totals['observed_entry_veh'], 1)
        self.assertEqual(totals['terminal_inferred_exit_veh'], 1)
        self.assertEqual(totals['unresolved_inside_disappearance_veh'], 1)
        self.assertEqual(physical['first_seen_in_window_by_physical_link'], {'1': 1})
        self.assertEqual(physical['reappeared_in_window_by_physical_link'], {'1': 1})
        self.assertEqual(physical['final_inside_veh'], 3)
        self.assertEqual(physical['max_sampled_stock_closure_error_veh'], 0)
        self.assertAlmostEqual(totals['ttt_trapezoid_veh_h'], 4/3600)
        verify_ranges(self.path, physical['fzp_source']['selected_ranges'])

    def test_final_timestamp_needs_later_complete_row(self):
        self.write(self.fixture()[:-1])
        with self.assertRaisesRegex(ValueError, 'not closed'):
            self.measure()

    def test_partial_lookahead_row_is_not_evidence_of_completeness(self):
        self.write(self.fixture())
        self.path.write_bytes(self.path.read_bytes().rstrip(b'\n'))
        with self.assertRaisesRegex(ValueError, 'incomplete row'):
            self.measure()

    def test_record_order_does_not_change_counts(self):
        self.write(self.fixture())
        first, _, _ = self.measure()
        self.write(self.fixture(), reverse=True)
        second, _, _ = self.measure()
        self.assertEqual(first['totals'], second['totals'])
        self.assertEqual(first['initial_link_counts'], second['initial_link_counts'])

    def test_inferred_terminal_cannot_reappear(self):
        rows = self.fixture()
        rows[2][1].append((3, 1, 20, 0))
        self.write(rows)
        with self.assertRaisesRegex(ValueError, 'contradicted'):
            self.measure()

    def test_measured_range_mutation_is_rejected(self):
        self.write(self.fixture())
        first, _, _ = self.measure()
        self.path.write_bytes(self.path.read_bytes().replace(b'99;36', b'98;36'))
        with self.assertRaisesRegex(ValueError, 'changed'):
            verify_ranges(self.path, first['fzp_source']['selected_ranges'])

    def test_equal_aggregate_hides_opposite_component_errors(self):
        values = component_errors({'omega_veh': 100, 'freeway_veh': 70, 'urban_and_ramps_veh': 30},
                                  {'omega_veh': 100, 'freeway_veh': 50, 'urban_and_ramps_veh': 50})
        self.assertEqual(values['model_minus_observed']['omega_veh'], 0)
        self.assertEqual(values['sum_absolute_component_errors_veh'], 40)
        self.assertEqual(values['cancellation_veh'], 40)

    def signal_rows(self):
        # GREEN during [0,5), AMBER during [5,8), RED during [8,10).
        rows = []
        for sec in range(10):
            aspect = 'GREEN' if sec < 5 else 'AMBER' if sec < 8 else 'RED'
            for stage, time in (('immediate', sec), ('post_step', sec+1)):
                rows.append({'sim_sec': str(time), 'sc_no': '1', 'sg_no': '1',
                             'stage': stage, 'requested_state': aspect,
                             'readback_state': aspect, 'ok': '1'})
        return rows

    def signal_audit(self, rows):
        controllers = {'1': {'cycle_sec': 10., 'offset_sec': 0., 'windows': {'1': [(0., 5.)]}}}
        return strict_signal_trace(rows, controllers, {}, start=0, end=10)

    def test_two_endpoint_rows_cannot_prove_ten_seconds_of_signal_observation(self):
        rows = [self.signal_rows()[0], {**self.signal_rows()[1], 'sim_sec': '10'}]
        result = self.signal_audit(rows)
        # Historical integration credits all ten seconds; strict cadence rejects.
        self.assertTrue(result['interval_complete'])
        self.assertFalse(result['valid'])
        self.assertEqual(len(result['strict_one_second_cadence']['problems']), 2)

    def test_every_second_signal_rows_pass_but_missing_or_duplicate_row_fails(self):
        rows = self.signal_rows()
        self.assertTrue(self.signal_audit(rows)['valid'])
        self.assertFalse(self.signal_audit(rows[:7]+rows[8:])['valid'])
        self.assertFalse(self.signal_audit(rows+[rows[6]])['valid'])

    def test_noninteger_sample_cannot_replace_expected_second(self):
        rows = self.signal_rows()
        rows[6] = {**rows[6], 'sim_sec': '3.5'}
        result = self.signal_audit(rows)
        self.assertFalse(result['valid'])
        self.assertTrue(any(p['unexpected_seconds'] for p in result['strict_one_second_cadence']['problems']))

    def test_nonfinite_extra_timestamp_is_not_silently_ignored(self):
        rows = self.signal_rows()
        result = self.signal_audit(rows+[{**rows[0], 'sim_sec': 'nan'}])
        self.assertFalse(result['valid'])
        self.assertEqual(len(result['strict_one_second_cadence']['invalid_timestamp_rows']), 1)

    def test_vsl_readback_requires_both_finite_distribution_values(self):
        self.assertTrue(vsl_readback_matches({'speed_kph': '80', 'readback': '80|80'}))
        for readback in ('nan|80', '80|inf', '80', '80|80|80', 'bad|80', '100|80'):
            with self.subTest(readback=readback):
                self.assertFalse(vsl_readback_matches({'speed_kph': '80', 'readback': readback}))

    def test_only_two_identical_start_ramp_reapplications_are_allowed(self):
        rows = [{**row, 'sc_no': '9101'} for row in self.signal_rows()]
        def audit(values):
            return strict_signal_trace(values, {}, {'9101': 5.}, start=0, end=10)
        # The meter uses one amber second, so correct the generic SG fixture.
        for row in rows:
            sec = float(row['sim_sec'])-(row['stage'] == 'post_step')
            row['requested_state'] = row['readback_state'] = 'GREEN' if sec < 5 else 'AMBER' if sec < 6 else 'RED'
        result = audit([rows[0]]+rows)
        self.assertTrue(result['valid'])
        self.assertEqual(result['strict_one_second_cadence']['raw_duplicate_rows_total'], 1)
        self.assertEqual(len(result['strict_one_second_cadence']['allowed_start_ramp_reapplications']), 1)
        self.assertFalse(audit([rows[0], rows[0]]+rows)['valid'])  # Three start writes.
        self.assertFalse(audit(rows+[rows[4]])['valid'])  # A middle-second duplicate.
        self.assertFalse(audit([{**rows[0], 'readback_state': 'RED'}]+rows)['valid'])
        self.assertFalse(self.signal_audit([self.signal_rows()[0]]+self.signal_rows())['valid'])  # Urban duplicate.

    def cell_fixture(self):
        initial = {'freeway_cells_veh': {'FW_E': [20., 10.]}, 'freeway_speed_kph': {'FW_E': [30., 100.]}}
        final = {'freeway_cells_veh': {'FW_E': [30., 5.]}, 'freeway_speed_kph': {'FW_E': [100., 110.]},
                 'freeway_density_veh_km_lane': {'FW_E': [30., 5.]},
                 'freeway_effective_lanes': {'FW_E': [2., 2.]}, 'freeway_continuity_cell_length_km': .5}
        raw0 = {'freeway_segments': {'FW_E': [dict(count=20, speed_sum=600., length_km=.6, lanes=2),
                                              dict(count=10, speed_sum=1000., length_km=.6, lanes=2)]}}
        raw1 = {'freeway_segments': {'FW_E': [dict(count=24, speed_sum=960., length_km=.6, lanes=2),
                                              dict(count=0, speed_sum=0., length_km=.6, lanes=2)]}}
        mapping = {'freeway_model_links': {'FW_E': {'segment_bounds_m': [0., 600., 1200.]}}}
        trace = [{'elapsed_sec': 10, 'cell_counts_veh': final['freeway_cells_veh'], 'cell_speed_kph': final['freeway_speed_kph']}]
        return initial, final, raw0, raw1, mapping, trace

    def test_cells_preserve_geometry_and_empty_speed_and_detect_false_recovery(self):
        args = self.cell_fixture(); before = pickle.dumps(args)
        result = compare_freeway_cells(*args)
        self.assertEqual(pickle.dumps(args), before)
        row, empty = result['rows']
        self.assertEqual(row['count_error_veh'], 6.)
        self.assertEqual(row['speed_error_kph'], 60.)
        self.assertEqual(row['observed_density_veh_km_lane'], 20.)
        self.assertEqual(row['observed_density_in_model_continuity_units'], 24.)
        self.assertTrue(row['false_recovery_at_endpoint'])
        self.assertEqual(row['predicted_threshold_crossings'][0]['elapsed_sec'], 10)
        self.assertIsNone(empty['observed_speed_kph'])
        self.assertIsNone(empty['speed_error_kph'])
        self.assertEqual(result['summary']['nonempty_observed_cells'], 1)
        self.assertEqual(result['summary']['count_bias_sum_veh'], 11.)

    def test_cell_axis_mismatch_and_empty_speed_moment_are_rejected(self):
        args = list(self.cell_fixture())
        args[3] = copy.deepcopy(args[3]); args[3]['freeway_segments']['FW_E'].pop()
        with self.assertRaisesRegex(ValueError, 'axes differ'):
            compare_freeway_cells(*args)
        args = list(self.cell_fixture()); args[3]['freeway_segments']['FW_E'][1]['speed_sum'] = 1.
        with self.assertRaisesRegex(ValueError, 'Empty COM cell'):
            compare_freeway_cells(*args)


if __name__ == '__main__':
    unittest.main()
