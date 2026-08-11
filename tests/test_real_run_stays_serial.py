# 실 런이 leader/grid 병렬 경로를 타지 않는다는 사실을 못박는다 (N8-3 유예 근거)
"""N8-3 의 병렬 등가성은 아직 검증되지 않았다. 미뤄도 되는 근거가 이 검사다.

## 왜 미룰 수 있나

`stackelberg_mpc._evaluate_candidate_set` 의 직렬 분기는 후보마다 incumbent 를 조이는데
(`:2118-2122`) 병렬 분기는 seed 직후 값으로 고정한다(`:2134`). incumbent 는 조기절단
기준선이므로(`:236`) 같은 후보가 worker 수에 따라 다른 지점에서 잘릴 수 있고, 잘린 후보가
참값 대신 부분값을 보고하면 계획 N8-3 의 `차이 <= 1e-9` 를 위반한다.

**그런데 실 런은 그 경로를 안 탄다.** 어댑터가 하드코딩으로 막는다.

## 왜 검사가 필요한가

NumSim 쪽 `DistributedFollowerWorkerEquivalenceTests` 는 지금 skip 이다 - fixture 의 후보
셋이 같은 목적함수를 내 비대칭을 못 재면서 240 초를 쓴다. 그 자리를 비워 두면 다음 사람이
"병렬 등가성은 검사되고 있다" 고 착각한다.

이 검사는 1 초에 끝나고, **병렬을 켜려는 순간 터진다.** 그때 상류의 skip 을 풀고 후보 6개
이상 fixture 로 다시 만들면 된다.

skip 자체를 여기서 검사하지는 않는다. 그 검사는 상류 NumSim 에 있고 vendor 스냅샷은 다른
주기로 재앵커되므로, 둘을 한 검사로 묶으면 재스냅샷 시차마다 빨간불이 켜진다.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
ADAPTER = REPO / "evaluation" / "controllers" / "vissim_stackelberg_adapter.py"
DEFAULT_YAML = REPO / "vendor" / "NumSim-mine" / "src" / "config" / "default.yaml"
PRODUCTION_CONFIG = (
    REPO / "evaluation" / "configs"
    / "real_world_modi_pstack_distributed_core15n41_20260805.json"
)

PARALLEL_KEYS = ("stackelberg_leader_parallel_backend", "grid_parallel_backend")


class RealRunStaysSerialTests(unittest.TestCase):
    def test_adapter_hardcodes_serial_for_both_parallel_surfaces(self) -> None:
        """config 로 못 뒤집는 층이다 - 어댑터가 직접 박는다."""
        source = ADAPTER.read_text(encoding="utf-8")
        for key in PARALLEL_KEYS:
            with self.subTest(key=key):
                hits = re.findall(rf'"{key}"\s*:\s*"([a-z]+)"', source)
                self.assertTrue(hits, f"{key} 하드코딩이 사라졌다")
                self.assertEqual(set(hits), {"serial"}, f"{key} = {set(hits)}")

    def test_vendor_default_is_serial_too(self) -> None:
        """어댑터를 안 거치는 경로가 생겨도 기본값이 직렬이어야 한다."""
        text = DEFAULT_YAML.read_text(encoding="utf-8")
        for key in PARALLEL_KEYS:
            with self.subTest(key=key):
                match = re.search(rf"^\s*{key}\s*:\s*(\w+)\s*$", text, re.MULTILINE)
                self.assertIsNotNone(match, f"{key} 가 default.yaml 에 없다")
                self.assertEqual(match.group(1), "serial")

    def test_production_config_does_not_turn_parallel_on(self) -> None:
        """생산 config 가 기본값을 덮어써 병렬을 켜면 안 된다."""
        mpc = json.loads(PRODUCTION_CONFIG.read_text(encoding="utf-8"))
        mpc = (mpc.get("config_overrides") or {}).get("mpc") or {}
        for key in PARALLEL_KEYS:
            with self.subTest(key=key):
                self.assertIn(mpc.get(key, "serial"), ("serial", None))


if __name__ == "__main__":
    unittest.main()
