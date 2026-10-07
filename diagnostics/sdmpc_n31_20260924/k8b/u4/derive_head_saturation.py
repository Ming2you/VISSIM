"""U4 saturation table v1: per physical head group, the measured queue-discharge (saturation) flow per lane (network v3b).

Urban batch 2, C3 = U4 + U5 + U6 (user decisions 2026-09-27/28/29): the 206.53 veh/h-green/lane normalisation
(vissim_stackelberg_adapter.install_movement_capacity_by_lanes) is replaced by a pinned per-head-group saturation table.
The groups are the rows of the U5 shared head-group contract v1 (--groups, pinned here by sha256): the 105 observation
groups of signal_head_observation.physical_groups, the 3 controlled groups whose lanes carry an upstream head of another
controller (1220011001|p1, 1220013600|p3, 1220013600|p4) and the 66 groups of the native signals the plant models
(key <stopline_link>|nSG<sg>; user decision Q1 2026-09-29: U4 and U5 apply to them). Group key = contract group_id.

Measurement (the method of the batch-2 U4 draft, B/u4/{trees,analyze_run,build_table}.py, ported unchanged; it
reproduces the draft's 105 observation-group rows, see the stage-3 report):
  approach trees      per head, the stop lane before the head, its in-connector lanes and the upstream link lanes
                      heading into them (NextLink, or the only connector left ahead), within D_MAX of the head; a lane
                      with a pre-head exit excludes vehicles bound for it. A vehicle belongs to the head with the
                      smallest positive distance.
  crossings           vehicle-centric look-ahead between consecutive 5 s frames (stop link beyond the head, an
                      after-head out-connector, its to-link, a link reachable downstream; serial heads)
  Q0 / saturated bins the queue standing at green start + 1 s (front within FRONT_M of the head, <= V_Q_KMH, gaps
                      <= GAP_M); 5 s bins inside the green that end with a head-bound Q0 vehicle not yet across
  primary rate        the unimpeded bins starting >= T_SU s after green start (walk stops at the first impeded bin:
                      0 passages, or the front head-bound Q0 vehicle standing < V_STAND at the bin start); rate =
                      3600 x passages / bin seconds, pooled over the group's heads (per lane) and the five NC fit seeds
  status              measured if bins >= MIN_BINS, cycles >= MIN_CYCLES, seeds with samples >= MIN_SEEDS; else
                      default (DEFAULT_VEH_H_LANE); serial_first_head for the downstream head of a serial double stop
                      line in the SAME signal group as its first head (it never queues on its own: 1210012001|p3, head
                      30601 SC11 SG 6 after 30603/30604 SG 6 of 1220012001|p3, the native_input 1093 pre-head pair):
                      its value is the first head group's
  s31 exact           R-obs-b (.mer head detectors, the seed-31 trajectory) exact passage headways, record only
Lane files (stage 4, BATCH2_PLAN 4.1-1 [C-8]): the two movement-lane files of install_movement_capacity_by_lanes are
pinned (lane_files); the U4 installer counts the lanes of the movements outside every group through these pins only.
Green windows: the native fixed-time programs (.sig) the pinned .inpx names (NC runs are native), checked against the
R-obs-b signal-change protocol (.lsa). Record only (no value depends on it): flags, per-seed spread, validation.
Nothing here reads a closed-loop run or the plant; the draft's plant / collector / closed-loop columns are not carried.

Run from the worktree root (reads the NC runs and R-obs-b under D:/VISSIM_runs, read only; ~5 min):
  python -B scripts/derive_head_saturation.py --out <file> [--check]
"""
from __future__ import annotations

import argparse
import hashlib
import math
import pathlib
import statistics as st
import sys
from bisect import bisect_left, bisect_right
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import urban_b2_evidence as E  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCHEMA = "u4-saturation-table/v1"
CONTRACT_SCHEMA = "shared-head-discharge-contract/v1"
DEFAULTS = {"groups": E.N31 + "/urban/shared_head_groups_v3b_20260929.json",
            "prehead": E.N31 + "/scenario/native_input_1093_prehead_ver2_9b761e.json",
            # the lane counts of the movements outside every head group (the files install_movement_capacity_by_lanes
            # reads); the U4 installer reads them through these pins only (BATCH2_PLAN 4.1-1 [C-8], stage 4)
            "lanes_internal": "outputs/movement_lanes_core17legs4b_20260821.json",
            "lanes_perimeter": "outputs/movement_lanes_perimeter_20260824.json"}
# approach trees (trees.py)
D_MAX = 300.0
DOWN_MAX = 250.0
MAX_DEPTH = 6
# crossings / queue (analyze_run.py)
FRONT_M = 10.0
V_Q_KMH = 10.0
GAP_M = 10.0
T_FROM = 900.0
T_END = 9000.0
HEAD_TOL = 0.5
REACH_M = 100.0
# table (build_table.py)
T_SU = 5.0
V_STAND = 5.0
MIN_BINS = 24
MIN_CYCLES = 8
MIN_SEEDS = 3
SEED_MIN_BINS = 6
H_BLOCK = 6.0
DEFAULT_VEH_H_LANE = 1850.0
SERIAL_DOWNSTREAM = {"1210012001|p3": "1220012001|p3"}


# ================================================================================================ approach trees
def build_trees(net, groups):
    """trees.py on the contract's group heads: per head the approach elements, the downstream reach of every stop
    link, the kept links and the stop-link info the crossing rules read."""
    heads = [h for g in groups for h in g["heads"]]
    stop_links = sorted({h["link"] for h in heads}, key=int)
    elig = defaultdict(set)
    for h in heads:
        elig[h["link"]].add(h["lane"])
    any_head = defaultdict(lambda: defaultdict(list))
    for x in net.heads.values():
        any_head[x["link"]][x["lane"]].append(x["position_m"])
    trees, keep, down = {}, set(), {}
    for h in heads:
        L, l, p = h["link"], h["lane"], h["position_m"]
        pre = sorted((net.conn[c]["from_pos"], c) for c in net.outof.get(L, [])
                     if net.conn[c]["from_lane"] <= l < net.conn[c]["from_lane"] + net.conn[c]["lanes"]
                     and net.conn[c]["from_pos"] < p - 0.5)
        elems = [{"link": L, "lane": l, "O": p, "max_x": p, "kind": "stop", "via": None, "depth": 0,
                  "pre_head_exits": [[fp, c] for fp, c in pre]}]
        stack = [(L, l, p, 0)]
        seen = {(L, l)}
        while stack:
            Ee, lane_E, O_E, depth = stack.pop()
            if depth >= MAX_DEPTH:
                continue
            for c in net.into.get(Ee, []):
                cc = net.conn[c]
                if not (cc["to_lane"] <= lane_E < cc["to_lane"] + cc["lanes"]):
                    continue
                j = lane_E - cc["to_lane"] + 1
                O_C = cc["length"] + (O_E - cc["to_pos"])
                if O_C - cc["length"] > D_MAX:
                    continue
                if (c, j) not in seen:
                    seen.add((c, j))
                    elems.append({"link": c, "lane": j, "O": O_C, "max_x": cc["length"], "kind": "conn", "via": None,
                                  "depth": depth + 1})
                if O_C >= D_MAX:
                    continue
                U, u = cc["from"], cc["from_lane"] + j - 1
                O_U = cc["from_pos"] + O_C
                if (U, u) in seen:
                    continue
                seen.add((U, u))
                alts = [(net.conn[o]["from_pos"], o) for o in net.outof.get(U, [])
                        if net.conn[o]["from_lane"] <= u < net.conn[o]["from_lane"] + net.conn[o]["lanes"]]
                elems.append({"link": U, "lane": u, "O": O_U, "max_x": cc["from_pos"], "kind": "up", "via": c,
                              "alts": sorted(alts), "depth": depth + 1})
                if O_U - cc["from_pos"] < D_MAX:
                    stack.append((U, u, O_U, depth + 1))
        trees[h["head_id"]] = elems
        keep.update(e["link"] for e in elems)
        if L not in down:
            starts = []
            for c in net.outof.get(L, []):
                lanes_c = range(net.conn[c]["from_lane"], net.conn[c]["from_lane"] + net.conn[c]["lanes"])
                if (any(ln in elig[L] for ln in lanes_c)
                        and all(net.conn[c]["from_pos"] >= max(any_head[L][ln]) - 0.5 for ln in lanes_c
                                if any_head[L][ln])):
                    starts.append(c)
            seen_d, reach, frontier = {L}, set(), []
            for c in starts:
                seen_d.add(c)
                reach.add(c)
                T = net.conn[c]["to"]
                if T not in seen_d:
                    seen_d.add(T)
                    reach.add(T)
                    frontier.append((T, net.conn[c]["length"] - net.conn[c]["to_pos"]))
            while frontier:
                X, dist0 = frontier.pop()
                for c in net.outof.get(X, []):
                    if c in seen_d:
                        continue
                    seen_d.add(c)
                    reach.add(c)
                    d2 = dist0 + net.conn[c]["from_pos"] + net.conn[c]["length"]
                    T = net.conn[c]["to"]
                    if T not in seen_d and d2 < DOWN_MAX:
                        seen_d.add(T)
                        reach.add(T)
                        frontier.append((T, d2 - net.conn[c]["to_pos"]))
            down[L] = sorted(reach, key=int)
    links = {}
    for lk in stop_links:
        outs = sorted(({"connector": c, "from_lane_first": net.conn[c]["from_lane"], "n_lanes": net.conn[c]["lanes"],
                        "from_pos_m": net.conn[c]["from_pos"], "to_link": net.conn[c]["to"]}
                       for c in net.outof.get(lk, [])), key=lambda x: (x["from_lane_first"], x["connector"]))
        links[lk] = outs
        keep.add(lk)
        for c in outs:
            keep.add(c["connector"])
            keep.add(c["to_link"])
    return trees, down, links, keep


# ================================================================================================ one run
def analyze_run(arr, itt_names, heads, trees, down, links, windows, mer=None):
    """analyze_run.py: per head, per green, the queue-discharge record of one run."""
    hp = {(int(h["link"]), h["lane"]): h["position_m"] for h in heads}
    hid = {(int(h["link"]), h["lane"]): int(h["head_id"]) for h in heads}
    stop_of = {int(h["head_id"]): int(h["link"]) for h in heads}
    lane_of = {int(h["head_id"]): h["lane"] for h in heads}
    outc = {}
    to_of_out = defaultdict(lambda: defaultdict(list))
    for lk, outs in links.items():
        for c in outs:
            outc[int(c["connector"])] = (int(lk), c["from_lane_first"], c["n_lanes"], c["from_pos_m"])
            to_of_out[int(lk)][int(c["to_link"])].append(int(c["connector"]))
    stop_links = {int(lk) for lk in links}
    k_arr, veh_arr = arr["k"], arr["veh"]
    link_l = arr["link"].tolist()
    lane_l = arr["lane"].tolist()
    pos_l = arr["pos"].tolist()
    sp_l = arr["speed"].tolist()
    len_l = arr["length"].tolist()
    nx_l = arr["next"].tolist()
    itt_l = arr["itt"].tolist()
    k_l = k_arr.tolist()
    veh_l = veh_arr.tolist()
    kmax = int(k_arr.max())

    def past_head(L2, i):
        if link_l[i] == L2:
            p2 = hp.get((L2, lane_l[i]))
            return hid[L2, lane_l[i]] if p2 is not None and pos_l[i] >= p2 else None
        C = outc.get(link_l[i])
        if C is not None and C[0] == L2:
            fl = C[1] + lane_l[i] - 1
            p2 = hp.get((L2, fl))
            return hid[L2, fl] if p2 is not None and C[3] >= p2 - HEAD_TOL else None
        return None

    member = defaultdict(list)
    has_pre, member_pre = {}, {}
    for H, elems in trees.items():
        for e in elems:
            if e["kind"] == "stop":
                alts = [(float(a), int(b)) for a, b in e.get("pre_head_exits", [])]
                has_pre[int(H)] = bool(alts)
                member_pre[int(H)] = alts
            else:
                alts = [(float(a), int(b)) for a, b in e.get("alts", [])]
            member[int(e["link"]), int(e["lane"])].append((int(H), float(e["O"]), float(e["max_x"]), e["kind"],
                                                           int(e["via"]) if e["via"] else None, alts))
    down_i = {int(L): {int(x) for x in v} for L, v in down.items()}

    def membership(i):
        best = None
        x = pos_l[i]
        for H, O, mx, kind, via, alts in member.get((link_l[i], lane_l[i]), ()):
            if (x >= mx) if kind == "stop" else (x > mx + 0.5):
                continue
            if kind == "up":
                nx = nx_l[i]
                if nx:
                    if nx != via:
                        continue
                else:
                    ahead = {c for fp, c in alts if fp > x}
                    if ahead != {via}:
                        continue
            elif kind == "stop" and alts:
                nx = nx_l[i]
                if nx and any(nx == c for fp, c in alts):
                    continue
            d = O - x
            if d > 0 and (best is None or d < best[1]):
                best = (H, d)
        return best

    n = len(k_l)
    memb_of = [membership(i) for i in range(n)]
    memb = [defaultdict(dict) for _ in range(kmax + 1)]
    for i in range(n):
        m = memb_of[i]
        if m is not None:
            memb[k_l[i]][m[0]][veh_l[i]] = (m[1], i)
    import numpy as np
    order = np.lexsort((k_arr, veh_arr)).tolist()
    cross = defaultdict(dict)
    cross_list = defaultdict(list)
    stats = defaultdict(int)
    for a in range(len(order)):
        i1 = order[a]
        m1 = memb_of[i1]
        if m1 is None:
            continue
        H, d1 = m1
        v = veh_l[i1]
        i2 = order[a + 1] if a + 1 < len(order) and veh_l[order[a + 1]] == v else None
        if i2 is not None:
            m2 = memb_of[i2]
            if m2 is not None and m2[0] == H:
                continue
        L = stop_of[H]
        target, how = None, ""
        if i2 is None or k_l[i2] > k_l[i1] + 1:
            if has_pre[H]:
                pre_ids = {c for fp, c in member_pre[H]}
                on_L = link_l[i1] == L
                decided = on_L and (pos_l[i1] > max(fp for fp, c in member_pre[H])
                                    or (nx_l[i1] and nx_l[i1] not in pre_ids))
                if not decided:
                    stats["E_gone_prehead_lane"] += 1
                    continue
            if d1 > max(REACH_M, 1.3 * 5.0 * sp_l[i1] / 3.6 + 20.0):
                stats["E_gone_far"] += 1
                continue
            target, how = H, "E_gone"
        elif link_l[i2] == L:
            ln2 = lane_l[i2]
            p2 = hp.get((L, ln2))
            if p2 is None:
                stats["A_headless_lane"] += 1
                continue
            if pos_l[i2] >= p2:
                target, how = hid[L, ln2], "A_stop_link"
            else:
                stats["A_lane_change_upstream"] += 1
                continue
        elif link_l[i2] in outc and outc[link_l[i2]][0] == L:
            C = outc[link_l[i2]]
            fl = C[1] + lane_l[i2] - 1
            p2 = hp.get((L, fl))
            if p2 is None:
                stats["B_headless_lane"] += 1
                continue
            if C[3] >= p2 - HEAD_TOL:
                target, how = hid[L, fl], "B_out_connector"
            else:
                stats["B_pre_head_exit"] += 1
                continue
        elif link_l[i2] in to_of_out[L]:
            cands = to_of_out[L][link_l[i2]]
            ref_lane = lane_l[i1] if link_l[i1] == L else lane_of[H]
            if link_l[i1] == L and nx_l[i1] in cands:
                cands = [nx_l[i1]]
            cov = [c for c in cands if outc[c][1] <= ref_lane < outc[c][1] + outc[c][2]]
            if len(cov) == 1:
                cands = cov
            after = [c for c in cands
                     if all(hp.get((L, ln)) is None or outc[c][3] >= hp[L, ln] - HEAD_TOL
                            for ln in range(outc[c][1], outc[c][1] + outc[c][2]))]
            if not after:
                stats["B2_pre_head_exit"] += 1
                continue
            if len(after) != len(cands):
                stats["B2_ambiguous"] += 1
                continue
            C = outc[after[0]]
            lanes = range(C[1], C[1] + C[2])
            fl = ref_lane if ref_lane in lanes else min(lanes, key=lambda q: abs(q - ref_lane))
            if (L, fl) not in hid:
                stats["B2_headless_lane"] += 1
                continue
            target, how = hid[L, fl], "B2_to_link"
        elif link_l[i2] in down_i[L]:
            target, how = H, "C_downstream"
            if link_l[i1] == L:
                nx = nx_l[i1]
                if nx in outc and outc[nx][0] == L:
                    C = outc[nx]
                    lanes = range(C[1], C[1] + C[2])
                    fl = lane_l[i1] if lane_l[i1] in lanes else min(lanes, key=lambda q: abs(q - lane_l[i1]))
                    if (L, fl) in hid:
                        target = hid[L, fl]
        else:
            stats["D_elsewhere"] += 1
            continue
        k = k_l[i1] + 1
        if v in cross[target]:
            stats["dup_crossing"] += 1
            continue
        cross[target][v] = k
        cross_list[target].append(k)
        stats["crossing_" + how] += 1
        if i2 is not None and k_l[i2] == k_l[i1] + 1:
            L2 = link_l[i2] if link_l[i2] in stop_links else (outc[link_l[i2]][0] if link_l[i2] in outc else None)
            if L2 is not None and L2 != L and L2 in down_i[L]:
                H2 = past_head(L2, i2)
                if H2 is not None and v not in cross[H2]:
                    cross[H2][v] = k
                    cross_list[H2].append(k)
                    stats["crossing_serial"] += 1
    cross_cnt = {h: np.bincount(np.asarray(lst, dtype=np.int64), minlength=kmax + 2) for h, lst in cross_list.items()}
    out_heads = {}
    for h in heads:
        H = int(h["head_id"])
        key = "%s-%s" % (h["sc"], h["sg"])
        greens = [(a, b) for a, b in windows.get(key, {}).get("green", []) if a >= T_FROM and b <= T_END and b - a >= 1.0]
        ambers = windows.get(key, {}).get("amber", [])
        cnt = cross_cnt.get(H, np.zeros(kmax + 2, dtype=np.int64))
        ck = cross.get(H, {})
        mh = mer.get(H) if mer is not None else None          # heads without an obs150 detector: no exact record
        mt = [x[0] for x in mh] if mh is not None else None
        mer_pass = defaultdict(list)
        for t, v in (mh or ()):
            mer_pass[v].append(t)
        cycles = []
        for gs, ge in greens:
            k0 = int(np.floor((gs + 1.0 - 0.1) / 5.0))
            if k0 < 0 or k0 + 1 > kmax:
                continue
            rows = sorted(memb[k0].get(H, {}).items(), key=lambda kv: kv[1][0])
            q0 = []
            prev_rear = None
            for v, (d, i) in rows:
                if sp_l[i] > V_Q_KMH:
                    break
                if prev_rear is None:
                    if d > FRONT_M:
                        break
                elif d - prev_rear > GAP_M:
                    break
                q0.append(v)
                prev_rear = d + len_l[i]
            kk_first = int(np.ceil((gs - 0.1) / 5.0 - 1e-9))
            full = [kk for kk in range(kk_first, kmax) if E.t_of(kk) >= gs and E.t_of(kk + 1) <= ge]
            hb = {v: ck[v] for v in q0 if v in ck and ck[v] > k0}
            rec = {"gs": gs, "ge": ge, "q0": len(q0), "q0_headbound": len(hb),
                   "gf_cross": int(sum(cnt[kk + 1] for kk in full)), "gf_sec": 5.0 * len(full), "bins": []}
            if hb:
                j = 1
                while k0 + j <= kmax:
                    a = max(E.t_of(k0 + j - 1), gs)
                    b = E.t_of(k0 + j)
                    if b > ge:
                        break
                    remaining = sum(1 for kc in hb.values() if kc > k0 + j)
                    c = int(cnt[k0 + j])
                    memp = memb[k0 + j - 1].get(H, {})
                    cand = sorted(memp[v] for v in hb if v in memp and hb[v] > k0 + j - 1)
                    front = [round(cand[0][0], 1), round(sp_l[cand[0][1]], 1),
                             itt_names.get(itt_l[cand[0][1]], "?")] if cand else None
                    rec["bins"].append([round(a - gs, 2), round(b - a, 2), c, remaining, front])
                    if remaining < 1:
                        break
                    j += 1
            if mh is not None:
                i0, i1 = bisect_left(mt, gs), bisect_right(mt, ge)
                qm = {}
                for v in q0:
                    after = [t for t in mer_pass.get(v, []) if t > gs]
                    if after:
                        qm[v] = min(after)
                if qm:
                    in_green = [t for t in qm.values() if t <= ge]
                    if in_green:
                        last = max(in_green)
                        rec["disc_t"] = [round(t - gs, 2) for t in mt[i0:i1] if t <= last]
                if rec["bins"]:
                    rec["bins_mer"] = [bisect_right(mt, gs + x[0] + x[1]) - bisect_right(mt, gs + x[0])
                                       for x in rec["bins"]]
            cycles.append(rec)
        out_heads[str(H)] = {"n_cross_total": int(sum(1 for kk in cross_list.get(H, []) if E.t_of(kk) > T_FROM + 5)),
                             "cycles": cycles}
    agree = None
    if mer is not None:
        rows = []
        for H in sorted(hid.values()):
            if H not in mer:
                continue
            n_m = sum(1 for t, _ in mer[H] if T_FROM + 5 < t <= E.t_of(kmax))
            n_f = sum(1 for kk in cross_list.get(H, []) if E.t_of(kk) > T_FROM + 5)
            rows.append((H, n_m, n_f))
        agree = {r[0]: (r[1], r[2]) for r in rows}
    return out_heads, dict(stats), agree


# ================================================================================================ table
def rate(n, t):
    return round(3600.0 * n / t, 1) if t > 0 else None


def impeded(b):
    front = b[4]
    return b[2] == 0 or (front is not None and front[1] < V_STAND)


def head_stats(cycles):
    r = defaultdict(float)
    cyc_rates = []
    for c in cycles:
        q = [b for b in c["bins"] if b[3] >= 1 and b[1] >= 4.99 and b[0] >= T_SU]
        stop = False
        n_c = t_c = 0.0
        for b in q:
            r["q_bins"] += 1
            r["n_all"] += b[2]
            r["t_all"] += b[1]
            if b[2] > 0:
                r["n_eff"] += b[2]
                r["t_eff"] += b[1]
            else:
                r["zero_bins"] += 1
            if impeded(b):
                r["impeded_bins"] += 1
                stop = True
            if not stop:
                n_c += b[2]
                t_c += b[1]
        if t_c > 0:
            r["n"] += n_c
            r["t"] += t_c
            r["bins"] += t_c / 5.0
            r["cycles"] += 1
            if t_c >= 15.0 - 1e-6:
                cyc_rates.append(3600.0 * n_c / t_c)
            end = max(b[0] + b[1] for b in q if not impeded(b)) if any(not impeded(b) for b in q) else None
            if end is not None:
                allb = [b for b in c["bins"] if b[0] + b[1] <= end + 1e-9]
                r["gs_n"] += sum(b[2] for b in allb)
                r["gs_t"] += end
        r["gf_n"] += c["gf_cross"]
        r["gf_t"] += c["gf_sec"]
    return r, cyc_rates


def exact_stats(cycles):
    nh, sh, blocked, hs = 0, 0.0, 0, []
    for c in cycles:
        d = c.get("disc_t")
        if not d:
            continue
        for x, y in zip(d, d[1:]):
            if x < T_SU:
                continue
            if y - x > H_BLOCK:
                blocked += 1
                break
            nh += 1
            sh += y - x
            hs.append(y - x)
    return nh, sh, blocked, hs


def trunc_mer(cycles):
    n_f = n_m = t = 0.0
    for c in cycles:
        if "bins_mer" not in c:
            continue
        stop = False
        for b, bm in zip(c["bins"], c["bins_mer"]):
            if not (b[3] >= 1 and b[1] >= 4.99 and b[0] >= T_SU):
                continue
            if impeded(b):
                stop = True
            if stop:
                break
            n_f += b[2]
            n_m += bm
            t += b[1]
    return n_f, n_m, t


def quantile(v, p):
    return v[min(len(v) - 1, max(0, int(round(p * (len(v) - 1)))))] if v else None


def group_row(g, runs, agree31, names):
    hs = [h["head_id"] for h in g["heads"]]
    n_l = len(hs)
    pooled = defaultdict(float)
    per_seed, per_head, cyc_rates = {}, {}, []
    for seed in E.NC_SEEDS:
        agg = defaultdict(float)
        for H in hs:
            s_, cr = head_stats(runs[seed][H]["cycles"])
            cyc_rates.extend(cr)
            ph = per_head.setdefault(H, defaultdict(float))
            for k2, v in s_.items():
                agg[k2] += v
                ph[k2] += v
        per_seed["s%d" % seed] = {"s_veh_h_lane": rate(agg["n"], agg["t"]) if agg["bins"] >= SEED_MIN_BINS else None,
                                  "bins": int(round(agg["bins"])), "passages": int(agg["n"]), "cycles": int(agg["cycles"])}
        for k2, v in agg.items():
            pooled[k2] += v
    seeds_with = sum(1 for s in per_seed.values() if s["bins"] > 0)
    s_tr = rate(pooled["n"], pooled["t"])
    vals = [s["s_veh_h_lane"] for s in per_seed.values() if s["s_veh_h_lane"] is not None]
    spread = None
    if len(vals) >= 2:
        mu = st.mean(vals)
        spread = {"n_seeds": len(vals), "min": min(vals), "max": max(vals), "mean": round(mu, 1),
                  "sd": round(st.stdev(vals), 1), "cv": round(st.stdev(vals) / mu, 3)}
    bins = int(round(pooled["bins"]))
    measured = bins >= MIN_BINS and pooled["cycles"] >= MIN_CYCLES and seeds_with >= MIN_SEEDS
    cr = sorted(cyc_rates)
    cyc_q = ({"n_cycles_ge15s": len(cr), "p25": round(cr[int(0.25 * (len(cr) - 1))], 1),
              "p50": round(cr[int(0.5 * (len(cr) - 1))], 1), "p75": round(cr[int(0.75 * (len(cr) - 1))], 1)}
             if len(cr) >= 5 else {"n_cycles_ge15s": len(cr)})
    imp_share = pooled["impeded_bins"] / pooled["q_bins"] if pooled["q_bins"] else None
    nh = sh = blk = 0.0
    allh = []
    nf = nm = tt = 0.0
    n31 = t31 = 0.0
    for H in hs:
        a, b, c_, h_ = exact_stats(runs[31][H]["cycles"])
        nh += a
        sh += b
        blk += c_
        allh += h_
        x, y, z = trunc_mer(runs[31][H]["cycles"])
        nf += x
        nm += y
        tt += z
        s31, _cr = head_stats(runs[31][H]["cycles"])
        n31 += s31["n"]
        t31 += s31["t"]
    s31_tr = rate(n31, t31)
    exact = round(3600.0 * nh / sh, 1) if sh > 0 else None
    with_det = [H for H in hs if int(H) in agree31]
    pas = ((sum(agree31[int(H)][0] for H in with_det), sum(agree31[int(H)][1] for H in with_det))
           if len(with_det) == len(hs) else None)
    validation = None
    if with_det:
        validation = {"heads_with_detector": len(with_det), "s_trunc_fzp_s31": s31_tr,
                      "s_trunc_bins_counted_with_mer_s31": rate(nm, tt), "s_exact_headway_s31": exact,
                      "s_exact_median_headway_s31": round(3600.0 / st.median(allh), 1) if len(allh) >= 10 else None,
                      "exact_headways_s31": int(nh), "exact_cycles_cut_by_blocking_s31": int(blk),
                      "passages_mer_fzp_s31": list(pas) if pas else None,
                      "trunc_bin_passages_fzp_vs_mer_s31": [int(nf), int(nm)]}
    flags = []
    if imp_share is not None and imp_share >= 0.10:
        flags.append("impeded_share_ge_10pct")
    if exact and s31_tr and nh >= 50 and abs(s31_tr - exact) / exact > 0.10:
        flags.append("fzp_vs_exact_s31_gt_10pct")
    if pas and pas[0] >= 100 and abs(pas[1] - pas[0]) / pas[0] > 0.05:
        flags.append("passage_count_fzp_vs_mer_gt_5pct")
    if spread and spread["cv"] > 0.08:
        flags.append("seed_cv_gt_8pct")
    sc = g["signal"].removeprefix("SC")
    sg_ids = sorted({h["sg"] for h in g["heads"]}, key=int)
    sgn = [names.get("%s-%s" % (sc, s)) for s in sg_ids]
    mtype = ("left" if all(x and x.endswith("L") for x in sgn) else
             "through" if all(x and x.endswith("T") for x in sgn) else "other")
    return {
        "key": g["group_id"], "signal": g["signal"], "phase": g["phase"], "native_signal": g["native_signal"],
        "observation_group": g["observation_group"], "stopline_link": g["stopline_link"], "signal_groups": sg_ids,
        "sg_names": sgn, "movement_type": mtype, "n_lanes": n_l,
        "heads": [{"head_id": h["head_id"], "lane": h["lane"], "sg": h["sg"], "position_m": round(h["position_m"], 3)}
                  for h in g["heads"]],
        "status": "measured" if measured else "default",
        "saturation_veh_h_per_lane": s_tr if measured else DEFAULT_VEH_H_LANE,
        "flags": flags,
        "measured": {
            "s_unimpeded_veh_h_lane": s_tr, "bins_5s": bins, "exposure_s": pooled["t"], "passages": int(pooled["n"]),
            "cycles": int(pooled["cycles"]), "seeds_with_samples": seeds_with,
            "qualifying_bins_incl_impeded": int(pooled["q_bins"]), "impeded_bins": int(pooled["impeded_bins"]),
            "impeded_share": round(imp_share, 3) if imp_share is not None else None,
            "s_effective_incl_partial_impediment_veh_h_lane": rate(pooled["n_eff"], pooled["t_eff"]),
            "s_all_queue_bins_incl_zero_veh_h_lane": rate(pooled["n_all"], pooled["t_all"]),
            "s_from_green_start_incl_startup_veh_h_lane": rate(pooled["gs_n"], pooled["gs_t"]),
            "green_average_flow_veh_h_lane": rate(pooled["gf_n"], pooled["gf_t"]),
            "per_cycle_rate_quantiles": cyc_q, "per_seed": per_seed, "per_seed_spread": spread,
            "per_head": {H: {"lane": next(h["lane"] for h in g["heads"] if h["head_id"] == H),
                             "s_veh_h": rate(v["n"], v["t"]), "bins_5s": int(round(v["bins"])), "cycles": int(v["cycles"]),
                             "impeded_bins": int(v["impeded_bins"])} for H, v in per_head.items()}},
        "validation_s31_exact": validation}


# ================================================================================================ derive
def derive(args) -> dict:
    root = pathlib.Path(args.root).resolve()
    contract = E.load_json(root / args.groups)
    if contract.get("schema") != CONTRACT_SCHEMA:
        raise SystemExit("--groups is not a %s document" % CONTRACT_SCHEMA)
    net_pin = E.file_pin(root, E.NETWORK)
    if contract["network"] != net_pin:
        raise SystemExit("the contract is pinned to another network")
    net = E.Network(root / E.NETWORK)
    groups = []
    for row in contract["groups"]:
        heads = []
        for h in row["heads"]:
            x = net.heads[h["head_id"]]
            if (x["link"], x["lane"], x["sg"]) != (row["stopline_link"], h["lane"], h["sg"]) \
                    or "SC" + x["sc"] != row["signal"] or abs(x["position_m"] - h["position_m"]) > 1e-3:
                raise SystemExit("%s: head %s differs from the network" % (row["group_id"], h["head_id"]))
            heads.append(dict(x))
        groups.append({"group_id": row["group_id"], "signal": row["signal"], "phase": row["phase"],
                       "native_signal": row["native_signal"], "observation_group": row["observation_group"],
                       "stopline_link": row["stopline_link"], "heads": heads})
    heads = [h for g in groups for h in g["heads"]]
    if len({h["head_id"] for h in heads}) != len(heads):
        raise SystemExit("a head belongs to two contract groups")
    # observation groups: the SHO rule on the pinned network and plan
    plan = E.load_json(root / E.PLAN)
    lanes = defaultdict(list)
    for h in net.root.findall("./signalHeads/signalHead"):
        link, lane = h.get("lane").split()
        lanes[link, lane].append(h)
    sho = defaultdict(set)
    for (link, lane), hs in lanes.items():
        if len(hs) != 1 or hs[0].get("allVehTypes") != "true":
            continue
        sc, sg = hs[0].get("sg").split()
        ctl = plan.get("controllers", {}).get(sc, {})
        ph = [p for p, g in ctl.get("phase_signal_groups", {}).items() if sg in map(str, g)]
        if len(ph) != 1 or sg in map(str, ctl.get("midblock_native_signal_groups", [])):
            continue
        sho["%s|%s" % (link, ph[0])].add(hs[0].get("no"))
    # observation groups: the SHO groups; the contract may add the controlling head of a lane that carries several
    # heads (SHO drops such lanes; e.g. 1220008601|p1 lane 2: 140402 SG 4 after 140701 SG 7)
    obs = {g["group_id"]: {h["head_id"] for h in g["heads"]} for g in groups if g["observation_group"]}
    extra_ok = all(len(net.heads_by_lane[net.heads[x]["link"], net.heads[x]["lane"]]) > 1
                   for key, hs in obs.items() for x in hs - sho.get(key, set()))
    if set(obs) != set(sho) or any(not sho[k] <= obs[k] for k in obs) or not extra_ok:
        raise SystemExit("the contract's observation groups are not signal_head_observation.physical_groups")
    # serial rule evidence (native_input 1093 pre-head pair)
    pre = E.load_json(root / args.prehead)
    first = {"%s|%s" % (x["lane"].split()[0], ph) for x in pre["first_heads"].values()
             for ph in [pre["first_phase"].rpartition("_")[2]]}
    for down_key, first_key in SERIAL_DOWNSTREAM.items():
        gd = next(g for g in groups if g["group_id"] == down_key)
        gf = next(g for g in groups if g["group_id"] == first_key)
        if first != {first_key} or {h["sg"] for h in gd["heads"]} != {h["sg"] for h in gf["heads"]} \
                or [net.conn[c]["to"] for c in net.outof[gf["stopline_link"]]] != [gd["stopline_link"]]:
            raise SystemExit("%s is not the same-SG downstream head of the serial first head %s" % (down_key, first_key))
    trees, down, links, keep = build_trees(net, groups)
    scs = sorted({h["sc"] for h in heads}, key=int)
    windows, sig_meta = E.sig_windows(net, scs)
    for sc in scs:
        for seed in E.NC_SEEDS:
            ran = pathlib.Path(E.nc_inpx(seed)).parent / sig_meta[sc]["sig"]
            if E.sha256_file(ran) != sig_meta[sc]["sig_sha256"]:
                raise SystemExit("SC%s: the .sig of NC seed %d differs from the pinned network's" % (sc, seed))
    lsa = E.lsa_windows(E.robs_file("lsa"), set(scs))
    used = sorted({"%s-%s" % (h["sc"], h["sg"]) for h in heads})
    lsa_mismatch = E.compare_windows(windows, lsa, used)
    names = {}
    for sc in scs:
        node = net.controllers[sc]
        import xml.etree.ElementTree as ET
        r = ET.parse(str(net.path.parent / node.get("supplyFile2").replace("#data#", ""))).getroot()
        for sg in r.findall("./sgs/sg"):
            names["%s-%s" % (sc, sg.get("id"))] = sg.get("name")
    runs, pins, stats, signatures = {}, [], {}, {}
    for seed in E.NC_SEEDS:
        signatures["s%d" % seed] = E.Network(E.nc_inpx(seed)).signature() == net.signature()
        arr, meta = E.stream_fzp(E.nc_fzp(seed), keep)
        mer = None
        if seed == 31:
            detectors = E.head_detectors(root)
            entries, mmeta = E.mer_head_entries(E.robs_file("mer"), detectors)
            mer = {int(h): [] for h in detectors.values()}      # a detector head without an entry is a zero record
            for head, t, veh in entries:
                mer[int(head)].append((t, veh))
            for h in mer:
                mer[h].sort()
        out_heads, st_, agree = analyze_run(arr, meta["itt_names"], heads, trees, down, links, windows, mer)
        runs[seed] = out_heads
        stats["s%d" % seed] = dict(sorted(st_.items()))
        if seed == 31:
            agree31 = agree
        pins.append({"seed": seed, "path": meta["path"], "sha256": meta["sha256"], "bytes": meta["bytes"],
                     "rows_total": meta["rows_total"], "rows_kept": meta["rows_kept"]})
        del arr
    rows = [group_row(g, runs, agree31, names) for g in groups]
    by = {r["key"]: r for r in rows}
    for down_key, first_key in SERIAL_DOWNSTREAM.items():
        r = by[down_key]
        r["status"] = "serial_first_head"
        r["saturation_veh_h_per_lane"] = by[first_key]["saturation_veh_h_per_lane"]
        r["value_source"] = first_key
    for r in rows:
        r.setdefault("value_source", r["key"] if r["status"] == "measured" else "default")
        if r["status"] == "default":
            b = r["measured"]["bins_5s"]
            r["default_reason"] = ("no_queue_discharge_sample" if b == 0 else
                                   "insufficient_samples(bins=%d,cycles=%d,seeds=%d)"
                                   % (b, r["measured"]["cycles"], r["measured"]["seeds_with_samples"]))
    meas = [r for r in rows if r["status"] == "measured"]
    allv = sorted(r["saturation_veh_h_per_lane"] for r in meas)
    clean = sorted(r["saturation_veh_h_per_lane"] for r in meas if not r["flags"])

    def part(sel):
        v = sorted(r["saturation_veh_h_per_lane"] for r in sel if r["status"] == "measured")
        return {"groups": len(sel), "measured": len(v), "default": sum(1 for r in sel if r["status"] == "default"),
                "serial_first_head": sum(1 for r in sel if r["status"] == "serial_first_head"),
                "median_measured": st.median(v) if v else None}
    summary = {
        "n_groups": len(rows), "n_heads": sum(r["n_lanes"] for r in rows),
        "status": {s: sum(1 for r in rows if r["status"] == s) for s in ("measured", "default", "serial_first_head")},
        "by_class": {"observation_105": part([r for r in rows if r["observation_group"]]),
                     "controlled_multi_head_3": part([r for r in rows if not r["observation_group"]
                                                      and not r["native_signal"]]),
                     "native_66": part([r for r in rows if r["native_signal"]])},
        "measured_per_lane_quantiles": {"min": allv[0], "p10": quantile(allv, .1), "p25": quantile(allv, .25),
                                        "median": quantile(allv, .5), "p75": quantile(allv, .75),
                                        "p90": quantile(allv, .9), "max": allv[-1]} if allv else None,
        "measured_unflagged_per_lane_quantiles": {"n": len(clean), "p25": quantile(clean, .25),
                                                  "median": quantile(clean, .5), "p75": quantile(clean, .75)},
        "flagged_groups": {r["key"]: r["flags"] for r in rows if r["flags"]},
        "crossing_stats": stats,
        "nc_network_signature_equal_to_pinned": signatures,
        "sig_vs_robsb_lsa_mismatching_used_sgs": lsa_mismatch,
    }
    return {
        "schema": SCHEMA,
        "generated": args.generated,
        "generator": "scripts/derive_head_saturation.py",
        "decision": ("user decisions 2026-09-27/28/29: urban batch 2 C3 = U4 + U5 + U6 (all or nothing); U4 covers the "
                     "observation, multi-head and native groups (Q1); default 1850 veh/h/lane (BATCH2_PLAN 10-1)"),
        "network": net_pin,
        "network_signature": net.signature(),
        "groups_source": E.file_pin(root, args.groups),
        "prehead_evidence": E.file_pin(root, args.prehead),
        "lane_files": {"internal": E.file_pin(root, args.lanes_internal),
                       "perimeter": E.file_pin(root, args.lanes_perimeter),
                       "use": ("lane count of a movement outside every head group (default_veh_h_per_lane x lanes; "
                               "the lane files and turn-median rules of install_movement_capacity_by_lanes)")},
        "nc_fzp": pins,
        "robsb_exact": {"mer": {"path": E.posix(E.robs_file("mer")), "sha256": E.sha256_file(E.robs_file("mer"))},
                        "lsa": {"path": E.posix(E.robs_file("lsa")), "sha256": E.sha256_file(E.robs_file("lsa"))},
                        "head_detectors": E.file_pin(root, E.N31 + "/obs150/obs150_detectors_v2.csv")},
        "sig": {sc: {k: sig_meta[sc][k] for k in ("sig", "sig_sha256", "prog", "cycle_sec", "offset_sec")} for sc in scs},
        "sig_equal_in_nc_runs": "every .sig above is byte-equal in the prepared network of each NC fit seed (checked)",
        "parameters": {"D_MAX_m": D_MAX, "DOWN_MAX_m": DOWN_MAX, "FRONT_M": FRONT_M, "V_Q_KMH": V_Q_KMH, "GAP_M": GAP_M,
                       "window_s": [T_FROM, T_END], "HEAD_TOL_m": HEAD_TOL, "REACH_M": REACH_M, "T_SU_s": T_SU,
                       "V_STAND_kmh": V_STAND, "MIN_BINS": MIN_BINS, "MIN_CYCLES": MIN_CYCLES, "MIN_SEEDS": MIN_SEEDS,
                       "SEED_MIN_BINS": SEED_MIN_BINS, "H_BLOCK_s": H_BLOCK},
        "default_veh_h_per_lane": DEFAULT_VEH_H_LANE,
        "value_rules": {"measured": "s_unimpeded_veh_h_lane of the five NC fit seeds",
                        "default": "default_veh_h_per_lane",
                        "serial_first_head": "the value of the serial first head group (value_source)"},
        "summary": summary,
        "groups": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for k, v in DEFAULTS.items():
        ap.add_argument("--" + k.replace("_", "-"), dest=k, default=v)
    ap.add_argument("--root", default=str(HERE.parent))
    ap.add_argument("--generated", default="2026-09-29")
    ap.add_argument("--out", required=True)
    ap.add_argument("--check", action="store_true", help="compare with --out instead of writing it")
    args = ap.parse_args()
    data = E.dumps(derive(args))
    root = pathlib.Path(args.root).resolve()
    out = pathlib.Path(args.out) if pathlib.Path(args.out).is_absolute() else root / args.out
    if args.check:
        if not out.is_file() or out.read_bytes() != data:
            raise SystemExit("%s differs from its derivation" % args.out)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    import json
    doc = json.loads(data)
    print("summary", {k: doc["summary"][k] for k in ("n_groups", "n_heads", "status", "by_class")})
    print("HEAD_SATURATION_OK sha256=" + hashlib.sha256(data).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
