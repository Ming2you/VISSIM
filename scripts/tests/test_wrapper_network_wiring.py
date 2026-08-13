# 생성된 실행 스크립트가 그 산출물이 나온 바로 그 망을 열도록 고정한다
"""배선이 어긋나면 런 중에만 보인다.

`.ps1` 은 VISSIM 을 실제로 띄우는 스위치이고, 그 안의 `$Network` 가 어느 망을 열지
정한다. 생성기는 tuning·mapping·calibration·vbs 네 경로만 치환하고 **망은 안 건드렸다**
(`write_wrapper`). 그래서 dual-ring 망에서 만든 산출물을 물린 wrapper 가 구
`modi_eval_rw_control.inpx` 를 열었다.

그 상태로 돌리면 모델은 150 s 4현시로 명령하고 플랜트는 140/150/160/170 의 옛 프로그램을
돌린다. 정적 검사로는 하나도 안 걸린다 - 두 산출물이 각자 자기 안에서는 일관되기 때문이다.

여기서 거는 계약은 하나다 - **wrapper 의 `$Network` == 그 wrapper 가 물린 mapping 이
기록한 `source_files.network_inpx`**.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

NETWORK_RE = re.compile(r'\$Network = Join-Path \$repo "([^"]+)"')
MAPPING_RE = re.compile(r'\$Mapping = Join-Path \$repo "([^"]+)"')


def _repo_relative(raw: str) -> str:
    """`\` 든 `/` 든, 절대든 상대든 저장소 기준 POSIX 경로 하나로 모은다."""
    text = str(raw).replace("\\", "/").strip()
    if not text:
        return ""
    path = Path(text)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            return path.as_posix()
    return path.as_posix()


def _wrapper_pairs() -> list[tuple[Path, str, str]]:
    """(wrapper, 선언한 망, mapping 이 기록한 망) 목록."""
    out: list[tuple[Path, str, str]] = []
    for wrapper in sorted((ROOT / "scripts").glob("run_real_world_single_watchdog_distributed*.ps1")):
        text = wrapper.read_text(encoding="utf-8-sig")
        network = NETWORK_RE.search(text)
        mapping = MAPPING_RE.search(text)
        if not network or not mapping:
            continue
        mapping_path = ROOT / mapping.group(1).replace("\\", "/")
        # 망 출처를 적는 것은 `player_config` 다. wrapper 가 그것을 직접 참조하지는 않으므로
        # `$Mapping` 의 형제 파일로 찾는다(생성기가 같은 slug·stamp 로 같이 낸다).
        player_path = mapping_path.with_name(
            mapping_path.name.replace("control_mapping_", "player_config_")
        )
        if not player_path.is_file():
            continue
        recorded = ((json.loads(player_path.read_text(encoding="utf-8")).get("source_files") or {})
                    .get("network_inpx") or "")
        out.append(
            (
                wrapper,
                _repo_relative(network.group(1)),
                _repo_relative(str(recorded)),
            )
        )
    return out


class WrapperNetworkWiringTests(unittest.TestCase):
    def test_every_wrapper_opens_the_network_its_artifacts_came_from(self) -> None:
        """`source_files.network_inpx` 를 기록한 mapping 에만 건다.

        그 필드는 나중에 생겼다. 그 이전 산출물(15core·core15all·core15axis 등)은 망을
        적어 두지 않아 대조할 근거 자체가 없다 - 없는 것을 통과로 세지 않으려고 여기서
        **몇 개를 실제로 쟀는지**도 같이 든다.
        """
        pairs = _wrapper_pairs()
        checked = [item for item in pairs if item[2]]
        self.assertGreaterEqual(
            len(checked), 1, f"망을 기록한 wrapper 가 하나도 없다 (후보 {len(pairs)}개)"
        )
        for wrapper, declared, recorded in checked:
            with self.subTest(wrapper=wrapper.name):
                self.assertEqual(recorded, declared)

    def test_the_dual_ring_wrapper_opens_the_dual_ring_network(self) -> None:
        """되돌림 증명 - 두 망이 저장소에 다 있어야 위 검사가 의미를 가진다.

        전부 같은 망을 가리키면 위 검사는 무엇을 넣어도 통과한다.
        """
        networks = {declared for _, declared, _ in _wrapper_pairs()}
        self.assertIn(
            "network/real_world_gaepo_modi/modi_eval_rw_control_n4dr150_20260812.inpx", networks
        )
        self.assertGreater(len(networks), 1, "모든 wrapper 가 같은 망이면 대조가 공허하다")


if __name__ == "__main__":
    unittest.main()
