"""Shared readers of the urban batch-2 evidence generators (network v3b; user decisions 2026-09-27/29).

Used by scripts/derive_head_saturation.py (U4), scripts/derive_shared_head_groups.py (U5),
scripts/derive_ramp_diverge.py (U6), scripts/derive_phase_authority_shared_lane_v3b.py (Q2) and
scripts/check_urban_batch2_evidence.py (cross-consistency). Nothing here imports the runtime (evaluation/**) or writes a
file; every reader is a pure function of its inputs:

  sha256_file / file_pin     sha256 (and size) of a file; a pin is {"path": <repo-relative or absolute posix>, "sha256"}
  Network                    one parse of an .inpx: links (length, lanes, connector ends), signal heads by lane, signal
                             controllers, static routing decisions/routes, a signature of heads/connectors/controllers/
                             static routes (the part of a network the evidence depends on)
  sig_windows                green / amber windows of fixed-time controllers from the .sig files an .inpx points to
                             (VISSIG Red-Green-Amber: green until the red command minus the fixed amber; cycle second =
                             (t - offset) mod C), 0..T_END; lsa_windows reads a run's signal-change protocol (.lsa) for
                             the same SCs to verify them
  stream_fzp                 one streaming pass over a vehicle record (.fzp, 5 s frames) keeping the rows of a set of
                             links; the file's sha256 is computed in the same pass
The NC runs of network v3b (the U4 fit seeds 31/41/43/47/53) and R-obs-b (v3b NC, obs150 collection, the same
trajectory as seed 31) are read only.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

N31 = "diagnostics/sdmpc_n31_20260924"
NETWORK = N31 + "/network/baseline_s31_v3bnc.inpx"
PLAN = "diagnostics/controller_confidence_20260913/local_native_clock_v2/native_clock_plan_local.json"
NC_SEEDS = (31, 41, 43, 47, 53)
NC_ROOT = "D:/VISSIM_runs/20260925_v3b"
ROBS = "D:/VISSIM_runs/20260925_sdmpc31_v3b/sdmpc31_v3b_nc_s31b"
T_END = 9000.0
FRAME_SEC = 5.0
FRAME_OFFSET = 0.1


def nc_fzp(seed: int) -> str:
    return "%s/s%d_v3bnc/run/vissim_eval/baseline_s%d_v3bnc_001.fzp" % (NC_ROOT, seed, seed)


def nc_inpx(seed: int) -> str:
    return "%s/s%d_v3bnc/prepared/network/baseline_s%d_v3bnc.inpx" % (NC_ROOT, seed, seed)


def robs_file(suffix: str) -> str:
    return "%s/vissim_eval/sdmpc31_sdmpc31_v3b_nc_s31b_001.%s" % (ROBS, suffix)


def sha256_file(path, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def posix(path) -> str:
    return str(path).replace("\\", "/")


def file_pin(root: Path, rel: str, *, size: bool = False) -> dict:
    """{"path", "sha256"[, "bytes"]} of a repo-relative (or absolute) file."""
    p = Path(rel) if Path(rel).is_absolute() else root / rel
    out = {"path": posix(rel), "sha256": sha256_file(p)}
    if size:
        out["bytes"] = p.stat().st_size
    return out


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def dumps(doc) -> bytes:
    return (json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def rnd(x, n=6):
    return None if x is None else round(float(x), n)


def rel_flow(raw) -> float:
    """relFlow "2 0:122" -> 122.0; empty -> 1.0 (CLAUDE.md rule 4; the rule of scripts/derive_routing_beta_physical.py)."""
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


def poly_length(node) -> float:
    pts = [(float(p.get("x")), float(p.get("y"))) for p in node.findall("./geometry/linkPolyPts/linkPolyPoint")]
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


class Network:
    """One parse of an .inpx (read only)."""

    def __init__(self, path):
        self.path = Path(path)
        self.root = ET.parse(str(path)).getroot()
        self.links, self.conn = {}, {}
        self.into, self.outof = defaultdict(list), defaultdict(list)
        for node in self.root.findall("./links/link"):
            no = node.get("no")
            lanes = len(node.findall("./lanes/lane"))
            self.links[no] = {"node": node, "lanes": lanes, "length": poly_length(node)}
            a, b = node.find("fromLinkEndPt"), node.find("toLinkEndPt")
            if a is None or b is None:
                continue
            fl, fla = a.get("lane").split()
            tl, tla = b.get("lane").split()
            c = {"no": no, "from": fl, "from_lane": int(fla), "from_pos": float(a.get("pos")), "to": tl,
                 "to_lane": int(tla), "to_pos": float(b.get("pos")), "lanes": lanes, "length": self.links[no]["length"]}
            self.conn[no] = c
            self.into[tl].append(no)
            self.outof[fl].append(no)
        self.heads, self.heads_by_lane = {}, defaultdict(list)
        for h in self.root.findall("./signalHeads/signalHead"):
            link, lane = h.get("lane").split()
            sc, sg = h.get("sg").split()
            row = {"head_id": h.get("no"), "link": link, "lane": int(lane), "position_m": float(h.get("pos")),
                   "sc": sc, "sg": sg, "all_vehicle_types": h.get("allVehTypes") == "true",
                   "compliance": float(h.get("complRate", 1))}
            self.heads[h.get("no")] = row
            self.heads_by_lane[link, int(lane)].append(row)
        self.controllers = {c.get("no"): c for c in self.root.findall("./signalControllers/signalController")}
        self.routes = {}
        self.decisions = {}
        for d in self.root.findall("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic"):
            self.decisions[d.get("no")] = d
            for r in d.findall("./vehRoutSta/vehicleRouteStatic"):
                seq = [d.get("link")] + [x.get("key") for x in r.findall("./linkSeq/intObjectRef")] + [r.get("destLink")]
                self.routes["%s:%s" % (d.get("no"), r.get("no"))] = {"path": seq, "decision": d, "route": r}

    def signature(self) -> dict:
        """sha256[:16] of the parts the evidence reads: heads, connectors (ends, lanes), controllers (type, program,
        supply file, offset), static routing decisions and routes (link, pos, relFlow, link sequence)."""
        heads = sorted((h.get("no"), h.get("lane"), h.get("pos"), h.get("sg"), h.get("allVehTypes"), h.get("complRate"))
                       for h in self.root.findall("./signalHeads/signalHead"))
        conns = sorted((c["no"], c["from"], c["from_lane"], c["from_pos"], c["to"], c["to_lane"], c["to_pos"], c["lanes"])
                       for c in self.conn.values())
        scs = sorted((c.get("no"), c.get("type"), c.get("supplyFile2"), c.get("progNo"), c.get("offset"))
                     for c in self.controllers.values())
        routes = sorted((k, r["decision"].get("link"), r["decision"].get("pos"), r["route"].get("relFlow"), tuple(r["path"]))
                        for k, r in self.routes.items())
        h = lambda x: hashlib.sha256(json.dumps(x).encode()).hexdigest()[:16]  # noqa: E731
        return {"heads": h(heads), "connectors": h(conns), "signal_controllers": h(scs), "static_routes": h(routes),
                "n_heads": len(heads), "n_connectors": len(conns), "n_static_routes": len(routes)}


# ------------------------------------------------------------------------------------------------ signal windows
def _merge(iv):
    res = []
    for a, b in sorted(iv):
        if res and a <= res[-1][1] + 1e-9:
            res[-1][1] = max(res[-1][1], b)
        else:
            res.append([a, b])
    return res


def sig_windows(net: Network, scs, t_end: float = T_END):
    """{"<sc>-<sg>": {"green": [[a, b], ...], "amber": [...]}} and per-SC meta, from the .sig files next to the .inpx."""
    out, meta = {}, {}
    for sc in sorted(scs, key=int):
        node = net.controllers[sc]
        if node.get("type") != "FIXEDTIME":
            raise ValueError("SC%s is %s, not FIXEDTIME" % (sc, node.get("type")))
        f = net.path.parent / node.get("supplyFile2").replace("#data#", "")
        prog_no = node.get("progNo")
        root = ET.parse(str(f)).getroot()
        seqs = {s.get("id"): s.get("name") for s in root.findall("./signalsequences/signalsequence")}
        prog = next(p for p in root.findall("./progs/prog") if p.get("id") == prog_no)
        C = float(prog.get("cycletime")) / 1000.0
        off = float(prog.get("offset")) / 1000.0 + float(node.get("offset") or 0.0)
        meta[sc] = {"sig": f.name, "sig_sha256": sha256_file(f), "prog": prog_no, "cycle_sec": C, "offset_sec": off}
        for sg in prog.findall("./sgs/sg"):
            sid = sg.get("sg_id")
            name = seqs.get(sg.get("signal_sequence"))
            cmds = sorted((float(c.get("begin")) / 1000.0, c.get("display")) for c in sg.findall("./cmds/cmd"))
            amber = sum(float(x.get("duration")) / 1000.0 for x in sg.findall("./fixedstates/fixedstate")
                        if x.get("display") == "4")
            cyc_green, cyc_amber = [], []
            if name != "Permanent Red":
                n = len(cmds)
                for i, (b, d) in enumerate(cmds):
                    nb, nd = cmds[(i + 1) % n]
                    end = nb if i + 1 < n else nb + C
                    if d == "3":
                        g_end = end - (amber if nd == "1" else 0.0)
                        cyc_green.append((b, g_end))
                        if nd == "1" and amber > 0:
                            cyc_amber.append((g_end, end))
            greens, ambers = [], []
            for k in range(int((0.0 - off) // C) - 1, int((t_end - off) // C) + 2):
                base = off + k * C
                greens += [(base + a, base + b) for a, b in cyc_green]
                ambers += [(base + a, base + b) for a, b in cyc_amber]
            clip = lambda iv: sorted((max(a, 0.0), min(b, t_end)) for a, b in iv if b > 0.0 and a < t_end)  # noqa: E731
            out["%s-%s" % (sc, sid)] = {"green": _merge(clip(greens)), "amber": _merge(clip(ambers)),
                                        "cycle_green_sec": sum(b - a for a, b in cyc_green), "sequence": name}
    return out, meta


def lsa_windows(path, scs, t_end: float = T_END):
    """Green / amber windows of the SCs from a run's .lsa (Red-Green-Amber sequence; t <= 1 rows are initial states)."""
    ev = defaultdict(list)
    for line in open(path, encoding="latin-1"):
        parts = [p.strip() for p in line.split(";")]
        if len(parts) < 7 or not re.match(r"^\d+(\.\d+)?$", parts[0]):
            continue
        t, sc, sg, state, dur = float(parts[0]), parts[2], parts[3], parts[4], float(parts[5])
        if sc in scs:
            ev["%s-%s" % (sc, sg)].append((t, state, dur))
    out = {}
    before = {"green": "red", "amber": "green", "red": "amber"}
    for key, rows in ev.items():
        rows.sort(key=lambda r: r[0])
        greens, ambers = [], []
        last_t, last_state = None, None
        for t, state, dur in rows:
            if t <= 1.0 and last_state is None:
                last_t, last_state = max(0.0, t - dur), state
                continue
            prev = last_state if last_state is not None else before.get(state)
            start = last_t if last_state is not None else max(0.0, t - dur)
            if prev == "green":
                greens.append((start, t))
            elif prev == "amber":
                ambers.append((start, t))
            last_t, last_state = t, state
        if last_state == "green":
            greens.append((last_t, t_end))
        elif last_state == "amber":
            ambers.append((last_t, t_end))
        out[key] = {"green": _merge([(a, min(b, t_end)) for a, b in greens if a < t_end]),
                    "amber": _merge([(a, min(b, t_end)) for a, b in ambers if a < t_end])}
    return out


def compare_windows(a, b, keys, t_from: float = 5.0):
    """Keys whose green interval lists differ by more than 0.05 s on [t_from, T_END]."""
    def cut(iv):
        return [(max(x, t_from), y) for x, y in iv if y > t_from]
    bad = []
    for key in sorted(keys):
        ga, gb = cut(a.get(key, {}).get("green", [])), cut(b.get(key, {}).get("green", []))
        if len(ga) != len(gb) or any(abs(x[0] - y[0]) > 0.05 or abs(x[1] - y[1]) > 0.05 for x, y in zip(ga, gb)):
            bad.append(key)
    return bad


def overlap(windows, a: float, b: float) -> float:
    return sum(max(0.0, min(y, b) - max(x, a)) for x, y in windows)


# ------------------------------------------------------------------------------------------------ vehicle records
FZP_COLUMNS = ("SIMSEC", "NO", "LANE\\LINK\\NO", "LANE\\INDEX", "POS", "SPEED", "LENGTH", "NEXTLINK\\NO",
               "INTERACTTARGTYPE", "ROUTDECNO", "ROUTENO")


def stream_fzp(path, keep_links):
    """One pass over an .fzp: the rows on <keep_links> as parallel lists (k = frame index, t = 5 k + 0.1) and the file's
    sha256 / size / row counts. Interaction target types are coded per file (itt_names)."""
    import numpy as np
    keep = {str(x).encode() for x in keep_links}
    cols = {k: [] for k in ("k", "veh", "link", "lane", "pos", "speed", "length", "next", "itt", "rdec", "route")}
    itt_codes = {b"": 0}
    h = hashlib.sha256()
    n = kept = size = 0
    idx = None
    with open(path, "rb", buffering=16 * 1024 * 1024) as fh:
        for line in fh:
            h.update(line)
            size += len(line)
            if idx is None:
                if line.startswith(b"$VEHICLE:"):
                    names = line[len(b"$VEHICLE:"):].strip().decode("latin-1").split(";")
                    idx = [names.index(c) for c in FZP_COLUMNS]
                continue
            if not line or line[0] in (42, 36, 13, 10):
                continue
            n += 1
            p = line.split(b";")
            if p[idx[2]] not in keep:
                continue
            t = float(p[idx[0]])
            k = int(round((t - FRAME_OFFSET) / FRAME_SEC))
            if abs(t - (FRAME_SEC * k + FRAME_OFFSET)) > 1e-6:
                raise ValueError("unexpected frame time %r in %s" % (t, path))
            cols["k"].append(k)
            cols["veh"].append(int(p[idx[1]]))
            cols["link"].append(int(p[idx[2]]))
            cols["lane"].append(int(p[idx[3]]))
            cols["pos"].append(float(p[idx[4]]))
            cols["speed"].append(float(p[idx[5]]))
            cols["length"].append(float(p[idx[6]]))
            cols["next"].append(int(p[idx[7]]) if p[idx[7]] else 0)
            cols["itt"].append(itt_codes.setdefault(p[idx[8]], len(itt_codes)))
            cols["rdec"].append(int(p[idx[9]]) if p[idx[9]] else 0)
            cols["route"].append(int(p[idx[10]]) if p[idx[10]] else 0)
            kept += 1
    if idx is None:
        raise ValueError("no $VEHICLE header in %s" % path)
    arr = {"k": np.asarray(cols["k"], dtype=np.int32), "veh": np.asarray(cols["veh"], dtype=np.int32),
           "link": np.asarray(cols["link"], dtype=np.int64), "lane": np.asarray(cols["lane"], dtype=np.int16),
           "pos": np.asarray(cols["pos"], dtype=np.float64), "speed": np.asarray(cols["speed"], dtype=np.float64),
           "length": np.asarray(cols["length"], dtype=np.float64), "next": np.asarray(cols["next"], dtype=np.int64),
           "itt": np.asarray(cols["itt"], dtype=np.int16), "rdec": np.asarray(cols["rdec"], dtype=np.int32),
           "route": np.asarray(cols["route"], dtype=np.int32)}
    meta = {"path": posix(path), "sha256": h.hexdigest(), "bytes": size, "rows_total": n, "rows_kept": kept,
            "itt_names": {v: k.decode("latin-1") for k, v in itt_codes.items()}}
    return arr, meta


def t_of(k) -> float:
    return FRAME_SEC * k + FRAME_OFFSET


def head_detectors(root: Path) -> dict:
    """obs150 head detectors (dcm number -> head id) of the pinned detector table (role 'head')."""
    heads = {}
    with open(root / N31 / "obs150/obs150_detectors_v2.csv", newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["role"] == "head":
                heads[r["dcm_no"]] = r["ref"].split("|")[0]
    return heads


def mer_head_entries(path, dcm_to_head):
    """(head id, entry time, vehicle no) of every head-detector entry of a .mer, and the file's sha256 / size."""
    keys = {k.encode(): v for k, v in dcm_to_head.items()}
    rows = []
    h = hashlib.sha256()
    size = 0
    with open(path, "rb", buffering=16 * 1024 * 1024) as fh:
        for line in fh:
            h.update(line)
            size += len(line)
            p = line.split(b";")
            if len(p) < 12:
                continue
            head = keys.get(p[0].strip())
            if head is None:
                continue
            t = float(p[1])
            if t < 0:
                continue
            rows.append((head, t, int(p[3])))
    return rows, {"path": posix(path), "sha256": h.hexdigest(), "bytes": size, "head_entries": len(rows)}
