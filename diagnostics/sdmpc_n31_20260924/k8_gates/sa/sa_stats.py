"""Pure statistics for the SA gate calculators (no model imports).

pair_stats       bias / MAE / Pearson r of paired (model, observed) values (u6 analyze_u6.pearson definition:
                 None when n < 3 or a zero variance)
boot_ci_iid      percentile CI of the mean of increments, items resampled with replacement
boot_ci_cluster  percentile CI of the mean of increments, clusters resampled with replacement (all items of a drawn
                 cluster enter; the statistic is the item mean of the drawn sample)
Both bootstraps use numpy.random.default_rng(seed) and `n` draws; the percentile CI is two-sided (2.5, 97.5) for
level 0.95 (np.quantile, linear interpolation)."""
from __future__ import annotations

import math
import statistics as st


def mean(xs):
    xs = list(xs)
    return math.fsum(xs) / len(xs) if xs else None


def median(xs):
    xs = list(xs)
    return st.median(xs) if xs else None


def pearson(x, y):
    """analyze_u6.pearson: None when len < 3 or a zero spread."""
    if len(x) < 3:
        return None
    mx, my = st.mean(x), st.mean(y)
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    if sx == 0 or sy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def pair_stats(model, observed):
    """bias = mean(model - observed), mae = mean |model - observed|, r = pearson(model, observed)."""
    xs = [float(a) for a in model]
    ys = [float(b) for b in observed]
    if len(xs) != len(ys):
        raise ValueError('paired series differ in length')
    if not xs:
        return dict(n=0, bias=None, mae=None, r=None, model_mean=None, obs_mean=None)
    d = [a - b for a, b in zip(xs, ys)]
    return dict(n=len(xs), bias=mean(d), mae=mean(abs(v) for v in d), r=pearson(xs, ys),
                model_mean=mean(xs), obs_mean=mean(ys))


def _quantiles(values, level):
    import numpy as np
    lo = (1.0 - level) / 2.0
    return float(np.quantile(values, lo)), float(np.quantile(values, 1.0 - lo))


def boot_ci_iid(increments, *, n=2000, seed=0, level=0.95):
    import numpy as np
    x = np.asarray([float(v) for v in increments], dtype=float)
    if x.size == 0:
        return dict(n_items=0, mean=None, lo=None, hi=None, draws=n, seed=seed)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, x.size, size=(n, x.size))
    means = x[idx].mean(axis=1)
    lo, hi = _quantiles(means, level)
    return dict(n_items=int(x.size), mean=float(x.mean()), lo=lo, hi=hi, draws=n, seed=seed, level=level)


def boot_ci_cluster(increments, clusters, *, n=2000, seed=0, level=0.95):
    import numpy as np
    x = [float(v) for v in increments]
    if not x:
        return dict(n_items=0, n_clusters=0, mean=None, lo=None, hi=None, draws=n, seed=seed)
    keys = sorted(set(clusters), key=lambda k: (str(type(k)), k))
    groups = {k: [v for v, g in zip(x, clusters) if g == k] for k in keys}
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(n):
        drawn = rng.integers(0, len(keys), size=len(keys))
        vals = [v for i in drawn for v in groups[keys[int(i)]]]
        means.append(math.fsum(vals) / len(vals))
    lo, hi = _quantiles(means, level)
    return dict(n_items=len(x), n_clusters=len(keys), mean=math.fsum(x) / len(x), lo=lo, hi=hi, draws=n, seed=seed,
                level=level)


def rel_diff(a, b):
    """|a - b| / max(|b|, 1e-300)."""
    return abs(float(a) - float(b)) / max(abs(float(b)), 1e-300)
