"""Use the canonical Omega endpoint for follower ranking and offset retention."""
from __future__ import annotations
import math
from contextlib import contextmanager


@contextmanager
def shared_response_gc_scope(enabled=False):
    """Defer cyclic collection through one synchronous physical response.

    Reference counting remains active. Always collect deferred cycles and
    restore the caller's collector state before returning, including failures.
    Cleanup belongs to the endpoint time/budget, not to background work.
    A nested scope or an already-disabled collector is left untouched.
    """
    if type(enabled) is not bool:
        raise ValueError('Response GC deferral must be boolean')
    import gc
    from time import perf_counter, process_time
    stats = {'cyclic_gc_deferred_queries': 0, 'cyclic_gc_cleanup_wall_sec': 0.,
             'cyclic_gc_cleanup_cpu_sec': 0., 'cyclic_gc_collected_objects': 0}
    restore = enabled and gc.isenabled()
    if restore:
        gc.disable()
        stats['cyclic_gc_deferred_queries'] = 1
    try:
        yield stats
    finally:
        if restore:
            wall, cpu = perf_counter(), process_time()
            try:
                stats['cyclic_gc_collected_objects'] = gc.collect()
            finally:
                gc.enable()
                stats['cyclic_gc_cleanup_wall_sec'] = perf_counter()-wall
                stats['cyclic_gc_cleanup_cpu_sec'] = process_time()-cpu


@contextmanager
def shared_query_runtime_scope():
    """Restore adapter runtime data after a serial model/command query.

    Includes operational lane/segment contexts, not just diagnostic counters.
    Runtime installers and source changes must finish before opening this scope;
    this is not a lock for concurrent COM/model sessions or hook installation.
    """
    import copy
    import pickle
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    def selected(key, value):
        return key.startswith('_') and key.isupper() and isinstance(value, (dict, list, set))
    # This is an installed solver binding, not query-owned runtime data. A deep
    # copy must not silently replace the controller that later callbacks read.
    bound_follower = getattr(adapter, '_PHASE_VECTOR_FOLLOWER', {}).get('ref')
    def clone(value):
        memo = {id(bound_follower): bound_follower} if bound_follower is not None else {}
        return copy.deepcopy(value, memo)
    def children(value):
        if not isinstance(value, (dict, list)):
            return None
        items = value.items() if isinstance(value, dict) else enumerate(value)
        # Keep entry refs separately: equal per-root bytes cannot prove an
        # external cfg alias survived replacement by an equal-valued child.
        return tuple((key, child, None if child is bound_follower or
                      type(child) in (type(None), bool, int, float, complex, str, bytes)
                      else pickle.dumps(child, protocol=5)) for key, child in items)
    def unchanged(child, encoded):
        if encoded is None:
            return True
        try:
            return pickle.dumps(child, protocol=5) == encoded
        except Exception as exc:
            if isinstance(exc, MemoryError):
                raise
            return False
    saved = {key: (value, clone(value), children(value)) for key, value in vars(adapter).items()
             if selected(key, value)}
    try:
        yield
    finally:
        for key in tuple(vars(adapter)):
            if selected(key, getattr(adapter, key)) and key not in saved:
                delattr(adapter, key)
        for key, (original, before, entries) in saved.items():
            if entries is not None:
                restored, fallback = [], None
                for child_key, child, encoded in entries:
                    if unchanged(child, encoded):
                        restored.append((child_key, child))
                    else:
                        if fallback is None:
                            fallback = clone(before)
                        # Never roll back the entry child in place: a cfg/state
                        # alias that was actually mutated must remain changed
                        # outside runtime so the full context guard rejects it.
                        restored.append((child_key, fallback[child_key]))
                if isinstance(original, dict):
                    current = list(original.items())
                    if len(current) != len(restored) or any(
                            a is not c or b is not d for (a, b), (c, d) in zip(current, restored)):
                        original.clear()
                        original.update(restored)
                else:
                    values = [child for _, child in restored]
                    if len(original) != len(values) or any(a is not b for a, b in zip(original, values)):
                        original[:] = values
            else:
                # Config-name/kind sets contain immutable strings. Rebuilding
                # an unchanged set can reorder its hash table and its pickle,
                # spuriously invalidating an otherwise unchanged context.
                unchanged_keywords = (type(original) is set and original == before
                                      and all(type(item) is str for item in original))
                if not unchanged_keywords:
                    original.clear()
                    original.update(clone(before))
            setattr(adapter, key, original)

def enabled(cfg):
    return bool(getattr(cfg.network, "control_area_enabled", False))


def expand_shared_vsl_action(action, cfg, *, segment_vsl_func):
    """Expand a historical direction-only action using the installed writer.

    Warmup records can omit segment keys while commanding their direction value
    at every DSD. Fill only absent keys and verify every effective segment value
    before/after. Existing inconsistent segment values or fallback aliases fail.
    No new speed level, meter, signal or past physical command is selected.
    """
    import copy
    import pickle
    def packed(value):
        return pickle.dumps(value, protocol=5)
    before = packed(action)
    result = copy.deepcopy(action)
    added, effective = [], {}
    with shared_query_runtime_scope():
        for link in cfg.network.freeway_links:
            count = len(cfg.network.freeway_vsl_zone_head_of_cell[link])
            values = [float(segment_vsl_func(action, link, i, cfg)) for i in range(count)]
            if not values or not all(math.isfinite(v) for v in values):
                raise ValueError('Incomplete finite historical VSL command')
            if result.vsl.get(link) != min(values):
                raise ValueError('Historical direction fallback differs from its effective segment minimum')
            for i, value in enumerate(values):
                key = f'{link}__seg{i}'
                if key in result.vsl and result.vsl[key] != value:
                    raise ValueError('Historical explicit VSL differs from its effective written value')
                if key not in result.vsl:
                    result.vsl[key] = value
                    added.append(key)
            effective[link] = values
        for link, values in effective.items():
            if values != [float(segment_vsl_func(result, link, i, cfg)) for i in range(len(values))]:
                raise ValueError('Historical VSL expansion changed effective segment commands')
    if packed(action) != before:
        raise ValueError('Historical VSL expansion mutated caller input')
    if packed({k: v for k, v in vars(result).items() if k != 'vsl'}) != packed(
            {k: v for k, v in vars(action).items() if k != 'vsl'}):
        raise ValueError('Historical VSL expansion changed another action field')
    return result, {'added_segment_keys': added, 'effective_segment_commands_preserved': True,
                    'effective_segment_values': effective,
                    'source': 'Installed segment_vsl used by canonical writer'}


def shared_urban_cost_inputs(follower, response, *, start_sec, horizon_steps):
    """Project accepted joint-trajectory operands onto existing local models.

    This changes neither the local cost expression nor the shared dynamics.
    Ordinary and ramp-aware local queues keep their existing attribution. The
    optional trace's whole physical stock is used; Omega-only cohorts are not
    substituted for those existing local operands. Resource-limit certification,
    external prices and quantity terms are separate contracts.
    """
    cfg = follower.cfg
    if not enabled(cfg) or response.get('schema') != 'control-area-fixed-response/v1':
        raise ValueError('Shared local inputs require a canonical Omega response')
    if type(horizon_steps) is not int or horizon_steps < 1:
        raise ValueError('Explicit positive held horizon required')
    dt_sec = float(cfg.simulation.T_u_sec)
    dt_h = float(cfg.simulation.T_u_h)
    start_step = int(round(float(start_sec) / dt_sec))
    if not math.isfinite(float(start_sec)) or abs(start_step * dt_sec - start_sec) > 1e-8:
        raise ValueError('Shared response start is not on the urban clock')
    count = horizon_steps * int(cfg.simulation.K_cu)
    models = follower._local_models
    if set(models) != set(cfg.network.signals):
        raise ValueError('Shared response must cover every configured urban owner')
    samples = [row for row in response['residence'] if row['stage'] == 'urban']
    if len(samples) != count:
        raise ValueError('Incomplete urban residence horizon')
    for index, row in enumerate(samples):
        if (row['start_sec'] != (start_step + index) * dt_sec
                or row['end_sec'] != (start_step + index + 1) * dt_sec or row['dt_h'] != dt_h):
            raise ValueError('Urban response clock/quadrature mismatch')
        if not isinstance(row.get('model_stock_veh'), dict):
            raise ValueError('Shared local costs require full physical stock operands')

    movement_owner = {}
    onramps = {}
    for signal, model in models.items():
        for ramp, movements in model.onramp_movements.items():
            for movement in movements:
                if movement in movement_owner:
                    raise ValueError('On-ramp movement has duplicate owners')
                movement_owner[movement] = signal
                onramps[movement] = ramp
    accepted = [{m: 0.0 for m in onramps} for _ in range(count)]
    for row in response['transfers']:
        source = row['source']
        if not isinstance(source, str) or not source.startswith('movement:'):
            continue
        movement = source[len('movement:'):]
        if movement not in onramps:
            continue
        offset = (float(row['start_sec']) - float(start_sec)) / dt_sec
        index = int(round(offset))
        if (row['stage'] != 'urban' or not 0 <= index < count or abs(index - offset) > 1e-8
                or row['end_sec'] != (start_step + index + 1) * dt_sec
                or row['target'] != 'ramp:' + onramps[movement]
                or row['route_key'] != 'movement:' + movement):
            raise ValueError('On-ramp accepted response has another clock or destination')
        amount = row['vehicles']
        if type(amount) not in (int, float) or not math.isfinite(amount) or amount < 0:
            raise ValueError('Invalid accepted on-ramp vehicle count')
        accepted[index][movement] += amount

    result = {}
    for signal, model in models.items():
        queue = [m for m in model.movements if not model.has_ramps or model.kind_of[m] != 'off_ramp']
        steps = []
        for index, sample in enumerate(samples):
            stocks = sample['model_stock_veh']
            # Exact indexing is intentional: absent required stock is not zero.
            row = {'service_step': start_step + index,
                   'stage': 'after_urban_service_before_fw_landing',
                   'queue_veh': {m: stocks['movement:' + m] for m in queue}}
            if model.has_ramps:
                row.update(offramp_stock_veh={r: stocks['storage:' + cfg.network.off_ramp_storage_link[r]]
                                            for r in model.offramp_movements},
                           ramp_stock_veh={r: stocks['ramp:' + r] for r in model.onramp_movements},
                           accepted_to_ramp_by_movement_veh={m: accepted[index][m]
                               for movements in model.onramp_movements.values() for m in movements})
            steps.append(row)
        result[signal] = steps
    return result


def score_shared_urban_point(follower, point, state, *, horizon_steps):
    """Consume a common response once; never run independent local dynamics."""
    from evaluation.controllers.local_signal_service import score_shared_urban_response
    response = getattr(point, 'control_area_response', None)
    if not isinstance(response, dict):
        raise ValueError('Fixed local evaluation requires a captured common endpoint')
    steps = shared_urban_cost_inputs(follower, response, start_sec=state.time_sec,
                                     horizon_steps=horizon_steps)
    frozen_congestion = follower._frozen_freeway_congestion(state)
    output = {}
    for signal, model in follower._local_models.items():
        kwargs = {}
        if model.has_ramps:
            kwargs = {'freeway_congestion': {r: frozen_congestion[r] for r in model.onramp_movements},
                      'ramp_metering_weight': follower.ramp_metering_weight}
        output[signal] = score_shared_urban_response(model, steps[signal],
            start_step=int(round(state.time_sec / follower.cfg.simulation.T_u_sec)),
            substeps=horizon_steps * int(follower.cfg.simulation.K_cu),
            dt_h=float(follower.cfg.simulation.T_u_h), **kwargs)
    return output


def score_shared_owner_point(follower, point, state, candidate, reference, *, horizon_steps):
    """Project one held coupled response onto all urban/FW local functionals.

    The joint FW game explicitly uses physical destination approach residence
    in place of the old frozen-boundary virtual rejected-demand queue. Prices
    must subtract this same functional. This does not dispatch a solver or
    certify resource limits merely because a finite local score is available.
    """
    from evaluation.controllers import link_predictor
    cfg = follower.cfg
    response = getattr(point, 'control_area_response', None)
    if not isinstance(response, dict) or response.get('schema') != 'control-area-fixed-response/v1':
        raise ValueError('Owner costs require the canonical captured response')
    initial = response['initial_freeway_operands']
    frames = response['freeway_frames']
    if len(frames) != horizon_steps * cfg.simulation.K_cf or not frames:
        raise ValueError('Shared freeway frames do not cover the held horizon')
    fields = ('N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times',
              'offsets', 'inflow_outflow_allocation')
    applied = {key: getattr(candidate, key) for key in fields}
    if initial['start_sec'] != state.time_sec or initial['applied_control'] != applied:
        raise ValueError('Shared response was initialized with another state time/control')
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger, MembershipError
    source_ledger = get_ledger(state)
    if source_ledger is None:
        raise ValueError('Shared response initial state has no source ledger')
    try:
        source_ledger.assert_stocks(model_inventory(state, cfg))
    except MembershipError as exc:
        raise ValueError('Shared response initial traffic operands differ from the supplied state') from exc
    if (initial['stock_cohorts'] != source_ledger.stocks
            or initial['model_stock_veh'] != {k: v['inside'] + v['outside'] for k, v in source_ledger.stocks.items()}
            or initial['freeway_density'] != state.freeway_density
            or initial['urban_movement_queue'] != state.urban_movement_queue
            or initial['shared_approach_state'] != getattr(state, 'shared_approach_state', None)
            or initial.get('offramp_route_inventory_state') != getattr(state, 'offramp_route_inventory_state', None)):
        raise ValueError('Shared response initial traffic operands differ from the supplied state')
    dt = cfg.simulation.T_f_sec
    for index, frame in enumerate(frames):
        if (frame['stage'] != 'landing' or frame['start_sec'] != state.time_sec + index * dt
                or frame['end_sec'] != state.time_sec + (index + 1) * dt
                or frame['applied_control'] != applied):
            raise ValueError('Shared response changed control or freeway clock')
    output = score_shared_urban_point(follower, point, state, horizon_steps=horizon_steps)
    for link in cfg.network.freeway_links:
        ramps = tuple(follower._local_freeway_models[link].owned_ramps)
        landing = link_predictor.shared_freeway_landing_links(follower, link)
        physical_approach = follower.count_blocked_ramp_inflow
        contract = link_predictor.shared_freeway_approach_source_contract(follower, link) if physical_approach else None

        def approach_sources(raw):
            movements = [m for values in contract['movements_by_ramp'].values() for m in values]
            storage = contract['shared_storage']
            return {'movement_queue_veh': {m: raw['urban_movement_queue'][m] for m in movements},
                    'shared_approach_bins': raw['shared_approach_state']['bins'] if storage else {},
                    'shared_approach_stock_veh': raw['model_stock_veh']['storage:' + storage] if storage else 0.}

        local = {'link': link, 'start_sec': state.time_sec,
                 'end_sec': state.time_sec + len(frames) * dt,
                 'sample_stage': 'post_freeway_landing', 'applied_control': applied,
                 'frames': [], 'final_density': frames[-1]['freeway_density'][link],
                 'initial_protected_queue_veh': dict(initial['urban_movement_queue']),
                 'final_ramp_release_veh_h': {r: frames[-1]['actual_ramp_release_veh_h'][r] for r in ramps}}
        protected = str(getattr(cfg.mpc, 'protected_queue_movement', '') or '')
        if (protected and float(getattr(cfg.mpc, 'protected_queue_weight', 0.)) > 0.
                and cfg.network.urban_movements[protected].get('ramp') in ramps):
            local['initial_protected_queue_veh'] = {protected: initial['urban_movement_queue'][protected]}
        if physical_approach:
            local.update(ramp_approach_queue_semantics=contract['semantics'],
                         ramp_approach_queue_lineage=contract,
                         initial_ramp_approach_sources=approach_sources(initial))
        for raw in frames:
            stocks = raw['model_stock_veh']
            frame = {'start_sec': raw['start_sec'], 'end_sec': raw['end_sec'],
                     'link_vehicles_veh': stocks['freeway:' + link],
                     'ramp_queue_veh': {r: stocks['ramp:' + r] for r in ramps},
                     'landing_stock_veh': {s: stocks['storage:' + s] for s in landing}}
            if physical_approach:
                frame['ramp_approach_sources'] = approach_sources(raw)
            else:
                frame['blocked_queue_veh'] = dict.fromkeys(ramps, 0.)
            local['frames'].append(frame)
        output[link] = link_predictor.score_shared_freeway_response(follower, link, local, candidate, reference)
    return output


def score_shared_priced_point(follower, point, state, candidate, reference, *, horizon_steps,
                              lambda_p, lambda_uf, target_np_veh, target_nuf_veh_h, price_context):
    """One fixed joint-response payoff used by every owner in the same round.

    Leader targets and duals are explicit frozen inputs, separate from the
    candidate's realized meter-rate sum. Resource certification and the outer
    price/dual update remain separate; no incomplete witness becomes gap zero.
    """
    from evaluation.controllers.area_leader_objective import shared_urban_quantities, fixed_joint_price_terms
    local = score_shared_owner_point(follower, point, state, candidate, reference,
                                     horizon_steps=horizon_steps)
    quantities = shared_urban_quantities(follower, point.control_area_response,
        start_sec=state.time_sec, horizon_steps=horizon_steps)
    additions = fixed_joint_price_terms(follower, candidate, quantities,
        lambda_p=lambda_p, lambda_uf=lambda_uf, target_np_veh=target_np_veh,
        target_nuf_veh_h=target_nuf_veh_h, price_context=price_context)
    if set(local) != set(additions['owners']):
        raise ValueError('Local and fixed-price owner catalogs differ')
    costs = {owner: local[owner]['cost'] + additions['owners'][owner]['total'] for owner in local}
    if any(not math.isfinite(value) for value in costs.values()):
        raise ValueError('Nonfinite shared owner payoff')
    return {'owner_costs': costs, 'local_costs': local, 'additive_terms': additions,
            'quantities': quantities, 'objective_veh_h': float(point.objective),
            'shared_capacity_certificate': False,
            'scope': 'Fixed-leader shared-response local+external+dual payoff; no solve or full feasibility certificate'}


def evaluate_shared_owner_batch(follower, state, reference, forecast, candidates, *, horizon_steps,
                                check_budget=None):
    """Evaluate exact full-action repeats once in a single private query batch.

    This is the common physical response used for local costs and matched
    external-cost probes. No optimizer, price refresh, COM, or cross-batch cache
    runs here. The full action is the cache key: physical aliases are NOT merged
    before their model/price equivalence has been proved. Only compact scored
    results are retained; large trajectories are released after each query.

    Follower/config, initial state, reference and demand are private copies.
    Adapter diagnostic accumulators are restored on success and failure. This
    does not certify arbitrary concurrent module-hook replacement or all shared
    capacities; runtime installation must finish before invoking this function.
    """
    import copy
    if type(horizon_steps) is not int or horizon_steps < 1:
        raise ValueError('Explicit positive held horizon required')
    if not enabled(follower.cfg):
        raise ValueError('Shared owner batch requires the Omega endpoint')
    private, initial, anchor, demand, actions = copy.deepcopy(
        (follower, state, reference, forecast, tuple(candidates)))
    return _evaluate_shared_owner_batch_owned(private, initial, anchor, demand,
        actions, horizon_steps=horizon_steps, **({'check_budget': check_budget} if check_budget is not None else {}))


def _evaluate_shared_owner_batch_owned(private, initial, anchor, demand, actions, *, horizon_steps,
                                       response_cache=None, check_budget=None, response_audit=None):
    """Internal batch body consuming exclusively owned, already-copied inputs.

    Public batch callers still deep-copy the whole input graph once. A fixed
    game owns its deep-copied context for the solve and copies only each action.
    All before/after exact-value and runtime restoration checks remain here.
    If this raises after a model mutation, the fixed-game caller must discard or
    restore its private context before any subsequent validation/query.
    """
    import copy
    import hashlib
    import pickle
    from collections import Counter
    from time import perf_counter, process_time
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers.area_leader_objective import shared_urban_quantities
    from src.controllers import rollout_endpoint

    if type(horizon_steps) is not int or horizon_steps < 1:
        raise ValueError('Explicit positive held horizon required')
    if not enabled(private.cfg):
        raise ValueError('Shared owner batch requires the Omega endpoint')
    if not actions:
        raise ValueError('A shared owner batch must contain candidates')
    # Pickle is a process-local exact-value key, not a portable content hash.
    def packed(value):
        if response_cache is None:
            return pickle.dumps(value, protocol=5)
        wall, cpu = perf_counter(), process_time()
        result = pickle.dumps(value, protocol=5)
        response_cache['record'](serialization_wall_sec=perf_counter()-wall,
                                 serialization_cpu_sec=process_time()-cpu)
        return result
    def unpacked(value):
        if response_cache is None:
            return pickle.loads(value)
        wall, cpu = perf_counter(), process_time()
        result = pickle.loads(value)
        response_cache['record'](serialization_wall_sec=perf_counter()-wall,
                                 serialization_cpu_sec=process_time()-cpu)
        return result
    frozen = packed((private, initial, anchor, demand))
    token = hashlib.sha256(frozen).hexdigest()
    if response_cache is not None:
        signature = packed((frozen, horizon_steps, response_cache['source_fingerprint'],
                            response_cache['runtime_token']))
        if response_cache['context'] is None:
            response_cache['context'] = signature
        elif response_cache['context'] != signature:
            raise ValueError('Decision response cache used with different frozen model inputs or horizon')
    diagnostics = {key: (value, copy.deepcopy(value)) for key, value in vars(adapter).items()
                   if key.endswith('_LAST') and isinstance(value, dict)}
    def restore_diagnostics():
        for name in tuple(vars(adapter)):
            value = getattr(adapter, name)
            if name.endswith('_LAST') and isinstance(value, dict) and name not in diagnostics:
                delattr(adapter, name)
        for name, (original, before) in diagnostics.items():
            original.clear()
            original.update(copy.deepcopy(before))
            setattr(adapter, name, original)
    cache = response_cache['values'] if response_cache is not None and response_cache['enabled'] else {}
    results = []
    endpoint_sec = score_sec = endpoint_cpu = score_cpu = 0.0
    endpoint_calls = cache_hits = 0
    saved_endpoint_sec = saved_score_sec = 0.0
    try:
        for action in actions:
            if check_budget is not None:
                check_budget('physical_response')
            key = packed(action)
            if key in cache:
                # Unpickle prevents aliases between separate returned requests.
                results.append(unpacked(cache[key]))
                cache_hits += 1
                if response_cache is not None:
                    prior = response_cache['timings'][key]
                    saved_endpoint_sec += prior[0]
                    saved_score_sec += prior[1]
                    response_cache['record'](cache_hits=1,
                        avoided_endpoint_sec_from_prior_queries=prior[0],
                        avoided_local_score_sec_from_prior_queries=prior[1])
                continue
            restore_diagnostics()
            tick = perf_counter()
            cpu_tick = process_time()
            if response_cache is not None:
                response_cache['record'](endpoint_attempts=1)
            with shared_response_gc_scope(getattr(private.cfg.network, 'control_area_defer_response_gc', False)) as gc_stats, shared_query_runtime_scope():
                point = rollout_endpoint.evaluate_price_point(initial, action, demand, (),
                    rollout_endpoint.ObjectiveSpec(private.cfg, depth_override=horizon_steps,
                        box_walk=False, score_mode='raw'), capture_response=True)
            this_endpoint = perf_counter() - tick
            endpoint_sec += this_endpoint
            this_endpoint_cpu = process_time() - cpu_tick
            endpoint_cpu += this_endpoint_cpu
            endpoint_calls += 1
            if response_cache is not None:
                response_cache['record'](endpoint_calls=1, endpoint_sec=this_endpoint,
                                         endpoint_cpu_sec=this_endpoint_cpu)
                if gc_stats['cyclic_gc_deferred_queries']:
                    response_cache['record'](**gc_stats)
            if point.aborted or len(point.states) != horizon_steps:
                raise ValueError('Incomplete shared endpoint is not cacheable')
            tick = perf_counter()
            cpu_tick = process_time()
            with shared_query_runtime_scope():
                local = score_shared_owner_point(private, point, initial, action, anchor,
                                                 horizon_steps=horizon_steps)
            response = point.control_area_response
            quantities = shared_urban_quantities(private, response,
                start_sec=initial.time_sec, horizon_steps=horizon_steps)
            if packed(action) != key or packed((private, initial, anchor, demand)) != frozen:
                raise ValueError('Shared query mutated its frozen operands')
            resources = response['resource_allocations']
            response_bytes = packed(response)
            if response_audit is not None:
                _save_shared_response_audit(response_bytes, hashlib.sha256(key).hexdigest(),
                    token, response_audit)
            value = {'objective_veh_h': float(point.objective),
                'local_base_costs': {owner: row['cost'] for owner, row in local.items()},
                'local_costs': local, 'quantities': quantities,
                'control_area': copy.deepcopy(point.control_area),
                'response_token': hashlib.sha256(response_bytes).hexdigest(),
                'action_token': hashlib.sha256(key).hexdigest(),
                'frozen_context_token': token,
                'price_or_quantity_terms_included': False,
                'shared_capacity_certificate': False,
                'model_constraint_coverage': copy.deepcopy(response.get('model_constraint_coverage')),
                'conditional_model_feasibility_witness': response.get('conditional_model_feasibility_witness', False),
                'native_prehead_reference_overdraw_veh': (
                    getattr(point.states[-1], 'native_input_prehead_state', {}).get('existing_wn_budget_overdraw_veh', 0.)
                    - getattr(initial, 'native_input_prehead_state', {}).get('existing_wn_budget_overdraw_veh', 0.)),
                'native_prehead_limit_scope': 'Existing W/N versus left-reference budget mismatch; upstream capacity and same-step crossing correspondence are unverified',
                'resource_summary': {'count': len(resources),
                    'kinds': dict(Counter(row['kind'] for row in resources)),
                    'max_exceedance_veh': max((row['exceedance_veh'] for row in resources), default=0.)}}
            cache[key] = packed(value)
            results.append(unpacked(cache[key]))
            this_score = perf_counter() - tick
            score_sec += this_score
            this_score_cpu = process_time() - cpu_tick
            score_cpu += this_score_cpu
            if response_cache is not None:
                response_cache['timings'][key] = (this_endpoint, this_score)
                response_cache['record'](local_score_sec=this_score, local_score_cpu_sec=this_score_cpu)
            del point, response
    finally:
        restore_diagnostics()
    result = {'results': results, 'requested': len(actions), 'endpoint_calls': endpoint_calls,
            'cache_hits': cache_hits,
            'retained_result_bytes': sum(len(key) + len(value) for key, value in cache.items()),
            'endpoint_sec': endpoint_sec, 'score_sec': score_sec,
            'scope': 'Exact full-action reuse within one private shared-response batch; no solver or full feasibility certificate'}
    if response_cache is not None:
        result.update(endpoint_cpu_sec=endpoint_cpu, local_score_cpu_sec=score_cpu,
            avoided_endpoint_sec_from_prior_queries=saved_endpoint_sec,
            avoided_local_score_sec_from_prior_queries=saved_score_sec,
            scope='Exact full-action compact response reuse in one decision-owned physical context; prices and duals excluded')
    return result


_SHARED_RESPONSE_WORKER = {}


def _save_shared_response_audit(response_bytes, action_token, context_token, audit):
    """Optional diagnostic: preserve the exact token input for at most2 actions."""
    import hashlib
    import json
    import os
    from pathlib import Path
    if action_token not in audit['action_tokens']:
        raise ValueError('Response audit encountered an undeclared action')
    target = Path(audit['directory']) / (action_token + '.pickle')
    # Exclusive creation preserves earlier failures and bounds diagnostic files.
    with target.open('xb') as stream:
        stream.write(response_bytes)
    with target.with_suffix('.json').open('x', encoding='utf-8') as stream:
        json.dump({'schema': 'shared-response-raw-audit/v1', 'pid': os.getpid(),
            'action_token': action_token, 'local_context_token': context_token,
            'response_token': hashlib.sha256(response_bytes).hexdigest(),
            'bytes': len(response_bytes)}, stream, indent=2)


def _shared_response_transport_token(owned_bytes, runtime_bytes, bootstrap_bytes, horizon, source):
    import hashlib
    import pickle
    return hashlib.sha256(pickle.dumps(
        (owned_bytes, runtime_bytes, bootstrap_bytes, horizon, source), protocol=5)).hexdigest()


def _initialize_shared_response_worker(owned_bytes, runtime_bytes, bootstrap_bytes,
                                       horizon, source, transport_token, deadline, response_audit=None):
    """Reinstall the existing model hooks once in an explicitly owned spawn."""
    import hashlib
    import os
    import pickle
    import sys
    from pathlib import Path
    from time import perf_counter, process_time
    wall, cpu = perf_counter(), process_time()
    if deadline is not None and wall >= deadline:
        raise TimeoutError('Decision deadline during shared worker startup')
    if _shared_response_transport_token(owned_bytes, runtime_bytes, bootstrap_bytes, horizon, source) != transport_token:
        raise ValueError('Shared worker transport digest mismatch')
    bootstrap = pickle.loads(bootstrap_bytes)
    for name, expected in bootstrap['runtime_sources'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
            raise ValueError('Shared worker source changed: ' + name)
    root = Path(__file__).resolve().parents[2]
    vendor = str(root / 'vendor/NumSim-mine')
    if vendor not in sys.path:
        sys.path.insert(0, vendor)
    owned = pickle.loads(owned_bytes)
    before = pickle.dumps(owned, protocol=5)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers.runtime_setup import install_worker_runtime
    metadata = install_worker_runtime(adapter, owned[0].cfg,
        bootstrap['state_json'], bootstrap['detector_mapping'])
    if pickle.dumps(owned, protocol=5) != before:
        raise ValueError('Shared worker bootstrap changed frozen model operands')
    if deadline is not None and perf_counter() >= deadline:
        raise TimeoutError('Decision deadline after shared worker bootstrap')
    _SHARED_RESPONSE_WORKER.clear()
    _SHARED_RESPONSE_WORKER.update(owned=owned, frozen=before, runtime_bytes=runtime_bytes,
        horizon=horizon, deadline=deadline, transport_token=transport_token,
        response_audit=response_audit,
        source_fingerprint=source, local_context_token=hashlib.sha256(before).hexdigest(),
        startup={'pid': os.getpid(), 'ready_monotonic': perf_counter(),
            'initializer_wall_sec': perf_counter()-wall, 'initializer_cpu_sec': process_time()-cpu,
            'source_files_checked': len(bootstrap['runtime_sources']),
            'bootstrap_metadata': metadata})


def _evaluate_shared_response_worker(task):
    """Evaluate an exact transported full action using the canonical batch body."""
    import hashlib
    import pickle
    from time import perf_counter, process_time
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    index, action_bytes = task
    ctx = _SHARED_RESPONSE_WORKER
    def check(stage):
        if ctx['deadline'] is not None and perf_counter() >= ctx['deadline']:
            raise TimeoutError('Decision deadline in shared worker: ' + stage)
    check('task_start')
    if pickle.dumps(ctx['owned'], protocol=5) != ctx['frozen']:
        raise ValueError('Shared worker reused mutated model operands')
    action = pickle.loads(action_bytes)
    action_token = hashlib.sha256(action_bytes).hexdigest()
    if hashlib.sha256(pickle.dumps(action, protocol=5)).hexdigest() != action_token:
        raise ValueError('Shared action changed while crossing the spawn boundary')
    tick, cpu = perf_counter(), process_time()
    query_counts = {}
    def record(**values):
        for name, value in values.items():
            query_counts[name] = query_counts.get(name, 0.) + value
    response_cache = {'enabled': False, 'source_fingerprint': ctx['source_fingerprint'],
        'runtime_token': hashlib.sha256(ctx['runtime_bytes']).hexdigest(), 'context': None,
        'values': {}, 'timings': {}, 'record': record}
    with shared_query_runtime_scope():
        runtime = pickle.loads(ctx['runtime_bytes'])
        runtime['_PHASE_VECTOR_FOLLOWER']['ref'] = ctx['owned'][0]
        for name in tuple(vars(adapter)):
            value = getattr(adapter, name)
            if (name.startswith('_') and name.isupper() and isinstance(value, (dict, list, set))
                    and name not in runtime):
                delattr(adapter, name)
        for name, value in runtime.items():
            setattr(adapter, name, value)
        batch = _evaluate_shared_owner_batch_owned(*ctx['owned'], (action,),
            horizon_steps=ctx['horizon'], check_budget=check, response_cache=response_cache,
            **({'response_audit': ctx['response_audit']} if ctx.get('response_audit') is not None else {}))
    check('task_complete')
    after = pickle.dumps(ctx['owned'], protocol=5)
    if after != ctx['frozen']:
        raise ValueError('Shared worker query changed frozen model operands')
    value = batch['results'][0]
    if (batch['requested'] != 1 or batch['endpoint_calls'] != 1
            or value['action_token'] != action_token
            or value['frozen_context_token'] != ctx['local_context_token']):
        raise ValueError('Shared worker returned an unbound or incomplete result')
    return {'index': index, 'result': value, 'transport_token': ctx['transport_token'],
        'source_fingerprint': ctx['source_fingerprint'],
        'local_context_before': ctx['local_context_token'],
        'local_context_after': hashlib.sha256(after).hexdigest(),
        'action_token': action_token, 'startup': ctx['startup'],
        'task_wall_sec': perf_counter()-tick, 'task_cpu_sec': process_time()-cpu,
        'endpoint_sec': batch['endpoint_sec'], 'score_sec': batch['score_sec'],
        'endpoint_cpu_sec': batch['endpoint_cpu_sec'],
        'local_score_cpu_sec': batch['local_score_cpu_sec'], 'query_counts': query_counts}


def make_decision_shared_query(follower, state, reference, forecast, *, horizon_steps,
                               source_fingerprint, cache_enabled=True, check_budget=None,
                               parallel_workers=0, worker_bootstrap=None, deadline_monotonic=None,
                               response_audit=None, unlimited_time=False):
    """Own one immutable physical/local-cost context until this decision ends.

    This extends the existing compact batch cache; it does not retain captured
    trajectories or final price/dual scores. Full action payloads remain exact
    keys, including NP/NUF and diagnostics. No physical alias is assumed. Each
    invocation returns independent values and restores runtime/caller data.
    OFF uses the same owned endpoint path for an algorithm-preserving A/B.
    """
    import copy
    import hashlib
    import pickle
    from time import perf_counter, process_time
    from evaluation.controllers import vissim_stackelberg_adapter as adapter

    if (type(unlimited_time) is not bool or (unlimited_time and deadline_monotonic is not None)):
        raise ValueError('Explicit unlimited time requires no deadline')
    if (type(horizon_steps) is not int or horizon_steps < 1
            or type(cache_enabled) is not bool or not isinstance(source_fingerprint, str)
            or not source_fingerprint or type(parallel_workers) is not int
            or parallel_workers not in (0, 1, 2, 3, 4, 8)):
        raise ValueError('Explicit decision response horizon, source fingerprint and boolean cache switch required')
    if response_audit is not None:
        from pathlib import Path
        if (type(response_audit) is not dict or set(response_audit) != {'directory', 'action_tokens'}
                or type(response_audit['directory']) is not str
                or not Path(response_audit['directory']).is_absolute()
                or not Path(response_audit['directory']).is_dir()
                or type(response_audit['action_tokens']) is not tuple
                or not 1 <= len(response_audit['action_tokens']) <= 2
                or len(set(response_audit['action_tokens'])) != len(response_audit['action_tokens'])
                or any(type(x) is not str or len(x) != 64 or any(c not in '0123456789abcdef' for c in x)
                       for x in response_audit['action_tokens'])):
            raise ValueError('Response audit requires an existing absolute directory and1–2 exact action SHA256s')
        response_audit = copy.deepcopy(response_audit)
    if parallel_workers:
        from pathlib import Path
        if not unlimited_time and (type(deadline_monotonic) not in (float, int) or not math.isfinite(deadline_monotonic)
                or deadline_monotonic <= perf_counter()):
            raise ValueError('Spawn response queries require a future whole-decision deadline')
        if (type(worker_bootstrap) is not dict
                or set(worker_bootstrap) != {'state_json', 'detector_mapping', 'runtime_sources'}
                or type(worker_bootstrap['state_json']) is not dict
                or set(worker_bootstrap['state_json']) != {'network_path'}
                or type(worker_bootstrap['state_json']['network_path']) is not str
                or not Path(worker_bootstrap['state_json']['network_path']).is_absolute()
                or not Path(worker_bootstrap['state_json']['network_path']).is_file()
                or type(worker_bootstrap['detector_mapping']) is not dict
                or type(worker_bootstrap['runtime_sources']) is not dict
                or not worker_bootstrap['runtime_sources']):
            raise ValueError('Shared worker requires the existing bootstrap and exact runtime source pins')
        for path, token in worker_bootstrap['runtime_sources'].items():
            if (type(path) is not str or not Path(path).is_absolute()
                    or type(token) is not str or len(token) != 64
                    or any(c not in '0123456789abcdef' for c in token)):
                raise ValueError('Shared worker source pins require absolute paths and SHA256 values')
    started, cpu_started = perf_counter(), process_time()
    if check_budget is not None:
        check_budget('response_context_copy')
    copy_started, copy_cpu_started = perf_counter(), process_time()
    owned = copy.deepcopy((follower, state, reference, forecast))
    private = owned[0]
    # Operational adapter data can affect physics. Freeze it together with the
    # source pins and bind the copied follower while each query runs. Prices
    # subsequently installed in another follower never alter this namespace.
    memo = {id(follower): private}
    bound = getattr(adapter, '_PHASE_VECTOR_FOLLOWER', {}).get('ref')
    if bound is not None:
        memo[id(bound)] = private
    runtime = copy.deepcopy({k: v for k, v in vars(adapter).items()
        if k.startswith('_') and k.isupper() and isinstance(v, (dict, list, set))}, memo)
    # The copied follower is already owned separately. Do not serialize it
    # again inside every operational runtime restore.
    runtime.setdefault('_PHASE_VECTOR_FOLLOWER', {})['ref'] = None
    preparation_copy_sec = perf_counter()-copy_started
    preparation_copy_cpu = process_time()-copy_cpu_started
    serialization_started, serialization_cpu_started = perf_counter(), process_time()
    packed_owned = pickle.dumps(owned, protocol=5)
    runtime_bytes = pickle.dumps(runtime, protocol=5)
    preparation_serialization_sec = perf_counter()-serialization_started
    preparation_serialization_cpu = process_time()-serialization_cpu_started
    cache = {'enabled': cache_enabled, 'source_fingerprint': source_fingerprint,
        'runtime_token': hashlib.sha256(runtime_bytes).hexdigest(), 'context': None,
        'values': {}, 'timings': {}}
    counters = {'schema': 'decision-shared-response-cache/v1', 'cache_enabled': cache_enabled,
        'requests': 0, 'endpoint_attempts': 0, 'endpoint_calls': 0, 'cache_hits': 0, 'batches': 0, 'failures': 0,
        'endpoint_sec': 0., 'local_score_sec': 0., 'endpoint_cpu_sec': 0., 'local_score_cpu_sec': 0.,
        'query_wall_sec': 0., 'query_cpu_sec': 0.,
        'serialization_wall_sec': 0., 'serialization_cpu_sec': 0.,
        'avoided_endpoint_sec_from_prior_queries': 0., 'avoided_local_score_sec_from_prior_queries': 0.,
        'preparation_wall_sec': perf_counter()-started, 'preparation_cpu_sec': process_time()-cpu_started,
        'preparation_copy_wall_sec': preparation_copy_sec, 'preparation_copy_cpu_sec': preparation_copy_cpu,
        'preparation_serialization_wall_sec': preparation_serialization_sec,
        'preparation_serialization_cpu_sec': preparation_serialization_cpu,
        'source_fingerprint': source_fingerprint, 'horizon_steps': horizon_steps,
        'frozen_operand_bytes': len(packed_owned), 'frozen_runtime_bytes': len(runtime_bytes),
        'timing_scope': 'Endpoint/local scoring and serialization are nested within query wall/CPU; serialization may also nest within local scoring. Preparation copy/serialization nest within preparation. Avoided time is prior-query measured work, not measured total speedup'}
    def record(**values):
        for key, value in values.items():
            counters[key] = counters.get(key, 0.) + value
    cache['record'] = record
    executor = None
    closed = False
    worker_processes = {}
    worker_proofs = {}
    bootstrap_bytes = pickle.dumps(worker_bootstrap, protocol=5) if parallel_workers else None
    transport_token = (_shared_response_transport_token(packed_owned, runtime_bytes,
        bootstrap_bytes, horizon_steps, source_fingerprint) if parallel_workers else None)
    parent_context_token = hashlib.sha256(packed_owned).hexdigest()
    counters.update(parallel_workers=parallel_workers, parallel_submitted=0,
        parallel_completed=0, parallel_accepted=0, worker_task_wall_sec_sum=0.,
        worker_task_cpu_sec_sum=0., parallel_submit_wall_sec=0., parallel_wait_wall_sec=0.,
        parallel_failed_tasks_with_unknown_endpoint_count=0,
        worker_cleanup_wall_sec=0., pool_started_monotonic=None,
        parallel_transport_token=transport_token, deadline_stage=None)

    def remaining(stage):
        if check_budget is not None:
            try:
                check_budget(stage)
            except BaseException:
                counters['deadline_stage'] = stage
                raise
        if unlimited_time:
            return None  # concurrent.futures.wait: no wall deadline
        left = deadline_monotonic-perf_counter()
        if left <= 0:
            counters['deadline_stage'] = stage
            raise TimeoutError('Whole decision deadline: ' + stage)
        return left

    def remember_workers():
        if executor is not None:
            worker_processes.update(getattr(executor, '_processes', None) or {})

    def close():
        nonlocal executor, closed
        if closed:
            return
        closed = True
        tick = perf_counter()
        remember_workers()
        pool, executor = executor, None
        if pool is not None:
            # Python3.12 has no terminate_workers. These are only this pool's
            # Process handles; no process-name scan or unrelated tree cleanup.
            pool.shutdown(wait=False, cancel_futures=True)
            for process in worker_processes.values():
                if process.is_alive():
                    process.terminate()
            for process in worker_processes.values():
                process.join(timeout=.25)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=.25)
        counters['worker_cleanup_wall_sec'] += perf_counter()-tick
        if any(p.is_alive() for p in worker_processes.values()):
            raise RuntimeError('Owned shared response worker survived bounded cleanup')

    def parallel_query(actions):
        nonlocal executor
        from concurrent.futures import FIRST_COMPLETED, wait
        from concurrent.futures import ProcessPoolExecutor
        import multiprocessing
        if not actions:
            raise ValueError('A shared owner batch must contain candidates')
        remaining('parallel_response_prepare')
        signature = pickle.dumps((packed_owned, horizon_steps, source_fingerprint,
                                  cache['runtime_token']), protocol=5)
        if cache['context'] is None:
            cache['context'] = signature
        elif cache['context'] != signature:
            raise ValueError('Parallel response reused a different frozen context')
        values = cache['values'] if cache_enabled else {}
        keys = [pickle.dumps(a, protocol=5) for a in actions]
        misses = list(dict.fromkeys(key for key in keys if key not in values))
        original_hits = len(keys)-len(misses)
        if misses and executor is None:
            counters['pool_started_monotonic'] = perf_counter()
            executor = ProcessPoolExecutor(max_workers=parallel_workers,
                mp_context=multiprocessing.get_context('spawn'),
                initializer=_initialize_shared_response_worker,
                initargs=(packed_owned, runtime_bytes, bootstrap_bytes, horizon_steps,
                    source_fingerprint, transport_token, None if unlimited_time else float(deadline_monotonic), response_audit))
        futures = {}
        tick = perf_counter()
        for index, key in enumerate(misses):
            remaining('parallel_response_submit')
            future = executor.submit(_evaluate_shared_response_worker, (index, key))
            futures[future] = (index, key)
            counters['parallel_submitted'] += 1
            remember_workers()
        counters['parallel_submit_wall_sec'] += perf_counter()-tick
        endpoint_sec = score_sec = 0.
        while futures:
            tick = perf_counter()
            ready, _ = wait(futures, timeout=remaining('parallel_response_wait'),
                            return_when=FIRST_COMPLETED)
            counters['parallel_wait_wall_sec'] += perf_counter()-tick
            if not ready:
                counters['deadline_stage'] = 'parallel_response_wait'
                raise TimeoutError('Whole decision deadline: parallel_response_wait')
            for future in ready:
                index, key = futures.pop(future)
                counters['parallel_completed'] += 1
                try:
                    envelope = future.result()
                except BaseException:
                    counters['parallel_failed_tasks_with_unknown_endpoint_count'] += 1
                    raise
                value = envelope['result']
                local_token = envelope['local_context_before']
                if (envelope['index'] != index or envelope['transport_token'] != transport_token
                        or envelope['source_fingerprint'] != source_fingerprint
                        or envelope['local_context_after'] != local_token
                        or value['frozen_context_token'] != local_token
                        or envelope['action_token'] != hashlib.sha256(key).hexdigest()
                        or value['action_token'] != envelope['action_token']):
                    raise ValueError('Shared worker response failed transport/local context/action proof')
                # A transported identical byte graph has an explicit common
                # identity; local re-pickle identity is independently proved.
                # Keep that evidence outside the unchanged compact result.
                pid = envelope['startup']['pid']
                if pid not in worker_processes:
                    raise ValueError('Shared response came from an unowned worker PID')
                worker_proofs[pid] = {**envelope['startup'],
                    'transport_token': transport_token, 'local_context_token': local_token,
                    'parent_context_token': parent_context_token}
                value['frozen_context_token'] = parent_context_token
                values[key] = pickle.dumps(value, protocol=5)
                cache['timings'][key] = (envelope['endpoint_sec'], envelope['score_sec'])
                endpoint_sec += envelope['endpoint_sec']
                score_sec += envelope['score_sec']
                counters['worker_task_wall_sec_sum'] += envelope['task_wall_sec']
                counters['worker_task_cpu_sec_sum'] += envelope['task_cpu_sec']
                counters['endpoint_cpu_sec'] += envelope['endpoint_cpu_sec']
                counters['local_score_cpu_sec'] += envelope['local_score_cpu_sec']
                counters['endpoint_attempts'] += int(envelope['query_counts']['endpoint_attempts'])
                for counter, amount in envelope['query_counts'].items():
                    if counter.startswith('cyclic_gc_'):
                        counters[counter] = counters.get(counter, 0.) + amount
                counters['parallel_accepted'] += 1
                counters['endpoint_calls'] += 1
        # Restore the original query order and independent returned instances.
        results = [pickle.loads(values[key]) for key in keys]
        counters['cache_hits'] += original_hits
        hit_keys = set(misses)
        saved_endpoint = saved_score = 0.
        for key in keys:
            if key in hit_keys:
                hit_keys.remove(key)
            else:
                previous_time = cache['timings'][key]
                saved_endpoint += previous_time[0]
                saved_score += previous_time[1]
        counters['avoided_endpoint_sec_from_prior_queries'] += saved_endpoint
        counters['avoided_local_score_sec_from_prior_queries'] += saved_score
        counters['endpoint_sec'] += endpoint_sec
        counters['local_score_sec'] += score_sec
        return {'results': results, 'requested': len(actions), 'endpoint_calls': len(misses),
            'cache_hits': original_hits,
            'retained_result_bytes': sum(len(k)+len(v) for k, v in values.items()),
            'endpoint_sec': endpoint_sec, 'score_sec': score_sec,
            'scope': 'Decision-owned spawned copies of the canonical shared response; original action order retained'}

    def query(actions):
        nonlocal owned
        tick, cpu_tick = perf_counter(), process_time()
        counters['batches'] += 1
        actions = tuple(actions)
        counters['requests'] += len(actions)
        try:
            if closed:
                raise RuntimeError('Decision shared response query is closed')
            if check_budget is not None:
                check_budget('response_query')
            if parallel_workers:
                return parallel_query(actions)
            with shared_query_runtime_scope():
                # Rebind every frozen operational value, not only price holders.
                # The outer scope restores the caller's original object identities.
                restored_runtime = pickle.loads(runtime_bytes)
                restored_runtime['_PHASE_VECTOR_FOLLOWER']['ref'] = owned[0]
                for name, value in restored_runtime.items():
                    setattr(adapter, name, value)
                result = _evaluate_shared_owner_batch_owned(*owned, copy.deepcopy(actions),
                    horizon_steps=horizon_steps, response_cache=cache, check_budget=check_budget,
                    **({'response_audit': response_audit} if response_audit is not None else {}))
            return result
        except BaseException:
            counters['failures'] += 1
            owned = pickle.loads(packed_owned)
            if parallel_workers:
                close()
            raise
        finally:
            counters['query_wall_sec'] += perf_counter()-tick
            counters['query_cpu_sec'] += process_time()-cpu_tick

    def stats():
        result = dict(counters)
        result['retained_result_bytes'] = sum(len(k)+len(v) for k, v in cache['values'].items())
        result['retained_timing_entries'] = len(cache['timings'])
        result['context_token'] = (hashlib.sha256(cache['context']).hexdigest()
                                   if cache['context'] is not None else None)
        result['hit_rate'] = counters['cache_hits']/max(1, counters['requests'])
        result['worker_proofs'] = copy.deepcopy(worker_proofs)
        result['owned_worker_pids'] = list(worker_processes)
        result['owned_workers_alive'] = [pid for pid, p in worker_processes.items() if p.is_alive()]
        result['closed'] = closed
        if parallel_workers:
            result['parallel_timing_scope'] = ('Parent query wall/CPU are local; endpoint/local-score '
                'CPU and wall are sums of completed worker tasks, not elapsed parallel wall. '
                'Submitted, completed, accepted and unknown failed endpoint counts remain separate.')
        return result
    query.stats = stats
    query.close = close
    return query


def prepare_joint_leader_candidates(controller, state, forecast, previous, *,
                                    budget_tolerance_veh_h, check_budget=None):
    """Build a declared realized leader domain before any objective query.

    Preserve every NP value from the installed leader proposal generator. Pair
    them with every distinct canonical meter schedule reachable from its NUF
    request domains and representable by the unchanged directional shares.
    Quantization creates a NEW, explicit finite leader domain: this is neither
    a nearest-budget initializer nor an after-score replacement of a target.
    Equal NUF with different NP caps or different physical schedules survives.
    Shared traffic feasibility and objective ranking remain later obligations.
    """
    import copy
    import pickle
    from evaluation.controllers import area_meter_finalization as meters
    from evaluation.controllers.joint_owner_neighbors import _current_meter_points

    cfg, follower = controller.cfg, controller.nash_solver
    if (not enabled(cfg) or cfg.mpc.leader_budget_off
            or cfg.mpc.wu_faithful_np_coordination_mode != 'cap'
            or cfg.mpc.wu_faithful_nuf_coordination_mode != 'equality'):
        raise ValueError('Joint leader preparation requires active NP cap and NUF equality')
    tolerance = budget_tolerance_veh_h
    if type(tolerance) not in (int, float) or not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError('Explicit finite nonnegative meter budget tolerance required')
    if not forecast:
        raise ValueError('Joint leader preparation requires the observed demand forecast')
    from evaluation.controllers import physical_ramp_branches
    if physical_ramp_branches.enabled(cfg):
        return physical_ramp_branches.leader_seed_domain(controller, state, forecast, previous,
            check_budget=check_budget)
    original_inputs = (controller.leader, cfg, follower, state, forecast, previous)
    before = pickle.dumps(original_inputs, protocol=5)
    private_leader, follower, state, forecast, previous = copy.deepcopy(
        (controller.leader, follower, state, forecast, previous))
    cfg = follower.cfg
    historical_rates = meters.historical_meter_anchor_rates(previous)
    meter_box_previous = copy.deepcopy(previous)
    meter_box_previous.ramp_metering = dict(historical_rates)
    current_request = copy.deepcopy(previous)
    current_request.diagnostics.pop(meters.HISTORICAL_REFERENCE, None)
    with shared_query_runtime_scope():
        raw = tuple(private_leader.candidates(state.copy(), previous.copy(), forecast=forecast))
        preview = meters.prepare_canonical_candidate(current_request, cfg,
            owned_ramps=tuple(cfg.network.ramps), total_budget=None,
            directional_budgets={}, budget_tolerance_veh_h=tolerance)
    if not raw:
        raise ValueError('Installed leader returned no proposals')
    np_values = tuple(dict.fromkeys(float(action.N_P_star) for action in raw))
    targets = tuple(dict.fromkeys(float(action.N_UF_star) for action in raw))
    # NP is a signed net-inflow cap [veh]; a negative cap requests draining.
    # NUF remains a nonnegative finalized meter-rate budget [veh/h].
    if (any(not math.isfinite(value) for value in np_values)
            or any(not math.isfinite(value) or value < 0 for value in targets)):
        raise ValueError('Leader proposals contain invalid vehicle quantities')
    owners = tuple(cfg.network.freeway_links)
    shares = {owner: float(follower._wu._omega_f[owner]) for owner in owners}
    if (len(owners) != 2 or any(not math.isfinite(v) or v < 0 for v in shares.values())
            or abs(math.fsum(shares.values()) - 1.) > 1e-12):
        raise ValueError('Joint leader requires the installed two-direction unit shares')
    requests, provenance = {}, {}
    for owner in owners:
        points, seen, sources = [], set(), []
        for index, target in enumerate(targets):
            if check_budget is not None: check_budget('leader_meter_request')
            request = preview.copy()
            request.N_UF_star = target
            with shared_query_runtime_scope():
                current, mode, budget, source = _current_meter_points(
                    follower, owner, preview, request, meter_box_previous)
            sources.append({'index': index, 'raw_target_nuf_veh_h': target,
                'budget_mode': mode, 'direction_budget_veh_h': budget, 'source': source})
            for label, pair in current:
                key = tuple(sorted(pair.items()))
                if key not in seen:
                    seen.add(key)
                    points.append((f'leader{index}:{label}', pair))
        requests[owner] = tuple(points)
        provenance[owner] = {'queries': sources,
            'previous_box_source': 'Verified historical final-writeback rates',
            'candidate_leader_source': 'Installed Leader.candidates before scoring'}
    with shared_query_runtime_scope():
        bank = meters.reachable_meter_budgets(preview, cfg,
            directional_requests=requests, source_provenance=provenance,
            budget_tolerance_veh_h=tolerance, check_budget=check_budget)
    candidates, incompatible = [], []
    for index, candidate in enumerate(bank['candidates']):
        target = candidate['total_budget_veh_h']
        directional = candidate['directional_budgets_veh_h']
        if any(abs(directional[owner] - shares[owner] * target) > tolerance for owner in owners):
            incompatible.append(index)
            continue
        budgets = {owner: {'mode': 'equality', 'veh_h': directional[owner]} for owner in owners}
        for np_value in np_values:
            if check_budget is not None: check_budget('leader_candidate_realization')
            control = candidate['control'].copy()
            control.N_P_star = np_value
            with shared_query_runtime_scope():
                control = meters.prepare_canonical_candidate(control, cfg,
                    owned_ramps=tuple(cfg.network.ramps), total_budget={'mode': 'equality', 'veh_h': target},
                    directional_budgets=budgets, budget_tolerance_veh_h=tolerance)
            candidates.append({'control': control, 'target_np_veh': np_value,
                'target_nuf_veh_h': target, 'directional_budgets': copy.deepcopy(budgets),
                'meter_bank_index': index, 'physical_meter_rows': copy.deepcopy(candidate['physical_rows'])})
    if pickle.dumps(original_inputs, protocol=5) != before:
        raise ValueError('Joint leader preparation mutated its original decision inputs')
    if not candidates:
        raise ValueError('No reachable canonical meter budget preserves the installed directional shares')
    return {'schema': 'joint-leader-realized-domain/v1', 'candidates': candidates,
        'raw_leader_proposals': [{'N_P_star': float(a.N_P_star), 'N_UF_star': float(a.N_UF_star)} for a in raw],
        'np_values': np_values, 'raw_nuf_requests': targets, 'directional_shares': shares,
        'incompatible_meter_bank_indices': incompatible,
        'meter_bank': bank, 'candidate_count': len(candidates),
        'objective_queries': 0, 'leader_target_selected': False,
        'scope': 'All installed NP values crossed with reachable fixed-share physical meter schedules; new finite pre-score domain, not an optimum or shared traffic-feasibility certificate'}


class DecisionDeadline(TimeoutError):
    """Cooperative whole-decision deadline; never a feasibility certificate."""


class DecisionBudget:
    """Small wall/CPU recorder. Inclusive scopes must not be added together."""
    def __init__(self, seconds, *, reserve_sec=10., started=None, cpu_started=None, unlimited_time=False):
        import time
        if type(unlimited_time) is not bool or not math.isfinite(seconds) or not 0 <= reserve_sec < seconds:
            raise ValueError('Positive decision budget and smaller finalization reserve required')
        self.started = time.perf_counter() if started is None else started
        self.cpu_started = time.process_time() if cpu_started is None else cpu_started
        self.seconds, self.reserve_sec = float(seconds), float(reserve_sec)
        self.unlimited_time = unlimited_time
        self.scopes, self.expired_stage = {}, None

    def remaining(self, *, final=False):
        import time
        if self.unlimited_time:
            return math.inf
        return max(0., self.started + self.seconds - (0. if final else self.reserve_sec) - time.perf_counter())

    def check(self, stage, *, final=False):
        if self.remaining(final=final) <= 0:
            self.expired_stage = stage
            raise DecisionDeadline('Whole decision ' + ('finalization' if final else 'search') + ' deadline at ' + stage)

    def scope(self, name):
        from contextlib import contextmanager
        import time
        @contextmanager
        def measured():
            wall, cpu = time.perf_counter(), time.process_time()
            try:
                yield
            finally:
                row = self.scopes.setdefault(name, {'calls': 0, 'wall_sec': 0., 'cpu_sec': 0.})
                row['calls'] += 1
                row['wall_sec'] += time.perf_counter() - wall
                row['cpu_sec'] += time.process_time() - cpu
        return measured()

    def report(self):
        import time
        elapsed = time.perf_counter() - self.started
        result = {'budget_sec': self.seconds, 'finalization_reserve_sec': self.reserve_sec,
                'wall_sec': elapsed, 'cpu_sec': time.process_time() - self.cpu_started,
                'overrun_sec': max(0., elapsed-self.seconds), 'expired_stage': self.expired_stage,
                'inclusive_scopes': self.scopes,
                'scope_rule': 'Inclusive nested scopes; do not sum. Deadline checked between callbacks; an in-flight callback can overrun.'}
        if self.unlimited_time:
            result.update(budget_sec=None, finalization_reserve_sec=None, overrun_sec=None,
                          unlimited_time=True, configured_inactive_budget_sec=self.seconds,
                          scope_rule='Wall limits explicitly disabled; elapsed wall/CPU still measured; finite work limits and all validation remain active.')
        return result


def joint_decision_move_limits(follower):
    """Existing per-step bounds, applied to all phases at the actual anchor."""
    cfg, trust = follower.cfg, follower.offset_marginal_price_trust_sec
    from evaluation.controllers import physical_ramp_branches
    return {'green_sec': 6., 'vsl_kmh': float(cfg.freeway_follower.max_vsl_step),
            **({'meter_green_sec':cfg.network.physical_ramp_branches['max_green_change_sec']}
               if physical_ramp_branches.enabled(cfg) else {'meter_veh_h':300.}),
            'offset_sec': {owner: min(float(trust), cfg.network.signal_cycle_length(owner)/2)
                           if trust is not None else cfg.network.signal_cycle_length(owner)/2
                           for owner in cfg.network.signals}}


class FrozenJointContextError(ValueError):
    """Keep the actual two pickle streams when a strict context check fails."""
    def __init__(self, before, after):
        super().__init__('Frozen joint query context changed')
        self.before, self.after = before, after

    def write_evidence(self, report_path):
        import hashlib
        from pathlib import Path
        evidence = {}
        for name, payload in (('before', self.before), ('after', self.after)):
            path = Path(report_path).with_suffix('.frozen_' + name + '.pickle')
            with path.open('xb') as stream:
                stream.write(payload)
            evidence[name] = {'path': str(path.resolve()), 'bytes': len(payload),
                              'sha256': hashlib.sha256(payload).hexdigest()}
        return evidence


def joint_context_fingerprint(adapter):
    """Same full SHA check, with failure-only evidence and no extra pickling."""
    import hashlib
    import pickle
    initial = None
    initial_token = None
    def fingerprint(value):
        nonlocal initial, initial_token
        runtime = {k: v for k, v in vars(adapter).items()
                   if k.startswith('_') and k.isupper() and isinstance(v, (dict, list, set))}
        payload = pickle.dumps((value, runtime), protocol=5)
        token = hashlib.sha256(payload).hexdigest()
        if initial is None:
            initial, initial_token = payload, token
        elif token != initial_token:
            raise FrozenJointContextError(initial, payload)
        return token
    return fingerprint


def _joint_runtime_callbacks(follower, state, forecast, historical, leader, mapping, sources, *,
                             reference, total_budget, directional, tolerance, budget=None,
                             price_probe=False, progress=None):
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers import area_meter_finalization as meters
    from evaluation.controllers.joint_owner_neighbors import make_joint_neighbor_callbacks, interleave_realized_neighbors
    from src.models.state import segment_vsl
    cfg = follower.cfg
    with shared_query_runtime_scope():
        coupling = follower._wu._coupling(state.copy(), reference.copy(), forecast[0])
    plan = {'controllers': {signal[2:]: node for signal, node in cfg.network.signal_actuation_contract['nodes'].items()}}
    actuation = cfg.network.control_area_meter_context['actuation']
    context = {'follower': follower, 'state': state, 'forecast': forecast, 'previous': historical,
        'reference': reference, 'leader': leader, 'coupling': coupling, 'mapping': mapping,
        'selected_plan': plan, 'actuation': actuation, 'runtime_sources': sources,
        'total_budget': total_budget, 'directional_budgets': directional,
        'decision_anchor': historical, 'move_limits': joint_decision_move_limits(follower)}
    fingerprint = joint_context_fingerprint(adapter)
    callbacks = make_joint_neighbor_callbacks(follower, state, coupling, forecast[0], leader,
        historical, mapping, plan, actuation, {'controller_variant': 'wu-link'},
        segment_vsl_func=segment_vsl, context=context, context_fingerprint=fingerprint,
        query_scope=shared_query_runtime_scope,
        held_horizon_sec=cfg.mpc.horizon_steps * cfg.simulation.T_c_sec,
        budget_tolerance_veh_h=tolerance, total_budget=total_budget, directional_budgets=directional,
        previous_meter_anchor=(None if hasattr(cfg.network,'physical_ramp_branches') else historical.diagnostics[meters.HISTORICAL_REFERENCE]),
        freeway_joint_pairs=lambda owner, domain: tuple((head, value, label)
            for head, values in domain.head_values.items() for value in values
            for label, _ in domain.meter_points),
        decision_anchor=historical, move_limits=context['move_limits'],
        deadline_check=budget.check if budget else None, price_probe=price_probe,
        defer_unvisited_command_checks=getattr(cfg.network, 'control_area_defer_unvisited_command_checks', False))
    original = callbacks['neighbors']
    def observed(owner, action, supplied):
        if budget:
            budget.check('price_candidates' if price_probe else 'follower_candidates')
        domain = original(owner, action, supplied)
        if not price_probe:
            domain = interleave_realized_neighbors(callbacks['ownership'], owner, action, domain)
        if progress:
            progress({'stage': 'joint_neighbors', 'owner': owner, 'candidates': len(domain.candidates),
                      'complete': domain.complete, 'price_probe': price_probe})
        return domain
    callbacks['neighbors'] = observed
    return callbacks, context, fingerprint


def initialize_decision_nuf(follower, state, reference, item):
    """Set only this decision's target from the actual-command merge forecast.

    The returned action must be queried in its own right: changing a target
    never licenses relabelling a cached full-action response/token.
    """
    import copy
    import hashlib
    import pickle
    from evaluation.controllers.physical_ramp_branches import checked_merge_rates
    token = hashlib.sha256(pickle.dumps(reference, protocol=5)).hexdigest()
    if item.get('action_token') != token:
        raise ValueError('NUF initialization needs the exact actual-reference response')
    end = state.time_sec + follower.cfg.mpc.horizon_steps * follower.cfg.simulation.T_c_sec
    rates, _ = checked_merge_rates(item['quantities']['predicted_ramp_merge'], follower.cfg,
                                  start_sec=state.time_sec, end_sec=end)
    initial = copy.deepcopy(reference)
    initial.N_UF_star = math.fsum(rates.values())
    return initial, {'schema': 'decision-nuf-initialization/v1',
        'start_sec': state.time_sec, 'end_sec': end,
        'previous_target_veh_h': reference.N_UF_star, 'target_veh_h': initial.N_UF_star,
        'accepted_rate_veh_h_by_ramp': rates, 'reference_action_token': token,
        'reference_response_token': item['response_token'],
        'frozen_context_token': item['frozen_context_token'],
        'scope': 'Current actual-command forecast at decision entry; fixed for every seed and follower candidate in this decision'}


def validate_hold_anchor(held, historical, cfg, state):
    """Only an explicitly initialized new-step NUF may differ from execution."""
    fields = ('N_P_star', 'ramp_metering', 'vsl', 'green_times', 'offsets', 'inflow_outflow_allocation')
    if any(getattr(held['control'], f) != getattr(historical, f) for f in fields):
        raise ValueError('Validated hold changed the actual previous action')
    refresh = getattr(cfg.network, 'control_area_refresh_nuf_target_each_decision', False)
    if not refresh:
        if held['control'].N_UF_star != historical.N_UF_star:
            raise ValueError('Validated hold changed the actual previous action')
        return
    init = held.get('nuf_initialization', {})
    if (not getattr(cfg.network, 'physical_ramp_branches', None)
            or init.get('schema') != 'decision-nuf-initialization/v1'
            or init.get('start_sec') != state.time_sec
            or init.get('end_sec') != state.time_sec + cfg.mpc.horizon_steps * cfg.simulation.T_c_sec
            or init.get('previous_target_veh_h') != historical.N_UF_star
            or init.get('target_veh_h') != held['control'].N_UF_star
            or init.get('physical_commands_unchanged') is not True):
        raise ValueError('Validated hold lacks its current-decision NUF initialization')


def validate_actual_decision_hold(follower, state, reference, item, *, callbacks,
                                  context, source_fingerprint, options):
    """Validate today's prediction of the unchanged actual command, without prices.

    This is a feasible hold witness, never a Nash result. Its explicit NP/NUF
    targets are checked; new-step NUF initialization happens before this call.
    """
    import copy
    import hashlib
    import pickle
    from evaluation.controllers.area_leader_objective import shared_quantity_constraints
    token = hashlib.sha256(pickle.dumps(reference, protocol=5)).hexdigest()
    if item.get('action_token') != token:
        raise ValueError('Held response belongs to another actual action')
    owners = tuple(callbacks['ownership'].owners)
    if len(owners) != 19 or set(item.get('local_base_costs', {})) != set(owners):
        raise ValueError('Held response lacks the complete owner cost catalog')
    quantities = shared_quantity_constraints(follower, reference, item['quantities'],
        start_sec=state.time_sec, horizon_steps=follower.cfg.mpc.horizon_steps,
        np_mode='cap', target_np_veh=reference.N_P_star,
        np_tolerance_veh=options['np_tolerance_veh'], nuf_mode='equality',
        target_nuf_veh_h=reference.N_UF_star, nuf_tolerance_veh_h=options['nuf_tolerance_veh_h'])
    commands = callbacks['command_evidence'](reference, context)
    if set(commands['owner_physical_sha256']) != set(owners):
        raise ValueError('Held command lacks complete physical owner evidence')
    physical = bool(getattr(getattr(follower.cfg, 'network', None), 'physical_ramp_branches', None))
    directional = {}
    if not physical:
        shares = follower._wu._omega_f
        if (set(shares) != {'FW_W', 'FW_E'}
                or any(not math.isfinite(v) or v < 0 for v in shares.values())
                or abs(math.fsum(shares.values())-1.) > 1e-12):
            raise ValueError('Held command needs the installed directional shares')
        directional = {owner: {'actual': quantities['meter_rate_veh_h_by_owner'][owner],
            'target': reference.N_UF_star*shares[owner], 'tolerance': options['nuf_tolerance_veh_h']}
            for owner in shares}
    # Physical8 constrains the total predicted accepted merge only, exactly as
    # the main game does. The historical 50/50 service split is not a target.
    direction_ok = all(abs(r['actual']-r['target']) <= r['tolerance'] for r in directional.values())
    coverage = item.get('model_constraint_coverage', {})
    resource = item['resource_summary']['max_exceedance_veh']
    objective = item['objective_veh_h']
    if not all(type(v) in (int, float) and math.isfinite(v) for v in (resource, objective)) or resource < 0:
        raise ValueError('Held response has invalid objective/resource evidence')
    feasible = (item.get('conditional_model_feasibility_witness') is True
        and coverage.get('complete') is True and coverage.get('conditional_model_feasibility_witness') is True
        and resource <= options['shared_tolerance'] and quantities['feasible'] is True and direction_ok)
    score = copy.deepcopy(item)
    score.update(quantity_constraints=quantities, physical_owner_tokens=copy.deepcopy(commands['owner_physical_sha256']))
    return {'schema': 'validated-decision-hold/v1', 'feasible': feasible,
        'control': copy.deepcopy(reference), 'final_action_token': token,
        'final_score': score, 'command_evidence': copy.deepcopy(commands),
        'source_fingerprint': source_fingerprint, 'directional_constraints': directional,
        'shared_tolerance': options['shared_tolerance'], 'finite_neighborhood_certified': False,
        'final_check_complete': False, 'maximum_finite_candidate_gap': None,
        'scope': 'Current-state fixed-target/box/command/model feasibility only; no prices, search or GNE certificate'}



def _np_kind_totals(quantities, signals):
    """Exactly the canonical 17-owner accepted-service coordinate, never Omega."""
    kinds = ('boundary_in', 'off_ramp', 'boundary_out', 'on_ramp', 'internal')
    if (quantities.get('schema') != 'shared-urban-kind-service/v1'
            or len(signals) != 17 or set(quantities.get('owners', {})) != set(signals)):
        raise ValueError('Fast NP initialization needs all canonical 17 urban owners')
    totals = dict.fromkeys(kinds, 0.)
    for owner in signals:
        row = quantities['owners'][owner]
        by_kind = row['by_kind_veh']
        if set(by_kind) != set(kinds) or any(type(v) not in (int, float)
                or not math.isfinite(v) or v < 0 for v in by_kind.values()):
            raise ValueError('Invalid accepted movement service in NP basis')
        nin = by_kind['boundary_in'] + by_kind['off_ramp'] - by_kind['boundary_out'] - by_kind['on_ramp']
        if not math.isclose(nin, row['net_inflow_veh'], rel_tol=0., abs_tol=1e-8):
            raise ValueError('NP kind-signed service differs from canonical owner total')
        for kind in kinds:
            totals[kind] += by_kind[kind]
    return totals


def _linear_green_extreme(net, owner, coefficients, move_box, reference):
    """Tiny linear heuristic on the exact millisecond phase/actual-command box."""
    from evaluation.controllers import signal_actuation_contract as signals
    live = tuple(net.signal_live_phases(owner))
    physical = signals.phase_bounds(net, owner)
    limits = {key: (ref, limit) for field, key, ref, limit, cycle in move_box.entries
              if field == 'green_times'}
    box = {}
    for p in live:
        ref, limit = limits[owner + '_' + p]
        lo, hi = physical[p]
        box[p] = (math.ceil(1000 * max(lo, ref-limit) - 1e-8),
                  math.floor(1000 * min(hi, ref+limit) + 1e-8))
        if box[p][0] > box[p][1]:
            raise ValueError('Empty actual-command phase intersection')
    total = round(1000 * net.signal_effective_green_total(owner))
    if abs(total / 1000 - net.signal_effective_green_total(owner)) > 1e-9:
        raise ValueError('Green total is not on writer millisecond grid')
    basis = signals.native_clock_basis(net, owner)
    # No measured green direction: retain the actual command instead of
    # arbitrarily filling a phase at a flat objective's extreme.
    concurrent = basis is not None and basis['kind'] == 'concurrent_p1_p2'
    flat = (all(v == 0. for v in coefficients.values()) if concurrent else
            max(coefficients.values()) == min(coefficients.values()))
    if flat:
        return {p: float(reference.green_times[owner+'_'+p]) for p in signals.PHASES}
    if basis is not None and basis['kind'] == 'concurrent_p1_p2':
        if set(live) != {'p1', 'p2', 'p4'}:
            raise ValueError('Unsupported concurrent phase basis')
        amber = round(1000 * basis['amber_sec'])
        if abs(amber / 1000 - basis['amber_sec']) > 1e-9:
            raise ValueError('Concurrent amber is not on writer grid')
        lo = max(box['p2'][0], total-box['p4'][1], box['p1'][0]+amber)
        hi = min(box['p2'][1], total-box['p4'][0])
        if lo > hi:
            raise ValueError('Empty concurrent phase intersection')
        points = {lo, hi, min(hi, max(lo, box['p1'][1]+amber))}
        def vector(y):
            x = box['p1'][0] if coefficients['p1'] >= 0 else min(box['p1'][1], y-amber)
            return {'p1': x, 'p2': y, 'p4': total-y}
        candidates = [vector(y) for y in sorted(points)]
        chosen = min(candidates, key=lambda v: (math.fsum(coefficients[p]*v[p] for p in live),
            math.fsum((v[p]/1000-reference.green_times[owner+'_'+p])**2 for p in live)))
    else:
        chosen = {p: box[p][0] for p in live}
        residual = total - sum(chosen.values())
        if not 0 <= residual <= sum(hi-lo for lo, hi in box.values()):
            raise ValueError('Phase box cannot preserve the current cycle')
        for p in sorted(live, key=lambda p: (coefficients[p], live.index(p))):
            addition = min(residual, box[p][1]-chosen[p])
            chosen[p] += addition
            residual -= addition
    result = {p: chosen.get(p, 0)/1000 for p in signals.PHASES}
    signals.validate_vector(net, owner, result)
    return result


def prepare_fast_np_seeds(follower, reference, measured, move_box):
    """Reuse existing full-horizon price responses for a signed-flow initializer.

    These secants already include destination queues, predicted arrivals, travel
    time, receiving/lane/shared-stock constraints, spillback and signal clocks
    implemented by the canonical model. Extrapolation is only a heuristic.
    No physical response or new search is performed here.
    """
    import copy
    import numpy as np
    from time import perf_counter
    from evaluation.controllers import signal_actuation_contract as signals
    net = follower.cfg.network
    started = perf_counter()
    if move_box is None:
        raise ValueError('Fast NP seeds require a fixed actual-command trust region')
    responses = measured['responses']['results']
    base = _np_kind_totals(responses[0]['quantities'], net.signals)
    kinds = tuple(base)
    green_only, with_offset = copy.deepcopy(reference), copy.deepcopy(reference)
    evidence = {}
    for owner in net.signals:
        live = tuple(net.signal_live_phases(owner))
        keys = tuple(owner+'_'+p for p in live) + (owner,)
        selection = measured['probe_selection'][owner]
        edges = measured['secants'][owner]
        indices = selection['action_indices']
        if len(edges) != len(indices) or len(edges) != len(live):
            raise ValueError('Incomplete urban NP tangent basis')
        x = np.asarray([[edge['coordinate']['direction'][key] for key in keys] for edge in edges])
        y = np.asarray([[(_np_kind_totals(responses[i]['quantities'], net.signals)[k]-base[k])
                         for k in kinds] for i in indices])
        coefficients, _, rank, _ = np.linalg.lstsq(x, y, rcond=None)
        if rank != len(live) or not np.isfinite(coefficients).all():
            raise ValueError('Unidentified urban NP tangent direction')
        signed = coefficients @ np.asarray([1., 1., -1., -1., 0.])
        greens = _linear_green_extreme(net, owner, dict(zip(live, signed[:-1])), move_box, reference)
        for p, value in greens.items():
            green_only.green_times[owner+'_'+p] = with_offset.green_times[owner+'_'+p] = value
        cycle = float(net.signal_cycle_length(owner))
        entry = next(e for e in move_box.entries if e[:2] == ('offsets', owner))
        ref, limit = entry[2:4]
        delta = lambda value: ((value-ref+cycle/2) % cycle)-cycle/2
        offsets = {float(reference.offsets[owner])}
        offsets.update(round((float(f)*cycle) % cycle, 3) % cycle for f in follower.offset_fractions)
        offsets = {v for v in offsets if abs(delta(v)) <= limit+1e-9}
        with_offset.offsets[owner] = min(offsets, key=lambda v: (float(signed[-1])*delta(v), abs(delta(v)), v))
        evidence[owner] = {'coordinates': keys, 'kind_service_secants_veh_per_sec': coefficients.tolist(),
            'signed_np_secants_veh_per_sec': signed.tolist(), 'phase_green_sec': greens,
            'offset_sec': with_offset.offsets[owner], 'response_indices': indices}
    move_box.validate(green_only)
    move_box.validate(with_offset)
    return {'seeds': (green_only, with_offset), 'evidence': {
        'schema': 'fast-np-initialization/v1', 'anchor_token': move_box.anchor_token,
        'base_kind_service_veh': base, 'owners': evidence,
        'forecast_window': {k: responses[0]['quantities']['provenance'][k] for k in ('start_sec', 'end_sec')},
        'frozen_context_token': responses[0]['frozen_context_token'],
        'response_tokens': [r['response_token'] for r in responses], 'new_endpoint_calls': 0,
        'initializer_generation_wall_sec': perf_counter()-started,
        'possibility': 'unknown', 'global_np_lower_bound_veh': None,
        'domain_infeasible': False, 'full_control_domain_bound_certified': False,
        'bound_limit': 'Local observed secants do not bound all green/offset/VSL/meter combinations. No target may be excluded by these values.',
        'scope': '17-owner boundary_in + off_ramp - boundary_out - on_ramp accepted service. Full model and writer must validate each retargeted seed; no queue-only 450s service cap.'}}


def prepare_common_joint_prices(controller, state, forecast, historical, mapping, *,
                                 runtime_sources, options, budget=None, progress=None,
                                 worker_bootstrap=None):
    """One actual-anchor field, independent of candidate NP/NUF constraints."""
    import copy
    import hashlib
    import pickle
    from evaluation.controllers import vissim_stackelberg_adapter as adapter, area_runtime
    from evaluation.controllers import area_meter_finalization as meters
    from evaluation.controllers.area_leader_objective import install_joint_price_field
    follower, state, forecast, historical, mapping = copy.deepcopy(
        (controller.nash_solver, state, forecast, historical, mapping))
    source_token = hashlib.sha256(pickle.dumps(runtime_sources, protocol=5)).hexdigest()
    reference = meters.prepare_held_actual_reference(historical, follower.cfg)
    refresh_nuf = getattr(follower.cfg.network, 'control_area_refresh_nuf_target_each_decision', False)
    initialization = None
    with shared_query_runtime_scope():
        adapter._PHASE_VECTOR_FOLLOWER['ref'] = follower
        callbacks, context, fingerprint = _joint_runtime_callbacks(follower, state, forecast,
            historical, reference, mapping, runtime_sources, reference=reference,
            total_budget=None, directional={},
            tolerance=options['nuf_tolerance_veh_h'], budget=budget, price_probe=True, progress=progress)
        query = make_decision_shared_query(follower, state, reference, forecast,
            horizon_steps=follower.cfg.mpc.horizon_steps, source_fingerprint=source_token,
            cache_enabled=options.get('response_cache_enabled', True), check_budget=budget.check if budget else None,
            parallel_workers=options.get('response_parallel_workers', 0),
            worker_bootstrap=worker_bootstrap,
            deadline_monotonic=(budget.started + budget.seconds - budget.reserve_sec) if budget and not budget.unlimited_time else None,
            **({'unlimited_time': True} if budget and budget.unlimited_time else {}))
        if budget is not None:
            budget.response_query = query
        if budget is not None or refresh_nuf:
            # Complete a usable current-state witness before the expensive price
            # basis. The identical reference in the later batch is a cache hit.
            from contextlib import nullcontext
            with budget.scope('actual_hold_prediction_and_validation') if budget else nullcontext():
                item = query((reference,))['results'][0]
                initial = reference
                if refresh_nuf:
                    initial, initialization = initialize_decision_nuf(follower, state, reference, item)
                    original_commands = callbacks['command_evidence'](reference, context)
                    # Keep the original reference/price anchor intact. Query the
                    # exact new target action, including its full action token.
                    item = query((initial,))['results'][0]
                hold = validate_actual_decision_hold(follower, state, initial, item,
                    callbacks=callbacks, context=context, source_fingerprint=source_token, options=options)
                if initialization is not None:
                    if (original_commands['owner_physical_sha256'] != hold['command_evidence']['owner_physical_sha256']
                            or item['frozen_context_token'] != initialization['frozen_context_token']
                            or hold['final_score']['quantity_constraints']['nuf']['actual'] != initialization['target_veh_h']):
                        raise ValueError('New-step NUF initialization changed physical commands or predicted merges')
                    initialization['physical_commands_unchanged'] = True
                    hold['nuf_initialization'] = copy.deepcopy(initialization)
                    validate_hold_anchor(hold, historical, follower.cfg, state)
                validation = {'feasible': hold['feasible'],
                    'quantity_constraints': hold['final_score']['quantity_constraints'],
                    'directional_constraints': hold['directional_constraints'],
                    'resource_max_exceedance_veh': item['resource_summary']['max_exceedance_veh']}
                if initialization is not None:
                    validation['nuf_initialization'] = copy.deepcopy(initialization)
                if budget is not None:
                    budget.hold_validation = validation
                if budget is not None and hold['feasible']:
                    budget.validated_hold_bytes = pickle.dumps(hold, protocol=5)
                    budget.validated_hold_sha256 = hashlib.sha256(budget.validated_hold_bytes).hexdigest()
                if progress:
                    progress({'stage': 'actual_hold_validated', **validation})
        measured = area_runtime.evaluate_joint_prices(follower, state, reference, forecast,
            callbacks=callbacks, context=context, context_fingerprint=fingerprint,
            horizon_steps=follower.cfg.mpc.horizon_steps, directional_nuf_targets_veh_h={},
            nuf_tolerance_veh_h=options['nuf_tolerance_veh_h'], source_fingerprint=source_token,
            progress=progress, response_query=query, check_budget=budget.check if budget else None,
            nuf_price_policy='independent')
        expected = measured['field']['context']
        installed = install_joint_price_field(follower, reference, measured['field'],
            expected_owners=callbacks['ownership'].owners, expected_context=expected, nuf_mode='equality')
    fast_np = None
    if getattr(follower.cfg.network, 'control_area_fast_np_initialization', None) is not None:
        fast_np = prepare_fast_np_seeds(follower, reference, measured, callbacks['move_box'])
    return {**({'fast_np': fast_np} if fast_np is not None else {}),
            'measured': measured, 'installed': installed, 'follower': follower,
            'reference': reference, 'response_query': query, 'expected_context': expected,
            'nuf_initialization': initialization}


def solve_runtime_joint_leader(controller, state, forecast, historical, mapping, *,
                               runtime_sources, options, progress=None, budget=None,
                               worker_bootstrap=None):
    """Rank final shared follower responses over an explicit realized domain.

    All prepared NP caps, NUF equalities and physical meter schedules survive.
    ``diverse`` changes evaluation order only: start at the largest NP/NUF,
    then use farthest-first normalized NP, NUF and four grouped-meter values
    (squared Euclidean distance, source order breaks ties). No objective proxy,
    nearest-budget choice, NUF-only reuse, or legacy fallback is used.

    One actual-anchor price field precedes every candidate. One whole-decision
    deadline includes preparation and reserves finalization time. In-process
    callbacks are cooperative; optional owned workers have deadline cleanup.
    Per-candidate limits never extend the decision deadline. Thus this
    is best-observed final Omega J, not a leader optimum, response uniqueness,
    equilibrium selection guarantee, or proof of domain infeasibility.
    """
    import copy
    import hashlib
    import pickle
    from time import perf_counter
    from evaluation.controllers.area_leader_objective import validate_joint_leader_result

    candidate_keys = {'max_evaluations', 'time_budget_sec', 'improvement_tolerance',
                      'shared_tolerance', 'np_tolerance_veh', 'nuf_tolerance_veh_h', 'traversal'}
    leader_keys = {'max_leader_candidates', 'leader_time_budget_sec', 'leader_candidate_order'}
    decision_keys = {'decision_time_budget_sec', 'finalization_reserve_sec', 'response_cache_enabled',
                     'response_parallel_workers', 'ignore_wall_time_limits'}
    if type(options.get('ignore_wall_time_limits', False)) is not bool:
        raise ValueError('ignore_wall_time_limits must be boolean')
    if not isinstance(options, dict) or not candidate_keys | leader_keys <= set(options) or set(options) - candidate_keys - leader_keys - decision_keys:
        raise ValueError('Exact explicit joint candidate and leader work options required')
    if (type(options['max_leader_candidates']) is not int or options['max_leader_candidates'] < 1
            or type(options['max_evaluations']) is not int or options['max_evaluations'] < 0):
        raise ValueError('Positive leader count and nonnegative candidate evaluation count required')
    for key in (candidate_keys - {'max_evaluations', 'traversal'}) | {'leader_time_budget_sec'}:
        value = options[key]
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError('Finite nonnegative explicit work limit/tolerance required: ' + key)
    if options['leader_candidate_order'] != 'diverse' or options['traversal'] not in ('sequential', 'round_robin', 'round_robin_balanced'):
        raise ValueError('Explicit diverse leader order and supported follower traversal required')
    if not isinstance(runtime_sources, dict) or not runtime_sources:
        raise ValueError('Runtime source provenance required')

    def digest(value):
        return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()

    started = perf_counter()
    if budget is None:
        budget = DecisionBudget(options.get('decision_time_budget_sec', 120.),
                                reserve_sec=options.get('finalization_reserve_sec', 10.),
                                unlimited_time=options.get('ignore_wall_time_limits', False))
    budget.check('leader_preparation')
    # Legacy controller instances can own pools and installed method closures.
    # Copy only the consumed objects together, preserving their shared cfg;
    # the shallow shell's unrelated legacy resources are never used or hashed.
    controller = copy.copy(controller)
    inputs = copy.deepcopy((controller.leader, controller.nash_solver, controller.cfg,
                            state, forecast, historical, mapping, runtime_sources, options))
    (controller.leader, controller.nash_solver, controller.cfg,
     state, forecast, historical, mapping, runtime_sources, options) = inputs
    def frozen_values():
        return (controller.leader, controller.nash_solver, controller.cfg,
                state, forecast, historical, mapping, runtime_sources, options)
    fixed = digest(frozen_values())
    candidate_options = {key: options[key] for key in sorted(candidate_keys)}
    domain = prepare_joint_leader_candidates(controller, state, forecast, historical,
        budget_tolerance_veh_h=options['nuf_tolerance_veh_h'], check_budget=budget.check)
    proposals = domain['candidates']
    if (domain.get('schema') != 'joint-leader-realized-domain/v1' or not proposals
            or domain.get('candidate_count') != len(proposals)
            or domain.get('objective_queries') != 0 or domain.get('leader_target_selected') is not False):
        raise ValueError('Complete unscored realized leader domain required')
    domain_token = digest(domain)
    physical_domain = domain.get('quantity_semantics') == 'predicted_accepted_mainline_merge'
    ramp_keys = tuple(sorted(controller.cfg.network.ramps))
    vectors, summaries = [], []
    for index, proposal in enumerate(proposals):
        action = proposal['control']
        np_value, nuf_value = proposal['target_np_veh'], proposal['target_nuf_veh_h']
        # Physical seeds are ordered by NP then diverse service coordinates;
        # service sum is an ordering coordinate only, never an NUF estimate.
        ordering_nuf = math.fsum(action.ramp_metering.values()) if physical_domain else nuf_value
        values = (np_value, ordering_nuf, *(action.ramp_metering[key] for key in ramp_keys))
        if (set(action.ramp_metering) != set(ramp_keys) or action.N_P_star != np_value
                or (not physical_domain and action.N_UF_star != nuf_value)
                or (physical_domain and (nuf_value is not None or proposal.get('requires_merge_prediction') is not True))
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in values)
                or any(v < 0 for v in values[1:])):  # Signed NP, nonnegative NUF/meters.
            raise ValueError('Prepared leader coordinates must be finite and exactly action-bound')
        vectors.append(values)
        summaries.append({'index': index, 'target_np_veh': np_value, 'target_nuf_veh_h': nuf_value,
            'meter_bank_index': proposal['meter_bank_index'],
            'grouped_meter_rates_veh_h': dict(action.ramp_metering),
            'directional_budgets': copy.deepcopy(proposal['directional_budgets']),
            'proposal_token': digest(proposal), 'physical_meter_rows_token': digest(proposal['physical_meter_rows']),
            'status': 'unvisited', 'objective_veh_h': None, 'maximum_finite_candidate_gap': None})
    minima = tuple(min(v[k] for v in vectors) for k in range(len(vectors[0])))
    spans = tuple(max(v[k] for v in vectors) - minima[k] for k in range(len(minima)))
    normalized = [tuple((v[k] - minima[k]) / spans[k] if spans[k] else 0.
                        for k in range(len(v))) for v in vectors]
    first = max(range(len(proposals)), key=lambda i: (vectors[i][0], vectors[i][1], -i))
    order, remaining = [first], set(range(len(proposals))) - {first}
    def pair_distance(i, j):
        return math.fsum((a - b) ** 2 for a, b in zip(normalized[i], normalized[j]))
    nearest = {i: pair_distance(i, first) for i in remaining}
    while remaining:
        budget.check('leader_candidate_order')
        chosen = max(remaining, key=lambda i: (nearest[i], -i))
        order.append(chosen)
        remaining.remove(chosen)
        # Same farthest-first order and source-index ties. Preserve the exact
        # minimum instead of recomputing every already visited distance.
        for i in remaining:
            nearest[i] = min(nearest[i], pair_distance(i, chosen))
    if digest(frozen_values()) != fixed:
        raise ValueError('Leader preparation changed its frozen decision inputs')

    best, best_index, attempted, stop, failure = None, None, [], None, None
    common = None
    try:
        with budget.scope('common_price_preparation_and_measurement'):
            common = prepare_common_joint_prices(controller, state, forecast, historical, mapping,
                runtime_sources=runtime_sources, options=options, budget=budget, progress=progress,
                worker_bootstrap=worker_bootstrap)
    except TimeoutError as exc:
        stop = 'decision_time_budget_during_common_prices'
        if progress:
            progress({'stage': stop, 'reason': str(exc), 'budget': budget.report()})
    for index in order:
        if common is None or budget.remaining() <= 0:
            stop = stop or 'decision_time_budget'
            break
        if not budget.unlimited_time and perf_counter() - started >= options['leader_time_budget_sec']:
            stop = 'leader_time_budget'
            break
        if len(attempted) >= options['max_leader_candidates']:
            stop = 'leader_candidate_budget'
            break
        row = summaries[index]
        attempted.append(index)
        tick = perf_counter()
        try:
            prepared = proposals[index]
            if physical_domain:
                from evaluation.controllers import physical_ramp_branches
                budget.check('leader_seed_merge_prediction')
                initialization = common.get('nuf_initialization')
                if initialization is not None:
                    target = initialization['target_veh_h']
                    row['target_source'] = initialization['scope']
                else:
                    with budget.scope('leader_seed_merge_prediction'):
                        item = common['response_query']((prepared['control'],))['results'][0]
                        rates, _ = physical_ramp_branches.checked_merge_rates(
                            item['quantities']['predicted_ramp_merge'], controller.cfg,
                            start_sec=state.time_sec, end_sec=state.time_sec+controller.cfg.mpc.horizon_steps*controller.cfg.simulation.T_c_sec)
                    target = math.fsum(rates.values())
                    row['target_source'] = 'Accepted merge of this seed before follower search; frozen thereafter'
                prepared = copy.deepcopy(prepared)
                prepared['control'].N_UF_star = prepared['target_nuf_veh_h'] = target
                prepared['requires_merge_prediction'] = False
                row['target_nuf_veh_h'] = target
            if progress is not None:
                progress({'stage': 'joint_leader_candidate_start', 'index': index,
                          'domain_count': len(proposals), 'target_np_veh': row['target_np_veh'],
                          'target_nuf_veh_h': row['target_nuf_veh_h']})
            solved = solve_runtime_joint_candidate(controller, state, forecast, historical,
                prepared, mapping, runtime_sources=runtime_sources,
                options=candidate_options, progress=progress, common=common, budget=budget)
            if (digest(frozen_values()) != fixed or digest(domain) != domain_token
                    or candidate_options != {key: options[key] for key in candidate_keys}):
                raise ValueError('Leader candidate changed frozen inputs or the prepared domain')
            if (solved['target_np_veh'] != row['target_np_veh']
                    or solved['target_nuf_veh_h'] != row['target_nuf_veh_h']
                    or solved['source_fingerprint'] != digest(runtime_sources)):
                raise ValueError('Candidate response belongs to another leader/source context')
            if 'fast_np' in solved['response']:
                row['fast_np'] = copy.deepcopy(solved['response']['fast_np'])
            scheduling_receipt = solved['response'].get('queries', {}).get('bounded_response_schedule')
            if scheduling_receipt is not None:
                row['response_scheduling'] = copy.deepcopy(scheduling_receipt)
                row['final_check_reserve'] = copy.deepcopy(solved['response']['game'].get('final_check_reserve'))
            status = solved['candidate_status']
            if status == 'feasible_final_response':
                # Validate the actual final action/score again at the selection
                # boundary; never rank a nominal/initializer score or price sum.
                validated = validate_joint_leader_result(solved['response'],
                    target_np_veh=row['target_np_veh'], target_nuf_veh_h=row['target_nuf_veh_h'],cfg=controller.cfg)
                if digest(validated) != digest(solved['validated_nash']):
                    raise ValueError('Transported Nash result differs from the validated final response')
                game = solved['response']['game']
                row.update(status=status, objective_veh_h=validated['objective_value'],
                    final_check_complete=game['final_check_complete'],
                    finite_neighborhood_certified=game['certified'],
                    maximum_finite_candidate_gap=game['maximum_finite_candidate_gap'],
                    final_action_token=solved['response']['final_action_token'],
                    game_error=copy.deepcopy(game['error']), evaluations=game['evaluations'])
                if best is None or row['objective_veh_h'] < summaries[best_index]['objective_veh_h']:
                    best, best_index = solved, index
            elif status in ('infeasible_initializer', 'unscored_budget_stop', 'restoration_budget_stop') and solved['validated_nash'] is None:
                row.update(status=status, game_error=copy.deepcopy(solved['response']['game']['error']),
                           initializer_evidence=copy.deepcopy(solved['initializer_evidence']))
            else:
                raise ValueError('Unknown or inconsistent runtime candidate outcome')
            if (solved['response']['game'].get('error') or {}).get('kind') == 'decision_deadline':
                stop = 'decision_time_budget'
                break
        except TimeoutError as exc:
            row.update(status='unscored_budget_stop', failure={'type': type(exc).__name__, 'message': str(exc)})
            stop = 'decision_time_budget'
            break
        except Exception as exc:
            row.update(status='failed_unknown', failure={'type': type(exc).__name__, 'message': str(exc)})
            failure, stop = copy.deepcopy(row['failure']), 'candidate_failure'
            break
        finally:
            row['elapsed_sec'] = perf_counter() - tick
    elapsed = perf_counter() - started
    rank = sorted((i for i in attempted if summaries[i]['status'] == 'feasible_final_response'),
                  key=lambda i: (summaries[i]['objective_veh_h'], attempted.index(i)))
    unknown = [r['index'] for r in summaries if r['status'] in
               ('unvisited', 'failed_unknown', 'unscored_budget_stop', 'restoration_budget_stop')]
    metadata = {'schema': 'runtime-joint-leader-selection/v1', 'domain_count': len(proposals),
        'domain_token': domain_token, 'source_fingerprint': digest(runtime_sources),
        'frozen_decision_inputs_token': fixed, 'options': copy.deepcopy(options),
        'domain_scope': domain['scope'], 'preparation_objective_queries': 0,
        'evaluation_order': order, 'attempted_indices': attempted, 'ranking_indices': rank,
        'candidates': summaries, 'unknown_candidate_indices': unknown,
        'infeasible_initializer_indices': [r['index'] for r in summaries if r['status'] == 'infeasible_initializer'],
        'all_candidates_attempted': len(attempted) == len(proposals),
        'all_candidates_have_feasible_final_response': len(rank) == len(proposals),
        'stop_reason': stop, 'failure': failure, 'elapsed_sec': elapsed,
        'leader_time_budget_overrun_sec': None if budget.unlimited_time else max(0., elapsed - options['leader_time_budget_sec']),
        'best_completed_index': best_index, 'selected_index': best_index if failure is None else None,
        'selection_status': ('aborted_failure' if failure else 'selected_best_observed' if best is not None else 'no_validated_response'),
        'leader_optimum_certified': False, 'leader_domain_infeasible': False,
        'decision_budget': budget.report(),
        'common_price_measurement_count': int(common is not None),
        'common_price_reference_token': digest(historical),
        'physical_response_cache': common['response_query'].stats() if common else (
            budget.response_query.stats() if hasattr(budget, 'response_query') else None),
        'fixed_move_limits': joint_decision_move_limits(controller.nash_solver),
        'time_budget_scope': ('Computation wall limits disabled; evaluation/sweep/candidate bounds remain active'
            if budget.unlimited_time else
            'Single preparation/price/search/finalization deadline; cooperative callback overrun is reported'),
        'ranking_scope': 'Pure final Omega J among validated observed follower responses; partial/null gaps are preserved; infeasible initializers do not prove leader-domain infeasibility'}
    held = None
    # Short restoration can exhaust finite work before the decision deadline.
    # Unknown candidates do not invalidate the separately checked actual hold.
    finite_work_exhausted = bool(unknown) and (
        stop in ('leader_time_budget', 'leader_candidate_budget')
        or (stop is None and len(attempted) == len(proposals)))
    if best is None and failure is None and (finite_work_exhausted
            or stop in ('decision_time_budget', 'decision_time_budget_during_common_prices')):
        raw_hold = getattr(budget, 'validated_hold_bytes', None)
        if raw_hold is not None:
            if hashlib.sha256(raw_hold).hexdigest() != budget.validated_hold_sha256:
                raise ValueError('Validated actual hold witness changed')
            held = pickle.loads(raw_hold)
            if not held['feasible'] or held['source_fingerprint'] != digest(runtime_sources):
                raise ValueError('Validated actual hold has another source or failed feasibility')
            validate_hold_anchor(held, historical, controller.cfg, state)
            metadata['selection_status'] = 'validated_actual_hold'
            metadata['hold_price_complete'] = common is not None
    metadata['actual_hold_validation'] = getattr(budget, 'hold_validation', None)
    return {'selected': best if failure is None else None, 'held_response': held, 'metadata': metadata}


def _runtime_joint_candidate_validation(result, *, target_np, target_nuf, initial, expected_owners, cfg=None):
    """Separate a witnessed bad initializer from unknown work/contract failure."""
    import hashlib
    import pickle
    from evaluation.controllers.area_leader_objective import validate_joint_leader_result
    game, score = result['game'], result['final_score']
    error = game.get('error') or {}
    budget_stop = error.get('kind') in ('time_budget', 'evaluation_budget', 'decision_deadline')
    cached_infeasible = (budget_stop and score is not None
        and (score.get('quantity_constraints', {}).get('feasible') is False
             or score.get('resource_summary', {}).get('max_exceedance_veh', 0.) > game['limits']['shared_tolerance']))
    if error.get('kind') == 'infeasible_incumbent' or cached_infeasible:
        action_token = hashlib.sha256(pickle.dumps(initial, protocol=5)).hexdigest()
        if (score is None or result['final_action_token'] != action_token
                or score.get('action_token') != action_token
                or hashlib.sha256(pickle.dumps(game['control'], protocol=5)).hexdigest() != action_token
                or set(game['owners']) != set(expected_owners) or game['owner_count'] != 19
                or score.get('conditional_model_feasibility_witness') is not True
                or score['model_constraint_coverage'].get('complete') is not True
                or score['model_constraint_coverage'].get('conditional_model_feasibility_witness') is not True):
            raise ValueError('Infeasible initializer needs the unchanged complete witnessed initial response')
        quantity = score['quantity_constraints']
        violation = score['resource_summary']['max_exceedance_veh']
        quantity_failed = False
        for channel, mode, target in (('np', 'cap', target_np), ('nuf', 'equality', target_nuf)):
            row = quantity[channel]
            actual, tolerance = row['actual'], row['tolerance']
            if (any(type(v) not in (int, float) or not math.isfinite(v) for v in (actual, target, tolerance))
                    or tolerance < 0 or row.get('mode') != mode or row.get('target') != target
                    or row.get('constraint_checked') is not True):
                raise ValueError('Infeasible initializer has another or incomplete quantity context')
            residual = actual - target
            excess = max(0., residual) if mode == 'cap' else abs(residual)
            if (row.get('residual') != residual or row.get('violation') != excess
                    or row.get('satisfied') is not (excess <= tolerance)):
                raise ValueError('Infeasible initializer quantity witness is inconsistent')
            quantity_failed |= excess > tolerance
        if (quantity.get('schema') != 'shared-quantity-constraints/v1'
                or quantity.get('feasible') is not (not quantity_failed)
                or type(violation) not in (int, float) or not math.isfinite(violation) or violation < 0
                or not (quantity_failed or violation > game['limits']['shared_tolerance'])):
            raise ValueError('No witnessed initializer constraint violation')
        evidence = {'quantity_constraints': quantity,
            'resource_max_exceedance_veh': violation, 'leader_domain_infeasible': False}
        if cached_infeasible:
            restoration = result.get('initializer_restoration')
            allowed = ('time_budget', 'evaluation_budget', 'decision_deadline',
                       'restoration_exhausted', 'iteration_limit')
            if (not isinstance(restoration, dict) or restoration.get('status') not in allowed
                    or restoration.get('feasible') is not False or restoration.get('control') is not None
                    or restoration.get('domain_infeasible') is not False
                    or hashlib.sha256(pickle.dumps(restoration.get('best_infeasible'), protocol=5)).hexdigest() != action_token
                    or (restoration.get('error') is not None and
                        restoration['error'].get('kind') not in ('time_budget', 'evaluation_budget', 'decision_deadline'))):
                raise ValueError('Cached infeasible budget stop needs an unchanged bounded restoration witness')
            owners = set(expected_owners)
            np_owners = quantity.get('net_inflow_veh_by_owner')
            nuf_owners = quantity.get('meter_rate_veh_h_by_owner')
            if (not isinstance(np_owners, dict) or set(np_owners) != owners-{'FW_E', 'FW_W'}
                    or not isinstance(nuf_owners, dict) or set(nuf_owners) != {'FW_E', 'FW_W'}
                    or any(type(v) not in (int, float) or not math.isfinite(v)
                           for v in (*np_owners.values(), *nuf_owners.values(), *initial.ramp_metering.values()))
                    or initial.N_P_star != target_np
                    or any(v < 0 for v in (*nuf_owners.values(), *initial.ramp_metering.values()))):
                raise ValueError('Cached infeasible witness needs complete finite action-bound quantity owners')
            from evaluation.controllers import physical_ramp_branches
            physical = cfg is not None and physical_ramp_branches.enabled(cfg)
            if physical:
                physical_ramp_branches.prepare_control(initial.copy(), cfg)
                window = quantity.get('window')
                merge = quantity.get('physical_ramp_merge')
                if (not isinstance(window, dict)
                        or quantity.get('nuf_definition') != 'predicted_accepted_mainline_merge'
                        or score.get('control_area', {}).get('predicted_ramp_merge') != merge):
                    raise ValueError('Cached infeasible NUF needs its captured physical merge response')
                rates, physical_owners = physical_ramp_branches.checked_merge_rates(
                    merge, cfg, start_sec=window.get('start_sec'), end_sec=window.get('end_sec'))
                if physical_owners != nuf_owners:
                    raise ValueError('Cached infeasible NUF owner totals differ from physical merges')
                nuf = math.fsum(rates.values())
            else:
                if len(initial.ramp_metering) != 4:
                    raise ValueError('Four grouped meters required unless physical branches are configured')
                nuf = math.fsum(initial.ramp_metering.values())
            if (math.fsum(np_owners[o] for o in sorted(np_owners)) != quantity['np']['actual']
                    or nuf != quantity['nuf']['actual']
                    or initial.N_UF_star != (target_nuf if physical else nuf)
                    or abs(math.fsum(nuf_owners.values())-nuf) > 2*math.ulp(nuf)):
                raise ValueError('Cached infeasible witness quantities differ from owner/action totals')
            expected_merit = (max(0., quantity['np']['actual']-target_np-quantity['np']['tolerance'])/max(1., abs(target_np))
                + max(0., abs(nuf-target_nuf)-quantity['nuf']['tolerance'])/max(1., abs(target_nuf))
                + max(0., violation-game['limits']['shared_tolerance']))
            if restoration.get('final_violation') != expected_merit or expected_merit <= 0.:
                raise ValueError('Cached infeasible restoration merit differs from its complete witness')
            evidence.update(initializer_feasible=False, candidate_feasibility_known=False,
                restoration_status=restoration['status'], restoration_final_violation=expected_merit)
            return 'restoration_budget_stop', None, evidence
        return 'infeasible_initializer', None, evidence
    if score is None and budget_stop:
        return 'unscored_budget_stop', None, {'feasibility_known': False, 'leader_domain_infeasible': False}
    validated = validate_joint_leader_result(result, target_np_veh=target_np, target_nuf_veh_h=target_nuf,cfg=cfg)
    return 'feasible_final_response', validated, None


def solve_runtime_joint_candidate(controller, state, forecast, historical, proposal, mapping, *,
                                  runtime_sources, options, progress=None, common=None, budget=None):
    """Candidate initialization and response under one decision's actual-anchor prices."""
    import copy
    import hashlib
    import pickle
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers import area_meter_finalization as meters
    from evaluation.controllers.area_leader_objective import install_joint_price_field
    def digest(value):
        return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()
    if common is None:
        common = prepare_common_joint_prices(controller, state, forecast, historical, mapping,
            runtime_sources=runtime_sources, options=options, budget=budget, progress=progress)
    follower, state, forecast, historical, proposal, mapping = copy.deepcopy(
        (controller.nash_solver, state, forecast, historical, proposal, mapping))
    cfg = follower.cfg
    from evaluation.controllers import physical_ramp_branches
    physical = physical_ramp_branches.enabled(cfg)
    from time import perf_counter
    candidate_started = perf_counter()
    fast_policy = getattr(cfg.network, 'control_area_fast_np_initialization', None)
    target_np, target_nuf = proposal['target_np_veh'], proposal['target_nuf_veh_h']
    total_budget = None if physical else {'mode': 'equality', 'veh_h': target_nuf}
    directional = proposal['directional_budgets']
    leader = proposal['control'].copy()
    if leader.N_P_star != target_np or leader.N_UF_star != target_nuf:
        raise ValueError('Prepared candidate must carry its unchanged NP/NUF targets')
    with shared_query_runtime_scope():
        adapter._PHASE_VECTOR_FOLLOWER['ref'] = follower
        installed = install_joint_price_field(follower, common['reference'], common['measured']['field'],
            expected_owners=tuple(cfg.network.signals)+tuple(cfg.network.freeway_links),
            expected_context=common['expected_context'], nuf_mode='equality')
        if budget:
            budget.check('leader_initializer')
        initial = (physical_ramp_branches.prepare_control(leader.copy(), cfg) if physical else
            meters.prepare_canonical_candidate(leader, cfg, owned_ramps=tuple(cfg.network.ramps),
                total_budget=total_budget, directional_budgets=directional,
                budget_tolerance_veh_h=options['nuf_tolerance_veh_h']))
        callbacks, context, fingerprint = _joint_runtime_callbacks(follower, state, forecast,
            historical, leader, mapping, runtime_sources, reference=common['reference'],
            total_budget=total_budget, directional=directional, tolerance=options['nuf_tolerance_veh_h'],
            budget=budget, progress=progress)
        work_options = dict(options)
        if budget and budget.unlimited_time:
            work_options['time_budget_sec'] = None
        fast_seeds = ()
        if fast_policy is not None:
            if common.get('fast_np') is None:
                raise ValueError('Fast NP candidate lacks common response-derived seeds')
            prepared_seeds = []
            for prototype in common['fast_np']['seeds']:
                seed = copy.deepcopy(initial)
                seed.green_times, seed.offsets = copy.deepcopy((prototype.green_times, prototype.offsets))
                prepared_seeds.append(seed)
            fast_seeds = tuple(prepared_seeds)
            cap = max(0., fast_policy['candidate_time_budget_sec'] - (perf_counter()-candidate_started))
            work_options['time_budget_sec'] = min(cap, work_options['time_budget_sec']) if work_options['time_budget_sec'] is not None else cap
        result = solve_fixed_shared_game(follower, state, common['reference'], forecast, initial,
            callbacks=callbacks, context=context, context_fingerprint=fingerprint,
            horizon_steps=cfg.mpc.horizon_steps, lambda_p=follower._lambda_P, lambda_uf=follower._lambda_UF,
            target_np_veh=target_np, target_nuf_veh_h=target_nuf,
            price_context={'leader_present': True, 'np_mode': 'cap', 'nuf_mode': 'equality',
                'inactive_price_addresses': dict.fromkeys(('phase', 'offset', 'vsl', 'meter'), ())},
            max_sweeps=cfg.mpc.max_nash_iter, scope_label='Common actual-anchor price and fixed-box joint candidate',
            response_query=common['response_query'], deadline_check=budget.check if budget else None,
            **({'decision_deadline_monotonic': budget.started+budget.seconds-budget.reserve_sec}
                if budget and not budget.unlimited_time else {}),
            restore_initializer=True, initial_seeds=fast_seeds, restoration_policy=fast_policy,
            progress=progress if budget and budget.unlimited_time else None, **work_options)
        if fast_policy is not None:
            result['fast_np'] = copy.deepcopy(common['fast_np']['evidence'])
            result['fast_np']['candidate_time_budget_sec'] = fast_policy['candidate_time_budget_sec']
            result['fast_np']['candidate_elapsed_sec'] = perf_counter()-candidate_started
            result['fast_np']['candidate_time_overrun_sec'] = max(0., perf_counter()-candidate_started-fast_policy['candidate_time_budget_sec'])
            result['fast_np']['seed_checks'] = copy.deepcopy(result['initializer_seed_checks'])
            observed = [r['np_veh'] for r in result['initializer_seed_checks']
                        if r.get('model_and_writer_validated') and r['nuf_satisfied']]
            result['fast_np']['observed_np_range_veh'] = [min(observed), max(observed)] if observed else None
            result['fast_np']['observed_range_scope'] = 'Only evaluated seeds satisfying the fixed NUF band and model/writer constraints; no whole-domain limit.'
            result['fast_np']['skip_rule'] = 'Unrestored cap/NUF within short budget remains unknown; advance to the next leader candidate. Model/command contract failure aborts.'
        status, validated, initializer_evidence = _runtime_joint_candidate_validation(result,
            target_np=target_np, target_nuf=target_nuf, initial=result.get('restored_initial', initial),
            expected_owners=callbacks['ownership'].owners,cfg=cfg)
    return {'response': result, 'validated_nash': validated, 'candidate_status': status,
        'initializer_evidence': initializer_evidence, 'price_installation': installed,
        'price_field': common['measured']['field'],
        'price_probe_selection': common['measured']['probe_selection'],
        'target_np_veh': target_np, 'target_nuf_veh_h': target_nuf,
        'source_fingerprint': digest(runtime_sources), 'price_measurements_this_candidate': 0}


def _make_bounded_response_schedule(ownership, *, neighbors, physical_fingerprint,
                                    response_query, fingerprint, traversal,
                                    nuf_semantics, lookahead):
    """Warm only the next logical reads; the game still evaluates/adopts in order."""
    import copy
    from time import perf_counter
    import hashlib
    import pickle
    from collections import deque
    from evaluation.controllers import joint_owner_game as game
    owners = game.traversal_owner_order(ownership, traversal)
    packed = lambda value: pickle.dumps(value, protocol=5)
    scope = None
    domains, queued = {}, deque()
    stream = None
    base = supplied = work_check = phase = None
    prefetched, consumed = set(), set()
    proof = {'lookahead': lookahead, 'scopes': 0, 'batches': 0,
        'requested_responses': 0, 'endpoint_calls': 0, 'prepared_reads': 0,
        'physical_checks': 0, 'wall_sec': 0., 'phases': {},
        'completed_batches_past_work_limit': 0,
        'selection_or_domain_changed': False}

    def check():
        work_check()
        fingerprint(supplied)

    def physical(action):
        check()
        trial = copy.deepcopy(action)
        before = packed(trial)
        value = physical_fingerprint(trial, supplied)
        if packed(trial) != before or not isinstance(value, dict) or set(value) != set(owners):
            raise ValueError('Bounded prefetch requires unchanged complete physical commands')
        if any(type(v) not in (str, bytes) or not v for v in value.values()):
            raise ValueError('Bounded prefetch requires typed physical command tokens')
        proof['physical_checks'] += 1
        check()
        return tuple((owner, type(value[owner]), value[owner]) for owner in owners)

    def get_domain(owner, action, context):
        check()
        if packed(action) != packed(base) or context is not supplied:
            raise ValueError('Bounded prefetch neighborhood belongs to another base/context')
        if owner not in domains:
            trial = copy.deepcopy(action)
            before = packed(trial)
            value = neighbors(owner, trial, context)
            if packed(trial) != before:
                raise ValueError('Bounded prefetch neighbor producer changed its incumbent')
            if (not isinstance(value, game.Neighborhood) or type(value.candidates) is not tuple
                    or value.complete is not True or type(value.domain_label) is not str or not value.domain_label):
                raise ValueError('Bounded prefetch requires a complete materialized neighborhood')
            check()
            domains[owner] = copy.deepcopy(value)
        return copy.deepcopy(domains[owner])

    def owner_actions(owner, base_physical):
        yield owner, copy.deepcopy(base)
        seen = {(game._action_key(ownership, base), base_physical)}
        for candidate in get_domain(owner, base, supplied).candidates:
            check()
            game.validate_action_addresses(ownership, candidate)
            game.validate_nuf_semantics(candidate, nuf_semantics)
            game.assert_owner_transition(ownership, owner, base, candidate)
            if game._extra(candidate, nuf_semantics=nuf_semantics) != game._extra(base, nuf_semantics=nuf_semantics):
                raise ValueError('Bounded prefetch candidate changed a fixed/nonlever operand')
            command = physical(candidate)
            if any(new != old for new, old in zip(command, base_physical) if new[0] != owner):
                raise ValueError('Bounded prefetch candidate changed a foreign physical command')
            identity = (game._action_key(ownership, candidate), command)
            if identity not in seen:
                seen.add(identity)
                yield owner, copy.deepcopy(candidate)

    def logical_actions():
        base_physical = physical(base)
        if phase == 'final_check':
            for owner in owners:
                yield from owner_actions(owner, base_physical)
            return
        pending = {}
        # A game's first next(inspect_steps) reads the base and first neighbor.
        for owner in owners:
            iterator = owner_actions(owner, base_physical)
            yield next(iterator)
            pending[owner] = iterator
            try:
                yield next(iterator)
            except StopIteration:
                del pending[owner]
        while pending:
            for owner in owners:
                if owner in pending:
                    try:
                        yield next(pending[owner])
                    except StopIteration:
                        del pending[owner]

    def prepare(owner, current_base, action, context, current_phase, credit, checkpoint):
        nonlocal scope, stream, base, supplied, work_check, phase
        work_check, supplied = checkpoint, context
        check()
        identity = (packed(current_base), current_phase, fingerprint(context))
        if identity != scope:
            scope, base, phase = identity, copy.deepcopy(current_base), current_phase
            domains.clear()
            queued.clear()
            stream = logical_actions()
            proof['scopes'] += 1
        if not queued:
            probes = []
            for _ in range(min(lookahead, credit)):
                check()
                try:
                    who, candidate = next(stream)
                except StopIteration:
                    break
                queued.append((who, packed(candidate)))
                probes.append(candidate)
            if probes:
                before = tuple(packed(candidate) for candidate in probes)
                check()
                tick = perf_counter()
                phase_proof = proof['phases'].setdefault(phase, {'batches': 0,
                    'requested_responses': 0, 'endpoint_calls': 0, 'wall_sec': 0.})
                try:
                    batch = response_query(tuple(probes))
                    proof['batches'] += 1
                    proof['requested_responses'] += len(probes)
                    proof['endpoint_calls'] += batch['endpoint_calls']
                    phase_proof['batches'] += 1
                    phase_proof['requested_responses'] += len(probes)
                    phase_proof['endpoint_calls'] += batch['endpoint_calls']
                    if tuple(packed(candidate) for candidate in probes) != before:
                        raise ValueError('Bounded response query changed its supplied actions')
                    if len(batch['results']) != len(probes):
                        raise ValueError('Bounded response query returned an incomplete batch')
                    tokens = set()
                    for payload, item in zip(before, batch['results']):
                        if item.get('action_token') != hashlib.sha256(payload).hexdigest():
                            raise ValueError('Bounded response belongs to another full action')
                        token = item.get('frozen_context_token')
                        if type(token) is not str or not token:
                            raise ValueError('Bounded response needs its frozen context token')
                        tokens.add(token)
                    if len(tokens) != 1:
                        raise ValueError('Bounded response batch mixed frozen contexts')
                    prefetched.update(before)
                    try:
                        check()
                    except (game._Stop, TimeoutError):
                        proof['completed_batches_past_work_limit'] += 1
                        raise
                finally:
                    elapsed = perf_counter()-tick
                    proof['wall_sec'] += elapsed
                    phase_proof['wall_sec'] += elapsed
        if not queued or queued[0] != (owner, packed(action)):
            raise ValueError('Bounded prefetch logical order differs from the unchanged game')
        queued.popleft()
        proof['prepared_reads'] += 1

    def note_read(action):
        consumed.add(packed(action))

    def report(logical_reads):
        return {**copy.deepcopy(proof), 'logical_reads': logical_reads,
            'prefetched_distinct_actions': len(prefetched),
            'consumed_prefetched_actions': len(prefetched & consumed),
            'unconsumed_prefetched_actions': len(prefetched-consumed),
            'queued_logical_reads': len(queued), 'full_domain_precomputed': False}

    prepare.neighbors, prepare.note_read, prepare.report = get_domain, note_read, report
    return prepare


def solve_fixed_shared_game(follower, state, reference, forecast, incumbent, *,
                            callbacks, context, context_fingerprint, horizon_steps,
                            lambda_p, lambda_uf, target_np_veh, target_nuf_veh_h,
                            price_context, max_sweeps, max_evaluations, time_budget_sec,
                            improvement_tolerance, shared_tolerance, scope_label,
                            np_tolerance_veh, nuf_tolerance_veh_h, traversal='sequential',
                            response_query=None, deadline_check=None, restore_initializer=False,
                            progress=None, initial_seeds=(), restoration_policy=None, decision_deadline_monotonic=None):
    """Select a realized joint action at one explicit fixed leader/price context.

    Uses the installed neighbor/writer callbacks and the same captured physical
    trajectory for all 19 local payoffs, accepted quantities and implemented
    model constraints. Repeated whole actions are reused only within this solve.
    No refresh of prices/duals, late lever refinement or legacy dispatch occurs.
    The returned finite certificate is conditional on the implemented model;
    it does not certify native VISSIM capacity fidelity or a price fixed point.

    The caller must bind source, mapping, writer, candidate and operational
    context in context_fingerprint. Callback construction/initial realization
    happens before this timed solve. Time limits are cooperative and incomplete
    owner checks keep null gaps. No uncounted endpoint runs occur after a stop.
    """
    import copy
    import hashlib
    import pickle
    from time import perf_counter
    from evaluation.controllers import joint_owner_game as game
    from evaluation.controllers.area_leader_objective import fixed_joint_price_terms, shared_quantity_constraints
    from evaluation.controllers import physical_ramp_branches
    nuf_semantics = 'fixed_target' if physical_ramp_branches.enabled(follower.cfg) else 'realized_sum'

    if progress is not None and not callable(progress):
        raise ValueError('Fixed game progress must be callable')
    if decision_deadline_monotonic is not None and (deadline_check is None
            or type(decision_deadline_monotonic) not in (int, float)
            or not math.isfinite(decision_deadline_monotonic)):
        raise ValueError('Absolute decision deadline requires its unchanged deadline callback')
    required = {'ownership', 'neighbors', 'physical_fingerprint', 'physical_rows', 'command_evidence'}
    if not isinstance(callbacks, dict) or not required.issubset(callbacks):
        raise ValueError('Installed joint neighbor/writer callbacks required')
    owners = game.traversal_owner_order(callbacks['ownership'], traversal)
    if (len(owners) != 19 or set(owners) != set(follower.cfg.network.signals)
            | set(follower.cfg.network.freeway_links)):
        raise ValueError('Fixed shared game requires every configured 19 owner')
    if type(horizon_steps) is not int or horizon_steps < 1:
        raise ValueError('Explicit positive held horizon required')
    private, initial, anchor, demand, policy = copy.deepcopy(
        (follower, state, reference, forecast, price_context))
    def packed(value):
        return pickle.dumps(value, protocol=5)
    def token(value):
        return hashlib.sha256(packed(value)).hexdigest()
    fixed = packed((private, initial, anchor, demand, policy,
                    lambda_p, lambda_uf, target_np_veh, target_nuf_veh_h, horizon_steps,
                    np_tolerance_veh, nuf_tolerance_veh_h))
    external_token = context_fingerprint(context)
    if type(external_token) not in (str, bytes) or not external_token:
        raise ValueError('Explicit full context fingerprint required')
    fixed_context_identity = token((external_token, fixed))
    def fingerprint(supplied):
        if packed((private, initial, anchor, demand, policy,
                   lambda_p, lambda_uf, target_np_veh, target_nuf_veh_h, horizon_steps,
                   np_tolerance_veh, nuf_tolerance_veh_h)) != fixed:
            raise ValueError('Private fixed game inputs changed')
        observed = context_fingerprint(supplied)
        if observed != external_token:
            raise ValueError('External fixed game context changed')
        return fixed_context_identity

    cache = {}
    batch_context_token = None
    scheduled = None
    stats = {'requests': 0, 'endpoint_calls': 0, 'cache_hits': 0,
             'endpoint_sec': 0., 'local_score_sec': 0., 'price_sec': 0., 'query_sec': 0.}
    def command_query(callback, action, supplied):
        trial = copy.deepcopy(action)
        before = packed(trial)
        with shared_query_runtime_scope():
            value = callback(trial, supplied)
        if packed(trial) != before:
            raise ValueError('Command serialization changed its supplied full action')
        fingerprint(supplied)
        return value
    def evaluate(owner, action, supplied):
        nonlocal batch_context_token, private, initial, anchor, demand, policy
        fingerprint(supplied)
        stats['requests'] += 1
        key = packed(action)
        if key not in cache:
            if deadline_check is not None:
                deadline_check('follower_physical_response')
            tick = perf_counter()
            # These inputs are already solve-owned private copies. Recopying the
            # whole follower/config/state for every unique candidate is redundant
            # when the batch's exact frozen-input guard succeeds. The candidate
            # remains independently copied, including all diagnostic payload.
            try:
                batch = (response_query((action,)) if response_query is not None else
                    _evaluate_shared_owner_batch_owned(private, initial, anchor, demand,
                        (copy.deepcopy(action),), horizon_steps=horizon_steps))
            except BaseException:
                # Preserve the old public-batch isolation on failures too. A
                # successful-but-mutating endpoint is rejected by the guard;
                # recover private inputs before core records that failure. The
                # original caller objects were never passed to the endpoint.
                # A separate response worker cannot have changed these local
                # objects merely by timing out. Unpickling an unchanged graph
                # can itself change its alias/reduction encoding and invalidate
                # the exact context witness needed to return a checked action.
                if packed((private, initial, anchor, demand, policy,
                           lambda_p, lambda_uf, target_np_veh, target_nuf_veh_h, horizon_steps,
                           np_tolerance_veh, nuf_tolerance_veh_h)) != fixed:
                    private, initial, anchor, demand, policy = pickle.loads(fixed)[:5]
                raise
            stats['query_sec'] += perf_counter() - tick
            stats['endpoint_calls'] += batch['endpoint_calls']
            stats['endpoint_sec'] += batch['endpoint_sec']
            stats['local_score_sec'] += batch['score_sec']
            item = batch['results'][0]
            if item['action_token'] != hashlib.sha256(key).hexdigest():
                raise ValueError('Shared response is bound to another full action')
            if batch_context_token is None:
                batch_context_token = item['frozen_context_token']
            elif batch_context_token != item['frozen_context_token']:
                raise ValueError('Candidate queries used different fixed model inputs')
            if set(item['local_base_costs']) != set(owners):
                raise ValueError('Incomplete common-response local payoff catalog')
            tick = perf_counter()
            with shared_query_runtime_scope():
                additions = fixed_joint_price_terms(private, action, item['quantities'],
                    lambda_p=lambda_p, lambda_uf=lambda_uf, target_np_veh=target_np_veh,
                    target_nuf_veh_h=target_nuf_veh_h, price_context=policy)
            if set(additions['owners']) != set(owners):
                raise ValueError('Incomplete fixed-price owner catalog')
            costs = {who: float(item['local_base_costs'][who] + additions['owners'][who]['total'])
                     for who in owners}
            if not all(math.isfinite(value) for value in costs.values()):
                raise ValueError('Nonfinite fixed-game owner payoff')
            quantity_constraints = shared_quantity_constraints(private, action, item['quantities'],
                np_mode=policy['np_mode'], target_np_veh=target_np_veh,
                np_tolerance_veh=np_tolerance_veh, nuf_mode=policy['nuf_mode'],
                target_nuf_veh_h=target_nuf_veh_h, nuf_tolerance_veh_h=nuf_tolerance_veh_h,
                start_sec=initial.time_sec, horizon_steps=horizon_steps)
            fingerprint(supplied)
            item.update(owner_costs=costs, additive_terms=additions, quantity_constraints=quantity_constraints,
                        physical_owner_tokens=command_query(callbacks['physical_fingerprint'], action, supplied))
            cache[key] = packed(item)
            stats['price_sec'] += perf_counter() - tick
        else:
            stats['cache_hits'] += 1
        item = pickle.loads(cache[key])
        if scheduled is not None:
            scheduled.note_read(action)
        coverage = item.get('model_constraint_coverage')
        witnessed = (item.get('conditional_model_feasibility_witness') is True
                     and isinstance(coverage, dict) and coverage.get('complete') is True)
        violation = item['resource_summary']['max_exceedance_veh']
        feasible = witnessed and violation <= shared_tolerance and item['quantity_constraints']['feasible'] is True
        reason = None
        if not witnessed:
            reason = 'Implemented model constraint coverage is incomplete'
        elif violation > shared_tolerance:
            reason = 'Accepted allocation exceeds an implemented model limit'
        elif not item['quantity_constraints']['feasible']:
            reason = 'Frozen leader quantity constraint violated: ' + repr(item['quantity_constraints'])
        result = game.Evaluation(feasible=feasible,
            cost=item['owner_costs'][owner], shared_violation=violation,
            witness_complete=witnessed, reason=reason)
        if progress is not None:
            progress({'stage': 'joint_candidate_evaluated', 'owner': owner,
                'requests': stats['requests'], 'endpoint_calls': stats['endpoint_calls'],
                'cache_hits': stats['cache_hits'], 'feasible': feasible,
                'witness_complete': witnessed})
        return result

    started = perf_counter()
    seed_incumbent = copy.deepcopy(incumbent) if restoration_policy is not None else None
    restoration = None
    if restore_initializer:
        def feasibility(action, supplied):
            checked = evaluate(owners[0], action, supplied)
            item = pickle.loads(cache[packed(action)])
            quantity = item['quantity_constraints']
            # Fixed dimensionless scales, not a sum of vehicles and veh/h.
            np_excess = max(0., quantity['np']['actual'] - target_np_veh - np_tolerance_veh)
            nuf_excess = max(0., abs(quantity['nuf']['actual'] - target_nuf_veh_h) - nuf_tolerance_veh_h)
            merit = (np_excess/max(1., abs(target_np_veh))
                     + nuf_excess/max(1., abs(target_nuf_veh_h))
                     + max(0., checked.shared_violation-shared_tolerance))
            return game.RestorationEvaluation(checked.feasible, merit, checked.witness_complete, checked.reason)
        restore_evaluations, restore_time = max_evaluations, time_budget_sec
        if restoration_policy is not None:
            restore_evaluations = min(max_evaluations, restoration_policy['restoration_max_evaluations'])
            restore_time = min(time_budget_sec, restoration_policy['restoration_time_budget_sec']) if time_budget_sec is not None else restoration_policy['restoration_time_budget_sec']
        restoration = game.restore_feasibility(callbacks['ownership'], incumbent, context,
            neighbors=callbacks['neighbors'], evaluate=feasibility, context_fingerprint=fingerprint,
            physical_fingerprint=callbacks['physical_fingerprint'], max_evaluations=restore_evaluations,
            time_budget_sec=restore_time, deadline_check=deadline_check, initial_seeds=initial_seeds,
            max_sweeps=max_sweeps, improvement_tolerance=improvement_tolerance,
            scope_label='Fixed-target, fixed-box initializer feasibility restoration', nuf_semantics=nuf_semantics)
        if restoration.get('control') is not None:
            incumbent = restoration['control']
        elif restoration.get('best_infeasible') is not None:
            incumbent = restoration['best_infeasible']
    remaining_evaluations = max(0, max_evaluations-(restoration['evaluations'] if restoration else 0))
    if restoration_policy is not None and restoration is not None and not restoration['feasible']:
        # Keep the existing checked infeasible witness; do not spend a second
        # game budget trying to score the same failed initializer again.
        remaining_evaluations = 0
    game_neighbors = callbacks['neighbors']
    from evaluation.controllers.area_runtime import response_scheduling_options
    scheduling = response_scheduling_options(getattr(private.cfg.network, 'control_area_response_scheduling', None))
    prefetch_enabled = getattr(private.cfg.network, 'control_area_prefetch_first_owner_responses', False)
    full_prefetch = getattr(private.cfg.network, 'control_area_prefetch_complete_sweep_responses', False)
    if scheduling is not None:
        if (traversal not in ('round_robin', 'round_robin_balanced') or full_prefetch
                or response_query is None or not callable(getattr(response_query, 'stats', None))
                or response_query.stats().get('cache_enabled') is not True
                or response_query.stats().get('parallel_workers', 0) < 1):
            raise ValueError('Bounded scheduling requires round-robin and the existing parallel response cache')
        prefetch_enabled = False
        scheduled = _make_bounded_response_schedule(callbacks['ownership'], neighbors=callbacks['neighbors'],
            physical_fingerprint=lambda action, supplied: command_query(callbacks['physical_fingerprint'], action, supplied),
            response_query=response_query, fingerprint=fingerprint, traversal=traversal,
            nuf_semantics=nuf_semantics,
            lookahead=min(scheduling['lookahead'], response_query.stats()['parallel_workers']))
        game_neighbors = scheduled.neighbors
    if type(full_prefetch) is not bool:
        raise ValueError('Complete-sweep response prefetch must be boolean')
    if full_prefetch and (time_budget_sec is not None or traversal not in ('round_robin', 'round_robin_balanced')
            or response_query is None or not callable(getattr(response_query, 'stats', None))
            or response_query.stats().get('parallel_workers', 0) < 2
            or response_query.stats().get('cache_enabled') is not True):
        raise ValueError('Complete-sweep prefetch requires unlimited time, round-robin and parallel response cache')
    if full_prefetch and remaining_evaluations >= 2*len(owners)+1:
        batch_size = response_query.stats()['parallel_workers']
        prefetch = {'batch_size': batch_size, 'prepared_bases': 0, 'completed_bases': 0,
            'completed_batches': 0, 'requested_responses': 0, 'endpoint_calls': 0,
            'skipped_insufficient_evaluation_budget': 0, 'wall_sec': 0.,
            'selection_or_domain_changed': False, 'scoring_and_feasibility_remain_in_game': True}
        domains, base_key = {}, None
        game_request_start = stats['requests']
        def complete_sweep_neighbors(owner, action, supplied):
            nonlocal domains, base_key
            fingerprint(supplied)
            key = packed(action)
            if key == base_key:
                return copy.deepcopy(domains[owner])
            started_batch = perf_counter()
            base_key, domains = key, {}
            try:
                for who in owners:
                    trial = copy.deepcopy(action); before_trial = packed(trial)
                    domain = callbacks['neighbors'](who, trial, supplied)
                    fingerprint(supplied)
                    if packed(trial) != before_trial:
                        raise ValueError('Prefetch neighbor producer changed its supplied incumbent')
                    if (not isinstance(domain, game.Neighborhood) or type(domain.candidates) is not tuple
                            or domain.complete is not True or type(domain.domain_label) is not str or not domain.domain_label):
                        raise ValueError('Complete-sweep prefetch requires complete materialized neighborhoods')
                    domains[who] = domain
                prefetch['prepared_bases'] += 1
                # Conservative bound includes even duplicate candidates plus
                # every owner's incumbent check. Never spend physical queries
                # for a sweep that the remaining evaluation cap cannot finish.
                needed = len(owners) + sum(len(domain.candidates) for domain in domains.values())
                left = remaining_evaluations - (stats['requests']-game_request_start)
                if left < needed:
                    prefetch['skipped_insufficient_evaluation_budget'] += 1
                    return copy.deepcopy(domains[owner])
                def physical_key(candidate):
                    value = command_query(callbacks['physical_fingerprint'], candidate, supplied)
                    if (not isinstance(value, dict) or set(value) != set(owners)
                            or any(type(value[who]) not in (str, bytes) or not value[who] for who in owners)):
                        raise ValueError('Prefetch physical fingerprint must cover every owner')
                    return tuple((who, type(value[who]).__name__,
                        value[who].hex() if type(value[who]) is bytes else value[who]) for who in owners)
                physical_base = physical_key(action)
                initial_key = (game._action_key(callbacks['ownership'], action), physical_base)
                candidates = {}
                for who, domain in domains.items():
                    seen, candidates[who] = {initial_key}, []
                    for candidate in domain.candidates:
                        game.validate_action_addresses(callbacks['ownership'], candidate)
                        game.validate_nuf_semantics(candidate, nuf_semantics)
                        game.assert_owner_transition(callbacks['ownership'], who, action, candidate)
                        if game._extra(candidate, nuf_semantics=nuf_semantics) != game._extra(action, nuf_semantics=nuf_semantics):
                            raise ValueError('Prefetch candidate changed a fixed target or nonlever payload')
                        physical = physical_key(candidate)
                        if any(new != old for new, old in zip(physical, physical_base) if new[0] != who):
                            raise ValueError('Prefetch candidate changed a foreign physical command')
                        candidate_key = (game._action_key(callbacks['ownership'], candidate), physical)
                        if candidate_key not in seen:
                            seen.add(candidate_key); candidates[who].append(candidate)
                ordered = [candidates[who][i] for i in range(max(map(len, candidates.values()), default=0))
                           for who in owners if i < len(candidates[who])]
                for first in range(0, len(ordered), batch_size):
                    probes = tuple(copy.deepcopy(ordered[first:first+batch_size]))
                    before_probes = packed(probes)
                    if deadline_check is not None:
                        deadline_check('complete_sweep_response_preparation')
                    query_start = perf_counter()
                    result = response_query(probes)
                    stats['query_sec'] += perf_counter()-query_start
                    if packed(probes) != before_probes:
                        raise ValueError('Prefetch response query changed its supplied actions')
                    fingerprint(supplied)
                    stats['endpoint_calls'] += result['endpoint_calls']
                    stats['endpoint_sec'] += result['endpoint_sec']
                    stats['local_score_sec'] += result['score_sec']
                    prefetch['requested_responses'] += len(probes)
                    prefetch['endpoint_calls'] += result['endpoint_calls']
                    prefetch['completed_batches'] += 1
                    if progress is not None:
                        progress({'stage': 'joint_response_prefetch_completed', 'responses': len(probes),
                            'endpoint_calls': result['endpoint_calls'], 'feasibility_not_yet_scored': True})
                prefetch['completed_bases'] += 1
                return copy.deepcopy(domains[owner])
            finally:
                prefetch['wall_sec'] += perf_counter()-started_batch
        game_neighbors = complete_sweep_neighbors
        stats['complete_sweep_prefetch'] = prefetch
    if (not full_prefetch and prefetch_enabled and traversal in ('round_robin', 'round_robin_balanced') and response_query is not None
            and callable(getattr(response_query, 'stats', None))
            and response_query.stats().get('parallel_workers', 0) > 1
            and remaining_evaluations >= 2*len(owners)+1):
        # Warm only one worker-sized group ahead of the round-robin traversal.
        # Waiting for every owner at once can consume the deadline before the
        # game uses any completed response. Domains and adoption stay unchanged.
        batch_size = response_query.stats()['parallel_workers']
        prefetch = {'owners': [], 'domain_sizes': {}, 'requested_responses': 0,
                    'completed': False, 'completed_batches': 0, 'timed_out': False,
                    'batch_size': batch_size, 'wall_sec': 0.,
                    'selection_or_domain_changed': False}
        domains = {}
        base_key = packed(incumbent)
        def prepared_neighbors(owner, action, supplied):
            fingerprint(supplied)
            if packed(action) != base_key:
                return callbacks['neighbors'](owner, action, supplied)
            if owner in domains:
                return copy.deepcopy(domains[owner])
            started_batch = perf_counter()
            probes = []
            try:
                physical_base = command_query(callbacks['physical_fingerprint'], action, supplied)
                first = owners.index(owner)
                for next_owner in owners[first:first+batch_size]:
                    if next_owner in domains:
                        continue
                    if deadline_check is not None:
                        deadline_check('first_owner_response_preparation')
                    domain = callbacks['neighbors'](next_owner, copy.deepcopy(action), supplied)
                    if not isinstance(domain, game.Neighborhood) or not domain.complete:
                        raise ValueError('First-owner prefetch needs the complete unchanged neighborhood')
                    domains[next_owner] = domain
                    prefetch['domain_sizes'][next_owner] = len(domain.candidates)
                    for candidate in domain.candidates:
                        if game._action_key(callbacks['ownership'], candidate) == game._action_key(callbacks['ownership'], action):
                            continue
                        game.assert_owner_transition(callbacks['ownership'], next_owner, action, candidate)
                        if game._extra(candidate, nuf_semantics=nuf_semantics) != game._extra(action, nuf_semantics=nuf_semantics):
                            raise ValueError('Prefetch candidate changed a fixed target or nonlever payload')
                        physical = command_query(callbacks['physical_fingerprint'], candidate, supplied)
                        if any(physical[who] != physical_base[who] for who in owners if who != next_owner):
                            raise ValueError('Prefetch candidate changed a foreign physical command')
                        probes.append(candidate)
                        prefetch['owners'].append(next_owner)
                        break
                if probes:
                    prefetch['requested_responses'] += len(probes)
                    # Results stay in the existing exact full-action cache.
                    # Owner costs/constraints and adoption remain in the game.
                    response_query(tuple(probes))
                prefetch['completed_batches'] += 1
                prefetch['completed'] = len(domains) == len(owners)
                return copy.deepcopy(domains[owner])
            except TimeoutError:
                prefetch['timed_out'] = True
                raise
            finally:
                prefetch['wall_sec'] += perf_counter()-started_batch
        game_neighbors = prepared_neighbors
        stats['first_owner_prefetch'] = prefetch
    remaining_time = (max(0., time_budget_sec-(perf_counter()-started))
        if time_budget_sec is not None and (restore_initializer or prefetch_enabled or scheduling is not None) else time_budget_sec)
    decision_remaining = (max(0., decision_deadline_monotonic-perf_counter())
        if scheduling is not None and decision_deadline_monotonic is not None else None)
    result = game.solve(callbacks['ownership'], incumbent, context,
        neighbors=game_neighbors, evaluate=evaluate,
        context_fingerprint=fingerprint, physical_fingerprint=callbacks['physical_fingerprint'],
        max_sweeps=max_sweeps, max_evaluations=remaining_evaluations, time_budget_sec=remaining_time,
        improvement_tolerance=improvement_tolerance, shared_tolerance=shared_tolerance,
        scope_label=scope_label, nuf_semantics=nuf_semantics, traversal=traversal,
        deadline_check=deadline_check,
        **({'before_evaluate': scheduled,
            'final_check_reserve_sec': scheduling['final_check_reserve_sec'],
            **({'decision_time_remaining_sec': decision_remaining} if decision_remaining is not None else {})}
            if scheduled is not None else {}))
    if scheduled is not None:
        stats['bounded_response_schedule'] = scheduled.report(result['evaluations'])
    stats['solve_wall_sec'] = perf_counter() - started
    stats['retained_result_bytes'] = sum(len(key) + len(value) for key, value in cache.items())
    final = result['control']
    final_score = pickle.loads(cache[packed(final)]) if packed(final) in cache else None
    # These are serialization-only checks. Never rescore an unvisited final
    # incumbent or change a command after the cooperative game deadline.
    fingerprint(context)
    physical = command_query(callbacks['physical_fingerprint'], final, context)
    evidence = command_query(callbacks['command_evidence'], final, context)
    if callable(callbacks.get('validate_move_box')):
        evidence['fixed_move_box'] = callbacks['validate_move_box'](final)
    if final_score is not None and physical != final_score['physical_owner_tokens']:
        raise ValueError('Final written command differs from the scored full action')
    fingerprint(context)
    extra = {'initializer_restoration': restoration, 'restored_initial': incumbent} if restore_initializer else {}
    if restoration_policy is not None:
        seed_checks = []
        for index, seed in enumerate((seed_incumbent, *initial_seeds)):
            raw_seed = cache.get(packed(seed))
            row = {'seed_index': index, 'action_token': token(seed), 'evaluated': raw_seed is not None}
            if raw_seed is not None:
                observed = pickle.loads(raw_seed)
                q = observed['quantity_constraints']
                row.update(np_veh=q['np']['actual'], nuf_veh_h=q['nuf']['actual'],
                    nuf_satisfied=q['nuf']['satisfied'], target_cap_satisfied=q['np']['satisfied'],
                    model_and_writer_validated=(observed.get('conditional_model_feasibility_witness') is True
                        and observed['model_constraint_coverage'].get('complete') is True
                        and observed['resource_summary']['max_exceedance_veh'] <= shared_tolerance),
                    accepted_as_initializer=bool(restoration and restoration['feasible'] and packed(seed)==packed(incumbent)))
            seed_checks.append(row)
        extra['initializer_seed_checks'] = seed_checks
    return {'game': result, 'final_score': final_score, 'command_evidence': evidence, **extra,
            'queries': stats, 'fixed_inputs_token': hashlib.sha256(fixed).hexdigest(),
            'final_action_token': token(final),
            'price_refresh_performed': False, 'leader_or_dual_update_performed': False,
            'native_plant_feasibility_certified': False,
            'shared_violation_scalar_scope': 'Traffic allocation exceedance in vehicles; leader NP/NUF residuals and tolerances are reported separately in final_score.quantity_constraints',
            'scope': 'Finite fixed-price 19-owner selection conditional on implemented model constraints; no native or price-fixed-point certificate'}


def install_runtime(cfg):
    if not enabled(cfg):
        if hasattr(cfg.mpc, "_control_area_fallback_ttt_before"):
            cfg.mpc.stackelberg_fallback_guard_use_rollout_ttt = cfg.mpc._control_area_fallback_ttt_before
            del cfg.mpc._control_area_fallback_ttt_before
        return {}
    if not hasattr(cfg.mpc, "_control_area_fallback_ttt_before"):
        cfg.mpc._control_area_fallback_ttt_before = cfg.mpc.stackelberg_fallback_guard_use_rollout_ttt
    # Its existing objective comparator handles negative J additively and keeps
    # severe terminal/completion checks. Avoid a second, global-TTT veto.
    cfg.mpc.stackelberg_fallback_guard_use_rollout_ttt = False
    from src.controllers.wu_faithful_follower import WuFaithfulFollower
    cls = WuFaithfulFollower
    if getattr(cls._rollout_horizon_ttt, "_control_area_follower_objective", False):
        return {"control_area_follower_objective_installed": 1.0, "control_area_fallback_uses_objective": 1.0}
    original_rollout = cls._rollout_horizon_ttt
    original_solve = cls.solve

    def rollout(self, state, control, forecast):
        if not enabled(self.cfg):
            return original_rollout(self, state, control, forecast)
        _finalize_link_phases(self, control, state, forecast)
        from evaluation.controllers import area_meter_finalization
        area_meter_finalization.finalize(control, self.cfg)
        from src.controllers.rollout_endpoint import ObjectiveSpec, evaluate_price_point
        point = evaluate_price_point(state, control, forecast, (), ObjectiveSpec(
            cfg=self.cfg, depth_override=max(1, int(self.cfg.mpc.horizon_steps)),
            box_walk=False, score_mode="raw", split_ttt=True))
        area = getattr(point, "control_area", None)
        if not isinstance(area, dict):
            raise ValueError("Omega follower requires the canonical area endpoint")
        values = {
            "objective_veh_h": float(point.objective),
            "ttt_veh_h": float(area["ttt_veh_h"]),
            "ttd_veh": float(area["ttd_veh"]),
            "near_score_veh_h": float(area["near_score_veh_h"]),
            "additional_cost_veh_h": float(area["additional_cost_veh_h"]),
            "global_freeway_ttt_veh_h": float(point.freeway_ttt),
            "global_urban_ttt_veh_h": float(point.urban_ttt),
        }
        if not all(math.isfinite(v) for v in values.values()):
            raise ValueError("nonfinite Omega follower endpoint result")
        control.diagnostics.update({"control_area_follower_" + k: v for k, v in values.items()})
        events = getattr(self, "_control_area_follower_events", None)
        if events is not None:
            events.append(values)
        # The first component is a ranking score in Omega mode. The two split
        # components retain their global TTT meaning; never reward TD twice.
        return values["objective_veh_h"], values["global_freeway_ttt_veh_h"], values["global_urban_ttt_veh_h"]

    def solve(self, *args, **kwargs):
        if not enabled(self.cfg):
            return original_solve(self, *args, **kwargs)
        absent = object()
        previous_events = getattr(self, "_control_area_follower_events", absent)
        previous_margin = self.offset_keep_margin
        self._control_area_follower_events = events = []
        # A relative threshold on possibly negative TTT-beta*TD is invalid.
        # The existing guard now retains only a strict J improvement (>1e-9).
        self.offset_keep_margin = 0.0
        try:
            result = original_solve(self, *args, **kwargs)
        finally:
            self.offset_keep_margin = previous_margin
            if previous_events is absent:
                del self._control_area_follower_events
            else:
                self._control_area_follower_events = previous_events
        if not events:
            raise ValueError("Omega follower solve produced no canonical endpoint score")
        final = events[-1]
        diagnostics = result.control.diagnostics
        diagnostics["distributed_response_rollout_ttt"] = final["global_freeway_ttt_veh_h"] + final["global_urban_ttt_veh_h"]
        diagnostics["control_area_follower_objective_active"] = 1.0
        diagnostics["control_area_offset_keep_margin"] = 0.0
        # The canonical solve invokes on/off twice only when its offset guard
        # runs, then evaluates the chosen result once. Preserve honest TTT labels
        # and expose the score that actually governed retention separately.
        guard_ran = len(events) == 3 and "wu_faithful_offset_ttt_on" in diagnostics
        if guard_ran:
            for suffix, values in zip(("on", "off"), events[:2]):
                diagnostics["wu_faithful_offset_ttt_" + suffix] = values["global_freeway_ttt_veh_h"] + values["global_urban_ttt_veh_h"]
                for key in ("objective_veh_h", "ttt_veh_h", "ttd_veh"):
                    diagnostics["control_area_offset_" + suffix + "_" + key] = values[key]
        elif "wu_faithful_offset_ttt_on" in diagnostics or "wu_faithful_offset_ttt_off" in diagnostics:
            raise ValueError("unrecognized Omega offset guard endpoint sequence")
        diagnostics["control_area_offset_guard_evaluated"] = float(guard_ran)
        result.diagnostics.update(diagnostics)
        return result

    rollout._control_area_follower_objective = True
    solve._control_area_follower_objective = True
    cls._rollout_horizon_ttt = rollout
    cls.solve = solve
    return {"control_area_follower_objective_installed": 1.0, "control_area_fallback_uses_objective": 1.0}


def install_controller(controller):
    """Called by the canonical builder; workers also reinstall from their cfg."""
    metadata = install_runtime(controller.cfg)
    if enabled(controller.cfg):
        _install_link_phase_finalization()
        metadata["control_area_link_phase_finalization_installed"] = 1.0
    return metadata


def _finalize_link_phases(self, control, state, forecast):
    context = getattr(self, "_control_area_link_phase_context", None)
    if context is None:
        return
    if control.diagnostics.get("_control_area_phase_token") == context["token"]:
        if dict(control.green_times) != context["greens"]:
            raise ValueError("Omega scored phase vector changed after finalization")
        return
    before = dict(control.green_times)
    source = "none"
    if self.phase_price_in_gne:
        from src.models.state import phase_key
        for signal, vector in (getattr(self, "_gne_phase_override", None) or {}).items():
            for phase, value in vector.items():
                key = phase_key(signal, phase)
                if key in control.green_times:
                    control.green_times[key] = float(value)
        source = "gne_commit"
    elif self.signal_phase_price:
        # Calls the currently installed canonical refinement chain once, with
        # the same demand that the outer Link.solve would pass to it.
        context["refined_count"] = self.apply_phase_price_refinement(control, state, context["demand"])
        source = "phase_refinement"
    from evaluation.controllers import signal_actuation_contract
    if signal_actuation_contract.enabled(self.cfg.network):
        signal_actuation_contract.validate_control(control, self.cfg)
    context["greens"] = dict(control.green_times)
    control.diagnostics["_control_area_phase_token"] = context["token"]
    control.diagnostics["control_area_phase_finalized_before_score"] = 1.0
    control.diagnostics["control_area_phase_finalization_source"] = source
    control.diagnostics["control_area_phase_finalized_changed_values"] = float(sum(
        before.get(key) != value for key, value in control.green_times.items()))


def _install_link_phase_finalization():
    from src.controllers.priced_wu_link_controller import LinkAgentWuFollower
    cls = LinkAgentWuFollower
    if getattr(cls.solve, "_control_area_link_phase_finalization", False):
        return
    original_solve = cls.solve
    original_refine = cls.apply_phase_price_refinement

    def refine(self, control, state, demand=None):
        context = getattr(self, "_control_area_link_phase_context", None)
        if (enabled(self.cfg) and context is not None and
                control.diagnostics.get("_control_area_phase_token") == context["token"]):
            if dict(control.green_times) != context["greens"]:
                raise ValueError("Omega outer phase vector differs from scored vector")
            return context.get("refined_count", 0)
        return original_refine(self, control, state, demand)

    def solve(self, state, leader, demand, *args, **kwargs):
        if not enabled(self.cfg):
            return original_solve(self, state, leader, demand, *args, **kwargs)
        absent = object()
        previous = getattr(self, "_control_area_link_phase_context", absent)
        context = {"demand": demand}
        # The diagnostics string survives ControlAction.copy for the zero arm;
        # the scope exists only for this solve and is restored on every exit.
        context["token"] = str(id(context))
        self._control_area_link_phase_context = context
        try:
            result = original_solve(self, state, leader, demand, *args, **kwargs)
            if "greens" not in context or dict(result.control.green_times) != context["greens"]:
                raise ValueError("Omega Link returned an unscored final phase vector")
            result.control.diagnostics["control_area_phase_outer_matches_scored"] = 1.0
            result.control.diagnostics.pop("_control_area_phase_token", None)
            result.diagnostics.pop("_control_area_phase_token", None)
            result.diagnostics.update(result.control.diagnostics)
            return result
        finally:
            if previous is absent:
                del self._control_area_link_phase_context
            else:
                self._control_area_link_phase_context = previous

    solve._control_area_link_phase_finalization = True
    cls.apply_phase_price_refinement = refine
    cls.solve = solve
