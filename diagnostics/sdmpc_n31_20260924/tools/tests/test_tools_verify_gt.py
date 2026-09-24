"""WP-D D6: obs150_verify_gt.py - crossing engine, chain membership, window verdicts, real probe truth."""
from __future__ import annotations

import copy
import csv
import json
import shutil
import sys
import tempfile
import types
import unittest
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import synthetic_run as sr  # noqa: E402
import obs150_verify_gt as g  # noqa: E402
from n31_common import oc  # noqa: E402

PR = Path(r'D:\VISSIM_runs\20260923_obs150\probe\run_20260924_000152')
PR_CONFIG = Path(r'D:\VISSIM_runs\20260923_obs150\probe\config')
PR_NETWORK = Path(r'D:\VISSIM_runs\20260923_obs150\probe\network\obs150_probe.inpx')


def net():
    L = g.Link
    return g.Network.from_parts([
        L(1, False, None, None, None, None, 100.0), L(2, False, None, None, None, None, 50.0),
        L(9, False, None, None, None, None, 40.0),
        L(11, True, 1, 60.0, 9, 0.0, 20.0),          # off connector leaving 1 at 60 m (untracked target 9)
        L(12, True, 1, 99.8, 2, 0.0, 2.0),           # short continuation 1 -> 2 at the end
        L(13, True, 5, 10.0, 1, 30.0, 8.0),          # joins link 1 at 30 m from an untracked link 5
    ])


def P(link, lane, pos, speed=36.0):
    return g.Pos(link, lane, pos, speed, None, None)


class Engine(unittest.TestCase):
    def events(self, fa, fb, points, tracked=(1, 2, 11, 12), removed=None, route_end=None):
        engine = g.Engine(net(), points, tracked, removed or {}, route_end or {})
        return engine.step(100, fa, 101, fb), engine.anomalies

    def test_case_a_same_link(self):
        pts = [g.Point('p', 1, 40.0, frozenset((1,))), g.Point('q', 1, 40.0, None)]
        ev, an = self.events({7: P(1, 1, 39.5)}, {7: P(1, 1, 40.5)}, pts)
        self.assertEqual(sorted((e.pid, e.lane, e.kind) for e in ev), [('p', 1, 'clean'), ('q', 1, 'clean')])
        ev, _ = self.events({7: P(1, 1, 40.0)}, {7: P(1, 1, 41.0)}, pts)      # q >= x already: crossed before
        self.assertEqual(ev, [])
        ev, _ = self.events({7: P(1, 1, 39.0)}, {7: P(1, 1, 40.0)}, pts)      # front reaches x: crossed
        self.assertEqual(len(ev), 2)
        ev, _ = self.events({7: P(1, 2, 39.5)}, {7: P(1, 2, 40.5)}, pts)      # other lane: only the any-lane point
        self.assertEqual([e.pid for e in ev], ['q'])

    def test_lane_change_inside_the_step(self):
        pts = [g.Point('l1', 1, 40.0, frozenset((1,))), g.Point('l2', 1, 40.0, frozenset((2,)))]
        ev, _ = self.events({7: P(1, 1, 39.5)}, {7: P(1, 2, 40.5)}, pts)
        self.assertEqual(sorted((e.pid, e.lane, e.kind) for e in ev), [('l1', None, 'lane_change'), ('l2', None, 'lane_change')])

    def test_case_b_exit_through_connector(self):
        # x=50 lies before the off connector at 60: a vehicle leaving at 60 passed it; x=70 it did not.
        pts = [g.Point('before', 1, 50.0, None), g.Point('after', 1, 70.0, None)]
        ev, an = self.events({7: P(1, 1, 49.5, 36.0)}, {7: P(11, 1, 0.2)}, pts)
        # 49.5 -> the connector at 60 is out of reach in 0.1 s (1 m/0.1 s + 1 m slack): unexplained at both
        self.assertEqual(ev, [])
        self.assertEqual([a['kind'] for a in an], ['unexplained_exit', 'unexplained_exit'])
        ev, an = self.events({7: P(1, 1, 59.5, 36.0)}, {7: P(11, 1, 0.2)}, [g.Point('after', 1, 70.0, None),
                                                                                g.Point('mid', 1, 59.8, None)])
        self.assertEqual([(e.pid, e.kind) for e in ev], [('mid', 'exit')])
        self.assertEqual(an, [])

    def test_case_b_vanished_to_untracked_or_removed(self):
        pts = [g.Point('end', 1, 100.0, None)]
        # link 1 continues through connector 12 (tracked) at its end: vanishing there is unexplained,
        ev, an = self.events({7: P(1, 1, 99.7)}, {}, pts)
        self.assertEqual(ev, [])
        self.assertEqual(an[0]['kind'], 'unexplained_exit')
        # ... unless 12 is not recorded: then the end is the only candidate.
        ev, an = self.events({7: P(1, 1, 99.7)}, {}, pts, tracked=(1, 2, 11))
        self.assertEqual([e.kind for e in ev], ['exit'])
        # a removal inside the step is never a crossing and never an anomaly
        ev, an = self.events({7: P(1, 1, 99.7)}, {}, pts, tracked=(1, 2, 11), removed={7: [10.05]})
        self.assertEqual((ev, an), ([], []))

    def test_case_b_ambiguous_candidates(self):
        # untracked off connector 11 at 60 and the untracked continuation 12 at 99.8 are both in reach
        n = net()
        n.links[1] = n.links[1]._replace(length=61.0)
        n.out[1] = [n.links[11], n.links[12]._replace(from_pos=60.5)]
        engine = g.Engine(n, [g.Point('x', 1, 60.2, None)], (1, 2), {}, {})
        ev = engine.step(100, {7: P(1, 1, 59.9)}, 101, {})
        self.assertEqual(ev, [])
        self.assertEqual(engine.anomalies[0]['kind'], 'ambiguous_exit')

    def test_case_c_entry(self):
        pts = [g.Point('start', 11, 0.0, frozenset((1,))), g.Point('p1', 11, 1.0, None),
               g.Point('mid1', 1, 20.0, None), g.Point('mid2', 1, 35.0, None)]
        ev, _ = self.events({7: P(1, 1, 59.9)}, {7: P(11, 1, 0.3)}, pts)       # onto a connector: entry at 0
        self.assertEqual([(e.pid, e.kind, e.lane) for e in ev], [('start', 'entry', 1)])
        # entering link 1 from untracked 5 via connector 13 at 30 m: passed 20? no; 35? no (pos 30.4)
        ev, an = self.events({}, {8: P(1, 1, 30.4)}, pts)
        self.assertEqual((ev, an), ([], []))
        ev, an = self.events({}, {8: P(1, 1, 35.5, 200.0)}, pts)                 # 35 lies after the entry at 30
        self.assertEqual(([e.pid for e in ev], an), (['mid2'], []))
        ev, an = self.events({}, {8: P(1, 1, 35.5, 36.0)}, pts)                  # 30 m is out of 0.1 s reach
        self.assertEqual(ev, [])
        self.assertEqual({a['kind'] for a in an}, {'unexplained_entry'})

    def test_origin_link_input_and_short_connector_traverse(self):
        pts = [g.Point('origin', 2, 0.0, None)]
        n = net()
        n.into[2] = []                                                           # link 2 as an origin link
        engine = g.Engine(n, pts, (1, 2), {}, {})
        self.assertEqual([e.kind for e in engine.step(100, {}, 101, {9: P(2, 1, 0.0)})], ['entry'])
        engine = g.Engine(net(), [g.Point('c', 12, 1.0, None)], (1, 2, 12), {}, {})
        ev = engine.step(100, {9: P(1, 1, 99.7)}, 101, {9: P(2, 1, 0.5)})
        self.assertEqual([(e.pid, e.kind) for e in ev], [('c', 'traverse')])

    def test_chain_membership_pending_until_reappearance(self):
        n = net()
        engine = g.Engine(n, [], (1, 2), {}, {})
        m = g.ChainMembership(n, {1, 12, 2}, (1, 2), engine)
        m.step(100, {5: P(1, 1, 99.7), 6: P(1, 1, 59.9)}, 101, {6: P(11, 1, 0.2)})
        self.assertEqual(m.exits, [(6, 101)])            # onto the off connector: left the chain
        self.assertEqual({v: p['vanished_b10'] for v, p in m.pending.items()}, {5: 101})   # into unrecorded 12
        self.assertEqual(m.pending[5]['kind'], 'chain')
        m.step(101, {}, 102, {5: P(2, 1, 0.4)})
        self.assertEqual(m.pending, {})
        self.assertEqual(m.resolved[0]['outcome'], 'reappeared')
        m.step(102, {5: P(2, 1, 49.9)}, 103, {})         # network exit at the end of 2
        self.assertEqual(m.exits, [(6, 101), (5, 103)])

    def test_chain_membership_closes_the_window_deterministically(self):
        """Review fix 2a: pending vehicles are settled at the window end, never left 'unresolved'."""
        n = net()
        n.links[1] = n.links[1]._replace(length=101.5)          # 1 runs on 1.7 m past the start of 12
        def membership():
            engine = g.Engine(n, [], (1, 2), {}, {})
            return g.ChainMembership(n, {1, 12, 2}, (1, 2), engine)
        # (a) still on the unrecorded connector at e: no exit (a connector has no branch)
        m = membership()
        m.step(100, {5: P(1, 1, 99.7, 18.0)}, 101, {})           # reach 1.5 m: only 12 (99.8) is reachable
        m.close((10.0, 10.2), [])
        self.assertEqual((m.exits, m.anomalies, m.resolved[0]['outcome']), ([], [], 'on_chain_at_window_end'))
        # (b) removed on the unrecorded connector inside the window: an exit at the removal time; also for
        #     a vehicle that was already on it when the window began (never visible)
        m = membership()
        m.step(100, {5: P(1, 1, 99.7, 18.0)}, 101, {})
        m.close((10.0, 10.2), [{'vehicle_id': 5, 'time_sec': 10.15, 'link': 12, 'kind': 'lane_change_removal'},
                               {'vehicle_id': 8, 'time_sec': 10.05, 'link': 12, 'kind': 'lane_change_removal'},
                               {'vehicle_id': 9, 'time_sec': 10.25, 'link': 12, 'kind': 'lane_change_removal'},
                               {'vehicle_id': 10, 'time_sec': 10.1, 'link': 1, 'kind': 'lane_change_removal'}])
        self.assertEqual(sorted(m.exits), [(5, 102), (8, 101)])   # 9 is after e; 10 is on a recorded link
        self.assertEqual(m.pending, {})
        # (c) the link end is in reach too (fast vehicle): 'ambiguous' until evidence settles it
        m = membership()
        m.step(100, {5: P(1, 1, 99.7, 72.0)}, 101, {})           # reach 3 m: 12 at 99.8 and the end at 101.5
        self.assertEqual((m.pending[5]['kind'], m.pending[5]['candidates']), ('ambiguous', ['12', 'network_end']))
        m.close((10.0, 10.2), [])                                  # no frame at e: never guessed
        self.assertEqual([a['kind'] for a in m.anomalies], ['ambiguous_chain_exit'])
        self.assertEqual(m.exits, [])
        m = membership()
        m.step(100, {5: P(1, 1, 99.7, 72.0)}, 101, {})
        m.close((10.0, 10.2), [], frame_end={5: 12})               # VISSIM's frame at e: on 12
        self.assertEqual((m.exits, m.anomalies), ([], []))
        m = membership()
        m.step(100, {5: P(1, 1, 99.7, 72.0)}, 101, {})
        m.close((10.0, 10.2), [], frame_end={})                    # not in the network at e: left at the end of 1
        self.assertEqual((m.exits, m.resolved[0]['outcome']), ([(5, 101)], 'left_at_vanish'))
        # (d) a 'chain' vanish the frame contradicts (gone without a removal) is unexplained
        m = membership()
        m.step(100, {5: P(1, 1, 99.7, 18.0)}, 101, {})
        m.close((10.0, 10.2), [], frame_end={})
        self.assertEqual([a['kind'] for a in m.anomalies], ['unexplained_chain_vanish'])

    def test_connector_lane_mapping_makes_lane_changes_unknown(self):
        """B/C: the connector's first lane tells the lane a vehicle left/entered by; a traversed connector's
        lane is the one both ends give."""
        L = g.Link
        n = g.Network.from_parts([
            L(1, False, None, None, None, None, 100.0, lanes=2), L(2, False, None, None, None, None, 50.0, lanes=2),
            L(11, True, 1, 60.0, 9, 0.0, 20.0, 1, 1, 1),       # leaves lane 1 of link 1
            L(12, True, 1, 99.0, 2, 0.0, 2.0, 1, 1, 2)])       # lanes 1-2 of 1 -> lanes 1-2 of 2
        pts = [g.Point('l1', 1, 59.8, frozenset((1,))), g.Point('l2', 1, 59.8, frozenset((2,)))]
        engine = g.Engine(n, pts, (1, 2, 11, 12))
        ev = engine.step(100, {7: P(1, 1, 59.5)}, 101, {7: P(11, 1, 0.2)})     # lane 1 -> lane 1 of 11: clean
        self.assertEqual([(e.pid, e.lane, e.kind) for e in ev], [('l1', 1, 'exit')])
        engine = g.Engine(n, pts, (1, 2, 11, 12))
        ev = engine.step(100, {7: P(1, 2, 59.5)}, 101, {7: P(11, 1, 0.2)})     # from lane 2 it must have changed
        self.assertEqual(sorted((e.pid, e.lane, e.kind, e.lanes) for e in ev),
                         [('l1', None, 'exit', frozenset((1, 2))), ('l2', None, 'exit', frozenset((1, 2)))])
        c = [g.Point('c1', 12, 1.0, frozenset((1,))), g.Point('c2', 12, 1.0, frozenset((2,)))]
        engine = g.Engine(n, c, (1, 2))
        ev = engine.step(100, {7: P(1, 2, 98.9)}, 101, {7: P(2, 2, 0.5)})      # connector lane 2 at both ends
        self.assertEqual([(e.pid, e.lane, e.kind) for e in ev], [('c2', 2, 'traverse')])
        engine = g.Engine(n, c, (1, 2))
        ev = engine.step(100, {7: P(1, 2, 98.9)}, 101, {7: P(2, 1, 0.5)})      # ends disagree: lane unknown
        self.assertEqual(sorted((e.pid, e.lane) for e in ev), [('c1', None), ('c2', None)])


class LaneAttribution(unittest.TestCase):
    """Review fix 1: lane-unknown crossings are attributed by .mer, never counted twice."""
    R = __import__('collections').namedtuple('R', 'dcp_no link lane')
    M = __import__('collections').namedtuple('M', 'veh t_entry')

    def resolve(self, events, mer, rows=None, window=(750, 900)):
        rows = rows or [self.R(1, 26, 1), self.R(2, 26, 2)]
        by_pid = defaultdict(list)
        for dcp, ev in events:
            by_pid[f'dcp:{dcp}'].append(ev)
        return g.resolve_unknown_lanes(rows, by_pid, {d: {v: self.M(v, 0.0) for v in vs} for d, vs in mer.items()},
                                       window)

    def lc(self, dcp, veh=7, b10=8000, lanes=(1, 2)):
        return dcp, g.Event(f'dcp:{dcp}', veh, b10, None, 'lane_change', None if lanes is None else frozenset(lanes))

    def test_attributed_to_the_lane_mer_holds(self):
        res = self.resolve([self.lc(1), self.lc(2)], {2: [7]})
        self.assertEqual((res.attributed, res.failures, res.open, res.uncounted), ({2: {7: self.lc(2)[1]}}, [], [], []))

    def test_counted_twice_or_never_fails(self):
        self.assertEqual(self.resolve([self.lc(1), self.lc(2)], {1: [7], 2: [7]}).failures[0]['kind'],
                         'recorded_at_points_of_no_single_lane')
        self.assertEqual(self.resolve([self.lc(1), self.lc(2)], {}).failures[0]['kind'], 'not_recorded')

    def test_lane_without_a_point_explains_no_record(self):
        rows = [self.R(1, 26, 1)]                           # lane 2 has no point (a lane without a head)
        res = self.resolve([self.lc(1)], {}, rows)
        self.assertEqual((res.failures, len(res.uncounted)), ([], 1))
        res = self.resolve([self.lc(1, lanes=None)], {}, rows)     # lanes unknown: may be any lane
        self.assertEqual((res.failures, len(res.uncounted)), ([], 1))

    def test_last_second_stays_open_for_the_tail(self):
        res = self.resolve([self.lc(1, b10=8995), self.lc(2, b10=8995)], {})
        self.assertEqual([c['options'] for c in res.open], [[frozenset({1}), frozenset({2})]])
        self.assertEqual(res.failures, [])
        res = self.resolve([self.lc(1, b10=8995), self.lc(2, b10=8995)], {2: [7]})    # already written: resolved
        self.assertEqual((res.open, list(res.attributed)), ([], [2]))


class SyntheticWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix='n31_gt_')
        cls.syn = sr.SyntheticRun(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_pass_and_truth(self):
        result = g.verify(self.syn.run, out=Path(self.tmp) / 'v.json')
        self.assertEqual(result['verdict'], 'PASS')
        items = result['windows'][0]['items']
        truth = self.syn.truth()
        self.assertEqual(items['source']['by_road']['FW_W']['gt'], truth['source'])
        self.assertEqual(items['off_split']['by_off']['10485']['gt_off'], truth['off'])
        self.assertEqual(items['off_split']['by_off']['10485']['gt_through'], truth['through'])
        self.assertEqual(items['boundaries']['by_ref']['chain_end:FW_W']['gt'], truth['chain_end'])
        self.assertEqual(items['heads']['by_head']['70203']['gt_crossings'], truth['head'])
        self.assertEqual(items['freeway_exit_count']['gt'], truth['off'] + truth['chain_end'] + 1)   # + the removal
        tails = [r for r in items['detectors']['rows'] if r['tail']]
        self.assertTrue(tails and all(r['ok'] for r in tails))
        self.assertEqual(items['err_realtime']['final_removals_in_window'], 1)

    def test_each_wrong_quantity_fails_its_item(self):
        cases = {'off_split': lambda d: d['off_split']['10485'].update(off_veh=d['off_split']['10485']['off_veh'] + 1),
                 'freeway_exit_count': lambda d: d['freeway_exit_count'].update(value=d['freeway_exit_count']['value'] - 1),
                 'heads': lambda d: d['head_window']['heads'][0].update(qualified_crossings=0),
                 'boundaries': lambda d: d['boundaries']['source:FW_W'].update(cross=0),
                 'link_403': lambda d: d['link_departures_window'].update({'403': 3}),
                 'source': lambda d: d['source_boundary']['FW_W'].update(admitted_window=1)}
        original = copy.deepcopy(self.syn.derived)
        path = oc.resolve(self.syn.states[900][oc.RAW_STATE_KEY], oc.derived_path(900))
        try:
            for item, mutate in cases.items():
                derived = copy.deepcopy(original)
                mutate(derived)
                path.write_bytes(oc.canonical_json_bytes(derived) + b'\n')
                result = g.verify(self.syn.run, out=Path(self.tmp) / f'v_{item}.json')
                self.assertEqual(result['verdict'], 'FAIL', item)
                self.assertIs(result['windows'][0]['items'][item]['ok'], False, item)
        finally:
            path.write_bytes(oc.canonical_json_bytes(original) + b'\n')

    def test_points_on_unrecorded_links_are_reported_not_judged(self):
        syn = self.syn
        removed, route_end, removal_rows = g.read_removals(syn.err)
        tracked = {r.link for r in syn.rows}
        gt = g.collect(syn.run / 'gt_veh.csv', g.Network(syn.inpx), syn.rows, (750, 900), tracked, removed, route_end,
                       {26, 10771, 120}, g.read_gt_meta_steps(syn.run / 'gt_meta.csv'))
        gt['signals'] = g.read_gt_signals(syn.run / 'gt_sig.csv')
        gt['recorded_links'] = gt['recorded_links'] - {10485}
        derived = copy.deepcopy(syn.derived)
        derived['off_split']['10485']['off_veh'] += 5          # would FAIL if it were judged
        items = g.verify_window((750, 900), syn.states[900], derived, syn.rows, g.Network(syn.inpx), gt,
                                removal_rows, 'next')
        self.assertIsNone(items['off_split']['by_off']['10485']['ok'])
        self.assertEqual(items['off_split']['by_off']['10485']['not_recorded_links'], [10485])
        self.assertIsNone(items['boundaries']['by_ref']['off_entry:10485']['ok'])
        self.assertIs(items['boundaries']['by_ref']['source:FW_W']['ok'], True)
        # Review fix 2b: an entry that is not judged makes its item and the window INCOMPLETE, not PASS.
        self.assertIsNone(items['off_split']['ok'])
        self.assertIsNone(items['boundaries']['ok'])
        verdict, failed, not_judged = g.window_verdict(items)
        self.assertEqual((verdict, failed), ('INCOMPLETE', []))
        self.assertIn('off_split', not_judged)

    def test_green_rule_is_reported_both_ways(self):
        result = g.verify(self.syn.run, sig_rule='previous', out=Path(self.tmp) / 'v_prev.json')
        head = result['windows'][0]['items']['heads']['by_head']['70203']
        self.assertEqual(set(head['gt']), {'next', 'previous'})

    def test_explicit_err_must_exist(self):
        with self.assertRaisesRegex(g.ToolError, 'is not a file'):
            g.verify(self.syn.run, err_path=Path(self.tmp) / 'missing.err', out=Path(self.tmp) / 'v_err.json')


class LaneChangeWindow(unittest.TestCase):
    """Review fix 1/2 end to end (SyntheticRun lane_change=True): lane changes inside the crossing step at
    the two-lane 'at' station through:10485 and at the two-lane head pair 70203/70204, one in the last
    second (a tail), and vehicle 904 on the chain connector 10771 at the window end."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix='n31_gt_lc_')
        cls.syn = sr.SyntheticRun(cls.tmp, lane_change=True)
        cls.result = g.verify(cls.syn.run, out=Path(cls.tmp) / 'v.json')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def recorded(self, link, x, lane):
        """VISSIM's count of the trajectories at a lane-level point (the lane at the end of the step)."""
        return sum(1 for v in self.syn.vehicles if (t := sr.crossing_time(v, link, x)) is not None
                   and 750 < t <= 900 and sr.recorded_lane(v, t) == lane)

    def test_lane_changes_are_attributed_not_failed(self):
        self.assertEqual(self.result['verdict'], 'PASS')
        items = self.result['windows'][0]['items']
        rows = items['detectors']['rows']
        row = lambda ref, lane: next(r for r in rows if r['boundary_ref'] == ref and r['lane'] == lane)
        through1, through2 = row('through:10485', 1), row('through:10485', 2)
        self.assertEqual((through1['gt_lane_change'], through2['gt_lane_change']), ([901, 903], [901, 903]))
        self.assertEqual((through1['attributed_lane_change'], through2['attributed_lane_change']), ([], [901]))
        self.assertEqual((through2['excess'], through2['tail']), (1, 1))          # 903 is still a tail at 900
        group = items['detectors']['lane_change']['open_groups'][0]
        self.assertEqual((group['rows'], group['lane_choices'], group['lane_choices_fitting'], group['ok']),
                         (sorted([through1['dcp'], through2['dcp']]), 2, 1, True))
        head1, head2 = row('head:70203', 1), row('head:70204', 2)
        self.assertEqual((head1['gt_lane_change'], head1['attributed_lane_change']), ([902], []))
        self.assertEqual((head2['gt_lane_change'], head2['attributed_lane_change']), ([902], [902]))
        heads = items['heads']['by_head']
        self.assertEqual(heads['70203']['gt_crossings'], self.recorded(26, 100.0, 1))
        self.assertEqual(heads['70204']['gt_crossings'], self.recorded(26, 100.004, 2))
        self.assertTrue(heads['70203']['ok'] and heads['70204']['ok'])
        truth = self.syn.truth()
        self.assertEqual(items['boundaries']['by_ref']['through:10485']['gt'], truth['through'])
        self.assertEqual(items['off_split']['by_off']['10485']['gt_through'], truth['through'])
        self.assertEqual(items['boundaries']['by_ref']['head:70204']['gt'], self.recorded(26, 100.004, 2))
        # 905 enters x = 0 on lane 1 and passes p = 1 m on lane 2: the source lane terms (lane at p) differ from
        # the lanes at x, only their sum is exact (CONTRACT 3), so they are reported and the station is judged.
        source = items['boundaries']['by_ref']['source:FW_W']
        self.assertIs(source['ok'], True)
        self.assertTrue(source['lanes_report_only'])
        self.assertEqual(sorted(x['ok'] for x in source['lanes']), [False, False])
        self.assertEqual(source['gt'], truth['source'])

    def test_wrong_head_or_station_values_still_fail(self):
        path = oc.resolve(self.syn.states[900][oc.RAW_STATE_KEY], oc.derived_path(900))
        original = path.read_bytes()
        cases = {'heads': lambda d: d['head_window']['heads'][1].update(
                     qualified_crossings=d['head_window']['heads'][1]['qualified_crossings'] - 1),
                 'boundaries': lambda d: d['boundaries']['through:10485'].update(
                     cross=d['boundaries']['through:10485']['cross'] + 1)}
        try:
            for item, mutate in cases.items():
                derived = json.loads(original)
                mutate(derived)
                path.write_bytes(oc.canonical_json_bytes(derived) + b'\n')
                result = g.verify(self.syn.run, out=Path(self.tmp) / f'v_{item}.json')
                self.assertEqual(result['verdict'], 'FAIL', item)
                self.assertIs(result['windows'][0]['items'][item]['ok'], False, item)
        finally:
            path.write_bytes(original)

    def test_unrecorded_chain_connector_is_closed(self):
        """Review fix 2a: the runner records only the detector links, so 10771 is unrecorded; 904 is on it at 900."""
        tmp = Path(self.tmp) / 'runner'
        syn = sr.SyntheticRun(tmp, lane_change=True)
        for name in ('gt_veh.csv', 'gt_sig.csv', 'gt_meta.csv'):
            (syn.run / name).unlink()
        syn.write_runner_ground_truth(links={r.link for r in syn.rows})
        result = g.verify(syn.run, out=tmp / 'v.json')
        self.assertEqual(result['verdict'], 'PASS')
        item = result['windows'][0]['items']['freeway_exit_count']
        self.assertIs(item['ok'], True)
        self.assertEqual(item['unrecorded_connector']['by_outcome'].get('on_chain_at_window_end'), 1)
        last = next(x for x in item['unrecorded_connector']['examples'] if x['veh'] == 904)
        self.assertEqual((last['outcome'], last['link'], last['vanished_b10']), ('on_chain_at_window_end', 10771, 8999))
        # 26 runs on 1 m past the start of 10771: every vanish there is 'ambiguous' until it reappears on 120
        self.assertTrue(all(x['kind'] == 'ambiguous' for x in item['unrecorded_connector']['examples']))


class RunnerFormat(unittest.TestCase):
    """The runner's own A9 files (VBS Obs150GtStepTo): <decisions>/obs150_gt, 'veh' column, no speed."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix='n31_gt_runner_')
        cls.syn = sr.SyntheticRun(cls.tmp)
        cls.probe = g.verify(cls.syn.run, out=Path(cls.tmp) / 'v_probe.json')
        for name in ('gt_veh.csv', 'gt_sig.csv', 'gt_meta.csv'):      # only the runner's folder is left
            (cls.syn.run / name).unlink()
        cls.folder = cls.syn.write_runner_ground_truth()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_runner_files_give_the_same_verdict(self):
        result = g.verify(self.syn.run, out=Path(self.tmp) / 'v_runner.json')
        self.assertEqual(result['verdict'], 'PASS')
        self.assertEqual(Path(result['files']['gt_veh']), self.folder / 'gt_veh.csv')
        self.assertEqual(Path(result['files']['gt_meta']), self.folder / 'gt_meta.csv')
        mine, theirs = result['windows'][0]['items'], self.probe['windows'][0]['items']
        for item in ('detectors', 'boundaries', 'off_split', 'source', 'freeway_exit_count', 'link_403'):
            self.assertEqual(mine[item], theirs[item], item)
        self.assertEqual(mine['gt_anomalies']['count'], 0)
        head = mine['heads']['by_head']['70203']
        self.assertIs(head['ok'], True)
        self.assertEqual(head['gt']['next'], theirs['heads']['by_head']['70203']['gt']['next'])
        self.assertFalse(head['gt']['previous']['covered'])     # gt_sig stops at 10e-1: 'previous' is not judged

    def test_rule_the_runner_cannot_cover_is_incomplete_not_pass(self):
        """Review fix 2b: with --sig-rule previous no head is judged; that used to print PASS."""
        result = g.verify(self.syn.run, sig_rule='previous', out=Path(self.tmp) / 'v_prev.json')
        self.assertEqual(result['verdict'], 'INCOMPLETE')
        self.assertEqual((result['windows'][0]['failed'], result['windows'][0]['not_judged']), ([], ['heads']))
        self.assertEqual(g.main([str(self.syn.run), '--sig-rule', 'previous', '--out', str(Path(self.tmp) / 'v3.json')]),
                         3)
        self.assertEqual(g.main([str(self.syn.run), '--out', str(Path(self.tmp) / 'v4.json')]), 0)

    def test_reach_without_speed_is_the_vehicles_own_displacement(self):
        engine = g.Engine(net(), [], tracked=(1,))
        slow = lambda pos: g.Pos(1, 1, pos, None, None, None)
        self.assertAlmostEqual(engine._reach(slow(10.0), 7), g.MAX_SPEED_KMH / 36 + g.REACH_SLACK_M)
        engine.step(100, {7: slow(10.0)}, 101, {7: slow(11.5)})
        self.assertAlmostEqual(engine._reach(slow(11.5), 7), 1.5 + g.REACH_SLACK_M)
        self.assertAlmostEqual(engine._reach(P(1, 1, 11.5, speed=36.0), 7), 1.0 + g.REACH_SLACK_M)   # GT speed wins

    def test_folder_choice_never_mixes_files(self):
        other = Path(self.tmp) / 'explicit'
        other.mkdir(exist_ok=True)
        shutil.copyfile(self.folder / 'gt_veh.csv', other / 'gt_veh.csv')
        with self.assertRaisesRegex(g.ToolError, 'no gt_sig.csv'):
            g.gt_folder(other, self.syn.run, self.syn.decisions)
        self.assertEqual(g.gt_folder(None, self.syn.run, self.syn.decisions), self.folder)
        with self.assertRaisesRegex(g.ToolError, 'gt_veh.csv not found'):
            g.gt_folder(Path(self.tmp) / 'nowhere', self.syn.run, self.syn.decisions)

    def test_veh_and_no_columns_together_are_refused(self):
        bad = Path(self.tmp) / 'bad_gt_veh.csv'
        bad.write_text('t10,veh,no,link,lane,pos\n7500,1,1,26,1,0.5\n', encoding='latin-1')
        with self.assertRaisesRegex(g.ToolError, 'same quantity'):
            list(g.read_gt_frames(bad, 7500, 7500))


def com_log(events, owner='com'):
    start = {'9-1': {'owner': 'com', 'state': 'RED', 'verified': True} if owner == 'com' else {'owner': 'native'}}
    return {'scs': ['9'], 'start': start, 'events': [list(e) for e in events], 'complete': True}


def read_back(greens, s=750, e=900):
    """gt_sig of SG 9-1 as the runner samples it (t10 = 10s .. 10e-1): GREEN on [10a, 10b) for writes at a, b."""
    return {('9', '1'): {t10: 'GREEN' if any(10 * a <= t10 < 10 * b for a, b in greens) else 'RED'
                         for t10 in range(10 * s, 10 * e)}}


class ComHeadDelay(unittest.TestCase):
    """Integrator fix (WP-B1 note to WP-D, D10 = 1): a COM write at u reads back at once but the heads take
    it one update later, so the GT state of a COM-owned second is the read back 10 samples earlier, and the
    d10 item checks D10 itself on the lead vehicles."""

    KEY = ('9', '1')

    def greens(self, truth, rule='next'):
        return [b10 for b10 in range(7501, 9001) if truth.state(self.KEY, b10, rule) == 'GREEN']

    def test_com_second_reads_back_one_second_earlier(self):
        signals = read_back([(800, 820)])
        log = com_log([(800, '9', '1', 'write', 'GREEN'), (820, '9', '1', 'write', 'RED')])
        self.assertEqual(self.greens(g.SignalTruth(signals, log, (750, 900), 1)), list(range(8011, 8211)))  # (801, 821]
        self.assertEqual(self.greens(g.SignalTruth(signals, log, (750, 900), 0)), list(range(8001, 8201)))  # (800, 820]
        # before the first sample of the window, the logged start state stands in for the read back
        self.assertEqual(g.SignalTruth(signals, log, (750, 900), 1).state(self.KEY, 7501, 'next'), 'RED')
        # a native SG keeps the V0-4 rule whatever the delay
        native = g.SignalTruth(signals, com_log([], owner='native'), (750, 900), 1)
        self.assertEqual(self.greens(native), list(range(8001, 8201)))

    def test_own_moves_with_the_delay_and_the_switch_second_is_unknown(self):
        signals = read_back([(800, 900)])
        log = com_log([(800, '9', '1', 'own', True), (800, '9', '1', 'write', 'GREEN')], owner='native')
        truth = g.SignalTruth(signals, log, (750, 900), 1)
        self.assertEqual((truth.is_com(self.KEY, 800), truth.is_com(self.KEY, 801)), (False, True))
        # (800, 801]: the heads still show the native program, the read back already the COM write
        self.assertIsNone(truth.state(self.KEY, 8005, 'next'))
        self.assertEqual(truth.state(self.KEY, 8011, 'next'), 'GREEN')
        self.assertEqual(truth.state(self.KEY, 7995, 'next'), 'RED')

    def probe_item(self, move_t10, delay, *, gap=0.8, green_at=850):
        """One lead vehicle 7 standing gap m before head 70001 of SG 9-1 until move_t10."""
        signals = read_back([(green_at, 900)])
        log = com_log([(green_at, '9', '1', 'write', 'GREEN')])
        row = types.SimpleNamespace(role='meter_head', ref='70001|9-1', link=5, lane=1, pos=100.0)
        probe = g.D10Probe([row], g.SignalTruth(signals, log, (750, 900), delay))
        for t10 in range(7500, 9001):
            moved = move_t10 is not None and t10 >= move_t10
            pos = 100.0 - gap + (0.01 * (t10 - move_t10 + 1) if moved else 0.0)
            probe.feed(t10, {7: g.Pos(5, 1, pos, None, None, None), 8: g.Pos(5, 1, 60.0 + t10 / 100, None, None, None)})
        return probe.item(delay)

    def test_lead_departure_decides_d10(self):
        one = self.probe_item(8511, 1)                       # departs at 851.1 after GREEN written at 850
        self.assertEqual((one['ok'], one['green_writes'], one['lead_samples'], one['by_kind']),
                         (True, 1, 1, {'match': 1}))
        self.assertEqual(one['samples'][0]['departure_after_write_s'], 1.1)
        self.assertEqual(one['contradiction_samples'], [])
        zero = self.probe_item(8511, 0)
        self.assertIs(zero['ok'], False)                      # the same departure contradicts D10 = 0
        self.assertEqual([s['departure_after_write_s'] for s in zero['contradiction_samples']], [1.1])
        self.assertIs(self.probe_item(8501, 1)['ok'], False)  # departs at 850.1: the heads took the write at once
        self.assertIs(self.probe_item(8501, 0)['ok'], True)
        other = self.probe_item(8515, 1)                      # a late start decides nothing
        self.assertEqual((other['ok'], other['by_kind']), (None, {'other': 1}))
        self.assertEqual(self.probe_item(None, 1)['by_kind'], {'no_move': 1})
        far = self.probe_item(8511, 1, gap=5.0)               # not waiting at the head: no sample
        self.assertEqual((far['ok'], far['lead_samples']), (None, 0))

    def test_run_level_d10(self):
        window = lambda d10: {'items': {g.D10_ITEM: d10}}
        self.assertEqual(g.run_d10([window({'ok': None, 'com_head_sgs': []})])['ok'], 'not_applicable')
        self.assertIsNone(g.run_d10([window({'ok': None, 'com_head_sgs': ['9-1']})])['ok'])
        self.assertIs(g.run_d10([window({'ok': None, 'com_head_sgs': ['9-1']}),
                                 window({'ok': True, 'com_head_sgs': ['9-1']})])['ok'], True)
        self.assertIs(g.run_d10([window({'ok': True, 'com_head_sgs': ['9-1']}),
                                 window({'ok': False, 'com_head_sgs': ['9-1']})])['ok'], False)
        # a window without d10 evidence is not INCOMPLETE by itself
        self.assertEqual(g.window_verdict({g.D10_ITEM: {'ok': None}, 'x': {'ok': True}}), ('PASS', [], []))
        self.assertEqual(g.window_verdict({g.D10_ITEM: {'ok': False}, 'x': {'ok': True}}), ('FAIL', [g.D10_ITEM], []))


class ComHeadWindow(unittest.TestCase):
    """End to end: the synthetic head 70203 (SC5 SG2) COM-owned. The runner writes GREEN at 759 and 849 and
    RED at 799; with D10 = 1 the vehicles' green is (760, 800], (850, 900], the green the derived head window
    already holds. The read back is GREEN from the write on (gt_sig)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix='n31_gt_com_')
        cls.syn = syn = sr.SyntheticRun(cls.tmp)
        state = syn.states[900]
        state[oc.RAW_STATE_KEY]['signal_log'] = {
            'scs': ['5'], 'start': {'5-2': {'owner': 'com', 'state': 'RED', 'verified': True}},
            'events': [[759, '5', '2', 'write', 'GREEN'], [799, '5', '2', 'write', 'RED'],
                       [849, '5', '2', 'write', 'GREEN']], 'complete': True}
        oc.validate_signal_log(state[oc.RAW_STATE_KEY]['signal_log'], 750, 900)
        (syn.decisions / 'state_000900.json').write_text(json.dumps(state), encoding='utf-8')
        syn.write_derived()
        with open(syn.run / 'gt_sig.csv', 'w', encoding='latin-1', newline='') as f:
            f.write('t10,sc,sg,sig_state,t_sig_state\n')
            for t10 in range(7500, 9001):
                green = 7590 <= t10 < 7990 or t10 >= 8490
                f.write(f'{t10},5,2,{"GREEN" if green else "RED"},0\n')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_delay_one_matches_the_head_window(self):
        result = g.verify(self.syn.run, out=Path(self.tmp) / 'v1.json')
        window = result['windows'][0]
        head = window['items']['heads']['by_head']['70203']
        self.assertIs(head['ok'], True)
        self.assertEqual((head['gt']['next']['green_sec'], head['gt_com_sec']), (90.0, 150))
        self.assertEqual(window['verdict'], 'PASS')
        # the synthetic vehicles never stand at the head: D10 is not re-checked, so the run is not a PASS
        d10 = result['d10']
        self.assertEqual((d10['ok'], d10['green_writes'], d10['lead_samples']), (None, 2, 0))
        self.assertEqual(result['verdict'], 'INCOMPLETE')
        self.assertEqual(g.main([str(self.syn.run), '--out', str(Path(self.tmp) / 'v1m.json')]), 3)

    def test_delay_zero_puts_the_green_a_second_early(self):
        result = g.verify(self.syn.run, out=Path(self.tmp) / 'v0.json', com_head_delay=0)
        head = result['windows'][0]['items']['heads']['by_head']['70203']
        self.assertIs(head['ok'], False)
        self.assertEqual(head['gt']['next']['green_sec'], 91.0)      # (759, 799] + (849, 900]
        self.assertEqual(result['verdict'], 'FAIL')


@unittest.skipUnless(PR.is_dir() and PR_NETWORK.is_file(), 'probe run data not available')
class ProbeD10(unittest.TestCase):
    """D10Probe on the probe run: GREEN written on the meter SC9106 SG1 at 850, both lanes' lead vehicles
    move at 851.1 (the V0-4 evidence of test_clock_probe) -> D10 = 1 confirmed, D10 = 0 contradicted."""

    @classmethod
    def setUpClass(cls):
        signals = g.read_gt_signals(PR / 'gt_sig.csv')
        writes = []
        for line in (PR / 'results.jsonl').read_text(encoding='utf-8').splitlines():
            record = json.loads(line) if line.strip() else {}
            if record.get('check') == 'f_write':
                writes.append([int(record['t10']) // 10, str(record['sc']), str(record['sg']), 'write', record['state']])
        log = {'scs': ['9106'], 'start': {'9106-1': {'owner': 'com', 'state': signals['9106', '1'][7500],
                                                      'verified': True}},
               'events': [w for w in writes if 750 <= w[0] < 900], 'complete': True}
        rows = [types.SimpleNamespace(role='meter_head', ref=f"{r['head_no']}|9106-1", link=int(r['link']),
                                      lane=int(r['lane']), pos=float(r['pos']))
                for r in csv.DictReader(open(PR_CONFIG / 'heads.csv', encoding='latin-1'))
                if (r['sc'], r['sg']) == ('9106', '1')]
        cls.items = {}
        for delay in (1, 0):
            probe = g.D10Probe(rows, g.SignalTruth(signals, log, (750, 900), delay))
            for t10, frame in g.read_gt_frames(PR / 'gt_veh.csv', 7500, 9000):
                probe.feed(t10, frame)
            cls.items[delay] = probe.item(delay)

    def test_meter_lead_vehicles_confirm_one_second(self):
        one = self.items[1]
        self.assertIs(one['ok'], True)
        self.assertEqual(one['by_kind'], {'match': 2})
        self.assertEqual({s['u'] for s in one['samples']}, {850})
        self.assertEqual(one['departures_after_write_s'], {1.1: 2})
        self.assertIs(self.items[0]['ok'], False)


@unittest.skipUnless(PR.is_dir() and PR_NETWORK.is_file(), 'probe run data not available')
class ProbeTruth(unittest.TestCase):
    """The engine reproduces VISSIM's own Vehs(Current,6,All) at the 18 probe points (PRB f)."""

    @classmethod
    def setUpClass(cls):
        cls.net = g.Network(PR_NETWORK)
        cls.rows = list(csv.DictReader(open(PR_CONFIG / 'detectors.csv', encoding='latin-1')))
        cls.tracked = [int(r['link']) for r in csv.DictReader(open(PR_CONFIG / 'tracked_links.csv', encoding='latin-1'))]
        cls.removed, cls.route_end, _ = g.read_removals(PR / 'err' / 'obs150_probe_001.err')
        verdict = json.loads((PR / 'verdict.json').read_text(encoding='utf-8'))
        cls.vissim = {str(r['dcp']): r['dc_k6'] for r in verdict['f']['counts']}

    def run_points(self, points):
        engine = g.Engine(self.net, points, self.tracked, self.removed, self.route_end)
        events, previous = [], None
        for t10, frame in g.read_gt_frames(PR / 'gt_veh.csv', 7500, 9000):
            if previous is not None:
                events += [(e, previous[1]) for e in engine.step(previous[0], previous[1], t10, frame)]
            previous = (t10, frame)
        return events, engine.anomalies

    def test_counts_equal_vissim(self):
        points = [g.Point(r['dcp_no'], int(r['link']), float(r['pos_request']), frozenset((int(r['lane']),)))
                  for r in self.rows]
        events, anomalies = self.run_points(points)
        self.assertEqual(anomalies, [])
        by = defaultdict(list)
        for e, _ in events:
            by[e.pid].append(e)
        for r in self.rows:
            known = [e for e in by[r['dcp_no']] if e.lane is not None]
            changed = [e for e in by[r['dcp_no']] if e.lane is None]
            if not changed:
                self.assertEqual(len(known), self.vissim[r['dcp_no']], r['ref'])
        # link 26 at 40 m: one lane change inside a step; the station sum is exact
        station = set()
        for d in ('950016', '950017', '950018'):
            station |= {e.veh for e in by[d]}
        self.assertEqual(len(station), sum(self.vissim[d] for d in ('950016', '950017', '950018')))

    def test_lane_unknown_crossings_are_attributed_by_mer(self):
        """Review fix 1 on real data: every probe point's GT vehicles (lane-known + attributed) equal the
        vehicles VISSIM's own .mer holds there, vehicle by vehicle; 6703 (26 at 40 m, PRB f) sits at 950016."""
        points = [g.Point(f"dcp:{r['dcp_no']}", int(r['link']), float(r['pos_request']), frozenset((int(r['lane']),)))
                  for r in self.rows]
        events, anomalies = self.run_points(points)
        self.assertEqual(anomalies, [])
        by_pid = defaultdict(list)
        for e, _ in events:
            by_pid[e.pid].append(e)
        mer = defaultdict(dict)
        for line in (PR / 'vissim_eval' / 'obs150_probe_001.mer').read_text(encoding='latin-1').splitlines():
            parts = [p.strip() for p in line.split(';')]
            if len(parts) > 4 and parts[0].isdigit() and float(parts[1]) >= 0 and 750 < float(parts[1]) <= 900:
                mer[int(parts[0])][int(parts[3])] = LaneAttribution.M(int(parts[3]), float(parts[1]))
        rows = [LaneAttribution.R(int(r['dcp_no']), int(r['link']), int(r['lane'])) for r in self.rows]
        res = g.resolve_unknown_lanes(rows, by_pid, mer, (750, 900))
        self.assertEqual((res.failures, res.open, res.uncounted), ([], [], []))
        self.assertIn(6703, res.attributed[950016])
        for r in rows:
            clean = {e.veh for e in by_pid[f'dcp:{r.dcp_no}'] if e.lane is not None}
            self.assertEqual(clean | set(res.attributed.get(r.dcp_no, ())), set(mer[r.dcp_no]), r)

    def test_10643_exit_lane_by_destination(self):
        events, anomalies = self.run_points([g.Point('x', 10643, 318.998328, frozenset((1, 2)))])
        self.assertEqual(anomalies, [])
        table = defaultdict(Counter)
        for e, fa in events:
            table[str(e.lane)][self.net.destination_10643(fa[e.veh].route)] += 1
        # PR check_stdout (V0-5 truth)
        self.assertEqual({k: dict(v) for k, v in table.items()}, {'1': {10634: 2, 10642: 7}, '2': {10634: 7, 10635: 9}})


if __name__ == '__main__':
    unittest.main()
