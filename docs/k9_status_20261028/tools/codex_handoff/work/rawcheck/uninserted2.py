# RAW_CHECK step 5 (v2): common-arrival estimator.
# Evidence that arrivals are seed-determined and shared by all arms: realized arrivals by 8100 (I+U) equal across the 5 control arms
# (1098: 16070 x5; 1099: 20166-20169; each urban input: identical counts). So A_i(t) is common; I_c,i(t) <= A_i(t).
# Estimator: A_i(t) = max( envelope_c I_c,i(t) [lag-corrected], scaled expected profile ) for 1098/1099;
#            urban inputs: A_i(t) = envelope over the 6 arms (nc, joint, window, off, freeway_only, urban_only) of lag-corrected I.
# U_c,i(t) = max(0, A_i(t) - I_c,i(t)).  Integral 0-8100 on 1-s grid.  Check against native DelayLatent per arm.
import json, numpy as np
S = "scan"
inp = json.load(open("inputs_64cf.json", encoding="utf-8"))
g = json.load(open("graph_64cf.json")); pred = g["pred"]
link2in = {v["link"]: k for k, v in inp.items()}
def owner(link):
    link = str(link)
    if link in link2in: return link2in[link]
    cur = [link]; seen = set()
    for hop in range(3):
        nxt = []
        for c in cur:
            for p in pred.get(c, []):
                if p not in seen: seen.add(p); nxt.append(p)
        hit = sorted({link2in[p] for p in nxt if p in link2in})
        if hit: return hit[0] if len(hit) == 1 else "AMBIG"
        cur = nxt
    return "NONE"
rates = {k: sorted((int(tv["timeInt"].split()[1]) / 1000.0, float(tv["volume"])) for tv in v["vols"]) for k, v in inp.items()}
def Aexp(k, t):
    s = 0.0; R = rates[k]
    for i, (st, q) in enumerate(R):
        en = R[i + 1][0] if i + 1 < len(R) else 1e12
        if t > st: s += q / 3600.0 * (min(t, en) - st)
    return s
ARMS = ["nc", "joint", "window", "off", "freeway_only", "urban_only"]
NATIVE = {"nc": (9000, 69444031.299998), "joint": (8100, 59124855.799999), "window": (8100, 58795405.800001),
          "off": (8100, 59231689.899999), "freeway_only": (8100, 63131643.999999), "urban_only": (8100, 59188358.400000)}
UEND = {"nc": 10857, "joint": 10217, "window": 10235, "off": 10285, "freeway_only": 11409, "urban_only": 10334}
grid = np.arange(0.5, 9000, 1.0)
ins = {}
for c in ARMS:
    z = np.load(f"{S}/{c}_veh.npz")
    lf, tf, pf, sf = z["link_first"], z["t_first"], z["pos_first"], z["speed_first"]
    oc = {}; own = np.array([oc.setdefault(l, owner(l)) for l in lf.tolist()])
    v = sf / 3.6
    lag = np.where(v > 0.5, np.minimum(5.0, pf / np.maximum(v, 1e-9)), 2.5)
    ins[c] = {k: np.sort(tf[own == k] - lag[own == k]) for k in inp}
    ins[c]["_raw"] = {k: np.sort(tf[own == k]) for k in inp}
I = {c: {k: np.searchsorted(ins[c][k], grid, side="right").astype(float) for k in inp} for c in ARMS}
env = {k: np.max(np.vstack([I[c][k] for c in ARMS]), axis=0) for k in inp}
# realized totals
R8100 = {}
for k in ("1098", "1099"):
    R8100[k] = {c: int(np.searchsorted(ins[c]["_raw"][k], 8100, side="right")) + (UEND[c] if k == "1099" and c != "nc" else 0) for c in ARMS if c != "nc"}
print("realized arrivals by 8100 (I+U) per control arm:", R8100)
nc_R9000 = {"1098": int(np.searchsorted(ins["nc"]["_raw"]["1098"], 9000, side="right")),
            "1099": int(np.searchsorted(ins["nc"]["_raw"]["1099"], 9000, side="right")) + UEND["nc"]}
print("NC realized arrivals by 9000:", nc_R9000, "NC I_1098(8100)", int(np.searchsorted(ins['nc']['_raw']['1098'], 8100, side='right')))
A = {}
for k in inp:
    if k in ("1098", "1099"):
        Rk = int(np.median(list(R8100[k].values())))
        # scale expected profile on [0,8100] to Rk; beyond 8100 use NC total 9000
        e8100 = Aexp(k, 8100)
        base = np.array([Aexp(k, t) for t in grid])
        a = np.where(grid <= 8100, base * Rk / e8100,
                     Rk + (base - e8100) * (nc_R9000[k] - Rk) / max(1e-9, Aexp(k, 9000) - e8100))
        A[k] = np.maximum(a, env[k])
    else:
        A[k] = env[k].copy()
res = {}
m81 = grid < 8100
for c in ARMS:
    per = {}
    for k in inp:
        U = np.maximum(0.0, A[k] - I[c][k])
        per[k] = dict(int_0_8100=float(U[m81].sum() / 3600), int_0_9000=float(U.sum() / 3600) if c == "nc" else None,
                      U_8100=float(A[k][8099] - I[c][k][8099]))
    T, dl = NATIVE[c]
    tot81 = sum(p["int_0_8100"] for p in per.values())
    totT = sum((p["int_0_9000"] if T == 9000 else p["int_0_8100"]) for p in per.values())
    urb = sum(p["int_0_8100"] for k, p in per.items() if k not in ("1098", "1099"))
    res[c] = dict(per_input=per, recon_0_8100=tot81, recon_0_T=totT, native_0_T=dl / 3600, resid_native_minus_recon=dl / 3600 - totT,
                  i1098=per["1098"]["int_0_8100"], i1099=per["1099"]["int_0_8100"], urban=urb)
    topu = sorted(((k, round(p["int_0_8100"], 2)) for k, p in per.items() if k not in ("1098", "1099")), key=lambda x: -x[1])[:5]
    print(f"{c:13s} 1098 {res[c]['i1098']:8.1f}  1099 {res[c]['i1099']:9.1f}  urban {urb:6.1f} top {topu}  recon0-8100 {tot81:9.1f}  "
          f"recon0-{T} {totT:9.1f} native0-{T} {dl/3600:9.1f} resid {dl/3600-totT:7.1f}")
# NC 0-8100 by two routes
resid_ctrl = [res[c]["resid_native_minus_recon"] for c in ARMS if c != "nc"]
nc_fwd = res["nc"]["recon_0_8100"]
nc_tail = res["nc"]["recon_0_T"] - res["nc"]["recon_0_8100"]
print("\nresidual native-recon over 5 control arms: mean %.1f min %.1f max %.1f" % (np.mean(resid_ctrl), min(resid_ctrl), max(resid_ctrl)))
print("NC recon 0-8100 %.1f, NC recon tail 8100-9000 %.1f, NC native 0-9000 %.1f, NC resid(0-9000) %.1f" % (nc_fwd, nc_tail, res['nc']['native_0_T'], res['nc']['resid_native_minus_recon']))
print("NC 4b(0-8100) route A (native9000 - recon tail): %.1f" % (res['nc']['native_0_T'] - nc_tail))
print("NC 4b(0-8100) route B (recon 0-8100 + mean control-arm residual): %.1f" % (nc_fwd + np.mean(resid_ctrl)))
# per-input 0-8100 differences vs NC (A-independent when both queued)
print("\nper-input d(arm - NC) 0-8100 veh.h (1098, 1099, urban, total):")
for c in ARMS[1:]:
    d98 = res[c]["i1098"] - res["nc"]["i1098"]; d99 = res[c]["i1099"] - res["nc"]["i1099"]; du = res[c]["urban"] - res["nc"]["urban"]
    print(f"  {c:13s} {d98:8.1f} {d99:8.1f} {du:7.1f} {d98+d99+du:8.1f}")
json.dump(dict(R8100=R8100, nc_R9000=nc_R9000, res=res, resid_ctrl=resid_ctrl,
               nc_4b_routeA=res['nc']['native_0_T'] - nc_tail, nc_4b_routeB=nc_fwd + float(np.mean(resid_ctrl))),
          open("uninserted2_out.json", "w"), indent=1)
