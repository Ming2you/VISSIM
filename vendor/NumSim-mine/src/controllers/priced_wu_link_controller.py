# -*- coding: utf-8 -*-
"""Wu 충실 팔로워를 그대로 쓰되 player 입도를 링크 단위로 고정한 가격 Stackelberg 팔.

무엇을 하는 파일인가
--------------------
`StackelbergWuMeteredController`(가격 4채널 + λ_P/λ_UF)와 `WuFaithfulFollower`(Wu 2022
§IV-D 충실 Jacobi 분산 팔로워)를 **그대로** 쓴다. 바꾸는 것은 한 줄이다.

    segment_agents = False        freeway agent 를 세그먼트 16개가 아니라 링크 2개로

이게 전부인 이유는 wu 팔로워가 이미 우리가 원하는 player 구조를 기본값으로 갖기 때문이다.

    urban_agents   = list(cfg.network.signals)         17개 (SC1 … SC1005)
    freeway_agents = list(cfg.network.freeway_links)    2개 (FW_W · FW_E)
    segment_agents = False                              ← 기본이 링크 단위

`build_pstack_flagship_controller` 가 `segment_agents = True` 로 켜서 세그먼트로 쪼개고
있었을 뿐이다. 그래서 "player 를 우리 구조로" 는 그 스위치를 끄는 것으로 끝난다.

**plant 모델은 안 바뀐다.** `freeway_segments_per_link = 8` · `ramps = 4` 가 그대로라
METANET 롤아웃은 여전히 2링크 x 8세그먼트 = 16셀 + 램프 4개를 굴린다. 바뀌는 것은
"누가 어느 레버를 소유하고 어느 셀을 보는가" 뿐이다. 링크 agent 는 VSL 1 + 램프 2 =
액션 3개를 정확히 소유한다 — 세그먼트 8개가 VSL 하나를 두고 경합하던 구조가 사라진다.

2026-08-20 개정 — 초판(333줄)에서 덜어낸 것
-------------------------------------------
초판은 `DistributedCoordinator` 를 베이스로 삼아 가격 오라클 3개·λ_P 듀얼·neighbor
결합항을 직접 구현했다. **그건 요청받은 것이 아니었다** — 요청은 "wu 구조를 홀드하고
player 만" 이었는데 초판은 리더의 가격 기구만 보존하고 팔로워의 GNE 를 분산 코디네이터
것으로 바꿔놨다(순수 Jacobi 대 블록 Gauss-Seidel, 결합변수 해상도 4키 대 48키).
확인해 보니 직접 구현한 것도 전부 불필요하거나 열등했다.

  가격 오라클 3개   wu 에 7개가 이미 있다(green·metering·vsl·offset·교차 2종·λ_P).
  λ_P 듀얼          wu 의 `_lambda_np_update` + `use_dual_np`(기본 True)가 이미 한다.
                    λ_UF 도 있다(`wu_faithful_nuf_coordination_mode`, 기본 "equality").
  neighbor 결합항   램프 저수지가 차기 전 상류 교차로 비용을 매끄럽게 계상하려던 휴리스틱.
                    (a) 문턱은 물리적으로 옳다 — 저수지에 공간이 있는 동안 차량은 램프에
                        대기하고 그건 이미 `link_ramp_queue` 로 계상된다. 빠진 질량이 아니었다.
                    (b) wu 는 그 회계를 substep 마다 FIFO 이월로 돌려 분산 판의 종말 1회
                        추정보다 정교하다(`count_blocked_ramp_inflow`, 기본 True).
                    (c) 근시 병리는 wu 의 `follower_terminal_cost_enabled`(기본 OFF)가
                        Q^2/2R 삼각 배수 tail 로 더 잘 다룬다 — far 의 램프 항과 같은 형태다.
                    그래서 넣지 않는다. 필요해지면 (c) 를 켜는 게 먼저다.

`AgentSpec.neighbors`(분산 코디네이터의 죽은 필드) 이야기도 여기서는 해당 없다 — wu 는
`_coupling` 으로 램프↔교차로를 직접 주고받는다(`u_on_{ramp}` · `arr_{signal}_{phase}` ·
freeway→urban 은 `_last_offramp_flow`).

무엇을 켜는가
-------------
가격 플래그는 어댑터의 `build_priced_wu_link_controller` 가 세운다. flagship 과 같은
운영점(green·metering·vsl·offset ON, 교차가격 OFF)을 쓰되 `segment_agents` 만 다르다.
"""
from __future__ import annotations

from typing import Dict, List, Mapping, Optional

from src.controllers.rollout_endpoint import evaluate_price_point
from src.controllers.stackelberg_wu_metered import StackelbergWuMeteredController
from src.controllers.wu_faithful_follower import WuFaithfulFollower
from src.models.state import (
    MODEL_PHASES,
    ControlAction,
    ExperimentConfig,
    TrafficState,
    _project_to_budget,
    phase_key,
)
from src.models.urban_queue_model import movement_specs


class LinkAgentWuFollower(WuFaithfulFollower):
    """Wu 충실 팔로워 그대로. freeway agent 입도만 링크 단위로 고정한다.

    `segment_agents` 는 wu 의 기본값도 False 지만 여기서 명시적으로 못박는다 —
    `build_pstack_flagship_controller` 가 True 로 켜는 값이라 "안 켰으니 False 일 것" 에
    기대면 빌더가 바뀔 때 조용히 뒤집힌다.
    """

    def __init__(self, cfg: ExperimentConfig):
        super().__init__(cfg)
        self.segment_agents = False


    # ================= 현시별 가격 (2026-08-20) =================
    #
    # 왜 필요한가. 기존 green 가격은 `p1` 축 하나다 — `set_signal_green` 이 p1 을 δ 흔들면
    # 나머지 현시가 **현재 비율대로** 함께 움직이므로, g_ext 는 편미분이 아니라 그 광선을
    # 따라간 방향미분이다. 2현시면 p2 = total - p1 이라 광선이 유일해 완전하지만, 4현시면
    # 총합 고정 단체(simplex)의 자유도가 3인데 그중 **1방향만** 가격이 붙는다.
    #
    # 그게 문제인 이유는 한 신호의 현시들이 서로 다른 종류의 movement 를 먹이기 때문이다.
    # 실측(core17legs4b): 17 SC 중 **14개**가 현시별 movement 종류가 다르고, 특히
    #
    #     SC1001   p3 off_ramp 6개 · p4 off_ramp 2개 · p1/p2 없음
    #     SC1004   p3 off_ramp 8개 · p4 off_ramp 2개 · p1/p2 없음
    #
    # 이 둘은 freeway agent 의 이웃 교차로다. p3 에 녹색을 주는 것과 p2 에 주는 것은 망
    # 외부효과가 근본적으로 다른데, p1 축 가격은 나머지에서 **비율대로** 걷어오므로 정작
    # 중요한 현시를 다른 현시와 섞어 희석한다.
    #
    # 가격 형태. 총합이 고정이라 절대 가격이 아니라 **교환 가격**이어야 한다. 현시 i 에
    # +δ 를 주고 나머지 live 현시에서 δ/(n-1) 씩 걷는 방향 d_i 를 잡고 그 방향미분을 g_i 로
    # 둔다. 팔로워는 `Σ_i g_i · (p_i - ref_i)` 를 더하는데, 총합 고정이라
    # `Σ(p_i - ref_i) = 0` 이므로 g 에 상수를 더해도 값이 안 변한다 — 게이지가 자동으로
    # 고정되어 사영이 필요 없다.
    signal_phase_price: Optional[Dict[str, Dict[str, float]]] = None
    signal_phase_price_ref: Optional[Dict[str, Dict[str, float]]] = None
    signal_phase_price_weight: float = 1.0

    def phase_shape_local_cost(
        self,
        signal: str,
        phases: Mapping[str, float],
        state: TrafficState,
    ) -> float:
        """현시 벡터 하나의 국소 큐 TTS [veh*h]. 가격항 제외.

        `UrbanFollower._urban_stage2_signal_cost` 와 같은 큐 배수 모형이되 p1 스칼라가 아니라
        **명시적 현시 벡터**를 받는다. 교환 후보를 채점하려면 그 프리미티브가 필요하다.
        """
        net = self.cfg.network
        specs = movement_specs(self.cfg)
        horizon = max(1, int(self.cfg.mpc.horizon_steps))
        dt_h = float(self.cfg.simulation.T_c_h)
        q: Dict[str, float] = {}
        sat: Dict[str, float] = {}
        for pid in MODEL_PHASES:
            movements = [m for m, s in specs.items() if s.get("phase") == phase_key(signal, pid)]
            q[pid] = sum(max(0.0, float(state.urban_movement_queue.get(m, 0.0))) for m in movements)
            sat[pid] = max(len(movements) * float(net.movement_capacity_veh_h), 1.0e-9)
        cost = 0.0
        for _ in range(horizon):
            for pid in MODEL_PHASES:
                service = (float(phases.get(pid, 0.0)) / max(net.cycle_length, 1.0e-9)) * sat[pid] * dt_h
                q[pid] = max(0.0, q[pid] - service)
            cost += sum(q.values()) * dt_h
        return float(cost)

    def _phase_exchange_candidates(self, signal: str, base: Mapping[str, float], step: float):
        """총합을 보존하는 쌍교환 후보 — (i 에서 step 빼서 j 에 준다)."""
        net = self.cfg.network
        live = [pid for pid in net.signal_live_phases(signal) if float(base.get(pid, 0.0)) > 0.0]
        lo, hi = float(net.green_min), float(net.green_max)
        out = []
        for i in live:
            for j in live:
                if i == j:
                    continue
                cand = dict(base)
                cand[i] = float(base[i]) - step
                cand[j] = float(base[j]) + step
                if cand[i] < lo - 1.0e-9 or cand[j] > hi + 1.0e-9:
                    continue
                out.append(cand)
        return out

    def apply_phase_price_refinement(self, control: ControlAction, state: TrafficState) -> int:
        """가격이 붙은 방향으로만 현시를 재배분한다. 총합·주기는 불변.

        `p1` 축 탐색(기존)이 끝난 뒤에 돈다. 시드가 그 결과이고 개선될 때만 교체하므로
        같은 목적함수 아래에서 기존 답보다 나빠지지 않는다. 가격이 없으면 즉시 반환한다
        (= 비트동일).
        """
        prices = self.signal_phase_price
        if not prices:
            return 0
        refs = self.signal_phase_price_ref or {}
        weight = float(self.signal_phase_price_weight)
        net = self.cfg.network
        steps = tuple(getattr(self.cfg.mpc, "phase_price_exchange_steps_sec", (6.0, 2.0)))
        improved = 0
        for signal, price in prices.items():
            ref = refs.get(signal) or {}
            base = {pid: float(control.green_times.get(phase_key(signal, pid), 0.0))
                    for pid in MODEL_PHASES}

            def scored(vec: Mapping[str, float]) -> float:
                local = self.phase_shape_local_cost(signal, vec, state)
                ext = sum(
                    float(price.get(pid, 0.0)) * (float(vec.get(pid, 0.0)) - float(ref.get(pid, 0.0)))
                    for pid in MODEL_PHASES
                )
                return local + weight * ext

            best, best_obj = base, scored(base)
            for step in steps:
                for cand in self._phase_exchange_candidates(signal, best, float(step)):
                    obj = scored(cand)
                    if obj < best_obj - 1.0e-12:
                        best, best_obj = cand, obj
            if best is not base:
                for pid, value in best.items():
                    key = phase_key(signal, pid)
                    if key in control.green_times:
                        control.green_times[key] = float(value)
                improved += 1
        control.diagnostics["wu_phase_price_signals_refined"] = float(improved)
        control.diagnostics["wu_phase_price_signals_priced"] = float(len(prices))
        return improved

    def solve(self, state, leader, demand, previous_control=None, leader_incumbent_obj=None):
        import numpy as _np

        result = (
            super().solve(state, leader, demand, previous_control)
            if leader_incumbent_obj is None
            else super().solve(state, leader, demand, previous_control, leader_incumbent_obj)
        )
        if self.signal_phase_price:
            self.apply_phase_price_refinement(result.control, state)
        return result


class PricedWuLinkStackelbergController(StackelbergWuMeteredController):
    """가격 리더 그대로 + 링크 단위 player.

    `StackelbergWuMeteredController` 가 "`_make_follower_solver` 만 오버라이드하는 thin
    서브클래스" 로 설계돼 있어(그 파일 독스트링) 가격 계산·하달·GNE 반복을 한 줄도
    건드리지 않는다.
    """

    # 현시별 교환 가격 (2026-08-20). 기본 꺼짐 = 비트동일.
    #
    # **비용 경고.** 소스가 `_maybe_refresh_signal_prices` 의 98.4% 가 전역 롤아웃이라고
    # 적어 놨다(stackelberg_wu_metered.py:29). 지금은 신호당 2회(lo/hi)인데 여기에
    # 신호당 live 현시 수만큼이 더 붙는다 — 기준 1 + Σn_live ≈ 1 + 17x4 = 69 롤아웃이
    # 기존 34 에 **추가**된다. 리더에서 제일 비싼 자리를 약 3배로 만든다.
    phase_price_enabled: bool = False
    phase_price_delta_sec: float = 6.0
    phase_price_weight: float = 1.0

    def _make_follower_solver(self, cfg: ExperimentConfig):
        return LinkAgentWuFollower(cfg)

    def _phase_vector(self, control: ControlAction, signal: str) -> Dict[str, float]:
        return {pid: float(control.green_times.get(phase_key(signal, pid), 0.0))
                for pid in MODEL_PHASES}

    def _phase_direction(
        self, signal: str, base: Mapping[str, float], target: str, delta: float,
    ) -> Optional[Dict[str, float]]:
        """현시 `target` 에 +δ, 나머지 live 에서 δ/(n-1) 씩 — 총합 보존 + 박스 사영.

        총합을 보존해야 하는 이유는 유효녹색 총량이 신호마다 고정이기 때문이다. 안 지키면
        가격이 "재배분" 이 아니라 "총량 증감" 을 재게 되어 p1 축 가격과 중복된다.
        """
        net = self.cfg.network
        live = [pid for pid in net.signal_live_phases(signal) if float(base.get(pid, 0.0)) > 0.0]
        if target not in live or len(live) < 2:
            return None
        share = float(delta) / float(len(live) - 1)
        raw = {pid: float(base.get(pid, 0.0)) for pid in MODEL_PHASES}
        raw[target] += float(delta)
        for pid in live:
            if pid != target:
                raw[pid] -= share
        rest = [pid for pid in live]
        total = sum(float(base.get(pid, 0.0)) for pid in live)
        projected = _project_to_budget(
            [raw[pid] for pid in rest], total, float(net.green_min), float(net.green_max),
        )
        out = {pid: 0.0 for pid in MODEL_PHASES}
        for pid, value in zip(rest, projected):
            out[pid] = float(value)
        return out

    def _global_ttt_with_phases(
        self,
        state: TrafficState,
        previous: ControlAction,
        forecast: List[DemandStep],
        signal: str,
        phases: Optional[Mapping[str, float]],
    ) -> float:
        """그 신호의 현시 벡터만 바꾼 control 로 전역 롤아웃.

        `evaluate_price_point` 는 schedule 이 비면 넘긴 control 을 그대로 쓴다
        (`rollout_endpoint.py:129`). 그래서 `green` 레버(p1 전용)를 확장하지 않고도
        임의 현시 벡터를 평가할 수 있다 — vendor 의 레버 종류를 안 건드린다.
        """
        ctrl = previous
        if phases is not None:
            ctrl = previous.copy()
            ctrl.green_times = dict(previous.green_times)
            for pid, value in phases.items():
                key = phase_key(signal, pid)
                if key in ctrl.green_times:
                    ctrl.green_times[key] = float(value)
        point = evaluate_price_point(
            state, ctrl, forecast, (),
            self._rollout_spec(score_mode="price", barrier=True),
        )
        return float(point.objective)

    def _refresh_phase_prices(
        self, state: TrafficState, forecast: List[DemandStep], previous: ControlAction,
    ) -> None:
        """g_i = (전역 방향미분) - (국소 방향미분) = 현시 i 로의 재배분이 갖는 외부효과.

        기존 p1 축 가격과 같은 규약이다 — 국소분을 빼서 **팔로워가 이미 보는 몫**을 제거한다.
        빼지 않으면 팔로워가 자기 비용을 두 번 센다.
        """
        follower = self.nash_solver
        if not isinstance(follower, LinkAgentWuFollower):
            return
        net = self.cfg.network
        delta = float(self.phase_price_delta_sec)
        base_ttt = self._global_ttt_with_phases(state, previous, forecast, "", None)
        prices: Dict[str, Dict[str, float]] = {}
        refs: Dict[str, Dict[str, float]] = {}
        rollouts = 1
        for signal in net.signals:
            base = self._phase_vector(previous, signal)
            live = [pid for pid in net.signal_live_phases(signal) if base.get(pid, 0.0) > 0.0]
            if len(live) < 3:
                # 2현시 이하는 p1 축 가격이 이미 완전하다 — 자유도가 1뿐이다.
                continue
            base_local = follower.phase_shape_local_cost(signal, base, state)
            g: Dict[str, float] = {}
            for pid in live:
                moved = self._phase_direction(signal, base, pid, delta)
                if moved is None:
                    continue
                ttt = self._global_ttt_with_phases(state, previous, forecast, signal, moved)
                rollouts += 1
                local = follower.phase_shape_local_cost(signal, moved, state)
                # 척도 보정 (n-1)/n. 방향 d_i = e_i - (1/(n-1))*sum_{j!=i} e_j 로 재면
                #   d_i - d_j = (n/(n-1)) * (e_i - e_j)
                # 이라 g_i - g_j 가 순수 교환 미분의 n/(n-1) 배가 된다. 팔로워는 순수
                # 교환(step 을 i 에서 빼 j 에 준다)으로 움직이므로 그대로 쓰면 가격항이
                # 참값보다 n/(n-1) 배 크다 — 4현시 4/3, 3현시 3/2 로 **현시 수마다 다르다**.
                # 한 신호 안에서는 상수배라 argmin 이 안 바뀌지만, 국소비용 대비 가격항의
                # 상대 가중치가 신호마다 12.5% 어긋난다. 여기서 참값으로 되돌린다.
                scale = float(len(live) - 1) / float(len(live))
                raw_g = ((ttt - base_ttt) - (local - base_local)) / max(delta, 1.0e-9)
                g[pid] = float(raw_g * scale)
            if g:
                prices[signal] = g
                refs[signal] = base
        follower.signal_phase_price = prices or None
        follower.signal_phase_price_ref = refs or None
        follower.signal_phase_price_weight = float(self.phase_price_weight)
        self._phase_price_rollouts = rollouts
        self._phase_price_signals = len(prices)

    def _maybe_refresh_signal_prices(
        self,
        state: TrafficState,
        forecast: List[DemandStep],
        previous: ControlAction,
        force: bool = False,
    ) -> None:
        super()._maybe_refresh_signal_prices(state, forecast, previous, force=force)
        if bool(self.phase_price_enabled):
            self._refresh_phase_prices(state, forecast, previous)
