"""Summarize complete per-process profiles without adding overlapping wall time."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import pstats

ROOT = Path(__file__).resolve().parents[1]
WORKERS = {'_price_worker_green', '_price_worker_vsl', '_price_worker_offset_walk', '_price_worker_phase'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--partial', action='store_true')
    args = parser.parse_args()
    directory = (ROOT/args.directory).resolve()
    manifest_path = directory/'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    complete = manifest.get('valid') is True and manifest.get('process_profile_validation', {}).get('complete') is True
    if not complete and not args.partial:
        parser.error('Complete summary requires validated completed preflight and all profiles')
    profile = directory/'profile'
    starts = list(profile.glob('*.started.json'))
    start_data = [json.loads(p.read_text(encoding='utf-8')) for p in starts]
    pids = {r['pid'] for r in start_data}
    roots = [r['pid'] for r in start_data if r['parent_pid'] not in pids]
    if len(roots) != 1:
        raise ValueError('Profile must contain one adapter process tree')
    adapter_pid = roots[0]
    groups = defaultdict(lambda: defaultdict(lambda: [0, 0., 0.]))
    processes, sources = [], {str(manifest_path.relative_to(ROOT)): digest(manifest_path)}
    for stats_path in sorted(profile.glob('*.pstats')):
        sidecar = stats_path.with_suffix('.json')
        row = json.loads(sidecar.read_text(encoding='utf-8'))
        stats = pstats.Stats(str(stats_path)).stats
        tasks = {name: sum(v[1] for k, v in stats.items() if k[2] == name) for name in WORKERS}
        tasks = {k: v for k, v in tasks.items() if v}
        role = 'adapter' if row['pid'] == adapter_pid else '+'.join(sorted(tasks)) or 'worker_without_task'
        process = {**row, 'role': role, 'task_entries': tasks}
        process['secondary_thread_bootstrap_calls'] = sum(v[1] for k, v in stats.items()
            if k[0].replace('\\', '/').endswith('/threading.py') and k[2] == '_bootstrap')
        process['function_attribution_usable'] = not process['secondary_thread_bootstrap_calls']
        process['area_price_endpoint_calls'] = sum(v[1] for k, v in stats.items()
            if k[0].replace('\\', '/').endswith('/evaluation/controllers/area_runtime.py') and k[2] == 'evaluate_price_point')
        processes.append(process)
        group = 'adapter' if row['pid'] == adapter_pid else 'completed_workers'
        for key, value in stats.items():
            filename = key[0].replace('\\', '/')
            try:
                filename = Path(filename).relative_to(ROOT).as_posix()
            except ValueError:
                pass
            target = groups[group][(filename, key[1], key[2])]
            target[0] += value[1]
            target[1] += value[2]
            target[2] += value[3]
        sources[str(stats_path.relative_to(ROOT))] = digest(stats_path)
        sources[str(sidecar.relative_to(ROOT))] = digest(sidecar)
    functions = {group: sorted([{'file': k[0], 'line': k[1], 'function': k[2],
                    'calls': v[0], 'self_wall_sec': v[1], 'inclusive_wall_sec': v[2]}
                    for k, v in values.items()], key=lambda r: r['self_wall_sec'], reverse=True)
                 for group, values in groups.items()}
    result = {'schema': 'decision-process-profile-summary/v1', 'complete': complete,
              'started_processes': len(starts), 'flushed_processes': len(processes),
              'adapter_pid': adapter_pid,
              'preflight_wall_sec': manifest.get('elapsed_sec'),
              'adapter_decision_wall_sec': manifest.get('validated_metadata', {}).get('decision_wall_sec'),
              'completed_process_cpu_sec': sum(r['process_cpu_sec'] for r in processes),
              'worker_cpu_sec': sum(r['process_cpu_sec'] for r in processes if r['pid'] != adapter_pid),
              'processes': processes, 'functions': functions, 'input_sha256': sources,
              'producer_sha256': digest(Path(__file__)),
              'limits': ['Original v1 sidecar main-thread-only scope is incorrect on this Python 3.12 build; see diagnostics/cprofile_thread_attribution.json.',
                         'Concurrent threads mix cProfile call stacks: adapter caller/self/inclusive attribution must not rank pool overhead.',
                         'Function times use wall clocks, not function CPU clocks; bootstrap absence is only a single-thread screening check.',
                         'Cumulative function times overlap within a process; worker wall times overlap across processes.',
                         'Per-process CPU seconds are additive work, not decision elapsed time.',
                         'This instrumented run is not an unprofiled speed benchmark.',
                         'Repeated invocations are aggregated in pstats; their individual intervals are not reconstructed.']}
    output = directory/('profile_summary.json' if complete else 'profile_summary_partial.json')
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('processes', 'functions', 'input_sha256', 'limits')}, indent=2))


if __name__ == '__main__':
    main()
