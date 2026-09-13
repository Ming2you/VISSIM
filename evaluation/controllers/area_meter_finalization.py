"""Finalize existing physical meter allocation before Omega candidate scoring.

The measured demand and spillback hints are frozen at the current decision.
They are not forecasts of future physical queue tails. The grouped model uses
the existing calibrated equivalent rate; physical connector timing remains an
actuation approximation rather than a microscopic signal replay.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

MARKER = '_control_area_meter_finalized'
HISTORICAL_REFERENCE = '_control_area_meter_historical_reference'
HELD_ACTUAL_REFERENCE = '_control_area_held_actual_reference'
WRITTEN_CONTEXT = '_control_area_written_meter_context'
PHYSICAL_SERVICE_CANDIDATE = '_control_area_physical_service_candidate'


def enabled(cfg):
    return bool(getattr(cfg.network, 'control_area_enabled', False))


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def configure(adapter, cfg, tuning, mapping, state_json, previous_action_path, state, calibration=None):
    if not enabled(cfg):
        return {}
    actuation = adapter.adapter_actuation_settings(calibration or {}, tuning or {})
    settings = actuation.get('real_world_ramp_metering', {})
    if settings.get('allocation') != 'measured_table' or not settings.get('write_back_realized', True):
        raise ValueError('Omega meter finalization requires the existing measured_table write-back contract')
    if not mapping.get('ramp_meters'):
        raise ValueError('Omega meter finalization requires physical ramp mappings')
    if actuation.get('ramp_release_guard', {}).get('enabled', False):
        raise ValueError('Omega meter finalization does not support an additional late ramp_release_guard')
    # These optional policies can change a candidate after endpoint evaluation.
    if actuation.get('active_lever_mask', {}).get('enabled', False) or actuation.get('F_ramp_invalid_guard_active', False):
        raise ValueError('Omega meter finalization does not support a late actuator mask/invalid-F override')
    if ((tuning or {}).get('adapter', {}).get('post_guard_safety', {}) or {}).get('enabled', False):
        raise ValueError('Omega meter finalization does not support the separate post_guard_safety baseline selector')
    previous_diag = {}
    if previous_action_path and Path(previous_action_path).is_file():
        previous_diag = json.loads(Path(previous_action_path).read_text(encoding='utf-8')).get('diagnostics', {})
    # Only calibration inputs are serialized into cfg; never retain the full
    # vehicle snapshot or look up future measurements inside candidate scoring.
    previous_diag = {k: v for k, v in previous_diag.items()
                     if k.startswith('rw_meter_demand_') or k.startswith('rw_meter_green_')}
    far = state_json.get('local_observation', {}).get('far_measurement', {})
    spill = (getattr(state, 'local_observation_summary', {}) or {}).get('ramp_spillback', {})
    cfg.network.control_area_meter_context = {
        'actuation': actuation,
        'mapping': {'ramp_meters': copy.deepcopy(mapping['ramp_meters'])},
        'raw': {'local_observation': {'far_measurement': {'link_volume_veh_h': copy.deepcopy(far.get('link_volume_veh_h', {}))}}},
        'previous_diagnostics': previous_diag,
        'spillback': copy.deepcopy(spill),
        'sim_sec': float(state_json.get('sim_sec', getattr(state, 'time_sec', 0.0))),
    }
    _context(cfg)  # Validate finite, serializable calibration inputs now.
    return {'control_area_meter_finalization_enabled': 1.0,
            'control_area_meter_context_sec': cfg.network.control_area_meter_context['sim_sec']}


def _context(cfg):
    context = getattr(cfg.network, 'control_area_meter_context', None)
    if not isinstance(context, dict):
        raise ValueError('Omega candidate lacks the shared physical meter decision context')
    identity = _hash({'context': context, 'capacities': dict(cfg.network.ramp_capacity_veh_h)})
    return context, identity


def _rates(control):
    return {str(k): float(v) for k, v in control.ramp_metering.items()}


def _commands(diag):
    return {k: v for k, v in diag.items() if k.startswith('rw_meter_')}


def _matches(control, marker, identity):
    basic = (isinstance(marker, dict) and marker.get('context_sha256') == identity
            and marker.get('realized_rates') == _rates(control)
            and marker.get('commands') == _commands(control.diagnostics))
    if not basic:
        return False
    service = control.diagnostics.get(PHYSICAL_SERVICE_CANDIDATE)
    if service is not None:
        return (isinstance(service, dict)
            and service.get('schema') == 'physical-meter-service-diagnostic/v1'
            and service.get('context_sha256') == identity
            and service.get('service_rates_veh_h') == _rates(control)
            and service.get('commands') == _commands(control.diagnostics)
            and service.get('derived_nuf_veh_h') == control.N_UF_star
            and service.get('proof_sha256') == _hash({k: v for k, v in service.items() if k != 'proof_sha256'})
            and marker.get('physical_service_proof_sha256') == service.get('proof_sha256')
            and HELD_ACTUAL_REFERENCE not in control.diagnostics)
    held = control.diagnostics.get(HELD_ACTUAL_REFERENCE)
    if held is None:
        return 'held_actual_reference_sha256' not in marker
    if not isinstance(held, dict):
        return False
    proof = held.get('historical_proof')
    return (held.get('schema') == 'held-actual-meter-reference/v1'
            and held.get('context_sha256') == identity
            and held.get('reference_only') is True
            and held.get('new_command_applied') is False
            and held.get('reference_rates') == _rates(control)
            and held.get('commands') == _commands(control.diagnostics)
            and isinstance(proof, dict)
            and proof.get('proof_sha256') == _hash({k: v for k, v in proof.items() if k != 'proof_sha256'})
            and held.get('proof_sha256') == _hash({k: v for k, v in held.items() if k != 'proof_sha256'})
            and marker.get('held_actual_reference_sha256') == held.get('proof_sha256'))


def finalize(control, cfg):
    """Mutate the candidate's meter fields once per rate/context combination.

    A copied finalized action retains its exact schedule when unchanged. An
    explicitly verified held-actual reference also retains its old commands
    under the current query context. Any change invalidates that exception.
    Rate, demand, spill, table or mapping changes invalidate ordinary allocations.
    Diagnostics are copied before writes because box-walk uses shallow copies.
    """
    if not enabled(cfg):
        return control
    from evaluation.controllers import physical_ramp_branches
    if physical_ramp_branches.enabled(cfg):
        return physical_ramp_branches.prepare_control(control, cfg)
    if (getattr(control, 'diagnostics', {}) or {}).get(HISTORICAL_REFERENCE):
        raise ValueError('Historical meter reference cannot be reallocated as a current candidate')
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    context, identity = _context(cfg)
    old_diag = getattr(control, 'diagnostics', {}) or {}
    if _matches(control, old_diag.get(MARKER), identity):
        return control
    if PHYSICAL_SERVICE_CANDIDATE in old_diag:
        raise ValueError('Explicit physical service candidate changed; no demand-based reallocation is permitted')
    requested = _rates(control)
    control.diagnostics = {k: v for k, v in old_diag.items()
                           if not k.startswith('rw_meter_') and k not in (MARKER, HELD_ACTUAL_REFERENCE)}
    guard_meta = {}
    observed = SimpleNamespace(local_observation_summary={'ramp_spillback': context['spillback']})
    previous = SimpleNamespace(diagnostics=context['previous_diagnostics'])
    adapter.apply_ramp_spillback_guard(control, cfg, observed, context['actuation'], guard_meta)
    adapter.real_world_ramp_meter_write_back(control, cfg, context['actuation'], context['mapping'],
        guard_meta, state_json=context['raw'], previous=previous)
    control.diagnostics['control_area_meter_finalized_before_score'] = 1.0
    control.diagnostics['control_area_meter_finalized_changed_rates'] = float(sum(
        abs(requested[k] - control.ramp_metering[k]) > 1e-9 for k in requested))
    control.diagnostics['control_area_meter_context_sec'] = context['sim_sec']
    control.diagnostics[MARKER] = {
        'context_sha256': identity, 'requested_rates': requested,
        'realized_rates': _rates(control), 'commands': copy.deepcopy(_commands(control.diagnostics)),
        'guard_metadata': guard_meta,
    }
    return control


def for_endpoint(previous, action_schedule, spec):
    """Preserve endpoint input immutability, including empty/base price probes."""
    from src.controllers.rollout_endpoint import apply_action_schedule
    control = apply_action_schedule(previous.copy(), action_schedule, spec)
    return finalize(control, spec.cfg)


def assert_writer(control, cfg, *, require_scored):
    """The writer cannot silently change a scored action; warmup may initialize."""
    if not enabled(cfg):
        return {}
    from evaluation.controllers import physical_ramp_branches
    if physical_ramp_branches.enabled(cfg):
        if require_scored and set(control.ramp_metering) != set(cfg.network.ramps):
            raise ValueError('Scored physical ramp action cannot use legacy grouped rates')
        physical_ramp_branches.prepare_control(control.copy(), cfg)
        return {'physical_ramp_writer_service_matches_green': True}
    _, identity = _context(cfg)
    if not require_scored:
        finalize(control, cfg)
    marker = control.diagnostics.get(MARKER)
    if not _matches(control, marker, identity):
        raise ValueError('Omega meter writer received a changed or unfinalized scored action')
    return {**marker['guard_metadata'], 'control_area_meter_writer_matches_scored': 1.0,
            'control_area_meter_context_sha256': identity}


class MeterCandidateInfeasible(ValueError):
    """Physical realization cannot preserve the supplied candidate constraints."""


def _candidate_number(value, label):
    if isinstance(value, bool):
        raise ValueError(f'{label} must be finite and nonnegative')
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f'{label} must be finite and nonnegative')
    return number


def _candidate_budget(budget, label):
    if budget is None:
        return None
    if not isinstance(budget, dict) or set(budget) != {'mode', 'veh_h'}:
        raise ValueError(f'{label} needs explicit mode and veh_h, or None')
    if budget['mode'] not in ('cap', 'equality'):
        raise ValueError(f'{label} mode must be cap or equality')
    return budget['mode'], _candidate_number(budget['veh_h'], label)


def prepare_physical_service_meter_candidate(reference, cfg, *, greens_by_meter,
                                               owned_ramps, physical_green_box):
    """Opt-in diagnostic over an explicit <=1s box around eight actual SGs.

    The existing table supplies saturated service, independent of observed
    outflow hints. The four grouped queues/receiving limits still bound actual
    release; this does not create eight connector states or calibrate traffic.
    No ordinary allocator, active game/domain or leader setting calls this.
    """
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    context, identity = _context(cfg)
    held = (getattr(reference, 'diagnostics', {}) or {}).get(HELD_ACTUAL_REFERENCE)
    if not enabled(cfg) or not isinstance(held, dict) or not _matches(reference, reference.diagnostics.get(MARKER), identity):
        raise ValueError('Physical service diagnostic requires the verified held-actual eight-SG reference')
    settings = context['actuation']['real_world_ramp_metering']
    cycle = _candidate_number(settings['cycle_sec'], 'Meter cycle')
    if cycle != 10. or settings.get('allocation') != 'measured_table':
        raise ValueError('Physical service diagnostic supports only the existing10s measured table')
    minimum = _candidate_number(settings.get('min_green_sec', 2.), 'Minimum green')
    maximum = _candidate_number(settings.get('max_green_sec', cycle), 'Maximum green')
    catalog = context['mapping']['ramp_meters']
    by_id = {str(m['id']): m for m in catalog}
    if len(catalog) != 8 or len(by_id) != 8 or type(greens_by_meter) is not dict or set(greens_by_meter) != set(by_id):
        raise ValueError('Exactly eight explicit physical meter greens required')
    caps = {r: _candidate_number(v, r) for r, v in cfg.network.ramp_capacity_veh_h.items()}
    if type(owned_ramps) is not tuple or not owned_ramps or len(set(owned_ramps)) != len(owned_ramps) or not set(owned_ramps) <= set(caps):
        raise ValueError('Explicit immutable unique owned ramp tuple required')
    if (type(physical_green_box) is not tuple or len(physical_green_box) != 8
            or any(type(row) is not tuple or len(row) != 3 for row in physical_green_box)):
        raise ValueError('Explicit immutable eight-meter green box required')
    boxes = {row[0]: row[1:] for row in physical_green_box}
    if len(boxes) != 8 or set(boxes) != set(by_id):
        raise ValueError('Green box must contain every physical meter exactly once')
    actual = {row['id']: row for row in held['verified_written_meter_rows']}
    before_rows = adapter.real_world_ramp_meter_actions(copy.deepcopy(reference), cfg, context['actuation'], context['mapping'])
    if len(actual) != 8 or set(actual) != set(by_id) or set(before_rows) != set(by_id):
        raise ValueError('Held actual physical meter catalog differs')
    table = {str(k): _candidate_number(v, 'Service table') for k, v in
        (settings.get('per_lane_veh_per_cycle') or adapter.METER_PER_LANE_VEH_PER_CYCLE_DEFAULT).items()}
    lanes = settings.get('meter_lanes') or adapter.METER_LANES_DEFAULT
    greens, services, groups = {}, {}, {r: [] for r in caps}
    for mid, meter in by_id.items():
        row, anchor = actual[mid], _candidate_number(actual[mid]['green_sec'], mid)
        if (before_rows[mid]['green_sec'] != anchor or int(before_rows[mid]['sc_no']) != row['sc_no']
                or round(before_rows[mid]['rate_vph'], 3) != row['rate_vph']
                or before_rows[mid]['sg_no'] != 1 or _candidate_number(meter.get('capacity_vph', 900), mid) != 900.):
            raise ValueError('Held actual meter writer no longer matches its physical proof')
        low, high = (_candidate_number(v, mid+' box') for v in boxes[mid])
        green = _candidate_number(greens_by_meter[mid], mid+' green')
        if (any(v != int(v) for v in (anchor, low, high, green))
                or low > high or low < max(0., anchor-1.) or high > min(cycle, anchor+1.)
                or not low <= anchor <= high or not low <= green <= high
                or (green != 0. and not minimum <= green <= maximum)):
            raise MeterCandidateInfeasible('Physical green is outside the explicit<=1s box: '+mid)
        ramp = meter['model_ramp_key']
        if ramp not in groups or (ramp not in owned_ramps and green != anchor):
            raise MeterCandidateInfeasible('Physical green changed a foreign meter group: '+mid)
        lane_count = _candidate_number(lanes.get(mid, 1.), mid+' lanes')
        if lane_count <= 0. or (green > 0. and str(int(green)) not in table):
            raise ValueError('Exact positive lane count and explicit service-table entry required')
        groups[ramp].append(mid)
        greens[mid] = green
        services[mid] = adapter._meter_flow_vph(lane_count, int(green), table, cycle)
    if any(len(mids) != 2 for mids in groups.values()):
        raise ValueError('Physical service diagnostic requires the existing two-meter groups')
    rates = {r: min(caps[r], math.fsum(services[mid] for mid in mids)) for r, mids in groups.items()}
    if any(rates[r] != reference.ramp_metering[r] for r in caps if r not in owned_ramps):
        raise MeterCandidateInfeasible('Foreign group is not already in the saturated service coordinate')
    guard = settings.get('spillback_guard', {})
    if adapter._is_enabled_value(guard.get('enabled', False)):
        threshold = _candidate_number(guard.get('spill_threshold_veh', 8.), 'Spill threshold')
        floor = _candidate_number(guard.get('floor_vph', 1800.), 'Spill floor')
        for ramp in owned_ramps:
            if (_candidate_number(context['spillback'].get(ramp, 0.), ramp+' spill') > threshold
                    and (rates[ramp] < floor or (floor >= caps[ramp] and any(greens[mid] != cycle for mid in groups[ramp])))):
                raise MeterCandidateInfeasible('Explicit physical green conflicts with the existing spillback guard: '+ramp)
    candidate = copy.deepcopy(reference)
    for name in (MARKER, HELD_ACTUAL_REFERENCE, HISTORICAL_REFERENCE, WRITTEN_CONTEXT):
        candidate.diagnostics.pop(name, None)
    for ramp in owned_ramps:
        candidate.ramp_metering[ramp] = rates[ramp]
        for kind, value in (('requested', rates[ramp]), ('realized', rates[ramp]),
                            ('open', float(all(greens[mid] == cycle for mid in groups[ramp])))):
            candidate.diagnostics['rw_meter_'+kind+'_'+ramp] = value
        for mid in groups[ramp]:
            candidate.diagnostics['rw_meter_green_'+mid] = greens[mid]
    candidate.N_UF_star = math.fsum(rates[r] for r in sorted(rates))
    proof = {'schema': 'physical-meter-service-diagnostic/v1', 'context_sha256': identity,
        'held_actual_proof': copy.deepcopy(held), 'physical_green_box': physical_green_box,
        'owned_ramps': owned_ramps, 'greens_sec': greens, 'saturated_service_by_meter_veh_h': services,
        'service_rates_veh_h': rates, 'derived_nuf_veh_h': candidate.N_UF_star,
        'commands': copy.deepcopy(_commands(candidate.diagnostics)),
        'scope': 'Diagnostic only; four grouped service ceilings, no eight-branch queue model or native improvement',
        'hint_scope': 'Retained historical allocation diagnostics; not a current forecast or service ceiling'}
    proof['proof_sha256'] = _hash(proof)
    candidate.diagnostics[PHYSICAL_SERVICE_CANDIDATE] = proof
    candidate.diagnostics[MARKER] = {'context_sha256': identity, 'requested_rates': rates,
        'realized_rates': rates, 'commands': copy.deepcopy(_commands(candidate.diagnostics)),
        'physical_service_proof_sha256': proof['proof_sha256'], 'guard_metadata': {}}
    finalize(candidate, cfg)
    assert_writer(candidate, cfg, require_scored=True)
    written = adapter.real_world_ramp_meter_actions(copy.deepcopy(candidate), cfg, context['actuation'], context['mapping'])
    if any(written[mid]['green_sec'] != greens[mid] or written[mid]['rate_vph'] != 900.*greens[mid]/cycle
           or (by_id[mid]['model_ramp_key'] not in owned_ramps and written[mid] != before_rows[mid]) for mid in by_id):
        raise ValueError('Explicit physical service candidate did not survive the unchanged writer')
    return candidate


def prepare_recorded_historical_meter_reference(previous, current_cfg, *, previous_sim_sec,
                                                written_meter_rows, source_provenance):
    """Use the context saved with a real previous command, never today's demand.

    The caller verifies the actual action JSON/CSV paths and SHA256 values in
    source_provenance['action_json'/'action_csv'], and supplies that JSON's time
    and its parsed meter rows. This function does not read files or allocate a
    new schedule. Fixed actuation, mapping and model capacities must still match.
    """
    if not enabled(current_cfg):
        raise ValueError('Recorded meter history requires enabled current context')
    current, _ = _context(current_cfg)
    recorded = (getattr(previous, 'diagnostics', {}) or {}).get(WRITTEN_CONTEXT)
    if not isinstance(recorded, dict):
        raise ValueError('Previous action lacks its recorded written meter context')
    previous_sec = _candidate_number(previous_sim_sec, 'Previous action time')
    recorded_sec = _candidate_number(recorded.get('sim_sec'), 'Recorded meter context time')
    current_sec = _candidate_number(current.get('sim_sec'), 'Current meter context time')
    if recorded_sec != previous_sec or previous_sec >= current_sec:
        raise ValueError('Recorded meter context must match previous action time before current time')
    for key in ('actuation', 'mapping'):
        if (not isinstance(recorded.get(key), dict) or not isinstance(current.get(key), dict)
                or _hash(recorded[key]) != _hash(current[key])):
            raise ValueError('Recorded and current meter physical ' + key + ' differ')
    for key in ('action_json', 'action_csv'):
        item = source_provenance.get(key) if isinstance(source_provenance, dict) else None
        if (not isinstance(item, dict) or not isinstance(item.get('path'), str) or not item['path']
                or not isinstance(item.get('sha256'), str) or len(item['sha256']) != 64
                or any(c not in '0123456789abcdef' for c in item['sha256'])):
            raise ValueError('Verified previous ' + key + ' path/SHA256 provenance required')
    historical_cfg = copy.deepcopy(current_cfg)
    historical_cfg.network.control_area_meter_context = copy.deepcopy(recorded)
    # _context hashes these CURRENT capacities with the RECORDED context. The
    # original finalization marker must match, so changed capacities fail closed.
    return prepare_historical_meter_reference(previous, historical_cfg,
        written_meter_rows=written_meter_rows, source_provenance=source_provenance)


def prepare_historical_meter_reference(previous, historical_cfg, *, written_meter_rows,
                                       source_provenance):
    """Bind a previous final-writeback anchor to its historical context and CSV.

    The caller supplies the ORIGINAL action/context and the eight actual CSV
    meter rows, with their frozen input provenance. No current-context allocator
    is run. The returned reference normalizes only all-open model aliases; its
    original writeback rates remain the movement-box anchor, including PARTIAL
    rates after quantization. Original N_UF is recorded, never a new leader target.
    This reference is not a current scored candidate and cannot be refinalized.
    """
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    if not enabled(historical_cfg):
        raise ValueError('Historical meter proof requires its enabled historical context')
    context, identity = _context(historical_cfg)
    diag = getattr(previous, 'diagnostics', {}) or {}
    if diag.get(HISTORICAL_REFERENCE) or not _matches(previous, diag.get(MARKER), identity):
        raise ValueError('Original final-writeback action does not match historical meter context')
    if not isinstance(source_provenance, dict) or not source_provenance:
        raise ValueError('Actual previous action/CSV/context source provenance required')
    _hash(source_provenance)
    source_rates = {r: _candidate_number(v, r) for r, v in previous.ramp_metering.items()}
    capacities = {r: _candidate_number(v, r) for r, v in historical_cfg.network.ramp_capacity_veh_h.items()}
    if set(source_rates) != set(capacities):
        raise ValueError('Incomplete historical model ramp vector')
    cycle = _candidate_number(context['actuation']['real_world_ramp_metering']['cycle_sec'], 'Historical cycle')
    if cycle <= 0:
        raise ValueError('Positive historical meter cycle required')
    original = copy.deepcopy(previous)
    physical = adapter.real_world_ramp_meter_actions(copy.deepcopy(previous), historical_cfg,
        context['actuation'], context['mapping'])
    expected = []
    groups = {r: [] for r in capacities}
    for mid, row in physical.items():
        if row['model_ramp_key'] not in groups or row['sg_no'] != 1:
            raise ValueError('Historical physical meter mapping differs from writer SG1 contract')
        green = _candidate_number(row['green_sec'], mid)
        if green > cycle:
            raise ValueError('Historical physical green exceeds cycle')
        groups[row['model_ramp_key']].append(green)
        expected.append({'kind': 'ramp_meter', 'id': mid, 'sc_no': int(row['sc_no']),
                         'rate_vph': round(row['rate_vph'], 3), 'green_sec': round(green, 3)})
    if len(expected) != 8 or any(not greens for greens in groups.values()):
        raise ValueError('Historical proof requires all eight physical meters')
    actual = []
    for row in written_meter_rows:
        sc = _candidate_number(row['sc_no'], 'Written meter SC')
        if sc != int(sc) or row['kind'] != 'ramp_meter':
            raise ValueError('Invalid written meter address')
        actual.append({'kind': row['kind'], 'id': row['id'], 'sc_no': int(sc),
                       'rate_vph': _candidate_number(row['rate_vph'], 'Written meter rate'),
                       'green_sec': _candidate_number(row['green_sec'], 'Written meter green')})
    if actual != expected:
        raise ValueError('Actual written meter rows differ from historical action/context')
    reference = copy.deepcopy(previous)
    for ramp, greens in groups.items():
        if all(g == cycle for g in greens):
            reference.ramp_metering[ramp] = capacities[ramp]
    reference.N_UF_star = math.fsum(reference.ramp_metering[r] for r in sorted(source_rates))
    # Keep the original green/demand/allocation diagnostics. They are evidence,
    # not a newly fabricated finalization marker under the current decision.
    proof = {'schema': 'historical-meter-anchor/v1', 'source_provenance': copy.deepcopy(source_provenance),
             'historical_context_sha256': identity, 'historical_context_sec': context['sim_sec'],
             'physical_definition_sha256': _hash({'actuation': context['actuation'],
                 'mapping': context['mapping'], 'capacities': capacities}),
             'historical_capacities': capacities, 'final_writeback_rates': source_rates,
             'original_nuf_star': previous.N_UF_star, 'written_meter_rows': actual,
             'reference_rates': _rates(reference), 'commands': copy.deepcopy(_commands(diag))}
    proof['proof_sha256'] = _hash(proof)
    reference.diagnostics[HISTORICAL_REFERENCE] = copy.deepcopy(proof)
    if vars(previous) != vars(original) or _context(historical_cfg)[1] != identity:
        raise ValueError('Historical source action/context changed while preparing reference')
    return {'previous': reference, 'meter_anchor': proof}


def historical_meter_anchor_rates(reference, proof=None):
    """Validate the private historical reference and return original box rates."""
    stored = (getattr(reference, 'diagnostics', {}) or {}).get(HISTORICAL_REFERENCE)
    proof = stored if proof is None else proof
    if not isinstance(proof, dict) or proof.get('schema') != 'historical-meter-anchor/v1':
        raise ValueError('Verified historical meter anchor proof required')
    body = {k: v for k, v in proof.items() if k != 'proof_sha256'}
    if (stored != proof or proof.get('proof_sha256') != _hash(body)
            or proof['reference_rates'] != _rates(reference)
            or proof['commands'] != _commands(reference.diagnostics)):
        raise ValueError('Historical meter reference or anchor proof changed')
    return copy.deepcopy(proof['final_writeback_rates'])


def prepare_held_actual_reference(historical, cfg):
    """Represent the verified previous eight commands at today's query state.

    This is a reference for holding/scoring the actual prior command, not a
    fresh allocation using today's demand and not evidence of a new COM write.
    Historical normalized group aliases and every physical meter row must stay
    identical. The original historical reference/proof are never mutated.
    Editing a meter or its commands invalidates this exception in ``finalize``.
    """
    from evaluation.controllers import vissim_stackelberg_adapter as adapter, physical_ramp_branches
    if physical_ramp_branches.enabled(cfg):
        return physical_ramp_branches.held_actual_reference(historical, cfg)
    if not enabled(cfg):
        raise ValueError('Held actual meter reference requires enabled current context')
    historical_meter_anchor_rates(historical)
    context, identity = _context(cfg)
    proof = copy.deepcopy(historical.diagnostics[HISTORICAL_REFERENCE])
    capacities = {r: _candidate_number(v, r) for r, v in cfg.network.ramp_capacity_veh_h.items()}
    definition = _hash({'actuation': context['actuation'], 'mapping': context['mapping'],
                        'capacities': capacities})
    if (proof.get('physical_definition_sha256') != definition
            or proof.get('historical_capacities') != capacities
            or set(proof['reference_rates']) != set(capacities)):
        raise ValueError('Held actual reference and current physical meter definition differ')
    if (_candidate_number(proof['historical_context_sec'], 'Historical reference time')
            > _candidate_number(context['sim_sec'], 'Current reference time')):
        raise ValueError('Held actual reference cannot come from a future context')
    original = copy.deepcopy(historical)
    reference = copy.deepcopy(historical)
    physical = adapter.real_world_ramp_meter_actions(reference, cfg, context['actuation'], context['mapping'])
    rows = []
    addresses = set()
    for mid, row in physical.items():
        address = (int(row['sc_no']), int(row['sg_no']))
        if address in addresses or row['sg_no'] != 1 or row['model_ramp_key'] not in capacities:
            raise ValueError('Held actual reference has invalid physical meter addresses')
        addresses.add(address)
        rows.append({'kind': 'ramp_meter', 'id': mid, 'sc_no': address[0],
                     'rate_vph': round(_candidate_number(row['rate_vph'], mid), 3),
                     'green_sec': round(_candidate_number(row['green_sec'], mid), 3)})
    if (len(rows) != 8 or rows != proof.get('written_meter_rows')
            or _rates(reference) != proof['reference_rates']
            or _commands(reference.diagnostics) != proof['commands']):
        raise ValueError('Held actual reference writer differs from the eight historical commands')
    reference.diagnostics.pop(HISTORICAL_REFERENCE)
    held = {'schema': 'held-actual-meter-reference/v1', 'context_sha256': identity,
            'reference_only': True, 'new_command_applied': False,
            'historical_proof': proof, 'physical_definition_sha256': definition,
            'reference_rates': _rates(reference), 'commands': copy.deepcopy(_commands(reference.diagnostics)),
            'verified_written_meter_rows': rows}
    held['proof_sha256'] = _hash(held)
    reference.diagnostics[HELD_ACTUAL_REFERENCE] = held
    reference.diagnostics[MARKER] = {
        'context_sha256': identity, 'requested_rates': _rates(reference),
        'realized_rates': _rates(reference), 'commands': copy.deepcopy(_commands(reference.diagnostics)),
        'guard_metadata': {'control_area_meter_held_actual_reference': 1.0,
                           'control_area_meter_new_command_applied': 0.0},
        'held_actual_reference_sha256': held['proof_sha256']}
    if vars(historical) != vars(original) or _context(cfg)[1] != identity:
        raise ValueError('Held reference preparation changed source history or current context')
    assert_writer(reference, cfg, require_scored=True)
    return reference


def prepare_canonical_candidate(control, cfg, *, owned_ramps, total_budget,
                                directional_budgets, budget_tolerance_veh_h):
    """Prepare a private, budget-checked fixed candidate or price-query point.

    This explicit API does not install a legacy solver/local-price hook. Budgets
    constrain FINAL grouped model rates, not allocation requests: use None for
    an explicitly unconstrained total/direction, otherwise
    {'mode': 'cap' or 'equality', 'veh_h': value}. Direction keys come from
    ramp_to_freeway; an empty directional_budgets means no directional limits.
    Tolerance is caller supplied. N_UF_star is the sum over the full vector.

    Only owned groups whose EVERY physical green equals the configured cycle
    are normalized to their existing near capacity. PARTIAL/CLOSED retain the
    existing allocation. Reallocation must preserve all physical commands;
    otherwise this representation is infeasible in the frozen context. Foreign
    groups need a valid existing marker (owned rates may have been edited).
    No owner redistribution, budget expansion, or open-flag semantics is added.
    """
    if not enabled(cfg):
        raise ValueError('Canonical meter candidates require Omega meter finalization')
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    context, identity = _context(cfg)
    settings = context['actuation']['real_world_ramp_metering']
    if settings.get('allocation') != 'measured_table' or not settings.get('write_back_realized', True):
        raise ValueError('Canonical meter candidates require measured_table write-back')
    cycle = _candidate_number(settings['cycle_sec'], 'Explicit meter cycle')
    if cycle == 0:
        raise ValueError('Explicit meter cycle must be positive')
    rates = {r: _candidate_number(v, r) for r, v in control.ramp_metering.items()}
    caps = {r: _candidate_number(v, r) for r, v in cfg.network.ramp_capacity_veh_h.items()}
    if not rates or set(rates) != set(caps) or any(not isinstance(r, str) or not r for r in rates):
        raise ValueError('Candidate must contain the complete configured ramp vector')
    owned = tuple(owned_ramps)
    if not owned or len(set(owned)) != len(owned) or not set(owned) <= set(rates):
        raise ValueError('Owned ramps must be an explicit unique nonempty subset')
    directions = dict(cfg.network.ramp_to_freeway)
    if set(directions) != set(rates) or any(not isinstance(d, str) or not d for d in directions.values()):
        raise ValueError('Every model ramp needs one configured direction')
    if not isinstance(directional_budgets, dict) or not set(directional_budgets) <= set(directions.values()):
        raise ValueError('Unknown directional budget')
    tolerance = _candidate_number(budget_tolerance_veh_h, 'Budget tolerance')
    checks = [('total', tuple(rates), _candidate_budget(total_budget, 'Total budget'))]
    checks += [(d, tuple(r for r in rates if directions[r] == d), _candidate_budget(b, d))
               for d, b in directional_budgets.items()]
    groups = {r: [] for r in rates}
    meter_ids = set()
    for meter in context['mapping']['ramp_meters']:
        mid = str(meter.get('id', meter.get('control_id', '')))
        ramp = meter.get('model_ramp_key')
        if not mid or mid in meter_ids or ramp not in groups:
            raise ValueError('Invalid or duplicate physical meter mapping')
        meter_ids.add(mid)
        groups[ramp].append(mid)
    if any(not ids for ids in groups.values()):
        raise ValueError('Every model ramp needs physical meters')
    foreign = set(rates) - set(owned)
    diag = getattr(control, 'diagnostics', {}) or {}
    marker = diag.get(MARKER, {})
    for ramp in foreign:
        keys = [f'rw_meter_{kind}_{ramp}' for kind in ('requested', 'realized', 'open')]
        keys += [f'rw_meter_{kind}_{mid}' for mid in groups[ramp] for kind in ('green', 'demand')]
        if (marker.get('context_sha256') != identity or marker.get('realized_rates', {}).get(ramp) != rates[ramp]
                or any(k not in diag or marker.get('commands', {}).get(k) != diag[k] for k in keys)):
            raise ValueError('Foreign meter group lacks its unchanged finalized context')

    def physical_rows(action):
        # group_rate_vph is modeled metadata, not a physical writer command.
        rows = adapter.real_world_ramp_meter_actions(copy.deepcopy(action), cfg,
                                                     context['actuation'], context['mapping'])
        if set(rows) != meter_ids:
            raise ValueError('Physical writer returned a different meter catalog')
        return {mid: {k: row[k] for k in ('sc_no', 'sg_no', 'rate_vph', 'green_sec', 'model_ramp_key')}
                for mid, row in rows.items()}

    candidate = copy.deepcopy(control)
    fixed = {k: copy.deepcopy(v) for k, v in vars(control).items()
             if k not in ('ramp_metering', 'N_UF_star', 'diagnostics')}
    try:
        foreign_rows = physical_rows(control) if foreign else {}
        finalize(candidate, cfg)
        allocated_rates = _rates(candidate)
        allocated_rows = physical_rows(candidate)
        for ramp in owned:
            if all(allocated_rows[mid]['green_sec'] == cycle for mid in groups[ramp]):
                candidate.ramp_metering[ramp] = caps[ramp]
        if _rates(candidate) != allocated_rates:
            finalize(candidate, cfg)
        final_rows = physical_rows(candidate)
        if final_rows != allocated_rows:
            raise MeterCandidateInfeasible('Near-capacity normalization changes physical meter commands')
        if any(candidate.ramp_metering[r] != caps[r] for r in owned
               if all(allocated_rows[mid]['green_sec'] == cycle for mid in groups[r])):
            raise MeterCandidateInfeasible('All-open allocation cannot retain its canonical near capacity')
        if any(candidate.ramp_metering[r] != allocated_rates[r] for r in rates
               if not all(allocated_rows[mid]['green_sec'] == cycle for mid in groups[r])):
            raise MeterCandidateInfeasible('Normalization changed a PARTIAL/CLOSED allocation')
        if any(candidate.ramp_metering[r] != rates[r] or
               any(final_rows[mid] != foreign_rows[mid] for mid in groups[r]) for r in foreign):
            raise MeterCandidateInfeasible('Physical allocation changed a foreign owner')
        if fixed != {k: v for k, v in vars(candidate).items() if k not in ('ramp_metering', 'N_UF_star', 'diagnostics')}:
            raise MeterCandidateInfeasible('Meter allocation changed another lever or fixed action context')
        candidate.N_UF_star = math.fsum(candidate.ramp_metering[r] for r in sorted(rates))
        for label, ramps, budget in checks:
            if budget is None:
                continue
            mode, limit = budget
            actual = math.fsum(candidate.ramp_metering[r] for r in sorted(ramps))
            residual = actual - limit
            if (abs(residual) if mode == 'equality' else residual) > tolerance:
                raise MeterCandidateInfeasible(f'{label} {mode} budget infeasible: realized {actual}, limit {limit}')
        assert_writer(candidate, cfg, require_scored=True)
        return candidate
    finally:
        if _context(cfg)[1] != identity:
            raise ValueError('Canonical meter preparation changed its frozen context')


def reachable_meter_budgets(control, cfg, *, directional_requests,
                            source_provenance, budget_tolerance_veh_h, check_budget=None):
    """Realize the ordered product of EXISTING two-ramp request domains.

    directional_requests maps each FW direction to an explicit ordered tuple of
    (label, {its two ramps: requested rate}). Callers obtain these points from
    the existing source fractions/previous-box/trust/certification branch, e.g.
    current Domain.meter_points, and supply that branch's source_provenance.
    This helper does not generate rates, filter a new trust domain, optimize,
    change omega, or silently adopt a new leader target.

    Each returned full action preserves input N_P, greens, offsets, VSL and all
    other non-meter payload. Only meters, their derived diagnostics and N_UF
    (the exact sorted full realized rate sum) differ. Budgets returned alongside
    it are NEW pre-score leader-candidate evidence, not replacements for an old
    equality target. Callers must explicitly select/encode total AND directional
    budgets before scoring; existing prepare_canonical_candidate equality checks
    remain unchanged. Asymmetric directions are retained even if the current
    fixed-omega leader cannot encode them.

    Fixed demand/table and integer full-cycle greens give a finite canonical
    response alphabet: partial rates are discrete table/demand sums; full-open
    rates are the existing near capacities. The legacy max-green-below-cycle
    case can retain arbitrary requested rates and is explicitly outside this
    contract. This enumerates only the supplied finite request product, not all
    possible schedules or a physical receiving/traffic feasibility certificate.
    """
    from collections.abc import Mapping
    from itertools import product
    from evaluation.controllers import vissim_stackelberg_adapter as adapter

    if not enabled(cfg):
        raise ValueError('Reachable meter budgets require canonical Omega allocation')
    context, identity = _context(cfg)
    settings = context['actuation']['real_world_ramp_metering']
    if settings.get('allocation') != 'measured_table' or not settings.get('write_back_realized', True):
        raise ValueError('Reachable meter budgets require measured_table write-back')
    cycle = _candidate_number(settings['cycle_sec'], 'Explicit meter cycle')
    maximum = _candidate_number(settings['max_green_sec'], 'Explicit maximum green')
    if cycle <= 0 or cycle != int(cycle) or maximum != cycle:
        raise ValueError('Finite canonical response contract requires integer max_green == cycle')
    tolerance = _candidate_number(budget_tolerance_veh_h, 'Budget tolerance')
    caps = {r: _candidate_number(v, r) for r, v in cfg.network.ramp_capacity_veh_h.items()}
    rates = {r: _candidate_number(v, r) for r, v in control.ramp_metering.items()}
    directions = dict(cfg.network.ramp_to_freeway)
    if set(rates) != set(caps) or set(rates) != set(directions) or len(rates) != 4:
        raise ValueError('Current reachable contract requires all four configured model meters')
    order = tuple(dict.fromkeys(directions[r] for r in rates))
    if set(order) != {'FW_E', 'FW_W'}:
        raise ValueError('Current reachable contract requires both freeway directions')
    owned = {d: tuple(r for r in rates if directions[r] == d) for d in order}
    if any(len(keys) != 2 for keys in owned.values()):
        raise ValueError('Each freeway direction requires its two configured model meters')
    if (not isinstance(directional_requests, Mapping) or set(directional_requests) != set(order)
            or not isinstance(source_provenance, Mapping) or set(source_provenance) != set(order)
            or any(not isinstance(source_provenance[d], Mapping) or not source_provenance[d] for d in order)):
        raise ValueError('Every direction needs explicit request points and nonempty source provenance')
    points = {}
    for direction in order:
        supplied = directional_requests[direction]
        if type(supplied) is not tuple:
            raise ValueError('Each source domain must be an ordered finite tuple')
        labels, points[direction] = set(), []
        for item in supplied:
            if type(item) is not tuple or len(item) != 2:
                raise ValueError('Expected explicit (label, two-ramp request) source points')
            label, pair = item
            if type(label) is not str or not label or label in labels:
                raise ValueError('Source point labels must be nonempty and unique within direction')
            if not isinstance(pair, Mapping) or set(pair) != set(owned[direction]):
                raise ValueError('Source point changed its configured two-ramp ownership')
            labels.add(label)
            points[direction].append((label, {r: _candidate_number(pair[r], r) for r in owned[direction]}))
    meters = context['mapping']['ramp_meters']
    meter_ids = tuple(str(m.get('id', m.get('control_id', ''))) for m in meters)
    if len(meter_ids) != 8 or len(set(meter_ids)) != 8:
        raise ValueError('Current reachable contract requires eight distinct physical meters')
    # One frozen-value guard for the operation; no file access or candidate-level
    # source rehash. prepare_canonical_candidate also guards its meter context.
    def input_identity():
        return _hash({'control': vars(control), 'requests': directional_requests,
            'source_provenance': source_provenance, 'directions': cfg.network.ramp_to_freeway})
    before = input_identity()
    candidates, rejected, seen = [], [], {}
    requested_count = 0
    try:
        for combination in product(*(points[d] for d in order)):
            if check_budget is not None: check_budget('leader_meter_product')
            request_index = requested_count
            requested_count += 1
            request = {r: rates[r] for r in rates}
            labels = {}
            for direction, (label, pair) in zip(order, combination):
                request.update(pair)
                labels[direction] = label
            alias = {'request_index': request_index, 'source_labels': labels,
                'requested_rates_veh_h': dict(request),
                'requested_total_veh_h': math.fsum(request[r] for r in sorted(request)),
                'requested_directional_veh_h': {d: math.fsum(request[r] for r in sorted(owned[d])) for d in order}}
            if any(request[r] > caps[r] + tolerance for r in request):
                rejected.append({**alias, 'stage': 'requested_capacity',
                                 'reason': 'Source request exceeds configured group capacity'})
                continue
            trial = copy.deepcopy(control)
            trial.ramp_metering.update(request)
            try:
                canonical = prepare_canonical_candidate(trial, cfg, owned_ramps=tuple(rates),
                    total_budget=None, directional_budgets={}, budget_tolerance_veh_h=tolerance)
            except MeterCandidateInfeasible as exc:
                rejected.append({**alias, 'stage': 'canonical_realization', 'reason': str(exc)})
                continue
            realized = dict(canonical.ramp_metering)
            if any(realized[r] > caps[r] + tolerance for r in realized):
                rejected.append({**alias, 'stage': 'realized_capacity', 'reason': 'Canonical realized rate exceeds configured group capacity',
                                 'realized_rates_veh_h': realized})
                continue
            raw_rows = adapter.real_world_ramp_meter_actions(copy.deepcopy(canonical), cfg,
                                                            context['actuation'], context['mapping'])
            if tuple(raw_rows) != meter_ids:
                raise ValueError('Canonical writer meter order/coverage changed')
            rows = tuple({'id': mid, **{k: raw_rows[mid][k] for k in
                ('sc_no', 'sg_no', 'rate_vph', 'green_sec', 'model_ramp_key')}} for mid in meter_ids)
            total = math.fsum(realized[r] for r in sorted(realized))
            per_direction = {d: math.fsum(realized[r] for r in sorted(owned[d])) for d in order}
            if canonical.N_UF_star != total:
                raise ValueError('Canonical action N_UF differs from its realized full sum')
            # NEVER collapse a sum alone: rates, direction allocation and every
            # physical meter schedule stay in the identity and returned evidence.
            key = _hash({'rates': realized, 'physical_rows': rows})
            if key in seen:
                candidates[seen[key]]['aliases'].append(alias)
            else:
                seen[key] = len(candidates)
                candidates.append({'control': canonical, 'realized_rates_veh_h': realized,
                    'total_budget_veh_h': total, 'directional_budgets_veh_h': per_direction,
                    'physical_rows': rows, 'physical_and_model_sha256': key, 'aliases': [alias]})
        return {'schema': 'reachable-canonical-meter-budgets/v1',
            'complete': True, 'status': 'reachable_candidates' if candidates else 'empty_reachable_set',
            'scope': 'supplied ordered two-direction request product only; not all possible schedules',
            'direction_order': order, 'source_point_counts': {d: len(points[d]) for d in order},
            'requested_count': requested_count, 'candidate_count': len(candidates),
            'candidates': candidates, 'rejected': rejected,
            'input_N_UF_star_unchanged': control.N_UF_star,
            'meter_context_sha256': identity, 'input_sha256': before,
            'source_provenance': copy.deepcopy(dict(source_provenance)),
            'source_policy_verification': 'caller-supplied existing filtered source domain; not rederived here',
            'canonical_response_quantized': True, 'leader_target_selected': False,
            'omega_modified': False, 'shared_physical_feasibility_certified': False}
    finally:
        if _context(cfg)[1] != identity or input_identity() != before:
            raise ValueError('Reachable meter enumeration changed its frozen inputs')
