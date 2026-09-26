"""Stop-line crossing table for urban.queue.attribution "route" (SDMPC-31, network v3b).

The adapter attributes each observed queue vehicle on a queue link (a link of the detector mapping's
link_to_movements) to a movement by, in order (vissim_stackelberg_adapter._route_queue_shares):
  1. its current static route (RoutDecNo, RouteNo of the obs150 frame, bound to the snapshot), when the route's
     linkSeq contains the vehicle's link:
     a. the first crossing of an anchor (stop line or reviewed upstream branch -> connector) after that link;
     b. no crossing, but the route ends where a stop line of the link's movements can be reached before any other
        stop line (it ends ON the stop-line link, e.g. SC105 E 114:1, SC12 E 194:1): that stop line's movements by
        routing beta (the decision that re-routes the vehicle there);
     c. no crossing and no such stop line reachable from the route's end (it diverges before the approach:
        114:3 364 -> 359, 194:3 -> 1220015700, 254:4 -> 190): the vehicle is not in this approach's stop-line
        queue; it goes to the link's storage (the approach storage the observation already fills);
  2. without a usable route, on an anchor link: its lane -> the connectors that leave from that lane, split by the
     routing beta of their movements (a shared lane);
  3. otherwise (no route, not on an anchor link): the routing beta of the link's movements within each approach,
     the detector weights across approaches (the decision point's relFlow is that beta).
A crossing whose movements all carry beta 0 (a zero runtime beta on a physical connector; SC7 E 10332 was the case
until the v3b declaration correction of 2026-09-26 gave it its relFlow 0.429) and a crossing of an unsignalized
movement from a lane its connector does not leave are passed to the lane rule.
This file carries what the adapter needs, all derived from the pinned .inpx and the routing_v3b2 record:
  anchors          link -> connector -> {source lanes, runtime movement per approach (merge representative /
                   corridor keep)}
  routes           'decision:route' -> the linkSeq (decision link ... destLink), every static route of the network
  route_end_anchors 'decision:route' -> the anchor links reachable from the route's destLink before any other anchor
                   (the destLink itself when it is one), within MAX_WALK elements
  link_lengths_m   non-connector link -> polyline length of the pinned .inpx (the 30 m head window of the queue
                   member walk; the older FZP length table outputs/urban_link_geometry_20260904.json predates v3b)
  origins          'decision:route' -> approach, for the interchange populations of the pinned entry table.
                   DIAGNOSTIC ONLY (offramp_origin_veh counter): the off-ramp routes end on link 127 / 71 before
                   the stop line (1117 / 1140 re-route every vehicle), so no stop-line queue member carries them in
                   no-control; the proposal's "off-ramp origin to the off-ramp storage" rule is not implemented
                   (that storage is the lane plant's physical port, LaneOfframpRuntime.assert_mirrors).

Run from the worktree root:
  python -B scripts/derive_route_queue_attribution.py --out <file> [--check]
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import math
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
N31D = "diagnostics/sdmpc_n31_20260924"
DEFAULTS = {
    "network": N31D + "/network/baseline_s31_v3bnc.inpx",
    "beta": N31D + "/beta/movement_beta_routing_v3b2_20260925.json",
    "entry": N31D + "/beta/approach_entry_v3b2_20260925.json",
    "movements": N31D + "/scenario/config_n31_v2.base.json",
    "merge_plan": "outputs/movement_merge_plan_20260824.json",
}
SCHEMA = "route-queue-attribution/v2"
MAX_WALK = 40


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derive(args) -> dict:
    net_path = ROOT / args.network
    root = ET.parse(str(net_path)).getroot()
    conns = {}
    lengths = {}
    succ = collections.defaultdict(list)
    for el in root.iter("link"):
        f = el.find("fromLinkEndPt")
        if f is None:
            pts = [(float(p.get("x")), float(p.get("y"))) for p in el.iter("linkPolyPoint")]
            lengths[el.get("no")] = round(math.fsum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])), 3)
        if f is not None:
            link, lane = f.get("lane").split()
            conns[el.get("no")] = {"from": link, "lanes": list(range(int(lane), int(lane) + len(el.find("lanes").findall("lane")))),
                                   "from_pos_m": float(f.get("pos")), "to": el.find("toLinkEndPt").get("lane").split()[0]}
    for c, row in conns.items():
        succ[row["from"]].append(c)
        succ[c].append(row["to"])
    routes = {}
    for d in root.iter("vehicleRoutingDecisionStatic"):
        for r in d.iter("vehicleRouteStatic"):
            routes["%s:%s" % (d.get("no"), r.get("no"))] = ([d.get("link")] + [e.get("key") for e in r.iter("intObjectRef")]
                                                           + [r.get("destLink")])
    beta = json.loads((ROOT / args.beta).read_text(encoding="utf-8"))
    if beta["inputs"]["network"]["sha256"] != sha256(net_path):
        raise SystemExit("routing beta record was derived on another network")
    tuning = json.loads((ROOT / args.movements).read_text(encoding="utf-8-sig"))
    um = tuning["config_overrides"]["network"]["urban_movements"]
    rep = json.loads((ROOT / args.merge_plan).read_text(encoding="utf-8"))["leg_representative"]
    folded = {}
    for rel in ((tuning.get("urban") or {}).get("route_choice_corridor") or {}).get("evidence_paths", []):
        for row in json.loads((ROOT / rel).read_text(encoding="utf-8")).get("incoming_turns", {}).values():
            folded[row["remove"]] = row["keep"]

    def final(m: str) -> str:
        m = folded.get(m, m)
        s = um[m]
        return "%s_%s_to_%s" % (s["signal"], s["approach"], rep.get("%s|%s" % (s["signal"], s["exit"]), s["exit"]))

    anchors: dict[str, dict] = {}
    for rec in beta["approaches"]:
        key = "%s|%s" % (rec["signal"], rec["approach"])
        for m, cs in rec["physical_connectors"].items():
            for c in cs:
                link = conns[c]["from"]
                row = anchors.setdefault(link, {}).setdefault(c, {"lanes": conns[c]["lanes"],
                                                                 "from_pos_m": conns[c]["from_pos_m"],
                                                                 "to_link": conns[c]["to"], "movements": {}})
                old = row["movements"].get(key)
                if old is not None and old != final(m):
                    raise SystemExit("connector %s maps approach %s to two movements: %s / %s" % (c, key, old, final(m)))
                row["movements"][key] = final(m)
    entry = json.loads((ROOT / args.entry).read_text(encoding="utf-8"))
    if entry["network_sha256"] != sha256(net_path):
        raise SystemExit("entry table is pinned to another network")
    origins = {}
    for key, row in entry["entries"].items():
        for token in row["start"]:
            if ":" in token:
                origins[token] = key
            else:
                for r in routes:
                    if r.split(":")[0] == token:
                        origins[r] = key
    anchor_links = set(anchors)

    def end_anchors(dest: str) -> list[str]:
        """Anchor links reachable from a route's destLink before any other anchor (breadth first, MAX_WALK)."""
        found, seen, layer = set(), {dest}, [dest]
        for _ in range(MAX_WALK):
            nxt = []
            for x in layer:
                if x in anchor_links:
                    found.add(x)
                    continue
                for y in succ.get(x, []):
                    if y not in seen:
                        seen.add(y)
                        nxt.append(y)
            if not nxt:
                break
            layer = nxt
        return sorted(found, key=int)

    order = lambda x: tuple(map(int, x.split(":")))  # noqa: E731
    return {
        "schema": SCHEMA,
        "generated": args.generated,
        "network": {"path": args.network, "sha256": sha256(net_path)},
        "inputs": {k: {"path": getattr(args, k), "sha256": sha256(ROOT / getattr(args, k))} for k in DEFAULTS},
        "anchors": {k: anchors[k] for k in sorted(anchors, key=int)},
        "routes": {k: routes[k] for k in sorted(routes, key=order)},
        "route_end_anchors": {k: end_anchors(routes[k][-1]) for k in sorted(routes, key=order)},
        "link_lengths_m": {k: lengths[k] for k in sorted(lengths, key=int)},
        "origins": dict(sorted(origins.items())),
        "origins_use": "diagnostic_only",
    }


def dumps(doc: dict) -> bytes:
    return (json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for k, v in DEFAULTS.items():
        ap.add_argument("--" + k.replace("_", "-"), dest=k, default=v)
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
    print("anchors %d, routes %d (ending before an anchor %d), link lengths %d, origins %s" % (
        len(doc["anchors"]), len(doc["routes"]), sum(1 for v in doc["route_end_anchors"].values() if v),
        len(doc["link_lengths_m"]), doc["origins"]))
    print("ROUTE_QUEUE_ATTRIBUTION_OK sha256=" + hashlib.sha256(data).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
