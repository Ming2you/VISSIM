"""Two saved-state, held-450s model queries for an all-open meter alias.

No optimizer, native access, FZP reader, calibration change or installed patch.
All paths are explicit. The selected run must have a successful completion receipt.
Run as a fresh Python CLI with no inherited trace/profiling bootstrap and with
NUMSIM_REPO_ROOT absent or pointing at this checkout's vendor/NumSim-mine.
This reproduces the CURRENT grouped-rate/physical-command ambiguity; it does not
apply a correction or establish a native traffic effect.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import pickle
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
GROUPS = {"R_D_W", "R_D_E", "R_F_W", "R_F_E"}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_environment():
    trace_keys = {"RW_DECISION_PROFILE_DIR", "RW_PHASE_COMMIT_TRACE_DIR", "RW_PHASE_TRACE_DIR",
                  "RW_EVALUATION_TRACE_DIR", "RW_EVALUATION_TRACE_INPUTS_JSON", "RW_EVALUATION_TRACE_MANIFEST",
                  "RW_DECISION_RESOURCE_DIR", "RW_EVALUATION_TRACE_BACKEND", "RW_EVALUATION_TRACE_LOCALS"}
    active = sorted(k for k, value in os.environ.items() if value and
                    (k in trace_keys or k.startswith("RW_VALIDATION_")))
    require(not active, "Inherited trace/profile/validation override: " + ", ".join(active))
    bootstraps = {"phase_trace_bootstrap", "decision_profile_bootstrap",
                  "evaluation_trace_bootstrap", "decision_resource_bootstrap"}
    search_paths = [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p]
    require(not any(Path(p).resolve().name.casefold() in bootstraps for p in search_paths),
            "Inherited diagnostic PYTHONPATH bootstrap")
    require(sys.gettrace() is None and sys.getprofile() is None, "Active Python trace/profile hook")
    require(not any(k == "src" or k.startswith(("src.", "evaluation.controllers.")) for k in sys.modules),
            "Use a fresh CLI; controller/model modules were already imported")
    native_root = os.environ.get("NUMSIM_REPO_ROOT", "")
    require(not native_root or Path(native_root).resolve() == (ROOT / "vendor/NumSim-mine").resolve(),
            "NUMSIM_REPO_ROOT points at another checkout")
    return {"no_inherited_instrumentation": True, "no_preimported_runtime": True,
            "NUMSIM_REPO_ROOT": native_root, "PYTHONPATH": search_paths}


def meter_definition_bytes(cfg):
    # Deliberately exclude unrelated mutable solver caches/closures.
    return pickle.dumps((cfg.network.control_area_meter_context,
                         dict(cfg.network.ramp_capacity_veh_h)), protocol=5)


def prepare_inputs(args, report):
    run, config = args.run.resolve(strict=True), args.config.resolve(strict=True)
    decision = run / ("decisions_" + run.name)
    receipt_path = run / "completion_receipt.json"
    manifest_path = run / ("run_provenance_" + run.name + ".json")
    receipt, manifest = read(receipt_path), read(manifest_path)
    require(receipt.get("completed") is True and receipt.get("exit_code") == 0
            and receipt.get("owned_native_alive") is False, "Run completion/owned exit is not certified")
    require(receipt.get("run_id") == manifest.get("run_id") and receipt.get("name") == run.name,
            "Completion receipt/run provenance differs")
    require(Path(receipt.get("provenance_path", "")).resolve() == manifest_path
            and receipt.get("provenance_sha256") == sha(manifest_path),
            "Completion receipt does not pin the current run manifest")
    require(manifest.get("controller") == "wu-link" and manifest.get("control_interval_sec") == 150,
            "Only the recorded wu-link/150-second decision path is supported")
    require(args.sim_sec >= 900 and args.sim_sec % 150 == 0
            and args.sim_sec + 150 <= manifest["sim_period_sec"], "Require a controlled decision with one completed native interval")
    report['horizon_scope'] = {'native_terminal_sec':manifest['sim_period_sec'],
        'held_model_start_sec':args.sim_sec,'held_model_end_sec':args.sim_sec+450,
        'scope':'Three existing forecast steps are model predictions; native evidence ends at the recorded terminal. No unobserved native traffic is inferred.'}
    require(sha(config) == manifest["files"]["tuning"]["sha256"], "Config differs from the executed tuning")
    paths = {"config": config, "receipt": receipt_path, "manifest": manifest_path,
             "state": decision / f"state_{args.sim_sec:06d}.json",
             "previous": decision / f"action_{args.sim_sec-150:06d}.json",
             "action": decision / f"action_{args.sim_sec:06d}.json",
             "csv": decision / f"action_{args.sim_sec:06d}.csv"}
    raw, action, previous = (read(paths[k]) for k in ("state", "action", "previous"))
    for item in (raw, action, previous):
        require(item["run_provenance"]["run_id"] == manifest["run_id"], "Input run identity differs")
    require(raw["sim_sec"] == action["metadata"]["sim_sec"] == args.sim_sec,
            "State/action timestamp differs")
    require(previous["metadata"]["sim_sec"] == args.sim_sec - 150, "Previous action is not the preceding decision")
    require(action["metadata"].get("controller_status") == "ok", "Recorded decision was not successful")
    require(set(action["ramp_metering"]) == GROUPS, "Expected exactly four model ramp groups")
    require(raw["run_provenance"]["manifest_path"] == str(manifest_path), "Raw snapshot references another manifest")
    for key, item in manifest["files"].items():
        if item.get("sha256") and item.get("path"):
            # Provenance sources only: never enumerate native output/trajectory files.
            p = Path(item["path"]).resolve(strict=True)
            require(p.suffix.lower() not in (".fzp", ".lsa"), "Unexpected trajectory in source manifest")
            current_sha = sha(p)
            if current_sha != item["sha256"]:
                # These two execution-only producers were changed and qualified
                # after the saved run. Neither is executed by this model query.
                # Keep every Python/model/config/physical-input pin strict.
                producers = {
                    "main_vbs_runner": ROOT / "scripts/run_real_world_stackelberg_controller.vbs",
                    "watchdog_wrapper": ROOT / "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1",
                }
                require(key in producers and p == producers[key], "Executed input changed: " + key)
                edit_path = ROOT / "diagnostics/com_execution_equivalence/canonical_edit_receipt.json"
                edit = read(edit_path)
                require(edit.get("schema") == "canonical-com-execution-edit/v1", "Unknown execution edit receipt")
                changes = [row for row in edit["changes"] if (ROOT / row["path"]).resolve() == p]
                require(len(changes) == 1 and changes[0]["before_sha256"] == item["sha256"]
                        and changes[0]["after_sha256"] == current_sha,
                        "Execution producer differs from the recorded COM-only edit: " + key)
                paths["execution_only_edit_receipt"] = edit_path
                report.setdefault("historical_execution_source_changes", []).append({
                    "key": key, "path": str(p), "recorded_sha256": item["sha256"],
                    "current_sha256": current_sha, "edit_receipt_sha256": sha(edit_path),
                    "scope": "Historical state producer only; not imported or executed by this model query",
                })
            paths["source:" + key] = p
    reviewed = {Path(path).resolve(strict=True) for path in getattr(args, 'reviewed_source_change', ())}
    require(all(path.is_relative_to(ROOT / 'evaluation/controllers') and path.suffix == '.py'
                for path in reviewed), 'Reviewed source changes must name exact canonical controller Python files')
    reviewed_changes = {}
    def check_controller_source(path, recorded_sha, label):
        current_sha = sha(path)
        if current_sha == recorded_sha:
            return
        require(path in reviewed, 'Historical controller source changed: ' + str(path))
        reviewed_changes[str(path)] = {'recorded_sha256': recorded_sha, 'current_sha256': current_sha,
            'scope': 'Explicit current-source model replay on unchanged historical observations; not reproduction of the historical controller computation'}
    for key, item in action["run_provenance"].get("imported_modules", {}).items():
        p = Path(item["path"]).resolve(strict=True)
        check_controller_source(p, item["sha256"], key)
        paths["module:" + key] = p
    sources = manifest.get("controller_sources")
    require(isinstance(sources, list) and sources, "Historical controller source manifest is missing")
    seen = set()
    for item in sources:
        p = Path(item["path"]).resolve(strict=True)
        require(p not in seen and p.is_relative_to(ROOT) and p.suffix == ".py",
                "Duplicate/non-checkout controller source")
        require(item.get("exists") is True, "Historical controller source did not exist: " + str(p))
        check_controller_source(p, item.get("sha256"), str(p))
        seen.add(p)
        paths["controller:" + str(p)] = p
    require(reviewed == {Path(path) for path in reviewed_changes}, 'Reviewed source list contains unchanged or unrecorded files')
    if reviewed_changes:
        report['reviewed_controller_source_changes'] = reviewed_changes
        report['historical_computation_reproduced'] = False
    return run, paths, read(config), action


def compare(args, report):
    report["environment"] = validate_environment()
    run, paths, tuning, document = prepare_inputs(args, report)
    # Imports are deliberately deferred; parsing/AST inspection cannot run a model.
    sys.path[:0] = [str(ROOT), str(ROOT / "vendor/NumSim-mine")]
    from diagnostics.probe_model_area_integration import build_projected, replay_provenance
    from diagnostics.audit_live_prediction_interval import command_roundtrip, stock_snapshot
    from evaluation.controllers import area_meter_finalization, area_runtime
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from src.controllers import rollout_endpoint
    from src.models.state import ControlAction
    from src.models.demand import DemandStep
    from src.simulation import coupling

    before = replay_provenance(tuning, Path(__file__), *paths.values())
    report.update(run=str(run), sim_sec=args.sim_sec, source_sha256=before,
                  recorded_controller_source_count=sum(k.startswith("controller:") for k in paths),
                  provenance_scope="Receipt-pinned manifest controller_sources, recorded imported modules/inputs, and current recursive runtime/config pins")
    try:
        cfg, state, detectors, tuning, raw, mapping, meta = build_projected(
            paths["config"], paths["state"], paths["previous"], fixture_inputs=False)
        require(cfg.network.control_area_enabled and cfg.mpc.horizon_steps == 3,
                "Require enabled Omega and the existing three-interval horizon")
        require(float(cfg.simulation.T_c_sec) == 150 and float(cfg.simulation.T_f_sec) == 10,
                "This diagnostic expects the existing 150s/10s clock")
        require(not meta.get("route_choice_held_unknown_route_veh", 0), "Unknown route holding invalidates comparison")
        frozen_definition = meter_definition_bytes(cfg)
        report["frozen_meter_definition_sha256"] = hashlib.sha256(frozen_definition).hexdigest()
        calibration = adapter.deep_update(dict(adapter.load_optional_json(str(
            ROOT / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"))),
            tuning.get("calibration_override", {}))
        forecast = adapter.demand_from_state(raw, cfg, DemandStep, 3, calibration, detectors)
        require(len(forecast) == 3, "Incomplete forecast")
        baseline = adapter.control_from_json(paths["action"], cfg, ControlAction)
        for name in ("N_P_star", "N_UF_star", "green_times", "offsets", "vsl", "ramp_metering"):
            require(getattr(baseline, name) == document[name], "Action parser changed " + name)
        area_meter_finalization.assert_writer(baseline, cfg, require_scored=True)
        meters = mapping["ramp_meters"]
        require(len(meters) == 8 and {m["model_ramp_key"] for m in meters} == GROUPS,
                "Expected the current eight physical meters/four groups")
        settings = adapter.adapter_actuation_settings(calibration, tuning)["real_world_ramp_metering"]
        require(float(settings["max_green_sec"]) == float(settings["cycle_sec"]), "Maximum GREEN is not fully open")
        for meter in meters:
            require(baseline.diagnostics["rw_meter_green_" + meter["id"]] == float(settings["cycle_sec"]),
                    "Recorded action contains a non-open physical meter")
        alias = baseline.copy()
        alias.ramp_metering = {k: float(cfg.network.ramp_capacity_veh_h[k]) for k in baseline.ramp_metering}
        require(all(math.isfinite(v) and v > 0 for v in alias.ramp_metering.values()), "Invalid near-model capacity")
        area_meter_finalization.finalize(alias, cfg)
        alias.N_UF_star = sum(alias.ramp_metering.values())
        require(alias.ramp_metering == {k: float(cfg.network.ramp_capacity_veh_h[k]) for k in baseline.ramp_metering},
                "Finalizer changed the requested near-capacity representation")
        report["near_model_capacities_vph"] = dict(alias.ramp_metering)
        report["roundtrips"] = {}
        for name, action in (("recorded", baseline), ("open_capacity_alias", alias)):
            for field in ("N_P_star", "green_times", "offsets", "vsl", "inflow_outflow_allocation"):
                require(getattr(action, field) == getattr(baseline, field), "Foreign action change: " + field)
            require(action.N_UF_star == sum(action.ramp_metering.values()), "Model budget is not the represented rate sum")
            lo, hi = cfg.leader.N_UF_star_range
            require(lo <= action.N_UF_star <= hi, "Alias exceeds the existing leader budget box")
            roundtrip = command_roundtrip(action, cfg, mapping, calibration, tuning,
                                          copy.deepcopy(document), paths["csv"])
            report["roundtrips"][name] = roundtrip
            require(roundtrip["physical_columns_exact"], "Physical CSV alias mismatch: " + name)
        # Any failed command gate above stops BEFORE either endpoint.
        report["initial"] = stock_snapshot(state, cfg)
        report["arms"] = {}
        for name, action in (("recorded", baseline), ("open_capacity_alias", alias)):
            require(meter_definition_bytes(cfg) == frozen_definition,
                    "Frozen meter context/near capacities changed before " + name)
            frozen = pickle.dumps((state, action, forecast), protocol=5)
            expected = {k: copy.deepcopy(getattr(action, k)) for k in
                        ("N_P_star", "N_UF_star", "ramp_metering", "green_times", "offsets", "vsl")}
            trace = []
            original_release, original_step = coupling.compute_ramp_release_flows, coupling.freeway_substep

            def observe_release(s, c, demand, config, **kw):
                require(all(getattr(c, k) == v for k, v in expected.items()), "Held endpoint action changed")
                offer, diag = original_release(s, c, demand, config, **kw)
                trace.append({"elapsed_sec": (len(trace) + 1) * cfg.simulation.T_f_sec,
                              "requested_vph": dict(c.ramp_metering),
                              "no_meter_total_vph": float(diag["total_no_meter_flow"]),
                              "meter_limited_offer_vph": dict(offer)})
                return offer, diag

            def observe_step(*pos, **kw):
                require(trace and "accepted_vph" not in trace[-1], "Release/acceptance trace order differs")
                require(all(getattr(pos[1], k) == v for k, v in expected.items()), "Held action changed at freeway step")
                require("ramp_release_veh_h" in kw, "Canonical accepted ramp argument missing")
                trace[-1]["accepted_vph"] = dict(kw["ramp_release_veh_h"])
                return original_step(*pos, **kw)

            try:
                with patch.object(coupling, "compute_ramp_release_flows", observe_release), \
                        patch.object(coupling, "freeway_substep", observe_step):
                    point = rollout_endpoint.evaluate_price_point(state, action, forecast, [],
                        rollout_endpoint.ObjectiveSpec(cfg, depth_override=3, box_walk=False, score_mode="raw"))
            finally:
                require(meter_definition_bytes(cfg) == frozen_definition,
                        "Frozen meter context/near capacities changed during " + name)
            require(not point.aborted and len(point.states) == 3 and len(trace) == 45
                    and all("accepted_vph" in row for row in trace), "Incomplete two-phase substep/endpoint trace")
            require(pickle.dumps((state, action, forecast), protocol=5) == frozen, "Endpoint mutated its inputs")
            ends = []
            for index, last in enumerate(point.states, 1):
                last._control_area_ledger.assert_stocks(area_runtime.model_inventory(last, cfg))
                ends.append({"elapsed_sec": index * 150, "metrics": vars(last._control_area_ledger.metrics).copy(),
                             "flow_counts": dict(last._control_area_ledger.flow_counts),
                             "ramp_queues_veh": dict(last.ramp_queue)})
            report["arms"][name] = {"N_UF_star_vph": action.N_UF_star, "meter_rates_vph": dict(action.ramp_metering),
                "objective_veh_h": float(point.objective), "endpoints": ends, "substeps": trace,
                "input_unchanged": True, "frozen_meter_definition_unchanged": True}
        report["objective_alias_minus_recorded_veh_h"] = (
            report["arms"]["open_capacity_alias"]["objective_veh_h"] - report["arms"]["recorded"]["objective_veh_h"])
    finally:
        after = replay_provenance(tuning, Path(__file__), *paths.values())
        report["source_changes"] = [p for p, h in before.items() if after.get(p) != h]
        # Modules imported lazily during the query were not historical before-pins.
        report["newly_imported_source_sha256"] = {p: h for p, h in after.items() if p not in before}
        require(not report["source_changes"], "Source/input changed during diagnostic")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--sim-sec", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True, help="New diagnostic JSON; never an existing result")
    parser.add_argument('--reviewed-source-change', type=Path, action='append', default=[],
                        help='Exact edited controller source for an explicit current-code replay; physical/config/input pins remain strict')
    args = parser.parse_args()
    out = args.out.resolve()
    require(out.is_relative_to(ROOT / "diagnostics") and out.suffix == ".json", "Output must be a new diagnostics JSON")
    require(not out.exists(), "Refuse to replace an existing result")
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {"schema": "selected-open-meter-alias/v1", "status": "running", "completed": False,
              "method": "Exactly two current canonical held450s raw endpoints; same physical CSV, different grouped open-rate representation",
              "interpretation": "Current model alias diagnostic only; not a correction, candidate search or native causal result",
              "trace_scope": "Per-group requested/meter-limited/accepted rates; no-meter is the original aggregate diagnostic, not an invented per-group split"}
    started = time.monotonic()
    with out.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.flush()
        try:
            compare(args, report)
            report.update(status="complete", completed=True)
        except Exception as exc:
            report.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        report["elapsed_sec"] = time.monotonic() - started
        handle.seek(0)
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.truncate()
    print(json.dumps({"out": str(out), "completed": report["completed"], "error": report.get("error")}))
    return 0 if report["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
