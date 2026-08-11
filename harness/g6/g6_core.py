# 계약 §11 G6(순위 정합) 측정 코어 — 후보 액션 집합, 목적함수 범함수, 모델 rollout, VISSIM 관측 투영.
"""G6 core.

핵심 아이디어는 하나다. **목적함수를 상태궤적의 순수 범함수로 정의하고, 그 하나의
함수를 두 궤적에 그대로 적용한다.**

  J_model(a)  = J( 모델이 a 로 rollout 한 상태열 , a )
  J_vissim(a) = J( VISSIM 이 a 를 집행해 실제로 만든 상태열을 관측 투영한 것 , a )

두 값의 차이는 오직 상태궤적에서 온다. 목적함수 구현이 한 개이므로 "다른 목적함수를
비교했다"는 오염이 원천적으로 불가능하다.

목적함수 선택 근거는 `objective_from_states` docstring 에 적었다.
"""

from __future__ import annotations

import copy
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

VISSIM_ROOT = Path(__file__).resolve().parents[2]
ADAPTER_DIR = VISSIM_ROOT / "evaluation" / "controllers"
if str(ADAPTER_DIR) not in sys.path:
    sys.path.insert(0, str(ADAPTER_DIR))

import vissim_stackelberg_adapter as ad  # noqa: E402

DEFAULT_MAPPING = VISSIM_ROOT / "evaluation/real_world_modi_control/control_mapping.json"
DEFAULT_DETECTOR_MAPPING = VISSIM_ROOT / "evaluation/real_world_modi_control/detector_local_mapping.json"
DEFAULT_CALIBRATION = VISSIM_ROOT / "evaluation/calibration/real_world_modi_control_v2_fdrefit_20260802.json"
DEFAULT_TUNING = VISSIM_ROOT / "evaluation/configs/real_world_modi_pstack_flagship_segvsl_fdrefit_20260802.json"


# ---------------------------------------------------------------------------
# 1. 후보 액션 집합
# ---------------------------------------------------------------------------
#
# 계약 §11 G6 은 "forced green/offset/VSL/ramp perturbation 포함"을 요구한다.
# 어댑터의 `_diagnostic_fixed_control` 계열은 네 채널(vsl / d·f ramp / major·minor
# green / offset)을 **전부 명시**하므로 후보끼리 채널 정의가 어긋나지 않는다.
#
# 반대로 이름에 `-original` 또는 `-only` 가 붙은 변형은 어댑터가
# `metadata["suppress_signal_rows"]=1` 을 찍어 **VISSIM 신호를 원래 .sig 프로그램에
# 맡긴다**. 모델 쪽 ControlAction 은 green 57/57 을 그대로 들고 있으므로 모델과
# 플랜트의 액션이 서로 다르다. G6 후보로 쓰면 순위가 아니라 채널 불일치를 재는 셈이라
# 아래 집합에서 **의도적으로 제외**했다(`EXCLUDED_VARIANTS` 참조).

@dataclass(frozen=True)
class Candidate:
    """후보 액션 하나. `variant` 는 어댑터 --controller 값과 1:1 대응한다."""

    candidate_id: str
    variant: str
    axis: str
    vsl_kph: float
    d_ramp_vph: float
    f_ramp_vph: float
    major_green_sec: float
    minor_green_sec: float
    offset_sec: float


# d/f ramp 기본값 1800.0 은 `_diagnostic_fixed_control` 이 cfg.network.ramp_capacity_veh_h
# 평균으로 채우는 값(실세계 캘리브레이션에서 4개 램프 모두 1800)이다.
_RAMP_OPEN = 1800.0

CANDIDATE_SET_V1: tuple[Candidate, ...] = (
    Candidate("c00_anchor", "diagnostic-fixed57", "anchor", 120.0, _RAMP_OPEN, _RAMP_OPEN, 57.0, 57.0, 0.0),
    Candidate("c01_vsl110", "diagnostic-vsl110", "vsl", 110.0, _RAMP_OPEN, _RAMP_OPEN, 57.0, 57.0, 0.0),
    Candidate("c02_vsl100", "diagnostic-vsl100", "vsl", 100.0, _RAMP_OPEN, _RAMP_OPEN, 57.0, 57.0, 0.0),
    Candidate("c03_vsl80", "diagnostic-vsl80", "vsl", 80.0, _RAMP_OPEN, _RAMP_OPEN, 57.0, 57.0, 0.0),
    Candidate("c10_rampd1364", "diagnostic-ramp-d1364", "ramp", 120.0, 1364.0, _RAMP_OPEN, 57.0, 57.0, 0.0),
    Candidate("c11_rampd1253", "diagnostic-ramp-d1253", "ramp", 120.0, 1253.0, _RAMP_OPEN, 57.0, 57.0, 0.0),
    Candidate("c12_rampd691", "diagnostic-ramp-hold", "ramp", 120.0, 691.0, _RAMP_OPEN, 57.0, 57.0, 0.0),
    Candidate("c20_major75", "diagnostic-signal-major", "green", 120.0, _RAMP_OPEN, _RAMP_OPEN, 75.0, 25.0, 0.0),
    Candidate("c21_minor75", "diagnostic-signal-minor", "green", 120.0, _RAMP_OPEN, _RAMP_OPEN, 25.0, 75.0, 0.0),
    Candidate("c22_major62", "diagnostic-signal-major62", "green", 120.0, _RAMP_OPEN, _RAMP_OPEN, 62.0, 52.0, 0.0),
    Candidate("c23_minor62", "diagnostic-signal-minor62", "green", 120.0, _RAMP_OPEN, _RAMP_OPEN, 52.0, 62.0, 0.0),
    Candidate("c30_offset30", "diagnostic-signal-offset30", "offset", 120.0, _RAMP_OPEN, _RAMP_OPEN, 57.0, 57.0, 30.0),
    Candidate("c40_combined_strong", "diagnostic-combined-strong", "combined", 80.0, 691.0, _RAMP_OPEN, 75.0, 25.0, 0.0),
    Candidate("c41_combined_extreme", "diagnostic-combined-extreme", "combined", 60.0, 360.0, 360.0, 90.0, 5.0, 0.0),
)

# V2 — 실측 기반 재설계 (2026-08-03).
#
# V1 의 문제 두 가지를 실측으로 확인하고 고쳤다.
#
# (1) VSL 상단이 무의미했다. 실측 속도 분포는 p50=96.4 / p90=115.8 / max=123.6 km/h 이고
#     속도>120 표본이 1.23 % 뿐이다. 혼잡 구간(t0=2700)에서는 앵커 평균속도가 75.3 km/h 라
#     VSL 110 과 100 이 거의 구속하지 않았고, 실제로 두 후보의 **관측 목적함수가 정확히 같았다**
#     (c01_vsl110 vs c02_vsl100 차이 0.0000 %). 순위를 매길 수 없는 쌍을 채점에 넣고 있었다.
#     -> 선택지를 [100, 90, 80, 70, 60, 50] 으로 바꾼다. 100 이 상단(표본의 43 % 에서 구속),
#        50 이 혼잡 하단(관측 v최저 19.0 km/h)을 덮는다.
#
# (2) 신호 후보에 중복이 있었다. c22_major62 와 c23_minor62 의 관측 목적함수도 정확히 같았다.
#     -> 62/52 쌍을 제거하고 75/25 쌍만 남긴다.
#
# 램프 후보는 그대로 둔다. 관측 J 폭이 H5 에서 102.55 로 구분은 되기 때문이다
# (다만 미터율이 실제 램프 수요를 구속하는지는 별도 확인이 필요하다).
CANDIDATE_SET_V2: tuple[Candidate, ...] = (
    Candidate("c00_anchor", "diagnostic-fixed57", "anchor", 120.0, _RAMP_OPEN, _RAMP_OPEN, 57.0, 57.0, 0.0),
    Candidate("c01_vsl100", "diagnostic-vsl100", "vsl", 100.0, _RAMP_OPEN, _RAMP_OPEN, 57.0, 57.0, 0.0),
    Candidate("c02_vsl90", "diagnostic-vsl90", "vsl", 90.0, _RAMP_OPEN, _RAMP_OPEN, 57.0, 57.0, 0.0),
    Candidate("c03_vsl80", "diagnostic-vsl80", "vsl", 80.0, _RAMP_OPEN, _RAMP_OPEN, 57.0, 57.0, 0.0),
    Candidate("c04_vsl70", "diagnostic-vsl70", "vsl", 70.0, _RAMP_OPEN, _RAMP_OPEN, 57.0, 57.0, 0.0),
    Candidate("c05_vsl60", "diagnostic-vsl60", "vsl", 60.0, _RAMP_OPEN, _RAMP_OPEN, 57.0, 57.0, 0.0),
    Candidate("c06_vsl50", "diagnostic-vsl50", "vsl", 50.0, _RAMP_OPEN, _RAMP_OPEN, 57.0, 57.0, 0.0),
    Candidate("c10_rampd1364", "diagnostic-ramp-d1364", "ramp", 120.0, 1364.0, _RAMP_OPEN, 57.0, 57.0, 0.0),
    Candidate("c11_rampd1253", "diagnostic-ramp-d1253", "ramp", 120.0, 1253.0, _RAMP_OPEN, 57.0, 57.0, 0.0),
    Candidate("c12_rampd691", "diagnostic-ramp-hold", "ramp", 120.0, 691.0, _RAMP_OPEN, 57.0, 57.0, 0.0),
    # 네 그룹 전부를 구동하고, 미터율을 실제 램프 수요 아래로 내린 후보 (2026-08-04).
    # 위 c10/c11/c12 는 d_ramp 만 지정해 R_D_W 그룹(미터 2개)에만 걸렸고 그 미터율마저
    # 램프 수요보다 높아 구속하지 않았다. 그룹 미터율은 물리 미터 2개에 절반씩 갈리므로
    # 아래 1000/800/600 은 미터당 500/400/300 이다.
    # 실측 램프 수요: 10646=816 10681=741 10480=668 10490=619 10644=560 10482=492 10639=354 10484=307
    Candidate("c13_rampall500", "diagnostic-ramp-all500", "ramp", 120.0, 1000.0, 1000.0, 57.0, 57.0, 0.0),
    Candidate("c14_rampall400", "diagnostic-ramp-all400", "ramp", 120.0, 800.0, 800.0, 57.0, 57.0, 0.0),
    Candidate("c15_rampall300", "diagnostic-ramp-all300", "ramp", 120.0, 600.0, 600.0, 57.0, 57.0, 0.0),
    Candidate("c20_major75", "diagnostic-signal-major", "green", 120.0, _RAMP_OPEN, _RAMP_OPEN, 75.0, 25.0, 0.0),
    Candidate("c21_minor75", "diagnostic-signal-minor", "green", 120.0, _RAMP_OPEN, _RAMP_OPEN, 25.0, 75.0, 0.0),
    Candidate("c30_offset30", "diagnostic-signal-offset30", "offset", 120.0, _RAMP_OPEN, _RAMP_OPEN, 57.0, 57.0, 30.0),
    Candidate("c40_combined_strong", "diagnostic-combined-strong", "combined", 80.0, 691.0, _RAMP_OPEN, 75.0, 25.0, 0.0),
    Candidate("c41_combined_extreme", "diagnostic-combined-extreme", "combined", 60.0, 360.0, 360.0, 90.0, 5.0, 0.0),
)

# 기본 후보집합. 환경변수 G6_CANDIDATE_SET=v1 로 되돌릴 수 있다.
ACTIVE_CANDIDATE_SET: tuple[Candidate, ...] = (
    CANDIDATE_SET_V1 if os.environ.get("G6_CANDIDATE_SET", "v2").lower() == "v1" else CANDIDATE_SET_V2
)

# 신호 채널이 모델과 플랜트에서 어긋나므로 G6 후보로 쓰면 안 되는 변형들.
EXCLUDED_VARIANTS: dict[str, str] = {
    "diagnostic-vsl60-only": "suppress_signal_rows=1 (VISSIM native signal, model green=57)",
    "diagnostic-vsl80-only": "suppress_signal_rows=1",
    "diagnostic-vsl80-original": "suppress_signal_rows=1",
    "diagnostic-ramp-all735-original": "suppress_signal_rows=1",
    "diagnostic-ramp-all360-original": "suppress_signal_rows=1",
    "no-control": "액션 채널이 열려 있지 않아 fixed-action 비교 대상이 아니다",
}


def candidate_by_id(candidate_id: str) -> Candidate:
    for item in ACTIVE_CANDIDATE_SET:
        if item.candidate_id == candidate_id:
            return item
    raise KeyError(candidate_id)


def build_control(cfg, ControlAction, cand: Candidate):
    """후보를 모델 ControlAction 으로 실체화한다. 어댑터 생성기를 그대로 호출한다."""

    return ad._diagnostic_fixed_control(
        cfg,
        ControlAction,
        vsl_kph=cand.vsl_kph,
        d_ramp_rate_vph=cand.d_ramp_vph,
        f_ramp_rate_vph=cand.f_ramp_vph,
        major_green_sec=cand.major_green_sec,
        minor_green_sec=cand.minor_green_sec,
        offset_sec=cand.offset_sec,
    )


# ---------------------------------------------------------------------------
# 2. 런타임 조립 (어댑터 main() 과 동일 경로)
# ---------------------------------------------------------------------------


@dataclass
class G6Runtime:
    cfg: Any
    score_cfg: Any
    leader: Any
    ControlAction: Any
    TrafficState: Any
    DemandStep: Any
    mapping: dict
    detector_mapping: dict
    calibration: dict
    tuning: dict


def build_runtime(
    state_json: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
    mapping_json: Path = DEFAULT_MAPPING,
    detector_mapping_json: Path = DEFAULT_DETECTOR_MAPPING,
    calibration_json: Path = DEFAULT_CALIBRATION,
    tuning_json: Path = DEFAULT_TUNING,
    mode: str = "fast-smoke",
) -> G6Runtime:
    """어댑터 main() 이 하는 조립을 그대로 재현한다(런타임 패치 포함)."""

    repo_root = Path(repo_root or ad.DEFAULT_REPO_ROOT)
    mapping = json.loads(Path(mapping_json).read_text(encoding="utf-8"))
    detector_mapping = ad.load_optional_json(str(detector_mapping_json))
    calibration = ad.load_optional_json(str(calibration_json))
    tuning = ad.load_optional_json(str(tuning_json))
    calibration_override = tuning.get("calibration_override", {})
    if isinstance(calibration_override, Mapping):
        calibration = ad.deep_update(dict(calibration), calibration_override)

    control_interval = float(state_json.get("control_interval_sec", 60.0))
    sim_period = float(state_json.get("sim_period_sec", max(180.0, control_interval)))
    (_, DemandStep, ControlAction, _EC, TrafficState, _sv) = ad.repo_imports(repo_root)
    local_observation = bool(ad._link_counts_from_local_observation(state_json) and detector_mapping)
    cfg = ad.build_config(
        repo_root,
        control_interval,
        sim_period,
        mode,
        calibration,
        tuning,
        local_observation=local_observation,
        flagship=False,
    )
    ad.install_adapter_calibration_fingerprints(cfg, tuning)
    ad.install_vissim_calibration_runtime_patches(cfg, calibration)
    ad.install_vsl_metanet_rollout_runtime_patch(cfg, tuning)
    if local_observation:
        ad.install_local_observation_runtime_guards()

    from src.controllers.leader import Leader

    # 채점 전용 cfg: objective_mode 를 state_accumulation 으로 고정한다(근거는
    # objective_from_states docstring). 운영 cfg 는 건드리지 않는다.
    score_cfg = copy.deepcopy(cfg)
    score_cfg.leader.objective_mode = "state_accumulation"
    return G6Runtime(
        cfg=cfg,
        score_cfg=score_cfg,
        leader=Leader(score_cfg),
        ControlAction=ControlAction,
        TrafficState=TrafficState,
        DemandStep=DemandStep,
        mapping=mapping,
        detector_mapping=detector_mapping,
        calibration=calibration,
        tuning=tuning,
    )


def project_observed_state(rt: G6Runtime, state_json: Mapping[str, Any]):
    """VISSIM state_XXXXXX.json → 모델 TrafficState. 컨트롤러가 쓰는 관측 경로 그대로."""

    return ad.traffic_state_from_vissim(
        dict(state_json), rt.cfg, rt.TrafficState, rt.detector_mapping, rt.calibration
    )


# ---------------------------------------------------------------------------
# 3. 목적함수 — 상태궤적의 순수 범함수
# ---------------------------------------------------------------------------


def objective_from_states(rt: G6Runtime, states: Sequence[Any], control) -> dict[str, float]:
    """후보 목적함수 J(states, a).

    **무엇을 골랐는가.** 컨트롤러가 후보를 실제로 고를 때 쓰는 값은
    `Leader.objective_terms(...)["leader_total_objective"]` 다
    (`stackelberg_mpc.py:1575` 가 `_LeaderCandidateEvaluation.objective` 에 이 값을
    그대로 넣는다). 그래서 이것을 그대로 쓴다.

    **한 가지만 바꾼다 — base 항.** 운영 기본값 `leader.objective_mode="follower_ttt"`
    에서 base 는 follower Nash 해의 rollout TTT 다. 이것은 상태의 함수가 아니라
    **모델 내부 solve 의 산출물**이라 VISSIM 관측에 대응물이 없다. G6 는 같은 함수를
    두 궤적에 적용해야 하므로 base 를 관측 가능한 등가물인
    `state_accumulation` (= Σ_k [freeway veh + offramp storage + urban veh])로 고정한다.

    두 모드는 **양의 상수배 관계**라 순위를 보존한다. follower_ttt 모드는 base 를
    veh·h 로 두고 모든 벌점에 `accumulation_penalty_scale = T_c_h` 를 곱하며
    (`leader.py:876-878`), state_accumulation 모드는 base 를 veh 로 두고 scale=1.0 을
    쓴다. follower rollout TTT ≈ accumulation × T_c_h 인 한
    J_follower_ttt = T_c_h · J_state_accumulation 이고, T_c_h > 0 이므로 Spearman ρ 와
    pairwise ordering 은 동일하다. 이 가정은 진단값으로 함께 기록해 감사 가능하게 둔다.

    반환은 스칼라 하나가 아니라 항 전체다. 승패가 어느 항에서 갈렸는지 봐야 하기 때문.
    """

    states = list(states)
    terms = rt.leader.objective_terms(
        states,
        control,
        None,               # previous: smoothness 항이 하드 비활성(leader.py:920)이라 미사용
        0.0,                # follower_objective: state_accumulation 모드에서 base 에 미반영
        True,               # nash_converged: 비수렴 벌점은 진단 전용(Spec 4.6)
        0.0,
        0.0,
    )
    T_c_h = float(rt.score_cfg.simulation.T_c_h)
    net = rt.score_cfg.network
    total_veh = sum(
        float(s.total_freeway_vehicles(net))
        + float(s.off_ramp_storage_occupancy_veh(net))
        + float(s.objective_urban_vehicles(net, False))
        for s in states
    )
    out = {str(k): float(v) for k, v in terms.items()}
    out["g6_objective"] = float(terms["leader_total_objective"])
    out["g6_ttt_veh_h"] = float(total_veh * T_c_h)
    out["g6_state_count"] = float(len(states))
    return out


def spillback_flag(rt: G6Runtime, states: Sequence[Any], *, threshold: float = 0.90) -> bool:
    """호라이즌 안에서 spillback 이 한 번이라도 발생했는가.

    urban link storage 는 TrafficState 에 **잔여 여유(veh)** 로 저장된다
    (`leader._urban_halfcap_excess` 가 occupancy = capacity − storage 로 계산한다).
    같은 규칙을 모델 예측 상태열과 VISSIM 관측 투영 상태열에 동일하게 적용한다.
    """

    net = rt.score_cfg.network
    ramp_cap = float(getattr(net, "ramp_queue_max_veh", 0.0) or 0.0)
    for state in states:
        for link, capacity_value in net.urban_link_storage_veh.items():
            capacity = float(capacity_value)
            # 용량 0 인 저류는 판정에서 제외한다.
            #
            # 2026-08-05: 구 격자 유령 저류링크를 용량 0 으로 무력화했더니 여기서
            # max(cap, 1e-9) 가 1e-9 를 깔고, 그 링크의 urban_link_storage 가 0 이면
            # occupancy = 1e-9 - 0 = 1e-9 >= 0.9 x 1e-9 로 **항상 참**이 됐다.
            # 그 결과 g6 spillback 이 72/72 레코드에서 (예측,관측)=(True,True) 가 되어
            # F1 이 0.031 -> 1.000 으로 뛰었다. 개선이 아니라 인공물이었다.
            # 용량이 없는 링크는 넘칠 수도 없으므로 건너뛴다.
            if capacity <= 1.0e-9:
                continue
            occupancy = max(0.0, capacity - float(state.urban_link_storage.get(link, capacity)))
            if occupancy >= threshold * capacity:
                return True
        if ramp_cap > 0.0:
            for value in state.ramp_queue.values():
                if float(value) >= threshold * ramp_cap:
                    return True
    return False


# ---------------------------------------------------------------------------
# 4. 모델 rollout (open-loop, fixed action)
# ---------------------------------------------------------------------------


def model_rollout_states(
    rt: G6Runtime,
    initial_state,
    control,
    forecast: Sequence[Any],
    horizon_steps: int,
) -> list[Any]:
    """초기상태에서 액션을 H 스텝 동안 **고정한 채** 전개한 예측 상태열.

    상류 production rollout endpoint 를 거친다(N7 "우회 호출 0"). endpoint 가 초기상태를
    복사해 전진시키므로 `initial_state` 는 불변이고, 반환 상태열은
    t0+T_c, ..., t0+H·T_c (초기상태 제외) — 관측 쪽과 시각을 맞춘다.

    이동 전 직접 루프와의 수치 동일성 근거(`tests/test_g6_core_rollout_endpoint.py` 가 고정).
      - 수요 — 이동 전 클램프 `forecast[min(step, len-1)]` 를 호출 **전에** 실체화해
        endpoint 의 `forecast[:depth]` 절단과 같은 수요열을 넘긴다. 실 런에서는
        `demand_from_state` 가 정확히 H 개를 내므로 두 규약이 애초에 같지만,
        len(forecast) < H 인 호출이 들어와도 동작이 갈리지 않게 여기서 맞춰 둔다.
      - 액션 — `action_schedule=()` 이면 endpoint 는 previous 를 사본조차 만들지 않고
        그대로 쓴다(`rollout_endpoint.py:122-125`).
      - box-walk — 이동 전 루프에 없던 경로라 `box_walk=False` 로 끈다.
      - 시각 — endpoint 는 `s.time_sec += interval` 로 누적하고 이동 전은
        `t0 + interval*(step+1)` 절대식이었다. 실 런의 t0(정수초)·interval=60.0 에서
        두 식은 비트 동일하다.
    """

    from src.controllers.rollout_endpoint import ObjectiveSpec, evaluate_price_point

    steps = int(horizon_steps)
    demands = [forecast[min(step, len(forecast) - 1)] for step in range(steps)]
    point = evaluate_price_point(
        initial_state,
        control,
        demands,
        (),
        ObjectiveSpec(cfg=rt.cfg, depth_override=steps, box_walk=False),
    )
    return point.states


def build_forecast(rt: G6Runtime, state_json: Mapping[str, Any], horizon_steps: int) -> list[Any]:
    return ad.demand_from_state(
        dict(state_json),
        rt.cfg,
        rt.DemandStep,
        int(horizon_steps),
        rt.calibration,
        rt.detector_mapping,
    )
