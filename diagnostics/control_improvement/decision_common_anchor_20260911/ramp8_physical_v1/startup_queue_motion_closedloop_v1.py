"""One completed closed-loop FZP window; reuse saved baseline motion evidence."""
from collections import Counter
import json
from pathlib import Path
import sys
import time
import traceback

D = Path(__file__).resolve().parent
sys.path.insert(0, str(D))
import startup_queue_motion_v1 as motion


def main():
    output = D / (sys.argv[1] if len(sys.argv) > 1 else 'startup_queue_motion_closedloop_v1.json')
    if output.exists():
        raise FileExistsError(output)
    tick = time.perf_counter()
    lanes = motion.lanes
    pins = {}
    report = {'completed': False, 'window_sec': [900, 1350],
        'baseline_fzp_reread': False, 'native_or_model_execution': False,
        'scope': 'Completed closed-loop v3, SC1004 motion proxies and qualification road balances. Baseline motion is reused from its completed saved JSON; no baseline FZP read.',
        'limitations': ['Motion is a two-consecutive-GREEN-frame speed>1 km/h threshold proxy, not reaction time or fitted startup loss. Sampling-only latency bounds are retained.',
            'Compare equal initial ranks on identical source lanes. Queue size, red duration, spacing, arrivals and downstream conditions are not randomized.',
            'Whole initial-cohort clearance excludes later arrivals. Terminal green, missing observations and source-lane loss remain censored/rejected.',
            'Road exits aggregate all movements on that road; they are not equivalent to an individual SG service count. First appearances and observed link entries remain distinct.',
            'No queue-proportional delay coefficient or causal explanation of aggregate TTT/TTD changes is inferred.'],
        'calibration_supported': False}
    try:
        qualification_path = D / 'fast_np_closedloop_qualification_v1.json'
        baseline_path = D / 'startup_queue_motion_v1.json'
        qualification = lanes.meters.read_json(qualification_path)
        baseline = lanes.meters.read_json(baseline_path)
        assert qualification['completed'] and not qualification['source_changes']
        assert qualification['native']['completed'] and qualification['native']['execution_passed']
        assert baseline['completed'] and not baseline['source_changes']
        cached = qualification['sc1004']
        assert baseline['arms']['baseline']['head_geometry'] == cached['baseline']['head_geometry']
        assert baseline['arms']['baseline']['fzp_bounded_read'] == cached['baseline']['fzp_bounded_read']
        for p in (Path(__file__), Path(motion.__file__), Path(lanes.__file__),
                  qualification_path, baseline_path, Path(lanes.meters.__file__),
                  Path(lanes.meters.WINDOWS.__file__),
                  lanes.ROOT / 'diagnostics/probe_e8_lane_receiving.py',
                  lanes.ROOT / 'diagnostics/validate_native_signal_record.py'):
            pins[str(p)] = lanes.meters.sha(p)
        lanes.meters.END = 1350
        run = lanes.meters.load_run('codex_physical8_fw080_u050_fastnp_closedloop1350_v3')
        audit = lanes.lane_audit(run, cached['closedloop'], capture_motion=True)
        pins.update(run['pins'])
        print(json.dumps({'closedloop_bounded_fzp_read_finished': True,
                          'bytes_read': audit['fzp_bytes_read']}), flush=True)
        report['closedloop_motion'] = audit
        report['baseline_motion_reference'] = {'path': str(baseline_path),
            'sha256': pins[str(baseline_path)], 'arm': 'baseline',
            'head_geometry_and_bounded_native_rows_match_qualification': True}
        report['lane_summaries'] = {
            'baseline': baseline['lane_summaries']['baseline'],
            'closedloop': motion.summarize('closedloop', audit)}
        report['same_rank_queue_size_comparisons'] = {}
        for key in ('SG6:52:L1', 'SG3:66:L4'):
            report['same_rank_queue_size_comparisons'][key] = [r
                for arm in report['lane_summaries'].values()
                for r in arm[key]['episodes'] if r.get('first4_same_rank_motion')]
        statuses = Counter()
        reasons = Counter()
        checked = 0
        censored = []
        for row in audit['lane_green_windows']:
            if row['last_green_frame_sec'] == 1350:
                censored.append({k: row.get(k) for k in ('sg', 'link', 'lane',
                    'first_green_frame_sec', 'last_green_frame_sec', 'standing_contiguous_queue_n',
                    'unambiguous_ordered_prefix_n', 'rejections')})
            for c in row['cohort']:
                m = c['motion_onset']
                statuses[m['status']] += 1
                if m.get('reason'):
                    reasons[m['reason']] += 1
                if m['status'] == 'observed_threshold_proxy':
                    lo, hi = m['onset_interval_sec']
                    g = row['first_green_frame_sec']
                    assert hi - lo == 1 and m['confirmation_frame_sec'] == hi + 1
                    assert g <= hi < row['last_green_frame_sec']
                    assert m['motion_latency_sampling_bounds_sec'] == [lo - g, hi - (g - 1)]
                    checked += 1
        report['closedloop_motion_validation'] = {'observed_interval_checks_passed': checked,
            'status_counts': statuses, 'reject_censor_reason_counts': reasons,
            'terminal_green_lanes': censored}
        report['road_balances_from_qualification'] = {}
        for arm, corridor in qualification['corridor_52_66_71'].items():
            assert corridor['all_link_frame_balances_zero']
            roads = {}
            for road, row in corridor['links'].items():
                item = {k: row.get(k, 0) for k in ('initial_n', 'observed_entries',
                    'first_appearances', 'observed_exits', 'unexplained_absences', 'end_n',
                    'stopped_vehicle_seconds_lt5', 'lane_changes')}
                assert (item['initial_n'] + item['observed_entries'] + item['first_appearances']
                        - item['observed_exits'] - item['unexplained_absences'] == item['end_n'])
                roads[road] = item
            report['road_balances_from_qualification'][arm] = roads
        report['source_changes'] = [p for p, h in pins.items() if lanes.meters.sha(p) != h]
        report['completed'] = not report['source_changes']
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        report['source_sha256'] = pins
        report['wall_sec'] = time.perf_counter() - tick
        with output.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
            stream.write('\n')
    print(json.dumps({k: report.get(k) for k in ('completed', 'wall_sec', 'source_changes', 'error')}))
    print(json.dumps(report.get('closedloop_motion_validation')))
    for key, episodes in report.get('same_rank_queue_size_comparisons', {}).items():
        for r in episodes:
            print(key, r['arm'], r['green_frame_sec'], 'queue', r['initial_queue_n'],
                  'tail_m', round(r['tail_front_distance_to_head_m'], 2),
                  'rank1to4', [c['motion'].get('motion_latency_midpoint_sec', c['motion']['status'])
                               for c in r['first4_same_rank_motion']],
                  'tail_motion', r['last_initial_rank_motion'].get('motion_latency_midpoint_sec',
                                                                  r['last_initial_rank_motion']['status']),
                  'tail_cross', r['last_initial_cohort_crossing_endpoint_age_sec'])
    return 0 if report['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
