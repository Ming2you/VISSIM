"""Physical phase authority of the batch-1 candidates (urban.movements.physical_phase_authority), network v3b.

User decision 2026-09-26: the runtime declaration that SC7_E_to_N_SC11 / SC7_E_SC16_to_N_SC11 do not exist is the v2
reading. On v3b connector 10332 leaves the single lane of 1210009600 to 1220008701 -> 10334 -> SC11 (static route
252:3, relFlow 63), and head 140101 (SC7 SG 1) stands upstream of it and of its sibling 10333. The candidates
therefore use the v3b declaration (N31D/urban/movement_nonexistent_v3b_20260926.json: its 'corrected' movements
exist) and serve each corrected movement in the phase of its real head. This script writes that phase authority:
the default tuning's reviewed evidence (its urban.movements.physical_phase_authority, copied unchanged: the three
reviewed rows, the unsignalized and head-free sections, the network and plan pins) plus one by_movement row per
corrected movement, derived from the pinned .inpx and the selected plan exactly as
evaluation/controllers/physical_movement_routes.configure_phase_authority re-verifies them at install:
  path           the declaration's [stop-line link, connector, landing link]; the connector must leave that link
                 for that landing link
  connector      its lanes and end positions
  source_heads   every head of the signal on the stop-line link; upstream of the connector they cover every lane
  native_routes  every static route whose linkSeq passes the three elements; each enters the stop-line link
                 upstream of the heads
  new_phase      the unique selected-plan phase whose signal groups hold the heads' SGs; it must have native green,
                 and the declared phase must hold none of those SGs
  expected_spec  the movement's declared spec (signal, phase, origin, destination, receiving_link, kind); no
                 2026-08-28 phase correction may name it (the row replaces the declared phase)
Two record-only fields (configure_phase_authority does not read them; the network sha pin keeps them current):
  source_lane_connectors     every connector leaving the stop-line link from a head-covered lane, after the heads.
                             More than one means a shared stop-line lane: the model does NOT split its capacity by
                             routing beta (install_movement_capacity_by_lanes gives each movement its own connector
                             lanes; see CAVEATS). 2026-09-26 review: the first caveat claimed the opposite.
  crossed_heads_after_source every signal head on the connector, and on the landing link between the landing point
                             and the point where the native routes' vehicles leave it (the route's next connector, or
                             the landing link's only exit when the static route ends there), with its plan role (the
                             plan phase of its SG, 'midblock_native', or 'not_in_plan'). 2026-09-26 review: SC7 SG 16
                             (midblock, native program, in no plan phase) stands on 1220008701 before its only exit
                             10334; route 252:3 ends on 1220008701 at 3.6 m.
No other movement's phase changes. The adapter's complete-beta check refuses a routing_v3b2 table whose inputs name
another declaration or phase authority than the tuning, and flow in a phase without native green.

Run from the worktree root:
  python -B scripts/derive_phase_authority_v3b.py --out <file> [--check]
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

N31D = "diagnostics/sdmpc_n31_20260924"
DEFAULTS = {
    "network": N31D + "/network/baseline_s31_v3bnc.inpx",
    "movements": N31D + "/scenario/config_n31_v2.base.json",
    "declaration": N31D + "/urban/movement_nonexistent_v3b_20260926.json",
    "phase_correction": "outputs/movement_phase_correction_20260828.json",
}
SCHEMA = "physical-phase-authority/v1"
DECLARATION_SCHEMA = "movement-nonexistent-declaration/v1"
SPEC_KEYS = ("signal", "phase", "origin", "destination", "receiving_link", "kind")
RATIONALE = ("v3b correction (user decision 2026-09-26): the stop-line lane crosses this signal's head before the "
             "connector; the movement is served in the selected-plan phase of that head's SG. Phase correspondence "
             "only; no service capacity or yielding claim.")
CAVEATS = ["No capacity split on a shared stop-line lane (source_lane_connectors): install_movement_capacity_by_lanes gives "
           "every movement its own connector lanes, so each connector leaving the same lane after the same head carries "
           "its own connector-lane capacity. A head-observation floor of the (stop line, phase) group, when observed, "
           "redistributes by routing beta a total that starts at the sum of those member capacities. This is the model's "
           "rule for every shared stop-line lane, not a property of this phase correction; a lane-group capacity split "
           "is a capacity-model change.",
           "Heads crossed after the source head (crossed_heads_after_source) whose SG is in no selected-plan phase "
           "(a midblock SG running its native program) gate no model movement: their red is not represented in the "
           "service of this movement or of any other movement crossing them.",
           "Other signal controllers upstream, receiving blockage, and native conflict areas remain separate constraints."]


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derive(args) -> dict:
    net_path = ROOT / args.network
    root = ET.parse(str(net_path)).getroot()
    links = {x.get("no"): x for x in root.findall("./links/link")}
    heads = [x for x in root.findall("./signalHeads/signalHead")]
    tuning = json.loads((ROOT / args.movements).read_text(encoding="utf-8-sig"))
    um = tuning["config_overrides"]["network"]["urban_movements"]
    base_rel = ((tuning.get("urban") or {}).get("movements") or {}).get("physical_phase_authority")
    if not base_rel:
        raise SystemExit("the movements config names no physical_phase_authority to extend")
    base = json.loads((ROOT / base_rel).read_text(encoding="utf-8-sig"))
    if base.get("schema") != SCHEMA:
        raise SystemExit("unsupported base phase authority schema: %r" % base.get("schema"))
    if base["network"]["sha256"] != sha256(net_path) or base["network"]["path"] != args.network:
        raise SystemExit("the base phase authority is pinned to another network")
    plan_path = ROOT / base["selected_plan"]["path"]
    if sha256(plan_path) != base["selected_plan"]["sha256"]:
        raise SystemExit("selected plan differs from the base phase authority pin")
    plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    decl = json.loads((ROOT / args.declaration).read_text(encoding="utf-8"))
    if decl.get("schema") != DECLARATION_SCHEMA or decl["network"]["sha256"] != sha256(net_path):
        raise SystemExit("the declaration is not a v3b movement declaration of the pinned network")
    corrections = json.loads((ROOT / args.phase_correction).read_text(encoding="utf-8")).get("corrections") or {}

    # static routes: 'decision:route' -> (linkSeq, decision, route)
    routes = {}
    for d in root.findall("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic"):
        for r in d.findall("./vehRoutSta/vehicleRouteStatic"):
            seq = [d.get("link")] + [x.get("key") for x in r.findall("./linkSeq/intObjectRef")] + [r.get("destLink")]
            routes["%s:%s" % (d.get("no"), r.get("no"))] = (seq, d, r)
    ctl_of = {str(k): v for k, v in plan["controllers"].items()}

    def plan_role(sc: str, sg: str) -> str:
        ctl_ = ctl_of.get(sc.removeprefix("SC"))
        if ctl_ is None:
            return "not_in_plan"
        owners_ = sorted(p for p, g in ctl_["phase_signal_groups"].items() if sg in map(str, g))
        if owners_:
            return "phase:" + ",".join(owners_)
        if sg in map(str, ctl_.get("midblock_native_signal_groups") or []):
            return "midblock_native"
        return "not_in_plan"

    def head_row(h) -> dict:
        link_, lane_ = h.get("lane").split()
        sc_, sg_ = h.get("sg").split()
        return {"head": h.get("no"), "link": link_, "lane": int(lane_), "pos_m": float(h.get("pos")),
                "SC": "SC" + sc_, "SG": sg_, "plan_role": plan_role("SC" + sc_, sg_)}

    out = copy.deepcopy(base)
    added = {}
    for name, row in sorted((decl.get("corrected") or {}).items()):
        spec = um.get(name)
        if spec is None:
            raise SystemExit("the declaration corrects an unknown movement: " + name)
        if name in base["by_movement"] or name in corrections:
            raise SystemExit("%s already has a reviewed phase row or a 2026-08-28 correction" % name)
        source, connector, target = row["physical_path"]
        node = links.get(connector)
        start = node.find("fromLinkEndPt") if node is not None else None
        end = node.find("toLinkEndPt") if node is not None else None
        if start is None or end is None or start.get("lane").split()[0] != source or end.get("lane").split()[0] != target:
            raise SystemExit("%s: %s is not a connector %s -> %s" % (name, connector, source, target))
        conn = {"id": connector, "source_lane": int(start.get("lane").split()[1]), "source_pos": float(start.get("pos")),
                "target_lane": int(end.get("lane").split()[1]), "target_pos": float(end.get("pos")),
                "lanes": len(node.findall("./lanes/lane"))}
        signal = str(spec["signal"])
        own = [h for h in heads if h.get("lane").split()[0] == source and h.get("sg").split()[0] == signal.removeprefix("SC")]
        source_heads = [{"head": h.get("no"), "link": source, "lane": int(h.get("lane").split()[1]),
                         "pos_m": float(h.get("pos")), "SC": signal, "SG": h.get("sg").split()[1],
                         "all_vehicle_types": h.get("allVehTypes") == "true", "compliance": float(h.get("complRate", 1))}
                        for h in sorted(own, key=lambda h: h.get("no"))]
        if not source_heads or any(not h["all_vehicle_types"] or h["compliance"] != 1 for h in source_heads):
            raise SystemExit("%s: no complete all-vehicle head of %s on %s" % (name, signal, source))
        lanes = {h["lane"] for h in source_heads if h["pos_m"] < conn["source_pos"]}
        if lanes != set(range(1, len(links[source].findall("./lanes/lane")) + 1)):
            raise SystemExit("%s: the heads do not cover every lane of %s before the connector" % (name, source))
        native = []
        for key, (seq, d, _r) in routes.items():
            for i in range(len(seq) - 2):
                if seq[i:i + 3] != [source, connector, target]:
                    continue
                if d.get("allVehTypes") != "true" or d.get("routeChoiceMeth") != "STATIC":
                    raise SystemExit("%s: route %s has unsupported applicability" % (name, key))
                entry = float(d.get("pos")) if i == 0 else float(links[seq[i - 1]].find("toLinkEndPt").get("pos"))
                if entry >= min(h["pos_m"] for h in source_heads):
                    raise SystemExit("%s: route %s enters after the head" % (name, key))
                native.append(key)
                break
        if not native:
            raise SystemExit("%s: no static route passes %s" % (name, row["physical_path"]))
        # record only: the connectors that share the head-covered stop-line lanes after the heads ...
        shared = []
        for key, other in sorted(links.items(), key=lambda kv: int(kv[0])):
            edge = other.find("fromLinkEndPt")
            if edge is None or edge.get("lane").split()[0] != source:
                continue
            first, width = int(edge.get("lane").split()[1]), len(other.findall("./lanes/lane"))
            covered = set(range(first, first + width)) & lanes
            if covered and all(float(edge.get("pos")) > h["pos_m"] for h in source_heads if h["lane"] in covered):
                shared.append({"id": key, "source_lanes": sorted(range(first, first + width)),
                               "source_pos": float(edge.get("pos")), "lanes": width,
                               "target_link": other.find("toLinkEndPt").get("lane").split()[0]})
        if connector not in {c["id"] for c in shared}:
            raise SystemExit("%s: %s does not leave %s after its heads" % (name, connector, source))
        # ... and every head a vehicle of a native route crosses after the source head: on the connector, and on the
        # landing link from the landing point to where it leaves that link -- the route's next connector, or, when the
        # static route ends on the landing link, the landing link's only outgoing connector (with several, refuse)
        exits = sorted((k for k, x in links.items() if x.find("fromLinkEndPt") is not None
                        and x.find("fromLinkEndPt").get("lane").split()[0] == target), key=int)
        crossed = {}
        for key in native:
            seq, _d, r = routes[key]
            i = next(i for i in range(len(seq) - 2) if seq[i:i + 3] == [source, connector, target])
            if i + 3 < len(seq):
                leave_by = seq[i + 3]
            elif len(exits) == 1:
                leave_by = exits[0]
            else:
                raise SystemExit("%s: route %s ends on %s, which has exits %s" % (name, key, target, exits))
            if leave_by not in exits:
                raise SystemExit("%s: route %s does not leave %s by a connector" % (name, key, target))
            leave = float(links[leave_by].find("fromLinkEndPt").get("pos"))
            for h in heads:
                link_ = h.get("lane").split()[0]
                if link_ == connector or (link_ == target and conn["target_pos"] <= float(h.get("pos")) < leave):
                    row_ = crossed.setdefault(h.get("no"), dict(head_row(h), native_routes=[], leaves_by=[]))
                    row_["native_routes"].append(key)
                    if leave_by not in row_["leaves_by"]:
                        row_["leaves_by"].append(leave_by)
        crossed_rows = sorted(crossed.values(), key=lambda c: (c["link"] != connector, c["pos_m"], c["lane"]))
        ctl = plan["controllers"][signal.removeprefix("SC")]
        sgs = {h["SG"] for h in source_heads}
        owners = sorted(p for p, g in ctl["phase_signal_groups"].items() if sgs & set(map(str, g)))
        if len(owners) != 1 or not sgs <= set(map(str, ctl["phase_signal_groups"][owners[0]])):
            raise SystemExit("%s: the heads' SGs %s have no unique plan phase: %s" % (name, sorted(sgs), owners))
        phase = owners[0]
        if not ctl["phase_segments"].get(phase) or float(ctl["axis_green_sec"].get(phase, 0.0)) <= 0.0:
            raise SystemExit("%s: the plan phase %s of its head has no native green" % (name, phase))
        declared = str(spec["phase"])
        if sgs & set(map(str, ctl["phase_signal_groups"][declared.rpartition("_")[2]])):
            raise SystemExit("%s: declared phase %s already holds the head SG" % (name, declared))
        new_phase = signal + "_" + phase
        if new_phase == declared:
            raise SystemExit("%s: already in the phase of its head" % name)
        out["by_movement"][name] = {
            "expected_spec": {k: spec[k] for k in SPEC_KEYS},
            "new_phase": new_phase,
            "path": [source, connector, target],
            "native_routes": sorted(native, key=lambda k: tuple(map(int, k.split(":")))),
            "connector": conn,
            "source_heads": source_heads,
            "source_lane_connectors": shared,
            "crossed_heads_after_source": crossed_rows,
            "rationale": RATIONALE,
            "caveats": list(CAVEATS),
        }
        added[name] = {"before": declared, "after": new_phase, "heads": [h["head"] for h in source_heads],
                       "SGs": sorted(sgs), "native_green_sec": float(ctl["axis_green_sec"][phase]),
                       "shared_lane_connectors": [c["id"] for c in shared],
                       "crossed_heads": ["%s %s-%s %s" % (c["head"], c["SC"], c["SG"], c["plan_role"]) for c in crossed_rows]}
    if set(added) != set(decl.get("corrected") or {}):
        raise SystemExit("not every corrected movement got a phase row")
    out["v3b_corrections"] = {
        "generator": "scripts/derive_phase_authority_v3b.py",
        "generated": args.generated,
        "base": {"path": base_rel, "sha256": sha256(ROOT / base_rel)},
        "declaration": {"path": args.declaration, "sha256": sha256(ROOT / args.declaration)},
        "phase_correction": {"path": args.phase_correction, "sha256": sha256(ROOT / args.phase_correction)},
        "added": added,
        "unchanged": "every other key of the base evidence, byte-equal as JSON values",
    }
    return out


def dumps(doc: dict) -> bytes:
    return (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for k, v in DEFAULTS.items():
        ap.add_argument("--" + k.replace("_", "-"), dest=k, default=v)
    ap.add_argument("--generated", default="2026-09-26")
    ap.add_argument("--out", required=True)
    ap.add_argument("--check", action="store_true", help="compare with --out instead of writing it")
    args = ap.parse_args()
    data = dumps(derive(args))
    out = ROOT / args.out
    if args.check:
        if not out.is_file() or out.read_bytes() != data:
            raise SystemExit("%s differs from its derivation" % args.out)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    doc = json.loads(data)
    print("rows:", sorted(doc["by_movement"]))
    print("added:", doc["v3b_corrections"]["added"])
    print("PHASE_AUTHORITY_V3B_OK sha256=" + hashlib.sha256(data).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
