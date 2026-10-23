"""Assess only the two predeclared CDF-cap forecasts, if actually complete."""
import gzip
import hashlib
import json
from pathlib import Path

A = Path(__file__).resolve().parent
H = A.parent
O = A / 'cdf_cap_candidate'
PINS = {}


def read(path):
    raw = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def main():
    assert not (O / 'assessment.json').exists()
    done = read(O / 'completion.json')
    assert done['status'] == 'complete_pending_assessment' and done['new_forecasts'] == 2
    for p, digest in done['source_pins'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest() == digest, p
    base = {r['name']: r for r in read(H / 'matched_off2250_v3/summary.json')['results']}
    baseline_response = read(H / 'matched_off2250_v3/hold_response.json.gz')
    cut = read(A / 'approach_flux.json')
    horizons = read(H / 'native_analysis_repaired_20261016/horizon_summary.json')
    reports = {}
    for case in ('single90', 'selected'):
        result = read(O / f'{case}_result.json')
        response = read(O / f'{case}_response.json.gz')
        rows = []
        for index, horizon in enumerate((150, 300, 450), 1):
            end = 2250 + horizon
            flow = {key: sum(r['accepted_total_veh'] for r in response['resource_allocations']
                         if r['kind'] == kind and r['resource'] == resource and r['end_sec'] <= end + 1e-8)
                    for key, kind, resource in [('incoming13', 'freeway_mainline_sending', 'FW_E:cell:13'),
                        ('outgoing18', 'freeway_mainline_sending', 'FW_E:cell:18'),
                        ('off10481', 'freeway_offramp_sending', '10481')]}
            stock = sum(result['snapshots'][index]['n']['FW_E'][14:19])
            residual = stock - sum(result['snapshots'][0]['n']['FW_E'][14:19]) - flow['incoming13'] + flow['outgoing18'] + flow['off10481']
            assert abs(residual) < 1e-7
            old = next(r for r in cut['rows'] if r['case'] == case and r['horizon_sec'] == horizon)
            omega = []
            for source in (baseline_response, response):
                assert not any(r['start_sec'] < end - 1e-8 and r['end_sec'] > end + 1e-8 for r in source['residence'])
                omega.append(sum(sum(r['inside_veh'].values()) * r['dt_h'] for r in source['residence'] if r['end_sec'] <= end + 1e-8))
            rows.append(dict(horizon=horizon,
                native_flow_delta=old['outgoing18_boundary_delta_if_no_loss_in_first_meter'],
                native_detector_delta=old['outgoing18_detector_delta'],
                native_first_meter_storage_delta=old['outgoing18_first_meter_storage_delta'],
                original_flow_delta=old['outgoing18_model_delta'],
                candidate_flow_delta=flow['outgoing18'] - cut['cases']['hold']['model_cumulative'][str(horizon)]['outgoing18'],
                native_stock_delta=old['native_region_stock_delta'],
                original_stock_delta=sum(base[case]['snapshots'][index]['n']['FW_E'][14:19]) - sum(base['hold']['snapshots'][index]['n']['FW_E'][14:19]),
                candidate_stock_delta=stock-sum(base['hold']['snapshots'][index]['n']['FW_E'][14:19]),
                native_omega_delta=horizons['comparisons'][case][str(horizon)]['native_delta_omega_veh_h'],
                original_omega_delta=horizons['comparisons'][case][str(horizon)]['model_delta_omega_veh_h'],
                candidate_omega_delta=omega[1] - omega[0],
                model_region_balance_residual=residual))
        final = rows[-1]
        reports[case] = dict(rows=rows, seconds=result['seconds'], original_seconds=base[case]['seconds'],
            physical_constraints=result['physical_constraints'],
            regional_model_cost_deltas={k: result['costs'][k]-v for k,v in base['hold']['costs'].items()},
            outside_model_cost_deltas={k: result['outside_costs'][k]-v for k,v in base['hold']['outside_costs'].items()},
            final_flow_error_improved=abs(final['candidate_flow_delta']-final['native_flow_delta']) < abs(final['original_flow_delta']-final['native_flow_delta']),
            final_stock_error_improved=abs(final['candidate_stock_delta']-final['native_stock_delta']) < abs(final['original_stock_delta']-final['native_stock_delta']),
            final_flow_direction=final['candidate_flow_delta'] * final['native_flow_delta'] > 0,
            final_stock_direction=final['candidate_stock_delta'] * final['native_stock_delta'] > 0)
    eligible = all(all(report[k] for k in ('final_flow_error_improved', 'final_stock_error_improved', 'final_flow_direction', 'final_stock_direction')) for report in reports.values())
    output = dict(status='requires_independent_validation' if eligible else 'not_sufficient_response_correction',
        reports=reports, candidate_adopted=False, goal_complete=False, new_forecasts=2,
        new_native=0, fits=0, production_edits=0, source_pins=PINS,
        limitations=['No convergence, independent-case, scalar/AD, NP/NUF optimization or policy-gain claim.',
            'Native five-second TTT quadrature and first-meter no-loss qualification retained.',
            'No tiny Omega benefit-sign gate; report local flow/stock magnitudes and full external costs together.',
            'Model cost breakdown is not relabelled as native regional cost; completed native component_comparison.json remains authoritative.'])
    (O / 'assessment.json').write_text(json.dumps(output, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf8')
    print(json.dumps({'status': output['status'], 'cases': {k: v['rows'] for k,v in reports.items()}}, indent=2))


if __name__ == '__main__':
    main()
