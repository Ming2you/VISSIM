from __future__ import annotations

import copy
from contextlib import ExitStack
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import tests.test_b1a_core_provenance as core_provenance
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from src.vissim_strict import (
    build_physical_projection_reference,
    load_bounded_json_snapshot,
    load_validated_approved_topology,
    project_vehicle_records,
    publish_projection_outputs,
    validate_physical_projection_reference,
    validate_projection_output_paths,
    validate_projection_sidecar,
    validate_run_manifest,
    write_projection_sidecar,
)
from src.vissim_strict.physical_projection import (
    atomic_write_json,
    file_sha256,
    normalize_vehicle_records,
    strict_load_json,
    thaw_json,
)
from src.vissim_strict.physical_projection_reference import (
    MAX_PROJECTION_SIDECAR_BYTES,
    MAX_PROJECTION_REFERENCE_BYTES,
    MAX_RUN_MANIFEST_BYTES,
    MAX_STATE_BYTES,
    ProjectionReferenceValidationError,
    physical_projection_reference_semantic_sha256,
)
import src.vissim_strict.physical_projection_reference as projection_reference_module
import src.vissim_strict.run_evidence as run_evidence_module


class PhysicalProjectionReferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = core_provenance.B1aProvenanceScriptTests("runTest")
        self.fixture.setUp()
        self.root = self.fixture.root
        self.state_path, self.manifest_path = self.fixture.write_selection_and_state()
        self.manifest_snapshot = load_bounded_json_snapshot(
            self.manifest_path, max_bytes=MAX_RUN_MANIFEST_BYTES
        )
        self.manifest = validate_run_manifest(
            self.manifest_snapshot.value, workspace_root=self.root,
            capture_time=900.0,
        )
        self.approved_topology = load_validated_approved_topology(
            self.manifest, workspace_root=self.root
        )
        self.topology_path = self.approved_topology.topology_snapshot.path
        self.topology = self.approved_topology.topology
        self.state_snapshot = load_bounded_json_snapshot(
            self.state_path, max_bytes=MAX_STATE_BYTES
        )
        self.state = self.state_snapshot.value
        _, _, records_hash = normalize_vehicle_records(
            self.state, self.topology.tolerance_m
        )
        self.context = {
            "topology_file_sha256": self.approved_topology.topology_snapshot.file_sha256,
            "topology_semantic_sha256": self.topology.semantic_sha256,
            "approving_manifest_sha256": self.approved_topology.approval_snapshot.file_sha256,
            "state_file_sha256": self.state_snapshot.file_sha256,
            "vehicle_records_semantic_sha256": records_hash,
        }
        self.sidecar_path = self.state_path.with_name("state_000900.physical_projection_v2_1.json")
        write_projection_sidecar(
            self.sidecar_path,
            project_vehicle_records(self.topology, self.state, self.context),
        )
        self.sidecar_snapshot = load_bounded_json_snapshot(
            self.sidecar_path, max_bytes=MAX_PROJECTION_SIDECAR_BYTES
        )
        self.sidecar = self.sidecar_snapshot.value
        validate_projection_sidecar(
            self.sidecar, topology=self.topology, state=self.state,
            hash_context=self.context, run_id="run-13", sim_sec=900.0,
        )
        self.reference_path = self.state_path.with_name("physical_projection_reference_v2_1.json")
        self.reference = build_physical_projection_reference(
            workspace_root=self.root, run_manifest=self.manifest,
            run_manifest_snapshot=self.manifest_snapshot,
            state_snapshot=self.state_snapshot,
            approved_topology=self.approved_topology,
            sidecar_path=self.sidecar_path,
            sidecar_snapshot=self.sidecar_snapshot,
        )
        atomic_write_json(self.reference_path, self.reference)

    def tearDown(self) -> None:
        self.fixture.tearDown()

    def validate(self):
        return validate_physical_projection_reference(
            self.reference_path.relative_to(self.root).as_posix(),
            workspace_root=self.root,
            run_manifest_path=self.manifest_path.relative_to(self.root).as_posix(),
        )

    def _publish_authored_sidecar(self, sidecar: dict) -> None:
        from src.vissim_strict.physical_projection import projection_semantic_payload
        from src.vissim_strict.topology import canonical_json_sha256

        sidecar["normalized_projection_sha256"] = canonical_json_sha256({
            "topology_semantic_sha256": self.context["topology_semantic_sha256"],
            "vehicle_assignments": sidecar["vehicle_assignments"],
            "stock_counts": sidecar["stock_counts"],
        })
        sidecar["semantic_sha256"] = canonical_json_sha256(
            projection_semantic_payload(sidecar)
        )
        atomic_write_json(self.sidecar_path, sidecar)
        reference = copy.deepcopy(self.reference)
        reference["projection_sidecar_file_sha256"] = file_sha256(self.sidecar_path)
        reference["projection_sidecar_semantic_sha256"] = sidecar["semantic_sha256"]
        reference["normalized_projection_sha256"] = sidecar["normalized_projection_sha256"]
        reference["semantic_sha256"] = physical_projection_reference_semantic_sha256(
            reference
        )
        atomic_write_json(self.reference_path, reference)

    def _publish_authored_reference(self, reference: dict) -> None:
        reference["semantic_sha256"] = physical_projection_reference_semantic_sha256(
            reference
        )
        atomic_write_json(self.reference_path, reference)

    def test_valid_reference_reopens_exact_companions(self) -> None:
        validated = self.validate()
        self.assertEqual(validated.artifact["status"], "PASS")
        self.assertEqual(
            thaw_json(validated.sidecar["vehicle_assignments"]),
            self.sidecar["vehicle_assignments"],
        )

    def test_reference_top_level_mutations_fail_even_when_rehashed(self) -> None:
        for key, value in (
            ("status", "FAIL"),
            ("reasons", [{"code": "attacker"}]),
            ("record_count", True),
            ("state_path", "../escape.json"),
            ("projection_sidecar_file_sha256", "0" * 64),
            ("run_id", "other-run"),
            ("qualification", {"mode": "live_required"}),
        ):
            with self.subTest(key=key):
                mutated = copy.deepcopy(self.reference)
                mutated[key] = value
                mutated["semantic_sha256"] = physical_projection_reference_semantic_sha256(mutated)
                atomic_write_json(self.reference_path, mutated)
                with self.assertRaises(ProjectionReferenceValidationError):
                    self.validate()
        mutated = copy.deepcopy(self.reference)
        mutated["extra"] = "forbidden"
        atomic_write_json(self.reference_path, mutated)
        with self.assertRaises(ProjectionReferenceValidationError):
            self.validate()

    def test_reference_exact_type_range_status_and_hash_matrix(self) -> None:
        mutations = (
            ("schema_version", True),
            ("status", True),
            ("reasons", {}),
            ("qualification", []),
            ("run_id", True),
            ("sim_sec", 900),
            ("sim_sec", True),
            ("sim_sec", -1.0),
            ("record_count", True),
            ("record_count", 1.0),
            ("record_count", -1),
            ("assigned_count", False),
            ("stock_total", 1.0),
            ("global_residual", 0.0),
            ("state_path", True),
            ("projection_sidecar_path", []),
        )
        for field, value in mutations:
            with self.subTest(field=field, value=repr(value)):
                reference = copy.deepcopy(self.reference)
                reference[field] = value
                self._publish_authored_reference(reference)
                with self.assertRaises(ProjectionReferenceValidationError):
                    self.validate()
        hash_fields = [key for key in self.reference if key.endswith("sha256")]
        for field in hash_fields:
            with self.subTest(invalid_hash=field):
                reference = copy.deepcopy(self.reference)
                reference[field] = "A" * 64
                if field != "semantic_sha256":
                    reference["semantic_sha256"] = (
                        physical_projection_reference_semantic_sha256(reference)
                    )
                atomic_write_json(self.reference_path, reference)
                with self.assertRaises(ProjectionReferenceValidationError):
                    self.validate()
        for key in tuple(self.reference):
            with self.subTest(missing=key):
                mutated = copy.deepcopy(self.reference)
                del mutated[key]
                atomic_write_json(self.reference_path, mutated)
                with self.assertRaises(ProjectionReferenceValidationError):
                    self.validate()

    def test_sidecar_mutations_fail_even_when_rehashed(self) -> None:
        for key, value in (
            ("stock_counts", {}),
            ("vehicle_assignments", []),
            ("view_summaries", {}),
            ("projection_diagnostics", {}),
            ("normalized_projection_sha256", "0" * 64),
        ):
            with self.subTest(key=key):
                sidecar = copy.deepcopy(self.sidecar)
                sidecar[key] = value
                from src.vissim_strict.physical_projection import projection_semantic_payload
                from src.vissim_strict.topology import canonical_json_sha256
                sidecar["semantic_sha256"] = canonical_json_sha256(projection_semantic_payload(sidecar))
                atomic_write_json(self.sidecar_path, sidecar)
                reference = copy.deepcopy(self.reference)
                reference["projection_sidecar_file_sha256"] = file_sha256(self.sidecar_path)
                reference["projection_sidecar_semantic_sha256"] = sidecar["semantic_sha256"]
                reference["normalized_projection_sha256"] = sidecar["normalized_projection_sha256"]
                reference["semantic_sha256"] = physical_projection_reference_semantic_sha256(reference)
                atomic_write_json(self.reference_path, reference)
                with self.assertRaises(ProjectionReferenceValidationError):
                    self.validate()

    def test_coherently_rehashed_boolean_stock_count_is_rejected(self) -> None:
        sidecar = copy.deepcopy(self.sidecar)
        stock_id = next(key for key, count in sidecar["stock_counts"].items() if count == 1)
        sidecar["stock_counts"][stock_id] = True
        from src.vissim_strict.physical_projection import projection_semantic_payload
        from src.vissim_strict.topology import canonical_json_sha256
        sidecar["semantic_sha256"] = canonical_json_sha256(projection_semantic_payload(sidecar))
        atomic_write_json(self.sidecar_path, sidecar)
        reference = copy.deepcopy(self.reference)
        reference["projection_sidecar_file_sha256"] = file_sha256(self.sidecar_path)
        reference["projection_sidecar_semantic_sha256"] = sidecar["semantic_sha256"]
        reference["semantic_sha256"] = physical_projection_reference_semantic_sha256(reference)
        atomic_write_json(self.reference_path, reference)
        with self.assertRaises(ProjectionReferenceValidationError):
            self.validate()

    def test_nested_coherent_rehash_exact_json_type_matrix(self) -> None:
        stock_id = next(
            key for key, count in self.sidecar["stock_counts"].items() if count == 1
        )
        mutations = (
            ("assignment.sim_sec.int", lambda value: value["vehicle_assignments"][0].__setitem__("sim_sec", 900)),
            ("assignment.veh_no.bool", lambda value: value["vehicle_assignments"][0].__setitem__("veh_no", True)),
            ("assignment.position.int", lambda value: value["vehicle_assignments"][0].__setitem__("source_position_m", 50)),
            ("stock.bool", lambda value: value["stock_counts"].__setitem__(stock_id, True)),
            ("stock.float", lambda value: value["stock_counts"].__setitem__(stock_id, 1.0)),
            ("objective.bool", lambda value: value["view_summaries"]["objective_views"].__setitem__("physical_total", True)),
            ("objective.float", lambda value: value["view_summaries"]["objective_views"].__setitem__("physical_total", 1.0)),
            ("owner.int", lambda value: value["view_summaries"]["owner_partition"].__setitem__(next(iter(value["view_summaries"]["owner_partition"])), 1)),
            ("sample.bool", lambda value: value["sample_dimensions"].__setitem__("records", True)),
            ("sample.float", lambda value: value["sample_dimensions"].__setitem__("records", 1.0)),
            ("diagnostic.bool", lambda value: value["projection_diagnostics"].__setitem__("raw_record_count", True)),
            ("diagnostic.float", lambda value: value["projection_diagnostics"].__setitem__("raw_record_count", 1.0)),
            ("residual.bool", lambda value: value["projection_diagnostics"].__setitem__("global_residual", False)),
            ("residual.float", lambda value: value["projection_diagnostics"].__setitem__("global_residual", 0.0)),
            ("owner_residual.int", lambda value: value["projection_diagnostics"].__setitem__("owner_partition_residual", 0)),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                sidecar = copy.deepcopy(self.sidecar)
                mutate(sidecar)
                self._publish_authored_sidecar(sidecar)
                with self.assertRaises(ProjectionReferenceValidationError):
                    self.validate()

    def test_coherently_rehashed_mass_and_nested_shape_mutations_fail(self) -> None:
        mutations = (
            lambda value: value["stock_counts"].__setitem__(next(iter(value["stock_counts"])), 7),
            lambda value: value["vehicle_assignments"][0].__setitem__("stock_id", "stock:attacker"),
            lambda value: value["view_summaries"]["roles_nonpartitioning"].clear(),
            lambda value: value["projection_diagnostics"]["per_link_residuals"].clear(),
            lambda value: value["sample_dimensions"].__setitem__("extra", 1),
        )
        for mutate in mutations:
            with self.subTest(mutation=mutations.index(mutate)):
                sidecar = copy.deepcopy(self.sidecar)
                mutate(sidecar)
                self._publish_authored_sidecar(sidecar)
                with self.assertRaises(ProjectionReferenceValidationError):
                    self.validate()

    def test_state_run_qualification_topology_approval_and_identity_matrix(self) -> None:
        originals = {
            path: path.read_bytes()
            for path in (
                self.state_path,
                self.manifest_path,
                self.topology_path,
                self.approved_topology.approval_snapshot.path,
                self.sidecar_path,
                self.reference_path,
            )
        }

        def restore() -> None:
            for path, data in originals.items():
                path.write_bytes(data)

        cases = []

        def state_run_mismatch():
            state = copy.deepcopy(self.state)
            state["run_provenance"]["run_id"] = "other-run"
            atomic_write_json(self.state_path, state)
            reference = copy.deepcopy(self.reference)
            reference["state_file_sha256"] = file_sha256(self.state_path)
            self._publish_authored_reference(reference)

        cases.append(("state/run", state_run_mismatch))
        cases.append((
            "run-manifest",
            lambda: self.manifest_path.write_bytes(b"{}\n"),
        ))
        cases.append((
            "topology-file",
            lambda: self.topology_path.write_bytes(b"{}\n"),
        ))
        cases.append((
            "approval-file",
            lambda: self.approved_topology.approval_snapshot.path.write_bytes(b"{}\n"),
        ))

        def qualification_mismatch():
            reference = copy.deepcopy(self.reference)
            reference["qualification"] = {"mode": "live_required"}
            self._publish_authored_reference(reference)

        cases.append(("qualification", qualification_mismatch))

        def topology_semantic_mismatch():
            reference = copy.deepcopy(self.reference)
            reference["topology_semantic_sha256"] = "0" * 64
            self._publish_authored_reference(reference)

        cases.append(("topology-semantic", topology_semantic_mismatch))

        def state_path_identity_mismatch():
            reference = copy.deepcopy(self.reference)
            reference["state_path"] = reference["projection_sidecar_path"]
            self._publish_authored_reference(reference)

        cases.append(("path-identity", state_path_identity_mismatch))

        for label, mutate in cases:
            with self.subTest(label=label):
                restore()
                mutate()
                with self.assertRaises(ProjectionReferenceValidationError):
                    self.validate()

    def test_huge_integer_reference_numeric_fails_closed(self) -> None:
        reference = copy.deepcopy(self.reference)
        reference["sim_sec"] = 10**400
        reference["semantic_sha256"] = physical_projection_reference_semantic_sha256(reference)
        atomic_write_json(self.reference_path, reference)
        with self.assertRaises(ProjectionReferenceValidationError):
            self.validate()

    def test_malformed_duplicate_nonfinite_and_invalid_utf8_fail_closed(self) -> None:
        bad_reference_bytes = (
            b'{"status":"PASS","status":"PASS"}\n',
            b'{"sim_sec":NaN}\n',
            b'{"sim_sec":Infinity}\n',
            b'\xff\xfe\x00',
        )
        for data in bad_reference_bytes:
            with self.subTest(reference=data[:20]):
                self.reference_path.write_bytes(data)
                with self.assertRaises(ProjectionReferenceValidationError):
                    self.validate()
        for data in (
            b'{"status":"PASS","status":"PASS"}\n',
            b'{"sim_sec":NaN}\n',
            b'\xff',
        ):
            with self.subTest(sidecar=data[:20]):
                atomic_write_json(self.reference_path, self.reference)
                self.sidecar_path.write_bytes(data)
                with self.assertRaises(ProjectionReferenceValidationError):
                    self.validate()

    def test_bounds_are_rejected_before_opening_oversized_artifact(self) -> None:
        original_open = Path.open

        def assert_prechecked(target: Path, limit: int) -> None:
            target.write_bytes(b" " * (limit + 1))

            def guarded(path, *args, **kwargs):
                if Path(path).resolve(strict=False) == target.resolve(strict=False):
                    raise AssertionError("oversized artifact was opened")
                return original_open(path, *args, **kwargs)

            with mock.patch.object(Path, "open", guarded):
                with self.assertRaises(ProjectionReferenceValidationError):
                    self.validate()

        assert_prechecked(self.reference_path, MAX_PROJECTION_REFERENCE_BYTES)
        atomic_write_json(self.reference_path, self.reference)
        assert_prechecked(self.state_path, MAX_STATE_BYTES)
        atomic_write_json(self.state_path, self.state)
        assert_prechecked(self.sidecar_path, MAX_PROJECTION_SIDECAR_BYTES)

    def test_validation_hashes_each_exact_parsed_snapshot(self) -> None:
        targets = {
            path.resolve(): path.read_bytes()
            for path in (
                self.reference_path,
                self.manifest_path,
                self.approved_topology.approval_snapshot.path,
                self.approved_topology.lane_graph_snapshot.path,
                self.topology_path,
                self.state_path,
                self.sidecar_path,
            )
        }
        original = projection_reference_module.load_bounded_json_snapshot
        replaced: set[Path] = set()

        def replace_after_snapshot(path, *, max_bytes):
            snapshot = original(path, max_bytes=max_bytes)
            resolved = Path(path).resolve()
            if resolved in targets and resolved not in replaced:
                resolved.write_bytes(b"{}\n")
                replaced.add(resolved)
            return snapshot

        with mock.patch.object(
            projection_reference_module,
            "load_bounded_json_snapshot",
            side_effect=replace_after_snapshot,
        ):
            validated = self.validate()
        self.assertEqual(replaced, set(targets))
        self.assertEqual(
            validated.reference_file_sha256,
            hashlib.sha256(targets[self.reference_path.resolve()]).hexdigest(),
        )
        self.assertEqual(
            validated.state_snapshot.file_sha256,
            hashlib.sha256(targets[self.state_path.resolve()]).hexdigest(),
        )
        self.assertEqual(
            validated.sidecar_snapshot.file_sha256,
            hashlib.sha256(targets[self.sidecar_path.resolve()]).hexdigest(),
        )

    def test_path_spelling_escape_reparse_and_unicode_space_matrix(self) -> None:
        for field, value in (
            ("state_path", "../state.json"),
            ("state_path", self.reference["state_path"].replace("/", "\\")),
            ("state_path", self.reference["state_path"].upper()),
            ("projection_sidecar_path", "../sidecar.json"),
            ("projection_sidecar_path", self.reference["projection_sidecar_path"].replace("/", "\\")),
            ("projection_sidecar_path", self.reference["projection_sidecar_path"].upper()),
        ):
            with self.subTest(field=field, value=value):
                reference = copy.deepcopy(self.reference)
                reference[field] = value
                self._publish_authored_reference(reference)
                with self.assertRaises(ProjectionReferenceValidationError):
                    self.validate()

        link = self.sidecar_path.with_name("projection-sidecar-link.json")
        try:
            os.symlink(self.sidecar_path, link)
        except OSError:
            link = None
        if link is not None:
            reference = copy.deepcopy(self.reference)
            reference["projection_sidecar_path"] = link.relative_to(self.root).as_posix()
            self._publish_authored_reference(reference)
            with self.assertRaises(ProjectionReferenceValidationError):
                self.validate()
        else:
            atomic_write_json(self.reference_path, self.reference)
            original_is_reparse = run_evidence_module._is_reparse

            def mark_sidecar_reparse(path):
                return (
                    Path(path).resolve(strict=False)
                    == self.sidecar_path.resolve(strict=False)
                    or original_is_reparse(path)
                )

            with mock.patch.object(
                run_evidence_module,
                "_is_reparse",
                side_effect=mark_sidecar_reparse,
            ):
                with self.assertRaises(ProjectionReferenceValidationError):
                    self.validate()

        with tempfile.TemporaryDirectory() as parent_name:
            unicode_root = Path(parent_name) / "workspace with space 한글"
            unicode_root.mkdir()
            fixture = core_provenance.B1aProvenanceScriptTests("runTest")
            fixture.workspace_root_override = unicode_root
            fixture.setUp()
            state_path, manifest_path = fixture.write_selection_and_state()
            manifest_snapshot = load_bounded_json_snapshot(
                manifest_path, max_bytes=MAX_RUN_MANIFEST_BYTES
            )
            manifest = validate_run_manifest(
                manifest_snapshot.value,
                workspace_root=unicode_root,
                capture_time=900.0,
            )
            approved = load_validated_approved_topology(
                manifest, workspace_root=unicode_root
            )
            state_snapshot = load_bounded_json_snapshot(
                state_path, max_bytes=MAX_STATE_BYTES
            )
            _, _, records_hash = normalize_vehicle_records(
                state_snapshot.value, approved.topology.tolerance_m
            )
            context = {
                "topology_file_sha256": approved.topology_snapshot.file_sha256,
                "topology_semantic_sha256": approved.topology.semantic_sha256,
                "approving_manifest_sha256": approved.approval_snapshot.file_sha256,
                "state_file_sha256": state_snapshot.file_sha256,
                "vehicle_records_semantic_sha256": records_hash,
            }
            unicode_sidecar_path = state_path.with_name("projection.json")
            write_projection_sidecar(
                unicode_sidecar_path,
                project_vehicle_records(
                    approved.topology, state_snapshot.value, context
                ),
            )
            sidecar_snapshot = load_bounded_json_snapshot(
                unicode_sidecar_path, max_bytes=MAX_PROJECTION_SIDECAR_BYTES
            )
            unicode_reference_path = state_path.with_name("reference.json")
            unicode_reference = build_physical_projection_reference(
                workspace_root=unicode_root,
                run_manifest=manifest,
                run_manifest_snapshot=manifest_snapshot,
                state_snapshot=state_snapshot,
                approved_topology=approved,
                sidecar_path=unicode_sidecar_path,
                sidecar_snapshot=sidecar_snapshot,
            )
            atomic_write_json(unicode_reference_path, unicode_reference)
            validated = validate_physical_projection_reference(
                unicode_reference_path.relative_to(unicode_root).as_posix(),
                workspace_root=unicode_root,
                run_manifest_path=manifest_path.relative_to(unicode_root).as_posix(),
            )
            self.assertEqual(validated.artifact["status"], "PASS")

    def test_output_role_collision_matrix_includes_hardlink_identity(self) -> None:
        immutable = {
            "state": self.state_path,
            "manifest": self.manifest_path,
            "topology": self.topology_path,
            "approval": self.approved_topology.approval_snapshot.path,
            "adapter": Path(adapter.__file__).resolve(),
        }
        spare = self.reference_path.with_name("spare-sidecar.json")
        for role, path in immutable.items():
            with self.subTest(role=role):
                with self.assertRaises(ProjectionReferenceValidationError):
                    validate_projection_output_paths(
                        spare, path, immutable_paths=immutable
                    )
        with self.assertRaises(ProjectionReferenceValidationError):
            validate_projection_output_paths(
                spare, spare, immutable_paths=immutable
            )
        hardlink = self.reference_path.with_name("state-hardlink.json")
        os.link(self.state_path, hardlink)
        with self.assertRaises(ProjectionReferenceValidationError):
            validate_projection_output_paths(
                spare, hardlink, immutable_paths=immutable
            )

    def test_publication_validates_complete_temp_and_removes_stale_on_failure(self) -> None:
        immutable = {
            "state": self.state_path,
            "manifest": self.manifest_path,
            "topology": self.topology_path,
            "approval": self.approved_topology.approval_snapshot.path,
            "adapter": Path(adapter.__file__).resolve(),
        }
        original_replace = projection_reference_module.os.replace
        observed_reference_temp = False

        def observe_replace(source, destination):
            nonlocal observed_reference_temp
            destination_path = Path(destination).resolve(strict=False)
            if destination_path == self.reference_path.resolve(strict=False):
                self.assertFalse(self.reference_path.exists())
                temporary = strict_load_json(
                    source, max_bytes=MAX_PROJECTION_REFERENCE_BYTES
                )
                self.assertEqual(temporary["status"], "PASS")
                observed_reference_temp = True
            return original_replace(source, destination)

        with mock.patch.object(
            projection_reference_module.os, "replace", side_effect=observe_replace
        ):
            publish_projection_outputs(
                workspace_root=self.root,
                sidecar_path=self.sidecar_path,
                reference_path=self.reference_path,
                immutable_paths=immutable,
                projection_ledger=self.sidecar,
                run_manifest=self.manifest,
                run_manifest_snapshot=self.manifest_snapshot,
                state_snapshot=self.state_snapshot,
                approved_topology=self.approved_topology,
            )
        self.assertTrue(observed_reference_temp)
        self.assertEqual(self.validate().artifact["status"], "PASS")

        self.reference_path.write_bytes(b'{"status":"PASS"}\n')
        with mock.patch.object(
            projection_reference_module,
            "validate_physical_projection_reference",
            side_effect=ProjectionReferenceValidationError(["forced temp failure"]),
        ):
            with self.assertRaises(ProjectionReferenceValidationError):
                publish_projection_outputs(
                    workspace_root=self.root,
                    sidecar_path=self.sidecar_path,
                    reference_path=self.reference_path,
                    immutable_paths=immutable,
                    projection_ledger=self.sidecar,
                    run_manifest=self.manifest,
                    run_manifest_snapshot=self.manifest_snapshot,
                    state_snapshot=self.state_snapshot,
                    approved_topology=self.approved_topology,
                )
        self.assertFalse(self.reference_path.exists())

    def test_validator_uses_shared_projection_kernel(self) -> None:
        self.assertFalse(hasattr(projection_reference_module, "_expected_projection"))

    def test_action_projection_provenance_has_exact_complete_shape(self) -> None:
        validated = self.validate()
        old_root = adapter.WORKSPACE_ROOT
        adapter.WORKSPACE_ROOT = self.root
        try:
            provenance = adapter._projection_provenance(validated)
        finally:
            adapter.WORKSPACE_ROOT = old_root
        self.assertEqual(set(provenance), {
            "schema_version", "qualification", "run_id", "sim_sec",
            "run_manifest_path", "run_manifest_sha256", "state_path",
            "state_file_sha256", "topology_path", "topology_file_sha256",
            "topology_semantic_sha256", "projection_sidecar_path",
            "projection_sidecar_file_sha256", "projection_sidecar_semantic_sha256",
            "projection_reference_path", "projection_reference_file_sha256",
            "projection_reference_semantic_sha256", "normalized_projection_sha256",
            "record_count", "assigned_count", "stock_total", "global_residual",
        })

    def test_validated_assignment_constructs_model_queue_over_poisoned_legacy_count(self) -> None:
        validated = self.validate()
        old_root = adapter.WORKSPACE_ROOT
        adapter.WORKSPACE_ROOT = self.root
        try:
            state_json, projection_input = adapter._state_json_from_b1a_projection(
                validated
            )
        finally:
            adapter.WORKSPACE_ROOT = old_root
        source_link = str(validated.sidecar["vehicle_assignments"][0]["source_link_no"])
        expected_count = state_json["local_observation"]["link_counts"][source_link]
        state_json["ramp_counts"] = {"R_TEST": 999999.0}

        class FakeState:
            @classmethod
            def initial(cls, _cfg):
                value = cls()
                value.ramp_queue = {"R_TEST": 0.0}
                value.boundary_queue = {}
                value.urban_movement_queue = {}
                value.urban_link_storage = {}
                value.freeway_density = {}
                value.freeway_speed = {}
                value.freeway_flow = {}
                value.freeway_effective_lanes = {}
                return value

            def ensure_freeway_lane_profile(self, _network):
                return None

        cfg = SimpleNamespace(network=SimpleNamespace(
            freeway_links=[],
            urban_link_storage_veh={},
            urban_movements={},
            ramps=["R_TEST"],
            off_ramp_storage_link={},
        ))
        detector_mapping = {
            "link_partition": {},
            "freeway_link_to_model_link": {},
            "ramp_link_to_queues": {source_link: ["R_TEST"]},
            "link_to_origins": {},
            "link_to_movements": {},
            "boundary_link_to_queue": {},
            "agents": {},
        }
        model_state = adapter.traffic_state_from_vissim(
            state_json,
            cfg,
            FakeState,
            detector_mapping=detector_mapping,
            calibration={},
            physical_projection_input=projection_input,
        )
        self.assertEqual(model_state.ramp_queue["R_TEST"], expected_count)
        self.assertNotEqual(model_state.ramp_queue["R_TEST"], 999999.0)
        self.assertIs(model_state.physical_projection_input, projection_input)


class AdapterProjectionGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = core_provenance.B1aProvenanceScriptTests("runTest")
        self.fixture.setUp()
        self.root = self.fixture.root
        self.state_path, self.manifest_path = self.fixture.write_selection_and_state()
        self.topology_path = self.fixture.topology_path
        self.sidecar_path = self.state_path.with_name("state_000900.physical_projection_v2_1.json")
        self.reference_path = self.state_path.with_name("physical_projection_reference_v2_1.json")
        self.original_root = adapter.WORKSPACE_ROOT
        self.original_argv = sys.argv[:]
        self.original_source_check = adapter._validate_b1a_adapter_source
        self.original_project = adapter.project_vehicle_records
        self.original_repo_imports = adapter.repo_imports
        adapter.WORKSPACE_ROOT = self.root
        adapter._validate_b1a_adapter_source = lambda manifest: None

    def tearDown(self) -> None:
        adapter.WORKSPACE_ROOT = self.original_root
        adapter._validate_b1a_adapter_source = self.original_source_check
        adapter.project_vehicle_records = self.original_project
        adapter.repo_imports = self.original_repo_imports
        sys.argv = self.original_argv
        self.fixture.tearDown()

    def _projection_only(self) -> None:
        calls = 0

        def projector(*args, **kwargs):
            nonlocal calls
            calls += 1
            return self.original_project(*args, **kwargs)

        adapter.project_vehicle_records = projector
        sys.argv = [
            "adapter", "--projection-only", "--state-json", "evaluation/runs/x/state_000900.json",
            "--run-manifest", "evaluation/runs/x/run_manifest.json",
            "--approved-topology", "outputs/physical_stock_topology_v2_1.json",
            "--out-projection-sidecar", "evaluation/runs/x/state_000900.physical_projection_v2_1.json",
            "--out-projection-reference", "evaluation/runs/x/physical_projection_reference_v2_1.json",
        ]
        forbidden = (
            "repo_imports",
            "load_optional_json",
            "build_config",
            "traffic_state_from_vissim",
            "demand_from_state",
            "control_from_json",
            "apply_vissim_policy_guards",
            "build_one_step_prediction",
            "apply_post_guard_safety_evaluation",
            "write_action_csv",
        )
        with ExitStack() as stack:
            for name in forbidden:
                stack.enter_context(mock.patch.object(
                    adapter,
                    name,
                    side_effect=AssertionError(
                        f"projection-only reached forbidden entry point {name}"
                    ),
                ))
            adapter.main()
        self.assertEqual(calls, 1)
        self.assertTrue(self.sidecar_path.is_file())
        self.assertTrue(self.reference_path.is_file())

    def _assert_parser_failure_invalidates_valid_reference(
        self, *extra_args: str
    ) -> None:
        self._projection_only()
        validate_physical_projection_reference(
            self.reference_path.relative_to(self.root).as_posix(),
            workspace_root=self.root,
            run_manifest_path=self.manifest_path.relative_to(self.root).as_posix(),
        )
        sys.argv = [
            "adapter", "--projection-only",
            "--state-json", "evaluation/runs/x/state_000900.json",
            "--run-manifest", "evaluation/runs/x/run_manifest.json",
            "--approved-topology", "outputs/physical_stock_topology_v2_1.json",
            "--out-projection-sidecar", "evaluation/runs/x/state_000900.physical_projection_v2_1.json",
            "--out-projection-reference", "evaluation/runs/x/physical_projection_reference_v2_1.json",
            *extra_args,
        ]
        with self.assertRaises(SystemExit):
            adapter.main()
        self.assertFalse(self.reference_path.exists())

    def _assert_abbreviation_rejected(
        self, argv: list[str], protected_paths: tuple[Path, ...]
    ) -> None:
        originals = {path: path.read_bytes() for path in protected_paths}
        sys.argv = ["adapter", *argv]
        stderr = io.StringIO()
        with mock.patch.object(sys, "stderr", stderr):
            with self.assertRaises(SystemExit):
                adapter.main()
        self.assertIn("unrecognized arguments:", stderr.getvalue())
        for path, data in originals.items():
            self.assertEqual(path.read_bytes(), data)

    def test_projection_only_projects_once_without_action_or_numsim(self) -> None:
        self._projection_only()
        self.assertFalse((self.root / "action.json").exists())
        self.assertFalse((self.root / "action.csv").exists())

    def test_invalid_mode_parser_failure_invalidates_valid_reference(self) -> None:
        self._assert_parser_failure_invalidates_valid_reference(
            "--mode", "invalid-mode"
        )

    def test_invalid_controller_parser_failure_invalidates_valid_reference(self) -> None:
        self._assert_parser_failure_invalidates_valid_reference(
            "--controller", "invalid-controller"
        )

    def test_unknown_option_parser_failure_invalidates_valid_reference(self) -> None:
        self._assert_parser_failure_invalidates_valid_reference(
            "--unknown-projection-option"
        )

    def test_missing_option_value_parser_failure_invalidates_valid_reference(self) -> None:
        self._assert_parser_failure_invalidates_valid_reference("--mode")

    def test_split_single_dash_reference_is_rejected_and_preserved(self) -> None:
        victim_path = self.root / "-victim.json"
        stale = b'{"status":"PASS"}\n'
        victim_path.write_bytes(stale)
        sys.argv = [
            "adapter", "--projection-only",
            "--state-json", "evaluation/runs/x/state_000900.json",
            "--run-manifest", "evaluation/runs/x/run_manifest.json",
            "--approved-topology", "outputs/physical_stock_topology_v2_1.json",
            "--out-projection-sidecar", "evaluation/runs/x/state_000900.physical_projection_v2_1.json",
            "--out-projection-reference", "-victim.json",
        ]
        stderr = io.StringIO()
        with mock.patch.object(sys, "stderr", stderr):
            with self.assertRaises(SystemExit):
                adapter.main()
        self.assertIn("expected one argument", stderr.getvalue())
        self.assertTrue(victim_path.exists())
        self.assertEqual(victim_path.read_bytes(), stale)

    def test_rejected_prefix_does_not_capture_single_dash_option_token(self) -> None:
        victim_path = self.root / "-victim.json"
        victim_path.write_bytes(b'{"status":"PASS"}\n')
        sys.argv = [
            "adapter", "--projection-only",
            "--run-manifest", "evaluation/runs/x/run_manifest.json",
            "--approved-topology", "outputs/physical_stock_topology_v2_1.json",
            "--out-projection-sidecar", "evaluation/runs/x/state_000900.physical_projection_v2_1.json",
            "--out-projection-reference=-victim.json",
            "--state-j", "-victim.json",
        ]
        stderr = io.StringIO()
        with mock.patch.object(sys, "stderr", stderr):
            with self.assertRaises(SystemExit):
                adapter.main()
        self.assertIn("unrecognized arguments:", stderr.getvalue())
        self.assertFalse(victim_path.exists())

    def test_split_negative_number_reference_remains_parser_accepted(self) -> None:
        reference_path = self.root / "-1"
        reference_path.write_bytes(b'{"status":"PASS"}\n')
        sys.argv = [
            "adapter", "--projection-only",
            "--state-json", "evaluation/runs/x/state_000900.json",
            "--run-manifest", "evaluation/runs/x/run_manifest.json",
            "--approved-topology", "outputs/physical_stock_topology_v2_1.json",
            "--out-projection-sidecar", "evaluation/runs/x/state_000900.physical_projection_v2_1.json",
            "--out-projection-reference", "-1",
            "--mode", "invalid-mode",
        ]
        stderr = io.StringIO()
        with mock.patch.object(sys, "stderr", stderr):
            with self.assertRaises(SystemExit):
                adapter.main()
        self.assertIn("invalid choice", stderr.getvalue())
        self.assertFalse(reference_path.exists())

    def test_projection_only_abbreviation_is_rejected_and_preserves_reference(self) -> None:
        self._projection_only()
        self._assert_abbreviation_rejected(
            [
                "--projection-onl",
                "--state-json", "evaluation/runs/x/state_000900.json",
                "--run-manifest", "evaluation/runs/x/run_manifest.json",
                "--approved-topology", "outputs/physical_stock_topology_v2_1.json",
                "--out-projection-sidecar", "evaluation/runs/x/state_000900.physical_projection_v2_1.json",
                "--out-projection-reference", "evaluation/runs/x/physical_projection_reference_v2_1.json",
            ],
            (self.reference_path,),
        )

    def test_reference_abbreviation_is_rejected_and_preserves_reference(self) -> None:
        self._projection_only()
        self._assert_abbreviation_rejected(
            [
                "--projection-only",
                "--state-json", "evaluation/runs/x/state_000900.json",
                "--run-manifest", "evaluation/runs/x/run_manifest.json",
                "--approved-topology", "outputs/physical_stock_topology_v2_1.json",
                "--out-projection-sidecar", "evaluation/runs/x/state_000900.physical_projection_v2_1.json",
                "--out-projection-referenc=evaluation/runs/x/physical_projection_reference_v2_1.json",
            ],
            (self.reference_path,),
        )

    def test_state_abbreviation_is_rejected_and_preserves_source(self) -> None:
        self._assert_abbreviation_rejected(
            [
                "--projection-only",
                "--state-j=evaluation/runs/x/state_000900.json",
                "--run-manifest", "evaluation/runs/x/run_manifest.json",
                "--approved-topology", "outputs/physical_stock_topology_v2_1.json",
                "--out-projection-sidecar", "evaluation/runs/x/state_000900.physical_projection_v2_1.json",
                "--out-projection-reference", "evaluation/runs/x/state_000900.json",
            ],
            (self.state_path,),
        )

    def test_run_manifest_abbreviation_is_rejected_and_preserves_source(self) -> None:
        self._assert_abbreviation_rejected(
            [
                "--projection-only",
                "--state-json", "evaluation/runs/x/state_000900.json",
                "--run-manifes", "evaluation/runs/x/run_manifest.json",
                "--approved-topology", "outputs/physical_stock_topology_v2_1.json",
                "--out-projection-sidecar", "evaluation/runs/x/state_000900.physical_projection_v2_1.json",
                "--out-projection-reference", "evaluation/runs/x/run_manifest.json",
            ],
            (self.manifest_path,),
        )

    def test_topology_abbreviation_is_rejected_and_preserves_source(self) -> None:
        self._assert_abbreviation_rejected(
            [
                "--projection-only",
                "--state-json", "evaluation/runs/x/state_000900.json",
                "--run-manifest", "evaluation/runs/x/run_manifest.json",
                "--approved-topolog=outputs/physical_stock_topology_v2_1.json",
                "--out-projection-sidecar", "evaluation/runs/x/state_000900.physical_projection_v2_1.json",
                "--out-projection-reference", "outputs/physical_stock_topology_v2_1.json",
            ],
            (self.topology_path,),
        )

    def test_required_normal_rejects_reference_hash_before_numsim(self) -> None:
        self._projection_only()
        sys.argv = [
            "adapter", "--b1a-required", "--state-json", "evaluation/runs/x/state_000900.json",
            "--run-manifest", "evaluation/runs/x/run_manifest.json",
            "--projection-reference", "evaluation/runs/x/physical_projection_reference_v2_1.json",
            "--projection-reference-sha256", "0" * 64,
            "--out-action-json", "action.json", "--out-action-csv", "action.csv",
        ]
        forbidden = (
            "repo_imports", "load_optional_json", "build_config",
            "traffic_state_from_vissim", "demand_from_state", "control_from_json",
            "apply_vissim_policy_guards", "build_one_step_prediction",
            "apply_post_guard_safety_evaluation", "write_action_csv",
        )
        with ExitStack() as stack:
            for name in forbidden:
                stack.enter_context(mock.patch.object(
                    adapter,
                    name,
                    side_effect=AssertionError(
                        f"pre-trust failure reached forbidden entry point {name}"
                    ),
                ))
            with self.assertRaises(SystemExit):
                adapter.main()
        self.assertFalse((self.root / "action.json").exists())
        self.assertFalse((self.root / "action.csv").exists())

    def test_missing_projection_argument_invalidates_stale_pass_reference(self) -> None:
        stale = b'{"status":"PASS"}\n'
        self.reference_path.write_bytes(stale)
        sys.argv = [
            "adapter", "--projection-only", "--state-json", "evaluation/runs/x/state_000900.json",
            "--run-manifest", "evaluation/runs/x/run_manifest.json",
            "--out-projection-sidecar", "evaluation/runs/x/state_000900.physical_projection_v2_1.json",
            "--out-projection-reference", "evaluation/runs/x/physical_projection_reference_v2_1.json",
        ]
        with self.assertRaises(SystemExit):
            adapter.main()
        self.assertFalse(self.reference_path.exists())

    def test_reference_output_cannot_alias_state_before_invalidation(self) -> None:
        original_state = self.state_path.read_bytes()
        sys.argv = [
            "adapter", "--projection-only", "--state-json", "evaluation/runs/x/state_000900.json",
            "--run-manifest", "evaluation/runs/x/run_manifest.json",
            "--approved-topology", "outputs/physical_stock_topology_v2_1.json",
            "--out-projection-sidecar", "evaluation/runs/x/state_000900.physical_projection_v2_1.json",
            "--out-projection-reference", "evaluation/runs/x/state_000900.json",
        ]
        with self.assertRaises(SystemExit):
            adapter.main()
        self.assertEqual(self.state_path.read_bytes(), original_state)

    def test_reference_output_cannot_equal_approval_bound_a1_graph(self) -> None:
        graph_path = self.fixture.graph_path
        original_graph = graph_path.read_bytes()
        sys.argv = [
            "adapter", "--projection-only",
            "--state-json", "evaluation/runs/x/state_000900.json",
            "--run-manifest", "evaluation/runs/x/run_manifest.json",
            "--approved-topology", "outputs/physical_stock_topology_v2_1.json",
            "--out-projection-sidecar", "evaluation/runs/x/state_000900.physical_projection_v2_1.json",
            "--out-projection-reference", graph_path.relative_to(self.root).as_posix(),
        ]
        with self.assertRaises(SystemExit):
            adapter.main()
        self.assertEqual(graph_path.read_bytes(), original_graph)

    def test_reference_output_cannot_hardlink_approval_bound_a1_graph(self) -> None:
        graph_path = self.fixture.graph_path
        original_graph = graph_path.read_bytes()
        os.link(graph_path, self.reference_path)
        self.assertTrue(os.path.samefile(graph_path, self.reference_path))
        sys.argv = [
            "adapter", "--projection-only",
            "--state-json", "evaluation/runs/x/state_000900.json",
            "--run-manifest", "evaluation/runs/x/run_manifest.json",
            "--approved-topology", "outputs/physical_stock_topology_v2_1.json",
            "--out-projection-sidecar", "evaluation/runs/x/state_000900.physical_projection_v2_1.json",
            "--out-projection-reference", "evaluation/runs/x/physical_projection_reference_v2_1.json",
        ]
        with self.assertRaises(SystemExit):
            adapter.main()
        self.assertEqual(graph_path.read_bytes(), original_graph)
        self.assertTrue(os.path.samefile(graph_path, self.reference_path))

    def test_malformed_spelling_aliases_are_reserved_before_exact_resolution(self) -> None:
        cases = (
            (
                "state-case",
                "--state-json",
                "evaluation/RUNS/x/state_000900.json",
                self.state_path,
            ),
            (
                "manifest-slash",
                "--run-manifest",
                "evaluation\\runs\\x\\run_manifest.json",
                self.manifest_path,
            ),
            (
                "topology-case",
                "--approved-topology",
                "outputs/PHYSICAL_STOCK_TOPOLOGY_V2_1.json",
                self.topology_path,
            ),
        )
        defaults = {
            "--state-json": "evaluation/runs/x/state_000900.json",
            "--run-manifest": "evaluation/runs/x/run_manifest.json",
            "--approved-topology": "outputs/physical_stock_topology_v2_1.json",
        }
        originals = {path: path.read_bytes() for _, _, _, path in cases}
        for label, malformed_option, malformed_value, protected_path in cases:
            with self.subTest(label=label):
                for path, data in originals.items():
                    path.write_bytes(data)
                values = dict(defaults)
                values[malformed_option] = malformed_value
                sys.argv = [
                    "adapter", "--projection-only",
                    "--state-json", values["--state-json"],
                    "--run-manifest", values["--run-manifest"],
                    "--approved-topology", values["--approved-topology"],
                    "--out-projection-sidecar", "evaluation/runs/x/state_000900.physical_projection_v2_1.json",
                    "--out-projection-reference", protected_path.relative_to(self.root).as_posix(),
                ]
                with self.assertRaises(SystemExit):
                    adapter.main()
                self.assertEqual(protected_path.read_bytes(), originals[protected_path])

    def test_projection_sidecar_collision_invalidates_safe_stale_reference(self) -> None:
        original_manifest = self.manifest_path.read_bytes()
        self.reference_path.write_bytes(b'{"status":"PASS"}\n')
        sys.argv = [
            "adapter", "--projection-only", "--state-json", "evaluation/runs/x/state_000900.json",
            "--run-manifest", "evaluation/runs/x/run_manifest.json",
            "--approved-topology", "outputs/physical_stock_topology_v2_1.json",
            "--out-projection-sidecar", "evaluation/runs/x/run_manifest.json",
            "--out-projection-reference", "evaluation/runs/x/physical_projection_reference_v2_1.json",
        ]
        with self.assertRaises(SystemExit):
            adapter.main()
        self.assertEqual(self.manifest_path.read_bytes(), original_manifest)
        self.assertFalse(self.reference_path.exists())

    def test_projection_only_huge_integer_fails_closed_and_removes_stale_reference(self) -> None:
        state = strict_load_json(self.state_path)
        state["sim_sec"] = 10**400
        atomic_write_json(self.state_path, state)
        self.reference_path.write_bytes(b'{"status":"PASS"}\n')
        sys.argv = [
            "adapter", "--projection-only", "--state-json", "evaluation/runs/x/state_000900.json",
            "--run-manifest", "evaluation/runs/x/run_manifest.json",
            "--approved-topology", "outputs/physical_stock_topology_v2_1.json",
            "--out-projection-sidecar", "evaluation/runs/x/state_000900.physical_projection_v2_1.json",
            "--out-projection-reference", "evaluation/runs/x/physical_projection_reference_v2_1.json",
        ]
        with self.assertRaises(SystemExit) as raised:
            adapter.main()
        self.assertIn("B1a projection-only failed", str(raised.exception))
        self.assertFalse(self.reference_path.exists())

    def test_required_normal_missing_reference_stops_before_all_runtime_entry_points(self) -> None:
        sys.argv = [
            "adapter", "--b1a-required",
            "--state-json", "evaluation/runs/x/state_000900.json",
            "--out-action-json", str(self.root / "action.json"),
            "--out-action-csv", str(self.root / "action.csv"),
        ]
        forbidden = (
            "repo_imports", "load_optional_json", "build_config",
            "traffic_state_from_vissim", "demand_from_state", "control_from_json",
            "apply_vissim_policy_guards", "build_one_step_prediction",
            "apply_post_guard_safety_evaluation", "write_action_csv",
        )
        with ExitStack() as stack:
            for name in forbidden:
                stack.enter_context(mock.patch.object(
                    adapter, name,
                    side_effect=AssertionError(
                        f"missing trust input reached forbidden entry point {name}"
                    ),
                ))
            with self.assertRaises(SystemExit):
                adapter.main()

    def test_required_normal_consumes_validated_ledger_and_serializes_fallback_provenance(self) -> None:
        poisoned_state = strict_load_json(self.state_path)
        poisoned_state["local_observation"] = {
            "link_counts": {"legacy-poison": 999999},
            "link_speeds_kph": {"legacy-poison": 999999.0},
        }
        poisoned_state["physical_projection"] = {"attacker": "legacy bypass"}
        poisoned_state["urban_vehicles"] = 999999.0
        atomic_write_json(self.state_path, poisoned_state)
        self._projection_only()
        expected_reference_hash = file_sha256(self.reference_path)
        validated = validate_physical_projection_reference(
            self.reference_path.relative_to(self.root).as_posix(),
            workspace_root=self.root,
            run_manifest_path=self.manifest_path.relative_to(self.root).as_posix(),
            expected_reference_file_sha256=expected_reference_hash,
        )

        mapping_path = self.root / "inputs/action mapping 한글.json"
        detector_path = self.root / "inputs/detector.json"
        calibration_path = self.root / "inputs/calibration.json"
        atomic_write_json(mapping_path, {
            "segments": [{
                "segment_id": "EB_S0_W_EXT_ENTRY",
                "link": 1,
                "dsd_by_lane": {"1": {"dsd_no": 101}},
            }],
            "signals": [{"id": "A", "sc_no": 1}],
            "ramp_meters": [{"id": "meter-1"}],
        })
        atomic_write_json(detector_path, {})
        atomic_write_json(calibration_path, {})
        out_json = self.root / "evaluation/runs/x/action.json"
        out_csv = self.root / "evaluation/runs/x/action.csv"

        class FakeControl:
            def __init__(self):
                self.N_P_star = 0.0
                self.N_UF_star = 0.0
                self.ramp_metering = {}
                self.vsl = {}
                self.green_times = {}
                self.offsets = {}
                self.inflow_outflow_allocation = {}
                self.diagnostics = {}

            @classmethod
            def fixed(cls, _cfg):
                return cls()

            @classmethod
            def uncontrolled(cls, _cfg):
                return cls()

        class RaisingController:
            def __init__(self, _cfg):
                raise RuntimeError("forced controller fallback")

        cfg = SimpleNamespace(
            mpc=SimpleNamespace(
                horizon_steps=1,
                control_horizon_steps=1,
                max_nash_iter=1,
                follower_solver_mode="two_block",
            ),
            freeway_follower=SimpleNamespace(
                vsl_set=[60.0, 100.0, 120.0],
                horizon_beam_width=1,
                horizon_ramp_candidate_limit=1,
                horizon_vsl_candidate_limit_per_link=1,
            ),
            network=SimpleNamespace(
                urban_link_storage_veh={},
                lost_time=0.0,
                movement_capacity_veh_h=0.0,
                boundary_queue_max_veh=0.0,
                ramp_queue_max_veh=0.0,
                ramp_capacity_veh_h={},
                off_ramp_storage_link={},
            ),
        )
        captured: dict[str, object] = {}

        def consume_state(
            state_json,
            _cfg,
            _traffic_state,
            detector_mapping=None,
            calibration=None,
            physical_projection_input=None,
        ):
            captured["state_json"] = copy.deepcopy(state_json)
            captured["projection_input"] = physical_projection_input
            return SimpleNamespace()

        adapter.project_vehicle_records = mock.Mock(
            side_effect=AssertionError("normal mode reprojected")
        )
        sys.argv = [
            "adapter",
            "--b1a-required",
            "--state-json", "evaluation/runs/x/state_000900.json",
            "--run-manifest", "evaluation/runs/x/run_manifest.json",
            "--projection-reference", "evaluation/runs/x/physical_projection_reference_v2_1.json",
            "--projection-reference-sha256", expected_reference_hash,
            "--out-action-json", str(out_json),
            "--out-action-csv", str(out_csv),
            "--mapping-json", str(mapping_path),
            "--detector-mapping-json", str(detector_path),
            "--calibration-json", str(calibration_path),
            "--repo-root", str(self.root),
        ]
        patches = (
            mock.patch.object(adapter, "repo_imports", return_value=(
                RaisingController, object, FakeControl, object, object,
                lambda *_args: 100.0,
            )),
            mock.patch.object(adapter, "build_config", return_value=cfg),
            mock.patch.object(adapter, "traffic_state_from_vissim", side_effect=consume_state),
            mock.patch.object(adapter, "demand_from_state", return_value=[]),
            mock.patch.object(adapter, "control_from_json", side_effect=lambda _p, _c, action: action.fixed(_c)),
            mock.patch.object(adapter, "adapter_actuation_settings", return_value={}),
            mock.patch.object(adapter, "install_adapter_calibration_fingerprints", return_value={}),
            mock.patch.object(adapter, "install_vissim_calibration_runtime_patches", return_value={}),
            mock.patch.object(adapter, "install_vsl_metanet_rollout_runtime_patch", return_value={}),
            mock.patch.object(adapter, "install_monitor_fixed_signal_runtime_patch", return_value={}),
            mock.patch.object(adapter, "install_local_observation_runtime_guards", return_value=None),
            mock.patch.object(adapter, "summarize_model_state", return_value={}),
            mock.patch.object(adapter, "prediction_error_from_previous", return_value={}),
            mock.patch.object(adapter, "build_run_provenance", return_value={}),
            mock.patch.object(adapter, "apply_vissim_policy_guards", side_effect=lambda control, *_args: (control, {})),
            mock.patch.object(adapter, "apply_actuation_guards_to_control", return_value={}),
            mock.patch.object(adapter, "build_one_step_prediction", return_value={"status": "ok", "wall_sec": 0.0}),
            mock.patch.object(adapter, "apply_post_guard_safety_evaluation", side_effect=lambda control, *_args: (control, {}, _args[-1])),
            mock.patch.object(adapter, "physical_ramp_actions", return_value={}),
            mock.patch.object(adapter, "real_world_ramp_meter_actions", return_value={
                "meter-1": {
                    "sc_no": 6.0,
                    "rate_vph": 500.0,
                    "green_sec": 10.0,
                    "model_ramp_key": "R_D_W",
                    "group_rate_vph": 500.0,
                },
            }),
        )
        with ExitStack() as stack:
            for item in patches:
                stack.enter_context(item)
            adapter.main()

        adapter.project_vehicle_records.assert_not_called()
        consumed_state = captured["state_json"]
        self.assertNotIn(
            "legacy-poison", consumed_state["local_observation"]["link_counts"]
        )
        self.assertEqual(
            consumed_state["physical_projection"], thaw_json(validated.sidecar)
        )
        projection_input = captured["projection_input"]
        self.assertEqual(
            thaw_json(projection_input["ledger"]), thaw_json(validated.sidecar)
        )

        action_json = json.loads(out_json.read_text(encoding="utf-8"))
        provenance = action_json["physical_projection_provenance"]
        self.assertEqual(
            set(provenance),
            {
                "schema_version", "qualification", "run_id", "sim_sec",
                "run_manifest_path", "run_manifest_sha256", "state_path",
                "state_file_sha256", "topology_path", "topology_file_sha256",
                "topology_semantic_sha256", "projection_sidecar_path",
                "projection_sidecar_file_sha256", "projection_sidecar_semantic_sha256",
                "projection_reference_path", "projection_reference_file_sha256",
                "projection_reference_semantic_sha256", "normalized_projection_sha256",
                "record_count", "assigned_count", "stock_total", "global_residual",
            },
        )
        self.assertEqual(action_json["metadata"]["controller_status"], "fallback_fixed")
        with out_csv.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertGreater(len(rows), 0)
        self.assertEqual({row["kind"] for row in rows}, {"vsl", "signal", "ramp_meter"})
        for row in rows:
            csv_metadata = json.loads(row["metadata"])
            self.assertEqual(csv_metadata["controller_status"], "fallback_fixed")
            self.assertEqual(
                csv_metadata["physical_projection_provenance"], provenance
            )


if __name__ == "__main__":
    unittest.main()
