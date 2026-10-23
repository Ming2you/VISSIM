"""Counterfactual target values on frozen old trajectories; not new forecasts."""
import gzip
import hashlib
import json
import math
from pathlib import Path
from cdf_congestion_cap import CDFCongestionCap

A = Path(__file__).resolve().parent
H = A.parent
O = A / 'cdf_cap_candidate'
PINS = {}


def read(p):
    raw = p.read_bytes()
    PINS[str(p)] = hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if p.suffix == '.gz' else raw)


def main():
    assert not (O / 'cached_target_audit.json').exists()
    config = read(H / 'cached_vsl_exposure_audit_v2/active_component_config.json')
    assert config['active_component_fd'] == {'law': 'carlson', 'A': .5, 'E': 2., 'alpha': 0.}
    candidate = CDFCongestionCap(read(A / 'distribution_contract.json')['distributions'])
    summaries = []
    max_legacy_error = 0.
    detailed = []
    for case in ('hold', 'single90', 'selected'):
        rows = read(H / 'cached_vsl_exposure_audit_v2' / f'{case}_rows.json.gz')
        for r in rows:
            p = config['parameters'][r['cell']]
            vf, rc, a, rho = p['v_free'], p['rho_crit'], p['metanet_a_m'], r['rho']
            nominal = vf * math.exp(-(max(0., rho) / rc) ** a / a)
            b = 90 / 110
            shifted_rc, shifted_a = rc * (1 + .5 * (1 - b)), a * (2 - b)
            carlson90 = vf * b * math.exp(-(max(0., rho) / shifted_rc) ** shifted_a / shifted_a)
            error = max(abs(nominal-r['target110']), abs(carlson90-r['target90']))
            assert error < 1e-7, (case, r['cell'], error)
            max_legacy_error = max(max_legacy_error, error)
            new90 = candidate.target(vf, rc, a, rho, 90)
            detailed.append(dict(case=case, cell=r['cell'], start_sec=r['start_sec'], end_sec=r['end_sec'],
                rho=rho, fraction90=r['fraction90'], nominal=nominal,
                old_direct_delta=r['fraction90'] * (carlson90 - nominal),
                candidate_direct_delta=r['fraction90'] * (new90 - nominal)))
    for case in ('hold', 'single90', 'selected'):
        for cell in range(14, 26):
            for block in range(3):
                rows = [r for r in detailed if r['case'] == case and r['cell'] == cell
                        and 2250 + block * 150 <= r['start_sec'] < 2400 + block * 150]
                assert abs(sum(r['end_sec']-r['start_sec'] for r in rows) - 150) < 1e-7
                means = {k: math.fsum(r[k] * (r['end_sec'] - r['start_sec']) for r in rows) / 150
                         for k in ('rho', 'fraction90', 'nominal', 'old_direct_delta', 'candidate_direct_delta')}
                summaries.append(dict(case=case, cell=cell, block=block, **means))
    for p in (Path(__file__), A / 'cdf_congestion_cap.py'):
        PINS[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    output = dict(status='complete_counterfactual_target_values_on_fixed_old_trajectory',
        updates=len(detailed), legacy_formula_max_error=max_legacy_error, rows=summaries,
        source_pins=PINS, new_forecasts=0, new_native=0, fits=0, production_edits=0,
        limitation='State, density, VSL cohorts and all other forces are held at the old trajectories. This is a target-law diagnostic only, not a corrected trajectory, outflow, Omega benefit, or independent validation.')
    (O / 'cached_target_audit.json').write_text(json.dumps(output, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'updates': len(detailed), 'legacy_max_error': max_legacy_error,
                      'selected_cell18': [r for r in summaries if r['case'] == 'selected' and r['cell'] == 18]}, indent=2))


if __name__ == '__main__':
    main()
