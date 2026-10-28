# VERIFY: narrow NC 0-8100 uninserted wait (④b) with the LOCAL bit-identical 64cf-s29 NC run (read only).
# Source: D:/VISSIM_runs/vsl_repro_s29/none/run (our own 2026-09-24 reproduction; native totals equal HANDOFF NC).
# Input 1099 inserts on link 26 (entry link, only connector 10480 feeds it from a ramp), so a vehicle whose
# first FZP record is on link 26 is a 1099 insertion. U(t) = uninserted 1099 vehicles.
import json, math, time
F = "D:/VISSIM_runs/vsl_repro_s29/none/run/vissim_eval/vsl_seed29_none_001.fzp"
NATIVE_W9000_S = 69444031.2999984        # DelayLatent (s) at 9000, native_netperf.csv
U9000 = 10857                            # DemandLatent at 9000
DEM = [(0, 8870.4), (900, 12672.0), (1800, 13305.6), (2700, 11404.8), (3600, 8870.4), (4500, 6336.0)]  # 64cf 1099 veh/h
t0 = time.time()
seen = set()
first26 = []          # first-seen times of vehicles first seen on link 26
other_first = 0
frames = set()
with open(F, "rb") as fh:
    for raw in fh:
        if not raw[:1].isdigit():
            continue
        p = raw.split(b";", 3)
        no = p[1]
        if no in seen:
            continue
        seen.add(no)
        t = float(p[0])
        if p[2] == b"26":
            first26.append(t)
        else:
            other_first += 1
first26.sort()
print("scan sec", round(time.time() - t0, 1), "vehicles", len(seen), "first-on-26", len(first26), "first elsewhere", other_first)
def A_exp(t):  # expected cumulative 1099 arrivals
    s = 0.0
    for i, (st, q) in enumerate(DEM):
        en = DEM[i + 1][0] if i + 1 < len(DEM) else 1e9
        if t > st:
            s += q / 3600.0 * (min(t, en) - st)
    return s
import bisect
def I(t):
    return bisect.bisect_right(first26, t)
# sanity 1: realized arrivals deviation over 0-9000
A9000_real = I(9000) + U9000
print("A(0-9000) expected", round(A_exp(9000), 1), "realized (I+U)", A9000_real, "diff", round(A9000_real - A_exp(9000), 1),
      "poisson sd", round(math.sqrt(A_exp(9000)), 1))
# sanity 2: forward integral with expected arrivals scaled to realized total
scale = A9000_real / A_exp(9000)
dt = 1.0
fw = sum(max(0.0, A_exp(t) * scale - I(t)) * dt for t in [x + 0.5 for x in range(0, 9000)])
print("forward ∫U dt 0-9000 (scaled expected arrivals) veh·h", round(fw / 3600, 1), "native", round(NATIVE_W9000_S / 3600, 1))
# tail 8100-9000, backward from exact U(9000)
ins_tail = I(9000) - I(8100)
res = {}
for label, arr_tail in [("expected", A_exp(9000) - A_exp(8100)),
                        ("expected-2sd", A_exp(9000) - A_exp(8100) - 2 * math.sqrt(A_exp(9000) - A_exp(8100))),
                        ("expected+2sd", A_exp(9000) - A_exp(8100) + 2 * math.sqrt(A_exp(9000) - A_exp(8100)))]:
    rate = arr_tail / 900.0
    tail = 0.0
    for k in range(900):
        t = 8100 + k + 0.5
        U = U9000 - (rate * (9000 - t)) + (I(9000) - I(t))
        tail += U
    U8100 = U9000 - arr_tail + ins_tail
    nc4b = (NATIVE_W9000_S - tail) / 3600
    res[label] = dict(arrivals_8100_9000=round(arr_tail, 1), insertions_8100_9000=ins_tail, U8100=round(U8100, 1),
                      tail_veh_h=round(tail / 3600, 1), NC_4b_0_8100=round(nc4b, 1))
print(json.dumps(res, indent=1))
print("insertion rate 8100-9000 veh/h", round(ins_tail / 0.25, 1))
json.dump(dict(first26_count=len(first26), ins_tail=ins_tail, res=res), open(
    "C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/verify/v6_nc_latent.json", "w"), indent=1)
