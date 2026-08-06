from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "validate_sc12_shared_lane.py"
SPEC = importlib.util.spec_from_file_location("validate_sc12_shared_lane", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

PLANT_ROOT = REPO_ROOT / "plant"
sys.path.insert(0, str(PLANT_ROOT))
from src.vissim_strict.compiler import compile_network  # noqa: E402


REAL_NETWORK = (
    REPO_ROOT
    / "network"
    / "real_world_gaepo_modi"
    / "modi_eval_rw_control.inpx"
)


class ValidateSc12SharedLaneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.reference = compile_network(REAL_NETWORK)
        cls.reference_path = cls.root / "signal_reference_v2_1.json"
        cls.reference_path.write_text(
            json.dumps(cls.reference, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def write_mutation(self, payload: object, name: str) -> Path:
        path = self.root / name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    @staticmethod
    def sc12(payload: dict[str, object]) -> dict[str, object]:
        schedules = payload["schedules"]["fixed"]  # type: ignore[index]
        return next(item for item in schedules if item["controller_no"] == "12")

    def test_real_compiler_reference_proves_shared_lane_contract(self) -> None:
        result = validator.validate_reference(self.reference_path)

        self.assertEqual(result["schema_version"], "sc12-shared-lane-v2.1")
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["complete"])
        self.assertEqual(result["reasons"], [])
        for key in (
            "input_hashes",
            "command_version",
            "generated_at_utc",
            "sample_dimensions",
            "units",
            "downstream_consumers",
            "summary",
            "checks",
        ):
            self.assertIn(key, result)
        self.assertEqual(
            result["input_hashes"]["reference_sha256"],
            validator._sha256_file(self.reference_path),
        )
        self.assertEqual(result["sample_dimensions"]["timeline_pair_comparisons"], 6)
        self.assertEqual(result["sample_dimensions"]["target_connectors"], 4)
        self.assertEqual(result["sample_dimensions"]["resolved_target_connectors"], 4)

        connector_evidence = result["checks"]["connector_lane_mapping"]["evidence"]["connectors"]
        self.assertEqual(
            connector_evidence["10241"]["actual"],
            {
                "lane_count": 2,
                "from_endpoint": {
                    "link_no": "1220012103",
                    "lane_no": 1,
                    "lane_id": "lane:1220012103:1",
                },
                "to_endpoint": {
                    "link_no": "1220013700",
                    "lane_no": 1,
                    "lane_id": "lane:1220013700:1",
                },
                "connector_lane_ids": ["lane:10241:1", "lane:10241:2"],
                "lane_mapping": [
                    {
                        "from_lane_id": "lane:1220012103:1",
                        "connector_lane_id": "lane:10241:1",
                        "to_lane_id": "lane:1220013700:1",
                    },
                    {
                        "from_lane_id": "lane:1220012103:2",
                        "connector_lane_id": "lane:10241:2",
                        "to_lane_id": "lane:1220013700:2",
                    },
                ],
            },
        )
        self.assertEqual(
            connector_evidence["10242"]["actual"]["to_endpoint"]["lane_id"],
            "lane:1220015100:3",
        )
        self.assertEqual(
            connector_evidence["10238"]["actual"]["lane_mapping"][1],
            {
                "from_lane_id": "lane:1220013600:2",
                "connector_lane_id": "lane:10238:2",
                "to_lane_id": "lane:1220012003:2",
            },
        )
        self.assertEqual(
            connector_evidence["10240"]["actual"]["to_endpoint"]["lane_id"],
            "lane:1220012600:3",
        )

        contract = result["physical_stock_contract"]
        self.assertFalse(contract["movement_queue_duplication_allowed"])
        self.assertEqual(len(contract["stocks"]), 4)
        self.assertEqual(
            contract["stocks"]["lane:1220012103:2"]["movements"],
            ["movement:10241", "movement:10242"],
        )
        self.assertEqual(
            contract["stocks"]["lane:1220013600:2"]["movements"],
            ["movement:10238", "movement:10240"],
        )
        self.assertEqual(result["profile_bundle_policy"]["scope"], "current_profile_bundle_policy")
        self.assertFalse(result["profile_bundle_policy"]["physical_invariant"])
        self.assertTrue(
            all(
                item["raw_ms_timeline_equal"]
                for item in result["checks"]["profile_timeline_policy"]["evidence"]["comparisons"]
            )
        )

    def test_mutated_head_assignment_fails(self) -> None:
        payload = copy.deepcopy(self.reference)
        schedule = self.sc12(payload)
        head = next(item for item in schedule["signal_heads"] if item["vissim_no"] == "50201")
        head["sg_no"] = 2
        path = self.write_mutation(payload, "bad_head.json")

        result = validator.validate_reference(path)

        self.assertEqual(result["status"], "FAIL")
        check = result["checks"]["head_assignments"]
        self.assertEqual(check["status"], "FAIL")
        self.assertIn("head 50201 assignment mismatch", check["evidence"]["reasons"])

    def test_mutated_connector_lane_mapping_fails_stock_proof(self) -> None:
        payload = copy.deepcopy(self.reference)
        connector = next(item for item in payload["connectors"] if item["vissim_no"] == "10242")
        connector["lane_mapping"][0]["from_lane_id"] = "lane:1220012103:1"
        path = self.write_mutation(payload, "bad_connector.json")

        result = validator.validate_reference(path)

        self.assertEqual(result["checks"]["connector_lane_mapping"]["status"], "FAIL")
        self.assertEqual(result["checks"]["physical_stock_contract"]["status"], "FAIL")
        self.assertIn(
            "connector 10242 exact topology contract mismatch",
            result["checks"]["connector_lane_mapping"]["evidence"]["reasons"],
        )

    def test_mutated_connector_lane_id_fails_with_same_upstream_stock(self) -> None:
        payload = copy.deepcopy(self.reference)
        connector = next(item for item in payload["connectors"] if item["vissim_no"] == "10241")
        connector["lane_mapping"][1]["connector_lane_id"] = "lane:10241:99"
        path = self.write_mutation(payload, "bad_connector_lane_id.json")

        result = validator.validate_reference(path)

        check = result["checks"]["connector_lane_mapping"]
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(check["status"], "FAIL")
        self.assertEqual(result["checks"]["physical_stock_contract"]["status"], "PASS")
        self.assertIn(
            "connector 10241 exact topology contract mismatch",
            check["evidence"]["reasons"],
        )

    def test_mutated_downstream_lane_fails_with_same_upstream_stock(self) -> None:
        payload = copy.deepcopy(self.reference)
        connector = next(item for item in payload["connectors"] if item["vissim_no"] == "10240")
        connector["lane_mapping"][0]["to_lane_id"] = "lane:1220012600:2"
        path = self.write_mutation(payload, "bad_downstream_lane.json")

        result = validator.validate_reference(path)

        check = result["checks"]["connector_lane_mapping"]
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(check["status"], "FAIL")
        self.assertEqual(result["checks"]["physical_stock_contract"]["status"], "PASS")
        self.assertIn(
            "connector 10240 exact topology contract mismatch",
            check["evidence"]["reasons"],
        )

    def test_mutated_lane_count_and_destination_endpoint_fail(self) -> None:
        payload = copy.deepcopy(self.reference)
        connector = next(item for item in payload["connectors"] if item["vissim_no"] == "10238")
        connector["lane_count"] = 1
        connector["to_endpoint"]["lane_id"] = "lane:1220019999:1"
        path = self.write_mutation(payload, "bad_count_and_destination.json")

        result = validator.validate_reference(path)

        check = result["checks"]["connector_lane_mapping"]
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(check["status"], "FAIL")
        self.assertIn(
            "connector 10238 exact topology contract mismatch",
            check["evidence"]["reasons"],
        )

    def test_mutated_raw_ms_timeline_fails_profile_policy(self) -> None:
        payload = copy.deepcopy(self.reference)
        schedule = self.sc12(payload)
        program = next(item for item in schedule["programs"] if item["active_prog_no"] == 2)
        program["sg_timelines"]["5"]["commands"][0]["begin_ms"] += 1
        path = self.write_mutation(payload, "bad_timeline.json")

        result = validator.validate_reference(path)

        check = result["checks"]["profile_timeline_policy"]
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(check["status"], "FAIL")
        self.assertFalse(check["evidence"]["physical_invariant"])
        self.assertIn(
            "program 2 SG2 and SG5 raw-ms timelines differ",
            check["evidence"]["reasons"],
        )

    def test_missing_connector_is_not_evaluated(self) -> None:
        payload = copy.deepcopy(self.reference)
        payload["connectors"] = [
            item for item in payload["connectors"] if item["vissim_no"] != "10240"
        ]
        path = self.write_mutation(payload, "missing_connector.json")

        result = validator.validate_reference(path)

        self.assertEqual(result["status"], "NOT_EVALUATED")
        self.assertFalse(result["complete"])
        self.assertEqual(result["checks"]["connector_lane_mapping"]["status"], "NOT_EVALUATED")
        self.assertEqual(result["checks"]["physical_stock_contract"]["status"], "NOT_EVALUATED")
        self.assertEqual(result["sample_dimensions"]["target_connectors"], 4)
        self.assertEqual(result["sample_dimensions"]["resolved_target_connectors"], 3)

    def test_cli_strict_and_require_complete_exit_contract(self) -> None:
        valid_out = self.root / "valid_output.json"
        self.assertEqual(
            validator.main(
                [
                    "--reference",
                    str(self.reference_path),
                    "--out",
                    str(valid_out),
                    "--strict",
                    "--require-complete",
                ]
            ),
            0,
        )
        self.assertEqual(json.loads(valid_out.read_text(encoding="utf-8"))["status"], "PASS")

        missing_out = self.root / "missing_output.json"
        self.assertEqual(
            validator.main(
                [
                    "--reference",
                    str(self.root / "does_not_exist.json"),
                    "--out",
                    str(missing_out),
                    "--strict",
                    "--require-complete",
                ]
            ),
            3,
        )
        self.assertEqual(
            json.loads(missing_out.read_text(encoding="utf-8"))["status"],
            "NOT_EVALUATED",
        )

    def test_atomic_writer_preserves_existing_output_on_replace_failure(self) -> None:
        output = self.root / "atomic.json"
        output.write_text("sentinel", encoding="utf-8")

        with mock.patch.object(validator.os, "replace", side_effect=OSError("replace failed")):
            with self.assertRaises(OSError):
                validator.atomic_write_json(output, {"status": "PASS"})

        self.assertEqual(output.read_text(encoding="utf-8"), "sentinel")
        self.assertEqual(list(self.root.glob(".atomic.json.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
