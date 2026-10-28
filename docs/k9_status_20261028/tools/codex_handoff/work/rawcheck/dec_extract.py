# RAW_CHECK: extract VSL / RM / hold evidence from codex decision JSONs (read only). One arm per call.
import json, glob, re, sys, os, time, ctypes, collections
try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except Exception:
    pass
arm = sys.argv[1]
D = glob.glob(f"D:/VISSIM_handoff/20261024/raw/{arm}/sdmpc/decisions_*")[0]
STEP_THR = 0.5 * (10.0 / 110.0)   # half a legal 10 km/h step in scaled units
rows = []
t0 = time.time()
for f in sorted(glob.glob(f"{D}/action_*.json")):
    m = re.search(r"action_(\d+)\.json$", f)
    if not m: continue
    t = int(m.group(1))
    if t < 900: continue
    o = json.load(open(f, encoding="utf-8"))
    md = o.get("metadata", {})
    j = md.get("joint_leader_selection") or {}
    r = dict(t=t, controller_status=md.get("controller_status"), decision_wall_sec=md.get("decision_wall_sec"),
             has_joint_json=os.path.exists(f"{D}/action_{t:06d}.joint.json"),
             selection_status=j.get("selection_status"), converged=j.get("converged"),
             held_objective=j.get("held_objective"), selected_objective=j.get("selected_objective"),
             prediction_ttt_reduction=j.get("prediction_ttt_reduction"),
             candidates=[(c.get("np_cap"), c.get("nuf_target"), c.get("status"), c.get("objective")) for c in j.get("candidates", [])],
             vsl_out=sorted({v for v in (o.get("vsl") or {}).values()}),
             rm_out=o.get("ramp_metering"), rm_green={k[len("rw_meter_green_"):]: v for k, v in (o.get("diagnostics") or {}).items() if k.startswith("rw_meter_green_")})
    # VSL gradient rows
    vr = [g for g in j.get("gradient_rows", []) if g.get("kind") == "vsl"]
    r["vsl_rows"] = len(vr)
    if vr:
        tot = [g.get("total", 0.0) for g in vr]
        r["vsl_methods"] = dict(collections.Counter(f"{g.get('derivative_method')}|{g.get('fallback_reason')}" for g in vr))
        r["vsl_total_pos"] = sum(1 for x in tot if x > 0)
        r["vsl_total_zero"] = sum(1 for x in tot if x == 0)
        r["vsl_total_neg"] = sum(1 for x in tot if x < 0)
        r["vsl_total_max"] = max(tot); r["vsl_total_min"] = min(tot)
        r["vsl_own_max"] = max(g.get("own", 0) for g in vr)
        r["vsl_pos_ge_step_thr_times_prox"] = sum(1 for x in tot if x >= STEP_THR * 10.0)
        r["vsl_pos_rows"] = [(g["key"], g["block"], round(g["total"], 4), round(g["own"], 4), round(g["external"], 4)) for g in vr if g.get("total", 0) > 0]
        r["vsl_allowed_block0"] = sorted({tuple(g.get("allowed", [])) for g in vr if g.get("block") == 0})
    # local rows steps on VSL coordinates
    coords = j.get("coordinates", [])
    owner_idx = collections.defaultdict(list)
    for c in coords:
        owner_idx[c["owner"]].append(c)
    vsl_steps = []
    for lr in j.get("local_rows", []):
        ow = lr.get("owner")
        if ow in ("FW_E", "FW_W"):
            cs = owner_idx[ow]
            st = lr.get("step") or []
            for c, s in zip(cs, st):
                if c["kind"] == "vsl" and s != 0:
                    vsl_steps.append((ow, c["key"], c["block"], lr.get("cap"), lr.get("iteration"), s))
    r["vsl_nonzero_local_steps"] = vsl_steps
    # trial rows: any VSL != 110 in tried actions?
    tr = j.get("trial_rows", [])
    r["trial_rows"] = len(tr)
    r["trial_vsl_values"] = sorted({json.dumps(x.get("vsl")) for x in tr if isinstance(x, dict) and x.get("vsl")})[:5]
    r["trial_keys"] = sorted(tr[0].keys()) if tr else []
    # meter neighbor audit
    na = j.get("meter_neighbor_audit") or {}
    r["audit_performed"] = j.get("finite_neighbor_audit_performed")
    r["audit_selected"] = na.get("selected"); r["audit_baseline"] = na.get("baseline_objective")
    r["audit_keys"] = sorted(na.keys())
    r["audit_candidates"] = [(c.get("candidate"), c.get("feasible"), None if c.get("delta_veh_h") is None else round(c["delta_veh_h"], 4)) for c in na.get("candidates", [])]
    for k in na:
        if k not in ("candidates", "baseline_objective", "selected"):
            r["audit_" + k] = na[k] if not isinstance(na[k], (dict, list)) else json.dumps(na[k])[:400]
    # storage guards
    mob = (j.get("meter_operating_bounds") or {}).get("ramps", {})
    r["meter_guard_triggered"] = {k: (v.get("previous_green_sec"), v.get("minimum_green_sec")) for k, v in mob.items() if v.get("triggered")}
    ug = j.get("urban_storage_guard") or {}
    trig = []
    for sc, ph in ((ug.get("observation") or {}).get("signals") or {}).items():
        for p, val in ph.items():
            if isinstance(val, (int, float)) and val >= 0.9:
                trig.append((p, round(val, 3)))
    r["urban_guard_fill_ge_0_9"] = trig
    r["urban_guard_keys"] = sorted(ug.keys())
    r["urban_guard_applied"] = json.dumps(ug.get("applied") or ug.get("constraints") or {})[:300]
    r["forecast_ramp_arrival_total_vph"] = md.get("forecast_ramp_arrival_total_vph")
    rows.append(r)
    print(t, r["controller_status"], r["selection_status"], "vslrows", r["vsl_rows"], "pos", r.get("vsl_total_pos"), "max", r.get("vsl_total_max") and round(r["vsl_total_max"], 3),
          "steps", len(vsl_steps), "audit", r["audit_selected"], "guardE", list(r["meter_guard_triggered"]), round(time.time() - t0), flush=True)
json.dump(rows, open(f"dec_{arm}.json", "w"), indent=1)
