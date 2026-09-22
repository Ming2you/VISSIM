"""Fresh-process entry point. Only local, parent-created pickle files are read."""
from __future__ import annotations
import copy
import hashlib
import math
import pickle
import sys
import time
import traceback
from collections import deque
from types import ModuleType
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]


def state_error(a, b, path='states', seen=None):
    """Compare every stored state field, including physical runtime objects.

Packed audit lists are unwrapped only at their known ledger field. No field
containing a model stock, cohort, velocity, queue, clock or transfer is omitted.
"""
    import numbers
    import numpy as np
    from evaluation.controllers.sdmpc_dual import Dual, primal
    seen = set() if seen is None else seen
    if isinstance(a, (numbers.Real, Dual)) and isinstance(b, (numbers.Real, Dual)):
        aa, bb = primal(a), primal(b)
        if aa == bb:
            return 0.
        if not math.isfinite(aa) or not math.isfinite(bb):
            raise ValueError('Nonfinite or mismatched state: '+path)
        return abs(aa-bb)
    if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
        if a.shape != b.shape:
            raise ValueError('State array shape mismatch: '+path)
        return state_error(a.tolist(), b.tolist(), path, seen)
    if isinstance(a, ModuleType) or callable(a):
        # Runtime objects retain references to the installed adapter/module.
        # Source identity is checked separately; traversing sys.modules would
        # compare the interpreter rather than traffic state (and its NaNs).
        if a is not b:
            raise ValueError('State model-code identity mismatch: '+path)
        return 0.
    if isinstance(a, dict) and isinstance(b, dict):
        if a.keys() != b.keys():
            raise ValueError('State keys mismatch: '+path)
        return max((state_error(a[k], b[k], path+'.'+str(k), seen) for k in a), default=0.)
    if isinstance(a, (tuple, list, deque)) and isinstance(b, type(a)):
        if path.endswith('.transfers'):
            # Sparse zero-sized transfers may disappear at float roundoff.
            # Compare every additive ledger quantity on the exact route/clock;
            # do not drop small events or change either prediction's evidence.
            from collections import defaultdict
            amounts = ('vehicles','ttd_veh','entered_veh')
            identities = ('stage','start_sec','end_sec','source','target','route_key')
            def grouped(rows):
                groups = defaultdict(lambda: {k:[] for k in amounts})
                for row in rows:
                    if set(row) != set(amounts+identities):
                        raise ValueError('Unknown transfer schema in state comparison: '+path)
                    key = tuple(row[k] for k in identities)
                    for name in amounts:
                        groups[key][name].append(primal(row[name]))
                return {k:{name:math.fsum(values) for name,values in v.items()} for k,v in groups.items()}
            aa,bb = grouped(a),grouped(b)
            zero = dict.fromkeys(amounts,0.)
            return max((state_error(aa.get(k,zero),bb.get(k,zero),path+'.route',seen)
                        for k in aa.keys()|bb.keys()),default=0.)
        if len(a) != len(b):
            import itertools
            def brief(row):
                if isinstance(row,dict):
                    return {k:primal(v) if isinstance(v,(numbers.Real,Dual)) else v
                            for k,v in row.items() if k in ('vehicles','route_key','start_sec','end_sec','source','target','stage')}
                return type(row).__name__
            first = next((i for i,(x,y) in enumerate(zip(a,b)) if brief(x)!=brief(y)), min(len(a),len(b)))
            context = [(brief(x),brief(y)) for x,y in itertools.islice(zip(a,b),max(0,first-1),first+2)]
            raise ValueError(f'State sequence length mismatch: {path}; {len(a)} vs {len(b)}; first={first}; {context}')
        if path.endswith('._packed_response_records'):
            return state_error([pickle.loads(v) for v in a], [pickle.loads(v) for v in b], path+'.unpacked', seen)
        return max((state_error(x, y, path+f'[{i}]', seen) for i, (x, y) in enumerate(zip(a, b))), default=0.)
    if hasattr(a, '__dict__') and type(a) is type(b) and not callable(a):
        pair = (id(a), id(b))
        if pair in seen:
            return 0.
        seen.add(pair)
        if type(a).__name__ == 'ModelAreaLedger' and hasattr(a,'_response'):
            def captured_count(ledger):
                return len(ledger._response['transfers'])+sum(len(pickle.loads(v)['transfers'])
                    for v in getattr(ledger,'_packed_response_records',()))
            # The counter is derived from the sparse records. Verify that any
            # uncaptured prefix is identical, then compare all transfer masses
            # below. Do not treat a rounded-away 1e-15 vehicle as a two-vehicle
            # state error merely because two log entries disappeared.
            if a.event_count-captured_count(a) != b.event_count-captured_count(b):
                raise ValueError('Unexplained ledger event counter mismatch: '+path)
            return state_error({k:v for k,v in vars(a).items() if k!='event_count'},
                {k:v for k,v in vars(b).items() if k!='event_count'},path,seen)
        return state_error(vars(a), vars(b), path, seen)
    if hasattr(type(a), '__slots__') and type(a) is type(b):
        slots = type(a).__slots__
        if isinstance(slots, str):
            slots = (slots,)
        return max((state_error(getattr(a, k), getattr(b, k), path+'.'+k, seen)
                    for k in slots), default=0.)
    if a is b or (type(a) is type(b) and a == b):
        return 0.
    raise ValueError('Unsupported or mismatched state field: '+path+' '+type(a).__name__)


def run(request, finder, progress):
    ad = finder.ad
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers.runtime_setup import install_worker_runtime
    from evaluation.controllers import area_follower_objective as joint
    from evaluation.controllers import area_leader_objective as constraints
    from evaluation.controllers.sdmpc import omega_costs
    from src.controllers import rollout_endpoint
    import numpy as np

    follower, state, reference, forecast = request['owned']
    cfg = follower.cfg
    reverse = cfg.network.sdmpc_options.get('tangent_backend') == 'reverse-v1'
    surrogate_mode = request.get('surrogate_evaluation')
    if surrogate_mode is not None:
        if (not cfg.network.sdmpc_options.get('surrogate_reuse') or not reverse
                or surrogate_mode not in ('ad', 'scalar')
                or any(name in request for name in ('shared_primal', 'shared_primal_stdin', 'scalar_output', 'diagnostic_checkpoint'))):
            raise ValueError('Invalid continuous candidate reuse request')
        from evaluation.controllers import sdmpc_tangent_surrogate
        filename = str(Path(sdmpc_tangent_surrogate.__file__).resolve())
        finder.source_hashes[filename] = hashlib.sha256(Path(filename).read_bytes()).hexdigest()
    skip_scalar_witness = surrogate_mode == 'ad'
    reverse_workers=cfg.network.sdmpc_options.get('derivative_workers',1)
    if 'reverse_worker_limit' in request:
        limit=request['reverse_worker_limit']
        if (not (cfg.network.sdmpc_options.get('initial_derivative_overlap') or surrogate_mode) or not reverse
                or type(limit) is not int or not 1<=limit<reverse_workers<=8):
            raise ValueError('Invalid overlapped reverse worker limit')
        reverse_workers=limit
    if finder.backend != cfg.network.sdmpc_options.get('tangent_backend', 'forward'):
        raise ValueError('Tangent backend does not match the frozen request')
    if reverse:
        if 'column_indices' in request or request.get('diagnostic_checkpoint'):
            raise ValueError('Reverse mode requires one complete tape; cross-process tape checkpoints are unsupported')
        filename = str(Path(ad.__file__).resolve())
        finder.source_hashes[filename] = hashlib.sha256(Path(filename).read_bytes()).hexdigest()
    shared_mode = cfg.network.sdmpc_options.get('tangent_shared_primal', False)
    deferred = request.get('shared_primal_stdin', False)
    if deferred and (not reverse or not shared_mode or
            not cfg.network.sdmpc_options.get('tangent_concurrent_primal')):
        raise ValueError('Deferred scalar witness requires explicit concurrent reverse mode')
    if cfg.network.sdmpc_options.get('tangent_concurrent_primal'):
        from evaluation.controllers import sdmpc_tangent_concurrent
        filename = str(Path(sdmpc_tangent_concurrent.__file__).resolve())
        finder.source_hashes[filename] = hashlib.sha256(Path(filename).read_bytes()).hexdigest()
    immutable_audit = cfg.network.sdmpc_options.get('immutable_audit', False)
    if immutable_audit:
        from evaluation.controllers import sdmpc_tangent_records
        filename = str(Path(sdmpc_tangent_records.__file__).resolve())
        finder.source_hashes[filename] = hashlib.sha256(Path(filename).read_bytes()).hexdigest()
    if (request.get('shared_primal') or request.get('scalar_output')) and not shared_mode:
        raise ValueError('Shared primal requires the explicit controller option')
    bootstrap = request['bootstrap']
    for name, expected in bootstrap['runtime_sources'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
            raise ValueError('Tangent source changed: '+name)
    frozen = pickle.dumps(request['owned'], protocol=5)
    install_worker_runtime(adapter, cfg, bootstrap['state_json'], bootstrap['detector_mapping'])
    if frozen != pickle.dumps(request['owned'], protocol=5):
        raise ValueError('Tangent bootstrap changed frozen model operands')
    from evaluation.controllers.sdmpc_continuous import install as install_continuous
    install_continuous(cfg)
    if cfg.network.sdmpc_options.get('prediction_cache'):
        from evaluation.controllers import sdmpc_prediction_cache
        filename = str(Path(sdmpc_prediction_cache.__file__).resolve())
        finder.source_hashes[filename] = hashlib.sha256(Path(filename).read_bytes()).hexdigest()
        if reverse:
            ad.DIRECT_SUM_NODES = True
    if cfg.network.sdmpc_options.get('compact_audit'):
        from evaluation.controllers import sdmpc_tangent_audit
        filename = str(Path(sdmpc_tangent_audit.__file__).resolve())
        finder.source_hashes[filename] = hashlib.sha256(Path(filename).read_bytes()).hexdigest()
        sdmpc_tangent_audit.WITNESS_PROCESS = True
        if reverse:
            sdmpc_tangent_audit.install_guards()
    if cfg.network.sdmpc_options.get('fast_primitives'):
        from evaluation.controllers.sdmpc_tangent_fast import install as install_fast
        install_fast(finder, cfg)
    if cfg.network.sdmpc_options.get('prediction_hotpath'):
        from evaluation.controllers.sdmpc_tangent_summary import install as install_summary
        install_summary(finder,cfg,surrogate_mode=surrogate_mode)
    central_registry = None
    if cfg.network.sdmpc_options.get('central_multiplier'):
        if surrogate_mode not in ('ad', 'scalar'):
            raise ValueError('Central state sensitivities require the continuous candidate model')
        from evaluation.controllers import sdmpc_tangent_constraints
        central_registry = sdmpc_tangent_constraints.install(finder,
            [state.time_sec+(k+1)*cfg.simulation.T_c_sec for k in range(request['horizon'])])
    fifo_stats = None
    if cfg.network.sdmpc_options.get('persistent_urban_fifo') or cfg.network.sdmpc_options.get('array_urban_pipeline'):
        from evaluation.controllers import sdmpc_tangent_fifo,sdmpc_tangent_transport,sdmpc_tangent_spatial
        fifo_stats = sdmpc_tangent_fifo.STATS
        for module in (sdmpc_tangent_fifo,sdmpc_tangent_transport,sdmpc_tangent_spatial):
            path = Path(module.__file__).resolve()
            finder.source_hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    urban_stats = None
    if cfg.network.sdmpc_options.get('array_urban_pipeline'):
        from evaluation.controllers import sdmpc_tangent_urban,sdmpc_tangent_urban_store
        urban_stats = sdmpc_tangent_urban.STATS
        path = Path(sdmpc_tangent_urban.__file__).resolve()
        finder.source_hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        path = Path(sdmpc_tangent_urban_store.__file__).resolve()
        finder.source_hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    transport_stats = None
    if cfg.network.sdmpc_options.get('array_transport'):
        from evaluation.controllers import sdmpc_tangent_transport,sdmpc_tangent_spatial
        transport_stats = sdmpc_tangent_transport.STATS
        for module in (sdmpc_tangent_transport,sdmpc_tangent_spatial):
            path = Path(module.__file__).resolve()
            finder.source_hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    spatial_stats = None
    if cfg.network.sdmpc_options.get('spatial_receiving'):
        from evaluation.controllers import sdmpc_tangent_spatial
        spatial_stats = sdmpc_tangent_spatial.STATS
        path = Path(sdmpc_tangent_spatial.__file__).resolve()
        finder.source_hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    frozen = pickle.dumps(request['owned'], protocol=5)
    surrogate_prediction = None
    central_names, central_values = None, None
    surrogate_context = request.get('surrogate_context_sha256', hashlib.sha256(frozen).hexdigest())

    def predict(action):
        nonlocal surrogate_prediction, central_names, central_values
        from contextlib import nullcontext
        runtime = copy.deepcopy(request['runtime'])
        runtime['_PHASE_VECTOR_FOLLOWER']['ref'] = follower
        for name, value in runtime.items():
            setattr(adapter, name, value)
        plan_scope = nullcontext()
        if 'sdmpc_prediction_sequence' in action.diagnostics:
            from evaluation.controllers.sdmpc_sequence import prediction_scope
            plan_scope = prediction_scope(action, cfg, state.time_sec, request['horizon'])
        with joint.shared_query_runtime_scope(), joint.shared_response_gc_scope(True), plan_scope:
            point = rollout_endpoint.evaluate_price_point(state, action, forecast, (),
                rollout_endpoint.ObjectiveSpec(cfg, depth_override=request['horizon'],
                    box_walk=False, score_mode='raw'), capture_response=True)
            if point.aborted or len(point.states) != request['horizon']:
                raise ValueError('Incomplete tangent response')
            local, partition = omega_costs(point, cfg)
            q = constraints.shared_urban_quantities(follower, point.control_area_response,
                start_sec=state.time_sec, horizon_steps=request['horizon'])
            resource = constraints.shared_quantity_constraints(follower, action, q,
                start_sec=state.time_sec, horizon_steps=request['horizon'],
                np_mode='cap', target_np_veh=action.N_P_star, np_tolerance_veh=0.,
                nuf_mode='equality', target_nuf_veh_h=action.N_UF_star, nuf_tolerance_veh_h=0.)
        if surrogate_mode:
            surrogate_prediction = sdmpc_tangent_surrogate.prediction(point, state, request['action'],
                local, partition, q, surrogate_context)
        if central_registry is not None:
            central_names, central_values = central_registry.finish(point.states, cfg)
            surrogate_prediction.pop('response_token')
            surrogate_prediction['central_physical'] = dict(names=central_names,
                values=[ad.primal(v) for v in central_values],
                scope='Horizon-end queue/density/storage/lane inventory and recorded urban state bounds; all original stepwise dynamic audits retained')
            surrogate_prediction['response_token'] = sdmpc_tangent_surrogate.token(surrogate_prediction)
        costs = [partition['costs'][owner] for owner in request['costs_order']]
        return point, costs, [resource['np']['actual'], resource['nuf']['actual']]

    started = time.perf_counter()
    shared = request.get('shared_primal')
    scalar_load_sec = 0.
    def read_shared(shared):
        if shared['anchor_sha256'] != request['shared_anchor_sha256']:
            raise ValueError('Shared scalar witness anchor mismatch')
        print('shared_scalar_load_start', flush=True)
        data = Path(shared['path']).read_bytes()
        if (hashlib.sha256(data).hexdigest() != shared['sha256']
                or shared['anchor_sha256'] != request['shared_anchor_sha256']):
            raise ValueError('Shared scalar witness digest/anchor mismatch')
        witness = pickle.loads(data)
        del data
        if witness['anchor_sha256'] != request['shared_anchor_sha256']:
            raise ValueError('Scalar witness contains another prediction anchor')
        for name, expected in witness['sources'].items():
            if (hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected
                    or (name in finder.source_hashes and finder.source_hashes[name] != expected)):
                raise ValueError('Shared scalar source changed: '+name)
        return witness['states'], witness['costs'], witness['resources']

    if skip_scalar_witness:
        scalar_sec = 0.
    elif shared:
        scalar_states, costs, resources = read_shared(shared)
        scalar_load_sec = time.perf_counter()-started
        scalar_sec = 0.
    elif deferred:
        scalar_sec = 0.
    else:
        print('continuous_scalar_start', flush=True)
        scalar, costs, resources = predict(request['action'].copy())
        scalar_states = scalar.states
        scalar_sec = time.perf_counter()-started
    progress['scalar_sec'] = scalar_sec
    print('continuous_scalar_done', scalar_sec, flush=True)
    if surrogate_mode == 'scalar':
        if frozen != pickle.dumps(request['owned'], protocol=5):
            raise ValueError('Continuous candidate mutated model operands')
        for filename, expected in finder.source_hashes.items():
            if hashlib.sha256(Path(filename).read_bytes()).hexdigest() != expected:
                raise ValueError('Continuous candidate source changed')
        return dict(costs=costs, resources=resources, scalar_sec=scalar_sec,
            scalar_rollouts=1, tangent_rollouts=0, primal_audit_performed=False,
            surrogate_prediction=surrogate_prediction, surrogate_evaluation=surrogate_mode,
            transformed_source_sha256=finder.source_hashes)
    if request.get('scalar_output'):
        started = time.perf_counter()
        if frozen != pickle.dumps(request['owned'], protocol=5):
            raise ValueError('Scalar witness mutated frozen model operands')
        for name, expected in finder.source_hashes.items():
            if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
                raise ValueError('Scalar witness source changed: '+name)
        data = pickle.dumps(dict(states=scalar_states, costs=costs, resources=resources,
            sources=dict(finder.source_hashes), anchor_sha256=request['shared_anchor_sha256']), protocol=5)
        Path(request['scalar_output']).write_bytes(data)
        return dict(costs=costs, resources=resources, scalar_sec=scalar_sec,
            scalar_export_sec=time.perf_counter()-started, scalar_rollouts=1,
            method='shared_continuous_scalar_witness',
            **({'array_urban_pipeline':dict(urban_stats),'native_urban_store':dict(sdmpc_tangent_urban_store.STATS)} if urban_stats is not None else {}),
            **({'persistent_urban_fifo':dict(fifo_stats)} if fifo_stats is not None else {}),
            **({'array_transport':dict(transport_stats)} if transport_stats is not None else {}),
            **({'spatial_receiving':dict(spatial_stats)} if spatial_stats is not None else {}),
            shared_primal=dict(path=request['scalar_output'], sha256=hashlib.sha256(data).hexdigest(),
                               anchor_sha256=request['shared_anchor_sha256'], bytes=len(data)),
            transformed_source_sha256=finder.source_hashes)
    if request.get('scalar_only'):
        return dict(costs=costs,resources=resources,scalar_sec=scalar_sec,
            method='continuous_scalar_verification',transformed_source_sha256=finder.source_hashes)
    blocks = cfg.network.sdmpc_options.get('control_blocks', 1)
    if blocks not in (1,3) or (blocks == 3 and request['horizon'] != 3):
        raise ValueError('Invalid SDMPC derivative block horizon')
    catalogs = [[(a['owner'],a['kind'],a['key']) for a in request['axes']
                 if a.get('block',0) == k] for k in range(blocks)]
    if not catalogs[0] or any(c != catalogs[0] for c in catalogs[1:]) or sum(map(len,catalogs)) != len(request['axes']):
        raise ValueError('Every SDMPC block requires the same complete independent control catalog')
    if blocks == 3:
        from evaluation.controllers import sdmpc_sequence as sequence
        controls = sequence.actions(request['action'], blocks)
    else:
        controls = [request['action'].copy()]
    trace = ad.Trace([axis['fd'] for axis in request['axes']], track_stencils=False)
    fallback = {}
    active = []
    columns = request.get('column_indices',list(range(len(request['axes']))))
    if (not columns or any(type(j) is not int for j in columns)
            or len(set(columns)) != len(columns) or min(columns) < 0
            or max(columns) >= len(request['axes'])):
        raise ValueError('Invalid derivative column partition')
    # Seed every continuous control at the same reference. There is no
    # quantization, finite-difference stencil, or changed-control rollout here.
    for j, axis in enumerate(request['axes']):
        if j not in columns:
            continue
        action = controls[axis.get('block', 0)]
        kind, owner, key = axis['kind'], axis['owner'], axis['key']
        if kind == 'green':
            for phase, factor in request['green_vectors'][j].items():
                name = owner+'_'+phase
                value = action.green_times[name]
                tangents = dict(ad.derivative(value))
                tangents[j] = factor*axis['scale']
                action.green_times[name] = ad.Dual(ad.primal(value), tangents, trace)
        elif kind == 'offset':
            action.offsets[key] = ad.Dual(action.offsets[key], {j:axis['scale']}, trace)
        elif kind == 'meter':
            name = 'rw_meter_green_'+key
            action.diagnostics[name] = ad.Dual(action.diagnostics[name], {j:axis['scale']}, trace)
        elif kind == 'vsl':
            value = ad.Dual(action.vsl[key], {j: axis['scale']}, trace)
            for cell, head in enumerate(cfg.network.freeway_vsl_zone_head_of_cell[owner]):
                if head == axis['head']:
                    action.vsl[f'{owner}__seg{cell}'] = value
        else:
            raise ValueError('Unsupported continuous SDMPC coordinate: '+kind)
        active.append(j)
    for action in controls:
        for owner in cfg.network.freeway_links:
            action.vsl[owner] = ad.minimum(action.vsl[f'{owner}__seg{i}']
                for i in range(len(cfg.network.freeway_vsl_zone_head_of_cell[owner])))
    action = sequence.pack(controls) if blocks == 3 else controls[0]
    started = time.perf_counter()
    print('continuous_tangent_start', flush=True)
    if cfg.network.sdmpc_options.get('array_urban_pipeline'):
        with sdmpc_prediction_cache.reverse_arrays():
            tangent, dual_costs, dual_resources = predict(action)
    else:
        tangent, dual_costs, dual_resources = predict(action)
    tangent_sec = time.perf_counter()-started
    progress['tangent_sec'] = tangent_sec
    print('continuous_tangent_done', tangent_sec, flush=True)
    if skip_scalar_witness:
        costs = [ad.primal(value) for value in dual_costs]
        resources = [ad.primal(value) for value in dual_resources]
    if deferred:
        from evaluation.controllers.sdmpc_tangent_concurrent import read_descriptor
        started = time.perf_counter()
        shared = read_descriptor(sys.stdin)
        scalar_states, costs, resources = read_shared(shared)
        scalar_load_sec = time.perf_counter()-started
    if request.get('diagnostic_checkpoint'):
        Path(request['diagnostic_checkpoint']).write_bytes(pickle.dumps(
            dict(scalar_states=scalar_states, tangent_states=tangent.states,
                 scalar_costs=costs, scalar_resources=resources,
                 dual_costs=dual_costs, dual_resources=dual_resources), protocol=5))
    started = time.perf_counter()
    compare = state_error
    if shared_mode or reverse or immutable_audit:
        from evaluation.controllers import sdmpc_tangent_state
        filename = str(Path(sdmpc_tangent_state.__file__).resolve())
        finder.source_hashes[filename] = hashlib.sha256(Path(filename).read_bytes()).hexdigest()
        compare = sdmpc_tangent_state.state_error
    error = None if skip_scalar_witness else (compare(scalar_states, tangent.states,
                     fast_records=cfg.network.sdmpc_options.get('fast_primitives',False),
                     compact_records=cfg.network.sdmpc_options.get('compact_audit',False))
             if cfg.network.sdmpc_options.get('fast_primitives') or cfg.network.sdmpc_options.get('compact_audit')
             else compare(scalar_states, tangent.states))
    state_check_sec = time.perf_counter()-started
    tolerance = cfg.network.sdmpc_options['tangent_primal_abs_tolerance']
    if error is not None and error > tolerance:
        raise ValueError(f'Tangent full state differs from scalar: {error}')
    for plain, dual in zip(costs+resources, dual_costs+dual_resources):
        if abs(plain-ad.primal(dual)) > tolerance:
            raise ValueError('Tangent primal costs/resources differ from scalar')
    reverse_sec = None
    if reverse:
        started = time.perf_counter()
        jacobian = trace.jacobian(dual_costs+dual_resources,
                                 reverse_workers)
        reverse_sec = time.perf_counter()-started
    central_physical = None
    if central_registry is not None:
        # Preserve the cost/resource reverse-sweep receipt while adding state derivatives.
        original_sweeps = copy.deepcopy(trace.backward_receipt)
        state_jacobian, state_receipt = sdmpc_tangent_constraints.jacobian(trace, central_values, reverse_workers)
        trace.backward_receipt = original_sweeps
        central_physical = dict(surrogate_prediction['central_physical'],
            jacobian=state_jacobian.tolist(), derivative_work=state_receipt)
    events = trace.result(dual_costs+dual_resources)
    # Capacity min/max and measured meter-table knots use the selected
    # piecewise derivative. Do not replace these by all-axis finite differences.
    # Branch/event risks remain explicit. Surrogate mode deliberately uses its
    # own predicted constraints; the default path keeps the exact-model gate.
    if frozen != pickle.dumps(request['owned'], protocol=5):
        raise ValueError('Tangent query mutated frozen model operands')
    for filename, expected in finder.source_hashes.items():
        if hashlib.sha256(Path(filename).read_bytes()).hexdigest() != expected:
            raise ValueError('Tangent source changed during prediction: '+filename)
    def jac(values):
        return [[ad.derivative(v).get(j, 0.) for j in columns] for v in values]
    return dict(costs=costs, resources=resources,
        cost_jacobian=jacobian[:len(costs)].tolist() if reverse else jac(dual_costs),
        resource_jacobian=jacobian[len(costs):].tolist() if reverse else jac(dual_resources), fallback_reasons=fallback,
        active_axes=active, ad_axes=[j for j in active if j not in fallback],
        complete_primal_state_match=not skip_scalar_witness, max_primal_state_error=error,
        scalar_rollouts=0 if shared or skip_scalar_witness else 1, tangent_rollouts=1, scalar_sec=scalar_sec, tangent_sec=tangent_sec,
        trace=events, transformed_source_sha256=finder.source_hashes,
        **({'central_physical':central_physical} if central_physical is not None else {}),
        method='continuous_actuator_compiled_reverse' if reverse else 'continuous_actuator_sparse_forward', execution_validation_required=True,
        derivative_scope='Active physical branch; endogenous discrete travel events held on that branch',
        reference_model='continuous_signal_windows_and_cycle_mean_meter_service',
        signal_transition_width_sec=cfg.network.sdmpc_options['signal_transition_width_sec'],
        **(dict(surrogate_prediction=surrogate_prediction, surrogate_evaluation=surrogate_mode,
                primal_audit_performed=False) if surrogate_mode else {}),
        **(dict(scalar_load_sec=scalar_load_sec, state_check_sec=state_check_sec,
                shared_primal=shared) if shared_mode or reverse else {}),
        **(dict(reverse_sec=reverse_sec, reverse_sweeps=trace.backward_receipt) if reverse else {}),
        **({'spatial_receiving':dict(spatial_stats)} if spatial_stats is not None else {}),
        **({'column_indices':columns} if 'column_indices' in request else {}),
        **({'array_urban_pipeline':dict(urban_stats),'native_urban_store':dict(sdmpc_tangent_urban_store.STATS)} if urban_stats is not None else {}),
        **({'persistent_urban_fifo':dict(fifo_stats)} if fifo_stats is not None else {}),
        **({'array_transport':dict(transport_stats)} if transport_stats is not None else {}),
        **({'control_blocks':blocks, 'control_interval_sec':cfg.simulation.T_c_sec} if blocks == 3 else {}))


def expand_shared_request(envelope):
    """Bind every worker operand to the same parent-owned request bytes."""
    if 'shared_request' not in envelope:
        return envelope
    if set(envelope) - {'shared_request', 'scalar_output', 'shared_primal', 'column_indices',
                       'shared_primal_stdin', 'worker_backend'}:
        raise ValueError('Unexpected shared derivative override')
    descriptor = envelope['shared_request']
    data = Path(descriptor['path']).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != descriptor['sha256']:
        raise ValueError('Common derivative request changed')
    request = pickle.loads(data)
    forbidden = {'scalar_only', 'scalar_output', 'shared_primal', 'shared_request',
                 'shared_anchor_sha256', 'column_indices', 'shared_primal_stdin', 'worker_backend'}
    if forbidden & request.keys():
        raise ValueError('Nested or partial common derivative request')
    if sum(k in envelope for k in ('scalar_output', 'shared_primal', 'shared_primal_stdin')) != 1:
        raise ValueError('Shared request must export or consume exactly one scalar witness')
    if 'shared_primal_stdin' in envelope and envelope['shared_primal_stdin'] is not True:
        raise ValueError('Invalid deferred scalar witness request')
    request.pop('diagnostic_checkpoint', None)
    request.update({k: v for k, v in envelope.items() if k not in ('shared_request', 'worker_backend')})
    request['shared_anchor_sha256'] = digest
    return request


def main():
    request_path, result_path, expected = sys.argv[1:4]
    result = {'request_sha256': expected}
    try:
        from evaluation.controllers.sdmpc_tangent_runtime import install
        finder = install(ROOT, sys.argv[4] if len(sys.argv)>4 else 'forward')
        data = Path(request_path).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Tangent request digest mismatch')
        result.update(run(expand_shared_request(pickle.loads(data)), finder, result))
    except Exception:
        result['error'] = traceback.format_exc()
    Path(result_path).write_bytes(pickle.dumps(result, protocol=5))
    return 1 if 'error' in result else 0


if __name__ == '__main__':
    raise SystemExit(main())
