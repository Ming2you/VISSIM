"""One baseline-only ordered native trajectory/signal comparison."""
import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from diagnostics.audit_observed_nc_trajectory import payload
from diagnostics.audit_nc5400_native_signals import events


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    a = p.parse_args()
    a.run = a.run.resolve()
    receipt = json.loads((a.run/'run.json').read_text(encoding='utf-8-sig'))
    assert receipt['terminal_sec'] == 5400 and receipt['owned_native_alive'] is False
    log = (a.run/'stdout.txt').read_text()
    assert 'STAGE=SIM_DONE' in log and 'SIM_SEC=5400' in log and 'ERROR=' not in log
    assert not (a.run/'stderr.txt').read_bytes()
    assert receipt['exit_code'] in (None, 0)
    native = a.run/'vissim_eval'
    trajectory = payload(next(native.glob('*.fzp')))
    signals = events(next(native.glob('*.lsa')))
    expected = {'payload_sha256':'2a0747f1c8f363214273780782d97e5b7b5ca8b5024af8b745e26f5cbdabaa79',
                'rows':26693633, 'payload_bytes':1415951346, 'first_sec':1.0, 'last_sec':5400.0}
    expected_signals = {'event_sha256':'693864e6204fd2b0be1e7cfdea4de8c59b0343dde4d8f8639d118f17c7542e40',
                        'rows':30845, 'first_sec':1.0, 'last_sec':5400.0}
    with (a.run/'readback.csv').open(newline='', encoding='ascii') as f:
        readback = list(csv.DictReader(f))
    assert all(r['expected'] == r['actual'] for r in readback)
    result = {'baseline_run':str(a.run), 'reference_run':'codex_contract_nc_headoff_continuous_s13_5400_v3_20260910',
              'trajectory':trajectory, 'signals':signals,
              'trajectory_exact':all(trajectory[k] == v for k,v in expected.items()),
              'signal_events_exact':all(signals[k] == v for k,v in expected_signals.items()),
              'readback_rows':len(readback), 'all_readbacks_match':True,
              'original_wrapper_receipt_preserved':receipt,
              'exit_code_capture_limitation':'OS exit code missing in v1; native completion markers, no stderr, full payload and natural process exit checked independently' if receipt['exit_code'] is None else None,
              'reference_expected_trajectory':expected, 'reference_expected_signals':expected_signals,
              'scope':'One fast-mode physical equivalence check only; no repeat for demand candidates.'}
    output = a.run/'baseline_equivalence.json'
    assert not output.exists()
    output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('trajectory_exact','signal_events_exact','readback_rows')}))
    return 0 if result['trajectory_exact'] and result['signal_events_exact'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
