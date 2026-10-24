"""WP-0: the counting identity (plan 1.3). Signs fixed on synthetic trajectories (V0-6b style).

A 0.1 s kinematic toy moves vehicles along an upstream link 4 (20 m) into
link 5 (100 m) and off its end. Ground truth counts the actual crossings of
the boundary x; the contract's evaluate_boundary sees only what a decision
sees: the station count Vehs(p), two frames and the .err removals.
"""
from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_fixtures as fx  # noqa: E402
from contract_fixtures import c  # noqa: E402

UP_LEN, LINK_LEN, DT = 20.0, 100.0, 0.1
UP_CM, LINK_CM = 2000, 10000   # the toy integrates in integer centimetres: no float drift at a boundary


def locate(q_cm):
    return (4, (q_cm + UP_CM) / 100) if q_cm < 0 else (5, q_cm / 100)


def simulate(seed, *, t_end=300.0, frames_at=(150.0, 300.0), remove_zone=None, lanes=(1,)):
    """Return frames {t: frame}, station crossings, removals and ground truth by (point, lane)."""
    rng = random.Random(seed)
    vehicles = {}
    next_id, t = 1, 0.0
    crossings = []   # (time, point_name, lane, veh)
    removals = []
    exits = []       # (time, lane)
    frames = {}
    points = {'xm2': -200, 'x0': 0, 'p5': 500, 'p95': 9500}
    steps = int(round(t_end / DT))
    for step in range(1, steps + 1):
        t = round(step * DT, 1)
        if rng.random() < 0.08:
            vehicles[next_id] = {'q': -UP_CM, 'lane': rng.choice(lanes), 'stop_until': 0.0}
            next_id += 1
        for veh, v in list(vehicles.items()):
            if t < v['stop_until']:
                speed = 0.0
            else:
                speed = rng.choice((0, 30, 75, 120, 150))   # cm per 0.1 s step
                if rng.random() < 0.01:
                    v['stop_until'] = t + rng.uniform(1.0, 40.0)
            old, new = v['q'], v['q'] + speed
            v['q'] = new
            for name, z in points.items():
                if old < z <= new:
                    crossings.append((t, name, v['lane'], veh))
            if new > LINK_CM:
                exits.append((t, v['lane']))
                del vehicles[veh]
                continue
            if remove_zone and remove_zone[0] <= new / 100 <= remove_zone[1] and rng.random() < 0.004:
                link, pos = locate(new)
                removals.append({'kind': 'lane_change_removal', 'time_sec': t, 'vehicle_id': veh,
                                 'link': link, 'position_m': pos, 'lane': v['lane']})
                del vehicles[veh]
        if t in frames_at:
            rows = []
            for veh, v in sorted(vehicles.items()):
                link, pos = locate(v['q'])
                rows.append((veh, link, v['lane'], pos))
            frames[t] = fx.frame(int(t), rows)
    return frames, crossings, removals, exits


def count(crossings, name, start, end, lane=None):
    return sum(1 for t, n, l, _ in crossings if n == name and start < t <= end and (lane is None or l == lane))


def row(role, ref, link, lane, pos, orientation, segment, key=960001, mode='exact', geometry=None):
    geometry = geometry or {'link_length_m': LINK_LEN, 'lane_count': 2}
    return c.DetectorRow(key, key, role, ref, link, lane, pos, mode, orientation,
                         c.expected_boundary_ref(role, ref), segment, geometry)


class IdentitySigns(unittest.TestCase):
    def test_formula(self):
        self.assertEqual(c.identity_cross('at', 7, 0, 0, 0), 7)
        self.assertEqual(c.identity_cross('down', 10, 3, 1, 2), 14)
        self.assertEqual(c.identity_cross('up', 10, 3, 1, 2), 6)
        with self.assertRaises(c.ObsContractError):
            c.identity_cross('at', 7, 1, 0, 0)
        with self.assertRaises(c.ObsContractError):
            c.identity_cross('sideways', 7, 0, 0, 0)

    def test_closure(self):
        seg = (c.SegmentPiece(5, 0.0, 5.0),)
        self.assertTrue(c.segment_contains(seg, 'down', 5, 1, 0.0))
        self.assertFalse(c.segment_contains(seg, 'down', 5, 1, 5.0))
        self.assertTrue(c.segment_contains(seg, 'up', 5, 1, 5.0))
        two = (c.SegmentPiece(4, 18.0, 20.0), c.SegmentPiece(5, 0.0, 5.0))
        self.assertTrue(c.segment_contains(two, 'down', 4, 1, 20.0))
        self.assertFalse(c.segment_contains(two, 'down', 5, 1, 5.0))
        lane = (c.SegmentPiece(5, 0.0, 5.0, (2,)),)
        self.assertFalse(c.segment_contains(lane, 'down', 5, 1, 2.0))
        self.assertTrue(c.segment_contains(lane, 'down', 5, 1, 2.0, use_lane=False))


class DownstreamOffset(unittest.TestCase):
    """in_x = Vehs(p) + N_[x,p)(T) - N_[x,p)(T-150) + R_[x,p)  (x = link 5 start, p = 5 m)."""

    def test_matches_ground_truth(self):
        for seed in range(12):
            frames, crossings, removals, _ = simulate(seed, remove_zone=(-5.0, 7.0))
            station = row('source', 'FW_E', 5, 1, 5.0, 'down', (c.SegmentPiece(5, 0.0, 5.0, (1,)),))
            detectors = {'960001': count(crossings, 'p5', 150, 300)}
            terms = c.evaluate_boundary([station], detectors, frames[300.0], frames[150.0], removals, 150, 300)
            self.assertEqual(terms.cross, count(crossings, 'x0', 150, 300), f'seed {seed}')
            removed_in = [r for r in removals if 150 < r['time_sec'] <= 300 and r['link'] == 5
                          and 0.0 <= r['position_m'] < 5.0]
            self.assertEqual(terms.removed, len(removed_in))
            self.assertEqual(terms.lane_exact, not removed_in)

    def test_two_piece_segment_across_a_link_end(self):
        # x = 2 m before the end of link 4 (q = -2), p = 5 m on link 5: the segment spans the join,
        # and removals on either piece are inside it.
        for seed in range(8):
            frames, crossings, removals, _ = simulate(seed, remove_zone=(-5.0, 7.0))
            station = row('source', 'FW_E', 5, 1, 5.0, 'down',
                          (c.SegmentPiece(4, 18.0, 20.0), c.SegmentPiece(5, 0.0, 5.0)))
            detectors = {'960001': count(crossings, 'p5', 150, 300)}
            terms = c.evaluate_boundary([station], detectors, frames[300.0], frames[150.0], removals, 150, 300)
            self.assertEqual(terms.cross, count(crossings, 'xm2', 150, 300), f'seed {seed}')


class UpstreamOffset(unittest.TestCase):
    """out_x = Vehs(p) + N_[p,x](T-150) - N_[p,x](T) - R_[p,x]  (x = end of link 5, p = 95 m)."""

    def test_matches_ground_truth(self):
        for seed in range(12):
            frames, crossings, removals, exits = simulate(seed, remove_zone=(90.0, 100.0))
            station = row('chain_end', 'FW_E', 5, 1, 95.0, 'up', (c.SegmentPiece(5, 95.0, 100.0, (1,)),),
                          mode='end_minus', geometry={'link_length_m': 100.0, 'lane_count': 2,
                                                      'offset_from_end_m': 5.0})
            detectors = {'960001': count(crossings, 'p95', 150, 300)}
            terms = c.evaluate_boundary([station], detectors, frames[300.0], frames[150.0], removals, 150, 300)
            self.assertEqual(terms.cross, sum(1 for t, _ in exits if 150 < t <= 300), f'seed {seed}')


class PerLaneStations(unittest.TestCase):
    def test_lanes_sum_to_the_station_and_removals_are_station_level(self):
        for seed in range(8):
            frames, crossings, removals, _ = simulate(seed, lanes=(1, 2), remove_zone=(-5.0, 7.0))
            rows = [row('off_entry', '10643', 5, lane, 5.0, 'down', (c.SegmentPiece(5, 0.0, 5.0, (lane,)),),
                        key=960001 + lane) for lane in (1, 2)]
            detectors = {str(960001 + lane): count(crossings, 'p5', 150, 300, lane) for lane in (1, 2)}
            terms = c.evaluate_boundary(rows, detectors, frames[300.0], frames[150.0], removals, 150, 300)
            self.assertEqual(terms.cross, count(crossings, 'x0', 150, 300))
            self.assertEqual(sum(t.n_end for t in terms.lanes), terms.n_end)
            removed_in = [r for r in removals if 150 < r['time_sec'] <= 300 and r['link'] == 5
                          and 0.0 <= r['position_m'] < 5.0]
            if not removed_in:
                for lane_terms in terms.lanes:
                    self.assertEqual(lane_terms.cross, count(crossings, 'x0', 150, 300, lane_terms.lane))
            self.assertEqual(sum(t.cross for t in terms.lanes) + terms.removed, terms.cross)

    def test_exact_station_and_negative_guard(self):
        head = row('head', '90030883|1004-2', 71, 1, 78.980074, 'at', ())
        terms = c.evaluate_boundary([head], {'960001': 12}, fx.frame(900), fx.frame(750), [], 750, 900)
        self.assertEqual((terms.cross, terms.n_end, terms.removed), (12, 0, 0))
        station = row('source', 'FW_E', 5, 1, 5.0, 'down', (c.SegmentPiece(5, 0.0, 5.0, (1,)),))
        with self.assertRaises(c.ObsContractError):
            c.evaluate_boundary([station], {'960001': 0}, fx.frame(900), fx.frame(750, [(1, 5, 1, 2.0)]), [], 750, 900)

    def test_removal_window_is_left_open(self):
        station = row('source', 'FW_E', 5, 1, 5.0, 'down', (c.SegmentPiece(5, 0.0, 5.0, (1,)),))
        at_start = {'kind': 'lane_change_removal', 'time_sec': 750.0, 'vehicle_id': 1, 'link': 5, 'position_m': 1.0}
        at_end = dict(at_start, time_sec=900.0, vehicle_id=2)
        terms = c.evaluate_boundary([station], {'960001': 0}, fx.frame(900), fx.frame(750), [at_start, at_end],
                                    750, 900)
        self.assertEqual(terms.removed_vehicles, (2,))

    def test_evaluate_boundaries_groups_the_table(self):
        rows = fx.detector_rows()
        obs = fx.raw_obs(900, rows)
        result = c.evaluate_boundaries(obs, rows, fx.frame(900), fx.frame(750), [])
        self.assertEqual(set(result), set(c.group_boundaries(rows)))
        self.assertEqual(result['source:FW_E'].cross, 4 * 3)
        self.assertEqual(result['source:FW_E'].as_dict()['lanes'][0]['lane'], 1)


if __name__ == '__main__':
    unittest.main()
