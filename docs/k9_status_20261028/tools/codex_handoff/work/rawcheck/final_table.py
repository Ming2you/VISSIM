# Final metric table for the 6 conditions (64cf-s29, one seed): Omega701, Omega635 (previous_inside_links), FW_E7, local19,
# 4a (FZP), 4b (native DelayLatent 0-8100 for control arms; NC reconstructed), 4 = 4a + 4b, Omega-outside (a) = 4 - Omega701,
# Omega-outside (b) = 4a - Omega701, per-input 4b (1098, 1099, urban 32).
import json
B = "D:/VISSIM_handoff/20261024"
d = json.load(open(f"{B}/derived/omega_membership_exact.json", encoding="utf-8"))
prev = set(d["controlled_intersection_expansion"]["previous_inside_links"])
inside = set(d["inside_links"])
print("previous_inside_links", len(prev), "subset of 701:", prev <= inside)
M = json.load(open("metrics_out.json"))["codex_rule"]
U = json.load(open("uninserted2_out.json"))
res = U["res"]
nc4b_A = U["nc_4b_routeA"]; nc4b_B = U["nc_4b_routeB"]
T = {}
for c in ["nc", "joint", "window", "off", "freeway_only", "urban_only"]:
    lr = json.load(open(f"scan/{c}.json"))["link_residence_veh_h"]
    o635 = sum(v for k, v in lr.items() if k in prev)
    m = M[c]
    if c == "nc":
        b4 = nc4b_A
    else:
        b4 = res[c]["native_0_T"]
    # per-input split: reconstruction + common residual spread proportionally? keep raw reconstruction, residual reported separately
    T[c] = dict(Omega701=m["Omega701"], Omega635=o635, FW_E7=m["FW_E_7"], local19=m["local_19"], a4=m["whole_4a"], b4=b4,
                four=m["whole_4a"] + b4, out_a=m["whole_4a"] + b4 - m["Omega701"], out_b=m["whole_4a"] - m["Omega701"],
                b4_1098=res[c]["i1098"], b4_1099=res[c]["i1099"], b4_urban=res[c]["urban"],
                urban_roads=m["urban_roads"], offramps=m["offramps"], onE=m["onramps_E"], onW=m["onramps_W"], FW_W=m["FW_W"])
keys = ["Omega701", "Omega635", "FW_E7", "local19", "a4", "b4", "four", "out_a", "out_b", "b4_1098", "b4_1099", "b4_urban", "urban_roads", "offramps", "onE", "onW", "FW_W"]
print("cond".ljust(13) + "".join(k.rjust(11) for k in keys))
for c, t in T.items():
    print(c.ljust(13) + "".join(f"{t[k]:11.1f}" for k in keys))
print("--- minus NC")
for c, t in T.items():
    if c == "nc": continue
    print(c.ljust(13) + "".join(f"{t[k]-T['nc'][k]:11.1f}" for k in keys))
print("--- joint minus off / window minus off")
for a, b in [("joint", "off"), ("window", "off")]:
    print(f"{a}-{b}".ljust(13) + "".join(f"{T[a][k]-T[b][k]:11.1f}" for k in keys))
print("NC 4b route A %.1f route B %.1f (diff %.1f); joint-NC d4 with route B: %.1f" % (nc4b_A, nc4b_B, nc4b_B - nc4b_A, T['joint']['four'] - (T['nc']['a4'] + nc4b_B)))
print("percent joint vs NC: Omega701 %.3f%% Omega635 %.3f%% 4 %.3f%% out_a %.3f%% out_b %.3f%%" % tuple(100 * (T['joint'][k] / T['nc'][k] - 1) for k in ["Omega701", "Omega635", "four", "out_a", "out_b"]))
json.dump(T, open("final_table.json", "w"), indent=1)
