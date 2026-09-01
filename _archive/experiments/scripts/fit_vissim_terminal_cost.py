from __future__ import annotations

import argparse
import csv
import glob
import json
import math
from pathlib import Path
from typing import Any


DEFAULT_FEATURES = [
    "total_vehicles",
    "urban_vehicles",
    "freeway_vehicles",
    "ramp_vehicles",
    "boundary_vehicles",
    "stopped_vehicles",
    "mean_speed_kph",
    "freeway_mean_speed_kph",
]


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def read_state_csv(path: Path) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if "sim_sec" not in row or "total_vehicles" not in row:
                continue
            rows.append({str(key): to_float(value) for key, value in row.items() if key})
    rows.sort(key=lambda item: item.get("sim_sec", 0.0))
    return rows


def future_vehicle_hours(rows: list[dict[str, float]], index: int, horizon_sec: float) -> float | None:
    start = rows[index]["sim_sec"]
    end = start + horizon_sec
    if not rows or end > rows[-1]["sim_sec"]:
        return None
    total = 0.0
    for j in range(index, len(rows) - 1):
        t0 = max(start, rows[j]["sim_sec"])
        t1 = min(end, rows[j + 1]["sim_sec"])
        if t1 > t0:
            total += max(0.0, rows[j]["total_vehicles"]) * (t1 - t0) / 3600.0
        if rows[j + 1]["sim_sec"] >= end:
            break
    return total


def expand_paths(values: list[str]) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for value in values:
        matches = [Path(item) for item in glob.glob(value)] if any(ch in value for ch in "*?[]") else [Path(value)]
        for path in matches:
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                paths.append(path)
    return paths


def build_samples(
    paths: list[Path],
    features: list[str],
    horizon_sec: float,
    min_sim_sec: float,
) -> tuple[list[list[float]], list[float], list[dict[str, Any]]]:
    x_rows: list[list[float]] = []
    y_values: list[float] = []
    meta: list[dict[str, Any]] = []
    for path in paths:
        rows = read_state_csv(path)
        used = 0
        for index, row in enumerate(rows):
            sim_sec = row.get("sim_sec", 0.0)
            if sim_sec < min_sim_sec:
                continue
            target = future_vehicle_hours(rows, index, horizon_sec)
            if target is None:
                continue
            x_rows.append([row.get(feature, 0.0) for feature in features])
            y_values.append(float(target))
            meta.append({"case": path.stem, "path": str(path), "sim_sec": sim_sec})
            used += 1
        if used == 0:
            print(f"warning: no usable samples from {path}")
    return x_rows, y_values, meta


def feature_stats(x_rows: list[list[float]]) -> tuple[list[float], list[float]]:
    count = len(x_rows)
    width = len(x_rows[0]) if x_rows else 0
    means = [sum(row[j] for row in x_rows) / max(1, count) for j in range(width)]
    stds: list[float] = []
    for j, mean in enumerate(means):
        var = sum((row[j] - mean) ** 2 for row in x_rows) / max(1, count)
        std = math.sqrt(var)
        stds.append(std if std > 1.0e-9 else 1.0)
    return means, stds


def solve_linear_system(a: list[list[float]], b: list[float]) -> list[float]:
    n = len(b)
    aug = [list(row) + [float(b[i])] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(aug[row][col]))
        if abs(aug[pivot][col]) < 1.0e-12:
            aug[pivot][col] = 1.0e-12
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        pivot_value = aug[col][col]
        for item in range(col, n + 1):
            aug[col][item] /= pivot_value
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            if factor == 0.0:
                continue
            for item in range(col, n + 1):
                aug[row][item] -= factor * aug[col][item]
    return [aug[i][n] for i in range(n)]


def fit_ridge(
    x_rows: list[list[float]],
    y_values: list[float],
    means: list[float],
    stds: list[float],
    ridge: float,
) -> tuple[list[float], list[float]]:
    width = len(means)
    xtx = [[0.0 for _ in range(width + 1)] for _ in range(width + 1)]
    xty = [0.0 for _ in range(width + 1)]
    for row, target in zip(x_rows, y_values):
        z = [1.0] + [(row[j] - means[j]) / stds[j] for j in range(width)]
        for i, zi in enumerate(z):
            xty[i] += zi * target
            for j, zj in enumerate(z):
                xtx[i][j] += zi * zj
    for j in range(1, width + 1):
        xtx[j][j] += ridge
    standardized = solve_linear_system(xtx, xty)
    raw = [standardized[0]]
    for j in range(width):
        coef = standardized[j + 1] / stds[j]
        raw.append(coef)
        raw[0] -= coef * means[j]
    return standardized, raw


def predict(raw: list[float], x_rows: list[list[float]]) -> list[float]:
    out: list[float] = []
    for row in x_rows:
        out.append(raw[0] + sum(raw[j + 1] * value for j, value in enumerate(row)))
    return out


def metrics(y_true: list[float], y_pred: list[float]) -> dict[str, float]:
    if not y_true:
        return {"n": 0.0, "mae": 0.0, "rmse": 0.0, "r2": 0.0}
    errors = [pred - true for true, pred in zip(y_true, y_pred)]
    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = math.sqrt(sum(error * error for error in errors) / len(errors))
    mean_y = sum(y_true) / len(y_true)
    ss_res = sum(error * error for error in errors)
    ss_tot = sum((value - mean_y) ** 2 for value in y_true)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1.0e-12 else 0.0
    return {"n": float(len(y_true)), "mae": mae, "rmse": rmse, "r2": r2}


def per_case_metrics(meta: list[dict[str, Any]], y_true: list[float], y_pred: list[float]) -> dict[str, dict[str, float]]:
    grouped: dict[str, tuple[list[float], list[float]]] = {}
    for item, true, pred in zip(meta, y_true, y_pred):
        key = str(item["case"])
        if key not in grouped:
            grouped[key] = ([], [])
        grouped[key][0].append(true)
        grouped[key][1].append(pred)
    return {case: metrics(values[0], values[1]) for case, values in sorted(grouped.items())}


def write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# VISSIM Terminal Cost Fit",
        "",
        f"- horizon_sec: {result['horizon_sec']}",
        f"- samples: {int(result['metrics']['n'])}",
        f"- rmse_vehicle_hours: {result['metrics']['rmse']:.6f}",
        f"- mae_vehicle_hours: {result['metrics']['mae']:.6f}",
        f"- r2: {result['metrics']['r2']:.6f}",
        "",
        "## Raw Linear Coefficients",
        "",
        "| term | vehicle_hours coefficient |",
        "|---|---:|",
        f"| intercept | {result['raw_intercept']:.9f} |",
    ]
    for feature, value in result["raw_coefficients"].items():
        lines.append(f"| {feature} | {value:.9f} |")
    lines.extend([
        "",
        "## Standardized Coefficients",
        "",
        "| feature | standardized coefficient |",
        "|---|---:|",
    ])
    for feature, value in result["standardized_coefficients"].items():
        lines.append(f"| {feature} | {value:.9f} |")
    lines.extend([
        "",
        "## Per Case Fit",
        "",
        "| case | n | rmse | mae | r2 |",
        "|---|---:|---:|---:|---:|",
    ])
    for case, values in result["per_case_metrics"].items():
        lines.append(
            f"| {case} | {int(values['n'])} | {values['rmse']:.6f} | "
            f"{values['mae']:.6f} | {values['r2']:.6f} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fit a VISSIM-observed terminal-cost proxy from state CSV logs."
    )
    parser.add_argument("--state-csv", action="append", default=[], help="State CSV path; may be repeated.")
    parser.add_argument("--state-glob", action="append", default=[], help="Glob for state CSV paths; may be repeated.")
    parser.add_argument("--horizon-sec", type=float, default=300.0)
    parser.add_argument("--min-sim-sec", type=float, default=0.0)
    parser.add_argument("--ridge", type=float, default=1.0e-3)
    parser.add_argument("--features", default=",".join(DEFAULT_FEATURES))
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", default="")
    args = parser.parse_args()

    features = [item.strip() for item in args.features.split(",") if item.strip()]
    paths = expand_paths(args.state_csv + args.state_glob)
    if not paths:
        raise SystemExit("no state CSV paths provided")

    x_rows, y_values, meta = build_samples(paths, features, args.horizon_sec, args.min_sim_sec)
    if len(x_rows) <= len(features) + 1:
        raise SystemExit(f"not enough samples to fit {len(features)} features: {len(x_rows)}")

    means, stds = feature_stats(x_rows)
    standardized, raw = fit_ridge(x_rows, y_values, means, stds, args.ridge)
    y_pred = predict(raw, x_rows)
    result = {
        "horizon_sec": float(args.horizon_sec),
        "min_sim_sec": float(args.min_sim_sec),
        "ridge": float(args.ridge),
        "features": features,
        "state_csvs": [str(path) for path in paths],
        "metrics": metrics(y_values, y_pred),
        "per_case_metrics": per_case_metrics(meta, y_values, y_pred),
        "feature_means": dict(zip(features, means)),
        "feature_stds": dict(zip(features, stds)),
        "raw_intercept": raw[0],
        "raw_coefficients": dict(zip(features, raw[1:])),
        "standardized_intercept": standardized[0],
        "standardized_coefficients": dict(zip(features, standardized[1:])),
    }

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    if args.out_md:
        write_markdown(Path(args.out_md), result)
    print(json.dumps({"status": "ok", "samples": len(x_rows), "out_json": str(out_json)}, indent=2))


if __name__ == "__main__":
    main()
