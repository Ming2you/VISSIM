# Recompute local_ramp_arrival_forecast for each joint decision from state_<t>.json ramp_counts:
# fallback formula (runtime keys RM_C* not in R_* tables): v = clamp(max(120, count*3600/120), 0, 900)
# table formula (if keys had matched, group mapping R_D_W etc.): v = clamp(max(120, count*3600/drain_g), 0, max_g)
import json, glob, os, re
D = "D:/VISSIM_runs/20261026_codex_b_v3c3/s43/sdmpc/decisions_sdmpc31_sdmpc9000_s43"   # [B copy 2026-10-26 KST, COMPARE_RULE_B: path constants only; seed v3c3-s43; slot "nc" = NC3, "joint" = B] 
GROUP = {"RM_C10480": "R_D_W", "RM_C10482": "R_D_W", "RM_C10646": "R_F_W", "RM_C10644": "R_F_W",
         "RM_C10639": "R_F_E", "RM_C10681": "R_F_E", "RM_C10490": "R_D_E", "RM_C10484": "R_D_E"}
DRAIN = {"R_D_W": 33.5, "R_F_W": 77.2, "R_D_E": 30.7, "R_F_E": 6.5}
MAXV = {"R_D_W": 865.0, "R_F_W": 1394.0, "R_D_E": 1079.0, "R_F_E": 638.0}
rows = []
for f in sorted(glob.glob(f"{D}/action_*.json")):
    m = re.search(r"action_(\d+)\.json$", f)
    if not m: continue
    t = int(m.group(1))
    if t < 900: continue
    st = json.load(open(f"{D}/state_{t:06d}.json", encoding="utf-8"))
    rc = st.get("ramp_counts", {})
    act = json.load(open(f, encoding="utf-8"))
    md = act.get("metadata", {})
    tot = md.get("forecast_ramp_arrival_total_vph")
    fb = tb = 0.0
    keys = sorted(k for k in rc)
    for r in GROUP:
        c = max(0.0, float(rc.get(r, 0.0)))
        if c > 0:
            fb += min(900.0, max(120.0, c * 30.0))
            g = GROUP[r]; tb += min(MAXV[g], max(120.0, c * 3600.0 / DRAIN[g]))
    rows.append((t, tot, round(fb, 3), round(tb, 3), {k: rc[k] for k in keys}))
    print(t, "logged", tot, "fallback-recalc", round(fb, 1), "table-recalc", round(tb, 1), "ramp_counts", {k: rc[k] for k in keys})
json.dump(rows, open("ramp_fc_out.json", "w"), indent=0)
