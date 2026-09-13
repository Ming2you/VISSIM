"""Small abstract 2/3-owner games only; no traffic/model/COM imports."""
from copy import deepcopy
import json
import math
import unittest

from evaluation.controllers.joint_owner_game import (
    Address, Ownership, Evaluation, Neighborhood, solve,
)


class Clock:
    def __init__(self): self.value = 0.
    def __call__(self): return self.value


def catalog(names=('A', 'B'), joint=False):
    addresses = [Address('offsets', owner, owner, 'strategy') for owner in names]
    if joint:
        addresses.append(Address('green_times', 'A_p1', 'A', 'strategy'))
    return Ownership(tuple(names), tuple(addresses), ())


def action(ownership):
    u = {'green_times': {}, 'offsets': {}, 'vsl': {}, 'ramp_metering': {},
         'N_P_star': 7., 'N_UF_star': 9., 'inflow_outflow_allocation': {}, 'diagnostics': {}}
    for address in ownership.addresses:
        u[address.field][address.key] = 0.
    return u


def toggles(owner, incumbent, ctx):
    candidate = deepcopy(incumbent)
    candidate['offsets'][owner] = 1. - candidate['offsets'][owner]
    return Neighborhood((deepcopy(incumbent), candidate, deepcopy(candidate)), True, 'own binary offset')


def feasible(cost):
    return Evaluation(True, float(cost), 0., True)


def physical_tokens(ownership, u, ctx):
    # Abstract physical schedules only; production must use canonical writer
    # rows plus its plan/mapping/source context, not this synthetic schema.
    return {owner: json.dumps({
        'values': [(a.field, a.key, u[a.field][a.key])
                   for a in ownership.addresses if a.owner == owner],
        'schedule': u['diagnostics'].get('physical_schedules', {}).get(owner, 0),
        'context': ctx,
    }, sort_keys=True) for owner in ownership.owners}


def run(ownership, initial, score, *, neighbors=toggles, context=None, **limits):
    cfg = dict(max_sweeps=5, max_evaluations=100, time_budget_sec=10.,
               improvement_tolerance=0., shared_tolerance=0., scope_label='synthetic finite game', clock=Clock())
    cfg.update(limits)
    cfg.setdefault('physical_fingerprint', lambda u, ctx: physical_tokens(ownership, u, ctx))
    return solve(ownership, initial, {} if context is None else context, neighbors=neighbors, evaluate=score,
                 context_fingerprint=lambda c: json.dumps(c, sort_keys=True), **cfg)


class FiniteJointOwnerTests(unittest.TestCase):
    @staticmethod
    def meter_game():
        own = Ownership(('A', 'B'), tuple(
            Address('ramp_metering', owner + str(i), owner, 'strategy')
            for owner in ('A', 'B') for i in (1, 2)), ())
        initial = action(own)
        initial['ramp_metering'] = {a.key: 1000. for a in own.addresses}
        initial['N_UF_star'] = 4000.
        return own, initial

    @staticmethod
    def meter_neighbors(owner, u, ctx):
        v = deepcopy(u)
        if owner == 'A':
            v['ramp_metering'].update(A1=900., A2=800.)
            v['N_UF_star'] = math.fsum(v['ramp_metering'][r] for r in sorted(v['ramp_metering']))
        return Neighborhood((u, v), True, 'explicit owned meter pair')

    def test_explicit_realized_sum_accepts_owned_pair_without_changing_leader(self):
        own, initial = self.meter_game()
        ctx = {'leader_target_nuf_veh_h': 3900., 'lambda_uf': .1}
        before = deepcopy(ctx)
        score = lambda owner, u, c: feasible(sum(u['ramp_metering'][owner + str(i)] for i in (1, 2)))
        result = run(own, initial, score, context=ctx, neighbors=self.meter_neighbors,
                     nuf_semantics='realized_sum')
        self.assertTrue(result['certified'], result['error'])
        self.assertEqual(result['control']['ramp_metering'], {'A1': 900., 'A2': 800., 'B1': 1000., 'B2': 1000.})
        self.assertEqual(result['control']['N_UF_star'], 3700.)
        self.assertEqual(result['control']['N_P_star'], initial['N_P_star'])
        self.assertEqual(ctx, before)
        self.assertEqual(initial, self.meter_game()[1])
        # The same sum-changing neighbor remains invalid in the prepared mode.
        old = run(own, initial, score, context=ctx, neighbors=self.meter_neighbors)
        self.assertFalse(old['certified'])
        self.assertEqual(old['error']['kind'], 'callback_mutation')
        self.assertEqual(old['control'], initial)

    def test_realized_sum_rejects_incorrect_alias_np_and_foreign_changes(self):
        own, initial = self.meter_game()
        for mutation in (
                lambda v: v.update(N_UF_star=999.),
                lambda v: v.update(N_P_star=8.),
                lambda v: (v['ramp_metering'].update(B1=900.), v.update(N_UF_star=3600.)),
                lambda v: v['inflow_outflow_allocation'].update(other=1.)):
            def neighbors(owner, u, ctx):
                v = deepcopy(self.meter_neighbors(owner, u, ctx).candidates[-1])
                mutation(v)
                return Neighborhood((v,), True, 'invalid derived/frozen candidate')
            result = run(own, initial, lambda *args: feasible(0), neighbors=neighbors,
                         nuf_semantics='realized_sum')
            self.assertFalse(result['certified'])
            self.assertIsNotNone(result['error'])
            self.assertIsNone(result['maximum_finite_candidate_gap'])
            self.assertEqual(result['control'], initial)
        bad = deepcopy(initial); bad['N_UF_star'] = 3999.
        with self.assertRaisesRegex(ValueError, 'exact realized full meter sum'):
            run(own, bad, lambda *args: feasible(0), nuf_semantics='realized_sum')
        with self.assertRaisesRegex(ValueError, 'nuf_semantics'):
            run(own, initial, lambda *args: feasible(0), nuf_semantics='unchecked')

    def test_realized_sum_evaluator_and_producer_mutations_still_fail(self):
        own, initial = self.meter_game()
        def score(owner, u, ctx):
            u['N_UF_star'] += 1.
            return feasible(0)
        evaluated = run(own, initial, score, neighbors=self.meter_neighbors,
                        nuf_semantics='realized_sum')
        self.assertFalse(evaluated['certified'])
        self.assertIsNotNone(evaluated['error'])
        def neighbors(owner, u, ctx):
            u['ramp_metering']['A1'] = 900.
            u['N_UF_star'] = 3900.
            return Neighborhood((u,), True, 'mutated supplied incumbent')
        generated = run(own, initial, lambda *args: feasible(0), neighbors=neighbors,
                        nuf_semantics='realized_sum')
        self.assertFalse(generated['certified'])
        self.assertEqual(generated['error']['kind'], 'callback_mutation')
        self.assertEqual(initial, self.meter_game()[1])

    def test_equal_rates_different_physical_schedules_are_not_deduped(self):
        own = catalog(); initial = action(own)
        def neighbors(owner, u, ctx):
            if owner == 'B': return Neighborhood((u,), True, 'inert B')
            values = []
            for schedule in (0, 1):
                v = deepcopy(u)
                v['diagnostics']['physical_schedules'] = {'A': schedule}
                values.append(v)
            return Neighborhood(tuple(values), True, 'two physical schedules with unchanged rates')
        def score(owner, u, ctx):
            return feasible(1 - u['diagnostics'].get('physical_schedules', {}).get(owner, 0))
        result = run(own, initial, score, neighbors=neighbors)
        self.assertTrue(result['certified'])
        self.assertEqual(result['control']['offsets'], initial['offsets'])
        self.assertEqual(result['control']['ramp_metering'], initial['ramp_metering'])
        self.assertEqual(result['control']['diagnostics']['physical_schedules'], {'A': 1})
        self.assertEqual(result['per_owner']['A']['unique_neighbors'], 1)
        self.assertEqual(len(result['accepted_updates']), 1)

    def test_physical_schedule_mutations_are_rejected_but_output_diagnostics_are_allowed(self):
        own = catalog(); initial = action(own)
        def bad_foreign(owner, u, ctx):
            v = deepcopy(u); v['diagnostics']['physical_schedules'] = {'B': 1}
            return Neighborhood((v,), True, 'foreign physical schedule')
        foreign = run(own, initial, lambda *args: feasible(0), neighbors=bad_foreign)
        self.assertEqual(foreign['error']['kind'], 'callback_mutation')
        def bad_eval(owner, u, ctx):
            u['diagnostics']['physical_schedules'] = {owner: 1}
            return feasible(0)
        evaluated = run(own, initial, bad_eval)
        self.assertEqual(evaluated['error']['kind'], 'callback_mutation')
        def bad_neighbors(owner, u, ctx):
            u['diagnostics']['physical_schedules'] = {owner: 1}
            return Neighborhood((u,), True, 'mutated incumbent schedule')
        generated = run(own, initial, lambda *args: feasible(0), neighbors=bad_neighbors)
        self.assertEqual(generated['error']['kind'], 'callback_mutation')
        def harmless(owner, u, ctx):
            u['diagnostics']['audit_only'] = 'query output'
            return feasible(0)
        safe = run(own, initial, harmless)
        self.assertTrue(safe['certified'])
        self.assertEqual(initial, action(own))

    def test_physical_fingerprint_requires_exact_catalog_coverage_and_valid_tokens(self):
        own = catalog(); initial = action(own)
        for result in ({'A': 'ok'}, {'A': '', 'B': 'ok'}, {'A': 'ok', 'B': None},
                       {'A': 'ok', 'B': 'ok', 'extra': 'no'}):
            failed = run(own, initial, lambda *args: feasible(0),
                         physical_fingerprint=lambda *args, result=result: result)
            self.assertFalse(failed['certified'])
            self.assertEqual(failed['error']['kind'], 'callback_contract_failure')
            self.assertEqual(failed['evaluations'], 0)

    def test_revisit_owner_after_other_owner_changes(self):
        own = catalog(); initial = action(own); calls = []
        def score(owner, u, ctx):
            a, b = u['offsets']['A'], u['offsets']['B']
            calls.append((owner, a, b))
            return feasible((a-b)**2 if owner == 'A' else (1-b)**2)
        result = run(own, initial, score)
        self.assertEqual(result['control']['offsets'], {'A': 1., 'B': 1.})
        self.assertEqual([(r['sweep'], r['owner']) for r in result['accepted_updates']], [(1, 'B'), (2, 'A')])
        self.assertTrue(result['certified'])
        self.assertEqual(result['maximum_finite_candidate_gap'], 0.)
        self.assertEqual(result['evaluations'], len(calls))
        self.assertEqual(initial, action(own))
        # The final four queries all share final controls except the tested
        # owner's deviation; other actors' previous flows were not fixed here.
        self.assertEqual(calls[-4:], [('A', 1., 1.), ('A', 0., 1.), ('B', 1., 1.), ('B', 1., 0.)])

    def test_joint_only_improvement_is_kept_as_one_owner_move(self):
        own = catalog(joint=True); initial = action(own)
        def neighbors(owner, u, ctx):
            if owner != 'A':
                return Neighborhood((u,), True, 'inert B')
            candidates = []
            for green, offset in ((0., 0.), (1., 0.), (0., 1.), (1., 1.)):
                v = deepcopy(u); v['green_times']['A_p1'] = green; v['offsets']['A'] = offset
                candidates.append(v)
            return Neighborhood(tuple(candidates), True, 'A full green x offset product')
        def score(owner, u, ctx):
            g, o = u['green_times']['A_p1'], u['offsets']['A']
            return feasible(0. if owner == 'B' or (g, o) == (1., 1.) else 1. if (g, o) == (0., 0.) else 2.)
        result = run(own, initial, score, neighbors=neighbors)
        self.assertTrue(result['certified'])
        self.assertEqual(result['control']['green_times']['A_p1'], 1.)
        self.assertEqual(result['control']['offsets']['A'], 1.)
        self.assertEqual(len(result['accepted_updates']), 1)
        self.assertTrue(result['per_owner']['B']['vacuous_no_feasible_nontrivial_neighbor'])

    def test_three_owners_all_visited_and_first_tie_kept_deterministically(self):
        own = catalog(('A', 'B', 'C')); initial = action(own)
        def neighbors(owner, u, ctx):
            values = []
            for number in (1., 2.):
                v = deepcopy(u); v['offsets'][owner] = number; values.append(v)
            return Neighborhood(tuple(values), True, 'two equal-cost alternatives')
        score = lambda owner, u, ctx: feasible(1. if u['offsets'][owner] == 0 else 0.)
        a = run(own, initial, score, neighbors=neighbors)
        b = run(own, initial, score, neighbors=neighbors)
        self.assertEqual(a, b)
        self.assertEqual(a['owner_count'], 3)
        self.assertEqual(a['control']['offsets'], {'A': 1., 'B': 1., 'C': 1.})
        self.assertTrue(all(row['complete'] for row in a['per_owner'].values()))

    def test_iteration_limit_final_recheck_exposes_profitable_revisit(self):
        own = catalog(); initial = action(own)
        def score(owner, u, ctx):
            a, b = u['offsets']['A'], u['offsets']['B']
            return feasible((a-b)**2 if owner == 'A' else (1-b)**2)
        result = run(own, initial, score, max_sweeps=1)
        self.assertTrue(result['iteration_limit_reached'])
        self.assertTrue(result['final_check_complete'])
        self.assertFalse(result['certified'])
        self.assertEqual(result['per_owner']['A']['gap'], 1.)
        self.assertEqual(result['maximum_finite_candidate_gap'], 1.)
        self.assertEqual(result['control']['offsets'], {'A': 0., 'B': 1.})

    def test_final_evaluation_budget_missing_owner_has_null_not_zero_gap(self):
        own = catalog()
        result = run(own, action(own), lambda owner, u, ctx: feasible(u['offsets'][owner]),
                     max_sweeps=1, max_evaluations=6)
        self.assertTrue(result['evaluation_budget_reached'])
        self.assertTrue(result['per_owner']['A']['complete'])
        self.assertFalse(result['per_owner']['B']['complete'])
        self.assertIsNone(result['per_owner']['B']['gap'])
        self.assertIsNone(result['maximum_finite_candidate_gap'])
        self.assertEqual(result['evaluations'], 6)
        self.assertFalse(result['certified'])

    def test_known_infeasible_deviations_are_explicit_and_vacuous(self):
        own = catalog()
        def score(owner, u, ctx):
            excess = sum(u['offsets'].values())
            return Evaluation(False, None, excess, True, 'declared joint capacity') if excess else feasible(0)
        result = run(own, action(own), score)
        self.assertTrue(result['certified'])
        self.assertEqual(result['max_shared_violation_seen_including_rejected'], 1.)
        for row in result['per_owner'].values():
            self.assertTrue(row['vacuous_no_feasible_nontrivial_neighbor'])
            self.assertEqual(row['infeasible_neighbors'], 1)
            self.assertEqual(row['rejected'][0]['reason'], 'declared joint capacity')

    def test_infeasible_initial_incumbent_is_not_a_certificate(self):
        own = catalog(); initial = action(own)
        result = run(own, initial, lambda *args: Evaluation(False, None, 1., True, 'initial infeasible'))
        self.assertEqual(result['error']['kind'], 'infeasible_incumbent')
        self.assertFalse(result['certified'])
        self.assertEqual(result['control'], initial)
        self.assertTrue(all(row['gap'] is None for row in result['per_owner'].values()))

    def test_incomplete_domain_witness_and_callback_failure_remain_uncertified(self):
        own = catalog(); initial = action(own)
        domain = lambda *args: Neighborhood((), False, 'truncated domain', 'candidate cap')
        a = run(own, initial, lambda *args: feasible(0), neighbors=domain)
        self.assertEqual(a['error']['kind'], 'incomplete_domain')
        b = run(own, initial, lambda *args: Evaluation(True, 0., 0., False, 'local/shared mismatch'))
        self.assertEqual(b['error']['kind'], 'incomplete_witness')
        def failure(*args): raise RuntimeError('oracle failed')
        c = run(own, initial, failure)
        self.assertEqual(c['error']['kind'], 'callback_failure')
        for result in (a, b, c):
            self.assertFalse(result['certified'])
            self.assertIsNone(result['maximum_finite_candidate_gap'])

    def test_time_deadline_before_dispatch_and_callback_overrun(self):
        own = catalog(); initial = action(own); calls = []
        score = lambda *args: calls.append(1) or feasible(0)
        before = run(own, initial, score, time_budget_sec=0.)
        self.assertEqual(before['evaluations'], 0)
        self.assertEqual(calls, [])
        clock = Clock()
        def slow(*args): clock.value = 2.; return feasible(0)
        late = run(own, initial, slow, clock=clock, time_budget_sec=1.)
        self.assertTrue(late['time_budget_reached'])
        self.assertEqual(late['evaluations'], 1)
        self.assertFalse(late['certified'])
        self.assertEqual(late['control'], initial)

    def test_foreign_owner_payload_and_callback_mutations_are_rejected(self):
        own = catalog(); initial = action(own)
        for mutation in (lambda u: u['offsets'].update(B=1.), lambda u: u.update(N_UF_star=99.)):
            def bad_neighbors(owner, u, ctx):
                v = deepcopy(u); mutation(v)
                return Neighborhood((v,), True, 'bad neighbor')
            result = run(own, initial, lambda *args: feasible(0), neighbors=bad_neighbors)
            self.assertFalse(result['certified'])
            self.assertIsNotNone(result['error'])
            self.assertEqual(result['control'], initial)
        def mutate(owner, u, ctx): u['offsets'][owner] = 1.; return feasible(0)
        result = run(own, initial, mutate)
        self.assertEqual(result['error']['kind'], 'callback_mutation')
        self.assertEqual(initial, action(own))

    def test_context_change_nonfinite_and_inconsistent_feasibility_rejected(self):
        own = catalog(); initial = action(own); context = {'price': 1.}
        def mutate(owner, u, ctx): ctx['price'] = 2.; return feasible(0)
        changed = run(own, initial, mutate, context=context)
        self.assertEqual(changed['error']['kind'], 'context_changed')
        for score in (lambda *args: feasible(float('nan')),
                      lambda *args: Evaluation(True, 0., 1., True)):
            result = run(own, initial, score)
            self.assertFalse(result['certified'])
            self.assertIsNotNone(result['error'])


if __name__ == '__main__':
    unittest.main()
