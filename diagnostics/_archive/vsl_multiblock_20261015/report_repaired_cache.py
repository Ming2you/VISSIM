"""Report the completed comparison from existing JSON caches only."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "native_analysis_repaired_20261016"
PACK = Path("D:/VISSIM_packages/vsl_multizone355_20261015")
OLD = Path("E:/VISSIM_analysis/20261011_vsl_response349/causal_off2250_analysis_v2/native_analysis")


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    horizon = read(OUT / "horizon_summary.json")
    summary = read(OUT / "summary.json")
    closure = read(OUT / "runtime_closure.json")
    assert closure["all_owned_processes_closed"] and closure["wrapper_closed"]
    assert closure["owner_exit_code"] == 0 and closure["normal_native_end_sec"] == 2700
    assert summary["counterfactual_valid"] and summary["existing_forecast_comparison_qualified"]
    membership_path = PACK / "diagnostics/repin_v3c3_review_20261001/urban_area263/approaches_only/membership.json"
    mapping_path = PACK / "evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json"
    ramps_path = PACK / "outputs/freeway_ramp_split_v2_20260907.json"
    inside = set(map(str, read(membership_path)["inside_links"]))
    mapping = read(mapping_path)
    ramps = read(ramps_path)
    groups = {
        "east_mainline": set(map(str, mapping["freeway_model_links"]["FW_E"]["chain_links"])) & inside,
        "west_mainline": set(map(str, mapping["freeway_model_links"]["FW_W"]["chain_links"])) & inside,
        "onramp_connectors": {str(x["connector"]) for x in ramps["on_ramps"]} & inside,
    }
    classified = set().union(*groups.values())
    assert len(classified) == sum(map(len, groups.values()))
    groups["urban_and_offramps"] = inside - classified
    assert len(inside) == 701 and set().union(*groups.values()) == inside
    paths = {"hold": OUT / "hold/area_metrics.json", "single90": OLD / "vsl90/area_metrics.json", "selected": OUT / "selected/area_metrics.json"}
    components = {}
    for case, path in paths.items():
        area = read(path)
        residence = area["physical_link_residence"]
        components[case] = {}
        for group, links in groups.items():
            components[case][group] = {
                key: sum(residence.get(link, {}).get(key, 0) for link in links)
                for key in ("ttt_veh_h", "slow_veh_h")
            }
        assert abs(sum(v["ttt_veh_h"] for v in components[case].values()) - area["ttt_veh_h"]) < 1e-6
        assert area["slow_threshold_kph"] == 5
    component_deltas = {
        case: {group: {key: values[key] - components["hold"][group][key] for key in values}
               for group, values in components[case].items()}
        for case in ("single90", "selected")
    }
    model_flow_deltas = {}
    model_component_deltas = {}
    for case in ("single90", "selected"):
        model_flow_deltas[case] = {}
        model_component_deltas[case] = {}
        for end in ("150", "300", "450"):
            a, b = horizon["model"]["hold"][end], horizon["model"][case][end]
            model_flow_deltas[case][end] = {key: b[key] - a[key] for key in b if isinstance(b[key], (int, float))}
            changes = {key: value - a["component_ttt"].get(key, 0) for key, value in b["component_ttt"].items()}
            grouped = {}
            for key, value in changes.items():
                prefix = key.split(":")[0]
                grouped[prefix] = grouped.get(prefix, 0) + value
            model_component_deltas[case][end] = {"groups": grouped, "east_mainline": changes.get("freeway:FW_E"), "west_mainline": changes.get("freeway:FW_W")}
    result = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Completed fixed city/RM conditional VSL experiment; JSON caches only",
        "new_fzp_scans": 0, "new_forecasts": 0, "new_native_runs": 0,
        "input_pins": {str(p): sha(p) for p in [OUT / "horizon_summary.json", OUT / "summary.json", OUT / "runtime_closure.json", membership_path, mapping_path, ramps_path, *paths.values()]},
        "partition": {key: sorted(values, key=int) for key, values in groups.items()},
        "component_totals_0_2700": components,
        "component_deltas_vs_hold": component_deltas,
        "component_delta_window": "0..2700 differences equal treatment-window differences because complete pre-treatment prefix is exact; absolute totals remain 0..2700",
        "model_transfer_deltas_NOT_native_counts": model_flow_deltas,
        "model_component_deltas": model_component_deltas,
        "limitations": [
            "Entry ramps here are the eight mapped on-ramp connectors; shared urban feeder links remain urban, not assigned wholesale to freeway.",
            "Slow residence is sampled time below5km/h, not queue length or stationary-only delay.",
            "Native internal merge and per-component final stock at150/300/450 are unavailable in these caches; not inferred from model transfers or Omega boundary counts.",
            "Physical-link residence and sampled Omega stock integrations differ at interpolation boundaries; compare treatment deltas with that sampling limitation.",
            "One seed, fixed recorded city/RM, negligible effect; no8100 policy or robust VSL benefit established.",
        ],
    }
    (OUT / "component_comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"component_deltas": component_deltas, "model450": model_flow_deltas["selected"]["450"], "partition_counts": {key: len(values) for key, values in groups.items()}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
