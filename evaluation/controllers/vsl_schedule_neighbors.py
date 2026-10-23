"""Finite physical VSL schedules; no activation reward or changed traffic model.

At the standard two-road/four-zone layout this proposes at most 25 schedules:
each zone at 90 for two or three blocks, adjacent pairs and each whole road
for three blocks, and both roads together. Caps and other actuators are fixed.
"""


def schedules(coord, anchor):
    axes, owners = {}, {}
    for j, axis in enumerate(coord.axes):
        if axis['kind'] == 'vsl':
            axes.setdefault(axis['key'], []).append(j)
            owners.setdefault(axis['owner'], set()).add(axis['key'])
    groups = []
    for owner, keys in sorted(owners.items()):
        keys = sorted(keys, key=lambda key: int(key.rsplit('__seg', 1)[1]))
        groups.extend((key, [key], duration) for key in keys for duration in (2, 3))
        groups.extend((f'{owner}:adjacent:{a}+{b}', [a, b], 3)
                      for a, b in zip(keys, keys[1:]))
        if len(keys) > 1:
            groups.append((owner + ':all', keys, 3))
    if len(owners) > 1:
        groups.append(('all_roads', sorted(axes), 3))
    start = coord.encode(anchor)
    seen = {tuple(start)}
    result, skipped = [], []
    for label, keys, duration in groups:
        label = f'{label}:90x{duration}'
        z = start.copy()
        illegal = False
        for key in keys:
            indices = sorted(axes[key], key=lambda j: coord.axes[j].get('block', 0))
            if [coord.axes[j].get('block', 0) for j in indices] != [0, 1, 2]:
                raise ValueError('VSL schedule audit requires three complete control blocks')
            for j in indices[:duration]:
                axis = coord.axes[j]
                if 90 not in axis['allowed']:
                    illegal = True
                    break
                z[j] = (90 - axis['reference_value']) / axis['scale']
        if illegal or not coord.valid(z):
            skipped.append(dict(candidate=label, reason='physical_command_or_move_bounds'))
            continue
        if tuple(z) in seen:
            continue
        candidate = coord.decode(z, anchor)
        coord.validate(candidate)
        actual = coord.encode(candidate)
        if any(abs(actual[j] - start[j]) > 1e-10 for j, axis in enumerate(coord.axes)
               if axis['kind'] != 'vsl'):
            raise ValueError('VSL schedule changed another actuator')
        if (candidate.N_P_star, candidate.N_UF_star) != (anchor.N_P_star, anchor.N_UF_star):
            raise ValueError('VSL schedule changed shared caps')
        if max(abs(actual - z), default=0.) > 1e-10:
            raise ValueError('Decoded VSL schedule differs from its legal proposal')
        if tuple(actual) not in seen:
            seen.add(tuple(actual))
            result.append((label, candidate))
    return result, skipped


def audit(coord, best, tolerance, evaluate, feasible):
    """Evaluate complete schedules once with the incumbent's unchanged cap.

    A combined schedule is tested even when its individual components lose.
    This is a bounded neighborhood, not a convergence or exhaustive claim.
    """
    baseline = best[1]['objective_veh_h']
    proposals, skipped = schedules(coord, best[0])
    values = evaluate([action for _, action in proposals]) if proposals else []
    if len(values) != len(proposals):
        raise ValueError('Incomplete finite VSL schedule evaluation')
    rows, selected = [], None
    for (label, action), item in zip(proposals, values):
        valid = feasible(action, item)
        rows.append(dict(candidate=label, objective=item['objective_veh_h'],
                         delta_veh_h=item['objective_veh_h'] - baseline, feasible=valid))
        if valid and item['objective_veh_h'] < best[1]['objective_veh_h'] - tolerance:
            best, selected = (action, item, None), label
    return best, dict(baseline_objective=baseline, selected=selected, candidates=rows,
                      skipped=skipped, additional_predictions=len(values), exhaustive=False,
                      scope='Finite 90 km/h schedules; unchanged signals, RM, NP and NUF caps')
