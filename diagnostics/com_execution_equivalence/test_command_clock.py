"""Synthetic command/readback rows only; no actual run payload or COM."""
import copy
import unittest

from diagnostics.com_execution_equivalence.command_clock import CommandClock, native_options, native_clock_options


def city(offset=0):
    axis = dict(kind='signal', sc_no='2', dsd_no='', offset=str(offset),
                p1_green='5', p2_green='5', p3_green='0', p4_green='0')
    return [axis] + [dict(kind='signal_sg', sc_no='2', dsd_no=str(sg), offset=str(offset),
                         p1_green=str(a), p2_green=str(b), green_sec='16')
                     for sg, a, b in [(1, 0, 5), (2, 5, 10)]]


def batch(green, speed=120, offset=0):
    return city(offset) + [dict(kind='ramp_meter', sc_no='9101', green_sec=str(green), rate_vph=str(green*90)),
                           dict(kind='vsl', dsd_no='7', speed_kph=str(speed))]


def signal(sec, stage, sc, sg, value):
    return dict(sim_sec=sec, stage=stage, sc_no=sc, sg_no=sg,
                requested_state=value, readback_state=value, ok='1')


class ClockTest(unittest.TestCase):
    def setUp(self):
        self.groups = {'2': {'1': 1, '2': 1, '3': 0}}
        self.batches = {1: batch(10), 10: batch(2, 80, 4)}
        self.clock = CommandClock(self.batches, self.groups, {'9101': 900})

    def test_prepost_plan_and_offset_boundary(self):
        self.assertEqual(self.clock.check_signal(signal(10, 'post_step', 2, 2, 'GREEN')), 'GREEN')  # old t9
        self.assertEqual(self.clock.check_signal(signal(10, 'immediate', 2, 2, 'RED')), 'RED')  # new t10+offset4
        with self.assertRaisesRegex(ValueError, 'Command clock mismatch'):
            self.clock.check_signal(signal(10, 'post_step', 2, 2, 'RED'))

    def test_amber_suppressed_by_other_group_green(self):
        self.clock.check_signal(signal(5, 'immediate', 2, 1, 'RED'))
        with self.assertRaises(ValueError): self.clock.check_signal(signal(5, 'immediate', 2, 1, 'AMBER'))

    def test_amber_without_other_green(self):
        clock = CommandClock({1: batch(10)}, self.groups, {'9101': 900})
        clock.check_signal(signal(10, 'immediate', 2, 2, 'AMBER'))
        clock.check_signal(signal(13, 'immediate', 2, 2, 'RED'))

    def test_red_only_owned_group(self):
        self.clock.check_signal(signal(2, 'immediate', 2, 3, 'RED'))
        with self.assertRaises(ValueError): self.clock.check_signal(signal(2, 'immediate', 2, 3, 'GREEN'))

    def test_meter_boundary_quantized_clock(self):
        for t, stage, value in [(10,'post_step','GREEN'),(10,'immediate','GREEN'),
                                (12,'post_step','GREEN'),(12,'immediate','AMBER'),
                                (13,'post_step','AMBER'),(13,'immediate','RED')]:
            self.clock.check_signal(signal(t, stage, 9101, 1, value))
        with self.assertRaises(ValueError): self.clock.check_signal(signal(12, 'immediate', 9101, 1, 'GREEN'))

    def test_meter_bad_quantization_rejected(self):
        rows = batch(2); rows[-2]['rate_vph'] = '300'
        with self.assertRaisesRegex(ValueError, 'quantization'): CommandClock({1: rows}, self.groups, {'9101': 900})

    def test_zero_amber_meter_boundary_keeps_prepost_order_and_city_clock(self):
        clock = CommandClock(self.batches, self.groups, {'9101': 900}, ramp_amber_sec=0)
        for t, stage, value in [(10,'post_step','GREEN'),(10,'immediate','GREEN'),
                                (12,'post_step','GREEN'),(12,'immediate','RED'),
                                (13,'post_step','RED'),(13,'immediate','RED')]:
            clock.check_signal(signal(t, stage, 9101, 1, value))
        with self.assertRaises(ValueError): clock.check_signal(signal(12, 'immediate', 9101, 1, 'AMBER'))
        for green in range(11):
            for sec in range(31):
                self.assertEqual(clock.expected_meter_state(green, sec), 'GREEN' if sec % 10 < green else 'RED')
        for snapshot, old in zip(clock.snapshots, self.clock.snapshots):
            for sec in range(31):
                for sg in self.groups['2']:
                    self.assertEqual(clock.expected_urban_state('2', snapshot['signals']['2'], sg, sec),
                                     self.clock.expected_urban_state('2', old['signals']['2'], sg, sec))

    def test_explicit_legacy_amber_is_exact_and_invalid_values_fail(self):
        from diagnostics.live_beta0_first_interval_audit import expected_ramp
        for green in range(11):
            for sec in range(31):
                self.assertEqual(self.clock.expected_meter_state(green, sec), expected_ramp(green, sec))
        for value in (True, False, '0', '1', None, -1, 2, 0.5, float('nan')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                CommandClock(self.batches, self.groups, {'9101': 900}, ramp_amber_sec=value)

    def test_vsl_exact_address_time_request(self):
        row = dict(sim_sec=10, dsd_no=7, veh_class_no=30, requested_kph=80,
                   readback_distribution_no=80, stage='immediate', ok='1')
        self.clock.check_vsl(row)
        # Both requested and actual can agree yet disagree with this command.
        with self.assertRaisesRegex(ValueError, 'command/readback'):
            self.clock.check_vsl({**row, 'requested_kph':120, 'readback_distribution_no':120})
        with self.assertRaises(ValueError): self.clock.check_vsl({**row, 'sim_sec':11})

    def test_missing_positive_window_not_red_inference(self):
        rows = batch(10); rows.pop(1)
        with self.assertRaisesRegex(ValueError, 'window count'): CommandClock({1:rows}, self.groups, {'9101':900})

    def test_pinned_literals_guard_reuse_constants(self):
        vbs = 'Const RAMP_CYCLE_SEC = 10\nConst RAMP_AMBER_SEC = 1\nConst AMBER_SEC = 3\n'
        config = 'RW_RAMP_METER_SCS = "9101"\nRW_RAMP_METER_CAPACITIES_VPH = "900.0"\n'
        self.assertEqual(native_options(vbs, config), {'9101':900})
        with self.assertRaises(ValueError): native_options(vbs.replace('SEC = 3', 'SEC = 4'), config)

    def test_inputs_unmodified(self):
        before = copy.deepcopy((self.batches, self.groups))
        self.clock.check_signal(signal(2, 'immediate', 2, 1, 'GREEN'))
        self.assertEqual((self.batches, self.groups), before)


class NativeClockTest(unittest.TestCase):
    def setUp(self):
        self.groups = {'7': {'1': 1, '3': 0, '4': 1, '7': 1, '8': 1}}
        self.source = 'RW_SIGNAL_NATIVE_CLOCKS = "7:concurrent_p1_p2:120.000000:0.000000:1101"\n'
        self.options = native_clock_options(self.source, self.groups)
        self.rows = [dict(kind='signal', sc_no='7', offset='0', p1_green='67',
                         p2_green='90', p3_green='0', p4_green='24')]
        self.rows += [dict(kind='signal_sg', sc_no='7', dsd_no=str(sg), offset='0',
                         p1_green=str(a), p2_green=str(b), green_sec='120')
                      for sg, a, b in ((4, 0, 67), (8, 0, 67), (7, 0, 90), (1, 93, 117))]

    def test_sc7_own_amber_and_direct_transition_oracle_require_source_optin(self):
        native = CommandClock({1: self.rows}, self.groups, {}, native_clock_plans=self.options)
        old = CommandClock({1: self.rows}, self.groups, {})
        # Source phase67 enters AMBER; pre-step command66 drives frame67.
        native.check_signal(signal(66, 'immediate', 7, 4, 'AMBER'))
        native.check_signal(signal(67, 'post_step', 7, 4, 'AMBER'))
        old.check_signal(signal(66, 'immediate', 7, 4, 'GREEN'))
        for sc, sg, value in ((7, 4, 'AMBER'), (7, 8, 'AMBER'), (7, 7, 'GREEN'), (7, 3, 'RED')):
            self.assertEqual(native.check_signal(signal(68, 'immediate', sc, sg, value)), value)
            self.assertEqual(native.check_signal(signal(69, 'post_step', sc, sg, value)), value)
            self.assertEqual(native.expected_urban_state(str(sc), native.snapshots[0]['signals'][str(sc)], str(sg), 68), value)
        old.check_signal(signal(68, 'immediate', 7, 4, 'RED'))
        with self.assertRaisesRegex(ValueError, 'Command clock mismatch'):
            old.check_signal(signal(68, 'immediate', 7, 4, 'AMBER'))
        self.assertEqual(native_clock_options('', self.groups), {})
        self.assertEqual(native_clock_options('RW_SIGNAL_NATIVE_CLOCKS = ""', self.groups), {})

    def test_native_tokens_and_axis_constraints_fail_closed(self):
        for text in (self.source + self.source,
                     self.source.replace('1101', '110x'),
                     self.source.replace('7:concurrent', '16:concurrent'),
                     self.source.replace('120.000000', 'NaN'),
                     'RW_SIGNAL_NATIVE_CLOCKS = dynamic_variable'):
            with self.assertRaises(ValueError): native_clock_options(text, self.groups)
        with self.assertRaisesRegex(ValueError, 'Incomplete native'):
            native_clock_options(self.source, {**self.groups, '16': {'1': 0}})
        for key, value in (('p1_green', '88'), ('p2_green', '89'), ('p3_green', '1'), ('offset', '1')):
            bad = copy.deepcopy(self.rows); bad[0][key] = value
            with self.assertRaises(ValueError):
                CommandClock({1: bad}, self.groups, {}, native_clock_plans=self.options)
        continued = 'RW_SIGNAL_NATIVE_CLOCKS = "7:concurrent_p1_p2:" & _\n  "120:0:1101"\n'
        self.assertEqual(native_clock_options(continued, self.groups), self.options)

    def test_all17_actual_generated_plan_and_adapter_rows_match_sig(self):
        from diagnostics.test_native_vbs_clock import source_plan, ROOT, parse_sig
        from diagnostics.com_execution_equivalence.verify_pair import _plan_groups
        from scripts.derive_signal_group_actuation_plan_mainline_20260825 import render_vbs
        from evaluation.controllers import vissim_stackelberg_adapter as adapter
        raw, audit = source_plan()
        text = render_vbs(raw)
        groups, _ = _plan_groups(text.encode(), True)
        native = native_clock_options(text, groups)
        rows = []
        for sc, node in raw['controllers'].items():
            offset = node['native_clock_basis']['reference_offset_sec']
            rows.append(dict(kind='signal', sc_no=sc, offset=offset,
                             **{p+'_green': value for p, value in node['axis_green_sec'].items()}))
            rows.extend(adapter.signal_group_action_rows(raw, int(sc), node['axis_green_sec'], offset, 'proof'))
        clock = CommandClock({1: rows}, groups, {}, native_clock_plans=native)
        count = 0
        for sc, source in audit['controllers'].items():
            program = parse_sig(ROOT / source['program'], 1)
            for sec in range(1, int(program.cycle_length_sec)+1):
                for sg in source['owned_signal_groups']:
                    expected = program.state_at(sec, sg)
                    clock.check_signal(signal(sec + 1, 'post_step', sc, sg, program.state_at(sec + 1, sg)))
                    clock.check_signal(signal(sec, 'immediate', sc, sg, program.state_at(sec + 1, sg)))
                    count += 1
        self.assertEqual(count, 20160)


if __name__ == '__main__': unittest.main()
