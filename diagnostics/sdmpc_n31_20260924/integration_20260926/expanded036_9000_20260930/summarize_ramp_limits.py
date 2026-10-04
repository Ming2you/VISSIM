"""Attribute saved one-second physical ramp receipts, without forecasting."""
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
EPS = 1e-8


def summarize(rows, resources):
    stats = Counter()
    keys = ('head_service_limit_veh', 'head_service_veh', 'accepted_merge_veh',
            'receiving_budget_veh', 'unused_receiving_budget_veh')
    lanes = {}
    for row in rows:
        assert row['duration_sec'] == 1
        for key in keys:
            stats[key] += row[key]
        for i, lane in enumerate(row.get('lane_receipts', [row])):
            item = lanes.setdefault(str(i), dict(counts=Counter(), start=lane['start']))
            c = item['counts']
            item['end'] = lane['end']
            c['seconds'] += 1
            # No admissions occur inside advance; finish() admits urban arrivals
            # afterwards. Reconstruct the three pre-service operands from end
            # stocks, avoiding a pre-exchange start snapshot where applicable.
            assert lane['requested_arrivals_veh'] == lane['admitted_arrivals_veh'] == 0
            ready = lane['end']['head_ready_veh'] + lane['head_service_veh']
            post = (lane['end']['downstream_travelling_veh'] +
                    lane['end']['merge_ready_veh'] - lane['head_service_veh'])
            space = max(0., lane['nominal_posthead_storage_veh'] - post)
            service = lane['head_service_limit_veh']
            head = lane['head_service_veh']
            merge = lane['accepted_merge_veh']
            eligible, supply = lane['eligible_merge_veh'], lane['receiving_budget_veh']
            head_error = abs(head - min(ready, space, service))
            merge_error = abs(merge - min(eligible, supply))
            assert head_error < EPS and merge_error < EPS, (row['ramp'], i, row['start_sec'])
            c['max_head_formula_error'] = max(c['max_head_formula_error'], head_error)
            c['max_merge_formula_error'] = max(c['max_merge_formula_error'], merge_error)
            if service <= EPS:
                c['head_service_zero_seconds'] += 1
                if ready > EPS:
                    c['head_service_zero_with_ready_seconds'] += 1
            else:
                operands = dict(service=service, ready=ready, posthead_space=space)
                binding = [k for k, v in operands.items() if abs(v-head) < EPS]
                c['head_positive_service_binding_' + '+'.join(binding) + '_seconds'] += 1
            if eligible <= EPS:
                c['merge_empty_seconds'] += 1
            elif eligible > supply + EPS:
                c['merge_receiving_limited_seconds'] += 1
            elif supply > eligible + EPS:
                c['merge_eligible_limited_seconds'] += 1
            else:
                c['merge_tied_seconds'] += 1
            for key in keys:
                c[key] += lane[key]
            c['ready_time_veh_sec'] += lane['end']['head_ready_veh']
            c['posthead_time_veh_sec'] += lane['end']['downstream_travelling_veh'] + lane['end']['merge_ready_veh']
    by_time = {(r['start_sec'], r['kind']): r for r in resources}
    for row in rows:
        t = row['start_sec']
        canonical = by_time[t, 'physical_ramp_merge_canonical_receiving']['available_veh']
        physical = by_time[t, 'physical_ramp_merge_physical_receiving']['available_veh']
        assert abs(physical-row['receiving_budget_veh']) < EPS
        assert physical <= canonical + EPS
        stats['canonical_receiving_budget_veh'] += canonical
        stats['physical_below_canonical_seconds'] += int(physical < canonical-EPS)
    return dict(start_sec=rows[0]['start_sec'], end_sec=rows[-1]['end_sec'],
                commands_green_sec=sorted({r['green_sec'] for r in rows}),
                totals=stats, lanes=lanes)


def main():
    out = dict(scope='Saved model constraint attribution only; no new fit or native test.',
               formula_tolerance_veh=EPS, arms={}, pins={}, new_forecasts=0)
    for arm in ('selected', 'progressive'):
        folder = HERE / ('ramp_limit3600_' + arm)
        for name in ('trace.json.gz', 'summary.json'):
            p = folder / name
            out['pins'][str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
        trace = json.loads(gzip.decompress((folder/'trace.json.gz').read_bytes()))
        summary = json.loads((folder/'summary.json').read_bytes())
        ramps = {}
        for ramp, expected in summary['ramps'].items():
            rows = sorted((r for r in trace['rows'] if r['ramp'] == ramp), key=lambda r:r['start_sec'])
            assert len(rows) == 450
            resources = [r for r in trace['resources'] if r['resource'] == ramp]
            total = summarize(rows, resources)
            for key, value in (('accepted_merge_veh', expected['merges']),
                               ('head_service_veh', expected['head_crossings'])):
                assert abs(total['totals'][key] - value) < EPS
            total['blocks'] = [summarize(rows[start:start+150], resources) for start in range(0,450,150)]
            ramps[ramp] = total
        out['arms'][arm] = dict(ttt=summary['ttt_omega_veh_h'], ramps=ramps)
    out['all8_two_arm_minimum_and_receiving_checks_pass'] = True
    p = HERE / 'ramp_limit_attribution.json'
    p.write_text(json.dumps(out, indent=2, allow_nan=False), encoding='utf-8')
    for arm, data in out['arms'].items():
        r = data['ramps']['RM_C10681']
        print(json.dumps(dict(arm=arm, totals=r['totals'], lanes=r['lanes'],
                              blocks=[dict(start=b['start_sec'], green=b['commands_green_sec'],
                                           totals=b['totals'],lanes=b['lanes']) for b in r['blocks']]), allow_nan=False))


if __name__ == '__main__':
    main()
