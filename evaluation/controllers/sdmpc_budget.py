"""Initialize upper budgets from a control's measured prediction, never commands."""
import copy
import hashlib
import pickle


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
    seed = copy.deepcopy(control)
    seed.N_P_star, seed.N_UF_star = q['np']['actual'], q['nuf']['actual']
    return seed, dict(schema='decision-pfo-budget-initialization/v1',
        start_sec=q['window']['start_sec'], end_sec=q['window']['end_sec'],
        np_cap_veh=seed.N_P_star, nuf_cap_veh_h=seed.N_UF_star,
        accepted_rate_veh_h_by_ramp=q['physical_ramp_merge']['rate_veh_h_by_ramp'],
        reference_action_token=source_token, reference_response_token=item['response_token'],
        frozen_context_token=item['frozen_context_token'],
        budget_policy='upper_caps', source='current_interval_PFO_prediction',
        previous_budget_reused=False, physical_commands_unchanged=True,
        scope='Achieved quantities in the current prediction, not future VISSIM observations')


def search_limits(center, np_domain, nuf_capacity):
    """The achieved witness remains a legal center, even outside the old NP grid.

    This only bounds subsequent *budget proposals*. It never expands a trial's
    fixed cap to accommodate a violating action, or modifies actuator limits.
    """
    return ([min(min(np_domain), center[0]), 0.],
            [max(max(np_domain), center[0]), max(nuf_capacity, center[1])])
