"""Opt-in near-horizon Omega objective through the existing rollout endpoint.

Physical observation defines initial cohorts. Predicted grouped reservoirs use
proportional mixing and canonical stopline/turn paths, explicitly an approximation.
Freeway stock uses the METANET continuity volume, including its effective lanes.
No endpoint stock subtraction is used as a throughput reward.
"""
from __future__ import annotations
from dataclasses import replace
import copy
import json
from pathlib import Path

from evaluation.controllers.control_area_objective import (
    MembershipError, ModelAreaLedger, ControlAreaObjective, get_ledger,
    model_stock_values, physical_membership_from_ledger, projection_stock_cohorts,
)


def model_inventory(state, cfg):
    from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts
    return model_stock_values(state, cfg.network,
                              freeway_vehicle_counts=continuity_vehicle_counts(state, cfg))


def seed_from_projection(state, cfg, physical):
    provenance = state.local_observation_summary.get('projection_diagnostics', {}).get('physical_stock_assignment_by_link')
    if provenance is None:
        raise MembershipError('area objective requires physical stock projection provenance')
    cohorts = projection_stock_cohorts(provenance, physical)
    inventory = model_inventory(state, cfg)
    for key, amount in inventory.items():
        if key.startswith('freeway:'):
            cohorts[key] = {'inside': amount, 'outside': 0.0}
        elif key.startswith('origin:'):
            cohorts[key] = {'inside': 0.0, 'outside': amount}
        elif key not in cohorts:
            if amount > 1e-7:
                raise MembershipError(f'positive initial stock lacks observed cohort: {key}={amount}')
            cohorts[key] = {'inside': 0.0, 'outside': 0.0}
    state._control_area_ledger = ModelAreaLedger(cohorts)
    state._control_area_ledger.assert_stocks(inventory)
    return state._control_area_ledger


def pair_initial_arrival_releases(state, cfg):
    """Give every initialized storage->queue reservation one storage release.

    The legacy arrival seed can be enabled while release restore is sinks-only.
    Its queue arrival otherwise creates a duplicate of the still occupied store.
    Dedicated OR stores drain directly and must not also seed movement arrivals.
    This is initialization only, before any candidate flow has been scheduled.
    """
    from src.models import urban_queue_model as uqm
    sinks = set(uqm.sink_storage_links(cfg))
    off_stores = set(cfg.network.off_ramp_storage_link.values())
    added = removed_off = replaced = 0.0
    for source in cfg.network.urban_link_storage_veh:
        arrivals = state.urban_arrival_buffer.get(source, {})
        if source in off_stores:
            removed_off += sum(arrivals.values())
            state.urban_arrival_buffer.pop(source, None)
            state.urban_storage_release_buffer.pop(source, None)
        elif source not in sinks:
            prior = state.urban_storage_release_buffer.get(source, {})
            replaced += sum(prior.values())
            added += sum(arrivals.values())
            state.urban_storage_release_buffer[source] = dict(arrivals)
    return {'paired_initial_arrival_release_veh': added,
            'paired_initial_release_previous_veh': replaced,
            'dedicated_offramp_arrival_duplicate_removed_veh': removed_off}


def configure_initial_transit(cfg, tuning, state):
    """Independent physics flag: usable with the unchanged legacy objective."""
    section = (tuning or {}).get('urban', {})
    if 'conservative_initial_transit' not in section:
        return {}
    enabled = section['conservative_initial_transit']
    if type(enabled) is not bool:
        raise ValueError('urban.conservative_initial_transit must be boolean')
    cfg.network.conservative_initial_transit = enabled
    if not enabled:
        return {'conservative_initial_transit_enabled': 0.0}
    if hasattr(state, '_conservative_initial_transit_applied'):
        return dict(state._conservative_initial_transit_applied)
    metadata = pair_initial_arrival_releases(state, cfg)
    metadata['conservative_initial_transit_enabled'] = 1.0
    state._conservative_initial_transit_applied = metadata
    return dict(metadata)


def configure(adapter, cfg, tuning, state, detector_mapping):
    section = (tuning or {}).get('control_area_objective') or {}
    if not section.get('enabled', False):
        return {}
    if not getattr(cfg.network, 'conservative_initial_transit', False) or not hasattr(state, '_conservative_initial_transit_applied'):
        raise ValueError('area objective requires urban.conservative_initial_transit initialized before area configuration')
    if 'beta_seconds' not in section:
        raise ValueError('control_area_objective.beta_seconds is required; no default reward weight')
    beta = float(section['beta_seconds'])
    ControlAreaObjective(beta / 3600.0)
    root = Path(adapter.__file__).resolve().parents[2]
    def read_required(key):
        path = Path(section[key])
        if not path.is_absolute():
            path = root / path
        return json.loads(path.read_text(encoding='utf-8'))
    membership = read_required('membership_path')
    physical = physical_membership_from_ledger(membership)
    routes = read_required('route_contract_path')
    from evaluation.controllers.area_arrival_routes import extend_gate_routes
    routes, arrival_metadata = extend_gate_routes(cfg, routes, membership, root=root, detector_mapping=detector_mapping)
    dynamic_path = getattr(cfg.network, 'dynamic_physical_route_topology_path', None)
    if dynamic_path:
        from evaluation.controllers.area_dynamic_routes import extend_routes
        routes, dynamic_metadata = extend_routes(cfg, routes, detector_mapping, membership, dynamic_path)
        arrival_metadata.update(dynamic_metadata)
    shared = getattr(cfg.network, 'shared_approach', None)
    if shared:
        side = physical[str(shared['physical_link'])]
        routes['input:shared:' + shared['storage']] = {'target_inside': side, 'physical_link': shared['physical_link'],
                                                     'event_kind': 'native_internal_generation'}
    projection = detector_mapping.get('physical_storage_projection', {}) or {}
    target_links = {}
    for link, target in (projection.get('link_to_storage', {}) or {}).items():
        target_links.setdefault(str(target), set()).add(str(link))
    # Each off-ramp branch uses its dedicated physical observation support. A
    # mixed target requires an explicit route; a geometric 1/n share is forbidden.
    for off in cfg.network.off_ramps:
        targets = {'offramp_signal:': cfg.network.off_ramp_storage_link[off]}
        direct = (getattr(cfg.network, 'offramp_direct_tail_by_offramp', {}) or {}).get(off)
        if direct:
            targets['offramp_direct:'] = direct
        for prefix, target in targets.items():
            key = prefix + off
            if key in routes:
                continue
            support = target_links.get(target, set())
            # B0's east direct connector is folded into W_out, not a dedicated
            # storage override; take the explicitly mapped branch destination.
            if not support:
                branches = detector_mapping.get('off_ramp_connectors', {}).get(off, [])
                for branch in branches:
                    connector = str(branch['connector'])
                    assigned = (projection.get('link_to_storage', {}) or {}).get(connector)
                    if prefix == 'offramp_direct:' and assigned != cfg.network.off_ramp_storage_link[off]:
                        support.add(connector)
            sides = {physical.get(link) for link in support}
            if len(sides) != 1 or None in sides:
                raise MembershipError(f'off-ramp target route unresolved: {key}: {support}')
            routes[key] = {'status': 'physical_branch', 'target_inside': sides.pop(), 'physical_links': sorted(support)}
    cfg.network.control_area_enabled = True
    cfg.network.control_area_beta_seconds = beta
    cfg.network.control_area_routes = routes
    if getattr(cfg.network, 'sc2001_corridor', None):
        from evaluation.controllers.sc2001_corridor import extend_area_routes
        arrival_metadata.update(extend_area_routes(cfg))
    if getattr(cfg.network, 'route_choice_corridor', None):
        from evaluation.controllers.route_choice_corridor import extend_area_routes
        arrival_metadata.update(extend_area_routes(cfg))
    if getattr(cfg.network, 'native_internal_inputs', None):
        from evaluation.controllers.native_internal_input import extend_area_routes
        arrival_metadata.update(extend_area_routes(cfg))
    ledger = seed_from_projection(state, cfg, physical)
    metadata = install(adapter, cfg)
    metadata.update(arrival_metadata)
    metadata.update({'control_area_initial_inside_veh': sum(row['inside'] for row in ledger.stocks.values()),
                     'control_area_beta_seconds': beta,
                     'control_area_near_only': 1.0})
    return metadata


def install(adapter, cfg):
    if not getattr(cfg.network, 'control_area_enabled', False):
        return {}
    from evaluation.controllers import urban_flow_accounting, area_freeway_accounting
    out = urban_flow_accounting.install(adapter, cfg)
    out.update(area_freeway_accounting.install(adapter, cfg))
    from evaluation.controllers import area_follower_objective
    out.update(area_follower_objective.install_runtime(cfg))
    from src.controllers import rollout_endpoint as endpoint
    if getattr(endpoint.evaluate_price_point, '_control_area_objective', False):
        return out
    original = endpoint.evaluate_price_point

    def evaluate_price_point(state, previous, forecast, action_schedule, objective_spec):
        cfg = objective_spec.cfg
        if not getattr(cfg.network, 'control_area_enabled', False):
            return original(state, previous, forecast, action_schedule, objective_spec)
        ledger = get_ledger(state)
        if ledger is None:
            raise MembershipError('area objective requires a seeded candidate ledger')
        candidate = state.copy()
        # A copied rollout endpoint can be called on an already predicted state.
        # Retain its cohorts, but reset this evaluation window's accumulated score.
        candidate._control_area_ledger = ModelAreaLedger(copy.deepcopy(ledger.stocks))
        spec = replace(objective_spec, abort_above=None, far_enabled=False)
        from evaluation.controllers import area_meter_finalization
        control = area_meter_finalization.for_endpoint(previous, action_schedule, spec)
        result = original(candidate, control, forecast, (), spec)
        closing = get_ledger(result.states[-1]) if result.states else get_ledger(candidate)
        if result.states:
            closing.assert_stocks(model_inventory(result.states[-1], cfg))
        metrics = closing.metrics
        weight = ControlAreaObjective(float(cfg.network.control_area_beta_seconds) / 3600.0)
        # Existing feasibility/hinge penalties are preserved; the global near TTT
        # is replaced once. Far is explicitly disabled until it has Omega scope.
        other = result.objective - result.ttt
        result.objective = weight.score(metrics) + other
        result.ttt = result.partial_ttt = metrics.ttt_veh_h
        result.far = 0.0
        result.control_area = {
            'ttt_veh_h': metrics.ttt_veh_h, 'ttd_veh': metrics.ttd_veh,
            'entered_veh': metrics.entered_veh, 'beta_seconds': weight.beta_hours * 3600,
            'near_score_veh_h': weight.score(metrics), 'additional_cost_veh_h': other,
            'candidate_scores': {str(beta): ControlAreaObjective(beta / 3600).score(metrics) + other
                                 for beta in (0, 60, 150, 300)},
            'event_count': closing.event_count, 'flow_counts': dict(closing.flow_counts),
            'prediction_approximation': 'proportional mixing; canonical stopline/physical path crossing timing',
            'far_disabled': True, 'legacy_partial_ttt_pruning_disabled': True,
        }
        return result

    evaluate_price_point._control_area_objective = True
    adapter._fw_rebind('evaluate_price_point', original, evaluate_price_point)
    endpoint.evaluate_price_point = evaluate_price_point
    out['control_area_endpoint_enabled'] = 1.0
    return out
