"""Source-only exact native clock checks; no model endpoint or COM calls."""
from __future__ import annotations

import copy
from dataclasses import replace
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plant" / "src"))
from vissim_strict.signal_program import parse_sig
from evaluation.controllers import signal_group_plan as plans


class NativeClockPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = json.loads((ROOT / "outputs/signal_group_actuation_plan_mainline_20260825.json").read_text(encoding="utf-8"))
        audit = json.loads((ROOT / "reports/20260911_decision_runtime/current_native_anchor_source_audit.json").read_text(encoding="utf-8"))
        cls.cases = {}
        for row in audit["controllers"]:
            plan = plans.node_plan_from_json(raw["controllers"][row["sc"]])
            program = parse_sig(ROOT / row["program"], 1)
            basis = plans.build_native_clock_basis(plan, program, amber_sec=3.0, all_red_sec=0.0)
            cls.cases[row["sc"]] = (replace(plan, native_clock_basis=basis), program)

    def test_all_source_green_amber_red_and_first_states(self):
        self.assertEqual(len(self.cases), 17)
        count = 0
        for sc, (plan, program) in self.cases.items():
            greens = plan.axis_green_sec
            basis = plan.native_clock_basis
            cycle = plans.node_cycle_sec(plan, greens, 3.0, 0.0)
            self.assertEqual(cycle, program.cycle_length_sec)
            groups = sorted({sg for ids in plan.phase_signal_groups.values() for sg in ids})
            # Includes actual simulation time zero, exact boundaries and midpoints.
            for t in [step / 2 for step in range(int(2 * cycle))]:
                phase = (t + basis["reference_offset_sec"]) % cycle
                for sg in groups:
                    actual = plans.plan_state_at(plan, greens, sg, phase, 3.0, 0.0)
                    self.assertEqual(actual, program.state_at(t, sg), (sc, sg, t))
                    count += 1
            windows = plans.plan_windows(plan, greens, plans.MODEL_PHASES, 3.0, 0.0)
            self.assertFalse(plans.conflict_violations(windows, plan.conflict_pairs), sc)
        self.assertGreater(count, 35000)

    def test_sc7_concurrent_amber_and_independent_green(self):
        plan, _ = self.cases["7"]
        self.assertEqual(plan.native_clock_basis["kind"], "concurrent_p1_p2")
        self.assertEqual(plans.native_phase_windows(plan, plan.axis_green_sec, 3.0, 0.0),
                         {"p1": (0.0, 67.0), "p2": (0.0, 90.0), "p4": (93.0, 117.0)})
        self.assertEqual(plans.plan_state_at(plan, plan.axis_green_sec, "4", 68, 3, 0), "AMBER")
        self.assertEqual(plans.plan_state_at(plan, plan.axis_green_sec, "7", 68, 3, 0), "GREEN")
        changed = dict(plan.axis_green_sec, p1=60.0, p2=87.0, p4=27.0)
        self.assertEqual(plans.node_cycle_sec(plan, changed, 3, 0), 120)
        for bad in [dict(changed, p1=85.0), dict(changed, p4=26.0), dict(changed, p3=1.0)]:
            with self.assertRaises(plans.SignalGroupPlanError):
                plans.native_phase_windows(plan, bad, 3, 0)

    def test_sc16_fixed_idle_and_permuted_order(self):
        plan, _ = self.cases["16"]
        self.assertEqual(plan.native_clock_basis["idle_after_phase_sec"]["p3"], 34.0)
        self.assertEqual(plan.native_clock_basis["phase_order"], ["p3", "p2", "p1"])
        self.assertEqual(plans.native_phase_windows(plan, plan.axis_green_sec, 3, 0),
                         {"p3": (0.0, 27.0), "p2": (64.0, 81.0), "p1": (84.0, 147.0)})
        changed = dict(plan.axis_green_sec, p1=60.0, p2=20.0)
        self.assertEqual(plans.node_cycle_sec(plan, changed, 3, 0), 150)
        for sg in ["2", "3", "4", "6", "7", "8"]:
            self.assertEqual(plans.plan_state_at(plan, changed, sg, 40, 3, 0), "RED")
        with self.assertRaises(plans.SignalGroupPlanError):
            plans.native_phase_windows(plan, dict(changed, p1=61), 3, 0)

    def test_round_trip_isolated_and_legacy_absent_path(self):
        for native, _ in self.cases.values():
            encoded = plans.node_plan_to_json(native)
            self.assertEqual(plans.node_plan_to_json(plans.node_plan_from_json(encoded)), encoded)
            encoded["native_clock_basis"]["phase_order"].reverse()
            self.assertNotEqual(encoded["native_clock_basis"], native.native_clock_basis)
            old = replace(native, native_clock_basis=None)
            self.assertNotIn("native_clock_basis", plans.node_plan_to_json(old))
            greens = old.axis_green_sec
            expected, cursor = [], 0.0
            for phase in plans.MODEL_PHASES:
                span = greens.get(phase, 0)
                if span <= 0:
                    continue
                for sg, index, low, high in old.phase_segments[phase]:
                    expected.append(plans.PlanWindow(sg, index, cursor + low * span, cursor + high * span))
                cursor += span + 3.0
            expected.sort(key=lambda row: (int(row.sg_no), row.window_index))
            self.assertEqual(plans.plan_windows(old, greens, plans.MODEL_PHASES, 3, 0), tuple(expected))
            self.assertEqual(plans.node_cycle_sec(old, greens, 3, 0), plans.plan_cycle_sec(greens, 3, 0))

    def test_explicit_basis_rejects_bad_clearance_schema_and_source(self):
        native, program = self.cases["7"]
        with self.assertRaises(plans.SignalGroupPlanError):
            plans.native_phase_windows(native, native.axis_green_sec, 4, 0)
        bad = copy.deepcopy(plans.node_plan_to_json(native))
        bad["native_clock_basis"]["schema_version"] = "unknown"
        with self.assertRaises(plans.SignalGroupPlanError):
            plans.node_plan_from_json(bad)
        with self.assertRaises(plans.SignalGroupPlanError):
            plans.build_native_clock_basis(native, program, amber_sec=2, all_red_sec=0)
        for value in [float("nan"), float("inf"), -1]:
            with self.assertRaises(plans.SignalGroupPlanError):
                plans.native_phase_windows(native, dict(native.axis_green_sec, p1=value), 3, 0)

    def test_controller_offset_preserves_source_clock_sign(self):
        original, program = self.cases["7"]
        basis = plans.build_native_clock_basis(original, program, amber_sec=3, all_red_sec=0,
                                               controller_offset_sec=13)
        self.assertEqual(basis["reference_offset_sec"], 106)
        native = replace(original, native_clock_basis=basis)
        for t in range(120):
            for sg in ["1", "3", "4", "7", "8"]:
                self.assertEqual(plans.plan_state_at(native, native.axis_green_sec, sg,
                                 t + basis["reference_offset_sec"], 3, 0),
                                 program.state_at(t, sg, controller_offset_sec=13))


if __name__ == "__main__":
    unittest.main()
