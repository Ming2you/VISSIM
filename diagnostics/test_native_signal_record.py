"""Small synthetic LDP/command-clock tests; no native run or model evaluation."""
import copy
from pathlib import Path
import tempfile
import unittest

from diagnostics import validate_native_signal_record as v
from diagnostics.com_execution_equivalence.command_clock import CommandClock
from diagnostics.com_execution_equivalence.test_command_clock import city
from diagnostics.live_beta0_first_interval_audit import expected_ramp, expected_signal


def ldp(sc, sgs, rows):
    # Same fixed-width vertical labels as the completed 2020 three-SG pilot.
    labels = {6: 'Simul.second', 11: 'Cyclesecond'}
    labels.update({12+i: f'Sig.DisplaySG{sg}' for i, sg in enumerate(sgs)})
    height = max(map(len, labels.values()))
    header = [f'SC Detector Record   [synthetic]', f'SC {sc}; Program file: test;']
    for row in range(height):
        header.append(''.join(labels.get(col, '').rjust(height)[row] if col in labels else ' '
                              for col in range(12+len(sgs))))
    data = [f'{t:7.1f}{0:5.1f}{symbols}' for t, symbols in rows]
    return ('\r\n'.join(header + data) + '\r\n').encode('ascii')


class NativeLdpTest(unittest.TestCase):
    def test_columns_are_bound_by_address_not_expected_order(self):
        parsed = v.parse_ldp_columns(ldp(1004, [5, 1, 8], [(1, '.I '), (2, '/=.')]),
                                     1004, [1, 5, 8], 1, 2)
        self.assertEqual(parsed['column_order'], (5, 1, 8))
        self.assertEqual(parsed['frames'][1], {'1004:5': 'RED', '1004:1': 'GREEN', '1004:8': 'OFF'})
        self.assertEqual(parsed['frames'][2]['1004:1'], 'REDAMBER')

    def test_wrong_or_duplicate_column_address_rejected(self):
        for sgs in ([1, 1], [1, 3]):
            with self.subTest(sgs=sgs), self.assertRaises(ValueError):
                v.parse_ldp_columns(ldp(7, sgs, [(1, '..')]), 7, [1, 2], 1, 1)

    def test_missing_duplicate_reordered_seconds_rejected(self):
        for times in ([1, 3], [1, 2, 2, 3], [2, 1, 3], []):
            with self.subTest(times=times), self.assertRaises(ValueError):
                v.parse_ldp_columns(ldp(7, [1], [(t, '.') for t in times]), 7, [1], 1, 3)

    def test_bad_state_or_lost_off_column_rejected(self):
        for symbol in ('|', '?', '', 'II'):
            with self.subTest(symbol=symbol), self.assertRaises(ValueError):
                v.parse_ldp_columns(ldp(7, [1], [(1, symbol)]), 7, [1], 1, 1)

    def test_bad_clock_cycle_midheader_rejected(self):
        raw = ldp(7, [1], [(1, '.'), (2, '.')])
        tail = b'    2.0  0.0.'
        for replacement in (b'   -2.0  0.0.', b'    nan  0.0.', b'    2.5  0.0.',
                            b'    2.0  NaN.', b'    2.0 -1.0.', b'      header!'):
            self.assertIn(tail, raw)
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                v.parse_ldp_columns(raw.replace(tail, replacement), 7, [1], 1, 2)

    def test_header_controller_clock_and_label_rejected(self):
        raw = ldp(7, [1], [(1, '.')])
        wrong = [raw.replace(b'SC 7;', b'SC 8;'), raw.replace(b'SC 7;', b'SC 7;\nSC 7;'),
                 raw.replace(b'            S\r\n', b'            X\r\n')]
        for item in wrong:
            self.assertNotEqual(raw, item)
            with self.assertRaises(ValueError):
                v.parse_ldp_columns(item, 7, [1], 1, 1)

    def test_partial_window_does_not_skip_invalid_outside_row(self):
        raw = ldp(7, [1], [(1, '.'), (2, 'I'), (3, '/')])
        self.assertEqual(set(v.parse_ldp_columns(raw, 7, [1], 2, 2)['frames']), {2})
        with self.assertRaises(ValueError):
            v.parse_ldp_columns(raw.replace(b'    3.0  0.0/', b'    3.0  0.0?'), 7, [1], 2, 2)

    def test_selected_eight_meter_files_exact_map_and_pins(self):
        with tempfile.TemporaryDirectory() as directory:
            files = {}; groups = {sc: (1,) for sc in range(9101, 9109)}
            for sc in groups:
                path = Path(directory) / f'meter_{sc}.ldp'
                path.write_bytes(ldp(sc, [1], [(1, ' '), (2, 'I')]))
                files[sc] = path
            record = v.read_ldp_frames(files, groups, 1, 2)
            self.assertTrue(record['native_ldp_frame_coverage_passed'])
            self.assertEqual((record['row_count'], record['sample_count'], len(record['pins'])), (16, 16, 8))
            for bad in ({**files, 1: files[9101]}, {k:p for k,p in files.items() if k != 9101},
                        {**files, 9102: files[9101]}):
                with self.assertRaises(ValueError): v.read_ldp_frames(bad, groups, 1, 2)

    def test_expected_address_and_range_guards(self):
        for groups in ({7:[1,1]}, {7:[0]}, {True:[1]}, {7:[]}, {7:'1'}):
            with self.subTest(groups=groups), self.assertRaises(ValueError):
                v.read_ldp_frames({}, groups, 1, 2)
        for start, end in [(2,1),(0,2),(1.1,2),(True,2)]:
            with self.assertRaises(ValueError):
                v.parse_ldp_columns(ldp(7,[1],[(1,'.')]), 7, [1], start, end)

    def test_144_groups_including_zero_window_addresses(self):
        groups = {sc:tuple(range(1,9)) for sc in range(1,18)}
        groups.update({sc:(1,) for sc in range(9101,9109)})
        with tempfile.TemporaryDirectory() as directory:
            files = {}
            for sc, sgs in groups.items():
                files[sc] = Path(directory) / f'sc_{sc}.ldp'
                files[sc].write_bytes(ldp(sc, sgs, [(t, '.'*len(sgs)) for t in range(1,4)]))
            record = v.read_ldp_frames(files, groups, 1, 3)
            self.assertEqual((record['row_count'], record['sample_count']), (75, 432))
            self.assertEqual(len(record['frames'][1]), 144)
            self.assertTrue(all(state == 'RED' for row in record['frames'].values() for state in row.values()))

    def test_legacy_single_column_parser_preserved(self):
        raw = ldp(1004, [5], [(t, '.') for t in range(1,61)])
        before = v.parse_ldp(raw, 1004, 5)
        after = v.parse_ldp_columns(raw, 1004, [5], 1, 60)
        self.assertEqual([row['state'] for row in before.values()],
                         [row['1004:5'] for row in after['frames'].values()])


class NativeClockTest(unittest.TestCase):
    def setUp(self):
        groups = {'2': {'1':1, '2':1, '3':0}}
        def rows(green, offset):
            return city(offset) + [dict(kind='ramp_meter', sc_no='9101', green_sec=str(green), rate_vph=str(green*90))]
        self.clock = CommandClock({1:rows(10,0), 150:rows(2,4), 300:rows(0,0)}, groups, {'9101':900})
        frames = {1:{'2:1':'OFF', '2:2':'OFF', '2:3':'OFF', '9101:1':'OFF'}}
        for t in range(2,301):
            index = 0 if t <= 150 else 1
            snap = self.clock.snapshots[index]
            frames[t] = {f'2:{sg}':expected_signal(snap['signals']['2'], sg, t-1) for sg in groups['2']}
            frames[t]['9101:1'] = expected_ramp(snap['ramps']['9101'], t-1)
        self.record = dict(expected_groups={2:(1,2,3),9101:(1,)}, start_sec=1, end_sec=300, frames=frames)
        self.first = dict.fromkeys(frames[1], 1)

    def test_actual_clock_150_and_300_prewrite_boundary_and_initial(self):
        original = copy.deepcopy(self.record)
        result = v.check_ldp_command_clock(self.record, self.clock, self.first)
        self.assertTrue(result['passed'])
        self.assertEqual(result['compared_samples'], 4*299)
        self.assertEqual(result['pre_control_native_frames'], {1:original['frames'][1]})
        self.assertFalse(result['lsa_coverage_assessed'])
        self.assertTrue(result['initial_immediate_readback_required_separately'])
        self.assertEqual(result['observed_post_control_transitions_by_group']['2:3'], 0)
        self.assertEqual(self.record, original)

    def test_com_actual_mismatch_and_red_only_not_silently_filled(self):
        for t, key in [(2,'2:3'),(150,'9101:1'),(151,'2:1'),(300,'9101:1')]:
            record = copy.deepcopy(self.record)
            current = record['frames'][t][key]
            record['frames'][t][key] = 'RED' if current != 'RED' else 'GREEN'
            result = v.check_ldp_command_clock(record, self.clock, self.first)
            self.assertFalse(result['passed'])
            self.assertEqual([(x['sim_sec'],x['address']) for x in result['mismatches']], [(t,key)])

    def test_missing_frames_address_or_false_late_first_control_rejected(self):
        record = copy.deepcopy(self.record); del record['frames'][150]
        with self.assertRaises(ValueError): v.check_ldp_command_clock(record,self.clock,self.first)
        record = copy.deepcopy(self.record); del record['frames'][150]['2:3']
        with self.assertRaises(ValueError): v.check_ldp_command_clock(record,self.clock,self.first)
        with self.assertRaises(ValueError):
            v.check_ldp_command_clock(self.record,self.clock,{**self.first,'2:1':150})

    def test_allopen_hold_is_coverage_not_transition_validation(self):
        clock = CommandClock({1:[dict(kind='ramp_meter',sc_no='9101',green_sec='10',rate_vph='900')]}, {}, {'9101':900})
        record = dict(expected_groups={9101:[1]},start_sec=1,end_sec=3,
                      frames={1:{'9101:1':'OFF'},2:{'9101:1':'GREEN'},3:{'9101:1':'GREEN'}})
        result = v.check_ldp_command_clock(record, clock, {'9101:1':1})
        self.assertTrue(result['passed'])
        self.assertEqual(result['observed_post_control_transitions_by_group'], {'9101:1':0})


if __name__ == '__main__':
    unittest.main()
