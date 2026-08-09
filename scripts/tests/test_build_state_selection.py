# v3 N0-4 - state-selection-v2.1 생산자의 계약 준수를 소비자로 직접 검증하는 테스트
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
for search_root in (REPO / "scripts", REPO / "plant"):
    if str(search_root) not in sys.path:
        sys.path.insert(0, str(search_root))

from build_state_manifest_v2_1 import (  # noqa: E402
    SELECTION_FIELDS,
    StateManifestValidationError,
    validate_state_selection,
)
from build_state_selection_v2_1 import build_selection, main as selection_main  # noqa: E402


RUN_ID = "run-n04"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def make_workspace(root: Path, sim_secs=(900.0, 60.0, 1500.0)) -> tuple[Path, Path]:
    """run 디렉터리에 state 파일과 run manifest 를 만든다. sim_sec 순서는 일부러 뒤섞는다."""
    run_dir = root / "evaluation" / "runs" / "campaign-n04"
    manifest_path = run_dir / "run_manifest.json"
    write_json(manifest_path, {"schema_version": "run-manifest-v2.1", "run_id": RUN_ID})
    for sim_sec in sim_secs:
        write_json(
            run_dir / ("state_%06d.json" % int(sim_sec)),
            {
                "run_provenance": {"run_id": RUN_ID},
                "sim_sec": sim_sec,
                "total_vehicles": 0,
                "stopped_vehicles": 0,
            },
        )
    # sidecar 는 state 로 세면 안 된다.
    write_json(run_dir / "state_000900.physical_projection_v2_1.json", {"status": "PASS"})
    write_json(run_dir / "state_000900.vehicle_capture_v2_1.json", {"status": "PASS"})
    return run_dir, manifest_path


class BuildStateSelectionTests(unittest.TestCase):
    def test_producer_output_is_accepted_by_the_consumer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir, manifest_path = make_workspace(root)
            selection = build_selection(
                workspace_root=root,
                run_directory=run_dir,
                run_manifest_path=manifest_path,
                campaign_id="campaign-n04",
                required_vehicle_records=True,
            )
            self.assertEqual(set(selection), SELECTION_FIELDS)
            self.assertEqual(selection["status"], "PASS")
            self.assertEqual(selection["reasons"], [])
            # 소비자가 그대로 받아들여야 한다. 이것이 이 생산자의 유일한 존재 이유다.
            normalized = validate_state_selection(selection, workspace_root=root)
            self.assertEqual(len(normalized), 3)
            self.assertEqual([entry["sim_sec"] for entry in normalized], [60.0, 900.0, 1500.0])
            self.assertTrue(all(entry["run_id"] == RUN_ID for entry in normalized))
            self.assertTrue(all(entry["required_vehicle_records"] for entry in normalized))

    def test_sidecars_are_not_selected_as_states(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir, manifest_path = make_workspace(root)
            selection = build_selection(
                workspace_root=root,
                run_directory=run_dir,
                run_manifest_path=manifest_path,
                campaign_id="campaign-n04",
                required_vehicle_records=False,
            )
            paths = [entry["state_path"] for entry in selection["entries"]]
            self.assertEqual(len(paths), 3)
            self.assertTrue(all(path.endswith((".json",)) for path in paths))
            self.assertFalse([p for p in paths if "physical_projection" in p or "vehicle_capture" in p])

    def test_state_without_run_provenance_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir, manifest_path = make_workspace(root)
            write_json(run_dir / "state_002100.json", {"sim_sec": 2100.0})
            with self.assertRaises(StateManifestValidationError):
                build_selection(
                    workspace_root=root,
                    run_directory=run_dir,
                    run_manifest_path=manifest_path,
                    campaign_id="campaign-n04",
                    required_vehicle_records=True,
                )

    def test_cli_writes_a_consumer_valid_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir, manifest_path = make_workspace(root)
            out = root / "outputs" / "state_selection_v2_1.json"
            code = selection_main([
                "--workspace-root", str(root),
                "--run-directory", str(run_dir),
                "--run-manifest", str(manifest_path),
                "--campaign-id", "campaign-n04",
                "--out", str(out),
            ])
            self.assertEqual(code, 0)
            selection = json.loads(out.read_text(encoding="utf-8"))
            validate_state_selection(selection, workspace_root=root)


if __name__ == "__main__":
    unittest.main()
