"""Replay nc_190w recorded states through the model with candidate tunings.

Question (2026-07-15): is the urban mass over-prediction a movement-capacity
structural artifact? Every movement discharges at min(queue, green_fraction x
movement_capacity_veh_h) with a SINGLE shared constant (1800 via adapter), so a
movement carrying ~76% of a gate's flow saturates in the model (~855 veh/h at
green 0.475) while the real 2-lane VISSIM approach serves ~2x that. Uniform
ratios spread demand below the per-movement cap, hiding the error.

Replay: for each recorded nc_190w decision state (plant ran fixed-time), call
the adapter with --controller no-control (same control as plant) and a
candidate tuning; the adapter chains prediction_error against the previous
replay output. Compare urban bias across candidates.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from statistics import mean

WORKSPACE = Path(__file__).resolve().parents[1]
ADAPTER = WORKSPACE / "evaluation/controllers/vissim_stackelberg_adapter.py"
CALIB = WORKSPACE / "evaluation/calibration/vissim_network_calibration_v2_8seg_20260714.json"
import os
DEC_DIR = WORKSPACE / os.environ.get("REPLAY_DEC", "evaluation/runs/8seg_sweet_w_20260714/decisions_nc_190w")
OUT_ROOT = WORKSPACE / os.environ.get("REPLAY_OUT", "evaluation/runs/8seg_sweet_w_20260714/replay_discharge_hypothesis")

METRICS = [
    "total_model_vehicles",
    "urban_total_veh",
    "urban_movement_queue_total_veh",
    "urban_link_occupancy_total_veh",
    "boundary_queue_total_veh",
    "freeway_total_veh",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", nargs="+", required=True, help="tuning json paths (name = stem)")
    parser.add_argument("--t-min", type=int, default=3600)
    parser.add_argument("--t-max", type=int, default=10800)
    args = parser.parse_args()

    states = sorted(DEC_DIR.glob("state_*.json"), key=lambda p: int(p.stem.split("_")[1]))
    states = [p for p in states if args.t_min <= int(p.stem.split("_")[1]) <= args.t_max]
    print(f"states in window: {len(states)}")

    summary_rows = []
    for cand_path in map(Path, args.candidates):
        name = cand_path.stem.replace("replay_cand_", "")
        out_dir = OUT_ROOT / name
        out_dir.mkdir(parents=True, exist_ok=True)
        prev_action = ""
        per = {m: [] for m in METRICS}
        n_fail = 0
        for sp in states:
            t = int(sp.stem.split("_")[1])
            out_json = out_dir / f"action_{t:06d}.json"
            out_csv = out_dir / f"action_{t:06d}.csv"
            cmd = [
                sys.executable, str(ADAPTER),
                "--state-json", str(sp),
                "--out-action-json", str(out_json),
                "--out-action-csv", str(out_csv),
                "--controller", "no-control",
                "--calibration-json", str(CALIB),
            ]
            if str(cand_path) and cand_path.stat().st_size > 3:
                cmd += ["--tuning-json", str(cand_path)]
            if prev_action:
                cmd += ["--previous-action-json", prev_action]
            r = subprocess.run(cmd, text=True, capture_output=True)
            if r.returncode != 0:
                n_fail += 1
                prev_action = ""
                continue
            prev_action = str(out_json)
            try:
                d = json.loads(out_json.read_text(encoding="utf-8"))
            except Exception:
                n_fail += 1
                continue
            pe = d.get("prediction_error", {})
            if pe.get("status") != "ok":
                continue
            # raw prediction for the SAME target, from the previous replay output
            se = pe.get("scalar_errors", {})
            for m in METRICS:
                e = se.get(m, {})
                if isinstance(e, dict) and "observed" in e:
                    per[m].append((float(e.get("predicted", 0.0)), float(e["observed"])))
        print(f"--- {name} (fails={n_fail}) ---")
        for m in METRICS:
            rows = per[m]
            if not rows:
                continue
            bias = mean(o - p for p, o in rows)
            mae = mean(abs(o - p) for p, o in rows)
            obs = mean(o for _, o in rows)
            print(f"  {m:42s} bias={bias:+8.1f}  MAE={mae:7.1f}  ({100*mae/max(1e-9,obs):5.1f}% of obs {obs:7.1f})")
            summary_rows.append({"candidate": name, "metric": m, "bias": bias, "mae": mae, "obs_mean": obs})

    out_csv = OUT_ROOT / "summary.csv"
    import csv as _csv
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        w = _csv.DictWriter(fh, fieldnames=["candidate", "metric", "bias", "mae", "obs_mean"])
        w.writeheader()
        w.writerows(summary_rows)
    print("WROTE", out_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
