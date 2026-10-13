"""Current-plant, unpriced own-cost prox-linear PFO warm start.

This is the explicitly selected adaptation, not the legacy local METANET PFO.
All owners use one current prediction; owner i uses only dJ_i/du_i. There are
no externality/budget prices or NP/NUF constraints. Executable Jacobi profiles
are checked with the current plant; sum of owned costs is the line-search
merit (PASSIVE_OMEGA is excluded). No Nash convergence certificate is claimed.
"""
import time
import numpy as np


def model_feasible(item, tolerance):
    coverage = item.get('model_constraint_coverage', {})
    return (item.get('conditional_model_feasibility_witness') is True
        and coverage.get('complete') is True
        and coverage.get('conditional_model_feasibility_witness') is True
        and item['resource_summary']['max_exceedance_veh'] <= tolerance)


def solve(reference, coord, policy, options, evaluate, derivative, quantities, check_budget, emit):
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
    initial = item
    best = (action,item) if model_feasible(item,options['shared_tolerance']) else None
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
                raise ValueError('PFO own-cost QP failed: '+str(qr))
            proposal[ix] = step
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
        # Also retain the final PFO Jacobian for the first SDMPC iteration.
        values = evaluate(trials,derivatives=True)
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
    coord.validate(best[0])
    metadata = dict(algorithm='unpriced-own-proxlinear-pfo/v1',max_iterations=cap,
        executed_iterations=len(iterations),accepted_iterations=accepted,converged=False,status=status,
        local_rows=local_rows,trial_rows=trial_rows,iterations=iterations,
        initial_omega_objective=initial['objective_veh_h'],selected_omega_objective=best[1]['objective_veh_h'],
        selected_owned_objective=merit(best[1]),prices_used=False,budget_constraints_used=False,
        additional_native_runs=0,seconds=time.perf_counter()-started,
        sensitivity_policy='Updated at each accepted PFO iterate; final prediction/Jacobian reused by SDMPC',
        line_search_merit='sum of 19 owned costs; passive-area cost excluded')
    emit('sdmpc_pfo_done',max_iterations=cap,executed_iterations=len(iterations),
        accepted_iterations=accepted,converged=False,seconds=metadata['seconds'])
    return (*best,metadata,initial)
