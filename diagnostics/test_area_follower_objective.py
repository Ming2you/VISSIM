"""Actual follower solve + unchanged guard, with explicit endpoint response fixtures."""
from __future__ import annotations
import ast
import copy
import inspect
from pathlib import Path
import sys
import textwrap
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/NumSim-mine")]
from evaluation.controllers import area_follower_objective as proposed
from diagnostics.probe_signal_feasibility import setup
from evaluation.controllers import vissim_stackelberg_adapter as adapter, area_meter_finalization
from diagnostics.review_fixtures import fixture_path
from src.controllers import rollout_endpoint
from src.controllers.wu_faithful_follower import WuFaithfulFollower
from src.models.state import ControlAction

BASE_ROLLOUT = WuFaithfulFollower._rollout_horizon_ttt
BASE_SOLVE = WuFaithfulFollower.solve
source = ast.parse(textwrap.dedent(inspect.getsource(WuFaithfulFollower._solve_followers)))
guard = next(n for n in ast.walk(source) if isinstance(n, ast.If) and "offset_keep_margin" in ast.unparse(n.test))
GUARD = compile(ast.Module(body=[guard], type_ignores=[]), "actual offset retention guard", "exec")


def configure_actual_meter_context(cfg, tuning, state, raw, mapping):
    calibration = adapter.load_optional_json(str(ROOT / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"))
    calibration = adapter.deep_update(dict(calibration), tuning.get("calibration_override", {}))
    previous = fixture_path(ROOT / "evaluation/runs/codex_nc_s13_6056c94_20260909_retry/decisions_codex_nc_s13_6056c94_20260909_retry/action_000001.json")
    return area_meter_finalization.configure(adapter, cfg, tuning, mapping, raw, str(previous), state, calibration)


class AreaFollowerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg, cls.state, _, cls.tuning, cls.raw, cls.mapping, _ = setup()

    def exercise(self, area, on_j=-30., off_j=-10., endpoint_error=False):
        cfg = copy.deepcopy(self.cfg)
        controller = adapter.build_priced_wu_link_controller(cfg, self.tuning)
        cfg.network.control_area_enabled = area
        configure_actual_meter_context(cfg, self.tuning, self.state, self.raw, self.mapping)
        cfg.network.control_area_beta_seconds = 300.
        follower = controller.nash_solver
        prior_margin = follower.offset_keep_margin
        records = []
        def endpoint(state, control, forecast, schedule, spec):
            if endpoint_error:
                raise ValueError("fixture endpoint failure")
            active = bool(control.offsets.get("SC1004"))
            j, ttt = (on_j, 55.) if active else (off_j, 50.)
            records.append((active, spec.split_ttt, spec.score_mode))
            return SimpleNamespace(objective=j, ttt=ttt, freeway_ttt=41. if active else 40., urban_ttt=60.,
                                   control_area={"ttt_veh_h": ttt, "ttd_veh": (ttt-j)*12., "near_score_veh_h": j,
                                                 "additional_cost_veh_h": 0.})
        def followers(state, demand, previous, leader, forecast):
            control = ControlAction.uncontrolled(cfg)
            control.offsets["SC1004"] = 10.
            ttt_on = follower._rollout_horizon_ttt(state, control, forecast)[0]
            zero_control = control.copy()
            zero_control.offsets = {s: 0. for s in control.offsets}
            ttt_off = follower._rollout_horizon_ttt(state, zero_control, forecast)[0]
            namespace = dict(self=follower, control=control, zero_control=zero_control,
                             ttt_on=ttt_on, ttt_off=ttt_off, offsets_kept=1)
            exec(GUARD, namespace)
            control.diagnostics.update(wu_faithful_offset_ttt_on=ttt_on, wu_faithful_offset_ttt_off=ttt_off)
            return control, 1, True, 0., 1
        with mock.patch.object(WuFaithfulFollower, "_rollout_horizon_ttt", BASE_ROLLOUT), mock.patch.object(WuFaithfulFollower, "solve", BASE_SOLVE):
            installed = proposed.install_controller(controller)
            wrapped = WuFaithfulFollower.solve
            proposed.install_controller(controller)
            self.assertIs(WuFaithfulFollower.solve, wrapped)
            with mock.patch.object(rollout_endpoint, "evaluate_price_point", endpoint), mock.patch.object(follower, "_solve_followers", followers):
                if endpoint_error:
                    with self.assertRaisesRegex(ValueError, "fixture endpoint failure"):
                        follower.solve(self.state, None, [object()])
                    result = None
                else:
                    result = follower.solve(self.state, None, [object()])
            self.assertEqual(follower.offset_keep_margin, prior_margin)
            self.assertFalse(hasattr(follower, "_control_area_follower_events"))
            self.assertEqual(cfg.mpc.stackelberg_fallback_guard_use_rollout_ttt, not area)
            cfg.network.control_area_enabled = False
            proposed.install_runtime(cfg)
            self.assertTrue(cfg.mpc.stackelberg_fallback_guard_use_rollout_ttt)
        return result, records

    def test_area_better_j_kept_even_when_global_ttt_worse_and_reward_once(self):
        result, records = self.exercise(True)
        self.assertEqual(result.control.offsets["SC1004"], 10.)
        self.assertEqual(result.objective_value, -30.)
        d = result.diagnostics
        self.assertEqual(d["distributed_response_rollout_ttt"], 101.)
        self.assertEqual(d["wu_faithful_offset_ttt_on"], 101.)
        self.assertEqual(d["control_area_offset_on_objective_veh_h"], -30.)
        self.assertEqual(d["control_area_follower_ttt_veh_h"], 55.)
        self.assertEqual(d["control_area_follower_ttd_veh"], 1020.)
        self.assertEqual(result.control.diagnostics, result.diagnostics)
        self.assertEqual(records, [(True, True, "raw"), (False, True, "raw"), (True, True, "raw")])

    def test_tie_and_worse_negative_j_return_zero(self):
        for on, off in [(-10., -10.), (-9.9, -10.), (-100., -100.1)]:
            with self.subTest(on=on, off=off):
                result, _ = self.exercise(True, on, off)
                self.assertEqual(result.control.offsets["SC1004"], 0.)
                self.assertEqual(result.objective_value, off)
                self.assertGreater(result.diagnostics["distributed_response_rollout_ttt"], 0.)

    def test_off_retains_global_ttt_veto_and_legacy_metadata(self):
        result, _ = self.exercise(False)
        self.assertEqual(result.control.offsets["SC1004"], 0.)
        self.assertEqual(result.objective_value, 100.)
        self.assertEqual(result.diagnostics["wu_faithful_offset_ttt_on"], 101.)
        self.assertFalse(any(k.startswith("control_area_") for k in result.diagnostics))

    def test_exception_restores_solver_scope(self):
        self.exercise(True, endpoint_error=True)

    def test_actual_fallback_negative_j_and_severe_constraints(self):
        cfg = copy.deepcopy(self.cfg)
        controller = adapter.build_priced_wu_link_controller(cfg, self.tuning)
        cfg.network.control_area_enabled = True
        configure_actual_meter_context(cfg, self.tuning, self.state, self.raw, self.mapping)
        with mock.patch.object(WuFaithfulFollower, "_rollout_horizon_ttt", BASE_ROLLOUT), mock.patch.object(WuFaithfulFollower, "solve", BASE_SOLVE):
            proposed.install_controller(controller)
            def item(score, ttt, terminal=10., completed=100.):
                control = ControlAction.uncontrolled(cfg)
                control.diagnostics.update(distributed_response_rollout_ttt=ttt,
                                           distributed_response_terminal_proxy_vehicles=terminal,
                                           distributed_response_mainline_exit_veh=completed)
                return SimpleNamespace(objective=score, nash=SimpleNamespace(control=control, diagnostics={}), rollout_used=True)
            fallback = item(-100.1, 100.)
            for score, ttt, terminal, completed, expected in [(-120., 200., 10., 100., False),
                                                             (-100., 50., 10., 100., True),
                                                             (-100.1, 50., 10., 100., True),
                                                             (-120., 50., 200., 100., True),
                                                             (-120., 50., 10., 50., True)]:
                rejected, diagnostics = controller._fallback_guard_rejects(item(score, ttt, terminal, completed), fallback)
                self.assertEqual(rejected, expected)
                self.assertEqual(diagnostics["leader_fallback_guard_metric_ttt"], 0.)


if __name__ == "__main__":
    unittest.main()
