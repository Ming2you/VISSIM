# RAW_CHECK: per-input uninserted (latent) queue integrals, 0-8100 s, reconstructed from FZP first-seen times.
# Method: I_i(t) = cumulative count of vehicles first seen on input i's link (or 1-2 connector hops downstream of it).
#         A_i(t) = expected arrivals from the .inpx volume table (STOCHASTIC), scaled so A_i(T) = I_i(T) + U_i(T),
#         U_i(T) from the .err "could not be finished (remain: N)" line (absent => 0).
#         U_i(t) = max(0, A_i(t) - I_i(t)); integral on 1-s grid. Lag variant: insertion time = first-seen time - min(5, pos/v).
import json, numpy as np, bisect, math
S = "scan"
inp = json.load(open("inputs_64cf.json", encoding="utf-8"))
g = json.load(open("graph_64cf.json"))
pred = g["pred"]
link2in = {v["link"]: k for k, v in inp.items()}
def owner(link):
    link = str(link)
    if link in link2in: return link2in[link]
    cur = [link]; seen = set()
    for hop in range(3):
        nxt = []
        for c in cur:
            for p in pred.get(c, []):
                if p in seen: continue
                seen.add(p); nxt.append(p)
        hit = sorted({link2in[p] for p in nxt if p in link2in})
        if len(hit) == 1: return hit[0]
        if len(hit) > 1: return "AMBIG"
        cur = nxt
    return None
rates = {}
for k, v in inp.items():
    rr = []
    for tv in v["vols"]:
        st = int(tv["timeInt"].split()[1]) / 1000.0
        rr.append((st, float(tv["volume"])))
    rates[k] = sorted(rr)
def Aexp(k, t):
    s = 0.0; R = rates[k]
    for i, (st, q) in enumerate(R):
        en = R[i + 1][0] if i + 1 < len(R) else 1e12
        if t > st: s += q / 3600.0 * (min(t, en) - st)
    return s
UEND = {"nc": 10857, "lnc": 10857, "joint": 10217, "window": 10235, "off": 10285, "freeway_only": 11409, "urban_only": 10334}
TEND = {"nc": 9000, "lnc": 9000}
NATIVE_DL = {"nc": 69444031.299998, "joint": 59124855.799999, "window": 58795405.800001, "off": 59231689.899999,
             "freeway_only": 63131643.999999, "urban_only": 59188358.400000}
grid = np.arange(0.5, 8100, 1.0)
out = {}
for c in ["nc", "joint", "window", "off", "freeway_only", "urban_only"]:
    z = np.load(f"{S}/{c}_veh.npz")
    lf, tf, pf, sf = z["link_first"], z["t_first"], z["pos_first"], z["speed_first"]
    cache = {}
    own = []
    for l in lf.tolist():
        if l not in cache: cache[l] = owner(l)
        own.append(cache[l])
    own = np.array([o if o else "NONE" for o in own])
    v = sf / 3.6
    lag = np.where(v > 0.5, np.minimum(5.0, pf / np.maximum(v, 1e-9)), 2.5)
    T = TEND.get(c, 8100)
    res = {}
    for k in inp:
        m = own == k
        ti = np.sort(tf[m]); tl = np.sort(tf[m] - lag[m])
        IT = int(np.searchsorted(ti, T, side="right"))
        Uend = UEND[c] if k == "1099" else 0
        R = IT + Uend
        ae = Aexp(k, T)
        sc = R / ae if ae > 0 else float("nan")
        A = np.array([Aexp(k, t) for t in grid]) * sc
        I1 = np.searchsorted(ti, grid, side="right"); I2 = np.searchsorted(tl, grid, side="right")
        U1 = np.maximum(0.0, A - I1); U2 = np.maximum(0.0, A - I2)
        # 0-8100 integrals (veh.h)
        res[k] = dict(link=inp[k]["link"], inserted_le_T=IT, U_end=Uend, realized_arrivals_T=R, expected_T=round(ae, 1), scale=round(sc, 4),
                      I_8100=int(np.searchsorted(ti, 8100, side="right")),
                      int_0_8100_veh_h=float(U1.sum() / 3600), int_0_8100_lagcorr_veh_h=float(U2.sum() / 3600),
                      U_at={str(t): round(float(A[int(t) - 1] - I1[int(t) - 1]), 1) for t in (900, 1800, 2700, 3600, 4500, 5400, 6300, 7200, 8099)},
                      peak_U=round(float((A - I1).max()), 1), t_peak=float(grid[int(np.argmax(A - I1))]))
    tot1 = sum(r["int_0_8100_veh_h"] for r in res.values()); tot2 = sum(r["int_0_8100_lagcorr_veh_h"] for r in res.values())
    big = {k: r for k, r in res.items() if k in ("1098", "1099")}
    urban1 = sum(r["int_0_8100_veh_h"] for k, r in res.items() if k not in ("1098", "1099"))
    urban2 = sum(r["int_0_8100_lagcorr_veh_h"] for k, r in res.items() if k not in ("1098", "1099"))
    out[c] = dict(per_input=res, total_0_8100=tot1, total_0_8100_lag=tot2, urban_0_8100=urban1, urban_0_8100_lag=urban2,
                  native_DelayLatent_veh_h=NATIVE_DL[c] / 3600, native_window=(0, TEND.get(c, 8100)),
                  unattributed=int((own == "NONE").sum()), ambiguous=int((own == "AMBIG").sum()))
    print(f"== {c}: unattributed {out[c]['unattributed']} ambiguous {out[c]['ambiguous']} native DelayLatent(0-{TEND.get(c,8100)}) {NATIVE_DL[c]/3600:.1f} veh.h")
    for k in ("1098", "1099"):
        r = res[k]
        print(f"   {k} link {r['link']}: I(T) {r['inserted_le_T']} Uend {r['U_end']} R {r['realized_arrivals_T']} exp {r['expected_T']} scale {r['scale']} "
              f"int0-8100 {r['int_0_8100_veh_h']:.1f} (lag {r['int_0_8100_lagcorr_veh_h']:.1f}) peak {r['peak_U']}@{r['t_peak']} U@ {r['U_at']}")
    print(f"   urban 32 inputs sum: {urban1:.1f} (lag {urban2:.1f}); top:",
          sorted(((k, round(r['int_0_8100_veh_h'], 1), r['scale']) for k, r in res.items() if k not in ('1098', '1099')), key=lambda x: -x[1])[:6])
    print(f"   total 0-8100 {tot1:.1f} (lag {tot2:.1f})")
json.dump(out, open("uninserted_out.json", "w"), indent=1)
