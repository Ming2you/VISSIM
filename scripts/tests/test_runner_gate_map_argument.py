# 러너가 도시 유입 게이트 맵 경로를 인자로 받는지 고정한다
"""게이트 맵이 하드코딩이면 배선이 계열별로 갈릴 수 없다.

`DefaultUrbanInputGateMapPath()` 는 `urban_input_gate_map_20260811.csv` 를 박아 두고
있었다. 그 맵은 격자 leg 방위에서 유도되므로 leg 을 고치면 같이 움직여야 하는데, 러너가
경로를 바꿀 방법을 안 주면 새 배선으로는 런이 안 돈다. 실제로 이렇게 죽었다.

    ValueError: state.demand.urban_volume_vph_by_gate has gates the model does
                not know: in_SC1001_W

SC1001 의 W 가 격자 leg(W_SC1004)이 되어 경계 게이트가 아니게 됐는데 러너는 옛 맵의
in_SC1001_W 를 계속 넘겼다.

계약 둘.
  - 인자 25 를 주면 그 경로를 쓴다.
  - 안 주면(빈 문자열 포함) 종전 기본값 그대로다 - 기존 런 스크립트가 안 깨진다.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "run_real_world_stackelberg_controller.vbs"
LEGACY_MAP = "urban_input_gate_map_20260811.csv"


class RunnerGateMapArgumentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = RUNNER.read_text(encoding="utf-8", errors="replace")

    def test_the_gate_map_path_is_read_from_an_argument(self) -> None:
        """인자에서 읽어 변수에 담아야 한다. 인덱스 24 까지 이미 쓰고 있으므로 25 다."""
        self.assertRegex(
            self.source,
            r"urbanInputGateMapPath\s*=\s*ArgOrDefaultText\(\s*25\s*,",
            "게이트 맵 경로를 인자 25 에서 읽지 않는다",
        )

    def test_the_loader_is_called_with_that_variable_not_the_hardcoded_default(self) -> None:
        """`LoadInpxDemandSchedule` 호출이 그 변수를 넘겨야 한다.

        기본값 함수를 그대로 넘기면 인자를 읽어도 쓰이지 않는다 - 통과할 수밖에 없는
        검사가 되지 않도록 **호출 지점**을 든다.
        """
        call = re.search(r"LoadInpxDemandSchedule\s+[^\r\n]+", self.source)
        self.assertIsNotNone(call, "LoadInpxDemandSchedule 호출을 못 찾았다")
        self.assertIn("urbanInputGateMapPath", call.group(0))

    def test_an_empty_argument_falls_back_to_the_shipped_map(self) -> None:
        """빈 문자열이면 종전 기본값으로 떨어져야 기존 런 스크립트가 안 깨진다."""
        self.assertRegex(
            self.source,
            r"If\s+urbanInputGateMapPath\s*=\s*\"\"\s*Then\s+urbanInputGateMapPath\s*=\s*"
            r"DefaultUrbanInputGateMapPath\(\)",
            "빈 인자에 대한 폴백이 없다",
        )

    def test_the_shipped_default_is_still_the_legacy_map(self) -> None:
        """되돌림 증명 - 기본값이 이미 새 맵이면 위 검사들은 아무것도 증명하지 않는다.

        기본값을 옮기는 것은 생산 배선을 바꾸는 별개 결정이다. 이 회차는 **인자를 여는
        것**까지이고, 기본값은 그대로 둔다.
        """
        default = re.search(
            r"DefaultUrbanInputGateMapPath\s*=\s*fso\.BuildPath\([^\r\n]+", self.source
        )
        self.assertIsNotNone(default)
        self.assertIn(LEGACY_MAP, default.group(0))


if __name__ == "__main__":
    unittest.main()
