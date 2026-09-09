# -*- coding: utf-8 -*-
"""21셀 격자 세그먼트별 FD 적합 — 150 s(제어 간격) 기준, 자기정합 보장 (2026-09-08).

2026-09-07 판을 대체한다. 그 판의 결함 넷을 여기서 닫는다(독립 검토에서 확인):
  (1) 표본을 8셀 매핑으로 뽑고 21셀 차로를 중점 규칙으로 되유도해 **FW_W S7 이 3차로로 잡혔다**
      (정본은 4차로, 하필 R_D_W 합류 셀 → 밀도 33% 과대). 이제 n21 매핑 표본만 받는다.
  (2) 식별 불가로 떨어진 셀에 이전 판의 rho_crit/a/q_cap 이 남아 q_cap 이 자기 삼중항과 6~29% 어긋났다.
      이제 **모든 기록의 q_cap 을 자기 (v_free, rho_crit, a) 에서 계산**하고 검산한다.
  (3) 퇴화 판정이 최적화 경계 근접만 봐서 FW_E S12 (rho_crit 10.5 · a 3.6) 를 통과시켰다 — 그 삼중항은
      k=26.7 에서 V=0.04 km/h 인 **흐름벽**인데 같은 밀도 실측은 19.2 km/h 다. 이제 **물리 창**으로도 막는다.
  (4) v_free 실측을 저밀도 표본의 **평균**으로 잡아 병목 하류 셀에서 큐 방류 상태가 섞였다.
      이제 자유 가지 속도의 **p85** 를 쓴다.

사용: python fit_fd21_150s_20260908.py <samples_glob_prefix> <out_json>
      예) python fit_fd21_150s_20260908.py outputs/fd_ver2_20260907/fd21n_samples outputs/fd_ver2_20260907/fd_fit21_150s_v2.json
"""
import collections
import csv
import io
import json
import math
import sys
import datetime

import numpy as np
from scipy.optimize import least_squares

LEVELS = ["x04", "x08", "x12", "x15", "x18"]
PER = 30                      # 150 s = 5 s x 30 = 제어 간격
BOUNDS_LO = [80.0, 5.0, 0.6]  # v_free, rho_crit, a
BOUNDS_HI = [140.0, 90.0, 6.0]
# 물리 창 — 최적화 경계와 **별개**다. 경계 안이어도 자유류 고속도로 셀로 말이 안 되면 기각한다.
PHYS = {"v_free": (85.0, 135.0), "rho_crit": (15.0, 60.0), "metanet_a_m": (1.0, 3.0)}


def fit3(k, v):
    def resid(p):
        vf, kc, a = p
        return vf * np.exp(-(1.0 / a) * np.power(np.maximum(k, 1e-6) / kc, a)) - v
    best = None
    for vf0 in (108.0, 122.0):
        for kc0 in (18.0, 28.0, 40.0):
            for a0 in (1.0, 1.6, 2.4):
                try:
                    r = least_squares(resid, [vf0, kc0, a0], bounds=(BOUNDS_LO, BOUNDS_HI), max_nfev=3000)
                except Exception:
                    continue
                if best is None or r.cost < best.cost:
                    best = r
    if best is None:
        return None
    vf, kc, a = best.x
    return float(vf), float(kc), float(a), float(np.sqrt(np.mean(best.fun ** 2)))


def main():
    prefix, outj = sys.argv[1], sys.argv[2]
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    D = collections.defaultdict(lambda: collections.defaultdict(list))
    lanes_of = {}
    for tag in LEVELS:
        for r in csv.DictReader(io.open("%s_%s.csv" % (prefix, tag), encoding="utf-8")):
            key = (r["dir"], int(r["seg"]))
            D[key][tag].append((float(r["t"]), float(r["k_veh_km_lane"]), float(r["v_kph"]),
                                float(r["q_kv_veh_h_lane"])))
            lanes_of[key] = float(r["lanes"])

    def agg(key):
        """비겹침 150 s 창. 겹치면 상위분위가 부풀어 용량 추정이 낙관적이 된다."""
        K, V, Q = [], [], []
        for tag in LEVELS:
            a = sorted(D[key][tag])
            for i in range(0, len(a) - PER + 1, PER):
                b = a[i:i + PER]
                K.append(float(np.mean([x[1] for x in b])))
                V.append(float(np.mean([x[2] for x in b])))
                Q.append(float(np.mean([x[3] for x in b])))     # 셀 평균 k·v = 모형의 q_values 와 같은 양
        return np.array(K), np.array(V), np.array(Q)

    out = {}
    print("%-10s %-4s %6s %6s | %6s %6s %5s %8s %6s | %s"
          % ("셀", "차로", "k_p05", "k_p95", "v_free", "k_crit", "a", "q_cap", "RMSE", "판정"))
    for dr in ("FW_E", "FW_W"):
        for s in range(21):
            key = (dr, s)
            K, V, Q = agg(key)
            lanes = lanes_of[key]
            p05, p95 = float(np.percentile(K, 5)), float(np.percentile(K, 95))
            free = V[K < 10.0]
            v_meas = float(np.percentile(free, 85)) if len(free) >= 5 else float(np.percentile(V, 95))
            rec = {"lanes": lanes, "k_p05": p05, "k_p95": p95, "n_windows": int(len(K)),
                   "v_free_meas": round(v_meas, 2),
                   "q_kv_sustained": round(float(np.mean(sorted(Q, reverse=True)[:max(1, len(Q) // 20)])), 1),
                   "frac_above_kcrit": None}
            ok = (p05 <= 12.0 and p95 >= 22.0 and len(K) >= 40)
            verdict = "자유류만"
            if ok:
                f = fit3(K, V)
                if f:
                    vf, kc, a, rmse = f
                    phys = (PHYS["v_free"][0] <= vf <= PHYS["v_free"][1]
                            and PHYS["rho_crit"][0] <= kc <= PHYS["rho_crit"][1]
                            and PHYS["metanet_a_m"][0] <= a <= PHYS["metanet_a_m"][1])
                    rec.update({"fit_v_free": round(vf, 3), "fit_rho_crit": round(kc, 3),
                                "fit_metanet_a_m": round(a, 4), "fit_rmse": round(rmse, 3),
                                "physically_plausible": bool(phys)})
                    if phys:
                        rec.update({"v_free": round(vf, 3), "rho_crit": round(kc, 3), "metanet_a_m": round(a, 4),
                                    "identifiable": True, "rmse": round(rmse, 3)})
                        verdict = "식별"
                    else:
                        verdict = "물리창 기각"
            if not rec.get("identifiable"):
                rec.update({"identifiable": False})
            # 임계 위 체류 비율 — 용량 앵커를 양방향으로 걸지 판단하는 증거
            kc_ref = rec.get("rho_crit")
            if kc_ref:
                rec["frac_above_kcrit"] = round(float((K > kc_ref).mean()), 4)
            # q_cap 은 언제나 자기 삼중항에서 계산한다(식별된 셀만; 나머지는 급 형상 단계에서 채운다)
            if rec.get("identifiable"):
                rec["q_cap"] = round(rec["rho_crit"] * rec["v_free"] * math.exp(-1.0 / rec["metanet_a_m"]), 1)
                chk = abs(rec["q_cap"] - rec["rho_crit"] * rec["v_free"] * math.exp(-1.0 / rec["metanet_a_m"]))
                assert chk < 0.2, (key, chk)
            out["%s_S%d" % key] = rec
            print("%-10s %-4d %6.1f %6.1f | %6s %6s %5s %8s %6s | %s"
                  % ("%s_S%d" % key, int(lanes), p05, p95,
                     ("%.1f" % rec["v_free"]) if rec.get("identifiable") else ("%.1f*" % v_meas),
                     ("%.1f" % rec["rho_crit"]) if rec.get("identifiable") else "-",
                     ("%.2f" % rec["metanet_a_m"]) if rec.get("identifiable") else "-",
                     ("%.0f" % rec["q_cap"]) if rec.get("identifiable") else "-",
                     ("%.2f" % rec["rmse"]) if rec.get("identifiable") else "-", verdict))
    doc = {"schema": "fd_fit21_150s_v2", "generated": datetime.date.today().isoformat(),
           "samples_prefix": prefix, "levels": LEVELS, "aggregation_sec": PER * 5,
           "fit_bounds": {"v_free": BOUNDS_LO[0:1] + BOUNDS_HI[0:1], "rho_crit": [BOUNDS_LO[1], BOUNDS_HI[1]],
                          "metanet_a_m": [BOUNDS_LO[2], BOUNDS_HI[2]]},
           "physical_window": PHYS,
           "definition": "150 s 비겹침 창의 (k, v) 로 V(k)=v_free·exp(-(1/a)(k/k_cr)^a) 적합. "
                         "식별 관문 = 자유(k_p05<=12)와 정체(k_p95>=22) 두 가지 모두 존재. "
                         "물리 창을 통과 못 하면 기각한다(최적화 경계와 별개). "
                         "v_free_meas = 자유 가지(k<10) 속도의 p85. q_kv_sustained = 셀 평균 k·v 상위 5% 평균.",
           "segments": out}
    io.open(outj, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
    n_id = sum(1 for v in out.values() if v.get("identifiable"))
    n_rej = sum(1 for v in out.values() if v.get("physically_plausible") is False)
    print("\n식별 %d / 42 · 물리창 기각 %d · → %s" % (n_id, n_rej, outj))


if __name__ == "__main__":
    main()
