"""Initialize upper budgets from a control's measured prediction, never commands."""
import copy
import hashlib
import math
import pickle

MARGIN_KEYS = ('np_cap_margin_veh', 'nuf_cap_margin_veh_h')
PFO_CAP_KEYS = ('max_iterations', 'nuf_tolerance_veh_h') + MARGIN_KEYS


def checked_margin(value, name):
    """Finite nonnegative float; int is widened so 50 and 50.0 hash alike."""
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('Finite nonnegative PFO cap margin required: '+name)
    return float(value)


def margins(policy):
    """No fallback: a policy without both margins cannot initialize caps."""
    options = policy['pfo_cap_options']
    return tuple(checked_margin(options[key], key) for key in MARGIN_KEYS)


def initialize(follower, state, control, item, options):
    from evaluation.controllers.area_leader_objective import shared_quantity_constraints
    source_token = hashlib.sha256(pickle.dumps(control, protocol=5)).hexdigest()
    if item.get('action_token') != source_token:
        raise ValueError('Warm-start budget needs the exact PFO action response')
    coverage = item.get('model_constraint_coverage', {})
    if (item.get('conditional_model_feasibility_witness') is not True
            or coverage.get('complete') is not True
            or coverage.get('conditional_model_feasibility_witness') is not True
            or item['resource_summary']['max_exceedance_veh'] > options['shared_tolerance']):
        raise ValueError('PFO prediction lacks a complete feasible physical witness')
    q = shared_quantity_constraints(follower, control, item['quantities'],
        start_sec=state.time_sec, horizon_steps=follower.cfg.mpc.horizon_steps,
        np_mode='dual', target_np_veh=0., np_tolerance_veh=0.,
        nuf_mode='dual', target_nuf_veh_h=0., nuf_tolerance_veh_h=0.)
    if q.get('nuf_definition') != 'predicted_accepted_mainline_merge':
        raise ValueError('PFO budget must use actual accepted mainline merge')
    np_margin, nuf_margin = margins(follower.cfg.network.sdmpc_options)
    achieved_np, achieved_nuf = q['np']['actual'], q['nuf']['actual']
    seed = copy.deepcopy(control)
    # x + 0.0 is bitwise x unless x is -0.0; both come from math.fsum, never -0.0.
    seed.N_P_star, seed.N_UF_star = achieved_np + np_margin, achieved_nuf + nuf_margin
    return seed, dict(schema='decision-pfo-budget-initialization/v2',
        start_sec=q['window']['start_sec'], end_sec=q['window']['end_sec'],
        np_cap_veh=seed.N_P_star, nuf_cap_veh_h=seed.N_UF_star,
        achieved_np_veh=achieved_np, achieved_nuf_veh_h=achieved_nuf,
        np_cap_margin_veh=np_margin, nuf_cap_margin_veh_h=nuf_margin,
        cap_rule='cap = PFO-achieved + configured nonnegative margin',
        accepted_rate_veh_h_by_ramp=q['physical_ramp_merge']['rate_veh_h_by_ramp'],
        reference_action_token=source_token, reference_response_token=item['response_token'],
        frozen_context_token=item['frozen_context_token'],
        budget_policy='upper_caps', source='current_interval_PFO_prediction',
        previous_budget_reused=False, physical_commands_unchanged=True,
        scope='PFO-achieved quantities in the current prediction plus the configured margin; not future VISSIM observations')


def search_limits(center, np_domain, nuf_capacity):
    """The initial cap (PFO-achieved + margin) remains a legal center, even outside the old NP grid.

    This only bounds subsequent *budget proposals*. It never expands a trial's
    fixed cap to accommodate a violating action, or modifies actuator limits.
    """
    return ([min(min(np_domain), center[0]), 0.],
            [max(max(np_domain), center[0]), max(nuf_capacity, center[1])])
