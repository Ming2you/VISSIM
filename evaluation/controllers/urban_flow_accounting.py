"""Canonical accounted urban methods extracted from the fixed NumSim vendor.

Equations and update order are retained; accepted transfers call one area API.
No runtime AST, source execution, dictionary interception, or vendor mutation.
Installation/adapter branch wrappers are defined below the extracted methods.
"""
from __future__ import annotations
import math
from typing import Dict, Mapping, Tuple
from src.models import urban_queue_model as _uqm
from src.models.state import TrafficState, ControlAction, ExperimentConfig
from src.models.demand import DemandStep
from evaluation.controllers.control_area_objective import (
    emit_transfer, emit_input, integrate_residence, get_ledger,
)
from evaluation.controllers.lane_ramp_runtime import receiving_space as _ramp_receiving_space
from evaluation.controllers.lane_urban_runtime import observe_ready as _lane_ready, is_local_movement

def _resource_ledger(state):
    """Return the optional recorder; ordinary steps collect no resource maps."""
    ledger = get_ledger(state)
    return ledger if ledger is not None and ledger.captures_response else None


def _receive_corridor(state, cfg, movement, vehicles, urban_step_index):
    if getattr(cfg.network, 'known_legsplit_routes', None):
        from evaluation.controllers.route_choice_corridor import known_legsplit_receive
        target = cfg.network.urban_movements[movement].get('receiving_link')
        if target in cfg.network.urban_link_storage_veh:
            known_legsplit_receive(state, cfg, vehicles,
                urban_step_index + _uqm._link_delay_steps(state, cfg, target), movement=movement)
    if getattr(cfg.network, 'native_internal_inputs', None):
        from evaluation.controllers.native_input_prehead import receive_accepted as notify_prehead
        notify_prehead(state, cfg, movement, vehicles, urban_step_index)
        from evaluation.controllers.native_input_routes import receive_accepted
        if receive_accepted(state, cfg, movement, vehicles, urban_step_index):
            return True
    if getattr(cfg.network, 'route_choice_corridor', None):
        from evaluation.controllers.route_choice_corridor import receive_accepted
        if receive_accepted(state, cfg, movement, vehicles, urban_step_index):
            return True
    if getattr(cfg.network, 'sc2001_corridor', None):
        from evaluation.controllers.sc2001_corridor import receive_accepted
        return receive_accepted(state, cfg, movement, vehicles, urban_step_index)
    return False


def _corridor_intended(state, control, cfg, movement, available, urban_step_index, ordinary):
    physical_local=is_local_movement(state,movement)
    if getattr(cfg.network, 'route_choice_corridor', None):
        from evaluation.controllers.route_choice_corridor import intended_departure
        value = intended_departure(state, control, cfg, movement, available, urban_step_index)
        if value is not None:
            ordinary = value
    if getattr(cfg.network, 'native_internal_inputs', None):
        from evaluation.controllers.native_input_prehead import limit_intended
        ordinary = limit_intended(state, cfg, movement, available, ordinary, urban_step_index)
    # Preserve receiver batch preparation, while assigning this movement's
    # actual service exclusively to the physical lane transport's exit.
    return 0. if physical_local else ordinary


def _drain_offramp_storage_accounted(
    state: TrafficState,
    control: ControlAction,
    cfg: ExperimentConfig,
    specs: Mapping[str, Mapping[str, object]],
    step_idx: int,
    routing: Mapping[str, list[tuple[str, float]]],
) -> Dict[str, float]:
    """off-ramp storage(=Wu 식17 off-ramp 큐)를 하류 교차로로 Wu 식3대로 방출한다.

    방출률 = green·포화유율·하류 수용공간의 min. storage 점유를 β로 off_ramp movement에
    나눠, 각 movement의 하류 receiving_link 가용공간에 게이트해 방출한다. 하류가 차면
    방출이 막혀 storage 점유가 누적(spillback) → effective_lane_profile의 λ_eff↓(식22).
    혼잡 해소 시 가용공간 복원으로 정상 방출(점유·λ_eff 복원).

    차량보존: storage occupancy(cap−available)와 movement 큐·하류 링크 점유 모두
    urban_total_vehicles에 포함되므로 storage→하류 링크 이동은 점유 중립이다. 여기서는
    off_ramp movement 큐를 경유하지 않고 storage→receiving_link로 직접 전달한다
    (off_ramp movement는 교차로 stop-line이 아니라 ramp 합류부라 별도 신호 대기 큐가 없다).
    Returns off_ramp별 방출 차량수.
    """
    net = cfg.network
    dt_h = cfg.simulation.T_u_h
    resource_ledger = _resource_ledger(state)
    physical_ports=getattr(state,'lane_offramp_runtime',None)
    if physical_ports is not None:
        return physical_ports.drain(state,control,cfg,step_idx,routing)
    departures: Dict[str, float] = {}
    for off_ramp in net.off_ramps:
        if getattr(state,'lane_urban_runtime',None) is not None and off_ramp == 'OR_F_E':
            continue  # Physical10643 sending and local126 receiving are coupled once.
        storage_link = net.off_ramp_storage_link.get(off_ramp, "")
        if not storage_link or storage_link not in state.urban_link_storage:
            continue
        capacity = float(net.urban_link_storage_veh.get(storage_link, 0.0))
        occupancy = max(0.0, capacity - state.urban_link_storage.get(storage_link, capacity))
        # W6: 점유 중 아직 램프를 통과 중인 몫은 방출 후보에서 뺀다. 도착 substep 이 지난
        # 예약은 지워 자연히 방출 후보로 편입된다(점유 자체는 건드리지 않아 질량 불변).
        occupancy = max(0.0, occupancy - _uqm._mature_offramp_transit(state, storage_link, step_idx))
        if occupancy <= 0.0:
            continue
        movements = [m for m in net.off_ramp_to_movement.get(off_ramp, []) if m in specs]
        released_total = 0.0
        for movement in movements:
            spec = specs[movement]
            beta = float(spec.get("beta", 0.0))
            if beta <= 0.0:
                continue
            cap_flow = _uqm._movement_capacity_flow(control, cfg, movement, spec)
            green_fraction = _uqm._phase_green_fraction(control, cfg, spec, urban_step_index=step_idx)
            # Wu 식3: green·포화유율·(β 몫의 storage 점유)·하류 수용공간의 min.
            intended = min(beta * occupancy, dt_h * green_fraction * cap_flow)
            intended = _corridor_intended(state, control, cfg, movement,
                                         beta * occupancy, step_idx, intended)
            receiving_link = str(spec.get("receiving_link", ""))
            if receiving_link and receiving_link in state.urban_link_storage:
                # S_eff: 하류 링크 점큐 반영(spec §3.3.2, 397행) → off-ramp spillback(식22).
                receiving_space = _uqm._effective_available_space(state, cfg, receiving_link)
                actual = min(intended, receiving_space)
                if resource_ledger is not None:
                    resource_ledger.record_resource_allocation(
                        'offramp_receiving', 'storage:' + receiving_link, receiving_space,
                        {'movement:' + movement: actual})
            else:
                actual = intended
            if resource_ledger is not None:
                sources = {'movement:' + movement: actual}
                resource_ledger.record_resource_allocation('offramp_intended_limit', movement, intended, sources)
                resource_ledger.record_resource_allocation('offramp_source_ready', movement, beta * occupancy, sources)
            if actual <= 0.0:
                continue
            released_total += actual
            emit_transfer(state, cfg, 'storage:' + storage_link, 'storage:' + receiving_link if receiving_link in state.urban_link_storage else None, actual, route_key='movement:' + movement)
            if receiving_link in state.urban_link_storage:
                state.urban_link_storage[receiving_link] = max(
                    0.0,
                    state.urban_link_storage.get(receiving_link, 0.0) - actual,
                )
                if not _receive_corridor(state, cfg, movement, actual, step_idx):
                    delay_steps = _uqm._link_delay_steps(state, cfg, receiving_link)
                    arrival_step = step_idx + delay_steps
                    if receiving_link in routing:
                        _uqm._schedule(state.urban_arrival_buffer, receiving_link, arrival_step, actual)
                    _uqm._schedule(state.urban_storage_release_buffer, receiving_link, arrival_step, actual)
        if released_total > 0.0:
            state.urban_link_storage[storage_link] = min(
                capacity,
                state.urban_link_storage.get(storage_link, 0.0) + released_total,
            )
        departures[off_ramp] = released_total
    return departures


def urban_substep_accounted(
    state: TrafficState,
    control: ControlAction,
    demand: DemandStep,
    cfg: ExperimentConfig,
    urban_step_index: int | None = None,
    ramp_release_veh_h: Mapping[str, float] | None = None,
    defer_legsplit_sinks: bool = False,
) -> Tuple[float, Dict[str, float]]:
    """movement-level horizontal queue를 `T_u` 한 스텝만 전진한다."""
    _uqm.ensure_urban_state(state, cfg)
    resource_ledger = _resource_ledger(state)
    if getattr(cfg.network, 'native_internal_inputs', None):
        from evaluation.controllers.native_input_routes import advance
        advance(state, cfg, _uqm._urban_step_index(state, cfg) if urban_step_index is None else urban_step_index)
        if resource_ledger is not None:
            resource_ledger.complete_constraint_coverage('native_route_queue')
        from evaluation.controllers.native_input_prehead import advance as advance_prehead
        advance_prehead(state, cfg, _uqm._urban_step_index(state, cfg) if urban_step_index is None else urban_step_index)
        if resource_ledger is not None:
            resource_ledger.complete_constraint_coverage('native_prehead_queue')
    choice_diagnostics = {}
    choice = getattr(cfg.network, 'route_choice_corridor', None)
    if choice:
        from evaluation.controllers.route_choice_corridor import advance
        choice_diagnostics = advance(state, control, demand, cfg,
            _uqm._urban_step_index(state, cfg) if urban_step_index is None else urban_step_index)
        if resource_ledger is not None:
            resource_ledger.complete_constraint_coverage('route_choice_allocator')
    if getattr(cfg.network, 'shared_approach', None):
        from evaluation.controllers.shared_approach import advance
        advance(state, control, demand, cfg, _uqm._urban_step_index(state, cfg) if urban_step_index is None else urban_step_index)
    net = cfg.network
    sim = cfg.simulation
    specs = _uqm.movement_specs(cfg)
    diagnostics: Dict[str, float] = {
        "movement_queue_model_active": 1.0,
        "urban_storage_active": 1.0,
        "urban_substep_active": 1.0,
        "onramp_two_reservoir_active": 1.0,
    }
    diagnostics.update({key: value for key, value in choice_diagnostics.items()
                        if isinstance(value, (int, float))})
    initial_accumulation = state.protected_accumulation_veh(cfg.network)
    interval_net_inflow_target = _uqm._control_net_inflow_target_veh_h(control, cfg)
    initial_accumulation_error = 0.0
    overflow_count = 0.0
    projection_count = 0.0
    total_departures_veh = 0.0
    inbound_service_veh = 0.0
    outbound_service_veh = 0.0
    onramp_arrivals_veh = 0.0
    onramp_green_release_request_veh = 0.0
    onramp_green_releases_veh = 0.0
    onramp_green_release_shortfall_veh = 0.0
    ramp_metering_release_request_veh = 0.0
    ramp_metering_releases_veh = 0.0
    ramp_metering_release_shortfall_veh = 0.0
    ramp_metering_request_by_ramp: Dict[str, float] = {ramp: 0.0 for ramp in net.ramps}
    ramp_metering_actual_by_ramp: Dict[str, float] = {ramp: 0.0 for ramp in net.ramps}
    ramp_metering_shortfall_by_ramp: Dict[str, float] = {ramp: 0.0 for ramp in net.ramps}
    off_ramp_departures: Dict[str, float] = {r: 0.0 for r in net.off_ramps}
    step_idx = _uqm._urban_step_index(state, cfg) if urban_step_index is None else urban_step_index
    from evaluation.controllers import head_service_resources
    head_resource_context = head_service_resources.regular_context(cfg, control, step_idx)
    routing = _uqm.approach_routing(cfg)
    sink_links = _uqm.sink_storage_links(cfg)
    choice_storages = set(choice['capacity_veh']) if choice else set()
    if choice_storages:
        sink_links = set(sink_links) - choice_storages
    corridor = getattr(net, 'sc2001_corridor', None)
    if corridor:
        from evaluation.controllers.sc2001_corridor import advance
        corridor_diagnostics = advance(state, control, demand, cfg, step_idx)
        diagnostics.update({key: value for key, value in corridor_diagnostics.items()
                            if isinstance(value, (int, float))})
        sink_links = set(sink_links) - {corridor['storage']}
    boundary_out_sink_veh = 0.0
    boundary_out_ramp_blocked_veh = 0.0
    boundary_out_ramp_released_veh = 0.0
    urban_gate_inflow_veh = 0.0
    urban_demand_arrivals_veh = 0.0
    if getattr(net, 'native_internal_inputs', None):
        from evaluation.controllers.native_internal_input import advance
        native_rows = advance(state, control, demand, cfg, step_idx)['native_internal_input_step']
        if resource_ledger is not None:
            resource_ledger.complete_constraint_coverage('native_input_generation')
        for input_no, row in native_rows.items():
            diagnostics.update({f'native_internal_{input_no}_{key}': value for key, value in row.items()})
            urban_demand_arrivals_veh += row['generated_inside_veh']

    for link in net.urban_link_storage_veh:
        if link in choice_storages:
            continue
        if corridor and link == corridor['storage']:
            continue
        released = _uqm._pop_buffer(state.urban_storage_release_buffer, link, step_idx)
        if released > 0.0:
            # sink(boundary_out) 링크는 release pop에서 available을 복원하지 않는다 —
            # 차량은 out 링크 점유 상태로 남아(in-transit→링크 끝 대기) 아래 유한 출구용량
            # 게이트가 cap만큼만 이탈시킨다(A″-1). available을 복원하면 점유가 사라져
            # (a) receiving 게이트에 backup이 안 잡히고 (b) sink로 기록되지 않아 차량이
            # 소멸한다(보존 위반). 내부 링크는 기존대로 복원해 다음 노드로 이동시킨다.
            if link in sink_links or link in getattr(net,'lane_plant_tail_stores',()):
                continue
            cap = net.urban_link_storage_veh[link]
            state.urban_link_storage[link] = min(cap, state.urban_link_storage.get(link, cap) + released)

    # 유한 출구용량(A″-1): 각 boundary_out 링크에서 시스템을 떠나는 유량을
    # min(out 링크 점유, exit_capacity·dt)로 제약한다(모델 밖 하류 도로 용량). 못 나간
    # 차량은 out 링크 storage에 남아(보존) 점유가 누적되고, 그 점유가
    # `_effective_available_space`(receiving 게이트)에 반영돼 exit movement가 막히면서
    # backup이 grid로 전파된다(S_eff 일관). 자유 sink 시절엔 도착 즉시 전량 이탈해
    # off-ramp 홍수가 urban을 포화시키지 못했다(roadmap §3).
    exit_capacity_veh_h = float(net.boundary_out_capacity_veh_h)
    finite_exit = exit_capacity_veh_h > 0.0
    exit_capacity_veh = exit_capacity_veh_h * sim.T_u_h
    # 램프행 이탈 분할(2026-09-01). `boundary_out_ramp_split` 이 없으면 종전과 비트 동일.
    #
    # 왜. 경계 out 링크 중 일부는 하류가 **on-ramp** 다(SC1001_W_out -> 링크 31 ->
    # 미터 10480 R_D_W · 10484 R_D_E). 그 몫은 모델 밖 도로가 아니라 램프 저수지와
    # 미터가 받는데, 지금은 전부 `boundary_out_capacity_veh_h`(일괄 1600 vph)로 자유
    # 이탈한다 — 램프가 꽉 차도 도시 쪽은 아무 제약을 못 느낀다.
    #
    # 그래서 이탈을 목적지별로 쪼개고 램프행에만 동적 용량을 건다:
    #     ramp_exit_cap = min(ramp_space, metering_release x T_u_h)
    #     ramp_space    = ramp_queue_cap(r) - w_r      (램프별 상한. 스칼라 180 이 아니다)
    # 못 나간 차량은 out 링크 storage 에 남아 점유가 누적되고, 그 점유가
    # `_effective_available_space` -> receiving 게이트로 상류 exit movement 를 막아
    # backup 이 grid 로 전파된다. 그 잔류는 kind=boundary_out 이므로 protected_kinds 에
    # 들어가 far 도시항 n_u^2 에도 실린다(램프 큐는 far 램프항에 따로 실린다 — 서로 다른
    # 차량이라 이중계상이 아니다).
    #
    # **램프 저수지에 더하지 않는다.** 본선 램프 유입은 `demand.ramp_arrival`(관측 기반)로
    # 이미 외생 계상돼 있어 여기서 또 넣으면 이중 주입이다. 여기서는 **제약만** 건다.
    #
    # 저류는 쪼개지 않는다(사용자 결정). 링크 31 은 하나의 도로이고 램프는 그 도중에
    # 갈라지므로, 램프행 잔류가 통과 차량의 가용공간도 같이 줄이는 것이 실제 거동이다.
    ramp_split = dict(getattr(net, "boundary_out_ramp_split", {}) or {})
    # Deterministic physical sink traversal, including floating accumulation
    # order and appended transfer/resource evidence, across spawned processes.
    for link in sorted(sink_links):
        if defer_legsplit_sinks and link in ramp_split:
            continue  # The wrapper performs one explicit accepted W_out transfer.
        cap = net.urban_link_storage_veh.get(link, net.boundary_queue_max_veh)
        occupancy = max(0.0, cap - state.urban_link_storage.get(link, cap))
        # N3-2: 점유에는 **방금 out 링크에 진입해 아직 링크 끝에 못 간 차량**이 섞여 있다.
        # 그 몫(= release buffer 에 남은 미래 도착 예약)을 빼야 게이트가 도착한 차량만
        # 내보낸다. 빼기 전에는 진입 substep 에 곧바로 이탈해 out 링크 통행시간이 0 이었다
        # (실런 core15n41 · 120 substep 실측: 빼기 전 26,311.59 veh 이탈 → 뺀 뒤 22,620.52,
        # 차이 3,691.07 veh 가 링크를 다 못 가고 나가던 몫이다). 점유 자체는 건드리지
        # 않으므로 질량 회계는 불변이고, W6 의 off-ramp 처리와 같은 구조다.
        arrived = max(0.0, occupancy - _uqm._pending_in_transit(
            state.urban_storage_release_buffer, link, step_idx
        ))
        # 유한용량이면 min(도착분, exit_cap·dt), 0 이하이면 자유 sink(도착분 전량 이탈, 하위호환).
        departed = min(arrived, exit_capacity_veh) if finite_exit else arrived
        split = ramp_split.get(link)
        if split and arrived > 0.0:
            # 목적지별로 쪼개 각자 자기 용량에 건다. free 몫은 종전 exit_capacity 그대로.
            free_share = max(0.0, float(split.get("free", 0.0)))
            free_in = arrived * free_share
            departed = min(free_in, exit_capacity_veh) if finite_exit else free_in
            if resource_ledger is not None:
                resource_ledger.record_resource_allocation('sink_free_ready', link, free_in, {'sink:' + link: departed})
                if finite_exit:
                    resource_ledger.record_resource_allocation('sink_exit_capacity', link, exit_capacity_veh, {'sink:' + link: departed})
            for ramp, share in (split.get("ramps") or {}).items():
                ramp_in = arrived * max(0.0, float(share))
                if ramp_in <= 0.0:
                    continue
                cap_r = (net.ramp_queue_cap(str(ramp))
                         if hasattr(net, "ramp_queue_cap") else float(net.ramp_queue_max_veh))
                space = max(0.0, cap_r - max(0.0, state.ramp_queue.get(str(ramp), 0.0)))
                meter = float((ramp_release_veh_h or {}).get(str(ramp), 0.0)) * sim.T_u_h
                ramp_exit_cap = min(space, max(0.0, meter))
                allowed = min(ramp_in, ramp_exit_cap)
                if resource_ledger is not None:
                    sources = {'sink:' + link + ':ramp:' + str(ramp): allowed}
                    resource_ledger.record_resource_allocation('sink_ramp_ready', link + ':' + str(ramp), ramp_in, sources)
                    resource_ledger.record_resource_allocation('sink_ramp_entry_limit', link + ':' + str(ramp), ramp_exit_cap, sources)
                departed += allowed
                boundary_out_ramp_blocked_veh += max(0.0, ramp_in - allowed)
                boundary_out_ramp_released_veh += allowed
        elif resource_ledger is not None:
            sources = {'sink:' + link: departed}
            resource_ledger.record_resource_allocation('sink_ready', link, arrived, sources)
            if finite_exit:
                resource_ledger.record_resource_allocation('sink_exit_capacity', link, exit_capacity_veh, sources)
        if departed <= 0.0:
            continue
        state.urban_link_storage[link] = min(cap, state.urban_link_storage.get(link, cap) + departed)
        boundary_out_sink_veh += departed
        if not (getattr(net, 'leg_ramp_split_enabled', False) and link in ramp_split):
            emit_transfer(state, cfg, 'storage:' + link, None, departed, route_key='sink:' + link, target_inside=False)

    # arrival = "다음 노드 도착 → β분할" (spec §3.3.5). 1:1 next_movement 체인이 아님.
    for source, targets in routing.items():
        if source in choice_storages:
            continue
        if corridor and source == corridor['storage']:
            continue
        arrived = _uqm._pop_buffer(state.urban_arrival_buffer, source, step_idx)
        local=getattr(state,'lane_urban_runtime',None)
        if local is not None and source==local.origin:
            local.consume_upstream(state,cfg,step_idx,arrived)
            continue
        if hasattr(net,'physical_ramp_branches'):
            from evaluation.controllers.physical_ramp_branches import split_tagged_arrival
            city_spec = net.physical_ramp_branches.get('shared_city_arrival',{})
            city_amount = (getattr(state,'shared_approach_state',{}).get('city_arrival_tags',{}).get(step_idx,0.)
                           if source == city_spec.get('receiver') else 0.)
            tagged=split_tagged_arrival(state,cfg,source,step_idx,arrived,targets)
            if tagged is not None:
                for movement,amount in tagged:
                    state.urban_movement_queue[movement]+=amount
                    _lane_ready(state,cfg,movement,amount,
                        city_amount=city_amount*city_spec['conditional_shares'].get(movement,0.))
                    emit_transfer(state,cfg,'storage:'+source,'movement:'+movement,amount,route_key='arrival:'+movement)
                continue
        if arrived <= 0.0:
            continue
        for movement, beta in targets:
            state.urban_movement_queue[movement] += beta * arrived
            _lane_ready(state,cfg,movement,beta*arrived)
            emit_transfer(state, cfg, 'storage:' + source, 'movement:' + movement, beta * arrived, route_key='arrival:' + movement)

    # 게이트 수요는 그 교차로에 "해당 방향에서 도착"으로 주입 후 동일 β분할. 단 게이트를
    # 넘은 차량은 in링크를 통과해야 정지선에 닿으므로 _inflow_delay_steps 만큼 지연한다(W6).
    # 주입 substep 에 바로 큐에 넣던 것이 순간이동이었다.
    inflow_delay = _uqm._inflow_delay_steps(cfg)
    for origin in net.boundary_in_links:
        landed = _uqm._pop_buffer(state.urban_inflow_transit_buffer, f"gate:{origin}", step_idx)
        if landed > 0.0:
            for movement, beta in routing.get(origin, []):
                state.urban_movement_queue[movement] += beta * landed
                _lane_ready(state,cfg,movement,beta*landed)
                emit_transfer(state, cfg, 'transit:gate:' + origin, 'movement:' + movement, beta * landed, route_key='arrival:' + movement)
        arrival = demand.urban_boundary.get(origin, 0.0) * sim.T_u_h
        targets = routing.get(origin, [])
        if arrival <= 0.0 or not targets:
            continue
        # 외부 유입 계상은 게이트 통과 시점이다(질량 장부의 accepted_external). 그 사이
        # 차량은 urban_inflow_transit_buffer 에 있고 total_physical_vehicles 가 센다.
        urban_demand_arrivals_veh += arrival
        emit_input(state, cfg, 'transit:gate:' + origin, arrival, route_key='input:gate:' + origin)
        _uqm._schedule(
            state.urban_inflow_transit_buffer,
            f"gate:{origin}",
            step_idx + inflow_delay,
            arrival,
        )

    # 외생 on-ramp 수요는 먼저 urban 접근부 저수지 x_on(해당 ramp의 on_ramp movement들)에 쌓인다.
    # 접근부 링크 주행지연은 게이트 수요와 동일하게 적용한다(W6).
    for ramp, movements in net.on_ramp_to_movement.items():
        landed = _uqm._pop_buffer(state.urban_inflow_transit_buffer, f"ramp:{ramp}", step_idx)
        if landed > 0.0 and movements:
            landed_share = landed / len(movements)
            for movement in movements:
                state.urban_movement_queue[movement] = (
                    state.urban_movement_queue.get(movement, 0.0) + landed_share
                )
                emit_transfer(state, cfg, 'transit:ramp:' + ramp, 'movement:' + movement, landed_share, route_key='arrival:' + movement)
        arrival = max(0.0, demand.ramp_arrival.get(ramp, 0.0)) * sim.T_u_h
        if arrival <= 0.0 or not movements:
            continue
        _uqm._schedule(
            state.urban_inflow_transit_buffer,
            f"ramp:{ramp}",
            step_idx + inflow_delay,
            arrival,
        )
        onramp_arrivals_veh += arrival
        emit_input(state, cfg, 'transit:ramp:' + ramp, arrival, route_key='input:ramp:' + ramp)

    # ramp metering은 freeway ramp 저수지 w_r에서 freeway로 빠져나가는 흐름이다.
    if ramp_release_veh_h is not None:
        for ramp, release_flow in ramp_release_veh_h.items():
            requested = max(0.0, release_flow) * sim.T_u_h
            before = max(0.0, state.ramp_queue.get(ramp, 0.0))
            physical = getattr(state, 'lane_ramp_runtime', None)
            if physical is not None:
                if physical.predebited is None or abs(requested-physical.predebited[ramp]*sim.T_u_h) > 1e-8:
                    raise ValueError('Urban meter interface differs from accepted physical merge')
                actual = requested
                if resource_ledger is not None:
                    resource_ledger.record_resource_allocation('urban_physical_merge_receipt', ramp,
                        requested, {'ramp:'+ramp:actual})
            else:
                actual = min(before, requested)
                if resource_ledger is not None:
                    sources = {'ramp:' + ramp: actual}
                    resource_ledger.record_resource_allocation('urban_meter_release_stock', ramp, before, sources)
                    resource_ledger.record_resource_allocation('urban_meter_release_request', ramp, requested, sources)
                state.ramp_queue[ramp] = max(0.0, before - actual)
                emit_transfer(state, cfg, 'ramp:' + ramp, 'merge_pending:' + ramp, actual, preserve_area=True)
            shortfall = max(0.0, requested - actual)
            ramp_metering_release_request_veh += requested
            ramp_metering_releases_veh += actual
            ramp_metering_release_shortfall_veh += shortfall
            ramp_metering_request_by_ramp[ramp] = ramp_metering_request_by_ramp.get(ramp, 0.0) + requested
            ramp_metering_actual_by_ramp[ramp] = ramp_metering_actual_by_ramp.get(ramp, 0.0) + actual
            ramp_metering_shortfall_by_ramp[ramp] = ramp_metering_shortfall_by_ramp.get(ramp, 0.0) + shortfall

    # urban green은 접근부 저수지(x_on, ramp행 movement들)에서 freeway ramp 저수지 w_r로
    # 보내는 흐름이다. ramp는 sink가 아니라 freeway로의 transfer(차량 보존).
    ramp_requests: Dict[str, Dict[str, float]] = {}
    for movement, spec in specs.items():
        ramp = str(spec.get("ramp", ""))
        if not ramp:
            continue
        available = max(0.0, state.urban_movement_queue.get(movement, 0.0))
        cap_flow = _uqm._movement_capacity_flow(control, cfg, movement, spec)
        green_fraction = _uqm._phase_green_fraction(control, cfg, spec, urban_step_index=step_idx)
        ramp_requests.setdefault(ramp, {})[movement] = min(
            available,
            sim.T_u_h * green_fraction * cap_flow,
        )
    for ramp, requests in ramp_requests.items():
        requested_total = sum(requests.values())
        # 램프별 상한. 스칼라 180 은 네 램프 실제값(111.2~174.5) 모두보다 커서
        # 차단이 늦게 시작되고 도시 역류를 과소평가한다.
        _cap_sp = (net.ramp_queue_cap(ramp) if hasattr(net, "ramp_queue_cap")
                   else float(net.ramp_queue_max_veh))
        ramp_space = _ramp_receiving_space(state, cfg, ramp)
        scale = 1.0 if requested_total <= ramp_space else ramp_space / max(requested_total, 1.0e-9)
        released_total = 0.0
        accepted_sources = {} if resource_ledger is not None else None
        for movement, requested in requests.items():
            actual = requested * scale
            before = max(0.0, state.urban_movement_queue.get(movement, 0.0))
            actual = min(before, actual)
            if accepted_sources is not None:
                accepted_sources['movement:' + movement] = actual
                resource_ledger.record_resource_allocation('urban_ramp_movement_intended', movement,
                    requested, {'movement:' + movement: actual})
                resource_ledger.record_resource_allocation('urban_ramp_movement_stock', movement,
                    before, {'movement:' + movement: actual})
            state.urban_movement_queue[movement] = max(0.0, before - actual)
            released_total += actual
            emit_transfer(state, cfg, 'movement:' + movement, 'ramp:' + ramp, actual, target_inside=True, route_key='movement:' + movement)
            total_departures_veh += actual
            outbound_service_veh += actual
            if str(specs[movement].get("kind", "")) in {"boundary_in", "off_ramp"}:
                # 게이트에서 곧장 ramp로 가는 movement는 perimeter 유입이기도 하다.
                inbound_service_veh += actual
        if resource_ledger is not None:
            resource_ledger.record_resource_allocation(
                'urban_ramp_receiving', 'ramp:' + ramp, ramp_space, accepted_sources)
        # 램프별 상한(2026-09-01). 스칼라 180 을 쓰면 METANET 과 어긋나 `min` 이 차량을
        # 소멸시킨다(실측 192 대 180 = 12대). 두 갱신자가 같은 상한을 봐야 보존이 닫힌다.
        _cap_r = (net.ramp_queue_cap(ramp) if hasattr(net, "ramp_queue_cap")
                  else float(net.ramp_queue_max_veh))
        state.ramp_queue[ramp] = min(
            _cap_r,
            max(0.0, state.ramp_queue.get(ramp, 0.0) + released_total),
        )
        onramp_green_release_request_veh += requested_total
        onramp_green_releases_veh += released_total
        onramp_green_release_shortfall_veh += max(0.0, requested_total - released_total)

    # off-ramp storage(=Wu 식17 큐)를 하류 receiving 공간에 게이트해 방출(Wu 식3). 하류
    # 정체 시 방출이 막혀 storage 점유 누적(spillback)→λ_eff↓(식22). stage 2 전에 실행해
    # 같은 substep의 하류 가용공간을 두 흐름이 공유하게 한다.
    drained = _drain_offramp_storage_accounted(state, control, cfg, specs, step_idx, routing)
    for off_ramp, released in drained.items():
        off_ramp_departures[off_ramp] = off_ramp_departures.get(off_ramp, 0.0) + released
        total_departures_veh += released
        inbound_service_veh += released  # off-ramp 합류 = perimeter 유입.

    intended_by_storage: Dict[str, Dict[str, float]] = {}
    no_storage_intended: Dict[str, float] = {}
    movement_limits = {} if resource_ledger is not None else None
    for movement, spec in specs.items():
        if str(spec.get("ramp", "")):
            continue  # ramp행 movement는 위 transfer 루프에서 처리됨.
        if str(spec.get("kind", "")) == "off_ramp":
            continue  # off_ramp movement는 _drain_offramp_storage가 storage에서 직접 방출.
        available = max(0.0, state.urban_movement_queue.get(movement, 0.0))
        cap_flow = _uqm._movement_capacity_flow(control, cfg, movement, spec)
        green_fraction = _uqm._phase_green_fraction(control, cfg, spec, urban_step_index=step_idx)
        intended = min(available, sim.T_u_h * green_fraction * cap_flow)
        intended = _corridor_intended(state, control, cfg, movement,
                                     available, step_idx, intended)
        if movement_limits is not None:
            movement_limits[movement] = (available, intended)
        receiving_link = str(spec.get("receiving_link", ""))
        if receiving_link and receiving_link in state.urban_link_storage:
            intended_by_storage.setdefault(receiving_link, {})[movement] = intended
        else:
            no_storage_intended[movement] = intended

    actual_departure: Dict[str, float] = dict(no_storage_intended)
    receiving_evidence = {} if resource_ledger is not None else None
    head_accepted = {} if resource_ledger is not None else None
    if (getattr(net, 'sdmpc_options', None) or {}).get('spatial_receiving'):
        from evaluation.controllers.sdmpc_tangent_spatial import regular_receivers
        receivers = regular_receivers(state, cfg, intended_by_storage, step_idx,
                                      head_resource_context, _uqm)
        for storage_link, intended, available_space, accepted in receivers:
            if receiving_evidence is not None:
                receiving_evidence[storage_link] = (available_space, {'movement:' + m: 0.0 for m in intended})
            actual_departure.update(accepted)
    else:
        for storage_link, intended in intended_by_storage.items():
            if choice:
                from evaluation.controllers.route_choice_corridor import limit_intended_batch
                intended = limit_intended_batch(state, cfg, intended, step_idx)
            intended = head_service_resources.regular_batch(cfg, intended, head_resource_context)
            # S_eff: 하류 링크 끝 점큐를 점유로 반영(spec §3.3.2, 397행) → backup 전파.
            available_space = _uqm._effective_available_space(state, cfg, storage_link)
            if receiving_evidence is not None:
                receiving_evidence[storage_link] = (available_space, {'movement:' + m: 0.0 for m in intended})
            actual_departure.update(_uqm._allocate_receiving_counts(
                cfg.urban_follower.receiving_space_rule,
                intended,
                available_space,
            ))

    for movement, departed in actual_departure.items():
        if movement_limits is not None:
            available, intended = movement_limits[movement]
            # Record the final actual min, including zero-service phases. The
            # route-owned replacement limit is not the overridden legacy cap.
            amount = min(state.urban_movement_queue.get(movement, 0.0), departed)
            sources = {'movement:' + movement: amount}
            resource_ledger.record_resource_allocation('urban_movement_stock', movement, available, sources)
            resource_ledger.record_resource_allocation('urban_movement_intended_limit', movement, intended, sources)
        if departed <= 0.0:
            continue
        spec = specs[movement]
        before = state.urban_movement_queue.get(movement, 0.0)
        actual = min(before, departed)
        head_service_resources.regular_accepted(movement, actual, head_resource_context)
        receiving_key = str(spec.get('receiving_link', ''))
        if receiving_evidence is not None:
            if receiving_key in receiving_evidence:
                receiving_evidence[receiving_key][1]['movement:' + movement] = actual
            if movement in head_resource_context[2]:
                head_accepted[movement] = actual
        emit_transfer(state, cfg, 'movement:' + movement, 'storage:' + receiving_key if receiving_key in state.urban_link_storage else None, actual, route_key='movement:' + movement)
        total_departures_veh += actual
        state.urban_movement_queue[movement] = max(0.0, before - actual)
        receiving_link = str(spec.get("receiving_link", ""))
        if receiving_link in state.urban_link_storage:
            state.urban_link_storage[receiving_link] = max(
                0.0,
                state.urban_link_storage.get(receiving_link, 0.0) - actual,
            )
            if not _receive_corridor(state, cfg, movement, actual, step_idx):
                delay_steps = _uqm._link_delay_steps(state, cfg, receiving_link)
                arrival_step = step_idx + delay_steps
                # 내부 링크면 다음 교차로 approach buffer로(도착 시 β분할), sink 링크면 release만.
                if receiving_link in routing:
                    _uqm._schedule(state.urban_arrival_buffer, receiving_link, arrival_step, actual)
                _uqm._schedule(state.urban_storage_release_buffer, receiving_link, arrival_step, actual)
        if spec.get("kind") == "off_ramp":
            off_ramp = str(spec.get("off_ramp", ""))
            off_ramp_departures[off_ramp] = off_ramp_departures.get(off_ramp, 0.0) + actual
            inbound_service_veh += actual
        elif spec.get("kind") == "boundary_in":
            inbound_service_veh += actual
            urban_gate_inflow_veh += actual
        elif spec.get("kind") == "boundary_out":
            outbound_service_veh += actual

    if resource_ledger is not None:
        for storage_link, (available_space, accepted_sources) in receiving_evidence.items():
            resource_ledger.record_resource_allocation(
                'regular_receiving', 'storage:' + storage_link, available_space, accepted_sources)
        # Only this regular-head context is owned here. Route-choice/native head
        # budgets in other modules remain outside this partial evidence coverage.
        limits, used, members = head_resource_context
        for group, limit in limits.items():
            accepted_sources = {'movement:' + m: head_accepted[m]
                                for m in head_accepted if members[m] == group}
            # Match the kernel's accepted debit, not its earlier intended flow.
            if sum(accepted_sources.values()) != used.get(group, 0.0):
                raise ValueError('Regular head evidence differs from accepted debit: ' + str(group))
            resource_ledger.record_resource_allocation(
                'regular_shared_head', str(group), limit, accepted_sources)

    if getattr(net, 'native_internal_inputs', None):
        from evaluation.controllers.native_input_prehead import finish_step
        diagnostics.update(finish_step(state, control, cfg, step_idx))
        if resource_ledger is not None:
            resource_ledger.complete_constraint_coverage('native_prehead_residual')

    projection_protected_veh = 0.0
    protected_queue_kinds = {"internal", "boundary_out", "off_ramp"}
    for movement, spec in specs.items():
        qmax = _uqm._queue_max(cfg, movement, spec)
        q = state.urban_movement_queue.get(movement, 0.0)
        if q > qmax:
            overflow_count += 1.0
            projection_count += q - qmax
            if str(spec.get("kind", "")) in protected_queue_kinds:
                projection_protected_veh += q - qmax
            state.urban_movement_queue[movement] = qmax
            emit_transfer(state, cfg, 'movement:' + movement, 'projection_loss:' + movement, q - qmax, preserve_area=True, route_key='queue_projection_loss')
        if resource_ledger is not None:
            resource_ledger.record_state_upper_bound('urban_queue_after_existing_projection', movement,
                state.urban_movement_queue.get(movement, 0.0), qmax)

    # off-ramp 램프 storage 점유는 freeway로 재귀속(design 2026-06-17). _storage_occupancy가
    # 이미 제외하므로 urban_ttt에서 자동으로 빠진다. 그 양의 TTT는 진단으로 노출해 coupling이
    # freeway_ttt에 더한다(보존: urban에서 빠진 양 = freeway에 더해지는 양, 같은 T_u_h 단위).
    offramp_storage_occupancy = _uqm._offramp_storage_occupancy(state, cfg)
    offramp_storage_ttt = offramp_storage_occupancy * sim.T_u_h
    uncontrolled_node_movement = state.uncontrolled_node_movement_queue_veh(net)
    uncontrolled_node_storage = state.uncontrolled_node_storage_occupancy_veh(net)
    uncontrolled_node_vehicles = uncontrolled_node_movement + uncontrolled_node_storage
    urban_ttt = (
        sum(state.urban_movement_queue.values())
        + _uqm._storage_occupancy(state, cfg)
    ) * sim.T_u_h

    _uqm._sync_legacy_queues(state, cfg)
    inbound = inbound_service_veh / max(sim.T_u_h, 1.0e-9)
    outbound = outbound_service_veh / max(sim.T_u_h, 1.0e-9)
    net_inflow = inbound - outbound
    accumulation_error = 0.0
    net_inflow_error = abs(net_inflow - interval_net_inflow_target)
    diagnostics["inbound_service_veh"] = float(inbound_service_veh)
    diagnostics["outbound_service_veh"] = float(outbound_service_veh)
    diagnostics["urban_total_departures_veh"] = float(total_departures_veh)
    diagnostics["net_inflow"] = float(net_inflow)
    diagnostics["net_inflow_target"] = float(interval_net_inflow_target)
    diagnostics["urban_net_inflow_target_veh_h"] = float(interval_net_inflow_target)
    diagnostics["urban_accumulation_initial_veh"] = float(initial_accumulation)
    diagnostics["urban_accumulation_initial_error_veh"] = float(initial_accumulation_error)
    diagnostics["urban_accumulation_veh"] = float(state.protected_accumulation_veh(cfg.network))
    diagnostics["urban_accumulation_target_disabled"] = 1.0
    diagnostics["urban_accumulation_target_veh"] = 0.0
    diagnostics["urban_accumulation_error_veh"] = float(accumulation_error)
    diagnostics["urban_accumulation_abs_error_veh"] = abs(float(accumulation_error))
    diagnostics["urban_net_inflow_tracking_error_veh_h"] = float(net_inflow_error)
    diagnostics["net_inflow_tracking_error"] = float(net_inflow_error)
    diagnostics.update(_uqm.movement_balance_summary(
        state,
        cfg,
        saturation_fraction=cfg.evaluation.boundary_degenerate_saturation_fraction,
        degenerate_ratio=cfg.evaluation.boundary_degenerate_ratio,
        eps=cfg.evaluation.eps,
    ))
    diagnostics.update(_uqm.boundary_indices(state.boundary_queue.values(), net.boundary_queue_max_veh))
    diagnostics["queue_overflow_count"] = float(overflow_count)
    diagnostics["movement_queue_projection_veh"] = float(projection_count)
    diagnostics["movement_queue_projection_protected_veh"] = float(projection_protected_veh)
    diagnostics["urban_storage_occupancy"] = _uqm._storage_occupancy(state, cfg)
    diagnostics["urban_link_occupancy_veh"] = _uqm._storage_occupancy(state, cfg)
    diagnostics["urban_uncontrolled_node_movement_queue_veh"] = float(uncontrolled_node_movement)
    diagnostics["urban_uncontrolled_node_storage_occupancy_veh"] = float(uncontrolled_node_storage)
    diagnostics["urban_uncontrolled_node_vehicles_veh"] = float(uncontrolled_node_vehicles)
    diagnostics["urban_uncontrolled_node_ttt"] = float(uncontrolled_node_vehicles * sim.T_u_h)
    # off-ramp 램프 storage 재귀속(design 2026-06-17): freeway_ttt로 보낼 점유·TTT.
    diagnostics["offramp_storage_occupancy_veh"] = float(offramp_storage_occupancy)
    diagnostics["offramp_storage_ttt"] = float(offramp_storage_ttt)
    # 보존 회계(proposal §8): 유입(게이트 service + off_ramp 복귀 + 외생 ramp 수요)
    # = 이탈(boundary_out sink + on_ramp 전이) + Δ누적. off_ramp 복귀는 coupling에서 집계.
    diagnostics["urban_gate_inflow_veh"] = float(urban_gate_inflow_veh)
    diagnostics["urban_demand_arrivals_veh"] = float(urban_demand_arrivals_veh)
    diagnostics["boundary_out_sink_veh"] = float(boundary_out_sink_veh)
    # 램프행 이탈 게이트(2026-09-01). 분할이 없으면 둘 다 0.0 이라 종전과 구분된다.
    diagnostics["boundary_out_ramp_blocked_veh"] = float(boundary_out_ramp_blocked_veh)
    diagnostics["boundary_out_ramp_released_veh"] = float(boundary_out_ramp_released_veh)
    diagnostics["urban_total_vehicles_veh"] = float(
        sum(state.urban_movement_queue.values()) + _uqm._storage_occupancy(state, cfg)
    )
    diagnostics["onramp_arrivals_veh"] = float(onramp_arrivals_veh)
    diagnostics["onramp_green_release_request_veh"] = float(onramp_green_release_request_veh)
    diagnostics["onramp_green_releases_veh"] = float(onramp_green_releases_veh)
    diagnostics["onramp_green_release_shortfall_veh"] = float(onramp_green_release_shortfall_veh)
    diagnostics["ramp_metering_release_request_veh"] = float(ramp_metering_release_request_veh)
    diagnostics["ramp_metering_releases_veh"] = float(ramp_metering_releases_veh)
    diagnostics["ramp_metering_release_shortfall_veh"] = float(ramp_metering_release_shortfall_veh)
    for ramp in net.ramps:
        diagnostics[f"ramp_metering_release_request_{ramp}_veh"] = float(
            ramp_metering_request_by_ramp.get(ramp, 0.0)
        )
        diagnostics[f"ramp_metering_release_actual_{ramp}_veh"] = float(
            ramp_metering_actual_by_ramp.get(ramp, 0.0)
        )
        diagnostics[f"ramp_metering_release_shortfall_{ramp}_veh"] = float(
            ramp_metering_shortfall_by_ramp.get(ramp, 0.0)
        )
    diagnostics["onramp_approach_queue_veh"] = float(sum(
        state.urban_movement_queue.get(movement, 0.0)
        for movements in net.on_ramp_to_movement.values()
        for movement in movements
    ))
    diagnostics["ramp_queue_veh"] = float(sum(state.ramp_queue.values()))
    diagnostics["offramp_departures_veh"] = float(sum(off_ramp_departures.values()))
    for off_ramp, value in off_ramp_departures.items():
        diagnostics[f"offramp_departures_{off_ramp}_veh"] = float(value)
    if resource_ledger is not None:
        resource_ledger.complete_constraint_coverage('urban_allocator')
    return float(urban_ttt), diagnostics


def legsplit_substep_accounted(state, control, demand, cfg_arg, urban_step_index=None, ramp_release_veh_h=None):
    net_a = cfg_arg.network
    table = dict(getattr(net_a, "boundary_out_ramp_split", {}) or {})
    if not table or not bool(getattr(net_a, "leg_ramp_split_enabled", False)):
        return urban_substep_accounted(state, control, demand, cfg_arg, urban_step_index=urban_step_index,
                             ramp_release_veh_h=ramp_release_veh_h)
    rel = ramp_release_veh_h
    if rel is None:
        rel = dict(getattr(control, "ramp_metering", {}) or {})
    sim = cfg_arg.simulation
    # B3 (2026-09-05): 꼬리 sink(<SC>_W_tail)의 통과속도. vendor _link_delay_steps 는 관측속도가 없으면
    # 전역 urban_avg_speed 로 "가용공간×6 m" 를 통과시켜 빈 꼬리(200대=1.2 km)가 수백 초 이동 중이 된다.
    # W_out 의 관측 유효속도를 그대로 준다(같은 도로의 하류 구간).
    spd_map = getattr(state, "urban_link_speed_kph", None)
    if isinstance(spd_map, dict):
        for link in table:
            tail = str(link).replace("_W_out", "_W_tail")
            if tail in net_a.urban_link_storage_veh and spd_map.get(str(link)) and not spd_map.get(tail):
                spd_map[tail] = float(spd_map[str(link)])
    idx = _uqm._urban_step_index(state, cfg_arg) if urban_step_index is None else int(urban_step_index)
    resource_ledger = _resource_ledger(state)
    leg_limits = {} if resource_ledger is not None else None
    # ---- B1''' (2026-09-05 19:1x): W_out 인출을 τ 도착량 기준으로 래퍼가 정한다 ----
    # vendor 블록(:1053-1083)의 두 결함: (1) 램프 진입 상한이 min(공간, 미터방출)인데 미터방출은 저수지
    # 큐가 있어야 생겨서 빈 저수지엔 못 들어가는 교착, (2) 자유 진출이 share×재고를 매 substep 다시
    # 계산해 1,600 vph 로 재고 전체(램프행 포함)를 빼간다. 여기서는 이번 substep 에 링크 끝에 닿는
    # 양(reach)만 목적지별로 나눈다. 일반 sink 인출은 이 래퍼에서만 유예하며, 도시 본문 실행 뒤
    # 실제 수신 여유를 다시 확인한 accepted 양만 원 저장고에서 한 번 빼고 목적지로 옮긴다.
    inject: dict[str, float] = {}
    accepted_transfers = []
    from evaluation.controllers.route_choice_corridor import known_legsplit_requests, known_legsplit_commit
    adjust: dict[str, float] = {}   # source link -> accepted departures freeing its storage
    exit_cap_h = float(getattr(net_a, "boundary_out_capacity_veh_h", 0.0) or 0.0)
    finite_exit = exit_cap_h > 0.0
    conn_caps = dict(getattr(net_a, "ramp_capacity_veh_h", {}) or {})
    for link, spec in table.items():
        arrived = _adapter._legsplit_arrived_at_link(state, net_a, str(link), idx)
        if arrived <= 0.0:
            continue
        spd = float(getattr(net_a, "leg_ramp_split_wout_speed_kmh", 40.0) or 40.0)
        reach = min(arrived, arrived * _adapter._legsplit_wout_rate(net_a, str(link), spd) * float(sim.T_u_h))
        known_requests = known_legsplit_requests(state, cfg_arg, str(link), reach, arrived, idx)
        free_share = max(0.0, float(spec.get("free", 0.0)))
        free_request = reach * free_share if known_requests is None else known_requests.get('free', 0.)
        exit_cap_veh = exit_cap_h * float(sim.T_u_h)
        intended_free = min(free_request, exit_cap_veh) if finite_exit else free_request
        intended_total = intended_free
        accepted_transfers.append((str(link), None, intended_free))
        if leg_limits is not None:
            leg_limits[(str(link), None)] = (free_request, exit_cap_veh if finite_exit else free_request)
        for ramp, share in (spec.get("ramps") or {}).items():
            sh = max(0.0, float(share))
            cap_r = float(net_a.ramp_queue_cap(str(ramp)))
            space = _ramp_receiving_space(state, cfg_arg, str(ramp))
            conn = max(0.0, float(conn_caps.get(str(ramp), 0.0) or 0.0)) * float(sim.T_u_h)
            entry_cap = min(space, conn) if conn > 0.0 else space
            request = reach * sh if known_requests is None else known_requests.get(str(ramp), 0.)
            allowed = min(request, entry_cap)
            if leg_limits is not None:
                leg_limits[(str(link), str(ramp))] = (request, entry_cap)
            if allowed > 0.0:
                inject[str(ramp)] = inject.get(str(ramp), 0.0) + allowed
                intended_total += allowed
                accepted_transfers.append((str(link), str(ramp), allowed))
        adjust[str(link)] = intended_total
    # B5 v2: 게이트발 on-ramp 큐가 등록된 램프는 도시 착지(ramp_arrival)만 0 — β×게이트 항과 이중계상 방지.
    #   리더의 N_UF 도착 목표는 원래 demand 를 보므로 건드리지 않는다(v1 은 demand_from_state 에서 0 으로 두어 t=900 미터를 조였다).
    _gq_ramps = getattr(net_a, "gate_onramp_queue_ramps", None) or ()
    if _gq_ramps:
        import copy as _copy
        demand = _copy.copy(demand)
        demand.ramp_arrival = {k: (0.0 if str(k) in set(str(x) for x in _gq_ramps) else v) for k, v in dict(getattr(demand, 'ramp_arrival', {}) or {}).items()}
    out = urban_substep_accounted(state, control, demand, cfg_arg, urban_step_index=urban_step_index,
                        ramp_release_veh_h=rel, defer_legsplit_sinks=True)
    # The body can accept other urban/corridor vehicles into the same
    # ramp after these requests were prepared. Reconcile requests against the
    # actual remaining room before withdrawing any of their source stock.
    receipt_scale: dict[str, float] = {}
    resource_ledger = _resource_ledger(state)
    receiving_evidence = {} if resource_ledger is not None else None
    for ramp, requested in inject.items():
        room = _ramp_receiving_space(state, cfg_arg, ramp)
        accepted = min(requested, room)
        if receiving_evidence is not None:
            receiving_evidence[ramp] = (room, {})
        receipt_scale[ramp] = accepted / requested if requested > 0.0 else 0.0
        inject[ramp] = accepted
        _adapter._LEGSPLIT_LAST["leg_ramp_split_receiving_rejected_veh"] = (
            _adapter._LEGSPLIT_LAST.get("leg_ramp_split_receiving_rejected_veh", 0.0) + requested - accepted)
    reconciled_transfers = []
    for source_link, ramp, requested in accepted_transfers:
        accepted = requested if ramp is None else requested * receipt_scale[ramp]
        if resource_ledger is not None:
            source_part, entry_cap = leg_limits[(source_link, ramp)]
            key = source_link + ':' + (ramp or 'outside')
            sources = {'legsplit:' + key: accepted}
            resource_ledger.record_resource_allocation('legsplit_source_reach_share', key, source_part, sources)
            resource_ledger.record_resource_allocation('legsplit_individual_entry_limit', key, entry_cap, sources)
        if receiving_evidence is not None and ramp is not None:
            sources = receiving_evidence[ramp][1]
            key = 'legsplit:' + source_link
            sources[key] = sources.get(key, 0.0) + accepted
        # Available storage increases only by accepted departures. A rejected
        # vehicle stays in its original W_out, retaining its arrival reservation.
        adjust[source_link] -= requested - accepted
        reconciled_transfers.append((source_link, ramp, accepted))
    accepted_transfers = reconciled_transfers
    if resource_ledger is not None:
        for ramp, (room, accepted_sources) in receiving_evidence.items():
            resource_ledger.record_resource_allocation(
                'legsplit_ramp_receiving', 'ramp:' + ramp, room, accepted_sources)
    for ramp, veh in inject.items():
        state.ramp_queue[ramp] = max(0.0, float(state.ramp_queue.get(ramp, 0.0))) + veh
        _adapter._LEGSPLIT_LAST["leg_ramp_split_injected_%s" % ramp] = _adapter._LEGSPLIT_LAST.get("leg_ramp_split_injected_%s" % ramp, 0.0) + veh
    # B3 (2026-09-05): 꼬리 sink 의 추가 배출. vendor 는 전역 1,600 vph 로만 내보내 3,600 vph 유입에 쌓인다.
    tail_caps = _adapter._mapping(getattr(net_a, "wout_tail_exit_capacity_veh_h", None))
    exit_base_h = float(getattr(net_a, "boundary_out_capacity_veh_h", 0.0) or 0.0)
    for tail, cap_h in tail_caps.items():
        if tail not in net_a.urban_link_storage_veh:
            continue
        extra_h = max(0.0, float(cap_h) - exit_base_h)
        if extra_h <= 0.0:
            continue
        cap_t = float(net_a.urban_link_storage_veh[tail])
        arrived_t = _adapter._legsplit_arrived_at_link(state, net_a, tail, idx)
        extra = min(arrived_t, extra_h * float(sim.T_u_h))
        if resource_ledger is not None:
            sources = {'tail:' + tail: extra}
            resource_ledger.record_resource_allocation('legsplit_tail_ready', tail, arrived_t, sources)
            resource_ledger.record_resource_allocation('legsplit_tail_extra_service', tail, extra_h * float(sim.T_u_h), sources)
        if extra > 0.0:
            state.urban_link_storage[tail] = min(cap_t, float(state.urban_link_storage.get(tail, cap_t)) + extra)
            emit_transfer(state, cfg_arg, 'storage:' + tail, None, extra, target_inside=False, route_key='tail_exit:' + tail)
            _adapter._LEGSPLIT_LAST["leg_ramp_split_tail_extra_exit_veh"] = _adapter._LEGSPLIT_LAST.get("leg_ramp_split_tail_extra_exit_veh", 0.0) + extra
    for link, delta in adjust.items():
        if abs(delta) <= 1.0e-12:
            continue
        cap_l = float(net_a.urban_link_storage_veh.get(link, net_a.boundary_queue_max_veh))
        # The generic sink was deferred, so actual accepted departures
        # now free their source space exactly once; never infer an undo.
        available = float(state.urban_link_storage.get(link, cap_l))
        if delta < -1.0e-9 or available + delta > cap_l + 1.0e-7:
            raise ValueError("accepted W_out transfer exceeds source stock: " + str(link))
        if resource_ledger is not None:
            resource_ledger.record_resource_allocation('legsplit_source_stock', str(link), cap_l - available,
                                                     {'legsplit:' + str(link): delta})
        state.urban_link_storage[link] = available + delta
        _adapter._LEGSPLIT_LAST["leg_ramp_split_storage_adjust_veh"] = (
            _adapter._LEGSPLIT_LAST.get("leg_ramp_split_storage_adjust_veh", 0.0) + delta)
    _adapter._LEGSPLIT_LAST["leg_ramp_split_injected_veh"] = (
        _adapter._LEGSPLIT_LAST.get("leg_ramp_split_injected_veh", 0.0) + sum(inject.values()))
    for source_link, ramp, amount in accepted_transfers:
        emit_transfer(state, cfg_arg, 'storage:' + source_link, 'ramp:' + ramp if ramp else None, amount, target_inside=bool(ramp), route_key='legsplit:' + source_link)
    known_legsplit_commit(state, cfg_arg, accepted_transfers, idx)
    if resource_ledger is not None:
        resource_ledger.complete_constraint_coverage('legsplit_allocator')
    return out


_adapter = None


def schedule_offramp_arrivals_accounted(state, cfg, off_ramp, vehicles, urban_step_index, *, branch_vehicles=None):
    """Split the selected group flow once; emit only physically accepted landings."""
    net = cfg.network
    resource_ledger = _resource_ledger(state)
    source = 'freeway:' + str(net.off_ramp_from_freeway[off_ramp])
    share = float((getattr(net, 'offramp_direct_share_by_offramp', {}) or {}).get(off_ramp, 0.0))
    target = (getattr(net, 'offramp_direct_tail_by_offramp', {}) or {}).get(off_ramp)
    remaining = max(0.0, float(vehicles))
    if branch_vehicles is not None:
        from evaluation.controllers.offramp_routing import inventory_enabled
        if (not inventory_enabled(cfg) or set(branch_vehicles) != {'signal', 'direct'}
                or any(not math.isfinite(v) or v < 0 for v in branch_vehicles.values())
                or not math.isclose(sum(branch_vehicles.values()), remaining, abs_tol=1e-7, rel_tol=1e-10)):
            raise ValueError('Explicit off-ramp branch landings must match selected group vehicles')
        share = branch_vehicles['direct'] / remaining if remaining else 0.
    direct_accepted = direct_rejected = 0.0
    if share > 0 and target and target in net.urban_link_storage_veh and remaining > 0:
        _uqm.ensure_urban_state(state, cfg)
        direct = branch_vehicles['direct'] if branch_vehicles is not None else remaining * min(1.0, share)
        available = max(0.0, float(state.urban_link_storage.get(target, net.urban_link_storage_veh[target])))
        direct_accepted = min(direct, available)
        if resource_ledger is not None:
            resource_ledger.record_resource_allocation(
                'offramp_direct_landing', 'storage:' + target, available,
                {'offramp_direct:' + off_ramp: direct_accepted})
        direct_rejected = direct - direct_accepted
        state.urban_link_storage[target] = max(0.0, available - direct_accepted)
        _adapter._LEGSPLIT_LAST['offramp_direct_veh'] = _adapter._LEGSPLIT_LAST.get('offramp_direct_veh', 0.0) + direct_accepted
        emit_transfer(state, cfg, source, 'storage:' + target, direct_accepted,
                      route_key='offramp_direct:' + off_ramp)
        from evaluation.controllers.route_choice_corridor import known_legsplit_receive
        known_legsplit_receive(state, cfg, direct_accepted, urban_step_index, off_ramp=off_ramp)
        remaining = max(0.0, remaining - direct)
    if branch_vehicles is not None:
        remaining = branch_vehicles['signal']
    original = getattr(_uqm, '_offramp_landing_orig_schedule', None)
    if original is None:
        original = _original_schedule
    if resource_ledger is not None and remaining > 0.0:
        # Captured coupled states are initialized/ledger-seeded. Read the exact
        # free stock used by the original schedule; do not add an ensure call
        # or infer a pre-service limit from its post-service stock.
        signal_available = max(0.0, state.urban_link_storage[net.off_ramp_storage_link[off_ramp]])
    accepted, rejected = original(state, cfg, off_ramp, remaining, urban_step_index)
    if resource_ledger is not None and remaining > 0.0:
        resource_ledger.record_resource_allocation(
            'offramp_signal_landing', 'storage:' + net.off_ramp_storage_link[off_ramp], signal_available,
            {'offramp_signal:' + off_ramp: accepted})
    emit_transfer(state, cfg, source, 'storage:' + net.off_ramp_storage_link[off_ramp], accepted,
                  route_key='offramp_signal:' + off_ramp)
    if resource_ledger is not None:
        resource_ledger.complete_constraint_coverage('offramp_landing:' + off_ramp)
    # The capacity hook must prevent selecting flow which cannot land. Losing
    # selected FW vehicles is a model conservation error, never a rewarded exit.
    if float(rejected) + direct_rejected > 1e-7:
        raise ValueError('selected freeway off-ramp flow could not land: ' + str(off_ramp))
    return float(accepted) + direct_accepted, float(rejected) + direct_rejected


def install(adapter, cfg):
    """Enable explicit events after all original urban/landing runtime hooks."""
    global _adapter, _original_schedule
    if not (getattr(cfg.network, 'control_area_enabled', False)
            or getattr(cfg.network, 'sc2001_corridor', None)
            or getattr(cfg.network, 'route_choice_corridor', None)
            or getattr(cfg.network, 'native_internal_inputs', None)):
        return {'area_urban_accounting_enabled': 0.0}
    _adapter = adapter
    if getattr(_uqm.urban_substep, '_control_area_events', False):
        return {'area_urban_accounting_enabled': 1.0}
    original_urban = _uqm.urban_substep
    _original_schedule = _uqm.schedule_offramp_arrivals

    def urban_substep(state, control, demand, cfg, *args, **kwargs):
        area_enabled = bool(getattr(cfg.network, 'control_area_enabled', False))
        if not (area_enabled or getattr(cfg.network, 'sc2001_corridor', None)
                or getattr(cfg.network, 'route_choice_corridor', None)
                or getattr(cfg.network, 'native_internal_inputs', None)):
            return original_urban(state, control, demand, cfg, *args, **kwargs)
        if area_enabled and get_ledger(state) is None:
            raise ValueError('enabled urban accounting requires candidate-owned ledger')
        result = legsplit_substep_accounted(state, control, demand, cfg, *args, **kwargs)
        local = getattr(state,'lane_urban_runtime',None)
        if local is not None:
            step = kwargs.get('urban_step_index')
            if step is None:
                step = args[0] if args else _uqm._urban_step_index(state,cfg)
            physical = local.advance(state,control,cfg,step)
            result[1].update(physical)
        if area_enabled:
            keys = [k for k in get_ledger(state).stocks if k.startswith(('storage:', 'movement:', 'ramp:', 'transit:'))]
            integrate_residence(state, cfg, keys, cfg.simulation.T_u_h)
        return result

    def schedule_offramp_arrivals(state, cfg, *args, **kwargs):
        if not getattr(cfg.network, 'control_area_enabled', False):
            return _original_schedule(state, cfg, *args, **kwargs)
        if get_ledger(state) is None:
            raise ValueError('enabled landing accounting requires candidate-owned ledger')
        return schedule_offramp_arrivals_accounted(state, cfg, *args, **kwargs)

    urban_substep._control_area_events = True
    urban_substep._legsplit_wrapped = True
    schedule_offramp_arrivals._control_area_events = True
    adapter._fw_rebind('urban_substep', original_urban, urban_substep)
    adapter._fw_rebind('schedule_offramp_arrivals', _original_schedule, schedule_offramp_arrivals)
    _uqm.urban_substep = urban_substep
    _uqm.schedule_offramp_arrivals = schedule_offramp_arrivals
    return {'area_urban_accounting_enabled': 1.0}
