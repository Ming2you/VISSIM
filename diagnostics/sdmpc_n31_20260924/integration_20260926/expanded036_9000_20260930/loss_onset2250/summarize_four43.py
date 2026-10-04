"""Check the completed eight fixed-command forecasts against existing native caches."""
import csv
import gzip
import hashlib
import json
from pathlib import Path

L = Path(__file__).resolve().parent
I = L.parent.parent
O = L / 'physical_speed/four43'
A = I / 'seed43_fullplant_20260929'
pins = {}


def read(path):
    data = path.read_bytes()
    pins[str(path)] = hashlib.sha256(data).hexdigest()
    return data


def load(path):
    data = read(path)
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def close(a, b):
    assert abs(a - b) < 1e-7, (a, b)


assert not (O / 'verification.json').exists()
protocol = load(O / 'protocol.json')
for path, expected in protocol['source_pins'].items():
    assert hashlib.sha256(read(Path(path))).hexdigest() == expected, path
proof = load(A / 'analysis_v2/observation_reuse.json')
assert proof['passed'] and proof['precontrol_prefix_exact']
assert proof['native_execution_passed']
legacy_proof = load(Path(proof['reused_native_proof']['path']))
assert pins[proof['reused_native_proof']['path']] == proof['reused_native_proof']['sha256']
assert legacy_proof['passed']
comparison = load(A / 'comparison.json')
decomposition = load(A / 'decomposition.json')
arms = ('nc', 'rm', 'vsl', 'both')
native = {}
for arm in arms:
    rows = list(csv.DictReader(read(A / f'analysis_v2/{arm}_area_stocks_5s.csv').decode('utf-8-sig').splitlines()))
    assert len(rows) == 91
    assert float(rows[0]['time_s']) == 2250.1 and float(rows[-1]['time_s']) == 2700.1
    costs = {}
    for name in ('omega', 'network'):
        values = [float(row[name + '_n']) for row in rows]
        costs[name] = sum((a + b) * 0.5 * 5. / 3600 for a, b in zip(values, values[1:]))
        costs[name + '_left'] = sum(values[:-1]) * 5. / 3600
    close(costs['omega'], comparison['costs'][arm]['native_omega_veh_h'])
    close(costs['network'], comparison['costs'][arm]['native_inserted_network_veh_h'])
    costs['outside'] = costs['network'] - costs['omega']
    native[arm] = dict(cost=costs, components_30s=decomposition['arms'][arm]['native_30s_veh_h'],
        removals=decomposition['arms'][arm]['removal_count'],
        ramps={row['ramp']: row['actual'] for row in comparison['ramps'] if row['arm'] == arm})
    assert len(native[arm]['ramps']) == 8
for arm in arms:
    native[arm]['delta'] = {k: v - native['nc']['cost'][k] for k, v in native[arm]['cost'].items()}
    native[arm]['delta_components_30s'] = {k: v - native['nc']['components_30s'][k]
        for k, v in native[arm]['components_30s'].items()}

models = {}
records = {}
for model in ('before', 'after'):
    folder = I / f'closedloop_recorded2250_lever450_trace10484_physical_speed_{model}_s43_20261001'
    summary = load(folder / 'summary.json')
    assert not summary['native_started'] and not summary['future_observation_inputs']
    assert summary['optimizer_iterations'] == 0 and summary['prediction_conditioned_on_executed_commands']
    assert summary['city_signals_held']
    for path, expected in summary['native_profile_inputs'].items():
        assert hashlib.sha256(read(Path(path))).hexdigest() == expected, path
    result = {}
    for arm in arms:
        key = 'held_actual' if arm == 'nc' else arm
        row = load(folder / f'{key}.json')
        assert row == summary['results'][key]
        assert row['validation']['all_actuator_and_step_constraints_checked']
        assert len(row['ramps']) == 8
        assert max(abs(r['residual']) for r in row['ramps'].values()) < 1e-8
        close(sum(row['cost_by_stock'].values()), row['ttt_omega_veh_h'])
        assert [c['meters']['RM_C10484'] for c in row['commands']] == ([8., 6., 4.] if arm in ('rm', 'both') else [10.] * 3)
        parts = {road: row['cost_by_stock']['freeway:' + road] for road in ('FW_E', 'FW_W')}
        parts['eight_on_ramps'] = sum(v for k, v in row['cost_by_stock'].items() if k.startswith('ramp:'))
        parts['other_Omega'] = row['ttt_omega_veh_h'] - sum(parts.values())
        result[arm] = dict(omega=row['ttt_omega_veh_h'], outside=row['tracked_outside_residence_veh_h'],
            combined=row['ttt_with_tracked_outside_veh_h'], components=parts, ramps=row['ramps'])
        records[model, arm] = row
        assert row['physical_cell_states'][0] == records[model, 'nc']['physical_cell_states'][0]
        trace = load(folder / f'{key}_RM_C10484_trace.json.gz')
        records[model, arm, 'trace'] = trace
    for arm in arms:
        result[arm]['delta'] = {k: result[arm][k] - result['nc'][k] for k in ('omega', 'outside', 'combined')}
        result[arm]['delta_components'] = {k: v - result['nc']['components'][k] for k, v in result[arm]['components'].items()}
    models[model] = result
for arm in arms:
    for key in ('commands',):
        assert records['before', arm][key] == records['after', arm][key]
    assert records['before', arm]['physical_cell_states'][0] == records['after', arm]['physical_cell_states'][0]
    for key in ('initial_stock', 'initial_buffer', 'head_service_by_green'):
        assert records['before', arm, 'trace'][key] == records['after', arm, 'trace'][key]

rank = {'native': sorted(arms, key=lambda a: native[a]['cost']['omega'])}
rank.update({model: sorted(arms, key=lambda a: models[model][a]['omega']) for model in models})
report = dict(status='completed_not_gain_qualified', adopted=False, forecasts=8, session58487='exit0',
    fit=0, new_native=0, fzp_scans=0, live_poll=0, push=0, native=native, models=models, rank=rank,
    checks=dict(native_prefix_and_execution=True, command_input_pins=True, before_after_commands_identical=True,
        initial_freeway_states_identical=True, initial10484_buffer_and_service_identical=True, all8_ramp_mass=True,
        native_5s_trapezoid_reproduced=True, actuator_checks=True, optimizer_run=False, NP_NUF_selection_checked=False),
    limitations=[
        'Native Omega uses existing 5s trapezoid; left-rule sensitivity retained. Model integration starts2250, native2250.1.',
        'Native component costs are existing30s physical snapshots; never subtract these from5s Omega to infer exact urban cost.',
        'Native merge is conservation reconstruction, not a direct merge detector. Endpoint stocks and entry counts can conceal timing changes.',
        'Native outside is inserted-network residence; model tracked outside has different coverage. No full-window uninserted qualification.',
        'Seed43 has previously been inspected; this is independent of this speed-unit change, not a pristine blind calibration holdout.',
        'Fixed executed-command predictions, not optimizer or full9000 gain validation. Combined response still has the wrong Omega sign.',
        'Neither altered native traffic nor future observations are prediction inputs. No coefficient fit or additional candidate search.'
    ], pins=pins)
(O / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(rank=rank, native={a:native[a]['delta'] for a in arms},
    models={m:{a:models[m][a]['delta'] for a in arms} for m in models}), indent=2))
