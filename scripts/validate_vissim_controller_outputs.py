from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


DECISION_FILE_RE = re.compile(r"^action_(\d+)\.(csv|json)$")


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        return [], []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def to_float(value: Any, default: float = math.nan) -> float:
    try:
        if value is None or value == "":
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def sec_from_value(value: Any) -> int | None:
    sec = to_float(value)
    if not math.isfinite(sec):
        return None
    rounded = int(round(sec))
    if abs(sec - rounded) <= 1.0e-6:
        return rounded
    return None


def sec_from_decision_path(path: Path) -> int | None:
    match = DECISION_FILE_RE.match(path.name)
    return int(match.group(1)) if match else None


def values_equal(left: Any, right: Any) -> bool:
    ltext = "" if left is None else str(left).strip()
    rtext = "" if right is None else str(right).strip()
    if ltext == rtext:
        return True
    lnum = to_float(ltext)
    rnum = to_float(rtext)
    if math.isfinite(lnum) and math.isfinite(rnum):
        return abs(lnum - rnum) <= 1.0e-6
    return False


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relpath(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def file_record(path: Path, root: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {"path": relpath(path, root), "exists": False}
    return {
        "path": relpath(path, root),
        "exists": True,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def add_check(checks: list[dict[str, Any]], ok: bool, code: str, message: str, **details: Any) -> None:
    item = {"ok": bool(ok), "code": code, "message": message}
    item.update(details)
    checks.append(item)


def expected_decision_count(sim_period_sec: float | None, control_interval_sec: float | None) -> int | None:
    if sim_period_sec is None or control_interval_sec is None:
        return None
    if sim_period_sec <= 0.0 or control_interval_sec <= 0.0:
        return None
    return int(math.floor(sim_period_sec / control_interval_sec)) + 1


def parse_log_sim_sec(text: str) -> float | None:
    matches = re.findall(r"^SIM_SEC=([0-9.]+)\s*$", text, flags=re.MULTILINE)
    if not matches:
        return None
    value = to_float(matches[-1])
    return value if math.isfinite(value) else None


def load_json(path: Path, checks: list[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        add_check(checks, False, "json_read", f"{path.name}: {type(exc).__name__}")
        return None
    return raw if isinstance(raw, dict) else {}


def case_paths(run_dir: Path, case: str) -> dict[str, Path]:
    if case:
        return {
            "state_csv": run_dir / f"state_{case}.csv",
            "action_csv": run_dir / f"action_{case}.csv",
            "decision_dir": run_dir / f"decisions_{case}",
            "runlog": run_dir / f"runlog_{case}.txt",
        }
    return {
        "state_csv": run_dir / "state.csv",
        "action_csv": run_dir / "action.csv",
        "decision_dir": run_dir / "decisions",
        "runlog": run_dir / "runlog.txt",
    }


def discover_cases(run_dir: Path, requested: list[str]) -> list[str]:
    if requested:
        return requested
    names = sorted(path.stem[len("state_") :] for path in run_dir.glob("state_*.csv"))
    if names:
        return names
    if (run_dir / "state.csv").exists():
        return [""]
    return []


def collect_manifest_files(paths: dict[str, Path]) -> list[Path]:
    files = [paths["state_csv"], paths["action_csv"], paths["runlog"]]
    decision_dir = paths["decision_dir"]
    if decision_dir.exists():
        files.extend(sorted(decision_dir.glob("action_*.json")))
        files.extend(sorted(decision_dir.glob("action_*.csv")))
    return files


def validate_case(
    run_dir: Path,
    case: str,
    sim_period_sec: float | None,
    control_interval_sec: float | None,
    expected_decisions: int | None,
    expect_prediction_errors: str,
    root: Path,
) -> dict[str, Any]:
    paths = case_paths(run_dir, case)
    checks: list[dict[str, Any]] = []

    for key in ("state_csv", "action_csv", "decision_dir", "runlog"):
        add_check(checks, paths[key].exists(), f"{key}_exists", f"{key} exists", path=relpath(paths[key], root))

    state_rows, _ = read_csv(paths["state_csv"])
    action_rows, action_fields = read_csv(paths["action_csv"])
    decision_dir = paths["decision_dir"]
    json_paths = sorted(decision_dir.glob("action_*.json")) if decision_dir.exists() else []
    csv_paths = sorted(decision_dir.glob("action_*.csv")) if decision_dir.exists() else []

    add_check(checks, len(state_rows) > 0, "state_rows_nonzero", "state CSV has rows", count=len(state_rows))
    add_check(checks, len(action_rows) > 0, "action_rows_nonzero", "action CSV has rows", count=len(action_rows))
    add_check(checks, len(json_paths) > 0, "decision_json_nonzero", "decision JSON files exist", count=len(json_paths))
    add_check(checks, len(csv_paths) > 0, "decision_csv_nonzero", "decision CSV files exist", count=len(csv_paths))

    state_secs = [sec_from_value(row.get("sim_sec")) for row in state_rows]
    state_secs_ok = [sec for sec in state_secs if sec is not None]
    completed_sim_sec = max(state_secs_ok) if state_secs_ok else 0
    if sim_period_sec is not None:
        add_check(
            checks,
            completed_sim_sec + 1.0e-6 >= sim_period_sec,
            "state_completed_sim_period",
            "state CSV reaches requested sim period",
            completed_sim_sec=completed_sim_sec,
            sim_period_sec=sim_period_sec,
        )

    state_statuses = sorted(
        {str(row.get("controller_status", "")).strip() for row in state_rows if str(row.get("controller_status", "")).strip()}
    )
    non_ok_state = [status for status in state_statuses if status != "ok"]
    add_check(
        checks,
        not non_ok_state,
        "state_controller_status_ok",
        "state controller_status values are ok",
        statuses=state_statuses,
    )

    action_by_sec: dict[int, list[dict[str, str]]] = {}
    bad_action_secs = 0
    for row in action_rows:
        sec = sec_from_value(row.get("sim_sec"))
        if sec is None:
            bad_action_secs += 1
            continue
        action_by_sec.setdefault(sec, []).append(row)
    add_check(checks, bad_action_secs == 0, "action_sim_sec_parse", "action sim_sec values parse", bad_rows=bad_action_secs)

    json_secs = {sec_from_decision_path(path) for path in json_paths}
    csv_secs = {sec_from_decision_path(path) for path in csv_paths}
    action_secs = set(action_by_sec)
    json_secs.discard(None)
    csv_secs.discard(None)

    add_check(
        checks,
        action_secs == json_secs == csv_secs,
        "decision_sec_sets_match",
        "action CSV, decision JSON, and decision CSV seconds match",
        action_secs=sorted(action_secs),
        json_secs=sorted(json_secs),
        csv_secs=sorted(csv_secs),
    )

    expected = expected_decisions
    if expected is None:
        expected = expected_decision_count(sim_period_sec, control_interval_sec)
    if expected is not None:
        add_check(checks, len(json_paths) == expected, "decision_json_count_expected", "decision JSON count matches expected", expected=expected, actual=len(json_paths))
        add_check(checks, len(csv_paths) == expected, "decision_csv_count_expected", "decision CSV count matches expected", expected=expected, actual=len(csv_paths))
        add_check(checks, len(action_secs) == expected, "action_decision_count_expected", "action decision count matches expected", expected=expected, actual=len(action_secs))

    runlog_text = ""
    if paths["runlog"].exists():
        runlog_text = paths["runlog"].read_text(encoding="utf-8", errors="replace")
    add_check(checks, "STAGE=SIM_DONE" in runlog_text, "sim_done", "run log contains STAGE=SIM_DONE")
    log_sim_sec = parse_log_sim_sec(runlog_text)
    if sim_period_sec is not None:
        add_check(
            checks,
            log_sim_sec is not None and log_sim_sec + 1.0e-6 >= sim_period_sec,
            "log_sim_sec_reaches_period",
            "run log SIM_SEC reaches requested sim period",
            log_sim_sec=log_sim_sec,
            sim_period_sec=sim_period_sec,
        )

    total_decision_csv_rows = 0
    csv_mismatch_samples: list[str] = []
    for csv_path in csv_paths:
        sec = sec_from_decision_path(csv_path)
        decision_rows, decision_fields = read_csv(csv_path)
        total_decision_csv_rows += len(decision_rows)
        action_sec_rows = action_by_sec.get(sec or -1, [])
        if len(decision_rows) != len(action_sec_rows):
            csv_mismatch_samples.append(f"{csv_path.name}: rows {len(decision_rows)} != action {len(action_sec_rows)}")
            continue
        compare_fields = [field for field in decision_fields if field in action_fields and field not in {"sim_sec", "readback"}]
        for row_index, (decision_row, action_row) in enumerate(zip(decision_rows, action_sec_rows), start=1):
            for field in compare_fields:
                if not values_equal(decision_row.get(field), action_row.get(field)):
                    csv_mismatch_samples.append(f"{csv_path.name}: row {row_index} field {field}")
                    break
            if len(csv_mismatch_samples) >= 5:
                break
        if len(csv_mismatch_samples) >= 5:
            break
    add_check(
        checks,
        not csv_mismatch_samples,
        "decision_csv_matches_action_csv",
        "per-decision CSV rows match final action CSV rows",
        samples=csv_mismatch_samples,
    )
    add_check(
        checks,
        total_decision_csv_rows == len(action_rows),
        "decision_csv_row_total_matches_action",
        "sum of decision CSV rows matches action CSV rows",
        decision_csv_rows=total_decision_csv_rows,
        action_rows=len(action_rows),
    )

    prediction_error_count = 0
    prediction_error_status_bad: list[str] = []
    json_status_bad: list[str] = []
    json_sim_sec_bad: list[str] = []
    prediction_error_seen = False
    for json_path in json_paths:
        expected_sec = sec_from_decision_path(json_path)
        raw = load_json(json_path, checks)
        if raw is None:
            continue
        metadata = raw.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        json_sec = sec_from_value(raw.get("sim_sec", metadata.get("sim_sec")))
        if json_sec != expected_sec:
            json_sim_sec_bad.append(f"{json_path.name}:{json_sec}")
        status = str(raw.get("status") or metadata.get("controller_status") or metadata.get("status") or "").strip()
        if status != "ok":
            json_status_bad.append(f"{json_path.name}:{status or '<missing>'}")
        prediction_error = raw.get("prediction_error")
        if isinstance(prediction_error, dict):
            prediction_error_seen = True
            pred_status = str(prediction_error.get("status", "")).strip()
            if pred_status == "ok":
                prediction_error_count += 1
            else:
                prediction_error_status_bad.append(f"{json_path.name}:{pred_status or '<missing>'}")

    add_check(checks, not json_sim_sec_bad, "json_sim_sec_matches_filename", "decision JSON sim_sec matches filename", samples=json_sim_sec_bad[:5])
    add_check(checks, not json_status_bad, "json_status_ok", "decision JSON status is ok", samples=json_status_bad[:5])
    add_check(
        checks,
        not prediction_error_status_bad,
        "prediction_error_status_ok",
        "prediction_error statuses are ok",
        samples=prediction_error_status_bad[:5],
    )

    if expect_prediction_errors == "yes" or (expect_prediction_errors == "auto" and prediction_error_seen):
        expected_prediction_errors = max(0, len(json_paths) - 1)
        add_check(
            checks,
            prediction_error_count == expected_prediction_errors,
            "prediction_error_count_expected",
            "prediction_error_count matches expectation",
            expected=expected_prediction_errors,
            actual=prediction_error_count,
        )

    files = [file_record(path, root) for path in collect_manifest_files(paths)]
    ok = all(check["ok"] for check in checks)
    return {
        "case": case or run_dir.name,
        "status": "ok" if ok else "fail",
        "counts": {
            "state_rows": len(state_rows),
            "action_rows": len(action_rows),
            "decision_count_action_csv": len(action_secs),
            "decision_json_count": len(json_paths),
            "decision_csv_count": len(csv_paths),
            "prediction_error_count": prediction_error_count,
        },
        "completed_sim_sec": completed_sim_sec,
        "checks": checks,
        "files": files,
    }


def manifest_hash_index(payload: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for case in payload.get("cases", []):
        if not isinstance(case, dict):
            continue
        for item in case.get("files", []):
            if isinstance(item, dict) and item.get("exists") and item.get("sha256"):
                out[str(item.get("path"))] = str(item.get("sha256"))
    return out


def compare_manifest(current: dict[str, Any], expected_path: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    try:
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        add_check(checks, False, "manifest_read", f"{expected_path}: {type(exc).__name__}")
        return checks
    current_hashes = manifest_hash_index(current)
    expected_hashes = manifest_hash_index(expected if isinstance(expected, dict) else {})
    missing = sorted(path for path in expected_hashes if path not in current_hashes)
    changed = sorted(path for path, digest in expected_hashes.items() if current_hashes.get(path) not in (None, digest))
    add_check(checks, not missing, "manifest_paths_present", "manifest paths are still present", samples=missing[:5])
    add_check(checks, not changed, "manifest_hashes_match", "manifest SHA-256 hashes match", samples=changed[:5])
    return checks


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate VISSIM controller run outputs without running VISSIM.")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--case", action="append", default=[], help="Case suffix without state_/action_/decisions_ prefixes. May be repeated.")
    parser.add_argument("--sim-period-sec", type=float, default=None)
    parser.add_argument("--control-interval-sec", type=float, default=None)
    parser.add_argument("--expected-decisions", type=int, default=None)
    parser.add_argument("--expect-prediction-errors", choices=("auto", "yes", "no"), default="auto")
    parser.add_argument("--out-json", default="")
    parser.add_argument("--write-manifest", default="")
    parser.add_argument("--check-manifest", default="")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    root = Path.cwd()
    cases = discover_cases(run_dir, args.case)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": "ok",
        "run_dir": relpath(run_dir, root),
        "cases": [],
    }
    if not cases:
        payload["status"] = "fail"
        payload["cases"] = []
        payload["checks"] = [{"ok": False, "code": "cases_found", "message": "no state CSV cases found"}]
    else:
        payload["cases"] = [
            validate_case(
                run_dir=run_dir,
                case=case,
                sim_period_sec=args.sim_period_sec,
                control_interval_sec=args.control_interval_sec,
                expected_decisions=args.expected_decisions,
                expect_prediction_errors=args.expect_prediction_errors,
                root=root,
            )
            for case in cases
        ]
        if any(case["status"] != "ok" for case in payload["cases"]):
            payload["status"] = "fail"

    if args.check_manifest:
        manifest_checks = compare_manifest(payload, Path(args.check_manifest))
        payload["manifest_checks"] = manifest_checks
        if any(not check["ok"] for check in manifest_checks):
            payload["status"] = "fail"

    if args.out_json:
        write_json(Path(args.out_json), payload)
    if args.write_manifest:
        write_json(Path(args.write_manifest), payload)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
