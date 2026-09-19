"""Read-only offline handoff check: hashes, unit tests, and one450s forecast."""
from pathlib import Path
import hashlib
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
import numpy  # Import before older tests alter dependency search paths.


def main():
    for row in e.load(ROOT/'diagnostics/handoff_20260919/direct_files.json')['files']:
        p = ROOT/row['path']
        assert p.stat().st_size == row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest() == row['sha256'], row['path']
    h = ROOT/'diagnostics/demand_sweep/ramp_dsd_20260916_v2'
    final = h/'merge_drain_response_20260919'
    for rel, digest in e.load(final/'verification_v1/freeze.json').items():
        assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() == digest, rel
    prefix = 'diagnostics.demand_sweep.ramp_dsd_20260916_v2.'
    names = ['diagnostics.test_freeway_fd', prefix+'state_response_20260919.test_state_response',
             prefix+'plant_completion_20260919.test_receiving_node', prefix+'spatial_calibration_20260919.test_off_interval',
             prefix+'ramp_response_20260919.test_ramp_profiles', prefix+'merge_drain_response_20260919.test_transit',
             'diagnostics.handoff_20260916.test_restore_evidence']
    result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    assert result.wasSuccessful()
    cfg = final/'decisions_v1/internal_cost'
    data = e.ObservationData(h/'state_response_20260919/native_s33_v1/observations/none')
    model = e.load_base_model(data.geometry, cfg/'config.json')
    profile = e.load(cfg/'port_profile.json')
    params = e.load(cfg/'selected_parameters.json')['parameters']
    window = e.window(data, model, 2400, 'history_forecast', profile, lambda t: ({}, {}))
    pred = e.simulate(model, window, params)
    recorded = e.load(final/'causal_v1/prediction_33_baseline_none.json')
    for field in ['cells', 'flows', 'ramps', 'ports']:
        assert json.loads(json.dumps(pred[field])) == recorded[field], field
    parts = e.component(data, model, 2400, pred)
    expected = e.load(final/'causal_v1/results.json')['33']['baseline']['arms']['none']['predicted_internal']
    for key, field in [('mainline', 'freeway_ttt_veh_h'), ('on', 'ramp_ttt_veh_h'), ('off', 'off_ttt_veh_h')]:
        assert abs(parts[field]-sum(row[key] for row in expected.values())) < 1e-10, field
    print(json.dumps({'unit_tests_passed': result.testsRun, 'source_pins_match': True,
                      'forecast': 'seed33,2400-2850s,internal_cost,no_control',
                      'full_physical_records_exact': True, 'component': parts,
                      'archived_directional_residence': expected, 'native_runs_started': 0}, ensure_ascii=False))


if __name__ == '__main__':
    main()
