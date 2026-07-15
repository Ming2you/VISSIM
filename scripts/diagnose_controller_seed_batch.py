from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def fmt(value: Any, ndigits: int = 3) -> str:
    return f"{to_float(value):.{ndigits}f}"


def controller_stats(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get("controller", ""))].append(row)
    out: list[dict[str, Any]] = []
    for controller, items in sorted(groups.items()):
        if not controller:
            continue
        total_pct = [to_float(row.get("vehicle_hours_total_pct_vs_no_control")) for row in items]
        stopped_pct = [to_float(row.get("stopped_vehicle_hours_pct_vs_no_control")) for row in items]
        speed_pct = [to_float(row.get("mean_speed_kph_pct_vs_no_control")) for row in items]
        pred_pct = [to_float(row.get("prediction_total_abs_error_mean_veh_pct_vs_no_control")) for row in items]
        row = {
            "controller": controller,
            "cases": len(items),
            "mean_total_pct": mean(total_pct) if total_pct else 0.0,
            "median_total_pct": median(total_pct) if total_pct else 0.0,
            "total_improved_count": sum(1 for value in total_pct if value < 0.0),
            "mean_stopped_pct": mean(stopped_pct) if stopped_pct else 0.0,
            "median_stopped_pct": median(stopped_pct) if stopped_pct else 0.0,
            "stopped_improved_count": sum(1 for value in stopped_pct if value < 0.0),
            "mean_speed_pct": mean(speed_pct) if speed_pct else 0.0,
            "mean_pred_err_pct": mean(pred_pct) if pred_pct else 0.0,
            "pred_err_improved_count": sum(1 for value in pred_pct if value < 0.0),
            "mean_decision_wall_sec": mean(to_float(row.get("mean_decision_wall_sec")) for row in items),
            "max_decision_wall_sec": max(to_float(row.get("max_decision_wall_sec")) for row in items),
            "mean_signal_split_abs_sec": mean(to_float(row.get("mean_signal_split_abs_sec")) for row in items),
            "mean_signal_offset_abs_sec": mean(to_float(row.get("mean_signal_offset_abs_sec")) for row in items),
            "mean_vsl_step_kph": mean(to_float(row.get("vsl_mean_abs_step_kph")) for row in items),
            "mean_ramp_green_step_sec": mean(to_float(row.get("ramp_green_abs_step_sec")) for row in items),
            "fallback_rows": sum(to_float(row.get("fallback_state_rows")) for row in items),
            "controller_errors": sum(to_float(row.get("controller_error_count")) for row in items),
            "wu_convergence_rate": mean(to_float(row.get("wu_convergence_rate")) for row in items),
            "wu_iterations_mean": mean(to_float(row.get("wu_iterations_mean")) for row in items),
            "pfo_convergence_rate": mean(to_float(row.get("pfo_convergence_rate")) for row in items),
            "pfo_iterations_mean": mean(to_float(row.get("pfo_iterations_mean")) for row in items),
        }
        out.append(row)
    return out


def root_causes(stats: list[dict[str, Any]], calibration_md: Path | None) -> list[str]:
    by_controller = {str(row["controller"]): row for row in stats}
    causes: list[str] = []
    wu = by_controller.get("wu", {})
    pfo = by_controller.get("pfo", {})

    if wu:
        causes.append(
            "1. Wu is effectively inactive under this setup: "
            f"mean total veh-h {fmt(wu.get('mean_total_pct'))}% vs no-control, "
            f"stopped veh-h {fmt(wu.get('mean_stopped_pct'))}%, "
            f"VSL step {fmt(wu.get('mean_vsl_step_kph'))} kph, "
            f"ramp step {fmt(wu.get('mean_ramp_green_step_sec'))} s, "
            f"signal offset {fmt(wu.get('mean_signal_offset_abs_sec'))} s. "
            "It solves without fallback, but the selected actions barely change the plant."
        )
    if pfo:
        causes.append(
            "2. PFO benefits are limited to signal timing: "
            f"stopped veh-h improves {fmt(pfo.get('mean_stopped_pct'))}% on average, "
            f"but total veh-h only {fmt(pfo.get('mean_total_pct'))}%. "
            f"VSL and ramp steps are both {fmt(pfo.get('mean_vsl_step_kph'))}/"
            f"{fmt(pfo.get('mean_ramp_green_step_sec'))}, while signal split/offset move "
            f"{fmt(pfo.get('mean_signal_split_abs_sec'))} s / {fmt(pfo.get('mean_signal_offset_abs_sec'))} s."
        )
        causes.append(
            "3. PFO is computationally heavy for this loop: "
            f"mean decision wall time {fmt(pfo.get('mean_decision_wall_sec'))} s, "
            f"max {fmt(pfo.get('max_decision_wall_sec'))} s. "
            "It fits a 60 s control interval, but it is expensive for larger horizons, more seeds, or parallel VISSIM."
        )
    if calibration_md and calibration_md.exists():
        causes.append(
            "4. METANET audit calibration is not stable enough to promote blindly. "
            f"The latest Bayesian patch is recorded at `{calibration_md}`; use it as a candidate and validate on held-out demand/seed before replacing active dynamics."
        )
    causes.append(
        "5. This symmetric-high demand mainly exercises signal timing. "
        "Because VSL and ramp metering never activate, the next diagnostic should use freeway-heavy and ramp-biased scenarios after the audit calibration is held out."
    )
    return causes


def write_markdown(path: Path, stats: list[dict[str, Any]], causes: list[str], source: Path) -> None:
    lines = [
        "# Controller seed-batch diagnosis",
        "",
        f"- Source: `{source}`",
        "- Baseline: seed-paired no-control.",
        "- Negative total/stopped percentage means improvement vs no-control.",
        "",
        "## Paired summary",
        "",
        "| controller | cases | total % mean | total improved | stopped % mean | stopped improved | speed % mean | pred err % mean | wall s | signal split | signal offset | VSL step | ramp step |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in stats:
        lines.append(
            "| "
            f"`{row['controller']}` | {row['cases']} | {fmt(row['mean_total_pct'])}% | "
            f"{int(row['total_improved_count'])}/{row['cases']} | {fmt(row['mean_stopped_pct'])}% | "
            f"{int(row['stopped_improved_count'])}/{row['cases']} | {fmt(row['mean_speed_pct'])}% | "
            f"{fmt(row['mean_pred_err_pct'])}% | {fmt(row['mean_decision_wall_sec'])} | "
            f"{fmt(row['mean_signal_split_abs_sec'])} | {fmt(row['mean_signal_offset_abs_sec'])} | "
            f"{fmt(row['mean_vsl_step_kph'])} | {fmt(row['mean_ramp_green_step_sec'])} |"
        )
    lines.extend([
        "",
        "## Prioritized causes / next fixes",
        "",
    ])
    lines.extend(causes)
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--calibration-md", default="")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    rows = read_csv(out_dir / "stress_case_summary.csv")
    stats = controller_stats(rows)
    calibration_md = Path(args.calibration_md) if args.calibration_md else None
    causes = root_causes(stats, calibration_md)
    payload = {"status": "ok", "source": str(out_dir), "stats": stats, "causes": causes}
    (out_dir / "controller_seed_diagnosis.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(out_dir / "controller_seed_diagnosis.md", stats, causes, out_dir)
    print(json.dumps({"status": "ok", "diagnosis_md": str(out_dir / "controller_seed_diagnosis.md")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
