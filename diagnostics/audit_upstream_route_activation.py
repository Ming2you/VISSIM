"""Actual current-route snapshots near the upstream1135 replacement tree."""
from collections import Counter, defaultdict
from pathlib import Path
import json
import xml.etree.ElementTree as ET

from diagnostics import run_fixed_beta300v3_route_experiment as d


def main():
    output = d.ROOT / 'diagnostics/startup_gui_upstream_route_activation_v1.json'
    d.require(not output.exists(), 'Fresh evidence file required')
    batch_path = d.ROOT / 'diagnostics/startup_gui_three_arm_comparison_v1/manifest.json'
    batch = d.load(batch_path)
    d.require(batch['valid'] is True and batch['source_changes'] == [], 'Incomplete batch')
    pins = {d.relative(batch_path): d.sha(batch_path)}
    report = {'schema': 'upstream-route-activation-snapshot/v1', 'runs': {}, 'source_sha256': pins,
              'scope': 'Current routes at750/900/1050 only; selected snapshots are not route-choice probabilities or complete trip cohorts.'}
    for arm in batch['arms']:
        run = d.workspace_path(arm['run'])
        network = Path(arm['command'][arm['command'].index('-Network') + 1])
        d.pin(pins, network, arm['network_sha256'])
        tree = ET.parse(network).getroot()
        decisions = {int(node.get('no')): node for node in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')}
        parent_link = {key: int(decisions[key].get('link')) for key in (1123, 1124, 1125)}
        counts = Counter()
        on68 = Counter()
        examples = []
        observed_ids = defaultdict(set)
        for sec in (750, 900, 1050):
            path = run / ('decisions_' + run.name) / f'state_{sec:06d}.json'
            d.pin(pins, path)
            raw = d.load(path)
            routes, vehicles = raw['vehicle_routes'], raw['vehicle_records']
            d.require(routes['complete'] is True and routes['sim_sec_before'] == routes['sim_sec_after'] == sec
                      and vehicles['complete'] is True and vehicles['capture_sim_sec_before'] == vehicles['capture_sim_sec_after'] == sec,
                      'Incomplete or non-simultaneous snapshot')
            positions = {r['veh_no']: r for r in vehicles['records']}
            d.require(len(positions) == vehicles['record_count'] == len(vehicles['records'])
                      and len(routes['records']) == routes['record_count']
                      and len({r['veh_no'] for r in routes['records']}) == routes['record_count'], 'Duplicate/missing snapshot rows')
            for r in routes['records']:
                pos = positions.get(r['veh_no'])
                d.require(pos is not None, 'Route has no same-time physical record')
                key = f"{r['route_decision_type']}:{r['route_decision_no']}:{r['route_no']}"
                if pos['link_no'] == 68:
                    on68[key] += 1
                if r['route_decision_type'] != 'STATIC':
                    continue
                if r['route_decision_no'] in parent_link or r['route_decision_no'] == 1135:
                    counts[key] += 1
                    observed_ids[key].add(r['veh_no'])
                if r['route_decision_no'] in parent_link and r['route_no'] in (4, 5, 6):
                    examples.append({'sec': sec, **r, **pos,
                                     'still_on_parent_approach': pos['link_no'] == parent_link[r['route_decision_no']]})
        if arm['arm'] == 'upstream1135':
            d.require(1135 not in decisions and not any(k.startswith('STATIC:1135:') for k in counts),
                      'Removed downstream routing decision remains in native network or actual route snapshots')
        report['runs'][arm['arm']] = {
            'downstream1135_in_xml': 1135 in decisions,
            'snapshot_current_route_record_counts': dict(counts),
            'snapshot_unique_vehicle_counts_by_route': {k: len(v) for k, v in observed_ids.items()},
            'link68_snapshot_current_routes': dict(on68),
            'expanded_route_observations': examples,
            'expanded_route_observations_on_parent_approach': sum(r['still_on_parent_approach'] for r in examples)}
    d.assert_pins(pins)
    report['source_changes'] = []
    report['producer_sha256'] = d.sha(__file__)
    d.save(output, report)
    print(json.dumps({k: {'on68': v['link68_snapshot_current_routes'], 'expanded_on_parent': v['expanded_route_observations_on_parent_approach'],
                          'expanded_route_records': len(v['expanded_route_observations'])} for k, v in report['runs'].items()}))


if __name__ == '__main__':
    main()
