"""Paused-state E8/E9 receipt contract; no endpoint, FZP or traffic simulation.

The receipt validator checks supplied events, not how much traffic should move.
It deliberately supplies no lane-change probability, service or speed law.
"""
from __future__ import annotations

from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from evaluation.controllers.projection_support import complete_records
from evaluation.controllers.vehicle_routes import complete_vehicle_routes

ROOT = Path(__file__).resolve().parents[1]
RUN = "codex_area_sources_beta0_s13_20260910"
NETWORK = "network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx"
MAPPING = "evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json"
NODES = ("10643", "10639", "10682", "10681")


def finite_nonnegative(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError("Expected a finite nonnegative number")
    return float(value)


def commit_receipts(initial, owners, capacities, allowed_edges, events, duration_sec=10.):
    """Check and commit explicit accepted events to disjoint stock subsets.

    allowed_edges is route/progress/lane evidence, never an inferred equal split.
    capacities are caller-supplied *physical* bucket limits for this algebraic
    test. Production receiver resources shared by several buckets need the same
    reservation table; no capacity is estimated here. A prior accepted event
    may release space for a later event. Simultaneous demand allocation is not
    specified by this validator and must not be inferred from input row order.
    """
    duration_sec = finite_nonnegative(duration_sec)
    stock = {k: finite_nonnegative(v) for k, v in initial.items()}
    if set(stock) != set(owners) or set(stock) != set(capacities):
        raise ValueError("Every disjoint stock needs exactly one owner and capacity")
    caps = {k: finite_nonnegative(v) for k, v in capacities.items()}
    if any(stock[k] > caps[k] + 1e-9 for k in stock):
        raise ValueError("Initial stock exceeds declared capacity")
    owner0 = Counter()
    for key, n in stock.items():
        owner0[owners[key]] += n
    seen, last_time, receipts = set(), -1., []
    for row in events:
        key, source, target = row["receipt_id"], row["source"], row["target"]
        at, count = finite_nonnegative(row["at_sec"]), finite_nonnegative(row["vehicles"])
        if not key or key in seen:
            raise ValueError("Receipt identity is missing or duplicated")
        if at < last_time or at > duration_sec:
            raise ValueError("Receipt time is outside the step or unordered")
        if source == target or source not in stock or target not in stock or (source, target) not in allowed_edges:
            raise ValueError("Unproved path/route/lane edge")
        if count > stock[source] + 1e-9:
            raise ValueError("Source overdraw: rejected demand must stay upstream")
        if count > caps[target] - stock[target] + 1e-9:
            raise ValueError("Shared receiving space was oversubscribed")
        stock[source] -= count
        stock[target] += count
        receipts.append(copy.deepcopy(row))
        seen.add(key)
        last_time = at
    owner1 = Counter()
    for key, n in stock.items():
        owner1[owners[key]] += n
    residual = sum(stock.values()) - sum(initial.values())
    if abs(residual) > 1e-9:
        raise AssertionError("Receipt conservation failed")
    return {"stock": stock, "owner_delta": {k: owner1[k] - owner0[k] for k in owner0},
            "receipts": receipts, "mass_residual": residual}


def node_only_deltas(signal, direct, merge_before, merge_after, through_correction=0.):
    """Cell deltas relative to the current grouped location, fixed other rates.

    Input unit is vehicles per one common interval. through_correction is the
    concurrent change in E8->E9 accepted receipts, not an automatic parameter.
    """
    s, d, a, b, dq = map(finite_nonnegative, (signal, direct, merge_before, merge_after, through_correction))
    old = {"E8": -(s+d), "E9": a+b}
    ordered = {"E8": -s+a-dq, "E9": -d+b+dq}
    result = {k: ordered[k]-old[k] for k in old}
    assert abs(sum(result.values())) < 1e-9
    return result


def main():
    output = ROOT / "diagnostics/e8_receipt_contract_diagnosis.json"
    if output.exists():
        raise FileExistsError("Preserve historical output; select/rename explicitly before another run")
    paths = [NETWORK, MAPPING, "evaluation/controllers/area_freeway_accounting.py",
             "evaluation/controllers/link_predictor.py", "evaluation/controllers/urban_flow_accounting.py",
             "vendor/NumSim-mine/src/controllers/local_freeway_plant.py",
             "vendor/NumSim-mine/src/simulation/coupling.py",
             "diagnostics/e8_ordered_gate_observability.json",
             "diagnostics/e8_route_flow_assignment_1200.json", "diagnostics/e8_route_flow_assignment_3300.json",
             "evaluation/controllers/projection_support.py", "evaluation/controllers/vehicle_routes.py",
             str(Path(__file__).relative_to(ROOT)).replace("\\", "/")]
    snapshots = [f"evaluation/runs/{RUN}/decisions_{RUN}/state_{t:06d}.json" for t in (900, 1200, 3300)]
    paths += snapshots
    sha = lambda p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    pins = {p: sha(p) for p in paths}
    prior = json.loads((ROOT / paths[7]).read_text(encoding="utf-8"))
    for p in (NETWORK, MAPPING):
        assert prior["source_sha256"][p] == pins[p], "Pinned physical geometry changed"
    mapping = json.loads((ROOT/MAPPING).read_text(encoding="utf-8"))["freeway_model_links"]["FW_E"]
    offset = mapping["chain_offsets_m"][mapping["chain_links"].index(2)]
    lower, boundary, upper = mapping["segment_bounds_m"][8:11]
    xml = ET.parse(ROOT/NETWORK).getroot()
    links = {x.get("no"): x for x in xml.findall("./links/link")}
    nodes = {}
    for key in NODES:
        role = "diverge" if key in ("10643", "10682") else "merge"
        end = links[key].find("fromLinkEndPt" if role == "diverge" else "toLinkEndPt")
        road, first_lane = map(int, end.get("lane").split())
        assert road == 2
        nodes[key] = {"role": role, "chain_m": offset+float(end.get("pos")),
                      "lanes": list(range(first_lane, first_lane+len(links[key].findall("./lanes/lane"))))}
    assert [nodes[k]["chain_m"] for k in NODES] == sorted(nodes[k]["chain_m"] for k in NODES)
    cuts = [lower, nodes["10643"]["chain_m"], nodes["10639"]["chain_m"], boundary,
            nodes["10682"]["chain_m"], nodes["10681"]["chain_m"], upper]
    reaches = [{"reach": i, "lower_m": a, "upper_m": b, "length_m": b-a,
                "macro_owner": "E8" if b <= boundary else "E9"} for i, (a,b) in enumerate(zip(cuts,cuts[1:]))]
    by_snapshot = []
    for relative in snapshots:
        raw = json.loads((ROOT/relative).read_text(encoding="utf-8"))
        records = complete_records(raw)
        route_rows = complete_vehicle_routes(raw, required=True)
        rows, buckets = [], Counter()
        for vehicle in records:
            x = vehicle["position_m"]+offset
            if vehicle["link_no"] != 2 or not lower <= x < upper:
                continue
            reach = next(r for r in reaches if r["lower_m"] <= x < r["upper_m"])
            route = route_rows[vehicle["veh_no"]]
            tag = (f"{route['route_decision_no']}:{route['route_no']}"
                   if route["route_decision_type"] == "STATIC" else "unresolved")
            bucket = f"{reach['reach']}|lane{vehicle['lane_no']}|{tag}"
            buckets[bucket] += 1
            rows.append({"veh_no": vehicle["veh_no"], "reach": reach["reach"], "macro_owner": reach["macro_owner"],
                         "chain_m": x, "lane": vehicle["lane_no"], "route": tag,
                         "speed_kph": vehicle["speed_kph"], "remaining_to_next_cut_m": reach["upper_m"]-x})
        macro_counts = Counter(r["macro_owner"] for r in rows)
        for i in (8,9):
            assert macro_counts[f"E{i}"] == raw["freeway_segments"]["FW_E"][i]["count"]
        by_reach = []
        for reach in reaches:
            group = [r for r in rows if r["reach"] == reach["reach"]]
            by_reach.append({**reach, "count": len(group), "lanes": [dict(Counter(r["route"] for r in group if r["lane"] == lane)) for lane in (1,2,3,4)],
                             "density_veh_km_lane": len(group)/(reach["length_m"]/1000*4)})
        current_bounds = {}
        for node, tag in (("10643", "1130:1"), ("10682", "1130:3")):
            candidates = [r for r in rows if r["route"] == tag and r["chain_m"] < nodes[node]["chain_m"]]
            compatible = [r for r in candidates if r["lane"] in nodes[node]["lanes"]]
            current_bounds[node] = {"route_tag": tag, "current_route_stock_upstream_in_scope": len(candidates),
                                   "same_lane_upstream_stock": len(compatible),
                                   "needs_lateral_exchange": len(candidates)-len(compatible),
                                   "already_past_node_same_route_ids": [r["veh_no"] for r in rows if r["route"] == tag and r["chain_m"] > nodes[node]["chain_m"]],
                                   "scope": "Current positions/lane compatibility only; not a future discharge bound with upstream arrivals/exchanges."}
        branches = {node: {"count": sum(r["link_no"] == int(node) for r in records),
                            "route_counts": dict(Counter(f"{route_rows[r['veh_no']]['route_decision_no']}:{route_rows[r['veh_no']]['route_no']}" for r in records if r["link_no"] == int(node)))}
                    for node in NODES}
        assert branches["10639"]["count"]+branches["10681"]["count"] == raw["ramp_counts"]["R_F_E"]
        by_snapshot.append({"source": relative, "sha256": pins[relative], "sim_sec": raw["sim_sec"],
                            "macro_counts": dict(macro_counts), "buckets": dict(buckets), "reaches": by_reach,
                            "current_exit_lane_bounds": current_bounds, "branch_stocks": branches, "vehicle_rows": rows,
                            "stock_sum_residual": sum(buckets.values())-sum(macro_counts.values()),
                            "new_initial_omega_entries_or_exits": 0,
                            "future_data_used": False})
    arithmetic = []
    for t in (1200,3300):
        history = json.loads((ROOT/f"diagnostics/e8_route_flow_assignment_{t}.json").read_text(encoding="utf-8"))
        first, schedule = history["freeway_cells"][0], history["offramp_schedule"][0]
        s,d = schedule["signal_accepted_veh"], schedule["direct_accepted_veh"]
        total_merge = first["merge_R_FE_vph"]/360.
        arithmetic.append({"historical_start_sec":t, "signal_veh_first10s":s, "direct_veh_first10s":d,
                           "group_merge_veh_first10s":total_merge,
                           "direct_only_relabel_fixed_through_delta":node_only_deltas(s,d,0.,total_merge),
                           "direct_relabel_plus_equal_through_restoration_delta":node_only_deltas(s,d,0.,total_merge,d),
                           "before_merge_correction_range_E8_veh": [0.,total_merge],
                           "scope":"Incidence arithmetic on already recorded historical flows, not a new current-source replay or valid traffic forecast. Actual before-merge receipt is unidentified by the group total."})
    changes = [p for p,h in pins.items() if sha(p) != h]
    assert not changes, changes
    result = {"schema":"e8-receipt-contract-diagnosis/v1", "scope":"Current snapshot partition and algebraic receipt checks only; no new traffic prediction.",
              "source_sha256":pins, "source_changes":changes, "nodes":nodes, "reaches":reaches,
              "snapshots":by_snapshot, "incidence_counterexamples":arithmetic,
              "limitations":["Current native route identity may end/change inside E9; future route decision requires its declared prior at the actual decision position.",
                             "Initial same-lane stock does not identify future successful lane changes or service; unknown routes remain unknown.",
                             "A supplied accepted-event validator is not a predictive allocator, speed model or proof of improved E8 prediction."]}
    output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"output":str(output.relative_to(ROOT)), "snapshots":[{"sim_sec":r["sim_sec"],"macro_counts":r["macro_counts"],"reach_counts":[z["count"] for z in r["reaches"]],"branches":r["branch_stocks"]} for r in by_snapshot],"source_changes":changes},indent=2))


if __name__ == "__main__":
    main()
