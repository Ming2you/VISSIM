# VERIFY: fresh recount of VSL / RM / TSC actions from handoff/evidence (read only)
import csv, json, collections
E = "D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/handoff/evidence"
R = list(csv.DictReader(open(f"{E}/decision_greens.csv", encoding="utf-8-sig")))
A = json.load(open(f"{E}/action_audit.json", encoding="utf-8"))
for c in A:
    a = A[c]
    print(c, "vsl_rows", a.get("vsl_rows"), "speeds", a.get("vsl_speeds"), "readbacks", a.get("vsl_readbacks"),
          "ramp_rows", a.get("ramp_rows"), "signal_rows", a.get("signal_rows"))
# controlled DSD groups count
dsd = list(csv.DictReader(open(f"{E}/controlled_dsd_groups.csv", encoding="utf-8-sig")))
print("controlled_dsd_groups rows", len(dsd), "66x55=", 66 * 55, "66x61=", 66 * 61)
# RM per meter (joint), decisions 900..7950
def rm_table(cond):
    by = collections.defaultdict(dict)
    for r in R:
        if r["condition"] == cond and r["kind"] == "ramp_meter":
            by[r["id"]][int(float(r["sim_sec"]))] = float(r["green_sec"])
    out = {}
    for mid, ts in sorted(by.items()):
        dec = [t for t in sorted(ts) if 900 <= t <= 7950]
        vals = [ts[t] for t in dec]
        changes = sum(1 for i in range(1, len(vals)) if vals[i] != vals[i - 1])
        # count changes including from pre-900 state (10)
        pre = [ts[t] for t in sorted(ts) if t < 900]
        out[mid] = dict(n=len(dec), dist=dict(sorted(collections.Counter(vals).items())), mean=round(sum(vals) / len(vals), 2),
                        below10=sum(v < 10 for v in vals), changes=changes, pre900=sorted(set(pre)),
                        max_abs_step=max([abs(vals[i] - vals[i - 1]) for i in range(1, len(vals))] or [0]))
    return out
for cond in ["joint", "off", "window", "freeway_only", "urban_only", "nc"]:
    t = rm_table(cond)
    moved = [m for m, v in t.items() if v["below10"] > 0]
    print(f"== {cond}: meters with any green<10: {len(moved)} {moved}")
    if cond == "joint":
        for m, v in t.items():
            print("  ", m, v)
    else:
        print("   means", {m: v["mean"] for m, v in t.items()}, "max|step|", max(v["max_abs_step"] for v in t.values()))
# signals: unique plans per SC, held decisions (all 17 SC + 8 RM identical to previous decision)
def sig_state(cond):
    S = collections.defaultdict(dict)
    for r in R:
        if r["condition"] == cond and r["kind"] == "signal":
            S[int(float(r["sim_sec"]))][r["id"]] = (r["p1"], r["p2"], r["p3"], r["p4"], r["offset"])
    M = collections.defaultdict(dict)
    for r in R:
        if r["condition"] == cond and r["kind"] == "ramp_meter":
            M[int(float(r["sim_sec"]))][r["id"]] = r["green_sec"]
    return S, M
for cond in ["joint", "window", "off", "urban_only", "freeway_only"]:
    S, M = sig_state(cond)
    times = sorted(S)
    scs = sorted({sc for t in times for sc in S[t]})
    uniq = {sc: len({S[t][sc] for t in times if sc in S[t]}) for sc in scs}
    uniq_to7950 = {sc: len({S[t][sc] for t in times if sc in S[t] and t <= 7950}) for sc in scs}
    held, partial = [], []
    for i in range(1, len(times)):
        t, p = times[i], times[i - 1]
        if t > 7950:
            continue
        same_sc = sum(1 for sc in scs if S[t].get(sc) == S[p].get(sc))
        same_rm = all(M[t].get(m) == M[p].get(m) for m in M[t])
        if same_sc == len(scs) and same_rm:
            held.append(t)
        elif same_sc >= len(scs) - 3:
            partial.append((t, same_sc, "rm_same" if same_rm else "rm_changed"))
    print(f"== {cond}: n_times={len(times)} first={times[0]} last={times[-1]} n_SC={len(scs)} uniq plans min/max (to 8100)={min(uniq.values())}/{max(uniq.values())} (to 7950) {min(uniq_to7950.values())}/{max(uniq_to7950.values())}")
    print("   fully held (all SC+RM same as prev):", held)
    print("   partial (>= n-3 SC same):", partial)
    if cond == "joint":
        # offsets changed count and green sums
        ch = tot = 0
        for i in range(1, len(times)):
            for sc in scs:
                a, b = S[times[i]].get(sc), S[times[i - 1]].get(sc)
                if a and b:
                    tot += 1
                    ch += a[4] != b[4]
        print("   offset changes", ch, "of", tot)
        zero = collections.Counter()
        sums = collections.defaultdict(set)
        for t in times:
            for sc, v in S[t].items():
                g = [float(x) if x else 0.0 for x in v[:4]]
                sums[sc].add(round(sum(g), 1))
                for k, x in enumerate(g):
                    if x == 0:
                        zero[(sc, f"p{k+1}")] += 1
        print("   zero-green slots", dict(zero))
        print("   green sum sets", {sc: (sorted(s)[0], sorted(s)[-1], len(s)) for sc, s in sums.items()})
# extra: offset changes 900..7950 only, and RM_C10482 time of 9 s
S, M = sig_state("joint")
times = [t for t in sorted(S) if t <= 7950]
ch = tot = 0
for i in range(1, len(times)):
    for sc in S[times[i]]:
        a, b = S[times[i]].get(sc), S[times[i-1]].get(sc)
        if a and b:
            tot += 1; ch += a[4] != b[4]
print("joint offset changes 900..7950:", ch, "of", tot)
print("RM_C10482 9s at", [t for t in sorted(M) if M[t].get("RM_C10482") == "9.0"])
cnt2 = {m: sum(1 for t in sorted(M) if 900 <= t <= 7950 and M[t].get(m) == "2.0") for m in ["RM_C10480", "RM_C10639"]}
print("min-green 2 s counts", cnt2)
