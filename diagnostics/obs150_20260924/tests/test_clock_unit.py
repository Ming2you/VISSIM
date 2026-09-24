"""WP-B1 B4: obs150_signal_clock on synthetic runner logs (ownership, fail, unverified time).

COM head delay (D10, CONTRACT 2.3): a COM write at the stop t reaches the heads
at the update t+1, so a COM green written at t and ended at t' is (t+1, t'+1].
The runner log's start is the state before the writes at T-150 and its events
are the stops T-150 <= t < T. OC accepts an event at T-150 once
patches/OC_B1_D10.patch is applied; while it is pending the tests that need one
run the patched validate_signal_log (applied in memory, test_capture_t1).
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_fixtures  # noqa: E402,F401
from contract_fixtures import c as oc  # noqa: E402
from evaluation.controllers import obs150_signal_clock as sc  # noqa: E402
import test_capture_t1 as patches  # noqa: E402

WINDOW = {'start_s': 750, 'end_s': 900}
SHA = 'a' * 64
# SC1004 as in the probe: offset 75, cycle 150, SG2 green [0, 45), SG5 green [48, 72)
TABLE = {'1004': oc.SigProgram('1004', 'C:\\n\\1004.sig', SHA, 1, 75, 150, {'2': ((0, 45),), '5': ((48, 72),)}),
         '7': oc.SigProgram('7', 'C:\\n\\7.sig', SHA, 1, 0, 100, {'1': ((90, 100), (0, 20)), '2': ()})}
D10_OC_PATCH = patches.PATCHES / 'OC_B1_D10.patch'
SIGLOG_VBS_PATCH = patches.PATCHES / 'VBS_B1_SIGLOG.patch'
D10_VBS_PATCH = patches.PATCHES / 'VBS_B1_D10.patch'
VBS_FILE = 'scripts/run_real_world_stackelberg_controller.vbs'


def integrated_text(relative, patch_files):
    """relative's text as the integrator will have it: each still pending patch applied in memory, in order."""
    text = (patches.ROOT / relative).read_text(encoding='utf-8')
    for patch in patch_files:
        if patches.patch_state(patch) == 'pending':
            text = patches.apply_patch(text, patches.file_sections(patch.read_text(encoding='utf-8'))[relative])
    return text


def contract_signal_log_validator():
    """validate_signal_log as the integrator will have it (events at T-150 allowed)."""
    return patches.patched_function(D10_OC_PATCH, patches.OC_FILE, oc, 'validate_signal_log')


def d10_windows(*args, **keywords):
    with mock.patch.object(oc, 'validate_signal_log', contract_signal_log_validator()):
        return sc.windows(*args, **keywords)


def log(events=(), *, meter_state='GREEN', verified=True, complete=True, native=('1004-2', '1004-5')):
    start = {key: {'owner': 'native'} for key in native}
    start['9106-1'] = {'owner': 'com', 'state': meter_state, 'verified': verified}
    return {'scs': sorted({k.split('-')[0] for k in start}, key=int), 'start': start, 'events': [list(e) for e in events],
            'complete': complete}


class Clock(unittest.TestCase):
    def test_interface_signature(self):
        self.assertEqual(oc.check_module('evaluation.controllers.obs150_signal_clock'),
                         ['evaluation.controllers.obs150_signal_clock.windows'])

    def test_t1_has_no_window(self):
        self.assertEqual(sc.windows(log(), TABLE, None), {})

    def test_native_program_with_offset(self):
        clocks = sc.windows(log(), TABLE, WINDOW)
        self.assertEqual(clocks['1004-2'], {'green': [(825, 870)], 'native_sec': 150, 'controlled_sec': 0,
                                            'unverified_sec': 0, 'complete': True})
        self.assertEqual(clocks['1004-5']['green'], [(873, 897)])
        self.assertEqual(sc.green_seconds(clocks['1004-2']), 45)

    def test_green_wrapping_the_cycle_end_is_one_interval(self):
        clocks = sc.windows(log(native=('7-1', '7-2')), TABLE, WINDOW)
        # (t mod 100) in [90, 100) or [0, 20): 790-819 and 890-899 (+900 closes the window)
        self.assertEqual(clocks['7-1']['green'], [(790, 820), (890, 900)])
        self.assertEqual(clocks['7-2']['green'], [])

    def test_com_writes_reach_the_heads_one_second_later(self):
        self.assertEqual(sc.COM_HEAD_DELAY_S, 1)
        clocks = sc.windows(log([(760, '9106', '1', 'write', 'RED'), (790, '9106', '1', 'write', 'GREEN'),
                                 (820, '9106', '1', 'write', 'AMBER'), (823, '9106', '1', 'write', 'RED')]),
                            TABLE, WINDOW)
        # start GREEN holds through the update at 760; the GREEN written at 790 governs 791-821
        self.assertEqual(clocks['9106-1'], {'green': [(750, 761), (791, 821)], 'native_sec': 0,
                                            'controlled_sec': 150, 'unverified_sec': 0, 'complete': True})

    def test_writes_at_the_window_edges(self):
        """A write at T-150 acts from T-149 (its slot T-150 keeps the start); a write at T-1 reaches only T+1."""
        events = [(750, '9106', '1', 'write', 'RED'), (870, '9106', '1', 'write', 'GREEN'),
                  (899, '9106', '1', 'write', 'RED')]
        clock = d10_windows(log(events), TABLE, WINDOW)['9106-1']
        self.assertEqual((clock['green'], clock['controlled_sec']), ([(750, 751), (871, 900)], 150))
        clock = d10_windows(log([(750, '9106', '1', 'write', 'GREEN')], meter_state='RED'), TABLE, WINDOW)['9106-1']
        self.assertEqual(clock['green'], [(751, 900)])
        # a fail at T-150 leaves the start slot verified; the window is still incomplete (the runner rule)
        events = [(750, '9106', '1', 'fail', 'RED', 'ERR:readback=GREEN'), (760, '9106', '1', 'write', 'GREEN')]
        clock = d10_windows(log(events, complete=False), TABLE, WINDOW)['9106-1']
        self.assertEqual((clock['green'], clock['unverified_sec'], clock['complete']), ([(750, 751), (761, 900)], 10, False))
        with self.assertRaises(oc.ObsContractError):        # before the window's first stop
            d10_windows(log([(749, '9106', '1', 'write', 'RED')]), TABLE, WINDOW)
        with self.assertRaises(oc.ObsContractError):        # the bundle stop T belongs to the next window
            d10_windows(log([(900, '9106', '1', 'write', 'RED')]), TABLE, WINDOW)

    def test_fail_is_unverified_until_the_next_successful_write(self):
        events = [(800, '9106', '1', 'fail', 'RED', 'ERR:readback=GREEN'), (850, '9106', '1', 'write', 'GREEN')]
        clock = sc.windows(log(events, complete=False), TABLE, WINDOW)['9106-1']
        self.assertEqual(clock, {'green': [(750, 801), (851, 900)], 'native_sec': 0, 'controlled_sec': 100,
                                 'unverified_sec': 50, 'complete': False})
        # an SG without a fail keeps its own clock complete only if the runner closed the log complete
        self.assertFalse(sc.windows(log(events, complete=False), TABLE, WINDOW)['1004-2']['complete'])
        with self.assertRaises(oc.ObsContractError):        # a window with a fail cannot be complete
            sc.windows(log(events, complete=True), TABLE, WINDOW)

    def test_unverified_start_is_carried_over(self):
        clock = sc.windows(log([(770, '9106', '1', 'write', 'RED')], verified=False, complete=False),
                           TABLE, WINDOW)['9106-1']
        self.assertEqual((clock['green'], clock['unverified_sec'], clock['controlled_sec']), ([], 21, 129))

    def test_programless_native_seconds_are_unverified(self):
        # G1 (09-24, sim 150): the ramp meters 9101-9108 are fixed-time SCs with no .sig file.
        # The runner owns them at the stop t=1 and the heads follow at t=2 (D10), so their
        # native state in (0, 2] is unknown: unverified seconds, not an error.
        window = {'start_s': 0, 'end_s': 150}
        events = [(1, '9101', '1', 'own', True), (1, '9101', '1', 'write', 'GREEN')]
        signal_log = {'scs': ['9101'], 'start': {'9101-1': {'owner': 'native'}},
                      'events': [list(e) for e in events], 'complete': True}
        clock = d10_windows(signal_log, TABLE, window, programless_scs=frozenset({'9101'}))['9101-1']
        self.assertEqual(clock, {'green': [(2, 150)], 'native_sec': 0, 'controlled_sec': 148,
                                 'unverified_sec': 2, 'complete': False})
        with self.assertRaises(oc.ObsContractError):   # unmarked, a native SC without a program stays an error
            d10_windows(signal_log, TABLE, window)
        with self.assertRaises(oc.ObsContractError):   # an SC cannot be both program-less and programmed
            d10_windows(signal_log, TABLE, window, programless_scs=frozenset({'1004'}))

    def test_ownership_changes(self):
        # own(true) with the write at the same stop: verified at once; own(false): the program again.
        # Both move the slot owner one second later, like a write.
        events = [(800, '1004', '2', 'own', True), (800, '1004', '2', 'write', 'RED'),
                  (840, '1004', '2', 'write', 'GREEN'), (850, '1004', '2', 'own', False)]
        clock = sc.windows(log(events), TABLE, WINDOW)['1004-2']
        # native 750-800 (program red), COM 801-850 (RED, GREEN from 841), native 851-899 (program green to 870)
        self.assertEqual(clock, {'green': [(841, 870)], 'native_sec': 100, 'controlled_sec': 50,
                                 'unverified_sec': 0, 'complete': True})
        # own(true) without a write: unknown state until the next successful write
        events = [(800, '1004', '2', 'own', True), (830, '1004', '2', 'write', 'GREEN')]
        clock = sc.windows(log(events, complete=False), TABLE, WINDOW)['1004-2']
        self.assertEqual(clock, {'green': [(831, 900)], 'native_sec': 51, 'controlled_sec': 69,
                                 'unverified_sec': 30, 'complete': False})

    def test_frame_advance_one_emulation_is_the_native_clock(self):
        """D10: a runner that writes at the stop t the program state of t+1 reproduces the native heads.

        That is SignalClockPosition's frame advance 1 (VBS OBS150_FRAME_ADVANCE); advance 0 is one second late.
        """
        for key in ('1004-2', '1004-5', '7-1'):
            no, sg = key.split('-')
            native = sc.windows(log(native=(key,)), TABLE, WINDOW)[key]
            for advance, expected in ((1, native['green']), (0, [(a + 1, min(b + 1, 900)) for a, b in native['green']])):
                def state(t, advance=advance, no=no, sg=sg):
                    return 'GREEN' if sc.program_green_at(TABLE[no], sg, t + advance) else 'RED'
                # the emulating runner writes every stop whose state differs from the stop before
                events = [(t, no, sg, 'write', state(t)) for t in range(750, 900) if state(t) != state(t - 1)]
                document = log(events, native=())
                document['start'] = {key: {'owner': 'com', 'state': state(749), 'verified': True}}
                document['scs'] = [no]
                with self.subTest(key=key, advance=advance):
                    clock = d10_windows(document, TABLE, WINDOW)[key]
                    self.assertEqual(clock['green'], [iv for iv in expected if iv[0] < iv[1]])

    def test_refusals(self):
        with self.assertRaises(oc.ObsContractError):        # a write to a native-owned SG
            sc.windows(log([(800, '1004', '2', 'write', 'GREEN')]), TABLE, WINDOW)
        with self.assertRaises(oc.ObsContractError):        # the window is one 150 s window
            sc.windows(log(), TABLE, {'start_s': 750, 'end_s': 850})
        with self.assertRaises(oc.ObsContractError):        # a native SC without its .sig program
            sc.windows(log(native=('5-2',)), TABLE, WINDOW)
        with self.assertRaises(oc.ObsContractError):        # an SG the program does not have
            sc.windows(log(native=('1004-9',)), TABLE, WINDOW)
        with self.assertRaises(oc.ObsContractError):        # event outside [T-150, T)
            sc.windows(log([(900, '9106', '1', 'write', 'RED')]), TABLE, WINDOW)

    def test_contract_and_runner_patches_carry_the_delay(self):
        """The COM head delay spans three owners: B1 (here), OC/CONTRACT (OC_B1_D10) and the runner.

        VBS_B1_SIGLOG makes the runner log exact for this clock (start before the writes at T-150,
        events from T-150 on). VBS_B1_D10 sets the native-clock emulation to the same delay
        (frame advance 1). A patch that neither applies nor reverses fails here.
        """
        for patch in (D10_OC_PATCH, SIGLOG_VBS_PATCH, D10_VBS_PATCH):
            with self.subTest(patch=patch.name):
                self.assertIn(patches.patch_state(patch), ('pending', 'applied'))
        oc_text = integrated_text(patches.OC_FILE, (D10_OC_PATCH,))
        self.assertIn('start_s <= t < end_s', oc_text)
        vbs_text = integrated_text(VBS_FILE, (SIGLOG_VBS_PATCH, D10_VBS_PATCH))
        self.assertIn('Sub Obs150SignalAppend(eventJson)\n    If CLng(obs150StopSec) >= CLng(obs150SigWindowStart) Then',
                      vbs_text)
        reset = vbs_text[vbs_text.index('Function Obs150SignalLogJson(T)'):]
        reset = reset[reset.index('If CLng(T) >= OBS150_DECISION_SEC Then'):reset.index('End Function')]
        self.assertIn('obs150SigStart.Add key, obs150SigNow(key)', reset)      # the start is taken before the writes at T
        self.assertIn('obs150SigStartTaken = True', reset)
        self.assertEqual(re.findall(r'(?m)^Const OBS150_FRAME_ADVANCE = (\d+)$', vbs_text), [str(sc.COM_HEAD_DELAY_S)])

    def test_validated_by_the_contract(self):
        clocks = sc.windows(log([(760, '9106', '1', 'write', 'RED')]), TABLE, WINDOW)
        oc.validate_clocks(clocks, WINDOW)
        self.assertEqual(sorted(clocks), ['1004-2', '1004-5', '9106-1'])


if __name__ == '__main__':
    unittest.main()
