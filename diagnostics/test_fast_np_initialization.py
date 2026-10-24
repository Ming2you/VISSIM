"""Fast NP seed semantics and bounded restoration; synthetic checks, not fidelity."""
import copy
import itertools
import pickle
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from evaluation.controllers import area_follower_objective as subject
from evaluation.controllers import signal_actuation_contract as signals
from evaluation.controllers import joint_owner_game as game
from evaluation.controllers.joint_owner_neighbors import FixedMoveBox
from diagnostics.test_joint_decision_anchor import RestorationTests
from diagnostics.test_joint_owner_game_candidate import action, catalog


class FastNPTests(unittest.TestCase):
    def fixture(self):
        owners = tuple('SC'+str(i) for i in range(17))
        net = NS(signals=owners, signal_live_phases=lambda _: ('p1', 'p2', 'p3', 'p4'),
            signal_effective_green_total=lambda _: 120., signal_cycle_length=lambda _: 150.)
        ref = NS(green_times={s+'_'+p: 30. for s in owners for p in ('p1','p2','p3','p4')},
            offsets=dict.fromkeys(owners, 30.), vsl={'FW_E': 120., 'FW_W': 120.},
            ramp_metering={'meter': 1800.}, N_P_star=-250., N_UF_star=1900., diagnostics={})
        box = FixedMoveBox(tuple([('green_times', k, v, 6., None) for k,v in ref.green_times.items()]
            + [('offsets', k, v, 15., 150.) for k,v in ref.offsets.items()]), 'actual-anchor')
        return owners, net, ref, box

    def measurement(self, ref, owners, shared=False):
        def result(owner=None, direction=None):
            rows = {}
            for s in owners:
                d = direction if s == owner else {}
                a, b = d.get(s+'_p1', 0.), d.get(s+'_p2', 0.)
                c, o = d.get(s+'_p4', 0.), d.get(s, 0.)
                kinds = {'boundary_in': 100.+a, 'off_ramp': 10.,
                    'boundary_out': 100.+2*b+c+o+(3*a if shared else 0.), 'on_ramp': 20.,
                    'internal': 1e6 + 1000*a}
                rows[s] = {'by_kind_veh': kinds, 'net_inflow_veh': kinds['boundary_in']+10.-kinds['boundary_out']-20.}
            return {'quantities': {'schema': 'shared-urban-kind-service/v1', 'owners': rows,
                    'provenance': {'start_sec': 900., 'end_sec': 1350.}},
                'frozen_context_token': 'same-destination-queues-450-arrivals', 'response_token': str((owner, direction))}
        results, selections, secants = [result()], {}, {}
        for owner in owners:
            directions = []
            for p in ('p1','p2','p3'):
                directions.append({owner+'_p1': 0., owner+'_p2': 0., owner+'_p3': 0., owner+'_p4': -1., owner: 0.})
                directions[-1][owner+'_'+p] = 1.
            directions.append({owner+'_p1': 0., owner+'_p2': 0., owner+'_p3': 0., owner+'_p4': 0., owner: 1.})
            indices = []
            for direction in directions:
                indices.append(len(results)); results.append(result(owner, direction))
            selections[owner] = {'action_indices': indices}
            secants[owner] = [{'coordinate': {'direction': d}} for d in directions]
        return {'responses': {'results': results}, 'probe_selection': selections, 'secants': secants}

    def test_shared_phase_net_effect_and_unknown_global_bound(self):
        owners, net, ref, box = self.fixture()
        follower = NS(cfg=NS(network=net), offset_fractions=(.1, .2, .3))
        original = pickle.dumps(ref)
        with patch.object(signals, 'phase_bounds', return_value=dict.fromkeys(('p1','p2','p3','p4'), (20., 50.))), \
             patch.object(signals, 'native_clock_basis', return_value=None), \
             patch.object(signals, 'validate_vector'):
            usual = subject.prepare_fast_np_seeds(follower, ref, self.measurement(ref, owners), box)
            shared = subject.prepare_fast_np_seeds(follower, ref, self.measurement(ref, owners, shared=True), box)
        self.assertEqual(usual['seeds'][0].green_times['SC0_p1'], 24.)
        self.assertEqual(shared['seeds'][0].green_times['SC0_p1'], 36.)
        self.assertEqual(usual['seeds'][1].offsets['SC0'], 45.)
        self.assertEqual(usual['seeds'][0].offsets, ref.offsets)
        for result in (usual, shared):
            evidence = result['evidence']
            self.assertEqual(evidence['possibility'], 'unknown')
            self.assertIsNone(evidence['global_np_lower_bound_veh'])
            self.assertFalse(evidence['domain_infeasible'])
            self.assertEqual(evidence['new_endpoint_calls'], 0)
            for seed in result['seeds']:
                box.validate(seed)
                self.assertEqual(seed.N_P_star, -250.)
                self.assertEqual(seed.N_UF_star, 1900.)
                self.assertEqual(seed.ramp_metering, ref.ramp_metering)
                self.assertEqual(seed.vsl, ref.vsl)
                for s in owners:
                    self.assertEqual(sum(seed.green_times[s+'_'+p] for p in ('p1','p2','p3','p4')), 120.)
        self.assertEqual(pickle.dumps(ref), original)

    def test_np_excludes_nonowner_internal_and_omega_counts(self):
        owners, _, ref, _ = self.fixture()
        q = self.measurement(ref, owners)['responses']['results'][0]['quantities']
        q['nonowner_service'] = {'net_inflow_veh': 1e9}
        q['TTD'] = 1e9; q['omega_stock'] = 1e9
        self.assertEqual(subject._np_kind_totals(q, owners)['boundary_in'], 1700.)
        for mutate in (lambda q: q['owners'].pop('SC0'),
                       lambda q: q['owners']['SC0']['by_kind_veh'].__setitem__('on_ramp', -1.),
                       lambda q: q['owners']['SC0'].__setitem__('net_inflow_veh', 999.)):
            broken = copy.deepcopy(q); mutate(broken)
            with self.assertRaises(ValueError): subject._np_kind_totals(broken, owners)

    def test_flat_green_direction_retains_actual_command(self):
        owners, net, ref, box = self.fixture()
        with patch.object(signals, 'phase_bounds', return_value=dict.fromkeys(('p1','p2','p3','p4'), (20.,50.))), \
             patch.object(signals, 'native_clock_basis', return_value=None):
            green = subject._linear_green_extreme(net, owners[0], dict.fromkeys(('p1','p2','p3','p4'), 0.), box, ref)
        self.assertEqual(green, dict.fromkeys(('p1','p2','p3','p4'), 30.))

    def test_concurrent_extreme_matches_enumerated_small_box_and_clearance(self):
        net = NS(signal_live_phases=lambda _: ('p1','p2','p4'), signal_effective_green_total=lambda _: .120)
        ref = NS(green_times={'S_p1': .045, 'S_p2': .060, 'S_p3': 0., 'S_p4': .060})
        box = FixedMoveBox(tuple(('green_times', k, v, .006, None) for k,v in ref.green_times.items()), 'fixed')
        bounds = {'p1': (.030,.070), 'p2': (.040,.080), 'p4': (.040,.080)}
        feasible = [{'p1':x/1000,'p2':y/1000,'p4':(.120-y/1000)}
            for x,y in itertools.product(range(39,52), range(54,67)) if x+10 <= y]
        for c in ({'p1':-3.,'p2':2.,'p4':-1.}, {'p1':2.,'p2':-4.,'p4':3.}):
            with patch.object(signals, 'phase_bounds', return_value=bounds), \
                 patch.object(signals, 'native_clock_basis', return_value={'kind':'concurrent_p1_p2','amber_sec':.010}), \
                 patch.object(signals, 'validate_vector'):
                v = subject._linear_green_extreme(net, 'S', c, box, ref)
            self.assertLessEqual(v['p1']+.010, v['p2']+1e-12)
            self.assertAlmostEqual(v['p2']+v['p4'], .120)
            self.assertAlmostEqual(sum(c[p]*v[p] for p in c), min(sum(c[p]*r[p] for p in c) for r in feasible))


class FastRestorationTests(unittest.TestCase):
    def fixture(self):
        f = RestorationTests()
        own = catalog(); seed = action(own)
        seed['offsets'] = {'A': 1., 'B': 1.}
        return f, seed

    def test_all_owner_seed_checked_before_local_descent_and_nuf_is_fixed(self):
        f, seed = self.fixture()
        result = f.restore(f.merit, initial_seeds=(seed,))
        self.assertTrue(result['feasible'])
        self.assertEqual(result['evaluations'], 2)
        self.assertEqual(result['neighbor_calls'], 0)
        self.assertEqual(result['control']['N_UF_star'], 9.)
        seed['N_UF_star'] = 10.
        failed = f.restore(f.merit, initial_seeds=(seed,))
        self.assertFalse(failed['feasible'])
        self.assertEqual(failed['status'], 'callback_contract_failure')

    def test_failed_short_restoration_does_not_start_another_game_search(self):
        from diagnostics.test_fixed_shared_game import FixedSharedGameTests, digest
        from evaluation.controllers import area_leader_objective as pricing
        f = FixedSharedGameTests(); f.setUp()
        def quantity(follower, action, quantities, **kwargs):
            return {'feasible':False, 'np':{'actual':286., 'satisfied':False},
                    'nuf':{'actual':5., 'satisfied':True}}
        with patch.object(subject, '_evaluate_shared_owner_batch_owned', f.batch), \
             patch.object(pricing, 'fixed_joint_price_terms', f.prices), \
             patch.object(pricing, 'shared_quantity_constraints', quantity):
            result = subject.solve_fixed_shared_game(f.follower, f.state, f.action, f.forecast, f.action,
                callbacks=f.callbacks,context=f.context,context_fingerprint=digest,horizon_steps=3,
                lambda_p=0.,lambda_uf=0.,target_np_veh=3.,target_nuf_veh_h=5.,
                price_context={'np_mode':'cap','nuf_mode':'equality'}, max_sweeps=4,max_evaluations=1000,
                time_budget_sec=120.,improvement_tolerance=1e-9, shared_tolerance=1e-7,
                scope_label='Short infeasible initializer test',np_tolerance_veh=1e-7,nuf_tolerance_veh_h=1e-7,
                restore_initializer=True,restoration_policy={'restoration_time_budget_sec':45.,'restoration_max_evaluations':3})
        self.assertEqual(result['initializer_restoration']['evaluations'], 3)
        self.assertEqual(result['game']['evaluations'], 0)
        self.assertEqual(len(f.calls), 3)
        self.assertFalse(result['initializer_restoration']['domain_infeasible'])
        self.assertEqual(result['initializer_seed_checks'][0]['np_veh'], 286.)
        self.assertTrue(result['initializer_seed_checks'][0]['nuf_satisfied'])
        self.assertFalse(result['initializer_seed_checks'][0]['target_cap_satisfied'])

    def test_budget_during_seeds_is_unknown_and_retains_only_checked_action(self):
        f, seed = self.fixture()
        result = f.restore(f.merit, initial_seeds=(seed,), max_evaluations=1)
        self.assertEqual(result['status'], 'evaluation_budget')
        self.assertFalse(result['domain_infeasible'])
        self.assertIsNone(result['control'])
        self.assertEqual(result['evaluations'], 1)
        self.assertEqual(result['neighbor_calls'], 0)


if __name__ == '__main__': unittest.main()
