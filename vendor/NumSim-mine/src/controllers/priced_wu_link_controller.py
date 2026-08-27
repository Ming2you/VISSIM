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
from src.controllers.stackelberg_wu_metered import (
    _PRICE_WORKER_CTX,
    _adapter_patch_present,
    StackelbergWuMeteredController,
    _price_worker_init,
)
from src.controllers.local_signal_plant import rollout_local_tts_phased
from src.models.demand import DemandStep
from src.controllers.wu_faithful_follower import WuFaithfulFollower
from src.models.state import (
    MODEL_PHASES,
    PRIMARY_PHASE,
    ControlAction,
    ExperimentConfig,
    TrafficState,
    _project_to_budget,
    distribute_phase_green,
    phase_key,
    signal_green_reference,
)
from src.models.urban_queue_model import _urban_step_index, movement_specs


def _price_worker_phase(task):
    """(signal, pid, phases) -> (signal, pid, ttt). 직렬 호출과 인자가 동일하다.

    `stackelberg_wu_metered._price_worker_init` 이 워커당 한 번 컨트롤러·작동점을 고정한
    컨텍스트를 그대로 쓴다 — green 가격 병렬 경로와 같은 규약이라 결과가 같고 수집 순서만
    다르다. 모듈 수준 함수여야 spawn(Windows) 에서 피클된다.
    """
    signal, pid, phases = task
    ctx = _PRICE_WORKER_CTX
    ttt = ctx["ctrl"]._global_ttt_with_phases(  # noqa: SLF001
        ctx["state"], ctx["previous"], ctx["forecast"], signal, phases,
    )
    return signal, pid, float(ttt)


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

    # 정련이 쓸 국소 비용 모형. "drain"(기본) = 기존 큐 배수 모형 → 비트 동일.
    # "phased" = GNE 팔로워가 쓰는 `rollout_local_tts_phased`(도착·스필백·offset 포함).
    #
    # 왜 바꿀 수 있어야 하는가. 정련은 GNE 가 끝난 뒤 green_times 를 **덮어쓴다**
    # (실측: 매 결정 17개 신호 중 평균 13.7개). 그런데 `phase_shape_local_cost` 는
    # 도착도 스필백도 per-movement 용량도 안 본다 — GNE 가 계산한 물리를 버린다.
    # 게다가 sat 을 `len(movements) x movement_capacity_veh_h` 로 잡아 SC1_p1 이
    # 28,000 veh/h 가 된다(실측 통과 2,640 veh/h). 그래서 어떤 큐도 첫 스텝에 비어
    # local 이 항등 0 이 되고, 남는 선형 가격항이 해를 상자 꼭짓점으로 몬다.
    phase_price_local_cost_model: str = "drain"
    # 나머지 현시 배분의 기준. "previous"(기본) = 직전 녹색 비율 → 비트 동일.
    # "pressure" = 현시별 큐 비례.
    green_reference_mode: str = "previous"
    # 정련 반복 횟수 상한. 1 이면 종전과 비트 동일. 개선이 없으면 조기 종료한다.
    phase_price_refine_rounds: int = 1

    def __getstate__(self):
        """가격 워커로 보낼 때 정련 캐시는 빼고 피클한다.

        캐시에는 신호 17개분 플래툰 프로파일(약 25k float)이 들어간다. 워커 작업마다
        직렬화하면 계산보다 전송이 비싸진다. 워커는 정련을 돌지 않으므로 버려도 된다."""
        st = dict(self.__dict__)
        st.pop("_phase_ctx_cache", None)
        return st

    @staticmethod
    def _phase_refine_signature(state, control, demand):
        """ctx 재사용 판정 키. control 이 조금이라도 다르면 coupling 이 달라진다."""
        def _d(m):
            return tuple(sorted((str(k), round(float(v), 9)) for k, v in (m or {}).items()))
        return (
            round(float(getattr(state, "time_sec", 0.0)), 6),
            id(demand),
            _d(getattr(control, "green_times", None)),
            _d(getattr(control, "offsets", None)),
            _d(getattr(control, "vsl", None)),
            _d(getattr(control, "ramp_metering", None)),
        )

    def _phase_refine_context(self, state, control, demand):
        """정련 1회분 공통 셋업. drain 모드거나 demand 가 없으면 None(= 기존 경로).

        결정 1회에 리더가 후보를 여러 번 평가하면서 팔로워 solve 가 반복 호출된다.
        `_coupling`(전 신호 도착 결합) 과 신호별 플래툰 프로파일이 그때마다 다시 계산되면
        정련이 GNE 보다 비싸진다. 입력(state·control·demand)이 같으면 결과도 같으므로
        서명으로 캐시한다 — 같은 입력에 같은 값이라 **비트 동일**이다.
        """
        if str(getattr(self, "phase_price_local_cost_model", "drain")).lower() != "phased":
            return None
        if demand is None:
            return None
        # `solve()` 의 demand 는 단일 DemandStep 일 수도, 예측 리스트일 수도 있다
        # (DistributedCoordinator.solve 와 같은 규약). 첫 스텝이 현재 구간이다.
        # 2026-08-22: 이 정규화를 빠뜨려 첫 스모크가 controller_status=fallback_fixed 로
        # 떨어졌다 — "'list' object has no attribute 'urban_boundary'".
        if not isinstance(demand, DemandStep):
            try:
                seq = list(demand)
            except TypeError:
                return None
            if not seq:
                return None
            demand = seq[0]
        sig = self._phase_refine_signature(state, control, demand)
        cached = getattr(self, "_phase_ctx_cache", None)
        if cached is not None and cached[0] == sig:
            cached[1]["cache_hits"] = int(cached[1].get("cache_hits", 0)) + 1
            return cached[1]
        sim = self.cfg.simulation
        ctrl = ControlAction.uncontrolled(self.cfg)
        ctrl.green_times = dict(control.green_times)
        ctrl.offsets = dict(control.offsets)
        ctrl.vsl = dict(control.vsl)
        ctrl.ramp_metering = dict(control.ramp_metering)
        ctrl.inflow_outflow_allocation = {}
        snapshot = ControlAction(
            ramp_metering=dict(ctrl.ramp_metering), vsl=dict(ctrl.vsl),
            green_times=dict(ctrl.green_times), offsets=dict(ctrl.offsets),
            inflow_outflow_allocation={},
        )
        ctx = {
            "coupling": self._wu._coupling(state, ctrl, demand),
            "s_eff_frozen": self._frozen_s_eff(state),
            "snapshot": snapshot,
            "demand": demand,
            "substeps": max(1, int(self.cfg.mpc.horizon_steps)) * max(1, int(sim.K_cu)),
            "dt_h": float(sim.T_u_h),
            "start_idx": _urban_step_index(state, self.cfg),
            "setups": {},
            "cache_hits": 0,
        }
        self._phase_ctx_cache = (sig, ctx)
        return ctx

    def _phase_refine_signal_setup(self, signal: str, state: TrafficState, ctx):
        """신호 하나의 롤아웃 입력. ego green 에 불변이라 후보마다 다시 안 만든다."""
        setups = ctx.get("setups")
        if setups is not None and signal in setups:
            return setups[signal]
        model = self._local_models.get(signal)
        if model is None or model.has_ramps:
            if setups is not None:
                setups[signal] = None
            return None
        arr_movement = self._per_movement_arrivals(signal, state, ctx["snapshot"], ctx["demand"])
        arr_phase = {
            pid: float(ctx["coupling"].get(f"arr_{phase_key(signal, pid)}", 0.0))
            for pid in MODEL_PHASES
        }
        arr_mv: Dict[str, float] = {}
        for pid in MODEL_PHASES:
            movs = [m for m in model.movements
                    if model.phase_of[m] == pid and model.kind_of[m] != "off_ramp"]
            raw = sum(max(0.0, float(arr_movement.get(m, 0.0))) for m in movs)
            target = max(0.0, arr_phase[pid])
            scale = (target / raw) if raw > 1.0e-12 else 0.0
            for m in movs:
                arr_mv[m] = max(0.0, float(arr_movement.get(m, 0.0))) * scale
        q0 = {m: max(0.0, float(state.urban_movement_queue.get(m, 0.0))) for m in model.movements}
        s_eff0 = {
            model.receiving_of[m]: float(ctx["s_eff_frozen"].get(model.receiving_of[m], 0.0))
            for m in model.movements if model.receiving_of[m]
        }
        arr_by_substep = self._platoon_arrival_profiles(
            signal, state, ctx["snapshot"], ctx["demand"], arr_mv, ctx["substeps"], ctx["start_idx"],
        )
        setup = {"model": model, "q0": q0, "arr": arr_by_substep, "s_eff0": s_eff0}
        if setups is not None:
            setups[signal] = setup
        return setup

    def _phase_local_cost_phased(self, signal, phases, setup, ctx) -> float:
        """GNE 와 **같은** 국소 물리로 현시 벡터를 채점한다."""
        offset = float(ctx["snapshot"].offsets.get(signal, 0.0))
        gf = self._offset_green_fractions_vec(
            signal, phases, offset, ctx["substeps"], ctx["start_idx"],
        )
        return float(rollout_local_tts_phased(
            setup["model"], setup["q0"], setup["arr"], gf, setup["s_eff0"],
            ctx["substeps"], ctx["dt_h"],
        ))

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
        # 신호별 상한. 3현시 141 이면 101 이고, 스칼라 78 을 걸면 그 신호에서
        # 실계획을 재현할 수 없다(2026-08-22).
        lo, hi = float(net.green_min), float(net.signal_green_max(signal))
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

    def apply_phase_price_refinement(self, control: ControlAction, state: TrafficState,
                                     demand=None) -> int:
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
        # phased 모드면 정련도 GNE 와 같은 물리로 채점한다. drain 이면 ctx 가 None 이라
        # 아래 분기가 기존 경로 그대로 — 비트 동일이다.
        ctx = self._phase_refine_context(state, control, demand)
        phased_signals = 0
        refine_rounds_used = 0
        improved = 0
        for signal, price in prices.items():
            ref = refs.get(signal) or {}
            base = {pid: float(control.green_times.get(phase_key(signal, pid), 0.0))
                    for pid in MODEL_PHASES}
            # 정련 **직전**(=GNE 출력) 값을 남긴다. 이게 없으면 커밋된 녹색만 보이고
            # GNE 가 뭘 내놨는지 / 정련이 얼마나 바꿨는지를 가를 수 없다.
            for pid in MODEL_PHASES:
                control.diagnostics[f"wu_pre_refine_{signal}_{pid}"] = float(base.get(pid, 0.0))
            setup = self._phase_refine_signal_setup(signal, state, ctx) if ctx else None
            if setup is not None:
                phased_signals += 1

            def scored(vec: Mapping[str, float], _setup=setup) -> float:
                if _setup is not None:
                    local = self._phase_local_cost_phased(signal, vec, _setup, ctx)
                else:
                    local = self.phase_shape_local_cost(signal, vec, state)
                ext = sum(
                    float(price.get(pid, 0.0)) * (float(vec.get(pid, 0.0)) - float(ref.get(pid, 0.0)))
                    for pid in MODEL_PHASES
                )
                return local + weight * ext

            # 개선이 없을 때까지 반복한다(좌표하강). 목적함수는 이미 TTT 단위다 —
            # local[veh*h] + Σ price[veh*h/s] x Δg[s]. 그런데 지금까지 그 목적함수로
            # 실제 탐색한 범위는 **쌍교환 6초 한 걸음**뿐이고, 나머지 배분은 GNE 의
            # 휴리스틱(직전 녹색 비율)이 정했다. 반복하면 최종 배분을 TTT 가 정한다.
            # rounds=1 이면 종전과 비트 동일.
            best, best_obj = base, scored(base)
            max_rounds = max(1, int(getattr(self, "phase_price_refine_rounds", 1)))
            used = 0
            for _round in range(max_rounds):
                moved = False
                for step in steps:
                    for cand in self._phase_exchange_candidates(signal, best, float(step)):
                        obj = scored(cand)
                        if obj < best_obj - 1.0e-12:
                            best, best_obj = cand, obj
                            moved = True
                used += 1
                if not moved:
                    break
            refine_rounds_used += used
            if best is not base:
                for pid, value in best.items():
                    key = phase_key(signal, pid)
                    if key in control.green_times:
                        control.green_times[key] = float(value)
                improved += 1
        control.diagnostics["wu_phase_price_signals_refined"] = float(improved)
        control.diagnostics["wu_phase_price_local_cost_phased_signals"] = float(phased_signals)
        control.diagnostics["wu_phase_refine_rounds_used"] = float(refine_rounds_used)
        control.diagnostics["wu_green_reference_pressure_signals"] = float(
            len(getattr(self.cfg.network, "phase_pressure_by_signal", {}) or {}))
        pmap = dict(getattr(self.cfg.network, "primary_phase_by_signal", {}) or {})
        if pmap:
            control.diagnostics["wu_primary_by_price_signals"] = float(len(pmap))
            for sig, pid in sorted(pmap.items()):
                control.diagnostics[f"wu_primary_phase_{sig}"] = float(int(str(pid)[1:]))
        if ctx is not None:
            control.diagnostics["wu_phase_refine_ctx_cache_hits"] = float(ctx.get("cache_hits", 0))
        control.diagnostics["wu_phase_price_signals_priced"] = float(len(prices))
        # 가격 g 와 실제 이동량을 내보낸다 — 이게 없으면 "재배분됐다" 만 알고 **얼마나
        # 값어치가 있었는지** 를 모른다. 경량화(대상 신호를 좁힐지, 채널을 끌지)는 이
        # 분포로만 판정할 수 있다. 2026-08-20 첫 런에서 이걸 빠뜨려 재실행했다.
        for signal, price in prices.items():
            ref = refs.get(signal) or {}
            for pid, value in price.items():
                control.diagnostics[f"wu_phase_price_{signal}_{pid}"] = float(value)
            moved = sum(
                abs(float(control.green_times.get(phase_key(signal, pid), 0.0))
                    - float(ref.get(pid, 0.0)))
                for pid in MODEL_PHASES
            )
            control.diagnostics[f"wu_phase_price_moved_sec_{signal}"] = float(moved)
            spread = (max(price.values()) - min(price.values())) if price else 0.0
            control.diagnostics[f"wu_phase_price_spread_{signal}"] = float(spread)
        return improved

    def _refresh_phase_pressure(self, state) -> int:
        """신호별 현시 압력(큐 합)을 심는다. `distribute_phase_green` 의 나머지 배분이
        직전 녹색 비율 대신 이걸 쓴다.

        왜. 나머지 배분이 직전 녹색이면 "직전에 낮았으면 계속 낮게" 라는 자기강화 고리가
        된다. 실측(map4d SC5): p3 가격이 SC5 에서 1위인 결정 14개 **전부**에서 p3 가
        하한 22.7 에 묶였다(고정계획 47). 큐 비례로 나누면 축을 고정하지 않고도 큐가 큰
        현시가 몫을 받는다 — 주현시 교체(prim)와 달리 축을 안 바꾸므로 reference
        재해석 비용이 없다.

        팔로워는 이미 현시별 압력을 계산해 두고도 "주현시 대 나머지 **합**" 으로만
        쓴다(wu_faithful_follower:729). 여기서는 그 값을 나머지 배분에도 쓴다.
        """
        net = self.cfg.network
        press: Dict[str, Dict[str, float]] = {}
        for movement, spec in (net.urban_movements or {}).items():
            phase = str(spec.get("phase", ""))
            if not phase:
                continue
            signal, _, pid = phase.rpartition("_")
            if not signal or pid not in MODEL_PHASES:
                continue
            q = max(0.0, float(state.urban_movement_queue.get(movement, 0.0)))
            press.setdefault(signal, {p: 0.0 for p in MODEL_PHASES})[pid] += q
        # 전부 0 인 신호는 뺀다 — 남기면 균등이 아니라 0 가중치가 되어 상자 사영이 엉킨다.
        press = {k: v for k, v in press.items() if sum(v.values()) > 1.0e-9}
        setattr(net, "phase_pressure_by_signal", press)
        return len(press)

    # ============ 현시가격을 GNE 안으로 (2026-08-27, 사용자 지시) ============
    #
    # 종전 구조의 문제. `apply_phase_price_refinement` 는 `solve()` 가 GNE 를 **다 끝낸
    # 뒤에** 돌았다. 그래서 매 결정 이 순서가 반복됐다.
    #
    #     1. GNE      신호당 1차원(p1)만 최적화 → 나머지 현시는 직전 비율로 뭉개짐
    #     2. 정련      현시가격으로 6초씩 교환해 되돌리려 함 (실측 녹색 L1 360~576초)
    #     3. 다음 결정  GNE 가 1번을 다시 해서 2번 결과를 지움
    #
    # 이 파일 492행 주석이 그 증상을 이미 적어 놓았다 — "가격은 옳게 가리키는데 그
    # 방향으로 갈 대역폭이 없다. 정련의 6초 교환만이 되돌릴 수 있는데 GNE 가 매 결정
    # 비율을 다시 뭉갠다." Stackelberg 에서 리더 가격은 팔로워의 **최적화 문제 안에**
    # 들어가야 균형 자체가 옮겨간다. 밖에서 밀면 다음 반복에 복원된다 — 고정점이 아니라
    # 매 스텝 이탈 후 복원이다. 리더 해와 PFO 해의 realized TTT 차가 0.0001 인 이유다.
    #
    # 그래서 국소 최선응답 안에서 p1 축 해를 시드로 삼아 현시 벡터를 좌표하강한다.
    # 채점은 정련과 **같은 함수**를 쓴다 — local[veh*h] + Σ price·Δg. 같은 목적함수를
    # 두 곳에서 다르게 쓰던 것을 하나로 합치는 것이다.
    #
    # 비용. 상류 주석(이 파일 480행)이 경고한 대로 롤아웃이 는다. 다만 여기서 부르는
    # 것은 전역 롤아웃이 아니라 국소 채점기(`_phase_local_cost_phased` / drain)라
    # 신호당 (현시쌍 x step 수) 회의 국소 평가다. GNE 반복마다 돈다.
    #
    # 기본 꺼짐 = 비트 동일. `urban.phase_price.in_gne: true` 로 켠다.
    phase_price_in_gne: bool = False
    phase_price_in_gne_rounds: int = 2

    def _solve_urban_agent_local(self, signal, state, *args, **kwargs):
        """국소 최선응답을 **현시 벡터**로 푼다. p1 축을 쓰지 않는다.

        왜 p1 축을 버리는가. 상류는 스칼라 `p1` 후보를 훑고
        `distribute_phase_green(net, p1, ref)` 이 나머지 현시를 **직전 비율대로** 채운다.
        총합 고정 단체의 자유도는 (live 현시 −1) 인데 그중 1방향만 탐색하는 것이고,
        그 방향이 늘 p1 에 고정돼 있다. 한 신호의 현시들은 서로 다른 종류의 movement 를
        먹이므로(실측 core17legs4b: 17 SC 중 14개가 현시별 movement 종류가 다르고,
        SC1001·SC1004 는 p3/p4 만 off_ramp 를 갖는다) p1 축 하나로는 정작 중요한 현시를
        다른 현시와 비율로 섞어 희석한다. 실측으로 SC5 p3 가 가격 1위인 결정 14개
        **전부**에서 p3 가 하한에 묶였다.
        가격도 마찬가지다 — 상류 B2 항 `g_ext·(p1 − ref)` 는 교차로당 1차원이라
        "어느 현시에 줄지"를 표현할 수 없다.

        그래서 여기서는 직전 커밋 벡터를 시드로 현시쌍 교환 좌표하강을 돌린다.
        채점은 `local[veh·h] + Σ_i price_i·(g_i − ref_i)` — 정련과 **같은 함수**다.
        총합이 고정이라 `Σ(g_i − ref_i) = 0` 이므로 가격에 상수를 더해도 값이 안 변한다
        (게이지 자동 고정 — 이 클래스 독스트링 참조).

        상류 계약은 유지한다. 반환은 여전히 `(p1, obj, evals, nin)` 이고, 고른 벡터는
        `_gne_phase_override[signal]` 에 남겨 패치된 `distribute_phase_green` 이 집어간다.
        패치가 없거나 실패하면 반환된 p1 으로 종전 비율 전개가 돌아 안전하다.
        """
        store = getattr(self, "_gne_phase_override", None)
        if store is None:
            store = {}
            setattr(self, "_gne_phase_override", store)
        # **상류 탐색 전에 이 신호의 저장분을 비운다.** 안 비우면 패치된
        # `distribute_phase_green` 이 직전 sweep 의 벡터를 돌려주어, 상류가 p1 을 훑는
        # 동안 모든 후보가 같은 벡터로 채점된다(= 탐색이 통째로 무의미해진다).
        store.pop(str(signal), None)

        out = super()._solve_urban_agent_local(signal, state, *args, **kwargs)
        if not (self.phase_price_in_gne and self.signal_phase_price):
            return out
        # `candidates_override` 가 있으면 **단일 후보 채점**이다 — 리더가 가격(g_ext)을
        # 구하려고 특정 p1 의 국소 비용을 물어보는 경로(`local_green_costs`).
        # 거기서 벡터를 다시 최적화하면 물어본 점이 아닌 다른 점의 비용을 돌려주게 되어
        # **가격 자체가 틀어진다.** 그 경로는 상류 답을 그대로 쓴다.
        # 위치인자 번호는 상류 시그니처에서 뽑았다 —
        # (self, signal, state, coupling, arr_movement, s_eff_frozen, reservoir_drain,
        #  freeway_congestion, previous, leader, lambda_p, forecast_arrivals, horizon_h,
        #  demand, candidates_override, committed_prev)
        # 여기 *args 는 coupling 부터이므로 previous=args[5], candidates_override=args[11].
        if kwargs.get("candidates_override") is not None or (
            len(args) > 11 and args[11] is not None
        ):
            return out
        price = (self.signal_phase_price or {}).get(signal)
        if not price:
            return out
        try:
            net = self.cfg.network
            previous = kwargs.get("previous")
            if previous is None:
                previous = args[5] if len(args) > 5 else None
            if previous is None:
                return out
            ref = (self.signal_phase_price_ref or {}).get(signal) or {}
            weight = float(self.signal_phase_price_weight)
            demand = kwargs.get("demand")
            ctx = self._phase_refine_context(state, previous, demand)
            setup = self._phase_refine_signal_setup(signal, state, ctx) if ctx else None

            def scored(vec):
                if setup is not None:
                    local = self._phase_local_cost_phased(signal, vec, setup, ctx)
                else:
                    local = self.phase_shape_local_cost(signal, vec, state)
                ext = sum(float(price.get(pid, 0.0))
                          * (float(vec.get(pid, 0.0)) - float(ref.get(pid, 0.0)))
                          for pid in MODEL_PHASES)
                return local + weight * ext

            # 시드 둘 — 직전 커밋 벡터와 상류 p1 해. 나은 데서 출발한다. 상류 해를 버리지
            # 않는 이유는 그것이 국소 TTS 를 한 축에서 이미 최적화한 결과라, 가격이 약한
            # 신호에서는 좋은 출발점이기 때문이다.
            prev_vec = {pid: float(previous.green_times.get(phase_key(signal, pid), 0.0))
                        for pid in MODEL_PHASES}
            up_vec = dict(distribute_phase_green(
                net, float(out[0]), signal_green_reference(previous, net, signal), signal=signal))

            # trust region. 상류 p1 축은 `|p1 - ref| <= trust` 로 묶여 있고(실측 6.0초,
            # 493호출 중 459회에 심겨 있다), `_phase_exchange_candidates` 는 green_min/max 만
            # 보므로 벡터로 풀 때 그 제약이 빠진다. 같은 폭을 벡터에도 건다 — 각 현시가
            # 기준에서 trust 초를 넘게 벗어나지 못한다. 신호 계획의 시간축 안정성이
            # 플래툰·연동의 전제인데 모델은 그 비용을 안 본다.
            # **anchor 는 `committed_prev` 다.** GNE 본 루프는
            # `_solve_urban_agent_local(..., snapshot, ..., committed_prev=previous)` 로 부르는데
            # 8번째 위치인자 `previous` 는 **매 sweep 갱신되는 GNE 반복값**(snapshot)이다.
            # 거기에 trust 를 걸면 기준이 매 sweep 따라 움직여 6초씩 계속 걸어간다 —
            # 실측으로 sweep 이 누적돼 한 현시가 60.5초까지 이동했다(기준 34.5 대비).
            # 진짜 직전 커밋은 `committed_prev` 로 따로 온다.
            trust = getattr(self, "signal_marginal_price_trust_sec", None)
            committed = kwargs.get("committed_prev")
            if committed is None and len(args) > 12:
                committed = args[12]
            anchor_src = committed if committed is not None else previous
            anchor = {pid: float(anchor_src.green_times.get(phase_key(signal, pid), 0.0))
                      for pid in MODEL_PHASES}
            if sum(anchor.values()) <= 1.0e-9:
                anchor = dict(up_vec)

            def in_trust(vec):
                if trust is None:
                    return True
                t = float(trust)
                return all(
                    abs(float(vec.get(pid, 0.0)) - float(anchor.get(pid, 0.0))) <= t + 1.0e-9
                    for pid in MODEL_PHASES)

            # 시드도 거른다 — 후보만 걸러도 상류 해가 이미 trust 밖이면 거기서 출발한다.
            seeds = [s for s in (prev_vec, up_vec)
                     if sum(s.values()) > 1.0e-9 and in_trust(s)]
            if not seeds:
                return out
            best, best_obj = None, float("inf")
            for s in seeds:
                v = scored(s)
                if v < best_obj:
                    best, best_obj = s, v

            steps = tuple(getattr(self.cfg.mpc, "phase_price_exchange_steps_sec", (6.0, 2.0)))
            for _round in range(max(1, int(self.phase_price_in_gne_rounds))):
                moved = False
                for step in steps:
                    for cand in self._phase_exchange_candidates(signal, best, float(step)):
                        if not in_trust(cand):
                            continue
                        obj = scored(cand)
                        if obj < best_obj - 1.0e-12:
                            best, best_obj = cand, obj
                            moved = True
                if not moved:
                    break
            store[str(signal)] = {pid: float(v) for pid, v in best.items()}
            # 반환 p1 도 고른 벡터와 맞춘다 — 패치가 없을 때의 폴백이 엉뚱해지지 않게.
            p1 = float(best.get(PRIMARY_PHASE, out[0]))
            return (p1, float(out[1]), int(out[2]), float(out[3]))
        except Exception as exc:
            # **조용히 삼키지 않는다.** 2026-08-27 에 이 except 가 NameError 를 먹어
            # 벡터 탐색이 493호출 내내 한 번도 안 돌았는데 런은 정상으로 보였다
            # (`_gne_phase_override` 저장 0회). GNE 를 죽이지 않으려고 잡되, 무엇이
            # 몇 번 터졌는지는 남긴다 — 진단이 0 이 아니면 그 팔은 무효다.
            store2 = getattr(self, "_gne_phase_errors", None)
            if store2 is None:
                store2 = {}
                setattr(self, "_gne_phase_errors", store2)
            key = "%s: %s" % (type(exc).__name__, exc)
            store2[key] = store2.get(key, 0) + 1
            return out

    def solve(self, state, leader, demand, previous_control=None, leader_incumbent_obj=None):
        import numpy as _np

        if str(getattr(self, "green_reference_mode", "previous")).lower() == "pressure":
            self._pressure_signal_count = self._refresh_phase_pressure(state)

        result = (
            super().solve(state, leader, demand, previous_control)
            if leader_incumbent_obj is None
            else super().solve(state, leader, demand, previous_control, leader_incumbent_obj)
        )
        if self.phase_price_in_gne:
            # GNE 안에서 고른 현시 벡터를 심는다. 총합은 교환 후보가 보존하므로 주기 불변.
            store = getattr(self, "_gne_phase_override", None) or {}
            n = 0
            for signal, vec in store.items():
                for pid, value in vec.items():
                    key = phase_key(signal, pid)
                    if key in result.control.green_times:
                        result.control.green_times[key] = float(value)
                n += 1
            result.control.diagnostics["wu_phase_price_in_gne_signals"] = float(n)
            result.control.diagnostics["wu_phase_price_in_gne_enabled"] = 1.0
            errs = getattr(self, "_gne_phase_errors", None) or {}
            result.control.diagnostics["wu_phase_price_in_gne_errors"] = float(sum(errs.values()))
            if errs:
                top = max(errs.items(), key=lambda kv: kv[1])
                result.control.diagnostics["wu_phase_price_in_gne_error_top"] = str(top[0])[:200]
            setattr(self, "_gne_phase_override", {})
            setattr(self, "_gne_phase_errors", {})
        # 가격이 GNE 안에 있으면 정련은 **구조적으로 불필요**하다 — 같은 목적함수
        # (local + Σ price·Δg)로 같은 탐색을 한 번 더 하는 것이다. 그리고 해롭다.
        #
        # 실측(canon_gne_far, 37결정). 둘을 다 켜니 정련이 만진 신호가 10 -> 14 로 늘고
        # 라운드가 48 -> 94 로 2배가 됐다. 결정 간 녹색 변동 L1 도 368 -> 632.9초로 1.7배다.
        # 순서가 나쁘다 — GNE 가 벡터를 정하고, 정련이 또 옮기고, 다음 결정의 GNE 가
        # **정련이 옮긴 값**을 시드로 다시 푼다. 시드가 매번 남의 손을 탄 값이라 출렁임이
        # 누적된다. TTT 4940.8(+121.3)로 이 대장 최악이었다.
        #
        # config 규율(`refine_rounds: 0` 을 같이 적기)에 맡기지 않고 여기서 막는다 —
        # "두 곳이 서로 맞아야 한다" 가 이 저장소에서 반복된 실패 유형이다.
        if self.signal_phase_price and not self.phase_price_in_gne:
            self.apply_phase_price_refinement(result.control, state, demand)
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
    # 정련의 국소 비용 모형. 어댑터가 tuning `phase_price.local_cost_model` 로 심고,
    # 가격을 하달할 때 팔로워로 그대로 넘긴다. 기본 "drain" = 비트 동일.
    phase_price_local_cost_model: str = "drain"
    # 나머지 현시 배분 기준. 어댑터가 tuning `urban.green_reference` 로 심는다.
    green_reference_mode: str = "previous"
    phase_price_refine_rounds: int = 1
    # 주현시를 **가격 최고 현시**로 잡을지. 기본 꺼짐 = 비트 동일.
    #
    # 왜. `distribute_phase_green` 은 주현시 하나를 정하고 나머지를 비율대로 나눈다 —
    # 신호당 자유도가 1차원이고 그 축이 늘 p1 이다. 실측(map4d SC5): p3 가격이 SC5 에서
    # 1위인 결정 14개 **전부**에서 p3 가 하한(22.7)에 묶였다(고정계획은 47). 가격은
    # 옳게 가리키는데 그 방향으로 갈 대역폭이 없다 — 정련의 6초 교환만이 되돌릴 수
    # 있는데 GNE 가 매 결정 비율을 다시 뭉갠다.
    phase_price_primary_by_price: bool = False
    phase_price_primary_margin: float = 0.0

    def __setstate__(self, state):
        """언피클 직후 — 가격 워커에서 어댑터의 런타임 몽키패치를 되살린다.

        가격 롤아웃 병렬화는 워커를 **spawn** 한다(Windows). 새 인터프리터는 모듈을
        새로 import 하므로 부모가 런타임에 심은 패치가 워커에는 없다. 대상은
        `_phase_green_fraction`(어댑터가 5개 모듈에 심는다) 이고, 그게 없으면 워커는
        실제 신호 프로그램이 아니라 일반 공식으로 green->유량을 계산한다. 실패가 아니라
        **조용히 틀린 값**이라 더 나쁘다.

        2026-08-20 실측(phasepar 런). 같은 입력 t=600 에서 직렬과 병렬이 갈렸다 —
        가격 15개 중 14개 불일치(SC5 27%, SC6 부호 반전), 커밋된 녹색이 SC1002·SC12·SC5
        에서 8초씩 반대. `ramp_metering`·`vsl`·`offsets` 는 비트 동일했는데, 이 패치가
        green 전용이라는 것과 정확히 맞는다. 워커 4개와 10개는 서로 비트 동일해
        (청킹이 다른데도) 비결정성·해시시드·부동소수 순서는 전부 배제됐다.

        cfg 속성으로 들어가는 패치는 해당 없다 — 캘리브레이션 v2
        (`freeway_segment_length_profile_km`)와 VSL/METANET 은 컨트롤러와 함께 피클된다.

        되살리기에 실패하면 **raise 한다**. pool 이 깨지고 호출처의 except 가 직렬로
        재실행하며 `price_parallel_serial_rerun_count` 와 사유를 남긴다. 워커인데
        부트스트랩이 아예 없는 경우도 같이 막는다 — 그게 이 버그의 원래 모습이다.
        """
        self.__dict__.update(state)
        boot = state.get("price_worker_bootstrap")
        import multiprocessing as _mp

        in_worker = _mp.parent_process() is not None
        if not boot:
            if in_worker:
                raise RuntimeError(
                    "가격 워커에 런타임 패치 부트스트랩이 없다 — 워커가 패치 안 된 "
                    "_phase_green_fraction 으로 가격을 매기게 된다"
                )
            return
        import importlib
        import sys as _sys

        path = boot.get("sys_path")
        if path and path not in _sys.path:
            _sys.path.insert(0, path)
        module = importlib.import_module(boot["module"])
        getattr(module, boot["func"])(
            self.cfg, boot["state_json"], boot["detector_mapping"],
        )
        probe = importlib.import_module(boot["verify_module"])
        if not hasattr(probe, boot["verify_attr"]):
            raise RuntimeError(
                "가격 워커 부트스트랩이 "
                f"{boot['verify_module']}.{boot['verify_attr']} 를 심지 못했다"
            )

    def _make_follower_solver(self, cfg: ExperimentConfig):
        return LinkAgentWuFollower(cfg)

    def _evaluate_full_candidate(self, index, action, state, forecast, previous,
                                 stage="coarse", incumbent_obj=float("inf"),
                                 rollout_abort_obj=float("inf")):
        """상류 그대로 + 후보별 벽시계와 N_UF 재사용 계측만 덧붙인다(거동 불변).

        왜 재나. 결정 wall 373초 중 가격 배치가 약 134초고 나머지는 후보 full 평가다
        (가격만 병렬화했을 때 1.48배에서 멈춘 이유). 그런데 후보 평가를 병렬로 쪼개는 게
        이득인지는 **N_UF 재사용 캐시**(`_nuf_solve_cache`)에 달렸다 — 상류 설계상 N_UF 가
        같은 후보는 follower solve 와 rollout 을 통째로 재사용하므로, 직렬에서 2·3번째
        후보가 거의 공짜면 병렬로 쪼개도 각 워커가 다시 계산해 이득이 사라진다.

        그래서 먼저 재고 나서 정한다. `..._wall_sec_{stage}_{index}` 와 재사용 적중 수를
        남긴다.
        """
        import time as _time

        hits_before = int(getattr(self, "_dedupe_hits", 0) or 0)
        t0 = _time.perf_counter()
        out = super()._evaluate_full_candidate(
            index, action, state, forecast, previous,
            stage=stage, incumbent_obj=incumbent_obj,
            rollout_abort_obj=rollout_abort_obj,
        )
        elapsed = float(_time.perf_counter() - t0)
        hit = int(getattr(self, "_dedupe_hits", 0) or 0) - hits_before
        out.metadata[f"leader_candidate_wall_sec_{stage}_{index}"] = elapsed
        out.metadata[f"leader_candidate_nuf_reuse_{stage}_{index}"] = float(hit)
        out.metadata[f"leader_candidate_nuf_star_{stage}_{index}"] = float(
            getattr(action, "N_UF_star", 0.0)
        )
        return out

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

    def _phase_price_rollouts(
        self,
        state: TrafficState,
        previous: ControlAction,
        forecast: List[DemandStep],
        tasks: List[tuple],
    ) -> Dict[tuple, float]:
        """현시 방향 전역 롤아웃을 일괄 평가한다 — (signal, pid) -> TTT.

        `_green_price_rollouts` 와 같은 규약이다. `price_parallel_workers <= 1` 이면 직렬이고
        기존과 비트 동일하다. 병렬이어도 각 롤아웃 인자가 같고 순수 함수이므로 결과가 같다.
        병렬 실패는 **조용히 넘기지 않는다** — 직렬로 재실행하되 카운터와 사유를 남긴다
        (그러지 않으면 런타임 예산이 조용히 몇 배로 늘고 병렬 경로가 한 번도 안 돈 채
        "동일" 로 읽힌다).
        """
        if not tasks:
            return {}
        workers = int(getattr(self, "price_parallel_workers", 0) or 0)

        def serial() -> Dict[tuple, float]:
            return {
                (sig, pid): self._global_ttt_with_phases(state, previous, forecast, sig, phases)
                for sig, pid, phases in tasks
            }

        if workers <= 1 or len(tasks) <= 1:
            return serial()

        from concurrent.futures import ProcessPoolExecutor

        out: Dict[tuple, float] = {}
        try:
            with ProcessPoolExecutor(
                max_workers=min(workers, len(tasks)),
                initializer=_price_worker_init,
                initargs=(self, state, previous, forecast, _adapter_patch_present()),
            ) as pool:
                for sig, pid, ttt in pool.map(_price_worker_phase, tasks):
                    out[(sig, pid)] = float(ttt)
        except Exception as exc:  # noqa: BLE001
            self.price_parallel_serial_rerun_count += 1
            self.price_parallel_last_error = f"{type(exc).__name__}: {exc}"
            return serial()
        return out

    def _refresh_phase_prices(
        self, state: TrafficState, forecast: List[DemandStep], previous: ControlAction,
    ) -> None:
        """g_i = (전역 방향미분) - (국소 방향미분) = 현시 i 로의 재배분이 갖는 외부효과.

        기존 p1 축 가격과 같은 규약이다 — 국소분을 빼서 **팔로워가 이미 보는 몫**을 제거한다.
        빼지 않으면 팔로워가 자기 비용을 두 번 센다.

        전역 롤아웃은 **한 번에 모아 병렬로** 돈다. 국소분(`phase_shape_local_cost`)은 큐
        배수 모형이라 싸므로 직렬로 둔다.
        """
        follower = self.nash_solver
        if not isinstance(follower, LinkAgentWuFollower):
            return
        net = self.cfg.network
        delta = float(self.phase_price_delta_sec)
        base_ttt = self._global_ttt_with_phases(state, previous, forecast, "", None)

        tasks: List[tuple] = []
        meta: Dict[tuple, tuple] = {}
        refs: Dict[str, Dict[str, float]] = {}
        for signal in net.signals:
            base = self._phase_vector(previous, signal)
            live = [pid for pid in net.signal_live_phases(signal) if base.get(pid, 0.0) > 0.0]
            if len(live) < 3:
                # 2현시 이하는 p1 축 가격이 이미 완전하다 — 자유도가 1뿐이다.
                continue
            base_local = follower.phase_shape_local_cost(signal, base, state)
            added = False
            for pid in live:
                moved = self._phase_direction(signal, base, pid, delta)
                if moved is None:
                    continue
                tasks.append((signal, pid, moved))
                meta[(signal, pid)] = (moved, base_local, len(live))
                added = True
            if added:
                refs[signal] = base

        rollouts = self._phase_price_rollouts(state, previous, forecast, tasks)

        prices: Dict[str, Dict[str, float]] = {}
        for (signal, pid), ttt in rollouts.items():
            moved, base_local, n_live = meta[(signal, pid)]
            local = follower.phase_shape_local_cost(signal, moved, state)
            # 척도 보정 (n-1)/n. 방향 d_i = e_i - (1/(n-1))*sum_{j!=i} e_j 로 재면
            #   d_i - d_j = (n/(n-1)) * (e_i - e_j)
            # 이라 g_i - g_j 가 순수 교환 미분의 n/(n-1) 배가 된다. 팔로워는 순수 교환으로
            # 움직이므로 그대로 쓰면 가격항이 참값보다 크고, 그 배율이 **현시 수마다 다르다**
            # (4현시 4/3, 3현시 3/2). 여기서 참값으로 되돌린다.
            scale = float(n_live - 1) / float(n_live)
            raw_g = ((float(ttt) - base_ttt) - (local - base_local)) / max(delta, 1.0e-9)
            prices.setdefault(signal, {})[pid] = float(raw_g * scale)

        if bool(getattr(self, "phase_price_primary_by_price", False)) and prices:
            self._assign_primary_by_price(prices)
        follower.signal_phase_price = prices or None
        follower.signal_phase_price_ref = {s: refs[s] for s in prices} or None
        follower.signal_phase_price_weight = float(self.phase_price_weight)
        follower.phase_price_local_cost_model = str(
            getattr(self, "phase_price_local_cost_model", "drain")
        )
        follower.green_reference_mode = str(getattr(self, "green_reference_mode", "previous"))
        follower.phase_price_refine_rounds = int(getattr(self, "phase_price_refine_rounds", 1))
        # 현시가격을 GNE 안에서 쓸지. 팔로워가 국소 최선응답에서 읽는다(2026-08-27).
        follower.phase_price_in_gne = bool(getattr(self, "phase_price_in_gne", False))
        follower.phase_price_in_gne_rounds = int(getattr(self, "phase_price_in_gne_rounds", 2))
        self._phase_price_rollout_count = len(tasks) + 1
        self._phase_price_workers = int(getattr(self, "price_parallel_workers", 0) or 0)

    def _assign_primary_by_price(self, prices) -> None:
        """가격이 가장 높은 현시를 그 신호의 주현시로 잡는다.

        가격은 교환가격이라 합이 0 에 가깝다 — 최고가 현시가 "녹색을 더 주면 망 전체
        한계이득이 가장 큰 곳" 이고, 그게 자유변수가 되어야 할 축이다.

        진동 방지. 현 주현시보다 `phase_price_primary_margin` 이상 비쌀 때만 바꾼다.
        매 결정 축이 뒤집히면 나머지 현시의 reference 비율이 매번 재해석되어 불안정해진다.
        """
        net = self.cfg.network
        current = dict(getattr(net, "primary_phase_by_signal", {}) or {})
        margin = float(getattr(self, "phase_price_primary_margin", 0.0))
        changed = 0
        for signal, price in prices.items():
            live = set(net.signal_live_phases(signal))
            cand = {pid: float(v) for pid, v in price.items() if pid in live}
            if not cand:
                continue
            best_pid = max(cand, key=lambda k: cand[k])
            cur_pid = current.get(str(signal)) or net.signal_primary_phase(signal)
            cur_v = cand.get(cur_pid)
            if cur_v is None or cand[best_pid] > cur_v + margin:
                if current.get(str(signal)) != best_pid:
                    changed += 1
                current[str(signal)] = best_pid
        setattr(net, "primary_phase_by_signal", current)
        self._primary_by_price_changed = changed

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
