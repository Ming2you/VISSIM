# G5/G6 공용 rollout 원시자 — 한 앵커에서 한 액션을 H 스텝 굴린 예측열과 같은 시각의 관측열을 짝지어 담는다.
"""공용 하네스의 심장.

G5 와 G6 는 **같은 rollout 객체**(`Episode`)를 본다. 차이는 무엇을 스윕하느냐뿐이다.

    G5 : 앵커 시각 t 를 스윕한다(rolling-origin). 액션은 그 런이 실제로 집행한 것 하나.
         → Episode.pred_states[k] vs Episode.obs_states[k] 의 **상태 오차**를 본다.
    G6 : 앵커 시각 t 를 고정하고 후보 액션 a 를 스윕한다.
         → J(Episode.pred_states) vs J(Episode.obs_states) 의 **순위 일치**를 본다.

한 번 굴려 둘 다 낸다는 임무 요구가 이 모듈에 형식으로 박혀 있다. `build_episode` 는
G5 도 G6 도 같은 함수를 호출하며, 어느 게이트를 재는지 알지 못한다.

★ 지평 — 운영 실측값 control_interval=60 s 를 쓴다. H=1/3/5 = 60/180/300 s.
   (이전 측정이 계약 문서 기본값 180 s 를 잘못 가져와 3배 긴 지평을 쟀다.)
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
G6_DIR = HERE.parent / "g6"
if str(G6_DIR) not in sys.path:
    sys.path.insert(0, str(G6_DIR))

import g6_core as core  # noqa: E402

VISSIM_ROOT = core.VISSIM_ROOT
STATE_RE = re.compile(r"^state_(\d{6})\.json$")
ACTION_RE = re.compile(r"^action_(\d{6})\.json$")


# ---------------------------------------------------------------------------
# 1. 런 디렉터리 → 관측 시계열
# ---------------------------------------------------------------------------


def state_series(decision_dir: Path) -> dict[int, Path]:
    """decisions_* 디렉터리의 state_XXXXXX.json 을 {sim_sec: path} 로 모은다."""

    out: dict[int, Path] = {}
    for child in Path(decision_dir).iterdir():
        match = STATE_RE.match(child.name)
        if match:
            out[int(match.group(1))] = child
    return dict(sorted(out.items()))


def action_series(decision_dir: Path) -> dict[int, Path]:
    out: dict[int, Path] = {}
    for child in Path(decision_dir).iterdir():
        match = ACTION_RE.match(child.name)
        if match:
            out[int(match.group(1))] = child
    return dict(sorted(out.items()))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def control_interval_of(state_json: Mapping[str, Any]) -> int:
    return int(round(float(state_json.get("control_interval_sec", 60.0))))


# ---------------------------------------------------------------------------
# 2. 기하 — 관측 state JSON 에서 셀 길이/차로를 그대로 가져온다
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CellGeometry:
    """셀 count 환산에 쓸 기하. **관측 state JSON 이 정본**이다.

    모델 cfg 의 `freeway_segment_length_km`(1.346925)와 관측 링크별 실측
    (FW_E 1.346639 / FW_W 1.347212)이 0.02 % 다르다. count = rho x L x n 에서
    L 을 양쪽에 **같은 값**으로 써야 이 기하 차이가 예측오차로 새지 않는다.
    그래서 관측 기하를 양쪽에 공통 적용하고, 그 사실을 리포트에 남긴다.
    """

    length_km: dict[str, list[float]]
    lanes: dict[str, list[float]]

    def count(self, link: str, index: int, density_veh_km_lane: float) -> float:
        return float(density_veh_km_lane) * self.length_km[link][index] * self.lanes[link][index]

    @property
    def links(self) -> list[str]:
        return sorted(self.length_km)

    def segment_count(self, link: str) -> int:
        return len(self.length_km[link])


def geometry_from_state_json(state_json: Mapping[str, Any]) -> CellGeometry:
    segments = state_json.get("freeway_segments") or {}
    length_km: dict[str, list[float]] = {}
    lanes: dict[str, list[float]] = {}
    for link, cells in segments.items():
        length_km[str(link)] = [float(cell.get("length_km", 0.0)) for cell in cells]
        lanes[str(link)] = [float(cell.get("lanes", 0.0)) for cell in cells]
    return CellGeometry(length_km=length_km, lanes=lanes)


# ---------------------------------------------------------------------------
# 3. 앵커 — 실측으로 상태를 고정한 한 시점
# ---------------------------------------------------------------------------


@dataclass
class Anchor:
    """teacher-forced 앵커. 매 제어시점 실측 (rho, v, 큐) 로 상태를 다시 잡는다."""

    t_sec: int
    state_json: dict[str, Any]
    state: Any                  # 모델 TrafficState (관측 투영)
    geometry: CellGeometry
    forecast: list[Any]         # 앵커 관측에서 뽑은 수요 예보
    source_path: Path


def build_anchor(rt: core.G6Runtime, path: Path, t_sec: int, horizon: int) -> Anchor:
    state_json = read_json(path)
    return Anchor(
        t_sec=int(t_sec),
        state_json=state_json,
        state=core.project_observed_state(rt, state_json),
        geometry=geometry_from_state_json(state_json),
        forecast=core.build_forecast(rt, state_json, int(horizon)),
        source_path=Path(path),
    )


# ---------------------------------------------------------------------------
# 4. 액션 — (a) 실제 집행된 것, (b) 후보 집합
# ---------------------------------------------------------------------------


def executed_control(rt: core.G6Runtime, decision_dir: Path, t_sec: int):
    """그 시각에 VISSIM 이 실제로 집행한 ControlAction 을 복원한다.

    어댑터의 `control_from_json` 을 그대로 쓴다 — 하네스가 액션 스키마를 다시
    해석하지 않는다. teacher-forced G5 는 반드시 **집행된 액션**으로 굴려야 한다.
    """

    path = Path(decision_dir) / f"action_{int(t_sec):06d}.json"
    return core.ad.control_from_json(path, rt.cfg, rt.ControlAction)


def candidate_control(rt: core.G6Runtime, candidate: core.Candidate):
    return core.build_control(rt.cfg, rt.ControlAction, candidate)


# ---------------------------------------------------------------------------
# 5. Episode — 공용 rollout 산출물
# ---------------------------------------------------------------------------


@dataclass
class Episode:
    """한 앵커 x 한 액션 x 지평 H 의 rollout 결과.

    `pred_states[k-1]` 과 `obs_states[k-1]` 은 **같은 시각** t0 + k x T_c 다.
    obs_states 가 짧으면(관측 결손) 그만큼만 채워지고 `missing_sec` 에 기록된다.
    """

    anchor_t_sec: int
    horizon: int
    interval_sec: int
    action_id: str
    action_payload: dict[str, Any]
    pred_states: list[Any]
    obs_states: list[Any]
    missing_sec: list[int] = field(default_factory=list)
    geometry: CellGeometry | None = None
    model_runtime_sec: float = 0.0

    @property
    def complete(self) -> bool:
        return not self.missing_sec and len(self.obs_states) == len(self.pred_states) == self.horizon

    def pairs(self) -> list[tuple[int, Any, Any]]:
        """[(step_k, pred_state, obs_state), ...] — 관측이 있는 스텝만."""

        out = []
        for index in range(min(len(self.pred_states), len(self.obs_states))):
            out.append((index + 1, self.pred_states[index], self.obs_states[index]))
        return out


def build_episode(
    rt: core.G6Runtime,
    anchor: Anchor,
    control,
    horizon: int,
    *,
    observed: Mapping[int, Path] | None,
    action_id: str,
    action_payload: Mapping[str, Any] | None = None,
    persistence: bool = False,
) -> Episode:
    """★ 공용 rollout. G5 도 G6 도 이 함수 하나만 호출한다.

    `persistence=True` 면 모델을 굴리지 않고 앵커 상태를 H 번 복사한다(Delta=0 대조군).
    """

    import time

    interval = int(round(float(rt.cfg.simulation.control_interval)))
    started = time.perf_counter()
    if persistence:
        pred = [anchor.state.copy() for _ in range(int(horizon))]
        for step, state in enumerate(pred, start=1):
            state.time_sec = float(anchor.t_sec + interval * step)
    else:
        pred = core.model_rollout_states(rt, anchor.state, control, anchor.forecast, int(horizon))
    model_runtime = time.perf_counter() - started

    obs: list[Any] = []
    missing: list[int] = []
    if observed is not None:
        for step in range(1, int(horizon) + 1):
            sim_sec = anchor.t_sec + interval * step
            path = observed.get(sim_sec)
            if path is None:
                missing.append(sim_sec)
                continue
            obs.append(core.project_observed_state(rt, read_json(path)))

    return Episode(
        anchor_t_sec=anchor.t_sec,
        horizon=int(horizon),
        interval_sec=interval,
        action_id=action_id,
        action_payload=dict(action_payload or {}),
        pred_states=pred,
        obs_states=obs,
        missing_sec=missing,
        geometry=anchor.geometry,
        model_runtime_sec=model_runtime,
    )


def build_free_run_episode(
    rt: core.G6Runtime,
    anchor: Anchor,
    control,
    steps: int,
    *,
    observed: Mapping[int, Path],
    action_id: str,
) -> Episode:
    """참고 지표 (B) — 개루프 자유주행. 앵커 한 번, 이후 재앵커 없이 끝까지 전진.

    본 시험이 아니다. MPC 는 매 결정마다 실측으로 재앵커하므로 (A) rolling-origin 이
    옳은 프로토콜이고, 이 함수의 산출은 별도 섹션에만 기록한다.
    """

    long_forecast = core.build_forecast(rt, anchor.state_json, int(steps))
    saved, anchor.forecast = anchor.forecast, long_forecast
    try:
        return build_episode(
            rt, anchor, control, int(steps),
            observed=observed, action_id=action_id,
            action_payload={"mode": "open_loop_free_run"},
        )
    finally:
        anchor.forecast = saved


# ---------------------------------------------------------------------------
# 6. 계층(holdout) 라벨 — seed / demand profile / control policy
# ---------------------------------------------------------------------------

_SEED_RE = re.compile(r"seed(\d+)")
_SCALE_RE = re.compile(r"(scale\d+|fw\d+)")
_POLICY_TOKENS = (
    "pstack_flagship", "stackelberg", "no_control", "no-control", "fixed_time", "fixedtime",
)


@dataclass(frozen=True)
class Stratum:
    """계약 §11 G5 가 요구한 holdout 3축. 디렉터리 이름에서 뽑는다."""

    seed: str
    demand: str
    policy: str

    def key(self) -> str:
        return f"seed={self.seed}|demand={self.demand}|policy={self.policy}"


def stratum_of(decision_dir: Path) -> Stratum:
    name = Path(decision_dir).name
    seed = _SEED_RE.search(name)
    demand = _SCALE_RE.search(name)
    policy = next((token for token in _POLICY_TOKENS if token in name), "unknown")
    for candidate in core.ACTIVE_CANDIDATE_SET:
        if candidate.candidate_id in name:
            policy = candidate.candidate_id
            break
    return Stratum(
        seed=seed.group(1) if seed else "unknown",
        demand=demand.group(1) if demand else "unknown",
        policy=policy.replace("-", "_"),
    )


def holdout_split(strata: Sequence[Stratum], axis: str) -> dict[str, list[Stratum]]:
    """축(seed/demand/policy) 값별로 계층을 묶는다. fold 분리의 근거표."""

    out: dict[str, list[Stratum]] = {}
    for stratum in strata:
        out.setdefault(getattr(stratum, axis), []).append(stratum)
    return out
