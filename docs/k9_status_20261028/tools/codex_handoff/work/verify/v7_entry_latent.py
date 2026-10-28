# VERIFY: forward reconstruction of latent queues at both freeway entries (1098 link 74, 1099 link 26), local NC (read only)
import bisect, math, json
F = "D:/VISSIM_runs/vsl_repro_s29/none/run/vissim_eval/vsl_seed29_none_001.fzp"
D98 = [(0, 7096.32), (900, 10137.6), (1800, 10644.48), (2700, 9123.84), (3600, 7096.32), (4500, 5068.8)]
D99 = [(0, 8870.4), (900, 12672.0), (1800, 13305.6), (2700, 11404.8), (3600, 8870.4), (4500, 6336.0)]
seen = set(); first = {b"26": [], b"74": []}
with open(F, "rb") as fh:
    for raw in fh:
        if not raw[:1].isdigit():
            continue
        p = raw.split(b";", 3)
        if p[1] in seen:
            continue
        seen.add(p[1])
        if p[2] in first:
            first[p[2]].append(float(p[0]))
for k in first: first[k].sort()
def A(D, t):
    s = 0.0
    for i, (st, q) in enumerate(D):
        en = D[i + 1][0] if i + 1 < len(D) else 1e9
        if t > st: s += q / 3600 * (min(t, en) - st)
    return s
out = {}
for name, D, key, Uend in [("1098", D98, b"74", 0), ("1099", D99, b"26", 10857)]:
    I = first[key]
    real = len(I) + Uend
    sc = real / A(D, 9000)
    Ut = lambda t: A(D, t) * sc - bisect.bisect_right(I, t)
    integ = sum(max(0.0, Ut(t + 0.5)) for t in range(9000)) / 3600
    integ8100 = sum(max(0.0, Ut(t + 0.5)) for t in range(8100)) / 3600
    peak = max((Ut(t), t) for t in range(0, 9000, 30))
    out[name] = dict(first_seen=len(I), expected_0_9000=round(A(D, 9000), 1), realized_0_9000=real, scale=round(sc, 4),
                     U_at={t: round(Ut(t), 0) for t in (1800, 3600, 4500, 5400, 6300, 7200, 8100, 9000)},
                     peak=(round(peak[0]), peak[1]), integral_0_9000_veh_h=round(integ, 1), integral_0_8100_veh_h=round(integ8100, 1))
print(json.dumps(out, indent=1))
print("sum of both integrals 0-9000", round(out["1098"]["integral_0_9000_veh_h"] + out["1099"]["integral_0_9000_veh_h"], 1), "native 19290.0")
