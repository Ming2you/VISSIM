import json, numpy as np, collections
S = "scan"
inp = json.load(open("inputs_64cf.json", encoding="utf-8"))
link2in = {int(v["link"]): k for k, v in inp.items()}
for c in ["nc", "joint", "lnc"]:
    z = np.load(f"{S}/{c}_veh.npz")
    lf = z["link_first"]; tf = z["t_first"]; pf = z["pos_first"]
    m = np.isin(lf, list(link2in))
    print(c, "veh", len(lf), "first on input link", int(m.sum()), "elsewhere", int((~m).sum()))
    cnt = collections.Counter(lf[~m].tolist()).most_common(15)
    print("   elsewhere top:", cnt)
    # first seen at t<=0? and pos distribution on input links
    print("   pos_first on input links: p50 %.1f p95 %.1f max %.1f" % tuple(np.percentile(pf[m], [50, 95, 100])))
    el = ~m
    if el.sum():
        print("   elsewhere t range", tf[el].min(), tf[el].max(), "pos p50", np.median(pf[el]))
