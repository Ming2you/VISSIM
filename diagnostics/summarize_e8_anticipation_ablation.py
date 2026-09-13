"""Summarize the pinned paired experiments without executing a model or FZP scan."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    detail, metrics, sources = [], [], {}
    for start in (1200, 3300):
        path = ROOT/f'diagnostics/e8_anticipation_integrated_{start}.json'
        sources[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        doc = json.loads(path.read_text(encoding='utf-8'))
        observed = {(int(row['sim_sec']), row['model_link'], int(row['segment_index'])): row
                    for row in doc['observed_rows']}
        for name, scenario in doc['scenarios'].items():
            errors = []
            for row in scenario['rows']:
                elapsed = int(row['elapsed_sec'])
                if elapsed % 30:
                    continue
                for link, speeds in row['freeway_speed'].items():
                    for cell, speed in enumerate(speeds):
                        actual = observed[start+elapsed, link, cell]
                        out = {'start_sec': start, 'horizon_sec': elapsed, 'scenario': name,
                               'model_link': link, 'cell': cell, 'observed_count': float(actual['count']),
                               'observed_speed_kmh': float(actual['mean_speed_kph']),
                               'model_speed_kmh': speed,
                               'observed_density': float(actual['density_veh_km_lane']),
                               'model_density': row['freeway_density'][link][cell]}
                        out['speed_absolute_error'] = abs(out['model_speed_kmh']-out['observed_speed_kmh'])
                        out['speed_metric_eligible'] = out['observed_count'] >= 5
                        detail.append(out)
                        if out['speed_metric_eligible']:
                            errors.append(out)
            for group, selected in [('all_freeway_cells', errors),
                                    ('FW_E_cell8', [r for r in errors if r['model_link']=='FW_E' and r['cell']==8])]:
                metrics.append({'start_sec': start, 'scenario': name, 'scope': group,
                                'observations': len(selected),
                                'speed_mae_kmh': sum(r['speed_absolute_error'] for r in selected)/len(selected)})
    path = ROOT/'diagnostics/e8_anticipation_comparison.csv'
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(detail[0]))
        writer.writeheader()
        writer.writerows(detail)
    report = {'method': 'Absolute error at the 15 observed 30-second horizons; speed metrics require observed count >=5. Observations within one seed are correlated. Beyond150s pure-n7 actions may change.',
              'sources_sha256': sources, 'rows': len(detail), 'metrics': metrics,
              'comparison_csv_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    (ROOT/'diagnostics/e8_anticipation_summary.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
