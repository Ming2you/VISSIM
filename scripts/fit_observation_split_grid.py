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
]

SCORE_WEIGHTS = {
    "total_model_vehicles": 0.20,
    "protected_accumulation_veh": 0.30,
    "urban_queue_plus_link_occupancy_total_veh": 0.25,
    "urban_link_occupancy_total_veh": 0.15,
    "urban_movement_queue_total_veh": 0.10,
}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def state_time(path: Path) -> int:
    try:
        return int(path.stem.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        return 0


def parse_grid(text: str) -> list[float]:
    values: list[float] = []
    for raw in text.split(","):
        raw = raw.strip()
        if not raw:
            continue
        value = max(0.0, min(1.0, float(raw)))
        if value not in values:
            values.append(value)
    return values


def case_scenario(case_dir: Path) -> str:
    payload = read_json(case_dir / "case.json")
    case = payload.get("case", payload)
    scenario = case.get("scenario", {}) if isinstance(case, dict) else {}
    if isinstance(scenario, dict) and scenario.get("scenario_id"):
        return str(scenario["scenario_id"])
    if isinstance(case, dict) and case.get("scenario_id"):
        return str(case["scenario_id"])
    return case_dir.name


def candidate_name(internal_fraction: float, offramp_fraction: float) -> str:
    return f"int{int(round(internal_fraction * 100)):03d}_off{int(round(offramp_fraction * 100)):03d}"


def candidate_specs(internal_grid: list[float], offramp_grid: list[float]) -> list[dict[str, float | str]]:
    seen: set[str] = set()
    specs: list[dict[str, float | str]] = []
    preferred = [(0.35, 0.50)]
    for internal_fraction, offramp_fraction in preferred + [
        (internal_fraction, offramp_fraction)
        for internal_fraction in internal_grid
        for offramp_fraction in offramp_grid
    ]:
        name = candidate_name(internal_fraction, offramp_fraction)
        if name in seen:
            continue
        seen.add(name)
        specs.append({
            "name": name,
            "internal_storage_fraction": float(internal_fraction),
            "offramp_storage_fraction": float(offramp_fraction),
        })
    return specs


def make_candidate_calibration(
    *,
    base_calibration: dict[str, Any],
    candidate: dict[str, float | str],
    out_path: Path,
) -> Path:
    calibration = json.loads(json.dumps(base_calibration))
    observation = calibration.get("observation", {})
    if not isinstance(observation, dict):
        observation = {}
    observation.update({
        "mode": "detector_local_v2_storage_split",
        "internal_storage_fraction": float(candidate["internal_storage_fraction"]),
        "offramp_storage_fraction": float(candidate["offramp_storage_fraction"]),
        "status": "candidate_observation_split_grid_fit_20260629",
        "fit_candidate": str(candidate["name"]),
    })
    calibration["observation"] = observation
    write_json(out_path, calibration)
    return out_path


def make_candidate_tuning(base_tuning: dict[str, Any], candidate: dict[str, float | str], out_path: Path) -> Path:
    tuning = json.loads(json.dumps(base_tuning))
    tuning["name"] = f"obs_split_{candidate['name']}"
    write_json(out_path, tuning)
    return out_path


def run_candidate(
    *,
    candidate: dict[str, float | str],
    case_dirs: list[Path],
    out_dir: Path,
    adapter: Path,
    calibration_path: Path,
    tuning_path: Path,
    controller: str,
    mode: str,
) -> list[dict[str, Any]]:
    candidate_dir = out_dir / str(candidate["name"])
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
            sim_sec = state_time(state_path)
            out_json = replay_dir / f"action_{sim_sec:06d}.json"
            out_csv = replay_dir / f"action_{sim_sec:06d}.csv"
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
                str(calibration_path),
                "--tuning-json",
                str(tuning_path),
            ]
            completed = subprocess.run(cmd, text=True, errors="replace", capture_output=True, shell=False)
            if completed.returncode != 0:
                rows.append({
                    "candidate": candidate["name"],
                    "internal_storage_fraction": candidate["internal_storage_fraction"],
                    "offramp_storage_fraction": candidate["offramp_storage_fraction"],
                    "scenario_id": scenario_id,
                    "case_dir": str(case_dir),
                    "state_json": str(state_path),
                    "sim_sec": sim_sec,
                    "status": "adapter_failed",
                    "returncode": completed.returncode,
                    "stderr": completed.stderr[-1000:],
                })
                previous_action = str(out_json)
                continue
            action = read_json(out_json)
            metadata = action.get("metadata", {})
            prediction_error = action.get("prediction_error", {})
            scalar = prediction_error.get("scalar_errors", {}) if isinstance(prediction_error, dict) else {}
            for metric in KEY_METRICS:
                item = scalar.get(metric, {}) if isinstance(scalar, dict) else {}
                if not isinstance(item, dict):
                    continue
                rows.append({
                    "candidate": candidate["name"],
                    "internal_storage_fraction": candidate["internal_storage_fraction"],
                    "offramp_storage_fraction": candidate["offramp_storage_fraction"],
                    "scenario_id": scenario_id,
                    "case_dir": str(case_dir),
                    "state_json": str(state_path),
                    "action_json": str(out_json),
                    "sim_sec": sim_sec,
                    "status": "ok",
                    "metric": metric,
                    "predicted": as_float(item.get("predicted")),
                    "observed": as_float(item.get("observed")),
                    "error": as_float(item.get("error")),
                    "abs_error": as_float(item.get("abs_error")),
                    "metadata_internal_storage_fraction": as_float(
                        metadata.get("local_observation_internal_storage_fraction")
                    ) if isinstance(metadata, dict) else 0.0,
                    "metadata_offramp_storage_fraction": as_float(
                        metadata.get("local_observation_offramp_storage_fraction")
                    ) if isinstance(metadata, dict) else 0.0,
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
    by_scenario: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("status") != "ok":
            continue
        groups[(str(row.get("candidate")), str(row.get("metric")))].append(row)
        by_scenario[
            (str(row.get("candidate")), str(row.get("scenario_id")), str(row.get("metric")))
        ].append(row)

    summary_rows: list[dict[str, Any]] = []
    for (candidate, metric), items in sorted(groups.items()):
        values = [as_float(item.get("abs_error")) for item in items]
        first = items[0]
        summary_rows.append({
            "scope": "overall",
            "candidate": candidate,
            "scenario_id": "",
            "internal_storage_fraction": first.get("internal_storage_fraction"),
            "offramp_storage_fraction": first.get("offramp_storage_fraction"),
            "metric": metric,
            "n": len(values),
            "mean_abs_error": mean(values) if values else 0.0,
        })
    for (candidate, scenario_id, metric), items in sorted(by_scenario.items()):
        values = [as_float(item.get("abs_error")) for item in items]
        first = items[0]
        summary_rows.append({
            "scope": "scenario",
            "candidate": candidate,
            "scenario_id": scenario_id,
            "internal_storage_fraction": first.get("internal_storage_fraction"),
            "offramp_storage_fraction": first.get("offramp_storage_fraction"),
            "metric": metric,
            "n": len(values),
            "mean_abs_error": mean(values) if values else 0.0,
        })
    return summary_rows


def candidate_metric_map(summary_rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = defaultdict(dict)
    for row in summary_rows:
        if row.get("scope") != "overall":
            continue
        out[str(row["candidate"])][str(row["metric"])] = as_float(row["mean_abs_error"])
    return out


def ranked_candidates(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_candidate = candidate_metric_map(summary_rows)
    base = by_candidate.get(candidate_name(0.35, 0.50), {})
    candidate_meta: dict[str, dict[str, Any]] = {}
    for row in summary_rows:
        if row.get("scope") == "overall":
            candidate_meta[str(row["candidate"])] = {
                "internal_storage_fraction": row.get("internal_storage_fraction"),
                "offramp_storage_fraction": row.get("offramp_storage_fraction"),
            }

    ranked: list[dict[str, Any]] = []
    for candidate, metrics in by_candidate.items():
        score = 0.0
        weight_total = 0.0
        for metric, weight in SCORE_WEIGHTS.items():
            value = metrics.get(metric)
            if value is None:
                continue
            denom = max(1.0e-9, base.get(metric, value))
            score += weight * value / denom
            weight_total += weight
        score = score / max(1.0e-9, weight_total)
        row = {
            "candidate": candidate,
            "score_relative_to_base": score,
            **candidate_meta.get(candidate, {}),
        }
        for metric in KEY_METRICS:
            row[metric] = metrics.get(metric, 0.0)
            if metric in base:
                row[f"{metric}_delta_pct_vs_base"] = (
                    100.0 * (metrics.get(metric, 0.0) - base[metric]) / max(1.0e-9, base[metric])
                )
        ranked.append(row)
    return sorted(ranked, key=lambda row: as_float(row.get("score_relative_to_base"), 999.0))


def write_markdown(path: Path, ranked: list[dict[str, Any]]) -> None:
    lines = [
        "# Observation queue/storage split grid fit",
        "",
        "Lower score is better. The score is a weighted relative mean absolute one-step prediction error, normalized to the current base split `internal=0.35`, `offramp=0.50`.",
        "",
        "| rank | candidate | internal | offramp | score | total | protected | urban q+storage | urban storage | movement queue | total vs base | protected vs base |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rank, row in enumerate(ranked[:20], start=1):
        lines.append(
            f"| {rank} | `{row['candidate']}` | "
            f"{as_float(row.get('internal_storage_fraction')):.2f} | "
            f"{as_float(row.get('offramp_storage_fraction')):.2f} | "
            f"{as_float(row.get('score_relative_to_base')):.3f} | "
            f"{as_float(row.get('total_model_vehicles')):.3f} | "
            f"{as_float(row.get('protected_accumulation_veh')):.3f} | "
            f"{as_float(row.get('urban_queue_plus_link_occupancy_total_veh')):.3f} | "
            f"{as_float(row.get('urban_link_occupancy_total_veh')):.3f} | "
            f"{as_float(row.get('urban_movement_queue_total_veh')):.3f} | "
            f"{as_float(row.get('total_model_vehicles_delta_pct_vs_base')):.1f}% | "
            f"{as_float(row.get('protected_accumulation_veh_delta_pct_vs_base')):.1f}% |"
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
    parser.add_argument(
        "--internal-grid",
        default="0.10,0.20,0.30,0.35,0.40,0.50,0.60,0.70",
    )
    parser.add_argument("--offramp-grid", default="0.35,0.50,0.65,0.80")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    case_dirs = [Path(value) for value in args.case_dirs]
    base_calibration = read_json(Path(args.calibration))
    base_tuning = read_json(Path(args.base_tuning))
    all_rows: list[dict[str, Any]] = []
    candidates = candidate_specs(parse_grid(args.internal_grid), parse_grid(args.offramp_grid))
    for candidate in candidates:
        print(
            "START "
            f"{candidate['name']} "
            f"internal={candidate['internal_storage_fraction']} "
            f"offramp={candidate['offramp_storage_fraction']}",
            flush=True,
        )
        candidate_dir = out_dir / str(candidate["name"])
        calibration_path = make_candidate_calibration(
            base_calibration=base_calibration,
            candidate=candidate,
            out_path=candidate_dir / "calibration.json",
        )
        tuning_path = make_candidate_tuning(
            base_tuning=base_tuning,
            candidate=candidate,
            out_path=candidate_dir / "tuning.json",
        )
        all_rows.extend(
            run_candidate(
                candidate=candidate,
                case_dirs=case_dirs,
                out_dir=out_dir,
                adapter=Path(args.adapter),
                calibration_path=calibration_path,
                tuning_path=tuning_path,
                controller=str(args.controller),
                mode=str(args.mode),
            )
        )

    summary_rows = summarize(all_rows)
    ranked = ranked_candidates(summary_rows)
    write_csv(out_dir / "observation_split_grid_rows.csv", all_rows)
    write_csv(out_dir / "observation_split_grid_summary.csv", summary_rows)
    write_csv(out_dir / "observation_split_grid_ranked.csv", ranked)
    write_markdown(out_dir / "observation_split_grid_summary.md", ranked)
    best = ranked[0] if ranked else {}
    write_json(out_dir / "observation_split_grid_best.json", {"best": best, "ranked": ranked[:20]})
    print(json.dumps({
        "status": "ok",
        "candidate_count": len(candidates),
        "row_count": len(all_rows),
        "best": best,
        "summary_md": str(out_dir / "observation_split_grid_summary.md"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
