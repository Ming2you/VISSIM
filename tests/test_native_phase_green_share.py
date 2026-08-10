# v3 N4-3 - 제어 movement 가 실 .sig 의 native 녹색배분을 쓰는지, N=2 에서 비트동일한지 고정한다
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
NETWORK = WORKSPACE_ROOT / "network" / "real_world_gaepo_modi" / "modi_eval_rw_control.inpx"
DETECTOR_MAPPING = (
    WORKSPACE_ROOT
    / "evaluation"
    / "real_world_modi_control_distributed_20260728"
    / "detector_local_mapping_distributed_core15n41_20260805.json"
)
TUNING = (
    WORKSPACE_ROOT
    / "evaluation"
    / "configs"
    / "real_world_modi_pstack_distributed_core15n41_20260805.json"
)
VENDOR_NUMSIM = WORKSPACE_ROOT / "vendor" / "NumSim-mine"

# outputs/signal_group_timing_v3.json 의 SC1001(150 s, SG 8개) 실측이다.
# 브리핑에 적힌 .193/.267 은 반올림 표기이므로 녹색창에서 나오는 정확한 유리수를 쓴다
# (NBL 118-147 s = 29 s, SBT 75-115 s = 40 s).
SC1001_MEASURED_GREEN_FRACTION = {
    "WBL": 24.0 / 150.0,
    "EBT": 45.0 / 150.0,
    "NBL": 29.0 / 150.0,
    "SBT": 40.0 / 150.0,
    "EBL": 24.0 / 150.0,
    "WBT": 45.0 / 150.0,
    "SBL": 18.0 / 150.0,
    "NBT": 51.0 / 150.0,
}

# 2현시 합성 프로그램. 주기 120 s, major(EBT/WBT) 녹색창이 서로 완전히 같고
# minor(NBT/SBT) 도 서로 완전히 같다 - 이것이 "N=2" 의 정의다.
TWO_PHASE_SIG = """<?xml version="1.0" encoding="UTF-8"?>
<sc version="201602" id="900" name="two-phase">
  <signaldisplays>
    <display id="1" name="Red" state="RED" />
    <display id="3" name="Green" state="GREEN" />
    <display id="4" name="Amber" state="AMBER" />
  </signaldisplays>
  <signalsequences>
    <signalsequence id="7" name="Red-Green-Amber">
      <state display="1" isFixedDuration="false" defaultDuration="1000" />
      <state display="3" isFixedDuration="false" defaultDuration="5000" />
      <state display="4" isFixedDuration="true" defaultDuration="3000" />
    </signalsequence>
  </signalsequences>
  <sgs>
    <sg id="1" name="EBT" defaultSignalSequence="7" />
    <sg id="2" name="WBT" defaultSignalSequence="7" />
    <sg id="3" name="NBT" defaultSignalSequence="7" />
    <sg id="4" name="SBT" defaultSignalSequence="7" />
  </sgs>
  <progs>
    <prog id="1" cycletime="120000" switchpoint="0" offset="0" name="two-phase">
      <sgs>
        <sg sg_id="1" signal_sequence="7">
          <cmds><cmd display="3" begin="0" /><cmd display="1" begin="60000" /></cmds>
          <fixedstates><fixedstate display="4" duration="3000" /></fixedstates>
        </sg>
        <sg sg_id="2" signal_sequence="7">
          <cmds><cmd display="3" begin="0" /><cmd display="1" begin="60000" /></cmds>
          <fixedstates><fixedstate display="4" duration="3000" /></fixedstates>
        </sg>
        <sg sg_id="3" signal_sequence="7">
          <cmds><cmd display="1" begin="0" /><cmd display="3" begin="60000" /></cmds>
          <fixedstates><fixedstate display="4" duration="3000" /></fixedstates>
        </sg>
        <sg sg_id="4" signal_sequence="7">
          <cmds><cmd display="1" begin="0" /><cmd display="3" begin="60000" /></cmds>
          <fixedstates><fixedstate display="4" duration="3000" /></fixedstates>
        </sg>
      </sgs>
    </prog>
  </progs>
</sc>
"""


def _vendor_phase_green_fraction():
    """실제 상류 `_phase_green_fraction` 을 그대로 쓴다 - 재구현하면 비교가 무의미하다."""
    if str(VENDOR_NUMSIM) not in sys.path:
        sys.path.insert(0, str(VENDOR_NUMSIM))
    from src.models.urban_queue_model import _phase_green_fraction

    return _phase_green_fraction


def _vendor_experiment_config():
    if str(VENDOR_NUMSIM) not in sys.path:
        sys.path.insert(0, str(VENDOR_NUMSIM))
    from src.models.state import ExperimentConfig

    return ExperimentConfig()


class NativeSignalGroupFractionTests(unittest.TestCase):
    """N4-3 요구 3 - SC1001 8개 SG 분율이 실측과 1e-9 이내로 맞아야 한다."""

    def test_sc1001_signal_group_green_fractions_match_measurement(self) -> None:
        from evaluation.controllers.fixed_signal_schedule import (
            compile_fixed_signal_schedules,
        )
        from evaluation.controllers.native_phase_green import (
            signal_group_green_fractions,
        )

        schedules, errors = compile_fixed_signal_schedules(NETWORK, {"SC1001"}, {})
        self.assertEqual(errors, {})
        program = schedules["SC1001"].program
        self.assertEqual(program.cycle_length_sec, 150.0)

        fractions = signal_group_green_fractions(program)
        by_name = {
            program.sg_timelines[sg_id].name: value
            for sg_id, value in fractions.items()
        }
        self.assertEqual(set(by_name), set(SC1001_MEASURED_GREEN_FRACTION))
        for name, expected in SC1001_MEASURED_GREEN_FRACTION.items():
            self.assertLess(abs(by_name[name] - expected), 1.0e-9, name)
        # 브리핑에 적힌 반올림 표기와도 어긋나지 않는지 함께 본다.
        self.assertAlmostEqual(by_name["NBL"], 0.193, places=3)
        self.assertAlmostEqual(by_name["SBT"], 0.267, places=3)


class TwoPhaseBitIdenticalTests(unittest.TestCase):
    """N4-3 요구 2 - N=2 에서 기존 경로와 비트동일해야 한다."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.sig_path = Path(cls._tmp.name) / "two_phase.sig"
        cls.sig_path.write_text(TWO_PHASE_SIG, encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _two_phase_schedule(self):
        from plant.src.vissim_strict.signal_program import parse_sig
        from evaluation.controllers.fixed_signal_schedule import FixedControllerSchedule

        program = parse_sig(self.sig_path, 1)
        return FixedControllerSchedule(
            node_id="SC900",
            program=program,
            controller_offset_sec=0.0,
            phase_signal_groups={"p2": ("1", "2"), "p1": ("3", "4")},
            origin_signal_groups={
                "east_in": ("1",),
                "west_in": ("2",),
                "north_in": ("3",),
                "both_major_in": ("1", "2"),
            },
            approach_signal_groups={"E": ("1",), "W": ("2",), "N": ("3",)},
        )

    def test_two_phase_program_produces_only_unit_shares(self) -> None:
        from evaluation.controllers.native_phase_green import (
            build_native_phase_share_table,
        )

        movements = {
            "m_east": {
                "intersection": "SC900",
                "phase": "SC900_p2",
                "origin": "east_in",
                "approach": "E_SC901",
            },
            "m_both": {
                "intersection": "SC900",
                "phase": "SC900_p2",
                "origin": "both_major_in",
                "approach": "E_SC901",
            },
            "m_north": {
                "intersection": "SC900",
                "phase": "SC900_p1",
                "origin": "north_in",
                "approach": "N_SC902",
            },
        }
        table = build_native_phase_share_table(movements, {"SC900": self._two_phase_schedule()})

        self.assertEqual(dict(table.shares), {})
        self.assertEqual(dict(table.unresolved), {})
        self.assertEqual(set(table.unit_share_movements), set(movements))
        for spec in movements.values():
            self.assertIsNone(table.share_for(spec))

    def test_unit_share_path_is_bit_identical_to_original(self) -> None:
        from evaluation.controllers.native_phase_green import (
            build_native_phase_share_table,
        )
        from evaluation.controllers import vissim_stackelberg_adapter as adapter

        original = _vendor_phase_green_fraction()
        cfg = _vendor_experiment_config()
        table = build_native_phase_share_table({}, {})
        patched = adapter.build_patched_phase_green_fraction(original, {}, table)

        spec_p1 = {
            "intersection": "SC900",
            "phase": "SC900_p1",
            "origin": "north_in",
            "approach": "N_SC902",
        }
        spec_p2 = dict(spec_p1, phase="SC900_p2", origin="east_in", approach="E_SC901")

        compared = 0
        for g1 in (0.0, 12.5, 40.0, 57.0, 92.0):
            for g2 in (0.0, 20.0, 57.0, 91.5):
                for offset in (0.0, 7.5, 33.0, 60.0, 119.5):
                    control = SimpleNamespace(
                        green_times={"SC900_p1": g1, "SC900_p2": g2},
                        offsets={"SC900": offset},
                    )
                    for index in (None, 0, 1, 7, 12, 23, 24, 1000):
                        for spec in (spec_p1, spec_p2):
                            self.assertEqual(
                                patched(control, cfg, spec, index),
                                original(control, cfg, spec, index),
                                (g1, g2, offset, index, spec["phase"]),
                            )
                            compared += 1
        self.assertEqual(compared, 5 * 4 * 5 * 8 * 2)


class ControlledMovementNativeShareTests(unittest.TestCase):
    """N4-3 요구 1/4 - 제어 movement 가 native 배분을 쓰고, 미해결은 계상된다."""

    @classmethod
    def setUpClass(cls) -> None:
        from evaluation.controllers.fixed_signal_schedule import (
            compile_fixed_signal_schedules,
        )

        cls.detector_mapping = json.loads(DETECTOR_MAPPING.read_text(encoding="utf-8"))
        cls.tuning = json.loads(TUNING.read_text(encoding="utf-8"))
        cls.network_cfg = cls.tuning["config_overrides"]["network"]
        cls.signals = set(cls.network_cfg["signals"])
        cls.schedules, cls.errors = compile_fixed_signal_schedules(
            NETWORK, cls.signals, cls.detector_mapping
        )

    def test_every_controlled_signal_compiles(self) -> None:
        self.assertEqual(self.errors, {})
        self.assertEqual(set(self.schedules), self.signals)

    def test_sc1001_through_movement_gets_its_native_window_share(self) -> None:
        from evaluation.controllers.native_phase_green import (
            build_native_phase_share_table,
        )

        # SC1002_to_SC1001 는 WBT(SG 6, 0-45 s) 하나만 잡는다. 같은 축(major)의 native
        # 녹색 합집합은 EBT/WBT [0,45) 와 WBL/EBL [48,72) 로 45+24 = 69 s 다.
        spec = {
            "intersection": "SC1001",
            "phase": "SC1001_p2",
            "origin": "SC1002_to_SC1001",
            "approach": "E_SC1002",
        }
        table = build_native_phase_share_table({"m": spec}, self.schedules)
        self.assertAlmostEqual(table.share_for(spec), 45.0 / 69.0, places=12)

    def test_sc1001_multi_group_origin_keeps_full_axis_share(self) -> None:
        from evaluation.controllers.native_phase_green import (
            build_native_phase_share_table,
        )

        # SC1004_to_SC1001 는 EBT(2)+EBL(5) 를 잡아 축 녹색 전체를 덮는다 -> 배분 1.0.
        spec = {
            "intersection": "SC1001",
            "phase": "SC1001_p2",
            "origin": "SC1004_to_SC1001",
            "approach": "W_SC1004",
        }
        table = build_native_phase_share_table({"m": spec}, self.schedules)
        self.assertIsNone(table.share_for(spec))
        self.assertEqual(table.unit_share_movements, ("m",))

    def test_real_config_shares_are_bounded_and_actually_reduce_green(self) -> None:
        from evaluation.controllers.native_phase_green import (
            build_native_phase_share_table,
        )

        table = build_native_phase_share_table(
            self.network_cfg["urban_movements"], self.schedules
        )
        values = list(table.shares.values())
        self.assertTrue(values)
        self.assertGreater(min(values), 0.0)
        self.assertLess(max(values), 1.0)
        # 되돌림 증명 - 배선을 빼면(=전부 1.0) 이 단언이 깨진다.
        self.assertLess(min(values), 0.5)

    def test_unresolved_controlled_movements_are_counted_not_defaulted(self) -> None:
        from evaluation.controllers.native_phase_green import (
            build_native_phase_share_table,
        )

        movements = self.network_cfg["urban_movements"]
        phase_movements = [
            name for name, spec in movements.items() if str(spec.get("phase", ""))
        ]
        table = build_native_phase_share_table(movements, self.schedules)

        # `shares` 는 (intersection, phase, origin, approach) 로 키를 잡으므로 exit 만
        # 다른 movement 들이 한 항목으로 합쳐진다. 총계는 movement 목록으로 센다.
        self.assertEqual(
            len(table.scaled_movements)
            + len(table.unit_share_movements)
            + len(table.unresolved),
            len(phase_movements),
        )
        self.assertLess(len(table.shares), len(table.scaled_movements))
        self.assertGreater(len(table.unresolved), 0)
        for name, reason in table.unresolved.items():
            self.assertIn(
                reason,
                {"no_schedule", "no_signal_group_mapping", "axis_mismatch", "no_axis_green"},
                name,
            )
        diagnostics = table.diagnostics
        self.assertEqual(
            diagnostics["native_phase_share_unresolved_count"],
            float(len(table.unresolved)),
        )
        self.assertEqual(
            diagnostics["native_phase_share_movement_count"], float(len(phase_movements))
        )
        self.assertGreater(
            diagnostics["native_phase_share_unresolved_reasons"]["no_signal_group_mapping"],
            0,
        )

    def test_patched_path_applies_the_native_share_to_a_controlled_movement(self) -> None:
        """배선 자체를 고정한다 - 어댑터가 배분을 곱하지 않으면 여기서 깨진다."""
        from evaluation.controllers.native_phase_green import (
            build_native_phase_share_table,
        )
        from evaluation.controllers import vissim_stackelberg_adapter as adapter

        original = _vendor_phase_green_fraction()
        cfg = _vendor_experiment_config()
        spec = {
            "intersection": "SC1001",
            "phase": "SC1001_p2",
            "origin": "SC1002_to_SC1001",
            "approach": "E_SC1002",
        }
        table = build_native_phase_share_table({"m": spec}, self.schedules)
        patched = adapter.build_patched_phase_green_fraction(original, {}, table)
        control = SimpleNamespace(
            green_times={"SC1001_p1": 40.0, "SC1001_p2": 50.0},
            offsets={"SC1001": 0.0},
        )
        # p2 녹색창은 [g1+lost/2, +g2) = [44, 94) s 이고 T_u=5 s 다. 겹치는 substep 만 고른다.
        for index in (None, 9, 12, 17):
            base = original(control, cfg, spec, index)
            self.assertGreater(base, 0.0, index)
            self.assertEqual(
                patched(control, cfg, spec, index), base * (45.0 / 69.0), index
            )
            self.assertNotEqual(patched(control, cfg, spec, index), base, index)

    def test_unresolved_movements_do_not_get_a_silent_share(self) -> None:
        from evaluation.controllers.native_phase_green import (
            build_native_phase_share_table,
        )

        spec = {
            "intersection": "SC1001",
            "phase": "SC1001_p2",
            "origin": "__no_such_origin__",
            "approach": "__no_such_leg__",
        }
        table = build_native_phase_share_table({"m": spec}, self.schedules)
        self.assertIsNone(table.share_for(spec))
        self.assertEqual(dict(table.unresolved), {"m": "no_signal_group_mapping"})
        self.assertEqual(table.unit_share_movements, ())


if __name__ == "__main__":
    unittest.main()
