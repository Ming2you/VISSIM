from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


KEY_METRICS = [
    "total_model_vehicles",
    "protected_accumulation_veh",
    "urban_queue_plus_link_occupancy_total_veh",
    "urban_link_occupancy_total_veh",
    "urban_movement_queue_total_veh",
    "freeway_total_veh",
    "freeway_mean_speed_kph",
]


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return raw if isinstance(raw, dict) else {}


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def state_time(path: Path) -> int:
    stem = path.stem
    try:
        return int(stem.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        return 0


def case_scenario(case_dir: Path) -> str:
    case = read_json(case_dir / "case.json")
    if isinstance(case.get("case"), dict):
        case = case["case"]
    scenario = case.get("scenario", {})
    if isinstance(scenario, dict):
        return str(scenario.get("scenario_id", case_dir.name))
    return str(case.get("scenario_id", case_dir.name))


def candidate_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = [
        {
            "name": "base",
            "network": {},
        }
    ]
    for movement_capacity in (2200.0, 2600.0, 3200.0):
        specs.append({
            "name": f"cap{int(movement_capacity)}",
            "network": {"movement_capacity_veh_h": movement_capacity},
        })
    for urban_speed in (70.0, 90.0, 110.0):
        specs.append({
            "name": f"speed{int(urban_speed)}",
            "network": {"urban_avg_speed_km_h": urban_speed},
        })
    for movement_capacity in (2200.0, 2600.0, 3200.0):
        for urban_speed in (70.0, 90.0, 110.0):
            specs.append({
                "name": f"cap{int(movement_capacity)}_speed{int(urban_speed)}",
                "network": {
                    "movement_capacity_veh_h": movement_capacity,
                    "urban_avg_speed_km_h": urban_speed,
                },
            })
    for lost_time in (4.0, 5.0):
        specs.append({
            "name": f"lost{int(lost_time)}_cap2600_speed90",
            "network": {
                "lost_time": lost_time,
                "movement_capacity_veh_h": 2600.0,
                "urban_avg_speed_km_h": 90.0,
            },
        })
    return specs


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_candidate(
    *,
    candidate: dict[str, Any],
    case_dirs: list[Path],
    out_dir: Path,
    adapter: Path,
    calibration: Path,
    base_tuning: Path,
    controller: str,
    mode: str,
) -> list[dict[str, Any]]:
    candidate_dir = out_dir / str(candidate["name"])
    tuning_path = candidate_dir / "tuning.json"
    base = read_json(base_tuning)
    tuning = dict(base)
    tuning["name"] = str(candidate["name"])
    network = dict(tuning.get("network", {})) if isinstance(tuning.get("network"), dict) else {}
    network.update(candidate.get("network", {}))
    tuning["network"] = network
    write_json(tuning_path, tuning)

    rows: list[dict[str, Any]] = []
    for case_dir in case_dirs:
        state_paths = sorted((case_dir / "decisions").glob("state_*.json"), key=state_time)
        if not state_paths:
            continue
        scenario_id = case_scenario(case_dir)
        replay_dir = candidate_dir / case_dir.name / "decisions"
        replay_dir.mkdir(parents=True, exist_ok=True)
        previous_action = ""
        for state_path in state_paths:
            t = state_time(state_path)
            out_json = replay_dir / f"action_{t:06d}.json"
            out_csv = replay_dir / f"action_{t:06d}.csv"
            cmd = [
                sys.executable,
                str(adapter),
                "--state-json",
                str(state_path),
                "--previous-action-json",
                previous_action,
                "--out-action-json",
                str(out_json),
                "--out-action-csv",
                str(out_csv),
                "--controller",
                controller,
                "--mode",
                mode,
                "--calibration-json",
                str(calibration),
                "--tuning-json",
                str(tuning_path),
            ]
            completed = subprocess.run(cmd, text=True, capture_output=True, shell=False)
            if completed.returncode != 0:
                rows.append({
                    "candidate": candidate["name"],
                    "scenario_id": scenario_id,
                    "case_dir": str(case_dir),
                    "state_json": str(state_path),
                    "status": "adapter_failed",
                    "returncode": completed.returncode,
                    "stderr": completed.stderr[-500:],
                })
                previous_action = str(out_json)
                continue
            action = read_json(out_json)
            err = action.get("prediction_error", {})
            scalar = err.get("scalar_errors", {}) if isinstance(err, dict) else {}
            for metric in KEY_METRICS:
                item = scalar.get(metric, {}) if isinstance(scalar, dict) else {}
                if not isinstance(item, dict):
                    continue
                rows.append({
                    "candidate": candidate["name"],
                    "scenario_id": scenario_id,
                    "case_dir": str(case_dir),
                    "state_json": str(state_path),
                    "action_json": str(out_json),
                    "sim_sec": t,
                    "status": "ok",
                    "metric": metric,
                    "predicted": as_float(item.get("predicted")),
                    "observed": as_float(item.get("observed")),
                    "error": as_float(item.get("error")),
                    "abs_error": as_float(item.get("abs_error")),
                })
            previous_action = str(out_json)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("status") != "ok":
            continue
        groups[(str(row.get("candidate")), str(row.get("metric")))].append(row)
    out: list[dict[str, Any]] = []
    for (candidate, metric), items in sorted(groups.items()):
        values = [as_float(item.get("abs_error")) for item in items]
        out.append({
            "candidate": candidate,
            "metric": metric,
            "n": len(values),
            "mean_abs_error": mean(values) if values else 0.0,
        })
    return out


def write_markdown(path: Path, summary_rows: list[dict[str, Any]]) -> None:
    by_candidate: dict[str, dict[str, float]] = defaultdict(dict)
    for row in summary_rows:
        by_candidate[str(row["candidate"])][str(row["metric"])] = as_float(row["mean_abs_error"])
    base = by_candidate.get("base", {})
    score_metrics = [
        "total_model_vehicles",
        "protected_accumulation_veh",
        "urban_queue_plus_link_occupancy_total_veh",
        "freeway_total_veh",
    ]
    ranked: list[tuple[float, str]] = []
    for candidate, metrics in by_candidate.items():
        score = mean([metrics.get(metric, 0.0) for metric in score_metrics])
        ranked.append((score, candidate))
    lines = [
        "# Offline prediction tuning replay",
        "",
        "Lower mean abs error is better. Replay uses saved Vissim `state_*.json`; it does not rerun Vissim.",
        "",
        "| rank | candidate | score | total | protected | urban q+storage | freeway | total vs base | protected vs base |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rank, (score, candidate) in enumerate(sorted(ranked), start=1):
        metrics = by_candidate[candidate]
        total = metrics.get("total_model_vehicles", 0.0)
        protected = metrics.get("protected_accumulation_veh", 0.0)
        urban = metrics.get("urban_queue_plus_link_occupancy_total_veh", 0.0)
        freeway = metrics.get("freeway_total_veh", 0.0)
        base_total = base.get("total_model_vehicles", total)
        base_protected = base.get("protected_accumulation_veh", protected)
        total_delta = 100.0 * (total - base_total) / max(1.0e-9, base_total)
        protected_delta = 100.0 * (protected - base_protected) / max(1.0e-9, base_protected)
        lines.append(
            f"| {rank} | `{candidate}` | {score:.3f} | {total:.3f} | {protected:.3f} | "
            f"{urban:.3f} | {freeway:.3f} | {total_delta:.1f}% | {protected_delta:.1f}% |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case_dirs", nargs="+")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--adapter", default="evaluation/controllers/vissim_stackelberg_adapter.py")
    parser.add_argument("--calibration", default="evaluation/calibration/vissim_network_calibration_v2_20260628.json")
    parser.add_argument("--base-tuning", default="evaluation/configs/pfo_h3_i3_medium.json")
    parser.add_argument("--controller", default="no-control")
    parser.add_argument("--mode", default="fast-smoke")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    case_dirs = [Path(value) for value in args.case_dirs]
    all_rows: list[dict[str, Any]] = []
    for candidate in candidate_specs():
        print(f"START {candidate['name']}", flush=True)
        all_rows.extend(
            run_candidate(
                candidate=candidate,
                case_dirs=case_dirs,
                out_dir=out_dir,
                adapter=Path(args.adapter),
                calibration=Path(args.calibration),
                base_tuning=Path(args.base_tuning),
                controller=str(args.controller),
                mode=str(args.mode),
            )
        )
    summary_rows = summarize(all_rows)
    write_csv(out_dir / "prediction_tuning_replay_rows.csv", all_rows)
    write_csv(out_dir / "prediction_tuning_replay_summary.csv", summary_rows)
    write_markdown(out_dir / "prediction_tuning_replay_summary.md", summary_rows)
    print(json.dumps({
        "status": "ok",
        "row_count": len(all_rows),
        "summary_md": str(out_dir / "prediction_tuning_replay_summary.md"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
