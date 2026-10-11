"""K9-1-2 W2-A tests (K8_PREDECLARATION_AMENDMENT_19 r2 sections 2.2 and 4.2 G3 K9-1-2 (a)-(g); synthetic W_out link
and corridor state only -- no capture, rollout, adapter run or VISSIM; the install reads the repository network /
membership files of the deployed SC2001 corridor evidence).

  install  runtime_setup.install_wout_side_handoff: the side class (evidence shares and exit-law lengths) on the
           SC1001_W_out exit law and the one corridor branch wout_handover (path 78 -> 10703 -> 31, 2 lanes, every
           origin prior 1.0, the three NC13 branches kept as provenance); config errors.
  (a) (c)  the K8b-2 toy (tests/test_k8b_p4) with side landings through wout_side_handoff_land inside the W_out step:
           cumulative assigned side shares = the declared shares (1e-12), every step |sum X - (A - sum a)| <= 1e-9.
  (b)      after the inflow stops: cumulative side exits per destination / landed side = the declared shares (1e-9).
  (d) (e)  sc2001_corridor.advance with the wout_handover branch: the accepted mass = the X[side] increase (1e-12)
           and moves SC2001_S_out -> SC1001_W_out storage; with the W_out room 0 nothing is handed over and the
           corridor's ready stock stays.
  (f)      meter_spill.sc2001_branches does nothing for the corridor without a ramp branch (no ledger access).
  (g)      key absent: nothing installed, the three NC13 branches and the two-class law are the former path.

    PYTHONHASHSEED=0 python -B -m pytest -p no:cacheprovider diagnostics/sdmpc_n31_20260924/tests/test_k9_w2a.py -v
"""
from __future__ import annotations

import copy
import hashlib
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
from evaluation.controllers import sc2001_corridor as SCC  # noqa: E402
from evaluation.controllers import meter_spill as MS  # noqa: E402
import test_k8b_p4 as P4  # noqa: E402

LINK = P4.LINK
EVIDENCE = 'diagnostics/sdmpc_n31_20260924/k9/wout_side_handoff_v3c3_20261009.json'
EVIDENCE_SHA256 = '4683484bf3f6ac7e9a6e5f669ed40d80d3337508151d2801c22b44c01f1e37a2'     # K91_VALUES.json w2a
CORRIDOR = 'diagnostics/sdmpc_n31_20260924/scenario/sc2001_corridor_nc13_2d0c62.json'
STORE = 'SC2001_S_out'


def pin():
    return {'evidence': EVIDENCE, 'evidence_sha256': hashlib.sha256((ROOT / EVIDENCE).read_bytes()).hexdigest()}


def values():
    return json.loads((ROOT / EVIDENCE).read_text(encoding='utf-8'))['values']


def corridor_spec():
    doc = json.loads((ROOT / CORRIDOR).read_text(encoding='utf-8-sig'))
    return {'network': dict(doc['network']), 'area_source': {'path': doc['membership_path']}, 'storage': doc['storage'],
            'branches': {k: {'path': list(v['path']), 'target_kind': v['target_kind'], 'target': v.get('target')}
                         for k, v in doc['branches'].items()},
            'calibration': {'priors': copy.deepcopy(doc['calibration']['priors'])}, 'capacity_veh': 40.0, 'lanes': 2}


def tuning(key=True):
    urban = {'sc2001_corridor': CORRIDOR, 'wout_exit_law': P4.law_key()}
    if key:
        urban['wout_side_handoff'] = pin()
    return {'urban': urban}


def installed(key=True):
    cfg, st, _ = P4.make(True)
    cfg.network.sc2001_corridor = corridor_spec()
    meta = RS.install_wout_side_handoff(cfg, tuning(key))
    return cfg, st, meta


def declared(v=None):
    v = v or values()
    return {'free': v['shares']['free'], v['ramp_of']['R_D_E']: v['shares']['R_D_E'],
            v['ramp_of']['R_D_W']: v['shares']['R_D_W']}


class Toy:
    """The K8b-2 toy second (test_k8b_p4.Toy) with a side landing inside the W_out step context."""

    def __init__(self, cfg, st):
        self.cfg, self.st = cfg, st
        self.spec = cfg.network.wout_exit_law[LINK]
        self.sums, self.landed = [], 0.0
        self.side_exits = {d: 0.0 for d in self.spec['dests']}

    def arrived(self, t):
        buf = self.st.urban_storage_release_buffer[LINK]
        return max(0.0, (P4.CAP - self.st.urban_link_storage[LINK]) - sum(x for d, x in buf.items() if d > t))

    def run(self, steps, sig_in, side_in, t0=0):
        st, spec = self.st, self.spec
        for t in range(t0, t0 + steps):
            A = self.arrived(t)
            ctx = UFA._wout_store_update(st, spec, LINK, A, t)
            R = UFA._wout_requests(ctx, P4.V, P4.T_U) if A > 0.0 else None
            if R is None:
                ctx['a'] = {d: 0.0 for d in spec['dests']}
            UFA._WOUT_STEP['ctx'] = {LINK: ctx}
            buf = st.urban_storage_release_buffer[LINK]
            if sig_in:
                st.urban_link_storage[LINK] -= sig_in
                buf[t + 33] = buf.get(t + 33, 0.0) + sig_in
            if side_in:
                st.urban_link_storage[LINK] -= side_in
                UFA.wout_side_handoff_land(st, self.cfg, t, side_in)
                self.landed += side_in
            acc = []
            before = {d: ctx['X']['side'][d] for d in spec['dests']}
            if R is not None:
                acc.append((LINK, None, min(R['free'], P4.EXIT)))
                for r in ('RM_C10484', 'RM_C10480'):
                    acc.append((LINK, r, R[r]))
            UFA._wout_store_accept(st, {LINK: ctx}, acc)
            for d in spec['dests']:
                self.side_exits[d] += before[d] - ctx['X']['side'][d]
            st.urban_link_storage[LINK] += sum(x[2] for x in acc)
            UFA._wout_store_check({LINK: ctx})
            UFA._WOUT_STEP['ctx'] = None
            self.sums.append(abs(sum(x for row in ctx['X'].values() for x in row.values())
                                 - (ctx['A'] - sum(ctx['a'].values()))))
            for k in [k for k in buf if k <= t]:
                buf.pop(k)


class InstallTests(unittest.TestCase):
    def test_evidence_is_the_p0_file(self):
        self.assertEqual(pin()['evidence_sha256'], EVIDENCE_SHA256)

    def test_install_side_class_and_handover_branch(self):
        cfg, _st, meta = installed()
        v = values()
        spec = cfg.network.wout_exit_law[LINK]
        self.assertEqual(spec['classes'][-1], 'side')
        self.assertEqual(spec['s']['side'], declared(v))
        self.assertEqual(spec['l_km']['side'], {'free': v['l_km']['free'], v['ramp_of']['R_D_E']: v['l_km']['R_D_E'],
                                                v['ramp_of']['R_D_W']: v['l_km']['R_D_W']})
        self.assertEqual(spec['side_class'], 'side')
        cor = cfg.network.sc2001_corridor
        self.assertEqual(sorted(cor['branches']), ['wout_handover'])
        b = cor['branches']['wout_handover']
        self.assertEqual((b['path'], b['target_kind'], b['target'], b['lanes'], b['source_inside'], b['target_inside']),
                         (['78', '10703', '31'], 'wout', LINK, 2, True, True))
        self.assertEqual([r['link'] for r in b['travel_segments']], ['78', '10703'])
        self.assertTrue(all(r['stop_m'] >= r['start_m'] for r in b['travel_segments']))
        self.assertEqual({o: r['shares'] for o, r in cor['calibration']['priors'].items()},
                         {o: {'wout_handover': 1.0} for o in ('W', 'N', 'E_SC2002', 'initial_unknown_origin')})
        self.assertEqual(sorted(cor['wout_handover']['replaced_branches']), ['R_D_E', 'R_D_W', 'outside_125'])
        m = meta['k9_w2a']
        self.assertEqual((m['evidence_sha256'], m['link'], m['x_side_m']), (EVIDENCE_SHA256, LINK, 350.718))
        self.assertEqual(m['shares'], declared(v))
        self.assertEqual(cfg.network.wout_side_handoff, {'link': LINK, 'evidence_sha256': EVIDENCE_SHA256})

    def test_config_errors(self):
        cfg, _st, _meta = installed()
        with self.assertRaisesRegex(ValueError, 'installed twice'):
            RS.install_wout_side_handoff(cfg, tuning())
        cfg, _st, _ = P4.make(True)
        cfg.network.sc2001_corridor = corridor_spec()
        bad = tuning()
        del bad['urban']['sc2001_corridor']
        with self.assertRaisesRegex(ValueError, 'needs urban.sc2001_corridor'):
            RS.install_wout_side_handoff(cfg, bad)
        bad = tuning()
        bad['urban']['wout_side_handoff'] = dict(pin(), evidence_sha256='0' * 64)
        with self.assertRaisesRegex(ValueError, 'sha256 mismatch'):
            RS.install_wout_side_handoff(cfg, bad)
        cfg2, _st, _ = P4.make(True)
        with self.assertRaisesRegex(ValueError, 'not installed'):                  # no corridor spec in the cfg
            RS.install_wout_side_handoff(cfg2, tuning())

    def test_g_key_absent_is_the_former_path(self):
        cfg, _st, meta = installed(key=False)
        self.assertEqual(meta, {})
        self.assertEqual(sorted(cfg.network.sc2001_corridor['branches']), ['R_D_E', 'R_D_W', 'outside_125'])
        self.assertNotIn('side', cfg.network.wout_exit_law[LINK]['classes'])
        self.assertFalse(hasattr(cfg.network, 'wout_side_handoff'))
        cnt = UFA._wout_counters(_st, LINK, cfg.network.wout_exit_law[LINK])
        self.assertNotIn('side_handoff_veh', cnt)                                 # K8b-5 counter dict


class SideClassTests(unittest.TestCase):
    def test_a_c_assigned_shares_and_balance(self):
        cfg, st, _ = installed()
        toy = Toy(cfg, st)
        toy.run(900, 0.12, 0.10)
        cnt = st.wout_exit_counters[LINK]
        tot = sum(cnt[f'assigned|side|{d}'] for d in toy.spec['dests'])
        self.assertAlmostEqual(tot, toy.landed, places=9)
        for d, s in declared().items():
            self.assertLessEqual(abs(cnt[f'assigned|side|{d}'] / tot - s), 1e-12)                       # (a)
        self.assertLessEqual(max(toy.sums), 1e-9)                                                        # (c)
        self.assertAlmostEqual(cnt['side_handoff_veh'], toy.landed, places=9)
        self.assertEqual(cnt['side_handoff_band_events'], 900.0)
        self.assertEqual(cnt['shrink_veh'], 0.0)

    def test_b_exit_shares_after_inflow_stops(self):
        cfg, st, _ = installed()
        toy = Toy(cfg, st)
        toy.run(600, 0.12, 0.10)
        toy.run(4000, 0.0, 0.0, t0=600)
        self.assertLess(sum(st.wout_class_store[LINK]['side'].values()), 1e-9)
        for d, s in declared().items():
            self.assertLessEqual(abs(toy.side_exits[d] / toy.landed - s), 1e-9)                        # (b)

    def test_landing_outside_the_step_or_without_side_class(self):
        cfg, st, _ = installed()
        toy = Toy(cfg, st)
        toy.run(5, 0.12, 0.10)
        with self.assertRaises(UFA.WoutExitInvariantError):
            UFA.wout_side_handoff_land(st, cfg, 6, 0.1)                                                 # no step context
        cfg2, st2, _ = P4.make(True)
        cfg2.network.wout_side_handoff = {'link': LINK, 'evidence_sha256': 'x'}
        with self.assertRaises(UFA.WoutExitInvariantError):
            UFA.wout_side_handoff_land(st2, cfg2, 0, 0.1)


class CorridorHandoverTests(unittest.TestCase):
    def setup_corridor(self, room, ready=3.0, idx=100):
        cfg, st, _ = installed()
        net = cfg.network
        net.movement_capacity_veh_h = 1800.0
        net.urban_movements = {}
        net.urban_stopline_storage_veh = {}
        net.urban_link_storage_veh[STORE] = 40.0
        cfg.simulation.T_u_sec = 1.0
        st.urban_movement_queue = {}
        st.urban_link_storage[STORE] = 40.0 - ready
        st.urban_link_storage[LINK] = room
        st.sc2001_corridor_state = {'bins': {'W': {'wout_handover': {idx: ready}}}, 'last_step': idx - 1,
                                    'received_veh': 0.0, 'departed_veh': 0.0}
        spec = net.wout_exit_law[LINK]
        A = P4.CAP - room
        ctx = UFA._wout_store_update(st, spec, LINK, A, idx)
        ctx['a'] = {d: 0.0 for d in spec['dests']}
        return cfg, st, spec, ctx, idx

    def test_d_handover_mass_lands_in_the_side_class(self):
        cfg, st, spec, ctx, idx = self.setup_corridor(room=10.0)
        x0 = dict(ctx['X']['side'])
        UFA._WOUT_STEP['ctx'] = {LINK: ctx}
        try:
            out = SCC.advance(st, None, None, cfg, idx)
        finally:
            UFA._WOUT_STEP['ctx'] = None
        a = out['sc2001_accepted_by_branch']['wout_handover']
        self.assertEqual(a, 1.0)                                                  # min(ready 3, room 10, 2 lanes x 1800 veh/h x 1 s)
        gained = sum(ctx['X']['side'][d] - x0[d] for d in spec['dests'])
        self.assertLessEqual(abs(gained - a), 1e-12)                                                     # (d)
        self.assertEqual(st.urban_link_storage[LINK], 10.0 - a)
        self.assertEqual(st.urban_link_storage[STORE], 40.0 - 3.0 + a)
        self.assertEqual(out['sc2001_external_exit_veh'], 0.0)
        self.assertEqual(st.wout_exit_counters[LINK]['side_handoff_veh'], a)
        self.assertEqual(ctx['A'], P4.CAP - 10.0 + a)
        UFA._wout_store_check({LINK: ctx})

    def test_e_no_room_no_handover_ready_kept(self):
        cfg, st, spec, ctx, idx = self.setup_corridor(room=0.0)
        UFA._WOUT_STEP['ctx'] = {LINK: ctx}
        try:
            out = SCC.advance(st, None, None, cfg, idx)
        finally:
            UFA._WOUT_STEP['ctx'] = None
        self.assertEqual(out['sc2001_accepted_by_branch']['wout_handover'], 0.0)                         # (e)
        self.assertEqual(st.sc2001_corridor_state['bins']['W']['wout_handover'], {idx: 3.0})
        self.assertEqual(st.urban_link_storage[LINK], 0.0)
        self.assertEqual(sum(ctx['X']['side'].values()), 0.0)

    def test_f_meter_spill_has_no_row(self):
        cfg, st, _spec, _ctx, _idx = self.setup_corridor(room=10.0)
        st._control_area_ledger = types.SimpleNamespace()                          # any ledger call would raise
        spec = cfg.network.sc2001_corridor
        MS.sc2001_branches(st, spec, {'wout_handover': 3.0}, {'wout_handover': 1.0}, {'wout_handover': 1.0},
                           1800.0, 1.0 / 3600.0)                                                          # (f)
        self.assertEqual(vars(st._control_area_ledger), {})


if __name__ == '__main__':
    unittest.main()
