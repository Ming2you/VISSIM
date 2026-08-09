# canonical_topology 의 관측 연산자가 실런 네트워크에 실제로 존재하는지 고정한다 (v3 N9)
"""관측 연산자 토폴로지와 실런 `.inpx` 가 같은 네트워크를 가리키는지 검사한다.

## 왜 필요한가

`evaluation/strict_plant_20260731/canonical_topology.json` 은 **미추적 22.8 MB** 산출물이고,
자기 provenance 에 `source.inpx_path` 가 다른 워크스페이스(`...\\Codex\\VISSIM\\...\\modi.inpx`)
이며 `source.inpx_sha256 = 12489a21...` 로 기록돼 있다. **그 해시와 일치하는 `.inpx` 가 이
저장소에 하나도 없다.** 반면 실런은 `network/real_world_gaepo_modi/modi_eval_rw_control.inpx`
(sha256 f3ce390f...)를 쓴다.

그래서 "낡은 토폴로지에 조인한 것 아닌가" 라는 의심이 정당하다. 실측으로 확인한 결과는
다음과 같다.

    vehicleTravelTimeMeasurement  191/191  id·name 동일
    queueCounter                   90/90   id·name 동일
    dataCollectionPoint           198/198  id·name 동일
    토폴로지 연산자 479개 중 실런 inpx 에 없는 것 0개

즉 관측 계층에 한해서는 두 네트워크가 같다. **그러나 이것은 지금 시점의 사실일 뿐이다.**
어느 한쪽을 다시 만들면 조용히 어긋날 수 있고, 어긋난 채로 N9 를 돌리면 측정소-링크 조인이
다른 네트워크를 가리킨 채 1,620 셀이 낭비된다. 그래서 고정한다.

## 남은 재현성 구멍 (여기서 해결하지 않음)

토폴로지 산출물이 추적되지 않으므로 새로 클론하면 이 테스트가 skip 된다. 산출물을 커밋할지,
`.inpx` 에서 다시 컴파일하는 CLI 를 만들지는 별건 결정이다. 지금은 구멍의 존재를 기록한다.
"""

from __future__ import annotations

import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
TOPOLOGY_PATH = REPO / "evaluation" / "strict_plant_20260731" / "canonical_topology.json"
NETWORK_DIR = REPO / "network" / "real_world_gaepo_modi"
LIVE_INPX = NETWORK_DIR / "modi_eval_rw_control.inpx"

# 토폴로지의 연산자 종류 -> inpx 의 XML 태그.
OPERATOR_TAGS = {
    "travel_time_measurement": "vehicleTravelTimeMeasurement",
    "queue_counter": "queueCounter",
    "data_collection_point": "dataCollectionPoint",
}
EXPECTED_COUNTS = {
    "travel_time_measurement": 191,
    "queue_counter": 90,
    "data_collection_point": 198,
}


def _operator_numbers(inpx: Path, tag_name: str) -> set[str]:
    root = ET.parse(inpx).getroot()
    return {
        element.get("no")
        for element in root.iter()
        if element.tag.split("}")[-1] == tag_name and element.get("no") is not None
    }


def _topology_numbers(topology: dict) -> dict[str, set[str]]:
    grouped: dict[str, set[str]] = {}
    for operator in topology["observation_operators"]:
        kind = operator.get("kind") or operator.get("type")
        number = operator.get("vissim_no") or operator.get("no") or operator.get("id")
        grouped.setdefault(str(kind), set()).add(str(number))
    return grouped


@unittest.skipUnless(TOPOLOGY_PATH.exists(), f"canonical topology 없음: {TOPOLOGY_PATH}")
@unittest.skipUnless(LIVE_INPX.exists(), f"실런 네트워크 없음: {LIVE_INPX}")
class ObservationOperatorNetworkIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.topology = json.loads(TOPOLOGY_PATH.read_text(encoding="utf-8"))
        cls.by_kind = _topology_numbers(cls.topology)

    def test_topology_source_inpx_is_absent_from_this_repository(self) -> None:
        """구멍을 사실로 고정한다. 사라지면(= 원본이 추적되면) 이 테스트가 알려 준다."""
        import hashlib

        recorded = self.topology["source"]["inpx_sha256"]
        digests = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(NETWORK_DIR.glob("*.inpx"))
        }
        self.assertTrue(digests, "네트워크 디렉터리에 inpx 가 하나도 없다")
        self.assertNotIn(
            recorded,
            set(digests.values()),
            "토폴로지 원본 inpx 가 이제 저장소에 있다 — 재현성 구멍이 메워졌으니 "
            "이 테스트와 모듈 docstring 을 갱신하라",
        )

    def test_every_topology_operator_exists_in_the_live_network(self) -> None:
        """조인이 다른 네트워크를 가리킨 채 1,620 셀을 돌리는 것을 막는다."""
        for kind, tag in OPERATOR_TAGS.items():
            with self.subTest(kind=kind):
                topology_numbers = self.by_kind.get(kind, set())
                self.assertEqual(len(topology_numbers), EXPECTED_COUNTS[kind])
                live = _operator_numbers(LIVE_INPX, tag)
                missing = sorted(topology_numbers - live)
                self.assertEqual(missing, [], f"{kind}: 실런 네트워크에 없는 연산자")

    def test_every_repository_network_shares_the_same_measurement_layout(self) -> None:
        """저장소의 모든 inpx 가 같은 측정소 구성을 갖는지 기록한다.

        실측 결과 8개 파일 전부 동일했다. 그래서 "다른 네트워크와 대조" 식 음성 대조는
        후보가 없어 성립하지 않는다(그 대신 아래 합성 대조를 쓴다).

        이 사실 자체가 유용하다 — 어느 시나리오 변형을 돌리든 측정소 매핑을 다시 만들 필요가
        없다는 뜻이고, 어느 하나가 달라지면 여기서 먼저 드러난다.
        """
        reference = _operator_numbers(LIVE_INPX, "queueCounter")
        for path in sorted(NETWORK_DIR.glob("*.inpx")):
            with self.subTest(network=path.name):
                self.assertEqual(_operator_numbers(path, "queueCounter"), reference)

    def test_a_fabricated_operator_is_reported_missing(self) -> None:
        """음성 대조 — 비교 로직에 이빨이 있는지 확인한다.

        저장소에 측정소 구성이 다른 네트워크가 없으므로 파일 대조로는 대조가 안 된다.
        대신 실재하지 않는 연산자 번호를 섞어 반드시 missing 으로 잡히는지 본다.
        이게 없으면 위 검사는 "항상 통과하는 검사" 와 구별되지 않는다.
        """
        live = _operator_numbers(LIVE_INPX, "queueCounter")
        fabricated = "999999999"
        self.assertNotIn(fabricated, live)
        tampered = set(self.by_kind["queue_counter"]) | {fabricated}
        self.assertEqual(sorted(tampered - live), [fabricated])


if __name__ == "__main__":
    unittest.main()
