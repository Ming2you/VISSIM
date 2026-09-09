# -*- coding: utf-8 -*-
"""Ver2 수요 sweep 5수준 통합 FD 적합 (2026-09-07 v3).

v2 와의 차이 — 표본이 한 수요(x18)가 아니라 x04/x08/x12/x15/x18 다섯이다. 상류 세그먼트가 자유류부터
정체까지 전 구간을 훑으므로 v_free 와 k_crit 이 더 이상 상쇄되지 않아 **셋을 동시에 적합**할 수 있다.
(v2 는 자유류 표본이 없어 v_free 를 118.5 로 고정해야 했다.)

식별 관문: 표본이 두 가지 안에 다 있어야 한다 — k_p05 <= 12 (자유 가지) 그리고 k_p95 >= 22 (정체 가지).
못 만족하면 급 대표 형상 + 그 셀의 저밀도 실측 속도를 쓴다(하류 셀은 병목 하류라 물리적으로 용량 관측 불가).

사용: python fit_fd_ver2_v3_20260907.py <out_json> <out_png>
"""
import collections
import csv
import io
import json
import math
import sys

import numpy as np
from scipy.optimize import least_squares
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for _f in ("Malgun Gothic", "Gulim", "Batang"):
    if any(_f.lower() == f.name.lower() for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = _f
        break
plt.rcParams["axes.unicode_minus"] = False

SRC = "outputs/fd_ver2_20260907/"
LEVELS = [("x04", SRC + "fd_samples_x04.csv"), ("x08", SRC + "fd_samples_x08.csv"),
          ("x12", SRC + "fd_samples_x12.csv"), ("x15", SRC + "fd_samples_x15.csv"),
          ("x18", SRC + "fd_samples_v0.csv")]
COLOR = {"x04": "#8ecae6", "x08": "#219ebc", "x12": "#023047", "x15": "#fb8500", "x18": "#c1121f"}
CLASS = {("FW_E", 0): "plain4", ("FW_E", 1): "plain4", ("FW_E", 2): "plain4", ("FW_E", 3): "weave4",
         ("FW_E", 4): "plain4", ("FW_E", 5): "drop+weave3", ("FW_E", 6): "plain3", ("FW_E", 7): "plain3",
         ("FW_W", 0): "plain3", ("FW_W", 1): "plain3", ("FW_W", 2): "gain+weave3", ("FW_W", 3): "plain4",
         ("FW_W", 4): "weave4", ("FW_W", 5): "merge4", ("FW_W", 6): "plain4", ("FW_W", 7): "plain4"}
NOTE = {("FW_E", 3): "OFF4386(2ln) ON4611 OFF4747 ON4900",
        ("FW_E", 5): "OFF6827(2ln) 4->3@6840 ON7153 OFF7240 ON7448",
        ("FW_W", 2): "OFF3425 ON3525 OFF3651 3->4@3817 ON3833",
        ("FW_W", 4): "OFF5910 ON6075 OFF6225(2ln)", ("FW_W", 5): "ON6777"}


def load():
    D = collections.defaultdict(lambda: collections.defaultdict(list))
    for tag, path in LEVELS:
        for r in csv.DictReader(io.open(path, encoding="utf-8")):
            D[(r["dir"], int(r["seg"]))][tag].append(
                (float(r["k_veh_km_lane"]), float(r["v_kph"]), float(r["q_edge_veh_h_lane"]), float(r["lanes"])))
    return D


def fit3(k, v):
    """v_free, k_crit, a 동시 적합."""
    def resid(p):
        vf, kc, a = p
        return vf * np.exp(-(1.0 / a) * np.power(np.maximum(k, 1e-6) / kc, a)) - v
    best = None
    for vf0 in (110.0, 120.0):
        for kc0 in (20.0, 30.0, 45.0):
            for a0 in (1.0, 1.6, 2.4):
                try:
                    r = least_squares(resid, [vf0, kc0, a0], bounds=([80.0, 5.0, 0.6], [140.0, 90.0, 6.0]),
                                      max_nfev=4000)
                except Exception:
                    continue
                if best is None or r.cost < best.cost:
                    best = r
    vf, kc, a = best.x
    return float(vf), float(kc), float(a), float(np.sqrt(np.mean(best.fun ** 2)))


def main():
    outj, outp = sys.argv[1], sys.argv[2]
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    D = load()
    lanes_of = {key: D[key]["x18"][0][3] for key in D}

    def pooled(keys):
        k, v = [], []
        for key in keys:
            for tag, _ in LEVELS:
                for row in D[key][tag]:
                    k.append(row[0]); v.append(row[1])
        return np.array(k), np.array(v)

    # 급 대표는 **진입 세그먼트 S0 를 뺀다** — 차량 삽입 지점이라 속도가 삽입·대기로 오염된다
    # (실측: plain4 에 E S0 를 넣으면 RMSE 8.64, 빼면 5.46 / plain3 에 W S0 를 넣으면 6.84, 빼면 4.54).
    cls_keys = {"plain4": [("FW_E", 1), ("FW_E", 2)],
                "plain3": [("FW_W", 1)]}
    cls = {}
    print("=== 급 대표 적합 (5수준 통합, v_free 도 동시 적합) ===")
    for name, keys in cls_keys.items():
        k, v = pooled(keys)
        vf, kc, a, rmse = fit3(k, v)
        qc = kc * vf * math.exp(-1.0 / a)
        cls[name] = {"v_free": vf, "k_crit": kc, "a": a, "q_cap": qc, "rmse": rmse, "n": int(len(k))}
        print("  %-8s v_free %6.1f  k_crit %5.1f  a %.2f  q_cap %6.0f veh/h/lane  RMSE %.2f  (표본 %d, k %.1f~%.1f)"
              % (name, vf, kc, a, qc, rmse, len(k), k.min(), k.max()))

    out = {"schema": "fd_fit_v3", "sources": [p for _, p in LEVELS], "class_fit": cls, "segments": {}}
    fig, axes = plt.subplots(4, 4, figsize=(19, 15))
    order = [("FW_E", i) for i in range(8)] + [("FW_W", i) for i in range(8)]
    print("\n%-10s %-12s %2s %7s %7s | %7s %7s %6s %8s %6s | %s"
          % ("세그", "급", "L", "k_p05", "k_p95", "v_free", "k_crit", "a", "q_cap", "RMSE", "판정"))
    for idx, key in enumerate(order):
        ax = axes[idx // 4][idx % 4]
        lanes = lanes_of[key]
        base = cls["plain4"] if lanes >= 4 else cls["plain3"]
        k, v = pooled([key])
        kp05, kp95 = np.percentile(k, 5), np.percentile(k, 95)
        ident = (kp05 <= 12.0) and (kp95 >= 22.0)
        rec = {"class": CLASS[key], "lanes": lanes, "note": NOTE.get(key, ""),
               "k_p05": float(kp05), "k_p95": float(kp95), "identifiable": bool(ident)}
        if ident:
            vf, kc, a, rmse = fit3(k, v)
            qc = kc * vf * math.exp(-1.0 / a)
            rec.update({"v_free": vf, "rho_crit": kc, "metanet_a_m": a, "q_cap_veh_h_lane": qc,
                        "rmse": rmse, "origin": "5수준 통합 세그먼트 적합"})
            print("%-10s %-12s %2d %7.1f %7.1f | %7.1f %7.1f %6.2f %8.0f %6.2f | 3파라미터 식별"
                  % ("%s_S%d" % key, CLASS[key], lanes, kp05, kp95, vf, kc, a, qc, rmse))
        else:
            free = v[k < 10.0]
            vf = float(free.mean()) if len(free) > 20 else base["v_free"]
            kc, a = base["k_crit"], base["a"]
            qc = kc * vf * math.exp(-1.0 / a)
            rec.update({"v_free": vf, "rho_crit": kc, "metanet_a_m": a, "q_cap_veh_h_lane": qc,
                        "rmse": None, "origin": "급 형상 + 저밀도 실측 v_free (병목 하류라 용량 미관측)"})
            print("%-10s %-12s %2d %7.1f %7.1f | %7.1f %7.1f %6.2f %8.0f %6s | 자유류만 (급 형상 차용)"
                  % ("%s_S%d" % key, CLASS[key], lanes, kp05, kp95, vf, kc, a, qc, "-"))
        out["segments"]["%s_S%d" % key] = rec

        for tag, _ in LEVELS:
            a_ = np.array([[r[0], r[2], r[3]] for r in D[key][tag]])
            w = 12
            ax.scatter(np.convolve(a_[:, 0], np.ones(w) / w, mode="same"),
                       np.convolve(a_[:, 1] * a_[0, 2], np.ones(w) / w, mode="same") / a_[0, 2],
                       s=2.5, alpha=0.30, c=COLOR[tag], label=tag if idx == 0 else None)
        kk = np.linspace(0.5, max(k.max(), rec["rho_crit"] * 2.2), 220)
        ax.plot(kk, kk * rec["v_free"] * np.exp(-(1.0 / rec["metanet_a_m"]) * (kk / rec["rho_crit"]) ** rec["metanet_a_m"]),
                "k-", lw=1.7)
        ax.plot([rec["rho_crit"]], [rec["q_cap_veh_h_lane"]], "k*", ms=11)
        ax.plot(kk, kk * 120.0 * np.exp(-(1.0 / 1.6) * (kk / 27.0) ** 1.6), ":", color="#888", lw=1.3)
        ax.set_title("%s S%d  %s  (%d차로)%s\n%s" % (key[0], key[1], CLASS[key], lanes,
                     "" if rec["identifiable"] else "  [자유류만]", NOTE.get(key, "램프 없음 · 차로수 일정")), fontsize=8.5)
        ax.set_xlabel("k [veh/km/lane]", fontsize=8); ax.set_ylabel("q [veh/h/lane]", fontsize=8)
        ax.tick_params(labelsize=7); ax.grid(alpha=0.25); ax.set_ylim(0, 2400); ax.set_xlim(0, 120)
        if idx == 0:
            ax.legend(fontsize=7, markerscale=3, title="본선 수요", title_fontsize=7)
    fig.suptitle("Ver2 무제어 수요 sweep 5수준 통합 기본도 q–k  ·  검정=세그먼트 적합 · ★=용량 · 회색 점선=현재 정본(v_free120·k_cr27·a1.6)",
                 fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(outp, dpi=115)
    io.open(outj, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print("\n→ %s\n→ %s" % (outj, outp))


if __name__ == "__main__":
    main()
