"""Address-only actual mapping + synthetic callback tests. No model imports.

The actual writer's two pure DSD catalog functions and existing address-fixture
setup are compiled from AST. Meter quantization/physical payloads are explicitly
synthetic; this is not canonical meter realization or a controller integration.
"""
import ast
import copy
from dataclasses import replace
import json
import math
from pathlib import Path
import sys
import subprocess
from types import SimpleNamespace
from typing import Any, Mapping
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.controllers import joint_owner_game as canonical_game
from evaluation.controllers import joint_owner_neighbors as canonical_neighbors


def address_fixture():
    owner = canonical_game
    adapter = ROOT / 'evaluation/controllers/vissim_stackelberg_adapter.py'
    tree = ast.parse(adapter.read_text(encoding='utf-8'))
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name in ('_as_float', '_segment_dsd_controls')]
    if len(functions) != 2:
        raise AssertionError('Pure actual writer catalog boundary changed')
    env = {'Any': Any, 'Mapping': Mapping}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(adapter), 'exec'), env)
    path = ROOT / 'diagnostics/test_joint_owner_addresses.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    fixture = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'OwnerAddressesTests')
    fixture.body = [n for n in fixture.body if isinstance(n, ast.FunctionDef) and n.name in ('setUp', 'build')]
    if len(fixture.body) != 2:
        raise AssertionError('Address fixture boundary changed')
    env = {'ROOT': ROOT, 'SimpleNamespace': SimpleNamespace, 'json': json, 'copy': copy,
           'unittest': unittest, 'proposed': owner, '_segment_dsd_controls': env['_segment_dsd_controls']}
    exec(compile(ast.Module(body=[fixture], type_ignores=[]), str(path), 'exec'), env)
    obj = env['OwnerAddressesTests'](); obj.setUp()
    # Effective JSON values, not an inferred/default VSL domain.
    configured = json.loads((ROOT / 'diagnostics/contract_candidate_configs_v4/n7_area_beta300.json').read_text(encoding='utf-8-sig'))
    obj.cfg.freeway_follower = SimpleNamespace(vsl_set=configured['config_overrides']['freeway_follower']['vsl_set'])
    helper = canonical_neighbors
    return obj, owner, helper


class FreewayNeighborsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture, cls.owner_helper, cls.helper = address_fixture()
        cls.catalog = cls.fixture.build()

    def setUp(self):
        self.cfg = copy.deepcopy(self.fixture.cfg)
        self.old = {field: {} for field in self.owner_helper.LEVER_FIELDS}
        for a in self.catalog.addresses:
            self.old[a.field][a.key] = 0.0 if a.role == 'fixed_dead' or a.field == 'offsets' else (120.0 if a.field == 'vsl' else 30.0)
        for direction in ('FW_E', 'FW_W'):
            for i in range(21):
                self.old['vsl'][f'{direction}__seg{i}'] = (100.0, 120.0, 80.0, 120.0)[min(i // 5, 3)]
            self.old['vsl'][direction] = 80.0
        self.old['ramp_metering'] = {r: 1000.0 for r in self.cfg.network.ramp_to_freeway}
        self.old.update(N_P_star=2.0, N_UF_star=2000.0, diagnostics={})
        self.before = copy.deepcopy(self.old)

    def tearDown(self):
        self.assertEqual(self.old, self.before)

    def test_actual_canonical_exports_and_fresh_process_without_model_bootstrap(self):
        from diagnostics import joint_urban_neighbors_candidate as urban_compat
        from diagnostics import joint_freeway_neighbors_candidate as freeway_compat
        for compatibility, names in (
                (urban_compat, ('generate_urban_requests', 'realize_urban_requests')),
                (freeway_compat, ('Domain', 'generate', 'owner_physical_fingerprints'))):
            for name in names:
                actual = getattr(canonical_neighbors, name)
                self.assertIs(getattr(compatibility, name), actual)
                self.assertEqual(actual.__module__, 'evaluation.controllers.joint_owner_neighbors')
        # A previous test may legitimately have imported a model. Test the actual
        # import boundary in a fresh process, independent of suite ordering.
        code = """
import json
from pathlib import Path
import sys
root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
from evaluation.controllers import joint_owner_game, joint_owner_neighbors
assert Path(joint_owner_neighbors.__file__).resolve() == root / 'evaluation/controllers/joint_owner_neighbors.py'
assert Path(joint_owner_game.__file__).resolve() == root / 'evaluation/controllers/joint_owner_game.py'
for name in joint_owner_neighbors.__all__:
    assert getattr(joint_owner_neighbors, name).__module__ == joint_owner_neighbors.__name__
assert not any(name == 'src' or name.startswith('src.') for name in sys.modules)
assert 'evaluation.controllers.vissim_stackelberg_adapter' not in sys.modules
print(json.dumps({'actual_canonical_import': True, 'model_bootstrap': False}))
"""
        result = subprocess.run(
            [sys.executable, '-I', '-B', '-X', 'utf8', '-c', code, str(ROOT)],
            cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout),
                         {'actual_canonical_import': True, 'model_bootstrap': False})

    def ramps(self, direction='FW_E'):
        return tuple(a.key for a in self.catalog.addresses if a.owner == direction and a.field == 'ramp_metering')

    def domain(self, direction='FW_E'):
        r1, r2 = self.ramps(direction)
        return self.helper.Domain(
            head_values={0: (80.0, 100.0), 5: (100.0, 120.0), 10: (80.0, 100.0)},
            meter_points=(('one', {r1: 800.0, r2: 1000.0}), ('two', {r1: 900.0, r2: 1100.0})),
            joint_pairs=((0, 80.0, 'two'),), held_horizon_sec=150.0,
            budget_mode='none', budget_veh_h=None, budget_tolerance_veh_h=1e-9,
            provenance={'test': 'synthetic frozen branch domain; not a runtime extractor'})

    def rows(self, control):
        out = {}
        for kind, identity, owner, key in self.catalog.writes:
            if kind == 'dsd': payload = ('vsl', control['vsl'][key])
            elif owner.startswith('FW_'): payload = ('synthetic_meter', control['ramp_metering'][key])
            else: payload = ('synthetic_signal', tuple(control['green_times'][f'{owner}_p{i}'] for i in range(1, 5)), control['offsets'][owner])
            out[kind, identity] = payload
        return out

    @staticmethod
    def admit(_control):
        return {'feasible': True, 'scope': 'synthetic callback'}

    def generate(self, *, direction='FW_E', domain=None, incumbent=None, **callbacks):
        args = dict(requested_admissible=self.admit, realize=lambda x: x,
                    realized_admissible=self.admit, physical_rows=self.rows)
        args.update(callbacks)
        return self.helper.generate(self.catalog, self.cfg, direction, self.old if incumbent is None else incumbent,
                                    self.domain(direction) if domain is None else domain, **args)

    def test_actual_mapping_and_nonuniform_full_vector(self):
        self.assertEqual(len(self.catalog.owners), 19)
        self.assertEqual(len(self.catalog.writes), 213)
        self.assertEqual(sum(w[0] == 'dsd' for w in self.catalog.writes), 66)
        self.assertEqual(sum(a.field == 'vsl' for a in self.catalog.addresses), 44)
        for direction in ('FW_E', 'FW_W'):
            result = self.generate(direction=direction)
            self.assertTrue(result['incumbent_feasible'])
            self.assertEqual(result['requested_count'], 10)
            self.assertEqual(len(result['candidates']), 7)
            for candidate in result['candidates']:
                self.owner_helper.assert_owner_transition(self.catalog, direction, self.old, candidate['control'])
                self.assertEqual(candidate['owner_vector']['vsl_heads'][15], 120.0)
                self.assertEqual(set(candidate['owner_vector']['meter_veh_h']), set(self.ramps(direction)))
            joint = next(c for c in result['candidates'] if any(a['alias'] == 'joint:0' for a in c['aliases']))
            self.assertEqual(list(joint['owner_vector']['vsl_heads'].values()), [80.0, 120.0, 80.0, 120.0])
            self.assertEqual(tuple(joint['owner_vector']['meter_veh_h'].values()), (900.0, 1100.0))
            self.assertEqual(joint['control']['vsl']['FW_W' if direction == 'FW_E' else 'FW_E'], 80.0)

    def test_post_quantization_dedup_retains_request_aliases(self):
        r1, r2 = self.ramps()
        domain = replace(self.domain(), head_values={0: (), 5: (), 10: ()}, joint_pairs=(),
                         meter_points=(('a', {r1: 1001.0, r2: 1000.0}), ('b', {r1: 1002.0, r2: 1000.0})))
        def quantize(control):
            for r in (r1, r2): control['ramp_metering'][r] = round(control['ramp_metering'][r] / 100.0) * 100.0
            control['diagnostics']['synthetic_quantized'] = True
            return control
        result = self.generate(domain=domain, realize=quantize)
        self.assertEqual(len(result['candidates']), 1)
        self.assertEqual([x['alias'] for x in result['candidates'][0]['aliases']], ['incumbent', 'meter:a', 'meter:b'])
        self.assertEqual(result['candidates'][0]['aliases'][1]['request']['ramp_metering'][r1], 1001.0)

    def test_same_physical_different_model_refuses_unsafe_dedup(self):
        fixed = self.rows(self.old)
        with self.assertRaisesRegex(ValueError, 'unsafe deduplication'):
            self.generate(physical_rows=lambda x: fixed)

    def test_realized_equality_is_empty_not_silent_projection(self):
        domain = replace(self.domain(), budget_mode='equality', budget_veh_h=2001.0)
        result = self.generate(domain=domain)
        self.assertEqual(result['status'], 'empty_infeasible')
        self.assertFalse(result['incumbent_feasible'])
        self.assertEqual(len(result['rejected']), result['requested_count'])
        self.assertTrue(all(r['budget_residual_veh_h'] != 0 for r in result['rejected']))
        valid = self.generate(domain=replace(domain, budget_veh_h=2000.0))
        self.assertTrue(valid['incumbent_feasible'])
        self.assertTrue(all(sum(c['owner_vector']['meter_veh_h'].values()) == 2000.0 for c in valid['candidates']))
        cap = self.generate(domain=replace(domain, budget_mode='cap', budget_veh_h=1900.0))
        self.assertFalse(cap['incumbent_feasible'])
        self.assertTrue(all(sum(c['owner_vector']['meter_veh_h'].values()) <= 1900.0 for c in cap['candidates']))

    def test_revisit_and_callback_evidence_and_no_shared_candidates(self):
        result = self.generate(requested_admissible=lambda c: {'feasible': True, 'side': 'request'},
                               realized_admissible=lambda c: {'feasible': True, 'side': 'realized'})
        moved = next(c['control'] for c in result['candidates'] if c['owner_vector']['vsl_heads'][0] == 80.0)
        revisit = self.generate(incumbent=moved)
        self.assertTrue(any(c['owner_vector']['vsl_heads'][0] == 100.0 for c in revisit['candidates']))
        aliases = result['candidates'][0]['aliases']
        self.assertEqual(aliases[0]['request_evidence']['side'], 'request')
        self.assertEqual(aliases[0]['realized_evidence']['side'], 'realized')
        result['candidates'][0]['control']['diagnostics']['local'] = True
        self.assertTrue(all('local' not in c['control']['diagnostics'] for c in result['candidates'][1:]))

    def test_constraints_mutations_and_nonfinite_fail_closed(self):
        for head_values in ({0: (90.0,), 5: (), 10: ()}, {False: (), 5: (), 10: ()}, {0: (float('nan'),), 5: (), 10: ()}, {0: (), 5: (), 15: ()}):
            with self.subTest(head_values=head_values), self.assertRaises(ValueError):
                self.generate(domain=replace(self.domain(), head_values=head_values))
        for field, key, value in (('vsl', 'FW_W__seg0', 80.0), ('vsl', 'FW_E__seg15', 80.0),
                                  ('vsl', 'FW_E__seg0', 90.0), ('ramp_metering', self.ramps()[0], -1.0)):
            def bad(control): control[field][key] = value; return control
            with self.subTest(field=field, key=key), self.assertRaises(ValueError): self.generate(realize=bad)
        def bad_context(control): control['N_UF_star'] += 1.0; return control
        with self.assertRaisesRegex(ValueError, 'non-lever'): self.generate(realize=bad_context)
        def bad_admit(control): control['ramp_metering'][self.ramps()[0]] += 1.0; return {'feasible': True}
        with self.assertRaisesRegex(ValueError, 'callback mutated'): self.generate(requested_admissible=bad_admit)

    def test_physical_foreign_recovery_and_callback_copy(self):
        key = next((k, i) for k, i, owner, action in self.catalog.writes if owner == 'FW_E' and action == 'FW_E__seg15')
        for changed_key in (key, next((k, i) for k, i, owner, action in self.catalog.writes if owner == 'FW_W')):
            calls = [0]
            def bad_rows(control):
                calls[0] += 1
                rows = self.rows(control)
                control['diagnostics']['writer_side_effect'] = True
                if calls[0] > 1: rows[changed_key] = ('changed',)
                return rows
            with self.subTest(changed_key=changed_key), self.assertRaisesRegex(ValueError, 'foreign/fixed|already-realized incumbent'):
                self.generate(physical_rows=bad_rows)
        def throws(control): control['diagnostics']['touched'] = True; raise RuntimeError('synthetic failed')
        with self.assertRaisesRegex(RuntimeError, 'synthetic failed'): self.generate(realize=throws)

    def test_realized_sum_mode_changes_only_derived_scalar_and_preserves_budget(self):
        initial = copy.deepcopy(self.old)
        initial['N_UF_star'] = math.fsum(initial['ramp_metering'][r] for r in sorted(initial['ramp_metering']))
        domain = replace(self.domain(), nuf_semantics='realized_sum')
        frozen_domain = copy.deepcopy(domain)
        def realize(control):
            control['N_UF_star'] = math.fsum(control['ramp_metering'][r] for r in sorted(control['ramp_metering']))
            return control
        result = self.generate(incumbent=initial, domain=domain, realize=realize)
        self.assertTrue(result['incumbent_feasible'])
        self.assertTrue(any(c['control']['N_UF_star'] != initial['N_UF_star'] for c in result['candidates']))
        for candidate in result['candidates']:
            control = candidate['control']
            self.assertEqual(control['N_UF_star'], math.fsum(control['ramp_metering'][r] for r in sorted(control['ramp_metering'])))
            self.assertEqual(control['N_P_star'], initial['N_P_star'])
            self.owner_helper.assert_owner_transition(self.catalog, 'FW_E', initial, control)
        self.assertEqual(domain, frozen_domain)
        # Equality still constrains the original owner budget, independently of
        # the full-vector derived action scalar.
        equality = replace(domain, budget_mode='equality', budget_veh_h=2000.)
        constrained = self.generate(incumbent=initial, domain=equality, realize=realize)
        self.assertTrue(any(r['stage'] == 'realized' and r['budget_residual_veh_h'] == -200.
                            for r in constrained['rejected']))
        self.assertTrue(all(sum(c['control']['ramp_metering'][r] for r in self.ramps()) == 2000.
                            for c in constrained['candidates']))
        with self.assertRaisesRegex(ValueError, 'non-lever action context'):
            self.generate(incumbent=initial, realize=realize)

    def test_realized_sum_rejects_bad_incumbent_realizer_and_np_changes(self):
        domain = replace(self.domain(), nuf_semantics='realized_sum')
        with self.assertRaisesRegex(ValueError, 'exact realized full meter sum'):
            self.generate(domain=domain)
        initial = copy.deepcopy(self.old); initial['N_UF_star'] = 4000.
        for value in (3999., float('nan'), True):
            def bad(control): control['N_UF_star'] = value; return control
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.generate(domain=domain, incumbent=initial, realize=bad)
        def np_change(control): control['N_P_star'] += 1.; return control
        with self.assertRaisesRegex(ValueError, 'non-lever action context'):
            self.generate(domain=domain, incumbent=initial, realize=np_change)
        with self.assertRaisesRegex(ValueError, 'nuf_semantics'):
            self.generate(domain=replace(domain, nuf_semantics='unchecked'), incumbent=initial)

    def test_rejection_records_and_full_two_meter_domain(self):
        reject = self.generate(requested_admissible=lambda c: {'feasible': False, 'reason': 'caller current trust'})
        self.assertEqual(reject['status'], 'empty_infeasible')
        self.assertTrue(all(r['stage'] == 'requested' for r in reject['rejected']))
        with self.assertRaisesRegex(ValueError, 'two-meter'):
            self.generate(domain=replace(self.domain(), meter_points=(('bad', {self.ramps()[0]: 2000.0}),)))
        with self.assertRaisesRegex(ValueError, 'explicit feasible'):
            self.generate(realized_admissible=lambda c: {})

    def test_incumbent_realization_cannot_change_rate_or_schedule(self):
        domain = replace(self.domain(), head_values={0: (), 5: (), 10: ()}, meter_points=(), joint_pairs=())
        ramp = self.ramps()[0]
        def change_rate(control): control['ramp_metering'][ramp] += 100.0; return control
        with self.assertRaisesRegex(ValueError, 'already-realized incumbent'):
            self.generate(domain=domain, realize=change_rate)
        key = next((kind, identity) for kind, identity, owner, source in self.catalog.writes
                   if owner == 'FW_E' and source == ramp)
        def diag_change(control): control['diagnostics']['synthetic_schedule'] = True; return control
        def changed_rows(control):
            rows = self.rows(control)
            if control['diagnostics'].get('synthetic_schedule'): rows[key] = ('different physical schedule',)
            return rows
        with self.assertRaisesRegex(ValueError, 'already-realized incumbent'):
            self.generate(domain=domain, realize=diag_change, physical_rows=changed_rows)
        # Bookkeeping alone is permitted when every control and command agrees.
        same = self.generate(domain=domain, realize=diag_change)
        self.assertTrue(same['incumbent_feasible'])
        self.assertEqual(same['candidates'][0]['physical_rows'], self.rows(self.old))

    def test_owner_physical_tokens_match_core_contract(self):
        result = self.generate()
        base = self.helper.owner_physical_fingerprints(self.catalog, self.rows(self.old))
        self.assertEqual(set(base), set(self.catalog.owners))
        self.assertTrue(all(type(v) is str and len(v) == 64 for v in base.values()))
        for candidate in result['candidates']:
            tokens = candidate['owner_physical_sha256']
            self.assertEqual(tokens, self.helper.owner_physical_fingerprints(self.catalog, candidate['physical_rows']))
            self.assertTrue(all(tokens[owner] == base[owner] for owner in self.catalog.owners if owner != 'FW_E'))
        rows = self.rows(self.old)
        key = next((kind, identity) for kind, identity, owner, source in self.catalog.writes
                   if owner == 'FW_E' and source == self.ramps()[0])
        rows[key] = ('same model rate, different native schedule',)
        changed = self.helper.owner_physical_fingerprints(self.catalog, rows)
        self.assertNotEqual(changed['FW_E'], base['FW_E'])
        self.assertTrue(all(changed[owner] == base[owner] for owner in base if owner != 'FW_E'))
        del rows[key]
        with self.assertRaisesRegex(ValueError, 'catalog differs'):
            self.helper.owner_physical_fingerprints(self.catalog, rows)


class CurrentFreewayDomainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        FreewayNeighborsTests.setUpClass()
        # Execute only the original metering method with an inert local-cost
        # recorder. No source model, dynamics or solver module is imported.
        import numpy as np
        source = ROOT / 'vendor/NumSim-mine/src/controllers/wu_faithful_follower.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        owner = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'WuFaithfulFollower')
        node = next(n for n in owner.body if isinstance(n, ast.FunctionDef) and n.name == '_solve_freeway_agent_metered')
        env = {'np': np, 'ControlAction': SimpleNamespace}
        future = ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[future, node], type_ignores=[])), str(source), 'exec'), env)
        cls.original_metered = staticmethod(env['_solve_freeway_agent_metered'])

    def setUp(self):
        base = FreewayNeighborsTests()
        base.setUp()
        self.base = base
        self.cfg, self.ownership = base.cfg, base.catalog
        self.initial = copy.deepcopy(base.old)
        self.initial['N_UF_star'] = 4000.
        self.previous = copy.deepcopy(self.initial)
        self.cfg.network.ramps = tuple(self.cfg.network.ramp_to_freeway)
        self.cfg.network.freeway_vsl_zone_of_cell = {d: [min(i // 5, 3) for i in range(21)] for d in ('FW_E', 'FW_W')}
        self.cfg.mpc = SimpleNamespace(wu_faithful_nuf_coordination_mode='dual',
            baseline_move_box=True, leader_budget_off=False, relaxed_quantized_controls=True, horizon_steps=3)
        self.cfg.freeway_follower.max_vsl_step = 40.
        self.cfg.freeway_follower.vsl_sequence_search = True
        self.cfg.freeway_follower.freeway_prediction_horizon_steps = 3
        self.cfg.network.ramp_capacity_veh_h = {r: 1800. for r in self.cfg.network.ramps}
        current = [self.initial['vsl'][f'FW_E__seg{i}'] for i in range(21)]
        lower = [80. if i < 5 else value for i, value in enumerate(current)]
        self.state = SimpleNamespace(time_sec=900., freeway_density={'FW_E': [30.] * 21},
                                     source_vectors=[current, lower])
        class WuFixture:
            def _relaxed_freeway_segment_candidates(self, link, n, state, coupling, previous, demand):
                self._repair_diagnostics['queries'] += 1
                state.lane_profile_initialized = True
                coupling['private_source_diagnostic'] = 1.
                demand.private_source_diagnostic = 1.
                return copy.deepcopy(state.source_vectors)
        class FollowerFixture:
            def _freeway_vsl_sequence_candidates(self, link, n, previous, base, horizon):
                return [[list(vector) for _ in range(horizon)] for vector in base]
        FollowerFixture._freeway_vsl_sequence_candidates._rw_vsl_kbest = True
        self.follower = FollowerFixture()
        self.follower.cfg = self.cfg
        self.follower._wu = WuFixture()
        self.follower._wu._omega_f = {'FW_E': .5, 'FW_W': .5}
        self.follower._wu._repair_diagnostics = {'queries': 0}
        for key, value in dict(ramp_metering_fractions=(1., .7, .5, .35, .25),
                metering_marginal_price=None, metering_marginal_price_ref={},
                metering_marginal_price_trust_frac=None, metering_release_certified=None,
                metering_price_split=False, _lambda_UF=0., metering_marginal_price_weight=1.,
                metering_budget_penalty_weight=0., vsl_marginal_price=None,
                vsl_marginal_price_ref={}, vsl_marginal_price_trust_kmh=None).items():
            setattr(self.follower, key, value)
        self.leader = SimpleNamespace(N_UF_star=4000.)
        self.coupling, self.demand = {'p_down_FW_E': .2}, SimpleNamespace(incident_capacity_factor=1.)

    def build(self, **overrides):
        kwargs = dict(ownership=self.ownership, held_horizon_sec=450., budget_tolerance_veh_h=1e-9,
                      joint_pairs=(), nuf_semantics='realized_sum',
                      context_provenance={'test': 'explicit synthetic frozen source and runtime scope'})
        kwargs.update(overrides)
        return canonical_neighbors.build_current_freeway_domain(
            self.follower, 'FW_E', self.state, self.coupling, self.demand,
            self.initial, self.leader, self.previous, **kwargs)

    def test_installed_source_reuse_order_private_repair_and_explicit_joint_pairs(self):
        before = copy.deepcopy((self.initial, self.previous, vars(self.state), vars(self.cfg.mpc)))
        domain = self.build()
        self.assertEqual(domain.head_values, {0: (100., 80.), 5: (120.,), 10: (80.,)})
        self.assertEqual(domain.held_horizon_sec, 450.)
        self.assertEqual(domain.provenance['source_horizon_steps'], 3)
        self.assertFalse(domain.provenance['legacy_sequential_search_equivalent'])
        self.assertFalse(domain.provenance['shared_feasibility_certified'])
        self.assertEqual(self.follower._wu._repair_diagnostics, {'queries': 0})
        self.assertNotIn('private_source_diagnostic', self.coupling)
        self.assertFalse(hasattr(self.demand, 'private_source_diagnostic'))
        self.assertEqual(before, (self.initial, self.previous, vars(self.state), vars(self.cfg.mpc)))
        pair = (0, 80., domain.meter_points[-1][0])
        combined = self.build(joint_pairs=(pair,))
        self.assertEqual(combined.joint_pairs, (pair,))
        domain.provenance['query_context']['test'] = 'changed private result'
        self.assertNotEqual(domain.provenance, combined.provenance)
        with self.assertRaisesRegex(ValueError, 'outside current'):
            self.build(joint_pairs=((0, 60., pair[2]),))

    def test_meter_extraction_matches_original_fixed_seed_in_all_source_branches(self):
        ramps = self.base.ramps()
        cases = ('dual_box', 'dual_fraction', 'priced_dual', 'priced_cap', 'priced_equality',
                 'cap', 'equality', 'split_equality', 'pfo', 'pfo_cert_trust', 'budget_off')
        for case in cases:
            with self.subTest(case=case):
                self.setUp()
                f = self.follower
                m = self.cfg.mpc
                if case == 'dual_fraction': m.baseline_move_box = False
                if 'cap' in case: m.wu_faithful_nuf_coordination_mode = 'cap'; self.leader.N_UF_star = 3000.
                if 'equality' in case: m.wu_faithful_nuf_coordination_mode = 'equality'; self.leader.N_UF_star = 2900.
                if case.startswith('priced') or case in ('pfo_cert_trust', 'split_equality'):
                    f.metering_marginal_price = {r: 0. for r in ramps}
                    f.metering_marginal_price_ref = {r: 1100. for r in ramps}
                    f.metering_release_certified = {ramps[0]: False, ramps[1]: True}
                    f.metering_marginal_price_trust_frac = .01
                if case.startswith('pfo'): self.leader = None
                if case == 'budget_off': m.leader_budget_off = True
                if case == 'split_equality': f.metering_price_split = True
                recorded = []
                def local(link, state, coupling, demand, previous):
                    recorded.append({r: previous.ramp_metering[r] for r in ramps})
                    return {}, 0., 1
                f._solve_freeway_agent_local = local
                self.original_metered(f, 'FW_E', self.state, self.coupling, self.demand,
                    SimpleNamespace(**copy.deepcopy(self.initial)), self.leader,
                    SimpleNamespace(**copy.deepcopy(self.previous)))
                domain = self.build()
                self.assertEqual([point for _, point in domain.meter_points], recorded)
                self.assertEqual(domain.budget_mode, case if case in ('cap', 'equality') else 'equality' if case == 'split_equality' else 'none')
                self.assertEqual(domain.provenance['meter']['leader_target_nuf_veh_h'],
                                 0. if self.leader is None else self.leader.N_UF_star)

    def test_vsl_price_trust_preserves_empty_fallback_and_rechecks_projection(self):
        f = self.follower
        f.vsl_marginal_price = {'FW_E__seg0': 1.}
        f.vsl_marginal_price_ref = {'FW_E__seg0': 80.}
        f.vsl_marginal_price_trust_kmh = 0.
        kept = self.build()
        self.assertEqual(kept.head_values[0], (80.,))
        self.assertEqual(kept.head_values[5], ())
        self.assertFalse(kept.provenance['vsl_empty_trust_fallback'])
        f.vsl_marginal_price_ref = {'FW_E__seg0': 60.}
        fallback = self.build()
        self.assertEqual(fallback.head_values[0], (100., 80.))
        self.assertTrue(fallback.provenance['vsl_empty_trust_fallback'])

    def test_vsl_snapshot_and_meter_previous_commit_have_distinct_anchors(self):
        class SnapshotWu(type(self.follower._wu)):
            def _relaxed_freeway_segment_candidates(self, link, n, state, coupling, previous, demand):
                # Like legacy _solve_with, this argument must be the current
                # full snapshot, even when the committed previous differs.
                return [[previous['vsl'][f'{link}__seg{i}'] for i in range(n)]]
        self.follower._wu.__class__ = SnapshotWu
        for i in range(5):
            self.previous['vsl'][f'FW_E__seg{i}'] = 80.
        ramp = self.base.ramps()[0]
        self.previous['ramp_metering'][ramp] = 800.
        domain = self.build()
        self.assertEqual(domain.head_values[0], (100.,))
        self.assertEqual(domain.provenance['vsl_snapshot_heads'][0], 100.)
        self.assertEqual(domain.provenance['meter']['previous_box'][ramp], (500., 1100.))
        self.assertEqual(domain.provenance['meter']['box_points'][ramp], [1100., 950., 800., 650., 500.])

    def test_unsupported_source_recovery_step_and_stale_sum_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'provenance'):
            self.build(context_provenance={})
        self.cfg.mpc.relaxed_quantized_controls = False
        with self.assertRaisesRegex(ValueError, 'relaxed temporal'):
            self.build()
        self.cfg.mpc.relaxed_quantized_controls = True
        self.state.source_vectors[0][15] = 100.
        with self.assertRaisesRegex(ValueError, 'zone aliases or fixed recovery'):
            self.build()
        self.setUp()
        self.cfg.freeway_follower.max_vsl_step = 10.
        with self.assertRaisesRegex(ValueError, 'snapshot step'):
            self.build()
        self.setUp()
        self.initial['N_UF_star'] = 3999.
        with self.assertRaisesRegex(ValueError, 'exact realized'):
            self.build()


if __name__ == '__main__':
    unittest.main()
