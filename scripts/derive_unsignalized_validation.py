"""FZP validation table of the unsignalized-turn evidence (scripts/derive_unsignalized_turns.py), network v3b.

Validation only: no value of the model is taken from here. derive_unsignalized_turns.py includes a head-free
exclusive-lane turn only when this table shows that at most 5% of the vehicles that took its connector stopped on
the source link before it (over >= 100 observed transitions).

Source: the v3b no-control FZPs of seeds 31 / 41 / 37 (5 s frames), streamed once each (sha256 recorded).
Per vehicle, the observed element sequence (consecutive frames on one element merged: element, first / last
time, route, lane, count of frames below 5 km/h) is formed as in the 2026-09-25 extraction (scratchpad
urban-b1/fzp_paths.py, fzp_crossings.py, periodicity.py, turn_stops.py), which this script replaces.
Screened connectors: every connector whose source link is an urban approach link of territory v2 (the turns of the
signals); the 2026-09-25 table carried only the connectors named by its own output (circular), now a superset.
  stopped_before_share / _n   direct observed transitions source -> connector, or source -> the connector's
                              to-link when the connector frame was skipped (the connector is the unique one for that
                              pair, else the one leaving the vehicle's last lane on the source); t >= 900 s at the
                              element after the source; stopped = at least one frame below 5 km/h on the source.
  red_bin_share_c150 / _c160  crossing times (the element sequence with 5 s gaps filled by the unique shortest
                              connector/link path, depth <= 8; time of the first observed element after the crossing),
                              t >= 900 s, pooled over the seeds: share of the 10 s bins of t mod C below 20% of the mean.
  crossings                   the number of those crossing times.
Head-controlled references 10118 / 10371 / 10698: stopped 0.90-0.99, red bins 0.60-0.80.

Run from the worktree root (reads about 3.5 GB; a few minutes):
  python -B scripts/derive_unsignalized_validation.py --out <file> [--check]
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import io
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
N31D = "diagnostics/sdmpc_n31_20260924"
DEFAULTS = {
    "network": N31D + "/network/baseline_s31_v3bnc.inpx",
    "territory": "outputs/urban_player_territory_v2_20260907.json",
}
FZPS = {"31": "D:/VISSIM_runs/20260925_v3b/s31_v3bnc/run/vissim_eval/baseline_s31_v3bnc_001.fzp",
        "41": "D:/VISSIM_runs/20260925_v3b/s41_v3bnc/run/vissim_eval/baseline_s41_v3bnc_001.fzp",
        "37": "D:/VISSIM_runs/20260925_v3b/s37_v3bnc/run/vissim_eval/baseline_s37_v3bnc_001.fzp"}
SCHEMA = "unsignalized-turn-validation/v2"
T_FROM = 900.0
STOPPED_KPH = 5.0
FILL_DEPTH = 8
PERIODS = (150.0, 160.0)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def network(path: pathlib.Path):
    """Links in document order (the gap fill takes the first parent found, as the 2026-09-25 graph did)."""
    root = ET.parse(str(path)).getroot()
    links = {}
    for el in root.iter("link"):
        f, t = el.find("fromLinkEndPt"), el.find("toLinkEndPt")
        if f is not None and t is not None:
            fl, fln = f.get("lane").split()
            n = len(el.find("lanes").findall("lane"))
            links[el.get("no")] = {"conn": True, "frm": fl, "to": t.get("lane").split()[0],
                                   "lanes": list(range(int(fln), int(fln) + n))}
        else:
            links[el.get("no")] = {"conn": False}
    succ = collections.defaultdict(list)
    for x, r in links.items():
        if r["conn"]:
            succ[r["frm"]].append(x)
            succ[x] = [r["to"]]
    return links, succ


class Filler:
    def __init__(self, succ):
        self.succ, self.cache = succ, {}

    def __call__(self, a: str, b: str) -> list:
        key = (a, b)
        if key in self.cache:
            return self.cache[key]
        frontier, layer, found = {a: None}, [a], None
        for _ in range(FILL_DEPTH):
            nxt, hits = [], []
            for x in layer:
                for y in self.succ.get(x, []):
                    if y in frontier:
                        continue
                    frontier[y] = x
                    nxt.append(y)
                    if y == b:
                        hits.append(x)
            if hits:
                if len(hits) == 1:
                    path, cur = [], b
                    while cur is not None:
                        path.append(cur)
                        cur = frontier[cur]
                    found = list(reversed(path))[1:-1]
                break
            layer = nxt
        self.cache[key] = found or []
        return self.cache[key]


def vehicle_sequences(fzp: pathlib.Path, digest):
    """Yield every vehicle's merged element sequence [[elem, t0, t1, rd, rn, lane, stopped_frames], ...] once it
    leaves (not seen in a time step), then the rest at the end; every byte read feeds digest."""
    cur: dict = {}
    cur_tb, seen, t = None, set(), 0.0
    with io.open(fzp, "rb", buffering=1 << 22) as f:
        for raw in f:
            digest.update(raw)
            c0 = raw[:1]
            if not c0 or c0 not in b"0123456789":
                continue
            p = raw.split(b";", 13)
            tb = p[0]
            if tb != cur_tb:
                if cur_tb is not None:
                    for v in [v for v in cur if v not in seen]:
                        yield cur.pop(v)
                cur_tb, t, seen = tb, float(tb), set()
            veh = p[1]
            seen.add(veh)
            elem = p[2].decode()
            sp = float(p[6])
            seq = cur.get(veh)
            if seq is None:
                seq = cur[veh] = []
            if seq and seq[-1][0] == elem:
                last = seq[-1]
                last[2], last[3], last[4], last[5] = t, p[11].decode(), p[12].decode(), int(p[3])
                last[6] += 1 if sp < STOPPED_KPH else 0
            else:
                seq.append([elem, t, t, p[11].decode(), p[12].decode(), int(p[3]), 1 if sp < STOPPED_KPH else 0])
    for seq in cur.values():
        yield seq


def derive(args) -> dict:
    net_path = ROOT / args.network
    links, succ = network(net_path)
    terr = json.loads((ROOT / args.territory).read_text(encoding="utf-8"))["territory"]
    approach_links = {str(x) for legs in terr["urban"].values() for ids in legs.values() for x in ids}
    screened = sorted((c for c, r in links.items() if r["conn"] and r["frm"] in approach_links), key=int)
    screened_set = set(screened)
    by_pair: dict[tuple, list] = collections.defaultdict(list)
    for c in screened:
        by_pair[(links[c]["frm"], c)].append(c)
        by_pair[(links[c]["frm"], links[c]["to"])].append(c)
    fill = Filler(succ)
    times: dict[str, list] = collections.defaultdict(list)
    cnt, stp = collections.Counter(), collections.Counter()
    sources = {}
    for seed, rel in sorted(FZPS.items(), key=lambda x: int(x[0])):
        path = pathlib.Path(rel)
        digest = hashlib.sha256()
        vehicles = 0
        for seq in vehicle_sequences(path, digest):
            vehicles += 1
            # stopped before the connector: direct observed transitions
            for i in range(len(seq) - 1):
                cands = by_pair.get((seq[i][0], seq[i + 1][0]))
                if not cands or seq[i + 1][1] < T_FROM:
                    continue
                if len(cands) > 1:
                    cands = [c for c in cands if seq[i][5] in links[c]["lanes"]]
                    if len(cands) != 1:
                        continue
                cnt[cands[0]] += 1
                stp[cands[0]] += 1 if seq[i][6] > 0 else 0
            # crossing times on the gap-filled sequence
            elems, tt = [], []
            for i, e in enumerate(seq):
                if i and e[0] not in succ.get(seq[i - 1][0], []):
                    for g in fill(seq[i - 1][0], e[0]):
                        elems.append(g)
                        tt.append(e[1])
                elems.append(e[0])
                tt.append(e[1])
            for j in range(len(elems) - 1):
                c = elems[j + 1]
                if c in screened_set and links[c]["frm"] == elems[j]:
                    times[c].append(tt[j + 1])
        sources[seed] = {"path": rel, "bytes": path.stat().st_size, "sha256": digest.hexdigest(), "vehicles": vehicles}
        print("seed %s: %d vehicles" % (seed, vehicles), flush=True)
    conn = {}
    for c in screened:
        ts = [t for t in times.get(c, []) if t >= T_FROM]
        red = {}
        for period in PERIODS:
            h = [0] * int(period // 10)
            for t in ts:
                h[int((t % period) // 10)] += 1
            mean = sum(h) / len(h)
            red[int(period)] = round(sum(1 for x in h if x < 0.2 * mean) / len(h), 2) if mean else None
        conn[c] = {"stopped_before_share": round(stp[c] / cnt[c], 4) if cnt[c] else None,
                   "stopped_before_n": cnt[c],
                   "red_bin_share_c150": red[150], "red_bin_share_c160": red[160], "crossings": len(ts)}
    return {
        "schema": SCHEMA,
        "generated": args.generated,
        "what": ("v3b no-control FZP (5 s frames, t >= 900 s, seeds 31/41/37 pooled), every connector leaving an urban "
                 "approach link of territory v2. stopped_before_share: share of vehicles with a frame below 5 km/h on "
                 "the source link before taking the connector (stopped_before_n direct observed transitions). "
                 "red_bin_share_c<C>: share of 10 s bins of crossing time mod C below 20% of the mean count (5 s gaps "
                 "filled on the network graph). Validation only: no value of the model is taken from here."),
        "generator": "scripts/derive_unsignalized_validation.py",
        "sources": sources,
        "inputs": {k: {"path": getattr(args, k), "sha256": sha256(ROOT / getattr(args, k))} for k in DEFAULTS},
        "network_sha256": sha256(net_path),
        "connectors": conn,
    }


def dumps(doc: dict) -> bytes:
    return (json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for k, v in DEFAULTS.items():
        ap.add_argument("--" + k, dest=k, default=v)
    ap.add_argument("--generated", default="2026-09-26")
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
    print("screened connectors %d, with transitions %d" % (len(doc["connectors"]),
                                                           sum(1 for r in doc["connectors"].values() if r["stopped_before_n"])))
    print("UNSIGNALIZED_VALIDATION_OK sha256=" + hashlib.sha256(data).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
