"""Decompose completed city-only/hold measurements; no FZP or prediction run."""
import csv
import gzip
import hashlib
import json
import pickle
from collections import defaultdict
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
A = HERE.parent
H = A.parent
ROOT = HERE.parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/NumSim-mine")]
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.matched280.review import model_boundary
from diagnostics.repin_v3c3_review_20261001.urban_rm269.sc12_source import audit as head_reader

NATIVE = Path("E:/VISSIM_analysis/20261010_urbanrm269_cityonly289")
RUNS = {
    "hold": Path("E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/decisions_sdmpc31_g_2400_hold_s29"),
    "city": Path("E:/VISSIM_runs/20261010_urbanrm269_cityonly289_s29/selected/decisions_sdmpc31_g_2400_selected_s29"),
}
PINS = {}


def pin(path):
    path = Path(path)
    data = path.read_bytes()
    PINS[str(path.resolve())] = hashlib.sha256(data).hexdigest()
    return data


def read(path):
    return json.loads(pin(path))


def native_boundary():
    columns = ("observed_entry_events", "appeared_inside_events", "reappeared_inside_events",
               "observed_exit_events", "terminal_exit_inferred_events", "unresolved_inside_disappearances")
    totals, counts = {}, {}
    for arm, directory in (("hold", "hold"), ("city", "selected")):
        rows = list(csv.DictReader(pin(NATIVE / directory / "area_timeseries.csv").decode("utf-8-sig").splitlines()))
        rows = [r for r in rows if float(r["sim_sec"]) > 2400]
        totals[arm] = {k: dict(vehicles=0., cost=0.) for k in columns}
        for r in rows:
            assert abs(float(r["stock_closure_residual_veh"])) < 1e-7
            weight = (2850 - float(r["sim_sec"]) + float(r["interval_sec"]) / 2) / 3600
            for i, k in enumerate(columns):
                count = float(r[k])
                totals[arm][k]["vehicles"] += count
                totals[arm][k]["cost"] += count * weight * (1 if i < 3 else -1)
        counts[arm] = [{
            "native_sec": float(r["sim_sec"]), "inside": float(r["inside_vehicles"]),
            "cumulative_ttt": float(r["ttt_veh_h_cumulative"]),
        } for r in rows if float(r["sim_sec"]) in (2550.1, 2700.1, 2850)]
        assert len(counts[arm]) == 3
    delta = {k: {f: totals["city"][k][f] - totals["hold"][k][f] for f in ("vehicles", "cost")} for k in columns}
    return dict(totals=totals, delta=delta, block_end_stocks=counts)


def main():
    target = HERE / "assessment.json"
    assert not target.exists(), "Preserve completed assessment"
    source = read(NATIVE / "cached_summary.json")
    assert source["paired_prefix_exact"] and source["common_start_vehicle_records_exact"]
    assert all(x["native_execution_passed"] for x in source["arms"].values())
    assert read(NATIVE / "runtime_closure.json")["all_owned_processes_closed"]
    for file, digest in source["source_pins"].items():
        assert hashlib.sha256(Path(file).read_bytes()).hexdigest() == digest, file
    # Consult prior Claude diagnosis, including the distinction between inventory,
    # readiness time, turn composition and an upstream discharge cascade.
    for relative in ("upstream_worklog/02_urban_b2/diag_c3_r2/U7.md",
                     "upstream_worklog/02_urban_b2/diag_c3/C3_DIAGNOSIS.md"):
        pin(H.parent / relative)
    pin(H / "city_response/README.md")
    city_folder = A / "citysplit287/forecast2400"
    hold_folder = A / "matched280/authority"
    summaries = dict(city=read(city_folder / "summary.json"), hold=read(hold_folder / "summary.json"))
    cfg, _, _ = pickle.loads(pin(city_folder / "initial.pickle"))
    predictions = {}
    for arm, folder, name in (("hold", hold_folder, "hold"), ("city", city_folder, "city_only")):
        summary = summaries[arm]
        assert summary["status"] == "complete" and (summary["start_sec"], summary["end_sec"]) == (2400, 2850)
        r = json.loads(gzip.decompress(pin(folder / (name + ".response.json.gz"))))
        stocks = read(folder / (name + ".stocks.json"))
        value = summary["results"][name]
        assert value["conservation_states"] == 4 and value["resource_max_exceedance"] < 1e-7
        predictions[arm] = dict(response=r, boundary=model_boundary(r, stocks, value["omega_ttt_veh_h"], cfg))
    model_delta = {}
    for key in set(predictions["hold"]["boundary"]["routes"]) | set(predictions["city"]["boundary"]["routes"]):
        x = predictions["hold"]["boundary"]["routes"].get(key, {})
        y = predictions["city"]["boundary"]["routes"].get(key, {})
        model_delta[key] = {k: y.get(k, 0.) - x.get(k, 0.) for k in (
            "entered", "departed", "generated_inside", "entry_cost", "departure_cost", "generation_cost")}
    assert abs(sum(sum(r[k] for k in ("entry_cost", "departure_cost", "generation_cost"))
                   for r in model_delta.values()) - source["comparison"]["model_city_minus_hold_veh_h"]) < 1e-7
    boundary = native_boundary()
    assert abs(sum(v["cost"] for v in boundary["delta"].values()) - source["delta_TTT_veh_h"]) < 1e-7

    # Both raw metrics cover identical pre-control history, so pair differences
    # cancel that prefix. Cumulative link counts have no intra-window timestamps.
    am, bm = [read(NATIVE / arm / "area_metrics.json") for arm in ("hold", "selected")]
    links = []
    for key in set(am["physical_link_residence"]) | set(bm["physical_link_residence"]):
        x, y = [m["physical_link_residence"].get(key, {}) for m in (am, bm)]
        inside = x.get("inside", y.get("inside"))
        if x and y:
            assert x["inside"] == y["inside"]
        links.append(dict(link=key, inside=inside, delta_ttt=y.get("ttt_veh_h", 0.) - x.get("ttt_veh_h", 0.),
                          delta_slow=y.get("slow_veh_h", 0.) - x.get("slow_veh_h", 0.)))
    assert abs(sum(x["delta_ttt"] for x in links if x["inside"]) - source["delta_TTT_veh_h"]) < 1e-7
    exits = {k: bm["exit_events_by_observed_link_pair"].get(k, 0) - am["exit_events_by_observed_link_pair"].get(k, 0)
             for k in set(am["exit_events_by_observed_link_pair"]) | set(bm["exit_events_by_observed_link_pair"])}
    geometry = ET.fromstring(pin(ROOT / "diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx"))
    head_sg = {h.get("no"): h.get("sg").split()[1] for h in geometry.findall("./signalHeads/signalHead")}
    head_reader.LINKS = dict(SC6_S=1210018302, SC101_S=1220011503)
    phases = {
        "SC6_S": {"p1": ["SC6_S_SC12_to_N_SC103", "SC6_S_SC12_to_E_SC104"], "p2": ["SC6_S_SC12_to_W_SC5"]},
        "SC101_S": {"p1": ["SC101_S_SC1_to_N_SC2005"], "p2": ["SC101_S_SC1_to_W_SC1002"]},
    }
    heads, native_admitted = {}, {}
    for arm in ("hold", "city"):
        heads[arm] = []
        raw = [read(RUNS[arm] / f"state_{end:06}.json") for end in (2400, 2550, 2700, 2850)]
        native_admitted[arm] = {road: [y["obs150"]["source_cumulative_vehs"][road] - x["obs150"]["source_cumulative_vehs"][road]
                                     for x, y in zip(raw, raw[1:])] for road in ("FW_E", "FW_W")}
        for end in (2550, 2700, 2850):
            physical, events = head_reader.heads_and_entries(RUNS[arm], end)
            for group, phase_table in phases.items():
                node = cfg.network.signal_actuation_contract["nodes"][group.split("_")[0]]
                for phase, movements in phase_table.items():
                    native_heads = [x for x in physical[group]["rows"] if head_sg[x["head_id"]] in node["phase_signal_groups"][phase]]
                    assert native_heads
                    rows = [t for t in predictions[arm]["response"]["transfers"] if end - 150 <= t["start_sec"] < end
                            and t["source"] in {"movement:" + m for m in movements}]
                    heads[arm].append(dict(end=end, group=group, phase=phase, actual=sum(x["crossings"] for x in native_heads),
                                           model=sum(x["vehicles"] for x in rows), movements=movements))
    PINS.update(head_reader.PINS)
    predicted_blocks = {}
    for arm, p in predictions.items():
        predicted_blocks[arm] = []
        for end in (2550, 2700, 2850):
            rows = [r for r in p["response"]["residence"] if r["end_sec"] <= end + 1e-7]
            predicted_blocks[arm].append(dict(end=end, inside=sum(rows[-1]["inside_veh"].values()),
                cumulative_ttt=sum(sum(r["inside_veh"].values()) * r["dt_h"] for r in rows)))
    result = dict(status="completed_cached_city_response_localization", start_sec=2400, end_sec=2850,
        native_boundary=boundary, model_boundary_delta=model_delta,
        native_physical_link_cost_delta=sorted(links, key=lambda r: abs(r["delta_ttt"]), reverse=True),
        native_exit_count_delta_by_pair=sorted(exits.items(), key=lambda r: abs(r[1]), reverse=True),
        head_counts=heads, native_mainline_admitted=native_admitted, model_block_end_stocks=predicted_blocks,
        source_pins=PINS, new_predictions=0, new_native=0, new_fzp_scans=0, fits=0,
        previous_goal_turn="progress: qualified city-only native response isolated wrong city-signal gain direction",
        limitations=["One matched initial state; no future observation is used as a predictive input.",
            "5s sampled native boundary identity and 10s model endpoint identity are separate accounting checks.",
            "Boundary exit counts are not necessarily whole-network terminations; unexplained disappearances remain separate.",
            "Whole-link costs are geographic; initial model stock supports cannot establish complete future geographic identity.",
            "The two inspected approach heads are not a census of all urban signal movements."])
    pin(Path(__file__))
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf8")
    print("NATIVE_BOUNDARY", boundary["delta"])
    print("MODEL_ROUTES", sorted(model_delta.items(), key=lambda x: abs(sum(x[1][k] for k in ("entry_cost", "departure_cost", "generation_cost"))), reverse=True)[:8])
    print("HEADS", heads)
    print("LOCAL_COSTS", result["native_physical_link_cost_delta"][:12])
    print("ENTRIES", native_admitted)


if __name__ == "__main__":
    main()
