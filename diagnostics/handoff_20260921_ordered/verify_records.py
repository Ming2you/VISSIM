"""Verify saved current-frame observations; no native or forecast execution."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import lateral_body_observation as a


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    result = load(a.OUT / 'result.json')
    frames = {int(t): {int(i): v for i, v in frame.items()} for t, frame in load(a.OUT / 'frames.json').items()}
    for name, digest in result['source_pins'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    geo = a.geometry(a.d.H / 'source_dsd/baseline.inpx')
    assert json.loads(json.dumps(geo)) == result['geometry']
    assert len(frames) == result['source_receipt']['selected_frames'] == 164
    assert sum(map(len, frames.values())) == result['source_receipt']['selected_rows']
    assert result['qualified'] is False and result['new_native_runs'] == result['production_changes'] == 0
    observed = {t: a.observe(frame, geo) for t, frame in frames.items()}
    snapshots = {start: observed[start] for start in a.STARTS}
    assert json.loads(json.dumps(snapshots)) == load(a.OUT / 'snapshots.json')
    overlaps = []
    for summary in result['summaries']:
        start = summary['start']; counts = Counter()
        for t in range(start, start + 30):
            state = observed[t]
            counts['unique_vehicle_seconds'] += len(frames[t])
            counts['reference_occupancy_vehicle_seconds'] += state['reference_lane_occupancies']
            for row in state['projected_overlaps']:
                overlaps.append(dict(t=t, start=start, **row))
                counts['projected_overlap_pairs'] += 1
                counts['reference_sections_separate'] += row['reference_sections_separate']
                counts['either_current_lane_change'] += any(row[k]['lane_change'] != 'None' for k in ('back_state', 'front_state'))
            for row in state['neighbor_comparison']:
                counts['observed_native_targets'] += 1
                counts['old_matches_target'] += row['old_matches_target']
                counts['lateral_matches_target'] += row['lateral_matches_target']
                counts['lateral_changes_candidate'] += row['old_leader'] != row['lateral_leader']
            for row in state['bodies'].values():
                if row['lane_change'] != 'None':
                    counts['active_lane_change_vehicle_seconds'] += 1
                    counts['destination_equals_reported_lane'] += row['destination_lane'] == row['lane']
                    counts['reference_spans_multiple_lanes'] += len(row['reference_occupied_lanes']) > 1
        assert counts == Counter(summary['counts'])
        assert len(summary['active_transitions']) == counts['active_lane_change_vehicle_seconds']
        assert all(r['future_values_are_labels_only'] for r in summary['active_transitions'])
    assert json.loads(json.dumps(overlaps)) == load(a.OUT / 'overlap_pairs.json')
    assert len(overlaps) == 80 and sum(r['reference_sections_separate'] for r in overlaps) == 4
    saved = ET.parse(a.d.H / 'source_dsd/baseline.inpx').getroot().find('simulation').get('simRes')
    report = dict(passed=True, qualified=False, source_pins=len(result['source_pins']),
        frames_recomputed=len(frames), snapshots_exact=4, summaries_exact=4,
        projected_overlaps_exact=80, lateral_reference_separate=4,
        source_xml_simRes=saved, runtime_resolution_or_cause_verified=False,
        full_body_geometry_verified=False, native_started=False, forecasts_recomputed=False)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
