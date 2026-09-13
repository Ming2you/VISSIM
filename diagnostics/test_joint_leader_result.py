"""Pure shared-result transport checks; no endpoint, controller solve or native run."""
import copy
import hashlib
import json
from pathlib import Path
import pickle
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
from evaluation.controllers import area_leader_objective as subject
from src.controllers.nash_solver import NashResult
from src.models.state import ControlAction


def digest(value):
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def fixture():
    signals = [f'SC{i}' for i in range(1, 18)]
    owners = signals + ['FW_E', 'FW_W']
    control = ControlAction(N_P_star=340., N_UF_star=7200.,
        ramp_metering=dict.fromkeys(('R_D_E', 'R_F_E', 'R_D_W', 'R_F_W'), 1800.),
        vsl={'FW_E': 80., 'FW_W': 100.}, green_times={'SC1_p1': 30.},
        offsets={'SC1': 12.}, inflow_outflow_allocation={'m1': 7.},
        diagnostics={'canonical_meter': {'requested_rates': [1400., 1450.]}})
    def quantity(mode, unit, actual, target):
        residual = actual - target
        return dict(mode=mode, unit=unit, actual=actual, target=target,
            residual=residual, violation=max(0., residual) if mode == 'cap' else abs(residual),
            tolerance=1e-7, constraint_checked=True, satisfied=True)
    constraints = dict(schema='shared-quantity-constraints/v1', feasible=True,
        np=quantity('cap', 'veh', 255., 340.),
        nuf=quantity('equality', 'veh/h', 7200., 7200.),
        net_inflow_veh_by_owner=dict.fromkeys(signals, 15.),
        meter_rate_veh_h_by_owner={'FW_E': 3600., 'FW_W': 3600.})
    return dict(game=dict(control=control, owners=owners, owner_count=19,
        per_owner={o: dict(complete=False, gap=None, status='unvisited') for o in owners},
        final_check_complete=False, certified=False, maximum_finite_candidate_gap=None,
        error={'kind': 'time_budget', 'phase': 'search'}, search_status='interrupted_time_budget',
        sweeps_started=1, sweeps_completed=0, evaluations=44,
        limits={'improvement_tolerance': 1e-8, 'shared_tolerance': 1e-7}),
        final_score=dict(objective_veh_h=-12.,
            control_area={'near_score_veh_h': -12., 'additional_cost_veh_h': 0.,
                          'ttt_veh_h': 8., 'ttd_veh': 240., 'beta_seconds': 300.},
            local_base_costs=dict.fromkeys(owners, 2.), owner_costs=dict.fromkeys(owners, -1.),
            physical_owner_tokens={o: digest(o) for o in owners},
            action_token=digest(control), response_token=digest('response'),
            frozen_context_token=digest('context'), price_or_quantity_terms_included=False,
            model_constraint_coverage={'complete': True, 'conditional_model_feasibility_witness': True},
            conditional_model_feasibility_witness=True, resource_summary={'max_exceedance_veh': 0.},
            shared_capacity_certificate=False, quantity_constraints=constraints,
            native_prehead_reference_overdraw_veh=.716),
        final_action_token=digest(control), fixed_inputs_token=digest('fixed'),
        command_evidence={'untouched_root_final_csv_responsibility': True},
        native_plant_feasibility_certified=False)


class JointLeaderResultTests(unittest.TestCase):
    def test_explicit_no_wall_limit_transports_without_inventing_gap(self):
        value=fixture()
        value['game']['limits']['time_budget_sec']=None
        value['game']['error']={'kind':'evaluation_budget','phase':'search'}
        result=self.validate(value)
        self.assertEqual(result['objective_value'],-12.)
        self.assertIsNone(result['diagnostics']['joint_shared_response']['maximum_finite_candidate_gap'])
        json.dumps(result['diagnostics'],allow_nan=False)

    def validate(self, value, **kwargs):
        return subject.validate_joint_leader_result(value,
            target_np_veh=kwargs.get('np', 340.), target_nuf_veh_h=kwargs.get('nuf', 7200.))

    def test_budget_result_constructs_actual_nash_with_unknown_legacy_residuals(self):
        value = fixture()
        nash = NashResult(**self.validate(value))
        self.assertEqual(nash.objective_value, -12.)  # Already includes beta; no double charge.
        self.assertEqual(nash.iterations, 0)
        self.assertIs(nash.converged, False)
        self.assertIsNone(nash.residual_objective)
        self.assertIsNone(nash.residual_control)
        marker = nash.diagnostics['joint_shared_response']
        self.assertIsNone(marker['maximum_finite_candidate_gap'])
        self.assertEqual(marker['quantity_constraints']['np']['actual'], 255.)
        self.assertEqual((nash.control.N_P_star, nash.control.N_UF_star), (340., 7200.))
        self.assertEqual(marker['native_prehead_reference_overdraw_veh'], .716)
        self.assertIs(marker['final_csv_verified'], False)
        self.assertIs(marker['shared_capacity_certificate'], False)
        json.dumps(nash.diagnostics, allow_nan=False)

    def test_complete_finite_certificate_does_not_claim_legacy_convergence(self):
        value = fixture()
        game = value['game']
        game.update(error=None, final_check_complete=True, certified=True,
                    maximum_finite_candidate_gap=0., sweeps_completed=1)
        for row in game['per_owner'].values():
            row.update(complete=True, gap=0., status='complete')
        result = self.validate(value)
        self.assertTrue(result['diagnostics']['joint_shared_response']['finite_neighborhood_certified'])
        self.assertFalse(result['converged'])
        self.assertIsNone(result['residual_objective'])
        self.assertIsNone(result['residual_control'])

    def test_partial_final_gaps_survive_budget_stop(self):
        value = fixture()
        value['game']['per_owner']['SC1'].update(complete=True, gap=.2, status='complete')
        result = self.validate(value)['diagnostics']['joint_shared_response']
        self.assertEqual(result['per_owner']['SC1']['gap'], .2)
        self.assertIsNone(result['per_owner']['SC2']['gap'])
        self.assertIsNone(result['maximum_finite_candidate_gap'])

    def test_inputs_untouched_and_nested_result_isolated(self):
        value = fixture()
        before = pickle.dumps(value, protocol=5)
        result = self.validate(value)
        result['control'].diagnostics['canonical_meter']['requested_rates'][0] = -1.
        result['diagnostics']['joint_shared_response']['quantity_constraints']['np']['actual'] = -2.
        self.assertEqual(before, pickle.dumps(value, protocol=5))

    def test_partial_round_robin_search_is_separate_from_unvisited_final_audit(self):
        value = fixture(); game = value['game']
        owners = game['owners']
        search = {o: dict(complete=False, gap=None, status='unvisited', evaluations=0)
                  for o in owners}
        # First pass stopped after 16 checked neighbors and the 17th incumbent.
        for owner in owners[:16]:
            search[owner].update(status='evaluating', evaluations=2,
                announced_candidates=104, unique_neighbors=1, feasible_neighbors=1,
                incumbent_cost=2., observed_gap_lower_bound=.75)
        search[owners[16]].update(status='evaluating', evaluations=1,
            announced_candidates=None, unique_neighbors=0, feasible_neighbors=0,
            incumbent_cost=2., observed_gap_lower_bound=None)
        game.update(evaluations=33, traversal='round_robin', neighbor_calls=17,
            search_sweeps=[{'sweep': 1, 'owners': search}],
            accepted_updates=[{'sweep': 1, 'owner': owners[0], 'from_cost': 2.,
                'to_cost': 1.25, 'gap': .75, 'partial_sweep': True,
                'lever_values': [('offsets', owners[0], 12.)],
                'physical_command_key': [(owners[0], 'str', 'command')],
                'selection_policy': 'Largest completely checked own-payoff improvement at the fixed sweep incumbent'}])
        before = pickle.dumps(value, protocol=5)
        marker = self.validate(value)['diagnostics']['joint_shared_response']
        kept = marker['search']
        for field in ('search_sweeps', 'accepted_updates', 'traversal', 'neighbor_calls'):
            self.assertEqual(kept[field], game[field])
        self.assertEqual(kept['missing_producer_fields'], [])
        self.assertEqual(sum(r['evaluations'] for r in kept['search_sweeps'][0]['owners'].values()), 33)
        self.assertTrue(all(r['status'] == 'unvisited' for r in marker['per_owner'].values()))
        self.assertIn('does not imply no search', marker['per_owner_scope'])
        self.assertFalse(marker['final_check_complete'])
        self.assertFalse(marker['finite_neighborhood_certified'])
        self.assertIsNone(marker['maximum_finite_candidate_gap'])
        json.dumps(marker, allow_nan=False)
        kept['search_sweeps'][0]['owners'][owners[0]]['evaluations'] = -1
        kept['accepted_updates'][0]['lever_values'].append(('changed',))
        self.assertEqual(before, pickle.dumps(value, protocol=5))
        game['accepted_updates'][0]['to_cost'] = -99.
        self.assertEqual(kept['accepted_updates'][0]['to_cost'], 1.25)

    def test_absent_search_history_is_unknown_without_changing_legacy_acceptance(self):
        marker = self.validate(fixture())['diagnostics']['joint_shared_response']
        fields = ('search_sweeps', 'accepted_updates', 'traversal', 'neighbor_calls')
        self.assertEqual(marker['search']['missing_producer_fields'], list(fields))
        self.assertTrue(all(marker['search'][field] is None for field in fields))
        self.assertEqual(marker['evaluations'], 44)

    def test_no_missing_nonfinite_or_extra_endpoint_cost(self):
        for field, bad in (('objective_veh_h', None), ('objective_veh_h', float('nan')),
                           ('price_or_quantity_terms_included', True)):
            with self.subTest(field=field, bad=bad):
                value = fixture(); value['final_score'][field] = bad
                with self.assertRaises(ValueError): self.validate(value)
        value = fixture(); value['final_score'] = None
        with self.assertRaises(ValueError): self.validate(value)
        for key, bad in (('near_score_veh_h', 1.), ('additional_cost_veh_h', 1.)):
            value = fixture(); value['final_score']['control_area'][key] = bad
            with self.assertRaises(ValueError): self.validate(value)

    def test_full_action_token_binds_nonlever_metadata_too(self):
        for kind in ('offset', 'metadata', 'token'):
            value = fixture()
            if kind == 'offset': value['game']['control'].offsets['SC1'] += 1.
            elif kind == 'metadata': value['game']['control'].diagnostics['canonical_meter']['requested_rates'][0] += 1.
            else: value['final_score']['action_token'] = digest('wrong')
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'scored full action'):
                self.validate(value)

    def test_frozen_targets_cannot_be_closed_to_realized_or_expanded(self):
        value = fixture()
        for targets in ({'np': 255.}, {'nuf': 5416.}):
            with self.subTest(targets=targets), self.assertRaises(ValueError):
                self.validate(value, **targets)
        for field, bad in (('N_P_star', 255.), ('N_UF_star', 5416.)):
            value = fixture(); setattr(value['game']['control'], field, bad)
            value['final_action_token'] = value['final_score']['action_token'] = digest(value['game']['control'])
            with self.subTest(field=field), self.assertRaises(ValueError): self.validate(value)

    def test_true_feasible_flag_cannot_hide_bad_reported_quantities(self):
        for channel, key, bad in (('np', 'actual', 254.), ('np', 'target', 255.),
                                 ('np', 'residual', 0.), ('np', 'violation', 1.),
                                 ('np', 'tolerance', float('inf')), ('nuf', 'mode', 'dual'),
                                 ('nuf', 'actual', True), ('nuf', 'satisfied', 1)):
            value = fixture(); value['final_score']['quantity_constraints'][channel][key] = bad
            with self.subTest(channel=channel, key=key), self.assertRaises(ValueError): self.validate(value)

    def test_true_feasible_flag_cannot_hide_actual_np_cap_exceedance(self):
        value = fixture(); q = value['final_score']['quantity_constraints']
        q['net_inflow_veh_by_owner']['SC1'] = 115.
        q['np'].update(actual=355., residual=15., violation=15.)
        with self.assertRaises(ValueError): self.validate(value)

    def test_missing_owners_and_meter_rates_rejected(self):
        for field in ('local_base_costs', 'owner_costs', 'physical_owner_tokens'):
            value = fixture(); value['final_score'][field].pop('SC1')
            with self.subTest(field=field), self.assertRaises(ValueError): self.validate(value)
        value = fixture(); value['final_score']['quantity_constraints']['net_inflow_veh_by_owner'].pop('SC1')
        with self.assertRaises(ValueError): self.validate(value)
        value = fixture(); value['game']['control'].ramp_metering.pop('R_D_E')
        value['final_action_token'] = value['final_score']['action_token'] = digest(value['game']['control'])
        with self.assertRaises(ValueError): self.validate(value)

    def test_missing_coverage_resource_overdraw_or_native_claim_rejected(self):
        for mutate in (
            lambda s: s['model_constraint_coverage'].update(complete=False),
            lambda s: s['model_constraint_coverage'].update(conditional_model_feasibility_witness=False),
            lambda s: s.update(conditional_model_feasibility_witness=False),
            lambda s: s['resource_summary'].update(max_exceedance_veh=.1),
            lambda s: s.update(shared_capacity_certificate=True)):
            value = fixture(); mutate(value['final_score'])
            with self.assertRaises(ValueError): self.validate(value)
        value = fixture(); value['native_plant_feasibility_certified'] = True
        with self.assertRaises(ValueError): self.validate(value)

    def test_nonbudget_callback_failure_rejected_even_with_scored_incumbent(self):
        value = fixture(); value['game']['error']['kind'] = 'callback_contract_failure'
        with self.assertRaisesRegex(ValueError, 'callback failure'): self.validate(value)

    def test_zero_gap_or_certificate_cannot_replace_incomplete_check(self):
        for mutate in (
            lambda g: g.update(maximum_finite_candidate_gap=0.),
            lambda g: g.update(certified=True),
            lambda g: g.update(final_check_complete=True),
            lambda g: g['per_owner']['SC1'].update(gap=0.)):
            value = fixture(); mutate(value['game'])
            with self.assertRaises(ValueError): self.validate(value)

    def test_explicit_helper_does_not_install_any_legacy_hooks(self):
        from src.controllers.leader import Leader
        from src.controllers.stackelberg_mpc import StackelbergMPCController as MPC
        functions = (Leader.objective_terms, MPC._leader_evaluation_base,
                     MPC._close_nash_response_leader_action, MPC._apply_output_closure)
        self.validate(fixture())
        self.assertEqual(functions, (Leader.objective_terms, MPC._leader_evaluation_base,
                                   MPC._close_nash_response_leader_action, MPC._apply_output_closure))


if __name__ == '__main__':
    unittest.main()
