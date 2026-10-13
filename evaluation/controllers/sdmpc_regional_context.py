"""Audited own-information graph at the canonical regional solve boundary.

Static catalogs remain global for native command validation. Traffic state,
reactive service/guard inputs and forecasts are regional; source crossing
requests are frozen at the last closed window. Outlets remain explicitly open.
"""
import copy
from dataclasses import fields, is_dataclass
from types import SimpleNamespace

from evaluation.controllers import sdmpc_regional_prototype as regional
from evaluation.controllers.sdmpc_regional_contracts import project_forecast

SCHEMA = 'regional-decision-context/v1'
# Explicit installed static network extensions, in addition to the base schema.
STATIC_NETWORK = frozenset("""
freeway_segment_lanes freeway_segment_params freeway_variable_cell_lengths
physical_vehicle_counts freeway_segment_length_profile_km freeway_geometry_profile
physical_vsl_sign_binding physical_vsl_groups freeway_lane_drop_phi local_lane_context
conservative_offramp_drain local_landing_state freeway_vsl_zone_heads
freeway_vsl_zone_head_of_cell freeway_vsl_zone_of_cell freeway_vsl_zone_free
leg_ramp_split_enabled gate_onramp_queue_kept leg_ramp_split_wout_speed_kmh
movement_merge_rename gate_onramp_queue_ramps offramp_direct_share_by_offramp
offramp_direct_tail_by_offramp native_signal_minimum_policy signal_actuation_contract
native_signal_runtime_source_binding sc1001_shared_observation_enabled
head_green_exposure_windows boundary_out_ramp_split
dynamic_physical_route_topology_path shared_approach route_choice_corridor
regular_alias_pool calibrated_urban_native348 local_service_pool
native_input_signal_authority native_internal_inputs native_input_schedule
sc2001_corridor physical_ramp_branches head_queue_movement_lanes
head_queue_upstream_storage kinematic_queue_zero_links conservative_initial_transit
lane_plant_service_ownership lane_plant_tail_stores
sc1001_shared_movements lane_plant_enabled lane_plant_sources
control_area_reuse_final_audit_physical_proofs
control_area_audit_response_pipeline control_area_compact_signal_clock_cache
control_area_enabled control_area_refresh_nuf_target_each_decision
control_area_pack_completed_response_records control_area_defer_response_gc
control_area_defer_unvisited_command_checks control_area_prefetch_first_owner_responses
control_area_response_scheduling control_area_fast_np_initialization control_area_beta_seconds
control_area_routes known_legsplit_routes direct_exit_legsplit route_corridor_aggregate_step_sec
multirate_freeway_exchange_enabled multirate_urban_clock_sec multirate_joint_clock_enabled
sc107_shared316 _sc10_north325 _sc12_future_routes329
sdmpc_options sdmpc_cost_ownership component_vsl_transport freeway_source_capacity_veh_h
freeway_state_response freeway_terminal_capacity_veh_h freeway_vsl_fd_response
offramp_route_inventory terminal_zero_gradient
""".split())
OWN_NETWORK = {
    'freeway_only': frozenset(('freeway_source_boundary_observed', 'far_ramp_capacity_veh_h')),
    'urban_only': frozenset(('head_free_service', 'head_service_resources',
        'sc1001_shared_observation', 'urban_storage_guard', 'lane_plant_10643_lane_split',
        'physical_gate_travel', 'sc109_transport317', 'urban_boundary_travel_time_sec')),
}
# Installed settings, not stateful multipliers or previous response caches.
FOLLOWER_SETTINGS = tuple("""
ramp_offset_enabled offset_fractions offset_marginal_price_trust_sec
ramp_metering_fractions metering_marginal_price_trust_frac vsl_marginal_price_trust_kmh
phase_price_in_gne metering_in_gne
""".split())


def _schema_copy(obj, extra=()):
    """Copy declared configuration fields and explicitly installed static fields."""
    allowed = {f.name for f in fields(obj)} if is_dataclass(obj) else set()
    allowed.update(extra)
    result = copy.copy(obj)
    result.__dict__ = {k: copy.deepcopy(v) for k, v in vars(obj).items() if k in allowed}
    return result


def local_cfg(original, mode):
    if mode not in regional_modes():
        raise ValueError('Unknown local information mode')
    cfg = _schema_copy(original, ('_canonical_parameters',
        '_vissim_vsl_rollout_enabled', '_vissim_vsl_rollout_consensus_enabled'))
    for name in ('simulation', 'mpc', 'leader', 'freeway_follower', 'urban_follower',
                 'freeway_offramp_capacity_drop', 'evaluation', 'auto_tuning'):
        value = getattr(original, name)
        cfg.__dict__[name] = _schema_copy(value, (
            'phase_price_exchange_steps_sec', '_control_area_fallback_ttt_before',
            'leader_skip_local_refinement', 'leader_rollout_early_stop'))
    net = _schema_copy(original.network, STATIC_NETWORK | OWN_NETWORK[mode])
    cfg.network = net
    # These base-schema fields have observed urban values after initialization.
    # In FW mode their only use is a zero-stock shape / static writer catalog.
    if mode == 'freeway_only':
        net.movement_capacity_by_movement_veh_h = {}
        net.phase_pressure_by_signal = {}
        net.urban_link_storage_veh = dict.fromkeys(net.urban_link_storage_veh, 0.)
        net.urban_movements = copy.deepcopy(net.urban_movements)
        for movement in net.urban_movements.values():
            movement['beta'] = 0.
    context = original.network.control_area_meter_context
    # Physical8 prepare_control maps explicit SG greens through static tables;
    # it never invokes the legacy measured-demand allocator. Only its static
    # writer contract belongs here, also inside each FW component cfg.
    net.control_area_meter_context = {
        'actuation': copy.deepcopy(context['actuation']),
        'mapping': copy.deepcopy(context['mapping']),
        'raw': {}, 'previous_diagnostics': {}, 'spillback': {}, 'sim_sec': 0.,
    }
    return cfg


def regional_modes():
    return ('freeway_only', 'urban_only')


def local_history(historical, cfg, mode):
    from src.models.state import ControlAction
    from evaluation.controllers.sdmpc_actuator_scope import check
    # Check the actual inactive command first; never rewrite historical commands
    # to make an old integrated run appear to have a regional native baseline.
    check(historical, cfg.network.sdmpc_options, cfg)
    result = ControlAction(
        N_P_star=historical.N_P_star if mode == 'urban_only' else 0.,
        N_UF_star=historical.N_UF_star if mode == 'freeway_only' else 0.,
        ramp_metering=copy.deepcopy(historical.ramp_metering),
        vsl=copy.deepcopy(historical.vsl),
        green_times=copy.deepcopy(historical.green_times),
        offsets=copy.deepcopy(historical.offsets),
        inflow_outflow_allocation={}, infeasibility={}, diagnostics={})
    keys = ('physical_ramp_recorded_csv', 'physical_ramp_quantity_semantics')
    result.diagnostics = {k: copy.deepcopy(historical.diagnostics[k])
        for k in (*keys, *('rw_meter_green_'+r for r in cfg.network.ramps))
        if k in historical.diagnostics}
    return result


def local_bootstrap(bootstrap):
    if not isinstance(bootstrap, dict):
        raise ValueError('Regional decision requires static worker bootstrap')
    detector = bootstrap['detector_mapping']
    return dict(state_json={'network_path': bootstrap['state_json']['network_path']},
        detector_mapping={
            'link_to_origins': copy.deepcopy(detector['link_to_origins']),
            'link_partition': {'owned_link_legs': copy.deepcopy(
                detector.get('link_partition', {}).get('owned_link_legs', {}))}},
        runtime_sources=copy.deepcopy(bootstrap['runtime_sources']))


def prepare(controller, state, forecast, historical, mapping, *, derived, bootstrap):
    """Return a disjoint own-information graph, never a full-info fallback."""
    original = controller.nash_solver.cfg
    mode = original.network.sdmpc_options.get('regional_prediction_prototype')
    if mode not in regional_modes():
        raise ValueError('Explicit local information policy required')
    if original.network.sdmpc_options.get('actuator_scope', {}).get('mode') != mode:
        raise ValueError('Information and actuator region differ')
    cfg = local_cfg(original, mode)
    boundary = regional.boundary_requests(derived, mode, state.time_sec,
        original.network.ramps, state.lane_freeway_runtime.offramps)
    local = regional.project_state(state, cfg, mode, boundary)
    if mode == 'freeway_only':
        for road, nested in list(local.lane_freeway_runtime.configs.items()):
            local.lane_freeway_runtime.configs[road] = local_cfg(nested, mode)
    # Reconstruct the installed follower and leader from local configuration:
    # no original previous_control, coupling, trajectory, price or leader cache.
    follower = type(controller.nash_solver)(cfg)
    for key in FOLLOWER_SETTINGS:
        if hasattr(controller.nash_solver, key):
            setattr(follower, key, copy.deepcopy(getattr(controller.nash_solver, key)))
    leader = type(controller.leader)(cfg)
    private = SimpleNamespace(cfg=cfg, nash_solver=follower, leader=leader)
    history = local_history(historical, cfg, mode)
    local.regional_context = dict(schema=SCHEMA, mode=mode, complete=True)
    return dict(controller=private, state=local, forecast=project_forecast(forecast, mode),
        historical=history, mapping=copy.deepcopy(mapping), worker_bootstrap=local_bootstrap(bootstrap),
        evidence=dict(schema=SCHEMA, mode=mode, outlet=boundary['outlet'],
            measured_flow_is_capacity=False, remote_prediction=False))
