"""Current-plant, unpriced own-cost prox-linear PFO warm start.

This is the explicitly selected adaptation, not the legacy local METANET PFO.
All owners use one current prediction; owner i uses only dJ_i/du_i. There are
no externality/budget prices or NP/NUF constraints. Executable Jacobi profiles
are checked with the current plant; sum of owned costs is the line-search
merit (PASSIVE_OMEGA is excluded). No Nash convergence certificate is claimed.
"""
import time
import os
import numpy as np


def model_feasible(item, tolerance):
    coverage = item.get('model_constraint_coverage', {})
    return (item.get('conditional_model_feasibility_witness') is True
        and coverage.get('complete') is True
        and coverage.get('conditional_model_feasibility_witness') is True
        and item['resource_summary']['max_exceedance_veh'] <= tolerance)


def solve(reference, coord, policy, options, evaluate, derivative, quantities, check_budget, emit, screening_context=None):
    from evaluation.controllers.sdmpc import solve_qp, token, PASSIVE
    from evaluation.controllers.sdmpc_tangent import checked_matrices
    started = time.perf_counter()
    cap = policy['pfo_cap_options']['max_iterations']
    owners = (*coord.owners, PASSIVE)
    def costs(item):
        return np.array([item['sdmpc_omega_partition']['costs'][o] for o in owners])
    def merit(item):
        return float(costs(item)[:-1].sum())
    def qp(z, center, gradient, proximal, ix):
        G = coord.G[:, ix]; mask = np.any(G != 0, axis=1)
        return solve_qp(center, gradient, proximal, coord.lower[ix]-z[ix], coord.upper[ix]-z[ix],
            G[mask], (coord.glo-coord.G@z)[mask], (coord.ghi-coord.G@z)[mask], policy)
    emit('sdmpc_pfo_start', max_iterations=cap, budget_constraints=False, prices=False)
    action = reference.copy()
    item = evaluate([action], derivatives=True)[0]
    adaptive_selection = None
    threshold = os.environ.get('SDMPC_EXPERIMENTAL_ADAPTIVE_THRESHOLD', '').strip() or None
    pre_pfo = os.environ.get('SDMPC_PRE_PFO_LAGRANGIAN') == '1'
    if pre_pfo and (os.environ.get('SDMPC_POST_PFO_LAGRANGIAN') == '1' or
                    os.environ.get('SDMPC_EXPERIMENTAL_NO_PFO') == '1' or
                    os.environ.get('SDMPC_EXPERIMENTAL_LAGRANGIAN_SELECTION') != '1' or threshold is None):
        raise ValueError('Pre-PFO selection requires PFO, Lagrangian threshold and no post-PFO selection')
    if os.environ.get('SDMPC_POST_PFO_LAGRANGIAN') == '1':
        threshold = None  # Preserve the complete PFO; screen the resulting anchor later.
    if threshold is not None:
        from evaluation.controllers import adaptive_lever_selection
        query = getattr(derivative, '__self__', None)
        if query is None or not hasattr(query, 'activate_derivative_axes'):
            raise ValueError('Adaptive screening requires the surrogate query')
        initial_receipt = derivative(action)
        grad, resources, fallback = checked_matrices(initial_receipt,costs(item),quantities(action,item),coord.axes,
            policy['tangent_primal_abs_tolerance'],allow_surrogate=True)
        if fallback or initial_receipt.get('ad_axes') != list(range(len(coord.axes))):
            raise ValueError('Adaptive screening requires complete initial derivatives')
        if os.environ.get('SDMPC_EXPERIMENTAL_LAGRANGIAN_SELECTION')=='1':
            if (os.environ.get('SDMPC_EXPERIMENTAL_NO_PFO')!='1' and not pre_pfo) or screening_context is None:
                raise ValueError('Lagrangian screening requires the protected-seed cap experiment')
            ctx=screening_context(action,item)
            if not pre_pfo:
                raise ValueError('Finite-step VSL screening requires pre-PFO selection')
            from evaluation.controllers.vsl_finite_screen import score_adjacent
            def vsl_probe(prices, proximal, resource_scale):
                return score_adjacent(coord, action, item, evaluate, quantities,
                    lambda candidate: model_feasible(candidate, options['shared_tolerance']),
                    prices, proximal, resource_scale)
            ctx['vsl_probe']=vsl_probe
            adaptive_selection=adaptive_lever_selection.select_lagrangian(coord,action,grad,resources,float(threshold),**ctx)
            adaptive_selection['protected_reference_first_block'] = dict(
                green_times=dict(action.green_times), offsets=dict(action.offsets),
                ramp_metering=dict(action.ramp_metering), vsl=dict(action.vsl),
                diagnostics={k:v for k,v in action.diagnostics.items() if k.startswith('rw_meter_green_')})
            if pre_pfo: adaptive_selection['selection_stage']='before_pfo'
        else:
            adaptive_selection = adaptive_lever_selection.select(coord,action,grad,resources,float(threshold))
        query.activate_derivative_axes(adaptive_selection['active_axes'])
        emit('adaptive_levers_selected', selected=len(adaptive_selection['selected_groups']),
             fixed=len(adaptive_selection['fixed_groups']), active_axes=len(adaptive_selection['active_axes']),
             selection_seconds=adaptive_selection['selection_cost_sec'])
    initial = item
    best = (action,item) if model_feasible(item,options['shared_tolerance']) else None
    if os.environ.get('SDMPC_EXPERIMENTAL_NO_PFO') == '1':
        if best is None:
            raise ValueError('Protected seed lacks physical feasibility; no-PFO budget cannot initialize')
        metadata = dict(algorithm='protected-seed-no-pfo/experimental-v1',pfo_used=False,
            max_iterations=0,executed_iterations=0,accepted_iterations=0,converged=False,
            status='intentionally_skipped',local_rows=[],trial_rows=[],iterations=[],
            initial_omega_objective=item['objective_veh_h'],selected_omega_objective=item['objective_veh_h'],
            selected_owned_objective=merit(item),prices_used=False,budget_constraints_used=False,
            additional_native_runs=0,seconds=time.perf_counter()-started,
            sensitivity_policy='Initial full derivative computed; subsequent leader uses selected coordinates',
            line_search_merit='PFO omitted; protected seed and forecast initialize current budget')
        if adaptive_selection is not None:metadata['adaptive_selection']=adaptive_selection
        emit('sdmpc_pfo_skipped',seconds=metadata['seconds'],reason='explicit_no_pfo_experiment')
        return action,item,metadata,initial
    iterations, local_rows, trial_rows = [], [], []
    accepted = 0; status = 'iteration_limit'
    for iteration in range(cap):
        check_budget('sdmpc_pfo_iteration')
        z = coord.encode(action)
        receipt = derivative(action)
        G, _, fallback = checked_matrices(receipt,costs(item),quantities(action,item),coord.axes,
            policy['tangent_primal_abs_tolerance'],allow_surrogate=True)
        if fallback:
            raise ValueError('PFO requires complete direct own-cost sensitivities')
        iterations.append(dict(iteration=iteration,action_token=token(action)))
        proposal = np.zeros(len(z))
        for owner in coord.owners:
            ix = np.array([j for j,a in enumerate(coord.axes) if a['owner']==owner])
            own = G[owners.index(owner),ix]
            step, qr = qp(z,np.zeros(len(ix)),own,policy['proximal'],ix)
            local_rows.append(dict(iteration=iteration,owner=owner,own_gradient=own.tolist(),
                externality_gradient_used=False,prices_used=False,traffic_rollouts=0,**qr))
            if not qr['success']:
                if best is None:
                    raise ValueError('PFO own-cost QP failed and no verified warm start exists: '+str(qr))
                # Discard the entire incomplete Jacobi proposal.  Continue
                # from the best already evaluated and feasible PFO action.
                status = 'own_qp_failed_using_verified_warm_start'
                emit('sdmpc_pfo_qp_failed', iteration=iteration, owner=owner, receipt=qr,
                     using_verified_warm_start=True)
                break
            proposal[ix] = step
        if status == 'own_qp_failed_using_verified_warm_start':
            break
        step, qr = qp(z,proposal,np.zeros(len(z)),1.,np.arange(len(z)))
        if not qr['success']:
            raise ValueError('PFO actuator projection failed: '+str(qr))
        trials = []
        for k in range(policy['line_search_steps']):
            try: candidate = coord.decode(z+(.5**k)*step,action)
            except ValueError: continue
            if token(candidate) not in {token(a) for a in trials}:
                trials.append(candidate)
        if not trials:
            status = 'no_executable_step'; break
        # Score every trial; lazy mode differentiates accepted iterates only.
        values = evaluate(trials,derivatives=not policy.get('lazy_trial_derivatives'))
        winners = []
        for a,value in zip(trials,values):
            ok = model_feasible(value,options['shared_tolerance'])
            trial_rows.append(dict(iteration=iteration,feasible=ok,owned_cost=merit(value),
                omega_cost=value['objective_veh_h'],action_token=token(a)))
            if ok: winners.append((a,value))
        if not winners:
            status = 'no_feasible_nonlinear_step'; break
        chosen,value = min(winners,key=lambda av:merit(av[1]))
        if best is not None and merit(value) >= merit(best[1])-policy['objective_tolerance']:
            status = 'no_improving_step'; break
        action,item = chosen,value; best = (action,item); accepted += 1
        emit('sdmpc_pfo_step_accepted',iteration=iteration,owned_cost=merit(item),omega_cost=item['objective_veh_h'])
    if best is None:
        raise ValueError('PFO has no model-feasible executable warm start')
    if policy.get('lazy_trial_derivatives'):
        # Budget initialization uses the same AD primal as its warm binding.
        # Query checks the previous scalar response before publishing this AD.
        derivative(best[0])
        best = (best[0], evaluate([best[0]])[0])
    coord.validate(best[0])
    metadata = dict(algorithm='unpriced-own-proxlinear-pfo/v1',max_iterations=cap,
        executed_iterations=len(iterations),accepted_iterations=accepted,converged=False,status=status,
        local_rows=local_rows,trial_rows=trial_rows,iterations=iterations,
        initial_omega_objective=initial['objective_veh_h'],selected_omega_objective=best[1]['objective_veh_h'],
        selected_owned_objective=merit(best[1]),prices_used=False,budget_constraints_used=False,
        additional_native_runs=0,seconds=time.perf_counter()-started,
        sensitivity_policy='Updated at each accepted PFO iterate; final prediction/Jacobian reused by SDMPC',
        line_search_merit='sum of 19 owned costs; passive-area cost excluded')
    if adaptive_selection is not None:
        metadata['adaptive_selection'] = adaptive_selection
    emit('sdmpc_pfo_done',max_iterations=cap,executed_iterations=len(iterations),
        accepted_iterations=accepted,converged=False,seconds=metadata['seconds'])
    return (*best,metadata,initial)
