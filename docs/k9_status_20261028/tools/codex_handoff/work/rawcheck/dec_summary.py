import json, collections, statistics as st, sys
arm = sys.argv[1] if len(sys.argv) > 1 else "joint"
rows = json.load(open(f"dec_{arm}.json"))
fresh = [r for r in rows if r["controller_status"] == "ok" and r["t"] <= 7950]
print(arm, "decisions>=900:", len(rows), "fresh<=7950:", len(fresh), "status counts", collections.Counter(r["controller_status"] for r in rows))
# VSL
allv = []
for r in fresh:
    pass
nv = sum(r["vsl_rows"] for r in fresh)
pos_sig = [(r["t"], x) for r in fresh for x in r.get("vsl_pos_rows", []) if x[2] > 1e-9]
print("VSL rows total", nv, "methods", collections.Counter(k for r in fresh for k in (r.get("vsl_methods") or {}) for _ in range(r["vsl_methods"][k])))
print("VSL rows with total>1e-9:", pos_sig)
print("VSL total max over all:", max((r.get("vsl_total_max", -9) for r in fresh)), "min:", min((r.get("vsl_total_min", 9) for r in fresh)))
print("rows with total >= 0.4545 (needed for a 10 km/h step at prox 10):", sum(r.get("vsl_pos_ge_step_thr_times_prox", 0) for r in fresh))
big = [(r["t"], s) for r in fresh for s in r["vsl_nonzero_local_steps"] if abs(s[5]) > 1e-9]
print("VSL local steps |s|>1e-9:", big)
print("vsl outputs:", collections.Counter(tuple(r["vsl_out"]) for r in rows))
print("vsl allowed block0 sets:", collections.Counter(str(r.get("vsl_allowed_block0")) for r in fresh))
# candidates
st_c = collections.Counter(c[2] for r in fresh for c in r["candidates"])
print("cap candidates per decision:", collections.Counter(len(r["candidates"]) for r in fresh), "statuses", st_c)
print("selection_status:", collections.Counter(r["selection_status"] for r in fresh), "converged:", collections.Counter(r["converged"] for r in fresh))
red = [r["prediction_ttt_reduction"] for r in fresh if r["prediction_ttt_reduction"] is not None]
print("prediction_ttt_reduction (held - selected) veh.h: mean %.3f median %.3f min %.3f max %.3f" % (st.mean(red), st.median(red), min(red), max(red)))
# audit
sel = collections.Counter(r["audit_selected"] for r in fresh)
print("audit performed:", collections.Counter(r["audit_performed"] for r in fresh), "selected:", sel)
dsel = []
for r in fresh:
    d = {c[0]: c[2] for c in r["audit_candidates"]}
    dsel.append((r["t"], r["audit_selected"], d.get(r["audit_selected"])))
print("selected audit candidate delta (veh.h) by decision:", dsel)
neg = [x[2] for x in dsel if x[2] is not None and x[2] < 0]
print("decisions where audit chose a candidate with delta<0:", len(neg), "sum", round(sum(neg), 3), "min", min(neg) if neg else None)
print("candidates per decision (incl. multiple budgets):", collections.Counter(len(r["audit_candidates"]) for r in fresh))
print("infeasible audit candidates:", sum(1 for r in fresh for c in r["audit_candidates"] if c[1] is False))
print("additional predictions per audit:", collections.Counter(r.get("audit_additional_predictions") for r in fresh))
# guards
print("meter storage guard triggered:", [(r["t"], r["meter_guard_triggered"]) for r in fresh if r["meter_guard_triggered"]])
ug = [(r["t"], r["urban_guard_fill_ge_0_9"]) for r in fresh if r["urban_guard_fill_ge_0_9"]]
print("urban guard fill>=0.9 decisions:", len(ug), ug[:10])
print("urban guard keys:", collections.Counter(str(r["urban_guard_keys"]) for r in fresh))
# rm outputs
greens = collections.defaultdict(list)
for r in rows:
    for k, v in (r["rm_green"] or {}).items(): greens[k].append(v)
print("rw_meter_green values per meter:", {k: dict(collections.Counter(v)) for k, v in greens.items()})
