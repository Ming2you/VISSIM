"""Verify saved model evidence only; never launch forecasts or VISSIM."""
from pathlib import Path
import hashlib
import json
import math
import subprocess

ROOT = Path(__file__).resolve().parents[2]
K = ROOT / 'diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920'


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(4*1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def close(a, b):
    assert math.isfinite(a) and math.isfinite(b) and abs(a-b) < 1e-8, (a, b)


def main():
    folders = ('matched_resolution_response_v1', 'matched_lane_response_v1',
               'matched_port_timing_response_v2', 'matched_seed33_boundary_v1')
    records = {name: load(K/name/'result.json') for name in folders}
    pins = forecasts = components = defaults = 0
    for name, result in records.items():
        assert result['qualified'] is False
        for path, digest in result['source_pins'].items():
            target = (ROOT/path).resolve()
            assert target.is_relative_to(ROOT.resolve())
            assert sha(target) == digest, path
            pins += 1
        if name == folders[-1]:
            continue
        assert result['future_inputs'] is False and result['native_runs'] == 0
        for seed, row in result['cases'].items():
            variants = row['predicted'] if name == folders[0] else row
            for variant, arms in variants.items():
                for arm, case in arms.items():
                    label = 'step'+variant if name == folders[0] else variant
                    pred = load(K/name/f'prediction_s{seed}_{label}_{arm}.json')
                    for road in pred['diagnostics']['roads']:
                        assert road['continuity_residual_max_veh'] < 1e-7
                        assert road['negative_density_count'] == 0
                    assert all(abs(r['conservation_residual_veh']) < 1e-7 for r in pred['ports']+pred['ramps'])
                    east = next(r for r in pred['diagnostics']['roads'] if r['road']=='FW_E')
                    for part, field in [('mainline','model_residence_10s_veh_h'),
                                        ('on','ramp_connector_residence_local_1s_veh_h'),
                                        ('off','off_connector_residence_event_veh_h')]:
                        close(case['component'][part], east[field])
                        components += 1
                    if name == folders[0] and variant == '10':
                        prior = (K/'matched_meter_midpoint_s33_v2'/f'prediction_{arm}.json' if seed=='33' else
                                 K/'matched_meter_midpoint_v1/prediction_rm6.json' if arm=='rm6' else
                                 K/'matched_meter2550_v1'/f'prediction_{arm}.json')
                        assert pred == load(prior)
                        defaults += 1
                    if arm != 'rm8':
                        for part in ('mainline','on','off'):
                            close(case['component'][part]-arms['rm8']['component'][part], case['delta_vs_g8'][part])
                        close(sum(case['delta_vs_g8'][p] for p in ('mainline','on','off')), case['delta_vs_g8']['total'])
                    forecasts += 1
    boundary = records[folders[-1]]
    actual = load(K/'matched_meter_midpoint_s33_v2/result.json')
    assert boundary['continuity_steps']==1350 and boundary['identical_initial_frames']
    for arm, prefixes in boundary['deltas'].items():
        for row in prefixes.values():
            close(row['initial_cohort_ttt_veh_h']+row['later_cohort_ttt_veh_h'], row['ttt_veh_h'])
            close(sum(row['boundary_moments'].values()), row['ttt_veh_h'])
        close(prefixes['3000']['ttt_veh_h'], actual['actual_deltas_vs_g8'][arm]['mainline'])
    core = ['evaluation/controllers/physical_lane_groups.py', 'evaluation/controllers/physical_ramp_boundary.py',
            'evaluation/controllers/vissim_stackelberg_adapter.py',
            'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py']
    for name in core:
        old = subprocess.check_output(['git','show','9b0108d:'+name], cwd=ROOT)
        assert hashlib.sha256(old).hexdigest()==sha(ROOT/name), name
    assert forecasts == 48 and defaults == 6
    print(json.dumps(dict(passed=True,qualified=False,source_pins=pins,forecasts_checked=forecasts,
        component_checks=components,default_predictions_exact=defaults,boundary_prefix_checks=6,
        core_unchanged_from='9b0108d',native_started=False,forecasts_recomputed=False),indent=2))


if __name__ == '__main__':
    main()
