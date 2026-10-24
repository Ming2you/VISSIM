"""Read completed native JSON caches; never run VISSIM or rescan FZP."""
import argparse
import hashlib
import json
import sys
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def boundary_balances(root, geometry, audit, prediction):
    """Use already recorded detector bundles and stock frames, not future model inputs."""
    sys.path.insert(0, str(root))
    from evaluation.controllers import obs150_contract as oc
    from evaluation.controllers.obs150_observation import check_rule_crosscheck

    chains = {road: {int(x["link"]) for x in chain} for road, chain in geometry["chains"].items()}
    offs = [b for b in geometry["boundaries"] if b["kind"] == "offramp"]
    ramps = {road: [b["id"] for b in geometry["boundaries"] if b["kind"] == "ramp" and b["road"] == road]
             for road in chains}
    result = {"native": {}, "model_flow_counts": {}, "meter10681": {}, "new_forecasts": 0, "fzp_rescans": 0,
              "scope": "Integer150s recorded windows; removals excluded from exits. Closure residual = final minus (initial + source + merge - off_entry - terminal - removals). Off-ramp drain inferred by conservation, not an independent downstream detector."}
    for arm, pred_key in (("hold", "held_actual"), ("selected", "selected")):
        paths = sorted(Path(p) for p in audit["input_sha256"] if arm in Path(p).parts)
        assert len(paths) == 4
        states = [read(p) for p in paths]
        assert [s["sim_sec"] for s in states] == [2700, 2850, 3000, 3150]
        assert all(s["vehicle_records"]["complete"] for s in states)
        assert all(hashlib.sha256(p.read_bytes()).hexdigest() == audit["input_sha256"][str(p)] for p in paths)

        def stock(raw, links):
            return sum(int(v["link_no"]) in links for v in raw["vehicle_records"]["records"])

        rows = []
        meter_rows = []
        for i, (before, after) in enumerate(zip(states, states[1:])):
            start, end = before["sim_sec"], after["sim_sec"]
            obs = after[oc.RAW_STATE_KEY]
            detectors, _ = oc.read_detector_csv(obs["detector_config"]["path"], obs["detector_config"]["sha256"])
            oc.validate_raw(obs, detectors, expected_simres=oc.EXPECTED_SIMRES)
            check_rule_crosscheck(obs, detectors)
            bundle = oc.load_bundle(after)
            counts = oc.evaluate_boundaries(obs, detectors, bundle.frame_end, bundle.frame_start, bundle.err_rows)
            removals = oc.window_removals(bundle.err_rows, start, end)
            heads = [d for d in detectors if d.role == "meter_head" and d.link == 10681]
            assert len(heads) == 2 and {d.lane for d in heads} == {1, 2}
            meter = dict(start_sec=start, end_sec=end, lanes={})
            for head in heads:
                lane = {"head_crossings": counts[head.boundary_ref].cross}
                for name, raw in (("initial", before), ("final", after)):
                    vehicles = [v for v in raw["vehicle_records"]["records"]
                                if int(v["link_no"]) == 10681 and int(v["lane_no"]) == head.lane]
                    lane[name] = {side: {"vehicles": len(vs), "stopped": sum(v["stopped"] for v in vs)}
                        for side, vs in (("prehead", [v for v in vehicles if v["position_m"] <= head.pos]),
                                         ("posthead", [v for v in vehicles if v["position_m"] > head.pos]))}
                meter["lanes"][str(head.lane)] = lane
            meter_rows.append(meter)
            row = {"start_sec": start, "end_sec": end, "offramps": {}, "mainline": {}}
            for off in offs:
                link = off["connector"]
                initial, final = stock(before, {link}), stock(after, {link})
                entry = counts[f"off_entry:{link}"].cross
                removed = sum(int(r["link"]) == link for r in removals)
                row["offramps"][str(link)] = dict(road=off["road"], initial=initial, entry=entry,
                    drain=initial + entry - final - removed, final=final, removals=removed)
            for road, links in chains.items():
                initial, final = stock(before, links), stock(after, links)
                source = counts["source:" + road].cross
                terminal = counts["chain_end:" + road].cross
                merge = sum(audit["arms"][arm][r]["actual"]["windows"][i]["merge"] for r in ramps[road])
                off_entry = sum(r["entry"] for r in row["offramps"].values() if r["road"] == road)
                removed = sum(int(r["link"]) in links for r in removals)
                row["mainline"][road] = dict(initial=initial, source=source, merge=merge,
                    off_entry=off_entry, terminal=terminal, final=final, removals=removed,
                    closure_residual=final - (initial + source + merge - off_entry - terminal - removed))
            rows.append(row)
        result["native"][arm] = rows
        result["meter10681"][arm] = meter_rows
        result["model_flow_counts"][arm] = {k: v for k, v in prediction[pred_key]["control_area"]["flow_counts"].items()
                                                 if "freeway:" in k}
    result["native_response_delta_veh"] = {}
    for road in chains:
        result["native_response_delta_veh"][road] = {k: sum(row["mainline"][road][k] for row in result["native"]["selected"])
            - sum(row["mainline"][road][k] for row in result["native"]["hold"])
            for k in ("source", "merge", "off_entry", "terminal", "removals", "closure_residual")}
        result["native_response_delta_veh"][road]["final_stock"] = result["native"]["selected"][-1]["mainline"][road]["final"] - result["native"]["hold"][-1]["mainline"][road]["final"]
    result["coarse150_delta_ttt_veh_h"] = {}
    for road in chains:
        terms = {k: sum((b["mainline"][road][k] - a["mainline"][road][k])
                       * (3150 - (a["start_sec"] + a["end_sec"]) / 2) / 3600
                       for a, b in zip(result["native"]["hold"], result["native"]["selected"], strict=True))
                 for k in ("source", "merge", "off_entry", "terminal", "removals", "closure_residual")}
        terms["stock_trapezoid"] = sum(((b["mainline"][road]["initial"] - a["mainline"][road]["initial"])
                                        + (b["mainline"][road]["final"] - a["mainline"][road]["final"])) * 75 / 3600
                                       for a, b in zip(result["native"]["hold"], result["native"]["selected"], strict=True))
        assert abs(terms["stock_trapezoid"] - (terms["source"] + terms["merge"] - terms["off_entry"]
            - terms["terminal"] - terms["removals"] + terms["closure_residual"])) < 1e-9
        result["coarse150_delta_ttt_veh_h"][road] = terms
    result["coarse150_limitation"] = "Accounting identity at150s endpoints, not a causal decomposition or replacement for5s FZP TTT. Source timing differences cannot be removed to identify a pure control effect."
    return result


def assess(analysis, output, *, boundaries=False):
    root = Path(__file__).resolve().parents[3]
    integration = root / "diagnostics/sdmpc_n31_20260924/integration_20260926"
    summary_path = analysis / "summary.json"
    summary = read(summary_path)
    for key in ("counterfactual_valid", "paired_prefix_exact",
                "common_start_vehicle_records_exact", "original_initial_history_exact"):
        assert summary[key] is True, (key, summary[key])
    assert all(a["native_execution_passed"] for a in summary["arms"].values())
    prediction_path = Path(summary["prediction_source"])
    audit = read(analysis / "ramp_response_audit.json")
    assert hashlib.sha256(prediction_path.read_bytes()).hexdigest() == audit["prediction_sha256"]
    prediction = read(prediction_path)["results"]
    paths = {
        "summary": summary_path, "prediction": prediction_path,
        "geometry": integration / "selected/port_gain/geometry.json",
        "hold_area": integration / "native_rm_observation2700_writerfix_v3/analysis/hold/area_metrics.json",
        "selected_area": analysis / "selected/area_metrics.json",
        "ramps": analysis / "ramp_response_audit.json",
    }
    geometry = read(paths["geometry"])
    groups = {direction: {str(x["link"]) for x in chain}
              for direction, chain in geometry["chains"].items()}
    ramp_ids = {str(int(key.removeprefix("ramp:RM_C")))
                for key in prediction["held_actual"]["cost_by_stock"] if key.startswith("ramp:RM_C")}
    assert len(ramp_ids) == 8
    groups["eight_ramps"] = ramp_ids
    seen = set()
    for links in groups.values():
        assert not seen.intersection(links)
        seen.update(links)
    areas = {arm: read(paths[arm + "_area"])["physical_link_residence"]
             for arm in ("hold", "selected")}
    native, model = {}, {}
    for arm, pred_key in (("hold", "held_actual"), ("selected", "selected")):
        links = areas[arm]
        assert all(links[k]["inside"] for k in seen if k in links)
        native[arm] = {group: sum(links[k]["ttt_veh_h"] for k in ids if k in links)
                       for group, ids in groups.items()}
        native[arm]["other_Omega"] = sum(v["ttt_veh_h"] for k, v in links.items()
                                                if v["inside"] and k not in seen)
        assert abs(sum(native[arm].values()) - summary["arms"][arm]["TTT_0_3150_veh_h"]) < 1e-7
        p = prediction[pred_key]
        stocks = p["cost_by_stock"]
        assert abs(sum(stocks.values()) - p["ttt_omega_veh_h"]) < 1e-7
        model[arm] = {"FW_E": stocks["freeway:FW_E"], "FW_W": stocks["freeway:FW_W"],
                      "eight_ramps": sum(v for k, v in stocks.items() if k.startswith("ramp:"))}
        model[arm]["other_Omega"] = p["ttt_omega_veh_h"] - sum(model[arm].values())
    actual_delta = {k: native["selected"][k] - native["hold"][k] for k in native["hold"]}
    model_delta = {k: model["selected"][k] - model["hold"][k] for k in model["hold"]}
    assert abs(sum(actual_delta.values()) - summary["delta_TTT_veh_h"]) < 1e-7
    response = {}
    for ramp, hold in audit["arms"]["hold"].items():
        selected = audit["arms"]["selected"][ramp]
        response[ramp] = {field: {
            "actual": selected["actual"][field] - hold["actual"][field],
            "predicted": selected["predicted"][field] - hold["predicted"][field],
        } for field in ("arrival", "merge", "final_stock")}
    top_links = sorted(({
        "link": k, "inside": areas["hold"].get(k, areas["selected"].get(k))["inside"],
        "delta_veh_h": areas["selected"].get(k, {}).get("ttt_veh_h", 0)
                      - areas["hold"].get(k, {}).get("ttt_veh_h", 0),
    } for k in areas["hold"].keys() | areas["selected"].keys()), key=lambda x: x["delta_veh_h"])
    end_fields = ("Omega_TTD_events", "Omega_end_vehicles", "native_removals",
                  "unresolved_Omega_disappearances", "native_uninserted_at_end")
    result = {
        "status": "complete", "goal_qualified": False,
        "scope": "Selected minus held, common prefix and initial state verified; physical-link residence over 0-3150 cancels the identical prefix. No movement queue versus whole-link comparison.",
        "new_forecasts": 0, "fzp_rescans": 0,
        "actual_delta_veh_h": actual_delta, "model_delta_veh_h": model_delta,
        "model_minus_actual_delta_veh_h": {k: model_delta[k] - actual_delta[k] for k in model_delta},
        "actual_omega_delta_veh_h": sum(actual_delta.values()),
        "model_omega_delta_veh_h": sum(model_delta.values()),
        "outside_scope_separate": {
            "sampled_native_outside_delta_veh_h": summary["delta_outside_Omega_residence_veh_h"],
            "model_tracked_outside_delta_veh_h": prediction["selected"]["tracked_outside_residence_veh_h"] - prediction["held_actual"]["tracked_outside_residence_veh_h"],
            "native_total_including_uninserted_delta_veh_h": summary["delta_native_total_time_including_uninserted_veh_h"],
            "native_uninserted_delay_delta_veh_h": summary["delta_native_uninserted_delay_veh_h"],
            "note": "Tracked model outside stocks exclude some native network and uninserted costs; no like-for-like outside prediction error is claimed.",
        },
        "native_end_deltas": {k: summary["arms"]["selected"][k] - summary["arms"]["hold"][k] for k in end_fields},
        "native_arms": summary["arms"], "ramp_response_delta_veh": response,
        "largest_native_link_savings": top_links[:10], "largest_native_link_increases": top_links[-10:][::-1],
        "lsa_passed": {arm: value["lsa_passed"] for arm, value in summary["arms"].items()},
        "limitations": summary["limitations"],
        "input_sha256": {k: {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                         for k, p in paths.items()},
    }
    if boundaries:
        result["boundary_balances"] = boundary_balances(root, geometry, audit, prediction)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("actual_delta_veh_h", "model_delta_veh_h", "outside_scope_separate", "native_end_deltas")}, ensure_ascii=False))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--boundaries", action="store_true")
    args = parser.parse_args()
    assess(args.analysis, args.output, boundaries=args.boundaries)
