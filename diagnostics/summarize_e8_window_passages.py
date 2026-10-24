"""Compact tables from the recorded bounded-window evidence, no trajectory scan."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KINDS = ('e8_e9', 'diverge_before_1m', 'diverge_after_1m', 'connector_10682_entry',
         'connector_10682_exit', 'connector_10639_exit', 'connector_10681_exit')


def main():
    rows, closures, sources = [], [], {}
    for label in ('NC', 'n7', 'zero', 'offset10'):
        path = ROOT / f'diagnostics/e8_window_passages_{label}.json'
        data = json.loads(path.read_text())
        sources[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        for start, kinds in data['nominal_passages'].items():
            for kind in KINDS:
                record = kinds[kind]
                row = {'run': label, 'start_sec': int(start), 'end_sec': int(start)+150, 'kind': kind,
                       **{k: record[k] for k in ('estimated_count_observed', 'estimated_count_inferred', 'definitely_within_observed',
                                               'possibly_within_observed', 'interval_only_observed', 'ambiguous_crossing_lane_count')}}
                for lane in range(1, 5):
                    row[f'later_endpoint_lane_{lane}'] = record['lane_after_estimated_counts'].get(str(lane), 0)
                rows.append(row)
        for start, window in data['sampled_stock_closure'].items():
            for region, value in window['regions'].items():
                assert value['identity_residual'] == 0
                assert value['flux_residual_after_verified_removals'] == 0
                closures.append({'run': label, 'nominal_start_sec': int(start), 'observed_start_sec': window['observed_window'][0],
                                 'observed_end_sec': window['observed_window'][1], 'region': region,
                                 **{k: value[k] for k in ('count_start', 'count_end', 'delta_count', 'strict_physical_flux_net',
                                                          'strict_flux_residual', 'flux_residual_after_verified_removals')},
                                 'verified_removed_vehicles': len(value['matched_removal_ids']),
                                 'unverified_disappeared_vehicles': len(set(value['disappeared_ids'])-set(value['matched_removal_ids']))})
    for name, values in [('summary', rows), ('closure', closures)]:
        with (ROOT / f'diagnostics/e8_window_passages_{name}.csv').open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(values[0]))
            writer.writeheader()
            writer.writerows(values)
    manifest = {'source_sha256': sources, 'nominal_rows': len(rows), 'closure_rows': len(closures),
                'closure_validation': '48/48 sampled identities and physical flux closures after one deduplicated verified removal pass',
                'note': 'A vehicle can inhabit both mainline control volumes; removal14249 occurs in two closure rows but is one vehicle.'}
    (ROOT / 'diagnostics/e8_window_passages_summary_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
