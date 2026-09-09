# -*- coding: utf-8 -*-
"""Ver2 FD 그림 v4 — 표시 해상도와 유량 정의를 고친 판 (2026-09-07).

v3 그림이 산포가 컸던 이유 둘, 둘 다 물리가 아니라 측정/표시였다.
  (1) q 를 5 s 경계통과 대수로 셌다 → 4차로 셀은 **180 veh/h/lane 계단**(3차로는 240)이고 60 s 이동평균만
      걸어서 계수잡음이 그대로 보였다. 여기서는 **300 s 창**으로 집계한다.
  (2) q_edge(다음 셀로 가는 통과 유량)만 썼다 → 셀 안에 off-ramp 가 있는 위빙 셀에서 그 셀 유량을
      33~50% 과소평가했다(E S3 +33% · W S2 +38% · W S4 +50%). vendor `freeway_substep` 의
      `q_values[i] = rho*v*lanes` 는 off-ramp 몫까지 포함한 **sending flow** 이므로 q_send 를 쓴다.
      마지막 셀 S7 은 하류 경계가 없어 q_edge 가 늘 0 이었다(그림이 통째로 빈 칸) — q_send 로 해결.

적합 자체는 (k, v) 쌍으로 하므로 위 잡음과 무관하다. v 는 셀 안 순간속도 평균이라 계수 계단이 없다.
사용: python plot_fd_ver2_v4_20260907.py <fit_json> <out_png> [win_sec]
"""
import collections
import csv
import io
import json
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for _f in ("Malgun Gothic", "Gulim", "Batang"):
    if any(_f.lower() == f.name.lower() for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = _f
        break
plt.rcParams["axes.unicode_minus"] = False

SRC = "outputs/fd_ver2_20260907/fd2_samples_%s.csv"
LEVELS = ["x04", "x08", "x12", "x15", "x18"]
COLOR = {"x04": "#8ecae6", "x08": "#219ebc", "x12": "#023047", "x15": "#fb8500", "x18": "#c1121f"}


def main():
    fitj, outp = sys.argv[1], sys.argv[2]
    win = float(sys.argv[3]) if len(sys.argv) > 3 else 300.0
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    fit = json.load(io.open(fitj, encoding="utf-8"))
    D = collections.defaultdict(lambda: collections.defaultdict(list))
    for tag in LEVELS:
        for r in csv.DictReader(io.open(SRC % tag, encoding="utf-8")):
            D[(r["dir"], int(r["seg"]))][tag].append(
                (float(r["t"]), int(r["n"]), float(r["v_kph"]), int(r["cross"]) + int(r["leave"]), float(r["lanes"])))

    fig, axes = plt.subplots(4, 4, figsize=(19.5, 15.5))
    order = [("FW_E", i) for i in range(8)] + [("FW_W", i) for i in range(8)]
    for idx, key in enumerate(order):
        ax = axes[idx // 4][idx % 4]
        rec = fit["segments"]["%s_S%d" % key]
        lanes = rec["lanes"]
        allk, allq = [], []
        for tag in LEVELS:
            rows = sorted(D[key][tag])
            lanes = rows[0][4]
            per = int(win / 5.0)
            kk, qq = [], []
            for i in range(0, len(rows) - per + 1, per):
                blk = rows[i:i + per]
                n = np.mean([b[1] for b in blk])
                k = n / (1.348 * lanes) if key[0] == "FW_E" else n / (1.3476 * lanes)
                q = sum(b[3] for b in blk) * 3600.0 / win / lanes
                kk.append(k); qq.append(q)
            ax.scatter(kk, qq, s=16, alpha=0.75, c=COLOR[tag], edgecolors="none",
                       label=tag if idx == 0 else None)
            allk += kk; allq += qq
        allk, allq = np.array(allk), np.array(allq)
        # 밀도 구간 평균 (검은 사각) — 모양을 눈으로 확인하는 기준선
        edges = np.array([0, 5, 10, 15, 20, 25, 30, 40, 50, 65, 85, 105, 130.0])
        bx, by = [], []
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = (allk >= lo) & (allk < hi)
            if m.sum() >= 3:
                bx.append(allk[m].mean()); by.append(allq[m].mean())
        ax.plot(bx, by, "s-", color="k", ms=4.5, lw=1.2, alpha=0.85, zorder=5)
        kk = np.linspace(0.5, 125.0, 250)
        vf, kc, a = rec["v_free"], rec["rho_crit"], rec["metanet_a_m"]
        ax.plot(kk, kk * vf * np.exp(-(1.0 / a) * (kk / kc) ** a), "-", color="#c1121f", lw=1.8, zorder=6)
        ax.plot(kk, kk * 120.0 * np.exp(-(1.0 / 1.6) * (kk / 27.0) ** 1.6), ":", color="#888", lw=1.4)
        ident = "" if rec["identifiable"] else "  [자유류만 · 급 형상 차용]"
        ax.set_title("%s S%d  %s  (%d차로)%s\n%s" % (key[0], key[1], rec["class"], lanes, ident,
                     rec.get("note") or "램프 없음 · 차로수 일정"), fontsize=8.5)
        ax.set_xlabel("k [veh/km/lane]", fontsize=8); ax.set_ylabel("q_send [veh/h/lane]", fontsize=8)
        ax.tick_params(labelsize=7); ax.grid(alpha=0.25); ax.set_ylim(0, 2500); ax.set_xlim(0, 125)
        ax.text(0.97, 0.95, "v_f %.0f · k_cr %.1f · a %.2f" % (vf, kc, a), transform=ax.transAxes,
                ha="right", va="top", fontsize=7.5, color="#c1121f")
        if idx == 0:
            ax.legend(fontsize=7, markerscale=1.4, title="본선 수요", title_fontsize=7, loc="lower right")
    fig.suptitle("Ver2 무제어 수요 sweep · 세그먼트 기본도 (표본 %.0f s 집계 · q = sending flow)   "
                 "빨강=적합 · 검정 사각=밀도구간 평균 · 회색 점선=현재 정본" % win, fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.965])
    fig.savefig(outp, dpi=115)
    print("→", outp)


if __name__ == "__main__":
    main()
