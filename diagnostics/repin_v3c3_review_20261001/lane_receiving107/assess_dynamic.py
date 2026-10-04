"""Assess the six already-completed REVIEW107 forecasts; never rerun them."""
import ast
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
D = HERE / 'dynamic'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


summary = read(D / 'summary.json')
assert summary['completed'] == 6
rows = {r['version']: r for r in summary['rows']}
native = {
    key: rows['lanes_release_vsl90']['actual'][key] - rows['lanes_release']['actual'][key]
    for key in ('ttt', 'mainline_ttt', 'ramp_ttt', 'off_ttt', 'end_n', 'exits')
}
responses = {}
for version in ('lanes', 'receiving'):
    responses[version] = {
        key: rows[version + '_release_vsl90']['predicted'][key] - rows[version + '_release']['predicted'][key]
        for key in native
    }
    responses[version]['mainline_response_error'] = abs(responses[version]['mainline_ttt'] - native['mainline_ttt'])
error_reduction = 1 - responses['receiving']['mainline_response_error'] / responses['lanes']['mainline_response_error']
state_ratios = {
    arm: {key: rows['receiving_' + arm]['score'][key]['rmse'] / rows['lanes_' + arm]['score'][key]['rmse']
          for key in ('density', 'speed', 'cell_n', 'flow_vph')}
    for arm in ('release', 'release_vsl90')
}
checks = {
    'default_off_exact_cells_flows_ports_ramps': all(read(D / 'disabled_parity.json').values()),
    'valid_conservation_and_state': all(not r['score']['invalid'] for r in rows.values()),
    'response_error_reduction_at_least20percent': error_reduction >= .20,
    'meaningful_mainline_response_sign': responses['receiving']['mainline_ttt'] * native['mainline_ttt'] > 0,
    'state_rmse_no_more_than10percent_worse': all(r <= 1.1 for values in state_ratios.values() for r in values.values()),
}
assert abs(native['mainline_ttt']) >= .5
blocks = read(HERE / 'blocks.json')
forecasts = {}
for label in ('lanes_release', 'lanes_release_vsl90', 'receiving_release', 'receiving_release_vsl90'):
    path = D / (label + '.json.gz')
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        pred = json.load(f)
    reg = pred['diagnostics']['roads'][0]['joint_lane_region']
    out_by_step = {(round(r['time_s'], 3), r['lane']): r['mainline_in_veh']
                   for r in reg['rows'] if r['cell'] == 20}
    receiving = reg['receiving_rows']
    saturation = sum(out_by_step[(round(r['time_s'] + 1, 3), r['lane'])] >= r['supply_veh'] - 1e-8 for r in receiving)
    predicted_blocks = [sum(r['downstream_crossings'] for r in pred['flows']
                            if r['cell'] == 19 and r['window_start_s'] >= 2670.1 + 150*j - 1e-5
                            and r['window_end_s'] <= 2820.1 + 150*j + 1e-5) for j in range(3)]
    case = '67_release_vsl90' if label.endswith('vsl90') else '67_release'
    actual_blocks = [next(r['actual'] for r in blocks if r['case'] == case and r['duration_sec'] == 150
                          and abs(r['start'] - (2670.1 + 150*j)) < 1e-5) for j in range(3)]
    forecasts[label] = dict(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        predicted_cell19_boundary150_veh=predicted_blocks,
        actual_cell19_boundary150_veh=actual_blocks,
        receiving_records=len(receiving), receiving_budget_saturated_steps=saturation,
        # Same already-inspected witness instant as REVIEW106, not a new fitting sample.
        witness2940_lane1=[r for r in reg['rows'] if abs(r['time_s']-2940.1) < 1e-5
                          and r['cell'] in (19, 20) and r['lane'] == 1],
    )

protocol = read(HERE / 'protocol.json')
for filename, digest in protocol['protected_sha256'].items():
    assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == digest
assert hashlib.sha256(Path(protocol['STOP']['path']).read_bytes()).hexdigest() == protocol['STOP']['sha256']
tree = ast.parse((HERE.parent / 'entry10682/audit.py').read_text(encoding='utf-8'))
functions = {n.name: hashlib.sha256(ast.dump(n, include_attributes=False).encode()).hexdigest()
             for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
for name, digest in protocol['old_helper_ast_sha256'].items():
    assert functions[name] == digest, name

result = dict(
    status='complete_rejected', continuation_gate_pass=all(checks.values()), checks=checks,
    scope='FW_E31 physical cells plus four on-ramp and four off-ramp connectors; NOT whole Omega.',
    comparison='seed67 common2670.1 initial state,450s, RM release, VSL90 minus110; command-conditioned component rollout, no future state observations.',
    native_delta=native, predicted_deltas=responses, response_error_reduction_fraction=error_reduction,
    state_rmse_ratios=state_ratios, forecast_details=forecasts,
    default_current_release=rows['default_before']['predicted'],
    default_current_release_rmse={k: rows['default_before']['score'][k]['rmse'] for k in ('speed', 'density', 'cell_n', 'flow_vph')},
    checks_preserved=dict(core_files=len(protocol['protected_sha256']), old_helper_functions=len(protocol['old_helper_ast_sha256']), STOP=True, hooks_restored=read(D/'restoration.json')),
    qualifications=dict(production_adopted=False, whole_omega_qualified=False, current_goal_complete=False),
    budget=dict(component450_calls=6, fitting=0, new_native=0, FZP_scans=0, elapsed_forecast_seconds=summary['elapsed_sec']),
    interpretation=[
        'Conditional current-state receiving improves discharge estimates but autonomous lane-state evolution does not reproduce the VSL response.',
        'The lane-only baseline is an archived rejected model. Its absolute state and TTT errors exceed the current aggregate model; modest improvement over it is not qualification.',
        'This receiving law uses lane density, not a calibrated stopped-queue onset/drain model. It does not rule out a better queue/lane mechanism.',
        'Current lane exchange rates are constant per unit time and destination-independent. Extra travel time alone is not a demonstrated improvement in mandatory lane-change completion.',
        'No additional coefficient sweep, independent forecast expansion, or production adoption follows the failed gate.',
    ],
)
assert not result['continuation_gate_pass']
write(HERE / 'dynamic_assessment.json', result)
write(HERE / 'dynamic_status.json', dict(status='complete_rejected', completed=6, assessment='dynamic_assessment.json'))
print(json.dumps({k: result[k] for k in ('status', 'native_delta', 'predicted_deltas', 'response_error_reduction_fraction', 'checks')}, ensure_ascii=False, indent=2))
