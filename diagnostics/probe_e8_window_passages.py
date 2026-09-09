"""Bounded full-window ID passage evidence; no simulator or model execution."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from diagnostics.probe_e8_lane_receiving import IndexedFzp, RUNS, read_rows

WINDOWS = ((1050, 1200), (1200, 1350), (3150, 3300), (3300, 3450))
RANGES = ((1050, 1350), (3150, 3450))


def frames(reader, start, end, budget_deadline, provenance):
    reader.seek_time(start)
    current, current_t = {}, None
    digest, rows, first_byte = hashlib.sha256(), 0, None
    while row := reader.line():
        fields = row.rstrip(b'\r\n').split(b';')
        t = float(fields[0])
        if t < start:
            continue
        if t > end:
            break
        if first_byte is None:
            first_byte = reader.handle.tell() - len(row)
        if current_t is not None and t != current_t:
            assert t > current_t
            if time.monotonic() > budget_deadline:
                raise RuntimeError('45-second per-run CPU/wall budget exhausted')
            yield current_t, current
            current = {}
        current_t = t
        digest.update(row)
        rows += 1
        i = reader.index
        vehicle = int(fields[i['NO']])
        assert vehicle not in current
        current[vehicle] = (int(fields[i['LANE\\LINK\\NO']]), int(fields[i['LANE\\INDEX']]),
                            float(fields[i['POS']]), float(fields[i['SPEED']]))
    if current_t is not None:
        yield current_t, current
    provenance.append({'start_sec': start, 'end_sec': end, 'rows': rows,
                       'first_byte': first_byte, 'raw_range_sha256': digest.hexdigest()})


class Geometry:
    def __init__(self, evidence):
        mapping = json.loads((ROOT / 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json').read_text(encoding='utf-8'))
        chain = mapping['freeway_model_links']['FW_E']
        self.offsets = dict(zip(map(int, chain['chain_links']), chain['chain_offsets_m']))
        self.connectors = {}
        import xml.etree.ElementTree as ET
        network = ET.parse(ROOT / 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx').getroot()
        pairs = defaultdict(list)
        for node in network.findall('./links/link'):
            source, target = node.find('fromLinkEndPt'), node.find('toLinkEndPt')
            if source is None or target is None:
                continue
            src, dst = int(source.get('lane').split()[0]), int(target.get('lane').split()[0])
            pairs[src, dst].append(int(node.get('no')))
            key = int(node.get('no'))
            if key not in (10639, 10681, 10682):
                continue
            points = [(float(p.get('x')), float(p.get('y')), float(p.get('zOffset', 0)))
                      for p in node.findall('./geometry/linkPolyPts/linkPolyPoint')]
            self.connectors[key] = {'source': src, 'target': dst, 'source_lane': int(source.get('lane').split()[1]),
                                    'target_lane': int(target.get('lane').split()[1]), 'source_pos': float(source.get('pos')),
                                    'target_pos': float(target.get('pos')),
                                    'length': sum(math.dist(a, b) for a, b in zip(points, points[1:]))}
        self.unique_pairs = {pair: keys[0] for pair, keys in pairs.items() if len(keys) == 1 and keys[0] in self.connectors}
        direct = evidence['physical_connectors']['10682']['endpoints']['fromLinkEndPt']['freeway_chain_m']
        merge1 = evidence['physical_connectors']['10639']['endpoints']['toLinkEndPt']['freeway_chain_m']
        merge2 = evidence['physical_connectors']['10681']['endpoints']['toLinkEndPt']['freeway_chain_m']
        self.gates = {'e8_e9': evidence['cell_bounds_m'][1], 'diverge_before_1m': direct - 1,
                      'diverge_after_1m': direct + 1, 'weave_start': merge1 - 1, 'weave_end': merge2 + 1}
        self.regions = {'weave_mainline': (self.gates['weave_start'], self.gates['weave_end']),
                        'e9_diverge_mainline': (self.gates['e8_e9'], self.gates['diverge_after_1m'])}

    def pos(self, row):
        return row[2] + self.offsets[row[0]] if row[0] in self.offsets else None

    def memberships(self, row):
        p = self.pos(row)
        keys = [name for name, (a, b) in self.regions.items() if p is not None and a <= p < b]
        if row[0] == 10682:
            keys.append('direct_connector')
        return keys

    def classify(self, row):
        if row is None:
            return 'absent'
        if row[0] in self.connectors:
            return 'connector:' + str(row[0])
        if row[0] in self.offsets:
            return 'mainline'
        return 'other_link:' + str(row[0])


def transitions(geometry, vehicle, old, new, t0, t1):
    """Proven mainline subpaths; unique skipped connectors are tagged separately."""
    result = []
    def emit(kind, distance_before, distance_total, *, inferred=False, lane0=None, lane1=None, direction=1):
        valid = distance_total > 0 and -1e-6 <= distance_before <= distance_total + 1e-6
        result.append({'kind': kind, 'vehicle_id': vehicle, 't0': t0, 't1': t1,
                       'estimated_sec': t0 + (t1-t0)*distance_before/distance_total if valid else None,
                       'method': 'linear_path_distance' if valid else 'interval_only',
                       'inferred_short_connector': inferred, 'direction': direction,
                       'lane_before': lane0, 'lane_after': lane1,
                       'lane_endpoints_agree': lane0 is not None and lane0 == lane1,
                       'old_link': old[0], 'new_link': new[0], 'old_pos': old[2], 'new_pos': new[2]})
    def gates(a, b, total, prefix=0., inferred=False, lane0=None, lane1=None):
        for name, gate in geometry.gates.items():
            if a < gate <= b:
                emit(name, prefix+gate-a, total, inferred=inferred, lane0=lane0, lane1=lane1)
            elif b <= gate < a:
                emit(name, prefix+a-gate, total, inferred=inferred, lane0=lane0, lane1=lane1, direction=-1)
    a, b = geometry.pos(old), geometry.pos(new)
    if a is not None and b is not None:
        gates(a, b, abs(b-a), lane0=old[1], lane1=new[1])
    if old[0] == new[0]:
        return result
    for conn, spec in geometry.connectors.items():
        if new[0] == conn:
            distance = spec['source_pos'] - old[2] if old[0] == spec['source'] else None
            total = distance + new[2] if distance is not None else -1.
            emit(f'connector_{conn}_entry', distance if distance is not None else -1., total)
            if a is not None and old[0] == spec['source']:
                gates(a, spec['source_pos'] + geometry.offsets[old[0]], total, lane0=old[1], lane1=spec['source_lane'])
        if old[0] == conn:
            remaining = spec['length'] - old[2]
            total = remaining + new[2] - spec['target_pos'] if new[0] == spec['target'] else -1.
            emit(f'connector_{conn}_exit', remaining, total)
            if b is not None and new[0] == spec['target']:
                gates(spec['target_pos'] + geometry.offsets[new[0]], b, total, prefix=remaining, lane0=spec['target_lane'], lane1=new[1])
    skipped = geometry.unique_pairs.get((old[0], new[0]))
    if skipped:
        spec = geometry.connectors[skipped]
        first = spec['source_pos'] - old[2]
        total = first + spec['length'] + new[2] - spec['target_pos']
        emit(f'connector_{skipped}_entry', first, total, inferred=True)
        emit(f'connector_{skipped}_exit', first+spec['length'], total, inferred=True)
        if a is not None:
            gates(a, spec['source_pos'] + geometry.offsets[old[0]], total, inferred=True, lane0=old[1], lane1=spec['source_lane'])
        if b is not None:
            gates(spec['target_pos'] + geometry.offsets[new[0]], b, total, first+spec['length'], True, spec['target_lane'], new[1])
    return result


def inventory(geometry, frame):
    out = {name: set() for name in (*geometry.regions, 'direct_connector')}
    for veh, row in frame.items():
        for region in geometry.memberships(row):
            out[region].add(veh)
    return out


def removal_matches(rows, t0, t1):
    # A warning at t0 can follow that second's FZP record; the vehicle is then
    # first absent at t1. Preserve this bracket rather than shifting its time.
    return [r for r in rows if t0 <= float(r['sim_sec']) <= t1]


def event_summary(events, a, b):
    groups = defaultdict(list)
    for event in events:
        if event['t1'] > a and event['t0'] < b:
            groups[event['kind']].append(event)
    output = {}
    for key, rows in groups.items():
        estimated = [r for r in rows if r['estimated_sec'] is not None and a < r['estimated_sec'] <= b]
        strict = [r for r in estimated if not r['inferred_short_connector']]
        counts = Counter(str(r['lane_after']) for r in strict if r['lane_after'] is not None)
        output[key] = {'estimated_count_observed': len(strict), 'estimated_count_inferred': len(estimated)-len(strict),
                       'estimated_unique_vehicle_ids': sorted({r['vehicle_id'] for r in estimated}),
                       'definitely_within_observed': sum(r['t0'] >= a and r['t1'] <= b and not r['inferred_short_connector'] for r in rows),
                       'possibly_within_observed': sum(not r['inferred_short_connector'] for r in rows),
                       'interval_only_observed': sum(r['estimated_sec'] is None and not r['inferred_short_connector'] for r in rows),
                       'lane_after_estimated_counts': dict(counts),
                       'lane_before_estimated_counts': dict(Counter(str(r['lane_before']) for r in strict if r['lane_before'] is not None)),
                       'ambiguous_crossing_lane_count': sum(r['lane_before'] is not None and not r['lane_endpoints_agree'] for r in strict),
                       'reverse_crossings': sum(r['direction'] < 0 for r in strict)}
    return output


def analyze(label):
    started = time.monotonic()
    evidence_path = ROOT / 'diagnostics/e8_lane_receiving_evidence.json'
    evidence = json.loads(evidence_path.read_text())
    source = evidence['runs'][label]
    geometry = Geometry(evidence)
    path = ROOT / source['fzp_snapshot_provenance']['path']
    cadence = source['cadence_sec']
    reader = IndexedFzp(path, max_bytes=256*1024*1024)
    first_time = 1.
    ceil_frame = lambda t: first_time + math.ceil((t-first_time)/cadence)*cadence
    floor_frame = lambda t: first_time + math.floor((t-first_time)/cadence)*cadence
    observed_windows = [(ceil_frame(a), ceil_frame(b)) for a, b in WINDOWS]
    closures = {str(a): {'nominal_window': [a, b], 'observed_window': list(obs), 'regions': {}}
                for (a, b), obs in zip(WINDOWS, observed_windows)}
    events, changes, provenance = [], [], []
    warning_rows = source.get('link2_lane_change_removals') or []
    warnings = defaultdict(list)
    for row in warning_rows:
        warnings[int(row['vehicle'])].append(row)
    snapshots = {}
    for a, b in RANGES:
        previous, prev_t, prev_inv = None, None, None
        for t, current in frames(reader, floor_frame(a)-cadence, ceil_frame(b)+cadence, started+45, provenance):
            inv = inventory(geometry, current)
            if any(t in window for window in observed_windows):
                snapshots[t] = {k: sorted(v) for k, v in inv.items()}
            if previous is not None:
                for veh in previous.keys() & current.keys():
                    old, new = previous[veh], current[veh]
                    if (old[0] in geometry.offsets or new[0] in geometry.offsets or
                            old[0] in geometry.connectors or new[0] in geometry.connectors):
                        events.extend(transitions(geometry, veh, old, new, prev_t, t))
                for region in inv:
                    for direction, vehicles in [('in', inv[region]-prev_inv[region]), ('out', prev_inv[region]-inv[region])]:
                        for veh in vehicles:
                            old, new = previous.get(veh), current.get(veh)
                            matches = removal_matches(warnings.get(veh, []), prev_t, t)
                            changes.append({'region': region, 'vehicle_id': veh, 't0': prev_t, 't1': t,
                                            'direction': direction, 'source': geometry.classify(old), 'target': geometry.classify(new),
                                            'old': old, 'new': new, 'matched_lane_change_removal': matches})
            previous, prev_t, prev_inv = current, t, inv
    reader.handle.close()
    for (a, b), (oa, ob) in zip(WINDOWS, observed_windows):
        for region in (*geometry.regions, 'direct_connector'):
            rows = [r for r in changes if r['region'] == region and r['t0'] >= oa and r['t1'] <= ob]
            incoming = [r for r in rows if r['direction'] == 'in']
            outgoing = [r for r in rows if r['direction'] == 'out']
            n0, n1 = len(snapshots[oa][region]), len(snapshots[ob][region])
            categories = Counter(f"{r['direction']}:{r['source']}->{r['target']}" for r in rows)
            if region == 'weave_mainline':
                positive, negative = ('weave_start', 'connector_10639_exit', 'connector_10681_exit'), ('weave_end', 'connector_10682_entry')
            elif region == 'e9_diverge_mainline':
                positive, negative = ('e8_e9',), ('diverge_after_1m', 'connector_10682_entry')
            else:
                positive, negative = ('connector_10682_entry',), ('connector_10682_exit',)
            flux = [e for e in events if e['t0'] >= oa and e['t1'] <= ob and e['kind'] in positive+negative]
            signed = lambda e: e['direction']*(1 if e['kind'] in positive else -1)
            net_strict = sum(signed(e) for e in flux if not e['inferred_short_connector'])
            net_all = sum(signed(e) for e in flux)
            removals = [r['vehicle_id'] for r in outgoing if r['matched_lane_change_removal']]
            region_result = {'count_start': n0, 'count_end': n1, 'delta_count': n1-n0,
                             'observed_membership_entries': len(incoming), 'observed_membership_exits': len(outgoing),
                             'identity_residual': n1-n0-len(incoming)+len(outgoing),
                             'membership_categories': dict(categories), 'strict_physical_flux_net': net_strict,
                             'physical_flux_net_including_unique_skips': net_all,
                             'strict_flux_residual': n1-n0-net_strict, 'flux_residual_including_unique_skips': n1-n0-net_all,
                             'flux_residual_after_verified_removals': n1-n0-net_all+len(removals),
                             'newly_appeared_ids': [r['vehicle_id'] for r in incoming if r['source']=='absent'],
                             'disappeared_ids': [r['vehicle_id'] for r in outgoing if r['target']=='absent'],
                             'matched_removal_ids': removals}
            assert region_result['identity_residual'] == 0
            closures[str(a)]['regions'][region] = region_result
    result = {'run': RUNS[label], 'label': label, 'cadence_sec': cadence, 'nominal_windows': WINDOWS,
              'gate_chain_m': geometry.gates, 'region_bounds_m': geometry.regions, 'connectors': geometry.connectors,
              'method': {'nominal_event_windows': '(start,end]; linear interpolation over the observed path, with full bracket retained',
                         'mainline_lane': 'before/after lanes both retained; disagreement proves ambiguity, agreement is only an endpoint proxy and cannot rule out unobserved intermediate lane changes',
                         'branch_lane': 'connector endpoints prove route; inferred skipped connectors require a unique physical source-target pair',
                         'stock_closure': 'exact sampled membership identity and independent gate/branch flux, on ceil-to-recorded-time endpoints',
                         'censoring': 'interior disappearance is a loss/unknown, never successful outflow; bounded stream has bracket frames',
                         'capacity': 'no estimated counts or rates are identified capacities; no parameter fitting'},
              'provenance': {'fzp_path': str(path.relative_to(ROOT)), 'file_size': path.stat().st_size, 'mtime_ns': path.stat().st_mtime_ns,
                             'bytes_read': reader.bytes_read, 'ranges': provenance, 'elapsed_sec': time.monotonic()-started,
                             'warning_cache_available': source['warning_cache_available'],
                             'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                               (Path(__file__), ROOT/'diagnostics/probe_e8_lane_receiving.py', evidence_path)}},
              'nominal_passages': {str(a): event_summary(events, a, b) for a, b in WINDOWS},
              'sampled_stock_closure': closures, 'endpoint_stock_vehicle_ids': snapshots,
              'events': events, 'membership_changes': changes}
    out = ROOT / f'diagnostics/e8_window_passages_{label}.json'
    out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'label': label, 'output': str(out.relative_to(ROOT)), 'bytes_read': reader.bytes_read,
                      'seconds': round(time.monotonic()-started, 3), 'events': len(events),
                      'max_physical_flux_residual': max(abs(r['flux_residual_including_unique_skips']) for w in closures.values() for r in w['regions'].values())}), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('labels', nargs='*', choices=list(RUNS), default=list(RUNS))
    args = p.parse_args()
    for label in args.labels:
        analyze(label)
