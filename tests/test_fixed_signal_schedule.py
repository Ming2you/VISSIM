from __future__ import annotations

import json
import unittest
from pathlib import Path

from evaluation.controllers.fixed_signal_schedule import (
    compile_fixed_signal_schedules,
    movement_phase,
)


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
NETWORK = WORKSPACE_ROOT / "network" / "real_world_gaepo_modi" / "modi_eval_rw_control.inpx"
DETECTOR_MAPPING = WORKSPACE_ROOT / "evaluation" / "real_world_modi_control_distributed_20260728" / "detector_local_mapping_distributed_core15n41_20260805.json"
TUNING = WORKSPACE_ROOT / "evaluation" / "configs" / "real_world_modi_pstack_distributed_core15n41_20260805.json"
MONITOR_NODES = {
    "SC2", "SC3", "SC4", "SC7", "SC8", "SC9", "SC10", "SC13", "SC14",
    "SC15", "SC16", "SC17", "SC18", "SC19", "SC102", "SC103", "SC104",
    "SC106", "SC2001", "SC2002", "SC2003", "SC2004", "SC2005", "SC9001",
    "SC9002", "SC9003",
}


class FixedSignalScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.detector_mapping = json.loads(DETECTOR_MAPPING.read_text(encoding="utf-8"))
        cls.tuning = json.loads(TUNING.read_text(encoding="utf-8"))
        cls.schedules, cls.errors = compile_fixed_signal_schedules(
            NETWORK, MONITOR_NODES, cls.detector_mapping
        )

    def test_every_monitor_node_has_a_valid_schedule(self) -> None:
        self.assertEqual(self.errors, {})
        self.assertEqual(set(self.schedules), MONITOR_NODES)

    def test_monitor_green_fraction_is_not_always_green(self) -> None:
        for node, schedule in self.schedules.items():
            fractions = []
            for phase in schedule.phase_signal_groups:
                fraction = schedule.green_fraction(phase)
                fractions.append(fraction)
                self.assertLess(fraction, 1.0, (node, phase))
            self.assertTrue(any(value > 0.0 for value in fractions), node)

    def test_substep_green_fraction_integrates_to_cycle_average(self) -> None:
        schedule = self.schedules["SC2"]
        for phase in schedule.phase_signal_groups:
            cycle = schedule.program.cycle_length_sec
            integral = sum(
                schedule.green_fraction(phase, second, 1.0)
                for second in range(int(cycle))
            )
            self.assertAlmostEqual(integral / cycle, schedule.green_fraction(phase), places=9)

    def test_movement_axis_matches_current_rotated_grid_rule(self) -> None:
        self.assertEqual(movement_phase({"approach": "NW_SC1"}, {"p1", "p2"}), "p1")
        self.assertEqual(movement_phase({"approach": "E_SC1"}, {"p1", "p2"}), "p2")
        self.assertEqual(movement_phase({"approach": "N"}, {"p2"}), "p2")

    def test_same_axis_groups_use_green_union(self) -> None:
        self.assertAlmostEqual(self.schedules["SC104"].green_fraction("p2"), 0.5, places=9)

    def test_generated_monitor_movements_have_physical_green(self) -> None:
        movements = self.tuning["config_overrides"]["network"]["urban_movements"].values()
        for spec in movements:
            node = str(spec.get("intersection", ""))
            if node in MONITOR_NODES:
                self.assertGreater(
                    self.schedules[node].movement_green_fraction(spec),
                    0.0,
                    (node, spec.get("approach"), spec.get("origin")),
                )

    def test_absolute_step_time_does_not_add_anchor_twice(self) -> None:
        from evaluation.controllers.vissim_stackelberg_adapter import (
            _absolute_urban_step_start_sec,
        )

        self.assertEqual(_absolute_urban_step_start_sec(90, 10.0), 900.0)


if __name__ == "__main__":
    unittest.main()
