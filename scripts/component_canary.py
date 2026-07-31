from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean
from typing import Any, Iterable


CANARY_COMPONENTS = ("leader_hinge", "np_deadband", "leader_mfd_far")


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def finite(values: Iterable[float]) -> list[float]:
    out: list[float] = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            out.append(number)
    return out


def avg(values: Iterable[float]) -> float:
    vals = finite(values)
    return float(mean(vals)) if vals else 0.0


def maxv(values: Iterable[float]) -> float:
    vals = finite(values)
    return float(max(vals)) if vals else 0.0


def load_decisions(decision_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(decision_dir.glob("action_*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            rows.append(
                {
                    "path": str(path),
                    "status": "parse_error",
                    "error": f"{type(exc).__name__}: {exc}",
                    "sim_sec": 0.0,
                    "metadata": {},
                }
            )
            continue
        meta = raw.get("metadata", {})
        if not isinstance(meta, dict):
            meta = {}
        rows.append(
            {
                "path": str(path),
                "status": "ok",
                "sim_sec": to_float(meta.get("sim_sec")),
                "metadata": meta,
            }
        )
    return rows


def summarize_dir(decision_dir: Path, active_start_sec: float) -> dict[str, Any]:
    decisions = load_decisions(decision_dir)
    ok_rows = [row for row in decisions if row.get("status") == "ok"]
    active = [row for row in ok_rows if to_float(row.get("sim_sec")) >= active_start_sec]
    scope = active or ok_rows

    def meta_values(key: str, rows: list[dict[str, Any]] = scope) -> list[float]:
        return [to_float(row.get("metadata", {}).get(key)) for row in rows]

    recalib_flags = meta_values("meta_leader_recalib_needed")
    mismatch_counts = meta_values("meta_calib_fingerprint_mismatch_count")
    active_count = len(active)
    recalib_count = sum(1 for value in recalib_flags if value > 0.0)
    recalib_rate = float(recalib_count / len(scope)) if scope else 0.0
    mismatch_max = maxv(mismatch_counts)

    if not scope:
        recommendation = "no_decision_json"
    elif recalib_rate >= 0.5 or mismatch_max >= len(CANARY_COMPONENTS):
        recommendation = "recalibrate_components"
    elif recalib_rate > 0.0 or mismatch_max > 0.0:
        recommendation = "monitor_and_recheck"
    else:
        recommendation = "canary_clean"

    return {
        "decision_dir": str(decision_dir),
        "active_start_sec": float(active_start_sec),
        "decision_json_count": len(decisions),
        "ok_decision_json_count": len(ok_rows),
        "parse_error_count": len(decisions) - len(ok_rows),
        "active_decision_count": active_count,
        "canary_components": list(CANARY_COMPONENTS),
        "recalib_needed_count": recalib_count,
        "recalib_needed_rate": recalib_rate,
        "fingerprint_mismatch_count_mean": avg(mismatch_counts),
        "fingerprint_mismatch_count_max": mismatch_max,
        "decision_wall_sec_mean": avg(meta_values("decision_wall_sec")),
        "decision_wall_sec_max": maxv(meta_values("decision_wall_sec")),
        "leader_recalib_objective_used_rate": avg(meta_values("meta_leader_follower_response_objective_used")),
        "leader_objective_gap_mean": avg(meta_values("meta_leader_candidate_objective_gap")),
        "leader_objective_gap_max": maxv(meta_values("meta_leader_candidate_objective_gap")),
        "leader_mfd_storage_penalty_mean": avg(meta_values("meta_leader_mfd_storage_penalty")),
        "leader_density_penalty_mean": avg(meta_values("meta_leader_density_penalty")),
        "leader_target_penalty_mean": avg(meta_values("meta_leader_target_penalty")),
        "recommendation": recommendation,
    }


def write_markdown(path: Path, summaries: list[dict[str, Any]]) -> None:
    lines = [
        "# Component canary report",
        "",
        "Canary components: `leader_hinge`, `np_deadband`, `leader_mfd_far`.",
        "",
        "| decision dir | active decisions | recalib rate | mismatch max | wall mean/max | recommendation |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in summaries:
        lines.append(
            "| "
            f"`{item['decision_dir']}` | "
            f"{item['active_decision_count']} | "
            f"{item['recalib_needed_rate']:.3f} | "
            f"{item['fingerprint_mismatch_count_max']:.0f} | "
            f"{item['decision_wall_sec_mean']:.3f}/{item['decision_wall_sec_max']:.3f} | "
            f"`{item['recommendation']}` |"
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- `recalibrate_components` means at least half of the active decisions asked for recalibration, or the max fingerprint mismatch covers all three canary components.",
            "- This script diagnoses the drift; it does not silently change controller parameters.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("decision_dirs", nargs="+", type=Path)
    parser.add_argument("--active-start-sec", type=float, default=3600.0)
    parser.add_argument("--out-json", default="")
    parser.add_argument("--out-md", default="")
    args = parser.parse_args()

    summaries = [summarize_dir(path, active_start_sec=float(args.active_start_sec)) for path in args.decision_dirs]
    payload = {
        "status": "ok",
        "active_start_sec": float(args.active_start_sec),
        "summaries": summaries,
    }
    if args.out_json:
        out_json = Path(args.out_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.out_md:
        write_markdown(Path(args.out_md), summaries)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
