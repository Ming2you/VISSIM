"""Installed production module plus archived original-method fixtures.

Both execute against tiny explicit storage/substep stubs. Production is loaded
from its actual path; its vendor import is supplied by a strict fixture hook.
No actual METANET, installed hooks, worker or GNE equivalence is established.
"""
from __future__ import annotations
import ast
import builtins
from collections.abc import Mapping
import copy
import __future__
import math
import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
import zipfile

from diagnostics import prepare_fixed_freeway_query_patch_v2 as producer


class Action:
    def __init__(self, *, tag='rollout', **fields):
        self.__dict__.update(fields)
        self.tag = tag


def method_namespace(source, vendor, landing):
    if source == producer.SOURCE.read_text(encoding='utf-8'):
        # Load the actual installed module. Stub only dependencies of the local
        # loop; no AST rewriting of the production function under test.
        native_import = builtins.__import__
        def fixture_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == 'src.controllers' and tuple(fromlist) == ('wu_faithful_follower',):
                return NS(wu_faithful_follower=vendor)
            if name not in ('__future__', 'collections', 'collections.abc', 'math', 'types', 'typing'):
                raise AssertionError('Unexpected model/runtime import: ' + name)
            return native_import(name, globals, locals, fromlist, level)
        spec = importlib.util.spec_from_file_location('_installed_fixed_fw_fixture', producer.SOURCE)
        module = importlib.util.module_from_spec(spec)
        module.__dict__['__builtins__'] = {**vars(builtins), '__import__': fixture_import}
        spec.loader.exec_module(module)
        module.LocalLandingState = landing
        return module.__dict__
    wanted = {'solve_freeway_agent_local', '_freeway_query_setup',
              'evaluate_fixed_freeway_candidate', '_evaluate_freeway_sequences'}
    nodes = [copy.deepcopy(n) for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    class StubVendorImport(ast.NodeTransformer):
        def visit_ImportFrom(self, node):
            if node.module == 'src.controllers':
                if [(alias.name, alias.asname) for alias in node.names] != [('wu_faithful_follower', 'vendor')]:
                    raise AssertionError('Unexpected production import extraction')
                return ast.copy_location(ast.Pass(), node)
            return node  # Any other executed import is blocked below.
    tree = ast.fix_missing_locations(StubVendorImport().visit(ast.Module(body=nodes, type_ignores=[])))
    def no_import(*args, **kwargs):
        raise AssertionError('A model import was attempted by a pure fixture')
    scope = {'math': math, 'Mapping': Mapping, 'vendor': vendor, 'LocalLandingState': landing,
             '__builtins__': {**vars(builtins), '__import__': no_import}}
    exec(compile(tree, '<isolated-freeway-methods>', 'exec', flags=__future__.annotations.compiler_flag), scope)
    return scope


def fixture(*, mutate_during_enumeration=False, substep_vehicles=None):
    log = []
    reference = Action(tag='reference', vsl={'FW_E': 110.0, 'FW_E__seg0': 110.0, 'FW_E__seg1': 100.0},
                       ramp_metering={'R': 12.0}, green_times={'SC1_p1': 20.0}, offsets={'SC1': 3.0})
    candidate = Action(tag='candidate', vsl={'FW_E': 80.0, 'FW_E__seg0': 80.0, 'FW_E__seg1': 90.0},
                       ramp_metering={'R': 25.0}, green_times={'SC1_p1': 25.0}, offsets={'SC1': 4.0})
    net = NS(local_landing_state=True, freeway_lanes=3, freeway_buffer_segments=0,
             ramp_queue_cap=lambda ramp: 100.0)
    ff = NS(freeway_prediction_horizon_steps=1, vsl_set=(80.0, 90.0, 100.0, 110.0), vsl_smoothness_weight=.001)
    cfg = NS(network=net, freeway_follower=ff, simulation=NS(T_f_h=.1, T_c_h=.1, K_cf=1),
             mpc=NS(horizon_steps=1, relaxed_quantized_controls=False,
                    follower_terminal_cost_enabled=False, protected_queue_movement='', protected_queue_weight=0.0))
    model = NS(n_seg=2, owned_ramps=('R',), owned_offramps=('OR',))
    state = NS(freeway_density={'FW_E': [1., 2.]}, freeway_speed={'FW_E': [60., 70.]},
               freeway_effective_lanes={'FW_E': [3., 3.]}, mainline_origin_queue={'FW_E': 0.},
               ramp_queue={'R': 0.}, urban_movement_queue={})
    wu = NS(_last_offramp_flow={'unrelated': 99.}, _has_last_offramp_flow=False)
    def enumerate_candidates(link, n_seg, previous):
        log.append(('enumerate', link, n_seg))
        if mutate_during_enumeration:
            # Same raw setup must be retained even if existing candidate code
            # mutates a nested config value or the previous command in place.
            ff.freeway_prediction_horizon_steps = 2
            ff.vsl_smoothness_weight = 999.
            cfg.simulation.T_f_h = .7
            previous.vsl['FW_E__seg0'] = 5.
        return [[100., 110.], [80., 90.]]
    wu._freeway_segment_candidates = enumerate_candidates
    wu._relaxed_freeway_segment_candidates = lambda *args: enumerate_candidates(args[0], args[1], args[4])
    def sequences(link, n_seg, previous, candidates, horizon):
        log.append(('sequences', horizon))
        return [[list(row) for _ in range(horizon)] for row in candidates]
    owner = NS(cfg=cfg, _local_freeway_models={'FW_E': model}, _wu=wu,
               _freeway_vsl_sequence_candidates=sequences,
               _local_ramp_release=lambda *args: {'R': 0.}, count_blocked_ramp_inflow=False,
               vsl_marginal_price=None, vsl_marginal_price_trust_kmh=None,
               vsl_marginal_price_ref={}, vsl_marginal_price_weight=1.,
               vsl_meter_cross_price=None, vsl_meter_cross_ref={}, vsl_meter_cross_weight=1.,
               price_smoothness_disabled=False,
               _last_local_landing_diagnostics={'unrelated': {'keep': True}})
    def segment_vsl(control, link, index, config):
        value = control.vsl[f'{link}__seg{index}']
        log.append(('segment_vsl', control.tag, index, value))
        return value
    def substep(model, rhos, speeds, lanes, occupancy, origin, ramp_release, capacity, control, demand, *, buffer_bc):
        vector = tuple(control.vsl[f'FW_E__seg{i}'] for i in range(2))
        log.append(('substep', vector, dict(control.ramp_metering), dict(control.green_times), dict(control.offsets)))
        vehicles = sum(vector) / 100. if substep_vehicles is None else substep_vehicles
        return rhos, speeds, lanes, origin, {'OR': 7.}, [vehicles]
    class Landing:
        def __init__(self, follower, local_model, initial_state):
            self.stock = {'OR': 1.}
            self.initial_stock = 1.
            self.ledger = {'max_abs_residual_veh': 0.}
            self.replaced_coupling = {}
        def advance(self, control, ramp_q, dt_h):
            log.append(('advance', dt_h))
        def capacities(self, dt_h):
            return {'OR': 100.}
        def occupancy(self):
            return dict(self.stock)
        def land(self, flow, dt_h):
            pass
    vendor = NS(ControlAction=Action, segment_vsl=segment_vsl, freeway_substep_local=substep)
    return owner, state, {}, NS(), reference, candidate, vendor, Landing, log


class FixedFreewayV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        archive = producer.ROOT / 'diagnostics/fixed_freeway_query_installed_v1/baseline_source.zip'
        with zipfile.ZipFile(archive) as bundle:
            raw = bundle.read('link_predictor.py')
        if hashlib.sha256(raw).hexdigest() != producer.EXPECTED:
            raise ValueError('Archived pre-extraction predictor SHA differs')
        cls.original = raw.decode('utf-8')
        cls.revised = producer.SOURCE.read_text(encoding='utf-8')

    def test_01_source_shape_install_and_non_target_functions_unchanged(self):
        a, b = ast.parse(self.original), ast.parse(self.revised)
        def other(tree):
            return [ast.dump(node, include_attributes=False) for node in tree.body
                    if not (isinstance(node, ast.FunctionDef) and node.name in {
                        'solve_freeway_agent_local', '_freeway_query_setup', 'evaluate_fixed_freeway_candidate', '_evaluate_freeway_sequences',
                        'shared_freeway_landing_links', 'score_shared_freeway_response',
                        'shared_freeway_approach_source_contract', '_shared_freeway_approach_quantities',
                        '_freeway_residence_increment', '_freeway_base_tail_cost'})]
        self.assertEqual(other(a), other(b))
        setup = next(node for node in b.body if isinstance(node, ast.FunctionDef) and node.name == '_freeway_query_setup')
        original_solve = next(node for node in a.body if isinstance(node, ast.FunctionDef) and node.name == 'solve_freeway_agent_local')
        candidate_index = next(i for i, node in enumerate(original_solve.body)
                               if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                               and node.targets[0].id == 'candidates')
        old_setup = original_solve.body[1:candidate_index]
        self.assertEqual([ast.dump(n) for n in old_setup], [ast.dump(n) for n in setup.body[1:-1]])
        self.assertEqual(len(producer.SETUP_NAMES), 13)

    def legacy(self, source, **options):
        owner, state, coupling, demand, ref, cand, vendor, landing, log = fixture(**options)
        ns = method_namespace(source, vendor, landing)
        result = ns['solve_freeway_agent_local'](owner, 'FW_E', state, coupling, demand, ref)
        return result, owner._wu._last_offramp_flow, owner._wu._has_last_offramp_flow, owner._last_local_landing_diagnostics, log

    def test_02_legacy_candidate_order_cost_and_direct_commit_exact(self):
        self.assertEqual(self.legacy(self.original), self.legacy(self.revised))

    def test_03_legacy_setup_reads_once_before_nested_cfg_and_previous_mutation(self):
        a = self.legacy(self.original, mutate_during_enumeration=True)
        b = self.legacy(self.revised, mutate_during_enumeration=True)
        self.assertEqual(a, b)
        self.assertEqual([row for row in b[-1] if row[0] == 'segment_vsl'],
                         [('segment_vsl', 'reference', 0, 110.), ('segment_vsl', 'reference', 1, 100.)])
        self.assertEqual([row for row in b[-1] if row[0] == 'advance'], [('advance', .1), ('advance', .1)])

    def test_04_legacy_infinite_candidate_retains_reference_fallback(self):
        a = self.legacy(self.original, substep_vehicles=math.inf)
        b = self.legacy(self.revised, substep_vehicles=math.inf)
        self.assertEqual(a, b)
        self.assertTrue(math.isinf(b[0][1]))
        self.assertEqual(b[0][0]['FW_E__seg0'], 110.)

    def query(self, *, vehicle_count=None, configure=None):
        owner, state, coupling, demand, ref, cand, vendor, landing, log = fixture(substep_vehicles=vehicle_count)
        ns = method_namespace(self.revised, vendor, landing)
        if configure:
            configure(owner, ns)
        snapshot = copy.deepcopy((ref.__dict__, cand.__dict__, owner._wu._last_offramp_flow,
                                  owner._wu._has_last_offramp_flow, owner._last_local_landing_diagnostics))
        result = ns['evaluate_fixed_freeway_candidate'](owner, 'FW_E', state, coupling, demand, cand, ref)
        self.assertEqual(snapshot, (ref.__dict__, cand.__dict__, owner._wu._last_offramp_flow,
                                    owner._wu._has_last_offramp_flow, owner._last_local_landing_diagnostics))
        return result, log

    def test_05_fixed_query_holds_expanded_candidate_meter_and_does_not_search_or_commit(self):
        result, log = self.query()
        self.assertEqual(result['candidate_count'], 1)
        self.assertFalse(result['standing_result_committed'])
        self.assertFalse(result['includes_price_terms'])
        self.assertFalse(result['shared_trajectory_connected'])
        self.assertEqual(result['vsl'], {'FW_E': 80., 'FW_E__seg0': 80., 'FW_E__seg1': 90.})
        self.assertFalse(any(row[0] in ('enumerate', 'sequences') for row in log))
        self.assertEqual([row for row in log if row[0] == 'substep'],
                         [('substep', (80., 90.), {'R': 25.}, {'SC1_p1': 25.}, {'SC1': 4.})])

    def test_06_fixed_nonfinite_score_rejected_without_legacy_fallback(self):
        for value in (math.inf, -math.inf, math.nan):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'one finite score'):
                self.query(vehicle_count=value)

    def test_07_fixed_bad_count_or_changed_missing_extra_expanded_value_rejected(self):
        for mutation in (
            lambda r: r.update(candidate_count=0), lambda r: r.update(candidate_count=2),
            lambda r: r.update(candidate_count=True),
            lambda r: r['vsl'].update(FW_E=90.), lambda r: r['vsl'].update(FW_E__seg1=math.nan),
            lambda r: r['vsl'].pop('FW_E__seg0'), lambda r: r['vsl'].update(FW_E__seg2=80.),
        ):
            def wrap(owner, ns):
                evaluate = ns['_evaluate_freeway_sequences']
                def altered(*args, **kwargs):
                    result = evaluate(*args, **kwargs)
                    mutation(result)
                    return result
                ns['_evaluate_freeway_sequences'] = altered
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.query(configure=wrap)

    def test_08_additive_price_exclusion_does_not_change_smoothness_policy(self):
        def priced(owner, ns):
            owner.vsl_marginal_price = {'FW_E__seg0': 2.}
            owner.vsl_marginal_price_ref = {'FW_E__seg0': 110.}
            owner.vsl_meter_cross_price = {'R': 3.}
            owner.vsl_meter_cross_ref = {'R': (12., 110.)}
            owner.price_smoothness_disabled = True
        absent, _ = self.query()
        excluded, _ = self.query(configure=priced)
        # Active price policy suppresses smoothness even when additive prices
        # are excluded. It is kept separate from the include-price switch.
        self.assertAlmostEqual(absent['cost'] - excluded['cost'], .001 * (30 + 10))
        owner, state, coupling, demand, ref, cand, vendor, landing, log = fixture()
        ns = method_namespace(self.revised, vendor, landing); priced(owner, ns)
        included = ns['evaluate_fixed_freeway_candidate'](owner, 'FW_E', state, coupling, demand, cand, ref, include_price_terms=True)
        expected_price = 2 * (80 - 110) + 3 * (25 - 12) * (80 - 110)
        self.assertAlmostEqual(included['cost'] - excluded['cost'], expected_price)

    def test_09_two_owned_meters_are_held_for_every_substep(self):
        owner, state, coupling, demand, ref, cand, vendor, landing, log = fixture()
        owner._local_freeway_models['FW_E'].owned_ramps = ('R', 'S')
        owner.cfg.freeway_follower.freeway_prediction_horizon_steps = 2
        owner.cfg.simulation.K_cf = 2
        ref.ramp_metering['S'] = 6.; cand.ramp_metering['S'] = 31.; state.ramp_queue['S'] = 0.
        owner._local_ramp_release = lambda *args: {'R': 0., 'S': 0.}
        before = copy.deepcopy((vars(state), vars(ref), vars(cand), vars(owner._wu), owner._last_local_landing_diagnostics))
        ns = method_namespace(self.revised, vendor, landing)
        result = ns['evaluate_fixed_freeway_candidate'](owner, 'FW_E', state, coupling, demand, cand, ref)
        rows = [row for row in log if row[0] == 'substep']
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row[1:3] == ((80., 90.), {'R': 25., 'S': 31.}) for row in rows))
        self.assertEqual(result['candidate_count'], 1)
        self.assertFalse(any(row[0] in ('enumerate', 'sequences') for row in log))
        self.assertEqual(before, (vars(state), vars(ref), vars(cand), vars(owner._wu), owner._last_local_landing_diagnostics))

    def test_10_missing_negative_or_nonfinite_owned_meter_rejected_before_substep(self):
        for value in (None, -1., math.nan, math.inf):
            with self.subTest(value=value):
                owner, state, coupling, demand, ref, cand, vendor, landing, log = fixture()
                if value is None: del cand.ramp_metering['R']
                else: cand.ramp_metering['R'] = value
                ns = method_namespace(self.revised, vendor, landing)
                with self.assertRaisesRegex(ValueError, '(owned meter|finite and nonnegative)'):
                    ns['evaluate_fixed_freeway_candidate'](owner, 'FW_E', state, coupling, demand, cand, ref)
                self.assertFalse(any(row[0] == 'substep' for row in log))
                self.assertEqual(owner._wu._last_offramp_flow, {'unrelated': 99.})

    def test_11_fixed_substep_exception_does_not_commit_or_mutate_inputs(self):
        owner, state, coupling, demand, ref, cand, vendor, landing, log = fixture()
        def fail(*args, **kwargs): raise RuntimeError('injected local substep failure')
        vendor.freeway_substep_local = fail
        before = copy.deepcopy((vars(state), vars(ref), vars(cand), vars(owner._wu), owner._last_local_landing_diagnostics))
        ns = method_namespace(self.revised, vendor, landing)
        with self.assertRaisesRegex(RuntimeError, 'injected local substep failure'):
            ns['evaluate_fixed_freeway_candidate'](owner, 'FW_E', state, coupling, demand, cand, ref)
        self.assertEqual(before, (vars(state), vars(ref), vars(cand), vars(owner._wu), owner._last_local_landing_diagnostics))

    def test_12_fixed_a_b_a_repeat_is_identical_with_pure_hooks(self):
        owner, state, coupling, demand, ref, cand, vendor, landing, log = fixture()
        other = copy.deepcopy(cand); other.vsl.update(FW_E=100., FW_E__seg0=100., FW_E__seg1=110.)
        other.ramp_metering['R'] = 38.
        ns = method_namespace(self.revised, vendor, landing)
        call = ns['evaluate_fixed_freeway_candidate']
        a = call(owner, 'FW_E', state, coupling, demand, cand, ref)
        b = call(owner, 'FW_E', state, coupling, demand, other, ref)
        again = call(owner, 'FW_E', state, coupling, demand, cand, ref)
        self.assertEqual(a, again); self.assertNotEqual(a['cost'], b['cost'])
        self.assertEqual(owner._wu._last_offramp_flow, {'unrelated': 99.})

    def test_13_legacy_prices_override_and_exception_order_exact(self):
        def run(source, fail=False):
            owner, state, coupling, demand, ref, cand, vendor, landing, log = fixture()
            owner.vsl_marginal_price = {'FW_E__seg0': 2.}
            owner.vsl_marginal_price_ref = {'FW_E__seg0': 100.}
            owner.vsl_meter_cross_price = {'R': 3.}
            owner.vsl_meter_cross_ref = {'R': (6., 100.)}
            if fail:
                def substep(*args, **kwargs):
                    log.append(('injected_failure',)); raise RuntimeError('same failure')
                vendor.freeway_substep_local = substep
            ns = method_namespace(source, vendor, landing)
            try: result = ns['solve_freeway_agent_local'](owner, 'FW_E', state, coupling, demand, ref, [80., 90.])
            except RuntimeError as exc: result = (type(exc).__name__, str(exc))
            return result, dict(owner._wu._last_offramp_flow), owner._wu._has_last_offramp_flow, copy.deepcopy(owner._last_local_landing_diagnostics), log
        self.assertEqual(run(self.original), run(self.revised))
        self.assertEqual(run(self.original, True), run(self.revised, True))


class SharedFreewayResponseTests(unittest.TestCase):
    """Explicit coupled operands and strict dynamics stubs, never a model run."""

    def fixture(self, *, tail=False):
        owner, state, coupling, demand, ref, cand, vendor, landing, log = fixture()
        net = owner.cfg.network
        net.off_ramp_storage_link = {'OR': 'OR'}
        net.offramp_direct_share_by_offramp = {}
        net.urban_link_storage_veh = {'OR': 20.}
        net.urban_movements = {}
        owner._wu._offramp_drain_flow = {}
        owner._wu._specs = {}
        for action in (ref, cand):
            action.N_P_star = 0.
            action.N_UF_star = sum(action.ramp_metering.values())
            action.inflow_outflow_allocation = {}
        for field in ('ramp_metering', 'green_times', 'offsets'):
            setattr(cand, field, copy.deepcopy(getattr(ref, field)))
        cand.N_UF_star = ref.N_UF_star
        final_queue = 0.
        if tail:
            net.ramp_capacity_veh_h = {'R': 1000.}
            net.rho_crit, net.rho_max = 10., 20.
            net.urban_movements = {'M': {'ramp': 'R'}}
            owner._local_freeway_models['FW_E'].ramp_merge_idx = {'R': 0}
            owner.cfg.mpc.follower_terminal_cost_enabled = True
            owner.cfg.mpc.protected_queue_movement = 'M'
            owner.cfg.mpc.protected_queue_weight = .4
            owner.cfg.mpc.protected_queue_max_veh = 5.
            state.urban_movement_queue = {'M': 20.}
            state.ramp_queue = {'R': 10.}
            owner._local_ramp_release = lambda *args: {'R': 2.}
            final_queue = 9.8
        fields = ('N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times', 'offsets',
                  'inflow_outflow_allocation')
        response = {'link': 'FW_E', 'start_sec': 900., 'end_sec': 1260.,
                    'sample_stage': 'post_freeway_landing',
                    'applied_control': {k: copy.deepcopy(getattr(cand, k)) for k in fields},
                    'frames': [{'start_sec': 900., 'end_sec': 1260., 'link_vehicles_veh': 1.7,
                                'ramp_queue_veh': {'R': final_queue}, 'landing_stock_veh': {'OR': 1.},
                                'blocked_queue_veh': {'R': 0.}}]}
        if tail:
            response.update(final_density=[1., 2.], final_ramp_release_veh_h={'R': 2.},
                            initial_protected_queue_veh={'M': 20.})
        source = producer.SOURCE.read_text(encoding='utf-8')
        ns = method_namespace(source, vendor, landing)
        return owner, state, coupling, demand, ref, cand, response, ns, log, vendor, landing

    def test_same_operands_same_local_functional_without_dynamics_or_commit(self):
        for tail in (False, True):
            owner, state, coupling, demand, ref, cand, response, ns, log, vendor, landing = self.fixture(tail=tail)
            local = ns['evaluate_fixed_freeway_candidate'](owner, 'FW_E', state, coupling, demand, cand, ref)
            log.clear()
            before = copy.deepcopy((response, vars(cand), vars(ref), owner._wu._last_offramp_flow,
                                    owner._last_local_landing_diagnostics))
            def forbidden(*args, **kwargs): raise AssertionError('Shared scoring reran dynamics')
            ns['LocalLandingState'] = forbidden
            vendor.freeway_substep_local = forbidden
            owner._local_ramp_release = forbidden
            shared = ns['score_shared_freeway_response'](owner, 'FW_E', response, cand, ref)
            self.assertEqual(shared['cost'], local['cost'])
            self.assertEqual(shared['frame_count'], 1)
            self.assertFalse(shared['includes_price_terms'])
            self.assertFalse(shared['standing_result_committed'])
            self.assertTrue(shared['shared_trajectory_connected'])
            self.assertEqual(before, (response, vars(cand), vars(ref), owner._wu._last_offramp_flow,
                                      owner._last_local_landing_diagnostics))
            self.assertFalse(any(row[0] in ('advance', 'substep', 'enumerate') for row in log))

    def test_extracted_terminal_protected_and_smoothness_matches_archived_legacy(self):
        owner, state, coupling, demand, ref, cand, response, ns, log, vendor, landing = self.fixture(tail=True)
        with zipfile.ZipFile(producer.ROOT / 'diagnostics/fixed_freeway_query_installed_v1/baseline_source.zip') as z:
            old = z.read('link_predictor.py').decode('utf-8')
        original = method_namespace(old, vendor, landing)
        expected = original['solve_freeway_agent_local'](owner, 'FW_E', state, coupling, demand, ref, [80., 90.])[1]
        actual = ns['score_shared_freeway_response'](owner, 'FW_E', response, cand, ref)
        self.assertEqual(actual['cost'], expected)
        owner.vsl_marginal_price = {'FW_E__seg0': 999.}
        owner.vsl_meter_cross_price = {'R': 999.}
        self.assertEqual(ns['score_shared_freeway_response'](owner, 'FW_E', response, cand, ref)['cost'], expected)
        owner.price_smoothness_disabled = True
        without_smooth = ns['score_shared_freeway_response'](owner, 'FW_E', response, cand, ref)['cost']
        self.assertAlmostEqual(expected - without_smooth, .04)

    def test_shared_accepted_queue_stock_and_reference_are_separate_operands(self):
        owner, _, _, _, ref, cand, response, ns, *_ = self.fixture()
        call = ns['score_shared_freeway_response']
        a = call(owner, 'FW_E', response, cand, ref)
        changed = copy.deepcopy(response)
        changed['frames'][0]['ramp_queue_veh']['R'] = 3.
        b = call(owner, 'FW_E', changed, cand, ref)
        self.assertAlmostEqual(b['cost'] - a['cost'], .3)
        self.assertEqual(a, call(owner, 'FW_E', response, cand, ref))
        same_ref = copy.deepcopy(ref)
        same_ref.vsl = dict(cand.vsl)
        self.assertAlmostEqual(a['cost'] - call(owner, 'FW_E', response, cand, same_ref)['cost'], .04)

    def test_missing_wrong_time_control_catalog_and_nonfinite_operands_fail(self):
        owner, _, _, _, ref, cand, response, ns, *_ = self.fixture()
        mutations = (
            lambda r: r['frames'][0].pop('blocked_queue_veh'),
            lambda r: r['frames'][0]['landing_stock_veh'].clear(),
            lambda r: r['frames'][0]['ramp_queue_veh'].update(FOREIGN=1.),
            lambda r: r['frames'][0].update(link_vehicles_veh=math.nan),
            lambda r: r['frames'][0]['blocked_queue_veh'].update(R=1.),
            lambda r: r['frames'][0].update(start_sec=901.),
            lambda r: r.update(end_sec=1259.),
            lambda r: r['frames'].append(copy.deepcopy(r['frames'][0])),
            lambda r: r['applied_control']['offsets'].update(SC1=9.),
            lambda r: r.update(sample_stage='before_freeway'),
            lambda r: r.update(link='FW_W'),
        )
        for mutate in mutations:
            changed = copy.deepcopy(response)
            mutate(changed)
            with self.subTest(mutate=mutate), self.assertRaises((ValueError, KeyError)):
                ns['score_shared_freeway_response'](owner, 'FW_E', changed, cand, ref)

    def test_enabled_virtual_blocked_requires_unresolved_physical_counterpart(self):
        owner, _, _, _, ref, cand, response, ns, log, *_ = self.fixture()
        owner.count_blocked_ramp_inflow = True
        with self.assertRaisesRegex(ValueError, 'no defined physical counterpart'):
            ns['score_shared_freeway_response'](owner, 'FW_E', response, cand, ref)
        self.assertEqual(log, [])

    def test_optional_cost_operands_are_required_when_active(self):
        owner, _, _, _, ref, cand, response, ns, *_ = self.fixture(tail=True)
        for key in ('final_density', 'final_ramp_release_veh_h', 'initial_protected_queue_veh'):
            changed = copy.deepcopy(response)
            del changed[key]
            with self.subTest(key=key), self.assertRaises(KeyError):
                ns['score_shared_freeway_response'](owner, 'FW_E', changed, cand, ref)
        owner.cfg.network.offramp_direct_share_by_offramp = {'OR': .5}
        owner.cfg.network.offramp_direct_tail_by_offramp = {'OR': 'same'}
        owner.cfg.network.urban_link_storage_veh['same'] = 100.
        owner._wu._offramp_drain_flow = {'OR': [('SC1', 'm1'), ('SC2', 'm2')]}
        owner._wu._specs = {'m1': {'receiving_link': 'same'}, 'm2': {'receiving_link': 'same'}}
        self.assertEqual(ns['shared_freeway_landing_links'](owner, 'FW_E'), ('OR', 'same'))
        response['frames'][0]['landing_stock_veh']['same'] = 2.
        self.assertGreater(ns['score_shared_freeway_response'](owner, 'FW_E', response, cand, ref)['cost'], 0.)

    def physical_fixture(self, *, tail=False):
        values = self.fixture(tail=tail)
        owner, _, _, _, ref, cand, response, ns, *_ = values
        owner.count_blocked_ramp_inflow = True
        owner.cfg.network.urban_movements['M'] = {'ramp': 'R'}
        owner.cfg.network.urban_link_storage_veh['shared_69'] = 100.
        owner.cfg.network.shared_approach = {
            'storage': 'shared_69',
            'branches': {'1': {'target_kind': 'ramp', 'target': 'R'},
                         '2': {'target_kind': 'storage', 'target': 'other_urban'},
                         '3': {'target_kind': 'ramp', 'target': 'OTHER_RAMP'},
                         '4': {'target_kind': 'storage', 'target': 'another_urban'}}}
        sources = {'movement_queue_veh': {'M': 4.},
                   'shared_approach_bins': {'1': {180: 2., 1000: 5.}, '2': {180: 11.},
                                            '3': {1000: 13.}, '4': {180: 17.}},
                   'shared_approach_stock_veh': 48.}
        response.update(ramp_approach_queue_semantics='physical_destination_cohorts/v1',
                        ramp_approach_queue_lineage=ns['shared_freeway_approach_source_contract'](owner, 'FW_E'),
                        initial_ramp_approach_sources=copy.deepcopy(sources))
        response['frames'][0].pop('blocked_queue_veh')
        response['frames'][0]['ramp_approach_sources'] = copy.deepcopy(sources)
        return values

    def test_physical_destination_mode_counts_all_owned_bins_and_nonzero_initial_stock(self):
        owner, _, _, _, ref, cand, response, ns, log, *_ = self.physical_fixture()
        before = copy.deepcopy((response, vars(cand), vars(ref), owner._wu._last_offramp_flow))
        result = ns['score_shared_freeway_response'](owner, 'FW_E', response, cand, ref)
        self.assertEqual(result['initial_ramp_approach_queue_veh'], {'R': 11.})
        self.assertEqual(result['final_ramp_approach_queue_veh'], {'R': 11.})
        self.assertTrue(result['local_functional_changed'])
        self.assertEqual(result['ramp_approach_queue_semantics'], 'physical_destination_cohorts/v1')
        self.assertAlmostEqual(result['residence_cost'], (1.7 + 1. + 4. + 2. + 5.) * .1)
        self.assertEqual(before, (response, vars(cand), vars(ref), owner._wu._last_offramp_flow))
        self.assertFalse(any(row[0] in ('advance', 'substep', 'enumerate') for row in log))
        # Readiness changes eligibility, not residence or ownership. No due filter.
        later = copy.deepcopy(response)
        later['frames'][0]['ramp_approach_sources']['shared_approach_bins']['1'] = {2000: 7.}
        self.assertEqual(result['cost'], ns['score_shared_freeway_response'](owner, 'FW_E', later, cand, ref)['cost'])

    def test_accepted_approach_to_ramp_transfer_preserves_residence_and_terminal_operand(self):
        owner, _, _, _, ref, cand, response, ns, *_ = self.physical_fixture(tail=True)
        call = ns['score_shared_freeway_response']
        before = call(owner, 'FW_E', response, cand, ref)
        transferred = copy.deepcopy(response)
        frame = transferred['frames'][0]
        frame['ramp_queue_veh']['R'] += 7.
        frame['ramp_approach_sources']['shared_approach_bins']['1'] = {}
        frame['ramp_approach_sources']['shared_approach_stock_veh'] -= 7.
        after = call(owner, 'FW_E', transferred, cand, ref)
        self.assertAlmostEqual(before['cost'], after['cost'])
        self.assertAlmostEqual(before['residence_cost'], after['residence_cost'])
        self.assertEqual(after['final_ramp_approach_queue_veh'], {'R': 4.})

    def test_physical_source_registry_lineage_closure_and_required_initial_are_strict(self):
        owner, _, _, _, ref, cand, response, ns, *_ = self.physical_fixture()
        mutations = (
            lambda r: r.pop('ramp_approach_queue_semantics'),
            lambda r: r.pop('initial_ramp_approach_sources'),
            lambda r: r['ramp_approach_queue_lineage'].update(shared_due_selection='ready_only'),
            lambda r: r['frames'][0].update(blocked_queue_veh={'R': 0.}),
            lambda r: r['frames'][0]['ramp_approach_sources']['movement_queue_veh'].clear(),
            lambda r: r['frames'][0]['ramp_approach_sources']['movement_queue_veh'].update(UNKNOWN=0.),
            lambda r: r['frames'][0]['ramp_approach_sources']['shared_approach_bins'].pop('4'),
            lambda r: r['frames'][0]['ramp_approach_sources'].update(shared_approach_stock_veh=49.),
            lambda r: r['frames'][0]['ramp_approach_sources'].update(unadmitted_demand_veh=10.),
            lambda r: r['frames'][0]['ramp_approach_sources']['shared_approach_bins']['1'].update({'180': 2.}),
            lambda r: r['initial_ramp_approach_sources']['shared_approach_bins']['1'].update({180: -1.}),
        )
        for mutate in mutations:
            changed = copy.deepcopy(response)
            mutate(changed)
            with self.subTest(mutate=mutate), self.assertRaises((ValueError, KeyError)):
                ns['score_shared_freeway_response'](owner, 'FW_E', changed, cand, ref)
        # JSON due-key restoration is lossless and accepted.
        import json
        restored = json.loads(json.dumps(response))
        self.assertEqual(ns['score_shared_freeway_response'](owner, 'FW_E', response, cand, ref),
                         ns['score_shared_freeway_response'](owner, 'FW_E', restored, cand, ref))

    def test_unregistered_ramp_and_landing_overlap_reject_instead_of_zero_or_double_count(self):
        owner, _, _, _, ref, cand, response, ns, *_ = self.physical_fixture()
        owner.cfg.network.shared_approach['storage'] = 'OR'
        with self.assertRaisesRegex(ValueError, 'duplicate a landing'):
            ns['shared_freeway_approach_source_contract'](owner, 'FW_E')
        owner.cfg.network.shared_approach = None
        owner.cfg.network.urban_movements.clear()
        with self.assertRaisesRegex(ValueError, 'No registered physical'):
            ns['shared_freeway_approach_source_contract'](owner, 'FW_E')

    def test_declared_new_functional_is_not_legacy_virtual_queue_equivalence(self):
        owner, _, _, _, ref, cand, response, ns, *_ = self.physical_fixture()
        physical = ns['score_shared_freeway_response'](owner, 'FW_E', response, cand, ref)
        owner.count_blocked_ramp_inflow = False
        with self.assertRaisesRegex(ValueError, 'disabled local queue-cost'):
            ns['score_shared_freeway_response'](owner, 'FW_E', response, cand, ref)
        legacy = copy.deepcopy(response)
        for field in ('ramp_approach_queue_semantics', 'ramp_approach_queue_lineage', 'initial_ramp_approach_sources'):
            legacy.pop(field)
        legacy['frames'][0].pop('ramp_approach_sources')
        legacy['frames'][0]['blocked_queue_veh'] = {'R': 0.}
        old_definition = ns['score_shared_freeway_response'](owner, 'FW_E', legacy, cand, ref)
        self.assertAlmostEqual(physical['cost'] - old_definition['cost'], 1.1)
        self.assertFalse(old_definition['local_functional_changed'])


if __name__ == '__main__':
    unittest.main()
