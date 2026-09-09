# -*- coding: utf-8 -*-
"""21셀 세그먼트별 METANET 파라미터 산출 v2 (schema freeway_segment_params_v1, 2026-09-08).

2026-09-07 판을 대체한다. 독립 검토가 잡은 설계 결함 셋을 닫는다.

(1) **앵커를 모형이 쓰는 양에 건다.** 종전에는 경계 flux(q_send = 통과 + 셀 내 이탈)로 앵커했는데,
    vendor 의 `q_values[i] = segment_flow_veh_h(rho_i, v_i, lanes_i)` 는 **셀 평균 k·v** 다
    (off-ramp 분기는 그 뒤에 일어난다). 램프 셀에서 둘이 27~37% 어긋나고 앵커 대상 대부분이 램프
    셀이라, 종전 앵커는 사실상 그 정의 차이를 재고 있었다. 이제 `q_kv_sustained`(셀 평균 k·v 상위 5%)를 쓴다.

(2) **앵커를 양방향으로 만든다.** 종전 `max(적합, 관측)` 은 한쪽이라, 적합이 과대한 셀을 못 내렸다.
    관측 지속 방류가 용량의 하한일 뿐인 것은 **수요 부족 셀**에서만 참이다. 셀이 실제로 임계 위에서
    상당 시간을 보내면(`frac_above_kcrit > 0.10`) 그 관측은 하한이 아니라 **용량 추정치**이므로 그대로 쓴다.

(3) **ρ_crit 만 되풀지 않는다.** 그러면 V(k) 가 가로로 늘어나 적합했던 정체 가지와 어긋난다.
    이제 목표 용량을 제약으로 두고 **(v_free, a) 2파라미터를 그 셀 자료에 다시 적합**한다
    (ρ_crit = q_cap/(v_free·e^{-1/a}) 로 소거). 제약 후 RMSE 를 같이 적어 열화가 보이게 한다.

식별 불가(병목 하류) 셀은 급 형상 + 그 셀의 자유가지 p85 속도. 관측 지속 방류가 그 형상의 용량을 넘으면
그만큼만 ρ_crit 을 올린다(하한이므로) — 그 사실을 `capacity_raised_to_observed` 로 남긴다.

사용: python build_freeway_segment_params_20260908.py <fit_json> <split_json> <out_json>
"""
import io
import json
import math
import sys
import datetime
import collections
import csv

import numpy as np
from scipy.optimize import least_squares

SAMPLES = "outputs/fd_ver2_20260907/fd21n_samples_%s.csv"
LEVELS = ["x04", "x08", "x12", "x15", "x18"]
PER = 30
PLAIN4 = [("FW_E", i) for i in range(2, 8)]
PLAIN3 = [("FW_W", i) for i in range(1, 5)]
HEAD_FRAC = 0.05          # 활성 병목(큐 머리)으로 관측된 창의 최소 비율


def load_windows():
    D = collections.defaultdict(lambda: collections.defaultdict(list))
    for tag in LEVELS:
        for r in csv.DictReader(io.open(SAMPLES % tag, encoding="utf-8")):
            D[(r["dir"], int(r["seg"]))][tag].append(
                (float(r["t"]), float(r["k_veh_km_lane"]), float(r["v_kph"])))
    out = {}
    for key, per_tag in D.items():
        K, V = [], []
        for tag in LEVELS:
            a = sorted(per_tag[tag])
            for i in range(0, len(a) - PER + 1, PER):
                b = a[i:i + PER]
                K.append(float(np.mean([x[1] for x in b])))
                V.append(float(np.mean([x[2] for x in b])))
        out[key] = (np.array(K), np.array(V))
    return out


def refit_at_capacity(K, V, q_target):
    """q_cap 을 제약으로 두고 (v_free, a) 만 적합. rho_crit 은 제약으로 소거된다."""
    def resid(p):
        vf, a = p
        kc = q_target / max(vf * math.exp(-1.0 / a), 1e-9)
        return vf * np.exp(-(1.0 / a) * np.power(np.maximum(K, 1e-6) / kc, a)) - V
    best = None
    for vf0 in (100.0, 118.0, 128.0):
        for a0 in (1.2, 1.8, 2.5):
            try:
                r = least_squares(resid, [vf0, a0], bounds=([85.0, 1.0], [135.0, 3.0]), max_nfev=3000)
            except Exception:
                continue
            if best is None or r.cost < best.cost:
                best = r
    if best is None:
        return None
    vf, a = best.x
    kc = q_target / max(vf * math.exp(-1.0 / a), 1e-9)
    return float(vf), float(kc), float(a), float(np.sqrt(np.mean(best.fun ** 2)))


def main():
    fitj, splitj, outj = sys.argv[1], sys.argv[2], sys.argv[3]
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    fit = json.load(io.open(fitj, encoding="utf-8"))
    segs = fit["segments"]
    split = json.load(io.open(splitj, encoding="utf-8"))
    ramps = collections.defaultdict(list)
    for r in split["on_ramps"]:
        ramps[(r["direction"], r["segment_index"])].append("ON " + r["name"])
    for r in split["off_ramps"]:
        ramps[(r["direction"], r["segment_index"])].append("OFF " + r["name"])
    W = load_windows()

    plain = {}
    for lanes, keys in ((4, PLAIN4), (3, PLAIN3)):
        rows = [segs["%s_S%d" % k] for k in keys if segs["%s_S%d" % k].get("identifiable")]
        vf = float(np.median([r["v_free"] for r in rows]))
        kc = float(np.median([r["rho_crit"] for r in rows]))
        a = float(np.median([r["metanet_a_m"] for r in rows]))
        plain[lanes] = {"v_free": vf, "rho_crit": kc, "metanet_a_m": a,
                        "q_cap": kc * vf * math.exp(-1.0 / a), "n_cells": len(rows)}
        print("평지 %d차로 대표 (식별 셀 %d개 중앙값): v_free %.1f · k_crit %.1f · a %.2f · q_cap %.0f"
              % (lanes, len(rows), vf, kc, a, plain[lanes]["q_cap"]))

    # 큐 머리 판정: 자기 k > 자기 ρ_cr 이고 바로 하류 k < 하류 ρ_cr 인 창 = 활성 병목.
    #   스필백으로 정체된 셀은 자기 용량이 아니라 하류가 받아주는 만큼 흘린다(2026-09-07 실측: FW_E S2~S7 의
    #   정체 가지는 전적으로 S8/S9 램프 병목이 밀어올린 큐이고 전선이 상류로 14 km/h 로 번진다).
    #   그래서 그런 창에서만 셀 평균 k·v 의 상위 20% 평균을 용량 추정치로 받는다.
    def kcrit_of(key):
        r = segs["%s_S%d" % key]
        return float(r["rho_crit"]) if r.get("identifiable") else float(plain[int(r["lanes"])]["rho_crit"])
    head_stats = {}
    for dr_ in ("FW_E", "FW_W"):
        for s_ in range(20):
            key = (dr_, s_)
            dn = (dr_, s_ + 1)
            K, V = W[key]
            Kd, _ = W[dn]
            n = min(len(K), len(Kd))
            if n < 20:
                continue
            m = (K[:n] > kcrit_of(key)) & (Kd[:n] < kcrit_of(dn))
            if m.sum() == 0:
                head_stats[key] = (0.0, None)
                continue
            q = (K[:n] * V[:n])[m]
            top = np.sort(q)[-max(1, len(q) // 5):]
            head_stats[key] = (float(m.mean()), float(np.mean(top)))


    out = {}
    print("\n%-10s %-3s %-16s %8s %8s %8s | %6s %6s %5s %6s | %s"
          % ("셀", "L", "출처", "적합q", "관측q(k·v)", "채택q", "v_free", "k_crit", "a", "RMSE", "램프"))
    for dr in ("FW_E", "FW_W"):
        for s in range(21):
            key = (dr, s)
            rec = segs["%s_S%d" % key]
            lanes = int(rec["lanes"])
            base = plain[lanes]
            q_obs = float(rec["q_kv_sustained"])
            K, V = W[key]
            note = ""
            if rec.get("identifiable"):
                q_fit = float(rec["q_cap"])
                head_frac, q_head = head_stats.get(key, (0.0, None))
                if head_frac >= HEAD_FRAC and q_head:
                    q_use, why = q_head, "큐머리 %.0f%%" % (100 * head_frac)
                else:
                    q_use, why = max(q_fit, q_obs), ("관측하한" if q_obs > q_fit else "적합")
                if abs(q_use - q_fit) / max(q_fit, 1.0) > 0.005:
                    r2 = refit_at_capacity(K, V, q_use)
                    # 제약이 자료와 심하게 싸우면(RMSE 50% 이상 악화, 또는 재적합이 경계에 붙으면)
                    # 그 용량 목표를 기각하고 자유 적합을 지킨다 — 자료가 그 용량을 거부한다는 뜻이다.
                    bad = (r2 is None) or (r2[3] > 1.5 * float(rec["rmse"]))                         or not (86.0 < r2[0] < 134.0) or not (1.05 < r2[2] < 2.95)
                    if bad:
                        vf, kc, a, rmse = rec["v_free"], rec["rho_crit"], rec["metanet_a_m"], rec["rmse"]
                        q_use = q_fit
                        origin = "셀 적합"
                        why += "→기각(제약이 자료와 충돌)"
                        note = "용량목표 %.0f 기각: 제약 RMSE %s vs 자유 %.2f" % (
                            q_head or 0.0, ("%.2f" % r2[3]) if r2 else "발산", float(rec["rmse"]))
                    else:
                        vf, kc, a, rmse = r2
                        origin = "셀 적합+용량제약"
                        note = "제약 RMSE %.2f (자유 %.2f)" % (rmse, rec["rmse"])
                else:
                    vf, kc, a, rmse = rec["v_free"], rec["rho_crit"], rec["metanet_a_m"], rec["rmse"]
                    origin = "셀 적합"
                origin += " / " + why
            else:
                vf = float(rec["v_free_meas"])
                kc, a = base["rho_crit"], base["metanet_a_m"]
                q_fit = kc * vf * math.exp(-1.0 / a)
                rmse = None
                origin = "급형상+실측 v_free"
                if q_obs > q_fit:
                    kc = q_obs / max(vf * math.exp(-1.0 / a), 1e-9)
                    origin += " (관측하한으로 k_cr↑)"
                q_use = kc * vf * math.exp(-1.0 / a)
            q_final = kc * vf * math.exp(-1.0 / a)
            assert abs(q_final - q_use) / max(q_use, 1.0) < 0.01, (key, q_final, q_use)
            out["%s_S%d" % key] = {
                "lanes": float(lanes), "v_free": round(vf, 2), "rho_crit": round(kc, 2),
                "metanet_a_m": round(a, 3), "q_cap_veh_h_lane": round(q_final, 1),
                "q_cap_fit": round(q_fit, 1), "q_cap_observed_kv": round(q_obs, 1),
                "frac_above_kcrit": rec.get("frac_above_kcrit"),
                "queue_head_frac": round(head_stats.get(key, (0.0, None))[0], 4),
                "identifiable": bool(rec.get("identifiable")), "origin": origin,
                "v_free_meas": round(float(rec["v_free_meas"]), 2),
                "constrained_rmse": (round(rmse, 3) if rmse is not None else None),
                "ramps": " · ".join(ramps.get(key, [])), "note": note}
            print("%-10s %-3d %-16s %8.0f %10.0f %8.0f | %6.1f %6.1f %5.2f %6s | %s %s"
                  % ("%s_S%d" % key, lanes, origin[:16], q_fit, q_obs, q_final, vf, kc, a,
                     ("%.2f" % rmse) if rmse is not None else "-", " · ".join(ramps.get(key, [])), note))
    doc = {"schema": "freeway_segment_params_v1", "generated": datetime.date.today().isoformat(),
           "aggregation_sec": PER * 5, "grid": {"segments_per_link": 21},
           "source_fit": fitj, "source_split": splitj, "levels": LEVELS,
           "plain_class": {str(k): v for k, v in plain.items()},
           "head_frac_threshold": HEAD_FRAC,
           "head_stats": {"%s_S%d" % k: {"frac": v[0], "q_head": v[1]} for k, v in head_stats.items()},
           "definition": "21셀 세그먼트별 METANET FD. 용량 앵커는 셀 평균 k·v(모형의 q_values 와 같은 양) 기준이며 "
                         "정체 증거가 있는 셀에서는 양방향, 없으면 관측을 하한으로만 쓴다. 용량이 바뀐 셀은 "
                         "그 용량을 제약으로 (v_free, a) 를 다시 적합해 ρ_crit 을 소거한다.",
           "segments": out}
    io.open(outj, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print("\n세그먼트 %d개 → %s" % (len(out), outj))


if __name__ == "__main__":
    main()
