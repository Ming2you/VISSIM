"""WP-B1 V0-3: green crossings of the probe's 5 heads in 750-900 s against the 0.1 s truth.

Heads (PR config heads.csv): SC1004 SG2/SG5 (link 71) and SC5 SG2 run native
.sig programs, SC9106 SG1 (ramp meter 10681, two lanes) is COM-owned. The
truth crossing is the gt_veh.csv front crossing (check_probe.gt_crossings);
it is green when the head shows GREEN in its 0.1 s step (x, x+0.1]: the
gt_sig.csv read at x for a native SG, the read at x-1 for the COM SG (head
update delay, test_clock_probe.head_state, CONTRACT 2.3). The head window is
obs150_head_window.build on the t900 capture of the probe chain
(test_capture_probe).

Every crossing of the 5 heads in this window was green (PRB review note), so
the same crossings are also classified against the three other SGs' clocks:
that gives real not-green passages on real times (cross-SG check). Synthetic
amber/red/boundary cases are in test_head_unit.py.
"""
from __future__ import annotations

import csv
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_capture_probe as probe  # noqa: E402
import test_clock_probe as clock_probe  # noqa: E402
from contract_fixtures import c as oc  # noqa: E402
from evaluation.controllers import obs150_head_window as hw  # noqa: E402
from evaluation.controllers import obs150_signal_clock as sc  # noqa: E402

SHA_TABLE, SHA_CONFIG = 'c' * 64, 'd' * 64
T = 900


def probe_context(table):
    positions = {}
    with open(probe.PROBE_CONFIG / 'heads.csv', newline='', encoding='ascii') as handle:
        for r in csv.DictReader(handle):
            positions[r['head_no']] = float(r['pos'])
    groups = {}
    for row in table:
        if row.role == 'head':
            head, sc_no, sg = oc.parse_head_ref(row.ref)
            groups.setdefault((str(row.link), f'SC{sc_no}_SG{sg}'), []).append(
                {'head_id': head, 'link': str(row.link), 'lane': row.lane, 'position_m': positions[head],
                 'sc': sc_no, 'sg': sg})
    return oc.Obs150Context(
        manifest_sha256='a' * 64, network_sha256='b' * 64, detector_csv_path='probe.csv', detector_csv_sha256=SHA_TABLE,
        detectors=table, boundaries=oc.group_boundaries(table), chain_links={}, chain_internal_connectors=frozenset(),
        offramps={}, ramp_arrivals={}, source_refs={}, chain_end_refs={},
        headfree_refs={'10565': 'headfree:10565', '10570': 'headfree:10570'}, x10643_exit_ref='x10643_exit:10643',
        destination_refs={}, lane_map_10643={}, route_destinations_10643={},
        head_groups={k: tuple(v) for k, v in groups.items()}, sig_table={}, source_schedule={})


@unittest.skipUnless(probe.HAVE_PROBE, probe.SKIP_REASON)
class V03HeadGreenCrossings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root, metas = probe.probe_chain()
        cls.table = probe.probe_table()
        cls.context = probe_context(cls.table)
        cls.chunk = probe.chain_chunk(root, metas[T])
        obs = probe.bundle_obs(T, metas[T])
        obs['detector_config'] = {'sha256': SHA_TABLE}
        cls.raw = {oc.RAW_STATE_KEY: obs}
        cls.sig_table = clock_probe.probe_sig_table()
        cls.clocks = sc.windows(clock_probe.probe_signal_log(cls.sig_table), cls.sig_table, clock_probe.WINDOW)
        cls.assignment = oc.assign_window(obs, cls.chunk)
        cls.window = hw.build(cls.raw, cls.context, cls.clocks, cls.chunk,
                              boundaries={'headfree:10565': {'cross': 0}}, config_sha256=SHA_CONFIG)
        cls.events = probe.ground_truth_events()
        cls.truth = probe.ground_truth_signal()

    def truth_green(self, key, t_step_end):
        """The head state in the crossing's step (x, x+0.1]: the read at x (native) or at x-1 (COM head delay)."""
        return clock_probe.head_state(self.truth, key, round(t_step_end * 10) - 1) == oc.GREEN_STATE

    def head_rows(self):
        return [r for r in self.table if r.role == 'head']

    def test_window_is_contract_valid(self):
        oc.validate_head_window_v2(self.window, end_sec=T, detector_config_sha256=SHA_TABLE)
        self.assertEqual((self.window['start_sec'], self.window['clock_complete'], len(self.window['heads'])),
                         (750, True, 5))
        self.assertEqual(self.window['bypass_link_exits'], {'403': 0})

    def test_counts_equal_the_truth(self):
        rows = {r['head_id']: r for r in self.window['heads']}
        for row in self.head_rows():
            head, sc_no, sg = oc.parse_head_ref(row.ref)
            key = f'{sc_no}-{sg}'
            truth_all = {e[1] for e in self.events if e[0] == row.dcp_no}
            truth_green = {e[1] for e in self.events if e[0] == row.dcp_no and self.truth_green(key, e[3])}
            with self.subTest(head=head):
                self.assertEqual(rows[head]['crossings'], len(truth_all))
                self.assertEqual(rows[head]['qualified_crossings'], len(truth_green))
                self.assertEqual(rows[head]['boundary_ambiguous'], 0)
                self.assertEqual(rows[head]['green_sec'], sc.green_seconds(self.clocks[key]))
        self.assertEqual({h: (r['crossings'], r['qualified_crossings']) for h, r in rows.items()},
                         {'90030883': (5, 5), '90030880': (9, 9), '90030898': (3, 3), '90030899': (29, 29),
                          '70203': (4, 4)})

    def test_vehicles_equal_the_truth_for_every_clock(self):
        """Each head's crossings against its own SG and the three other SGs: same vehicles as the truth."""
        not_green = 0
        for row in self.head_rows():
            self.assertEqual(self.assignment.tails[row.dcp_no], 0)     # every t900 crossing is in the file
            for key in sorted(self.truth):
                counts, labels = hw.classify_entries(self.chunk, self.assignment.entries[row.dcp_no],
                                                     self.clocks[key]['green'], (T - 150, T))
                ours = {r.veh for r, label in labels if label == 'green'}
                truth = {e[1] for e in self.events if e[0] == row.dcp_no and self.truth_green(key, e[3])}
                with self.subTest(head=row.ref, clock=key):
                    self.assertEqual(counts['ambiguous'], 0)
                    self.assertEqual(ours, truth)
                not_green += counts['not_green']
        self.assertGreater(not_green, 20)


if __name__ == '__main__':
    unittest.main()
