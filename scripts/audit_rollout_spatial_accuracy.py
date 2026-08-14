#!/usr/bin/env python3
"""rollout 예측을 **공간 분해**해서 VISSIM 과 대조한다.

## 왜 필요한가

`audit_rollout_prediction_accuracy.py` 는 망 전체 스칼라 4개만 본다. 그것으로는
"맞았다" 고 말할 수 없다 - **링크마다 틀려도 합계는 상쇄되어 맞게 나온다.** 게다가
컨트롤러는 교차로별로 작동하므로 제어 품질을 좌우하는 것은 공간 분해된 정확도다.

두 층을 본다.

    고속도로 세그먼트  16개(FW_E 8 + FW_W 8). 대수 / 밀도 / 속도 셋 다.
                       모델은 state.freeway_density / freeway_speed 와
                       summarize 의 freeway_segment_vehicles 가 준다.
                       VISSIM 은 bottleneck_segments_*.csv 가 같은 셋을 준다.
    도시부 저류        161통. 모델 점유 = capacity - state.urban_link_storage.
                       VISSIM 은 bottleneck_links_*.csv 의 링크별 대수를
                       link_owner/link_upstream 으로 같은 통에 모아 준다.

## 저류 통 이름 규칙

`SC{상류}_to_SC{소유}` — 상류가 있으면. 없으면 `SC{소유}_{방위}_out` (유입 경계).
`derive_urban_storage_capacity.py` 와 같은 규칙이다. 분수 귀속(link_split /
link_upstream_split)이 있는 링크는 지분대로 나눠 넣는다.

## 무엇을 보고하는가

지표별로 셀·anchor·스텝을 가로질러 **개별 단위의 APE 분포**(중앙값 / p90)를 낸다.
집계 APE 와 나란히 놓으면 상쇄가 얼마나 있었는지가 바로 보인다.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

# stdout 을 여기서 다시 감싸면 안 된다 - 아래 import 한 모듈이 이미 감쌌고, 두 번 감싸면
# 바깥 래퍼가 회수될 때 밑의 버퍼를 닫아 버려 마지막 print 가 죽는다(실제로 겪음).

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from audit_rollout_prediction_accuracy import (  # noqa: E402
    _load_adapter,
    ape,
    rollout_from_anchor,
)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCHEMA_VERSION = "rollout-spatial-accuracy-v1"
# 이 밑으로는 APE 분모가 불안정해서 뺀다. 빈 세그먼트/빈 저류의 1대 차이가 100% 로
# 잡히면 분포가 그 잡음에 지배된다.
MIN_OBS_VEH = 5.0
MIN_OBS_SPEED_KPH = 1.0


# --------------------------------------------------------------------------- 저류 지도


def storage_bucket_shares(assignment: Mapping[str, Any]) -> dict[str, dict[str, float]]:
    """VISSIM 링크 -> {저류 이름: 지분}. derive_urban_storage_capacity.py 와 같은 규칙."""
    owner = assignment.get("link_owner") or {}
    upstream = assignment.get("link_upstream") or {}
    leg = assignment.get("link_leg") or {}
    dsplit = assignment.get("link_split") or {}
    usplit = assignment.get("link_upstream_split") or {}

    def down_parts(link: str) -> list[tuple[Any, float]]:
        spec = dsplit.get(link)
        if spec:
            out = []
            for part in spec.get("parts", []):
                to = str(part.get("to", ""))
                if to.startswith("SC"):
                    out.append((int(to[2:]), float(part.get("share", 0.0))))
            if out:
                return out
        own = owner.get(link)
        return [(int(own), 1.0)] if own is not None else []

    def up_parts(link: str) -> list[tuple[Any, float]]:
        spec = usplit.get(link)
        if spec:
            out = []
            for part in spec.get("upstream", []):
                to = str(part.get("to", ""))
                if to.startswith("SC"):
                    out.append((int(to[2:]), float(part.get("share", 0.0))))
            if out:
                return out
        up = upstream.get(link)
        return [(int(up), 1.0)] if up is not None else [(None, 1.0)]

    shares: dict[str, dict[str, float]] = {}
    for link in owner:
        per: dict[str, float] = defaultdict(float)
        for own_sc, ds in down_parts(link):
            for up_sc, us in up_parts(link):
                weight = ds * us
                if weight <= 0:
                    continue
                if up_sc is not None:
                    name = f"SC{int(up_sc)}_to_SC{int(own_sc)}"
                else:
                    name = f"SC{int(own_sc)}_{leg.get(link, '?')}_out"
                per[name] += weight
        if per:
            shares[str(link)] = dict(per)
    return shares


# --------------------------------------------------------------------------- 관측


def observed_segments(path: Path) -> dict[float, dict[str, dict[str, float]]]:
    """sim_sec -> segment_id -> {count, density, speed}"""
    out: dict[float, dict[str, dict[str, float]]] = defaultdict(dict)
    if not path.is_file():
        return out
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                sec = float(row["sim_sec"])
                out[sec][str(row["segment_id"])] = {
                    "count": float(row["count"]),
                    "density": float(row["density_veh_km_lane"]),
                    "speed": float(row["mean_speed_kph"]),
                }
            except (KeyError, TypeError, ValueError):
                continue
    return out


def observed_storage(path: Path, shares: Mapping[str, Mapping[str, float]], want_sec: set[float]):
    """sim_sec -> 저류 이름 -> 대수. 링크 대수를 지분대로 통에 모은다."""
    out: dict[float, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    if not path.is_file():
        return out
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                sec = float(row["sim_sec"])
            except (KeyError, TypeError, ValueError):
                continue
            if sec not in want_sec:
                continue
            per = shares.get(str(row.get("link")))
            if not per:
                continue
            try:
                count = float(row["count"])
            except (KeyError, TypeError, ValueError):
                continue
            for name, weight in per.items():
                out[sec][name] += count * weight
    return out


# --------------------------------------------------------------------------- 모델


def model_segments(state, cfg, summary: Mapping[str, Any]) -> dict[str, dict[str, float]]:
    """모델의 세그먼트별 대수/밀도/속도. segment_id 는 러너 규칙 RW_<link>_S<i> 를 따른다."""
    out: dict[str, dict[str, float]] = {}
    counts = summary.get("freeway_segment_vehicles") or {}
    density = getattr(state, "freeway_density", {}) or {}
    speed = getattr(state, "freeway_speed", {}) or {}
    for link, values in counts.items():
        dens = list(density.get(link, []) or [])
        spd = list(speed.get(link, []) or [])
        for i, veh in enumerate(values):
            out[f"RW_{link}_S{i}"] = {
                "count": float(veh),
                "density": float(dens[i]) if i < len(dens) else float("nan"),
                "speed": float(spd[i]) if i < len(spd) else float("nan"),
            }
    return out


def model_storage_occupancy(state, cfg) -> dict[str, float]:
    """모델의 저류별 점유 대수. urban_link_storage 는 **잔여 용량**이라 뒤집어야 한다."""
    capacity = getattr(cfg.network, "urban_link_storage_veh", {}) or {}
    remaining = getattr(state, "urban_link_storage", {}) or {}
    out: dict[str, float] = {}
    for name, cap in capacity.items():
        rem = remaining.get(name)
        if rem is None:
            continue
        out[str(name)] = max(0.0, float(cap) - float(rem))
    return out


# --------------------------------------------------------------------------- 집계


def _dist(values: Sequence[float]) -> dict[str, float]:
    live = sorted(v for v in values if v == v)
    if not live:
        return {"n": 0}
    return {
        "n": len(live),
        "median": st.median(live),
        "p90": live[int(0.9 * (len(live) - 1))],
        "mean": st.mean(live),
    }


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--tag", default="n5parent_20260814")
    ap.add_argument("--anchors", default="900,1500,2100")
    ap.add_argument("--horizon-steps", type=int, default=3, help="기본 3 = 이 격자의 mpc.horizon_steps")
    ap.add_argument("--limit-cells", type=int, default=0)
    ap.add_argument(
        "--assignment", type=Path,
        default=REPO / "outputs" / "link_player_assignment_pedfold_20260814.json",
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

    run_dir = args.run_dir.resolve()
    anchors = [int(s) for s in str(args.anchors).split(",") if s.strip()]
    paths = {
        "tuning": args.tuning,
        "calibration": args.calibration,
        "detector_mapping": args.detector_mapping,
    }
    assignment = json.loads(args.assignment.read_text(encoding="utf-8"))
    shares = storage_bucket_shares(assignment)

    ad = _load_adapter()
    seg_ape: dict[str, list[float]] = {"count": [], "density": [], "speed": []}
    sto_ape: list[float] = []
    per_unit_seg: dict[str, list[float]] = defaultdict(list)
    per_unit_sto: dict[str, list[float]] = defaultdict(list)
    matched = {"segments": 0, "storages": 0}
    # 매핑 건전성 검사. 저류별 합계가 각 쪽의 집계와 맞아야 per-bucket 오차를 믿을 수
    # 있다. 안 맞으면 오차가 아니라 내 링크->저류 지도가 틀린 것이다.
    sum_check: list[dict[str, float]] = []
    failures: list[str] = []
    cells_used: list[str] = []

    cells = sorted(run_dir.glob(f"state_{args.tag}_*.csv"))
    cells = [c for c in cells if "_r" not in c.name[len("state_") : -len(".csv")].rsplit("_s", 1)[-1]]
    if args.limit_cells:
        cells = cells[: args.limit_cells]

    for state_csv in cells:
        name = state_csv.name[len("state_") : -len(".csv")]
        cells_used.append(name)
        decision_dir = run_dir / f"decisions_{name}"
        obs_seg = observed_segments(run_dir / f"bottleneck_segments_{name}.csv")
        want_sec: set[float] = set()
        for anchor in anchors:
            for k in range(1, args.horizon_steps + 1):
                want_sec.add(float(anchor + 60 * k))
        obs_sto = observed_storage(run_dir / f"bottleneck_links_{name}.csv", shares, want_sec)

        for anchor in anchors:
            anchor_path = decision_dir / f"anchor_{anchor:06d}.json"
            if not anchor_path.is_file():
                continue
            try:
                anchor_json = json.loads(anchor_path.read_text(encoding="utf-8"))
                steps, _interval, cfg = rollout_from_anchor(ad, anchor_json, args.horizon_steps, paths)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{name}@{anchor}: {type(exc).__name__}: {exc}")
                continue
            for step in steps:
                sec = float(step["sim_sec"])
                ms = model_segments(step["state"], cfg, step["summary"])
                os_ = obs_seg.get(sec, {})
                for sid, mv in ms.items():
                    ov = os_.get(sid)
                    if not ov:
                        continue
                    matched["segments"] += 1
                    if ov["count"] >= MIN_OBS_VEH:
                        a = ape(mv["count"], ov["count"])
                        seg_ape["count"].append(a)
                        per_unit_seg[sid].append(a)
                        seg_ape["density"].append(ape(mv["density"], ov["density"]))
                    if ov["speed"] >= MIN_OBS_SPEED_KPH:
                        seg_ape["speed"].append(ape(mv["speed"], ov["speed"]))

                mo = model_storage_occupancy(step["state"], cfg)
                oo = obs_sto.get(sec, {})
                sum_check.append(
                    {
                        "sim_sec": sec,
                        "model_storage_sum": sum(mo.values()),
                        "model_urban_total": float(step["summary"].get("urban_link_occupancy_total_veh", float("nan"))),
                        "observed_storage_sum": sum(oo.values()),
                    }
                )
                for sname, mval in mo.items():
                    oval = oo.get(sname)
                    if oval is None or oval < MIN_OBS_VEH:
                        continue
                    matched["storages"] += 1
                    a = ape(mval, oval)
                    sto_ape.append(a)
                    per_unit_sto[sname].append(a)

    worst_seg = sorted(
        ((k, st.median([v for v in vs if v == v])) for k, vs in per_unit_seg.items() if vs),
        key=lambda kv: -kv[1],
    )[:8]
    worst_sto = sorted(
        ((k, st.median([v for v in vs if v == v])) for k, vs in per_unit_sto.items() if vs),
        key=lambda kv: -kv[1],
    )[:10]

    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if (matched["segments"] or matched["storages"]) and not failures else "FAIL",
        "reasons": failures[:20],
        "setup": {
            "run_dir": str(run_dir),
            "anchors_sec": anchors,
            "horizon_steps": args.horizon_steps,
            "cells": cells_used,
            "min_observed_veh": MIN_OBS_VEH,
            "min_observed_speed_kph": MIN_OBS_SPEED_KPH,
            "note": (
                "APE 분모가 작으면 분포가 잡음에 지배되므로 관측 대수 5 미만 / 속도 1 kph "
                "미만 단위는 뺐다. 뺀 개수는 matched 와 n 의 차이로 드러난다."
            ),
        },
        "matched_units": matched,
        "freeway_segment_ape": {k: _dist(v) for k, v in seg_ape.items()},
        "urban_storage_ape": _dist(sto_ape),
        "worst_segments_median_ape": [{"segment_id": k, "median_ape": v} for k, v in worst_seg],
        "worst_storages_median_ape": [{"storage": k, "median_ape": v} for k, v in worst_sto],
        "storage_units_compared": len(per_unit_sto),
        "mapping_sum_check": {
            "note": (
                "저류별 합계가 양쪽 집계와 맞아야 per-bucket 오차를 믿을 수 있다. "
                "model_storage_sum 은 model_urban_total 과, observed_storage_sum 은 "
                "VISSIM urban_vehicles 와 같은 규모여야 한다."
            ),
            "samples": sum_check[:12],
            "model_ratio_median": (
                st.median([c["model_storage_sum"] / c["model_urban_total"]
                           for c in sum_check if c["model_urban_total"]])
                if sum_check else float("nan")
            ),
        },
        "segment_units_compared": len(per_unit_seg),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8", newline="\n",
    )

    print(f"status={payload['status']}  셀={len(cells_used)}  세그먼트단위={payload['segment_units_compared']}  저류단위={payload['storage_units_compared']}")
    for k, d in payload["freeway_segment_ape"].items():
        if d.get("n"):
            print(f"  고속 세그먼트 {k:8s} n={d['n']:6d}  중앙값={d['median']:7.1f}%  p90={d['p90']:8.1f}%")
    d = payload["urban_storage_ape"]
    if d.get("n"):
        print(f"  도시 저류    {'occupancy':8s} n={d['n']:6d}  중앙값={d['median']:7.1f}%  p90={d['p90']:8.1f}%")
    if worst_sto:
        print("  최악 저류:", ", ".join(f"{k}={v:.0f}%" for k, v in worst_sto[:5]))
    for r in payload["reasons"][:3]:
        print("  " + r)
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
