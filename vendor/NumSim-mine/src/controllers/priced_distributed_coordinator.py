# -*- coding: utf-8 -*-
"""가격 리더(wu) + 분산 player(17 도시 · 2 고속) 하이브리드.

무엇을 섞는가
-------------
저장소에 컨트롤러가 두 벌 있고 각자 반쪽씩 갖고 있다.

  StackelbergMPCController + DistributedCoordinator   player 17+16, **가격 없음**
  StackelbergWuMeteredController + WuFaithfulFollower 가격 4채널 + λ_P/λ_UF, **player 구조 없음**

여기서는 **리더를 그대로 두고 팔로워만 바꾼다.** `StackelbergWuMeteredController` 자체가
"`_make_follower_solver` 만 오버라이드하는 thin 서브클래스" 로 설계돼 있어서(그 파일 독스트링),
가격 계산·GNE 반복·하달 방식을 한 줄도 안 건드리고 player 구조만 갈아끼울 수 있다.

가격이 팔로워 종류에 의존하지 않는 이유는 계약이 속성/메서드 수준이기 때문이다.

    리더:  레버를 ±δ 흔들고 -> follower.local_*_costs() 로 국소 비용을 물어본다
           -> g_ext = g_i - (cost_hi - cost_lo)/2δ        (유한차분, 팔로워 내부 불문)
           -> follower.<price 속성> 에 기록
    팔로워: cost += w · g_ext[lever] · (lever - ref[lever])   + trust region

두 스케일을 **둘 다** 넣는다 (2026-08-20 사용자 설계)
---------------------------------------------------
  neighbor 결합   최인접 교차로로 퍼지는 **국소** 영향
  price           그 너머 망 전반에 걸치는 **전역** 외부효과

베이스 `DistributedCoordinator` 는 국소 쪽이 문턱형이라 반쪽만 담고 있었다.

    blocked_to_urban = max(0, ramp_start + incoming - release - capacity)
    urban_tts        = 0.5 * blocked_to_urban * horizon_h

즉 **램프 저수지가 넘치기 전까지 미터링의 도시 비용이 정확히 0** 이다. 실제로는 조이는
순간부터 상류 교차로가 차량을 물고 있어야 한다. λ_UF 주석의 "metering 이 절벽 레버" 와
같은 현상이다. 여기서는 점유율에 비례하는 매끄러운 항을 **문턱 항과 함께** 더한다.

그리고 `AgentSpec.neighbors` 는 베이스에서 **죽은 필드**였다 — 최인접 교차로를 선언해 두는데
해석부가 안 읽고 `tests/test_constraints.py:696` 만 읽는다. 여기서 처음으로 그 선언을 쓴다.

무엇을 안 넣었나 (실제로 안 도는 가지는 만들지 않는다)
-----------------------------------------------------
  offset 가격            `offset_price_enabled` 를 켜야 하고 오라클이 96줄이다. 이 팔은 끈다.
  교차가격 2종           flagship 빌더에서도 False 다(green x offset, vsl x meter).
  price_far/price_hinge  flagship 기본 False. 2026-07-09 ablation 이 "노이즈 증폭" 으로 되돌렸다.

리더가 각 `local_*_costs` 호출을 자기 enable 플래그로 감싸므로(1161~1175행), 끈 채널의
오라클은 **호출되지 않는다** — 없어도 안전하다.
"""
from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Sequence

from src.controllers.distributed_coordinator import DistributedCoordinator
from src.controllers.stackelberg_wu_metered import StackelbergWuMeteredController
from src.models.demand import DemandStep
from src.models.metanet import effective_lane_profile
from src.models.state import (
    MODEL_PHASES,
    ControlAction,
    ExperimentConfig,
    TrafficState,
    phase_key,
)
from src.models.urban_queue_model import movement_specs


class PricedDistributedCoordinator(DistributedCoordinator):
    """가격을 받는 분산 팔로워. 베이스의 GNE 반복·agent 분할을 그대로 물려받는다."""

    def __init__(self, cfg: ExperimentConfig):
        super().__init__(cfg)
        # ---------- 리더가 써 넣는 가격 (없으면 완전 휴면 = 베이스와 비트동일) ----------
        self.signal_marginal_price: Optional[Dict[str, float]] = None
        self.signal_marginal_price_ref: Dict[str, float] = {}
        self.signal_marginal_price_weight: float = 1.0
        self.signal_marginal_price_trust_sec: Optional[float] = None

        self.metering_marginal_price: Optional[Dict[str, float]] = None
        self.metering_marginal_price_ref: Dict[str, float] = {}
        self.metering_marginal_price_weight: float = 1.0
        self.metering_marginal_price_trust_frac: Optional[float] = None
        self.metering_release_certified: Optional[Dict[str, bool]] = None

        self.vsl_marginal_price: Optional[Dict[str, float]] = None
        self.vsl_marginal_price_ref: Dict[str, float] = {}
        self.vsl_marginal_price_weight: float = 1.0
        self.vsl_marginal_price_trust_kmh: Optional[float] = None

        # ---------- N_P 듀얼 (λ_P). 리더가 _lambda_np_update 로 굴린다 ----------
        self.np_price_enabled: bool = True
        self.lambda_np_step_gain: float = 0.01
        self.lambda_np_cap: float = 10.0

        # ---------- neighbor 결합 가중치 ----------
        # 0.0 = 베이스와 비트동일(문턱 항만). 켜면 저수지 점유율에 비례해 최인접 교차로
        # 대기비용을 **넘치기 전부터** 계상한다.
        self.neighbor_coupling_weight: float = float(
            getattr(cfg.mpc, "ramp_neighbor_coupling_weight", 0.0)
        )
        # 어댑터 호환(six_controller 가 n_agents 를 셀 때 읽는다).
        self.urban_agents_ids = list(cfg.network.signals)

    # ================= neighbor 결합: 램프 <-> 최인접 교차로 =================

    def _neighbor_urban_queue_veh(self, agent, state: TrafficState) -> float:
        """이 freeway agent 의 최인접 교차로가 물고 있는 on-ramp 접근 대기 [veh].

        `AgentSpec.neighbors` 는 `build_agent_specs` 가 `urban_by_ramp`/`urban_by_offramp`
        로 채운다 — 램프가 붙은 교차로다. 베이스는 이 필드를 안 읽었다.
        """
        if not agent.neighbors:
            return 0.0
        specs = movement_specs(self.cfg)
        owners = {str(n) for n in agent.neighbors}
        total = 0.0
        for movement, spec in specs.items():
            if str(spec.get("kind", "")) != "on_ramp":
                continue
            signal = str(spec.get("intersection", "") or "")
            if signal and f"U_{signal}" in owners:
                total += max(0.0, float(state.urban_movement_queue.get(movement, 0.0)))
        return float(total)

    def _neighbor_coupling_tts(
        self,
        agent,
        state: TrafficState,
        ramp_terminal_veh: float,
        capacity_veh: float,
        horizon_h: float,
    ) -> float:
        """저수지 점유율에 비례하는 최인접 교차로 대기비용 [veh*h].

        베이스의 `blocked_to_urban` 은 저수지가 **넘친 뒤**에만 값이 생긴다(문턱). 조이기
        시작한 순간부터 상류 교차로가 차량을 물고 있으므로, 점유율 r = terminal/capacity 에
        비례해 이웃 대기를 미리 계상한다. r=1 에서 문턱 항과 매끄럽게 이어진다.
        """
        w = self.neighbor_coupling_weight
        if w <= 0.0:
            return 0.0
        ratio = min(1.0, max(0.0, ramp_terminal_veh / max(capacity_veh, 1.0e-9)))
        return float(w * ratio * self._neighbor_urban_queue_veh(agent, state) * horizon_h)

    def _agent_queue_tts_terms(
        self,
        agent,
        state: TrafficState,
        ramp_metering: Mapping[str, float],
        coupling: Mapping[str, float],
        horizon_h: float,
    ) -> tuple[float, float]:
        """베이스의 문턱 항에 neighbor 결합 항을 더한다."""
        ramp_tts, urban_tts = super()._agent_queue_tts_terms(
            agent, state, ramp_metering, coupling, horizon_h
        )
        if self.neighbor_coupling_weight <= 0.0 or not agent.ramps:
            return ramp_tts, urban_tts
        net = self.cfg.network
        ramp_start = sum(max(0.0, state.ramp_queue.get(r, 0.0)) for r in agent.ramps)
        incoming = sum(
            max(0.0, float(coupling.get(f"u_on_{r}", 0.0))) * horizon_h for r in agent.ramps
        )
        release = sum(max(0.0, ramp_metering.get(r, 0.0)) * horizon_h for r in agent.ramps)
        capacity = sum(net.ramp_queue_cap(r) for r in agent.ramps)
        terminal = min(capacity, max(0.0, ramp_start + incoming - release))
        return ramp_tts, float(
            urban_tts
            + self._neighbor_coupling_tts(agent, state, terminal, capacity, horizon_h)
        )

    # ================= 가격 오라클: 리더가 유한차분으로 부른다 =================
    #
    # 규약 셋(wu 판과 동일):
    #   1. 후보를 팔로워 자신이 쓰는 것과 **같은 경로**로 채점한다
    #   2. 채점 중 가격을 일시 비활성 — d_local 은 비가격 own-TTS 기울기여야 한다
    #      (가격이 들어가면 g_ext = g_i - d_local 이 자기 가격을 되빼는 순환)
    #   3. 영속 상태를 건드리지 않는다

    def _phase_queue_and_sat(self, signal: str, state: TrafficState):
        """`UrbanFollower._select_stage2_controls` 와 같은 방식으로 q0/sat 을 만든다."""
        net = self.cfg.network
        specs = movement_specs(self.cfg)
        phase_movements = {
            pid: [m for m, s in specs.items() if s.get("phase") == phase_key(signal, pid)]
            for pid in MODEL_PHASES
        }
        q0 = {
            pid: sum(
                max(0.0, float(state.urban_movement_queue.get(m, 0.0)))
                for m in phase_movements[pid]
            )
            for pid in MODEL_PHASES
        }
        sat = {
            pid: max(len(phase_movements[pid]) * net.movement_capacity_veh_h, 1.0e-9)
            for pid in MODEL_PHASES
        }
        return q0, sat

    def local_green_costs(
        self,
        requests: Mapping[str, Sequence[float]],
        state: TrafficState,
        control: ControlAction,
        demand: DemandStep,
    ) -> Dict[str, List[float]]:
        """신호별 green-p1 후보의 국소 own-TTS [veh*h]. 가격항 제외."""
        saved = self.signal_marginal_price
        self.signal_marginal_price = None
        try:
            out: Dict[str, List[float]] = {}
            for signal, candidates in requests.items():
                q0, sat = self._phase_queue_and_sat(str(signal), state)
                offset = float(control.offsets.get(str(signal), 0.0))
                out[str(signal)] = [
                    float(self.urban_follower._urban_stage2_signal_cost(
                        str(signal), float(p1), offset, control, q0, sat,
                    ))
                    for p1 in candidates
                ]
            return out
        finally:
            self.signal_marginal_price = saved

    def _freeway_agent_for_ramp(self, ramp: str):
        for agent in self.freeway_agents:
            if ramp in agent.ramps:
                return agent
        return None

    def local_metering_costs(
        self,
        requests: Mapping[str, Sequence[float]],
        state: TrafficState,
        control: ControlAction,
        demand: DemandStep,
    ) -> Dict[str, List[float]]:
        """ramp별 metering 후보의 freeway-agent 국소 own-TTS [veh*h]. 가격항 제외."""
        saved = self.metering_marginal_price
        self.metering_marginal_price = None
        try:
            net = self.cfg.network
            horizon_h = self.cfg.simulation.T_c_h * max(1, self.cfg.mpc.horizon_steps)
            lane_profile, _ = effective_lane_profile(state, self.cfg, demand)
            forecast = [demand]
            upper = {r: float(net.ramp_capacity_veh_h[r]) for r in net.ramps}
            out: Dict[str, List[float]] = {}
            for ramp, candidates in requests.items():
                agent = self._freeway_agent_for_ramp(str(ramp))
                if agent is None:
                    out[str(ramp)] = [0.0 for _ in candidates]
                    continue
                costs: List[float] = []
                for rate in candidates:
                    metering = dict(control.ramp_metering)
                    metering[str(ramp)] = float(rate)
                    veh_tts, _excess, _peak, _merge, _rel = self._candidate_freeway_tts_terms(
                        agent, state, metering, upper, forecast, lane_profile,
                    )
                    ramp_tts, urban_tts = self._agent_queue_tts_terms(
                        agent, state, metering, {}, horizon_h,
                    )
                    costs.append(float(veh_tts + ramp_tts + urban_tts))
                out[str(ramp)] = costs
            return out
        finally:
            self.metering_marginal_price = saved

    def local_vsl_costs(
        self,
        requests: Mapping[str, Sequence[Sequence[float]]],
        state: TrafficState,
        control: ControlAction,
        demand: DemandStep,
    ) -> Dict[str, List[float]]:
        """link별 VSL 벡터 후보의 freeway-agent 국소 own-TTS [veh*h]. 가격항 제외.

        VSL 은 링크당 스칼라 하나다(`control.vsl[link]`). 벡터가 오면 대표값으로 첫 원소를
        쓴다 — 세그먼트별 VSL 레버가 없으므로 벡터의 나머지는 표현할 수단이 없다.
        """
        saved = self.vsl_marginal_price
        self.vsl_marginal_price = None
        try:
            net = self.cfg.network
            horizon_h = self.cfg.simulation.T_c_h * max(1, self.cfg.mpc.horizon_steps)
            lane_profile, _ = effective_lane_profile(state, self.cfg, demand)
            forecast = [demand]
            upper = {r: float(net.ramp_capacity_veh_h[r]) for r in net.ramps}
            out: Dict[str, List[float]] = {}
            for link, candidates in requests.items():
                agent = next((a for a in self.freeway_agents if a.link == str(link)), None)
                if agent is None:
                    out[str(link)] = [0.0 for _ in candidates]
                    continue
                costs: List[float] = []
                for vector in candidates:
                    seq = list(vector) if isinstance(vector, (list, tuple)) else [float(vector)]
                    trial = control.copy()
                    trial.vsl = dict(control.vsl)
                    trial.vsl[str(link)] = float(seq[0]) if seq else float(net.v_free)
                    veh_tts, _excess, _peak, _merge, _rel = self._candidate_freeway_tts_terms(
                        agent, state, trial.ramp_metering, upper, forecast, lane_profile,
                    )
                    ramp_tts, urban_tts = self._agent_queue_tts_terms(
                        agent, state, trial.ramp_metering, {}, horizon_h,
                    )
                    costs.append(float(veh_tts + ramp_tts + urban_tts))
                out[str(link)] = costs
            return out
        finally:
            self.vsl_marginal_price = saved

    # ================= N_P 듀얼 =================

    def _lambda_np_update(self, lambda_p: float, sum_nin: float, target: float) -> float:
        """λ_P 적분 갱신. 비음수·상한 clip — 유입 억제 방향의 단방향 가격이다."""
        if not self.np_price_enabled:
            return 0.0
        return float(
            min(
                self.lambda_np_cap,
                max(0.0, float(lambda_p) + self.lambda_np_step_gain * (float(sum_nin) - float(target))),
            )
        )


class PricedDistributedStackelbergController(StackelbergWuMeteredController):
    """가격 리더는 그대로, 팔로워만 분산 player 로.

    `StackelbergWuMeteredController` 의 가격 계산·GNE 반복·하달 경로를 한 줄도 안 건드린다.
    """

    def _make_follower_solver(self, cfg: ExperimentConfig):
        return PricedDistributedCoordinator(cfg)
