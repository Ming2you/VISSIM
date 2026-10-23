"""Freeze one unfit CDF/cap hypothesis and check its algebra, using saved evidence."""
import gzip
import hashlib
import json
import math
from pathlib import Path
from cdf_congestion_cap import capped_mean, cap_for_mean, CDFCongestionCap
from distribution_contract import quantile

A = Path(__file__).resolve().parent
O = A / 'cdf_cap_candidate'
PINS = {}


def read(p):
    raw = p.read_bytes()
    PINS[str(p)] = hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if p.suffix == '.gz' else raw)


def main():
    assert not O.exists()
    contract = read(A / 'distribution_contract.json')
    for p, digest in contract['source_pins'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest() == digest
    read(A / 'interaction_response/decision.json')
    rows = {int(k): v for k, v in contract['distributions'].items()}
    candidate = CDFCongestionCap(rows)
    checks = []
    assert capped_mean([(0., 80.), (1., 120.)], 100.) == 95.
    checks.append('analytic_uniform_integral')
    assert capped_mean([(0., 90.), (1., 90.)], 100.) == 90.
    checks.append('constant_distribution')
    for cap in (40., 80., 95., 110., 140.):
        for cmd in (90, 110):
            points = rows[cmd]['points']
            numerical = math.fsum(min(cap, quantile(points, (i + .5) / 20000)) for i in range(20000)) / 20000
            assert abs(capped_mean(points, cap) - numerical) < 1e-5
    checks.append('independent_midpoint_quadrature')
    for fraction in (0., .25, .5, .75, .9, .99, 1.):
        requested = rows[110]['mean'] * fraction
        assert abs(capped_mean(rows[110]['points'], cap_for_mean(rows[110]['points'], requested)) - requested) < 1e-9
    checks.append('inverse_baseline_parity')
    for rho in (0., 10., 30., 60., 100.):
        assert candidate.target(120., 30., 2., rho, 110) == 120. * math.exp(-(rho / 30.) ** 2 / 2)
    checks.append('inactive110_exact')
    assert abs(candidate.target(120., 30., 2., 100., 90) - candidate.target(120., 30., 2., 100., 110)) < 1e-10
    checks.append('deep_congestion_no_extra_braking')
    assert abs(candidate.target(120., 30., 2., 0., 90) - 120. * rows[90]['mean'] / rows[110]['mean']) < 1e-9
    checks.append('freeflow_native_cdf_mean_ratio')
    try:
        candidate.target(120., 30., 2., 10., 100.)
    except ValueError:
        checks.append('unqualified_commands_rejected')
    else:
        raise AssertionError('Unqualified command accepted')
    # Summarize PRE-treatment matching without filtering on current outcomes.
    details = read(A / 'interaction_response/first_exposures.json')
    base = {(r[0], r[1]): r for r in read(A / 'interaction_response/hold_records.json.gz')['rows']}
    strata = []
    for case in ('single90', 'selected'):
        eligible = [r for r in details if r['case'] == case and r['pre_identical']]
        for name, lo, hi in [('below_new_desired_by10', -math.inf, -10), ('within10', -10, 10), ('above_new_desired_by10', 10, math.inf)]:
            samples = [r for r in eligible if lo <= base[round(r['time'] - 5, 1), r['vehicle']][5] - r['selected_desired'] < hi]
            strata.append(dict(case=case, stratum=name, n=len(samples),
                mean_speed_delta=math.fsum(r['speed_delta'] for r in samples) / len(samples),
                mean_endpoint_acceleration_delta=math.fsum(r['acceleration_delta'] for r in samples) / len(samples),
                unchanged_speed=sum(abs(r['speed_delta']) < 1e-8 for r in samples)))
    for p in (Path(__file__), A / 'cdf_congestion_cap.py'):
        PINS[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    protocol = dict(status='qualified_for_two_scalar_conditional_forecasts',
        hypothesis='A mean FD shift applies excess VSL braking below the effective desired-speed constraint. Replace only the active desired-speed target with a native-CDF mixture under a common density-dependent traffic cap, with the unchanged110 FD reproduced exactly.',
        formula='s=vfree/E[Q110]; choose w so E[min(Q110,w)]=V110(rho)/s; Vc(rho)=s E[min(Qc,w)]',
        comparison='This inferred common traffic cap is an aggregate closure assumption, not a native Wiedemann rule or empirical capacity gain. Existing VSL cohort transport/point exposure and all other coefficients are unchanged.',
        budget={'forecasts': 2, 'fits': 0, 'native': 0, 'full_optimizations': 0},
        cases=['single90', 'selected'], baseline='Reuse unchanged110 matched_off2250_v3; no baseline forecast',
        checks=checks, first_exposure_strata=strata,
        gate='Conservation, exact initial/command parity, feasible450 model path; inspect150/300/450 flow, stocks, Omega and external costs. A clear wrong response or degraded local error rejects the candidate as sufficient. Tiny Omega sign alone is never a gate. Independent native cases plus scalar/AD and NP/NUF checks remain required before adoption.',
        limitations=['Common cap and homogeneous per-command CDF within a cell are hypotheses; no leader gaps or lane sorting represented.',
            'One common vfree/CDFmean normalization preserves the calibrated baseline but is not a literal physical speed cap.',
            'Some low native fractiles INCREASE under distribution90; retain the original distributions rather than forcing monotonicity.',
            'First-exposure comparisons span up to5s with unknown within-step crossing time and interacting traffic; they do not identify an acceleration coefficient.',
            'Endpoint acceleration may recover after braking; speed change is also retained.',
            'Scalar90/110 prototype only; no AD, other commands, or SDMPC selection qualification.'],
        references=['https://www.dcsc.tudelft.nl/~bdeschutter/pub/rep/02_015.pdf',
            'https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/5_Netzbearbeiten/Strassennetz_Wunschg_vWunsch_aendern.htm',
            'https://www.cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/4_BasisdatenSim/BasisdatenWunschgeschw_verteil_verw.htm'],
        source_pins=PINS, candidate_adopted=False)
    O.mkdir()
    (O / 'protocol.json').write_text(json.dumps(protocol, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    print(json.dumps({'checks': checks, 'strata': strata}, indent=2))


if __name__ == '__main__':
    main()
