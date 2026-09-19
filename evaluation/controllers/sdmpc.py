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
    if mode != 'proxlinear-v1':
        raise ValueError('adapter.sdmpc must be proxlinear-v1')
    from evaluation import parameters
    options = parameters.section('sdmpc')
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

    def decode(self, z, template):
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
        out = physical_ramp_branches.candidate_from_greens(out, self.reference, self.cfg, greens)
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
    if prices.shape != (2,) or not np.all(np.isfinite(prices)) or prices[0] < 0:
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
    if cfg.mpc.horizon_steps*cfg.simulation.T_c_sec != 450:
        raise ValueError('First SDMPC migration requires the agreed 450s horizon')
    state._sdmpc_interval_sec = cfg.simulation.T_c_sec
    prices, price_receipt = load_prices(previous_path, state, policy)
    del state._sdmpc_interval_sec
    source_token = token(runtime_sources)
    reference = meters.prepare_held_actual_reference(historical, cfg)
    scale = np.array([policy['budget_scale_np_veh'], policy['budget_scale_nuf_veh_h']])
    with joint.shared_query_runtime_scope():
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
        coord = Coordinates(cfg, reference, callbacks['move_box'], policy)
        def emit(stage, **kw):
            if progress: progress({'stage': stage, **kw})
        def evaluate(actions):
            answer = query(tuple(actions))['results']
            for action, item in zip(actions, answer):
                if item['action_token'] != token(action) or 'sdmpc_omega_partition' not in item:
                    raise ValueError('SDMPC shared response/action mismatch')
            return answer
        def quantity(action, item):
            return constraints.shared_quantity_constraints(follower, action, item['quantities'],
                start_sec=state.time_sec, horizon_steps=cfg.mpc.horizon_steps,
                np_mode='cap', target_np_veh=action.N_P_star, np_tolerance_veh=options['np_tolerance_veh'],
                nuf_mode='equality', target_nuf_veh_h=action.N_UF_star, nuf_tolerance_veh_h=options['nuf_tolerance_veh_h'])
        def vector(action, item):
            q = quantity(action, item)
            return np.array([q['np']['actual'], q['nuf']['actual']])
        def feasible(action, item):
            coverage = item['model_constraint_coverage']
            return (quantity(action, item)['feasible'] and item['conditional_model_feasibility_witness']
                    and coverage['complete'] and coverage['conditional_model_feasibility_witness']
                    and item['resource_summary']['max_exceedance_veh'] <= options['shared_tolerance'])
        emit('sdmpc_hold_start', axes=len(coord.axes), owners=len(coord.owners))
        held_old = evaluate([reference])[0]
        anchor, initialization = joint.initialize_decision_nuf(follower, state, reference, held_old)
        held = evaluate([anchor])[0]
        initialization['physical_commands_unchanged'] = (
            callbacks['command_evidence'](anchor, context)['owner_physical_sha256']
            == callbacks['command_evidence'](reference, context)['owner_physical_sha256'])
        if not initialization['physical_commands_unchanged']:
            raise ValueError('SDMPC NUF refresh changed physical commands')
        hold_valid = feasible(anchor, held)
        best = (anchor, held, None) if hold_valid else None
        domain = joint.prepare_joint_leader_candidates(controller, state, forecast, historical,
            budget_tolerance_veh_h=options['nuf_tolerance_veh_h'], check_budget=budget.check)
        caps = sorted(set(domain['np_values']), reverse=True)
        observed_np = vector(anchor, held)[0]
        ordered = [caps[0]]
        for subset in (sorted(c for c in caps[1:] if c >= observed_np),
                       sorted((c for c in caps[1:] if c < observed_np), reverse=True)):
            if subset: ordered.append(subset[0])
        targets = ordered[:options['max_leader_candidates']]
        candidate_rows, gradient_rows, local_rows, trials = [], [], [], []
        costs_order = (*coord.owners, PASSIVE)
        def costs(item):
            return np.array([item['sdmpc_omega_partition']['costs'][p] for p in costs_order])
        derivatives_cache = GradientCache()
        def derivatives(z, action, item):
            # 모든 player가 정확히 같은 기준점/동일 traffic response를 사용한다.
            key = derivatives_cache.key(z, action, costs(item), vector(action, item))
            cached = derivatives_cache.get(key, action.N_P_star)
            if cached is not None:
                emit('sdmpc_derivatives_reused', **derivatives_cache.reuse[-1])
                return cached
            candidates, stencils = [], []
            for j in range(len(z)):
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
            grad, A = np.zeros((len(costs_order), len(z))), np.zeros((2, len(z)))
            resolved = []
            for j, ((li, lv), (ri, rv)) in enumerate(stencils):
                low, high = item if li is None else measured[li], item if ri is None else measured[ri]
                la, ha = action if li is None else candidates[li], action if ri is None else candidates[ri]
                if rv-lv > 1e-10:
                    grad[:, j] = (costs(high)-costs(low))/(rv-lv)
                    A[:, j] = (vector(ha, high)-vector(la, low))/(rv-lv)/scale
                    resolved.append(j)
                gradient_rows.append({**coord.axes[j], 'anchor_z': z[j], 'stencil': [lv, rv],
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
                lo = np.r_[lo, -np.inf, -c[1]]
                hi = np.r_[hi, -c[0], -c[1]]
            return solve_qp(center, gradient, proximal, coord.lower[ix]-z[ix], coord.upper[ix]-z[ix], G, lo, hi, policy)
        for cap in targets:
            action = anchor.copy(); action.N_P_star = cap
            current = evaluate([action])[0]
            z, status, accepted = coord.encode(action), 'iteration_limit', 0
            target = np.array([cap, anchor.N_UF_star])
            candidate_best = (action, current, None) if feasible(action, current) else None
            emit('sdmpc_candidate_start', np_cap=cap, nuf=anchor.N_UF_star)
            for iteration in range(policy['max_iterations']):
                budget.check('sdmpc_iteration')
                grad, A = derivatives(z, action, current)
                c = (vector(action, current)-target)/scale
                proposal = np.zeros(len(z))
                for owner in coord.owners:
                    ix = np.array([j for j,a in enumerate(coord.axes) if a['owner']==owner])
                    own = grad[costs_order.index(owner), ix]
                    external = grad[:, ix].sum(axis=0)-own
                    d, receipt = qp(z, np.zeros(len(ix)), own+external+(A.T@prices)[ix], policy['proximal'], ix=ix)
                    local_rows.append({'cap': cap, 'iteration': iteration, 'owner': owner,
                        'own_gradient': own.tolist(), 'externality_gradient': external.tolist(),
                        'price_gradient': (A.T@prices)[ix].tolist(), 'step': d.tolist(),
                        'traffic_rollouts': 0, **receipt})
                    if receipt['success']: proposal[ix] = d
                raw = c+A@proposal
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
                values = evaluate(trial_actions)
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
                candidate_best = (chosen, value, signal)
                action, current, z = chosen, value, coord.encode(chosen)
                accepted += 1
                emit('sdmpc_step_accepted', cap=cap, iteration=iteration, objective=value['objective_veh_h'])
            candidate_rows.append({'np_cap': cap, 'nuf_target': anchor.N_UF_star, 'status': status,
                'accepted_steps': accepted, 'feasible': candidate_best is not None,
                'objective': candidate_best[1]['objective_veh_h'] if candidate_best else None,
                'converged': False})
            if candidate_best and (best is None or candidate_best[1]['objective_veh_h'] < best[1]['objective_veh_h']-policy['objective_tolerance']):
                best = candidate_best
        if best is None:
            raise ValueError('SDMPC found no executable feasible candidate; hold was also infeasible')
        selected, item, signal = best
        # 기존 검증의 물리/제약/명령 부분만 재사용한다. hold 또는 Nash로 명명하지 않는다.
        response = joint.validate_actual_decision_hold(follower, state, selected, item,
            callbacks=callbacks, context=context, source_fingerprint=source_token, options=options)
        if not response['feasible']: raise ValueError('SDMPC final validation failed')
        response.update(schema='validated-sdmpc-response/v1', algorithm=SCHEMA,
            scope='Prox-linear SDMPC final original-model and physical-command validation; no Nash or nonlinear convergence claim')
        next_prices = prices.copy()
        if signal is not None:
            next_prices += policy['dual_step']*np.array(signal['raw_local_residual_scaled'])
            next_prices[0] = max(0., next_prices[0])
        state_record = {'schema': SCHEMA, 'sim_sec': state.time_sec, 'policy_sha256': token(policy),
            'prices_scaled': prices.tolist(), 'next_prices_scaled': next_prices.tolist(),
            'pending_native_application': True, 'price_update_signal': signal,
            'previous_application': price_receipt}
        metadata = {'algorithm': SCHEMA, 'converged': False, 'feasible': True,
            'selection_status': 'best_observed_feasible_sdmpc', 'candidates': candidate_rows,
            'nuf_initialization': initialization, 'held_feasible': hold_valid,
            'held_objective': held['objective_veh_h'], 'selected_objective': item['objective_veh_h'],
            'prediction_ttt_reduction': held['objective_veh_h']-item['objective_veh_h'],
            'final_constraints': response['final_score']['quantity_constraints'],
            'omega_partition': item['sdmpc_omega_partition'], 'price_state': state_record,
            'coordinates': coord.axes, 'gradient_rows': gradient_rows, 'local_rows': local_rows,
            'gradient_reuse': derivatives_cache.reuse,
            'trial_rows': trials, 'local_trial_traffic_rollouts': 0,
            'finite_neighbor_audit_performed': False, 'policy': policy}
        emit('sdmpc_completed', objective=item['objective_veh_h'], held_objective=held['objective_veh_h'])
        return response, metadata
