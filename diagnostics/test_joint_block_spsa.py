"""Diagnostic simultaneous perturbation tests, all endpoints synthetic."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from diagnostics import test_runtime_joint_prices as fixtures
from diagnostics import compare_joint_block_spsa as diagnostic
from diagnostics.compare_joint_block_spsa import compare


class JointBlockSPSATests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.RuntimeJointPricesTests()
        self.fixture.setUp()
        self.measured = self.fixture.evaluate()
        self.fixture.calls.clear()

    def run_compare(self, **updates):
        f = self.fixture
        args = dict(realize=copy.deepcopy,
            validate=lambda a: {'synthetic_only': True, **f.evidence(a, f.context)},
            response_query=f.responses, pair_budgets=(8, 16), seed=13)
        args.update(updates)
        return compare(f.follower, f.reference, self.measured, **args)

    def test_full_coordinate_coverage_counts_and_feasible_one_sided_meter_pairs(self):
        result = self.run_compare()
        self.assertEqual(result['successful_response_actions'], 32)
        self.assertEqual(len(result['pairs']), 16)
        self.assertEqual([row['attempted_pairs'] for row in result['comparisons']], [8, 16])
        for checkpoint in result['comparisons']:
            self.assertTrue(checkpoint['all_coordinates_observed'])
            self.assertTrue(all(row['price_rank_complete'] for row in checkpoint['owners'].values()))
        self.assertTrue(all(0. <= v <= 100. for a in self.fixture.calls for v in a.ramp_metering.values()))
        self.assertFalse(result['production_field_installed'])
        self.assertFalse(result['selection_compared'])
        self.assertIsNone(result['selected_actions'])
        # Finite simultaneous samples must not be advertised as exact secants.
        self.assertTrue(any(row['external_delta_mae_veh_h'] > 1e-8
            for row in result['comparisons'][-1]['owners'].values()))

    def test_incomplete_coordinate_budget_keeps_prices_unknown(self):
        result = self.run_compare(pair_budgets=(1,))
        row = result['comparisons'][0]
        self.assertFalse(row['all_coordinates_observed'])
        self.assertTrue(all(o['fitted_prices'] is None for o in row['owners'].values()))
        self.assertTrue(all(o['missing_basis_indices'] for o in row['owners'].values()))

    def test_local_owner_cost_is_subtracted_from_same_response(self):
        def response(actions):
            batch = self.fixture.responses(actions)
            for item in batch['results']:
                # SC1's complete local change equals its Omega change.
                item['local_base_costs']['SC1'] = item['objective_veh_h']
            return batch
        result = self.run_compare(response_query=response, pair_budgets=(8,))
        row = result['comparisons'][0]['owners']['SC1']
        self.assertTrue(row['price_rank_complete'])
        self.assertEqual(row['estimated_external_deltas_veh_h'], [0.]*4)
        self.assertTrue(all(price['estimated'] == 0. for price in row['fitted_prices']))

    def test_seeded_pairs_are_repeatable_except_timing(self):
        a, b = self.run_compare(pair_budgets=(8,)), self.run_compare(pair_budgets=(8,))
        self.assertEqual(a['comparisons'], b['comparisons'])
        self.assertEqual([r['plus_action_token'] for r in a['pairs']], [r['plus_action_token'] for r in b['pairs']])

    def test_other_physical_context_is_not_compared_with_existing_exact_prices(self):
        def other_context(actions):
            batch = self.fixture.responses(actions)
            for row in batch['results']:
                row['frozen_context_token'] = 'another-model-or-reference'
            return batch
        result = self.run_compare(response_query=other_context, pair_budgets=(1,))
        self.assertEqual(result['successful_response_actions'], 0)
        self.assertIn('measured common physical context', result['pairs'][0]['failure']['message'])
        self.assertFalse(result['comparisons'][0]['all_coordinates_observed'])

    def test_realizer_change_and_writer_failure_are_preserved_not_partially_scored(self):
        def changed(action):
            action.green_times['SC1_p1'] += 1.
            return action
        result = self.run_compare(realize=changed, pair_budgets=(1,))
        self.assertEqual(result['successful_response_actions'], 0)
        self.assertEqual(result['pairs'][0]['status'], 'failed')
        self.assertIn('changed a requested', result['pairs'][0]['failure']['message'])
        self.assertFalse(result['comparisons'][0]['all_coordinates_observed'])
        self.assertFalse(self.fixture.calls)

    def test_deadline_preserves_attempt_without_fake_price_coverage(self):
        def check(stage):
            raise TimeoutError('whole decision deadline')
        result = self.run_compare(check_budget=check)
        self.assertEqual(result['stop_reason'], 'decision_time_budget')
        self.assertEqual(result['successful_response_actions'], 0)
        self.assertFalse(result['comparisons'][0]['all_coordinates_observed'])

    def zero_meter_edges(self):
        f = self.fixture
        for owner in f.follower.cfg.network.freeway_links:
            for row in self.measured['secants'][owner]:
                coordinate = row['coordinate']
                for ramp in f.follower._local_freeway_models[owner].owned_ramps:
                    coordinate['probe_values'][ramp] = coordinate['base_values'][ramp]
                    coordinate['direction'][ramp] = 0.

    def test_zero_columns_without_analytic_proof_remain_unknown(self):
        self.zero_meter_edges()
        result = self.run_compare(pair_budgets=(8,))
        self.assertEqual(result['fixed_meter_coordinates'], {})
        for owner in self.fixture.follower.cfg.network.freeway_links:
            row = result['comparisons'][0]['owners'][owner]
            self.assertFalse(row['price_rank_complete'])
            self.assertIsNone(row['fitted_prices'])
            self.assertEqual(row['unknown_reason'], 'unproved unobserved active coordinates')
            self.assertEqual(len(row['unknown_coordinates']), 2)

    def test_only_source_validated_fixed_columns_are_removed(self):
        self.zero_meter_edges()
        f = self.fixture
        fixed = dict(f.reference.ramp_metering)
        proof, box = {'synthetic_interval_proof': True}, object()
        self.measured['field']['fixed_meter_proofs'] = proof
        for owner in f.follower.cfg.network.freeway_links:
            self.measured['field']['owner_fits'][owner]['fixed_meter_coordinates'] = {
                r: fixed[r] for r in f.follower._local_freeway_models[owner].owned_ramps}
        with patch('evaluation.controllers.joint_owner_neighbors.validate_fixed_meter_coordinate_proofs', return_value=fixed) as validate:
            result = self.run_compare(pair_budgets=(8,), move_box=box)
        validate.assert_called_once_with(f.follower.cfg, f.reference, proof, move_box=box)
        self.assertEqual(result['fixed_meter_coordinates'], fixed)
        self.assertIn('not identified derivatives', result['fixed_meter_price_convention'])
        for owner in f.follower.cfg.network.freeway_links:
            row = result['comparisons'][0]['owners'][owner]
            self.assertTrue(row['price_rank_complete'])
            self.assertEqual(row['active_dimension'], 3)
            self.assertTrue(all(p['channel'] != 'meter' for p in row['fitted_prices']))

    def test_invalid_interval_proof_cannot_hide_zero_columns(self):
        self.zero_meter_edges()
        self.measured['field']['fixed_meter_proofs'] = {'schema': 'forged'}
        with self.assertRaisesRegex(ValueError, 'Explicit fixed meter interval proof'):
            self.run_compare(pair_budgets=(8,))
        self.assertFalse(self.fixture.calls)

    def test_native_concurrent_phase_basis_preserves_independent_p1(self):
        f = self.fixture
        f.follower.cfg.network.signal_live_phases = lambda owner: ('p1', 'p2', 'p4')
        f.follower.cfg.network.signal_actuation_contract = {'nodes': {'SC1': {
            'native_clock_basis': {'kind': 'concurrent_p1_p2'}}}}
        rows = [{'coordinate': {'direction': dict(SC1_p1=6., SC1_p2=0., SC1_p4=0., SC1=0.)}},
                {'coordinate': {'direction': dict(SC1_p1=0., SC1_p2=6., SC1_p4=-6., SC1=0.)}}]
        matrix, columns = diagnostic._vectors(f.follower, 'SC1', rows)
        self.assertEqual(matrix.tolist(), [[6., 0., 0.], [0., 12., 0.]])
        self.assertEqual(columns[0][1], 'SC1_p1')


class RecordedSPSACliTests(unittest.TestCase):
    def receipt(self, path):
        flags = ['--state-json', '--previous-action-json', '--out-action-json', '--out-action-csv',
                 '--mapping-json', '--detector-mapping-json', '--calibration-json', '--tuning-json']
        argv = ['-B', '-X', 'utf8', 'evaluation/controllers/vissim_stackelberg_adapter.py']
        for flag in flags:
            argv += [flag, str(path)]
        argv += ['--controller', 'wu-link', '--mode', 'fast-smoke']
        return {'arguments': argv, 'experiment_environment': {'RW_OFFSET_WRITER': 'experiment'}, 'completed': False}

    def test_saved_inputs_exactly_preserved_and_only_output_paths_changed(self):
        receipt = self.receipt('recorded.json')
        argv = diagnostic._recorded_arguments(receipt, Path('new'))
        before, after = dict(zip(receipt['arguments'][4::2], receipt['arguments'][5::2])), dict(zip(argv[::2], argv[1::2]))
        self.assertEqual({k for k in before if before[k] != after[k]}, {'--out-action-json', '--out-action-csv'})
        receipt['arguments'][-4] = '--mode'
        with self.assertRaisesRegex(ValueError, 'exact unique'):
            diagnostic._recorded_arguments(receipt, Path('new'))

    def test_success_and_exact_failure_both_intercept_before_action_writer(self):
        from contextlib import nullcontext
        import evaluation.controllers as package
        from evaluation.controllers.area_follower_objective import DecisionBudget
        fixture = fixtures.RuntimeJointPricesTests()
        fixture.setUp()
        measured = fixture.evaluate()
        root = Path(diagnostic.__file__).resolve().parents[1]
        for failed_exact in (False, True):
            with self.subTest(failed_exact=failed_exact), tempfile.TemporaryDirectory(dir=root/'diagnostics') as directory:
                directory = Path(directory)
                input_path = directory/'recorded.json'
                input_path.write_text('{}', encoding='utf-8')
                receipt_path = directory/'receipt.json'
                receipt_path.write_text(json.dumps(self.receipt(input_path)), encoding='utf-8')
                calls = {'prepare': 0, 'closed': 0, 'action_writer': 0}
                def query(actions):
                    return fixture.responses(actions)
                query.stats = lambda: {'synthetic': True}
                query.close = lambda: calls.update(closed=calls['closed']+1)
                def prepare(*args, budget, **kwargs):
                    calls['prepare'] += 1
                    budget.response_query = query
                    if failed_exact:
                        raise TimeoutError('exact preparation deadline')
                    return dict(measured=measured, follower=fixture.follower, reference=fixture.reference, response_query=query)
                def evidence(action, context):
                    owners = fixture.evidence(action, context)['owner_physical_sha256']
                    return {'ordered_rows': [], 'physical_rows': {('synthetic', 'row'): ()},
                            'owner_physical_sha256': owners, 'owner_model_sha256': owners, 'provenance': {'synthetic': True}}
                joint = NS(DecisionBudget=DecisionBudget, prepare_common_joint_prices=prepare,
                    shared_query_runtime_scope=nullcontext, solve_runtime_joint_leader=None,
                    _joint_runtime_callbacks=lambda *a, **k: ({'ownership': fixture.ownership,
                        'command_evidence': evidence, 'move_box': None}, {}, None))
                meters = NS(prepare_canonical_candidate=lambda action, *a, **k: copy.deepcopy(action))
                adapter = NS(__file__='synthetic_adapter.py', _PHASE_VECTOR_FOLLOWER={})
                def main():
                    outer = DecisionBudget(120.)
                    try:
                        joint.solve_runtime_joint_leader(NS(nash_solver=fixture.follower), NS(time_sec=1050.),
                            [NS()], fixture.reference, {}, runtime_sources={},
                            options={'nuf_tolerance_veh_h': 0.}, budget=outer)
                        calls['action_writer'] += 1
                    finally:
                        if hasattr(outer, 'response_query'):
                            outer.response_query.close()
                adapter.main = main
                with patch('diagnostics.check_selected_open_meter_alias.validate_environment', return_value={'synthetic': True}), \
                     patch.object(package, 'vissim_stackelberg_adapter', adapter, create=True), \
                     patch.object(package, 'area_follower_objective', joint), \
                     patch.object(package, 'area_meter_finalization', meters, create=True):
                    report = diagnostic.run_recorded(receipt_path, directory/'output', exact_budget_sec=400.,
                        spsa_budget_sec=180., pair_budgets=(8,))
                self.assertEqual(calls, {'prepare': 1, 'closed': 1, 'action_writer': 0})
                self.assertTrue(report['adapter_intercepted_before_action_write'])
                self.assertFalse(report['action_written'])
                self.assertFalse(report['production_joint_decision_completed'])
                self.assertFalse(report['approximate_price_field_installed'])
                self.assertEqual(report['input_changes'], [])
                self.assertEqual(report['status'], 'failed' if failed_exact else 'completed', report.get('error'))
                if failed_exact:
                    self.assertNotIn('comparison', report)
                else:
                    self.assertEqual(report['comparison']['successful_response_actions'], 16)
                persisted = json.loads((directory/'output/comparison.json').read_text(encoding='utf-8'))
                self.assertEqual(persisted['status'], report['status'])


if __name__ == '__main__':
    unittest.main()
