"""Prepare one input/route demand intervention; standard library, no traffic run."""
from __future__ import annotations

import csv
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PREFIX = ROOT / "diagnostics/demand_sweep_origin_routes"
NETWORK = ROOT / "diagnostics/fixed_beta300v3_network_arms_flat_v1/baseline.inpx"
PROFILE = ROOT / "evaluation/configs/demand_profiles/ver2_fdsweep_x15_20260907.csv"
ROLES = ROOT / "evaluation/real_world_modi_inventory/vehicle_input_roles.csv"
NETWORK_SHA = "085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317"
ALPHA = Fraction(4, 5)  # Parent's explicitly selected first experiment.


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_bytes(fields, rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def output(suffix, data):
    path = Path(str(PREFIX) + suffix)
    if path.exists():
        raise FileExistsError(path)
    path.write_bytes(data)
    return {"path": str(path.relative_to(ROOT)), "sha256": sha(path)}


def main():
    sources = [NETWORK, PROFILE, ROLES, Path(__file__),
               ROOT / "scripts/run_real_world_stackelberg_controller.vbs"]
    pins = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    assert sha(NETWORK) == NETWORK_SHA
    doc = ET.fromstring(NETWORK.read_bytes())
    links = {x.get("no"): x for x in doc.findall("./links/link")}
    inputs = {x.get("no"): x for x in doc.iter("vehicleInput")}
    decisions = {x.get("no"): x for x in doc.iter("vehicleRoutingDecisionStatic")}
    role_rows = list(csv.DictReader(ROLES.open(encoding="utf-8-sig", newline="")))
    roles = {x["no"]: x["role"] for x in role_rows}
    profile = {x["role"]: Fraction(x["multiplier"])
               for x in csv.DictReader(PROFILE.open(encoding="utf-8-sig", newline=""))}
    decision = decisions["1130"]
    routes = {x.get("no"): x for x in decision.findall("./vehRoutSta/vehicleRouteStatic")}
    assert set(routes) == {"1", "2", "3"}
    assert [x.get("no") for x in inputs.values() if x.get("link") == "74"] == ["1098"]
    assert [x.get("no") for x in decisions.values() if x.get("link") == "74"] == ["1130"]
    incoming, outgoing = [], []
    for key, link in links.items():
        f, t = link.find("fromLinkEndPt"), link.find("toLinkEndPt")
        if t is not None and t.get("lane", "").split()[0] == "74":
            incoming.append(key)
        if f is not None and f.get("lane", "").split()[0] == "74":
            outgoing.append({"connector": key, "from": f.attrib, "to": t.attrib})
    assert not incoming and len(outgoing) == 1 and outgoing[0]["connector"] == "10699"
    assert Fraction(decision.get("pos")) < Fraction(outgoing[0]["from"]["pos"])
    assert decision.get("allVehTypes") == "true" and decision.get("routeChoiceMeth") == "STATIC"
    assert decision.get("combineStaRoutDec") == "true"
    weights = {key: Fraction(route.get("relFlow").split(":")[1]) for key, route in routes.items()}
    assert weights == {"1": Fraction("1.6"), "2": Fraction(8), "3": Fraction(4)}
    assert all(route.get("formula") == "" for route in routes.values())
    old_total = sum(weights.values())
    new_weights = dict(weights, **{"3": weights["3"] * ALPHA})
    new_total = sum(new_weights.values())
    factor = new_total / old_total
    assert factor == Fraction(16, 17)
    complete_demand, table, override = [], [], []
    for no, vi in inputs.items():
        multiplier = profile.get("no:" + no, profile.get(roles.get(no, ""), profile["__default__"]))
        for interval in vi.findall("./timeIntVehVols/timeIntervalVehVolume"):
            start = int(Fraction(interval.get("timeInt").split()[1]) / 1000)
            base = Fraction(interval.get("volume"))
            before = base * multiplier  # Actual run DemandScale=1.
            after = before * factor if no == "1098" else before
            complete_demand.append({"input_no": no, "start_sec": start,
                                    "before_vph": float(before), "after_vph": float(after)})
            if no != "1098":
                assert before == after
                continue
            assert interval.get("vehComp") == "1" and interval.get("volType") == "STOCHASTIC"
            row = {"start_sec": start, "end_sec": start + 900, "native_input_vph": float(base),
                   "profile_multiplier": float(multiplier), "input_before_vph": float(before),
                   "input_after_vph": float(after)}
            for key in ("1", "2", "3"):
                old = before * weights[key] / old_total
                new = after * new_weights[key] / new_total
                assert new == old * (ALPHA if key == "3" else 1)
                row[f"route{key}_before_vph"] = float(old)
                row[f"route{key}_after_vph"] = float(new)
                row[f"route{key}_before_exact"] = str(old)
                row[f"route{key}_after_exact"] = str(new)
            table.append(row)
            override.append({"input_no": 1098, "start_sec": start, "volume_vph": format(float(after), ".17g")})
    assert len(complete_demand) == 204 and len(override) == 6
    assert [r["start_sec"] for r in override] == [0, 900, 1800, 2700, 3600, 4500]
    route_rows = []
    for key, route in routes.items():
        path = [decision.get("link"), *[x.get("key") for x in route.findall("./linkSeq/intObjectRef")], route.get("destLink")]
        route_rows.append({"route_no": key, "attributes": dict(route.attrib), "path": path,
                           "before_weight_exact": str(weights[key]), "after_weight_exact": str(new_weights[key]),
                           "before_probability_exact": str(weights[key] / old_total),
                           "after_probability_exact": str(new_weights[key] / new_total)})
    assert route_rows[2]["path"] == ["74", "10699", "2", "10682", "121", "10773", "123"]
    route_override = {
        "schema": "single-native-static-route-weight-override/v1",
        "status": "specification_only_network_not_generated_or_loaded",
        "base_network": str(NETWORK.relative_to(ROOT)), "base_network_sha256": NETWORK_SHA,
        "alpha": 0.8, "decision_no": 1130, "route_no": 3,
        "decision_attributes_before": dict(decision.attrib),
        "route_attributes_before": dict(routes["3"].attrib),
        "attribute_changes": {"relFlow": {"before": "2 0:4", "after": "2 0:3.2"}},
        "same_route_path": route_rows[2]["path"],
        "unchanged_sibling_relFlow": {"1": "2 0:1.6", "2": "2 0:8"},
        "requirements": ["Change exactly one relFlow attribute; preserve all other original XML bytes.",
                         "Keep route IDs, route sequence/destPos, classes, time interval, Combine and LookAhead unchanged.",
                         "Keep all signals, geometry and lane-change distance unchanged.",
                         "Apply the paired six absolute input overrides; a route-only weight change redistributes demand.",
                         "Verify native route readback and all 204 input/interval targets before simulation."],
    }
    files = [output(".input_override.csv", csv_bytes(["input_no", "start_sec", "volume_vph"], override)),
             output(".route_override.json", (json.dumps(route_override, ensure_ascii=False, indent=2) + "\n").encode()),
             output(".csv", csv_bytes(list(table[0]), table))]
    result = {
        "schema": "demand-sweep-origin-routes/v1", "alpha": float(ALPHA),
        "scope": "Declared source-cohort desired demand only; no observed passage/stock fitting, model, COM or VISSIM execution.",
        "network_sha256": NETWORK_SHA, "source_sha256": pins,
        "target": "Input1098 first decision1130 route3, 74→10699→2→10682→121→10773→123",
        "source74_proof": {"input": dict(inputs["1098"].attrib), "incoming": incoming,
                           "outgoing": outgoing, "only_decision": dict(decision.attrib),
                           "public_transport_lines_count": len(list(doc.iter("ptLine"))),
                           "parking_lots_count": len(list(doc.iter("parkingLot")))},
        "vehicle_composition1": [x.attrib for x in next(x for x in doc.iter("vehicleComposition") if x.get("no") == "1").findall("./vehCompRelFlows/vehicleCompositionRelativeFlow")],
        "routes": route_rows, "source_input_factor_exact": str(factor),
        "base_profile_multiplier_exact": str(profile[roles["1098"]]),
        "equivalent_single_input_profile_multiplier_exact": str(profile[roles["1098"]] * factor),
        "time_windows": table, "unchanged_other_input_intervals": 198,
        "all_input_interval_count": len(complete_demand), "all_input_intervals": complete_demand,
        "checks": {"non_target_1130_route1_2_exact_expected_demand_preserved_all_windows": True,
                   "target_route3_exact_expected_demand_times_alpha_all_windows": True,
                   "other_198_input_intervals_unchanged": True,
                   "network_generated": False, "COM_readback": False, "simulation_run": False},
        "excluded": {"input1100_route1124_1_whole_turn": "Reduces mixed city/other-destination demand and is outside the selected ramp-only intervention.",
                     "route1135_4_only_weight_change": "Shared46/52/66 origins; renormalizes10646/123 sibling demand unless upstream input/path weights are changed coherently. Deferred.",
                     "input1101_route1134_3": "Separate10639 ramp source experiment, not combined with the selected direct-offramp intervention."},
        "interpretation_limits": ["Rates describe source generation cohorts, not same-clock downstream ramp arrival or accepted service.",
                                  "STOCHASTIC input demand and changed RNG consumption do not preserve same-seed realized OD IDs/counts.",
                                  "Non-target source/path expected demand is preserved; realized non-target discharge can change with congestion.",
                                  "All6 source windows change from t0; no delayed stock-conditional selection or observed admission substitute.",
                                  "Current model native_demand_forecast enforces symmetric freeway sources; this asymmetric treatment requires the model-free fast NC path, not stripping fields to bypass model guards."],
        "outputs": files,
    }
    result["source_changes"] = [k for k, value in pins.items() if sha(ROOT / k) != value]
    assert not result["source_changes"]
    out = output(".json", (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode())
    print(json.dumps({"result": out, "paired_artifacts": files, "source_changes": []}, ensure_ascii=False))


if __name__ == "__main__":
    main()
