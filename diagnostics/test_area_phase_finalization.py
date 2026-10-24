"""Actual base/Link solve and canonical refinement; bounded endpoint fixtures."""
from __future__ import annotations
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/NumSim-mine")]
from diagnostics.test_area_follower_objective import BASE_ROLLOUT, BASE_SOLVE, GUARD, configure_actual_meter_context
from diagnostics.probe_signal_feasibility import setup
from evaluation.controllers import vissim_stackelberg_adapter as adapter, signal_actuation_contract as contract
from src.controllers.priced_wu_link_controller import LinkAgentWuFollower
from src.controllers.wu_faithful_follower import WuFaithfulFollower
from src.controllers import rollout_endpoint
from src.models.state import ControlAction

from evaluation.controllers import area_follower_objective as proposed
LINK_SOLVE = LinkAgentWuFollower.solve


class FinalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg, cls.state, _, cls.tuning, cls.raw, cls.mapping, _ = setup()

    def exercise(self, *, area=True, gne=False, endpoint_error=False, authoritative=False, second_solve=False):
        cfg = copy.deepcopy(self.cfg)
        tuning = copy.deepcopy(self.tuning)
        tuning["urban"]["physical_signal_contract"] = True
        tuning["actuation"]["real_world_signal_control"]["offset_writer"] = "test_only"
        contract.configure(cfg, tuning, adapter.load_signal_group_actuation_plan())
        controller = adapter.build_priced_wu_link_controller(cfg, tuning)
        follower = controller.nash_solver
        cfg.network.control_area_enabled = area
        configure_actual_meter_context(cfg, tuning, self.state, self.raw, self.mapping)
        follower.signal_phase_price = {"SC1004": {"p1": -1., "p2": 0., "p3": 0., "p4": 0.}}
        follower.signal_phase_price_ref = None
        follower.phase_price_in_gne = gne
        follower.phase_price_local_cost_model = "drain"
        follower.phase_price_refine_rounds = 2
        refine_calls, points, results = [], [], []
        current_refine = LinkAgentWuFollower.apply_phase_price_refinement

        def real_refine(self, control, state, demand=None):
            refine_calls.append(dict(control.green_times))
            return current_refine(self, control, state, demand)

        def endpoint(state, control, forecast, schedule, objective_spec):
            if endpoint_error:
                raise ValueError("fixture endpoint failure")
            active = bool(control.offsets["SC1004"])
            high = control.green_times["SC1004_p1"] > 35.
            j = (-30. if active else -10.) if high else (-1. if active else -2.)
            points.append((dict(control.green_times), active, j))
            return SimpleNamespace(objective=j, ttt=50., freeway_ttt=40., urban_ttt=60.,
                                   control_area={"ttt_veh_h": 50., "ttd_veh": (50.-j)*12.,
                                                 "near_score_veh_h": j, "additional_cost_veh_h": 0.})

        def followers(state, demand, previous, leader, forecast):
            control = contract.prepare_control(ControlAction.uncontrolled(cfg), cfg)
            vector = contract.project_vector(cfg.network, "SC1004", {"p1": 30., "p2": 24.968, "p3": 58.064, "p4": 24.968})
            for key, value in vector.items():
                control.green_times["SC1004_" + key] = value
            control.offsets["SC1004"] = 10.
            if gne:
                follower._gne_phase_override = {"SC1004": {"p1": 40., "p2": 24.968, "p3": 48.064, "p4": 24.968}}
            if not authoritative:
                ttt_on = follower._rollout_horizon_ttt(state, control, forecast)[0]
                zero_control = control.copy()
                zero_control.offsets = {signal: 0. for signal in control.offsets}
                ttt_off = follower._rollout_horizon_ttt(state, zero_control, forecast)[0]
                namespace = dict(self=follower, control=control, zero_control=zero_control, ttt_on=ttt_on, ttt_off=ttt_off, offsets_kept=1)
                exec(GUARD, namespace)
                control.diagnostics.update(wu_faithful_offset_ttt_on=ttt_on, wu_faithful_offset_ttt_off=ttt_off)
            return control, 1, True, 0., 1

        with mock.patch.object(WuFaithfulFollower, "_rollout_horizon_ttt", BASE_ROLLOUT), mock.patch.object(WuFaithfulFollower, "solve", BASE_SOLVE), mock.patch.object(LinkAgentWuFollower, "solve", LINK_SOLVE), mock.patch.object(LinkAgentWuFollower, "apply_phase_price_refinement", real_refine):
            proposed.install_controller(controller)
            wrapped = LinkAgentWuFollower.solve
            proposed.install_controller(controller)
            self.assertIs(LinkAgentWuFollower.solve, wrapped)
            with mock.patch.object(rollout_endpoint, "evaluate_price_point", endpoint), mock.patch.object(follower, "_solve_followers", followers), mock.patch.object(follower, "phase_shape_local_cost", return_value=0.):
                if endpoint_error:
                    with self.assertRaisesRegex(ValueError, "fixture endpoint failure"):
                        follower.solve(self.state, None, [object()])
                else:
                    results.append(follower.solve(self.state, None, [object()]))
                    if second_solve:
                        results.append(follower.solve(self.state, None, [object()], results[-1].control))
            self.assertFalse(hasattr(follower, "_control_area_link_phase_context"))
            self.assertFalse(hasattr(follower, "_control_area_follower_events"))
        return results, refine_calls, points

    def test_real_refinement_before_guard_changes_offset_choice_and_outer_is_idempotent(self):
        results, calls, points = self.exercise()
        result = results[0]
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(points), 3)
        self.assertTrue(all(point[0] == result.control.green_times for point in points))
        self.assertGreater(result.control.green_times["SC1004_p1"], 35.)
        self.assertEqual(result.control.offsets["SC1004"], 10.)
        self.assertEqual(result.objective_value, -30.)
        self.assertEqual(result.diagnostics["control_area_offset_on_objective_veh_h"], -30.)
        self.assertEqual(result.diagnostics["control_area_offset_off_objective_veh_h"], -10.)
        self.assertEqual(result.diagnostics["control_area_phase_outer_matches_scored"], 1.)
        self.assertEqual(result.diagnostics["control_area_phase_finalization_source"], "phase_refinement")

    def test_off_preserves_old_order_and_stale_score_without_new_metadata(self):
        results, calls, points = self.exercise(area=False)
        self.assertEqual(len(calls), 1)
        self.assertNotEqual(points[-1][0], results[0].control.green_times)
        self.assertEqual(results[0].objective_value, 100.)
        self.assertFalse(any(key.startswith("control_area_") for key in results[0].diagnostics))

    def test_pending_gne_commit_is_scored_before_guard_without_refinement(self):
        results, calls, points = self.exercise(gne=True)
        self.assertEqual(len(calls), 0)
        self.assertTrue(all(point[0] == results[0].control.green_times for point in points))
        self.assertEqual(results[0].control.green_times["SC1004_p1"], 40.)
        self.assertEqual(results[0].diagnostics["control_area_phase_finalization_source"], "gne_commit")

    def test_no_guard_path_finalizes_once_without_fabricated_guard(self):
        results, calls, points = self.exercise(authoritative=True)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(points), 1)
        self.assertEqual(results[0].diagnostics["control_area_offset_guard_evaluated"], 0.)

    def test_second_solve_and_exception_restore_scope(self):
        results, calls, points = self.exercise(second_solve=True)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(results), 2)
        self.assertEqual(len(points), 6)
        self.exercise(endpoint_error=True)


if __name__ == "__main__":
    unittest.main()
