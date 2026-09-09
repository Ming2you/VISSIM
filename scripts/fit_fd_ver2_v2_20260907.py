# -*- coding: utf-8 -*-
"""Ver2 v0 세그먼트별 FD 2단계 적합 (2026-09-07 v2).
1단계: 자유류 속도 v_f — 혼잡 세그먼트는 자유류 표본이 없어 직접 못 재므로, 램프에서 먼 '평지' 격자 실측(≈118.5)을 기준값으로 고정.
2단계: v_f 고정 상태로 (k_cr, a) 최소제곱. 대조로 (k_cr,a)를 평지 급 값으로 고정하고 v_f 만 맞추는 표현도 같이 낸다.
사용: python fit_fd_ver2_v2_20260907.py <fd_samples_csv> <out_json> <out_png>"""
import io, sys, json, csv, collections
import numpy as np
from scipy.optimize import least_squares
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for _f in ("Malgun Gothic", "MalgunGothic", "Gulim", "Batang"):
    if any(_f.lower() == f.name.lower() for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = _f; break
plt.rcParams["axes.unicode_minus"] = False

VF_PLAIN = 118.5   # 램프에서 먼 평지 격자 실측 (100 m 프로파일: E 8600~10800, W 8600~10800 = 118~119)
CLASS = {("FW_E",0):"plain4",("FW_E",1):"plain4",("FW_E",2):"plain4",("FW_E",3):"weave4",
         ("FW_E",4):"plain4",("FW_E",5):"drop+weave3",("FW_E",6):"plain3",("FW_E",7):"plain3",
         ("FW_W",0):"plain3",("FW_W",1):"plain3",("FW_W",2):"gain+weave3",("FW_W",3):"plain4",
         ("FW_W",4):"weave4",("FW_W",5):"merge4",("FW_W",6):"plain4",("FW_W",7):"plain4"}
NOTE = {("FW_E",3):"OFF4386(2ln) ON4611 OFF4747 ON4900",
        ("FW_E",5):"OFF6827(2ln) 4->3@6840 ON7153 OFF7240 ON7448",
        ("FW_W",2):"OFF3425 ON3525 OFF3651 3->4@3817 ON3833",
        ("FW_W",4):"OFF5910 ON6075 OFF6225(2ln)", ("FW_W",5):"ON6777"}


def fit_kc_a(k, v, vf):
    def resid(p):
        kc, a = p
        return vf * np.exp(-(1.0 / a) * np.power(np.maximum(k, 1e-6) / kc, a)) - v
    best = None
    for kc0 in (12., 20., 28., 40.):
        for a0 in (1.0, 1.6, 2.4):
            try:
                r = least_squares(resid, [kc0, a0], bounds=([3., 0.6], [90., 6.]), max_nfev=3000)
            except Exception:
                continue
            if best is None or r.cost < best.cost:
                best = r
    kc, a = best.x
    return float(kc), float(a), float(np.sqrt(np.mean(best.fun ** 2)))


def fit_vf(k, v, kc, a):
    def resid(p):
        return p[0] * np.exp(-(1.0 / a) * np.power(np.maximum(k, 1e-6) / kc, a)) - v
    r = least_squares(resid, [110.0], bounds=([20.0], [140.0]), max_nfev=2000)
    return float(r.x[0]), float(np.sqrt(np.mean(r.fun ** 2)))


def main():
    src, outj, outp = sys.argv[1], sys.argv[2], sys.argv[3]
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = list(csv.DictReader(io.open(src, encoding="utf-8")))
    D = collections.defaultdict(list)
    for r in rows:
        D[(r["dir"], int(r["seg"]))].append((float(r["k_veh_km_lane"]), float(r["v_kph"]),
                                             float(r["q_edge_veh_h_lane"]), float(r["lanes"])))
    A = {key: np.array([[x[0], x[1], x[2]] for x in D[key]]) for key in D}
    LANES = {key: D[key][0][3] for key in D}

    # 급 대표 적합 — 평지 4차로는 E S0~S2 (자유~정체 전 구간), 평지 3차로는 W S0/S1 (정체지) + E S6/S7 (자유)
    pool4 = np.vstack([A[("FW_E", i)] for i in (0, 1, 2)])
    pool3 = np.vstack([A[("FW_W", 0)], A[("FW_W", 1)], A[("FW_E", 6)], A[("FW_E", 7)]])
    kc4, a4, r4 = fit_kc_a(pool4[:, 0], pool4[:, 1], VF_PLAIN)
    kc3, a3, r3 = fit_kc_a(pool3[:, 0], pool3[:, 1], VF_PLAIN)
    qc4 = kc4 * VF_PLAIN * np.exp(-1.0 / a4); qc3 = kc3 * VF_PLAIN * np.exp(-1.0 / a3)
    print("급 대표 적합 (v_f = %.1f 고정)" % VF_PLAIN)
    print("  plain4  k_cr=%.1f  a=%.2f  q_cap=%.0f veh/h/lane  RMSE=%.2f  (표본 %d, k %.1f~%.1f)"
          % (kc4, a4, qc4, r4, len(pool4), pool4[:, 0].min(), pool4[:, 0].max()))
    print("  plain3  k_cr=%.1f  a=%.2f  q_cap=%.0f veh/h/lane  RMSE=%.2f  (표본 %d, k %.1f~%.1f)"
          % (kc3, a3, qc3, r3, len(pool3), pool3[:, 0].min(), pool3[:, 0].max()))
    print()
    out = {"schema": "fd_fit_v2", "source": src, "v_free_plain_measured": VF_PLAIN,
           "class_fit": {"plain4": {"k_crit": kc4, "a": a4, "q_cap": qc4, "rmse": r4, "n": int(len(pool4))},
                         "plain3": {"k_crit": kc3, "a": a3, "q_cap": qc3, "rmse": r3, "n": int(len(pool3))}},
           "segments": {}}
    fig, axes = plt.subplots(4, 4, figsize=(19, 15))
    order = [("FW_E", i) for i in range(8)] + [("FW_W", i) for i in range(8)]
    print("%-6s %-3s %-12s %2s %6s %6s %6s %7s %6s | %7s %6s | %s" % (
        "dir", "seg", "class", "L", "k_min", "k_p95", "k_cr", "a", "q_cap", "v_f(B)", "RMSE", "판정"))
    for idx, key in enumerate(order):
        ax = axes[idx // 4][idx % 4]
        a_ = A[key]; k, v, qe = a_[:, 0], a_[:, 1], a_[:, 2]
        lanes = LANES[key]; cls = CLASS[key]
        base = (kc4, a4) if lanes >= 4 else (kc3, a3)
        kmin, kp95 = k.min(), np.percentile(k, 95)
        ident = kp95 >= 22.0
        rec = {"class": cls, "lanes": lanes, "note": NOTE.get(key, ""),
               "k_min": float(kmin), "k_p95": float(kp95), "identifiable": bool(ident)}
        if ident:
            kc, aa, rr = fit_kc_a(k, v, VF_PLAIN)
            qc = kc * VF_PLAIN * np.exp(-1.0 / aa)
            vfB, rrB = fit_vf(k, v, base[0], base[1])
            rec.update({"A_vf_fixed": {"v_free": VF_PLAIN, "k_crit": kc, "a": aa, "q_cap": qc, "rmse": rr},
                        "B_shape_fixed": {"v_free": vfB, "k_crit": base[0], "a": base[1],
                                          "q_cap": base[0] * vfB * np.exp(-1.0 / base[1]), "rmse": rrB}})
            verdict = "용량 식별 가능"
            print("%-6s %-3d %-12s %2d %6.1f %6.1f %6.1f %7.2f %6.0f | %7.1f %6.2f | %s"
                  % (key[0], key[1], cls, lanes, kmin, kp95, kc, aa, qc, vfB, rr, verdict))
            kk = np.linspace(0.5, max(k.max(), kc * 2.0), 200)
            ax.plot(kk, kk * VF_PLAIN * np.exp(-(1.0 / aa) * (kk / kc) ** aa), "k-", lw=1.6, label="A: v_f 고정")
            ax.plot(kk, kk * vfB * np.exp(-(1.0 / base[1]) * (kk / base[0]) ** base[1]), "--",
                    color="#888", lw=1.3, label="B: 형상 고정")
            ax.plot([kc], [qc], "k*", ms=11)
        else:
            vf_meas = float(v[k < 10].mean()) if (k < 10).sum() > 20 else float("nan")
            rec.update({"free_only_v_at_k_lt10": vf_meas})
            print("%-6s %-3d %-12s %2d %6.1f %6.1f %6s %7s %6s | %7.1f %6s | 자유류만 — 용량 미식별"
                  % (key[0], key[1], cls, lanes, kmin, kp95, "-", "-", "-", vf_meas, "-"))
        kk = np.linspace(0.5, max(k.max(), base[0] * 1.6), 200)
        ax.plot(kk, kk * VF_PLAIN * np.exp(-(1.0 / base[1]) * (kk / base[0]) ** base[1]), ":",
                color="#c1121f", lw=1.4, label="평지 %d차로 기준" % (4 if lanes >= 4 else 3))
        w = 12
        ax.scatter(np.convolve(k, np.ones(w) / w, mode="same"), np.convolve(qe, np.ones(w) / w, mode="same"),
                   s=3, alpha=0.25, c="#1b4965")
        ax.set_title("%s S%d  %s  (%d차로)\n%s" % (key[0], key[1], cls, lanes,
                                                NOTE.get(key, "램프 없음 · 차로수 일정")), fontsize=8.5)
        ax.set_xlabel("k [veh/km/lane]", fontsize=8); ax.set_ylabel("q [veh/h/lane]", fontsize=8)
        ax.tick_params(labelsize=7); ax.grid(alpha=0.25); ax.set_ylim(0, 2400); ax.set_xlim(0, 120)
        if idx == 0:
            ax.legend(fontsize=7, loc="upper right")
        out["segments"]["%s_S%d" % (key[0], key[1])] = rec
    fig.suptitle("Ver2 무제어(v0) 세그먼트별 기본도 q–k · 점=실측(60 s 평활) · 검정=세그먼트 적합 · 빨강 점선=평지 기준곡선", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.97]); fig.savefig(outp, dpi=115)
    io.open(outj, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print("\n→ %s\n→ %s" % (outj, outp))


if __name__ == "__main__":
    main()
