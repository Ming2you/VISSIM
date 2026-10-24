"""Score a bounded recombination against the identical saved-command baseline."""
from pathlib import Path
import argparse, hashlib, json

HERE = Path(__file__).resolve().parent
H = HERE.parent
MOVEMENT = 'SC101_S_SC1_to_N_SC2005'
pins = {}


def read(p):
    pins[str(p.resolve())] = hashlib.sha256(p.read_bytes()).hexdigest()
    return json.loads(p.read_bytes())


def scalar(summary, key):
    return summary['selected'][key] - summary['hold'][key]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--include3300', action='store_true')
    args = ap.parse_args()
    out = HERE / ('assessment.json' if args.include3300 else 'pair_assessment.json')
    assert not out.exists()
    plan = read(HERE / 'plan.json')
    for p, digest in plan['source_pins'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest() == digest, p
    assert read(HERE / 'completion2400.json')['exit_code'] == 0
    native = read(H / 'service_ceiling/comparison.json')
    baseline = {a: read(H / 'spatial_receiving/forecast2400' / (a + '.json')) for a in ('hold', 'selected')}
    trial = {a: read(HERE / 'forecast2400' / (a + '.json')) for a in baseline}
    head_rows = []
    for arm in baseline:
        actual = next(r['actual'] for r in native['head_comparisons2400']
                      if r['arm'] == arm and r['group'] == 'SC101_S' and r['phase'] == 'p1')
        b = [r['by_movement'][MOVEMENT] for r in baseline[arm]['local']['SC101_S']['bins']]
        c = [r['by_movement'][MOVEMENT] for r in trial[arm]['local']['SC101_S']['bins']]
        head_rows.append(dict(arm=arm, actual=actual, baseline=b, candidate=c,
            baseline_abs_error=sum(abs(x-y) for x,y in zip(actual,b)),
            candidate_abs_error=sum(abs(x-y) for x,y in zip(actual,c))))
    original = read(H / 'spatial_receiving/assessment.json')
    physical = {}
    for arm, summary in trial.items():
        assert summary['writer_validated'] and summary['conservation_states'] == 4
        assert summary['resource_max_exceedance'] <= 1e-7
        physical[arm] = dict(feasible=summary['shared_constraints']['feasible'],
            max_resource_exceedance=summary['resource_max_exceedance'],
            conservation_states=summary['conservation_states'], writer_three_blocks=True,
            omega_veh_h=summary['omega_ttt_veh_h'], merge10681=summary['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681'])
    delta = lambda k: trial['selected']['costs_by_stock'].get(k,0.) - trial['hold']['costs_by_stock'].get(k,0.)
    freeway = sum(delta(k) for k in set().union(*(r['costs_by_stock'] for r in trial.values())) if k.startswith('freeway:'))
    omega = scalar(trial, 'omega_ttt_veh_h')
    wout, ramp = delta('storage:SC1004_W_out'), delta('ramp:RM_C10681')
    old_error = sum(r['baseline_abs_error'] for r in head_rows)
    new_error = sum(r['candidate_abs_error'] for r in head_rows)
    expand = new_error < .8 * old_error and all(r['feasible'] for r in physical.values())
    report = dict(status='bounded_recombination_evaluated', controls='Same2400 joint city/RM hold versus selected,450s; no reoptimization',
        head_comparisons=head_rows, paired_head_abs_error=dict(baseline=old_error,candidate=new_error),
        delta_omega_veh_h=dict(actual=original['native_delta']['omega'],
            baseline=scalar(baseline,'omega_ttt_veh_h'), candidate=omega),
        delta_cost_veh_h=dict(mainline=freeway, W_out=wout, ramp10681=ramp,
            combined=freeway+wout+ramp, remaining_city_and_ramps=omega-freeway-wout-ramp),
        physical=physical, conditional3300_allowed=expand, forecasts_completed=2,
        new_fits=0, reused_past_service_parameters=1, full_ad=0, full_sdmpc=0, new_native=0,
        production_changed=False, calibration_control_gate_passed=False,
        limitations=[
            'This tests an interaction of existing supply and service fixes, not a newly fitted head rate.',
            'A larger past achieved prefix rate is not a guaranteed future saturation capacity.',
            'Initial-support spatial cost attribution is diagnostic; future transit footprint is incomplete.',
            'Fresh3300 is separate from the1650-1950 rate data, but already inspected same-seed development data.',
            'No complete SDMPC wall-time claim from these fixed forecasts.'
        ])
    if args.include3300:
        assert expand and read(HERE / 'completion3300.json')['exit_code'] == 0
        new = read(HERE / 'forecast3300/applied.json')
        base = read(H / 'connector_lane/forecast3300/applied.json')
        actual = next(r['actual'] for r in native['head_comparisons3300'] if r['group']=='SC101_S' and r['phase']=='p1')
        forecast = new['local']['SC101_S']['bins'][0]['by_movement'][MOVEMENT]
        old_forecast = base['local']['SC101_S']['bins'][0]['by_movement'][MOVEMENT]
        assert new['writer_validated'] and new['conservation_states']==2 and new['resource_max_exceedance'] <= 1e-7
        report['fresh3300'] = dict(actual_head=actual, candidate_head=forecast, connector_baseline_head=old_forecast,
            baseline_scope='Prior connector baseline does not contain spatial ramp receiving; head validation is of the combination, not isolated whole-Omega service effect.',
            local_improved=abs(actual-forecast)<abs(actual-old_forecast), full_450_not_tested=True)
        report['forecasts_completed'] = 3
    report['source_pins'] = pins
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_pins','limitations')},ensure_ascii=False))


if __name__ == '__main__':
    main()
