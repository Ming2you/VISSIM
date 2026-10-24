"""Qualify completed gate296 without rerunning any traffic prediction."""
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parent
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert not (HERE / 'qualification.json').exists()
    summary = read(HERE / 'forecast2400/summary.json')
    assessment = read(HERE / 'assessment.json')
    reference = read(A / 'sourcepath292/assessment.json')
    pins = summary['source_pins']
    assert all(sha(p) == h for p, h in pins.items())
    assert summary['status'] == 'complete' and summary['forecasts'] == 2
    assert summary['initial_state_error'] == 0
    p1 = {'movement:SC6_S_SC12_to_N_SC103', 'movement:SC6_S_SC12_to_E_SC104'}
    checks = {}
    sources = [Path(__file__), HERE / 'assessment.json',
               HERE / 'forecast2400/summary.json', A / 'sourcepath292/assessment.json']
    for arm in ('hold', 'city'):
        gp = HERE / 'forecast2400' / (arm + '.gate.json')
        rp = HERE / 'forecast2400' / (arm + '.response.json.gz')
        sources += [gp, rp]
        g = read(gp)
        r = json.loads(gzip.decompress(rp.read_bytes()))
        rows = g['history']
        result = summary['results'][arm]
        assert len(rows) == 45 and [x['sec'] for x in rows] == list(range(2400, 2850, 10))
        assert r['model_constraint_coverage']['complete']
        assert r['conditional_model_feasibility_witness']
        assert not r['physical_native_fidelity_certificate']
        assert result['writer_three_blocks'] and result['shared_constraints']['feasible']
        assert result['conservation_states'] == 4
        assert result['resource_max_exceedance'] < 1e-7
        pending = sum(x['vehicles'] for x in g['pending'])
        ready = sum(g['ready'].values())
        balance = g['received'] - g['discharged'] - pending - ready
        red_release = sum(x['discharged'] for x in rows if x['green_sec'] == 0)
        assert abs(balance) < 1e-7 and red_release == 0
        assert all(x['discharged'] <= min(x['ready_before'], x['budget']) + 1e-7 for x in rows)
        assert all(x['tracked_gate_stock'] <= x['parent_occupied'] + 1e-7 for x in rows)
        inbound = [t for t in r['transfers'] if t['source'] == 'storage:SC12_to_SC6'
                   and t['target'] in p1 and 2590 <= t['start_sec'] < 2610]
        checks[arm] = dict(
            received=g['received'], discharged=g['discharged'], terminal_pending=pending,
            terminal_ready=ready, mass_residual=balance, red_release=red_release,
            binding_positive_green_times=[x['sec'] for x in rows if x['positive_green_capacity_binding']],
            largest_full_green_ready=max(x['ready_before'] for x in rows if x['green_sec'] == 10),
            full_green10_capacity=5600 * 10 / 3600,
            model_p1_point_arrivals_2590_2610=sum(t['vehicles'] for t in inbound),
            implemented_constraint_coverage=True, physical_native_fidelity=False,
            three_block_writer=True, shared_np_nuf_feasible=True,
            resource_max_exceedance=result['resource_max_exceedance'],
            endpoint_wall_sec=result['wall_sec'])
    candidate = assessment['candidate_city_minus_hold_veh_h']
    prior = reference['candidate_city_minus_hold_veh_h']
    native = assessment['native_city_minus_hold_veh_h']
    report = dict(
        status='complete_diagnostic_not_adopted', current_initial_state_unchanged=True,
        source_pins_verified=len(pins), gate_checks=checks,
        whole_omega=dict(native_city_minus_hold=native, sourcepath292_city_minus_hold=prior,
                         gate296_city_minus_hold=candidate, incremental_change=candidate-prior,
                         incremental_error_reduction_percent=100*(1-abs(candidate-native)/abs(prior-native)),
                         direction_matched=candidate*native>0, unit='veh*h'),
        head_response=assessment['head_response_delta'],
        native_2550_2700_p1_counts={arm: assessment['heads'][arm]['SC6_S']['actual_by150'][1]
                                  for arm in ('hold', 'city')},
        model_2550_2700_p1_counts={arm: assessment['heads'][arm]['SC6_S']['candidate_by150'][1]
                                 for arm in ('hold', 'city')},
        interpretation=[
            'SC10 green/red grouping changes head timing, but the whole-Omega city-effect direction stays wrong.',
            '5600veh/h is provisional, not calibrated saturation. It binds only at two 2-second partial-green intervals per arm; that is not proof of rate-insensitivity.',
            'New accepted traffic only: current initial reservations and all accepted-receiving constraints remain unchanged.',
            'Point queue arrivals are not the native terminal-road inlet boundary; do not subtract their counts as the same flow.',
            'No independent internal SC10 lane storage/FIFO model; parent occupied stock bounds are preserved.',
            'Executed review.py reused a geometry-only wording. This is a gate-clock/service diagnostic, not geometry-only. Executed source is preserved.'
        ],
        decision='Preserve candidate; do not adopt or run coefficient grids, another native run, AD/full optimizer, or unused-state qualification without a stronger mechanism and gain-direction improvement.',
        budget_used=dict(fixed450_forecasts=2, optimizer_iterations=0, native_runs=0,
                         fzp_reads=0, fits=0, production_changes=0),
        goal_complete=False, source_pins={str(p): sha(p) for p in sources})
    with (HERE / 'qualification.json').open('x', encoding='utf8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({k: report[k] for k in ('status', 'whole_omega', 'gate_checks')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
