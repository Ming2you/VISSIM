"""Finite directional-price fitting; synthetic operands, no model/COM imports."""
import copy
import math
import unittest

from diagnostics.test_shared_joint_price_quantity import api, fixture as local_fixture


def fixture(*, meter_equality=False, fixed_meter_rate=None):
    f, action, _, _ = local_fixture()
    net = f.cfg.network
    net.ramp_capacity_veh_h = dict.fromkeys(net.ramps, 200. if fixed_meter_rate is None else 1800.)
    if fixed_meter_rate is not None:
        action.ramp_metering = dict.fromkeys(net.ramps, fixed_meter_rate)
    phases = ('p1', 'p2', 'p3', 'p4')
    net.signal_live_phases = lambda s: ('p1', 'p2') if s == 'SC17' else phases
    net.signal_cycle_length = lambda s: 120. if s == 'SC1' else 150.
    net.freeway_vsl_zone_heads = {s: (0, 2, 3, 4) for s in net.freeway_links}
    net.freeway_vsl_zone_head_of_cell = {s: (0, 0, 2, 3, 4, 4) for s in net.freeway_links}
    net.freeway_vsl_zone_free = (0, 1, 2)
    action.vsl = {k: 120. for s in net.freeway_links for k in (s, *(f'{s}__seg{i}' for i in range(6)))}
    action.green_times.update(SC17_p3=0., SC17_p4=0.)
    action.offsets['SC1'] = 119.
    for model in f._local_freeway_models.values():
        model.n_seg = 6
    owners = tuple(net.signals) + tuple(net.freeway_links)
    models = {s: {**{s+'_'+p: action.green_times[s+'_'+p] for p in phases}, s: action.offsets[s]}
              for s in net.signals}
    models.update({s: {**{f'{s}__seg{i}': action.vsl[f'{s}__seg{i}'] for i in range(6)}, s: action.vsl[s],
                          **{r: action.ramp_metering[r] for r in f._local_freeway_models[s].owned_ramps}}
                   for s in net.freeway_links})
    base = {'objective_veh_h': 100., 'local_base_costs': dict.fromkeys(owners, 10.),
        'context': {'beta_seconds': 300., 'frozen_digest': 'same-reference-state-demand',
                    'local_cost_definition': 'same-shared-physical-base/v1'},
        'response_token': 'same-base', 'local_cost_response_token': 'same-base',
        'physical_owner_tokens': {o: o+'-base' for o in owners}, 'model_owner_values': models,
        'price_or_quantity_terms_included': False, 'local_cost_contains_omega_beta': False}
    edge_sets, truth = {}, {}
    for owner in owners:
        before = models[owner]
        urban = owner in net.signals
        included = set(before) if urban else set(before)-{owner}
        kinds = {a: ('offset' if a == owner else 'green') if urban else
                       ('vsl' if a.startswith(owner+'__seg') else 'meter') for a in included}
        directions = []
        if urban:
            live = tuple(net.signal_live_phases(owner))
            prices = dict.fromkeys(included, 0.)
            prices.update({owner+'_'+p: float(2*i-(len(live)-1)) for i,p in enumerate(live)})
            prices[owner] = .25
            for p in live[:-1]:
                directions.append({owner+'_'+p: 6., owner+'_'+live[-1]: -6.})
            directions.append({owner: 2.})
        else:
            prices = dict.fromkeys(included, 0.)
            for head, zone_price in ((0, .3), (2, .5), (3, .7)):
                cells = [i for i,h in enumerate(net.freeway_vsl_zone_head_of_cell[owner]) if h == head]
                for i in cells: prices[f'{owner}__seg{i}'] = zone_price/len(cells)
                directions.append({f'{owner}__seg{i}': -20. for i in cells})
            for ramp, p in zip(f._local_freeway_models[owner].owned_ramps, (.02, -.03)):
                prices[ramp] = p
                if not meter_equality and fixed_meter_rate is None:
                    directions.append({ramp: 10.})
            if meter_equality and fixed_meter_rate is None:
                r1, r2 = f._local_freeway_models[owner].owned_ramps
                directions.append({r1: 10., r2: -10.})
        truth[owner] = prices
        edges = []
        for index, direction in enumerate(directions):
            after = dict(before)
            for a, d in direction.items(): after[a] += d
            if urban: after[owner] %= net.signal_cycle_length(owner)
            else: after[owner] = min(after[f'{owner}__seg{i}'] for i in range(6))
            probe = copy.deepcopy(base)
            probe['model_owner_values'][owner] = after
            probe['response_token'] = probe['local_cost_response_token'] = f'{owner}-probe-{index}'
            probe['physical_owner_tokens'][owner] = f'{owner}-physical-{index}'
            probe['local_base_costs'][owner] += 4.
            probe['objective_veh_h'] += 4. + math.fsum(prices[a]*d for a,d in direction.items())
            coordinate = {'owner': owner, 'kind': 'joint_direction', 'parameter_unit': '1',
                'displacement': 1., 'base_values': {a: before[a] for a in included},
                'probe_values': {a: after[a] for a in included},
                'direction': {a: direction.get(a, 0.) for a in included},
                'address_kinds': kinds, 'address_owners': dict.fromkeys(included, owner),
                'offset_cycles': {owner: net.signal_cycle_length(owner)} if urban else {}}
            edges.append(api.matched_external_secant(base, probe, owners=owners, owner=owner, coordinate=coordinate))
        edge_sets[owner] = edges
    return f, action, edge_sets, truth


class JointPriceFieldTests(unittest.TestCase):
    def fit(self, args):
        return api.fit_joint_price_field(*args[:3])

    def equality_fit(self, args, **updates):
        kw = dict(nuf_price_policy='fixed_direction_equality',
                  directional_nuf_targets_veh_h={'FW_E': 200., 'FW_W': 200.},
                  nuf_equality_tolerance_veh_h=0.)
        kw.update(updates)
        return api.fit_joint_price_field(*args[:3], **kw)

    def bounded_fit(self, args, **updates):
        f, a, _, _ = args
        kw = dict(nuf_price_policy='bounded_direction_equality',
                  directional_nuf_targets_veh_h={link: math.fsum(a.ramp_metering[r] for r in model.owned_ramps)
                                                for link, model in f._local_freeway_models.items()},
                  nuf_equality_tolerance_veh_h=0.,
                  final_meter_bounds_veh_h={r: {'lower': 0., 'upper': cap}
                                            for r, cap in f.cfg.network.ramp_capacity_veh_h.items()})
        kw.update(updates)
        return api.fit_joint_price_field(*args[:3], **kw)

    def test_exact_upper_bound_singleton_retains_zero_representatives_not_gradients(self):
        args = fixture(fixed_meter_rate=1800.)
        result = self.bounded_fit(args); holders = result['holder_values']
        self.assertEqual(len(result['owner_fits']), 19)
        self.assertEqual(holders['metering_marginal_price'], dict.fromkeys(('R1','R2','R3','R4'), 0.))
        self.assertEqual(holders['metering_marginal_price_ref'], args[1].ramp_metering)
        for owner in ('FW_E', 'FW_W'):
            report = result['owner_fits'][owner]
            self.assertEqual((report['rank'], report['dimension']), (3, 3))
            proof = report['nuf_equality']['final_bounds_proof']
            self.assertTrue(proof['singleton_proven'])
            self.assertFalse(proof['meter_tangent_fitted'])
            self.assertFalse(proof['meter_gradient_certified'])
            self.assertEqual(proof['first_meter_feasible_interval_exact'], [[1800, 1], [1800, 1]])
            for edge in args[2][owner]:
                # Any finite meter coefficients have the same zero reference-relative contribution.
                ramps = args[0]._local_freeway_models[owner].owned_ramps
                self.assertEqual(sum(p*edge['realized_deltas'][r] for p,r in zip((123., -456.), ramps)), 0.)
                self.assertAlmostEqual(sum(holders['vsl_marginal_price'].get(k, 0.)*v
                                           for k,v in edge['realized_deltas'].items()), edge['external_delta_veh_h'])

    def test_exact_lower_bound_singleton_also_has_fixed_meter_cost(self):
        result = self.bounded_fit(fixture(fixed_meter_rate=0.))
        for owner in ('FW_E','FW_W'):
            proof = result['owner_fits'][owner]['nuf_equality']['final_bounds_proof']
            self.assertTrue(proof['singleton_proven'])
            self.assertEqual(set(proof['fixed_rates_veh_h'].values()), {0.})

    def test_singleton_does_not_change_old_independent_or_equality_policy(self):
        args = fixture(fixed_meter_rate=1800.)
        with self.assertRaisesRegex(ValueError, 'unidentified active'):
            self.fit(args)
        with self.assertRaisesRegex(ValueError, 'unidentified active'):
            self.equality_fit(args, directional_nuf_targets_veh_h={'FW_E': 3600., 'FW_W': 3600.})

    def test_bounded_movable_pair_preserves_tangent_and_remaining_rank(self):
        args = fixture(meter_equality=True)
        result = self.bounded_fit(args)
        legacy = self.equality_fit(args)
        self.assertEqual(result['holder_values'], legacy['holder_values'])
        for owner in ('FW_E', 'FW_W'):
            self.assertFalse(result['owner_fits'][owner]['nuf_equality']['final_bounds_proof']['singleton_proven'])
            self.assertEqual(result['owner_fits'][owner]['dimension'], 4)
        del args[2]['FW_E'][-1]
        with self.assertRaisesRegex(ValueError, 'unidentified active'):
            self.bounded_fit(args)

    def test_one_fixed_and_one_movable_direction_are_not_globally_collapsed(self):
        args = fixture(meter_equality=True)
        args[0].cfg.network.ramp_capacity_veh_h.update(R1=100., R2=100.)
        args[2]['FW_E'] = args[2]['FW_E'][:3]
        result = self.bounded_fit(args)
        self.assertEqual(result['owner_fits']['FW_E']['dimension'], 3)
        self.assertEqual(result['owner_fits']['FW_W']['dimension'], 4)
        self.assertEqual(result['holder_values']['metering_marginal_price']['R1'], 0.)
        self.assertAlmostEqual(result['holder_values']['metering_marginal_price']['R3'], .025)

    def test_wrong_missing_narrow_or_nonfinite_final_bounds_fail_closed(self):
        for mode in ('missing', 'unknown', 'lower', 'upper', 'nan', 'keys', 'false_fixed'):
            args = fixture(meter_equality=mode == 'false_fixed', fixed_meter_rate=None if mode == 'false_fixed' else 1800.)
            bounds = {r: {'lower': 0., 'upper': cap} for r,cap in args[0].cfg.network.ramp_capacity_veh_h.items()}
            if mode == 'missing': del bounds['R1']
            elif mode == 'unknown': bounds['unknown'] = {'lower': 0., 'upper': 1.}
            elif mode == 'lower': bounds['R1']['lower'] = 1.
            elif mode == 'upper': bounds['R1']['upper'] -= 1.
            elif mode == 'nan': bounds['R1']['upper'] = float('nan')
            elif mode == 'keys': bounds['R1']['source'] = 'trust-me'
            else: bounds['R1']['upper'] = bounds['R2']['upper'] = 100.
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.bounded_fit(args, final_meter_bounds_veh_h=bounds)

    def test_budget_tolerance_does_not_collapse_small_movable_interval_or_empty_set(self):
        # Exact interval width is positive although much smaller than the budget tolerance.
        args = fixture(fixed_meter_rate=1800.-1e-10)
        with self.assertRaisesRegex(ValueError, 'unidentified active'):
            self.bounded_fit(args, nuf_equality_tolerance_veh_h=1.)
        args = fixture(fixed_meter_rate=1800.)
        with self.assertRaisesRegex(ValueError, 'empty intersection'):
            self.bounded_fit(args, directional_nuf_targets_veh_h={'FW_E': 3600.+1e-10, 'FW_W': 3600.},
                             nuf_equality_tolerance_veh_h=1.)

    def test_singleton_rejects_reference_and_probe_drift_even_inside_budget_tolerance(self):
        args = fixture(fixed_meter_rate=1800.-1e-10)
        with self.assertRaisesRegex(ValueError, 'reference violates'):
            self.bounded_fit(args, directional_nuf_targets_veh_h={'FW_E': 3600., 'FW_W': 3600.},
                             nuf_equality_tolerance_veh_h=1.)
        for drift in (-1e-10, 1e-10):
            args = fixture(fixed_meter_rate=1800.)
            edge = args[2]['FW_E'][0]
            edge['model_owner_values']['probe']['FW_E']['R1'] += drift
            edge['coordinate']['probe_values']['R1'] += drift
            actual = edge['coordinate']['probe_values']['R1']-edge['coordinate']['base_values']['R1']
            edge['realized_deltas']['R1'] = edge['coordinate']['direction']['R1'] = actual
            with self.subTest(drift=drift), self.assertRaisesRegex(ValueError, 'probe violates'):
                self.bounded_fit(args, nuf_equality_tolerance_veh_h=1.)

    def test_fixed_meters_do_not_waive_any_vsl_axis_or_external_cost_residual(self):
        for index in (0, 1, 2):
            args = fixture(fixed_meter_rate=1800.)
            del args[2]['FW_E'][index]
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, 'unidentified active'):
                self.bounded_fit(args)
        args = fixture(fixed_meter_rate=1800.)
        extra = copy.deepcopy(args[2]['FW_E'][0]); extra['probe_response_token'] += '-nonlinear'
        extra['external_delta_veh_h'] += 1.
        extra['delta_global_veh_h'] += 1.
        extra['directional_secant'] += 1.
        args[2]['FW_E'].append(extra)
        result = self.bounded_fit(args)['owner_fits']['FW_E']
        self.assertAlmostEqual(result['max_abs_residual_veh_h'], .5)

    def test_bounded_output_and_source_bounds_do_not_alias_or_mutate(self):
        args = fixture(fixed_meter_rate=1800.)
        bounds = {r: {'lower': 0., 'upper': 1800.} for r in args[1].ramp_metering}
        before = copy.deepcopy((args[0].__dict__, args[1].__dict__, args[2], bounds))
        result = self.bounded_fit(args, final_meter_bounds_veh_h=bounds)
        result['owner_fits']['FW_E']['nuf_equality']['final_bounds_proof']['bounds_veh_h']['R1']['upper'] = 3.
        self.assertEqual((args[0].__dict__, args[1].__dict__, args[2], bounds), before)
        for policy in ('independent', 'fixed_direction_equality'):
            with self.subTest(policy=policy), self.assertRaisesRegex(ValueError, 'explicit bounded equality'):
                api.fit_joint_price_field(*args[:3], nuf_price_policy=policy, final_meter_bounds_veh_h=bounds)

    def test_equality_tangent_keeps_both_meters_gauge_and_dotproduct(self):
        f, a, edges, truth = args = fixture(meter_equality=True)
        result = self.equality_fit(args); holders = result['holder_values']
        self.assertEqual(set(holders['metering_marginal_price']), set(a.ramp_metering))
        self.assertEqual(result['nuf_price_policy'], 'fixed_direction_equality')
        for link in f.cfg.network.freeway_links:
            r1, r2 = f._local_freeway_models[link].owned_ramps
            self.assertAlmostEqual(holders['metering_marginal_price'][r1], .025)
            self.assertAlmostEqual(holders['metering_marginal_price'][r2], -.025)
            self.assertEqual(holders['metering_marginal_price'][r1]+holders['metering_marginal_price'][r2], 0.)
            fit = result['owner_fits'][link]
            self.assertEqual((fit['rank'], fit['dimension']), (4, 4))
            self.assertEqual(fit['columns'][-1], r1+' minus '+r2)
            self.assertEqual(fit['nuf_equality']['reference_residual_veh_h'], 0.)
            self.assertEqual(fit['nuf_equality']['normal_displacements_veh_h'], [0.]*4)
            self.assertEqual(holders['metering_marginal_price_ref'][r1], 100.)
            for edge in edges[link]:
                fitted = math.fsum(holders['vsl_marginal_price'].get(k,
                    holders['metering_marginal_price'].get(k))*d for k,d in edge['realized_deltas'].items())
                self.assertAlmostEqual(fitted, edge['external_delta_veh_h'])

    def test_equality_does_not_automatically_reduce_independent_default_rank(self):
        with self.assertRaisesRegex(ValueError, 'rank 4/5'):
            self.fit(fixture(meter_equality=True))

    def test_equality_requires_target_tolerance_and_actual_tangent(self):
        for mode in ('missing_target', 'unknown_direction', 'missing_tolerance', 'negative_tolerance',
                     'nan_target', 'wrong_target', 'normal_edge', 'budget_slack_is_not_tangent'):
            args = fixture(meter_equality=mode not in ('normal_edge', 'budget_slack_is_not_tangent'))
            kw = {}
            if mode == 'missing_target': kw['directional_nuf_targets_veh_h'] = None
            elif mode == 'unknown_direction': kw['directional_nuf_targets_veh_h'] = {'FW_E': 200.}
            elif mode == 'missing_tolerance': kw['nuf_equality_tolerance_veh_h'] = None
            elif mode == 'negative_tolerance': kw['nuf_equality_tolerance_veh_h'] = -1.
            elif mode == 'nan_target': kw['directional_nuf_targets_veh_h'] = {'FW_E': float('nan'), 'FW_W': 200.}
            elif mode == 'wrong_target': kw['directional_nuf_targets_veh_h'] = {'FW_E': 199., 'FW_W': 200.}
            elif mode == 'budget_slack_is_not_tangent': kw['nuf_equality_tolerance_veh_h'] = 20.
            with self.subTest(mode=mode), self.assertRaises(ValueError): self.equality_fit(args, **kw)

    def test_equality_missing_free_zone_or_meter_tangent_still_fails(self):
        for index in (0, 3):
            args = fixture(meter_equality=True)
            del args[2]['FW_E'][index]
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, 'unidentified active'):
                self.equality_fit(args)

    def test_equality_reports_budget_rounding_separately_without_changing_targets(self):
        args = fixture(meter_equality=True)
        targets = {'FW_E': 199.75, 'FW_W': 200.}
        result = self.equality_fit(args, directional_nuf_targets_veh_h=targets,
                                   nuf_equality_tolerance_veh_h=.25)
        report = result['owner_fits']['FW_E']['nuf_equality']
        self.assertEqual(report['reference_residual_veh_h'], .25)
        self.assertEqual(report['probe_residuals_veh_h'], [.25]*4)
        self.assertEqual(report['normal_displacements_veh_h'], [0.]*4)
        self.assertEqual(targets, {'FW_E': 199.75, 'FW_W': 200.})
        self.assertEqual(result['reference_levers']['ramp_metering'], dict.fromkeys(('R1','R2','R3','R4'), 100.))

    def test_independent_policy_rejects_ignored_equality_arguments(self):
        args = fixture()
        for kw in ({'nuf_price_policy': 'unknown'}, {'directional_nuf_targets_veh_h': {}},
                   {'nuf_equality_tolerance_veh_h': 0.}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                api.fit_joint_price_field(*args[:3], **kw)

    def test_identified_all_owner_field_recovers_zero_sum_gauge_and_exact_reference(self):
        args = fixture(); result = self.fit(args); f,a,_,truth = args
        holders = result['holder_values']
        self.assertEqual(len(result['owner_fits']), 19)
        for s in f.cfg.network.signals:
            for p in ('p1','p2','p3','p4'):
                self.assertAlmostEqual(holders['signal_phase_price'][s][p], truth[s][s+'_'+p])
                self.assertEqual(holders['signal_phase_price_ref'][s][p], a.green_times[s+'_'+p])
            self.assertAlmostEqual(math.fsum(holders['signal_phase_price'][s].values()), 0.)
            self.assertAlmostEqual(holders['offset_marginal_price'][s], .25)
        self.assertEqual(holders['signal_phase_price']['SC17']['p3'], 0.)
        self.assertEqual(holders['signal_phase_price']['SC17']['p4'], 0.)
        self.assertEqual(holders['offset_marginal_price_ref']['SC1'], 119.)
        self.assertTrue(all(v['rank'] == v['dimension'] for v in result['owner_fits'].values()))
        self.assertLess(max(v['max_abs_residual_veh_h'] for v in result['owner_fits'].values()), 1e-12)
        self.assertTrue(result['finite_secant_fit'])
        self.assertFalse(result['feasibility_or_equilibrium_certified'])

    def test_zone_expansion_preserves_dot_product_and_never_prices_bare_alias(self):
        f,a,edges,truth = args = fixture(); h = self.fit(args)['holder_values']
        for owner in f.cfg.network.freeway_links:
            self.assertNotIn(owner, h['vsl_marginal_price'])
            self.assertAlmostEqual(h['vsl_marginal_price'][owner+'__seg0'], .15)
            self.assertAlmostEqual(h['vsl_marginal_price'][owner+'__seg1'], .15)
            self.assertEqual(h['vsl_marginal_price'][owner+'__seg4'], 0.)
            self.assertEqual(h['vsl_marginal_price'][owner+'__seg5'], 0.)
            for edge in edges[owner]:
                fitted = math.fsum((h['vsl_marginal_price'].get(key, h['metering_marginal_price'].get(key))) * delta
                                  for key,delta in edge['realized_deltas'].items())
                self.assertAlmostEqual(fitted, edge['external_delta_veh_h'])

    def test_missing_or_rank_deficient_active_edges_fail_not_zero(self):
        for mode in ('owner','empty','offset','dependent'):
            args = fixture(); edges = args[2]
            if mode == 'owner': del edges['SC17']
            elif mode == 'empty': edges['SC1'] = []
            elif mode == 'offset': edges['SC1'] = edges['SC1'][:-1]
            else:
                # Every column is nonzero, yet these identical joint rows have rank one.
                edge = copy.deepcopy(edges['SC1'][0])
                combined = {a: sum(e['realized_deltas'][a] for e in edges['SC1']) for a in edge['realized_deltas']}
                edge['realized_deltas'] = combined
                for a,delta in combined.items():
                    val = edge['model_owner_values']['base']['SC1'][a] + delta
                    if a == 'SC1': val %= 120.
                    edge['model_owner_values']['probe']['SC1'][a] = val
                    edge['coordinate']['probe_values'][a] = val
                edge['coordinate']['direction'] = combined
                edges['SC1'] = [edge]*4
            with self.subTest(mode=mode), self.assertRaises(ValueError): self.fit(args)

    def test_overdetermined_nonlinear_cost_returns_residual_without_claiming_derivative(self):
        args = fixture(); extra = copy.deepcopy(args[2]['SC1'][0])
        for a, delta in extra['realized_deltas'].items():
            extra['realized_deltas'][a] = 2.*delta
            extra['coordinate']['direction'][a] = 2.*delta
            after = extra['model_owner_values']['base']['SC1'][a] + 2.*delta
            if a == 'SC1': after %= 120.
            extra['model_owner_values']['probe']['SC1'][a] = after
            extra['coordinate']['probe_values'][a] = after
        extra['probe_response_token'] = 'SC1-double-exchange-curved-response'
        extra['external_delta_veh_h'] = 2.*extra['external_delta_veh_h'] + 2.
        extra['delta_global_veh_h'] = extra['delta_local_veh_h'] + extra['external_delta_veh_h']
        extra['directional_secant'] = extra['external_delta_veh_h']
        args[2]['SC1'].append(extra)
        result = self.fit(args)['owner_fits']['SC1']
        self.assertEqual(result['edge_count'], 5)
        self.assertAlmostEqual(result['max_abs_residual_veh_h'], .8)
        self.assertAlmostEqual(result['rms_residual_veh_h'], .4)

    def test_wrong_context_reference_foreign_owner_and_circle_fail(self):
        for mode in ('context','response','reference','foreign','cycle','delta','cost','nan'):
            args = fixture(); edge = args[2]['SC1'][0]
            if mode == 'context': edge['context']['frozen_digest'] = 'other'
            elif mode == 'response': edge['base_response_token'] = 'other-base'
            elif mode == 'reference': edge['model_owner_values']['base']['SC1']['SC1_p1'] += 1.
            elif mode == 'foreign': edge['model_owner_values']['probe']['FW_W']['R3'] += 1.
            elif mode == 'cycle': edge['coordinate']['offset_cycles']['SC1'] = 150.
            elif mode == 'delta': edge['realized_deltas']['SC1_p1'] += 1.
            elif mode == 'cost': edge['external_delta_veh_h'] += 1.
            else: edge['model_owner_values']['probe']['FW_W']['R3'] = float('nan')
            with self.subTest(mode=mode), self.assertRaises(ValueError): self.fit(args)

    def test_configured_dead_recovery_and_zone_equality_fail_closed(self):
        for mode in ('dead_reference','dead_edge','recovery','split_zone','alias','missing_meter'):
            args = fixture(); f,a,edges,_ = args
            if mode == 'dead_reference': a.green_times['SC17_p4'] = 1.
            elif mode == 'missing_meter': del a.ramp_metering['R1']
            else:
                owner = 'SC17' if mode == 'dead_edge' else 'FW_E'
                edge = edges[owner][0]
                key = {'dead_edge':'SC17_p4','recovery':'FW_E__seg4',
                       'split_zone':'FW_E__seg1','alias':'FW_E'}[mode]
                edge['model_owner_values']['probe'][owner][key] -= 1.
                if key in edge['coordinate']['probe_values']:
                    edge['coordinate']['probe_values'][key] -= 1.
                    edge['realized_deltas'][key] -= 1.
            with self.subTest(mode=mode), self.assertRaises((ValueError, KeyError)): self.fit(args)

    def test_fitting_does_not_mutate_prices_config_inputs_or_return_aliases(self):
        args = fixture(); f,a,edges,_ = args
        before = copy.deepcopy((f.__dict__,a.__dict__,edges))
        result = self.fit(args)
        self.assertEqual((f.__dict__,a.__dict__,edges), before)
        result['reference_levers']['green_times']['SC1_p1'] = -10.
        result['holder_values']['signal_phase_price_ref']['SC1']['p1'] = -20.
        result['context']['frozen_digest'] = 'modified'
        self.assertEqual((f.__dict__,a.__dict__,edges), before)
        self.assertIsNone(f.signal_phase_price)

    def test_missing_context_wrong_direction_and_beta_flags_fail(self):
        for mode in ('context','beta','response','direction','unit','secant','double_beta'):
            args = fixture(); edge = args[2]['SC1'][0]
            if mode == 'context': edge['context'] = {}
            elif mode == 'beta': edge['context']['beta_seconds'] = float('nan')
            elif mode == 'response': edge['probe_response_token'] = edge['base_response_token']
            elif mode == 'direction': edge['coordinate']['direction']['SC1_p1'] = 3.
            elif mode == 'unit': edge['coordinate']['parameter_unit'] = 's'
            elif mode == 'secant': edge['directional_secant'] += 1.
            else: edge['local_beta_term_subtracted'] = True
            with self.subTest(mode=mode), self.assertRaises(ValueError): self.fit(args)


if __name__ == '__main__': unittest.main()
