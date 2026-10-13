"""Assess the six bounded forecasts against existing closed-run observations."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
H = HERE.parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(ROOT), str(H)]
from qualify_native2400 import validate_scope
from evaluation.controllers import obs150_contract as oc

read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out = HERE / 'assessment.json'
    assert not out.exists()
    native = read(H / 'native2400_analysis/summary.json')
    validate_scope(native, read(H / 'native2400_analysis/observed_input_qualification.json'))
    measured = read(H / 'native2400_analysis/urban_service_audit.json')['arms']
    original = read(H / 'native2400_assessment.json')
    pair = {}
    pins = {}
    for variant in ('baseline', 'queue', 'service'):
        folder = H / 'selection2400_discrete' if variant == 'baseline' else HERE / f'forecast2400_{variant}'
        if variant != 'baseline':
            result = read(folder / 'summary.json')
            assert result['status'] == 'complete' and result['forecasts'] == 2
            assert not result['future_observation_inputs'] and result['optimizer_calls'] == result['native_runs'] == 0
            for p, h in result['source_pins'].items():
                assert sha(Path(p)) == h, p
        arms = {arm: read(folder / (arm + '.json')) for arm in ('hold', 'selected')}
        for arm in arms:
            pins[str(folder / (arm + '.json'))] = sha(folder / (arm + '.json'))
        delta = arms['selected']['omega_ttt_veh_h'] - arms['hold']['omega_ttt_veh_h']
        # Reuse the canonical stock-family definition, not a guessed prefix.
        fw_keys = [k for k in arms['hold']['costs_by_stock'] if k.startswith('freeway:')]
        assert fw_keys
        fw_delta = sum(arms['selected']['costs_by_stock'].get(k, 0.) - arms['hold']['costs_by_stock'].get(k, 0.) for k in fw_keys)
        heads = {}
        for arm, r in arms.items():
            if variant == 'baseline':
                head_bins = measured[arm]['SC6_S']
                model_left = [b['by_movement']['SC6_S_SC12_to_W_SC5'] for b in head_bins]
                model_all = [b['predicted_head_veh'] for b in head_bins]
            else:
                head_bins = r['local']['SC6_S']['bins']
                model_left = [b['by_movement']['SC6_S_SC12_to_W_SC5'] for b in head_bins]
                model_all = [sum(b['by_movement'].values()) for b in head_bins]
            actual_left = [b['actual_head_by_lane']['4'] for b in measured[arm]['SC6_S']]
            actual_all = [b['actual_head_veh'] for b in measured[arm]['SC6_S']]
            heads[arm] = dict(actual_left=actual_left, predicted_left=model_left,
                actual_all=actual_all, predicted_all=model_all,
                left_abs_error_sum=sum(abs(a-b) for a,b in zip(actual_left, model_left)),
                all_abs_error_sum=sum(abs(a-b) for a,b in zip(actual_all, model_all)),
                shared_caps_feasible=r['shared_constraints']['feasible'],
                resource_max_exceedance=r['resource_max_exceedance'])
        pair[variant] = dict(delta_omega_veh_h=delta, delta_mainline_veh_h=fw_delta,
            actual_delta_omega_veh_h=original['delta_omega_veh_h']['actual'],
            delta_error_veh_h=delta-original['delta_omega_veh_h']['actual'],
            delta_merge10681=arms['selected']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']-
                             arms['hold']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681'],
            SC6_south_head=heads)
    F = Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
    raw_path = F / 'state_003450.json'
    raw = read(raw_path)
    bundle = oc.load_bundle(raw)
    ds, _ = oc.read_detector_csv(bundle.obs['detector_config']['path'], bundle.obs['detector_config']['sha256'])
    oc.validate_raw(bundle.obs, ds, expected_simres=10)
    boundaries = oc.evaluate_boundaries(bundle.obs, ds, bundle.frame_end, bundle.frame_start, bundle.err_rows)
    native_heads = {str(d.lane): boundaries[d.boundary_ref].cross for d in ds if d.role == 'head' and d.link == 1210018302}
    assert len(native_heads) == 4
    later = dict(at=3300, end=3450, actual_left=native_heads['4'], actual_all=sum(native_heads.values()),
                 actual_head_by_lane=native_heads, variants={})
    pins[str(raw_path)] = sha(raw_path)
    for variant in ('baseline', 'service'):
        folder = HERE / f'forecast3300_{variant}_first150'
        report = read(folder / 'summary.json')
        assert report['status'] == 'complete' and report['forecasts'] == 1
        for p,h in report['source_pins'].items(): assert sha(Path(p)) == h, p
        r = report['results']['applied']
        b = r['local']['SC6_S']['bins'][0]
        left = b['by_movement']['SC6_S_SC12_to_W_SC5']
        total = sum(b['by_movement'].values())
        later['variants'][variant] = dict(predicted_left=left, predicted_all=total,
            left_abs_error=abs(left-later['actual_left']), all_abs_error=abs(total-later['actual_all']),
            initial=b['initial'], final=b['final'], incoming_veh=b['incoming_veh'],
            omega_ttt_veh_h=r['omega_ttt_veh_h'], resource_max_exceedance=r['resource_max_exceedance'])
    report = dict(status='bounded_diagnostic_complete', pair2400=pair, later3300=later, source_pins=pins,
        forecasts=6, new_native=0, new_optimizations=0, parameter_grid=False,
        causal_scope='New native pair has exact common history and matched observed initial/history inputs. Original byte-history failure remains preserved.',
        limitations=['3300 is a separate saved state of seed29, not an independent seed or full450 paired native test.',
                     'Several urban/RM controls change together at2400; this is not isolated10681 causation.',
                     'Past achieved discharge is an observed service support, not proof that future demand/receiving permits that discharge.',
                     'Queue/shared approach geography and signal-head crossing are distinct from corridor exit.'],
        calibration_control_gate_passed=False, runtime_pair_launched=False)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf8')
    print(json.dumps(dict(pair={k:dict(delta=v['delta_omega_veh_h'], error=v['delta_error_veh_h'],
        left={a:r['predicted_left'] for a,r in v['SC6_south_head'].items()}) for k,v in pair.items()}, later=later), indent=2))


if __name__ == '__main__':
    main()
