"""Identify regional lane transitions from five-second interval endpoints.

Cross-cell transitions inside the same physical region remain observations.
This is still a conditional-on-region-survival estimate, not full trajectory truth.
"""
import collections
import copy
import math
from pathlib import Path
import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent
EDGES = ((0, 1), (1, 0), (1, 2), (2, 1))


def transition(logrates, dt=5.):
    q = np.zeros((3, 3))
    for (i, j), rate in zip(EDGES, np.exp(logrates)):
        q[i, j] = rate
    q -= np.diag(q.sum(axis=1))
    nu = max(-np.diag(q))
    if nu == 0:
        return np.eye(3)
    a = np.eye(3) + q / nu
    term = np.eye(3)
    weight = math.exp(-nu * dt)
    p = weight * term
    for k in range(1, 80):
        term = term @ a
        weight *= nu * dt / k
        p += weight * term
        if k > 8 and weight < 1e-16:
            break
    assert np.min(p) >= -1e-14 and np.max(np.abs(p.sum(axis=1) - 1)) < 1e-13
    return p


def fit(counts, initial):
    lo, hi = math.log(1e-5), math.log(.05)
    n = float(counts.sum())
    def loss(z):
        return float(-np.sum(counts * np.log(np.maximum(transition(z), 1e-30))) / n)
    z = np.array(initial, dtype=float)
    history = [loss(z)]
    eps = 2e-4
    for sweep in range(100):
        before = z.copy()
        for j in range(4):
            a, b = z.copy(), z.copy()
            a[j] += eps
            b[j] -= eps
            f, fa, fb = loss(z), loss(a), loss(b)
            grad = (fa-fb) / (2*eps)
            curvature = max(1e-8, (fa-2*f+fb) / eps**2)
            step = float(np.clip(z[j]-grad/curvature, lo, hi)-z[j])
            for _ in range(24):
                trial = z.copy()
                trial[j] += step
                if loss(trial) <= f + 1e-14:
                    z = trial
                    break
                step *= .5
        history.append(loss(z))
        if max(abs(z-before)) < 1e-8:
            break
    gradients = []
    for j in range(4):
        a, b = z.copy(), z.copy()
        a[j] += eps
        b[j] -= eps
        g = (loss(a)-loss(b)) / (2*eps)
        gradients.append(min(g, 0.) if z[j] <= lo+1e-7 else max(g, 0.) if z[j] >= hi-1e-7 else g)
    assert max(abs(x) for x in gradients) < 1e-6
    assert all(b <= a+1e-12 for a, b in zip(history, history[1:]))
    return z.tolist(), dict(sweeps=sweep+1, normalized_nll=history[-1],
                          projected_gradient=max(abs(x) for x in gradients), history=history)


def region(cell):
    return 0 if 20 <= cell <= 21 else 1 if 22 <= cell <= 25 else None


def main():
    assert not (HERE/'protocol.json').exists()
    previous = h.read(h.R/'exit_refit191/protocol.json')
    h.save(HERE/'protocol.json', dict(
        previous_goal_turn='PROGRESS191: bounded joint refit completed/rejected; no live forecast',
        hypothesis='168 same-cell endpoint censoring omits cross-cell lane changes, especially short21/22. Test interval-likelihood identification of the SAME two regional four-direction rates.',
        source='Exact148/132 plus171; no190 split20,178phase,189priority,191refit.',
        train='Only existing29 NC/VSL frames2220.1..2970.1, two frozen regional generators20-21 and22-25. No67/43 gain fitting.',
        method='MLE of exp(5Q) over region-surviving endpoint lane pairs; adjacent birth-death Q, four rates/region bounded1e-5..0.05/s. No new speed/density covariates or command labels.',
        limitations='Conditioning on both endpoints remaining in a region can still select slow survivors. Unknown crossing locations, return changes and departures are not direct event counts. No claim of unbiased microscopic rates.',
        literature='Chen2021 Eq8 target density-ratio recovery overlaps existing linear net exchange; not adding it as a duplicate penalty. This probe changes observation likelihood, not physical law.',
        prior_reviewed='Local Claude REVIEW/REVIEW_CHECK context,166/167/168 lateral event definitions and172/174 separate merge diagnostics. No coefficients imported from v3c3.',
        budget=dict(new_fits=2,forecasts450_max=13,native=0,FZP_reads=0),
        gates='Fit and freeze before heldout transition scores; at most one autonomous12-condition candidate plus parity.150/450 physical gain gates unchanged; no further rate grid on failure.',
        protected_sha256=previous['protected_sha256'],STOP=previous['STOP']))
    inputs = h.read(h.R/'state_information92/protocol.json')['inputs']
    tables = {}
    pins = {str(Path(__file__)): h.sha(__file__)}
    for case, info in inputs.items():
        path = h.ROOT/info['path']
        assert h.sha(path) == info['sha256']
        pins[str(path)] = info['sha256']
        doc = h.read(path)
        fs = {float(t): {vid: dict(zip(doc['fields'], x)) for vid, x in frame.items()} for t, frame in doc['frames'].items()}
        counts = np.zeros((2, 3, 3), dtype=int)
        subsets = np.zeros_like(counts)
        excluded = collections.Counter()
        for t, u in zip(sorted(fs), sorted(fs)[1:]):
            assert abs(u-t-5) < 1e-6
            for vid, a in fs[t].items():
                reg = region(a['cell'])
                if reg is None:
                    continue
                b = fs[u].get(vid)
                if b is None:
                    excluded['missing_next'] += 1
                elif region(b['cell']) != reg:
                    excluded['leaves_region'] += 1
                else:
                    i, j = int(a['lane'])-1, int(b['lane'])-1
                    assert i in range(3) and j in range(3)
                    counts[reg, i, j] += 1
                    if a['cell'] == b['cell']:
                        subsets[reg, i, j] += 1
        tables[case] = dict(counts=counts.tolist(), same_cell_counts=subsets.tolist(), excluded=dict(excluded))
    h.save(HERE/'endpoint_counts.json', tables)
    old = h.read(h.R/'state_lateral168/coefficients.json')['regional']
    fitted = []
    fitting = []
    for reg in (0, 1):
        counts = sum(np.array(v['counts'])[reg] for k, v in tables.items() if k.startswith('29_'))
        z, audit = fit(counts, old[reg*4:reg*4+4])
        fitted.extend(z)
        fitting.append(dict(region=reg, counts=counts.tolist(), **audit))
    # Immutable fitted coefficients precede heldout scoring.
    h.save(HERE/'coefficients.json', dict(regional=fitted, rate_matrices=[
        [[math.exp(fitted[reg*4+EDGES.index((i,j))]) if (i,j) in EDGES else 0. for j in range(3)] for i in range(3)]
        for reg in (0,1)], fits=fitting))
    scores = []
    for case, table in tables.items():
        for reg in (0, 1):
            c = np.array(table['counts'][reg])
            for label, z in [('168regional', old), ('192interval', fitted)]:
                p = transition(z[reg*4:reg*4+4])
                scores.append(dict(case=case, region=reg, model=label, observations=int(c.sum()),
                    normalized_nll=float(-np.sum(c*np.log(p))/c.sum()),
                    observed_lane_changes=int(c.sum()-np.trace(c)),
                    predicted_endpoint_changes=float(sum(c[i].sum()*(1-p[i,i]) for i in range(3)))))
    h.save(HERE/'transfer_scores.json', scores)
    # Semigroup and two-state analytic checks validate interval probabilities.
    rng = np.random.default_rng(192)
    maximum = 0.
    for _ in range(30):
        z = rng.uniform(math.log(1e-5), math.log(.05), 4)
        maximum = max(maximum, float(np.max(np.abs(transition(z, 5)-np.linalg.matrix_power(transition(z, 1), 5)))))
    assert maximum < 1e-12
    prepare()


def prepare():
    previous = h.read(HERE/'protocol.json')
    inputs = h.read(h.R/'state_information92/protocol.json')['inputs']
    pins = {str(h.ROOT/v['path']): v['sha256'] for v in inputs.values()}
    pins[str(Path(__file__))] = h.sha(__file__)
    maximum = 0.
    for z in np.random.default_rng(192).uniform(math.log(1e-5), math.log(.05), (30, 4)):
        maximum = max(maximum, float(np.max(np.abs(transition(z,5)-np.linalg.matrix_power(transition(z,1),5)))))
    assert maximum < 1e-12
    coeff = h.read(HERE/'coefficients.json')
    source = h.read(h.R/'spatial_context148/forecast/executed_function_sources.json')
    oldsource = copy.deepcopy(source)
    cls = source['RouteLaneRegion']
    token = "        self.rates = copy.deepcopy(spec['exchange_rates_per_sec'])\n"
    assert cls.count(token) == 1
    cls = cls.replace(token, token+"        self.rates192 = spec.get('sampling192_rates')\n        self.lateral192_rows = []\n")
    token = '            for g,rates in enumerate(self.rates):\n                hazard = sum(rates)\n'
    assert cls.count(token) == 1
    cls = cls.replace(token, "            active_rates = self.rates192[int(i>=22)] if self.rates192 is not None else self.rates\n            for g,rates in enumerate(active_rates):\n                hazard = sum(rates)\n")
    token = '            moment = [n*v for n,v in zip(ns,self.oldv[i])]\n'
    assert cls.count(token) == 1
    cls = cls.replace(token, "            self.lateral192_rows.append(dict(time_s=state.time_sec,cell=i,donor_stock=list(ns),state_n=list(self.n0[i]),state_v=list(self.oldv[i]),accepted=copy.deepcopy(matrix)))\n"+token)
    source['RouteLaneRegion'] = cls
    assert all(source[k] == v for k,v in oldsource.items() if k != 'RouteLaneRegion')
    h.save(HERE/'executed_function_sources.json', source)
    spec = h.read(h.F/'joint_lane_25/protocol.json')['candidate']
    spec.update(congested_receiving_cells=[21], reciprocal_off='10483',sampling192_rates=coeff['rate_matrices'])
    h.save(HERE/'spec.json', spec)
    for path, digest in {**pins, **previous['protected_sha256'], previous['STOP']['path']:previous['STOP']['sha256']}.items():
        assert h.sha(path) == digest, path
    h.save(HERE/'pins.json', pins)
    h.save(HERE/'preflight.json', dict(status='pass', semigroup_max_error=maximum, source_only_lateral_rates=True,
                                     fits=coeff['fits'], coefficients_frozen_before_scoring=True))
    h.save(HERE/'status.json',dict(status='prepared',forecasts=0,adopted=False))
    print('RATES_NEW', np.exp(coeff['regional']).tolist())
    print('PREPARED; existing coefficient file reused, no refit in prepare')


if __name__ == '__main__':
    import sys
    prepare() if '--prepare-only' in sys.argv else main()
