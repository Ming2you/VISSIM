"""Candidate-private landing storage for the canonical link-local predictor.

The local solver below is the single-method extraction of vendor
WuFaithfulFollower._solve_freeway_agent_local. Candidate generation and price
terms are preserved; landing dynamics use explicit stocks and a mass ledger.
External urban arrivals and other freeway links remain frozen boundaries.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import math
from types import SimpleNamespace
from typing import Dict, List, Optional, Sequence


def _finite_nonnegative(value, name):
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return value


def branch_capacity(signal_available, direct_available, share, dt_h):
    """Largest total flow whose fixed split fits both receiving branches."""
    signal_available = _finite_nonnegative(signal_available, "signal_available")
    direct_available = _finite_nonnegative(direct_available, "direct_available")
    share = _finite_nonnegative(share, "share")
    dt_h = _finite_nonnegative(dt_h, "dt_h")
    if share > 1 or dt_h == 0:
        raise ValueError("share must be <= 1 and dt_h must be positive")
    signal = signal_available / (1 - share) if share < 1 else math.inf
    direct = direct_available / share if share > 0 else math.inf
    return min(signal, direct) / dt_h


def configure(cfg, tuning):
    flag = (tuning.get("freeway", {}) or {}).get("local_landing_state", False)
    if not isinstance(flag, bool):
        raise ValueError("freeway.local_landing_state must be a boolean")
    cfg.network.local_landing_state = flag
    if flag:
        for prerequisite in ("local_lane_context", "conservative_offramp_drain"):
            if not getattr(cfg.network, prerequisite, False):
                raise ValueError(f"local_landing_state requires freeway.{prerequisite}=true")
    return {"local_landing_state": 1.0} if flag else {}


class LocalLandingState:
    """One candidate's physical storages; capacity is never treated as stock.

    Receiver links are shared dictionaries, including when multiple offramps
    feed one direct landing. Point queues reserve receiving space but retain
    their existing urban owner. They are frozen boundary constraints here.
    """
    def __init__(self, follower, model, state):
        self.follower, self.model, self.cfg = follower, model, follower.cfg
        net = self.cfg.network
        self.net = net
        self.step = int(round(state.time_sec / self.cfg.simulation.T_u_sec))
        self.signal = {o: str(net.off_ramp_storage_link[o]) for o in model.owned_offramps}
        self.share = {o: float(getattr(net, "offramp_direct_share_by_offramp", {}).get(o, 0)) for o in self.signal}
        self.direct = {o: str(getattr(net, "offramp_direct_tail_by_offramp", {}).get(o, "")) for o in self.signal}
        self.receivers = set()
        for off in self.signal:
            branch_capacity(0, 0, self.share[off], self.cfg.simulation.T_f_h)
            if self.share[off] and self.direct[off] not in net.urban_link_storage_veh:
                raise ValueError(f"Missing direct landing storage: {off} -> {self.direct[off]}")
            for _, movement in follower._wu._offramp_drain_flow.get(off, []):
                target = str(follower._wu._specs[movement].get("receiving_link", ""))
                if target:
                    if target not in net.urban_link_storage_veh:
                        raise ValueError(f"Missing signal receiver storage: {target}")
                    self.receivers.add(target)
        links = set(self.signal.values()) | self.receivers | {self.direct[o] for o in self.signal if self.share[o]}
        if len(set(self.signal.values())) != len(self.signal):
            raise ValueError("Offramps sharing one signal storage require explicit routing ownership")
        if set(self.signal.values()) & (self.receivers | set(self.direct.values())):
            raise ValueError("Signal OR storage cannot also be a direct or receiving link")
        self.capacity = {k: _finite_nonnegative(net.urban_link_storage_veh[k], f"capacity {k}") for k in links}
        self.stock = {k: max(0.0, cap - float(state.urban_link_storage.get(k, cap))) for k, cap in self.capacity.items()}
        self.point_queue = Counter()
        for movement, q in state.urban_movement_queue.items():
            origin = str(net.urban_movements.get(movement, {}).get("origin", ""))
            if origin in links:
                self.point_queue[origin] += max(0.0, float(q))
        self.pending = {k: {} for k in links}
        for attr in ("urban_storage_release_buffer", "offramp_transit_buffer"):
            for k, arrivals in getattr(state, attr, {}).items():
                if k in links:
                    for step, count in arrivals.items():
                        if int(step) > self.step:
                            self.pending[k][int(step)] = self.pending[k].get(int(step), 0.0) + float(count)
        self.speeds = dict(state.urban_link_speed_kph)
        self.external_ramp_q = {r: max(0.0, float(q)) for r, q in state.ramp_queue.items()}
        self.initial_stock = sum(self.stock.values())
        self.ledger = Counter()
        self.split = dict(getattr(net, "boundary_out_ramp_split", {}) or {})
        if any(k in self.split for k in links) and not getattr(net, "leg_ramp_split_enabled", False):
            raise ValueError("Local W_out landing requires the canonical leg_ramp_split runtime")
        # Decompose the frozen coupling once, using the same W_out stock/τ
        # estimator; these components are replaced by explicit internal transfers.
        self.replaced_coupling = Counter()
        for k in links:
            if k in self.split:
                reach_rate = self.arrived(k) * self._reach_rate(k)
                # WuDistributed._coupling requests the estimator over T_c,
                # even though this candidate advances at T_f/T_u internally.
                reach_rate = min(self.arrived(k) / self.cfg.simulation.T_c_h, reach_rate)
                for ramp, share in self.split[k].get("ramps", {}).items():
                    if ramp in model.owned_ramps:
                        self.replaced_coupling[ramp] += reach_rate * float(share)

    def _reach_rate(self, link):
        lengths = getattr(self.net, "boundary_out_link_length_km", {}) or {}
        length = float(lengths.get(link, 0) or (getattr(self.net, "urban_link_length_km", {}) or {}).get(link, 0))
        if length <= 0:
            raise ValueError(f"Explicit W_out travel length required: {link}")
        speed = float(self.net.leg_ramp_split_wout_speed_kmh)
        return 1.0 / max(length / max(speed, 5.0), 1e-4)

    def arrived(self, link):
        future = sum(v for t, v in self.pending[link].items() if t > self.step)
        return max(0.0, self.stock[link] - future)

    def available(self, link):
        physical = max(0.0, self.capacity[link] - self.stock[link])
        stopline = (getattr(self.net, 'urban_stopline_storage_veh', {}) or {}).get(link)
        if stopline is not None:
            physical = min(physical, float(stopline))
        return max(0.0, physical - self.point_queue[link])

    def occupancy(self):
        return {off: self.stock[k] + self.point_queue[k] for off, k in self.signal.items()}

    def capacities(self, dt_h):
        # Reserve shared direct space proportionally to each group's independent
        # demand bound. This guarantees all simultaneous branch arrivals fit.
        caps = {off: branch_capacity(self.available(k), self.available(self.direct[off]) if self.share[off] else 0,
                    self.share[off], dt_h) for off, k in self.signal.items()}
        for target in {self.direct[o] for o in self.signal if self.share[o]}:
            groups = [o for o in caps if self.share[o] and self.direct[o] == target]
            needed = sum(caps[o] * self.share[o] * dt_h for o in groups)
            ratio = min(1.0, self.available(target) / needed) if needed else 1.0
            for off in groups:
                caps[off] *= ratio
        caps[self.model.link] = sum(caps.values())
        return caps

    def _schedule(self, link, vehicles, delay):
        if vehicles:
            at = self.step + int(delay)
            self.pending[link][at] = self.pending[link].get(at, 0.0) + vehicles

    def _record_closure(self):
        residual = sum(self.stock.values()) - self.initial_stock - self.ledger['arrivals_veh'] + self.ledger['departures_veh']
        self.ledger['max_abs_residual_veh'] = max(self.ledger['max_abs_residual_veh'], abs(residual))
        if abs(residual) > 1e-7 or any(v < -1e-8 or v > self.capacity[k] + 1e-7 for k, v in self.stock.items()):
            raise RuntimeError(f"Local landing stock conservation failed: {residual}")

    def land(self, flows, dt_h):
        from src.models.urban_queue_model import _inflow_delay_steps
        additions = Counter()
        for off, target in self.signal.items():
            total = _finite_nonnegative(flows.get(off, 0), f"offramp flow {off}") * dt_h
            direct = total * self.share[off]
            additions[target] += total - direct
            if direct:
                additions[self.direct[off]] += direct
            self._schedule(target, total - direct, _inflow_delay_steps(self.cfg))
        for k, value in additions.items():
            if value > self.available(k) + 1e-7:
                raise RuntimeError(f"Offramp accepted flow exceeds branch receiving capacity: {k}")
            self.stock[k] += value
        self.ledger['arrivals_veh'] += sum(additions.values())
        self._record_closure()

    def advance(self, control, ramp_q, dt_h):
        """Advance urban boundaries before FW withdrawal, at native urban steps."""
        from src.models.urban_queue_model import _link_delay_steps
        tu = self.cfg.simulation.T_u_h
        count = round(dt_h / tu)
        if count < 1 or abs(count * tu - dt_h) > 1e-12:
            raise ValueError("Local landing requires integral T_f/T_u")
        for _ in range(count):
            # Service uses the current boundary; FW landings follow all urban steps.
            # Frozen external receiving boundaries; own ramps are explicit state.
            for target in sorted(set(self.stock) - set(self.signal.values())):
                arrived = self.arrived(target)
                departed = 0.0
                split = self.split.get(target)
                exit_cap = float(self.net.boundary_out_capacity_veh_h)
                if split:
                    reach = min(arrived, arrived * self._reach_rate(target) * tu)
                    free = reach * float(split.get('free', 0))
                    departed = min(free, exit_cap * tu) if exit_cap > 0 else free
                    for ramp, share in split.get('ramps', {}).items():
                        queue = ramp_q.get(ramp, self.external_ramp_q.get(ramp, 0.0))
                        room = max(0.0, self.net.ramp_queue_cap(ramp) - queue)
                        cap = float(self.net.ramp_capacity_veh_h[ramp]) * tu
                        transfer = min(reach * float(share), room, cap)
                        departed += transfer
                        if ramp in self.model.owned_ramps:
                            ramp_q[ramp] = queue + transfer
                            self.ledger['own_ramp_transfers_veh'] += transfer
                        else:
                            self.ledger['external_ramp_transfers_veh'] += transfer
                else:
                    # Same finite receiver boundary as the prior local predictor;
                    # tail override matches the canonical global tail sink.
                    cap = float((getattr(self.net, 'wout_tail_exit_capacity_veh_h', {}) or {}).get(target, exit_cap))
                    departed = min(arrived, cap * tu) if cap > 0 else arrived
                self.stock[target] -= departed
                self.ledger['departures_veh'] += departed
            for off, target in self.signal.items():
                receiver_occ = {k: self.capacity[k] - self.available(k) for k in self.receivers}
                drain, intakes = self.follower._local_offramp_drain(off, self.arrived(target), receiver_occ, control, tu)
                removed = drain * tu
                if removed > self.arrived(target) + 1e-8:
                    raise RuntimeError("Local signal drain exceeds available vehicles")
                self.stock[target] -= removed
                landed = 0.0
                for receiving, rate in intakes.items():
                    value = rate * tu
                    if value > self.available(receiving) + 1e-7:
                        raise RuntimeError("Shared signal receiver over capacity")
                    self.stock[receiving] += value
                    landed += value
                    view = SimpleNamespace(urban_link_storage={k: self.capacity[k] - self.stock[k] for k in self.stock},
                                           urban_link_speed_kph=self.speeds)
                    self._schedule(receiving, value, _link_delay_steps(view, self.cfg, receiving))
                self.ledger['departures_veh'] += removed - landed
            self._record_closure()
            self.step += 1


def install(cfg):
    from src.controllers.wu_faithful_follower import WuFaithfulFollower
    original = WuFaithfulFollower._solve_freeway_agent_local
    if not getattr(original, '_rw_local_landing_state', False):
        def selected(self, *args, **kwargs):
            if not getattr(self.cfg.network, 'local_landing_state', False):
                return original(self, *args, **kwargs)
            return solve_freeway_agent_local(self, *args, **kwargs)
        selected._rw_local_landing_state = True
        WuFaithfulFollower._solve_freeway_agent_local = selected
    return {'local_landing_state_runtime': 1.0} if getattr(cfg.network, 'local_landing_state', False) else {}


def solve_freeway_agent_local(
    self,
    link: str,
    state: TrafficState,
    coupling: Mapping[str, float],
    demand: DemandStep,
    previous: ControlAction,
    vsl_override: Optional[Sequence[float]] = None,
) -> tuple[Dict[str, float], float, int]:
    """`_solve_freeway_agent`의 per-link 국소판 — 후보 채점이 **이 link 본선만** 전진한다.

    SPEC: parent `_solve_freeway_agent`는 후보마다 `freeway_substep`(전체 freeway link 루프)을
    돌려 비국소다. 여기서는 `freeway_substep_local`(이 link만)로 같은 own-TTS를 채점한다.
    본선 이웃 경계는 plant 규약(upstream=v_free, downstream=self)으로 이미 동결돼 있어 별도
    조작 없이 plant와 동일 거동을 낸다. on-ramp reservoir·off-ramp storage는 이 link 권역만
    국소 추적한다. 반환 (segment 키 vsl_dict, own-TTS, evaluations) — parent와 동일 시그니처.
    반환 dict의 off-ramp 유출은 `_last_offramp_flow`에 캐시(coupling freeway→urban 재사용)."""
    from src.controllers import wu_faithful_follower as vendor
    ControlAction = vendor.ControlAction
    segment_vsl = vendor.segment_vsl
    freeway_substep_local = vendor.freeway_substep_local
    net = self.cfg.network
    sim = self.cfg.simulation
    ff = self.cfg.freeway_follower
    model = self._local_freeway_models[link]
    horizon = max(1, ff.freeway_prediction_horizon_steps or self.cfg.mpc.horizon_steps)
    dt_h = sim.T_f_h
    vsl_max = max(ff.vsl_set)
    smooth_w = ff.vsl_smoothness_weight
    n_seg = model.n_seg
    prev_vec = [segment_vsl(previous, link, i, self.cfg) for i in range(n_seg)]

    candidates = (
        self._wu._relaxed_freeway_segment_candidates(link, n_seg, state, coupling, previous, demand)
        if self.cfg.mpc.relaxed_quantized_controls
        else self._wu._freeway_segment_candidates(link, n_seg, previous)
    )
    vsl_sequences = self._freeway_vsl_sequence_candidates(
        link, n_seg, previous, candidates, horizon,
    )
    # JOINT h_local probe: vsl를 단일 값으로 고정 채점(고정 (meter,vsl) own-TTS).
    if vsl_override is not None:
        fixed_vec = [float(v) for v in vsl_override][:n_seg]
        if len(fixed_vec) < n_seg:
            fixed_vec += [float(fixed_vec[-1] if fixed_vec else vsl_max)] * (n_seg - len(fixed_vec))
        vsl_sequences = [[list(fixed_vec) for _ in range(horizon)]]
    # PRICE-TR: VSL 가격 활성 시 trust region(±vsl_marginal_price_trust_kmh) 밖 후보 제외
    # (선형화 유효 반경 — 가격이 측정된 이웃만). 전무 시 전체 fallback(이동성 보장).
    elif self.vsl_marginal_price and self.vsl_marginal_price_trust_kmh is not None:
        trust_v = float(self.vsl_marginal_price_trust_kmh)
        kept = []
        for seq in vsl_sequences:
            fv = seq[0] if seq else []
            ok = True
            for i, v in enumerate(fv):
                ref = self.vsl_marginal_price_ref.get(f"{link}__seg{i}")
                if ref is not None and abs(float(v) - float(ref)) > trust_v + 1.0e-9:
                    ok = False
                    break
            if ok:
                kept.append(seq)
        if kept:
            vsl_sequences = kept

    # 후보 무관 초기 스냅샷(이 link 권역만).
    rhos0 = list(state.freeway_density.get(link, []))
    speeds0 = list(state.freeway_speed.get(link, []))
    lanes0 = list(state.freeway_effective_lanes.get(link, [])) or [
        float(net.freeway_lanes) for _ in range(n_seg)
    ]
    if len(lanes0) != n_seg:
        lanes0 = [float(net.freeway_lanes) for _ in range(n_seg)]
    origin_q0 = max(0.0, float(state.mainline_origin_queue.get(link, 0.0)))
    # Phase B(완충 동결 결합): 완충 plant면 상·하류 완충 경계를 결정시점 값으로 동결해 전달.
    _buf_bc = None
    if int(getattr(net, "freeway_buffer_segments", 0)) > 0:
        _bu_r_bc = state.freeway_buffer_up_density.get(link) or []
        _bu_v_bc = state.freeway_buffer_up_speed.get(link) or []
        _bd_r_bc = state.freeway_buffer_down_density.get(link) or []
        if _bu_r_bc and _bd_r_bc:
            from src.models.metanet import segment_flow_veh_h as _sfvh_bc
            _bu_send_bc = _sfvh_bc(_bu_r_bc[-1], _bu_v_bc[-1], float(net.freeway_lanes))
            _phi_bc = float(getattr(net, "capacity_drop_discharge_phi", 1.0) or 1.0)
            if _phi_bc < 1.0 and _bu_r_bc[-1] > float(net.rho_crit):
                # plant capacity drop과 동일 cap(동결 BC 정합).
                _bu_send_bc = min(_bu_send_bc, _phi_bc * float(net.freeway_capacity_veh_h))
            _buf_bc = (
                _bu_send_bc,
                float(_bu_v_bc[-1]),
                float(_bd_r_bc[0]),
            )
    ramp_q0 = {r: max(0.0, float(state.ramp_queue.get(r, 0.0))) for r in model.owned_ramps}
    best_vec, best_obj = list(prev_vec), float("inf")
    best_offramp_flow: Dict[str, float] = {o: 0.0 for o in model.owned_offramps}
    evals = 0
    best_landing = None
    max_landing_residual = 0.0
    for sequence in vsl_sequences:
        candidate_control = ControlAction(
            ramp_metering=dict(previous.ramp_metering),
            vsl=dict(previous.vsl),
            green_times=dict(previous.green_times),
            offsets=dict(previous.offsets),
            inflow_outflow_allocation={},
        )
        first_vec = sequence[0] if sequence else list(prev_vec)
        for i, v in enumerate(first_vec):
            candidate_control.vsl[f"{link}__seg{i}"] = float(v)
        # 국소 상태 복사(후보별 독립).
        rhos = list(rhos0)
        speeds = list(speeds0)
        prev_lanes = list(lanes0)
        origin_q = origin_q0
        ramp_q = dict(ramp_q0)
        landing = LocalLandingState(self, model, state)
        # 가상 상류 blocked 큐[veh]: reservoir 만석으로 수용 못 한 coupling 유입의 이월분
        # (P1 — urban 상류 externality를 own-TTS에 보이게 한다). 후보별 독립.
        blocked_q = {r: 0.0 for r in model.owned_ramps}
        cost = 0.0
        first_offramp_flow = dict(best_offramp_flow)
        first_substep = True
        for horizon_idx in range(horizon):
            current_vec = sequence[min(horizon_idx, len(sequence) - 1)]
            # Sequence MPC: score the bounded VSL trajectory inside the
            # horizon, but commit only first_vec to the plant controller.
            for i, v in enumerate(current_vec):
                candidate_control.vsl[f"{link}__seg{i}"] = float(v)
            for _ in range(sim.K_cf):
                # Spec 3.4.3: ramp metering release는 T_f 시작 시점의 reservoir만 본다.
                # 같은 T_f 안에서 urban green으로 새로 들어온 차량은 이번 release가 아니라
                # 다음 release 결정부터 사용할 수 있으므로, release를 먼저 계산하고 나중에 적재한다.
                ramp_release = self._local_ramp_release(link, rhos, ramp_q, candidate_control, demand)
                for ramp, rel in ramp_release.items():
                    ramp_q[ramp] = max(0.0, ramp_q.get(ramp, 0.0) - max(0.0, rel) * dt_h)
                # Candidate-owned urban steps precede this freeway withdrawal.
                landing.advance(candidate_control, ramp_q, dt_h)
                # urban->freeway coupling[veh/h]은 release 이후 ramp reservoir에 적재된다.
                for ramp in model.owned_ramps:
                    approach = max(0.0, float(coupling.get(f"u_on_{ramp}", 0.0)) - landing.replaced_coupling.get(ramp, 0.0))
                    if self.count_blocked_ramp_inflow:
                        # 가상 blocked 큐: reservoir 가용공간(space)에 blocked 이월분을
                        # 먼저(FIFO) 넣고, 남은 공간에 신규 유입을 넣는다. 못 들어간
                        # 차량은 blocked_q에 남아 own-TTS에서 세어진다(무한 큐 가시화).
                        q = max(0.0, ramp_q.get(ramp, 0.0))
                        space = max(0.0, net.ramp_queue_cap(ramp) - q)
                        arrival = approach * dt_h
                        adm1 = min(blocked_q[ramp], space)
                        adm2 = min(arrival, space - adm1)
                        ramp_q[ramp] = min(net.ramp_queue_cap(ramp), q + adm1 + adm2)
                        blocked_q[ramp] = blocked_q[ramp] - adm1 + (arrival - adm2)
                    else:
                        ramp_q[ramp] = min(
                            net.ramp_queue_cap(ramp),
                            max(0.0, ramp_q.get(ramp, 0.0)) + approach * dt_h,
                        )
                offramp_capacity = landing.capacities(dt_h)
                occ = landing.occupancy()
                # per-link METANET 한 substep 전진(이 link 본선만).
                rhos, speeds, prev_lanes, origin_q, offramp_flow, veh_count = freeway_substep_local(
                    model, rhos, speeds, prev_lanes, occ, origin_q,
                    ramp_release, offramp_capacity, candidate_control, demand,
                    buffer_bc=_buf_bc,
                )
                landing.land(offramp_flow, dt_h)
                if first_substep:
                    first_offramp_flow = {o: max(0.0, float(offramp_flow.get(o, 0.0))) for o in best_offramp_flow}
                    first_substep = False
                # Wu own-TTS: 이 link segment 차량 + 이 link ramp queue + off-ramp storage 점유
                # + (P1) reservoir가 수용 못 한 가상 blocked 큐(urban 상류 externality).
                link_vehicles = sum(veh_count)
                link_ramp_queue = sum(max(0.0, ramp_q.get(r, 0.0)) for r in model.owned_ramps)
                link_offramp_storage = sum(landing.stock.values())
                link_blocked_queue = sum(blocked_q.values())
                cost += (
                    link_vehicles + link_ramp_queue + link_offramp_storage + link_blocked_queue
                ) * dt_h
        # (ii-b 2026-07-19, 기본 OFF) follower terminal cost: rollout 끝에 남은 ramp+blocked
        # 큐의 삼각 배수 tail(Q²/2R)을 own-TTS에 가산 — 창 밖 배수 비용이 무가격이라
        # metering이 과대평가되는 근시 병리 교정. R = ramp_cap×receiving(ρ_merge_end),
        # far(MFD tail)의 ramp 항과 동일 형태·상수 0(상태 유도).
        if getattr(self.cfg.mpc, "follower_terminal_cost_enabled", False):
            _rho_crit_tc = float(net.rho_crit)
            _rho_max_tc = float(net.rho_max)
            for _ramp_tc in model.owned_ramps:
                _q_end = max(0.0, ramp_q.get(_ramp_tc, 0.0)) + max(0.0, blocked_q.get(_ramp_tc, 0.0))
                if _q_end <= 0.0:
                    continue
                _m_idx = model.ramp_merge_idx[_ramp_tc]
                _rho_m = float(rhos[_m_idx]) if _m_idx < len(rhos) else 0.0
                _recv = min(1.0, max(0.0, (_rho_max_tc - _rho_m) / max(_rho_max_tc - _rho_crit_tc, 1.0e-9)))
                _r_end = max(1.0, float(net.ramp_capacity_veh_h.get(_ramp_tc, 0.0)) * _recv)
                cost += _q_end * _q_end / (2.0 * _r_end)
        # VdB4 보호큐 벌점 — 링크-agent metering 배선(2026-07-19 3차, 기본 OFF):
        # 방류-결합형(초과 지속 중 미방류 몫 과금). rollout 전체의 평균 release로 근사.
        _pq_mv_f = str(getattr(self.cfg.mpc, "protected_queue_movement", "") or "")
        _pq_w_f = float(getattr(self.cfg.mpc, "protected_queue_weight", 0.0))
        if _pq_mv_f and _pq_w_f > 0.0:
            _pq_spec_f = self.cfg.network.urban_movements.get(_pq_mv_f, {})
            _pq_ramp_f = str(_pq_spec_f.get("ramp", "") or "")
            if _pq_ramp_f in model.owned_ramps:
                _pq_max_f = float(getattr(self.cfg.mpc, "protected_queue_max_veh", 50.0))
                _pq_now_f = max(0.0, float(state.urban_movement_queue.get(_pq_mv_f, 0.0)))
                _pq_exc_f = max(0.0, _pq_now_f - _pq_max_f)
                if _pq_exc_f > 0.0:
                    _cap_f = max(float(net.ramp_capacity_veh_h.get(_pq_ramp_f, 1500.0)), 1.0e-9)
                    _rel_f = max(0.0, float(ramp_release.get(_pq_ramp_f, 0.0)))
                    _idle_f = 1.0 - min(1.0, _rel_f / _cap_f)
                    cost += _pq_w_f * _pq_exc_f * _idle_f * (sim.T_c_h)
        smooth = sum(abs(first_vec[i] - prev_vec[i]) for i in range(min(n_seg, len(first_vec))))
        for prev_step, next_step in zip(sequence, sequence[1:]):
            smooth += sum(
                abs(next_step[i] - prev_step[i])
                for i in range(min(len(prev_step), len(next_step), n_seg))
            )
        # PRICE-TR: VSL 가격 활성이면 smoothness 마찰 0(trust ±10km/h가 보폭 제약).
        if not (self.price_smoothness_disabled and self.vsl_marginal_price):
            cost += smooth_w * smooth
        # B3 VSL 가격항(설정 시에만): + w·g·(vsl_seg − ref_seg). 기본 None=완전 휴면.
        if self.vsl_marginal_price:
            for i, value in enumerate(first_vec):
                key = f"{link}__seg{i}"
                g_vsl = self.vsl_marginal_price.get(key)
                if g_vsl is not None and i < len(prev_vec):
                    ref = float(self.vsl_marginal_price_ref.get(key, float(prev_vec[i])))
                    cost += self.vsl_marginal_price_weight * float(g_vsl) * (
                        float(value) - ref
                    )
        # JOINT vsl×metering cross항(설정 시에만): 이 link 소유 ramp의 metering(previous에
        # 고정)과 후보 link-binding VSL(min seg)의 교차. primal joint은 이미 metering
        # best-response로 포착되나, cross 가격이 externality 곡률을 반영한다.
        if self.vsl_meter_cross_price:
            vsl_bind = float(min(first_vec)) if first_vec else vsl_max
            for ramp in model.owned_ramps:
                h_c = self.vsl_meter_cross_price.get(ramp)
                if h_c is None:
                    continue
                m_ref, v_ref = self.vsl_meter_cross_ref.get(ramp, (0.0, vsl_bind))
                m_now = float(previous.ramp_metering.get(ramp, float(m_ref)))
                cost += self.vsl_meter_cross_weight * float(h_c) * (
                    (m_now - float(m_ref)) * (vsl_bind - float(v_ref))
                )
        evals += 1
        max_landing_residual = max(max_landing_residual, landing.ledger['max_abs_residual_veh'])
        if cost < best_obj:
            best_obj, best_vec = cost, list(first_vec)
            best_offramp_flow = dict(first_offramp_flow)
            best_landing = {'ledger': dict(landing.ledger), 'initial_stock_veh': landing.initial_stock,
                            'final_stock_by_link': dict(landing.stock),
                            'replaced_coupling_veh_h': dict(landing.replaced_coupling)}
    # 선택 후보 VSL의 off-ramp 유출 캐시(coupling freeway→urban 재사용).
    if best_obj < float("inf"):
        for off_ramp, flow in best_offramp_flow.items():
            self._wu._last_offramp_flow[off_ramp] = float(flow)
        self._wu._last_offramp_flow[link] = float(sum(best_offramp_flow.values()))
        self._wu._has_last_offramp_flow = True
    else:
        for off_ramp in best_offramp_flow:
            self._wu._last_offramp_flow[off_ramp] = 0.0
        self._wu._last_offramp_flow[link] = 0.0
    diagnostics = getattr(self, '_last_local_landing_diagnostics', {})
    diagnostics[link] = {'candidate_count': evals, 'maximum_candidate_mass_residual_veh': max_landing_residual,
                         'selected': best_landing,
                         'boundary_assumptions': 'External urban inflow and other freeway ramp receiving states frozen; non-W_out receiver finite exit retained.'}
    self._last_local_landing_diagnostics = diagnostics
    vsl_dict: Dict[str, float] = {f"{link}__seg{i}": float(v) for i, v in enumerate(best_vec)}
    vsl_dict[link] = float(min(best_vec)) if best_vec else vsl_max
    return vsl_dict, best_obj, evals
