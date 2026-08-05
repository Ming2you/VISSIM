from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "generate_real_world_distributed_players.py"
SPEC = importlib.util.spec_from_file_location("generate_real_world_distributed_players", MODULE_PATH)
assert SPEC and SPEC.loader
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)


class TopologyGenerationGuardTests(unittest.TestCase):
    def test_clear_assignment_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "assignment.json"
            payload = {"tie_status": "CLEAR", "unresolved_tie_count": 0}
            path.write_text(json.dumps(payload), encoding="utf-8")
            evidence = generator.validate_link_assignment(path, payload, None)
            self.assertEqual(evidence["status"], "clear")

    def test_legacy_or_unresolved_assignment_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "assignment.json"
            payload = {"link_owner": {"1": "SC1"}}
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(SystemExit):
                generator.validate_link_assignment(path, payload, None)

    def test_override_is_bound_to_assignment_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "assignment.json"
            payload = {"tie_status": "UNRESOLVED", "unresolved_tie_count": 1}
            path.write_text(json.dumps(payload), encoding="utf-8")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            approval_path = root / "approval.json"
            approval_path.write_text(
                json.dumps(
                    {
                        "approved": True,
                        "assignment_sha256": digest,
                        "approved_by": "test-reviewer",
                        "reason": "regression fixture",
                    }
                ),
                encoding="utf-8",
            )
            evidence = generator.validate_link_assignment(path, payload, approval_path)
            self.assertEqual(evidence["status"], "approved_override")

            path.write_text(json.dumps({**payload, "changed": True}), encoding="utf-8")
            with self.assertRaises(SystemExit):
                generator.validate_link_assignment(path, {**payload, "changed": True}, approval_path)


if __name__ == "__main__":
    unittest.main()
