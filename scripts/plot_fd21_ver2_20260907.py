# -*- coding: utf-8 -*-
"""21셀 격자 세그먼트별 기본도 q-k — 방향마다 한 장 (2026-09-07).

표본은 300 s 집계(5 s 프레임 60개), q 는 sending flow(경계 통과 + 셀 안 off-ramp/망이탈).
빨강 곡선 = 그 셀 자체 적합(식별된 셀만), 회색 점선 = 같은 차로수 평지 셀 대표, 검정 사각 = 밀도구간 평균.
사용: python plot_fd21_ver2_20260907.py <fit_json> <split_json> <out_prefix> [win_sec]
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

SRC = "outputs/fd_ver2_20260907/fd21_samples_%s.csv"
LEVELS = ["x04", "x08", "x12", "x15", "x18"]
COLOR = {"x04": "#8ecae6", "x08": "#219ebc", "x12": "#023047", "x15": "#fb8500", "x18": "#c1121f"}
# 평지 대표 (21셀 격자에서 램프 없는 셀들의 중앙값) — E S2~S7 / W S1~S4
PLAIN = {4: dict(v_free=123.0, k_crit=35.5, a=1.52), 3: dict(v_free=121.7, k_crit=29.0, a=1.72)}
LANEBRK = {"FW_E": 6841.7, "FW_W": 3822.4}


def curve(k, p):
    return k * p["v_free"] * np.exp(-(1.0 / p["a"]) * (k / p["k_crit"]) ** p["a"])


def main():
    fitj, splitj, prefix = sys.argv[1], sys.argv[2], sys.argv[3]
    win = float(sys.argv[4]) if len(sys.argv) > 4 else 300.0
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    fit = json.load(io.open(fitj, encoding="utf-8"))
    split = json.load(io.open(splitj, encoding="utf-8"))
    lab = collections.defaultdict(list)
    for r in split["on_ramps"]:
        lab[(r["direction"], r["segment_index"])].append("ON " + r["name"])
    for r in split["off_ramps"]:
        lab[(r["direction"], r["segment_index"])].append("OFF " + r["name"])

    D = collections.defaultdict(lambda: collections.defaultdict(list))
    for tag in LEVELS:
        for r in csv.DictReader(io.open(SRC % tag, encoding="utf-8")):
            D[(r["dir"], int(r["seg"]))][tag].append(
                (float(r["t"]), float(r["k_veh_km_lane"]), int(r["cross"]) + int(r["leave"]), float(r["lanes"])))

    for dr in ("FW_E", "FW_W"):
        seglen = (10784.028 if dr == "FW_E" else 10780.5) / 21.0
        fig, axes = plt.subplots(3, 7, figsize=(23, 11))
        for s in range(21):
            ax = axes[s // 7][s % 7]
            rec = fit["%s_S%d" % (dr, s)]
            lanes = int(rec["lanes"])
            allk, allq = [], []
            for tag in LEVELS:
                rows = sorted(D[(dr, s)][tag])
                per = int(win / 5.0)
                kk, qq = [], []
                for i in range(0, len(rows) - per + 1, per):
                    blk = rows[i:i + per]
                    kk.append(float(np.mean([b[1] for b in blk])))
                    qq.append(sum(b[2] for b in blk) * 3600.0 / win / lanes)
                ax.scatter(kk, qq, s=14, alpha=0.75, c=COLOR[tag], edgecolors="none",
                           label=tag if s == 0 else None)
                allk += kk; allq += qq
            allk, allq = np.array(allk), np.array(allq)
            edges = np.array([0, 4, 8, 12, 16, 20, 25, 31, 38, 47, 58, 72, 90, 130.0])
            bx, by = [], []
            for lo, hi in zip(edges[:-1], edges[1:]):
                m = (allk >= lo) & (allk < hi)
                if m.sum() >= 3:
                    bx.append(allk[m].mean()); by.append(allq[m].mean())
            ax.plot(bx, by, "s-", color="k", ms=3.5, lw=1.0, alpha=0.85, zorder=5)
            kx = np.linspace(0.5, 125.0, 220)
            ax.plot(kx, curve(kx, PLAIN[lanes]), ":", color="#888", lw=1.4, zorder=4)
            if rec.get("identifiable"):
                p = dict(v_free=rec["v_free"], k_crit=rec["rho_crit"], a=rec["metanet_a_m"])
                ax.plot(kx, curve(kx, p), "-", color="#c1121f", lw=1.8, zorder=6)
                ax.plot([p["k_crit"]], [rec["q_cap"]], "*", color="#c1121f", ms=12, zorder=7)
                sub = "v_f %.0f · k_cr %.1f · a %.2f · q_cap %.0f" % (p["v_free"], p["k_crit"], p["a"], rec["q_cap"])
            else:
                sub = "용량 미식별 (병목 하류) · 저밀도 v %.0f" % rec["v_free"]
            tags = " · ".join(lab.get((dr, s), []))
            if (dr == "FW_E" and s == 13) or (dr == "FW_W" and s == 7):
                tags = (tags + " · 차로전이").strip(" ·")
            ax.set_title("S%d  %.0f~%.0f m  %d차로\n%s" % (s, s * seglen, (s + 1) * seglen, lanes, tags or "램프 없음"),
                         fontsize=8)
            ax.text(0.5, 0.96, sub, transform=ax.transAxes, ha="center", va="top", fontsize=6.8,
                    color="#c1121f" if rec.get("identifiable") else "#666")
            ax.set_xlim(0, 125); ax.set_ylim(0, 2600); ax.grid(alpha=0.25); ax.tick_params(labelsize=6.5)
            if s % 7 == 0:
                ax.set_ylabel("q_send [veh/h/lane]", fontsize=7.5)
            if s // 7 == 2:
                ax.set_xlabel("k [veh/km/lane]", fontsize=7.5)
            if s == 0:
                ax.legend(fontsize=6.5, markerscale=1.2, title="본선 수요", title_fontsize=6.5, loc="upper right")
        fig.suptitle("%s · 21셀 격자 세그먼트별 기본도 (점 = %.0f s 집계 · q = sending flow)   "
                     "빨강 = 셀 적합 · 회색 점선 = 평지 %d/%d차로 대표 · 검정 = 밀도구간 평균"
                     % (dr, win, 4, 3), fontsize=13)
        fig.tight_layout(rect=[0, 0, 1, 0.955])
        out = "%s_%s.png" % (prefix, dr)
        fig.savefig(out, dpi=110)
        print("→", out)


if __name__ == "__main__":
    main()
