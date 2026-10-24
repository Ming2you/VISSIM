"""Current-route observations at eight fixed anchors, not full trip probabilities."""
import argparse
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

from diagnostics import run_no_control_network_arms as n

d = n.d
ANCHORS = tuple(map(int, n.ANCHORS.split(',')))


def inspect(run, network, arm, pins):
    tree = ET.parse(network).getroot()
    decisions = {int(node.get('no')): node for node in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')}
    parents = {key: int(decisions[key].get('link')) for key in (1123, 1124, 1125)}
    counts, by_time, on_parent, observed, road68 = Counter(), {}, Counter(), defaultdict(set), Counter()
    for sec in ANCHORS:
        path = run / ('decisions_' + run.name) / f'anchor_{sec:06d}.json'
        d.pin(pins, path)
        raw = d.load(path)
        routes, vehicles = raw['vehicle_routes'], raw['vehicle_records']
        d.require(routes['complete'] is True and routes['sim_sec_before'] == routes['sim_sec_after'] == sec
                  and vehicles['complete'] is True and vehicles['capture_sim_sec_before'] == vehicles['capture_sim_sec_after'] == sec,
                  'Incomplete or non-simultaneous route anchor')
        positions = {row['veh_no']: row for row in vehicles['records']}
        d.require(len(positions) == vehicles['record_count'] == len(vehicles['records'])
                  and len(routes['records']) == routes['record_count']
                  and len({r['veh_no'] for r in routes['records']}) == routes['record_count'], 'Duplicate/missing anchor rows')
        sample = Counter()
        for row in routes['records']:
            pos = positions.get(row['veh_no'])
            d.require(pos is not None, 'Route without a same-time vehicle')
            if row['route_decision_type'] != 'STATIC':
                continue
            decision, route = row['route_decision_no'], row['route_no']
            key = f'{decision}:{route}'
            if pos['link_no'] == 68:
                road68[key] += 1
            if decision not in parents and decision != 1135:
                continue
            counts[key] += 1; sample[key] += 1; observed[key].add(row['veh_no'])
            if decision in parents and route in (4, 5, 6) and pos['link_no'] == parents[decision]:
                on_parent[key] += 1
        by_time[sec] = sample
    if arm == 'upstream1135':
        d.require(1135 not in decisions and not any(k.startswith('1135:') for k in counts), 'Removed downstream1135 still present')
    return dict(downstream1135_in_xml=1135 in decisions, observations_by_route=counts,
                observations_by_anchor=by_time, expanded_observations_still_on_parent=on_parent,
                unique_vehicles_by_route={key: len(ids) for key, ids in observed.items()},
                link68_route_observations=road68,
                observed_expanded_routes=sorted(k for k in counts if int(k.split(':')[0]) in parents and int(k.split(':')[1]) in (4, 5, 6)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args()
    manifest, output = d.workspace_path(args.manifest), d.workspace_path(args.output)
    d.require(not output.exists(), 'New output required')
    batch = d.load(manifest)
    d.require(batch['valid'] is True and batch['completed'] is True and batch['status'] == 'all_three_passed'
              and [r['arm'] for r in batch['arms']] == list(d.ARMS), 'Incomplete or wrong batch')
    pins = {d.relative(p): d.sha(p) for p in (manifest, Path(__file__), Path(n.__file__), Path(d.__file__))}
    records, used = {}, set()
    for row in batch['arms']:
        run = d.workspace_path(row['run'])
        d.require(row['valid'] and row['status'] == 'passed' and row['exit_code'] == 0
                  and run.name == row['name'] and run not in used, 'Wrong or duplicate completed run')
        used.add(run)
        provenance_path = run / ('run_provenance_' + run.name + '.json')
        d.pin(pins, provenance_path, row['validation']['provenance_sha256'])
        provenance = d.load(provenance_path)
        d.require(all(provenance[k] == v for k, v in n.EXPECTED.items()), 'Wrong NC source')
        network = d.workspace_path(provenance['files']['network']['path'])
        d.pin(pins, network, provenance['files']['network']['sha256'])
        records[row['arm']] = inspect(run, network, row['arm'], pins)
    d.assert_pins(pins)
    d.save(output, dict(valid=True, anchors_sec=ANCHORS, runs=records, source_sha256=pins, source_changes=[],
                        scope='Eight simultaneous current-route snapshots. Repeated vehicle observations are not independent trips; these counts are not choice probabilities.',
                        limits=['A current-route attribute does not disclose all internal LookAhead future choices.',
                                'Matching seed and turning probabilities does not match every realized vehicle OD after route-tree changes.']))
    print({arm: {'expanded_routes': len(r['observed_expanded_routes']), 'on_parent_observations': sum(r['expanded_observations_still_on_parent'].values())}
           for arm, r in records.items()})


if __name__ == '__main__':
    main()
