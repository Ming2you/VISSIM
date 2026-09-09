# -*- coding: utf-8 -*-
"""Ver2 v0 본선 공간 진단: 차로별 평균속도·밀도 종단면 + 램프/차로수 전이 표시 (2026-09-07).
왜 필요한가 — 세그먼트(1.35 km) FD 만 보면 '합류 구간은 v_free 가 낮다'로 보이지만, 그 저하가 셀 전체인지
합류점 하류 국소인지, 그리고 차로수 전이 자체 때문인지 이웃 램프 때문인지는 종단면으로만 갈린다."""
import io, sys, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for _f in ("Malgun Gothic", "Gulim", "Batang"):
    if any(_f.lower() == f.name.lower() for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = _f; break
plt.rcParams["axes.unicode_minus"] = False

MARK = {"FW_E": [(4386.3,"OFF",2),(4610.8,"ON",1),(4746.9,"OFF",1),(4900.0,"ON",2),
                 (6826.8,"OFF",2),(6839.6,"차로 4→3",0),(7153.4,"ON",1),(7240.3,"OFF",1),(7448.4,"ON",1)],
        "FW_W": [(3425.4,"OFF",1),(3525.1,"ON",1),(3650.9,"OFF",1),(3816.8,"차로 3→4",0),(3832.6,"ON",2),
                 (5909.7,"OFF",1),(6075.4,"ON",1),(6224.8,"OFF",2),(6777.1,"ON",1)]}
SEGL = {"FW_E": 1348.004, "FW_W": 1347.563}
LANEBRK = {"FW_E": (6841.7, 4, 3), "FW_W": (3822.4, 3, 4)}


def main():
    prof, lanesp, outp = sys.argv[1], sys.argv[2], sys.argv[3]
    z = np.load(prof, allow_pickle=True); BIN = float(z["bin_m"])
    zl = np.load(lanesp, allow_pickle=True); LB = float(zl["bin_m"])
    fig, axes = plt.subplots(2, 2, figsize=(17, 9.5))
    for r, d in enumerate(("FW_E", "FW_W")):
        cnt = z["cnt_%s" % d]; spd = z["spd_%s" % d]; nb = cnt.shape[1]
        xb = (np.arange(nb) + 0.5) * BIN
        brk, la, lb = LANEBRK[d]
        lanes = np.where(xb <= brk, la, lb).astype(float)
        k = cnt / (BIN / 1000.0) / lanes
        with np.errstate(invalid="ignore"):
            v = np.where(cnt > 0, spd / np.maximum(cnt, 1), np.nan)
        kmed = np.nanmedian(np.where(cnt > 0, k, np.nan), axis=0)
        acc = zl["acc_%s" % d]; cn = zl["cnt_%s" % d]
        xl = (np.arange(acc.shape[0]) + 0.5) * LB
        ax = axes[r][0]
        for ln, col in ((1, "#c1121f"), (2, "#e07a5f"), (3, "#2a6f97"), (4, "#1b4965")):
            m = cn[:, ln] > 30
            ax.plot(xl[m], (acc[m, ln] / cn[m, ln]), lw=1.6, color=col, label="차로 %d" % ln)
        ax.set_ylabel("평균 속도 [km/h]"); ax.set_ylim(0, 130)
        ax.set_title("%s  차로별 평균속도 종단면 (t≥900 전체)" % d, fontsize=11)
        ax.legend(fontsize=8, ncol=4, loc="lower right")
        ax2 = axes[r][1]
        ax2.plot(xb, kmed, lw=1.8, color="#1b4965")
        ax2.axhline(35.8 if d == "FW_E" else 30.1, color="#c1121f", ls="--", lw=1.2,
                    label="평지 k_crit 실측 (%s)" % ("4차로 35.8" if d == "FW_E" else "3차로 30.1"))
        ax2.axhline(27.0, color="#888", ls=":", lw=1.2, label="현재 config rho_crit 27")
        ax2.set_ylabel("중앙 밀도 [veh/km/lane]"); ax2.set_ylim(0, 120)
        ax2.set_title("%s  밀도 종단면" % d, fontsize=11); ax2.legend(fontsize=8)
        for a_ in (ax, ax2):
            for x0, lab, nl in MARK[d]:
                a_.axvline(x0, color=("k" if lab.startswith("차로") else ("#2a9d8f" if lab == "ON" else "#e9c46a")),
                           lw=(1.8 if lab.startswith("차로") else 1.0),
                           ls=("-" if lab.startswith("차로") else "--"), alpha=0.8)
            for s in range(1, 8):
                a_.axvline(s * SEGL[d], color="#ccc", lw=0.8, zorder=0)
            for s in range(8):
                a_.text((s + 0.5) * SEGL[d], a_.get_ylim()[1] * 0.94, "S%d" % s,
                        ha="center", fontsize=8, color="#666")
            a_.set_xlabel("사슬 위치 [m]"); a_.grid(alpha=0.2); a_.set_xlim(0, 10800)
        for x0, lab, nl in MARK[d]:
            ax.text(x0, 6, lab, rotation=90, fontsize=7, ha="right", va="bottom",
                    color=("k" if lab.startswith("차로") else "#444"))
    fig.suptitle("Ver2 무제어(v0) 본선 종단면 — 초록 파선=on-ramp, 노랑 파선=off-ramp, 검정 실선=차로수 전이", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96]); fig.savefig(outp, dpi=115)
    print("→", outp)


if __name__ == "__main__":
    main()
