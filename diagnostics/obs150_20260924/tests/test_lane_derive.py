"""WP-B2, plan B6: obs150_lane.derive on synthetic decisions of the contract_fixtures table.

The 900 s world exercises every lane-plant quantity with hand-checked numbers:
the 10643 ledger (recorded, tail, pre-window segment, in-segment removal,
destination / frame / removal labels), off splits, arrival and 10643 lane
shares, the freeway exit count with a chain removal, the origin boundary and
the 403 departures. The t=1 world checks the open-interval closure.
"""
from __future__ import annotations

import dataclasses
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_lane_support as sup  # noqa: E402
from test_lane_support import c  # noqa: E402

from evaluation.controllers import obs150_lane as lane  # noqa: E402

X = 'x10643_exit:10643'


def world_900():
    w = sup.World(900)
    # 10643 exit station p = 1651.7, x = 1651.8 (fixture geometry).
    w.set(X, 1, 3, tail=1)
    w.entry(X, 1, 101, 760.2)
    w.entry(X, 1, 102, 800.5)
    w.set(X, 2, 2, tail=1)
    w.entry(X, 2, 201, 770.0)
    w.frame_start += [(301, 10643, 1, 1651.72), (302, 10643, 2, 1651.75)]
    w.remove(302, 800.0, 10643, 1651.8)        # .err positions carry one decimal; 0.1 m past p is decidable
    w.frame_start.append(sup.frame_row(401, 126, 1, 152.0, decision=1126, route=2, kind='STATIC'))
    w.frame_end += [
        sup.frame_row(103, 126, 1, 151.0, decision=1126, route=3, kind='STATIC'),           # tail, beyond x
        sup.frame_row(202, 10643, 2, 1651.75, decision=1126, route=1, kind='STATIC'),       # tail, still in [p, x]
        sup.frame_row(102, 71, 1, 40.0, decision=1126, route=2, kind='STATIC', next_link=10634),
        sup.frame_row(301, 10635, 1, 5.0, decision=1126, route=1, kind='STATIC'),           # past its destination point
        sup.frame_row(401, 71, 1, 30.0, decision=1126, route=2, kind='STATIC'),             # crossed before T-150
        sup.frame_row(402, 126, 1, 153.0, decision=1140, route=2, kind='STATIC'),           # came from 10776
        sup.frame_row(900, 74, 1, 0.5),                                                     # origin segment [0, 1)
    ]
    w.remove(201, 850.0, 71, 70.0, decision=1126, route=1)
    w.remove(501, 760.0, 2, 1000.0, decision=1100, route=1)                                 # chain removal
    w.set('destination:10642', 1, 1)
    w.entry('destination:10642', 1, 101, 790.0)
    w.set('destination:10635', 1, 1, tail=1)
    w.set('off_entry:10481', 1, 10, tail=10)
    w.set('through:10481', 1, 90, tail=90)
    w.set('off_entry:10643', 1, 4, tail=4)
    w.set('off_entry:10643', 2, 6, tail=6)
    w.set('ramp_arrival:RM_C10681', 1, 3, tail=3)
    w.set('ramp_arrival:RM_C10681', 2, 1, tail=1)
    w.set('chain_end:FW_E', 1, 20, tail=20)
    w.set('chain_end:FW_W', 1, 10, tail=10)
    w.set('source:FW_E', 1, 150, tail=150)
    w.set('headfree:10565', 1, 7, tail=7)
    w.set('headfree:10570', 1, 2, tail=2)
    return w


def run(world, *, ground_truth=True, context=None):
    with tempfile.TemporaryDirectory() as tmp:
        state = sup.write_bundle(world, tmp, ground_truth=ground_truth)
    context = context or sup.fixture_context(world.rows)
    frame_end, frame_start = world.frames()
    return lane.derive(state, context, world.mer_rows(), world.err_rows(), frame_end, frame_start)


class Ledger10643(unittest.TestCase):
    def test_vehicle_ledger_and_composition(self):
        out = run(world_900())
        ledger = out['ledger_10643']
        got = {(v['veh'], v['lane'], v['via'], v['connector'], v['label_source']) for v in ledger['vehicles']}
        self.assertEqual(got, {(101, 1, 'mer', 10642, 'destination'), (102, 1, 'mer', 10634, 'frame'),
                               (201, 2, 'mer', 10635, 'removal'), (301, 1, 'mer', 10635, 'frame'),
                               (103, 1, 'tail', 10642, 'frame')})
        self.assertEqual(ledger['by_lane'], {'1': {'10634': 1, '10635': 1, '10642': 2}, '2': {'10635': 1}})
        self.assertEqual(ledger['tail_by_lane'], {'1': 1, '2': 1})
        self.assertEqual(out['offramp_10643_history']['off_composition'],
                         [[[10634, 0.25], [10635, 0.25], [10642, 0.5]], [[10635, 1.0]]])
        history = out['offramp_10643_history']
        self.assertEqual((history['information_cutoff_s'], history['history_start_s']), (900, 750))

    def test_d9_strict_run_fails_on_unidentified_tail(self):
        w = world_900()
        w.frame_end = [r for r in w.frame_end if r[0] != 103]
        with self.assertRaisesRegex(c.ObsContractError, 'D9'):
            run(w)

    def test_d9_operational_run_marks_the_tail_unidentified(self):
        w = world_900()
        w.frame_end = [r for r in w.frame_end if r[0] != 103]
        out = run(w, ground_truth=False)
        vehicles = out['ledger_10643']['vehicles']
        self.assertIn({'veh': None, 'lane': 1, 'via': 'tail', 'connector': None, 'label_source': 'unidentified'},
                      vehicles)
        self.assertEqual(len(vehicles), 5)
        self.assertEqual(out['offramp_10643_history']['off_composition'][0],
                         [[10634, 0.25], [10635, 0.25], [10642, 0.25], [None, 0.25]])

    def test_extra_unrecorded_vehicle_is_not_silently_labelled(self):
        w = world_900()
        w.frame_end.append(sup.frame_row(104, 10641, 1, 3.0, decision=1126, route=1, kind='STATIC'))
        with self.assertRaisesRegex(c.ObsContractError, 'D9'):
            run(w)

    def test_destination_record_while_still_upstream_is_a_contradiction(self):
        w = world_900()
        w.frame_end.append(sup.frame_row(101, 71, 1, 60.0, decision=1126, route=3, kind='STATIC'))
        with self.assertRaisesRegex(c.ObsContractError, 'still upstream'):
            run(w)

    def test_removal_downstream_of_the_destination_keeps_the_destination_label(self):
        """101 passed destination 10642 at 790.0 and was removed on 67 at 850.0: a normal trajectory."""
        w = world_900()
        w.remove(101, 850.0, 67, 30.0, decision=1126, route=3)
        out = run(w)
        ledger = out['ledger_10643']
        got = {(v['veh'], v['lane'], v['via'], v['connector'], v['label_source']) for v in ledger['vehicles']}
        self.assertIn((101, 1, 'mer', 10642, 'destination'), got)
        self.assertEqual(ledger['by_lane'], {'1': {'10634': 1, '10635': 1, '10642': 2}, '2': {'10635': 1}})

    def test_removal_on_a_destination_connector_after_its_record_keeps_the_label(self):
        w = world_900()
        w.remove(101, 850.0, 10642, 5.0, decision=1126, route=3)
        out = run(w)
        labels = {v['veh']: (v['connector'], v['label_source']) for v in out['ledger_10643']['vehicles']}
        self.assertEqual(labels[101], (10642, 'destination'))

    def test_removal_upstream_of_a_recorded_destination_is_a_contradiction(self):
        w = world_900()
        w.remove(101, 850.0, 71, 30.0, decision=1126, route=3)
        with self.assertRaisesRegex(c.ObsContractError, 'removed upstream of it'):
            run(w)

    def test_stationary_vehicle_in_the_exit_segment_is_not_a_crossing(self):
        w = world_900()
        w.frame_start.append((303, 10643, 1, 1651.71))     # in [p, x] at T-150 and still there at T
        w.frame_end.append((303, 10643, 1, 1651.78))
        out = run(w)
        self.assertEqual(len(out['ledger_10643']['vehicles']), 5)
        self.assertNotIn(303, {v['veh'] for v in out['ledger_10643']['vehicles']})

    def test_recorded_vehicle_already_past_p_before_the_window_is_a_contradiction(self):
        w = world_900()
        w.frame_start.append((102, 10643, 1, 1651.75))
        with self.assertRaisesRegex(c.ObsContractError, 'both recorded'):
            run(w)

    def test_empty_lane_takes_the_labels_of_vehicles_on_10643(self):
        w = sup.World(900)
        w.frame_end += [sup.frame_row(601, 10643, 2, 100.0, decision=1126, route=2, kind='STATIC'),
                        sup.frame_row(602, 10643, 2, 10.0)]          # before RD 1126 at 23.34 m: no route yet
        out = run(w)
        self.assertEqual(out['offramp_10643_history']['off_composition'],
                         [[[None, 1.0]], [[10634, 0.5], [None, 0.5]]])

    def test_frame_label_mirrors_physical_urban_transport_observe(self):
        context = sup.fixture_context()
        row = sup.frame_row(1, 71, 1, 10.0, decision=1126, route=2, kind='STATIC', next_link=10634)
        self.assertEqual(lane.frame_label(row, context), 10634)
        row[9] = 10642                                     # next link contradicts the static route
        self.assertIsNone(lane.frame_label(row, context))
        self.assertEqual(lane.frame_label(sup.frame_row(1, 126, 1, 151.0, decision=1126, route=1.0, kind='Static'),
                                          context), 10635)
        self.assertIsNone(lane.frame_label(sup.frame_row(1, 126, 1, 151.0, decision=1140, route=1, kind='STATIC'),
                                           context))

    def test_a_missing_exit_lane_tail_is_a_contract_error(self):
        w = world_900()
        context = sup.fixture_context(w.rows)
        with tempfile.TemporaryDirectory() as tmp:
            obs = sup.write_bundle(w, tmp)[c.RAW_STATE_KEY]
        frame_end, frame_start = w.frames()
        mer, err = w.mer_rows(), w.err_rows()
        terms = c.evaluate_boundaries(obs, context.detectors, frame_end, frame_start, err)
        assignment = c.assign_window(obs, mer)
        lane_2 = sup.key_of(w.rows, X, 2)
        broken = dataclasses.replace(assignment, tails={k: n for k, n in assignment.tails.items() if k != lane_2})
        with self.assertRaisesRegex(c.ObsContractError, 'lacks a tail of the 10643 exit lanes'):
            lane.ledger_10643(context, terms, broken, mer, err, frame_end, frame_start, strict=True)


class LaneParts(unittest.TestCase):
    def test_splits_shares_exits_source_departures(self):
        out = run(world_900())
        self.assertEqual(set(out), set(c.LANE_PART_KEYS))
        self.assertEqual(out['off_split']['10481'], {'downstream_veh': 90, 'off_veh': 10,
                                                     'post_branch_ramp_bypass_veh': 0, 'eligible_exits_veh': 100,
                                                     'ratio': 0.1})
        self.assertEqual(out['off_split']['10483']['ratio'], 0.0)
        self.assertEqual(out['offramp_10643_lane_shares'], [0.4, 0.6])
        self.assertEqual(out['ramp_arrival_shares'], {'RM_C10484': [1.0], 'RM_C10681': [0.75, 0.25]})
        self.assertEqual(out['freeway_exit_count'], {'value': 51, 'off_total': 20, 'chain_end_total': 30,
                                                     'chain_removals': 1})
        fw_e, fw_w = out['source_boundary']['FW_E'], out['source_boundary']['FW_W']
        self.assertEqual((fw_e['admitted_window'], fw_e['admitted_cum'], fw_e['interval_s']), (151, 551, 150))
        self.assertAlmostEqual(fw_e['recent_vph'], 3624.0, places=12)
        self.assertAlmostEqual(fw_e['schedule_integral_veh'], 750.0, places=12)
        self.assertAlmostEqual(fw_e['backlog_veh'], 199.0, places=12)
        self.assertEqual((fw_w['admitted_window'], fw_w['admitted_cum']), (0, 300))
        self.assertAlmostEqual(fw_w['backlog_veh'], 450.0, places=12)
        self.assertEqual(out['link_departures_window'], {'403': 9})
        self.assertEqual(out['edie_residuals'], {})

    def test_d11_late_removal_row_fails_a_verification_run(self):
        """A removal of (600, 750] first seen in the 900 s .err chunk is in neither window's R (D11)."""
        w = world_900()
        w.remove(502, 700.0, 2, 1000.0, decision=1100, route=1)             # chain link, previous window
        with self.assertRaisesRegex(c.ObsContractError, 'D11'):
            run(w)
        out = run(w, ground_truth=False)                                     # operational: unchanged counts
        self.assertEqual(out['freeway_exit_count']['chain_removals'], 1)

    def test_removal_straddling_an_inner_segment_end_fails_a_verification_run(self):
        """.err rounds to 0.1 m: 1651.7 may be 1651.65 (before p) or 1651.74 (in [p, x])."""
        w = world_900()
        w.removals = [r if r[1] != 302 else (800.0, 302, 10643, 1651.7, 1126, 1) for r in w.removals]
        with self.assertRaisesRegex(c.ObsContractError, r"\(302, 'x10643_exit:10643', 1651\.7\)"):
            run(w)
        out = run(w, ground_truth=False)                    # operational: counted by the rounded position
        self.assertEqual(out['ledger_10643'], run(world_900())['ledger_10643'])

    def test_ambiguous_removals_only_at_inner_segment_ends(self):
        context = sup.fixture_context()
        w = sup.World(900)
        for veh, link, pos in ((1, 10643, 1651.75), (2, 10643, 1651.8), (3, 10481, 0.0), (4, 10481, 0.95),
                               (5, 24, 499.9), (6, 24, 500.0), (7, 74, 1.0), (8, 74, 1.1), (9, 2, 1000.0)):
            w.remove(veh, 800.0, link, pos, decision=1100, route=1)
        w.remove(10, 700.0, 10481, 1.0, decision=1100, route=1)             # previous window: not this R
        self.assertEqual(lane.ambiguous_removals(context, w.err_rows(), 750, 900),
                         [(1, 'x10643_exit:10643', 1651.7), (4, 'off_entry:10481', 1.0),
                          (5, 'chain_end:FW_E', 499.9), (7, 'source:FW_E', 1.0)])

    def test_lane_values_need_exact_lane_terms(self):
        w = world_900()
        w.remove(777, 800.0, 10643, 0.5)                     # a removal inside off_entry:10643 [0, 1)
        with self.assertRaisesRegex(c.ObsContractError, 'lane_exact'):
            run(w)

    def test_t1_closure(self):
        w = sup.World(1)
        w.frame_end.append((1, 74, 2, 0.3))                   # inserted in (0, 1], not yet at the station
        out = run(w)
        self.assertEqual({o: r['ratio'] for o, r in out['off_split'].items()},
                         {o: 0.0 for o in sup.fx.OFFS})
        self.assertEqual(out['ramp_arrival_shares'], {'RM_C10484': [1.0], 'RM_C10681': [0.5, 0.5]})
        self.assertEqual(out['offramp_10643_lane_shares'], [0.5, 0.5])
        self.assertEqual(out['offramp_10643_history']['off_composition'], [[[None, 1.0]], [[None, 1.0]]])
        self.assertEqual((out['offramp_10643_history']['information_cutoff_s'],
                          out['offramp_10643_history']['history_start_s']), (1, 0))
        self.assertEqual(out['freeway_exit_count']['value'], 0)
        self.assertEqual(out['link_departures_window'], {'403': 0})
        fw_e = out['source_boundary']['FW_E']
        self.assertEqual((fw_e['admitted_window'], fw_e['admitted_cum'], fw_e['interval_s']), (1, 1, 1))
        self.assertEqual(fw_e['recent_vph'], 3600.0)
        self.assertEqual(fw_e['backlog_veh'], 0.0)
        self.assertEqual(out['edie_residuals'], {})

    def test_t1_rejects_an_off_ramp_count(self):
        w = sup.World(1)
        w.set('off_entry:10481', 1, 1)
        w.entry('off_entry:10481', 1, 5, 0.9)
        with self.assertRaisesRegex(c.ObsContractError, 't=1'):
            run(w)

    def test_frames_must_bound_the_interval(self):
        w = world_900()
        with tempfile.TemporaryDirectory() as tmp:
            state = sup.write_bundle(w, tmp)
        frame_end, frame_start = w.frames()
        with self.assertRaisesRegex(c.ObsContractError, 'Frames must be'):
            lane.derive(state, sup.fixture_context(), w.mer_rows(), w.err_rows(), frame_start, frame_end)


class Edie(unittest.TestCase):
    def test_weight_is_the_remaining_share_of_the_segment_average(self):
        self.assertEqual(lane.edie_weight(0.0, 25.0, 10.0), 1.0)
        self.assertEqual(lane.edie_weight(25.0, 25.0, 10.0), 0.0)
        self.assertAlmostEqual(lane.edie_weight(22.5, 25.0, 10.0), 0.5 / 3)   # halfway in the short last segment
        self.assertAlmostEqual(lane.edie_weight(10.0, 25.0, 10.0), 2 / 3)

    def test_entries_identity_on_a_synthetic_trajectory(self):
        """Constant-speed vehicles on a 25 m link: segment-average Edie flow + stock weights = entries."""
        length, seg, dt, t0, t1 = 25.0, 10.0, 0.1, 0.0, 30.0
        speeds = [2.0, 3.0, 1.5, 4.0, 2.5, 0.5]
        starts = [-10.0, 1.0, 5.0, 12.0, 20.0, -2.0]       # position at t0 (negative: not yet entered)
        nseg = 3
        dist = [0.0] * nseg
        entries = 0
        for x0, v in zip(starts, speeds):
            a, b = x0, x0 + v * (t1 - t0)
            entries += a < 0 <= b
            for j in range(nseg):
                lo, hi = j * seg, min((j + 1) * seg, length)
                dist[j] += max(0.0, min(b, hi) - max(a, lo))
        volume = sum(d / ((min((j + 1) * seg, length) - j * seg) * (t1 - t0)) * 3600 for j, d in enumerate(dist)) / nseg
        at_end = [x0 + v * (t1 - t0) for x0, v in zip(starts, speeds) if 0 <= x0 + v * (t1 - t0) <= length]
        at_start = [x0 for x0 in starts if 0 <= x0 <= length]
        estimate = lane.edie_entries(volume, t1 - t0, length, seg, at_end, at_start)
        self.assertAlmostEqual(estimate, entries, places=9)


class Interface(unittest.TestCase):
    def test_signature(self):
        self.assertEqual(c.check_module('evaluation.controllers.obs150_lane'),
                         ['evaluation.controllers.obs150_lane.derive'])


if __name__ == '__main__':
    unittest.main()
