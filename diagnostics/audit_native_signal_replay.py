"""Read-only audit of native signal programs versus the current COM plan writer."""
from __future__ import annotations
from collections import defaultdict
import csv
import json
import hashlib
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.controllers import plant_cycle, signal_group_plan, signal_timing_oracle
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from plant.src.vissim_strict.signal_program import parse_sig
from scripts.analyze_actuation import signal_intervals


def audit():
    network = ROOT / "network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx"
    tuning = adapter.load_optional_json(str(ROOT / "evaluation/configs/n21_n7_20260908.json"))
    adapter.install_config_switches(tuning)
    plan = adapter.load_signal_group_actuation_plan()
    # native_fixed_control is a separate, hardcoded legacy source path. Do not
    # conflate that alias with the effective plan selected by the live writer.
    legacy_plan = json.loads((ROOT / "outputs/signal_group_actuation_plan_v3.json").read_text(encoding="utf-8"))
    controllers = {node.get("no"): node for node in ET.parse(network).getroot().findall(".//signalControllers/signalController")}
    run = ROOT / "evaluation/runs/codex_nc_s13_6056c94_20260909_retry"
    lsa = next((run / "vissim_eval").glob("*.lsa"))
    observed = defaultdict(dict)
    for sc, sg, start, end, aspect in signal_intervals(lsa, 1800):
        if str(sc) in plan["controllers"]:
            for sec in range(max(900, int(start)), min(1800, int(end))):
                observed[sc, str(sg)][sec] = aspect.upper()
    amber, all_red = plant_cycle.runner_clearance_sec()
    frozen = json.loads((ROOT / "diagnostics/frozen_n7_2100_green_action.json").read_text(encoding="utf-8"))
    actual_csv = ROOT / "evaluation/runs/codex_n7_s13_6056c94_20260909/decisions_codex_n7_s13_6056c94_20260909/action_002100.csv"
    with actual_csv.open(encoding="utf-8-sig", newline="") as stream:
        actual_command_rows = list(csv.DictReader(stream))
    rows, detail = [], []
    for sc, node in plan["controllers"].items():
        raw = controllers[sc]
        path = str(raw.get("supplyFile2", ""))
        if path.lower().startswith("#data#"):
            path = path[6:]
        program = parse_sig(network.parent / path, int(raw.get("progNo", "1")))
        native_offset = program.program_offset_sec + float(raw.get("offset", 0))
        greens = {phase: (plant_cycle.written_axis_green_sec(value) if value > 0 else 0.0)
                  for phase, value in node["axis_green_sec"].items()}
        cycle = signal_group_plan.plan_cycle_sec(greens, amber, all_red)
        windows = signal_group_plan.plan_windows(signal_group_plan.node_plan_from_json(node), greens,
                      signal_group_plan.phase_layout_order(node.get("major_maps_to", "p2")), amber, all_red)
        by_sg = defaultdict(list)
        for window in windows:
            by_sg[window.sg_no].append((window.start_sec, window.end_sec))
        controlled_groups = {str(sg) for groups in node["phase_signal_groups"].values() for sg in groups}
        controlled_groups -= {str(sg) for sg in node.get("midblock_native_signal_groups", ())}
        counts = defaultdict(int)
        native_grid, composed_grid = [], []
        for sg, timeline in program.sg_timelines.items():
            if sg not in controlled_groups:
                continue
            native_green = sum(i.end_sec - i.start_sec for i in timeline.intervals if i.state == "GREEN")
            native_windows = [(i.start_sec, i.end_sec) for i in timeline.intervals if i.state == "GREEN"]
            composed_green = sum(end - start for start, end in by_sg[sg])
            detail.append({"sc": int(sc), "sg": int(sg), "native_cycle": program.cycle_length_sec,
                           "composed_cycle": cycle, "native_green": native_green,
                           "composed_green": composed_green})
            for sec in range(900, 1800):
                native = program.state_at(sec, sg, controller_offset_sec=float(raw.get("offset", 0)))
                plus = signal_timing_oracle.intended_state(by_sg[sg], sec + native_offset, cycle, amber)
                minus = signal_timing_oracle.intended_state(by_sg[sg], sec - native_offset, cycle, amber)
                counts["samples"] += 1
                counts["composed_raw_native_offset_match"] += (plus == native)
                counts["composed_sign_corrected_offset_match"] += (minus == native)
                raw_replay = signal_timing_oracle.intended_state(native_windows, sec - native_offset,
                                                               program.cycle_length_sec, amber)
                counts["raw_native_window_replay_match"] += (raw_replay == native)
                actual = observed[int(sc), sg].get(sec)
                if actual is not None:
                    counts["observed_samples"] += 1
                    counts["native_parser_lsa_match"] += (actual == native)
                    raw_plus_native = program.state_at(sec + 2 * native_offset, sg,
                        controller_offset_sec=float(raw.get("offset", 0)))
                    counts["plus_offset_parser_lsa_match"] += (actual == raw_plus_native)
            if cycle == program.cycle_length_sec:
                native_grid.append([program.state_at(sec, sg, controller_offset_sec=float(raw.get("offset", 0)))
                                    for sec in range(int(cycle))])
                composed_grid.append([signal_timing_oracle.intended_state(by_sg[sg], sec, cycle, amber)
                                      for sec in range(int(cycle))])
        best = {}
        if native_grid:
            native_array, composed_array = np.array(native_grid), np.array(composed_grid)
            mismatch = [(int(np.sum(native_array != np.roll(composed_array, -offset, axis=1))), offset)
                        for offset in range(int(cycle))]
            residual, offset = min(mismatch)
            best = {"best_possible_writer_offset_sec": offset,
                    "best_possible_offset_mismatched_samples_per_cycle": residual,
                    "samples_per_cycle": int(native_array.size)}
        duration_mismatches = []
        for sg, timeline in program.sg_timelines.items():
            duration = sum(i.end_sec - i.start_sec for i in timeline.intervals if i.state == "GREEN")
            declared = node.get("native_green_sec", {}).get(sg)
            if declared is None or abs(float(declared) - duration) > 1e-9:
                duration_mismatches.append({"sg": sg, "plan_native_green_sec": declared, "actual_native_green_sec": duration})
        recorded_greens = {phase: plant_cycle.written_axis_green_sec(frozen["green_times"][f"SC{sc}_{phase}"])
                           if frozen["green_times"][f"SC{sc}_{phase}"] > 0 else 0.0
                           for phase in signal_group_plan.MODEL_PHASES}
        legacy_greens = {phase: plant_cycle.written_axis_green_sec(value) if value > 0 else 0.0
                         for phase, value in legacy_plan["controllers"][sc]["axis_green_sec"].items()}
        csv_signal = next(r for r in actual_command_rows if r["kind"] == "signal" and r["sc_no"] == sc)
        csv_cycles = {float(r["green_sec"]) for r in actual_command_rows if r["kind"] == "signal_sg" and r["sc_no"] == sc}
        if len(csv_cycles) != 1:
            raise ValueError(f"recorded n7 CSV has inconsistent SG cycles: SC{sc}")
        rows.append({"sc": int(sc), "program": str(program.source_path),
                     "native_cycle_sec": program.cycle_length_sec, "composed_cycle_sec": cycle,
                     "declared_plan_native_cycle_sec": node.get("native_cycle_sec"),
                     "plan_native_duration_mismatches": duration_mismatches,
                     "actual_native_mainline_green_windows": {sg: [(i.start_sec, i.end_sec) for i in program.sg_timelines[sg].intervals if i.state == "GREEN"] for sg in sorted(controlled_groups)},
                     "frozen_n7_2100_unrounded_cycle_sec": signal_group_plan.plan_cycle_sec(recorded_greens, amber, all_red),
                     "frozen_n7_2100_written_greens_sec": recorded_greens,
                     "actual_n7_2100_csv_cycle_sec": next(iter(csv_cycles)),
                     "actual_n7_2100_csv_greens_sec": {phase: float(csv_signal[f"{phase}_green"]) for phase in signal_group_plan.MODEL_PHASES},
                     "legacy_native_fixed_input_clamped_cycle_before_other_guards_sec": signal_group_plan.plan_cycle_sec(legacy_greens, amber, all_red),
                     "legacy_native_fixed_input_clamped_greens_sec": legacy_greens,
                     "native_offset_sec": native_offset, "writer_raw_timeline_offset_sec": (-native_offset) % program.cycle_length_sec,
                     "phase_greens_sec": greens, **counts, **best})
    result = {"network": str(network.relative_to(ROOT)),
              "effective_plan": str(adapter.signal_group_actuation_plan_path().relative_to(ROOT)),
              "effective_plan_content_sha256": hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest(),
              "declared_plan_source": plan.get("source", {}),
              "legacy_native_fixed_green_source": "outputs/signal_group_actuation_plan_v3.json (hardcoded in native_fixed_control)",
              "actual_n7_2100_action_csv": str(actual_csv.relative_to(ROOT)),
              "actual_n7_2100_action_csv_sha256": hashlib.sha256(actual_csv.read_bytes()).hexdigest(),
              "config": "evaluation/configs/n21_n7_20260908.json",
              "supersedes": "Earlier audit read the raw v3 plan without install_config_switches; its plan-composition conclusions are withdrawn.",
              "note": "LSA validates native city SGs only; COM-controlled meters must use post-step readback.",
              "time_window": [900, 1800], "controllers": rows, "groups": detail}
    target = ROOT / "diagnostics/native_signal_replay_audit.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for row in rows:
        print(row["sc"], "cycle", row["native_cycle_sec"], "->", row["composed_cycle_sec"],
              "native_lsa", row["native_parser_lsa_match"], "/", row["observed_samples"],
              "raw_offset_composed", row["composed_raw_native_offset_match"], "/", row["samples"],
              "corrected_offset_composed", row["composed_sign_corrected_offset_match"])
    return result


if __name__ == "__main__":
    audit()
