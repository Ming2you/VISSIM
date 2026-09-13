"""Bounded held-action endpoint experiment; never installs a production change.

The zero multiplier is a limiting identification ablation, NOT a calibrated
parameter or a proposed capacity. It removes only positive anticipation. All
other canonical speed terms, accepted-flow rules and conservation stay intact.
"""
from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager
import csv
import hashlib
import inspect
import json
import os
from pathlib import Path
import pickle
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/NumSim-mine")]
from diagnostics.probe_model_area_integration import build_projected, replay_provenance
from evaluation.controllers import vissim_stackelberg_adapter as adapter, signal_actuation_contract
from src.controllers import rollout_endpoint as endpoint
from src.models import metanet
from src.models.state import ControlAction
from src.models.demand import DemandStep
from src.simulation import coupling


def digest(value):
    return hashlib.sha256(pickle.dumps(value)).hexdigest()


def accelerating_nu(rho, downstream_rho, nu, factor):
    if not 0.0 <= factor <= 1.0:
        raise ValueError("Diagnostic positive-anticipation multiplier must be in [0,1]")
    return nu * factor if downstream_rho < rho else nu


@contextmanager
def positive_anticipation(factor):
    """Temporarily wrap the *already installed* function, preserving cell context."""
    accelerating_nu(1.0, 0.0, 1.0, factor)
    original = metanet.metanet_speed_update_kmh
    calls = []

    def speed_update(speed, upstream_speed, rho, downstream_rho, v_eff, dt_h,
                     length_km, tau_h, nu_km2_h, kappa_veh_km_lane, v_min):
        selected = accelerating_nu(rho, downstream_rho, nu_km2_h, factor)
        parent = inspect.currentframe().f_back
        owner = parent
        while owner is not None and owner.f_code.co_name not in ("freeway_substep", "_freeway_substep_events"):
            owner = owner.f_back
        values = owner.f_locals if owner is not None else {}
        result = original(speed, upstream_speed, rho, downstream_rho, v_eff, dt_h,
                          length_km, tau_h, selected, kappa_veh_km_lane, v_min)
        if values.get("link") == "FW_E" and values.get("i") in (7, 8, 9):
            calls.append({"cell": values["i"], "speed_before": speed, "rho": rho,
                          "downstream_rho": downstream_rho, "upstream_speed": upstream_speed,
                          "v_eff": v_eff, "nu_original": nu_km2_h, "nu_passed": selected,
                          "speed_before_merge": result})
        del owner, parent
        return result

    owners = [module for module in tuple(sys.modules.values())
              if getattr(module, "metanet_speed_update_kmh", None) is original]
    for module in owners:
        module.metanet_speed_update_kmh = speed_update
    try:
        yield calls
    finally:
        for module in owners:
            assert module.metanet_speed_update_kmh is speed_update
            module.metanet_speed_update_kmh = original


@contextmanager
def trace_freeway(cfg):
    original = coupling.freeway_substep
    rows = []

    def traced(state, control, demand, cfg, *args, **kwargs):
        # Neither this state nor the returned diagnostics are modified.
        before = {link: sum(max(0.0, rho) * cfg.network.freeway_segment_length_km * max(lane, 1e-9)
                            for rho, lane in zip(state.freeway_density[link], state.freeway_effective_lanes[link]))
                  for link in cfg.network.freeway_links}
        result = original(state, control, demand, cfg, *args, **kwargs)
        rows.append({"elapsed_sec": (len(rows) + 1) * cfg.simulation.T_f_sec,
                     "applied_action": action_vector(control),
                     "freeway_density": copy.deepcopy(state.freeway_density),
                     "freeway_speed": copy.deepcopy(state.freeway_speed),
                     "freeway_flow": copy.deepcopy(state.freeway_flow),
                     "freeway_effective_lanes": copy.deepcopy(state.freeway_effective_lanes),
                     "ramp_queue": dict(state.ramp_queue), "stock_before_by_link": before,
                     "substep_ttt": result[0], "diagnostics": dict(result[1])})
        return result

    coupling.freeway_substep = traced
    try:
        yield rows
    finally:
        assert coupling.freeway_substep is traced
        coupling.freeway_substep = original


def action_vector(control):
    return {key: copy.deepcopy(getattr(control, key)) for key in
            ("green_times", "ramp_metering", "vsl", "offsets") if hasattr(control, key)}


def run(args):
    started = time.monotonic()
    os.environ["RW_MAINLINE_SG_ONLY"] = "1"
    config = ROOT / args.config
    run_dir = ROOT / "evaluation/runs" / args.run
    decisions = run_dir / ("decisions_" + args.run)
    state_path, action_path, previous = (decisions / f"{kind}_{sec:06d}.json" for kind, sec in
                                         (("state", args.start), ("action", args.start), ("action", args.start - 150)))
    cfg, state, detectors, tuning, raw, mapping, metadata = build_projected(config, state_path, previous, fixture_inputs=False)
    writer = tuning.get("actuation", {}).get("real_world_signal_control", {}).get("offset_writer", "intent_only")
    os.environ["RW_OFFSET_WRITER"] = writer
    action = adapter.control_from_json(action_path, cfg, ControlAction)
    recorded = action_vector(action)
    if signal_actuation_contract.enabled(cfg.network):
        action = signal_actuation_contract.prepare_control(action, cfg)
    calibration = adapter.load_optional_json(str(ROOT / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"))
    calibration = adapter.deep_update(dict(calibration), tuning.get("calibration_override", {}))
    forecast = adapter.demand_from_state(raw, cfg, DemandStep, 3, calibration, detectors)
    inputs = (cfg, state, action, forecast)
    initial_hash = digest(inputs)
    sources = replay_provenance(tuning, config, state_path, action_path, previous, Path(__file__))
    scenarios = {}
    for name, factor in (("canonical", 1.0), ("positive_anticipation_zero", 0.0)):
        private_cfg, private_state, private_action, private_forecast = copy.deepcopy(inputs)
        # Existing meter finalization may alter candidates; record the actual
        # result control explicitly, and require the paired arms to match.
        with positive_anticipation(factor) as speed_calls, trace_freeway(private_cfg) as rows:
            point = endpoint.evaluate_price_point(private_state, private_action, private_forecast, (),
                endpoint.ObjectiveSpec(private_cfg, depth_override=3, box_walk=False, score_mode="raw"))
        assert not point.aborted and len(rows) == 3 * cfg.simulation.K_cf
        if hasattr(point.states[-1], "_control_area_ledger"):
            from evaluation.controllers import area_runtime
            point.states[-1]._control_area_ledger.assert_stocks(area_runtime.model_inventory(point.states[-1], private_cfg))
        assert digest(inputs) == initial_hash, "Caller-owned cfg/state/action/demand mutated"
        scenarios[name] = {"factor": factor, "objective": point.objective, "ttt": point.ttt,
                           "freeway_ttt": point.freeway_ttt, "urban_ttt": point.urban_ttt,
                           "area_metrics": getattr(point, "control_area", None),
                           "stock_closure_checked": hasattr(point.states[-1], "_control_area_ledger"),
                           "finalized_action": action_vector(point.control),
                           "macro_states": [{"time_sec": s.time_sec,
                                             "freeway_density": s.freeway_density, "freeway_speed": s.freeway_speed}
                                            for s in point.states],
                           "rows": rows, "speed_calls": speed_calls}
    assert scenarios["canonical"]["finalized_action"] == scenarios["positive_anticipation_zero"]["finalized_action"]
    assert [row["applied_action"] for row in scenarios["canonical"]["rows"]] == [row["applied_action"] for row in scenarios["positive_anticipation_zero"]["rows"]]
    after = replay_provenance(tuning, config, state_path, action_path, previous, Path(__file__))
    assert all(after.get(path) == value for path, value in sources.items()), "Input/source bytes changed"
    observed_path = run_dir / f"bottleneck_segments_{args.run}.csv"
    with observed_path.open(encoding="utf-8-sig", newline="") as stream:
        observed = [row for row in csv.DictReader(stream)
                    if args.start <= float(row["sim_sec"]) <= args.start + 450]
    sources[str(observed_path.relative_to(ROOT))] = hashlib.sha256(observed_path.read_bytes()).hexdigest()
    result = {"run": args.run, "start_sec": args.start, "horizon_sec": 450,
              "definition": "Single canonical endpoint, three 150-second intervals, held seed action, current-rate demand persistence; only positive anticipation multiplied by 0 in the second arm.",
              "interpretation": "Zero is a limiting sensitivity ablation, not an identified model parameter or validated repair.",
              "comparison_limit": "Recorded plant actions can change after +150; +450 plant comparison for pure n7 is observational, not a held-action counterfactual.",
              "config_path": str(config.relative_to(ROOT)), "source_sha256": sources,
              "recorded_action": recorded, "prepared_action": action_vector(action),
              "input_hash_unchanged": initial_hash, "source_unchanged": True,
              "metadata": metadata, "observed_rows": observed, "scenarios": scenarios,
              "wall_sec": time.monotonic() - started}
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "wall_sec": result["wall_sec"],
                     "e8": {key: [{"elapsed": row["elapsed_sec"], "speed": row["freeway_speed"]["FW_E"][8],
                                     "rho": row["freeway_density"]["FW_E"][8]}
                                    for row in value["rows"] if row["elapsed_sec"] in (10, 30, 150, 450)]
                            for key, value in scenarios.items()}}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="evaluation/configs/n21_n7_20260908.json")
    parser.add_argument("--run", default="codex_n7_pure_s13_20260910")
    parser.add_argument("--start", type=int, choices=(1200, 3300), required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())
