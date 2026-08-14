#!/usr/bin/env python3
"""plant 를 anchor 에서 H 스텝 굴려 VISSIM 실측과 대조한다 (다중스텝 예측 검증).

## 왜 필요한가

기존 `scripts/audit_real_world_prediction_accuracy.py` 는 **one-step 전용**이다
(`mode = coupled_interval_one_step`, 60초 한 걸음). "우리 plant 로 rollout 했을 때
VISSIM 을 얼마나 맞히는가" 는 아무도 재지 않았다. MPC 는 horizon 만큼 굴려서 결정하므로
검증도 그 길이여야 한다.

## 왜 부모런이 그 검증에 맞는가

부모런은 **no-control** 이다. 그래서 VISSIM 궤적이 컨트롤러 정책에 오염되지 않은
순수 플랜트 궤적이고, 모델도 무제어로 굴리면 **동역학만** 비교된다. 예측이 틀리면
그것은 모델의 동역학이 틀린 것이지 정책이 달라서가 아니다.

anchor 900/1500/2100/2700 에 전 차량 레코드와 local_observation 이 있고,
상태 CSV 가 5초 간격이라 어느 시각의 실측이든 꺼내 쓸 수 있다.

## 어떻게 굴리는가

어댑터의 정본 경로를 그대로 쓴다 - 우회 호출을 만들지 않는다(계획 N7 "우회 0").

    traffic_state_from_vissim(anchor_json, cfg, TrafficState, ...)   초기조건
    demand_from_state(anchor_json, cfg, DemandStep, H, ...)          수요 예측
    _guarded_no_control_baseline(...)                               무제어 액션
    evaluate_price_point(..., ObjectiveSpec(depth_override=H)).states  궤적 H개
    summarize_model_state(s, cfg)                                    스텝별 요약

`build_one_step_prediction` 이 하는 것과 같은 경로에 `depth_override` 만 H 로 준 것이다.

## 무엇과 비교하는가

| 모델 요약 | VISSIM 상태 CSV |
|---|---|
| `total_model_vehicles` | `total_vehicles` |
| `urban_total_veh` | `urban_vehicles` |
| `freeway_total_veh` | `freeway_vehicles` |
| `freeway_mean_speed_kph` | `freeway_mean_speed_kph` |

`boundary_queue_total_veh` 는 뺀다 - VISSIM 쪽 `boundary_vehicles` 가 전 구간 0 이라
APE 분모가 0 이 된다.

## 캘리브레이션

`--fit-calibration` 을 주면 **training 시드에서만** componentwise
`mean(observed)/mean(predicted)` 스케일을 적합하고, holdout 에서 그 스케일이 실제로
오차를 줄이는지 따로 보고한다. holdout 은 적합에 쓰지 않는다.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import statistics as st
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = "rollout-prediction-accuracy-v1"
ANCHORS_SEC = (900, 1500, 2100, 2700)

# 모델 요약 키 -> VISSIM 상태 CSV 열
METRIC_PAIRS = {
    "total_model_vehicles": "total_vehicles",
    "urban_total_veh": "urban_vehicles",
    "freeway_total_veh": "freeway_vehicles",
    "freeway_mean_speed_kph": "freeway_mean_speed_kph",
}


def _load_adapter():
    sys.path.insert(0, str(REPO / "evaluation" / "controllers"))
    import vissim_stackelberg_adapter as ad  # noqa: E402

    return ad


def observed_series(state_csv: Path) -> dict[float, dict[str, float]]:
    out: dict[float, dict[str, float]] = {}
    with open(state_csv, encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                sec = float(row["sim_sec"])
            except (KeyError, TypeError, ValueError):
                continue
            rec: dict[str, float] = {}
            for col in set(METRIC_PAIRS.values()):
                try:
                    rec[col] = float(row[col])
                except (KeyError, TypeError, ValueError):
                    pass
            out[sec] = rec
    return out


def rollout_from_anchor(ad, anchor_json: Mapping[str, Any], horizon_steps: int, paths: Mapping[str, Path]):
    """어댑터 정본 경로로 anchor 에서 H 스텝 무제어 rollout 을 굴린다."""
    repo_root = Path(ad.DEFAULT_REPO_ROOT)
    (
        _Controller,
        DemandStep,
        ControlAction,
        _ExperimentConfig,
        TrafficState,
        _vsl,
    ) = ad.repo_imports(repo_root)

    state_json = dict(anchor_json)
    detector_mapping = ad.load_optional_json(str(paths["detector_mapping"]))
    calibration = ad.load_optional_json(str(paths["calibration"]))
    tuning = ad.load_optional_json(str(paths["tuning"]))
    override = tuning.get("calibration_override", {})
    if isinstance(override, Mapping):
        calibration = ad.deep_update(dict(calibration), override)
    actuation = ad.adapter_actuation_settings(calibration, tuning)

    control_interval = float(state_json.get("control_interval_sec", 60.0))
    sim_period = float(state_json.get("sim_period_sec", max(180.0, control_interval)))
    local_observation = bool(
        ad._link_counts_from_local_observation(state_json) and detector_mapping
    )
    cfg = ad.build_config(
        repo_root,
        control_interval,
        sim_period,
        "local_observation" if local_observation else "global",
        calibration,
        tuning,
        local_observation=local_observation,
        flagship=False,
    )
    ad.install_adapter_calibration_fingerprints(cfg, tuning)
    ad.install_vissim_calibration_runtime_patches(cfg, calibration)
    ad.install_vsl_metanet_rollout_runtime_patch(cfg, tuning)
    state = ad.traffic_state_from_vissim(
        state_json, cfg, TrafficState, detector_mapping, calibration
    )
    ad.install_monitor_fixed_signal_runtime_patch(cfg, state_json, detector_mapping)
    if local_observation:
        ad.install_local_observation_runtime_guards()

    forecast = ad.demand_from_state(
        state_json, cfg, DemandStep, horizon_steps, calibration, detector_mapping
    )
    control = ad._guarded_no_control_baseline(ControlAction, cfg, state, state_json, actuation)

    from src.controllers.rollout_endpoint import ObjectiveSpec, evaluate_price_point

    result = evaluate_price_point(
        state,
        control,
        list(forecast),
        (),
        ObjectiveSpec(cfg=cfg, depth_override=int(horizon_steps), box_walk=False),
    )
    t0 = float(state_json.get("sim_sec", 0.0))
    steps = []
    for k, s in enumerate(result.states, start=1):
        steps.append(
            {
                "step": k,
                "sim_sec": t0 + k * control_interval,
                "summary": ad.summarize_model_state(s, cfg),
            }
        )
    return steps, control_interval


def ape(pred: float | None, obs: float | None) -> float:
    if pred is None or obs is None or obs == 0:
        return float("nan")
    return 100.0 * abs(float(pred) - float(obs)) / abs(float(obs))


def collect(
    run_dir: Path,
    tag: str,
    horizon_steps: int,
    paths: Mapping[str, Path],
    *,
    training_seeds: Sequence[int],
    holdout_seeds: Sequence[int],
    anchors: Sequence[int],
    limit_cells: int = 0,
) -> dict[str, Any]:
    ad = _load_adapter()
    samples: list[dict[str, Any]] = []
    failures: list[str] = []

    cells = []
    for state_csv in sorted(run_dir.glob(f"state_{tag}_*.csv")):
        name = state_csv.name[len("state_") : -len(".csv")]
        if "_r" in name.rsplit("_s", 1)[-1]:  # base replay 는 부모와 같은 궤적이다
            continue
        parts = name.split("_")
        try:
            seed = int(parts[-1][1:])
            demand = int(parts[-2][1:]) / 100.0
            role = parts[-3]
        except (IndexError, ValueError):
            continue
        cells.append({"name": name, "role": role, "demand": demand, "seed": seed, "state_csv": state_csv})
    if limit_cells:
        cells = cells[:limit_cells]

    for cell in cells:
        obs = observed_series(cell["state_csv"])
        decision_dir = run_dir / f"decisions_{cell['name']}"
        for anchor in anchors:
            anchor_path = decision_dir / f"anchor_{anchor:06d}.json"
            if not anchor_path.is_file():
                continue
            try:
                anchor_json = json.loads(anchor_path.read_text(encoding="utf-8"))
                steps, interval = rollout_from_anchor(ad, anchor_json, horizon_steps, paths)
            except Exception as exc:  # noqa: BLE001 - 어느 셀에서 왜 죽었는지 남긴다
                failures.append(f"{cell['name']}@{anchor}: {type(exc).__name__}: {exc}")
                continue
            for step in steps:
                o = obs.get(step["sim_sec"])
                if not o:
                    continue
                rec = {
                    "cell": cell["name"],
                    "role": cell["role"],
                    "demand": cell["demand"],
                    "seed": cell["seed"],
                    "anchor_sec": anchor,
                    "step": step["step"],
                    "horizon_sec": step["step"] * interval,
                    "sim_sec": step["sim_sec"],
                    "metrics": {},
                }
                for model_key, obs_key in METRIC_PAIRS.items():
                    p = step["summary"].get(model_key)
                    v = o.get(obs_key)
                    rec["metrics"][model_key] = {
                        "predicted": p,
                        "observed": v,
                        "ape": ape(p, v),
                    }
                samples.append(rec)

    return {"samples": samples, "failures": failures, "cells": [c["name"] for c in cells]}


def summarize(samples: Sequence[Mapping[str, Any]], seeds: Sequence[int] | None = None) -> dict[str, Any]:
    picked = [s for s in samples if seeds is None or s["seed"] in set(seeds)]
    by_metric: dict[str, list[float]] = {k: [] for k in METRIC_PAIRS}
    by_step: dict[int, dict[str, list[float]]] = {}
    for s in picked:
        for key, rec in s["metrics"].items():
            a = rec["ape"]
            if a == a:
                by_metric[key].append(a)
                by_step.setdefault(s["step"], {}).setdefault(key, []).append(a)
    return {
        "sample_count": len(picked),
        "median_ape_by_metric": {
            k: (st.median(v) if v else float("nan")) for k, v in by_metric.items()
        },
        "median_ape_by_step": {
            str(step): {k: (st.median(v) if v else float("nan")) for k, v in per.items()}
            for step, per in sorted(by_step.items())
        },
    }


def fit_scales(
    samples: Sequence[Mapping[str, Any]], seeds: Sequence[int], max_step: int = 0
) -> dict[str, float]:
    """componentwise mean(observed)/mean(predicted). 기존 감사 캘리브레이션과 같은 방법.

    `max_step` 을 주면 그 스텝까지만 적합한다. **이것이 중요하다** — 모델은 MPC horizon
    까지만 쓰이는데(이 격자는 3스텝=180초), 그 너머는 고속도로가 폭주해서(10스텝에서
    대수 63.9% / 속도 75.3%) 평균비가 통째로 그쪽에 끌려간다. horizon 밖 오차로 적합한
    스케일을 horizon 안에 먹이면 멀쩡하던 구간이 망가진다.
    """
    wanted = set(seeds)
    out: dict[str, float] = {}
    for key in METRIC_PAIRS:
        preds, obss = [], []
        for s in samples:
            if s["seed"] not in wanted:
                continue
            if max_step and int(s["step"]) > max_step:
                continue
            rec = s["metrics"][key]
            p, o = rec["predicted"], rec["observed"]
            if p is None or o is None or not math.isfinite(float(p)) or not math.isfinite(float(o)):
                continue
            preds.append(float(p))
            obss.append(float(o))
        if preds and st.mean(preds) != 0:
            out[key] = st.mean(obss) / st.mean(preds)
    return out


def apply_scales(samples: Sequence[Mapping[str, Any]], scales: Mapping[str, float]) -> list[dict[str, Any]]:
    out = []
    for s in samples:
        rec = json.loads(json.dumps(s))
        for key, m in rec["metrics"].items():
            scale = scales.get(key)
            if scale is None or m["predicted"] is None:
                continue
            m["predicted"] = float(m["predicted"]) * float(scale)
            m["ape"] = ape(m["predicted"], m["observed"])
        out.append(rec)
    return out


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--tag", default="n5parent_20260814")
    ap.add_argument("--horizon-steps", type=int, default=10, help="제어주기 몇 걸음. 10 x 60s = 600s = 다음 anchor")
    ap.add_argument("--anchors", default="900,1500,2100")
    ap.add_argument("--training-seeds", default="13,29")
    ap.add_argument("--holdout-seeds", default="47")
    ap.add_argument("--limit-cells", type=int, default=0, help="시험용. 0 이면 전부")
    ap.add_argument("--fit-calibration", action="store_true")
    ap.add_argument(
        "--fit-max-step", type=int, default=3,
        help="이 스텝까지만 적합한다. 기본 3 = 이 격자의 mpc.horizon_steps. 0 이면 전 구간.",
    )
    ap.add_argument(
        "--tuning", type=Path,
        default=REPO / "evaluation" / "configs" / "real_world_modi_pstack_distributed_pedovrx_20260814.json",
    )
    ap.add_argument(
        "--calibration", type=Path,
        default=REPO / "evaluation" / "calibration" / "real_world_prediction_calibration_pshb4500fix_20260724.json",
    )
    ap.add_argument(
        "--detector-mapping", type=Path,
        default=REPO / "evaluation" / "real_world_modi_control_distributed_20260728"
        / "detector_local_mapping_distributed_pedovrx_20260814.json",
    )
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)

    training = [int(s) for s in str(args.training_seeds).split(",") if s.strip()]
    holdout = [int(s) for s in str(args.holdout_seeds).split(",") if s.strip()]
    anchors = [int(s) for s in str(args.anchors).split(",") if s.strip()]
    paths = {
        "tuning": args.tuning,
        "calibration": args.calibration,
        "detector_mapping": args.detector_mapping,
    }

    collected = collect(
        args.run_dir.resolve(), args.tag, args.horizon_steps, paths,
        training_seeds=training, holdout_seeds=holdout, anchors=anchors,
        limit_cells=args.limit_cells,
    )
    samples = collected["samples"]

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if samples and not collected["failures"] else "FAIL",
        "reasons": collected["failures"][:20],
        "setup": {
            "run_dir": str(args.run_dir),
            "horizon_steps": args.horizon_steps,
            "anchors_sec": anchors,
            "training_seeds": training,
            "holdout_seeds": holdout,
            "tuning": args.tuning.name,
            "calibration_in_effect": args.calibration.name,
            "controller": "no-control (부모런과 같은 무제어 - 동역학만 비교된다)",
            "metric_pairs": METRIC_PAIRS,
        },
        "raw": {
            "all": summarize(samples),
            "training": summarize(samples, training),
            "holdout": summarize(samples, holdout),
        },
    }

    if args.fit_calibration and samples:
        horizon = int(args.fit_max_step)
        scales = fit_scales(samples, training, max_step=horizon)
        rescaled = apply_scales(samples, scales)
        in_horizon = [s for s in samples if not horizon or int(s["step"]) <= horizon]
        rescaled_in = [s for s in rescaled if not horizon or int(s["step"]) <= horizon]
        payload["fitted_calibration"] = {
            "method": "componentwise mean(observed)/mean(predicted), training 시드에서만 적합",
            "fit_seeds": training,
            "fit_max_step": horizon,
            "why_max_step": (
                "모델은 MPC horizon 까지만 쓰인다. 그 너머는 고속도로가 폭주해서 평균비가 "
                "통째로 그쪽에 끌려가고, 그 스케일을 horizon 안에 먹이면 멀쩡하던 구간이 망가진다."
            ),
            "scales": scales,
            "before_in_horizon": {
                "training": summarize(in_horizon, training),
                "holdout": summarize(in_horizon, holdout),
            },
            "after_in_horizon": {
                "training": summarize(rescaled_in, training),
                "holdout": summarize(rescaled_in, holdout),
            },
            "after_full_rollout": {
                "training": summarize(rescaled, training),
                "holdout": summarize(rescaled, holdout),
            },
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8", newline="\n",
    )

    print(f"status={payload['status']}  표본={len(samples)}  셀={len(collected['cells'])}")
    for scope in ("all", "training", "holdout"):
        med = payload["raw"][scope]["median_ape_by_metric"]
        n = payload["raw"][scope]["sample_count"]
        print(f"  [{scope:8s} n={n:5d}] " + "  ".join(f"{k.split('_')[0]}={v:6.1f}%" for k, v in med.items()))
    if "fitted_calibration" in payload:
        fc = payload["fitted_calibration"]
        h = fc["fit_max_step"]
        print(f"  적합 스케일(스텝<={h}):", {k: round(v, 4) for k, v in fc["scales"].items()})
        for label, block in (("보정전", "before_in_horizon"), ("보정후", "after_in_horizon")):
            for scope in ("training", "holdout"):
                med = fc[block][scope]["median_ape_by_metric"]
                n = fc[block][scope]["sample_count"]
                print(
                    f"  [{label} horizon내 {scope:8s} n={n:4d}] "
                    + "  ".join(f"{k.split('_')[0]}={v:6.1f}%" for k, v in med.items())
                )
    for reason in payload["reasons"][:5]:
        print("  " + reason)
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
