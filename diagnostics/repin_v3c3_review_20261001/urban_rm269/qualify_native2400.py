"""Qualify the new paired response separately from failed raw-history replay.

The original summary is immutable. The two new arms have byte-exact FZP history.
Check their observed inputs against the old forecast source, without pretending
the older simulator's unobserved microscopic state was reproduced bit for bit.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'native2400_analysis'
SOURCE = Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
RUNS = Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_scope(proof, audit):
    assert proof['original_initial_history_exact'] is False
    assert proof['counterfactual_valid'] is False  # preserve the original failure
    assert proof['paired_prefix_exact'] and proof['common_start_vehicle_records_exact']
    assert all(v['native_execution_passed'] for v in proof['arms'].values())
    assert audit['start_sec'] == 2400 and audit['end_sec'] == 2850
    assert audit['source_summary_sha256'] == sha(OUT / 'summary.json')
    assert audit['matched_current_observations'] and audit['matched_historical_flow_inputs']
    assert audit['new_pair_causal_response_valid']
    assert not audit['original_microscopic_history_bit_exact']
    assert audit['max_prior_position_difference_m'] <= 1e-12
    return 'New paired response and matched observed-input forecast comparison; original bit-exact replay failed'


def main():
    target = OUT / 'observed_input_qualification.json'
    assert not target.exists()
    pins = {}
    def read(path):
        pins[str(path)] = sha(path)
        return json.loads(path.read_text(encoding='utf-8-sig'))
    proof = read(OUT / 'summary.json')
    difference = read(OUT / 'prefix_difference_audit.json')
    assert difference['hashes'] == [proof['original_prefix']['sha256'], proof['prefixes']['hold']['sha256']]
    # No different identity, time, link, lane, speed, desired speed, or route.
    assert set(difference['column_difference_counts']) <= {
        'POS', 'COORDFRONTX', 'COORDFRONTY', 'COORDREARX', 'COORDREARY',
        'DELAYTM', 'ACCELERATION', 'INTERACTSTATE'}
    assert difference['last_difference'] < 2000
    assert difference['maximum_absolute_numeric_difference']['POS'] < .011
    folders = [SOURCE] + [RUNS / arm / f'decisions_sdmpc31_g_2400_{arm}_s29'
                          for arm in ('hold', 'selected')]
    observation_keys = ('detectors', 'detectors_cum', 'rule_crosscheck',
                        'linkeval_volume_veh_h', 'signal_log', 'source_cumulative_vehs')
    checked = []
    max_position_delta = 0.
    for sec in range(150, 2401, 150):
        states = [read(p / f'state_{sec:06d}.json') for p in folders]
        base = states[0]
        for other in states[1:]:
            assert other['freeway_segments'] == base['freeway_segments']
            for key in observation_keys:
                assert other['obs150'][key] == base['obs150'][key], (sec, key)
            left, right = base['vehicle_records'], other['vehicle_records']
            assert left['complete'] and right['complete']
            assert left.keys() == right.keys()
            assert {k: v for k, v in left.items() if k != 'records'} == {
                k: v for k, v in right.items() if k != 'records'}
            assert len(left['records']) == len(right['records'])
            for a, b in zip(left['records'], right['records']):
                if a == b:
                    continue
                assert sec < 2400, 'Current initial state must be exact'
                assert {k: v for k, v in a.items() if k != 'position_m'} == {
                    k: v for k, v in b.items() if k != 'position_m'}
                delta = abs(a['position_m'] - b['position_m'])
                assert delta <= 1e-12, 'Historical physical position differs materially'
                max_position_delta = max(max_position_delta, delta)
        # Actual measurement rows, not just their cumulative counts.
        mer_hashes, removal_rows = [], []
        for folder, state in zip(folders, states):
            obs = state['obs150']
            mer = folder / obs['mer']['chunk']
            assert sha(mer) == obs['mer']['chunk_sha256']
            pins[str(mer)] = sha(mer)
            mer_hashes.append(pins[str(mer)])
            err = folder / obs['err']['chunk']
            assert sha(err) == obs['err']['chunk_sha256']
            pins[str(err)] = sha(err)
            rows = [json.loads(line) for line in err.read_text(encoding='utf8').splitlines()]
            # File offsets/padding/warnings are not vehicle removal events.
            removal_rows.append([{k: v for k, v in row.items()
                if k not in ('byte_offset', 'raw_line_sha256', 'message')}
                for row in rows if row['kind'] == 'lane_change_removal'])
        assert len(set(mer_hashes)) == 1
        assert removal_rows[0] == removal_rows[1] == removal_rows[2]
        checked.append(sec)
    audit = dict(start_sec=2400, end_sec=2850, source_summary_sha256=sha(OUT / 'summary.json'),
        source_pins=pins, checked_observation_times=checked,
        matched_current_observations=True, matched_historical_flow_inputs=True,
        max_prior_position_difference_m=max_position_delta,
        new_pair_causal_response_valid=True, original_microscopic_history_bit_exact=False,
        original_failure_preserved=True,
        limitations=['The two new arms share exact history; the older source run differs in14 FZP rows before2000.',
                    'Observed forecast inputs agree, with one prior position differing by approximately1e-15m.',
                    'This does not prove equality of unobserved simulator internals or independent-seed robustness.',
                    'No native rerun, no model fit, no FZP metric rescan.'])
    audit['scope'] = validate_scope(proof, audit)
    target.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: v for k, v in audit.items() if k != 'source_pins'}, indent=2))


if __name__ == '__main__':
    main()
