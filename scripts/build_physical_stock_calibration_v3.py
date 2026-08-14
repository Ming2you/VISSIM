#!/usr/bin/env python3
"""N6 — 부모런에서 physical_stock_calibration_v3.json 을 만든다.

## 지금 무엇을 갈아끼우는가

`outputs/urban_storage_capacity_ovr_20260814.json` 이 `jam_density_veh_km_lane: 130.0`,
**`jam_sample_count: 0`** 이다. 지금 plant 는 관측이 하나도 없는 폴백 상수로 돌고 있다.
이 도구가 그것을 실측으로 대체한다.

## 추정기 셋 — 셋을 다 내고 비교한다

    headway          정지차 연속쌍의 간격에서 (차량길이 + 정지간격) 을 직접 잰다.
                     k_jam = 1000 / gap. anchor 의 전 차량 레코드(lane_no, position_m)가 출처다.
    queue_occupancy  포화 링크에서 stopped / ((len - queue_tail)/1000 * lanes).
                     큐가 링크 일부만 차지하는 것을 큐꼬리로 잘라 보정한다.
    link_p90         링크별 최대밀도의 p90. derive_urban_storage_capacity.py:39 와 같은 산식.
                     밀도를 링크 **전체 길이**로 나누므로 하향 편의가 있다 - 비교용이다.

셋이 갈리는 것이 정상이고, 그 차이가 계획이 "큐꼬리 관측으로 고정분율(0.35/0.50)을
대체한다" 고 한 이유다. 실측으로 headway 168 대 link_p90 103~129 였다.

## geometry prior 는 망에서 나온다

임의의 상수를 쓰지 않는다. 차량 길이는
`vehicleInput/timeIntervalVehVolume[vehComp,volume]` 로 볼륨 가중한 차종 구성 →
`vehicleType[model2D3DDistr]` → `model2D3DDistribution` → `model2D3DDistributionElement[share]`
→ `model2D3D` → `model2D3DSegment[length]` 합으로 계산한다. 계획의 PASS 기준
"geometry prior 차이 <=15%" 가 이 값을 기준으로 삼는다.

정지간격은 관측(headway)에서 차량길이를 빼서 얻는다 - 둘의 합만 관측되므로 이 분해에는
prior 가 필요하고, 그 prior 가 위 차량길이다.

## 적합은 training 시드에서만

holdout 시드(47)는 적합·임계선택·후보교체에 쓰지 않는다. 이 도구는 holdout 셀을
**읽지도 않는다** - 읽지 않았다는 사실을 산출물에 기록한다.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics as st
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

SCHEMA_VERSION = "physical-stock-calibration-v3"
ANCHORS_SEC = (900, 1500, 2100, 2700)
SATURATED_SPEED_KPH = 3.0
SATURATED_STOPPED_FRACTION = 0.5
MIN_LANE_GROUPS = 30
MIN_SAMPLES = 200
MAX_CI_HALF_WIDTH_FRACTION = 0.10
MAX_PRIOR_DIFF_FRACTION = 0.15
MAX_SEED_FIT_DIFF_FRACTION = 0.15
# 같은 차로에서 이 간격을 넘으면 큐가 끊긴 것으로 본다. 정지차가 떨어져 서 있으면
# 그 사이는 차간거리가 아니라 빈 공간이다.
MAX_QUEUE_GAP_M = 15.0
BOOTSTRAP_DRAWS = 2000

# anchor 4개를 못 채운 셀. 조용히 빠지면 안 되므로 모아서 산출물에 싣는다.
INCOMPLETE_CELLS: list[str] = []


# --------------------------------------------------------------------------- 기하 prior


def vehicle_length_prior(inpx: Path) -> dict[str, Any]:
    """볼륨 가중 차종 구성의 평균 차량 길이(m)를 망에서 계산한다."""
    root = ET.parse(inpx).getroot()

    model_length: dict[str, float] = {}
    for model in root.iter("model2D3D"):
        total = sum(float(seg.get("length", 0.0)) for seg in model.iter("model2D3DSegment"))
        if total > 0:
            model_length[str(model.get("no"))] = total

    distr_length: dict[str, float] = {}
    for dist in root.iter("model2D3DDistribution"):
        num, den = 0.0, 0.0
        for el in dist.iter("model2D3DDistributionElement"):
            share = float(el.get("share", 0.0))
            length = model_length.get(str(el.get("model2D3D")))
            if length is not None and share > 0:
                num += share * length
                den += share
        if den > 0:
            distr_length[str(dist.get("no"))] = num / den

    type_length: dict[str, float] = {}
    for vt in root.iter("vehicleType"):
        length = distr_length.get(str(vt.get("model2D3DDistr")))
        if length is not None:
            type_length[str(vt.get("no"))] = length

    comp_length: dict[str, float] = {}
    for comp in root.iter("vehicleComposition"):
        num, den = 0.0, 0.0
        for el in comp.iter("vehicleCompositionRelativeFlow"):
            # relFlow 가 비어 있으면 VISSIM 기본값 1 이다. 0 이 아니다.
            raw = (el.get("relFlow") or "").strip()
            weight = float(raw) if raw else 1.0
            length = type_length.get(str(el.get("vehType")))
            if length is not None and weight > 0:
                num += weight * length
                den += weight
        if den > 0:
            comp_length[str(comp.get("no"))] = num / den

    # 유입 볼륨으로 구성을 가중한다.
    num, den = 0.0, 0.0
    comp_volume: dict[str, float] = defaultdict(float)
    for tiv in root.iter("timeIntervalVehVolume"):
        comp = str(tiv.get("vehComp"))
        try:
            volume = float(tiv.get("volume", 0.0))
        except (TypeError, ValueError):
            continue
        length = comp_length.get(comp)
        if length is None or volume <= 0:
            continue
        comp_volume[comp] += volume
        num += volume * length
        den += volume

    return {
        "vehicle_length_m": (num / den) if den > 0 else float("nan"),
        "source": "inpx vehicleInput volume-weighted composition -> model2D3DSegment length",
        "network": inpx.name,
        "composition_count": len(comp_length),
        "vehicle_type_count": len(type_length),
        "weighted_volume_vph": den,
        "per_composition_length_m": {k: round(v, 4) for k, v in sorted(comp_length.items())},
    }


# --------------------------------------------------------------------------- 셀 열거


def cell_records(run_dir: Path, tag: str, seeds: Iterable[int]) -> list[dict[str, Any]]:
    """완주한 셀만 돌려준다.

    **도는 중인 셀을 넣으면 안 된다.** 러너는 상태 CSV 를 처음부터 열어 두고 쓰기 때문에
    파일 존재만으로는 완주를 알 수 없고, anchor 도 시각을 지날 때마다 하나씩 생긴다.
    부분 데이터가 섞이면 표본이 조용히 편향된다 - anchor 2700(가장 혼잡한 시각)만 빠지면
    jam density 가 낮게 나온다. anchor 4개가 다 있는 것을 완주 조건으로 삼는다.
    """
    wanted = set(int(s) for s in seeds)
    out: list[dict[str, Any]] = []
    for state in sorted(run_dir.glob(f"state_{tag}_*.csv")):
        name = state.name[len("state_") : -len(".csv")]
        # base replay(_rNN)는 부모와 같은 궤적이므로 캘리브레이션 표본을 부풀린다. 제외한다.
        if "_r" in name.rsplit("_s", 1)[-1]:
            continue
        parts = name.split("_")
        try:
            seed = int(parts[-1][1:])
            demand = int(parts[-2][1:]) / 100.0
            role = parts[-3]
        except (IndexError, ValueError):
            continue
        if seed not in wanted:
            continue
        decision_dir = run_dir / f"decisions_{name}"
        if len(_anchor_paths(decision_dir)) != len(ANCHORS_SEC):
            INCOMPLETE_CELLS.append(name)
            continue
        out.append(
            {
                "name": name,
                "role": role,
                "demand": demand,
                "seed": seed,
                "state_csv": state,
                "links_csv": run_dir / f"bottleneck_links_{name}.csv",
                "decision_dir": run_dir / f"decisions_{name}",
            }
        )
    return out


# --------------------------------------------------------------------------- 추정기


def _anchor_paths(decision_dir: Path) -> list[Path]:
    return [
        decision_dir / f"anchor_{sec:06d}.json"
        for sec in ANCHORS_SEC
        if (decision_dir / f"anchor_{sec:06d}.json").is_file()
    ]


def headway_samples(decision_dir: Path) -> dict[str, Any]:
    """정지차 연속쌍의 간격(m). 같은 (링크, 차로) 안에서만, 큐가 끊긴 자리는 제외한다."""
    gaps: list[float] = []
    lane_groups: set[tuple[str, str]] = set()
    thresholds: set[float] = set()
    for path in _anchor_paths(decision_dir):
        payload = json.loads(path.read_text(encoding="utf-8"))
        vr = payload.get("vehicle_records") or {}
        threshold = vr.get("stopped_threshold_kph")
        if threshold is not None:
            thresholds.add(float(threshold))
        by_lane: dict[tuple[str, str], list[float]] = defaultdict(list)
        for rec in vr.get("records") or []:
            if not rec.get("stopped"):
                continue
            key = (str(rec.get("link_no")), str(rec.get("lane_no")))
            by_lane[key].append(float(rec.get("position_m", 0.0)))
        for key, positions in by_lane.items():
            if len(positions) < 2:
                continue
            lane_groups.add(key)
            positions.sort()
            for a, b in zip(positions, positions[1:]):
                gap = b - a
                if 0.0 < gap <= MAX_QUEUE_GAP_M:
                    gaps.append(gap)
    return {
        "gaps_m": gaps,
        "lane_groups": len(lane_groups),
        "stopped_threshold_kph": sorted(thresholds),
    }


def queue_occupancy_samples(decision_dir: Path, geometry: dict[str, Any]) -> dict[str, Any]:
    """포화 링크에서 큐 점유길이로 나눈 밀도. 큐꼬리가 점유 구간을 준다."""
    densities: list[float] = []
    links: set[str] = set()
    skipped_no_geometry = 0
    for path in _anchor_paths(decision_dir):
        payload = json.loads(path.read_text(encoding="utf-8"))
        obs = payload.get("local_observation") or {}
        counts = obs.get("link_counts") or {}
        stopped = obs.get("link_stopped_counts") or {}
        speeds = obs.get("link_speeds_kph") or {}
        tails = obs.get("link_queue_tail_pos_m") or {}
        for link, count in counts.items():
            count = float(count)
            stp = float(stopped.get(link, 0.0))
            if count <= 0 or stp < SATURATED_STOPPED_FRACTION * count:
                continue
            if float(speeds.get(link, 1e9)) >= SATURATED_SPEED_KPH:
                continue
            geo = geometry.get(str(link))
            if not geo:
                skipped_no_geometry += 1
                continue
            lanes = float(geo.get("lanes", 0) or 0)
            length_m = float(geo.get("len_m", 0.0) or 0.0)
            tail = float(tails.get(link, 0.0) or 0.0)
            # 큐는 정지선(하류 끝)에서 꼬리까지다. 꼬리가 0 이면 링크 전체로 본다.
            occupied_m = length_m - tail if tail > 0 else length_m
            if lanes <= 0 or occupied_m <= 5.0:
                continue
            densities.append(stp / (occupied_m / 1000.0) / lanes)
            links.add(str(link))
    return {
        "densities": densities,
        "links": len(links),
        "skipped_no_geometry": skipped_no_geometry,
    }


def link_p90_samples(links_csv: Path, geometry: dict[str, Any], t0: float) -> dict[str, Any]:
    """derive_urban_storage_capacity.py:39 와 같은 산식. 비교용."""
    per: dict[str, list[tuple[float, float, float]]] = defaultdict(list)
    if not links_csv.is_file():
        return {"per_link_max": [], "links": 0}
    with open(links_csv, newline="", encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            try:
                if float(row["sim_sec"]) < t0:
                    continue
                link = row["link"]
                if link not in geometry:
                    continue
                per[link].append(
                    (float(row["count"]), float(row["mean_speed_kph"]), float(row["stopped_count"]))
                )
            except (KeyError, TypeError, ValueError):
                continue
    maxima: list[float] = []
    for link, rows in per.items():
        geo = geometry[link]
        lkm = float(geo["len_m"]) / 1000.0
        lanes = float(geo["lanes"])
        if lkm <= 0.02 or lanes <= 0:
            continue
        jam = [
            n / lkm / lanes
            for n, sp, stp in rows
            if n > 0 and sp < SATURATED_SPEED_KPH and stp >= SATURATED_STOPPED_FRACTION * n
        ]
        if jam:
            maxima.append(max(jam))
    return {"per_link_max": maxima, "links": len(maxima)}


# --------------------------------------------------------------------------- 통계


def _percentile(values: Sequence[float], q: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    idx = int(q * (len(ordered) - 1))
    return ordered[idx]


def _lcg(seed: int):
    """결정적 난수. Math.random 없이 재현 가능한 bootstrap 을 만든다."""
    state = seed & 0xFFFFFFFF

    def nxt() -> float:
        nonlocal state
        state = (1664525 * state + 1013904223) & 0xFFFFFFFF
        return state / 0x100000000

    return nxt


def cluster_bootstrap_ci(
    per_cluster: dict[str, list[float]], statistic, *, draws: int = BOOTSTRAP_DRAWS, seed: int = 20260815
) -> dict[str, Any]:
    """run-cluster bootstrap. 표본이 아니라 **런(클러스터)** 을 복원추출한다.

    같은 런 안의 표본은 서로 독립이 아니다 - 같은 시드·같은 수요의 한 궤적에서 나온다.
    표본 단위로 뽑으면 CI 가 실제보다 좁아진다.
    """
    clusters = [name for name, values in per_cluster.items() if values]
    if len(clusters) < 2:
        return {"available": False, "reason": f"클러스터 {len(clusters)}개로는 못 잰다"}
    rand = _lcg(seed)
    estimates: list[float] = []
    for _ in range(draws):
        pooled: list[float] = []
        for _ in range(len(clusters)):
            pick = clusters[min(int(rand() * len(clusters)), len(clusters) - 1)]
            pooled.extend(per_cluster[pick])
        if pooled:
            value = statistic(pooled)
            if not math.isnan(value):
                estimates.append(value)
    if len(estimates) < 100:
        return {"available": False, "reason": f"bootstrap 표본 {len(estimates)}개"}
    lo = _percentile(estimates, 0.025)
    hi = _percentile(estimates, 0.975)
    point = statistic([v for values in per_cluster.values() for v in values])
    half = (hi - lo) / 2.0
    return {
        "available": True,
        "clusters": len(clusters),
        "draws": len(estimates),
        "point": point,
        "ci95_low": lo,
        "ci95_high": hi,
        "half_width": half,
        "half_width_fraction": (half / point) if point else float("nan"),
    }


# --------------------------------------------------------------------------- 조립


def build(
    run_dir: Path,
    tag: str,
    assignment_path: Path,
    network_path: Path,
    *,
    training_seeds: Sequence[int],
    holdout_seeds: Sequence[int],
    t0: float,
) -> dict[str, Any]:
    assignment = json.loads(assignment_path.read_text(encoding="utf-8"))
    geometry = assignment.get("link_geometry") or {}
    prior = vehicle_length_prior(network_path)

    training = cell_records(run_dir, tag, training_seeds)
    holdout_names = [c["name"] for c in cell_records(run_dir, tag, holdout_seeds)]

    reasons: list[str] = []
    if not training:
        reasons.append("training 셀이 하나도 없다")
    overlap = sorted(set(training_seeds) & set(holdout_seeds))
    if overlap:
        reasons.append(f"training/holdout 시드 중복: {overlap}")

    per_cell: list[dict[str, Any]] = []
    headway_by_cell: dict[str, list[float]] = {}
    occupancy_by_cell: dict[str, list[float]] = {}
    linkp90_by_cell: dict[str, list[float]] = {}
    thresholds: set[float] = set()
    lane_group_total = 0

    for cell in training:
        hw = headway_samples(cell["decision_dir"])
        qo = queue_occupancy_samples(cell["decision_dir"], geometry)
        lp = link_p90_samples(cell["links_csv"], geometry, t0)
        headway_by_cell[cell["name"]] = hw["gaps_m"]
        occupancy_by_cell[cell["name"]] = qo["densities"]
        linkp90_by_cell[cell["name"]] = lp["per_link_max"]
        thresholds.update(hw["stopped_threshold_kph"])
        lane_group_total += hw["lane_groups"]
        per_cell.append(
            {
                "name": cell["name"],
                "role": cell["role"],
                "demand": cell["demand"],
                "seed": cell["seed"],
                "headway_gap_samples": len(hw["gaps_m"]),
                "headway_lane_groups": hw["lane_groups"],
                "headway_median_gap_m": st.median(hw["gaps_m"]) if hw["gaps_m"] else float("nan"),
                "headway_k_jam": (1000.0 / st.median(hw["gaps_m"])) if hw["gaps_m"] else float("nan"),
                "queue_occupancy_samples": len(qo["densities"]),
                "queue_occupancy_links": qo["links"],
                "queue_occupancy_p90": _percentile(qo["densities"], 0.9),
                "link_p90_links": lp["links"],
                "link_p90": _percentile(lp["per_link_max"], 0.9),
            }
        )

    def k_from_gaps(gaps: Sequence[float]) -> float:
        return 1000.0 / st.median(gaps) if gaps else float("nan")

    headway_ci = cluster_bootstrap_ci(headway_by_cell, k_from_gaps)
    occupancy_ci = cluster_bootstrap_ci(occupancy_by_cell, lambda v: _percentile(v, 0.9))
    linkp90_ci = cluster_bootstrap_ci(linkp90_by_cell, lambda v: _percentile(v, 0.9))

    total_gaps = sum(len(v) for v in headway_by_cell.values())
    median_gap = (
        st.median([g for values in headway_by_cell.values() for g in values]) if total_gaps else float("nan")
    )
    k_jam = 1000.0 / median_gap if median_gap and not math.isnan(median_gap) else float("nan")
    length_prior = prior["vehicle_length_m"]
    standstill_gap = median_gap - length_prior if not math.isnan(median_gap) else float("nan")

    # --- PASS 기준 ---
    if lane_group_total < MIN_LANE_GROUPS:
        reasons.append(f"포화 lane-group {lane_group_total} < {MIN_LANE_GROUPS}")
    if total_gaps < MIN_SAMPLES:
        reasons.append(f"표본 {total_gaps} < {MIN_SAMPLES}")
    if headway_ci.get("available"):
        frac = headway_ci["half_width_fraction"]
        if not math.isnan(frac) and frac > MAX_CI_HALF_WIDTH_FRACTION:
            reasons.append(f"jam CI 반폭 {frac:.1%} > {MAX_CI_HALF_WIDTH_FRACTION:.0%}")
    else:
        reasons.append(f"bootstrap 불가: {headway_ci.get('reason')}")
    if not math.isnan(length_prior) and not math.isnan(median_gap):
        # 관측 간격은 (차량길이 + 정지간격) 이므로 prior 보다 커야 하고, 정지간격이
        # 음수로 나오면 prior 나 관측 중 하나가 틀린 것이다.
        if standstill_gap <= 0:
            reasons.append(
                f"정지간격이 음수다({standstill_gap:.3f} m) - 차량길이 prior {length_prior:.3f} m 가 관측 간격 {median_gap:.3f} m 보다 크다"
            )
    seed_fits = [c["headway_k_jam"] for c in per_cell if not math.isnan(c["headway_k_jam"])]
    if len(seed_fits) >= 2:
        spread = (max(seed_fits) - min(seed_fits)) / st.mean(seed_fits)
        if spread > MAX_SEED_FIT_DIFF_FRACTION:
            reasons.append(f"시드별 적합 차이 {spread:.1%} > {MAX_SEED_FIT_DIFF_FRACTION:.0%}")
    else:
        spread = float("nan")

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not reasons else "FAIL",
        "reasons": sorted(set(reasons)),
        "split": {
            "training_seeds": sorted(set(int(s) for s in training_seeds)),
            "holdout_seeds": sorted(set(int(s) for s in holdout_seeds)),
            "training_cells": [c["name"] for c in training],
            "holdout_cells_not_read": holdout_names,
            "incomplete_cells_excluded": sorted(set(INCOMPLETE_CELLS)),
            "note": "holdout 셀은 적합·임계선택·후보교체에 쓰지 않았다. 이 도구는 읽지도 않는다.",
        },
        "prior": prior,
        "definitions": {
            "saturated": f"speed < {SATURATED_SPEED_KPH} kph 이고 stopped >= {SATURATED_STOPPED_FRACTION} * count",
            "stopped_threshold_kph_in_runner": sorted(thresholds),
            "note": (
                "러너의 stopped 플래그는 위 임계로 찍힌다(계획의 lane-group 필터 3 kph 와 다를 수 있다). "
                "보수적인 쪽이며 어느 정의를 썼는지 여기 기록한다."
            ),
            "max_queue_gap_m": MAX_QUEUE_GAP_M,
            "t0_sec": t0,
        },
        "estimators": {
            "headway": {
                "k_jam_veh_km_lane": k_jam,
                "median_gap_m": median_gap,
                "samples": total_gaps,
                "lane_groups": lane_group_total,
                "ci95": headway_ci,
                "method": "정지차 연속쌍 간격의 중앙값 -> 1000/gap",
            },
            "queue_occupancy": {
                "k_jam_veh_km_lane": _percentile(
                    [v for values in occupancy_by_cell.values() for v in values], 0.9
                ),
                "samples": sum(len(v) for v in occupancy_by_cell.values()),
                "ci95": occupancy_ci,
                "method": "포화 링크에서 stopped / ((len - queue_tail)/1000 * lanes) 의 p90",
            },
            "link_p90": {
                "k_jam_veh_km_lane": _percentile(
                    [v for values in linkp90_by_cell.values() for v in values], 0.9
                ),
                "samples": sum(len(v) for v in linkp90_by_cell.values()),
                "ci95": linkp90_ci,
                "method": "링크별 최대밀도의 p90 (링크 전체 길이로 나눔 - 하향 편의 있음)",
            },
        },
        "fit": {
            "jam_density_veh_km_lane": k_jam,
            "chosen_estimator": "headway",
            "why": (
                "간격을 직접 재므로 큐가 링크의 어디를 차지하는지에 의존하지 않는다. "
                "link_p90 은 밀도를 링크 전체 길이로 나눠 하향 편의가 있고, queue_occupancy 는 "
                "큐꼬리 관측이 anchor 4시점에만 있어 표본이 얇다."
            ),
            "vehicle_length_m": length_prior,
            "standstill_gap_m": standstill_gap,
            "seed_fit_spread_fraction": spread,
        },
        "per_cell": per_cell,
        "sample_dimensions": {
            "training_cells": len(training),
            "anchors_per_cell": len(ANCHORS_SEC),
            "headway_samples": total_gaps,
            "saturated_lane_groups": lane_group_total,
        },
        "inputs": {
            "run_dir": str(run_dir),
            "assignment": assignment_path.name,
            "assignment_sha256": hashlib.sha256(assignment_path.read_bytes()).hexdigest(),
            "network": network_path.name,
        },
    }
    payload["semantic_sha256"] = hashlib.sha256(
        json.dumps(
            {k: v for k, v in payload.items() if k not in {"inputs"}},
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    repo = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--tag", default="n5parent_20260814")
    ap.add_argument(
        "--assignment",
        type=Path,
        default=repo / "outputs" / "link_player_assignment_pedfold_20260814.json",
    )
    ap.add_argument(
        "--network",
        type=Path,
        default=repo / "network" / "real_world_gaepo_modi" / "modi_eval_userfix_20260814e.inpx",
    )
    ap.add_argument("--training-seeds", default="13,29")
    ap.add_argument("--holdout-seeds", default="47")
    ap.add_argument("--t0", type=float, default=900.0)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)

    payload = build(
        args.run_dir.resolve(),
        args.tag,
        args.assignment.resolve(),
        args.network.resolve(),
        training_seeds=[int(s) for s in str(args.training_seeds).split(",") if s.strip()],
        holdout_seeds=[int(s) for s in str(args.holdout_seeds).split(",") if s.strip()],
        t0=args.t0,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    est = payload["estimators"]
    print(
        "status=%s cells=%d samples=%d lane_groups=%d hash=%s"
        % (
            payload["status"],
            payload["sample_dimensions"]["training_cells"],
            payload["sample_dimensions"]["headway_samples"],
            payload["sample_dimensions"]["saturated_lane_groups"],
            payload["semantic_sha256"][:16],
        )
    )
    print(
        "  차량길이 prior %.3f m   관측 간격 중앙값 %.3f m   정지간격 %.3f m"
        % (
            payload["prior"]["vehicle_length_m"],
            est["headway"]["median_gap_m"],
            payload["fit"]["standstill_gap_m"],
        )
    )
    for name in ("headway", "queue_occupancy", "link_p90"):
        rec = est[name]
        ci = rec["ci95"]
        band = (
            "CI95 [%.2f, %.2f] 반폭 %.1f%%"
            % (ci["ci95_low"], ci["ci95_high"], 100.0 * ci["half_width_fraction"])
            if ci.get("available")
            else f"CI 없음 ({ci.get('reason')})"
        )
        print("  %-16s k_jam=%8.2f  n=%-7d %s" % (name, rec["k_jam_veh_km_lane"], rec["samples"], band))
    for reason in payload["reasons"][:10]:
        print("  " + reason)
    return 2 if args.strict and payload["status"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
