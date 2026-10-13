"""Regional quantity contracts; absent resources carry no physical claim."""
import copy
import math

MODES = ('freeway_only', 'urban_only')
KINDS = dict(boundary_in=1., off_ramp=1., boundary_out=-1., on_ramp=-1., internal=0.)


def checked_number(value, label, *, nonnegative=False):
    if type(value) not in (int, float) or not math.isfinite(value) or (nonnegative and value < 0):
        raise ValueError('Invalid regional ' + label)
    return float(value)


def mode_for(cfg):
    mode = cfg.network.sdmpc_options.get('regional_prediction_prototype')
    if mode not in MODES:
        raise ValueError('Explicit regional prediction mode required')
    return mode



def active_resources(mode):
    if mode not in MODES:
        raise ValueError('Explicit regional resource mode required')
    return [mode == 'urban_only', mode == 'freeway_only']


def project_forecast(forecast, mode):
    active_resources(mode)
    result = copy.deepcopy(forecast)
    for demand in result:
        demand.ramp_arrival = dict.fromkeys(demand.ramp_arrival, 0.)
        if mode == 'freeway_only':
            demand.urban_boundary = dict.fromkeys(demand.urban_boundary, 0.)
        else:
            demand.freeway_mainline = dict.fromkeys(demand.freeway_mainline, 0.)
            demand.freeway_lane_loss = {}
            demand.incident_capacity_factor = 1.
    return result


def active_owners(cfg):
    mode = mode_for(cfg)
    return tuple(cfg.network.freeway_links if mode == 'freeway_only' else cfg.network.signals)


def quantity_constraints(follower, action, quantities, *, start_sec, horizon_steps,
                         np_mode, target_np_veh, np_tolerance_veh,
                         nuf_mode, target_nuf_veh_h, nuf_tolerance_veh_h):
    """Validate own accepted quantities, preserving the shared cap semantics."""
    cfg = follower.cfg
    mode = mode_for(cfg)
    q = quantities
    end = start_sec + horizon_steps * cfg.simulation.T_c_sec
    if (type(horizon_steps) is not int or horizon_steps < 1 or end <= start_sec
            or q.get('schema') != 'regional-accepted-quantities/v1'
            or q.get('region') != mode or q.get('start_sec') != start_sec or q.get('end_sec') != end
            or q.get('active_resource') != ('NUF' if mode == 'freeway_only' else 'NP')):
        raise ValueError('Regional quantity context mismatch')
    coverage = q.get('coverage', {})
    dt = 5. if mode == 'freeway_only' else 10.
    if (coverage.get('region') != mode or coverage.get('complete') is not True
            or coverage.get('sample_sec') != dt
            or type(coverage.get('samples')) is not int or coverage['samples'] != (end-start_sec)/dt
            or coverage.get('configured_movement_count') !=
                (len(cfg.network.urban_movements) if mode == 'urban_only' else 0)):
        raise ValueError('Incomplete regional quantity clock/catalog')
    expected_owners = set(cfg.network.signals) if mode == 'urban_only' else set()
    if set(q['owners']) != expected_owners:
        raise ValueError('Regional quantity owner catalog differs')
    owner_np = {}
    for owner, row in q['owners'].items():
        if (set(row['by_kind_veh']) != set(KINDS)
                or type(row['accepted_event_count']) is not int or row['accepted_event_count'] < 0):
            raise ValueError('Incomplete regional accepted owner service')
        total = math.fsum(KINDS[k] * checked_number(v, 'accepted service', nonnegative=True)
                          for k, v in row['by_kind_veh'].items())
        actual = checked_number(row['net_inflow_veh'], 'owner net inflow')
        if not math.isclose(total, actual, rel_tol=1e-12, abs_tol=1e-8):
            raise ValueError('Regional signed owner service differs')
        owner_np[owner] = actual
    merge = q['predicted_ramp_merge']
    expected_ramps = set(cfg.network.ramps) if mode == 'freeway_only' else set()
    if (merge.get('active') is not (mode == 'freeway_only')
            or merge.get('remote_prediction') is not False or merge.get('boundary') != 'ramp_to_mainline'
            or set(merge['rate_veh_h_by_ramp']) != expected_ramps
            or set(merge['accepted_vehicles_by_ramp']) != expected_ramps):
        raise ValueError('Regional accepted merge scope differs')
    rates = {}
    for ramp in sorted(expected_ramps):
        rates[ramp] = checked_number(merge['rate_veh_h_by_ramp'][ramp], 'merge rate', nonnegative=True)
        vehicles = checked_number(merge['accepted_vehicles_by_ramp'][ramp], 'merge count', nonnegative=True)
        if not math.isclose(vehicles*3600/(end-start_sec), rates[ramp], rel_tol=1e-12, abs_tol=1e-8):
            raise ValueError('Regional merge count/rate differs')
    actuals = math.fsum(owner_np.values()), math.fsum(rates.values())
    for key, actual in zip(('np_actual', 'nuf_actual'), actuals):
        if not math.isclose(checked_number(q[key], key), actual, rel_tol=1e-12, abs_tol=1e-8):
            raise ValueError('Regional aggregate differs from accepted service')
    rows = {}
    for name, actual, target, tolerance, requested_mode, active, unit in (
        ('np', actuals[0], target_np_veh, np_tolerance_veh, np_mode, mode == 'urban_only', 'veh'),
        ('nuf', actuals[1], target_nuf_veh_h, nuf_tolerance_veh_h, nuf_mode, mode == 'freeway_only', 'veh/h')):
        if requested_mode not in ('cap', 'dual', 'inactive', 'equality') or (name == 'np' and requested_mode == 'equality'):
            raise ValueError('Unsupported regional resource policy')
        target = checked_number(target, name + ' target', nonnegative=name == 'nuf')
        tolerance = checked_number(tolerance, name + ' tolerance', nonnegative=True)
        if not active and target != 0:
            raise ValueError('Absent regional resource must have a zero target')
        residual = actual-target
        violation = abs(residual) if requested_mode == 'equality' else max(0., residual)
        checked = active and requested_mode in ('cap', 'equality')
        rows[name] = dict(mode=requested_mode if active else 'inactive', active=active, unit=unit,
            actual=actual, target=target, residual=residual, violation=violation,
            tolerance=tolerance, constraint_checked=checked, satisfied=violation <= tolerance if checked else None)
    return dict(schema='regional-quantity-constraints/v1', region=mode, **rows,
        feasible=all(row['satisfied'] is not False for row in rows.values()),
        net_inflow_veh_by_owner=owner_np,
        meter_rate_veh_h_by_owner={owner:math.fsum(v for ramp,v in rates.items()
            if cfg.network.ramp_to_freeway[ramp] == owner) for owner in cfg.network.freeway_links}
            if mode == 'freeway_only' else {},
        nuf_definition='predicted_accepted_mainline_merge' if mode == 'freeway_only' else 'inactive_absent_resource',
        physical_ramp_merge=copy.deepcopy(merge),
        window=dict(start_sec=start_sec, end_sec=end, horizon_steps=horizon_steps),
        nonowner_service_included_in_np=False, individual_np_quotas_created=False,
        directional_nuf_constraints_checked=False, quantity_constraints_only=True,
        physical_feasibility_certified=False, leader_target_changed=False)
