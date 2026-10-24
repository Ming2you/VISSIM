"""Reuse the completed67 hold run to assess the already executed SDMPC choice."""
import csv
import hashlib
import json
from pathlib import Path

from evaluation.controllers.control_area_objective import physical_membership_from_ledger
from scripts.measure_control_area import read_fzp_frames, measure_frames, terminal_lengths

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
OLD = I / 'heldout67_freeway_20260930'
RUN = Path('D:/VISSIM_runs/20260930_release2670_s67/hold/run')
PREPARED = RUN.parent.parent / 'prepared_hold'
OUTPUT = HERE / 'held_reuse82'
pins = {}


def read(path):
    data = path.read_bytes()
    pins[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(data)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def table(path, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    assert not OUTPUT.exists(), 'Preserve any earlier attempt/results'
    OUTPUT.mkdir()
    run = read(RUN / 'run.json')
    assert run['completed'] and run['exit_code'] == 0 and run['terminal_sec'] == 3300
    assert not run['owned_native_alive'] and run['error'] is None
    old = read(OLD / 'native_summary.json')
    assert old['common_prefix_exact']
    held = next(r for r in old['rows'] if r['arm'] == 'hold')
    release = next(r for r in old['rows'] if r['arm'] == 'release')
    assert held['prefix'] == release['prefix']
    alignment = read(HERE.parent / 's67_full_observation/recording_start_alignment76.json')
    assert alignment['overlap_exact'] and held['prefix'] == alignment['overlap']
    current = read(HERE.parent / 's67_selected_vsl78/analysis/summary.json')
    assert current['counterfactual_valid'] and current['arms']['selected']['native_execution_passed']
    reference = read(HERE.parent / 's67_full_observation/analysis/summary.json')
    assert current['prefixes']['selected'] == reference['prefixes']['release']
    validation = read(RUN / 'fixed_validation.json')
    assert validation['passed'] and not validation['unrecorded_signal_groups']
    assert validation['untargeted_snapshot_sha256_before'] == validation['untargeted_snapshot_sha256_after']
    profile = read(PREPARED / 'fixed_profile.json')
    pred = read(I / 'closedloop_recorded2700_select_check_s67_service66_selection77_access/summary.json')
    commands = pred['results']['held_actual']['commands']
    ramps = ['RM_C10480', 'RM_C10482', 'RM_C10646', 'RM_C10644',
             'RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484']
    meter_checks = 0
    for sec, command in zip((2700, 2850, 3000), commands):
        for sc, ramp in enumerate(ramps, 9101):
            actual = max((r for r in profile['meter_commands'] if r['sc_no'] == sc and r['time_s'] <= sec), key=lambda r: r['time_s'])
            assert actual['green_sec'] == command['meters'][ramp]
            meter_checks += 1
        assert set(command['vsl'].values()) == {110.}
    assert not profile['vsl_commands'], 'Held baseline must have no VSL changes'
    membership_path = I / 'selected/scenario/control_area_membership_213a5d.json'
    ledger = read(membership_path)
    membership = physical_membership_from_ledger(ledger)
    # The old cached extractor used this original ledger; certify identical membership.
    old_ledger = read(Path(read(OLD / 'omega_membership_proof.json')['ledger']))
    assert physical_membership_from_ledger(old_ledger) == membership
    fzp = RUN / 'vissim_eval/release2670_s67_hold_001.fzp'
    stat = fzp.stat()
    assert stat.st_size == next(r['bytes'] for r in run['native_files'] if r['name'] == fzp.name)
    save(OUTPUT / 'protocol.json', dict(
        scope='Previously completed native hold versus completed selected77; same network/seed/history, current450 forecast reused.',
        old_native_completed=True, new_native=0, new_forecasts=0,
        one_old_held_fzp_scan=True, selected_fzp_rescan=False,
        interval='2700.1..3150s; final4.9s stock hold in both arms. First0.1s after command is not resolved by native samples.',
        native_city_baseline='Unchanged native programs; current selected arm changes cities and10490 jointly.',
        limits=['Original common raw interval5.1..2695.1 exact; new0.1 startup record has no old counterpart.',
                'No old obs150 microscopic2700 snapshot: do not claim a newly verified exact2700 COM state.',
                'Native uninserted delay checkpoints are2670 and3120, not this interval: no matched450 total-cost claim.',
                'This is joint city/RM selection, not isolated freeway/RM/VSL benefit or independent seed.'],
        initial_inputs_sha256=pins, fzp=dict(path=str(fzp), bytes=stat.st_size, mtime_ns=stat.st_mtime_ns)))

    def through_end():
        for frame in read_fzp_frames(fzp):
            if frame.time_sec > 3150:
                break
            yield frame

    metrics, times = measure_frames(through_end(), membership, terminal_lengths(ledger),
        end_sec=3150, simulation_step_sec=.1, include_distance=True)
    save(OUTPUT / 'area_metrics.json', metrics)
    table(OUTPUT / 'area_timeseries.csv', times)
    selected_path = HERE.parent / 's67_selected_vsl78/analysis/selected/area_timeseries.csv'
    pins[str(selected_path)] = hashlib.sha256(selected_path.read_bytes()).hexdigest()
    with selected_path.open(encoding='utf-8-sig') as stream:
        selected = [{k: float(v) if k != 'source' else v for k, v in row.items()} for row in csv.DictReader(stream)]
    # Verify the reused old cached area series before computing new endpoints.
    old_path = OLD / 'observations/hold/area_stocks_5s.csv'
    pins[str(old_path)] = hashlib.sha256(old_path.read_bytes()).hexdigest()
    by_time = {round(r['sim_sec'], 1): r for r in times}
    with old_path.open(encoding='utf-8-sig') as stream:
        cached = list(csv.DictReader(stream))
    for row in cached:
        found = by_time[round(float(row['time_s']), 1)]
        assert found['inside_vehicles'] == int(row['omega_n']) and found['network_vehicles'] == int(row['network_n'])

    def interval(rows):
        begin = next(r for r in rows if round(r['sim_sec'], 1) == 2700.1)
        end = next(r for r in rows if r['sim_sec'] == 3150)
        keys = ['ttt_veh_h_cumulative', 'ttd_observed_plus_terminal_cumulative',
                'sampled_tvd_omega_veh_km_cumulative']
        values = {k: end[k] - begin[k] for k in keys}
        span = [r for r in rows if 2700.1 <= r['sim_sec'] <= 3150]
        values['outside_observed_veh_h'] = sum((a['outside_vehicles'] + b['outside_vehicles']) / 2 *
            (b['sim_sec'] - a['sim_sec']) / 3600 for a, b in zip(span, span[1:]))
        values['remaining_inside'] = end['inside_vehicles']
        values['unresolved_inside_disappearances'] = sum(r['unresolved_inside_disappearances'] for r in span[1:])
        return values

    h, s = interval(times), interval(selected)
    delta = {k: s[k] - h[k] for k in h}
    assert by_time[2700.1]['inside_vehicles'] == next(r['inside_vehicles'] for r in selected if round(r['sim_sec'], 1) == 2700.1)
    result = dict(status='NATIVE_SELECTION_COMPARISON_WITH_EXPLICIT_REUSE_LIMITS',
        hold=h, selected=s, delta_selected_minus_hold=delta,
        predicted450_delta_omega=pred['results']['selected']['ttt_omega_veh_h'] - pred['results']['held_actual']['ttt_omega_veh_h'],
        matched_meter_block_checks=meter_checks, matched_cached_stock_frames=len(cached),
        exact_initial2700_com_state_claimed=False, fresh_seed=False, native450_uninserted_delay_available=False,
        new_native=0, new_forecasts=0, old_held_fzp_scans=1, gain_qualification_complete=False,
        input_sha256=pins, fzp_stat_unchanged=(fzp.stat().st_size, fzp.stat().st_mtime_ns) == (stat.st_size, stat.st_mtime_ns))
    assert result['fzp_stat_unchanged']
    for path, digest in pins.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    save(OUTPUT / 'assessment.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'input_sha256'}))


def verify_first_frame():
    """Compare all recorded columns in the first post-command native sample."""
    assert (OUTPUT / 'assessment.json').exists()
    assert not (OUTPUT / 'first_frame_proof.json').exists()
    paths = [RUN / 'vissim_eval/release2670_s67_hold_001.fzp',
             Path('D:/VISSIM_runs/20261003_s67_selected_vsl78/selected/vissim_eval/sdmpc31_g_2700_selected_s67_001.fzp')]
    evidence = []
    for path in paths:
        stat = path.stat()
        header, lines = None, []
        with path.open('rb') as stream:
            for line in stream:
                if line.startswith(b'$VEHICLE:'):
                    header = line.strip()
                if not line[:1].isdigit():
                    continue
                time = float(line.split(b';', 1)[0])
                if time > 2700.1:
                    break
                if time == 2700.1:
                    lines.append(line.rstrip(b'\r\n'))
        assert header and lines
        assert (path.stat().st_size, path.stat().st_mtime_ns) == (stat.st_size, stat.st_mtime_ns)
        evidence.append(dict(path=str(path), time_sec=2700.1, rows=len(lines),
            header_sha256=hashlib.sha256(header).hexdigest(),
            sorted_rows_sha256=hashlib.sha256(b'\n'.join(sorted(lines)) + b'\n').hexdigest(),
            bytes=stat.st_size, mtime_ns=stat.st_mtime_ns))
    equal = all(evidence[0][k] == evidence[1][k] for k in ('rows', 'header_sha256', 'sorted_rows_sha256'))
    result = dict(status='EXACT' if equal else 'DIFFERENT_POST_COMMAND_SAMPLE', evidence=evidence,
        all_recorded_columns_exact=equal, time_sec=2700.1,
        scope='Native first sample after intervention; do not rename this an observed2700.0 COM state.',
        new_simulations=0, metric_rescans=0, targeted_frame_reads=2)
    save(OUTPUT / 'first_frame_proof.json', result)
    print(json.dumps(result))


def compare_components():
    """Correct only the proven startup-recording difference in cached link costs."""
    from collections import Counter
    assert not (OUTPUT / 'components.json').exists()
    proof = read(OUTPUT / 'first_frame_proof.json')
    assert proof['all_recorded_columns_exact']
    measured = read(OUTPUT / 'assessment.json')
    old_metrics = read(OUTPUT / 'area_metrics.json')
    selected_metrics = read(HERE.parent / 's67_selected_vsl78/analysis/selected/area_metrics.json')
    sources = [Path(row['path']) for row in proof['evidence']]
    old_stream, new_stream = (read_fzp_frames(p) for p in sources)
    old_first, new_first, new_second = next(old_stream), next(new_stream), next(new_stream)
    old_stream.close()
    new_stream.close()
    assert old_first.time_sec == new_second.time_sec == 5.1 and new_first.time_sec == .1
    assert old_first.vehicles == new_second.vehicles
    at5 = Counter(v.link for v in old_first.vehicles.values())
    at0 = Counter(v.link for v in new_first.vehicles.values())
    startup_difference = {link: (2.55 * at0[link] - .05 * at5[link]) / 3600 for link in set(at5) | set(at0)}
    geo = read(I / 'selected/port_gain/geometry.json')
    chains = {r: {str(x['link']) for x in c} for r, c in geo['chains'].items()}
    ramps = {str(x['connector']) for x in geo['boundaries'] if x['kind'] == 'ramp'}
    delta = dict(FW_E=0., FW_W=0., ramps=0., other_omega=0.)
    links = set(old_metrics['physical_link_residence']) | set(selected_metrics['physical_link_residence'])
    bias = 0.
    for link in links:
        old = old_metrics['physical_link_residence'].get(link)
        new = selected_metrics['physical_link_residence'].get(link)
        if not (old or new)['inside']:
            continue
        assert old is None or new is None or old['inside'] == new['inside']
        key = next((r for r, ls in chains.items() if link in ls), 'ramps' if link in ramps else 'other_omega')
        correction = startup_difference.get(link, 0.)
        delta[key] += (new['ttt_veh_h'] if new else 0.) - (old['ttt_veh_h'] if old else 0.) - correction
        bias += correction
    assert abs(sum(delta.values()) - measured['delta_selected_minus_hold']['ttt_veh_h_cumulative']) < 1e-7
    prediction = read(I / 'closedloop_recorded2700_select_check_s67_service66_selection77_access/summary.json')['results']
    parts = {}
    for arm in ('held_actual', 'selected'):
        value = prediction[arm]
        parts[arm] = {r: value['cost_by_stock']['freeway:' + r] for r in chains}
        parts[arm]['ramps'] = sum(v for k, v in value['cost_by_stock'].items() if k.startswith('ramp:'))
        parts[arm]['other_omega'] = value['ttt_omega_veh_h'] - sum(parts[arm].values())
    report = dict(actual_delta_components=delta,
        predicted_delta_components={k: parts['selected'][k] - parts['held_actual'][k] for k in delta},
        startup_delta_omega_veh_h_removed=bias,
        physical_meaning='Joint city andRM choice; attribution by residence location, not a causal per-lever decomposition.',
        native_interval='2700.1..3150 with4.9s tail hold', prediction_interval='2700..3150',
        first_post_command_frame_exact=True, initial2700_COM_state_not_relabelled=True,
        full_fzp_metric_rescans=0, startup_frames_read=3, input_sha256=pins)
    save(OUTPUT / 'components.json', report)
    print(json.dumps({k: v for k, v in report.items() if k != 'input_sha256'}))


if __name__ == '__main__':
    import sys
    if sys.argv[1:] == ['--verify-first-frame']:
        verify_first_frame()
    elif sys.argv[1:] == ['--components']:
        compare_components()
    else:
        assert not sys.argv[1:]
        main()
