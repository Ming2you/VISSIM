"""Rank enabled Omega candidates by their canonical endpoint score alone.

Physical state equations and feasibility are untouched. Legacy cost components
remain inspectable as excluded diagnostics; config weights are never rewritten.
Supported selection consumers are the Wu full, Wu proxy and Wu PFO paths.
Base proxy/fallback scalars have no verified Omega provenance and fail closed.
"""
from __future__ import annotations
import functools
import math
from copy import deepcopy

APPLIED_LEGACY_COSTS = (
    'leader_target_penalty', 'leader_mfd_storage_penalty',
    'leader_boundary_in_queue_penalty', 'leader_density_penalty',
    'leader_ramp_queue_penalty', 'leader_vissim_terminal_cost_penalty',
)


def enabled(cfg):
    return bool(getattr(cfg.network, 'control_area_enabled', False))


def validate_config(cfg):
    if not enabled(cfg):
        return
    if cfg.leader.objective_mode != 'follower_ttt':
        raise ValueError('Omega leader requires the canonical endpoint objective as follower_ttt base')
    if getattr(cfg.mpc, 'leader_proxy_near_far', False):
        raise ValueError('Omega leader cannot add the unscoped direct proxy far cost')


def require_pure_endpoint_base(objective, ttt):
    """Unknown endpoint extras fail before the near score is replaced by ΩJ."""
    objective, ttt = float(objective), float(ttt)
    if not math.isfinite(objective) or not math.isfinite(ttt) or ttt < 0. or objective != ttt:
        raise ValueError('Unrecognized endpoint cost outside the Omega objective scope')


def canonicalize_terms(cfg, terms, endpoint_objective):
    """Idempotent final boundary, also called after instance terminal wrappers.

The terminal installer can precede or follow the class installer. Its final call
here prevents captured old methods or subsequent terminal costs from escaping.
"""
    if not enabled(cfg):
        return terms
    validate_config(cfg)
    score = float(endpoint_objective)
    if not math.isfinite(score):
        raise ValueError('Omega leader endpoint objective is not finite')
    values = {key: float(terms.get(key, 0.)) for key in APPLIED_LEGACY_COSTS}
    total = float(terms['leader_total_objective'])
    if not all(math.isfinite(x) for x in (total, *values.values())):
        raise ValueError('Omega leader legacy cost diagnostics are not finite')
    if not math.isclose(total-score, sum(values.values()), rel_tol=1e-10, abs_tol=1e-8):
        raise ValueError('Unrecognized cost was added outside the Omega endpoint')
    result = dict(terms)
    for key, value in values.items():
        if key not in terms:
            continue
        excluded = 'leader_excluded_' + key.removeprefix('leader_')
        result[excluded] = float(result.get(excluded, 0.)) + value
        result[key] = 0.
    if 'leader_vissim_terminal_cost_active' in result:
        result['leader_excluded_vissim_terminal_cost_configured'] = float(
            max(result.get('leader_excluded_vissim_terminal_cost_configured', 0.),
                result['leader_vissim_terminal_cost_active']))
        result['leader_vissim_terminal_cost_active'] = 0.
    result['leader_excluded_legacy_cost_total'] = sum(
        float(result.get('leader_excluded_' + key.removeprefix('leader_'), 0.))
        for key in APPLIED_LEGACY_COSTS)
    result['leader_objective_base'] = score
    result['leader_follower_ttt_base'] = score
    result['leader_total_objective'] = score
    result['leader_control_area_objective_only'] = 1.
    return result


def install_runtime(cfg):
    if not enabled(cfg):
        return {}
    validate_config(cfg)
    from src.controllers.leader import Leader
    if not getattr(Leader.objective_terms, '_control_area_leader_objective', False):
        original = Leader.objective_terms
        @functools.wraps(original)
        def objective_terms(self, predicted_states, action, previous, follower_objective,
                            nash_converged, nash_residual_objective=0., nash_residual_control=0.):
            terms = original(self, predicted_states, action, previous, follower_objective,
                             nash_converged, nash_residual_objective, nash_residual_control)
            return canonicalize_terms(self.cfg, terms, follower_objective)
        objective_terms._control_area_leader_objective = True
        Leader.objective_terms = objective_terms
    _install_scoring_consumers()
    return {'control_area_leader_objective_only_installed': 1.}


def _proxy_score_candidate(self, index, action, state, forecast, previous):
    """Enabled proxy method extracted from StackelbergWuMeteredController.

    Preserve projection, capacity-proportional meter allocation and output keys.
    Only the score source changes from generic _predict's TTT to endpoint J.
    """
    validate_config(self.cfg)
    from src.controllers.rollout_endpoint import evaluate_price_point
    action, _projection_meta = self._project_action_to_follower_feasible_np(
        action, state, forecast, previous)
    control = previous.copy()
    control.N_P_star = float(action.N_P_star)
    control.N_UF_star = float(action.N_UF_star)
    net = self.cfg.network
    if float(action.N_UF_star) > 0.:
        follower = self.nash_solver
        for link in net.freeway_links:
            owned = list(follower._local_freeway_models[link].owned_ramps)
            if not owned:
                continue
            caps = {r: float(net.ramp_capacity_veh_h[r]) for r in owned}
            cap_sum = sum(caps.values())
            if cap_sum <= 0.:
                continue
            omega = float(follower._wu._omega_f.get(link, 0.))
            budget = min(max(omega*float(action.N_UF_star), 0.), cap_sum)
            for ramp in owned:
                share = budget*(caps[ramp]/cap_sum)
                control.ramp_metering[ramp] = float(min(max(share, 0.), caps[ramp]))
    point = evaluate_price_point(state, control, forecast, (), self._rollout_spec(score_mode='raw'))
    terms = self.leader.objective_terms(point.states, control, previous,
                                        float(point.objective), True, 0., 0.)
    return {'index': float(index), 'N_P_star': float(action.N_P_star),
            'N_UF_star': float(action.N_UF_star),
            'objective': float(terms['leader_total_objective']),
            'base': float(terms['leader_objective_base']),
            'follower_ttt': float(terms['leader_follower_ttt_base']),
            'spillback_violation': 0.}


def _install_scoring_consumers():
    from src.controllers.stackelberg_mpc import StackelbergMPCController
    from src.controllers.stackelberg_wu_metered import StackelbergWuMeteredController
    cls = StackelbergWuMeteredController
    if not getattr(cls._proxy_score_candidate, '_control_area_leader_objective', False):
        original_proxy = cls._proxy_score_candidate
        @functools.wraps(original_proxy)
        def proxy(self, index, action, state, forecast, previous):
            if not enabled(self.cfg):
                return original_proxy(self, index, action, state, forecast, previous)
            return _proxy_score_candidate(self, index, action, state, forecast, previous)
        proxy._control_area_leader_objective = True
        cls._proxy_score_candidate = proxy
    cls = StackelbergMPCController
    if not getattr(cls._proxy_score_candidate, '_control_area_leader_objective', False):
        original_base_proxy = cls._proxy_score_candidate
        @functools.wraps(original_base_proxy)
        def base_proxy(self, index, action, state, forecast, previous):
            if enabled(self.cfg):
                raise ValueError('Omega does not support the base/DistributedCoordinator proxy score')
            return original_base_proxy(self, index, action, state, forecast, previous)
        base_proxy._control_area_leader_objective = True
        cls._proxy_score_candidate = base_proxy
    if not getattr(cls._leader_evaluation_base, '_control_area_leader_objective', False):
        original_base = cls._leader_evaluation_base
        @functools.wraps(original_base)
        def base(self, state, nash, forecast, incumbent_obj=float('inf'), previous=None):
            if not enabled(self.cfg):
                return original_base(self, state, nash, forecast, incumbent_obj, previous)
            validate_config(self.cfg)
            from src.controllers.rollout_endpoint import evaluate_price_point
            point = evaluate_price_point(state, nash.control, forecast, (),
                self._rollout_spec(score_mode='raw', walk_previous=previous))
            return point.states, float(point.objective), True
        base._control_area_leader_objective = True
        cls._leader_evaluation_base = base
    if not getattr(cls._make_fallback_evaluation, '_control_area_leader_objective', False):
        original_fallback = cls._make_fallback_evaluation
        @functools.wraps(original_fallback)
        def fallback(self, index, stage, nash, previous, state, forecast, extra_metadata=None):
            if enabled(self.cfg):
                raise ValueError('Omega does not support the base fallback response scalar; use the Wu PFO path')
            return original_fallback(self, index, stage, nash, previous, state, forecast, extra_metadata)
        fallback._control_area_leader_objective = True
        cls._make_fallback_evaluation = fallback


def _joint_number(value, label, *, nonnegative=False):
    if type(value) not in (int, float) or not math.isfinite(value) or (nonnegative and value < 0):
        raise ValueError(f'{label} must be a finite {"nonnegative " if nonnegative else ""}number')
    return float(value)


def validate_joint_leader_result(response, *, target_np_veh, target_nuf_veh_h, cfg=None):
    """Return NashResult constructor kwargs for an explicitly supplied joint result.

    This is an opt-in, pure transport boundary, not a legacy dispatch hook.
    It never reruns a response, applies either legacy quantity closure, or adds
    prices/beta to the already scored Omega objective. The caller must compare
    command_evidence with its final physical CSV before writing the action.

    A completed finite-neighborhood check is not the legacy Nash residual
    definition: converged remains False and both legacy residuals remain None.
    A budget stop may retain a scored feasible incumbent and partial final gaps;
    other callback failures are rejected. Reported absolute quantity tolerances
    belong to the frozen producer contract, not newly chosen leader budgets.
    Search history is copied separately from per_owner's final-gap audit. Missing
    history stays unknown; an unvisited final audit does not imply no search.
    """
    import copy
    import hashlib
    import pickle

    def mapping(value, label):
        if not isinstance(value, dict):
            raise ValueError(label + ' must be an explicit mapping')
        return value

    def token(value, label):
        if (type(value) is not str or len(value) != 64
                or any(c not in '0123456789abcdef' for c in value)):
            raise ValueError(label + ' must be a SHA256 token')
        return value

    response = mapping(response, 'Joint response')
    game = mapping(response.get('game'), 'Joint game')
    score = mapping(response.get('final_score'), 'Scored final response')
    control = game.get('control')
    fields = ('N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times',
              'offsets', 'inflow_outflow_allocation')
    if control is None or any(not hasattr(control, key) for key in fields):
        raise ValueError('Complete final ControlAction required')
    digest = hashlib.sha256(pickle.dumps(control, protocol=5)).hexdigest()
    if (token(response.get('final_action_token'), 'Final action') != digest
            or token(score.get('action_token'), 'Scored action') != digest):
        raise ValueError('Final action differs from the scored full action')
    for field in fields:
        value = getattr(control, field)
        if field in fields[:2]:
            _joint_number(value, field)
        else:
            for key, item in mapping(value, field).items():
                if type(key) is not str or not key:
                    raise ValueError('Action addresses must be nonempty strings')
                _joint_number(item, field + ':' + key,
                              nonnegative=field == 'ramp_metering')
    owners = game.get('owners')
    if (not isinstance(owners, (tuple, list)) or len(owners) != 19
            or any(type(owner) is not str or not owner for owner in owners)
            or len(set(owners)) != 19 or not {'FW_E', 'FW_W'}.issubset(owners)
            or type(game.get('owner_count')) is not int or game['owner_count'] != 19):
        raise ValueError('Complete explicit 19-owner catalog required')
    owners = set(owners)
    for field in ('local_base_costs', 'owner_costs', 'physical_owner_tokens'):
        values = mapping(score.get(field), field)
        if set(values) != owners:
            raise ValueError('Final score owner catalog differs: ' + field)
        for owner, value in values.items():
            if field == 'physical_owner_tokens':
                if type(value) not in (str, bytes) or not value:
                    raise ValueError('Nonempty physical owner token required')
            else:
                _joint_number(value, field + ':' + owner)
    objective = _joint_number(score.get('objective_veh_h'), 'Final Omega score')
    area = mapping(score.get('control_area'), 'Final Omega metrics')
    if (_joint_number(area.get('near_score_veh_h'), 'Captured Omega score') != objective
            or _joint_number(area.get('additional_cost_veh_h'), 'Additional cost') != 0.
            or score.get('price_or_quantity_terms_included') is not False):
        raise ValueError('Joint leader requires the pure captured Omega score')
    coverage = mapping(score.get('model_constraint_coverage'), 'Model constraint coverage')
    if (coverage.get('complete') is not True
            or coverage.get('conditional_model_feasibility_witness') is not True
            or score.get('conditional_model_feasibility_witness') is not True):
        raise ValueError('Implemented model constraint coverage is incomplete')
    limits = mapping(game.get('limits'), 'Frozen game limits')
    resource = mapping(score.get('resource_summary'), 'Resource summary')
    violation = _joint_number(resource.get('max_exceedance_veh'), 'Resource exceedance', nonnegative=True)
    shared_tolerance = _joint_number(limits.get('shared_tolerance'), 'Resource tolerance', nonnegative=True)
    if violation > shared_tolerance:
        raise ValueError('Final response violates an implemented model resource limit')
    if (score.get('shared_capacity_certificate') is not False
            or response.get('native_plant_feasibility_certified') is not False):
        raise ValueError('Joint transport cannot claim full shared/native feasibility')
    constraints = mapping(score.get('quantity_constraints'), 'Frozen quantity constraints')
    if constraints.get('schema') != 'shared-quantity-constraints/v1' or constraints.get('feasible') is not True:
        raise ValueError('Feasible explicit joint quantity constraints required')
    np_target = _joint_number(target_np_veh, 'Frozen NP cap')
    nuf_target = _joint_number(target_nuf_veh_h, 'Frozen NUF equality', nonnegative=True)
    nin_by_owner = mapping(constraints.get('net_inflow_veh_by_owner'), 'Accepted NP by owner')
    nuf_by_owner = mapping(constraints.get('meter_rate_veh_h_by_owner'), 'Finalized NUF by owner')
    if set(nin_by_owner) != owners - {'FW_E', 'FW_W'} or set(nuf_by_owner) != {'FW_E', 'FW_W'}:
        raise ValueError('Quantity owner catalogs are incomplete')
    nin = math.fsum(_joint_number(nin_by_owner[o], 'Owner NP') for o in sorted(nin_by_owner))
    meters = control.ramp_metering
    from evaluation.controllers import physical_ramp_branches
    physical = cfg is not None and physical_ramp_branches.enabled(cfg)
    if physical:
        physical_ramp_branches.prepare_control(control.copy(),cfg)
        window=mapping(constraints.get('window'),'Physical merge window')
        start=_joint_number(window.get('start_sec'),'Physical merge start',nonnegative=True)
        end=_joint_number(window.get('end_sec'),'Physical merge end',nonnegative=True)
        quantity=mapping(constraints.get('physical_ramp_merge'),'Physical merge quantity')
        if (constraints.get('nuf_definition') != 'predicted_accepted_mainline_merge'
                or area.get('predicted_ramp_merge') != quantity):
            raise ValueError('Final NUF must match the captured physical merge response')
        rates,physical_owners=physical_ramp_branches.checked_merge_rates(quantity,cfg,start_sec=start,end_sec=end)
        if physical_owners != nuf_by_owner:
            raise ValueError('Final NUF owner totals differ from physical merges')
        nuf=math.fsum(rates.values())
    else:
        if len(meters) != 4:
            raise ValueError('Four finalized grouped meter rates required; eight branches need their explicit config')
        nuf = math.fsum(meters.values())
    # A sum of two already rounded owner subtotals can differ from fsum of
    # all four coordinates. This guards only aggregation roundoff, not budgets.
    owner_nuf = math.fsum(_joint_number(nuf_by_owner[o], 'Owner NUF', nonnegative=True)
                         for o in sorted(nuf_by_owner))
    if abs(owner_nuf - nuf) > 2 * math.ulp(nuf):
        raise ValueError('Owner NUF differs from final meter rates')
    for channel, mode, unit, actual, target in (
            ('np', 'cap', 'veh', nin, np_target),
            ('nuf', 'equality', 'veh/h', nuf, nuf_target)):
        row = mapping(constraints.get(channel), channel + ' constraint')
        residual = actual - target
        excess = max(0., residual) if channel == 'np' else abs(residual)
        tolerance = _joint_number(row.get('tolerance'), channel + ' tolerance', nonnegative=True)
        expected = {'mode': mode, 'unit': unit, 'actual': actual, 'target': target,
                    'residual': residual, 'violation': excess}
        for key in ('actual', 'target', 'residual', 'violation'):
            _joint_number(row.get(key), channel + ' ' + key)
        if (any(row.get(key) != value for key, value in expected.items())
                or row.get('constraint_checked') is not True or row.get('satisfied') is not True
                or excess > tolerance):
            raise ValueError('Frozen ' + channel + ' constraint is inconsistent or violated')
    if control.N_P_star != np_target or control.N_UF_star != (nuf_target if physical else nuf):
        raise ValueError('Final action must retain NP cap and its declared NUF target semantics')
    records = mapping(game.get('per_owner'), 'Final owner checks')
    if set(records) != owners:
        raise ValueError('Final owner check catalog is incomplete')
    for owner, row in records.items():
        row = mapping(row, 'Final check ' + owner)
        if type(row.get('complete')) is not bool:
            raise ValueError('Explicit owner check completion required')
        if row['complete']:
            _joint_number(row.get('gap'), 'Finite owner gap', nonnegative=True)
        elif row.get('gap') is not None:
            raise ValueError('Incomplete owner gap must remain unknown')
    complete, certified = game.get('final_check_complete'), game.get('certified')
    if type(complete) is not bool or type(certified) is not bool:
        raise ValueError('Explicit finite check/certificate status required')
    error = game.get('error')
    if error is not None and (not isinstance(error, dict)
            or error.get('kind') not in ('time_budget', 'evaluation_budget', 'decision_deadline')):
        raise ValueError('Joint callback failure cannot be a leader response')
    gap = game.get('maximum_finite_candidate_gap')
    if complete != (error is None and all(row['complete'] for row in records.values())):
        raise ValueError('Final check completion is inconsistent')
    if complete:
        if _joint_number(gap, 'Maximum finite gap', nonnegative=True) != max(row['gap'] for row in records.values()):
            raise ValueError('Maximum finite gap differs from owner checks')
    elif gap is not None:
        raise ValueError('Incomplete final check must retain unknown maximum gap')
    tolerance = _joint_number(limits.get('improvement_tolerance'), 'Finite improvement tolerance', nonnegative=True)
    if certified != (complete and gap <= tolerance):
        raise ValueError('Finite neighborhood certificate is inconsistent')
    for field in ('sweeps_started', 'sweeps_completed', 'evaluations'):
        if type(game.get(field)) is not int or game[field] < 0:
            raise ValueError('Nonnegative integer game counter required: ' + field)
    if game['sweeps_completed'] > game['sweeps_started']:
        raise ValueError('Completed sweeps exceed started sweeps')
    diagnostics = {'schema': 'joint-shared-leader-response/v1',
        'objective_veh_h': objective, 'final_action_token': digest,
        'response_token': token(score.get('response_token'), 'Captured response'),
        'fixed_inputs_token': token(response.get('fixed_inputs_token'), 'Fixed game inputs'),
        'frozen_context_token': token(score.get('frozen_context_token'), 'Fixed response context'),
        'quantity_constraints': copy.deepcopy(constraints),
        'model_constraint_coverage': copy.deepcopy(coverage),
        'conditional_model_feasibility_witness': True,
        'resource_max_exceedance_veh': violation,
        'native_prehead_reference_overdraw_veh': _joint_number(
            score.get('native_prehead_reference_overdraw_veh'), 'Unresolved prehead reference overdraw'),
        'finite_neighborhood_certified': certified, 'final_check_complete': complete,
        'maximum_finite_candidate_gap': gap, 'per_owner': copy.deepcopy(records),
        'per_owner_scope': 'Final-gap audit at the final incumbent; unvisited does not imply no search',
        'search': {
            'scope': 'Producer search history at sweep incumbents; not the final-gap audit or a certificate',
            **{field: copy.deepcopy(game.get(field)) for field in
               ('search_sweeps', 'accepted_updates', 'traversal', 'neighbor_calls')},
            'missing_producer_fields': [field for field in
                ('search_sweeps', 'accepted_updates', 'traversal', 'neighbor_calls') if field not in game]},
        'search_status': game.get('search_status'), 'error': copy.deepcopy(error),
        'sweeps_started': game['sweeps_started'], 'sweeps_completed': game['sweeps_completed'],
        'evaluations': game['evaluations'], 'legacy_residuals_computed': False,
        'leader_target_changed': False, 'final_csv_verified': False,
        'shared_capacity_certificate': False, 'native_plant_feasibility_certified': False}
    return {'control': copy.deepcopy(control), 'objective_value': objective,
            'iterations': game['sweeps_completed'], 'converged': False,
            'residual_objective': None, 'residual_control': None,
            'diagnostics': {'joint_shared_response': diagnostics}}


def verify_joint_written_action(response, control, cfg, mapping, segment_vsl_values,
                                ramp_actions, metadata, actuation, *,
                                signal_group_plan_table, offset_writer,
                                action_json_path=None, action_csv_path=None):
    """Bind an already validated joint winner to prewrite/actual command files.

    Resolved VSL values and meter actions are the SAME values already obtained
    by the canonical writer, not additional runtime callbacks or allocations.
    Paths are both absent for prewrite, both present after the writer closes.
    Live diagnostics/provenance may grow, but seven scored action fields and
    every ordered physical CSV column must remain exact. Native execution is
    always pending here. Failures never rewrite or delete existing artifacts.
    """
    import copy
    import csv
    import hashlib
    import io
    import json
    import pickle
    from pathlib import Path
    from evaluation.controllers import action_csv_schema
    from evaluation.controllers import vissim_stackelberg_adapter as adapter

    fields = ('N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times',
              'offsets', 'inflow_outflow_allocation')
    csv_fields = tuple(action_csv_schema.ACTION_CSV_FIELDS)
    physical_fields = tuple(key for key in csv_fields if key != 'metadata')
    def require(ok, message):
        if not ok:
            raise ValueError(message)
    def digest(data):
        return hashlib.sha256(data).hexdigest()
    def canonical(value):
        return json.dumps(value, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=False, allow_nan=False).encode('utf-8')
    def action_fields(action):
        values = action if isinstance(action, dict) else vars(action)
        require(set(fields).issubset(values), 'Complete seven final action fields required')
        out = {}
        for field in fields:
            value = values[field]
            if field in fields[:2]:
                out[field] = _joint_number(value, field)
            else:
                require(isinstance(value, dict), 'Action field must be a mapping: ' + field)
                require(all(type(k) is str and k for k in value), 'Invalid action address: ' + field)
                out[field] = {k: _joint_number(v, field + ':' + k,
                    nonnegative=field == 'ramp_metering') for k, v in value.items()}
        return out
    def serialize(rows):
        require(isinstance(rows, (list, tuple)) and bool(rows), 'Ordered command rows required')
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=csv_fields)
        writer.writeheader()
        for row in rows:
            require(isinstance(row, dict) and set(row).issubset(csv_fields), 'Invalid command CSV columns')
            for key, value in row.items():
                require(value is None or type(value) in (str, int, float), 'Invalid command CSV scalar')
                if type(value) in (int, float):
                    require(math.isfinite(value), 'Nonfinite command CSV scalar: ' + key)
            writer.writerow(row)
        raw = stream.getvalue().encode('utf-8')
        parsed = list(csv.DictReader(io.StringIO(raw.decode('utf-8'), newline='')))
        return raw, parsed
    def physical(rows):
        return [tuple(row[key] for key in physical_fields) for row in rows]

    require((action_json_path is None) == (action_csv_path is None), 'Supply both written JSON/CSV paths or neither')
    require(isinstance(response, dict), 'Validated joint response required')
    game, score, evidence = (response.get(k) for k in ('game', 'final_score', 'command_evidence'))
    held = response.get('schema') == 'validated-decision-hold/v1'
    require(all(isinstance(v, dict) for v in (score, evidence)), 'Scored response and command evidence required')
    if held:
        require(response.get('feasible') is True and response.get('finite_neighborhood_certified') is False
                and response.get('maximum_finite_candidate_gap') is None, 'Invalid validated hold status')
        coverage = score.get('model_constraint_coverage', {})
        require(score.get('conditional_model_feasibility_witness') is True and coverage.get('complete') is True
                and coverage.get('conditional_model_feasibility_witness') is True
                and score['resource_summary']['max_exceedance_veh'] <= response['shared_tolerance']
                and score['quantity_constraints']['feasible'] is True,
                'Held response no longer has complete feasible model evidence')
        physical_eight = bool(getattr(cfg.network, 'physical_ramp_branches', None))
        require(set(response['directional_constraints']) == (set() if physical_eight else {'FW_W', 'FW_E'})
                and all(abs(v['actual']-v['target']) <= v['tolerance'] for v in response['directional_constraints'].values()),
                'Held response violates its directional NUF target')
        scored = response.get('control')
    else:
        require(isinstance(game, dict), 'Scored joint game response required')
        scored = game.get('control')
    require(scored is not None, 'Scored final control required')
    action_token = digest(pickle.dumps(scored, protocol=5))
    require(response.get('final_action_token') == action_token and score.get('action_token') == action_token,
            'Final action token differs from scored full action')
    owners = evidence.get('owner_physical_sha256')
    require(isinstance(owners, dict) and len(owners) == 19 and owners == score.get('physical_owner_tokens'),
            'Command evidence differs from scored physical owner tokens')
    expected_fields = canonical(action_fields(scored))
    require(canonical(action_fields(control)) == expected_fields, 'Final seven action fields differ from scored action')
    _, scored_rows = serialize(evidence.get('ordered_rows'))
    private = copy.deepcopy(control)
    expected_rows = tuple(adapter.iter_action_csv_rows(private, cfg, mapping,
        segment_vsl_values, ramp_actions, metadata, actuation, signal_group_plan_table, offset_writer))
    require(canonical(action_fields(private)) == expected_fields, 'Command iterator changed scored action fields')
    expected_bytes, live_rows = serialize(expected_rows)
    require(physical(live_rows) == physical(scored_rows), 'Live ordered physical CSV rows differ from scored command evidence')
    result = {'schema': 'joint-written-command-binding/v1',
        'phase': 'prewrite' if action_json_path is None else 'postwrite',
        'prewrite_binding_passed': True, 'written_command_binding_passed': False,
        'scored_action_token': action_token, 'seven_action_fields': list(fields),
        'seven_action_fields_sha256': digest(expected_fields), 'ordered_row_count': len(live_rows),
        'ordered_physical_rows_sha256': digest(canonical(physical(live_rows))),
        'expected_live_metadata_sha256': digest(canonical([r['metadata'] for r in live_rows])),
        'expected_csv_sha256': digest(expected_bytes),
        'native_execution_passed': None, 'native_execution_status': 'pending',
        'scope': 'Scored model fields and written command files only; no native application or traffic certificate'}
    if held:
        result.update(response_kind='validated_actual_hold', nash_result=False, final_gap_checked=False)
    if action_json_path is not None:
        json_path, csv_path = Path(action_json_path), Path(action_csv_path)
        json_bytes, csv_bytes = json_path.read_bytes(), csv_path.read_bytes()
        payload = json.loads(json_bytes.decode('utf-8-sig'))
        require(canonical(action_fields(payload)) == expected_fields, 'Written JSON action fields differ from scored action')
        reader = csv.DictReader(io.StringIO(csv_bytes.decode('utf-8'), newline=''))
        require(reader.fieldnames == list(csv_fields), 'Written CSV header differs from canonical header')
        written_rows = list(reader)
        require(all(set(r) == set(csv_fields) and all(v is not None for v in r.values()) for r in written_rows),
                'Written CSV has missing or extra columns')
        require(physical(written_rows) == physical(scored_rows), 'Written ordered physical CSV rows differ from scored evidence')
        require([r['metadata'] for r in written_rows] == [r['metadata'] for r in live_rows],
                'Written CSV metadata differs from expected live metadata')
        require(csv_bytes == expected_bytes, 'Written CSV binary serialization differs from canonical iterator')
        result.update(written_command_binding_passed=True,
            action_json={'path': str(json_path.resolve()), 'sha256': digest(json_bytes)},
            action_csv={'path': str(csv_path.resolve()), 'sha256': digest(csv_bytes)})
    return result


def _joint_catalog(follower):
    net = follower.cfg.network
    signals = tuple(net.signals)
    if not signals or len(set(signals)) != len(signals) or set(follower._local_models) != set(signals):
        raise ValueError('Exact configured urban owner catalog required')
    kinds = ('boundary_in', 'off_ramp', 'boundary_out', 'on_ramp', 'internal')
    expected_owned = set()
    nonowner = {}
    for movement, spec in net.urban_movements.items():
        signal, kind = spec['signal'], spec['kind']
        if not isinstance(signal, str) or not signal or kind not in kinds:
            raise ValueError('Every configured movement needs an explicit signal and supported kind')
        if signal in signals:
            expected_owned.add(movement)
        else:
            if spec['phase'] != '':
                raise ValueError('Nonowner movement requires an explicitly empty controlled phase')
            nonowner[movement] = (signal, kind)
    catalog = {}
    for signal in signals:
        model = follower._local_models[signal]
        if model.signal != signal or set(model.kind_of) != set(model.movements):
            raise ValueError('Local model identity or kind catalog mismatch')
        for movement in model.movements:
            kind = model.kind_of[movement]
            if movement in catalog or kind not in kinds:
                raise ValueError('Duplicate movement owner or unsupported quantity kind')
            if (net.urban_movements[movement]['kind'] != kind
                    or net.urban_movements[movement]['signal'] != signal):
                raise ValueError('Local quantity signal/kind differs from the configured movement')
            catalog[movement] = (signal, kind)
    if set(catalog) != expected_owned:
        raise ValueError('Every controlled movement must have exactly its configured local owner')
    return signals, kinds, catalog, nonowner


def shared_urban_quantities(follower, response, *, start_sec, horizon_steps):
    """Kind-signed ACTUAL accepted service, not the old cycle-average proxy.

    This is an algorithm/leader-coordinate contract change: the old Wu nin(p1)
    reconstructs all phases and predicts served=min(available, averaged cap).
    Here every canonical movement:<id> transfer is counted once, including
    off-ramp service whose source is storage. Signs remain boundary_in/off_ramp
    +1, boundary_out/on_ramp -1, internal 0. Omega entry/TD are never substituted.
    A complete urban residence grid and physical movement inventory establish
    the zero-event context; absence of a positive accepted event then means 0.
    Configured nonowner signals with empty controlled phase remain dynamic;
    their accepted service is validated/reported separately, not assigned to
    a new strategic owner or silently included in the existing 17-owner NP.
    The caller owns trace/action identity and any target migration. No target,
    dual update, feasibility certificate or solver hook is changed here.
    """
    cfg = follower.cfg
    if not enabled(cfg) or response.get('schema') != 'control-area-fixed-response/v1':
        raise ValueError('Canonical captured Omega response required')
    signals, kinds, catalog, nonowner = _joint_catalog(follower)
    all_catalog = {**catalog, **nonowner}
    start = _joint_number(start_sec, 'start_sec', nonnegative=True)
    dt = _joint_number(cfg.simulation.T_u_sec, 'T_u_sec', nonnegative=True)
    dt_h = _joint_number(cfg.simulation.T_u_h, 'T_u_h', nonnegative=True)
    k = cfg.simulation.K_cu
    if dt == 0 or dt_h == 0 or type(k) is not int or k < 1 or type(horizon_steps) is not int or horizon_steps < 1:
        raise ValueError('Positive explicit urban clock and horizon required')
    first = int(round(start / dt))
    if abs(first * dt - start) > 1e-8:
        raise ValueError('Quantity start is not on the urban clock')
    count = horizon_steps * k
    samples = [r for r in response['residence'] if r['stage'] == 'urban']
    if len(samples) != count:
        raise ValueError('Incomplete quantity response horizon')
    for i, row in enumerate(samples):
        if (row['start_sec'] != (first+i)*dt or row['end_sec'] != (first+i+1)*dt
                or row['dt_h'] != dt_h):
            raise ValueError('Quantity response has another urban clock')
        for movement in all_catalog:
            _joint_number(row['model_stock_veh']['movement:' + movement], movement, nonnegative=True)
    served = {m: 0. for m in all_catalog}
    nonowner_signals = tuple(dict.fromkeys(s for s, _ in nonowner.values()))
    events = {s: 0 for s in signals + nonowner_signals}
    for row in response['transfers']:
        key = row['route_key']
        if not isinstance(key, str):
            raise ValueError('Canonical route key must be text')
        if not key.startswith('movement:'):
            continue
        movement = key[len('movement:'):]
        if movement not in all_catalog:
            raise ValueError('Unknown accepted movement route')
        offset = (_joint_number(row['start_sec'], 'event start') - start) / dt
        index = int(round(offset))
        if (row['stage'] != 'urban' or abs(offset-index) > 1e-8 or not 0 <= index < count
                or row['end_sec'] != (first+index+1)*dt):
            raise ValueError('Accepted movement event has another urban clock')
        served[movement] = _joint_number(served[movement] +
            _joint_number(row['vehicles'], 'accepted vehicles', nonnegative=True), 'cumulative service')
        events[all_catalog[movement][0]] += 1
    owners = {}
    nonowner_by_signal = {}
    for signal in signals + nonowner_signals:
        by_kind = {kind: sum(served[m] for m, (s, knd) in all_catalog.items()
                             if s == signal and knd == kind) for kind in kinds}
        for kind, value in by_kind.items():
            _joint_number(value, kind + ' cumulative service')
        nin = by_kind['boundary_in'] + by_kind['off_ramp'] - by_kind['boundary_out'] - by_kind['on_ramp']
        _joint_number(nin, 'actual kind-signed quantity')
        output = owners if signal in signals else nonowner_by_signal
        output[signal] = {'by_kind_veh': by_kind, 'net_inflow_veh': nin,
                           'accepted_event_count': events[signal]}
    result = {'schema': 'shared-urban-kind-service/v1', 'owners': owners,
            'served_by_movement_veh': served, 'unit': 'veh',
            'nonowner_service': {'by_signal': nonowner_by_signal,
                'served_by_movement_veh': {m: served[m] for m in nonowner},
                'included_in_owner_np': False,
                'constant_traffic_assumed': False},
            'provenance': {'response_schema': response['schema'], 'start_sec': start,
                'end_sec': (first+count)*dt, 'urban_samples': count,
                'movement_catalog': {m: {'owner': s, 'kind': kind} for m, (s, kind) in catalog.items()},
                'nonowner_movement_catalog': {m: {'signal': s, 'kind': kind, 'phase': ''}
                                              for m, (s, kind) in nonowner.items()},
                'configured_movement_count': len(all_catalog), 'owned_movement_count': len(catalog),
                'nonowner_movement_count': len(nonowner),
                'zero_events': 'zero accepted service within complete captured urban grid',
                'quantity_definition': 'actual accepted movement service with legacy kind signs',
                'legacy_cycle_average_equivalent': False, 'omega_crossing_quantity': False,
                'trace_action_identity_certified': False}}
    from evaluation.controllers import physical_ramp_branches
    if physical_ramp_branches.enabled(follower.cfg):
        result['predicted_ramp_merge'] = physical_ramp_branches.predicted_merge_quantity(
            response, follower.cfg, start_sec=start, end_sec=(first+count)*dt)
    return result


def _joint_channel(values, refs, prices, inactive, weight, label, *, cycle=None):
    """Explicit None disables a channel; sparse prices need declared inactive addresses."""
    keys = set(values)
    inactive = tuple(inactive)
    if len(set(inactive)) != len(inactive):
        raise ValueError(label + ' has duplicate inactive addresses')
    if prices is None:
        if refs not in (None, {}) or inactive:
            raise ValueError(label + ' inactive channel has references/address declarations')
        return {key: 0. for key in values}
    if (not isinstance(prices, dict) or not isinstance(refs, dict)
            or set(prices) & set(inactive) or set(prices) | set(inactive) != keys
            or set(refs) != set(prices)):
        raise ValueError(label + ' price/reference/inactive catalog mismatch')
    weight = _joint_number(weight, label + ' weight', nonnegative=True)
    result = {}
    for key, value in values.items():
        if key in inactive:
            result[key] = 0.
            continue
        delta = value - _joint_number(refs[key], label + ' reference')
        if cycle is not None:
            period = cycle[key]
            delta = ((delta + period/2.) % period) - period/2.
        result[key] = weight * _joint_number(prices[key], label + ' price') * delta
        _joint_number(result[key], label + ' cost')
    return result


def _validate_joint_quantity_catalog(quantities, signals, catalog, nonowner):
    if (quantities.get('schema') != 'shared-urban-kind-service/v1' or quantities.get('unit') != 'veh'
            or set(quantities['owners']) != set(signals)
            or quantities['provenance']['movement_catalog'] !=
                {m: {'owner': s, 'kind': k} for m, (s, k) in catalog.items()}
            or quantities['provenance']['nonowner_movement_catalog'] !=
                {m: {'signal': s, 'kind': k, 'phase': ''} for m, (s, k) in nonowner.items()}):
        raise ValueError('Quantity definition/owner catalog mismatch')


def _joint_quantity_nin(row, kinds):
    if set(row['by_kind_veh']) != set(kinds):
        raise ValueError('Quantity kind catalog mismatch')
    by_kind = {k: _joint_number(row['by_kind_veh'][k], k, nonnegative=True) for k in kinds}
    nin = by_kind['boundary_in'] + by_kind['off_ramp'] - by_kind['boundary_out'] - by_kind['on_ramp']
    if _joint_number(row['net_inflow_veh'], 'net inflow') != nin:
        raise ValueError('Quantity total differs from its signed kinds')
    return nin


def shared_quantity_constraints(follower, action, quantities, *, start_sec, horizon_steps,
                                np_mode, target_np_veh, np_tolerance_veh,
                                nuf_mode, target_nuf_veh_h, nuf_tolerance_veh_h):
    """Check a shared NP cap and/or a global finalized-rate NUF equality.

    NP is the SUM of all configured 17 owners' actual accepted kind-signed
    service [veh], excluding explicitly reported nonowner service. There are
    no per-owner quotas and no replacement by Omega entry/TD. Caller binds
    this captured quantity to the candidate, state and common response; its
    catalog and explicit start/horizon are checked here. This actual-service
    quantity is an algorithm change from the legacy cycle-average proxy.

    In legacy mode NUF is the sum of four finalized grouped meter rates [veh/h], NOT
    accepted release and NOT action.N_UF_star (whose meaning depends on the
    outer policy). The supplied target is frozen; it is never expanded.
    Directional budgets, physical meter-grid realization and other shared
    resource constraints remain canonical candidate/neighbor checks. This
    helper certifies only the enabled quantity inequalities/equality.
    Dual/inactive channels return residuals but add no hard constraint or cost.
    Physical eight-branch mode instead uses the captured actual accepted
    mainline merge rate, averaged over this same explicit horizon. It never
    substitutes the sum of physical service ceilings or changes the target.
    All tolerances are caller-supplied absolute tolerances in the stated unit.
    """
    if np_mode not in ('dual', 'inactive', 'cap') or nuf_mode not in ('dual', 'equality'):
        raise ValueError('Explicit supported shared quantity policies required')
    signals, kinds, catalog, nonowner = _joint_catalog(follower)
    net, sim = follower.cfg.network, follower.cfg.simulation
    freeway = tuple(net.freeway_links)
    if (len(signals) != 17 or len(freeway) != 2 or set(freeway) != {'FW_E', 'FW_W'}
            or set(follower._local_freeway_models) != set(freeway)):
        raise ValueError('Shared quantity constraints require exact 17 urban plus two FW owners')
    _validate_joint_quantity_catalog(quantities, signals, catalog, nonowner)
    start = _joint_number(start_sec, 'start_sec', nonnegative=True)
    dt = _joint_number(sim.T_u_sec, 'T_u_sec', nonnegative=True)
    dt_h = _joint_number(sim.T_u_h, 'T_u_h', nonnegative=True)
    if (dt == 0 or dt_h == 0 or type(sim.K_cu) is not int or sim.K_cu < 1
            or type(horizon_steps) is not int or horizon_steps < 1):
        raise ValueError('Positive explicit urban clock and horizon required')
    first, count = int(round(start/dt)), horizon_steps*sim.K_cu
    provenance = quantities['provenance']
    if (abs(first*dt-start) > 1e-8 or provenance['response_schema'] != 'control-area-fixed-response/v1'
            or provenance['start_sec'] != start or provenance['end_sec'] != (first+count)*dt
            or type(provenance['urban_samples']) is not int or provenance['urban_samples'] != count
            or provenance['configured_movement_count'] != len(catalog)+len(nonowner)
            or provenance['owned_movement_count'] != len(catalog)
            or provenance['nonowner_movement_count'] != len(nonowner)):
        raise ValueError('Quantity provenance differs from the explicit state clock/horizon/catalog')
    nin_by_owner = {s: _joint_quantity_nin(quantities['owners'][s], kinds) for s in signals}
    ramp_owner = {}
    from evaluation.controllers import physical_ramp_branches
    physical = physical_ramp_branches.enabled(follower.cfg)
    for link in freeway:
        model = follower._local_freeway_models[link]
        if model.link != link or len(model.owned_ramps) != (4 if physical else 2):
            raise ValueError('Each FW quantity owner requires its two configured meters')
        for ramp in model.owned_ramps:
            if ramp in ramp_owner or net.ramp_to_freeway[ramp] != link:
                raise ValueError('Duplicate or inconsistent ramp ownership')
            ramp_owner[ramp] = link
    if (set(ramp_owner) != set(net.ramps) or set(net.ramp_to_freeway) != set(ramp_owner)
            or set(action.ramp_metering) != set(ramp_owner)):
        raise ValueError('Complete finalized grouped meter catalog required')
    meters = {r: _joint_number(action.ramp_metering[r], r, nonnegative=True) for r in sorted(ramp_owner)}
    nin = _joint_number(math.fsum(nin_by_owner[s] for s in sorted(signals)), 'total actual NP')
    nuf = _joint_number(math.fsum(meters.values()), 'total finalized NUF', nonnegative=True)
    nuf_by_owner = {link: math.fsum(meters[r] for r in meters if ramp_owner[r] == link) for link in freeway}
    if physical:
        actual_rates, nuf_by_owner = physical_ramp_branches.checked_merge_rates(
            quantities.get('predicted_ramp_merge'), follower.cfg, start_sec=start, end_sec=(first+count)*dt)
        nuf = math.fsum(actual_rates.values())
    target_np = _joint_number(target_np_veh, 'N_P target')
    target_nuf = _joint_number(target_nuf_veh_h, 'N_UF target', nonnegative=True)
    np_tol = _joint_number(np_tolerance_veh, 'N_P tolerance', nonnegative=True)
    nuf_tol = _joint_number(nuf_tolerance_veh_h, 'N_UF tolerance', nonnegative=True)
    np_residual = _joint_number(nin-target_np, 'N_P residual')
    nuf_residual = _joint_number(nuf-target_nuf, 'N_UF residual')
    np_violation, nuf_violation = max(0., np_residual), abs(nuf_residual)
    np_ok = np_violation <= np_tol if np_mode == 'cap' else None
    nuf_ok = nuf_violation <= nuf_tol if nuf_mode == 'equality' else None
    return {'schema': 'shared-quantity-constraints/v1',
            'np': {'mode': np_mode, 'unit': 'veh', 'actual': nin, 'target': target_np,
                   'residual': np_residual, 'violation': np_violation,
                   'tolerance': np_tol, 'constraint_checked': np_mode == 'cap', 'satisfied': np_ok},
            'nuf': {'mode': nuf_mode, 'unit': 'veh/h', 'actual': nuf, 'target': target_nuf,
                    'residual': nuf_residual, 'violation': nuf_violation,
                    'tolerance': nuf_tol, 'constraint_checked': nuf_mode == 'equality', 'satisfied': nuf_ok},
            'feasible': np_ok is not False and nuf_ok is not False,
            'net_inflow_veh_by_owner': nin_by_owner,
            'meter_rate_veh_h_by_owner': nuf_by_owner,
            **({'nuf_definition': 'predicted_accepted_mainline_merge',
                'physical_ramp_merge': deepcopy(quantities['predicted_ramp_merge'])} if physical else {}),
            'window': {'start_sec': start, 'end_sec': (first+count)*dt,
                       'horizon_steps': horizon_steps, 'urban_samples': count},
            'nonowner_service_included_in_np': False, 'individual_np_quotas_created': False,
            'directional_nuf_constraints_checked': False, 'quantity_constraints_only': True,
            'physical_feasibility_certified': False, 'leader_target_changed': False}


def fixed_joint_price_terms(follower, action, quantities, *, lambda_p, lambda_uf,
                            target_np_veh, target_nuf_veh_h, price_context):
    """Add fixed local external prices/quantity terms; never optimize or mutate.

    Required context keys: leader_present=True; np_mode='dual'/'inactive'/'cap';
    nuf_mode='dual'/'equality'; inactive_price_addresses={phase,offset,vsl,meter}.
    Each inactive-address collection explicitly closes a sparse active price
    map; None alone means an entirely inactive channel. Active references are
    required, never inferred from the candidate. Phase addresses are SC_phase.
    Full-phase prices replace scalar-green prices here (no scalar/cross double
    addition). Expanded VSL seg prices are used exactly once, without repricing
    zone repetitions or the derived bare-link minimum alias.
    Circular offsets use each configured signal_cycle_length, correcting the
    legacy global-cycle price wrap when physical owner cycles differ.

    External terms retain configured weights and references. Lambda_P[h] times
    actual kind-signed service[veh] and lambda_UF[h^2] times FINAL grouped meter
    rate[veh/h] are separate. Target constants are returned in residuals, not
    silently modified or added once per owner. Realization/command identity,
    fixed-round context, price FD provenance and capacity checks belong to the
    caller. PFO, active cross-price and soft-anchor policies fail explicitly.
    NP cap requires lambda_P=0; shared_quantity_constraints checks the total
    hard cap separately. NUF equality likewise requires lambda_UF=0 and its
    hard residual/tolerance check is separate, never replaced by a penalty.
    No local base cost, smoothness, global J substitution or dual update here.
    """
    required = {'leader_present', 'np_mode', 'nuf_mode', 'inactive_price_addresses'}
    if (not isinstance(price_context, dict) or set(price_context) != required
            or price_context['leader_present'] is not True
            or price_context['np_mode'] not in ('dual', 'inactive', 'cap')
            or price_context['nuf_mode'] not in ('dual', 'equality')):
        raise ValueError('Explicit supported fixed-leader price policy required')
    inactive = price_context['inactive_price_addresses']
    if not isinstance(inactive, dict) or set(inactive) != {'phase', 'offset', 'vsl', 'meter'}:
        raise ValueError('Explicit inactive address collections required for all price channels')
    if follower.green_offset_cross_price is not None or follower.vsl_meter_cross_price is not None:
        raise ValueError('Active cross-price policy is not part of the additive full-vector contract')
    if (follower.metering_marginal_price is not None and not follower.metering_price_split
            and price_context['nuf_mode'] != 'dual'):
        raise ValueError('Equality with non-split priced metering implies an unsupported soft anchor')
    signals, kinds, catalog, nonowner = _joint_catalog(follower)
    net = follower.cfg.network
    freeway = tuple(net.freeway_links)
    models = follower._local_freeway_models
    if len(set(freeway)) != len(freeway) or set(models) != set(freeway) or set(signals) & set(freeway):
        raise ValueError('Exact disjoint configured owner catalogs required')
    if (set(follower._phase_movements) != set(signals) or any(
            set(follower._phase_movements[s]) != {'p1', 'p2', 'p3', 'p4'} for s in signals)):
        raise ValueError('Every urban owner requires all four phase addresses, including dark phases')
    phase_owner = {signal + '_' + phase: signal for signal in signals
                   for phase in follower._phase_movements[signal]}
    vsl_owner = {f'{link}__seg{i}': link for link in freeway for i in range(models[link].n_seg)}
    ramp_owner = {}
    for link in freeway:
        if models[link].link != link:
            raise ValueError('Freeway model owner mismatch')
        for ramp in models[link].owned_ramps:
            if ramp in ramp_owner or net.ramp_to_freeway[ramp] != link:
                raise ValueError('Duplicate or inconsistent ramp ownership')
            ramp_owner[ramp] = link
    if set(ramp_owner) != set(net.ramps):
        raise ValueError('Every configured ramp must have one freeway owner')
    if (set(action.green_times) != set(phase_owner) or set(action.offsets) != set(signals)
            or set(action.ramp_metering) != set(ramp_owner)
            or set(action.vsl) != set(vsl_owner) | set(freeway)):
        raise ValueError('Complete realized four-lever action required')
    green = {k: _joint_number(v, k, nonnegative=True) for k, v in action.green_times.items()}
    offsets = {k: _joint_number(v, k) for k, v in action.offsets.items()}
    vsl = {k: _joint_number(action.vsl[k], k, nonnegative=True) for k in vsl_owner}
    meters = {k: _joint_number(v, k, nonnegative=True) for k, v in action.ramp_metering.items()}
    for link in freeway:
        if _joint_number(action.vsl[link], link) != min(vsl[k] for k in vsl if vsl_owner[k] == link):
            raise ValueError('Derived VSL minimum alias does not match expanded cells')
    phase_prices = follower.signal_phase_price
    phase_refs = follower.signal_phase_price_ref
    if phase_prices is not None:
        phase_prices = {s+'_'+p: v for s, by_phase in phase_prices.items() for p, v in by_phase.items()}
        if not isinstance(phase_refs, dict):
            raise ValueError('Active phase references required')
        phase_refs = {s+'_'+p: v for s, by_phase in phase_refs.items() for p, v in by_phase.items()}
    cycles = {s: _joint_number(net.signal_cycle_length(s), s + ' cycle', nonnegative=True) for s in signals}
    if any(period == 0 for period in cycles.values()):
        raise ValueError('Circular offset price requires a positive cycle')
    channels = {
        'phase': _joint_channel(green, phase_refs, phase_prices, inactive['phase'],
                                follower.signal_phase_price_weight, 'phase'),
        'offset': _joint_channel(offsets, follower.offset_marginal_price_ref,
            follower.offset_marginal_price, inactive['offset'], follower.offset_marginal_price_weight,
            'offset', cycle=cycles),
        'vsl': _joint_channel(vsl, follower.vsl_marginal_price_ref, follower.vsl_marginal_price,
                              inactive['vsl'], follower.vsl_marginal_price_weight, 'vsl'),
        'meter': _joint_channel(meters, follower.metering_marginal_price_ref,
            follower.metering_marginal_price, inactive['meter'], follower.metering_marginal_price_weight, 'meter')}
    _validate_joint_quantity_catalog(quantities, signals, catalog, nonowner)
    lp = _joint_number(lambda_p, 'lambda_P', nonnegative=True)
    lu = _joint_number(lambda_uf, 'lambda_UF')
    if ((price_context['np_mode'] in ('inactive', 'cap') and lp != 0)
            or (price_context['nuf_mode'] == 'equality' and lu != 0)):
        raise ValueError('Inactive dual channel has a nonzero price')
    target_np = _joint_number(target_np_veh, 'N_P target')
    target_nuf = _joint_number(target_nuf_veh_h, 'N_UF target', nonnegative=True)
    owners = {s: {name: 0. for name in ('phase', 'offset', 'vsl', 'meter', 'lambda_P', 'lambda_UF')}
              for s in signals + freeway}
    for channel, addresses in (('phase', phase_owner), ('offset', {s: s for s in signals}),
                               ('vsl', vsl_owner), ('meter', ramp_owner)):
        for address, cost in channels[channel].items():
            owners[addresses[address]][channel] += cost
    nin_by_owner = {}
    for signal in signals:
        nin = _joint_quantity_nin(quantities['owners'][signal], kinds)
        nin_by_owner[signal] = nin
        owners[signal]['lambda_P'] = lp * nin
    rates_by_owner = {link: sum(meters[r] for r in meters if ramp_owner[r] == link) for link in freeway}
    total_nuf = sum(meters.values())
    from evaluation.controllers import physical_ramp_branches
    if physical_ramp_branches.enabled(follower.cfg):
        provenance = quantities['provenance']
        actual_rates, rates_by_owner = physical_ramp_branches.checked_merge_rates(
            quantities.get('predicted_ramp_merge'), follower.cfg,
            start_sec=provenance['start_sec'], end_sec=provenance['end_sec'])
        total_nuf = math.fsum(actual_rates.values())
    for link in freeway:
        owners[link]['lambda_UF'] = lu * rates_by_owner[link]
    for terms in owners.values():
        terms['total'] = _joint_number(sum(terms.values()), 'fixed additive owner price')
    np_residual = _joint_number(sum(nin_by_owner.values()) - target_np, 'N_P residual')
    nuf_residual = _joint_number(total_nuf - target_nuf, 'N_UF residual')
    return {'owners': owners, 'net_inflow_veh': nin_by_owner, 'meter_rate_veh_h': rates_by_owner,
            'target_np_veh': target_np, 'target_nuf_veh_h': target_nuf,
            'np_residual_veh': np_residual, 'nuf_residual_veh_h': nuf_residual,
            'units': {'cost': 'veh*h', 'lambda_P': 'h', 'lambda_UF': 'h^2',
                      'phase_offset_price': 'veh*h/s', 'vsl_price': 'veh*h/(km/h)', 'meter_price': 'h^2'},
            'scalar_green_channel_included': False, 'global_objective_substituted': False,
            'local_base_cost_included': False, 'feasibility_certified': False,
            'leader_target_changed': False, 'quantity_definition': 'actual accepted kind-signed service'}


def _joint_native_price_nodes(net, context):
    """Bind an optional measured native clock to the current frozen config."""
    nodes = {s: node for s, node in
        (getattr(net, 'signal_actuation_contract', {}) or {}).get('nodes', {}).items()
        if node.get('native_clock_basis') is not None}
    measured = context.get('native_clock_nodes', {})
    if not isinstance(measured, dict) or measured != nodes:
        raise ValueError('Measured native clock nodes differ from the configured price manifold')
    return nodes


def matched_external_secant(base, probe, *, owners, owner, coordinate):
    """Return a matched directional external-cost secant, not a phase gradient.

    Each explicit endpoint envelope has objective_veh_h, local_base_costs for
    all 19 owners, context, response_token, local_cost_response_token,
    physical_owner_tokens, model_owner_values,
    price_or_quantity_terms_included=False and
    local_cost_contains_omega_beta=False. Context is an equal mapping containing
    finite beta_seconds, frozen_digest and local_cost_definition; caller binds
    its digest to the same initial state, forecast, committed reference, leader
    targets, horizon, physical access definition and operational/source context.
    Both local and global values must come from that envelope's response token.
    model_owner_values maps every owner to its complete four-lever owned
    address/value map, including the FW bare-link minimum alias. Nonowner model
    values must be unchanged even when different rates write the same all-GREEN
    schedule. The changed owner's values must exactly match the coordinate
    (excluding only that derived alias); caller still binds each map to the
    action that produced its response, not merely to a proposed command.

    Coordinate fields: owner, kind (phase_exchange/offset/vsl/meter/joint_direction),
    parameter_unit (s/km/h/veh/h/1), signed nonzero displacement, base_values,
    probe_values, direction, address_kinds, address_owners, offset_cycles.
    The five address maps cover the owner's COMPLETE realized vector. Urban
    vectors contain owner_p1..p4 and owner offset; FW vectors contain contiguous
    owner__seg0..N-1 plus owned meters, without the derived bare-link VSL alias.
    Address provenance/complete FW ownership and physical tokens come from the
    canonical writer/owner catalog, not a new realizer in this arithmetic helper.

    Actual coordinate differences must equal displacement*direction. Offset
    differences use the supplied owner cycle's signed circular convention.
    Joint directions use a dimensionless path parameter, retaining every
    physical address/unit in the returned direction. Phase exchanges preserve
    the four-green sum and offset. An explicit native_clock_nodes mapping in
    the matched context instead binds source-clock validation; the supported
    concurrent p1/p2 clock preserves p2+p4 while p1 moves independently. No
    (n-1)/n rescaling or independent per-phase prices are invented. This is a
    finite secant on this edge, not a derivative,
    equilibrium certificate, new local optimization or a replacement for Ci.
    """
    import copy
    import json

    owners = tuple(owners)
    if (len(owners) != 19 or len(set(owners)) != 19 or owner not in owners
            or any(not isinstance(o, str) or not o for o in owners)):
        raise ValueError('Exact explicit 19-owner catalog and changed owner required')
    fields = {'objective_veh_h', 'local_base_costs', 'context', 'response_token',
              'local_cost_response_token', 'physical_owner_tokens', 'model_owner_values',
              'price_or_quantity_terms_included', 'local_cost_contains_omega_beta'}
    parsed = []
    for label, point in (('base', base), ('probe', probe)):
        if not isinstance(point, dict) or set(point) != fields:
            raise ValueError(label + ' needs the explicit matched endpoint envelope')
        if (point['price_or_quantity_terms_included'] is not False
                or point['local_cost_contains_omega_beta'] is not False):
            raise ValueError('Local base costs must exclude external/dual prices and Omega beta')
        context = point['context']
        if not isinstance(context, dict) or not {'beta_seconds', 'frozen_digest', 'local_cost_definition'} <= set(context):
            raise ValueError('Explicit beta and frozen physical local-cost context required')
        _joint_number(context['beta_seconds'], 'beta_seconds', nonnegative=True)
        if any(not isinstance(context[key], str) or not context[key]
               for key in ('frozen_digest', 'local_cost_definition')):
            raise ValueError('Frozen context identity/physical local-cost definition missing')
        try:
            context_text = json.dumps(context, sort_keys=True, separators=(',', ':'), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError('Context must contain explicit finite serializable values') from exc
        token = point['response_token']
        tokens = point['physical_owner_tokens']
        if (type(token) not in (str, bytes) or not token or point['local_cost_response_token'] != token
                or not isinstance(tokens, dict) or set(tokens) != set(owners)
                or any(type(v) not in (str, bytes) or not v for v in tokens.values())):
            raise ValueError('Response/local-source token or physical owner binding mismatch')
        costs = point['local_base_costs']
        if not isinstance(costs, dict) or set(costs) != set(owners):
            raise ValueError('Every local base cost is required, including other owners')
        local = {o: _joint_number(costs[o], label + ' local ' + o) for o in owners}
        model_values = point['model_owner_values']
        if not isinstance(model_values, dict) or set(model_values) != set(owners):
            raise ValueError('Every owner needs its complete model address values')
        seen_addresses = set()
        freeway_owners = set()
        for o, by_address in model_values.items():
            if (not isinstance(by_address, dict) or not by_address
                    or any(not isinstance(a, str) or not a for a in by_address)
                    or seen_addresses.intersection(by_address)):
                raise ValueError('Missing, invalid or overlapping model owner addresses')
            seen_addresses.update(by_address)
            for address, value in by_address.items():
                _joint_number(value, label + ' model ' + address)
            if o in ('FW_E', 'FW_W'):
                freeway_owners.add(o)
                segments = {a for a in by_address if a.startswith(o + '__seg')}
                meters = set(by_address) - segments - {o}
                physical_addresses = context.get('physical_meter_addresses_by_owner')
                if physical_addresses is not None:
                    if (not isinstance(physical_addresses, dict) or set(physical_addresses) != {'FW_E','FW_W'}
                            or any(not isinstance(v,list) or len(v) != 4 or len(set(v)) != 4 for v in physical_addresses.values())
                            or set(physical_addresses['FW_E']) & set(physical_addresses['FW_W'])
                            or meters != set(physical_addresses[o])):
                        raise ValueError('Physical secant meter addresses differ from the frozen owner catalog')
                meter_count = 4 if physical_addresses is not None else 2
                if (o not in by_address or not segments or len(meters) != meter_count
                        or segments != {f'{o}__seg{i}' for i in range(len(segments))}
                        or by_address[o] != min(by_address[a] for a in segments)):
                    raise ValueError('FW model values require expanded cells, all configured meters and exact bare alias')
            elif set(by_address) != {o + '_' + p for p in ('p1', 'p2', 'p3', 'p4')} | {o}:
                raise ValueError('Urban model values require four greens and offset')
        if freeway_owners != {'FW_E', 'FW_W'}:
            raise ValueError('Exact two-FW and seventeen-urban model owner inventory required')
        parsed.append((_joint_number(point['objective_veh_h'], label + ' J_Omega'), local, context_text))
    if parsed[0][2] != parsed[1][2]:
        raise ValueError('Base/probe beta, state, reference or frozen local-cost context differs')
    if base['response_token'] == probe['response_token']:
        raise ValueError('Distinct realized probes require distinct canonical response tokens')
    for o in owners:
        before_model, after_model = base['model_owner_values'][o], probe['model_owner_values'][o]
        if set(before_model) != set(after_model) or (o != owner and before_model != after_model):
            raise ValueError('Model owner inventory differs or a foreign model owner changed')
        same = base['physical_owner_tokens'][o] == probe['physical_owner_tokens'][o]
        if same == (o == owner):
            raise ValueError('Physical alias or a changed foreign owner')
    required = {'owner', 'kind', 'parameter_unit', 'displacement', 'base_values', 'probe_values',
                'direction', 'address_kinds', 'address_owners', 'offset_cycles'}
    if not isinstance(coordinate, dict) or set(coordinate) != required or coordinate['owner'] != owner:
        raise ValueError('Explicit realized coordinate and matching owner required')
    kind, unit = coordinate['kind'], coordinate['parameter_unit']
    units = {'phase_exchange': 's', 'offset': 's', 'vsl': 'km/h', 'meter': 'veh/h', 'joint_direction': '1'}
    if kind not in units or unit != units[kind]:
        raise ValueError('Unsupported directional coordinate or unit')
    step = _joint_number(coordinate['displacement'], 'realized displacement')
    if step == 0:
        raise ValueError('Zero realized displacement has no external secant')
    values = coordinate['base_values']
    maps = [coordinate[k] for k in ('probe_values', 'direction', 'address_kinds', 'address_owners')]
    if (not isinstance(values, dict) or not values or any(not isinstance(m, dict) or set(m) != set(values) for m in maps)
            or any(v != owner for v in coordinate['address_owners'].values())):
        raise ValueError('Complete realized address maps/ownership must agree')
    kinds = coordinate['address_kinds']
    if any(v not in ('green', 'offset', 'vsl', 'meter') for v in kinds.values()):
        raise ValueError('Unknown physical price address kind')
    groups = {k: {a for a in values if kinds[a] == k} for k in ('green', 'offset', 'vsl', 'meter')}
    urban = bool(groups['green'] or groups['offset'])
    if urban:
        if (groups['green'] != {owner+'_'+p for p in ('p1', 'p2', 'p3', 'p4')}
                or groups['offset'] != {owner} or groups['vsl'] or groups['meter']):
            raise ValueError('Urban secants require the full four-green plus offset vector')
    elif (not groups['vsl'] or not groups['meter'] or
          groups['vsl'] != {f'{owner}__seg{i}' for i in range(len(groups['vsl']))}):
        raise ValueError('FW secants require contiguous expanded VSL and owned meters; no derived alias')
    for point, field in ((base, 'base_values'), (probe, 'probe_values')):
        model_values = point['model_owner_values'][owner]
        model_coordinate = {a: v for a, v in model_values.items() if urban or a != owner}
        if model_coordinate != coordinate[field]:
            raise ValueError('Realized coordinate is not the changed owner model input')
    cycles = coordinate['offset_cycles']
    if not isinstance(cycles, dict) or set(cycles) != groups['offset']:
        raise ValueError('Every offset needs its actual owner cycle, with no extras')
    deltas = {}
    for address, value in values.items():
        before = _joint_number(value, 'base coordinate')
        after = _joint_number(coordinate['probe_values'][address], 'probe coordinate')
        delta = after - before
        if kinds[address] == 'offset':
            cycle = _joint_number(cycles[address], 'owner cycle', nonnegative=True)
            if cycle == 0:
                raise ValueError('Owner offset cycle must be positive')
            delta = ((delta + cycle/2.) % cycle) - cycle/2.
        direction = _joint_number(coordinate['direction'][address], 'realized direction')
        if not math.isclose(delta, step*direction, rel_tol=1e-12, abs_tol=0.):
            raise ValueError('Nominal displacement/direction differs from the realized coordinate')
        deltas[address] = _joint_number(delta, 'realized coordinate difference')
    changed = {kinds[a] for a, delta in deltas.items() if delta != 0.}
    expected = {'phase_exchange': {'green'}, 'offset': {'offset'}, 'vsl': {'vsl'}, 'meter': {'meter'}}
    if not changed or (kind in expected and changed != expected[kind]):
        raise ValueError('Zero/aliased coordinate or undeclared joint change')
    if urban:
        scale = max(1., *(abs(float(v)) for v in values.values()),
                    *(abs(float(v)) for v in coordinate['probe_values'].values()))
        conserved = groups['green']
        native_nodes = base['context'].get('native_clock_nodes', {})
        if (not isinstance(native_nodes, dict)
                or not set(native_nodes) <= set(owners)-{'FW_E', 'FW_W'}):
            raise ValueError('Explicit native urban clock node inventory required')
        if owner in native_nodes:
            from evaluation.controllers import signal_group_plan as plans
            node = plans.node_plan_from_json(native_nodes[owner])
            basis = node.native_clock_basis
            if (basis is None or node.node_id not in (owner, owner.removeprefix('SC'))
                    or cycles[owner] != basis['cycle_sec']):
                raise ValueError('Native clock owner or offset cycle differs from the matched coordinate')
            for field in ('base_values', 'probe_values'):
                greens = {p: coordinate[field][owner+'_'+p] for p in plans.MODEL_PHASES}
                plans.native_phase_windows(node, greens, basis['amber_sec'], basis['all_red_sec'])
            if basis['kind'] == 'concurrent_p1_p2':
                conserved = {owner+'_p2', owner+'_p4'}
        if abs(math.fsum(deltas[a] for a in conserved)) > 32*math.ulp(scale):
            raise ValueError('Realized green direction changes the fixed green budget')
    delta_global = _joint_number(parsed[1][0] - parsed[0][0], 'Delta J_Omega')
    delta_local = _joint_number(parsed[1][1][owner] - parsed[0][1][owner], 'Delta C_i')
    external = _joint_number(delta_global - delta_local, 'Delta external cost')
    secant = _joint_number(external / step, 'external directional secant')
    return {'owner': owner, 'delta_global_veh_h': delta_global, 'delta_local_veh_h': delta_local,
            'external_delta_veh_h': external, 'directional_secant': secant,
            'parameter_unit': unit, 'secant_unit': 'veh*h' if unit == '1' else 'veh*h/(' + unit + ')',
            'coordinate': copy.deepcopy(coordinate), 'realized_deltas': deltas,
            'context': copy.deepcopy(base['context']),
            'base_response_token': base['response_token'], 'probe_response_token': probe['response_token'],
            'all_owner_costs_checked': len(owners), 'directional_only': True,
            'all_owner_model_values_checked': len(owners),
            'model_owner_values': {'base': copy.deepcopy(base['model_owner_values']),
                                   'probe': copy.deepcopy(probe['model_owner_values'])},
            'per_phase_gradient_constructed': False, 'gauge_selected': False,
            'price_or_dual_terms_subtracted': False, 'local_beta_term_subtracted': False,
            'feasibility_or_equilibrium_certified': False}


def fit_joint_price_field(follower, reference, secants_by_owner, *,
                          nuf_price_policy='independent',
                          directional_nuf_targets_veh_h=None,
                          nuf_equality_tolerance_veh_h=None,
                          final_meter_bounds_veh_h=None, fixed_meter_proofs=None,
                          fixed_move_box=None):
    """Fit raw external prices from matched realized edges at one fixed action.

    No model, optimization, holder mutation or legacy dispatch occurs here.
    Every owner needs full column rank in its configured active tangent space;
    missing directions raise instead of becoming zero prices. Urban prices use
    the explicit sum(active prices)=0 gauge, including headless active phases;
    configured dead phases are fixed at zero. Offset displacements use each
    owner's actual cycle. A free-zone VSL price is distributed equally over
    its expanded cells, preserving the dot product for zone-uniform controls.
    Fixed recovery cells have known zero prices, not estimated inactive prices.

    Default independent metering retains both independent price coordinates.
    Explicit fixed_direction_equality instead requires frozen FW_E/FW_W rate
    targets and an absolute budget tolerance [veh/h]. Base and probe sums must
    meet those targets; every edge must also preserve its directional rate sum
    within 32 ULP of its operands. Budget tolerance cannot turn a changing-sum
    edge into a tangent. Each two-meter pair keeps BOTH output addresses with
    p1+p2=0 gauge and the single fit column delta_m1-delta_m2. Its unobservable
    common price is a declared gauge, not an estimated zero. All remaining
    tangent coordinates still need full rank, including at all-open boundaries.

    Opt-in bounded_direction_equality additionally requires each final meter
    bound as {'lower': 0, 'upper': configured ramp_capacity_veh_h}. Narrower
    caller bounds/trust regions cannot manufacture a fixed coordinate. Only
    an EXACT singleton of this continuous box intersected with m1+m2=B can
    remove the meter fit column; supplied binary64 values are compared using
    exact rational arithmetic, not budget tolerance. Both prices then remain
    present as zero REPRESENTATIVES, not identified gradients: every feasible
    meter displacement is zero, so any finite meter prices give the same
    reference-relative cost. Reference and all probes must match those fixed
    rates exactly. A movable box intersection retains the existing tangent
    and rank requirement. Quantization can narrow that set but never supplies
    a singleton proof here. The caller binds cfg/bounds to the frozen actual
    realization context; this helper does not itself run the physical writer.

    Least squares minimizes unweighted squared external COST residuals on the
    supplied edges (not residuals of nominal directional derivatives). Columns
    are scaled by their Euclidean norms before the NumPy default-rcond rank
    test, so measurement units do not alone set identifiability. Nonlinear
    secant residuals are returned; even a full-rank exact fit is not a gradient,
    feasibility or equilibrium certificate. This helper neither divides by nor
    changes existing channel weights. Caller applies returned holder_values at
    this fixed reference/context, with scalar-green and cross channels excluded.
    Caller still binds the matched results to actual shared responses and the
    canonical complete owner/command catalog.
    """
    import copy
    import json
    import numpy as np

    signals, _, _, _ = _joint_catalog(follower)
    net = follower.cfg.network
    freeway = tuple(net.freeway_links)
    owners = signals + freeway
    phases = ('p1', 'p2', 'p3', 'p4')
    if nuf_price_policy not in ('independent', 'fixed_direction_equality', 'bounded_direction_equality'):
        raise ValueError('Explicit supported NUF price-coordinate policy required')
    bounded_equality = nuf_price_policy == 'bounded_direction_equality'
    meter_equality = nuf_price_policy != 'independent'
    physical_meters = bool(getattr(net, 'physical_ramp_branches', None))
    if physical_meters and meter_equality:
        raise ValueError('Predicted merge equality is not a service-rate price tangent')
    independently_fixed = {}
    if fixed_meter_proofs is not None:
        if meter_equality or fixed_move_box is None:
            raise ValueError('Physical fixed-coordinate proofs require independent policy and actual move box')
        from evaluation.controllers.joint_owner_neighbors import validate_fixed_meter_coordinate_proofs
        independently_fixed = validate_fixed_meter_coordinate_proofs(follower.cfg, reference,
            fixed_meter_proofs, move_box=fixed_move_box)
    if bounded_equality:
        from fractions import Fraction
        if (not isinstance(final_meter_bounds_veh_h, dict)
                or set(final_meter_bounds_veh_h) != set(net.ramps)
                or set(net.ramp_capacity_veh_h) != set(net.ramps)):
            raise ValueError('Bounded equality requires exact complete configured final meter bounds')
        final_bounds = {}
        for ramp, bounds in final_meter_bounds_veh_h.items():
            if not isinstance(bounds, dict) or set(bounds) != {'lower', 'upper'}:
                raise ValueError('Each final meter requires explicit lower and upper bounds')
            lower = _joint_number(bounds['lower'], ramp+' lower', nonnegative=True)
            upper = _joint_number(bounds['upper'], ramp+' upper', nonnegative=True)
            cap = _joint_number(net.ramp_capacity_veh_h[ramp], ramp+' configured cap', nonnegative=True)
            if lower != 0. or cap == 0. or upper != cap:
                raise ValueError('Final meter bounds must exactly equal [0, configured ramp capacity]')
            final_bounds[ramp] = {'lower': lower, 'upper': upper}
    elif final_meter_bounds_veh_h is not None:
        raise ValueError('Final meter bounds require the explicit bounded equality price policy')
    if meter_equality:
        if (not isinstance(directional_nuf_targets_veh_h, dict)
                or set(directional_nuf_targets_veh_h) != {'FW_E', 'FW_W'}):
            raise ValueError('Equality prices require both frozen directional NUF targets')
        equality_targets = {s: _joint_number(v, s+' NUF target', nonnegative=True)
                            for s, v in directional_nuf_targets_veh_h.items()}
        equality_tol = _joint_number(nuf_equality_tolerance_veh_h, 'NUF equality tolerance', nonnegative=True)
    elif directional_nuf_targets_veh_h is not None or nuf_equality_tolerance_veh_h is not None:
        raise ValueError('Directional equality arguments require the explicit equality price policy')
    if (len(signals) != 17 or set(freeway) != {'FW_E', 'FW_W'} or len(freeway) != 2
            or not isinstance(secants_by_owner, dict) or set(secants_by_owner) != set(owners)):
        raise ValueError('Price field requires exact 17 urban plus two FW edge catalogs')
    if (set(follower._phase_movements) != set(signals) or any(
            set(follower._phase_movements[s]) != set(phases) for s in signals)
            or set(follower._local_freeway_models) != set(freeway)):
        raise ValueError('Incomplete configured local owner/phase catalogs')
    reference_levers = {k: copy.deepcopy(getattr(reference, k)) for k in
                        ('green_times', 'offsets', 'vsl', 'ramp_metering')}
    if any(not isinstance(v, dict) for v in reference_levers.values()):
        raise ValueError('Explicit complete realized reference lever maps required')
    model_ref, domains, meter_owner = {}, {}, {}
    for s in signals:
        live = tuple(net.signal_live_phases(s))
        if not live or len(set(live)) != len(live) or not set(live) <= set(phases):
            raise ValueError(s + ': invalid explicit active phases')
        live = tuple(p for p in phases if p in live)
        cycle = _joint_number(net.signal_cycle_length(s), s + ' cycle', nonnegative=True)
        if cycle == 0:
            raise ValueError('Positive actual owner cycle required')
        model_ref[s] = {s+'_'+p: _joint_number(reference.green_times[s+'_'+p], s+'_'+p,
                                               nonnegative=True) for p in phases}
        model_ref[s][s] = _joint_number(reference.offsets[s], s + ' offset')
        if any(model_ref[s][s+'_'+p] != 0. for p in phases if p not in live):
            raise ValueError(s + ': configured dead-phase reference must be zero')
        native_basis = (getattr(net, 'signal_actuation_contract', {}) or {}).get('nodes', {}).get(s, {}).get('native_clock_basis')
        concurrent = isinstance(native_basis, dict) and native_basis.get('kind') == 'concurrent_p1_p2'
        if concurrent and live != ('p1', 'p2', 'p4'):
            raise ValueError(s + ': unsupported concurrent price phase catalog')
        domains[s] = {'live': live, 'cycle': cycle,
                      'columns': [s+'_'+p+' minus '+s+'_'+live[-1] for p in live[:-1]] + [s+' offset']}
        if native_basis is not None:
            from evaluation.controllers import signal_group_plan as plans
            node = plans.node_plan_from_json(net.signal_actuation_contract['nodes'][s])
            if node.node_id not in (s, s.removeprefix('SC')) or native_basis['cycle_sec'] != cycle:
                raise ValueError(s + ': native source node/cycle differs from the price owner')
            plans.native_phase_windows(node, {p: model_ref[s][s+'_'+p] for p in phases},
                native_basis['amber_sec'], native_basis['all_red_sec'])
            domains[s]['native_node'] = node
        if concurrent:
            domains[s]['concurrent_p1_p2'] = True
            domains[s]['columns'] = [s+'_p1', s+'_p2 minus '+s+'_p4', s+' offset']
    for link in freeway:
        model = follower._local_freeway_models[link]
        ramps = tuple(model.owned_ramps)
        heads = tuple(net.freeway_vsl_zone_heads[link])
        head_of = tuple(net.freeway_vsl_zone_head_of_cell[link])
        free = tuple(net.freeway_vsl_zone_free)
        meter_count = 4 if physical_meters else 2
        if (model.link != link or len(ramps) != meter_count or len(set(ramps)) != meter_count
                or type(model.n_seg) is not int or model.n_seg < 1
                or len(head_of) != model.n_seg or not heads or len(set(heads)) != len(heads)
                or any(type(h) is not int or not 0 <= h < model.n_seg for h in heads)
                or not free or len(set(free)) != len(free)
                or any(type(z) is not int or not 0 <= z < len(heads) for z in free)
                or set(head_of) != set(heads)):
            raise ValueError(link + ': invalid explicit free-zone/owned-meter inventory')
        cells = {h: tuple(i for i, value in enumerate(head_of) if value == h) for h in heads}
        if any(h not in cells[h] for h in heads):
            raise ValueError(link + ': zone head must belong to its own cell group')
        values = {f'{link}__seg{i}': _joint_number(reference.vsl[f'{link}__seg{i}'],
                   link + ' cell VSL', nonnegative=True) for i in range(model.n_seg)}
        values[link] = _joint_number(reference.vsl[link], link + ' alias', nonnegative=True)
        if (values[link] != min(values[f'{link}__seg{i}'] for i in range(model.n_seg))
                or any(len({values[f'{link}__seg{i}'] for i in group}) != 1 for group in cells.values())):
            raise ValueError(link + ': reference must have exact zone-uniform VSL and minimum alias')
        for ramp in ramps:
            if ramp in meter_owner or net.ramp_to_freeway[ramp] != link:
                raise ValueError('Duplicate or unknown meter owner')
            meter_owner[ramp] = link
            values[ramp] = _joint_number(reference.ramp_metering[ramp], ramp, nonnegative=True)
        model_ref[link] = values
        meter_columns = [ramps[0]+' minus '+ramps[1]] if meter_equality else [r for r in ramps if r not in independently_fixed]
        fixed_values, bounds_proof = None, None
        if bounded_equality:
            r1, r2 = ramps
            target = Fraction(equality_targets[link])
            lo = max(Fraction(final_bounds[r1]['lower']), target-Fraction(final_bounds[r2]['upper']))
            hi = min(Fraction(final_bounds[r1]['upper']), target-Fraction(final_bounds[r2]['lower']))
            if lo > hi:
                raise ValueError(link + ': exact frozen equality and final meter bounds have empty intersection')
            singleton = lo == hi
            bounds_proof = {'bounds_veh_h': {r: dict(final_bounds[r]) for r in ramps},
                'first_meter': r1, 'first_meter_feasible_interval_exact':
                    [[lo.numerator, lo.denominator], [hi.numerator, hi.denominator]],
                'singleton_proven': singleton,
                'arithmetic': 'exact rational values of supplied binary64 operands; no tolerance collapse',
                'meter_tangent_fitted': not singleton, 'meter_gradient_certified': False,
                'price_convention': 'zero representatives on fixed coordinates, not gradients' if singleton
                                    else 'sum of movable directional meter prices=0 gauge'}
            if singleton:
                exact_fixed = {r1: lo, r2: target-lo}
                fixed_values = {r: float(v) for r, v in exact_fixed.items()}
                if any(Fraction(fixed_values[r]) != v for r, v in exact_fixed.items()):
                    raise ValueError(link + ': exact singleton rates are not representable as final binary64 rates')
                meter_columns = []
                bounds_proof['fixed_rates_veh_h'] = dict(fixed_values)
                bounds_proof['meter_cost_invariant'] = 'all feasible meter displacements from reference are exactly zero'
            if (any(not final_bounds[r]['lower'] <= values[r] <= final_bounds[r]['upper'] for r in ramps)
                    or (fixed_values is not None and any(values[r] != fixed_values[r] for r in ramps))):
                raise ValueError(link + ': reference violates final meter bounds or exact singleton rates')
        domains[link] = {'cells': cells, 'free_heads': tuple(heads[z] for z in free), 'ramps': ramps,
                        'columns': [link+' zone '+str(heads[z]) for z in free] + meter_columns,
                        'fixed_meter_values': fixed_values}
        if meter_equality:
            actual = _joint_number(math.fsum(values[r] for r in ramps), link+' reference NUF')
            residual = _joint_number(actual-equality_targets[link], link+' reference NUF residual')
            if abs(residual) > equality_tol:
                raise ValueError(link + ': reference violates the frozen directional NUF equality')
            domains[link]['equality'] = {'target_veh_h': equality_targets[link],
                'reference_rate_veh_h': actual, 'reference_residual_veh_h': residual,
                'budget_tolerance_veh_h': equality_tol, 'probe_residuals_veh_h': [],
                'normal_displacements_veh_h': [], 'tangent_tolerances_veh_h': []}
            if bounds_proof is not None:
                domains[link]['equality']['final_bounds_proof'] = bounds_proof
    if (set(reference.green_times) != {s+'_'+p for s in signals for p in phases}
            or set(reference.offsets) != set(signals) or set(reference.ramp_metering) != set(meter_owner)
            or set(meter_owner) != set(net.ramps) or set(net.ramp_to_freeway) != set(meter_owner)
            or set(reference.vsl) != {a for link in freeway for a in model_ref[link] if a not in meter_owner}):
        raise ValueError('Reference contains unknown or missing realized lever addresses')
    holders = {k: {} for k in ('signal_phase_price', 'signal_phase_price_ref',
        'offset_marginal_price', 'offset_marginal_price_ref', 'vsl_marginal_price',
        'vsl_marginal_price_ref', 'metering_marginal_price', 'metering_marginal_price_ref')}
    fits, context_text, context_value, base_token = {}, None, None, None
    for owner in owners:
        edges, domain = secants_by_owner[owner], domains[owner]
        if not isinstance(edges, (tuple, list)) or not edges:
            raise ValueError(owner + ': active prices are unknown without matched edges')
        rows, costs = [], []
        for edge in edges:
            if (edge['owner'] != owner or edge['directional_only'] is not True
                    or edge['all_owner_costs_checked'] != 19 or edge['all_owner_model_values_checked'] != 19
                    or any(edge[k] is not False for k in ('per_phase_gradient_constructed', 'gauge_selected',
                        'price_or_dual_terms_subtracted', 'local_beta_term_subtracted',
                        'feasibility_or_equilibrium_certified'))):
                raise ValueError('Explicit unweighted matched directional edges required')
            context = edge['context']
            if (not isinstance(context, dict) or not {'beta_seconds', 'frozen_digest', 'local_cost_definition'} <= set(context)
                    or any(not isinstance(context[k], str) or not context[k] for k in ('frozen_digest', 'local_cost_definition'))):
                raise ValueError('Complete matched frozen context required')
            _joint_number(context['beta_seconds'], 'matched beta', nonnegative=True)
            if (type(edge['base_response_token']) not in (str, bytes) or not edge['base_response_token']
                    or type(edge['probe_response_token']) not in (str, bytes) or not edge['probe_response_token']
                    or edge['base_response_token'] == edge['probe_response_token']):
                raise ValueError('Explicit distinct matched response identities required')
            current_context = json.dumps(edge['context'], sort_keys=True, separators=(',', ':'), allow_nan=False)
            if context_text is None:
                _joint_native_price_nodes(net, context)
                context_text, context_value, base_token = current_context, copy.deepcopy(edge['context']), edge['base_response_token']
            if current_context != context_text or edge['base_response_token'] != base_token:
                raise ValueError('Edges have different frozen context or reference response')
            models = edge['model_owner_values']
            if models['base'] != model_ref or set(models['probe']) != set(owners):
                raise ValueError('Every edge must start at the complete fixed realized reference')
            for other in owners:
                values = models['probe'][other]
                if set(values) != set(model_ref[other]) or (other != owner and values != model_ref[other]):
                    raise ValueError('Foreign model change or incomplete probe model catalog')
                for value in values.values():
                    _joint_number(value, 'probe model value')
            before, after = model_ref[owner], models['probe'][owner]
            coordinate = edge['coordinate']
            included = set(before) if owner in signals else set(before)-{owner}
            if (coordinate['owner'] != owner or coordinate['base_values'] != {a: before[a] for a in included}
                    or coordinate['probe_values'] != {a: after[a] for a in included}):
                raise ValueError('Matched coordinate does not bind the full realized edge')
            kinds = {a: ('offset' if a == owner else 'green') if owner in signals else
                         ('meter' if a in domain['ramps'] else 'vsl') for a in included}
            units = {'phase_exchange': 's', 'offset': 's', 'vsl': 'km/h', 'meter': 'veh/h', 'joint_direction': '1'}
            if (coordinate['address_kinds'] != kinds or coordinate['address_owners'] != dict.fromkeys(included, owner)
                    or coordinate['kind'] not in units or coordinate['parameter_unit'] != units[coordinate['kind']]
                    or set(coordinate['direction']) != included):
                raise ValueError('Matched direction has unknown owner, address kind or unit')
            step = _joint_number(coordinate['displacement'], 'matched displacement')
            if step == 0.:
                raise ValueError('Matched direction has zero displacement')
            deltas = {a: after[a]-before[a] for a in included}
            if owner in signals:
                if coordinate['offset_cycles'] != {owner: domain['cycle']}:
                    raise ValueError('Matched offset uses a different owner cycle')
                if 'native_node' in domain:
                    node = domain['native_node']; basis = node.native_clock_basis
                    plans.native_phase_windows(node, {p: after[owner+'_'+p] for p in phases},
                        basis['amber_sec'], basis['all_red_sec'])
                deltas[owner] = ((deltas[owner]+domain['cycle']/2.) % domain['cycle'])-domain['cycle']/2.
                live = domain['live']
                conserved = ('p2', 'p4') if domain.get('concurrent_p1_p2') else live
                if (any(deltas[owner+'_'+p] != 0. for p in phases if p not in live)
                        or abs(math.fsum(deltas[owner+'_'+p] for p in conserved)) >
                           32*math.ulp(max(1., *(abs(v) for v in before.values()), *(abs(v) for v in after.values())))):
                    raise ValueError('Edge leaves the configured fixed-sum active green tangent')
                row = ([deltas[owner+'_p1'], deltas[owner+'_p2']-deltas[owner+'_p4'], deltas[owner]]
                       if domain.get('concurrent_p1_p2') else
                       [deltas[owner+'_'+p]-deltas[owner+'_'+live[-1]] for p in live[:-1]] + [deltas[owner]])
            else:
                if coordinate['offset_cycles'] != {}:
                    raise ValueError('FW direction must not invent an offset cycle')
                if after[owner] != min(after[f'{owner}__seg{i}'] for group in domain['cells'].values() for i in group):
                    raise ValueError('Probe derived FW alias differs from its expanded cells')
                zone_delta = {}
                for head, group in domain['cells'].items():
                    ds = {deltas[f'{owner}__seg{i}'] for i in group}
                    if len(ds) != 1 or (head not in domain['free_heads'] and ds != {0.}):
                        raise ValueError('Edge changes fixed recovery or violates a VSL zone equality')
                    zone_delta[head] = next(iter(ds))
                meter_deltas = [deltas[r] for r in domain['ramps']]
                if not meter_equality:
                    if any(after[r] != independently_fixed[r] for r in domain['ramps'] if r in independently_fixed):
                        raise ValueError(owner + ': edge leaves a proved fixed physical meter coordinate')
                    meter_deltas = [deltas[r] for r in domain['ramps'] if r not in independently_fixed]
                if meter_equality:
                    equality = domain['equality']
                    if bounded_equality:
                        fixed = domain['fixed_meter_values']
                        if (any(not final_bounds[r]['lower'] <= after[r] <= final_bounds[r]['upper']
                                for r in domain['ramps'])
                                or (fixed is not None and any(after[r] != fixed[r] for r in domain['ramps']))):
                            raise ValueError(owner + ': probe violates final meter bounds or exact singleton rates')
                    actual = _joint_number(math.fsum(after[r] for r in domain['ramps']), owner+' probe NUF')
                    residual = _joint_number(actual-equality['target_veh_h'], owner+' probe NUF residual')
                    normal = _joint_number(math.fsum(meter_deltas), owner+' NUF normal displacement')
                    tangent_tol = 32*math.ulp(max(1., *(abs(before[r]) for r in domain['ramps']),
                                                   *(abs(after[r]) for r in domain['ramps'])))
                    if abs(residual) > equality_tol or abs(normal) > tangent_tol:
                        raise ValueError(owner + ': edge leaves the fixed directional NUF equality tangent')
                    equality['probe_residuals_veh_h'].append(residual)
                    equality['normal_displacements_veh_h'].append(normal)
                    equality['tangent_tolerances_veh_h'].append(tangent_tol)
                    meter_deltas = [] if domain['fixed_meter_values'] is not None else [meter_deltas[0]-meter_deltas[1]]
                row = [zone_delta[h] for h in domain['free_heads']] + meter_deltas
            if deltas != edge['realized_deltas']:
                raise ValueError('Reported realized displacement differs from model edge')
            if not any(deltas.values()) or any(not math.isclose(delta, step*_joint_number(
                    coordinate['direction'][a], 'matched direction'), rel_tol=1e-12, abs_tol=0.)
                    for a, delta in deltas.items()):
                raise ValueError('Matched nominal direction differs from its realized displacement')
            external = _joint_number(edge['external_delta_veh_h'], 'external edge cost')
            if (external != _joint_number(edge['delta_global_veh_h'], 'global edge cost') -
                    _joint_number(edge['delta_local_veh_h'], 'local edge cost')
                    or _joint_number(edge['directional_secant'], 'matched secant') != external/step):
                raise ValueError('External edge cost does not match global-minus-local cost')
            rows.append(row); costs.append(external)
        matrix, values = np.asarray(rows, dtype=float), np.asarray(costs, dtype=float)
        if not np.isfinite(matrix).all() or not np.isfinite(values).all():
            raise ValueError('Nonfinite price-fit operands')
        scale = np.linalg.norm(matrix, axis=0)
        if not np.isfinite(scale).all() or np.any(scale == 0):
            missing = [name for name, size in zip(domain['columns'], scale) if not math.isfinite(size) or size == 0]
            raise ValueError(owner + ': unidentified active price coordinates: ' + repr(missing))
        solution, _, rank, singular = np.linalg.lstsq(matrix/scale, values, rcond=None)
        if rank != len(domain['columns']):
            raise ValueError(f'{owner}: active price field rank {rank}/{len(domain["columns"])} is insufficient')
        solution = solution/scale
        residual = matrix @ solution - values
        if not np.isfinite(solution).all() or not np.isfinite(residual).all():
            raise ValueError('Nonfinite fitted prices or residuals')
        prices = [float(v) for v in solution]
        if owner in signals:
            live = domain['live']
            phase_prices = dict.fromkeys(phases, 0.)
            if domain.get('concurrent_p1_p2'):
                phase_prices.update(p1=prices[0], p2=prices[1], p4=-prices[1])
            else:
                phase_prices.update(dict(zip(live[:-1], prices[:-1])))
                phase_prices[live[-1]] = -math.fsum(prices[:-1])
            holders['signal_phase_price'][owner] = phase_prices
            holders['signal_phase_price_ref'][owner] = {p: before[owner+'_'+p] for p in phases}
            holders['offset_marginal_price'][owner] = prices[-1]
            holders['offset_marginal_price_ref'][owner] = before[owner]
        else:
            zone_prices = dict(zip(domain['free_heads'], prices))
            for head, group in domain['cells'].items():
                for i in group:
                    key = f'{owner}__seg{i}'
                    holders['vsl_marginal_price'][key] = zone_prices.get(head, 0.)/len(group)
                    holders['vsl_marginal_price_ref'][key] = before[key]
            meter_prices = prices[len(domain['free_heads']):]
            if meter_equality:
                meter_prices = [0., 0.] if domain['fixed_meter_values'] is not None else [meter_prices[0], -meter_prices[0]]
            elif independently_fixed:
                active_prices = iter(meter_prices)
                meter_prices = [0. if r in independently_fixed else next(active_prices) for r in domain['ramps']]
            for ramp, price in zip(domain['ramps'], meter_prices):
                holders['metering_marginal_price'][ramp] = price
                holders['metering_marginal_price_ref'][ramp] = before[ramp]
        max_residual = float(np.max(np.abs(residual)))
        rms_residual = max_residual * math.sqrt(math.fsum((float(v)/max_residual)**2 for v in residual)/len(residual)) if max_residual else 0.
        fits[owner] = {'edge_count': len(edges), 'rank': int(rank), 'dimension': len(domain['columns']),
            'columns': domain['columns'], 'column_scales': scale.tolist(),
            'scaled_singular_values': singular.tolist(), 'scaled_condition_number': float(singular[0]/singular[-1]),
            'external_delta_veh_h': costs, 'fitted_external_delta_veh_h': (matrix @ solution).tolist(),
            'residual_veh_h': residual.tolist(), 'max_abs_residual_veh_h': max_residual,
            'rms_residual_veh_h': rms_residual}
        if owner in freeway and meter_equality:
            fits[owner]['nuf_equality'] = domain['equality']
        if owner in freeway and any(r in independently_fixed for r in domain['ramps']):
            fits[owner]['fixed_meter_coordinates'] = {r: independently_fixed[r] for r in domain['ramps'] if r in independently_fixed}
            fits[owner]['fixed_meter_price_convention'] = 'zero representatives, not identified derivatives'
        if owner in signals and domain.get('concurrent_p1_p2'):
            fits[owner]['phase_gauge'] = 'p1 independent; p2+p4 prices sum to zero; p3 fixed zero'
    result = {'holder_values': holders, 'owner_fits': fits, 'reference_levers': reference_levers,
            'context': context_value, 'base_response_token': base_token,
            'phase_gauge': 'sum(active phase prices)=0; configured dead phase prices=0',
            'nuf_price_policy': nuf_price_policy,
            'meter_gauge': ('proven fixed coordinates: zero representatives, not gradients; movable directional pairs: price sum=0'
                            if bounded_equality else 'each fixed directional two-meter price sum=0' if meter_equality else None),
            'units': {'phase': 'veh*h/s', 'offset': 'veh*h/s', 'vsl': 'veh*h/(km/h)', 'meter': 'h^2'},
            'finite_secant_fit': True, 'raw_external_prices_before_channel_weights': True,
            'legacy_dispatch_changed': False, 'feasibility_or_equilibrium_certified': False}
    if independently_fixed:
        result['fixed_meter_proofs'] = copy.deepcopy(fixed_meter_proofs)
        result['meter_gauge'] = 'Proved fixed physical coordinates use zero representatives; remaining independent coordinates are fitted'
    if any(domains[s].get('concurrent_p1_p2') for s in signals):
        result['phase_gauge'] = 'Serial: active phase price sum=0; concurrent_p1_p2: p1 independent and p2+p4 price sum=0; dead phases=0'
    return result


def install_joint_price_field(follower, reference, field, *, expected_owners, expected_context, nuf_mode):
    """Install a complete matched field at its exact frozen reference/context.

    This is an explicit installation boundary, not a price refresh or solver
    hook. The caller supplies evaluate_joint_prices(...)["field"], the same
    realized reference and its expected frozen context. All eight maps are
    validated and copied before one plain-instance-dictionary update; failure
    before that update leaves every follower attribute/alias unchanged.

    Existing Link/WuFaithful local and shared-price consumers read self.* for
    these holders. The nested _wu supplies coupling/omega/model bookkeeping and
    has no consumer of these eight price maps, so it is deliberately untouched.
    Weights, duals, scalar-green/cross channels, flags and physical strategy
    domains are not rewritten. Non-split equality metering remains unsupported
    even when every fitted meter price is a fixed-coordinate zero representative.
    Recreate context, neighbor callbacks and binding fingerprints AFTER success:
    an active holder can change the existing priced candidate/trust branches.
    Installation certifies neither the measured response nor a game equilibrium.
    """
    import copy
    import inspect
    import json

    names = ('signal_phase_price', 'signal_phase_price_ref', 'offset_marginal_price',
             'offset_marginal_price_ref', 'vsl_marginal_price', 'vsl_marginal_price_ref',
             'metering_marginal_price', 'metering_marginal_price_ref')
    signals, _, _, _ = _joint_catalog(follower)
    net = follower.cfg.network
    freeway = tuple(net.freeway_links); owners = signals + freeway
    expected = tuple(expected_owners)
    if (len(signals) != 17 or len(freeway) != 2 or set(freeway) != {'FW_E', 'FW_W'}
            or len(set(owners)) != 19 or len(expected) != 19 or set(expected) != set(owners)
            or set(follower._local_freeway_models) != set(freeway)):
        raise ValueError('Price installation requires the exact expected 19-owner catalog')
    if (not isinstance(field, dict) or field.get('finite_secant_fit') is not True
            or field.get('raw_external_prices_before_channel_weights') is not True
            or field.get('feasibility_or_equilibrium_certified') is not False
            or not isinstance(field.get('owner_fits'), dict) or set(field['owner_fits']) != set(owners)):
        raise ValueError('A complete finite matched-price field is required')
    for owner, fit in field['owner_fits'].items():
        if (type(fit.get('dimension')) is not int or fit['dimension'] < 1
                or type(fit.get('rank')) is not int or fit['rank'] != fit['dimension']):
            raise ValueError(owner + ': incomplete active price rank')
    if (not isinstance(expected_context, dict) or not isinstance(field.get('context'), dict)
            or not {'beta_seconds', 'frozen_digest', 'local_cost_definition'} <= set(expected_context)
            or any(not isinstance(expected_context[k], str) or not expected_context[k]
                   for k in ('frozen_digest', 'local_cost_definition'))):
        raise ValueError('Explicit expected frozen measurement context required')
    _joint_number(expected_context['beta_seconds'], 'context beta', nonnegative=True)
    if json.dumps(field['context'], sort_keys=True, allow_nan=False) != json.dumps(expected_context, sort_keys=True, allow_nan=False):
        raise ValueError('Measured price context differs from the expected frozen context')
    _joint_native_price_nodes(net, field['context'])
    policy = field.get('nuf_price_policy')
    if (nuf_mode not in ('dual', 'equality') or policy not in
            ('independent', 'fixed_direction_equality', 'bounded_direction_equality')
            or (policy != 'independent' and nuf_mode != 'equality')):
        raise ValueError('Measured meter tangent requires its explicit supported NUF policy')
    if nuf_mode == 'equality' and follower.metering_price_split is not True:
        raise ValueError('Equality with non-split priced metering implies an unsupported soft anchor, including fixed zero representatives')
    if follower.green_offset_cross_price is not None or follower.vsl_meter_cross_price is not None:
        raise ValueError('Active cross-price policy is not part of the additive full-vector contract')
    phases = ('p1', 'p2', 'p3', 'p4')
    if (set(follower._phase_movements) != set(signals) or any(
            set(follower._phase_movements[s]) != set(phases) for s in signals)):
        raise ValueError('All four phase addresses, including dark phases, are required')
    reference_levers = {name: copy.deepcopy(getattr(reference, name))
                        for name in ('green_times', 'offsets', 'vsl', 'ramp_metering')}
    if any(not isinstance(values, dict) for values in reference_levers.values()):
        raise ValueError('Complete realized reference maps required')
    for name, values in reference_levers.items():
        for key, value in values.items(): _joint_number(value, name+':'+key, nonnegative=name != 'offsets')
    measured_reference = field.get('reference_levers')
    if not isinstance(measured_reference, dict) or measured_reference != reference_levers:
        raise ValueError('Measured price reference differs from the supplied realized reference')
    for name, values in measured_reference.items():
        for key, value in values.items(): _joint_number(value, 'measured reference '+name+':'+key)
    phase_keys = {s+'_'+p for s in signals for p in phases}; vsl_keys = set(); ramps = set()
    for link in freeway:
        model = follower._local_freeway_models[link]
        meter_count = 4 if getattr(net, 'physical_ramp_branches', None) else 2
        if model.link != link or type(model.n_seg) is not int or model.n_seg < 1 or len(model.owned_ramps) != meter_count:
            raise ValueError('Invalid configured freeway owner shape')
        cells = {f'{link}__seg{i}' for i in range(model.n_seg)}; vsl_keys.update(cells)
        for ramp in model.owned_ramps:
            if ramp in ramps or net.ramp_to_freeway.get(ramp) != link:
                raise ValueError('Unknown or duplicate configured meter ownership')
            ramps.add(ramp)
        if not cells <= set(reference.vsl) or reference.vsl.get(link) != min(reference.vsl[k] for k in cells):
            raise ValueError('Expanded VSL reference/minimum alias mismatch')
    if (set(reference.green_times) != phase_keys or set(reference.offsets) != set(signals)
            or set(reference.vsl) != vsl_keys | set(freeway) or set(reference.ramp_metering) != ramps
            or set(net.ramps) != ramps or set(net.ramp_to_freeway) != ramps):
        raise ValueError('Unknown or missing realized reference address')
    staged = copy.deepcopy(field.get('holder_values'))
    if not isinstance(staged, dict) or set(staged) != set(names) or any(not isinstance(v, dict) for v in staged.values()):
        raise ValueError('Exactly eight complete price/reference holders required')
    for name in ('signal_phase_price', 'signal_phase_price_ref'):
        if set(staged[name]) != set(signals) or any(not isinstance(v, dict) or set(v) != set(phases) for v in staged[name].values()):
            raise ValueError('Full urban price/reference phase shape required')
    flat_prices = {s+'_'+p: staged['signal_phase_price'][s][p] for s in signals for p in phases}
    flat_refs = {s+'_'+p: staged['signal_phase_price_ref'][s][p] for s in signals for p in phases}
    channels = ((reference.green_times, flat_refs, flat_prices, 'signal_phase_price_weight', 'phase'),
        (reference.offsets, staged['offset_marginal_price_ref'], staged['offset_marginal_price'], 'offset_marginal_price_weight', 'offset'),
        ({k:reference.vsl[k] for k in vsl_keys}, staged['vsl_marginal_price_ref'], staged['vsl_marginal_price'], 'vsl_marginal_price_weight', 'vsl'),
        (reference.ramp_metering, staged['metering_marginal_price_ref'], staged['metering_marginal_price'], 'metering_marginal_price_weight', 'meter'))
    for values, refs, prices, weight, label in channels:
        _joint_channel(values, refs, prices, (), getattr(follower, weight), label)
        if refs != values: raise ValueError(label + ': holder references differ from the exact realized reference')
    for signal in signals:
        live = tuple(net.signal_live_phases(signal)); price = staged['signal_phase_price'][signal]
        if not live or len(set(live)) != len(live) or not set(live) <= set(phases):
            raise ValueError('Invalid live-phase gauge catalog')
        if any(price[p] != 0. or reference.green_times[signal+'_'+p] != 0. for p in phases if p not in live):
            raise ValueError('Dead-phase price/reference must remain zero')
        native_basis = (getattr(net, 'signal_actuation_contract', {}) or {}).get('nodes', {}).get(signal, {}).get('native_clock_basis')
        concurrent = isinstance(native_basis, dict) and native_basis.get('kind') == 'concurrent_p1_p2'
        if concurrent and set(live) != {'p1', 'p2', 'p4'}:
            raise ValueError('Unsupported concurrent price gauge catalog')
        gauge = ('p2', 'p4') if concurrent else live
        if abs(math.fsum(price[p] for p in gauge)) > 32*math.ulp(max(1., *(abs(price[p]) for p in live))):
            raise ValueError('Active phase prices do not use the measured zero-sum gauge')
    fixed_proof = copy.deepcopy(field.get('fixed_meter_proofs'))
    if fixed_proof is not None:
        if policy != 'independent':
            raise ValueError('Physical fixed-meter proof is only supported for independent coordinates')
        from evaluation.controllers.joint_owner_neighbors import validate_fixed_meter_coordinate_proofs
        fixed_rates = validate_fixed_meter_coordinate_proofs(follower.cfg, reference, fixed_proof)
        if any(staged['metering_marginal_price'][r] != 0. for r in fixed_rates):
            raise ValueError('Proved fixed meter coordinates require the declared zero representative')
    target = vars(follower)
    if type(target) is not dict or any(hasattr(inspect.getattr_static(type(follower), name, None), '__set__') for name in names):
        raise ValueError('Installation requires ordinary instance price attributes, not setters')
    report = {'installed': True, 'holder_names': names, 'owners': owners,
            'context': copy.deepcopy(expected_context), 'nuf_mode': nuf_mode,
            'nested_wu_synchronized': False, 'weights_flags_duals_changed': False,
            'caller_must_rebuild_context_and_callbacks': True,
            'scalar_green_channel_included': False, 'feasibility_or_equilibrium_certified': False}
    if fixed_proof is not None:
        report['fixed_meter_proofs'] = copy.deepcopy(fixed_proof)
    # No fallible validation/deep copy or user setter remains after this point.
    target.update(staged)
    if fixed_proof is not None:
        target['_joint_fixed_meter_proofs'] = fixed_proof
    else:
        target.pop('_joint_fixed_meter_proofs', None)
    return report
