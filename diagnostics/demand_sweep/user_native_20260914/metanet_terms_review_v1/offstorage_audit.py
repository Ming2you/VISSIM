"""Read existing native aggregates; audit connector stock and entry/drain meaning.

No native execution, raw FZP read, fitted constants, or frozen artifact changes.
"""
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'metanet_calibration_v1'


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_csv(path, values):
    with path.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]))
        writer.writeheader()
        writer.writerows(values)


def main():
    spacing = load(ROOT / 'evaluation/parameters.json')['network']['urban_avg_vehicle_length_m']
    geometry = load(BASE / 'seed13_observations/geometry.json')
    network = Path(geometry['network']['path'])
    tree = ET.parse(network)
    nodes = {int(n.get('no')): n for n in tree.findall('./links/link')}
    heads, exits, physical = defaultdict(list), defaultdict(list), {}
    for number, node in nodes.items():
        points = [tuple(float(p.get(k, 0)) for k in ('x', 'y', 'zOffset'))
                  for p in node.findall('./geometry/linkPolyPts/linkPolyPoint')]
        physical[number] = {'length_m': math.fsum(math.dist(a, b) for a, b in zip(points, points[1:])),
                            'lanes': len(node.findall('./lanes/lane'))}
        a, z = node.find('fromLinkEndPt'), node.find('toLinkEndPt')
        if a is not None:
            exits[int(a.get('lane').split()[0])].append({'connector': number,
                'from_pos_m': float(a.get('pos')), 'to_link': int(z.get('lane').split()[0]),
                'to_pos_m': float(z.get('pos'))})
    for h in tree.findall('./signalHeads/signalHead'):
        heads[int(h.get('lane').split()[0])].append({'lane': h.get('lane'), 'pos_m': float(h.get('pos')), 'sg': h.get('sg')})

    # First signal reachable along each physical branch, ending at that signal.
    # This is a topology inventory, not route probabilities or realized paths.
    def downstream(link, pos, path, depth=0):
        hs = [h for h in heads[link] if h['pos_m'] >= pos]
        if hs:
            return [{'path': path, 'signal_link': link, 'heads': hs}]
        if depth >= 4:
            return [{'path': path, 'status': 'depth_limit'}]
        branches = [e for e in exits[link] if e['from_pos_m'] >= pos]
        if not branches:
            return [{'path': path, 'status': 'terminal_no_downstream_connector'}]
        result = []
        for edge in branches:
            if edge['to_link'] in {x['link'] for road in geometry['chains'].values() for x in road}:
                result.append({'path': path + [edge['connector'], edge['to_link']], 'status': 'returns_to_mainline'})
            elif edge['to_link'] not in path:
                result.extend(downstream(edge['to_link'], edge['to_pos_m'], path + [edge['connector'], edge['to_link']], depth + 1))
        return result

    native13 = HERE.parent / 'east080_v1/results_v1'
    link150 = {(int(r['end_sec']), int(r['link'])): r for r in rows(native13 / 'links_150s.csv')}
    off150 = {(int(r['end_sec']), int(r['connector'])): r for r in rows(native13 / 'offramps_150s.csv')}
    totals, series, validation, provenance = [], [], [], {}
    for seed in (13, 17):
        folder = BASE / f'seed{seed}_observations'
        manifest, geo = load(folder / 'manifest.json'), load(folder / 'geometry.json')
        observations = rows(folder / 'boundaries_30s.csv')
        exclusion = load(folder / 'exclusion_evidence.json')
        cell = {(int(r['time_s']), r['road'], int(r['cell'])): r for r in rows(folder / 'cells_30s.csv')}
        provenance[str(seed)] = {'manifest_sha256': sha(folder / 'manifest.json'), 'fzp_sha256_recorded': manifest['fzp']['file_sha256'],
            'network_sha256': geo['network']['sha256'], 'files': manifest['files']}
        for b in [x for x in geo['boundaries'] if x['kind'] == 'offramp']:
            connector = b['connector']
            records = [r for r in observations if r['id'] == b['id']]
            capacity = b['length_m'] * b['lanes'] / spacing
            previous, drains, local = 0, [], []
            native_removals = [r for r in exclusion['native_removals'] if int(r['link']) == connector]
            for r in records:
                end = int(r['window_end_s']); n = int(r['snapshot_n_veh']); entry = int(r['crossings'])
                # Conservation implies exits + unresolved absences - other entries.
                # It is not by itself a measured connector->urban crossing count.
                drain = previous + entry - n
                mainline = cell[end, b['road'], b['from_cell']]
                item = {'seed': seed, 'connector': connector, 'id': b['id'], 'window_start_s': end - 30,
                    'window_end_s': end, 'start_n': previous, 'end_n': n, 'entry_from_mainline': entry,
                    'conservation_implied_departure': drain, 'stock_delta': n - previous,
                    'nominal_capacity_veh_6m': capacity, 'stock_fraction_nominal': n / capacity,
                    'mainline_cell_display': b['from_cell'] + 1, 'mainline_n': int(mainline['n_veh']),
                    'mainline_speed_kmh': float(mainline['v_kmh']) if mainline['v_kmh'] else None}
                series.append(item); local.append(item); drains.append(drain); previous = n
            peak = max(local, key=lambda r: r['end_n'])
            stopped_total = ttt_total = 0.
            absent_total = exit_total = other_entry_total = 0
            if seed == 13:
                for end in range(150, 9001, 150):
                    interval = [r for r in local if end - 150 < r['window_end_s'] <= end]
                    physical_row = link150.get((end, connector))
                    if physical_row is None:
                        # Existing link table is sparse: no row before the first
                        # vehicle appears, or throughout an entirely empty bin.
                        assert all(r['start_n'] == r['end_n'] == r['entry_from_mainline'] == 0 for r in interval)
                        physical_row = dict.fromkeys(('observed_other_link_exits', 'unresolved_absences',
                            'entries', 'stopped_veh_h', 'ttt_veh_h'), 0)
                    inferred = sum(r['conservation_implied_departure'] for r in interval)
                    actual_exits = int(physical_row['observed_other_link_exits'])
                    absences = int(physical_row['unresolved_absences'])
                    extra_entries = int(physical_row['entries']) - sum(r['entry_from_mainline'] for r in interval)
                    residual = inferred - actual_exits - absences + extra_entries
                    validation.append({'seed': seed, 'connector': connector, 'start_s': end - 150, 'end_s': end,
                        'implied_departures_veh': inferred, 'observed_other_link_exits': actual_exits,
                        'unresolved_absences': absences, 'entries_other_than_measured_mainline': extra_entries,
                        'reconciliation_residual': residual})
                    absent_total += absences; exit_total += actual_exits; other_entry_total += extra_entries
                    stopped_total += float(physical_row['stopped_veh_h']); ttt_total += float(physical_row['ttt_veh_h'])
            downstream_paths = downstream(b['to_link'], b['to_pos_m'], [connector, b['to_link']])
            summary = {'seed': seed, 'id': b['id'], 'connector': connector, 'road': b['road'],
                'mainline_cell_display': b['from_cell'] + 1, 'branch_chain_pos_m': b['chain_pos_m'],
                'length_m': b['length_m'], 'lanes': b['lanes'], 'nominal_capacity_veh_6m': capacity,
                'peak_n': peak['end_n'], 'first_peak_sec': peak['window_end_s'], 'peak_fraction_nominal': peak['end_n'] / capacity,
                'samples_ge80pct': sum(r['stock_fraction_nominal'] >= .8 for r in local),
                'samples_ge90pct': sum(r['stock_fraction_nominal'] >= .9 for r in local),
                'first_ge80pct_sec': next((r['window_end_s'] for r in local if r['stock_fraction_nominal'] >= .8), None),
                'end_n': previous, 'total_mainline_entries': sum(r['entry_from_mainline'] for r in local),
                'total_implied_departures': sum(drains), 'min_implied_departures_30s': min(drains),
                'windows_stock_increases': sum(r['stock_delta'] > 0 for r in local),
                'windows_stock_decreases': sum(r['stock_delta'] < 0 for r in local),
                'mean_abs_entry_vs_drain_difference_vph': sum(abs(r['stock_delta']) for r in local) * 120 / len(local),
                'max_abs_entry_vs_drain_difference_vph': max(abs(r['stock_delta']) for r in local) * 120,
                'explicit_native_removals': len(native_removals),
                'connector_stopped_veh_h_seed13_only': stopped_total if seed == 13 else None,
                'connector_ttt_veh_h_seed13_only': ttt_total if seed == 13 else None,
                'connector_stopped_residence_fraction_seed13_only': stopped_total / ttt_total if seed == 13 and ttt_total else None,
                'observed_connector_exits_seed13_only': exit_total if seed == 13 else None,
                'unresolved_connector_absences_seed13_only': absent_total if seed == 13 else None,
                'other_connector_entries_seed13_only': other_entry_total if seed == 13 else None,
                'landing_link': b['to_link'], 'landing_pos_m': b['to_pos_m'],
                'landing_length_m': physical[b['to_link']]['length_m'], 'landing_lanes': physical[b['to_link']]['lanes'],
                'mainline_speed_at_first_peak_kmh': peak['mainline_speed_kmh'],
                'downstream_paths': json.dumps(downstream_paths)}
            totals.append(summary)
    assert all(r['reconciliation_residual'] == 0 for r in validation)
    write_csv(HERE / 'offstorage_summary.csv', totals)
    write_csv(HERE / 'offstorage_timeseries_30s.csv', series)
    write_csv(HERE / 'offstorage_seed13_drain_reconciliation_150s.csv', validation)
    output = {'schema': 'offstorage-identifiability-audit/v1', 'spacing_m': spacing, 'provenance': provenance,
        'source_script_sha256': sha(__file__), 'source_code': {str(p.relative_to(ROOT)): sha(p) for p in [
            BASE/'boundary_factory.py', BASE/'canonical_harness.py', ROOT/'evaluation/controllers/area_freeway_accounting.py']},
        'freeze_sha256': sha(BASE/'FREEZE.json'), 'summaries': totals,
        'seed13_drain_validation': {'windows': len(validation), 'max_abs_residual': max(abs(r['reconciliation_residual']) for r in validation),
            'unresolved_absences': sum(r['unresolved_absences'] for r in validation),
            'other_entries': sum(r['entries_other_than_measured_mainline'] for r in validation)},
        'limits': ['Capacity is length times lanes divided by canonical6m spacing; not observed jam capacity.',
            '30s connector stock cannot resolve lane occupancy or queue tail reaching the mainline.',
            'Implied departures are entries minus stock change; seed13 checked against existing150s physical exits/absences. Seed17 lacks that independent physical-exit table.',
            'Stock near nominal full plus coincident mainline congestion is association, not causal spillback identification.',
            'Boundary factory off_capacity_vph is mainline-to-connector entry rate, not connector-to-urban drainage.',
            'Harness connector occupancy is externally prescribed/frozen; no autonomous connector accumulation or downstream urban signal coupling is validated.',
            'Landing links carry traffic from multiple sources; full-link stock is not solely off-ramp destination stock.',
            'No actual downstream signal timing/cycle-event join or lane-position tail observation was performed.']}
    with (HERE / 'offstorage_audit.json').open('x', encoding='utf-8') as stream:
        json.dump(output, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'done': str(HERE), 'seed13_reconciliation': output['seed13_drain_validation'], 'summary': totals}, ensure_ascii=False))


if __name__ == '__main__':
    main()
