# canonical topology 를 실런 네트워크에서 재생성하고 낡음을 잡아내는 계약 테스트
"""토폴로지를 산출물이 아니라 **빌드 산물**로 다룬다.

## 왜

`evaluation/strict_plant_20260731/canonical_topology.json` 은 미추적 22.8 MB 인데,
실측해 보니 두 가지로 낡았다.

    source.inpx   modi.inpx (12489a21..)  <- 실런은 modi_eval_rw_control.inpx (f3ce390f..)
    compiler      1.0.0                   <- 현재 1.1.1

그 결과 신호 계층이 크게 어긋난다.

    signal_controllers  37 -> 50      signal_groups  392 -> 440
    signal_heads       475 -> 541     routes         278 -> 339

관측 연산자(198/90/191)만 우연히 같아서 조인은 유효했지만, **N4 신호 작업이 이 파일을 보면
컨트롤러를 37개로 착각한다.**

재생성은 9초다. 그래서 커밋하지 않고(24 MB), 저장소 관례대로 gitignore 하고, 낡으면
테스트가 재생성 명령을 알려 주게 한다. `.gitignore:34-36` 이 이미 같은 계열의 큰 토폴로지
산출물을 그렇게 다룬다.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
if str(REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO / "scripts"))

import build_canonical_topology as builder  # noqa: E402


LIVE_INPX = REPO / "network" / "real_world_gaepo_modi" / "modi_eval_rw_control.inpx"
STALE = REPO / "evaluation" / "strict_plant_20260731" / "canonical_topology.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StalenessTests(unittest.TestCase):
    def test_current_compiler_version_is_declared(self) -> None:
        """컴파일러 판올림을 놓치면 낡음 판정이 조용히 통과한다."""
        self.assertTrue(builder.CURRENT_COMPILER_VERSION)
        self.assertIn("vissim-strict-phase0", builder.CURRENT_COMPILER_VERSION)

    @unittest.skipUnless(STALE.exists(), "07-31 토폴로지 없음")
    @unittest.skipUnless(LIVE_INPX.exists(), "실런 네트워크 없음")
    def test_the_0731_artifact_is_reported_stale_for_both_reasons(self) -> None:
        """음성 대조 겸 회귀 — 낡은 파일이 낡았다고 나와야 검사에 이빨이 있다."""
        verdict = builder.staleness(STALE, LIVE_INPX)
        self.assertTrue(verdict["stale"])
        self.assertIn("source_inpx_sha256", verdict["reasons"])
        self.assertIn("compiler_version", verdict["reasons"])
        # 재생성 명령을 알려 주지 않으면 읽는 사람이 무엇을 해야 할지 모른다.
        self.assertIn("build_canonical_topology", verdict["remedy"])

    @unittest.skipUnless(LIVE_INPX.exists(), "실런 네트워크 없음")
    def test_a_freshly_built_topology_is_not_stale(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "canonical_topology_v3.json"
            self.assertEqual(
                builder.main(["--inpx", str(LIVE_INPX), "--out", str(out)]), 0
            )
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["source"]["inpx_sha256"], _sha256(LIVE_INPX))
            self.assertEqual(payload["compiler_version"], builder.CURRENT_COMPILER_VERSION)

            verdict = builder.staleness(out, LIVE_INPX)
            self.assertFalse(verdict["stale"], verdict["reasons"])

    @unittest.skipUnless(LIVE_INPX.exists(), "실런 네트워크 없음")
    def test_rebuild_recovers_the_signal_layer_the_stale_file_understates(self) -> None:
        """낡은 파일이 신호를 과소 계상한다는 사실 자체를 고정한다.

        이 수치가 흔들리면 N4 의 전제가 흔들린다. 그때 조용히 지나가면 안 된다.
        """
        if not STALE.exists():
            self.skipTest("07-31 토폴로지 없음")
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "t.json"
            self.assertEqual(
                builder.main(["--inpx", str(LIVE_INPX), "--out", str(out)]), 0
            )
            fresh = json.loads(out.read_text(encoding="utf-8"))
            stale = json.loads(STALE.read_text(encoding="utf-8"))

            for key in ("signal_controllers", "signal_groups", "signal_heads"):
                with self.subTest(key=key):
                    self.assertGreater(
                        len(fresh[key]),
                        len(stale[key]),
                        f"{key}: 재생성이 낡은 것보다 많아야 한다",
                    )
            # 관측 연산자는 우연히 같았다. 그 우연도 고정해 둔다 - 달라지면 조인이 깨진다.
            self.assertEqual(
                len(fresh["observation_operators"]), len(stale["observation_operators"])
            )


if __name__ == "__main__":
    unittest.main()
