"""Compare response capture OFF/ON at a completed run's held-450s decision.

Uses the canonical endpoint, no controller solve or native process. The earlier
alias diagnostic pins the fixture; explicitly named query-preparation edits are
reported, not claimed identical to that historical producer. Current inputs and
sources must remain fixed throughout both evaluations.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import pickle
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SINK_ORDER_ARCHIVE = ROOT/'diagnostics/control_improvement/decision_common_anchor_20260911/sink_order_before.py.txt'
sys.path.insert(0, str(ROOT))
from diagnostics.check_selected_open_meter_alias import read, sha, require, validate_environment

PREPARATION_EDITS = {
    # Same helper hash as the completed peel-off v4 comparison; it only
    # clarifies that native coverage can end before the held model horizon.
    'diagnostics/check_selected_open_meter_alias.py',
    'evaluation/controllers/control_area_objective.py',
    'evaluation/controllers/area_runtime.py',
    'evaluation/controllers/area_freeway_accounting.py',
    'evaluation/controllers/area_meter_finalization.py',
    'evaluation/controllers/link_predictor.py',
    'evaluation/controllers/local_signal_service.py',
    'evaluation/controllers/area_follower_objective.py',
    'evaluation/controllers/freeway_fd.py',
    'evaluation/controllers/signal_group_plan.py',
    'evaluation/controllers/signal_actuation_contract.py',
    # Disclosed optional native-clock writer/runtime source validation. Current
    # WSH/OFF semantics: NATIVE_WRITER_PURE_VALIDATION.md (26 tests); this is
    # not a claim of byte equality with the old recorded native runner.
    'scripts/run_real_world_stackelberg_controller.vbs',
    'evaluation/controllers/runtime_setup.py',
    # Reviewed optional native-node cycle and explicit physical-meter profile;
    # saved wu-link fixture does not call this profile. Disclose changed SHA.
    'evaluation/controllers/diagnostic_signal_profile.py',
    'evaluation/controllers/joint_owner_game.py',
    # Exact serialization reuse and post-price candidate traversal are reported
    # against the old fixture; current source immutability is still enforced.
    'evaluation/controllers/joint_owner_neighbors.py',
    # Reviewed 10642 upstream peel-off: model signal authority changes while
    # the native network, demand and recorded command stay fixed.
    'evaluation/controllers/physical_movement_routes.py',
    'diagnostics/physical_phase_authority_ver2.json',
    'evaluation/controllers/area_leader_objective.py',
    'evaluation/controllers/urban_flow_accounting.py',
    'evaluation/controllers/route_choice_corridor.py',
    'evaluation/controllers/native_internal_input.py',
    'evaluation/controllers/native_input_routes.py',
    'evaluation/controllers/native_input_prehead.py',
    'evaluation/controllers/shared_approach.py',
    'evaluation/controllers/sc2001_corridor.py',
    'evaluation/controllers/vissim_stackelberg_adapter.py',
}


def digest(value):
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def compare_urban_costs(state, control, forecast, cfg, tuning, report, *, all_owners=False):
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers.area_follower_objective import (
        score_shared_urban_point, score_shared_owner_point, score_shared_priced_point)
    from src.controllers import rollout_endpoint
    follower = adapter.build_priced_wu_link_controller(cfg, tuning).nash_solver
    frozen = digest((state, control, forecast))
    trial = control.copy()
    owner, head = 'FW_E', 10
    heads = tuple(cfg.network.freeway_vsl_zone_heads[owner])
    require(head in heads[:-1], 'Probe must use a free VSL zone head')
    head_of = tuple(cfg.network.freeway_vsl_zone_head_of_cell[owner])
    before_value = control.vsl[f'{owner}__seg{head}']
    value = max(v for v in cfg.freeway_follower.vsl_set if v < before_value)
    changed = {}
    for cell, source in enumerate(head_of):
        if source == head:
            key = f'{owner}__seg{cell}'
            trial.vsl[key] = float(value)
            changed[key] = [control.vsl[key], float(value)]
    trial.vsl[owner] = min(trial.vsl[f'{owner}__seg{i}'] for i in range(len(head_of)))
    require({k: v for k, v in vars(control).items() if k != 'vsl'} ==
            {k: v for k, v in vars(trial).items() if k != 'vsl'},
            'Probe changed another lever or leader budget')
    probe_key = 'owner_cost_probe' if all_owners else 'urban_cost_probe'
    arms_key = 'owner_cost_arms' if all_owners else 'urban_cost_arms'
    owners = tuple(cfg.network.signals) + (tuple(cfg.network.freeway_links) if all_owners else ())
    fixed_price_context = None
    if all_owners:
        price_keys = {'phase': tuple(control.green_times), 'offset': tuple(control.offsets),
                      'vsl': tuple(k for k in control.vsl if '__seg' in k), 'meter': tuple(control.ramp_metering)}
        attrs = {'phase': 'signal_phase_price', 'offset': 'offset_marginal_price',
                 'vsl': 'vsl_marginal_price', 'meter': 'metering_marginal_price'}
        inactive = {}
        for channel, attribute in attrs.items():
            prices = getattr(follower, attribute)
            require(prices in (None, {}), 'This algebra smoke requires unrefreshed empty builder prices')
            inactive[channel] = list(price_keys[channel]) if prices == {} else []
        fixed_price_context = {'leader_present': True, 'np_mode': 'dual', 'nuf_mode': 'dual',
                               'inactive_price_addresses': inactive}
    report[probe_key] = {'owner': owner, 'zone_head': head, 'changed_vsl': changed,
        'meter_rates': dict(control.ramp_metering), 'N_UF_star': control.N_UF_star,
        'recorded_meter_interpretation_retained': True,
        'solver_price_dispatch_connected': False, 'native_run': False}
    from src.models import urban_queue_model as uqm
    report['native_prehead_capacity_context'] = {}
    for no, entry in getattr(cfg.network, 'native_internal_inputs', {}).get('inputs', {}).items():
        if entry.get('kind') != 'native_choice_prehead':
            continue
        spec = entry['prehead_spec']
        movements = spec['wn_movements'] + [spec['capacity_reference_movement']]
        report['native_prehead_capacity_context'][no] = {
            'spec': spec, 'movement_capacities_veh_h': {
                movement: uqm._movement_capacity_flow(control, cfg, movement, cfg.network.urban_movements[movement])
                for movement in movements},
            'movement_declarations': {movement: cfg.network.urban_movements[movement] for movement in movements}}
    costs = {}
    for name, action in (('recorded', control), ('freeway_vsl_neighbor', trial)):
        query_frozen = digest((state, action, forecast))
        started = time.monotonic()
        point = rollout_endpoint.evaluate_price_point(state, action, forecast, (),
            rollout_endpoint.ObjectiveSpec(cfg, depth_override=3, box_walk=False, score_mode='raw'),
            capture_response=True)
        elapsed = time.monotonic() - started
        require(not point.aborted and len(point.states) == 3, 'Incomplete joint response')
        before_response = digest(point.control_area_response)
        started = time.monotonic()
        local = (score_shared_owner_point(follower, point, state, action, control, horizon_steps=3)
                 if all_owners else score_shared_urban_point(follower, point, state, horizon_steps=3))
        score_elapsed = time.monotonic() - started
        require(digest(point.control_area_response) == before_response, 'Scoring mutated response')
        require(digest((state, action, forecast)) == query_frozen, 'Query mutated input')
        require(set(local) == set(owners), 'Owner coverage differs')
        costs[name] = local
        report.setdefault(arms_key, {})[name] = {
            'endpoint_elapsed_sec': elapsed, 'local_score_elapsed_sec': score_elapsed,
            'signature': signature(point), 'local_costs': local,
            'response_sha256': before_response,
            'native_prehead_reference_overdraw_veh': (
                getattr(point.states[-1], 'native_input_prehead_state', {}).get('existing_wn_budget_overdraw_veh', 0.)
                - getattr(state, 'native_input_prehead_state', {}).get('existing_wn_budget_overdraw_veh', 0.)),
            'accepted_events': len(point.control_area_response['transfers']),
            'residence_records': len(point.control_area_response['residence'])}
        if all_owners:
            priced = score_shared_priced_point(follower, point, state, action, control, horizon_steps=3,
                lambda_p=float(follower._lambda_P), lambda_uf=float(follower._lambda_UF),
                target_np_veh=float(control.N_P_star), target_nuf_veh_h=float(control.N_UF_star),
                price_context=fixed_price_context)
            require(priced['local_costs'] == local, 'Combined pricing changed the local functional')
            report[arms_key][name]['fixed_price_algebra_smoke'] = priced
            resources = point.control_area_response['resource_allocations']
            report[arms_key][name]['resource_summary'] = {
                'count': len(resources), 'kinds': dict(Counter(row['kind'] for row in resources)),
                'max_exceedance_veh': max((row['exceedance_veh'] for row in resources), default=0.),
                'full_shared_capacity_certificate': False}
            wrong_state = state.copy()
            wrong_state.freeway_density['FW_E'][0] += 1.
            try:
                score_shared_owner_point(follower, point, wrong_state, action, control, horizon_steps=3)
            except ValueError as exc:
                require('initial traffic operands' in str(exc), 'Unexpected mismatched-state error')
            else:
                raise ValueError('Response from a different initial state was accepted')
            require(digest(point.control_area_response) == before_response, 'Payoff consumption mutated response')
            require(digest((state, action, forecast)) == query_frozen, 'Payoff consumption mutated inputs')
    require(digest((state, control, forecast)) == frozen, 'Scoring mutated original inputs')
    report[probe_key]['local_cost_delta'] = {
        signal: costs['freeway_vsl_neighbor'][signal]['cost'] - costs['recorded'][signal]['cost']
        for signal in owners}
    if all_owners:
        report[probe_key]['fixed_price_smoke_scope'] = (
            'Explicit fixed targets from recorded action scalars and unrefreshed builder prices/duals; '
            'not the recorded PFO/leader game, not marginal-price production or solver integration')


def signature(point):
    # Deliberately exclude only the opt-in ledger response payload, not traffic,
    # cohorts, metrics, accepted flow counters or ordinary endpoint diagnostics.
    states = []
    for state in point.states:
        ledger = state._control_area_ledger
        physical = {k: v for k, v in vars(state).items() if k != '_control_area_ledger'}
        states.append({'physical_state_sha256': digest(physical),
                       'cohorts_sha256': digest(ledger.stocks),
                       'metrics': vars(ledger.metrics),
                       'flow_counts_sha256': digest(ledger.flow_counts),
                       'event_count': ledger.event_count})
    ordinary = {k: v for k, v in vars(point).items()
                if k not in ('states', 'control_area_response')}
    return {'states': states, 'ordinary_endpoint_sha256': digest(ordinary),
            'objective_veh_h': point.objective, 'control_area': point.control_area}


def _full_response_value_diff(left, right):
    """Diagnostic proof over every response value; pickle identity stays separate."""
    import struct
    import numpy as np
    from collections import Counter
    differences, order_differences = [], []
    counts = Counter()
    aliases = [{}, {}]
    alias_hashes = [hashlib.sha256(), hashlib.sha256()]
    mutable_hashes = [hashlib.sha256(), hashlib.sha256()]
    active = [set(), set()]
    def key_token(key):
        typ = type(key)
        if typ is float:
            value = struct.pack('!d', key).hex()
        elif typ is complex:
            value = struct.pack('!dd', key.real, key.imag).hex()
        elif typ in (str, int, bool, type(None)):
            value = key
        elif typ is bytes:
            value = key.hex()
        elif typ in (tuple, frozenset):
            value = [key_token(item) for item in key]
            if typ is frozenset:
                value.sort()
        else:
            raise TypeError('Unsupported response dictionary key: '+str(typ))
        return json.dumps((typ.__name__, value), ensure_ascii=True, separators=(',', ':'))
    def note(path, kind, x, y):
        counts['differences'] += 1
        if len(differences) < 50:
            differences.append({'path': path, 'kind': kind, 'serial': repr(x)[:240], 'worker': repr(y)[:240]})
    def visit(x, y, path):
        counts['visited_values'] += 1
        if type(x) is not type(y):
            note(path, 'type', type(x), type(y))
            return
        typ = type(x)
        counts['type:' + typ.__module__ + '.' + typ.__qualname__] += 1
        tracked = typ in (dict, Counter, list, tuple, str, bytes) or typ is np.ndarray
        if tracked:
            for side, value in enumerate((x, y)):
                first = aliases[side].setdefault(id(value), path)
                item = json.dumps((path, first), ensure_ascii=True).encode('ascii')
                alias_hashes[side].update(item)
                if typ in (dict, Counter, list) or typ is np.ndarray:
                    mutable_hashes[side].update(item)
                if id(value) in active[side]:
                    note(path, 'unsupported-cycle', 'cycle', 'cycle')
                    return
        if typ in (dict, Counter):
            try:
                left_keys = {key_token(k): k for k in x}
                right_keys = {key_token(k): k for k in y}
            except TypeError:
                note(path, 'unsupported-dict-key', tuple(x), tuple(y))
                return
            if len(left_keys) != len(x) or len(right_keys) != len(y):
                note(path, 'ambiguous-typed-dict-key', tuple(x), tuple(y))
                return
            if set(left_keys) != set(right_keys):
                note(path, 'typed-dict-keys', sorted(left_keys), sorted(right_keys))
            if list(left_keys) != list(right_keys):
                counts['dict_order_differences'] += 1
                if len(order_differences) < 20:
                    order_differences.append(path)
            active[0].add(id(x)); active[1].add(id(y))
            for token in sorted(set(left_keys) & set(right_keys)):
                key = left_keys[token]
                visit(x[key], y[right_keys[token]], path+'['+repr(key)+']')
            active[0].remove(id(x)); active[1].remove(id(y))
        elif typ in (list, tuple):
            if len(x) != len(y):
                note(path, 'length', len(x), len(y))
            active[0].add(id(x)); active[1].add(id(y))
            for index, (a, b) in enumerate(zip(x, y)):
                visit(a, b, path+'['+str(index)+']')
            active[0].remove(id(x)); active[1].remove(id(y))
        elif typ is float:
            if struct.pack('!d', x) != struct.pack('!d', y):
                note(path, 'ieee754-float64-bits', x.hex(), y.hex())
        elif typ is complex:
            if struct.pack('!dd', x.real, x.imag) != struct.pack('!dd', y.real, y.imag):
                note(path, 'complex128-bits', x, y)
        elif typ is np.ndarray or isinstance(x, np.generic):
            if x.dtype.hasobject or y.dtype.hasobject:
                note(path, 'unsupported-object-array', x.dtype, y.dtype)
            elif (x.dtype != y.dtype or x.shape != y.shape or x.tobytes(order='C') != y.tobytes(order='C')):
                note(path, 'array-dtype-shape-exact-bits', (x.dtype, x.shape), (y.dtype, y.shape))
        elif typ in (type(None), bool, int, str, bytes):
            if x != y:
                note(path, 'value', x, y)
        elif typ.__module__ == 'src.models.state' and typ.__qualname__ == 'ControlAction':
            # The endpoint retains the applied action as this exact dataclass.
            # Keep every field (including diagnostics), rather than dropping it.
            visit(vars(x), vars(y), path+'.__dict__')
        else:
            note(path, 'unsupported-type', typ, typ)
    visit(left, right, 'response')
    return {'all_typed_values_exact': counts['differences'] == 0,
        'counts': dict(counts), 'first_differences': differences,
        'first_dict_order_differences': order_differences,
        'alias_graph_sha256': [h.hexdigest() for h in alias_hashes],
        'mutable_alias_graph_sha256': [h.hexdigest() for h in mutable_hashes],
        'scope': 'Every row, key, ordered list/tuple, exact Python type and IEEE/array bits; dict insertion order and scalar/mutable alias graphs reported separately; unsupported types fail'}


def _sink_order_original_callback(module, archive=SINK_ORDER_ARCHIVE):
    """Compile only the trusted archived callback; no original module imports."""
    import ast
    raw = archive.read_bytes()
    manifest = read(archive.with_suffix('.sha256.json'))
    require(hashlib.sha256(raw).hexdigest() == manifest['sha256'] and len(raw) == manifest['bytes'],
            'Archived sink source does not match its exact manifest')
    before = raw.decode('utf-8-sig').replace('\r\n', '\n')
    after = Path(module.__file__).read_text(encoding='utf-8-sig')
    replacement = ('    # Deterministic physical sink traversal, including floating accumulation\n'
                   '    # order and appended transfer/resource evidence, across spawned processes.\n'
                   '    for link in sorted(sink_links):')
    require(before.count('    for link in sink_links:') == 1
            and after == before.replace('    for link in sink_links:', replacement),
            'Sink A/B requires exactly the disclosed traversal change')
    functions = [node for node in ast.parse(before).body
                 if isinstance(node, ast.FunctionDef) and node.name == 'urban_substep_accounted']
    require(len(functions) == 1, 'Archived sink callback not unique')
    tree = ast.Module(body=functions, type_ignores=[])
    ast.fix_missing_locations(tree)
    namespace = dict(vars(module))
    exec(compile(tree, str(archive), 'exec'), namespace)
    return namespace['urban_substep_accounted'], manifest


def _sink_order_endpoint_graph(point):
    """Every physical state/ledger field; captured record payload is separate."""
    states = []
    for state in point.states:
        ledger = state._control_area_ledger
        states.append({'state': {k: v for k, v in vars(state).items() if k != '_control_area_ledger'},
            'ledger': {k: v for k, v in vars(ledger).items() if k != '_response'}})
    return {'states': states,
        'endpoint': {k: v for k, v in vars(point).items() if k not in ('states', 'control_area_response')},
        'response': point.control_area_response}


def _sink_order_graph_comparison(original, sorted_order):
    """Retain every row/bit; disclose only the two sink-record permutations."""
    import struct
    def typed(value):
        typ = type(value)
        if typ is dict:
            return ('dict', sorted([(typed(k), typed(v)) for k, v in value.items()], key=lambda pair: repr(pair[0])))
        if typ in (list, tuple):
            return (typ.__name__, [typed(v) for v in value])
        if typ is float:
            return ('float64_ieee_bits', struct.pack('!d', value).hex())
        if typ in (int, str, bool, type(None)):
            return (typ.__name__, value)
        raise TypeError('Unsupported sink record value: '+str(typ))
    def encoded(value):
        return json.dumps(typed(value), ensure_ascii=True, separators=(',', ':'))
    physical = _full_response_value_diff(
        {k: original[k] for k in ('states', 'endpoint')},
        {k: sorted_order[k] for k in ('states', 'endpoint')})
    left, right = original['response'], sorted_order['response']
    require(set(left) == set(right), 'Sink traversal changed response fields')
    ordinary = _full_response_value_diff(
        {k: v for k, v in left.items() if k not in ('transfers', 'resource_allocations')},
        {k: v for k, v in right.items() if k not in ('transfers', 'resource_allocations')})
    records = {}
    for name in ('transfers', 'resource_allocations'):
        aa, bb = Counter(map(encoded, left[name])), Counter(map(encoded, right[name]))
        records[name] = {'lengths': [len(left[name]), len(right[name])],
            'original_sequence_equal': left[name] == right[name],
            'exact_typed_ieee_record_multiset_equal': aa == bb,
            'unmatched_original': sum((aa-bb).values()), 'unmatched_sorted': sum((bb-aa).values()),
            'scope': 'Complete rows include original stage/start/end/source/resource identity; multiplicity preserved'}
    return {'all_physical_state_and_endpoint_values_exact': physical['all_typed_values_exact'],
        'physical_state_comparison': physical, 'ordered_response_fields_comparison': ordinary,
        'record_permutations': records,
        'passed': physical['all_typed_values_exact'] and ordinary['all_typed_values_exact']
            and all(row['exact_typed_ieee_record_multiset_equal'] for row in records.values()),
        'scope': 'No row removed or physical float tolerance; only disclosed complete sink records may change sequence. Parallel qualification remains separate'}


def compare_sink_order(state, control, forecast, cfg, report, output):
    from unittest.mock import patch
    from evaluation.controllers import urban_flow_accounting as urban
    from evaluation.controllers.area_follower_objective import shared_query_runtime_scope
    from src.controllers import rollout_endpoint
    original, manifest = _sink_order_original_callback(urban)
    current = urban.urban_substep_accounted
    fixed = digest((state, control, forecast, cfg))
    directory = output.resolve().with_suffix('.states')
    directory.mkdir(exist_ok=False)
    report['sink_order_comparison'] = {'archive_manifest': manifest, 'arms': {}}
    graphs = {}
    try:
        for name, callback in (('original', original), ('sorted', current)):
            wall, cpu = time.perf_counter(), time.process_time()
            with patch.object(urban, 'urban_substep_accounted', callback), shared_query_runtime_scope():
                point = rollout_endpoint.evaluate_price_point(state, control, forecast, (),
                    rollout_endpoint.ObjectiveSpec(cfg, depth_override=3, box_walk=False, score_mode='raw'),
                    capture_response=True)
            require(not point.aborted and len(point.states) == 3, 'Incomplete held450s sink endpoint')
            require(fixed == digest((state, control, forecast, cfg)), 'Sink A/B mutated frozen caller operands')
            payload = pickle.dumps(_sink_order_endpoint_graph(point), protocol=5)
            path = directory/(name+'.pickle')
            with path.open('xb') as stream:
                stream.write(payload)
            report['sink_order_comparison']['arms'][name] = {'wall_sec': time.perf_counter()-wall,
                'cpu_sec': time.process_time()-cpu, 'path': str(path), 'bytes': len(payload),
                'sha256': hashlib.sha256(payload).hexdigest(), 'objective_veh_h': point.objective}
            graphs[name] = path
            del point, payload
        comparison = _sink_order_graph_comparison(
            pickle.loads(graphs['original'].read_bytes()), pickle.loads(graphs['sorted'].read_bytes()))
        report['sink_order_comparison']['validation'] = comparison
        require(comparison['passed'], 'Sink ordering changed a physical state/IEEE value or matched accepted record')
    finally:
        report['sink_order_comparison']['callback_restored'] = urban.urban_substep_accounted is current
        require(urban.urban_substep_accounted is current, 'Sink A/B callback was not restored')


def _compare_full_response_audits(directory, arm, serial_results, worker_results):
    rows = []
    for serial, worker in zip(serial_results, worker_results):
        require(serial['action_token'] == worker['action_token'], 'Response audit action mismatch')
        token = serial['action_token']
        payloads = []
        row = {'action_token': token}
        for name, compact in (('serial', serial), (arm, worker)):
            path = directory / name / (token + '.pickle')
            raw = path.read_bytes()
            metadata = json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
            require(hashlib.sha256(raw).hexdigest() == compact['response_token'] == metadata['response_token'],
                    'Preserved full response does not match its original response token')
            require(metadata['action_token'] == token and metadata['bytes'] == len(raw),
                    'Preserved full response metadata mismatch')
            payloads.append(raw)
            row[name] = {'path': str(path), **metadata}
        row['raw_pickle_bytes_exact'] = payloads[0] == payloads[1]
        row['full_response_value_comparison'] = _full_response_value_diff(
            pickle.loads(payloads[0]), pickle.loads(payloads[1]))
        rows.append(row)
    return rows


def _parallel_qualification_actions(control, workers):
    """Explicit existing VSL neighbors; four distinct jobs for four workers."""
    import copy
    labels = ('base', 'E100', 'W100', 'both100') if workers == 4 else ('base', 'E100')
    actions = []
    for label in labels:
        action = copy.deepcopy(control)
        for direction in ('FW_E', 'FW_W'):
            if label == 'both100' or label == direction[-1]+'100':
                for cell in range(10, 15):
                    action.vsl[f'{direction}__seg{cell}'] = 100.
                action.vsl[direction] = min(action.vsl[f'{direction}__seg{i}'] for i in range(21))
        actions.append(action)
    require(len({tuple(sorted(action.vsl.items())) for action in actions}) == len(labels),
            'Qualification requires physically distinct existing VSL actions')
    return labels, tuple(actions)


def _parallel_compact_comparison(serial, worker):
    comparison = _full_response_value_diff(serial, worker)
    tokens = (len(serial) == len(worker) and all(
        all(left[key] == right[key] for key in ('response_token', 'action_token', 'frozen_context_token'))
        for left, right in zip(serial, worker)))
    return {'typed_values': comparison, 'full_response_action_context_tokens_exact': tokens,
        'qualified': comparison['all_typed_values_exact'] and tokens,
        'scope': 'All keys, exact types/IEEE bits and ordered lists plus original raw-response/action/context proof. Compact pickle memo identity is reported separately, not used as a portable value hash.'}


def compare_decision_cache(state, control, forecast, cfg, tuning, report, *,
                           parallel_workers=0, worker_bootstrap=None, deadline_sec=120.,
                           response_audit_dir=None, compact_results_dir=None):
    """Same two full actions revisited by price/initializer/owner query callers."""
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers.area_follower_objective import make_decision_shared_query
    follower = adapter.build_priced_wu_link_controller(cfg, tuning).nash_solver
    trial = control.copy()
    for cell in range(10, 15):
        trial.vsl[f'FW_E__seg{cell}'] = 100.
    trial.vsl['FW_E'] = min(trial.vsl[f'FW_E__seg{i}'] for i in range(21))
    source_token, fixed = digest(report['source_sha256']), digest((follower, state, control, trial, forecast))
    results = {}
    if parallel_workers:
        require(parallel_workers in (1, 4) and 0 < deadline_sec < float('inf'),
                'Explicit bounded parallel diagnostic options required')
        deadline = time.perf_counter()+deadline_sec
        require(100. in cfg.freeway_follower.vsl_set, 'Qualification VSL100 is outside the existing candidate set')
        labels, actions = _parallel_qualification_actions(control, parallel_workers)
        bank_token = digest(actions)
        if compact_results_dir is not None:
            compact_results_dir.mkdir(parents=True, exist_ok=False)
        def check_deadline(stage):
            if time.perf_counter() >= deadline:
                raise TimeoutError('Parallel qualification deadline: ' + stage)
        arms = [('serial', 0), ('spawn1', 1)]
        if parallel_workers == 4:
            arms.append(('spawn4', 4))
        report['parallel_response_comparison'] = {}
        report['parallel_action_bank'] = {'labels': labels, 'unique_physical_jobs': len(actions),
            'action_tokens': [digest(a) for a in actions],
            'expanded_from_two_action_measurement': parallel_workers == 4,
            'scope': 'Four-worker qualification uses four distinct valid100kph VSL action combinations; compare arm timings only within this identical bank'}
        report['parallel_qualified'] = False
        report['parallel_deadline_sec'] = deadline_sec
        for name, workers in arms:
            check_deadline('arm_start:' + name)
            wall, cpu = time.perf_counter(), time.process_time()
            response_audit = None
            if response_audit_dir is not None:
                directory = response_audit_dir / name
                directory.mkdir(parents=True, exist_ok=False)
                response_audit = {'directory': str(directory), 'action_tokens': tuple(digest(a) for a in actions)}
            query = make_decision_shared_query(follower, state, control, forecast, horizon_steps=3,
                source_fingerprint=source_token, cache_enabled=True, check_budget=check_deadline,
                parallel_workers=workers, worker_bootstrap=worker_bootstrap if workers else None,
                deadline_monotonic=deadline if workers else None,
                response_audit=response_audit)
            row = {'requested_workers': workers, 'completed': False}
            report['parallel_response_comparison'][name] = row
            try:
                # Distinct physical actions in one batch exercise concurrent
                # misses; later requests must reuse those same physical results.
                batch = query(actions)
                repeated = query(tuple(reversed(actions)))
                require(repeated['results'] == list(reversed(batch['results'])),
                        'Parallel diagnostic cross-query cache changed results')
                results[name] = batch['results']
                row.update(completed=True, results_sha256=digest(batch['results']),
                    action_tokens=[value['action_token'] for value in batch['results']],
                    response_tokens=[value['response_token'] for value in batch['results']])
                if compact_results_dir is not None:
                    path = compact_results_dir/(name+'.pickle')
                    payload = pickle.dumps(batch['results'], protocol=5)
                    with path.open('xb') as stream:
                        stream.write(payload)
                    row['compact_pickle'] = {'path': str(path), 'bytes': len(payload),
                                             'sha256': hashlib.sha256(payload).hexdigest()}
            finally:
                try:
                    query.close()
                finally:
                    row.update(wall_sec=time.perf_counter()-wall, parent_cpu_sec=time.process_time()-cpu,
                               stats=query.stats())
            require(not row['stats']['owned_workers_alive'], 'Parallel qualification left owned workers alive')
            if workers:
                if response_audit_dir is not None:
                    row['full_response_audit'] = _compare_full_response_audits(
                        response_audit_dir, name, results['serial'], results[name])
                row['exact_value_equality'] = results[name] == results['serial']
                row['exact_result_pickle_equality'] = (
                    pickle.dumps(results[name], protocol=5) == pickle.dumps(results['serial'], protocol=5))
                row['compact_value_proof'] = _parallel_compact_comparison(results['serial'], results[name])
                if not row['exact_result_pickle_equality']:
                    row['failed_actual_results'] = results[name]
                    row['failed_serial_results'] = results['serial']
                require(row['exact_value_equality'] and row['compact_value_proof']['qualified'],
                        name + ' changed response, owner costs, quantities, action/context proof or validation evidence')
                require(row['stats']['parallel_accepted'] == len(actions),
                        'Parallel qualification silently skipped its distinct endpoint tasks')
                if workers == 4:
                    row['distinct_actual_worker_pids'] = sorted(map(int, row['stats']['worker_proofs']))
                    require(len(row['distinct_actual_worker_pids']) == 4,
                            'Four-worker qualification did not actually execute physical jobs in four workers')
                # A failed1-worker comparison stops before any4-worker attempt.
                if workers == 1:
                    report['one_spawn_worker_qualified'] = True
        require(digest((follower, state, control, trial, forecast)) == fixed,
                'Parallel qualification mutated caller inputs')
        require(digest(actions) == bank_token, 'Parallel qualification mutated its explicit action bank')
        report['parallel_qualified'] = True
        report['exact_response_cost_quantity_equality'] = True
        report['scope'] = ('Same model/input and explicit held450s action bank, serial then1 spawned worker '
            'before optional4-worker pool requiring four actual executing worker PIDs. Compact raw pickle '
            'differences remain disclosed; qualification uses exact typed values and raw response proofs. '
            'Defensive-copy independence is separately tested in test_parallel_shared_response.py. '
            'No controller/native gain or full70-probe qualification.')
        return
    for enabled in (False, True):
        wall, cpu = time.perf_counter(), time.process_time()
        query = make_decision_shared_query(follower, state, control, forecast, horizon_steps=3,
            source_fingerprint=source_token, cache_enabled=enabled)
        rows = []
        try:
            for action in (control, trial, control, trial):
                rows.append(query((action,))['results'][0])
        finally:
            query.close()
        name = 'cache_on' if enabled else 'cache_off'
        results[name] = rows
        report[name] = {'wall_sec': time.perf_counter()-wall, 'cpu_sec': time.process_time()-cpu,
                        'stats': query.stats(), 'results_sha256': digest(rows)}
    require(pickle.dumps(results['cache_on'], protocol=5) == pickle.dumps(results['cache_off'], protocol=5),
            'Cache changed physical responses, costs, quantities, or validation evidence')
    require(digest((follower, state, control, trial, forecast)) == fixed, 'Decision query mutated caller')
    report['exact_response_cost_quantity_equality'] = True
    report['scope'] = 'Same model, two held450s actions, four sequential requests; cache-only microbenchmark, not total decision or traffic gain'
    report['wall_reduction_fraction'] = 1-report['cache_on']['wall_sec']/report['cache_off']['wall_sec']


def compare_shared_batch(state, control, forecast, cfg, tuning, report):
    """Direct actual endpoints versus repeated requests in one private batch."""
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers.area_follower_objective import evaluate_shared_owner_batch
    compare_urban_costs(state, control, forecast, cfg, tuning, report, all_owners=True)
    follower = adapter.build_priced_wu_link_controller(cfg, tuning).nash_solver
    trial = control.copy()
    for key, (_, value) in report['owner_cost_probe']['changed_vsl'].items():
        trial.vsl[key] = value
    trial.vsl['FW_E'] = min(trial.vsl[f'FW_E__seg{i}'] for i in range(21))
    frozen = digest((state, control, trial, forecast, follower))
    diagnostic_before = digest({key: value for key, value in vars(adapter).items()
                               if key.endswith('_LAST') and isinstance(value, dict)})
    batch = evaluate_shared_owner_batch(follower, state, control, forecast,
                                       (control, trial, control, trial), horizon_steps=3)
    require(batch['endpoint_calls'] == 2 and batch['cache_hits'] == 2, 'Exact request reuse failed')
    require(batch['results'][0] == batch['results'][2] and batch['results'][1] == batch['results'][3],
            'Repeated batch results differ')
    for index, name in enumerate(('recorded', 'freeway_vsl_neighbor')):
        direct = report['owner_cost_arms'][name]
        item = batch['results'][index]
        require(item['local_costs'] == direct['local_costs'], 'Private batch local costs differ from direct endpoint')
        require(item['objective_veh_h'] == direct['signature']['objective_veh_h'], 'Private batch Omega score differs')
        require(item['control_area'] == direct['signature']['control_area'], 'Private batch physical accounting differs')
        require(item['quantities'] == direct['fixed_price_algebra_smoke']['quantities'], 'Private batch accepted quantities differ')
        require(item['native_prehead_reference_overdraw_veh'] == direct['native_prehead_reference_overdraw_veh'],
                'Private batch changed prehead reference overdraw diagnostics')
    require(digest((state, control, trial, forecast, follower)) == frozen, 'Batch mutated caller operands')
    require(digest({key: value for key, value in vars(adapter).items()
                    if key.endswith('_LAST') and isinstance(value, dict)}) == diagnostic_before,
            'Batch leaked adapter diagnostic accumulators')
    report['shared_batch_probe'] = batch
    report['shared_batch_probe']['direct_costs_accounting_quantities_exact'] = True
    report['shared_batch_probe']['caller_inputs_diagnostics_preserved'] = True
    # The secant uses the same two physical responses and their own local costs.
    # Its physical identity comes from the canonical writer, never model rates alone.
    from evaluation.controllers.area_leader_objective import matched_external_secant
    from evaluation.controllers.joint_owner_game import build_ownership
    from evaluation.controllers.joint_owner_neighbors import owner_physical_fingerprints
    from evaluation.controllers.action_csv_schema import ACTION_CSV_FIELDS
    from src.models.state import segment_vsl
    mapping = read(ROOT / tuning['mapping_json'])
    plan = {'controllers': {signal[2:]: node
                           for signal, node in cfg.network.signal_actuation_contract['nodes'].items()}}
    ownership = build_ownership(cfg, mapping, plan, segment_dsd_controls=adapter._segment_dsd_controls)
    physical_tokens = []
    for action in (control, trial):
        candidate = action.copy()
        values = [segment_vsl(candidate, *adapter._segment_model_coordinates(str(seg['segment_id']), seg), cfg)
                  for seg in mapping['segments']]
        meters = adapter.real_world_ramp_meter_actions(candidate, cfg, tuning['actuation'], mapping)
        rows = list(adapter.iter_action_csv_rows(candidate, cfg, mapping, values, meters,
            {'controller_variant': 'wu-link'}, tuning['actuation'], plan,
            cfg.network.signal_actuation_contract['offset_writer']))
        physical = {}
        for row in rows:
            kind = row['kind']
            if kind == 'vsl':
                key = ('dsd', str(row['dsd_no']))
            elif kind == 'signal':
                key = ('signal_sc', str(row['sc_no']))
            elif kind == 'signal_sg':
                key = ('signal_sg', str(row['sc_no']) + ':' + str(row['dsd_no']))
            elif kind == 'ramp_meter':
                meter = next(item for item in mapping['ramp_meters'] if item['id'] == row['id'])
                require(int(meter['sc_no']) == row['sc_no'], 'Meter mapping and writer controller differ')
                key = ('signal_sg', str(row['sc_no']) + ':' + str(meter['sg_no']))
            else:
                raise ValueError('Unknown physical writer row: ' + kind)
            require(key not in physical, 'Duplicate physical row in selected full-phase plan')
            physical[key] = tuple(row.get(field, '') for field in ACTION_CSV_FIELDS if field != 'metadata')
        physical_tokens.append(owner_physical_fingerprints(ownership, physical))
    owner = 'FW_E'
    keys = [address for address in ownership.addresses if address.owner == owner
            and address.field in ('vsl', 'ramp_metering') and address.key != owner]
    before_values = {address.key: getattr(control, address.field)[address.key] for address in keys}
    after_values = {address.key: getattr(trial, address.field)[address.key] for address in keys}
    step = trial.vsl[owner+'__seg10'] - control.vsl[owner+'__seg10']
    coordinate = {'owner': owner, 'kind': 'vsl', 'parameter_unit': 'km/h', 'displacement': step,
        'base_values': before_values, 'probe_values': after_values,
        'direction': {key: (after_values[key] - value) / step for key, value in before_values.items()},
        'address_kinds': {address.key: 'vsl' if address.field == 'vsl' else 'meter' for address in keys},
        'address_owners': {address.key: owner for address in keys}, 'offset_cycles': {}}
    envelopes = []
    for index, item in enumerate(batch['results'][:2]):
        action = (control, trial)[index]
        require(item['action_token'] == digest(action), 'Returned response and requested full action differ')
        model_values = {who: {address.key: getattr(action, address.field)[address.key]
                             for address in ownership.addresses if address.owner == who}
                        for who in ownership.owners}
        envelopes.append({'objective_veh_h': item['objective_veh_h'], 'local_base_costs': item['local_base_costs'],
            'context': {'frozen_digest': item['frozen_context_token'],
                'beta_seconds': cfg.network.control_area_beta_seconds,
                'runtime_sources_digest': digest(report['source_sha256']),
                'local_cost_definition': 'shared-urban-source-cost+FW-physical-destination-cohorts/v1'},
            'response_token': item['response_token'], 'local_cost_response_token': item['response_token'],
            'model_owner_values': model_values,
            'physical_owner_tokens': physical_tokens[index], 'price_or_quantity_terms_included': False,
            'local_cost_contains_omega_beta': False})
    report['matched_external_secant_probe'] = matched_external_secant(*envelopes,
        owners=ownership.owners, owner=owner, coordinate=coordinate)


def compare_meters(state, control, forecast, cfg, report):
    from evaluation.controllers import area_meter_finalization as meters
    from src.controllers import rollout_endpoint
    frozen = digest((state, control, forecast))
    caps = dict(cfg.network.ramp_capacity_veh_h)
    total = sum(caps.values())
    directional = {d: {'mode': 'equality', 'veh_h': sum(v for r, v in caps.items()
                    if cfg.network.ramp_to_freeway[r] == d)}
                   for d in set(cfg.network.ramp_to_freeway.values())}
    kwargs = dict(owned_ramps=tuple(caps), total_budget={'mode': 'equality', 'veh_h': total},
                  directional_budgets=directional, budget_tolerance_veh_h=1e-9)
    for mode in ('equality', 'cap'):
        try:
            meters.prepare_canonical_candidate(control, cfg, **{**kwargs,
                'total_budget': {'mode': mode, 'veh_h': control.N_UF_star}})
        except meters.MeterCandidateInfeasible as exc:
            report.setdefault('rejected_original_budgets', {})[mode] = str(exc)
        else:
            raise ValueError('Original lower budget was silently increased')
    alias = control.copy()
    alias.ramp_metering = caps
    alias.N_UF_star = total
    plain = None
    for name, requested in (('recorded_request', control), ('near_capacity_request', alias)):
        prepared = meters.prepare_canonical_candidate(requested, cfg, **kwargs)
        meters.assert_writer(prepared, cfg, require_scored=True)
        require(prepared.ramp_metering == caps and prepared.N_UF_star == total,
                'All-open candidate has a different canonical model bound')
        require({k: v for k, v in vars(prepared).items() if k not in ('diagnostics', 'ramp_metering', 'N_UF_star')}
                == {k: v for k, v in vars(control).items() if k not in ('diagnostics', 'ramp_metering', 'N_UF_star')},
                'Meter preparation changed another control field')
        for meter in cfg.network.control_area_meter_context['mapping']['ramp_meters']:
            key = 'rw_meter_green_' + meter['id']
            require(prepared.diagnostics[key] == control.diagnostics[key], 'Physical meter schedule changed')
        point = rollout_endpoint.evaluate_price_point(state, prepared, forecast, (),
            rollout_endpoint.ObjectiveSpec(cfg, depth_override=3, box_walk=False, score_mode='raw'))
        require(not point.aborted and len(point.states) == 3, 'Incomplete canonical meter endpoint')
        current = signature(point)
        if plain is None:
            plain = current
        else:
            require(current == plain, 'Same canonical physical point produced different model responses')
        report.setdefault('canonical_meter_arms', {})[name] = {
            'requested_rates': dict(requested.ramp_metering), 'prepared_rates': dict(prepared.ramp_metering),
            'N_UF_star': prepared.N_UF_star, 'signature': current}
    require(digest((state, control, forecast)) == frozen, 'Preparation/query mutated original inputs')
    report['canonical_meter_result'] = {'fixed_leader_budget': total,
        'directional_budgets': directional, 'physical_schedules_preserved': True,
        'states_flows_cost_exact_between_aliases': True,
        'original_budget_silent_expansion_rejected': True,
        'legacy_solver_price_dispatch_connected': False}


def compare_fixed_game(state, control, previous, forecast, cfg, tuning, report, *, reachable=False, prices_only=False, priced_game=False, runtime_game=False, historical_inputs=None):
    """Short installed-domain integration, with strict recorded leader budgets.

    Unlike the earlier zero-price algebra smoke, this must inspect the actual
    inherited quantity modes. It cannot relabel equality as dual or enlarge an
    infeasible budget merely to obtain a candidate selection.
    """
    from evaluation.controllers import area_meter_finalization as meters
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers.area_follower_objective import (
        solve_fixed_shared_game, shared_query_runtime_scope, expand_shared_vsl_action)
    from evaluation.controllers.joint_owner_neighbors import make_joint_neighbor_callbacks, _current_meter_points
    from src.models.state import segment_vsl
    controller = adapter.build_priced_wu_link_controller(cfg, tuning)
    follower = controller.nash_solver
    np_mode = cfg.mpc.wu_faithful_np_coordination_mode
    nuf_mode = cfg.mpc.wu_faithful_nuf_coordination_mode
    leader = control.copy()
    total_budget = ({'mode': nuf_mode, 'veh_h': float(leader.N_UF_star)}
                    if nuf_mode in ('cap', 'equality') else None)
    directional = ({link: {'mode': nuf_mode, 'veh_h': min(
        float(follower._wu._omega_f[link]) * leader.N_UF_star,
        sum(cfg.network.ramp_capacity_veh_h[r] for r in cfg.network.ramps
            if cfg.network.ramp_to_freeway[r] == link))}
        for link in cfg.network.freeway_links} if total_budget else {})
    report['fixed_game_setup'] = setup = {
        'actual_np_mode': np_mode, 'actual_nuf_mode': nuf_mode,
        'leader_budget_off': cfg.mpc.leader_budget_off,
        'lambda_p': float(follower._lambda_P), 'lambda_uf': float(follower._lambda_UF),
        'recorded_target_np_veh': control.N_P_star,
        'recorded_target_nuf_veh_h': control.N_UF_star,
        'recorded_meter_rates_veh_h': dict(control.ramp_metering),
        'hard_total_budget': total_budget, 'hard_directional_budgets': directional,
        'horizon_steps': cfg.mpc.horizon_steps, 'max_sweeps': cfg.mpc.max_nash_iter,
        'price_refresh_performed': False, 'native_run': False,
        'scope': 'Recorded scalar leader targets and actual inherited domain modes; unrefreshed builder prices, not a reconstruction of the recorded outer game'}
    require(not cfg.mpc.leader_budget_off, 'PFO quantity policy is not integrated in this fixed-game query')
    previous, setup['previous_vsl_expansion'] = expand_shared_vsl_action(
        previous, cfg, segment_vsl_func=segment_vsl)
    kwargs = dict(owned_ramps=tuple(cfg.network.ramps), budget_tolerance_veh_h=1e-7)
    require(historical_inputs is not None, 'Original previous action/context/CSV are required for meter history')
    history = meters.prepare_historical_meter_reference(previous, historical_inputs['cfg'],
        written_meter_rows=historical_inputs['meter_rows'],
        source_provenance=historical_inputs['source_provenance'])
    historical = history['previous']
    setup['historical_meter_anchor'] = history['meter_anchor']
    with shared_query_runtime_scope():
        preview = meters.prepare_canonical_candidate(control, cfg, **kwargs,
            total_budget=None, directional_budgets={})
    setup['canonical_previous_meter_rates_veh_h'] = dict(historical.ramp_metering)
    setup['canonical_initial_preview_meter_rates_veh_h'] = dict(preview.ramp_metering)
    setup['canonical_initial_preview_nuf_veh_h'] = preview.N_UF_star
    meter_keys = ['rw_meter_green_' + m['id']
                  for m in cfg.network.control_area_meter_context['mapping']['ramp_meters']]
    require(all(preview.diagnostics[key] == control.diagnostics[key] for key in meter_keys),
            'Canonical initial representation changed the recorded physical meter schedules')
    setup['preview_preserves_all_eight_recorded_meter_greens'] = True
    if reachable:
        preparation_started = time.monotonic()
        require(nuf_mode == 'equality', 'Reachable diagnostic requires the actual equality policy')
        # Existing leader request sources, followed by the existing meter
        # request domains. This is a declared NEW pre-score candidate list, not
        # a replacement of the historical target or an equality tolerance hack.
        with shared_query_runtime_scope():
            raw_leaders = controller.leader.candidates(state.copy(), previous.copy(), forecast=forecast)
        targets = tuple(dict.fromkeys([float(action.N_UF_star) for action in raw_leaders]
                                     + [float(leader.N_UF_star)]))
        requests, provenance = {}, {}
        for owner in cfg.network.freeway_links:
            points, seen, sources = [], {}, []
            for index, target in enumerate(targets):
                source_leader = leader.copy()
                source_leader.N_UF_star = target
                with shared_query_runtime_scope():
                    current, mode, budget, source = _current_meter_points(
                        follower, owner, preview, source_leader, previous)
                sources.append({'index': index, 'raw_target_nuf_veh_h': target,
                                'budget_mode': mode, 'direction_budget_veh_h': budget, 'source': source})
                for label, pair in current:
                    key = tuple(sorted(pair.items()))
                    if key not in seen:
                        seen[key] = len(points)
                        points.append((f'leader{index}:{label}', pair))
            requests[owner] = tuple(points)
            provenance[owner] = {'queries': sources,
                'previous_box_source': 'Recorded previous final write-back rates before canonical normalization',
                'candidate_leader_source': 'Installed Leader.candidates, plus recorded target'}
        with shared_query_runtime_scope():
            bank = meters.reachable_meter_budgets(control, cfg, directional_requests=requests,
                source_provenance=provenance, budget_tolerance_veh_h=1e-7)
        compatible = []
        for index, candidate in enumerate(bank['candidates']):
            expected = {owner: follower._wu._omega_f[owner] * candidate['total_budget_veh_h']
                        for owner in cfg.network.freeway_links}
            ok = all(abs(candidate['directional_budgets_veh_h'][owner] - expected[owner]) <= 1e-7
                     for owner in cfg.network.freeway_links)
            if ok:
                compatible.append(index)
        report['reachable_budget_preflight'] = {k: v for k, v in bank.items() if k != 'candidates'}
        report['reachable_budget_preflight']['candidates'] = [
            {k: v for k, v in candidate.items() if k != 'control'} for candidate in bank['candidates']]
        report['reachable_budget_preflight']['fixed_omega_compatible_indices'] = compatible
        report['reachable_budget_preflight']['raw_leader_nuf_requests_veh_h'] = targets
        report['reachable_budget_preflight']['elapsed_sec'] = time.monotonic() - preparation_started
        print(json.dumps({'stage': 'reachable_budget_preflight', 'request_product': bank['requested_count'],
                          'canonical_candidates': bank['candidate_count'],
                          'fixed_omega_compatible': len(compatible)}), flush=True)
        require(compatible, 'No realized budget can be represented by the unchanged fixed-omega leader')
        selected_index = min(compatible, key=lambda i: (
            abs(bank['candidates'][i]['total_budget_veh_h'] - control.N_UF_star), i))
        selected = bank['candidates'][selected_index]
        leader.N_UF_star = selected['total_budget_veh_h']
        total_budget = {'mode': 'equality', 'veh_h': leader.N_UF_star}
        directional = {owner: {'mode': 'equality', 'veh_h': amount}
                       for owner, amount in selected['directional_budgets_veh_h'].items()}
        setup.update(new_pre_score_target_nuf_veh_h=leader.N_UF_star,
            new_pre_score_directional_budgets=directional,
            reachable_candidate_index=selected_index,
            candidate_selection_policy='Nearest feasible canonical budget to recorded request, stable source order; initialization smoke, NOT an objective optimum or reconstructed recorded leader choice',
            original_target_was_replaced_before_any_score=True,
            original_target_equality_failure_preserved='fixed_shared_game_t900_v1_actual_budget.json')
        initial_request = selected['control']
    else:
        initial_request = control
    with shared_query_runtime_scope():
        initial = meters.prepare_canonical_candidate(initial_request, cfg, **kwargs,
            total_budget=total_budget, directional_budgets=directional)
    setup['initial_passed_actual_hard_budgets'] = True
    # Cap quantity/PFO policies need their actual shared quantity constraint,
    # not a zero-lambda substitution under a differently named policy.
    require(np_mode in ('dual', 'cap') and nuf_mode in ('dual', 'equality'),
            'Actual quantity mode is not yet supported by the shared fixed-price payoff')
    mapping = read(ROOT / tuning['mapping_json'])
    if runtime_game:
        from evaluation.controllers.area_follower_objective import solve_runtime_joint_candidate
        proposal = {'control': initial, 'target_np_veh': leader.N_P_star,
                    'target_nuf_veh_h': leader.N_UF_star, 'directional_budgets': directional}
        result = solve_runtime_joint_candidate(controller, state, forecast, historical, proposal, mapping,
            runtime_sources=report['source_sha256'], options={
                'max_evaluations': 80, 'time_budget_sec': 240., 'improvement_tolerance': 1e-7,
                'shared_tolerance': 1e-7, 'np_tolerance_veh': 1e-7, 'nuf_tolerance_veh_h': 1e-7,
                'traversal': 'round_robin'},
            progress=lambda event: print(json.dumps(event), flush=True))
        result['response']['game']['control'] = vars(result['response']['game']['control'])
        result['validated_nash']['control'] = vars(result['validated_nash']['control'])
        result['response']['command_evidence'].pop('physical_rows', None)
        report['runtime_joint_candidate'] = result
        setup['scope'] = 'Production joint candidate function with round-robin traversal; fixed initialization smoke, no leader optimum or native execution'
        return
    plan = {'controllers': {signal[2:]: node
                           for signal, node in cfg.network.signal_actuation_contract['nodes'].items()}}
    # configure() already froze the same merged calibration+tuning settings
    # used by the real writer. Raw tuning omits effective defaults.
    actuation = cfg.network.control_area_meter_context['actuation']
    setup['actuation_source'] = 'Configured actual writer context after calibration+tuning merge'
    setup['raw_tuning_actuation_equals_effective'] = tuning.get('actuation') == actuation
    private_state, private_action = state.copy(), initial.copy()
    with shared_query_runtime_scope():
        coupling = follower._wu._coupling(private_state, private_action, forecast[0])
    context = {'follower': follower, 'state': state, 'forecast': forecast,
        'previous': historical, 'reference': initial, 'leader': leader, 'coupling': coupling,
        'mapping': mapping, 'selected_plan': plan, 'actuation': actuation,
        'runtime_sources': report['source_sha256'], 'total_budget': total_budget,
        'directional_budgets': directional}
    def fingerprint(value):
        runtime = {k: v for k, v in vars(adapter).items()
                   if k.startswith('_') and k.isupper() and isinstance(v, (dict, list, set))}
        return digest((value, runtime))
    def bind_callbacks():
        return make_joint_neighbor_callbacks(follower, state, coupling, forecast[0],
            leader, historical, mapping, plan, actuation, {'controller_variant': 'wu-link'},
            segment_vsl_func=segment_vsl, context=context, context_fingerprint=fingerprint,
            query_scope=shared_query_runtime_scope, held_horizon_sec=cfg.mpc.horizon_steps * cfg.simulation.T_c_sec,
            budget_tolerance_veh_h=1e-7, total_budget=total_budget, directional_budgets=directional,
            previous_meter_anchor=history['meter_anchor'],
            freeway_joint_pairs=lambda owner, domain: tuple((head, value, label)
                for head, values in domain.head_values.items() for value in values
                for label, _ in domain.meter_points))
    callbacks = bind_callbacks()
    original_neighbors = callbacks['neighbors']
    def observed_neighbors(owner, action, supplied):
        domain = original_neighbors(owner, action, supplied)
        print(json.dumps({'stage': 'fixed_game_neighbors', 'owner': owner,
                          'candidate_count': len(domain.candidates), 'domain_complete': domain.complete}), flush=True)
        return domain
    callbacks['neighbors'] = observed_neighbors
    if prices_only or priced_game:
        from evaluation.controllers.area_runtime import evaluate_joint_prices
        report['joint_price_measurement'] = evaluate_joint_prices(
            follower, state, initial, forecast, callbacks=callbacks, context=context,
            context_fingerprint=fingerprint, horizon_steps=cfg.mpc.horizon_steps,
            directional_nuf_targets_veh_h={owner: row['veh_h'] for owner, row in directional.items()},
            nuf_tolerance_veh_h=1e-7, source_fingerprint=digest(report['source_sha256']),
            progress=lambda event: print(json.dumps(event), flush=True))
        setup['price_refresh_performed'] = True
        setup['scope'] = 'Actual matched joint-price measurements at a new reachable pre-score budget; no leader search or native run'
        if prices_only:
            return
        from evaluation.controllers.area_leader_objective import install_joint_price_field
        measured = report['joint_price_measurement']
        expected_context = {
            'frozen_digest': digest((fingerprint(context), measured['responses']['results'][0]['frozen_context_token'])),
            'beta_seconds': cfg.network.control_area_beta_seconds,
            'runtime_sources_digest': digest(report['source_sha256']),
            'local_cost_definition': 'shared-urban-source-cost+FW-physical-destination-cohorts/v1'}
        setup['price_installation'] = install_joint_price_field(
            follower, initial, measured['field'], expected_owners=callbacks['ownership'].owners,
            expected_context=expected_context, nuf_mode=nuf_mode)
        measured['holders_installed'] = True
        # Prices/references are bound by the factory. Never reuse pre-install
        # callbacks or auto-toggle the meter split/trust policy to accept them.
        callbacks = bind_callbacks()
        original_neighbors = callbacks['neighbors']
        callbacks['neighbors'] = observed_neighbors
        setup['post_install_context_fingerprint'] = fingerprint(context)
        setup['scope'] = 'Actual matched prices installed before fixed-price shared selection; finite inherited domain and original smoke work limits; no leader update or native run'
    attrs = {'phase': 'signal_phase_price', 'offset': 'offset_marginal_price',
             'vsl': 'vsl_marginal_price', 'meter': 'metering_marginal_price'}
    keys = {'phase': tuple(initial.green_times), 'offset': tuple(initial.offsets),
            'vsl': tuple(k for k in initial.vsl if '__seg' in k), 'meter': tuple(initial.ramp_metering)}
    inactive = {}
    for channel, attribute in attrs.items():
        prices = getattr(follower, attribute)
        if priced_game:
            require(isinstance(prices, dict) and prices, 'Measured price channel was not installed')
            inactive[channel] = []
        else:
            require(prices in (None, {}), 'Fixed-game smoke requires explicit unrefreshed builder prices')
            inactive[channel] = list(keys[channel]) if prices == {} else []
    result = solve_fixed_shared_game(follower, state, initial, forecast, initial,
        callbacks=callbacks, context=context, context_fingerprint=fingerprint,
        horizon_steps=cfg.mpc.horizon_steps, lambda_p=follower._lambda_P, lambda_uf=follower._lambda_UF,
        target_np_veh=leader.N_P_star, target_nuf_veh_h=leader.N_UF_star,
        price_context={'leader_present': True, 'np_mode': np_mode, 'nuf_mode': nuf_mode,
                       'inactive_price_addresses': inactive},
        max_sweeps=cfg.mpc.max_nash_iter, max_evaluations=80, time_budget_sec=240.,
        improvement_tolerance=1e-7, shared_tolerance=1e-7,
        np_tolerance_veh=1e-7, nuf_tolerance_veh_h=1e-7,
        scope_label='Short fixed inherited-domain smoke; full held450s trajectory, declared evaluation/time limits')
    result['game']['control'] = vars(result['game']['control'])
    # Tuple-keyed native rows are represented by the already retained ordered
    # CSV rows. Do not manufacture a second command representation for JSON.
    result['command_evidence'].pop('physical_rows', None)
    report['fixed_game_result'] = result


@contextmanager
def capture_offramp_supply_frames(cfg, start_sec, end_sec):
    """Read two reservoirs at existing operand samples; restore even on failure."""
    from evaluation.controllers.control_area_objective import ModelAreaLedger
    original = ModelAreaLedger.record_freeway_operands
    frames = []

    def record(ledger, state, control, actual_ramp_release=None, *, initial=False):
        result = original(ledger, state, control, actual_ramp_release, initial=initial)
        if not ledger.captures_response:
            return result
        stamp = {'start_sec': float(state.time_sec)} if initial else ledger._response_stamp()
        sec = stamp.get('end_sec', stamp['start_sec'])
        if start_sec <= sec <= end_sec:
            step = sec / cfg.simulation.T_u_sec
            require(step == int(step), 'Off-ramp sample is not on the urban clock')
            reservoirs = {}
            for off in ('OR_F_W', 'OR_F_E'):
                storage = cfg.network.off_ramp_storage_link[off]
                capacity = float(cfg.network.urban_link_storage_veh[storage])
                available = float(state.urban_link_storage[storage])
                pending = dict(state.offramp_transit_buffer.get(storage, {}))
                occupied = max(0.0, capacity - available)
                not_ready = sum(value for due, value in pending.items() if due > int(step))
                reservoirs[off] = {'storage': storage, 'capacity_veh': capacity,
                    'available_veh': available, 'occupied_veh': occupied,
                    'pending_by_due_urban_step': pending,
                    'pending_not_ready_at_sample_veh': not_ready,
                    'ready_storage_at_sample_veh': max(0.0, occupied - not_ready)}
            frames.append({'time_sec': sec, 'urban_step_index': int(step),
                           'initial': initial, 'reservoirs': reservoirs})
        return result

    ModelAreaLedger.record_freeway_operands = record
    try:
        yield frames
    finally:
        ModelAreaLedger.record_freeway_operands = original


def summarize_offramp_supply(cfg, frames, transfers, resource_rows, delay_steps):
    """Join accepted events to observed bins; beta is not a destination census."""
    require(frames and frames[0]['initial'] and all(not row['initial'] for row in frames[1:]),
            'Off-ramp supply requires one initial sample')
    sim, net = cfg.simulation, cfg.network
    output = {'schema': 'held-offramp-supply-balance/v1',
        'scope': 'Initial and post-FW-landing stocks; actual accepted events and pending bins, not native observations',
        'pending_semantics': 'Raw bins may retain due-now entries until the next urban drain; ready uses due > sample step',
        'beta_semantics': 'Per-service fraction of shared ready storage, not fixed destination cohorts',
        'delay_inputs': {'urban_boundary_link_length_m': net.urban_boundary_link_length_m,
            'urban_avg_speed_km_h': net.urban_avg_speed_km_h,
            'T_u_sec': sim.T_u_sec, 'T_u_h': sim.T_u_h, 'T_f_sec': sim.T_f_sec,
            'K_fu': sim.K_fu, 'inflow_delay_steps': delay_steps,
            'inflow_delay_sec': delay_steps * sim.T_u_sec},
        'frames': frames, 'offramps': {}}
    for off in ('OR_F_W', 'OR_F_E'):
        storage = net.off_ramp_storage_link[off]
        key = 'storage:' + storage
        incoming = [dict(row) for row in transfers if row['target'] == key]
        outgoing = [dict(row) for row in transfers if row['source'] == key]
        for row in incoming:
            require(row['route_key'] == 'offramp_signal:' + off and row['stage'] == 'landing',
                    'Unexpected off-ramp storage supply: ' + off)
            step = row['end_sec'] / sim.T_u_sec
            require(step == int(step), 'Off-ramp landing is not on the urban clock')
            row.update(scheduled_from_urban_step=int(step), due_urban_step=int(step) + delay_steps,
                       due_sec=(int(step) + delay_steps) * sim.T_u_sec)
        checks = []
        for before, after in zip(frames, frames[1:]):
            lo, hi = before['time_sec'], after['time_sec']
            require(hi - lo == sim.T_f_sec, 'Missing off-ramp post-landing sample')
            entered = [row for row in incoming if lo <= row['start_sec'] < row['end_sec'] <= hi]
            departed = [row for row in outgoing if lo <= row['start_sec'] < row['end_sec'] <= hi]
            a, b = before['reservoirs'][off], after['reservoirs'][off]
            # The last drain was at (post-landing step - 1), not at the next
            # urban start. Preserve a due-now bin exactly as the scheduler does.
            last_drain = after['urban_step_index'] - 1
            expected = {due: value for due, value in a['pending_by_due_urban_step'].items() if due > last_drain}
            for row in entered:
                due = row['due_urban_step']
                expected[due] = expected.get(due, 0.0) + row['vehicles']
            actual = b['pending_by_due_urban_step']
            bin_error = max((abs(expected.get(due, 0.0) - actual.get(due, 0.0))
                             for due in expected.keys() | actual.keys()), default=0.0)
            residual = b['occupied_veh'] - a['occupied_veh'] - sum(row['vehicles'] for row in entered) + sum(row['vehicles'] for row in departed)
            require(set(expected) == set(actual) and bin_error < 1e-8,
                    'Off-ramp observed due bins differ from accepted landing schedule: ' + off)
            require(abs(residual) < 1e-8, 'Off-ramp accepted-flow stock balance differs: ' + off)
            checks.append({'start_sec': lo, 'end_sec': hi, 'last_drained_urban_step': last_drain,
                'signal_accepted_veh': sum(row['vehicles'] for row in entered),
                'all_branches_outgoing_veh': sum(row['vehicles'] for row in departed),
                'stock_balance_residual_veh': residual, 'pending_bin_max_error_veh': bin_error})
        movements = list(net.off_ramp_to_movement[off])
        output['offramps'][off] = {'storage': storage, 'freeway': net.off_ramp_from_freeway[off],
            'configured_segment_index': net.off_ramp_segment_index.get(off),
            'off_ramp_split_ratio': net.off_ramp_split_ratio.get(off, 0.0),
            'direct_share': getattr(net, 'offramp_direct_share_by_offramp', {}).get(off, 0.0),
            'direct_target': getattr(net, 'offramp_direct_tail_by_offramp', {}).get(off),
            'movements': {name: {field: net.urban_movements[name].get(field) for field in
                ('kind', 'origin', 'receiving_link', 'phase', 'beta')} for name in movements},
            'signal_landings_with_verified_due': incoming, 'all_storage_outgoing': outgoing,
            'direct_landings_bypassing_storage': [dict(row) for row in transfers if row['route_key'] == 'offramp_direct:' + off],
            'source_ready_and_fw_limits': [dict(row) for row in resource_rows if (
                row['kind'] == 'offramp_source_ready' and row['resource'] in movements) or (
                row['kind'] in ('freeway_offramp_sending', 'freeway_offramp_receiving') and row['resource'] == off)],
            'interval_checks': checks}
    return output


def boundary_window_response(state, control, forecast, cfg, report):
    """One recorded held query; inspect its first interval, never raw-flow TD."""
    from src.controllers import rollout_endpoint
    from src.models import urban_queue_model as uqm
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers.area_meter_finalization import assert_writer
    sec, end = float(state.time_sec), float(state.time_sec) + 150.0
    require(sec == 900.0 and float(cfg.simulation.T_c_sec) == 150.0,
            'Boundary window requires the recorded 900..1050 interval')
    initial_ledger = state._control_area_ledger
    require(initial_ledger.event_count == 0
            and all(value == 0.0 for value in vars(initial_ledger.metrics).values()),
            'Boundary window requires an unaccumulated initial ledger')
    aliases = ('SC1004_W_to_S', 'SC1004_offW_to_S', 'SC1004_offE_to_S')
    origin, receiver = 'in_SC1004_W', 'SC1004_S_out'
    routes = cfg.network.control_area_routes
    for name in aliases:
        route = routes['movement:' + name]
        require(route.get('source_inside') is True and route.get('target_inside') is False
                and route.get('outward_crossings_per_vehicle') == 1
                and route.get('inward_crossings_per_vehicle') == 0
                and any(turn.get('connector') == '10642' for turn in route.get('physical_turns', [])),
                'SC1004 alias no longer represents the reviewed outward turn: ' + name)
    shared = cfg.network.shared_approach
    require(shared['branches']['4']['connector'] == '10640'
            and shared['branches']['4']['target'] == origin, 'Shared69 branch4 target changed')
    shared_storage = shared['storage']
    delay_metadata = {
        'tau_length_cap_enabled': bool(adapter._tau_length_cap_enabled()),
        'physical_length_m': adapter._storage_length_m().get(origin),
        'observed_speed_delay_cap_ratio': uqm.OBSERVED_SPEED_DELAY_CAP_RATIO,
        'installed_link_delay_function': {'module': uqm._link_delay_steps.__module__,
                                         'qualname': uqm._link_delay_steps.__qualname__}}
    assert_writer(control, cfg, require_scored=True)
    frozen = digest((state, control, forecast))
    inflow_delay_steps = uqm._inflow_delay_steps(cfg)
    started = time.monotonic()
    with capture_offramp_supply_frames(cfg, sec, end) as supply_frames:
        point = rollout_endpoint.evaluate_price_point(state, control, forecast, (),
            rollout_endpoint.ObjectiveSpec(cfg, depth_override=3, box_walk=False, score_mode='raw'),
            capture_response=True)
    elapsed = time.monotonic() - started
    require(not point.aborted and len(point.states) == 3, 'Incomplete held endpoint')
    require(digest((state, control, forecast)) == frozen, 'Boundary query mutated inputs')
    control_fields = ('N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times',
                      'offsets', 'inflow_outflow_allocation')
    require(all(getattr(point.control, key) == getattr(control, key) for key in control_fields),
            'Held endpoint changed a recorded control field')
    first = point.states[0]
    require(float(first.time_sec) == end, 'First endpoint is not 1050')
    response = point.control_area_response
    require(response['shared_capacity_certificate'] is False, 'Unproved physical capacity certificate')

    def in_window(row):
        start, stop = row['start_sec'], row['end_sec']
        require(sec <= start < stop <= sec + 450.0, 'Invalid response clock')
        require(not start < end < stop, 'Response event straddles the first interval boundary')
        return stop <= end

    transfers = [row for row in response['transfers'] if in_window(row)]
    residence = [row for row in response['residence'] if in_window(row)]
    totals = {'ttd_veh': sum(row['ttd_veh'] for row in transfers),
              'entered_veh': sum(row['entered_veh'] for row in transfers),
              'ttt_veh_h': sum(row['dt_h'] * sum(row['inside_veh'].values()) for row in residence)}
    closing = first._control_area_ledger
    errors = {key: value - getattr(closing, key) for key, value in totals.items()}
    require(len(transfers) == closing.event_count, 'First-window accepted event coverage differs')
    require(all(abs(value) < 1e-8 for value in errors.values()), 'First-window accounting does not close')
    grouped = {}
    for row in transfers:
        key = (row['route_key'], row['source'], row['target'], row['stage'])
        item = grouped.setdefault(key, dict(zip(('route_key', 'source', 'target', 'stage'), key),
                                           ttd_veh=0.0, entered_veh=0.0, accepted_veh=0.0, events=0))
        for target, source in (('ttd_veh', 'ttd_veh'), ('entered_veh', 'entered_veh'), ('accepted_veh', 'vehicles')):
            item[target] += row[source]
        item['events'] += 1
    terminal_keys = {f'freeway:{link}->external:terminal:{link}' for link in cfg.network.freeway_links}
    terminal = sum(row['ttd_veh'] for row in transfers if row['route_key'] in terminal_keys)
    alias_keys = {'movement:' + name for name in aliases}
    selected_keys = alias_keys | {'arrival:' + name for name in aliases}
    selected_keys.add(f'storage:{shared_storage}->storage:{origin}')
    resources = [row for row in response['resource_allocations'] if in_window(row) and (
        bool(alias_keys.intersection(row['accepted_by_source_veh']))
        or (row['kind'] == 'regular_receiving' and row['resource'] == 'storage:' + receiver)
        or 'shared:' + shared_storage + ':branch:4' in row['accepted_by_source_veh'])]
    require(len(supply_frames) == 1 + int((end - sec) / cfg.simulation.T_f_sec)
            and supply_frames[0]['time_sec'] == sec and supply_frames[-1]['time_sec'] == end,
            'Incomplete off-ramp supply samples')
    supply_balance = summarize_offramp_supply(cfg, supply_frames, transfers,
        [row for row in response['resource_allocations'] if in_window(row)], inflow_delay_steps)
    supply_balance['delay_inputs']['installed_inflow_delay_function'] = {
        'module': uqm._inflow_delay_steps.__module__, 'qualname': uqm._inflow_delay_steps.__qualname__}
    stocks = ('storage:' + origin, 'storage:' + receiver, 'storage:' + shared_storage)
    frames = [response['initial_freeway_operands']] + [row for row in response['freeway_frames'] if in_window(row)]
    source_frames = [{'time_sec': row.get('end_sec', row['start_sec']),
                      'movement_queue_veh': {name: row['urban_movement_queue'][name] for name in aliases},
                      'model_stock_veh': {key: row['model_stock_veh'][key] for key in stocks},
                      'shared69_branch4_bins': row['shared_approach_state']['bins']['4']} for row in frames]
    specs = {name: {key: cfg.network.urban_movements[name].get(key) for key in
                   ('kind', 'origin', 'receiving_link', 'phase', 'beta', 'turn', 'unsignalized')}
             for name in aliases}
    report['boundary_window'] = {
        'schema': 'held-boundary-window/v1', 'start_sec': sec, 'end_sec': end,
        'held_signature': signature(point),
        'endpoint_calls': 1, 'endpoint_elapsed_sec': elapsed, 'held_horizon_sec': 450,
        'scope': 'Current-source recorded-action model response; no native effect or capture OFF/ON comparison',
        'metrics': totals, 'ledger_metrics': vars(closing.metrics), 'metric_reconstruction_error': errors,
        'accepted_events': len(transfers), 'residence_records': len(residence),
        'terminal_ttd_veh': terminal, 'nonterminal_ttd_veh': totals['ttd_veh'] - terminal,
        'terminal_route_keys': sorted(terminal_keys),
        'boundary_routes': [row for row in grouped.values() if row['ttd_veh'] or row['entered_veh']],
        'route_accepted_veh_is_not_ttd': True,
        'offramp_supply_balance': supply_balance,
        'sc1004_10642': {'aliases': list(aliases),
            'ttd_veh': sum(row['ttd_veh'] for row in transfers if row['route_key'] in alias_keys),
            'transfers': [row for row in transfers if row['route_key'] in selected_keys],
            'resource_allocations': resources, 'source_frames': source_frames, 'movement_specs': specs,
            'movement_capacities_veh_h': {name: cfg.network.movement_capacity_by_movement_veh_h.get(name)
                                         for name in aliases},
            'held_green_times': {key: value for key, value in control.green_times.items() if key.startswith('SC1004_')},
            'held_offset_sec': control.offsets['SC1004'],
            'allocation_values': {key: control.inflow_outflow_allocation[key] for key in
                set(aliases) | {cfg.network.urban_movements[name][field] for name in aliases for field in ('origin', 'destination')}
                if key in control.inflow_outflow_allocation},
            'arrival_delay_inputs': {**delay_metadata, 'origin': origin,
                'capacity_veh': cfg.network.urban_link_storage_veh[origin],
                'initial_available_veh': state.urban_link_storage[origin],
                'observed_corrected_speed_kph': state.urban_link_speed_kph.get(origin),
                'nominal_speed_kph': cfg.network.urban_avg_speed_km_h,
                'vehicle_length_m': cfg.network.urban_avg_vehicle_length_m,
                'initial_arrival_buffer': state.urban_arrival_buffer.get(origin, {}),
                'final_arrival_buffer': first.urban_arrival_buffer.get(origin, {}),
                'scope': 'Existing initial/final operands only; intermediate enqueue time/delay is not captured'}},
        'shared_capacity_certificate': False, 'physical_native_fidelity_certificate': False}


def compare(args, report):
    report['environment'] = validate_environment()
    import os
    report['environment']['RW_OFFSET_WRITER'] = os.environ.get('RW_OFFSET_WRITER', '')
    baseline = read(args.baseline)
    require(baseline.get('completed') is True, 'Reference alias probe did not complete')
    changes = []
    pinned = []
    for name, before_sha in baseline['source_sha256'].items():
        path = (ROOT / name).resolve(strict=True)
        after_sha = sha(path)
        if before_sha != after_sha:
            require(path.relative_to(ROOT).as_posix() in PREPARATION_EDITS,
                    'Unrelated fixture/source changed: ' + str(path))
            changes.append({'path': str(path.relative_to(ROOT)),
                            'before_sha256': before_sha, 'current_sha256': after_sha})
        pinned.append(path)
    report['preparation_source_changes'] = changes
    run = Path(baseline['run'])
    sec = int(baseline['sim_sec'])
    decision = run / ('decisions_' + run.name)
    config = args.config.resolve(strict=True)
    manifest = read(run / ('run_provenance_' + run.name + '.json'))
    require(sha(config) == manifest['files']['tuning']['sha256'], 'Config changed from completed run')
    state_path = decision / f'state_{sec:06d}.json'
    previous_path = decision / f'action_{sec-150:06d}.json'
    action_path = decision / f'action_{sec:06d}.json'
    for path in (config, state_path, previous_path, action_path):
        require(path.resolve() in pinned, 'Reference did not pin input: ' + str(path))
    from diagnostics.probe_model_area_integration import build_projected, replay_provenance
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from src.controllers import rollout_endpoint
    from src.models.state import ControlAction
    from src.models.demand import DemandStep
    if args.mode == 'sink-order':
        pinned.extend((SINK_ORDER_ARCHIVE, SINK_ORDER_ARCHIVE.with_suffix('.sha256.json')))
    if args.mode in ('shared-batch', 'fixed-game', 'reachable-game', 'joint-prices', 'priced-game', 'runtime-game'):
        # Include these production inputs in the before/after source pin set.
        from evaluation.controllers import joint_owner_game, joint_owner_neighbors
    historical_inputs = None
    if args.mode in ('fixed-game', 'reachable-game', 'joint-prices', 'priced-game', 'runtime-game'):
        # Build history first so the current decision's runtime installation is
        # last. Never re-run the old meter allocation with current observations.
        import csv
        history_state = decision / f'state_{sec-150:06d}.json'
        history_previous = decision / f'action_{sec-300:06d}.json'
        history_csv = decision / f'action_{sec-150:06d}.csv'
        history_paths = (history_state, history_previous, history_csv, previous_path)
        history_pins = {str(path.relative_to(ROOT)): sha(path) for path in history_paths}
        history_cfg = build_projected(config, history_state, history_previous, fixture_inputs=False)[0]
        with history_csv.open(encoding='utf-8-sig', newline='') as stream:
            history_rows = [row for row in csv.DictReader(stream) if row['kind'] == 'ramp_meter']
        historical_inputs = {'cfg': history_cfg, 'meter_rows': history_rows,
            'source_provenance': {'source_sha256': history_pins,
                                  'recorded_run': str(run), 'sim_sec': sec-150}}
        report['historical_meter_input_sources'] = history_pins
        pinned.extend(path for path in history_paths if path not in pinned)
    cfg, state, detectors, tuning, raw, mapping, meta = build_projected(
        config, state_path, previous_path, fixture_inputs=False)
    require(cfg.network.control_area_enabled and cfg.mpc.horizon_steps == 3, 'Expected Omega/450s')
    calibration = adapter.deep_update(dict(adapter.load_optional_json(str(ROOT /
        'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))),
        tuning.get('calibration_override', {}))
    forecast = adapter.demand_from_state(raw, cfg, DemandStep, 3, calibration, detectors)
    control = adapter.control_from_json(action_path, cfg, ControlAction)
    frozen = digest((state, control, forecast))
    before = replay_provenance(tuning, Path(__file__), args.baseline, *pinned)
    report.update(run=str(run), sim_sec=sec, source_sha256=before, arms={})
    try:
        if args.mode == 'sink-order':
            compare_sink_order(state, control, forecast, cfg, report, args.out)
            return
        if args.mode == 'boundary-window':
            if args.profile_endpoint:
                import cProfile
                profiler = cProfile.Profile()
                profiler.enable()
                try:
                    boundary_window_response(state, control, forecast, cfg, report)
                finally:
                    profiler.disable()
                    profile_path = args.out.with_suffix('.pstats')
                    profiler.dump_stats(str(profile_path))
                    report['endpoint_profile'] = {'path': str(profile_path),
                        'timings_include_profile_overhead': True}
            else:
                boundary_window_response(state, control, forecast, cfg, report)
            return
        if args.mode == 'decision-cache':
            workers = getattr(args, 'parallel_workers', 0)
            bootstrap = None
            if workers:
                bootstrap = {'state_json': {'network_path': str(adapter._network_path_from_state(raw).resolve(strict=True))},
                    'detector_mapping': detectors,
                    'runtime_sources': {str((ROOT/name).resolve(strict=True)): value for name, value in before.items()}}
            compare_decision_cache(state, control, forecast, cfg, tuning, report,
                parallel_workers=workers, worker_bootstrap=bootstrap,
                deadline_sec=getattr(args, 'parallel_deadline_sec', 120.),
                response_audit_dir=(args.out.resolve().with_suffix('.responses')
                    if getattr(args, 'parallel_response_audit', False) else None),
                compact_results_dir=args.out.resolve().with_suffix('.compact') if workers else None)
            return
        if args.mode == 'ledger-copy':
            import copy
            from unittest.mock import patch
            from evaluation.controllers import control_area_objective as ledger
            before_inputs = digest((state, control, forecast, cfg))
            comparisons = {}
            for optimized in (False, True):
                local = {}
                wall, cpu = time.perf_counter(), time.process_time()
                copier = ledger._copy_response_tree if optimized else copy.deepcopy
                with patch.object(ledger, '_copy_response_tree', copier):
                    boundary_window_response(state, control, forecast, cfg, local)
                name = 'optimized' if optimized else 'original_copy'
                comparisons[name] = {'wall_sec': time.perf_counter()-wall,
                    'cpu_sec': time.process_time()-cpu, 'boundary_window': local['boundary_window']}
            original = dict(comparisons['original_copy']['boundary_window'])
            improved = dict(comparisons['optimized']['boundary_window'])
            original.pop('endpoint_elapsed_sec'); improved.pop('endpoint_elapsed_sec')
            require(pickle.dumps(original, protocol=5) == pickle.dumps(improved, protocol=5),
                    'Ledger copy optimization changed full held physical state/flow/cost or selected boundary evidence')
            require(before_inputs == digest((state, control, forecast, cfg)), 'Ledger A/B changed caller operands')
            report['ledger_copy_comparison'] = comparisons
            report['exact_full_horizon_and_boundary_equality'] = True
            report['wall_reduction_fraction'] = 1-comparisons['optimized']['wall_sec']/comparisons['original_copy']['wall_sec']
            return
        if args.mode in ('fixed-game', 'reachable-game', 'joint-prices', 'priced-game', 'runtime-game'):
            previous = adapter.control_from_json(previous_path, cfg, ControlAction)
            compare_fixed_game(state, control, previous, forecast, cfg, tuning, report,
                               reachable=args.mode in ('reachable-game', 'joint-prices', 'priced-game', 'runtime-game'),
                               prices_only=args.mode == 'joint-prices', priced_game=args.mode == 'priced-game', runtime_game=args.mode == 'runtime-game',
                               historical_inputs=historical_inputs)
            return
        if args.mode == 'shared-batch':
            compare_shared_batch(state, control, forecast, cfg, tuning, report)
            return
        if args.mode in ('urban-cost', 'owner-cost'):
            compare_urban_costs(state, control, forecast, cfg, tuning, report, all_owners=args.mode == 'owner-cost')
            return
        if args.mode == 'canonical-meter':
            compare_meters(state, control, forecast, cfg, report)
            return
        plain = None
        for capture in (False, True):
            started = time.monotonic()
            point = rollout_endpoint.evaluate_price_point(state, control, forecast, (),
                rollout_endpoint.ObjectiveSpec(cfg, depth_override=3, box_walk=False, score_mode='raw'),
                capture_response=capture)
            elapsed = time.monotonic() - started
            require(not point.aborted and len(point.states) == 3, 'Incomplete endpoint')
            require(digest((state, control, forecast)) == frozen, 'Query mutated inputs')
            current = signature(point)
            name = 'capture_on' if capture else 'capture_off'
            report['arms'][name] = {'elapsed_sec': elapsed, 'signature': current}
            if not capture:
                require(not hasattr(point, 'control_area_response'), 'OFF unexpectedly captured response')
                plain = current
                continue
            require(current == plain, 'Capture changed physical states/flows/endpoint')
            response = point.control_area_response
            require(response['shared_capacity_certificate'] is False, 'Unproved capacity certificate')
            flows = Counter()
            td = entered = ttt = 0.0
            stages = Counter()
            for row in response['transfers']:
                require(sec <= row['start_sec'] < row['end_sec'] <= sec + 450, 'Invalid transfer clock')
                flows[row['route_key']] += row['vehicles']
                td += row['ttd_veh']
                entered += row['entered_veh']
                stages[row['stage']] += 1
            for row in response['residence']:
                require(sec <= row['start_sec'] < row['end_sec'] <= sec + 450, 'Invalid residence clock')
                ttt += row['dt_h'] * sum(row['inside_veh'].values())
            closing = point.states[-1]._control_area_ledger
            require(len(response['transfers']) == closing.event_count, 'Accepted event coverage differs')
            require(all(v == closing.flow_counts[k] for k, v in flows.items()), 'Accepted route totals differ')
            errors = {'ttt_veh_h': ttt - closing.ttt_veh_h,
                      'ttd_veh': td - closing.ttd_veh, 'entered_veh': entered - closing.entered_veh}
            require(all(abs(v) < 1e-8 for v in errors.values()), 'Response accounting does not close')
            report['response_summary'] = {'accepted_events': len(response['transfers']),
                'residence_records': len(response['residence']), 'stages': dict(stages),
                'metric_reconstruction_error': errors, 'physical_states_and_flows_exact': True,
                'shared_capacity_certificate': False}
        report['historical_recorded_objective_equal'] = (
            plain['objective_veh_h'] == baseline['arms']['recorded']['objective_veh_h'])
    finally:
        after = replay_provenance(tuning, Path(__file__), args.baseline, *pinned)
        report['source_changes_during_query'] = [p for p, h in before.items() if after.get(p) != h]
        require(not report['source_changes_during_query'], 'Source/input changed while querying')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--profile-endpoint', action='store_true')
    parser.add_argument('--parallel-workers', type=int, choices=(0, 1, 4), default=0,
                        help='decision-cache only: same-input serial/spawn qualification; OFF by default')
    parser.add_argument('--parallel-deadline-sec', type=float, default=120.,
                        help='Total qualification phase deadline including startup and cleanup')
    parser.add_argument('--parallel-response-audit', action='store_true',
                        help='Preserve and compare exactly2 raw responses per arm; diagnostic only, OFF by default')
    parser.add_argument('--mode', choices=('response', 'boundary-window', 'decision-cache', 'sink-order', 'ledger-copy', 'canonical-meter', 'urban-cost', 'owner-cost', 'shared-batch', 'fixed-game', 'reachable-game', 'joint-prices', 'priced-game', 'runtime-game'), default='response')
    args = parser.parse_args()
    require(not args.parallel_workers or args.mode == 'decision-cache',
            '--parallel-workers is supported only by decision-cache qualification')
    require(not args.parallel_response_audit or args.parallel_workers == 1,
            '--parallel-response-audit requires serial/spawn1 only (maximum4 full response files)')
    out = args.out.resolve()
    require(out.is_relative_to(ROOT / 'diagnostics') and not out.exists(), 'Require new diagnostics output')
    report = {'schema': 'fixed-candidate-response-equivalence/v1', 'completed': False,
              'mode': args.mode,
              'scope': 'Current fixed-candidate model preparation only; no solver change or native effect'}
    start = time.monotonic()
    with out.open('x', encoding='utf-8') as handle:
        json.dump(report, handle)
        handle.flush()
        try:
            compare(args, report)
            report['completed'] = True
        except Exception as exc:
            report.update(error_type=type(exc).__name__, error=str(exc))
            import traceback
            report['failure_traceback'] = traceback.format_exc()
            if hasattr(exc, 'resource_allocation'):
                report['failed_resource_allocation'] = exc.resource_allocation
        report['elapsed_sec'] = time.monotonic() - start
        handle.seek(0)
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.truncate()
    print(json.dumps({k: report.get(k) for k in ('completed', 'elapsed_sec', 'error', 'response_summary', 'canonical_meter_result', 'urban_cost_probe', 'owner_cost_probe')}))
    return 0 if report['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
