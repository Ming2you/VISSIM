"""Assess the completed, bounded boundary-response experiment from saved data."""
import hashlib
import json
from pathlib import Path

A = Path(__file__).resolve().parent
O = A / 'refine_boundary_fit'
PINS = {}


def read(path):
    raw = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)


def main():
    assert not (O / 'assessment.json').exists()
    done = read(O / 'completion.json')
    selection = read(O / 'selection.json')
    protocol = read(O / 'protocol.json')
    for path, expected in done['source_pins'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected, path
    assert done['forecasts'] <= 16 and done['updates'] == 1
    assert done['native'] == 0 and done['production_edits'] == 0
    baseline, fitted = selection['baseline'], selection['fitted']
    report = dict(
        status='bounded_boundary_update_assessed',
        training_gate_passed=selection['eligible'],
        training_loss_reduction=1 - fitted['data_loss'] / baseline['data_loss'],
        baseline=baseline, fitted=fitted,
        fixed_cell15=protocol['fixed_cell15'],
        original_response=protocol['original_response'],
        new_forecasts=done['forecasts'], reused_forecasts=done['reused_forecasts'],
        updates=done['updates'], new_native=0, production_edits=0,
        candidate_adopted=False, goal_complete=False,
        nonlinear_convergence_claimed=False,
        max_route_balance=done['max_route_balance'],
        max_vsl_balance=done['max_vsl_balance'],
        independent_validation_performed=False,
        next_independent_comparison_warranted=False,
        limits=[
            'One bounded local update is not converged parameter calibration.',
            '2250 is a training/development case; its VSL90 outcomes did not enter fitting.',
            'Scalar conditional feasibility does not establish optimizer NP/NUF or AD validity.',
            'No production adoption, new native experiment or policy improvement claim.',
        ],
    )
    if selection['eligible']:
        comparison = read(O / 'development_response.json')
        actual = read(A / 'approach_flux.json')
        previous = read(A / 'refine15_regime_fit_v3/assessment.json')['development_response']
        hold, selected = comparison['hold'], comparison['selected']
        rows = []
        for j, horizon in enumerate((150, 300, 450)):
            native = next(r for r in actual['rows'] if r['case'] == 'selected' and r['horizon_sec'] == horizon)
            prior = next(r for r in previous['rows'] if r['horizon'] == horizon)
            predicted_flow = selected['throughflow'][j] - hold['throughflow'][j]
            predicted_stock = (
                sum(selected['snapshots'][j + 1]['n']['FW_E'][14:19])
                - sum(hold['snapshots'][j + 1]['n']['FW_E'][14:19])
            )
            rows.append(dict(
                horizon=horizon,
                native_flow_delta=native['outgoing18_detector_delta'],
                native_face_stock=native['outgoing18_first_meter_storage_delta'],
                prior_predicted_flow_delta=prior['predicted_flow_delta'],
                predicted_flow_delta=predicted_flow,
                native_stock_delta=native['native_region_stock_delta'],
                prior_predicted_stock_delta=prior['predicted_stock_delta'],
                predicted_stock_delta=predicted_stock,
            ))
        omega = selected['ttt'] - hold['ttt']
        report['development_response'] = dict(
            rows=rows, predicted_omega_delta=omega,
            prior_predicted_omega_delta=previous['predicted_omega_delta'],
            native_omega_delta=previous['native_omega_delta'],
        )
        end = rows[-1]
        flow_better = abs(end['predicted_flow_delta'] - end['native_flow_delta']) < abs(end['prior_predicted_flow_delta'] - end['native_flow_delta'])
        stock_better = abs(end['predicted_stock_delta'] - end['native_stock_delta']) < abs(end['prior_predicted_stock_delta'] - end['native_stock_delta'])
        report['next_independent_comparison_warranted'] = flow_better and stock_better
    report['source_pins'] = PINS
    (O / 'assessment.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('source_pins', 'original_response')}, indent=2))


if __name__ == '__main__':
    main()
