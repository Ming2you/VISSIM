#!/usr/bin/env python3
"""보존 단위(저류 + 그 저류에 대기하는 movement 큐)로 rollout 오차를 잰다.

## 왜 이걸 먼저 재야 하나

`diagnose_storage_redistribution.py` 는 **저류만** 본다. 그런데 plant 는 링크 차량을
`urban_link_storage` 와 `urban_movement_queue` 둘로 쪼개 담는다(관측 분율 0.35/0.50).
차가 큐에서 저류로 옮겨 가기만 해도 저류만 보면 오차로 잡히지만 **구간 총량은 안 변한다.**

즉 저류 단위 55% 에는 **우리 장부 내부의 재분류**가 섞여 있을 수 있다. 그것을 안 가르고
고치러 들어가면 모델이 아니라 우리 회계를 최적화하게 된다.

보존 단위는 movement 의 `origin` 이 준다 - 그 movement 가 대기하는 저류다.

    conserved[s] = storage_occupancy[s] + sum(movement_queue[m] for m.origin == s)

양쪽 모두 어댑터의 `build_local_observation_summary` / plant 상태에서 같은 규약으로
꺼내므로 남는 차이는 예측 오차뿐이다.

## 임계

저장소가 이미 쓰는 G5 기준을 그대로 쓴다 - `threshold = max(5.0, 0.10 * 관측대수)`.
임의 목표를 새로 만들지 않는다. 통과 = 오차가 그 임계 이하.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from audit_rollout_prediction_accuracy import _load_adapter, rollout_from_anchor  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

G5_FLOOR_VEH = 5.0
G5_RATIO = 0.10
MIN_OBS_VEH = 5.0


def _mdape(pairs: Sequence[tuple[float, float]]) -> float:
    vals = [100.0 * abs(m - o) / o for m, o in pairs if o > 0]
    return st.median(vals) if vals else float("nan")


def bias_decomposition(samples: Sequence[tuple[float, float, str, str]]) -> dict[str, Any]:
    """계통 편향과 산포를 가른다 — MdAPE 만으로는 안 되는 일.

    MdAPE 는 분해되지 않는다. 편향-분산 분해는 제곱오차 스케일에서만 성립한다:
        E[(m-o)^2] = (E[m]-E[o])^2 + (sd(m)-sd(o))^2 + 2(1-r)sd(m)sd(o)
    세 항을 MSE 로 나눈 것이 Theil 의 bias / variance / covariance 비율이고 합이 1 이다.
    Toledo & Koutsopoulos (2004, TRR 1876) 의 해석 규범: bias 와 variance 비율은 작을수록
    좋고 **covariance 비율은 1 에 가까워야 한다** - 즉 covariance 몫은 0 으로 몰 대상이
    아니다. 우리 부호 있는 중앙값 -11.6% 는 bias 쪽이고 그건 처리 대상이다.

    편향 제거 후 MdAPE 를 두 가지로 낸다.
      global   : 곱셈 보정 k 하나(k = median(o/m))를 전 표본에 적용. 파라미터 1개라 과적합이
                 거의 없다.
      per-storage LOCO : 저류별 k 를 **그 셀을 뺀** 나머지 셀에서 적합해 held-out 셀에 적용한다.
                 in-sample 로 저류별 k 를 맞추면 표본이 적어 오차가 인위적으로 0 에 가까워지므로
                 leave-one-cell-out 이 아니면 숫자가 거짓이 된다.
    """
    xs = [(m, o, s, c) for m, o, s, c in samples if o > 0]
    if len(xs) < 3:
        return {}
    m_all = [m for m, _, _, _ in xs]
    o_all = [o for _, o, _, _ in xs]
    n = len(xs)
    errs = [m - o for m, o in zip(m_all, o_all)]
    mse = sum(e * e for e in errs) / n
    mean_m, mean_o = st.fmean(m_all), st.fmean(o_all)
    # 모집단 표준편차(분해 항등식이 성립하는 형태)
    sd_m = (sum((x - mean_m) ** 2 for x in m_all) / n) ** 0.5
    sd_o = (sum((x - mean_o) ** 2 for x in o_all) / n) ** 0.5
    cov = sum((a - mean_m) * (b - mean_o) for a, b in zip(m_all, o_all)) / n
    r = cov / (sd_m * sd_o) if sd_m > 0 and sd_o > 0 else 0.0
    out: dict[str, Any] = {
        "n": n,
        "me_veh": st.fmean(errs),
        "mpe_pct": st.fmean([100.0 * (m - o) / o for m, o, _, _ in xs]),
        "rmse_veh": mse ** 0.5,
        "theil_u2": (mse ** 0.5) / ((sum(x * x for x in m_all) / n) ** 0.5 + (sum(x * x for x in o_all) / n) ** 0.5)
        if (m_all or o_all) else None,
        "pearson_r": r,
    }
    if mse > 0:
        out["proportions"] = {
            "bias": (mean_m - mean_o) ** 2 / mse,
            "variance": (sd_m - sd_o) ** 2 / mse,
            "covariance": 2.0 * (1.0 - r) * sd_m * sd_o / mse,
        }

    base = _mdape([(m, o) for m, o, _, _ in xs])
    out["mdape_before"] = base

    ratios = [o / m for m, o, _, _ in xs if m > 0]
    if ratios:
        k = st.median(ratios)
        out["global_k"] = k
        out["mdape_after_global_k"] = _mdape([(k * m, o) for m, o, _, _ in xs])

    # 저류별 k, leave-one-cell-out
    by_storage_cell: dict[str, dict[str, list[tuple[float, float]]]] = defaultdict(lambda: defaultdict(list))
    for m, o, s, c in xs:
        by_storage_cell[s][c].append((m, o))
    loco: list[tuple[float, float]] = []
    for storage, cells in by_storage_cell.items():
        if len(cells) < 2:
            continue
        for held, held_pairs in cells.items():
            train = [p for c, ps in cells.items() if c != held for p in ps]
            rs = [o / m for m, o in train if m > 0]
            if not rs:
                continue
            k_s = st.median(rs)
            loco.extend((k_s * m, o) for m, o in held_pairs)
    if loco:
        out["mdape_after_per_storage_loco"] = _mdape(loco)
        out["loco_n"] = len(loco)

    # leave-one-DEMAND-out. LOCO 는 셀 하나만 빼므로 같은 수요의 다른 시드가 훈련에 남아
    # "수요를 건너서도 통하는가"를 검정하지 못한다. 저류별 보정이 파라미터가 될 수 있으려면
    # 수요 0.75+1.0 에서 적합한 k 가 1.25 에서도 통해야 한다. 통하지 않으면 그것은 고정
    # 파라미터가 아니라 상태의존 함수이고, 모형 구조를 바꿔야 하는 문제다.
    def demand_of(cell: str) -> str:
        for token in ("d075", "d100", "d125"):
            if token in cell:
                return token
        return "unknown"

    by_storage_demand: dict[str, dict[str, list[tuple[float, float]]]] = defaultdict(lambda: defaultdict(list))
    for m, o, s, c in xs:
        by_storage_demand[s][demand_of(c)].append((m, o))
    lodo: list[tuple[float, float]] = []
    lodo_by_demand: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for storage, demands in by_storage_demand.items():
        if len(demands) < 2:
            continue
        for held, held_pairs in demands.items():
            train = [p for d, ps in demands.items() if d != held for p in ps]
            rs = [o / m for m, o in train if m > 0]
            if not rs:
                continue
            k_s = st.median(rs)
            corrected = [(k_s * m, o) for m, o in held_pairs]
            lodo.extend(corrected)
            lodo_by_demand[held].extend(corrected)
    if lodo:
        out["mdape_after_per_storage_lodo"] = _mdape(lodo)
        out["lodo_n"] = len(lodo)
        out["mdape_after_per_storage_lodo_by_demand"] = {
            d: _mdape(v) for d, v in sorted(lodo_by_demand.items()) if v
        }

    # 저류별 k 를 그대로 내보낸다. 어느 저류가 계통적으로 어긋나 있는지 알아야 다음 수정을
    # 겨눌 수 있다. k > 1 은 모형이 과소예측(보정하려면 키워야 함), k < 1 은 과대예측이다.
    ks: dict[str, float] = {}
    for storage, cells_ in by_storage_cell.items():
        rs = [o / m for ps in cells_.values() for m, o in ps if m > 0]
        if len(rs) >= 3:
            ks[storage] = st.median(rs)
    if ks:
        ordered = sorted(ks.items(), key=lambda kv: abs(math.log(max(kv[1], 1e-9))), reverse=True)
        out["per_storage_k"] = {s: round(v, 4) for s, v in sorted(ks.items())}
        out["per_storage_k_summary"] = {
            "n": len(ks),
            "median": st.median(ks.values()),
            "within_10pct": sum(1 for v in ks.values() if 0.9 <= v <= 1.1),
            "over_2x": sum(1 for v in ks.values() if v >= 2.0 or v <= 0.5),
            "worst": [{"storage": s, "k": round(v, 3)} for s, v in ordered[:12]],
        }
    return out


def g5_threshold(observed: float) -> float:
    return max(G5_FLOOR_VEH, G5_RATIO * abs(observed))


def observed_link_metrics(path: Path, want: set[float]):
    out = defaultdict(lambda: {"link_counts": {}, "link_speeds_kph": {}, "link_stopped_counts": {}})
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                sec = float(row["sim_sec"])
            except (KeyError, TypeError, ValueError):
                continue
            if sec not in want:
                continue
            link = str(row["link"])
            out[sec]["link_counts"][link] = float(row["count"])
            out[sec]["link_speeds_kph"][link] = float(row["mean_speed_kph"])
            out[sec]["link_stopped_counts"][link] = float(row["stopped_count"])
    return out


def conserved_from_parts(
    cfg, occupancy: Mapping[str, float], movement_queue: Mapping[str, float]
) -> dict[str, float]:
    out: dict[str, float] = {str(k): float(v) for k, v in occupancy.items()}
    for name, spec in cfg.network.urban_movements.items():
        origin = str(spec.get("origin") if isinstance(spec, dict) else getattr(spec, "origin", ""))
        if not origin:
            continue
        out[origin] = out.get(origin, 0.0) + float(movement_queue.get(name, 0.0) or 0.0)
    return out


def model_conserved(state, cfg) -> dict[str, float]:
    capacity = cfg.network.urban_link_storage_veh
    remaining = getattr(state, "urban_link_storage", {}) or {}
    occ = {
        str(k): max(0.0, float(cap) - float(remaining.get(k, cap)))
        for k, cap in capacity.items()
    }
    return conserved_from_parts(cfg, occ, getattr(state, "urban_movement_queue", {}) or {})


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--tag", default="n5parent_20260814")
    ap.add_argument("--anchors", default="900,1500,2100")
    ap.add_argument("--horizon-steps", type=int, default=3)
    ap.add_argument("--limit-cells", type=int, default=0)
    ap.add_argument(
        "--tuning", type=Path,
        default=REPO / "evaluation/configs/real_world_modi_pstack_distributed_pedovrx_20260814.json",
    )
    ap.add_argument(
        "--calibration", type=Path,
        default=REPO / "evaluation/calibration/real_world_prediction_calibration_pshb4500fix_20260724.json",
    )
    ap.add_argument(
        "--detector-mapping", type=Path,
        default=REPO / "evaluation/real_world_modi_control_distributed_20260728"
        / "detector_local_mapping_distributed_pedovrx_20260814.json",
    )
    ap.add_argument(
        "--storage-capacity-json", type=Path, default=None,
        help="저류 용량을 이 파일로 덮어써서 **시험만** 한다. 생산 config 는 안 건드린다. "
             "jam density 재보정 효과를 격리해 보려는 용도다.",
    )
    ap.add_argument(
        "--movement-beta-json", type=Path, default=None,
        help="movement beta 를 이 파일(derive_movement_beta_from_routes.py 산출)로 덮어써서 "
             "**시험만** 한다. origin 별 합이 1 이 되도록 정규화한다 - 안 하면 질량이 생기거나 "
             "사라진다. 유도값이 없는 movement 는 기존 beta 를 유지한 뒤 같이 정규화된다.",
    )
    ap.add_argument(
        "--movement-capacity-vph", type=float, default=None,
        help="movement 포화유율[veh/h]을 이 값으로 덮어써서 **시험만** 한다. 기본값은 "
             "default.yaml:109 의 1400.0 이고 차로수가 안 들어간다 - 실제는 차로당 1800~1900 이라 "
             "다차로 접근에서 계통적으로 과소하다.",
    )
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)

    run_dir = args.run_dir.resolve()
    anchors = [int(s) for s in str(args.anchors).split(",") if s.strip()]
    paths = {"tuning": args.tuning, "calibration": args.calibration, "detector_mapping": args.detector_mapping}

    ad = _load_adapter()
    if args.movement_capacity_vph is not None:
        _orig_cap = ad.build_config

        def _build_config_with_cap(*a, **kw):
            cfg = _orig_cap(*a, **kw)
            cfg.network.movement_capacity_veh_h = float(args.movement_capacity_vph)
            return cfg

        ad.build_config = _build_config_with_cap
        print(f"[시험] movement 포화유율을 {args.movement_capacity_vph:.0f} veh/h 로 덮어썼다")
    if args.movement_beta_json:
        derived = json.loads(args.movement_beta_json.read_text(encoding="utf-8")).get("derived_beta") or {}
        _orig_bc = ad.build_config

        def _build_config_with_beta(*a, **kw):
            cfg = _orig_bc(*a, **kw)
            mvs = cfg.network.urban_movements
            by_origin = defaultdict(list)
            for name, spec in mvs.items():
                origin = str(spec.get("origin", "") if isinstance(spec, dict) else getattr(spec, "origin", ""))
                by_origin[origin].append(name)
            n_set = 0
            for origin, names in by_origin.items():
                vals = {}
                for nm in names:
                    spec = mvs[nm]
                    old = float(spec.get("beta", 0.0) if isinstance(spec, dict) else getattr(spec, "beta", 0.0))
                    vals[nm] = float(derived.get(nm, old))
                    if nm in derived:
                        n_set += 1
                total = sum(vals.values())
                if total <= 0:
                    continue
                for nm, v in vals.items():
                    spec = mvs[nm]
                    if isinstance(spec, dict):
                        spec["beta"] = v / total
                    else:
                        setattr(spec, "beta", v / total)
            return cfg

        ad.build_config = _build_config_with_beta
        print(f"[시험] beta {len(derived)}개를 {args.movement_beta_json.name} 로 덮어쓰고 origin 별 정규화")
    if args.storage_capacity_json:
        # build_config 를 감싸 반환된 cfg 의 용량만 갈아끼운다. 생산 config 는 그대로다.
        override = json.loads(args.storage_capacity_json.read_text(encoding="utf-8"))
        caps = {str(k): float(v) for k, v in (override.get("urban_link_storage_veh") or {}).items()}
        _orig_build_config = ad.build_config

        def _build_config_with_caps(*a, **kw):
            cfg = _orig_build_config(*a, **kw)
            existing = cfg.network.urban_link_storage_veh
            for key in list(existing):
                if key in caps:
                    existing[key] = caps[key]
            return cfg

        ad.build_config = _build_config_with_caps
        print(f"[시험] 저류 용량 {len(caps)}통을 {args.storage_capacity_json.name} 로 덮어썼다")
    detector_mapping = ad.load_optional_json(str(args.detector_mapping))
    calibration = ad.load_optional_json(str(args.calibration))
    tuning = ad.load_optional_json(str(args.tuning))
    ov = tuning.get("calibration_override", {})
    if isinstance(ov, Mapping):
        calibration = ad.deep_update(dict(calibration), ov)

    cells = sorted(run_dir.glob(f"state_{args.tag}_*.csv"))
    cells = [c for c in cells if "_r" not in c.name[len("state_") : -len(".csv")].rsplit("_s", 1)[-1]]
    if args.limit_cells:
        cells = cells[: args.limit_cells]

    storage_only: dict[int, list[float]] = defaultdict(list)
    conserved: dict[int, list[float]] = defaultdict(list)
    abs_err: dict[int, list[float]] = defaultdict(list)
    # (모형, 관측, 저류, 셀) 짝을 남긴다. 편향-분산 분해와 편향 제거 후 재계산에는 오차만으로는
    # 부족하고 원 짝이 있어야 한다. MdAPE 는 분해되지 않으므로(제곱오차 스케일에서만 성립)
    # 계통 편향이 41.6% 중 몇 pt 인지는 이 짝에서만 나온다.
    pairs: dict[int, list[tuple[float, float, str, str]]] = defaultdict(list)
    g5_pass = defaultdict(lambda: [0, 0])
    signed: list[float] = []
    failures: list[str] = []

    for state_csv in cells:
        name = state_csv.name[len("state_") : -len(".csv")]
        want = {float(a + 60 * k) for a in anchors for k in range(1, args.horizon_steps + 1)}
        obs_raw = observed_link_metrics(run_dir / f"bottleneck_links_{name}.csv", want)
        for anchor in anchors:
            ap_path = run_dir / f"decisions_{name}" / f"anchor_{anchor:06d}.json"
            if not ap_path.is_file():
                continue
            try:
                aj = json.loads(ap_path.read_text(encoding="utf-8"))
                steps, _iv, cfg = rollout_from_anchor(ad, aj, args.horizon_steps, paths)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{name}@{anchor}: {type(exc).__name__}: {exc}")
                continue
            for stp in steps:
                sec = float(stp["sim_sec"])
                raw = obs_raw.get(sec)
                if not raw:
                    continue
                synthetic = dict(aj)
                synthetic["local_observation"] = {**(aj.get("local_observation") or {}), **raw}
                osum = ad.build_local_observation_summary(synthetic, cfg, detector_mapping, calibration)
                o_occ = osum.get("urban_link_storage_occupancy") or {}
                o_mq = osum.get("urban_movement_queue") or {}
                o_cons = conserved_from_parts(cfg, o_occ, o_mq)
                m_cons = model_conserved(stp["state"], cfg)
                m_occ_state = getattr(stp["state"], "urban_link_storage", {}) or {}
                for s, oval in o_cons.items():
                    if oval < MIN_OBS_VEH:
                        continue
                    mval = m_cons.get(s, 0.0)
                    err = abs(mval - oval)
                    conserved[stp["step"]].append(100.0 * err / oval)
                    # 절대 대수(veh)도 같이 남긴다. 문헌이 링크 단위 오차를 보고할 때 쓰는
                    # 유일한 공통 통화가 절대 veh 다(예: Portilla et al. 2020 의 링크상태
                    # RMS 4.94 veh). MdAPE 는 분모가 작은 이동류에서 부풀려지므로 둘을 나란히
                    # 둬야 "분모 효과 아니냐"는 반론에 답할 수 있다. VISSIM 자신의 시드 간
                    # 실현 편차가 중앙 1.7~2.1 veh 이므로 그것과 직접 비교되는 값이다.
                    abs_err[stp["step"]].append(err)
                    pairs[stp["step"]].append((mval, oval, s, state_csv.stem))
                    signed.append(100.0 * (mval - oval) / oval)
                    ok = err <= g5_threshold(oval)
                    g5_pass[stp["step"]][0] += 1 if ok else 0
                    g5_pass[stp["step"]][1] += 1
                    # 같은 표본에서 저류만 본 값도 같이 남겨 대조한다.
                    cap = float(cfg.network.urban_link_storage_veh.get(s, 0.0) or 0.0)
                    if cap > 0:
                        m_only = max(0.0, cap - float(m_occ_state.get(s, cap)))
                        o_only = float(o_occ.get(s, 0.0) or 0.0)
                        if o_only >= MIN_OBS_VEH:
                            storage_only[stp["step"]].append(100.0 * abs(m_only - o_only) / o_only)

    payload = {
        "schema_version": "rollout-conserved-unit-v1",
        "status": "PASS" if conserved and not failures else "FAIL",
        "reasons": failures[:20],
        "setup": {
            "run_dir": str(run_dir),
            "anchors_sec": anchors,
            "horizon_steps": args.horizon_steps,
            "cells": len(cells),
            "conserved_unit": "storage_occupancy[s] + sum(movement_queue[m] for m.origin == s)",
            "g5_threshold": "max(5.0 veh, 0.10 * observed)",
            "min_observed_veh": MIN_OBS_VEH,
        },
        "median_ape_by_step": {
            "conserved": {str(k): st.median(v) for k, v in sorted(conserved.items()) if v},
            "storage_only": {str(k): st.median(v) for k, v in sorted(storage_only.items()) if v},
        },
        "abs_err_veh_by_step": {
            str(k): {
                "median": st.median(v),
                "p90": sorted(v)[int(0.9 * (len(v) - 1))],
                "mean": st.fmean(v),
                "n": len(v),
            }
            for k, v in sorted(abs_err.items()) if v
        },
        "g5_pass_rate_by_step": {
            str(k): {"pass": v[0], "total": v[1], "rate_pct": 100.0 * v[0] / v[1] if v[1] else None}
            for k, v in sorted(g5_pass.items())
        },
        "signed_median_pct": st.median(signed) if signed else None,
        "bias_decomposition_by_step": {
            str(k): bias_decomposition(v) for k, v in sorted(pairs.items()) if v
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
                        encoding="utf-8", newline="\n")

    print(f"status={payload['status']}  셀={len(cells)}")
    print(f"{'스텝':>4s}  {'보존단위':>9s}  {'저류만':>9s}  {'절대오차':>11s}  {'G5 통과':>9s}")
    for k in sorted(conserved):
        c = st.median(conserved[k])
        s = st.median(storage_only[k]) if storage_only.get(k) else float("nan")
        a = payload["abs_err_veh_by_step"].get(str(k), {})
        g = payload["g5_pass_rate_by_step"][str(k)]
        print(f"{k:>4d}  {c:8.1f}%  {s:8.1f}%  {a.get('median', float('nan')):7.2f}veh  "
              f"{g['rate_pct']:7.1f}%  ({g['pass']}/{g['total']})")
    print(f"부호 있는 중앙값 {payload['signed_median_pct']:+.1f}%")
    bd = payload["bias_decomposition_by_step"]
    if bd:
        print(f"\n{'스텝':>4s} {'ME':>9s} {'MPE':>8s} {'RMSE':>8s} {'Theil U2':>9s} "
              f"{'편향':>7s} {'분산':>7s} {'공분산':>7s}")
        for k in sorted(bd, key=int):
            d = bd[k]
            p = d.get("proportions") or {}
            print(f"{k:>4s} {d['me_veh']:+8.2f}v {d['mpe_pct']:+7.1f}% {d['rmse_veh']:7.2f}v "
                  f"{d.get('theil_u2') or float('nan'):9.4f} "
                  f"{p.get('bias', float('nan')):6.3f} {p.get('variance', float('nan')):6.3f} "
                  f"{p.get('covariance', float('nan')):6.3f}")
        print("\n편향 제거 후 MdAPE (스텝: 원래 -> 전역 k -> 저류별 k, 셀 하나 빼고 -> 수요 하나 빼고)")
        for k in sorted(bd, key=int):
            d = bd[k]
            print(f"  {k}: {d.get('mdape_before', float('nan')):5.1f}% -> "
                  f"{d.get('mdape_after_global_k', float('nan')):5.1f}% (k={d.get('global_k', float('nan')):.3f}) -> "
                  f"{d.get('mdape_after_per_storage_loco', float('nan')):5.1f}% -> "
                  f"{d.get('mdape_after_per_storage_lodo', float('nan')):5.1f}%")
        print("\n수요 하나 빼고 적합한 저류별 보정을, 그 빠진 수요에 적용한 결과")
        for k in sorted(bd, key=int):
            byd = bd[k].get("mdape_after_per_storage_lodo_by_demand") or {}
            if byd:
                cells = "  ".join(f"{d}: {v:5.1f}%" for d, v in byd.items())
                print(f"  스텝 {k}   {cells}")
    for r in payload["reasons"][:3]:
        print("  " + r)
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
