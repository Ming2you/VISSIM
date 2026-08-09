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

from update_numsim_snapshot import main as snapshot_main  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
