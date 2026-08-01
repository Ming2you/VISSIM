# 실측 no-control FD 점군에 METANET 지수형 속도-밀도식을 회귀 적합해 v_free/rho_crit/a/capacity를 뽑는다.
"""실행:
    "C:/Users/alsrj/anaconda3/python.exe" scripts/fit_freeway_fd_20260801.py \
        --points outputs/no_control_fd_mfd_20260801_freeway_fd_points.csv \
        --out-prefix outputs/fd_refit_20260801

적합 모델 (NumSim `src/models/metanet.py:desired_speed_kmh`와 동일 형태)
    V(rho) = v_free * exp(-(1/a) * (rho/rho_crit)**a)
    q_lane(rho) = rho * V(rho),  최대는 rho = rho_crit 에서
    q_cap_lane = rho_crit * v_free * exp(-1/a)

방식 — 상단 포락선(p95 envelope)이 아니라 **binned 평균 회귀 + capacity 등식 제약**이다.
구 캘리브레이션(v_free=100)이 저밀도 p95 상단에서 왔고 그 때문에 +35 km/h 편향이 생겼다
(outputs/vsl_sensitivity_20260801.md §1-4). 여기서는

  1. 밀도 2 veh/km/lane 폭으로 binning 하고 bin 별 평균 속도/평균 차로당 유량을 만든다.
  2. 관측 용량 q_cap_obs = (표본수 >= --cap-min-n 인 bin 의 평균 차로당 유량) 의 최대값.
  3. q_cap_lane(params) == q_cap_obs 등식 제약을 걸어 자유도를 (rho_crit, a) 2개로 줄이고
     v_free = q_cap_obs / (rho_crit * exp(-1/a)) 로 종속시킨다.
  4. bin 표본수 가중 최소제곱으로 (rho_crit, a) 를 격자 탐색 + 국소 세분화한다.

제약 없는 3파라미터 적합도 함께 계산해 대조로 남긴다(구 진단의 v_free≈95.3/rho_crit≈40.8/a≈1.0 재현용).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BIN_WIDTH = 2.0


def desired_speed_kmh(rho: float, v_free: float, rho_crit: float, a: float) -> float:
    ratio = max(rho, 0.0) / max(rho_crit, 1.0e-9)
    return float(v_free * math.exp(-(1.0 / a) * (ratio ** a)))


def cap_lane(v_free: float, rho_crit: float, a: float) -> float:
    """차로당 용량 = rho_crit * v_free * exp(-1/a) (dq/drho = 0 인 rho = rho_crit)."""
    return float(rho_crit * v_free * math.exp(-1.0 / a))


def fnum(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_points(paths: list[Path], links: set[str] | None) -> list[dict[str, float | str]]:
    points: list[dict[str, float | str]] = []
    for path in paths:
        with path.open(newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                count = fnum(row.get("count"))
                rho = fnum(row.get("density_veh_km_lane"))
                speed = fnum(row.get("mean_speed_kph"))
                if count <= 0.0 or rho <= 0.0 or speed <= 0.0:
                    # 빈 세그먼트는 mean_speed=0 으로 기록되므로 회귀에서 제외한다.
                    continue
                link = str(row.get("model_link", ""))
                if links and link not in links:
                    continue
                points.append({
                    "source": path.name,
                    "model_link": link,
                    "segment_index": int(fnum(row.get("segment_index"))),
                    "sim_sec": fnum(row.get("sim_sec")),
                    "rho": rho,
                    "speed": speed,
                    "lanes": fnum(row.get("lanes"), 1.0),
                    "q_lane": rho * speed,
                })
    return points


def make_bins(points: list[dict], bin_width: float = BIN_WIDTH) -> list[dict[str, float]]:
    groups: dict[float, list[dict]] = defaultdict(list)
    for row in points:
        center = (int(float(row["rho"]) / bin_width) + 0.5) * bin_width
        groups[center].append(row)
    bins = []
    for center in sorted(groups):
        rows = groups[center]
        n = len(rows)
        bins.append({
            "bin_center": center,
            "n": n,
            "rho_mean": sum(float(r["rho"]) for r in rows) / n,
            "speed_mean": sum(float(r["speed"]) for r in rows) / n,
            "q_lane_mean": sum(float(r["q_lane"]) for r in rows) / n,
        })
    return bins


def weighted_bin_sse(bins: list[dict], v_free: float, rho_crit: float, a: float,
                     weight_by_n: bool) -> float:
    sse = 0.0
    wsum = 0.0
    for b in bins:
        w = float(b["n"]) if weight_by_n else 1.0
        resid = float(b["speed_mean"]) - desired_speed_kmh(float(b["rho_mean"]), v_free, rho_crit, a)
        sse += w * resid * resid
        wsum += w
    return sse / max(wsum, 1.0e-12)


def fit_constrained(bins: list[dict], q_cap_obs_lane: float, weight_by_n: bool,
                    v_free_max: float | None = None) -> dict[str, float]:
    """capacity 등식 제약 하에서 (rho_crit, a) 격자 탐색 + 3단계 세분화."""
    best = None
    rho_lo, rho_hi = 5.0, 150.0
    a_lo, a_hi = 0.40, 5.00
    steps = 120
    for _ in range(4):
        rho_step = (rho_hi - rho_lo) / steps
        a_step = (a_hi - a_lo) / steps
        for i in range(steps + 1):
            rho_crit = rho_lo + i * rho_step
            if rho_crit <= 0.0:
                continue
            for j in range(steps + 1):
                a = a_lo + j * a_step
                if a <= 0.05:
                    continue
                v_free = q_cap_obs_lane / (rho_crit * math.exp(-1.0 / a))
                if v_free <= 0.0 or v_free > 400.0:
                    continue
                if v_free_max is not None and v_free > v_free_max:
                    continue
                mse = weighted_bin_sse(bins, v_free, rho_crit, a, weight_by_n)
                if best is None or mse < best[0]:
                    best = (mse, v_free, rho_crit, a)
        _mse, _v, _rc, _a = best
        rho_lo, rho_hi = max(1.0, _rc - 4 * rho_step), _rc + 4 * rho_step
        a_lo, a_hi = max(0.10, _a - 4 * a_step), _a + 4 * a_step
    mse, v_free, rho_crit, a = best
    return {"v_free": v_free, "rho_crit": rho_crit, "a": a, "bin_wrmse": math.sqrt(mse)}


def fit_unconstrained(bins: list[dict], weight_by_n: bool) -> dict[str, float]:
    best = None
    v_lo, v_hi = 40.0, 200.0
    rho_lo, rho_hi = 5.0, 150.0
    a_lo, a_hi = 0.40, 5.00
    steps = 40
    for _ in range(6):
        v_step = (v_hi - v_lo) / steps
        rho_step = (rho_hi - rho_lo) / steps
        a_step = (a_hi - a_lo) / steps
        for i in range(steps + 1):
            v_free = v_lo + i * v_step
            for j in range(steps + 1):
                rho_crit = rho_lo + j * rho_step
                if rho_crit <= 0.0:
                    continue
                for k in range(steps + 1):
                    a = a_lo + k * a_step
                    if a <= 0.05:
                        continue
                    mse = weighted_bin_sse(bins, v_free, rho_crit, a, weight_by_n)
                    if best is None or mse < best[0]:
                        best = (mse, v_free, rho_crit, a)
        _mse, _v, _rc, _a = best
        v_lo, v_hi = max(10.0, _v - 3 * v_step), _v + 3 * v_step
        rho_lo, rho_hi = max(1.0, _rc - 3 * rho_step), _rc + 3 * rho_step
        a_lo, a_hi = max(0.10, _a - 3 * a_step), _a + 3 * a_step
    mse, v_free, rho_crit, a = best
    return {"v_free": v_free, "rho_crit": rho_crit, "a": a, "bin_wrmse": math.sqrt(mse)}


def point_metrics(points: list[dict], v_free: float, rho_crit: float, a: float) -> dict[str, float]:
    """점 단위 지표. bias 는 (모델 − 실측) 부호로 보고한다(구 진단 표기와 동일)."""
    n = len(points)
    sse = 0.0
    bias = 0.0
    abs_err = 0.0
    for row in points:
        model = desired_speed_kmh(float(row["rho"]), v_free, rho_crit, a)
        diff = model - float(row["speed"])
        sse += diff * diff
        bias += diff
        abs_err += abs(diff)
    return {
        "n": n,
        "rmse_kph": math.sqrt(sse / max(n, 1)),
        "bias_model_minus_obs_kph": bias / max(n, 1),
        "mae_kph": abs_err / max(n, 1),
    }


def bias_table(points: list[dict], params: list[tuple[str, float, float, float]],
               edges=((0, 5), (5, 10), (10, 15), (15, 20), (20, 25), (25, 30),
                      (30, 40), (40, 60))) -> list[dict]:
    out = []
    for lo, hi in edges:
        sel = [r for r in points if lo <= float(r["rho"]) < hi]
        if not sel:
            continue
        rho_mid = sum(float(r["rho"]) for r in sel) / len(sel)
        obs = sum(float(r["speed"]) for r in sel) / len(sel)
        row = {"rho_lo": lo, "rho_hi": hi, "n": len(sel), "rho_mean": rho_mid, "obs_speed": obs}
        for name, v_free, rho_crit, a in params:
            model = desired_speed_kmh(rho_mid, v_free, rho_crit, a)
            row[f"model_{name}"] = model
            row[f"dev_{name}"] = obs - model
        out.append(row)
    return out


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def rho_bind(vsl: float, v_free: float, rho_crit: float, a: float) -> float:
    """V(rho) = vsl 이 되는 밀도. vsl >= v_free 이면 어디서도 구속하지 않는다(None 대용 0.0)."""
    if vsl >= v_free:
        return 0.0
    return float(rho_crit * (a * math.log(v_free / vsl)) ** (1.0 / a))


def plot(points: list[dict], bins: list[dict], fits: dict, out_png: Path,
         old: tuple[float, float, float]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    v_new, rc_new, a_new = fits["primary"]["v_free"], fits["primary"]["rho_crit"], fits["primary"]["a"]
    v_old, rc_old, a_old = old
    grid = [i * 0.5 for i in range(1, 241)]
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5), dpi=140, constrained_layout=True)
    colors = {"FW_E": "#1f77b4", "FW_W": "#d62728"}
    for link in sorted({str(r["model_link"]) for r in points}):
        rows = [r for r in points if str(r["model_link"]) == link]
        axes[0].scatter([float(r["rho"]) for r in rows], [float(r["speed"]) for r in rows],
                        s=8, alpha=0.25, color=colors.get(link), label=f"{link} points")
        axes[1].scatter([float(r["rho"]) for r in rows], [float(r["q_lane"]) for r in rows],
                        s=8, alpha=0.25, color=colors.get(link), label=f"{link} points")
    axes[0].scatter([b["rho_mean"] for b in bins], [b["speed_mean"] for b in bins],
                    s=40, color="black", marker="s", label="binned mean")
    axes[0].plot(grid, [desired_speed_kmh(r, v_new, rc_new, a_new) for r in grid],
                 color="#2ca02c", lw=2.2, label=f"fit 20260801 (v_free={v_new:.1f}, rho_c={rc_new:.1f}, a={a_new:.2f})")
    axes[0].plot(grid, [desired_speed_kmh(r, v_old, rc_old, a_old) for r in grid],
                 color="#ff7f0e", lw=1.6, ls="--", label=f"old v0 (v_free={v_old:.0f}, rho_c={rc_old:.0f}, a={a_old:.3f})")
    axes[0].set_xlabel("Density (veh/km/lane)")
    axes[0].set_ylabel("Speed (km/h)")
    axes[0].set_title("Speed-Density fit")

    axes[1].scatter([b["rho_mean"] for b in bins], [b["q_lane_mean"] for b in bins],
                    s=40, color="black", marker="s", label="binned mean")
    axes[1].plot(grid, [r * desired_speed_kmh(r, v_new, rc_new, a_new) for r in grid],
                 color="#2ca02c", lw=2.2, label="fit 20260801")
    axes[1].plot(grid, [r * desired_speed_kmh(r, v_old, rc_old, a_old) for r in grid],
                 color="#ff7f0e", lw=1.6, ls="--", label="old v0")
    axes[1].set_xlabel("Density (veh/km/lane)")
    axes[1].set_ylabel("Flow (veh/h/lane)")
    axes[1].set_title("Flow-Density (per lane)")
    for ax in axes:
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=7.5)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--points", nargs="+", required=True, type=Path)
    parser.add_argument("--out-prefix", type=Path, required=True)
    parser.add_argument("--lanes", type=float, default=4.0,
                        help="링크 용량 환산용 공칭 차로 수(캘리브레이션 freeway_capacity_veh_h 는 링크 단위).")
    parser.add_argument("--cap-min-n", type=int, default=10,
                        help="관측 용량으로 인정할 bin 의 최소 표본수.")
    parser.add_argument("--cap-interior-bins", type=int, default=2,
                        help="용량 bin 이 내부 최대인지 판정할 때 위쪽에서 확인할 유효 bin 수.")
    parser.add_argument("--vsl-menu", nargs="*", type=float, default=[80.0, 100.0, 120.0])
    parser.add_argument("--old", nargs=3, type=float, default=[100.0, 24.0, 1.867],
                        metavar=("V_FREE", "RHO_CRIT", "A"))
    parser.add_argument("--old-capacity-link", type=float, default=7600.0)
    args = parser.parse_args()

    points = load_points(args.points, None)
    if not points:
        raise SystemExit("no usable FD points")
    bins = make_bins(points)

    cap_bins = [b for b in bins if b["n"] >= args.cap_min_n]
    cap_bin = max(cap_bins, key=lambda b: b["q_lane_mean"])
    q_cap_obs_lane = float(cap_bin["q_lane_mean"])

    # capacity 등식 제약은 관측이 실제로 임계밀도를 **넘겼을 때만** 식별된다.
    # 데이터가 ρ_crit 아래에서 잘리면 관측 최대 유량이 진짜 용량이 아니라 절단점이 되고,
    # 그 값을 등식으로 박으면 ρ_crit이 아래로, a가 위로 끌려간다(합성 검증에서 확인).
    # 판정: 용량 bin 위쪽에 유효 bin이 --cap-interior-bins 개 이상 있고, 그 유량이 모두 더 낮다.
    above = [b for b in cap_bins if b["bin_center"] > cap_bin["bin_center"]]
    capacity_interior_max = (
        len(above) >= args.cap_interior_bins
        and all(b["q_lane_mean"] < q_cap_obs_lane for b in above[: args.cap_interior_bins])
    )

    primary = fit_constrained(bins, q_cap_obs_lane, weight_by_n=True)
    alt_equal_weight = fit_constrained(bins, q_cap_obs_lane, weight_by_n=False)
    unconstrained = fit_unconstrained(bins, weight_by_n=True)

    fits = {"primary": primary, "alt_equal_bin_weight": alt_equal_weight,
            "alt_unconstrained": unconstrained}
    for name, fit in fits.items():
        fit["capacity_veh_h_lane"] = cap_lane(fit["v_free"], fit["rho_crit"], fit["a"])
        fit["capacity_veh_h_link"] = fit["capacity_veh_h_lane"] * args.lanes
        fit["point_metrics"] = point_metrics(points, fit["v_free"], fit["rho_crit"], fit["a"])

    old_v, old_rc, old_a = args.old
    old_metrics = point_metrics(points, old_v, old_rc, old_a)

    # 링크별 참고 적합(캘리브레이션은 스칼라 1조라 pooled 를 쓴다).
    per_link = {}
    for link in sorted({str(r["model_link"]) for r in points}):
        sub = [r for r in points if str(r["model_link"]) == link]
        sub_bins = make_bins(sub)
        sub_cap_bins = [b for b in sub_bins if b["n"] >= args.cap_min_n]
        if not sub_cap_bins:
            continue
        sub_cap = max(b["q_lane_mean"] for b in sub_cap_bins)
        f = fit_constrained(sub_bins, sub_cap, weight_by_n=True)
        f["capacity_veh_h_lane"] = cap_lane(f["v_free"], f["rho_crit"], f["a"])
        f["capacity_veh_h_link"] = f["capacity_veh_h_lane"] * args.lanes
        f["observed_capacity_veh_h_lane"] = sub_cap
        f["point_metrics"] = point_metrics(sub, f["v_free"], f["rho_crit"], f["a"])
        per_link[link] = f

    speeds = [float(r["speed"]) for r in points]
    rhos = [float(r["rho"]) for r in points]
    coverage = {
        "speed_p50": percentile(speeds, 0.50),
        "speed_p90": percentile(speeds, 0.90),
        "speed_p95": percentile(speeds, 0.95),
        "speed_max": max(speeds),
        "rho_p50": percentile(rhos, 0.50),
        "rho_p90": percentile(rhos, 0.90),
        "rho_p95": percentile(rhos, 0.95),
        "rho_max": max(rhos),
        "frac_speed_gt_80": sum(1 for s in speeds if s > 80.0) / len(speeds),
        "frac_speed_gt_100": sum(1 for s in speeds if s > 100.0) / len(speeds),
        "frac_speed_gt_120": sum(1 for s in speeds if s > 120.0) / len(speeds),
        "frac_rho_gt_rho_crit_fit": sum(1 for r in rhos if r > primary["rho_crit"]) / len(rhos),
    }

    menu = sorted(args.vsl_menu)
    binding = []
    for vsl in menu:
        rb_new = rho_bind(vsl, primary["v_free"], primary["rho_crit"], primary["a"])
        rb_old = rho_bind(vsl, old_v, old_rc, old_a)
        binding.append({
            "vsl_kph": vsl,
            "binds_at_all_new": vsl < primary["v_free"],
            "rho_bind_new": rb_new,
            "frac_points_binding_new": (sum(1 for r in rhos if r >= rb_new) / len(rhos)
                                        if vsl < primary["v_free"] else 0.0),
            "binds_at_all_old": vsl < old_v,
            "rho_bind_old": rb_old,
            "frac_points_binding_old": (sum(1 for r in rhos if r >= rb_old) / len(rhos)
                                        if vsl < old_v else 0.0),
        })

    table = bias_table(points, [("new", primary["v_free"], primary["rho_crit"], primary["a"]),
                                ("old", old_v, old_rc, old_a)])

    out_prefix = args.out_prefix
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    png = out_prefix.with_name(out_prefix.name + "_fd_fit.png")
    try:
        plot(points, bins, fits, png, (old_v, old_rc, old_a))
        png_path = str(png)
    except Exception as exc:  # matplotlib 부재 시에도 수치 산출물은 남긴다
        png_path = f"SKIPPED: {exc}"

    summary = {
        "inputs": [str(p) for p in args.points],
        "point_count_used": len(points),
        "bin_width_veh_km_lane": BIN_WIDTH,
        "nominal_lanes": args.lanes,
        "observed_capacity": {
            "q_cap_obs_veh_h_lane": q_cap_obs_lane,
            "q_cap_obs_veh_h_link": q_cap_obs_lane * args.lanes,
            "bin_center_veh_km_lane": cap_bin["bin_center"],
            "bin_rho_mean": cap_bin["rho_mean"],
            "bin_n": cap_bin["n"],
            "cap_min_n": args.cap_min_n,
            "capacity_bin_is_interior_max": capacity_interior_max,
            "identifiability_note": (
                "OK: 관측이 임계밀도를 넘겨 용량 등식 제약이 식별된다."
                if capacity_interior_max else
                "WARN: 관측 유량이 상단에서 잘려 최대 bin 이 절단점일 수 있다. "
                "이 경우 용량 제약이 rho_crit 을 아래로, a 를 위로 당기므로 "
                "alt_unconstrained 를 우선 검토하라."
            ),
        },
        "method": {
            "model": "V(rho) = v_free * exp(-(1/a) * (rho/rho_crit)**a)",
            "primary": "binned mean (2 veh/km/lane) + bin-count-weighted least squares, "
                       "capacity equality constraint q_cap_lane == observed binned-mean max",
            "not_used": "low-density p95 upper envelope (source of the +35 km/h bias in v0)",
            "excluded_points": "count == 0 or density == 0 or speed == 0 (empty segments)",
        },
        "fits": fits,
        "per_link_fits": per_link,
        "old_v0": {
            "v_free_kph": old_v, "rho_crit_veh_km_lane": old_rc, "metanet_a_m": old_a,
            "capacity_veh_h_link_declared": args.old_capacity_link,
            "capacity_veh_h_link_implied_by_fd": cap_lane(old_v, old_rc, old_a) * args.lanes,
            "point_metrics": old_metrics,
        },
        "coverage": coverage,
        "vsl_menu_binding": binding,
        "bias_table": table,
        "bins": bins,
        "outputs": {"png": png_path},
    }
    json_path = out_prefix.with_name(out_prefix.name + "_fit.json")
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("bins", "bias_table")},
                     indent=2, ensure_ascii=False))
    print("\n=== bias table (rho band | n | obs | model_new | dev_new | model_old | dev_old) ===")
    for row in table:
        print(f"{row['rho_lo']:2.0f}-{row['rho_hi']:2.0f} | {row['n']:4d} | {row['obs_speed']:6.1f} | "
              f"{row['model_new']:6.1f} | {row['dev_new']:+6.1f} | "
              f"{row['model_old']:6.1f} | {row['dev_old']:+6.1f}")
    print(f"\nJSON={json_path}")


if __name__ == "__main__":
    main()
