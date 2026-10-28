import json, glob, re, ctypes
try: ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except Exception: pass
D = "D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29"
out = []
for f in sorted(glob.glob(f"{D}/action_*.json")):
    m = re.search(r"action_(\d+)\.json$", f)
    if not m or int(m.group(1)) < 900: continue
    md = json.load(open(f, encoding="utf-8")).get("metadata", {})
    j = md.get("joint_leader_selection") or {}
    v = {k: md[k] for k in md if "10633" in k}
    blocks = (j.get("urban_storage_guard") or {}).get("blocks") or []
    ncon = sum(1 for b in blocks for x in b if x.get("status") == "constrained")
    out.append((int(m.group(1)), v, ncon))
json.dump(out, open("h10633_out.json", "w"), indent=0)
vals = [list(x[1].values())[0] for x in out if x[1]]
print("decisions", len(out), "with 10633 key", len(vals), "min/max", min(vals) if vals else None, max(vals) if vals else None)
print("distinct values", sorted(set(round(v, 3) for v in vals))[:20])
print("urban guard constrained blocks>0 in", sum(1 for x in out if x[2] > 0), "decisions; total constrained signal-blocks", sum(x[2] for x in out))
