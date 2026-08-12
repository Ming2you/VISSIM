# v3 N1.5 - vendor 스냅샷 재앵커 파이프라인의 계약을 고정하는 테스트
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
if str(REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO / "scripts"))

import update_numsim_snapshot as snapshot  # noqa: E402
from update_numsim_snapshot import main as snapshot_main  # noqa: E402

VENDOR = REPO / "vendor" / "NumSim-mine"
UPSTREAM = REPO.parent / "NumSim-mine"


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return (result.stdout or "").strip()


def blob_oid(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def make_upstream(path: Path, files: dict[str, bytes]) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-q")
    git(path, "config", "user.email", "t@example.com")
    git(path, "config", "user.name", "t")
    git(path, "config", "core.autocrlf", "false")
    for relative, data in files.items():
        target = path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "fixture")
    return path


def make_workspace(path: Path) -> Path:
    """A workspace holding the vendor snapshot and the verifier that repeats its facts."""
    vendor = path / "vendor" / "NumSim-mine"
    (vendor / "src").mkdir(parents=True)
    (vendor / "UPSTREAM_TREE.json").write_text(
        json.dumps(
            {
                "schema_version": "numsim-upstream-tree-v1",
                "upstream_repository": "https://example.invalid/numsim.git",
                "commit": "0" * 40,
                "root_tree": "1" * 40,
                "src_tree": "2" * 40,
                "object_format": "sha1",
                "python_file_count": 0,
                "python_blobs": {},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (vendor / "SNAPSHOT.md").write_text(
        "\n".join(
            (
                "# NumSim bundled runtime snapshot",
                "",
                "| Field | Value |",
                "|---|---|",
                "| Upstream repository | `https://example.invalid/numsim.git` |",
                "| Upstream commit | `" + "0" * 40 + "` |",
                "| Upstream root tree | `" + "1" * 40 + "` |",
                "| Upstream `src` tree | `" + "2" * 40 + "` |",
                "| Git object format | `sha1` |",
                "| Immutable anchor | `UPSTREAM_TREE.json` (`numsim-upstream-tree-v1`, 0 Python blobs) |",
                "| Snapshot date | `1970-01-01` |",
                "",
            )
        ),
        encoding="utf-8",
    )
    scripts = path / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "build_preflight_manifest.py").write_text(
        'EXPECTED_NUMSIM_COMMIT = "' + "0" * 40 + '"\n', encoding="utf-8"
    )
    # baseline 검증기는 verify_runtime_source 와 **똑같은 다섯 상수**를 따로 들고 있다.
    # 커밋 하나만 갱신하면 나머지 넷이 낡아 trust-anchor 6종 불일치로 FAIL 한다 - 실측했다.
    (scripts / "validate_baseline_snapshot.py").write_text(
        'EXPECTED_NUMSIM_COMMIT = "' + "0" * 40 + '"\n'
        'EXPECTED_ROOT_TREE = "' + "1" * 40 + '"\n'
        'EXPECTED_SRC_TREE = "' + "2" * 40 + '"\n'
        'EXPECTED_ANCHOR_SEMANTIC_SHA256 = "' + "3" * 64 + '"\n'
        "EXPECTED_PYTHON_FILE_COUNT = 0\n",
        encoding="utf-8",
    )
    (scripts / "verify_runtime_source.py").write_text(
        'EXPECTED_SNAPSHOT_COMMIT = "' + "0" * 40 + '"\n'
        'EXPECTED_ROOT_TREE = "' + "1" * 40 + '"\n'
        'EXPECTED_SRC_TREE = "' + "2" * 40 + '"\n'
        "EXPECTED_PYTHON_FILE_COUNT = 0\n"
        'EXPECTED_ANCHOR_SEMANTIC_SHA256 = "' + "3" * 64 + '"\n',
        encoding="utf-8",
    )
    return path


class UpdateNumsimSnapshotTests(unittest.TestCase):
    def test_anchor_records_upstream_commit_and_lf_normalised_blob_oids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # CRLF 로 저장한다. 검증기가 LF 정규화 후 해시하므로 앵커는 LF 기준이어야 한다.
            upstream = make_upstream(
                root / "upstream",
                {"src/pkg/mod.py": b"VALUE = 1\r\n", "src/__init__.py": b""},
            )
            workspace = make_workspace(root / "ws")

            code = snapshot_main([
                "--workspace-root", str(workspace),
                "--upstream", str(upstream),
            ])
            self.assertEqual(code, 0)

            anchor = json.loads(
                (workspace / "vendor" / "NumSim-mine" / "UPSTREAM_TREE.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(anchor["commit"], git(upstream, "rev-parse", "HEAD"))
            self.assertEqual(anchor["python_file_count"], 2)
            self.assertEqual(
                anchor["python_blobs"]["src/pkg/mod.py"], blob_oid(b"VALUE = 1\n")
            )


    def test_sources_are_copied_and_stale_vendor_files_removed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream = make_upstream(root / "upstream", {"src/keep.py": b"KEEP = 1\n"})
            workspace = make_workspace(root / "ws")
            vendor = workspace / "vendor" / "NumSim-mine"
            # 상류에 더 이상 없는 파일. 남겨 두면 검증기가 앵커 미등록으로 거부한다.
            (vendor / "src" / "stale.py").write_text("STALE = 1\n", encoding="utf-8")

            self.assertEqual(
                snapshot_main([
                    "--workspace-root", str(workspace),
                    "--upstream", str(upstream),
                ]),
                0,
            )

            self.assertEqual(
                (vendor / "src" / "keep.py").read_bytes(), b"KEEP = 1\n"
            )
            self.assertFalse((vendor / "src" / "stale.py").exists())

    def test_dirty_upstream_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream = make_upstream(root / "upstream", {"src/mod.py": b"V = 1\n"})
            workspace = make_workspace(root / "ws")
            # 커밋되지 않은 추적 변경. 앵커가 가리키는 커밋과 파일 내용이 어긋난다.
            (upstream / "src" / "mod.py").write_text("V = 2\n", encoding="utf-8")

            self.assertEqual(
                snapshot_main([
                    "--workspace-root", str(workspace),
                    "--upstream", str(upstream),
                ]),
                1,
            )
            anchor = json.loads(
                (workspace / "vendor" / "NumSim-mine" / "UPSTREAM_TREE.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(anchor["commit"], "0" * 40)

    def test_snapshot_md_and_verifier_constants_are_rewritten_together(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream = make_upstream(root / "upstream", {"src/mod.py": b"V = 1\n"})
            workspace = make_workspace(root / "ws")

            self.assertEqual(
                snapshot_main([
                    "--workspace-root", str(workspace),
                    "--upstream", str(upstream),
                    "--snapshot-date", "2026-08-07",
                ]),
                0,
            )

            commit = git(upstream, "rev-parse", "HEAD")
            md = (workspace / "vendor" / "NumSim-mine" / "SNAPSHOT.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("| Upstream commit | `" + commit + "` |", md)
            self.assertIn("`numsim-upstream-tree-v1`, 1 Python blobs)", md)
            self.assertIn("| Snapshot date | `2026-08-07` |", md)

            verifier = (workspace / "scripts" / "verify_runtime_source.py").read_text(
                encoding="utf-8"
            )
            # 검증기가 앵커 사실을 다섯 상수로 반복한다. 하나라도 빠지면 FAIL 한다 -
            # 실측으로 root_tree/src_tree/semantic 세 개를 빠뜨려 겪었다.
            anchor = json.loads(
                (workspace / "vendor" / "NumSim-mine" / "UPSTREAM_TREE.json").read_text(
                    encoding="utf-8"
                )
            )
            semantic = hashlib.sha256(
                json.dumps(
                    anchor, ensure_ascii=True, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest()
            self.assertIn('EXPECTED_SNAPSHOT_COMMIT = "' + commit + '"', verifier)
            self.assertIn("EXPECTED_PYTHON_FILE_COUNT = 1", verifier)
            self.assertIn(
                'EXPECTED_ROOT_TREE = "' + git(upstream, "rev-parse", "HEAD^{tree}") + '"',
                verifier,
            )
            self.assertIn(
                'EXPECTED_SRC_TREE = "' + git(upstream, "rev-parse", "HEAD:src") + '"',
                verifier,
            )
            self.assertIn(
                'EXPECTED_ANCHOR_SEMANTIC_SHA256 = "' + semantic + '"', verifier
            )
            # preflight 빌더도 같은 커밋을 독립 상수로 들고 있다(여섯 번째 지점).
            preflight = (workspace / "scripts" / "build_preflight_manifest.py").read_text(
                encoding="utf-8"
            )
            self.assertIn('EXPECTED_NUMSIM_COMMIT = "' + commit + '"', preflight)
            # baseline 검증기는 다섯 상수를 전부 요구한다. 커밋만 갱신하면 사슬 세 단계가
            # 전부 PASS 인데 실런의 baseline 검증에서만 trust-anchor 6종 불일치로 거부된다.
            baseline = (workspace / "scripts" / "validate_baseline_snapshot.py").read_text(
                encoding="utf-8"
            )
            self.assertIn('EXPECTED_NUMSIM_COMMIT = "' + commit + '"', baseline)
            self.assertIn(
                'EXPECTED_ROOT_TREE = "' + git(upstream, "rev-parse", "HEAD^{tree}") + '"',
                baseline,
            )
            self.assertIn(
                'EXPECTED_SRC_TREE = "' + git(upstream, "rev-parse", "HEAD:src") + '"',
                baseline,
            )
            self.assertIn("EXPECTED_PYTHON_FILE_COUNT = 1", baseline)
            self.assertIn(
                'EXPECTED_ANCHOR_SEMANTIC_SHA256 = "' + semantic + '"', baseline
            )

    def test_identical_content_does_not_rewrite_vendor_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream = make_upstream(root / "upstream", {"src/mod.py": b"V = 1\n"})
            workspace = make_workspace(root / "ws")
            target = workspace / "vendor" / "NumSim-mine" / "src" / "mod.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            # vendor 사본은 CRLF 다. LF 정규화 기준으로 upstream 과 같은 내용이므로 다시 쓸
            # 이유가 없다. 다시 쓰면 git 이 dirty 로 보아 verify_runtime_source 의
            # tracked_source_clean 이 FAIL 한다. 실측으로 확인한 실패 양식이다.
            target.write_bytes(b"V = 1\r\n")

            self.assertEqual(
                snapshot_main([
                    "--workspace-root", str(workspace),
                    "--upstream", str(upstream),
                ]),
                0,
            )

            self.assertEqual(target.read_bytes(), b"V = 1\r\n")


class AnchorConstantCoverageTests(unittest.TestCase):
    """앵커 사실을 반복하는 상수가 파이프라인 밖에 새로 생기는 것을 막는다.

    이 부류의 사고를 세 번 겪었다. 매번 "지점이 더 있었다" 로 끝났다.

      1차 - verify_runtime_source 의 다섯 중 둘만 갱신 -> trust_anchor 3종 FAIL
      2차 - build_preflight_manifest 를 놓침 -> runtime_source.expected_commit FAIL
      3차 - validate_baseline_snapshot 의 다섯을 통째로 놓침 -> baseline 21+ FAIL

    셋 다 "사슬 세 단계는 PASS 인데 다른 곳이 조용히 거부" 하는 형태라 원인을 찾기 어렵다.
    그래서 개별 대응 대신 부류를 막는다. scripts/ 를 훑어 앵커 상수를 module-level 로 들고
    있는 파일을 찾고, 그 전부가 파이프라인의 갱신 대상인지 확인한다.

    새 파일이 앵커 상수를 들면 이 테스트가 먼저 깨진다. update_numsim_snapshot 의 갱신
    표에 그 파일을 넣으면 통과한다.
    """

    ANCHOR_CONSTANTS = (
        "EXPECTED_SNAPSHOT_COMMIT",
        "EXPECTED_NUMSIM_COMMIT",
        "EXPECTED_ROOT_TREE",
        "EXPECTED_SRC_TREE",
        "EXPECTED_ANCHOR_SEMANTIC_SHA256",
        "EXPECTED_PYTHON_FILE_COUNT",
    )

    def test_every_file_holding_anchor_constants_is_rewritten_by_the_pipeline(self) -> None:
        import re

        import update_numsim_snapshot as tool

        pattern = re.compile(
            r"^(" + "|".join(self.ANCHOR_CONSTANTS) + r")\s*=", re.MULTILINE
        )
        holders = {
            path.name
            for path in sorted((REPO / "scripts").glob("*.py"))
            if pattern.search(path.read_text(encoding="utf-8"))
        }
        # 파이프라인 자신은 상수를 쓰지 않고 이름만 언급하므로 정규식에 안 걸린다.
        self.assertNotIn("update_numsim_snapshot.py", holders)

        covered = set(tool.ANCHOR_CONSTANT_FILES)
        missing = sorted(holders - covered)
        self.assertEqual(
            missing,
            [],
            "앵커 상수를 들고 있는데 파이프라인이 갱신하지 않는 파일이다. "
            "update_numsim_snapshot.ANCHOR_CONSTANT_FILES 에 추가하라: " + str(missing),
        )

        stale = sorted(covered - holders)
        self.assertEqual(
            stale, [], "갱신 대상인데 실제로는 앵커 상수가 없는 파일이다: " + str(stale)
        )


if __name__ == "__main__":
    unittest.main()


class NonPythonSourceTests(unittest.TestCase):
    """스냅샷은 `.py` 만 복사했다. 그래서 `src/config/*.yaml` 이 영원히 낡는다.

    **2026-08-12 실측.** 상류를 4현시로 옮기면서 `default.yaml` 을 150/12/78 로 바꿨는데
    재스냅샷 뒤에도 vendor 는 120/8/92 였다. 247 키 중 셋이 어긋났고 그중
    **`cycle_length` 는 생산 config 가 안 덮어** 실 런이 vendor 의 120 을 쓴다.
    모델이 150 을 쓴다고 믿는 동안 플랜트는 다른 주기를 돈다.

    앵커도 이것을 못 잡는다 - `python_file_count` 와 `python_blobs` 만 검증한다.
    파이썬이 아닌 소스는 검증 대상 밖이라 드리프트가 조용하다.
    """

    def test_upstream_sources_include_non_python_config(self) -> None:
        upstream = snapshot._upstream_source_files(UPSTREAM) if hasattr(
            snapshot, "_upstream_source_files"
        ) else []
        names = {path.as_posix() for path in upstream}
        self.assertTrue(
            any(name.endswith("config/default.yaml") for name in names),
            "src/config/default.yaml 이 복사 대상에 없다",
        )

    def test_the_anchor_covers_non_python_sources(self) -> None:
        """복사만 하고 앵커에 안 넣으면 드리프트가 여전히 조용하다."""
        self.assertTrue(
            hasattr(snapshot, "SOURCE_GLOBS") or hasattr(snapshot, "_upstream_source_files"),
            "비파이썬 소스를 다루는 지점이 없다",
        )
        tree = json.loads((VENDOR / "UPSTREAM_TREE.json").read_text(encoding="utf-8"))
        self.assertIn(
            "source_blobs", tree,
            "앵커가 비파이썬 소스 해시를 담지 않는다",
        )
        self.assertIn("src/config/default.yaml", tree["source_blobs"])

    def test_vendor_config_matches_upstream_byte_for_byte(self) -> None:
        """이 검사가 이번 결함의 직접 재현이다."""
        a = UPSTREAM / "src" / "config" / "default.yaml"
        b = VENDOR / "src" / "config" / "default.yaml"
        if not a.is_file():
            self.skipTest("상류 저장소 없음")
        self.assertEqual(
            _normalise(b.read_bytes()), _normalise(a.read_bytes()),
            "vendor config 가 상류와 다르다 - 재스냅샷이 복사하지 않았다",
        )


def _normalise(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")
