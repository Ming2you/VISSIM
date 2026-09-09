"""Qualify current-route COM semantics; sampled rows are not route flow rates."""
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'diagnostics/vehicle_route_com_probe_20260910_01'


def main():
    rows = list(csv.DictReader((SOURCE/'routes.csv').open(encoding='utf-8')))
    manifest = json.loads((SOURCE/'manifest.json').read_text(encoding='utf-8-sig'))
    if not manifest['passed'] or manifest['source_changes']:
        raise AssertionError('COM probe was not complete under fixed source inputs')
    groups = {}
    for name, select in {
        '56_before_1129': lambda r: r['lane'].split('-')[0] == '56' and float(r['pos_m']) < 253.172200720,
        '56_after_1129': lambda r: r['lane'].split('-')[0] == '56' and float(r['pos_m']) >= 253.172200720,
        '57': lambda r: r['lane'].split('-')[0] == '57',
        '10617': lambda r: r['lane'].split('-')[0] == '10617',
        '10621': lambda r: r['lane'].split('-')[0] == '10621',
        '10634': lambda r: r['lane'].split('-')[0] == '10634',
    }.items():
        selected = [r for r in rows if select(r)]
        counts = Counter((r['route_decision_no'], r['route_no'], r['route_decision_type']) for r in selected)
        groups[name] = {'record_count': len(selected), 'unique_vehicle_count': len({r['veh_no'] for r in selected}),
                        'current_routes': [{'decision': d, 'route': r, 'type': t, 'records': n}
                                           for (d, r, t), n in sorted(counts.items())]}
    for name, allowed in [('56_after_1129', {'1', '2', '3'}), ('57', {'2', '3'}), ('10617', {'2', '3'})]:
        if not groups[name]['record_count'] or any(r['decision'] != '1129' or r['route'] not in allowed
                                                or r['type'] != 'STATIC' for r in groups[name]['current_routes']):
            raise AssertionError('Current route did not identify the past-decision cohort: ' + name)
    by_id = defaultdict(list)
    for row in rows:
        by_id[row['veh_no']].append(row)
    crossings = []
    for vehicle, trace in by_id.items():
        for before, after in zip(trace, trace[1:]):
            if (before['lane'].split('-')[0] == after['lane'].split('-')[0] == '56'
                    and float(after['sim_sec'])-float(before['sim_sec']) == 1
                    and float(before['pos_m']) < 253.172200720 <= float(after['pos_m'])):
                crossings.append({'veh_no': int(vehicle), 'before': before, 'after': after})
    missing = [r for r in rows if r['route_decision_no'] == '<EMPTY>']
    if any(r['route_no'] != '<EMPTY>' or r['route_decision_type'] != '<EMPTY>' for r in missing):
        raise AssertionError('Partially missing current-route identity in native probe')
    report = {'scope': 'Read-only COM attribute qualification under original native network demand and signals; not a controlled trial.',
              'simulated_seconds': 1050, 'elapsed_wall_sec': manifest['elapsed_sec'],
              'complete': True, 'raw_record_count': len(rows), 'groups': groups,
              'one_second_decision_crossings': len(crossings), 'crossing_examples': crossings[:4],
              'missing_current_route': {'records': len(missing), 'variant_types': sorted({r['decision_vartype'] for r in missing}),
                                        'value': 'Empty for all three attributes; serialized as three nulls by the optional collector'},
              'present_variant_types': sorted({(r['decision_vartype'], r['route_vartype'], r['type_vartype']) for r in rows if r['route_decision_no'] != '<EMPTY>'}),
              'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (SOURCE/'routes.csv', SOURCE/'manifest.json', SOURCE/'stdout.txt', SOURCE/'stderr.txt', Path(__file__))},
              'limitations': ['Record counts include repeated observations of the same vehicles; they are not native route choice shares.',
                              'No zero or negative no-route sentinel was observed. Empty is not evidence of an eligible future choice.',
                              'The physical branch proves bypass membership on10621 after its current static route ends.',
                              'This probe qualified COM attributes. The added production JSON collector is separately checked with fake COM and must be observed in the next live controller trial.']}
    (ROOT/'diagnostics/vehicle_route_com_qualification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('raw_record_count', 'one_second_decision_crossings', 'missing_current_route')}, indent=2))


if __name__ == '__main__':
    main()
