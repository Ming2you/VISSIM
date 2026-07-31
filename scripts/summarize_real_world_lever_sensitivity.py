#!/usr/bin/env python
"""Summarize real-world VISSIM lever sensitivity runs.

The run state logs are snapshots and may not land exactly on the requested
evaluation boundary, so integration clips every run to the same time window and
linearly interpolates the boundary values.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


RUNS = [
    "no_control_600s_seed13",
    "fixed57_600s_seed13",
    "signal_major_600s_seed13",
    "signal_offset30_600s_seed13",
    "vsl80_600s_seed13",
    "ramp_hold_600s_seed13",
    "pstack_v1_600s_seed13",
]

LABELS = {
    "no_control_600s_seed13": "no control(original VISSIG)",
    "fixed57_600s_seed13": "fixed57(COM SC1 57/57)",
    "signal_major_600s_seed13": "signal major 75/25",
    "signal_offset30_600s_seed13": "signal offset +30",
    "vsl80_600s_seed13": "VSL 80",
    "ramp_hold_600s_seed13": "ramp hold",
    "pstack_v1_600s_seed13": "P-Stack v1",
}

COUNT_COLS = [
    "total_vehicles",
    "freeway_vehicles",
    "urban_vehicles",
    "ramp_vehicles",
    "stopped_vehicles",
]


def fnum(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def rows_through_end(rows: list[dict[str, str]], *, end_sec: float) -> list[dict[str, str]]:
    filtered = [
        row
        for row in rows
        if (sim_sec := fnum(row.get("sim_sec"))) is not None and sim_sec <= end_sec
    ]
    return filtered or rows[:1]


def integrate_vehicle_hours(
    rows: list[dict[str, str]],
    col: str,
    *,
    start_sec: float,
    end_sec: float,
) -> float:
    pts: list[tuple[float, float]] = []
    for row in rows:
        t = fnum(row.get("sim_sec"))
        y = fnum(row.get(col))
        if t is not None and y is not None:
            pts.append((t, y))
    pts.sort()
    if not pts:
        return math.nan

    def value_at(target: float) -> float:
        if target <= pts[0][0]:
            return pts[0][1] if pts[0][0] <= 1.0e-9 else 0.0
        if target >= pts[-1][0]:
            return pts[-1][1]
        for (t0, y0), (t1, y1) in zip(pts, pts[1:]):
            if t0 <= target <= t1:
                if t1 <= t0:
                    return y1
                frac = (target - t0) / (t1 - t0)
                return y0 + frac * (y1 - y0)
        return pts[-1][1]

    pts = (
        [(start_sec, value_at(start_sec))]
        + [(t, y) for t, y in pts if start_sec < t < end_sec]
        + [(end_sec, value_at(end_sec))]
    )
    area = 0.0
    for (t0, y0), (t1, y1) in zip(pts, pts[1:]):
        area += (t1 - t0) * (y0 + y1) / 2.0
    return area / 3600.0


def summarize_state(base: Path, run: str, *, start_sec: float, end_sec: float) -> dict[str, Any]:
    rows = read_csv(base / f"state_{run}.csv")
    rows = rows_through_end(rows, end_sec=end_sec)
    window_rows = [
        row
        for row in rows
        if (sim_sec := fnum(row.get("sim_sec"))) is not None
        and start_sec <= sim_sec <= end_sec
    ]
    last = (window_rows or rows)[-1]
    rec: dict[str, Any] = {"run": run, "label": LABELS.get(run, run)}
    for col in COUNT_COLS:
        rec[col + "_h"] = integrate_vehicle_hours(rows, col, start_sec=start_sec, end_sec=end_sec)
    rec["ttt_veh_h"] = rec["total_vehicles_h"]
    rec["last_sim_sec"] = fnum(last.get("sim_sec"))
    rec["final_total"] = fnum(last.get("total_vehicles"))
    rec["final_fw"] = fnum(last.get("freeway_vehicles"))
    rec["final_urban"] = fnum(last.get("urban_vehicles"))
    rec["final_ramp"] = fnum(last.get("ramp_vehicles"))
    rec["final_stopped"] = fnum(last.get("stopped_vehicles"))
    speeds = [
        value
        for row in window_rows
        if (value := fnum(row.get("mean_speed_kph"))) is not None
    ]
    fw_speeds = [
        value
        for row in window_rows
        if (value := fnum(row.get("freeway_mean_speed_kph"))) is not None and value > 0
    ]
    rec["mean_speed_avg"] = statistics.mean(speeds) if speeds else math.nan
    rec["fw_speed_avg"] = statistics.mean(fw_speeds) if fw_speeds else math.nan
    return rec


def summarize_action(base: Path, run: str) -> dict[str, Any]:
    path = base / f"action_{run}.csv"
    if not path.exists():
        return {}
    rows = read_csv(path)
    counts = Counter(row.get("kind") for row in rows)
    readback_bad = 0
    for row in rows:
        readback = (row.get("readback") or "").strip()
        if not readback or any(marker in readback.upper() for marker in ("ERR", "FAIL")):
            readback_bad += 1
    vsl = [
        value
        for row in rows
        if row.get("kind") == "vsl" and (value := fnum(row.get("speed_kph"))) is not None
    ]
    ramp_green = [
        value
        for row in rows
        if row.get("kind") == "ramp_meter" and (value := fnum(row.get("green_sec"))) is not None
    ]
    ramp_rate = [
        value
        for row in rows
        if row.get("kind") == "ramp_meter" and (value := fnum(row.get("rate_vph"))) is not None
    ]
    signal_rows = [row for row in rows if row.get("kind") == "signal"]
    signal_major = [
        value
        for row in signal_rows
        if (value := fnum(row.get("major_green"))) is not None
    ]
    signal_minor = [
        value
        for row in signal_rows
        if (value := fnum(row.get("minor_green"))) is not None
    ]
    signal_offset = [
        value for row in signal_rows if (value := fnum(row.get("offset"))) is not None
    ]
    return {
        "rows_by_kind": dict(counts),
        "readback_bad": readback_bad,
        "vsl_unique": sorted({round(x, 3) for x in vsl}),
        "vsl_mean": statistics.mean(vsl) if vsl else math.nan,
        "ramp_green_unique": sorted({round(x, 3) for x in ramp_green}),
        "ramp_green_mean": statistics.mean(ramp_green) if ramp_green else math.nan,
        "ramp_rate_unique": sorted({round(x, 3) for x in ramp_rate}),
        "signal_count": len(signal_rows),
        "signal_major_unique": sorted({round(x, 3) for x in signal_major}),
        "signal_minor_unique": sorted({round(x, 3) for x in signal_minor}),
        "signal_offset_unique": sorted({round(x, 3) for x in signal_offset}),
        "signal_readbacks": dict(
            Counter((row.get("readback") or "").strip() for row in signal_rows)
        ),
    }


def summarize_pstack_decisions(
    base: Path,
    pstack_run: str = "pstack_v1_600s_seed13",
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    decision_dir = base / f"decisions_{pstack_run}"
    if not decision_dir.exists():
        return [], {}
    rows: list[dict[str, Any]] = []
    for path in sorted(decision_dir.glob("action_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        metadata = data.get("metadata", {})
        green_times = data.get("green_times", {})
        rows.append(
            {
                "name": path.name,
                "sim_sec": metadata.get("sim_sec"),
                "forecast_ramp_arrival_total_vph": metadata.get(
                    "forecast_ramp_arrival_total_vph"
                ),
                "local_observation_total_ramp_queue": metadata.get(
                    "local_observation_total_ramp_queue"
                ),
                "prediction_total_model_vehicles_abs_error": metadata.get(
                    "prediction_total_model_vehicles_abs_error"
                ),
                "prediction_protected_accumulation_abs_error": metadata.get(
                    "prediction_protected_accumulation_abs_error"
                ),
                "prediction_freeway_total_abs_error": metadata.get(
                    "prediction_freeway_total_abs_error"
                ),
                "leader_objective": metadata.get("leader_objective"),
                "nash_objective": metadata.get("nash_objective"),
                "decision_wall_sec": metadata.get("decision_wall_sec"),
                "signal_D_p1": green_times.get("D_p1"),
                "signal_D_p2": green_times.get("D_p2"),
                "vsl": data.get("vsl"),
                "ramp_metering": data.get("ramp_metering"),
            }
        )

    def mean_key(key: str) -> float:
        values = [value for row in rows if (value := fnum(row.get(key))) is not None]
        return statistics.mean(values) if values else math.nan

    aggregate = {
        key: mean_key(key)
        for key in [
            "forecast_ramp_arrival_total_vph",
            "local_observation_total_ramp_queue",
            "prediction_total_model_vehicles_abs_error",
            "prediction_protected_accumulation_abs_error",
            "prediction_freeway_total_abs_error",
            "leader_objective",
            "nash_objective",
            "decision_wall_sec",
        ]
    }
    return rows, aggregate


def fmt(value: float | int | None, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "nan"
    return f"{value:.{digits}f}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--start-sec", type=float, default=0.0)
    parser.add_argument("--end-sec", type=float, default=600.0)
    parser.add_argument(
        "--runs",
        default=",".join(RUNS),
        help="Comma-separated run-name suffixes matching state_<run>.csv.",
    )
    parser.add_argument(
        "--pstack-run",
        default="pstack_v1_600s_seed13",
        help="Run name used for optional P-Stack decision diagnostics.",
    )
    args = parser.parse_args()
    if args.start_sec < 0.0:
        raise SystemExit("--start-sec must be non-negative")
    if args.end_sec <= args.start_sec:
        raise SystemExit("--end-sec must be greater than --start-sec")

    run_names = [run.strip() for run in args.runs.split(",") if run.strip()]
    state_rows = [
        summarize_state(args.base, run, start_sec=args.start_sec, end_sec=args.end_sec)
        for run in run_names
    ]
    action_rows = {run: summarize_action(args.base, run) for run in run_names}
    base_ttt = state_rows[0]["ttt_veh_h"]
    fixed_row = next((row for row in state_rows if "fixed57" in row["run"]), None)
    fixed_ttt = fixed_row["ttt_veh_h"] if fixed_row is not None else base_ttt

    print("METRICS_TABLE")
    print(
        "run,label,TTT_veh_h,delta_vs_no,delta_pct,delta_vs_fixed57,"
        "fw_h,urban_h,ramp_h,stopped_h,final_total,final_stopped,avg_speed,avg_fw_speed"
    )
    for row in state_rows:
        delta_no = row["ttt_veh_h"] - base_ttt
        delta_fixed = row["ttt_veh_h"] - fixed_ttt
        pct = delta_no / base_ttt * 100.0 if base_ttt else math.nan
        print(
            ",".join(
                [
                    row["run"],
                    row["label"],
                    fmt(row["ttt_veh_h"]),
                    f"{delta_no:+.3f}",
                    f"{pct:+.2f}%",
                    f"{delta_fixed:+.3f}",
                    fmt(row["freeway_vehicles_h"]),
                    fmt(row["urban_vehicles_h"]),
                    fmt(row["ramp_vehicles_h"]),
                    fmt(row["stopped_vehicles_h"]),
                    f"{row['final_total']:.0f}",
                    f"{row['final_stopped']:.0f}",
                    fmt(row["mean_speed_avg"], 2),
                    fmt(row["fw_speed_avg"], 2),
                ]
            )
        )

    print("\nLEVER_DELTAS")
    for row in state_rows[1:]:
        delta_no = row["ttt_veh_h"] - base_ttt
        delta_fixed = row["ttt_veh_h"] - fixed_ttt
        print(
            f"{row['run']}: vs_no={delta_no:+.3f} veh-h "
            f"({delta_no / base_ttt * 100:+.2f}%), "
            f"vs_fixed57={delta_fixed:+.3f} veh-h "
            f"({delta_fixed / fixed_ttt * 100:+.2f}%)"
        )

    print("\nACTION_SUMMARY")
    for run in run_names:
        print(run, json.dumps(action_rows[run], ensure_ascii=False, sort_keys=True))

    pstack_rows, pstack_aggregate = summarize_pstack_decisions(args.base, args.pstack_run)
    if not pstack_rows:
        return 0
    print("\nPSTACK_DECISIONS")
    print(
        "name,sim_sec,forecast_ramp_vph,local_ramp_q,pred_abs,"
        "protected_abs,freeway_abs,D_p1,D_p2,vsl,ramp_metering"
    )
    for row in pstack_rows:
        print(
            ",".join(
                [
                    str(row["name"]),
                    str(row["sim_sec"]),
                    fmt(fnum(row["forecast_ramp_arrival_total_vph"])),
                    fmt(fnum(row["local_observation_total_ramp_queue"])),
                    fmt(fnum(row["prediction_total_model_vehicles_abs_error"])),
                    fmt(fnum(row["prediction_protected_accumulation_abs_error"])),
                    fmt(fnum(row["prediction_freeway_total_abs_error"])),
                    fmt(fnum(row["signal_D_p1"])),
                    fmt(fnum(row["signal_D_p2"])),
                    json.dumps(row["vsl"], sort_keys=True),
                    json.dumps(row["ramp_metering"], sort_keys=True),
                ]
            )
        )

    print("\nPSTACK_AGG")
    for key, value in pstack_aggregate.items():
        print(key, fmt(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
