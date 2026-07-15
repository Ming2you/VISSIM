from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def finite(values: Iterable[float]) -> list[float]:
    return [float(v) for v in values if math.isfinite(float(v))]


def positive_median(values: Iterable[float], default: float = 5.0) -> float:
    vals = sorted(v for v in finite(values) if v > 0.0)
    return float(median(vals)) if vals else float(default)


def weighted_mean(rows: list[dict[str, str]], key: str, dts: list[float]) -> float:
    den = sum(dts)
    if den <= 0.0:
        return 0.0
    return float(sum(to_float(row.get(key)) * dt for row, dt in zip(rows, dts)) / den)


def state_metrics(path: Path, warmup_sec: float) -> dict[str, Any]:
    rows = read_csv(path)
    if not rows:
        return {"state_rows": 0, "completed_sim_sec": 0.0, "ok": False}
    rows = sorted(rows, key=lambda row: to_float(row.get("sim_sec")))
    secs = [to_float(row.get("sim_sec")) for row in rows]
    default_dt = positive_median((b - a for a, b in zip(secs, secs[1:])), default=5.0)
    rows_after = [row for row in rows if to_float(row.get("sim_sec")) >= warmup_sec] or rows
    secs_after = [to_float(row.get("sim_sec")) for row in rows_after]
    dts = [
        max(0.0, secs_after[i + 1] - sec) if i + 1 < len(secs_after) else default_dt
        for i, sec in enumerate(secs_after)
    ]
    decision_walls = [to_float(row.get("decision_wall_sec")) for row in rows if to_float(row.get("decision_wall_sec")) > 0.0]
    statuses = sorted({str(row.get("controller_status", "")).strip() for row in rows if str(row.get("controller_status", "")).strip()})
    final = rows[-1]
    return {
        "ok": True,
        "state_rows": len(rows),
        "completed_sim_sec": max(secs),
        "warmup_sec": float(warmup_sec),
        "analysis_time_h": sum(dts) / 3600.0,
        "vehicle_hours_total": sum(to_float(row.get("total_vehicles")) * dt for row, dt in zip(rows_after, dts)) / 3600.0,
        "vehicle_hours_freeway": sum(to_float(row.get("freeway_vehicles")) * dt for row, dt in zip(rows_after, dts)) / 3600.0,
        "vehicle_hours_urban": sum(to_float(row.get("urban_vehicles")) * dt for row, dt in zip(rows_after, dts)) / 3600.0,
        "stopped_vehicle_hours": sum(to_float(row.get("stopped_vehicles")) * dt for row, dt in zip(rows_after, dts)) / 3600.0,
        "mean_total_vehicles": weighted_mean(rows_after, "total_vehicles", dts),
        "mean_freeway_vehicles": weighted_mean(rows_after, "freeway_vehicles", dts),
        "mean_urban_vehicles": weighted_mean(rows_after, "urban_vehicles", dts),
        "mean_ramp_vehicles": weighted_mean(rows_after, "ramp_vehicles", dts),
        "mean_boundary_vehicles": weighted_mean(rows_after, "boundary_vehicles", dts),
        "mean_speed_kph": weighted_mean(rows_after, "mean_speed_kph", dts),
        "freeway_mean_speed_kph": weighted_mean(rows_after, "freeway_mean_speed_kph", dts),
        "mean_stopped_vehicles": weighted_mean(rows_after, "stopped_vehicles", dts),
        "final_total_vehicles": to_float(final.get("total_vehicles")),
        "final_urban_vehicles": to_float(final.get("urban_vehicles")),
        "final_freeway_vehicles": to_float(final.get("freeway_vehicles")),
        "final_stopped_vehicles": to_float(final.get("stopped_vehicles")),
        "controller_statuses": "|".join(statuses),
        "fallback_state_rows": sum(1 for row in rows if str(row.get("controller_status", "")).strip() not in ("", "ok")),
        "mean_decision_wall_sec_state_csv": mean(decision_walls) if decision_walls else 0.0,
        "max_decision_wall_sec_state_csv": max(decision_walls) if decision_walls else 0.0,
    }


def action_metrics(path: Path) -> dict[str, Any]:
    rows = read_csv(path)
    if not rows:
        return {"action_rows": 0, "decision_count_action_csv": 0}
    by_sec: dict[float, dict[str, list[float]]] = {}
    for row in rows:
        sec = to_float(row.get("sim_sec"))
        by_sec.setdefault(sec, {
            "vsl": [],
            "ramp_green": [],
            "signal_green": [],
            "ramp_rate": [],
            "signal_split_abs": [],
            "signal_offset_abs": [],
        })
        kind = str(row.get("kind", ""))
        if kind == "vsl":
            by_sec[sec]["vsl"].append(to_float(row.get("speed_kph")))
        elif kind == "ramp_meter":
            by_sec[sec]["ramp_green"].append(to_float(row.get("green_sec")))
            by_sec[sec]["ramp_rate"].append(to_float(row.get("rate_vph")))
        elif kind == "signal":
            major = to_float(row.get("major_green"))
            minor = to_float(row.get("minor_green"))
            offset = to_float(row.get("offset"))
            by_sec[sec]["signal_green"].append(major)
            by_sec[sec]["signal_green"].append(minor)
            by_sec[sec]["signal_split_abs"].append(abs(major - minor))
            by_sec[sec]["signal_offset_abs"].append(abs(offset))
    secs = sorted(by_sec)

    def per_decision_mean(key: str) -> list[float]:
        return [mean(by_sec[sec][key]) for sec in secs if by_sec[sec][key]]

    def mean_abs_step(values: list[float]) -> float:
        diffs = [abs(b - a) for a, b in zip(values, values[1:])]
        return float(mean(diffs)) if diffs else 0.0

    vsl = per_decision_mean("vsl")
    ramp_green = per_decision_mean("ramp_green")
    ramp_rate = per_decision_mean("ramp_rate")
    signal_green = per_decision_mean("signal_green")
    signal_split_abs = per_decision_mean("signal_split_abs")
    signal_offset_abs = per_decision_mean("signal_offset_abs")
    return {
        "action_rows": len(rows),
        "decision_count_action_csv": len(secs),
        "mean_vsl_kph": mean(vsl) if vsl else 0.0,
        "mean_ramp_green_sec": mean(ramp_green) if ramp_green else 0.0,
        "mean_ramp_rate_vph": mean(ramp_rate) if ramp_rate else 0.0,
        "mean_signal_green_sec": mean(signal_green) if signal_green else 0.0,
        "mean_signal_split_abs_sec": mean(signal_split_abs) if signal_split_abs else 0.0,
        "mean_signal_offset_abs_sec": mean(signal_offset_abs) if signal_offset_abs else 0.0,
        "vsl_mean_abs_step_kph": mean_abs_step(vsl),
        "ramp_green_abs_step_sec": mean_abs_step(ramp_green),
        "ramp_rate_abs_step_vph": mean_abs_step(ramp_rate),
        "signal_green_abs_step_sec": mean_abs_step(signal_green),
        "signal_split_abs_step_sec": mean_abs_step(signal_split_abs),
        "signal_offset_abs_step_sec": mean_abs_step(signal_offset_abs),
    }


def decision_metrics(decision_dir: Path) -> dict[str, Any]:
    paths = sorted(decision_dir.glob("action_*.json"))
    if not paths:
        return {"decision_json_count": 0}
    statuses: list[str] = []
    variants: list[str] = []
    decision_wall: list[float] = []
    prediction_wall: list[float] = []
    prediction_total_abs: list[float] = []
    prediction_np_abs: list[float] = []
    prediction_freeway_abs: list[float] = []
    # Local-decomposition components (calibrated by the 0.90/0.20 observation split).
    # Reported separately from total mass so component improvements cannot hide behind
    # total_model_vehicles cancellation (see calibration observation.metric_scope).
    prediction_urban_storage_abs: list[float] = []
    prediction_urban_movement_queue_abs: list[float] = []
    prediction_urban_queue_plus_storage_abs: list[float] = []
    prediction_lags: list[float] = []
    wu_converged: list[float] = []
    wu_residual: list[float] = []
    wu_iterations: list[float] = []
    pfo_converged: list[float] = []
    pfo_res_obj: list[float] = []
    pfo_res_ctrl: list[float] = []
    pfo_iterations: list[float] = []
    controller_errors: list[str] = []

    for path in paths:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            controller_errors.append(f"{path.name}:{type(exc).__name__}")
            continue
        meta = raw.get("metadata", {})
        if isinstance(meta, dict):
            statuses.append(str(meta.get("controller_status", "")))
            variants.append(str(meta.get("controller_variant", "")))
            decision_wall.append(to_float(meta.get("decision_wall_sec")))
            prediction_wall.append(to_float(meta.get("prediction_wall_sec")))
            if "wu_converged" in meta:
                wu_converged.append(to_float(meta.get("wu_converged")))
                wu_residual.append(to_float(meta.get("wu_coupling_residual")))
                wu_iterations.append(to_float(meta.get("wu_iterations")))
            if "pfo_converged" in meta:
                pfo_converged.append(to_float(meta.get("pfo_converged")))
                pfo_res_obj.append(to_float(meta.get("pfo_residual_objective")))
                pfo_res_ctrl.append(to_float(meta.get("pfo_residual_control")))
                pfo_iterations.append(to_float(meta.get("pfo_iterations")))
            if meta.get("controller_error"):
                controller_errors.append(str(meta.get("controller_error")))
        err = raw.get("prediction_error", {})
        if isinstance(err, dict) and err.get("status") == "ok":
            prediction_lags.append(to_float(err.get("target_lag_sec")))
            scalar = err.get("scalar_errors", {})
            if isinstance(scalar, dict):
                prediction_total_abs.append(to_float((scalar.get("total_model_vehicles") or {}).get("abs_error")))
                prediction_np_abs.append(to_float((scalar.get("protected_accumulation_veh") or {}).get("abs_error")))
                prediction_freeway_abs.append(to_float((scalar.get("freeway_total_veh") or {}).get("abs_error")))
                prediction_urban_storage_abs.append(to_float((scalar.get("urban_link_occupancy_total_veh") or {}).get("abs_error")))
                prediction_urban_movement_queue_abs.append(to_float((scalar.get("urban_movement_queue_total_veh") or {}).get("abs_error")))
                prediction_urban_queue_plus_storage_abs.append(to_float((scalar.get("urban_queue_plus_link_occupancy_total_veh") or {}).get("abs_error")))

    def avg(values: list[float]) -> float:
        vals = finite(values)
        return float(mean(vals)) if vals else 0.0

    def maxv(values: list[float]) -> float:
        vals = finite(values)
        return float(max(vals)) if vals else 0.0

    return {
        "decision_json_count": len(paths),
        "controller_variants": "|".join(sorted(set(v for v in variants if v))),
        "controller_statuses_json": "|".join(sorted(set(v for v in statuses if v))),
        "controller_error_count": len(controller_errors),
        "controller_error_sample": controller_errors[0] if controller_errors else "",
        "mean_decision_wall_sec": avg(decision_wall),
        "max_decision_wall_sec": maxv(decision_wall),
        "mean_prediction_wall_sec": avg(prediction_wall),
        "prediction_error_count": len(prediction_total_abs),
        "prediction_lag_max_abs_sec": maxv([abs(v) for v in prediction_lags]),
        "prediction_total_abs_error_mean_veh": avg(prediction_total_abs),
        "prediction_total_abs_error_max_veh": maxv(prediction_total_abs),
        "prediction_np_abs_error_mean_veh": avg(prediction_np_abs),
        "prediction_freeway_abs_error_mean_veh": avg(prediction_freeway_abs),
        "prediction_urban_storage_abs_error_mean_veh": avg(prediction_urban_storage_abs),
        "prediction_urban_movement_queue_abs_error_mean_veh": avg(prediction_urban_movement_queue_abs),
        "prediction_urban_queue_plus_storage_abs_error_mean_veh": avg(prediction_urban_queue_plus_storage_abs),
        "wu_convergence_rate": avg(wu_converged),
        "wu_residual_mean": avg(wu_residual),
        "wu_residual_max": maxv(wu_residual),
        "wu_iterations_mean": avg(wu_iterations),
        "pfo_convergence_rate": avg(pfo_converged),
        "pfo_residual_objective_mean": avg(pfo_res_obj),
        "pfo_residual_control_mean": avg(pfo_res_ctrl),
        "pfo_iterations_mean": avg(pfo_iterations),
    }


def summarize(run_dir: Path, warmup_sec: float) -> dict[str, Any]:
    out = {
        "run_dir": str(run_dir),
        "state_csv": str(run_dir / "state.csv"),
        "action_csv": str(run_dir / "action.csv"),
        "decision_dir": str(run_dir / "decisions"),
    }
    # Some older batch runs use actions.csv.
    action_csv = run_dir / "action.csv"
    if not action_csv.exists() and (run_dir / "actions.csv").exists():
        action_csv = run_dir / "actions.csv"
        out["action_csv"] = str(action_csv)
    out.update(state_metrics(run_dir / "state.csv", warmup_sec=warmup_sec))
    out.update(action_metrics(action_csv))
    out.update(decision_metrics(run_dir / "decisions"))
    out["primary_rank_key"] = (
        to_float(out.get("vehicle_hours_total"))
        + 0.25 * to_float(out.get("stopped_vehicle_hours"))
        + 1000.0 * to_float(out.get("fallback_state_rows"))
        + 1000.0 * to_float(out.get("controller_error_count"))
    )
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dirs", nargs="+")
    parser.add_argument("--warmup-sec", type=float, default=300.0)
    parser.add_argument("--out-json", default="")
    parser.add_argument("--out-csv", default="")
    args = parser.parse_args()

    rows = [summarize(Path(item), warmup_sec=float(args.warmup_sec)) for item in args.run_dirs]
    payload = {"status": "ok", "warmup_sec": float(args.warmup_sec), "runs": rows}
    if args.out_json:
        out = Path(args.out_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.out_csv:
        write_csv(Path(args.out_csv), rows)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
