"""Eight bounded semantic checks of the saved-snapshot diagnostic, no runtime.

Compile only its nested locator and head-partition expression from the actual
source AST. This avoids importing/running main or duplicating its algorithms.
Two already saved small snapshots are read once; no model, network XML, or FZP.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/20260911_decision_runtime'
SOURCE = REPORT / 'audit_meter_branch_snapshots.py'
TREE = ast.parse(SOURCE.read_text(encoding='utf-8'))
LOCATOR = next(n for n in ast.walk(TREE) if isinstance(n, ast.FunctionDef) and n.name == 'locate')
BEFORE = next(n.value for n in ast.walk(TREE) if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == 'before' for t in n.targets))


def locator(routes, meters=(500,), endpoints=None):
    env = {'routes': routes, 'meters': set(meters), 'endpoints': endpoints or {}}
    exec(compile(ast.Module(body=[copy.deepcopy(LOCATOR)], type_ignores=[]), str(SOURCE), 'exec'), env)
    return env['locate']


def route(path, start=0.0, end=1000.0, continuous=True):
    return {'path': path, 'start_pos_m': start, 'end_pos_m': end,
            'all_links_exist': True, 'continuous': continuous}


def selected(decision=1, number=2, kind='STATIC'):
    return {'route_decision_no': decision, 'route_no': number, 'route_decision_type': kind}


def position(link=100, pos=50.0):
    return {'link_no': link, 'position_m': pos}


class MeterBranchSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = json.loads((REPORT / 'METER_BRANCH_OBSERVATIONS.json').read_text(encoding='utf-8'))
        cls.raw = {}
        for sec in cls.evidence['snapshots']:
            candidates = [p for p in cls.evidence['source_sha256'] if p.endswith(f'state_{int(sec):06d}.json')]
            assert len(candidates) == 1
            path = ROOT / candidates[0]
            data = path.read_bytes()
            assert hashlib.sha256(data).hexdigest() == cls.evidence['source_sha256'][candidates[0]]
            cls.raw[sec] = json.loads(data.decode('utf-8-sig'))
        cls.vehicles = {sec: {int(x['veh_no']): x for x in raw['vehicle_records']['records']}
                        for sec, raw in cls.raw.items()}
        cls.assignments = {sec: {int(x['veh_no']): x for x in raw['vehicle_routes']['records']}
                           for sec, raw in cls.raw.items()}

    def test_current_selected_route_confirms_only_explicit_future_meter(self):
        query = locator({(1, 2): route([100, 500, 200])})
        self.assertEqual(query(position(), selected()), (500, 'explicit_unique_future_meter'))
        # A same-number route at another decision must not join by route number alone.
        self.assertEqual(query(position(), selected(decision=9))[1], 'route_id_not_in_pinned_static_network')

    def test_missing_or_unselected_continuation_remains_unknown(self):
        query = locator({(1, 2): route([100, 200])})
        self.assertEqual(query(position(), selected())[1], 'no_explicit_future_meter_in_current_route')
        for kind in (None, 'DYNAMIC'):
            with self.subTest(kind=kind):
                self.assertEqual(query(position(), selected(kind=kind))[1], 'missing_or_nonstatic_route')

    def test_ambiguous_or_absent_current_link_does_not_assign(self):
        for path in ([100, 400, 100, 500, 200], [400, 500, 200]):
            with self.subTest(path=path):
                query = locator({(1, 2): route(path)})
                self.assertEqual(query(position(), selected())[1], 'current_link_absent_or_repeated_in_route')

    def test_physical_route_and_position_interval_are_required(self):
        endpoints = {500: {'from_link': 100, 'from_pos_m': 100.0, 'to_link': 200, 'to_pos_m': 10.0}}
        query = locator({(1, 2): route([100, 500, 200], start=20.0, end=80.0)}, endpoints=endpoints)
        for link, pos in ((100, 19.0), (100, 101.0), (200, 9.0), (200, 81.0)):
            with self.subTest(link=link, pos=pos):
                self.assertEqual(query(position(link, pos), selected())[1], 'position_outside_current_route_interval')
        invalid = locator({(1, 2): route([100, 500, 200], continuous=False)})
        self.assertEqual(invalid(position(), selected())[1], 'static_path_geometry_not_continuous')

    def test_already_passed_and_multiple_future_meters_are_not_upstream_assignment(self):
        query = locator({(1, 2): route([100, 500, 200])})
        self.assertEqual(query(position(200), selected())[1], 'no_explicit_future_meter_in_current_route')
        query = locator({(1, 2): route([100, 500, 200, 600, 300])}, meters=(500, 600))
        self.assertEqual(query(position(), selected())[1], 'multiple_future_meters_in_current_route')

    def test_each_lane_head_partitions_inventory_at_its_own_position(self):
        rows = [{'veh_no': 1, 'lane_no': 1, 'position_m': 100.0},
                {'veh_no': 2, 'lane_no': 1, 'position_m': 100.01},
                {'veh_no': 3, 'lane_no': 2, 'position_m': 100.01},
                {'veh_no': 4, 'lane_no': 2, 'position_m': 100.21}]
        expression = ast.Expression(body=copy.deepcopy(BEFORE))
        before = eval(compile(expression, str(SOURCE), 'eval'), {'physical': rows, 'heads': {1: 100.0, 2: 100.2}})
        self.assertEqual([r['veh_no'] for r in before], [1, 3])
        after = [r for r in rows if r not in before]
        self.assertEqual([r['veh_no'] for r in after], [2, 4])
        self.assertEqual(len(before)+len(after), len(rows))

    def test_actual_unknown_overlap_and_city_turn_are_kept_separate(self):
        for sec, stopped_count in (('900', 7), ('1050', 2)):
            branches = self.evidence['snapshots'][sec]['branches']
            ids = []
            for ramp in ('10646', '10681'):
                ids.append(set(v for row in branches[ramp]['scoped_unknown_by_reason'].values() for v in row['vehicle_ids']))
                self.assertEqual(branches[ramp]['scoped_unknown_stopped'], stopped_count)
                for vid in ids[-1]:
                    assignment = self.assignments[sec][vid]
                    self.assertFalse(assignment['route_decision_no'] == 1124 and assignment['route_no'] == 2)
            # Both inspection regions contain the same unresolved 66 cohort.
            self.assertGreater(len(ids[0] & ids[1]), 0)
            self.assertLess(len(ids[0] | ids[1]), len(ids[0])+len(ids[1]))
            stopped = {v for v in ids[0] | ids[1] if self.vehicles[sec][v]['speed_kph'] <= 1.0}
            self.assertEqual(len(stopped), stopped_count)
            for vid in stopped:
                self.assertEqual((self.vehicles[sec][vid]['link_no'], self.assignments[sec][vid]['route_decision_no'],
                                  self.assignments[sec][vid]['route_no']), (66, 1124, 1))
            for ramp in ('10646', '10681'):
                self.assertEqual(branches[ramp]['scoped_current_route_leaves_scope_stopped'], 1)

    def test_actual_snapshot_join_inventory_partition_and_known_route_binding(self):
        source_key = str(SOURCE.relative_to(ROOT))
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), self.evidence['source_sha256'][source_key])
        routes = {(r['decision_no'], r['route_no']): r for r in self.evidence['static_routes_with_meter'].values()}
        endpoints = {int(r): o['physical_endpoints'] for r, o in self.evidence['ownership'].items()}
        query = locator(routes, meters=endpoints, endpoints=endpoints)
        for sec, snap in self.evidence['snapshots'].items():
            self.assertEqual(set(self.vehicles[sec]), set(self.assignments[sec]))
            unique_known, unique_physical = set(), set()
            for ramp, row in snap['branches'].items():
                with self.subTest(sec=sec, ramp=ramp):
                    rows = [r for r in self.vehicles[sec].values() if int(r['link_no']) == int(ramp)]
                    heads = self.evidence['ownership'][ramp]['head_pos_m_by_lane']
                    pre = [r for r in rows if r['position_m'] <= heads[str(r['lane_no'])]]
                    self.assertEqual(row['physical_inventory'], len(rows))
                    self.assertEqual(row['inventory_before_head'], len(pre))
                    self.assertEqual(row['inventory_after_head'], len(rows)-len(pre))
                    self.assertEqual(row['stopped_before_head'], sum(r['speed_kph'] <= 1.0 for r in pre))
                    self.assertEqual(row['physical_stopped'], sum(r['speed_kph'] <= 1.0 for r in rows))
                    physical_ids = set(row['physical_vehicle_ids'])
                    self.assertFalse(physical_ids & unique_physical)
                    unique_physical |= physical_ids
                    known = row['known_upstream_vehicles']
                    self.assertEqual(row['known_upstream_inventory'], len(known))
                    for r in known:
                        vid = int(r['veh_no'])
                        self.assertNotIn(vid, unique_known)
                        unique_known.add(vid)
                        self.assertEqual(query(self.vehicles[sec][vid], self.assignments[sec][vid])[0], int(ramp))
                    self.assertFalse(set(r['veh_no'] for r in known) & physical_ids)
            self.assertFalse(unique_physical & unique_known)


if __name__ == '__main__':
    unittest.main(verbosity=2)
