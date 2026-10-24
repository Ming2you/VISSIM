"""Reconcile saved common-cohort paths and separate entry/remaining travel times."""
from pathlib import Path
from collections import Counter
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = HERE / 'marginal_cohort_paths_v1'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    result = load(OUT / 'result.json')
    for name, digest in result['source_pins'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    vehicles = load(OUT / 'vehicles.json')
    assert len(vehicles) == len({r['vehicle'] for r in vehicles}) == 676
    prior = {a: load(HERE / 'marginal_boundary_timing_v1' / (a + '.json')) for a in ('rm8', 'rm_ramp')}
    exits = {}
    for arm, data in prior.items():
        records = [r for r in data['events'] if r['sign'] == -1 and r['initial_vehicle']]
        assert len(records) == len({r['vehicle'] for r in records}), 'Repeated exits need separate treatment'
        exits[arm] = {r['vehicle']: r for r in records}
        assert {r['vehicle'] for r in vehicles} == set(data['initial_ids'])
        assert sum(r['arms'][arm]['residence_s'] for r in vehicles) == sum(data['initial_cohort_residence_s'].values())
        grid = load(OUT / (arm + '_cell_lane_1s.json'))
        for t in range(2551, 3001):
            observed = next(r for r in data['trace'] if r['time_s'] == t)
            assert sum(r['n'] for r in grid if r['time_s'] == t) == observed['n']
            assert sum(r['initial_n'] for r in grid if r['time_s'] == t) == observed['initial_cohort_n']
        for row in vehicles:
            a = row['arms'][arm]
            assert sum(a['by_cell'].values()) == a['residence_s']
    same, changed, censored = [], [], []
    for row in vehicles:
        a, b = [exits[arm].get(row['vehicle']) for arm in ('rm8', 'rm_ramp')]
        if a and b:
            if a['kind'] != b['kind']:
                changed.append(row['vehicle'])
            else:
                assert b['time_s'] - a['time_s'] == row['delta_residence_s']
                same.append(dict(vehicle=row['vehicle'], kind=a['kind'], delta_s=row['delta_residence_s']))
        else:
            censored.append(dict(vehicle=row['vehicle'], delta_s=row['delta_residence_s']))
    terminal_ids = {r['vehicle'] for r in same if r['kind'] == 'terminal_inferred'}
    decompositions = []
    for cell in range(13, 21):
        rows = []
        for row in vehicles:
            if row['vehicle'] not in terminal_ids:
                continue
            a, b = [row['arms'][arm] for arm in ('rm8', 'rm_ramp')]
            if str(cell) not in a['cell_first_time'] or str(cell) not in b['cell_first_time']:
                continue
            entry = b['cell_first_time'][str(cell)] - a['cell_first_time'][str(cell)]
            rows.append((entry, row['delta_residence_s'] - entry, row['delta_residence_s']))
        sums = [sum(r[i] for r in rows) for i in range(3)]
        assert sums[0] + sums[1] == sums[2]
        decompositions.append(dict(entry_cell=cell, same_terminal_vehicles=len(rows),
            summed_entry_time_delta_s=sums[0], summed_remaining_travel_delta_s=sums[1],
            summed_terminal_exit_delta_s=sums[2]))
    by_cell = Counter()
    for row in vehicles:
        for arm, sign in (('rm8', -1), ('rm_ramp', 1)):
            by_cell.update({c: sign * n for c, n in row['arms'][arm]['by_cell'].items()})
    expected = sum(r['delta_residence_s'] for r in vehicles)
    assert sum(by_cell.values()) == expected == 1553
    assert not changed
    files = [Path(__file__), OUT / 'result.json', OUT / 'vehicles.json']
    report = dict(passed=True, qualified=False, previous_goal_turn='progress: verified and pushed completed evidence',
        native_runs=0, model_changes=0, initial_vehicles=676, stock_checks=900,
        per_vehicle_cell_sum_checks=1352, same_recorded_exit_vehicles=len(same), changed_recorded_exit_vehicles=changed,
        censored_vehicles=censored, same_exit_residence_delta_s=sum(r['delta_s'] for r in same),
        delta_residence_s=expected, delta_residence_s_by_cell=dict(by_cell),
        delta_stopped_s=sum(r['arms']['rm_ramp']['stopped_s'] - r['arms']['rm8']['stopped_s'] for r in vehicles),
        delta_slow30_s=sum(r['arms']['rm_ramp']['slow30_s'] - r['arms']['rm8']['slow30_s'] for r in vehicles),
        changed_residence_counts=dict(Counter('positive' if r['delta_residence_s'] > 0 else
            'negative' if r['delta_residence_s'] < 0 else 'same' for r in vehicles)),
        terminal_travel_decomposition=decompositions,
        scope='Common initial mainline vehicles; retrospective. Entry times are observed, not forecast inputs.',
        source_pins={p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    path = OUT / 'validation.json'
    with path.open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k not in ('source_pins', 'censored_vehicles')}))


if __name__ == '__main__':
    main()
