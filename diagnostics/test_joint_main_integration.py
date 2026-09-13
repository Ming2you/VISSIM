"""Focused native adapter boundaries; no model endpoints or COM calls."""
import copy
import csv
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from diagnostics.test_area_meter_finalization import CanonicalMeterCandidateTests
from diagnostics.test_joint_leader_result import fixture
from evaluation.controllers import area_leader_objective as leader
from evaluation.controllers import area_meter_finalization as meters
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers.area_follower_objective import DecisionBudget


OPTIONS = dict(max_evaluations=80, time_budget_sec=240., improvement_tolerance=1e-7,
    shared_tolerance=1e-7, np_tolerance_veh=1e-7, nuf_tolerance_veh_h=1e-7,
    traversal='round_robin', max_leader_candidates=3, leader_time_budget_sec=1800.,
    leader_candidate_order='diverse')


class JointMainIntegrationTests(unittest.TestCase):
    def test_absent_option_preserves_legacy_without_reading_cfg(self):
        self.assertIsNone(adapter.joint_owner_game_settings({}, object(), 'stackelberg'))

    def test_variant_requires_explicit_joint_limits_and_disables_legacy_selection(self):
        cfg = SimpleNamespace(network=SimpleNamespace(control_area_enabled=True),
            simulation=SimpleNamespace(T_c_sec=150.),
            mpc=SimpleNamespace(leader_budget_off=False, wu_faithful_np_coordination_mode='cap',
                wu_faithful_nuf_coordination_mode='equality', stackelberg_enable_fallback=False,
                stackelberg_enable_pfo_incumbent=False))
        tuning = {'adapter': {'joint_owner_game': OPTIONS}}
        expected = dict(OPTIONS, decision_time_budget_sec=120., finalization_reserve_sec=10.,
                        response_cache_enabled=True, response_parallel_workers=0)
        for mode in ('wu-link', 'no-control'):
            self.assertEqual(adapter.joint_owner_game_settings(tuning, cfg, mode), expected)
        self.assertEqual(tuning['adapter']['joint_owner_game'], OPTIONS)
        balanced = copy.deepcopy(tuning)
        balanced['adapter']['joint_owner_game']['traversal'] = 'round_robin_balanced'
        balanced['adapter']['joint_owner_game']['nuf_tolerance_veh_h'] = 40.
        actual = adapter.joint_owner_game_settings(balanced, cfg, 'wu-link')
        self.assertEqual(actual['traversal'], 'round_robin_balanced')
        self.assertEqual(actual['nuf_tolerance_veh_h'] * 450 / 3600, 5.)
        for field in ('stackelberg_enable_fallback', 'stackelberg_enable_pfo_incumbent'):
            bad = copy.deepcopy(cfg)
            setattr(bad.mpc, field, True)
            with self.assertRaisesRegex(ValueError, 'legacy PFO'):
                adapter.joint_owner_game_settings(tuning, bad, 'wu-link')
        for key, value in (('max_evaluations', True), ('leader_time_budget_sec', float('nan')),
                           ('time_budget_sec', 0), ('traversal', 'unknown'),
                           ('decision_time_budget_sec', 150.), ('finalization_reserve_sec', 120.),
                           ('response_cache_enabled', 'true'), ('response_parallel_workers', True),
                           ('response_parallel_workers', 2), ('response_parallel_workers', 5)):
            bad = copy.deepcopy(tuning)
            bad['adapter']['joint_owner_game'][key] = value
            with self.assertRaises(ValueError):
                adapter.joint_owner_game_settings(bad, cfg, 'wu-link')

    def test_explicit_decision_budget_and_cache_switch_leave_control_period_intact(self):
        cfg = SimpleNamespace(network=SimpleNamespace(control_area_enabled=True),
            simulation=SimpleNamespace(T_c_sec=150.),
            mpc=SimpleNamespace(leader_budget_off=False, wu_faithful_np_coordination_mode='cap',
                wu_faithful_nuf_coordination_mode='equality', stackelberg_enable_fallback=False,
                stackelberg_enable_pfo_incumbent=False))
        specified = dict(OPTIONS, decision_time_budget_sec=100., finalization_reserve_sec=15.,
                         response_cache_enabled=False, response_parallel_workers=1)
        result = adapter.joint_owner_game_settings({'adapter': {'joint_owner_game': specified}}, cfg, 'wu-link')
        self.assertEqual(result, specified)
        self.assertEqual(cfg.simulation.T_c_sec, 150.)
        specified['ignore_wall_time_limits']=True
        self.assertEqual(adapter.joint_owner_game_settings({'adapter':{'joint_owner_game':specified}},cfg,'wu-link'),specified)
        self.assertEqual(cfg.simulation.T_c_sec,150.)
        specified['ignore_wall_time_limits']='true'
        with self.assertRaisesRegex(ValueError,'must be boolean'):
            adapter.joint_owner_game_settings({'adapter':{'joint_owner_game':specified}},cfg,'wu-link')

    def test_actual_historical_command_pair_binds_saved_context_and_rejects_mismatch(self):
        cfg, control = CanonicalMeterCandidateTests().fixture()
        meters.finalize(control, cfg)
        control.diagnostics[meters.WRITTEN_CONTEXT] = copy.deepcopy(cfg.network.control_area_meter_context)
        context = cfg.network.control_area_meter_context
        physical = adapter.real_world_ramp_meter_actions(control.copy(), cfg, context['actuation'], context['mapping'])
        rows = [{'kind': 'ramp_meter', 'id': mid, 'sc_no': row['sc_no'],
                 'rate_vph': round(row['rate_vph'], 3), 'green_sec': round(row['green_sec'], 3)}
                for mid, row in physical.items()]
        raw = {key: getattr(control, key) for key in ('N_P_star', 'N_UF_star', 'green_times',
            'offsets', 'vsl', 'ramp_metering', 'inflow_outflow_allocation', 'diagnostics')}
        raw['run_provenance'] = {'run_id': 'fixture-run'}
        raw['metadata'] = {'sim_sec': context['sim_sec'], 'run_provenance': {'run_id': 'fixture-run'}}
        cfg.network.control_area_meter_context['sim_sec'] += 150.
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'action_000750.json'
            path.write_text(json.dumps(raw), encoding='utf-8')
            def write_rows():
                with path.with_suffix('.csv').open('w', encoding='utf-8', newline='') as stream:
                    writer = csv.DictWriter(stream, fieldnames=adapter.action_csv_schema.ACTION_CSV_FIELDS)
                    writer.writeheader()
                    writer.writerows(rows)
            write_rows()
            def load(run_id='fixture-run', sec=raw['metadata']['sim_sec']):
                return adapter.load_joint_historical_reference(path, control, cfg,
                    expected_run_id=run_id, expected_previous_sim_sec=sec)
            result, pins = load()
            self.assertEqual(len(pins), 2)
            self.assertEqual(result['meter_anchor']['historical_context_sec'], raw['metadata']['sim_sec'])
            for run_id, sec in (('other-run', raw['metadata']['sim_sec']),
                                ('fixture-run', raw['metadata']['sim_sec'] - 150)):
                with self.assertRaisesRegex(ValueError, 'immediately preceding action'):
                    load(run_id, sec)
            rows[0]['green_sec'] += 1
            write_rows()
            with self.assertRaisesRegex(ValueError, 'written meter rows differ'):
                load()

    def test_dispatch_preserves_final_nash_and_failed_selection_evidence(self):
        response = fixture()
        validated = leader.validate_joint_leader_result(response, target_np_veh=340., target_nuf_veh_h=7200.)
        selection = {'selected': {'validated_nash': validated, 'response': response,
            'price_installation': {'installed': True}, 'price_field': {'scope': 'fixture'}},
            'metadata': {'selection_status': 'selected_best_observed', 'ranking_indices': [1, 0]}}
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(adapter, 'load_joint_historical_reference', return_value=({'previous': 'history'}, {})), \
                patch.object(adapter, 'joint_runtime_source_pins', return_value={}), \
                patch('evaluation.controllers.area_follower_objective.expand_shared_vsl_action', return_value=('expanded-history', {'preserved': True})), \
                patch('evaluation.controllers.area_follower_objective.solve_runtime_joint_leader', return_value=selection) as solve:
            path = Path(folder) / 'action.joint.json'
            def run():
                return adapter.run_joint_owner_decision(object(), SimpleNamespace(time_sec=900.),
                    [1], object(), SimpleNamespace(simulation=SimpleNamespace(T_c_sec=150)), {}, {},
                    {'run_id': 'fixture-run'}, Path('previous.json'), OPTIONS, path, segment_vsl_func=object())
            result, final, report = run()
            self.assertEqual(result.leader_objective, -12.)
            self.assertIsNone(result.nash.residual_objective)
            self.assertFalse(result.nash.converged)
            self.assertIs(final, response)
            self.assertTrue(report['completed'])
            self.assertEqual(solve.call_args.args[3], 'expanded-history')
            selection['selected'] = None
            selection['metadata']['selection_status'] = 'aborted_failure'
            with self.assertRaisesRegex(ValueError, 'no usable final response'):
                run()
            failed = json.loads(path.read_text(encoding='utf-8'))
            self.assertFalse(failed['completed'])
            self.assertEqual(failed['selection']['selection_status'], 'aborted_failure')

    def test_worker_cleanup_failure_still_writes_failed_decision_evidence(self):
        response = fixture()
        validated = leader.validate_joint_leader_result(response, target_np_veh=340., target_nuf_veh_h=7200.)
        selection = {'selected': {'validated_nash': validated, 'response': response,
            'price_installation': {'installed': True}, 'price_field': {'scope': 'fixture'}},
            'metadata': {'selection_status': 'selected_best_observed', 'ranking_indices': [0]}}
        for selection_fails in (False, True):
            with self.subTest(selection_fails=selection_fails), tempfile.TemporaryDirectory() as folder, \
                    patch.object(adapter, 'load_joint_historical_reference', return_value=({'previous': 'history'}, {})), \
                    patch.object(adapter, 'joint_runtime_source_pins', return_value={}), \
                    patch('evaluation.controllers.area_follower_objective.expand_shared_vsl_action', return_value=('expanded-history', {})), \
                    patch('evaluation.controllers.area_follower_objective.solve_runtime_joint_leader',
                          side_effect=ValueError('selection failed') if selection_fails else None,
                          return_value=selection), \
                    patch('time.perf_counter', return_value=1.), patch('time.process_time', return_value=0.):
                events = []
                def close():
                    events.append('close')
                    raise RuntimeError('owned worker did not exit')
                def stats():
                    events.append('stats')
                    return {'owned_worker_pids': [12345], 'worker_cleanup_complete': False}
                budget = DecisionBudget(120., started=0., cpu_started=0.)
                budget.response_query = SimpleNamespace(close=close, stats=stats)
                path = Path(folder) / 'action.joint.json'
                with self.assertRaisesRegex(RuntimeError, 'owned worker did not exit'):
                    adapter.run_joint_owner_decision(object(), SimpleNamespace(time_sec=900.),
                        [1], object(), SimpleNamespace(simulation=SimpleNamespace(T_c_sec=150)), {}, {},
                        {'run_id': 'fixture-run'}, Path('previous.json'), OPTIONS, path,
                        segment_vsl_func=object(), budget=budget)
                report = json.loads(path.read_text(encoding='utf-8'))
                self.assertEqual(events, ['close', 'stats'])
                self.assertFalse(report['completed'])
                self.assertEqual(report['worker_cleanup_error'],
                    {'type': 'RuntimeError', 'message': 'owned worker did not exit'})
                self.assertFalse(report['physical_response_cache']['worker_cleanup_complete'])
                self.assertEqual(report['source_changes'], [])
                self.assertEqual(report['decision_budget']['wall_sec'], 1.)
                if selection_fails:
                    self.assertEqual(report['error'], {'type': 'ValueError', 'message': 'selection failed'})
                else:
                    self.assertEqual(report['selection'], selection['metadata'])


if __name__ == '__main__':
    unittest.main()
