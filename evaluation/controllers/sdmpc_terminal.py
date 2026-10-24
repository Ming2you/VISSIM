"""Opt-in x(T)' P x(T), Scheu & Marquardt (2011), Eq. (12).

Traffic specialization: x contains disjoint Omega vehicle inventories, with
each physical ramp separate from its freeway. P is an explicitly supplied
nonnegative diagonal in h/veh. This is a terminal approximation, not measured
TTT, an action bonus, or a Lyapunov/stability certificate. No default P is
invented, no outside cohort is penalized, and no extra traffic rollout is run.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math

PASSIVE = 'PASSIVE_OMEGA'
SCHEMA = 'omega-quadratic-terminal/v1'


def group_owners(cfg):
    net = cfg.network
    return {**{key: key for key in (*net.signals, *net.freeway_links, PASSIVE)},
            **{'ramp:'+key: net.ramp_to_freeway[key] for key in net.ramps}}


def group_for_stock(stock, cfg):
    if stock.startswith('ramp:'):
        if stock.split(':', 1)[1] not in cfg.network.ramps:
            raise ValueError('Terminal cost encountered unknown ramp: '+stock)
        return stock
    return cfg.network.sdmpc_cost_ownership.get(stock, PASSIVE)


def configure(tuning, cfg):
    spec = tuning.get('adapter', {}).get('sdmpc_terminal_cost')
    if spec is None:
        if hasattr(cfg.network, 'sdmpc_terminal_cost'):
            del cfg.network.sdmpc_terminal_cost
        return
    if (not isinstance(spec, dict) or set(spec) != {'schema', 'p_diag_h_per_veh', 'design'}
            or spec['schema'] != SCHEMA or not isinstance(spec['design'], str)
            or not spec['design'].strip()):
        raise ValueError('Explicit terminal schema, P diagonal and design required')
    coefficients = spec['p_diag_h_per_veh']
    if not isinstance(coefficients, dict) or set(coefficients) != set(group_owners(cfg)):
        raise ValueError('Terminal P must cover all urban/freeway/passive/ramp groups')
    for key, value in coefficients.items():
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError('Terminal P must be finite positive semidefinite: '+key)
    if not any(coefficients.values()):
        raise ValueError('Terminal P cannot be identically zero; omit the option to disable')
    if not cfg.network.control_area_enabled or cfg.network.control_area_beta_seconds != 0:
        raise ValueError('Quadratic terminal currently requires Omega TTT without exit reward')
    cfg.network.sdmpc_terminal_cost = copy.deepcopy(spec)


def specification_token(spec):
    return hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def evaluate(stocks, cfg):
    spec = getattr(cfg.network, 'sdmpc_terminal_cost', None)
    if spec is None:
        return None
    owners = group_owners(cfg)
    values = {key: [] for key in owners}
    for stock, cohorts in stocks.items():
        n = cohorts['inside']
        if not math.isfinite(n) or n < 0:
            raise ValueError('Invalid terminal Omega inventory: '+stock)
        values[group_for_stock(stock, cfg)].append(n)
    counts = {key: math.fsum(rows) for key, rows in values.items()}
    costs = {key: spec['p_diag_h_per_veh'][key]*n*n for key, n in counts.items()}
    if any(not math.isfinite(value) for value in costs.values()):
        raise ValueError('Nonfinite terminal cost')
    by_owner = {owner: math.fsum(costs[g] for g in owners if owners[g] == owner)
                for owner in (*cfg.network.signals, *cfg.network.freeway_links, PASSIVE)}
    return dict(schema=SCHEMA, specification_sha256=specification_token(spec),
        inventory_veh=counts, cost_by_group_veh_h=costs, cost_by_owner_veh_h=by_owner,
        total_veh_h=math.fsum(costs.values()), inside_veh=math.fsum(counts.values()),
        outside_included=False, stability_certificate=False)


def apply(point, closing, cfg):
    receipt = evaluate(closing.stocks, cfg)
    if receipt is None:
        return
    point.far = receipt['total_veh_h']
    point.objective += point.far
    point.control_area.update(terminal_cost=receipt,
        additional_cost_veh_h=point.far, selection_score_veh_h=point.objective,
        far_disabled=False, legacy_far_disabled=True)


def validate_score(area, objective, cfg):
    """The writer boundary accepts only the explicitly configured terminal term."""
    if cfg is not None and getattr(cfg.network,'sdmpc_distance_reward',None) is not None:
        from evaluation.controllers.omega_distance import validate_reward_score
        validate_reward_score(area,objective,cfg)
        return
    if 'distance_reward' in area:
        raise ValueError('Unconfigured distance reward receipt')
    spec = getattr(cfg.network, 'sdmpc_terminal_cost', None) if cfg is not None else None
    receipt = area.get('terminal_cost')
    near, additional = area['near_score_veh_h'], area['additional_cost_veh_h']
    if spec is None:
        if receipt is not None or additional != 0. or near != objective:
            raise ValueError('Unexpected cost outside the configured Omega objective')
        return
    if (not isinstance(receipt, dict) or receipt.get('schema') != SCHEMA
            or receipt.get('specification_sha256') != specification_token(spec)
            or receipt.get('outside_included') is not False
            or receipt.get('stability_certificate') is not False):
        raise ValueError('Missing or mismatched terminal cost receipt')
    counts = receipt['inventory_veh']
    owners = group_owners(cfg)
    if set(counts) != set(owners) or any(not math.isfinite(n) or n < 0 for n in counts.values()):
        raise ValueError('Invalid terminal inventory receipt')
    costs = {key: spec['p_diag_h_per_veh'][key]*n*n for key, n in counts.items()}
    by_owner = {owner: math.fsum(costs[g] for g in owners if owners[g] == owner)
                for owner in (*cfg.network.signals, *cfg.network.freeway_links, PASSIVE)}
    total = math.fsum(costs.values())
    if (receipt['cost_by_group_veh_h'] != costs or receipt['cost_by_owner_veh_h'] != by_owner
            or receipt['total_veh_h'] != total or receipt['inside_veh'] != math.fsum(counts.values())
            or additional != total or near+total != objective
            or area.get('selection_score_veh_h') != objective):
        raise ValueError('Terminal cost decomposition or selection score mismatch')
