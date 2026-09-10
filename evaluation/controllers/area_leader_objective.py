"""Rank enabled Omega candidates by their canonical endpoint score alone.

Physical state equations and feasibility are untouched. Legacy cost components
remain inspectable as excluded diagnostics; config weights are never rewritten.
Supported selection consumers are the Wu full, Wu proxy and Wu PFO paths.
Base proxy/fallback scalars have no verified Omega provenance and fail closed.
"""
from __future__ import annotations
import functools
import math

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
