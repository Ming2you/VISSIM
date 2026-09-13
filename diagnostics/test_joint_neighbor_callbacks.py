"""Actual writer/meter integration with geometry-free state/source fixtures.

No traffic model/endpoint/COM runs. Existing urban phase source is AST fixture;
FW source methods are explicit finite fixtures. Actual canonical catalog,
neighbor factory, writer row iterator and measured meter allocation are used.
"""
import copy
import csv
import io
import json
import pickle
from collections import UserDict
from pathlib import Path
from contextlib import contextmanager
from types import SimpleNamespace, MethodType
import tempfile
import unittest
from unittest.mock import patch
import numpy as np  # Load before the existing temporary src-module fixture.

from diagnostics import test_joint_urban_neighbors as urban_fixture
from evaluation.controllers import joint_owner_neighbors as module
from evaluation.controllers import joint_owner_game as game
from evaluation.controllers import area_meter_finalization as meters
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers.action_csv_schema import ACTION_CSV_FIELDS


class JointNeighborCallbackTests(unittest.TestCase):
    def test_alias_context_is_checked_once_and_distinct_contexts_are_both_guarded(self):
        checked = []
        def fingerprint(value):
            checked.append(id(value))
            return module._key(value)
        callbacks = self.make(context_fingerprint=fingerprint, defer_unvisited_command_checks=True)
        expected = callbacks['command_evidence'](self.initial)
        checked.clear()
        self.assertEqual(callbacks['command_evidence'](self.initial, self.context), expected)
        shared_checks = len(checked)
        equivalent = copy.deepcopy(self.context)
        checked.clear()
        self.assertEqual(callbacks['command_evidence'](self.initial, equivalent), expected)
        self.assertEqual(len(checked), 2 * shared_checks)
        self.assertEqual(set(checked), {id(equivalent), id(self.context)})
        equivalent['source'] = 'changed caller context'
        with self.assertRaisesRegex(ValueError, 'context changed'):
            callbacks['command_evidence'](self.initial, equivalent)
        equivalent = copy.deepcopy(self.context)
        self.context['source'] = 'changed original context'
        with self.assertRaisesRegex(ValueError, 'context changed'):
            callbacks['command_evidence'](self.initial, equivalent)

    def test_cached_command_proof_is_exact_isolated_and_context_guarded(self):
        eager, cached = self.make(), self.make(defer_unvisited_command_checks=True)
        expected = eager['command_evidence'](self.initial)
        first = cached['command_evidence'](self.initial)
        self.assertEqual(expected, first)
        first['ordered_rows'][0]['kind'] = 'poisoned'
        with patch.object(adapter, 'iter_action_csv_rows', side_effect=AssertionError('Repeated writer')):
            self.assertEqual(expected, cached['command_evidence'](copy.deepcopy(self.initial)))
        stats = cached['command_cache_stats']()
        self.assertEqual((stats['writer_checks'], stats['hits']), (1, 1))
        self.assertGreater(stats['retained_bytes'], 0)
        self.context['fixed_prices']['changed'] = 1
        with self.assertRaisesRegex(ValueError, 'context changed'):
            cached['command_evidence'](self.initial)

    def test_cached_command_proof_rechecks_changed_action_and_binding(self):
        cached = self.make(defer_unvisited_command_checks=True)
        cached['command_evidence'](self.initial)
        broken = copy.deepcopy(self.initial)
        broken.vsl['FW_E__seg0'] = 73.
        with self.assertRaises(ValueError):
            cached['command_evidence'](broken)
        self.mapping['segments'][0]['dsd_no'] = -1
        with self.assertRaisesRegex(ValueError, 'binding changed'):
            cached['command_evidence'](self.initial)

    def test_deferred_checks_preserve_domain_and_full_visited_command_proof(self):
        eager, deferred = self.make(), self.make(defer_unvisited_command_checks=True)
        writer = adapter.iter_action_csv_rows
        with patch.object(adapter, 'iter_action_csv_rows', wraps=writer) as calls:
            before = eager['neighbors']('SC1', self.initial, self.context)
            eager_calls = calls.call_count
        with patch.object(adapter, 'iter_action_csv_rows', wraps=writer) as calls:
            after = deferred['neighbors']('SC1', self.initial, self.context)
            deferred_calls = calls.call_count
        self.assertEqual(pickle.dumps(before, protocol=5), pickle.dumps(after, protocol=5))
        self.assertEqual(eager_calls-deferred_calls, len(before.candidates))
        self.assertEqual(deferred_calls, 1)  # Complete incumbent command proof.
        for candidate in after.candidates:
            self.assertEqual(eager['command_evidence'](candidate), deferred['command_evidence'](candidate))
        # Explicit exhaustive diagnostics remain exhaustive with the option on.
        full = deferred['neighbor_evidence']('SC1', self.initial, self.context)
        self.assertEqual(len(full['command_evidence']), len(after.candidates))

    def setUp(self):
        fixture = urban_fixture.UrbanNeighborTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.base = fixture
        self.cfg, self.follower = fixture.cfg, fixture.follower
        self.mapping, self.plan = fixture.mapping, fixture.plan
        net = self.cfg.network
        net.control_area_enabled = True
        net.ramps = tuple(net.ramp_to_freeway)
        net.ramp_capacity_veh_h = {r: 1800. for r in net.ramps}
        net.freeway_vsl_zone_of_cell = {d: [min(i // 5, 3) for i in range(21)] for d in net.freeway_links}
        self.cfg.freeway_follower = SimpleNamespace(vsl_set=(60., 80., 100., 120.),
            max_vsl_step=40., vsl_sequence_search=True, freeway_prediction_horizon_steps=3)
        for k, v in dict(wu_faithful_nuf_coordination_mode='dual', baseline_move_box=True,
                         leader_budget_off=False, relaxed_quantized_controls=True, horizon_steps=3).items():
            setattr(self.cfg.mpc, k, v)
        self.follower.offset_fractions = (0., .125)
        self.follower.offset_marginal_price = None
        for key, value in dict(ramp_metering_fractions=(1., .7, .5, .35, .25),
                metering_marginal_price=None, metering_marginal_price_ref={},
                metering_marginal_price_trust_frac=None, metering_release_certified=None,
                metering_price_split=False, _lambda_UF=0., vsl_marginal_price=None,
                vsl_marginal_price_ref={}, vsl_marginal_price_trust_kmh=None).items():
            setattr(self.follower, key, value)
        class Wu:
            def _relaxed_freeway_segment_candidates(self, owner, n, state, coupling, snapshot, demand):
                self._repair_diagnostics['calls'] += 1
                state.private_initialized = True
                coupling['private'] = 1.
                demand.private = 1.
                current = [snapshot.vsl[f'{owner}__seg{i}'] for i in range(n)]
                lower = [max(60., v - 40.) if i < 5 else v for i, v in enumerate(current)]
                return [current, lower]
        self.follower._wu = Wu()
        self.follower._wu._repair_diagnostics = {'calls': 0}
        self.follower._wu._omega_f = {'FW_E': .5, 'FW_W': .5}
        def sequences(self, owner, n, snapshot, base, horizon):
            return [[list(vector) for _ in range(horizon)] for vector in base]
        sequences._rw_vsl_kbest = True
        self.follower._freeway_vsl_sequence_candidates = MethodType(sequences, self.follower)
        self.state = SimpleNamespace(time_sec=900., freeway_density={d: [30.] * 21 for d in net.freeway_links},
            local_observation_summary={'ramp_spillback': {r: 0. for r in net.ramps}})
        self.coupling, self.demand = {'p_down_FW_E': .2}, SimpleNamespace(incident_capacity_factor=1.)
        self.leader = SimpleNamespace(N_UF_star=5416.227623335266, N_P_star=17.)
        raw = {'sim_sec': 900., 'local_observation': {'far_measurement': {
            'link_volume_veh_h': {str(m['connector']): 200. for m in self.mapping['ramp_meters']}}}}
        meters.configure(adapter, self.cfg, fixture.tuning, self.mapping, raw, None, self.state)
        self.actuation = copy.deepcopy(net.control_area_meter_context['actuation'])
        initial = copy.deepcopy(fixture.control)
        initial.ramp_metering = {r: 1800. for r in net.ramps}
        self.initial = meters.prepare_canonical_candidate(initial, self.cfg, owned_ramps=tuple(net.ramps),
            total_budget=None, directional_budgets={}, budget_tolerance_veh_h=1e-9)
        self.previous = self.historical_reference(self.initial, self.cfg)['previous']
        self.context = {'source': 'explicit synthetic frozen decision', 'fixed_prices': {}}
        self.scope_stats = {'entered': 0, 'exited': 0}
        self.runtime = {'values': []}
        @contextmanager
        def scope():
            self.scope_stats['entered'] += 1
            old = copy.deepcopy(self.runtime['values'])
            try:
                yield
            finally:
                self.runtime['values'][:] = old
                self.scope_stats['exited'] += 1
        self.scope = scope
        self.callbacks = self.make()

    def segment(self, control, link, index, cfg):
        self.runtime['values'].append((link, index))
        return control.vsl[f'{link}__seg{index}']

    def historical_reference(self, control, cfg):
        context = cfg.network.control_area_meter_context
        physical = adapter.real_world_ramp_meter_actions(copy.deepcopy(control), cfg,
            context['actuation'], context['mapping'])
        written = [{'kind': 'ramp_meter', 'id': mid, 'sc_no': int(row['sc_no']),
                    'rate_vph': round(row['rate_vph'], 3), 'green_sec': round(row['green_sec'], 3)}
                   for mid, row in physical.items()]
        return meters.prepare_historical_meter_reference(control, cfg,
            written_meter_rows=written, source_provenance={'fixture': 'actual writer, explicit synthetic historical context'})

    def make(self, **overrides):
        kwargs = dict(segment_vsl_func=self.segment, context=self.context,
            context_fingerprint=module._key, query_scope=self.scope,
            held_horizon_sec=450., budget_tolerance_veh_h=1e-9, total_budget=None,
            directional_budgets={}, freeway_joint_pairs=lambda owner, domain: (
                (0, domain.head_values[0][-1], domain.meter_points[-1][0]),))
        kwargs.update(overrides)
        return module.make_joint_neighbor_callbacks(self.follower, self.state, self.coupling,
            self.demand, self.leader, self.previous, self.mapping, self.plan, self.actuation,
            {'controller_variant': 'wu-link'}, **kwargs)

    def test_search_interleave_preserves_actual_writer_candidates_and_starts_coupled(self):
        # Use the existing partial-meter fixture so physical quantization has
        # nontrivial meter points. The all-open fixture legitimately has none.
        volumes = self.cfg.network.control_area_meter_context['raw']['local_observation']['far_measurement']['link_volume_veh_h']
        volumes.update({k: 1500. for k in volumes})
        self.initial.ramp_metering = {r: 1500. for r in self.initial.ramp_metering}
        self.initial = meters.prepare_canonical_candidate(self.initial, self.cfg,
            owned_ramps=tuple(self.cfg.network.ramps), total_budget=None,
            directional_budgets={}, budget_tolerance_veh_h=1e-9)
        self.previous = self.historical_reference(self.initial, self.cfg)['previous']
        callbacks = self.make(freeway_joint_pairs=lambda owner, domain: tuple(
            (head, value, label) for head, values in domain.head_values.items()
            for value in values for label, _ in domain.meter_points))
        for owner in ('SC1', 'FW_E'):
            with self.subTest(owner=owner):
                evidence = callbacks['neighbor_evidence'](owner, self.initial, self.context)
                source = game.Neighborhood(evidence['candidates'], True, evidence['domain_label'])
                frozen = tuple(module._key(vars(c)) for c in source.candidates)
                shuffled = module.interleave_realized_neighbors(
                    callbacks['ownership'], owner, self.initial, source)
                self.assertEqual(sorted(frozen), sorted(module._key(vars(c)) for c in shuffled.candidates))
                self.assertEqual(frozen, tuple(module._key(vars(c)) for c in source.candidates))
                self.assertIs(shuffled.candidates[0], source.candidates[0])
                # The actual fixture has coupled, pure first-lever and pure
                # second-lever commands, all already checked by the writer.
                fields = ('vsl', 'ramp_metering') if owner == 'FW_E' else ('green_times', 'offsets')
                changed = lambda c: {f for f in fields if getattr(c, f) != getattr(self.initial, f)}
                self.assertEqual([changed(c) for c in shuffled.candidates[1:4]],
                                 [set(fields), {fields[0]}, {fields[1]}])
                for family in (set(fields), {fields[0]}, {fields[1]}):
                    self.assertEqual([id(c) for c in source.candidates if changed(c) == family],
                                     [id(c) for c in shuffled.candidates if changed(c) == family])
                self.assertTrue(shuffled.complete)
                self.assertIn('coupled-family-interleave/v1', shuffled.domain_label)

    def test_search_interleave_handles_absent_family_without_claiming_completion(self):
        source = self.callbacks['neighbors']('SC1', self.initial, self.context)
        pure_green = tuple(c for c in source.candidates
                           if c.offsets == self.initial.offsets)
        partial = game.Neighborhood(pure_green, False, 'partial-fixture', 'missing domain')
        shuffled = module.interleave_realized_neighbors(
            self.callbacks['ownership'], 'SC1', self.initial, partial)
        self.assertEqual([id(c) for c in shuffled.candidates], [id(c) for c in pure_green])
        self.assertFalse(shuffled.complete)
        self.assertEqual(shuffled.incomplete_reason, 'missing domain')

    def test_search_interleave_rejects_foreign_change_and_duplicate_incumbent(self):
        bad = copy.deepcopy(self.initial)
        bad.offsets['SC5'] += 1
        for second in (bad, copy.deepcopy(self.initial)):
            with self.assertRaises(ValueError):
                module.interleave_realized_neighbors(self.callbacks['ownership'], 'SC1', self.initial,
                    game.Neighborhood((self.initial, second), True, 'invalid-fixture'))

    def test_binding_snapshot_skips_only_exact_values_and_reordering_falls_back(self):
        original_key, binding_calls = module._key, []
        def counted(value):
            if type(value) is dict and {'selected_plan', 'meter_context', 'omega_f'}.issubset(value):
                binding_calls.append(original_key(value))
            return original_key(value)
        with patch.object(module, '_key', side_effect=counted):
            callbacks = self.make()
            self.assertEqual(len(binding_calls), 1)
            before = callbacks['command_evidence'](self.initial)
            self.assertEqual(len(binding_calls), 1)
            omega = self.follower._wu._omega_f
            reordered = list(reversed(list(omega.items())))
            omega.clear(); omega.update(reordered)
            after = callbacks['command_evidence'](self.initial)
            self.assertEqual(after, before)
            self.assertGreater(len(binding_calls), 1)
            self.assertTrue(all(value == callbacks['provenance']['binding_sha256'] for value in binding_calls))
            omega['FW_E'] = .6
            with self.assertRaisesRegex(ValueError, 'Frozen physical/domain binding changed'):
                callbacks['command_evidence'](self.initial)

    def test_binding_with_custom_mapping_retains_original_hash_checks(self):
        self.follower.offset_marginal_price_ref = UserDict({'SC1': 0.})
        original_key, binding_calls = module._key, []
        def counted(value):
            if type(value) is dict and {'selected_plan', 'meter_context', 'omega_f'}.issubset(value):
                binding_calls.append(original_key(value))
            return original_key(value)
        with patch.object(module, '_key', side_effect=counted):
            callbacks = self.make()
            self.assertEqual(len(binding_calls), 1)
            evidence = callbacks['command_evidence'](self.initial)
            self.assertEqual(len(evidence['ordered_rows']), 213)
            self.assertGreater(len(binding_calls), 1)
            self.follower.offset_marginal_price_ref['SC1'] = 1.
            with self.assertRaisesRegex(ValueError, 'Frozen physical/domain binding changed'):
                callbacks['command_evidence'](self.initial)

    def test_actual_writer_order_full_bytes_catalog_and_sc5_red_only_plan(self):
        saved = copy.deepcopy(vars(self.initial))
        evidence = self.callbacks['command_evidence'](self.initial)
        self.assertEqual(len(evidence['ordered_rows']), 213)
        self.assertEqual(len(evidence['physical_rows']), 213)
        self.assertEqual(len(evidence['owner_physical_sha256']), 19)
        kinds = [r['kind'] for r in evidence['ordered_rows']]
        self.assertEqual({k: kinds.count(k) for k in set(kinds)},
                          {'vsl': 66, 'signal': 17, 'signal_sg': 122, 'ramp_meter': 8})
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'action.csv'
            with self.scope():
                adapter.write_action_csv(path, copy.deepcopy(self.initial), self.cfg, self.mapping,
                    self.segment, {'controller_variant': 'wu-link'}, self.actuation, self.plan, 'experiment')
            buffer = io.StringIO(newline='')
            writer = csv.DictWriter(buffer, fieldnames=ACTION_CSV_FIELDS)
            writer.writeheader(); writer.writerows(evidence['ordered_rows'])
            self.assertEqual(buffer.getvalue().encode('utf-8'), path.read_bytes())
        self.assertEqual(vars(self.initial), saved)
        self.assertEqual(self.runtime['values'], [])
        self.assertEqual(self.scope_stats['entered'], self.scope_stats['exited'])
        bad_plan = self.plan['controllers']['5']
        original = copy.deepcopy(bad_plan)
        bad_plan['red_only'] = {'mutated': 1}
        with self.assertRaisesRegex(ValueError, 'binding changed'):
            self.callbacks['physical_rows'](self.initial)
        bad_plan.clear(); bad_plan.update(original)

    def test_urban_and_freeway_candidates_foreign_rows_full_vectors_and_revisit(self):
        baseline = self.callbacks['command_evidence'](self.initial)
        for owner in ('SC1', 'SC1004', 'FW_E', 'FW_W'):
            with self.subTest(owner=owner):
                result = self.callbacks['neighbor_evidence'](owner, self.initial, self.context)
                self.assertTrue(result['complete'])
                self.assertGreater(len(result['candidates']), 1)
                self.assertEqual(vars(result['candidates'][0]), vars(self.initial))
                for candidate, evidence in zip(result['candidates'], result['command_evidence']):
                    game.validate_nuf_semantics(candidate, 'realized_sum')
                    game.assert_owner_transition(self.callbacks['ownership'], owner, self.initial, candidate)
                    for other in self.callbacks['ownership'].owners:
                        if owner != other:
                            self.assertEqual(evidence['owner_physical_sha256'][other], baseline['owner_physical_sha256'][other])
                            self.assertEqual(evidence['owner_model_vectors'][other], baseline['owner_model_vectors'][other])
                second = self.callbacks['neighbors'](owner, result['candidates'][1], self.context)
                self.assertIsInstance(second, game.Neighborhood)
                self.assertTrue(second.complete)
                self.assertEqual(vars(second.candidates[0]), vars(result['candidates'][1]))
        self.assertEqual(self.follower._wu._repair_diagnostics, {'calls': 0})
        self.assertFalse(hasattr(self.state, 'private_initialized'))
        self.assertNotIn('private', self.coupling)
        self.assertFalse(hasattr(self.demand, 'private'))
        self.assertEqual(self.runtime['values'], [])

    def test_modeled_alias_offset_sum_and_noncanonical_previous_rejected(self):
        for kind in ('vsl_alias', 'vsl_grid', 'offset', 'sum', 'meter_alias'):
            bad = copy.deepcopy(self.initial)
            if kind == 'vsl_alias': bad.vsl['FW_E__seg1'] = 100.
            if kind == 'vsl_grid':
                for i in range(5): bad.vsl[f'FW_E__seg{i}'] = 119.
                bad.vsl['FW_E'] = 119.
            if kind == 'offset': bad.offsets['SC1'] = 150.
            if kind == 'sum': bad.N_UF_star += 1.
            if kind == 'meter_alias':
                ramp = next(iter(bad.ramp_metering)); bad.ramp_metering[ramp] = 1000.
                bad.N_UF_star = sum(bad.ramp_metering.values())
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.callbacks['physical_rows'](bad)
        ramp = next(iter(self.previous.ramp_metering))
        self.previous.ramp_metering[ramp] = 1000.
        self.previous.N_UF_star = sum(self.previous.ramp_metering.values())
        with self.assertRaisesRegex(ValueError, 'Historical meter reference'):
            self.make()

    def test_previous_box_retains_partial_and_allopen_final_writeback_anchors(self):
        # Remove the real calibration's high prior only in this explicit
        # synthetic demand-change fixture; both contexts keep the same table.
        self.cfg.network.control_area_meter_context['actuation']['real_world_ramp_metering']['demand_prior_vph'] = {}
        self.actuation['real_world_ramp_metering']['demand_prior_vph'] = {}
        self.initial = meters.prepare_canonical_candidate(self.initial, self.cfg,
            owned_ramps=tuple(self.cfg.network.ramps), total_budget=None,
            directional_budgets={}, budget_tolerance_veh_h=1e-9)
        historical_cfg = copy.deepcopy(self.cfg)
        historical_ctx = historical_cfg.network.control_area_meter_context
        historical_ctx['sim_sec'] = 750.
        for meter in self.mapping['ramp_meters']:
            if meter['model_ramp_key'] == 'R_D_W':
                historical_ctx['raw']['local_observation']['far_measurement']['link_volume_veh_h'][str(meter['connector'])] = 1200.
        original = copy.deepcopy(self.initial)
        original.ramp_metering['R_D_W'] = 131.39246994163818
        original.ramp_metering['R_F_W'] = 1000.
        meters.finalize(original, historical_cfg)
        source_rates = dict(original.ramp_metering)
        source_greens = {k: v for k, v in original.diagnostics.items() if k.startswith('rw_meter_green_')}
        # Actual old failure: current demand turns the historical PARTIAL into OPEN.
        wrong = meters.prepare_canonical_candidate(original, self.cfg,
            owned_ramps=tuple(original.ramp_metering), total_budget=None,
            directional_budgets={}, budget_tolerance_veh_h=1e-9)
        self.assertNotEqual(source_greens, {k: v for k, v in wrong.diagnostics.items() if k.startswith('rw_meter_green_')})
        prepared = self.historical_reference(original, historical_cfg)
        self.previous = prepared['previous']
        self.assertEqual(self.previous.ramp_metering['R_D_W'], source_rates['R_D_W'])
        self.assertEqual(self.previous.ramp_metering['R_F_W'], 1800.)
        self.assertEqual(source_greens, {k: v for k, v in self.previous.diagnostics.items() if k.startswith('rw_meter_green_')})
        result = self.make()['neighbor_evidence']('FW_W', self.initial, self.context)
        actual = result['source_bundle']['domain_provenance']['meter']['previous_box']
        for ramp in ('R_D_W', 'R_F_W'):
            self.assertEqual(actual[ramp], (max(0., source_rates[ramp]-300.), min(1800., source_rates[ramp]+300.)))
        self.assertNotEqual(actual['R_D_W'], (1500., 1800.))
        self.assertEqual(actual['R_F_W'], (700., 1300.))
        # Explicit and embedded proof forms agree; callers cannot substitute a new anchor.
        explicit = self.make(previous_meter_anchor=prepared['meter_anchor'])
        self.assertEqual(explicit['provenance'], self.make()['provenance'])
        bad = copy.deepcopy(prepared['meter_anchor']); bad['final_writeback_rates']['R_D_W'] = 1800.
        with self.assertRaisesRegex(ValueError, 'proof changed'):
            self.make(previous_meter_anchor=bad)

    def test_factory_rejects_previous_without_historical_proof(self):
        self.previous = copy.deepcopy(self.initial)
        with self.assertRaisesRegex(ValueError, 'anchor proof required'):
            self.make()

    def test_context_physical_definition_price_and_leader_changes_fail_closed(self):
        for obj, key, value in ((self.context, 'source', 'changed'),
                (self.follower.metering_marginal_price_ref, 'R_D_E', 30.),
                (vars(self.leader), 'N_UF_star', 1.),
                (self.actuation['real_world_ramp_metering'], 'cycle_sec', 11.)):
            before = copy.deepcopy(obj)
            obj[key] = value
            with self.assertRaisesRegex(ValueError, 'changed'):
                self.callbacks['neighbors']('SC1', self.initial, self.context)
            obj.clear(); obj.update(before)

    def test_explicit_hard_budget_does_not_rewrite_previous_or_incumbent(self):
        callback = self.make(total_budget={'mode': 'equality', 'veh_h': self.leader.N_UF_star})
        before = copy.deepcopy(vars(self.previous))
        with self.assertRaises(meters.MeterCandidateInfeasible):
            callback['neighbors']('SC1', self.initial, self.context)
        self.assertEqual(vars(self.previous), before)
        self.assertEqual(self.initial.N_UF_star, 7200.)
        self.assertNotEqual(self.initial.N_UF_star, self.leader.N_UF_star)

    def test_runtime_scope_restored_on_callback_failure_and_bad_vsl_resolution(self):
        original_identity = self.runtime['values']
        def bad(control, link, index, cfg):
            self.runtime['values'].append('error')
            raise RuntimeError('intentional callback error')
        with self.assertRaisesRegex(RuntimeError, 'intentional'):
            self.make(segment_vsl_func=bad)['physical_rows'](self.initial)
        self.assertIs(self.runtime['values'], original_identity)
        self.assertEqual(self.runtime['values'], [])
        with self.assertRaisesRegex(ValueError, 'Runtime VSL command differs'):
            self.make(segment_vsl_func=lambda *args: 80.)['physical_rows'](self.initial)
        self.assertEqual(self.scope_stats['entered'], self.scope_stats['exited'])

    def test_source_restored_before_nested_live_runtime_fingerprint(self):
        runtime = self.runtime
        parent = type(self.follower._wu)
        class MutatingSource(parent):
            def _relaxed_freeway_segment_candidates(self, *args):
                runtime['values'].append('temporary source lane context')
                return super()._relaxed_freeway_segment_candidates(*args)
        self.follower._wu.__class__ = MutatingSource
        # Root fingerprints LIVE uppercase runtime globals, not only the initial
        # frozen dict. A wide outer scope alone fails at the next nested guard.
        def live_fingerprint(context):
            return module._key({'frozen': context, 'live_runtime': runtime})
        callback = self.make(context_fingerprint=live_fingerprint)
        result = callback['neighbors']('FW_E', self.initial, self.context)
        self.assertTrue(result.complete)
        self.assertGreater(len(result.candidates), 1)
        self.assertEqual(runtime['values'], [])
        self.assertEqual(self.scope_stats['entered'], self.scope_stats['exited'])

    def test_actual_meter_partial_quantization_rejections_and_foreign_preservation(self):
        # Greater actual demand yields partial allocations; no synthetic meter
        # realizer is substituted. Explicit physical failures remain rejections.
        raw = self.cfg.network.control_area_meter_context['raw']
        volumes = raw['local_observation']['far_measurement']['link_volume_veh_h']
        volumes.update({k: 1500. for k in volumes})
        self.initial.ramp_metering = {r: 1500. for r in self.initial.ramp_metering}
        self.initial = meters.prepare_canonical_candidate(self.initial, self.cfg,
            owned_ramps=tuple(self.cfg.network.ramps), total_budget=None,
            directional_budgets={}, budget_tolerance_veh_h=1e-9)
        self.previous = self.historical_reference(self.initial, self.cfg)['previous']
        callbacks = self.make()
        result = callbacks['neighbor_evidence']('FW_E', self.initial, self.context)
        self.assertTrue(result['complete'])
        self.assertTrue(result['source_bundle']['incumbent_feasible'])
        self.assertTrue(any(c.ramp_metering != self.initial.ramp_metering for c in result['candidates']))
        self.assertTrue(any(r['stage'] == 'realized' for r in result['source_bundle']['rejected']))

    def test_only_known_candidate_infeasibility_is_recorded_other_failures_propagate(self):
        original = meters.prepare_canonical_candidate
        def fail_changed(action, *args, **kwargs):
            if action.ramp_metering != self.initial.ramp_metering:
                raise meters.MeterCandidateInfeasible('explicit synthetic physical rejection')
            return original(action, *args, **kwargs)
        with patch.object(meters, 'prepare_canonical_candidate', fail_changed):
            result = self.callbacks['neighbor_evidence']('FW_E', self.initial, self.context)
        self.assertTrue(result['complete'])
        self.assertTrue(any(r['stage'] == 'canonical_realization' for r in result['source_bundle']['rejected']))
        def unexpected(action, *args, **kwargs):
            if action.ramp_metering != self.initial.ramp_metering:
                raise RuntimeError('unexpected allocation failure')
            return original(action, *args, **kwargs)
        with patch.object(meters, 'prepare_canonical_candidate', unexpected), self.assertRaisesRegex(RuntimeError, 'unexpected'):
            self.callbacks['neighbors']('FW_E', self.initial, self.context)


if __name__ == '__main__':
    unittest.main()
