"""Execute the canonical VBS/adapter/writer with fake COM, then compare commands."""
import csv
import argparse
import hashlib
import json
from pathlib import Path

from diagnostics.test_profile_runner_invocation import ProfileRunnerInvocationTests
from diagnostics.run_area_production_preflight import hashes

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'diagnostics/fixed_beta300v3_profile_invocation_v1'
PROFILE = ROOT/'diagnostics/fixed_beta300v3_900_signal_profile'
SOURCE = ROOT/'evaluation/runs/codex_contract_beta300_s13_1050_v3_20260910/decisions_codex_contract_beta300_s13_1050_v3_20260910'


def main():
    global OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUTPUT)
    args = parser.parse_args()
    OUTPUT = args.out.resolve()
    if not OUTPUT.is_relative_to(ROOT/'diagnostics'):
        raise ValueError('Output must stay in worktree diagnostics')
    before = hashes()
    prepared = json.loads((PROFILE/'manifest.json').read_bytes())
    for path, expected in prepared['source_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != expected:
            raise ValueError('Prepared profile source changed: '+path)
    for item in prepared['outputs'].values():
        if hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('Prepared profile output changed')
    OUTPUT.mkdir(exist_ok=False)
    result = ProfileRunnerInvocationTests().invoke(
        OUTPUT, 'diagnostic-signal-profile', 'fixed_beta300v3_900_signal_profile/config.json')
    (OUTPUT/'stdout.txt').write_text(result.stdout, encoding='utf-8')
    (OUTPUT/'stderr.txt').write_text(result.stderr, encoding='utf-8')
    report = {'scope': 'Actual canonical VBS command, adapter and CSV consumer with fake COM. Two decisions and existing prediction path; no MPC search, no live VISSIM.',
              'exit_code': result.returncode, 'source_sha256': before,
              'source_unchanged': before == hashes(), 'commands': [], 'passed': False}
    if result.returncode == 0:
        for sec in (1,900):
            left_path, right_path = SOURCE/f'action_{sec:06d}.csv', OUTPUT/f'action_{sec:06d}.csv'
            def rows(path):
                with path.open(encoding='utf-8-sig', newline='') as stream:
                    return list(csv.DictReader(stream))
            left,right = rows(left_path),rows(right_path)
            differences = []
            if len(left) != len(right):
                differences.append({'reason':'row_count', 'left':len(left),'right':len(right)})
            for index,(a,b) in enumerate(zip(left,right)):
                if a.keys() != b.keys():
                    differences.append({'row':index, 'reason':'columns'})
                for key in a.keys() | b.keys():
                    if key != 'metadata' and a.get(key) != b.get(key):
                        differences.append({'row':index, 'key':key, 'left':a.get(key), 'right':b.get(key)})
            report['commands'].append({'time':sec, 'source_sha256':hashlib.sha256(left_path.read_bytes()).hexdigest(),
                                       'actual_sha256':hashlib.sha256(right_path.read_bytes()).hexdigest(),
                                       'rows':len(right), 'nonmetadata_column_differences':differences})
        with (OUTPUT/'signalTraceFile.csv').open(newline='') as stream:
            trace = list(csv.DictReader(stream))
        report['fake_readback_rows'] = len(trace)
        report['fake_readback_exact'] = bool(trace) and all(r['ok']=='1' and r['requested']==r['readback'] for r in trace)
        report['passed'] = (report['source_unchanged'] and report['fake_readback_exact']
                            and not any(r['nonmetadata_column_differences'] for r in report['commands']))
    report['producer_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (OUTPUT/'validation.json').write_text(json.dumps(report, indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report.get(k) for k in ('passed','exit_code','commands','fake_readback_rows','fake_readback_exact')}, indent=2))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
