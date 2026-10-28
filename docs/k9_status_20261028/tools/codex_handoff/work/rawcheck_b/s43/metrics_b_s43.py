# RAW_CHECK: metrics from own scan (scan/*.json) vs codex cache (derived/metrics_0_8100.csv, independent_fzp_counts.json)
import json, csv
B = "D:/VISSIM_handoff/20261024"
S = "C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/rawcheck_b/s43/scan"   # [B copy 2026-10-26 KST, COMPARE_RULE_B: path constants only; seed v3c3-s43; slot "nc" = NC3, "joint" = B] 
inside = set(json.load(open(f"{B}/derived/omega_membership_exact.json", encoding="utf-8"))["inside_links"])
geo = json.load(open(f"{B}/code/diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json", encoding="utf-8"))
chain = {str(x["link"]): r for r, rows in geo["chains"].items() for x in rows}
on = {str(b["connector"]): b["road"] for b in geo["boundaries"] if b["kind"] == "ramp"}
off = {str(b["connector"]) for b in geo["boundaries"] if b["kind"] == "offramp"}
S7 = {"74", "10699", "2", "10613", "119", "10702", "24"}
S19 = S7 | {"10484", "10490", "10639", "10681", "10481", "10483", "10643", "10682", "129", "31", "68", "70"}
UPSTREAM = {"70": "FW_E", "68": "FW_E", "129": "FW_E", "31": "FW_E", "124": "FW_W", "32": "FW_W", "121": "FW_W", "69": "FW_W"}
assert set(chain.get(k) for k in S7) == {"FW_E"}
assert all(k in inside for k in UPSTREAM)
print("offramps inside:", sorted(k for k in off if k in inside), "outside:", sorted(k for k in off if k not in inside))
def parts(res, alt=False):
    p = {k: 0.0 for k in ("FW_E", "FW_W", "onramps_E", "onramps_W", "urban_roads", "offramps", "outside")}
    for link, v in res.items():
        if link not in inside:
            g = "outside"
        elif link in chain:
            g = chain[link]
        elif link in on:
            g = "onramps_E" if on[link] == "FW_E" else "onramps_W"
        elif alt and link in UPSTREAM:
            g = "onramps_E" if UPSTREAM[link] == "FW_E" else "onramps_W"
        elif link in off:
            g = "offramps"
        else:
            g = "urban_roads"
        p[g] += v
    p["urban"] = p["urban_roads"] + p["offramps"]
    p["Omega701"] = p["FW_E"] + p["FW_W"] + p["onramps_E"] + p["onramps_W"] + p["urban"]
    p["Omega_minus_W_mainline"] = p["Omega701"] - p["FW_W"]
    p["whole_4a"] = p["Omega701"] + p["outside"]
    p["FW_E_7"] = sum(res.get(k, 0) for k in S7)
    p["local_19"] = sum(res.get(k, 0) for k in S19)
    return p
conds = ["nc", "joint", "window", "off", "freeway_only", "urban_only", "lnc"]
M, A = {}, {}
scan = {}
for c in conds:
    d = json.load(open(f"{S}/{c}.json"))
    scan[c] = {k: d[k] for k in d if k != "link_residence_veh_h"}
    M[c] = parts(d["link_residence_veh_h"]); A[c] = parts(d["link_residence_veh_h"], alt=True)
# codex cache
cache = {}
for r in csv.DictReader(open(f"{B}/derived/metrics_0_8100.csv", encoding="utf-8-sig")):
    cache.setdefault(r["condition"], {})[r["metric"]] = float(r["veh_h"])
ifc = json.load(open(f"{B}/derived/independent_fzp_counts.json", encoding="utf-8"))
mapc = {"FW_E_7": "FW_E_7", "local_19": "local_19", "Omega701": "Omega701", "outside_Omega_residence": "outside",
        "network_sampled_residence": "whole_4a", "urban_roads": "urban_roads", "urban": "urban", "onramps_E": "onramps_E",
        "onramps_W": "onramps_W", "offramps": "offramps", "Omega_minus_W_mainline": "Omega_minus_W_mainline"}
maxdiff = 0
print("\n== own vs codex metrics_0_8100.csv (cache) ==")
for c in cache:
    for mk, ok in mapc.items():
        if mk in cache[c]:
            dlt = M[c][ok] - cache[c][mk]; maxdiff = max(maxdiff, abs(dlt))
            if abs(dlt) > 1e-6: print("  DIFF", c, mk, M[c][ok], cache[c][mk], dlt)
print("max |own - cache| =", maxdiff, "conditions in cache:", sorted(cache))
print("\n== own vs independent_fzp_counts.json ==")
for c, v in ifc.items():
    if not isinstance(v, dict) or c not in M: continue
    for k, ok in [("FW_E_7", "FW_E_7"), ("local_19", "local_19"), ("Omega701", "Omega701"), ("whole_observed", "whole_4a")]:
        if k in v: print(f"  {c:12s} {k:15s} own {M[c][ok]:.6f} ifc {v[k]:.6f} diff {M[c][ok]-v[k]:.2e}")
    if "rows" in v: print(f"  {c:12s} rows own {scan[c]['rows_le_8100']} ifc {v['rows']} frames own {scan[c]['frames_le_8100']} ifc {v.get('frames')}")
print("\n== table (own scan) ==")
keys = ["Omega701", "FW_E_7", "local_19", "whole_4a", "outside", "urban_roads", "offramps", "urban", "onramps_E", "onramps_W", "FW_W", "Omega_minus_W_mainline"]
print("cond".ljust(13) + "".join(k[:11].rjust(12) for k in keys))
for c in conds:
    print(c.ljust(13) + "".join(f"{M[c][k]:12.3f}" for k in keys))
print("\n== minus NC (own) ==")
for c in conds[1:]:
    print(c.ljust(13) + "".join(f"{M[c][k]-M['nc'][k]:12.3f}" for k in keys))
print("\n== urban_roads % reduction (codex rule) ==")
for c in conds[1:]:
    print(c, f"{100*(1-M[c]['urban_roads']/M['nc']['urban_roads']):.6f} %", "Omega701", f"{100*(1-M[c]['Omega701']/M['nc']['Omega701']):.6f} %")
print("\n== ALT rule: meter-upstream links 70,68,129,31 / 124,32,121,69 counted as on-ramp ==")
for c in conds:
    print(c.ljust(13) + "".join(f"{A[c][k]:12.3f}" for k in keys))
for c in conds[1:]:
    print(c, "urban_roads(alt) d", round(A[c]['urban_roads'] - A['nc']['urban_roads'], 3), f"{100*(1-A[c]['urban_roads']/A['nc']['urban_roads']):.4f} %",
          "onramps_E(alt) d", round(A[c]['onramps_E'] - A['nc']['onramps_E'], 3), "onramps_W(alt) d", round(A[c]['onramps_W'] - A['nc']['onramps_W'], 3))
up = {c: {k: json.load(open(f"{S}/{c}.json"))["link_residence_veh_h"].get(k, 0) for k in UPSTREAM} for c in conds}
print("\nupstream link residence per cond:")
for k in UPSTREAM:
    print(" ", k, UPSTREAM[k], " ".join(f"{c}={up[c][k]:.2f}" for c in conds))
json.dump(dict(codex_rule=M, alt_rule=A, scan=scan, upstream=up, max_abs_diff_vs_cache=maxdiff), open(f"{S}/../metrics_out.json", "w"), indent=1)
