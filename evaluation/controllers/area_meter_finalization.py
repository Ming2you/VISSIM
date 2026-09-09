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
from pathlib import Path
from types import SimpleNamespace

MARKER = '_control_area_meter_finalized'


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
    return (isinstance(marker, dict) and marker.get('context_sha256') == identity
            and marker.get('realized_rates') == _rates(control)
            and marker.get('commands') == _commands(control.diagnostics))


def finalize(control, cfg):
    """Mutate the candidate's meter fields once per rate/context combination.

    A copied finalized action retains its exact schedule when unchanged. Any
    rate, demand, spill, table or mapping change invalidates the old allocation.
    Diagnostics are copied before writes because box-walk uses shallow copies.
    """
    if not enabled(cfg):
        return control
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    context, identity = _context(cfg)
    old_diag = getattr(control, 'diagnostics', {}) or {}
    if _matches(control, old_diag.get(MARKER), identity):
        return control
    requested = _rates(control)
    control.diagnostics = {k: v for k, v in old_diag.items()
                           if not k.startswith('rw_meter_') and k != MARKER}
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
    _, identity = _context(cfg)
    if not require_scored:
        finalize(control, cfg)
    marker = control.diagnostics.get(MARKER)
    if not _matches(control, marker, identity):
        raise ValueError('Omega meter writer received a changed or unfinalized scored action')
    return {**marker['guard_metadata'], 'control_area_meter_writer_matches_scored': 1.0,
            'control_area_meter_context_sha256': identity}
