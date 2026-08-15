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
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)

    run_dir = args.run_dir.resolve()
    anchors = [int(s) for s in str(args.anchors).split(",") if s.strip()]
    paths = {"tuning": args.tuning, "calibration": args.calibration, "detector_mapping": args.detector_mapping}

    ad = _load_adapter()
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
        "g5_pass_rate_by_step": {
            str(k): {"pass": v[0], "total": v[1], "rate_pct": 100.0 * v[0] / v[1] if v[1] else None}
            for k, v in sorted(g5_pass.items())
        },
        "signed_median_pct": st.median(signed) if signed else None,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
                        encoding="utf-8", newline="\n")

    print(f"status={payload['status']}  셀={len(cells)}")
    print(f"{'스텝':>4s}  {'보존단위':>9s}  {'저류만':>9s}  {'G5 통과':>9s}")
    for k in sorted(conserved):
        c = st.median(conserved[k])
        s = st.median(storage_only[k]) if storage_only.get(k) else float("nan")
        g = payload["g5_pass_rate_by_step"][str(k)]
        print(f"{k:>4d}  {c:8.1f}%  {s:8.1f}%  {g['rate_pct']:7.1f}%  ({g['pass']}/{g['total']})")
    print(f"부호 있는 중앙값 {payload['signed_median_pct']:+.1f}%")
    for r in payload["reasons"][:3]:
        print("  " + r)
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
