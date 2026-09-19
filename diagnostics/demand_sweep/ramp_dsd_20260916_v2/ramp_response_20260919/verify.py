"""Compatibility, conservation and causal input checks for ramp-only trials."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.ramp_response_20260919.calibrate_ramps import *
import numpy  # Resolve the project runtime before legacy tests change sys.path.
import unittest

CASES = [
    (13, H/'controller_response_4500_v1/none', H/'response_pairs_v1', 1650),
    (23, H/'controller_response_s23_v1/none', H/'response_late_s23_v1', 2400),
    (33, H/'state_response_20260919/native_s33_v1/observations/none',
     H/'state_response_20260919/native_s33_v1', 2400),
]


def main():
    out = HERE/'verification_v2'
    out.mkdir(exist_ok=False)
    candidate = HERE/'arrival_v1/gap84/model'
    pins = [BASE/'config.json', BASE/'selected_parameters.json',
            candidate/'config.json', candidate/'selected_parameters.json',
            candidate/'port_profile.json', ROOT/e.load(BASE/'config.json')['freeway']['segment_params'],
            e.CAL/'canonical_harness.py', H/'evaluate_response.py',
            ROOT/'evaluation/controllers/physical_ramp_boundary.py',
            ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py',
            ROOT/'evaluation/controllers/freeway_fd.py',
            ROOT/'evaluation/controllers/area_freeway_accounting.py']
    freeze = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}
    write(out/'freeze.json', freeze)
    modules = ['diagnostics.test_freeway_fd',
        'diagnostics.demand_sweep.ramp_dsd_20260916_v2.state_response_20260919.test_state_response',
        'diagnostics.demand_sweep.ramp_dsd_20260916_v2.plant_completion_20260919.test_receiving_node',
        'diagnostics.demand_sweep.ramp_dsd_20260916_v2.spatial_calibration_20260919.test_off_interval',
        'diagnostics.demand_sweep.ramp_dsd_20260916_v2.ramp_response_20260919.test_ramp_profiles']
    with (out/'tests.log').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromNames(modules))
    assert result.wasSuccessful(), 'Unit tests failed; see preserved log'
    print('unit tests', result.testsRun, flush=True)
    before = e.load(BASE/'config.json'); after = e.load(candidate/'config.json')
    expected = copy.deepcopy(before)
    expected['freeway']['physical_ramp_receiving_nodes']['RM_C10484'] = {
        'critical_gap_sec': 2.5, 'followup_sec': 2.5, 'lane_arrival_history_sec': 150}
    assert expected == after
    for filename in ['selected_parameters.json', 'port_profile.json']:
        assert (BASE/filename).read_bytes() == (candidate/filename).read_bytes()
    profile = e.load(BASE/'port_profile.json')
    params = e.load(BASE/'selected_parameters.json')['parameters']
    exact = totals = poison = 0
    for seed, folder, bank, start in CASES:
        data = e.ObservationData(folder)
        model = e.load_base_model(data.geometry, BASE/'config.json')
        wave = e.load_base_model(data.geometry, HERE/'arrival_v1/wave/model/config.json')
        protocol = e.load(bank/'protocol.json')
        for arm in ['none', 'rm_ramp', 'vsl', 'both']:
            seq = protocol['candidate_bank'].get(arm, {'green': [], 'vsl': []})
            def command(t):
                i = int((t-start)//150)
                return ({'RM_C10490': seq['green'][i]} if seq['green'] else {},
                    {d: seq['vsl'][i] for d in protocol.get('dsd_ids', [59,60,61,62])} if seq['vsl'] else {})
            window = e.window(data, model, start, 'history_forecast', profile, command)
            prediction = e.simulate(model, window, params)
            archived = H/'spatial_calibration_20260919/combined_v3'/f'prediction_{seed}_spatial_{arm}.json'
            # JSON archives represent tuple-valued receipts as arrays. Compare
            # the full serialized payload without deleting any field.
            assert json.loads(json.dumps(prediction)) == e.load(archived), ('Default changed', seed, arm)
            exact += 1
        for cutoff in [900, 1650, 2400, 3600]:
            a = e.window(data, model, cutoff, 'history_forecast', profile, lambda t: ({}, {}))
            b = e.window(data, wave, cutoff, 'history_forecast', profile, lambda t: ({}, {}))
            for mid in model.ramps:
                for block in range(3):
                    ix = slice(block*15, (block+1)*15)
                    total_a = sum(s['ramp_arrival_vph'][mid]/360 for s in a['boundary_steps'][ix])
                    total_b = sum(s['ramp_arrival_vph'][mid]/360 for s in b['boundary_steps'][ix])
                    assert abs(total_a-total_b) < 1e-8, (seed, cutoff, mid, block)
                    totals += 1
        cutoff = start
        original = e.window(data, wave, cutoff, 'history_forecast', profile, lambda t: ({}, {}))
        data.cells = {t: rs for t, rs in data.cells.items() if t <= cutoff}
        for attr in ['boundaries', 'flows', 'ports']:
            setattr(data, attr, {k: r for k, r in getattr(data, attr).items() if k[0] <= cutoff})
        data.port_cohorts = {k: r for k, r in data.port_cohorts.items() if int(k) <= cutoff}
        data.port_events = [r for r in data.port_events if float(r['time_s']) <= cutoff]
        assert original == e.window(data, wave, cutoff, 'history_forecast', profile, lambda t: ({}, {}))
        poison += 1
        print('default replay / totals / future removal', seed, flush=True)
    for path, digest in freeze.items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest
    validation = {'unit_tests_passed': result.testsRun, 'default_full_json_exact_checks': exact,
        'unchanged_150s_ramp_request_total_checks': totals, 'future_removed_window_exact_checks': poison,
        'only_config_change_in_gap84_candidate': 'Add10484 receiving node',
        'mainline_parameters_and_transit_profile_byte_exact': True,
        'frozen_files_unchanged': True, 'native_runs_started': 0,
        'control_response_qualified': False}
    write(out/'validation.json', validation)
    print(validation, flush=True)


if __name__ == '__main__':
    main()
