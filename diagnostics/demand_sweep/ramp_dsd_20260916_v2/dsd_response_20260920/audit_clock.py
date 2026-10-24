"""Align native DESSPEED records without shifting vehicle motion or commands."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from collections import defaultdict
import math
import xml.etree.ElementTree as ET
import argparse

HERE = Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--observations',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    out = HERE / args.output
    out.mkdir(exist_ok=False)
    crossings = e.load(HERE / args.observations / 'crossings.json')
    wanted = defaultdict(list)
    for i, row in enumerate(crossings):
        if row['predicted_desired'] is None:
            continue
        frame = math.ceil(row['time_s'])
        row['crossing_frame_s'] = frame
        row['native_samples'] = {}
        for offset in [-1, 0, 1, 2]:
            wanted[frame + offset, row['vehicle']].append((i, offset))
    path = HERE / 'native_v2/run_retry1/vissim_eval/baseline_001.fzp'
    with path.open('rb') as stream:
        for line in stream:
            if not line[:1].isdigit():
                continue
            parts = line.rstrip(b'\r\n;').split(b';')
            sec = int(float(parts[0]))
            if sec < 2249:
                continue
            for i, offset in wanted.get((sec, int(parts[1])), []):
                crossings[i]['native_samples'][str(offset)] = {
                    'time_s': sec, 'link': int(parts[2]), 'lane': int(parts[3]),
                    'pos_m': float(parts[4]), 'speed_kmh': float(parts[6]),
                    'desired_kmh': float(parts[9])}
    statistics = []
    for changed_only in [False, True]:
        rows = [r for r in crossings if 'native_samples' in r and
                (not changed_only or r['prior_id'] != r['new_id'])]
        for offset in [0, 1, 2]:
            errors = [r['native_samples'][str(offset)]['desired_kmh'] - r['predicted_desired']
                      for r in rows if str(offset) in r['native_samples']]
            failures = [r for r in rows if str(offset) in r['native_samples'] and
                        abs(r['native_samples'][str(offset)]['desired_kmh'] - r['predicted_desired']) > .01]
            statistics.append({'changed_only': changed_only, 'frame_offset': offset,
                'eligible': len(rows), 'recorded': len(errors), 'over_001_kmh': len(failures),
                'max_abs_error_kmh': max(map(abs, errors)),
                'mae_kmh': sum(map(abs, errors)) / len(errors),
                'failures': failures})
    root = ET.parse(HERE / 'native_v2/prepared/network/baseline.inpx').getroot()
    metadata = {'statistics': statistics, 'simulation': root.find('simulation').attrib,
                'warning': 'Native field alignment only. Do not delay physical motion or actuation.'}
    e.save(out / 'summary.json', metadata)
    e.save(out / 'crossings.json', crossings)
    for row in statistics:
        print({k: v for k, v in row.items() if k != 'failures'}, flush=True)


if __name__ == '__main__':
    main()
