"""Offline scalar hypothesis: an unchanged FD realized through a common traffic cap.

This is a diagnostic alternative to Carlson's command-dependent FD, not an
implementation of Wiedemann or a production calibration. No parameters fitted.
"""
import math


def capped_mean(points, cap):
    """Exact integral of min(Q(p), cap) for a piecewise-linear quantile Q."""
    total = 0.
    for (p, x), (q, y) in zip(points, points[1:]):
        if cap <= x:
            mean = cap
        elif cap >= y:
            mean = (x + y) / 2
        else:
            mean = cap - (cap - x) ** 2 / (2 * (y - x))
        total += (q - p) * mean
    return total


def cap_for_mean(points, mean):
    """Invert the baseline capped mean; endpoints preserve the original FD."""
    maximum = points[-1][1]
    free_mean = capped_mean(points, maximum)
    if not 0 <= mean <= free_mean * (1 + 1e-14):
        raise ValueError('Requested mean is outside the baseline distribution')
    if mean <= points[0][1]:
        return mean
    if mean >= free_mean:
        return maximum
    lo, hi = points[0][1], maximum
    for _ in range(42):
        mid = (lo + hi) / 2
        if capped_mean(points, mid) < mean:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


class CDFCongestionCap:
    def __init__(self, distributions):
        self.distributions = {int(k): v for k, v in distributions.items()}
        self.baseline = self.distributions[110]['points']
        self.mean110 = self.distributions[110]['mean']
        self.calls = 0

    def target(self, vf, critical, shape, rho, command):
        if command not in (90, 110):
            raise ValueError('Only the declared 90/110 diagnostic is qualified')
        nominal = vf * math.exp(-(max(0., rho) / critical) ** shape / shape)
        if command == 110:
            return nominal
        self.calls += 1
        # Calibrated vf supplies one common units/mean normalization. The
        # traffic cap is inferred from the model's CURRENT density, never
        # from future native speed or interaction labels.
        scale = vf / self.mean110
        cap = cap_for_mean(self.baseline, nominal / scale)
        return scale * capped_mean(self.distributions[90]['points'], cap)

    def install(self, fd, area):
        original = fd.literature_desired_speed
        # PhysicalLaneGroups imports this hook inside _desired_speed, so it
        # follows fd directly. The aggregate module retains an imported alias.
        self.saved = [(fd, original), (area, area.literature_desired_speed)]
        def replacement(spec, cfg, road, cell, rho, target, command, active):
            if spec is None or not active:
                return original(spec, cfg, road, cell, rho, target, command, active)
            if not isinstance(rho, (float, int)) or not isinstance(command, (float, int)):
                raise TypeError('This diagnostic has no tangent implementation')
            if spec != {'law': 'carlson', 'A': .5, 'E': 2., 'alpha': 0.}:
                raise ValueError('Unexpected adopted baseline VSL law')
            net = cfg.network
            row = net.freeway_segment_params[road][cell]
            return self.target(row.get('v_free', net.v_free),
                row.get('rho_crit', net.rho_crit),
                row.get('metanet_a_m', net.metanet_a_m), rho, command)
        for module, old in self.saved:
            module.literature_desired_speed = replacement

    def restore(self):
        for module, old in self.saved:
            module.literature_desired_speed = old
