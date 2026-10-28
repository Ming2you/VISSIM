# Compare native LSA (signal change protocol) event rows between arms, per SC, 0-8100 s.
import collections, hashlib, json
R = "D:/VISSIM_handoff/20261024/raw"
P = {"nc": f"{R}/nc/vissim_eval/sdmpc31_nc9000_s29_001.lsa"}
for a in ["joint", "window", "off", "freeway_only", "urban_only"]:
    P[a] = f"{R}/{a}/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.lsa"
ev = {}
for a, p in P.items():
    per = collections.defaultdict(list); n = 0; tmax = 0
    for raw in open(p, "rb"):
        s = raw.decode("latin-1").strip()
        if not s or ";" not in s: continue
        f = [x.strip() for x in s.split(";")]
        try:
            t = float(f[0])
        except ValueError:
            continue
        if t > 8100: continue
        sc = f[2]; per[sc].append(";".join(f[:6])); n += 1; tmax = max(tmax, t)
    ev[a] = per
    print(a, "rows<=8100", n, "SCs", len(per), "tmax", tmax, "first row", per[sorted(per)[0]][0] if per else None)
scs = sorted(set().union(*[set(v) for v in ev.values()]), key=lambda x: int(x) if x.isdigit() else 0)
print("SC ids in LSA:", scs)
res = {}
for a in ev:
    if a == "nc": continue
    same = [sc for sc in scs if ev[a].get(sc) == ev["nc"].get(sc)]
    diff = [sc for sc in scs if ev[a].get(sc) != ev["nc"].get(sc)]
    # first differing time for a few
    fd = {}
    for sc in diff[:40]:
        x, y = ev[a].get(sc, []), ev["nc"].get(sc, [])
        for i, (u, v) in enumerate(zip(x, y)):
            if u != v: fd[sc] = (u.split(";")[0], len(x), len(y)); break
        else: fd[sc] = ("len", len(x), len(y))
    res[a] = dict(same=same, diff=diff, first_diff=fd)
    print(f"{a}: identical to NC for {len(same)} SC, differ {len(diff)}: {diff}")
    print("   first diff (time, rows arm, rows nc):", fd)
json.dump(res, open("lsa_cmp_out.json", "w"), indent=1)
