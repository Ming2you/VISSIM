"""Optional single-lane ramp entry receiving from current positions and past service.

Reuses the existing receiving envelope. This is a finite backward-wave bound,
not a lane-changing model or a command-specific benefit correction.
"""
from copy import copy
from evaluation.controllers.known_wout_causal_response import attach
from evaluation.controllers.route_choice_corridor import _positive


def configure(cfg, tuning, state):
    option = (tuning or {}).get('urban', {}).get('single_lane_causal_receiving')
    if option is None:
        return {}
    if not isinstance(option, dict) or set(option) != {'ramps', 'wave_m_s'}:
        raise ValueError('Single-lane receiving requires explicit ramps and wave_m_s')
    names = option['ramps']
    if (not isinstance(names, list) or not names
            or any(not isinstance(name, str) for name in names)
            or len(set(names)) != len(names)):
        raise ValueError('Single-lane receiving requires distinct ramp names')
    wave = _positive(option['wave_m_s'], 'single-lane receiving wave_m_s')
    runtime = getattr(state, 'lane_ramp_runtime', None)
    if runtime is None:
        raise ValueError('Single-lane receiving requires projected physical ramp buffers')
    prepared = []
    for name in names:
        if name not in runtime.buffers:
            raise ValueError('Unknown receiving ramp: '+name)
        buffer = runtime.buffers[name]
        children = getattr(buffer, '_lane_buffers', [buffer])
        if (getattr(buffer, 'lane_exchange_rates', None) is not None
                or len(children) != 1 or children[0].lanes != 1):
            raise ValueError('Receiving target must have one lane and no lateral exchange')
        child = children[0]
        if child.time_sec != state.time_sec or hasattr(child, '_spatial_entry'):
            raise ValueError('Receiving requires fresh current-time ramp initialization')
        # Construct every envelope before modifying any physical buffer.
        staged = copy(child)
        attach(staged, wave)
        memory = staged._spatial_entry
        if memory['envelope'].lag < max(cfg.simulation.T_f_sec, cfg.simulation.T_u_sec):
            raise ValueError('Ramp receiving wave lag is shorter than the exchange step')
        prepared.append((child, memory))
    for child, memory in prepared:
        child._spatial_entry = memory
        child._causal_receiving_enabled = True
    return {'single_lane_causal_receiving_ramps': list(names),
            'single_lane_receiving_wave_m_s': wave}
