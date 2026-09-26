"""Unsignalized turns with an exclusive lane (urban.movements.unsignalized_evidence), SDMPC-31 network v3b.

A movement is unsignalized in the model when every physical connector it uses (routing_v3b2 derivation record,
physical_connectors) satisfies, on the pinned .inpx:
  1. no signal head: none anywhere on the connector's source lanes of the source link, and none on the connector
     itself (heads on the landing link belong to the next stop line). Stricter than the head-free predicate of
     signal_head_observation's bypass collector (connector leaves before the head): a head placed just past a
     diverge (SC1002 N 10683, heads 0.5-0.8 m downstream on its lanes) is a network drafting question, not a free
     turn by design, and is listed instead (downstream_head_not_included);
  2. its source lanes are exclusive: no other connector leaves the source link from any of those lanes, so the
     turners never queue behind a signal-held movement in the same lane;
and the v3b no-control FZP confirms it (validation only, pinned file): at most 5% of the vehicles that take the
connector stopped on the source link before it, over at least 100 observed transitions (head-controlled references
stop 90-99%). A connector without enough observations is not included (listed).
Every stop-line / reviewed-branch connector of every approach is screened; the output lists the included
movements with the connector facts the adapter re-verifies at install time, and every screened connector without a
head on its lanes that fails the lane test (shared lane) with the other connectors of its lanes.
Movements that are already unsignalized through the reviewed physical phase authority (urban.movements.
physical_phase_authority: unsignalized_movements / head_free_movements) are reported, not repeated.

Run from the worktree root:
  python -B scripts/derive_unsignalized_turns.py --out <file> [--check]
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
N31D = "diagnostics/sdmpc_n31_20260924"
DEFAULTS = {
    "network": N31D + "/network/baseline_s31_v3bnc.inpx",
    "beta": N31D + "/beta/movement_beta_routing_v3b2_20260925.json",
    "movements": N31D + "/scenario/config_n31_v2.base.json",
    "validation": N31D + "/urban/unsignalized_validation_v3bnc_20260925.json",
}
MAX_STOPPED_SHARE = 0.05
MIN_OBSERVED = 100
SCHEMA = "unsignalized-turns/v1"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def network_facts(path: pathlib.Path):
    root = ET.parse(str(path)).getroot()
    links, heads = {}, collections.defaultdict(list)
    for el in root.iter("link"):
        f, t = el.find("fromLinkEndPt"), el.find("toLinkEndPt")
        lanes = el.find("lanes")
        rec = {"lanes": len(lanes.findall("lane")) if lanes is not None else 0}
        if f is not None and t is not None:
            fl, fln = f.get("lane").split()
            tl, _ = t.get("lane").split()
            rec.update(conn=True, frm=fl, frm_lane=int(fln), frm_pos=float(f.get("pos")), to=tl)
        else:
            rec["conn"] = False
        links[el.get("no")] = rec
    for h in root.iter("signalHead"):
        link, lane = h.get("lane").split()
        heads[link].append({"head": h.get("no"), "lane": int(lane), "pos_m": float(h.get("pos")), "sg": h.get("sg")})
    return links, heads


def connector_facts(links, heads, conn: str) -> dict:
    """The facts install_unsignalized_turns re-checks: source lanes/position, heads, lane-sharing connectors."""
    rec = links[conn]
    source = rec["frm"]
    lanes = list(range(rec["frm_lane"], rec["frm_lane"] + rec["lanes"]))
    controlling = [h for h in heads.get(source, []) if h["lane"] in lanes and h["pos_m"] <= rec["frm_pos"]]
    on_path = list(heads.get(conn, []))
    sharing = sorted(c for c, r in links.items() if r["conn"] and c != conn and r["frm"] == source
                     and set(range(r["frm_lane"], r["frm_lane"] + r["lanes"])) & set(lanes))
    return {"connector": conn, "source_link": source, "source_lanes": lanes, "source_pos_m": rec["frm_pos"],
            "target_link": rec["to"], "controlling_heads": controlling, "heads_on_connector": on_path,
            "lane_sharing_connectors": sharing,
            "downstream_heads_on_source_lanes": sorted(h["head"] for h in heads.get(source, [])
                                                       if h["lane"] in lanes and h["pos_m"] > rec["frm_pos"] + 1e-6)}


def derive(args) -> dict:
    net_path = ROOT / args.network
    links, heads = network_facts(net_path)
    beta = json.loads((ROOT / args.beta).read_text(encoding="utf-8"))
    if beta["inputs"]["network"]["sha256"] != sha256(net_path):
        raise SystemExit("routing beta record was derived on another network")
    validation = json.loads((ROOT / args.validation).read_text(encoding="utf-8"))
    if validation["network_sha256"] != sha256(net_path):
        raise SystemExit("FZP validation table belongs to another network")
    tuning = json.loads((ROOT / args.movements).read_text(encoding="utf-8-sig"))
    um = tuning["config_overrides"]["network"]["urban_movements"]
    authority_rel = ((tuning.get("urban") or {}).get("movements") or {}).get("physical_phase_authority")
    already = {}
    if authority_rel:
        auth = json.loads((ROOT / authority_rel).read_text(encoding="utf-8"))
        for key in ("unsignalized_movements", "head_free_movements"):
            for m, row in (auth.get(key) or {}).items():
                already[m] = {"source": authority_rel, "section": key, "path": row.get("path")}
    included, shared, signalized, unvalidated, downstream = {}, [], 0, [], []
    for rec in beta["approaches"]:
        for m, conns in sorted(rec["physical_connectors"].items()):
            if not conns:
                continue
            facts = [connector_facts(links, heads, c) for c in conns]
            free = [f for f in facts if not f["controlling_heads"] and not f["heads_on_connector"]]
            if len(free) != len(facts):
                signalized += 1
                for f in free:   # a head-free connector of a movement that also has a signalized one
                    shared.append({"movement": m, "reason": "movement_also_uses_signalized_connector", **f})
                continue
            if m in already or um[m].get("unsignalized"):
                already.setdefault(m, {"source": args.movements, "section": "urban_movements (config unsignalized)"})
                continue
            if any(f["lane_sharing_connectors"] for f in facts):
                for f in facts:
                    shared.append({"movement": m, "reason": "shared_source_lane", **f})
                continue
            if any(f["downstream_heads_on_source_lanes"] for f in facts):
                downstream.append({"movement": m, "connectors": [f["connector"] for f in facts],
                                   "downstream_heads": sorted({h for f in facts for h in f["downstream_heads_on_source_lanes"]})})
                continue
            checks = [validation["connectors"].get(f["connector"], {}) for f in facts]
            if any((x.get("stopped_before_n") or 0) < MIN_OBSERVED or x.get("stopped_before_share") is None
                   or x["stopped_before_share"] > MAX_STOPPED_SHARE for x in checks):
                unvalidated.append({"movement": m, "connectors": [f["connector"] for f in facts], "validation": checks})
                continue
            spec = um[m]
            included[m] = {"validation": checks, "expected_spec": {k: spec.get(k) for k in ("signal", "approach", "kind", "origin",
                                                                       "receiving_link")},
                           "connectors": facts, "routing_beta": beta["beta"][m]}
    return {
        "schema": SCHEMA,
        "generated": args.generated,
        "definition": ("A movement is unsignalized when every physical connector it uses has no signal head on its "
                       "source lanes at or upstream of the diverge, none on the connector itself, and "
                       "source lanes that no other connector uses. See scripts/derive_unsignalized_turns.py."),
        "network": {"path": args.network, "sha256": sha256(net_path)},
        "inputs": {k: {"path": getattr(args, k), "sha256": sha256(ROOT / getattr(args, k))} for k in DEFAULTS},
        "movements": included,
        "not_included_shared_lane": shared,
        "already_unsignalized_by_phase_authority": already,
        "screened_signalized_movements": signalized,
        "not_included_fzp_validation": unvalidated,
        "downstream_head_not_included": downstream,
        "validation_rule": {"max_stopped_before_share": MAX_STOPPED_SHARE, "min_observed_transitions": MIN_OBSERVED},
    }


def dumps(doc: dict) -> bytes:
    return (json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for k, v in DEFAULTS.items():
        ap.add_argument("--" + k, dest=k, default=v)
    ap.add_argument("--generated", default="2026-09-25")
    ap.add_argument("--out", required=True)
    ap.add_argument("--check", action="store_true")
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
    print("included:", sorted(doc["movements"]))
    print("shared-lane / mixed (not included):", sorted({(x["movement"], x["connector"], x["reason"]) for x in doc["not_included_shared_lane"]}))
    print("already unsignalized:", sorted(doc["already_unsignalized_by_phase_authority"]))
    print("not included (FZP validation):", [(x["movement"], x["connectors"]) for x in doc["not_included_fzp_validation"]])
    print("not included (head just downstream of the diverge):", [(x["movement"], x["connectors"])
                                                                  for x in doc["downstream_head_not_included"]])
    print("UNSIGNALIZED_TURNS_OK sha256=" + hashlib.sha256(data).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
