"""Actual main builder/phase-price callers; no endpoint, MPC or VISSIM."""
from contextlib import ExitStack
from dataclasses import asdict
import json
import os
import pickle
import subprocess
import sys
import unittest
from unittest.mock import patch

from diagnostics.test_shared_service_pool import ROOT, adapter, inputs, installed
from src.controllers.priced_wu_link_controller import PricedWuLinkStackelbergController


def built_inputs():
    cfg, state, action, demand, model, raw, detectors = inputs()
    tuning = adapter.load_optional_json(str(ROOT / 'diagnostics/area_candidate_configs/n7_area_beta0.json'))
    from evaluation.controllers import local_signal_service as pool
    pool.configure(cfg, {'urban': {'shared_local_service_pool': True}})
    controller = adapter.build_priced_wu_link_controller(cfg, tuning)
    adapter.install_vissim_terminal_cost_objective(controller, cfg, tuning)
    adapter.install_price_worker_bootstrap(controller, raw, detectors)
    return controller, state, action, demand, raw, detectors


def local_result(controller, state, action, demand):
    follower = controller.nash_solver
    follower.phase_price_local_cost_model = controller.phase_price_local_cost_model
    ctx = follower._phase_refine_context(state, action, demand)
    setup = follower._phase_refine_signal_setup('SC1004', state, ctx)
    phases = {p: action.green_times['SC1004_' + p] for p in ('p1', 'p2', 'p3', 'p4')}
    score = follower._phase_local_cost_phased('SC1004', phases, setup, ctx)
    return {'score': score, 'seed': asdict(setup['ready_seed']),
            'substeps': ctx['substeps'], 'default_phase_resolved': follower.ramp_aware_phase_resolved}


class MainStackTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict(os.environ, {'RW_OFFSET_WRITER': 'experiment'}))
        self.pool, _, self.runtime = self.stack.enter_context(installed())
        self.stack.enter_context(patch.object(PricedWuLinkStackelbergController, '_refresh_phase_prices',
            PricedWuLinkStackelbergController._refresh_phase_prices))
        self.controller, self.state, self.action, self.demand, self.raw, self.detectors = built_inputs()

    def test_actual_main_builder_has_explicit_ready_seed(self):
        result = local_result(self.controller, self.state, self.action, self.demand)
        self.assertFalse(result['default_phase_resolved'])
        self.assertEqual(result['seed']['start_step'], 180)
        self.assertIsNone(self.pool._READY_CONTEXT.get())

    def test_actual_phase_refresh_uses_shared_cost_without_solve_context(self):
        controller = self.controller
        calls = []
        original = self.pool.ramp_refinement_cost
        def trace(agent, signal, phases, setup, ctx):
            self.assertIsNone(self.pool._READY_CONTEXT.get())
            calls.append((signal, setup['ready_seed']))
            return original(agent, signal, phases, setup, ctx)
        # Only the expensive GLOBAL finite differences are stubs. Every setup,
        # green profile and LOCAL candidate cost follows the actual main stack.
        def global_values(state, previous, forecast, tasks):
            return {(signal, phase): 0. for signal, phase, _ in tasks}
        before = pickle.dumps((self.state, self.action, self.demand))
        with patch.object(controller, '_global_ttt_with_phases', return_value=0.), \
             patch.object(controller, '_phase_price_rollouts', side_effect=global_values), \
             patch.object(self.pool, 'ramp_refinement_cost', side_effect=trace):
            controller._refresh_phase_prices(self.state, [self.demand], self.action)
        self.assertGreater(len(calls), 1)
        self.assertEqual({signal for signal, _ in calls}, {'SC1004'})
        self.assertTrue(all(seed == calls[0][1] for _, seed in calls))
        self.assertEqual(before, pickle.dumps((self.state, self.action, self.demand)))
        self.assertIsNone(self.pool._READY_CONTEXT.get())

    def test_serialized_actual_controller_bootstrap_restores_phase_ready(self):
        self.assertTrue(self.controller.price_worker_bootstrap)
        expected = local_result(self.controller, self.state, self.action, self.demand)
        code = '''import pickle,sys,json
from diagnostics.test_shared_service_main_stack import local_result
controller,state,action,demand=pickle.loads(sys.stdin.buffer.read())
print(json.dumps(local_result(controller,state,action,demand),sort_keys=True))
'''
        result = subprocess.run([sys.executable, '-X', 'utf8', '-c', code],
            input=pickle.dumps((self.controller, self.state, self.action, self.demand)),
            capture_output=True, cwd=ROOT, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_late_installer_repair_is_idempotent_and_preserves_other_ramp(self):
        follower = self.controller.nash_solver
        follower.phase_price_local_cost_model = self.controller.phase_price_local_cost_model
        tuning = adapter.load_optional_json(str(ROOT / 'diagnostics/area_candidate_configs/n7_area_beta0.json'))
        context_before = type(follower)._phase_refine_context
        adapter.install_ramp_aware_phase_local(self.controller, tuning)
        ctx = follower._phase_refine_context(self.state, self.action, self.demand)
        setup = follower._phase_refine_signal_setup('SC1001', self.state, ctx)
        phases = {p: self.action.green_times['SC1001_' + p] for p in ('p1', 'p2', 'p3', 'p4')}
        expected = follower._phase_local_cost_phased('SC1001', phases, setup, ctx)
        self.pool.install_refinement(self.controller.cfg)
        self.assertIs(type(follower)._phase_refine_context, context_before)
        methods = tuple(getattr(type(follower), name) for name in (
            '_phase_refine_context', '_phase_refine_signal_setup', '_phase_local_cost_phased'))
        self.pool.install_refinement(self.controller.cfg)
        self.assertEqual(methods, tuple(getattr(type(follower), name) for name in (
            '_phase_refine_context', '_phase_refine_signal_setup', '_phase_local_cost_phased')))
        newer = follower._phase_refine_context(self.state, self.action, self.demand)
        setup_new = follower._phase_refine_signal_setup('SC1001', self.state, newer)
        self.assertEqual(expected, follower._phase_local_cost_phased('SC1001', phases, setup_new, newer))
        self.assertEqual(setup_new['ramp_aware'], True)
        self.assertNotIn('shared_ramp_service', setup_new)
        self.assertEqual(local_result(self.controller, self.state, self.action, self.demand)['seed']['start_step'], 180)

    def test_final_installer_off_preserves_original_methods_and_cost(self):
        follower = self.controller.nash_solver
        self.pool.configure(self.controller.cfg, {'urban': {'shared_local_service_pool': False}})
        follower.phase_price_local_cost_model = self.controller.phase_price_local_cost_model
        ctx = follower._phase_refine_context(self.state, self.action, self.demand)
        setup = follower._phase_refine_signal_setup('SC1004', self.state, ctx)
        phases = {p: self.action.green_times['SC1004_' + p] for p in ('p1', 'p2', 'p3', 'p4')}
        before = follower._phase_local_cost_phased('SC1004', phases, setup, ctx)
        names = ('_phase_refine_context', '_phase_refine_signal_setup', '_phase_local_cost_phased')
        methods = tuple(getattr(type(follower), name) for name in names)
        self.pool.install_refinement(self.controller.cfg)
        self.assertEqual(methods, tuple(getattr(type(follower), name) for name in names))
        self.assertEqual(before, follower._phase_local_cost_phased('SC1004', phases, setup, ctx))
        self.assertNotIn('shared_ramp_service', setup)


if __name__ == '__main__':
    unittest.main()
