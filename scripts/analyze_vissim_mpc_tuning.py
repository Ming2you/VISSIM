from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.controllers import action_csv_schema  # noqa: E402


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def to_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def positive_median(values: Iterable[float], default: float = 5.0) -> float:
    vals = sorted(v for v in values if v > 0.0 and math.isfinite(v))
    return float(median(vals)) if vals else float(default)


def weighted_mean(rows: list[dict[str, str]], key: str, dts: list[float]) -> float:
    den = sum(dts)
    if den <= 0.0:
        return 0.0
    return sum(to_float(row.get(key)) * dt for row, dt in zip(rows, dts)) / den


def state_metrics(rows: list[dict[str, str]], warmup_sec: float) -> dict[str, float | str]:
    if not rows:
        return {
            "state_rows": 0,
            "completed_sim_sec": 0.0,
            "vehicle_hours_total": 0.0,
            "vehicle_hours_freeway": 0.0,
            "vehicle_hours_urban": 0.0,
            "stopped_vehicle_hours": 0.0,
            "mean_total_vehicles": 0.0,
            "mean_freeway_vehicles": 0.0,
            "mean_urban_vehicles": 0.0,
            "mean_speed_kph": 0.0,
            "freeway_mean_speed_kph": 0.0,
            "mean_stopped_vehicles": 0.0,
            "final_total_vehicles": 0.0,
            "controller_fallback_rows": 0,
            "mean_decision_wall_sec": 0.0,
            "max_decision_wall_sec": 0.0,
            "controller_statuses": "",
        }
    rows = sorted(rows, key=lambda row: to_float(row.get("sim_sec")))
    sim_secs = [to_float(row.get("sim_sec")) for row in rows]
    diffs = [b - a for a, b in zip(sim_secs, sim_secs[1:])]
    default_dt = positive_median(diffs, default=5.0)
    rows_after = [row for row in rows if to_float(row.get("sim_sec")) >= warmup_sec]
    if not rows_after:
        rows_after = rows
    secs_after = [to_float(row.get("sim_sec")) for row in rows_after]
    dts = []
    for idx, sec in enumerate(secs_after):
        if idx + 1 < len(secs_after):
            dts.append(max(0.0, secs_after[idx + 1] - sec))
        else:
            dts.append(default_dt)
    total_time_h = sum(dts) / 3600.0
    statuses = sorted({str(row.get("controller_status", "")) for row in rows if str(row.get("controller_status", ""))})
    decision_walls = [to_float(row.get("decision_wall_sec")) for row in rows if to_float(row.get("decision_wall_sec")) > 0.0]
    fallback_rows = sum(1 for row in rows if str(row.get("controller_status", "")).strip() not in ("", "ok"))
    final = rows[-1]
    return {
        "state_rows": len(rows),
        "completed_sim_sec": max(sim_secs),
        "vehicle_hours_total": sum(to_float(row.get("total_vehicles")) * dt for row, dt in zip(rows_after, dts)) / 3600.0,
        "vehicle_hours_freeway": sum(to_float(row.get("freeway_vehicles")) * dt for row, dt in zip(rows_after, dts)) / 3600.0,
        "vehicle_hours_urban": sum(to_float(row.get("urban_vehicles")) * dt for row, dt in zip(rows_after, dts)) / 3600.0,
        "stopped_vehicle_hours": sum(to_float(row.get("stopped_vehicles")) * dt for row, dt in zip(rows_after, dts)) / 3600.0,
        "mean_total_vehicles": weighted_mean(rows_after, "total_vehicles", dts),
        "mean_freeway_vehicles": weighted_mean(rows_after, "freeway_vehicles", dts),
        "mean_urban_vehicles": weighted_mean(rows_after, "urban_vehicles", dts),
        "mean_speed_kph": weighted_mean(rows_after, "mean_speed_kph", dts),
        "freeway_mean_speed_kph": weighted_mean(rows_after, "freeway_mean_speed_kph", dts),
        "mean_stopped_vehicles": weighted_mean(rows_after, "stopped_vehicles", dts),
        "final_total_vehicles": to_float(final.get("total_vehicles")),
        "final_urban_vehicles": to_float(final.get("urban_vehicles")),
        "final_freeway_vehicles": to_float(final.get("freeway_vehicles")),
        "controller_fallback_rows": fallback_rows,
        "mean_decision_wall_sec": mean(decision_walls) if decision_walls else 0.0,
        "max_decision_wall_sec": max(decision_walls) if decision_walls else 0.0,
        "controller_statuses": "|".join(statuses),
        "analysis_time_h": total_time_h,
    }


def action_metrics(rows: list[dict[str, str]]) -> dict[str, float]:
    if not rows:
        return {
            "decision_count": 0,
            "vsl_mean_abs_step_kph": 0.0,
            "ramp_green_abs_step_sec": 0.0,
            "signal_green_abs_step_sec": 0.0,
            "mean_vsl_kph": 0.0,
            "mean_ramp_green_sec": 0.0,
            "mean_signal_green_sec": 0.0,
        }
    by_sec: dict[float, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        sec = to_float(row.get("sim_sec"))
        kind = str(row.get("kind", ""))
        if kind == "vsl":
            by_sec[sec]["vsl"].append(to_float(row.get("speed_kph")))
        elif kind == "ramp_meter":
            by_sec[sec]["ramp_green"].append(to_float(row.get("green_sec")))
        elif kind == "signal":
            # N4-0. v3 은 축 2열, v4 는 현시 4열이다. 저장소의 옛 런은 v3 이므로
            # 헤더로 세대를 가린다. 녹색 0 인 현시는 쓰지 않는 현시라 평균에서 뺀다.
            fields = (
                action_csv_schema.PHASE_GREEN_FIELDS
                if action_csv_schema.row_is_v4(row)
                else action_csv_schema.LEGACY_AXIS_GREEN_FIELDS
            )
            for field in fields:
                value = to_float(row.get(field))
                if value > 0.0:
                    by_sec[sec]["signal_green"].append(value)
    secs = sorted(by_sec)
    series = {
        "vsl": [mean(by_sec[sec]["vsl"]) if by_sec[sec]["vsl"] else 0.0 for sec in secs],
        "ramp_green": [
            mean(by_sec[sec]["ramp_green"]) if by_sec[sec]["ramp_green"] else 0.0
            for sec in secs
        ],
        "signal_green": [
            mean(by_sec[sec]["signal_green"]) if by_sec[sec]["signal_green"] else 0.0
            for sec in secs
        ],
    }

    def mean_abs_step(values: list[float]) -> float:
        diffs = [abs(b - a) for a, b in zip(values, values[1:]) if a > 0.0 or b > 0.0]
        return mean(diffs) if diffs else 0.0

    return {
        "decision_count": len(secs),
        "vsl_mean_abs_step_kph": mean_abs_step(series["vsl"]),
        "ramp_green_abs_step_sec": mean_abs_step(series["ramp_green"]),
        "signal_green_abs_step_sec": mean_abs_step(series["signal_green"]),
        "mean_vsl_kph": mean([v for v in series["vsl"] if v > 0.0]) if any(v > 0.0 for v in series["vsl"]) else 0.0,
        "mean_ramp_green_sec": mean([v for v in series["ramp_green"] if v > 0.0]) if any(v > 0.0 for v in series["ramp_green"]) else 0.0,
        "mean_signal_green_sec": mean([v for v in series["signal_green"] if v > 0.0]) if any(v > 0.0 for v in series["signal_green"]) else 0.0,
    }


def read_manifest(out_dir: Path) -> list[dict[str, object]]:
    path = out_dir / "batch_manifest.json"
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, list) else []
    rows = read_csv(out_dir / "batch_manifest.csv")
    return [dict(row) for row in rows]


def case_summary(row: dict[str, object], warmup_sec: float) -> dict[str, object]:
    state_csv = Path(str(row.get("state_csv", "")))
    action_csv = Path(str(row.get("action_csv", "")))
    metrics: dict[str, object] = {
        "case_id": row.get("case_id", ""),
        "tuning_name": row.get("tuning_name", ""),
        "demand_profile": row.get("demand_profile", ""),
        "returncode": int(to_float(row.get("returncode"), default=999.0)),
        "timed_out": str(row.get("timed_out", "")).lower() == "true",
        "elapsed_sec": to_float(row.get("elapsed_sec")),
        "sim_period_sec": to_float(row.get("sim_period_sec")),
        "urban_volume_vph": to_float(row.get("urban_volume_vph")),
        "freeway_volume_vph": to_float(row.get("freeway_volume_vph")),
        "rand_seed": int(to_float(row.get("rand_seed"))),
        "state_csv": str(state_csv),
        "action_csv": str(action_csv),
    }
    metrics.update(state_metrics(read_csv(state_csv), warmup_sec=warmup_sec))
    metrics.update(action_metrics(read_csv(action_csv)))
    metrics["primary_rank_key"] = (
        to_float(metrics.get("vehicle_hours_total"))
        + 0.25 * to_float(metrics.get("stopped_vehicle_hours"))
        + 0.002 * to_float(metrics.get("vsl_mean_abs_step_kph"))
        + 0.01 * to_float(metrics.get("ramp_green_abs_step_sec"))
        + 0.002 * to_float(metrics.get("signal_green_abs_step_sec"))
        + 1000.0 * to_float(metrics.get("controller_fallback_rows"))
    )
    return metrics


def group_summaries(cases: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for case in cases:
        if int(case.get("returncode", 999)) == 0 and to_float(case.get("state_rows")) > 0:
            group_key = f"{case.get('tuning_name', '')} / {case.get('demand_profile', '')}"
            groups[group_key].append(case)
    out = []
    keys = [
        "primary_rank_key",
        "vehicle_hours_total",
        "vehicle_hours_freeway",
        "vehicle_hours_urban",
        "stopped_vehicle_hours",
        "mean_total_vehicles",
        "mean_speed_kph",
        "freeway_mean_speed_kph",
        "mean_decision_wall_sec",
        "vsl_mean_abs_step_kph",
        "ramp_green_abs_step_sec",
        "signal_green_abs_step_sec",
        "mean_vsl_kph",
        "mean_ramp_green_sec",
        "mean_signal_green_sec",
    ]
    for tuning_name, rows in groups.items():
        item: dict[str, object] = {
            "tuning_name": str(rows[0].get("tuning_name", "")) if rows else tuning_name,
            "demand_profile": str(rows[0].get("demand_profile", "")) if rows else "",
            "group": tuning_name,
            "case_count": len(rows),
        }
        for key in keys:
            vals = [to_float(row.get(key)) for row in rows]
            item[f"mean_{key}"] = mean(vals) if vals else 0.0
            item[f"max_{key}"] = max(vals) if vals else 0.0
        item["fallback_rows_total"] = sum(int(to_float(row.get("controller_fallback_rows"))) for row in rows)
        item["seeds"] = ",".join(str(int(to_float(row.get("rand_seed")))) for row in rows)
        out.append(item)
    out.sort(key=lambda row: (to_float(row.get("mean_primary_rank_key")), to_float(row.get("mean_vehicle_hours_total"))))
    for idx, row in enumerate(out, start=1):
        row["rank"] = idx
    return out


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
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


def fmt(value: object, ndigits: int = 3) -> str:
    val = to_float(value)
    return f"{val:.{ndigits}f}"


def write_markdown(path: Path, cases: list[dict[str, object]], groups: list[dict[str, object]], warmup_sec: float) -> None:
    failed = [case for case in cases if int(case.get("returncode", 999)) != 0 or to_float(case.get("state_rows")) <= 0]
    best = groups[0] if groups else {}
    lines = [
        "# Vissim MPC tuning summary",
        "",
        f"- Warmup excluded from vehicle-hour metrics: {warmup_sec:.0f} s",
        f"- Case count: {len(cases)}",
        f"- Completed usable cases: {len(cases) - len(failed)}",
        f"- Failed/empty cases: {len(failed)}",
    ]
    if best:
        lines.extend(
            [
        f"- Current best group: `{best.get('group', best.get('tuning_name'))}`",
                f"- Best mean total vehicle-hours: {fmt(best.get('mean_vehicle_hours_total'))}",
                f"- Best mean stopped vehicle-hours: {fmt(best.get('mean_stopped_vehicle_hours'))}",
            ]
        )
    lines.extend(["", "## Group ranking", ""])
    if groups:
        lines.append("| rank | tuning | demand | cases | total veh-h | stopped veh-h | speed kph | VSL step | ramp step | signal step | fallback rows |")
        lines.append("| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for row in groups:
            lines.append(
                "| "
                f"{row.get('rank')} | `{row.get('tuning_name')}` | `{row.get('demand_profile')}` | {row.get('case_count')} | "
                f"{fmt(row.get('mean_vehicle_hours_total'))} | {fmt(row.get('mean_stopped_vehicle_hours'))} | "
                f"{fmt(row.get('mean_mean_speed_kph'))} | {fmt(row.get('mean_vsl_mean_abs_step_kph'))} | "
                f"{fmt(row.get('mean_ramp_green_abs_step_sec'))} | {fmt(row.get('mean_signal_green_abs_step_sec'))} | "
                f"{int(to_float(row.get('fallback_rows_total')))} |"
            )
    else:
        lines.append("No usable completed cases.")
    lines.extend(["", "## Case-level notes", ""])
    if cases:
        lines.append("| case | demand | status | total veh-h | stopped veh-h | mean speed | decisions | decision wall s |")
        lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |")
        for case in sorted(cases, key=lambda c: str(c.get("case_id"))):
            ok = int(case.get("returncode", 999)) == 0 and to_float(case.get("state_rows")) > 0
            lines.append(
                "| "
                f"`{case.get('case_id')}` | `{case.get('demand_profile')}` | {'ok' if ok else 'failed'} | "
                f"{fmt(case.get('vehicle_hours_total'))} | {fmt(case.get('stopped_vehicle_hours'))} | "
                f"{fmt(case.get('mean_speed_kph'))} | {int(to_float(case.get('decision_count')))} | "
                f"{fmt(case.get('mean_decision_wall_sec'))} |"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--warmup-sec", type=float, default=120.0)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    manifest = read_manifest(out_dir)
    cases = [case_summary(row, warmup_sec=float(args.warmup_sec)) for row in manifest]
    cases.sort(key=lambda row: str(row.get("case_id")))
    groups = group_summaries(cases)

    write_csv(out_dir / "tuning_case_summary.csv", cases)
    write_csv(out_dir / "tuning_group_summary.csv", groups)
    (out_dir / "tuning_summary.json").write_text(
        json.dumps({"cases": cases, "groups": groups}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown(out_dir / "tuning_summary.md", cases, groups, warmup_sec=float(args.warmup_sec))
    print(
        json.dumps(
            {
                "status": "ok",
                "case_count": len(cases),
                "group_count": len(groups),
                "best_tuning": groups[0]["tuning_name"] if groups else "",
                "best_demand_profile": groups[0]["demand_profile"] if groups else "",
                "summary_md": str(out_dir / "tuning_summary.md"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
