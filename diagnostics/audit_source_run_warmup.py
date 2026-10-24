"""Compare completed pre-control observations without reading future trajectories."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from diagnostics.audit_area_live_actuation import read_csv_prefix

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', default='codex_area_sources_beta0_s13_20260910')
    parser.add_argument('--reference', default='codex_area_observed_nc_s13_20260910')
    parser.add_argument('--output', default='diagnostics/source_run_warmup_equivalence.json')
    args = parser.parse_args()
    runs = [(ROOT/'evaluation/runs'/name).resolve() for name in (args.run, args.reference)]
    if any(p.parent != (ROOT/'evaluation/runs').resolve() for p in runs):
        raise ValueError('Run must be a direct child of evaluation/runs')
    output = (ROOT/args.output).resolve()
    if not output.is_relative_to((ROOT/'diagnostics').resolve()) or output.exists():
        raise ValueError('A new output under diagnostics is required')
    report = {'target': args.run, 'reference': args.reference, 'sources': {}, 'tables': {}}
    ignored = {'controller_mode', 'controller_status', 'decision_wall_sec'}
    for prefix in ('state', 'bottleneck_links', 'bottleneck_segments'):
        pairs = []
        for run in runs:
            path = run/f'{prefix}_{run.name}.csv'
            rows, evidence = read_csv_prefix(path, 870)
            rows = [{k: v for k, v in row.items() if k not in ignored}
                    for row in rows if float(row['sim_sec']) <= 870]
            report['sources'][str(path.relative_to(ROOT))] = evidence
            pairs.append(rows)
        report['tables'][prefix] = {
            'equal': pairs[0] == pairs[1], 'target_rows': len(pairs[0]), 'reference_rows': len(pairs[1]),
            'last_target_sec': max((float(r['sim_sec']) for r in pairs[0]), default=None),
            'first_differences': [i for i, (a, b) in enumerate(zip(*pairs)) if a != b][:10],
        }
    snapshots = []
    for run in runs:
        path = run/('decisions_'+run.name)/'state_000900.json'
        report['sources'][str(path.relative_to(ROOT))] = {'sha256': sha(path)}
        snapshots.append(json.loads(path.read_text(encoding='utf-8-sig')))
    selected = ['sim_sec', 'total_vehicles', 'urban_vehicles', 'freeway_vehicles', 'ramp_vehicles',
                'boundary_vehicles', 'other_vehicles', 'mean_speed_kph', 'freeway_mean_speed_kph',
                'stopped_vehicles', 'demand', 'ramp_counts', 'vehicle_records', 'vehicle_routes', 'freeway_segments']
    report['snapshot900'] = {key: snapshots[0][key] == snapshots[1][key] for key in selected}
    report['local_observation_equal'] = snapshots[0]['local_observation'] == snapshots[1]['local_observation']
    report['record_count'] = snapshots[0]['vehicle_records']['record_count']
    report['valid'] = (all(row['equal'] and row['last_target_sec'] == 870 for row in report['tables'].values())
                       and all(report['snapshot900'].values()))
    report['scope'] = 'Exact recorded physical CSV observations through870 and full snapshot900; not every between-snapshot trajectory or equality of estimator history.'
    report['ignored_csv_fields'] = sorted(ignored)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('valid', 'tables', 'snapshot900', 'local_observation_equal', 'record_count')}, ensure_ascii=False))
    return 0 if report['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
