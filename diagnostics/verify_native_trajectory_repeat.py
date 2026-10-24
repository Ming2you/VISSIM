"""Verify whether the failed meter trial repeated the native baseline trajectory.

This can qualify its finer observations for measurement calibration only. It
cannot turn a trial with an unapplied treatment into a valid metering experiment.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'evaluation/runs/codex_nc_s13_6056c94_20260909_retry'
REPEAT = ROOT / 'evaluation/runs/codex_meter10639_g5_s13_20260910'


def selected_records(path):
    digest = hashlib.sha256()
    count = 0
    header = None
    first = last = None
    with path.open('rb') as file:
        for raw in file:
            row = raw.strip()
            if not row or row.startswith(b'*'):
                continue
            if row.startswith(b'$VEHICLE:'):
                header = row.decode('utf-8')
                continue
            if row.startswith(b'$'):
                continue
            if header is None:
                raise ValueError('data before vehicle header')
            time = float(row.split(b';', 1)[0])
            if time <= 5396 and abs((time - 1) % 5) < 1e-8:
                digest.update(row + b'\n')
                count += 1
                first = time if first is None else first
                last = time
    return dict(header=header, rows=count, first_sec=first, last_sec=last,
                selected_record_sha256=digest.hexdigest(), path=str(path))


def main():
    rows = [selected_records(next(run.glob('vissim_eval/*.fzp')))
            for run in (BASELINE, REPEAT)]
    fields = ('header', 'rows', 'first_sec', 'last_sec', 'selected_record_sha256')
    equal = all(rows[0][key] == rows[1][key] for key in fields)
    result = dict(equal_at_all_original_record_times=equal, evidence=rows,
                  failed_trial_status='INVALID metering trial: its t=900 command failed; never use as metering treatment',
                  permitted_use='Finer native-baseline measurement only if equality and retained native/open actuation are independently verified')
    (ROOT / 'diagnostics/native_trajectory_repeat_check.json').write_text(
        json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    if not equal:
        raise SystemExit('Trajectories differ; do not reuse as the baseline')


if __name__ == '__main__':
    main()
