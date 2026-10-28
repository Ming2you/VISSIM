# Compare per-second signal display states (LDP) between each arm and NC, 0-8100 s, for every SC with an LDP file.
import glob, re, json, os
R = "D:/VISSIM_handoff/20261024/raw"
def load(p):
    rows = {}
    for raw in open(p, "rb"):
        s = raw.decode("latin-1").rstrip("\r\n")
        m = re.match(r"^\s*(\d+\.\d)\s+(\d+\.\d)(.*)$", s)
        if m:
            t = float(m.group(1))
            if t <= 8100: rows[t] = (m.group(2), m.group(3))
    return rows
nc = {re.search(r"_s29_(\d+)_001\.ldp$", p).group(1): load(p) for p in glob.glob(f"{R}/nc/vissim_eval/*_001.ldp")}
CTRL = ["1", "5", "6", "7", "11", "12", "16", "101", "105", "107", "108", "109", "1001", "1002", "1003", "1004", "1005"]
out = {}
for a in ["joint", "window", "off", "freeway_only", "urban_only"]:
    res = {}
    for p in glob.glob(f"{R}/{a}/sdmpc/vissim_eval/*_001.ldp"):
        sc = re.search(r"_s29_(\d+)_001\.ldp$", p).group(1)
        x = load(p); y = nc.get(sc, {})
        ts = sorted(set(x) & set(y))
        st_diff = [t for t in ts if x[t][1] != y[t][1]]
        cy_diff = [t for t in ts if x[t][0] != y[t][0]]
        res[sc] = dict(n=len(ts), state_diff_sec=len(st_diff), first_state_diff=st_diff[0] if st_diff else None,
                       cycle_diff_sec=len(cy_diff), state_diff_after_900=sum(1 for t in st_diff if t > 900))
    out[a] = res
    ctrl_diff = {sc: res[sc]["state_diff_sec"] for sc in CTRL if sc in res}
    other_diff = {sc: r["state_diff_sec"] for sc, r in res.items() if sc not in CTRL and r["state_diff_sec"]}
    print(a, "LDP SCs", len(res), "| controlled SC state-diff seconds vs NC:", ctrl_diff, "| other SCs with diff:", other_diff,
          "| first diff:", min((r["first_state_diff"] for r in res.values() if r["first_state_diff"]), default=None))
json.dump(out, open("ldp_cmp_out.json", "w"), indent=1)
