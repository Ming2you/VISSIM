"""Final-response leader ranking with stub solves; no endpoint/model/native run."""
import copy
import json
import pickle
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from diagnostics.test_joint_leader_result import fixture, digest
from evaluation.controllers import area_follower_objective as module
from evaluation.controllers.area_leader_objective import validate_joint_leader_result


class RuntimeJointLeaderTests(unittest.TestCase):
    def setUp(self):
        self.clock = 0.
        self.calls = []
        self.costs = {340.: 10., 500.: 30.}
        self.sources = {'installed.py': 'a' * 64}
        self.common_calls = []
        self.shared_contexts = []
        self.common = {'price_field': {'anchor': 'actual-previous', 'phase': {'SC1_p1': 2.}},
            'reference': {'actual_previous': True},
            'response_query': SimpleNamespace(stats=lambda: {'requests': 0, 'cache_hits': 0})}
        self.move_limits = {'green_sec': 6., 'offset_sec': {'SC1': 6.},
                            'vsl_kmh': 20., 'meter_veh_h': 300.}
        self.options = dict(max_evaluations=80, time_budget_sec=240., improvement_tolerance=1e-7,
            shared_tolerance=1e-7, np_tolerance_veh=1e-7, nuf_tolerance_veh_h=1e-7,
            traversal='round_robin', max_leader_candidates=3, leader_time_budget_sec=1800.,
            leader_candidate_order='diverse')
        self.base = fixture()
        self.controller = SimpleNamespace(cfg=SimpleNamespace(network=SimpleNamespace(
            ramps=tuple(self.base['game']['control'].ramp_metering))))
        self.controller.leader = SimpleNamespace()
        self.controller.nash_solver = SimpleNamespace(cfg=self.controller.cfg)
        self.domain = self.make_domain((340., 500.))

    def make_domain(self, np_values):
        proposals = []
        for index, np_value in enumerate(np_values):
            action = self.base['game']['control'].copy()
            action.N_P_star = np_value
            proposals.append(dict(control=action, target_np_veh=np_value, target_nuf_veh_h=7200.,
                directional_budgets={o: {'mode': 'equality', 'veh_h': 3600.} for o in ('FW_E', 'FW_W')},
                meter_bank_index=0, physical_meter_rows=[{'sc': 9101, 'green': 10.}]))
        return dict(schema='joint-leader-realized-domain/v1', candidates=proposals,
            candidate_count=len(proposals), objective_queries=0, leader_target_selected=False,
            scope='Pure exact proposal source fixture')

    def response(self, proposal):
        response = copy.deepcopy(self.base)
        action = proposal['control'].copy()
        action.green_times['SC1_p1'] += 6.  # Different final response, not a nominal score.
        np_value = proposal['target_np_veh']
        response['game']['control'] = action
        score = response['final_score']
        score['objective_veh_h'] = self.costs[np_value]
        score['control_area']['near_score_veh_h'] = self.costs[np_value]
        np_row = score['quantity_constraints']['np']
        if np_value < np_row['actual']:
            np_row['actual'] = np_value - 10.
            owners = score['quantity_constraints']['net_inflow_veh_by_owner']
            owners.update(dict.fromkeys(owners, 0.))
            owners[next(iter(owners))] = np_row['actual']
        np_row.update(target=np_value, residual=np_row['actual'] - np_value)
        response['final_action_token'] = score['action_token'] = digest(action)
        return response

    def solve(self, controller, state, forecast, historical, proposal, mapping, **kwargs):
        self.shared_contexts.append(kwargs['common'])
        self.assertIs(kwargs['common'], self.common)
        self.calls.append((proposal['target_np_veh'], proposal['target_nuf_veh_h']))
        response = self.response(proposal)
        validated = validate_joint_leader_result(response, target_np_veh=proposal['target_np_veh'],
                                               target_nuf_veh_h=proposal['target_nuf_veh_h'])
        return dict(response=response, validated_nash=validated, candidate_status='feasible_final_response',
            initializer_evidence=None, target_np_veh=proposal['target_np_veh'],
            target_nuf_veh_h=proposal['target_nuf_veh_h'], source_fingerprint=digest(kwargs['runtime_sources']))

    def prepare_common(self, *args, **kwargs):
        self.common_calls.append((args, kwargs))
        return self.common

    def run_selection(self, solve=None, prepare=None, common=None, historical=None):
        with patch.object(module, 'prepare_joint_leader_candidates',
                          side_effect=prepare or (lambda *a, **kw: copy.deepcopy(self.domain))), \
             patch.object(module, 'solve_runtime_joint_candidate', side_effect=solve or self.solve), \
             patch.object(module, 'prepare_common_joint_prices', side_effect=common or self.prepare_common), \
             patch.object(module, 'joint_decision_move_limits', return_value=self.move_limits), \
             patch('time.perf_counter', side_effect=lambda: self.clock):
            return module.solve_runtime_joint_leader(self.controller, {'time': 900}, [{'demand': 1}],
                {'historical': True} if historical is None else historical, {'mapping': 1},
                runtime_sources=self.sources, options=self.options)

    def test_price_timeout_returns_only_previously_validated_actual_hold(self):
        def timeout(*args, **kwargs):
            budget = kwargs['budget']
            hold = {'feasible':True,'source_fingerprint':digest(self.sources),'control':copy.deepcopy(args[3])}
            budget.validated_hold_bytes=pickle.dumps(hold,protocol=5)
            import hashlib
            budget.validated_hold_sha256=hashlib.sha256(budget.validated_hold_bytes).hexdigest()
            self.clock=111.
            raise module.DecisionDeadline('prices')
        action = self.base['game']['control']
        result = self.run_selection(common=timeout,historical=action)
        self.assertIsNone(result['selected'])
        self.assertTrue(result['held_response']['feasible'])
        self.assertEqual(result['metadata']['selection_status'],'validated_actual_hold')
        self.assertFalse(result['metadata']['hold_price_complete'])
        self.assertFalse(self.calls)

    def test_stale_hold_cannot_be_returned_on_price_timeout(self):
        def timeout(*args, **kwargs):
            budget=kwargs['budget']
            hold={'feasible':True,'source_fingerprint':digest(self.sources),'control':copy.deepcopy(args[3])}
            hold['control'].N_P_star += 1.
            budget.validated_hold_bytes=pickle.dumps(hold,protocol=5)
            import hashlib
            budget.validated_hold_sha256=hashlib.sha256(budget.validated_hold_bytes).hexdigest()
            raise module.DecisionDeadline('prices')
        with self.assertRaisesRegex(ValueError,'actual previous action'):
            self.run_selection(common=timeout,historical=self.base['game']['control'])

    def test_model_error_does_not_fall_back_to_hold(self):
        def fail(*args,**kwargs):
            kwargs['budget'].validated_hold_bytes=b'not usable'
            raise ValueError('unexpected model failure')
        with self.assertRaisesRegex(ValueError,'unexpected model failure'):
            self.run_selection(common=fail)

    def prepare_common_with_validated_hold(self, *args, **kwargs):
        import hashlib
        budget = kwargs['budget']
        hold = {'feasible': True, 'source_fingerprint': digest(self.sources),
            'control': copy.deepcopy(args[3])}
        budget.validated_hold_bytes = pickle.dumps(hold, protocol=5)
        budget.validated_hold_sha256 = hashlib.sha256(budget.validated_hold_bytes).hexdigest()
        return self.prepare_common(*args, **kwargs)

    def test_short_restoration_returns_hold_on_finite_work_exhaustion(self):
        for stop in ('leader_candidate_budget', 'leader_time_budget', None):
            with self.subTest(stop=stop):
                self.setUp()
                if stop == 'leader_candidate_budget':
                    self.options['max_leader_candidates'] = 1
                if stop == 'leader_time_budget':
                    self.options['leader_time_budget_sec'] = 20.
                def short_restore(controller, state, forecast, historical, proposal, mapping, **kwargs):
                    self.calls.append(proposal['target_np_veh'])
                    self.clock += 30.
                    return {'target_np_veh': proposal['target_np_veh'],
                        'target_nuf_veh_h': proposal['target_nuf_veh_h'],
                        'source_fingerprint': digest(kwargs['runtime_sources']),
                        'candidate_status': 'restoration_budget_stop', 'validated_nash': None,
                        'initializer_evidence': {'candidate_feasibility_known': False},
                        'response': {'game': {'error': {'kind': 'evaluation_budget'}}}}
                action = self.base['game']['control']
                result = self.run_selection(solve=short_restore,
                    common=self.prepare_common_with_validated_hold, historical=action)
                meta = result['metadata']
                self.assertIsNone(result['selected'])
                self.assertIsNone(meta['selected_index'])
                self.assertEqual(digest(result['held_response']['control']), digest(action))
                self.assertEqual(meta['selection_status'], 'validated_actual_hold')
                self.assertEqual(meta['stop_reason'], stop)
                self.assertTrue(meta['hold_price_complete'])
                self.assertEqual(meta['unknown_candidate_indices'], [0, 1])
                self.assertEqual(meta['ranking_indices'], [])
                self.assertEqual(meta['all_candidates_attempted'], stop is None)
                self.assertFalse(meta['leader_domain_infeasible'])
                self.assertFalse(meta['leader_optimum_certified'])
                self.assertLess(meta['decision_budget']['wall_sec'], 110.)

    def test_candidate_callback_failure_does_not_return_validated_hold(self):
        def fail(*args, **kwargs):
            raise ValueError('candidate model contract failed')
        result = self.run_selection(solve=fail, common=self.prepare_common_with_validated_hold,
            historical=self.base['game']['control'])
        self.assertIsNone(result['selected'])
        self.assertIsNone(result['held_response'])
        self.assertEqual(result['metadata']['selection_status'], 'aborted_failure')
        self.assertEqual(result['metadata']['stop_reason'], 'candidate_failure')
        self.assertEqual(result['metadata']['failure']['message'], 'candidate model contract failed')
        self.assertFalse(result['metadata']['leader_domain_infeasible'])

    def test_same_nuf_different_np_rank_final_j_and_preserve_partial_gaps(self):
        result = self.run_selection()
        self.assertEqual(self.calls, [(500., 7200.), (340., 7200.)])
        self.assertEqual(result['selected']['validated_nash']['objective_value'], 10.)
        self.assertEqual(result['selected']['target_np_veh'], 340.)
        self.assertEqual(result['selected']['response']['game']['control'].green_times['SC1_p1'], 36.)
        meta = result['metadata']
        self.assertEqual(meta['ranking_indices'], [0, 1])
        self.assertTrue(meta['all_candidates_have_feasible_final_response'])
        self.assertFalse(meta['leader_optimum_certified'])
        self.assertIsNone(meta['candidates'][0]['maximum_finite_candidate_gap'])
        self.assertFalse(meta['candidates'][0]['final_check_complete'])
        self.assertEqual(meta['common_price_measurement_count'], 1)
        self.assertEqual(len(self.common_calls), 1)
        self.assertTrue(all(context is self.common for context in self.shared_contexts))
        json.dumps(meta, allow_nan=False)

    def test_candidate_budget_keeps_whole_domain_and_unvisited_unknown(self):
        self.options['max_leader_candidates'] = 1
        result = self.run_selection()
        meta = result['metadata']
        self.assertEqual(meta['domain_count'], 2)
        self.assertEqual(meta['unknown_candidate_indices'], [0])
        self.assertEqual(meta['stop_reason'], 'leader_candidate_budget')
        self.assertEqual(meta['selected_index'], 1)
        self.assertFalse(meta['leader_domain_infeasible'])

    def test_negative_np_candidate_can_win_without_clipping_or_domain_removal(self):
        self.domain = self.make_domain((-250., 0., 500.))
        self.costs = {-250.: -20., 0.: 0., 500.: 5.}
        result = self.run_selection()
        self.assertEqual(result['metadata']['evaluation_order'], [2, 0, 1])
        self.assertEqual(result['metadata']['domain_count'], 3)
        self.assertEqual(result['selected']['validated_nash']['control'].N_P_star, -250.)
        self.assertEqual(result['selected']['validated_nash']['objective_value'], -20.)
        self.assertEqual({np for np, _ in self.calls}, {-250., 0., 500.})

    def test_signed_np_still_rejects_nonfinite_np_negative_nuf_and_meter(self):
        for kind, value in (('np', float('nan')), ('np', float('-inf')), ('nuf', -1.), ('meter', -1.)):
            self.domain = self.make_domain((-250., 500.))
            row = self.domain['candidates'][0]
            if kind == 'np':
                row['control'].N_P_star = row['target_np_veh'] = value
            elif kind == 'nuf':
                row['control'].N_UF_star = row['target_nuf_veh_h'] = value
            else:
                row['control'].ramp_metering[next(iter(row['control'].ramp_metering))] = value
            with self.assertRaisesRegex(ValueError, 'finite and exactly action-bound'):
                self.run_selection()
        self.assertFalse(self.calls)

    def test_zero_total_budget_does_not_call_candidate_or_claim_infeasible(self):
        self.options['leader_time_budget_sec'] = 0.
        result = self.run_selection()
        self.assertEqual(self.calls, [])
        self.assertIsNone(result['selected'])
        self.assertEqual(result['metadata']['unknown_candidate_indices'], [0, 1])
        self.assertFalse(result['metadata']['leader_domain_infeasible'])

    def test_common_price_field_and_reference_are_reused_for_every_leader_candidate(self):
        self.domain = self.make_domain((-250., 0., 500.))
        self.costs = {-250.: -20., 0.: 0., 500.: 5.}
        before = copy.deepcopy(self.common['price_field'])
        result = self.run_selection()
        self.assertEqual(len(self.common_calls), 1)
        self.assertEqual(len(self.shared_contexts), 3)
        self.assertTrue(all(context is self.common for context in self.shared_contexts))
        self.assertEqual(self.common['price_field'], before)
        self.assertEqual(result['metadata']['common_price_measurement_count'], 1)
        self.assertEqual(result['metadata']['fixed_move_limits'], self.move_limits)

    def test_physical_seeds_share_current_decision_target_without_retargeting(self):
        self.domain['quantity_semantics']='predicted_accepted_mainline_merge'
        for row in self.domain['candidates']:
            row['target_nuf_veh_h']=None
            row['requires_merge_prediction']=True
            row['directional_budgets']={}
        self.common['nuf_initialization']={'target_veh_h':2034.526,'scope':'frozen-at-entry'}
        # This query is deliberately noncallable: seed-specific predictions
        # must not choose another target after entry initialization.
        def stop_unscored(controller,state,forecast,historical,proposal,mapping,**kw):
            self.calls.append((proposal['target_np_veh'],proposal['target_nuf_veh_h']))
            self.assertEqual(proposal['control'].N_UF_star,2034.526)
            self.assertFalse(proposal['requires_merge_prediction'])
            self.assertIs(kw['common'],self.common)
            return {'target_np_veh':proposal['target_np_veh'],'target_nuf_veh_h':2034.526,
                'source_fingerprint':digest(kw['runtime_sources']),'candidate_status':'unscored_budget_stop',
                'validated_nash':None,'initializer_evidence':None,
                'response':{'game':{'error':{'kind':'evaluation_budget'}}}}
        result=self.run_selection(solve=stop_unscored)
        self.assertEqual(self.calls,[(500.,2034.526),(340.,2034.526)])
        self.assertEqual(len(self.common_calls),1)
        self.assertTrue(all(row['target_source']=='frozen-at-entry' for row in result['metadata']['candidates']))
        self.assertTrue(all(row['target_nuf_veh_h'] is None for row in self.domain['candidates']))

    def test_expired_common_prices_return_no_candidate_or_false_certificate(self):
        def expire(*args, **kwargs):
            self.clock = 121.
            kwargs['budget'].check('price_endpoint')
        result = self.run_selection(common=expire)
        meta = result['metadata']
        self.assertIsNone(result['selected'])
        self.assertFalse(self.calls)
        self.assertEqual(meta['attempted_indices'], [])
        self.assertEqual(meta['common_price_measurement_count'], 0)
        self.assertEqual(meta['stop_reason'], 'decision_time_budget_during_common_prices')
        self.assertFalse(meta['leader_domain_infeasible'])
        self.assertFalse(meta['leader_optimum_certified'])
        self.assertEqual(meta['unknown_candidate_indices'], [0, 1])

    def test_completed_price_work_that_exhausts_search_budget_starts_no_candidate(self):
        def complete_late(*args, **kwargs):
            self.clock = 115.  # 120 total minus 10 finalization reserve.
            return self.prepare_common(*args, **kwargs)
        result = self.run_selection(common=complete_late)
        self.assertIsNone(result['selected'])
        self.assertFalse(self.calls)
        self.assertEqual(result['metadata']['common_price_measurement_count'], 1)
        self.assertEqual(result['metadata']['stop_reason'], 'decision_time_budget')

    def test_explicit_unlimited_skips_whole_and_leader_clocks(self):
        self.options['ignore_wall_time_limits']=True
        def long_prices(*args,**kwargs):
            self.clock=100000.
            kwargs['budget'].check('long_prices')
            return self.prepare_common(*args,**kwargs)
        result=self.run_selection(common=long_prices)
        self.assertEqual(len(self.calls),2)
        self.assertIsNone(result['metadata']['leader_time_budget_overrun_sec'])
        self.assertTrue(result['metadata']['decision_budget']['unlimited_time'])

    def test_cooperative_overrun_retains_validated_inflight_response(self):
        self.options['leader_time_budget_sec'] = 1.
        def solve(*args, **kwargs):
            value = self.solve(*args, **kwargs)
            self.clock = 2.5
            return value
        result = self.run_selection(solve)
        self.assertEqual(len(self.calls), 1)
        self.assertIsNotNone(result['selected'])
        self.assertEqual(result['metadata']['leader_time_budget_overrun_sec'], 1.5)
        self.assertEqual(result['metadata']['stop_reason'], 'leader_time_budget')

    def test_hard_failure_aborts_selection_without_relabelling_domain(self):
        def solve(*args, **kwargs):
            if self.calls:
                raise ValueError('Active price rank is deficient')
            return self.solve(*args, **kwargs)
        result = self.run_selection(solve)
        self.assertIsNone(result['selected'])
        self.assertEqual(result['metadata']['best_completed_index'], 1)
        self.assertEqual(result['metadata']['candidates'][0]['status'], 'failed_unknown')
        self.assertFalse(result['metadata']['leader_domain_infeasible'])

    def test_initializer_failure_is_not_domain_infeasibility(self):
        def solve(*args, **kwargs):
            result = self.solve(*args, **kwargs)
            if result['target_np_veh'] == 500.:
                result.update(candidate_status='infeasible_initializer', validated_nash=None,
                    initializer_evidence={'leader_domain_infeasible': False})
                result['response']['game']['error'] = {'kind': 'infeasible_incumbent'}
            return result
        result = self.run_selection(solve)
        self.assertEqual(result['metadata']['infeasible_initializer_indices'], [1])
        self.assertEqual(result['selected']['target_np_veh'], 340.)
        self.assertFalse(result['metadata']['leader_domain_infeasible'])

    def test_infeasible_status_requires_real_witness_in_candidate_classifier(self):
        proposal = self.domain['candidates'][0]
        response = self.response(proposal)
        initial = proposal['control'].copy()
        response['game']['control'] = initial
        response['final_action_token'] = response['final_score']['action_token'] = digest(initial)
        response['game']['error'] = {'kind': 'infeasible_incumbent'}
        args = dict(target_np=340., target_nuf=7200., initial=initial, expected_owners=response['game']['owners'])
        with self.assertRaisesRegex(ValueError, 'No witnessed'):
            module._runtime_joint_candidate_validation(response, **args)
        response['final_score']['quantity_constraints']['feasible'] = False
        with self.assertRaisesRegex(ValueError, 'No witnessed'):
            module._runtime_joint_candidate_validation(response, **args)
        response['final_score']['quantity_constraints']['np'].update(
            actual=400., residual=60., violation=60., satisfied=False)
        status, validated, evidence = module._runtime_joint_candidate_validation(response, **args)
        self.assertEqual(status, 'infeasible_initializer')
        self.assertIsNone(validated)
        self.assertFalse(evidence['leader_domain_infeasible'])
        response['final_score']['model_constraint_coverage']['complete'] = False
        with self.assertRaisesRegex(ValueError, 'complete witnessed'):
            module._runtime_joint_candidate_validation(response, **args)

    def test_unscored_budget_stop_keeps_feasibility_unknown(self):
        for kind in ('time_budget', 'evaluation_budget', 'decision_deadline'):
            with self.subTest(kind=kind):
                response = copy.deepcopy(self.base)
                response['final_score'] = None
                response['game']['error']['kind'] = kind
                status, validated, evidence = module._runtime_joint_candidate_validation(response,
                    target_np=340., target_nuf=7200., initial=response['game']['control'],
                    expected_owners=response['game']['owners'])
                self.assertEqual(status, 'unscored_budget_stop')
                self.assertIsNone(validated)
                self.assertFalse(evidence['feasibility_known'])

    def test_whole_deadline_keeps_a_validated_feasible_response_and_unknown_gaps(self):
        def solve(*args, **kwargs):
            value = self.solve(*args, **kwargs)
            value['response']['game']['error'] = {'kind': 'decision_deadline', 'phase': 'search'}
            value['validated_nash'] = validate_joint_leader_result(value['response'],
                target_np_veh=value['target_np_veh'], target_nuf_veh_h=value['target_nuf_veh_h'])
            self.clock = 110.
            return value
        result = self.run_selection(solve)
        self.assertIsNotNone(result['selected'])
        self.assertEqual(result['metadata']['stop_reason'], 'decision_time_budget')
        self.assertEqual(result['metadata']['selection_status'], 'selected_best_observed')
        self.assertEqual(result['metadata']['attempted_indices'], [1])
        self.assertIsNone(result['metadata']['candidates'][1]['maximum_finite_candidate_gap'])

    def restored_infeasible_response(self, proposal, kind='time_budget'):
        response = self.response(proposal)
        initial = response['game']['control']
        response['game']['error'] = {'kind': kind, 'phase': 'search'}
        quantity = response['final_score']['quantity_constraints']
        np_row = quantity['np']; target = proposal['target_np_veh']
        np_row.update(actual=target+60., residual=60., violation=60., satisfied=False)
        quantity['feasible'] = False
        owners = quantity['net_inflow_veh_by_owner']
        owners.update(dict.fromkeys(owners, 0.))
        owners[next(iter(owners))] = np_row['actual']
        response['initializer_restoration'] = {'status': kind, 'error': {'kind': kind},
            'feasible': False, 'control': None, 'domain_infeasible': False,
            'best_infeasible': initial.copy(),
            'final_violation': (np_row['actual']-target-np_row['tolerance'])/max(1.,abs(target))}
        return response

    def test_cached_infeasible_restoration_budget_is_unknown_and_keeps_prior_best(self):
        for kind in ('time_budget', 'evaluation_budget', 'decision_deadline'):
            with self.subTest(kind=kind):
                self.calls = []; self.clock = 0.
                def solve(*args, **kwargs):
                    if not self.calls:
                        return self.solve(*args, **kwargs)
                    proposal = args[4]
                    response = self.restored_infeasible_response(proposal, kind)
                    status, validated, evidence = module._runtime_joint_candidate_validation(response,
                        target_np=proposal['target_np_veh'], target_nuf=proposal['target_nuf_veh_h'],
                        initial=response['game']['control'], expected_owners=response['game']['owners'])
                    self.assertEqual(status, 'restoration_budget_stop')
                    self.assertFalse(evidence['candidate_feasibility_known'])
                    self.assertFalse(evidence['initializer_feasible'])
                    if kind == 'decision_deadline': self.clock = 110.
                    return dict(response=response, validated_nash=validated, candidate_status=status,
                        initializer_evidence=evidence, target_np_veh=proposal['target_np_veh'],
                        target_nuf_veh_h=proposal['target_nuf_veh_h'], source_fingerprint=digest(kwargs['runtime_sources']))
                result = self.run_selection(solve)
                self.assertEqual(result['selected']['target_np_veh'], 500.)
                self.assertEqual(result['metadata']['candidates'][0]['status'], 'restoration_budget_stop')
                self.assertEqual(result['metadata']['unknown_candidate_indices'], [0])
                self.assertIsNone(result['metadata']['failure'])
                self.assertFalse(result['metadata']['leader_domain_infeasible'])

    def test_cached_infeasible_budget_requires_complete_bound_restoration_evidence(self):
        proposal = self.domain['candidates'][0]
        original = self.restored_infeasible_response(proposal)
        for broken in ('missing', 'action', 'coverage', 'quantity', 'merit', 'callback_failure'):
            response = copy.deepcopy(original)
            if broken == 'missing': del response['initializer_restoration']
            if broken == 'action': response['initializer_restoration']['best_infeasible'].offsets['SC1'] += 1.
            if broken == 'coverage': response['final_score']['model_constraint_coverage']['complete'] = False
            if broken == 'quantity': response['final_score']['quantity_constraints']['net_inflow_veh_by_owner']['SC1'] += 1.
            if broken == 'merit': response['initializer_restoration']['final_violation'] += 1.
            if broken == 'callback_failure': response['initializer_restoration']['error']['kind'] = 'callback_failure'
            with self.subTest(broken=broken), self.assertRaises(ValueError):
                module._runtime_joint_candidate_validation(response,
                    target_np=proposal['target_np_veh'], target_nuf=proposal['target_nuf_veh_h'],
                    initial=response['game']['control'], expected_owners=response['game']['owners'])

    def test_changed_final_action_or_wrong_np_is_rejected(self):
        for kind in ('action', 'np'):
            def solve(*args, **kwargs):
                value = self.solve(*args, **kwargs)
                if kind == 'action':
                    value['response']['game']['control'].offsets['SC1'] += 1.
                else:
                    value['target_np_veh'] += 1.
                return value
            result = self.run_selection(solve)
            self.assertIsNone(result['selected'])
            self.assertEqual(result['metadata']['stop_reason'], 'candidate_failure')

    def test_diverse_order_is_complete_deterministic_and_prescore(self):
        self.domain = self.make_domain((300., 350., 400., 450., 500.))
        self.costs = {v: 1. for v in (300., 350., 400., 450., 500.)}
        result = self.run_selection()
        self.assertEqual(result['metadata']['evaluation_order'], [4, 0, 2, 1, 3])
        self.assertEqual(result['metadata']['attempted_indices'], [4, 0, 2])
        self.assertEqual(result['metadata']['selected_index'], 4)  # Stable equal-J tie.

    def test_exception_mutation_cannot_change_caller_inputs(self):
        before = pickle.dumps((self.controller, self.sources, self.options), protocol=5)
        def solve(controller, *args, **kwargs):
            controller.cfg.network.ramps = ('changed',)
            raise RuntimeError('failed')
        result = self.run_selection(solve)
        self.assertIsNone(result['selected'])
        self.assertEqual(before, pickle.dumps((self.controller, self.sources, self.options), protocol=5))

    def test_unused_legacy_pool_is_not_copied_or_pickled(self):
        class UncopyablePool:
            def __deepcopy__(self, memo):
                raise AssertionError('Unused legacy pool must not be copied')
            def __reduce__(self):
                raise AssertionError('Unused legacy pool must not be pickled')
        self.controller.legacy_pool = UncopyablePool()
        self.controller.installed_callback = lambda value: value
        def solve(controller, *args, **kwargs):
            self.assertIs(controller.cfg, controller.nash_solver.cfg)
            self.assertIsNot(controller.cfg, self.controller.cfg)
            return self.solve(controller, *args, **kwargs)
        self.assertIsNotNone(self.run_selection(solve)['selected'])

    def test_exact_options_fail_before_preparation(self):
        for changes in ({'max_leader_candidates': True}, {'leader_candidate_order': 'nearest'},
                        {'leader_time_budget_sec': float('nan')}, {'new_hidden_policy': 1}):
            with patch.dict(self.options, changes), patch.object(module, 'prepare_joint_leader_candidates') as prepare:
                with self.assertRaises(ValueError):
                    self.run_selection()
                prepare.assert_not_called()


if __name__ == '__main__':
    unittest.main()
