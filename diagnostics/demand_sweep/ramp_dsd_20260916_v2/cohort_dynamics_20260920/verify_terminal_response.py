"""Verify the bounded terminal/speed diagnostic and preserve its exact scope."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, H, CASES
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.off_spatial_supply import ReceivingTests
from collections import Counter
import hashlib
import unittest

HERE = Path(__file__).resolve().parent


def port_parts(folder):
    rows = [r for r in e.rows(folder/'ports_30s.csv') if r['road'] == 'FW_E']
    table = {(int(float(r['window_end_s'])), r['connector']): r for r in rows}
    events = Counter((int(float(r['time_s'])), r['connector'], r['kind'])
                     for r in e.rows(folder/'port_events.csv') if 2400 < float(r['time_s']) <= 2850)
    result = Counter()
    for c in {c for t, c in table}:
        opening = float(table[2400, c]['end_n_veh'])
        arrivals = sum(n for (t, port, kind), n in events.items() if port == c and kind == 'arrival')
        departures = sum(n for (t, port, kind), n in events.items() if port == c and kind == 'departure')
        assert all(kind in ('arrival', 'departure') for (t, port, kind) in events if port == c)
        assert opening + arrivals - departures == float(table[2850, c]['end_n_veh'])
        cost = opening * 450/3600 + sum((2850-t+1)*n/3600*(1 if kind == 'arrival' else -1)
                                      for (t, port, kind), n in events.items() if port == c)
        result['on' if table[2850, c]['kind'] == 'ramp' else 'off'] += cost
    return dict(result)


def main():
    tests = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReceivingTests))
    assert tests.wasSuccessful()
    inputs = [Path(__file__), HERE/'speed_oracle.py', HERE/'rm_transport_audit.py']
    pins = e.load(HERE/'off_space_response_v1/result.json')['pins']
    pins.update(e.load(HERE/'rm_transport_audit_v1/result.json')['pins'])
    for name, pin in pins.items():
        assert hashlib.sha256((e.ROOT/name).read_bytes()).hexdigest() == pin, name
    native = e.load(HERE/'vehicle_lengths_native_v1/analysis/result.json')
    assert native['completed'] and native['native_validation_passed']
    assert native['all_original_ten_columns_exact_rows'] == 11788963
    run = e.load(HERE/'vehicle_lengths_native_v1/run_retry/run.json')
    assert run['completed'] and run['terminal_sec'] == 3000 and not run['owned_native_alive']
    default_exact = 0
    comparisons = []
    for seed, treatment in [(23, 'rm_ramp'), (33, 'rm_ramp'), (23, 'vsl'), (33, 'spread_only')]:
        if treatment == 'rm_ramp':
            capped = HERE/'rm_speed_default_replay_v1'
            opened = HERE/'rm_speed_open_v1'
        else:
            capped = H/'vsl_speed_capped_20260920_v1'
            opened = H/'vsl_speed_open_20260920_v1'
        arms = {}
        changed_cells = set()
        for arm in ['none', treatment]:
            pair = {}
            for label, folder in [('capped', capped), ('open', opened)]:
                path = folder/f'prediction_s{seed}_all_{arm}.json'
                inputs.append(path)
                pred = e.load(path)
                pair[label] = pred
                for r in pred['diagnostics']['roads']:
                    assert r['continuity_residual_max_veh'] < 1e-7
                    assert r['negative_density_count'] == 0 and r['jam_density_exceedance_count'] == 0
                for r in pred['ports']:
                    assert abs(r['conservation_residual_veh']) < 1e-7
            for key in ['cells', 'flows']:
                assert [r for r in pair['capped'][key] if r['road'] == 'FW_W'] == [r for r in pair['open'][key] if r['road'] == 'FW_W']
            # Under the identical future velocity input, changed N/flow must be
            # identified by cell rather than explained with a total-cost match.
            for a, b in zip(pair['capped']['lane_groups']['FW_E'], pair['open']['lane_groups']['FW_E']):
                assert (a['time_s'], a['cell'], a['group']) == (b['time_s'], b['cell'], b['group'])
                assert a['v_kmh'] == b['v_kmh']
                if a != b:
                    changed_cells.add(a['cell'])
            for key in ['ramps', 'ports']:
                assert pair['capped'][key] == pair['open'][key]
            if treatment == 'rm_ramp':
                old = HERE/f'rm_speed_oracle_v1/prediction_s{seed}_all_{arm}.json'
                inputs.append(old)
                assert pair['capped'] == e.load(old)
                default_exact += 1
            arms[arm] = {label: parts(pred) for label, pred in pair.items()}
        deltas = {mode: {k: arms[treatment][mode][k]-arms['none'][mode][k]
                         for k in ('mainline', 'on', 'off')} for mode in ('capped', 'open')}
        for value in deltas.values():
            value['total'] = sum(value.values())
        _, nc, bank, start = next(r for r in CASES if r[0] == seed)
        obs = bank/'observations'/treatment
        ports_nc = port_parts(nc)
        inputs.extend([nc/'port_events.csv', nc/'ports_30s.csv'])
        if treatment == 'spread_only':
            # This trial saved exact native1s component sums, not a full
            # port-event extraction. Reuse its on/off sums only; its whole-link
            # mainline sum includes negative source coordinates and is not used.
            source = H/'state_exchange_20260920/dispersion_seed33_analysis_v1/summary.json'
            measured = e.load(source)['results']
            for k in ('on', 'off'):
                assert abs(ports_nc[k]-measured['none']['parts'][k]) < 1e-8
            ports_control = {k: measured['spread_only']['parts'][k] for k in ('on', 'off')}
            inputs.append(source)
        else:
            ports_control = port_parts(obs)
            inputs.extend([obs/'port_events.csv', obs/'ports_30s.csv'])
        balance = HERE/('rm_boundary_cohorts_v1' if treatment == 'rm_ramp' else 'component_boundary_cohorts_v2')
        total = e.load(balance/'summary.json')[str(seed)][treatment]['delta_ttt']
        actual = {k: ports_control[k]-ports_nc[k] for k in ('on', 'off')}
        actual['mainline'] = total-sum(actual.values())
        actual['total'] = total
        comparisons.append(dict(seed=seed, treatment=treatment, actual_1s=actual,
                                future_speed_diagnostic=deltas, changed_cells=sorted(changed_cells)))
        inputs.append(balance/'summary.json')
    result = dict(passed=True, receiving_tests=tests.testsRun,
        previous_pins_checked=len(pins), rm_default_whole_predictions_exact=default_exact,
        comparisons=comparisons, core_source_unchanged=True,
        qualification='NOT_QUALIFIED: observed future speeds in both variants; no causal gain improvement proven',
        scope='FW_E component; new terminal tests use existing recordings only. Historical native length observation repeat retained.',
        pins={str(p.relative_to(e.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    e.save(HERE/'terminal_response_validation_v1.json', result)
    for r in comparisons:
        print(r, flush=True)
    print('PASS', default_exact, 'exact default replays', flush=True)


if __name__ == '__main__':
    main()
