# VERIFY: independent recount of the NC side (0-8100) from the LOCAL bit-identical 64cf-s29 NC FZP (read only).
# Own implementation (not codex check_fzp.py): per-frame link counts, trapezoid from empty t=0, hold last frame to 8100.
import json, collections, time
F = "D:/VISSIM_runs/vsl_repro_s29/none/run/vissim_eval/vsl_seed29_none_001.fzp"
E = "D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/handoff/evidence"
inside = set(map(int, json.load(open(f"{E}/omega_membership_exact.json", encoding="utf-8"))["inside_links"]))
S7 = {74, 10699, 2, 10613, 119, 10702, 24}
S19 = S7 | {10484, 10490, 10639, 10681, 10481, 10483, 10643, 10682, 129, 31, 68, 70}
END = 8100.0
t0 = time.time()
area = collections.defaultdict(float)
prev_t, prev = 0.0, {}
cur_t, cur = None, collections.Counter()
rows = 0
frames = 0
def commit(t, counts):
    global prev_t, prev, frames
    dt = t - prev_t
    for k in set(prev) | set(counts):
        area[k] += (prev.get(k, 0) + counts.get(k, 0)) * dt / 2 / 3600
    prev_t, prev = t, dict(counts)
    frames += 1
with open(F, "rb") as fh:
    for raw in fh:
        if not raw[:1].isdigit():
            continue
        p = raw.split(b";", 3)
        t = float(p[0])
        if t > END:
            break
        if cur_t is not None and t != cur_t:
            commit(cur_t, cur)
            cur = collections.Counter()
        cur_t = t
        cur[int(p[2])] += 1
        rows += 1
commit(cur_t, cur)
for k, n in prev.items():
    area[k] += n * (END - prev_t) / 3600
res = dict(rows=rows, frames=frames, last_sec=prev_t, FW_E_7=sum(area[k] for k in S7), local_19=sum(area[k] for k in S19),
           Omega701=sum(v for k, v in area.items() if k in inside), whole=sum(area.values()))
res["outside_b"] = res["whole"] - res["Omega701"]
ifc = json.load(open(f"{E}/independent_fzp_counts.json", encoding="utf-8"))["nc"]
cmp = {k: (round(res[k], 6), round(ifc[j], 6), round(res[k] - ifc[j], 9)) for k, j in
       [("FW_E_7", "FW_E_7"), ("local_19", "local_19"), ("Omega701", "Omega701"), ("whole", "whole_observed")]}
print("scan sec", round(time.time() - t0, 1), "rows", rows, "codex rows", ifc["rows"], "frames", frames, "codex frames", ifc["frames"], "last", prev_t)
print(json.dumps(cmp, indent=1))
json.dump(dict(res=res, cmp=cmp), open(
    "C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/verify/v8_nc_fzp.json", "w"), indent=1)
