"""K8b-2 P-4' + P-4b tests (K8_PREDECLARATION_AMENDMENT_16 r2 sections 2.3 / 2.4 and 4.1 G3 K8b-2 (a)-(f), as
corrected by AMENDMENT_17, variant A of D-K8b-4).  Synthetic W_out link only (no capture, rollout, adapter run or
VISSIM): the toy replays the lane-plant order of one second -- A = occupancy - reservations due > t ->
_wout_store_update -> _wout_requests -> body (signal arrivals with a +33 s reservation; the LOR direct row through
wout_direct_delay) -> acceptance -> _wout_store_accept -> storage adjust -> _wout_store_check -- with the installed
spec of the committed evidence (runtime_setup.install_wout_exit_law).

    PYTHONHASHSEED=0 python -B -m pytest -p no:cacheprovider diagnostics/sdmpc_n31_20260924/tests/test_k8b_p4.py -v
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
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


if __name__ == '__main__':
    unittest.main()
