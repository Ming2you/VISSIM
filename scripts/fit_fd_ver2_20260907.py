# -*- coding: utf-8 -*-
"""Ver2 v0 세그먼트별 q-k 기본도 적합 + 그림 (2026-09-07).
METANET 정상상태 속도식  V(k) = v_f · exp[ -(1/a) · (k/k_cr)^a ]  를 세그먼트별로 최소제곱 적합하고
용량 q_cap = k_cr · v_f · exp(-1/a) [veh/h/lane] 를 낸다.
사용: python fit_fd_ver2_20260907.py <fd_samples_csv> <out_json> <out_png>"""
import io, sys, json, csv, collections
import numpy as np
from scipy.optimize import least_squares
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 세그먼트 분류 (사슬 위치 기준, 2026-09-07 커넥터 전수조사)
CLASS = {
 ("FW_E",0):"plain4",   ("FW_E",1):"plain4",   ("FW_E",2):"plain4",
 ("FW_E",3):"weave4",   ("FW_E",4):"plain4",   ("FW_E",5):"drop+weave3",
 ("FW_E",6):"plain3",   ("FW_E",7):"plain3",
 ("FW_W",0):"plain3",   ("FW_W",1):"plain3",   ("FW_W",2):"gain+weave3",
 ("FW_W",3):"plain4",   ("FW_W",4):"weave4",   ("FW_W",5):"merge4",
 ("FW_W",6):"plain4",   ("FW_W",7):"plain4",
}
NOTE = {
 ("FW_E",3):"OFF 4386(2ln)·ON 4611·OFF 4747·ON 4900",
 ("FW_E",5):"OFF 6827(2ln)·차로 4→3 6840·ON 7153·OFF 7240·ON 7448",
 ("FW_W",2):"OFF 3425·ON 3525·OFF 3651·차로 3→4 3817·ON 3833",
 ("FW_W",4):"OFF 5910·ON 6075·OFF 6225(2ln)",
 ("FW_W",5):"ON 6777",
}


def fit_seg(k, v):
    """V(k)=v_f exp(-(1/a)(k/k_cr)^a) 적합. 자료 범위가 좁으면 v_f 만 낸다."""
    ok = np.isfinite(k) & np.isfinite(v) & (k > 0)
    k, v = k[ok], v[ok]
    if len(k) < 50:
        return None
    krange = np.percentile(k, 95) - np.percentile(k, 5)
    vf0 = np.percentile(v[k <= np.percentile(k, 15)], 90) if (k <= np.percentile(k, 15)).sum() > 5 else v.max()
    if krange < 8.0:
        return {"v_free": float(vf0), "k_crit": None, "a": None, "q_cap": None,
                "rmse": None, "n": int(len(k)), "k_span": float(krange), "identifiable": False}

    def resid(p):
        vf, kc, a = p
        return vf * np.exp(-(1.0 / a) * np.power(np.maximum(k, 1e-6) / kc, a)) - v

    best = None
    for kc0 in (15.0, 25.0, 35.0, 50.0):
        for a0 in (1.2, 1.8, 2.5):
            try:
                r = least_squares(resid, [max(vf0, 60.0), kc0, a0],
                                  bounds=([30.0, 3.0, 0.6], [160.0, 120.0, 6.0]), max_nfev=4000)
            except Exception:
                continue
            if best is None or r.cost < best.cost:
                best = r
    if best is None:
        return None
    vf, kc, a = best.x
    rmse = float(np.sqrt(np.mean(best.fun ** 2)))
    qcap = float(kc * vf * np.exp(-1.0 / a))
    return {"v_free": float(vf), "k_crit": float(kc), "a": float(a), "q_cap": qcap,
            "rmse": rmse, "n": int(len(k)), "k_span": float(krange), "identifiable": True}


def main():
    src, outj, outp = sys.argv[1], sys.argv[2], sys.argv[3]
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = list(csv.DictReader(io.open(src, encoding="utf-8")))
    D = collections.defaultdict(list)
    for r in rows:
        D[(r["dir"], int(r["seg"]))].append((float(r["k_veh_km_lane"]), float(r["v_kph"]),
                                             float(r["q_kv_veh_h_lane"]), float(r["q_edge_veh_h_lane"]),
                                             int(r["n"]), float(r["lanes"]), float(r["t"])))
    out = {"schema": "fd_fit_v1", "source": src, "segments": {}}
    fig, axes = plt.subplots(4, 4, figsize=(19, 15))
    order = [("FW_E", i) for i in range(8)] + [("FW_W", i) for i in range(8)]
    print("%-6s %-3s %-12s %6s %8s %7s %6s %9s %7s  %s" % (
        "dir", "seg", "class", "lanes", "v_free", "k_crit", "a", "q_cap", "rmse", "표본 k 범위"))
    for idx, key in enumerate(order):
        ax = axes[idx // 4][idx % 4]
        a = np.array([[x[0], x[1], x[2], x[3], x[4], x[5]] for x in D[key]])
        k, v, qkv, qe, n, lanes = a[:, 0], a[:, 1], a[:, 2], a[:, 3], a[:, 4], a[:, 5]
        # 60 s 이동평균으로 경계유량 잡음 완화 (표본 5 s)
        w = 12
        qe_s = np.convolve(qe, np.ones(w) / w, mode="same")
        k_s = np.convolve(k, np.ones(w) / w, mode="same")
        f = fit_seg(k, v)
        cls = CLASS[key]
        out["segments"]["%s_S%d" % (key[0], key[1])] = {"class": cls, "lanes": float(lanes[0]),
                                                        "note": NOTE.get(key, ""), "fit": f}
        col = {"plain3": "#2a6f97", "plain4": "#1b4965", "weave4": "#bc4749", "merge4": "#e07a5f",
               "drop+weave3": "#8338ec", "gain+weave3": "#c1121f"}[cls]
        ax.scatter(k_s, qe_s, s=3, alpha=0.25, c=col, label="측정 (60 s 평활)")
        if f and f.get("identifiable"):
            kk = np.linspace(0.5, max(k.max(), f["k_crit"] * 2.2), 200)
            vv = f["v_free"] * np.exp(-(1.0 / f["a"]) * (kk / f["k_crit"]) ** f["a"])
            ax.plot(kk, kk * vv, "k-", lw=1.6, label="METANET 적합")
            ax.axvline(f["k_crit"], color="k", ls=":", lw=1)
            ax.plot([f["k_crit"]], [f["q_cap"]], "k*", ms=11)
        ax.set_title("%s S%d  %s  (%dL)\n%s" % (key[0], key[1], cls, lanes[0], NOTE.get(key, "차로수 일정·램프 없음")),
                     fontsize=8.5)
        ax.set_xlabel("k [veh/km/lane]", fontsize=8); ax.set_ylabel("q [veh/h/lane]", fontsize=8)
        ax.tick_params(labelsize=7); ax.grid(alpha=0.25); ax.set_ylim(0, 2400)
        if idx == 0:
            ax.legend(fontsize=7)
        line = "%-6s %-3d %-12s %6.0f" % (key[0], key[1], cls, lanes[0])
        if f is None:
            line += "   자료 부족"
        elif not f["identifiable"]:
            line += " %8.1f %7s %6s %9s %7s  k 범위 %.1f (자유류만)" % (f["v_free"], "-", "-", "-", "-", f["k_span"])
        else:
            line += " %8.1f %7.1f %6.2f %9.0f %7.2f  k %.1f~%.1f" % (
                f["v_free"], f["k_crit"], f["a"], f["q_cap"], f["rmse"], k.min(), k.max())
        print(line)
    fig.suptitle("Ver2 무제어(v0) 본선 세그먼트별 기본도  q–k  ·  점=실측(60 s 평활), 선=METANET V(k) 적합, ★=용량", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(outp, dpi=115)
    io.open(outj, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print("\n→ %s\n→ %s" % (outj, outp))


if __name__ == "__main__":
    main()
