#!/usr/bin/env python3
"""warm-start rollout — release 스케줄을 **plant 가 스스로 짓게** 한 뒤 비교한다.

## 왜

투영은 저류 **점유량만** 싣고 `urban_storage_release_buffer` 를 비워 둔다. 그런데 plant 의
방출은 전적으로 그 버퍼에 물려 있어서, 빈 버퍼로 시작하면 내부 링크는 동결되고
sink 는 통째로 비워진다(실측: 스텝 0 에서 0.0% -> 스텝 1 에서 55%).

버퍼를 내가 지어 넣는 것은 이미 실패했다 — 유출만 복원하고 그에 맞는 유입은 못 살려서
전부 복원하면 오히려 -37.4% 로 무너진다.

그래서 **지어 넣지 않는다.** anchor 보다 W 초 앞에서 시작해 관측 수요로 굴리면 plant 가
자기 규약대로 스케줄을 만든다. anchor 시점에 그 스케줄을 관측 점유량에 맞춰 비례
조정하면, 유입·유출이 함께 살아 있는 자기일관적 상태가 된다.

    anchor - W 에서 투영 -> W/Tc 스텝 무제어 rollout (plant 가 버퍼를 짓는다)
    -> anchor 에서 관측 점유량에 맞춰 저류와 버퍼를 같은 비율로 조정
    -> H 스텝 굴려 비교

## 비교 단위

`audit_rollout_conserved_unit.py` 와 같다 — 저류 + 그 저류에 대기하는 movement 큐.
임계도 같은 G5 기준(`max(5 veh, 0.10 * 관측)`)을 쓴다.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from audit_rollout_prediction_accuracy import _load_adapter  # noqa: E402
from audit_rollout_conserved_unit import (  # noqa: E402
    MIN_OBS_VEH,
    conserved_from_parts,
    g5_threshold,
    model_conserved,
    observed_link_metrics,
)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _setup(ad, state_json: Mapping[str, Any], paths: Mapping[str, Path]):
    """어댑터 정본 경로로 cfg / state / 무제어 액션을 만든다."""
    repo_root = Path(ad.DEFAULT_REPO_ROOT)
    _c, DemandStep, ControlAction, _E, TrafficState, _v = ad.repo_imports(repo_root)
    detector_mapping = ad.load_optional_json(str(paths["detector_mapping"]))
    calibration = ad.load_optional_json(str(paths["calibration"]))
    tuning = ad.load_optional_json(str(paths["tuning"]))
    ov = tuning.get("calibration_override", {})
    if isinstance(ov, Mapping):
        calibration = ad.deep_update(dict(calibration), ov)
    actuation = ad.adapter_actuation_settings(calibration, tuning)
    ci = float(state_json.get("control_interval_sec", 60.0))
    sp = float(state_json.get("sim_period_sec", max(180.0, ci)))
    local = bool(ad._link_counts_from_local_observation(state_json) and detector_mapping)
    cfg = ad.build_config(
        repo_root, ci, sp, "local_observation" if local else "global",
        calibration, tuning, local_observation=local, flagship=False,
    )
    ad.install_adapter_calibration_fingerprints(cfg, tuning)
    ad.install_vissim_calibration_runtime_patches(cfg, calibration)
    ad.install_vsl_metanet_rollout_runtime_patch(cfg, tuning)
    state = ad.traffic_state_from_vissim(dict(state_json), cfg, TrafficState, detector_mapping, calibration)
    ad.install_monitor_fixed_signal_runtime_patch(cfg, dict(state_json), detector_mapping)
    if local:
        ad.install_local_observation_runtime_guards()
    control = ad._guarded_no_control_baseline(ControlAction, cfg, state, dict(state_json), actuation)
    return cfg, state, control, DemandStep, detector_mapping, calibration, ci


def _roll(state, control, cfg, forecast, steps: int):
    from src.controllers.rollout_endpoint import ObjectiveSpec, evaluate_price_point

    return evaluate_price_point(
        state, control, list(forecast), (),
        ObjectiveSpec(cfg=cfg, depth_override=int(steps), box_walk=False),
    ).states


def _rescale_to_observed(state, cfg, observed_occ: Mapping[str, float]) -> dict[str, float]:
    """저류 점유와 그 release 예약을 관측 점유량에 맞춰 **같은 비율**로 조정한다.

    비율을 맞추므로 plant 가 지은 스케줄의 **모양**(언제 얼마가 만기되는가)은 보존된다.
    점유만 갈아끼우고 스케줄을 그대로 두면 다시 불일치가 된다.
    """
    stats = {"links": 0.0, "scaled": 0.0}
    capacity = cfg.network.urban_link_storage_veh
    remaining = getattr(state, "urban_link_storage", {}) or {}
    buffer = getattr(state, "urban_storage_release_buffer", None)
    for link, cap in capacity.items():
        cap = float(cap)
        target = max(0.0, min(cap, float(observed_occ.get(link, 0.0) or 0.0)))
        current = max(0.0, cap - float(remaining.get(link, cap)))
        remaining[link] = cap - target
        stats["links"] += 1.0
        if isinstance(buffer, dict) and current > 1.0e-9:
            ratio = target / current
            pending = buffer.get(str(link))
            if pending:
                buffer[str(link)] = {k: v * ratio for k, v in pending.items()}
                stats["scaled"] += 1.0
    return stats


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--tag", default="n5parent_20260814")
    ap.add_argument("--anchors", default="1500,2100")
    ap.add_argument("--horizon-steps", type=int, default=3)
    ap.add_argument("--warmstart-sec", type=int, default=300, help="anchor 보다 이만큼 앞에서 시작")
    ap.add_argument("--limit-cells", type=int, default=3)
    ap.add_argument("--no-rescale", action="store_true", help="관측 점유량 재조정을 끄고 순수 warm-start 만")
    ap.add_argument(
        "--tuning", type=Path,
        default=REPO / "evaluation/configs/real_world_modi_pstack_distributed_pedovrx_20260814.json")
    ap.add_argument(
        "--calibration", type=Path,
        default=REPO / "evaluation/calibration/real_world_prediction_calibration_pshb4500fix_20260724.json")
    ap.add_argument(
        "--detector-mapping", type=Path,
        default=REPO / "evaluation/real_world_modi_control_distributed_20260728"
        / "detector_local_mapping_distributed_pedovrx_20260814.json")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)

    run_dir = args.run_dir.resolve()
    anchors = [int(s) for s in str(args.anchors).split(",") if s.strip()]
    paths = {"tuning": args.tuning, "calibration": args.calibration, "detector_mapping": args.detector_mapping}
    ad = _load_adapter()

    cells = sorted(run_dir.glob(f"state_{args.tag}_*.csv"))
    cells = [c for c in cells if "_r" not in c.name[len("state_") : -len(".csv")].rsplit("_s", 1)[-1]]
    if args.limit_cells:
        cells = cells[: args.limit_cells]

    ape_by_step: dict[int, list[float]] = defaultdict(list)
    g5 = defaultdict(lambda: [0, 0])
    signed: list[float] = []
    failures: list[str] = []

    for state_csv in cells:
        name = state_csv.name[len("state_") : -len(".csv")]
        want = {float(a + 60 * k) for a in anchors for k in range(0, args.horizon_steps + 1)}
        want |= {float(a - args.warmstart_sec) for a in anchors}
        obs_raw = observed_link_metrics(run_dir / f"bottleneck_links_{name}.csv", want)
        for anchor in anchors:
            ap_path = run_dir / f"decisions_{name}" / f"anchor_{anchor:06d}.json"
            warm_sec = float(anchor - args.warmstart_sec)
            if not ap_path.is_file() or warm_sec not in obs_raw:
                continue
            try:
                aj = json.loads(ap_path.read_text(encoding="utf-8"))
                # anchor 보다 W 초 앞의 관측으로 상태를 짓는다.
                warm_json = dict(aj)
                warm_json["sim_sec"] = warm_sec
                warm_json["local_observation"] = {**(aj.get("local_observation") or {}), **obs_raw[warm_sec]}
                cfg, state, control, DemandStep, det, cal, ci = _setup(ad, warm_json, paths)
                warm_steps = max(1, int(round(args.warmstart_sec / ci)))
                fc = ad.demand_from_state(warm_json, cfg, DemandStep, warm_steps + args.horizon_steps, cal, det)
                warmed = _roll(state, control, cfg, fc, warm_steps)[-1]
                if not args.no_rescale:
                    osum_anchor = ad.build_local_observation_summary(dict(aj), cfg, det, cal)
                    _rescale_to_observed(warmed, cfg, osum_anchor.get("urban_link_storage_occupancy") or {})
                warmed.time_sec = float(anchor)
                states = _roll(warmed, control, cfg, fc[warm_steps:], args.horizon_steps)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{name}@{anchor}: {type(exc).__name__}: {exc}")
                continue

            for k, s in enumerate(states, start=1):
                sec = float(anchor + k * ci)
                raw = obs_raw.get(sec)
                if not raw:
                    continue
                synth = dict(aj)
                synth["local_observation"] = {**(aj.get("local_observation") or {}), **raw}
                osum = ad.build_local_observation_summary(synth, cfg, det, cal)
                o_cons = conserved_from_parts(
                    cfg, osum.get("urban_link_storage_occupancy") or {}, osum.get("urban_movement_queue") or {}
                )
                m_cons = model_conserved(s, cfg)
                for sname, oval in o_cons.items():
                    if oval < MIN_OBS_VEH:
                        continue
                    mval = m_cons.get(sname, 0.0)
                    err = abs(mval - oval)
                    ape_by_step[k].append(100.0 * err / oval)
                    signed.append(100.0 * (mval - oval) / oval)
                    g5[k][0] += 1 if err <= g5_threshold(oval) else 0
                    g5[k][1] += 1

    payload = {
        "schema_version": "rollout-warmstart-v1",
        "status": "PASS" if ape_by_step and not failures else "FAIL",
        "reasons": failures[:20],
        "setup": {
            "run_dir": str(run_dir), "anchors_sec": anchors,
            "warmstart_sec": args.warmstart_sec, "horizon_steps": args.horizon_steps,
            "rescale_to_observed": not args.no_rescale, "cells": len(cells),
            "conserved_unit": "storage + movement queue (origin 기준)",
            "g5_threshold": "max(5.0 veh, 0.10 * observed)",
        },
        "median_ape_by_step": {str(k): st.median(v) for k, v in sorted(ape_by_step.items()) if v},
        "g5_pass_rate_by_step": {
            str(k): {"pass": v[0], "total": v[1], "rate_pct": 100.0 * v[0] / v[1] if v[1] else None}
            for k, v in sorted(g5.items())
        },
        "signed_median_pct": st.median(signed) if signed else None,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
                        encoding="utf-8", newline="\n")

    print(f"status={payload['status']}  셀={len(cells)}  warm={args.warmstart_sec}s  "
          f"rescale={'on' if not args.no_rescale else 'off'}")
    for k in sorted(ape_by_step):
        g = payload["g5_pass_rate_by_step"][str(k)]
        print(f"  스텝 {k}  중앙값 {st.median(ape_by_step[k]):6.1f}%   G5 통과 {g['rate_pct']:5.1f}%  ({g['pass']}/{g['total']})")
    if signed:
        print(f"  부호 있는 중앙값 {payload['signed_median_pct']:+.1f}%")
    for r in payload["reasons"][:3]:
        print("  " + r)
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
