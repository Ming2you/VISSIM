"""Complete physical routing beta for every runtime movement (urban.beta.source routing_v3b2).

User decision 2026-09-25: a movement's beta is 0 if there is no physical path from its approach to its exit,
otherwise the share of the static routes' relFlow (exogenous). No realised (NC FZP) shares are values; the
v3b no-control FZP is only a validation target.

Why a second derivation (scripts/derive_routing_turn_beta.py stays, it rebuilds the 0824 and routing_v3b tables)
-----------------------------------------------------------------------------------------------------------------
routing_v3b covers 370 of the 492 runtime movements. The rest keep the config default share (1/2, 1/4, 1/6, 1/8),
and so do covered movements that no route evidence reaches ("held" shares). At runtime these held shares do not
create vehicles but distort the split: the leg_split fold adds the on-ramp shares to the W exit, and the exit merge
renormalises every approach to 1 (adapter install_leg_ramp_split_fold / install_merged_movements). Example: SC1001
S_SC1003 left turn 0.333 in the table, 0.429 at runtime, 0.32-0.34 in the v3b FZP.

What this derivation does instead
---------------------------------
1. Stop lines and their connectors. The stop line of an approach is the one of
   outputs/movement_connector_map_ver2_20260907.json (key signal|representative leg of the merge plan); every
   connector that leaves that link in the pinned .inpx is a physical turn. Eight interchange approaches get their
   stop line and population start from the pinned entry table (N31D/beta/approach_entry_v3b2_20260925.json).
2. Exit of a connector. Walk downstream from the connector's to-link: the first link owned (territory v2) by
   another signal is an internal exit to that signal; a freeway link or the end of the network is a boundary exit.
   A boundary exit is named by the physical out-link table (outputs/out_link_storage_ver2_20260909.json, the links
   of each '<sig>_<h>_out') wherever it lists a link the path passes, else by the compass heading of the links
   passed, nearest first (the pn_boundary_turns heading rule). Review 2026-09-26: the heading rule alone sent SC104
   S_SC106 10171 -> 65 (15.5 m, heads N) -> 10092 -> 1220061100 to N_out, but 1220061100 is the E out link (also
   entered by 10099 and 10102). Every boundary exit of a signal that ends on the same element must name one out
   movement, or the derivation fails; the exits the table decided against the heading rule are listed. A route's
   own exit is resolved along its own linkSeq first. The movement of an exit is the approach's movement whose
   receiving link is '<sig>_to_<signal>' (internal) or that out link (boundary).
3. Evidence. Default: every static route whose linkSeq crosses the stop line (stop-line link followed by a
   connector leaving it) adds its raw relFlow to that connector (relFlow empty = 1, CLAUDE.md rule 4). Entry
   approaches: the named start routes are followed to their end; a route that ends before the stop line continues
   with the routing decision that re-routes the vehicle there (decision on the destLink at or after destPos, else
   the first decision along a unique downstream chain), with the route's relFlow share within its decision as the
   branch weight; a named peel-off connector ends the walk on its kept movement; a named excluded connector drops
   the branch (not an urban movement of this approach).
4. beta = the evidence share over the approach's matched exits. A movement that no evidence reaches is 0; its
   reason is recorded (no physical path, exit twin merged into its representative, own-leg U-turn dropped by the
   merge, on-ramp reached only through W_out, E_SC107 reached only through E_SC1005's connector, physical but no
   route). An approach whose stop line no route crosses keeps the config default shares of its physically
   existing movements (renormalised) and is listed. A phase whose every movement would be 0 keeps the config
   default share of its physically existing movements (starvation guard) and is listed; physically impossible
   movements never get a share. The phases here are the RUNTIME phases (2026-09-26): the declared phase, then the
   2026-08-28 phase correction (outputs/movement_phase_correction_20260828.json corrections, by merge family, as
   the adapter's apply_movement_phase_correction), then the pinned physical phase authority (by merge family, as
   physical_movement_routes.configure_phase_authority), without the own-leg U-turns the exit merge drops. The
   adapter still re-checks with the final phases that no phase other than the listed phases_without_flow carries
   only zero shares and that no share sits in a phase without native green (check_complete_beta_runtime), and
   refuses a tuning whose declaration or phase authority differs from this table's inputs.
Declarations (user decision 2026-09-26). The movements declared nonexistent come from the v3b declaration
(N31D/urban/movement_nonexistent_v3b_20260926.json, the candidates' urban.movements.nonexistent_declaration), not
from the older phase-correction section (a v2 reading). A declared movement that a physical connector reaches fails
the derivation (there is no exception list any more), and so does a 'corrected' movement that no physical connector
reaches or whose connector / runtime phase the phase authority does not name: SC7_E_to_N_SC11 and
SC7_E_SC16_to_N_SC11 (10332, relFlow 63 of 147 = 0.429, served by head 140101 = SC7 SG 1 = plan p4).
5. Every approach sums to 1 exactly (up to float rounding) before any runtime renormalisation, so the fold of
   non-kept on-ramp movements, the exit merge and the off-ramp direct renormalisation are no-ops; the adapter
   refuses otherwise (install_measured_turn_beta and the three consumers check it for this source).

Run from the worktree root:
  python -B scripts/derive_routing_beta_physical.py --out <file> [--check]
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from evaluation.controllers.beta_source import is_enabled_value  # noqa: E402  (the adapter's switch predicate)

N31D = "diagnostics/sdmpc_n31_20260924"
DEFAULTS = {
    "network": N31D + "/network/baseline_s31_v3bnc.inpx",
    "territory": "outputs/urban_player_territory_v2_20260907.json",
    "movements": N31D + "/scenario/config_n31_v2.base.json",
    "connector_map": "outputs/movement_connector_map_ver2_20260907.json",
    "merge_plan": "outputs/movement_merge_plan_20260824.json",
    "entry": N31D + "/beta/approach_entry_v3b2_20260925.json",
    "phase_correction": "outputs/movement_phase_correction_20260828.json",
    "nonexistent_declaration": N31D + "/urban/movement_nonexistent_v3b_20260926.json",
    "phase_authority": N31D + "/urban/physical_phase_authority_v3b_20260926.json",
    "out_links": "outputs/out_link_storage_ver2_20260909.json",
}
SCHEMA = "movement_beta_routing_physical/v1"
DECLARATION_SCHEMA = "movement-nonexistent-declaration/v1"
AUTHORITY_SCHEMA = "physical-phase-authority/v1"
DIRV = {"N": (0.0, 1.0), "S": (0.0, -1.0), "E": (1.0, 0.0), "W": (-1.0, 0.0)}
MAX_CHAIN = 6
MAX_WALK = 40


def rel_flow(raw: str | None) -> float:
    """relFlow "2 0:122" -> 122.0; empty -> 1.0 (CLAUDE.md rule 4, same as derive_routing_turn_beta._rel_flow)."""
    raw = (raw or "").strip()
    if not raw:
        return 1.0
    total = 0.0
    for token in raw.split():
        if ":" in token:
            try:
                total += float(token.rsplit(":", 1)[1])
            except ValueError:
                continue
    return total


class Network:
    def __init__(self, path: pathlib.Path):
        root = ET.parse(str(path)).getroot()
        self.links: dict[str, dict] = {}
        for el in root.iter("link"):
            no = el.get("no")
            lanes = el.find("lanes")
            rec = {"lanes": len(lanes.findall("lane")) if lanes is not None else 0,
                   "pts": [(float(p.get("x")), float(p.get("y"))) for p in el.iter("linkPolyPoint")]}
            f, t = el.find("fromLinkEndPt"), el.find("toLinkEndPt")
            if f is not None and t is not None:
                fl, fln = f.get("lane").split()
                tl, _tln = t.get("lane").split()
                rec.update(conn=True, frm=fl, frm_lane=int(fln), frm_pos=float(f.get("pos")), to=tl,
                           to_pos=float(t.get("pos")))
            else:
                rec["conn"] = False
            self.links[no] = rec
        self.out_conns: dict[str, list[str]] = collections.defaultdict(list)
        for c, rec in self.links.items():
            if rec["conn"]:
                self.out_conns[rec["frm"]].append(c)
        for v in self.out_conns.values():
            v.sort(key=int)
        self.decisions: dict[str, dict] = {}
        self.decisions_on: dict[str, list[dict]] = collections.defaultdict(list)
        for d in root.iter("vehicleRoutingDecisionStatic"):
            routes = []
            for r in d.iter("vehicleRouteStatic"):
                seq = [d.get("link")] + [e.get("key") for e in r.iter("intObjectRef")] + [r.get("destLink")]
                routes.append({"no": r.get("no"), "name": (r.get("name") or "").strip(), "rel": rel_flow(r.get("relFlow")),
                               "dest": r.get("destLink"), "dest_pos": float(r.get("destPos") or 0.0), "seq": seq})
            dec = {"no": d.get("no"), "link": d.get("link"), "pos": float(d.get("pos") or 0.0), "routes": routes}
            self.decisions[dec["no"]] = dec
            self.decisions_on[dec["link"]].append(dec)
        for v in self.decisions_on.values():
            v.sort(key=lambda x: x["pos"])

    def successors(self, element: str) -> list[str]:
        rec = self.links.get(element)
        if rec is None:
            return []
        return [rec["to"]] if rec["conn"] else list(self.out_conns.get(element, []))

    def link_heading(self, link: str) -> str | None:
        """Compass heading of a link: its first segment longer than 8 m (the pn_boundary_turns rule,
        scripts/derive_pn_boundary_turns.py Net.heading/compass, applied to every link passed)."""
        q = self.links.get(link, {}).get("pts") or []
        dx = dy = 0.0
        if len(q) >= 2:
            dx, dy = q[-1][0] - q[0][0], q[-1][1] - q[0][1]
            for j in range(1, len(q)):
                ddx, ddy = q[j][0] - q[0][0], q[j][1] - q[0][1]
                if math.hypot(ddx, ddy) > 8.0:
                    dx, dy = ddx, ddy
                    break
        n = math.hypot(dx, dy) or 1.0
        best, score = None, 0.0
        for d, (ux, uy) in DIRV.items():
            v = (dx * ux + dy * uy) / n
            if v > score:
                best, score = d, v
        return best if score > 0.45 else None


class Resolver:
    """Exit of a stop-line connector (physical) and of a route (its own linkSeq first).

    An internal exit is ('internal', signal); a boundary exit is ('boundary', headings, outs, terminal) where
    headings are the compass headings of the links passed after the connector, nearest first (a slip lane can start
    in one direction and join its boundary leg in another: SC107 10616 -> 381 heads E, then 10607 -> 1 heads S),
    outs are the '<sig>_<h>_out' names of the physical out-link table that list a link passed (the authority where
    it covers the signal), and terminal is the element where the walk ended (freeway link or network end)."""

    def __init__(self, net: Network, owners: dict[str, set[str]], freeway: set[str],
                 out_of_link: dict[str, set[str]] | None = None):
        self.net, self.owners, self.freeway = net, owners, freeway
        self.out_of_link = out_of_link or {}

    def _outs(self, sig: str, element: str) -> tuple:
        return tuple(sorted(o for o in self.out_of_link.get(element, ()) if o.startswith(sig + "_")))

    def _classify(self, sig: str, element: str):
        other = self.owners.get(element, set()) - {sig}
        if other:
            return [("internal", s) for s in sorted(other)]
        if element in self.freeway:
            return "boundary"
        return None

    def _heading(self, element: str) -> str | None:
        rec = self.net.links.get(element)
        if rec is None or rec["conn"]:
            return None
        return self.net.link_heading(element)

    def exits_of_connector(self, sig: str, conn: str) -> set[tuple]:
        """Every exit reachable from the connector before another signal's territory (all branches)."""
        found: set[tuple] = set()
        seen = {conn}
        frontier = [(self.net.links[conn]["to"], 0, (), self._outs(sig, conn))]
        while frontier:
            element, depth, heads, outs = frontier.pop()
            if element in seen:
                continue
            seen.add(element)
            h = self._heading(element)
            heads = heads + ((h,) if h and h not in heads else ())
            outs = tuple(sorted(set(outs) | set(self._outs(sig, element))))
            cls = self._classify(sig, element)
            if isinstance(cls, list):
                found.update(cls)
                continue
            nxt = self.net.successors(element)
            if cls == "boundary" or not nxt or depth >= MAX_WALK:
                found.add(("boundary", heads, outs, element))
                continue
            frontier.extend((n, depth + 1, heads, outs) for n in nxt)
        return found

    def exit_of_route(self, sig: str, seq: list[str], idx_conn: int) -> tuple | None:
        """Exit taken by a route that leaves the stop line by seq[idx_conn]: along its own linkSeq, then along a
        unique downstream chain; None if it branches before any owned link (fall back to the connector)."""
        heads: tuple = ()
        outs: set = set(self._outs(sig, seq[idx_conn]))
        for element in seq[idx_conn + 1:]:
            h = self._heading(element)
            heads = heads + ((h,) if h and h not in heads else ())
            outs |= set(self._outs(sig, element))
            cls = self._classify(sig, element)
            if isinstance(cls, list):
                return cls[0] if len(cls) == 1 else None
            if cls == "boundary":
                return ("boundary", heads, tuple(sorted(outs)), element)
        element, steps = seq[-1], 0
        while steps < MAX_WALK:
            nxt = self.net.successors(element)
            if not nxt:
                return ("boundary", heads, tuple(sorted(outs)), element)
            if len(nxt) > 1:
                return None
            element = nxt[0]
            steps += 1
            h = self._heading(element)
            heads = heads + ((h,) if h and h not in heads else ())
            outs |= set(self._outs(sig, element))
            cls = self._classify(sig, element)
            if isinstance(cls, list):
                return cls[0] if len(cls) == 1 else None
            if cls == "boundary":
                return ("boundary", heads, tuple(sorted(outs)), element)
        return None


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derive(args) -> tuple[dict, dict]:
    net_path = ROOT / args.network
    net = Network(net_path)
    terr = json.loads((ROOT / args.territory).read_text(encoding="utf-8"))["territory"]
    owners: dict[str, set[str]] = collections.defaultdict(set)
    for sig, legs in terr["urban"].items():
        for _leg, ids in legs.items():
            for link in ids:
                owners[str(link)].add(sig)
    freeway = {str(x) for v in terr["freeway"].values() for x in v}
    # Physical out-link table: '<sig>_<h>_out' -> the links (and connectors) that carry it. It names a boundary exit
    # wherever it lists a link the exit path passes; the heading rule only fills the signals it does not cover
    # (review 2026-09-26: SC104 10171 -> 65 (15 m, heads N) -> 10092 -> 1220061100 is the E out link, not N).
    out_doc = json.loads((ROOT / args.out_links).read_text(encoding="utf-8"))
    out_of_link: dict[str, set[str]] = collections.defaultdict(set)
    for name, row in out_doc["links"].items():
        for item in row.get("physical", []):
            link = str(item).split(":")[0]
            if link not in net.links:
                raise SystemExit("out-link table names %s (%s), absent from the pinned network" % (link, name))
            out_of_link[link].add(str(name))
    for link, names in out_of_link.items():
        if len(names) > 1:
            raise SystemExit("out-link table puts link %s in two out links: %s" % (link, sorted(names)))
    resolver = Resolver(net, owners, freeway, out_of_link)

    um = json.loads((ROOT / args.movements).read_text(encoding="utf-8-sig"))["config_overrides"]["network"]["urban_movements"]
    cmap = json.loads((ROOT / args.connector_map).read_text(encoding="utf-8"))["approaches"]
    rep = json.loads((ROOT / args.merge_plan).read_text(encoding="utf-8"))["leg_representative"]
    entry_doc = json.loads((ROOT / args.entry).read_text(encoding="utf-8"))
    if entry_doc.get("network_sha256") != sha256(net_path):
        raise SystemExit("entry table is pinned to another network: %s" % entry_doc.get("network_sha256"))
    entries = entry_doc["entries"]
    ramp_conns = {k: set(v) for k, v in entry_doc["ramp_connectors"].items() if k != "why"}
    # Route-choice corridors (urban.route_choice_corridor of the movements config) merge each 'remove' movement into
    # its 'keep' twin at runtime (route_choice_corridor.configure, incoming_turns): both leave by the same stop-line
    # connector and split only downstream. The keep carries the connector's share; the removed movement is 0.
    tuning = json.loads((ROOT / args.movements).read_text(encoding="utf-8-sig"))
    folded: dict[str, str] = {}
    corridor_files = []
    for rel in ((tuning.get("urban") or {}).get("route_choice_corridor") or {}).get("evidence_paths", []):
        corridor_files.append({"path": rel, "sha256": sha256(ROOT / rel)})
        for row in json.loads((ROOT / rel).read_text(encoding="utf-8")).get("incoming_turns", {}).values():
            folded[str(row["remove"])] = str(row["keep"])

    def leg_rep(sig: str, leg: str) -> str:
        return str(rep.get("%s|%s" % (sig, leg), leg))

    by_app: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    for name, spec in um.items():
        by_app[(str(spec["signal"]), str(spec["approach"]))].append(name)

    # ---- stop lines -------------------------------------------------------------------------------------------
    stoplines: dict[tuple[str, str], list[str]] = {}
    problems: list[str] = []
    for (sig, app) in by_app:
        key = "%s|%s" % (sig, app)
        if key in entries:
            stoplines[(sig, app)] = list(entries[key]["stoplines"])
            continue
        ck = "%s|%s" % (sig, leg_rep(sig, app))
        if ck not in cmap and key in cmap:
            ck = key
        if ck not in cmap or not cmap[ck]["stoplines"]:
            problems.append("no stop line for %s" % key)
            continue
        stoplines[(sig, app)] = list(cmap[ck]["stoplines"])
        # the connector map must agree with the pinned network
        for turn in cmap[ck]["turns"]:
            rec = net.links.get(turn["connector"])
            if rec is None or not rec["conn"] or rec["frm"] != turn["from_link"] or rec["to"] != turn["to_link"]:
                problems.append("connector map turn %s of %s differs from the network" % (turn["connector"], ck))
        mapped = {t["connector"] for t in cmap[ck]["turns"]}
        actual = {c for s in cmap[ck]["stoplines"] for c in net.out_conns.get(s, [])}
        if mapped != actual:
            problems.append("stop-line connectors of %s: map %s, network %s" % (ck, sorted(mapped), sorted(actual)))
    if problems:
        raise SystemExit("stop-line table is inconsistent:\n  " + "\n  ".join(problems))

    def out_names(sig: str, exit_: tuple) -> list[str]:
        """Candidate '<sig>_<h>_out' of a boundary exit, in order: the physical out-link table where it lists a link
        of the path (authoritative, one name), else '<sig>_<heading>_out' for every heading along the path."""
        _kind, heads, outs, _terminal = exit_
        if len(outs) > 1:
            raise SystemExit("boundary exit of %s passes two out links: %s" % (sig, outs))
        return list(outs) if outs else ["%s_%s_out" % (sig, h) for h in heads]

    def movement_of_exit(sig: str, app: str, exit_: tuple | None) -> str | None:
        """Internal: the movement received by '<sig>_to_<signal>'. Boundary: the first out_names candidate that a
        movement of the approach receives. A corridor-removed movement maps to its keep twin."""
        if exit_ is None:
            return None
        kind, target = exit_[0], exit_[1]
        wants = ["%s_to_%s" % (sig, target)] if kind == "internal" else out_names(sig, exit_)
        for want in wants:
            hits = [m for m in by_app[(sig, app)] if str(um[m].get("receiving_link")) == want]
            if len(hits) > 1:
                raise SystemExit("two movements of %s|%s receive %s: %s" % (sig, app, want, hits))
            if hits:
                return folded.get(hits[0], hits[0])
        return None

    # ---- declared nonexistent movements: the v3b declaration (urban.movements.nonexistent_declaration) ------------
    # The adapter's apply_nonexistent_movement_beta_zero reads the same file in the candidates. A declared movement
    # stays 0 and no physical connector may reach its exit; a 'corrected' movement (declared by the older v2 reading,
    # physical on v3b) is an ordinary relFlow movement and must be reached (checked after the evidence below).
    decl_doc = json.loads((ROOT / args.nonexistent_declaration).read_text(encoding="utf-8"))
    if decl_doc.get("schema") != DECLARATION_SCHEMA or decl_doc["network"]["sha256"] != sha256(net_path):
        raise SystemExit("the movement declaration is not a %s of the pinned network" % DECLARATION_SCHEMA)
    declared = {str(k): str(v) for k, v in (decl_doc.get("known_nonexistent_movements") or {}).items()
                if not str(k).startswith("_")}
    corrected = {str(k): v for k, v in (decl_doc.get("corrected") or {}).items() if not str(k).startswith("_")}
    if set(declared) & set(corrected) or (set(declared) | set(corrected)) - set(um):
        raise SystemExit("the movement declaration names a movement twice or an unknown movement")

    # ---- runtime phases ------------------------------------------------------------------------------------------
    # configure_runtime: apply_movement_phase_correction (2026-08-28 corrections, by exit-merge family; a stale or
    # split family is skipped), install_merged_movements (drops own-leg U-turns), then configure_phase_authority (the
    # pinned evidence rows, by merged name = merge family). The starvation guard and phases_without_flow use these.
    authority = json.loads((ROOT / args.phase_authority).read_text(encoding="utf-8-sig"))
    if authority.get("schema") != AUTHORITY_SCHEMA or authority["network"]["sha256"] != sha256(net_path):
        raise SystemExit("the phase authority is not a %s of the pinned network" % AUTHORITY_SCHEMA)
    mv_section = (tuning.get("urban") or {}).get("movements") or {}
    if not is_enabled_value(mv_section.get("merge_exits")) or mv_section.get("phase_correction_skip_added"):
        raise SystemExit("runtime phases assume urban.movements.merge_exits and no phase_correction_skip_added")
    rt_phase = {m: str(s.get("phase") or "") for m, s in um.items()}
    family: dict[str, list[str]] = collections.defaultdict(list)
    merged_name: dict[str, str] = {}
    merge_dropped: set[str] = set()
    for m, s in um.items():
        sig_, ext = str(s["signal"]), leg_rep(str(s["signal"]), str(s.get("exit", "")))
        if leg_rep(sig_, str(s["approach"])) == ext:
            merge_dropped.add(m)
            continue
        merged_name[m] = "%s_%s_to_%s" % (sig_, s["approach"], ext)
        family[merged_name[m]].append(m)
    phase_changes: dict[str, dict] = {}
    correction_on = is_enabled_value(mv_section.get("phase_correction"))
    if correction_on:
        pc = json.loads((ROOT / args.phase_correction).read_text(encoding="utf-8"))
        for name, row in sorted((pc.get("corrections") or {}).items()):
            if name not in um:
                continue
            node = str(um[name].get("intersection") or "")
            want_from, want_to = node + "_" + str(row.get("declared_phase") or ""), node + "_" + str(row.get("evidence_phase") or "")
            members = family.get(merged_name.get(name, ""), [name])
            if rt_phase[name] != want_from or any(rt_phase[o] != want_from for o in members):
                continue
            for o in members:
                rt_phase[o] = want_to
                phase_changes[o] = {"declared": str(um[o].get("phase") or ""), "runtime": want_to,
                                    "by": "phase_correction:" + name}
    for name, row in sorted(authority["by_movement"].items()):
        members = family.get(name)
        if not members or any(rt_phase[o] != row["expected_spec"]["phase"] for o in members):
            raise SystemExit("phase authority row %s does not match a runtime merge family in its expected phase" % name)
        for o in members:
            rt_phase[o] = row["new_phase"]
            phase_changes[o] = {"declared": str(um[o].get("phase") or ""), "runtime": row["new_phase"],
                                "by": "phase_authority:" + name}

    # ---- reviewed upstream branches ------------------------------------------------------------------------------
    # A turn can leave before the canonical stop line (upstream channelisation). The reviewed physical paths of the
    # configured urban.movements.physical_route_topology evidence (by_movement: path [link, connector, ...] + native
    # routes) name them, e.g. SC107 S 378 -> 10608 -> 383 (right turn before the left-only stop line 382), SC101
    # N_SC2005 314 -> 10504 -> 316, SC107 N_SC1 1220006803 -> 10597 (tunnel). Such a (link, connector) pair is a physical
    # turn of the declared movement's approach; a route's first stop-line or reviewed-branch crossing is its turn.
    branches: dict[tuple[str, str], dict[tuple[str, str], str]] = collections.defaultdict(dict)
    topo_rel = ((tuning.get("urban") or {}).get("movements") or {}).get("physical_route_topology")
    topology_file = None
    if topo_rel:
        topology_file = {"path": topo_rel, "sha256": sha256(ROOT / topo_rel)}
        topo = json.loads((ROOT / topo_rel).read_text(encoding="utf-8"))
        if topo["network"]["sha256"] != sha256(net_path):
            raise SystemExit("physical_route_topology is pinned to another network")
        for m, row in topo["by_movement"].items():
            spec = um.get(m)
            if spec is None:
                raise SystemExit("reviewed physical path names an unknown movement: " + m)
            key = (str(spec["signal"]), str(spec["approach"]))
            link, conn = str(row["path"][0]), str(row["path"][1])
            rec = net.links.get(conn)
            if rec is None or not rec["conn"] or rec["frm"] != link:
                raise SystemExit("reviewed physical path of %s differs from the network" % m)
            if key in stoplines and link not in stoplines[key]:
                branches[key][(link, conn)] = folded.get(m, m)

    # ---- physical reach per movement ---------------------------------------------------------------------------
    physical_conns: dict[str, list[str]] = collections.defaultdict(list)   # movement -> leaving connectors
    conn_exits: dict[tuple[str, str], dict[str, set]] = {}
    for (sig, app), lines in stoplines.items():
        table = {}
        for s_ in lines:
            for c in net.out_conns.get(s_, []):
                if net.links[c]["to"] in lines:
                    continue    # connector between two stop-line links of the same approach (SC11 E 10365)
                exits = resolver.exits_of_connector(sig, c)
                table[c] = exits
                for ex in exits:
                    m = movement_of_exit(sig, app, ex)
                    if m is not None and c not in physical_conns[m]:
                        physical_conns[m].append(c)
        for (_link, c), m in branches.get((sig, app), {}).items():
            if c not in physical_conns[m]:
                physical_conns[m].append(c)
        entry = entries.get("%s|%s" % (sig, app))
        if entry:
            for c, m in entry["peel_off"].items():
                if m not in um or (str(um[m]["signal"]), str(um[m]["approach"])) != (sig, app):
                    raise SystemExit("peel-off %s names %s outside %s|%s" % (c, m, sig, app))
                physical_conns[m].append(c)
        conn_exits[(sig, app)] = table

    # ---- one out link = one out movement ---------------------------------------------------------------------
    # Every boundary exit of a signal that ends on the same element must name the same out movement, and where the
    # out-link table decides, the record keeps what the heading rule alone would have said (review 2026-09-26).
    out_at_signal = collections.defaultdict(set)
    for m, spec in um.items():
        out_at_signal[str(spec["signal"])].add(str(spec.get("receiving_link")))
    by_terminal: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    table_decided: dict[tuple[str, str], dict] = {}
    for (sig, _app), table in conn_exits.items():
        for c, exits in table.items():
            for ex in exits:
                if ex[0] != "boundary":
                    continue
                name = next((n for n in out_names(sig, ex) if n in out_at_signal[sig]), None)
                by_terminal[(sig, ex[3])].add(name)
                heading_rule = next(("%s_%s_out" % (sig, h) for h in ex[1] if "%s_%s_out" % (sig, h) in out_at_signal[sig]), None)
                if ex[2] and heading_rule != name:
                    table_decided[(sig, c)] = {"signal": sig, "connector": c, "headings": list(ex[1]),
                                               "heading_rule": heading_rule, "out_link_table": name, "terminal": ex[3]}
    clashes = {"%s|%s" % k: sorted(map(str, v)) for k, v in by_terminal.items() if len(v) > 1}
    if clashes:
        raise SystemExit("one out link resolves to two out movements: %s" % clashes)
    boundary_table_decided = [table_decided[k] for k in sorted(table_decided, key=lambda k: (k[0], int(k[1])))]

    # ---- evidence -----------------------------------------------------------------------------------------------
    def crossing(seq: list[str], lines: set[str], extra: dict, start: int = 0):
        """Index of the route's first stop-line connector or reviewed upstream-branch connector, None if neither."""
        for i in range(start, len(seq) - 1):
            if (seq[i], seq[i + 1]) in extra:
                return i + 1
            if seq[i] in lines:
                rec = net.links.get(seq[i + 1])
                if rec and rec["conn"] and rec["frm"] == seq[i] and rec["to"] not in lines:
                    return i + 1
        return None

    def next_decision(route: dict):
        """The decision that re-routes a vehicle whose route ended: on the destLink at or after destPos, else the
        first one passed along a unique downstream chain (a link entered by a connector only counts decisions at or
        after the connector's landing position)."""
        on = [d for d in net.decisions_on.get(route["dest"], []) if d["pos"] >= route["dest_pos"] - 1e-9]
        if on:
            return on[0]
        element, steps, entry_pos = route["dest"], 0, 0.0
        while steps < MAX_WALK:
            nxt = net.successors(element)
            if len(nxt) != 1:
                return None
            prev, element = element, nxt[0]
            steps += 1
            prec = net.links.get(prev, {})
            entry_pos = prec.get("to_pos", 0.0) if prec.get("conn") else 0.0
            on = [d for d in net.decisions_on.get(element, []) if d["pos"] >= entry_pos - 1e-9]
            if on:
                return on[0]
        return None

    records = []
    beta: dict[str, float] = {}
    reasons: dict[str, str] = {}
    default_approaches: list[str] = []
    disagreements: list[dict] = []
    corrected_rows: dict[str, dict] = {}
    shadowed: list[dict] = []
    unmatched_total = 0.0
    for (sig, app), names in sorted(by_app.items()):
        key = "%s|%s" % (sig, app)
        lines = set(stoplines[(sig, app)])
        entry = entries.get(key)
        terminal: dict[str, float] = collections.defaultdict(float)     # connector -> weight
        route_exit: dict[tuple, float] = collections.defaultdict(float)  # (connector, movement) -> weight
        sources: dict[str, float] = collections.defaultdict(float)
        excluded: dict[str, float] = collections.defaultdict(float)
        unplaced: dict[str, float] = collections.defaultdict(float)

        def place(route, dec_no, w, start, depth):
            seq = route["seq"]
            peel = entry["peel_off"] if entry else {}
            drop = entry["excluded"] if entry else {}
            for i in range(start, len(seq)):
                if seq[i] in peel:
                    route_exit[(seq[i], peel[seq[i]])] += w
                    terminal[seq[i]] += w
                    return
                if seq[i] in drop:
                    excluded[seq[i]] += w
                    return
                if seq[i] in lines and i + 1 < len(seq):
                    rec = net.links.get(seq[i + 1])
                    if rec and rec["conn"] and rec["frm"] == seq[i] and rec["to"] not in lines:
                        c = seq[i + 1]
                        terminal[c] += w
                        route_exit[(c, movement_of_exit(sig, app, resolver.exit_of_route(sig, seq, i + 1)))] += w
                        return
            nd = next_decision(route) if depth < MAX_CHAIN else None
            if nd is None:
                unplaced["%s:%s" % (dec_no, route["no"])] += w
                return
            tot = sum(r["rel"] for r in nd["routes"])
            for r in nd["routes"]:
                if r["rel"] > 0.0 and tot > 0.0:
                    place(r, nd["no"], w * r["rel"] / tot, 0, depth + 1)

        if entry and entry["start"]:
            for token in entry["start"]:
                dno, _, rno = token.partition(":")
                dec = net.decisions[dno]
                routes = [r for r in dec["routes"] if not rno or r["no"] == rno]
                tot = sum(r["rel"] for r in dec["routes"]) if not rno else None
                for r in routes:
                    w = (r["rel"] / tot) if tot else 1.0
                    sources[token if rno else "%s:%s" % (dno, r["no"])] += w
                    place(r, dno, w, 0, 0)
        else:
            extra = branches.get((sig, app), {})
            crossing_routes = collections.defaultdict(list)     # decision -> [(route, crossing index)]
            for dec in net.decisions.values():
                for r in dec["routes"]:
                    if r["rel"] <= 0.0:
                        continue
                    k = crossing(r["seq"], lines, extra)
                    if k is not None:
                        crossing_routes[dec["no"]].append((r, k))
            # A single-route decision states no split: it is a catch-all that re-routes whatever arrives without a
            # route, a number relFlow does not give (its relFlow is a bare 1 next to real volumes, or next to another
            # decision's unit weights: SC103 N 1096 on the stop line under 1091's 1:1:1). Where a multi-route decision
            # also crosses the stop line, single-route decisions are not evidence for this approach (listed).
            multi = any(sum(1 for r in net.decisions[no]["routes"] if r["rel"] > 0.0) > 1 for no in crossing_routes)
            for no in sorted(crossing_routes, key=int):
                if multi and sum(1 for r in net.decisions[no]["routes"] if r["rel"] > 0.0) == 1:
                    shadowed.append({"approach": key, "decision": no,
                                     "weight": sum(r["rel"] for r, _ in crossing_routes[no])})
                    continue
                for r, k in crossing_routes[no]:
                    dec = net.decisions[no]
                    sources["%s:%s" % (dec["no"], r["no"])] += r["rel"]
                    c = r["seq"][k]
                    terminal[c] += r["rel"]
                    reviewed = extra.get((r["seq"][k - 1], c))
                    route_exit[(c, reviewed or movement_of_exit(sig, app, resolver.exit_of_route(sig, r["seq"], k)))] += r["rel"]

        # route exits that stayed ambiguous fall back to the connector's unique physical movement
        evidence: dict[str, float] = collections.defaultdict(float)
        unmatched: dict[str, float] = collections.defaultdict(float)
        declared_hits: dict[str, float] = collections.defaultdict(float)
        for (c, m), w in route_exit.items():
            if m is None:
                cands = {movement_of_exit(sig, app, ex) for ex in conn_exits[(sig, app)].get(c, set())} - {None}
                m = cands.pop() if len(cands) == 1 else None
            if m is not None and m in declared:
                declared_hits[m] += w
                m = None
            if m is None:
                unmatched[c] += w
            else:
                evidence[m] += w
        matched = math.fsum(evidence.values())
        unmatched_total += math.fsum(unmatched.values())

        values: dict[str, float] = {}
        why: dict[str, str] = {}
        if matched > 0.0:
            for m in names:
                values[m] = evidence.get(m, 0.0) / matched
        else:
            phys = [m for m in names if physical_conns.get(m)]
            tot = math.fsum(float(um[m].get("beta", 0.0)) for m in phys)
            for m in names:
                values[m] = (float(um[m].get("beta", 0.0)) / tot) if (m in phys and tot > 0.0) else 0.0
                if m in phys:
                    why[m] = "no_route_evidence_config_default"
            default_approaches.append(key)
        for m in names:
            if m in declared:
                values[m] = 0.0
                why[m] = "declared_nonexistent"
                if physical_conns.get(m) or declared_hits.get(m):
                    disagreements.append({"movement": m, "physical_connectors": physical_conns.get(m, []),
                                          "route_weight": declared_hits.get(m, 0.0), "declared": declared[m]})
            if m in corrected:
                corrected_rows[m] = {"physical_connectors": physical_conns.get(m, []),
                                     "route_weight": evidence.get(m, 0.0), "matched": matched}
        for m in names:
            if values[m] > 0.0 and m not in why:
                why[m] = "relflow"
        for m in names:
            if m in why:
                continue
            spec = um[m]
            ex = str(spec.get("exit", ""))
            twin = [o for o in names if o != m and values.get(o, 0.0) > 0.0
                    and leg_rep(sig, str(um[o].get("exit", ""))) == leg_rep(sig, ex)]
            if leg_rep(sig, ex) == leg_rep(sig, app):
                why[m] = "own_leg_u_turn"
            elif m in folded:
                why[m] = "corridor_fold_into:" + folded[m]
            elif twin:
                why[m] = "exit_twin_of:" + twin[0]
            elif spec.get("ramp"):
                via = [c for c, exits in conn_exits[(sig, app)].items()
                       if any(e[0] == "boundary" for e in exits)]
                why[m] = ("excluded_peel_off" if entry and set(entry["excluded"]) & ramp_conns.get(str(spec["ramp"]), set())
                          else "onramp_via_boundary_out" if via else "no_physical_path")
            elif physical_conns.get(m):
                why[m] = "physical_no_route_evidence"
            else:
                why[m] = "no_physical_path"
        beta.update(values)
        reasons.update(why)
        records.append({
            "signal": sig, "approach": app, "stoplines": sorted(lines),
            "reviewed_branches": {"%s>%s" % k: v for k, v in sorted(branches.get((sig, app), {}).items())},
            "entry": key if entry else None,
            "sources": {k: round(v, 6) for k, v in sorted(sources.items())},
            "connectors": {c: round(w, 6) for c, w in sorted(terminal.items(), key=lambda x: int(x[0]))},
            "matched": round(matched, 6),
            "unmatched": {c: round(w, 6) for c, w in sorted(unmatched.items())},
            "excluded": {c: round(w, 6) for c, w in sorted(excluded.items())},
            "unplaced": {c: round(w, 6) for c, w in sorted(unplaced.items())},
            "physical_connectors": {m: physical_conns.get(m, []) for m in names},
            "beta": {m: beta[m] for m in names},
            "reason": {m: reasons[m] for m in names},
        })

    # ---- starvation guard: a phase whose every movement is 0 keeps its physical movements' default share -------
    by_phase: dict[str, list[str]] = collections.defaultdict(list)
    for m in um:
        if rt_phase[m] and m not in merge_dropped:
            by_phase[rt_phase[m]].append(m)
    guarded: list[dict] = []
    dead_phases: list[str] = []
    for phase, ms in sorted(by_phase.items()):
        if max(beta[m] for m in ms) > 0.0:
            continue
        keep = [m for m in ms if reasons[m] == "physical_no_route_evidence"]
        if not keep:
            dead_phases.append(phase)
            continue
        for m in keep:
            guarded.append({"phase": phase, "movement": m, "config_default": float(um[m].get("beta", 0.0))})
            reasons[m] = "starvation_guard_config_default"
    if guarded:
        for (sig, app), names in by_app.items():
            keep = [m for m in names if reasons[m] == "starvation_guard_config_default"]
            if not keep:
                continue
            held = math.fsum(float(um[m].get("beta", 0.0)) for m in keep)
            scale = 1.0 - held
            for m in names:
                beta[m] = float(um[m].get("beta", 0.0)) if m in keep else beta[m] * scale
        for r in records:
            for m in r["beta"]:
                r["beta"][m] = beta[m]
                r["reason"][m] = reasons[m]

    # ---- declarations must agree with the physics (no exception list) -------------------------------------------
    if disagreements:
        raise SystemExit("declared-nonexistent movements that a physical connector or route reaches: %s"
                         % [(d["movement"], d["physical_connectors"], d["route_weight"]) for d in disagreements])
    corrected_record = []
    for m in sorted(corrected):
        row = corrected_rows.get(m) or {}
        auth = authority["by_movement"].get(merged_name.get(m, ""))
        want = [str(x) for x in (corrected[m].get("physical_path") or [])]
        if (not row.get("physical_connectors") or auth is None or len(want) != 3 or auth["path"] != want
                or want[1] not in row["physical_connectors"] or rt_phase[m] != auth["new_phase"]):
            raise SystemExit("corrected declaration %s: physical connectors %s, phase authority path %s, runtime phase "
                             "%s -- they must agree" % (m, row.get("physical_connectors"), auth and auth["path"], rt_phase[m]))
        corrected_record.append({"movement": m, "physical_connectors": row["physical_connectors"],
                                 "route_weight": row["route_weight"], "approach_matched_weight": row["matched"],
                                 "beta": beta[m], "reason": reasons[m], "declared_phase": str(um[m].get("phase") or ""),
                                 "runtime_phase": rt_phase[m]})

    # ---- exact approach sums ------------------------------------------------------------------------------------
    sums = {}
    for (sig, app), names in by_app.items():
        s = math.fsum(beta[m] for m in names)
        if abs(s - 1.0) > 1e-12:
            raise SystemExit("approach %s|%s sums to %r" % (sig, app, s))
        sums["%s|%s" % (sig, app)] = s

    doc = {
        "schema": SCHEMA,
        "generated": args.generated,
        "definition": ("beta = share of the static routes' relFlow over the physical exits of the approach's stop line "
                       "(0 without a physical path); see scripts/derive_routing_beta_physical.py. Every approach sums "
                       "to 1 before any runtime renormalisation."),
        "approach_sum": "exact",
        "inputs": {k: {"path": getattr(args, k), "sha256": sha256(ROOT / getattr(args, k))} for k in DEFAULTS},
        "route_choice_corridors": corridor_files,
        "physical_route_topology": topology_file,
        "movements": len(beta),
        "beta": {m: beta[m] for m in sorted(beta)},
        "reason": {m: reasons[m] for m in sorted(reasons)},
        "no_route_evidence_approaches": sorted(default_approaches),
        "starvation_guard": guarded,
        "phases_without_flow": dead_phases,
        "runtime_phases": {
            "phase_correction_applied": correction_on,
            "merge_exits": True,
            "merge_dropped_movements": len(merge_dropped),
            "changed": {m: phase_changes[m] for m in sorted(phase_changes)},
        },
        "declared_nonexistent": sorted(declared),
        "corrected_declarations": corrected_record,
        "boundary_exits_decided_by_out_link_table": boundary_table_decided,
        "single_route_decisions_ignored": shadowed,
        "unmatched_route_weight": unmatched_total,
        "approaches": records,
    }
    return doc, sums


def dumps(doc: dict) -> bytes:
    return (json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for k, v in DEFAULTS.items():
        ap.add_argument("--" + k.replace("_", "-"), dest=k, default=v)
    ap.add_argument("--generated", default="2026-09-25")
    ap.add_argument("--out", required=True)
    ap.add_argument("--check", action="store_true", help="compare with --out instead of writing it")
    args = ap.parse_args()
    doc, _sums = derive(args)
    data = dumps(doc)
    out = ROOT / args.out
    if args.check:
        if not out.is_file() or out.read_bytes() != data:
            raise SystemExit("%s differs from its derivation" % args.out)
    else:
        out.write_bytes(data)
    reasons = collections.Counter(doc["reason"].values())
    zero = collections.Counter(r.split(":")[0] for m, r in doc["reason"].items() if doc["beta"][m] == 0.0)
    print("movements %d, approaches %d, unmatched route weight %.3f" % (doc["movements"], len(doc["approaches"]),
                                                                       doc["unmatched_route_weight"]))
    print("reasons:", dict(sorted(reasons.items())))
    print("zero by reason:", dict(sorted(zero.items())))
    print("no-route-evidence approaches:", doc["no_route_evidence_approaches"])
    print("starvation guard:", doc["starvation_guard"])
    print("phases without flow:", doc["phases_without_flow"])
    print("single-route decisions ignored:", [(d["approach"], d["decision"], d["weight"])
                                              for d in doc["single_route_decisions_ignored"]])
    print("declared nonexistent:", doc["declared_nonexistent"])
    print("corrected declarations:", [(d["movement"], d["physical_connectors"], d["route_weight"], round(d["beta"], 6),
                                       d["declared_phase"], d["runtime_phase"]) for d in doc["corrected_declarations"]])
    print("runtime phase changes:", len(doc["runtime_phases"]["changed"]))
    print("ROUTING_BETA_PHYSICAL_OK sha256=" + hashlib.sha256(data).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
