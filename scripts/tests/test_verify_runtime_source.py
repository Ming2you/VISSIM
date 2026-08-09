from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import verify_runtime_source as verifier


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "verify_runtime_source.py"


class RuntimeSourceVerifierTests(unittest.TestCase):
    def run_verifier(
        self,
        *extra: str,
        repo: Path = REPO,
        strict_argument: str = "--strict",
        set_rw_python: bool = True,
    ) -> tuple[subprocess.CompletedProcess[str], dict]:
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "runtime-source.json"
            environment = dict(os.environ)
            if set_rw_python:
                environment["RW_PYTHON_EXE"] = sys.executable
            else:
                environment.pop("RW_PYTHON_EXE", None)
            command = [
                sys.executable,
                "-B",
                str(SCRIPT),
                "--repo",
                str(repo),
                "--out",
                str(out),
            ]
            if strict_argument:
                command.append(strict_argument)
            command.extend(extra)
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=environment,
                timeout=180,
            )
            report = json.loads(out.read_text(encoding="utf-8"))
        return result, report

    def make_committed_repo(self, root: Path) -> Path:
        repo = root / "fixture-repo"
        shutil.copytree(REPO / "vendor" / "NumSim-mine", repo / "vendor" / "NumSim-mine")
        adapter = repo / "evaluation" / "controllers" / "vissim_stackelberg_adapter.py"
        adapter.parent.mkdir(parents=True)
        shutil.copy2(REPO / "evaluation" / "controllers" / "vissim_stackelberg_adapter.py", adapter)
        shutil.copy2(REPO / ".gitattributes", repo / ".gitattributes")
        subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "s0r-test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "S0R Test"], check=True)
        return repo

    def commit_all(self, repo: Path, message: str) -> None:
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", message], check=True, capture_output=True)

    def test_canonical_bundled_runtime_passes_strict_verification(self) -> None:
        result, report = self.run_verifier()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["schema_version"], "runtime-source-v2.1")
        self.assertEqual(report["status"], "PASS")
        # 앵커 커밋을 하드코딩하지 않는다. 재스냅샷마다 손봐야 하는 지점이 하나 늘 뿐이고,
        # 실제로 0240ba8 -> 7d05097 이동 때 이 계열에서만 26개가 깨졌다.
        # UPSTREAM_TREE.json 과 대조한다. 검증기는 이 앵커를 신뢰의 근거로 쓰므로, 보고서가
        # 앵커와 다른 커밋을 기대한다면 그것 자체가 결함이다.
        anchor = json.loads(
            (REPO / "vendor" / "NumSim-mine" / "UPSTREAM_TREE.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(report["expected_snapshot_commit"], anchor["commit"])
        self.assertTrue(report["selected_is_canonical"])
        self.assertEqual(report["reasons"], [])
        for key in (
            "input_hashes",
            "command_version",
            "reasons",
            "sample_dimensions",
            "units",
            "downstream_consumers",
        ):
            self.assertIn(key, report)
        self.assertTrue(all(report["input_hashes"].values()))
        self.assertEqual(report["command_version"]["version"], "runtime-source-v2.1")
        self.assertGreater(report["sample_dimensions"]["canonical_python_files"], 0)
        self.assertTrue(report["units"])
        self.assertTrue(report["downstream_consumers"])
        # 파일 수도 앵커에서 읽는다. 96 을 박아 두면 상류에 파일 하나만 늘어도 깨진다.
        # 여기서 의미 있는 검사는 "보고서가 앵커와 같은 수를 보고하는가" 이지 특정 숫자가 아니다.
        self.assertEqual(
            report["trust_anchor"]["python_file_count"], anchor["python_file_count"]
        )
        self.assertEqual(anchor["python_file_count"], len(anchor["python_blobs"]))
        checks = {item["id"]: item["status"] for item in report["checks"]}
        self.assertEqual(checks["canonical.anchor_python_blobs"], "PASS")
        self.assertEqual(checks["selected.anchor_python_blobs"], "PASS")
        self.assertTrue(report["canonical"]["files"])
        self.assertTrue(
            all(record["git_blob_oid"] for record in report["canonical"]["files"].values())
        )
        self.assertTrue(
            all(record["checkout_sha256"] for record in report["canonical"]["files"].values())
        )
        self.assertTrue(
            all(record["declared_eol"] == "lf" for record in report["canonical"]["files"].values())
        )

    def test_alternate_eol_override_preserves_normalised_tree_and_import_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            override = Path(temporary) / "NumSim-override"
            shutil.copytree(REPO / "vendor" / "NumSim-mine", override)
            canonical_uses_crlf = any(
                b"\r\n" in source.read_bytes()
                for source in REPO.joinpath("vendor", "NumSim-mine", "src").rglob("*.py")
            )
            for source in override.joinpath("src").rglob("*.py"):
                normalised = source.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
                source.write_bytes(
                    normalised if canonical_uses_crlf else normalised.replace(b"\n", b"\r\n")
                )

            result, report = self.run_verifier("--numsim-root", str(override))

        checks = {item["id"]: item["status"] for item in report["checks"]}
        self.assertNotEqual(result.returncode, 0)  # A copied directory has no verifiable upstream Git commit.
        self.assertEqual(checks["selected.python_tree"], "PASS")
        self.assertEqual(checks["selected.import_module_path_hash"], "PASS")
        self.assertNotEqual(
            report["selected"]["checkout_tree_sha256"],
            report["canonical"]["checkout_tree_sha256"],
        )
        self.assertEqual(
            report["selected"]["normalised_tree_sha256"],
            report["canonical"]["normalised_tree_sha256"],
        )

    def test_modified_override_tree_and_non_repository_commit_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            override = Path(temporary) / "NumSim-override"
            shutil.copytree(REPO / "vendor" / "NumSim-mine", override)
            state_py = override / "src" / "models" / "state.py"
            state_py.write_bytes(state_py.read_bytes() + b"\n# verifier mismatch fixture\n")

            result, report = self.run_verifier("--numsim-root", str(override))

        checks = {item["id"]: item["status"] for item in report["checks"]}
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(checks["selected.commit"], "FAIL")
        self.assertEqual(checks["selected.python_tree"], "FAIL")
        self.assertIn("selected.commit", report["reasons"])
        self.assertIn("selected.python_tree", report["reasons"])

    def test_snapshot_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            override = Path(temporary) / "NumSim-override"
            shutil.copytree(REPO / "vendor" / "NumSim-mine", override)
            snapshot = override / "SNAPSHOT.md"
            snapshot.write_text("snapshot commit: deadbee\n", encoding="utf-8")

            result, report = self.run_verifier("--numsim-root", str(override))

        checks = {item["id"]: item["status"] for item in report["checks"]}
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(checks["selected.snapshot_commit"], "FAIL")

    def test_tampered_anchor_fails_even_in_a_clean_committed_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = self.make_committed_repo(Path(temporary))
            anchor = repo / "vendor" / "NumSim-mine" / "UPSTREAM_TREE.json"
            payload = json.loads(anchor.read_text(encoding="utf-8"))
            payload["root_tree"] = "0" * 40
            anchor.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            self.commit_all(repo, "tampered anchor")

            result, report = self.run_verifier(repo=repo)

        checks = {item["id"]: item["status"] for item in report["checks"]}
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(checks["trust_anchor.semantic_sha256"], "FAIL")
        self.assertEqual(checks["trust_anchor.root_tree"], "FAIL")

    def test_clean_committed_vendor_content_drift_fails_anchor_blob_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = self.make_committed_repo(Path(temporary))
            state_py = repo / "vendor" / "NumSim-mine" / "src" / "models" / "state.py"
            state_py.write_bytes(state_py.read_bytes() + b"\n# committed drift fixture\n")
            self.commit_all(repo, "committed vendor drift")

            result, report = self.run_verifier(repo=repo)

        checks = {item["id"]: item["status"] for item in report["checks"]}
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(checks["canonical.tracked_source_clean"], "PASS")
        self.assertEqual(checks["canonical.anchor_python_blobs"], "FAIL")
        self.assertIn("src/models/state.py", report["checks"][[item["id"] for item in report["checks"]].index("canonical.anchor_python_blobs")]["actual"])

    def test_strict_mode_rejects_missing_rw_python_exe(self) -> None:
        result, report = self.run_verifier(strict_argument="", set_rw_python=False)

        checks = {item["id"]: item["status"] for item in report["checks"]}
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(report["strict"])
        self.assertEqual(checks["python.rw_python_exe_present"], "FAIL")

    def test_allow_nonstrict_is_explicit_and_records_false(self) -> None:
        result, report = self.run_verifier(
            strict_argument="--allow-nonstrict",
            set_rw_python=False,
        )

        self.assertEqual(result.returncode, 0, report["reasons"])
        self.assertEqual(report["status"], "PASS")
        self.assertFalse(report["strict"])

    def test_atomic_writer_replaces_target_and_removes_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "runtime-source.json"
            target.write_text('{"status":"OLD"}\n', encoding="utf-8")
            report = {
                "schema_version": "runtime-source-v2.1",
                "status": "PASS",
            }
            real_replace = os.replace
            calls: list[tuple[Path, Path]] = []

            def recording_replace(source: str | os.PathLike[str], destination: str | os.PathLike[str]) -> None:
                calls.append((Path(source), Path(destination)))
                real_replace(source, destination)

            with mock.patch.object(verifier.os, "replace", side_effect=recording_replace):
                verifier.write_report_atomic(target, report)

            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), report)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][0].parent, target.parent)
            self.assertEqual(calls[0][1], target)
            self.assertFalse(calls[0][0].exists())
            self.assertEqual(list(target.parent.glob(f".{target.name}.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
