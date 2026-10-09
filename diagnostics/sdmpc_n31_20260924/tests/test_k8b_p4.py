"""K8b-2 P-4' + P-4b tests (K8_PREDECLARATION_AMENDMENT_16 r2 sections 2.3 / 2.4 and 4.1 G3 K8b-2 (a)-(f), as
corrected by AMENDMENT_17, variant A of D-K8b-4).  Synthetic W_out link only (no capture, rollout, adapter run or
VISSIM): the toy replays the lane-plant order of one second -- A = occupancy - reservations due > t ->
_wout_store_update -> _wout_requests -> body (signal arrivals with a +33 s reservation; the LOR direct row through
wout_direct_delay) -> acceptance -> _wout_store_accept -> storage adjust -> _wout_store_check -- with the installed
spec of the committed evidence (runtime_setup.install_wout_exit_law).

K8b-5 (K8_PREDECLARATION_AMENDMENT_18 sections 2.2, 2.3 and 3.3 U5): WoutCounterParityTests -- the five declared
cases of the W_out near-balance band counter (scalar delta 0.0, Dual delta -2**-51 = the idx 3019 pair of
TL3_2700_SAF_A1_H3_ADREF_ad_full, Dual +2**-51, a real shrink -2e-9 as float and as Dual); DirectRowParityTests --
the LOR direct row at its structural zero room (A-1, a fresh tangent-instrumented subprocess k8b5_parity_probe.py,
forward and reverse-v1).  Counter dicts "equal" means: the same keys, the visit counters (*_events, update_steps)
exactly equal, the vehicle-valued counters within the state tolerance 1e-9 (tangent_worker.state_error).

    PYTHONHASHSEED=0 python -B -m pytest -p no:cacheprovider diagnostics/sdmpc_n31_20260924/tests/test_k8b_p4.py -v
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for extra in (ROOT, ROOT / 'vendor/NumSim-mine', HERE):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from evaluation.controllers import runtime_setup as RS  # noqa: E402
from evaluation.controllers import urban_flow_accounting as UFA  # noqa: E402

LINK = 'SC1001_W_out'
EVIDENCE = 'diagnostics/sdmpc_n31_20260924/k8b/wout_exit_v3c3_20261007.json'
TPL = {'free': 0.25, 'ramps': {'RM_C10484': 0.5, 'RM_C10480': 0.25}}
CAP = 169.61
T_U = 1.0 / 3600.0
V = 60.0
EXIT = 1600.0 * T_U
ROW = {'direct': True, 'group': 'OR_D_E', 'target': LINK, 'lanes': 1, 'connector': 10483}


def law_key():
    sha = hashlib.sha256((ROOT / EVIDENCE).read_bytes()).hexdigest()
    return {LINK: {'law': 'per_destination_class_v1', 'variant': 'A', 'evidence': EVIDENCE, 'evidence_sha256': sha}}


def make(law=True):
    net = types.SimpleNamespace(boundary_out_ramp_split={LINK: json.loads(json.dumps(TPL))},
                                leg_ramp_split_enabled=True, leg_ramp_split_wout_speed_kmh=V,
                                offramp_direct_tail_by_offramp={'OR_D_E': LINK},
                                urban_link_storage_veh={LINK: CAP})
    cfg = types.SimpleNamespace(network=net, simulation=types.SimpleNamespace(T_u_h=T_U))
    meta = RS.install_wout_exit_law(cfg, {'urban': {'wout_exit_law': law_key()}} if law else {'urban': {}})
    state = types.SimpleNamespace(urban_storage_release_buffer={LINK: {}}, urban_link_storage={LINK: CAP})
    return cfg, state, meta


class Toy:
    def __init__(self, cfg, state):
        self.cfg, self.state = cfg, state
        self.spec = cfg.network.wout_exit_law[LINK]
        self.exits = {}
        self.sums = []
        self.direct_delays = []

    def occ(self):
        return CAP - self.state.urban_link_storage[LINK]

    def arrived(self, t):
        buf = self.state.urban_storage_release_buffer[LINK]
        return max(0.0, self.occ() - sum(x for d, x in buf.items() if d > t))

    def run(self, steps, sig_in, dir_in, t0=0, cap_zero=None):
        st, cfg = self.state, self.cfg
        for t in range(t0, t0 + steps):
            A = self.arrived(t)
            ctx = UFA._wout_store_update(st, self.spec, LINK, A, t)
            R = None
            if A > 0.0:
                R = UFA._wout_requests(ctx, V, T_U)
            else:
                ctx['a'] = {d: 0.0 for d in self.spec['dests']}
            buf = st.urban_storage_release_buffer[LINK]
            if sig_in:
                st.urban_link_storage[LINK] -= sig_in
                buf[t + 33] = buf.get(t + 33, 0.0) + sig_in
            if dir_in:
                st.urban_link_storage[LINK] -= dir_in
                d = UFA.wout_direct_delay(st, cfg, t, '10483', ROW, LINK, dir_in)
                self.direct_delays.append(d)
                buf[t + d] = buf.get(t + d, 0.0) + dir_in
            acc = []
            if R is not None:
                acc.append((LINK, None, min(R['free'], EXIT)))
                for r in ('RM_C10484', 'RM_C10480'):
                    acc.append((LINK, r, 0.0 if r == cap_zero else R[r]))
            before = {c: dict(row) for c, row in ctx['X'].items()}
            UFA._wout_store_accept(st, {LINK: ctx}, acc)
            for c, row in ctx['X'].items():
                for d, x in row.items():
                    self.exits[c + '|' + d] = self.exits.get(c + '|' + d, 0.0) + (before[c][d] - x)
            st.urban_link_storage[LINK] += sum(x[2] for x in acc)
            UFA._wout_store_check({LINK: ctx})
            self.sums.append(abs(sum(x for row in ctx['X'].values() for x in row.values())
                                 - (A - sum(ctx['a'].values()))))
            for k in [k for k in buf if k <= t]:
                buf.pop(k)


class P4Tests(unittest.TestCase):
    def test_install_variant_a_values(self):
        cfg, _st, meta = make()
        spec = cfg.network.wout_exit_law[LINK]
        self.assertEqual(spec['dests'], ('free', 'RM_C10484', 'RM_C10480'))
        self.assertEqual(spec['s']['signal'], {'free': 0.1672316384180791, 'RM_C10484': 0.5114877589453861,
                                               'RM_C10480': 0.32128060263653485})
        self.assertEqual(spec['s']['direct'], {'free': 1.0, 'RM_C10484': 0.0, 'RM_C10480': 0.0})
        self.assertEqual(spec['l_km']['signal'], {'RM_C10484': 0.412, 'RM_C10480': 0.735, 'free': 0.735})
        self.assertEqual(spec['l_km']['direct'], {'RM_C10484': None, 'RM_C10480': 0.0, 'free': 0.0})
        self.assertEqual(spec['direct'], {'off': '10483', 'group': 'OR_D_E', 'l_residence_km': 0.121533})
        self.assertEqual(meta['k8b_p4'][LINK]['variant'], 'A')

    def test_a_c_e_assigned_shares_invariant_and_direct_class(self):
        cfg, st, _ = make()
        toy = Toy(cfg, st)
        toy.run(600, 0.12, 0.30)
        spec = toy.spec
        cnt = st.wout_exit_counters[LINK]
        for c in spec['classes']:
            tot = sum(cnt[f'assigned|{c}|{d}'] for d in spec['dests'])
            self.assertGreater(tot, 0.0)
            for d in spec['dests']:
                self.assertLessEqual(abs(cnt[f'assigned|{c}|{d}'] / tot - spec['s'][c][d]), 1e-12)      # (a)
        self.assertLessEqual(max(toy.sums), 1e-9)                                                        # (c)
        self.assertEqual(set(toy.direct_delays), {8})                                                     # (e)
        released = cnt['direct_release_veh']
        self.assertAlmostEqual(released, 600 * 0.30, places=9)
        self.assertAlmostEqual(cnt['direct_matured_veh'], (600 - 8) * 0.30, places=9)                      # (e)
        self.assertAlmostEqual(sum(cnt[f'assigned|direct|{d}'] for d in spec['dests']), (600 - 8) * 0.30, places=9)
        self.assertEqual(cnt['shrink_veh'], 0.0)

    def test_b_exit_shares_after_inflow_stops(self):
        cfg, st, _ = make()
        toy = Toy(cfg, st)
        toy.run(600, 0.12, 0.30)
        toy.run(4000, 0.0, 0.0, t0=600)
        spec = toy.spec
        cnt = st.wout_exit_counters[LINK]
        for c in spec['classes']:
            tot = sum(cnt[f'assigned|{c}|{d}'] for d in spec['dests'])
            for d in spec['dests']:
                self.assertLessEqual(abs(toy.exits[c + '|' + d] / tot - spec['s'][c][d]), 1e-9)          # (b)
                self.assertAlmostEqual(cnt[f'exited|{c}|{d}'], toy.exits[c + '|' + d], places=9)
        self.assertLess(toy.occ(), 1e-9)

    def test_d_closed_ramp_grows_only_its_store(self):
        cfg, st, _ = make()
        toy = Toy(cfg, st)
        toy.run(300, 0.12, 0.30)
        x0 = {c: dict(r) for c, r in st.wout_class_store[LINK].items()}
        toy.run(300, 0.12, 0.30, t0=300, cap_zero='RM_C10480')
        x1 = st.wout_class_store[LINK]
        self.assertGreater(sum(x1[c]['RM_C10480'] - x0[c]['RM_C10480'] for c in x1), 1.0)
        for c in x1:
            for d in ('free', 'RM_C10484'):
                self.assertLess(abs(x1[c][d] - x0[c][d]), 1.0)                                          # (d)

    def test_f_key_absent_is_the_former_law(self):
        cfg, st, meta = make(law=False)
        self.assertEqual(meta, {})
        self.assertFalse(hasattr(cfg.network, 'wout_exit_law'))
        self.assertIsNone(UFA.wout_direct_delay(st, cfg, 10, '10483', ROW, LINK, 0.3))
        for name in ('wout_class_store', 'wout_direct_pending', 'wout_exit_counters'):
            self.assertFalse(hasattr(st, name))
        cfg2, st2, _ = make()
        other = dict(ROW, target='SC1004_W_out')
        self.assertIsNone(UFA.wout_direct_delay(st2, cfg2, 10, '10682', other, 'SC1004_W_out', 0.3))

    def test_invariant_violations_raise_the_declared_kind(self):
        cfg, st, _ = make()
        bad = dict(ROW, group='OR_D_W')
        with self.assertRaises(UFA.WoutExitInvariantError):
            UFA.wout_direct_delay(st, cfg, 10, '10483', bad, LINK, 0.3)
        toy = Toy(cfg, st)
        toy.run(20, 0.12, 0.30)
        ctx = UFA._wout_store_update(st, toy.spec, LINK, toy.arrived(20), 20)
        UFA._wout_requests(ctx, V, T_U)
        UFA._wout_store_accept(st, {LINK: ctx}, [(LINK, None, 0.0)])
        ctx['X']['signal']['free'] += 1.0                                       # break the store identity
        with self.assertRaises(UFA.WoutExitInvariantError):
            UFA._wout_store_check({LINK: ctx})

    def test_config_errors(self):
        key = law_key()
        key[LINK]['variant'] = 'C'
        net = types.SimpleNamespace(boundary_out_ramp_split={LINK: json.loads(json.dumps(TPL))},
                                    leg_ramp_split_enabled=True, offramp_direct_tail_by_offramp={'OR_D_E': LINK})
        cfg = types.SimpleNamespace(network=net, simulation=types.SimpleNamespace(T_u_h=T_U))
        with self.assertRaisesRegex(ValueError, 'variant'):
            RS.install_wout_exit_law(cfg, {'urban': {'wout_exit_law': key}})
        key = law_key()
        key[LINK]['evidence_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'sha256 mismatch'):
            RS.install_wout_exit_law(cfg, {'urban': {'wout_exit_law': key}})
        net.boundary_out_ramp_split[LINK]['ramps'] = {'R_D_E': 0.5, 'R_D_W': 0.25}
        with self.assertRaisesRegex(ValueError, 'runtime ramps'):
            RS.install_wout_exit_law(cfg, {'urban': {'wout_exit_law': law_key()}})

    def test_make_config_apply_k8b_p4(self):
        path = ROOT / 'diagnostics/sdmpc_n31_20260924/make_config_n31.py'
        spec = importlib.util.spec_from_file_location('k8b_test_make_config_p4', path)
        mc = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(path.parent))
        try:
            spec.loader.exec_module(mc)
        finally:
            sys.path.remove(str(path.parent))
        doc = {'urban': {'stopline_approach': {'storage': 'observed_full'}}}
        out = mc.apply_k8b(doc, ROOT, parts=('p4',))
        self.assertEqual(out['urban']['wout_exit_law'], law_key())


# ---------------------------------------------------------------- K8b-5 (AMENDMENT_18)
A3019 = 2.1030714198204103          # idx 3019 of TL3_2700_SAF_A1_H3_ADREF_ad_full: arrived = scalar sum X (POST_DIAG 3.1)
TOT3019 = 2.103071419820411         # the tangent run's sum X there (one ulp larger)
PROBE = HERE / 'k8b5_parity_probe.py'
NUMBA_DEPS = Path(os.environ.get('K8G_DEPS', r'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps'))


def _p(x):
    return getattr(x, '_validation_primal', x)


def dual(v):
    from evaluation.controllers import sdmpc_dual as ad
    return ad.Dual(v, {0: 1.0}, ad.Trace([1.0]))


def band_case(arrived, tot_store):
    """I0 call, then sum X = tot_store in the i0 class / free store, then one update with `arrived` (dc_unit_demo)."""
    cfg, state, _ = make()
    spec = cfg.network.wout_exit_law[LINK]
    UFA._wout_store_update(state, spec, LINK, 1.0, 0)
    X = state.wout_class_store[LINK]
    for c in spec['classes']:
        for d in spec['dests']:
            X[c][d] = 0.0
    X[spec['i0_class']]['free'] = tot_store
    x0 = {c: dict(row) for c, row in X.items()}
    before = dict(state.wout_exit_counters[LINK])
    UFA._wout_store_update(state, spec, LINK, arrived, 1)
    after = state.wout_exit_counters[LINK]
    return state, spec, x0, {k: _p(after[k]) - _p(before.get(k, 0.0)) for k in after}


def declared_x(spec, x0, arrived, tot):
    """Section 2.2-4: delta = A - sum X; delta > 0 adds s_d delta to the i0 class, delta < 0 scales by A / sum X."""
    delta = arrived - tot
    pd = _p(delta)
    out = {c: dict(row) for c, row in x0.items()}
    if pd > 0.0:
        c0 = spec['i0_class']
        for d in spec['dests']:
            out[c0][d] = x0[c0][d] + spec['s'][c0][d] * delta
    elif pd < 0.0:
        ratio = arrived / tot
        for c in spec['classes']:
            for d in spec['dests']:
                out[c][d] = x0[c][d] * ratio
    return out


def counters_equal(test, a, b):
    test.assertEqual(set(a), set(b))
    for k in a:
        if k.endswith('_events') or k == 'update_steps':
            test.assertEqual(_p(a[k]), _p(b[k]), k)
        else:
            test.assertLessEqual(abs(_p(a[k]) - _p(b[k])), 1e-9, k)


def state_error(a, b):
    from evaluation.controllers.sdmpc_tangent_worker import state_error as err
    return err(a, b, 'state')


class WoutCounterParityTests(unittest.TestCase):
    """AMENDMENT_18 section 3.3 U5-1 (POST_DIAG section 3.3-1 cases)."""
    CASES = (('scalar_delta_0', lambda: A3019, A3019, 1.0, 0.0, 0.0),
             ('dual_delta_minus_ulp', lambda: dual(A3019), TOT3019, 1.0, 0.0, 0.0),
             ('dual_delta_plus_ulp', lambda: dual(TOT3019), A3019, 1.0, 0.0, 0.0),
             ('float_shrink_2e-9', lambda: A3019 - 2e-9, A3019, 0.0, 1.0, abs((A3019 - 2e-9) - A3019)),
             ('dual_shrink_2e-9', lambda: dual(A3019 - 2e-9), A3019, 0.0, 1.0, abs((A3019 - 2e-9) - A3019)))

    def test_declared_counts_and_store_arithmetic(self):
        self.assertEqual(TOT3019 - A3019, 2.0 ** -51)
        for name, arr, tot, near, shrink_n, shrink_v in self.CASES:
            with self.subTest(case=name):
                arrived = arr()
                state, spec, x0, dc = band_case(arrived, tot)
                self.assertEqual(dc['near_balance_events'], near)
                self.assertEqual(dc['shrink_events'], shrink_n)
                self.assertEqual(dc['shrink_veh'], shrink_v)
                self.assertNotIn('shrink_tiny_events', dc)
                if shrink_n:
                    self.assertAlmostEqual(shrink_v, 2e-9, delta=1e-15)
                want = declared_x(spec, x0, arrived, tot)
                X = state.wout_class_store[LINK]
                for c in spec['classes']:
                    for d in spec['dests']:
                        self.assertEqual(_p(X[c][d]), _p(want[c][d]), f'{c}|{d}')

    def test_scalar_and_dual_ulp_runs_agree(self):
        s_state, _spec, _x0, _dc = band_case(A3019, A3019)
        for arr, tot in ((dual(A3019), TOT3019), (dual(TOT3019), A3019)):
            with self.subTest(tot=tot):
                t_state, _s, _x, _d = band_case(arr, tot)
                counters_equal(self, s_state.wout_exit_counters[LINK], t_state.wout_exit_counters[LINK])
                self.assertLessEqual(state_error(s_state, t_state), 1e-9)


def probe(backend, scenario, root=None):
    env = dict(os.environ, PYTHONHASHSEED='0', NUMBA_NUM_THREADS='1', OMP_NUM_THREADS='1')
    if backend == 'reverse-v1':
        env['PYTHONPATH'] = os.pathsep.join([str(NUMBA_DEPS / 'sdmpc'), str(NUMBA_DEPS / 'sdmpc-numba'),
                                             env.get('PYTHONPATH', '')])
    args = [sys.executable, '-B', str(PROBE), backend, scenario] + ([str(root)] if root else [])
    done = subprocess.run(args, cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=900)
    if done.returncode != 0:
        raise AssertionError(done.stdout[-4000:] + done.stderr[-4000:])
    return json.loads(done.stdout.strip().splitlines()[-1])


class DirectRowParityTests(unittest.TestCase):
    """AMENDMENT_18 section 2.3.2 A-1 / 2.3.4 F-1 + F-2: the direct-row pending key and the band counters agree when
    the scalar witness has n = 0.0 (W_out room exactly 0) and the tangent run n = O(2**-51)."""

    def check(self, backend):
        out = probe(backend, 'direct_row')
        self.assertEqual(out['n_scalar'], 0.0)
        self.assertGreater(out['n_tangent'], 0.0)
        self.assertLessEqual(out['n_tangent'], 1e-9)
        self.assertEqual(out['pend_keys_after_drain'][0], out['pend_keys_after_drain'][1])
        self.assertTrue(out['events_equal'], out)
        self.assertTrue(out['parity'], out)
        for name in ('direct_release_band_events', 'direct_matured_band_events', 'near_balance_events'):
            self.assertIn(name, out['counters_scalar'])
        for name in ('direct_release_events', 'direct_matured_events', 'shrink_tiny_events'):
            self.assertNotIn(name, out['counters_scalar'])
        exc = out['full_state_report_only']['exception'] or ''
        self.assertNotIn('wout_', exc)            # a whole-state difference, if any, lies outside the K8b containers

    def test_forward(self):
        self.check('forward')

    def test_reverse_v1(self):
        self.check('reverse-v1')


if __name__ == '__main__':
    unittest.main()
