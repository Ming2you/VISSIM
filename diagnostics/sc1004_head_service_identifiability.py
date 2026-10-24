"""Read-only per-head queued-GREEN evidence; no model, optimizer or calibration write.

The full completed NC FZP is scanned once into a hash-pinned selected-link extract.
Subsequent analyses read only that extract. All outputs use this file's stem.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path
import time
import xml.etree.ElementTree as ET

from diagnostics.selected_signal_sampling_audit import head_events
from diagnostics.prepare_sc15_service_calibration import blocks_from_rows, HOLDOUTS
from plant.src.vissim_strict.signal_program import parse_sig
from evaluation.controllers.fixed_signal_schedule import _union_green_overlap

ROOT = Path(__file__).resolve().parents[1]
STEM = ROOT / 'diagnostics/sc1004_head_service_identifiability'
ROADS = ('46', '66', '71')
RUN = ROOT / 'evaluation/runs/codex_area_observed_nc_s13_20260910'
NETWORK = ROOT / 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'


def path(suffix): return Path(str(STEM) + suffix)
def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()


def geometry():
    tree = ET.parse(NETWORK).getroot()
    out = {road: {'heads': [], 'branches': {}} for road in ROADS}
    for h in tree.findall('./signalHeads/signalHead'):
        road, lane = h.get('lane').split()
        if road not in out: continue
        sc, sg = h.get('sg').split()
        if sc != '1004': raise ValueError('Unexpected head authority')
        out[road]['heads'].append({'head': h.get('no'), 'SC': sc, 'sg': sg,
                                 'lane': int(lane), 'pos_m': float(h.get('pos')), 'road': road})
    for node in tree.findall('./links/link'):
        a, b = node.find('fromLinkEndPt'), node.find('toLinkEndPt')
        if a is None or b is None: continue
        road, lane = a.get('lane').split()
        if road not in out: continue
        target, target_lane = b.get('lane').split()
        points = [tuple(float(p.get(k, 0)) for k in ('x', 'y', 'zOffset'))
                  for p in node.findall('./geometry/linkPolyPts/linkPolyPoint')]
        out[road]['branches'][node.get('no')] = {
            'source_lane': int(lane), 'target_lane': int(target_lane),
            'lanes': len(node.findall('./lanes/lane')), 'from_pos_m': float(a.get('pos')),
            'target': target, 'target_pos_m': float(b.get('pos')),
            'length_m': sum(math.dist(x, y) for x, y in zip(points, points[1:]))}
    for road, spec in out.items():
        for head in spec['heads']:
            same = {k: b for k, b in spec['branches'].items()
                    if b['source_lane'] <= head['lane'] < b['source_lane'] + b['lanes']}
            head['post_head_connectors'] = [k for k, b in same.items() if b['from_pos_m'] >= head['pos_m']]
            head['pre_head_bypasses'] = [k for k, b in same.items() if b['from_pos_m'] < head['pos_m']]
    sc = next(s for s in tree.findall('./signalControllers/signalController') if s.get('no') == '1004')
    if sc.get('type') != 'FIXEDTIME' or sc.get('active') != 'true': raise ValueError('Native clock changed')
    sig = NETWORK.parent / sc.get('supplyFile2').removeprefix('#data#')
    program = parse_sig(sig, int(sc.get('progNo')))
    return out, sig, program, float(sc.get('offset')), dict(sc.attrib)


def extract(geo):
    fzp = next((RUN / 'vissim_eval').glob('*.fzp'))
    output, manifest = path('.selected.fzp.gz'), path('.extract.json')
    watched = sorted(set(ROADS) | {k for g in geo.values() for k in g['branches']}
                     | {b['target'] for g in geo.values() for b in g['branches'].values()})
    stat = fzp.stat()
    if manifest.exists():
        m = json.loads(manifest.read_text(encoding='utf-8'))
        if (m['fzp']['bytes'], m['fzp']['mtime_ns']) != (stat.st_size, stat.st_mtime_ns):
            raise ValueError('Completed source FZP differs from cached extraction')
        if m['selected_links'] != watched or m['extract_sha256'] != sha(output):
            raise ValueError('Selected extract contract/hash changed')
        return output, m
    if output.exists(): raise ValueError('Unfinished extraction already exists')
    wanted = {x.encode() for x in watched}
    full_hash, selected_hash = hashlib.sha256(), hashlib.sha256()
    header = False; last = None; frame_count = 0; rows = kept = 0; first = None
    started = time.monotonic()
    with fzp.open('rb') as f, gzip.open(output, 'wb', compresslevel=1) as target:
        for line in f:
            full_hash.update(line)
            if line.startswith(b'$VEHICLE:'):
                expected = b'$VEHICLE:SIMSEC;NO;LANE\\LINK\\NO;LANE\\INDEX;POS;POSLAT;SPEED;TMINNETTOT;DELAYTM'
                if line.strip() != expected: raise ValueError('FZP schema changed')
                header = True; target.write(line); selected_hash.update(line); continue
            if not header or not line.strip() or line.startswith((b'*', b'$')): continue
            fields = line.split(b';', 4); rows += 1
            t = fields[0]
            if t != last:
                second = float(t)
                if last is not None and second - float(last) != 1: raise ValueError('FZP cadence is not1s')
                first = second if first is None else first
                last = t; frame_count += 1
            if fields[2].strip() in wanted:
                target.write(line); selected_hash.update(line); kept += 1
    if (first, float(last), frame_count) != (1., 5400., 5400): raise ValueError('Incomplete NC trajectory')
    if (stat.st_size, stat.st_mtime_ns) != (fzp.stat().st_size, fzp.stat().st_mtime_ns): raise ValueError('FZP changed')
    original = json.loads((ROOT / 'diagnostics/native_sc15_source_discharge.json').read_text(encoding='utf-8'))
    if full_hash.hexdigest() != original['fzp']['sha256']: raise ValueError('Different NC source from SC15 evidence')
    m = {'fzp': {'path': str(fzp.relative_to(ROOT)), 'sha256': full_hash.hexdigest(),
                 'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns},
         'selected_links': watched, 'rows_read': rows, 'rows_retained': kept,
         'frames': frame_count, 'first_sec': first, 'last_sec': float(last),
         'selected_uncompressed_sha256': selected_hash.hexdigest(), 'extract_sha256': sha(output),
         'extract_bytes': output.stat().st_size, 'elapsed_sec': time.monotonic() - started}
    manifest.write_text(json.dumps(m, indent=2) + '\n', encoding='utf-8')
    return output, m


def selected_frames(file):
    current, last = {}, None
    with gzip.open(file, 'rb') as f:
        for line in f:
            if line.startswith(b'$'): continue
            fields = line.split(b';'); t = int(float(fields[0])); no = int(fields[1])
            if last is not None and t != last:
                yield last, current
                for empty in range(last + 1, t): yield empty, {}
                current = {}
            if no in current: raise ValueError('Duplicate vehicle within selected frame')
            current[no] = (int(fields[2]), int(fields[3]), float(fields[4]), float(fields[6]))
            last = t
    if last is not None: yield last, current


def clock(program, offset):
    lsa = next((RUN / 'vissim_eval').glob('*.lsa'))
    changes = defaultdict(list)
    for line in lsa.read_text(errors='replace').splitlines():
        f = [x.strip() for x in line.split(';')]
        if len(f) >= 5 and f[2] == '1004': changes[f[3]].append((float(f[0]), f[4].upper()))
    result = {}
    for sg in ('2', '3', '4', '5', '7', '8'):
        rows = changes[sg]
        if not rows: raise ValueError('Missing actual native LSA group')
        mismatch = []; i = 0
        for t in range(math.ceil(rows[0][0]), 5400):
            while i + 1 < len(rows) and rows[i + 1][0] <= t: i += 1
            expected = program.state_at(t, sg, controller_offset_sec=offset)
            if expected != rows[i][1]: mismatch.append(t)
        if mismatch: raise ValueError('Native SC1004 clock mismatch')
        result[sg] = {'changes': len(rows), 'first_observed_sec': rows[0][0],
                      'last_observed_sec': rows[-1][0], 'state_mismatch_seconds': mismatch}
    return lsa, result


def queue_frame(head, spec, rows):
    before = [r for r in rows if str(r[0]) == head['road'] and r[1] == head['lane']
              and r[2] < head['pos_m'] and r[3] <= 5]
    near = [r for r in before if head['pos_m'] - r[2] <= 20]
    downstream = []
    for r in rows:
        if r[3] > 5: continue
        if str(r[0]) == head['road'] and r[1] == head['lane'] and head['pos_m'] <= r[2] <= head['pos_m'] + 20:
            downstream.append(r); continue
        for key in head['post_head_connectors']:
            b = spec['branches'][key]; lane_index = head['lane'] - b['source_lane']
            distance = None
            if str(r[0]) == key and r[1] == lane_index + 1:
                distance = b['from_pos_m'] - head['pos_m'] + r[2]
            elif str(r[0]) == b['target'] and r[1] == b['target_lane'] + lane_index:
                distance = b['from_pos_m'] - head['pos_m'] + b['length_m'] + r[2] - b['target_pos_m']
            if distance is not None and 0 <= distance <= 20: downstream.append(r)
    return {'stopped_before_head': len(before), 'stopped_near_head_20m': len(near),
            'stopped_first20m_after_head': len(downstream),
            'nearest_prehead_stopped_distance_m': min((head['pos_m'] - r[2] for r in before), default=None)}


def analyze(file, geo, program, offset, clocks):
    heads = {h['head']: h for g in geo.values() for h in g['heads']}
    series = {h: {} for h in heads}; events = []; uncertain = []; departures = []
    previous, previous_t = None, None
    stop_history = {}
    head_by_lane = {(h['road'], h['lane']): h for h in heads.values()}
    for t, current in selected_frames(file):
        if previous_t is not None and t - previous_t != 1: raise ValueError('Selected cadence gap')
        rows = list(current.values())
        for key, h in heads.items(): series[key][t] = queue_frame(h, geo[h['road']], rows)
        source = {no: r for no, r in current.items() if str(r[0]) in geo}
        for no, row in source.items():
            if previous is None or no not in previous or previous[no][0] != row[0]:
                # A repeated visit is not a new vehicle. Prior queue witnesses
                # from its earlier source visit must not validate this visit.
                for candidate in geo[str(row[0])]['heads']:
                    stop_history.pop((candidate['head'], no), None)
            h = head_by_lane.get((str(row[0]), row[1]))
            if h and row[3] <= 5 and row[2] < h['pos_m']:
                k = h['head'], no
                old = stop_history.setdefault(k, {'samples': 0, 'nearest_distance_m': math.inf})
                old['samples'] += 1
                old['nearest_distance_m'] = min(old['nearest_distance_m'], h['pos_m'] - row[2])
        if previous is not None:
            for no, old in previous.items():
                road = str(old[0]); new = current.get(no)
                if new is not None and new[0] == old[0] and max(old[2], new[2]) < min(h['pos_m'] for h in geo[road]['heads']) - 1:
                    continue
                rows0 = head_events(geo[road], no, old, new, previous_t, t)
                for event in rows0:
                    if event['kind'] == 'head_crossing':
                        h = heads[event['head']]; a, b = event['lower_sec'], event['upper_sec']
                        green = _union_green_overlap(program, (h['sg'],), a, b, offset)
                        event['guaranteed_green'] = abs(green - (b-a)) < 1e-9 and a >= clocks[h['sg']]['first_observed_sec']
                        event['input_no'] = event['head']  # Reuse SC15 block estimator per physical head.
                        event['physical_resource'] = h['post_head_connectors'][0] if len(h['post_head_connectors']) == 1 else None
                        prior_stop = stop_history.get((h['head'], no), {})
                        event['prior_same_lane_stopped_samples'] = prior_stop.get('samples', 0)
                        event['nearest_prior_stopped_distance_m'] = prior_stop.get('nearest_distance_m')
                        events.append(event)
                    elif event['kind'].startswith('unresolved'):
                        # Conservative gap contamination: unresolved crossing on
                        # a possible source lane is not silently an empty interval.
                        possible = [h['head'] for h in geo[road]['heads']
                                    if h['lane'] in (old[1], new[1] if new and new[0] == old[0] else old[1])
                                    and old[2] < h['pos_m']]
                        uncertain.append({**event, 'possible_heads': possible})
                if new is None or new[0] != old[0]:
                    departures.append({'vehicle_id': no, 'road': road, 'lower_sec': previous_t, 'upper_sec': t,
                                       'to_link': None if new is None else str(new[0]),
                                       'classifications': sorted({e['kind'] for e in rows0})})
        previous, previous_t = source, t
    if previous_t != 5400: raise ValueError('Incomplete selected extract')
    repeats = Counter((e['head'], e['vehicle_id']) for e in events)
    departures_by_id = defaultdict(list)
    for d in departures: departures_by_id[(d['road'], d['vehicle_id'])].append(d)
    for e in events:
        e['repeated_head_vehicle_id'] = repeats[e['head'], e['vehicle_id']] != 1
        later = [d for d in departures_by_id[(str(e['link']), e['vehicle_id'])] if d['upper_sec'] >= e['upper_sec']]
        exit0 = min(later, key=lambda d: d['upper_sec']) if later else None
        branch = None
        if exit0:
            candidates = [k for k,b in geo[str(e['link'])]['branches'].items() if exit0['to_link'] in (k,b['target'])]
            branch = candidates[0] if len(candidates) == 1 else None
        e['observed_subsequent_connector'] = branch
        e['resource_join_verified'] = branch is not None and branch == e['physical_resource']
    gaps = []; summaries = {}; all_blocks = []
    for key, h in heads.items():
        own = sorted([e for e in events if e['head'] == key], key=lambda e: e['linear_estimate_sec'])
        windows = []; start = None
        for t in range(5401):
            green = t < 5400 and program.state_at(t, h['sg'], controller_offset_sec=offset) == 'GREEN'
            if green and start is None: start = t
            if not green and start is not None: windows.append((start, t)); start = None
        head_gaps = []; cycles = []
        for a, b in windows:
            ev = [e for e in own if a <= e['linear_estimate_sec'] < b]
            for ordinal, (prev, cur) in enumerate(zip(ev, ev[1:]), 2):
                times = list(range(math.ceil(prev['upper_sec']), math.floor(cur['lower_sec']) + 1))
                if not prev['guaranteed_green'] or not cur['guaranteed_green']: continue
                q = [series[key][t] for t in times if t in series[key]]
                ambiguity = sum(key in e['possible_heads'] and e['upper_sec'] > prev['lower_sec']
                                and e['lower_sec'] < cur['upper_sec'] for e in uncertain)
                broad = ordinal >= 4 and bool(q) and min(r['stopped_before_head'] for r in q) >= 1
                near = broad and min(r['stopped_near_head_20m'] for r in q) >= 1
                blocked = bool(q) and max(r['stopped_first20m_after_head'] for r in q) > 0
                clean = not ambiguity and not prev['repeated_head_vehicle_id'] and not cur['repeated_head_vehicle_id']
                row = {'input_no': key, 'head': key, 'road': h['road'], 'sg': h['sg'], 'lane': h['lane'],
                       'green_start_sec': a, 'green_end_sec': b, 'departure_ordinal': ordinal,
                       'previous_vehicle_id': prev['vehicle_id'], 'vehicle_id': cur['vehicle_id'],
                       'linear_estimate_headway_sec': cur['linear_estimate_sec'] - prev['linear_estimate_sec'],
                       'lower_headway_sec': max(0., cur['lower_sec'] - prev['upper_sec']),
                       'upper_headway_sec': cur['upper_sec'] - prev['lower_sec'],
                       'all_prehead_queued': broad, 'near20_queued': near,
                       'downstream_stopped_witness': blocked, 'ambiguous_crossing_count': ambiguity,
                       'both_departures_previously_stopped_same_lane': bool(prev['prior_same_lane_stopped_samples'] and cur['prior_same_lane_stopped_samples']),
                       'minimum_nearest_stopped_distance_m': min((r['nearest_prehead_stopped_distance_m'] for r in q if r['nearest_prehead_stopped_distance_m'] is not None), default=None),
                       'maximum_nearest_stopped_distance_m': max((r['nearest_prehead_stopped_distance_m'] for r in q if r['nearest_prehead_stopped_distance_m'] is not None), default=None),
                       'queued_after_third_departure': near and clean and not blocked,
                       'qualified_broad_only': broad and clean and not blocked}
                head_gaps.append(row)
            observed = [series[key][t] for t in range(max(1,a), min(5400,b-1)+1)]
            cycles.append({'start_sec': a, 'end_sec': b, 'resolved_crossings': len(ev),
                           'near20_queue_seconds': sum(r['stopped_near_head_20m'] > 0 for r in observed),
                           'broad_queue_seconds': sum(r['stopped_before_head'] > 0 for r in observed),
                           'downstream_stop_seconds': sum(r['stopped_first20m_after_head'] > 0 for r in observed)})
        crossing_map = {(key, e['vehicle_id']): e for e in own if not e['repeated_head_vehicle_id']}
        blocks, excluded = blocks_from_rows(head_gaps, crossing_map)
        broad_rows = [{**r, 'queued_after_third_departure': r['qualified_broad_only']} for r in head_gaps]
        broad_blocks, broad_excluded = blocks_from_rows(broad_rows, crossing_map)
        confirmed_rows = [{**r, 'queued_after_third_departure': r['qualified_broad_only'] and r['both_departures_previously_stopped_same_lane']} for r in head_gaps]
        confirmed_blocks, confirmed_excluded = blocks_from_rows(confirmed_rows, crossing_map)
        def rates(bs):
            count = sum(b['gap_count'] for b in bs); hi = sum(b['duration_upper_sec'] for b in bs)
            lo = sum(b['duration_lower_sec'] for b in bs); linear = sum(b['linear_estimate_duration_sec'] for b in bs)
            return {'blocks': len(bs), 'gaps': count, 'duration_upper_sec': hi, 'duration_lower_sec': lo,
                    'rate_lower_veh_h': 3600 * count / hi if count and hi > 0 else None,
                    'rate_upper_veh_h': 3600 * count / lo if count and lo > 0 else None,
                    'interpolated_rate_veh_h': 3600 * count / linear if count and linear > 0 else None}
        summaries[key] = {**h, 'head_crossings': len(own), 'guaranteed_green_crossings': sum(e['guaranteed_green'] for e in own),
                          'subsequent_resource_join_verified_crossings': sum(e['resource_join_verified'] for e in own),
                          'repeated_head_vehicle_observations': sum(e['repeated_head_vehicle_id'] for e in own),
                          'same_green_gaps': len(head_gaps), 'startup_excluded_gaps': sum(r['departure_ordinal'] < 4 for r in head_gaps),
                          'broad_queued_gaps': sum(r['all_prehead_queued'] for r in head_gaps),
                          'near20_queued_gaps': sum(r['near20_queued'] for r in head_gaps),
                          'near20_blocked_gaps': sum(r['near20_queued'] and r['downstream_stopped_witness'] for r in head_gaps),
                          'near20_ambiguous_gaps': sum(r['near20_queued'] and r['ambiguous_crossing_count'] > 0 for r in head_gaps),
                          'strict_fit': rates(blocks), 'broad_fit_diagnostic_only': rates(broad_blocks),
                          'broad_fit_with_both_departures_stop_confirmed': rates(confirmed_blocks),
                          'broad_fit_blocks': broad_blocks,
                          'broad_queued_nearest_stop_distance_m': {
                              'min': min((r['minimum_nearest_stopped_distance_m'] for r in head_gaps if r['qualified_broad_only']), default=None),
                              'median_gap_maximum': statistics.median([r['maximum_nearest_stopped_distance_m'] for r in head_gaps if r['qualified_broad_only']]) if broad_blocks or broad_excluded else None,
                              'max': max((r['maximum_nearest_stopped_distance_m'] for r in head_gaps if r['qualified_broad_only']), default=None)},
                          'strict_time_holdout_gap_count': len(excluded), 'broad_time_holdout_gap_count': len(broad_excluded),
                          'strict_holdout_gaps': excluded, 'green_windows': cycles}
        validation = []
        for a,b in HOLDOUTS:
            within = [r for r in head_gaps
                      if crossing_map.get((key,r['previous_vehicle_id']),{}).get('lower_sec', -math.inf) >= a
                      and crossing_map.get((key,r['vehicle_id']),{}).get('upper_sec', math.inf) <= b]
            v_broad, _ = blocks_from_rows([{**r,'queued_after_third_departure':r['qualified_broad_only']} for r in within],crossing_map,holdouts=[])
            v_near, _ = blocks_from_rows(within,crossing_map,holdouts=[])
            validation.append({'start_sec':a,'end_sec':b,
                               'guaranteed_green_crossings':sum(e['guaranteed_green'] and a<=e['lower_sec'] and e['upper_sec']<=b for e in own),
                               'broad_queue_validation':rates(v_broad),'near20_validation':rates(v_near)})
        summaries[key]['held_time_validation'] = validation
        all_blocks += blocks; gaps += head_gaps
    return summaries, events, gaps, all_blocks, uncertain, departures, series


def write_csv(file, rows):
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with file.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys); writer.writeheader(); writer.writerows(rows)


def main():
    started = time.monotonic(); geo, sig, program, offset, controller = geometry()
    lsa, clocks = clock(program, offset)
    source_paths = [Path(__file__), NETWORK, sig, lsa,
                    ROOT / 'diagnostics/audit_sc15_source_discharge.py',
                    ROOT / 'diagnostics/prepare_sc15_service_calibration.py',
                    ROOT / 'diagnostics/selected_signal_sampling_audit.py',
                    ROOT / 'diagnostics/selected_signal_capacity_audit.json']
    pinned = {str(p.relative_to(ROOT)): sha(p) for p in source_paths}
    selected, provenance = extract(geo)
    summaries, events, gaps, blocks, uncertain, departures, series = analyze(selected, geo, program, offset, clocks)
    audit = json.loads((ROOT / 'diagnostics/selected_signal_capacity_audit.json').read_text(encoding='utf-8'))
    head_join = {}
    for key, h in summaries.items():
        rows = [m for m in audit['movements'] if any(str(x['head']) == key for x in m['physical_local_heads_from_pinned_audit'])]
        turns = [m for m in audit['movements'] if m.get('corridor_turn') and m['corridor_turn'].get('connector') in h['post_head_connectors']]
        head_join[key] = {'pinned_authority_members': [{k:m[k] for k in ('movement','phase','kind','beta','final_capacity_veh_h','source_class')} for m in rows],
                          'explicit_corridor_shared_members': [{k:m[k] for k in ('movement','phase','kind','beta','final_capacity_veh_h','corridor_turn')} for m in turns]}
    resource_heads = [k for k,h in summaries.items() if h['road']=='71' and h['sg']=='2']
    resource_green = _union_green_overlap(program,('2',),0,5400,offset)
    known_green = [t for t in range(max(1,int(clocks['2']['first_observed_sec'])),5400)
                   if program.state_at(t,'2',controller_offset_sec=offset)=='GREEN']
    resource_events = [e for e in events if e['head'] in resource_heads and e['guaranteed_green']
                       and e['resource_join_verified'] and not e['repeated_head_vehicle_id']]
    resource = {'connector':'10634','heads':resource_heads,'full_run_native_green_seconds':resource_green,
                'guaranteed_green_and_subsequent_connector_verified_crossings':len(resource_events),
                'unique_vehicle_ids':len({e['vehicle_id'] for e in resource_events}),
                'repeat_visit_vehicle_crossing_intervals':{
                    str(no):[[e['lower_sec'],e['upper_sec']] for e in resource_events if e['vehicle_id']==no]
                    for no,count in Counter(e['vehicle_id'] for e in resource_events).items() if count>1},
                'observed_green_exposure_rate_lower_bound_veh_h':len(resource_events)*3600/resource_green,
                'classification':'throughput lower bound, not saturation fit; full exposure denominator conservatively includes initially unverified LSA seconds',
                'all_lane_broad_queue_green_seconds':sum(all(series[h][t]['stopped_before_head']>0 for h in resource_heads) for t in known_green),
                'queued_lane_count_green_seconds':dict(Counter(sum(series[h][t]['stopped_before_head']>0 for h in resource_heads) for t in known_green)),
                'simultaneous_three_lane_saturation_estimate':None,
                'reason_no_joint_estimate':'Lanes1 and2 have no per-lane fourth-or-later continuously queued qualified gap; distinct-time lane3 evidence cannot identify all3 lanes.'}
    result = {'schema': 'sc1004-head-service-identifiability/v1', 'run': RUN.name, 'seed': 13,
              'scope': 'Offline observed discharge evidence only; no production capacity estimate installed',
              'holdouts_excluded_from_fit_sec': HOLDOUTS, 'seed14_validation': 'pending',
              'controller': controller, 'native_clock': {'program_offset_sec': program.program_offset_sec,
               'cycle_sec': program.cycle_length_sec, 'controller_offset_sec': offset, 'groups': clocks},
              'geometry': geo, 'extraction': provenance, 'heads': summaries, 'model_join': head_join,
              'shared_10634_observed_resource':resource,
              'online_measurement_empty_groups': [g for g in audit['measurement_groups'] if str(g['link']) in ROADS],
              'departure_classes': dict(Counter(k for d in departures for k in d['classifications'])),
              'unresolved_events': uncertain, 'qualified_fit_blocks': blocks,
              'source_sha256': pinned, 'source_changes': [str(p.relative_to(ROOT)) for p in source_paths if sha(p) != pinned[str(p.relative_to(ROOT))]],
              'elapsed_sec': time.monotonic() - started,
              'definitions': {'queue': 'Same physical lane, speed<=5km/h before head; strict subset also within20m, the existing SC15 near-head measure.',
                'headway': 'Both crossing brackets fully native GREEN; second resolved departure ordinal>=4, every intervening integer frame has stopped queue; exclude ambiguous crossing/repeated IDs.',
                'downstream_witness': 'Stopped vehicle on the same lane path within20m downstream of head; witness excluded, no witness does not prove unconstrained receiving.',
                'rates': '3600*sum(gaps)/sum(consecutive-block endpoint duration bounds); one-second measurement interval bounds, not statistical confidence limits.'},
              'limitations': ['No true microscopic receiving-space or conflict/yield reservation is observed. No-stop witness is insufficient to identify unconstrained saturation.',
                'Per-lane rates cannot be summed from different-time samples to claim a simultaneous3-lane resource capacity.',
                'Lane changes at a bracket and unresolved skipped paths are excluded; head crossings and link departures are distinct events.',
                'Future route-choice beta is not used to divide a measured head service. Initial source cohorts are not inferred from destination labels.']}
    if result['source_changes']: raise ValueError('Read-only source changed')
    path('.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    write_csv(path('.head_crossings.csv'), events); write_csv(path('.headways.csv'), gaps)
    write_csv(path('.departures.csv'), departures)
    write_csv(path('.head_frames.csv'), [{'head': h, 'sec': t, **row} for h, frames in series.items() for t, row in frames.items()])
    print(json.dumps({'elapsed_sec': result['elapsed_sec'], 'source_changes': result['source_changes'],
                      'heads': {k: {q:v for q,v in h.items() if q not in ('green_windows','strict_holdout_gaps','broad_fit_blocks')} for k,h in summaries.items()}}, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
