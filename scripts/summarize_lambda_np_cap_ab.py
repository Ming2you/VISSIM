# -*- coding: utf-8 -*-
"""probe_lambda_np_cap_20260901.py 산출을 표로 요약한다."""
import json
import sys
from pathlib import Path

p = Path(sys.argv[1] if len(sys.argv) > 1
         else "outputs/lambda_np_cap_ab_canon_farbn_d00_x18_20260901.json")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = json.loads(p.read_text(encoding="utf-8"))
print("run=%s  결정 %d개  caps=%s" % (d["run"], len(d["rows"]), d["caps"]))
hdr = ("%-4s %-9s %-24s %9s %9s %10s %8s %8s %10s %9s %9s %7s %7s"
       % ("idx", "cap", "λ path", "Σnin", "ΔΣnin", "realN_P*", "resid", "greenL1",
          "objTotal", "objBase", "Δobj", "best", "2nd"))
print(hdr)
for r in d["rows"]:
    print("-- idx %d t=%.0f  디스크: Σnin=%.3f N_P*=%.3f best_idx=%.0f obj=%.4f · "
          "재생(cap10) green L1 vs 디스크=%.3f"
          % (r["index"], r["sim_sec"], r["disk_sum_nin"], r["disk_realized_N_P"],
             r["disk_best_index"], r["disk_obj_total"],
             r["replay_cap10_green_L1_vs_disk"]))
    for a in r["arms"]:
        print("%-4d %-9g %-24s %9.3f %9.3f %10.3f %8.1f %8.4f %10.4f %9.4f %9.4f %7.0f %7.0f"
              % (r["index"], a["cap"], a["lam_path"], a["sum_nin"],
                 a["sum_nin_delta_vs_cap10"], a["realized_N_P"], a["residual_N_P"],
                 a["green_L1_vs_cap10"], a["obj_total"], a["obj_base"],
                 a["obj_delta_vs_cap10"], a["best_index"], a["second_index"]))
        print("      far: total=%.3f urban=%.3f main=%.3f ramp=%.3f | dens=%.4f mfd=%.4f "
              "rampQ=%.4f | pdIter=%.0f exit=%.0f resid=%.3f | rampL1=%.4f vslL1=%.4f"
              % (a["far_matched_total"] or 0.0, a["far_matched_urban"] or 0.0,
                 a["far_matched_mainline"] or 0.0, a["far_matched_ramp"] or 0.0,
                 a["obj_density_penalty"], a["obj_mfd_storage_penalty"],
                 a["obj_ramp_queue_penalty"], a["pd_iters"], a["pd_exit"],
                 a["pd_residual"], a["ramp_L1_vs_cap10"], a["vsl_L1_vs_cap10"]))
    # -250 후보의 첫 solve 를 팔 사이에서 직접 대조(동일 지점 비교)
    print("   [-250 후보의 첫 solve]")
    for a in r["arms"]:
        s = next((x for x in a["solves"]
                  if x["n_p_star_in"] is not None and abs(x["n_p_star_in"] + 250.0) < 1e-6),
                 None)
        if s is None:
            print("      cap=%-9g (없음)" % a["cap"])
            continue
        print("      cap=%-9g λ=%-26s Σnin=%9.3f tgt=%9.3f feas=[%.1f,%.1f] exit=%.0f it=%.0f"
              % (a["cap"], s["lam_path"], s["sum_nin"], s["projected_target"],
                 s["feas_min"], s["feas_max"], s["pd_exit"], s["pd_iters"]))
    ref = r["arms"][0]
    s0 = next((x for x in ref["solves"] if x["n_p_star_in"] is not None
               and abs(x["n_p_star_in"] + 250.0) < 1e-6), None)
    if s0 is not None:
        for a in r["arms"][1:]:
            s = next((x for x in a["solves"] if x["n_p_star_in"] is not None
                      and abs(x["n_p_star_in"] + 250.0) < 1e-6), None)
            if s is None:
                continue
            keys = set(s0["green"]) | set(s["green"])
            l1 = sum(abs(float(s0["green"].get(k, 0.0)) - float(s["green"].get(k, 0.0)))
                     for k in keys)
            print("      cap=%-9g -250 후보 green L1 vs cap10 = %.6f" % (a["cap"], l1))
