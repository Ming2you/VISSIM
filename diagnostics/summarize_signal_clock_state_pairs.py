"""Summarize explicit completed normal pairs; never discover/select favorable runs."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = {1500: 'Congestion onset', 3300: 'Heavy congestion', 4950: 'Partial western recovery; E8 congested'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pair', action='append', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    evidence = {}
    def read(path):
        path = path.resolve()
        raw = path.read_bytes()
        evidence[path.relative_to(ROOT).as_posix()] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)
    rows = []
    for supplied in args.pair:
        path = supplied.resolve()
        pair = read(path)
        if not all(pair.get(k) for k in ('complete', 'restored', 'source_delta_exactly_reviewed_clock', 'family_manifests_unchanged')):
            raise ValueError('Pair is not completely validated: '+str(path))
        comparison = read(ROOT/pair['result_comparison'] if 'result_comparison' in pair
                          else path.parent/'strict_result_comparison.json')
        if not (comparison['returned_results_exact'] and comparison['execution_environment_equal']
                and comparison['returned_provenance_independently_verified']):
            raise ValueError('Exact result comparison failed')
        members = {}
        for member in pair['members']:
            manifest = read(ROOT/member['manifest'])
            if ('normal_resource_validation' not in manifest or 'read_only_evaluation_trace' in manifest
                    or 'read_only_process_profile' in manifest or not manifest['valid']):
                raise ValueError('Expected completed normal run with exit-only counters')
            if manifest['python_hash_seed'] != {'adapter_and_workers': '20260910', 'explicit_cli': True}:
                raise ValueError('Different execution seed')
            directory = (ROOT/member['manifest']).parent
            action = read(directory/'action.json')
            processes = [read(p) for p in sorted((directory/'resources').glob('*.json'))
                         if not p.name.endswith('.started.json')]
            parent = next(p for p in processes if p['pid'] == manifest['adapter_pid'])
            workers = [p for p in processes if p is not parent]
            members[member['variant']] = {
                'manifest': member['manifest'], 'decision_wall_sec': action['metadata']['decision_wall_sec'],
                'parent_cpu_sec': parent['observed_process_cpu_sec'],
                'worker_cpu_sec_sum': sum(p['observed_process_cpu_sec'] for p in workers),
                'processes': len(processes),
                'parent_peak_MiB': parent['memory']['peak_working_set_bytes']/2**20,
                'worker_peak_MiB_range': [fn(p['memory']['peak_working_set_bytes']/2**20 for p in workers)
                                          for fn in (min, max)],
                'parent_clock_cache': parent['signal_clock_cache'],
                'follower_score': manifest['validated_metadata']['follower_score'],
            }
        before, after = (members[k]['decision_wall_sec'] for k in ('before', 'clock'))
        rows.append({'time': pair['time'], 'state': LABELS[pair['time']], 'members': members,
                     'saved_sec': before-after, 'reduction_percent': 100*(before-after)/before,
                     'exact_returned_results': True, 'pair': path.relative_to(ROOT).as_posix()})
    out = args.out.resolve()
    if not out.is_relative_to(ROOT/'diagnostics') or out.exists():
        raise ValueError('Use a new diagnostics output directory')
    for relative, expected in evidence.items():
        if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest() != expected:
            raise ValueError('Input changed while summarizing: '+relative)
    report = {'schema': 'signal-clock-state-pairs/v1', 'rows': rows, 'input_sha256': evidence,
              'producer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope': 'Same-input head-OFF recorded-state replays. One sequential normal before/after pair per listed state. No traffic improvement or variability estimate from one pair.',
              'limitations': ['Every listed pair is retained; individual state timings are not pooled into a speed claim.',
                              'These head-OFF states do not supply missing late warm head-history.',
                              'Partial western recovery is not whole-network recovery.',
                              'Full local-candidate trace preservation is a separate validation.',
                              'CPU work may be summed, overlapping wall time and memory peaks may not.']}
    out.mkdir(parents=True)
    (out/'summary.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    lines = ['# Signal clock: representative normal replay pairs', '', report['scope'], '',
             '| Recorded time | State | Original s | Cached s | Reduction | Exact returned results |',
             '|---:|---|---:|---:|---:|---|']
    for row in rows:
        m = row['members']
        lines.append(f"| {row['time']} | {row['state']} | {m['before']['decision_wall_sec']:.6f} | {m['clock']['decision_wall_sec']:.6f} | {row['reduction_percent']:.2f}% | PASS |")
    lines += ['', 'Inputs, process resource counters, source-only delta checks and strict comparison evidence are pinned in summary.json.', '',
              *['- '+s for s in report['limitations']]]
    (out/'assessment.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps([{'time': r['time'], 'saved_sec': r['saved_sec'], 'reduction_percent': r['reduction_percent']} for r in rows]))


if __name__ == '__main__':
    main()
