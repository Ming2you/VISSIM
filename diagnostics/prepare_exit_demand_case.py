"""Single reviewed destination change: source1098 / static route1130:3."""
import argparse
import csv
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from diagnostics.fast_nc_prepare import BASE, demand_rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--alpha', required=True)
    p.add_argument('--name', required=True)
    a = p.parse_args()
    alpha = Fraction(a.alpha)
    assert 0 < alpha <= 1 and a.name.isalnum()
    raw = BASE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317'
    before = b'<vehicleRouteStatic destLink="123" destPos="295.92350735286266" formula="" name="" no="3" relFlow="2 0:4">'
    after = before.replace(b'2 0:4', ('2 0:' + format(float(4*alpha), '.15g')).encode('ascii'))
    assert raw.count(before) == 1
    changed = raw.replace(before, after)
    old = ET.fromstring(raw)
    new = ET.fromstring(changed)
    route = new.find('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no="1130"]/vehRoutSta/vehicleRouteStatic[@no="3"]')
    assert route is not None
    route.set('relFlow', '2 0:4')
    assert ET.tostring(old) == ET.tostring(new), 'Only the selected demand weight may change'
    network = BASE.with_name('exit_' + a.name + '.inpx')
    out = ROOT / 'diagnostics/demand_sweep' / a.name
    assert not network.exists() and not out.exists()
    out.mkdir(parents=True)
    network.write_bytes(changed)
    weights = [Fraction('1.6'), Fraction(8), Fraction(4)]
    new_weights = [weights[0], weights[1], weights[2]*alpha]
    overrides, table = [], []
    for row in demand_rows(BASE):
        q = Fraction(str(row['volume_vph']))
        if row['input_no'] != 1098:
            continue
        new_q = q * sum(new_weights) / sum(weights)
        overrides.append({'input_no':1098, 'start_sec':row['start_sec'], 'volume_vph':float(new_q)})
        for index, (w, nw) in enumerate(zip(weights, new_weights), 1):
            od, adjusted = q*w/sum(weights), new_q*nw/sum(new_weights)
            assert adjusted == od*(alpha if index == 3 else 1)
            table.append({'input_no':1098, 'start_sec':row['start_sec'], 'end_sec':row['start_sec']+900,
                          'decision':1130, 'route':index, 'before_vph':float(od), 'after_vph':float(adjusted),
                          'before_exact':str(od), 'after_exact':str(adjusted)})
    for filename, rows in [('input_override.csv', overrides), ('desired_demand.csv', table)]:
        with (out/filename).open('x', encoding='ascii', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    report = {'alpha':float(alpha), 'network':str(network), 'network_sha256':hashlib.sha256(changed).hexdigest(),
              'input_override':str(out/'input_override.csv'), 'only_network_change':'1130:3 relFlow',
              'non_target_source_route_demand_preserved_exactly':True, 'other_input_intervals_unchanged':198,
              'seed':13, 'geometry_and_signals_unchanged':True,
              'meaning':'Source generation-cohort expected demand; stochastic realized vehicle counts may differ.'}
    (out/'case.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
