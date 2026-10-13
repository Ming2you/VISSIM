"""Read already-computed resource receipts; do not rerun the predictor."""
import ctypes
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    out = HERE / 'native2400_predicted_ramp_components.json'
    assert not out.exists(), 'Preserve completed extraction'
    read = lambda p: json.loads(p.read_bytes())
    points = read(HERE / 'native2400_predicted_stocks.json')
    prior = read(HERE / 'selection2400_discrete/summary.json')
    report = dict(source_pins={}, arms={}, forecasts=0, native_reads=0,
                  scope='Frozen discrete prediction: separate head, merge and connector arrival receipts')
    for arm in ('hold', 'selected'):
        path = HERE / 'selection2400_discrete' / (arm + '_response.json.gz')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == points['source_pins'][str(path)]
        report['source_pins'][str(path)] = digest
        with gzip.open(path, 'rt', encoding='utf8') as stream:
            response = json.load(stream)
        ramps = prior['results'][arm]['predicted_merge']['accepted_vehicles_by_ramp']
        rows = {r: [dict(start_sec=t, end_sec=t+150, head_by_lane={}, merge=0., arrival=0.,
                        head_receipts=0, merge_receipts=0) for t in (2400, 2550, 2700)] for r in ramps}
        for resource in response['resource_allocations']:
            kind = resource['kind']
            if kind not in ('physical_ramp_head_service', 'physical_ramp_merge_physical_receiving'):
                continue
            name = resource['resource']
            ramp, lane = name.rsplit(':', 1) if kind == 'physical_ramp_head_service' else (name, None)
            if ramp not in rows:
                continue
            block = int((resource['start_sec'] - 2400) // 150)
            assert 0 <= block < 3
            row = rows[ramp][block]
            if lane is None:
                row['merge'] += resource['accepted_total_veh']
                row['merge_receipts'] += 1
            else:
                lane = str(int(lane) + 1)
                row['head_by_lane'][lane] = row['head_by_lane'].get(lane, 0.) + resource['accepted_total_veh']
                row['head_receipts'] += 1
        for transfer in response['transfers']:
            target = transfer.get('target') or ''
            if not target.startswith('ramp:') or target[5:] not in rows:
                continue
            block = int((transfer['start_sec'] - 2400) // 150)
            assert 0 <= block < 3
            rows[target[5:]][block]['arrival'] += transfer['vehicles']
        stocks = {p['time_sec']: p['model_stock_veh'] for p in points['arms'][arm]}
        for ramp, windows in rows.items():
            assert abs(sum(w['merge'] for w in windows) - ramps[ramp]) < 1e-7
            for row in windows:
                row['initial_stock'] = stocks[row['start_sec']]['ramp:' + ramp]
                row['final_stock'] = stocks[row['end_sec']]['ramp:' + ramp]
                row['head'] = sum(row['head_by_lane'].values())
                row['posthead_stock_change'] = row['head'] - row['merge']
                assert row['merge_receipts'] == 150 and row['head_receipts'] == 150 * len(row['head_by_lane'])
                balance = row['initial_stock'] + row['arrival'] - row['merge'] - row['final_stock']
                assert abs(balance) < 1e-7, (arm, ramp, row['end_sec'], balance)
                row['conservation_residual'] = balance
        report['arms'][arm] = rows
        del response
    out.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf8')
    print(json.dumps({a: [{k:r[k] for k in ('end_sec','head','merge','arrival','posthead_stock_change')}
                         for r in rows['RM_C10681']] for a, rows in report['arms'].items()}, indent=2))


if __name__ == '__main__':
    main()
