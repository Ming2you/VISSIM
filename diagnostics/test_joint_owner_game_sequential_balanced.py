"""Bounded coordinate search: fresh complete actions, no model/native imports."""
from copy import deepcopy
import unittest

from diagnostics.test_joint_owner_game_candidate import Clock, action, catalog, feasible, run, physical_tokens
from diagnostics.test_joint_owner_game_round_robin import domain
from evaluation.controllers.joint_owner_game import (Address, Ownership, Evaluation, Neighborhood,
                                                   prepare_final_audit_domains)
from evaluation.controllers.joint_owner_neighbors import prioritize_lever_representatives


class SequentialBalancedTests(unittest.TestCase):
    def test_each_next_owner_is_regenerated_at_accepted_action(self):
        own = catalog(('A', 'B', 'C')); initial = action(own); bases = []
        producer = domain({'A': 100, 'B': 100, 'C': 100})
        def neighbors(owner, base, ctx):
            bases.append((owner, deepcopy(base['offsets'])))
            return producer(owner, base, ctx)
        result = run(own, initial, lambda owner, u, ctx: feasible(100-u['offsets'][owner]),
                     neighbors=neighbors, traversal='sequential_balanced',
                     search_owner_candidate_limit=2, max_sweeps=1, max_evaluations=9)
        self.assertEqual(bases, [('A', {'A': 0., 'B': 0., 'C': 0.}),
                                 ('B', {'A': 2., 'B': 0., 'C': 0.}),
                                 ('C', {'A': 2., 'B': 2., 'C': 0.})])
        self.assertEqual(result['control']['offsets'], {'A': 2., 'B': 2., 'C': 2.})
        self.assertEqual([u['owner'] for u in result['accepted_updates']], ['A', 'B', 'C'])
        self.assertTrue(all(not u['owner_domain_complete'] for u in result['accepted_updates']))
        self.assertTrue(all(r['gap'] is None and r['status'] == 'owner_candidate_limit'
                            for r in result['search_sweeps'][0]['owners'].values()))
        self.assertEqual(result['error']['phase'], 'final_check')
        self.assertFalse(result['certified']); self.assertIsNone(result['maximum_finite_candidate_gap'])
        self.assertEqual(initial, action(own))

    def test_shared_constraint_rechecked_prevents_combining_isolated_moves(self):
        own = catalog(); initial = action(own); seen = []
        def score(owner, u, ctx):
            seen.append((owner, deepcopy(u['offsets'])))
            if sum(u['offsets'].values()) > 1:
                return Evaluation(False, None, 1., True, 'joint shared capacity')
            return feasible(1-u['offsets'][owner])
        result = run(own, initial, score, traversal='sequential_balanced',
                     search_owner_candidate_limit=1, max_sweeps=1)
        self.assertEqual(result['control']['offsets'], {'A': 1., 'B': 0.})
        self.assertEqual([u['owner'] for u in result['accepted_updates']], ['A'])
        self.assertIn(('B', {'A': 1., 'B': 1.}), seen)
        self.assertTrue(result['certified'], result['error'])

    def test_final_audit_finds_improvement_outside_search_prefix_without_adopting_it(self):
        own = catalog(('A',)); initial = action(own)
        result = run(own, initial, lambda owner, u, ctx: feasible(10-u['offsets'][owner]),
                     neighbors=domain({'A': 3}), traversal='sequential_balanced',
                     search_owner_candidate_limit=1, max_sweeps=1)
        self.assertEqual(result['control']['offsets']['A'], 1.)
        self.assertTrue(result['final_check_complete'])
        self.assertEqual(result['maximum_finite_candidate_gap'], 2.)
        self.assertFalse(result['certified'])
        self.assertEqual(result['search_sweeps'][0]['owners']['A']['observed_gap_lower_bound'], 1.)

    def test_no_prefix_improvement_is_not_a_complete_search_claim(self):
        own = catalog(('A',)); initial = action(own)
        result = run(own, initial, lambda owner, u, ctx: feasible(0 if u['offsets']['A'] < 2 else -1),
                     neighbors=domain({'A': 3}), traversal='sequential_balanced',
                     search_owner_candidate_limit=1)
        self.assertEqual(result['search_status'], 'no_strict_improvement_in_checked_prefixes')
        self.assertEqual(result['control'], initial)
        self.assertEqual(result['maximum_finite_candidate_gap'], 1.)
        self.assertFalse(result['certified'])

    def test_none_limit_exhausts_domain_and_final_audit_can_certify(self):
        own = catalog(('A',)); initial = action(own)
        result = run(own, initial, lambda owner, u, ctx: feasible(10-u['offsets'][owner]),
                     neighbors=domain({'A': 3}), traversal='sequential_balanced', max_sweeps=1)
        self.assertEqual(result['control']['offsets']['A'], 3.)
        self.assertTrue(result['search_sweeps'][0]['owners']['A']['complete'])
        self.assertTrue(result['certified'], result['error'])

    def test_late_candidate_and_changed_context_are_not_adopted(self):
        own = catalog(('A',)); initial = action(own)
        for mutation in (False, True):
            clock = Clock(); ctx = {'fixed_price': 1}
            def score(owner, u, context):
                if u['offsets']['A']:
                    if mutation: context['fixed_price'] = 2
                    else: clock.value = 11.
                return feasible(10-u['offsets']['A'])
            result = run(own, initial, score, context=ctx, clock=clock,
                         traversal='sequential_balanced', search_owner_candidate_limit=1)
            self.assertEqual(result['control'], initial)
            self.assertFalse(result['certified'])
            self.assertEqual(result['error']['kind'], 'context_changed' if mutation else 'time_budget')

    def test_invalid_limit_does_not_silently_change_legacy_traversal(self):
        own = catalog(); initial = action(own)
        for value in (0, -1, True, 1.5):
            with self.assertRaisesRegex(ValueError, 'search_owner_candidate_limit'):
                run(own, initial, lambda *args: feasible(0),
                    traversal='sequential_balanced', search_owner_candidate_limit=value)
        with self.assertRaisesRegex(ValueError, 'search_owner_candidate_limit'):
            run(own, initial, lambda *args: feasible(0), search_owner_candidate_limit=1)


class RepresentativeNeighborTests(unittest.TestCase):
    def test_first_three_include_pure_vsl_g8_and_existing_coupled_action(self):
        own = Ownership(('FW_E',), (Address('vsl', 'v', 'FW_E', 'strategy'),
                                  Address('ramp_metering', 'r', 'FW_E', 'strategy')), ())
        initial = action(own); initial['vsl']['v'] = 120.; initial['ramp_metering']['r'] = 1512.
        candidates = [deepcopy(initial)]
        for vsl, meter in ((100., 1328.4), (100., 1512.), (120., 1328.4),
                           (120., 1166.4), (80., 1512.)):
            u = deepcopy(initial); u['vsl']['v'] = vsl; u['ramp_metering']['r'] = meter
            candidates.append(u)
        original = deepcopy(candidates)
        neighborhood = Neighborhood(tuple(candidates), True, 'same realized finite set')
        ordered = prioritize_lever_representatives(own, 'FW_E', initial, neighborhood)
        self.assertEqual(ordered.candidates[:4], tuple(candidates[i] for i in (0, 5, 4, 1)))
        self.assertCountEqual(ordered.candidates, neighborhood.candidates)
        self.assertEqual(candidates, original)
        self.assertTrue(ordered.complete)

    def test_missing_family_does_not_create_synthetic_candidate(self):
        own = catalog(('A',)); initial = action(own)
        n = domain({'A': 2})('A', initial, {})
        # The realizer supplies a deduplicated domain; the ordering rejects
        # unchanged nonfirst entries but preserves equal nontrivial payloads.
        ordered = prioritize_lever_representatives(own, 'A', initial, n)
        self.assertEqual(ordered.candidates[1]['offsets']['A'], 2.)
        self.assertCountEqual(ordered.candidates, n.candidates)

    def test_foreign_or_unchanged_nonfirst_neighbor_rejected(self):
        own = catalog(); initial = action(own)
        candidate = deepcopy(initial); candidate['offsets']['B'] = 1.
        with self.assertRaises(ValueError):
            prioritize_lever_representatives(own, 'A', initial,
                Neighborhood((initial, candidate), True, 'invalid'))
        with self.assertRaises(ValueError):
            prioritize_lever_representatives(own, 'A', initial,
                Neighborhood((initial, deepcopy(initial)), True, 'duplicate incumbent'))


class DeferredFinalAuditTests(unittest.TestCase):
    def prepare(self, own, initial, producer, ctx=None, physical=None):
        import json
        context = {} if ctx is None else ctx
        return prepare_final_audit_domains(own, initial, context, neighbors=producer,
            context_fingerprint=lambda c: json.dumps(c, sort_keys=True),
            physical_fingerprint=physical or (lambda u, c: physical_tokens(own, u, c)),
            traversal='sequential_balanced')

    def test_deferred_selected_audit_matches_original_control_payoffs_and_final_gaps(self):
        own = catalog(('A', 'B', 'C')); initial = action(own)
        producer = domain({'A': 4, 'B': 4, 'C': 4}); calls = []
        def score(owner, u, ctx):
            calls.append((owner, deepcopy(u['offsets'])))
            return feasible((4-u['offsets'][owner])**2)
        opts = dict(neighbors=producer, traversal='sequential_balanced',
                    search_owner_candidate_limit=2, max_sweeps=1)
        full = run(own, initial, score, **opts); full_calls = list(calls); calls.clear()
        deferred = run(own, initial, score, defer_final_audit=True, **opts)
        search_calls = list(calls)
        prepared = self.prepare(own, deferred['control'], producer)
        self.assertEqual(calls, search_calls)  # Inventory never evaluates payoffs.
        audited = run(own, deferred['control'], score, neighbors=prepared['neighbors'],
                      traversal='sequential_balanced', max_evaluations=prepared['evaluation_budget'],
                      audit_only=True)
        self.assertEqual(calls, full_calls)
        self.assertEqual(deferred['control'], full['control'])
        self.assertEqual(deferred['accepted_updates'], full['accepted_updates'])
        self.assertEqual(audited['control'], full['control'])
        self.assertEqual(audited['per_owner'], full['per_owner'])
        self.assertEqual(audited['maximum_finite_candidate_gap'], full['maximum_finite_candidate_gap'])
        self.assertEqual(audited['certified'], full['certified'])
        self.assertEqual(audited['evaluations'], prepared['evaluation_budget'])
        self.assertEqual(audited['sweeps_started'], 0); self.assertEqual(audited['sweeps_completed'], 0)
        self.assertEqual(audited['accepted_updates'], [])
        self.assertTrue(deferred['final_audit_deferred'])
        self.assertTrue(all(r['gap'] is None and r['status'] == 'deferred'
                            for r in deferred['per_owner'].values()))
        self.assertFalse(deferred['certified'])
        self.assertEqual(prepared['proof']['payoff_evaluations'], 0)

    def test_exact_budget_accounts_for_incumbents_and_duplicate_actions(self):
        own = catalog(); initial = action(own); producer = domain({'A': 2, 'B': 3})
        prepared = self.prepare(own, initial, producer)
        self.assertEqual(prepared['evaluation_budget'], 7)  # two baselines + five neighbors
        self.assertEqual(prepared['proof']['per_owner']['A']['duplicate_count'], 3)
        audit = run(own, initial, lambda *args: feasible(0), neighbors=prepared['neighbors'],
                    traversal='sequential_balanced', max_evaluations=7, audit_only=True)
        self.assertTrue(audit['certified'], audit['error'])
        short = run(own, initial, lambda *args: feasible(0), neighbors=prepared['neighbors'],
                    traversal='sequential_balanced', max_evaluations=6, audit_only=True)
        self.assertFalse(short['final_check_complete'])
        self.assertIsNone(short['maximum_finite_candidate_gap'])

    def test_budget_stopped_search_still_explicitly_defers_and_can_audit_its_checked_control(self):
        own = catalog(); initial = action(own); producer = domain({'A': 4, 'B': 4})
        score = lambda owner, u, ctx: feasible(4-u['offsets'][owner])
        deferred = run(own, initial, score, neighbors=producer,
                       traversal='sequential_balanced', search_owner_candidate_limit=1,
                       max_evaluations=2, defer_final_audit=True)
        self.assertEqual(deferred['error']['kind'], 'evaluation_budget')
        self.assertTrue(deferred['final_audit_deferred'])
        prepared = self.prepare(own, deferred['control'], producer)
        audit = run(own, deferred['control'], score, neighbors=prepared['neighbors'],
                    traversal='sequential_balanced', max_evaluations=prepared['evaluation_budget'],
                    audit_only=True)
        self.assertTrue(audit['final_check_complete'], audit['error'])
        self.assertFalse(audit['certified'])  # Positive finite deviations remain visible.

    def test_inventory_rejects_incomplete_domain_or_foreign_physical_write(self):
        own = catalog(); initial = action(own)
        with self.assertRaisesRegex(ValueError, 'complete materialized'):
            self.prepare(own, initial, lambda *args: Neighborhood((), False, 'unfinished'))
        def physical(u, ctx):
            values = physical_tokens(own, u, ctx)
            if u['offsets']['A']: values['B'] = 'changed foreign command'
            return values
        with self.assertRaisesRegex(ValueError, 'another owner physical'):
            self.prepare(own, initial, domain({'A': 1}), physical=physical)

    def test_prepared_domains_reject_changed_incumbent_context_and_copy_mutations(self):
        own = catalog(); initial = action(own); ctx = {'price': 1}
        prepared = self.prepare(own, initial, domain({'A': 2}), ctx)
        private = prepared['neighbors']('A', initial, ctx)
        private.candidates[1]['offsets']['A'] = 99.
        self.assertEqual(prepared['neighbors']('A', initial, ctx).candidates[1]['offsets']['A'], 1.)
        moved = deepcopy(initial); moved['offsets']['B'] = 1.
        with self.assertRaisesRegex(ValueError, 'one unchanged final action'):
            prepared['neighbors']('A', moved, ctx)
        ctx['price'] = 2
        with self.assertRaisesRegex(ValueError, 'context changed'):
            prepared['neighbors']('A', initial, ctx)

    def test_default_flags_preserve_full_results_and_incompatible_flags_fail(self):
        own = catalog(); initial = action(own); score = lambda *args: feasible(0)
        self.assertEqual(run(own, initial, score),
                         run(own, initial, score, audit_only=False, defer_final_audit=False))
        for options in ({'audit_only': True, 'defer_final_audit': True},
                        {'audit_only': 1}, {'defer_final_audit': 'yes'}):
            with self.assertRaisesRegex(ValueError, 'mutually exclusive'):
                run(own, initial, score, **options)


if __name__ == '__main__':
    unittest.main()
