"""Native support horizon for a causal ordered-neighbor closure.

Future lane/leader changes are scoring labels, never proposed online inputs.
"""
from pathlib import Path
from collections import defaultdict, Counter
import bisect, hashlib, sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import current_gap_response as g
d = g.d


def leaders(frame, shifts):
    lanes = defaultdict(list)
    for vid, row in frame.items():
        lanes[row['lane']].append((shifts[row['link']] + row['pos'], vid))
    result = {}
    for lane in lanes.values():
        lane.sort()
        for (_, vid), (_, ahead) in zip(lane, lane[1:]):
            result[vid] = ahead
    return result


def main():
    out = d.HERE / 'neighbor_persistence_v1'
    out.mkdir(exist_ok=False)
    gp = d.H / 'controller_response_s23_v1/none/geometry.json'
    geometry = d.e.load(gp)
    cells = {r['cell']: r for r in geometry['cells'] if r['road'] == 'FW_E'}
    bounds = [cells[c]['end_m'] for c in sorted(cells)]
    shifts = {r['link']: r['offset_m'] for r in geometry['chains']['FW_E']}
    source = d.HERE / 'route_state_native_v1/none_s23/run_retry1/vissim_eval/baseline_001.fzp'
    frames, receipt = g.read(source, True, 2279)
    neighbors = {t: leaders(frame, shifts) for t, frame in frames.items()}
    records = []
    coverage = Counter()
    for start in (2280, 2400, 2550, 2700):
        for vid, row in frames[start].items():
            cell = min(20, bisect.bisect_right(bounds, shifts[row['link']] + row['pos']))
            if cell < 15:
                continue
            coverage['initial_selected'] += 1
            ahead = neighbors[start].get(vid)
            if ahead is None:
                coverage['initial_no_geometric_leader'] += 1
                continue
            front = frames[start][ahead]
            gap = shifts[front['link']] + front['pos'] - front['length'] - shifts[row['link']] - row['pos']
            if gap < 0:
                coverage['initial_overlapping_lane_projection'] += 1
                continue
            record = dict(start_s=start, vehicle=vid, cell=cell, lane=row['lane'],
                initial_speed=row['v'], initial_gap_m=gap, initial_leader=ahead,
                initial_lane_change_flag=row['lane_change'],
                native_vehicle_target_known=row['target_type'] == 'Vehicle' and row['target'] in frames[start],
                native_target_matches_geometric=row['target_type'] == 'Vehicle' and row['target'] == ahead,
                horizons={})
            for horizon in (1, 5, 10, 20, 30):
                times = range(start + 1, start + horizon + 1)
                visible = all(vid in frames[t] for t in times)
                leader_visible = all(ahead in frames[t] for t in times)
                record['horizons'][str(horizon)] = dict(own_observed=visible, original_leader_observed=leader_visible,
                    own_lane_unchanged=visible and all(frames[t][vid]['lane'] == row['lane'] for t in times),
                    both_lanes_unchanged=visible and leader_visible and all(
                        frames[t][vid]['lane'] == row['lane'] and frames[t][ahead]['lane'] == front['lane'] for t in times),
                    continuous_same_geometric_leader=visible and leader_visible and all(neighbors[t].get(vid) == ahead for t in times))
            records.append(record)
    summaries = {}
    for label, selected in (('all', records), ('initial_speed_below30', [r for r in records if r['initial_speed'] < 30]),
                            ('cell16_at2550', [r for r in records if r['cell'] == 16 and r['start_s'] == 2550])):
        horizons = {}
        for h in (1, 5, 10, 20, 30):
            rows = [r['horizons'][str(h)] for r in selected]
            survivors = [r for r in rows if r['own_observed'] and r['original_leader_observed']]
            stable = sum(r['continuous_same_geometric_leader'] for r in survivors)
            horizons[str(h)] = dict(initial_pairs=len(rows), both_observed=len(survivors),
                continuously_same_leader=stable, both_lanes_unchanged=sum(r['both_lanes_unchanged'] for r in survivors),
                stable_fraction_of_observed_pairs=stable / len(survivors) if survivors else None,
                retained_fraction_of_initial_pairs=stable / len(rows) if rows else None)
        target_rows = [r for r in selected if r['native_vehicle_target_known']]
        summaries[label] = dict(horizons=horizons, current_known_native_targets=len(target_rows),
            current_target_matches_geometric=sum(r['native_target_matches_geometric'] for r in target_rows))
    assert sum(coverage.values()) == coverage['initial_selected'] + coverage['initial_no_geometric_leader'] + coverage['initial_overlapping_lane_projection']
    assert len(records) + coverage['initial_no_geometric_leader'] + coverage['initial_overlapping_lane_projection'] == coverage['initial_selected']
    d.e.save(out / 'result.json', dict(status='NEIGHBOR_RETENTION_OBSERVATION_ONLY', summaries=summaries,
        coverage=dict(coverage), records=records, source_receipt=receipt,
        pins={str(x.relative_to(d.ROOT)): hashlib.sha256(x.read_bytes()).hexdigest() for x in (Path(__file__), Path(g.__file__), gp)},
        limitations=['Single inspected NCseed23, four initial cutoffs; not independent observations or a causal control gain estimate.',
            'Pairs missing later from the selected chain are censored separately, not counted as observed lane changes.',
            'Geometric same-lane leaders need not equal native interaction targets; mismatch alone is not an error in VISSIM.',
            'Future persistence flags may stratify offline errors only. They cannot select an online model with hindsight.'],
        qualified=False, new_native_runs=0, production_changes=0))
    print('SUMMARY', summaries, flush=True)


if __name__ == '__main__':
    main()
