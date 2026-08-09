#!/usr/bin/env python3
# 런 디렉터리의 state 파일을 열거해 state-selection-v2.1 을 만드는 생산자 (v3 N0-4)
"""Produce `state-selection-v2.1` from the states a run actually wrote.

`build_state_manifest_v2_1.py` consumes this artifact but nothing in the repository
produced it - only test fixtures fabricated one. This closes that gap.

The consumer owns the contract. This module deliberately does not re-implement the
validation rules; it builds the artifact and then calls `validate_state_selection`
so a malformed selection fails here rather than downstream.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping


SCRIPT_ROOT = Path(__file__).resolve().parent
PLANT_ROOT = SCRIPT_ROOT.parent / "plant"
for _search_root in (SCRIPT_ROOT, PLANT_ROOT):
    if str(_search_root) not in sys.path:
        sys.path.insert(0, str(_search_root))

from build_state_manifest_v2_1 import (  # noqa: E402
    SELECTION_DOWNSTREAM_CONSUMERS,
    SELECTION_SCHEMA_VERSION,
    SELECTION_UNITS,
    StateManifestValidationError,
    _entry_sort_key,
    _reason,
    file_sha256,
    selection_semantic_payload,
    validate_state_selection,
    workspace_relative_path,
)
from src.vissim_strict.topology import canonical_json_sha256  # noqa: E402


# 런이 쓰는 state 파일만 고른다. sidecar 는 state 의 형제로 `state_` 접두사를 물려받으므로
# `state_*.json` 으로 훑으면 함께 걸린다(감사 쪽에서 같은 문제를 겪었다).
# 여기서는 정규식으로 `state_<정수>.json` 만 받아 구조적으로 배제한다.
STATE_FILE_PATTERN = re.compile(r"^state_(\d+)\.json$")


def discover_state_files(run_directory: Path) -> list[Path]:
    return sorted(
        item
        for item in run_directory.iterdir()
        if item.is_file() and STATE_FILE_PATTERN.fullmatch(item.name)
    )


def _read_identity(state_path: Path) -> tuple[str, float]:
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise StateManifestValidationError(
            [_reason("aggregate_mismatch", f"{state_path.name}: unreadable state: {exc}")]
        ) from exc
    provenance = payload.get("run_provenance") if isinstance(payload, Mapping) else None
    if not isinstance(provenance, Mapping) or not isinstance(provenance.get("run_id"), str):
        raise StateManifestValidationError(
            [_reason("aggregate_mismatch", f"{state_path.name}: missing run_provenance.run_id")]
        )
    sim_sec = payload.get("sim_sec")
    if isinstance(sim_sec, bool) or not isinstance(sim_sec, (int, float)):
        raise StateManifestValidationError(
            [_reason("aggregate_mismatch", f"{state_path.name}: invalid sim_sec")]
        )
    return str(provenance["run_id"]), float(sim_sec)


def build_selection(
    *,
    workspace_root: Path,
    run_directory: Path,
    run_manifest_path: Path,
    campaign_id: str,
    required_vehicle_records: bool = True,
    state_paths: Iterable[Path] | None = None,
) -> dict[str, Any]:
    root = Path(workspace_root).resolve()
    run_dir = Path(run_directory).resolve()
    manifest_path = Path(run_manifest_path).resolve()
    if not manifest_path.is_file():
        raise StateManifestValidationError(
            [_reason("aggregate_mismatch", f"run manifest is missing: {manifest_path}")]
        )
    discovered = list(state_paths) if state_paths is not None else discover_state_files(run_dir)
    if not discovered:
        raise StateManifestValidationError(
            [_reason("aggregate_mismatch", f"no state files under {run_dir}")]
        )

    manifest_relative = workspace_relative_path(root, manifest_path)
    entries: list[dict[str, Any]] = []
    for state_path in discovered:
        run_id, sim_sec = _read_identity(state_path)
        entries.append({
            "run_manifest_path": manifest_relative,
            "state_path": workspace_relative_path(root, state_path.resolve()),
            "run_id": run_id,
            "sim_sec": sim_sec,
            "required_vehicle_records": bool(required_vehicle_records),
        })
    # 소비자가 entries == sorted(entries, key=_entry_sort_key) 를 요구한다.
    entries.sort(key=_entry_sort_key)

    selection: dict[str, Any] = {
        "schema_version": SELECTION_SCHEMA_VERSION,
        "input_hashes": {"run_manifest_file_sha256": file_sha256(manifest_path)},
        "command_version": {"producer": "build_state_selection_v2_1"},
        "status": "PASS",
        "reasons": [],
        "sample_dimensions": {"entries": len(entries)},
        "units": dict(SELECTION_UNITS),
        "downstream_consumers": list(SELECTION_DOWNSTREAM_CONSUMERS),
        "campaign_id": campaign_id,
        "expected_entry_count": len(entries),
        "entries": entries,
        "semantic_sha256": "",
    }
    selection["semantic_sha256"] = canonical_json_sha256(selection_semantic_payload(selection))

    # 계약 소유자는 소비자다. 잘못된 selection 은 여기서 죽어야 한다.
    validate_state_selection(selection, workspace_root=root)
    return selection


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build state-selection-v2.1 from a run directory")
    parser.add_argument("--workspace-root", required=True, type=Path)
    parser.add_argument("--run-directory", required=True, type=Path)
    parser.add_argument("--run-manifest", required=True, type=Path)
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--optional-vehicle-records",
        action="store_true",
        help="mark every entry as not requiring a vehicle_records envelope",
    )
    args = parser.parse_args(argv)

    try:
        selection = build_selection(
            workspace_root=args.workspace_root,
            run_directory=args.run_directory,
            run_manifest_path=args.run_manifest,
            campaign_id=args.campaign_id,
            required_vehicle_records=not args.optional_vehicle_records,
        )
    except StateManifestValidationError as exc:
        print(json.dumps({"status": "FAIL", "reasons": exc.issues}, ensure_ascii=False))
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(selection, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        "status=%s entries=%d semantic=%s"
        % (selection["status"], len(selection["entries"]), selection["semantic_sha256"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
