"""Read-only verification of saved midpoint results; no native or model run."""
from pathlib import Path
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[2]
K = ROOT / 'diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920'


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def close(a, b):
    assert math.isfinite(a) and math.isfinite(b) and abs(a-b) < 1e-8, (a, b)


def local(p):
    value = p.replace('\\', '/')
    if ':/' in value:
        value = value.split('/control-full-review/', 1)[1]
    path = (ROOT / value).resolve()
    assert path.is_relative_to(ROOT.resolve()), value
    return path


def main():
    s23 = K / 'matched_meter_midpoint_v1'
    s33 = K / 'matched_meter_midpoint_s33_v2'
    a, b = load(s23 / 'result_v2.json'), load(s33 / 'result.json')
    network = load(s23 / 'network_response_v2/result.json')
    snapshot = s23 / 'analysis_stock_fix/matched_meter_midpoint_before.txt'
    pins = 0
    for record in [load(s23 / 'protocol.json'), load(s33 / 'protocol.json'), b, network]:
        for name, digest in record['source_pins'].items():
            p = local(name)
            candidates = [p] + ([snapshot] if p.name == 'matched_meter_midpoint.py' else [])
            assert any(v.is_file() and sha(v) == digest for v in candidates), name
            pins += 1
    ldp_pins = port_checks = 0
    for result in (a, b):
        assert result['qualified'] is False
        assert result['exact_prefix2550']['last_time_s'] == 2550
        for arm, item in result['actual'].items():
            for port in item['ports'].values():
                close(port['initial'] + port['arrivals'] - port['departures'], port['final'])
                port_checks += 1
            for part, ids in [('on', ['10639', '10681', '10490', '10484']),
                              ('off', ['10481', '10483', '10643', '10682'])]:
                close(sum(item['ports'][i]['ttt_veh_h'] for i in ids), item['component'][part])
        for arm, saved in result['actual_deltas_vs_g8'].items():
            delta = {part: result['actual'][arm]['component'][part] - result['actual']['rm8']['component'][part]
                     for part in ('mainline', 'on', 'off')}
            for part, value in delta.items():
                close(value, saved[part])
            close(sum(delta.values()), saved['total'])
        validations = ([result['native_validation']] if 'native_validation' in result
                       else list(result['native_checks'].values()))
        for check in validations:
            assert check['passed'] and check['paired_native_signals_passed']
            assert not check['unrecorded_signal_groups']
            assert check['untargeted_snapshot_sha256_before'] == check['untargeted_snapshot_sha256_after']
            for name, pin in check['ldp_pins'].items():
                path = local(name)
                assert sha(path) == pin['sha256'] and path.stat().st_size == pin['bytes'], name
                ldp_pins += 1
    assert a['stock_definition_correction']['negative_source_vehicle_seconds'] == 50
    close(a['stock_definition_correction']['added_mainline_ttt_veh_h'], 50 / 3600)
    assert network['strict_forecast_window_exact'] and network['continuity_steps'] == 450
    for prefix in network['prefix'].values():
        close(prefix['delta_initial_main'] + prefix['delta_later_main'], prefix['delta_main_ttt'])
        close(sum(prefix['signed_boundary_moments'].values()), prefix['delta_main_ttt'])
    close(network['prefix']['3000']['delta_main_ttt'], a['actual_deltas_vs_g8']['rm6']['mainline'])
    checkpoint = load(s33 / 'checkpoint.json')
    assert checkpoint['passed'] and checkpoint['completed_new_native_runs'] == 3
    assert all(r['completed'] and r['terminal_sec'] == 3000 and not r['owned_native_alive']
               for r in checkpoint['runs'])
    print(json.dumps(dict(passed=True, qualified=False, source_pins=pins, ldp_file_pins=ldp_pins,
                         port_conservation_checks=port_checks, boundary_prefix_checks=3,
                         completed_native_runs=3, verification_scope='saved records and bytes only',
                         native_started=False, forecasts_recomputed=False), indent=2))


if __name__ == '__main__':
    main()
