"""Pure readback completeness checks shared by observation and replay diagnostics."""
from __future__ import annotations
from collections import Counter, defaultdict
import math
from diagnostics.live_beta0_first_interval_audit import trace_audit


def strict_signal_trace(rows, controllers, ramps, *, start, end):
    """Require one immediate and one post-step row for every commanded SG/second.

    The historical trace auditor integrates from the last immediate write; that
    alone cannot distinguish continuously observed holds from missing rows.
    """
    if int(start) != start or int(end) != end:
        raise ValueError('Strict signal audit requires integer interval endpoints.')
    groups = {(str(sc), str(sg)) for sc, node in controllers.items() for sg in node['windows']}
    ramp_groups = {(str(sc), '1') for sc in ramps}
    groups.update(ramp_groups)
    expected = {'immediate': set(range(int(start), int(end))),
                'post_step': set(range(int(start)+1, int(end)+1))}
    observed = defaultdict(Counter)
    observed_rows = defaultdict(list)
    invalid_times = []
    for index, row in enumerate(rows):
        key = (str(row.get('sc_no')), str(row.get('sg_no')))
        stage = row.get('stage')
        if key not in groups or stage not in expected:
            continue
        try:
            sec = float(row['sim_sec'])
        except (KeyError, TypeError, ValueError):
            invalid_times.append({'sc': key[0], 'sg': key[1], 'stage': stage, 'sim_sec': row.get('sim_sec')})
            continue
        if not math.isfinite(sec):
            invalid_times.append({'sc': key[0], 'sg': key[1], 'stage': stage, 'sim_sec': row.get('sim_sec')})
            continue
        if ((stage == 'immediate' and start <= sec < end) or
                (stage == 'post_step' and start < sec <= end)):
            observed[key, stage][sec] += 1
            observed_rows[key, stage, sec].append((index, row))
    problems = []
    allowed_reapplications = []
    duplicate_rows_total = 0
    for key in sorted(groups):
        for stage, times in expected.items():
            counts = observed[key, stage]
            missing = sorted(times-counts.keys())
            duplicates = {str(sec): count for sec, count in counts.items() if count != 1}
            duplicate_rows_total += sum(count-1 for count in counts.values())
            if key in ramp_groups and stage == 'immediate' and counts[start] == 2:
                repeated = observed_rows[key, stage, start]
                if repeated[0][1] == repeated[1][1]:
                    duplicates.pop(str(float(start)), None)
                    allowed_reapplications.append({
                        'sc': key[0], 'sg': key[1], 'sim_sec': start, 'stage': stage,
                        'input_row_indices_zero_based': [entry[0] for entry in repeated],
                        'raw_rows': [dict(entry[1]) for entry in repeated],
                        'basis': 'VBS ApplyActionCsv invokes ApplyRampMeterSignal, then the first step ApplyRuntimeRampMeters reapplies the same meter at the same start second. Exactly two identical ramp rows are permitted only here.'})
            unexpected = sorted(counts.keys()-times)
            if missing or duplicates or unexpected:
                problems.append({'sc': key[0], 'sg': key[1], 'stage': stage,
                                 'missing_seconds': missing, 'duplicate_seconds': duplicates,
                                 'unexpected_seconds': unexpected})
    result = trace_audit(rows, controllers, ramps, start=start, end=end)
    result['strict_one_second_cadence'] = {
        'valid': bool(groups) and not (problems or invalid_times), 'groups': len(groups),
        'expected_rows_per_stage_per_group': end-start, 'problems': problems,
        'invalid_timestamp_rows': invalid_times,
        'raw_duplicate_rows_total': duplicate_rows_total,
        'allowed_start_ramp_reapplications': allowed_reapplications,
        'definition': 'One immediate row at every second in [start,end), one post_step row in (start,end], except exactly two byte-field-identical immediate ramp rows at start for the documented initial reapplication. All other duplicates fail.'}
    result['valid'] = result['valid'] and result['strict_one_second_cadence']['valid']
    return result



def vsl_readback_matches(row):
    """VBS records exactly DesSpeedDistr(10) and DesSpeedDistr(70)."""
    try:
        expected = float(row['speed_kph'])
        values = [float(value) for value in row['readback'].split('|')]
    except (KeyError, TypeError, ValueError, AttributeError):
        return False
    return (math.isfinite(expected) and len(values) == 2 and
            all(math.isfinite(value) and abs(value-expected) <= 1e-6 for value in values))
