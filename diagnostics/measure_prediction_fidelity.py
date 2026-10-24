"""Replay one executed control interval and compare cell predictions with VISSIM.

Every interval starts from its own observed state. This measures prediction and
actuation mismatch jointly; it neither fits parameters nor claims a counterfactual
VISSIM result. Future control decisions are never used in the forecast.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "diagnostics"), str(ROOT / "vendor/NumSim-mine")]
from probe_model_area_integration import build_projected
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from src.controllers import rollout_endpoint
from src.models.demand import DemandStep
from src.models.state import ControlAction
from src.simulation import coupling


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", default="codex_n7_pure_s13_20260910")
    parser.add_argument("--config", type=Path, default=Path("evaluation/configs/n21_n7_20260908.json"))
    parser.add_argument("--output-prefix", default="n7_prediction_fidelity")
    parser.add_argument("--start-sec", type=int, default=900)
    parser.add_argument("--end-sec", type=int, default=5250)
    args = parser.parse_args()
    directory = ROOT / "evaluation/runs" / args.run
    decisions = directory / f"decisions_{args.run}"
    segment_path = directory / f"bottleneck_segments_{args.run}.csv"
    with segment_path.open(encoding="utf-8-sig", newline="") as stream:
        observed = {(int(row["sim_sec"]), row["model_link"], int(row["segment_index"])): row
                    for row in csv.DictReader(stream)}
    records, input_hashes = [], {}
    for state_path in sorted(decisions.glob("state_*.json")):
        raw_time = int(state_path.stem.split("_")[-1])
        if not args.start_sec <= raw_time <= min(args.end_sec, 5250):
            continue
        action_path = decisions / f"action_{raw_time:06d}.json"
        earlier = [p for p in decisions.glob("action_*.json") if int(p.stem.split("_")[-1]) < raw_time]
        previous = max(earlier, key=lambda p: int(p.stem.split("_")[-1]))
        cfg, state, detectors, tuning, raw, _, _ = build_projected(ROOT / args.config, state_path, previous)
        action = adapter.control_from_json(action_path, cfg, ControlAction)
        calibration = adapter.load_optional_json(str(ROOT / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"))
        calibration = adapter.deep_update(dict(calibration), tuning.get("calibration_override", {}))
        forecast = adapter.demand_from_state(raw, cfg, DemandStep, 1, calibration, detectors)
        original_step = coupling.freeway_substep
        trace = [(0, state.copy())]
        calls = 0

        def traced_step(*step_args, **kwargs):
            nonlocal calls
            result = original_step(*step_args, **kwargs)
            calls += 1
            elapsed = round(calls * cfg.simulation.T_f_sec)
            if elapsed % 30 == 0:
                trace.append((elapsed, step_args[0].copy()))
            return result

        with patch.object(coupling, "freeway_substep", traced_step):
            result = rollout_endpoint.evaluate_price_point(
                state, action, forecast, [],
                rollout_endpoint.ObjectiveSpec(cfg, depth_override=1, box_walk=False, score_mode="raw"))
        if calls != cfg.simulation.K_cf or result.aborted:
            raise RuntimeError(f"Incomplete actual endpoint at {raw_time}: {calls}")
        for field in ("freeway_speed", "freeway_density"):
            if getattr(trace[-1][1], field) != getattr(result.states[-1], field):
                raise RuntimeError(f"Trace/end-state disagreement in {field} at {raw_time}")
        for elapsed, predicted in trace:
            for link in cfg.network.freeway_links:
                for cell in range(cfg.network.freeway_segments_per_link):
                    actual = observed[(raw_time + elapsed, link, cell)]
                    records.append(dict(start_sec=raw_time, horizon_sec=elapsed, sim_sec=raw_time + elapsed,
                        model_link=link, cell=cell, observed_count=float(actual["count"]),
                        observed_speed_kph=float(actual["mean_speed_kph"]),
                        predicted_speed_kph=float(predicted.freeway_speed[link][cell]),
                        observed_density=float(actual["density_veh_km_lane"]),
                        predicted_density=float(predicted.freeway_density[link][cell])))
        for path in (state_path, action_path):
            input_hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f"replayed {raw_time} -> {raw_time + 150}", flush=True)
    prefix = ROOT / "diagnostics" / args.output_prefix
    if not records:
        raise ValueError("No observed intervals selected")
    with prefix.with_suffix(".csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    groups = defaultdict(list)
    for row in records:
        if row["model_link"] == "FW_E" and 5 <= row["cell"] <= 10 and row["observed_count"] >= 5:
            regime = "before_breakdown" if row["start_sec"] < 1290 else "after_breakdown"
            groups[(regime, row["cell"], row["horizon_sec"])].append(row)
    summary = []
    for (regime, cell, horizon), rows in sorted(groups.items()):
        errors = [r["predicted_speed_kph"] - r["observed_speed_kph"] for r in rows]
        rho_errors = [r["predicted_density"] - r["observed_density"] for r in rows]
        summary.append(dict(regime=regime, cell=cell, horizon_sec=horizon, samples=len(rows),
            speed_bias_kph=sum(errors)/len(errors), speed_mae_kph=sum(abs(x) for x in errors)/len(errors),
            density_bias=sum(rho_errors)/len(rho_errors), density_mae=sum(abs(x) for x in rho_errors)/len(rho_errors)))
    runtime_paths = [ROOT / args.config, adapter.signal_group_actuation_plan_path(),
        ROOT / "evaluation/parameters.json",
        ROOT / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json",
        ROOT / tuning["mapping_json"], ROOT / tuning["detector_mapping_json"],
        *sorted((ROOT / "evaluation/controllers").glob("*.py"))]
    runtime_hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in runtime_paths}
    payload = dict(run=args.run, config=str(args.config), intervals=len(input_hashes)//2,
        method="Observed initial state, actual same-interval action JSON, current-rate demand forecast, production endpoint 150s; read-only substep trace.",
        limitations=["One seed; intervals/cells are correlated, not independent replicates.",
            "Includes known model/writer timing and projection mismatch; this is not pure FD parameter error.",
            "After/before refers to interval start relative to first persistent E8 event at 1290s.",
            "Speed metrics exclude observed cells with fewer than five vehicles; no data are imputed."],
        resolved_tuning_sha256=hashlib.sha256(json.dumps(tuning, sort_keys=True).encode()).hexdigest(),
        source_sha256={**input_hashes, **runtime_hashes,
            str(segment_path.relative_to(ROOT)): hashlib.sha256(segment_path.read_bytes()).hexdigest()},
        rows=summary)
    prefix.with_suffix(".json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    sys.path.append(str(ROOT / ".review-deps"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), sharex=True)
    for column, cell in enumerate((7, 8, 9)):
        series = [r for r in records if r["model_link"] == "FW_E" and r["cell"] == cell
                  and r["horizon_sec"] == 150]
        times = [r["start_sec"]/60 for r in series]
        for axis, metric, unit in ((axes[0, column], "speed_kph", "Speed (km/h)"),
                                  (axes[1, column], "density", "Density (veh/km/lane)")):
            axis.plot(times, [r[f"observed_{metric}"] for r in series], color="#555555", label="VISSIM +150s")
            axis.plot(times, [r[f"predicted_{metric}"] for r in series], color="#b74830", label="Model +150s")
            axis.set_title(f"FW_E cell {cell}")
            axis.set_ylabel(unit)
            axis.grid(alpha=.2)
        axes[1, column].set_xlabel("Observed initial time (min)")
    axes[0, 0].legend()
    fig.suptitle("N7 seed 13: one-interval prediction from observed state and executed action")
    fig.tight_layout()
    fig.savefig(prefix.with_suffix(".png"), dpi=160)
    plt.close(fig)
    print(json.dumps([x for x in summary if x['horizon_sec']==150 and x['cell'] in (5,8,9,10)], indent=2))


if __name__ == "__main__":
    main()
