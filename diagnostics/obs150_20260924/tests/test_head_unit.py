"""WP-B1 B5: obs150_head_window on synthetic chunks (plan V0-3 "boundary synthetic cases").

One COM-owned head SC7 SG1 on link 70. The window (750, 900] has red, green,
amber and the ±0.005 s records at the integer green endpoints that only the
file order can place (CONTRACT 2.4): 'after' (an earlier row already shows
a later step), 'before' (a later row still shows an earlier step) and
'ambiguous' (neither; D8, never counted as qualified). The tail (Vehs minus
records in the file) counts only when the last second (899, 900] is green.
Records at the window edges 750 and 900 are placed by their ordinal, not by
the file order (WindowEdges). A COM write at the stop t reaches the heads at
t+1 (CONTRACT 2.3), so every log here writes one second before the green
endpoint it makes: GREEN at 759 opens (760, ...].
"""
from __future__ import annotations

import dataclasses
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_fixtures as fx  # noqa: E402
from contract_fixtures import c as oc  # noqa: E402
from evaluation.controllers import obs150_head_window as hw  # noqa: E402
from evaluation.controllers import obs150_signal_clock as sc  # noqa: E402

SHA_TABLE, SHA_CONFIG = 'c' * 64, 'd' * 64
HEAD, EVIDENCE, OTHER = 960001, 960002, 960003
WINDOW = {'start_s': 750, 'end_s': 900}
EDGES = (750, 900)


def table():
    geometry = {'link_length_m': 60.0, 'lane_count': 2}
    return oc.validate_detector_rows((
        oc.DetectorRow(HEAD, HEAD, 'head', '11|7-1', 70, 1, 50.0, 'exact', 'at', 'head:11', (), geometry),
        oc.DetectorRow(EVIDENCE, EVIDENCE, 'headfree', '10565', 10565, 1, 1.0, 'exact', 'down', 'headfree:10565',
                       (oc.SegmentPiece(10565, 0.0, 1.0, (1,)),), geometry),
        oc.DetectorRow(OTHER, OTHER, 'headfree', '10570', 10570, 1, 1.0, 'exact', 'down', 'headfree:10570',
                       (oc.SegmentPiece(10570, 0.0, 1.0, (1,)),), geometry)))


def context(rows=None):
    rows = table() if rows is None else rows
    head = {'head_id': '11', 'link': '70', 'lane': 1, 'position_m': 50.0, 'sc': '7', 'sg': '1'}
    return oc.Obs150Context(
        manifest_sha256='a' * 64, network_sha256='b' * 64, detector_csv_path='t.csv', detector_csv_sha256=SHA_TABLE,
        detectors=rows, boundaries=oc.group_boundaries(rows), chain_links={}, chain_internal_connectors=frozenset(),
        offramps={}, ramp_arrivals={}, source_refs={}, chain_end_refs={},
        headfree_refs={'10565': 'headfree:10565', '10570': 'headfree:10570'}, x10643_exit_ref='x10643_exit:10643',
        destination_refs={}, lane_map_10643={}, route_destinations_10643={},
        head_groups={('70', 'p1'): (head,)}, sig_table={}, source_schedule={})


# (dcp, t_entry) in file order; the comment is the head record's expected label with the green of LOG_TAIL_GREEN
ROWS = [
    (HEAD, 755.30),       # red                                       not_green
    (HEAD, 760.00),       # green start; the next row is at 759.99 -> before -> tau 760   not_green
    (EVIDENCE, 759.99),
    (EVIDENCE, 760.01),
    (HEAD, 760.00),       # an earlier row is at 760.01 -> after -> tau 760.05           green
    (HEAD, 775.50),       # green
    (HEAD, 790.00),       # green end, nothing within 0.2 s -> ambiguous                   ambiguous
    (HEAD, 790.30),       # amber (written at 789, on the heads from 790)                  not_green
    (OTHER, 849.99),
    (HEAD, 850.00),       # green start at 850; the next row is at 849.98 -> before         not_green
    (EVIDENCE, 849.98),
    (HEAD, 870.00),       # near an integer that is no endpoint: plain (a, b]              green
    (HEAD, 899.30),       # green
]
TAIL = 2
LOG_TAIL_GREEN = [(759, '7', '1', 'write', 'GREEN'), (789, '7', '1', 'write', 'AMBER'), (792, '7', '1', 'write', 'RED'),
                  (849, '7', '1', 'write', 'GREEN')]      # green (760, 790], (850, 900]


def chunk(rows=ROWS):
    ordinals, out = {}, []
    for seq, (dcp, t) in enumerate(rows):
        ordinals[dcp] = ordinals.get(dcp, 0) + 1
        out.append(oc.MerRow(seq + 100, dcp, t, None, 1000 + seq, 100, 30.0, 4.5, ordinals[dcp]))
    return out


def raw_state(rows=ROWS, tail=TAIL, sim_sec=900, max_t_any=899.30):
    counts = {str(d): sum(1 for dcp, _ in rows if dcp == d) for d in (HEAD, EVIDENCE, OTHER)}
    vehs = dict(counts, **{str(HEAD): counts[str(HEAD)] + tail})
    obs = {'sim_sec': sim_sec, 'detectors': vehs, 'detectors_cum': dict(vehs),
           'mer': {'records_cum_by_dcp': counts, 'max_t_any': max_t_any},
           'detector_config': {'sha256': SHA_TABLE}}
    return {oc.RAW_STATE_KEY: obs, 'run_provenance': {'run_id': 'run1', 'manifest_path': 'unused'}}


def clocks(events, *, verified=True, complete=True):
    log = {'scs': ['7'], 'start': {'7-1': {'owner': 'com', 'state': 'RED', 'verified': verified}},
           'events': [list(e) for e in events], 'complete': complete}
    return sc.windows(log, {}, WINDOW)


def build(raw=None, rows=ROWS, events=LOG_TAIL_GREEN, **keywords):
    keywords.setdefault('boundaries', {'headfree:10565': {'cross': 4}})
    keywords.setdefault('config_sha256', SHA_CONFIG)
    return hw.build(raw_state(rows) if raw is None else raw, context(), keywords.pop('clocks', None) or clocks(events),
                    chunk(rows), **keywords)


class HeadWindow(unittest.TestCase):
    def test_interface_signature(self):
        self.assertEqual(oc.check_module('evaluation.controllers.obs150_head_window'),
                         ['evaluation.controllers.obs150_head_window.build'])

    def test_labels_of_every_boundary_case(self):
        obs = raw_state()[oc.RAW_STATE_KEY]
        assignment = oc.assign_window(obs, chunk())
        counts, labels = hw.classify_entries(chunk(), assignment.entries[HEAD], [(760, 790), (850, 900)], EDGES)
        self.assertEqual([label for _, label in labels],
                         ['not_green', 'not_green', 'green', 'green', 'ambiguous', 'not_green', 'not_green',
                          'green', 'green'])
        self.assertEqual(counts, {'green': 4, 'not_green': 4, 'ambiguous': 1})

    def test_tail_in_a_green_last_second_is_qualified(self):
        window = build()
        (row,) = window['heads']
        self.assertEqual({k: row[k] for k in oc.HEAD_COUNT_KEYS},
                         {'crossings': 11, 'qualified_crossings': 4 + TAIL, 'green_sec': 30 + 50, 'native_sec': 0,
                          'controlled_sec': 150, 'unverified_sec': 0, 'boundary_ambiguous': 1})
        self.assertEqual({k: row[k] for k in oc.HEAD_IDENTITY_KEYS},
                         {'head_id': '11', 'link': '70', 'lane': 1, 'position_m': 50.0, 'sc': '7', 'sg': '1'})
        self.assertEqual((window['start_sec'], window['end_sec'], window['clock_complete'],
                          window['bypass_link_exits'], window['config_sha256']),
                         (750, 900, True, {'403': 4}, SHA_CONFIG))
        oc.validate_head_window_v2(window, end_sec=900, detector_config_sha256=SHA_TABLE)

    def test_tail_in_a_red_last_second_is_not(self):
        (row,) = build(events=LOG_TAIL_GREEN[:3])['heads']
        # green is (760, 790] only: 760 after, 775.5; 790 still ambiguous; 850.00 is no endpoint now
        self.assertEqual((row['crossings'], row['qualified_crossings'], row['green_sec'], row['boundary_ambiguous']),
                         (11, 2, 30, 1))

    def test_before_at_a_green_end_is_green(self):
        rows = ROWS[:7] + [(EVIDENCE, 789.99)] + ROWS[7:]
        (row,) = build(rows=rows)['heads']
        self.assertEqual((row['qualified_crossings'], row['boundary_ambiguous']), (5 + TAIL, 0))

    def test_unverified_time_invalidates_the_window(self):
        events = [(759, '7', '1', 'write', 'GREEN'), (799, '7', '1', 'fail', 'RED', 'ERR:readback=GREEN'),
                  (849, '7', '1', 'write', 'GREEN')]       # green (760, 800], unverified (800, 850], green (850, 900]
        window = build(clocks=clocks(events, complete=False))
        (row,) = window['heads']
        self.assertFalse(window['clock_complete'])
        self.assertEqual((row['controlled_sec'], row['unverified_sec'], row['green_sec']), (100, 50, 40 + 50))

    def test_bypass_from_the_identity_on_the_bundle(self):
        raw = raw_state()
        obs = raw[oc.RAW_STATE_KEY]
        bundle = oc.Bundle(obs, tuple(chunk()), (), fx.frame(900, [(1, 10565, 1, 0.5), (2, 10565, 1, 1.0)]),
                           fx.frame(750, []))
        window = hw.build(raw, context(), clocks(LOG_TAIL_GREEN), chunk(), bundle=bundle, config_sha256=SHA_CONFIG)
        # Vehs(10565) = 3 rows in the chunk; N_[0,1)(900) = 1 (the vehicle at 1.0 m has crossed), N(750) = 0
        self.assertEqual(window['bypass_link_exits'], {'403': 3 + 1})
        with self.assertRaises(oc.ObsContractError):
            hw.build(raw, context(), clocks(LOG_TAIL_GREEN), chunk()[:-1], bundle=bundle, config_sha256=SHA_CONFIG)

    def test_config_sha_from_the_run_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'provenance.json'
            path.write_text(json.dumps({'run_id': 'run1', 'signal_observation': {'config_chain': [{'sha256': 'e' * 64}]}}))
            raw = raw_state()
            raw['run_provenance']['manifest_path'] = str(path)
            self.assertEqual(build(raw=raw, config_sha256=None)['config_sha256'], 'e' * 64)
            raw['run_provenance']['run_id'] = 'run2'
            with self.assertRaises(oc.ObsContractError):
                build(raw=raw, config_sha256=None)

    def test_t1_has_no_window(self):
        self.assertIsNone(build(raw=raw_state(rows=[], tail=0, sim_sec=1, max_t_any=None), rows=[]))

    def test_refusals(self):
        raw = raw_state()
        raw[oc.RAW_STATE_KEY]['detector_config']['sha256'] = 'f' * 64
        with self.assertRaises(oc.ObsContractError):        # the bundle used another detector table
            build(raw=raw)
        with self.assertRaises(oc.ObsContractError):        # no clock for the head SG
            hw.build(raw_state(), context(), {}, chunk(), boundaries={'headfree:10565': {'cross': 0}},
                     config_sha256=SHA_CONFIG)
        with self.assertRaises(oc.ObsLagError):             # tail with a lagging file
            build(raw=raw_state(max_t_any=898.9))
        for lane, position in ((2, 50.0), (1, 50.001), (1, 49.9999)):
            groups = {('70', 'p1'): ({'head_id': '11', 'link': '70', 'lane': lane, 'position_m': position,
                                      'sc': '7', 'sg': '1'},)}
            with self.subTest(lane=lane, position=position), self.assertRaises(oc.ObsContractError):
                # eligible head and its detector differ (lane, or position beyond the '%.6f' rounding)
                hw.build(raw_state(), dataclasses.replace(context(), head_groups=groups), clocks(LOG_TAIL_GREEN),
                         chunk(), boundaries={'headfree:10565': {'cross': 0}}, config_sha256=SHA_CONFIG)
        groups = {('70', 'p1'): ({'head_id': '11', 'link': '70', 'lane': 1, 'position_m': 50.0000004,
                                  'sc': '7', 'sg': '1'},)}
        window = hw.build(raw_state(), dataclasses.replace(context(), head_groups=groups), clocks(LOG_TAIL_GREEN),
                          chunk(), boundaries={'headfree:10565': {'cross': 0}}, config_sha256=SHA_CONFIG)
        self.assertEqual(window['heads'][0]['crossings'], 11)   # the CSV pos 50.000000 of a head at 50.0000004


class WindowEdges(unittest.TestCase):
    """A record at T-150 or T (±0.005) is placed by its ordinal (review fix: no ambiguity at a cut green).

    assign_window put it in (750, 900], so its step is (750, 750.1] or (899.9, 900]. A green
    that runs across the window edge makes the edge an interval endpoint; the file order
    must then agree or say nothing, and the opposite step raises.
    """
    START_GREEN = [(759, '7', '1', 'write', 'RED'), (849, '7', '1', 'write', 'GREEN')]    # (750, 760], (850, 900]

    def clocks(self, events, start):
        log = {'scs': ['7'], 'start': {'7-1': {'owner': 'com', 'state': start, 'verified': True}},
               'events': [list(e) for e in events], 'complete': True}
        return sc.windows(log, {}, WINDOW)

    def labels(self, rows, events, start='GREEN'):
        obs = raw_state(rows, tail=0, max_t_any=max(t for _, t in rows))[oc.RAW_STATE_KEY]
        assignment = oc.assign_window(obs, chunk(rows))
        green = self.clocks(events, start)['7-1']['green']
        counts, labels = hw.classify_entries(chunk(rows), assignment.entries[HEAD], green, EDGES)
        return counts, [(r.t_entry, label) for r, label in labels]

    def test_green_cut_at_both_edges_counts_without_file_evidence(self):
        rows = [(HEAD, 750.00), (EVIDENCE, 750.02), (HEAD, 800.00), (HEAD, 900.00)]
        self.assertEqual(self.clocks(self.START_GREEN, 'GREEN')['7-1']['green'], [(750, 760), (850, 900)])
        counts, labels = self.labels(rows, self.START_GREEN)
        self.assertEqual(labels, [(750.0, 'green'), (800.0, 'not_green'), (900.0, 'green')])
        self.assertEqual(counts['ambiguous'], 0)
        (row,) = build(raw=raw_state(rows, tail=0, max_t_any=900.0), rows=rows,
                       clocks=self.clocks(self.START_GREEN, 'GREEN'))['heads']
        self.assertEqual((row['crossings'], row['qualified_crossings'], row['boundary_ambiguous']), (3, 2, 0))

    def test_file_evidence_that_agrees(self):
        # an earlier row at 750.01 (step after 750); a later row at 899.99 (step up to 900)
        rows = [(EVIDENCE, 750.01), (HEAD, 750.00), (HEAD, 900.00), (EVIDENCE, 899.99)]
        counts, labels = self.labels(rows, self.START_GREEN)
        self.assertEqual(labels, [(750.0, 'green'), (900.0, 'green')])
        self.assertEqual(counts['ambiguous'], 0)

    def test_edges_outside_green_are_not_green(self):
        events = [(759, '7', '1', 'write', 'GREEN'), (849, '7', '1', 'write', 'RED')]         # (760, 850]
        counts, labels = self.labels([(HEAD, 750.00), (HEAD, 800.00), (HEAD, 900.00)], events, start='RED')
        self.assertEqual(labels, [(750.0, 'not_green'), (800.0, 'green'), (900.0, 'not_green')])
        self.assertEqual(counts['ambiguous'], 0)

    def test_interior_endpoints_keep_the_file_order_rule(self):
        # 760 and 850 are endpoints inside the window: nothing within 0.2 s -> ambiguous (D8)
        counts, labels = self.labels([(HEAD, 760.00), (HEAD, 850.00)], self.START_GREEN)
        self.assertEqual(labels, [(760.0, 'ambiguous'), (850.0, 'ambiguous')])

    def test_opposite_file_evidence_raises(self):
        def rows_at(*times):
            return [oc.MerRow(i, HEAD, t, None, 100 + i, 100, 30.0, 4.5, i + 1) for i, t in enumerate(times)]
        green = [(750, 760), (850, 900)]
        with self.assertRaises(oc.ObsContractError):    # a later row still in (749.9, 750]
            hw.classify_at_window_edge(rows_at(750.00, 749.99), 0, 750, EDGES, green)
        with self.assertRaises(oc.ObsContractError):    # an earlier row already in (900, 900.1]
            hw.classify_at_window_edge(rows_at(900.01, 900.00), 1, 900, EDGES, green)
        with self.assertRaises(oc.ObsContractError):    # 800 is no window edge
            hw.classify_at_window_edge(rows_at(800.00), 0, 800, EDGES, green)
        self.assertEqual(hw.classify_at_window_edge(rows_at(750.00, 750.01), 0, 750, EDGES, green), 'green')

    def test_lagging_tail_of_the_previous_window_as_evidence(self):
        """The chunk also holds the previous window's late rows; one at 749.99 after the edge record contradicts."""
        rows = [(HEAD, 750.00), (EVIDENCE, 749.99), (HEAD, 800.00)]
        obs = raw_state(rows, tail=0, max_t_any=800.0)[oc.RAW_STATE_KEY]
        obs['detectors'][str(EVIDENCE)] = 0          # EVIDENCE's row is ordinal 1 of the previous window
        assignment = oc.assign_window(obs, chunk(rows))
        self.assertEqual(assignment.entries[EVIDENCE], ())
        green = self.clocks(self.START_GREEN, 'GREEN')['7-1']['green']
        with self.assertRaises(oc.ObsContractError):
            hw.classify_entries(chunk(rows), assignment.entries[HEAD], green, EDGES)


if __name__ == '__main__':
    unittest.main()
