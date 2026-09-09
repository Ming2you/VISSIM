# -*- coding: utf-8 -*-
"""two-branch(삼각형/Newell) FD 를 **무제어 런**에서 적합한다 (2026-09-09).

왜 무제어인가. VSL 이 전 구간 120 이라 자유가지가 v_free 로 앵커된 순수 관측이고, 제어 런의
VSL 개입이 FD 를 오염시키지 않는다.

vendor 구현이 요구하는 형태 (`metanet.py:18-68`):

    w        = v_free · ρ_crit_tb / (ρ_jam − ρ_crit_tb)        고정 backward-wave
    ρ_c(vsl) = w · ρ_jam / (vsl + w)                            VSL↓ → ρ_c↑
    ρ ≤ ρ_c : v = vsl                자유가지(= VSL 로 회전)
    ρ >  ρ_c : v = w(ρ_jam − ρ)/ρ    혼잡가지(고정)  ⇒  q = w(ρ_jam − ρ)

**자유 파라미터는 사실상 ρ_jam 하나다.** 셀별 v_free 와 q_cap 은 D-lit 표
(`outputs/freeway_segment_params_dlit_20260908.json`)에 이미 적합돼 있고, 삼각형 nominal 은
ρ_crit_tb = q_cap / v_free 로 따라 나온다.

배선 제약 (실측으로 확인):
  * `metanet.py:620-621` 이 `net.rho_max` 와 `net.rho_crit_two_branch` 를 **네트워크 스칼라**로 읽는다.
  * 어댑터의 `_patched_effective_desired_speed_kmh` 는 셀별 `p["rho_max"]` 로 `rho_jam` 만 덮는다.
    `rho_crit_tb` 는 그대로 통과 → **셀별로 줄 수 없다.**
  * `effective_rho_crit(net, vsl)`(capacity-drop 등이 쓰는 것)도 두 값 모두 스칼라로 읽는다.
  ⇒ ρ_jam 은 셀별로 줄 수 있고 ρ_crit_tb 는 스칼라여야 한다. 그래서 스칼라 선택의 근거를 남긴다.

혼잡가지 적합. q_lane = w(ρ_jam − ρ) 는 (ρ, q_lane) 평면의 직선이다. 혼잡 표본만 골라
최소자승으로 절편·기울기를 얻고 ρ_jam = 절편/기울기, w = 기울기 로 읽는다. 단
  * 표본이 적은 셀(혼잡을 겪지 않는 하류)은 적합하지 않고 **풀링 값**으로 채운다.
  * ρ_jam 은 그 셀 관측 최대 ρ 보다 커야 한다(CTM receiving 이 음수가 되면 안 된다).

사용: python fit_two_branch_fd_ver2_20260909.py [출력json]
"""
import io
import json
import statistics
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
RUN = R / "evaluation/runs/n21_x15_nocontrol_ver2_20260907"
DLIT = R / "outputs/freeway_segment_params_dlit_20260908.json"
MIN_CONG = 6          # 셀별 적합에 필요한 최소 혼잡 표본
CONG_FRAC = 0.75      # v < CONG_FRAC · v_free 를 혼잡으로 본다
JAM_MARGIN = 1.08     # ρ_jam 하한 = 관측 최대 ρ × 이 값


def samples():
    """셀별 (ρ[veh/km/lane], v[km/h], q_lane[veh/h/lane]) 표본."""
    dd = list(RUN.glob("decisions_*"))
    if not dd:
        raise SystemExit("무제어 런 결정 폴더가 없다: %s" % RUN)
    out = {}
    for p in sorted(dd[0].glob("state_*.json")):
        js = json.load(io.open(p, encoding="utf-8"))
        for link, rows in (js.get("freeway_segments") or {}).items():
            for i, r in enumerate(rows):
                cnt = float(r.get("count", 0.0))
                if cnt <= 0.0:
                    continue
                L = float(r.get("length_km", 0.0)) or 1e-9
                lanes = max(1.0, float(r.get("lanes", 1.0)))
                rho = cnt / (L * lanes)
                v = float(r.get("speed_sum", 0.0)) / cnt
                out.setdefault("%s_S%d" % (link, i), []).append((rho, v, rho * v))
    return out


def fit_line(pts):
    """q = a + b·ρ 최소자승. 반환 (ρ_jam = −a/b, w = −b). b<0 이어야 유효."""
    n = len(pts)
    sx = sum(x for x, _ in pts)
    sy = sum(y for _, y in pts)
    sxx = sum(x * x for x, _ in pts)
    sxy = sum(x * y for x, y in pts)
    den = n * sxx - sx * sx
    if abs(den) < 1e-9:
        return None
    b = (n * sxy - sx * sy) / den
    a = (sy - b * sx) / n
    if b >= -1e-9:
        return None
    return (-a / b, -b)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    outj = sys.argv[1] if len(sys.argv) > 1 else "outputs/two_branch_fd_ver2_20260909.json"
    dlit = json.load(io.open(DLIT, encoding="utf-8"))["segments"]
    data = samples()

    # 1) 셀별 삼각형 nominal ρ_crit_tb = q_cap / v_free (D-lit 이 이미 적합한 두 값에서 파생)
    print("=== 셀별 삼각형 nominal ρ_crit_tb = q_cap / v_free ===")
    tb = {}
    for cell, p in sorted(dlit.items()):
        vf = float(p["v_free"])
        qc = float(p["q_cap_veh_h_lane"])
        tb[cell] = qc / max(vf, 1e-9)
    vals = sorted(tb.values())
    print("  n=%d  최소 %.2f  중앙 %.2f  최대 %.2f  (사분 %.2f~%.2f)"
          % (len(vals), vals[0], statistics.median(vals), vals[-1],
             vals[len(vals) // 4], vals[3 * len(vals) // 4]))

    # 2) 혼잡가지 적합 (셀별) → ρ_jam
    print("\n=== 혼잡가지 적합  q_lane = w(ρ_jam − ρ) ===")
    print("%-10s %6s %8s %9s %9s %9s   %s" % ("셀", "혼잡n", "관측maxρ", "ρ_jam", "w", "삼각cap", "판정"))
    fits, jam_ok = {}, []
    for cell in sorted(data):
        p = dlit.get(cell)
        if not p:
            continue
        vf = float(p["v_free"])
        pts_all = data[cell]
        rho_max_obs = max(x for x, _, _ in pts_all)
        cong = [(x, q) for x, v, q in pts_all if v < CONG_FRAC * vf and x > 0.0]
        rec = {"v_free": vf, "q_cap_veh_h_lane": float(p["q_cap_veh_h_lane"]),
               "rho_crit_tb_implied": round(tb[cell], 3),
               "n_congested": len(cong), "rho_max_observed": round(rho_max_obs, 2)}
        if len(cong) < MIN_CONG:
            rec["status"] = "표본부족"
            fits[cell] = rec
            continue
        f = fit_line(cong)
        if f is None:
            rec["status"] = "기울기 양수(무효)"
            fits[cell] = rec
            continue
        rho_jam, w = f
        rec.update({"rho_jam_fit": round(rho_jam, 2), "w_fit": round(w, 3)})
        if rho_jam < rho_max_obs * JAM_MARGIN:
            rec["status"] = "ρ_jam < 관측최대x%.2f — 기각" % JAM_MARGIN
        else:
            rec["status"] = "ok"
            jam_ok.append(rho_jam)
        fits[cell] = rec
        print("%-10s %6d %8.1f %9.1f %9.2f %9.0f   %s"
              % (cell, len(cong), rho_max_obs, rho_jam, w, vf * tb[cell], rec["status"]))

    if not jam_ok:
        raise SystemExit("유효한 ρ_jam 적합이 하나도 없다 — 혼잡 표본/선택 기준을 재검토해라")
    jam_med = statistics.median(jam_ok)
    rho_max_all = max(max(x for x, _, _ in v) for v in data.values())
    jam_scalar = max(jam_med, rho_max_all * JAM_MARGIN)
    tb_scalar = statistics.median(vals)

    print("\n=== 스칼라 채택 ===")
    print("  유효 ρ_jam 적합 %d개  중앙 %.1f" % (len(jam_ok), jam_med))
    print("  전 셀 관측 최대 ρ = %.1f  → 하한 %.1f (x%.2f)" % (rho_max_all, rho_max_all * JAM_MARGIN, JAM_MARGIN))
    print("  ρ_jam(scalar)          = %.1f" % jam_scalar)
    print("  ρ_crit_two_branch      = %.2f  (셀별 q_cap/v_free 중앙값)" % tb_scalar)
    w_s = 120.0 * tb_scalar / max(jam_scalar - tb_scalar, 1e-9)
    print("  함의 w(v_free 120)     = %.2f km/h" % w_s)
    print("  삼각형 용량(v_free 120)= %.0f veh/h/lane  (4차로 %.0f veh/h)"
          % (120.0 * tb_scalar, 4 * 120.0 * tb_scalar))

    print("\n=== VSL 이 임계밀도를 옮기는가 (ρ_c(vsl) = w·ρ_jam/(vsl+w)) ===")
    for vsl in (120.0, 100.0, 80.0, 70.0, 60.0):
        rc = w_s * jam_scalar / (vsl + w_s)
        print("   vsl %5.0f -> ρ_c %6.2f   삼각 용량 %7.0f veh/h/lane" % (vsl, rc, vsl * rc))

    doc = {"schema": "two_branch_fd/1", "generated": "2026-09-09",
           "source_run": RUN.name, "source_params": DLIT.name,
           "why": "vsl_fd_two_branch 를 켜려면 ρ_jam 과 삼각형 nominal ρ_crit_tb 가 필요하다. "
                  "셀별 v_free·q_cap 은 D-lit 이 이미 적합했으므로 자유 파라미터는 ρ_jam 뿐이다.",
           "wiring_note": "metanet.py:620-621 이 net.rho_max·net.rho_crit_two_branch 를 네트워크 "
                          "스칼라로 읽는다. 어댑터는 셀별 p['rho_max'] 로 rho_jam 만 덮으므로 "
                          "ρ_crit_tb 는 셀별로 줄 수 없다.",
           "method": {"congested_selector": "v < %.2f x v_free" % CONG_FRAC,
                      "min_congested_samples": MIN_CONG,
                      "jam_lower_bound": "관측 최대 ρ x %.2f" % JAM_MARGIN},
           "scalars": {"rho_max": round(jam_scalar, 2),
                       "rho_crit_two_branch": round(tb_scalar, 3),
                       "implied_w_at_vfree120": round(w_s, 3),
                       "triangular_cap_veh_h_lane_at_120": round(120.0 * tb_scalar, 1)},
           "per_cell": fits}
    io.open(outj, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print("\n-> %s" % outj)


if __name__ == "__main__":
    main()
