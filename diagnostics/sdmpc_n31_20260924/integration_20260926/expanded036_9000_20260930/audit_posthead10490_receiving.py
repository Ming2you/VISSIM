"""Retrospective point occupancy and isolated post-head accounting; no forecasts."""
import csv
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path

E = Path(__file__).resolve().parent
I = E.parent
L = E / 'loss_onset2250'
O = L / 'posthead10490_receiving'
D = Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
O.mkdir(exist_ok=True)
assert not (O / 'verification.json').exists(), 'Preserve completed diagnostic'
pins = {}


def raw(path):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    assert str(path) not in pins or pins[str(path)] == digest
    pins[str(path)] = digest
    return data


def read(path):
    data = raw(path)
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def save(name, value):
    (O / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def close(a, b):
    assert abs(a - b) < 1.e-7, (a, b)


def fluid_replay(initial_due, head_events, travel, resources):
    """Hold saved receiving budgets fixed; replace only the head input schedule.

    This is an isolated accounting diagnostic. Changed merges do NOT update the
    mainline, hence this is not a self-consistent autonomous plant prediction.
    """
    pending = list(initial_due) + [(t + travel, n) for t, n in head_events]
    supplied = sum(n for _, n in pending)
    queue = merged = unused = 0.
    for row in resources:
        t = row['end_sec']
        queue += sum(n for due, n in pending if due <= t)
        pending = [(due, n) for due, n in pending if due > t]
        flow = min(queue, row['available_veh'])
        queue -= flow
        merged += flow
        unused += row['available_veh'] - flow
    travelling = sum(n for _, n in pending)
    close(supplied, merged + queue + travelling)
    return dict(merge=merged, end_post=queue + travelling, end_eligible=queue,
                end_travelling=travelling, unused_receiving=unused)


save('protocol.json', dict(scope='Finalize the already explored two-window receiving diagnosis',
    prospective=False, windows=[[2250, 2400], [3600, 3750]],
    full_forecasts=0, fit=0, native_runs=0, fzp_scans=0, live_monitoring=0,
    questions=['Does lower mainline point flow mean less occupied time?',
               'Does the remaining posthead error disappear with the actual head input?',
               'Are measured point-clear gaps sufficient to explain retained ramp stock?'],
    limitations=['Actual future MER is retrospective evidence, never an autonomous input.',
                 'Conditional replays hold receiving budgets or measured point-clear gaps fixed.',
                 'Point gaps 1.4m before merge are not guaranteed downstream receiving space.',
                 'No coefficient selection, objective change, or model adoption.']))

catalog = list(csv.DictReader(raw(I / 'selected/obs150/obs150_detectors_v2.csv').decode('utf-8-sig').splitlines()))
detectors = [r for r in catalog if r['dcp_no'] in ('960238', '960239', '960240')]
assert len(detectors) == 3
detectors.sort(key=lambda r: int(r['lane']))
assert all(r['link'] == '119' and r['role'] == 'through' and r['ref'] == '10483' for r in detectors)
point = float(detectors[0]['pos'])
geometry_audit = read(L / 'eight_ramp_first150/merge_lane_10490.json')
merge = geometry_audit['native_connector_target']
assert merge['lane'] == '119 1'
distance_to_merge = float(merge['pos']) - point
assert 0 < distance_to_merge < 2
ref = read(I / 'baseline_reproduction_20260929/cellwise_calibration/expanded_joint/eval_036/reference_config.json')
node = ref['freeway']['physical_ramp_receiving_nodes']['RM_C10490']
tc, tf = node['critical_gap_sec'], node['followup_sec']
assert tc == tf == 1.5
timing = read(L / 'head10490_timing/verification.json')
for p in (I / 'selected/network/native_seed29.inpx',
          I / 'baseline_reproduction_20260929/cellwise_calibration/coupled_expanded_joint/candidate_config.json',
          L / 'head10490_timing/candidate_config.json',
          Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')):
    raw(p)

summaries = {}
lane_rows = []
pair_rows = []
boundary_exclusions = []
for start in (2250, 3600):
    stop = start + 150
    states = {t: read(D / f'state_{t:06d}.json') for t in (start, stop, stop + 150)}
    frames = {}
    for t in (start, stop):
        spec = states[t]['obs150']['frames']['current']
        frames[t] = read(D / spec['path'])
        assert pins[str(D / spec['path'])] == spec['sha256']
        assert frames[t]['complete'] and frames[t]['time_s'] == t
    events = []
    for t, s in states.items():
        spec = s['obs150']['mer']
        data = raw(D / spec['chunk'])
        assert pins[str(D / spec['chunk'])] == spec['chunk_sha256']
        events.extend(json.loads(line) for line in data.decode('utf-8').splitlines())
    assert len({r[0] for r in events}) == len(events)
    pairs = {}
    for r in events:
        if r[1] not in (960238, 960239, 960240):
            continue
        item = pairs.setdefault((r[1], r[4]), {})
        for i, name in ((2, 'entry'), (3, 'exit')):
            if r[i] is not None:
                assert name not in item or item[name] == r[i]
                item[name] = r[i]
        if r[2] is not None:
            item['entry_speed_kmh'] = r[6]
    clear_lane1 = None
    for det in detectors:
        dcp, lane = int(det['dcp_no']), int(det['lane'])
        selected = [(vid, p) for (n, vid), p in pairs.items() if n == dcp and
                    p.get('entry', -math.inf) < stop and p.get('exit', math.inf) > start]
        assert all('entry' in p and 'exit' in p for _, p in selected), 'Censored point interval'
        entries = [p for (n, _), p in pairs.items() if n == dcp and start <= p.get('entry', -1) < stop]
        n = len(entries)
        key = det['dcm_no']
        close(n, states[stop]['obs150']['detectors'][key])
        close(n, states[stop]['obs150']['detectors_cum'][key] - states[start]['obs150']['detectors_cum'][key])
        for t in (start, stop):
            mer_ids = {vid for (n0, vid), p in pairs.items() if n0 == dcp and
                       p.get('entry', -math.inf) <= t < p.get('exit', math.inf)}
            frame_ids = {v[0] for v in frames[t]['vehicles'] if v[1] == 119 and v[2] == lane and
                         v[3] - v[5] <= point <= v[3]}
            assert mer_ids <= frame_ids, (t, lane, mer_ids, frame_ids)
            # The point precedes the ramp merge by only1.4m. A ramp vehicle's
            # rear can cover it even though its front never crosses the point.
            # Preserve this observed incompleteness; do NOT fill its occupancy
            # interval from a single frame or call the point's gaps physical gaps.
            for vid in frame_ids - mer_ids:
                v = next(v for v in frames[t]['vehicles'] if v[0] == vid)
                head = [r[2] for r in events if r[1] == 960219 and r[4] == vid and r[2] is not None and r[2] < t]
                assert len(head) == 1 and lane == 1 and v[3] >= float(merge['pos'])
                assert not any(n == dcp and v_id == vid for n, v_id in pairs)
                boundary_exclusions.append(dict(time=t, lane=lane, vehicle=vid,
                    last_ramp_head_sec=head[0], front_m=v[3], rear_m=v[3]-v[5],
                    point_m=point, speed_kmh=v[4],
                    classification='Ramp front entered downstream of point; rear overlaps point without entry/exit record'))
        intervals = sorted((max(start, p['entry']), min(stop, p['exit'])) for _, p in selected)
        cursor = start
        gaps = []
        for a, b in intervals:
            assert b >= a >= cursor - 1.e-8, 'Overlapping same-lane point occupancy'
            if a > cursor:
                gaps.append((cursor, a))
            cursor = b
        if cursor < stop:
            gaps.append((cursor, stop))
        occupied = sum(b - a for a, b in intervals)
        close(occupied + sum(b - a for a, b in gaps), 150)
        slots = [a + tc + j * tf for a, b in gaps if b - a >= tc
                 for j in range(1 + math.floor((b - a - tc + 1.e-9) / tf))]
        q = n * 24.
        poisson = q * math.exp(-q * tc / 3600.) / -math.expm1(-q * tf / 3600.) / 24. if q else 150. / tf
        lane_rows.append(dict(start=start, stop=stop, lane=lane, dcp=dcp, entries=n,
            occupied_sec=occupied, occupancy_percent=occupied / 1.5,
            median_entry_speed_kmh=statistics.median(p['entry_speed_kmh'] for p in entries),
            median_completed_point_dwell_sec=statistics.median(p['exit'] - p['entry'] for _, p in selected),
            poisson_opportunities_veh=poisson, measured_clear_slot_count=len(slots),
            longest_clear_sec=max(b - a for a, b in gaps),
            detector_count_verified=True,
            unrecorded_ramp_body_at_window_boundary=[x for x in boundary_exclusions if start <= x['time'] <= stop and x['lane'] == lane]))
        pair_rows.extend(dict(start=start, dcp=dcp, lane=lane, vehicle=vid, **p) for vid, p in selected)
        if lane == 1:
            clear_lane1 = slots
    cp = L / f'city_path/{start}_ps_all8_geotimecandidate'
    initial = read(cp / 'ramp_initial.json')['buffers']['RM_C10490']
    trace = read(cp / 'trace.json.gz')
    meta = initial['metadata']
    travel = meta['post_head_travel_sec']
    due = [(start + (meta['length_m'] - p) / meta['posthead_travel_speed_kmh'] * 3.6, 1.)
           for p, _, _ in meta['initial_cohorts'] if p > meta['head_position_m']]
    resources = [r for r in trace['resources'] if r['kind'] == 'physical_ramp_merge_physical_receiving'
                 and r['resource'] == 'RM_C10490' and r['end_sec'] <= stop]
    assert len(resources) == 150
    model_heads = [(r['end_sec'], r['accepted_total_veh']) for r in trace['resources'] if
                   r['kind'] == 'physical_ramp_head_service' and r['resource'] == 'RM_C10490:0' and r['end_sec'] <= stop]
    native_heads = [(r[2], 1.) for r in events if r[1] == 960219 and r[2] is not None and start <= r[2] < stop]
    assert len({t for t, _ in native_heads}) == len(native_heads)
    close(len(native_heads), timing['rows'][str(start)]['native']['head'])
    snapshot = trace['ramp_snapshots'][0]['buffers']['RM_C10490']
    parity = fluid_replay(due, model_heads, travel, resources)
    close(parity['merge'], snapshot['cumulative_merge_veh'])
    close(parity['end_post'], snapshot['downstream_travelling_veh'] + snapshot['merge_ready_veh'])
    conditioned = fluid_replay(due, native_heads, travel, resources)
    quantized = fluid_replay(due, [(math.ceil(t), n) for t, n in native_heads], travel, resources)
    slot_resources = [dict(end_sec=t, available_veh=1.) for t in clear_lane1]
    # Final zero-budget tick advances remaining travelling stock to the end.
    slot_resources.append(dict(end_sec=stop, available_veh=0.))
    clear_replay = fluid_replay(due, native_heads, travel, slot_resources)
    native_post = sum(v[1] == 10490 and v[3] > meta['head_position_m'] for v in frames[stop]['vehicles'])
    native_merge = len(due) + len(native_heads) - native_post
    close(native_merge, 37 if start == 2250 else 32)
    summaries[str(start)] = dict(native_head=len(native_heads), initial_post=len(due),
        native_merge_from_conservation=native_merge, native_end_post=native_post,
        model_posthead_free_travel_sec=travel,
        saved_model_receiving_budget_veh=sum(r['available_veh'] for r in resources),
        autonomous_saved_model=parity,
        conditional_actual_head_fixed_saved_receiving=conditioned,
        conditional_actual_head_ceil_to_second=quantized,
        conditional_actual_head_measured_point_clear_slots=clear_replay,
        conditional_results_are_not_autonomous=True)

for path, digest in pins.items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
save('verification.json', dict(status='complete_diagnostic_only', goal='ACTIVE/NOT_QUALIFIED',
    distance_point_to_merge_m=distance_to_merge, tc_sec=tc, tf_sec=tf, windows=summaries,
    lanes=lane_rows, boundary_exclusions=boundary_exclusions, pins=pins, input_files_unchanged=True,
    full_forecasts=0, fit=0, native_runs=0, fzp_scans=0, live_monitoring=0,
    caveats=['Slots use the existing1.5s critical/followup times on observed clear intervals; this changes the gap definition.',
             'They are descriptive opportunities, not a calibrated or valid physical capacity bound.',
             'Point-clear slots omit ramp bodies entering downstream of the point and do not enforce downstream space, relative speed, yielding, or lane changes.',
             'Fixed-receiving replay is not self-consistent with its changed merges; it only isolates head-input sufficiency.',
             'Completed point-dwell pairs overlap the window; occupancy time is clipped to the window.',
             'Window edges truncate clear intervals; no time outside the evaluation window is rewarded.',
             'This local diagnosis does not identify the cause or counterfactual benefit of the full9000 policy.']))
for name, rows in (('lane_point_summary.csv', lane_rows), ('point_entry_exit_pairs.csv', pair_rows)):
    with (O / name).open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
print(json.dumps(dict(windows=summaries, lane1=[r for r in lane_rows if r['lane'] == 1]), ensure_ascii=False))
