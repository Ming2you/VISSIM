# VERIFY: fresh re-derivation of HANDOFF/TAKEOVER percentages from handoff/evidence (read only)
import csv, json, itertools
E = "D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/handoff/evidence"
rows = list(csv.DictReader(open(f"{E}/metrics_0_8100.csv", encoding="utf-8-sig")))
M = {}
for r in rows:
    M[(r["condition"], r["metric"])] = float(r["veh_h"])
conds = sorted({c for c, _ in M})
mets = sorted({m for _, m in M})
print("conditions", conds)
print("metrics", mets)
for m in mets:
    nc = M.get(("nc", m))
    for c in conds:
        if c == "nc" or (c, m) not in M:
            continue
        v = M[(c, m)]
        print(f"{m:40s} {c:13s} nc={nc:12.4f} v={v:12.4f} d={v-nc:+10.4f} pct={(v-nc)/nc*100:+8.4f}%")
ifc = json.load(open(f"{E}/independent_fzp_counts.json", encoding="utf-8"))
key = {"FW_E_7": "FW_E_7", "local_19": "local_19", "Omega701": "Omega701", "whole_observed": None}
print("--- independent vs csv")
for c in ["nc", "joint", "window", "off"]:
    for k in ["FW_E_7", "local_19", "Omega701", "whole_observed"]:
        iv = ifc[c][k]
        cands = [m for m in mets if (c, m) in M and abs(M[(c, m)] - iv) < 1e-6]
        print(c, k, round(iv, 6), "csv match:", cands)
rm = json.load(open(f"{E}/run_metadata.json", encoding="utf-8"))
N = {r["condition"]: r for r in rm}
print("--- native")
for c, r in N.items():
    print(c, r["sim_period_s"], round(r["native_road_veh_h"], 3), round(r["native_uninserted_wait_veh_h"], 3), r["native_uninserted_end_vehicles"],
          "ratio uninserted/road", round(r["native_uninserted_wait_veh_h"] / r["native_road_veh_h"], 4))
# arm differences joint-off, joint-window, window-off
def om(c):
    return ifc[c]["Omega701"]
for a, b in [("joint", "off"), ("joint", "window"), ("window", "off")]:
    d4 = N[a]["native_road_plus_uninserted_veh_h"] - N[b]["native_road_plus_uninserted_veh_h"]
    d4b = N[a]["native_uninserted_wait_veh_h"] - N[b]["native_uninserted_wait_veh_h"]
    dO = om(a) - om(b)
    print(f"{a}-{b}: dOmega={dO:+.2f} d4={d4:+.2f} d4b={d4b:+.2f} dOutside(a)={d4-dO:+.2f}")
# NC 0-8100 uninserted bracket under two assumption sets
D_last = 6336.0  # 64cf 1099 demand 4500-9000 interval veh/h (checked separately in v3_net.py)
U9000 = N["nc"]["native_uninserted_end_vehicles"]
W9000 = N["nc"]["native_uninserted_wait_veh_h"]
def nc_w8100(Q):
    U8100 = U9000 - (D_last - Q) * 0.25
    tail = (U8100 + U9000) / 2 * 0.25
    return U8100, W9000 - tail
j4a = M[("joint", "network_sampled_residence")]; n4a = M[("nc", "network_sampled_residence")]; jO = M[("joint","Omega701")]; nO = M[("nc","Omega701")]
print("joint 4a", j4a, "nc 4a", n4a)
for label, Qs in [("R_CLAIMS Q 3500-7000", (3500, 7000)), ("R_NET Q 0-6336", (0, 6336)), ("center 4400", (4400, 4400))]:
    out = []
    for Q in Qs:
        U8, w = nc_w8100(Q)
        d4b = N["joint"]["native_uninserted_wait_veh_h"] - w
        d4 = (j4a - n4a) + d4b
        nc4 = n4a + w
        out.append(dict(Q=Q, U8100=round(U8, 1), NC4b=round(w, 1), d4b=round(d4b, 1), d4=round(d4, 1), d4pct=round(d4/nc4*100, 2), dOutA=round(d4-(jO-nO), 1)))
    print(label, out)
