"""Ordered VISSIM runtime setup shared by the adapter, replay, and price workers.

Values and model structure are configured once in the parent/replay path.
Workers reinstall hooks from the configured network object without re-estimating
parameters or projecting observations again. No source execution is used here.
"""
from __future__ import annotations

from evaluation.controllers import freeway_local_state
from evaluation.controllers import link_predictor
from evaluation.controllers import offramp_routing
from evaluation.controllers import signal_actuation_contract
from evaluation.controllers import observation_projection
from evaluation.controllers.freeway_fd import install_freeway_fd_runtime, configure_state_response, configure_literature_vsl


def install_freeway_runtime(adapter, cfg, tuning=None):
    """Restore hooks after their values were configured; also safe in spawn."""
    from src.controllers import wu_faithful_follower

    metadata = dict(adapter.install_freeway_vsl_zones(cfg, tuning))
    metadata.update(adapter.install_freeway_segment_runtime(cfg))
    if metadata.get("fw_vsl_zones_enabled"):
        from src.models import state as state_module
        # The legacy segment wrapper masks the inner zone marker. Preserve it
        # so repeated worker setup cannot remap a cell to its head twice and
        # then read the head's FD parameters as that cell's parameters.
        state_module.segment_vsl._rw_vsl_zone = True
    metadata.update(freeway_local_state.install(cfg, adapter._FW_SEG_CTX_STATE))
    metadata.update(link_predictor.install(cfg))
    metadata.update(install_freeway_fd_runtime(adapter, wu_faithful_follower, cfg, tuning))
    metadata.update(adapter.install_freeway_vsl_sequence_kbest(cfg, tuning))
    metadata.update(adapter.install_freeway_vsl_price_dedupe(cfg, tuning))
    return metadata


def configure_freeway_runtime(adapter, cfg, tuning, mapping, *, component_validation=False):
    if (tuning.get('freeway', {}) or {}).get('vsl_fd_response') and not component_validation:
        raise ValueError('Calibrated VSL FD response is component-only; local follower equivalence is not qualified')
    metadata = dict(adapter.install_freeway_segment_lanes(cfg, tuning, mapping))
    freeway_settings = tuning.get("freeway", {}) or {}
    if "physical_vehicle_counts" in freeway_settings:
        flag = freeway_settings["physical_vehicle_counts"]
        if not isinstance(flag, bool):
            raise ValueError("freeway.physical_vehicle_counts must be a boolean")
        cfg.network.physical_vehicle_counts = flag
        metadata["freeway_physical_vehicle_counts"] = float(flag)
    metadata.update(adapter.install_freeway_lane_drop(cfg, tuning))
    metadata.update(adapter.install_freeway_two_branch_fd(cfg, tuning))
    metadata.update(configure_state_response(cfg, tuning))
    metadata.update(configure_literature_vsl(cfg, tuning))
    metadata.update(freeway_local_state.configure(cfg, tuning))
    metadata.update(link_predictor.configure(cfg, tuning))
    metadata.update(install_freeway_runtime(adapter, cfg, tuning))
    return metadata


def configure_runtime(adapter, cfg, tuning, mapping, state_json,
                      previous_action_path, detector_mapping, calibration,
                      TrafficState, physical_projection_input=None):
    """Configure and project with main()'s ordered model-installation sequence.

    cfg must already come from build_config with the caller's actual mode and
    controller. Input paths, calibration fingerprints, and forecast construction
    stay with the caller. The returned detector mapping includes movement merges.
    """
    timetable = (tuning or {}).get('prediction', {}).get('native_input_schedule', False)
    if not isinstance(timetable, bool):
        raise ValueError('prediction.native_input_schedule must be a boolean')
    if timetable and not (tuning or {}).get('urban', {}).get('native_internal_inputs'):
        raise ValueError('Native timetable requires the verified native_internal_inputs source contract')
    a = adapter
    local_observation = bool(a._link_counts_from_local_observation(state_json)
                             and (detector_mapping or physical_projection_input is not None))
    metadata = dict(a.install_vissim_calibration_runtime_patches(cfg, calibration))
    metadata.update(a.install_tau_length_cap_patch(cfg))
    # Phase correction precedes beta pruning; measured beta needs a second prune.
    metadata.update(a.apply_movement_phase_correction(cfg, tuning))
    metadata.update(a.apply_nonexistent_movement_beta_zero(cfg, tuning))
    metadata.update(a.apply_dead_phase_beta_zero(cfg))
    metadata.update(a.install_vsl_metanet_rollout_runtime_patch(cfg, tuning))
    metadata.update(a.install_urban_stopline_storage(cfg, tuning))
    metadata.update(a.install_measured_turn_beta(cfg, tuning))
    metadata.update(a._relabel(a.apply_dead_phase_beta_zero(cfg), "after_measured_beta"))
    metadata.update(configure_freeway_runtime(a, cfg, tuning, mapping))
    metadata.update(a.install_leg_ramp_split_fold(cfg, tuning))
    detector_mapping, merged = a.install_merged_movements(cfg, tuning, detector_mapping)
    metadata.update(merged)
    if (tuning or {}).get('urban', {}).get('movements', {}).get('physical_phase_authority'):
        from evaluation.controllers.physical_movement_routes import configure_phase_authority
        metadata.update(configure_phase_authority(
            cfg, tuning, a.load_signal_group_actuation_plan(), state_json=state_json))
    metadata.update(a.install_phase_vector_green_patch(cfg, tuning))
    metadata.update(a.install_movement_capacity_by_lanes(cfg, tuning))
    metadata.update(a.install_gate_onramp_queue(cfg, tuning))
    metadata.update(a.install_offramp_direct_landing(cfg, tuning))
    metadata.update(offramp_routing.install(cfg, tuning, state_json))
    metadata.update(a.install_offramp_landing_runtime(cfg))
    metadata.update(a.install_landing_storage(cfg, tuning))
    metadata.update(a.install_landing_storage_runtime(cfg))
    # Observed capacity already contains the native simultaneous-green effect.
    metadata.update(a.install_native_signal_structure(cfg, tuning))
    metadata.update(signal_actuation_contract.configure(cfg, tuning, a.load_signal_group_actuation_plan()))
    if getattr(cfg.network, 'native_signal_minimum_policy', None) == 'include_source_reference':
        metadata.update(a.validate_native_signal_runtime_source(cfg, state_json))
    from evaluation.controllers import head_service_resources
    from evaluation.controllers import signal_head_observation
    metadata.update(signal_head_observation.configure_head_free_service(cfg, tuning, state_json))
    metadata.update(head_service_resources.configure(
        cfg, tuning, state_json, a.load_signal_group_actuation_plan()))
    metadata.update(a.install_measured_movement_capacity(
        cfg, tuning, state_json, previous_action_path))
    metadata.update(a.install_measured_far_reservoir_rates(
        cfg, tuning, state_json, previous_action_path))
    metadata.update(a.install_observed_backpressure_price(
        cfg, tuning, state_json, previous_action_path))
    metadata.update(a.install_far_ramp_capacity_patch(cfg))
    metadata.update(a.install_boundary_out_ramp_split(cfg, tuning))
    metadata.update(a.install_leg_ramp_split_runtime(cfg))
    detector_mapping, branch_metadata = observation_projection.install_physical_branch_projection(
        cfg, tuning, detector_mapping, link_counts=a._link_counts_from_local_observation(state_json))
    if branch_metadata.get("physical_branch_projection_enabled"):
        metadata.update(branch_metadata)
    branch_receiving = observation_projection.install_direct_branch_capacity_runtime(cfg)
    if branch_receiving.get("direct_branch_receiving_enabled"):
        metadata.update(branch_receiving)
    if (tuning or {}).get('urban', {}).get('movements', {}).get('physical_route_topology'):
        from evaluation.controllers import physical_movement_routes
        detector_mapping, topology_metadata = physical_movement_routes.configure_topology_repair(
            cfg, detector_mapping, tuning, state_json=state_json)
        metadata.update(topology_metadata)
    if 'dynamic_physical_route_topology' in (tuning or {}).get('urban', {}).get('movements', {}):
        from evaluation.controllers import area_dynamic_routes
        detector_mapping, dynamic_metadata = area_dynamic_routes.configure(
            cfg, detector_mapping, tuning, state_json=state_json)
        metadata.update(dynamic_metadata)
    if (tuning or {}).get('urban', {}).get('shared_approach'):
        from evaluation.controllers import shared_approach
        metadata.update(shared_approach.configure(cfg, tuning, state_json))
    if (tuning or {}).get('urban', {}).get('route_choice_corridor'):
        from evaluation.controllers import route_choice_corridor
        detector_mapping, choice_metadata = route_choice_corridor.configure(
            cfg, tuning, state_json, detector_mapping,
            per_lane_capacity_veh_h=metadata.get('movement_capacity_by_lanes_per_lane_veh_h'))
        metadata.update(choice_metadata)
        detector_mapping, state_json, choice_projection = route_choice_corridor.prepare_projection(
            cfg, detector_mapping, state_json)
        metadata.update(choice_projection)
    from evaluation.controllers import local_signal_service
    metadata.update(head_service_resources.finalize(cfg))
    metadata.update(local_signal_service.configure(cfg, tuning))
    if (tuning or {}).get('urban', {}).get('native_internal_inputs'):
        if tuning.get('urban', {}).get('movements', {}).get('native_input_signal_authority'):
            from evaluation.controllers.physical_movement_routes import configure_native_input_signal_authority
            detector_mapping, authority_metadata = configure_native_input_signal_authority(
                cfg, tuning, detector_mapping, state_json=state_json)
            metadata.update(authority_metadata)
        from evaluation.controllers import native_internal_input
        metadata.update(native_internal_input.configure(cfg, tuning, state_json, detector_mapping))
        detector_mapping, state_json, native_projection = native_internal_input.prepare_projection(
            cfg, detector_mapping, state_json)
        metadata.update(native_projection)
    if (tuning or {}).get('observation', {}).get('physical_support_repair'):
        from evaluation.controllers import projection_support
        detector_mapping, state_json, support_metadata = projection_support.configure(cfg, tuning, detector_mapping, state_json)
        metadata.update(support_metadata)
    if (tuning or {}).get('urban', {}).get('sc2001_corridor'):
        from evaluation.controllers import sc2001_corridor
        metadata.update(sc2001_corridor.configure(cfg, tuning, state_json))
        detector_mapping, state_json, corridor_projection = sc2001_corridor.prepare_projection(
            cfg, detector_mapping, state_json)
        metadata.update(corridor_projection)
    from evaluation.controllers import physical_ramp_branches
    detector_mapping, physical_ramp_metadata = physical_ramp_branches.configure(
        cfg, tuning, mapping, detector_mapping, state_json)
    metadata.update(physical_ramp_metadata)
    metadata.update(offramp_routing.configure_inventory(cfg, tuning, state_json, mapping))
    state = a.traffic_state_from_vissim(
        state_json, cfg, TrafficState, detector_mapping, calibration,
        physical_projection_input=physical_projection_input)
    metadata.update(offramp_routing.initialize_inventory(state, cfg, state_json))
    metadata.update(a.install_monitor_fixed_signal_runtime_patch(
        cfg, state_json, detector_mapping) or {})
    if local_observation:
        a.install_local_observation_runtime_guards()
    if 'conservative_initial_transit' in (tuning or {}).get('urban', {}):
        from evaluation.controllers import area_runtime
        metadata.update(area_runtime.configure_initial_transit(cfg, tuning, state))
    if getattr(cfg.network, 'shared_approach', None):
        from evaluation.controllers import shared_approach
        metadata.update(shared_approach.initialize(state, cfg, state_json, detector_mapping))
        metadata.update(shared_approach.install(a, cfg))
    if getattr(cfg.network, 'sc2001_corridor', None):
        from evaluation.controllers import sc2001_corridor, urban_flow_accounting
        metadata.update(sc2001_corridor.initialize(state, cfg, state_json, detector_mapping))
        metadata.update(urban_flow_accounting.install(a, cfg))
    if getattr(cfg.network, 'route_choice_corridor', None):
        from evaluation.controllers import route_choice_corridor, urban_flow_accounting
        metadata.update(route_choice_corridor.initialize(state, cfg, state_json, detector_mapping))
        metadata.update(urban_flow_accounting.install(a, cfg))
    if getattr(cfg.network, 'native_internal_inputs', None):
        from evaluation.controllers import native_internal_input, native_input_routes, native_input_prehead, urban_flow_accounting
        metadata.update(native_internal_input.initialize(state, cfg, state_json, detector_mapping))
        metadata.update(native_input_routes.initialize(state, cfg, state_json))
        metadata.update(native_input_prehead.initialize(state, cfg, state_json))
        metadata.update(urban_flow_accounting.install(a, cfg))
    if (tuning or {}).get('control_area_objective', {}).get('enabled', False):
        from evaluation.controllers import area_runtime
        metadata.update(area_runtime.configure(a, cfg, tuning, state, detector_mapping))
        from evaluation.controllers import area_meter_finalization
        metadata.update(area_meter_finalization.configure(
            a, cfg, tuning, mapping, state_json, previous_action_path, state, calibration))
    from evaluation.controllers.route_choice_corridor import configure_known_legsplit
    metadata.update(configure_known_legsplit(cfg, tuning, state, state_json))
    return state, detector_mapping, metadata


def install_worker_runtime(adapter, cfg, state_json, detector_mapping):
    """Reinstall the existing worker hooks plus the shared freeway hooks."""
    a = adapter
    signal_actuation_contract.install_candidates(cfg)
    from evaluation.controllers import local_signal_service
    pool_metadata = local_signal_service.install(cfg)
    metadata = dict(a.install_monitor_fixed_signal_runtime_patch(
        cfg, state_json, detector_mapping) or {})
    metadata.update(pool_metadata)
    metadata.update(a.install_tau_length_cap_patch(cfg))
    metadata.update(a.install_far_ramp_capacity_patch(cfg))
    metadata.update(a.install_leg_ramp_split_runtime(cfg))
    metadata.update(a.install_offramp_landing_runtime(cfg))
    branch_receiving = observation_projection.install_direct_branch_capacity_runtime(cfg)
    if branch_receiving.get("direct_branch_receiving_enabled"):
        metadata.update(branch_receiving)
    metadata.update(a.install_landing_storage_runtime(cfg))
    metadata.update(install_freeway_runtime(a, cfg, None))
    if getattr(cfg.network, 'shared_approach', None):
        from evaluation.controllers import shared_approach
        metadata.update(shared_approach.install(a, cfg))
    if (getattr(cfg.network, 'sc2001_corridor', None)
            or getattr(cfg.network, 'route_choice_corridor', None)
            or getattr(cfg.network, 'native_internal_inputs', None)):
        from evaluation.controllers import urban_flow_accounting
        metadata.update(urban_flow_accounting.install(a, cfg))
    if getattr(cfg.network, 'control_area_enabled', False):
        from evaluation.controllers import area_runtime
        metadata.update(area_runtime.install(a, cfg))
    if getattr(cfg.network, "far_ramp_capacity_veh_h", None):
        import src.controllers.stackelberg_mpc as stackelberg_mpc
        if not getattr(stackelberg_mpc, "_rw_far_ramp_capacity_active", False):
            raise RuntimeError("price worker failed to restore measured far ramp capacity")
    return metadata
