"""Control-area route contract of the batch-1 candidates (control_area_objective.route_contract_path), network v3b.

User decision 2026-09-26: SC7_E_SC16_to_N_SC11 exists on v3b (connector 10332, relFlow 0.429) and is served in its
head's phase p4 (scripts/derive_phase_authority_v3b.py). A movement that departs needs a physical area route
(ModelAreaLedger.transfer refuses an unresolved destination), and the default contract
(diagnostics/control_area_route_contract_physical_routes.json, control_area_join.build_movement_join) left it
'no_match': its canonical turn (outputs/pn_boundary_turns_v2_20260907.json: 1210009600 -> 10332 -> 1220008701, leg
SC7-E_SC16, heading N, SG 1) lands on 1220008701, which the detector mapping observes as the S_SC108 approach storage
(SC108_to_SC7), so the join rejected it as 'different_model_storage'; the model receiver SC7_to_SC11 starts one unique
hop later (10334 -> 1220008702). With beta 0 it never departed, so this never surfaced.
This script writes the candidates' contract: the default contract unchanged, plus a departure route
('movement:<name>') for every corrected movement of the v3b declaration whose approach the default contract already
resolves (an approach it leaves unresolved keeps the corrected movement unresolved too: the synthetic boundary leg
SC7 E, in_SC7_E, which holds no vehicles in the R-obs-b replays; at runtime area_arrival_routes.extend_gate_routes
resolves both of its movements as gate aliases of the E_SC16 routes, SC7_E_to_N_SC11 now included, checked on the
T2700 replay: 35 gate aliases instead of 34). The route is built like build_movement_join's rows: the phase
authority row's stop-line turn [link, connector, landing] (turn_membership on the pinned area membership), its
canonical turn (leg and heading must match), and the receiver support: the landing's unique physical successors reach
a link whose detector-mapping origins hold the movement's receiving link. Arrival routes are not written (the runtime
fills them from the resolved sibling, area_arrival_routes.extend_gate_routes).

Run from the worktree root:
  python -B scripts/derive_area_routes_v3b.py --out <file> [--check]
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from evaluation.controllers.control_area_join import turn_membership  # noqa: E402
from evaluation.controllers.control_area_objective import physical_membership_from_ledger  # noqa: E402

N31D = "diagnostics/sdmpc_n31_20260924"
DEFAULTS = {
    "movements": N31D + "/scenario/config_n31_v2.base.json",
    "declaration": N31D + "/urban/movement_nonexistent_v3b_20260926.json",
    "phase_authority": N31D + "/urban/physical_phase_authority_v3b_20260926.json",
    "turns": "outputs/pn_boundary_turns_v2_20260907.json",
}
DECLARATION_SCHEMA = "movement-nonexistent-declaration/v1"
MAX_HOPS = 8


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8-sig"))


def derive(args) -> tuple[dict, dict]:
    tuning = read(args.movements)
    um = tuning["config_overrides"]["network"]["urban_movements"]
    area = tuning["control_area_objective"]
    base_rel, membership_rel, detectors_rel = area["route_contract_path"], area["membership_path"], tuning["detector_mapping_json"]
    base = read(base_rel)
    membership = read(membership_rel)
    physical = physical_membership_from_ledger(membership)
    net_path = ROOT / membership["network"]["path"]
    if sha256(net_path) != membership["network"]["sha256"]:
        raise SystemExit("area membership is pinned to another network")
    detectors = read(detectors_rel)
    decl = read(args.declaration)
    authority = read(args.phase_authority)
    if decl.get("schema") != DECLARATION_SCHEMA or decl["network"]["sha256"] != membership["network"]["sha256"]:
        raise SystemExit("the declaration is not a v3b movement declaration of the membership network")
    if authority["network"]["sha256"] != membership["network"]["sha256"]:
        raise SystemExit("the phase authority is pinned to another network")
    canonical = {str(t["connector"]): t for t in read(args.turns)["turns"]}
    root = ET.parse(str(net_path)).getroot()
    succ: dict[str, list[str]] = {}
    for el in root.iter("link"):
        f, t = el.find("fromLinkEndPt"), el.find("toLinkEndPt")
        if f is not None and t is not None:
            succ.setdefault(f.get("lane").split()[0], []).append(el.get("no"))
            succ.setdefault(el.get("no"), []).append(t.get("lane").split()[0])
    link_to_origins = {str(k): [str(x) for x in v] for k, v in detectors["link_to_origins"].items()}

    out = copy.deepcopy(base)
    added, kept = {}, {}
    for name in sorted(decl.get("corrected") or {}):
        spec = um[name]
        key = "movement:" + name
        if type(base.get(key, {}).get("target_inside")) is bool:
            raise SystemExit("%s already has a resolved departure route in the default contract" % name)
        siblings = [m for m, s in um.items() if m != name and s["signal"] == spec["signal"]
                    and s["approach"] == spec["approach"]]
        resolved = [m for m in siblings if type(base.get("movement:" + m, {}).get("target_inside")) is bool]
        if not resolved:
            kept[name] = {"reason": "approach_unresolved_in_default_contract", "siblings": sorted(siblings)}
            continue
        row = authority["by_movement"].get(name)
        if row is None:
            raise SystemExit("%s has no phase authority row" % name)
        source, connector, landing = row["path"]
        turn = canonical.get(connector)
        leg = "%s·%s" % (spec["signal"], spec["approach"])
        heading = str(spec["exit"]).split("_")[0]
        if (turn is None or str(turn["from_link"]) != source or str(turn["to_link"]) != landing
                or leg not in turn.get("legs", []) or str(turn.get("heading")) != heading or turn.get("sc") != spec["signal"]):
            raise SystemExit("%s: canonical turn %s does not match leg %s / heading %s" % (name, connector, leg, heading))
        # receiver support: unique physical successors from the landing to a link observed as the receiving storage
        trail, element = [landing], landing
        while spec["receiving_link"] not in link_to_origins.get(element, []):
            nxt = succ.get(element, [])
            if len(nxt) != 1 or len(trail) > MAX_HOPS:
                raise SystemExit("%s: no unique physical continuation from %s to %s" % (name, landing, spec["receiving_link"]))
            element = nxt[0]
            trail.append(element)
        member = turn_membership({"from_link": source, "connector": connector, "to_link": landing}, physical)
        continuation = [x for x in trail if x in physical]
        if any(physical[x] != member["target_inside"] for x in continuation):
            raise SystemExit("%s: the continuation to the receiver crosses the area boundary" % name)
        member.update({
            "canonical_class": turn["class"], "signal": spec["signal"], "canonical_source_legs": turn.get("legs", []),
            "source_evidence": {"canonical_approach_leg": True,
                                "runtime_detector_stopline": source in {str(k) for k, rows in detectors["link_to_movements"].items()
                                                                        if any(r["movement"] == name for r in rows)}},
            "exit_evidence": {"canonical_heading_matches_exit_compass": True, "actual_destination_storage_matches": False},
            "destination_support_status": "receiver_after_unique_physical_continuation",
            "destination_storage_support": link_to_origins.get(landing, []),
            "destination_support_paths": [trail],
            "receiver_support_link": element,
            "native_routes": list(row["native_routes"]),
            "weight_source": None, "weight": None, "canonical_declared_flow_veh_h": turn.get("flow_veh_h")})
        out[key] = {"status": "v3b_corrected_declaration", "source_inside": member["source_inside"],
                    "target_inside": member["target_inside"], "inside_to_inside": float(member["target_inside"]),
                    "outside_to_inside": float(member["target_inside"]),
                    "outward_crossings_per_vehicle": member["outward_crossings_per_vehicle"],
                    "inward_crossings_per_vehicle": member["inward_crossings_per_vehicle"],
                    "physical_turns": [member], "unresolved_reason": None,
                    "resolved_siblings_in_default_contract": sorted(resolved)}
        added[name] = {"path": [source, connector, landing], "continuation": trail, "receiver": spec["receiving_link"],
                       "source_inside": member["source_inside"], "target_inside": member["target_inside"]}
    record = {"generator": "scripts/derive_area_routes_v3b.py", "generated": args.generated,
              "base": {"path": base_rel, "sha256": sha256(ROOT / base_rel)},
              "membership": {"path": membership_rel, "sha256": sha256(ROOT / membership_rel)},
              "detector_mapping": {"path": detectors_rel, "sha256": sha256(ROOT / detectors_rel)},
              "inputs": {k: {"path": getattr(args, k), "sha256": sha256(ROOT / getattr(args, k))} for k in DEFAULTS},
              "added": added, "left_unresolved": kept}
    return out, record


def dumps(doc: dict) -> bytes:
    return (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for k, v in DEFAULTS.items():
        ap.add_argument("--" + k.replace("_", "-"), dest=k, default=v)
    ap.add_argument("--generated", default="2026-09-26")
    ap.add_argument("--out", required=True)
    ap.add_argument("--check", action="store_true", help="compare with --out (and its .provenance.json) instead")
    args = ap.parse_args()
    doc, record = derive(args)
    data, prov = dumps(doc), dumps(record)
    out = ROOT / args.out
    side = out.with_name(out.stem + ".provenance.json")
    if args.check:
        if not out.is_file() or out.read_bytes() != data or not side.is_file() or side.read_bytes() != prov:
            raise SystemExit("%s differs from its derivation" % args.out)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        side.write_bytes(prov)
    print("added:", record["added"])
    print("left unresolved:", record["left_unresolved"])
    print("AREA_ROUTES_V3B_OK sha256=%s provenance=%s" % (hashlib.sha256(data).hexdigest(), hashlib.sha256(prov).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
