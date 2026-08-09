# v3 N3-3 - 실런의 링크 저장용량이 전부 실측이고 기본값 fallback 이 0 건임을 고정한다
"""`urban_link_storage_veh` 가 29/29 실측으로 덮이는지 검사한다.

측정값이 없는 링크는 조용히 사라지지 않는다. `NetworkConfig.__post_init__` 이
`setdefault(link, grid_link_storage_veh)` 로 **220.0 veh 를 대신 넣는다**
(`vendor/NumSim-mine/src/models/state.py:247,324`). 예외도 경고도 없다.

실측 산식은 calibration 의 `urban_link_storage_capacity_source` 에 있다 —
`storage_veh = 유효길이_m × 차로수 / 6.49`. 신호 접근로는 정지선 위치를, 경계 유출
링크와 비통제 노드로 끝나는 링크는 전체 길이를 쓴다.

그래서 커버리지가 깨지면 실런이 실제 도로 길이가 아니라 220.0 이라는 격자 기본값으로
돌아간다. N3-3 의 "production fallback 0" 이 이것이다.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from evaluation.controllers import vissim_stackelberg_adapter as adapter


REPO = Path(__file__).resolve().parents[1]
VENDOR = REPO / "vendor" / "NumSim-mine"
if str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

from src.models.state import ExperimentConfig  # noqa: E402


CALIBRATION = (
    REPO / "evaluation/calibration/vissim_network_calibration_v2_8seg_20260714.json"
)
NUMSIM_DEFAULT_CONFIG = VENDOR / "src/config/default.yaml"
GRID_DEFAULT_VEH = 220.0


class UrbanStorageCapacityCoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
        self.overrides = adapter.calibration_to_config_overrides(self.calibration)
        self.measured = dict(self.overrides["network"]["urban_link_storage_veh"])
        self.links = set(
            ExperimentConfig.from_file(
                str(NUMSIM_DEFAULT_CONFIG)
            ).network.urban_link_storage_veh
        )

    def test_every_urban_link_has_a_measured_storage_capacity(self) -> None:
        missing = sorted(self.links - set(self.measured))
        self.assertEqual(missing, [], f"실측 없는 링크가 220.0 으로 대체된다: {missing}")

    def test_measured_capacities_are_not_the_grid_default(self) -> None:
        """실측이 있어도 값이 전부 220.0 이면 실측한 척만 하는 것이다."""
        values = [self.measured[link] for link in sorted(self.links)]
        self.assertTrue(values)
        self.assertNotEqual(
            {GRID_DEFAULT_VEH}, set(values), "모든 링크가 격자 기본값과 같다"
        )
        self.assertGreater(min(values), 0.0)

    def test_a_dropped_measurement_silently_becomes_the_grid_default(self) -> None:
        """음성 대조 — 커버리지가 깨졌을 때 무슨 일이 나는지 실제로 보여 준다.

        이 테스트가 없으면 위 두 테스트는 "원래 통과하는 검사" 와 구별되지 않는다.
        """
        victim = sorted(self.links)[0]
        broken = dict(self.measured)
        original = broken.pop(victim)
        self.assertNotAlmostEqual(original, GRID_DEFAULT_VEH, places=6)

        cfg = ExperimentConfig.from_file(
            str(NUMSIM_DEFAULT_CONFIG),
            overrides={"network": {"urban_link_storage_veh": broken}},
        )
        # 조용히 격자 기본값으로 채워진다. 예외도 경고도 없다.
        self.assertAlmostEqual(
            cfg.network.urban_link_storage_veh[victim], GRID_DEFAULT_VEH, places=6
        )


if __name__ == "__main__":
    unittest.main()
