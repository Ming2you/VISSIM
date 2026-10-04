"""K8-6 SA (stopline_approach) module tests on toy states (spec 8 + amendment 1 r2 section 8).

Only synthetic cfg/state objects, real DelayedPort / LaneOfframpRuntime /
ModelAreaLedger and, for the AD rows, a separate process with the tangent
Finder (stopline_tangent_probe.py). No adapter run, capture, rollout, harness
job or VISSIM. Rows that need a captured template (T2 LOR/DP, T6b, T8b, T9b,
T9c projection equivalence, T10b-b, T11, T15b, T20b) are gate-stage work.
"""
from __future__ import annotations

import copy
import json
import math
import os
import pickle
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for extra in (ROOT, ROOT / 'vendor/NumSim-mine', HERE):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import stopline_toy as T  # noqa: E402
from src.models import urban_queue_model as uqm  # noqa: E402
from evaluation.controllers import stopline_approach as SA  # noqa: E402
from evaluation.controllers import urban_flow_accounting as ufa  # noqa: E402
from evaluation.controllers.control_area_objective import MembershipError  # noqa: E402

E, S, N, IN = T.E, T.S, T.N, T.IN
PROBE = HERE / 'stopline_tangent_probe.py'
NUMBA_DEPS = Path(os.environ.get('K8G_DEPS', r'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps'))


def lane_members(st, lane):
    return [(p[2], p[3]) for p in st.stopline_approach_state['lanes'][lane]]


# ------------------------------------------------------------------ T1 schema

class SchemaTests(unittest.TestCase):
    def test_valid_view(self):
        cfg = T.config()
        spec = SA.build_view(cfg, T.section(), T.evidence(), 'a' * 64)
        self.assertEqual(spec['members'], (E, S, N))
        self.assertEqual(spec['receiver_of'], T.RECV)
        self.assertEqual(spec['lanes'][1]['S'], 81.0)
        self.assertEqual(spec['lanes'][2]['S'], 63.0)
        self.assertAlmostEqual(spec['exit129_m'], T.EXIT129, places=9)
        self.assertEqual(spec['connector_link'], '10777')
        self.assertEqual(spec['tail_link'], '129')

    def assertRefused(self, error=SA.StoplineConfigError, **changes):
        cfg = T.config()
        section = T.section(**changes.pop('section', {}))
        document = T.evidence(**changes.pop('evidence', {}))
        mutate = changes.pop('cfg', None)
        if mutate:
            mutate(cfg)
        with self.assertRaises(error):
            SA.build_view(cfg, section, document, 'a' * 64)

    def test_section_fields(self):
        base = T.section()
        for broken in ({k: v for k, v in base.items() if k != 'merge_rule'}, {**base, 'extra': 1},
                       {**base, 'storage': 'sfull'}, {**base, 'lane_model': 'group'},
                       {**base, 'approaches': ['SC1001_EB', 'X']}, {**base, 'evidence': {'path': 'x'}},
                       {**base, 'evidence': {'path': 'C:/abs.json', 'sha256': '0' * 64}},
                       {**base, 'evidence': {'path': 'x.json', 'sha256': 'A' * 64}}):
            with self.subTest(broken=sorted(broken)), self.assertRaises(SA.StoplineConfigError):
                SA.check_section(broken)

    def test_evidence_values(self):
        lanes = T.evidence()['approaches']['SC1001_EB']['lanes']
        bad_geo = json.loads(json.dumps(lanes)); bad_geo['1']['storage_veh']['geometric'] += 1e-6
        bad_sat = json.loads(json.dumps(lanes)); bad_sat['2']['s_veh_h_lane'] = 2300.0
        bad_members = json.loads(json.dumps(lanes)); bad_members['2']['members'] = ['E', 'S']
        for evidence in ({'lanes': bad_geo}, {'lanes': bad_sat}, {'lanes': bad_members},
                         {'jam_spacing_m': 6.3}, {'p_lane1_given_E': 1.0},
                         {'upstream_lane_prior': {'1': {'E': 0.5, 'S': 0.4}, '2': {'E': 1.0}, '3': {'N': 1.0}}},
                         {'posthead_rehome': {'10118': 'SC1001_to_SC1003'}},
                         {'posthead_rehome': {'99999': 'SC1001_to_SC2002'}},
                         {'pre_stopline_links': ['32', '129', '10777']},
                         {'route_exit': {'1117:3': 'W'}}, {'receiver': 'in_SC1001_E'}):
            with self.subTest(evidence=sorted(evidence)):
                self.assertRefused(evidence=evidence)
        document = T.evidence()
        document['inputs']['g2_inpx']['extract_sha12'] = 'deadbeef0000'
        with self.assertRaises(SA.StoplineConfigError):
            SA.build_view(T.config(), T.section(), document, 'a' * 64)

    def test_member_contract(self):
        def mutate(field, value, name=E):
            return lambda cfg: cfg.network.urban_movements[name].__setitem__(field, value)
        self.assertRefused(cfg=lambda cfg: cfg.network.urban_movements.pop(S))
        self.assertRefused(cfg=mutate('kind', 'internal'))
        self.assertRefused(cfg=mutate('phase', 'SC1001_p4'))
        self.assertRefused(cfg=mutate('phase', 'SC1001_p3', N))
        self.assertRefused(cfg=mutate('ramp', 'RM_C10482'))
        self.assertRefused(cfg=mutate('origin', 'in_SC1001_E'))
        self.assertRefused(cfg=mutate('receiving_link', 'SC1001_to_SC1003'))

    def test_configure_reads_pinned_evidence(self):
        tmp = Path(tempfile.mkdtemp(prefix='_sa_tmp_', dir=HERE))
        try:
            path = tmp / 'evidence.json'
            path.write_text(json.dumps(T.evidence()), encoding='utf-8')
            digest = __import__('hashlib').sha256(path.read_bytes()).hexdigest()
            rel = path.relative_to(ROOT).as_posix()
            tuning = {'urban': {'stopline_approach': T.section(path=rel, sha=digest), 'queue': {'contiguous': True}},
                      'freeway': {'lane_plant': 'diagnostics/sdmpc_n31_20260924/plant_n31_v2.json'}}
            cfg = T.config()
            meta = SA.configure(cfg, tuning, {})
            self.assertEqual(meta['stopline_approach_storage_arm'], 'observed_full')
            self.assertEqual(SA.view(cfg)['evidence_sha256'], digest)
            with self.assertRaises(SA.StoplineConfigError):     # configured once
                SA.configure(cfg, tuning, {})
            for broken in ({**tuning, 'freeway': {}},
                           {**tuning, 'urban': {**tuning['urban'], 'queue': {'contiguous': False}}},
                           {**tuning, 'urban': {**tuning['urban'],
                                                'stopline_approach': T.section(path=rel, sha='1' * 64)}}):
                with self.subTest(broken=broken), self.assertRaises(SA.StoplineConfigError):
                    SA.configure(T.config(), broken, {})
            geometric = {**tuning, 'urban': {**tuning['urban'],
                                             'stopline_approach': T.section('geometric', path=rel, sha=digest)}}
            cfg = T.config()
            SA.configure(cfg, geometric, {})
            self.assertEqual(SA.view(cfg)['lanes'][1]['S'], T.HEADS[1] / 6.0)
        finally:
            shutil.rmtree(tmp)


# ------------------------------------------------------------------- T2 absent

class KeyAbsentTests(unittest.TestCase):
    def test_configure_and_initialize_are_noops(self):
        cfg = T.config()
        st = T.state(cfg, 100)
        before = pickle.dumps((cfg, st), protocol=4)
        self.assertEqual(SA.configure(cfg, {'urban': {'queue': {'contiguous': True}}}, {}), {})
        self.assertEqual(SA.configure(cfg, None, {}), {})
        self.assertEqual(SA.initialize(st, cfg, {}, {}, None), {})
        self.assertFalse(hasattr(cfg.network, 'stopline_approach'))
        self.assertFalse(hasattr(st, 'stopline_approach_state'))
        self.assertEqual(pickle.dumps((cfg, st), protocol=4), before)
        with self.assertRaises(SA.StoplineInitError):
            SA.initialize(st, cfg, {}, {}, None, tuning={'urban': {'stopline_approach': T.section()}})

    def test_view_is_one_attribute_lookup(self):
        self.assertIsNone(SA.view(T.config()))


# ------------------------------------------------------------ T3 lane service

class LaneServiceTests(unittest.TestCase):
    def test_arrival_order_and_budget(self):
        cfg, st = T.bare(75)          # p3 green 75..119
        ctl = T.control()
        order = []
        for i in range(110):
            member = S if i % 11 == 3 else E
            order.append((member, 0.9 if member == E else 0.8, T.add_ready(st, cfg, 1, member,
                                                                           0.9 if member == E else 0.8, 70)))
        s = st.stopline_approach_state
        s['init_excess'][1] = s['stock'][1] - 81.0
        served = {E: 0.0, S: 0.0}
        budget = T.SAT[1] * (1.0 / 3600.0)
        for t in range(75, 120):
            SA.split_arrival(st, cfg, t, 0.0, uqm.approach_routing(cfg)[IN])
            wanted = SA.intended(st, ctl, cfg, t)
            self.assertLessEqual(math.fsum(x for _p, _m, x in s['plan']['lists'][1]), budget + 1e-12)
            realized = SA.resolve(st, cfg, dict(wanted))
            for member in (E, S):
                if realized[member] > 0:
                    before = st.urban_movement_queue[member]
                    SA.dequeue(st, cfg, member, realized[member], t)
                    st.urban_movement_queue[member] = before - realized[member]
                    served[member] += realized[member]
            SA.end_step(st, cfg, t)
        total = served[E] + served[S]
        self.assertAlmostEqual(total, budget * 45, places=9)
        # FIFO: exactly a prefix of the arrival order left the lane (the last one possibly in part).
        remaining = s['lanes'][1]
        first = next(i for i, (_m, _a, p) in enumerate(order) if p is remaining[0])
        self.assertEqual([p for _m, _a, p in order[first:]], remaining)
        expected = {E: 0.0, S: 0.0}
        for member, amount, _p in order[:first]:
            expected[member] += amount
        partial_member, partial_amount, partial = order[first]
        expected[partial_member] += partial_amount - partial[4]
        for member in (E, S):
            self.assertAlmostEqual(served[member], expected[member], places=9)
        self.assertGreater(served[S], 0.0)

    def test_zero_green_serves_nothing(self):
        cfg, st = T.bare(10)          # p1 green: lanes 1-3 red
        T.add_ready(st, cfg, 1, E, 5.0, 5)
        T.add_ready(st, cfg, 3, N, 5.0, 5)
        SA.split_arrival(st, cfg, 10, 0.0, uqm.approach_routing(cfg)[IN])
        wanted = SA.intended(st, T.control(), cfg, 10)
        self.assertEqual(wanted, {E: 0.0, S: 0.0, N: 0.0})
        SA.resolve(st, cfg, wanted)
        SA.end_step(st, cfg, 10)
        self.assertEqual(st.stopline_approach_state['counters']['lane_budget_binding_steps_1'], 1.0)

    def test_two_saturated_lanes_are_not_one_to_one(self):
        cfg, st = T.bare(75)
        ctl = T.control()
        served = {E: 0.0, S: 0.0}
        for t in range(75, 120):
            _diag, record = T.drive(st, cfg, ctl, t, gate=4.0)
            for member in (E, S):
                served[member] += record['departed'].get(member, 0.0)
        self.assertGreater(served[E], 3.0 * served[S])
        self.assertGreater(served[S], 0.0)

    def test_city_between_ready_and_moving_port_packet(self):
        cfg, st = T.bare(80)
        r1 = T.add_ready(st, cfg, 1, E, 0.3, 70)
        T.add_ready(st, cfg, 1, S, 0.2, 75)
        p = T.add_moving(st, cfg, 1, E, 0.4, 100, source='port:OR_D_W')
        uqm._schedule(st.urban_arrival_buffer, IN, 80, 1.0)
        uqm._schedule(st.urban_storage_release_buffer, IN, 80, 1.0)
        st.urban_link_storage[IN] -= 1.0
        T.drive(st, cfg, T.control(greens={**T.GREENS, 'SC1001_p3': 120.0}), 80)
        packets = st.stopline_approach_state['lanes'][1]
        self.assertNotIn(r1, packets)        # served
        sources = [x[2] for x in packets]
        self.assertEqual(sources[-1], 'port:OR_D_W')
        self.assertIs(packets[-1], p)
        self.assertTrue(all(s == 'city' or s == 'init:city' for s in sources[:-1]))
        ctl = T.control(greens={**T.GREENS, 'SC1001_p3': 120.0})
        for t in range(81, 100):
            _diag, record = T.drive(st, cfg, ctl, t)
            self.assertIn(p, st.stopline_approach_state['lanes'][1])
        self.assertEqual(st.stopline_approach_state['counters']['served_port_OR_D_W_veh'], 0.0)
        for t in range(100, 104):
            T.drive(st, cfg, ctl, t)
        self.assertGreater(st.stopline_approach_state['counters']['served_port_OR_D_W_veh'], 0.0)

    def test_phase_fraction_is_looked_up_at_call_time(self):
        cfg, st = T.bare(75)
        T.add_ready(st, cfg, 1, E, 5.0, 70)
        SA.split_arrival(st, cfg, 75, 0.0, uqm.approach_routing(cfg)[IN])
        with mock.patch.object(uqm, '_phase_green_fraction', return_value=0.25):
            wanted = SA.intended(st, T.control(), cfg, 75)
        self.assertEqual(wanted[E], T.SAT[1] * (1.0 / 3600.0) * 0.25)


# ---------------------------------------------------------- T4/T5 port release

class ZipperTests(unittest.TestCase):
    READY = {'10491': [[231.4, 30.0, 1]] * 3, '10481': [[454.3, 30.0, 1]] * 3}

    def plan(self, st, cfg, step=120):
        SA.allocate(st, cfg, step, '10491', None)
        return st.stopline_approach_state['plan']['ports']

    def fill(self, st, cfg, lane, stock):
        s = st.stopline_approach_state
        member = {1: E, 2: E, 3: N}[lane]
        T.add_ready(st, cfg, lane, member, stock, 100)
        self.assertEqual(s['stock'][lane], stock)

    def test_large_room_grants_requests(self):
        cfg, st = T.bare(120, cohorts=self.READY)
        ports = self.plan(st, cfg)
        for off, lanes in (('10491', 1), ('10481', 2)):
            self.assertAlmostEqual(ports[off]['request'], 1400.0 * lanes / 3600.0, places=12)
            self.assertAlmostEqual(ports[off]['limit'], ports[off]['request'], places=12)

    def test_small_room_halves_and_lends(self):
        cfg, st = T.bare(120, cohorts=self.READY)
        self.fill(st, cfg, 1, 81.0 - 0.2)
        ports = self.plan(st, cfg)
        self.assertAlmostEqual(ports['10481']['alloc'][1], 0.1, places=12)
        self.assertAlmostEqual(ports['10491']['alloc'][1], 0.1, places=12)
        cfg, st = T.bare(120, cohorts={'10491': self.READY['10491'], '10481': [[454.3, 30.0, 1]]})
        st.lane_offramp_runtime.ports['10481'].ready = 0.05
        st.lane_offramp_runtime.ports['10481'].pending = []
        st.urban_link_storage['OR_D_E_storage'] = T.CAPS['OR_D_E_storage'] - 0.05
        self.fill(st, cfg, 1, 81.0 - 0.2)
        ports = self.plan(st, cfg)
        w = cfg.network.stopline_approach['ports']['10481']['weights'][1]
        self.assertAlmostEqual(ports['10481']['alloc'][1], 0.05 * w, places=12)
        self.assertAlmostEqual(ports['10491']['alloc'][1],
                               min(cfg.network.stopline_approach['ports']['10491']['weights'][1] * 1400 / 3600,
                                   0.2 - 0.05 * w), places=12)

    def test_zero_weight_lane_is_skipped(self):
        cfg = T.config()
        for name in ('SC1001_offW_to_N_SC2002', 'SC1001_offE_to_N_SC2002'):
            cfg.network.urban_movements[name]['beta'] = 0.0
        cfg, st = T.bare(120, cohorts=self.READY, cfg=cfg)
        self.fill(st, cfg, 3, T.OBSERVED[3])
        ports = self.plan(st, cfg)
        self.assertEqual(cfg.network.stopline_approach['ports']['10491']['weights'][3], 0.0)
        self.assertGreater(ports['10491']['limit'], 0.3)

    def test_joint_cap(self):
        cfg, st = T.bare(120, cohorts=self.READY)
        st.urban_link_storage[IN] = 0.5
        ports = self.plan(st, cfg)
        self.assertAlmostEqual(ports['10481']['limit'], 0.25, places=12)
        self.assertAlmostEqual(ports['10491']['limit'], 0.25, places=12)
        self.assertLessEqual(ports['10481']['limit'] + ports['10491']['limit'], 0.5 + 1e-12)
        self.assertEqual(st.stopline_approach_state['counters']['port_joint_room_binding_steps'], 1.0)


class ConnectorFifoTests(unittest.TestCase):
    def test_one_full_lane_blocks_the_whole_connector(self):
        cfg, st = T.bare(120, cohorts=ZipperTests.READY)
        T.add_ready(st, cfg, 3, N, T.OBSERVED[3], 100)
        diag, record = T.drive(st, cfg, T.control(), 120)
        self.assertEqual(record['released'], {})
        self.assertEqual(diag['stopline_lane_full_steps_3'], 1.0)
        self.assertEqual(diag['stopline_port_blocked_steps_10491'], 1.0)
        self.assertEqual(diag['stopline_port_blocked_steps_10481'], 1.0)

    def test_release_within_limit(self):
        cfg, st = T.bare(120, cohorts=ZipperTests.READY)
        T.add_ready(st, cfg, 2, E, 63.0 - 0.05, 100)
        SA.split_arrival(st, cfg, 120, 0.0, uqm.approach_routing(cfg)[IN])
        limits = {off: SA.allocate(st, cfg, 120, off, None)[2] for off in SA.PORTS}
        self.assertTrue(all(v < 0.2 for v in limits.values()))
        st.stopline_approach_state['plan'] = {}
        st.stopline_approach_state['last_step'] = 119
        _diag, record = T.drive(st, cfg, T.control(), 120)
        for off, n in record['released'].items():
            self.assertLessEqual(n, limits[off] + 1e-12)


class LorIntegrationTests(unittest.TestCase):
    """T5b on the real DelayedPort/LaneOfframpRuntime; the LOR hook itself lands with the hooks commit."""

    def test_release_tags_reservations_and_mirror(self):
        cfg, st = T.bare(120, cohorts=ZipperTests.READY)
        routing = uqm.approach_routing(cfg)
        lor = st.lane_offramp_runtime
        SA.split_arrival(st, cfg, 120, 0.0, routing[IN])
        for off in SA.PORTS:
            arrival_before = copy.deepcopy(st.urban_arrival_buffer.get(IN, {}))
            release_before = copy.deepcopy(st.urban_storage_release_buffer.get(IN, {}))
            tags_before = copy.deepcopy(st.stopline_approach_state['tags'])
            key = lor.descriptions[off]['storage']
            avail_before = st.urban_link_storage[key]
            request = SA.allocate(st, cfg, 120, off, lor.ports[off])
            actual = lor.ports[off].release(120, 1., request[2] * 3600.)
            n = request[2] * actual / request[2]
            st.urban_link_storage[key] += n
            st.urban_link_storage[IN] -= n
            SA.land_release(st, cfg, 120, off, n, routing)
            lor.assert_mirrors(st, cfg)
            self.assertAlmostEqual(st.urban_link_storage[key] - avail_before, n, places=12)
            arrival = st.urban_arrival_buffer[IN]
            delta = {k: arrival.get(k, 0.0) - arrival_before.get(k, 0.0) for k in arrival}
            release = st.urban_storage_release_buffer[IN]
            self.assertEqual({k: release.get(k, 0.0) - release_before.get(k, 0.0) for k in release}, delta)
            self.assertAlmostEqual(math.fsum(delta.values()), n, places=12)
            tags = st.stopline_approach_state['tags']
            added = math.fsum(v for due, row in tags.items() for k, v in row.items()
                              if v != tags_before.get(due, {}).get(k))
            self.assertAlmostEqual(added, n, places=12)
            for due, row in tags.items():
                self.assertLessEqual(math.fsum(row.values()), arrival[due] + 1e-12)
        for name in cfg.network.stopline_approach['offramp_movements']:
            self.assertEqual(st.urban_movement_queue[name], 0.0)

    def test_tiny_moving_share_stays_untagged_in_the_reservation(self):
        """N-A4/N-A5: a primal <= 1e-12 lane share makes no packet; the per-lane reservation keeps it."""
        cfg = T.config()
        cfg.network.urban_movements['SC1001_offW_to_S_SC1003']['beta'] = 1e-14
        cfg, st = T.bare(120, cohorts=ZipperTests.READY, cfg=cfg)
        routing = uqm.approach_routing(cfg)
        SA.split_arrival(st, cfg, 120, 0.0, routing[IN])
        request = SA.allocate(st, cfg, 120, '10491', None)
        n = request[2]
        SA.land_release(st, cfg, 120, '10491', n, routing)
        s = st.stopline_approach_state
        tagged = math.fsum(v for row in s['tags'].values() for v in row.values())
        reserved = math.fsum(st.urban_arrival_buffer[IN].values())
        self.assertAlmostEqual(reserved, n, places=15)
        self.assertLess(tagged, n)
        self.assertAlmostEqual(n - tagged, n * cfg.network.stopline_approach['ports']['10491']['beta_tilde']['S'],
                               delta=1e-15)
        self.assertEqual(s['counters']['untagged_port_share_events'], 1.0)
        self.assertNotIn(S, [p[3] for p in s['lanes'][1]])


# ------------------------------------------------------- T6 toy conservation

class ToyConservationTests(unittest.TestCase):
    def test_many_steps_with_ledger(self):
        cohorts = {'10491': [[200.0 + i, 20.0, 1] for i in range(10)],
                   '10481': [[400.0 + i, 20.0, 1 + i % 2] for i in range(20)]}
        cfg, st = T.bare(60, cohorts=cohorts)
        T.add_ready(st, cfg, 1, E, 20.0, 50)
        T.add_ready(st, cfg, 1, S, 3.0, 50)
        T.add_ready(st, cfg, 2, E, 15.0, 55)
        T.add_ready(st, cfg, 3, N, 4.0, 55)
        T.add_moving(st, cfg, 1, E, 0.7, 75, source='init:port')
        T.add_moving(st, cfg, 3, N, 0.3, 64, source='init:unknown')
        ledger = T.attach_ledger(st, cfg)
        ctl = T.control()
        rng = random.Random(3)
        for t in range(60, 260):
            T.drive(st, cfg, ctl, t, gate=rng.uniform(0.0, 0.4),
                    landing={'10491': rng.uniform(0.0, 0.3), '10481': rng.uniform(0.0, 0.5)})
        counters = st.stopline_approach_state['counters']
        self.assertGreater(counters['port_release_veh_10491'], 1.0)
        self.assertGreater(counters['served_port_OR_D_E_veh'], 1.0)
        self.assertGreater(counters['served_city_veh'], 1.0)
        self.assertGreater(counters['np_boundary_in_veh'], 0.0)
        self.assertGreater(counters['internal_crossing_veh'], 0.0)
        self.assertEqual(st.stopline_approach_state['plan'], {})
        ledger.assert_stocks(T.inventory(st, cfg))
        diag = SA.diagnostics(st)
        self.assertLessEqual(len([k for k in diag if k in {'stopline_' + x for x in SA.STEP_KEYS}]), 20)
        self.assertAlmostEqual(counters['np_off_ramp_veh'],
                               counters['port_release_veh_10491'] + counters['port_release_veh_10481'], places=9)

    def test_invariant_violations_raise(self):
        cfg, st = T.bare(60)
        T.add_ready(st, cfg, 1, E, 1.0, 50)
        st.urban_movement_queue[E] += 0.01
        with self.assertRaises(SA.StoplineInvariantError):
            SA.end_step(st, cfg, 60)                                 # I7
        cfg, st = T.bare(60)
        T.add_ready(st, cfg, 1, E, 1.0, 50)
        st.stopline_approach_state['stock'][1] += 0.01
        with self.assertRaises(SA.StoplineInvariantError):
            SA.end_step(st, cfg, 60)                                 # I3
        cfg, st = T.bare(60)
        T.add_moving(st, cfg, 1, E, 1.0, 70)
        st.urban_arrival_buffer[IN][70] = 0.5
        with self.assertRaises(SA.StoplineInvariantError):
            SA.end_step(st, cfg, 60)                                 # I1
        cfg, st = T.bare(60)
        st.urban_movement_queue['SC1001_offW_to_E_SC1002'] = 1e-15
        with self.assertRaises(SA.StoplineInvariantError):
            SA.end_step(st, cfg, 60)                                 # I5
        cfg, st = T.bare(60)
        SA.end_step(st, cfg, 60)
        with self.assertRaises(SA.StoplineInvariantError):
            SA.end_step(st, cfg, 62)                                 # contiguity

    def test_tag_exceeding_arrival_raises(self):
        cfg, st = T.bare(60)
        T.add_moving(st, cfg, 1, E, 1.0, 60)
        with self.assertRaises(SA.StoplineInvariantError):
            SA.split_arrival(st, cfg, 60, 0.5, uqm.approach_routing(cfg)[IN])


# --------------------------------------------------------------------- T7 due

class DueTests(unittest.TestCase):
    def test_formula_and_floor(self):
        self.assertEqual(SA._due(10, 121.67, 6.0, 0.0, 36.0), 10 + 13)
        self.assertEqual(SA._due(10, 0.0, 6.0, 0.0, 36.0), 11)
        self.assertEqual(SA._due(10, 100.0, 7.675, 20.0, 50.0), 11)
        self.assertEqual(SA._due(0, 600.0, 6.0, 0.0, 20.0), math.ceil(600.0 / (20.0 / 3.6)))

    def test_same_due_port_before_city_and_overtaking(self):
        cfg, st = T.bare(200, cohorts=ZipperTests.READY)
        s = st.stopline_approach_state
        routing = uqm.approach_routing(cfg)
        SA.split_arrival(st, cfg, 200, 0.0, routing[IN])
        for off in SA.PORTS:
            request = SA.allocate(st, cfg, 200, off, None)
            n = request[2]
            st.lane_offramp_runtime.ports[off].release(200, 1., n * 3600.)
            st.urban_link_storage[st.lane_offramp_runtime.descriptions[off]['storage']] += n
            st.urban_link_storage[IN] -= n
            SA.land_release(st, cfg, 200, off, n, routing)
        dues = {p[2]: p[0] for p in s['lanes'][1]}
        self.assertLess(dues['port:OR_D_E'], dues['port:OR_D_W'])      # 10481 @210 m ahead of 10491 @302 m
        self.assertEqual([p[2] for p in s['lanes'][1]][:2], ['port:OR_D_E', 'port:OR_D_E'])
        SA._check_index(st, cfg, cfg.network.stopline_approach, s, 200)
        SA.intended(st, T.control(), cfg, 200)
        SA.resolve(st, cfg, {})
        SA.end_step(st, cfg, 200)
        due = dues['port:OR_D_E']
        for t in range(201, due):
            SA.split_arrival(st, cfg, t, uqm._pop_buffer(st.urban_arrival_buffer, IN, t), routing[IN])
            SA.intended(st, T.control(), cfg, t)
            SA.resolve(st, cfg, {})
            SA.end_step(st, cfg, t)
        arrived = uqm._pop_buffer(st.urban_arrival_buffer, IN, due)
        SA.split_arrival(st, cfg, due, arrived + 0.5, routing[IN])
        lane1 = [(p[0], p[2]) for p in s['lanes'][1] if p[0] <= due]
        self.assertEqual([x[1] for x in lane1], ['port:OR_D_E', 'port:OR_D_E', 'city', 'city'])
        self.assertEqual([p[3] for p in s['lanes'][1] if p[0] == due and p[2] == 'city'], [E, S])
        keys = [(p[0], p[1]) for p in s['lanes'][1]]
        self.assertEqual(keys, sorted(keys))

    def test_storage_arm_moves_queue_tail(self):
        dues = {}
        for arm in ('observed_full', 'geometric'):
            cfg, st = T.bare(200, arm=arm, cohorts=ZipperTests.READY)
            T.add_ready(st, cfg, 1, E, 40.0, 190)
            routing = uqm.approach_routing(cfg)
            SA.split_arrival(st, cfg, 200, 0.0, routing[IN])
            request = SA.allocate(st, cfg, 200, '10481', None)
            SA.land_release(st, cfg, 200, '10481', request[2], routing)
            dues[arm] = max(p[0] for p in st.stopline_approach_state['lanes'][1])
            sigma = cfg.network.stopline_approach['lanes'][1]['sigma']
            self.assertEqual(dues[arm], SA._due(200, T.HEADS[1] - T.LANDING['10481'][1], sigma, 40.0, 30.0))
        self.assertLess(dues['observed_full'], dues['geometric'])


class StorageArmTests(unittest.TestCase):
    def test_sigma_and_capacity(self):
        cfg = T.config()
        observed = SA.build_view(cfg, T.section('observed_full'), T.evidence(), 'a' * 64)
        geometric = SA.build_view(T.config(), T.section('geometric'), T.evidence(), 'a' * 64)
        self.assertAlmostEqual(observed['lanes'][1]['sigma'], T.HEADS[1] / 81.0, places=12)
        self.assertAlmostEqual(observed['lanes'][1]['sigma'], 7.675, places=3)
        self.assertAlmostEqual(observed['lanes'][2]['sigma'], 9.866, places=3)
        self.assertAlmostEqual(observed['lanes'][3]['sigma'], 6.0, places=12)
        for lane in SA.LANES:
            self.assertAlmostEqual(geometric['lanes'][lane]['sigma'], 6.0, places=12)
            self.assertAlmostEqual(geometric['lanes'][lane]['S'], T.HEADS[lane] / 6.0, places=12)
        self.assertEqual((observed['lanes'][1]['S'], observed['lanes'][2]['S']), (81.0, 63.0))


# -------------------------------------------------------------- initialization

def raw_state(t0, vehicles):
    from evaluation.controllers.vehicle_routes import ATTRIBUTES
    records, routes, counts = [], [], {}
    for veh, link, lane, pos, kph, route in vehicles:
        records.append({'veh_no': veh, 'link_no': int(link), 'lane_no': lane, 'position_m': pos, 'speed_kph': kph})
        decision, number = (route.split(':') if route else (None, None))
        routes.append({'veh_no': veh, 'route_decision_no': int(decision) if decision else None,
                       'route_no': int(number) if number else None,
                       'route_decision_type': 'STATIC' if route else None})
        counts[str(link)] = counts.get(str(link), 0) + 1
    n = len(records)
    return {'sim_sec': t0,
            'vehicle_records': {'complete': True, 'records': records, 'collection_count_before': n,
                                'collection_count_after': n, 'record_count': n, 'capture_sim_sec_before': t0,
                                'capture_sim_sec_after': t0, 'full_network_link_counts': counts},
            'vehicle_routes': {'schema_version': 'vissim-vehicle-routes-v1', 'complete': True, 'records': routes,
                               'source_attributes': ATTRIBUTES, 'record_count': n, 'collection_count_before': n,
                               'collection_count_after': n, 'sim_sec_before': t0, 'sim_sec_after': t0}}


FOURTEEN_EXTRA = 'SC1001_E_SC1002_to_N_SC2002'
MAPPING = {'link_to_origins': {'32': [IN], '10778': [IN], '129': [IN], '10777': [IN], '127': [IN],
                               '10491': ['OR_D_W_storage'], '10481': ['OR_D_E_storage'],
                               '10118': ['SC1001_to_SC1002'], '10368': ['SC1001_to_SC1003'],
                               '10695': ['SC1001_to_SC2002', IN]}}
T0 = 600
POSTHEAD = [(91, '127', 2, 626.47, 30.0, '1117:3'), (92, '127', 1, 624.15, 25.0, '1117:1'),
            (93, '127', 3, 621.9, 20.0, '1117:2')]
READY127 = [(1, '127', 1, 615.0, 0.0, '1117:3'), (2, '127', 1, 608.0, 0.5, '1117:1'),
            (3, '127', 1, 590.0, 0.0, None), (4, '127', 2, 612.0, 0.0, '1117:3'), (5, '127', 3, 618.0, 0.0, '1117:2')]
MOVING127 = [(6, '127', 1, 400.0, 30.0, '1117:3'), (7, '127', 1, 150.0, 40.0, '1132:2'),
             (8, '127', 1, 100.0, 35.0, '1136:2'), (9, '127', 2, 500.0, 36.0, '1117:3'),
             (10, '127', 3, 300.0, 15.0, '1117:1')]
OTHERS = [(11, '10777', 1, 0.5, 20.0, '1132:2'), (12, '129', 1, 260.0, 30.0, '1132:2'),
          (13, '129', 1, 100.0, 45.0, '1136:2'), (14, '10695', 1, 1.0, 10.0, '1117:2')]


def init_case(*, vehicles=None, extra_provenance=None, seeds=None, queue_by_lane=None, arm='observed_full',
              rehome_other=1.0):
    """127: 13 vehicles (3 post-head, 5 queued, 5 moving), 10777 1, 129 2 (one 1132:2 tail), 10695 1."""
    cfg = T.config()
    cfg.network.urban_movements[FOURTEEN_EXTRA] = {
        'kind': 'internal', 'origin': 'SC1002_to_SC1001', 'beta': 0.4068, 'phase': 'SC1001_p3',
        'receiving_link': 'SC1001_to_SC2002', 'destination': 'x', 'ramp': None}
    cfg.network.stopline_approach = SA.build_view(cfg, T.section(arm), T.evidence(), 'f' * 64)
    st = T.state(cfg, T0)
    vehicles = vehicles if vehicles is not None else POSTHEAD + READY127 + MOVING127 + OTHERS
    raw = raw_state(T0, vehicles)
    fourteen = [m for m in cfg.network.urban_movements if m.startswith('SC1001_')]
    assert len(fourteen) == 14
    n127 = sum(1 for v in vehicles if v[1] == '127')
    queued = sum((queue_by_lane or {('127', '1'): 3, ('127', '2'): 1, ('127', '3'): 1}).values())
    provenance = {'127': {'storage:' + IN: float(n127 - queued), **{'movement:' + m: queued / 14 for m in fourteen}},
                  '10777': {'storage:' + IN: float(sum(1 for v in vehicles if v[1] == '10777'))},
                  '129': {'storage:' + IN: float(sum(1 for v in vehicles if v[1] == '129'))},
                  '10695': {'storage:' + IN: 1.0, 'storage:SC1001_to_SC2002': rehome_other}}
    for link, row in (extra_provenance or {}).items():
        provenance.setdefault(link, {}).update(row)
    provenance = {k: {kk: vv for kk, vv in v.items() if vv} for k, v in provenance.items()}
    st.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link'] = provenance
    for link, row in provenance.items():
        for key, amount in row.items():
            kind, name = key.split(':', 1)
            if kind == 'storage':
                st.urban_link_storage[name] -= amount
            else:
                st.urban_movement_queue[name] += amount
    seeds = seeds or {'127': {IN: {'moving': 5.0, 'stopped': 3.0, 'due_moving_step': T0 + 15,
                                   'due_stopped_step': T0 + 105}},
                      '10777': {IN: {'moving': 1.0, 'stopped': 0.0, 'due_moving_step': T0 + 15,
                                     'due_stopped_step': T0 + 105}},
                      '129': {IN: {'moving': 1.5, 'stopped': 0.5, 'due_moving_step': T0 + 15,
                                   'due_stopped_step': T0 + 105}},
                      '10695': {IN: {'moving': 1.0, 'stopped': 0.0, 'due_moving_step': T0 + 15,
                                     'due_stopped_step': T0 + 105}},
                      'unattributed': {IN: 0.0}}
    for link, rows in seeds.items():
        if link == 'unattributed':
            continue
        for storage, row in rows.items():
            if storage != IN:
                continue
            for name in ('urban_arrival_buffer', 'urban_storage_release_buffer'):
                uqm._schedule(getattr(st, name), IN, row['due_moving_step'], row['moving'])
                uqm._schedule(getattr(st, name), IN, row['due_stopped_step'], row['stopped'])
    return cfg, st, raw, copy.deepcopy(MAPPING), seeds, queue_by_lane or {('127', '1'): 3.0, ('127', '2'): 1.0,
                                                                              ('127', '3'): 1.0}


def run_init(case):
    cfg, st, raw, mapping, seeds, queue = case
    meta = SA.initialize(st, cfg, raw, mapping, seeds, queue_by_lane=queue)
    return cfg, st, meta


def area_inventory(st, cfg):
    """The deployed area-ledger inventory (control_area_objective.model_stock_values, reached from SA.initialize by
    runtime_setup -> area_runtime.configure -> seed_from_projection; its _nonnegative refused the amendment 6 negative
    receiver storage, review B-r3-1) on the toy.  The toy has no freeway, ramp, origin or transit stocks: those
    inputs are empty, the urban movement queues and storages are the real ones."""
    import types
    from evaluation.controllers.control_area_objective import model_stock_values
    net = copy.copy(cfg.network)
    net.freeway_links, net.ramps = {}, {}
    state = types.SimpleNamespace(**vars(st))
    state.mainline_origin_queue, state.urban_inflow_transit_buffer = {}, {}
    return model_stock_values(state, net, freeway_vehicle_counts={})


class InitLedgerTests(unittest.TestCase):
    def test_ledger_identities(self):
        case = init_case()
        cfg, st, raw, mapping, seeds, queue = case
        occ_before = {k: T.CAPS[k] - st.urban_link_storage[k] for k in T.CAPS}
        q_before = dict(st.urban_movement_queue)
        provenance = st.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
        p127 = dict(provenance['127'])
        arrival_before = math.fsum(st.urban_arrival_buffer[IN].values())
        cfg, st, meta = run_init(case)
        s = st.stopline_approach_state
        info = meta['stopline_approach_initial']
        self.assertEqual(info['posthead_veh'], 3.0)
        self.assertEqual(info['posthead_rehomed_veh'], 1.0)
        # 127 no longer feeds the E approach or an off-ramp movement (I9).
        for name in [m for m in q_before if m.startswith('SC1001_off')] + [FOURTEEN_EXTRA]:
            self.assertEqual(st.urban_movement_queue[name], 0.0)
        # Queue: the five walked vehicles become the W member queues (destination by route, else prior).
        prior = T.evidence()['approaches']['SC1001_EB']['upstream_lane_prior']['1']
        expected_q = {E: 2.0 + prior['E'], S: 1.0 + prior['S'], N: 1.0 + prior['N']}
        for member in (E, S, N):
            self.assertAlmostEqual(st.urban_movement_queue[member], expected_q[member], places=12)
            self.assertAlmostEqual(st.urban_movement_queue[member] - q_before[member],
                                   expected_q[member] - p127['movement:' + member], places=12)
        # Storage: in_SC1001_W loses 127's residual 8, 10777's 1 and 10695's 1; regains |M| = 5 + 1.
        occ_after = {k: T.CAPS[k] - st.urban_link_storage[k] for k in T.CAPS}
        self.assertAlmostEqual(occ_after[IN] - occ_before[IN], 6.0 - 8.0 - 1.0 - 1.0, places=9)
        self.assertAlmostEqual(occ_after['SC1001_to_SC2002'] - occ_before['SC1001_to_SC2002'], 2.0, places=9)
        self.assertAlmostEqual(occ_after['SC1001_to_SC1002'] - occ_before['SC1001_to_SC1002'], 1.0, places=9)
        self.assertAlmostEqual(occ_after['SC1001_to_SC1003'] - occ_before['SC1001_to_SC1003'], 1.0, places=9)
        # Mass: total over storages and queues is unchanged.
        total = lambda occ, q: math.fsum(occ.values()) + math.fsum(q.values())
        self.assertAlmostEqual(total(occ_after, st.urban_movement_queue), total(occ_before, q_before), places=9)
        # Provenance after.
        p = st.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
        self.assertEqual(p['127']['storage:' + IN], 5.0)
        self.assertEqual({k for k in p['127'] if k.startswith('storage:SC1001_to')},
                         {'storage:SC1001_to_SC1002', 'storage:SC1001_to_SC1003', 'storage:SC1001_to_SC2002'})
        self.assertEqual(p['10777'], {'storage:' + IN: 1.0})
        self.assertEqual(p['10695'], {'storage:SC1001_to_SC2002': 2.0})
        for link, count in (('127', 13), ('10777', 1), ('10695', 2)):
            self.assertAlmostEqual(math.fsum(p[link].values()), count, places=12)
        # Index: ready 5, moving 127 (5) + 10777 (1) + 129 tail (1).
        stock = math.fsum(s['stock'].values())
        self.assertAlmostEqual(stock, 5.0 + 6.0 + 1.0, places=12)
        # Lane-stock ledger identity (K8 amendment 5 section 3, replaces spec 5.8-9 T8 / H-2b
        # "N_127 + N_10777 - |A|" = 11; amendment 7 section 1 adds N_shortfall_kept):
        # sum_l stock_l = N_127 + N_10777 - |A| + N_tail129 + M_other + N_shortfall_kept.
        # This case: 13 + 1 - 3 + 1 (vehicle 12, 129 @260 m, 1132:2 = the 5.8-5 init:port packet) + 0 + 0 = 12,
        # which is the 5 + 6 + 1 above (vehicle 13 on 129 is 1136:2, gate-owned; no other-link W mass; every
        # receiver has room, so nothing is kept on 127).
        n127, n10777, posthead = 13.0, 1.0, info['posthead_veh']
        self.assertEqual((info['tail129_port_veh'], info['other_link_ready_veh']), (1.0, 0.0))
        self.assertEqual(info['posthead_receiver_shortfall_veh'], 0.0)
        self.assertAlmostEqual(stock, n127 + n10777 - posthead + info['tail129_port_veh']
                               + info['other_link_ready_veh'] + info['posthead_receiver_shortfall_veh'], delta=1e-9)
        self.assertNotAlmostEqual(stock, n127 + n10777 - posthead, delta=1e-9)     # the superseded target
        area_inventory(st, cfg)                         # the deployed area ledger accepts every stock
        ready = math.fsum(p_[4] for l in SA.LANES for p_ in s['lanes'][l] if p_[0] <= T0)
        self.assertAlmostEqual(ready + math.fsum(v for row in s['carry'].values() for v in row.values()), 5.0,
                               places=12)
        # Reservations: before - (127 + 10777 + 10695 seeds) - tail + new moving reservations.
        after = math.fsum(st.urban_arrival_buffer[IN].values())
        self.assertAlmostEqual(after, arrival_before - 8.0 - 1.0 - 1.0 - 1.0 + 7.0, places=12)
        tags = math.fsum(v for row in s['tags'].values() for v in row.values())
        self.assertAlmostEqual(after, 1.0 + tags, places=12)      # gate-owned 129 seed + all tags (I11)
        self.assertEqual(st.lane_offramp_runtime.descriptions['10491']['approach'], 'SC1001_EB')
        self.assertEqual(st.lane_offramp_runtime.descriptions['10481']['approach'], 'SC1001_EB')

    def test_sources_and_reassignment(self):
        cfg, st, meta = run_init(init_case())
        s = st.stopline_approach_state
        sources = {(p[2], p[3]) for l in SA.LANES for p in s['lanes'][l]}
        self.assertIn(('init:port', E), sources)         # 1132:2 on 127, 10777 and the 129 tail
        self.assertIn(('init:city', E), sources)         # 1136:2
        self.assertIn(('init:unknown', S), sources)      # 1117:1
        lane1 = [(p[2], p[3]) for p in s['lanes'][1]]
        lane3 = [(p[2], p[3]) for p in s['lanes'][3]]
        self.assertIn(('init:unknown', S), lane1)        # vehicle 10: S observed on lane 3 -> lane 1
        self.assertNotIn(S, [m for _s, m in lane3])
        # vehicle 10 (S on lane 3) + the N prior share of four lane-1 vehicles without a 1117 route
        # (590 m queued, 1132:2, 1136:2 and the 10777 vehicle).
        self.assertAlmostEqual(meta['stopline_approach_initial']['lane_reassigned_veh'],
                               1.0 + 4 * T.evidence()['approaches']['SC1001_EB']['upstream_lane_prior']['1']['N'],
                               places=12)
        self.assertEqual(meta['stopline_approach_initial']['tail129_port_veh'], 1.0)

    def test_moving_due_formula_and_monotone(self):
        vehicles = [(1, '127', 1, 500.0, 36.0, '1117:3')]
        cfg, st, meta = run_init(init_case(vehicles=vehicles, arm='geometric', queue_by_lane={},
                                           seeds={'127': {IN: {'moving': 0.0, 'stopped': 0.0,
                                                               'due_moving_step': T0 + 15,
                                                               'due_stopped_step': T0 + 105}},
                                                  'unattributed': {IN: 0.0}}, rehome_other=0.0,
                                           extra_provenance={'10695': {'storage:' + IN: 0.0}}))
        packets = st.stopline_approach_state['lanes'][1]
        self.assertEqual([p[0] for p in packets], [T0 + 13])       # ceil(121.67/10) = 13, not 4
        cfg, st, meta = run_init(init_case())
        for lane in SA.LANES:
            dues = [p[0] for p in st.stopline_approach_state['lanes'][lane] if p[0] > T0]
            self.assertEqual(dues, sorted(dues))
            self.assertTrue(all(d >= T0 + 1 for d in dues))

    def test_posthead_vehicles_use_the_departure_side_effects(self):
        case = init_case()
        cfg, st = case[0], case[1]
        debited = copy.deepcopy(st)
        for target in T.RECV.values():
            debited.urban_link_storage[target] -= 1.0     # _post_service debits before the delay (UFA order)
        delays = {k: uqm._link_delay_steps(debited, cfg, k) for k in T.RECV.values()}
        cfg, st, meta = run_init(case)
        for member, target in T.RECV.items():
            release = st.urban_storage_release_buffer.get(target, {})
            self.assertIn(T0 + delays[target], release)
        packets = [p for l in SA.LANES for p in st.stopline_approach_state['lanes'][l]]
        # five queued vehicles; the 590 m one has no 1117 route and splits into E, S (lane 1) and N (lane 3)
        self.assertEqual(len([p for p in packets if p[0] == T0]), 7)

    def test_provenance_and_seed_failures(self):
        case = init_case()
        case[1].local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link'][
            '127']['storage:' + IN] += 1.0
        with self.assertRaises(SA.StoplineInitError):
            run_init(case)
        case = init_case()
        case[1].urban_arrival_buffer[IN][T0 + 15] += 0.5
        with self.assertRaises(SA.StoplineInitError):                       # I11 premise
            run_init(case)

    def test_i11_is_two_sided(self):
        """N-1: |new moving reservations - tags| <= 1e-9 is asserted, not only tags <= reservations."""
        with mock.patch.object(SA, 'TINY', 0.6):        # moving shares <= 0.6 become untagged reservations
            with self.assertRaisesRegex(SA.StoplineInvariantError, 'I11: new moving reservations'):
                run_init(init_case())
        cfg, st, meta = run_init(init_case())            # deployed TINY: tags = new reservations
        s = st.stopline_approach_state
        tags = math.fsum(v for row in s['tags'].values() for v in row.values())
        self.assertEqual(meta['stopline_approach_initial']['tiny_moving_veh'], 0.0)
        self.assertGreater(tags, 0.0)

    def test_posthead_branch_a_keeps_the_shortfall_on_127(self):
        """N-2 / K8 amendment 7 section 1 rule (A) (replaces amendment 6 section 2, review B-r3-1): a short receiver is
        not refused in branch (a).  The share that fits the room is booked through _post_service (the receiver ends
        exactly full, never negative); the rest stays a head ready packet of the 127 lane the vehicle passed (due t0,
        its origin tag).  Mass is preserved, the deployed area-ledger inventory (control_area_objective
        model_stock_values, its _nonnegative) and the step-8 provenance audit pass, the kept share is reported and
        enters the lane-stock identity as N_shortfall_kept.
        """
        from evaluation.controllers.observation_projection import audit_projection_provenance
        recv = 'SC1001_to_SC1003'
        case = init_case(extra_provenance={'39': {'storage:' + recv: T.CAPS[recv] - 0.5}})
        st0 = case[1]
        occ_before = {k: T.CAPS[k] - st0.urban_link_storage[k] for k in T.CAPS}
        q_before = dict(st0.urban_movement_queue)
        release_before = math.fsum(st0.urban_storage_release_buffer.get(recv, {}).values())
        calls = []
        real = ufa._post_service

        def spy(state, cfg, movement, actual, step, routing, receiving_link):
            calls.append((movement, actual, step, receiving_link, state.urban_link_storage[receiving_link]))
            return real(state, cfg, movement, actual, step, routing, receiving_link)
        with mock.patch.object(ufa, '_post_service', spy):
            cfg, st, meta = run_init(case)                      # no StoplineInitError, no ProjectionError
        self.assertIn((S, 0.5, T0, recv, 0.5), calls)            # only the share that fits the room is booked
        self.assertEqual(len(calls), 3)
        info = meta['stopline_approach_initial']
        self.assertEqual(info['posthead_veh'], 3.0)
        self.assertEqual(info['posthead_receiver_shortfall_veh'], 0.5)       # reported
        self.assertEqual(st.urban_link_storage[recv], 0.0)                   # exactly full, never negative
        self.assertAlmostEqual(math.fsum(st.urban_storage_release_buffer.get(recv, {}).values()) - release_before,
                               0.5, places=12)
        # The kept 0.5 is the head ready packet of lane 1 (vehicle 92 passed lane 1, which serves S): due t0, origin
        # tag of its route 1117:1 (init:unknown), ahead of every pre-head packet; the S queue holds it (I7).
        s = st.stopline_approach_state
        head = s['lanes'][1][0]
        self.assertEqual((head[0], head[2], head[3], head[4]), (T0, 'init:unknown', S, 0.5))
        SA._check_index(st, cfg, cfg.network.stopline_approach, s, T0)
        # Mass: storages + queues unchanged; the receiver holds only the booked 0.5, 127 keeps the rest.
        occ_after = {k: T.CAPS[k] - st.urban_link_storage[k] for k in T.CAPS}
        total = lambda occ, q: math.fsum(occ.values()) + math.fsum(q.values())
        self.assertAlmostEqual(total(occ_after, st.urban_movement_queue), total(occ_before, q_before), places=9)
        self.assertAlmostEqual(occ_after[recv] - occ_before[recv], 0.5, places=12)
        prov = st.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
        self.assertEqual(prov['127']['storage:' + recv], 0.5)
        self.assertAlmostEqual(math.fsum(prov['127'].values()), 13.0, places=12)
        audit_projection_provenance(prov, occ_after, st.urban_movement_queue, st.ramp_queue)
        # Lane-stock identity with N_shortfall_kept: 13 + 1 - 3 + 1 + 0 + 0.5.
        self.assertAlmostEqual(math.fsum(s['stock'].values()),
                               13.0 + 1.0 - info['posthead_veh'] + info['tail129_port_veh']
                               + info['other_link_ready_veh'] + info['posthead_receiver_shortfall_veh'], delta=1e-9)
        # The deployed area ledger inventory accepts every stock (the amendment 6 booking, receiver -0.5, is refused).
        inv = area_inventory(st, cfg)
        self.assertTrue(all(v >= 0.0 for v in inv.values()))
        self.assertEqual(inv['storage:' + recv], T.CAPS[recv])
        bad = copy.copy(st)
        bad.urban_link_storage = dict(st.urban_link_storage, **{recv: -0.5})
        with self.assertRaisesRegex(ValueError, 'nonnegative'):
            area_inventory(bad, cfg)
        # No room at all: nothing booked for that vehicle, the whole vehicle is the head packet.
        calls.clear()
        case = init_case(extra_provenance={'39': {'storage:' + recv: T.CAPS[recv]}})
        with mock.patch.object(ufa, '_post_service', spy):
            cfg, st, meta = run_init(case)
        self.assertEqual([c[0] for c in calls if c[0] == S], [])
        self.assertEqual(meta['stopline_approach_initial']['posthead_receiver_shortfall_veh'], 1.0)
        self.assertEqual(st.urban_link_storage[recv], 0.0)
        self.assertEqual(st.stopline_approach_state['lanes'][1][0][3:], [S, 1.0])
        area_inventory(st, cfg)
        # Room exactly sufficient: shortfall 0, receiver exactly full, the whole vehicle booked (the _post_service
        # value; nothing beyond it runs): the lane index is the one of a run with ample room.
        calls.clear()
        case = init_case(extra_provenance={'39': {'storage:' + recv: T.CAPS[recv] - 1.0}})
        with mock.patch.object(ufa, '_post_service', spy):
            cfg, st, meta = run_init(case)
        self.assertIn((S, 1.0, T0, recv, 1.0), calls)
        self.assertEqual(meta['stopline_approach_initial']['posthead_receiver_shortfall_veh'], 0.0)
        self.assertEqual(st.urban_link_storage[recv], 0.0)
        _cfg, ample, _meta = run_init(init_case())
        self.assertEqual(st.stopline_approach_state['lanes'], ample.stopline_approach_state['lanes'])
        self.assertEqual(st.stopline_approach_state['stock'], ample.stopline_approach_state['stock'])

    def test_posthead_kept_share_over_the_lane_cap_is_init_excess(self):
        """Amendment 7 section 1: a kept post-head share that takes its lane over the cap S_l sits in that lane's
        init_excess (spec 5.8 initial excess; I3 holds with the cap plus init_excess)."""
        recv = 'SC1001_to_SC1003'
        _cfg, st_ref, _meta = run_init(init_case())
        lane1 = st_ref.stopline_approach_state['stock'][1]
        self.assertEqual(st_ref.stopline_approach_state['init_excess'][1], 0.0)
        case = init_case(extra_provenance={'39': {'storage:' + recv: T.CAPS[recv]}})       # no room: 1.0 kept
        case[0].network.stopline_approach['lanes'][1]['S'] = lane1                          # lane 1 exactly full
        cfg, st, meta = run_init(case)
        s = st.stopline_approach_state
        self.assertAlmostEqual(s['stock'][1], lane1 + 1.0, places=12)
        self.assertAlmostEqual(s['init_excess'][1], 1.0, places=12)
        self.assertAlmostEqual(meta['stopline_approach_initial']['excess_veh'], 1.0, places=12)
        SA._check_index(st, cfg, cfg.network.stopline_approach, s, T0)
        area_inventory(st, cfg)

    def test_posthead_rehome_keeps_the_receiver_shortfall_on_lane_3(self):
        """K8 amendment 8 section 1 (review N-r6-1): branch (d) under rule (A), no 'Posthead rehome overfills'.
        Toy: the 10695 in_SC1001_W share a_c = 1 competes with the (a) N vehicle 93 (lane 3, route 1117:2) for the
        N receiver SC1001_to_SC2002, whose room after the projection is 2.0 / 1.5 / 1.0 / 0.5 / 0.0.  Branch (a) takes
        the room first (fit_a = min(1, room)), branch (d) books fit_d = min(1, room - fit_a) with that share of the
        10695 seed cells; every kept share is a lane 3 head ready packet (the 10695 one ahead of vehicle 93's), the
        kept 10695 share stays on 10695's provenance as the N queue.  Every room initializes: mass preserved, no
        storage negative, the deployed area-ledger inventory (_nonnegative), the provenance audit and the t0 index
        checks pass, the combined shortfall is reported and closes the lane-stock identity as N_shortfall_kept.
        """
        from evaluation.controllers.observation_projection import audit_projection_provenance
        recv = 'SC1001_to_SC2002'
        _cfg, ample, _meta = run_init(init_case())
        for room in (2.0, 1.5, 1.0, 0.5, 0.0):
            with self.subTest(room=room):
                # init_case books 1.0 of 10695 on the N receiver already; link 39 fills it up to the room
                case = init_case(extra_provenance={'39': {'storage:' + recv: T.CAPS[recv] - 1.0 - room}})
                st0 = case[1]
                self.assertAlmostEqual(st0.urban_link_storage[recv], room, places=12)
                occ_before = {k: T.CAPS[k] - st0.urban_link_storage[k] for k in T.CAPS}
                q_before = dict(st0.urban_movement_queue)
                release_before = math.fsum(st0.urban_storage_release_buffer.get(recv, {}).values())
                arrival_in_before = math.fsum(st0.urban_arrival_buffer[IN].values())
                cfg, st, meta = run_init(case)                        # no StoplineInitError at any room
                info = meta['stopline_approach_initial']
                fit_a = min(1.0, room)
                fit_d = min(1.0, room - fit_a)
                kept_a, kept_d = 1.0 - fit_a, 1.0 - fit_d
                self.assertEqual(info['posthead_rehomed_veh'], 1.0)
                self.assertAlmostEqual(info['posthead_rehome_shortfall_veh'], kept_d, places=12)
                self.assertAlmostEqual(info['posthead_receiver_shortfall_veh'], kept_a + kept_d, places=12)
                # Storage: never negative; the receiver holds exactly what was booked.
                self.assertTrue(all(v >= 0.0 for v in st.urban_link_storage.values()), st.urban_link_storage)
                self.assertAlmostEqual(st.urban_link_storage[recv], room - fit_a - fit_d, places=12)
                occ_after = {k: T.CAPS[k] - st.urban_link_storage[k] for k in T.CAPS}
                self.assertAlmostEqual(occ_after[recv] - occ_before[recv], fit_a + fit_d, places=12)
                # Mass: storages + queues unchanged (the kept shares are member queue now).
                total = lambda occ, q: math.fsum(occ.values()) + math.fsum(q.values())
                self.assertAlmostEqual(total(occ_after, st.urban_movement_queue), total(occ_before, q_before),
                                       places=9)
                # Provenance: 10695 still sums to its 2 vehicles, no in_SC1001_W share (I11), the kept share is
                # the N queue on 10695; 127 still sums to its 13 vehicles.
                p = st.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
                want = {'storage:' + recv: 1.0 + fit_d}
                if kept_d > 0.0:
                    want['movement:' + N] = kept_d
                self.assertEqual(p['10695'].keys(), want.keys())
                for key, value in want.items():
                    self.assertAlmostEqual(p['10695'][key], value, places=12)
                self.assertAlmostEqual(math.fsum(p['10695'].values()), 2.0, places=12)
                self.assertAlmostEqual(math.fsum(p['127'].values()), 13.0, places=12)
                audit_projection_provenance(p, occ_after, st.urban_movement_queue, st.ramp_queue)
                # Reservations: the whole 10695 seed leaves in_SC1001_W, only fit_d of it reaches the receiver
                # (its projection cells are not moved for the kept share); (a) adds fit_a through _post_service.
                self.assertAlmostEqual(math.fsum(st.urban_storage_release_buffer.get(recv, {}).values())
                                       - release_before, fit_a + fit_d, places=12)
                tags = math.fsum(v for row in st.stopline_approach_state['tags'].values() for v in row.values())
                self.assertAlmostEqual(math.fsum(st.urban_arrival_buffer[IN].values()),
                                       arrival_in_before - 8.0 - 1.0 - 1.0 - 1.0 + tags, places=12)
                # Lane 3 head: due t0 ready packets, the 10695 share first, then vehicle 93's.
                s = st.stopline_approach_state
                head = [(p_[0], p_[2], p_[3], p_[4]) for p_ in s['lanes'][3][:2]]
                expect = [(T0, 'init:unknown', N, x) for x in (kept_d, kept_a) if x > 0.0]
                self.assertEqual(head[:len(expect)], expect)
                SA._check_index(st, cfg, cfg.network.stopline_approach, s, T0)
                # Lane-stock identity: 13 + 1 - 3 + 1 + 0 + N_shortfall_kept (both branches).
                self.assertAlmostEqual(math.fsum(s['stock'].values()),
                                       13.0 + 1.0 - info['posthead_veh'] + info['tail129_port_veh']
                                       + info['other_link_ready_veh'] + info['posthead_receiver_shortfall_veh'],
                                       delta=1e-9)
                self.assertAlmostEqual(math.fsum(s['stock'].values()) - math.fsum(ample.stopline_approach_state[
                    'stock'].values()), kept_a + kept_d, places=12)
                inv = area_inventory(st, cfg)                   # the deployed area ledger (_nonnegative) accepts
                self.assertTrue(all(v >= 0.0 for v in inv.values()))
                if room == 2.0:                                  # room >= both shares: the ample run, bit equal
                    self.assertEqual(s['lanes'], ample.stopline_approach_state['lanes'])
                    self.assertEqual(s['stock'], ample.stopline_approach_state['stock'])
                    self.assertEqual(p['10695'], {'storage:' + recv: 2.0})

    def test_posthead_rehome_kept_share_over_the_lane_3_cap_is_init_excess(self):
        """Amendment 8 section 1: the kept 10695 share that takes lane 3 over its cap sits in lane 3's init_excess."""
        recv = 'SC1001_to_SC2002'
        _cfg, st_ref, _meta = run_init(init_case())
        lane3 = st_ref.stopline_approach_state['stock'][3]
        self.assertEqual(st_ref.stopline_approach_state['init_excess'][3], 0.0)
        case = init_case(extra_provenance={'39': {'storage:' + recv: T.CAPS[recv] - 2.0}})   # room 1: (a) takes it
        case[0].network.stopline_approach['lanes'][3]['S'] = lane3                            # lane 3 exactly full
        cfg, st, meta = run_init(case)
        s = st.stopline_approach_state
        self.assertEqual(meta['stopline_approach_initial']['posthead_rehome_shortfall_veh'], 1.0)
        self.assertAlmostEqual(s['stock'][3], lane3 + 1.0, places=12)
        self.assertAlmostEqual(s['init_excess'][3], 1.0, places=12)
        self.assertAlmostEqual(meta['stopline_approach_initial']['excess_veh'], 1.0, places=12)
        SA._check_index(st, cfg, cfg.network.stopline_approach, s, T0)
        area_inventory(st, cfg)


class SeedSubtractTests(unittest.TestCase):
    def test_exact_cells(self):
        cfg, st, meta = run_init(init_case())
        arrival, release = st.urban_arrival_buffer[IN], st.urban_storage_release_buffer[IN]
        # New moving reservations are exactly the tags here (no primal <= 1e-12 share in this case).
        new = {due: math.fsum(row.values()) for due, row in st.stopline_approach_state['tags'].items()}
        expect15 = 8.5 - 5.0 - 1.0 - 1.0 - 0.75 + new.get(T0 + 15, 0.0)
        expect105 = 3.5 - 3.0 - 0.25 + new.get(T0 + 105, 0.0)
        self.assertAlmostEqual(arrival[T0 + 15], expect15, places=12)
        self.assertAlmostEqual(arrival[T0 + 105], expect105, places=12)
        self.assertEqual(arrival, release)
        self.assertGreater(st.urban_storage_release_buffer['SC1001_to_SC2002'].get(T0 + 15, 0.0), 0.0)

    def test_one_10777_vehicle_is_subtracted_once(self):
        cfg, st, meta = run_init(init_case())
        self.assertEqual(meta['stopline_approach_initial']['seed_residual_veh'], 0.0)
        self.assertEqual(st.local_observation_summary['projection_diagnostics'][
            'physical_stock_assignment_by_link']['10777'], {'storage:' + IN: 1.0})

    def shift(self, case, amount):
        for name in ('urban_arrival_buffer', 'urban_storage_release_buffer'):
            getattr(case[1], name)[IN][T0 + 105] -= amount
            getattr(case[1], name)[IN][T0 + 15] += amount

    def test_overdraw_and_residual(self):
        case = init_case()
        self.shift(case, 0.25 + 5e-10)            # stopped cell 3.5 -> 3.25 - 5e-10; 127 takes 3.0, the tail 0.25
        cfg, st, meta = run_init(case)
        self.assertAlmostEqual(meta['stopline_approach_initial']['seed_residual_veh'], 5e-10, delta=1e-15)
        self.assertGreaterEqual(min(st.urban_arrival_buffer[IN].values()), 0.0)
        case = init_case()
        self.shift(case, 0.6)
        with self.assertRaises(SA.StoplineInitError):
            run_init(case)

    def test_missing_seed_split_is_refused(self):
        cfg, st, raw, mapping, seeds, queue = init_case()
        with self.assertRaises(SA.StoplineInitError):
            SA.initialize(st, cfg, raw, mapping, None, queue_by_lane=queue)
        seeds['unattributed'] = {IN: 0.25}
        with self.assertRaises(SA.StoplineInitError):
            SA.initialize(st, cfg, raw, mapping, seeds, queue_by_lane=queue)


class OtherLinkMassTests(unittest.TestCase):
    def test_ready_order_and_mirror(self):
        extra = {'129': {'movement:' + E: 0.4}, '32': {'movement:' + S: 0.3, 'movement:' + E: 0.2},
                 '10778': {'movement:' + N: 0.1}}
        case = init_case(extra_provenance=extra)
        case[1].local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link'][
            '129']['storage:' + IN] -= 0.4
        case[1].urban_link_storage[IN] += 0.4
        case[4]['129'][IN]['moving'] -= 0.4
        for name in ('urban_arrival_buffer', 'urban_storage_release_buffer'):
            getattr(case[1], name)[IN][T0 + 15] -= 0.4
        case[1].local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link'][
            '32'] = {'movement:' + S: 0.3, 'movement:' + E: 0.2}
        case[1].local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link'][
            '10778'] = {'movement:' + N: 0.1}
        cfg, st, meta = run_init(case)
        s = st.stopline_approach_state
        ready1 = [(p[2], p[3]) for p in s['lanes'][1] if p[0] == T0]
        self.assertEqual(ready1[-3:], [('init:unknown', E), ('init:city', E), ('init:city', S)])
        self.assertEqual([(p[2], p[3]) for p in s['lanes'][3] if p[0] == T0][-1], ('init:city', N))
        SA._check_index(st, cfg, cfg.network.stopline_approach, s, T0)
        # Amendment 5 section 3 identity with M_other = 0.4 (129) + 0.5 (32) + 0.1 (10778) = 1.0 (N_shortfall_kept 0).
        info = meta['stopline_approach_initial']
        self.assertAlmostEqual(info['other_link_ready_veh'], 1.0, places=12)
        self.assertEqual(info['posthead_receiver_shortfall_veh'], 0.0)
        self.assertAlmostEqual(math.fsum(s['stock'].values()),
                               13.0 + 1.0 - info['posthead_veh'] + info['tail129_port_veh'] + info['other_link_ready_veh']
                               + info['posthead_receiver_shortfall_veh'], delta=1e-9)


class InitExcessTests(unittest.TestCase):
    def test_excess_blocks_ports_until_drained(self):
        cfg, st = T.bare(75, cohorts=ZipperTests.READY)
        T.add_ready(st, cfg, 2, E, 65.0, 70)
        s = st.stopline_approach_state
        s['init_excess'][2] = 2.0
        ctl = T.control()
        released = []
        for t in range(75, 120):
            _diag, record = T.drive(st, cfg, ctl, t)
            released.append((t, s['stock'][2], record['released'].get('10491', 0.0)))
        first_open = next(t for t, stock, n in released if n > 0.0)
        stock_at_open = next(stock for t, stock, n in released if t == first_open)
        self.assertLessEqual(stock_at_open, 63.0 + 1e-9)
        self.assertTrue(all(n == 0.0 for t, stock, n in released if t < first_open))
        self.assertGreater(first_open, 76)


# ----------------------------------------------------------- T12 install check

class InstallCheckTests(unittest.TestCase):
    def refused(self, mutate):
        cfg, st, raw, mapping, seeds, queue = init_case()
        mutate(cfg, st, mapping, seeds)
        with self.assertRaises(SA.StoplineInitError):
            SA.install_check(st, cfg, mapping, seeds)

    def test_passes(self):
        cfg, st, raw, mapping, seeds, queue = init_case()
        meta = SA.install_check(st, cfg, mapping, seeds)
        self.assertTrue(meta['stopline_approach_install_check']['passed'])
        self.assertEqual(meta['stopline_approach_install_check']['posthead_rehome'], ['10695'])
        self.assertEqual(meta['stopline_approach_install_check']['seeded_links'], ['127', '10777', '10695'])
        # A link without an in_SC1001_W residual needs no seed row (only residuals SA moves are checked).
        provenance = st.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
        provenance['10777'] = {}
        seeds.pop('10777')
        meta = SA.install_check(st, cfg, mapping, seeds)
        self.assertEqual(meta['stopline_approach_install_check']['seeded_links'], ['127', '10695'])

    def test_refusals(self):
        net = lambda cfg: cfg.network
        cases = {
            'view missing': lambda cfg, st, m, s: delattr(net(cfg), 'stopline_approach'),
            'row direct': lambda cfg, st, m, s: st.lane_offramp_runtime.descriptions['10491'].__setitem__('direct', True),
            'row group': lambda cfg, st, m, s: st.lane_offramp_runtime.descriptions['10481'].__setitem__('group', 'OR_D_W'),
            'local pool': lambda cfg, st, m, s: setattr(net(cfg), 'local_service_pool', {'group_of': {E: '10634'}}),
            'head pool': lambda cfg, st, m, s: setattr(net(cfg), 'head_service_resources',
                                                       {'extra_pool_groups': {'x': {'members': [S]}}}),
            'route corridor': lambda cfg, st, m, s: setattr(net(cfg), 'route_choice_corridor',
                                                            {'corridors': [{'movements': [N]}]}),
            'native input': lambda cfg, st, m, s: setattr(net(cfg), 'native_internal_inputs', {'inputs': {'1': E}}),
            'ramp member': lambda cfg, st, m, s: net(cfg).urban_movements[E].__setitem__('ramp', 'RM_C10482'),
            'receiver storage': lambda cfg, st, m, s: st.urban_link_storage.pop('SC1001_to_SC1003'),
            'city receiver': lambda cfg, st, m, s: net(cfg).physical_ramp_branches['shared_city_arrival'].__setitem__(
                'receiver', IN),
            'legsplit': lambda cfg, st, m, s: setattr(net(cfg), 'known_legsplit_routes', {'storage': 'SC1001_to_SC2002'}),
            'choice storage': lambda cfg, st, m, s: setattr(net(cfg), 'route_choice_corridor', {'capacity_veh': {IN: 1}}),
            '10368 not fixed': lambda cfg, st, m, s: m['link_to_origins']['10368'].append(IN),
            '10695 fixed': lambda cfg, st, m, s: m['link_to_origins'].__setitem__('10695', ['SC1001_to_SC2002']),
            '10695 other origin': lambda cfg, st, m, s: m['link_to_origins'].__setitem__('10695', ['SC1001_to_SC1002', IN]),
            'foreign origin link': lambda cfg, st, m, s: m['link_to_origins'].__setitem__('40', [IN]),
            'unattributed': lambda cfg, st, m, s: s.__setitem__('unattributed', {IN: {'moving': 0.1, 'stopped': 0.0}}),
            # K8-4 ce8fe80 row form {moving, stopped}: opposite signs are still an unattributed seed (rebase check)
            'unattributed opposite signs': lambda cfg, st, m, s: s.__setitem__(
                'unattributed', {IN: {'moving': 0.1, 'stopped': -0.1}}),
            # wiring commit additions: 10777/127 projection premise, seed rows, joint port cap owner
            '10777 seed row': lambda cfg, st, m, s: s.pop('10777'),
            '127 seed row': lambda cfg, st, m, s: s.pop('127'),
            '10695 seed row': lambda cfg, st, m, s: s.pop('10695'),
            '10777 origins': lambda cfg, st, m, s: m['link_to_origins'].__setitem__('10777', [IN, 'SC1001_to_SC1002']),
            '127 origins': lambda cfg, st, m, s: m['link_to_origins'].__setitem__('127', []),
            '10777 movements': lambda cfg, st, m, s: m.__setitem__('link_to_movements', {'10777': [{'movement': E}]}),
            'other row into receiver': lambda cfg, st, m, s: st.lane_offramp_runtime.descriptions.__setitem__(
                '10479', {'group': 'OR_D_W', 'direct': True, 'target': IN}),
        }
        for name, mutate in cases.items():
            with self.subTest(name):
                self.refused(mutate)

    def test_rehome_requires_declared_connector(self):
        cfg, st, raw, mapping, seeds, queue = init_case()
        cfg.network.stopline_approach['posthead_rehome'] = {}
        with self.assertRaises(SA.StoplineInitError):
            SA.install_check(st, cfg, mapping, seeds)

    def test_origin_binding_is_refused(self):
        """N-8: urban.queue.origin_binding on -> refused (129 tail would be both ready mass and moving tail)."""
        for flag in (True, 1):
            with self.subTest(flag=flag):
                cfg, st, raw, mapping, seeds, queue = init_case()
                tuning = {'urban': {'queue': {'contiguous': True, 'origin_binding': flag}}}
                with self.assertRaisesRegex(SA.StoplineInitError, 'origin_binding'):
                    SA.install_check(st, cfg, mapping, seeds, tuning=tuning)
                with self.assertRaisesRegex(SA.StoplineInitError, 'origin_binding'):
                    SA.initialize(st, cfg, raw, mapping, seeds, tuning=tuning, queue_by_lane=queue)
        for tuning in (None, {}, {'urban': {'queue': {'contiguous': True, 'origin_binding': False}}},
                       {'urban': {'queue': {'contiguous': True}}}):
            with self.subTest(tuning=tuning):
                cfg, st, raw, mapping, seeds, queue = init_case()
                self.assertTrue(SA.install_check(st, cfg, mapping, seeds, tuning=tuning)
                                ['stopline_approach_install_check']['passed'])


class PostheadRehomeTests(unittest.TestCase):
    """T9c, synthetic part: two 10695 vehicles become wholly downstream with their seed cells."""

    def test_two_vehicles(self):
        case = init_case()
        cfg, st = case[0], case[1]
        p = st.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
        self.assertEqual(p['10695'], {'storage:' + IN: 1.0, 'storage:SC1001_to_SC2002': 1.0})
        release_recv_before = dict(st.urban_storage_release_buffer.get('SC1001_to_SC2002', {}))
        cfg, st, meta = run_init(case)
        p = st.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
        self.assertEqual(p['10695'], {'storage:SC1001_to_SC2002': 2.0})
        recv = st.urban_storage_release_buffer['SC1001_to_SC2002']
        self.assertAlmostEqual(recv.get(T0 + 15, 0.0) - release_recv_before.get(T0 + 15, 0.0), 1.0, places=12)
        self.assertNotIn('SC1001_to_SC2002', st.urban_arrival_buffer)       # receiver not in routing here


# ------------------------------------------------- T10/T10b refactor identity

def old_contiguous(state_json):
    """Frozen copy of ADP _contiguous_stopline_queue at fef1e76 (5384-5461; unchanged through ec063ff), for T10."""
    from evaluation.controllers import vissim_stackelberg_adapter as a
    local = a._mapping(state_json.get("local_observation"))
    raw = local.get("queue_bins")
    if not isinstance(raw, dict) or not raw:
        return {}
    bin_m = a._as_float(local.get("queue_bin_m"), 7.0) or 7.0
    by_lane = {}
    for key, value in raw.items():
        parts = str(key).split("|")
        if len(parts) != 3:
            continue
        try:
            idx = int(parts[2])
        except (TypeError, ValueError):
            continue
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            total, stopped = a._as_float(value[0], 0.0), a._as_float(value[1], 0.0)
        else:
            total, stopped = a._as_float(value, 0.0), 0.0
        by_lane.setdefault((parts[0], parts[1]), {})[idx] = (total, stopped)
    lengths = a._link_lengths_m()
    out = {}
    for (link, _lane), bins in by_lane.items():
        if not bins:
            continue
        occupied_idx = [i for i, (t, _s) in bins.items() if t > 0.0]
        if not occupied_idx:
            continue
        length = lengths.get(str(link), 0.0)
        if length > 0.0:
            head_m = (max(occupied_idx) + 1) * bin_m
            if (length - head_m) > a._QUEUE_HEAD_WINDOW_M:
                continue
        queued = 0.0
        for idx in sorted(bins, reverse=True):
            total, stopped = bins[idx]
            if total <= 0.0:
                continue
            if total > stopped:
                break
            queued += stopped
        if queued > 0.0:
            out[link] = out.get(link, 0.0) + queued
    return out


class ContiguousWalkTests(unittest.TestCase):
    def cases(self):
        fixed = [
            {}, {'queue_bins': {}},
            {'queue_bins': {'127|1|88': [1, 1], '127|1|87': [1, 1], '127|1|86': [2, 1], '127|1|85': [1, 1]}},
            {'queue_bins': {'127|1|88': [1, 1], '127|2|88': [1, 1], '127|2|87': [0, 0], '127|2|86': [1, 1],
                            '127|3|80': [1, 0]}, 'queue_bin_m': 7.0},
            {'queue_bins': {'127|1|88': [0, 0], '127|2|88': [3, 3], '127|2|87': [2, 2]}},  # first lane 0, next >0
            {'queue_bins': {'32|1|280': [1, 1], '32|1|279': [1, 1], '32|2|281': [1, 1], '129|1|5': [2, 2]}},
            {'queue_bins': {'bad': [1, 1], '127|x|y': [1, 1], '127|1|88': 2.0, '127|1|87': [1.5, 1.5]}},
            {'queue_bins': {'66|1|379': [1, 1], '66|1|10': [1, 1], '127|3|88': [0.5, 0.25]}},
            {'queue_bins': {'127|1|88': [1, 1], '127|1|88 ': [1, 1], '40|2|179': [4, 4], '40|2|178': [1, 1]}},
            {'queue_bins': {'30|1|75': [1, 1], '30|1|76': [1, 1], '30|2|76': [2, 1], '30|2|75': [1, 1]},
             'queue_bin_m': 6.5},
        ]
        rng = random.Random(20261004)
        for _ in range(60):
            bins = {}
            for _k in range(rng.randrange(0, 40)):
                link = rng.choice(['127', '32', '129', '66', '40', '30'])
                lane = str(rng.randrange(1, 4))
                idx = rng.randrange(0, 400)
                total = rng.choice([0, 1, 2, 3, 0.5])
                bins[f'{link}|{lane}|{idx}'] = [total, rng.choice([0, total, min(total, 1)])]
            fixed.append({'queue_bins': bins, 'queue_bin_m': rng.choice([7.0, 6.0, 7.5])})
        return [{'local_observation': c} for c in fixed]

    def test_bit_identical(self):
        from evaluation.controllers import vissim_stackelberg_adapter as a
        lengths = {'127': 627.4, '32': 1970.0, '129': 302.0, '66': 2660.0, '40': 1258.0, '30': 535.0}
        with mock.patch.object(a, '_link_lengths_m', return_value=lengths):
            for case in self.cases():
                old, new = old_contiguous(case), a._contiguous_stopline_queue(case)
                self.assertEqual(repr(old), repr(new))
                by_lane = a._contiguous_stopline_queue_by_lane(case)
                self.assertTrue(all(v > 0.0 for v in by_lane.values()))
                summed = {}
                for (link, _lane), v in by_lane.items():
                    summed[link] = summed.get(link, 0.0) + v
                self.assertEqual(repr(summed), repr(new))


def old_post_block(state, cfg, movement, actual, step_idx, routing, spec):
    """Frozen copy of UFA:600-612 at fef1e76 (unchanged through ec063ff), for T10b."""
    receiving_link = str(spec.get("receiving_link", ""))
    if receiving_link in state.urban_link_storage:
        state.urban_link_storage[receiving_link] = max(
            0.0,
            state.urban_link_storage.get(receiving_link, 0.0) - actual,
        )
        if not ufa._receive_corridor(state, cfg, movement, actual, step_idx):
            delay_steps = uqm._link_delay_steps(state, cfg, receiving_link)
            arrival_step = step_idx + delay_steps
            if receiving_link in routing:
                uqm._schedule(state.urban_arrival_buffer, receiving_link, arrival_step, actual)
            uqm._schedule(state.urban_storage_release_buffer, receiving_link, arrival_step, actual)


class PostServiceTests(unittest.TestCase):
    def test_extraction_is_operation_identical(self):
        rng = random.Random(11)
        cfg = T.config()
        cfg.network.urban_movements['SC1001_E_SC1002_to_N_SC2002'] = {
            'kind': 'internal', 'origin': 'SC1001_to_SC1002', 'beta': 0.4, 'phase': 'SC1001_p3',
            'receiving_link': 'SC1001_to_SC2002', 'destination': 'x', 'ramp': None}
        cfg.network.urban_movements['ghost'] = {'kind': 'internal', 'origin': 'nowhere', 'beta': 0.0,
                                                'phase': 'SC1001_p1', 'receiving_link': 'not_a_storage',
                                                'destination': 'x', 'ramp': None}
        routing = uqm.approach_routing(cfg)
        self.assertIn('SC1001_to_SC1002', routing)
        specs = uqm.movement_specs(cfg)
        for corridor in (False, True):
            for _ in range(200):
                st = T.state(cfg, 300)
                for k in st.urban_link_storage:
                    st.urban_link_storage[k] = rng.choice([0.0, 0.3, rng.uniform(0, 400)])
                st.urban_link_speed_kph = {k: rng.uniform(0, 60) for k in ('SC1001_to_SC1002', 'SC1001_to_SC2002')
                                           if rng.random() < 0.5}
                movement = rng.choice(list(cfg.network.urban_movements))
                actual = rng.choice([0.0, 1e-17, rng.uniform(0, 2)])
                step = rng.randrange(0, 900)
                one, two = copy.deepcopy(st), copy.deepcopy(st)
                receiving_key = str(specs[movement].get('receiving_link', ''))   # the loop's UFA:632 value
                with mock.patch.object(ufa, '_receive_corridor', return_value=corridor):
                    old_post_block(one, cfg, movement, actual, step, routing, specs[movement])
                    # N-4: the extracted body does no lookup of its own (movement_specs is not called).
                    with mock.patch.object(uqm, 'movement_specs', side_effect=AssertionError('new work')):
                        ufa._post_service(two, cfg, movement, actual, step, routing, receiving_key)
                strip = lambda x: {k: v for k, v in vars(x).items() if k != 'lane_offramp_runtime'}
                self.assertEqual(repr(strip(one)), repr(strip(two)))

    def test_departure_loop_calls_the_extracted_function(self):
        source = Path(ufa.__file__).read_text(encoding='utf-8')
        self.assertIn('        state.urban_movement_queue[movement] = max(0.0, before - actual)\n'
                      '        _post_service(state, cfg, movement, actual, step_idx, routing, receiving_key)\n', source)
        self.assertEqual(source.count('_post_service('), 2)
        # N-4: receiving_key is the UFA:632 str(spec.get('receiving_link', '')) of the same loop iteration.
        self.assertIn("        receiving_key = str(spec.get('receiving_link', ''))\n", source)
        body = source.split('def _post_service(', 1)[1].split('\ndef ', 1)[0]
        self.assertNotIn('movement_specs', body)


# ------------------------------------------------------------- T14 copies

class CopyTests(unittest.TestCase):
    def test_deepcopy_and_pickle(self):
        cfg, st = T.bare(75, cohorts=ZipperTests.READY)
        T.add_ready(st, cfg, 1, E, 3.0, 70)
        for t in range(75, 90):
            T.drive(st, cfg, T.control(), t, gate=0.2, landing={'10491': 0.2})
        for clone in (copy.deepcopy(st), pickle.loads(pickle.dumps(st, protocol=4))):
            self.assertEqual(clone.stopline_approach_state, st.stopline_approach_state)
            self.assertEqual(repr(clone.stopline_approach_state), repr(st.stopline_approach_state))
        self.assertEqual(pickle.loads(pickle.dumps(cfg.network.stopline_approach)), cfg.network.stopline_approach)
        # Mid-step copies keep the plan's packet aliasing.
        T.add_ready(st, cfg, 1, E, 1.0, 89)
        SA.split_arrival(st, cfg, 90, 0.0, uqm.approach_routing(cfg)[IN])
        SA.intended(st, T.control(), cfg, 90)
        SA.resolve(st, cfg, dict(st.stopline_approach_state['plan']['intended']))
        clone = copy.deepcopy(st)
        lane, packet, _x = clone.stopline_approach_state['plan']['items'][E][0]
        self.assertTrue(any(p is packet for p in clone.stopline_approach_state['lanes'][lane]))


# --------------------------------------------------------- T15a/T19 ledger keys

class NpAccountingTests(unittest.TestCase):
    def run_case(self, internal_as_movement=False, capture=True):
        cohorts = {'10491': [[230.0 - i, 20.0, 1] for i in range(4)], '10481': [[450.0 - i, 20.0, 1] for i in range(4)]}
        cfg, st = T.bare(75, cohorts=cohorts)
        T.add_ready(st, cfg, 1, E, 0.3, 70, source='init:port')
        T.add_ready(st, cfg, 1, S, 0.2, 70, source='init:city')
        T.add_ready(st, cfg, 2, E, 0.25, 70, source='init:unknown')
        T.add_ready(st, cfg, 3, N, 0.4, 70, source='init:port')
        ledger = T.attach_ledger(st, cfg, capture=capture)
        ctl = T.control()
        counted = released = 0.0
        original = SA._internal

        def as_movement(state, cfg_, ledger_, movement, target, amount):
            from evaluation.controllers.control_area_objective import emit_transfer
            emit_transfer(state, cfg_, 'movement:' + movement, target, amount, route_key='movement:' + movement)
        with mock.patch.object(SA, '_internal', as_movement if internal_as_movement else original):
            for t in range(75, 450):
                _diag, record = T.drive(st, cfg, ctl, t, gate=0.2 if t < 120 else 0.0,
                                        landing={'10491': 0.15, '10481': 0.1} if t < 100 else None)
                counted += math.fsum(record['counted'].values())
                released += math.fsum(record['released'].values())
                ledger.residence(['movement:' + m for m in (E, S, N)] + ['storage:' + IN], 1 / 3600.)
        return cfg, st, ledger, counted, released

    def test_route_keys(self):
        cfg, st, ledger, counted, released = self.run_case()
        rows = ledger._response['transfers']
        by = {}
        for row in rows:
            prefix = ('off_ramp' if row['route_key'].startswith('movement:SC1001_off') else
                      'boundary_in' if row['route_key'].startswith('movement:SC1001_W_to') else
                      'internal' if row['route_key'].startswith('stopline_internal:') else 'other')
            by[prefix] = by.get(prefix, 0.0) + row['vehicles']
        self.assertAlmostEqual(by['off_ramp'], released, places=9)
        self.assertAlmostEqual(by['boundary_in'], counted, places=9)
        c = st.stopline_approach_state['counters']
        self.assertAlmostEqual(by['internal'], c['internal_crossing_veh'], places=9)
        self.assertAlmostEqual(counted, c['np_boundary_in_veh'], places=9)
        city_side = c['served_city_veh'] + c['served_init_city_veh'] + c['served_init_unknown_veh']
        port_side = c['served_port_OR_D_W_veh'] + c['served_port_OR_D_E_veh'] + c['served_init_port_veh']
        self.assertAlmostEqual(counted, city_side, delta=1e-9 + c['merge_tiny_transfer_veh'])
        self.assertAlmostEqual(by['internal'], port_side, delta=1e-9 + c['merge_tiny_transfer_veh'])
        self.assertGreater(c['served_init_port_veh'], 0.0)
        self.assertGreater(c['served_port_OR_D_W_veh'], 0.0)
        self.assertGreater(by['boundary_in'], 0.0)
        self.assertGreater(c['served_init_unknown_veh'], 0.0)
        self.assertGreater(c['served_init_city_veh'], 0.0)

    def test_internal_key_changes_no_stock_or_ttt(self):
        a = self.run_case(False)
        b = self.run_case(True)
        la, lb = a[2], b[2]
        self.assertEqual(repr(la.stocks), repr(lb.stocks))
        self.assertEqual(la.ttt_veh_h, lb.ttt_veh_h)
        self.assertLessEqual(abs(la.ttd_veh - lb.ttd_veh), 1e-12 * max(1.0, abs(la.ttd_veh)))
        self.assertLessEqual(abs(la.entered_veh - lb.entered_veh), 1e-12)   # rounding-level outside cohorts

    def test_single_transfer_when_port_share_is_tiny(self):
        cfg, st = T.bare(75)
        budget = cfg.network.stopline_approach['lanes'][1]['s_veh_h'] * cfg.simulation.T_u_h * 1.0
        T.add_ready(st, cfg, 1, E, budget - 1e-13, 70, source='city')
        T.add_ready(st, cfg, 1, E, 0.1, 71, source='init:port')
        ledger = T.attach_ledger(st, cfg, capture=True)
        ledger.begin_response_step('urban', 75, 76)
        SA.split_arrival(st, cfg, 75, 0.0, uqm.approach_routing(cfg)[IN])
        wanted = SA.intended(st, T.control(), cfg, 75)
        realized = SA.resolve(st, cfg, dict(wanted))
        port_take = st.stopline_approach_state['plan']['items'][E][-1][2]
        self.assertGreater(port_take, 0.0)
        self.assertLessEqual(port_take, 1e-12)
        counted = SA.depart(st, cfg, E, realized[E], 75, T.RECV[E])
        keys = [r['route_key'] for r in ledger._response['transfers']]
        self.assertEqual(keys, ['movement:' + E])
        self.assertEqual(counted, realized[E])
        self.assertEqual(st.stopline_approach_state['counters']['merge_tiny_transfer_events'], 1.0)


class OutsideCohortTests(unittest.TestCase):
    def prepared(self):
        cfg, st = T.bare(75)
        T.add_ready(st, cfg, 1, E, 0.3, 70, source='port:OR_D_W')
        ledger = T.attach_ledger(st, cfg)
        SA.split_arrival(st, cfg, 75, 0.0, uqm.approach_routing(cfg)[IN])
        realized = SA.resolve(st, cfg, SA.intended(st, T.control(), cfg, 75))
        return cfg, st, ledger, realized

    def test_outside_cohort_refused(self):
        cfg, st, ledger, realized = self.prepared()
        ledger.stocks['movement:' + E]['outside'] = 1e-6
        with self.assertRaises(SA.StoplineRouteError):
            SA.depart(st, cfg, E, realized[E], 75, T.RECV[E])

    def test_route_premise(self):
        for route in ({'target_inside': 1.0, 'inside_to_inside': 1.0, 'outside_to_inside': 1.0},
                      {'target_inside': True, 'inside_to_inside': 1.0, 'outside_to_inside': 0.5}, None):
            cfg, st, ledger, realized = self.prepared()
            if route is None:
                cfg.network.control_area_routes.pop('movement:' + E)
            else:
                cfg.network.control_area_routes['movement:' + E] = route
            with self.subTest(route=route), self.assertRaises(SA.StoplineRouteError):
                SA.depart(st, cfg, E, realized[E], 75, T.RECV[E])

    def test_no_ledger_no_transfer(self):
        cfg, st, ledger, realized = self.prepared()
        del st._control_area_ledger
        self.assertEqual(SA.depart(st, cfg, E, realized[E], 75, T.RECV[E]), 0.0)


# ------------------------------------------------- T13/T13b/T20 (tangent probe)

def probe(backend, scenario):
    env = dict(os.environ, PYTHONHASHSEED='0', NUMBA_NUM_THREADS='1', OMP_NUM_THREADS='1')
    if backend == 'reverse-v1':
        env['PYTHONPATH'] = os.pathsep.join([str(NUMBA_DEPS / 'sdmpc'), str(NUMBA_DEPS / 'sdmpc-numba'),
                                             env.get('PYTHONPATH', '')])
    done = subprocess.run([sys.executable, '-B', str(PROBE), backend, scenario], cwd=str(ROOT), env=env,
                          capture_output=True, text=True, timeout=900)
    if done.returncode != 0:
        raise AssertionError(done.stdout[-4000:] + done.stderr[-4000:])
    return json.loads(done.stdout.strip().splitlines()[-1])


class TangentTests(unittest.TestCase):
    def test_derivatives_match_central_differences(self):
        out = probe('forward', 'derivatives')
        self.assertGreater(out['nonzero_checks'], 6)
        self.assertLessEqual(out['max_rel_error'], 1e-6, out['worst'])
        self.assertIn('offset', out['report_only'])

    def test_tie_residual_folds_into_carry(self):
        out = probe('forward', 'tie')
        self.assertTrue(out['tie_packet_deleted'])
        self.assertEqual(out['tie_carry_primal'], 0.0)
        self.assertGreater(out['tie_carry_tangent_abs'], 0.0)
        self.assertEqual(out['carry_after_fold'], 0.0)
        self.assertGreater(out['folded_packet_tangent_abs'], 0.0)
        self.assertTrue(out['float_residual_deleted'])
        self.assertGreater(out['float_residual_carry'], 0.0)
        self.assertLessEqual(out['float_residual_carry'], 1e-12)
        self.assertLessEqual(out['mirror_tangent_error'], 1e-12)

    @unittest.skipUnless((NUMBA_DEPS / 'sdmpc-numba' / 'numba').is_dir(), 'pinned numba dependency is absent')
    def test_forward_and_reverse_carry_derivatives(self):
        forward, reverse = probe('forward', 'carry'), probe('reverse-v1', 'carry')
        self.assertEqual(forward['primal'], reverse['primal'])
        for a, b in zip(forward['derivative'], reverse['derivative']):
            self.assertLessEqual(abs(a - b), 1e-12)
        self.assertGreater(max(abs(x) for x in forward['derivative']), 0.0)


class StructureParityTests(unittest.TestCase):
    def test_scalar_and_tangent_states_agree(self):
        """T20 under K8 amendment 10: K8-2 S3 tangent-only zero-primal ledger records (non-SA) are set aside and
        counted per site; SA creates none; any other key or length difference fails."""
        out = probe('forward', 'parity')
        s3 = out['s3']
        print('T20_S3_RULE ' + json.dumps({k: s3[k] for k in ('s3_calls', 's3_calls_by_origin', 'sa_created',
                                                                'excluded_records', 'excluded_by_site',
                                                                'excluded_by_origin', 'excluded_keys')}))
        self.assertEqual(out['state_error'], 0.0)
        self.assertTrue(out['s3_rule_ok'], out['s3_rule_why'])
        self.assertTrue(s3['installed'])
        self.assertEqual(s3['sa_created'], 0)
        self.assertEqual(s3['not_excluded_count'], 0, s3['not_excluded'])
        self.assertEqual(set(s3['excluded_by_site']), {'PRB-bd:307', 'PRB-bd:332', 'PRB-bd:370', 'CAO:608',
                                                       'AFA:247', 'AFA:393'})
        self.assertEqual(sum(s3['excluded_by_site'].values()), s3['excluded_records'])
        self.assertEqual(sum(s3['excluded_by_origin'].values()), s3['excluded_records'])
        self.assertTrue(out['tie_seen'])
        self.assertTrue(out['zero_release_seen'])
        self.assertGreater(out['dual_values'], 0)


if __name__ == '__main__':
    unittest.main()
