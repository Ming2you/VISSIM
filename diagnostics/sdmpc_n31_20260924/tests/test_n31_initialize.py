"""T5/T6 (plan C11).

Offline now:
  - bin_frame (LPR initialize binning) on the real C1 geometry: sum over the
    31 cells == chain vehicles past Pos=0 == sum over the 21 parents; a v2
    Pos<0 row (fail-safe only: the runner clamps [-8,0) to 0 and the v2 frame
    validator refuses Pos<0) is in no cell (EO:333-335) and outside the obs150
    source station, so A1's backlog carries it once (v1 keeps its byte-identical wrap);
  - the T6 guards: each silent fallback raises while active and is restored.
With a G1 state (set N31_G1_STATE to a state_000900.json of the G1 run):
  - T5 on the real lane frame (31 = frame = 21 rows).
The full T5/T6 replay (initialize + prepare_joint_leader_candidates under the
guards) runs in V3 with D1/D2 on G1 states: t6_guarded_decision.py runs the
replay's adapter arguments with the guards entered after configure_runtime
(its mechanics: test_n31_t6_runner.py).
"""
from __future__ import annotations

import json
import os
import types
import unittest
from pathlib import Path

import n31_fixtures as fx
from n31_guards import IndexGuardError, strict_index_guards
from evaluation.controllers import lane_plant_runtime as lpr
from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.freeway_refined_geometry import collapse_to_parents, parents


def chain_vehicles(geometry, vehicles, road):
    return [v for v in vehicles if (geometry['addresses'].get(str(v[1])) or [None])[0] == road]


def before_start(geometry, vehicles, road):
    return [v for v in chain_vehicles(geometry, vehicles, road) if float(geometry['addresses'][str(v[1])][1]) + v[3] < 0]


def synthetic_frame(geometry):
    rows, veh = [], 1
    for link, (road, offset) in geometry['addresses'].items():
        for k in range(12):
            rows.append([veh, int(link), 1 + k % 2, 3.7 * k + 0.5, 60.0 + k, 4.5] + [None] * 9)
            veh += 1
    rows.append([veh, 26, 1, -0.09, 12.0, 4.5] + [None] * 9)     # recorded before Pos=0
    return rows


class BinningTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.refined = fx.load_json(fx.GEOMETRY)
        cls.parent = collapse_to_parents(cls.refined)
        cls.table = parents(cls.refined)

    def check_frame(self, vehicles):
        for road in ('FW_E', 'FW_W'):
            cells31, bins31, dropped31 = lpr.bin_frame(self.refined, vehicles, road, drop_before_start=True)
            cells21, bins21, dropped21 = lpr.bin_frame(self.parent, vehicles, road, drop_before_start=True)
            self.assertEqual((len(cells31), len(cells21)), (31, 21))
            early = before_start(self.refined, vehicles, road)
            self.assertEqual(dropped31, early)
            self.assertEqual(dropped21, early)
            total = len(chain_vehicles(self.refined, vehicles, road)) - len(early)
            self.assertEqual(sum(map(len, bins31)), total)
            self.assertEqual(sum(map(len, bins21)), total)
            for p in range(21):
                children = [b for b, q in zip(bins31, self.table[road]) if q == p]
                self.assertEqual(sorted(r[0] for b in children for r in b), sorted(r[0] for r in bins21[p]))

    def test_synthetic_frame(self):
        vehicles = synthetic_frame(self.refined)
        self.assertEqual(len(before_start(self.refined, vehicles, 'FW_W')), 1)
        self.check_frame(vehicles)

    def test_before_start_is_dropped(self):
        rows = [[1, 26, 1, -0.09, 12.0, 4.5] + [None] * 9, [2, 26, 1, 0.0, 12.0, 4.5] + [None] * 9]
        _, v2, dropped = lpr.bin_frame(self.refined, rows, 'FW_W', drop_before_start=True)
        _, v1, kept = lpr.bin_frame(self.refined, rows, 'FW_W')
        self.assertEqual([r[0] for r in dropped], [1])                  # in no cell (EO:333-335)
        self.assertEqual([[r[0] for r in b] for b in v2], [[2]] + [[]] * 30)
        self.assertEqual(kept, [])
        self.assertEqual([[r[0] for r in b] for b in v1], [[2]] + [[]] * 29 + [[1]])   # the v1 wrap, byte-identical

    @unittest.skipUnless(fx.DETECTORS.is_file(), 'obs150 detector CSV not reachable')
    def test_before_start_is_outside_the_source_station(self):
        """The dropped row is left to backlog = schedule - admitted_cum: N_src(T) must not count it."""
        rows, _ = oc.read_detector_csv(fx.DETECTORS)
        for road in ('FW_E', 'FW_W'):
            link = next(int(k) for k, (r, offset) in self.refined['addresses'].items() if r == road and float(offset) == 0.0)
            source = [r for r in rows if r.boundary_ref == 'source:' + road]
            self.assertTrue(source)
            for r in source:
                self.assertFalse(oc.segment_contains(r.segment, r.orientation, link, r.lane, -0.09), road)
                self.assertTrue(oc.segment_contains(r.segment, r.orientation, link, r.lane, 0.0), road)

    @unittest.skipUnless(os.environ.get('N31_G1_STATE'), 'T5 on real data needs N31_G1_STATE (G1 run, V3)')
    def test_g1_frame(self):
        state = json.loads(Path(os.environ['N31_G1_STATE']).read_text(encoding='utf-8-sig'))
        meta = state['lane_plant_observation']
        frame_path = Path(meta['directory']) / ('frame_%06d.json' % state['sim_sec'])
        raw = frame_path.read_bytes()
        text = raw.decode('utf-16') if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else raw.decode('utf-8-sig')
        self.check_frame(json.loads(text)['vehicles'])


class GuardTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        fx.component()   # installs the reference-config hooks the guards wrap (segment_vsl zones, lane profile)

    def cfg(self, **network):
        return types.SimpleNamespace(network=types.SimpleNamespace(**network))

    def test_segment_vsl_out_of_zone_table(self):
        from src.models import state as st
        cfg = self.cfg(freeway_vsl_zone_head_of_cell={'FW_E': [0] * 5 + [5] * 5 + [10] * 11})
        cfg.freeway_follower = types.SimpleNamespace(vsl_set=[60.0, 80.0, 110.0])
        control = types.SimpleNamespace(vsl={'FW_E': 90.0, 'FW_E__seg10': 70.0})
        original = st.segment_vsl
        with strict_index_guards():
            self.assertEqual(st.segment_vsl(control, 'FW_E', 20, cfg), 70.0)
            with self.assertRaises(IndexGuardError):
                st.segment_vsl(control, 'FW_E', 23, cfg)
        self.assertIs(st.segment_vsl, original)
        self.assertEqual(st.segment_vsl(control, 'FW_E', 23, cfg), 90.0)   # the silent fallback

    def test_merge_index_clamps(self):
        from src.models import metanet as mn
        from src.controllers.leader import Leader
        from src.controllers.freeway_follower import FreewayFollower
        cfg = self.cfg(ramp_merge_segment_index={'RM_C10484': 23})
        holder = types.SimpleNamespace(cfg=cfg)
        with strict_index_guards():
            self.assertEqual(mn._ramp_merge_index(cfg, 'RM_C10484', 31), 23)
            with self.assertRaises(IndexGuardError):
                mn._ramp_merge_index(cfg, 'RM_C10484', 21)
            for cls in (Leader, FreewayFollower):
                self.assertEqual(cls._ramp_merge_index(holder, 'RM_C10484', 31), 23)
                with self.assertRaises(IndexGuardError):
                    cls._ramp_merge_index(holder, 'RM_C10484', 21)
        self.assertEqual(mn._ramp_merge_index(cfg, 'RM_C10484', 21), 20)
        self.assertEqual(Leader._ramp_merge_index(holder, 'RM_C10484', 21), 20)

    def test_merge_index_read_in_another_zone_namespace(self):
        """A 31-cell merge index read through a 21-cell zone table stays in range but names another zone.

        RM_C10681: refined cell 12 is parent cell 9 (head 5); the parent table reads cell 12 as head 10.
        """
        from src.models import state as st
        from src.models import metanet as mn
        from src.controllers.leader import Leader
        parent = {'FW_E': [0] * 5 + [5] * 5 + [10] * 5 + [15] * 6}
        refined = {'FW_E': [0] * 5 + [5] * 9 + [10] * 11 + [15] * 6}
        full = self.cfg(ramp_merge_segment_index={'RM_C10681': 12}, freeway_vsl_zone_head_of_cell=parent)
        road = self.cfg(ramp_merge_segment_index={'RM_C10681': 12}, freeway_vsl_zone_head_of_cell=refined)
        for cfg in (full, road):
            cfg.freeway_follower = types.SimpleNamespace(vsl_set=[60.0, 80.0, 110.0])
        control = types.SimpleNamespace(vsl={'FW_E': 110.0, 'FW_E__seg5': 80.0, 'FW_E__seg10': 60.0})
        record = {}
        with strict_index_guards(record):
            index = mn._ramp_merge_index(road, 'RM_C10681', 31)
            self.assertEqual(st.segment_vsl(control, 'FW_E', index, road), 80.0)    # same namespace
            self.assertEqual(st.segment_vsl(control, 'FW_E', 12, full), 60.0)       # a plain parent-cell read
            for index in (mn._ramp_merge_index(full, 'RM_C10681', 31),
                          Leader._ramp_merge_index(types.SimpleNamespace(cfg=full), 'RM_C10681', 31)):
                self.assertEqual((index, list(range(31))[index]), (12, 12))           # indexes the state as before
                with self.assertRaisesRegex(IndexGuardError, '31-cell state .* 21-cell zone table'):
                    st.segment_vsl(control, 'FW_E', index, full)
        self.assertEqual(len(record['guard_errors']), 2)
        # unguarded, the same read silently takes zone 10 (60) instead of zone 5 (80)
        self.assertEqual(st.segment_vsl(control, 'FW_E', mn._ramp_merge_index(full, 'RM_C10681', 31), full), 60.0)

    def test_lane_profile_length(self):
        from src.models import metanet as mn
        cfg = self.cfg(freeway_segment_lanes={'FW_E': [4.0] * 21})
        state = types.SimpleNamespace(freeway_density={'FW_E': [10.0] * 31})
        with strict_index_guards():
            with self.assertRaises(IndexGuardError):
                mn.effective_lane_profile(state, cfg)

    def test_domain_spy_restores(self):
        from evaluation.controllers import joint_owner_neighbors as jon
        original = jon.build_current_freeway_domain
        record = {}
        with strict_index_guards(record):
            self.assertIsNot(jon.build_current_freeway_domain, original)
            with self.assertRaises(Exception):
                jon.build_current_freeway_domain(None, 'FW_E', None, None, None, None)
        self.assertEqual(record['build_current_freeway_domain_calls'], 1)
        self.assertIs(jon.build_current_freeway_domain, original)


if __name__ == '__main__':
    unittest.main()
