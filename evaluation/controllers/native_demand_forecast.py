"""Use the declared input timetable for external demand, never future traffic.

Native internal/shared generation is advanced by its own conserved source
model. Here only mapped external gates and the reviewed symmetric freeway
inputs enter the existing demand-rate pipeline. Ramp observations persist.
"""
from __future__ import annotations

from copy import deepcopy
import math

from evaluation.controllers.shared_approach import demand_amount


def _rate(rows, start, end):
    return demand_amount(rows, start, end) * 3600.0 / (end - start)


def _totals(spec, start, end):
    gates, freeway, urban, internal, unmapped = {}, [], [], 0.0, 0.0
    for row in spec['inputs'].values():
        value = _rate(row['schedule'], start, end)
        if row['role'].startswith('freeway'):
            freeway.append(value)
        else:
            urban.append(value)
            if row['status'] == 'mapped':
                if not row['gate']:
                    raise ValueError('Mapped native input has no external gate')
                gates[row['gate']] = gates.get(row['gate'], 0.0) + value
            elif row['status'] == 'internal':
                internal += value
            else:
                unmapped += value
    if len(freeway) != 2 or not math.isclose(freeway[0], freeway[1], rel_tol=0, abs_tol=1e-6):
        raise ValueError('Native timetable requires the reviewed two symmetric freeway inputs')
    if not urban or not gates:
        raise ValueError('Native timetable lacks mapped urban inputs')
    return {'freeway_volume_vph': sum(freeway) / len(freeway),
            'urban_volume_vph': sum(urban) / len(urban),
            'urban_volume_vph_by_gate': gates,
            'urban_internal_volume_vph': internal,
            'urban_unmapped_volume_vph': unmapped}


def forecast_states(raw, cfg, horizon_steps):
    """Return private raw views whose external rates average each MPC interval."""
    spec = cfg.network.native_input_schedule
    if spec.get('schema') != 'native-input-schedule/v1':
        raise ValueError('Unsupported native demand timetable schema')
    if spec['run_id'] != raw.get('run_provenance', {}).get('run_id'):
        raise ValueError('Native timetable belongs to another observed run')
    if raw.get('demand', {}).get('demand_profile') != 'real_world_inpx_time_profile_scaled':
        raise ValueError('Native timetable needs the reviewed scaled input profile')
    start = float(raw['sim_sec'])
    interval = float(cfg.simulation.control_interval)
    if not math.isfinite(start) or start < 0 or not math.isfinite(interval) or interval <= 0:
        raise ValueError('Invalid native demand forecast time')
    for row in spec['inputs'].values():
        rows = row['schedule']
        if not rows or rows[0]['start_sec'] != 0:
            raise ValueError('Native timetable must start at zero')
        if any(not math.isfinite(float(r[k])) or float(r[k]) < 0
               for r in rows for k in ('start_sec', 'rate_veh_h')):
            raise ValueError('Native timetable requires finite nonnegative times and rates')
        if any(a['start_sec'] >= b['start_sec'] for a, b in zip(rows, rows[1:])):
            raise ValueError('Native timetable intervals must be strictly ordered')
    changes = sorted({r['start_sec'] for row in spec['inputs'].values() for r in row['schedule']})
    for index, time in enumerate(changes):
        end = changes[index + 1] if index + 1 < len(changes) else time + 1
        _totals(spec, time, min(time + 1, end))
    # Compare instantaneous configured demand with the runner's actual current
    # aggregate. Do not compare a straddling interval average to an instant.
    next_change = min((r['start_sec'] for row in spec['inputs'].values()
                       for r in row['schedule'] if r['start_sec'] > start), default=start + 1)
    current = _totals(spec, start, min(start + 1, next_change))
    for key, expected in current.items():
        observed = raw['demand'].get(key)
        if isinstance(expected, dict):
            if not isinstance(observed, dict) or set(observed) != set(expected):
                raise ValueError('Native timetable/current gate set differs')
            pairs = [(observed[k], value) for k, value in expected.items()]
        else:
            pairs = [(observed, expected)]
        if any(value is None or not math.isclose(float(value), target, rel_tol=0, abs_tol=1e-5)
               for value, target in pairs):
            raise ValueError('Native timetable/current observed demand differs: ' + key)
    output = []
    for index in range(max(1, int(horizon_steps))):
        # Only demand is copied. Observation objects are retained read-only by
        # profiled_demand_rates; no future vehicle/queue measurement is read.
        view = dict(raw)
        view['demand'] = deepcopy(raw['demand'])
        view['demand'].update(_totals(spec, start + index * interval, start + (index + 1) * interval))
        output.append(view)
    return output
