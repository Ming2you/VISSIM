# -*- coding: utf-8 -*-
"""FD 적합 산출물 → 세그먼트별 METANET 파라미터 산출물 (schema freeway_segment_params_v1, 2026-09-07).

규칙(자료가 말하는 만큼만 쓴다):
  - 세그먼트 자체 적합이 식별 가능하고 RMSE <= rmse_max 면 그 세그먼트 값(v_free 고정 + k_crit·a).
  - 식별 불가(자유류만)면 형상(k_crit·a)은 같은 급의 대표값을 쓰고, v_free 는 그 셀의 **실측 저밀도 속도**를 쓴다.
    합류·위빙 셀의 낮은 저밀도 속도는 잡음이 아니라 그 셀의 정상상태다(2026-09-07 종단면으로 확인).
  - 자체 적합이 있어도 RMSE 가 크면(양극 체제가 섞인 셀) 급 대표값으로 되돌린다.
사용: python build_freeway_segment_params_20260907.py <fd_fit_json> <out_json> [rmse_max]
"""
import io
import json
import sys
import datetime


def main():
    src = sys.argv[1]
    out = sys.argv[2]
    rmse_max = float(sys.argv[3]) if len(sys.argv) > 3 else 8.0
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    fit = json.load(io.open(src, encoding="utf-8"))
    vf_plain = float(fit["v_free_plain_measured"])
    cls = fit["class_fit"]
    segs = {}
    print("%-10s %-12s %2s %8s %8s %7s %9s  %s" % ("seg", "class", "L", "v_free", "k_crit", "a", "q_cap", "출처"))
    for key, rec in fit["segments"].items():
        lanes = float(rec["lanes"])
        base = cls["plain4"] if lanes >= 4 else cls["plain3"]
        A = rec.get("A_vf_fixed") or {}
        own = bool(rec.get("identifiable")) and float(A.get("rmse", 1e9)) <= rmse_max
        if own:
            v_free, k_crit, a = vf_plain, float(A["k_crit"]), float(A["a"])
            origin = "세그먼트 적합 (RMSE %.2f)" % float(A["rmse"])
        else:
            k_crit, a = float(base["k_crit"]), float(base["a"])
            meas = rec.get("free_only_v_at_k_lt10")
            if meas is not None and meas == meas:
                v_free = float(meas)
                origin = "급 형상 + 저밀도 실측 v_free"
            else:
                v_free = vf_plain
                origin = "급 대표값 (RMSE %.1f 로 자체 적합 기각)" % float(A.get("rmse", float("nan")))
        import math
        q_cap = k_crit * v_free * math.exp(-1.0 / a)
        segs[key] = {"class": rec["class"], "lanes": lanes, "v_free": round(v_free, 2),
                     "rho_crit": round(k_crit, 2), "metanet_a_m": round(a, 3),
                     "q_cap_veh_h_lane": round(q_cap, 1), "origin": origin, "note": rec.get("note", "")}
        print("%-10s %-12s %2d %8.1f %8.1f %7.2f %9.0f  %s" % (key, rec["class"], lanes, v_free, k_crit, a, q_cap, origin))
    doc = {"schema": "freeway_segment_params_v1", "generated": datetime.date.today().isoformat(),
           "source_fit": src, "rmse_max": rmse_max, "v_free_plain_measured": vf_plain,
           "class_fit": cls,
           "definition": "세그먼트별 METANET FD 파라미터. 어댑터가 freeway.segment_params 로 읽어 "
                         "cfg.network.freeway_segment_params[model_link][segment_index] 로 싣는다. "
                         "q_cap_veh_h_lane 은 진단용(모형은 v_free·rho_crit·a 만 쓴다).",
           "segments": segs}
    io.open(out, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print("\n세그먼트 %d개 → %s" % (len(segs), out))


if __name__ == "__main__":
    main()
