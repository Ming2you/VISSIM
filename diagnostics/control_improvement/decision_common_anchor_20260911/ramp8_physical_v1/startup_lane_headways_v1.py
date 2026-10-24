"""Offline SC1004 queue-rank startup evidence, native seconds 900..1350 only.

No COM/model execution or capacity fitting. Reject short, changing-lane,
interleaved, nonstanding, or censored cohorts before any startup arithmetic.
"""
from collections import Counter
import json
from pathlib import Path
import statistics
import sys
import time
import traceback
import xml.etree.ElementTree as ET

D = Path(__file__).resolve().parent
ROOT = D.parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'reports/20260911_decision_runtime')]
import audit_fw8_rg_meter_response as meters
from diagnostics.validate_native_signal_record import read_ldp_frames

START, END, SC = 900, 1350, 1004
MIN_RANK = 8  # Four initial vehicles plus at least four later queued headways.


def _motion_onset(frames, key, veh, green, end):
    """Two native GREEN samples above 1 km/h, on the initial approach lane."""
    first_high = None
    for sec in range(green, end + 1):
        row = frames[sec].get(veh)
        if row is None or row[:2] != key:
            return {'status': 'rejected', 'reason': 'source_lane_not_retained_before_confirmation',
                    'at_sec': sec, 'observed': row}
        if row[3] > 1:
            if first_high is not None:
                return {'status': 'observed_threshold_proxy',
                        'onset_interval_sec': [first_high - 1, first_high],
                        'confirmation_frame_sec': sec,
                        'motion_latency_midpoint_sec': first_high - green,
                        'motion_latency_sampling_bounds_sec': [first_high - green - 1,
                                                               first_high - green + 1]}
            first_high = sec
        else:
            first_high = None
    return {'status': 'censored',
            'reason': ('insufficient_green_frames_for_confirmation'
                       if first_high is not None or end - green + 1 < 2
                       else 'no_sustained_threshold_crossing_before_green_or_record_end'),
            'observed_through_sec': end, 'unconfirmed_high_frame_sec': first_high}


def lane_audit(run, cached, *, capture_motion=False):
    network = Path(run['provenance']['files']['network']['path'])
    doc = ET.parse(network).getroot()
    heads = {}
    for h in doc.iter('signalHead'):
        sc, sg = map(int, h.get('sg').split())
        if sc == SC and 1 <= sg <= 8:
            key = tuple(map(int, h.get('lane').split()))
            assert key not in heads, 'Ambiguous multiple head per lane'
            heads[key] = (sg, float(h.get('pos')))
    assert {f'{k[0]}:{k[1]}': list(v) for k, v in heads.items()} == cached['head_geometry']
    roads = {k[0] for k in heads}
    connections = {}
    for link in doc.findall('./links/link'):
        src = link.find('fromLinkEndPt')
        if src is not None and int(src.get('lane').split()[0]) in roads:
            road, lane = map(int, src.get('lane').split())
            connections[int(link.get('no'))] = (road, lane, float(src.get('pos')),
                                                  len(link.findall('./lanes/lane')))
    path = run['directory'] / f'vissim_eval/baseline_{SC}_001.ldp'
    native = read_ldp_frames({SC: path}, {SC: list(range(1, 9))}, START, END)
    ldp = native['frames']
    run['pins'][str(path)] = meters.sha(path)
    fzp_stat = run['fzp'].stat()
    reader = meters.IndexedFzp(run['fzp'], max_bytes=80 * 1024 * 1024)
    frames = {}
    try:
        for sec, frame in meters.WINDOWS.frames(reader, START, END):
            frames[sec] = {v: r for v, r in frame.items()
                           if r[0] in roads or r[0] in connections}
    finally:
        reader.handle.close()
    assert run['fzp'].stat().st_size == fzp_stat.st_size
    assert run['fzp'].stat().st_mtime_ns == fzp_stat.st_mtime_ns
    events = {k: [] for k in heads}
    for sec in range(START + 1, END + 1):
        for veh, old in frames[sec - 1].items():
            key = old[:2]
            if key not in heads or old[2] >= heads[key][1]:
                continue
            row = frames[sec].get(veh)
            if row is None:
                continue
            conn = connections.get(row[0])
            method = None
            if row[:2] == key and row[2] >= heads[key][1]:
                method = 'same_lane_head_crossing'
            elif (conn and conn[0] == old[0] and conn[2] >= heads[key][1]
                  and 1 <= row[1] <= conn[3] and conn[1] + row[1] - 1 == old[1]):
                method = 'continuous_connector_same_source_lane'
            if method:
                events[key].append({'vehicle': veh, 'interval_sec': [sec - 1, sec],
                                    'method': method, 'before': old, 'after': row})
    windows = {sg: meters.green_windows(ldp, f'{SC}:{sg}', start=START, end=END)[0]
               for sg in range(1, 9)}
    rows = []
    for key, (sg, pos) in sorted(heads.items()):
        for window in windows[sg]:
            g, end = window['first_native_green_frame_sec'], window['last_native_green_frame_sec']
            result = {'sg': sg, 'link': key[0], 'lane': key[1],
                      'first_green_frame_sec': g, 'last_green_frame_sec': end,
                      'onset_interval_sec': [g - 1, g], 'cohort': [], 'rejections': []}
            rows.append(result)
            if g <= START:
                result['rejections'].append('green_already_active_at_window_start')
                continue
            upstream = sorted(((veh, r) for veh, r in frames[g - 1].items()
                               if r[:2] == key and r[2] < pos), key=lambda x: -x[1][2])
            result['pre_green_upstream_n'] = len(upstream)
            result['pre_green_stopped_lt5_n'] = sum(r[3] < 5 for _, r in upstream)
            cohort = []
            previous_pos = pos
            for veh, row in upstream:
                if row[3] >= 1 or previous_pos - row[2] > 15:
                    break
                cohort.append((veh, row))
                previous_pos = row[2]
            result['standing_contiguous_queue_n'] = len(cohort)
            departures = [e for e in events[key] if g - 1 <= e['interval_sec'][0]
                          and e['interval_sec'][1] <= end]
            first = departures[0] if departures else None
            result['first_cross_interval_after_first_green_frame_sec'] = (
                [x - g for x in first['interval_sec']] if first else None)
            result['initial10s_all_departures_n'] = sum(e['interval_sec'][1] <= g + 10 for e in departures)
            for rank, (veh, initial) in enumerate(cohort, 1):
                matches = [e for e in departures if e['vehicle'] == veh]
                assert len(matches) <= 1
                match = matches[0] if matches else None
                item = {'rank': rank, 'vehicle': veh, 'initial_distance_m': pos - initial[2],
                        'initial_speed_kmh': initial[3], 'crossing': match, 'issues': []}
                if capture_motion:
                    item['motion_onset'] = _motion_onset(frames, key, veh, g, end)
                result['cohort'].append(item)
                until = match['interval_sec'][0] if match else end
                for sec in range(g, until + 1):
                    observed = frames[sec].get(veh)
                    if observed is None:
                        item['issues'].append({'sec': sec, 'reason': 'unobserved_or_left_scope'})
                        break
                    if observed[:2] != key:
                        item['issues'].append({'sec': sec, 'reason': 'lane_or_link_change_before_crossing',
                                               'observed': observed})
                        break
                if not match:
                    item['issues'].append({'reason': 'no_unambiguous_crossing_before_end_of_green'})
            prefix = []
            for item in result['cohort']:
                if item['issues']:
                    break
                prefix.append(item)
            for i, item in enumerate(prefix):
                if (i >= len(departures) or departures[i]['vehicle'] != item['vehicle']
                    or (i and item['crossing']['interval_sec'][1]
                        <= prefix[i - 1]['crossing']['interval_sec'][1])):
                    prefix = prefix[:i]
                    result['rejections'].append('departure_interleave_or_rank_order_ambiguity')
                    break
            result['unambiguous_ordered_prefix_n'] = len(prefix)
            times = [item['crossing']['interval_sec'][1] for item in prefix]
            result['prefix_crossing_end_sample_ages_sec'] = [t - g for t in times]
            result['prefix_headway_endpoint_differences_sec'] = (
                [times[0] - g] + [b - a for a, b in zip(times, times[1:])] if times else [])
            if len(cohort) < MIN_RANK:
                result['rejections'].append('fewer_than_8_initial_standing_contiguous_vehicles')
            if len(prefix) < MIN_RANK:
                result['rejections'].append('fewer_than_8_unambiguous_ranked_queued_departures')
            if end == END:
                result['rejections'].append('terminal_censored_green')
            if len(prefix) >= MIN_RANK:
                # Freeze a common rank horizon at 8 for comparison; retain all ranks separately.
                c4, c8 = times[3], times[7]
                h = (c8 - c4) / 4
                late = [times[i] - times[i - 1] for i in range(4, 8)]
                loss = c4 - g - 4 * h
                result['rank8_probe'] = {
                    'rank4_cross_interval_sec': [c4 - 1, c4],
                    'rank8_cross_interval_sec': [c8 - 1, c8],
                    'later_rank5to8_headway_samples_sec': late,
                    'later_headway_endpoint_mean_sec': h,
                    'later_headway_sampling_bounds_sec': [h - 0.25, h + 0.25],
                    'startup_excess_midpoint_sec': loss,
                    'startup_excess_sampling_bounds_sec': [loss - 2, loss + 2],
                    'retained_unpassed_cohort_after_rank8': len(cohort) - 8,
                    'descriptive_only': True,
                    'caveat': 'Four later headways do not prove stationary saturation or exclude downstream obstruction; bounds are sample-resolution bounds, not confidence intervals.'}
    result = {'name': run['name'], 'head_geometry': cached['head_geometry'],
              'lane_green_windows': rows, 'fzp_bounded_read': reader.selected,
              'fzp_bytes_read': reader.bytes_read, 'native_ldp_coverage_passed': native['native_ldp_frame_coverage_passed']}
    if capture_motion:
        result['motion_capture_method'] = {
            'speed_threshold_kmh_exclusive': 1,
            'consecutive_native_green_frames_required': 2,
            'definition': 'First two consecutive GREEN-frame speeds >1 km/h while continuously observed on the initial approach link/lane; onset is bracketed before the first of those frames.',
            'identity': 'Each motion_onset belongs to its enclosing initial-cohort vehicle, queue rank and initial_distance_m; later crossing exclusions remain separate.',
            'limits': 'Threshold proxy, not driver reaction time, first head crossing, or startup lost time. Confirmation cannot span a lane/link change, missing sample, amber or record end. No connector identity is inferred for motion.',
            'uncertainty': 'Latency uses the native green-onset interval [g-1,g]. Bounds reflect sampling only; an onset overlapping that interval can have a negative lower bound and does not establish event order.'}
    return result


def main():
    output = D / (sys.argv[1] if len(sys.argv) > 1 else 'startup_lane_headways_v1.json')
    if output.exists():
        raise FileExistsError(output)
    tick = time.perf_counter()
    report = {'completed': False, 'arms': {}, 'window_sec': [START, END], 'sc': SC,
              'numeric_calibration_authorized_by_evidence': False,
              'method': {'standing_queue': 'Consecutive upstream vehicles from the head, each speed <1 km/h and front-position gap <=15 m. Sensitivity count at <5 km/h retained separately. Vehicle length/type are not inferred.',
                         'cohort_match': 'Vehicle identity + pre-green lane/rank, continuous observations through crossing, connector source-lane mapping, no interleaved departures or tied/reversed ranks.',
                         'startup_excess': 'C4 - green_onset - 4 * ((C8-C4)/4), with native one-second onset and crossing intervals; never first-cross lag.',
                         'minimum': 'At least 8 initial standing contiguous vehicles and 8 retained ranked departures. This is an audit screen, not proof of saturated flow.',
                         'capacity': 'No capacity rescaling, demand normalization, or fitted controller parameter.',
                         'reference': 'https://ops.fhwa.dot.gov/publications/fhwahop08024/chapter3.htm'}}
    pins = {}
    try:
        source = D / 'fast_np_native_qualification_v1.json'
        cached = meters.read_json(source)['sc1004']
        for path in (Path(__file__), source, Path(meters.__file__), Path(meters.WINDOWS.__file__),
                     ROOT / 'reports/20260911_decision_runtime/audit_nuf_band_native.py',
                     ROOT / 'diagnostics/probe_e8_lane_receiving.py',
                     ROOT / 'diagnostics/validate_native_signal_record.py'):
            pins[str(path)] = meters.sha(path)
        meters.END = END
        for label, name in (('baseline', 'codex_physical8_fw080_u050_open1350_v1'),
                            ('selected', 'codex_physical8_fw080_u050_fastnp_1350_v2')):
            run = meters.load_run(name)
            report['arms'][label] = lane_audit(run, cached[label])
            pins.update(run['pins'])
        report['summary'] = {}
        for label, arm in report['arms'].items():
            rows = arm['lane_green_windows']
            probes = [r for r in rows if 'rank8_probe' in r]
            report['summary'][label] = {'lane_green_windows_n': len(rows),
                'rank8_probes_n': len(probes),
                'sg6_rank8_probes_n': sum(r['sg'] == 6 for r in probes),
                'screen_pass_n': sum(not r['rejections'] for r in rows),
                'rejection_counts': dict(Counter(x for r in rows for x in r['rejections']))}
        report['source_changes'] = [p for p, h in pins.items() if meters.sha(p) != h]
        report['completed'] = not report['source_changes']
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        report['source_sha256'] = pins
        report['wall_sec'] = time.perf_counter() - tick
        with output.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
            stream.write('\n')
    print(json.dumps({k: report.get(k) for k in ('completed', 'error', 'wall_sec', 'summary')}))
    for label, arm in report['arms'].items():
        for r in arm['lane_green_windows']:
            if r['sg'] == 6 or 'rank8_probe' in r:
                print(label, r['sg'], r['link'], r['lane'], r['first_green_frame_sec'],
                      r.get('standing_contiguous_queue_n'), r.get('unambiguous_ordered_prefix_n'),
                      r.get('prefix_crossing_end_sample_ages_sec'), r.get('rank8_probe'), r['rejections'])
    return 0 if report['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
