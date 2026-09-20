"""One intermediate RM contrast through existing model/preparer/runner paths.

Prepare and freeze the forecast before the native run. Analyze only afterwards.
No new adapter, physical model, calibration, or controller selection is added.
"""
from pathlib import Path
from collections import Counter
import argparse
import copy
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import matched_meter_increment as m
from diagnostics.fast_fixed_profile import prepare
from diagnostics.fast_fixed_profile_verify import verify, prefix_digest

K = Path(__file__).resolve().parent
OUT = K / 'matched_meter_midpoint_v1'
e = m.e


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def prepare_case():
    OUT.mkdir(exist_ok=False)
    source = Path(e.load(m.BANK / 'prepared_rm8/prepared.json')['source_network'])
    profile = e.load(m.BANK / 'rm8.json')
    assert profile['network_sha256'] == sha(source) and profile['seed'] == 23
    assert profile['control_start_sec'] == 2400
    profile['terminal_sec'] = 3000
    profile['meter_commands'] = [dict(time_s=t, sc_no=9107, green_sec=g)
                                  for t, g in ((2400, 8), (2550, 6), (2700, 6), (2850, 6))]
    assert not profile['vsl_commands']
    e.save(OUT / 'rm6.json', profile)
    prepare(source, OUT / 'rm6.json', OUT / 'prepared_rm6')
    data = m.prepare_data(m.BANK / 'observations/rm8')
    model = e.load_base_model(data.geometry, m.MODEL / 'config.json')
    parameters = e.load(m.MODEL / 'selected_parameters.json')['parameters']
    ports = e.load(m.MODEL / 'port_profile.json')
    command = lambda t: ({'RM_C10490': 6}, {})
    window = e.window(data, model, m.START, 'history_forecast', ports, command)
    truncated = copy.deepcopy(data)
    truncated.cells = {t: r for t, r in truncated.cells.items() if t <= m.START}
    for field in ('flows', 'boundaries', 'ports', 'headstocks'):
        setattr(truncated, field, {k: v for k, v in getattr(truncated, field).items() if k[0] <= m.START})
    truncated.port_cohorts = {t: r for t, r in truncated.port_cohorts.items() if float(t) <= m.START}
    for field in ('events', 'heads'):
        setattr(truncated, field, [r for r in getattr(truncated, field) if float(r['time_s']) <= m.START])
    assert e.window(truncated, model, m.START, 'history_forecast', ports, command) == window
    e.save(OUT / 'forecast_window.json', window)
    prediction = e.simulate(model, window, parameters)
    assert prediction['local_ramp_audit']['passed']
    e.save(OUT / 'prediction_rm6.json', prediction)
    reference = e.load(K / 'matched_meter2550_v1/result.json')
    component = m.parts(prediction)
    base = reference['predicted']['rm8']['component']
    delta = {k: component[k]-base[k] for k in ('mainline', 'on', 'off')}
    delta['total'] = sum(delta.values())
    e.save(OUT / 'prediction_summary.json', dict(component=component, delta_vs_g8=delta,
        merges={r['ramp']: r['end']['cumulative_merge_veh'] for r in prediction['ramps']
                if r['road'] == 'FW_E' and r['end_sec'] == m.END},
        future_truncation_window_exact=True, qualified=False))
    paths = [Path(__file__), Path(m.__file__), source, m.MODEL / 'config.json',
        m.MODEL / 'selected_parameters.json', m.MODEL / 'port_profile.json',
        OUT / 'prediction_rm6.json', OUT / 'prediction_summary.json', OUT / 'forecast_window.json',
        OUT / 'rm6.json', OUT / 'prepared_rm6/prepared.json', K / 'matched_meter2550_v1/result.json',
        e.CAL / 'canonical_harness.py', e.CAL / 'boundary_factory.py',
        e.ROOT / 'evaluation/controllers/vissim_stackelberg_adapter.py',
        e.ROOT / 'evaluation/controllers/physical_ramp_boundary.py']
    paths += [data.folder / n for n in ('cells_30s.csv', 'flows_30s.csv', 'boundaries_30s.csv',
        'ports_30s.csv', 'port_events.csv', 'port_cohorts_30s.json', 'head_crossings.csv', 'head_stock_1s.csv')]
    e.save(OUT / 'protocol.json', dict(seed=23, start_s=2550, run_end_s=3000,
        candidate_bank={'rm6': {'green': [8, 6, 6, 6], 'vsl': []}},
        scope='FW_E mainline and four on/four off connectors, not Omega or fullGNE',
        reference_run=str(m.BANK / 'run_rm8'),
        strong_reference=str(m.BANK / 'run_rm_ramp'),
        reference_results=str(K / 'matched_meter2550_v1/result.json'),
        source_pins={p.relative_to(e.ROOT).as_posix(): sha(p) for p in paths},
        hypothesis='Distinguish monotonic mainline relief/ramp cost from a nonmonotonic native response to g8,g6,g4 at the same2550state.',
        fixed='Same geometry, demand, seed, urban signals, VSL and prefix; only RM_C10490 green changes.',
        trust='g8->g6 is a permitted2s change;RED/GREEN10s clock;no amber.',
        prediction_frozen_before_native=True, new_forecasts=1, planned_new_native_runs=1,
        qualification=False, information='Current2550state and previous150s only; no new-arm outcomes yet.',
        gates=['Exact whole-network FZP prefix through2550', 'Native LDP and command/readback validation',
               'No unexplained port disappearance;1s component inventories and port continuity',
               'Compare mainline/on/off and accepted merges; do not fit or promote on this one development run.']))
    print(json.dumps(dict(prepared=str(OUT), prediction_delta_vs_g8=delta)), flush=True)


def analyze_case():
    protocol = e.load(OUT / 'protocol.json')
    for name, digest in protocol['source_pins'].items():
        pinned = e.ROOT / name
        if pinned.resolve() == Path(__file__).resolve() and sha(pinned) != digest:
            # Forecast/source were frozen before native; preserve that version.
            pinned = OUT / 'analysis_stock_fix/matched_meter_midpoint_before.txt'
        assert sha(pinned) == digest, name
    run = OUT / 'run_rm6'
    receipt = e.load(run / 'run.json')
    assert receipt['completed'] and receipt['terminal_sec'] == m.END and not receipt['owned_native_alive']
    validation = verify(OUT / 'prepared_rm6', run, m.BANK / 'run_rm8')
    assert validation['passed']
    a = prefix_digest(run / 'vissim_eval/baseline_001.fzp', m.START)
    b = prefix_digest(m.BANK / 'run_rm8/vissim_eval/baseline_001.fzp', m.START)
    assert a == b
    data = m.prepare_data(OUT / 'observations/rm6')
    reference_data = m.prepare_data(m.BANK / 'observations/rm8')
    assert data.cells[m.START] == reference_data.cells[m.START]
    assert data.port_cohorts[str(m.START)] == reference_data.port_cohorts[str(m.START)]
    stocks = {int(r['time_s']): r for r in e.rows(data.folder / 'component_stocks_1s.csv')}
    component = {k: sum(float(stocks[t]['FW_E_'+k]) for t in range(m.START+1, m.END+1))/3600
                 for k in ('mainline', 'on', 'off')}
    negative_source_seconds = sum(int(stocks[t]['FW_E_source_negative']) for t in range(m.START+1, m.END+1))
    # The frozen rm8/strong native references count all rows on mainline links,
    # including just-inserted Pos<0 rows. Match that convention explicitly.
    component['mainline'] += negative_source_seconds/3600
    ports = {}
    for spec in data.definitions.values():
        if spec['road'] != 'FW_E' or spec['kind'] not in ('ramp', 'offramp'):
            continue
        c = str(spec['connector'])
        initial = len(data.port_cohorts[str(m.START)][c]); n = initial
        stock_seconds = arrivals = departures = 0
        for t in range(m.START+1, m.END+1):
            incoming, outgoing = data.arrivals[t, c], data.departures[t, c]
            arrivals += incoming; departures += outgoing; n += incoming-outgoing
            assert n >= 0
            stock_seconds += n
            if t % 30 == 0:
                assert n == len(data.port_cohorts[str(t)][c])
                assert float(data.ports[t, c]['unresolved_absences_veh']) == 0
            if spec['kind'] == 'ramp':
                h = data.headstocks[t, c]
                assert n == int(h['prehead_n']) + int(h['posthead_n'])
        ports[c] = dict(initial=initial, final=n, arrivals=arrivals, departures=departures,
                        ttt_veh_h=stock_seconds/3600, kind=spec['kind'])
    for name, kind in (('on', 'ramp'), ('off', 'offramp')):
        assert abs(component[name]-sum(p['ttt_veh_h'] for p in ports.values() if p['kind']==kind)) < 1e-8
    reference = e.load(K / 'matched_meter2550_v1/result.json')
    actual = {arm: reference['actual'][arm] for arm in ('rm8', 'rm_ramp')}
    actual['rm6'] = dict(component=component, ports=ports)
    prediction = e.load(OUT / 'prediction_summary.json')
    deltas = {}
    for arm in ('rm6', 'rm_ramp'):
        values = {k: actual[arm]['component'][k]-actual['rm8']['component'][k] for k in component}
        deltas[arm] = dict(**values, total=sum(values.values()))
    predicted = dict(reference['predicted']); predicted['rm6'] = prediction
    result = dict(qualified=False, status='COMPLETED_MATCHED_MIDPOINT_DEVELOPMENT_CONTRAST',
        exact_prefix2550=a, native_validation=validation, initial_cells_and_ports_exact=True,
        actual=actual, actual_deltas_vs_g8=deltas, predicted=predicted,
        predicted_rm6_delta_vs_g8=prediction['delta_vs_g8'],
        predicted_strong_delta_vs_g8=reference['deltas']['predicted'], new_native_runs=1,
        stock_definition_correction=dict(negative_source_vehicle_seconds=negative_source_seconds,
            added_mainline_ttt_veh_h=negative_source_seconds/3600,
            reason='Match frozen whole-link native references;original result.json omitted negative-position source rows.',
            supersedes='result.json',native_or_prediction_changes=False),
        limitations=['Development seed23 only;not fresh holdout.', 'FW_E component,not Omega.',
            'Native1s end-frame inventories;model internal10s/mainline and1s ramp/event costs.',
            'No coefficient was fit to this new arm.'])
    e.save(OUT / 'result_v2.json', result)
    print(json.dumps(dict(actual_deltas_vs_g8=deltas,
                         predicted_rm6_delta_vs_g8=prediction['delta_vs_g8'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--analyze', action='store_true')
    args = parser.parse_args()
    analyze_case() if args.analyze else prepare_case()
