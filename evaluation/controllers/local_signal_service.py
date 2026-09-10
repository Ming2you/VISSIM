"""One physical service pool shared by global and local urban service.

The opt-in is limited to the evidenced closed SC1004/10634 group. Rates,
turning fractions, clock profiles and receiving allocation come from the
configured canonical model. Mutable budgets live in each substep, never cfg.
"""
from __future__ import annotations
import functools
import math
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Sequence
from src.models.state import MODEL_PHASES
from src.models.urban_queue_model import _allocate_receiving_counts

EPS = 1e-8
CONNECTOR = '10634'
MEMBERS = ('SC1004_offW_to_E_SC1005', 'SC1004_offE_to_E_SC1005',
           'SC1004_W_to_E_SC1005')
_READY_CONTEXT = ContextVar('shared_service_ready_seed', default=None)
_READY_METRICS = ContextVar('shared_service_candidate_metrics', default=None)


def _calibrated_resource_present(cfg):
    spec = getattr(cfg.network, 'route_choice_corridor', None) or {}
    return any(CONNECTOR in row.get('calibrated_service_resources', {})
               for row in spec.get('corridors', [spec]))


def configure(cfg, tuning):
    flag = (tuning or {}).get('urban', {}).get('shared_local_service_pool', False)
    if not isinstance(flag, bool):
        raise ValueError('urban.shared_local_service_pool must be boolean')
    if not flag:
        if _calibrated_resource_present(cfg):
            raise ValueError('Calibrated shared resource requires shared_local_service_pool')
        current = view(cfg)
        if current is not None:
            if current.get('schema') != 'shared-local-service-pool/v1':
                raise ValueError('Cannot clear an unowned local service specification')
            delattr(cfg.network, 'local_service_pool')
        return {}
    from evaluation.controllers.signal_actuation_contract import enabled
    if not enabled(cfg.network):
        raise ValueError('Shared local service requires the physical signal clock')
    spec = getattr(cfg.network, 'route_choice_corridor', None)
    if not spec:
        raise ValueError('Shared local service requires configured route corridors')
    turns = {m: t for m, t in spec['turns'].items() if t['connector'] == CONNECTOR}
    if set(turns) != set(MEMBERS):
        raise ValueError('The reviewed closed 10634 service group changed')
    signatures = []
    for m, turn in turns.items():
        movement = cfg.network.urban_movements[m]
        signatures.append((movement['signal'], movement['phase'], movement['receiving_link'],
                           float(turn['service_veh_h']), bool(turn['signal_controlled'])))
        if movement.get('ramp') or float(turn['service_veh_h']) != float(cfg.network.movement_capacity_by_movement_veh_h[m]):
            raise ValueError('Physical turn service no longer matches local cached capacity')
    if len(set(signatures)) != 1 or signatures[0][:2] != ('SC1004', 'SC1004_p3') or not signatures[0][-1]:
        raise ValueError('Sources sharing 10634 must use the same signal, phase, receiver and rate')
    signal, phase, receiver, rate, _ = signatures[0]
    _nonnegative(rate)
    if rate == 0:
        raise ValueError('Physical service rate must be positive')
    cfg.network.local_service_pool = {
        'schema': 'shared-local-service-pool/v1',
        'group_of': {m: CONNECTOR for m in MEMBERS},
        'groups': {CONNECTOR: {'members': MEMBERS, 'signal': signal,
                              'phase': phase, 'receiver': receiver, 'service_veh_h': rate}}}
    return {**install(cfg), 'local_shared_service_pool_groups': 1.,
            'local_shared_service_pool_phase_refinement': 1.}


def view(cfg):
    return getattr(cfg.network, 'local_service_pool', None)


def _nonnegative(value):
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError('Service operands must be finite and nonnegative')
    return value


def register_limit(limits, group, rate, dt_h, fraction):
    fraction = _nonnegative(fraction)
    if fraction > 1:
        raise ValueError('Physical green fraction exceeds one')
    budget = _nonnegative(rate) * _nonnegative(dt_h) * fraction
    prior = limits.get(group)
    if prior is not None and not math.isclose(prior, budget, abs_tol=EPS):
        raise ValueError('Sources sharing a physical turn have different service budgets')
    limits[group] = budget
    return budget


def limit_one(available, group, limits, used):
    return min(_nonnegative(available), max(0., limits[group] - used.get(group, 0.)))


def accepted(vehicles, group, limits, used):
    total = used.get(group, 0.) + _nonnegative(vehicles)
    if group not in limits or total > limits[group] + EPS:
        raise ValueError('Accepted physical service exceeds its registered budget')
    used[group] = total


def limit_batch(requests, group_of, limits, used, rule):
    grouped = {}
    for movement, amount in requests.items():
        if movement in group_of:
            grouped.setdefault(group_of[movement], {})[movement] = _nonnegative(amount)
    result = dict(requests)
    for group, amounts in grouped.items():
        remaining = max(0., limits[group] - used.get(group, 0.))
        result.update(_allocate_receiving_counts(rule, amounts, remaining))
    return result


def _model_view(model):
    spec = view(model.cfg)
    if not spec or not any(m in spec['group_of'] for m in model.movements):
        return None
    for group in spec['groups'].values():
        if not set(group['members']).issubset(model.movements) or model.signal != group['signal'] or not model.has_ramps:
            raise ValueError('Local signal model does not contain the complete physical pool')
        for m in group['members']:
            if (model.receiving_of[m] != group['receiver'] or model.cap_flow_of[m] != group['service_veh_h']
                    or model.phase_of[m] != group['phase'].rsplit('_', 1)[-1]):
                raise ValueError('Stale local physical service cache')
    return spec


@dataclass(frozen=True)
class ReadySeed:
    """Immutable reservations on existing stock, rebuilt from this solve's state."""
    start_step: int
    dt_h: float
    fw_steps: int
    delay_steps: int
    # (off, storage, capacity, initial_stock, direct_share, ((due_step, veh), ...))
    rows: tuple


def ready_vehicles(stock, pending, service_step):
    stock = _nonnegative(stock)
    if type(service_step) is not int:
        raise ValueError('Ready service step must be an integer')
    future = 0.
    for due, amount in pending.items():
        if type(due) is not int:
            raise ValueError('Pending arrival step must be an integer')
        amount = _nonnegative(amount)
        if due > service_step:
            future += amount
    if future > stock + EPS:
        raise ValueError('Pending transit exceeds physical OR stock')
    return max(0., stock - future)


def make_ready_seed(state, model):
    from src.models.urban_queue_model import _urban_step_index, _inflow_delay_steps
    cfg = model.cfg; sim = cfg.simulation; net = cfg.network
    start = _urban_step_index(state, cfg)
    if abs(float(state.time_sec) - start * sim.T_u_sec) > 1e-6:
        raise ValueError('Ready state must lie on the explicit urban step lattice')
    block = int(sim.K_fu)
    if block < 1 or not math.isclose(block * sim.T_u_h, sim.T_f_h, abs_tol=1e-12):
        raise ValueError('Ready arrivals require integral Tf/Tu')
    rows = []
    for off in sorted(model.offramp_movements):
        storage = net.off_ramp_storage_link[off]
        cap = _nonnegative(net.urban_link_storage_veh[storage])
        stock = cap - _nonnegative(state.urban_link_storage[storage])
        share = _nonnegative((getattr(net, 'offramp_direct_share_by_offramp', {}) or {}).get(off, 0.))
        if share > 1. or model.offramp_storage_cap[off] != cap:
            raise ValueError('Invalid signal branch share or stale local OR capacity')
        pending = dict(state.offramp_transit_buffer.get(storage, {}))
        ready_vehicles(stock, pending, start)
        rows.append((off, storage, cap, stock, share, tuple(sorted(pending.items()))))
    return ReadySeed(start, float(sim.T_u_h), block, _inflow_delay_steps(cfg), tuple(rows))


def _ready_copy(seed, model, occupancy, dt_h, profile_start_step):
    if (not isinstance(seed, ReadySeed) or type(seed.start_step) is not int
            or type(profile_start_step) is not int or profile_start_step != seed.start_step):
        raise ValueError('Ready seed and physical green profile clock are required')
    sim = model.cfg.simulation; net = model.cfg.network
    if (seed.dt_h != dt_h or dt_h != sim.T_u_h or seed.fw_steps != sim.K_fu
            or seed.delay_steps < 1 or set(occupancy) != set(model.offramp_movements)
            or len(seed.rows) != len(model.offramp_movements)
            or {r[0] for r in seed.rows} != set(model.offramp_movements)):
        raise ValueError('Stale ready model/time coverage')
    from src.models.urban_queue_model import _inflow_delay_steps
    if seed.delay_steps != _inflow_delay_steps(model.cfg):
        raise ValueError('Ready delay differs from canonical scheduling')
    pending = {}; share = {}
    for off, storage, cap, stock, direct, reservations in seed.rows:
        if (storage != net.off_ramp_storage_link[off] or cap != model.offramp_storage_cap[off]
                or stock != occupancy[off] or direct != float((getattr(net, 'offramp_direct_share_by_offramp', {}) or {}).get(off, 0.))):
            raise ValueError('Ready seed differs from candidate initial stock/configuration')
        pending[off] = dict(reservations); share[off] = direct
        ready_vehicles(stock, pending[off], seed.start_step)
    return pending, share


@contextmanager
def bind_ready(state, model):
    """Bound only for one actual caller; no model/config mutation or parent cache."""
    token = _READY_CONTEXT.set((model, make_ready_seed(state, model)))
    try:
        yield
    finally:
        _READY_CONTEXT.reset(token)


def install_ready_callers():
    from src.controllers.wu_faithful_follower import WuFaithfulFollower as cls
    if not getattr(cls._solve_urban_agent_local, '_shared_ready_scope', False):
        original_green = cls._solve_urban_agent_local
        @functools.wraps(original_green)
        def green(self, signal, state, *args, **kwargs):
            model = self._local_models.get(signal)
            if model is None or _model_view(model) is None:
                return original_green(self, signal, state, *args, **kwargs)
            # The baseline ramp green solver defaults to cycle averages.
            # Opt this signal into its existing physical-profile branch only
            # for this call; restore the original set even on nested failures.
            active = self._phase_resolved_active_signals
            self._phase_resolved_active_signals = set(active) | {signal}
            try:
                with bind_ready(state, model):
                    return original_green(self, signal, state, *args, **kwargs)
            finally:
                self._phase_resolved_active_signals = active
        green._shared_ready_scope = True
        cls._solve_urban_agent_local = green
    if not getattr(cls._solve_offset_local_ramp, '_shared_ready_scope', False):
        original_offset = cls._solve_offset_local_ramp
        @functools.wraps(original_offset)
        def offset(self, signal, green_p1, state, *args, **kwargs):
            model = self._local_models.get(signal)
            if model is None or _model_view(model) is None:
                return original_offset(self, signal, green_p1, state, *args, **kwargs)
            with bind_ready(state, model):
                return original_offset(self, signal, green_p1, state, *args, **kwargs)
        offset._shared_ready_scope = True
        cls._solve_offset_local_ramp = offset
    from src.controllers.priced_wu_link_controller import LinkAgentWuFollower
    if not getattr(LinkAgentWuFollower.solve, '_shared_ready_metrics', False):
        original_solve = LinkAgentWuFollower.solve
        @functools.wraps(original_solve)
        def solve(self, *args, **kwargs):
            if not view(self.cfg):
                return original_solve(self, *args, **kwargs)
            summary = {}; token = _READY_METRICS.set(summary)
            try:
                result = original_solve(self, *args, **kwargs)
                result.diagnostics.update(summary)
                result.control.diagnostics.update(summary)
                return result
            finally:
                _READY_METRICS.reset(token)
        solve._shared_ready_metrics = True
        LinkAgentWuFollower.solve = solve


def install(cfg):
    if not view(cfg):
        if _calibrated_resource_present(cfg):
            raise ValueError('Calibrated shared resource requires shared_local_service_pool')
        return {}
    from src.controllers import local_signal_plant, wu_faithful_follower
    for module in (local_signal_plant, wu_faithful_follower):
        original = module.rollout_local_tts_ramp_aware
        if getattr(original, '_shared_local_service_pool', False):
            continue
        @functools.wraps(original)
        def rollout(model, *args, _original=original, **kwargs):
            if _model_view(model) is None:
                return _original(model, *args, **kwargs)
            if kwargs.get('ready_seed') is None:
                bound = _READY_CONTEXT.get()
                if bound is None or bound[0] is not model:
                    raise ValueError('Shared service caller is missing its own ready context')
                kwargs['ready_seed'] = bound[1]
                kwargs['green_profile_start_step'] = bound[1].start_step
            return rollout_shared_ramp(model, *args, **kwargs)
        rollout._shared_local_service_pool = True
        module.rollout_local_tts_ramp_aware = rollout
    install_ready_callers()
    install_refinement(cfg)
    return {'local_shared_service_pool_installed': 1., 'local_shared_service_pool_phase_refinement': 1.,
            'local_shared_service_pool_ready_transit': 1., 'local_shared_service_pool_frozen_group_signal_split': 1.,
            'local_shared_service_pool_scoped_phased_green': 1.}


def rollout_shared_ramp(
    model,
    q0: Mapping[str, float],
    arr_movement: Mapping[str, float],
    s_eff0: Mapping[str, float],
    offramp_inflow: Mapping[str, float],
    offramp_occ0: Mapping[str, float],
    ramp_queue0: Mapping[str, float],
    reservoir_drain: Mapping[str, float],
    freeway_congestion: Mapping[str, float],
    ramp_metering_weight: float,
    greens: Mapping[str, float],
    substeps: int,
    dt_h: float,
    arr_by_substep: Optional[Mapping[str, Sequence[float]]] = None,
    gf_by_substep: Optional[Mapping[str, Sequence[float]]] = None,
    s_eff_by_substep: Optional[Mapping[str, Sequence[float]]] = None,
    ready_seed=None,
    green_profile_start_step=None,
    ready_trace=None,
    ready_diagnostics=None,
) -> float:
    """Narrow extraction of vendor ramp-aware substeps; no other local plant copied."""
    if gf_by_substep is None:
        raise ValueError('Shared local service requires explicit physical green profiles')
    pool = _model_view(model)
    group_of = pool['group_of']
    groups = pool['groups']
    for movement in group_of:
        profile = gf_by_substep.get(movement)
        if profile is None or len(profile) != substeps:
            raise ValueError('Missing or stale physical green profile for ' + movement)
        for value in profile:
            if _nonnegative(value) > 1.:
                raise ValueError('Physical green fraction exceeds one')
    pooled_receivers = {g['receiver'] for g in groups.values()}
    if not pooled_receivers.issubset(s_eff0):
        raise ValueError('Shared physical service requires its receiving-space operand')
    net = model.cfg.network
    cycle = max(net.cycle_length, 1.0e-9)
    green = {pid: float(greens.get(pid, 0.0)) for pid in MODEL_PHASES}

    def _gf(m: str, sub: int) -> float:
        if gf_by_substep is not None:
            prof = gf_by_substep.get(m)
            if prof is not None:
                return float(prof[sub])
        return green[model.phase_of[m]] / cycle
    ramp_movement_set = {m for mv in model.onramp_movements.values() for m in mv}
    queue_movements = [m for m in model.movements if model.kind_of[m] != "off_ramp"]
    q: Dict[str, float] = {m: max(0.0, float(q0.get(m, 0.0))) for m in queue_movements}
    occ: Dict[str, float] = {
        orr: max(0.0, float(offramp_occ0.get(orr, 0.0))) for orr in model.offramp_movements
    }
    pending, direct_share = _ready_copy(ready_seed, model, occ, dt_h, green_profile_start_step)
    initial_off_stock = sum(occ.values()); accepted_arrivals = departed_off = 0.
    offered_arrivals = rejected_arrivals = overflow_blocks = max_residual = 0.
    res: Dict[str, float] = {
        ramp: max(0.0, float(ramp_queue0.get(ramp, 0.0))) for ramp in model.onramp_movements
    }
    own_origin_links = {model.origin_of[m] for m in queue_movements if model.origin_of[m]}
    s_eff: Dict[str, float] = {link: max(0.0, float(v)) for link, v in s_eff0.items()}

    cost = 0.0
    for sub in range(substeps):
        service_step = ready_seed.start_step + sub
        eligible = {off: ready_vehicles(n, pending[off], service_step) for off, n in occ.items()}
        for reservations in pending.values():
            for due in tuple(reservations):
                if due <= service_step:
                    del reservations[due]
        stock_before = dict(occ) if ready_trace is not None else None
        limits, used = {}, {}
        for group, detail in groups.items():
            for m in detail['members']:
                register_limit(limits, group, detail['service_veh_h'], dt_h, _gf(m, sub))
        if s_eff_by_substep is not None:
            for recv, prof in s_eff_by_substep.items():
                if recv in s_eff:
                    s_eff[recv] = max(0.0, float(prof[sub]))
        receiver_left = {r: s_eff[r] for r in pooled_receivers if r in s_eff}
        for m in queue_movements:
            if arr_by_substep is not None:
                prof = arr_by_substep.get(m)
                if prof is not None:
                    q[m] += float(prof[sub]) * dt_h
                    continue
            q[m] += arr_movement.get(m, 0.0) * dt_h

        for ramp in model.onramp_movements:
            res[ramp] = max(0.0, res.get(ramp, 0.0) - reservoir_drain.get(ramp, 0.0) * dt_h)

        for ramp, movements in model.onramp_movements.items():
            requests: Dict[str, float] = {}
            for m in movements:
                green_fraction = _gf(m, sub)
                requests[m] = min(
                    max(0.0, q[m]), dt_h * green_fraction * model.cap_flow_of[m]
                )
            requested_total = sum(requests.values())
            ramp_space = max(0.0, model.ramp_queue_max - res.get(ramp, 0.0))
            scale = 1.0 if requested_total <= ramp_space else ramp_space / max(requested_total, 1.0e-9)
            released_total = 0.0
            for m, requested in requests.items():
                actual = min(max(0.0, q[m]), requested * scale)
                q[m] = max(0.0, q[m] - actual)
                released_total += actual
            res[ramp] = min(model.ramp_queue_max, res.get(ramp, 0.0) + released_total)
            cost += (
                released_total * freeway_congestion.get(ramp, 0.0) * ramp_metering_weight
            )

        for off_ramp in net.off_ramps:
            movements = model.offramp_movements.get(off_ramp, ())
            occupancy = occ.get(off_ramp, 0.0)
            available_stock = eligible.get(off_ramp, 0.)
            if available_stock <= 0.0:
                continue
            released_total = 0.0
            for m in movements:
                beta = model.beta_of[m]
                if beta <= 0.0:
                    continue
                green_fraction = _gf(m, sub)
                intended = min(beta * available_stock, dt_h * green_fraction * model.cap_flow_of[m],
                               max(0., available_stock - released_total))
                if m in group_of:
                    intended = limit_one(intended, group_of[m], limits, used)
                recv = model.receiving_of[m]
                if recv and recv in s_eff:
                    actual = min(intended, receiver_left.get(recv, s_eff[recv]))
                else:
                    actual = intended
                if actual <= 0.0:
                    continue
                released_total += actual
                if m in group_of:
                    accepted(actual, group_of[m], limits, used)
                if recv in receiver_left:
                    receiver_left[recv] = max(0., receiver_left[recv] - actual)
                if recv in own_origin_links and recv in s_eff:
                    s_eff[recv] = max(0.0, s_eff[recv] - actual)
            occ[off_ramp] = max(0.0, occupancy - released_total)
            departed_off += released_total

        intended_by_link: Dict[str, Dict[str, float]] = {}
        no_link_intended: Dict[str, float] = {}
        for m in queue_movements:
            if m in ramp_movement_set:
                continue  # ramp행 movement는 (a)에서 처리됨.
            green_fraction = _gf(m, sub)
            intended = min(max(0.0, q[m]), dt_h * green_fraction * model.cap_flow_of[m])
            recv = model.receiving_of[m]
            if recv and recv in s_eff:
                intended_by_link.setdefault(recv, {})[m] = intended
            else:
                no_link_intended[m] = intended
        actual: Dict[str, float] = dict(no_link_intended)
        for link, intended in intended_by_link.items():
            intended = limit_batch(intended, group_of, limits, used, model.receiving_space_rule)
            actual.update(_allocate_receiving_counts(
                model.receiving_space_rule, intended, receiver_left.get(link, s_eff.get(link, 0.0)),
            ))
        for m in queue_movements:
            if m in ramp_movement_set:
                continue
            departed = min(q[m], max(0.0, actual.get(m, 0.0)))
            if departed <= 0.0:
                continue
            q[m] -= departed
            if m in group_of:
                accepted(departed, group_of[m], limits, used)
            recv = model.receiving_of[m]
            if recv in receiver_left:
                receiver_left[recv] = max(0., receiver_left[recv] - departed)
            if recv in own_origin_links and recv in s_eff:
                s_eff[recv] = max(0.0, s_eff[recv] - departed)

        cost += (sum(q.values()) + sum(occ.values()) + sum(res.values())) * dt_h
        _pq_mv = str(getattr(model.cfg.mpc, "protected_queue_movement", "") or "")
        if _pq_mv and _pq_mv in q:
            _pq_w = float(getattr(model.cfg.mpc, "protected_queue_weight", 0.0))
            if _pq_w > 0.0:
                _pq_max = float(getattr(model.cfg.mpc, "protected_queue_max_veh", 50.0))
                cost += _pq_w * max(0.0, q[_pq_mv] - _pq_max) * dt_h
        # Global: urban service/residence precedes the next FW block landing.
        residence_off_stock = sum(occ.values())
        landings = []
        boundary = service_step + 1
        if (sub + 1) % ready_seed.fw_steps == 0:
            for off in model.offramp_movements:
                gross = _nonnegative(offramp_inflow.get(off, 0.)) * dt_h * ready_seed.fw_steps
                offered = gross * (1. - direct_share[off])
                room = max(0., model.offramp_storage_cap[off] - occ[off])
                landed = min(offered, room)
                due = boundary + ready_seed.delay_steps
                occ[off] += landed; accepted_arrivals += landed
                offered_arrivals += offered; rejected_arrivals += offered - landed
                overflow_blocks += float(offered - landed > EPS)
                if landed:
                    pending[off][due] = pending[off].get(due, 0.) + landed
                landings.append({'offramp': off, 'admission_step': boundary, 'due_step': due,
                    'gross_offered_veh': gross, 'direct_outside_local_OR_veh': gross - offered,
                    'signal_offered_veh': offered, 'signal_accepted_veh': landed,
                    'signal_rejected_veh': offered - landed})
        residual = sum(occ.values()) - initial_off_stock - accepted_arrivals + departed_off
        max_residual = max(max_residual, abs(residual))
        if abs(residual) > 1e-7:
            raise ValueError('Local OR stock/accepted flow conservation failed')
        if ready_trace is not None:
            ready_trace.append({'service_step': service_step, 'eligible_veh': dict(eligible),
                'stock_before_veh': stock_before, 'residence_off_stock_veh': residence_off_stock,
                'stock_after_landing_veh': dict(occ), 'pending': {o: dict(p) for o, p in pending.items()},
                'landings': landings, 'stock_residual_veh': residual})
    metrics = {'signal_offered_veh': offered_arrivals, 'signal_accepted_veh': accepted_arrivals,
               'signal_rejected_veh': rejected_arrivals, 'overflow_blocks': overflow_blocks,
               'max_abs_stock_residual_veh': max_residual}
    if ready_diagnostics is not None:
        ready_diagnostics.update(metrics)
    summary = _READY_METRICS.get()
    if summary is not None:
        # These describe searched candidates, never claimed selected physical flows.
        prefix = 'shared_service_ready_'
        summary[prefix + 'candidate_count'] = summary.get(prefix + 'candidate_count', 0.) + 1.
        summary[prefix + 'overflow_candidate_count'] = summary.get(prefix + 'overflow_candidate_count', 0.) + float(rejected_arrivals > EPS)
        for key, value in metrics.items():
            name = prefix + 'candidate_max_' + key
            summary[name] = max(summary.get(name, 0.), value)
    return float(cost)


def ramp_refinement_setup(agent, signal, state, ctx):
    """Same ramp inputs as GNE/offset solve; no new flow, geometry or rate fit."""
    model = agent._local_models[signal]
    off_inflow = {off: agent._frozen_offramp_inflow(off, state)
                  for off in model.offramp_movements}
    off_phase = {p: 0. for p in MODEL_PHASES}
    for off, movements in model.offramp_movements.items():
        for m in movements:
            off_phase[model.phase_of[m]] += model.beta_of[m] * off_inflow[off]
    arrivals = agent._per_movement_arrivals(signal, state, ctx['snapshot'], ctx['demand'])
    arr_mv = {}
    for phase in MODEL_PHASES:
        movements = [m for m in model.movements if model.phase_of[m] == phase
                     and model.kind_of[m] != 'off_ramp']
        raw = sum(max(0., float(arrivals.get(m, 0.))) for m in movements)
        target = max(0., float(ctx['coupling'].get(f'arr_{signal}_{phase}', 0.)) - off_phase[phase])
        for m in movements:
            arr_mv[m] = max(0., float(arrivals.get(m, 0.))) * (target / raw) if raw > 1e-12 else 0.
    profiles = agent._platoon_arrival_profiles(
        signal, state, ctx['snapshot'], ctx['demand'], arr_mv, ctx['substeps'], ctx['start_idx'])
    return {'shared_ramp_service': True, 'model': model, 'ready_seed': make_ready_seed(state, model),
            'q0': {m: max(0., float(state.urban_movement_queue.get(m, 0.))) for m in model.movements},
            'arr_mv': arr_mv, 'arr': {m: p for m, p in profiles.items() if model.kind_of[m] != 'off_ramp'},
            's_eff0': {model.receiving_of[m]: float(ctx['s_eff_frozen'].get(model.receiving_of[m], 0.))
                       for m in model.movements if model.receiving_of[m]},
            'off_inflow': off_inflow,
            'off_occ': {off: agent._offramp_occupancy(off, state) for off in model.offramp_movements},
            'ramp_q': {r: max(0., float(state.ramp_queue.get(r, 0.))) for r in model.onramp_movements},
            'drain': agent._frozen_reservoir_drain(state, ctx['snapshot'], ctx['demand']),
            'congestion': agent._frozen_freeway_congestion(state)}


def ramp_refinement_cost(agent, signal, phases, setup, ctx):
    fraction = agent._offset_green_fractions_vec(
        signal, phases, float(ctx['snapshot'].offsets.get(signal, 0.)), ctx['substeps'], ctx['start_idx'])
    return rollout_shared_ramp(
        setup['model'], setup['q0'], setup['arr_mv'], setup['s_eff0'],
        setup['off_inflow'], setup['off_occ'], setup['ramp_q'], setup['drain'],
        setup['congestion'], agent.ramp_metering_weight, phases,
        ctx['substeps'], ctx['dt_h'], arr_by_substep=setup['arr'], gf_by_substep=fraction,
        ready_seed=setup['ready_seed'], green_profile_start_step=ctx['start_idx'])


def install_refinement(cfg):
    if not view(cfg):
        return
    from src.controllers.priced_wu_link_controller import LinkAgentWuFollower
    cls = LinkAgentWuFollower
    if all(getattr(getattr(cls, name), '_shared_local_service_pool', False) for name in (
            '_phase_refine_context', '_phase_refine_signal_setup', '_phase_local_cost_phased')):
        return
    original_context = cls._phase_refine_context
    original_setup = cls._phase_refine_signal_setup
    original_cost = cls._phase_local_cost_phased
    @functools.wraps(original_context)
    def context(self, state, control, demand):
        if view(self.cfg):
            # The inherited signature omits stocks and mutable Wu flow caches.
            # Build once per refinement invocation; reuse only within that ctx.
            self.__dict__.pop('_phase_ctx_cache', None)
        result = original_context(self, state, control, demand)
        if view(self.cfg) and result is None:
            raise ValueError('Shared ramp refinement requires phased mode and current demand')
        return result
    @functools.wraps(original_setup)
    def setup(self, signal, state, ctx):
        model = self._local_models.get(signal)
        if model is None or _model_view(model) is None:
            return original_setup(self, signal, state, ctx)
        cached = ctx.setdefault('setups', {}).get(signal)
        if cached is None:
            cached = ramp_refinement_setup(self, signal, state, ctx)
            ctx['setups'][signal] = cached
        if not cached.get('shared_ramp_service'):
            raise ValueError('Stale non-ramp phase-refinement setup')
        return cached
    @functools.wraps(original_cost)
    def cost(self, signal, phases, setup, ctx):
        if view(self.cfg) and setup.get('shared_ramp_service'):
            return ramp_refinement_cost(self, signal, phases, setup, ctx)
        return original_cost(self, signal, phases, setup, ctx)
    setup._shared_local_service_pool = True
    cost._shared_local_service_pool = True
    context._shared_local_service_pool = True
    # A late adapter installer replaces setup/cost but leaves context intact.
    # Restore only the replaced methods; do not stack cache-reset wrappers.
    if not getattr(original_context, '_shared_local_service_pool', False):
        cls._phase_refine_context = context
    cls._phase_refine_signal_setup = setup
    cls._phase_local_cost_phased = cost
