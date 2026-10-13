"""Compare the bounded SC6 initialization change without refitting anything."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
H = HERE.parent
PINS = {}


def read(path):
    data = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--include3300', action='store_true')
    args = ap.parse_args()
    out = HERE / ('validation.json' if args.include3300 else 'pair_validation.json')
    assert not out.exists()
    plan = read(HERE / 'plan_at_execution.json')
    for p, digest in plan['source_pins'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest() == digest, p
    evidence = read(HERE / 'assessment.json')
    net = read(HERE / 'forecast2400/network.json')
    before = {arm: read(H / 'sc101_recombined/forecast2400' / (arm+'.json')) for arm in ('hold','selected')}
    after = {arm: read(HERE / 'forecast2400' / (arm+'.json')) for arm in before}
    rows = []
    for arm in before:
        for phase in ('p1','p2'):
            actual = [sum(row['crossings'] for row in w['head']['rows']
                          if (int(row['lane']) in (1,2,3)) == (phase=='p1'))
                      for w in evidence['arms'][arm]['windows']]
            counts = lambda r: [sum(n for m,n in b['by_movement'].items()
                if net['urban_movements'][m]['phase']=='SC6_'+phase)
                for b in r['local']['SC6_S']['bins']]
            b, c = counts(before[arm]), counts(after[arm])
            rows.append(dict(arm=arm, phase=phase, native=actual, baseline=b, candidate=c,
                baseline_abs_error=sum(abs(x-y) for x,y in zip(actual,b)),
                candidate_abs_error=sum(abs(x-y) for x,y in zip(actual,c))))
        a = after[arm]
        assert a['writer_validated'] and a['conservation_states']==4
        assert a['resource_max_exceedance'] <= 1e-7
    head_before = sum(r['baseline_abs_error'] for r in rows)
    head_after = sum(r['candidate_abs_error'] for r in rows)
    delta = lambda d: d['selected']['omega_ttt_veh_h']-d['hold']['omega_ttt_veh_h']
    actual_delta = read(H / 'sc101_recombined/assessment.json')['delta_omega_veh_h']['actual']
    feasible = all(a['shared_constraints']['feasible'] for a in after.values())
    proceed = feasible and head_after < .9*head_before and abs(delta(after)-actual_delta) <= abs(delta(before)-actual_delta)
    initial = read(HERE/'forecast2400/state.json')
    source = 'SC12_to_SC6'
    tagged = initial['gate_initial_route_tags'][source]
    tagged_by_phase = {phase: sum(n for row in tagged.values() for m,n in row.items()
                        if net['urban_movements'][m]['phase']=='SC6_'+phase) for phase in ('p1','p2')}
    report = dict(status='fixed_pair_evaluated', source_pins=PINS, head_comparisons=rows,
        total_head_abs_error=dict(baseline=head_before,candidate=head_after),
        delta_omega_veh_h=dict(native=actual_delta, baseline=delta(before), candidate=delta(after)),
        initial_tagged_by_phase=tagged_by_phase, feasible=feasible,
        conditional3300_allowed=proceed, new_fitted_coefficients=0, predictions=2,
        full_sdmpc=0, new_native=0, production_changed=False,
        calibration_control_gate_passed=False, runtime_comparison_launched=False,
        limitations=['Both controls change urban signals and multiple RM; not an isolated RM native effect.',
                     'Only current terminal-road cohorts have lane-aware tags. Upstream unknown route intent is still approximate.',
                     'This is fixed-control prediction validation, not a complete SDMPC timing benchmark.'])
    if args.include3300:
        assert proceed
        trial = read(HERE/'forecast3300/applied.json')
        base = read(H/'sc101_recombined/forecast3300/applied.json')
        native = read(H/'service_ceiling/comparison.json')
        fresh = []
        for phase in ('p1','p2'):
            actual = next(r['actual'] for r in native['head_comparisons3300'] if r['group']=='SC6_S' and r['phase']==phase)
            get = lambda s: sum(n for m,n in s['local']['SC6_S']['bins'][0]['by_movement'].items()
                               if net['urban_movements'][m]['phase']=='SC6_'+phase)
            fresh.append(dict(phase=phase,native=actual,baseline=get(base),candidate=get(trial)))
        assert trial['writer_validated'] and trial['conservation_states']==2 and trial['resource_max_exceedance'] <= 1e-7
        report.update(fresh3300=fresh, predictions=3)
        report['limitations'].append('3300 is separate same-seed development data, not an independent held-out seed.')
    PINS[str(Path(__file__))] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_pins','limitations')},ensure_ascii=False))


if __name__ == '__main__':
    main()
