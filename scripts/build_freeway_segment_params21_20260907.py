# -*- coding: utf-8 -*-
"""21셀 격자 세그먼트별 METANET 파라미터 산출 (schema freeway_segment_params_v1, 2026-09-07).

용량 앵커 규칙 — `q_cap = max(적합 봉우리, 관측 최대 지속유량)`.
  왜. 두 추정치가 서로 반대 방향으로 치우친다(2026-09-07 실측).
   · 평지 셀(E S2~S7)은 **자기 용량으로 흐른 적이 없다**. 자유류 아니면 하류 램프 병목이 밀어올린
     스필백 큐 둘 중 하나뿐이라, 적합은 두 가지 사이를 보간해 봉우리를 만든다. 관측 최대/적합 = 0.62~0.80.
     이 셀들은 이 망에서 구속한 적이 없으므로 적합값을 그대로 둔다(관측 최대는 하한일 뿐이다).
   · 병목 셀(E S8/S9)은 반대로 표본 대부분이 큐 안이라 적합이 **과소**하다. S9 는 적합 766 대 관측 1189
     (1.55배). 관측된 지속 방류율은 용량의 하한이므로 그쪽을 쓴다.
  k_crit 은 그 용량이 나오도록 되푼다: k_crit = q_cap / (v_free · exp(-1/a)).

식별 불가(병목 하류) 셀은 같은 차로수 평지 대표 형상 + 그 셀의 저밀도 실측 v_free 를 쓴다.
사용: python build_freeway_segment_params21_20260907.py <fit21_json> <split_json> <out_json>
"""
import collections
import csv
import io
import json
import math
import sys
import datetime

import numpy as np

SRC = "outputs/fd_ver2_20260907/fd21_samples_%s.csv"
LEVELS = ["x04", "x08", "x12", "x15", "x18"]
WIN_FRAMES = 60          # 300 s
PLAIN_KEYS = {4: [("FW_E", i) for i in range(2, 8)], 3: [("FW_W", i) for i in range(1, 5)]}


def main():
    fitj, splitj, outj = sys.argv[1], sys.argv[2], sys.argv[3]
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    fit = json.load(io.open(fitj, encoding="utf-8"))
    split = json.load(io.open(splitj, encoding="utf-8"))
    ramps = collections.defaultdict(list)
    for r in split["on_ramps"]:
        ramps[(r["direction"], r["segment_index"])].append("ON " + r["name"])
    for r in split["off_ramps"]:
        ramps[(r["direction"], r["segment_index"])].append("OFF " + r["name"])

    D = collections.defaultdict(lambda: collections.defaultdict(list))
    for tag in LEVELS:
        for r in csv.DictReader(io.open(SRC % tag, encoding="utf-8")):
            D[(r["dir"], int(r["seg"]))][tag].append(
                (float(r["t"]), int(r["cross"]) + int(r["leave"]), float(r["lanes"])))

    def observed_capacity(key):
        """관측 최대 지속유량 = 300 s 창 유량의 상위 5% 평균 [veh/h/lane]. 단발 첨두가 아니라 지속값."""
        vals = []
        for tag in LEVELS:
            rows = sorted(D[key][tag])
            lanes = rows[0][2]
            for i in range(0, len(rows) - WIN_FRAMES + 1, 6):
                blk = rows[i:i + WIN_FRAMES]
                vals.append(sum(b[1] for b in blk) * 12.0 / lanes)
        vals.sort(reverse=True)
        top = vals[:max(1, len(vals) // 20)]
        return float(np.mean(top))

    plain = {}
    for lanes, keys in PLAIN_KEYS.items():
        vf = float(np.median([fit["%s_S%d" % k]["v_free"] for k in keys]))
        kc = float(np.median([fit["%s_S%d" % k]["rho_crit"] for k in keys]))
        a = float(np.median([fit["%s_S%d" % k]["metanet_a_m"] for k in keys]))
        plain[lanes] = {"v_free": vf, "rho_crit": kc, "metanet_a_m": a,
                        "q_cap": kc * vf * math.exp(-1.0 / a), "n_cells": len(keys)}
        print("평지 %d차로 대표 (셀 %d개 중앙값): v_free %.1f · k_crit %.1f · a %.2f · q_cap %.0f"
              % (lanes, len(keys), vf, kc, a, plain[lanes]["q_cap"]))

    out = {}
    print("\n%-10s %-4s %-9s %8s %8s %8s | %7s %7s %6s | %s"
          % ("셀", "차로", "출처", "적합q", "관측q", "채택q", "v_free", "k_crit", "a", "램프"))
    for dr in ("FW_E", "FW_W"):
        for s in range(21):
            key = (dr, s)
            rec = fit["%s_S%d" % key]
            lanes = int(rec["lanes"])
            base = plain[lanes]
            q_obs = observed_capacity(key)
            # 적합이 최적화 경계에 붙은 셀은 퇴화다(k_crit 상한 90 / 하한 5). 급 형상으로 되돌린다.
            # 퇴화 판정: k_crit(5~90) · v_free(80~140) · a(0.6~6) 어느 경계에든 붙으면 급 형상으로 되돌린다.
            degenerate = bool(rec.get("identifiable")) and not (
                6.0 < float(rec.get("rho_crit", 0.0)) < 88.0
                and 82.0 < float(rec.get("v_free", 0.0)) < 138.0
                and 0.7 < float(rec.get("metanet_a_m", 0.0)) < 5.8)
            if rec.get("identifiable") and not degenerate:
                vf, a = float(rec["v_free"]), float(rec["metanet_a_m"])
                q_fit = float(rec["q_cap"])
                origin = "셀 적합"
            else:
                # 퇴화 기각이면 v_free 도 못 믿는다(경계에 붙은 값이다) → 그 셀의 저밀도 실측 속도로 되돌린다.
                vf = float(rec.get("v_free_meas", rec["v_free"])) if degenerate else float(rec["v_free"])
                a = float(base["metanet_a_m"])
                q_fit = float(base["rho_crit"]) * vf * math.exp(-1.0 / a)
                origin = "급형상(퇴화기각)" if degenerate else "급형상"
            q_use = max(q_fit, q_obs)
            anchored = q_use > q_fit + 1e-9
            kc = q_use / max(vf * math.exp(-1.0 / a), 1e-9)
            out["%s_S%d" % key] = {
                "class": rec["class"] if "class" in rec else "", "lanes": float(lanes),
                "v_free": round(vf, 2), "rho_crit": round(kc, 2), "metanet_a_m": round(a, 3),
                "q_cap_veh_h_lane": round(q_use, 1),
                "q_cap_fit": round(q_fit, 1), "q_cap_observed_sustained": round(q_obs, 1),
                "capacity_anchored_to_observed": bool(anchored),
                "v_free_meas": round(float(rec.get("v_free_meas", vf)), 2),
                "origin": origin + (" + 관측 용량 앵커" if anchored else ""),
                "ramps": " · ".join(ramps.get(key, [])),
            }
            print("%-10s %-4d %-9s %8.0f %8.0f %8.0f | %7.1f %7.1f %6.2f | %s%s"
                  % ("%s_S%d" % key, lanes, origin, q_fit, q_obs, q_use, vf, kc, a,
                     " · ".join(ramps.get(key, [])), "  ←앵커" if anchored else ""))

    doc = {"schema": "freeway_segment_params_v1", "generated": datetime.date.today().isoformat(),
           "aggregation_sec": 150.0, "grid": {"segments_per_link": 21, "segment_length_km": {"FW_E": 0.513525, "FW_W": 0.513357}},
           "source_fit": fitj, "source_split": splitj, "levels": LEVELS,
           "plain_class": {str(k): v for k, v in plain.items()},
           "definition": "21셀 격자 세그먼트별 METANET FD 파라미터. 어댑터가 freeway.segment_params 로 읽어 "
                         "cfg.network.freeway_segment_params[model_link][segment_index] 로 싣는다. "
                         "용량 = max(적합 봉우리, 300 s 관측 최대 지속유량), k_crit 은 그 용량에서 되푼 값.",
           "segments": out}
    io.open(outj, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
    n_anchor = sum(1 for v in out.values() if v["capacity_anchored_to_observed"])
    print("\n세그먼트 %d개 · 관측 용량으로 앵커된 셀 %d개 → %s" % (len(out), n_anchor, outj))


if __name__ == "__main__":
    main()
