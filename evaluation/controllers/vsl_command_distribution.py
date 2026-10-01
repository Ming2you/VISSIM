"""VSL command -> written desired-speed distribution number (plan REPIN_V3C2 K2/K5, U3-a).

The controller, the SDMPC axes (sdmpc.py:333-341), the action JSON `vsl` and the plant law all stay in
COMMAND space: config_overrides.freeway_follower.vsl_set, km/h. Only the action CSV column `speed_kph` of a
`vsl` row is what the runner writes as a desired-speed DISTRIBUTION number
(run_real_world_stackelberg_controller.vbs SetClassSpeedChecked: DesSpeedDistr(cls) = CLng(speed), read back,
against RW_ALLOWED_VSL_SPEEDS of the runner config). Two families:

  key absent      identity. Command c is written as c (the network distribution c, e.g. the spread 80/90/100
                  distributions of the N1 L1 law). Byte-identical to the writer before this module.
  single_value    actuation.vsl_command_distribution =
                      {'model': 'single_value', 'distribution_by_command': {'80': 81, '90': 91, '100': 101, '110': 110}}
                  command c is written as distribution_by_command[str(int(c))].

parse() validates a map against a vsl_set: exactly the vsl_set commands as positive-integer string keys, positive
integer values, injective, the maximum command (VSL off) written as itself. written_set() is the image of the
tuning vsl_set: the only speed_kph values a VSL row may carry. runner_allowed_speeds() reads the runner constant.
"""
from __future__ import annotations

import math
import re
from typing import Mapping

KEY = 'vsl_command_distribution'
MODELS = ('single_value',)
_INTEGER = re.compile(r'[1-9][0-9]*')
_RUNNER = re.compile(r'RW_ALLOWED_VSL_SPEEDS\s*=\s*"([0-9]+(?:,[0-9]+)*)"')


def command_set(vsl_set):
    """The vsl_set as a list of distinct positive finite floats (its own order)."""
    if not isinstance(vsl_set, (list, tuple)) or not vsl_set:
        raise ValueError('VSL commands require a non-empty vsl_set list')
    values = []
    for value in vsl_set:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f'VSL command must be a positive finite number: {value!r}')
        values.append(float(value))
    if len(set(values)) != len(values):
        raise ValueError('vsl_set repeats a command')
    return values


def tuning_vsl_set(tuning):
    """config_overrides.freeway_follower.vsl_set of an effective tuning, validated."""
    overrides = tuning.get('config_overrides') if isinstance(tuning, Mapping) else None
    follower = overrides.get('freeway_follower') if isinstance(overrides, Mapping) else None
    return command_set(follower.get('vsl_set') if isinstance(follower, Mapping) else None)


def parse(actuation, vsl_set):
    """None when the key is absent (identity), else {command: distribution number} in vsl_set order."""
    if actuation is None or KEY not in actuation:
        return None
    commands = command_set(vsl_set)
    spec = actuation[KEY]
    if (not isinstance(spec, Mapping) or set(spec) != {'model', 'distribution_by_command'}
            or spec['model'] not in MODELS):
        raise ValueError("actuation.vsl_command_distribution must be exactly "
                         "{'model': 'single_value', 'distribution_by_command': {...}}")
    table = spec['distribution_by_command']
    if not isinstance(table, Mapping) or not table:
        raise ValueError('vsl_command_distribution.distribution_by_command must be a non-empty object')
    mapping = {}
    for key, value in table.items():
        if not isinstance(key, str) or _INTEGER.fullmatch(key) is None:
            raise ValueError(f'VSL command key must be a positive integer string: {key!r}')
        if type(value) is not int or value <= 0:
            raise ValueError(f'Written VSL distribution must be a positive integer: {key} -> {value!r}')
        mapping[float(int(key))] = value
    if set(mapping) != set(commands):
        raise ValueError(f'vsl_command_distribution maps {sorted(mapping)}, the vsl_set is {sorted(commands)}')
    if len(set(mapping.values())) != len(mapping):
        raise ValueError('vsl_command_distribution is not injective: two commands share a written distribution')
    top = max(commands)
    if float(mapping[top]) != top:
        raise ValueError(f'The maximum command {top:g} (VSL off) must be written as itself, not {mapping[top]}')
    return {command: mapping[command] for command in commands}


def written_set(tuning):
    """Sorted speed_kph values a VSL row may carry: the image of the tuning vsl_set under its map."""
    commands = tuning_vsl_set(tuning)
    actuation = tuning.get('actuation')
    mapping = parse(actuation if isinstance(actuation, Mapping) else None, commands)
    return sorted(float(mapping[c]) if mapping is not None else c for c in commands)


def runner_allowed_speeds(text):
    """RW_ALLOWED_VSL_SPEEDS of a generated runner config text, as sorted floats (exactly one plain line)."""
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith('RW_ALLOWED_VSL_SPEEDS')]
    match = _RUNNER.fullmatch(lines[0]) if len(lines) == 1 else None
    if match is None:
        raise ValueError('Runner config must declare RW_ALLOWED_VSL_SPEEDS exactly once as a plain integer list')
    return sorted(float(v) for v in match.group(1).split(','))
