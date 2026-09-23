"""현재 Ω 예측기에 연결한 prox-linear S-DMPC. 기본 경로에는 영향이 없다.

Numerical-Sim b53ebd7의 공통 기준점 / own+externality / 고정 가격 /
resource projection / 원 모델 재검증 구조를 이식한다. 비선형-own NLP나
Nash 수렴을 주장하지 않는다. 실제 신호 clock과 이산 actuator를 보존한다.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import pickle
from contextlib import ExitStack
from pathlib import Path
from time import perf_counter

import numpy as np

SCHEMA = 'sdmpc-proxlinear/v1'
PASSIVE = 'PASSIVE_OMEGA'


def token(value):
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


class GradientCache:
    """NP is a constraint cap, not a physical input in this shared rollout.

    Reuse only the sensitivity matrix across NP caps, with identical physical
    actions and exact anchor costs/resources. Full scored response tokens and
    nonlinear feasibility checks remain cap-specific.
    """
    def __init__(self):
        self.entries = {}
        self.reuse = []

    def key(self, z, action, costs, resources):
        physical = copy.deepcopy(action)
        physical.N_P_star = 0.
        # Future rows carry a copy of the horizon-wide cap. actions() always
        # replaces it with the top-level cap before prediction. Normalize the
        # redundant copies too; otherwise identical three-block trajectories
        # miss the existing cross-cap cache after their first accepted step.
        from evaluation.controllers import sdmpc_sequence as sequence
        if sequence.KEY in physical.diagnostics:
            sequence.actions(physical, 3)  # Reject malformed/nested plans.
            for row in physical.diagnostics[sequence.KEY]['future']:
                row['N_P_star'] = 0.
        return token((z, physical, costs, resources))

    def get(self, key, cap):
        if key not in self.entries:
            return None
        source_cap, grad, matrix = self.entries[key]
        self.reuse.append({'key': key, 'source_np_cap': source_cap, 'np_cap': cap,
                           'anchor_costs_and_resources_exact': True})
        return grad.copy(), matrix.copy()

    def put(self, key, cap, grad, matrix):
        self.entries[key] = cap, grad.copy(), matrix.copy()


def configure(tuning, cfg, controller='wu-link'):
    if controller != 'wu-link':
        return None
    mode = tuning.get('adapter', {}).get('sdmpc')
    if mode is None:
        return None
    if mode not in ('proxlinear-v1', 'central-reuse-v2', 'central-pfo-cap-v3'):
        raise ValueError('Unsupported adapter.sdmpc mode')
    from evaluation import parameters
    options = parameters.section('sdmpc')
    if mode in ('central-reuse-v2', 'central-pfo-cap-v3'):
        central_options = parameters.section('sdmpc_central')
        for key in ('active_tolerance', 'stationarity_tolerance', 'zero_jacobian_tolerance', 'np_step_veh', 'nuf_step_veh_h'):
            if type(central_options[key]) not in (int,float) or not math.isfinite(central_options[key]) or central_options[key] <= 0:
                raise ValueError('Positive central SDMPC parameter required: '+key)
        if type(central_options['duplicate_decimals']) is not int or central_options['duplicate_decimals'] < 1:
            raise ValueError('Invalid central duplicate precision')
        options = dict(options, central_multiplier=True, central_options=central_options)
    if mode == 'central-pfo-cap-v3':
        pfo_cap_options = parameters.section('sdmpc_pfo_cap')
        value = pfo_cap_options['nuf_tolerance_veh_h']
        if type(value) not in (int,float) or not math.isfinite(value) or value < 0:
            raise ValueError('Finite nonnegative NUF cap tolerance required')
        if type(pfo_cap_options['max_iterations']) is not int or pfo_cap_options['max_iterations'] < 1:
            raise ValueError('Positive PFO iteration limit required')
        from evaluation.controllers import sdmpc_budget
        if set(pfo_cap_options) != set(sdmpc_budget.PFO_CAP_KEYS):
            raise ValueError('sdmpc_pfo_cap keys must be exactly: '+', '.join(sdmpc_budget.PFO_CAP_KEYS))
        for key in sdmpc_budget.MARGIN_KEYS:
            pfo_cap_options[key] = sdmpc_budget.checked_margin(pfo_cap_options[key], key)
        options = dict(options, budget_caps=True, pfo_each_interval=True, pfo_cap_options=pfo_cap_options)
    for name in ('response_np_cache', 'fast_primitives', 'prediction_cache', 'compact_audit', 'ramp_stock_cache',
                 'initial_derivative_overlap', 'trial_derivative_overlap', 'spatial_receiving', 'flow_update_cache', 'array_transport', 'persistent_urban_fifo', 'array_urban_pipeline', 'surrogate_reuse', 'initial_shared_prediction', 'prediction_hotpath'):
        value = tuning.get('adapter', {}).get('sdmpc_'+name)
        if value is not None:
            if type(value) is not bool:
                raise ValueError('sdmpc_'+name+' requires a boolean')
            options = dict(options, **{name:value})
    fifo_batch = tuning.get('adapter', {}).get('sdmpc_fifo_batch')
    if fifo_batch is not None:
        if type(fifo_batch) is not bool:
            raise ValueError('adapter.sdmpc_fifo_batch requires a boolean')
        options = dict(options, fifo_batch=fifo_batch)
    derivative_mode = tuning.get('adapter', {}).get('sdmpc_derivatives')
    if derivative_mode is not None:
        if derivative_mode != 'tangent-v1':
            raise ValueError('adapter.sdmpc_derivatives must be tangent-v1')
        options = dict(options, derivatives=derivative_mode,
            tangent_primal_abs_tolerance=parameters.require('sdmpc_tangent', 'primal_abs_tolerance'),
            signal_transition_width_sec=parameters.require('sdmpc_tangent', 'signal_transition_width_sec'))
        for key in ('tangent_primal_abs_tolerance', 'signal_transition_width_sec'):
            if type(options[key]) not in (int, float) or not math.isfinite(options[key]) or options[key] <= 0:
                raise ValueError('SDMPC positive parameter required: '+key)
    blocks = tuning.get('adapter', {}).get('sdmpc_control_blocks')
    primal_audit = tuning.get('adapter', {}).get('sdmpc_primal_audit')
    if primal_audit is not None:
        if type(primal_audit) is not bool:
            raise ValueError('sdmpc_primal_audit requires a boolean')
        options = dict(options, primal_audit=primal_audit)
    immutable_audit = tuning.get('adapter', {}).get('sdmpc_immutable_audit')
    if immutable_audit is not None:
        if type(immutable_audit) is not bool:
            raise ValueError('sdmpc_immutable_audit requires a boolean')
        options = dict(options, immutable_audit=immutable_audit)
    backend = tuning.get('adapter', {}).get('sdmpc_tangent_backend')
    if backend is not None:
        if backend != 'reverse-v1' or derivative_mode != 'tangent-v1':
            raise ValueError('sdmpc_tangent_backend requires reverse-v1 and tangent-v1')
        options = dict(options, tangent_backend=backend)
    shared_primal = tuning.get('adapter', {}).get('sdmpc_tangent_shared_primal')
    concurrent_primal = tuning.get('adapter', {}).get('sdmpc_tangent_concurrent_primal')
    if concurrent_primal is not None:
        if (type(concurrent_primal) is not bool or backend != 'reverse-v1'
                or shared_primal is not True
                or tuning.get('adapter', {}).get('sdmpc_derivative_workers', 1) < 2):
            raise ValueError('sdmpc_tangent_concurrent_primal requires shared reverse-v1 and 2..8 workers')
        options = dict(options, tangent_concurrent_primal=concurrent_primal)
    if shared_primal is not None:
        if type(shared_primal) is not bool or derivative_mode != 'tangent-v1':
            raise ValueError('sdmpc_tangent_shared_primal requires boolean and tangent-v1')
        options = dict(options, tangent_shared_primal=shared_primal)
    indexed_coverage = tuning.get('adapter', {}).get('sdmpc_indexed_coverage')
    if indexed_coverage is not None:
        if type(indexed_coverage) is not bool:
            raise ValueError('sdmpc_indexed_coverage requires a boolean')
        options = dict(options, indexed_coverage=indexed_coverage)
    derivative_workers = tuning.get('adapter', {}).get('sdmpc_derivative_workers')
    if derivative_workers is not None:
        if (type(derivative_workers) is not int or not 1 <= derivative_workers <= 8
                or derivative_mode != 'tangent-v1'):
            raise ValueError('sdmpc_derivative_workers requires 1..8 and tangent-v1')
        options = dict(options, derivative_workers=derivative_workers)
    aggregate = tuning.get('adapter', {}).get('sdmpc_aggregate_predictor')
    if aggregate is not None:
        if aggregate != 'route-bins-v1' or derivative_mode != 'tangent-v1':
            raise ValueError('sdmpc_aggregate_predictor requires route-bins-v1 and tangent-v1')
        options = dict(options,aggregate_predictor=aggregate)
    if blocks is not None:
        if (type(blocks) is not int or blocks != 3 or cfg.mpc.horizon_steps != blocks
                or cfg.simulation.T_c_sec != 150 or derivative_mode != 'tangent-v1'):
            raise ValueError('adapter.sdmpc_control_blocks requires 3 x 150s and tangent-v1')
        options = dict(options, control_blocks=blocks)
    if options.get('fast_primitives') and (backend != 'reverse-v1' or primal_audit is not True):
        raise ValueError('sdmpc_fast_primitives requires reverse-v1 and primal_audit')
    if options.get('compact_audit') and primal_audit is not True:
        raise ValueError('sdmpc_compact_audit requires primal_audit')
    if options.get('ramp_stock_cache') and not options.get('prediction_cache'):
        raise ValueError('sdmpc_ramp_stock_cache requires prediction_cache')
    if options.get('flow_update_cache') and not options.get('prediction_cache'):
        raise ValueError('sdmpc_flow_update_cache requires prediction_cache')
    if options.get('array_transport') and (not options.get('prediction_cache') or backend != 'reverse-v1'):
        raise ValueError('sdmpc_array_transport requires prediction_cache and reverse-v1')
    if options.get('persistent_urban_fifo') and (not options.get('prediction_cache') or backend != 'reverse-v1'):
        raise ValueError('sdmpc_persistent_urban_fifo requires prediction_cache and reverse-v1')
    if options.get('array_urban_pipeline') and (not options.get('prediction_cache')
            or not options.get('fast_primitives') or backend != 'reverse-v1'):
        raise ValueError('sdmpc_array_urban_pipeline requires prediction_cache, fast_primitives and reverse-v1')
    if options.get('surrogate_reuse') and (backend != 'reverse-v1' or blocks != 3
            or not options.get('response_np_cache') or options.get('derivative_workers') != 8):
        raise ValueError('sdmpc_surrogate_reuse requires reverse-v1, three blocks, NP cache and eight workers')
    if options.get('initial_shared_prediction') and (not options.get('surrogate_reuse')
            or not tuning.get('freeway', {}).get('lane_plant')):
        raise ValueError('sdmpc_initial_shared_prediction requires surrogate_reuse and lane_plant')
    if options.get('prediction_hotpath') and (not options.get('surrogate_reuse')
            or not options.get('fast_primitives') or not options.get('primal_audit')):
        raise ValueError('sdmpc_prediction_hotpath requires continuous surrogate reuse and fast primal checks')
    if options.get('central_multiplier') and (not options.get('surrogate_reuse')
            or not options.get('prediction_hotpath') or blocks != 3):
        raise ValueError('central-reuse-v2 requires the qualified three-block continuous predictor')
    if options.get('initial_derivative_overlap') and (backend!='reverse-v1'
            or concurrent_primal is not True or options.get('derivative_workers',1)<3):
        raise ValueError('sdmpc_initial_derivative_overlap requires concurrent reverse AD and 3..8 workers')
    if options.get('trial_derivative_overlap') and (not options.get('initial_derivative_overlap')
            or not options.get('response_np_cache') or options.get('derivative_workers') != 8):
        raise ValueError('sdmpc_trial_derivative_overlap requires initial overlap, NP response cache and eight workers')
    if options.get('spatial_receiving') and (backend != 'reverse-v1'
            or concurrent_primal is not True or options.get('derivative_workers') != 8):
        raise ValueError('sdmpc_spatial_receiving requires concurrent reverse AD and eight workers')
    if (not getattr(cfg.network, 'physical_ramp_branches', None)
            or not cfg.network.control_area_enabled
            or cfg.network.control_area_beta_seconds != 0
            or not cfg.network.control_area_refresh_nuf_target_each_decision):
        raise ValueError('SDMPC requires physical8, pure Omega TTT and actual-merge NUF')
    for key in ('max_iterations', 'line_search_steps', 'restoration_iterations', 'qp_iterations'):
        if type(options[key]) is not int or options[key] < 1:
            raise ValueError('SDMPC positive integer required: '+key)
    for key in ('proximal', 'fd_green_sec', 'fd_offset_sec', 'fd_meter_green_sec',
                'fd_vsl_kmh', 'budget_scale_np_veh', 'budget_scale_nuf_veh_h',
                'dual_step', 'qp_tolerance', 'objective_tolerance'):
        if type(options[key]) not in (int, float) or not math.isfinite(options[key]) or options[key] <= 0:
            raise ValueError('SDMPC positive parameter required: '+key)
    cfg.network.sdmpc_options = options
    return options


def install_cost_ownership(cfg, detector_mapping):
    """확정 권역과 기존 detector join만 사용; 모호한 재고는 수동 비용으로 보존."""
    from evaluation.controllers.control_area_objective import detector_stock_supports
    root = Path(__file__).resolve().parents[2]
    path = root / cfg.network.sdmpc_options['territory_path']
    territory = json.loads(path.read_text(encoding='utf-8'))['territory']
    physical = {}
    def leaves(value):
        if isinstance(value, dict):
            for child in value.values():
                yield from leaves(child)
        elif isinstance(value, list):
            for child in value:
                yield from leaves(child)
        else:
            yield str(value)
    for group in territory.values():
        for owner, links in group.items():
            for link in leaves(links):
                physical.setdefault(link, set()).add(owner)
    supports = detector_stock_supports(detector_mapping,
        off_ramp_storage_links=cfg.network.off_ramp_storage_link, freeway_chains={})
    owners = set(cfg.network.signals) | set(cfg.network.freeway_links)
    table = {}
    for stock, links in supports.items():
        candidates = set().union(*(physical.get(link, {PASSIVE}) for link in links))
        table[stock] = next(iter(candidates)) if len(candidates) == 1 and candidates <= owners else PASSIVE
    for ramp, owner in cfg.network.ramp_to_freeway.items():
        table['ramp:'+ramp] = owner
    for link in cfg.network.freeway_links:
        table['freeway:'+link] = table['origin:'+link] = link
    # transit은 같은 물리 storage의 내부/외부 cohort를 그대로 계승한다.
    for key, owner in list(table.items()):
        if key.startswith('storage:'):
            table['transit:'+key.split(':', 1)[1]] = owner
    cfg.network.sdmpc_cost_ownership = table
    return {'territory_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'resolved_stock_count': sum(v != PASSIVE for v in table.values()),
            'passive_rule': 'Uncontrolled or ambiguous physical territory; included once in total/external gradient, never assigned invented actuator ownership'}


def omega_costs(point, cfg):
    """같은 적분 기록에서 Ω TTT를 한 번씩 합산한다. 외부 queue는 더하지 않는다."""
    owners = tuple(cfg.network.signals) + tuple(cfg.network.freeway_links)
    pieces = {owner: [] for owner in (*owners, PASSIVE)}
    passive = {}
    table = cfg.network.sdmpc_cost_ownership
    for row in point.control_area_response['residence']:
        dt = float(row['dt_h'])
        for stock, count in row['inside_veh'].items():
            value = dt * count
            if not math.isfinite(value) or value < -1e-10:
                raise ValueError('Invalid Omega residence')
            owner = table.get(stock, PASSIVE)
            pieces[owner].append(value)
            if owner == PASSIVE and value:
                passive[stock] = passive.get(stock, 0.) + value
    costs = {owner: math.fsum(values) for owner, values in pieces.items()}
    total = math.fsum(costs.values())
    if not math.isclose(total, point.control_area['ttt_veh_h'], rel_tol=1e-10, abs_tol=1e-8):
        raise ValueError('SDMPC cost partition differs from original Omega ledger')
    local = {owner: {'cost': costs[owner], 'scope': 'disjoint_omega_residence'} for owner in owners}
    return local, {'schema': 'sdmpc-omega-partition/v1', 'costs': costs,
        'total_veh_h': total, 'residual_veh_h': total-point.control_area['ttt_veh_h'],
        'passive_stocks_veh_h': passive}


class Coordinates:
    """직전 실행 명령에 고정된 좌표와 native green의 선형 제약."""
    def __init__(self, cfg, reference, move_box, options):
        from evaluation.controllers import signal_actuation_contract as signals
        self.cfg, self.reference, self.move_box = cfg, reference.copy(), move_box
        self.axes, self.bounds, self.phase_rows = [], [], []
        self.green_vectors = {}
        self.limits = {(f, k): (a, lim, period) for f, k, a, lim, period in move_box.entries}
        net = cfg.network
        def axis(owner, kind, key, scale, step, lower, upper):
            self.axes.append(dict(owner=owner, kind=kind, key=key, scale=scale, fd=step/scale))
            self.bounds.append((lower/scale, upper/scale))
            return len(self.axes)-1
        for owner in net.signals:
            cycle = float(net.signal_cycle_length(owner))
            live = tuple(net.signal_live_phases(owner))
            basis = signals.native_clock_basis(net, owner)
            concurrent = basis is not None and basis['kind'] == 'concurrent_p1_p2'
            vectors = ({'p1': {'p1': 1.}, 'p2': {'p2': 1., 'p4': -1.}} if concurrent else
                       {p: {p: 1., live[-1]: -1.} for p in live[:-1]})
            owned = []
            for key, changes in vectors.items():
                limit = self.limits['green_times', owner+'_'+key][1]
                j = axis(owner, 'green', key, cycle, options['fd_green_sec'], -limit, limit)
                self.green_vectors[j] = changes
                owned.append(j)
            physical = signals.phase_bounds(net, owner)
            for p in live:
                a, limit, _ = self.limits['green_times', owner+'_'+p]
                lo, hi = physical[p]
                row = {j: cycle*self.green_vectors[j].get(p, 0.) for j in owned}
                self.phase_rows.append((row, max(lo, a-limit)-a, min(hi, a+limit)-a))
            if concurrent:
                a = reference.green_times[owner+'_p2']-reference.green_times[owner+'_p1']-basis['amber_sec']
                row = {j: cycle*(self.green_vectors[j].get('p2', 0.)-self.green_vectors[j].get('p1', 0.)) for j in owned}
                self.phase_rows.append((row, -a, np.inf))
            _, limit, _ = self.limits['offsets', owner]
            axis(owner, 'offset', owner, cycle, options['fd_offset_sec'], -limit, limit)
        for ramp in net.ramps:
            spec = net.physical_ramp_branches
            a, limit, _ = self.limits['diagnostics', 'rw_meter_green_'+ramp]
            allowed = [int(g) for g in spec['ramps'][ramp]['service_by_green_veh_h']
                       if abs(int(g)-a) <= limit and (int(g) == 0 or int(g) >= spec['minimum_green_sec'])]
            j = axis(net.ramp_to_freeway[ramp], 'meter', ramp, spec['cycle_sec'],
                     options['fd_meter_green_sec'], min(allowed)-a, max(allowed)-a)
            self.axes[j].update(allowed=allowed, reference_value=a)
        for owner in net.freeway_links:
            for zone in net.freeway_vsl_zone_free:
                head = net.freeway_vsl_zone_heads[owner][zone]
                key = f'{owner}__seg{head}'
                a, limit, _ = self.limits['vsl', key]
                allowed = [float(v) for v in cfg.freeway_follower.vsl_set if abs(v-a) <= limit]
                j = axis(owner, 'vsl', key, max(cfg.freeway_follower.vsl_set),
                         options['fd_vsl_kmh'], min(allowed)-a, max(allowed)-a)
                self.axes[j].update(allowed=allowed, head=head, reference_value=a)
        n = len(self.axes)
        self.G = np.zeros((len(self.phase_rows), n))
        for i, (row, _, _) in enumerate(self.phase_rows):
            for j, value in row.items():
                self.G[i, j] = value
        self.glo = np.array([r[1] for r in self.phase_rows])
        self.ghi = np.array([r[2] for r in self.phase_rows])
        self.lower, self.upper = np.array(self.bounds).T
        self.owners = tuple(net.signals)+tuple(net.freeway_links)

    def encode(self, control):
        z = []
        for a in self.axes:
            kind, key, owner, scale = (a[k] for k in ('kind', 'key', 'owner', 'scale'))
            if kind == 'green':
                delta = control.green_times[owner+'_'+key]-self.reference.green_times[owner+'_'+key]
            elif kind == 'offset':
                delta = (control.offsets[key]-self.reference.offsets[key]+scale/2)%scale-scale/2
            elif kind == 'meter':
                delta = control.diagnostics['rw_meter_green_'+key]-self.reference.diagnostics['rw_meter_green_'+key]
            else:
                delta = control.vsl[key]-self.reference.vsl[key]
            z.append(delta/scale)
        return np.array(z)

    def valid(self, z, tolerance=1e-8):
        return (np.all(z >= self.lower-tolerance) and np.all(z <= self.upper+tolerance)
                and np.all(self.G@z >= self.glo-tolerance) and np.all(self.G@z <= self.ghi+tolerance))

    def decode(self, z, template, *, previous=None):
        from evaluation.controllers import physical_ramp_branches, signal_actuation_contract as signals
        if not self.valid(z):
            raise ValueError('SDMPC proposed control exceeds native phase constraints')
        out = template.copy()
        out.green_times = dict(self.reference.green_times)
        greens = {r: self.reference.diagnostics['rw_meter_green_'+r] for r in self.cfg.network.ramps}
        for j, a in enumerate(self.axes):
            value = float(z[j]*a['scale'])
            kind, key, owner = (a[k] for k in ('kind', 'key', 'owner'))
            if kind == 'green':
                for p, factor in self.green_vectors[j].items():
                    out.green_times[owner+'_'+p] += factor*value
            elif kind == 'offset':
                out.offsets[key] = round((self.reference.offsets[key]+value)%a['scale'], 3)%a['scale']
            elif kind == 'meter':
                raw = self.reference.diagnostics['rw_meter_green_'+key]+value
                greens[key] = min(a['allowed'], key=lambda g: (abs(g-raw), abs(g-self.reference.diagnostics['rw_meter_green_'+key])))
            else:
                raw = self.reference.vsl[key]+value
                speed = min(a['allowed'], key=lambda v: (abs(v-raw), abs(v-self.reference.vsl[key])))
                for cell, head in enumerate(self.cfg.network.freeway_vsl_zone_head_of_cell[owner]):
                    if head == a['head']:
                        out.vsl[f'{owner}__seg{cell}'] = speed
        for owner in self.cfg.network.signals:
            live = tuple(self.cfg.network.signal_live_phases(owner))
            basis = signals.native_clock_basis(self.cfg.network, owner)
            concurrent = basis is not None and basis['kind'] == 'concurrent_p1_p2'
            for p in live:
                out.green_times[owner+'_'+p] = round(out.green_times[owner+'_'+p], 3)
            pivot = 'p4' if concurrent else live[-1]
            others = ('p2',) if concurrent else live[:-1]
            out.green_times[owner+'_'+pivot] = round(self.cfg.network.signal_effective_green_total(owner)-sum(out.green_times[owner+'_'+p] for p in others), 3)
        for owner in self.cfg.network.freeway_links:
            out.vsl[owner] = min(out.vsl[f'{owner}__seg{i}'] for i in range(len(self.cfg.network.freeway_vsl_zone_head_of_cell[owner])))
        out = physical_ramp_branches.candidate_from_greens(
            out, self.reference if previous is None else previous, self.cfg, greens)
        signals.validate_control(out, self.cfg)
        self.move_box.validate(out)
        return out

    def stencil(self, z, j):
        lo, hi = self.lower[j]-z[j], self.upper[j]-z[j]
        for row, low, high in zip(self.G, self.glo-self.G@z, self.ghi-self.G@z):
            v = row[j]
            if v > 0:
                lo, hi = max(lo, low/v), min(hi, high/v)
            elif v < 0:
                lo, hi = max(lo, high/v), min(hi, low/v)
        axis = self.axes[j]
        if axis['kind'] in ('meter', 'vsl'):
            # Probe legal actuator values directly. A 10 km/h numerical step
            # on the 80/100/120 grid otherwise rounds back to the anchor.
            steps = [(value-axis['reference_value'])/axis['scale']-z[j]
                     for value in axis['allowed']]
            steps = [step for step in steps if lo-1e-10 <= step <= hi+1e-10]
            lower = [step for step in steps if step < -1e-10]
            upper = [step for step in steps if step > 1e-10]
            nearest = lambda values: min(values, key=lambda step: (abs(abs(step)-axis['fd']), abs(step))) if values else 0.
            return nearest(lower), nearest(upper)
        return max(lo, -self.axes[j]['fd']), min(hi, self.axes[j]['fd'])


def solve_qp(center, gradient, proximal, lower, upper, G, glo, ghi, options):
    """교통 rollout이 없는 작은 convex QP; 성공과 제약 잔차를 함께 반환."""
    from scipy.optimize import minimize, LinearConstraint, Bounds
    center, gradient = np.asarray(center), np.asarray(gradient)
    constraints = []
    if len(G):
        equality = np.isfinite(glo) & (glo == ghi)
        for mask in (equality, ~equality):
            if np.any(mask):
                constraints.append(LinearConstraint(G[mask], glo[mask], ghi[mask]))
    result = minimize(lambda d: float(gradient@d + .5*proximal*np.sum((d-center)**2)),
        np.clip(center, lower, upper), jac=lambda d: gradient+proximal*(d-center),
        bounds=Bounds(lower, upper), constraints=constraints, method='SLSQP',
        options={'maxiter': options['qp_iterations'], 'ftol': options['qp_tolerance']})
    d = result.x
    violation = max(float(np.max(lower-d, initial=0)), float(np.max(d-upper, initial=0)),
                    float(np.max(glo-G@d, initial=0)), float(np.max(G@d-ghi, initial=0)))
    return d, {'success': bool(result.success and np.all(np.isfinite(d)) and violation <= 1e-7),
               'message': str(result.message), 'constraint_violation': violation, 'iterations': int(result.nit)}


def load_prices(previous_path, state, policy):
    """native ApplyActionCsv 성공 receipt가 있는 직전 명령만 다음 가격으로 확정."""
    raw = json.loads(Path(previous_path).read_text(encoding='utf-8-sig'))
    saved = raw.get('metadata', {}).get('sdmpc_state')
    if saved is None:
        return np.zeros(2), {'source': 'first_sdmpc_decision', 'committed': False}
    ack = Path(str(previous_path)+'.applied')
    if not ack.is_file():
        raise ValueError('SDMPC prior command lacks native application receipt')
    lines = ack.read_text(encoding='utf-16').splitlines()
    csv_path = Path(previous_path).with_suffix('.csv')
    if (len(lines) != 3 or float(lines[0]) != state.time_sec-state._sdmpc_interval_sec
            or Path(lines[1]).resolve() != csv_path.resolve()
            or int(lines[2]) != csv_path.stat().st_size or saved['schema'] != SCHEMA
            or saved['sim_sec'] != float(lines[0]) or saved['policy_sha256'] != token(policy)):
        raise ValueError('SDMPC prior price/application context mismatch')
    prices = np.array(saved['next_prices_scaled'], dtype=float)
    if (prices.shape != (2,) or not np.all(np.isfinite(prices)) or prices[0] < 0
            or (policy.get('budget_caps') and prices[1] < 0)):
        raise ValueError('Invalid persisted SDMPC budget price')
    return prices, {'source': str(ack), 'committed': True, 'receipt_sha256': hashlib.sha256(ack.read_bytes()).hexdigest()}


def solve(controller, state, forecast, historical, mapping, *, options, runtime_sources,
          worker_bootstrap, budget, progress, previous_path):
    from evaluation.controllers import area_follower_objective as joint
    from evaluation.controllers import area_meter_finalization as meters
    from evaluation.controllers import area_leader_objective as constraints
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    follower, state, forecast, historical = copy.deepcopy((controller.nash_solver, state, forecast, historical))
    cfg, policy = follower.cfg, dict(follower.cfg.network.sdmpc_options)
    central_mode = bool(policy.get('central_multiplier'))
    cap_mode = bool(policy.get('budget_caps'))
    if cap_mode:
        options = dict(options, nuf_tolerance_veh_h=policy['pfo_cap_options']['nuf_tolerance_veh_h'])
    if central_mode:
        from evaluation.controllers import sdmpc_central as central
    from evaluation.controllers import sdmpc_sequence as sequence
    # A previous decision's future plan was never executed. Start from its
    # actually written first-block fields, whether or not sequence mode is on.
    if sequence.KEY in historical.diagnostics:
        historical = sequence.first_action(historical)
    if cfg.mpc.horizon_steps*cfg.simulation.T_c_sec != 450:
        raise ValueError('First SDMPC migration requires the agreed 450s horizon')
    state._sdmpc_interval_sec = cfg.simulation.T_c_sec
    prices, price_receipt = load_prices(previous_path, state, policy)
    initial_central_dual = None
    if central_mode:
        initial_central_dual = central.initialize_duals(prices, caps=cap_mode)
        if price_receipt['committed']:
            saved = json.loads(Path(previous_path).read_text(encoding='utf-8-sig'))['metadata']['sdmpc_state']
            initial_central_dual = np.asarray(saved['next_central_duals_scaled'], dtype=float)
            if (initial_central_dual.shape != ((2,) if cap_mode else (3,)) or not np.isfinite(initial_central_dual).all()
                    or np.any(initial_central_dual < 0)
                    or not np.array_equal(central.signed_prices(initial_central_dual),prices)):
                raise ValueError('Invalid applied central multiplier warm start')
    del state._sdmpc_interval_sec
    source_token = token(runtime_sources)
    reference = meters.prepare_held_actual_reference(historical, cfg)
    scale = np.array([policy['budget_scale_np_veh'], policy['budget_scale_nuf_veh_h']])
    with joint.shared_query_runtime_scope(), ExitStack() as derivative_tasks:
        adapter._PHASE_VECTOR_FOLLOWER['ref'] = follower
        callbacks, context, fingerprint = joint._joint_runtime_callbacks(follower, state, forecast,
            historical, reference, mapping, runtime_sources, reference=reference, total_budget=None,
            directional={}, tolerance=options['nuf_tolerance_veh_h'], budget=budget, price_probe=False)
        query = joint.make_decision_shared_query(follower, state, reference, forecast,
            horizon_steps=cfg.mpc.horizon_steps, source_fingerprint=source_token,
            cache_enabled=True, check_budget=budget.check,
            parallel_workers=options['response_parallel_workers'], worker_bootstrap=worker_bootstrap,
            deadline_monotonic=None if budget.unlimited_time else budget.started+budget.seconds-budget.reserve_sec,
            unlimited_time=budget.unlimited_time)
        budget.response_query = query
        coordinate_type = sequence.SequenceCoordinates if policy.get('control_blocks') == 3 else Coordinates
        coord = coordinate_type(cfg, reference, callbacks['move_box'], policy)
        surrogate = bool(policy.get('surrogate_reuse'))
        if surrogate:
            from evaluation.controllers.sdmpc_tangent_surrogate import Query, MODEL
            from evaluation.controllers.sdmpc_tangent import prepare_request
            query.close()  # The ordinary worker pool has not been started.
            query = Query(prepare_request(follower, state, forecast, reference, reference, coord, worker_bootstrap),
                budget.check, lambda stage, **kw: progress({'stage': stage, **kw}) if progress else None)
            budget.response_query = query
            derivative_tasks.callback(query.close)
        physical_cache = None
        if policy.get('response_np_cache') and not surrogate:
            from evaluation.controllers.sdmpc_response_cache import ResponseCache
            physical_cache = ResponseCache(query, cfg)
        def emit(stage, **kw):
            if progress: progress({'stage': stage, **kw})
        def evaluate(actions, *, derivatives=False):
            answer = (query.evaluate(actions, derivatives=derivatives) if surrogate else
                      physical_cache(actions) if physical_cache is not None else query(tuple(actions))['results'])
            for action, item in zip(actions, answer):
                if item['action_token'] != token(action) or 'sdmpc_omega_partition' not in item:
                    raise ValueError('SDMPC shared response/action mismatch')
            return answer
        def quantity(action, item):
            return constraints.shared_quantity_constraints(follower, action, item['quantities'],
                start_sec=state.time_sec, horizon_steps=cfg.mpc.horizon_steps,
                np_mode='cap', target_np_veh=action.N_P_star, np_tolerance_veh=options['np_tolerance_veh'],
                nuf_mode='cap' if cap_mode else 'equality', target_nuf_veh_h=action.N_UF_star,
                nuf_tolerance_veh_h=options['nuf_tolerance_veh_h'])
        def vector(action, item):
            q = quantity(action, item)
            return np.array([q['np']['actual'], q['nuf']['actual']])
        def feasible(action, item):
            coverage = item['model_constraint_coverage']
            return (quantity(action, item)['feasible'] and item['conditional_model_feasibility_witness']
                    and coverage['complete'] and coverage['conditional_model_feasibility_witness']
                    and item['resource_summary']['max_exceedance_veh'] <= options['shared_tolerance'])
        pfo_receipt = pfo_initial = None
        if cap_mode:
            from evaluation.controllers import sdmpc_pfo, sdmpc_budget
            # Every solve is a fresh control interval. No persisted budget or
            # previous unexecuted plan may bypass this own-cost warm solve.
            warm_action, warm_item, pfo_receipt, pfo_initial = sdmpc_pfo.solve(
                reference,coord,policy,options,evaluate,query.derivative,vector,budget.check,emit)
            pfo_receipt['prediction_rollouts'] = query.stats()['total_rollouts']
            post_pfo_started = perf_counter()
            anchor, initialization = sdmpc_budget.initialize(follower,state,warm_action,warm_item,options)
            query.bind_warm_budget(warm_action,anchor,options)
            emit('sdmpc_pfo_budget_initialized',np_cap=anchor.N_P_star,nuf_cap=anchor.N_UF_star,
                 achieved_np=initialization['achieved_np_veh'],achieved_nuf=initialization['achieved_nuf_veh_h'],
                 np_margin=initialization['np_cap_margin_veh'],nuf_margin=initialization['nuf_cap_margin_veh_h'],
                 source='current_interval_PFO_prediction',extra_rollouts=0)
        else:
            emit('sdmpc_hold_start', axes=len(coord.axes), owners=len(coord.owners))
            shared_initial = bool(policy.get('initial_shared_prediction'))
            held_old = evaluate([reference], derivatives=shared_initial)[0]
            anchor, initialization = joint.initialize_decision_nuf(follower, state, reference, held_old)
            if shared_initial:
                query.bind_initial_target(reference, anchor)
                emit('sdmpc_initial_prediction_shared', removed_scalar_rollouts=1,
                     scope='Initial target binding only; unchanged physical commands and continuous-model AD')
        initial_derivative=None
        domain=None
        if policy.get('initial_derivative_overlap') and not surrogate:
            if not budget.unlimited_time:
                raise ValueError('Initial derivative overlap currently requires an unlimited decision budget')
            # The first NP candidate is always the largest cap, independent of
            # the held-action result. Its complete nonlinear response is still
            # queried and checked below, while this frozen Jacobian is prepared.
            domain = joint.prepare_joint_leader_candidates(controller, state, forecast, historical,
                budget_tolerance_veh_h=options['nuf_tolerance_veh_h'], check_budget=budget.check)
            first=anchor.copy();first.N_P_star=max(domain['np_values'])
            from evaluation.controllers import sdmpc_tangent
            from evaluation.controllers.sdmpc_tangent_prefetch import InitialDerivative
            request=sdmpc_tangent.prepare_request(follower,state,forecast,reference,first,coord,worker_bootstrap)
            initial_derivative=derivative_tasks.enter_context(InitialDerivative(request,sdmpc_tangent.evaluate))
            emit('sdmpc_initial_derivative_overlap_start',axes=len(coord.axes),
                 reserve_ordinary_prediction_workers=1,reverse_worker_limit=policy['derivative_workers']-1)
        held = evaluate([anchor], derivatives=surrogate)[0]
        initialization['physical_commands_unchanged'] = (
            callbacks['command_evidence'](anchor, context)['owner_physical_sha256']
            == callbacks['command_evidence'](warm_action if cap_mode else reference, context)['owner_physical_sha256'])
        if not initialization['physical_commands_unchanged']:
            raise ValueError('SDMPC NUF refresh changed physical commands')
        hold_valid = feasible(anchor, held)
        best = (anchor, held, None) if hold_valid else None
        if domain is None:
            domain = joint.prepare_joint_leader_candidates(controller, state, forecast, historical,
                budget_tolerance_veh_h=options['nuf_tolerance_veh_h'], check_budget=budget.check)
        caps = sorted(set(domain['np_values']), reverse=True)
        observed_np = vector(anchor, held)[0]
        ordered = [caps[0]]
        for subset in (sorted(c for c in caps[1:] if c >= observed_np),
                       sorted((c for c in caps[1:] if c < observed_np), reverse=True)):
            if subset: ordered.append(subset[0])
        targets = ordered[:options['max_leader_candidates']]
        if central_mode:
            targets = [(anchor.N_P_star if cap_mode else targets[0], anchor.N_UF_star)]
        central_rows, dual_updates = [], []
        candidate_rows, gradient_rows, local_rows, trials = [], [], [], []
        costs_order = (*coord.owners, PASSIVE)
        def costs(item):
            return np.array([item['sdmpc_omega_partition']['costs'][p] for p in costs_order])
        derivatives_cache = GradientCache()
        derivative_receipts = []
        pending_derivatives = None
        trial_overlap_rows = []
        def finish_trial_derivatives():
            nonlocal pending_derivatives
            if pending_derivatives is not None:
                pending_derivatives.close()
                pending_derivatives = None
        def derivatives(z, action, item):
            # 모든 player가 정확히 같은 기준점/동일 traffic response를 사용한다.
            key = derivatives_cache.key(z, action, costs(item), vector(action, item))
            cached = derivatives_cache.get(key, action.N_P_star)
            if cached is not None:
                finish_trial_derivatives()
                emit('sdmpc_derivatives_reused', **derivatives_cache.reuse[-1])
                return cached
            grad, A = np.zeros((len(costs_order), len(z))), np.zeros((2, len(z)))
            fallback = {j: 'finite_difference' for j in range(len(z))}
            if policy.get('derivatives') == 'tangent-v1':
                from evaluation.controllers import sdmpc_tangent
                emit('sdmpc_tangent_start', axes=len(z))
                request = (None if surrogate else sdmpc_tangent.prepare_request(follower, state, forecast,
                    reference, action, coord, worker_bootstrap))
                if surrogate:
                    receipt = query.derivative(action)
                elif initial_derivative is not None and not initial_derivative.consumed:
                    receipt = initial_derivative.consume(request)
                elif pending_derivatives is not None:
                    if pending_derivatives.contains_action(action):
                        receipt = pending_derivatives.consume(request)
                        finish_trial_derivatives()
                    else:
                        # Restoration can choose an action outside the trial
                        # batch. Drain owned work before using all eight slots.
                        finish_trial_derivatives()
                        receipt = sdmpc_tangent.evaluate(request)
                else:
                    receipt = sdmpc_tangent.evaluate(request)
                grad, A, fallback = sdmpc_tangent.checked_matrices(receipt,
                    costs(item), vector(action, item), coord.axes,
                    policy['tangent_primal_abs_tolerance'], allow_surrogate=surrogate)
                A = A/scale[:, None]
                derivative_receipts.append(receipt)
                emit('sdmpc_tangent_done', ad_axes=len(z)-len(fallback),
                    fallback_axes=len(fallback), seconds=receipt['wall_sec_including_spawn'])
            candidates, stencils = [], []
            for j in range(len(z)):
                if j not in fallback:
                    stencils.append(None)
                    continue
                endpoints = []
                for delta in coord.stencil(z, j):
                    zz = z.copy(); zz[j] += delta
                    try: aa = coord.decode(zz, action)
                    except ValueError: aa = action
                    actual = coord.encode(aa)
                    changed = np.flatnonzero(np.abs(actual-z)>1e-9)
                    if len(changed) and (len(changed) != 1 or changed[0] != j):
                        raise ValueError('FD stencil changed another independent coordinate')
                    if not len(changed):
                        endpoints.append((None, z[j]))
                    else:
                        endpoints.append((len(candidates), actual[j])); candidates.append(aa)
                stencils.append(endpoints)
            emit('sdmpc_derivatives_start', evaluations=len(candidates))
            measured = evaluate(candidates) if candidates else []
            resolved = []
            for j, stencil in enumerate(stencils):
                if stencil is None:
                    resolved.append(j)
                    gradient_rows.append({**coord.axes[j], 'anchor_z': z[j], 'stencil': None,
                        'resolved': True, 'derivative_method': ('compiled_reverse_active_path'
                            if policy.get('tangent_backend') == 'reverse-v1' else 'sparse_forward_active_path'),
                        'own': grad[costs_order.index(coord.axes[j]['owner']), j],
                        'external': float(grad[:, j].sum()-grad[costs_order.index(coord.axes[j]['owner']), j]),
                        'total': float(grad[:, j].sum()), 'resource_derivatives_scaled': A[:, j].tolist()})
                    continue
                (li, lv), (ri, rv) = stencil
                low, high = item if li is None else measured[li], item if ri is None else measured[ri]
                la, ha = action if li is None else candidates[li], action if ri is None else candidates[ri]
                if rv-lv > 1e-10:
                    grad[:, j] = (costs(high)-costs(low))/(rv-lv)
                    A[:, j] = (vector(ha, high)-vector(la, low))/(rv-lv)/scale
                    resolved.append(j)
                gradient_rows.append({**coord.axes[j], 'anchor_z': z[j], 'stencil': [lv, rv],
                    **({'derivative_method': 'executable_secant_fallback', 'fallback_reason': fallback[j]}
                       if policy.get('derivatives') == 'tangent-v1' else {}),
                    'resolved': j in resolved, 'own': grad[costs_order.index(coord.axes[j]['owner']), j],
                    'external': float(grad[:, j].sum()-grad[costs_order.index(coord.axes[j]['owner']), j]),
                    'total': float(grad[:, j].sum()), 'resource_derivatives_scaled': A[:, j].tolist()})
            derivatives_cache.put(key, action.N_P_star, grad, A)
            emit('sdmpc_derivatives_done', resolved_axes=len(resolved), all_axes=len(z))
            return grad, A
        def qp(z, center, gradient, proximal, A=None, c=None, ix=None):
            ix = np.arange(len(z)) if ix is None else ix
            G, lo, hi = coord.G[:, ix], coord.glo-coord.G@z, coord.ghi-coord.G@z
            active = np.any(G != 0, axis=1)
            G, lo, hi = G[active], lo[active], hi[active]
            if A is not None:
                G = np.vstack((G, A[:, ix]))
                if central_mode:
                    eps = np.array([options['np_tolerance_veh'],options['nuf_tolerance_veh_h']])/scale
                    resource_lo, resource_hi = central.qp_bounds(c, eps, caps=cap_mode)
                    lo, hi = np.r_[lo, resource_lo], np.r_[hi, resource_hi]
                else:
                    lo, hi = np.r_[lo, -np.inf, -c[1]], np.r_[hi, -c[0], -c[1]]
            return solve_qp(center, gradient, proximal, coord.lower[ix]-z[ix], coord.upper[ix]-z[ix], G, lo, hi, policy)
        for requested in targets:
            cap, requested_nuf = requested if central_mode else (requested, anchor.N_UF_star)
            action = anchor.copy(); action.N_P_star = cap
            if central_mode:
                action.N_UF_star = requested_nuf
                candidate_dual = initial_central_dual.copy()
                model_references = []
            current = evaluate([action])[0]
            z, status, accepted = coord.encode(action), 'iteration_limit', 0
            target = np.array([cap, requested_nuf])
            candidate_best = (action, current, None) if feasible(action, current) else None
            emit('sdmpc_candidate_start', np_cap=cap, nuf=requested_nuf)
            for iteration in range(policy['max_iterations']):
                budget.check('sdmpc_iteration')
                grad, A = derivatives(z, action, current)
                iteration_prices = prices
                if central_mode:
                    iteration_prices = central.signed_prices(candidate_dual)
                    receipt = query.derivative(action)
                    model_references.append((z.copy(),grad.copy(),A.copy(),receipt['central_physical']))
                c = (vector(action, current)-target)/scale
                proposal = np.zeros(len(z))
                for owner in coord.owners:
                    ix = np.array([j for j,a in enumerate(coord.axes) if a['owner']==owner])
                    own = grad[costs_order.index(owner), ix]
                    external = grad[:, ix].sum(axis=0)-own
                    d, receipt = qp(z, np.zeros(len(ix)), own+external+(A.T@iteration_prices)[ix], policy['proximal'], ix=ix)
                    local_rows.append({'cap': cap, 'iteration': iteration, 'owner': owner,
                        'own_gradient': own.tolist(), 'externality_gradient': external.tolist(),
                        'price_gradient': (A.T@iteration_prices)[ix].tolist(), 'step': d.tolist(),
                        'traffic_rollouts': 0, **receipt})
                    if receipt['success']: proposal[ix] = d
                raw = c+A@proposal
                if central_mode:
                    before_dual = candidate_dual.copy()
                    candidate_dual = central.update_duals(candidate_dual,raw,
                        np.array([options['np_tolerance_veh'],options['nuf_tolerance_veh_h']])/scale,
                        policy['dual_step'],caps=cap_mode)
                    dual_updates.append(dict(cap=cap,nuf_target=requested_nuf,iteration=iteration,
                        before=before_dual.tolist(),after=candidate_dual.tolist(),
                        prices_used=iteration_prices.tolist(),raw_residual_scaled=raw.tolist(),
                        same_anchor_for_all_players=True))
                step, qr = qp(z, proposal, np.zeros(len(z)), 1., A, c)
                if not qr['success']:
                    status = 'linear_resource_qp_failed'; break
                trial_actions = []
                for k in range(policy['line_search_steps']):
                    try: candidate = coord.decode(z+(.5**k)*step, action)
                    except ValueError: continue
                    if token(candidate) not in {token(a) for a in trial_actions}: trial_actions.append(candidate)
                if not trial_actions:
                    status = 'no_executable_step'; break
                if (policy.get('trial_derivative_overlap') and not surrogate
                        and iteration+1 < policy['max_iterations'] and len(trial_actions) <= 2):
                    from evaluation.controllers.sdmpc_response_cache import physical_key
                    # A cross-cap cache hit has no ordinary prediction to hide
                    # latency behind, and its derivative is normally cached too.
                    if all(physical_key(a) not in physical_cache.entries for a in trial_actions):
                        if pending_derivatives is not None:
                            raise ValueError('Previous speculative derivatives were not joined')
                        from evaluation.controllers import sdmpc_tangent
                        from evaluation.controllers.sdmpc_tangent_prefetch import TrialDerivatives
                        requests = [sdmpc_tangent.prepare_request(follower, state, forecast,
                            reference, a, coord, worker_bootstrap) for a in trial_actions]
                        pending_derivatives = derivative_tasks.enter_context(
                            TrialDerivatives(requests, sdmpc_tangent.evaluate))
                        trial_overlap_rows.append(pending_derivatives.receipt)
                        emit('sdmpc_trial_derivative_overlap_start', cap=cap, iteration=iteration,
                            candidates=len(trial_actions),
                            reverse_workers_per_derivative=pending_derivatives.reverse_workers,
                            max_numerical_workers=pending_derivatives.receipt['max_numerical_workers'])
                values = evaluate(trial_actions, derivatives=surrogate and iteration+1 < policy['max_iterations'])
                winners = []
                for a, value in zip(trial_actions, values):
                    ok = feasible(a, value)
                    trials.append({'cap': cap, 'iteration': iteration, 'objective': value['objective_veh_h'],
                        'quantities': quantity(a, value), 'feasible': ok, 'action_token': token(a)})
                    if ok: winners.append((a, value))
                # 양자화 또는 비선형 오차로 막힌 후보는 원 모델에서 제한된 복원.
                if not winners:
                    a, value = min(zip(trial_actions, values), key=lambda av: float(np.linalg.norm((vector(*av)-target)/scale)))
                    for _ in range(policy['restoration_iterations']):
                        zz = coord.encode(a); cc = (vector(a,value)-target)/scale
                        correction, cr = qp(zz, np.zeros(len(z)), np.zeros(len(z)), 1., A, cc)
                        if not cr['success']: break
                        try: repaired = coord.decode(zz+correction, a)
                        except ValueError: break
                        if token(repaired) == token(a): break
                        a, value = repaired, evaluate([repaired])[0]
                        if feasible(a,value): winners.append((a,value)); break
                if not winners:
                    status = 'no_feasible_nonlinear_step'; break
                chosen, value = min(winners, key=lambda av: av[1]['objective_veh_h'])
                if candidate_best is not None and value['objective_veh_h'] >= candidate_best[1]['objective_veh_h']-policy['objective_tolerance']:
                    status = 'no_improving_step'; break
                signal = {'raw_local_residual_scaled': raw.tolist(), 'anchor_residual_scaled': c.tolist(),
                    'resource_jacobian_scaled': A.tolist(), 'raw_local_step': proposal.tolist()}
                if central_mode:
                    signal['candidate_dual'] = candidate_dual.tolist()
                candidate_best = (chosen, value, signal)
                action, current, z = chosen, value, coord.encode(chosen)
                accepted += 1
                emit('sdmpc_step_accepted', cap=cap, iteration=iteration, objective=value['objective_veh_h'])
            finish_trial_derivatives()
            candidate_rows.append({'np_cap': cap, 'nuf_target': requested_nuf, 'status': status,
                'accepted_steps': accepted, 'feasible': candidate_best is not None,
                'objective': candidate_best[1]['objective_veh_h'] if candidate_best else None,
                **({'executed_iterations':iteration+1,'max_iterations':policy['max_iterations']} if cap_mode else {}),
                'converged': False})
            if central_mode:
                final_action, final_item, _ = candidate_best if candidate_best is not None else (action,current,None)
                final_z = coord.encode(final_action)
                if not model_references:
                    raise ValueError('No lower model for central multiplier recovery')
                _, reference_model = min(enumerate(model_references),
                    key=lambda pair:(float(np.linalg.norm(pair[1][0]-final_z)),-pair[0]))
                before_rollouts = query.stats()['total_rollouts']
                recovery = central.recover((*reference_model,final_item['central_physical']),
                    final_z,vector(final_action,final_item),target,scale,
                    np.array([options['np_tolerance_veh'],options['nuf_tolerance_veh_h']]),
                    coord,policy['central_options'],candidate_best is not None,caps=cap_mode)
                if query.stats()['total_rollouts'] != before_rollouts:
                    raise ValueError('Central recovery unexpectedly predicted traffic')
                recovery.update(np_cap=cap,nuf_target=requested_nuf)
                central_rows.append(recovery)
                emit('sdmpc_central_recovery_done',np_cap=cap,nuf=requested_nuf,seconds=recovery['seconds'],
                    physical_constraints=recovery['physical_constraints'],stationarity_inf=recovery['stationarity_inf'],
                    additional_rollouts=0)
                if len(targets) < options['max_leader_candidates']:
                    limits = (sdmpc_budget.search_limits(targets[0],caps,cfg.network.total_ramp_capacity)
                        if cap_mode else ([min(caps),0.],[max(caps),cfg.network.total_ramp_capacity]))
                    new_target = central.next_budget(targets[0],recovery,targets,
                        limits,policy['central_options'])
                    if new_target is not None:
                        targets.append(tuple(new_target))
            if candidate_best and (best is None or candidate_best[1]['objective_veh_h'] < best[1]['objective_veh_h']-policy['objective_tolerance']):
                best = candidate_best
        if best is None:
            raise ValueError('SDMPC found no executable feasible candidate; hold was also infeasible')
        selected, item, signal = best
        sequence_proof = coord.validate(selected) if policy.get('control_blocks') == 3 else None
        # 기존 검증의 물리/제약/명령 부분만 재사용한다. hold 또는 Nash로 명명하지 않는다.
        response = joint.validate_actual_decision_hold(follower, state, selected, item,
            callbacks=callbacks, context=context, source_fingerprint=source_token, options=options)
        if not response['feasible']: raise ValueError('SDMPC final validation failed')
        response.update(schema='validated-sdmpc-response/v1', algorithm=SCHEMA,
            scope='Prox-linear SDMPC final original-model and physical-command validation; no Nash or nonlinear convergence claim')
        if surrogate:
            response.update(prediction_model=MODEL, execution_model_evaluated=False,
                scope='Continuous surrogate feasibility and physical-command validation; exact actuator dynamics and native feasibility unverified')
        if sequence_proof is not None:
            response['control_sequence'] = {**sequence_proof, 'plan_action_token': token(selected),
                'start_sec': state.time_sec, 'end_sec': state.time_sec+3*cfg.simulation.T_c_sec,
                'scope': 'Three-block model feasibility; only block zero is written and later blocks are replanned'}
        next_prices = prices.copy()
        if signal is not None:
            if central_mode:
                next_prices = central.signed_prices(signal['candidate_dual'])
            else:
                next_prices += policy['dual_step']*np.array(signal['raw_local_residual_scaled'])
                next_prices[0] = max(0., next_prices[0])
        state_record = {'schema': SCHEMA, 'sim_sec': state.time_sec, 'policy_sha256': token(policy),
            'prices_scaled': prices.tolist(), 'next_prices_scaled': next_prices.tolist(),
            'pending_native_application': True, 'price_update_signal': signal,
            'previous_application': price_receipt}
        if central_mode:
            state_record.update(central_duals_scaled=initial_central_dual.tolist(),
                next_central_duals_scaled=signal['candidate_dual'] if signal is not None else initial_central_dual.tolist())
        metadata = {'algorithm': SCHEMA, 'converged': False, 'feasible': True,
            'selection_status': 'best_observed_feasible_sdmpc', 'candidates': candidate_rows,
            'nuf_initialization': initialization, 'held_feasible': hold_valid,
            'held_objective': held['objective_veh_h'], 'selected_objective': item['objective_veh_h'],
            'prediction_ttt_reduction': held['objective_veh_h']-item['objective_veh_h'],
            'final_constraints': response['final_score']['quantity_constraints'],
            'omega_partition': item['sdmpc_omega_partition'], 'price_state': state_record,
            'coordinates': coord.axes, 'gradient_rows': gradient_rows, 'local_rows': local_rows,
            'gradient_reuse': derivatives_cache.reuse,
            **({'physical_response_cache':physical_cache.stats()} if physical_cache is not None else {}),
            **({'trial_derivative_overlaps':trial_overlap_rows}
               if policy.get('trial_derivative_overlap') else {}),
            **({'tangent_derivatives': derivative_receipts}
               if policy.get('derivatives') == 'tangent-v1' else {}),
            'trial_rows': trials, 'local_trial_traffic_rollouts': 0,
            'finite_neighbor_audit_performed': False, 'policy': policy}
        if central_mode:
            metadata.update(algorithm='sdmpc-central-reuse/v2',central_multiplier=central_rows,
                iteration_dual_updates=dual_updates, price_update='each_lower_iteration_after_all_players',
                leader_signal='separate_approximate_central_multiplier',
                nuf_definition='predicted_accepted_mainline_merge',
                nuf_target_policy='initial_hold_merge_then_leader_candidate_search',
                central_derivative_work=[row['central_physical']['derivative_work'] for row in derivative_receipts])
        if cap_mode:
            metadata.pop('nuf_initialization'); metadata.pop('held_feasible')
            metadata.update(algorithm='sdmpc-central-pfo-cap/v3',pfo_warm_start=pfo_receipt,
                budget_initialization=initialization,budget_constraint_policy='NP <= cap; actual_merge_NUF <= cap',
                nuf_target_policy='fresh_PFO_achieved_plus_margin_budget_each_interval_then_leader_search',
                warm_start_feasible=hold_valid,warm_start_objective=held['objective_veh_h'],
                held_objective=pfo_initial['objective_veh_h'],
                prediction_ttt_reduction=pfo_initial['objective_veh_h']-item['objective_veh_h'],
                sdmpc_after_pfo_seconds=perf_counter()-post_pfo_started,
                sdmpc_after_pfo_rollouts=query.stats()['total_rollouts']-pfo_receipt['prediction_rollouts'])
        if surrogate:
            metadata.update(prediction_model=MODEL, execution_model_evaluated=False,
                independent_ad_witness_performed=False, surrogate_query=query.stats())
        if sequence_proof is not None:
            metadata['control_sequence'] = response['control_sequence']
        emit('sdmpc_completed', objective=item['objective_veh_h'], held_objective=held['objective_veh_h'])
        return response, metadata
