"""WP-B1 V0-4: the signal clock against the probe's 0.1 s signal truth (gt_sig.csv, 750-900 s).

1500 steps x 4 SGs: SC1004 SG2/SG5 and SC5 SG2 run their native .sig program,
SC9106 SG1 (ramp meter) is COM-owned and written by the probe at 760/790/820/850.
gt_sig.csv holds the SigState read at every 0.1 s pause x (after a write at x).

Fixed here (CONTRACT 2.3, NATIVE_STEP_RULE, COM_HEAD_DELAY_S):
- native, 'program_state_at_step_end': the read at x is the program state at
  phase (x - offset) mod cycle and governs the next step (x, x+0.1]. Every step
  matches (6000/6000 with the COM SG below). 'program_state_at_step_start'
  (read at x = program at x - 0.1) misses every native transition in the
  window, so it is refused. The lead vehicle stopped at each native head moves
  in the first step of the clock's green: speed 0 at s, > 0 at s+0.1 (3/3).
- COM, D10: the read-back at x shows a write at once, but the heads take it at
  the next once-a-second update (Vissim 2020 manual 2.17.3, p. 616): the step
  (x, x+0.1] shows the read-back of x-1. After the GREEN written at 850 the
  stopped lead vehicles on both meter lanes keep speed 0 through 851.0 and
  move at 851.1, the first step of the clock's green (851, 900], exactly as at
  the native heads. The SimRes 1 replay found the same one-second lag (COM
  LDP(t) = source(t-1)). So a COM green written at t is (t+1, t'+1].
The probe's only COM head is on a freeway-behaviour link (W99), its native
heads on urban links (W74). Both lanes moving exactly 1.0 s late, and the same
lag at SimRes 1 on urban SCs, point to the update clock and not to W99; G1 D6
rechecks it at an urban COM head (1050-1200). Whether VBS SignalClockPosition's
"+offset" plan convention equals "- .sig offset" is WP-A's to check.
"""
from __future__ import annotations

import csv
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_capture_probe as probe  # noqa: E402
from contract_fixtures import c as oc  # noqa: E402
from evaluation.controllers import obs150_signal_clock as sc  # noqa: E402

WINDOW = {'start_s': 750, 'end_s': 900}


def probe_sig_table():
    return {no: sc.sig_program_from_file(no, path, prog) for no, (path, prog) in probe.probe_sig_files().items()}


def probe_signal_log(sig_table):
    """The runner-side log a v2 runner would have written for 750-900 (native SCs + the meter).

    start is the state before the writes at 750 (CONTRACT 4.3). The probe wrote
    nothing at 750, so the read-back at 750.0 is that state.
    """
    truth = probe.ground_truth_signal()
    writes = probe.meter_writes()
    assert not any(e[0] == WINDOW['start_s'] for e in writes)
    start = {f'{no}-{sg}': {'owner': 'native'} for no, program in sig_table.items() for sg in program.green_s}
    start['9106-1'] = {'owner': 'com', 'state': truth['9106-1'][7500], 'verified': True}
    events = [e for e in writes if WINDOW['start_s'] <= e[0] < WINDOW['end_s']]
    return {'scs': sorted({k.split('-')[0] for k in start}, key=int), 'start': start, 'events': events,
            'complete': True}


def head_state(truth, key, t10):
    """The state the heads of key show in the step (t10/10, t10/10 + 0.1].

    native: the read at the pause itself; COM: the read one second earlier
    (COM_HEAD_DELAY_S), which before 751 is the start (no write at 750).
    """
    if key != '9106-1':
        return truth[key][t10]
    return truth[key][max(WINDOW['start_s'] * 10, t10 - 10 * sc.COM_HEAD_DELAY_S)]


@unittest.skipUnless(probe.HAVE_PROBE, probe.SKIP_REASON)
class V04NativeStepRule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = probe_sig_table()
        cls.clocks = sc.windows(probe_signal_log(cls.table), cls.table, WINDOW)
        cls.truth = probe.ground_truth_signal()

    def test_the_rule_constant(self):
        self.assertIn(sc.NATIVE_STEP_RULE, oc.NATIVE_STEP_RULES)
        self.assertEqual(sc.NATIVE_STEP_RULE, 'program_state_at_step_end')

    def test_programs_come_from_the_sig_prog_element(self):
        # NEW-9: offsets live in <prog offset>, the inpx SC offset is 0 (SC5 uses bed7_n4dr150.sig)
        self.assertEqual({no: (p.prog_no, p.offset_s, p.cycle_s) for no, p in self.table.items()},
                         {'1004': (1, 75, 150), '5': (1, 36, 150)})
        self.assertEqual(self.table['1004'].green_s['2'], ((0, 45),))
        self.assertTrue(Path(self.table['5'].path).name.endswith('bed7_n4dr150.sig'))

    def test_every_step_matches_the_truth(self):
        self.assertEqual(sorted(self.truth), ['1004-2', '1004-5', '5-2', '9106-1'])
        compared, mismatches = 0, []
        for key in self.truth:
            for t10 in range(7500, 9000):
                predicted = oc.in_green(t10 / 10 + 0.05, self.clocks[key]['green'])
                compared += 1
                if predicted != (head_state(self.truth, key, t10) == oc.GREEN_STATE):
                    mismatches.append((key, t10))
        self.assertEqual(compared, 6000)
        self.assertEqual(mismatches, [])
        self.assertEqual({k: self.clocks[k]['green'] for k in self.truth},
                         {'1004-2': [(825, 870)], '1004-5': [(873, 897)], '5-2': [(786, 833)],
                          '9106-1': [(750, 761), (791, 821), (851, 900)]})
        self.assertTrue(all(self.clocks[k]['complete'] for k in self.truth))
        self.assertEqual((self.clocks['9106-1']['controlled_sec'], self.clocks['1004-2']['native_sec']), (150, 150))

    def test_the_com_read_back_is_one_second_ahead_of_the_heads(self):
        """Against the read-back at the pause itself (no delay) the COM clock misses 10 steps per write."""
        misses = sum(oc.in_green(t10 / 10 + 0.05, self.clocks['9106-1']['green'])
                     != (self.truth['9106-1'][t10] == oc.GREEN_STATE) for t10 in range(7500, 9000))
        self.assertEqual(misses, 10 * len(probe.meter_writes()))

    def test_state_at_step_start_is_refuted(self):
        misses = 0
        for key in ('1004-2', '1004-5', '5-2'):
            no, sg = key.split('-')
            program = self.table[no]
            for t10 in range(7500, 9000):
                phase = ((t10 - 1) / 10 - program.offset_s) % program.cycle_s
                alternative = any(a <= phase < b for a, b in program.green_s[sg])
                misses += alternative != (self.truth[key][t10] == oc.GREEN_STATE)
        self.assertEqual(misses, 6)   # two per native transition (green start and end) in the window

    def test_changes_are_on_whole_seconds(self):
        for key, states in self.truth.items():
            changes = [t10 for t10 in range(7501, 9001) if states[t10] != states[t10 - 1]]
            self.assertTrue(changes, key)
            self.assertTrue(all(t10 % 10 == 0 for t10 in changes), key)

    def test_native_green_governs_the_next_step(self):
        """Lead vehicle at each native head: speed 0 at the first GREEN read s, moving at s+0.1."""
        sys.dont_write_bytecode = True
        if str(probe.PT) not in sys.path:
            sys.path.insert(0, str(probe.PT))
        import check_probe
        frames = check_probe.load_gt(probe.PR)
        heads = {}
        with open(probe.PROBE_CONFIG / 'heads.csv', newline='', encoding='ascii') as handle:
            for r in csv.DictReader(handle):
                heads[f"{r['sc']}-{r['sg']}"] = (int(r['link']), int(r['lane']), float(r['pos']))
        starts = 0
        for key in ('1004-2', '1004-5', '5-2'):
            link, lane, position = heads[key]
            for a, _ in self.clocks[key]['green']:
                s10 = a * 10
                self.assertEqual((self.truth[key][s10 - 1], self.truth[key][s10]), ('RED', 'GREEN'))
                lead = lambda t10: max((v for v in frames[t10].values()
                                        if v[0] == link and v[1] == lane and v[2] <= position), key=lambda v: v[2])
                self.assertEqual(lead(s10)[3], 0.0, key)
                self.assertGreater(lead(s10 + 1)[3], 0.0, key)
                starts += 1
        self.assertEqual(starts, 3)

    def test_com_green_moves_the_vehicles_one_second_after_the_write(self):
        """D10 evidence (module docstring): GREEN written at 850, the meter's stopped lead vehicles move at 851.1.

        The 790 write found no queue; 850 is the one COM green start with stopped vehicles.
        851.1 is the first step of the clock's green (851, 900], as at the native heads.
        """
        sys.dont_write_bytecode = True
        if str(probe.PT) not in sys.path:
            sys.path.insert(0, str(probe.PT))
        import check_probe
        frames = check_probe.load_gt(probe.PR)
        self.assertIn([850, '9106', '1', 'write', 'GREEN'], probe.meter_writes())
        self.assertEqual((self.truth['9106-1'][8499], self.truth['9106-1'][8500]), ('RED', 'GREEN'))  # read-back at once
        green_start = next(a for a, _ in self.clocks['9106-1']['green'] if a > 850 - 1)
        self.assertEqual(green_start, 850 + sc.COM_HEAD_DELAY_S)
        heads = []
        with open(probe.PROBE_CONFIG / 'heads.csv', newline='', encoding='ascii') as handle:
            for r in csv.DictReader(handle):
                if (r['sc'], r['sg']) == ('9106', '1'):
                    heads.append((int(r['link']), int(r['lane']), float(r['pos'])))
        self.assertEqual(len(heads), 2)
        first_move = {}
        for link, lane, position in heads:
            def lead(t10):
                return max((v for v in frames[t10].values() if v[0] == link and v[1] == lane and v[2] <= position),
                           key=lambda v: v[2])
            vehicle = lead(green_start * 10)
            self.assertEqual(vehicle[3], 0.0)                               # still stopped at 851.0
            first_move[lane] = next(t10 for t10 in range(8500, 8600) if lead(t10)[3] > 0.0)
            self.assertLess(position - lead(first_move[lane] - 1)[2], 1.5)      # stopped at the stop line
        # native and COM alike: speed > 0 in the first step (a, a+0.1] of the clock's green
        self.assertEqual(first_move, {1: green_start * 10 + 1, 2: green_start * 10 + 1})


@unittest.skipUnless(probe.HAVE_PROBE, probe.SKIP_REASON)
class SigFiles(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix='obs150_b1_sig_'))
        self.addCleanup(shutil.rmtree, self.directory, True)
        self.path, self.prog = probe.probe_sig_files()['1004']

    def copy(self, data=None):
        target = self.directory / self.path.name
        target.write_bytes(self.path.read_bytes() if data is None else data)
        return target

    def test_non_integer_times_and_pins_are_refused(self):
        text = self.path.read_bytes()
        for old, new in ((b'<cmd display="1" begin="48000" />', b'<cmd display="1" begin="48500" />'),
                         (b'offset="75000"', b'offset="75500"')):
            with self.subTest(change=new):
                self.assertIn(old, text)
                target = self.copy(text.replace(old, new, 1))
                with self.assertRaises(oc.ObsContractError):
                    sc.sig_program_from_file('1004', target, self.prog)
        with self.assertRaises(oc.ObsContractError):
            sc.sig_program_from_file('1004', self.path, self.prog, sha256='0' * 64)
        with self.assertRaises(oc.ObsContractError):
            sc.sig_program_from_file('1004', self.path, 9)

    def test_run_folder_copies_must_match_the_table(self):
        table = probe_sig_table()
        for path, _ in probe.probe_sig_files().values():
            shutil.copyfile(path, self.directory / path.name)
        log = probe_signal_log(table)
        self.assertEqual(sc.windows(log, table, WINDOW, network_dir=self.directory),
                         sc.windows(log, table, WINDOW))
        target = self.directory / self.path.name
        target.write_bytes(target.read_bytes() + b'\n')
        with self.assertRaises(oc.ObsContractError):
            sc.windows(log, table, WINDOW, network_dir=self.directory)
        target.unlink()
        with self.assertRaises(oc.ObsContractError):
            sc.windows(log, table, WINDOW, network_dir=self.directory)


if __name__ == '__main__':
    unittest.main()
