"""Read the four completed same-seed normal runs; never mix trace timings."""
import hashlib
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
RUNS = {
    'before': ['043809307925', '044114270062'],
    'clock': ['044656061078', '044928190811'],
}


def main():
    evidence, groups = {}, {}
    def read(path):
        raw = path.read_bytes()
        evidence[path.relative_to(ROOT).as_posix()] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)
    for name, stamps in RUNS.items():
        rows = []
        for stamp in stamps:
            directory = ROOT / ('diagnostics/area_production_preflight/'
                                'wu-link_t900_beta300_20260910T' + stamp + 'Z')
            manifest, action = read(directory/'manifest.json'), read(directory/'action.json')
            assert manifest['valid'] and manifest['source_unchanged'] and manifest['inputs_unchanged']
            assert manifest['python_hash_seed'] == {'adapter_and_workers': '20260910', 'explicit_cli': True}
            assert 'normal_resource_validation' in manifest
            assert not any(k in manifest for k in ('read_only_process_profile', 'read_only_evaluation_trace'))
            processes = [read(p) for p in sorted((directory/'resources').glob('*.json'))
                         if not p.name.endswith('.started.json')]
            parent = next(p for p in processes if p['pid'] == manifest['adapter_pid'])
            workers = [p for p in processes if p is not parent]
            row = {'directory': directory.relative_to(ROOT).as_posix(),
                   'decision_wall_sec': action['metadata']['decision_wall_sec'],
                   'parent_cpu_sec': parent['observed_process_cpu_sec'],
                   'worker_cpu_sec_sum': sum(p['observed_process_cpu_sec'] for p in workers),
                   'processes': len(processes),
                   'parent_peak_MiB': parent['memory']['peak_working_set_bytes']/2**20,
                   'worker_peak_MiB_range': [fn(p['memory']['peak_working_set_bytes']/2**20 for p in workers)
                                             for fn in (min, max)],
                   'parent_clock_cache': parent['signal_clock_cache']}
            if name == 'clock':
                comparison = read(directory/'strict_result_comparison.json')
                assert comparison['returned_results_exact'] and comparison['execution_environment_equal']
                assert comparison['returned_provenance_independently_verified']
                row['strict_returned_result_comparison'] = 'PASS'
                row['worker_clock_hits'] = sum(p['signal_clock_cache']['clock_hits'] for p in workers)
                row['worker_clock_misses'] = sum(p['signal_clock_cache']['clock_misses'] for p in workers)
            rows.append(row)
        values = [r['decision_wall_sec'] for r in rows]
        groups[name] = {'runs': rows, 'n': len(values), 'mean_sec': statistics.mean(values),
                        'sample_stdev_sec': statistics.stdev(values), 'min_sec': min(values), 'max_sec': max(values)}
    before, after = (groups[k]['mean_sec'] for k in ('before', 'clock'))
    report = {'schema': 'signal-clock-normal-performance/v1', 'groups': groups,
              'mean_saved_sec': before-after, 'mean_reduction_percent': 100*(before-after)/before,
              'input_sha256': evidence,
              'producer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope': 'One actual recorded900 state, beta300, cold v4 head-resource adoption, same explicit hash seed. Two normal sequential repetitions per implementation. No profiler/trace timing included.',
              'limitations': ['Two repeats do not establish a tail-latency guarantee; one optimized run remains above150s.',
                             'Returned results and CSV match exactly except individually checked timing/provenance fields. Complete rejected local-candidate equivalence remains pending bounded-memory tracing.',
                             'Onset/heavy/partial-recovery paired replays and matched VISSIM validation remain pending.',
                             'Worker CPU is additive work; overlapping wall time and peak-memory values are not summed.']}
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == h for p, h in evidence.items())
    target = ROOT/'diagnostics/signal_clock_performance_v1'
    target.mkdir(exist_ok=True)
    (target/'normal_summary.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    lines = ['# Signal clock cache: first normal decision comparison', '',
             'The same recorded900 input completed with the same commands, prices, objective components and returned residual/state fields. This is a computational improvement, not evidence of improved traffic or an all-lever equilibrium.', '',
             '| Implementation | Individual normal seconds | Mean | Sample SD |',
             '|---|---|---:|---:|']
    for name, group in groups.items():
        values = ', '.join(f"{r['decision_wall_sec']:.6f}" for r in group['runs'])
        lines.append(f"| {name} | {values} | {group['mean_sec']:.3f} | {group['sample_stdev_sec']:.3f} |")
    lines += ['', f'Mean reduction: **{before-after:.3f}s ({100*(before-after)/before:.2f}%)**. One optimized run still took150.172396s; this is not a robust sub150s result.', '',
              'Both pairs use the same Python hash seed20260910, beta300, previous750 action, full candidate configuration bytes and35 processes. Only signal_actuation_contract.py changed in the137-source candidate manifest. Normal runs retain exit-only resource counters. The earlier180.057479/172.496245/172.071095 timings with inherited random hash seeds remain separate evidence.', '',
              'The cache reuses validated immutable signal clocks and exact integer-event interval fractions. It preserves the original vector validation, millisecond serialization, VBS FMod expression, amber/all-red and absolute-time boundaries.12 focused tests,19,763 exact comparisons and actual fresh-worker aliases passed after application. The generated patch initially used CRLF; its source gate rejected that representation, then this module alone was normalized to the independently pinned reviewed LF bytes.', '',
              'The full JSON comparator retains every result field, signed zero and type distinctions. Its10 explicit timing/provenance paths include the relocated but byte-identical tuning file and its derived execution fingerprint; both fingerprints are independently recomputed. No numerical tolerance was added. The old unmodified-baseline1ULP diagnostic FAIL remains preserved. Source revisions require separate review and are never inferred equivalent from equal outputs.', '',
              '## Remaining verification', '', *['- '+x for x in report['limitations']], '',
              'The original v2 local trace was stopped at about8.2GB parent working set before completion. Its invalid manifest is retained. A disk-backed tracer is being checked; until that succeeds, identical returned results must not be described as equality of every rejected candidate.', '',
              'All source/input hashes, per-process CPU and per-process peak memory, bounded cache sizes and exact artifact paths are in normal_summary.json.']
    (target/'assessment.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('mean_saved_sec', 'mean_reduction_percent')}))


if __name__ == '__main__':
    main()
