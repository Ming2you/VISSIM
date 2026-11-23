"""Adjacent executable VSL candidate scores using whole-network predictions."""
import math
import time
import numpy as np


def score_adjacent(coord, anchor, anchor_item, evaluate, quantities, physical_feasible,
                   prices, proximal, resource_scale):
    started = time.perf_counter()
    z = coord.encode(anchor)
    if not coord.valid(z) or not physical_feasible(anchor_item):
        raise ValueError('VSL screen requires a verified physical anchor')
    base_cost = float(anchor_item['objective_veh_h'])
    base_q = np.asarray(quantities(anchor, anchor_item), dtype=float)
    price = np.asarray(prices, dtype=float)
    scale = np.asarray(resource_scale, dtype=float)
    if not np.isfinite(base_cost) or not np.isfinite(base_q).all() or not np.isfinite(price).all() or np.any(scale <= 0):
        raise ValueError('Invalid VSL screen anchor or prices')
    candidates, descriptors, details = [], [], {}
    for j, axis in enumerate(coord.axes):
        if axis['kind'] != 'vsl' or axis.get('block', 0) != 0:
            continue
        key = ('vsl', axis['key'])
        label = '/'.join(key)
        if label in details:
            raise ValueError('Duplicate first-block VSL group')
        current = float(axis['reference_value'] + z[j]*axis['scale'])
        allowed = sorted(set(map(float, axis['allowed'])))
        if not any(math.isclose(v, current, abs_tol=1e-6) for v in allowed):
            raise ValueError('Anchor VSL is not a legal actuator value')
        below = [v for v in allowed if v < current-1e-8]
        above = [v for v in allowed if v > current+1e-8]
        nearby = ([max(below)] if below else []) + ([min(above)] if above else [])
        details[label] = {'anchor_kmh': current, 'trials': [], 'chosen_kmh': None,
                          'basis': 'first block only; other controls fixed'}
        for target in nearby:
            dz = (target-current)/axis['scale']
            trial_z = z.copy(); trial_z[j] += dz
            if not coord.valid(trial_z):
                details[label]['trials'].append({'target_kmh': target, 'status': 'actuator_or_sequence_infeasible'})
                continue
            try:
                action = coord.decode(trial_z, anchor)
                coord.validate(action)
            except ValueError:
                details[label]['trials'].append({'target_kmh': target, 'status': 'decode_infeasible'})
                continue
            actual_z = coord.encode(action)
            changed = np.flatnonzero(np.abs(actual_z-z) > 1e-9)
            if changed.tolist() != [j] or not np.isclose(actual_z[j]-z[j], dz, atol=1e-8):
                raise ValueError('VSL probe changed another control coordinate')
            candidates.append(action)
            descriptors.append((key, label, current, target, float(dz)))
    results = evaluate(candidates, derivatives=False) if candidates else []
    if len(results) != len(candidates):
        raise ValueError('Missing VSL prediction results')
    scores = {('vsl', label.split('/', 1)[1]): 0.0 for label in details}
    for action, item, (key, label, current, target, dz) in zip(candidates, results, descriptors):
        if not physical_feasible(item):
            details[label]['trials'].append({'target_kmh': target, 'status': 'physical_model_infeasible'})
            continue
        q = np.asarray(quantities(action, item), dtype=float)
        objective = float(item['objective_veh_h'])
        if not np.isfinite(q).all() or not np.isfinite(objective):
            raise ValueError('Nonfinite VSL candidate prediction')
        delta_q = (q-base_q)/scale
        delta_cost = objective-base_cost
        regularizer = .5*float(proximal)*dz*dz
        delta_lagrangian = delta_cost + float(price @ delta_q) + regularizer
        improvement = max(0., -delta_lagrangian)
        details[label]['trials'].append(dict(target_kmh=target, status='predicted',
            normalized_step=dz, objective_delta_veh_h=delta_cost,
            resource_delta_scaled=delta_q.tolist(), proximal_term=regularizer,
            lagrangian_delta=delta_lagrangian, score=improvement))
        if improvement > scores[key]:
            scores[key] = improvement
            details[label]['chosen_kmh'] = target
    for label in details:
        details[label]['elapsed_batch_sec'] = time.perf_counter()-started
    return scores, details
