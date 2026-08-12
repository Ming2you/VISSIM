# N4-0 작업2 - 새 dual-ring .sig 를 가리키는 inpx 를 만드는 생산자의 계약 테스트
"""합성 픽스처가 아니라 실 `modi_eval_rw_control.inpx`(3.0 MB · SC 50개)에 건다.

## 무엇을 고정하는가

배선은 **한 속성값 15개** 말고는 아무것도 바꾸지 않는 수술이어야 한다. inpx 는 감사
`canonical_topology` 가 `inpx_sha256` 으로 붙잡고 있는 파일이라, 링크·커넥터·수요가
한 바이트라도 흔들리면 토폴로지 전체가 재검증 대상이 된다.

    바뀌는 것   제어 15 SC 의 `supplyFile2` 값 (`<stem>.sig` -> `<stem>_n4dr150.sig`)
    안 바뀌는 것 나머지 35 SC 의 `supplyFile2`, `progNo`, `offset`, 그 밖 전부

원본은 덮어쓰지 않는다. 새 파일명으로 쓰고, 원본 sha256 이 그대로인지 검사가 확인한다.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
if str(REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO / "scripts"))
if str(REPO / "plant") not in sys.path:
    sys.path.insert(0, str(REPO / "plant"))

NETWORK = REPO / "network" / "real_world_gaepo_modi" / "modi_eval_rw_control.inpx"
MAPPING = (
    REPO
    / "evaluation"
    / "real_world_modi_control_distributed_20260728"
    / "control_mapping_distributed_core15n41_20260805.json"
)

# 실측된 제어 15 SC -> `.sig` 파일 stem. 파일명 끝자리가 SC 번호와 다른 4건(5·6·11·12)이
# 여기서 갈린다. 이 표가 틀리면 배선이 엉뚱한 프로그램을 가리킨다.
EXPECTED_SIG_STEM = {
    1: "개포동 test-bed1",
    5: "개포동 test-bed7",
    6: "개포동 test-bed9",
    11: "개포동 test-bed3",
    12: "개포동 test-bed5",
    101: "개포동 test-bed101",
    105: "개포동 test-bed105",
    107: "개포동 test-bed107",
    108: "개포동 test-bed108",
    109: "개포동 test-bed109",
    1001: "개포동 test-bed1001",
    1002: "개포동 test-bed1002",
    1003: "개포동 test-bed1003",
    1004: "개포동 test-bed1004",
    1005: "개포동 test-bed1005",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _supply_by_controller(path: Path) -> dict[int, str]:
    root = ET.parse(path).getroot()
    return {
        int(element.get("no")): str(element.get("supplyFile2") or "")
        for element in root.findall(".//signalControllers/signalController")
        if element.get("no")
    }


class RewireContractTests(unittest.TestCase):
    """실 inpx 를 실제로 다시 써서 본다. 임시 디렉터리에 쓰고 원본은 읽기만 한다."""

    @classmethod
    def setUpClass(cls) -> None:
        if not NETWORK.is_file():
            raise unittest.SkipTest("run network is unavailable")
        import rewire_inpx_signal_programs as module

        cls.module = module
        cls.before_sha = _sha256(NETWORK)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "rewired.inpx"
        cls.table = module.rewire(
            network_path=NETWORK, mapping_path=MAPPING, out_path=cls.out
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_it_rewires_exactly_the_fifteen_controlled_controllers(self) -> None:
        rows = {int(row["sc_no"]): row for row in self.table["controllers"]}
        self.assertEqual(sorted(rows), sorted(EXPECTED_SIG_STEM))
        for sc_no, stem in EXPECTED_SIG_STEM.items():
            with self.subTest(sc=sc_no):
                self.assertEqual(rows[sc_no]["before_sig"], f"{stem}.sig")
                self.assertEqual(rows[sc_no]["after_sig"], f"{stem}_n4dr150.sig")

    def test_every_other_controller_keeps_its_program_declaration(self) -> None:
        """35 SC 는 한 글자도 안 바뀐다."""
        before = _supply_by_controller(NETWORK)
        after = _supply_by_controller(self.out)
        self.assertEqual(sorted(before), sorted(after))
        changed = {sc for sc in before if before[sc] != after[sc]}
        self.assertEqual(changed, set(EXPECTED_SIG_STEM))

    def test_the_shared_program_moves_only_for_the_controlled_controller(self) -> None:
        """전역 문자열 치환이면 여기서 깨진다.

        SC109 와 SC9004 는 **같은** `.sig` 를 가리킨다. SC9004 는 제어 대상이 아니므로
        옛 프로그램에 남아야 한다. 파일명으로 찾아 바꾸면 둘 다 옮겨 간다.
        """
        before = _supply_by_controller(NETWORK)
        after = _supply_by_controller(self.out)
        self.assertEqual(before[109], before[9004])
        self.assertEqual(after[109], "#data#개포동 test-bed109_n4dr150.sig")
        self.assertEqual(after[9004], before[9004])

    def test_the_only_byte_difference_is_the_fifteen_attribute_values(self) -> None:
        """줄 단위 diff 가 15 줄이고, 그 줄들의 차이가 `_n4dr150` 삽입뿐이다."""
        before = NETWORK.read_bytes().split(b"\r\n")
        after = self.out.read_bytes().split(b"\r\n")
        self.assertEqual(len(before), len(after))
        differing = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
        self.assertEqual(len(differing), 15, differing)
        for index in differing:
            restored = after[index].replace(b"_n4dr150.sig", b".sig")
            self.assertEqual(restored, before[index])

    def test_every_rewired_program_exists_and_runs_a_150_second_cycle(self) -> None:
        """배선 대상이 실제로 파싱되고 목표 주기를 돌린다. 이름만 맞으면 안 된다."""
        from src.vissim_strict.signal_program import parse_sig

        root = ET.parse(self.out).getroot()
        seen = 0
        for element in root.findall(".//signalControllers/signalController"):
            sc_no = int(element.get("no"))
            if sc_no not in EXPECTED_SIG_STEM:
                continue
            raw = str(element.get("supplyFile2"))
            self.assertTrue(raw.startswith("#data#"), raw)
            sig_path = NETWORK.parent / raw[6:]
            self.assertTrue(sig_path.is_file(), sig_path)
            program = parse_sig(sig_path, int(element.get("progNo", "1")))
            self.assertEqual(float(program.cycle_length_sec), 150.0, f"SC{sc_no}")
            seen += 1
        self.assertEqual(seen, 15)

    def test_it_refuses_when_a_target_program_is_missing(self) -> None:
        """되돌림 증명 - 없는 접미사를 주면 조용히 원본을 베끼지 않고 죽는다."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "x.inpx"
            with self.assertRaises(self.module.RewireError):
                self.module.rewire(
                    network_path=NETWORK,
                    mapping_path=MAPPING,
                    out_path=out,
                    suffix="_does_not_exist",
                )
            self.assertFalse(out.exists())

    def test_it_refuses_to_overwrite_the_original_network(self) -> None:
        """원본 inpx 덮어쓰기는 규칙 위반이라 생산자 자신이 막는다."""
        with self.assertRaises(self.module.RewireError):
            self.module.rewire(
                network_path=NETWORK, mapping_path=MAPPING, out_path=NETWORK
            )

    def test_the_original_network_is_untouched(self) -> None:
        self.assertEqual(_sha256(NETWORK), self.before_sha)

    def test_the_table_records_both_network_hashes(self) -> None:
        """감사 `canonical_topology` 가 `inpx_sha256` 을 보므로 파급을 표에 남긴다."""
        source = self.table["source"]
        self.assertEqual(source["network_sha256_before"], self.before_sha)
        self.assertEqual(source["network_sha256_after"], _sha256(self.out))
        self.assertNotEqual(
            source["network_sha256_before"], source["network_sha256_after"]
        )
        self.assertTrue(json.dumps(self.table, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
