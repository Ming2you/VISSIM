"""Verify transferred RM observation records; raw FZP equality is a saved receipt."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
K = ROOT / 'diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920'
RUN = K / 'route_state_native_v1/rm_ramp_s23'


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def portable(name):
    name = name.replace('\\', '/')
    if ':/' in name:
        name = 'diagnostics/' + name.split('/diagnostics/', 1)[1]
    p = (ROOT / name).resolve()
    assert p.is_relative_to(ROOT)
    return p


def main():
    run = load(RUN / 'run/run.json')
    assert run['completed'] and run['terminal_sec'] == run['requested_terminal_sec'] == 3000
    assert run['error'] is None and run['exit_code'] == run['fixed_profile_validation_exit_code'] == 0
    assert run['owned_native_alive'] is False
    validation = load(RUN / 'run/fixed_validation.json')
    assert validation['passed'] and not validation['unrecorded_signal_groups']
    assert validation['native_meter_samples_checked'] == 600
    assert validation['untargeted_snapshot_sha256_before'] == validation['untargeted_snapshot_sha256_after']
    for name, row in validation['ldp_pins'].items():
        p = portable(name)
        assert p.stat().st_size == row['bytes'] and sha(p) == row['sha256']
    result = load(RUN / 'analysis_v2/result.json')
    assert result['passed'] and result['qualified'] is False
    assert result['all_original_nine_columns_exact_rows'] == 11790482
    pair = load(RUN / 'analysis_v2/paired_focus.json')
    pins = 0
    for record in (result, pair):
        for name, digest in record['source_pins'].items():
            assert sha(portable(name)) == digest, name
            pins += 1
    frames = load(RUN / 'analysis_v2/interaction_frames.json')
    assert len(frames['columns']) == 20
    assert len(frames['global_initial_rows']) == result['global_initial_rows'] == 5189
    assert [f['time_s'] for f in frames['frames']] == list(range(2400, 2461))
    assert all(len(r) == 20 for r in frames['global_initial_rows'])
    count = 0
    for f in frames['frames']:
        assert all(len(r) == 20 and float(r[0]) == f['time_s'] for r in f['rows'])
        assert len({r[1] for r in f['rows']}) == len(f['rows'])
        count += len(f['rows'])
    assert count == sum(result['interaction_types'].values())
    row = next(r for r in pair['rows'] if r['vehicle'] == 17532 and r['time_s'] == 2418)
    assert row['none_interaction'] == 'Brake AX' and row['rm_interaction'] == 'Free'
    assert row['none_speed'] == 97.57 and row['rm_speed'] == 109.92
    print(json.dumps(dict(passed=True, qualified=False, source_pins=pins,
        ldp_files=len(validation['ldp_pins']), frames=61, selected_rows=count,
        saved_original9_exact_rows=11790482, raw_fzp_recompared=False,
        new_native_runs=0, new_forecasts=0)))


if __name__ == '__main__':
    main()
