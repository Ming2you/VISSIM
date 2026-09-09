"""Expose actual n7 signal model/writer mismatches without modifying runtime."""
from __future__ import annotations
import csv
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/NumSim-mine")]
from diagnostics.probe_model_area_integration import build_projected
from evaluation.controllers import vissim_stackelberg_adapter as adapter, plant_cycle


def setup():
    run = ROOT / "evaluation/runs/codex_nc_s13_6056c94_20260909_retry/decisions_codex_nc_s13_6056c94_20260909_retry"
    return build_projected(ROOT / "evaluation/configs/n21_n7_20260908.json",
                           run / "state_000900.json", run / "action_000001.json")


def interval_fraction(start, duration, offset, cycle, low, high):
    # Same positive-offset clock as VBS SignalCompositeStateAt/ApplyRuntimeSignals.
    begin, end = start + offset, start + offset + duration
    return sum(max(0., min(end, high + k * cycle) - max(begin, low + k * cycle))
               for k in range(math.floor(begin / cycle), math.floor(end / cycle) + 1)) / duration


def audit():
    from src.models.state import ControlAction, segment_vsl
    from src.models import urban_queue_model as uqm
    cfg, state, detectors, tuning, raw, mapping, metadata = setup()
    plan = adapter.load_signal_group_actuation_plan()
    action_path = ROOT / "diagnostics/frozen_n7_2100_green_action.json"
    recorded = json.loads(action_path.read_text(encoding="utf-8"))
    control = ControlAction.uncontrolled(cfg)
    control.green_times.update(recorded["green_times"])
    net = cfg.network
    result = {"plan_path": str(adapter.signal_group_actuation_plan_path()),
              "record_sha256": hashlib.sha256(action_path.read_bytes()).hexdigest(),
              "SC109_model": {"live": net.signal_live_phases("SC109"),
                              "cycle": net.signal_cycle_length("SC109"),
                              "budget": net.signal_effective_green_total("SC109"),
                              "max": net.signal_green_max("SC109"),
                              "greens": {p: control.green_times["SC109_" + p] for p in ("p1", "p2", "p3", "p4")}},
              "clock_cases": []}
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "action.csv"
        adapter.write_action_csv(path, control, cfg, mapping, segment_vsl, {}, tuning["actuation"], plan)
        emitted = list(csv.DictReader(path.open(newline="")))
    result["SC109_emitted"] = [x for x in emitted if x["sc_no"] == "109"]
    for signal, greens in (("SC109", {"p1": 0., "p2": 20., "p3": 96.5, "p4": 24.5}),
                           ("SC109", {"p1": 0., "p2": 20., "p3": 90., "p4": 31.}),
                           ("SC1001", {"p1": 21., "p2": 21., "p3": 75., "p4": 21.}),
                           ("SC105", {"p1": 21., "p2": 21., "p3": 75., "p4": 21.})):
        for offset in (0., 10.):
            sc = int(signal[2:])
            action = ControlAction.uncontrolled(cfg)
            action.green_times.update({f"{signal}_{p}": v for p, v in greens.items()})
            action.offsets[signal] = offset
            written = {p: plant_cycle.written_axis_green_sec(v) if v > 0 else 0. for p, v in greens.items()}
            sgrows = adapter.signal_group_action_rows(plan, sc, written, offset, "")
            phases = {}
            for phase in net.signal_live_phases(signal):
                spec = next(spec for spec in net.urban_movements.values()
                            if spec.get("phase") == f"{signal}_{phase}" and not spec.get("unsignalized"))
                groups = {str(x) for x in plan["controllers"][str(sc)]["phase_signal_groups"][phase]}
                row = next(x for x in sgrows if str(x["dsd_no"]) in groups)
                group = str(row["dsd_no"])
                differences = []
                for step in range(90):
                    observed = interval_fraction(step * cfg.simulation.T_u_sec, cfg.simulation.T_u_sec,
                                                 offset, float(row["green_sec"]),
                                                 float(row["p1_green"]), float(row["p2_green"]))
                    predicted = uqm._phase_green_fraction(action, cfg, spec, urban_step_index=step)
                    if abs(observed - predicted) > 1e-8:
                        differences.append({"sec": step * cfg.simulation.T_u_sec,
                                            "model": predicted, "writer": observed})
                phases[phase] = {"movement": spec.get("origin"), "sg": group,
                                 "model_average_fraction": uqm._phase_green_fraction(action, cfg, spec),
                                 "writer_average_fraction": (float(row["p2_green"]) - float(row["p1_green"])) / float(row["green_sec"]),
                                 "mismatched_substeps": len(differences), "first_differences": differences[:4]}
            result["clock_cases"].append(dict(signal=signal, greens=greens, offset=offset, phases=phases))
    baseline = adapter.native_fixed_control(cfg, ControlAction)
    result["native_fixed_selector_mismatch"] = {
        signal: {"produced": {p: baseline.green_times[f"{signal}_{p}"] for p in ("p1", "p2", "p3", "p4")},
                 "selected_plan": plan["controllers"][signal[2:]]["axis_green_sec"]}
        for signal in ("SC5", "SC7", "SC16")}
    path = ROOT / "diagnostics/signal_feasibility_audit.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"SC109_model": result["SC109_model"],
                      "clock_cases": result["clock_cases"],
                      "native_fixed": result["native_fixed_selector_mismatch"]}, indent=2))
    return result


if __name__ == "__main__":
    audit()
