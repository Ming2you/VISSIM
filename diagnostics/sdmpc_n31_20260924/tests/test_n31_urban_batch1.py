"""Urban plant batch 1 (U1 routing beta, U2 route queue attribution, U3 unsignalized turns), 2026-09-25.

Every new switch is a config key; with the keys absent the adapter must behave exactly as before (the full-decision
bit identity is proven by replaying the logged v3b no-control decisions, see the batch report). These tests pin:
  - the three generators rebuild their pinned files byte for byte (reproducibility);
  - routing_v3b2 covers every runtime movement, each approach sums to 1, and the physical-path rules hold on the
    interchange approaches; a boundary exit follows the physical out-link table (SC104 10171 -> E, review
    2026-09-26); the runtime guards refuse a moved or renormalised share only for the complete source, decided by
    the adapter's own predicate; the table is pinned (urban.beta.sha256), installed only with the declaration and
    phase authority it was derived with, and checked against the snapshot network, the runtime flowless phases and
    flow in a phase without native green;
  - the v3b declaration (user decision 2026-09-26): SC7_E(_SC16)_to_N_SC11 exist (10332, relFlow 63 / 147 = 0.429,
    S_SC108 0.571), are served in the phase of their head 140101 (SC7 SG 1 = p4) and nothing else changes phase;
    the departing one has its area route; the derivation has no exception list and refuses any declaration that
    disagrees with the physics; without the key the legacy declaration is read unchanged; the rows record (review
    2026-09-26) the shared stop-line lane -- whose capacity the model does not split by beta -- and the crossed midblock
    SC7 SG 16, and urban.movements.dead_phase_beta_zero is refused with the complete source;
  - urban.queue.attribution "route" needs its pinned evidence and attributes by route, route end, then lane, then
    beta; diverging routes go to storage; never to an off_ramp movement; zero-beta crossings and foreign-lane
    unsignalized crossings fall to the lane rule;
  - urban.movements.unsignalized_evidence sets the flag only for its pinned movements, every green-fraction
    path returns 1 for them, and they leave the head lane-group capacity split;
  - the dead queue origin filter is gone; the offramp direct share is explicit in the default config and a present
    key must name both interchanges;
  - the batch-1 candidate config is a separate file that adds exactly the batch-1 keys (subsets by --components).
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import json
import math
import sys
import tempfile
import types
import unittest
from pathlib import Path

import n31_fixtures as fx
import make_config_n31 as mc
from evaluation.controllers import beta_source
from evaluation.controllers import vissim_stackelberg_adapter as ad

ROOT = fx.ROOT


def _load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _args(module, **over):
    values = dict(module.DEFAULTS)
    values['generated'] = '2026-09-25'
    values.update(over)
    return types.SimpleNamespace(**values)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def runtime_movements():
    base = json.loads((ROOT / mc.BASE).read_text(encoding='utf-8-sig'))
    return base['config_overrides']['network']['urban_movements']


def cfg_with(movements):
    return types.SimpleNamespace(network=types.SimpleNamespace(urban_movements=copy.deepcopy(movements)))


DECLARED = {'merge_exits': True, 'phase_correction': True, 'physical_phase_authority': mc.URBAN_B1_PHASE_AUTHORITY,
            'nonexistent_declaration': {'path': mc.URBAN_B1_DECLARATION, 'sha256': mc.URBAN_B1_DECLARATION_SHA256}}
COMPLETE = {'urban': {'beta': {'measured': True, 'floor': 0.0, 'source': 'routing_v3b2', 'sha256': mc.URBAN_B1_BETA_SHA256},
                      'movements': dict(DECLARED)}}
DEFAULT = {'urban': {'beta': {'measured': True, 'floor': 0.0, 'source': 'routing_v3b'}}}
PLAN_SWITCHES = {'urban': {'plan': {'mainline_only': True, 'actuation_plan_json':
                 'diagnostics/controller_confidence_20260913/local_native_clock_v2/native_clock_plan_local.json'}}}


@contextlib.contextmanager
def switches(tuning):
    """install_config_switches(tuning) for the block, then restore the adapter's module switches."""
    saved = (dict(ad._CFG_SWITCHES), dict(ad._CFG_STRINGS), dict(ad._ROUTE_ATTRIBUTION), set(ad._CFG_MISSING))
    try:
        ad.install_config_switches(tuning)
        yield
    finally:
        for target, value in zip((ad._CFG_SWITCHES, ad._CFG_STRINGS, ad._ROUTE_ATTRIBUTION, ad._CFG_MISSING), saved):
            target.clear()
            target.update(value)


def complete_with(**movements):
    tuning = copy.deepcopy(COMPLETE)
    tuning['urban']['movements'].update(movements)
    return tuning


def runtime_phase_cfg(doc):
    """The complete table installed on the derivation's runtime phases, without the movements the exit merge drops
    (own-leg U-turns): the phase view check_complete_beta_runtime sees after configure_runtime's phase steps."""
    cfg = cfg_with(runtime_movements())
    ad.install_measured_turn_beta(cfg, COMPLETE)
    specs = cfg.network.urban_movements
    for m, row in doc['runtime_phases']['changed'].items():
        specs[m]['phase'] = row['runtime']
    for m in [m for m, why in doc['reason'].items() if why == 'own_leg_u_turn']:
        specs.pop(m)
    return cfg


class GeneratorReproductionTests(unittest.TestCase):

    def test_routing_beta_physical_rebuilds_the_pin(self):
        g = _load_script('derive_routing_beta_physical')
        doc, _sums = g.derive(_args(g))
        self.assertEqual(sha(g.dumps(doc)), mc.URBAN_B1_BETA_SHA256)
        self.assertEqual(sha((ROOT / mc.URBAN_B1_BETA_FILE).read_bytes()), mc.URBAN_B1_BETA_SHA256)

    def test_unsignalized_turns_rebuild_the_pin(self):
        g = _load_script('derive_unsignalized_turns')
        self.assertEqual(sha(g.dumps(g.derive(_args(g)))), mc.URBAN_B1_UNSIGNALIZED_SHA256)

    def test_route_queue_attribution_rebuilds_the_pin(self):
        g = _load_script('derive_route_queue_attribution')
        self.assertEqual(sha(g.dumps(g.derive(_args(g)))), mc.URBAN_B1_ROUTE_EVIDENCE_SHA256)

    def test_phase_authority_rebuilds_the_pin(self):
        g = _load_script('derive_phase_authority_v3b')
        self.assertEqual(sha(g.dumps(g.derive(_args(g, generated='2026-09-26')))), mc.URBAN_B1_PHASE_AUTHORITY_SHA256)

    def test_area_routes_rebuild_the_pin(self):
        g = _load_script('derive_area_routes_v3b')
        doc, record = g.derive(_args(g, generated='2026-09-26'))
        self.assertEqual(sha(g.dumps(doc)), mc.URBAN_B1_AREA_ROUTES_SHA256)
        self.assertEqual(sha(g.dumps(record)), mc.URBAN_B1_AREA_ROUTES_PROVENANCE_SHA256)

    def test_batch1_pins(self):
        mc.check_urban_batch1(ROOT)


class RoutingBetaPhysicalTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.doc = load(mc.URBAN_B1_BETA_FILE)
        cls.um = runtime_movements()
        cls.beta = cls.doc['beta']

    def test_covers_every_runtime_movement_and_sums_to_one(self):
        self.assertEqual(set(self.beta), set(self.um))
        self.assertEqual(len(self.beta), 492)
        sums = {}
        for m, spec in self.um.items():
            key = (spec['signal'], spec['approach'])
            sums[key] = sums.get(key, 0.0) + self.beta[m]
        self.assertEqual(len(sums), 123)
        self.assertLessEqual(max(abs(v - 1.0) for v in sums.values()), 1e-12)
        self.assertTrue(all(v >= 0.0 for v in self.beta.values()))

    def test_no_physical_path_is_zero(self):
        b, r = self.beta, self.doc['reason']
        # on-ramp movements that reach their ramp only through W_out (31 / 68): 14
        onramp = [m for m, why in r.items() if why == 'onramp_via_boundary_out']
        self.assertEqual(sorted(onramp), sorted(
            ['SC1001_%s_to_%s' % (a, e) for a in ('E_SC1002', 'N_SC2002', 'S_SC1003') for e in ('onE', 'onW')]
            + ['SC1004_%s_to_%s' % (a, e) for a in ('E_SC1005', 'E_SC107', 'N_SC1003', 'S') for e in ('onE', 'onW')]))
        # SC1004 *_to_E_SC107 use E_SC1005's connector: folded into E_SC1005 like route_choice_corridor does
        for a in ('W', 'offW', 'offE', 'N_SC1003', 'S'):
            self.assertEqual(r['SC1004_%s_to_E_SC107' % a], 'corridor_fold_into:SC1004_%s_to_E_SC1005' % a)
        for m in ('SC1001_offW_to_W', 'SC1001_offE_to_W', 'SC1004_offW_to_W', 'SC1004_offE_to_W',
                  'SC1004_E_SC1005_to_E_SC107', 'SC1004_E_SC107_to_E_SC1005'):
            self.assertEqual(r[m], 'no_physical_path', m)
        # declared nonexistent by the runtime's own list and without a physical path (no disagreement recorded)
        self.assertEqual(r['SC109_N_SC16_to_W_SC108'], 'declared_nonexistent')
        for m, why in r.items():
            if why != 'relflow' and not why.startswith(('no_route_evidence', 'starvation_guard')):
                self.assertEqual(b[m], 0.0, m)

    def test_interchange_approaches(self):
        b = self.beta
        # SC1001 W gate 1136 6:1:2 (onW / stop line / onE), the stop-line third split by 1117 7104:2065:707
        self.assertAlmostEqual(b['SC1001_W_to_onW'], 6 / 9, places=12)
        self.assertAlmostEqual(b['SC1001_W_to_onE'], 2 / 9, places=12)
        self.assertAlmostEqual(b['SC1001_W_to_E_SC1002'], 1 / 9 * 7104 / 9876, places=12)
        # off-ramp approaches re-routed by 1117; no path to W_out
        self.assertAlmostEqual(b['SC1001_offW_to_E_SC1002'], 7104 / 9876, places=12)
        self.assertEqual(b['SC1001_offW_to_W'], 0.0)
        # SC1004 N_SC1003 1125 relFlow 6:1:1 = 68 (W) : 67 (S) : 56 (E_SC1005)
        self.assertAlmostEqual(b['SC1004_N_SC1003_to_W'], 0.75, places=12)
        self.assertAlmostEqual(b['SC1004_N_SC1003_to_S'], 0.125, places=12)
        self.assertAlmostEqual(b['SC1004_N_SC1003_to_E_SC1005'], 0.125, places=12)
        # link 40 1119 1:1:1
        for e in ('W', 'N_SC2002', 'E_SC1002'):
            self.assertAlmostEqual(b['SC1001_S_SC1003_to_' + e], 1 / 3, places=12)
        # SC1004 W gate 1134: 10644 (folded on-ramp) and 10636 (underpass) are not its movements
        self.assertAlmostEqual(b['SC1004_W_to_onE'], 0.75, places=12)
        self.assertEqual(b['SC1004_W_to_onW'], 0.0)
        # native input 1083 on link 21: one connector 10112 -> SC109
        self.assertEqual(b['SC108_W_to_E_SC109'], 1.0)
        # a single-route catch-all decision is not evidence next to a multi-route one (SC103 N: 1096 under 1091)
        for e in ('E', 'S_SC6', 'W_SC102'):
            self.assertAlmostEqual(b['SC103_N_to_' + e], 1 / 3, places=12)

    def test_sc7_declaration_corrected_to_relflow(self):
        # user decision 2026-09-26: 10332 (252:3, relFlow 63) is the right turn to SC11, 10333 (252:1, 84) the left
        for app in ('E', 'E_SC16'):
            self.assertEqual(self.beta['SC7_%s_to_N_SC11' % app], 63 / 147)
            self.assertEqual(self.beta['SC7_%s_to_S_SC108' % app], 84 / 147)
            self.assertEqual(self.doc['reason']['SC7_%s_to_N_SC11' % app], 'relflow')
            rec = next(r for r in self.doc['approaches'] if (r['signal'], r['approach']) == ('SC7', app))
            self.assertEqual((rec['connectors'], rec['matched'], rec['unmatched']), ({'10332': 63.0, '10333': 84.0}, 147.0, {}))
        self.assertNotIn('declared_nonexistent_but_physical', self.doc)
        self.assertEqual(self.doc['declared_nonexistent'], ['SC109_N_SC16_to_W_SC108'])
        self.assertEqual(self.doc['unmatched_route_weight'], 0.0)
        rows = {d['movement']: d for d in self.doc['corrected_declarations']}
        self.assertEqual(set(rows), {'SC7_E_to_N_SC11', 'SC7_E_SC16_to_N_SC11'})
        for d in rows.values():
            self.assertEqual((d['physical_connectors'], d['route_weight'], d['declared_phase'], d['runtime_phase']),
                             (['10332'], 63.0, 'SC7_p3', 'SC7_p4'))
        # the starvation guard and the flowless phases use the runtime phases: SC7_p3 keeps no runtime movement
        self.assertEqual(self.doc['phases_without_flow'], ['SC109_p1'])
        self.assertEqual(self.doc['starvation_guard'], [])
        changed = self.doc['runtime_phases']['changed']
        self.assertEqual({m: r['by'] for m, r in changed.items() if m.startswith('SC7_')},
                         {'SC7_E_to_N_SC11': 'phase_authority:SC7_E_to_N_SC11',
                          'SC7_E_SC16_to_N_SC11': 'phase_authority:SC7_E_SC16_to_N_SC11'})
        self.assertEqual(self.doc['inputs']['nonexistent_declaration'],
                         {'path': mc.URBAN_B1_DECLARATION, 'sha256': mc.URBAN_B1_DECLARATION_SHA256})
        self.assertEqual(self.doc['inputs']['phase_authority'],
                         {'path': mc.URBAN_B1_PHASE_AUTHORITY, 'sha256': mc.URBAN_B1_PHASE_AUTHORITY_SHA256})
        g = _load_script('derive_routing_beta_physical')
        self.assertFalse(hasattr(g, 'DECLARED_NONEXISTENT_PENDING'))     # no exception list any more

    def test_derivation_refuses_a_declaration_that_disagrees_with_the_physics(self):
        g = _load_script('derive_routing_beta_physical')
        decl = load(mc.URBAN_B1_DECLARATION)
        with tempfile.TemporaryDirectory() as tmp:
            # the old v2 reading: SC7 E -> N_SC11 declared nonexistent although 10332 reaches it
            old = copy.deepcopy(decl)
            for m in list(old['corrected']):
                old['known_nonexistent_movements'][m] = old['corrected'].pop(m)['was']
            path = Path(tmp) / 'old.json'
            path.write_text(json.dumps(old), encoding='utf-8')
            with self.assertRaisesRegex(SystemExit, 'SC7_E_SC16_to_N_SC11'):
                g.derive(_args(g, nonexistent_declaration=str(path)))
            # SC109 N_SC16 -> W_SC108 has no physical path: 'correcting' it fails as well
            wrong = copy.deepcopy(decl)
            wrong['corrected']['SC109_N_SC16_to_W_SC108'] = {'physical_path': ['1210009402', '10283', '1220000803']}
            wrong['known_nonexistent_movements'].pop('SC109_N_SC16_to_W_SC108')
            path = Path(tmp) / 'wrong.json'
            path.write_text(json.dumps(wrong), encoding='utf-8')
            with self.assertRaisesRegex(SystemExit, 'SC109_N_SC16_to_W_SC108'):
                g.derive(_args(g, nonexistent_declaration=str(path)))
        # corrected movements whose phase the authority does not move (the default evidence): refused
        with self.assertRaisesRegex(SystemExit, 'corrected declaration SC7_E_SC16_to_N_SC11'):
            g.derive(_args(g, phase_authority=mc.URBAN_B1_PHASE_AUTHORITY_BASE))

    def test_boundary_exit_follows_the_out_link_table(self):
        # review 2026-09-26: 10171 -> 65 (heads N) -> 10092 -> 1220061100 is SC104's E out link, not N
        rec = next(r for r in self.doc['approaches'] if (r['signal'], r['approach']) == ('SC104', 'S_SC106'))
        self.assertEqual(rec['physical_connectors'], {'SC104_S_SC106_to_N': ['10167'], 'SC104_S_SC106_to_W_SC6': ['10170'],
                                                      'SC104_S_SC106_to_E': ['10171']})
        # no static route crosses the stop line: the config default of every physical movement (0.5 / 0.25 / 0.25)
        self.assertEqual(rec['beta'], {'SC104_S_SC106_to_N': 0.5, 'SC104_S_SC106_to_W_SC6': 0.25, 'SC104_S_SC106_to_E': 0.25})
        self.assertEqual(set(rec['reason'].values()), {'no_route_evidence_config_default'})
        self.assertEqual(self.doc['boundary_exits_decided_by_out_link_table'], [
            {'signal': 'SC104', 'connector': '10171', 'headings': ['N', 'E'], 'heading_rule': 'SC104_N_out',
             'out_link_table': 'SC104_E_out', 'terminal': '1220061100'}])
        ev = load(mc.URBAN_B1_ROUTE_EVIDENCE)
        self.assertEqual(ev['anchors']['1220002001']['10171']['movements'], {'SC104|S_SC106': 'SC104_S_SC106_to_E'})

    def test_one_out_link_one_out_movement(self):
        g = _load_script('derive_routing_beta_physical')
        doc, _ = g.derive(_args(g))
        # every boundary out link reached by the stop-line connectors of a signal names one out movement (the
        # derivation refuses otherwise); SC104 1220061100 is reached from N (10099), W_SC6 (10102) and S_SC106 (10171)
        by = {}
        for rec in doc['approaches']:
            for m, cs in rec['physical_connectors'].items():
                for c in cs:
                    by.setdefault(c, set()).add(self.um[m]['receiving_link'])
        self.assertEqual(by['10171'], {'SC104_E_out'})
        self.assertEqual(by['10099'], {'SC104_E_out'})

    def test_install_complete_source(self):
        cfg = cfg_with(self.um)
        meta = ad.install_measured_turn_beta(cfg, COMPLETE)
        self.assertEqual(meta['measured_beta_complete'], 1.0)
        self.assertEqual(meta['measured_beta_movements'], 492.0)
        self.assertEqual({m: s['beta'] for m, s in cfg.network.urban_movements.items()}, self.beta)
        missing = copy.deepcopy(self.um)
        missing.pop('SC1001_W_to_onW')
        with self.assertRaisesRegex(ValueError, 'differ|different|다르다'):
            ad.install_measured_turn_beta(cfg_with(missing), COMPLETE)
        with self.assertRaisesRegex(ValueError, 'floor'):
            ad.install_measured_turn_beta(cfg_with(self.um), {'urban': {'beta': dict(COMPLETE['urban']['beta'], floor=0.01)}})

    def test_install_requires_the_declaration_and_phases_of_the_table(self):
        # 2026-09-26: the table's SC7 relFlow shares are right only with the v3b declaration and the phase authority
        # that serves them in p4; any other combination is refused before anything is installed
        tuning = copy.deepcopy(COMPLETE)
        tuning['urban']['movements'].pop('nonexistent_declaration')
        with self.assertRaisesRegex(ValueError, 'nonexistent_declaration'):
            ad.install_measured_turn_beta(cfg_with(self.um), tuning)
        with self.assertRaisesRegex(ValueError, 'physical_phase_authority'):
            ad.install_measured_turn_beta(cfg_with(self.um),
                                          complete_with(physical_phase_authority=mc.URBAN_B1_PHASE_AUTHORITY_BASE))
        with self.assertRaisesRegex(ValueError, 'phase_correction'):
            ad.install_measured_turn_beta(cfg_with(self.um), complete_with(phase_correction=False))
        with self.assertRaisesRegex(ValueError, 'phase_correction'):
            ad.install_measured_turn_beta(cfg_with(self.um), complete_with(phase_correction_skip_added='2026-09-01'))
        with self.assertRaisesRegex(ValueError, 'nonexistent_declaration'):
            ad.install_measured_turn_beta(cfg_with(self.um), complete_with(
                nonexistent_declaration={'path': mc.URBAN_B1_DECLARATION, 'sha256': '0' * 64}))

    def test_complete_table_is_pinned(self):
        unpinned = {'urban': {'beta': {k: v for k, v in COMPLETE['urban']['beta'].items() if k != 'sha256'}}}
        with self.assertRaisesRegex(ValueError, 'sha256'):
            ad.install_measured_turn_beta(cfg_with(self.um), unpinned)
        with self.assertRaisesRegex(ValueError, 'sha256'):
            ad.install_measured_turn_beta(cfg_with(self.um), {'urban': {'beta': dict(COMPLETE['urban']['beta'], sha256='0' * 64)}})

    def test_runtime_check_network_flowless_phases_and_green(self):
        from unittest.mock import patch
        from evaluation.controllers import network_provenance
        cfg = runtime_phase_cfg(self.doc)
        self.assertEqual(ad.check_complete_beta_runtime(cfg, DEFAULT, {}), {})      # other sources: no-op
        net = self.doc['inputs']['network']['sha256']
        with switches(PLAN_SWITCHES), patch.object(network_provenance, 'snapshot_network_sha256', return_value=net):
            meta = ad.check_complete_beta_runtime(cfg, COMPLETE, {})
            self.assertEqual(meta['complete_beta_network_checked'], 1.0)
            self.assertEqual(meta['complete_beta_flowless_phases'], 1.0)            # SC109_p1
            self.assertGreater(meta['complete_beta_green_checked_movements'], 200.0)
            # a phase that loses its last flow at runtime (e.g. a phase correction the derivation did not see) stops it
            starved = copy.deepcopy(cfg)
            for m, s in starved.network.urban_movements.items():
                if s.get('phase') == 'SC1001_p2':
                    s['beta'] = 0.0
            with self.assertRaisesRegex(ValueError, 'SC1001_p2'):
                ad.check_complete_beta_runtime(starved, COMPLETE, {})
            # the relFlow share of SC7 E_SC16 -> N_SC11 left in its declared phase p3 (no native green): starving
            stale = copy.deepcopy(cfg)
            stale.network.urban_movements['SC7_E_SC16_to_N_SC11']['phase'] = 'SC7_p3'
            with self.assertRaisesRegex(ValueError, 'without native green.*SC7_E_SC16_to_N_SC11'):
                ad.check_complete_beta_runtime(stale, COMPLETE, {})
            # an unsignalized movement needs no green
            stale.network.urban_movements['SC7_E_SC16_to_N_SC11']['unsignalized'] = True
            ad.check_complete_beta_runtime(stale, COMPLETE, {})
        with patch.object(network_provenance, 'snapshot_network_sha256', return_value='0' * 64):
            with self.assertRaisesRegex(ValueError, 'another network'):
                ad.check_complete_beta_runtime(cfg, COMPLETE, {})

    def test_default_source_is_unchanged(self):
        meta = ad.install_measured_turn_beta(cfg_with(self.um), DEFAULT)
        self.assertNotIn('measured_beta_complete', meta)
        self.assertEqual(meta['measured_beta_movements'], 370.0)


class GuardTests(unittest.TestCase):

    def test_guards_only_fire_for_the_complete_source(self):
        self.assertTrue(beta_source.complete_beta_source(COMPLETE))
        self.assertFalse(beta_source.complete_beta_source(DEFAULT))
        self.assertFalse(beta_source.complete_beta_source({}))
        self.assertFalse(beta_source.complete_beta_source(
            {'urban': {'beta': {'measured': False, 'source': 'routing_v3b2'}}}))
        beta_source.require_zero_moved_beta(DEFAULT, 'x', {'a': 0.3})
        beta_source.require_unit_approach_sums(DEFAULT, 'x', {'a': {'signal': 'S', 'approach': 'A', 'beta': 0.3}})
        with self.assertRaisesRegex(ValueError, 'non-zero share'):
            beta_source.require_zero_moved_beta(COMPLETE, 'x', {'a': 0.3})
        beta_source.require_zero_moved_beta(COMPLETE, 'x', {'a': 0.0})
        with self.assertRaisesRegex(ValueError, 'differ from 1'):
            beta_source.require_unit_approach_sums(COMPLETE, 'x', {'a': {'signal': 'S', 'approach': 'A', 'beta': 0.3}})

    def test_guard_and_install_share_one_predicate(self):
        # review 2026-09-26: measured 1.0 / 2 installed the complete table while the guards stayed off
        for flag in (True, False, 1, 0, 1.0, 2, 0.5, 0.0, '1', '1.0', 'on', 'yes', 'true', 'off', '', None):
            self.assertEqual(beta_source.is_enabled_value(flag), ad._is_enabled_value(flag), flag)
            tuning = {'urban': {'beta': dict(COMPLETE['urban']['beta'], measured=flag)}}
            self.assertEqual(beta_source.complete_beta_source(tuning), ad._is_enabled_value(flag), flag)
        cfg = cfg_with(runtime_movements())
        meta = ad.install_measured_turn_beta(cfg, {'urban': {'beta': dict(COMPLETE['urban']['beta'], measured=1.0),
                                                             'movements': dict(DECLARED)}})
        self.assertEqual(meta['measured_beta_complete'], 1.0)

    def test_dead_phase_zeroing_is_guarded(self):
        cfg = cfg_with(runtime_movements())
        ad.install_measured_turn_beta(cfg, COMPLETE)
        saved = dict(ad._CFG_SWITCHES)
        saved_strings, saved_route = dict(ad._CFG_STRINGS), dict(ad._ROUTE_ATTRIBUTION)
        try:
            ad.install_config_switches({'urban': {'movements': {'dead_phase_beta_zero': True}}})
            # SC7 E in its runtime phases (N_SC11 moved to its head's p4): the dead phase p3 keeps only the own-leg
            # U-turn, which carries 0 in the table -> zeroing and renormalising are identity
            sc7 = cfg_with({m: s for m, s in cfg.network.urban_movements.items() if m.startswith('SC7_E_to_')})
            sc7.network.urban_movements['SC7_E_to_N_SC11']['phase'] = 'SC7_p4'
            before = {m: s['beta'] for m, s in sc7.network.urban_movements.items()}
            meta = ad.apply_dead_phase_beta_zero(sc7, tuning=COMPLETE)
            self.assertEqual(meta['dead_phase_beta_zero_enabled'], 1.0)
            self.assertGreater(meta['dead_phase_movements'], 0.0)
            self.assertEqual({m: s['beta'] for m, s in sc7.network.urban_movements.items()}, before)
            # on the declared phases (before phase correction / authority) the switch would move relFlow shares
            # (SC7_E_to_N_SC11 0.429 in p3, SC107_N_SC1_to_S): refused for the complete source
            declared = cfg_with({m: s for m, s in cfg.network.urban_movements.items() if m.startswith('SC7_E_to_')})
            with self.assertRaisesRegex(ValueError, 'non-zero share'):
                ad.apply_dead_phase_beta_zero(declared, tuning=COMPLETE)
            with self.assertRaisesRegex(ValueError, 'non-zero share'):
                ad.apply_dead_phase_beta_zero(copy.deepcopy(cfg), tuning=COMPLETE)
            ad.apply_dead_phase_beta_zero(copy.deepcopy(cfg))              # the call before the measured beta: no guard
        finally:
            ad.install_config_switches({})
            for target, value in ((ad._CFG_SWITCHES, saved), (ad._CFG_STRINGS, saved_strings),
                                  (ad._ROUTE_ATTRIBUTION, saved_route)):
                target.clear()
                target.update(value)

    def test_dead_phase_switch_is_refused_with_the_complete_source(self):
        # review 2026-09-26: the switch judges the declared phases before the phase authority, so with the complete
        # table it would move SC7 E / E_SC16 -> N_SC11 (declared p3, served in p4); refused at install with its cause
        with self.assertRaisesRegex(ValueError, 'dead_phase_beta_zero'):
            ad.install_measured_turn_beta(cfg_with(runtime_movements()), complete_with(dead_phase_beta_zero=True))
        meta = ad.install_measured_turn_beta(cfg_with(runtime_movements()), complete_with(dead_phase_beta_zero=False))
        self.assertEqual(meta['measured_beta_complete'], 1.0)
        # another source is not concerned
        meta = ad.install_measured_turn_beta(cfg_with(runtime_movements()),
                                             {'urban': {'beta': DEFAULT['urban']['beta'],
                                                        'movements': {'dead_phase_beta_zero': True}}})
        self.assertNotIn('measured_beta_complete', meta)
        # and the candidate generator refuses a default tuning with the switch on
        base = json.loads(mc.OUT.read_text(encoding='utf-8'))
        self.assertIs(base['urban']['movements']['dead_phase_beta_zero'], False)
        base['urban']['movements']['dead_phase_beta_zero'] = True
        with self.assertRaisesRegex(ValueError, 'dead_phase_beta_zero'):
            mc.apply_urban_batch1(base)

    def test_fold_refuses_a_held_onramp_share(self):
        um = runtime_movements()
        cfg = cfg_with(um)
        ad.install_measured_turn_beta(cfg, COMPLETE)
        tuning = copy.deepcopy(COMPLETE)
        tuning['urban']['ramp'] = {'leg_split': True, 'gate_onramp_queue': True}
        ok = copy.deepcopy(cfg)
        ok.network.boundary_out_link_length_km = {}
        ok.network.wout_travel_speed_km_h = 40.0
        ad.install_leg_ramp_split_fold(ok, tuning)          # every folded share is 0 in routing_v3b2
        bad = copy.deepcopy(cfg)
        bad.network.wout_travel_speed_km_h = 40.0
        bad.network.urban_movements['SC1001_S_SC1003_to_onW']['beta'] = 0.1
        with self.assertRaisesRegex(ValueError, 'non-zero share'):
            ad.install_leg_ramp_split_fold(bad, tuning)


class RouteAttributionTests(unittest.TestCase):

    def setUp(self):
        self.saved = dict(ad._ROUTE_ATTRIBUTION)

    def tearDown(self):
        ad._ROUTE_ATTRIBUTION.clear()
        ad._ROUTE_ATTRIBUTION.update(self.saved)

    def switches(self, queue):
        return ad.install_config_switches({'urban': {'queue': queue}})

    def test_key_absent_loads_nothing(self):
        self.switches({'stopped_split': True})
        self.assertEqual(ad._CFG_STRINGS['queue_attribution'], '')
        self.assertEqual(ad._ROUTE_ATTRIBUTION, {})

    def test_route_requires_its_pinned_evidence(self):
        with self.assertRaisesRegex(ValueError, 'route_evidence'):
            self.switches({'attribution': 'route'})
        with self.assertRaisesRegex(ValueError, 'sha256'):
            self.switches({'attribution': 'route', 'route_evidence': {'path': mc.URBAN_B1_ROUTE_EVIDENCE,
                                                                       'sha256': '0' * 64}})
        self.switches({'attribution': 'route', 'route_evidence': {'path': mc.URBAN_B1_ROUTE_EVIDENCE,
                                                                   'sha256': mc.URBAN_B1_ROUTE_EVIDENCE_SHA256}})
        self.assertEqual(ad._ROUTE_ATTRIBUTION['sha256'], mc.URBAN_B1_ROUTE_EVIDENCE_SHA256)
        self.switches({})
        self.assertEqual(ad._ROUTE_ATTRIBUTION, {})

    def route_on(self):
        self.switches({'attribution': 'route', 'route_evidence': {'path': mc.URBAN_B1_ROUTE_EVIDENCE,
                                                                   'sha256': mc.URBAN_B1_ROUTE_EVIDENCE_SHA256}})

    def test_link_127_by_route_route_end_lane_and_never_off_ramp(self):
        self.route_on()
        um = runtime_movements()
        names = ['SC1001_W_to_E_SC1002', 'SC1001_W_to_N_SC2002', 'SC1001_W_to_S_SC1003',
                 'SC1001_offW_to_E_SC1002', 'SC1001_offW_to_N_SC2002', 'SC1001_offW_to_S_SC1003',
                 'SC1001_E_SC1002_to_N_SC2002']            # the nema_phase_fallback entry of another approach
        betas = {'SC1001_W_to_E_SC1002': 0.5, 'SC1001_W_to_N_SC2002': 0.3, 'SC1001_W_to_S_SC1003': 0.2}
        cfg = cfg_with({m: dict(um[m], beta=betas.get(m, 0.3)) for m in names})
        usable = [{'movement': m, 'weight': 1.0} for m in names]
        # the head window uses the pinned network's polyline length (the older FZP length table has no link 127)
        length = ad._ROUTE_ATTRIBUTION['link_lengths_m']['127']
        self.assertAlmostEqual(length, 629.776, places=3)
        self.assertNotIn('127', ad._link_lengths_m())
        vehicles = [  # head of the queue in lanes 1 and 3; lane 2 carries a moving vehicle at the front
            {'veh_no': 1, 'lane_no': 1, 'position_m': length - 2.0, 'stopped': True},    # route 1117:3 -> 10118
            {'veh_no': 2, 'lane_no': 1, 'position_m': length - 9.0, 'stopped': True},    # route-less, lane 1
            {'veh_no': 3, 'lane_no': 3, 'position_m': length - 3.0, 'stopped': True},    # route 1132:2 (off-ramp)
            {'veh_no': 4, 'lane_no': 2, 'position_m': length - 2.0, 'stopped': False},
        ]
        routes = {1: {'route_decision_no': 1117, 'route_no': 3}, 2: {'route_decision_no': None, 'route_no': None},
                  3: {'route_decision_no': 1132, 'route_no': 2}, 4: {'route_decision_no': 1117, 'route_no': 3}}
        diag = {}
        shares, leaves = ad._route_queue_shares(cfg, '127', usable, vehicles, routes, diag)
        self.assertEqual(leaves, 0.0)
        self.assertAlmostEqual(sum(shares.values()), 1.0, places=12)
        self.assertFalse([m for m in shares if '_offW_' in m or m.startswith('SC1001_E_SC1002')])
        self.assertEqual(diag['members'], 3.0)
        self.assertEqual(diag['route_veh'], 1.0)      # veh 1
        self.assertEqual(diag['route_end_veh'], 1.0)  # veh 3: 1132:2 ends on 127 -> 1117 re-routes it (beta)
        self.assertEqual(diag['lane_veh'], 1.0)       # veh 2 (lane 1: 10118 / 10368 by beta)
        self.assertEqual(diag['offramp_origin_veh'], 1.0)    # diagnostic only
        self.assertEqual(ad._ROUTE_ATTRIBUTION['routes']['1132:2'][-1], '127')
        # veh 1 -> E_SC1002; veh 3 -> the 127 connectors by beta 0.5/0.3/0.2; veh 2 lane 1 -> 10118 (E) / 10368 (S)
        self.assertAlmostEqual(shares['SC1001_W_to_N_SC2002'], 0.3 / 3, places=12)
        self.assertAlmostEqual(shares['SC1001_W_to_E_SC1002'] + shares['SC1001_W_to_S_SC1003'], 1 - 0.1, places=12)

    def test_upstream_link_route_end_diverging_and_routeless(self):
        # link 364 feeds SC105 E_SC1: 114:1 ends ON the stop-line link 1220007001 (re-routed there, beta), 114:3
        # turns to 359 before the approach (storage, not the stop-line queue), a route-less vehicle takes the beta
        self.route_on()
        um = runtime_movements()
        names = ['SC105_E_SC1_to_W_SC1003', 'SC105_E_SC1_to_N_SC1002', 'SC105_E_SC1_to_S_SC1005']
        betas = dict(zip(names, (0.5, 0.25, 0.25)))
        cfg = cfg_with({m: dict(um[m], beta=betas[m]) for m in names})
        usable = [{'movement': m, 'weight': w} for m, w in zip(names, (0.6, 0.2, 0.2))]
        self.assertEqual(ad._ROUTE_ATTRIBUTION['route_end_anchors']['114:1'], ['1220007001'])
        self.assertNotIn('1220007001', ad._ROUTE_ATTRIBUTION['route_end_anchors']['114:3'])
        vehicles = [{'veh_no': i, 'lane_no': 1, 'position_m': 50.0 - i, 'stopped': True} for i in (1, 2, 3, 4)]
        routes = {1: {'route_decision_no': 114, 'route_no': 1}, 2: {'route_decision_no': 114, 'route_no': 3},
                  3: {'route_decision_no': None, 'route_no': None}, 4: {'route_decision_no': 114, 'route_no': 1}}
        diag = {}
        shares, leaves = ad._route_queue_shares(cfg, '364', usable, vehicles, routes, diag)
        self.assertEqual((diag['route_end_veh'], diag['route_leaves_veh'], diag['beta_veh']), (2.0, 1.0, 1.0))
        self.assertAlmostEqual(leaves, 0.25, places=12)
        self.assertEqual(diag['route_leaves_stopped_share'], 1.0)
        # every non-leaving vehicle takes the approach's routing beta (not the 0.6 / 0.2 / 0.2 detector weights)
        for m in names:
            self.assertAlmostEqual(shares[m], betas[m], places=12)

    def test_zero_beta_crossing_and_foreign_lane_unsignalized_go_to_the_lane_rule(self):
        self.route_on()
        um = runtime_movements()
        # a crossing whose movement carries beta 0 (constructed: SC7 E 252:3 -> 10332 -> SC7_E_to_N_SC11 at 0, its
        # routing_v3b2 value before the v3b declaration correction of 2026-09-26): not a frozen queue there
        names = ['SC7_E_to_N_SC11', 'SC7_E_to_S_SC108']
        cfg = cfg_with({'SC7_E_to_N_SC11': dict(um['SC7_E_to_N_SC11'], beta=0.0),
                        'SC7_E_to_S_SC108': dict(um['SC7_E_to_S_SC108'], beta=1.0)})
        self.assertIn('10332', ad._ROUTE_ATTRIBUTION['routes']['252:3'])
        diag = {}
        shares, _ = ad._route_queue_shares(cfg, '1210009600', [{'movement': m, 'weight': 1.0} for m in names],
                                           [{'veh_no': 1, 'lane_no': 1, 'position_m': 100.0, 'stopped': True}],
                                           {1: {'route_decision_no': 252, 'route_no': 3}}, diag)
        self.assertEqual((diag['route_to_lane_veh'], diag['lane_veh']), (1.0, 1.0))
        self.assertEqual(shares.get('SC7_E_to_S_SC108'), 1.0)
        self.assertEqual(shares.get('SC7_E_to_N_SC11', 0.0), 0.0)
        # SC1002 W_SC1001 link 30: 10686 (U3 unsignalized) leaves lane 1 only; a lane-2 vehicle routed there waits
        # in the signal-held lane 2 (10685)
        names = ['SC1002_W_SC1001_to_S_SC105', 'SC1002_W_SC1001_to_E_SC101', 'SC1002_W_SC1001_to_N_SC2004']
        cfg = cfg_with({m: dict(um[m], beta=b) for m, b in zip(names, (0.7, 0.2, 0.1))})
        cfg.network.urban_movements['SC1002_W_SC1001_to_S_SC105']['unsignalized'] = True
        key = next(k for k, seq in ad._ROUTE_ATTRIBUTION['routes'].items()
                   if '30' in seq and '10686' in seq and seq.index('10686') == seq.index('30') + 1)
        rd, rn = key.split(':')
        routes = {1: {'route_decision_no': int(rd), 'route_no': int(rn)}, 2: {'route_decision_no': int(rd), 'route_no': int(rn)}}
        vehicles = [{'veh_no': 1, 'lane_no': 1, 'position_m': 500.0, 'stopped': True},
                    {'veh_no': 2, 'lane_no': 2, 'position_m': 500.0, 'stopped': True}]
        diag = {}
        shares, _ = ad._route_queue_shares(cfg, '30', [{'movement': m, 'weight': 1.0} for m in names], vehicles, routes, diag)
        self.assertEqual((diag['route_veh'], diag['route_to_lane_veh'], diag['lane_veh']), (1.0, 1.0, 1.0))
        self.assertAlmostEqual(shares['SC1002_W_SC1001_to_S_SC105'], 0.5, places=12)
        self.assertAlmostEqual(shares['SC1002_W_SC1001_to_E_SC101'], 0.5, places=12)


class UnsignalizedTurnTests(unittest.TestCase):

    def tuning(self, sha256=mc.URBAN_B1_UNSIGNALIZED_SHA256):
        return {'urban': {'movements': {'unsignalized_evidence': {'path': mc.URBAN_B1_UNSIGNALIZED, 'sha256': sha256}}}}

    def test_absent_key_is_a_no_op(self):
        cfg = cfg_with(runtime_movements())
        before = copy.deepcopy(cfg.network.urban_movements)
        self.assertEqual(ad.install_unsignalized_turns(cfg, {'urban': {'movements': {}}}), {})
        self.assertEqual(cfg.network.urban_movements, before)
        self.assertFalse(hasattr(cfg.network, 'unsignalized_evidence_movements'))

    def test_head_free_turn_leaves_the_head_lane_group(self):
        # review 2026-09-26: SC1002 W_SC1001 10686 (lane 1, no head) shared the p3 through heads' floor by beta
        um = runtime_movements()
        names = ['SC1002_W_SC1001_to_S_SC105', 'SC1002_W_SC1001_to_E_SC101']
        specs = {m: dict(um[m], beta=b, phase='SC1002_p3', kind='internal') for m, b in zip(names, (0.6956, 0.1624))}
        origin = specs[names[0]]['origin']
        saved = dict(ad._LTO)
        try:
            ad._LTO.clear()
            ad._LTO['30'] = [origin]
            groups = [{'stopline_link': '30', 'signal': 'SC1002'}]
            before = cfg_with(specs)
            caps = {}
            ad._distribute_lane_group_capacity_to_movements(before, groups, {('30', 'p3'): 720.0}, caps)
            self.assertAlmostEqual(caps[names[0]], 720.0 * 0.6956 / (0.6956 + 0.1624), places=9)
            cfg = cfg_with(specs)
            doc = load(mc.URBAN_B1_UNSIGNALIZED)
            cfg.network.urban_movements = {m: s for m, s in runtime_movements().items()}
            ad.install_unsignalized_turns(cfg, self.tuning())
            self.assertEqual(cfg.network.unsignalized_evidence_movements, frozenset(doc['movements']))
            self.assertIn(names[0], cfg.network.unsignalized_evidence_movements)
            cfg.network.urban_movements = specs
            caps = {names[0]: 206.53}
            ad._distribute_lane_group_capacity_to_movements(cfg, groups, {('30', 'p3'): 720.0}, caps)
            self.assertEqual(caps, {names[0]: 206.53, names[1]: 720.0})    # its own lane capacity stays
        finally:
            ad._LTO.clear()
            ad._LTO.update(saved)

    def test_pinned_movements_become_unsignalized(self):
        doc = load(mc.URBAN_B1_UNSIGNALIZED)
        self.assertIn('SC1001_S_SC1003_to_E_SC1002', doc['movements'])     # 10377, link 40 lane 1
        self.assertIn('SC1001_E_SC1002_to_N_SC2002', doc['movements'])     # 10122, link 29 lane 1
        shared = {x['connector'] for x in doc['not_included_shared_lane']}
        self.assertTrue({'10121', '10628', '10625', '10632'} <= shared)
        self.assertIn('SC1004_W_to_S', doc['already_unsignalized_by_phase_authority'])   # 10642
        cfg = cfg_with(runtime_movements())
        meta = ad.install_unsignalized_turns(cfg, self.tuning())
        flagged = {m for m, s in cfg.network.urban_movements.items() if s.get('unsignalized')}
        self.assertEqual(meta['unsignalized_turns_movements'], float(len(doc['movements'])))
        self.assertTrue(set(doc['movements']) <= flagged)
        with self.assertRaisesRegex(ValueError, 'sha256'):
            ad.install_unsignalized_turns(cfg_with(runtime_movements()), self.tuning('0' * 64))
        with self.assertRaisesRegex(ValueError, 'already unsignalized'):
            ad.install_unsignalized_turns(cfg, self.tuning())

    def test_strict_rule_excludes_downstream_heads_and_unvalidated(self):
        doc = load(mc.URBAN_B1_UNSIGNALIZED)
        down = {x['movement']: x for x in doc['downstream_head_not_included']}
        # 10683: heads 90030858/9 stand 0.5-0.8 m past the diverge on its source lanes -> not a free turn by the rule
        self.assertIn('SC1002_N_SC2004_to_S_SC105', down)
        self.assertEqual(down['SC1002_N_SC2004_to_S_SC105']['connectors'], ['10683'])
        self.assertIn('SC107_W_SC1004_to_S', down)
        self.assertEqual({x['movement'] for x in doc['not_included_fzp_validation']}, {'SC107_N_SC1_to_W_SC1005'})
        excluded = set(down) | {x['movement'] for x in doc['not_included_fzp_validation']} | {
            x['movement'] for x in doc['not_included_shared_lane']}
        self.assertFalse(excluded & set(doc['movements']))
        self.assertEqual(len(doc['movements']), 23)
        for name, row in doc['movements'].items():
            for v in row['validation']:
                self.assertGreaterEqual(v['stopped_before_n'], doc['validation_rule']['min_observed_transitions'], name)
                self.assertLessEqual(v['stopped_before_share'], doc['validation_rule']['max_stopped_before_share'], name)

    def test_every_green_fraction_path_returns_one(self):
        from evaluation.controllers import sdmpc_continuous, signal_actuation_contract
        spec = {'phase': 'SC1001_p1', 'unsignalized': True}
        net = types.SimpleNamespace(signal_actuation_contract={'nodes': {}}, sdmpc_options={})
        cfg = types.SimpleNamespace(network=net)
        enabled = signal_actuation_contract.enabled
        signal_actuation_contract.enabled = lambda _net: True
        try:
            self.assertEqual(signal_actuation_contract.phase_fraction(None, cfg, spec), 1.0)
            self.assertEqual(sdmpc_continuous.phase_fraction(None, cfg, spec), 1.0)
        finally:
            signal_actuation_contract.enabled = enabled
        patched = ad.build_patched_phase_green_fraction(lambda *a, **k: 0.25, {}, types.SimpleNamespace(
            share_for=lambda s: 1.0))
        self.assertEqual(patched(None, cfg, spec), 1.0)


class AreaDynamicRoutesTests(unittest.TestCase):
    """area_dynamic_routes removes four own-leg U-turns and installed the offline NC13 prior (a realised share) on
    their retained branches. With the complete source the table (relFlow) values stay; otherwise nothing changes."""

    PATH = 'diagnostics/sdmpc_n31_20260924/scenario/dynamic_area_routes_ver2_dbaf86.json'

    @classmethod
    def setUpClass(cls):
        cls.doc = load(cls.PATH)
        cls.um = runtime_movements()

    def run_configure(self, tuning, edit=None):
        from unittest.mock import patch
        from evaluation.controllers import area_dynamic_routes as dr
        tuning = copy.deepcopy(tuning)
        tuning['urban']['movements'] = dict(tuning['urban'].get('movements', {}), dynamic_physical_route_topology=self.PATH)
        cfg = cfg_with(self.um)
        ad.install_measured_turn_beta(cfg, tuning)
        if edit:
            edit(cfg.network.urban_movements)
        detectors = {'link_to_movements': {}, 'link_to_origins': {}, 'agents': {}}
        for repair in self.doc['topology_repairs']:
            for link in repair['physical_projection_links']:
                detectors['link_to_movements'][link] = (
                    [{'movement': repair['remove_movement'], 'weight': 1.0}]
                    + [{'movement': m, 'weight': 1.0} for m in repair['keep_movements']])
        for repair in self.doc.get('origin_repairs', []):
            detectors['link_to_origins'][repair['physical_link']] = list(repair['expected_origins'])
        with patch.object(dr, 'snapshot_network_sha256', return_value=self.doc['network']['sha256']):
            out, meta = dr.configure(cfg, detectors, tuning, state_json={})
        return cfg, out, meta

    def test_default_source_keeps_the_offline_prior(self):
        cfg, _out, meta = self.run_configure(DEFAULT)
        specs = cfg.network.urban_movements
        self.assertEqual(len(meta['repairs']), 4)
        for row in meta['repairs']:
            self.assertNotIn(row['removed_movement'], specs)
            self.assertEqual(set(row), {'removed_movement', 'offline_calibrated_betas', 'projection', 'limitations'})
            for m, b in row['offline_calibrated_betas'].items():
                self.assertEqual(specs[m]['beta'], b)
        self.assertAlmostEqual(specs['SC107_W_SC1005_to_S']['beta'], 0.4899, places=4)

    def test_complete_source_keeps_the_table_values(self):
        table = load(mc.URBAN_B1_BETA_FILE)['beta']
        cfg, out, meta = self.run_configure(COMPLETE)
        specs = cfg.network.urban_movements
        self.assertEqual(len(meta['repairs']), 4)
        for row in meta['repairs']:
            self.assertEqual(row['beta_values_source'], 'complete_routing_table')
            self.assertNotIn(row['removed_movement'], specs)
            self.assertEqual(table[row['removed_movement']], 0.0)
            self.assertAlmostEqual(math.fsum(row['installed_betas'].values()), 1.0, places=12)
            for m, b in row['installed_betas'].items():
                self.assertEqual(b, table[m])
                self.assertEqual(specs[m]['beta'], table[m])
        # SC107 W: relFlow of 1061 (v3b NC FZP 0.756 / 0.244), not the NC13 prior 0.937 / 0.063 and 0.510 / 0.490
        self.assertAlmostEqual(specs['SC107_W_SC1004_to_E_SC108']['beta'], 0.7541, places=4)
        self.assertAlmostEqual(specs['SC107_W_SC1005_to_S']['beta'], 0.2459, places=4)
        # the reviewed physical projection links are re-weighted by the installed values as well, and say so
        rows = out['link_to_movements']['61']
        total = math.fsum(r['weight'] for r in rows)
        for r in rows:
            self.assertAlmostEqual(r['weight'] / total, table[r['movement']], places=12)
            self.assertEqual(r['source'], 'complete_routing_table')
        _cfg, out_default, _meta = self.run_configure(DEFAULT)
        self.assertEqual({r['source'] for r in out_default['link_to_movements']['61']},
                         {'offline_nc13_route_prior_without_phantom'})

    def test_complete_source_refuses_a_moved_or_partial_share(self):
        def removed_nonzero(specs):
            specs['SC107_W_SC1004_to_W_SC1005'] = dict(specs['SC107_W_SC1004_to_W_SC1005'], beta=0.1)
        with self.assertRaisesRegex(ValueError, 'non-zero share'):
            self.run_configure(COMPLETE, removed_nonzero)

        def partial(specs):
            specs['SC1004_E_SC1005_to_S'] = dict(specs['SC1004_E_SC1005_to_S'], beta=0.0)
        with self.assertRaisesRegex(ValueError, 'not the whole approach'):
            self.run_configure(COMPLETE, partial)


class OfframpDirectShareTests(unittest.TestCase):

    @staticmethod
    def net():
        movements = {
            'SC1001_offW_to_W_RAMP': {'origin': 'OR_D_W', 'beta': 0.2}, 'SC1001_offW_to_E_SC1002': {'origin': 'OR_D_W', 'beta': 0.8},
            'SC1001_offE_to_W_RAMP': {'origin': 'OR_D_E', 'beta': 0.1}, 'SC1001_offE_to_E_SC1002': {'origin': 'OR_D_E', 'beta': 0.9},
            'SC1004_offW_to_W': {'origin': 'OR_F_W', 'beta': 0.3}, 'SC1004_offW_to_N_SC1003': {'origin': 'OR_F_W', 'beta': 0.7},
            'SC1004_offE_to_W': {'origin': 'OR_F_E', 'beta': 0.4}, 'SC1004_offE_to_N_SC1003': {'origin': 'OR_F_E', 'beta': 0.6}}
        off = {'OR_D_W': ['SC1001_offW_to_W_RAMP', 'SC1001_offW_to_E_SC1002'],
               'OR_D_E': ['SC1001_offE_to_W_RAMP', 'SC1001_offE_to_E_SC1002'],
               'OR_F_W': ['SC1004_offW_to_W', 'SC1004_offW_to_N_SC1003'],
               'OR_F_E': ['SC1004_offE_to_W', 'SC1004_offE_to_N_SC1003']}
        return types.SimpleNamespace(network=types.SimpleNamespace(
            urban_movements=movements, urban_link_storage_veh={}, boundary_out_links=[], off_ramp_to_movement=off))

    def test_explicit_share_is_the_former_code_default_and_bit_identical(self):
        n31 = json.loads((ROOT / 'diagnostics/sdmpc_n31_20260924/config_n31_v2.json').read_text(encoding='utf-8-sig'))
        explicit = n31['urban']['ramp']['offramp_direct_share']
        self.assertEqual(explicit, ad.OFFRAMP_DIRECT_SHARE_LEGACY_DEFAULT)
        self.assertEqual(mc.OFFRAMP_DIRECT_SHARE, ad.OFFRAMP_DIRECT_SHARE_LEGACY_DEFAULT)
        absent, present = self.net(), self.net()
        meta_a = ad.install_offramp_direct_landing(absent, {'urban': {'ramp': {'offramp_direct': True}}})
        meta_p = ad.install_offramp_direct_landing(present, {'urban': {'ramp': {'offramp_direct': True,
                                                                                 'offramp_direct_share': explicit}}})
        self.assertEqual(meta_a, meta_p)
        self.assertEqual(vars(absent.network), vars(present.network))
        self.assertEqual(present.network.offramp_direct_share_by_offramp,
                         {'OR_D_W': 0.468, 'OR_D_E': 0.468, 'OR_F_W': 0.484, 'OR_F_E': 0.484})

    def test_present_share_must_name_both_interchanges(self):
        # an empty or partial mapping no longer falls back silently (empty -> old default, partial -> a 0 share)
        for bad in ({}, {'SC1001': 0.468}, None, {'SC1001': 0.468, 'SC1004': 0.484, 'SC9': 0.1}):
            with self.assertRaisesRegex(ValueError, 'offramp_direct_share'):
                ad.install_offramp_direct_landing(self.net(), {'urban': {'ramp': {'offramp_direct': True,
                                                                                  'offramp_direct_share': bad}}})

    def test_route_prior_sets_the_relflow_share_per_group(self):
        from evaluation.controllers import offramp_routing
        cfg = self.net()
        ad.install_offramp_direct_landing(cfg, {'urban': {'ramp': {'offramp_direct': True,
                                                                   'offramp_direct_share': mc.OFFRAMP_DIRECT_SHARE}}})
        before = copy.deepcopy(vars(cfg.network))
        self.assertEqual(offramp_routing.install(cfg, {'urban': {'ramp': {}}}), {})
        self.assertEqual(vars(cfg.network), before)
        meta = offramp_routing.install(cfg, {'urban': {'ramp': {'offramp_direct_route_prior': mc.URBAN_B1_OFFRAMP_PRIOR}}})
        self.assertEqual(meta['offramp_route_prior_enabled'], 1.0)
        shares = cfg.network.offramp_direct_share_by_offramp
        self.assertEqual(shares['OR_D_W'], 0.5)       # decision 1132 relFlow 1:1 (v3b NC FZP 0.49-0.50)
        self.assertEqual(shares['OR_D_E'], 0.8)
        self.assertEqual(shares['OR_F_W'], 0.75)
        self.assertAlmostEqual(shares['OR_F_E'], 2.0 / 3.0, places=15)


class SC7DeclarationTests(unittest.TestCase):
    """User decision 2026-09-26: correct the v2-reading declaration of SC7 E / E_SC16 -> N_SC11 to v3b, serve the two in
    the phase of their real head (140101, SC7 SG 1 = p4) and give the relFlow value; nothing else changes."""

    NET = 'diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3bnc.inpx'
    SIG = 'diagnostics/sdmpc_n31_20260924/network/개포동 test-bed14.sig'
    PLAN = PLAN_SWITCHES['urban']['plan']['actuation_plan_json']
    SC7_N = ('SC7_E_to_N_SC11', 'SC7_E_SC16_to_N_SC11')

    def test_declaration_matches_the_network(self):
        import xml.etree.ElementTree as ET
        decl = load(mc.URBAN_B1_DECLARATION)
        self.assertEqual(decl['schema'], ad.MOVEMENT_DECLARATION_SCHEMA)
        self.assertEqual(decl['network']['sha256'], mc.NETWORK_SHA256)
        self.assertEqual(set(decl['known_nonexistent_movements']), {'SC109_N_SC16_to_W_SC108'})
        self.assertEqual(set(decl['corrected']), set(self.SC7_N))
        legacy = load('outputs/movement_phase_correction_20260828.json')['known_nonexistent_movements']
        self.assertEqual({k for k in legacy if not k.startswith('_')},
                         set(decl['known_nonexistent_movements']) | set(decl['corrected']))
        root = ET.parse(str(ROOT / self.NET)).getroot()
        links = {x.get('no'): x for x in root.findall('./links/link')}
        c = links['10332']
        self.assertEqual((c.find('fromLinkEndPt').get('lane'), c.find('toLinkEndPt').get('lane').split()[0]),
                         ('1210009600 1', '1220008701'))
        self.assertEqual(len(links['1210009600'].findall('./lanes/lane')), 1)
        self.assertEqual(sorted(k for k, x in links.items() if x.find('fromLinkEndPt') is not None
                                and x.find('fromLinkEndPt').get('lane').split()[0] == '1210009600'), ['10332', '10333'])
        head = next(h for h in root.findall('./signalHeads/signalHead') if h.get('no') == '140101')
        self.assertEqual((head.get('lane'), head.get('sg')), ('1210009600 1', '7 1'))
        self.assertLess(float(head.get('pos')), float(c.find('fromLinkEndPt').get('pos')))
        for row in decl['corrected'].values():
            self.assertEqual(row['physical_path'], ['1210009600', '10332', '1220008701'])

    def test_head_sg_is_served_in_plan_p4(self):
        import xml.etree.ElementTree as ET
        plan = load(self.PLAN)['controllers']['7']
        self.assertEqual([p for p, g in plan['phase_signal_groups'].items() if '1' in map(str, g)], ['p4'])
        self.assertEqual((plan['axis_green_sec']['p3'], plan['axis_green_sec']['p4']), (0.0, 24.0))
        self.assertEqual(ad.plan_live_phases({'controllers': {'7': plan}}, 7), ('p1', 'p2', 'p4'))
        # the .sig program itself (prog 1, 120 s): SG 1 green from 93 s, 3 s amber at the cycle end -> 24 s;
        # SG 2 and 6 (p3) never leave red
        root = ET.parse(str(ROOT / self.SIG)).getroot()
        tag = lambda e: e.tag.split('}')[-1]  # noqa: E731
        prog = next(p for p in root.iter() if tag(p) == 'prog' and p.get('id') == '1')
        cmds = {sg.get('sg_id'): [(tag(c), c.attrib) for c in sg.iter() if tag(c) in ('cmd', 'fixedstate')]
                for sg in prog.iter() if tag(sg) == 'sg'}
        green = [int(a['begin']) for t, a in cmds['1'] if t == 'cmd' and a['display'] == '3']
        amber = [int(a['duration']) for t, a in cmds['1'] if t == 'fixedstate']
        self.assertEqual((int(prog.get('cycletime')) - green[0] - amber[0]) / 1000.0, 24.0)
        for sg in ('2', '6'):
            self.assertEqual({a['display'] for t, a in cmds[sg] if t == 'cmd'}, {'1'})

    def test_shared_lane_capacity_and_crossed_midblock_head(self):
        """Review 2026-09-26. (1) 10332 and 10333 share the single lane of 1210009600 after head 140101, and the model
        does NOT split that lane's capacity by beta: install_movement_capacity_by_lanes gives each movement its own
        connector lane (the authority caveat said the opposite before). (2) The N_SC11 path crosses SC7 SG 16 (heads
        141801/141802, midblock, native program, in no plan phase) on 1220008701 before its only exit 10334; that SG is
        red for 18 s of the 24 s p4 green and gates no model movement."""
        import xml.etree.ElementTree as ET
        doc = load(mc.URBAN_B1_PHASE_AUTHORITY)
        for m in self.SC7_N:
            row = doc['by_movement'][m]
            self.assertEqual([(c['id'], c['source_lanes'], c['lanes'], c['target_link']) for c in row['source_lane_connectors']],
                             [('10332', [1], 1, '1220008701'), ('10333', [1], 1, '1220007402')])
            self.assertEqual([(h['head'], h['link'], h['lane'], h['SC'], h['SG'], h['plan_role'], h['native_routes'],
                               h['leaves_by']) for h in row['crossed_heads_after_source']],
                             [('141802', '1220008701', 1, 'SC7', '16', 'midblock_native', ['252:3'], ['10334']),
                              ('141801', '1220008701', 2, 'SC7', '16', 'midblock_native', ['252:3'], ['10334'])])
            self.assertTrue(row['caveats'][0].startswith('No capacity split on a shared stop-line lane'))
            self.assertNotIn('splits the lane-group capacity', ' '.join(row['caveats']))
        # the other (base) rows are untouched by the record fields
        self.assertEqual({k for m, r in doc['by_movement'].items() if m not in self.SC7_N for k in r} &
                         {'source_lane_connectors', 'crossed_heads_after_source'}, set())
        plan = load(self.PLAN)['controllers']['7']
        self.assertIn('16', list(map(str, plan['midblock_native_signal_groups'])))
        self.assertFalse(any('16' in map(str, g) for g in plan['phase_signal_groups'].values()))
        root = ET.parse(str(ROOT / self.SIG)).getroot()
        tag = lambda e: e.tag.split('}')[-1]  # noqa: E731
        prog = next(p for p in root.iter() if tag(p) == 'prog' and p.get('id') == '1')
        cmds = {sg.get('sg_id'): [(tag(c), c.attrib) for c in sg.iter() if tag(c) in ('cmd', 'fixedstate')]
                for sg in prog.iter() if tag(sg) == 'sg'}
        sg16 = {a['display']: int(a['begin']) // 1000 for t, a in cmds['16'] if t == 'cmd'}
        self.assertEqual((sg16['1'], sg16['3']), (85, 111))                  # red 85-111 s, green from 111 s
        sg1_green = ({int(a['begin']) // 1000 for t, a in cmds['1'] if t == 'cmd' and a['display'] == '3'}.pop(),
                     (int(prog.get('cycletime')) - [int(a['duration']) for t, a in cmds['1'] if t == 'fixedstate'][0]) // 1000)
        self.assertEqual(sg1_green, (93, 117))
        self.assertEqual(min(sg1_green[1], sg16['3']) - max(sg1_green[0], sg16['1']), 18)
        # (1) the capacity rule: each connector-lane movement of the shared lane holds one lane's capacity
        cfg = cfg_with(runtime_movements())
        ad.install_measured_turn_beta(cfg, COMPLETE)
        meta = ad.install_movement_capacity_by_lanes(cfg, {'urban': {'capacity': {
            'per_lane': True, 'equivalent_uniform_veh_h': 330.0, 'perimeter': 'all'}}})
        caps = cfg.network.movement_capacity_by_movement_veh_h
        for approach in ('SC7_E_SC16', 'SC7_E'):
            self.assertEqual(caps[approach + '_to_N_SC11'], caps[approach + '_to_S_SC108'])
        self.assertEqual(caps['SC7_E_SC16_to_N_SC11'], meta['movement_capacity_by_lanes_per_lane_veh_h'])

    def test_phase_authority_moves_only_the_two_to_p4(self):
        from evaluation.controllers import physical_movement_routes as pmr
        tun = json.loads(mc.OUT.read_text(encoding='utf-8'))
        plan = load(self.PLAN)
        phases, metas = {}, {}
        with switches(tun):
            for path in (mc.URBAN_B1_PHASE_AUTHORITY_BASE, mc.URBAN_B1_PHASE_AUTHORITY):
                cfg = cfg_with(runtime_movements())
                ad.apply_movement_phase_correction(cfg, tun)
                t = copy.deepcopy(tun)
                t['urban']['movements']['physical_phase_authority'] = path
                metas[path] = pmr.configure_phase_authority(cfg, t, plan)
                phases[path] = {m: s['phase'] for m, s in cfg.network.urban_movements.items()}
        a, b = phases[mc.URBAN_B1_PHASE_AUTHORITY_BASE], phases[mc.URBAN_B1_PHASE_AUTHORITY]
        self.assertEqual({m: (a[m], b[m]) for m in a if a[m] != b[m]}, {m: ('SC7_p3', 'SC7_p4') for m in self.SC7_N})
        changes = metas[mc.URBAN_B1_PHASE_AUTHORITY]['physical_phase_authority_changes']
        for m in self.SC7_N:
            self.assertEqual(changes[m], {'before': 'SC7_p3', 'after': 'SC7_p4', 'source_SGs': ['1']})
        base_changes = metas[mc.URBAN_B1_PHASE_AUTHORITY_BASE]['physical_phase_authority_changes']
        self.assertEqual({k: v for k, v in changes.items() if k not in self.SC7_N}, base_changes)
        # the rest of the evidence is the default one, value for value
        new, old = load(mc.URBAN_B1_PHASE_AUTHORITY), load(mc.URBAN_B1_PHASE_AUTHORITY_BASE)
        self.assertEqual({k: v for k, v in new.items() if k not in ('by_movement', 'v3b_corrections')},
                         {k: v for k, v in old.items() if k != 'by_movement'})
        self.assertEqual({k: v for k, v in new['by_movement'].items() if k not in self.SC7_N}, old['by_movement'])
        # p3 / p4 of SC7 at runtime: p4 = both S_SC108 turns and both N_SC11 turns (SG 1); p3 keeps no flow
        self.assertEqual(sorted(m for m, p in b.items() if p == 'SC7_p4'),
                         ['SC7_E_SC16_to_N_SC11', 'SC7_E_SC16_to_S_SC108', 'SC7_E_to_N_SC11', 'SC7_E_to_S_SC108'])
        self.assertEqual(sorted(m for m, p in b.items() if p == 'SC7_p3'), ['SC7_E_SC16_to_E', 'SC7_E_to_E_SC16'])

    def test_nonexistent_declaration_key(self):
        um = runtime_movements()
        legacy = cfg_with(um)
        meta = ad.apply_nonexistent_movement_beta_zero(legacy, {'urban': {'movements': {}}})
        self.assertNotIn('nonexistent_movement_declaration_pinned', meta)       # key absent: the old section, as before
        for m in self.SC7_N + ('SC109_N_SC16_to_W_SC108',):
            self.assertEqual(legacy.network.urban_movements[m]['beta'], 0.0, m)
        pinned = cfg_with(um)
        meta = ad.apply_nonexistent_movement_beta_zero(pinned, {'urban': {'movements': {
            'nonexistent_declaration': DECLARED['nonexistent_declaration']}}})
        self.assertEqual((meta['nonexistent_movement_declaration_pinned'], meta['nonexistent_movement_declared']), (1.0, 1.0))
        self.assertEqual(pinned.network.urban_movements['SC109_N_SC16_to_W_SC108']['beta'], 0.0)
        for m in self.SC7_N:
            self.assertEqual(pinned.network.urban_movements[m]['beta'], um[m]['beta'], m)
        for bad in ({'path': mc.URBAN_B1_DECLARATION}, {'path': mc.URBAN_B1_DECLARATION, 'sha256': '0' * 64}):
            with self.assertRaisesRegex(ValueError, 'nonexistent_declaration'):
                ad.apply_nonexistent_movement_beta_zero(cfg_with(um), {'urban': {'movements': {'nonexistent_declaration': bad}}})

    def test_area_route_of_the_departing_movement(self):
        base, new = load(mc.URBAN_B1_AREA_ROUTES_BASE), load(mc.URBAN_B1_AREA_ROUTES)
        self.assertEqual({k for k in set(base) | set(new) if base.get(k) != new.get(k)}, {'movement:SC7_E_SC16_to_N_SC11'})
        self.assertEqual(base['movement:SC7_E_SC16_to_N_SC11']['status'], 'no_match')
        row = new['movement:SC7_E_SC16_to_N_SC11']
        self.assertEqual((row['source_inside'], row['target_inside'], row['inside_to_inside'], row['outside_to_inside'],
                          row['outward_crossings_per_vehicle'], row['inward_crossings_per_vehicle']), (True, True, 1.0, 1.0, 0, 0))
        turn = row['physical_turns'][0]
        self.assertEqual((turn['from_link'], turn['connector'], turn['to_link'], turn['native_routes']),
                         ('1210009600', '10332', '1220008701', ['252:3']))
        # the synthetic boundary leg (in_SC7_E) stays unresolved in the file like its sibling S_SC108 (the runtime
        # gate-alias extension resolves both from the E_SC16 routes)
        prov = load(mc.URBAN_B1_AREA_ROUTES_PROVENANCE)
        self.assertEqual(set(prov['left_unresolved']), {'SC7_E_to_N_SC11'})
        self.assertIsNot(type(new['movement:SC7_E_to_S_SC108'].get('target_inside')), bool)


class ConfigTests(unittest.TestCase):

    def test_dead_queue_origin_filter_is_removed(self):
        self.assertFalse(hasattr(ad, '_queue_origin_filter_enabled'))
        self.assertFalse(hasattr(ad, '_movement_origin'))

    def test_offramp_direct_share_is_explicit(self):
        tuning = mc.apply(fx.load_json(fx.OBS1), require_repinned=False)
        self.assertEqual(tuning['urban']['ramp']['offramp_direct_share'], {'SC1001': 0.468, 'SC1004': 0.484})

    @staticmethod
    def default_tuning():
        # the generated default (make_config_n31.py --check pins it); batch 1 extends its phase authority and area
        # route contract, so the candidate starts from exactly that tuning
        return json.loads((mc.OUT).read_text(encoding='utf-8'))

    def test_batch1_candidate_adds_exactly_its_keys(self):
        base = self.default_tuning()
        cand = mc.apply_urban_batch1(base)
        self.assertEqual(cand['urban']['beta']['source'], 'routing_v3b2')
        self.assertEqual(cand['urban']['beta']['sha256'], mc.URBAN_B1_BETA_SHA256)
        self.assertEqual(cand['urban']['queue']['attribution'], 'route')
        self.assertEqual(cand['urban']['queue']['route_evidence']['sha256'], mc.URBAN_B1_ROUTE_EVIDENCE_SHA256)
        self.assertEqual(cand['urban']['movements']['unsignalized_evidence']['sha256'], mc.URBAN_B1_UNSIGNALIZED_SHA256)
        self.assertEqual(cand['urban']['movements']['nonexistent_declaration'],
                         {'path': mc.URBAN_B1_DECLARATION, 'sha256': mc.URBAN_B1_DECLARATION_SHA256})
        self.assertEqual(cand['urban']['movements']['physical_phase_authority'], mc.URBAN_B1_PHASE_AUTHORITY)
        self.assertEqual(cand['control_area_objective']['route_contract_path'], mc.URBAN_B1_AREA_ROUTES)
        self.assertEqual(cand['urban']['ramp']['offramp_direct_route_prior'], mc.URBAN_B1_OFFRAMP_PRIOR)
        rest = copy.deepcopy(cand)
        rest.pop('_n31_urban_b1_note')
        rest['urban']['beta']['source'] = 'routing_v3b'
        rest['urban']['beta'].pop('sha256')
        for key in ('attribution', 'route_evidence'):
            rest['urban']['queue'].pop(key)
        rest['urban']['movements'].pop('unsignalized_evidence')
        rest['urban']['movements'].pop('nonexistent_declaration')
        rest['urban']['movements']['physical_phase_authority'] = mc.URBAN_B1_PHASE_AUTHORITY_BASE
        rest['control_area_objective']['route_contract_path'] = mc.URBAN_B1_AREA_ROUTES_BASE
        rest['urban']['ramp'].pop('offramp_direct_route_prior')
        self.assertEqual(rest, base)
        with self.assertRaises(ValueError):
            mc.apply_urban_batch1(cand)
        other = copy.deepcopy(base)
        other['urban']['movements']['physical_phase_authority'] = 'diagnostics/elsewhere.json'
        with self.assertRaisesRegex(ValueError, 'phase authority'):
            mc.apply_urban_batch1(other)

    def test_batch1_components(self):
        base = self.default_tuning()
        full = mc.apply_urban_batch1(base)
        u13 = mc.apply_urban_batch1(base, ('U1', 'U3'))
        self.assertNotIn('attribution', u13['urban']['queue'])
        self.assertIn('unsignalized_evidence', u13['urban']['movements'])
        u12 = mc.apply_urban_batch1(base, ('U2', 'U1'))
        self.assertNotIn('unsignalized_evidence', u12['urban']['movements'])
        self.assertEqual(u12['urban']['queue']['attribution'], 'route')
        u1 = mc.apply_urban_batch1(base, ('U1',))
        for doc in (u13, u12, u1):
            self.assertEqual(doc['urban']['beta'], full['urban']['beta'])
            self.assertEqual(doc['urban']['ramp'], full['urban']['ramp'])
            # the SC7 declaration correction belongs to U1 (the table's values need it)
            for key in ('nonexistent_declaration', 'physical_phase_authority'):
                self.assertEqual(doc['urban']['movements'][key], full['urban']['movements'][key])
            self.assertEqual(doc['control_area_objective'], full['control_area_objective'])
        for bad in (('U2', 'U3'), ('U1', 'U4'), ('U1', 'U1')):
            with self.assertRaises(ValueError):
                mc.apply_urban_batch1(base, bad)
        self.assertEqual(mc.urban_batch1_out().name, 'config_n31_v2_urban_b1.json')
        self.assertEqual(mc.urban_batch1_out(('U3', 'U1')).name, 'config_n31_v2_urban_b1_u1u3.json')


if __name__ == '__main__':
    unittest.main()
