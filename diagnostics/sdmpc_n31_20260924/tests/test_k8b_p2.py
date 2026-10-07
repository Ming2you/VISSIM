"""K8b-3 P-2 tests (K8_PREDECLARATION_AMENDMENT_16 r2 sections 2.2 and 4.1 G3 K8b-3; toy SA states of
stopline_toy.py / test_stopline_approach.init_case, no capture, rollout, adapter run or VISSIM):
  - the non-W targets receive per step what the gate loop without P-2 gives them with the same beta_hat;
  - the pending initial W mass equals the removed seed mass (+-1e-9) and the W share leaves the +15/+105 cells;
  - the gate mass beyond the in_SC1001_W room is admitted the former way and counted (p2_room_fallback_veh);
  - the window clamp w(T) at T = 1, 899, 900, 8999, 9000;
  - the named fold site 5 counts its visits; split_arrival sends the untagged mass to the non-W targets only;
  - key absent: configure / prepare / initialize create nothing.

    PYTHONHASHSEED=0 python -B -m pytest -p no:cacheprovider diagnostics/sdmpc_n31_20260924/tests/test_k8b_p2.py -v
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for extra in (ROOT, ROOT / 'vendor/NumSim-mine', HERE):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import stopline_toy as T  # noqa: E402
from src.models import urban_queue_model as uqm  # noqa: E402
from evaluation.controllers import stopline_approach as SA  # noqa: E402
from evaluation.controllers.control_area_objective import emit_transfer, emit_input  # noqa: E402

E, S, N, IN, ONE, ONW = T.E, T.S, T.N, T.IN, T.ONE, T.ONW
EVIDENCE = 'diagnostics/sdmpc_n31_20260924/k8b/city_arrival_v3c3_20261007.json'


def evidence_view(members):
    raw = (ROOT / EVIDENCE).read_bytes()
    return SA.city_arrival_view(json.loads(raw.decode('utf-8')), hashlib.sha256(raw).hexdigest(), members)


def city_cfg(t0=1650):
    cfg, st = T.bare(t0)
    spec = cfg.network.stopline_approach
    spec['city_arrival'] = evidence_view(spec['members'])
    st.urban_inflow_transit_buffer = {}
    import test_stopline_approach as TSA
    raw = TSA.raw_state(t0, [(1, '32', 1, 100.0, 30.0, None), (2, '32', 1, 500.0, 10.0, None)])
    return cfg, st, raw


class Demand:
    def __init__(self, rate):
        self.urban_boundary = {IN: rate}


class P2Tests(unittest.TestCase):
    def test_window_clamp(self):
        self.assertEqual([SA.city_window(T_) for T_ in (1, 899, 900, 8999, 9000)], [1, 1, 1, 9, 9])
        cfg, st, raw = city_cfg()
        for T_, w in ((1, 1), (899, 1), (900, 1), (8999, 9), (9000, 9)):
            c2, s2 = copy.deepcopy(cfg), copy.deepcopy(st)
            s2.time_sec = float(T_)
            meta = SA.city_arrival_prepare(s2, c2, raw)['k8b_p2']
            self.assertEqual(meta['window'], w)
            self.assertEqual(c2.network.stopline_city_arrival['beta_hat'], c2.network.stopline_approach[
                'city_arrival']['beta_hat'][w])

    def test_prepare_betas_and_dg(self):
        cfg, st, raw = city_cfg(1650)
        tpl = {m: cfg.network.urban_movements[m]['beta'] for m in (E, S, N, ONE, ONW)}
        meta = SA.city_arrival_prepare(st, cfg, raw)['k8b_p2']
        city = cfg.network.stopline_city_arrival
        hat = cfg.network.stopline_approach['city_arrival']['beta_hat'][1]
        bw_tpl = math.fsum(tpl[m] for m in (E, S, N))
        scale = (1.0 - math.fsum(hat.values())) / (1.0 - bw_tpl)
        for m in (E, S, N):
            self.assertEqual(cfg.network.urban_movements[m]['beta'], hat[m])
        for m in (ONE, ONW):
            self.assertEqual(cfg.network.urban_movements[m]['beta'], tpl[m] * scale)
        u32 = (30.0 + 10.0) / 2.0
        D_g = cfg.network.stopline_approach['city_arrival']['D_g_m']
        self.assertEqual(meta['d_g'], max(1, int(math.ceil(D_g / (max(u32, 20.0) / 3.6)))))
        self.assertEqual(city['u32_kph'], u32)

    def test_non_w_arrivals_equal_the_gate_loop_without_p2(self):
        cfg, st, raw = city_cfg(1650)
        SA.city_arrival_prepare(st, cfg, raw)
        st.stopline_approach_state['city_arrival'] = {'pending': {}, 'gate_w': {},
                                                      'counters': {k: 0.0 for k in SA.CITY_COUNTER_KEYS}}
        routing = uqm.approach_routing(cfg)
        delay, rate = 34, 1800.0
        ref = copy.deepcopy(st)
        got, want = {ONE: [], ONW: []}, {ONE: [], ONW: []}
        for step in range(1651, 1651 + 120):
            before = {m: st.urban_movement_queue[m] for m in (ONE, ONW)}
            released = uqm._pop_buffer(st.urban_storage_release_buffer, IN, step)
            if released > 0.0:
                st.urban_link_storage[IN] += released
            uqm._pop_buffer(st.urban_arrival_buffer, IN, step)
            st.stopline_approach_state['tags'].pop(step, None)
            SA._context(st, cfg, step)
            SA.city_gate_step(st, cfg, Demand(rate), step, routing, delay, IN, emit_transfer, emit_input)
            st.stopline_approach_state['plan'] = {}
            st.stopline_approach_state['last_step'] = step
            for m in (ONE, ONW):
                got[m].append(st.urban_movement_queue[m] - before[m])
            # the gate loop without P-2 (UFA:421-443) with the same (prepared) betas
            landed = uqm._pop_buffer(ref.urban_inflow_transit_buffer, 'gate:' + IN, step)
            beta = dict(routing[IN])
            for m in (ONE, ONW):
                want[m].append(beta[m] * landed if landed > 0.0 else 0.0)
            uqm._schedule(ref.urban_inflow_transit_buffer, 'gate:' + IN, step + delay, rate * cfg.simulation.T_u_h)
        for m in (ONE, ONW):
            self.assertGreater(sum(want[m]), 0.0)
            for a, b in zip(got[m], want[m]):
                self.assertLessEqual(abs(a - b), 1e-12 * max(1.0, abs(b)))

    def test_room_fallback_and_counters(self):
        cfg, st, raw = city_cfg(1650)
        SA.city_arrival_prepare(st, cfg, raw)
        st.stopline_approach_state['city_arrival'] = {'pending': {}, 'gate_w': {},
                                                      'counters': {k: 0.0 for k in SA.CITY_COUNTER_KEYS}}
        st.urban_link_storage[IN] = 0.5                                    # almost full gate receiver
        step = 1651
        SA._context(st, cfg, step)
        st.urban_inflow_transit_buffer['gate:' + IN] = {step: 10.0}
        st.stopline_approach_state['city_arrival']['gate_w'][step] = 4.0
        routing = uqm.approach_routing(cfg)
        q0 = {m: st.urban_movement_queue[m] for m in (E, S, N)}
        SA.city_gate_step(st, cfg, Demand(0.0), step, routing, 34, IN, emit_transfer, emit_input)
        cnt = st.stopline_approach_state['city_arrival']['counters']
        self.assertAlmostEqual(cnt['p2_room_fallback_veh'], 3.5, places=12)
        self.assertAlmostEqual(cnt['p2_landed_gate_veh'], 0.5, places=12)
        self.assertAlmostEqual(sum(st.urban_movement_queue[m] - q0[m] for m in (E, S, N)), 3.5, places=12)
        self.assertAlmostEqual(st.urban_link_storage[IN], 0.0, places=12)

    def test_tiny_city_share_is_the_named_fold_site(self):
        cfg, st, raw = city_cfg(1650)
        SA.city_arrival_prepare(st, cfg, raw)
        st.stopline_approach_state['city_arrival'] = {'pending': {}, 'gate_w': {},
                                                      'counters': {k: 0.0 for k in SA.CITY_COUNTER_KEYS}}
        SA._context(st, cfg, 1651)
        routing = uqm.approach_routing(cfg)
        SA._land_city(st, cfg, 1651, {N: 5e-13}, routing, 'init:city', False)
        cnt = st.stopline_approach_state['city_arrival']['counters']
        self.assertEqual(cnt['tiny_city_moving_share_events'], 1.0)
        self.assertEqual(cnt['p2_tiny_untagged_veh'], 5e-13)
        self.assertEqual(sum(len(v) for v in st.stopline_approach_state['lanes'].values()), 0)

    def test_split_arrival_untagged_goes_to_non_w(self):
        cfg, st, raw = city_cfg(1650)
        SA.city_arrival_prepare(st, cfg, raw)
        routing = uqm.approach_routing(cfg)
        out = dict(SA.split_arrival(st, cfg, 1651, 2.0, routing[IN]))
        bw = cfg.network.stopline_city_arrival['beta_W_hat']
        beta = dict(routing[IN])
        for m in (E, S, N):
            self.assertEqual(out[m], 0.0)
        for m in (ONE, ONW):
            self.assertEqual(out[m], beta[m] / (1.0 - bw) * 2.0)
        self.assertAlmostEqual(sum(out.values()), 2.0, places=12)

    def test_initialize_pending_equals_removed_seed(self):
        import test_stopline_approach as TSA
        cfg, st, raw, mapping, seeds, queue = TSA.init_case()
        spec = cfg.network.stopline_approach
        spec['city_arrival'] = evidence_view(spec['members'])
        SA.city_arrival_prepare(st, cfg, raw)
        SA.initialize(st, cfg, raw, mapping, seeds, queue_by_lane=queue)
        arr_before = math.fsum(st.urban_arrival_buffer.get(IN, {}).values())
        meta = SA.city_arrival_initialize(st, cfg, raw, seeds)['k8b_p2_init']
        city = st.stopline_approach_state['city_arrival']
        pending = math.fsum(x for row in city['pending'].values() for x in row.values())
        removed = math.fsum(meta['removed_by_due'].values())
        self.assertAlmostEqual(pending, removed, delta=1e-9)
        self.assertGreater(pending, 0.0)
        self.assertAlmostEqual(arr_before - math.fsum(st.urban_arrival_buffer.get(IN, {}).values()), removed,
                               delta=1e-9)
        self.assertEqual(meta['seed_residual_veh'], 0.0)
        self.assertEqual(set(city['counters']), set(SA.CITY_COUNTER_KEYS))

    def test_key_absent_creates_nothing(self):
        cfg, st = T.bare(1650)
        self.assertEqual(SA.city_arrival_prepare(st, cfg, {}), {})
        self.assertFalse(hasattr(cfg.network, 'stopline_city_arrival'))
        self.assertEqual(SA.city_arrival_initialize(st, cfg, {}, {}), {})
        self.assertNotIn('city_arrival', st.stopline_approach_state)
        sec = T.section()
        SA.check_section(sec)
        sec2 = dict(sec, city_arrival={'evidence': EVIDENCE, 'evidence_sha256': '0' * 64})
        SA.check_section(sec2)
        with self.assertRaises(SA.StoplineConfigError):
            SA.check_section(dict(sec, other=1))

    def test_config_error_kind(self):
        from evaluation.controllers.runtime_setup import load_k8b_evidence
        with self.assertRaises(ValueError):
            load_k8b_evidence({'evidence': EVIDENCE, 'evidence_sha256': '0' * 64}, SA.CITY_ARRIVAL_SCHEMA, 'x')


if __name__ == '__main__':
    unittest.main()
