# codex-PC decision wall times from runlog CONTROLLER_DECISION lines (VBS-measured) + decision_budget.json wall_sec (python-measured)
import re, json, glob, os, statistics as stt
R = "D:/VISSIM_handoff/20261024/raw"
ARMS = {"joint": "D:/VISSIM_runs/20261026_codex_b_v3c3/s31/sdmpc"}   # [B copy 2026-10-26 KST, COMPARE_RULE_B: path constants only; seed v3c3-s31; slot "nc" = NC3, "joint" = B] 
out = {}
pat = re.compile(r"^CONTROLLER_DECISION sim_sec=(\d+) wall_sec=([\d.]+) result=(\S+)")
for a, d in ARMS.items():
    rl = glob.glob(f"{d}/runlog_*.txt")[0]
    rows = []
    held = []
    for line in open(rl, encoding="utf-8", errors="replace"):
        m = pat.match(line)
        if m: rows.append((int(m.group(1)), float(m.group(2)), m.group(3)))
        if line.startswith("DECISION_HELD_PREVIOUS"): held.append(line.split()[1])
    dec = [r for r in rows if r[0] >= 900]
    w = [r[1] for r in dec]
    budget = {}
    for f in glob.glob(f"{d}/decisions_*/action_*.decision_budget.json"):
        t = int(re.search(r"action_(\d+)\.decision_budget", f).group(1))
        try: budget[t] = json.load(open(f, encoding="utf-8")).get("wall_sec")
        except Exception: pass
    bw = [v for t, v in budget.items() if t >= 900 and v is not None]
    out[a] = dict(n_decisions_ge900=len(dec), results=sorted({r[2] for r in dec}), wall=dict(
        mean=round(stt.mean(w), 1) if w else None, median=round(stt.median(w), 1) if w else None,
        max=max(w) if w else None, min=min(w) if w else None, gt1800=sum(x > 1800 for x in w), gt360=sum(x > 360 for x in w)),
        budget_wall=dict(n=len(bw), mean=round(stt.mean(bw), 1) if bw else None, max=round(max(bw), 1) if bw else None),
        held=held, per_decision=[(r[0], r[1], r[2]) for r in dec])
    print(a, json.dumps({k: v for k, v in out[a].items() if k != "per_decision"}))
json.dump(out, open("walltimes_out.json", "w"), indent=1)
print("joint per-decision:", [(t, w) for t, w, _ in out["joint"]["per_decision"]])
