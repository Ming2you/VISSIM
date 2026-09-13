"""Summarize already completed fidelity probes; no model or FZP access."""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "diagnostics/no_control_5400_baseline_prediction_v1"
RUN = ROOT / "evaluation/runs/codex_nc5400_r01_baseline_s13"
ANCHORS = (900, 1500, 2700, 4500)


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def statistics(rows):
    eligible = [r for r in rows if r["actual_count"] >= 5]
    def mean(key, selected):
        return sum(r[key] for r in selected) / len(selected) if selected else None
    return {"cells": len(rows), "speed_eligible_cells_count_ge5": len(eligible),
            "speed_bias_kph_eligible": mean("speed_error_kph", eligible),
            "speed_MAE_kph_eligible": sum(abs(r["speed_error_kph"]) for r in eligible) / len(eligible) if eligible else None,
            "density_bias_veh_km_lane_all_cells": mean("density_error_veh_km_lane", rows),
            "density_MAE_veh_km_lane_all_cells": sum(abs(r["density_error_veh_km_lane"]) for r in rows) / len(rows),
            "actual_count_sum": sum(r["actual_count"] for r in rows),
            "prediction_count_sum_using_rounded_CSV_geometry": sum(r["prediction_count_using_rounded_CSV_geometry"] for r in rows),
            "count_bias_using_rounded_CSV_geometry": sum(r["count_error_using_rounded_CSV_geometry"] for r in rows)}


def main():
    if (OUT / "summary.json").exists():
        raise ValueError("Preserve existing summary")
    # All four endpoint outputs must already exist before opening future CSV data.
    predictions = {t: load(OUT / f"t{t:04d}/prediction.json") for t in ANCHORS}
    invocations = {t: load(OUT / f"t{t:04d}/invocation.json") for t in ANCHORS}
    path = RUN / ("bottleneck_segments_" + RUN.name + ".csv")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        actual = {(int(r["sim_sec"]), r["model_link"], int(r["segment_index"])): r for r in csv.DictReader(stream)}
    records, cases = [], []
    for start in ANCHORS:
        result, invocation = predictions[start], invocations[start]
        if invocation["exit_code"] != 0 or invocation["source_changes"] or not invocation["future_CSV_stat_unchanged"] or result["all_stock_closures_pass"] is not True:
            raise ValueError("Failed/inconsistent completed case")
        keys = {(r["model_link"], r["cell"]) for r in result["records"]}
        if len(result["records"]) != 42 or keys != {(link, cell) for link in ("FW_E", "FW_W") for cell in range(21)}:
            raise ValueError("Incomplete42-cell result")
        case_rows = []
        for row in result["records"]:
            if row["start_sec"] != start or row["horizon_sec"] != 150:
                raise ValueError("Wrong prediction horizon")
            observation = actual[(start + 150, row["model_link"], row["cell"])]
            speed, density = row["production_prediction_speed_kph"], row["production_prediction_density"]
            if not all(math.isfinite(v) and v >= 0 for v in (speed, density)):
                raise ValueError("Invalid forecast value")
            if row["actual_speed_kph"] != float(observation["mean_speed_kph"]) or row["actual_density_veh_km_lane"] != float(observation["density_veh_km_lane"]):
                raise ValueError("Observed CSV changed after prediction")
            volume = float(observation["length_km"]) * int(observation["lanes"])
            count = int(observation["count"])
            item = {"start_sec": start, "target_sec": start + 150, "model_link": row["model_link"], "cell": row["cell"],
                    "actual_count": count, "speed_eligible_count_ge5": count >= 5,
                    "actual_speed_kph": row["actual_speed_kph"], "prediction_speed_kph": speed, "speed_error_kph": speed - row["actual_speed_kph"],
                    "actual_density_veh_km_lane": row["actual_density_veh_km_lane"], "prediction_density_veh_km_lane": density,
                    "density_error_veh_km_lane": density - row["actual_density_veh_km_lane"],
                    "CSV_length_km": float(observation["length_km"]), "CSV_lanes": int(observation["lanes"]),
                    "prediction_count_using_rounded_CSV_geometry": density * volume,
                    "count_error_using_rounded_CSV_geometry": density * volume - count}
            case_rows.append(item)
        records.extend(case_rows)
        cases.append({"start_sec": start, "target_sec": start + 150, "process_wall_sec": invocation["elapsed_sec"],
                      "exit_code": 0, "all_stock_closures_pass": True,
                      "loaded_source_prehash_uncovered": invocation.get("probe_loaded_source_prehash_uncovered", []),
                      "route_choice_information_complete": result["initial_route_information"]["route_choice_information_complete"],
                      "E8": next(r for r in case_rows if r["model_link"] == "FW_E" and r["cell"] == 8),
                      "E9": next(r for r in case_rows if r["model_link"] == "FW_E" and r["cell"] == 9),
                      "statistics": {link: statistics([r for r in case_rows if r["model_link"] == link]) for link in ("FW_E", "FW_W")},
                      "prediction_area_ledger": result["area"]})
    prefixes = ("evaluation/controllers/", "vendor/NumSim-mine/src/", "plant/src/")
    model_pins = [{p.replace("\\", "/"): h for p, h in predictions[t]["source_sha256"].items() if p.replace("\\", "/").startswith(prefixes)} for t in ANCHORS]
    same = all(pins == model_pins[0] for pins in model_pins[1:])
    if not same:
        raise ValueError("Loaded model source set/bytes differ across the four cases")
    with (OUT / "cell_errors.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    summary = {"status": "four_endpoints_complete_native_city_clock_not_certified", "config_path": "diagnostics/contract_observer_off_configs_v3/n7_area_beta0.json",
        "config_sha256": "201b7b6d5c759736201dd9a08b036dd3cd4891501a9d2de922b59651d3fd910d",
        "actual_NC_action": str(RUN / ("decisions_" + RUN.name) / "action_000900.json"), "cases": cases,
        "model_source_sets_and_bytes_equal_across_four_cases": same, "model_source_sha256": model_pins[0],
        "error_sign": "prediction minus observation", "count_conversion": "Approximate from CSV-rounded length_km times lanes times prediction density; raw observed count is integer. Primary forecast comparison is density.",
        "scope": "Requested existing helper/run() with current model, explicit actual snapshot/current action and previous actual action; no candidate search. Future30sCOM cell observations are validation-only, not FZP outcomes.",
        "limitations": ["Actual no-control writer emits no urban SG rows: native SIG retains ownership. Action JSON instead has equal-live-phase green values/offset0, used by model signal clock; native-city-signal fidelity is unverified.",
            "This is not solely dropped metadata: control_from_json preserves diagnostics, and live NoControl main also builds ControlAction.uncontrolled then calls build_one_step_prediction before CSV suppresses urban rows.",
            "Existing build_projected uses build_config(flagship=True); live no-control main uses flagship=False. These diagnostics do not certify exact live prediction parity.",
            "t900 omitted8plant Python modules from its prehash inventory; its original after-hashes/freeze statement are preserved. Later cases prehash all loaded modules; no900 rerun was performed.",
            "Stock closure does not establish correct signal, routing, arrivals, queue discharge or native plant prediction. Do not attribute observed errors solely to freeway physics.",
            "Speed aggregate errors exclude observed count<5 cells, while all42cell density/count records remain available. Negative count bias can be hidden by cancellation across cells."],
        "source_sha256": {str(path): sha(path), str(Path(__file__)): sha(Path(__file__))},
        "result_sha256": {f"t{t:04d}/prediction.json": sha(OUT / f"t{t:04d}/prediction.json") for t in ANCHORS}}
    with (OUT / "summary.json").open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps([{k: c[k] for k in ("start_sec", "statistics")} for c in cases]))


if __name__ == "__main__":
    main()
