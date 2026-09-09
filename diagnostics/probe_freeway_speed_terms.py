"""Read-only canonical METANET return-frame decomposition; no refit or override."""
from __future__ import annotations
import argparse
import copy
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/NumSim-mine")]
from diagnostics.probe_model_area_integration import build_projected
from evaluation.controllers import vissim_stackelberg_adapter as adapter, signal_actuation_contract
from src.controllers import rollout_endpoint
from src.models.state import ControlAction
from src.models.demand import DemandStep


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TermsTrace:
    def __init__(self):
        self.steps = 0
        self.frames = {}
        self.rows = {}

    @staticmethod
    def plant(frame):
        path = frame.f_code.co_filename.replace("\\", "/")
        return ((path.endswith("/models/metanet.py") and frame.f_code.co_name == "freeway_substep") or
                (path.endswith("/controllers/area_freeway_accounting.py") and frame.f_code.co_name == "_freeway_substep_events"))

    def owner(self, frame):
        owner = frame.f_back
        while owner is not None:
            if self.plant(owner):
                values = owner.f_locals
                if self.frames[id(owner)] <= 3 and values.get("link") == "FW_E" and values.get("i") in (7, 8, 9):
                    key = (self.frames[id(owner)], values["link"], values["i"])
                    return owner, self.rows.setdefault(key, {"step": key[0], "link": key[1], "cell": key[2]})
                return None, None
            owner = owner.f_back
        return None, None

    def __call__(self, frame, event, arg):
        if event == "call" and self.plant(frame):
            self.steps += 1
            self.frames[id(frame)] = self.steps
            return
        name = frame.f_code.co_name
        if event == "return" and name in ("metanet_speed_update_kmh", "_patched_metanet_speed_update_kmh"):
            owner, row = self.owner(frame)
            if row is None:
                return
            values = frame.f_locals
            if name == "metanet_speed_update_kmh":
                keys = ("speed", "upstream_speed", "rho", "downstream_rho", "v_eff", "dt_h", "length_km", "tau_h", "nu_km2_h", "kappa_veh_km_lane", "v_min", "relaxation", "convection", "anticipation")
                row["base"] = {key: float(values[key]) for key in keys}
                row["base_return_kmh"] = float(arg)
            else:
                row["segment"] = {key: float(values[key]) for key in ("_phi", "_dl", "_lam", "_rc_link", "length_km", "tau_h", "kappa_veh_km_lane")}
                row["segment"]["p"] = dict(values.get("p") or {})
                row["segment_return_kmh"] = float(arg)
            return
        if event != "call" or name != "segment_flow_veh_h" or frame.f_back is None or not self.plant(frame.f_back):
            return
        owner, row = self.owner(frame)
        if row is None or "base" not in row:
            return
        values = owner.f_locals
        index = values["i"]
        if len(values.get("next_speeds", [])) != index + 1:
            return
        net = values["net"]
        row["plant"] = {key: float(values[key]) for key in ("v_new", "rho_new", "q_in", "q_out", "vehicle_new", "vehicle_raw", "delta_m")}
        row["plant"].update({
            "boundary_speed_cap": values["boundary_speed_cap"],
            "ramp_in_veh_h": float(values["ramp_in_by_link"]["FW_E"][index]),
            "lanes_before": float(values["previous_lanes"][index]),
            "lanes_now": float(values["lanes_now"][index]),
            "rho_observed_or_previous": float(values["rhos"][index]),
            "q_inter_out_veh_h": float(values["q_inter"][index]),
            "receiving_downstream_veh_h": float(values["receiving_for_mainline"][index + 1]),
            "normal_off_total_veh_h": float(values["normal_off_total"]),
            "effective_off_total_veh_h": float(values["effective_off_total"]),
            "continuity_length_km": float(net.freeway_segment_length_km),
            "merge_kappa": float(net.metanet_kappa_veh_km_lane),
            "vsl_kmh": float(values["vsl_i"]),
            "two_branch": bool(getattr(net, "vsl_fd_two_branch", False)),
            "configured_link_capacity_veh_h": float(net.freeway_capacity_veh_h),
            "capacity_drop_discharge_phi": float(getattr(net, "capacity_drop_discharge_phi", 1.)),
        })


def decompose(row):
    b, s, p = row["base"], row["segment"], row["plant"]
    term = {key: b[key] for key in ("relaxation", "convection", "anticipation")}
    term["base_speed_floor"] = row["base_return_kmh"] - (b["speed"] + sum(term.values()))
    rc = float(s["p"].get("rho_crit", s["_rc_link"]))
    drop = (-s["_phi"] * b["dt_h"] * s["_dl"] * max(b["rho"], 0) * b["speed"] ** 2 /
            (max(s["length_km"], 1e-9) * s["_lam"] * max(rc, 1e-9))) if s["_phi"] > 0 and s["_dl"] > 0 else 0.
    term["lane_drop"] = drop
    term["lane_drop_floor"] = row["segment_return_kmh"] - (row["base_return_kmh"] + drop)
    merge = (-p["delta_m"] * b["dt_h"] * p["ramp_in_veh_h"] * b["speed"] /
             (p["continuity_length_km"] * max(p["lanes_now"], 1e-9) * (b["rho"] + p["merge_kappa"]))) if p["delta_m"] > 0 and p["ramp_in_veh_h"] > 0 else 0.
    term["merge"] = merge
    after_merge = max(b["v_min"], row["segment_return_kmh"] + merge)
    term["merge_floor"] = after_merge - row["segment_return_kmh"] - merge
    term["boundary_cap"] = p["v_new"] - after_merge
    row["terms_delta_kmh"] = term
    row["sum_delta_kmh"] = sum(term.values())
    row["actual_delta_kmh"] = p["v_new"] - b["speed"]
    row["sum_error_kmh"] = row["sum_delta_kmh"] - row["actual_delta_kmh"]
    row["continuity_residual_veh"] = p["vehicle_new"] - (b["rho"] * p["continuity_length_km"] * p["lanes_now"] + b["dt_h"] * (p["q_in"] - p["q_out"]))
    assert abs(row["sum_error_kmh"]) < 1e-10
    assert abs(row["continuity_residual_veh"]) < 1e-9
    return row


def run(mode, start, destination):
    os.environ["RW_OFFSET_WRITER"] = "experiment" if mode == "integrated" else ""
    os.environ["RW_MAINLINE_SG_ONLY"] = "1"
    config = ROOT / ("diagnostics/area_candidate_configs/n7_area_beta0.json" if mode == "integrated" else "evaluation/configs/n21_n7_20260908.json")
    run_name = "codex_n7_pure_s13_20260910"
    directory = ROOT / "evaluation/runs" / run_name
    decisions = directory / ("decisions_" + run_name)
    state_path, action_path, previous = (decisions / f"{kind}_{sec:06d}.json" for kind, sec in (("state", start), ("action", start), ("action", start - 150)))
    cfg, state, detectors, tuning, raw, mapping, metadata = build_projected(config, state_path, previous)
    action = adapter.control_from_json(action_path, cfg, ControlAction)
    raw_greens = json.loads(action_path.read_text(encoding="utf-8"))["green_times"]
    if signal_actuation_contract.enabled(cfg.network):
        action = signal_actuation_contract.prepare_control(action, cfg)
    projected = {key: {"recorded": value, "replayed": action.green_times[key]} for key, value in raw_greens.items() if value != action.green_times[key]}
    calibration = adapter.load_optional_json(str(ROOT / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"))
    calibration = adapter.deep_update(dict(calibration), tuning.get("calibration_override", {}))
    forecast = adapter.demand_from_state(raw, cfg, DemandStep, 1, calibration, detectors)
    before = copy.deepcopy(state.__dict__)
    trace = TermsTrace()
    assert sys.getprofile() is None
    sys.setprofile(trace)
    try:
        result = rollout_endpoint.evaluate_price_point(state, action, forecast, (), rollout_endpoint.ObjectiveSpec(cfg, depth_override=1, box_walk=False, score_mode="raw"))
    finally:
        sys.setprofile(None)
    plain = rollout_endpoint.evaluate_price_point(state, action, forecast, (), rollout_endpoint.ObjectiveSpec(cfg, depth_override=1, box_walk=False, score_mode="raw"))
    numerical_fields = ("freeway_density", "freeway_speed", "freeway_flow", "freeway_effective_lanes", "ramp_queue", "urban_movement_queue", "urban_link_storage")
    assert all(getattr(result.states[-1], key) == getattr(plain.states[-1], key) for key in numerical_fields)
    assert all(state.__dict__[key] == before[key] for key in numerical_fields)
    assert result.objective == plain.objective and result.ttt == plain.ttt and not result.aborted
    rows = [decompose(row) for _, row in sorted(trace.rows.items())]
    assert trace.steps == cfg.simulation.K_cf and len(rows) == 9, (trace.steps, len(rows))
    observed_path = directory / f"bottleneck_segments_{run_name}.csv"
    with observed_path.open(encoding="utf-8-sig", newline="") as stream:
        observed = [row for row in csv.DictReader(stream) if int(row["sim_sec"]) in (start, start + 30) and row["model_link"] == "FW_E" and int(row["segment_index"]) in (7, 8, 9)]
    sources = [config, state_path, action_path, previous, Path(adapter.__file__), ROOT / "evaluation/controllers/area_freeway_accounting.py", ROOT / "vendor/NumSim-mine/src/models/metanet.py", ROOT / "evaluation/controllers/freeway_fd.py", ROOT / "evaluation/controllers/runtime_setup.py"]
    report = {"mode": mode, "start_sec": start, "method": "Canonical endpoint; actual return-frame locals; no function replacement; first three 10-second freeway steps; independent untraced endpoint matches exactly", "limitations": ["Actual pure-n7 action is the seed; integrated physical signal contract projects infeasible raw phases before replay, explicitly listed.", "Current-rate demand persistence; no parameter/capacity fit or adjustment.", "Baseline means current canonical source with original n7 flags OFF; not historical source snapshot.", "Observed plant cadence30s; no10s plant speed is inferred."], "signal_projection": projected, "substeps": trace.steps, "trace_preserves_result_exactly": True, "initial_state_preserved": True, "sources_sha256": {str(path.relative_to(ROOT)): sha(path) for path in sources}, "rows": rows, "observed_rows": observed, "runtime_metadata": metadata}
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({"output": str(destination), "mode": mode, "start": start, "max_sum_error": max(abs(row["sum_error_kmh"]) for row in rows), "e8": [{"step": row["step"], "old": row["base"]["speed"], "new": row["plant"]["v_new"], "terms": row["terms_delta_kmh"]} for row in rows if row["cell"] == 8]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("baseline", "integrated"), required=True)
    parser.add_argument("--start", type=int, choices=(1200, 3300), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.mode, args.start, args.output)
