"""Completed-run motion proxies from existing bounded lane/queue audit only."""
from collections import Counter
import json
from pathlib import Path
import sys
import time
import traceback

D = Path(__file__).resolve().parent
sys.path.insert(0, str(D))
import startup_lane_headways_v1 as lanes


def summarize(arm, audit):
    groups = {}
    for row in audit['lane_green_windows']:
        key = f"SG{row['sg']}:{row['link']}:L{row['lane']}"
        group = groups.setdefault(key, {'episodes': [], 'motion_status_counts': Counter()})
        cohort = row['cohort']
        if not cohort:
            group['episodes'].append({'arm': arm, 'green_frame_sec': row['first_green_frame_sec'],
                'initial_queue_n': row.get('standing_contiguous_queue_n'),
                'queue_observation': 'empty' if 'standing_contiguous_queue_n' in row else 'left_censored'})
            continue
        statuses = Counter(c['motion_onset']['status'] for c in cohort)
        group['motion_status_counts'].update(statuses)
        first, last = cohort[0]['motion_onset'], cohort[-1]['motion_onset']
        complete = row['unambiguous_ordered_prefix_n'] == len(cohort)
        ages = row['prefix_crossing_end_sample_ages_sec']
        extent = [c['initial_distance_m'] for c in cohort]
        item = {'arm': arm, 'green_frame_sec': row['first_green_frame_sec'],
            'initial_queue_n': len(cohort), 'tail_front_distance_to_head_m': max(extent),
            'first_to_last_front_span_m': max(extent) - min(extent),
            'rank1_motion': first, 'last_initial_rank_motion': last,
            'motion_status_counts': statuses,
            'first4_same_rank_motion': [{'rank': c['rank'], 'vehicle': c['vehicle'],
                'initial_distance_m': c['initial_distance_m'], 'motion': c['motion_onset']}
                for c in cohort[:4]],
            'first_cohort_crossing_endpoint_age_sec': ages[0] if ages else None,
            'last_initial_cohort_crossing_endpoint_age_sec': ages[-1] if complete else None,
            'all_initial_cohort_crossings_retained': complete,
            'original_departure_screen_rejections': row['rejections']}
        if first['status'] == last['status'] == 'observed_threshold_proxy':
            f, t = first['onset_interval_sec'], last['onset_interval_sec']
            item['rank1_to_tail_motion_spread_midpoint_sec'] = t[1] - f[1]
            item['rank1_to_tail_motion_spread_sampling_bounds_sec'] = [t[0] - f[1], t[1] - f[0]]
        group['episodes'].append(item)
    return groups


def main():
    output = D / (sys.argv[1] if len(sys.argv) > 1 else 'startup_queue_motion_v1.json')
    if output.exists():
        raise FileExistsError(output)
    tick = time.perf_counter()
    report = {'completed': False, 'window_sec': [900, 1350], 'arms': {}, 'lane_summaries': {},
        'scope': 'Completed baseline and selected replay only, SC1004, seed13. Native motion-threshold proxies are distinct from reaction time, stopbar passage, startup lost time and initial-cohort clearance.',
        'calibration_supported': False,
        'limits': ['Motion latency is green-onset to first sustained >1 km/h threshold proxy; two consecutive native GREEN frames must remain on the original approach lane.',
            'Intervals describe native1 s sampling only. Negative lower bounds when green and motion intervals overlap do not identify event ordering.',
            'Compare rank1 with rank1, rank2 with rank2, etc. Comparing tail vehicles at different ranks alone confounds queue length with rank.',
            'No imposed linearity, regression, causal queue-length effect, capacity rescaling or controller delay calibration.',
            'Different arms/times have different red durations, arrivals, spacings, vehicle mixtures and downstream conditions. Six episodes per main lane remain a small dependent sample.'],
        'recommended_followup': 'Apply the same evidence fields to the completed initial closed-loop run; retain source-lane loss, terminal censoring, rank, physical position and downstream restrictions.'}
    pins = {}
    try:
        source = D / 'fast_np_native_qualification_v1.json'
        cached = lanes.meters.read_json(source)['sc1004']
        for p in (Path(__file__), Path(lanes.__file__), source, Path(lanes.meters.__file__),
                  Path(lanes.meters.WINDOWS.__file__),
                  lanes.ROOT / 'diagnostics/probe_e8_lane_receiving.py',
                  lanes.ROOT / 'diagnostics/validate_native_signal_record.py'):
            pins[str(p)] = lanes.meters.sha(p)
        lanes.meters.END = 1350
        for arm, name in (('baseline', 'codex_physical8_fw080_u050_open1350_v1'),
                          ('selected', 'codex_physical8_fw080_u050_fastnp_1350_v2')):
            run = lanes.meters.load_run(name)
            audit = lanes.lane_audit(run, cached[arm], capture_motion=True)
            report['arms'][arm] = audit
            report['lane_summaries'][arm] = summarize(arm, audit)
            pins.update(run['pins'])
            print(json.dumps({'arm': arm, 'bounded_fzp_read_finished': True,
                              'bytes_read': audit['fzp_bytes_read']}), flush=True)
        report['same_rank_queue_size_comparisons'] = {}
        for key in ('SG6:52:L1', 'SG3:66:L4'):
            episodes = [r for arm in report['lane_summaries'].values()
                        for r in arm[key]['episodes'] if r.get('first4_same_rank_motion')]
            report['same_rank_queue_size_comparisons'][key] = sorted(episodes,
                key=lambda r: (r['initial_queue_n'], r['arm'], r['green_frame_sec']))
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
    for key, episodes in report.get('same_rank_queue_size_comparisons', {}).items():
        for r in episodes:
            print(key, r['arm'], r['green_frame_sec'], 'queue', r['initial_queue_n'],
                  'extent', round(r['tail_front_distance_to_head_m'], 2),
                  'motion1to4', [c['motion'].get('motion_latency_midpoint_sec', c['motion']['status'])
                                for c in r['first4_same_rank_motion']],
                  'tail_motion', r['last_initial_rank_motion'].get('motion_latency_midpoint_sec',
                                                                  r['last_initial_rank_motion']['status']),
                  'last_cross', r['last_initial_cohort_crossing_endpoint_age_sec'])
    return 0 if report['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
