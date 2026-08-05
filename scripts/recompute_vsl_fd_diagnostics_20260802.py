# vsl_sensitivity_20260801.md 의 FD 의존 진단치를 새 FD/새 플랜트 점군으로 다시 계산한다.
"""실행:
    "C:/Users/alsrj/anaconda3/python.exe" scripts/recompute_vsl_fd_diagnostics_20260802.py

재계산 대상은 세 가지다(구 수치는 outputs/vsl_sensitivity_20260801.md 에 그대로 둔다).
  1. 내부 FD V(rho) 대 VISSIM 실측 평균속도의 RMSE / bias(모델-실측)
  2. 실측 밀도 분포 분위수와 rho_crit 초과 비율
  3. VSL 구속 상한 rho_bind(vsl) 과 운영 밀도 중 구속 비율

주의 — 구속 방향. V(rho) 는 rho 에 대해 단조감소이므로 VSL 은 rho <= rho_bind 에서만 구속한다.
"""
from __future__ import annotations

import csv
import io
import json
import math
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]

NEW_POINTS = [
    ROOT / "outputs/no_control_fd_mfd_20260802_scale135_freeway_fd_points.csv",
    ROOT / "outputs/no_control_fd_mfd_20260802_scale170_freeway_fd_points.csv",
]
OLD_POINTS = [ROOT / "outputs/no_control_fd_mfd_20260724_freeway_fd_points.csv"]
FIT_JSON = ROOT / "outputs/fd_refit_20260802_fit.json"
FIT_KEY = "alt_unconstrained"

# 이름 -> (v_free, rho_crit, a)
OLD_EFFECTIVE = (120.0, 30.0, 1.867)   # adapter_v1 calibration_override 가 실제로 컨트롤러에 준 값
OLD_CALIBRATION = (100.0, 24.0, 1.867)  # real_world_modi_control_v0_20260719.json 파일값
VSL_MENU = [80.0, 100.0, 120.0]


def V(rho: float, v_free: float, rho_crit: float, a: float) -> float:
    return float(v_free * math.exp(-(1.0 / a) * ((max(rho, 0.0) / rho_crit) ** a)))


def rho_bind(vsl: float, v_free: float, rho_crit: float, a: float) -> float | None:
    if vsl >= v_free:
        return None
    return float(rho_crit * (a * math.log(v_free / vsl)) ** (1.0 / a))


def load(paths: list[Path]) -> list[dict[str, float]]:
    out = []
    for p in paths:
        with p.open(newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                try:
                    rho = float(r["density_veh_km_lane"])
                    spd = float(r["mean_speed_kph"])
                    cnt = float(r["count"])
                except (KeyError, TypeError, ValueError):
                    continue
                if cnt <= 0 or rho <= 0 or spd <= 0:
                    continue
                out.append({"rho": rho, "speed": spd, "link": r.get("model_link", "")})
    return out


def pct(values: list[float], q: float) -> float:
    o = sorted(values)
    pos = (len(o) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(o) - 1)
    return o[lo] * (1 - (pos - lo)) + o[hi] * (pos - lo)


def metrics(points: list[dict], p: tuple[float, float, float]) -> dict[str, float]:
    n = len(points)
    sse = bias = mae = 0.0
    for r in points:
        d = V(r["rho"], *p) - r["speed"]
        sse += d * d
        bias += d
        mae += abs(d)
    return {"n": n, "rmse": math.sqrt(sse / n), "bias_model_minus_obs": bias / n, "mae": mae / n}


def band_table(points: list[dict], p: tuple[float, float, float]) -> list[dict]:
    edges = [(0, 5), (5, 10), (10, 15), (15, 20), (20, 25), (25, 30), (30, 40)]
    rows = []
    for lo, hi in edges:
        sel = [r for r in points if lo <= r["rho"] < hi]
        if not sel:
            continue
        rho_m = sum(r["rho"] for r in sel) / len(sel)
        obs = sum(r["speed"] for r in sel) / len(sel)
        mdl = V(rho_m, *p)
        rows.append({"lo": lo, "hi": hi, "n": len(sel), "rho_mean": rho_m,
                     "obs": obs, "model": mdl, "dev_obs_minus_model": obs - mdl})
    return rows


def main() -> int:
    fit = json.loads(FIT_JSON.read_text(encoding="utf-8"))["fits"][FIT_KEY]
    new_p = (float(fit["v_free"]), float(fit["rho_crit"]), float(fit["a"]))

    new_pts = load(NEW_POINTS)
    old_pts = load(OLD_POINTS)
    rhos = [r["rho"] for r in new_pts]
    speeds = [r["speed"] for r in new_pts]

    result: dict[str, object] = {
        "adopted_fit": {"key": FIT_KEY, "v_free_kph": new_p[0], "rho_crit_veh_km_lane": new_p[1],
                        "metanet_a_m": new_p[2],
                        "capacity_veh_h_link": fit["capacity_veh_h_link"]},
        "point_sets": {
            "new_20260802": {"files": [str(p) for p in NEW_POINTS], "n": len(new_pts)},
            "old_20260724": {"files": [str(p) for p in OLD_POINTS], "n": len(old_pts)},
        },
    }

    # (1) FD vs 실측 편향
    result["fd_vs_observation"] = {
        "old_effective_120_30_on_old_points": metrics(old_pts, OLD_EFFECTIVE),
        "old_effective_120_30_on_new_points": metrics(new_pts, OLD_EFFECTIVE),
        "old_calibration_100_24_on_new_points": metrics(new_pts, OLD_CALIBRATION),
        "refit_20260802_on_new_points": metrics(new_pts, new_p),
        "refit_20260802_band_table": band_table(new_pts, new_p),
        "old_effective_band_table_on_new_points": band_table(new_pts, OLD_EFFECTIVE),
    }

    # (2) 밀도/속도 분포
    old_rhos = [r["rho"] for r in old_pts]
    result["density_distribution"] = {
        "new": {"min": min(rhos), "p50": pct(rhos, .50), "p90": pct(rhos, .90),
                "p95": pct(rhos, .95), "max": max(rhos),
                "frac_gt_rho_crit_new": sum(1 for r in rhos if r > new_p[1]) / len(rhos),
                "frac_gt_30_old_rho_crit": sum(1 for r in rhos if r > 30.0) / len(rhos)},
        "old": {"min": min(old_rhos), "p50": pct(old_rhos, .50), "p90": pct(old_rhos, .90),
                "p95": pct(old_rhos, .95), "max": max(old_rhos),
                "frac_gt_30_old_rho_crit": sum(1 for r in old_rhos if r > 30.0) / len(old_rhos)},
    }
    result["speed_distribution_new"] = {
        "min": min(speeds), "p50": pct(speeds, .50), "p90": pct(speeds, .90),
        "p95": pct(speeds, .95), "max": max(speeds),
        "frac_gt_80": sum(1 for s in speeds if s > 80) / len(speeds),
        "frac_gt_100": sum(1 for s in speeds if s > 100) / len(speeds),
        "frac_gt_120": sum(1 for s in speeds if s > 120) / len(speeds),
    }

    # (3) VSL 구속
    binding = []
    for vsl in VSL_MENU:
        rb_new = rho_bind(vsl, *new_p)
        rb_old = rho_bind(vsl, *OLD_EFFECTIVE)
        row = {
            "vsl_kph": vsl,
            "new": {
                "rho_bind": rb_new,
                "ratio_to_rho_crit": (rb_new / new_p[1]) if rb_new is not None else None,
                "frac_operating_binding": (sum(1 for r in rhos if r <= rb_new) / len(rhos))
                                          if rb_new is not None else 0.0,
                "frac_operating_binding_above_rho_crit":
                    (sum(1 for r in rhos if r <= rb_new and r > new_p[1]) / len(rhos))
                    if rb_new is not None else 0.0,
            },
            "old_effective": {
                "rho_bind": rb_old,
                "ratio_to_rho_crit": (rb_old / OLD_EFFECTIVE[1]) if rb_old is not None else None,
                "frac_operating_binding_old_points":
                    (sum(1 for r in old_rhos if r <= rb_old) / len(old_rhos))
                    if rb_old is not None else 0.0,
            },
        }
        binding.append(row)
    result["vsl_binding"] = binding

    # 방향별
    per_link = {}
    for link in sorted({r["link"] for r in new_pts}):
        sub = [r for r in new_pts if r["link"] == link]
        sr = [r["rho"] for r in sub]
        per_link[link] = {
            "n": len(sub),
            "rho_p50": pct(sr, .50), "rho_p95": pct(sr, .95), "rho_max": max(sr),
            "refit_metrics": metrics(sub, new_p),
        }
    result["per_link_new"] = per_link

    out = ROOT / "outputs/vsl_fd_diagnostics_20260802.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print(f"\nJSON={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
