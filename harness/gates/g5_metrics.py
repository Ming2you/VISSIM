# 계약 §11 G5 측정 — Episode 에서 freeway 평균속도 MAPE / 셀 count MAE / urban 큐·storage 오차를 낸다.
"""G5 채점기.

**집계 수준을 두 개 다 낸다.** 계약 §11 G5 원문은

    "freeway mean-speed MAPE <= 10%, cell count MAE <= max(5 veh, 10%)"

인데 *mean-speed* 는 무엇에 대한 평균인지 쓰여 있지 않고, *cell* 은 G1/G2 가 정의한
"lane group 의 ordered cell"이므로 **셀(=세그먼트) 단위**가 계약이 요구한 수준이다.
그래서 판정은 아래처럼 갈라 쓴다.

    cell count MAE   -> **cell 수준이 판정 기준**. 계약이 'cell'이라고 명시했다.
    mean-speed MAPE  -> 계약 문구가 'mean-speed'라 링크 평균이 자연스러운 독법이지만,
                        셀 수준이 더 엄격하고 이전 보고에서 두 수준의 결론이 갈렸다.
                        **양쪽 다 계산해 리포트하고, 게이트는 두 수준 모두 요구**한다.
                        (느슨한 쪽만 통과하는 상태를 PASS 라고 부르지 않는다.)

임계 `max(5 veh, 10%)` 의 10 % 는 **그 집계 수준에서 관측된 평균 count** 에 대한 비율로
읽는다. 셀 수준과 링크 수준의 count 규모가 8배 다르므로 임계도 함께 움직여야 한다.

★ urban 항의 실측 제약. 이 플랜트의 관측 채널은
`real_world_modi_connector_local_v1` 이고 observable_links 22개는 전부 **본선 체인 링크와
커넥터**다(도시부 교차로 링크 0개, boundary_link_to_queue 비어 있음). 즉 도시부
큐/storage 에는 대응 관측이 존재하지 않는다. 관측 뒷받침이 있는 엔티티는 램프 큐 4개와
off-ramp storage 4개뿐이다. 그래서 이 모듈은
  - 도시부 엔티티 커버리지를 세어 리포트하고,
  - 커버리지가 1.0 이 아니면 urban 기준을 **NOT_EVALUATED** 로 둔다(PASS 로 위장하지 않는다),
  - 관측되는 8개(interface queue)는 별도 진단 지표로 따로 낸다.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from episode import CellGeometry, Episode

PASS = "PASS"
FAIL = "FAIL"
NOT_EVALUATED = "NOT_EVALUATED"

DEFAULT_THRESHOLDS = {
    "freeway_mean_speed_mape_max": 0.10,
    "cell_count_mae_floor_veh": 5.0,
    "cell_count_mae_ratio": 0.10,
    "urban_queue_error_initial_max": 0.25,
    "urban_queue_error_promotion_max": 0.15,
}


def _finite(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _mean(values: Sequence[float]) -> float | None:
    return statistics.fmean(values) if values else None


def _criterion(name: str, value: Any, operator: str, threshold: Any, *, evaluated: bool = True,
               note: str = "") -> dict[str, Any]:
    if not evaluated or value is None or threshold is None:
        verdict = NOT_EVALUATED
    elif operator == "<=":
        verdict = PASS if value <= threshold else FAIL
    elif operator == ">=":
        verdict = PASS if value >= threshold else FAIL
    else:
        raise AssertionError(operator)
    out = {"name": name, "value": value, "operator": operator, "threshold": threshold,
           "verdict": verdict}
    if note:
        out["note"] = note
    return out


def _gate(criteria: Sequence[Mapping[str, Any]]) -> str:
    verdicts = {item["verdict"] for item in criteria}
    if FAIL in verdicts:
        return FAIL
    if NOT_EVALUATED in verdicts:
        return NOT_EVALUATED
    return PASS


# ---------------------------------------------------------------------------
# 1. 표본 추출 — Episode 하나에서 (수준, 스텝)별 오차 표본을 뽑는다
# ---------------------------------------------------------------------------


@dataclass
class Sample:
    """오차 표본 하나. `level` 은 cell 또는 link, `step` 은 지평 스텝 k."""

    level: str
    entity: str
    step: int
    predicted: float
    observed: float

    @property
    def abs_error(self) -> float:
        return abs(self.predicted - self.observed)

    @property
    def ape(self) -> float | None:
        if abs(self.observed) < 1.0e-9:
            return None
        return abs(self.predicted - self.observed) / abs(self.observed)


def _link_speed(state: Any, geometry: CellGeometry, link: str) -> tuple[float, float]:
    """(count 가중 평균속도, 총 count). 링크 수준 평균속도의 정의."""

    total_count = 0.0
    weighted = 0.0
    for index in range(geometry.segment_count(link)):
        density = float(state.freeway_density[link][index])
        speed = float(state.freeway_speed[link][index])
        count = geometry.count(link, index, density)
        total_count += count
        weighted += count * speed
    if total_count <= 1.0e-9:
        return 0.0, 0.0
    return weighted / total_count, total_count


def freeway_samples(episode: Episode) -> list[Sample]:
    """본선 속도/count 표본을 cell 과 link 두 수준으로 동시에 뽑는다."""

    geometry = episode.geometry
    out: list[Sample] = []
    if geometry is None:
        return out
    for step, pred, obs in episode.pairs():
        for link in geometry.links:
            if link not in pred.freeway_density or link not in obs.freeway_density:
                continue
            for index in range(geometry.segment_count(link)):
                entity = f"{link}_S{index}"
                pred_count = geometry.count(link, index, float(pred.freeway_density[link][index]))
                obs_count = geometry.count(link, index, float(obs.freeway_density[link][index]))
                out.append(Sample("cell_count", entity, step, pred_count, obs_count))
                out.append(Sample("cell_speed", entity, step,
                                  float(pred.freeway_speed[link][index]),
                                  float(obs.freeway_speed[link][index])))
            pred_speed, pred_total = _link_speed(pred, geometry, link)
            obs_speed, obs_total = _link_speed(obs, geometry, link)
            out.append(Sample("link_count", link, step, pred_total, obs_total))
            out.append(Sample("link_speed", link, step, pred_speed, obs_speed))
    return out


# ---------------------------------------------------------------------------
# 2. urban / interface 큐 표본 — 관측 커버리지를 함께 센다
# ---------------------------------------------------------------------------


def _observed_urban_entities(detector_mapping: Mapping[str, Any]) -> set[str]:
    """관측 채널이 실제로 값을 공급하는 큐/storage 엔티티 이름 집합.

    매핑의 값 모양이 절마다 다르다 — `ramp_link_to_queues` 는 문자열 리스트,
    `link_to_movements` 는 dict 리스트({movement, origin, ...}), `off_ramp_connectors` 는
    키가 OR_* 이고 값이 커넥터 기하 리스트다. 전부 흡수한다.
    """

    out: set[str] = set()

    def absorb(value: Any) -> None:
        if isinstance(value, str):
            out.add(value)
        elif isinstance(value, Mapping):
            for key in ("movement", "origin", "queue", "storage", "storage_link"):
                if isinstance(value.get(key), str):
                    out.add(value[key])
        elif isinstance(value, (list, tuple)):
            for item in value:
                absorb(item)

    for section in ("ramp_link_to_queues", "link_to_movements", "link_to_origins",
                    "boundary_link_to_queue"):
        for value in (detector_mapping.get(section) or {}).values():
            absorb(value)
    # off-ramp storage 는 OR_* 키에서 이름이 나온다(값은 커넥터 기하다).
    for origin in (detector_mapping.get("off_ramp_connectors") or {}):
        out.add(str(origin))
    out.update(f"{name}_storage" for name in list(out) if name.startswith("OR_"))
    return out


@dataclass
class UrbanCoverage:
    total_entities: int
    observed_entities: int
    observed_names: list[str]
    unobserved_sample: list[str]

    @property
    def ratio(self) -> float:
        return self.observed_entities / self.total_entities if self.total_entities else 0.0


def urban_coverage(net: Any, detector_mapping: Mapping[str, Any]) -> UrbanCoverage:
    observed = _observed_urban_entities(detector_mapping)
    entities = sorted(set(getattr(net, "urban_link_storage_veh", {}) or {})
                      | set(getattr(net, "movement_links", []) or []))
    hit = [name for name in entities if name in observed
           or any(name.startswith(prefix) for prefix in observed)]
    miss = [name for name in entities if name not in hit]
    return UrbanCoverage(
        total_entities=len(entities),
        observed_entities=len(hit),
        observed_names=sorted(hit),
        unobserved_sample=sorted(miss)[:12],
    )


def urban_samples(episode: Episode, net: Any, *, entities: Iterable[str] | None = None,
                  one_step_only: bool = True) -> list[Sample]:
    """도시부 큐 + 링크 storage 점유 오차 표본.

    계약이 'urban **one-step** queue/storage error' 라고 못박았으므로 기본은 k=1 만 쓴다.
    storage 는 TrafficState 에 **잔여 여유**로 저장되므로 점유 = capacity - storage 로
    바꿔 비교한다(leader._urban_halfcap_excess 와 같은 규칙).
    """

    capacity = dict(getattr(net, "urban_link_storage_veh", {}) or {})
    allow = set(entities) if entities is not None else None
    out: list[Sample] = []
    for step, pred, obs in episode.pairs():
        if one_step_only and step != 1:
            continue
        for name, cap in capacity.items():
            if allow is not None and name not in allow:
                continue
            cap_value = max(float(cap), 1.0e-9)
            pred_occ = max(0.0, cap_value - float(pred.urban_link_storage.get(name, cap_value)))
            obs_occ = max(0.0, cap_value - float(obs.urban_link_storage.get(name, cap_value)))
            out.append(Sample("urban_storage", name, step, pred_occ, obs_occ))
        for name in sorted(set(pred.urban_movement_queue) & set(obs.urban_movement_queue)):
            if allow is not None and name not in allow:
                continue
            out.append(Sample("urban_queue", name, step,
                              float(pred.urban_movement_queue[name]),
                              float(obs.urban_movement_queue[name])))
        for name in sorted(set(pred.ramp_queue) & set(obs.ramp_queue)):
            out.append(Sample("interface_ramp_queue", name, step,
                              float(pred.ramp_queue[name]), float(obs.ramp_queue[name])))
    return out


# ---------------------------------------------------------------------------
# 3. 집계
# ---------------------------------------------------------------------------


def aggregate(samples: Sequence[Sample], level: str, *, step: int | None = None) -> dict[str, Any]:
    subset = [s for s in samples if s.level == level and (step is None or s.step == step)]
    if not subset:
        return {"sample_count": 0, "mae": None, "mape": None, "mean_observed": None,
                "rmse": None, "bias": None}
    errors = [s.abs_error for s in subset]
    apes = [s.ape for s in subset if s.ape is not None]
    return {
        "sample_count": len(subset),
        "entity_count": len({s.entity for s in subset}),
        "mae": _mean(errors),
        "rmse": math.sqrt(_mean([e * e for e in errors])),
        "bias": _mean([s.predicted - s.observed for s in subset]),
        "mape": _mean(apes),
        "mape_sample_count": len(apes),
        "mean_observed": _mean([abs(s.observed) for s in subset]),
    }


def count_threshold(stats: Mapping[str, Any], thresholds: Mapping[str, float]) -> float | None:
    """max(5 veh, 10 % of mean observed count) — 집계 수준별로 다시 계산한다."""

    mean_observed = stats.get("mean_observed")
    if mean_observed is None:
        return None
    return max(float(thresholds["cell_count_mae_floor_veh"]),
               float(thresholds["cell_count_mae_ratio"]) * float(mean_observed))


# ---------------------------------------------------------------------------
# 4. G5 리포트
# ---------------------------------------------------------------------------


def evaluate_g5(
    episodes: Sequence[Episode],
    *,
    net: Any,
    detector_mapping: Mapping[str, Any],
    thresholds: Mapping[str, float] | None = None,
    persistence_episodes: Sequence[Episode] | None = None,
    label: str = "",
) -> dict[str, Any]:
    """Episode 묶음에서 G5 지표와 게이트 판정을 만든다."""

    limits = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        limits.update(thresholds)

    freeway: list[Sample] = []
    urban: list[Sample] = []
    coverage = urban_coverage(net, detector_mapping)
    observed_urban = set(coverage.observed_names)
    for episode in episodes:
        freeway.extend(freeway_samples(episode))
        urban.extend(urban_samples(episode, net, entities=observed_urban or None))

    horizons = sorted({e.horizon for e in episodes})
    steps = sorted({s.step for s in freeway})

    by_level = {level: aggregate(freeway, level) for level in
                ("cell_count", "cell_speed", "link_count", "link_speed")}
    by_level_step = {
        level: {str(step): aggregate(freeway, level, step=step) for step in steps}
        for level in ("cell_count", "cell_speed", "link_count", "link_speed")
    }
    urban_levels = {level: aggregate(urban, level) for level in
                    ("urban_storage", "urban_queue", "interface_ramp_queue")}

    # urban 상대오차 — 관측 평균 대비. 관측 규모가 0 에 가까우면 정의되지 않는다.
    urban_rel: dict[str, float | None] = {}
    for level, stats in urban_levels.items():
        mean_observed = stats.get("mean_observed")
        mae = stats.get("mae")
        urban_rel[level] = (mae / mean_observed) if (mae is not None and mean_observed and
                                                     mean_observed > 1.0e-9) else None

    urban_evaluable = coverage.ratio >= 1.0 - 1.0e-9
    urban_note = (
        "" if urban_evaluable else
        f"관측 채널이 도시부 엔티티 {coverage.total_entities}개 중 "
        f"{coverage.observed_entities}개만 덮는다(coverage={coverage.ratio:.3f}). "
        "connector-local 관측에는 도시부 교차로 링크가 없어 계약 urban 항을 잴 수 없다."
    )

    cell_count_stats = by_level["cell_count"]
    link_count_stats = by_level["link_count"]
    criteria = [
        _criterion("freeway_mean_speed_mape_cell", by_level["cell_speed"]["mape"], "<=",
                   limits["freeway_mean_speed_mape_max"],
                   evaluated=bool(by_level["cell_speed"]["sample_count"]),
                   note="셀(세그먼트) 수준 — 더 엄격한 독법"),
        _criterion("freeway_mean_speed_mape_link", by_level["link_speed"]["mape"], "<=",
                   limits["freeway_mean_speed_mape_max"],
                   evaluated=bool(by_level["link_speed"]["sample_count"]),
                   note="링크 수준 — 계약 문구의 자연스러운 독법"),
        _criterion("cell_count_mae", cell_count_stats["mae"], "<=",
                   count_threshold(cell_count_stats, limits),
                   evaluated=bool(cell_count_stats["sample_count"]),
                   note="계약이 'cell'로 명시한 판정 수준"),
        _criterion("link_count_mae", link_count_stats["mae"], "<=",
                   count_threshold(link_count_stats, limits),
                   evaluated=bool(link_count_stats["sample_count"]),
                   note="참고 — 링크 수준"),
    ]
    urban_criterion_initial = _criterion(
        "urban_one_step_queue_storage_error", urban_rel.get("urban_storage"), "<=",
        limits["urban_queue_error_initial_max"], evaluated=urban_evaluable, note=urban_note)
    urban_criterion_promotion = _criterion(
        "urban_one_step_queue_storage_error", urban_rel.get("urban_storage"), "<=",
        limits["urban_queue_error_promotion_max"], evaluated=urban_evaluable, note=urban_note)

    initial = criteria + [urban_criterion_initial]
    promotion = criteria + [urban_criterion_promotion]

    report: dict[str, Any] = {
        "schema_version": "vissim-gates-g5-report/v1",
        "label": label,
        "protocol": "teacher_forced_rolling_origin",
        "episode_count": len(episodes),
        "horizons_steps": horizons,
        "interval_sec": episodes[0].interval_sec if episodes else None,
        "horizon_sec": [h * episodes[0].interval_sec for h in horizons] if episodes else [],
        "thresholds": limits,
        "geometry_note": "count = rho x L x n, L/n 은 관측 state JSON 기하를 양쪽에 공통 적용",
        "aggregate": by_level,
        "by_horizon_step": by_level_step,
        "urban": {
            "coverage": {
                "total_entities": coverage.total_entities,
                "observed_entities": coverage.observed_entities,
                "ratio": coverage.ratio,
                "observed_names": coverage.observed_names,
                "unobserved_sample": coverage.unobserved_sample,
            },
            "levels": urban_levels,
            "relative_error": urban_rel,
            "evaluable": urban_evaluable,
            "note": urban_note,
        },
        "gates": {
            "g5_initial": {"verdict": _gate(initial), "criteria": initial},
            "g5_promotion": {"verdict": _gate(promotion), "criteria": promotion},
        },
    }

    if persistence_episodes:
        persistence: list[Sample] = []
        for episode in persistence_episodes:
            persistence.extend(freeway_samples(episode))
        baseline = {level: aggregate(persistence, level) for level in
                    ("cell_count", "cell_speed", "link_count", "link_speed")}
        skill = {}
        for level, stats in baseline.items():
            model_mae = by_level[level]["mae"]
            base_mae = stats["mae"]
            skill[level] = (1.0 - model_mae / base_mae) if (model_mae is not None and base_mae
                                                            and base_mae > 1.0e-9) else None
        report["persistence_baseline"] = {
            "aggregate": baseline,
            "skill_score": skill,
            "note": "skill = 1 - MAE_model / MAE_persistence. 양수면 모델이 Delta=0 보다 낫다.",
        }
    return report
