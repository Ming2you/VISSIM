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


def response_scheduling_options(value):
    """One opt-in scheduling policy; absent/false retains the original path."""
    import math
    if value is None or value is False:
        return None
    if not isinstance(value, dict) or set(value) != {'lookahead', 'final_check_reserve_sec'}:
        raise ValueError('Response scheduling requires lookahead and final_check_reserve_sec')
    if type(value['lookahead']) is not int or not 1 <= value['lookahead'] <= 8:
        raise ValueError('Response lookahead must be an integer from 1 to 8')
    reserve = value['final_check_reserve_sec']
    if type(reserve) not in (int, float) or not math.isfinite(reserve) or reserve < 0:
        raise ValueError('Final-check reserve must be finite and nonnegative')
    return dict(value)


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
    sinks = set(uqm.sink_storage_links(cfg)) | set(getattr(cfg.network,'lane_plant_tail_stores',()))
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


def configure_final_audit_optimizations(network, tuning):
    """Explicit proof reuse/pipelining without changing the default runtime graph."""
    section = (tuning or {}).get('control_area_objective') or {}
    names = ('reuse_final_audit_physical_proofs', 'audit_response_pipeline')
    values = {name: section.get(name, False) for name in names}
    for name, value in values.items():
        if type(value) is not bool:
            raise ValueError('control_area_objective.'+name+' must be boolean')
    joint = (tuning or {}).get('adapter', {}).get('joint_owner_game') or {}
    if any(values.values()) and joint.get('defer_candidate_final_audit') is not True:
        raise ValueError('Final audit optimizations require deferred selected-candidate auditing')
    if values['audit_response_pipeline']:
        if (not values['reuse_final_audit_physical_proofs']
                or joint.get('ignore_wall_time_limits') is not True
                or joint.get('response_cache_enabled') is not True
                or type(joint.get('response_parallel_workers')) is not int
                or joint['response_parallel_workers'] not in (2, 3, 4, 8)
                or section.get('response_scheduling') is None
                or section.get('prefetch_complete_sweep_responses', False)):
            raise ValueError('Audit pipeline requires proof reuse, unlimited time, parallel cache and bounded scheduling')
        response_scheduling_options(section['response_scheduling'])
    # A failed request must not partially install either optimization.
    for name, value in values.items():
        attr = 'control_area_'+name
        if value:
            setattr(network, attr, True)
        elif hasattr(network, attr):
            delattr(network, attr)


def configure_compact_signal_clock(network, tuning):
    section = (tuning or {}).get('control_area_objective') or {}
    value = section.get('compact_signal_clock_cache', False)
    if type(value) is not bool:
        raise ValueError('control_area_objective.compact_signal_clock_cache must be boolean')
    attr = 'control_area_compact_signal_clock_cache'
    if value:
        setattr(network, attr, True)
    elif hasattr(network, attr):
        delattr(network, attr)


def configure(adapter, cfg, tuning, state, detector_mapping):
    section = (tuning or {}).get('control_area_objective') or {}
    if not section.get('enabled', False):
        return {}
    configure_final_audit_optimizations(cfg.network, tuning)
    configure_compact_signal_clock(cfg.network, tuning)
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
    refresh_nuf = section.get('refresh_nuf_target_each_decision', False)
    if type(refresh_nuf) is not bool:
        raise ValueError('control_area_objective.refresh_nuf_target_each_decision must be boolean')
    if refresh_nuf:
        if not getattr(cfg.network, 'physical_ramp_branches', None):
            raise ValueError('Current-state NUF initialization requires the physical eight ramps')
        cfg.network.control_area_refresh_nuf_target_each_decision = True
    packed_records = section.get('pack_completed_response_records', False)
    if type(packed_records) is not bool:
        raise ValueError('control_area_objective.pack_completed_response_records must be boolean')
    if packed_records:
        cfg.network.control_area_pack_completed_response_records = True
    defer_gc = section.get('defer_response_gc', False)
    if type(defer_gc) is not bool:
        raise ValueError('control_area_objective.defer_response_gc must be boolean')
    if defer_gc:
        cfg.network.control_area_defer_response_gc = True
    defer_commands = section.get('defer_unvisited_command_checks', False)
    if type(defer_commands) is not bool:
        raise ValueError('control_area_objective.defer_unvisited_command_checks must be boolean')
    if defer_commands:
        cfg.network.control_area_defer_unvisited_command_checks = True
    prefetch = section.get('prefetch_first_owner_responses', False)
    if type(prefetch) is not bool:
        raise ValueError('control_area_objective.prefetch_first_owner_responses must be boolean')
    if prefetch:
        cfg.network.control_area_prefetch_first_owner_responses = True
    full_prefetch = section.get('prefetch_complete_sweep_responses', False)
    if type(full_prefetch) is not bool:
        raise ValueError('control_area_objective.prefetch_complete_sweep_responses must be boolean')
    if full_prefetch:
        cfg.network.control_area_prefetch_complete_sweep_responses = True
    elif hasattr(cfg.network, 'control_area_prefetch_complete_sweep_responses'):
        del cfg.network.control_area_prefetch_complete_sweep_responses
    scheduling = response_scheduling_options(section.get('response_scheduling'))
    if scheduling is not None:
        if full_prefetch:
            raise ValueError('Bounded scheduling cannot use complete-sweep prefetch')
        cfg.network.control_area_response_scheduling = scheduling
    elif hasattr(cfg.network, 'control_area_response_scheduling'):
        del cfg.network.control_area_response_scheduling
    import math
    fast_np = section.get('fast_np_initialization')
    if fast_np is not None:
        required = {'candidate_time_budget_sec', 'restoration_time_budget_sec', 'restoration_max_evaluations'}
        if not isinstance(fast_np, dict) or set(fast_np) != required:
            raise ValueError('Explicit fast NP candidate/restoration budgets required')
        for key in ('candidate_time_budget_sec', 'restoration_time_budget_sec'):
            if type(fast_np[key]) not in (int, float) or not math.isfinite(fast_np[key]) or fast_np[key] <= 0:
                raise ValueError('Positive finite fast NP time budgets required')
        if (type(fast_np['restoration_max_evaluations']) is not int or fast_np['restoration_max_evaluations'] < 3
                or fast_np['restoration_time_budget_sec'] > fast_np['candidate_time_budget_sec']):
            raise ValueError('Restoration must fit candidate time and allow the incumbent plus two seeds')
        if full_prefetch:
            raise ValueError('Bounded fast NP candidates cannot use unlimited full-sweep prefetch')
        cfg.network.control_area_fast_np_initialization = dict(fast_np)
    elif hasattr(cfg.network, 'control_area_fast_np_initialization'):
        del cfg.network.control_area_fast_np_initialization
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
    from evaluation.controllers import area_leader_objective
    out = area_leader_objective.install_runtime(cfg)
    from evaluation.controllers import urban_flow_accounting, area_freeway_accounting
    out.update(urban_flow_accounting.install(adapter, cfg))
    out.update(area_freeway_accounting.install(adapter, cfg))
    from evaluation.controllers import area_follower_objective
    out.update(area_follower_objective.install_runtime(cfg))
    from src.controllers import rollout_endpoint as endpoint
    if getattr(endpoint.evaluate_price_point, '_control_area_objective', False):
        return out
    original = endpoint.evaluate_price_point

    def evaluate_price_point(state, previous, forecast, action_schedule, objective_spec, *, capture_response=False):
        """Optional query-owned response; ordinary price/solver calls stay untraced."""
        cfg = objective_spec.cfg
        if not getattr(cfg.network, 'control_area_enabled', False):
            if capture_response:
                raise ValueError('fixed response requires the enabled Omega endpoint')
            return original(state, previous, forecast, action_schedule, objective_spec)
        ledger = get_ledger(state)
        if ledger is None:
            raise MembershipError('area objective requires a seeded candidate ledger')
        candidate = state.copy()
        # A copied rollout endpoint can be called on an already predicted state.
        # Retain its cohorts, but reset this evaluation window's accumulated score.
        candidate._control_area_ledger = ModelAreaLedger(copy.deepcopy(ledger.stocks),
            capture_response=capture_response,
            indexed_coverage=getattr(cfg.network, 'sdmpc_options', {}).get('indexed_coverage', False),
            immutable_audit=getattr(cfg.network, 'sdmpc_options', {}).get('immutable_audit', False),
            primal_audit=getattr(cfg.network, 'sdmpc_options', {}).get('primal_audit', False))
        spec = replace(objective_spec, abort_above=None, far_enabled=False,
                       price_hinge=False, leader_hinge=False, protected_queue=False)
        from evaluation.controllers import area_meter_finalization
        control = area_meter_finalization.for_endpoint(previous, action_schedule, spec)
        get_ledger(candidate).record_freeway_operands(candidate, control, initial=True)
        from evaluation.controllers.sdmpc_prediction_cache import scope as prediction_scope
        with prediction_scope(cfg):
            result = original(candidate, control, forecast, (), spec)
        closing = get_ledger(result.states[-1]) if result.states else get_ledger(candidate)
        if result.states:
            closing.assert_stocks(model_inventory(result.states[-1], cfg))
        metrics = closing.metrics
        weight = ControlAreaObjective(float(cfg.network.control_area_beta_seconds) / 3600.0)
        # The physical rollout and inventory checks above are unchanged.
        # Ranking is exactly Omega TTT-beta*TD; unrecognized soft extras fail.
        area_leader_objective.require_pure_endpoint_base(result.objective, result.ttt)
        result.objective = weight.score(metrics)
        result.ttt = result.partial_ttt = metrics.ttt_veh_h
        result.far = 0.0
        result.control_area = {
            'ttt_veh_h': metrics.ttt_veh_h, 'ttd_veh': metrics.ttd_veh,
            'entered_veh': metrics.entered_veh, 'beta_seconds': weight.beta_hours * 3600,
            'near_score_veh_h': weight.score(metrics), 'additional_cost_veh_h': 0.0,
            'candidate_scores': {str(beta): ControlAreaObjective(beta / 3600).score(metrics)
                                 for beta in (0, 60, 150, 300)},
            'event_count': closing.event_count, 'flow_counts': dict(closing.flow_counts),
            'prediction_approximation': 'proportional mixing; canonical stopline/physical path crossing timing',
            'far_disabled': True, 'legacy_partial_ttt_pruning_disabled': True,
        }
        if capture_response:
            result.control_area_response = closing.response()
            from evaluation.controllers import physical_ramp_branches
            if physical_ramp_branches.enabled(cfg):
                result.control_area['predicted_ramp_merge'] = physical_ramp_branches.predicted_merge_quantity(
                    result.control_area_response, cfg, start_sec=state.time_sec,
                    end_sec=result.states[-1].time_sec)
        return result

    evaluate_price_point._control_area_objective = True
    adapter._fw_rebind('evaluate_price_point', original, evaluate_price_point)
    endpoint.evaluate_price_point = evaluate_price_point
    out['control_area_endpoint_enabled'] = 1.0
    return out


def evaluate_joint_prices(follower, state, reference, forecast, *, callbacks, context,
                          context_fingerprint, horizon_steps, directional_nuf_targets_veh_h,
                          nuf_tolerance_veh_h, source_fingerprint, progress=None,
                          response_query=None, check_budget=None,
                          nuf_price_policy='bounded_direction_equality'):
    """Measure a full-rank finite external-price field on canonical neighbors.

    The ordered basis is selected from realized existing neighborhoods BEFORE
    any cost is observed. This does not narrow follower search. Every edge uses
    the same whole-network response for J and all local costs. No holder, leader
    or solver is mutated; callers install the returned prices at this reference.
    A boundary-fixed meter coordinate needs an exact capacity/equality proof,
    not an unidentified zero. The fitter independently checks that proof.
    """
    import hashlib
    import pickle
    from fractions import Fraction
    from time import perf_counter, process_time
    import numpy as np
    from evaluation.controllers.area_follower_objective import evaluate_shared_owner_batch
    from evaluation.controllers.area_leader_objective import matched_external_secant, fit_joint_price_field
    from evaluation.controllers.joint_owner_game import assert_owner_transition

    def packed(value):
        return pickle.dumps(value, protocol=5)
    def digest(value):
        return hashlib.sha256(packed(value)).hexdigest()
    def emit(value):
        if progress is not None:
            progress(value)
    def check(stage):
        if check_budget is not None:
            check_budget(stage)
    def clock():
        return perf_counter(), process_time()
    def elapsed(start):
        return {'wall_sec': perf_counter()-start[0], 'cpu_sec': process_time()-start[1]}
    if nuf_price_policy not in ('bounded_direction_equality', 'independent'):
        raise ValueError('Supported explicit runtime price-coordinate policy required')
    independent = nuf_price_policy == 'independent'
    timings = {}
    overall_started = clock()
    stage_started = clock()
    check('price_preparation')
    initial_context = context_fingerprint(context)
    original = packed((follower, state, reference, forecast))
    ownership, net = callbacks['ownership'], follower.cfg.network
    if not isinstance(source_fingerprint, str) or not source_fingerprint:
        raise ValueError('Joint prices require frozen runtime source provenance')
    base_command = callbacks['command_evidence'](reference, context)
    # Each proof is already bound to the complete realized action and frozen
    # callback context. Keep it through this one immutable price batch.
    action_commands = [base_command]
    fixed_proof = callbacks.get('fixed_meter_proofs')
    fixed_rates = {}
    if independent and fixed_proof is not None and fixed_proof.get('meters'):
        from evaluation.controllers.joint_owner_neighbors import validate_fixed_meter_coordinate_proofs
        fixed_rates = validate_fixed_meter_coordinate_proofs(follower.cfg, reference, fixed_proof,
            move_box=callbacks.get('move_box'))
    actions, selections = [reference], {}
    for owner in ownership.owners:
        check('price_owner_basis:' + owner)
        domain = callbacks['neighbors'](owner, reference, context)
        if not domain.complete:
            raise ValueError(owner + ': incomplete price-probe source domain')
        urban = owner in net.signals
        if urban:
            live = tuple(net.signal_live_phases(owner))
            cycle = float(net.signal_cycle_length(owner))
            native_basis = (getattr(net, 'signal_actuation_contract', {}) or {}).get('nodes', {}).get(owner, {}).get('native_clock_basis')
            concurrent = isinstance(native_basis, dict) and native_basis.get('kind') == 'concurrent_p1_p2'
            if concurrent and set(live) != {'p1', 'p2', 'p4'}:
                raise ValueError(owner + ': unsupported concurrent price coordinates')
            dimension = len(live)  # live greens minus fixed sum, plus offset
            def vector(action):
                d = {p: action.green_times[owner+'_'+p] - reference.green_times[owner+'_'+p] for p in live}
                off = ((action.offsets[owner] - reference.offsets[owner] + cycle/2) % cycle) - cycle/2
                return [d['p1'], d['p2']-d['p4'], off] if concurrent else [d[p]-d[live[-1]] for p in live[:-1]] + [off]
        else:
            ramps = tuple(follower._local_freeway_models[owner].owned_ramps)
            heads = tuple(net.freeway_vsl_zone_heads[owner][z] for z in net.freeway_vsl_zone_free)
            if independent:
                # Both physical meter rates have their own external-effect
                # coordinate. A one-sided decrement identifies a finite secant
                # at all-open capacity; no symmetric probe is invented.
                dimension = len(heads) + sum(r not in fixed_rates for r in ramps)
                meter_fixed = False
            else:
                target = directional_nuf_targets_veh_h[owner]
                cap0, cap1 = (net.ramp_capacity_veh_h[r] for r in ramps)
                # Exact binary64 box/equality proof, not a float tolerance.
                exact_target, exact_cap0, exact_cap1 = map(Fraction, (target, cap0, cap1))
                lower = max(Fraction(0), exact_target-exact_cap1)
                upper = min(exact_cap0, exact_target)
                if lower > upper:
                    raise ValueError(owner + ': infeasible directional meter equality')
                meter_fixed = lower == upper
                dimension = len(heads) + (0 if meter_fixed else 1)
            def vector(action):
                row = [action.vsl[f'{owner}__seg{h}']-reference.vsl[f'{owner}__seg{h}'] for h in heads]
                if independent:
                    if any(not 0. <= action.ramp_metering[r] <= net.ramp_capacity_veh_h[r] for r in ramps):
                        raise ValueError(owner + ': independent price probe violates physical meter bounds')
                    if any(action.ramp_metering[r] != fixed_rates[r] for r in ramps if r in fixed_rates):
                        raise ValueError(owner + ': price probe violates a proved fixed meter coordinate')
                    row.extend(action.ramp_metering[r]-reference.ramp_metering[r] for r in ramps if r not in fixed_rates)
                elif not meter_fixed:
                    row.append((action.ramp_metering[ramps[0]]-reference.ramp_metering[ramps[0]])
                               -(action.ramp_metering[ramps[1]]-reference.ramp_metering[ramps[1]]))
                return row
        rows, indices, source_indices = [], [], []
        for source_index, action in enumerate(domain.candidates):
            check('price_probe_basis:' + owner)
            assert_owner_transition(ownership, owner, reference, action)
            row = vector(action)
            matrix = np.asarray(rows+[row], dtype=float)
            scales = np.linalg.norm(matrix, axis=0)
            matrix = matrix / np.where(scales == 0., 1., scales)
            rank = int(np.linalg.matrix_rank(matrix))
            if rank <= len(rows):
                continue
            command = callbacks['command_evidence'](action, context)
            if command['owner_physical_sha256'][owner] == base_command['owner_physical_sha256'][owner]:
                continue
            rows.append(row)
            indices.append(len(actions))
            source_indices.append(source_index)
            actions.append(action)
            action_commands.append(command)
            if len(rows) == dimension:
                break
        selections[owner] = {'dimension': dimension, 'rank': len(rows), 'action_indices': indices,
                             'source_indices': source_indices, 'source_candidate_count': len(domain.candidates),
                             'domain_label': domain.domain_label}
        if not urban and any(r in fixed_rates for r in ramps):
            selections[owner]['fixed_meter_coordinates'] = {r: fixed_rates[r] for r in ramps if r in fixed_rates}
        emit({'stage': 'joint_price_basis', 'owner': owner, **selections[owner]})
        if len(rows) != dimension:
            raise ValueError(owner + ': canonical price probes do not span the active tangent space')
    # The batch makes its own private inputs and preserves all original checks.
    # One response per distinct full action; no independently repeated J/C rollout.
    timings['candidate_generation_and_realization'] = elapsed(stage_started)
    check('price_endpoints')
    stage_started = clock()
    emit({'stage': 'joint_price_endpoints', 'candidate_count': len(actions)})
    if response_query is None:
        batch = evaluate_shared_owner_batch(follower, state, reference, forecast, actions,
            horizon_steps=horizon_steps, check_budget=check_budget)
    else:
        batch = response_query(actions)
    if len(batch['results']) != len(actions):
        raise ValueError('Incomplete price response batch')
    timings['shared_responses'] = elapsed(stage_started)
    stage_started = clock()
    envelopes = []
    native_nodes = {s: node for s, node in
        (getattr(net, 'signal_actuation_contract', {}) or {}).get('nodes', {}).items()
        if node.get('native_clock_basis') is not None}
    if len(action_commands) != len(actions):
        raise ValueError('Price command proofs do not cover every realized action')
    for action, item, evidence in zip(actions, batch['results'], action_commands):
        check('price_response_validation')
        if item['action_token'] != digest(action) or not item['conditional_model_feasibility_witness']:
            raise ValueError('Unbound action or incomplete implemented model constraints in price response')
        models = {who: {a.key: getattr(action, a.field)[a.key] for a in ownership.addresses if a.owner == who}
                  for who in ownership.owners}
        envelopes.append({'objective_veh_h': item['objective_veh_h'], 'local_base_costs': item['local_base_costs'],
            'context': {'frozen_digest': digest((initial_context, item['frozen_context_token'])),
                'beta_seconds': net.control_area_beta_seconds, 'runtime_sources_digest': source_fingerprint,
                'local_cost_definition': 'shared-urban-source-cost+FW-physical-destination-cohorts/v1'},
            'response_token': item['response_token'], 'local_cost_response_token': item['response_token'],
            'model_owner_values': models, 'physical_owner_tokens': evidence['owner_physical_sha256'],
            'price_or_quantity_terms_included': False, 'local_cost_contains_omega_beta': False})
        if native_nodes:
            envelopes[-1]['context']['native_clock_nodes'] = pickle.loads(pickle.dumps(native_nodes, protocol=5))
        if getattr(net, 'physical_ramp_branches', None):
            envelopes[-1]['context']['physical_meter_addresses_by_owner'] = {
                who:sorted(r for r in net.ramps if net.ramp_to_freeway[r] == who)
                for who in net.freeway_links}
    secants = {}
    for owner, selection in selections.items():
        check('price_secants:' + owner)
        urban = owner in net.signals
        owned = tuple(a for a in ownership.addresses if a.owner == owner and (urban or a.key != owner))
        kinds = {'green_times': 'green', 'offsets': 'offset', 'vsl': 'vsl', 'ramp_metering': 'meter'}
        before = {a.key: getattr(reference, a.field)[a.key] for a in owned}
        secants[owner] = []
        for index in selection['action_indices']:
            after = {a.key: getattr(actions[index], a.field)[a.key] for a in owned}
            delta = {k: after[k]-v for k, v in before.items()}
            cycles = {owner: float(net.signal_cycle_length(owner))} if urban else {}
            if urban:
                cycle = cycles[owner]
                delta[owner] = ((delta[owner]+cycle/2) % cycle)-cycle/2
            coordinate = {'owner': owner, 'kind': 'joint_direction', 'parameter_unit': '1',
                'displacement': 1., 'base_values': before, 'probe_values': after, 'direction': delta,
                'address_kinds': {a.key: kinds[a.field] for a in owned},
                'address_owners': {a.key: owner for a in owned}, 'offset_cycles': cycles}
            secants[owner].append(matched_external_secant(envelopes[0], envelopes[index],
                owners=ownership.owners, owner=owner, coordinate=coordinate))
    check('price_field_fit')
    fit_options = {'nuf_price_policy': nuf_price_policy}
    if fixed_rates:
        fit_options.update(fixed_meter_proofs=fixed_proof, fixed_move_box=callbacks.get('move_box'))
    if not independent:
        fit_options.update(directional_nuf_targets_veh_h=directional_nuf_targets_veh_h,
            nuf_equality_tolerance_veh_h=nuf_tolerance_veh_h,
            final_meter_bounds_veh_h={r: {'lower': 0., 'upper': net.ramp_capacity_veh_h[r]} for r in net.ramps})
    field = fit_joint_price_field(follower, reference, secants, **fit_options)
    if packed((follower, state, reference, forecast)) != original or context_fingerprint(context) != initial_context:
        raise ValueError('Price measurement changed the fixed caller/runtime context')
    timings['validation_and_price_fit'] = elapsed(stage_started)
    timings['total'] = elapsed(overall_started)
    timings['scope'] = 'Wall and process CPU measured independently; response internals nest within shared_responses, all phases nest within total'
    if callable(callbacks.get('command_cache_stats')):
        emit({'stage': 'price_command_evidence_cache', **callbacks['command_cache_stats']()})
    return {'field': field, 'probe_selection': selections, 'secants': secants,
            'responses': batch, 'source_fingerprint': source_fingerprint,
            'timings': timings, 'nuf_price_policy': nuf_price_policy,
            'holders_installed': False, 'leader_updated': False,
            'scope': 'Actual matched finite external-price measurements; no game or native execution certificate'}
