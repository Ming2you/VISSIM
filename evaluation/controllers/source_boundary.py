"""Mainline origin boundary A1 of the v2 lane plant (plan C6, NEW-13).

The calibration fed each freeway source with the admitted-interface recursion
of boundary_factory.build_window(history_forecast), BF:136-138:

    rate    = min(recent, max(0, demand + backlog*3600/step))
    backlog = max(0, backlog + (demand - rate)*step/3600)

with recent = the admitted rate of the last 150 s and backlog = integral of
the desired schedule minus the admitted count (BF:55-62, 102-105). The SDMPC
receives exogenous demand as one DemandStep per control interval, so the same
10 s recursion is averaged over each 150 s block. The block SUM equals the
calibration recursion exactly; only the placement inside a block is uniform,
the same resolution as every other exogenous input (urban gates, ramps).

Everything here is a pure function of observed data and the declared native
timetable. The forecast enters the workers as DemandStep data, so no
instrumented model code changes.
"""
from __future__ import annotations

import math

from evaluation.controllers.obs150_contract import (
    ROADS, SOURCE_BOUNDARY_BLOCK, ScheduleRow, schedule_integral_veh, schedule_rate_at, validate_schedule)

MODE = SOURCE_BOUNDARY_BLOCK['mode']
STEPS = (1, 5, 10)


def _finite_nonneg(value, what):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(what + ' must be finite and non-negative')
    return float(value)


def forecast(recent_vph, backlog_veh, schedule, start_s, block_s, n_blocks, step_s=10):
    """Block-mean admitted source rate [veh/h] for n_blocks blocks of block_s from start_s."""
    recent = _finite_nonneg(recent_vph, 'recent_vph')
    backlog = _finite_nonneg(backlog_veh, 'backlog_veh')
    _finite_nonneg(start_s, 'start_s')
    if type(step_s) is not int or step_s not in STEPS:
        raise ValueError('step_s must be 1, 5 or 10 s')
    if type(block_s) is not int or block_s <= 0 or block_s % step_s:
        raise ValueError('block_s must be a positive multiple of step_s')
    if type(n_blocks) is not int or n_blocks <= 0:
        raise ValueError('n_blocks must be a positive integer')
    schedule = validate_schedule(schedule)
    out = []
    for b in range(n_blocks):
        rates = []
        for i in range(block_s // step_s):
            t = start_s + b * block_s + i * step_s
            demand = schedule_rate_at(schedule, t)
            rate = min(recent, max(0., demand + backlog * 3600 / step_s))
            backlog = max(0., backlog + (demand - rate) * step_s / 3600)
            rates.append(rate)
        out.append(math.fsum(rates) / len(rates))
    return out


def schedule_rows(native_rows):
    """native_input_schedule rows [{'start_sec','rate_veh_h'}] -> ScheduleRow tuple.

    Each native rate holds until the next row's start; the last row is open,
    the same piecewise-constant meaning as shared_approach.demand_amount.
    """
    rows = []
    for index, row in enumerate(native_rows):
        end = native_rows[index + 1]['start_sec'] if index + 1 < len(native_rows) else None
        rows.append(ScheduleRow(float(row['start_sec']), None if end is None else float(end),
                                float(row['rate_veh_h'])))
    return validate_schedule(rows)


def road_schedules(native_input_schedule):
    """{road: ScheduleRow tuple} for the two declared mainline inputs (LPR:371-381)."""
    directed = native_input_schedule.get('freeway_link_by_input')
    if not directed or sorted(directed.values()) != sorted(ROADS):
        raise ValueError('Source boundary needs exactly one declared native input per freeway')
    return {road: schedule_rows(native_input_schedule['inputs'][no]['schedule']) for no, road in directed.items()}


def geometry_schedules(geometry):
    """{road: ScheduleRow tuple} of the calibration's desired_source_demand (BF:49-61)."""
    out = {}
    for road in ROADS:
        rows = sorted((r for r in geometry['desired_source_demand'] if r['road'] == road),
                      key=lambda r: float(r['start_sec']))
        out[road] = validate_schedule(tuple(ScheduleRow(float(r['start_sec']),
            None if r['end_sec'] is None else float(r['end_sec']), float(r['desired_volume_vph'])) for r in rows))
    return out


def same_schedule(a, b, *, tol=1e-9):
    """Piecewise-constant equality: same change points and rates."""
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if (abs(x.start_sec - y.start_sec) > tol or (x.end_sec is None) != (y.end_sec is None)
                or (x.end_sec is not None and abs(x.end_sec - y.end_sec) > tol) or abs(x.vph - y.vph) > tol):
            return False
    return True


def observed_block(observation, schedules):
    """The C4(i) record stored on cfg.network: observed boundary at the cutoff.

    It re-checks the observer's schedule integral against the timetable the
    forecast will use, so admitted/backlog and A1 cannot use two schedules.
    """
    cutoff = int(observation['information_cutoff_s'])
    rows = observation['source_boundary']
    if set(rows) != set(ROADS) or set(schedules) != set(ROADS):
        raise ValueError('Source boundary needs both freeway roads')
    for road in ROADS:
        integral = schedule_integral_veh(schedules[road], 0.0, float(cutoff))
        if abs(integral - rows[road]['schedule_integral_veh']) > 1e-9 * max(1.0, integral):
            raise ValueError('Observed source schedule integral differs from the native timetable: ' + road)
    return {'mode': MODE, 'information_cutoff_s': cutoff,
            'by_road': {road: {k: rows[road][k] for k in ('admitted_window', 'admitted_cum', 'interval_s',
                                                          'recent_vph', 'schedule_integral_veh', 'backlog_veh')}
                        for road in ROADS}}


def demand_blocks(cfg, start_s, n_blocks):
    """A1 block means {road: [vph...]} for demand_from_state, or None when A1 is off.

    None (the declared native timetable is kept) when the lane plant is absent,
    is v1, or the cutoff lies before the first complete 150 s history: BF
    defines the recursion only for cutoff >= history_sec (BF:91). That covers
    the t=1 no-control decision only; from t=150 on A1 is mandatory.

    Known, pre-existing order: the warm start (AD:9791
    warm_start_release_buffers, inside traffic_state_from_vissim at RS:199)
    runs before the lane plant initializes (RS:232), so lane_plant_enabled is
    still unset there and its demand_from_state keeps the native timetable.
    Only the decision forecast after initialize uses A1.
    """
    net = cfg.network
    sources = getattr(net, 'lane_plant_sources', None)
    block = (sources or {}).get('source_boundary') if getattr(net, 'lane_plant_enabled', False) else None
    if block is None:
        return None
    if block != SOURCE_BOUNDARY_BLOCK:
        raise ValueError('Unsupported source boundary declaration')
    observed = getattr(net, 'freeway_source_boundary_observed', None)
    if not isinstance(observed, dict) or observed.get('mode') != MODE:
        raise ValueError('A1 source boundary lacks its observed cutoff record')
    if float(observed['information_cutoff_s']) != float(start_s):
        raise ValueError('A1 source boundary observation is not at the forecast start')
    if observed['information_cutoff_s'] < block['history_sec']:
        return None
    interval = cfg.simulation.control_interval
    if not float(interval).is_integer():
        raise ValueError('A1 blocks need an integer-second control interval')
    schedules = road_schedules(net.native_input_schedule)
    return {road: forecast(row['recent_vph'], row['backlog_veh'], schedules[road], float(start_s),
                           int(interval), max(1, int(n_blocks)), step_s=block['model_step_sec'])
            for road, row in observed['by_road'].items()}
