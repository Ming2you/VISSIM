"""Small post-run summary of the frozen executed-command replays."""
import csv
import json
import math
import pathlib
import re
from collections import defaultdict

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
RUNS = {'none': 'rule100_none3000_s13_v1', 'vsl': 'rule100_vsl3000_s13_v2',
        'rm': 'rule100_rm3000_s13_v2', 'both': 'rule100_both3000_s13_v3'}


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def summarize():
    totals, details = [], {}
    for arm, run in RUNS.items():
        area = {int(float(r['sim_sec'])): r for r in rows(BASE / arm / 'native/area_timeseries.csv')}
        for start in (900, 1650, 1800, 2400):
            folder = BASE / arm / f'replay{start}'
            summary = load(folder / 'summary.json')
            assert summary['completed'] and summary['endpoint_calls'] == 1
            comparison = rows(folder / 'comparison_150s.csv')
            model_windows = rows(folder / 'model_windows_150s.csv')
            native_ttt = math.fsum(float(r['native_TTT_veh_h']) for r in comparison)
            native_ttd = math.fsum(float(r['native_TTD_veh']) for r in comparison)
            native_start = int(area[start]['inside_vehicles'])
            item = {'arm': arm, 'start_sec': start, 'end_sec': start + 450,
                    'initial_native_omega_n': native_start, 'initial_model_omega_n': summary['initial_omega_n'],
                    'initial_stock_bias_veh': summary['initial_omega_n'] - native_start,
                    'native_TTT_veh_h': native_ttt, 'model_TTT_veh_h': summary['TTT_veh_h'],
                    'TTT_bias_veh_h': summary['TTT_veh_h'] - native_ttt,
                    'TTT_bias_percent': 100 * (summary['TTT_veh_h'] / native_ttt - 1),
                    'native_TTD_veh': native_ttd, 'model_TTD_veh': summary['TTD_veh'],
                    'TTD_bias_veh': summary['TTD_veh'] - native_ttd,
                    'native_end_omega_n': int(area[start + 450]['inside_vehicles']),
                    'model_end_omega_n': float(comparison[-1]['model_end_omega_n']),
                    'forecast_sha256': summary['forecast_sha256']}
            totals.append(item)
            ramp_totals = defaultdict(lambda: defaultdict(float))
            for r in rows(folder / 'comparison_ramps_150s.csv'):
                dest = ramp_totals[r['ramp']]
                for field in ('native_explicit_merges_veh', 'model_accepted_merges_veh', 'native_ambiguous_parent_jumps'):
                    dest[field] += float(r[field])
                dest['error_veh'] = dest['model_accepted_merges_veh'] - dest['native_explicit_merges_veh']
            speed_errors = defaultdict(list)
            for r in rows(folder / 'comparison_cells_30s.csv'):
                if int(r['native_n']) > 0 and r['native_speed_kph']:
                    speed_errors[r['direction'] + r['cell']].append(
                        (float(r['predicted_speed_kph']), float(r['native_speed_kph'])))
            cells = {}
            for cell, values in speed_errors.items():
                cells[cell] = {'samples': len(values),
                               'mean_bias_kph': math.fsum(p - o for p, o in values) / len(values),
                               'mae_kph': math.fsum(abs(p - o) for p, o in values) / len(values),
                               'rmse_kph': math.sqrt(math.fsum((p - o) ** 2 for p, o in values) / len(values)),
                               'mean_model_kph': math.fsum(p for p, _ in values) / len(values),
                               'mean_native_kph': math.fsum(o for _, o in values) / len(values)}
            parity = []
            for frame in summary['applied_controls_by150']:
                sec = int(frame['start_sec'])
                action_path = ROOT / 'evaluation/runs' / run / ('decisions_' + run) / f'action_{sec:06d}.json'
                actual = load(action_path)
                for field in ('vsl', 'ramp_metering', 'green_times', 'offsets'):
                    assert frame['control'][field] == actual[field], (arm, sec, field)
                writer = rows(action_path.with_suffix('.csv'))
                for record in writer:
                    if record['kind'] == 'vsl':
                        direction, cell = re.fullmatch(r'RW_FW_([EW])_S(\d+)', record['id']).groups()
                        assert float(record['speed_kph']) == frame['control']['vsl'][f'FW_{direction}__seg{cell}']
                    if record['kind'] == 'ramp_meter':
                        assert float(record['green_sec']) == actual['diagnostics']['diagnostic_physical_meter_green_sec'][record['id']]
                parity.append({'start_sec': sec, 'model_vs_action_json_exact': True, 'vsl_csv_exact': True,
                               'meter_green_sec': actual['diagnostics']['diagnostic_physical_meter_green_sec']})
            details[f'{arm}_{start}'] = {'ramps': dict(ramp_totals), 'cells': cells, 'command_parity': parity,
                                       'model_TTT_groups': {field: math.fsum(float(r[field]) for r in model_windows)
                                           for field in ('mainline_ttt_veh_h', 'onramp_connector_and_pending_ttt_veh_h',
                                                         'urban_and_other_ttt_veh_h')}}
    assert len(totals) == 16
    common = [r for r in totals if r['start_sec'] == 900]
    assert len({r['forecast_sha256'] for r in common}) == 1
    anchor = next(r for r in common if r['arm'] == 'none')
    for r in common:
        r['same_initial_delta_native_TTT_vs_none'] = r['native_TTT_veh_h'] - anchor['native_TTT_veh_h']
        r['same_initial_delta_model_TTT_vs_none'] = r['model_TTT_veh_h'] - anchor['model_TTT_veh_h']
    meter_pairs = {}
    for base_arm, controlled_arm in (('none', 'rm'), ('vsl', 'both')):
        pair = [next(r for r in totals if r['arm'] == arm and r['start_sec'] == 1650)
                for arm in (base_arm, controlled_arm)]
        assert pair[0]['forecast_sha256'] == pair[1]['forecast_sha256']
        meter_pairs[controlled_arm + '_minus_' + base_arm] = {
            'delta_native_TTT_veh_h': pair[1]['native_TTT_veh_h'] - pair[0]['native_TTT_veh_h'],
            'delta_model_TTT_veh_h': pair[1]['model_TTT_veh_h'] - pair[0]['model_TTT_veh_h'],
            'delta_native_TTD_veh': pair[1]['native_TTD_veh'] - pair[0]['native_TTD_veh'],
            'delta_model_TTD_veh': pair[1]['model_TTD_veh'] - pair[0]['model_TTD_veh'],
            'physical_model_csv_byte_equal': {name:
                (BASE / base_arm / 'replay1650' / name).read_bytes() ==
                (BASE / controlled_arm / 'replay1650' / name).read_bytes()
                for name in ('model_windows_150s.csv', 'model_cells_30s.csv',
                             'model_ramps_10s.csv', 'model_transfers.csv')}}
    vsl_delta = {}
    for cell, nc in details['none_900']['cells'].items():
        controlled = details['vsl_900']['cells'][cell]
        vsl_delta[cell] = {
            'delta_model_mean_speed_kph': controlled['mean_model_kph'] - nc['mean_model_kph'],
            'delta_native_mean_speed_kph': controlled['mean_native_kph'] - nc['mean_native_kph']}
    output = {'windows': totals, 'details': details,
              'first_meter_1650_pairs': meter_pairs,
              'common900_vsl_speed_response': vsl_delta,
              'scope': 'Post-hoc actual command schedule, one450s endpoint per window. Common900 uses identical NC initial state and config and forecast; first-meter1650 uses same-history initial states within NC/RM and VSL/both pairs. Other late windows use each arm own state. Native cell speeds are same-time30s snapshot means, not interval averages. Initial stock bias is separate from subsequent dynamics and forecast error. No future observations enter the plant.'}
    (BASE / 'plant_replay_summary.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    fields = list(totals[0])
    with (BASE / 'plant_replay_windows.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(totals)
    print(json.dumps(totals, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    summarize()
