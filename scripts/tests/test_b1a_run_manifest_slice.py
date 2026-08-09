from __future__ import annotations

import ast
import copy
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import io
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
PLANT_ROOT = REPO / "plant"
SCRIPT_ROOT = REPO / "scripts"
for search_root in (PLANT_ROOT, SCRIPT_ROOT):
    if str(search_root) not in sys.path:
        sys.path.insert(0, str(search_root))

from src.vissim_strict.physical_projection import atomic_write_json, file_sha256, strict_load_json
from src.vissim_strict.approval_replay import (
    ApprovalReplayError,
    MAX_VALIDATION_RESULT_BYTES,
    decode_validation_result_wire,
    validation_result_wire_bytes,
)
from src.vissim_strict.topology import canonical_json_sha256
from src.vissim_strict.run_evidence import (
    APPROVED_TOPOLOGY_FIELDS,
    ADAPTER_CONTROLLERS,
    CONFIGURATION_FIELDS,
    CONFIGURATION_INPUT_ROLES,
    FILE_BINDING_FIELDS,
    POLICY_BINDING_FIELDS,
    PREFLIGHT_FIELDS,
    PRODUCER_SOURCE_ROLES,
    QUALIFICATION_FIELDS,
    RUN_MANIFEST_FIELDS,
    SIMULATION_FIELDS,
    MonotonicClockError,
    RunManifestPublicationError,
    RunManifestValidationError,
    SupportedVersionPolicyError,
    build_run_manifest_creation_result,
    parse_monotonic_clock_line,
    parse_supported_vissim_version,
    publish_run_manifest_create_once,
    resolve_canonical_workspace_absolute_file,
    resolve_canonical_workspace_file,
    run_manifest_semantic_sha256,
    validate_run_manifest,
    validate_supported_version_policy,
    write_run_manifest_creation_result,
)
from build_run_manifest_v2_1 import (
    MAX_REQUEST_BYTES,
    RunManifestRequestError,
    _read_request,
    main as producer_main,
    request_semantic_payload,
    validate_request_template_no_write,
)
from approve_physical_stock_topology import (
    _preflight_fingerprint_sha256,
    semantic_payload as approval_semantic_payload,
    validate_approval_artifact,
    validate_preflight_artifact,
)
from build_state_manifest_v2_1 import expected_approved_topology_binding


def _publication_barrier_writer(root, target, manifest, ready, release, result_queue):
    from src.vissim_strict import run_evidence

    real_fdopen = run_evidence.os.fdopen

    def barrier_fdopen(*args, **kwargs):
        ready.set()
        if not release.wait(20):
            raise RuntimeError("publication barrier timed out")
        return real_fdopen(*args, **kwargs)

    try:
        with mock.patch.object(run_evidence.os, "fdopen", side_effect=barrier_fdopen):
            outcome = publish_run_manifest_create_once(
                target,
                manifest,
                workspace_root=root,
            ).outcome
        result_queue.put(("ok", outcome))
    except BaseException as exc:
        result_queue.put(("error", f"{type(exc).__name__}: {exc}"))


def _publication_barrier_reader(root, target, manifest, result_queue):
    final_exists = Path(target).exists()
    try:
        publish_run_manifest_create_once(
            target,
            manifest,
            workspace_root=root,
            validate_only=True,
        )
        validation = "validated"
    except RunManifestPublicationError as exc:
        validation = "unavailable" if not final_exists else f"visible:{exc}"
    result_queue.put((final_exists, validation))


def _producer_process(request_path, result_queue):
    try:
        result_queue.put(producer_main(["--request", request_path]))
    except BaseException as exc:
        result_queue.put(f"{type(exc).__name__}: {exc}")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


class SkeletalRunManifestFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.paths: dict[str, str] = {}
        for index, role in enumerate(PRODUCER_SOURCE_ROLES):
            relative = (
                "plant/policies/supported_vissim_versions_v2_1.json"
                if role == "supported_version_policy"
                else f"sources/{index:02d}_{role}.txt"
            )
            path = root / Path(relative.replace("/", "\\"))
            if role == "supported_version_policy":
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((REPO / relative).read_bytes())
            else:
                _write(path, f"{role}\n")
            self.paths[role] = relative

        config_paths = {
            "network": "inputs/network.inpx",
            "generated_vbs_config": "inputs/generated_config.vbs",
            "adapter": self.paths["adapter"],
            "calibration": "inputs/calibration.json",
            "tuning": "inputs/공백 file.json",
            "control_mapping": "inputs/control_mapping.json",
            "vehicle_input_roles": "inputs/vehicle_input_roles.csv",
        }
        for role, relative in config_paths.items():
            if role != "adapter":
                _write(root / Path(relative.replace("/", "\\")), f"{role}\n")
        self.config_paths = config_paths

        self.topology_path = root / "outputs/physical_stock_topology_v2_1.json"
        self.approval_path = root / "outputs/topology_approval_v2_1.json"
        topology_semantic = "1" * 64
        atomic_write_json(self.topology_path, {"semantic_sha256": topology_semantic})
        topology_binding = {
            "topology_path": "outputs/physical_stock_topology_v2_1.json",
            "topology_file_sha256": file_sha256(self.topology_path),
            "topology_semantic_sha256": topology_semantic,
        }
        atomic_write_json(
            self.approval_path,
            {
                "schema_version": "topology-approval-v2.1",
                "status": "PASS",
                "reasons": [],
                "approved_topology": topology_binding,
            },
        )

        artifacts: dict[str, dict[str, object]] = {}
        for role, relative in self.paths.items():
            path = root / Path(relative.replace("/", "\\"))
            artifacts[role] = {
                "path": str(path),
                "exists": True,
                "size_bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            }
        for role, relative in self.config_paths.items():
            path = root / Path(relative.replace("/", "\\"))
            artifacts[role] = {
                "path": str(path),
                "exists": True,
                "size_bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            }
        self.preflight_path = root / "outputs/preflight_manifest_v3.json"
        atomic_write_json(
            self.preflight_path,
            {
                "schema_version": "preflight-v3",
                "status": "PASS",
                "reasons": [],
                "fingerprint_sha256": "2" * 64,
                "artifacts": artifacts,
            },
        )
        policy_path = root / Path(self.paths["supported_version_policy"].replace("/", "\\"))
        policy = strict_load_json(policy_path)
        producer_sources = {
            role: {
                "path": relative,
                "file_sha256": file_sha256(root / Path(relative.replace("/", "\\"))),
            }
            for role, relative in self.paths.items()
        }
        inputs = {
            role: {
                "path": relative,
                "file_sha256": file_sha256(root / Path(relative.replace("/", "\\"))),
            }
            for role, relative in self.config_paths.items()
        }
        inputs["demand_profile"] = {"path": None, "file_sha256": None}
        self.manifest = {
            "schema_version": "run-manifest-v2.1",
            "run_id": "run-001",
            "campaign_id": "campaign-001",
            "attempt": 1,
            "qualification": {"mode": "synthetic_fixture"},
            "approved_topology": {
                "approving_manifest_path": "outputs/topology_approval_v2_1.json",
                "approving_manifest_sha256": file_sha256(self.approval_path),
                **topology_binding,
            },
            "preflight": {
                "schema_version": "preflight-v3",
                "path": "outputs/preflight_manifest_v3.json",
                "file_sha256": file_sha256(self.preflight_path),
                "fingerprint_sha256": "2" * 64,
            },
            "producer_sources": producer_sources,
            "configuration": {
                "inputs": inputs,
                "simulation": {
                    "sim_period_sec": 1800,
                    "control_interval_sec": 60,
                    "seed": 13,
                    "controller": "stackelberg",
                    "control_start_sec": -1,
                    "warmup_controller": "no-control",
                    "state_log_interval_sec": 5,
                    "demand_scale": 1.0,
                    "demand_profile": None,
                    "incident_link": 0,
                    "incident_lane": 0,
                    "incident_pos_m": -1.0,
                    "incident_start_sec": -1,
                    "incident_end_sec": -1,
                    "incident_name": "",
                },
            },
            "allowed_capture_times": [60.0, 120.0, 900.0],
            "supported_version_policy": {
                "schema_version": "supported-vissim-versions-v2.1",
                "path": self.paths["supported_version_policy"],
                "file_sha256": file_sha256(policy_path),
                "semantic_sha256": policy["semantic_sha256"],
            },
        }
        self.rehash()

    def rehash(self, manifest: dict | None = None) -> dict:
        target = self.manifest if manifest is None else manifest
        target["semantic_sha256"] = run_manifest_semantic_sha256(target)
        return target

    def validate(self, manifest: dict | None = None, **kwargs):
        return validate_run_manifest(
            self.manifest if manifest is None else manifest,
            workspace_root=self.root,
            **kwargs,
        )


class RunManifestFixture:
    def __init__(self, unused_root: Path) -> None:
        from scripts.tests.test_b1a_core_provenance import B1aProvenanceScriptTests

        self.provenance = B1aProvenanceScriptTests("runTest")
        self.provenance.setUp()
        self.root = self.provenance.root
        _, run_manifest_path = self.provenance.write_selection_and_state()
        self.manifest = strict_load_json(run_manifest_path)
        self.preflight_path = self.provenance.preflight_path

    def close(self) -> None:
        self.provenance.tearDown()

    def rehash(self, manifest: dict | None = None) -> dict:
        target = self.manifest if manifest is None else manifest
        target["semantic_sha256"] = run_manifest_semantic_sha256(target)
        return target

    def validate(self, manifest: dict | None = None, **kwargs):
        return validate_run_manifest(
            self.manifest if manifest is None else manifest,
            workspace_root=self.root,
            **kwargs,
        )


class ApprovalReplayWireTests(unittest.TestCase):
    def wire_result(self) -> dict:
        return {
            "schema_version": "topology-approval-validation-v2.1",
            "status": "PASS",
            "reasons": [],
            "workspace_root": "C:\\검증 작업공간",
            "approval_path": "C:\\검증 작업공간\\outputs\\approval.json",
            "approval_file_sha256": "1" * 64,
            "preflight_path": "C:\\검증 작업공간\\증거\\preflight.json",
            "preflight_file_sha256": "2" * 64,
            "topology_path": "C:\\검증 작업공간\\증거\\topology.json",
            "topology_file_sha256": "3" * 64,
            "topology_semantic_sha256": "4" * 64,
        }

    def test_utf8_wire_round_trips_unicode_without_bom_and_with_exact_lf(self) -> None:
        result = self.wire_result()
        wire = validation_result_wire_bytes(result)
        self.assertFalse(wire.startswith(b"\xef\xbb\xbf"))
        self.assertTrue(wire.endswith(b"\n"))
        self.assertFalse(wire.endswith(b"\r\n"))
        self.assertIn("검증 작업공간".encode("utf-8"), wire)
        self.assertEqual(decode_validation_result_wire(wire), result)

    def test_utf8_wire_rejects_bom_invalid_utf8_noncanonical_lf_and_oversize(self) -> None:
        wire = validation_result_wire_bytes(self.wire_result())
        mutations = (
            b"\xef\xbb\xbf" + wire,
            b"\xff" + wire,
            wire[:-1] + b"\r\n",
            b"x" * (MAX_VALIDATION_RESULT_BYTES + 1),
        )
        for mutation in mutations:
            with self.subTest(prefix=mutation[:4]):
                with self.assertRaises(ApprovalReplayError):
                    decode_validation_result_wire(mutation)


class RunManifestValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        (self.root / "outputs").mkdir(parents=True)
        self.fixture = RunManifestFixture(self.root)
        self.root = self.fixture.root

    def tearDown(self) -> None:
        self.fixture.close()
        self.temporary.cleanup()

    def assert_invalid(self, mutation) -> None:
        manifest = copy.deepcopy(self.fixture.manifest)
        mutation(manifest)
        if "semantic_sha256" in manifest:
            try:
                self.fixture.rehash(manifest)
            except (KeyError, TypeError, ValueError):
                manifest["semantic_sha256"] = "0" * 64
        with self.assertRaises(RunManifestValidationError):
            self.fixture.validate(manifest)

    def test_exact_happy_path_returns_deeply_immutable_result(self) -> None:
        validated = self.fixture.validate(
            expected_run_id="run-13",
            expected_campaign_id="campaign-x",
            expected_attempt=1,
            capture_time=900.0,
        )
        self.assertEqual(validated.qualification_mode, "synthetic_fixture")
        with self.assertRaises(TypeError):
            validated.artifact["run_id"] = "changed"
        with self.assertRaises(TypeError):
            validated.artifact["configuration"]["inputs"]["network"]["path"] = "changed"

    def test_skeletal_self_declared_pass_bundle_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "outputs").mkdir(parents=True)
            skeletal = SkeletalRunManifestFixture(root)
            with self.assertRaises(RunManifestValidationError) as raised:
                skeletal.validate()
        self.assertIn("independent approval/preflight/topology replay failed", str(raised.exception))

    def test_coherently_rehashed_preflight_summary_still_fails_independent_replay(self) -> None:
        preflight = strict_load_json(self.fixture.preflight_path)
        preflight["command_version"]["sha256"] = "f" * 64
        fingerprint = _preflight_fingerprint_sha256(preflight)
        preflight["fingerprint"]["sha256"] = fingerprint
        preflight["fingerprint_sha256"] = fingerprint
        atomic_write_json(self.fixture.preflight_path, preflight)

        approval_path = self.fixture.provenance.approval_path
        approval = strict_load_json(approval_path)
        preflight_hash = file_sha256(self.fixture.preflight_path)
        approval["input_hashes"]["preflight_file_sha256"] = preflight_hash
        approval["source_inputs"]["preflight"]["file_sha256"] = preflight_hash
        approval["semantic_sha256"] = canonical_json_sha256(
            approval_semantic_payload(approval)
        )
        atomic_write_json(approval_path, approval)

        manifest = copy.deepcopy(self.fixture.manifest)
        manifest["preflight"]["file_sha256"] = preflight_hash
        manifest["preflight"]["fingerprint_sha256"] = fingerprint
        manifest["approved_topology"]["approving_manifest_sha256"] = file_sha256(
            approval_path
        )
        self.fixture.rehash(manifest)
        with self.assertRaises(RunManifestValidationError) as raised:
            self.fixture.validate(manifest)
        self.assertIn("independent approval/preflight/topology replay failed", str(raised.exception))

    def test_coherently_rehashed_skeletal_topology_still_fails_independent_replay(self) -> None:
        topology_path = self.fixture.provenance.topology_path
        topology_semantic = self.fixture.manifest["approved_topology"][
            "topology_semantic_sha256"
        ]
        atomic_write_json(topology_path, {"semantic_sha256": topology_semantic})
        topology_hash = file_sha256(topology_path)

        approval_path = self.fixture.provenance.approval_path
        approval = strict_load_json(approval_path)
        approval["input_hashes"]["topology_file_sha256"] = topology_hash
        approval["source_inputs"]["physical_stock_topology"][
            "file_sha256"
        ] = topology_hash
        approval["approved_topology"]["topology_file_sha256"] = topology_hash
        approval["semantic_sha256"] = canonical_json_sha256(
            approval_semantic_payload(approval)
        )
        atomic_write_json(approval_path, approval)

        manifest = copy.deepcopy(self.fixture.manifest)
        manifest["approved_topology"]["topology_file_sha256"] = topology_hash
        manifest["approved_topology"]["approving_manifest_sha256"] = file_sha256(
            approval_path
        )
        self.fixture.rehash(manifest)
        with self.assertRaises(RunManifestValidationError) as raised:
            self.fixture.validate(manifest)
        self.assertIn("independent approval/preflight/topology replay failed", str(raised.exception))

    def test_every_top_level_and_nested_field_is_exact(self) -> None:
        nested = {
            "qualification": QUALIFICATION_FIELDS,
            "approved_topology": APPROVED_TOPOLOGY_FIELDS,
            "preflight": PREFLIGHT_FIELDS,
            "producer_sources": PRODUCER_SOURCE_ROLES,
            "configuration": CONFIGURATION_FIELDS,
            "configuration.inputs": CONFIGURATION_INPUT_ROLES,
            "configuration.simulation": SIMULATION_FIELDS,
            "supported_version_policy": POLICY_BINDING_FIELDS,
        }
        for field in RUN_MANIFEST_FIELDS:
            with self.subTest(scope="top", field=field):
                self.assert_invalid(lambda value, field=field: value.pop(field))
        self.assert_invalid(lambda value: value.__setitem__("extra", None))
        for scope, fields in nested.items():
            for field in fields:
                with self.subTest(scope=scope, field=field):
                    def remove(value, scope=scope, field=field):
                        target = value
                        for part in scope.split("."):
                            target = target[part]
                        target.pop(field)
                    self.assert_invalid(remove)
            def add(value, scope=scope):
                target = value
                for part in scope.split("."):
                    target = target[part]
                target["extra"] = None
            self.assert_invalid(add)
        for role in PRODUCER_SOURCE_ROLES:
            for field in FILE_BINDING_FIELDS:
                with self.subTest(scope="producer", role=role, field=field):
                    self.assert_invalid(lambda value, role=role, field=field: value["producer_sources"][role].pop(field))
            with self.subTest(scope="producer-extra", role=role):
                self.assert_invalid(lambda value, role=role: value["producer_sources"][role].__setitem__("extra", None))
        for role in CONFIGURATION_INPUT_ROLES:
            for field in FILE_BINDING_FIELDS:
                with self.subTest(scope="input", role=role, field=field):
                    self.assert_invalid(lambda value, role=role, field=field: value["configuration"]["inputs"][role].pop(field))
            with self.subTest(scope="input-extra", role=role):
                self.assert_invalid(lambda value, role=role: value["configuration"]["inputs"][role].__setitem__("extra", None))

    def test_identity_qualification_numeric_enum_and_time_mutations(self) -> None:
        mutations = [
            lambda value: value.__setitem__("run_id", "bad id"),
            lambda value: value.__setitem__("campaign_id", ""),
            lambda value: value.__setitem__("attempt", True),
            lambda value: value.__setitem__("attempt", 0),
            lambda value: value["qualification"].__setitem__("mode", "live"),
            lambda value: value["configuration"]["simulation"].__setitem__("sim_period_sec", 1.0),
            lambda value: value["configuration"]["simulation"].__setitem__("control_interval_sec", 0),
            lambda value: value["configuration"]["simulation"].__setitem__("seed", True),
            lambda value: value["configuration"]["simulation"].__setitem__("controller", "unknown"),
            lambda value: value["configuration"]["simulation"].__setitem__("control_start_sec", 1801),
            lambda value: value["configuration"]["simulation"].__setitem__("incident_lane", -1),
            lambda value: value["configuration"]["simulation"].__setitem__("incident_pos_m", float("inf")),
            lambda value: value["configuration"]["simulation"].__setitem__("demand_scale", 0.0),
            lambda value: value.__setitem__("allowed_capture_times", [60, 120.0]),
            lambda value: value.__setitem__("allowed_capture_times", [120.0, 60.0]),
            lambda value: value.__setitem__("allowed_capture_times", [60.0, 60.0]),
            lambda value: value.__setitem__("snapshot_time", 60.0),
        ]
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                self.assert_invalid(mutation)
        empty = copy.deepcopy(self.fixture.manifest)
        empty["allowed_capture_times"] = []
        self.fixture.rehash(empty)
        self.fixture.validate(empty)
        with self.assertRaises(RunManifestValidationError):
            self.fixture.validate(empty, capture_time=0.0)

    def test_duplicate_bindings_and_source_preflight_disagreement_fail(self) -> None:
        self.assert_invalid(
            lambda value: value["configuration"]["inputs"].__setitem__(
                "adapter", copy.deepcopy(value["configuration"]["inputs"]["network"])
            )
        )
        self.assert_invalid(
            lambda value: value["producer_sources"]["watchdog"].update(
                value["producer_sources"]["vbs"]
            )
        )
        self.assert_invalid(
            lambda value: value["supported_version_policy"].__setitem__(
                "semantic_sha256", "3" * 64
            )
        )
        self.assert_invalid(
            lambda value: value["approved_topology"].__setitem__(
                "topology_file_sha256", "4" * 64
            )
        )
        self.assert_invalid(
            lambda value: value["preflight"].__setitem__(
                "fingerprint_sha256", "5" * 64
            )
        )

    def test_demand_profile_null_present_equality(self) -> None:
        self.assert_invalid(
            lambda value: value["configuration"]["simulation"].__setitem__(
                "demand_profile", "inputs/profile.json"
            )
        )
        _write(self.root / "inputs/profile.json", "{}\n")
        provenance = self.fixture.provenance
        provenance.preflight_fixture.paths["demand_profile"] = (
            self.root / "inputs/profile.json"
        )
        provenance.write_preflight()
        self.assertEqual(provenance.approve(), 0)
        preflight = strict_load_json(self.fixture.preflight_path)
        bundle = validate_approval_artifact(
            provenance.approval_path,
            workspace_root=self.root,
            supplied_topology_path=provenance.topology_path,
        )
        manifest = copy.deepcopy(self.fixture.manifest)
        manifest["approved_topology"] = expected_approved_topology_binding(bundle)
        manifest["preflight"]["file_sha256"] = file_sha256(self.fixture.preflight_path)
        manifest["preflight"]["fingerprint_sha256"] = preflight["fingerprint_sha256"]
        manifest["configuration"]["inputs"]["demand_profile"] = {
            "path": "inputs/profile.json",
            "file_sha256": file_sha256(self.root / "inputs/profile.json"),
        }
        manifest["configuration"]["simulation"]["demand_profile"] = "inputs/profile.json"
        self.fixture.rehash(manifest)
        self.fixture.validate(manifest)

    def test_windows_path_spelling_slashes_and_escape_fail(self) -> None:
        self.fixture.validate()
        self.assert_invalid(lambda value: value["configuration"]["inputs"]["network"].__setitem__("path", str(self.root / "inputs/network.inpx")))
        self.assert_invalid(lambda value: value["configuration"]["inputs"]["network"].__setitem__("path", "inputs\\network.inpx"))
        self.assert_invalid(lambda value: value["configuration"]["inputs"]["network"].__setitem__("path", "inputs/../inputs/network.inpx"))
        self.assert_invalid(lambda value: value["configuration"]["inputs"]["network"].__setitem__("path", "INPUTS/network.inpx"))

    def test_preflight_authored_paths_reject_slash_case_and_reparse_aliases(self) -> None:
        original = strict_load_json(self.fixture.preflight_path)
        watchdog_path = original["artifacts"]["watchdog"]["path"]
        lexical_mutations = (
            watchdog_path.replace("\\", "/"),
            watchdog_path.replace("\\scripts\\", "\\SCRIPTS\\"),
        )
        for authored in lexical_mutations:
            with self.subTest(authored=authored):
                preflight = copy.deepcopy(original)
                preflight["artifacts"]["watchdog"]["path"] = authored
                reasons = validate_preflight_artifact(preflight, self.root)
                self.assertIn("artifact watchdog is unavailable", str(reasons))

        def reject_watchdog(root, authored):
            if authored == watchdog_path:
                raise ValueError("reparse alias")
            return resolve_canonical_workspace_absolute_file(root, authored)

        with mock.patch(
            "approve_physical_stock_topology.resolve_canonical_workspace_absolute_file",
            side_effect=reject_watchdog,
        ):
            reasons = validate_preflight_artifact(original, self.root)
        self.assertIn("artifact watchdog is unavailable", str(reasons))

    def test_shared_validator_converts_memory_exhaustion_to_typed_failure(self) -> None:
        with mock.patch(
            "src.vissim_strict.run_evidence.strict_load_json",
            side_effect=MemoryError("adversarial allocation"),
        ):
            with self.assertRaisesRegex(
                RunManifestValidationError, "supported version policy is invalid"
            ):
                self.fixture.validate()

    def test_exported_validator_replays_with_only_plant_on_package_path(self) -> None:
        manifest_path = self.root / "evaluation/runs/x/run_manifest.json"
        self._assert_package_boundary_validation(
            self.root, manifest_path, self.fixture.manifest["semantic_sha256"]
        )

    def test_package_boundary_replay_accepts_non_ascii_workspace_and_bound_path(self) -> None:
        from scripts.tests.test_b1a_core_provenance import B1aProvenanceScriptTests

        provenance = B1aProvenanceScriptTests("runTest")
        provenance.workspace_root_override = (
            Path(self.temporary.name) / "검증 작업공간"
        )
        provenance.setUp()
        try:
            source = provenance.preflight_fixture.paths["monotonic_clock_helper"]
            non_ascii_source = provenance.root / "scripts" / "단조 시계 helper.py"
            shutil.copy2(source, non_ascii_source)
            provenance.preflight_fixture.paths["monotonic_clock_helper"] = (
                non_ascii_source
            )
            provenance.run_source_paths["monotonic_clock_helper"] = (
                non_ascii_source.relative_to(provenance.root).as_posix(),
                non_ascii_source,
            )
            provenance.write_preflight()
            self.assertEqual(provenance.approve(), 0)
            _, manifest_path = provenance.write_selection_and_state()
            manifest = strict_load_json(manifest_path)
            self.assertIn(
                "단조 시계",
                manifest["producer_sources"]["monotonic_clock_helper"]["path"],
            )
            self._assert_package_boundary_validation(
                provenance.root, manifest_path, manifest["semantic_sha256"]
            )
        finally:
            provenance.tearDown()

    def _assert_package_boundary_validation(
        self, workspace_root: Path, manifest_path: Path, semantic_sha256: str
    ) -> None:
        probe = """
import importlib.util
from pathlib import Path
import sys

if importlib.util.find_spec("approve_physical_stock_topology") is not None:
    raise SystemExit("top-level approval script unexpectedly importable")

from src.vissim_strict import validate_run_manifest
from src.vissim_strict.physical_projection import strict_load_json

workspace_root = Path(sys.argv[1])
manifest_path = Path(sys.argv[2])
before = tuple(sys.path)
validated = validate_run_manifest(
    strict_load_json(manifest_path),
    workspace_root=workspace_root,
)
if tuple(sys.path) != before:
    raise SystemExit("package validator mutated consumer sys.path")
print(validated.semantic_sha256)
"""
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(PLANT_ROOT)
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                probe,
                str(workspace_root),
                str(manifest_path),
            ],
            cwd=self.temporary.name,
            env=environment,
            capture_output=True,
            text=True, errors="replace",
            timeout=120,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        self.assertEqual(completed.stdout, semantic_sha256 + "\n")

    def test_reparse_component_is_rejected(self) -> None:
        with mock.patch(
            "src.vissim_strict.run_evidence._is_reparse",
            side_effect=lambda path: path.name == "network.inpx",
        ):
            with self.assertRaises(ValueError):
                resolve_canonical_workspace_file(self.root, "inputs/network.inpx")


class PublicationAndPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        (self.root / "outputs").mkdir(parents=True)
        self.fixture = RunManifestFixture(self.root)
        self.root = self.fixture.root

    def tearDown(self) -> None:
        self.fixture.close()
        self.temporary.cleanup()

    def test_create_reuse_no_mtime_change_and_differing_no_clobber(self) -> None:
        target = self.root / "outputs/run_manifest.json"
        first = publish_run_manifest_create_once(target, self.fixture.manifest, workspace_root=self.root)
        original = target.read_bytes()
        original_mtime = target.stat().st_mtime_ns
        time.sleep(0.02)
        second = publish_run_manifest_create_once(target, self.fixture.manifest, workspace_root=self.root, validate_only=True)
        self.assertEqual((first.outcome, second.outcome), ("created", "validated_existing"))
        self.assertEqual(target.stat().st_mtime_ns, original_mtime)
        different = copy.deepcopy(self.fixture.manifest)
        different["attempt"] = 2
        self.fixture.rehash(different)
        with self.assertRaises(RunManifestPublicationError):
            publish_run_manifest_create_once(target, different, workspace_root=self.root)
        self.assertEqual(target.read_bytes(), original)

    def test_concurrent_create_race_publishes_one_exact_identity(self) -> None:
        target = self.root / "outputs/race.json"
        def publish():
            try:
                return publish_run_manifest_create_once(target, self.fixture.manifest, workspace_root=self.root).outcome
            except RunManifestPublicationError:
                return "failed"
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = sorted(executor.map(lambda _: publish(), range(2)))
        self.assertEqual(outcomes, ["created", "failed"])
        self.fixture.validate(strict_load_json(target))

    def test_process_reader_never_observes_partial_final_path(self) -> None:
        target = self.root / "outputs/process_barrier.json"
        context = multiprocessing.get_context("spawn")
        ready = context.Event()
        release = context.Event()
        writer_results = context.Queue()
        reader_results = context.Queue()
        writer = context.Process(
            target=_publication_barrier_writer,
            args=(
                str(self.root),
                str(target),
                self.fixture.manifest,
                ready,
                release,
                writer_results,
            ),
        )
        writer.start()
        self.assertTrue(ready.wait(20), "writer did not reach publication barrier")
        reader = context.Process(
            target=_publication_barrier_reader,
            args=(str(self.root), str(target), self.fixture.manifest, reader_results),
        )
        reader.start()
        reader.join(20)
        reader_exitcode = reader.exitcode
        reader_result = reader_results.get(timeout=5)
        release.set()
        writer.join(20)
        self.assertEqual(reader_exitcode, 0)
        self.assertEqual(reader_result, (False, "unavailable"))
        self.assertEqual(writer.exitcode, 0)
        self.assertEqual(writer_results.get(timeout=5), ("ok", "created"))
        reused = publish_run_manifest_create_once(
            target,
            self.fixture.manifest,
            workspace_root=self.root,
            validate_only=True,
        )
        self.assertEqual(reused.outcome, "validated_existing")

    def test_published_manifest_is_strictly_reloaded_and_revalidated(self) -> None:
        from src.vissim_strict import run_evidence

        target = self.root / "outputs/strict_reload.json"
        real_load = run_evidence.strict_load_json

        def mutate_only_final(path, **kwargs):
            loaded = real_load(path, **kwargs)
            if Path(path) == target:
                loaded["unexpected"] = True
            return loaded

        with mock.patch.object(
            run_evidence, "strict_load_json", side_effect=mutate_only_final
        ):
            with self.assertRaisesRegex(
                RunManifestPublicationError, "published manifest strict reload failed"
            ):
                publish_run_manifest_create_once(
                    target,
                    self.fixture.manifest,
                    workspace_root=self.root,
                )

        self.assertEqual(
            target.read_bytes(),
            run_evidence.canonical_run_manifest_bytes(self.fixture.manifest),
        )
        self.fixture.validate(real_load(target))

    def test_creation_result_atomically_replaces_stale_deterministically(self) -> None:
        target = self.root / "outputs/result.json"
        target.write_text('{"status":"STALE_PASS"}\n', encoding="utf-8")
        result = build_run_manifest_creation_result(
            status="FAIL",
            reasons=["bad request"],
            outcome="failed",
            run_id="run-001",
            campaign_id="campaign-001",
            attempt=1,
            qualification="synthetic_fixture",
            manifest_path="outputs/run_manifest.json",
            file_sha256_value="",
            semantic_sha256_value="",
        )
        write_run_manifest_creation_result(target, result)
        first = target.read_bytes()
        target.write_text("stale", encoding="utf-8")
        write_run_manifest_creation_result(target, result)
        self.assertEqual(target.read_bytes(), first)

    def test_supported_version_policy_and_parser_mutations(self) -> None:
        policy = strict_load_json(REPO / "plant/policies/supported_vissim_versions_v2_1.json")
        validate_supported_version_policy(policy)
        for raw in ("20", "20.00-15", "2020", "2020.00 x64"):
            with self.subTest(raw=raw):
                self.assertEqual(parse_supported_vissim_version(raw, policy), 2020)
        for raw in ("", " 2020", "2021", "200", "2020.", "２０２０", float("nan")):
            with self.subTest(raw=raw):
                with self.assertRaises(SupportedVersionPolicyError):
                    parse_supported_vissim_version(raw, policy)
        for field in tuple(policy):
            changed = copy.deepcopy(policy)
            changed.pop(field)
            with self.assertRaises(SupportedVersionPolicyError):
                validate_supported_version_policy(changed)
        changed = copy.deepcopy(policy)
        changed["extra"] = None
        with self.assertRaises(SupportedVersionPolicyError):
            validate_supported_version_policy(changed)

    def test_adapter_controller_choices_do_not_drift(self) -> None:
        adapter_path = REPO / "evaluation/controllers/vissim_stackelberg_adapter.py"
        tree = ast.parse(adapter_path.read_text(encoding="utf-8-sig"))
        choices = None
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            if not (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument"
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "--controller"
            ):
                continue
            keyword = next(
                (item for item in node.keywords if item.arg == "choices"), None
            )
            if keyword is not None:
                choices = frozenset(ast.literal_eval(keyword.value))
                break
        self.assertIsNotNone(choices, "adapter --controller choices were not found")
        self.assertEqual(choices, ADAPTER_CONTROLLERS)


class ProducerCliTests(unittest.TestCase):
    def setUp(self) -> None:
        from scripts.tests.test_b1a_core_provenance import B1aProvenanceScriptTests

        self.provenance = B1aProvenanceScriptTests("runTest")
        self.provenance.setUp()
        self.root = self.provenance.root
        run_directory = "evaluation/runs/campaign-001/attempt_01_run-001"
        (self.root / "evaluation/runs/campaign-001").mkdir(parents=True)
        self.request_path = self.root / "inputs/run_manifest_request.json"
        self.output_relative = f"{run_directory}/run_manifest_v2_1.json"
        self.result_relative = f"{run_directory}/run_manifest_creation_result_v2_1.json"
        self.request = {
            "schema_version": "run-manifest-request-v2.1",
            "workspace_root": str(self.root),
            "run_directory": run_directory,
            "run_id": "run-001",
            "campaign_id": "campaign-001",
            "attempt": 1,
            "qualification": {"mode": "synthetic_fixture"},
            "topology_approval": "outputs/topology_approval_v2_1.json",
            "preflight": "outputs/preflight_manifest_v3.json",
            "producer_sources": {
                role: relative
                for role, (relative, _) in self.provenance.run_source_paths.items()
            },
            "configuration": {
                "inputs": {
                    role: (
                        None
                        if role == "demand_profile"
                        else self.provenance.run_input_paths[role][0]
                    )
                    for role in CONFIGURATION_INPUT_ROLES
                },
                "simulation": {
                    "sim_period_sec": 1800,
                    "control_interval_sec": 60,
                    "seed": 13,
                    "controller": "stackelberg",
                    "control_start_sec": -1,
                    "warmup_controller": "no-control",
                    "state_log_interval_sec": 5,
                    "demand_scale": 1.0,
                    "demand_profile": None,
                    "incident_link": 0,
                    "incident_lane": 0,
                    "incident_pos_m": -1.0,
                    "incident_start_sec": -1,
                    "incident_end_sec": -1,
                    "incident_name": "",
                },
            },
            "allowed_capture_times": [60.0, 120.0],
            "output_manifest": self.output_relative,
            "creation_result_output": self.result_relative,
            "validate_only": False,
        }
        self.write_request()

    def tearDown(self) -> None:
        self.provenance.tearDown()

    def write_request(self) -> None:
        self.request["semantic_sha256"] = canonical_json_sha256(
            request_semantic_payload(self.request)
        )
        atomic_write_json(self.request_path, self.request)

    def test_create_reuse_and_malformed_huge_value_replace_stale_result(self) -> None:
        preflight = strict_load_json(self.provenance.preflight_path)
        self.assertTrue(set(PRODUCER_SOURCE_ROLES).issubset(preflight["artifacts"]))
        self.assertEqual(
            validate_preflight_artifact(preflight, self.root),
            [],
            "official preflight producer output must pass the exact validator",
        )
        self.assertEqual(producer_main(["--request", str(self.request_path)]), 0)
        output = self.root / Path(self.output_relative.replace("/", "\\"))
        result_path = self.root / Path(self.result_relative.replace("/", "\\"))
        original = output.read_bytes()
        original_mtime = output.stat().st_mtime_ns
        self.assertEqual(strict_load_json(result_path)["status"], "PASS")
        time.sleep(0.02)
        self.request["validate_only"] = True
        self.write_request()
        self.assertEqual(producer_main(["--request", str(self.request_path)]), 0)
        self.assertEqual(output.stat().st_mtime_ns, original_mtime)
        self.assertEqual(strict_load_json(result_path)["outcome"], "validated_existing")

        self.request["configuration"]["simulation"]["incident_name"] = "x" * 100_000
        self.write_request()
        result_path.write_text('{"status":"STALE_PASS"}\n', encoding="utf-8")
        self.assertEqual(producer_main(["--request", str(self.request_path)]), 1)
        self.assertEqual(output.read_bytes(), original)
        self.assertEqual(strict_load_json(result_path)["status"], "FAIL")

    def test_non_validate_create_rejects_prepopulated_attempt_directory(self) -> None:
        run_dir = self.root / Path(self.request["run_directory"].replace("/", "\\"))
        run_dir.mkdir(parents=True, exist_ok=True)
        stale = run_dir / "stale_preexisting.bin"
        stale.write_bytes(b"stale")
        result_path = self.root / Path(self.result_relative.replace("/", "\\"))
        output = self.root / Path(self.output_relative.replace("/", "\\"))

        result = producer_main([
            "--request", str(self.request_path),
            "--workspace-root", str(self.root),
            "--run-directory", str(self.request["run_directory"]),
            "--creation-result-output", self.result_relative,
        ])

        self.assertEqual(result, 1)
        self.assertTrue(stale.exists())
        self.assertFalse(output.exists())
        self.assertFalse(result_path.exists())

    def test_over_limit_request_is_rejected_before_read_and_replaces_stale_result(self) -> None:
        self.assertEqual(producer_main(["--request", str(self.request_path)]), 0)
        result_path = self.root / Path(self.result_relative.replace("/", "\\"))
        self.request["validate_only"] = True
        self.request["configuration"]["simulation"]["incident_name"] = "x" * (
            MAX_REQUEST_BYTES + 1
        )
        self.write_request()
        result_path.write_text('{"status":"STALE_PASS"}\n', encoding="utf-8")
        with mock.patch.object(
            Path,
            "open",
            side_effect=AssertionError("oversized request must not be opened"),
        ):
            with self.assertRaises(RunManifestRequestError):
                _read_request(self.request_path)
        result = producer_main([
            "--request", str(self.request_path),
            "--workspace-root", str(self.root),
            "--run-directory", str(self.request["run_directory"]),
            "--creation-result-output", self.result_relative,
            "--validate-only",
        ])
        self.assertEqual(result, 1)
        self.assertEqual(strict_load_json(result_path)["status"], "FAIL")

    def test_memory_error_replaces_stale_result_fail_closed(self) -> None:
        self.assertEqual(producer_main(["--request", str(self.request_path)]), 0)
        result_path = self.root / Path(self.result_relative.replace("/", "\\"))
        self.request["validate_only"] = True
        self.write_request()
        result_path.write_text('{"status":"STALE_PASS"}\n', encoding="utf-8")
        with mock.patch(
            "build_run_manifest_v2_1._read_request",
            side_effect=MemoryError("adversarial allocation"),
        ):
            result = producer_main([
                "--request", str(self.request_path),
                "--workspace-root", str(self.root),
                "--run-directory", str(self.request["run_directory"]),
                "--creation-result-output", self.result_relative,
                "--validate-only",
            ])
        self.assertEqual(result, 1)
        failure = strict_load_json(result_path)
        self.assertEqual(failure["status"], "FAIL")
        self.assertIn("MemoryError", failure["reasons"][0])

    def test_oversized_bound_trust_artifacts_fail_without_manifest_clobber(self) -> None:
        self.assertEqual(producer_main(["--request", str(self.request_path)]), 0)
        output_path = self.root / Path(self.output_relative.replace("/", "\\"))
        original_manifest = output_path.read_bytes()
        self.request["validate_only"] = True
        self.write_request()
        artifacts = (
            (self.provenance.approval_path, 8 * 1024 * 1024),
            (self.provenance.preflight_path, 32 * 1024 * 1024),
            (self.provenance.topology_path, 128 * 1024 * 1024),
            (
                self.provenance.run_source_paths["supported_version_policy"][1],
                64 * 1024,
            ),
        )
        real_path_open = Path.open
        for artifact_path, limit in artifacts:
            with self.subTest(artifact=artifact_path.name):
                original = artifact_path.read_bytes()
                try:
                    with artifact_path.open("wb") as stream:
                        stream.seek(limit)
                        stream.write(b"x")
                    result_path = self.root / Path(
                        self.result_relative.replace("/", "\\")
                    )
                    result_path.write_text(
                        '{"status":"STALE_PASS"}\n', encoding="utf-8"
                    )

                    def reject_oversized_open(path, *args, **kwargs):
                        if Path(path) == artifact_path:
                            raise AssertionError(
                                "oversized trust artifact must not be opened"
                            )
                        return real_path_open(path, *args, **kwargs)

                    with mock.patch.object(Path, "open", reject_oversized_open):
                        self.assertEqual(
                            producer_main(["--request", str(self.request_path)]), 1
                        )
                    self.assertEqual(strict_load_json(result_path)["status"], "FAIL")
                    self.assertEqual(output_path.read_bytes(), original_manifest)
                finally:
                    artifact_path.write_bytes(original)

    def test_request_nested_extra_and_differing_manifest_never_clobber(self) -> None:
        self.assertEqual(producer_main(["--request", str(self.request_path)]), 0)
        output = self.root / Path(self.output_relative.replace("/", "\\"))
        original = output.read_bytes()
        self.request["validate_only"] = True
        self.request["qualification"]["extra"] = True
        self.write_request()
        self.assertEqual(producer_main(["--request", str(self.request_path)]), 1)
        self.assertEqual(output.read_bytes(), original)
        result = strict_load_json(self.root / Path(self.result_relative.replace("/", "\\")))
        self.assertEqual((result["status"], result["outcome"]), ("FAIL", "failed"))

    def test_pinned_producer_builds_exact_request_from_watchdog_template(self) -> None:
        template = dict(self.request)
        template.pop("semantic_sha256")
        stage_dir = self.root / "evaluation" / "runs" / "campaign-001"
        template_path = stage_dir / ".stage_attempt_01_run-001_request_template.json"
        request_path = stage_dir / ".stage_attempt_01_run-001_request.json"
        stage_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(template_path, template)
        self.assertEqual(
            producer_main(
                [
                    "--request-template", str(template_path),
                    "--write-request", str(request_path.relative_to(self.root)).replace("\\", "/"),
                    "--workspace-root", str(self.root),
                ]
            ),
            0,
        )
        built = strict_load_json(request_path)
        self.assertEqual(built["semantic_sha256"], canonical_json_sha256(request_semantic_payload(built)))
        self.assertEqual(
            producer_main(
                [
                    "--request", str(request_path),
                    "--workspace-root", str(self.root),
                    "--run-directory", self.request["run_directory"],
                    "--creation-result-output", self.result_relative,
                ]
            ),
            0,
        )

    def assert_same_json_types(self, left, right, path: str = "$") -> None:
        # assertEqual 로는 부족하다 - 파이썬에서 1 == 1.0 이라 JSON double 계약 위반을 못 잡는다.
        self.assertIs(type(left), type(right), f"type differs at {path}")
        if isinstance(left, dict):
            self.assertEqual(sorted(left), sorted(right), f"keys differ at {path}")
            for key in left:
                self.assert_same_json_types(left[key], right[key], f"{path}.{key}")
        elif isinstance(left, list):
            self.assertEqual(len(left), len(right), f"length differs at {path}")
            for index, (item_left, item_right) in enumerate(zip(left, right)):
                self.assert_same_json_types(item_left, item_right, f"{path}[{index}]")

    def test_dry_run_path_uses_the_shared_template_serializer(self) -> None:
        # 발행 경로는 위 회귀가 산출물로 검증한다. dry-run 호출부는 그렇게 못 한다 -
        # 하네스는 직렬화기를 직접 부르므로, .ps1 의 호출 한 줄만 옛 코드로 되돌려도
        # 산출물 기반 assertion 은 초록으로 남는다. 그래서 호출부를 소스로 고정한다.
        # (하네스가 python 을 띄우게 하는 방식은 환경에 따라 갈려 채택하지 않았다.)
        script = REPO / "scripts" / "run_real_world_single_watchdog_distributed_core15n41.ps1"
        source = script.read_text(encoding="utf-8")
        for function_name, expected_call in (
            ("Write-B1aJsonTemplate", "ConvertTo-B1aTemplateJson $Value $false"),
            ("Invoke-B1aTemplateValidationNoWrite", "ConvertTo-B1aTemplateJson $Template $true"),
        ):
            start = source.index(f"function {function_name}(")
            body = source[start:source.index("\n}", start)]
            with self.subTest(function=function_name):
                self.assertIn(expected_call, body)
                # 공유 직렬화기 밖에서 ConvertTo-Json 을 직접 부르면 정규화가 빠진다.
                self.assertNotIn("ConvertTo-Json", body)

    @unittest.skipUnless(shutil.which("powershell"), "Windows PowerShell is required")
    def test_watchdog_production_template_schedule_creates_and_validates_manifest(self) -> None:
        template = dict(self.request)
        template.pop("semantic_sha256")
        stage_dir = self.root / "evaluation" / "runs" / "campaign-001"
        template_path = stage_dir / ".stage_attempt_01_run-001_request_template.json"
        compressed_path = stage_dir / ".stage_attempt_01_run-001_dryrun_template.json"
        request_path = stage_dir / ".stage_attempt_01_run-001_request.json"
        validation_template_path = stage_dir / ".stage_attempt_01_run-001_validation_template.json"
        validation_request_path = stage_dir / ".stage_attempt_01_run-001_validation_request.json"
        script = REPO / "scripts" / "run_real_world_single_watchdog_distributed_core15n41.ps1"
        source = script.read_text(encoding="utf-8")
        helper_start = source.index("function Get-B1aWorkspaceRelativeFile")
        helper_end = source.index("if ($B1aRequired)", helper_start)
        helpers = source[helper_start:helper_end]
        ps_harness = self.root / "inputs" / "build_watchdog_template.ps1"
        ps_harness.write_text(
            "\n".join(
                (
                    "$ErrorActionPreference = 'Stop'",
                    f"$repo = '{self.root}'",
                    "$SimPeriod = 1800",
                    "$ControlIntervalSec = 60",
                    "$Seed = 13",
                    "$Controller = 'stackelberg'",
                    "$ControlStartSec = -1",
                    "$WarmupController = 'no-control'",
                    "$StateLogIntervalSec = 30",
                    "$DemandScale = 1.0",
                    "$IncidentLink = 0",
                    "$IncidentLane = 0",
                    "$IncidentPos = -1.0",
                    "$IncidentStartSec = -1",
                    "$IncidentEndSec = -1",
                    "$IncidentName = ''",
                    helpers,
                    "$schedule = Get-B1aSchedulePlan $SimPeriod $ControlIntervalSec $Controller $ControlStartSec $StateLogIntervalSec '60,120,1800' $false",
                    "$inputBindings = [ordered]@{",
                    f"  network = '{self.provenance.run_input_paths['network'][0]}'",
                    f"  generated_vbs_config = '{self.provenance.run_input_paths['generated_vbs_config'][0]}'",
                    f"  adapter = '{self.provenance.run_input_paths['adapter'][0]}'",
                    f"  calibration = '{self.provenance.run_input_paths['calibration'][0]}'",
                    f"  tuning = '{self.provenance.run_input_paths['tuning'][0]}'",
                    f"  control_mapping = '{self.provenance.run_input_paths['control_mapping'][0]}'",
                    f"  vehicle_input_roles = '{self.provenance.run_input_paths['vehicle_input_roles'][0]}'",
                    "  demand_profile = $null",
                    "}",
                    "$sourceBindings = [ordered]@{",
                    *(
                        f"  {role} = '{relative}'"
                        for role, (relative, _) in self.provenance.run_source_paths.items()
                    ),
                    "}",
                    "$template = New-B1aRequestTemplate 'run-001' 'campaign-001' 1 'evaluation/runs/campaign-001/attempt_01_run-001' 'evaluation/runs/campaign-001/attempt_01_run-001/run_manifest_creation_result_v2_1.json' $false $inputBindings $sourceBindings $schedule 'outputs/topology_approval_v2_1.json' 'outputs/preflight_manifest_v3.json'",
                    f"Write-B1aJsonTemplate '{template_path}' $template",
                    # dry-run(-B1aDryRun)은 압축 직렬화기를 쓴다. 발행본과 같은 정규화를
                    # 거치는지 여기서 고정한다 - 갈라지면 사전검증이 실제 바이트와 다른 것을 본다.
                    "$compressed = ConvertTo-B1aTemplateJson $template $true",
                    f"[System.IO.File]::WriteAllBytes('{compressed_path}', [System.Text.UTF8Encoding]::new($false).GetBytes($compressed))",
                    # 이 두 줄은 직렬화기만 태운다. 실제 dry-run 호출부는
                    # test_dry_run_path_uses_the_shared_template_serializer 가 지킨다.
                )
            ),
            encoding="utf-8",
        )
        stage_dir.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ps_harness),
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8", errors="replace",
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        produced_template = strict_load_json(template_path)
        self.assertEqual(
            produced_template["allowed_capture_times"],
            sorted(set(produced_template["allowed_capture_times"])),
        )
        self.assertTrue(
            all(isinstance(value, float) for value in produced_template["allowed_capture_times"])
        )
        self.assertEqual(produced_template["allowed_capture_times"][0], 1.0)

        compressed_template = strict_load_json(compressed_path)
        self.assertEqual(compressed_template, produced_template)
        self.assert_same_json_types(compressed_template, produced_template)
        self.assertTrue(
            all(isinstance(value, float) for value in compressed_template["allowed_capture_times"])
        )
        validate_request_template_no_write(compressed_template, workspace_root=self.root)

        validate_request_template_no_write(produced_template, workspace_root=self.root)
        self.assertFalse((self.root / self.output_relative).exists())
        self.assertFalse((self.root / self.result_relative).exists())
        int_template = dict(produced_template)
        int_template["allowed_capture_times"] = [1, 60]
        with self.assertRaises(RunManifestValidationError):
            validate_request_template_no_write(int_template, workspace_root=self.root)
        self.assertFalse((self.root / self.output_relative).exists())
        self.assertFalse((self.root / self.result_relative).exists())

        self.assertEqual(
            producer_main(
                [
                    "--request-template", str(template_path),
                    "--write-request", str(request_path.relative_to(self.root)).replace("\\", "/"),
                    "--workspace-root", str(self.root),
                ]
            ),
            0,
        )
        self.assertEqual(
            producer_main(
                [
                    "--request", str(request_path),
                    "--workspace-root", str(self.root),
                    "--run-directory", self.request["run_directory"],
                    "--creation-result-output", self.result_relative,
                ]
            ),
            0,
        )
        manifest_path = self.root / Path(self.output_relative.replace("/", "\\"))
        manifest = strict_load_json(manifest_path)
        self.assertTrue(all(isinstance(value, float) for value in manifest["allowed_capture_times"]))

        validation_template = dict(produced_template)
        validation_template["validate_only"] = True
        validation_template["creation_result_output"] = (
            "evaluation/runs/campaign-001/attempt_01_run-001/"
            "run_manifest_validation_result_v2_1.json"
        )
        atomic_write_json(validation_template_path, validation_template)
        self.assertEqual(
            producer_main(
                [
                    "--request-template",
                    str(validation_template_path),
                    "--write-request",
                    str(validation_request_path.relative_to(self.root)).replace("\\", "/"),
                    "--workspace-root",
                    str(self.root),
                ]
            ),
            0,
        )
        self.assertEqual(
            producer_main(
                [
                    "--request",
                    str(validation_request_path),
                    "--workspace-root",
                    str(self.root),
                    "--run-directory",
                    self.request["run_directory"],
                    "--creation-result-output",
                    validation_template["creation_result_output"],
                    "--validate-only",
                ]
            ),
            0,
        )

    def test_two_process_normal_creation_has_one_result_owner(self) -> None:
        context = multiprocessing.get_context("spawn")
        results = context.Queue()
        processes = [
            context.Process(
                target=_producer_process,
                args=(str(self.request_path), results),
            )
            for _ in range(2)
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(30)
            self.assertEqual(process.exitcode, 0)
        self.assertEqual(sorted(results.get(timeout=5) for _ in processes), [0, 1])
        result_path = self.root / Path(self.result_relative.replace("/", "\\"))
        output_path = self.root / Path(self.output_relative.replace("/", "\\"))
        result = strict_load_json(result_path)
        self.assertEqual((result["status"], result["outcome"]), ("PASS", "created"))
        self.assertEqual(result["run_manifest"]["file_sha256"], file_sha256(output_path))


class MonotonicHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("read_monotonic_clock", SCRIPT_ROOT / "read_monotonic_clock.py")
        assert spec is not None and spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_parser_exact_mutations(self) -> None:
        self.assertEqual(parse_monotonic_clock_line(b"python_perf_counter_ns=1\n"), 1)
        for value in (
            b"python_perf_counter_ns=0\n",
            b"python_perf_counter_ns=01\n",
            b"python_perf_counter_ns=1",
            b"python_perf_counter_ns=1\r\n",
            b"python_perf_counter_ns=1\nextra\n",
            b"other=1\n",
            "python_perf_counter_ns=é\n",
            1,
        ):
            with self.subTest(value=value):
                with self.assertRaises(MonotonicClockError):
                    parse_monotonic_clock_line(value)

    @unittest.skipUnless(sys.platform == "win32" and sys.version_info >= (3, 10), "Windows Python >=3.10 required")
    def test_process_stdout_stderr_and_increasing_readings(self) -> None:
        readings = []
        for _ in range(2):
            completed = subprocess.run(
                [sys.executable, "-B", str(SCRIPT_ROOT / "read_monotonic_clock.py")],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(completed.returncode, 0)
            self.assertEqual(completed.stderr, b"")
            readings.append(parse_monotonic_clock_line(completed.stdout))
        self.assertLess(readings[0], readings[1])

    def test_unsupported_platform_reads_no_counter_and_emits_nothing(self) -> None:
        output = io.StringIO()
        counter = mock.Mock(return_value=1)
        with mock.patch.object(self.module.sys, "platform", "linux"), mock.patch.object(
            self.module.time, "perf_counter_ns", counter
        ), mock.patch.object(self.module.sys, "stdout", output):
            self.assertEqual(self.module.main(), 1)
        counter.assert_not_called()
        self.assertEqual(output.getvalue(), "")

    @unittest.skipUnless(sys.platform == "win32" and sys.version_info >= (3, 10), "Windows Python >=3.10 required")
    def test_invalid_counter_emits_no_success_line(self) -> None:
        output = io.BytesIO()
        stdout = mock.Mock(buffer=output)
        with mock.patch.object(self.module.time, "perf_counter_ns", return_value=0), mock.patch.object(
            self.module.sys, "stdout", stdout
        ):
            self.assertEqual(self.module.main(), 1)
        self.assertEqual(output.getvalue(), b"")


if __name__ == "__main__":
    unittest.main()
