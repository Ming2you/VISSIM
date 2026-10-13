"""8c01693 multiplier recovery adapted to NP cap and actual-merge NUF band."""
import time
import numpy as np
from scipy.optimize import nnls


def resource_mask(active_resources=None):
    if active_resources is None:
        return np.ones(2, dtype=bool)
    mask = np.asarray(active_resources)
    if mask.shape != (2,) or mask.dtype != np.dtype(bool) or not mask.any():
        raise ValueError('Explicit nonempty two-resource boolean mask required')
    return mask


def initialize_duals(prices, *, caps=False, active_resources=None):
    mask = resource_mask(active_resources)
    p = np.asarray(prices, dtype=float).copy()
    p[~mask] = 0.
    if caps:
        return np.maximum(0., p)
    return np.array([max(0., p[0]), max(0., p[1]), max(0., -p[1])])


def signed_prices(dual):
    if len(dual) == 2:
        return np.asarray(dual, dtype=float).copy()
    return np.array([dual[0], dual[1]-dual[2]])


def budget_rows(residual, tolerance, *, caps=False):
    r, eps = np.asarray(residual), np.asarray(tolerance)
    if caps:
        return r-eps
    return np.array([r[0]-eps[0], r[1]-eps[1], -r[1]-eps[1]])


def update_duals(dual, raw_residual, tolerance, step, *, caps=False, active_resources=None):
    mask = resource_mask(active_resources)
    result = np.maximum(0., np.asarray(dual) + step*budget_rows(raw_residual, tolerance, caps=caps))
    result[~(mask if caps else np.array([mask[0], mask[1], mask[1]]))] = 0.
    return result


def qp_bounds(residual, tolerance, *, caps=False, active_resources=None):
    c, eps = np.asarray(residual), np.asarray(tolerance)
    mask = resource_mask(active_resources)
    lower, upper = np.array([-np.inf, -np.inf if caps else -eps[1]-c[1]]), eps-c
    lower[~mask], upper[~mask] = -np.inf, np.inf
    return lower, upper


def recover(reference, selected, final_quantities, target, scale, tolerance, coord, options, feasible, *, caps=False, active_resources=None):
    """Final actual constraints, reused coefficients; no traffic prediction."""
    started = time.perf_counter()
    z0, G, A, physical, final_physical = reference
    names = ['budget/NP/upper', 'budget/NUF/upper']
    h = list(budget_rows((np.asarray(final_quantities)-target)/scale, tolerance/scale, caps=caps))
    rows = [A[0], A[1]]
    if not caps:
        names.append('budget/NUF/lower'); rows.append(-A[1])
    mask = resource_mask(active_resources)
    keep = mask if caps else np.array([mask[0], mask[1], mask[1]])
    names, h, rows = ([v for v, yes in zip(values, keep) if yes] for values in (names, h, rows))
    budget_indices = {name: i for i, name in enumerate(names)}
    n = len(selected)
    eye = np.eye(n)
    for j in range(n):
        names.extend([f'control/{j}/lower', f'control/{j}/upper'])
        h.extend([coord.lower[j]-selected[j], selected[j]-coord.upper[j]])
        rows.extend([-eye[j], eye[j]])
    # Includes actual phase budgets and inter-block move constraints; no proximal term.
    for j, (row, lo, hi) in enumerate(zip(coord.G, coord.glo, coord.ghi)):
        if np.isfinite(lo):
            names.append(f'control/linear/{j}/lower'); h.append(lo-row@selected); rows.append(-row)
        if np.isfinite(hi):
            names.append(f'control/linear/{j}/upper'); h.append(row@selected-hi); rows.append(row)
    if physical['names'] != final_physical['names']:
        raise ValueError('Final physical registry differs from the reused linearization')
    names.extend(physical['names']); h.extend(final_physical['values']); rows.extend(physical['jacobian'])
    C, h, g = np.asarray(rows), np.asarray(h), np.asarray(G).sum(axis=0)
    if C.shape != (len(h), n) or not np.isfinite(C).all() or not np.isfinite(h).all():
        raise ValueError('Incomplete central constraint system')
    active = np.flatnonzero(abs(h) <= options['active_tolerance'])
    norms = np.linalg.norm(C[active], axis=1)
    nz = active[norms > options['zero_jacobian_tolerance']]
    groups = {}
    for i in nz:
        norm = np.linalg.norm(C[i])
        key = tuple(np.round(C[i]/norm, options['duplicate_decimals']))
        groups.setdefault(key, []).append((int(i), norm))
    representatives = [members[0] for members in groups.values()]
    matrix = np.column_stack([C[i]/norm for i,norm in representatives]) if representatives else np.zeros((n,0))
    multipliers = np.zeros(len(h))
    error = None
    try:
        fitted = nnls(matrix, -g)[0] if matrix.shape[1] else np.zeros(0)
        for value, members in zip(fitted, groups.values()):
            # Equal normalized contribution preserves every duplicate's provenance.
            for i, norm in members:
                multipliers[i] = value/(len(members)*norm)
        fit = True
    except (RuntimeError, ValueError) as exc:
        fit, error = False, repr(exc)
    residual = g+C.T@multipliers
    def budget_multiplier(name):
        return multipliers[budget_indices[name]] if name in budget_indices else 0.
    gradient = np.array([-budget_multiplier('budget/NP/upper')/scale[0],
        (-budget_multiplier('budget/NUF/upper')+budget_multiplier('budget/NUF/lower'))/scale[1]])
    stationarity = float(np.max(abs(residual), initial=0.))
    complementarity = float(np.max(abs(h*multipliers), initial=0.))
    usable = bool(feasible and fit and np.isfinite(gradient).all())
    return dict(schema='sdmpc-central-multiplier/v1', gradient_estimate=gradient.tolist(),
        **(dict(active_resources=mask.tolist()) if active_resources is not None else {}),
        accepted_for_leader_direction=usable, fit_success=fit, error=error,
        leader_signal_kind='approximate_central_multiplier', optimality_certified=False,
        stationarity_inf=stationarity, complementarity=complementarity,
        stationarity_pass=stationarity <= options['stationarity_tolerance'],
        complementarity_pass=complementarity <= options['stationarity_tolerance'],
        first_order_diagnostics_pass=False,
        derivative_certified=False, reference_point=np.asarray(z0).tolist(), selected_point=selected.tolist(),
        reference_distance_inf=float(np.max(abs(selected-z0))),
        reference_matches_selected=bool(np.array_equal(z0, selected)),
        final_values_from='selected continuous-model rollout; not native or exact-actuator validation',
        constraints=len(h), physical_constraints=len(physical['names']), active_constraints=len(active),
        active_zero_jacobians=len(active)-len(nz), duplicate_groups=sum(len(v)>1 for v in groups.values()),
        active_rows=[dict(index=int(i), name=names[i], value=float(h[i]), multiplier=float(multipliers[i])) for i in active],
        max_actual_violation=float(np.max(h,initial=0.)),
        physical_registry_scope=physical['scope'], additional_traffic_rollouts=0,
        additional_optimization_iterations=0, seconds=time.perf_counter()-started)


def next_budget(center, recovery, attempted, limits, options, *, active_resources=None):
    mask = resource_mask(active_resources)
    gradient = recovery.get('gradient_estimate') if recovery.get('accepted_for_leader_direction') else None
    direction = np.where(abs(np.asarray(gradient))>options['active_tolerance'],-np.sign(gradient),0.) if gradient is not None else np.zeros(2)
    radius = np.array([options['np_step_veh'], options['nuf_step_veh_h']])
    directions = ([direction, -direction] if np.any(direction) else [])
    directions += [np.array([0.,-1.]), np.array([0.,1.]), np.array([-1.,0.]), np.array([1.,0.])]
    for d in directions:
        if not np.any(d*mask):
            continue
        trial = np.clip(np.asarray(center)+radius*d*mask, limits[0], limits[1])
        trial[~mask] = np.asarray(center)[~mask]
        if not any(np.array_equal(trial, old) for old in attempted):
            # Hand back plain floats. The consumer stores these on the action as
            # N_P_star / N_UF_star, and area_leader_objective._joint_number rejects on
            # `type(value) not in (int, float)`, so a numpy scalar fails there with the
            # misleading message "N_P target must be a finite number" even though the
            # value is finite. This is why the multi-budget search never ran past the
            # first proposal.
            return tuple(float(v) for v in trial)
    return None
