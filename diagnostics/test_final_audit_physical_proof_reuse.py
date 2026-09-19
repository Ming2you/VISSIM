"""Exact frozen physical proof reuse; synthetic games and existing fake endpoint."""
import copy
import json
import pickle
import unittest
from unittest.mock import patch

from diagnostics.test_joint_owner_game_candidate import action, catalog, feasible, physical_tokens, run
from diagnostics.test_joint_owner_game_round_robin import domain
from diagnostics import test_selected_final_audit_runtime as runtime_fixtures
from evaluation.controllers import joint_owner_game as game


class PhysicalInventoryTests(unittest.TestCase):
    def prepare(self, *, reuse=True, count=4, guard=None, context=None):
        own = catalog(('A', 'B'))
        initial = action(own)
        context = {} if context is None else context
        calls = []
        def physical(u, c):
            calls.append(pickle.dumps(u, protocol=5))
            return physical_tokens(own, u, c)
        prepared = game.prepare_final_audit_domains(own, initial, context,
            neighbors=domain({'A': count, 'B': count}),
            context_fingerprint=lambda c: json.dumps(c, sort_keys=True),
            physical_fingerprint=physical, reuse_physical_proofs=reuse,
            physical_proof_guard=guard or (lambda c: None))
        return own, initial, context, physical, calls, prepared

    def test_more_than_256_actions_keep_exact_full_gap_without_repeat_physical_queries(self):
        def solve(reuse):
            own, initial, ctx, physical, calls, prepared = self.prepare(reuse=reuse, count=130)
            before = len(calls)
            result = run(own, initial, lambda who, u, c: feasible(200-u['offsets'][who]),
                context=ctx, neighbors=prepared['neighbors'], audit_only=True,
                physical_fingerprint=prepared.get('physical_fingerprint', physical),
                max_evaluations=prepared['evaluation_budget'])
            return result, len(calls)-before, prepared
        old, old_calls, _ = solve(False)
        new, new_calls, prepared = solve(True)
        self.assertEqual(new, old)
        self.assertGreater(old_calls, 256)
        self.assertEqual(new_calls, 0)
        self.assertEqual(prepared['proof']['physical_proof_reuse']['exact_full_action_count'], 261)
        self.assertTrue(new['final_check_complete'])
        self.assertEqual(new['maximum_finite_candidate_gap'], 130.)

    def test_returned_tokens_and_domain_cannot_poison_later_reads(self):
        own, initial, ctx, _, calls, prepared = self.prepare()
        get = prepared['physical_fingerprint']
        expected = physical_tokens(own, initial, ctx)
        first = get(copy.deepcopy(initial), ctx)
        first['A'] = 'poison'
        self.assertEqual(get(initial, ctx), expected)
        neighborhood = prepared['neighbors']('A', initial, ctx)
        neighborhood.candidates[1]['diagnostics']['changed_payload'] = True
        with self.assertRaisesRegex(ValueError, 'exact inventoried full action'):
            get(neighborhood.candidates[1], ctx)
        self.assertNotIn('changed_payload', prepared['neighbors']('A', initial, ctx).candidates[1]['diagnostics'])

    def test_context_and_hidden_physical_bindings_still_guard_every_reuse(self):
        hidden, checked = {'writer': 'fixed'}, []
        def guard(c):
            checked.append(True)
            if hidden['writer'] != 'fixed':
                raise ValueError('physical writer binding changed')
        _, initial, ctx, _, _, prepared = self.prepare(guard=guard)
        prepared['physical_fingerprint'](initial, ctx)
        self.assertTrue(checked)
        hidden['writer'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'physical writer binding changed'):
            prepared['physical_fingerprint'](initial, ctx)
        hidden['writer'] = 'fixed'
        ctx['price'] = 2.
        with self.assertRaisesRegex(ValueError, 'frozen context changed'):
            prepared['physical_fingerprint'](initial, ctx)

    def test_unknown_targets_and_equal_levers_with_changed_payload_are_not_keys(self):
        _, initial, ctx, _, _, prepared = self.prepare()
        for field, value in (('N_P_star', 8.), ('N_UF_star', 10.), ('diagnostics', {'new': 1})):
            wrong = copy.deepcopy(initial)
            wrong[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                prepared['physical_fingerprint'](wrong, ctx)

    def test_default_inventory_keeps_original_result_fields(self):
        *_, prepared = self.prepare(reuse=False)
        self.assertEqual(set(prepared), {'neighbors', 'evaluation_budget', 'proof'})
        self.assertNotIn('physical_proof_reuse', prepared['proof'])
        own, initial = catalog(), action(catalog())
        with self.assertRaisesRegex(ValueError, 'original physical binding guard'):
            game.prepare_final_audit_domains(own, initial, {}, neighbors=domain({'A': 1, 'B': 1}),
                context_fingerprint=lambda c: '{}', physical_fingerprint=lambda u, c: {},
                reuse_physical_proofs=True)


class RuntimeProofReuseTests(unittest.TestCase):
    def test_scheduled_audit_preserves_final_score_and_all_owner_records(self):
        fixture = runtime_fixtures.SelectedAuditIntegrationTests()
        fixture.setUp()
        f = fixture.f
        f.follower.cfg.network.control_area_response_scheduling = {'lookahead': 4, 'final_check_reserve_sec': 0.}
        f.follower.cfg.network.control_area_reuse_final_audit_physical_proofs = True
        guarded = []
        f.callbacks['guard_physical_proofs'] = lambda c: guarded.append(True)
        original_prepare = game.prepare_final_audit_domains
        def without_reuse(*args, **kwargs):
            result = original_prepare(*args, **{**kwargs, 'reuse_physical_proofs': False})
            result['physical_fingerprint'] = kwargs['physical_fingerprint']
            return result
        query, _, _ = f.full_sweep_query()
        # Identical frozen config on both arms: compare physical work paths,
        # without manufacturing a context-token match after a config change.
        with patch.object(game, 'prepare_final_audit_domains', without_reuse):
            old = fixture.run_fixed(f.action, audit_only=True, response_query=query)
        query, _, _ = f.full_sweep_query()
        new = fixture.run_fixed(f.action, audit_only=True, response_query=query)
        self.assertTrue(guarded)
        for key in ('final_action_token', 'final_score', 'command_evidence'):
            self.assertEqual(new[key], old[key])
        for key in ('per_owner', 'evaluations', 'maximum_finite_candidate_gap', 'accepted_updates', 'final_check_complete'):
            self.assertEqual(new['game'][key], old['game'][key])
        self.assertEqual(new['queries']['bounded_response_schedule']['unconsumed_prefetched_actions'], 0)
        self.assertTrue(new['final_audit_domain_inventory']['physical_proof_reuse']['enabled'])


if __name__ == '__main__':
    unittest.main()
