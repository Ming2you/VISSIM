from __future__ import annotations

import csv
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import build_preflight_manifest as preflight
from scripts import verify_runtime_source as runtime_verifier
from scripts.approve_physical_stock_topology import validate_preflight_artifact
from src.vissim_strict.run_evidence import (
    CONFIGURATION_INPUT_ROLES,
    PRODUCER_SOURCE_ROLES,
)


REPO = Path(__file__).resolve().parents[2]


class SyntheticPreflight:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.network_dir = root / "network" / "real_world_gaepo_modi"
        self.network_dir.mkdir(parents=True)
        self.network = self.network_dir / "modi_eval_rw_control.inpx"
        self.signal_roles = root / "evaluation" / "real_world_modi_inventory" / "signal_controller_roles.csv"
        self.runtime_root = root / "runtime"
        self.runtime_source = root / "runtime_source_v2_1.json"
        self.paths = {
            key: root / relative
            for key, relative in preflight.DEFAULT_PATHS.items()
        }
        self.paths["network"] = self.network
        self.paths["signal_roles"] = self.signal_roles
        self._write_inputs()

    def _write_inputs(self) -> None:
        self.network.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<network version="702" vissimVersion="2020.00 - 14 [95957]">
  <signalControllers>
    <signalController no="1" name="model" active="true" type="FIXEDTIME" progNo="1" supplyFile2="#data#model.sig" />
    <signalController no="9004" name="excluded" active="true" type="FIXEDTIME" progNo="1" supplyFile2="#data#excluded.sig" />
    <signalController no="9101" name="RW_SC_RM_C1" active="true" type="FIXEDTIME" progNo="1" supplyFile2="" />
  </signalControllers>
  <signalHeads>
    <signalHead no="1" sg="1 1" />
    <signalHead no="2" sg="9101 1" />
  </signalHeads>
</network>
""",
            encoding="utf-8",
        )
        for name, identifier in (("model.sig", "1"), ("excluded.sig", "9004")):
            (self.network_dir / name).write_text(
                f'<?xml version="1.0" encoding="UTF-8"?><sc version="1" id="{identifier}" />\n',
                encoding="utf-8",
            )

        self.signal_roles.parent.mkdir(parents=True)
        with self.signal_roles.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=("no", "role", "active", "signal_head_count", "supplyFile2"),
            )
            writer.writeheader()
            writer.writerow(
                {
                    "no": "1",
                    "role": "urban_signal_controller",
                    "active": "true",
                    "signal_head_count": "1",
                    "supplyFile2": "#data#model.sig",
                }
            )
            writer.writerow(
                {
                    "no": "9004",
                    "role": "urban_signal_controller",
                    "active": "true",
                    "signal_head_count": "0",
                    "supplyFile2": "#data#excluded.sig",
                }
            )
            writer.writerow(
                {
                    "no": "9101",
                    "role": "urban_signal_controller",
                    "active": "false",
                    "signal_head_count": "1",
                    "supplyFile2": "",
                }
            )

        written_paths: set[Path] = set()
        for key, path in self.paths.items():
            if key in {"network", "signal_roles"}:
                continue
            if path in written_paths:
                continue
            written_paths.add(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            if key == "tuning":
                path.write_text(
                    json.dumps(
                        {
                            "mapping_json": self.paths["control_mapping"].relative_to(self.root).as_posix(),
                            "detector_mapping_json": self.paths["detector_mapping"].relative_to(self.root).as_posix(),
                        }
                    ),
                    encoding="utf-8",
                )
            elif key == "generated_vbs":
                detector = self.paths["detector_mapping"].relative_to(self.root).as_posix()
                path.write_text(f'RW_DETECTOR_MAPPING_PATH = "{detector}"\n', encoding="utf-8")
            elif key == "supported_version_policy":
                path.write_bytes(
                    (REPO / preflight.DEFAULT_PATHS[key]).read_bytes()
                )
            elif key == "preflight_producer":
                path.write_bytes((REPO / preflight.DEFAULT_PATHS[key]).read_bytes())
            elif key == "physical_projection_module":
                shutil.copytree(
                    REPO / "plant" / "src",
                    self.root / "plant" / "src",
                    dirs_exist_ok=True,
                )
            elif key == "topology_approval_validator":
                path.write_bytes((REPO / preflight.DEFAULT_PATHS[key]).read_bytes())
                for dependency in (
                    "build_preflight_manifest.py",
                    "build_vissim_lane_graph.py",
                    "compile_physical_stock_topology.py",
                    "resolve_lane_routes.py",
                ):
                    dependency_path = self.root / "scripts" / dependency
                    dependency_path.parent.mkdir(parents=True, exist_ok=True)
                    dependency_path.write_bytes((REPO / "scripts" / dependency).read_bytes())
            else:
                path.write_text(f"fixture:{key}\n", encoding="utf-8")

        runtime_source_file = self.runtime_root / "src" / "models" / "state.py"
        runtime_source_file.parent.mkdir(parents=True)
        runtime_source_file.write_text("VALUE = 1\n", encoding="utf-8")
        snapshot = self.runtime_root / "SNAPSHOT.md"
        snapshot.write_text(
            "snapshot commit: 0240ba89b97bf43438e1a0f519f7b0c978288913\n",
            encoding="utf-8",
        )
        self.write_runtime_report()

    def write_runtime_report(self) -> None:
        tree = preflight.source_tree_identity(self.runtime_root)
        adapter = self.paths["adapter"]
        verifier = self.paths["runtime_source_verifier"]
        snapshot = self.runtime_root / "SNAPSHOT.md"
        payload = {
            "schema_version": "runtime-source-v2.1",
            "status": "PASS",
            "strict": True,
            "reasons": [],
            "checks": [
                {"id": check_id, "status": "PASS"}
                for check_id in preflight.RUNTIME_SOURCE_TRUST_CHECKS
            ],
            "expected_snapshot_commit": "0240ba89b97bf43438e1a0f519f7b0c978288913",
            "selected_is_canonical": False,
            "input_hashes": {
                "adapter_sha256": preflight.file_sha256(adapter),
                "python_executable_sha256": preflight.file_sha256(Path(sys.executable)),
                "selected_snapshot_sha256": preflight.file_sha256(snapshot),
                "selected_python_tree_normalised_sha256": tree["normalised_tree_sha256"],
                "upstream_tree_anchor_sha256": preflight.file_sha256(
                    self.paths["runtime_source_anchor"]
                ),
            },
            "command_version": {
                "command": "scripts/verify_runtime_source.py",
                "version": "runtime-source-v2.1",
                "sha256": preflight.file_sha256(verifier),
            },
            "python": {
                "executable": str(Path(sys.executable).resolve()),
                "executable_sha256": preflight.file_sha256(Path(sys.executable)),
                "version": sys.version,
            },
            "selected": {
                "root": str(self.runtime_root.resolve()),
                "snapshot_commit": "0240ba89b97bf43438e1a0f519f7b0c978288913",
                "python_file_count": tree["python_file_count"],
                "normalised_tree_sha256": tree["normalised_tree_sha256"],
                "git": {"head_commit": "fixture-commit"},
            },
            "imports": {
                "selected": {
                    "adapter_default_root": str(self.runtime_root.resolve()),
                    "adapter_path": str(adapter.resolve()),
                    "modules": {
                        "src.models.state": {
                            "relative_path": "src/models/state.py",
                        }
                    },
                    "external_modules": [],
                }
            },
        }
        self.runtime_source.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def build(self) -> dict:
        return preflight.build_manifest(
            self.root,
            self.runtime_source,
            path_overrides=self.paths,
            expected_model_count=1,
            expected_resolved_sig_count=1,
            expected_auxiliary_count=1,
        )


class BuildPreflightManifestTests(unittest.TestCase):
    def test_synthetic_fixture_classifies_model_excluded_and_auxiliary_controllers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SyntheticPreflight(Path(temporary))
            report = fixture.build()
            validation_reasons = validate_preflight_artifact(report, fixture.root)

        self.assertEqual(report["status"], "PASS", report["reasons"])
        self.assertEqual(validation_reasons, [])
        self.assertEqual(report["schema_version"], "preflight-v3")
        self.assertEqual(report["fingerprint_sha256"], report["fingerprint"]["sha256"])
        self.assertRegex(report["fingerprint_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(report["network"]["vissim_version"], "2020.00 - 14 [95957]")
        self.assertEqual([item["controller_no"] for item in report["network"]["model_controllers"]], ["1"])
        self.assertEqual(report["network"]["excluded_controller"]["controller_no"], "9004")
        self.assertEqual(report["network"]["excluded_controller"]["signal_head_reference_count"], 0)
        self.assertEqual([item["controller_no"] for item in report["network"]["auxiliary_controllers"]], ["9101"])
        self.assertEqual(report["sample_dimensions"]["resolved_signal_programs"], 1)
        for key in (
            "schema_version",
            "input_hashes",
            "command_version",
            "status",
            "reasons",
            "sample_dimensions",
            "units",
            "downstream_consumers",
        ):
            self.assertIn(key, report)
        for name in (
            "network",
            "signal_roles",
            "link_assignment",
            "adjacency",
            "storage_capacity",
            "tuning",
            "calibration",
            "control_mapping",
            "detector_mapping",
            "generated_vbs",
            "runner",
            "watchdog",
            "adapter",
            "runtime_source_anchor",
            "runtime_source",
            "python_executable",
        ):
            self.assertTrue(report["artifacts"][name]["path"])
            self.assertRegex(report["artifacts"][name]["sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(set(PRODUCER_SOURCE_ROLES).issubset(report["artifacts"]))
        self.assertTrue(
            (set(CONFIGURATION_INPUT_ROLES) - {"demand_profile"}).issubset(
                report["artifacts"]
            )
        )

    def test_fingerprint_is_deterministic_and_changes_with_a_sig(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SyntheticPreflight(Path(temporary))
            first = fixture.build()
            second = fixture.build()
            (fixture.network_dir / "model.sig").write_text(
                '<?xml version="1.0"?><sc version="2" id="1" />\n',
                encoding="utf-8",
            )
            changed = fixture.build()

        self.assertEqual(first["fingerprint"]["sha256"], second["fingerprint"]["sha256"])
        self.assertNotEqual(first["fingerprint"]["sha256"], changed["fingerprint"]["sha256"])

    def test_missing_sig_and_model_count_mismatch_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SyntheticPreflight(Path(temporary))
            (fixture.network_dir / "model.sig").unlink()
            report = fixture.build()

        self.assertEqual(report["status"], "FAIL")
        self.assertIn("signal_program.SC1.resolved", report["reasons"])
        self.assertIn("network.resolved_sig_count", report["reasons"])

    def test_runtime_source_tree_hash_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SyntheticPreflight(Path(temporary))
            (fixture.runtime_root / "src" / "models" / "state.py").write_text(
                "VALUE = 2\n",
                encoding="utf-8",
            )
            report = fixture.build()

        self.assertEqual(report["status"], "FAIL")
        self.assertIn("runtime_source.selected_tree_hash", report["reasons"])

    def test_nonstrict_runtime_source_report_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SyntheticPreflight(Path(temporary))
            payload = json.loads(fixture.runtime_source.read_text(encoding="utf-8"))
            payload["strict"] = False
            fixture.runtime_source.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            report = fixture.build()

        self.assertEqual(report["status"], "FAIL")
        self.assertIn("runtime_source.strict", report["reasons"])

    def test_missing_trust_anchor_check_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SyntheticPreflight(Path(temporary))
            payload = json.loads(fixture.runtime_source.read_text(encoding="utf-8"))
            payload["checks"] = [
                item
                for item in payload["checks"]
                if item["id"] != "canonical.anchor_python_blobs"
            ]
            fixture.runtime_source.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            report = fixture.build()

        self.assertEqual(report["status"], "FAIL")
        self.assertIn(
            "runtime_source.required_check.canonical.anchor_python_blobs",
            report["reasons"],
        )

    def test_default_watchdog_is_the_distributed_core15n41_launcher(self) -> None:
        self.assertEqual(
            preflight.DEFAULT_PATHS["watchdog"],
            "scripts/run_real_world_single_watchdog_distributed_core15n41.ps1",
        )

    def test_tuning_mapping_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SyntheticPreflight(Path(temporary))
            fixture.paths["tuning"].write_text(
                json.dumps(
                    {
                        "mapping_json": "wrong.json",
                        "detector_mapping_json": fixture.paths["detector_mapping"].relative_to(fixture.root).as_posix(),
                    }
                ),
                encoding="utf-8",
            )
            report = fixture.build()

        self.assertEqual(report["status"], "FAIL")
        self.assertIn("tuning.mapping_json", report["reasons"])

    def test_strict_cli_returns_nonzero_and_still_writes_failure_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SyntheticPreflight(Path(temporary))
            fixture.paths["storage_capacity"].unlink()
            output = fixture.root / "preflight.json"
            arguments = [
                "--repo",
                str(fixture.root),
                "--runtime-source",
                str(fixture.runtime_source),
                "--out",
                str(output),
                "--strict",
                "--expected-model-sc-count",
                "1",
                "--expected-resolved-sig-count",
                "1",
                "--expected-auxiliary-sc-count",
                "1",
            ]
            for key, path in fixture.paths.items():
                arguments.extend(("--" + key.replace("_", "-"), str(path)))
            result = preflight.main(arguments)
            report = json.loads(output.read_text(encoding="utf-8"))

        self.assertNotEqual(result, 0)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("artifact.storage_capacity.exists", report["reasons"])

    def test_atomic_writer_replaces_target_and_cleans_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "preflight.json"
            target.write_text('{"status":"OLD"}\n', encoding="utf-8")
            real_replace = os.replace
            calls: list[tuple[Path, Path]] = []

            def recording_replace(source: str | os.PathLike[str], destination: str | os.PathLike[str]) -> None:
                calls.append((Path(source), Path(destination)))
                real_replace(source, destination)

            with mock.patch.object(preflight.os, "replace", side_effect=recording_replace):
                preflight.write_manifest_atomic(target, {"schema_version": "preflight-v3", "status": "PASS"})

            payload = json.loads(target.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0].parent, calls[0][1].parent)
        self.assertFalse(calls[0][0].exists())

    def test_real_repository_counts_hold_while_future_b1a_sources_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime_report_path = Path(temporary) / "runtime_source.json"
            with mock.patch.dict(os.environ, {"RW_PYTHON_EXE": sys.executable}):
                runtime_report = runtime_verifier.build_report(
                    REPO,
                    REPO / "vendor" / "NumSim-mine",
                    strict=True,
                )
            self.assertEqual(runtime_report["status"], "PASS", runtime_report["reasons"])
            runtime_report_path.write_text(json.dumps(runtime_report), encoding="utf-8")
            report = preflight.build_manifest(REPO, runtime_report_path)

        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(
            report["reasons"],
            [
                "artifact.post_run_artifact_producer.exists",
                "artifact.post_run_artifact_producer.sha256",
                "artifact.live_replay_builder.exists",
                "artifact.live_replay_builder.sha256",
            ],
        )
        self.assertEqual(report["sample_dimensions"]["model_signal_controllers"], 41)
        self.assertEqual(report["sample_dimensions"]["resolved_signal_programs"], 41)
        self.assertEqual(report["sample_dimensions"]["unique_resolved_signal_programs"], 41)
        self.assertEqual(report["network"]["excluded_controller"]["controller_no"], "9004")
        self.assertEqual(report["network"]["excluded_controller"]["signal_head_reference_count"], 0)
        self.assertEqual(len(report["network"]["auxiliary_controllers"]), 8)


if __name__ == "__main__":
    unittest.main()
