"""Reuse129 sensitivities with current cached lane-state calibration targets.

N*v/L is a spatial movement proxy, NOT a measured boundary discharge.
All future observations here are fitting labels; rollout never consumes them.
"""
import copy
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
R = HERE.parent
ROOT = R.parents[1]
F = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/cellwise_calibration/freeway_first'
INPUTS = {
    ('s29_late', 'hold'): F / 'vsl_native_exposure/s29_late_hold_frames.json.gz',
    ('s29_late', 'hold_vsl90'): F / 'vsl_native_exposure/s29_late_hold_vsl90_frames.json.gz',
    ('s67_late', 'release'): F / 'flow67/release_frames.json.gz',
    ('s67_late', 'release_vsl90'): F / 'flow67/release_vsl90_frames.json.gz',
}
PINS = {}


def read(path):
    raw = Path(path).read_bytes()
    PINS[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def load_targets():
    bounds = read(R / 'lane_interaction110/frames.json.gz')['bounds_m']
    length = {c: (bounds[c+1] - bounds[c]) / 1000 for c in range(19, 26)}
    targets = {}
    for key, path in INPUTS.items():
        data = read(path)
        fields = data['fields']
        ci, vi, li = fields.index('cell'), fields.index('speed_kmh'), fields.index('lane')
        frames = {round(float(t), 1): rows for t, rows in data['frames'].items()}
        assert min(frames) == 2670.1 and max(frames) >= 3120.1
        samples = {}
        for step in range(1, 91):
            t = round(2670.1 + 5 * step, 1)
            rows = frames[t]
            values = {(c, lane): [0., 0.] for c in length for lane in (1, 2, 3)}
            for z in (rows.values() if isinstance(rows, dict) else rows):
                if z[ci] in length:
                    assert z[li] in (1, 2, 3)
                    item = values[z[ci], z[li]]
                    item[0] += 1
                    item[1] += z[vi] / length[z[ci]]
            samples[t] = values
        blocks = []
        for block in range(3):
            stamps = [round(2670.1 + 5 * step, 1) for step in range(30*block+1, 30*block+31)]
            for cell in length:
                for lane in (1, 2, 3):
                    blocks.append(dict(block=block, cell=cell, lane=lane,
                        n=sum(samples[t][cell, lane][0] for t in stamps) / 30,
                        motion=sum(samples[t][cell, lane][1] for t in stamps) / 30))
        targets[key] = dict(blocks=blocks, samples=samples, lengths=length)
    return targets


def attach(row, pred, targets):
    key = row['case'], row['arm']
    if key not in targets:
        return
    target = targets[key]
    recorded = pred['diagnostics']['roads'][0]['joint_lane_region']['rows']
    states = {(round(z['time_s'], 1), z['cell'], z['lane']): z for z in recorded}
    predicted = []
    for a in target['blocks']:
        block, cell, lane = a['block'], a['cell'], a['lane']
        zs = [states[round(2670.1 + 5*step, 1), cell, lane]
            for step in range(30*block+1, 30*block+31)]
        predicted.append(dict(block=block, cell=cell, lane=lane,
            n=sum(z['n_veh'] for z in zs)/30,
            motion=sum(z['n_veh']*z['v_kmh']/target['lengths'][cell] for z in zs)/30))
    row['lane_state'] = dict(actual=target['blocks'], predicted=predicted)


def vectors(rows):
    included = [r for r in rows if 'lane_state' in r]
    assert len(included) == 4
    n, motion, response = [], [], []
    for row in included:
        for a, p in zip(row['lane_state']['actual'], row['lane_state']['predicted']):
            assert (a['block'], a['cell'], a['lane']) == (p['block'], p['cell'], p['lane'])
            n.append((p['n']-a['n'])/4.)
            motion.append((p['motion']-a['motion'])/400.)
    for case in ('s29_late', 's67_late'):
        left, right = sorted([r for r in included if r['case'] == case], key=lambda r: r['arm'])
        assert 'vsl90' not in left['arm'] and 'vsl90' in right['arm']
        la, lp = left['lane_state']['actual'], left['lane_state']['predicted']
        ra, rp = right['lane_state']['actual'], right['lane_state']['predicted']
        for a, p, b, q in zip(la, lp, ra, rp):
            for name, floor in [('n', 2.), ('motion', 200.)]:
                observed, predicted = b[name]-a[name], q[name]-p[name]
                response.append((predicted-observed)/max(floor, abs(observed)))
    return [np.array(v)/math.sqrt(len(v)) for v in (n, motion, response)]


def augmented(original_residual, rows, normalizers):
    parts = [np.asarray(original_residual), *vectors(rows)]
    scores = [float(v@v) for v in parts]
    assert len(normalizers) == len(parts) == 4 and all(x > 0 for x in normalizers)
    return np.concatenate([v/math.sqrt(s) for v, s in zip(parts, normalizers)]), scores


def main():
    assert not (HERE / 'proposal.json').exists(), 'Preserve completed calibration proposal'
    save(HERE / 'analysis_protocol.json', dict(
        previous_goal_turn='PROGRESS:131 separated lane averaging from predicted state bias.',
        reason='129 fits aggregate cell RMSE; lane region uses lane N/v. Add independently observed lane-state and paired-response targets without new physical terms.',
        observations='29late hold/hold_vsl90 and67late release/release_vsl90; these seeds already training. Other4 RM cases retain original aggregate cost/flow response terms.',
        targets='Three150s averages of all3lane N and spatial movement proxy Nv/L in cells19..25, matched5s post-step snapshots. No framewise velocity fitting.',
        objective='Four blocks equally weighted after normalization by cached baseline squared loss: entire129 residual, lane N, lane motion Nv/L, paired lane response; plus0.1 mean squared parameter departure.',
        normalizers=dict(lane_n_veh=4., motion_proxy_vph=400., pair_n_floor_veh=2., pair_motion_floor_vph=200.),
        parameters=['delta21', 'delta23', 'tau_acc19..21', 'rho_crit19..21'],
        bounds=[.7, 1.3], strategy='Reuse129 baseline+8central differences; one bounded least-squares direction, new full/half physical evaluations only. No new Jacobian, widened bound, new structure or fit restart.',
        budget=dict(reused_vectors=9, new_training450=16, optional_autonomous_training450=8, optional_independent_state450=5, native=0, fzp=0),
        gate='Existing129 nonworse450/150 response and >=10% local discharge response improvement; augmented loss>=5% reduction; lane N and motion losses both nonworse, their mean relative loss>=10% reduction. Autonomous/independent/wholeOmega still required.',
        causal_caution='Cached labels score predictions only; no future state enters a rollout. Nv/L is not boundary flow. Shared124 structure remains unadopted.'))
    targets = load_targets()
    evaluations = []
    for i in range(9):
        folder = R / 'merge_response129' / f'eval_{i:02d}'
        item = read(folder / 'result.json')
        for row in item['rows']:
            key = row['case'], row['arm']
            if key in targets:
                pred = read(folder / (key[0] + '_' + key[1] + '.json.gz'))
                attach(row, pred, targets)
        evaluations.append(item)
    base = evaluations[0]
    parts = [np.asarray(base['residual']), *vectors(base['rows'])]
    normalizers = [float(v@v) for v in parts]
    for item in evaluations:
        original = item['residual']
        residual, scores = augmented(original, item['rows'], normalizers)
        item['residual129'] = original
        item['residual'] = residual.tolist()
        item['objective129'] = item['objective']
        item['objective'] = float(residual@residual) + .1*sum((x-1)**2 for x in item['z'])/4
        item['lane_state_scores'] = scores
    r0 = np.asarray(base['residual'])
    jac = np.array([(np.asarray(evaluations[2+2*i]['residual'])-evaluations[1+2*i]['residual'])/.2
                    for i in range(4)]).T
    matrix = np.vstack([jac, math.sqrt(.1/4)*np.eye(4)])
    target = np.r_[-r0, np.zeros(4)]
    solutions = []
    for face in itertools.product((-1, 0, 1), repeat=4):
        step = .3*np.array(face, dtype=float)
        free = [i for i, v in enumerate(face) if v == 0]
        if free:
            step[free] = np.linalg.lstsq(matrix[:, free], target-matrix@step, rcond=None)[0]
        if np.max(np.abs(step)) <= .3+1e-10:
            solutions.append((float(np.sum((matrix@step-target)**2)), step))
    value, step = min(solutions, key=lambda x: x[0])
    gradient = matrix.T@(matrix@step-target)
    tol = 1e-8*max(1., float(np.max(np.abs(matrix.T@target))))
    assert all(g >= -tol if x <= -.3+1e-9 else g <= tol if x >= .3-1e-9 else abs(g) <= tol
               for x, g in zip(step, gradient))
    save(HERE / 'cached_baseline.json', base)
    save(HERE / 'cached_scores.json', [dict(index=i, z=x['z'], objective=x['objective'],
        original_objective=x['objective129'], scores=x['lane_state_scores']) for i, x in enumerate(evaluations)])
    save(HERE / 'proposal.json', dict(step=step.tolist(), full=(1+step).tolist(), half=(1+.5*step).tolist(),
        normalizers=normalizers, predicted_linear_loss=value, kkt_verified=True,
        input_sha256=PINS, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        note='One linearized coefficient proposal from completed129; no new model prediction yet.'))
    for path, expected in PINS.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected
    print(json.dumps(dict(step=step.tolist(), normalizers=normalizers,
        cached=[dict(z=x['z'], objective=x['objective']) for x in evaluations]), indent=2))


if __name__ == '__main__':
    main()
