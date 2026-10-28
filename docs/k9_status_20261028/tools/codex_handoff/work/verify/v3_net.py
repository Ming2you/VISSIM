# VERIFY: fresh network comparison 64cf vs v3c3 (inputs, static routes, DSD, DSD decisions) - read only
import xml.etree.ElementTree as ET, re, math, json
A = "D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx"
B = "D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx"
def load(p):
    return ET.parse(p).getroot()
ra, rb = load(A), load(B)
def canon(e):
    s = ET.tostring(e, encoding="unicode")
    return re.sub(r"\s+", "", s)
def items(root, tag):
    return {e.get("no"): e for e in root.iter(tag)}
# 1 vehicle inputs
ia, ib = items(ra, "vehicleInput"), items(rb, "vehicleInput")
print("vehicleInputs", len(ia), len(ib))
diff_in = [k for k in ia if k in ib and canon(ia[k]) != canon(ib[k])]
print("inputs differing:", diff_in, "only64cf", set(ia) - set(ib), "onlyv3c3", set(ib) - set(ia))
def vols(e):
    return [(v.get("timeInt"), float(v.get("volume")), v.get("vehComp"), v.get("volType")) for v in e.iter("timeIntervalVehVolume")]
for k in ["1098", "1099"]:
    print(k, "64cf", vols(ia[k]))
    print(k, "v3c3", vols(ib[k]))
va, vb = vols(ia["1099"]), vols(ib["1099"])
print("1099 ratio 64cf/v3c3 per interval", [round(x[1] / y[1], 3) for x, y in zip(va, vb)])
print("1099/1098 in 64cf", [round(x[1] / y[1], 4) for x, y in zip(va, vols(ia["1098"]))])
def total_0_8100(vl):
    starts = [int(v[0].split()[1]) / 1000 for v in vl] + [8100]
    return sum(v[1] * (starts[i + 1] - starts[i]) / 3600 for i, v in enumerate(vl))
print("1099 nominal 0-8100: 64cf", round(total_0_8100(va), 1), "v3c3", round(total_0_8100(vb), 1), "ratio", round(total_0_8100(va) / total_0_8100(vb), 3))
# 2 static routing decisions
da, db = items(ra, "vehicleRoutingDecisionStatic"), items(rb, "vehicleRoutingDecisionStatic")
print("static decisions", len(da), len(db), "only v3c3", sorted(set(db) - set(da), key=int), "only 64cf", sorted(set(da) - set(db), key=int))
dd = sorted([k for k in da if k in db and canon(da[k]) != canon(db[k])], key=int)
print("content differs", len(dd), dd)
def routes(dec):
    return {r.get("no"): (r.get("destLink"), float(r.get("destPos")), r.get("relFlow")) for r in dec.iter("vehicleRouteStatic")}
cat = {}
for k in dd:
    a, b = da[k], db[k]
    ka = []
    if (a.get("link"), a.get("pos")) != (b.get("link"), b.get("pos")):
        ka.append("decision_pos")
    rA, rB = routes(a), routes(b)
    if {n: x[2] for n, x in rA.items()} != {n: x[2] for n, x in rB.items()}:
        ka.append("relFlow")
    if {n: (x[0], round(x[1], 3)) for n, x in rA.items()} != {n: (x[0], round(x[1], 3)) for n, x in rB.items()}:
        ka.append("dest")
    cat[k] = "+".join(ka) or "other"
print("diff categories", cat)
# bypass: routes of other decisions ending on the same link beyond decision pos
def bypass(dec):
    out = {}
    for k, d in dec.items():
        L, p = d.get("link"), float(d.get("pos"))
        hits = []
        for k2, d2 in dec.items():
            if k2 == k:
                continue
            for n, (dl, dp, rf) in routes(d2).items():
                if dl == L and dp > p + 1e-6:
                    hits.append(f"{k2}:{n}")
        if hits:
            out[k] = hits
    return out
ba, bb = bypass(da), bypass(db)
print("bypass 64cf", {k: v for k, v in ba.items()})
print("bypass v3c3", {k: v for k, v in bb.items()})
common = {k: sorted(set(ba.get(k, [])) & set(bb.get(k, []))) for k in set(ba) | set(bb)}
common = {k: v for k, v in common.items() if v}
print("bypass common", common)
na = {k: [h for h in v if h not in common.get(k, [])] for k, v in ba.items()}
na = {k: v for k, v in na.items() if v}
nb = {k: [h for h in v if h not in common.get(k, [])] for k, v in bb.items()}
nb = {k: v for k, v in nb.items() if v}
print("bypass excl. common: 64cf decisions", len(na), "routes", sum(len(v) for v in na.values()), sorted(na, key=int))
print("bypass excl. common: v3c3 decisions", len(nb), "routes", sum(len(v) for v in nb.values()))
# 3 desired speed distributions
sa, sb = items(ra, "desSpeedDistribution"), items(rb, "desSpeedDistribution")
print("DSD dists", len(sa), len(sb), "only v3c3", sorted(set(sb) - set(sa)), "only 64cf", sorted(set(sa) - set(sb)))
print("DSD differ", [k for k in sa if k in sb and canon(sa[k]) != canon(sb[k])])
def pts(e):
    return [(float(p.get("x")), float(p.get("fx"))) for p in e.iter("speedDistributionDataPoint")]
def stats(pp):
    # piecewise-linear CDF mean and quantiles
    mean = sum((x1 + x0) / 2 * (f1 - f0) for (x0, f0), (x1, f1) in zip(pp, pp[1:]))
    def q(a):
        for (x0, f0), (x1, f1) in zip(pp, pp[1:]):
            if f1 >= a and f1 > f0:
                return x0 + (a - f0) / (f1 - f0) * (x1 - x0)
    return round(mean, 2), [round(q(a), 1) for a in (0.05, 0.5, 0.95)]
for k in ["110"]:
    print("DSD110 64cf", pts(sa[k]), stats(pts(sa[k])))
    print("DSD110 v3c3", pts(sb[k]), stats(pts(sb[k])))
# 4 desired speed decisions
ea, eb = items(ra, "desSpeedDecision"), items(rb, "desSpeedDecision")
print("DSD decisions", len(ea), len(eb))
dpos = [k for k in ea if k in eb and canon(ea[k]) != canon(eb[k])]
print("DSD decisions differing", dpos)
for k in dpos:
    print(k, "64cf", ea[k].get("lane"), ea[k].get("pos"), "| v3c3", eb[k].get("lane"), eb[k].get("pos"))
la, lb = items(ra, "link"), items(rb, "link")
for side, L in [("64cf", la), ("v3c3", lb)]:
    c = L["10613"]
    print(side, "connector 10613 from", c.find("fromLinkEndPt").get("lane"), c.find("fromLinkEndPt").get("pos"))
print("links", len(la), len(lb), "links differing", sum(1 for k in la if k in lb and canon(la[k]) != canon(lb[k])))
# vehicle compositions used by 1098/1099
for k in ["1098", "1099"]:
    print(k, "vehComp 64cf", {v[2] for v in vols(ia[k])}, "v3c3", {v[2] for v in vols(ib[k])})
