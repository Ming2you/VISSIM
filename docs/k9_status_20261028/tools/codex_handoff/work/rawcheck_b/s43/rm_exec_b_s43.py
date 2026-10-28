# RM execution check: commanded green_sec (action CSV, held for 150 s) vs LDP green seconds per 150-s interval / 15 cycles.
import csv, re, json, collections
R = "D:/VISSIM_runs/20261026_codex_b_v3c3"   # [B copy 2026-10-26 KST, COMPARE_RULE_B: path constants only; seed v3c3-s43; slot "nc" = NC3, "joint" = B] 
MAP = {}
out = {}
for a in ["s43"]:
    rows = [r for r in csv.DictReader(open(f"{R}/{a}/sdmpc/action_sdmpc31_sdmpc9000_s43.csv", encoding="utf-8-sig")) if r["kind"] == "ramp_meter"]
    cmd = collections.defaultdict(dict)
    for r in rows:
        cmd[r["sc_no"]][float(r["sim_sec"])] = (float(r["green_sec"]), r["id"])
    res = {}
    for sc, d in cmd.items():
        g = {}
        for raw in open(f"{R}/{a}/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s43_{sc}_001.ldp", "rb"):
            s = raw.decode("latin-1").rstrip("\r\n")
            m = re.match(r"^\s*(\d+\.\d)\s+(\d+\.\d)(.*)$", s)
            if m: g[float(m.group(1))] = m.group(3)[:1]
        mism = 0; n = 0; worst = []
        for t0 in sorted(d):
            if t0 < 900 or t0 >= 8100: continue
            cg = d[t0][0]
            secs = [g.get(t0 + k + 1.0, "?") for k in range(150)]
            green = sum(1 for c in secs if c == "I")
            per_cycle = green / 15.0
            n += 1
            if abs(per_cycle - cg) > 0.5:
                mism += 1; worst.append((t0, cg, round(per_cycle, 2)))
        res[sc] = dict(id=list(d.values())[0][1], intervals=n, mismatches=mism, examples=worst[:5])
    out[a] = res
    print(a, {v["id"]: (v["intervals"], v["mismatches"], v["examples"][:2]) for v in res.values()})
json.dump(out, open("rm_exec_out.json", "w"), indent=1)
