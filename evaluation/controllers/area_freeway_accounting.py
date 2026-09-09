"""Explicit freeway/coupling transition hooks for the control-area ledger.

Two methods are extracted from the pinned vendor equations so actual selected
entry, merge and terminal flows are available where they are computed. Model
helpers are resolved dynamically from their canonical modules, preserving the
installed geometry/FD hooks. There is no production AST/source execution.

The disabled installer is a no-op. When installed, disabled configs delegate to
the pre-install methods. Off-ramp transfers belong exclusively to the urban
schedule hook; this module never counts them a second time. Freeway residence
uses end-of-substep stocks after that schedule, matching METANET quadrature.
"""
from __future__ import annotations
from src.models import metanet as _mn
from src.simulation import coupling as _cp
from evaluation.controllers import control_area_objective as _area

VENDOR_FREEWAY_METHOD_SHA256 = "eb19ad40207a07bac75db9b67c03280be8558a310123e9eddacf655ac49e8762"
VENDOR_COUPLING_METHOD_SHA256 = "ced88a0a6fef090f3eb78a43af4538f73c8b7d11de07c5633142fa9867ba59c0"


def continuity_vehicle_counts(state, cfg):
    """Stocks in the equations below, independent of patched display getters.

    The current model continuity uses one segment length and dynamic effective
    lanes. Observation geometry may differ; report that projection difference
    separately instead of inventing a flow event to reconcile the two stocks.
    """
    net = cfg.network
    if int(getattr(net, "freeway_buffer_segments", 0)):
        raise ValueError("control-area accounting requires explicit buffer-chain membership")
    state.ensure_freeway_lane_profile(net)
    return {link: [max(0.0, rho) * net.freeway_segment_length_km * max(lane, 1e-9)
                   for rho, lane in zip(state.freeway_density[link], state.freeway_effective_lanes[link])]
            for link in net.freeway_links}


def _freeway_substep_events(state: _mn.TrafficState, control: _mn.ControlAction, demand: _mn.DemandStep, cfg: _mn.ExperimentConfig, offramp_capacity_veh_h: _mn.Dict[str, float] | None=None, ramp_release_veh_h: _mn.Dict[str, float] | None=None, ramp_release_diagnostics: _mn.Dict[str, float] | None=None, update_ramp_queues: bool=True, include_ramp_queue_ttt: bool=True) -> _mn.Tuple[float, _mn.Dict[str, float]]:
    """Spec 3.1/3.2 METANET plant를 정확히 한 `T_f` step만 전진한다."""
    net = cfg.network
    sim = cfg.simulation
    dt_h = sim.T_f_h
    if update_ramp_queues:
        raise ValueError("area accounting requires coupled ramp releases, not standalone exogenous ramp arrivals")
    if int(getattr(net, "freeway_buffer_segments", 0)):
        raise ValueError("control-area accounting requires explicit buffer-chain membership")
    state.ensure_freeway_lane_profile(net)
    for link in net.freeway_links:
        state.mainline_origin_queue.setdefault(link, 0.0)
    freeway_ttt = 0.0
    _buffer_diag: _mn.Dict[str, float] = {}
    density_projection_count = 0
    speed_projection_count = 0
    flow_acc = 0.0
    flow_count = 0
    offramp_flow_acc: _mn.Dict[str, float] = {link: 0.0 for link in net.freeway_links}
    offramp_blocked_acc: _mn.Dict[str, float] = {link: 0.0 for link in net.freeway_links}
    mainline_exit_acc: _mn.Dict[str, float] = {link: 0.0 for link in net.freeway_links}
    cap_factor = getattr(demand, 'incident_capacity_factor', 1.0)
    q_cap = net.freeway_capacity_veh_h * cap_factor
    phi_cd = float(getattr(net, 'capacity_drop_discharge_phi', 1.0) or 1.0)
    delta_m = float(getattr(net, 'metanet_delta_merge', 0.0) or 0.0)
    target_flow = _mn._nuf_target_flow_veh_h(control, cfg)
    if ramp_release_veh_h is None:
        ramp_release, ramp_diag = _mn.compute_ramp_release_flows(state, control, demand, cfg)
    else:
        ramp_release = dict(ramp_release_veh_h)
        ramp_diag = dict(ramp_release_diagnostics) if ramp_release_diagnostics is not None else _mn.compute_ramp_release_flows(state, control, demand, cfg)[1]
    ramp_in_by_link = {link: [0.0 for _ in state.freeway_density[link]] for link in net.freeway_links}
    ramp_arrival_blocked: _mn.Dict[str, float] = {}
    for ramp, release in ramp_release.items():
        link = net.ramp_to_freeway[ramp]
        merge_idx = _mn._ramp_merge_index(cfg, ramp, len(state.freeway_density[link]))
        ramp_in_by_link[link][merge_idx] += max(0.0, release)
        _area.emit_transfer(state, cfg, f"merge_pending:{ramp}", f"freeway:{link}",
                            max(0.0, release) * dt_h, target_inside=True)
        if update_ramp_queues:
            arrival = demand.ramp_arrival.get(ramp, 0.0)
            q0 = max(0.0, state.ramp_queue.get(ramp, 0.0))
            cap_r = net.ramp_queue_cap(ramp) if hasattr(net, 'ramp_queue_cap') else float(net.ramp_queue_max_veh)
            drained = q0 - dt_h * release
            room = max(0.0, cap_r - max(0.0, drained))
            accepted = min(max(0.0, arrival) * dt_h, room)
            ramp_arrival_blocked[ramp] = max(0.0, max(0.0, arrival) * dt_h - accepted)
            next_queue = drained + accepted
            state.ramp_queue[ramp] = max(0.0, min(cap_r, next_queue))
    lane_now_by_link, lane_diag_start = _mn.effective_lane_profile(state, cfg, demand)
    for link in net.freeway_links:
        rhos = list(state.freeway_density[link])
        speeds = list(state.freeway_speed[link])
        previous_lanes = list(state.freeway_effective_lanes.get(link, []))
        lanes_now = lane_now_by_link[link]
        offramps_by_segment: _mn.Dict[int, list[str]] = {}
        for off_ramp in net.off_ramps:
            if net.off_ramp_from_freeway.get(off_ramp) != link:
                continue
            segment_idx = _mn._configured_segment_index(getattr(net, 'off_ramp_segment_index', {}), off_ramp, len(rhos) - 1, len(rhos))
            offramps_by_segment.setdefault(segment_idx, []).append(off_ramp)
        buf_n = int(getattr(net, 'freeway_buffer_segments', 0))
        _buf_lane = float(net.freeway_lanes)
        _buf_len = float(net.freeway_segment_length_km)
        if buf_n > 0:
            for _bd, _bv, _init in ((state.freeway_buffer_up_density, state.freeway_buffer_up_speed, 0.0), (state.freeway_buffer_down_density, state.freeway_buffer_down_speed, 0.0)):
                if len(_bd.setdefault(link, [])) != buf_n:
                    _bd[link] = [_init] * buf_n
                if len(_bv.setdefault(link, [])) != buf_n:
                    _bv[link] = [float(net.v_free)] * buf_n
            bu_r = list(state.freeway_buffer_up_density[link])
            bu_v = list(state.freeway_buffer_up_speed[link])
            bd_r = list(state.freeway_buffer_down_density[link])
            bd_v = list(state.freeway_buffer_down_speed[link])
        vehicles = [max(0.0, rho) * net.freeway_segment_length_km * max(lane, 1e-09) for rho, lane in zip(rhos, previous_lanes)]
        rho_for_flow = [n / max(net.freeway_segment_length_km * max(lane, 1e-09), 1e-09) for n, lane in zip(vehicles, lanes_now)]
        vsl_max = max(cfg.freeway_follower.vsl_set)
        q_values = [_mn.segment_flow_veh_h(rho, speed, lane) for rho, speed, lane in zip(rho_for_flow, speeds, lanes_now)]
        if phi_cd < 1.0:
            for _i in range(len(q_values)):
                if rho_for_flow[_i] > _mn.effective_rho_crit(net, _mn.segment_vsl(control, link, _i, cfg)):
                    q_values[_i] = min(q_values[_i], phi_cd * q_cap * max(lanes_now[_i], 1e-09) / max(float(net.freeway_lanes), 1e-09))
        flow_acc += sum(q_values)
        flow_count += len(q_values)
        receiving = [max(0.0, (net.rho_max - rho_for_flow[i]) * net.freeway_segment_length_km * max(lanes_now[i], 1e-09) / max(dt_h, 1e-09)) for i in range(len(rho_for_flow))]
        receiving_for_mainline = [max(0.0, receiving[i] - max(0.0, ramp_in_by_link[link][i])) for i in range(len(rho_for_flow))]
        off_ratio_by_segment = [_mn._clip(sum((net.off_ramp_split_ratio.get(off_ramp, 0.0) for off_ramp in offramps_by_segment.get(i, []))), 0.0, 1.0) for i in range(len(rho_for_flow))]
        mainline_sending = [(1.0 - off_ratio_by_segment[i]) * q_values[i] for i in range(len(rho_for_flow))]
        q_inter = [min(mainline_sending[i], receiving_for_mainline[i + 1]) for i in range(len(rho_for_flow) - 1)]
        if state.mainline_origin_queue.get(link) is None:
            state.mainline_origin_queue[link] = 0.0
        mainline_demand = max(0.0, demand.freeway_mainline.get(link, 0.0))
        _area.emit_transfer(state, cfg, f"external:mainline:{link}", f"origin:{link}",
                            mainline_demand * dt_h, source_inside=False, target_inside=False)
        queued_flow = state.mainline_origin_queue[link] / max(dt_h, 1e-09)
        entry_request = mainline_demand + queued_flow
        if buf_n > 0:
            _bu_recv0 = max(0.0, (net.rho_max - bu_r[0]) * _buf_len * _buf_lane / max(dt_h, 1e-09))
            entry_realized = min(entry_request, q_cap, _bu_recv0)
            _bu_send_last = _mn.segment_flow_veh_h(bu_r[-1], bu_v[-1], _buf_lane)
            if phi_cd < 1.0 and bu_r[-1] > float(net.rho_crit):
                _bu_send_last = min(_bu_send_last, phi_cd * q_cap)
            core_in0 = min(_bu_send_last, receiving_for_mainline[0])
        else:
            entry_realized = min(entry_request, q_cap, receiving_for_mainline[0])
            core_in0 = entry_realized
        state.mainline_origin_queue[link] = max(0.0, state.mainline_origin_queue[link] + dt_h * (mainline_demand - entry_realized))
        _area.emit_transfer(state, cfg, f"origin:{link}", f"freeway:{link}",
                            entry_realized * dt_h, target_inside=True)
        next_rhos = []
        next_speeds = []
        next_flows = []
        next_lanes = []
        next_vehicle_count = []
        for i, rho in enumerate(rho_for_flow):
            q_in = core_in0 if i == 0 else q_inter[i - 1]
            q_in += ramp_in_by_link[link][i]
            if i == len(rhos) - 1:
                if buf_n > 0:
                    _bd_recv0 = max(0.0, (net.rho_max - bd_r[0]) * _buf_len * _buf_lane / max(dt_h, 1e-09))
                    terminal_out = min(mainline_sending[i], _bd_recv0)
                elif getattr(net, 'terminal_zero_gradient', False):
                    terminal_out = mainline_sending[i]
                else:
                    terminal_cap = q_cap * max(lanes_now[i], 1e-09) / max(float(net.freeway_lanes), 1e-09)
                    terminal_out = min(mainline_sending[i], terminal_cap)
                q_out = terminal_out
            else:
                q_out = q_inter[i]
            boundary_speed_cap = None
            effective_off_total = 0.0
            normal_off_total = 0.0
            for off_ramp in offramps_by_segment.get(i, []):
                ratio = _mn._clip(net.off_ramp_split_ratio.get(off_ramp, 0.0), 0.0, 1.0)
                normal_off = ratio * q_values[i]
                if offramp_capacity_veh_h is None:
                    cap = None
                else:
                    cap = offramp_capacity_veh_h.get(off_ramp, offramp_capacity_veh_h.get(link))
                effective_off = normal_off if cap is None else min(normal_off, max(0.0, cap))
                effective_off_total += effective_off
                normal_off_total += normal_off
                offramp_flow_acc[off_ramp] = offramp_flow_acc.get(off_ramp, 0.0) + effective_off
                offramp_blocked_acc[off_ramp] = offramp_blocked_acc.get(off_ramp, 0.0) + max(0.0, normal_off - effective_off)
            if normal_off_total > 0.0:
                q_out += effective_off_total
                offramp_flow_acc[link] += effective_off_total
                offramp_blocked_acc[link] += max(0.0, normal_off_total - effective_off_total)
                if normal_off_total > effective_off_total + 1e-09:
                    boundary_speed_cap = q_out / max(rho * lanes_now[i], 1e-09)
            if i == len(rhos) - 1:
                if buf_n <= 0:
                    mainline_exit_acc[link] += terminal_out
                    _area.emit_transfer(state, cfg, f"freeway:{link}", f"external:terminal:{link}",
                                        terminal_out * dt_h, source_inside=True, target_inside=False)
                if terminal_out < mainline_sending[i] - 1e-09:
                    exit_speed_cap = q_out / max(rho * lanes_now[i], 1e-09)
                    boundary_speed_cap = exit_speed_cap if boundary_speed_cap is None else min(boundary_speed_cap, exit_speed_cap)
            vehicle_raw = vehicles[i] + dt_h * (q_in - q_out)
            vehicle_new = max(0.0, vehicle_raw)
            if abs(vehicle_new - vehicle_raw) > 1e-09:
                density_projection_count += 1
            rho_new = vehicle_new / max(net.freeway_segment_length_km * max(lanes_now[i], 1e-09), 1e-09)
            upstream_speed = (bu_v[-1] if buf_n > 0 else net.v_free) if i == 0 else speeds[i - 1]
            if i + 1 < len(rhos):
                downstream_rho = rho_for_flow[i + 1]
            elif buf_n > 0:
                downstream_rho = bd_r[0]
            elif getattr(net, 'terminal_zero_gradient', False):
                downstream_rho = rho_for_flow[i]
            else:
                downstream_rho = min(rho_for_flow[i], float(net.rho_crit))
            vsl_i = _mn.segment_vsl(control, link, i, cfg)
            vsl_active_i = vsl_i < vsl_max - 0.5
            v_eff = _mn.effective_desired_speed_kmh(rho, net.v_free, net.rho_crit, vsl_i, net.alpha_vsl, vsl_active_i, net.metanet_a_m, getattr(net, 'vsl_fd_two_branch', False), net.rho_max, float(getattr(net, 'rho_crit_two_branch', 0.0) or 0.0))
            v_new = _mn.metanet_speed_update_kmh(speeds[i], upstream_speed, rho, downstream_rho, v_eff, dt_h, net.freeway_segment_length_km, net.metanet_tau_h, _mn.select_anticipation_nu(rho, net, vsl_i), net.metanet_kappa_veh_km_lane, net.v_min)
            if delta_m > 0.0 and ramp_in_by_link[link][i] > 0.0:
                v_new = max(net.v_min, v_new - delta_m * dt_h * ramp_in_by_link[link][i] * speeds[i] / (net.freeway_segment_length_km * max(lanes_now[i], 1e-09) * (rho + net.metanet_kappa_veh_km_lane)))
            if v_new <= net.v_min + 1e-09:
                speed_projection_count += 1
            if boundary_speed_cap is not None and v_new > boundary_speed_cap:
                v_new = max(net.v_min, boundary_speed_cap)
                speed_projection_count += 1
            next_rhos.append(rho_new)
            next_speeds.append(v_new)
            next_lanes.append(float(lanes_now[i]))
            next_vehicle_count.append(float(vehicle_new))
            next_flows.append(_mn.segment_flow_veh_h(rho_new, v_new, lanes_now[i]))
        state.freeway_density[link] = next_rhos
        state.freeway_speed[link] = next_speeds
        state.freeway_flow[link] = next_flows
        state.freeway_effective_lanes[link] = next_lanes
        freeway_ttt += sum(next_vehicle_count) * dt_h
        if buf_n > 0:

            def _adv_chain(r0, v0, head_in, tail_out, ds_last_rho, up_head_speed):
                n = len(r0)
                sends = [_mn.segment_flow_veh_h(r0[j], v0[j], _buf_lane) for j in range(n)]
                if phi_cd < 1.0:
                    sends = [min(s, phi_cd * q_cap) if r0[j] > float(net.rho_crit) else s for j, s in enumerate(sends)]
                recvs = [max(0.0, (net.rho_max - r0[j]) * _buf_len * _buf_lane / max(dt_h, 1e-09)) for j in range(n)]
                flows_in = [0.0] * n
                flows_out = [0.0] * n
                flows_in[0] = head_in
                for j in range(n - 1):
                    f = min(sends[j], recvs[j + 1])
                    flows_out[j] = f
                    flows_in[j + 1] = f
                flows_out[n - 1] = tail_out
                nr, nv = ([], [])
                for j in range(n):
                    veh = r0[j] * _buf_len * _buf_lane + dt_h * (flows_in[j] - flows_out[j])
                    nr.append(max(0.0, veh) / (_buf_len * _buf_lane))
                    up_v = up_head_speed if j == 0 else v0[j - 1]
                    ds_rho = r0[j + 1] if j + 1 < n else ds_last_rho
                    v_eff = _mn.effective_desired_speed_kmh(r0[j], net.v_free, net.rho_crit, net.v_free, net.alpha_vsl, False, net.metanet_a_m, getattr(net, 'vsl_fd_two_branch', False), net.rho_max, float(getattr(net, 'rho_crit_two_branch', 0.0) or 0.0))
                    nv.append(_mn.metanet_speed_update_kmh(v0[j], up_v, r0[j], ds_rho, v_eff, dt_h, _buf_len, net.metanet_tau_h, _mn.select_anticipation_nu(r0[j], net), net.metanet_kappa_veh_km_lane, net.v_min))
                return (nr, nv)
            _bu_nr, _bu_nv = _adv_chain(bu_r, bu_v, entry_realized, core_in0, rho_for_flow[0], net.v_free)
            _bd_tail_send = _mn.segment_flow_veh_h(bd_r[-1], bd_v[-1], _buf_lane)
            if phi_cd < 1.0 and bd_r[-1] > float(net.rho_crit):
                _bd_tail_send = min(_bd_tail_send, phi_cd * q_cap)
            if getattr(net, 'terminal_zero_gradient', False):
                _bd_tail_out = _bd_tail_send
                _bd_tail_ds_rho = bd_r[-1]
            else:
                _bd_tail_out = min(_bd_tail_send, q_cap)
                _bd_tail_ds_rho = min(bd_r[-1], float(net.rho_crit))
            _bd_nr, _bd_nv = _adv_chain(bd_r, bd_v, terminal_out, _bd_tail_out, _bd_tail_ds_rho, speeds[-1])
            if _bd_tail_out < _bd_tail_send - 1e-09:
                _cap_v = _bd_tail_out / max(bd_r[-1] * _buf_lane, 1e-09)
                _bd_nv[-1] = max(net.v_min, min(_bd_nv[-1], _cap_v))
            mainline_exit_acc[link] += _bd_tail_out
            state.freeway_buffer_up_density[link] = _bu_nr
            state.freeway_buffer_up_speed[link] = _bu_nv
            state.freeway_buffer_down_density[link] = _bd_nr
            state.freeway_buffer_down_speed[link] = _bd_nv
            freeway_ttt += (sum(_bu_nr) + sum(_bd_nr)) * _buf_len * _buf_lane * dt_h
            _buffer_diag[f'buffer_down_max_rho_{link}'] = float(max(_bd_nr))
            _buffer_diag[f'buffer_down_end_rho_{link}'] = float(_bd_nr[-1])
            _buffer_diag[f'buffer_up_max_rho_{link}'] = float(max(_bu_nr))
    if include_ramp_queue_ttt:
        freeway_ttt += sum(state.ramp_queue.values()) * dt_h
        freeway_ttt += sum((max(0.0, q) for q in state.mainline_origin_queue.values())) * dt_h
    diagnostics: _mn.Dict[str, float] = {}
    diagnostics.update(_buffer_diag)
    avg_metering = float(sum(ramp_release.values()))
    avg_no_meter = ramp_diag['total_no_meter_flow']
    diagnostics['total_metering_flow'] = avg_metering
    queue_start_veh = float(ramp_diag.get('total_ramp_queue_start_flow', 0.0)) * dt_h
    queue_end_veh = sum((max(0.0, q) for q in state.ramp_queue.values()))
    queue_growth_flow = max(0.0, queue_end_veh - queue_start_veh) / max(dt_h, 1e-09)
    over_release = max(0.0, avg_metering - target_flow)
    shortfall = min(max(0.0, target_flow - avg_metering), queue_growth_flow)
    diagnostics['total_metering_error'] = over_release + shortfall
    diagnostics['total_no_meter_flow'] = float(avg_no_meter)
    diagnostics['metering_over_release_flow'] = float(over_release)
    diagnostics['metering_shortfall_flow'] = float(shortfall)
    diagnostics['nuf_target_flow'] = float(target_flow)
    diagnostics['total_ramp_queue_start_veh'] = float(queue_start_veh)
    diagnostics['total_ramp_queue_end_veh'] = float(queue_end_veh)
    diagnostics['ramp_arrival_blocked_veh'] = float(sum(ramp_arrival_blocked.values()))
    for _r, _v in ramp_arrival_blocked.items():
        diagnostics['ramp_arrival_blocked_%s_veh' % _r] = float(_v)
    diagnostics['metering_target_infeasible'] = float(target_flow > avg_no_meter + cfg.freeway_follower.eps_F)
    diagnostics['ramp_queue_overflow_count'] = float(sum((1 for _r, q in state.ramp_queue.items() if q > (net.ramp_queue_cap(_r) if hasattr(net, 'ramp_queue_cap') else float(net.ramp_queue_max_veh)))))
    diagnostics['mean_ramp_receiving_factor'] = ramp_diag['mean_ramp_receiving_factor']
    diagnostics['mean_segment_flow'] = flow_acc / flow_count if flow_count else 0.0
    diagnostics.update(lane_diag_start)
    diagnostics['offramp_storage_binding'] = float(any((v > 1e-09 for v in offramp_blocked_acc.values())))
    diagnostics['offramp_flow_total'] = float(sum((offramp_flow_acc.get(off_ramp, 0.0) for off_ramp in net.off_ramps)))
    diagnostics['offramp_blocked_flow_total'] = float(sum((offramp_blocked_acc.get(off_ramp, 0.0) for off_ramp in net.off_ramps)))
    diagnostics['mainline_exit_flow_total'] = float(sum(mainline_exit_acc.values()))
    for off_ramp in net.off_ramps:
        diagnostics[f'offramp_flow_{off_ramp}'] = float(offramp_flow_acc.get(off_ramp, 0.0))
        diagnostics[f'offramp_blocked_flow_{off_ramp}'] = float(offramp_blocked_acc.get(off_ramp, 0.0))
    for link in net.freeway_links:
        diagnostics[f'offramp_flow_{link}'] = float(offramp_flow_acc.get(link, 0.0))
        diagnostics[f'offramp_blocked_flow_{link}'] = float(offramp_blocked_acc.get(link, 0.0))
    diagnostics['density_projection_count'] = float(density_projection_count)
    diagnostics['speed_projection_count'] = float(speed_projection_count)
    diagnostics['mainline_origin_queue_total_veh'] = float(sum((max(0.0, q) for q in state.mainline_origin_queue.values())))
    diagnostics['density_exceedance_count'] = float(sum((1 for values in state.freeway_density.values() for rho in values if rho > net.rho_crit)))
    return (float(freeway_ttt), diagnostics)

def _run_coupled_interval_events(state: _cp.TrafficState, control: _cp.ControlAction, demand: _cp.DemandStep, cfg: _cp.ExperimentConfig) -> _cp.CoupledStepResult:
    """Spec 3.4.3의 `T_c -> T_f -> T_u` nested order로 한 control interval을 전진한다."""
    sim = cfg.simulation
    _cp.sync_onramp_queues_from_freeway(state, cfg)
    freeway_ttt = 0.0
    urban_ttt = 0.0
    offramp_storage_ttt_moved = 0.0
    freeway_rows: list[_cp.Dict[str, float]] = []
    urban_rows: list[_cp.Dict[str, float]] = []
    accepted_offramp = 0.0
    rejected_offramp = 0.0
    start_urban_step = int(round(state.time_sec / max(sim.T_u_sec, 1e-09)))
    for freeway_substep_index in range(sim.K_cf):
        _cp.sync_onramp_queues_to_freeway(state, cfg)
        ramp_release, ramp_diag = _cp.compute_ramp_release_flows(state, control, demand, cfg, include_current_arrivals=False)
        urban_rows_in_freeway_step: list[_cp.Dict[str, float]] = []
        for urban_offset in range(sim.K_fu):
            step_idx = start_urban_step + freeway_substep_index * sim.K_fu + urban_offset
            ur_ttt, ur_diag = _cp.urban_substep(state, control, demand, cfg, urban_step_index=step_idx, ramp_release_veh_h=ramp_release)
            urban_ttt += ur_ttt
            moved = float(ur_diag.get('offramp_storage_ttt', 0.0))
            freeway_ttt += moved
            offramp_storage_ttt_moved += moved
            urban_rows.append(ur_diag)
            urban_rows_in_freeway_step.append(ur_diag)
        _cp.sync_onramp_queues_to_freeway(state, cfg)
        actual_ramp_release = _cp._actual_ramp_release_flows(urban_rows_in_freeway_step, cfg)
        actual_ramp_diag = _cp._with_actual_ramp_diagnostics(ramp_diag, actual_ramp_release)
        offramp_capacity = _cp.off_ramp_capacity_by_freeway_link(state, cfg, interval_h=sim.T_f_h)
        fw_ttt, fw_diag = _cp.freeway_substep(state, control, demand, cfg, offramp_capacity_veh_h=offramp_capacity, ramp_release_veh_h=actual_ramp_release, ramp_release_diagnostics=actual_ramp_diag, update_ramp_queues=False, include_ramp_queue_ttt=True)
        freeway_ttt += fw_ttt
        freeway_rows.append(fw_diag)
        next_urban_step = start_urban_step + (freeway_substep_index + 1) * sim.K_fu
        for off_ramp in cfg.network.off_ramps:
            flow = _cp._offramp_flow_from_diagnostics(fw_diag, cfg, off_ramp)
            vehicles = flow * sim.T_f_h
            accepted, rejected = _cp.schedule_offramp_arrivals(state, cfg, off_ramp, vehicles, next_urban_step)
            accepted_offramp += accepted
            rejected_offramp += rejected
        # Scheduling owns FW -> off-ramp/direct transfers. Account FW residence
        # only after those transfers, using the same endpoint quadrature as METANET.
        _area.integrate_residence(state, cfg,
            [f"freeway:{link}" for link in cfg.network.freeway_links] +
            [f"origin:{link}" for link in cfg.network.freeway_links], sim.T_f_h)
    diagnostics: _cp.Dict[str, _cp.Any] = {'coupling_nested_order_active': 1.0, 'coupling_freeway_substeps': float(cfg.simulation.K_cf), 'coupling_urban_substeps': float(cfg.simulation.K_cu), 'coupling_onramp_sync_active': 1.0, 'coupling_onramp_two_reservoir_active': 1.0, 'coupling_offramp_storage_active': 1.0, 'coupling_aggregate_urban_model': 0.0, 'coupling_movement_urban_model': 1.0, 'coupling_offramp_arrivals_accepted_veh': float(accepted_offramp), 'coupling_offramp_arrivals_rejected_veh': float(rejected_offramp), 'coupling_offramp_storage_ttt_moved_to_freeway': float(offramp_storage_ttt_moved)}
    fw_diag = _cp._aggregate_freeway_diagnostics(freeway_rows, interval_h=sim.T_c_h, rows_per_cycle=max(1, int(round(cfg.network.cycle_length / sim.T_f_sec))), queue_cap_veh=sum((cfg.network.ramp_queue_cap(r) for r in cfg.network.ramps)))
    ur_diag = _cp.aggregate_urban_diagnostics(urban_rows, cfg, control, interval_h=sim.T_c_h)
    diagnostics.update(fw_diag)
    diagnostics.update(ur_diag)
    return _cp.CoupledStepResult(freeway_ttt=float(freeway_ttt), urban_ttt=float(urban_ttt), diagnostics=diagnostics)

def install(adapter, cfg):
    """Install after the geometry/FD and urban ledger hooks; repeatable in spawn."""
    if not getattr(cfg.network, "control_area_enabled", False):
        return {"area_freeway_accounting_enabled": 0.0}
    if int(getattr(cfg.network, "freeway_buffer_segments", 0)):
        raise ValueError("control-area accounting requires explicit buffer-chain membership")
    freeway_installed = bool(getattr(_mn.freeway_substep, "_control_area_events", False))
    coupling_installed = bool(getattr(_cp.run_coupled_interval, "_control_area_events", False))
    if freeway_installed != coupling_installed:
        raise RuntimeError("partial control-area freeway/coupling installation")
    if freeway_installed:
        return {"area_freeway_accounting_enabled": 1.0, "area_freeway_accounting_installed": 0.0}
    old_freeway, old_coupling = _mn.freeway_substep, _cp.run_coupled_interval

    def freeway_substep(state, control, demand, cfg, *args, **kwargs):
        if not getattr(cfg.network, "control_area_enabled", False):
            return old_freeway(state, control, demand, cfg, *args, **kwargs)
        if _area.get_ledger(state) is None:
            raise ValueError("enabled freeway accounting requires a candidate-owned ledger")
        return _freeway_substep_events(state, control, demand, cfg, *args, **kwargs)

    def run_coupled_interval(state, control, demand, cfg):
        if not getattr(cfg.network, "control_area_enabled", False):
            return old_coupling(state, control, demand, cfg)
        if _area.get_ledger(state) is None:
            raise ValueError("enabled coupling accounting requires a candidate-owned ledger")
        return _run_coupled_interval_events(state, control, demand, cfg)

    freeway_substep._control_area_events = True
    run_coupled_interval._control_area_events = True
    adapter._fw_rebind("freeway_substep", old_freeway, freeway_substep)
    adapter._fw_rebind("run_coupled_interval", old_coupling, run_coupled_interval)
    _mn.freeway_substep, _cp.run_coupled_interval = freeway_substep, run_coupled_interval
    return {"area_freeway_accounting_enabled": 1.0, "area_freeway_accounting_installed": 1.0}
